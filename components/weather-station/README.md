# Weather Station

Planned outdoor DIY weather station measuring temperature, humidity, pressure, UV index,
solar irradiance, wind speed, wind direction, rain, and lightning — posting live data to
Weather Underground and archiving all readings to Google Sheets.

**Status:** Planned — Phase 3 (architecture) complete, parts to purchase (~$227)

---

## What It Solves

Regional weather stations miles away don't capture hyperlocal conditions in Tucson —
temperature, UV, and wind vary significantly at the micro-scale. This station provides
personal weather data at the installation address, contributes to the Weather Underground
public PWS network, and feeds the JCTsh Google Sheets environmental archive alongside
data from the hiking sensor and other environmental sensors.

---

## Planning

All phases of pre-build planning are complete:

- **Phase 1 (Discovery):** Technology decisions, feasibility, sensor selection
- **Phase 2 (BOM):** Parts list confirmed; most sensors to purchase (~$227 estimated)
- **Phase 3 (Architecture):** MQTT topics, payload schema, six-phase build strategy,
  SmartThings integration, and Node-RED data handler pattern all decided

See [jctsh-weather-station-planning.md](jctsh-weather-station-planning.md) for the full
planning document.

Phase 4 (Claude Code build instructions) begins when directed.

---

## Planned Hardware

| Component | Details |
|---|---|
| Microcontroller | ESP32 DevKitC-32 (on hand) |
| Temp / humidity / pressure | BME280 in SRS100LX radiation shield (on hand) |
| UV index | VEML6075 |
| Solar irradiance | SI1145 |
| Wind + rain | SparkFun Weather Meter Kit (reed switch, RJ11) |
| Lightning | SparkFun AS3935 detector (to 40km) |
| RTC | DS3231 with CR2032 backup |
| SD card | Local data logging backup |
| Power | CN3791 MPPT solar charger + 6V panel + 6000mAh LiPo + MT3608 boost converter |
| Enclosure | YETLEBOX IP67 |
