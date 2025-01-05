# ZRAD Software folder

See the top level ReadMe.md for step by step instructions on building firmware for ZRAD.

The Application must be named ZRAD\_ED.s37 for the Test scripts to function properly.
The sample manufacturing flow in the ../Test folder uses the files in this folder to program into each DUT

# KEYS - MAKE YOUR OWN!

Over-The-Air (OTA) firmware updates REQUIRE keys to be programmed into each DUT and MUST be used when building the firmware and generating the gbl file.

The keys pre-built in this folder are SAMPLE KEYS and MUST NOT BE USED on derivative projects! You MUST create your own unique keys for your own products!

## Generating Keys:

1. Run the following commander commands:
2. `commander gbl keygen --type ecc-p256 -o ZRAD_sign.key`
2. `commander gbl keygen --type aes-ccm  -o ZRAD_encrypt.key`
