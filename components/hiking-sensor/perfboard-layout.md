# Hiking Monitor — Perfboard Layout (Step 14)

## Overview

Two-board approach:
- **Main board (5×7cm)** — ESP32 on female headers, BME280, LTR-390, voltage divider, harness breakouts
- **TP4056+boost module** — mounted separately in enclosure; connected to main board via wiring harness

The display, button, and TP4056 are all off-board. Everything connects to the main perfboard via wire harnesses.

---

## Board Selection

Use a **5×7cm FR4 double-sided perfboard** (from Bag 9) for the main board.

Measure the ESP32 DevKitC pin-row spacing before soldering the female headers: place the ESP32 flat on the perfboard and mark the two header rows with a pencil. The two 19-pin rows are typically 9 holes apart (center-to-center) but verify against your specific board — the header strips must match the actual ESP32 pin pitch exactly or the board won't seat correctly.

For the TP4056+boost module: no additional perfboard needed. Mount it in the enclosure with double-sided foam tape or small standoffs; run wires to the main board.

---

## Component Placement

```
5×7cm board — zone overview (50mm wide × 70mm tall)

 col:  1  2  3  4  5  6  7  8  9  10  11  12  13  14  15  16  17  18  19
       +-------------------------------------------------------------------+
row 1  |  .  .  .  .  .  .  .  .  .   .   .   .   .   .   .   .   .   .  |
row 2  |  .  L  .  .  .  .  .  .  .   .   R   .  [LTR-390 header      ]  |
row 3  |  .  L  .  .  .  .  .  .  .   .   R   .   .   .   .   .   .   .  |
row 4  |  .  L  .  .  .  .  .  .  .   .   R   .   .   .   .   .   .   .  |
row 5  |  .  L  .  .  .  .  .  .  .   .   R   .  [LTR-390 header      ]  |
row 6  |  .  L  .  .  .  .  .  .  .   .   R   .   .   .   .   .   .   .  |
       |  .  L  .  .  .  .  .  .  .   .   R   .   .   .   .   .   .   .  |
       |  .  L  .  .  .  .  .  .  .   .   R   .  [R1 100kΩ            ]  |
       |  .  L  . (ESP32 body)  .  .   .   R   .   .  R1..mid..R2      .  |
       |  .  L  .  .  .  .  .  .  .   .   R   .  [R2 100kΩ            ]  |
       |  .  L  .  .  .  .  .  .  .   .   R   .   .   .   .   .   .   .  |
       |  .  L  .  .  .  .  .  .  .   .   R   .   .   .   .   .   .   .  |
       |  .  L  .  .  .  .  .  .  .   .   R   .  [e-ink harness hdr   ]  |
       |  .  L  .  .  .  .  .  .  .   .   R   .   .   .   .   .   .   .  |
       |  .  L  .  .  .  .  .  .  .   .   R   .   .   .   .   .   .   .  |
       |  .  L  .  .  .  .  .  .  .   .   R   .   .   .   .   .   .   .  |
       |  .  L  .  .  .  .  .  .  .   .   R   .  [BME280 header       ]  |
       |  .  L  .  .  .  .  .  .  .   .   R   .   .   .   .   .   .   .  |
row 20 |  .  L  .  .  .  .  .  .  .   .   R   .  [BME280 header       ]  |
row 21 |  .  .  .  .  .  .  .  .  .   .   .   .   .   .   .   .   .   .  |
row 22 |  .  .  .  .  .  .  .  .  .   .   .   .   .   .   .   .   .   .  |
row 23 |  .  .  [power in: VIN GND]  [sw: GPIO27 GND]  .  [dock: R3 mid R4 GND] |
row 24 |  .  .  .  .  .  .  .  .  .   .   .   .   .   .   .   .   .   .  |
row 25 |  .  .  .  .  .  .  .  .  .   .   .   .   .   .   .   .   .   .  |
row 26 |  .  .  .  .  .  .  .  .  .   .   .   .   .   .   .   .   .   .  |
row 27 |  .  .  .  .  .  .  .  .  .   .   .   .   .   .   .   .   .   .  |
       +-------------------------------------------------------------------+

L = left ESP32 female header (col 2, 19 pins)
R = right ESP32 female header (col 11, 19 pins, 9-hole spacing from L)
```

