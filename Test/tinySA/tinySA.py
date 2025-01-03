#!/usr/bin/env python3
import serial
import numpy as np
import pylab as pl
import struct
from serial.tools import list_ports

# These are generic ST USB->UART chip VID/PID so they are not certain to find the proper device
VID = 0x0483 #1155
PID = 0x5740 #22336

# Get tinysa device automatically
def getport() -> str:
    device_list = list_ports.comports()
    for device in device_list:
        if device.vid == VID and device.pid == PID:
            return device.device
    raise OSError("device not found")

REF_LEVEL = (1<<9)

class tinySA:
    def __init__(self, dev = None):
        self.dev = dev or getport()
        self.serial = None
        self._frequencies = None
        self.points = 101
        
    @property
    def frequencies(self):
        return self._frequencies

    def set_frequencies(self, start = 1e6, stop = 350e6, points = None):
        if points:
            self.points = points
        self._frequencies = np.linspace(start, stop, self.points)

    def open(self):
        if self.serial is None:
            self.serial = serial.Serial(self.dev)

    def close(self):
        if self.serial:
            self.serial.close()
        self.serial = None

    def send_command(self, cmd):
        self.open()
        self.serial.write(cmd.encode())
        self.serial.readline() # discard empty line
#        print(self.serial.readline()) # discard empty line

    def cmd(self, text):
        self.open()
        self.serial.write((text + "\r").encode())
        self.serial.readline() # discard empty line
        data = self.fetch_data()
        return data
#        self.serial.readline() # discard empty line

    def set_sweep(self, start, stop):
        if start is not None:
            self.send_command("sweep start %d\r" % start)
        if stop is not None:
            self.send_command("sweep stop %d\r" % stop)

    def set_span(self, span):
        if span is not None:
            self.send_command("sweep span %d\r" % span)

    def set_center(self, center):
        if center is not None:
            self.send_command("sweep center %d\r" % center)

    def set_level(self, level):
        if level is not None:
            self.send_command("level %d\r" % level)

    def set_output(self, on):
        if on is not None:
            if on:
                self.send_command("output on\r")
            else:
                self.send_command("output off\r")

    def set_low_output(self):
        self.send_command("mode low output\r")

    def set_low_input(self):           
        self.send_command("mode low input\r")
    
    def set_high_input(self):           
        self.send_command("mode high input\r")
    
    def set_frequency(self, freq):
        if freq is not None:
            self.send_command("freq %d\r" % freq)

    def measure(self, freq):
        if freq is not None:
            self.send_command("hop %d 2\r" % freq)
            data = self.fetch_data()
            for line in data.split('\n'):
                if line:
                    return float(line)

    def temperature(self):
        self.send_command("k\r")
        data = self.fetch_data()
        for line in data.split('\n'):
            if line:
                return float(line)

    def rbw(self, data=0):
        if data == 0:
            self.send_command("rbw auto\r")
            return
        if data<1:
            self.send_command("rbw %f\r" % data)
            return
        if data >= 1:
            self.send_command("rbw %d\r" % data)
        
    def fetch_data(self):
        result = ''
        line = ''
        while True:
            c = self.serial.read().decode('utf-8')
            if c == chr(13):
                next # ignore CR
            line += c
            if c == chr(10):
                result += line
                line = ''
                next
            if line.endswith('ch>'):
                # stop on prompt
                break
        return result

#    def fetch_array(self, sel):
#        self.send_command("data %d\r" % sel)
#        data = self.fetch_data()
#        x = []
#        for line in data.split('\n'):
#            if line:
#                x.extend([float(d) for d in line.strip().split(' ')])
#        return np.array(x[0::2]) + np.array(x[1::2]) * 1j

#    def fetch_gamma(self, freq = None):
#        if freq:
#            self.set_frequency(freq)
#        self.send_command("gamma\r")
#        data = self.serial.readline()
#        d = data.strip().split(' ')
#        return (int(d[0])+int(d[1])*1.j)/REF_LEVEL

    def resume(self):
        self.send_command("resume\r")
    
    def pause(self):
        self.send_command("pause\r")
    
    def marker_value(self, nr = 1):
        self.send_command("marker %d\r" % nr)
        data = self.fetch_data()
        line = data.split('\n')[0]
#        print(line)
        if line:
            dl = line.strip().split(' ')
            if len(dl) >= 4:
                d = line.strip().split(' ')[3]
                return float(d)
        return 0

    def fetch_marker(self, nr = 1):
        ''' Return a list of [Frequency, value] or None'''
        self.send_command("marker %d\r" % nr)
        data = self.fetch_data()
        line = data.split('\n')[0]
