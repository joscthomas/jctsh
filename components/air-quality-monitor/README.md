# Air Quality Monitor

Planned portable clip-mounted sensor measuring PM1.0, PM2.5, PM4.0, PM10, VOC index,
and NOx index — carried on hikes alongside the hiking sensor to capture personal air
quality exposure on the trail.

**Status:** Planned — Phase 1 complete, parts ordered (SEN55, Adafruit adapter, JST cable)

---

## What It Solves

Fixed AQI stations miles away don't capture actual trail exposure to wildfire smoke,
haboobs, trail dust (silica), and summer ozone in the Tucson area. This device provides
a timestamped personal exposure record for every hike, correlated to GPS track and
hiking sensor environmental data in Google Sheets for post-hike analysis. A single RGB
LED gives immediate field awareness of PM2.5 level without a display.

---

## Planning

Phase 1 (discovery and feature decisions) is complete. Sensor selection, power system,
carry/enclosure approach, firmware pattern (follows hiking sensor exactly — do not
re-derive), and JCTsh integration are all decided. SEN55, Adafruit #5964 adapter, and
JST GH cable are ordered.

See [JCTsh-air-quality-monitor-phase1.md](JCTsh-air-quality-monitor-phase1.md) for the
full Phase 1 planning document.

Build begins after the hiking sensor is complete.

---

## Planned Hardware

| Component | Details |
|---|---|
| Microcontroller | ESP32 DevKitC-32 (on hand) |
| Air quality | Sensirion SEN55 (PM1.0/2.5/4.0/10, VOC, NOx) via Adafruit #5964 adapter |
| Field indicator | RGB LED — Green (Good < 12 μg/m³) / Yellow (Moderate) / Red (Unhealthy > 35 μg/m³) |
| Battery | EEMB LiPo pouch 603449, 1100mAh (on hand) |
| Power module | TP4056 + boost combined module (on hand) |
| Enclosure | 3D-printed with air intake/exhaust ports for SEN55 fan |