### Placement Rules

| Component | Position | Reason |
|---|---|---|
| ESP32 female headers | Cols 2 and 11, rows 2–20 | Standard 19-pin removable headers |
| LTR-390 breakout | Right zone, rows 2–5 | Top of board = closest to sky-facing enclosure opening |
| Voltage divider (R1+R2) | Right zone, rows 8–14 | R1=100kΩ (top), R2=100kΩ (bottom); short wire to BAT+ harness |
| E-ink harness header | Right zone, rows 15–18 | 8-pin male header; labeled wires connect to display |
| BME280 breakout | Right zone, rows 17–20 | Bottom of board = farthest from ESP32 (minimizes self-heating error) |
| Power-in header (VIN/GND) | Bottom zone, cols 3–5, row 23 | 2-pin JST or male header; VOUT+ direct → VIN, VOUT− → GND |
| Switch header (GPIO27/GND) | Bottom zone, cols 7–8, row 23 | 2-pin male header; wires to slide switch on enclosure; switch ON = GPIO27 LOW = hiking mode |
| Dock detect divider (R3+R4) | Bottom zone, cols 14–18, row 23 | R3=68kΩ (top), R4=100kΩ (bottom); top to TP4056 IN+, midpoint to GPIO32 |

---

## Wiring Connections

### Power

**BAT+ / BAT−** — battery connects here; BAT+ also tapped for voltage sense

| From | To | Notes |
|---|---|---|
| TP4056 BAT+ | R1 (100kΩ) top leg | Battery voltage sense — tap wire from TP4056 to voltage divider |

*(BAT− wired directly from LiPo black wire to TP4056 BAT− pad — no perfboard connection)*

**VOUT+ / VOUT−** — boosted 5.7V output; powers the ESP32 directly (no switch in power path)

| From | To | Notes |
|---|---|---|
| TP4056 VOUT+ | ESP32 VIN (left header pin 19, row 20) | 5.7V direct; harness wire lands on 2-pin power-in header at row 23, trace runs to VIN — bottom pin of left female header |
| TP4056 VOUT− | ESP32 GND (left header pin 14, row 15) | Harness wire lands on power-in header at row 23, trace runs to GND — right-side GND pins also acceptable |

**Slide switch** — hiking mode signal to ESP32; no longer in power path

| From | To | Notes |
|---|---|---|
| Switch terminal 1 | Switch header pin 1 (GPIO27) | Switch ON (closed) pulls GPIO27 LOW = hiking mode |
| Switch terminal 2 | Switch header pin 2 (GND) | |

**IN+ / IN−** — solar/USB charging input; IN+ also tapped for dock detect

| From | To | Notes |
|---|---|---|
| TP4056 IN+ | R3 (68kΩ) top leg | USB VBUS tap — dock detect divider input |

*(IN− wired directly from solar panel JST connector to TP4056 IN− pad — no perfboard connection)*

**On-board sensor power** — 3.3V rail from ESP32 to sensors

| From | To | Notes |
|---|---|---|
| ESP32 3.3V | LTR-390 VIN, BME280 VCC | Short jumpers to sensor header VCC pins |
| ESP32 GND | LTR-390 GND, BME280 GND, R2 (100kΩ) bottom leg, R4 (100kΩ) bottom leg | Short jumpers to sensor header GND pins |

### I2C (BME280 + LTR-390)

| ESP32 Pin | Sensor Pin | Notes |
|---|---|---|
| GPIO21 (SDA) | BME280 SDA + LTR-390 SDA | Wire both sensor SDA pins to GPIO21 |
| GPIO22 (SCL) | BME280 SCL + LTR-390 SCL | Wire both sensor SCL pins to GPIO22 |

