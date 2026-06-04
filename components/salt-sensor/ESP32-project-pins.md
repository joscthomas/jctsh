# Salt Sensor — ESP32 DevKitC-32 Pin Assignments
**Board:** ESP32 DevKitC-32, 38-pin, CP2102, USB-C
**Orientation:** USB-C connector at bottom. Left pin 1 and right pin 38 are at the top.

| Assignment | Left pin | Left | Right | Right pin | Assignment |
|---|---|---|---|---|---|
| | 1 | 3V3 | GND | 38 | |
| | 2 | EN | GPIO23 | 37 | |
| | 3 | GPIO36 *(input only)* | GPIO22 | 36 | |
| | 4 | GPIO39 *(input only)* | GPIO1 (TXD) | 35 | |
| | 5 | GPIO34 *(input only)* | GPIO3 (RXD) | 34 | |
| | 6 | GPIO35 *(input only)* | GPIO21 | 33 | |
| | 7 | GPIO32 | GND | 32 | |
| | 8 | GPIO33 | GPIO19 | 31 | |
| | 9 | GPIO25 | GPIO18 | 30 | JSN-SR04T Echo (via 1kΩ+2kΩ divider) |
| | 10 | GPIO26 | GPIO5 | 29 | JSN-SR04T Trig |
| | 11 | GPIO27 | GPIO17 | 28 | |
| | 12 | GPIO14 | GPIO16 | 27 | |
| | 13 | GPIO12 | GPIO4 | 26 | Green LED (good, 220Ω) |
| | 14 | GND | GPIO0 ⚠️ | 25 | |
| | 15 | GPIO13 | GPIO2 ⚠️ | 24 | Red LED (critical, 220Ω) ⚠️ |
| | 16 | GPIO9 ⛔ | GPIO15 ⚠️ | 23 | Yellow LED (warning, 220Ω) ⚠️ |
| | 17 | GPIO10 ⛔ | GPIO8 ⛔ | 22 | |
| | 18 | GPIO11 ⛔ | GPIO7 ⛔ | 21 | |
| | 19 | VIN (5V) | GPIO6 ⛔ | 20 | |

⛔ = connected to flash memory — do not use
⚠️ = strapping pin — avoid driving at boot

**Note:** GPIO2 and GPIO15 are strapping pins used for LEDs. Both are confirmed working in the deployed sketch — not a blocker, but avoid reassigning these pins if the sketch is ever reworked.
