#!/usr/bin/env python3
''' Z-Wave Alliance ZRADMini calibrate, program, test and print the QR code python script
    A Zebra label printer must be connected to the computer this program is run on
    A Zebra ZD411-300dpi is recommended. Do NOT use a 203dpi as it does not have sufficient resolution.

    Typically two DUTs are tested at a time. 
    One is being programmed/tested while the operator inserts the next DUT into the other jig.
    A command line is visible to the operator to issue commands.
    Typically they just press enter when the next DUT is ready and a PASS/FAIL is printed along with a QR code label.

    Recommendation is to call this script with a shell that assigns LCOM, RCOM, LSER and RSER.

    Several of the variables just below here may need to be customized for a specific test station.

    Steps:
    1) The SE version is checked that it matches the expected value or is upgraded 
    2) If CTUNE has not been set, then the crystal is calibrated
    3) Flash application 
    4) Run a quick functional test
    5) Print the QR code labels
    6) Display pass/fail to the screen and wait for the operator to insert the next DUT
    
    TODO - add a test for the USB data interface as there have been several board with a manufacturing defect in the USB circuitry
        Requires the operator plug in a USB cable. 
        Better solution would be test pads on the 2 USB data pins (and +5V/GND).
'''

import serial
import time
import sys, os, subprocess
import traceback
from packaging import version   # for comparing version numbers
from SmartStartQR import *
from serial.tools import list_ports
from PIL import Image
import ZG23CrystalCal
import zpl        # Zebra ZPL creation library - convert the PNG to ZPL
import zebra      # Zebra label printer library - send the ZPL code to the printer

# These 2 values are the minimum and maximum expected current measurements in milliAmps of the DUT using the WSTK AEM
# They have be derived empircally and may need future adjustments - TODO - need more testing here!!!
CURRENT_MIN = 5.0
CURRENT_MAX = 10.0

DEBUG = 5   # print debug messages - the higher the value, the more details are printed

# USB IDs for a WSTK to open the serial port to RailTest
WSTK_VID = 0x1366
WSTK_PID =  0x0105

APPLICATION_FILENAME = "../Software/ZRAD_ED_merged.s37"
RAILTEST_FILENAME = "../Software/railtest_ZG23_442.s37"

# The Secure Engine in the EFR32xG23 must match the application SSDK version!
# See AN1222 Production Programming of Series 2 Devices for more details.
# The .SEU file is only used if secure boot is enabled otherwise the .hex file is used.
# Copy the file from: C:\Users\<username>\SimplicityStudio\SDKs\<GDSK40203>\util\se_release\public
EXPECTED_SE_VERSION = "2.2.6"
SECURE_ENGINE_FILENAME = "../Software/s2c3_se_fw_upgrade_app_2v2p6.hex"

# path and executable to silabs commander
CMDR = "C:/SiliconLabs/SimplicityStudio/v5/developer/adapter_packs/commander/commander.exe"

# for debugging - skip the label printing when True, normally False
#SKIP_PRINTING = True
SKIP_PRINTING = False

