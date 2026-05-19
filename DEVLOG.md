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
