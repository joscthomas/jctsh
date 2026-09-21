# Back Patio Temp Sensor — Bench Test Plan (pre-flash)

**Covers the gap between "soldering is done" and `flashing.md`.** Every electrical check
below is derived from `wiring.md`'s connection tables — that doc is the authoritative
as-built wiring source; this one is the runnable worksheet for verifying it.

- **Before this doc:** `perfboard-layout.md` (assembly and soldering sequence)
- **After this doc:** `flashing.md`, then `testing.md` (post-flash, end-to-end)

**Status as of 2026-09-21:** soldering complete; BH1750 (light sensor) confirmed wired
correctly on a 5-pin header (VCC, GND, SCL, SDA, ADDR).

---

## The nine connections being verified

Straight from `wiring.md`. Everything in Sections 2–4 tests one of these, or the absence
of something that should not exist.

| # | From | To | Wire |
|---|---|---|---|
| 1 | BME280 (temp/humidity/pressure sensor) VCC | 3V3, pin 1 | Red |
| 2 | BME280 GND | GND, pin 38 | Black |
| 3 | BME280 SDA | GPIO21, pin 33 | Blue |
| 4 | BME280 SCL | GPIO22, pin 36 | Yellow |
| 5 | BH1750 (light sensor) VCC | 3V3, pin 1 | Red |
| 6 | BH1750 GND | GND, pin 38 | Black |
| 7 | BH1750 SDA | GPIO21, pin 33 | Blue |
| 8 | BH1750 SCL | GPIO22, pin 36 | Yellow |
| 9 | BH1750 ADDR | GND, pin 38 | Black |

ESP32 pin numbers per `ESP32-project-pins.md`: **viewed from the top**, component side up,
USB-C at the bottom, left pin 1 and right pin 38 at the top.

---

## Section 0 — Setup

- [ ] **Nothing inserted.** No ESP32 DevKitC-32 (microcontroller), no BME280, no BH1750.
      Sections 1–6 test the bare perfboard and its bridges only.
- [ ] Multimeter in continuity mode (audible beep).
- [ ] **Zero the meter:** touch probes together. Confirm it beeps and reads near 0 Ω.
      Record lead resistance: ______ Ω (typically 0.2–1.5). A good joint reads within
      about 1 Ω of this. If it does not beep probe-to-probe, nothing below is meaningful.
- [ ] Spare male header pins or solid-core wire offcuts on hand for probing sockets.

**Probing technique.** Female header sockets are recessed; a probe tip reads open on a
perfectly good joint. Drop a male pin into each socket and probe that. **Probe the socket,
not the solder blob on the back** — a cold joint reads fine from the back and open from
the front, and the front is the side the module actually contacts.

---

## Section 1 — Visual inspection

From `wiring.md`'s Pre-Flash Checklist. Do this before touching the meter; some faults are
faster to see than to measure.

- [ ] BME280 VCC → 3V3, pin 1 — **red** wire (not VIN, pin 19)
- [ ] BME280 GND → GND, pin 38 — **black**
- [ ] BME280 SDA → GPIO21, pin 33 — **blue**
- [ ] BME280 SCL → GPIO22, pin 36 — **yellow**
- [ ] BH1750 VCC → 3V3, pin 1 — **red**
- [ ] BH1750 GND → GND, pin 38 — **black**
- [ ] BH1750 SDA → GPIO21, pin 33 — **blue** (same rail as BME280 SDA)
- [ ] BH1750 SCL → GPIO22, pin 36 — **yellow** (same rail as BME280 SCL)
- [ ] BH1750 ADDR → GND, pin 38 — **black**
- [ ] No bare wire touching adjacent rows or pads
- [ ] **Nothing wired to pin 18** (non-functional as GND on this board batch, and almost
      certainly GPIO11/flash CMD — see `ESP32-project-pins.md`)
- [ ] No solder splash or whisker bridging neighbouring pads
- [ ] All joints shiny and concave — not dull grey blobs (cold joint) or balls sitting on
      top of the pad (no wetting)

---

## Section 2 — Power-rail isolation · DO FIRST

A 3.3V-to-GND short is the one defect that can damage the ESP32 DevKitC-32
(microcontroller) the instant USB is connected.

| Check | Expected | Result |
|---|---|---|
| 3V3 (pin 1) → GND (pin 38) | **No continuity** | |
| BME280 VCC socket → BME280 GND socket | **No continuity** | |
| BH1750 VCC socket → BH1750 GND socket | **No continuity** | |

> **Any beep here stops the build.** Clear the short before going further — do not
> continue to Section 3 "just to see."

---

## Section 3 — Continuity · should connect

