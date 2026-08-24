# Air Quality Monitor — ESP32 DevKitC-32 Pin Assignments
**Board:** ESP32 DevKitC-32, 38-pin, CP2102, USB-C
**Orientation:** USB-C connector at bottom. Left pin 1 and right pin 38 are at the top.

**Verify against the actual board's printed silkscreen labels before soldering or probing** — this table is only as good as the specific physical board it was written against (`JCTsh-Build-Standards.md` §1.2).

**Note:** the three "RGB LED module" rows (pins 30/31/37) are three pins on one single module (KY-016), not three separate LEDs — see `wiring.md`'s RGB LED Wiring section for the full 4-pin mapping and the confirmed no-external-resistor finding.

| Assignment                      | Left pin | Left                          | Right            | Right pin | Assignment                                         |
|----------------------------------|---|-------------------------------|------------------|---|----------------------------------------------------|
| 3.3V rail (from MCP1700 LDO VOUT, not VIN — see wiring.md) | 1 | 3V3                           | GND              | 38 | GND rail black |
|                                 | 2 | EN                            | GPIO23           | 37 | RGB LED module — `B` pin |
|                                 | 3 | SVP - GPIO36 *(input only)*   | GPIO22           | 36 | SCL (SEN55 via adapter) yellow |
|                                 | 4 | SVN - GPIO39 *(input only)*   | TX - GPIO1 (TXD) | 35 | |
| Battery ADC white               | 5 | GPIO34 *(input only)*         | RX - GPIO3 (RXD) | 34 | |
|                                 | 6 | GPIO35 *(input only, unused)* | GPIO21           | 33 | SDA (SEN55 via adapter) blue |
| Dock detect (TP4056 IN+) green  | 7 | GPIO32                        | GND              | 32 | GND rail |
|                                 | 8 | GPIO33                        | GPIO19           | 31 | RGB LED module — `G` pin |
|                                 | 9 | GPIO25                        | GPIO18           | 30 | RGB LED module — `R` pin |
|                                 | 10 | GPIO26                        | GPIO5            | 29 | |
| Reserved — planned debug UART TX (CARD-0205), not yet wired | 11 | GPIO27                        | GPIO17           | 28 | |
|                                 | 12 | GPIO14                        | GPIO16           | 27 | |
|                                 | 13 | GPIO12                        | GPIO4            | 26 | |
|                                 | 14 | GND                           | GPIO0 ⚠️         | 25 | |
|                                 | 15 | GPIO13                        | GPIO2 ⚠️         | 24 | |
|                                 | 16 | SD2 - GPIO9 ⛔                 | GPIO15 ⚠️        | 23 | |
|                                 | 17 | SD3 - GPIO10 ⛔                | SD1 - GPIO8 ⛔    | 22 | |
| Confirmed GND — not GPIO11 on this board, see note below | 18 | GND                           | SD0 - GPIO7 ⛔    | 21 | |
| **Unused — LDO bypasses this pin** | 19 | VIN (5V)                      | CLK - GPIO6 ⛔    | 20 | |

⛔ = connected to flash memory — do not use
⚠️ = strapping pin — avoid driving at boot

**VIN (pin 19) note:** on hiking-monitor, this pin receives the TP4056+boost module's 5V output. On air-quality-monitor, the LDO feeds `3V3` (pin 1) directly instead — `VIN`/pin 19 is intentionally unused. Don't wire anything to it; leaving it floating is correct, not an oversight.

**Pin 18 note (2026-08-19, real board-variant finding):** this table was originally copied from hiking-monitor's reference, which shows GPIO11 at this position. Verified directly against the actual physical board's silkscreen: the pin immediately next to `VIN`/5V (pin 19) is printed **GND**, not `GPIO11`/`SD_CMD`. This board variant's physical layout genuinely differs from hiking-monitor's at this one position — not a misread. Treat this pin as GND; GPIO11 is not accessible at this physical location on this unit. Doesn't affect this design either way (both GND and GPIO11 were unused here), but flagging it since a table copied from this file for a future build could otherwise propagate the wrong assumption.
