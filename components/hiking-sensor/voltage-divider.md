# Voltage Divider — Reference

## What It Is

A voltage divider takes an input voltage and produces a lower output voltage using two
resistors in series.

---

## Diagram

```
       ┌──── Top (V_in)
       │
      R1
       │
       ├──── Midpoint (V_out)
       │
      R2
       │
       └──── Bottom (GND)
```

The bottom is always GND (0V). That's what makes the math work — the two resistors
divide the voltage between V_in and 0V, and the midpoint lands somewhere in between.

---

## How It Works

Current flows from V_in through R1, then through R2 to GND. The output is tapped at
the midpoint between the two resistors. The bigger R2 is relative to R1, the more
voltage appears at the midpoint.

**Formula:**

```
V_out = V_in × R2 / (R1 + R2)
```

---

## Examples

**Equal resistors (R1=100kΩ, R2=100kΩ) — battery monitor divider:**
```
V_out = 3.8V × 100k / (100k + 100k) = 3.8V × 0.5 = 1.9V
```
Equal resistors always give exactly half the input voltage.

**Unequal resistors (R1=68kΩ, R2=100kΩ) — dock detect divider:**
```
V_out = 5.1V × 100k / (68k + 100k) = 5.1V × 0.595 = 3.04V
```
R2 is larger than R1, so more than half the voltage appears at the output.

---

## Why We Use Them in This Project

**Battery monitor (GPIO35):**
LiPo voltage (3.5–4.2V) is safe for the ESP32 ADC but we halve it for safety margin.
Equal 100kΩ+100kΩ resistors divide it in half. Firmware multiplies the reading by 2
to recover the real value.

**Dock detect (GPIO32):**
TP4056 IN+ swings to 5.1V when USB is connected — above the ESP32's 3.3V GPIO limit.
The 68kΩ+100kΩ divider brings it down to 3.04V, safe to read as HIGH. When USB is
absent, IN+ sits at 0.47V → midpoint ≈ 0.28V, read as LOW.

---

## Key Limitation

A voltage divider only works reliably when the load connected to V_out draws very
little current compared to the current flowing through R1+R2. High-value resistors
(100kΩ) keep the divider current low (~25µA at 4V), which is why we use them in
battery-powered designs.