| Check | Expected | Result |
|---|---|---|
| 1. BME280 VCC socket → 3V3 (pin 1) | Continuity | |
| 2. BME280 GND socket → GND (pin 38) | Continuity | |
| 3. BME280 SDA socket → GPIO21 (pin 33) | Continuity | |
| 4. BME280 SCL socket → GPIO22 (pin 36) | Continuity | |
| 5. BH1750 VCC socket → 3V3 (pin 1) | Continuity | |
| 6. BH1750 GND socket → GND (pin 38) | Continuity | |
| 7. BH1750 SDA socket → GPIO21 (pin 33) | Continuity | |
| 8. BH1750 SCL socket → GPIO22 (pin 36) | Continuity | |
| 9. BH1750 ADDR socket → GND (pin 38) | Continuity | |
| R1. BME280 SDA socket → BH1750 SDA socket | Continuity — shared rail intact | |
| R2. BME280 SCL socket → BH1750 SCL socket | Continuity — shared rail intact | |

**R1/R2 are not redundant.** Both sensors reach GPIO21/GPIO22 through one shared rail
(`wiring.md`). A break *between the two sensors* can still let checks 3/4/7/8 pass
individually while the bus is actually broken.

---

## Section 4 — Isolation · should NOT connect

| Check | Expected | Result |
|---|---|---|
| SDA rail → SCL rail | **No continuity** | |
| SDA rail → GND (pin 38) | **No continuity** | |
| SCL rail → GND (pin 38) | **No continuity** | |
| SDA rail → 3V3 (pin 1) | **No continuity** | |
| SCL rail → 3V3 (pin 1) | **No continuity** | |

SDA or SCL shorted to GND is the classic "sensor never appears on the bus" fault. Once
powered it is indistinguishable from a dead sensor — far cheaper to find here.

---

## Section 5 — Adjacent-pad bridge sweep

The most common perfboard defect, and **nothing in Sections 2–4 catches a bridge between
two unused pins.** Walk the meter down both 19-pin ESP32 header strips, probing each
socket against its immediate neighbour.

| Sweep | Pairs | Expected | Result |
|---|---|---|---|
| Left strip, pins 1↔2 through 18↔19 | 18 | **No continuity** on every pair | |
| Right strip, pins 20↔21 through 37↔38 | 18 | **No continuity** on every pair | |

**Zero exceptions — every one of the 36 pairs should read open.** Nothing on this build
bridges two adjacent sockets: the only multi-socket nets are GND (three wires all landing
on the pin 38 socket) and the SDA/SCL rails (pin 33 and pin 36, six sockets apart). Any
beep is a defect.

---

## Section 6 — Pin 18 confirmation

| Check | Expected | Result |
|---|---|---|
| Pin 18 socket → GND (pin 38) | **No continuity** | |
| Pin 18 socket → 3V3 (pin 1) | **No continuity** | |
| Pin 18 socket → SDA rail | **No continuity** | |
| Pin 18 socket → SCL rail | **No continuity** | |

Pin 18 should connect to nothing at all. A beep to GND here means a stray bridge on *your*
board — not the board-batch anomaly, which shows as the opposite: no continuity where the
silkscreen promises GND.

---

## Section 7 — Insert modules

Only once Sections 2–6 all pass.

- [ ] Insert ESP32 DevKitC-32 (microcontroller) into both 19-pin strips — press firmly and
      evenly; confirm no pin is folded under or missing its socket
- [ ] Insert BME280 (temp/humidity/pressure sensor) into its 4-pin header
- [ ] Insert BH1750 (light sensor) into its 5-pin header — confirm ADDR is the pin landing
      on the ADDR socket, not shifted by one position
- [ ] **Re-run Section 2's three short checks with modules seated.** A folded-under pin, or
      a module inserted one position off, creates a short that did not exist on the bare
      board. This is the single most valuable repeat check in this document.
- [ ] Attach M3 10mm brass standoffs to the four corner mounting holes

---

## Section 8 — First power-on smoke test

Still before flashing. USB-C to a **computer**, not a wall charger.

- [ ] Meter to **DC volts** (not continuity) before applying power
- [ ] Connect USB-C. Watch the first 5 seconds:
  - [ ] No smoke, no smell, no audible pop
  - [ ] Nothing hot to a fingertip touch — ESP32 regulator, BME280, BH1750
  - [ ] ESP32 onboard power LED lit
- [ ] Measure 3V3 (pin 1) → GND (pin 38): expect **3.2–3.4 V**. Actual: ______ V
- [ ] Measure BME280 VCC socket → GND (pin 38): same reading. Actual: ______ V
- [ ] Measure BH1750 VCC socket → GND (pin 38): same reading. Actual: ______ V

> **Anything hot, or 3V3 below ~3.0 V or above ~3.5 V — unplug immediately** and re-run
> Section 2. A sagging rail usually means a partial short pulling current.

- [x] Confirm the board enumerates on the computer (a new COM port appears) — this
      confirms the CP2102 USB-serial bridge and is a prerequisite for `flashing.md`.
      **2026-09-21: enumerated as COM7** (`Silicon Labs CP210x USB to UART Bridge`,
      VID_10C4/PID_EA60). Verified from the Windows side with
      `Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match 'COM\d+' }` —
      the four `Standard Serial over Bluetooth link` entries are not physical ports.

---

## Results

Run 1 — 2026-09-21, Joseph at the bench, walked through section by section.

