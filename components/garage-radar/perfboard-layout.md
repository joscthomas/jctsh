# Garage Radar — Perfboard Layout (Step 5)

## Materials

| Item | Spec |
|---|---|
| Perfboard | Chanzon FR4 double-sided, 5×7cm (~19×27 holes on 2.54mm grid) |
| Female headers | Glarks 2.54mm single-row — two 19-pin strips (ESP32), one 4-pin strip (LD2412) |
| Standoffs | Hilitchi M3 brass male-female, 10mm |
| Wire | Solid core jumper wire for back-of-board bridges |
| Green LED | 5mm T-1¾ (presence indicator — GPIO33) |
| Yellow LED | 5mm T-1¾ (vswitch mirror — GPIO32) |
| Resistors | 330Ω ¼W × 2 (one per LED) |

---

## Board Orientation

The board mounts **vertically** on the pegboard (standing perpendicular to the pegboard
surface). Keep this final orientation in mind throughout assembly:

```
[Pegboard surface]
       |
  [Standoffs] — board stands out from pegboard
       |
  ┌─────────┐
  │ LD2412  │ ← antenna face points horizontally toward workbench
  │         │
  │  ESP32  │
  │         │
  └─────────┘
       |
  [USB cable exits here → to outlet]
```

**Antenna end = top.** LD2412 goes at the top. USB end = bottom. This keeps the USB
cable hanging down and accessible without interfering with the detection zone.

---

## Component Placement

```
     A  B  C  D  E  F  G  H  I  J  K  L  M  N  O  P  Q  R  S
  1  [M]                                              [M]
  2
  3           [5V][GN][TX][RX] ← 4-pin LD2412 header (cols D–G)
  4  [YC][YA][YR]              ← Yellow LED (GPIO32 → vswitch): cathode col A, anode col B, 330Ω col B–C
  5  [GC][GA][GR]              ← Green LED (GPIO33 → presence): cathode col A, anode col B, 330Ω col B–C
  6
  7           [L]                    [R]   ← ESP32 pin 1 (3.3V / GND)
  8           [L]                    [R]
  9           [L]                    [R]
 10           [L]                    [R]
 11           [L]                    [R]
 12           [L]                    [R]
 13           [L]                    [R]
 14           [L]                    [R]
 15           [L]                    [R]
 16           [L]                    [R]
 17           [L]  GPIO16/RX2        [R]
 18           [L]  GPIO17/TX2        [R]
 19           [L]                    [R]
 20           [L]                    [R]
 21           [L]                    [R]
 22           [L]                    [R]
 23           [L]                    [R]
 24           [L]                    [R]
 25           [L]  5V (VIN)          [R] ← ESP32 pin 19 (USB end)
 26  [M]                                              [M]
 27
```

`[M]` = M3 standoff mounting hole. `[L]` = left ESP32 header row. `[R]` = right ESP32 header row.
`[YC]`/`[YA]`/`[YR]` = yellow LED cathode / anode / 330Ω resistor. `[GC]`/`[GA]`/`[GR]` = same for green.

Column spacing between `[L]` and `[R]` depends on your specific ESP32 module — measure the
pin-to-pin width across the board before soldering headers.

**LED orientation:** long leg (anode) faces col B (toward resistor). Short leg (cathode, flat
side of base) faces col A (toward GND). The 330Ω resistor bridges col B–C in the same row.
Installing an LED backwards will not damage it at 3.3V/330Ω — if it does not light, flip it.

> **Verify exact pin positions:** The row numbers for GPIO16, GPIO17, and VIN are
> approximate. Before soldering wire bridges, confirm the actual hole position for each
> pin using `ESP32pins.png` in this directory and count from the USB end of the inserted
> board.

---

## LD2412 Antenna Orientation

The **blank face** of the LD2412 (no components, just the PCB surface) is the antenna
face. It must point outward toward the workbench — not toward the ESP32 or the pegboard.

When plugged into the 4-pin header at the top of the board:
- Orient the LD2412 so the antenna face points **away from the perfboard surface**
  (upward when the board is flat on your workbench, then outward when mounted vertically)
- Do **not** place the ESP32 or any metal shield directly between the LD2412 antenna
  and the detection zone

---

## Wire Bridges (back of board)

Four wire bridges connect the LD2412 header to the ESP32 headers. Route all bridges
on the back (solder side) of the board using solid-core wire.

