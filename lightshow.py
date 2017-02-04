#!/usr/bin/env python2
## This is an example of a simple sound capture script.
##
## The script opens an ALSA pcm for sound capture. Set
## various attributes of the capture, and reads in a loop,
## Then prints the frequency list.

import alsaaudio, time, audioop
import pyaudio
import serial
import numpy
import sys
import math
import struct
import serial
import time

ser = serial.Serial('/dev/ttyACM0', 19200, timeout=1)

def lightSwitch(numbers):
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
    bass = [7, 10, 16, 18, 23, 26, 27, 28]
    midOne = [1, 5, 12, 13, 22]
    midTwo = [2, 3, 4, 6, 15, 21, 30]
    high = [9, 14, 17, 25, 31]
    constant = [29]
    return (bass * ls[0] + midOne * ls[1] + midTwo * ls[2] + high * ls[3] + constant)

inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE,alsaaudio.PCM_NONBLOCK)
#inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE,alsaaudio.PCM_NONBLOCK,device='hw:1,1,0')

rate = 8000

# Set attributes: Mono, 8000 Hz, 16 bit little endian samples
inp.setchannels(1)
inp.setrate(rate)
inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)

inp.setperiodsize(160)

def calculate_levels(data):
    # Use FFT to calculate volume for each frequency
    global MAX

    # Convert raw sound data to Numpy array
    fmt = "%dH" % (len(data) / 2)
    data2 = struct.unpack(fmt, data)
    data2 = numpy.array(data2, dtype='h')

    # Apply FFT
    fourier = numpy.fft.fft(data2)
    ffty = numpy.abs(fourier[0:len(fourier) / 2]) / 1000
    ffty1 = ffty[:len(ffty) / 2]
    ffty2 = ffty[len(ffty) / 2::] + 2
    ffty2 = ffty2[::-1]
    #print ffty1
    ffty = ffty1 + ffty2[:-1]
    ffty = numpy.log(ffty) - 2

    fourier = list(ffty)[4:-4]
    fourier = fourier[:len(fourier) / 2]

    size = len(fourier)

    # Add up for 6 lights
    levels = [sum(fourier[i:(i + size / 4)]) for i in xrange(0, size, size / 4)][:4]

    return levels

def thresholder(listy, threshold):
    returnable=[]
    for i in xrange(0,len(listy)):
        if listy[i] < threshold[i]:
            returnable.append(0)
        else:
            returnable.append(1)
    return returnable

running = 4*[[]]
offset = [2.5, 0.5, 0.25, 0.0]
scale = 4*[1.1]

if __name__ == "__main__":
    try:
        while True:
            # Read data from device
            l,data = inp.read()
            if l:
                # Return the maximum of the absolute value of all samples in a fragment.
                levels = calculate_levels(data)

                outstr = ''
                for i in xrange(0,len(levels)):
                    level = levels[i]
                    outstr += '% f' % level
                    outstr += '\t'
                    running[i].append(level)
                    if len(running[i]) > rate * 10:
                        running[i].pop(0)
                print(outstr)
                time.sleep(0.01)
                threshold = [offset[i] + scale[i]*numpy.mean(running[i]) for i in xrange(0,len(running))]
                lightSwitch(lightMusic(thresholder(levels,threshold)))
    finally:
        lightSwitch([])
        ser.close()