| Section | Result | Notes |
|---|---|---|
| 1. Visual inspection | Skipped | Covered by the meter sections; Joseph inspected while soldering |
| 2. Power-rail isolation | **Pass** | All 3 open |
| 3. Continuity (9 + 2 rail) | **Pass** | All 11 beeped, including R1/R2 shared-rail integrity |
| 4. Isolation (5) | **Pass** | All 5 open |
| 5. Adjacent-pad sweep (36) | **Pass** | All 36 pairs open |
| 6. Pin 18 | **Pass** | Isolated from GND, 3V3, SDA, SCL |
| 7. Insert modules + re-check | **Pass** | All 3 short checks still open with ESP32/BME280/BH1750 seated |
| 8. Power-on smoke test | **Pass** | 3.3 V at all three points (3V3 pin 1, BME280 VCC, BH1750 VCC). No heat, no smell, power LED lit. Enumerated as **COM7** — `Silicon Labs CP210x USB to UART Bridge`, VID_10C4/PID_EA60 |

**All sections pass. Board cleared for `flashing.md`.** Port for the first USB flash: **COM7**.

---

## Build and flash record — 2026-09-21

Captured so a later "is the running binary actually the one we built?" question has an
answer, rather than being re-derived. `esphome upload` can silently flash a stale binary;
the check is that the device's own boot log reports the same `build_time_str` below.

| Item | Value |
|---|---|
| ESPHome version | 2026.4.5 |
| `config_hash` | `0xf32d00da` |
| `build_time_str` | `2026-09-21 16:11:06 -0700` |
| Compile | Success, exit 0, 494.42 s — no warnings or errors |
| `firmware.factory.bin` | 1,064,208 bytes, written 16:19 MST |
| `firmware.ota.bin` | 998,672 bytes, written 16:19 MST |
| First flash | USB, COM7, `esphome upload --device COM7` |
| Flash result | Success — 998,672 bytes at `0x10000`, plus bootloader/partition/OTA-data regions. **Hash of data verified** on every region. Hard reset via RTS. |

**Verified 2026-09-21 16:24 MST — binary is fresh.** Device boot log:
`ESPHome version 2026.4.5 compiled on 2026-09-21 16:11:06 -0700`, an exact match for the
compile's `build_time_str`. No stale-upload problem.

### First-boot results

| Subsystem | Result |
|---|---|
| WiFi | Connected — `JCTnet1` |
| MQTT | Connected — broker accepted the new `back-patio-temp-sensor` account |
| safe_mode | Boot-loop counter reset — clean boot |
| BH1750 (light sensor) | **Working** — publishing illuminance (332.1, 330.6 lx) |
| BME280 (temp/humidity/pressure sensor) | **FAILED** — `Wrong chip ID or no response` |

**The BME280 in the socket is one of the counterfeit BMP280s** (Joseph confirmed, 2026-09-21)
— from Bin B3, not Bag 3. Not a build defect: BH1750 shares SDA (pin 33), SCL (pin 36),
3V3 (pin 1) and GND (pin 38) with it and works, which proves the bus, the rails, and every
solder joint on the shared path. The perfboard is good.

ESPHome's `bme280_i2c` platform reads the chip-ID register and refuses anything that is not
`0x60`; a BMP280 reports `0x58`, so the component is marked FAILED and publishes nothing —
not even the temperature and pressure the BMP280 can actually measure. **This is the
counterfeit detector `parts-list.md` predicted, working exactly as intended.**

**Resolution:** genuine BME280 ordered 2026-09-21. The swap is drop-in — same pinout, same
`0x76` address — so it needs no firmware change and no reflash, just reseat and power-cycle.

**Diagnostic note for next time:** `logger: level: INFO` suppresses CONFIG-level output, so
the `i2c: scan: true` results never appear in the log. Raise to `DEBUG` if an address-level
answer is ever needed.

**All eight pass → proceed to `flashing.md`.**

---

## Failure triage

| Symptom | Most likely cause | Next step |
|---|---|---|
| No beep on a Section 3 check | Cold joint, or probing the back instead of the socket | Re-probe from the socket with a male pin; reflow the joint if still open |
| Beep on a Section 2 check | Solder bridge between adjacent pads, or a wire stripped too far | Inspect under magnification along the relevant rail |
| R1 or R2 fails but 3/4/7/8 pass | Break in the shared SDA/SCL rail between the two sensors | Inspect the rail bridge on the back of the board |
| Section 5 beep between two unused pins | Solder bridge on the ESP32 header strip | Wick and reflow both pads |
| Section 2 passes bare but fails after insertion | Folded-under module pin, or module off by one position | Remove, straighten pins, confirm alignment, re-seat |
| 3V3 reads low under power | Partial short pulling current | Unplug, re-run Section 2 |
| No COM port appears | Charge-only USB cable, or missing CP2102 driver | Try a known data cable first — this is the common one |

---

## Notes / observations

Record anything unexpected here as it happens, not afterwards — deviations from the plan
get documented during the work (`JCTsh-Operating-System.md`, Note on Build). Anything
learned that generalizes belongs in `JCTsh-Build-Standards.md` at Reflection.
