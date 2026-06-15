# JCTsh Property Sensor Pattern
**Author:** Joseph C Thomas (JCT)
**Purpose:** Defines the standard pattern for all JCTsh environmental sensors deployed on or around the property — fixed, mobile, USB-powered, battery-powered, or solar-powered. Provides the variable decision table and new-sensor checklist that every build works through before touching firmware.
**Version:** 1.0
**Related files:** `JCTsh-Environmental-Data-Architecture.md`, `JCTsh-Build-Standards.md`, `house-lot-coordinates.md`

---

## What This Document Is

`JCTsh-Environmental-Data-Architecture.md` owns the **data pipeline** — payload schema, Google Sheets archive, Node-RED handler, Weather Underground.

This document owns the **sensor pattern** — the invariant standard every property sensor conforms to, the dimensions that vary between deployments, and the checklist that produces the concrete decisions needed to start a build.

Load this document at Phase 1 of any property sensor build alongside `JCTsh-Environmental-Data-Architecture.md`.

---

## Standard — Invariant Across Every Deployment

These elements are identical in every property sensor. They are not decisions — they are facts about how the system works.

**Firmware platform**
- ESPHome on ESP32. See `JCTsh-Build-Standards.md` §2 for all ESP32/ESPHome conventions.

**MQTT structure**
- Namespace: `jctsh/components/<name>/...`
- `/data` — standard JSON payload published on the data interval (see Variable Dimensions)
- `/log` — diagnostic messages in standard JSON format → Python log server wildcard, no setup needed
- `/heartbeat` — published on the heartbeat interval → Node-RED watchdog wildcard, no setup needed
- Dedicated Mosquitto account per device. See `JCTsh-Build-Standards.md` §2.11.

**Data payload**
- Always includes: `component`, `ts` (ISO 8601 UTC via SNTP), `lat`, `lon`, `rssi_dbm`
- Sensor-specific fields appended for each sensor present
- Fields a sensor does not measure are omitted entirely — no nulls for missing fields
- `lat`/`lon` exception: always present; send hardcoded value (fixed) or JSON `null` (mobile without GPS)
- See `JCTsh-Environmental-Data-Architecture.md` for the full field reference

**Infrastructure — zero changes needed for each new device**
- Node-RED wildcard `jctsh/components/+/data` catches the new sensor automatically
- Google Sheets `appendRow` handles any conforming payload — unknown fields are ignored
- Python log server wildcard `jctsh/+/+/log` catches all log messages automatically
- Node-RED watchdog wildcard `jctsh/+/+/heartbeat` catches all heartbeats automatically
- HA auto-discovery via MQTT creates entities automatically

**Coordinates source**
- `house-lot-coordinates.md` (repo root) is the canonical source for all fixed-sensor lat/lon. Identify the named point closest to the sensor's physical location and hardcode it in firmware.

---

## Variable Dimensions

Work through each dimension for every new sensor. Each decision produces a concrete value that goes directly into firmware or configuration.

### Location Type

| Type | lat/lon in payload | How to get coordinates |
|---|---|---|
| Fixed / stationary | Hardcoded constant | Named point in `house-lot-coordinates.md` |
| Mobile / vehicle | From GPSLogger → GPS Track sheet → Node-RED lookup; or dedicated GPS module | GPSLogger app on phone; see `JCTsh-Build-Standards.md` §5.5 |
| Mobile / carried | JSON `null` | Timestamp correlation with GaiaGPS track after activity |

### Power Source

| Source | Operational profile | Additional payload fields |
|---|---|---|
| USB / mains | Always-on. 60s sensor reads. Standard data interval (5 min). Standard heartbeat (30 min). | none |
| 12V coach / vehicle | Always-on when coach systems active. Same intervals as USB. | none |
| Battery | Deep sleep between reads. Duty-cycled intervals — set based on required battery life. | `battery_v` |
| Solar + battery | Always-on if panel is adequately sized; otherwise duty-cycled. Same intervals as USB when on. | `battery_v` |