### Voltage Divider

```
TP4056 BAT+ wire ──── R1 (100kΩ) ──┬──── R2 (100kΩ) ──── GND
                                    │
                               GPIO35 (via jumper wire)
```

Both resistors soldered directly to perfboard. Midpoint node connects to ESP32 GPIO35. Top node connects to TP4056 BAT+ via a short wire harness.

### E-Ink Display Harness (8 wires)

Solder an 8-pin male header to the perfboard. Label each pin. Attach matching female housing on the display cable end.

| Header pin | ESP32 pin | Display wire color | Display label |
|---|---|---|---|
| 1 | 3.3V | Grey | VCC |
| 2 | GND | Brown | GND |
| 3 | GPIO23 | Blue | DIN |
| 4 | GPIO18 | Yellow | CLK |
| 5 | GPIO5 | Orange | CS |
| 6 | GPIO17 | Green | DC |
| 7 | GPIO16 | White | RST |
| 8 | GPIO4 | Purple | BUSY |

---

## Voltage Divider Detail

R1 and R2 are through-hole 100kΩ 1/4W axial resistors soldered directly to the perfboard. Layout:

```
[BAT+ pad] ── R1 ── [midpoint pad] ── R2 ── [GND pad]
                          │
                     [GPIO35 pad]
```

Four solder pads, roughly in a line:
- Pad 1: BAT+ (wire runs off-board to TP4056 BAT+)
- Pad 2: midpoint (GPIO35 jumper + R1 (100kΩ) bottom + R2 (100kΩ) top)
- Pad 3: GND
- Pad 4 (optional): tie to GPIO35 jumper wire anchor

---

## Dock Detect Divider Detail

R3 (68kΩ) and R4 (100kΩ) are through-hole axial resistors soldered directly to the perfboard. Layout:

```
[IN+ pad] ── R3 (68kΩ) ── [midpoint pad] ── R4 (100kΩ) ── [GND pad]
                                  │
                             [GPIO32 pad]
```

Four solder pads, roughly in a line:
- Pad 1: IN+ (wire runs off-board to TP4056 IN+/USB VBUS pad)
- Pad 2: midpoint (GPIO32 jumper + R3 bottom + R4 top)
- Pad 3: GND
- Pad 4 (optional): tie to GPIO32 jumper wire anchor

Measured voltages: IN+ = 0.47V (USB absent) → midpoint ≈ 0.28V (LOW). IN+ = 5.1V (USB present) → midpoint ≈ 3.04V (HIGH). GPIO32 configured as INPUT (no pull-up or pull-down).

---

## Off-Board Components

| Component | Connection method | Notes |
|---|---|---|
| Waveshare 2.13" e-ink display | 8-wire harness (GPIO4/5/16/17/18/23 + 3.3V + GND) | Display mounts on enclosure face; harness loops inside enclosure to perfboard |
| Slide switch | 2-wire harness (GPIO27 + GND) | Switch mounts on enclosure side; signals hiking mode to ESP32 |
| TP4056+boost module | 4-pin male header + female Dupont | Single connector for all 4 TP4056→perfboard wires: VOUT+, VOUT−, BAT+, IN+; wire colors TBD |
| LiPo battery | Wired directly to TP4056 BAT+/BAT− pads | Battery sits in enclosure; wires to TP4056 (not to main perfboard directly) |

---

## Connector and Harness Plan

Connector types are decided below. Harness lengths, exact mounting positions, and
micro USB access approach are all TBD pending enclosure design (Step 15).

### Connection Summary

