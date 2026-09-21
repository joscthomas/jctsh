# Back Patio Temp Sensor — Wiring Reference

Perfboard build wiring for:
- **ESP32 DevKitC-32** (microcontroller) — same board type/batch as `air-quality-monitor`'s; see `ESP32-project-pins.md` for that batch's known pin 18 GND anomaly (not used by this build)
- **BME280** (temperature / humidity / pressure sensor)
- **BH1750** (light / illuminance sensor)

Identical wiring to `front-porch-temp-sensor` — same hardware, same I2C bus. Going straight to perfboard (no breadboard prototyping stage) since this design is already proven.

**Every ESP32 DevKitC-32 (microcontroller) pin below is named by both its silkscreen label and its physical pin number** (e.g. "GPIO21, pin 33") — the silkscreen label alone is ambiguous while probing or counting pads, and on this board the labels face down once the board is seated (see Pin Orientation Warning). Pin numbers follow `ESP32-project-pins.md`'s orientation: **viewed from the top** (component side up, antenna at top), USB-C connector at bottom, left pin 1 and right pin 38 at the top — the same view `ESP32pins.png` uses, and the one the board is actually looked at in while wiring. (`esp32-pins-photo.jpg` shows the *underside*, where the labels are printed, so its left/right are mirrored against this — read labels from it, read sides from here.)

---

## Wire Color Conventions

| Color | Signal |
|---|---|
| Red | 3.3V power |
| Black | GND |
| Blue | SDA (I2C data) |
| Yellow | SCL (I2C clock) |

---

## Pin Orientation Warning

**ESP32 DevKitC-32 (microcontroller) GPIO labels face down when inserted in a breadboard/perfboard header.** The silk-screened labels are on the underside. Reference `ESP32pins.png` for quick GPIO lookup while wiring.

---

## ESP32 DevKitC-32 (microcontroller) Connections

Every wired pin on the microcontroller, one row each — the board-side view of the two sensor-side tables below. Only four of the board's 38 pins are used.

| ESP32 pin | Silkscreen | Side | Signal | Connects to | Wire color |
|---|---|---|---|---|---|
| 1 | 3V3 | Left | 3.3V power | BME280 VCC, BH1750 VCC | Red |
| 33 | GPIO21 | Right | I2C SDA | BME280 SDA, BH1750 SDA | Blue |
| 36 | GPIO22 | Right | I2C SCL | BME280 SCL, BH1750 SCL | Yellow |
| 38 | GND | Right | Ground | BME280 GND, BH1750 GND, BH1750 ADDR | Black |

**All other pins are unused and left unwired**, including:
- **Pin 18 (silkscreen GND, left side)** — **⛔ never use, for anything.** Not continuous with the GND rail on this board batch, and as of 2026-09-21 the likely reason is that it is not a ground pin at all but **GPIO11 (flash CMD), mis-silkscreened as GND** — a flash-bus pin in the same ⛔ class as GPIO6–10, where driving it would interfere with SPI flash access. Strong hypothesis, not directly confirmed; see `ESP32-project-pins.md`'s pin 18 note for the evidence and the scope test that would settle it. GND comes from pin 38 only.
- **Pin 19 (VIN/5V, left side)** — this build is powered over USB-C, so VIN is not wired.
- **Pin 14 (GND, left side) and pin 32 (GND, right side)** — functional GND pins, but unused here; pin 38 is the single GND tap for this build so every black wire lands on one pad group.

---

## ESP32 DevKitC-32 (microcontroller) → BME280 (temp/humidity/pressure sensor)

| BME280 Pin | ESP32 DevKitC-32 Pin | Wire Color | Notes |
|---|---|---|---|
| VCC | 3V3, pin 1 | Red | Use 3.3V (pin 1) — **not VIN/5V (pin 19)** even if the module is silkscreened "5V". |
| GND | GND, pin 38 | Black | Do not use pin 18 — see `ESP32-project-pins.md`'s pin 18 note (this board batch). |
| SDA | GPIO21, pin 33 | Blue | Default I2C SDA |
| SCL | GPIO22, pin 36 | Yellow | Default I2C SCL |

## ESP32 DevKitC-32 (microcontroller) → BH1750 (light sensor)

| BH1750 Pin | ESP32 DevKitC-32 Pin | Wire Color | Notes |
|---|---|---|---|
| VCC | 3V3, pin 1 | Red | |
| GND | GND, pin 38 | Black | |
| SDA | GPIO21, pin 33 | Blue | Shared I2C bus — same rail as BME280 SDA |
| SCL | GPIO22, pin 36 | Yellow | Shared I2C bus — same rail as BME280 SCL |
| ADDR | GND, pin 38 | Black | Ties ADDR low, sets BH1750 I2C address to 0x23 — **never leave floating** (unpredictable address) |

---

## Schematic

```
ESP32 DevKitC-32 (microcontroller)
┌──────────────────────┐
│      3V3 (pin 1)     ├──┬── (red) ────── BME280 (temp/humidity/pressure) VCC
│                      │  └── (red) ────── BH1750 (light sensor) VCC
│      GND (pin 38)    ├──┬── (black) ─── BME280 (temp/humidity/pressure) GND
│                      │  ├── (black) ─── BH1750 (light sensor) GND
│                      │  └── (black) ─── BH1750 (light sensor) ADDR
│   GPIO21 (pin 33)    ├──┬── (blue) ──── BME280 (temp/humidity/pressure) SDA
│                      │  └── (blue) ──── BH1750 (light sensor) SDA
│   GPIO22 (pin 36)    ├──┬── (yellow) ── BME280 (temp/humidity/pressure) SCL
│                      │  └── (yellow) ── BH1750 (light sensor) SCL
└──────────────────────┘
```

Both sensors share the I2C bus. No level shifter needed — both breakouts include onboard pull-up resistors and operate at 3.3V logic.

---

## Pre-Flash Checklist

Before flashing, verify visually:

- [ ] ESP32 DevKitC-32 (microcontroller) inserted correctly
- [ ] BME280 VCC → 3V3, pin 1 via red wire (not VIN, pin 19)
- [ ] BME280 GND → GND, pin 38 via black wire
- [ ] BME280 SDA → GPIO21, pin 33 via blue wire
- [ ] BME280 SCL → GPIO22, pin 36 via yellow wire
- [ ] BH1750 VCC → 3V3, pin 1 via red wire
- [ ] BH1750 GND → GND, pin 38 via black wire
- [ ] BH1750 SDA → GPIO21, pin 33 via blue wire (same rail as BME280 SDA)
- [ ] BH1750 SCL → GPIO22, pin 36 via yellow wire (same rail as BME280 SCL)
- [ ] BH1750 ADDR → GND, pin 38 via black wire
- [ ] No bare wires touching adjacent rows/pads
- [ ] Nothing wired to pin 18 as a GND tap (confirmed non-functional on this board batch)
- [ ] USB-C cable connected to computer, not wall charger, for first flash

---

## Next Step

Proceed to `perfboard-layout.md` — this build goes directly to perfboard, no breadboard prototyping stage.
