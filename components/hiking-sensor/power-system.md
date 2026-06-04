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

## Step 4 — USB Charging

**Confirmed (2026-06-04):** Connecting Micro USB to the TP4056 module's USB port lights the red LED — charging in progress. LED turns off or blue when charge complete (exact behavior depends on module revision).

---

## Step 5 — Switch to Battery Power

**STATUS: COMPLETE (2026-06-04)**

Device running from LiPo without USB. Confirmed readings:

| Measurement | Expected | Actual |
|---|---|---|
| BAT+ to GND | 3.5–4.2V | 3.84V |
| VOUT+ to GND | ~5V | 5.7V (boost converters run slightly high — acceptable) |
| ESP32 3.3V to GND | ~3.3V | 3.35V |
| Voltage divider midpoint to GND | ~1.92V | 1.89V |
| `battery_v` in MQTT | ~3.84V | 3.85V ✓ |

Full MQTT data payload confirmed:
```json
{"component":"hiking-monitor","ts":"2026-06-04T18:11:48Z","lat":null,"lon":null,"temp_f":95.8,"humidity_pct":18.2,"pressure_hpa":926.9,"uv_index":0.01,"battery_v":3.85,"rssi_dbm":-37}
```

---

## Solar Panel (SUNYIMA 5.5V 80mA — Backpacking Only)

The SUNYIMA panel (Bag 6) is not needed for day hikes — the 1100mAh LiPo is sufficient.
Solar charging is only relevant for multi-day backpacking trips where the LiPo cannot be
recharged via USB overnight.

**Perfboard build (Step 14):** The SUNYIMA panel has bare wire leads (no connector). JST connectors are on hand. Solder a JST male plug to the panel leads and a JST female receptacle on the perfboard with leads going to the TP4056 IN+ and IN− pads. Confirm pitch and use it consistently for both ends. Verify polarity before soldering — mark + and − on both ends.

**Breadboard wiring (when needed):**

```
SUNYIMA panel + lead → IN+ pad on TP4056 module
SUNYIMA panel - lead → IN− pad on TP4056 module
```

**Confirmed (2026-06-04):** 60×60mm panel tested in sunlight — 5.5V under 100Ω load (~55mA), consistent with rated 80mA. This is loaded output, not open-circuit — the panel will maintain ~5.5V when connected to the TP4056 IN+. Well within the 8V input limit. No series diode needed.

**Before connecting the panel:**
1. Set multimeter to DC voltage (10V range)
2. Point panel at direct sunlight
3. Confirm open-circuit voltage is below 8V (TP4056 input limit)
4. Connect + lead to IN+, − lead to IN− on the module

**JST connector:** The SUNYIMA panel has a JST connector. Verify polarity matches the module's `Solar+`/`Solar-` terminals with a multimeter before connecting — same procedure as the LiPo polarity check.

**Enclosure note:** The solar JST port must be accessible from outside the enclosure. Account for this in the enclosure design (Step 15).

---

## What to Report Back

- LiPo JST polarity verified before connection: yes/no
- Charge LED behavior: charging (red) → full (blue): yes/no
- Device runs from LiPo without USB: yes/no
- `battery_v` reading in MQTT: actual value (V)
- Expected: 3.7–4.2V for a charged LiPo
