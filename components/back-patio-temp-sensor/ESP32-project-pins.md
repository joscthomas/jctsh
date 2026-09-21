# Back Patio Temp Sensor — ESP32 DevKitC-32 Pin Assignments
**Board:** ESP32 DevKitC-32, 38-pin, CP2102, USB-C — same board type/batch as `air-quality-monitor`'s
**Orientation:** **Viewed from the top** (component side up, antenna at top), USB-C connector at bottom. Left pin 1 and right pin 38 are at the top. This is the working view — `ESP32pins.png` uses it, and it is how the board is actually looked at while wiring and mounting.

**`esp32-pins-photo.jpg` is the *underside*, so its left/right are mirrored against this table (added 2026-09-21).** The silkscreen labels are on the bottom of the board, so a photo of them necessarily shows the reverse: pins 1–19 (3V3, EN, …) appear on the *right* in that photo, and pins 38–20 (GND, GPIO23, GPIO22, …) on the *left*. Use the photo to read what a pad is *labeled*; use this table and `ESP32pins.png` for which side it is on.

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
| **Silkscreened GND, but almost certainly GPIO11 (flash CMD) — never use, see note below** | 18 | GND (silkscreen) / GPIO11 ⛔ | SD0 - GPIO7 ⛔ | 21 | |
| | 19 | VIN (5V) — unused, not wired | GPIO6 ⛔ | 20 | |

⛔ = connected to flash memory — do not use
⚠️ = strapping pin — avoid driving at boot

**Pin 18 note — originally carried over from `components/air-quality-monitor/ESP32-project-pins.md` (found 2026-09-14, reproduced on two separate boards of this same batch); root cause revisited 2026-09-21 against `esp32-pins-photo.jpg` and now has a strong candidate explanation.** The silkscreen prints GND at pin 18, but a bench continuity test found it is **not actually continuous with the GND rail** (pin 38 → pin 18 does not beep).

**Strong hypothesis, not yet directly confirmed: pin 18 is GPIO11 (SD_CMD / flash CMD), mis-silkscreened by the board vendor as GND.** Three independent pieces of evidence agree:
1. `ESP32pins.png` — the generic 38-pin ESP32 reference used by this component (byte-identical copies also sit in `front-porch-temp-sensor/`, `garage-radar/`, and `hiking-monitor/`) — puts **GPIO11 / Flash CMD** at pin 18, not GND.
2. The continuity result is exactly what a GPIO11 pin would produce: it is not connected to the ground plane because it was never ground.
3. The pin sits immediately below GPIO9 (SD2, pin 16) and GPIO10 (SD3, pin 17) and immediately above VIN (pin 19) — the position GPIO11/SD_CMD occupies in the standard pinout, completing that flash group.

**Why this matters more than the earlier "nonfunctional GND" framing:** a dead pin is merely useless, but a flash-bus pin is ⛔ — same class as GPIO6–10. Driving it would interfere with SPI flash access, not just fail to work. Treat pin 18 as **never usable for anything**, not as a GND tap whose status is pending.

**Not directly confirmed, and deliberately recorded as a hypothesis rather than a fact:** this is inferred from a reference diagram plus a continuity result, not from probing pin 18 itself. A scope or logic analyzer on pin 18 during a flash write would settle it outright — activity synchronous with the flash bus confirms GPIO11; a flat line does not. Worth doing opportunistically, not a blocker: this build doesn't use pin 18 for anything, and GND comes from pin 38 (right side, top, next to 3.3V/pin 1) per `wiring.md`.

**Applies to `air-quality-monitor` too, which is where this note originated** — that component's own `ESP32-project-pins.md` and `wiring.md` still record the root cause as unknown, and frame the GPIO11 alternative as "hiking-monitor's reference" rather than the same generic reference. Not updated from here: `air-quality-monitor` belongs to the hiking-monitor cluster (`tos/JCTsh-Component-Session-Start.md`), so that session owns the edit.

**This build's actual pin usage is minimal** — only 3.3V, GND, GPIO21 (SDA), and GPIO22 (SCL) are wired, identical to `front-porch-temp-sensor`'s design. The rest of the table is included for completeness/future reference, same as that component's own pin file.
