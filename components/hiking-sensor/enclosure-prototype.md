# Hiking Monitor — Field Prototype Enclosure

A two-board sandwich for walking around with the device before committing to a 3D-printed case. No permanent modifications to the main perfboard.

---

## Concept

```
┌─────────────────────────────┐  ← Top perfboard
│  [display face-up]          │    e-ink hot-glued or taped
│  [cutout: LTR-390]          │    cutouts above LTR-390 and BME280
│  [cutout: BME280]           │
└──────┬──────────────┬───────┘
       │  standoffs   │          ← cavity (~35–40mm)
       │              │            TP4056 + LiPo sit here
       │              │            velcro or foam tape to main board
       │   [TP4056]   │
       │   [LiPo  ]   │
┌──────┴──────────────┴───────┐  ← Main perfboard (existing)
│  ESP32, BME280, LTR-390,    │    all wiring and solder joints
│  voltage dividers, headers  │    face DOWN (underside)
└─────────────────────────────┘
```

Solder joints face down and are never covered. The cavity between the boards houses the power components. The display faces up on the top board.

---

## Materials

- Second perfboard — same size as main board or slightly larger
- 4× M3 standoffs — measure height before purchasing (see Measurements below)
- 4× M3 screws (top and bottom)
- Hot glue or double-sided foam tape — display and power components
- Short extension harness or slack in existing harness — display wires must reach from top board down to main board header

---

## Key Measurements (take before buying standoffs)

1. **Tallest component above main board surface** — measure the ESP32 header pins or sensor headers; likely 12–15mm
2. **TP4056 module thickness** — approximately 5mm
3. **LiPo battery thickness** — measure your EEMB 1100mAh pack
4. **Total cavity needed** = tallest component + TP4056 + LiPo + ~5mm clearance
5. **Display harness length** — confirm the 8-wire harness reaches from the top board surface down to the main board header at the chosen standoff height; extend if needed

Standoff height = total cavity needed (typically 35–40mm).

---

## Layout Notes

**Top perfboard:**
- E-ink display centered and hot-glued face-up
- Cutout above LTR-390 position (UV sensor must see open sky)
- Cutout above BME280 position (needs airflow for accurate temperature)
- Display harness routes through a gap at the board edge or a slot cutout

**Cavity (between boards):**
- TP4056 velcroed or foam-taped to main board surface, micro USB port facing out one side of the stack
- LiPo alongside or on top of TP4056; JST connects to TP4056 BAT terminals
- Keep TP4056 micro USB and ESP32 USB-C accessible from the sides

**Slide switch:**
- Currently on a 2-pin header; extend with a short harness if the header is not reachable from the side of the stack

---

## What This Prototype Validates

- Carrying comfort and form factor before 3D printing
- Display readability in sunlight
- Switch and charging port accessibility
- LTR-390 UV readings with sensor exposed through cutout
- BME280 temperature accuracy with airflow through cutout
- Battery life in field conditions
