# Front Porch Temp Sensor — Wiring Reference (Step 4)

Breadboard prototype wiring for:
- **ESP32 DevKitC-32** (microcontroller)
- **BME280** (temperature / humidity / pressure sensor)
- **BH1750** (light / illuminance sensor)

---

## Wire Color Conventions

| Color | Signal |
|---|---|
| Red | 3.3V power |
| Black | GND |
| Blue | SDA (I2C data) |
| Yellow | SCL (I2C clock) |

Use these colors consistently — they make the wiring easy to trace and debug.

---

## Pin Orientation Warning

**ESP32 DevKitC-32 (microcontroller) GPIO labels face down when inserted in a breadboard.**
The silk-screened labels are on the underside and are not visible from above.
Before wiring, mark your key GPIO rows with masking tape labels so you can
identify them without pulling the board. Reference `ESP32pins.png` (see below).

---

## ESP32 DevKitC-32 (microcontroller) → BME280 (temp/humidity/pressure sensor)

| BME280 Pin | ESP32 DevKitC-32 Pin | Wire Color | Notes |
|---|---|---|---|
| VCC | 3.3V | Red | Use 3.3V — **not VIN/5V** despite the "5V" label on the BME280 module. The Podazz BME280 has an onboard regulator but must be powered from 3.3V on this board. |
| GND | GND | Black | |
| SDA | GPIO21 | Blue | Default I2C SDA |
| SCL | GPIO22 | Yellow | Default I2C SCL |

## ESP32 DevKitC-32 (microcontroller) → BH1750 (light sensor)

| BH1750 Pin | ESP32 DevKitC-32 Pin | Wire Color | Notes |
|---|---|---|---|
| VCC | 3.3V | Red | |
| GND | GND | Black | |
| SDA | GPIO21 | Blue | Shared I2C bus — connect to the same breadboard rail as BME280 SDA |
| SCL | GPIO22 | Yellow | Shared I2C bus — connect to the same breadboard rail as BME280 SCL |
| ADDR | GND | Black | Ties ADDR low, sets BH1750 I2C address to 0x23 |

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

Both the BME280 (temp/humidity/pressure sensor) and BH1750 (light sensor) share
the I2C bus on the ESP32 DevKitC-32. No level shifter needed — both breakouts
include onboard pull-up resistors and operate at 3.3V logic.

---

## Breadboard Assembly Notes

1. Insert the ESP32 DevKitC-32 (microcontroller) straddling the center channel.
   It spans 19 pins per side on a standard 830-point breadboard.

2. Mark key GPIO rows with masking tape before connecting anything:
   - 3.3V row
   - GND row
   - GPIO21 row (SDA — shared by BME280 and BH1750)
   - GPIO22 row (SCL — shared by BME280 and BH1750)

3. Run a black wire GND bus rail and a red wire 3.3V bus rail along the breadboard
   edges. Connect both the BME280 (temp/humidity/pressure sensor) and BH1750
   (light sensor) power and ground to these rails.

4. Run blue wires from GPIO21 to both the BME280 and BH1750 SDA pins. Run yellow
   wires from GPIO22 to both SCL pins. All four land on the same two GPIO rows.

5. Tie the BH1750 (light sensor) ADDR pin to GND with a black wire (same GND rail).
   Do not leave it floating — a floating ADDR pin results in an unpredictable I2C address.

6. The BME280 (temp/humidity/pressure sensor) and BH1750 (light sensor) breakouts
   each have onboard pull-up resistors for SDA and SCL. No external pull-ups needed.

7. Power the ESP32 DevKitC-32 via USB-C for the prototype. The 3.3V rail is
   sufficient to power both breakouts at their typical current draw (<5mA combined).

---

## Pinout Reference

`ESP32pins.png` is in this directory for quick GPIO reference while wiring.

---

## Pre-Flash Checklist

Before flashing, verify visually:

- [ ] ESP32 DevKitC-32 (microcontroller) inserted correctly
- [ ] GPIO labels identified and rows marked with tape
- [ ] BME280 (temp/humidity/pressure sensor) VCC → 3.3V via red wire (not VIN)
- [ ] BME280 (temp/humidity/pressure sensor) GND → GND via black wire
- [ ] BME280 (temp/humidity/pressure sensor) SDA → GPIO21 via blue wire
- [ ] BME280 (temp/humidity/pressure sensor) SCL → GPIO22 via yellow wire
- [ ] BH1750 (light sensor) VCC → 3.3V via red wire
- [ ] BH1750 (light sensor) GND → GND via black wire
- [ ] BH1750 (light sensor) SDA → GPIO21 via blue wire (same rail as BME280 SDA)
- [ ] BH1750 (light sensor) SCL → GPIO22 via yellow wire (same rail as BME280 SCL)
- [ ] BH1750 (light sensor) ADDR → GND via black wire
- [ ] No bare wires touching adjacent rows
- [ ] USB-C cable connected to computer, not wall charger

---

## Next Step

Proceed to `flashing.md` (Step 5) — flash firmware and validate sensors.
