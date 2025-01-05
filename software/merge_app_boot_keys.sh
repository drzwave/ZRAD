# Sample Script to merge the application, bootloader and keys into a single hex file
# Note that this script is ONLY for the End Device version of ZRAD
# If you are making your own product, you MUST regenerate NEW KEYS for your product!!! See the ReadMe.md for details
# ZRAD_ED.s37 is the hex file for the application which is typically a version of Switch On Off sample app
# The bootloader is the standard bootloader from Simplicity Studio specifically for Z-Wave
# The keys are REQUIRED for OTA and must be programmed into each DUT
# Note that the --device ZGM230 is needed to avoid the (could not get base address for region "TOKEN-STORAGE"). The ZG23 and ZGM230 use the same silicon die so the token locations are the same
C:/SiliconLabs/SimplicityStudio/v5/developer/adapter_packs/commander/commander.exe convert ZRAD_ED.s37 bootloader-storage-internal-single-zwave.s37 --tokengroup znet --tokenfile ZRAD_encrypt.key --tokenfile ZRAD_sign.key-tokens.txt --device ZGM230 --outfile ZRAD_ED_merged.s37

