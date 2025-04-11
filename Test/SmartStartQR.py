''' Z-Wave SmartStart QRCode generator

Usage: python3 SmartStartQR.py [ASCII characters for the QR code]
output: qrProd.png - Image file to be applied to the product. QRCode+PIN.
        qrPack.png - Image file to be applied to the PACKAGE (box) the product comes in. QRCode+DSK
Typically the image files are then sent to a label printer which are immediate applied to the 
product to ensure the label matches the DUT.

Z-Wave SmartStart QRCode details:
Refer to Silabs document SDS13937-4 "Node Provisioning QR Code Format for more details.
The following is a short version of the important parts of the SS QRCode.

QRCode Version 3 = 31x31 blocks and each block is 4x4 pixels resulting in an 124x124 pixels.
Additional pixels are easily added around the image as well as text for the PIN code or DSK.
Even images such as logos or regulatory marks can be added. In this example the Z-Wave Plus
logo is added to the qrProd.png

The code is 90 decimal digits long. 0-9 are the only allowed characters.
Some fields are only 2 digits. Others are 5 decimal digits which represent two hex bytes.
The LOW (7%) error correction is used to minimize the size of the QRCode.
The QR Type must be "TEXT".

QRCode string definition:
Digits | Value | Description
-------+-------+---------------------------------------------------------------
   2   |   90  | ASCII character 'Z' which identifies this as a Z-Wave QRCode
   2   |   01  | 01 for SmartStart (00 for S2 which is not supported)
   5   | CCCCC | decimal version of the first 2 bytes of the SHA-1 hash of the following data
   3   |  KKK  | Requested keys - bit 7=S0, 2=Access Control, 1=Authenticated, 0=UnAuthen
  40   |  DSK  | Device Specific Key - 16 bytes converted to 8 groups of 5 decimal digits for each pair of bytes.
   2   |  00   | TVL0 = Product Type identifier - must be 0
   2   |  10   | Length of this TVL
   5   | DDDDD | Device Type  (Convert the 2 hex digits into a 5 digit decimal value)
   5   | IIIII | InstallerIcon
   2   |  02   | TLV2 = Product ID
   2   |  20   | Length of this TVL
   5   | MMMMM | Manufacturer ID
   5   | TTTTT | ProductTypeID
   5   | PPPPP | ProductID
   5   | VVVVV | Application Version

Optional data may be added after this for the UUID16 and other fields but these are not currently supported.
'''

# Required Libraries
import sys
import qrcode   # QR Code generating code
import PIL      # image processing operations
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw
from PIL import ImageOps

DEBUG = 1  # higher numbers print more debugging messages

class SmartStartQR():
    ''' SmartStart QR Code generator class'''

    def SS_QRGen(QRin="9001111361314438312478026180785254448443755248313627001008193030790220000120051600002025800803001"):
        ''' Pass in the QR code string extracted from the DUT using Commander:
            C:/SiliconLabs/SimplicityStudio/v5/developer/adapter_packs/commander/commander.exe device zwave-qrcode -d EFR32ZG23 --timeout 1000
            Generates qrProg.png and qrPack.png QR code images which can then be printed on a label printer
            The default QRin above yields:
            90 = leadIn
            01 = version
            11136 = checksum
            131 = req keys
            4438312478026180785254448443755248313627 = DSK (44383=PIN)
            TLV-00 = type=00, len=10, DeviceType=08193, InstallerIconType=03079
            TLV-02 = type=02, len=20, MfgID=00012, ProdType=00516, ProdID=00002, AppVer=02580
        '''    
        # Generate a SmartStart QRCode Image
        qr=qrcode.QRCode(version=3, box_size=4, border=1, error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(QRin)
        qr.make()               # build the QRCode
        img=qr.make_image()     # convert to an image
        if DEBUG>5: print("image size={}".format(img.size))
        (x,y)=img.size          # Typically 124x124
        img2 = img.get_image()  # to pass the checks inside Image.paste, convert the QRcode.PIL image into an Image.Image
        imgProd=Image.new('L', (x+ 180,y+50),255)       # create product greyscale image big enough for the QR and text and Z-Wave Plus Logo
        imgProd.paste(img2,(15,27))     # the X,Y positions may need to be adjusted based on the printer and labels
        imgZWLogo=Image.open("Z-Wave_Plus_Logo.png") # This is optional 
        # other logos, images or text can be included on the label.
        # The final size of the label is managed by the printer drivers for the printer.
        imgProd.paste(imgZWLogo,(145,27))
        img3=ImageDraw.Draw(imgProd)
        font1=ImageFont.truetype('C:/windows/fonts/Verdanab.ttf',18)
        font2=ImageFont.truetype('C:/windows/fonts/Verdanab.ttf',22)
        img3.text((14,10),"Z-WAVE DSK",font=font1, fill=0)
        img3.text((12,143),"PIN:"+QRin[12:17],font=font2, fill=0)
        imgProd.save("qrProd.png")                  # This image goes ON the PRODUCT itself

        imgPack=Image.new('L', (x+100,y+50),255)     # create the package image which has the full DSK in text per Z-Wave Certification
        imgPack.paste(img2,(10,28))
        img3=ImageDraw.Draw(imgPack)
        img3.text((8,10),"Z-WAVE DSK",font=font1, fill=0)
        for i in range(0,8):
            img3.text((x+22,i*17+15),QRin[i*5+12:i*5+17],font=font1, fill=0)
        img3.text((7,146),"PIN:"+QRin[12:17],font=font2, fill=0)
        imgPack.save("qrPack.png")                  # This is the image that goes on the outside of the box

if __name__ == "__main__": # run the script standalone but typically the methods are called from a programming script
    #q=SmartStartQR()
    if len(sys.argv) < 2:
        print("Building a sample QR Code")
        SmartStartQR.SS_QRGen()
    else:
        SmartStartQR.SS_QRGen(sys.argv[1])
    print("QR codes generated - see qrPack.png * qrProd.png")
