# JCTsh DEVLOG

## 2026-05-16
Restructured Salt Sensor project into JCTsh smart home monorepo. Salt Sensor
becomes first component under jctsh/components/. Centralized Python log server
added to jctsh/core/logging/, served at http://raspberrypi.local/. ESP web server
removed; log messages now published via MQTT to jctsh/sensors/salt-sensor/log.
MQTT topics renamed from saltlevel/* to jctsh/sensors/salt-sensor/*. Node-RED
flow split into core.flow.json (broker) and salt-sensor.flow.json (sensor logic).
Test mode loop bug fixed — test sequence now runs once through WARNING then CRITICAL
instead of cycling indefinitely.

End-to-end verification completed. Fixed log_server.py missing MQTT credentials
(MQTT_USER/MQTT_PASS + username_pw_set) — broker requires auth. Sketch moved into
matching subfolder (Arduino IDE requirement). Confirmed: ESP publishes to new topics,
Node-RED responds with status, log dashboard displays messages, Pi reboot survival
verified. JCTsh.local mDNS alias closed out — Avahi CNAME not supported on this Pi;
address record causes local name collision; cosmetic value not worth the complexity.
Use http://raspberrypi.local/ for the dashboard.

Added hourly watchdog heartbeat to log_server.py. Publishes
{"component":"jctsh-core","category":"System","message":"Watchdog: alive."} to
jctsh/core/log-server/log every hour — confirms log server and MQTT broker are alive
between 12-hour sensor readings. Core infrastructure concern, not salt-sensor specific.

Confirmed Home Assistant is the SmartThings bridge — no other path exists. HA is
connected with the SmartThings integration active. Salt sensor switches verified as
HA entities synced to SmartThings. All future components requiring SmartThings alerts
or control must route through Node-RED → HA REST API → SmartThings integration.

Added Garage Presence component (components/garage-presence/). HA-only — no ESP32,
no Node-RED. Two HA helpers created via UI: timer.garage_presence_timer (countdown)
and input_number.garage_timer_duration (duration in minutes, default 20). ST Garage
Timer Duration dimmer (49a4fa15) had no HA entities — replaced by input_number helper.

## 2026-05-18
Garage Presence component tested and refined. Automation 1 (restart timer on activity)
confirmed working with back door sensor and garage motion sensor. Garage cam trigger
wired up but unreliable due to cam sensitivity — left in place. Correct HA entity for
door sensor is binary_sensor.back_door_door (not binary_sensor.garage_door_sensor_door
as originally assumed). Timer duration template fixed — seconds formula used instead
of HH:MM:SS to avoid zero-padding issues.

Automation 2 (timer expiry → turn off Garage Presence Vswitch + auto-close door)
removed by design — garage door control intentionally decoupled from presence detection.
Timer expiry signal available via timer.finished event for future automations to consume.

## 2026-05-19
Started Garage Radar component (components/garage-radar/). Hardware: HLK-LD2412 24GHz
mmWave radar + ESP32 DevKitC-32 (38-pin, CP2102 USB-C), firmware via ESPHome. ESPHome
YAML created (Step 1). Breadboard wired and verified (Step 2) — corrected wiring doc:
LD2412 pin is labeled 5V (not VCC) and connects to ESP32 VIN, not 3.3V; onboard
regulator handles the step-down; UART logic is 3.3V, no level shifter needed.

## 2026-05-20
Garage Radar Steps 3–10 completed with breadboard prototype. ESPHome flashed via USB
(Step 3) — fixed ESPHome 2026.x breaking change: ld2412 timeout option removed, replaced
with delayed_off: 30s filter on has_target binary sensor. Fixed whitespace-in-path issue
by copying files to C:\esphome\garage-radar\ for flash. Fixed raspberrypi.local resolving
to IPv6 link-local — used 192.168.1.117 (IPv4) for MQTT and HA MQTT integration setup.
All 8 HA entities confirmed (Presence, Moving Target, Still Target, 5 distance/energy sensors).

Sensor validation passed (Step 4): baseline, moving presence, still presence, 30s delayed_off
holdoff, and detection range all confirmed.

Steps 5–7 (perfboard transfer, soldered board validation, physical mount) deferred —
system fully functional on breadboard prototype. Perfboard layout and wiring docs complete
for when soldering is ready.

HA integration complete (Steps 8–9). 20-minute presence timeout confirmed as HA-only —
no Node-RED involvement. Two automations added: (1) garage_radar_presence added as trigger
to existing Garage Presence - Restart timer on activity automation; (2) new Garage Presence
- Radar keepalive automation fires every 10 minutes while radar detects presence, preventing
timer expiry during extended still workbench use. End-to-end tests 1–4 all passed.

Final documentation complete (Step 10): component README.md created, root README updated.

Infrastructure and documentation session. Added Architecture section to CLAUDE.md
covering component roles (ESP32 = edge sensor, no logic; Mosquitto = message bus;
Node-RED = brain/logic; Python log server = record keeper; HA = integration layer
only), full end-to-end message flow diagram, and the two parallel flows concept
(data flow vs. log flow) that every component produces.

Fixed raspberrypi.local resolution on Windows — hostname was always intermittent
due to Windows mDNS unreliability. Set DHCP reservation on router for
192.168.1.117, added hosts file entry on Windows to bypass mDNS entirely.
IP documented in CLAUDE.md as fallback reference.

Fixed log server hang (ThreadingHTTPServer). Phone on 5G could reach HA (port 8123,
Docker) but not the log dashboard (port 80, Python). Root cause: single-threaded
HTTPServer blocks all new connections if a client connects and drops mid-response
(phone browsers do this frequently). Docker punches through iptables directly so
HA was unaffected. Fix: switched HTTPServer to ThreadingHTTPServer — each request
now handled in its own thread. Deployed and confirmed working from phone.

Log dashboard tweaks deployed and confirmed. Timestamp color changed from #444
to #888 to match Component column. Repeat count color changed from fixed #444
to match the message color. Watchdog message now reports active components seen
since last restart (e.g. "Watchdog: alive. Active: salt-sensor, garage-radar.")
instead of the generic "Watchdog: alive." Log server hang fix (ThreadingHTTPServer)
also deployed — confirmed working from phone.

## 2026-05-18 (continued)
Garage Presence further refined. Added Automation 2 (timer expired → turn off Garage
Presence Vswitch) and Automation 3 (sync timer to vswitch — HA restart recovery).
Discovered SmartThings → HA sync is unreliable for real-time state triggers: virtual
switch and sensor state changes made in SmartThings do not reliably reach HA's event
system. Adopted Option A: HA owns Garage Presence Vswitch exclusively — no SmartThings
routines may turn it on. Removed ST routine that turned on vswitch on back door open.
PIR sensors (garage motion, garage cam) unreliable in hot Arizona garage — stay stuck
`on` preventing off→on transition triggers. Confirmed working in cooler morning
temperatures.
