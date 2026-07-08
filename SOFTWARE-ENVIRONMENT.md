# JCTsh Software Environment

Reference for what is installed and running on the home Pi. Useful for rebuilding, troubleshooting, or understanding service interdependencies. For physical devices see `ENVIRONMENT.md`. For architecture and Claude instructions see `CLAUDE.md`.

## Host: Home Pi

| Property | Value |
|---|---|
| Hostname | `raspberrypi.local` / `192.168.1.117` (DHCP reserved) |
| Tailscale IP | `100.70.162.24` |
| OS | Debian GNU/Linux 13 (Trixie) |
| Architecture | `aarch64` (ARM64) |
| Kernel | Linux 6.12 |
| Timezone | `America/Phoenix` (MST, UTC-7, no DST) |

## Services

All services start automatically at boot. None require manual intervention under normal operation.

### Home Assistant

| Property | Value |
|---|---|
| Version | `stable` (auto-tracks latest stable release) |
| Image | `ghcr.io/home-assistant/home-assistant:stable` |
| Managed by | Docker (`unless-stopped` restart policy) |
| Compose file | `core/homeassistant/docker-compose.yml` (repo) → `/home/pi/docker-compose.yml` (Pi) |
| Config volume | `/home/pi/homeassistant` → `/config` inside container |
| Web UI | `http://raspberrypi.local:8123` |
| External access | Nabu Casa (HA Cloud) — account `joscthomas@gmail.com` |

DNS is explicitly pinned to `8.8.8.8` / `8.8.4.4` in both the compose file and `/etc/docker/daemon.json`. This prevents a recurrence of the June 2026 outage where a stale DHCP-assigned DNS server in the container caused total cloud connectivity loss.

To manage:
```bash
docker restart homeassistant                  # restart after config change
cd /home/pi && docker compose up -d           # recreate from compose file
docker logs -f homeassistant                  # live logs
```

### Mosquitto MQTT Broker

| Property | Value |
|---|---|
| Version | 2.0.21 |
| Managed by | systemd (`mosquitto.service`) |
| Config | `/etc/mosquitto/mosquitto.conf` + `/etc/mosquitto/conf.d/local.conf` |
| Port | 1883 |
| Auth | Required — `allow_anonymous false`, passwords in `/etc/mosquitto/passwd` |
| Persistence | `/var/lib/mosquitto/` |
| Log | `/var/log/mosquitto/mosquitto.log` |
| Protocol | MQTT v5 (Node-RED broker node); MQTT v3.1.1 (ESP32/ESPHome/HA — Mosquitto 2.x accepts both simultaneously) |

Version-controlled config snapshot: `core/mqtt/mosquitto.conf`.

To manage:
```bash
sudo systemctl restart mosquitto
sudo mosquitto_passwd -b /etc/mosquitto/passwd <username> <password>
sudo chown root:mosquitto /etc/mosquitto/passwd   # required after any passwd change
```

### Node-RED

| Property | Value |
|---|---|
| Version | v4.1.10 |
| Node.js | v22.22.2 |
| Managed by | systemd (`nodered.service`) |
| Run as | `pi` user, working dir `/home/pi` |
| Web UI | `http://raspberrypi.local:1880` |
| Settings | `/home/pi/.node-red/settings.js` |

Version-controlled settings snapshot: `core/node-red/settings.js`.

**Flow deployment:** Import flows via the Node-RED UI (not SCP). Open the UI, use the hamburger menu → Import → paste JSON.

To manage:
```bash
sudo systemctl restart nodered
sudo systemctl status nodered
```

### JCTsh Log Server

| Property | Value |
|---|---|
| Runtime | Python 3.13.5 |
| Managed by | systemd (`jctsh-logging.service`) |
| Script | `/home/pi/jctsh/core/logging/log_server.py` |
| Credentials | `/etc/jctsh/log-server.env` (injected via systemd `EnvironmentFile`) |
| Web UI | `http://raspberrypi.local/` (port 80, HTTP Basic Auth — user: `jctsh`) |
| MQTT topic | Subscribes to `jctsh/#` |

