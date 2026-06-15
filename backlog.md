# JCTsh Backlog

Lightweight kanban. Each card has a **type** (idea | enhancement | bug) and a unique ID.

**Columns:** Backlog → Planning → Design → Build → Done
- **Backlog** — captured, not yet being worked on
- **Planning** — plan is being laid out
- **Design** — Claude Code instructions being written
- **Build** — going through Claude Code instructions, including testing
- **Done** — complete

---

## Backlog

### CARD-002 · [enhancement] MQTT v3.1.1 → v5 upgrade
**Component:** infrastructure  
**Notes:** Node-RED v4 creates MQTT In/Out nodes with v5 fields (nl, rap, respTopic, etc.) that silently break on the v3.1.1 broker — requires manual cleanup after every UI import. Mosquitto 2.x supports v5 and is backward-compatible with v3 clients, so ESP32/ESPHome devices stay on v3 unmodified. Steps: verify Mosquitto version, enable v5 in mosquitto.conf if needed, change Node-RED broker node protocolVersion from 4 to 5, test all existing flows. Do as a standalone maintenance task — not mid-component-build.

---

### CARD-003 · [enhancement] TLS for Mosquitto (port 8883)
**Component:** infrastructure  
**Notes:** Port 1883 is internet-exposed via DuckDNS/port-forward with fail2ban, but credentials and sensor data are cleartext. TLS on port 8883 eliminates this. Steps: get Let's Encrypt cert for the DuckDNS hostname (certbot with duckdns plugin), add a TLS listener on port 8883 in mosquitto.conf, update mqtt_broker port in every ESPHome secrets.yaml, update Node-RED broker node, update HA MQTT integration, reflash all ESP32s. Do as a standalone task after DuckDNS setup is stable. Depends on CARD-002 being done first (or do together).

---

### CARD-004 · [enhancement] Salt-sensor: migrate Arduino C++ → ESPHome
**Component:** salt-sensor  
**Notes:** Do this before perfboard transfer — ESPHome initializes hardware differently than Arduino and if a strapping pin causes a boot issue it's easier to rewire on breadboard than cut perfboard traces. Device side maps cleanly (ultrasonic platform, median filter, 12h interval, LED blink via globals). Hard part: test mode needs redesign — Node-RED currently injects fake readings; ESPHome has no equivalent. Replace with an HA script that triggers the threshold automation with a synthetic distance value. GPIO 2 and 15 are strapping pins but currently working — not a blocker.

---

### CARD-005 · [enhancement] p-w-firefly overlay filesystem
**Component:** p-w-firefly  
**Notes:** The Pi in the RV runs continuously, accumulating writes from logs, Tailscale state, and OS housekeeping — SD cards have a finite write cycle life and will eventually fail silently. An overlay filesystem makes the SD card effectively read-only during normal operation: all writes go to RAM, the card is only written during a deliberate shutdown sequence.

**Tailscale complication:** Tailscale stores its node identity and keys in `/var/lib/tailscale/`. If that directory is in the overlay (RAM-only), Tailscale loses its identity on every reboot and needs to re-authenticate. Fix: a persistent bind mount (small USB stick or dedicated partition) mapped to `/var/lib/tailscale/` so it survives reboots.

**eRVin image complication:** Raspbian Buster's modified `raspi-config` does not expose the overlay option in its UI — must be set up manually with `bilibop-lockfs` or equivalent.

**Interim protection:** SanDisk MAX Endurance card already installed.

---

### CARD-014 · [enhancement] Move environmental data pipeline to core
**Component:** core/data-pipeline (new)
**Notes:** The environmental data pipeline (Apps Script, Google Sheets, Node-RED wildcard data handler) is shared infrastructure consumed by all sensor components — not owned by hiking-sensor. All data flowing through it is environmental data, including observations. Move `environmental-data.gs`, `JCTsh-Environmental-Data-Architecture.md`, and the Node-RED wildcard data handler flow to `core/data-pipeline/`. Update references in component directories. Do before the system grows significantly — weather station, air quality monitor, and van sensors will all be consumers.

---

### CARD-006 · [enhancement] Move log directory to USB stick
**Component:** logging  
**Priority:** low  
**Notes:** Move LOG_DIR in log_server.py from the SD card to a USB stick plugged into the Pi for better write endurance. Add an /etc/fstab entry so it auto-mounts at boot before the jctsh-logging service starts.

---

### CARD-010 · [enhancement] Front-porch-temp-sensor — Use case definition
**Component:** front-porch-temp-sensor  
**Notes:** Perfboard transfer complete. No enclosure planned. Use case still being defined — what automations or alerts this sensor should drive beyond the existing Temp Alert and Temp Dropping automations. Perfboard layout: `components/front-porch-temp-sensor/perfboard-layout.md`.

---

