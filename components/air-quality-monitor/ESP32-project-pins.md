# Air Quality Monitor — ESP32 DevKitC-32 Pin Assignments
**Board:** ESP32 DevKitC-32, 38-pin, CP2102, USB-C
**Orientation:** USB-C connector at bottom. Left pin 1 and right pin 38 are at the top.

**Verify against the actual board's printed silkscreen labels before soldering or probing** — this table is only as good as the specific physical board it was written against (`JCTsh-Build-Standards.md` §1.2).

**Wire colors live in `wiring.md`, not here.** That doc is the authoritative as-built source (kept current against the physical bench build); this file is pin/GPIO assignment only.

**Note:** the three "RGB LED module" rows (pins 30/31/37) are three pins on one single module (KY-016), not three separate LEDs — see `wiring.md`'s RGB LED Wiring section for the full 4-pin mapping and the confirmed no-external-resistor finding.

| Assignment                      | Left pin | Left                          | Right            | Right pin | Assignment                                         |
|----------------------------------|---|-------------------------------|------------------|---|----------------------------------------------------|
| 3.3V rail (Pololu D24V10F3 VOUT — see wiring.md) | 1 | 3V3                           | GND              | 38 | GND rail |
|                                 | 2 | EN                            | GPIO23           | 37 | RGB LED module — `B` pin |
|                                 | 3 | SVP - GPIO36 *(input only)*   | GPIO22           | 36 | SCL (SEN55 via adapter) |
|                                 | 4 | SVN - GPIO39 *(input only)*   | TX - GPIO1 (TXD) | 35 | |
| Battery ADC                     | 5 | GPIO34 *(input only)*         | RX - GPIO3 (RXD) | 34 | |
|                                 | 6 | GPIO35 *(input only, unused)* | GPIO21           | 33 | SDA (SEN55 via adapter) |
| Dock detect (TP4056 IN+)        | 7 | GPIO32                        | GND              | 32 | GND rail |
|                                 | 8 | GPIO33                        | GPIO19           | 31 | RGB LED module — `G` pin |
|                                 | 9 | GPIO25                        | GPIO18           | 30 | RGB LED module — `R` pin |
|                                 | 10 | GPIO26                        | GPIO5            | 29 | |
| Intent switch (CARD-0218 — repurposed SS12D10 slide switch) | 11 | GPIO27                        | GPIO17           | 28 | Debug UART TX (CARD-0205 — reassigned from GPIO27 2026-08-27 when Intent switch claimed that pin; end-to-end log capture confirmed working) |
|                                 | 12 | GPIO14                        | GPIO16           | 27 | |
|                                 | 13 | GPIO12                        | GPIO4            | 26 | |
|                                 | 14 | GND                           | GPIO0 ⚠️         | 25 | |
|                                 | 15 | GPIO13                        | GPIO2 ⚠️         | 24 | |
|                                 | 16 | SD2 - GPIO9 ⛔                 | GPIO15 ⚠️        | 23 | |
|                                 | 17 | SD3 - GPIO10 ⛔                | SD1 - GPIO8 ⛔    | 22 | |
| Silkscreen prints GND, not GPIO11 — but NOT usable as a GND tap, see note below | 18 | GND (nonfunctional — see note) | SD0 - GPIO7 ⛔    | 21 | |
| **Unused — LDO bypasses this pin** | 19 | VIN (5V)                      | CLK - GPIO6 ⛔    | 20 | |

⛔ = connected to flash memory — do not use
⚠️ = strapping pin — avoid driving at boot

**VIN (pin 19) note:** on hiking-monitor, this pin receives the TP4056+boost module's 5V output. On air-quality-monitor, the LDO feeds `3V3` (pin 1) directly instead — `VIN`/pin 19 is intentionally unused. Don't wire anything to it; leaving it floating is correct, not an oversight.

**Pin 18 note — corrected 2026-09-14, see `wiring.md`'s Physical Pin Summary for the full story.** The original 2026-08-19 version of this note claimed pin 18 was "verified against the silkscreen" as GND (vs. hiking-monitor's reference, which has GPIO11 here). The silkscreen print is confirmed still correct — but a bench continuity test during Step 9 found it is **not actually continuous with the GND rail**, reproduced on two separate boards with identical markings. Root cause not yet understood (unpopulated pin on this board variant? genuinely NC despite the print?). **Do not treat pin 18 as a usable GND tap** until this is resolved — see `wiring.md` for the live status.
