# Back Patio Temp Sensor — Physical Mounting

Mount the completed perfboard on the back patio. Run after perfboard transfer is complete and all continuity checks pass.

---

## Mounting Constraints

- **BME280 (temp/pressure sensor) and BH1750 (light sensor) must face open air.** Board mounts with sensors facing up or outward — never enclosed.
- **Keep sensors out of direct sun.** Direct sunlight biases temperature readings. Confirmed 2026-09-21 (Joseph): the back patio has genuine overhang coverage — same siting profile as front-porch-temp-sensor.
- **Keep sensors away from rain splash.** No weather sealing on the perfboard — confirmed the overhang keeps rain off this mount point.
- **Locate near an outlet.** Power is USB-C from a wall outlet. Confirmed 2026-09-21 (Joseph): outlet is within reach at the mount point (P2, `house-lot-coordinates.md`).

---

## Materials

| Item | Qty |
|---|---|
| M3 brass male-female standoffs, 10mm (already on perfboard from perfboard-layout.md) | 4 |
| M3 screws for wall attachment | 4 |
| USB-C cable (sufficient length to reach outlet) | 1 |
| USB power adapter (5V, ≥500mA) | 1 |
| Pencil and drill for wall pilot holes | — |

---

## Mounting Procedure

**1. Choose final location**
- At the outlet mount point (P2: 32.4614183, -111.1184405 — see `house-lot-coordinates.md`), under the patio overhang
- Sensors facing outward or upward toward ambient air
- USB cable can reach the outlet without stretching

**2. Mark pilot holes**
- Hold board against mounting surface in final orientation
- Mark four M3 hole positions (board corners)
- Drill pilot holes appropriate for wall material

**3. Attach standoffs to wall**
- Drive M3 screws through wall into pilot holes, threading into the male end of each standoff
- Standoffs space the board away from the surface — do not mount board flush

**4. Mount the board**
- Seat the board onto the four standoffs
- Thread M3 nuts onto standoff tops to secure the board

**5. Route USB cable**
- Plug USB-C into the ESP32 DevKitC-32 (microcontroller) port
- Route cable to outlet — use cable clips or channel if needed for a clean run
- Plug into USB power adapter at the outlet

---

## Power-On Verification

After mounting and powering:

- [ ] HA Overview page shows Temperature, Humidity, Pressure, Illuminance updating within ~60 seconds
- [ ] Log dashboard shows MQTT connected message from this boot
- [ ] Heartbeat appears in log dashboard within 5 minutes
- [ ] `back-patio-temp-sensor` listed as active in watchdog message

If readings are absent, recheck USB power before troubleshooting. The firmware and wiring do not change during mounting.

---

## Location Notes

Known ahead of mounting (from Planning, CARD-0219):

| Item | Value |
|---|---|
| Mount point | Outlet (P2), `house-lot-coordinates.md`: 32.4614183, -111.1184405 |
| Patio geometry | SW corner (P1) → outlet (P2): 16 ft east. Outlet (P2) → SE corner (P3): 12 ft east. Patio depth (H1 to wall): 12 ft. |

*(Fill in after installation:)*

| Item | Value |
|---|---|
| Mounting surface | |
| Height above grade | |
| Facing direction | |
| Cable length needed | |

---

Proceed to `README.md`.
