#!/usr/bin/env python

import alsaaudio
import serial
import numpy
import struct

rate = 8000
framesbackfit = 100
framesbackavg = 2*rate
buckets = 4
fitdeg = 2
offset = buckets * [0.0]
scale = [2.0, 2.0, 1.8, 1.6]
device = -1
periodsize = 170

ser = serial.Serial('/dev/ttyACM0', 19200, timeout=1)

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
    ser.write(toSend)


def lightMusic(ls):
    bass = [7, 10, 18, 26, 27, 28]
    midOne = [1, 5, 12, 13, 15, 23, 30]
    midTwo = [3, 4, 6, 21, 22, 24]
    high = [2, 9, 14, 16, 17, 25, 31]
    constant = [29]
    return (bass * ls[0] + midOne * ls[1] + midTwo * ls[2] + high * ls[3] + constant)

inp = alsaaudio.pcms(type=alsaaudio.PCM_CAPTURE)[device]

inp.setchannels(1)
inp.setrate(rate)
inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)

inp.setperiodsize(periodsize)

def calculate_psd(size, rawdata):
    # Convert raw sound data to Numpy array
    fmt = "%dH" % size
    data = numpy.array(struct.unpack(fmt, rawdata), dtype='int16')

    fourierdata = numpy.fft.fft(data)
    psd = numpy.square(numpy.abs(fourierdata))

    return psd

running = numpy.zeros((framesbackfit, buckets))
runningpd = numpy.zeros((framesbackavg, buckets))
xvals = numpy.arange(0, framesbackfit*2 - 1) % framesbackfit

if __name__ == "__main__":
    try:
        j = 0
        while True:
            for i in range(0, framesbackfit):
                size = 0
                while size != periodsize:
                    size, data = inp.read()
                psd = calculate_psd(size, data)
                padpsd = numpy.pad(psd, (0, size % buckets), 'constant')
                levels = numpy.sum(padpsd.reshape((buckets, -1)), axis=1)
                running[i,:] = levels
                pd = numpy.polyfit(xvals[i:i+framesbackfit], running, fitdeg)[fitdeg - 1]
                pospd = numpy.copy(pd)
                pospd[pospd < 0] = 0
                runningpd[j,:] = pospd

                outstr = ''
                for i in range(0, buckets):
                    outstr += '% f' % pd[i]
                    outstr += '\t'
                #print(outstr)

                threshold = offset + scale * numpy.mean(runningpd, axis=0)
                print(threshold)

                vals = [a < b for (a, b) in zip(threshold, pd)]

                lightSwitch(lightMusic(vals))

                j = (j + 1) % framesbackavg
    finally:
        lightSwitch()
        ser.close()
