# Back Patio Temp Sensor — ESP32 DevKitC-32 Pin Assignments
**Board:** ESP32 DevKitC-32, 38-pin, CP2102, USB-C — same board type/batch as `air-quality-monitor`'s
**Orientation:** USB-C connector at bottom. Left pin 1 and right pin 38 are at the top.

**Verify against the actual board's printed silkscreen labels before soldering or probing** — this table is only as good as the specific physical board it was written against (`JCTsh-Build-Standards.md` §1.2).

**Wire colors live in `wiring.md`, not here.** That doc is the authoritative as-built source; this file is pin/GPIO assignment only.

| Assignment | Left pin | Left | Right | Right pin | Assignment |
|---|---|---|---|---|---|
| 3.3V rail | 1 | 3V3 | GND | 38 | GND rail — use this pin for GND, not pin 18 (see note below) |
| | 2 | EN | GPIO23 | 37 | |
| | 3 | GPIO36 *(input only)* | GPIO22 | 36 | SCL (BME280, BH1750) |
| | 4 | GPIO39 *(input only)* | GPIO1 (TXD) | 35 | |
| | 5 | GPIO34 *(input only)* | GPIO3 (RXD) | 34 | |
| | 6 | GPIO35 *(input only)* | GPIO21 | 33 | SDA (BME280, BH1750) |
| | 7 | GPIO32 | GND | 32 | |
| | 8 | GPIO33 | GPIO19 | 31 | |
| | 9 | GPIO25 | GPIO18 | 30 | |
| | 10 | GPIO26 | GPIO5 | 29 | |
| | 11 | GPIO27 | GPIO17 | 28 | |
| | 12 | GPIO14 | GPIO16 | 27 | |
| | 13 | GPIO12 | GPIO4 | 26 | |
| | 14 | GND | GPIO0 ⚠️ | 25 | |
| | 15 | GPIO13 | GPIO2 ⚠️ | 24 | |
| | 16 | GPIO9 ⛔ | GPIO15 ⚠️ | 23 | |
| | 17 | GPIO10 ⛔ | GPIO8 ⛔ | 22 | |
| **Not usable as a GND tap despite silkscreen — see note below** | 18 | GND (nonfunctional) | SD0 - GPIO7 ⛔ | 21 | |
| | 19 | VIN (5V) — unused, not wired | GPIO6 ⛔ | 20 | |

⛔ = connected to flash memory — do not use
⚠️ = strapping pin — avoid driving at boot

**Pin 18 note — carried over from `components/air-quality-monitor/ESP32-project-pins.md` (found 2026-09-14, reproduced on two separate boards of this same batch).** The silkscreen prints GND at pin 18, but a bench continuity test found it is **not actually continuous with the GND rail**. Root cause unresolved (unpopulated pin on this board variant? genuinely NC despite the print?). This build doesn't use pin 18 for anything — GND comes from pin 38 (right side, next to the 3.3V/pin 1) per `wiring.md` — but noted here in case any future GPIO expansion on this component is tempted to use it as a convenient GND tap. Don't, until this is independently resolved.

**This build's actual pin usage is minimal** — only 3.3V, GND, GPIO21 (SDA), and GPIO22 (SCL) are wired, identical to `front-porch-temp-sensor`'s design. The rest of the table is included for completeness/future reference, same as that component's own pin file.
