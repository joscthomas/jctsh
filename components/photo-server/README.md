# photo-server

Self-hosted Immich photo/video library on a dedicated GMKtec M8 mini PC. Replaces Google Photos as the primary browsing/curation platform for the family library — Google Photos continues as an independent backup, unaffected by anything here.

| Status | Production |
|---|---|
| Host | GMKtec NucBox M8, hostname `photo-server` |
| LAN | `192.168.1.165` (DHCP-reserved), `photo-server.local` |
| Tailscale | `100.111.16.14` |
| Web UI | `http://photo-server.local:2283` or `http://192.168.1.165:2283` |
| OS | Ubuntu 26.04 LTS |

## What's Here

| Doc | Contents |
|---|---|
| `setup.md` | Actual build steps as executed, with deviations from the original instructions |
| `migration.md` | Google Takeout migration results — final counts, issues, and the CARD-0039 re-verification |
| `operations.md` | Day-to-day maintenance — scheduled reboots, Immich Tags feature, router coordination |
| `heartbeat.md` | MQTT heartbeat script — how JCTsh dashboard monitoring works for this host |
| `network.md` | Final IP/hostname/MAC/Tailscale reference for this host |
| `backup.md` | rsync backup script, cron schedule, capacity monitoring |
| `docker-compose.yml` | Copy of the authoritative compose file actually running |
| `.env.example` | Template `.env` — real `.env` lives only on the M8, never committed |

## Accounts

| Account | Role |
|---|---|
| Joseph (`joscthomas@gmail.com`) | Admin |
| Robin (`robinbt@gmail.com`) | Standard user |

Credentials and API keys are in `credentials.local.md` (repo root, gitignored) — never in this file.

## Dependencies

- Two USB HDDs: Seagate Backup Plus 1TB (`/mnt/photo-library`, primary) and Seagate Momentus 640GB (`/mnt/photo-library-backup`, local backup)
- Docker + Docker Compose (official Docker apt repo, not Ubuntu's)
- Tailscale (remote admin access)
- `photo-tv-display` (planned) runs on this same machine — hard dependency on this migration being complete, which it now is

## Related Cards

CARD-0018 (superseded — see original planning), CARD-0028 (optional quality scan, not started), CARD-0029/CARD-0032 (heartbeat monitoring, done), CARD-0030 (zip cleanup, pending — see `backup.md`), CARD-0037/CARD-0039 (ML processing + import completeness gaps, done).
