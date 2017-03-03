# dmx over ethernet via python

import socket
import time
import math

KINET_MAGIC=b"\x04\x01\xdc\x4a"
KINET_VERSION=b"\x01\x00"
KINET_TYPE_DMXOUT=b"\x01\x01"

class DmxConnection(object):
    def __init__(self, address, port, dmx_port) :
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        self.sock.connect((address,port))
        self.dmx_port = dmx_port

    def send_dmx(self, data) :
        out=KINET_MAGIC+KINET_VERSION+KINET_TYPE_DMXOUT
        out+=b"\x00\x00\x00\x00" #seq
        out+=chr(self.dmx_port).encode('utf-8') # dmx port number
        out+=b"\x00" #flags
        out+=b"\x00\x00" # timerVal
        out+=b"\xFF\xFF\xFF\xFF" # uni
        out+=data
        if(len(out)!=self.sock.send(out)) :
            print("socket problem")
            raise SystemExit(1)

class sPDS480caConnection(object):
    def __init__(self, address, universe) :
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        self.sock.connect((address, 6038))
        self.universe = universe
        self.magic = (b"\x04\x01\xdc\x4a" # magic number
                      +b"\x01\x00" # kk version
                      +b"\x08\x01"
                      +b"\x00\x00\x00\x00\x00\x00\x00\x00"
                      +chr(universe).encode('utf-8')+b"\xD1\x00\x00\x00\x02\x00")

    def send_dmx(self, data) :
        self.sock.send(self.magic+data)
        # no error detection! yay!

class RGBLight(object):
    def __init__(self, row, col) :
        self.r = 0
        self.g = 0
        self.b = 0
        self.row = row
        self.col = col

    # h,s,b are from 0 to 1
    def sethue(self, hue, brightness, saturation) :
        angle = hue*6%6.0
        brightness = min(max(float(brightness), 0.0), 1.0)
        saturation = min(max(float(saturation), 0.0), 1.0)
        if angle<2.0 :
            self.r=1
            if angle<1.0 :
                self.g = 0
                self.b = 1.0-angle
            else :
                self.g = angle-1.0
                self.b = 0
        if angle>=2.0 and angle<4.0 :
            self.g=1
            if angle<3.0 :
                self.r=3.0-angle
                self.b=0
            else :
                self.r=0
                self.b=angle-3.0
        if angle>=4.0 :
            self.b=1
            if angle<5.0 :
                self.g=5.0-angle
                self.r=0
            else :
                self.g=0
                self.r=angle-5.0
        self.r=brightness*(min(max(brightness-saturation, 0.0), 1.0)*self.r+saturation)
        self.g=brightness*(min(max(brightness-saturation, 0.0), 1.0)*self.g+saturation)
        self.b=brightness*(min(max(brightness-saturation, 0.0), 1.0)*self.b+saturation)

    def setrgb(self, red, green, blue):
        self.r = red
        self.g = green
        self.b = blue

    # n.b. color-changing CK lights are not really designed to give off white-ish light
    # with subtle differences in color temperature (although CK does make some lights
    # that are designed to provide a wide range of color temperatures) but I wanted to
    # write this anyway. more deets on this algorithm at
    # http://www.tannerhelland.com/4435/convert-temperature-rgb-algorithm-code/ 
    # - sinback 2015
    def settemp(self, temperature, brightness) :
        # brightness a float between [0, 1]
        brightness = min(max(brightness, 0.0), 1.0)
        temperature = min(max(temperature, 1000.0), 40000.0)
        scaledTemp = temperature/100.0
        if scaledTemp < 66:
            self.r = brightness*255.0
        else:
            interim = scaledTemp - 60
            interim = 329.698727446 * (interim ** -0.1332047592)
            self.r = brightness*min(max(interim, 0.0), 255.0)

        if scaledTemp < 66:
            interim = scaledTemp
            interim = 99.4708025861 * math.log(interim) - 161.1195681661
            self.g = brightness*min(max(interim, 0.0), 255.0)
        else:
            interim = scaledTemp - 60
            interim = 288.1221695283 * (interim ** -0.0755148492)
            self.g = brightness*min(max(interim, 0.0), 255.0)

        if scaledTemp >= 66:
            self.b = brightness*255.0
        elif scaledTemp <= 19:
            self.b = brightness*0.0
        else:
            interim = scaledTemp - 10
            interim = 138.5177312231 * math.log(interim) - 305.0447927307 
            self.b = brightness*min(max(interim, 0.0), 255.0)

        self.r = self.r/255.0
        self.g = self.g/255.0
        self.b = self.b/255.0

