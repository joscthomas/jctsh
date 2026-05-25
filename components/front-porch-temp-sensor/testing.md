# Front Porch Temp Sensor — End-to-End Test (Step 11)

Run all tests with the breadboard prototype before transferring to perfboard.

**Automation logic summary:**
- **Alert:** temp >= threshold AND time between 6am–10pm → notify both phones
- **Reminder:** 15 minutes after alert, fires once (mode: single)
- **Dropping:** temp < threshold AND time between 6am–10pm → notify both phones

---

## 1. Sensor Validation

Confirm all sensor values updating every ~60 seconds in HA Overview page.

- [x] Temperature — plausible (~70–115°F in Tucson)
- [x] Pressure — ~13.4–13.5 psi (~925–930 hPa for Tucson elevation)
- [x] Illuminance — changes with ambient light
- [x] Humidity — shows Unknown (expected with BMP280 substitution)

---

## 2. Log Dashboard Check

Open `http://raspberrypi.local/` (Basic Auth, user: `jctsh`).

- [x] Log messages visible under `front-porch-temp-sensor`
- [x] MQTT connected message present from most recent boot

---

## 3. Heartbeat Check

- [x] Heartbeat appearing every 5 minutes in log dashboard
- [x] Heartbeat includes uptime, RSSI, and temperature

---

## 4. Watchdog Check

- [x] `front-porch-temp-sensor` listed as active in the core watchdog message

---

## 5. Lux Sensor Test

- [x] Cover the BH1750 (light sensor) — illuminance drops in HA
- [x] Uncover — illuminance rises

---

## 6. Alert Suppression — Outside Time Window

*Optional — run after 10pm or before 6am if convenient. Otherwise skip.*

1. Lower threshold below current temperature
2. Confirm no alert fires outside the 6am–10pm window

- [ ] No alert received outside time window
- [ ] Restore threshold to 80°F

---

## 7. Full Alert Test

1. Raise threshold to 95°F (forces a crossing when lowered)
2. Lower threshold to 75°F — both phones should receive alert within 60 seconds:
   - Title: "Front Porch Temp Alert"
   - Message includes current temperature

- [x] Alert received on both phones

---

## 8. Reminder Test

1. Leave conditions unchanged after alert fires in step 7
2. Wait 15 minutes
3. Both phones receive reminder:
   - Title: "Front Porch Temp Reminder"
   - Message includes current temperature

- [x] Reminder received on both phones

---

## 9. Dropping Test

1. Raise threshold above current temperature (forces a crossing)
2. Both phones receive dropping notification:
   - Title: "Front Porch Temp Dropping"
   - Message includes current temperature

- [x] Dropping notification received on both phones

---

## 10. Restore

- [x] Set temp threshold back to 80°F
- [x] Close front door

---

## Results

| Test | Result | Notes |
|---|---|---|
| 1. Sensor validation | Pass | |
| 2. Log dashboard | Pass | |
| 3. Heartbeat | Pass | |
| 4. Watchdog | Pass | |
| 5. Lux sensor | Pass | Took ~30 seconds to rise after uncovering |
| 6. Alert suppression — time window | Skipped | |
| 7. Full alert | Pass | |
| 8. Reminder | Pass | |
| 9. Dropping | Pass | |
| 10. Restore | Pass | |
