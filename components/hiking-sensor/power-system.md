# Hiking Monitor — Power System (Step 8)

## Overview

The power system consists of three elements:
- **EEMB 1100mAh 3.7V LiPo** (Bag 7) — primary energy storage
- **TP4056+boost combined module** (Bag 8) — charges LiPo from USB or solar; boosts 3.7V → 5V for ESP32 VIN
- **Voltage divider** (100kΩ + 100kΩ on breadboard) — scales LiPo voltage to ESP32 ADC range

---

## TP4056+Boost Module Terminals

Confirmed terminal layout on this module:

- **Micro-USB port** — USB charger input (5V). No separate solder pads — the port itself is the connection.
- **IN+ / IN-** — on either side of the micro-USB port — solar/auxiliary charging input. SUNYIMA panel connects here (see Solar section below).
- **VOUT+ / VOUT-** — 5V boost output → ESP32 VIN and GND.
- **BAT+ / BAT-** — LiPo JST battery connection.

| Terminal | Function |
|---|---|
| Micro-USB | USB charger input — plug standard USB charger here to charge the LiPo |
| `IN+` / `IN-` | Solar/auxiliary input — SUNYIMA 5.5V 80mA panel (Bag 6) connects here |
| `VOUT+` / `VOUT-` | 5V boost output → ESP32 VIN / GND |
| `BAT+` / `BAT-` | LiPo JST connection — battery positive and negative |

> **Critical:** `VOUT+` is a fixed regulated 5V regardless of battery charge state — useless for monitoring.
> The voltage divider must connect to **`BAT+`**, not `VOUT+`, to track actual LiPo voltage (3.5–4.2V).

**Charge indicator LEDs (typical for this module):**
- Red LED on: charging in progress
- Blue LED on: charge complete
- (LED color may vary by module revision — verify with your specific unit)

---

## Step 1 — Polarity Verification (Do Before Connecting LiPo)

This module has solder pads, not a JST connector on the battery side. The pads are labeled
`BAT+` and `BAT-`, so polarity is confirmed by verifying the LiPo leads directly:

1. Set multimeter to DC voltage (10V range)
2. Red probe on LiPo red wire, black probe on LiPo black wire
3. Confirm reading is positive (~3.7–4.2V for a charged cell)
4. Connect red wire to `BAT+` pad, black wire to `BAT-` pad

**Confirmed (2026-06-04):** Red probe on red wire reads +3.88V → red = positive. Connect red → `BAT+`, black → `BAT-`.

---

## Step 2 — Voltage Divider Rewire

During Steps 4–7, the voltage divider was temporarily connected to the ESP32 3.3V rail
as a placeholder (reads ~3.3V in ESPHome — not useful for battery monitoring).

For Step 8, rewire R1 from the 3.3V rail to the TP4056 `BAT+` terminal:

```
TP4056 BAT+ wire lead ──── R1 (100kΩ) ──┬──── R2 (100kΩ) ──── GND rail
                                         │
                                      GPIO35 (ADC input)
```

**Physical breadboard wiring — three rows:**

| Row | What connects here |
|---|---|
| Row A | TP4056 `BAT+` wire lead + R1 top leg |
| Row B (midpoint) | R1 bottom leg + R2 top leg + jumper wire to GPIO35 |
| GND rail | R2 bottom leg |

R1 bridges from the `BAT+` wire coming off the module to the midpoint node.
R2 bridges from the midpoint node to GND.
GPIO35 taps the midpoint — reads half the battery voltage; ESPHome multiplies by 2.

**Expected reading after rewire:**
- LiPo fully charged: ~4.2V → ADC reads ~2.1V → ESPHome × 2 = ~4.2V
- LiPo nominal: ~3.7V → ADC reads ~1.85V → ESPHome × 2 = ~3.7V
- LiPo low: ~3.5V → ADC reads ~1.75V → ESPHome × 2 = ~3.5V

---

## Step 3 — Breadboard Assembly

With polarity confirmed and voltage divider rewired:

1. Place TP4056+boost module on breadboard (or connect via jumper wires)
2. Wire `BAT+` → voltage divider R1 top (and to LiPo JST positive after polarity confirmed)
3. Wire `BAT-` → GND rail
4. Wire `OUT+` → ESP32 VIN
5. Wire `OUT-` → ESP32 GND (already on GND rail)
6. Connect LiPo JST to module JST header (polarity confirmed in Step 1)

---

## Step 4 — Initial Charge and Power-On

1. Connect Micro USB to the TP4056 module's USB port (not the ESP32 USB-C)
2. Confirm charge LED lights (red = charging)
3. The ESP32 powers on from the 5V boost output — confirm display activates and MQTT connects
4. Let charge complete (blue LED) if battery was low

---

## Step 5 — Switch to Battery Power

1. Disconnect Micro USB from TP4056 module
2. Disconnect USB-C from ESP32 (if still connected)
3. Confirm ESP32 continues running from LiPo via boost output
4. Check `battery_v` in MQTT data topic — expect 3.7–4.2V for a charged LiPo

If `battery_v` reads 0V: voltage divider R1 is not connected to B+.
If `battery_v` reads ~6–8V: divider is connected to OUT+ (5V boost) instead of B+ — rewire to B+.
If `battery_v` reads ~3.3V: divider is still on the 3.3V rail placeholder — rewire to B+.

---

## Solar Panel (SUNYIMA 5.5V 80mA — Backpacking Only)

The SUNYIMA panel (Bag 6) is not needed for day hikes — the 1100mAh LiPo is sufficient.
Solar charging is only relevant for multi-day backpacking trips where the LiPo cannot be
recharged via USB overnight.

**Wiring (when needed):**

```
SUNYIMA panel + lead → Solar+ terminal on TP4056 module
SUNYIMA panel - lead → Solar- terminal on TP4056 module
```

**Before connecting the panel, verify its output voltage under load:**
1. Set multimeter to DC voltage (10V range)
2. Point panel at direct sunlight
3. Measure across the panel leads under load (connect a ~100Ω resistor across the leads while measuring)
4. Target: 4.5–6V under load. The TP4056 input accepts up to 8V but is designed for 5V sources.
5. If open-circuit voltage is significantly above 6V, add a small Schottky diode in series (IN5819) to drop ~0.3V and protect the module

**JST connector:** The SUNYIMA panel has a JST connector. Verify polarity matches the module's `Solar+`/`Solar-` terminals with a multimeter before connecting — same procedure as the LiPo polarity check.

**Enclosure note:** The solar JST port must be accessible from outside the enclosure. Account for this in the enclosure design (Step 15).

---

## What to Report Back

- LiPo JST polarity verified before connection: yes/no
- Charge LED behavior: charging (red) → full (blue): yes/no
- Device runs from LiPo without USB: yes/no
- `battery_v` reading in MQTT: actual value (V)
- Expected: 3.7–4.2V for a charged LiPo