| Connection | From | To | Connector | Status |
|---|---|---|---|---|
| Battery | LiPo JST plug | TP4056 BAT+/BAT− | JST PH 2.0mm receptacle soldered to BAT pads | Decided |
| Solar input | SUNYIMA panel | TP4056 IN+/IN− | JST SM 2-pin (Bag 14) panel-mount on enclosure wall | Decided; position TBD |
| TP4056 harness (4-wire) | TP4056 VOUT+, VOUT−, BAT+, IN+ | Perfboard 4-pin header | 4-pin male header on perfboard + female Dupont housing; wire colors TBD | Decided |
| Slide switch | Perfboard switch header (GPIO27 + GND) | Enclosure-mounted slide switch | 2-wire harness + female Dupont; switch ON pulls GPIO27 LOW | Position TBD |
| E-ink display | Perfboard 8-pin header | Waveshare display cable | 8-pin male header + female housing on display end | Decided; length ~10–15cm |
| Charging input | USB charger | TP4056 micro USB | Panel-mount micro USB extension or enclosure cutout | TBD |
| TP4056 mounting | TP4056 module | Enclosure floor | M2 standoffs (preferred) or foam tape | TBD |

### Battery Connector (BAT+/BAT−)

The LiPo (EEMB 1100mAh) has a built-in JST PH 2.0mm plug. The TP4056 has bare BAT+/BAT− pads.
Solder a JST PH 2.0mm female receptacle to the BAT pads. Polarity confirmed: red = BAT+, black = BAT−
(see power-system.md Step 1).

### Solar Input Connector (IN+/IN−)

JST SM 2-pin panel-mount receptacle on enclosure wall — female receptacle mounted through the wall,
short internal wire from receptacle to TP4056 IN+/IN− pads. The SUNYIMA panel connects via its
existing JST plug to the external side of the receptacle.

The IN+ pad also has a dock detect tap wire — this runs from the TP4056 IN+ pad to pin 4 of the
4-pin perfboard header, then a trace connects to R3 top leg. Solar connected while hiking no
longer suppresses data collection (switch state determines mode, not dock detect).

### Slide Switch Harness

The switch is no longer in the power path. VOUT+ runs directly from TP4056 to the power-in header. The switch wires connect to the switch header (GPIO27 + GND).

```
TP4056 VOUT+ ── wire ── 4-pin header pin 1  (→ ESP32 VIN)
TP4056 VOUT− ── wire ── 4-pin header pin 2  (→ ESP32 GND)
TP4056 BAT+  ── wire ── 4-pin header pin 3  (→ R1 top leg)
TP4056 IN+   ── wire ── 4-pin header pin 4  (→ R3 top leg)
  (all four via female Dupont housing — single connector, wire colors TBD)

Switch terminal 1 ── wire ── switch header pin 1 (GPIO27)
Switch terminal 2 ── wire ── switch header pin 2 (GND)
```

Switch ON (closed): GPIO27 pulled LOW → firmware enters hiking/data-collection mode.
Switch OFF (open): GPIO27 floats HIGH via internal pull-up → firmware enters sleep or upload mode.

ESP32 deep sleep replaces the hard power cut. Sleep current ~10μA — negligible on a 1100mAh battery.
Exact wire lengths TBD once enclosure dimensions and switch position are known.

### Micro USB Charging Access

Two options — decide when enclosure is selected:
- **Panel-mount extension (preferred):** short male-to-female micro USB extension; female end
  mounts through enclosure wall; TP4056 micro USB connects to the male end internally.
  TP4056 position is flexible.
- **Cutout:** opening in enclosure wall aligned with the TP4056 micro USB port. Requires
  precise TP4056 positioning against the wall.

### TP4056 Mounting

Preferred: M2 standoffs screwed into enclosure floor — two screws, stable, removable.
Alternative: double-sided foam tape — faster but not removable without damage.
Position TBD pending enclosure selection; keep close to the USB charging port side to
minimise the micro USB extension run.

---

## Pre-Power Checks

Complete these before connecting the LiPo. Use a multimeter throughout. Remove the ESP32 and sensors from their headers for cleaner readings — re-seat for pin-to-pin checks if needed.

