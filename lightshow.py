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

def psd():
    data = yield
    while data is None:
        data = yield
    while True:
        fftdata = np.fft.fft(data)
        psd = np.square(np.abs(fftdata))
        data = yield psd

def bucket(spec=[[((0, 0.25), 0.80), ((0, 0.5), 0.20), ((0.25, 1), 0.125)], [((0.2, 1.0), 1)], [((0.,1.), 1)]]):
    data = yield
    while data is None:
        data = yield
    while True:
        size = len(data)
        buckets = []
        for ls in spec:
            tot = 0
            for ((ii, jj), r) in ls:
                i, j = int(size*ii), int(size*jj)
                tot += r * np.sum(data[i:j])
            buckets += [tot]
        data = yield buckets

def diff(length=12, degree=2):
    init = yield
    xvals = (np.arange(0, length*2 - 1) % length) - (length - 1)
    running = np.tile(init, (length, 1))
    for i in range(2, length - 1):
        running[i, :] = yield
    i = length - 1
    data = yield
    while data is None:
        data = yield
    while True:
        running[i, :] = data
        xs = xvals[length - 1 - i : 2*length - 1 - i]
        poly = np.polyfit(xs, running, degree)
        i = (i + 1) % length
        data = yield poly[degree - 1]

def normalize(length=32):
    data = yield
    while data is None:
        data = yield
    running = np.tile(data, (length, 1))
    i = 0
    while True:
        running[i, :] = data
        mean = running.mean(axis=0)
        stddev = np.sqrt(np.square(running - mean).mean(axis=0))
        stddev[stddev == 0] = 1
        i = (i + 1) % length
        data = yield (data - mean) / stddev

def log():
    maxlen = 0
    data = yield
    while True:
        if data is not None:
            outstr = ''
            for datum in data:
                nextstr = '% *.5f' % (maxlen, datum)
                maxlen = max(maxlen, len(nextstr))
                outstr += nextstr
                outstr += '\t'
            print(outstr)
        data = yield data

def threshold(threshold=[1.04, 1.1, 1.5]):
    from itertools import cycle
    data = yield
    while data is None:
        data = yield
    while True:
        data = yield [i - j for (i, j) in zip(data, cycle(threshold))]

def colorize():
    states = [2, 1, 0, 0]
    perm = np.random.permutation(4)
    rand = random.Random()
    st = rand.getstate()
    data = yield
    while data is None:
        data = yield
    while True:
        if data[0] > 0:
            perm = np.random.permutation(4)
        if data[1] > 0:
            rand.seed()
            st = rand.getstate()
        data = yield ([states[i] for i in perm], st)

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
    rand = random.Random()
    try:
        while True:
            try:
                data, st = yield
            except TypeError:
                continue
            rand.setstate(st)
            if data is not None:
                doflair = lambda x: [rand.choice(x)]
                states = [null, doflair, noop]
                vals = [states[i] for i in data]
                lightMusic(vals)
    finally:
        lightSwitch()

def tubes(address='lights-24.mit.edu', port=6038):
    import dmx
    import colorsys as cl
    tube = dmx.LightPanel(dmx.DmxConnection(address, port, 0), 0)
    rand = random.Random()
    while True:
        try:
            (data, st), [bass, treble, total] = yield
        except TypeError:
            continue
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
    try:
        while True:
            data = yield
            if data is None:
                continue
            if data[0] > 0:
                light = random.choice(random.choice(groups))
                bri = 127 + int(np.clip(127 * np.log(data[0]), 0, 128))
                Thread(target=huego, args=(light, bri)).start()
    finally:
        br.groups[0].action(effect='none')

def composeg(*gens):
    rev = list(reversed(gens))
    for gen in rev:
        gen.send(None)
    while True:
        tmp = None
        for gen in rev:
            tmp = gen.send(tmp)

"""
We specify a digraph as a list of vertices each with a list `edges' such that
j is in edges just in case the coroutine depends (directly) on vertices[j].
Note that we can have loops.
"""
def composedig(*vertices):
    verts = list(vertices)
    vals = len(verts) * [None]
    for i in range(len(verts)):
        v, es = verts[i]
        v.send(None)
    while True:
        for i in range(len(verts)):
            v, es = verts[i]
            try:
                toSend = (vals[j] for j in es)
            except TypeError:
                toSend = vals[es]
            vals[i] = v.send(toSend)

if __name__ == "__main__":
    from sys import argv
    if len(argv) <= 1:
        composedig((micGen(device='hw:1,0,0'), ()), (psd(), 0), (bucket(), 1), (diff(), 2), (normalize(), 3), (threshold(), 4), (colorize(), 5), (traffik(), 6), (tubes(), [6, 5]))
    elif argv[1] == 'verbose':
        composedig((micGen(device='hw:1,0,0'), ()), (psd(), 0), (bucket(), 1), (diff(), 2), (normalize(), 3), (threshold(), 4), (colorize(), 5), (traffik(), 6), (tubes(), [6, 5]), (log(), 4))
    elif argv[1] == 'hue':
        composeg(hue(), threshold(), log(), normalize(), diff(), bucket(), psd(), micGen())
