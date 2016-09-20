#!/usr/bin/env python2
## This is an example of a simple sound capture script.
##
## The script opens an ALSA pcm for sound capture. Set
## various attributes of the capture, and reads in a loop,
## Then prints the frequency list.

import alsaaudio, time, audioop
import pyaudio # from http://people.csail.mit.edu/hubert/pyaudio/
import serial  # from http://pyserial.sourceforge.net/
import numpy   # from http://numpy.scipy.org/
import sys
import math
import struct

import lightagain

inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE,alsaaudio.PCM_NONBLOCK)
#inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE,alsaaudio.PCM_NONBLOCK,device='hw:1,1,0')

# Set attributes: Mono, 8000 Hz, 16 bit little endian samples
inp.setchannels(1)
inp.setrate(8000)
inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)

# The period size controls the internal number of frames per period.
# The significance of this parameter is documented in the ALSA api.
# For our purposes, it is suficcient to know that reads from the device
# will return this many frames. Each frame being 2 bytes long.
# This means that the reads below will return either 320 bytes of data
# or 0 bytes of data. The latter is possible because we are in nonblocking
# mode.


#This was 160
inp.setperiodsize(160)
chunk      = 2**11 # Change if too fast/slow, never less than 2**11
scale      = 100   # Change if too dim/bright
exponent   = 5     # Change if too little/too much difference between loud and quiet sounds
samplerate = 44100

def calculate_levels(data, chunk, samplerate):
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



while True:
    # Read data from device
    l,data = inp.read()
    if l:
        # Return the maximum of the absolute value of all samples in a fragment.
        levels = calculate_levels(data, chunk, samplerate)

        outstr = ''
        for level in levels:
            outstr += '% f' % level
            outstr += '\t'
        print(outstr)
        time.sleep(0.01)
        threshold = [1.7 * x for x in [7.0, 5.0, 3.5, 3.0]]
        lightagain.lightSwitch(lightagain.lightMusic(thresholder(levels,threshold)))






