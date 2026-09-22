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
| Silkscreened GND, but almost certainly GPIO11 (flash CMD) — never use, see note below | 18 | GND (silkscreen) / GPIO11 ⛔   | SD0 - GPIO7 ⛔    | 21 | |
| **Unused — LDO bypasses this pin** | 19 | VIN (5V)                      | CLK - GPIO6 ⛔    | 20 | |

⛔ = connected to flash memory — do not use
⚠️ = strapping pin — avoid driving at boot

**VIN (pin 19) note:** on hiking-monitor, this pin receives the TP4056+boost module's 5V output. On air-quality-monitor, the LDO feeds `3V3` (pin 1) directly instead — `VIN`/pin 19 is intentionally unused. Don't wire anything to it; leaving it floating is correct, not an oversight.

**Pin 18 note — root cause revisited 2026-09-22 (from the porch/patio cluster session, which hit the same anomaly on `back-patio-temp-sensor`); supersedes the 2026-09-14 "root cause not yet understood" version.** History: the original 2026-08-19 note claimed pin 18 was "verified against the silkscreen" as GND. The silkscreen print is confirmed correct — but a bench continuity test during Step 9 (2026-09-14) found pin 18 is **not actually continuous with the GND rail**, reproduced on two separate boards with identical markings.

**Strong hypothesis, not yet directly confirmed: pin 18 is GPIO11 (SD_CMD / flash CMD), mis-silkscreened by the board vendor as GND.** Four pieces of evidence agree:

1. **This component's own board photo** (`esp32_pins.jpg`) shows the underside silkscreen reading `GND` at that position — the print really does say GND, and really does disagree with the chip.
2. **The generic 38-pin ESP32 reference puts GPIO11 / Flash CMD at pin 18.** The 2026-09-14 note framed this as "hiking-monitor's reference," implying some other board's documentation — **that framing was wrong.** `ESP32pins.png` is byte-identical across `hiking-monitor`, `front-porch-temp-sensor`, `garage-radar`, and `back-patio-temp-sensor`: it is the shared generic pinout for this board type, not a hiking-monitor-specific artifact.
3. **The continuity result is exactly what GPIO11 would produce** — not connected to the ground plane because it was never ground. No unpopulated-pin or manufacturing-defect theory is needed to explain it.
4. **Position fits.** Pin 18 sits directly below GPIO9 (SD2, pin 16) and GPIO10 (SD3, pin 17) and above VIN (pin 19) — exactly where GPIO11/SD_CMD completes that flash group in the standard pinout.

**Why this matters more than the old framing:** "nonfunctional GND" implies a merely useless pin. A flash-bus pin is ⛔ — same class as GPIO6–10 — and driving it would interfere with SPI flash access. Treat pin 18 as **never usable for anything**, not as a GND tap whose status is pending.

**Still a hypothesis, deliberately.** Inferred from a reference diagram plus a continuity result; pin 18 itself has never been probed for flash-bus activity. A scope or logic analyzer on it during a flash write would settle it — activity synchronous with the flash bus confirms GPIO11, a flat line does not. Not a blocker: this build never wires pin 18, and GND comes from pin 38 (`wiring.md`'s Physical Pin Summary).

**Same conclusion recorded in `components/back-patio-temp-sensor/ESP32-project-pins.md`** — same board batch, same anomaly, reached independently there 2026-09-21 before the two were connected.

**Cross-cluster edit.** `air-quality-monitor` belongs to the hiking-monitor cluster (`tos/JCTsh-Component-Session-Start.md`); this note was written from the porch/patio session at Joseph's explicit request, not by scope drift.
