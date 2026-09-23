# core/mqtt — Mosquitto Broker Configuration

Version-controlled copy of the Mosquitto MQTT broker config running on the Pi
(`pi1.local:1883`) — every JCTsh component publishes/subscribes through this broker.
The live config lives at `/etc/mosquitto/` on the Pi; files here are the source of
truth, deployed by hand-copying into `conf.d/`.

**Status:** Production — the broker every component in this repo depends on.

---

## Files

| File | Purpose |
|---|---|
| `mosquitto.conf` | Base config — persistence location, logging, `include_dir` for `conf.d/` |
| `jctsh.conf` | Adds ISO 8601 log timestamps, required for fail2ban's log parsing |
| `local.conf` | The plaintext LAN listener (port 1883) and auth settings — `listener 1883`, `allow_anonymous false`, `password_file /etc/mosquitto/passwd`. Existed live from the original install and was never tracked here; brought into the repo by CARD-0328's drift check, which found it Pi-only. No secrets in it (only the password file's path) |
| `mqtt-tls.conf` | TLS listener (CARD-0003) for internet-facing MQTT — only devices that leave the home network (hiking-monitor, air-quality-monitor) use this; stationary devices stay on the plaintext LAN-only listener from `jctsh.conf` |
| `mosquitto-cert-deploy-hook.sh` | Certbot deploy-hook for `jctsh.duckdns.org` — copies renewed certs into `/etc/mosquitto/certs` and reloads Mosquitto, installed at `/etc/letsencrypt/renewal-hooks/deploy/` |
| `monitoring.md` | How to check each layer of the DuckDNS → port forward → Mosquitto → fail2ban stack when debugging connectivity |

## Auth

`allow_anonymous false` with a per-component password file — every component gets its
own dedicated Mosquitto account (see root `CLAUDE.md`'s credentials table), never a
shared one. See `JCTsh-Build-Standards.md` §10.2 for the full security standard.

## Remote Access

The only accepted internet exposure is MQTT port 1883/8883, forwarded via DuckDNS
specifically so field ESP32 devices can reach the broker over cellular when away from
Tailscale-capable hardware — see `JCTsh-Build-Standards.md` §10.5 and `monitoring.md`
for the full path and how to check it's healthy.

## Deploy

Config changes are edited here, then hand-copied to `/etc/mosquitto/conf.d/` on the Pi
and applied with `sudo systemctl reload mosquitto` (or `restart` for changes that need a
full reload, e.g. `persistence_location`).

## Drift Check

Every file in this directory is checked daily against its live copy on the Pi by
`core/maintenance/config-drift-check.py` (CARD-0328) — it also flags any `*.conf` in
`/etc/mosquitto/conf.d/` that isn't tracked here (that's how `local.conf` was found).
Changes made live without coming back here open a kanban PR. To check by hand:
`ssh pi@pi1.local "sudo python3 /usr/local/bin/config-drift-check.py --dry-run"`. Adding a new
file here means adding it to that script's `MANIFEST` too.