### CARD-015 · [enhancement] Front-porch-temp-sensor — Environmental data pipeline integration
**Component:** front-porch-temp-sensor  
**Notes:** The front porch sensor publishes temperature, humidity, pressure, and illuminance every 60 seconds. Wire these readings into the environmental data pipeline (Node-RED wildcard data handler → Apps Script → Google Sheets) so they are archived alongside hiking-sensor data. Follow the payload schema and Node-RED handler pattern defined in `JCTsh-Environmental-Data-Architecture.md`. The front porch sensor is a fixed home station, so readings are always georeferenced to home — no GPS field needed. Consider whether illuminance (lx) belongs in the shared schema or is front-porch-specific.

---

## Planning

### CARD-012 · [idea] Air quality monitor
**Component:** air-quality-monitor  
**Planning doc:** `components/air-quality-monitor/JCTsh-air-quality-monitor-phase1.md`  
**Notes:** Portable clip-mounted SEN55 air quality sensor (PM1.0/2.5/4.0/10, VOC, NOx) carried on hikes alongside the hiking monitor. Phase 1 complete; SEN55, Adafruit #5964 adapter, and JST GH cable ordered. Follows hiking-monitor firmware pattern (onboard flash logging, WiFi replay). Build begins after hiking-sensor is complete. Phase 2 entry criteria: parts received, fan transistor availability confirmed, hiking sensor build complete.

---

### CARD-013 · [idea] Van sensors (indoor + outdoor)
**Component:** van-sensors  
**Planning doc:** `components/van-sensors/JCTsh-van-sensor-phase1.md`  
**Notes:** Two ESP32 ESPHome nodes for the Pleasure-Way ProMaster 3500 van. Outdoor: BME280 + LTR-390 UV + SEN55 air quality, LiPo powered. Indoor: BME280 + SCD40 CO2 + MQ-6 propane, 12V coach power. Both log to onboard flash during travel, sync to home MQTT on WiFi reconnect (home or Pixel hotspot). DS3231 RTC for accurate timestamps during extended trips. GPS correlation via GPSLogger on Pixel. Phase 1 complete — ready for Phase 2 (hardware selection, inventory scan, open questions resolved).

---

### CARD-011 · [idea] Weather station
**Component:** weather-station  
**Planning doc:** `components/weather-station/jctsh-weather-station-planning.md`  
**Notes:** Full DIY outdoor weather station — BME280 (temp/humidity/pressure), VEML6075 (UV), SI1145 (solar irradiance), SparkFun Weather Meter Kit (wind/rain), AS3935 lightning detector, DS3231 RTC, SD card backup, solar+LiPo power. Posts to Weather Underground and Google Sheets. Phase 3 (architecture) complete — MQTT topics, payload schema, SmartThings integration, and six-phase build strategy all decided. Ready for Phase 4 (Claude Code instructions) when directed. Most parts to purchase (~$227 estimated).

---

## Build

### CARD-008 · [enhancement] Hiking-sensor Step 21 — Pixel hotspot second WiFi
**Component:** hiking-sensor  
**Notes:** `JCT Hotspot` added as second WiFi network (JCTnet1 priority 1, hotspot priority 2). Broker changed to `jctsh.duckdns.org` (internet-routable via DuckDNS + port 1883 forward). Firmware OTA flashed 2026-06-12. Field test pending — first hotspot sync will happen on camping trip starting 2026-06-15.

**Upload workflow:** Enable Pixel hotspot → switch hiking monitor off then on → device connects to hotspot → reaches home broker over cellular → SPIFFS replay fires automatically → log dashboard shows `Replaying N hike readings...` then `Hike log replay complete.` → turn off hotspot. Confirm by watching IP in `Hiking monitor online` log message (hotspot DHCP ≠ 192.168.1.x).

---

### CARD-009 · [enhancement] Hiking-sensor Step 15 — Enclosure design and build
**Component:** hiking-sensor  
**Notes:** Design and build the permanent enclosure. Field prototype (two-board sandwich) documented in `components/hiking-sensor/enclosure-prototype.md`. Standoffs arrive 2026-06-14; temp enclosure build before camping trip departure 2026-06-15. Device will be used in the field for ~2 weeks on that trip — hiking and van sensor simulation. Full 3D-printed permanent enclosure is a later step.

---

## Done

### CARD-007 · [idea] Hiking observations pipeline (Tasker → Sheets)
**Component:** hiking-sensor  
**Resolution:** Tasker widget → Android speech recognition → HTTP POST to Apps Script → Hiking Observations sheet with automatic category classification. No keyword prefix — widget tap is the intent signal. Steps 23–26 complete 2026-06-13.

---

### CARD-001 · [bug] Garage-radar false presence on door close
**Component:** garage-radar  
**Resolution:** Ill-defined and no longer applicable — closed.
