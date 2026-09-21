# Back Patio Temp Sensor — End-to-End Test

Run all tests after perfboard assembly and flashing.

---

## 1. Sensor Validation

Confirm all sensor values updating every ~60 seconds in HA Overview page.

- [ ] Temperature — plausible (~70–115°F in Tucson)
- [ ] Pressure — ~13.4–13.5 psi (~925–930 hPa for Tucson elevation)
- [ ] Illuminance — changes with ambient light
- [ ] Humidity — plausible reading (%). If NaN, sensor is a counterfeit BMP280 — swap required (front-porch's original batch hit exactly this).

---

## 2. Log Dashboard Check

Open `http://pi1.local/` (Basic Auth, user: `jctsh`).

- [ ] Log messages visible under `back-patio-temp-sensor`
- [ ] MQTT connected message present from most recent boot

---

## 3. Heartbeat Check

- [ ] Heartbeat appearing every 5 minutes in log dashboard
- [ ] Heartbeat includes uptime, RSSI, and temperature

---

## 4. Watchdog Check

- [ ] `back-patio-temp-sensor` listed as active in the core watchdog message

---

## 5. Lux Sensor Test

- [ ] Cover the BH1750 (light sensor) — illuminance drops in HA
- [ ] Uncover — illuminance rises

---

## Custom Automation Tests — Deferred

Front-porch's own testing.md includes threshold-notification tests (alert suppression,
warm/close-door, cool/open-door). Those don't apply here yet — custom automation scope
for this component is deliberately undecided (see `integration.md`). Add equivalent tests
here once an automation is built.

---

## Results

| Test | Result | Notes |
|---|---|---|
| 1. Sensor validation | | |
| 2. Log dashboard | | |
| 3. Heartbeat | | |
| 4. Watchdog | | |
| 5. Lux sensor | | |
