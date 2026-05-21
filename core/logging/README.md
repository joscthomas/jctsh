# JCTsh Log Server

Central log aggregator for all JCTsh components. Subscribes to `jctsh/+/+/log` via
MQTT, applies duplicate suppression, and serves a live dashboard at `http://JCTsh.local/`.

## How it works

- Listens on MQTT topic `jctsh/+/+/log` (wildcard matches any type and component)
- Expects JSON payloads: `{"component":"...","category":"...","message":"..."}`
- Timestamps messages on receipt
- Collapses consecutive identical messages into a single entry with a repeat count
- Keeps the last 200 entries in memory for the dashboard
- Appends all entries to `/home/pi/jctsh/logs/jctsh.log` (rotates at 1 MB, 5 files kept)

## Install dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

## Run manually (for testing)

```bash
python3 log_server.py
```

Open `http://raspberrypi.local/` to see the dashboard (requires Basic Auth, user: `jctsh`).
Remote access via Tailscale: `http://100.70.162.24/`

> **Note:** Port 80 requires elevated privileges. The systemd service below grants the
> capability using `AmbientCapabilities`. To test manually as `pi`, use `sudo`:
> ```bash
> sudo python3 log_server.py
> ```

## Install as a systemd service

### 1. Create the service file

```bash
sudo nano /etc/systemd/system/jctsh-logging.service
```

Paste the following:

```ini
[Unit]
Description=JCTsh Log Server
After=network.target mosquitto.service

[Service]
ExecStart=/usr/bin/python3 /home/pi/jctsh/core/logging/log_server.py
WorkingDirectory=/home/pi/jctsh/core/logging
Restart=always
User=pi
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
```

### 2. Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable jctsh-logging
sudo systemctl start jctsh-logging
```

### 3. Check status

```bash
sudo systemctl status jctsh-logging
journalctl -u jctsh-logging -f
```

## Log file location

```
/home/pi/jctsh/logs/jctsh.log        # current
/home/pi/jctsh/logs/jctsh.log.1      # most recent rotation
/home/pi/jctsh/logs/jctsh.log.2      # ...up to .5
```

## MQTT log message format

All components must publish to `jctsh/<type>/<component>/log` with this JSON payload:

```json
{ "component": "salt-sensor", "category": "MQTT", "message": "Connected." }
```

| Category | Color  | Use for |
|----------|--------|---------|
| `MQTT`   | cyan   | MQTT connection/publish events |
| `System` | green  | Boot, WiFi, operational messages |
| `Sensor` | white  | Sensor readings |
| `Alert`  | red/orange | Warning and critical alerts |
| `Test`   | orange | Test mode messages |
