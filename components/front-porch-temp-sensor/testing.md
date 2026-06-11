# Front Porch Temp Sensor — End-to-End Test (Step 11)

Run all tests with the breadboard prototype before transferring to perfboard.

**Automation logic summary:**
- **Warm/Close Door:** temp stays ≥ threshold for 10 min AND 6am–10pm → notify both phones once
- **Cool/Open Door:** temp stays < threshold for 10 min AND 6am–1pm → notify both phones once

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

## 7. Warm/Close Door Test

1. Raise threshold to 95°F (forces a crossing when lowered)
2. Lower threshold to 75°F — wait up to 10 minutes; both phones should receive one notification:
   - Title: "Front Porch Warm"
   - Message includes current temperature and "Consider closing the door."
3. Confirm only one notification fires (no follow-up reminder)

- [ ] Notification received on both phones
- [ ] No second notification after waiting 15+ minutes

---

## 8. Cool/Open Door Test

1. Raise threshold above current temperature (forces a below crossing)
2. Wait up to 10 minutes between 6am–1pm; both phones receive one notification:
   - Title: "Front Porch Cool"
   - Message includes current temperature and "Good time to open the door."

- [ ] Notification received on both phones

---

## 9. Restore

- [ ] Set temp threshold back to 80°F

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
| 7. Warm/Close Door | | |
| 8. Cool/Open Door | | |
| 9. Restore | | |