**Do the short circuit check first.** A VIN–GND short will damage the TP4056 or ESP32 on first power-up.

### Short Circuit

| # | Probe A | Probe B | Mode | Expected |
|---|---|---|---|---|
| 1 | Power-in header pin 1 (VIN) | Power-in header pin 2 (GND) | Resistance | >100kΩ — if it beeps or reads <1kΩ, find the short before proceeding |

### Power Path

| # | Probe A | Probe B | Mode | Expected |
|---|---|---|---|---|
| 2 | TP4056 VOUT+ pad | ESP32 left header pin 19 (VIN, row 20) | Continuity | Beep |
| 3 | TP4056 VOUT− pad | ESP32 left header pin 14 (GND, row 15) | Continuity | Beep |

### Ground Rail

| # | Probe A | Probe B | Mode | Expected |
|---|---|---|---|---|
| 4 | ESP32 GND (left pin 14) | ESP32 GND (right pin 32) | Continuity | Beep |
| 5 | ESP32 GND | R2 bottom leg | Continuity | Beep |
| 6 | ESP32 GND | R4 bottom leg | Continuity | Beep |
| 7 | ESP32 GND | BME280 header GND pin | Continuity | Beep |
| 8 | ESP32 GND | LTR-390 header GND pin | Continuity | Beep |
| 9 | ESP32 GND | Switch header GND pin | Continuity | Beep |
| 10 | ESP32 GND | E-ink harness header pin 2 (GND) | Continuity | Beep |

### Sensor Power (3.3V Rail)

| # | Probe A | Probe B | Mode | Expected |
|---|---|---|---|---|
| 11 | ESP32 left pin 1 (3V3) | BME280 header VCC pin | Continuity | Beep |
| 12 | ESP32 left pin 1 (3V3) | LTR-390 header VIN pin | Continuity | Beep |
| 13 | ESP32 left pin 1 (3V3) | E-ink harness header pin 1 (VCC) | Continuity | Beep |

### Battery Voltage Divider (R1 + R2)

| # | Probe A | Probe B | Mode | Expected |
|---|---|---|---|---|
| 14 | TP4056 BAT+ pad | R1 top leg | Continuity | Beep |
| 15 | R1/R2 midpoint | ESP32 left pin 6 (GPIO35) | Continuity | Beep |
| 16 | TP4056 BAT+ tap | GND | Resistance | ~200kΩ (R1+R2 in series) |
| 17 | R1/R2 midpoint | GND | Resistance | ~100kΩ (R2 only) |

### Dock Detect Divider (R3 + R4)

| # | Probe A | Probe B | Mode | Expected |
|---|---|---|---|---|
| 18 | TP4056 IN+ tap wire | R3 top leg | Continuity | Beep |
| 19 | R3/R4 midpoint | ESP32 left pin 7 (GPIO32) | Continuity | Beep |
| 20 | TP4056 IN+ tap | GND | Resistance | ~168kΩ (R3+R4 in series) |
| 21 | R3/R4 midpoint | GND | Resistance | ~100kΩ (R4 only) |

### Slide Switch Header

| # | Probe A | Probe B | Mode | Expected |
|---|---|---|---|---|
| 22 | Switch header GPIO27 pin | ESP32 left pin 11 (GPIO27) | Continuity | Beep |

### I2C Bus

| # | Probe A | Probe B | Mode | Expected |
|---|---|---|---|---|
| 23 | BME280 header SDA pin | ESP32 right pin 33 (GPIO21) | Continuity | Beep |
| 24 | LTR-390 header SDA pin | ESP32 right pin 33 (GPIO21) | Continuity | Beep |
| 25 | BME280 header SCL pin | ESP32 right pin 36 (GPIO22) | Continuity | Beep |
| 26 | LTR-390 header SCL pin | ESP32 right pin 36 (GPIO22) | Continuity | Beep |

### E-Ink Harness (8 pins)

