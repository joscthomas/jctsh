# Salt Sensor — ESP32 Pin Assignments

**Board:** SparkleIoT XH-32S (ESP32-WROOM, WiFi+BT, 38-pin castellated module on a DevKit-style breakout)
**Orientation:** USB-C connector at bottom, boot/EN buttons at the very bottom edge.

**Corrected 2026-07-13 (CARD-0049):** this table previously used a generic "ESP32 DevKitC-32" position-numbered layout (pin 1–38, counted top-to-bottom-then-up) that turned out **not to match** the actual physical board used for this component's perfboard build. That mismatch caused a real wiring mistake — Trig was soldered to the pin labeled `RX2` instead of `D5`, only caught during Pre-Power Checks. This table is now built directly from the actual board's silkscreen (photo: `sparkleiot-xh-32s-pinout-photo.jpg`, same directory), organized by **printed label**, not position number. Per `JCTsh-Build-Standards.md` §1.2: always verify against the physical board in hand — even this corrected table is only guaranteed accurate for *this* board model.

## Left Column (top to bottom)

| Printed label | GPIO / function | Notes |
|---|---|---|
| `EN` | Reset/Enable | — |
| `VN` | GPIO39 | Input-only (ADC1_CH3) |
| `D34` | GPIO34 | Input-only |
| `D35` | GPIO35 | Input-only |
| `D32` | GPIO32 | **Red LED (critical), 220Ω** |
| `D33` | GPIO33 | **Yellow LED (warning), 220Ω** |
| `D25` | GPIO25 ⛔ | Do not use — DAC1, confirmed broken for digital output |
| `D26` | GPIO26 | Avoided as precaution — DAC2, same reinit family as GPIO25 |
| `D27` | GPIO27 | **Green LED (good), 220Ω** |
| `D14` | GPIO14 | Free |
| `D12` | GPIO12 ⚠️ | Strapping pin — avoid driving at boot |
| `D13` | GPIO13 | Free |
| `SD2` | GPIO9 ⛔ | Flash — do not use |
| `SD3` | GPIO10 ⛔ | Flash — do not use |
| `CMD` | GPIO11 ⛔ | Flash — do not use |
| `GND` | Ground | Ground bus feed point |
| `VIN` | 5V in | Fed internally from the board's own onboard USB port — no separate power-in header on this board |

## Right Column (top to bottom)

| Printed label | GPIO / function | Notes |
|---|---|---|
| `D23` | GPIO23 | Free |
| `D22` | GPIO22 | Free |
| `TX0` | GPIO1 | UART0 TX — used by USB serial/flashing, avoid for other use |
| `RX0` | GPIO3 | UART0 RX — used by USB serial/flashing, avoid for other use |
| `D21` | GPIO21 | Free |
| `D19` | GPIO19 | Free |
| `D18` | GPIO18 | **JSN-SR04T Echo** (via 1kΩ+2kΩ divider) |
| `D5` | GPIO5 ⚠️ | **JSN-SR04T Trig.** Strapping pin, logs a startup warning — unchanged from original wiring, accepted as-is. **Sits directly next to `TX2`/`RX2` — read the label carefully, this is exactly where the CARD-0049 mistake happened.** |
| `TX2` | GPIO17 | UART2 TX — free, but adjacent to `D5`/`RX2`, same mislabel risk |
| `RX2` | GPIO16 | Free — **not used by this design.** This is the pin Trig was mistakenly soldered to during CARD-0049's build; the mistake was caught and corrected to `D5` before power-on. |
| `D4` | GPIO4 | Free — previously used for Green LED before the CARD-0049 pin move to `D27` |
| `D2` | GPIO2 ⚠️ | Strapping pin — previously used for Red LED before the CARD-0049 pin move to `D32` |
| `D15` | GPIO15 ⚠️ | Strapping pin — previously used for Yellow LED before the CARD-0049 pin move to `D33` |
| `D0` | GPIO0 ⚠️ | Strapping pin (BOOT button) — do not drive at boot |
| `SD1` | GPIO8 ⛔ | Flash — do not use |
| `SD0` | GPIO7 ⛔ | Flash — do not use |
| `CLK` | GPIO6 ⛔ | Flash — do not use |
| `3V3` | 3.3V out | Not used externally on this board — no external 3.3V rail needed (see `perfboard-layout.md` Notes) |

⛔ = connected to flash memory — do not use
⚠️ = strapping pin — avoid driving at boot (GPIO5 is used anyway for Trig; accepted, logs a harmless startup warning)

## Current Assignments Summary

| Signal | Label | GPIO |
|---|---|---|
| Red LED | `D32` | GPIO32 |
| Yellow LED | `D33` | GPIO33 |
| Green LED | `D27` | GPIO27 |
| JSN-SR04T Trig | `D5` | GPIO5 |
| JSN-SR04T Echo | `D18` | GPIO18 (via divider) |
| Power in | `VIN` | — (from onboard USB) |
| Ground | `GND` | — |

**History:** For the perfboard build (CARD-0049), Red and Yellow were moved off strapping pins (GPIO2/`D2`, GPIO15/`D15`) and Green off GPIO4/`D4` onto GPIO32/33/27 (`D32`/`D33`/`D27`), so all three LEDs now sit together in the same physical area for easier soldering. GPIO25 (`D25`) was ruled out (confirmed broken for digital output — DAC1, reconfigured post-boot) and GPIO26 (`D26`) was avoided as a precaution (DAC2, same family). GPIO5 (`D5`, Trig) is itself a strapping pin and logs a startup warning, but is unchanged from the original wiring.
