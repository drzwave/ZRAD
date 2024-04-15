# ZRAD - Z-Wave Reference Application Design

Z-Wave USB Controller with best-in-class RF range Reference Application Design

More to come here...

# Setup - Simplicity Studio GDSK 4.4.2 (Z-Wave 7.21.2)

This setup guide assumes a ZRAD board has been assembled and is ready for programming.
ZRAD can be programmed as either a Controller or an End Device.
ZRAD uses the Silicon Labs EFR32ZG23A Z-Wave chip as the Z-Wave interface.
The challenge with Simplicity Studio (SSv5) is that since this is a "custom" board, many of the automatic features of SSv5 do not work.
Many aspects of the sample applications must be manually configured.

## Connect ZRAD to Simplicity Studio

1. Plug ZRAD into a WSTK via the Tag-Connect cable
    - ZRAD can be powered directly from the WSTK - ensure the switch next to the battery holder is set to AEM
    - Use a Tag-Connect [TC2050-CLIP](https://www.tag-connect.com/product/tc2050-clip-3pack-retaining-clip) retaining clip to hold the Tag-Connect securely to ZRAD
2. Plug the WSTK into a computer running Simplicity Studio
3. The WSTK should show up in the Debug Adapters pane of the Launcher Perspective
    - if not, click on detect target, if that still doesn't work, use Commander to identify the part part
    - if that still doesn't work, check that the WSTK is set to OUT (or Mini) mode
4. Select the WSTK in the debug adapters pane - SSv5 will then list the board as "custom" are Target Part as the ZG23

## Controller

1. Build the bootloader - 
    - more to come here

## End Device

1. Build the Bootloader
    - File-\>New
2. More to come here
3. Start with the Switch On/Off sample app - optionally use one of the others if applicable
4. File-\>New-\>Silicon Labs Project WizardA
4. Check that IDE/Toochain is set to GNU ARM v12.2.x (and not v10.x.x)
4. Check that the SDK is the latest
4. Next
4. Unselect Solution Examples
4. Select the Z-Wave checkbox
4. Select the Z-Wave SoC Switch On/Off project
4. Next
4. Change the project name to whatever you want
4. Finish - wait for the project to be created
4. Select the project in the Project Explorer of the Simplicity IDE perspective
4. Select the <proj>.slcp file
5. Select the Software Components tab
5. Scroll down to Z-Wave and open it (click on the triangle)
5. Click on Z-Wave Core Component gear icon
5. Change the RF Region to the desired value (United State Long Range)
6. Optionally enable debugprint to get messages out the UART for debugging purposes
    - click on Z-Wave Debug Print
    - click on Install
    - SSv5 should also instal the IO Stream USART but sometimes it does not
        - manually install Services-\>IO Stream-\>IO Stream USART
        - Click on configure
        - Choose USART0, Tx=PA09, RX=PA08
        - Build the project
        - If the build fails because USART is undefined, click on Configure in IO Stream USART
        - Click on View Source
            - if #warning "IO Stream USART peripheral is not configured" is at about line 90, then SSv5 didn't properly configure the USART
            - comment out the #warning line, then manually set the next several lines with the proper GPIO vlues (they are pretty obvious).
    - Edit app.c and uncomment the line: #define DEBUGPRINT
6. Build the project - it should build OK
7. Configure buttons and LEDs
    - The project built so far won't run. It will enter Default\_Handler because LEDs/buttons are not setup
7. Click on the .slcp file and select the Software Components then scroll down to Z-Wave Boards and click on the gear icon
7. Set Button1 On value=Active low, Button2 On Value Active low, Button2 Wake up from EM4 to ON (blue)
7. Scroll down to PB1\_GPIO=PC03, PB2\_GPIO=PC05 and name it LEARN - leave the rest at their defaults
7. Set LED1, LED2 and LED3 ON value = Active Low
7. Set LED1\_GPIO=PA00 name=GREEN, LED2\_GPIO=PA10 name=BLUE, LED3\GPIO=PC04 name=RED
    - Open the source files and check they are configured properly - sometimes SSv5 fails to configure them:
    - radio\_no\_board\_led.c - assign all 3 LEDs in a similar fashion
```
#define LED1_LABEL           "LED0"
#ifndef LED1_GPIO_PORT                          
#define LED1_GPIO_PORT                           gpioPortA
#endif
#ifndef LED1_GPIO_PIN                           
#define LED1_GPIO_PIN                            0
#endif
```
    - radio\_no\_board\_button.c
```
#ifndef PB2_GPIO_PORT                           
#define PB2_GPIO_PORT                            gpioPortC
#endif
#ifndef PB2_GPIO_PIN                            
#define PB2_GPIO_PIN                             5
#endif
```
8. Build and download - press the INCLUDE button should send a Z-Wave NIF and cause the blue LED to blink. Send a BASIC SET ON should turn the green LED on.

# QWIIC Connector Setup

The QWIIC connector on ZRAD makes it easy to connect any of the SparkFun sensors or other devices via a standard I2C interface. 
Fortunately SSv5 is able to add the I2CSPM component which makes adding and interfacing to I2C devices fairly easy.
The QWIIC connector is normally only used when implementing ZRAD as an End Device.

## I2CSPM Setup

1. Click on the .slcp file - select the Software Components tab - enter I2CSPM into the seach bar
2. Click on Platform-\>Driver-\>I2C-\>I2CSPM and Install it
3. Name the component QWIIC
4. Click on Configure
5. Reference clock frequency=0 (default), Speed mode=Fast mode (400kbit/s), Selected Module=I2C0 (or I2C1), SCL=PB00, SDA=PB02
    - Sometimes SSv5 does not properly configure the GPIOs - click on Source
    - Comment out the #warning
    - Uncomment the QWIIC\_PERIPHERAL to be I2C0 (or I2C1)
    - Uncomment the PORT and PIN lines and set them to the correct GPIOs for both SCL and SDA
6. The project should build OK - the I2C peripheral will be automatically initialized
7. The I2CSPM\_Transfer() function is then used to send/receive data over the I2C bus
8. See the Geographic Location Command Class repo for an example using the QWIIC connector

# Directory Structure

- docs - documentation folder
    - Datasheet
    - Technical reference manual and theory of operation
- hardware - PCB board design, bill of materials, Gerbers, KiCAD schematic and layout
- Test - Documents and scripts for testing

# Reference Documents

- See the docs/ZRADTechDocs.docx for detailed technical information on this project

