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
| Red LED (critical, 220Ω) | 7 | GPIO32 | GND | 32 | |
| Yellow LED (warning, 220Ω) | 8 | GPIO33 | GPIO19 | 31 | |
| GPIO25 — do not use (DAC1, broken for output) | 9 | GPIO25 ⛔ | GPIO18 | 30 | JSN-SR04T Echo (via 1kΩ+2kΩ divider) |
| GPIO26 — avoided as precaution (DAC2) | 10 | GPIO26 | GPIO5 ⚠️ | 29 | JSN-SR04T Trig |
| Green LED (good, 220Ω) | 11 | GPIO27 | GPIO17 | 28 | |
| | 12 | GPIO14 | GPIO16 | 27 | |
| | 13 | GPIO12 ⚠️ | GPIO4 | 26 | *(freed — was Green LED)* |
| | 14 | GND | GPIO0 ⚠️ | 25 | |
| | 15 | GPIO13 | GPIO2 ⚠️ | 24 | *(freed — was Red LED)* |
| | 16 | GPIO9 ⛔ | GPIO15 ⚠️ | 23 | *(freed — was Yellow LED)* |
| | 17 | GPIO10 ⛔ | GPIO8 ⛔ | 22 | |
| | 18 | GPIO11 ⛔ | GPIO7 ⛔ | 21 | |
| | 19 | VIN (5V) | GPIO6 ⛔ | 20 | |

⛔ = connected to flash memory, or confirmed broken for this use — do not use
⚠️ = strapping pin — avoid driving at boot

**Note:** For the perfboard build, Red and Yellow were moved off strapping pins (GPIO2,
GPIO15) and Green off GPIO4 onto GPIO32/33/27, so all three LEDs now sit together on the
left header row (pins 7/8/11). GPIO25 was ruled out (confirmed broken for digital output —
DAC1, reconfigured post-boot) and GPIO26 was avoided as a precaution (DAC2, same family).
GPIO5 (Trig) is itself a strapping pin and logs a startup warning, but is unchanged from
the original wiring.
