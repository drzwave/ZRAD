# ZRAD Test Folder

This folder contains various test scripts for ZRAD.

See the comments within the script for details.

# New Board Bring Up Procedure

Once a PCB has been fully assembled, use this procedure to ensure it is fully functional.
This is a manual procedure if the test jig system is not available.

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
9. Follow the crystal calibration procedure in the main README.md
10. Update the SE if needed, Flash the Bootloader OTA and a sample application
11. commander device reset (or power cycle the DUT)
12. Extract the DSK and add it to the PCC
    - Print the QR code label to apply to the PCB
11. Test the application by joining a network and observing the RSSI on Zniffer
11. Send basic on/off which should toggle the green LED
11. Press the LEARN button which should send a NIF and blink the blue LED
12. Unplug from WSTK
13. Plug in via USB and verify the board is functional - LEDs toggle with basic On/Off
14. Open PuTTY and observe the DEBUGPRINT from the sample app
15. Unplug from USB & insert CR123A battery - verify the board is still functional
16. Test other optional features like the QWIIC connector, the GPIOs, LEDs other applications

# Test Jig System

A 3D printed test jig and associated scripts provides a complete manufacturing flow for ZRAD.

MORE TO COME HERE!!!
