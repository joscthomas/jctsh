# Back Patio Temp Sensor — Perfboard Layout

Identical layout to `front-porch-temp-sensor` — same hardware, same component placement. Building directly to perfboard (no breadboard stage).

## Materials

| Item | Spec |
|---|---|
| Perfboard | Chanzon FR4 double-sided, 5×7cm (~19×27 holes on 2.54mm grid) |
| Female headers | 2.54mm single-row — two 19-pin strips for ESP32 DevKitC-32 (microcontroller), one 4-pin strip for BME280 (temp/pressure sensor), ~~one 3-pin strip~~ **one 5-pin strip** for BH1750 (light sensor) — see the header-size warning below |
| Standoffs | M3 brass male-female, 10mm |
| Wire | Solid core jumper wire for back-of-board bridges |

---

## ⚠️ Header-size defect — read before soldering (found 2026-09-21)

**This doc said the BH1750 (light sensor) needs a 3-pin female header. It needs 5.** The BH1750 (GY-302) breakout has five pins — VCC, GND, SCL, SDA, ADDR — and this build wires all five (`wiring.md`, and the Wire Bridges table below, which lists five BH1750 bridges including ADDR). A 3-pin socket cannot seat a 5-pin module.

**Inherited from `front-porch-temp-sensor/perfboard-layout.md`, which has the identical error** — it also says "3-pin strip" while listing five BH1750 bridges. Front-porch is built and working, so its *as-built* header must differ from what its doc says; the doc was never corrected to match (`JCTsh-Operating-System.md`: as-built docs describe what is, and this one doesn't). Corrected here to 5-pin, which is what the module physically requires.

**Corrected in `front-porch-temp-sensor/perfboard-layout.md` too, 2026-09-21** — same session, since both components share this cluster. What remains unverified there is the *physical* as-built header on the deployed front-porch board: it is built and running, so whatever is fitted works, but nobody has looked to confirm whether it is a 5-pin strip, a 4-pin plus a flying ADDR lead, or something else. Worth an eyeball next time that unit is accessible.

Headers are breakaway strips, so this costs nothing but a different break point — as long as it's caught before the 3-pin version is soldered down.

---

## Board Orientation

The board mounts at the outlet mount point (P2, `house-lot-coordinates.md`) via M3 standoffs, open face up. The BME280 (temp/pressure sensor) and BH1750 (light sensor) must remain exposed to ambient air and light — do not enclose them.

```
[Wall / mounting surface, at the outlet]
       |
  [Standoffs] — board stands out from surface
       |
  ┌─────────────┐
  │ BME280 BH1750│ ← sensors face up / outward toward open air
  │             │
  │    ESP32    │
  │             │
  └─────────────┘
       |
  [USB cable exits here → to outlet]
```

Place BME280 (temp/pressure sensor) and BH1750 (light sensor) away from the ESP32 DevKitC-32 (microcontroller) — the ESP32 generates slight heat that can affect temperature readings if sensors are too close.

---

## Component Placement

```
     A  B  C  D  E  F  G  H  I  J  K  L  M  N  O  P  Q  R  S
  1  [M]                                              [M]
  2
  3        [VC][GN][SD][SC] ← 4-pin BME280 header (cols C–F)
  4        [VC][GN][SC][SD][AD] ← 5-pin BH1750 header (cols C–G, shares SDA/SCL rail; AD=ADDR→GND)
  5
  6
  7           [L]                    [R]   ← ESP32 pin 1 (3.3V / GND end)
  8           [L]                    [R]
  9           [L]                    [R]
 10           [L]                    [R]
 11           [L]                    [R]
 12           [L]  GPIO21 (SDA)      [R]
 13           [L]  GPIO22 (SCL)      [R]
 14           [L]                    [R]
 15           [L]                    [R]
 16           [L]                    [R]
 17           [L]                    [R]
 18           [L]                    [R]
 19           [L]                    [R]
 20           [L]                    [R]
 21           [L]                    [R]
 22           [L]                    [R]
 23           [L]                    [R]
 24           [L]                    [R]
 25           [L]  3.3V / GND        [R] ← ESP32 pin 19 (USB end)
 26  [M]                                              [M]
 27
```

`[M]` = M3 standoff mounting hole. `[L]` = left ESP32 header row. `[R]` = right ESP32 header row.
`[VC]` = VCC, `[GN]` = GND, `[SD]` = SDA, `[SC]` = SCL, `[AD]` = ADDR (BH1750 only, tied to GND).

> **Verify exact pin positions** before soldering wire bridges. Confirm GPIO21 and GPIO22 row numbers by counting from the USB end using `ESP32pins.png`. Ground both sensor GND legs to pin 38, not pin 18 (see this build's `ESP32-project-pins.md` pin 18 note).

> **BH1750 ADDR pin:** Tie to GND via black wire on the back of the board.

---

## Wire Bridges (back of board)

Route all bridges on the back (solder side) using solid-core wire. Keep bridges short and flat. Do not route across mounting holes.

| Bridge | From | To | Wire Color |
|---|---|---|---|
| BME280 (temp/pressure) VCC | BME280 header pin 1 | ESP32 3.3V hole | Red |
| BME280 (temp/pressure) GND | BME280 header pin 2 | ESP32 GND hole (pin 38) | Black |
| BME280 (temp/pressure) SDA | BME280 header pin 3 | ESP32 GPIO21 hole | Blue |
| BME280 (temp/pressure) SCL | BME280 header pin 4 | ESP32 GPIO22 hole | Yellow |
| BH1750 (light sensor) VCC | BH1750 header pin 1 | ESP32 3.3V hole | Red |
| BH1750 (light sensor) GND | BH1750 header pin 2 | ESP32 GND hole (pin 38) | Black |
| BH1750 (light sensor) SDA | BH1750 header pin 3 | ESP32 GPIO21 hole | Blue |
| BH1750 (light sensor) SCL | BH1750 header pin 4 | ESP32 GPIO22 hole | Yellow |
| BH1750 (light sensor) ADDR | BH1750 ADDR pin | ESP32 GND hole (pin 38) | Black |

SDA and SCL bridges from both sensors land on the same GPIO21 and GPIO22 holes — connect them to a short shared rail on the back of the board rather than running two separate wires to the same hole.

---

## Soldering Sequence

**Do not insert the ESP32 DevKitC-32, BME280, or BH1750 until continuity checks pass.**

**1. Mark mounting holes first**
Hold the perfboard in final orientation. Mark the four corner mounting holes. Do not solder any component over these holes.

**2. Solder the ESP32 DevKitC-32 (microcontroller) female headers**
- Place both 19-pin strips at the correct column spacing to match your ESP32's pin width
- Tack one pin at each end of each strip, verify alignment and parallelism before soldering all pins
- Solder all 38 pins

**3. Solder the BME280 (temp/pressure sensor) 4-pin female header**
- Place at rows 3, columns C–F
- Solder all 4 pins

**4. Solder the BH1750 (light sensor) 5-pin female header**
- Place at row 4, columns C–G — **VCC, GND, SCL, SDA, ADDR**, in the module's own pin order (confirm against the physical BH1750 before soldering; GY-302 boards are not all ordered identically)
- Verify column positions match where bridges will run
- Solder all 5 pins

**5. Solder wire bridges**
- Cut wire segments to length — keep short and routed cleanly
- Strip and tin each end before soldering
- Solder all bridges on the back of the board
- Tie BH1750 ADDR to GND with a black wire

**6. Continuity checks — do not skip**

**Moved to `bench-test-plan.md` (2026-09-21).** The full procedure — meter prep and probing technique, power-rail isolation, the nine `wiring.md` continuity checks plus two shared-rail integrity checks, signal isolation, the 36-pair adjacent-pad sweep, the pin 18 confirmation, and a failure-triage table — lives there as a single runnable worksheet with result columns, rather than split between this doc's assembly sequence and the bench.

Run `bench-test-plan.md` Sections 0–6 now, with nothing inserted, then return here for step 7.

**Do not power on until all continuity checks pass.**

**7. Insert components and attach standoffs**
- Insert the ESP32 DevKitC-32 (microcontroller) into the two 19-pin header strips — press firmly and evenly
- Insert the BME280 (temp/pressure sensor) into its 4-pin header
- Insert the BH1750 (light sensor) into its header — confirm ADDR pin is tied to GND
- Attach M3 10mm brass standoffs to the four corner mounting holes

---

## After Assembly

Power the board via USB and confirm all sensors reading correctly in HA:
- Temperature, humidity, and pressure from the BME280
- Illuminance from the BH1750
- Heartbeat appearing in log dashboard

If readings are absent or wrong, recheck wire bridges with a multimeter before troubleshooting firmware. The firmware does not change — only the physical connections.

Proceed to `mounting.md`.
