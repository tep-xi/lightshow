#!/usr/bin/env python

import alsaaudio
import serial
import numpy
import struct
import argparse

buckets = 4

parser = argparse.ArgumentParser(description='Run the light show.')
parser.add_argument('-s', '--serial', metavar='ser', default='/dev/ttyACM0', const=None, nargs='?', help='serial device; if called without an argument disables serial')
parser.add_argument('-d', '--device', metavar='dev', default=None, help='audio input device')
parser.add_argument('-r', '--rate', metavar='N', default=8000, type=int, help='audio rate')
parser.add_argument('-p', '--period', metavar='N', default=170, type=int, help='period size for audio input')
parser.add_argument('--periods-fit', metavar='N', default=100, type=int, help='number of periods back to use for finding the derivative')
parser.add_argument('--periods-avg', metavar='N', default=16000, type=int, help='number of periods back to use for thresholding')
parser.add_argument('--fit-degree', metavar='deg', default=2, type=int, help='degree of the fitting polynomial')
parser.add_argument('--offset', metavar='float', nargs=buckets, default=buckets*[0.0], type=float, help='offset for each of the ' + str(buckets) + ' light groupings')
parser.add_argument('--scale', metavar='float', nargs=buckets, default=[2.0, 2.0, 1.8, 1.6], type=float, help='scale for each of the ' + str(buckets) + ' light groupings')

args = parser.parse_args()

if args.serial is not None:
    ser = serial.Serial('/dev/ttyACM0', 19200, timeout=1)
else:
    ser = None

def lightSwitch(numbers=None):
    toSend = [0b00000000, ] * 4
    if numbers:
        for light in numbers:
            if light >= 0 and light < 32:
                pos = light % 8
                index = light // 8
                toSend[index] = toSend[index] | (0b10000000 >> pos)
            else:
                toSend = [0b00000000, ] * 4
    else:
        toSend = [0b00000000, ] * 4
    if ser is not None:
        ser.write(str(bytearray(toSend)))


def lightMusic(ls):
    bass = [7, 10, 18, 26, 27, 28]
    midOne = [1, 5, 12, 13, 15, 23, 30]
    midTwo = [3, 4, 6, 21, 22, 24]
    high = [2, 9, 14, 16, 17, 25, 31]
    constant = [29]
    return (bass * ls[0] + midOne * ls[1] + midTwo * ls[2] + high * ls[3] + constant)

if args.device is not None:
    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, card=args.device)
else:
    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE)

inp.setchannels(1)
inp.setrate(args.rate)
inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)

inp.setperiodsize(args.period)

def calculate_psd(size, rawdata):
    # Convert raw sound data to Numpy array
    fmt = "%dH" % size
    data = numpy.array(struct.unpack(fmt, rawdata), dtype='int16')

    fourierdata = numpy.fft.fft(data)
    psd = numpy.square(numpy.abs(fourierdata))

    return psd

running = numpy.zeros((args.periods_fit, buckets))
runningpd = numpy.zeros((args.periods_avg, buckets))
xvals = numpy.arange(0, args.periods_fit*2 - 1) % args.periods_fit

if __name__ == "__main__":
    try:
        j = 0
        maxlen = 0
        while True:
            for i in range(0, args.periods_fit):
                size = 0
                while size != args.period:
                    size, data = inp.read()
                psd = calculate_psd(size, data)
                padpsd = numpy.pad(psd, (0, size % buckets), 'constant')
                levels = numpy.sum(padpsd.reshape((buckets, -1)), axis=1)
                running[i,:] = levels
                pd = numpy.polyfit(xvals[i:i+args.periods_fit], running, args.fit_degree)[args.fit_degree - 1]
                pospd = numpy.copy(pd)
                pospd[pospd < 0] = 0
                runningpd[j,:] = pospd

                outstr = ''
                for i in range(0, buckets):
                    nextstr = '% *.0f' % (maxlen, pd[i] / 1000)
                    maxlen = max(maxlen, len(nextstr))
                    outstr += nextstr
                    outstr += '\t'
                print(outstr)

                threshold = args.offset + args.scale * numpy.mean(runningpd, axis=0)

                vals = [a < b for (a, b) in zip(threshold, pd)]

                lightSwitch(lightMusic(vals))

                j = (j + 1) % args.periods_avg
    finally:
        lightSwitch()
        if ser is not None:
            ser.close()
