# JCTsh Heartbeat — photo-server

Publishes a heartbeat every 30 minutes from photo-server to the JCTsh log dashboard and
Node-RED watchdog, confirming both the box and the Immich containers are healthy.

---

## How It Works

A Python script runs on photo-server as a systemd timer (2 minutes after boot, then every
30 minutes). Unlike `coachproxyos` (which roams networks and reaches home over Tailscale),
photo-server is stationary on the home LAN, so it publishes directly to the home Pi's
Mosquitto broker at `192.168.1.117:1883` — no Tailscale involved.

Each run checks Docker health status (`docker inspect --format '{{.State.Health.Status}}'`)
for all four Immich containers: `immich_server`, `immich_postgres`,
`immich_machine_learning`, `immich_redis`. If all are `healthy`, it publishes a normal
`System` heartbeat. If any container is missing, stopped, or reports a non-`healthy`
status, it publishes an `Alert`-category log message instead (not prefixed
`"Heartbeat - "`, so it doesn't collapse and stays visible) while still publishing the
heartbeat topic — this keeps the watchdog from firing on an Immich-level problem where the
box itself is fine; the log dashboard is the place that surfaces it.

Topics:
- `jctsh/server/photo-server/log` — picked up by the log server, visible in the dashboard
- `jctsh/server/photo-server/heartbeat` — monitored by the Node-RED watchdog (35-minute timeout)

If photo-server is powered off or Docker/Immich is down at the OS level, messages stop
entirely and the watchdog alerts after 35 minutes of silence, same as any other component.

---

## Source Files in Repo

| File | Deployed to |
|---|---|
| `components/photo-server/photo-server-heartbeat.py` | `/usr/local/bin/photo-server-heartbeat.py` |
| `components/photo-server/photo-server-heartbeat.service` | `/etc/systemd/system/photo-server-heartbeat.service` |
| `components/photo-server/photo-server-heartbeat.timer` | `/etc/systemd/system/photo-server-heartbeat.timer` |

## Files on photo-server (not in repo)

| File | Purpose |
|---|---|
| `/etc/jctsh/heartbeat.env` | MQTT credentials (`MQTT_PASSWORD=...`) — chmod 640, owner root:jct |

---

## Deployment

```
scp components/photo-server/photo-server-heartbeat.py jct@192.168.1.165:/tmp/
scp components/photo-server/photo-server-heartbeat.service jct@192.168.1.165:/tmp/
scp components/photo-server/photo-server-heartbeat.timer jct@192.168.1.165:/tmp/
ssh jct@192.168.1.165 "sudo install -m 755 /tmp/photo-server-heartbeat.py /usr/local/bin/photo-server-heartbeat.py && sudo cp /tmp/photo-server-heartbeat.service /etc/systemd/system/ && sudo cp /tmp/photo-server-heartbeat.timer /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl restart photo-server-heartbeat.timer"
```

---

## MQTT Account

Account `photo-server` added to home Pi Mosquitto (`/etc/mosquitto/passwd`). Password
stored in `/etc/jctsh/heartbeat.env` on photo-server and in `credentials.local.md`.

---

## Installation Notes

- `python3-paho-mqtt` installed via `apt` (2.1.0) — photo-server runs Python 3.14, no
  version constraint like the eRVin Pi's Python 3.7.
- `jct` is already in the `docker` group, so the heartbeat service runs as `User=jct`
  (not root) and can call `docker inspect` without sudo.
- paho-mqtt 2.x requires `mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)` — the older
  no-argument constructor is deprecated/removed.

---

## Confirmed Details

| Item | Value |
|---|---|
| Heartbeat visible in dashboard | Yes — component `photo-server`, category `System` |
| Log topic | `jctsh/server/photo-server/log` |
| Watchdog topic | `jctsh/server/photo-server/heartbeat` |
| Broker | Home Pi — `192.168.1.117:1883`, direct LAN (no Tailscale) |
| Timer schedule | 2min after boot, every 30min thereafter |
| Watchdog timeout | 35 minutes |
| Containers checked | immich_server, immich_postgres, immich_machine_learning, immich_redis |
| paho-mqtt version | 2.1.0 (apt) |

Verified live 2026-07-04: heartbeat confirmed on dashboard (`/data` endpoint, collapsing
correctly into a single row with count). Degraded-path (container down) logic reviewed but
not live-tested, to avoid disrupting the in-progress Immich photo migration.

---

## Note on Dashboard Display

Same collapsing behavior as every other component: consecutive `"Heartbeat - "` messages
collapse into one row with count and time range. If Immich degrades, the `Alert` message
does not collapse and appears as its own row each time the check runs, making a stuck
problem visible rather than silently folded into a count.
