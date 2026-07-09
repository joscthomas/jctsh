# JCTsh DEVLOG

## 2026-07-09 (continued, part 3)
Completed photo-server's build Step 18 (harvest step) — the last remaining step in the
instructions doc, found by re-auditing the whole doc against actual state rather than
trusting it was done. Proposed and, after Joseph's review, applied JCTsh-Build-Standards.md
v1.13's new §9 Non-ESP32 / Docker-Based Component Standards: the five candidates the
instructions doc had originally anticipated (Docker DNS pinning, UUID storage mounts,
incremental rsync backup, bus-powered drive preference — folded into §9.2) plus two more
that only became obvious from this build's own operational work rather than the original
plan: §9.4 dashboard visibility for scheduled/background jobs (the MQTT start/complete
message pattern, independently reinvented twice in this build for reboots and backups,
which is what made it worth promoting to a standard) and §9.6 detached remote job execution
(nohup + disown, always verify via ps aux on the remote host — a lesson learned the hard
way during the original Takeout migration's duplicate-mv race).

## 2026-07-09 (continued, part 2)
photo-server documentation catch-up (Steps 15-17 of the build instructions, long overdue)
plus CARD-030 execution. Installed Node.js (Step 15, was never done). Wrote the 6 missing
Step 16 docs (README.md, docker-compose.yml, .env.example, setup.md, network.md,
backup.md) — deletion-log-setup.md skipped, Joseph moved that step to photo-tv-display's
scope, and Step 13 (face naming) marked N/A, decided "catch as catch can" rather than a
tracked task. Step 17: added photo-server to root README's component table, fixed a stale
parts-inventory note that still said "OS to be replaced" a week after Ubuntu had been
running, added a Storage section for the two USB HDDs + spares.

CARD-030: with CARD-039 having already done a far more rigorous completeness check than
the original "spot-check before deleting" plan called for, deleted both Takeout zip
staging locations (818GB reclaimed — Momentus 100%→19% used, NVMe root 87%→5%), re-enabled
the weekly backup cron, kicked off a manual verification run (still in progress — first
run is slow, reconciling a destination that previously held zip staging data instead of
real backups; future weekly runs should be fast since rsync is incremental).

Also added a consolidated "Scheduled Maintenance Windows" table to jctsh-network.md
(prompted by realizing KeepConnect's router reboot, now landing Wednesday 3am, was never
cross-referenced against the Pi/M8 reboot and backup schedule) and MQTT dashboard
visibility for backup runs (CARD-040, same "Backup starting."/"Backup complete." pattern
as CARD-036's reboot notifications) — not yet live-verified since the first post-cleanup
backup run was already in progress when the updated script was deployed.

## 2026-07-09 (continued)
Closed CARD-039: re-ran `immich-go` for real (not `--dry-run`) against every retained
Takeout zip for both accounts, prompted by CARD-037 raising doubt about whether this same
chaotic import had also dropped raw asset uploads, not just background ML jobs. Launched
fully detached (`nohup ... & disown` directly on the M8) so it survived the home network
being down for part of the run. Found 3,433 assets genuinely missing and uploaded them —
58 (Joseph, backup zips), 119 (Joseph, NVMe zips), 3,256 (Robin) — zero errors, single
clean pass, no restarts needed this time. Surprising part: Robin's gap was by far the
largest despite her original import being the "clean" one with no crashes, meaning the
missing-asset problem (like CARD-037's ML-processing gap) wasn't caused solely by Joseph's
restart history — something shared between both imports is the more likely cause, not
pinned down further since re-running was sufficient to fix it regardless. Full writeup in
`components/photo-server/migration.md` and `backlog.md` CARD-039.

## 2026-07-09
Closed CARD-037: Immich ML processing (face detection/recognition, CLIP smart search, OCR,
duplicate detection) had never run on a large fraction of both Joseph's and Robin's
libraries — found by chasing down Joseph's "most photos don't show identified people"
question through the API rather than guessing, and confirmed definitively via a duplicate
photo pair where one copy had 7 detected faces and its exact twin had zero. Checking
Robin's library too (96% zero-face rate, clean import, no crashes) ruled out the original
5-restart-import theory and showed the gap was server-wide, not import-specific.

Fix was to trigger all five affected jobs via the admin job-control API — Immich has no
dry-run, so starting each job doubled as both the diagnostic (revealing real backlogs:
~140K faces, 33K duplicates, ~17K each for smart search/OCR) and the fix itself. Verified
CPU-bound via `vmstat` (not I/O-bound) before running all five concurrently. Ran overnight
into a home-internet outage (unrelated — the jobs run locally on the M8, unaffected).
Confirmed complete 2026-07-09: all queues drained, zero failures, M8 uptime showed it never
rebooted mid-run. People clusters grew 2,626 → 3,331. Full writeup in `backlog.md` CARD-037.

Also documented the home router (TP-Link Archer AXE75, 192.168.1.1) in `jctsh-network.md`
and `ENVIRONMENT.md` — it had never been added despite being the gateway every other device
depends on, and despite `keepconnect.md` already referencing it extensively.

## 2026-07-08 (continued, part 3)
Closed the actual CARD-032 monitoring gap and live-tested CARD-029 in the same session.
`photo-server-heartbeat.py` now writes/reads/removes a marker file inside the
`immich_server` container's own `/data/upload` on every run, catching a broken bind mount
directly instead of trusting Docker's health check (which only pings the API). Live-tested
both degraded paths for real, now that the Immich migration is done and it's safe to:
container-down (`docker stop immich_redis`) produced the expected non-collapsing Alert row,
and a storage failure — reproduced via `mount -o remount,ro /mnt/photo-library` rather than
physically pulling the drive — produced `Alert - storage:...Read-only file system`, exactly
reproducing the original incident's failure mode. First attempt to simulate the storage
failure (`chmod 555` on the host-side upload directory) silently failed to trigger anything,
because the Immich container runs as root and root ignores POSIX permission bits — a
read-only remount enforces at the VFS level instead and actually worked. Both cards moved
to Done; full writeup in `components/photo-server/heartbeat.md`.

## 2026-07-08 (continued, part 2)
Added dashboard visibility for the CARD-035 scheduled reboots (CARD-036). Previously the
only way to confirm a reboot happened and succeeded was SSHing in and checking
`systemctl`/`docker ps` manually. Now `scheduled-reboot.service` publishes "Scheduled
reboot about to occur." right before rebooting, and a new `reboot-complete.service`
(runs on every boot) publishes "Boot complete." once the broker is reachable — both land
on the log dashboard under the same component identity as each host's existing heartbeat
(`jctsh-core` for the Pi, `photo-server` for the M8), reusing the existing MQTT accounts
rather than creating new ones. Had to split the previously-shared `scheduled-reboot.service`
into per-host versions (`scheduled-reboot-pi.service` / `scheduled-reboot-m8.service`)
since the broker address, credentials file, and topic now differ between the two hosts.
M8 needed `mosquitto-clients` installed (apt) since it only had the Python `paho-mqtt`
library, not the CLI. Verified live on both hosts via manual `systemctl start
reboot-complete.service` — confirmed on `/data` (live) and `/log` (persisted, after the
global `_pending` slot flushed on the next distinct message).

## 2026-07-08 (continued)
Added weekly scheduled reboot for the Pi and M8 photo-server (CARD-035), prompted by
the KeepConnect outlet reconfiguration work. `core/maintenance/scheduled-reboot.service`
(`/sbin/reboot`) + per-host timers, deployed as systemd units: Pi Monday 3:00 AM, M8
Monday 4:00 AM. The one-hour stagger matters — the M8's heartbeat script publishes to
the Pi's Mosquitto broker, so an overlapping reboot would read as a false M8-down alert
instead of the Pi just being mid-reboot. Deliberately not synchronized to KeepConnect's
own weekly router reset: that schedule has drifted off its original Wednesday setting,
most likely because its 7-day timer restarts from any reset (scheduled or
outage-triggered) rather than a fixed weekday, so there's nothing stable to sync against
— and a router reboot's brief network blip doesn't meaningfully interact with either
host's own reboot anyway. `Persistent=true` on both timers so a missed window (host off
at 3/4 AM) fires on next boot instead of skipping the week. Verified live via
`systemctl list-timers` on both hosts.

## 2026-07-08
Documented KeepConnect router rebooter (CARD-033). Not a JCTsh component — a
standalone Johnson Creative device (KeepConnect-27F8) that power-cycles the
router/modem on internet-loss detection. New `keepconnect.md` at repo root covers
full config: monitor mode set to "Require Full TCP/HTTPS Success" (switched from
vendor Roundtrip mode to avoid depending on Johnson Creative's own server uptime),
distinct primary/backup test domains (google.com / cloudflare.com), and a 4-minute
post-reset reconnect wait (raised from the 3-minute default to give the modem
headroom for DOCSIS ranging). Physically scoped to the router's own surge-protector
outlet only — the Immich Pi and SmartThings hub were moved to a separate always-on
outlet so router-triggered power cycling can't corrupt the Immich Postgres DB
mid-write or force a Zigbee/Z-Wave mesh rebuild on the hub. Linked from
`jctsh-network.md` and `ENVIRONMENT.md`. Open item carried forward: a clean
scheduled `shutdown -r` cron for the Pi/Immich stack, independent of power-strip
cycling.

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

MQTT hardening. Replaced single shared account (salt-sensor/raspberry) with
per-component accounts: jctsh-log-server, garage-radar, nodered, salt-sensor.
All passwords are strong random strings. Log server credentials moved out of
source code into /etc/jctsh/log-server.env on the Pi, injected via systemd
EnvironmentFile. garage-radar and salt-sensor secrets files (gitignored) updated
with new credentials. Node-RED broker node updated via UI. All four clients
confirmed connected in Mosquitto log.

Note: sudo mosquitto_passwd resets /etc/mosquitto/passwd group back to root —
always run sudo chown root:mosquitto /etc/mosquitto/passwd after any future
password changes, otherwise Mosquitto fails to start.

SSH key auth set up on Pi — passwordless SSH now works from this machine,
eliminating interactive password prompts for deployment commands.

Security hardening continued. Pi user password changed from default "raspberry"
to strong random password via chpasswd. Log dashboard secured with HTTP Basic
Auth (username: jctsh) — credentials injected via DASHBOARD_USER/DASHBOARD_PASS
env vars in /etc/jctsh/log-server.env alongside MQTT credentials. Verified 401
without auth, 200 with auth.

ESPHome/Arduino OTA passwords (currently "OTA"/"ota") deferred — changing OTA
password via OTA is a chicken-and-egg problem; requires USB flash. Low risk as
OTA is LAN-only. Defer to next time hardware is on the bench.

Updated CLAUDE.md: repo layout corrected to list all four components, added
Credentials section covering MQTT accounts, secrets file locations, mosquitto_passwd
ownership gotcha, dashboard Basic Auth, and SSH key auth. Log dashboard
infrastructure entry updated to note auth required. Future Components checklist
updated to include MQTT account creation.

Security hardening complete. Remaining items (MQTT ACLs, MQTT TLS, OTA passwords)
assessed as low risk for a home LAN not exposed to the internet — deferred
indefinitely. Log dashboard Basic Auth confirmed working from browser; credentials
saved in browser so no repeated prompts.

Post-hardening follow-up. Garage radar presence dropped while user was actively
working at workbench — garage door closed. Root cause: HA's MQTT integration was
using the old salt-sensor/raspberry credentials; when those were changed during
MQTT hardening, HA lost its broker connection. With no MQTT, garage radar entities
went unavailable, presence dropped, and the door closed. Fix: added dedicated
homeassistant MQTT account, updated HA MQTT integration via UI (Settings →
Devices & Services → MQTT → Configure). Presence restored immediately.

Lesson: HA MQTT integration credentials are configured through the UI only (not
in any config file) — easy to miss during MQTT password rotations. Always update
HA alongside Node-RED, ESPHome, and sketch secrets.

Pi timezone fixed from EDT to America/Phoenix (MST, UTC-7, no DST). Log server
restarted to clear EDT-timestamped entries. Passwordless sudo restored for pi
user after password change had revoked it.

Documented ST routine triggered by Garage Presence Vswitch turning off: closes
garage door and turns off lights. Added to garage-presence/CLAUDE.md with a note
that any false "presence off" (MQTT outage, HA restart, radar gap) will trigger it
unexpectedly — as confirmed by today's incident.

Repo cleanup. Added JCTsh-Component-Planning-Pattern.md (v1.4),
jctsh-parts-inventory.md, and components/front-porch-temp-sensor/ (instructions
in progress). Added .claude/settings.local.json to .gitignore — file contains
machine-specific absolute paths and should not be version controlled.

## 2026-06-05
Infrastructure maintenance. SmartThings integration had stopped working — root cause
traced to HA Docker container DNS failure. The container's /etc/resolv.conf had been
baked in at creation time (2026-05-15) with a stale DHCP-assigned DNS server
(192.168.1.222) that no longer existed. The Pi restarted on 2026-06-03 and Tailscale
overwrote the host's resolv.conf with its own DNS (100.100.100.100), but the container
kept its frozen copy — leaving HA unable to resolve any external hostnames.

Fix: pinned container DNS to 8.8.8.8/8.8.4.4 in both /etc/docker/daemon.json and a
new core/homeassistant/docker-compose.yml. The compose file also documents the full
container configuration (network_mode: host, volume mount, TZ, restart policy) which
was previously undocumented — container had been started with a bare docker run.

With DNS restored, set up Nabu Casa (HA Cloud, account joscthomas@gmail.com) to
provide an external HTTPS URL. This is required for the SmartThings integration's
OAuth setup flow — even though SmartThings communicates locally with the hub once
configured, the initial OAuth callback needs an externally reachable URL. SmartThings
re-added successfully; all devices visible.

Also cleared a stale production_auth.json from the HA cloud config directory that was
blocking Nabu Casa login with "Cannot login if already logged in."

Network housekeeping: jctsh-network.md updated to add SmartThings hub (192.168.1.112,
MAC 24-FD-5B-01-72-23), hiking-monitor (192.168.1.161, MAC 04-B2-47-97-DF-2C), and
coachproxyos (192.168.1.219, MAC B8-27-EB-BD-C6-63). DHCP reservations confirmed for
all three. SOFTWARE-ENVIRONMENT.md created to document all Pi services (Mosquitto,
Node-RED, HA Docker, log server, Tailscale) with versions, config paths, and
management commands.

## 2026-05-25
Started and completed front-porch-temp-sensor component. Breadboard prototype
fully built and tested (Steps 1–11). Hardware: ESP32 DevKitC-32 (microcontroller)
+ BMP280 (counterfeit BME280) + BH1750 (light sensor) sharing an I2C bus on
GPIO21 (SDA) / GPIO22 (SCL). ESPHome firmware with MQTT discovery, 60-second
sensor updates, and a 5-minute heartbeat.

Counterfeit BME280 issue: all three Podazz BME280 modules in the first batch
are actually BMP280s (no humidity support). Deployed with bmp280_i2c platform;
genuine BME280s ordered. Humidity shows Unknown in HA — expected. YAML has a
TODO comment to swap back when genuine modules arrive.

Whitespace-in-path issue (ESP-IDF compiler): "JCT Documents" path blocked
flashing. Fix: copy YAML + secrets to C:\esphome\front-porch-temp-sensor\ for
all flash operations. Established as standard for all ESPHome components going
forward.

Dedicated MQTT account created: front-porch-temp-sensor. Per-component MQTT
accounts are the established standard.

Two HA automations: Front Porch Temp Alert + Reminder (fires on temp >= threshold
6am–10pm; sends reminder 15 min later, once, via mode: single) and Front Porch
Temp Dropping (fires on temp < threshold 6am–10pm). Both notify
notify.mobile_app_pixel_10_pro_xl and notify.mobile_app_pixel_7_pro. Door sensor
condition removed at Robin's request — temperature and time window only. Lux
threshold removed in favor of explicit 6am–10pm time window.

End-to-end test complete (Steps 1–11). All 10 tests pass; time-window suppression
test (Step 6) skipped. Sensor readings confirmed in HA: 85–90°F, 13.46 psi,
illuminance responsive to light changes; humidity Unknown as expected.

Step 12 (perfboard transfer) deferred pending perfboard delivery. perfboard-layout.md
complete. mounting.md and component README.md written. Root README.md, parts
inventory, and CLAUDE.md credentials section updated.

## 2026-05-21
Installed Tailscale on Pi for remote access. Pi Tailscale IP: 100.70.162.24.
All local services (log dashboard, HA, Node-RED) now reachable from anywhere via
the Tailscale IP — no port forwarding, no public IP exposure. Install Tailscale on
any device and sign in with the same account to get access.

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
