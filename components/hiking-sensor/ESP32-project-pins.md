# Hiking Monitor — ESP32 DevKitC-32 Pin Assignments
**Board:** ESP32 DevKitC-32, 38-pin, CP2102, USB-C
**Orientation:** USB-C connector at bottom. Left pin 1 and right pin 38 are at the top.

| Assignment                      | Left pin | Left | Right | Right pin | Assignment                                         |
|---------------------------------|---|---|---|---|----------------------------------------------------|
| 3.3V rail red                   | 1 | 3V3 | GND | 38 | GND rail black                                     |
|                                 | 2 | EN | GPIO23 | 37 | DIN (e-ink) blue                                   |
|                                 | 3 | GPIO36 *(input only)* | GPIO22 | 36 | SCL (BME280 temp sensor, LTR-390 UV sensor) blue   |
|                                 | 4 | GPIO39 *(input only)* | GPIO1 (TXD) | 35 |                                                    |
|                                 | 5 | GPIO34 *(input only)* | GPIO3 (RXD) | 34 |                                                    |
| ADC (batt voltage)              | 6 | GPIO35 *(input only)* | GPIO21 | 33 | SDA (BME280 temp sensor, LTR-390 UV sensor) yellow |
| Button                          | 7 | GPIO32 | GND | 32 | GND rail                                           |
|                                 | 8 | GPIO33 | GPIO19 | 31 |                                                    |
|                                 | 9 | GPIO25 | GPIO18 | 30 | CLK (e-ink) yellow                                 |
|                                 | 10 | GPIO26 | GPIO5 | 29 | CS (e-ink) orange                                  |
|                                 | 11 | GPIO27 | GPIO17 | 28 | DC (e-ink) green                                   |
|                                 | 12 | GPIO14 | GPIO16 | 27 | RST (e-ink) white                                  |
|                                 | 13 | GPIO12 | GPIO4 | 26 | BUSY (e-ink) purple                                |
|                                 | 14 | GND | GPIO0 ⚠️ | 25 |                                                    |
|                                 | 15 | GPIO13 | GPIO2 ⚠️ | 24 |                                                    |
|                                 | 16 | GPIO9 ⛔ | GPIO15 ⚠️ | 23 |                                                    |
|                                 | 17 | GPIO10 ⛔ | GPIO8 ⛔ | 22 |                                                    |
|                                 | 18 | GPIO11 ⛔ | GPIO7 ⛔ | 21 |                                                    |
| 5V (TP4056 battery charger out) | 19 | VIN (5V) | GPIO6 ⛔ | 20 |                                                    |

⛔ = connected to flash memory — do not use
⚠️ = strapping pin — avoid driving at boot
