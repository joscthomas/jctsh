# photo-server — Operations Guide

Day-to-day maintenance for the GMKtec M8 (`photo-server`, `192.168.1.165`). For build steps see `photo-server-claude-code-instructions.md`; for monitoring see `heartbeat.md`.

## Scheduled Reboot

| Property | Value |
|---|---|
| Managed by | systemd timer (`scheduled-reboot.timer` → `scheduled-reboot.service`) |
| Schedule | Weekly, Monday 4:00 AM (`America/Phoenix`) |
| Action | Publish MQTT notice, then `/sbin/reboot` |

Version-controlled unit files: `core/maintenance/scheduled-reboot-m8.service` (deployed as
`scheduled-reboot.service`), `core/maintenance/scheduled-reboot-m8.timer` (deployed as
`scheduled-reboot.timer`). `Persistent=true` — if the M8 is powered off at the scheduled
time, it reboots on next boot instead of skipping the week.

**Value:** clears memory creep in long-running Docker containers (Immich server/ML), applies pending kernel/package updates from `unattended-upgrades` that need a reboot to take effect, and exercises the boot path regularly so a startup regression (bad mount, container not set to auto-restart) surfaces on a Monday morning instead of during an actual outage.

Staggered one hour behind the Pi's own weekly reboot (Monday 3:00 AM) — the M8's heartbeat script publishes to the Mosquitto broker on the Pi, so overlapping the two would produce a false "M8 down" reading while it's really just the Pi that's mid-reboot.

To check: `systemctl list-timers scheduled-reboot.timer`

All four Immich containers (`immich_server`, `immich_postgres`, `immich_machine_learning`, `immich_redis`) are on Docker's `restart: unless-stopped` policy and come back automatically after reboot — confirmed working 2026-07-08 after a manual power-cycle for outlet reconfiguration (see `keepconnect.md`).

**Dashboard visibility (added 2026-07-08):** `scheduled-reboot.service` publishes
`"Scheduled reboot about to occur."` (component `photo-server`, category `System`) to
`jctsh/server/photo-server/log` immediately before rebooting. A second unit,
`reboot-complete.service` (`core/maintenance/reboot-complete-m8.service`, runs on every
boot via `WantedBy=multi-user.target`, `After=network-online.target`), publishes
`"Boot complete."` to the same topic/component once the M8 has network access to reach
the Pi's broker. Both use the `photo-server` MQTT account already set up for the
heartbeat script (`/etc/jctsh/heartbeat.env`) and the `mosquitto_pub` CLI — required
installing the `mosquitto-clients` apt package (not previously present on the M8; the
heartbeat script uses the Python `paho-mqtt` library instead). Verified live 2026-07-08
via manual `systemctl start reboot-complete.service`.

## Router Reboot Coordination

KeepConnect (the router rebooter — see `keepconnect.md`) resets the router on its own weekly schedule, currently landing on a day that has drifted from its original Wednesday setting. This is expected: KeepConnect's "every 7 days" timer appears to restart from *any* reset, scheduled or outage-triggered, so the weekday it lands on shifts over time and can't be relied on as fixed. The Pi and M8 reboot schedule above is intentionally not synchronized to it — a router reboot is a brief (~30 sec cut, ~4 min reconnect) network blip that both machines tolerate regardless of whether they happen to be mid-boot at the same time.
