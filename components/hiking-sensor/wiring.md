# Hiking Monitor — Breadboard Wiring Reference
**Component:** hiking-monitor
**Purpose:** Complete wiring reference for the ESP32 breadboard prototype.

---

## Before Wiring

**ESP32 pin label orientation:** ESP32 DevKit pin labels face **down** when the board is inserted in a breadboard — the text is on the underside. Mark key GPIO rows with masking tape labels on the breadboard before wiring to avoid pin confusion.

Rows to label: GPIO4, GPIO5, GPIO16, GPIO17, GPIO18, GPIO21, GPIO22, GPIO23, GPIO32, GPIO35

GPIO32 note: configured as INPUT (no pull-up or pull-down) — the dock detect voltage divider provides defined state.

Copy `components/garage-radar/ESP32pins.png` to this directory for reference during wiring.

---

## GPIO Assignment Summary

| GPIO | Function | Component |
|---|---|---|
| GPIO4  | BUSY (input) | E-ink display |
| GPIO5  | SPI CS (active-low) | E-ink display |
| GPIO16 | RST (active-low reset) | E-ink display |
| GPIO17 | DC (data/command select) | E-ink display |
| GPIO18 | SPI CLK | E-ink display (VSPI) |
| GPIO21 | I2C SDA | BME280 + LTR-390 (shared) |
| GPIO22 | I2C SCL | BME280 + LTR-390 (shared) |
| GPIO23 | SPI MOSI / DIN | E-ink display (VSPI) |
| GPIO32 | Dock detect (divider midpoint, INPUT) | TP4056 IN+ → 68kΩ → midpoint → 100kΩ → GND |
| GPIO35 | Battery ADC (input-only) | Voltage divider midpoint |

---

## BME280 (GY-BME280) Wiring

| BME280 Pin | ESP32 Pin | Notes |
|---|---|---|
| VCC | 3.3V | The GY-BME280 has an onboard voltage regulator — connect to 3.3V, not 5V/VIN |
| GND | GND | |
| SDA | GPIO21 | I2C data — shared with LTR-390 |
| SCL | GPIO22 | I2C clock — shared with LTR-390 |

I2C address: 0x76 (SDO/CSB pin is tied to GND on GY-BME280 breakout).

---

## LTR-390 UV Sensor Wiring

| LTR-390 Pin | ESP32 Pin | Notes |
|---|---|---|
| VIN | 3.3V | Adafruit breakout has onboard 3.3V regulator — VIN accepts 3.3V directly |
| GND | GND | |
| SDA | GPIO21 | I2C data — shared with BME280 |
| SCL | GPIO22 | I2C clock — shared with BME280 |
| INT | (not connected) | Interrupt pin — not used |

I2C address: 0x53 (fixed — no configurable address pin).
No I2C address conflict with BME280 (0x76 ≠ 0x53).

