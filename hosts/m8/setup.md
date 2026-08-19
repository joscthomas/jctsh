# M8 — Base Machine Setup

**Split from `components/photo-server/setup.md`, 2026-08-19** — see `kanban-board.md` CARD-0096's addendum. That file retains everything specific to the Immich build (drive mapping/migration, since the drives were provisioned specifically for the photo library — see `components/photo-server/backup.md`).

## Base OS

- OS: **Ubuntu 26.04 LTS** (not a placeholder "current LTS" — confirmed via `lsb_release -a`)
- M8 has two identical-looking ethernet ports — only `eno1` carries the DHCP lease; the other silently drops network if used by mistake. See `network.md` for the full network reference.

## Scheduled Weekly Reboot (CARD-0035/CARD-0036)

Built beyond the original photo-server instructions doc's plan — `core/maintenance/scheduled-reboot-m8.service`/`.timer` and `reboot-complete-m8.service`, requiring `mosquitto-clients` to be installed (Immich's own heartbeat script uses Python `paho-mqtt` instead, so the CLI wasn't already present on this host). See `operations.md` for the full schedule/behavior.
