# Van Sensors

Planned indoor and outdoor ESP32 environmental sensor nodes for the Pleasure-Way Ram
ProMaster 3500 — log timestamped readings to onboard flash during travel, sync
automatically to JCTsh on WiFi reconnect at home or via Pixel hotspot.

**Status:** Planned — Phase 1 complete

---

## What It Solves

Documents environmental conditions in and around the van during road trips and camping —
temperature, humidity, CO2, propane levels, air quality, and UV. Readings are
timestamped with a hardware RTC (accurate across weeks without WiFi) and correlated
to the GPS track from GPSLogger for post-trip analysis in Google Sheets.

---

## Planning

Phase 1 (discovery and feature decisions) is complete. Two-node architecture,
DS3231 RTC for accurate timestamps on extended trips, GPSLogger GPS correlation via
Pixel, opportunistic Pixel hotspot sync, and full data pipeline design are all decided.

See [JCTsh-van-sensor-phase1.md](JCTsh-van-sensor-phase1.md) for the full Phase 1
planning document.

---

## Planned Nodes

### Outdoor Node

| Component | Details |
|---|---|
| Microcontroller | ESP32 DevKitC-32 |
| Temp / humidity / pressure | BME280 (on hand) |
| UV index | Adafruit LTR-390 |
| Air quality | Sensirion SEN55 (PM1.0/2.5/4.0/10, VOC, NOx) |
| Clock | DS3231 RTC with CR2032 backup |
| Power | EEMB 1100mAh LiPo + TP4056+boost; charges from 12V USB cradle in van |

### Indoor Node

| Component | Details |
|---|---|
| Microcontroller | ESP32 DevKitC-32 |
| Temp / humidity / pressure | BME280 (on hand) |
| CO2 | Sensirion SCD40 (photoacoustic, true CO2) |
| Propane / combustible gas | MQ-6 (LPG-specific, analog ADC) — monitoring only, not safety-critical |
| Clock | DS3231 RTC with CR2032 backup |
| Power | 12V coach power — always on (required for MQ-6 heating element) |

---

## Operating Modes

| Mode | Behavior |
|---|---|
| Field (traveling / camping) | Reads sensors every 10 minutes, timestamps via DS3231, stores to onboard flash |
| Home (on JCTnet1) | Replays full flash buffer to home MQTT broker; Node-RED routes to Google Sheets |
| Pixel hotspot | Same replay as home mode, over cellular — trivially small data volume (~58 KB/day both nodes) |
