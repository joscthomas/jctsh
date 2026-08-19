# M8 — Host Docs

GMKtec NucBox M8, general-purpose Docker application host. LAN `192.168.1.165`, Tailscale `100.111.16.14`. See `network.md` for the full reference.

This directory holds docs about the **physical machine itself** — base setup, network identity, host-wide scheduled jobs, cross-component maintenance checks. It does not describe any individual application running on it; each of those has its own `components/<name>/` directory:

| Component | Directory |
|---|---|
| Immich photo library | `components/photo-server/` |
| NetAlertX | `components/netalertx/` |
| hike-izer web + orchestrator | `components/hike-izer-web/`, `components/hike-izer-orchestrator/` |
| ring-mqtt | no dedicated directory yet — see CARD-0146 |
| photo-tv-display | `components/photo-tv-display/` |
| photo-quality-review | `components/photo-quality-review/` |

**Split from `components/m8/` (which was itself `components/photo-server/` before CARD-0096), 2026-08-19** — see `kanban-board.md` CARD-0096's addendum for the full reasoning. The directory previously mixed host-level docs with Immich-specific ones under a name that matched neither cleanly.

## Files

| File | Purpose |
|---|---|
| `network.md` | Hostname, LAN/Tailscale IPs, MAC, the dual-ethernet-port gotcha |
| `setup.md` | Base OS install facts |
| `operations.md` | Scheduled reboot, router-reboot coordination |
| `maintenance-check.py` | CARD-0095 — OS/firmware update checks, whole machine |
| `container-update-check.py` | CARD-0126 — image-update checks for containers without their own version API (NetAlertX, Caddy/hike-izer-web, cloudflared) |
