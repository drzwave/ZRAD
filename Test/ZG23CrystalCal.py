#!/usr/bin/env python3
''' ZG23 Crystal calibration python script - 10/9/2023 - DrZWave@drzwave.com
    Adjusts the CTUNE value until the RF carrier frequency is within 1000Hz (1ppm).
    Programs the CTUNE value into NVM when complete.
    Returns the CTUNE value if calibration worked - otherwise 0,
    Requires a TinySA spectrum analyzer and a Silabs WSTK ProDevKit
    The DUT must have RailTest programmed into it (tested with 2.15.0)
    Note that the CTUNE is RETURNED! But not programmed into the DUT NVM. 
    A higher level script is expected to program Railtest, run this script, then store the value in the DUT NVM.

    Usage: python ZG23CrystalCal.py
'''
import serial   # install the pySerial library and not serial ("pip install pyserial"
import time
import sys, os
import traceback
sys.path.insert(0,'./tinySA') # add the TinySA library to the path - this was downloaded from tinysa.org and then improved
import tinySA as sa # needs numpy and matplotlib libraries

DEBUG = 3   # print debug messages - the higher the value, the more details are printed

# USB IDs for a WSTK to open the serial port to RailTest
WSTK_VID = 0x1366
WSTK_PID =  0x0105

# The crystal must be calibrated to within 1ppm or 1000hz
TARGET_FREQ = 908420000
MIN_FREQ = TARGET_FREQ-1000
MAX_FREQ = TARGET_FREQ+1000
START_FREQ=TARGET_FREQ-30000
STOP_FREQ =TARGET_FREQ+30000
# number of frequencies to scan in the range above - the more points, the slower the scan so this is a fairly good balance
POINTS_SCAN = 145

# Number of adjustments to CTUNE before giving up. Usually takes 3-5 trials.
MAX_TRIALS = 12

# Minimum RSSI signal stength to accept a txtone marker from the TinySA in dBm.
# Typically should be about -8 if the DUT is with 1 foot of the tinySA and has an antenna installed
# If multiple test stations are nearby, this value may want to be higher (IE: -10) to ignore adjacent stations. 
# Adjacent test stations typically must be at least 5 meters apart or they will interfere with each other.
MIN_RSSI_TXTONE = -20

def getwstkport() -> str:
    device_list = serial.tools.list_ports.comports()
    for device in device_list:
        if device.vid == WSTK_VID and device.pid == WSTK_PID:
            return device.device
    raise OSError("No WSTK found")

