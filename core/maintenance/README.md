# core/maintenance — Scheduled Maintenance & Update Checks

systemd units and their Python scripts for scheduled maintenance work across the Pi and
M8: OS/firmware/container update checks, scheduled reboots with coordinated
pre/post-reboot notifications, backups, and image pulls. Deployed to `/usr/local/bin/`
on whichever host each unit's `.service` targets (see each unit's `ExecStart`) — check
`network/jctsh-network.md`'s Scheduled Maintenance Windows table before adding a new recurring
job here (`JCTsh-Build-Standards.md` §9.5, ≥1 hour clearance from other jobs).

**Status:** Production — every unit here is a currently-running scheduled job on the Pi
and/or M8.

---

## Update Checks

Notify-only (never auto-apply) — each posts an available-update finding to the log
dashboard and, via `open_kanban_pr.py` (CARD-0128), opens a placeholder PR against
`tos/kanban-board.md`.

| File | Checks |
|---|---|
| `container_update_check.py` | Shared library (`check_services()`) — generic GitHub-Releases-API update check for any Docker container, per `JCTsh-Build-Standards.md` §9.7. Per-host wrapper scripts (`hosts/m8/container-update-check.py`, `core/homeassistant/container-update-check.py`) import this and declare their own `SERVICES` list. |
| `container-update-check-m8.service`/`.timer`, `container-update-check-pi.service`/`.timer` | Run each host's own wrapper script daily |
| `pi-maintenance-check.py` | Pi OS/firmware — apt-upgradable packages, stale running kernel (CARD-0125, `maintenance-check.py`'s Pi sibling; the M8-side script itself lives in `hosts/m8/`) |
| `immich-update-check.service`/`.timer` | Runs `components/photo-server/immich-update-check.py` — Immich exposes its own `/api/server/version-check` API directly, more authoritative than a GitHub tag, so it doesn't use `container_update_check.py`'s generic path |

## Reboots

| File | Purpose |
|---|---|
| `scheduled-reboot-pi.service`/`.timer`, `scheduled-reboot-m8.service`/`.timer` | Weekly scheduled reboot per host, staggered (the M8's heartbeat publishes to the Pi's broker, so overlapping reboots would produce a false "down" reading) — publishes a "Scheduled reboot about to occur" log line before rebooting; the Pi's variant also snapshots the journal first (`journal-snapshot.service`, since `systemd-journald` uses volatile storage — CARD-0246) |
| `reboot-complete-pi.service`, `reboot-complete-m8.service` | Publishes "Boot complete." on next boot after a scheduled reboot |
| `reboot-health-check.py`/`.service` | Post-reboot health check (CARD-0158) — runs once at boot, oneshot |

## Backup

| File | Purpose |
|---|---|
| `pi1-backup-to-m8.py`/`.service`/`.timer` | Weekly backup of the Pi's HA + Mosquitto state to the M8 (CARD-0177) — the disaster-recovery gap CARD-0172's audit found |

## Image Pull

| File | Purpose |
|---|---|
| `pi-image-pull.py` | `ionice`-wrapped `ctr`-based Docker/containerd image pull for the Pi (CARD-0269/CARD-0268) — scheduled, not manual, since a plain `docker pull` can starve HA's own I/O on the Pi's shared USB 2.0 bus |

## Heartbeat

| File | Purpose |
|---|---|
| `pi-heartbeat.py`/`.service`/`.timer` | Publishes the Pi's own container-health heartbeat (extend the script's `CONTAINERS` list for more than `homeassistant`) |
