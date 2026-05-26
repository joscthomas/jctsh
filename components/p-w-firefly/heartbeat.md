# JCTsh Heartbeat — Pleasure-Way Firefly Interface

Publishes an hourly `Heartbeat - online.` message from the RV Pi to the JCTsh log dashboard, confirming the Pi and Tailscale are alive.

---

## How It Works

A Python script runs on the RV Pi as a systemd timer (2 minutes after boot, then every hour). It connects to the home Pi's MQTT broker via Tailscale and publishes to `jctsh/rv/coachproxyos/log`. The JCTsh log server subscribes to `jctsh/+/+/log` and displays the message in the dashboard under component `coachproxyos`.

When the Pi is powered off or Tailscale is down, messages stop — the last heartbeat timestamp in the dashboard shows how long ago the Pi was last online.

---

## Files on RV Pi

| File | Purpose |
|---|---|
| `/usr/local/bin/jctsh-heartbeat.py` | Python script — publishes heartbeat via paho-mqtt |
| `/etc/jctsh/heartbeat.env` | MQTT credentials (`MQTT_PASSWORD=...`) — chmod 640, owner root:pi |
| `/etc/systemd/system/jctsh-heartbeat.service` | oneshot service that runs the script |
| `/etc/systemd/system/jctsh-heartbeat.timer` | Fires 2min after boot, then every hour |

---

## MQTT Account

Account `coachproxyos` added to home Pi Mosquitto (`/etc/mosquitto/passwd`). Password stored in `/etc/jctsh/heartbeat.env` on RV Pi.

---

## Installation Notes

- `paho-mqtt 1.6.1` required — version 2.x requires Python 3.8+ and the eRVin image has Python 3.7
- `python3-pip` installed from `archive.raspberrypi.org/debian` source

---

## Confirmed Details

*(Confirmed complete — May 2026)*

| Item | Value |
|---|---|
| Heartbeat visible in dashboard | Yes — component `coachproxyos`, category `System` |
| MQTT topic | `jctsh/rv/coachproxyos/log` |
| Broker | Home Pi — `100.70.162.24:1883` via Tailscale |
| Timer schedule | 2min after boot, hourly thereafter |
| paho-mqtt version | 1.6.1 |

---

## Note on Dashboard Display

The log server collapses consecutive `Heartbeat - ` messages from the same component into a single row with a count and time range. A single heartbeat is held in memory until the next one arrives — the dashboard entry first appears after the second heartbeat (roughly one hour after boot). On subsequent visits, the collapsed entry shows the count and `[first–last]` timestamp range.
