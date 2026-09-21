# Back Patio Temp Sensor — Wiring Reference

Perfboard build wiring for:
- **ESP32 DevKitC-32** (microcontroller) — same board type/batch as `air-quality-monitor`'s; see `ESP32-project-pins.md` for that batch's known pin 18 GND anomaly (not used by this build)
- **BME280** (temperature / humidity / pressure sensor)
- **BH1750** (light / illuminance sensor)

Identical wiring to `front-porch-temp-sensor` — same hardware, same I2C bus. Going straight to perfboard (no breadboard prototyping stage) since this design is already proven.

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

## ESP32 DevKitC-32 (microcontroller) → BME280 (temp/humidity/pressure sensor)

| BME280 Pin | ESP32 DevKitC-32 Pin | Wire Color | Notes |
|---|---|---|---|
| VCC | 3.3V | Red | Use 3.3V — **not VIN/5V** even if the module is silkscreened "5V". |
| GND | GND (pin 38) | Black | Do not use pin 18 — see `ESP32-project-pins.md`'s pin 18 note (this board batch). |
| SDA | GPIO21 | Blue | Default I2C SDA |
| SCL | GPIO22 | Yellow | Default I2C SCL |

## ESP32 DevKitC-32 (microcontroller) → BH1750 (light sensor)

| BH1750 Pin | ESP32 DevKitC-32 Pin | Wire Color | Notes |
|---|---|---|---|
| VCC | 3.3V | Red | |
| GND | GND (pin 38) | Black | |
| SDA | GPIO21 | Blue | Shared I2C bus — same rail as BME280 SDA |
| SCL | GPIO22 | Yellow | Shared I2C bus — same rail as BME280 SCL |
| ADDR | GND (pin 38) | Black | Ties ADDR low, sets BH1750 I2C address to 0x23 — **never leave floating** (unpredictable address) |

---

## Schematic

```
ESP32 DevKitC-32 (microcontroller)
┌─────────────────┐
│           3.3V  ├──┬── (red) ────── BME280 (temp/humidity/pressure) VCC
│                 │  └── (red) ────── BH1750 (light sensor) VCC
│            GND  ├──┬── (black) ─── BME280 (temp/humidity/pressure) GND
│                 │  ├── (black) ─── BH1750 (light sensor) GND
│                 │  └── (black) ─── BH1750 (light sensor) ADDR
│          GPIO21 ├──┬── (blue) ──── BME280 (temp/humidity/pressure) SDA
│                 │  └── (blue) ──── BH1750 (light sensor) SDA
│          GPIO22 ├──┬── (yellow) ── BME280 (temp/humidity/pressure) SCL
│                 │  └── (yellow) ── BH1750 (light sensor) SCL
└─────────────────┘
```

Both sensors share the I2C bus. No level shifter needed — both breakouts include onboard pull-up resistors and operate at 3.3V logic.

---

## Pre-Flash Checklist

Before flashing, verify visually:

- [ ] ESP32 DevKitC-32 (microcontroller) inserted correctly
- [ ] BME280 VCC → 3.3V via red wire (not VIN)
- [ ] BME280 GND → GND (pin 38) via black wire
- [ ] BME280 SDA → GPIO21 via blue wire
- [ ] BME280 SCL → GPIO22 via yellow wire
- [ ] BH1750 VCC → 3.3V via red wire
- [ ] BH1750 GND → GND (pin 38) via black wire
- [ ] BH1750 SDA → GPIO21 via blue wire (same rail as BME280 SDA)
- [ ] BH1750 SCL → GPIO22 via yellow wire (same rail as BME280 SCL)
- [ ] BH1750 ADDR → GND via black wire
- [ ] No bare wires touching adjacent rows/pads
- [ ] Nothing wired to pin 18 as a GND tap (confirmed non-functional on this board batch)
- [ ] USB-C cable connected to computer, not wall charger, for first flash

---

## Next Step

Proceed to `perfboard-layout.md` — this build goes directly to perfboard, no breadboard prototyping stage.