| # | Harness pin | Signal | Probe B (ESP32) | Mode | Expected |
|---|---|---|---|---|---|
| 27 | Pin 3 | DIN | Right pin 37 (GPIO23) | Continuity | Beep |
| 28 | Pin 4 | CLK | Right pin 30 (GPIO18) | Continuity | Beep |
| 29 | Pin 5 | CS | Right pin 29 (GPIO5) | Continuity | Beep |
| 30 | Pin 6 | DC | Right pin 28 (GPIO17) | Continuity | Beep |
| 31 | Pin 7 | RST | Right pin 27 (GPIO16) | Continuity | Beep |
| 32 | Pin 8 | BUSY | Right pin 26 (GPIO4) | Continuity | Beep |

*(Harness pins 1 and 2 covered in checks 13 and 10 above.)*

---

## Assembly Sequence

1. **Mark header positions** — place ESP32 on bare perfboard, mark the two header rows with pencil. Verify 9-hole spacing matches your specific ESP32 before soldering anything.

2. **Solder left header strip** (19-pin female, col 2, rows 2–20)

3. **Test-fit ESP32** — insert ESP32 into left header. Mark right header position from actual pin position (do not assume — measure from the board). Remove ESP32.

4. **Solder right header strip** (19-pin female). Insert ESP32 and confirm it seats flat with no pin misalignment.

5. **Solder sensor headers** — 4-pin female headers for BME280 and LTR-390 in their respective zones. Confirm LTR-390 header is oriented so the sensor chip faces upward when the board is in its mounted position.

6. **Solder voltage divider** — R1 (100kΩ) and R2 (100kΩ) in-line, midpoint pad to GPIO35 jumper.

7. **Solder e-ink harness header** — 8-pin male header. Label each pin with a fine-tip marker or small paper flags before attaching wires.

8. **Solder dock detect divider** — R3 (68kΩ) and R4 (100kΩ) in-line in bottom zone. Top pad connects to TP4056 IN+ tap wire; midpoint pad connects to GPIO32 jumper; bottom pad connects to GND.

9. **Solder power-in header** — 2-pin for VOUT+ (direct) and VOUT−. Also solder 2-pin switch header (cols 7–8, row 23) for GPIO27 + GND.

10. **Run point-to-point jumpers** — connect sensor headers to ESP32 GPIO pins per wiring table above. Use short silicone wire; route along perfboard rows/columns neatly.

11. **Seat ESP32 and sensors** — insert ESP32 into headers. Insert BME280 and LTR-390 into their headers.

12. **Connect TP4056 harness** — connect VOUT+ directly to power-in header pin 1, VOUT− to pin 2, BAT+ tap wire to voltage divider R1 top pad. Connect slide switch harness to switch header (GPIO27 + GND).

13. **Power-on test** — connect LiPo to TP4056. Confirm device boots, sensors read correctly, battery_v reading is plausible. Check log dashboard for "MQTT connected" and sensor values.

---

## Notes

- **Do not solder ESP32 directly to perfboard** — female headers allow removal for rework and reuse.
- **BME280 position matters** — placing it at the far end from the ESP32 chip reduces thermal error. On breadboard, self-heating added ~10°F; perfboard separation should improve this.
- **LTR-390 orientation** — the sensor chip must face upward (toward sky) when the device is in normal carrying position. Verify orientation before soldering the header.
- **E-ink refresh** — display refreshes on every sensor update cycle (not on-demand). Full refresh every cycle causes visible flashing; accepted as preferable to an on-demand button.
- **Wire length** — keep I2C jumpers short and direct. E-ink harness can be 10–15cm to reach the enclosure face; longer is fine for low-speed SPI.
- **Silicone wire for harnesses** — use silicone hookup wire (Shelf) for all harnesses. It's flexible and handles repeated bending inside the enclosure without cracking.
- **Enclosure target** — the 75×45×20mm enclosure target from Step 15 may need revision once the perfboard actual dimensions are measured. Step 15 is designed around the completed perfboard, not the other way around.