| Bridge | From | To | Color |
|---|---|---|---|
| Power | LD2412 header pin 1 (5V) | ESP32 VIN hole | Red |
| Ground | LD2412 header pin 2 (GND) | ESP32 GND hole | Black |
| UART data | LD2412 header pin 3 (TX) | ESP32 GPIO16/RX2 hole | Green |
| UART data | LD2412 header pin 4 (RX) | ESP32 GPIO17/TX2 hole | Yellow |
| Yellow LED signal | GPIO32 header hole (row 13, col C) | 330Ω resistor leg at row 4, col C | Yellow |
| Green LED signal | GPIO33 header hole (row 14, col C) | 330Ω resistor leg at row 5, col C | Green |
| LED GND | Yellow LED cathode (row 4, col A) → Green LED cathode (row 5, col A) | ESP32 GND header hole | Black |

> **LED GND bridge:** daisy-chain — run one short wire from row 4 col A to row 5 col A to join the two
> cathodes, then run a single GND wire from row 5 col A back to the ESP32 GND hole (left header, pin 14,
> row 20 col C). Three short wires total for LED GND.

Keep bridges short and flat against the board. Do not route bridges across mounting
hole locations. Use the same TX→RX/RX→TX orientation as the breadboard build.

---

## Soldering Sequence

**Do not insert the ESP32 or LD2412 until continuity checks pass.**

**1. Mark mounting holes first**
Before soldering anything, hold the perfboard in the orientation it will be mounted.
Mark the four corner mounting holes. Do not solder any component over these holes.

**2. Solder the ESP32 female headers**
- Place both 19-pin strips in the correct columns with the correct spacing
- Tack one pin at each end of each strip, check alignment and parallelism before
  soldering all pins
- The two strips must be parallel and at exactly the correct column spacing to match
  your ESP32's pin width — measure the ESP32 pin-to-pin distance before placing headers
- Solder all 38 pins

**3. Solder the LD2412 4-pin header**
- Place the 4-pin strip at rows 3, columns D–G
- Verify the column positions match where your wire bridges will run
- Solder all 4 pins

**4. Solder LEDs and resistors**
- Place yellow LED at row 4: long leg (anode) in col B, short leg (cathode) in col A
- Place 330Ω resistor at row 4: one leg in col B (shared with LED anode), other leg in col C
- Place green LED at row 5: same orientation
- Place 330Ω resistor at row 5: same pattern
- Solder all four components from the back; trim leads flush

**5. Solder wire bridges**
- Cut wire segments to length — keep them short and routed cleanly
- Strip and tin each end before soldering
- Solder all six bridges (four for LD2412, two LED signals, LED GND daisy-chain) on the back of the board

**6. Continuity checks — do not skip**
Before inserting any component, use a multimeter in continuity mode (and resistance mode for LED paths):

| Check | Expected |
|---|---|
| LD2412 5V pin → ESP32 VIN pin | Continuity |
| LD2412 GND pin → ESP32 GND pin | Continuity |
| LD2412 TX pin → ESP32 GPIO16 pin | Continuity |
| LD2412 RX pin → ESP32 GPIO17 pin | Continuity |
| LD2412 5V pin → LD2412 GND pin | No continuity (short check) |
| ESP32 VIN pin → ESP32 GND pin | No continuity (short check) |
| LD2412 TX pin → LD2412 RX pin | No continuity (cross-wire check) |
| GPIO32 header hole → yellow LED anode | ~330Ω (use resistance mode) |
| GPIO33 header hole → green LED anode | ~330Ω (use resistance mode) |
| Yellow LED cathode → ESP32 GND | Continuity |
| Green LED cathode → ESP32 GND | Continuity |

**Do not power on until all continuity checks pass.**

**7. Insert the ESP32 and LD2412**
- Insert the ESP32 into the two 19-pin header strips — press firmly and evenly
- Plug the LD2412 into the 4-pin header with the antenna face pointing away from
  the board surface
- Attach M3 standoffs to the four corner mounting holes

---

## After Assembly

Proceed to **Step 6 — Soldered Board Validation** (`testing.md`).

Power the board via USB and re-run the full sensor validation from `testing.md`.
Behavior should be identical to the breadboard build. If not, recheck wire bridges
with a multimeter before troubleshooting firmware.