> **Charging state gap:** `battery_v` alone does not indicate whether a solar device is charging or draining. CARD-017 tracks the decision on additional schema fields (`charging`, `solar_v`, etc.). Until that card is resolved, include `battery_v` and document the limitation in the component README.

### Connectivity Profile

| Profile | WiFi config | MQTT broker |
|---|---|---|
| Home only | Single SSID (`wifi_ssid` secret) | `raspberrypi.local` / `192.168.1.117` |
| Home + hotspot | `networks:` list — home WiFi priority 1, hotspot priority 2 | `jctsh.duckdns.org` (internet-routable; required for cellular) |

See `JCTsh-Build-Standards.md` §2.8 for the multi-network WiFi boilerplate and hotspot SSID naming convention.

### Offline / Gap Handling

| Profile | Approach |
|---|---|
| Always-connected (USB, mains, coach power, home WiFi) | None needed — data publishes live |
| Intermittently-connected (mobile, remote battery, hotspot) | SPIFFS flash logging + replay on reconnect. See `JCTsh-Build-Standards.md` §2.10 and CARD-016. |

> **SPIFFS gap:** The SPIFFS logging pattern is documented in Build Standards §2.10 with the hiking sensor as the reference. CARD-016 tracks extracting it into a fully reusable standard for future builds.

### Data and Heartbeat Intervals

| Power source | Data interval | Heartbeat interval |
|---|---|---|
| USB / mains / coach | 5 min | 30 min |
| Battery / solar (duty-cycled) | Set per battery-life requirement | Match data interval or longer; document in README |

### Sensor Complement

Determined by what physical sensors are installed. Only measured fields appear in the payload. Standard fields by sensor:

| Sensor | Fields added to payload |
|---|---|
| BME280 | `temp_f`, `humidity_pct`, `pressure_hpa` |
| BH1750 | `illuminance_lx` |
| LTR-390 | `uv_index` |
| SEN55 | `pm1_ug_m3`, `pm25_ug_m3`, `pm4_ug_m3`, `pm10_ug_m3`, `voc_index`, `nox_index` |
| SCD40 | `co2_ppm` *(not yet in schema — add before first SCD40 build)* |
| Anemometer / wind vane | `wind_speed_mph`, `wind_dir_deg` |
| Rain gauge | `rain_tips` |
| LiPo / solar battery | `battery_v` |

Add new sensor fields to `JCTsh-Environmental-Data-Architecture.md` and the Apps Script before building any sensor that introduces one.

### Custom Automation (Optional)

Per-deployment HA automations that go beyond data archiving. Examples:

| Deployment | Custom automation |
|---|---|
| Front porch | Cool/warm temperature notifications (threshold ± 2°F hysteresis, time windows) |
| Backyard | None defined |
| Van interior | High-temperature alert when parked in sun |

Custom automations live in `components/<name>/automation-<purpose>.yaml` and are imported into HA manually. They are independent of the data pipeline — the pipeline runs whether or not a custom automation exists.

### SmartThings Exposure (Optional)

Determined during Phase 3. Not every sensor needs SmartThings exposure. If needed, follow the HA → SmartThings integration path in `JCTsh-Build-Standards.md` §5.

---

## New Sensor Checklist

Work through this before writing any firmware. Every item produces a concrete answer.

### 1. Name
- Component name (lowercase, hyphenated): `_______________`
- This becomes: MQTT prefix `jctsh/components/<name>/`, hostname `<name>.local`, directory `components/<name>/`

### 2. Location
- [ ] Fixed / stationary → Named point in `house-lot-coordinates.md`: `_______________`
  - Hardcoded lat: `_______________`   lon: `_______________`
- [ ] Mobile / vehicle → GPS source: `[ ] GPSLogger lookup` `[ ] GPS module on ESP32`
- [ ] Mobile / carried → lat/lon = null; timestamp correlation method: `_______________`

