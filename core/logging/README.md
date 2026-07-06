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
      ├── Keeps last 200 entries in memory (plus one pinned entry per
      │   component so infrequent reporters always show — see below)
      ├── Appends all entries to /home/pi/jctsh/logs/jctsh.log
      │   (rotates at 1 MB, 5 files kept)
      └── Serves dashboard at http://raspberrypi.local/  (Basic Auth)
```

### Per-Component Minimum Retention

The live dashboard (`/` and `/data`) only keeps the last 200 entries across *all*
components combined. A component that reports infrequently (e.g. `salt-sensor`, roughly
every 12h) can get crowded out of that window within hours by components that report
every few minutes (`front-porch-temp-sensor`, `garage-radar` presence events, etc.) — even
though its history is always intact in the full `/log` file.

Fixed 2026-07-06: `log_server.py` tracks a `_last_seen` dict (component → its most recent
entry, whatever that entry currently is — an active heartbeat group, an active pending
entry, or a stale one that already scrolled out of the last-200 window). `_snapshot()`
always includes one entry per known component, pulling from `_last_seen` for any component
not otherwise present in the current window. This guarantees every component that has
logged at least once since the server started shows up somewhere in the live view — sorted
into its correct chronological position by timestamp, so a stale entry is visually obvious
(old timestamp) rather than looking like fresh activity.

`_last_seen` resets on service restart, same as `_entries`/`_hb_groups`/`_pending` — a
component reappears in the live view on its next report after a restart, same as before
this fix.

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

### Dashboard Live Updates vs. Text Selection

The dashboard polls `/data` every 5s and replaces the table body's `innerHTML` to show new
entries. Naively doing this on every poll wipes any in-progress or just-finished text
selection (and, as a side effect, corrupts drag-selection direction — the browser's
selection anchor was re-resolving against freshly created DOM nodes mid-drag, causing
already-selected lines above the cursor to get pulled into the selection unexpectedly).

Fixed (2026-07-06) by skipping the re-render while there's an active selection, plus a
3-second grace period after any selection activity (`selectionchange`, `mousedown`,
`mouseup` on the table) before resuming — a plain "is there a selection right now" check
had a race where the render could slip through in the split-second gap during selection
finalization (e.g., right as the mouse button is released). If this bug resurfaces, check
that `_maybeRender()` in the dashboard's `<script>` block is still being gated by both
`_hasSelection()` and the grace timer before touching the DOM.

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