class ZRADCalProgTest:
    ''' Top level python script for testing the ZRADMini '''

    def __init__(self):
        self.wstk = ["COM4", None]  # typically 2 WSTKs are used to test one while the other is being clamped into the jig
        self.wstkser = ["440263534", "456"]
        try:
            for i in sys.argv:
                if "LCOM" in i:                     # See USAGE for details
                    self.wstk[0] = i.split('=')[1]
                elif "RCOM" in i:
                    self.wstk[1] = i.split('=')[1]
                elif "LSER" in i:
                    self.wstkser[0] = i.split('=')[1]
                elif "RSER" in i:
                    self.wstkser[1] = i.split('=')[1]
            self.wcom=None
        except Exception as err:
            print("failed to open devices:",err)
            traceback.print_tb(err.__traceback__)
            exit()
        
    @property

    def openwcom(self):
        if self.wcom is None:
            try:
                self.wcom = serial.Serial(self.wstk[self.side], timeout=3)
            except:
                print("Unable to open WSTK COM port")
                exit()

    def closewcom(self):
        if self.wcom:
            self.wcom.close()
        self.wcom = None

    def GetSEFirmwareVersion(self):
        ''' Return the version of the Secure Engine in the EFR32 chip as a Bytes array Ex: "2.1.0" '''
        rtn=subprocess.check_output(CMDR + " security status -d EFR32ZG23 --s {}".format(self.wstkser[self.side]),shell=True)
        if "SE Firmware" not in rtn.decode():
            print("SE firmware version get failed:\n\r{}\n\r".format(rtn))
            return(False)
        seVer = rtn.decode().split('\r')
        seVer2 = seVer[0].split(' ')[-1]
        for i in seVer:                 # if the DUT is locked, unlock it which also resets to factory fresh
            if "Debug lock" in i:
                if DEBUG>6: print("DUT locked - unlocking") 
                if "Enabled" in i:
                    self.FactoryFresh()
                break
        return(seVer2)

    def ProgramSecureEngine(self):
        ''' Check the SE version and update if out of date 
            Returns True if OK, False if it fails
        '''
        startSEupdate = time.time()
        seVer2=self.GetSEFirmwareVersion()
        if version.parse(EXPECTED_SE_VERSION) > version.parse(seVer2): # SE needs to be updated
            if DEBUG>4: print("Updating SE firmware from {} to {}".format(seVer2,EXPECTED_SE_VERSION))
            rtn=subprocess.check_output(CMDR + " flash --masserase -d EFR32ZG23 {} --s {}".format(SECURE_ENGINE_FILENAME,self.wstkser[self.side]),shell=True)
            time.sleep(2) # Per the AN1222 App note, wait 2s for the SE to update flash and boot
            seVer2=self.GetSEFirmwareVersion()
            if seVer2==False or version.parse(EXPECTED_SE_VERSION) != version.parse(seVer2):
                print("FAILED to update SE version")
                return(False)
            if DEBUG>4: print("SE firmware updated in {}s".format(time.time() - startSEupdate))
        elif version.parse(EXPECTED_SE_VERSION) != version.parse(seVer2):
            if DEBUG>2:print("***NOTE*** SE version is NEWER {} than the expected version {}. The application firmware may need to be updated!".format(seVer2,EXPECTED_SE_VERSION))
        else:    # if the SE version is the expected version, then keep going
            if DEBUG>4:print("SE has the expected version {}".format(seVer2))
        return(True)

    def FlashRailTest(self):
        if DEBUG>7: print("Flashing RailTest start")
        # Flash RailTest into the DUT to prepare for calibration
        rtn=subprocess.check_output(CMDR + " flash -d EFR32ZG23 {} --s {}".format(RAILTEST_FILENAME,self.wstkser[self.side]),shell=True)
        if "completed successfully" not in rtn.decode():
            print("Flashing RailTest failed")
            print(rtn)
            return(False)
        if DEBUG>7: print("Flashing RailTest complete")
        return(True)

    def CalibrateCrystal(self):
        '''Check if CTUNE is set, if not, run calibration #################### 
            Returns True if OK, False if it fails
        '''
        rtn=subprocess.check_output(CMDR + " ctune get -d EFR32ZG23 --s {}".format(self.wstkser[self.side]), shell=True)
        cal1 = rtn.decode().split('\r')
        if DEBUG>9: print("Cal={}".format(cal1))
        for idx in range(len(cal1)):
            if "Token" in cal1[idx]:
                if "Not" in cal1[idx]:
                    if not self.FlashRailTest():
                        return(False)
                    cal=ZG23CrystalCal.ZG23CrystalCal()
                    cal.wstk=self.wstk[self.side]
                    cal.wstkser=self.wstkser[self.side]
                    ctune=cal.CalibrateCrystal()
                    if ctune<=0:    # CTUNE failed
                        return(False)
                    rtn=subprocess.check_output(CMDR + " ctune set --value {} -d EFR32ZG23 --s {}".format(ctune, self.wstkser[self.side]), shell=True)
                    if DEBUG>9: print(rtn)
                    cal.closewcom
                else: # already calibrated so skip this part - The crystal can be recalibrated by running the calibation script
                    if DEBUG>7: print("Crystal Cal={}".format(cal1[idx][1:]))
                    break
        return(True)

    def FlashApplication(self):
        ''' Flash the application which includes the bootloader and keys'''
        startprogram = time.time()
        if DEBUG>2: print("Flashing Application start",flush=True)
        rtn=subprocess.check_output(CMDR + " flash -d EFR32ZG23 {} --s {}".format(APPLICATION_FILENAME,self.wstkser[self.side]),shell=True)
        if "completed successfully" not in rtn.decode():
            print("Flashing Application failed")
            print(rtn)
            return(False)
        if DEBUG>2: print("Flashing Application complete in {} seconds".format(round(time.time()-startprogram,2)),flush=True)
        time.sleep(0.5) # wait for the chip to boot and compute the DSK 
        return(True)

    def SendWcom(self,cmd):
        ''' Send a serial command to the application '''
        self.openwcom
        self.wcom.write(cmd.encode() + b'\n')
        time.sleep(1)
        self.closewcom

    def QuickFunctionalTest(self):
        ''' quick check of the voltage/current - if outside of the expected norm, fail the DUT '''
        aem=subprocess.check_output(CMDR+ " aem measure --windowlength 200 --s {}".format(self.wstkser[self.side]),shell=True)
        mA1 = aem.decode().split('\r')
        for i in range(len(mA1)):
            if "mA" in mA1[i]:
                mA2=mA1[i]
                break
        mA3=mA2.split(' ')
        mA = float(mA3[2])
        if (mA < CURRENT_MIN) or (mA > CURRENT_MAX):
            print("*** FAILED *** - DUT failed current test. Measured {}mA, Min={},Max{}".format(mA,CURRENT_MIN,CURRENT_MAX))
            return(False)
        #self.SendWcom("RED ON") - this doesn't work and locks up the WCOM port on the 2nd pass
        if DEBUG>7: print("Functional Test passed - DUT={}mA".format(mA3[2]))
        return(True)

    def CreateQRImages(self):
        if DEBUG>7: print("Get QR code")
        rtn=subprocess.check_output(CMDR + " device zwave-qrcode -d EFR32ZG23 --timeout 1000 --s {}".format(self.wstkser[self.side]),shell=True)
        qr1 = rtn.decode().split('\r')
        qr2=""
        for i in range(len(qr1)): 
            if "QR code" in qr1[i]: 
                qr2=qr1[i]
                break
        qr3 = qr2.split(' ')
        qr4=""
        for i in range(len(qr3)):
            if "90" in qr3[i]:
                qr4=qr3[i]
        if DEBUG>5: print("QR Code={}".format(qr4))
        SmartStartQR.SS_QRGen(qr4)  # convert the QR Code from the DUT into images to be printed

    def LockDebugPort(self):
        ''' Lock the debug port - requires a full device erase to be able to reprogram or debug DUT - See AN1222 for details'''
        rtn=subprocess.check_output(CMDR + " security lock --device EFR32ZG23 --s {}".format(self.wstkser[self.side]),shell=True)
        time.sleep(0.5) # wait for the lock to complete
        rtn=subprocess.check_output(CMDR + " security status --device EFR32ZG23 --s {}".format(self.wstkser[self.side]),shell=True)
        lock=rtn.decode().split('\r')[2]
        if "Enabled" not in lock:
            print("\r\n***FAILED to lock debug port***\r\n{}".format(rtn))  
            return(False)
        if DEBUG>9: print("Debug Port Locked")
        return(True)

    def FactoryFresh(self):
        ''' Clear ALL flash in the DUT to be Factory Fresh and unlock the debug port to allow it to be reprogrammed
            Note that the SE is a one-way upgrade so there is no way to set it back to Factory Fresh
        '''
        rtn=subprocess.check_output(CMDR + " device unlock -d EFR32ZG23 --s {}".format(self.wstkser[self.side]), shell=True) # this also runs a masserase
        if DEBUG>7: print("Unlock=" + rtn.decode())
        rtn=subprocess.check_output(CMDR + " device pageerase --region @userdata -d EFR32ZG23 --s {}".format(self.wstkser[self.side]), shell=True) # erases Z-Wave tokens, crystal cal, etc
        if DEBUG>7: print("UserData=" + rtn.decode())
        if DEBUG>1: print("DUT reset to Factory new")

    def zeb_init(self):
        ''' initialize the Zebra Label Printer '''
        self.zeb = zebra.Zebra()   # create the connection to the label printer
        zqueues = self.zeb.getqueues()
        zp = None
        for zz in zqueues:
            if "ZPL" in zz: zp = zz
        if zp == None:
            raise OSError("Zebra Printer not found") # TODO - on Windows this will never happen since once the printer driver is installed then ZP is ZDesigner ZD411-300dpi
            time.sleep(5)   # TODO want a way to test that the printer is actually connected and ready to print but haven't found one yet...
            sys.exit(1)
        self.zeb.setqueue(zp)

    def zeb_print(self):
        ''' print the labels '''
        l = zpl.Label(25.4*4,12.7*4,12) # 1x0.5" at 300dpi
        l.origin(17,0)
        i=Image.open('qrPack.png')
        if DEBUG>7: print(i.size[0], i.size[1])
        imageHeight = l.write_graphic(i,16)
        l.endorigin()
        self.zeb.output(l.dumpZPL())
        l = zpl.Label(25.4*4,12.7*4,12) # 1x0.5" at 300dpi
        l.origin(14,0)
        i=Image.open('qrProd.png')
        if DEBUG>7: print(i.size[0], i.size[1])
        imageHeight = l.write_graphic(i,22) # 2nd arg is width in mm
        l.endorigin()
        self.zeb.output(l.dumpZPL())

    def usage():
        print("Usage: python ZRADCalProgTest.py LCOM=COMxx RCOM=COMxx LSER=yyyyy RSER=yyyyy")
        print("LCOMxx is the serial COM port to the Left WSTK for use by Railtest")
        print("RCOMxx is the serial COM port to the Right WSTK for use by Railtest")
        print("LSER=yyyyyy is the serial number of the Left WSTK needed by Commander")
        print("RSER=yyyyyy is the serial number of the Right WSTK needed by Commander")
        print("Zebra Printer must be connected and powered on")
        print("TinySA Spectrum Analyzer must be connected and powered on")
        print("TinySA power button is a small slide switch on the side opposite the USB cable")
        device_list = serial.tools.list_ports.comports()
        for device in device_list:  # print the COM ports for the necessary devices
            print(device)
            if device.vid == WSTK_VID and device.pid == WSTK_PID:
                print("WSTK COM Port={}".format(device.device))
            if device.vid == 0x0483 and device.pid == 0x5740:
                print("TinySA COM Port={}".format(device.device))
        rtn=subprocess.check_output("C:/SiliconLabs/SimplicityStudio/v5/developer/adapter_packs/commander/commander.exe --version",shell=True)
        rtnsplit = rtn.decode().split('\r\n')
        for i in rtnsplit:
            if "SN=" in i: print(i)  # print the serial number of any connected WSTK ProKits
        print("")
        print("Commands:")
        print(" x=exit - statistics will be printed (not yet)")
        print(" <enter>=test the DUT in jig listed")
        print(" l=test the LEFT DUT")
        print(" r=test the RIGHT DUT")
        print(" F=Clear DUT flash to be Factory Fresh")
        print(" S=Program Secure Engine")
        print(" C=Run Crystal Calibration")
        print(" A=Program application")
        print(" t=Run the functional test")
        print(" Q=Generate QR Code Labels")
        print(" P=Print Labels of the last DUT")
        print(" Z=Toggle label printing On/Off")
        print(" ?=Print this help message")
        print("")

