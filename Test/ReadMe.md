# ZRAD Test Folder

This folder contains various test scripts for ZRAD/ZRADmini.

The RangeTesting folder has a number of scripts, data and results of RF Range Testing of ZRAD and ZRADmini. See the [ReadMe.md](./RangeTesting/ReadMe.md) for more details.

# New Board Bring Up Procedure

Once a PCB has been fully assembled, use this procedure to ensure it is fully functional.
This is a manual procedure if the test jig system is not available (see below).

1. Connect a WSTK to J3 using a Tag-Connect connector
2. Ensure the WSTK is set to Mini and the power switch is set to AEM
    - WSTK will then power the DUT via the Tag-Connect connector
3. Open Commander and connect to the WSTK
4. Click on Device Info
    - If the debug cable is working, the Chip Type and SE version will be displayed
    - If not, then check the power supplies or look for shorts/opens on the ZG23
5. Click on Flash
6. Select the RailTest file in the software directory and FLASH the DUT
7. Open the Serial 1 console in SSv5 to the WSTK or open PuTTY
8. Press Enter - type "reset" which will print the Railtest version information
9. Follow the crystal calibration procedure in the main [README.md](../README.md)
10. Update the SE if needed using Simplicity Studio, Flash the Bootloader OTA and a sample application
11. commander device reset (or power cycle the DUT)
12. Extract the DSK and add it to the PCC
    - Print the QR code label to apply to the PCB
11. Test the application by joining a network and observing the RSSI on Zniffer
11. Send basic on/off which should toggle the green LED
11. Press the LEARN button which should send a NIF and blink the blue LED
12. Unplug from WSTK
13. Plug in via USB and verify the board is functional - LEDs toggle with basic On/Off
14. Open PuTTY and observe the DEBUGPRINT from the sample app
16. Test other optional features like the QWIIC connector, the GPIOs, LEDs other applications

# Test Jig System

A 3D printed test jig and associated scripts provides a complete manufacturing flow for ZRADmini. 
Typically two jigs are connected to one computer enabling the test operator to load 1 DUT into one jig while the other jig is programming/testing. See the comments within the scripts for additional details on each step of the process.

The following hardware is required to build a ZRADmini Test Sytem:
    - [TinySA](https://www.tinysa.org/wiki/) Spectrum Analyzer
    - Raspberry Pi, keyboard, monitor & mouse
    - Zebra ZD400 label printer and labels
    - 2 3D Printed jigs from the 3D directory above
    - 2 Tag-Connect cables
    - 2 WSTK Silabs Devkit boards
    - 2 clamps
    - Mounting Plate
    - USB Cables and a USB hub

## Manufacturing Flow Scripts

- ZRADCalProgTest.py
    - This is the main script with a command line interface (CLI) that enables the operator to Calibrate, Program and Test each DUT yielding a PASS/FAIL
    - The operator merely presses ENTER, then place a fresh DUT in the other jig while the first one completes programming & testing
    - The CLI has other commands to run individual steps of the manufacturing flow for debugging
    - Note that this script has a minimal number of functional tests and real production should extend the testing for higher confidence in each DUT being fully functional
    - This script then calls the following scripts as needed
- ZG23CrystalCal.py
    - Calibrates the 39MHz crystal utilizing the TinySA spectrum analyzer
    - Relies on the tinySA scripts in the tinySA folder
- TinySA folder
    - Utilities from TinySA to control the Spectrum Analyzer 
- SmartStartQR.py
    - Generates the QR code from the DSK computed by the DUT and optionally prints it on a Zebra printer
    - Requires customization based on the needs of your products labels
    - Prints 2 labels for each DUT
        - Product label must be on the DUT enclosure itself
        - Packaging label is typically applied to the outside packaging
