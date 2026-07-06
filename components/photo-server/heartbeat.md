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

## Bug Found and Fixed (2026-07-06): False Watchdog Alerts

Joseph reported repeated "Component photo-server silent for 35 minutes" watchdog alerts
despite the server running fine. Investigation via Node-RED's own runtime log
(`journalctl -u nodered`, which logs every `node.warn()` call in the watchdog flow,
including "Timer set for photo-server" on every heartbeat receipt) showed the `/log` topic
was arriving 100% reliably (confirmed via the dashboard — 74/74 heartbeats collapsed with
no gaps) while the `/heartbeat` topic was intermittently dropped, roughly every 2-3 cycles,
causing the watchdog's 35-minute timer to expire even though the script itself logged
`Heartbeat sent. status=online` every single run with no gaps.

**Root cause:** the original script published both topics with `client.publish(..., qos=1)`
back-to-back, then called `client.disconnect()` immediately, without running the network
loop. `publish()` writes the outgoing packet to the socket but does not guarantee delivery
for QoS 1 without the client processing broker traffic — an immediate `disconnect()` can
close the socket before the second publish's packet is fully flushed. The first (`/log`)
message reliably went out; the second (`/heartbeat`) was the one intermittently lost.

**Fix:** call `client.loop_start()` after connecting, then `wait_for_publish(timeout=5)` on
both publish results before `loop_stop()` + `disconnect()`. This keeps the network loop
running long enough to actually confirm both QoS-1 deliveries. Verified by firing 5 rapid
back-to-back manual runs (the pattern that most reliably reproduced the drop) — all 5
registered in Node-RED's log with no gaps.

**Note:** `components/p-w-firefly/jctsh-heartbeat.py` (coachproxyos, the RV Pi) uses the
identical publish-then-disconnect pattern and almost certainly has the same latent bug —
just less noticeable since a stray "coachproxyos silent" alert is easy to dismiss for a
device that's expected to roam in and out of range. Not fixed yet — the RV Pi wasn't
reachable (Tailscale down) when this was found. See CARD-031.

---

## Note on Dashboard Display

Same collapsing behavior as every other component: consecutive `"Heartbeat - "` messages
collapse into one row with count and time range. If Immich degrades, the `Alert` message
does not collapse and appears as its own row each time the check runs, making a stuck
problem visible rather than silently folded into a count.