To deploy an updated script:
```bash
scp core/logging/log_server.py pi@raspberrypi.local:/home/pi/jctsh/core/logging/
ssh pi@raspberrypi.local "sudo systemctl restart jctsh-logging"
```

### Tailscale

| Property | Value |
|---|---|
| Version | 1.98.4 |
| Managed by | systemd (`tailscaled.service`) |
| Account | `joscthomas@gmail.com` |
| Tailscale IP | `100.70.162.24` |

Tailscale manages `/etc/resolv.conf` on this Pi (sets nameserver to `100.100.100.100`). The HA Docker container uses its own `/etc/resolv.conf` pinned to `8.8.8.8`/`8.8.4.4` — independent of host DNS.

### Docker

| Property | Value |
|---|---|
| Version | 29.5.0 |
| Managed by | systemd (`docker.service`) |
| Daemon config | `/etc/docker/daemon.json` — sets DNS `["8.8.8.8", "8.8.4.4"]` for all containers |

## Service Startup Order

At boot, systemd brings up services in parallel. HA (Docker) depends on Docker daemon. All MQTT clients (HA, Node-RED, log server, ESPHome devices) connect to Mosquitto independently — brief startup ordering differences are handled by each client's reconnect logic.

```
systemd
  ├── docker.service → homeassistant (Docker container, auto-restart)
  ├── mosquitto.service
  ├── nodered.service
  ├── jctsh-logging.service
  └── tailscaled.service
```

### Scheduled Reboot

| Property | Value |
|---|---|
| Managed by | systemd timer (`scheduled-reboot.timer` → `scheduled-reboot.service`) |
| Schedule | Weekly, Monday 3:00 AM (`America/Phoenix`) |
| Action | Publish MQTT notice, then `/sbin/reboot` |

Version-controlled unit files: `core/maintenance/scheduled-reboot-pi.service` (deployed as
`scheduled-reboot.service`), `core/maintenance/scheduled-reboot-pi.timer` (deployed as
`scheduled-reboot.timer`). `Persistent=true` — if the Pi is powered off at the scheduled
time, it reboots on next boot instead of skipping the week.

Staggered one hour ahead of the M8 photo-server's own weekly reboot (Monday 4:00 AM) so the M8's heartbeat script isn't trying to publish to Mosquitto while the Pi is mid-reboot. See `components/photo-server/operations.md`.

To check: `systemctl list-timers scheduled-reboot.timer`

**Dashboard visibility (added 2026-07-08):** `scheduled-reboot.service` publishes
`"Scheduled reboot about to occur."` (component `jctsh-core`, category `System`) to
`jctsh/core/log-server/log` immediately before rebooting. A second unit,
`reboot-complete.service` (`core/maintenance/reboot-complete-pi.service`, runs on every
boot via `WantedBy=multi-user.target`, `After=mosquitto.service`), publishes
`"Boot complete."` to the same topic/component once the broker is back up. Together these
give a positive pair of dashboard entries confirming the reboot actually happened and the
box came back — rather than relying on the absence of a watchdog silence alert. Both reuse the existing `jctsh-log-server` MQTT account credentials from
`/etc/jctsh/log-server.env` via the `mosquitto_pub` CLI — no new MQTT account. Verified
live 2026-07-08 via manual `systemctl start reboot-complete.service`.

## Nabu Casa (HA Cloud)

Required for SmartThings integration. SmartThings uses OAuth during setup, which needs an externally reachable HTTPS callback URL — Nabu Casa provides this. If the SmartThings integration is ever removed and needs to be re-added, Nabu Casa must be signed in first (Settings → Home Assistant Cloud), or setup will fail with "No OAuth services available."

Once set up, SmartThings communicates with the local SmartThings hub directly — Nabu Casa is only needed for the initial OAuth flow and for remote HA access.
