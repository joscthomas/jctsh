# JCTsh Log Server

Central log aggregator for all JCTsh components — subscribes to all component log
topics via MQTT wildcard, applies duplicate suppression, and serves a live dashboard
at `http://raspberrypi.local/`.

**Status:** Production — deployed as a systemd service on the Pi

---

## What It Solves

Without centralized logging, diagnosing issues across eight+ components means checking
each device individually. This server collects all component log messages in one place,
collapses repetitive heartbeats into single summary rows, and makes the full system
state visible in a browser on any device on the network.

---

## Architecture

```
All JCTsh components
      │  MQTT: jctsh/+/+/log  (wildcard)
      ▼
log_server.py  (Raspberry Pi)
      ├── Applies duplicate suppression and heartbeat collapsing
      ├── Keeps last 200 entries in memory
      ├── Appends all entries to /home/pi/jctsh/logs/jctsh.log
      │   (rotates at 1 MB, 5 files kept)
      └── Serves dashboard at http://raspberrypi.local/  (Basic Auth)
```

Also publishes its own hourly watchdog heartbeat to `jctsh/core/log-server/log` to
confirm the log server and MQTT broker are both alive.

---

## Quick Start

### Install dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

### Run manually (for testing)

```bash
sudo python3 log_server.py
```

Open `http://raspberrypi.local/` — Basic Auth, user: `jctsh`, password in
`/etc/jctsh/log-server.env`.

### Install as a systemd service

```bash
sudo nano /etc/systemd/system/jctsh-logging.service
```

Paste:

```ini
[Unit]
Description=JCTsh Log Server
After=network.target mosquitto.service

[Service]
ExecStart=/usr/bin/python3 /home/pi/jctsh/core/logging/log_server.py
WorkingDirectory=/home/pi/jctsh/core/logging
Restart=always
User=pi
EnvironmentFile=/etc/jctsh/log-server.env
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable jctsh-logging
sudo systemctl start jctsh-logging
```

### Deploy updated script

```bash
scp core/logging/log_server.py pi@raspberrypi.local:/home/pi/jctsh/core/logging/
ssh pi@raspberrypi.local "sudo systemctl restart jctsh-logging"
```

### Check status

```bash
sudo systemctl status jctsh-logging
journalctl -u jctsh-logging -f
```

---

## Log Message Format

All components publish to `jctsh/<type>/<component>/log` with this payload:

```json
{ "component": "salt-sensor", "category": "MQTT", "message": "Connected." }
```

| Category | Use for |
|---|---|
| `System` | Device health — boot, WiFi, heartbeat |
| `MQTT` | Broker connection events |
| `Sensor` | Sensor readings and state transitions |
| `Alert` | Threshold crossings requiring attention |
| `Test` | Messages generated during test mode |

Timestamps are added by the log server on receipt — do not include them in the payload.

### Heartbeat Collapsing

Consecutive same-state heartbeat messages per component are collapsed into a single row
showing count, time range, and last values. Messages must start with `"Heartbeat - "` to
be collapsed reliably. Messages without this prefix only collapse when consecutive
identical runs are uninterrupted.

---

## Log File Location

```
/home/pi/jctsh/logs/jctsh.log      — current
/home/pi/jctsh/logs/jctsh.log.1    — most recent rotation
/home/pi/jctsh/logs/jctsh.log.2–5  — older rotations
```

---

## Files

| File | Purpose |
|---|---|
| `log_server.py` | Python log server — deployed to `/home/pi/jctsh/core/logging/` |
| `requirements.txt` | Python dependencies |
