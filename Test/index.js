const { Driver, CommandClass } = require("zwave-js");
const { CommandClasses, RFRegion } = require("@zwave-js/core");

const path = require("node:path");
const { setTimeout } = require("node:timers/promises");

process.on("unhandledRejection", (r) => {
  debugger;
  throw r;
});

const port = "/dev/serial/by-id/usb-Silicon_Labs_CP2102N_USB_to_UART_Bridge_Controller_1a4581bf3c1fee1183758157024206e6-if00-port0";

const driver = new Driver(port, {
  // logConfig: {
  // 	logToFile: true,
  // 	forceConsole: true,
  // },
  securityKeys: {
    S0_Legacy: Buffer.from("5DD5A19627FB9972B4AA32F7F94FD3B8", "hex"),
    S2_Unauthenticated: Buffer.from("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "hex"),
    S2_Authenticated: Buffer.from("02B64AC2AF397AF692EDF7CFD4175236", "hex"),
    S2_AccessControl: Buffer.from("C6FDA8C1F65601DB868B2194F76324DF", "hex"),
  },
  securityKeysLongRange: {
    S2_Authenticated: Buffer.from("A99662FA524F4EE7890EFDCDBF80C703", "hex"),
    S2_AccessControl: Buffer.from("E3CE27F99226818C41CA629D9BEB336D", "hex"),
  },
  rf: {
    // Set the RF region to US_LR on startup
    region: RFRegion["USA (Long Range)"],
    // Configure TX Power and LR Powerlevel if desired
    txPower: {
      powerlevel: -1,
      measured0dBm: 0,
    },
    maxLongRangePowerlevel: 14,
  },
  storage: {
    cacheDir: path.join(__dirname, "cache"),
    lockDir: path.join(__dirname, "cache/locks"),
  },
  allowBootloaderOnly: true,
})
  .on("error", console.error)
  .once("driver ready", async () => {
    while (true) {
      // Create a custom command with raw payload
      const cc = new CommandClass(driver, {
        nodeId: 257,
        ccId: CommandClasses.Indicator,
        ccCommand: 0x02, // Get
        payload: Buffer.from([0x50]),
      });

      // Set up a listener for the response, returning null if it times out
      const response = driver
        .waitForCommand(
          (cc) => cc.ccId === CommandClasses.Indicator && cc.ccCommand === 0x03,
          5000
        )
        .catch(() => null);

      // Send the command
      await driver.sendCommand(cc);

      // And extract the payload of the command if it was received
      const payload = (await response)?.payload;
      if (payload) {
        // Do something with the payload
        console.log("received custom report");
        console.dir(payload, { depth: null });
      }

      // Wait 10 seconds before sending the next command
      await setTimeout(10000);
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
