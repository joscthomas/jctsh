# JCTsh Heartbeat — Pleasure-Way Firefly Interface

Publishes a `Heartbeat - online.` message every 30 minutes from the RV Pi to the JCTsh log dashboard and Node-RED watchdog, confirming the Pi and Tailscale are alive.

---

## How It Works

A Python script runs on the RV Pi as a systemd timer (2 minutes after boot, then every 30 minutes). It connects to the home Pi's MQTT broker via Tailscale and publishes to two topics:

- `jctsh/rv/coachproxyos/log` — picked up by the log server, visible in the dashboard
- `jctsh/rv/coachproxyos/heartbeat` — monitored by the Node-RED watchdog (35-minute timeout)

When the Pi is powered off or Tailscale is down, messages stop. The watchdog alerts after 35 minutes of silence. The last heartbeat timestamp in the dashboard shows how long ago the Pi was last online.

---

## Source Files in Repo

| File | Deployed to |
|---|---|
| `components/p-w-firefly/jctsh-heartbeat.py` | `/usr/local/bin/jctsh-heartbeat.py` |
| `components/p-w-firefly/jctsh-heartbeat.timer` | `/etc/systemd/system/jctsh-heartbeat.timer` |

## Files on RV Pi (not in repo)

| File | Purpose |
|---|---|
| `/etc/jctsh/heartbeat.env` | MQTT credentials (`MQTT_PASSWORD=...`) — chmod 640, owner root:pi |
| `/etc/systemd/system/jctsh-heartbeat.service` | oneshot service that runs the script |

---

## Deployment

```
scp components/p-w-firefly/jctsh-heartbeat.py pi@100.90.246.43:/tmp/jctsh-heartbeat.py
ssh pi@100.90.246.43 "sudo install -m 755 /tmp/jctsh-heartbeat.py /usr/local/bin/jctsh-heartbeat.py && sudo cp /etc/systemd/system/jctsh-heartbeat.timer /etc/systemd/system/jctsh-heartbeat.timer.bak"
ssh pi@100.90.246.43 "sudo sed -i 's/OnUnitActiveSec=1h/OnUnitActiveSec=30min/' /etc/systemd/system/jctsh-heartbeat.timer && sudo systemctl daemon-reload && sudo systemctl restart jctsh-heartbeat.timer"
```

---

## MQTT Account

Account `coachproxyos` added to home Pi Mosquitto (`/etc/mosquitto/passwd`). Password stored in `/etc/jctsh/heartbeat.env` on RV Pi.

---

## Installation Notes

- `paho-mqtt 1.6.1` required — version 2.x requires Python 3.8+ and the eRVin image has Python 3.7
- `python3-pip` installed from `archive.raspberrypi.org/debian` source
- paho-mqtt installed as the `pi` user lands at `/coachproxy/home/pi/.local/lib/python3.7/site-packages` — the eRVin image root is under `/coachproxy/`. Without `User=pi` in the service file, the service runs as root and cannot find the module. The service file must include `User=pi` under `[Service]`.

---

## Confirmed Details

| Item | Value |
|---|---|
| Heartbeat visible in dashboard | Yes — component `coachproxyos`, category `System` |
| Log topic | `jctsh/rv/coachproxyos/log` |
| Watchdog topic | `jctsh/rv/coachproxyos/heartbeat` |
| Broker | Home Pi — `100.70.162.24:1883` via Tailscale |
| Timer schedule | 2min after boot, every 30min thereafter |
| Watchdog timeout | 35 minutes |
| paho-mqtt version | 1.6.1 |

---

## Note on Dashboard Display

The log server collapses consecutive `Heartbeat - ` messages from the same component into a single row with a count and time range. A single heartbeat is displayed immediately; the count increments with each subsequent heartbeat. The collapsed entry shows count and `[first–last]` timestamp range.