class ZG23CrystalCal:
    def __init__(self):
        try:
            self.wstk = getwstkport()
            self.wstkser = "123"
            #self.wcom=None
            self.wcom = serial.Serial(self.wstk, timeout=3)
            if DEBUG>5: print("WSTK COM Port={}".format(self.wstk))
            self.sa = sa.tinySA()   # open the COM port to TinySA
            if DEBUG>5: print("TinySA COM Port={}".format(self.sa.dev), flush=True)
        except Exception as err:
            print("failed to open devices:",err)
            traceback.print_tb(err.__traceback__)
            exit()
        
    @property

    def openwcom(self):
        if self.wcom is None:
            try:
                self.wcom = serial.Serial(self.wstk, timeout=3)
            except:
                print("Cal:Unable to open WSTK COM port")
                sys.exit(1)

    def closewcom(self):
        if self.wcom:
            self.wcom.close()
        self.wcom = None

    def InitWstkCom(self):
        ''' Init WSTK COM port AFTER programming Railtest.
            Check that the right version is being used.
        '''
        self.openwcom
        self.wcom.write("\n".encode())          # clear the buffer
        time.sleep(0.5)                         # wait for the DUT to stabilize - otherwise get garbage characters from UART
        self.wcom.reset_input_buffer()          # purge any characters already sent - typically the railtest boot message which also often includes garbage characters
        txt=self.RailTestCmd("getversion")
        if txt == None:
            raise("Unable to connect to RailTest - was it programmed properly?")
        if DEBUG>5: print("RailTest Version =",txt)
        # TODO add an assert if the version is not the expected one

    def RailTestCmd(self, cmd):
        ''' Send RailTest Command in cmd, return the 2nd line of the command '''
        #self.openwcom()
        self.openwcom
        cmd2=cmd + "\n"
        self.wcom.write(cmd2.encode())
        txt=self.wcom.readline()   # 1st line is just an echo of the command
        timeout=10
        while cmd.encode() not in txt:       # skip over any garbage looking for the command
            if DEBUG>8: print("cmd={}, not in response={}".format(cmd,txt)) 
            txt=self.wcom.readline()
            timeout -=1
            if timeout==0: break
        txt=self.wcom.readline()   # The line after the cmd echo should be the response if any
        cmd1=cmd.split(' ',1)       # look for the 1st word of the string
        if cmd1[0].encode() not in txt: 
            print("Error - invalid response {} to command {}".format(txt,cmd))
            return(None)
        # TODO maybe try the command a 2nd time if it has failed?
        return(txt.decode())
        
    def getCtune(self):
        ''' Get the current DUT CTUNE value in RAM'''
        txt=self.RailTestCmd("getctune")
        if DEBUG>8: print(txt)
        if "CTUNEXIANA:" in txt:
            # CTUNE command response = {{(getctune)}{CTUNEXIANA:0x09b}{CTUNEXOANA:0x0c3}} - pick out the 0x09b which is the CTUNE value
            ctune = txt[txt.find("0"):txt.find("}{CTUNEXO")]
            ct = int(ctune,0)
            if DEBUG>6: print("ctune={}".format(ct))
            return(ct)
        return None

    def setCtune(self, val):
        self.RailTestCmd("rx 0")
        self.RailTestCmd("setctune {}".format(val))

    def TxToneInit(self):
        ''' Setup RailTest to output a carrier wave at 908.42MHz'''
        self.RailTestCmd("rx 0")
        self.RailTestCmd("setzwavemode 1 3")
        self.RailTestCmd("setzwaveregion 1") # US
        self.RailTestCmd("setchannel 2") # 908.42MHz
        
    def TxToneOn(self):
        ''' turn on the carrier ''' 
        self.RailTestCmd("SetTxTone 1")

    def TxToneOff(self):
        ''' turn Off the carrier ''' 
        self.RailTestCmd("SetTxTone 0")

    def saInit(self):
        ''' Initialize the TinySA Spectrum Analyzer '''
        self.sa.rbw(1) # 0=AUTO which typically picks 1K - could choose 3k which is faster but less accurate
        self.sa.send_command("spur off \r")  # turn spur off which speeds up scanning
        self.sa.set_frequencies(START_FREQ, STOP_FREQ, POINTS_SCAN)
        self.sa.set_sweep(START_FREQ,STOP_FREQ)
        self.sa.send_scan(START_FREQ, STOP_FREQ,POINTS_SCAN) # start with a clean scan of the noise floor
        #self.sa.set_high_input() # not needed with the TinySA Ultra - but it does have to be in Ultra mode which is done via the GUI

    def CalibrateCrystal(self):
        ''' Run the Crystal Calibration algorithm and return the calibrated CTUNE value or -1 if calibration fails
            Typical CTUNE values are between 50 and 200 
        '''
        self.InitWstkCom()
        initialCtune=self.getCtune()
        self.TxToneInit()
        ctune=initialCtune
        #ctune=initialCtune -20  # +/- 20 for debugging will force CTUNE to start off wrong and then it should converge
        #self.setCtune(ctune)    # debug only with the line above
        self.saInit()           # Initialize the TinySA
        calibrated = False
        self.sa.pause() # make sure the SA is not scanning to run 1 scan and know when it has completed
        self.sa.send_scan(START_FREQ, STOP_FREQ,POINTS_SCAN) # start with a clean scan of the noise floor
        current_time = time.time()

        for trials in range(MAX_TRIALS): # usually takes less than this many tries to zero in on the proper value
            self.TxToneOn()  # turn on carrier wave out of DUT
            self.sa.send_scan(START_FREQ, STOP_FREQ,POINTS_SCAN) # start a scan - returns once the scan is complete which typically takes 1.5s
            freq=self.sa.fetch_marker() # returns the FREQ and the signal strength of the peak signal
            self.TxToneOff()
            if DEBUG > 1: print("ctune={} Freq={} in {:.2f}s".format(ctune,freq,time.time()-current_time), flush=True)
            current_time=time.time()
            if freq != None:
                if freq[1] > MIN_RSSI_TXTONE: # The signal strength has to be high or else just ignore the reading and try again
                    if (freq[0] > MIN_FREQ) and (freq[0] < MAX_FREQ): # then done
                        calibrated = True
                        break
                    else:
                        delta = max(1,min(30,abs(int((TARGET_FREQ-freq[0])/1500)))) # limit the amount of change in ctune for each trial
                        if freq[0] < TARGET_FREQ:
                            ctune -=delta
                        else:
                            ctune +=delta
                    self.setCtune(ctune)
                else:
                    if DEBUG>1: print("marker strength is low {}".format(freq[1]))

        if not calibrated:  # then calibration failed
            self.setCtune(initialCtune) # return the DUT to the original ctune value in anticipation of trying again
            if DEBUG>1: print("*** Calibration FAILED ***")
            ctune = -1

        self.sa.resume()
        self.closewcom
        return(ctune)
 
if __name__ == "__main__":
    wstk=ZG23CrystalCal()
    
    ctune = wstk.CalibrateCrystal()
    print("CTUNE={}".format(ctune))

    wstk.closewcom()

    print("exit")
    exit()