### 3. Power source
- [ ] USB / mains
- [ ] 12V coach / vehicle
- [ ] Battery → target battery life: `_______________` → data interval: `_______________`
- [ ] Solar + battery → expected always-on? `[ ] Yes` `[ ] No` → intervals: `_______________`
- Battery/solar: include `battery_v` in payload: `[ ] Yes`

### 4. Connectivity
- [ ] Home WiFi only → broker: `raspberrypi.local`
- [ ] Home WiFi + hotspot → broker: `jctsh.duckdns.org`; hotspot SSID: `JCT Hotspot`

### 5. Offline handling
- [ ] Always-connected → no SPIFFS needed
- [ ] Intermittently-connected → implement SPIFFS logging (see `JCTsh-Build-Standards.md` §2.10)

### 6. Intervals
- Data interval: `_______________` (default 5 min for always-on)
- Heartbeat interval: `_______________` (default 30 min for always-on)
- Sensor read interval: `_______________` (default 60s for always-on)

### 7. Sensor complement
List each physical sensor and the payload fields it produces:

| Sensor | Fields |
|---|---|
| | |
| | |

Confirm every field exists in `JCTsh-Environmental-Data-Architecture.md`. Add new fields before starting the build.

### 8. HA entities
- All sensor fields are auto-discovered by HA via MQTT discovery — no manual setup.
- Any fields that should NOT appear as HA entities: `_______________`

### 9. Custom automation
- [ ] None
- [ ] Yes → describe: `_______________`
  - Threshold source: `[ ] input_number helper` `[ ] hardcoded`
  - Time window: `_______________`
  - Notification targets: `[ ] Pixel 10 Pro XL` `[ ] Pixel 7 Pro`

### 10. SmartThings exposure
- [ ] None
- [ ] Yes → entity type: `_______________`  HA entity: `_______________`

### 11. Enclosure
- [ ] Indoor — open standoff mount (default)
- [ ] Outdoor fixed — weatherproof project box (IP65+)
- [ ] Outdoor mobile — ruggedized case

### 12. Pre-build infrastructure tasks
- [ ] Named point confirmed in `house-lot-coordinates.md` (or coordinates measured and added)
- [ ] New fields added to `JCTsh-Environmental-Data-Architecture.md` and Apps Script
- [ ] Dedicated Mosquitto account created (see `JCTsh-Build-Standards.md` §2.11)
- [ ] `C:\esphome\<name>\` directory created
- [ ] `components/<name>/secrets.yaml` created from template
- [ ] DHCP reservation added on router; IP and MAC recorded in `jctsh-network.md`

---

## Reference Implementations

| Deployment | Power | Location | Connectivity | Offline | Custom automation |
|---|---|---|---|---|---|
| `front-porch-temp-sensor` | USB | Fixed — H8 (32.4612997, -111.1184154) | Home WiFi only | None | Cool/warm notifications |
| `hiking-sensor` | Battery | Mobile / carried | Home WiFi + hotspot | SPIFFS logging | None |

---

## Open Gaps

| Card | Gap | Status |
|---|---|---|
| CARD-016 | SPIFFS offline logging — extract reusable standard from hiking-sensor | Backlog |
| CARD-017 | Charging state schema fields for solar/battery devices | Backlog |

Until CARD-016 is resolved, use `components/hiking-sensor/hiking-sensor.yaml` and `JCTsh-Build-Standards.md` §2.10 as the SPIFFS reference.

Until CARD-017 is resolved, include `battery_v` for battery and solar devices and document the charging-state limitation in the component README.

---

## Document Update Policy

Update this document when:
- A new power source type or location type is added to the ecosystem
- A new sensor type is deployed that adds fields to the sensor complement table
- An open gap is resolved (update or remove the gap entry)
- A new reference implementation is complete (add it to the reference table)
- The checklist proves incomplete or misleading during a build
