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
    midTwo = [15, 2, 3, 4]
    high = [14, 17, 21, 25, 31]
    constant = [29]
    return (bass * ls[0] + midOne * ls[1] + midTwo * ls[2] + high * ls[3] + constant)


