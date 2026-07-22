# Salt Sensor — Perfboard Layout

## Overview

Transfer of the salt-sensor circuit from its current rewired-breadboard state (CARD-0049, follow-on to CARD-0004's ESPHome migration) to a permanent perfboard build. Much simpler than hiking-monitor's perfboard: no I2C sensors, no battery/TP4056/voltage-divider power chain, no display — just an ESP32 DevKitC-32, three status LEDs, and one JSN-SR04T ultrasonic distance sensor, powered by a 5V USB wall charger. GPIO assignments: Red LED GPIO32, Yellow LED GPIO33, Green LED GPIO27, JSN-SR04T Trig GPIO5, Echo GPIO18 (via divider) — see **Board Note** below before trusting any physical pin-position references.

**STATUS: COMPLETE (2026-07-13).** Perfboard soldered, all Pre-Power Checks passed, power-on test passed, two clean cold power-cycles confirmed. CARD-0049 closed.

## Board Note — read before touching a multimeter or iron

The physical ESP32 board actually used for this perfboard build is a **SparkleIoT XH-32S** module. Its silkscreen prints GPIO labels directly (`D32`, `D33`, `D27`, `D5`, `D18`, `VIN`, `GND`, etc.) — but its physical pin *order* does **not** match the position numbering in `ESP32-project-pins.md` (that table assumes a different reference board's layout). **Identify every pin by its printed label, not by a position number.** This is not a hypothetical risk — it caused a real mistake during this build: the Trig wire was soldered to the pad labeled `RX2` instead of `D5` (the two sit right next to each other in a crowded cluster — `D18, D5, TX2, RX2, D4`), and only got caught during Pre-Power Checks by reading the actual pad labels, not by trusting a documented position table. `ESP32-project-pins.md` has since been corrected (2026-07-13) to match this actual board, organized by printed label rather than position number — it's now safe to rely on.

Reference photo of the actual board's silkscreen: `sparkleiot-xh-32s-pinout-photo.jpg` (same directory).

## Board Selection

5×7cm Chanzon FR4 perfboard — the JCTsh default for ESP32 DevKit projects (`JCTsh-Build-Standards.md` §1.2). This circuit is small enough that board size isn't a tight constraint.

## Component Placement

- ESP32 DevKitC-32 (SparkleIoT XH-32S) centered, socketed into two 19-pin female header strips (not soldered directly — removable for rework/reuse, per standard).
- All three LEDs positioned near the `D32`/`D33`/`D27` pads (all on the same physical column on this board) — keeps LED wiring short and groups them for easy visual inspection/reflash access.
- Ground bus laid along one edge of the board (see Assembly Sequence step 3) — physically nearest the components with the most GND taps (the three LEDs) to keep those return wires short.
- JSN-SR04T connector header placed at a board edge for clean cable exit toward the sensor's mounted position.
- 220Ω LED resistors placed in-line, adjacent to each LED position. Echo divider (1kΩ + 2kΩ) placed near the JSN-SR04T connector header.

## Wiring Connections

### Power

| Net | From | To | Bus? |
|---|---|---|---|
| VIN (5V) | ESP32's own onboard USB port | ESP32 `VIN` pad (internal to the module) | — |
| VIN (5V) | `VIN` | JSN-SR04T VCC pad | No — single consumer, direct point-to-point wire (see Assembly Sequence step 4) |

### Ground

| Net | From | To |
|---|---|---|
| GND | ESP32 `GND` pad | Ground bus |
| GND | Ground bus | Red LED resistor return |
| GND | Ground bus | Yellow LED resistor return |
| GND | Ground bus | Green LED resistor return |
| GND | Ground bus | JSN-SR04T GND pad |
| GND | Ground bus | Echo divider bottom leg (2kΩ) |
| GND | Ground bus | *(2 spare tap points, unused)* |

### LED Drive Lines (each point-to-point, no bus)

| LED | GPIO pad | Resistor |
|---|---|---|
| Red | `D32` | 220Ω |
| Yellow | `D33` | 220Ω |
| Green | `D27` | 220Ω |

### JSN-SR04T (Trig/Echo each point-to-point, no bus)

| Signal | From | To |
|---|---|---|
| Trig | `D5` | Sensor Trig pad, direct — **not `RX2`, see Board Note** |
| Echo | Sensor Echo pad | 1kΩ (top leg) |
| Echo | 1kΩ/2kΩ midpoint | `D18` |
| Echo | 2kΩ (bottom leg) | Ground bus |

## Assembly Sequence

1. **Mark ESP32 header positions** on bare perfboard, verify pin spacing against the actual board before soldering anything.

2. **Solder left header strip** (19-pin female). Test-fit ESP32, mark the right header position from actual pin position (don't assume). Remove ESP32, solder right header strip, confirm flat seat with no pin misalignment.

3. **Solder the ground bus.** *Warranted* — GND is the highest fan-out net on this board: ESP32's own GND, all three LED returns (each through its 220Ω resistor), JSN-SR04T GND, and the bottom leg of the Echo divider (2kΩ→GND) — 5 consumers converging on one net. Solder a dedicated bus row/strip fed by a single jumper from the ESP32's `GND` pad, with **2 spare tap points** beyond the 5 known consumers for future additions. Do this early — it's infrastructure everything else hangs off of.

4. **Power (5V/VIN) — no bus.** *Not warranted* — only one consumer beyond the source itself (JSN-SR04T VCC; the ESP32 is the source via `VIN`). A bus implies 3+ consumers tapping a shared rail; with just one, a single point-to-point wire from `VIN` to the sensor's VCC pin is equivalent and simpler.

5. **Solder other buses. None warranted in this case.** Every remaining net — each LED's GPIO drive line (`D32`/`D33`/`D27`→resistor→LED), Trig (`D5`→sensor), and Echo (sensor→divider→`D18`) — is single-consumer point-to-point. No net besides GND has 3+ consumers. Recorded explicitly so this is a deliberate pass, not an assumption skipped on a future revision.

6. **Solder LED positions** with 220Ω resistors in-line — Red (`D32`), Yellow (`D33`), Green (`D27`). Tie each resistor's return leg into the ground bus from step 3.

7. **Solder the JSN-SR04T connector header** — VCC to the `VIN` wire (step 4), GND to the ground bus (step 3), Trig and Echo pads for the next two steps.

8. **Solder the Echo voltage divider** (1kΩ + 2kΩ) — top leg from sensor Echo output, midpoint to `D18`, bottom leg to the ground bus (step 3).

9. **Solder the Trig line** — direct point-to-point wire, `D5` to sensor Trig pin. **Double-check against the printed label** — `D5` sits in a crowded cluster next to `TX2`/`RX2`, which is exactly where this build's real wiring mistake happened.

10. **No separate power-in header on this board.** Power comes through the ESP32 module's own onboard USB port, which internally feeds `VIN` — nothing to solder here. (Left as its own numbered step, rather than renumbering everything after it, so this note doesn't get lost.)

11. **Seat ESP32 and JSN-SR04T** into their headers, confirming the ESP32's onboard USB port has clear physical access — it's now doing double duty as both the flashing port and the permanent power connector.

12. **Power-on test** — connect USB wall charger, confirm LED self-test, WiFi/MQTT connect, `/data` and `/status` reporting normally.

---

## Pre-Power Checks

**STATUS: COMPLETE (2026-07-13). All 19 checks passed.** Real issue found and fixed during this pass: Trig was soldered to `RX2` instead of `D5` (see Board Note) — caught here, before power-on, by reading pad labels directly rather than trusting position numbers. Checks 2–3 from the original hiking-monitor-derived template (verifying a separate USB power-in header) were dropped as not applicable — this board has no such header, power enters through the ESP32's own onboard USB port. Checks 17–19 were added during this build, not part of the original template — isolation checks between visually-adjacent pin labels, prompted directly by the `RX2`/`D5` mistake.

**Do the short circuit check first.** A VIN–GND short will damage the ESP32 on first power-up.

### Short Circuit

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 1 | `VIN` | `GND` | Resistance | >100kΩ (OL is the best possible result — a real board never reads pure open due to onboard regulator/USB-chip bias paths, but the check is a floor, not a target) | OL — PASS |

### Power Path

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 2 | `VIN` | JSN-SR04T VCC pad | Continuity | Beep | Beep — PASS |

### Ground Bus

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 3 | `GND` | Ground bus | Continuity | Beep | Beep — PASS |
| 4 | Ground bus | Red LED resistor return leg | Continuity | Beep | Beep — PASS |
| 5 | Ground bus | Yellow LED resistor return leg | Continuity | Beep | Beep — PASS |
| 6 | Ground bus | Green LED resistor return leg | Continuity | Beep | Beep — PASS |
| 7 | Ground bus | JSN-SR04T GND pad | Continuity | Beep | Beep — PASS |
| 8 | Ground bus | Echo divider bottom leg (2kΩ) | Continuity | Beep | Beep — PASS |

### LED Circuits

*If continuity (beep) mode doesn't register through an unlit LED, switch to diode-test mode — some multimeters' continuity threshold voltage is too low to forward-bias an LED. A diode-test reading well below a typical LED's rated forward voltage (1.8V+) is normal and still a pass — the meter's small test current, further reduced by the 220Ω series resistor, doesn't fully forward-bias the LED the way the ESP32's actual 3.3V GPIO drive will at power-on. What matters here is a real, non-zero, non-infinite reading.*

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 9 | `D32` | Ground bus | Continuity/Diode | Beep or forward-voltage reading, through 220Ω + Red LED | 0.486V (diode) — PASS |
| 10 | `D33` | Ground bus | Continuity/Diode | Beep or forward-voltage reading, through 220Ω + Yellow LED | 0.61V (diode) — PASS |
| 11 | `D27` | Ground bus | Continuity/Diode | Beep or forward-voltage reading, through 220Ω + Green LED | 0.486V (diode) — PASS |

### Echo Divider (1kΩ + 2kΩ)

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 12 | JSN-SR04T Echo pad | 1kΩ top leg | Continuity | Beep | Beep — PASS |
| 13 | 1kΩ/2kΩ midpoint | `D18` | Continuity | Beep | Beep — PASS |
| 14 | JSN-SR04T Echo pad | Ground bus (through full divider) | Resistance | ~3kΩ (1kΩ + 2kΩ in series) | 2.92kΩ — PASS |
| 15 | 1kΩ/2kΩ midpoint | Ground bus | Resistance | ~2kΩ (2kΩ only) | 1.93kΩ — PASS |

### Trig Line

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 16 | `D5` (corrected — not `RX2`) | JSN-SR04T Trig pad | Continuity | Beep | Beep — PASS |

### Adjacent-Pin Isolation (added during this build)

Prompted by the `RX2`/`D5` mix-up — this board's dense silkscreen means visually-adjacent labels are a real mistake risk, not just a theoretical one. These checks confirm no solder bridge exists between pins that sit close together but must remain electrically isolated.

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 17 | `D32` | `D33` | Continuity/Resistance | OL / open — no beep. A bridge here would put two ESP32 GPIO outputs in direct conflict. | No beep — PASS |
| 18 | `D5` | `D18` | Continuity/Resistance | OL / open — no beep. Adjacent in the same crowded cluster that caused the original mistake. | No beep — PASS |
| 19 | `D5` | `RX2` | Continuity/Resistance | OL / open — no beep. Confirms no residual bridge or leftover trace after moving the wire off `RX2`. | No beep — PASS |

---

## Reboot / Power-Cycle Verification

**STATUS: COMPLETE (2026-07-13). Two clean cold power-cycles confirmed.**

Salt-sensor is USB/wall-powered, not battery-powered — a **cold power-cycle** (physically unplug and replug the USB wall charger) is the meaningful test here, not just an OTA-triggered soft reboot. A warm reboot doesn't exercise WiFi association from scratch, MQTT re-auth, or the LED self-test's cold-boot path the way a real power interruption does.

**Cycle 1 (15:06 MST):** USB unplugged, replugged. LED self-test observed. Log dashboard: `Online — ESPHome 2026.4.5, IP: 192.168.1.181, MQTT connected` followed immediately by `Salt: 95% (21.5 cm)`. Clean.

**Cycle 2 (15:08 MST):** Repeated. Same result — LED self-test, MQTT reconnect, `Salt: 95% (21.5 cm)`. Clean.

No GPIO32/33/27 boot-time glitching observed on either cycle (expected, since none of these are strapping pins — confirmed empirically anyway since this was the first real power-cycle on the new pin assignment). Both readings matched the same value (95%, 21.5cm) referenced in CARD-0049's original 2026-07-10 breadboard field verification — the Trig/Echo circuit (including the divider fixed during this build) is producing consistent, sane measurements.

## Notes

- **Do not solder ESP32 directly to perfboard** — female headers allow removal for rework or reuse, matching the standard used on every other JCTsh perfboard build.
- **No 3.3V rail on this board.** Unlike hiking-monitor (which feeds BME280/LTR-390/e-ink from ESP32's 3V3 pin), nothing on salt-sensor needs 3.3V externally — the LEDs are driven directly from GPIO logic level (3.3V, well within the ~12mA a GPIO pin can safely source). This is a deliberate difference from hiking-monitor's design, not an oversight.
- **GPIO25/26 avoided** — GPIO25 (`D25`, DAC1) confirmed broken for digital output in ESPHome/Arduino; GPIO26 (`D26`, DAC2) avoided as a precaution for the same reinit family of issues. See `ESP32-project-pins.md` (corrected).
- **GPIO5 (Trig) is a strapping pin** and logs a startup warning — unchanged from the original wiring, accepted as-is (matches the original breadboard behavior, not a new issue introduced by this transfer).
- **Board-brand pin-order mismatch and the adjacent-label mistake it caused** — see Board Note at the top. Candidate for harvesting into `JCTsh-Build-Standards.md`: always verify against the physical board's silkscreen labels rather than a documented reference table, and add isolation checks between visually-adjacent labels as standard Pre-Power Checks practice, not just intentional-net continuity checks.
