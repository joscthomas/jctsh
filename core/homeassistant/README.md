# core/homeassistant — Home Assistant Configuration

Version-controlled copy of the Home Assistant configuration running on the Pi, plus its
Matter Server backend. The live config lives at `/mnt/jctsh-logs/homeassistant/` on the
Pi (bind-mounted into the container); files here are the source of truth, deployed by
hand-copying up before a container restart.

**Status:** Production — the "brain" this repo's own `CLAUDE.md` Component Roles table
describes: multi-condition automation logic, sensor fusion, and anything that should be
version-controlled and observable on the log dashboard.

---

## Files

| File | Purpose |
|---|---|
| `docker-compose.yml` | The `homeassistant` container (network_mode: host, config bind-mounted from the SD-card-avoiding `/mnt/jctsh-logs/` USB path per `JCTsh-Build-Standards.md` §9.10) plus its `matter-server` sidecar |
| `configuration.yaml` | HA's own top-level config |
| `automations.yaml` | HA-native automations (JCTsh-custom automation components each get their own `components/<name>/` doc — see root `README.md`'s Document Types table for the split) |
| `container-update-check.py` | Deployed alongside `core/maintenance/container_update_check.py` — checks the `home-assistant/core` GitHub Releases API for available updates, opens a maintenance-finding PR (CARD-0126/CARD-0128) |
| `pi-heartbeat.py` | Publishes container health (currently just `homeassistant`, extend the `CONTAINERS` list for more) to the log dashboard, with a post-reboot grace period so a normal weekly reboot doesn't look like a crash-loop (CARD-0249) |

## Matter

`matter-server` (a `python-matter-server` sidecar in the same compose file) is HA's
Matter integration backend — required before HA's own Matter integration or the
Companion app's "Add Matter Device" flow has anything to hand a new device off to. Pinned
to `--primary-interface wlan0` since the Pi is dual-homed (`eth0` + `wlan0`) — see
`JCTsh-Build-Standards.md` §6.4 for the commissioning gotcha this was built to fix
(CARD-0262).

## Deploy

```bash
scp core/homeassistant/*.yaml pi@pi1.local:/mnt/jctsh-logs/homeassistant/
ssh pi@pi1.local "docker restart homeassistant"
```

A `docker-compose.yml` change needs `docker compose up -d` from the host's actual
compose project directory, not just a restart.
