# Air Quality Monitor — ESP32 DevKitC-32 Pin Assignments
**Board:** ESP32 DevKitC-32, 38-pin, CP2102, USB-C
**Orientation:** USB-C connector at bottom. Left pin 1 and right pin 38 are at the top.

**Verify against the actual board's printed silkscreen labels before soldering or probing** — this table is only as good as the specific physical board it was written against (`JCTsh-Build-Standards.md` §1.2).

| Assignment                      | Left pin | Left | Right | Right pin | Assignment                                         |
|----------------------------------|---|---|---|---|----------------------------------------------------|
| 3.3V rail (from MCP1700 LDO VOUT, not VIN — see wiring.md) | 1 | 3V3 | GND | 38 | GND rail black |
|                                 | 2 | EN | GPIO23 | 37 | Blue (RGB LED) |
|                                 | 3 | GPIO36 *(input only)* | GPIO22 | 36 | SCL (SEN55 via adapter) blue |
|                                 | 4 | GPIO39 *(input only)* | GPIO1 (TXD) | 35 | |
| Battery ADC white               | 5 | GPIO34 *(input only)* | GPIO3 (RXD) | 34 | |
|                                 | 6 | GPIO35 *(input only, unused)* | GPIO21 | 33 | SDA (SEN55 via adapter) yellow |
| Dock detect (TP4056 IN+) green  | 7 | GPIO32 | GND | 32 | GND rail |
|                                 | 8 | GPIO33 | GPIO19 | 31 | Green (RGB LED) |
|                                 | 9 | GPIO25 | GPIO18 | 30 | Red (RGB LED) |
|                                 | 10 | GPIO26 | GPIO5 | 29 | |
| SEN55 power-gate (BC547B base, via 1kΩ) orange | 11 | GPIO27 | GPIO17 | 28 | |
|                                 | 12 | GPIO14 | GPIO16 | 27 | |
|                                 | 13 | GPIO12 | GPIO4 | 26 | |
|                                 | 14 | GND | GPIO0 ⚠️ | 25 | |
|                                 | 15 | GPIO13 | GPIO2 ⚠️ | 24 | |
|                                 | 16 | GPIO9 ⛔ | GPIO15 ⚠️ | 23 | |
|                                 | 17 | GPIO10 ⛔ | GPIO8 ⛔ | 22 | |
|                                 | 18 | GPIO11 ⛔ | GPIO7 ⛔ | 21 | |
| **Unused — LDO bypasses this pin** | 19 | VIN (5V) | GPIO6 ⛔ | 20 | |

⛔ = connected to flash memory — do not use
⚠️ = strapping pin — avoid driving at boot

**VIN (pin 19) note:** on hiking-monitor, this pin receives the TP4056+boost module's 5V output. On air-quality-monitor, the LDO feeds `3V3` (pin 1) directly instead — `VIN`/pin 19 is intentionally unused. Don't wire anything to it; leaving it floating is correct, not an oversight.