#        print(line)
        if line:
            dl = line.strip().split(' ')
            if len(dl) >= 4:
                freq = line.strip().split(' ')[2]
                val = line.strip().split(' ')[3]
                try:
                    return [float(freq), float(val)]
                except:
                    pass
        return None

    def data(self, array = 2):
        self.send_command("data %d\r" % array)
        data = self.fetch_data()
        x = []
        for line in data.split('\n'):
            if line:
                d = line.strip().split(' ')
                x.append(float(line))
        return np.array(x)

    def fetch_frequencies(self):
        self.send_command("frequencies\r")
        data = self.fetch_data()
        x = []
        for line in data.split('\n'):
            if line:
                x.append(float(line))
        self._frequencies = np.array(x)

    def send_scan(self, start = 1e6, stop = 900e6, points = None):
        if points:
            self.send_command("scan %d %d %d\r"%(start, stop, points))
        else:
            self.send_command("scan %d %d\r"%(start, stop))

    def scan(self):
        segment_length = 101
        array0 = []
        array1 = []
        if self._frequencies is None:
            self.fetch_frequencies()
        freqs = self._frequencies
        while len(freqs) > 0:
            seg_start = freqs[0]
            seg_stop = freqs[segment_length-1] if len(freqs) >= segment_length else freqs[-1]
            length = segment_length if len(freqs) >= segment_length else len(freqs)
            #print((seg_start, seg_stop, length))
            self.send_scan(seg_start, seg_stop, length)
            array0.extend(self.data(0))
            array1.extend(self.data(1))
            freqs = freqs[segment_length:]
        self.resume()
        return (array0, array1)
    
    def capture(self):
        from PIL import Image
        self.send_command("capture\r")
        b = self.serial.read(320 * 240 * 2)
        x = struct.unpack(">76800H", b)
        # convert pixel format from 565(RGB) to 8888(RGBA)
        arr = np.array(x, dtype=np.uint32)
        arr = 0xFF000000 + ((arr & 0xF800) >> 8) + ((arr & 0x07E0) << 5) + ((arr & 0x001F) << 19)
        return Image.frombuffer('RGBA', (320, 240), arr, 'raw', 'RGBA', 0, 1)

    def logmag(self, x):
        pl.grid(True)
        pl.xlim(self.frequencies[0], self.frequencies[-1])
        pl.plot(self.frequencies, x)
        
    def writeCSV(self,x,name):
        f = open(opt.save, "w")
        for i in range(len(x)):
            print("%d, "%self.frequencies[i], "%2.2f"%x[i], file=f)


if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser(usage="%prog: [options]")
    parser.add_option("-p", "--plot", dest="plot",
                      action="store_true", default=False,
                      help="plot rectanglar", metavar="PLOT")
    parser.add_option("-c", "--scan", dest="scan",
                      action="store_true", default=False,
                      help="scan by script", metavar="SCAN")
    parser.add_option("-S", "--start", dest="start",
                      type="float", default=1e6,
                      help="start frequency", metavar="START")
    parser.add_option("-E", "--stop", dest="stop",
                      type="float", default=900e6,
                      help="stop frequency", metavar="STOP")
    parser.add_option("-N", "--points", dest="points",
                      type="int", default=101,
                      help="scan points", metavar="POINTS")
    parser.add_option("-P", "--port", type="int", dest="port",
                      help="port", metavar="PORT")
    parser.add_option("-d", "--dev", dest="device",
                      help="device node", metavar="DEV")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="verbose output")
    parser.add_option("-C", "--capture", dest="capture",
                      help="capture current display to FILE", metavar="FILE")
    parser.add_option("-e", dest="command", action="append",
                      help="send raw command", metavar="COMMAND")
    parser.add_option("-o", dest="save",
                      help="write CSV file", metavar="SAVE")
    (opt, args) = parser.parse_args()

    nv = tinySA(opt.device or getport())

    if opt.command:
        print(opt.command)
        for c in opt.command:
            nv.send_command(c + "\r")
        data = nv.fetch_data()
        print(data)

    if opt.capture:
        print("capturing...")
        img = nv.capture()
        img.save(opt.capture)
        exit(0)

 #   nv.set_port(opt.port)
    if opt.start or opt.stop or opt.points:
        nv.set_frequencies(opt.start, opt.stop, opt.points)
#    plot = opt.plot 
    if opt.plot or opt.save or opt.scan:
        p = int(opt.port) if opt.port else 0
        if opt.scan or opt.points > 101:
            s = nv.scan()
            s = s[p]
        else:
            if opt.start or opt.stop:
                nv.set_sweep(opt.start, opt.stop)
            nv.fetch_frequencies()
            s = nv.data(p)
#            nv.fetch_frequencies()
    if opt.save:
        nv.writeCSV(s,opt.save)
    if opt.plot:
        nv.logmag(s)
        pl.show()
