#!/usr/bin/env python

import numpy as np
import random

def micGen(device=None, rate=8000, periodFrames=170, numPeriods=4):
    import alsaaudio as aa
    import struct
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

def bucket(spec=[[((0, 0.25), 0.80), ((0, 0.5), 0.20), ((0.25, 1), 0.125)], [((0.2, 1.0), 1)], [((0.,1.), 1)]]):
    def _bucket(gen):
        for data in gen:
            size = len(data)
            buckets = []
            for ls in spec:
                tot = 0
                for ((ii, jj), r) in ls:
                    i, j = int(size*ii), int(size*jj)
                    tot += r * np.sum(data[i:j])
                buckets += [tot]
            yield buckets
    return _bucket

def diff(length=12, degree=2):
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

def normalize(length=32):
    def _normalize(gen):
        init = next(gen)
        running = np.tile(init, (length, 1))
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

def threshold(threshold=[1.04, 1.1, 1.5]):
    from itertools import cycle
    def _threshold(gen):
        for data in gen:
            yield [i - j for (i, j) in zip(data, cycle(threshold))]
    return _threshold

def colorize(gen):
    states = [2, 1, 0, 0]
    perm = np.random.permutation(4)
    rand = random.Random()
    st = rand.getstate()
    for data in gen:
        if data[0] > 0:
            perm = np.random.permutation(4)
        if data[1] > 0:
            rand.seed()
            st = rand.getstate()
        yield ([states[i] for i in perm], st)

def traffik(device='/dev/ttyACM0'):
    from serial import Serial
    noop = lambda x: x
    null = lambda x: []
    ser = Serial(device, 19200, timeout=1)
    def lightSwitch(numbers=None):
        toSend = [0b00000000, ] * 4
        if numbers is not None:
            for light in numbers:
                if light >= 0 and light < 32:
                    pos = light % 8
                    index = light // 8
                    toSend[index] = toSend[index] | (0b10000000 >> pos)
                else:
                    toSend = [0b00000000, ] * 4
        else:
            toSend = [0b00000000, ] * 4
        ser.write(str(bytearray(toSend)))
    def lightMusic(ls):
        constant = [29]
        red = [7, 10, 18, 26, 27, 28]
        yellow = [1, 5, 12, 13, 15, 23, 30]
        green = [3, 4, 6, 21, 22, 24]
        blue = [2, 9, 14, 16, 17, 25, 31]
        colors = [red, yellow, green, blue]
        lightSwitch(constant + [light for (f, lights) in zip(ls, colors) for light in f(lights)])
    def _traffik(gen):
        rand = random.Random()
        try:
            for (data, st) in gen:
                rand.setstate(st)
                doflair = lambda x: [rand.choice(x)]
                states = [null, doflair, noop]
                vals = [states[i] for i in data]
                lightMusic(vals)
        finally:
            lightSwitch()
    return _traffik

def tubes(address='lights-24.mit.edu', port=6038):
    import dmx
    import colorsys as cl
    tube = dmx.LightPanel(dmx.DmxConnection(address, port, 0), 0)
    def _tubes(gen):
        rand = random.Random()
        for (data, st, bass, total) in gen:
            rand.setstate(st)
            r = rand.random() ** 4
            red = np.array([1,0,0])
            ylo = np.array([1,1,0])
            grn = np.array([0,1,0])
            blu = np.array([0,0,1])
            colors = [red, ylo, grn, blu]
            rgb = np.sum([color * (1-r if state == 2 else r if state == 1 else 0) for (color, state) in zip(colors, data)], axis=0)
            hue = cl.rgb_to_hsv(*rgb)[0]
            sat = (1 + np.clip(np.exp(bass), 0, 1))/2
            val = (1 + 2*np.clip(np.exp(total), 0, 1))/3
            out = cl.hsv_to_rgb(hue, sat, val)
            for row in tube.lights:
                for light in row:
                    light.r = out[0]
                    light.g = out[1]
                    light.b = out[2]
            out = cl.hsv_to_rgb((hue + 0.5) % 1, sat, val)
            tube.lights[11][4].r = out[0]
            tube.lights[11][4].g = out[1]
            tube.lights[11][4].b = out[2]
            tube.output()
    return _tubes

def hue(bridge='hue', password=None, lobri=16, groups=[[1,2,3],[4,5],[6]]):
    from qhue import Bridge
    from threading import Thread
    if password is None:
        from appdirs import user_config_dir
        passfile = open(user_config_dir(roaming=True) + '/huekey', 'r')
        password = passfile.read().strip()
        passfile.close()
    br = Bridge(bridge, password)
    br.groups[0].action(effect='colorloop', bri=lobri)
    def huego(light, hibri):
        br.lights[light].state(transitiontime=0, sat=255, bri=hibri)
        br.lights[light].state(transitiontime=1, sat=255, bri=lobri)
    def _hue(gen):
        try:
            for data in gen:
                if data[0] > 0:
                    light = random.choice(random.choice(groups))
                    bri = 127 + int(np.clip(127 * np.log(data[0]), 0, 128))
                    Thread(target=huego, args=(light, bri)).start()
        finally:
            br.groups[0].action(effect='none')
    return _hue

def composeg(*gens):
    rev = list(reversed(gens))
    chain = rev.pop(0)
    for gen in rev:
        chain = gen(chain)
    for data in chain:
        pass

"""
we specify a DAG as a list of vertices along with a list of lists of indices
corresponding to directed edges, where edges[i] can contain j only if i < j
"""
def composedag(vertices, edges):
    pass

if __name__ == "__main__":
    from sys import argv
    if len(argv) <= 1:
        composeg(traffik(), colorize, threshold(), normalize(), diff(), bucket(), psd, micGen(device='hw:1,0,0'))
    elif argv[1] == 'verbose':
        composeg(traffik(), colorize, threshold(), log, normalize(), diff(), bucket(), psd, micGen(device='hw:1,0,0'))
    elif argv[1] == 'hue':
        composeg(hue(), threshold(), log, normalize(), diff(), bucket(), psd, micGen())