**LTR-390 breadboard preparation:** The Adafruit LTR-390 (#4831) has STEMMA QT / Qwiic connectors, not standard 0.1" headers. Before breadboard use, solder standard 0.1" male header pins to the through-hole pads on the breakout board. The through-holes are labeled: VIN, GND, SDA, SCL, INT. Solder a 4-pin or 5-pin header strip to VIN/GND/SDA/SCL (INT is optional).

**LTR-390 placement:** Must face open sky during hikes. Position on breadboard near one edge. In the final enclosure it mounts on the top face. During bench testing, point at a sunlit window or outside to confirm UV readings change.

---

## Waveshare 2.13" E-Ink Display (V4, SSD1680) Wiring

The Waveshare V4 HAT is designed for a Raspberry Pi 40-pin header. For the ESP32, wire directly to the display's SPI + control pins using the FPC connector or via the HAT's pin header, connecting individual wires to the ESP32 breadboard.

**Use the labeled connector — not the 40-pin Pi header.**

The HAT has a connector with pre-attached color wires, each labeled. Connect each wire directly to the corresponding ESP32 breadboard row:

| Wire color | Label | ESP32 pin     |
|---|---|---------------|
| Grey | VCC | 3.3V          |
| Brown | GND | GND           |
| Blue | DIN | GPIO23 pin 37 |
| Yellow | CLK | GPIO18 pin 30 |
| Orange | CS | GPIO5 pin 29  |
| Green | DC | GPIO17 pin 28 |
| White | RST | GPIO16 pin27  |
| Purple | BUSY | GPIO4 pin 26  |

**Notes:**
- Display operates at 3.3V logic — no level shifting needed with ESP32.
- Keep wires short and tidy — SPI signals can be noise-sensitive at breadboard distances.
- The 40-pin Pi GPIO header on the HAT is not used.

---

## Dock Detect Wiring (GPIO32)

TP4056 IN+ (USB VBUS) is divided down to a safe GPIO level. Measured values: 0.47V (USB absent), 5.1V (USB present).

```
TP4056 IN+ ──── R3 (68kΩ) ──┬──── R4 (100kΩ) ──── GND
                             │
                         GPIO32 (INPUT, no pull)
```

After divider:
- USB absent: 0.47V × 100/(68+100) ≈ **0.28V → LOW** (field mode)
- USB present: 5.1V × 100/(68+100) ≈ **3.04V → HIGH** (docked/charging)

| Connection | Notes |
|---|---|
| TP4056 IN+ → R3 (68kΩ) → midpoint | Top half of divider |
| Midpoint → R4 (100kΩ) → GND | Bottom half; ensures LOW when IN+ absent |
| Midpoint → GPIO32 | No pull-up or pull-down — divider provides defined state |

On breadboard: R3 and R4 are through-hole resistors placed in the breadboard. Run a jumper from the TP4056 IN+ pin to R3, a jumper from R4 to GND rail, and a jumper from the midpoint to the GPIO32 breadboard row.

---

## Battery Voltage Divider Wiring

Divides LiPo voltage (3.5–4.2V) to fit ESP32 ADC range (0–3.9V at 11dB attenuation).
Using two equal resistors: R1 = 100kΩ (top), R2 = 100kΩ (bottom) → 2:1 divider.
Midpoint voltage = Vbatt / 2. ESPHome `filters: - multiply: 2.0` restores actual voltage.

```
TP4056 5V out (or LiPo+) ──── R1 (100kΩ) ──┬── R2 (100kΩ) ──── GND
                                             │
                                          GPIO35 (ADC input)
```

**Notes:**
- During breadboard testing without LiPo connected: wire the divider from the 3.3V rail instead of battery+ as a placeholder. Reads ~1.65V (scaled to ~3.3V in ESPHome). Replace with actual battery+ when power system is integrated in Step 8.
- High-value resistors (100kΩ) minimize current draw — total draw from divider is only ~40µA at 4V (3.7V / 200kΩ). Acceptable for battery-powered use.
- GPIO35 is an input-only pin — do not drive it as output. ADC use only.

---

## Power (Breadboard Phase — Steps 4–7)

Power ESP32 via USB-C cable from PC during all breadboard testing (Steps 4–7). Do NOT connect LiPo until Step 8 (power system integration with polarity verification).

Power wiring for Steps 4–7:
- USB-C → ESP32 USB-C port (powers ESP32 from PC)
- Breadboard power rails: 3.3V from ESP32 3.3V pin → red rail; GND from ESP32 GND → blue rail

---

## I2C Bus Notes

Both BME280 and LTR-390 share the same I2C bus (GPIO21 SDA, GPIO22 SCL). This is supported — each device has a unique I2C address. The GY-BME280 and LTR-390 breakout boards include onboard pull-up resistors on SDA/SCL. No external pull-ups needed (two sets of pull-ups on a shared bus is acceptable at these speeds).

Enable `scan: true` in the ESPHome `i2c:` block during initial testing to confirm both devices are detected. Confirm in the ESPHome log:
```
[I][i2c.arduino:069]: Found i2c device at address 0x53  ← LTR-390
[I][i2c.arduino:069]: Found i2c device at address 0x76  ← BME280
```

---

## Schematic Overview

```
              ┌───────────────────────────────────┐
              │     ESP32 DevKitC-32 (38-pin)     │
              │                                   │
3.3V ─────────┤ 3.3V                    GPIO4 ────┼──── BUSY (e-ink)
GND  ─────────┤ GND             GPIO5/SPI_CS ────┼──── CS (e-ink)
              │                        GPIO16 ────┼──── RST (e-ink)
BME280 SDA ───┤ GPIO21 (I2C SDA)       GPIO17 ────┼──── DC (e-ink)
LTR-390 SDA──┘                        GPIO18 ────┼──── CLK (e-ink)
              │                        GPIO23 ────┼──── DIN (e-ink)
BME280 SCL ───┤ GPIO22 (I2C SCL)
LTR-390 SCL──┘                         GPIO32 ────┼──── R3/R4 dock divider midpoint (TP4056 IN+)

              │                        GPIO35 ────┼──── R1/R2 divider midpoint
              └───────────────────────────────────┘
                                                    R1 (100kΩ) → Vbatt+
                                                    R2 (100kΩ) → GND
```