class SimpleLights(object):
    def __init__(self, dmx) :
        self.lights = [[RGBLight(j, 0)] for j in range(0, 128)]
        self.dmx = dmx
        self.width = 1
        self.height = 128
        self.time = time.time()
    def output(self) :
        out = chr(0x00)
        for i in range(0,128) :
            out += bytearray([int(255*min(max(float(self.lights[i][0].r),0),1.0))])
            out += bytearray([int(255*min(max(float(self.lights[i][0].g),0),1.0))])
            out += bytearray([int(255*min(max(float(self.lights[i][0].b),0),1.0))])
        while(len(out)<512) :
            out += b"\x00"
        out += b"\xff\xbf"
        self.dmx.send_dmx(out)
    def outputAndWait(self, fps) :
        self.output()
        endtime = time.time()-self.time
        if(1.0/fps > endtime) :
            time.sleep(1.0/fps-endtime)
        self.time = time.time()

class LightPanel(object):
    def __init__(self, dmx, comp) :
        self.lights = [[RGBLight(j, i) for i in range(0,12)]
                       for j in range(0,12)]
        self.dmx = dmx
        self.width = 12
        self.height = 12
        self.comp = comp
        self.time = time.time()
    def output(self) :
        out = b"\x00"
        colors = [0 for i in range(0,500)]
        for c in range(0,6) :
            for r in range(0,12) :
                colors[3*(r+12*(5-c))+0]=self.lights[r][c].r
                colors[3*(r+12*(5-c))+1]=self.lights[r][c].g
                colors[3*(r+12*(5-c))+2]=self.lights[r][c].b
        for c in range(6,12) :
            for r in range(0,12) :
                colors[3*(r+12*c)+self.comp+0]=self.lights[r][c].r
                colors[3*(r+12*c)+self.comp+1]=self.lights[r][c].g
                colors[3*(r+12*c)+self.comp+2]=self.lights[r][c].b
        for i in range(0,len(colors)) :
            out+=bytearray([int(255*min(max(float(colors[i]),0),1.0))])
        while(len(out)<512) :
            out+=b"\x00"
        out+=b"\xff\xbf"
        self.dmx.send_dmx(out)

    def outputAndWait(self, fps) :
        self.output()
        endtime = time.time()-self.time
        if(1.0/fps > endtime) :
            time.sleep(1.0/fps-endtime)
        self.time = time.time()

class HalfLightPanel(object):
    # direction: 0 is "bottom right corner is (0,0)" and 1 is "bottom left ..."
    def __init__(self, dmx, direction) :
        self.width = 6
        self.height = 12
        self.direction = direction
        self.lights = [[RGBLight(j, i) for i in range(0, self.width)]
                       for j in range(0, self.height)]
        self.dmx = dmx
        self.time = time.time()
    def output(self) :
        out = chr(0)
        row = 0
        col = 0
        for i in range(0, 72) :
            row = i%12
            if self.direction == 0 :
                col = 5-(i//12)
            else :
                col = i//12
            l = self.lights[row][col]
            out += chr(int(255*min(max(pow(l.r, 0.9), 0.0), 1.0)))
            out += chr(int(255*min(max(pow(l.g, 0.9), 0.0), 1.0)))
            out += chr(int(255*min(max(pow(l.b, 0.9), 0.0), 1.0)))
        for i in range(12*6, 511) :
            out += chr(0)
        out += chr(0xbf)
        self.dmx.send_dmx(out)
    def outputAndWait(self, fps) :
        self.output()
        endtime = time.time()-self.time
        if(1.0/fps > endtime) :
            time.sleep(1.0/fps-endtime)
        self.time = time.time()

class PanelComposite(object):
    def __init__(self) :
        self.panels = []
        self.panelloc = []
        self.lights = [[]]
        self.width = 0
        self.height = 0
    def addPanel(self, panel, llrow, llcol) :
        self.panels.append(panel)
        self.panelloc.append((llrow, llcol))
        self.width=max(self.width, llcol+panel.width)
        self.height=max(self.height, llrow+panel.height)
        newlights = [[RGBLight(row, col) for col in range(self.width)] for row in range(self.height)]
        for row in self.lights :
            for light in row :
                newlights[light.row][light.col] = light
        for row in panel.lights :
            for light in row :
                light.row = llrow + light.row
                light.col = llcol + light.col
                newlights[light.row][light.col] = light
        self.lights = newlights
    def output(self) :
        for panel in self.panels :
            panel.output()
    def outputAndWait(self, fps) :
        t = False
        for panel in self.panels :
            if t :
                panel.output()
            t = True
        self.panels[0].outputAndWait(fps)

def getDefaultPanel() :
    return LightPanel(DmxConnection("lights-23.mit.edu", 6038, 0), 0)

if __name__=="__main__" :
    a = getDefaultPanel()
    color = 1.0
    while True :
        for row in a.lights :
            for light in row :
                light.b=color
                a.outputAndWait(30)
        for row in a.lights :
            for light in row :
                light.g=color
                a.outputAndWait(30)
        for row in a.lights :
            for light in row :
                light.r=color
                a.outputAndWait(30)
        color = 1.0-color
