// Z-Wave Geographic Location Command Class range test sample code
// This javascript runs under Z-Wave JS and Node.js which will poll a DUT
// every 10s for it's GeoLoc coordinates and write them to a file.
//
const { Driver, CommandClass } = require("zwave-js");
const { CommandClasses, RFRegion } = require("@zwave-js/core");

const path = require("node:path");
const { setTimeout } = require("node:timers/promises");

const fs = require("node:fs/promises"); // data file to send coordinates to

process.on("unhandledRejection", (r) => {
  debugger;
  throw r;
});

/////////////////// REQUIRED CUSTOMIZATION ///////////////////////////////////
// UPDATE THE PORT name to the one currently connected
const port =
  "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_1a4581bf3c1fee1183758157024206e6-if00-port0";
// Then update the keys as needed - extract them from Z-Wave JS UI.

const DUTNodeID = 257; // UPDATE the NodeID for the Device Under Test here

const SecondsPerSample = 3; // UPDATE this with the desired time (in seconds) between samples - (1-100)

// Replace the securityKeys below if desired...
/////////////////////////////////////////////////////////////////////////////

const driver = new Driver(port, {
  // logConfig: {
  // 	logToFile: true,
  // 	forceConsole: true,
  // },
  securityKeys: {
    S0_Legacy: Buffer.from("5DD5A19627FB9972B4AA32F7F94FD3B8", "hex"),
    S2_Unauthenticated: Buffer.from(
      "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
      "hex",
    ),
    S2_Authenticated: Buffer.from(
      "02B64AC2AF397AF692EDF7CFD4175236",
      "hex",
    ),
    S2_AccessControl: Buffer.from(
      "C6FDA8C1F65601DB868B2194F76324DF",
      "hex",
    ),
  },
  securityKeysLongRange: {
    S2_Authenticated: Buffer.from(
      "A99662FA524F4EE7890EFDCDBF80C703",
      "hex",
    ),
    S2_AccessControl: Buffer.from(
      "E3CE27F99226818C41CA629D9BEB336D",
      "hex",
    ),
  },
  rf: {
    // Set the RF region to US_LR on startup
    region: RFRegion["USA (Long Range)"],
    // Configure TX Power and LR Powerlevel if desired
    txPower: {
      powerlevel: -1,
      measured0dBm: 0,
    },
    maxLongRangePowerlevel: 20,
  },
  storage: {
    cacheDir: path.join(__dirname, "cache"),
    lockDir: path.join(__dirname, "cache/locks"),
  },
  allowBootloaderOnly: true,
})
  .on("error", console.error)
  .once("driver ready", async () => {
    const start = new Date();
    await fs.appendFile(
      "geoloc.csv",
      `Time, Latitude, Longitude, Altitude, TxPower, RSSI, ${start}\n`,
    );

    let txpower = 0;
    let rssi = 0;
    const node = driver.controller.nodes.get(DUTNodeID);

    while (true) {
      // Create a custom command with raw payload
      const cc = new CommandClass(driver, {
        nodeId: DUTNodeID,
        ccId: CommandClasses["Geographic Location"],
        ccCommand: 0x02, // Get
      });

      // Set up a listener for the response, returning null if it times out
      const response = driver
        .waitForCommand(
          (cc) =>
            cc.ccId === CommandClasses["Geographic Location"]
            && cc.ccCommand === 0x03,
          5000,
        )
        .catch(() => null);

      try { // ignore errors on a NACK
        // Send the command
        await driver.sendCommand(cc, {
          // Extract the TX Power and RSSI from the TX Report when it is received
          onTXReport: (report) => {
            // The values behind ?? are used in case the info is not present in the report
            txpower = report.txPower ?? 0;
            rssi = report.ackRSSI ?? 0;
          },
        });
      } catch (error) {
        console.log("NACK");
        await setTimeout(SecondsPerSample * 1000); // wait
        continue;
      }

      // Extract the payload of the command if it was received
      const payload = (await response)?.payload;
      if (payload) {
        // convert payload into .csv file coordinates
        const lon = payload.readInt32BE(0) / (1 << 23); // convert the fixed point value to floating point - the decimal point is bit 23
        const lat = payload.readInt32BE(4) / (1 << 23);
        const alt = payload.readIntBE(8, 3) / 100; // reading is in centimeters but most tools want meters
        const now = new Date();
        const time = now.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
        const stat = payload[11];

        if (0x07 == (stat & 0x07)) { // ignore the reading if the GPS coordinates are not valid
          await fs.appendFile(
            "geoloc.csv",
            `${time}, ${lat}, ${lon}, ${alt}, ${txpower}, ${rssi}\n`,
          ); // write coords to the csv file
        }

        console.log("Lat=", lat, "Lon=", lon, "alt=", alt, "Sats=", stat>>4, "TxPower=",txpower);
      }

      await setTimeout(SecondsPerSample * 1000 / 2); // wait
/*
      // send an indicator to blink three times for a visual indicator that the DUT is still in range
      try {
        await node.commandClasses.Indicator.set([
          {
            indicatorId: 0x50,
            propertyId: 0x03,
            value: 2,
          },
          {
            indicatorId: 0x50,
            propertyId: 0x04,
            value: 3,
          },
        ]);
      } catch (error) {
        console.log("NACK");
      }

      // Wait before sending the next command
      await setTimeout(SecondsPerSample * 1000 / 2);
*/
    }
  });

void driver.start();

// Destroy the driver instance when the application gets a SIGINT or SIGTERM signal
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, async () => {
    await driver.destroy();
    process.exit(0);
  });
}
