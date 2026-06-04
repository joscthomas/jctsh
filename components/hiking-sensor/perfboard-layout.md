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
       |  .  L  .  .  .  .  .  .  .   .   R   .  [voltage divider R1  ]  |
       |  .  L  . (ESP32 body)  .  .   .   R   .   .  R1..mid..R2      .  |
       |  .  L  .  .  .  .  .  .  .   .   R   .  [voltage divider R2  ]  |
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
row 23 |  .  .  [power in header: VIN GND]  .   .  [btn header: G32 GND]  |
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
| Voltage divider (R1+R2) | Right zone, rows 8–14 | Center of board; short wire to BAT+ harness |
| E-ink harness header | Right zone, rows 15–18 | 8-pin male header; labeled wires connect to display |
| BME280 breakout | Right zone, rows 17–20 | Bottom of board = farthest from ESP32 (minimizes self-heating error) |
| Power-in header (VIN/GND) | Bottom zone, cols 3–5, row 23 | 2-pin JST or male header; TP4056 VOUT+/VOUT- connect here |
| Button header (GPIO32/GND) | Bottom zone, cols 14–16, row 23 | 2-pin JST or male header; button wires connect here |

---

## Wiring Connections

### Power

| From | To | Notes |
|---|---|---|
| TP4056 VOUT+ | Power-in header pin 1 | 5.7V boost output |
| Power-in header pin 1 | ESP32 VIN | Via perfboard trace or jumper |
| TP4056 VOUT− | Power-in header pin 2 | Common ground |
| Power-in header pin 2 | ESP32 GND | Via perfboard trace or jumper |
| TP4056 BAT+ | R1 top leg (voltage divider) | Battery voltage sense — separate wire from TP4056 to divider |
| ESP32 3.3V | LTR-390 VIN, BME280 VCC | Short jumpers to sensor header VCC pins |
| ESP32 GND | LTR-390 GND, BME280 GND, R2 bottom leg | Short jumpers to sensor header GND pins |

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

### Button Harness (2 wires)

Solder a 2-pin male header (or JST receptacle). One wire to GPIO32, one wire to GND.

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
- Pad 2: midpoint (GPIO35 jumper + R1 bottom + R2 top)
- Pad 3: GND
- Pad 4 (optional): tie to GPIO35 jumper wire anchor

---

## Off-Board Components

| Component | Connection method | Notes |
|---|---|---|
| Waveshare 2.13" e-ink display | 8-wire harness (GPIO4/5/16/17/18/23 + 3.3V + GND) | Display mounts on enclosure face; harness loops inside enclosure to perfboard |
| Tactile push button | 2-wire harness (GPIO32 + GND) | Button mounts on enclosure side; short harness to perfboard button header |
| TP4056+boost module | 2-wire power harness (VOUT+/VOUT−) + 1-wire BAT+ tap | TP4056 mounts separately in enclosure; 3 wires run to main perfboard |
| LiPo battery | Wired directly to TP4056 BAT+/BAT− pads | Battery sits in enclosure; wires to TP4056 (not to main perfboard directly) |

---

## Assembly Sequence

1. **Mark header positions** — place ESP32 on bare perfboard, mark the two header rows with pencil. Verify 9-hole spacing matches your specific ESP32 before soldering anything.

2. **Solder left header strip** (19-pin female, col 2, rows 2–20)

3. **Test-fit ESP32** — insert ESP32 into left header. Mark right header position from actual pin position (do not assume — measure from the board). Remove ESP32.

4. **Solder right header strip** (19-pin female). Insert ESP32 and confirm it seats flat with no pin misalignment.

5. **Solder sensor headers** — 4-pin female headers for BME280 and LTR-390 in their respective zones. Confirm LTR-390 header is oriented so the sensor chip faces upward when the board is in its mounted position.

6. **Solder voltage divider** — R1 and R2 in-line, midpoint pad to GPIO35 jumper.

7. **Solder e-ink harness header** — 8-pin male header. Label each pin with a fine-tip marker or small paper flags before attaching wires.

8. **Solder button harness header** — 2-pin male header or JST receptacle.

9. **Solder power-in header** — 2-pin for VOUT+/VOUT−.

10. **Run point-to-point jumpers** — connect sensor headers to ESP32 GPIO pins per wiring table above. Use short silicone wire; route along perfboard rows/columns neatly.

11. **Seat ESP32 and sensors** — insert ESP32 into headers. Insert BME280 and LTR-390 into their headers.

12. **Connect TP4056 harness** — connect VOUT+/VOUT− harness to power-in header, BAT+ tap wire to voltage divider R1 top pad.

13. **Power-on test** — connect LiPo to TP4056. Confirm device boots, sensors read correctly, battery_v reading is plausible. Check log dashboard for "MQTT connected" and sensor values.

---

## Notes

- **Do not solder ESP32 directly to perfboard** — female headers allow removal for rework and reuse.
- **BME280 position matters** — placing it at the far end from the ESP32 chip reduces thermal error. On breadboard, self-heating added ~10°F; perfboard separation should improve this.
- **LTR-390 orientation** — the sensor chip must face upward (toward sky) when the device is in normal carrying position. Verify orientation before soldering the header.
- **Wire length** — keep I2C jumpers short and direct. E-ink harness can be 10–15cm to reach the enclosure face; longer is fine for low-speed SPI.
- **Silicone wire for harnesses** — use silicone hookup wire (Shelf) for all harnesses. It's flexible and handles repeated bending inside the enclosure without cracking.
- **Enclosure target** — the 75×45×20mm enclosure target from Step 15 may need revision once the perfboard actual dimensions are measured. Step 15 is designed around the completed perfboard, not the other way around.