if __name__ == "__main__":
    ''' This program is typically run as a command line program in a windows PowerShell or Linux bash shell '''

    wstk=ZRADCalProgTest() # create the connection to both WSTKs

    zeb=wstk.zeb_init()

    if DEBUG>1: print("Begin Programming & Testing & QR Code Label Printing")

    cmd = ''
    wstk.side = 0
    DUT_side = ['LEFT', 'RIGHT']
    DUT_arrow = ['<', '>']
    starttime = time.time()
    goodUnits=0
    testedUnits=0
    while not ('x' in cmd):
        #wstk.closewcom    # close the port just in case it was left open
        print("Ready to test {}".format(DUT_side[wstk.side]),end="") 
        cmd=input(DUT_arrow[wstk.side])
        if len(cmd) == 0: # just pressed enter so test the DUT and switch at the end
            testedUnits +=1
            dutstarttime = time.time()
            print("Testing {}".format(DUT_side[wstk.side]), flush=True)

            good = wstk.ProgramSecureEngine() # 1) check SE and update if needed
            if not good:  # SE programming failed so skip the rest - typically re-seat or replace the DUT
                continue

            good = wstk.CalibrateCrystal() # 2) Check Crystal calibration and calibrate if needed
            if not good:
                continue

            good = wstk.FlashApplication() # 3) Flash the application, bootloader and keys
            if not good:
                continue

            good = wstk.QuickFunctionalTest() # 4) Quick Functional Test
            if not good:
                continue

            wstk.CreateQRImages()       # 5) generate the QR Code images

            if not SKIP_PRINTING:
                wstk.zeb_print()        # 6) print the labels

            good = wstk.LockDebugPort() # 7) Lock the debug port
            if not good:
                continue

            print("\n\r\n\r{} DUT PASSED {}{}{} in {} seconds\n\r".format(DUT_side[wstk.side],DUT_arrow[wstk.side],DUT_arrow[wstk.side],DUT_arrow[wstk.side],round(time.time()-dutstarttime,0)))

            goodUnits +=1
            if wstk.wstk[1] != None: wstk.side += 1 # only switch sides if there are 2 Jigs
            if wstk.side>1: 
                wstk.side=0
        elif 'l' in cmd:
            wstk.side=0
        elif 'r' in cmd:
            wstk.side=1
        elif 'F' in cmd:
            wstk.FactoryFresh()
        elif 'S' in cmd:
            wstk.ProgramSecureEngine()
        elif 'C' in cmd:
            wstk.CalibrateCrystal()
        elif 'A' in cmd:
            wstk.FlashApplication()
        elif 't' in cmd:
            wstk.QuickFunctionalTest()
        elif 'Q' in cmd:
            wstk.CreateQRImages() 
        elif 'P' in cmd:
            wstk.zeb_print()
        elif 'L' in cmd:
            wstk.LockDebugPort()
        elif 'Z' in cmd:
            if SKIP_PRINTING: SKIP_PRINTING=False
            else: SKIP_PRINTING=True
            print("SKIP_PRINTING=",SKIP_PRINTING)
        elif 'x' in cmd:
            pass
        else:
            ZRADCalProgTest.usage()

    if testedUnits>1:
        print("Programming/testing for {} minutes. Total DUTs={}, Good DUTs={} {}%".format(round((time.time()-starttime)/60,0),testedUnits,goodUnits, int(round(100*(goodUnits/testedUnits),0))))
    time.sleep(1)
    exit()
