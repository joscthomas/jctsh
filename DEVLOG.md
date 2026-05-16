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
