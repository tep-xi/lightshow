#!/usr/bin/env python

import alsaaudio as aa
import numpy as np
import struct
import serial
import random

def micGen(device=None, rate=8000, periodFrames=170, numPeriods=2):
    if device is not None:
        inp = aa.PCM(aa.PCM_CAPTURE, card=device)
    else:
        inp = aa.PCM(aa.PCM_CAPTURE)
    inp.setchannels(1)
    inp.setrate(rate)
    inp.setformat(aa.PCM_FORMAT_S16_LE)
    inp.setperiodsize(periodFrames)
    totalFrames = periodFrames * numPeriods
    while True:
        rawdata = b''
        for i in range(numPeriods):
            l = 0
            while l != periodFrames:
                l, d = inp.read()
            rawdata += d
        fmt = "%dH" % (totalFrames)
        stereodata = np.array(struct.unpack(fmt, rawdata), dtype='int16')
        data = stereodata.reshape((-1,2)).sum(1)
        yield data

def psd(gen):
    for data in gen:
        fftdata = np.fft.fft(data)
        psd = np.square(np.abs(fftdata))
        yield psd

def bucket(spec=[(0, 0.2), (0.2, 1.0)]):
    def _bucket(gen):
        for data in gen:
            size = len(data)
            indices = [(int(size*i), int(size*j)) for (i, j) in spec]
            buckets = [np.sum(data[i:j]) for (i, j) in indices]
            yield buckets
    return _bucket

def diff(length=25, degree=2):
    def _diff(gen):
        init = next(gen)
        xvals = (np.arange(0, length*2 - 1) % length) - (length - 1)
        running = np.tile(init, (length, 1))
        for i in range(2, length - 1):
            running[i, :] = next(gen)
        i = length - 1
        for data in gen:
            running[i, :] = data
            xs = xvals[length - 1 - i : 2*length - 1 - i]
            poly = np.polyfit(xs, running, degree)
            yield poly[degree - 1]
            i = (i + 1) % length
    return _diff

def normalize(length=500):
    def _normalize(gen):
        init = next(gen)
        running = np.tile(init, (length, 1))
#       for i in range(2, length - 1):
#           running[i, :] = next(gen)
        i = 0
        for data in gen:
            running[i, :] = data
            mean = running.mean(axis=0)
            stddev = np.sqrt(np.square(running - mean).mean(axis=0))
            yield (data - mean) / stddev
            i = (i + 1) % length
    return _normalize

def log(gen):
    maxlen = 0
    for data in gen:
        outstr = ''
        for datum in data:
            nextstr = '% *.5f' % (maxlen, datum)
            maxlen = max(maxlen, len(nextstr))
            outstr += nextstr
            outstr += '\t'
        print(outstr)
        yield data

def threshold(threshold=[1.357, 1.25]):
    def _threshold(gen):
        if len(threshold) == 1:
            for data in gen:
                yield [i > threshold[0] for i in data]
        else:
            for data in gen:
                yield [i > j for (i, j) in zip(data, threshold)]
    return _threshold

def traffik(device='/dev/ttyACM0'):
    noop = lambda x: x
    null = lambda x: []
    ser = serial.Serial(device, 19200, timeout=1)
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
        constant = [29]
        many = [30]
        red = [7, 10, 18, 26, 27, 28]
        yellow = [1, 5, 12, 13, 15, 23]
        green = [3, 4, 6, 21, 22, 24]
        blue = [2, 9, 14, 16, 17, 25, 31]
        colors = [many, red, yellow, green, blue]
        lightSwitch(constant + [light for (f, lights) in zip(ls, colors) for light in f(lights)])
    def _traffik(gen):
        perm = np.random.permutation(4)
        rand = random.Random()
        def doflair(ls):
            st = rand.getstate()
            ret = rand.choice(ls)
            rand.setstate(st)
            return [ret]
        states = [noop, doflair, null, null]
        for data in gen:
            if data[0]:
                perm = np.random.permutation(4)
            if data[1]:
                rand.seed()
            vals = [(noop if data[0] else null)] + [states[i] for i in perm]
            lightMusic(vals)
    return _traffik

def composeg(*gens):
    rev = list(reversed(gens))
    chain = rev.pop(0)
    for gen in rev:
        chain = gen(chain)
    for data in chain:
        pass

if __name__ == "__main__":
    composeg(traffik(), threshold(), log, normalize(), diff(), bucket(), psd, micGen(device='hw:1,0,0'))
