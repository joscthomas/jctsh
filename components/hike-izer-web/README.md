# hike-izer-web

Publishes Hike-izer's generated HTML summaries (CARD-0081) at a real public
URL — `https://photo-server.tailfe828a.ts.net` — instead of a local file.
Tracking card: **CARD-0088** on `kanban-board.md`.

---

## What runs where

Two containers, deployed on the M8 (`photo-server`), one compose project:

- **`web`** (`caddy:2-alpine`) — serves `~/hike-izer-web-app/srv/` (on the
  M8) as static files. Publishes only to `127.0.0.1:8090` on the host — not
  reachable from the LAN or WAN directly, only via loopback.
- **`orchestrator`** (`python:3.12-alpine`, `components/hike-izer-orchestrator/`,
  CARD-0086) — webhook receiver for automatic hike-end triggering, not
  published to the host at all. Reachable only via Caddy's `/webhook/*`
  route on this same URL (`web`'s `reverse_proxy`) — no second Funnel port.
  See `components/hike-izer-orchestrator/README.md`.

**Tailscale Funnel** (`tailscale funnel --bg 8090`, run on the M8 host, not
in a container) exposes that loopback port publicly at
`https://photo-server.tailfe828a.ts.net`, with TLS terminated by Tailscale.
`jct` is set as the Tailscale operator (`sudo tailscale set --operator=jct`,
one-time) so Funnel commands don't need `sudo`.

**Originally planned as Cloudflare Tunnel + a `hikes.jctnet.com` custom
domain instead** — pivoted 2026-07-24 after discovering Cloudflare's
free-tier onboarding doesn't support adding a subdomain as its own
independent zone (it insists on the full `jctnet.com` apex), which would
have meant migrating the domain's nameservers to Cloudflare while it still
had live Zoho email running through it. Too risky for what this card needed.
See CARD-0088 for the full story and **CARD-0094** for the (optional, not
committed) path back to Cloudflare once CARD-0093 (DNS cleanup, disabling
email on `jctnet.com`) removes that risk.

## Deploying content

`.claude/skills/hike-izer/SKILL.md`'s generation flow `scp`s each summary
(and its `_photos/` directory, if present) to
`jct@photo-server.local:~/hike-izer-web-app/srv/` as its last step —
publishing isn't a separate manual action. To copy something by hand:

```
scp -r <local file/dir> jct@photo-server.local:~/hike-izer-web-app/srv/
```

## Setup (one-time)

1. `mkdir -p ~/hike-izer-web-app/srv` on the M8 — kept alongside the compose
   file rather than under `/srv/`, matching how `netalertx-app/data` and
   `immich-app` already do it (`/srv` is root-owned; `jct` has no
   passwordless sudo, and there's no real reason to fight that when the
   home-directory convention already exists and lives on the same boot disk
   anyway).
2. `docker compose up -d`.
3. One-time, on the M8 host (not in a container): `sudo tailscale set --operator=jct`.
4. Enable Funnel for the tailnet, once, via the URL `tailscale funnel` prints
   the first time it's run if not yet enabled (Tailscale admin console).
5. `tailscale funnel --bg 8090` — exposes the container's published port
   publicly. Persists across reboots (stored in tailscaled's own state, not
   a foreground process).

## Checking it's up

```
docker ps                                              # container should show Up (healthy)
tailscale funnel status                                # confirm Funnel config is active
curl -s https://photo-server.tailfe828a.ts.net/         # should return the directory listing
```

Docker health for the container rides the M8's existing 30-minute heartbeat
(`components/photo-server/photo-server-heartbeat.py`) — no separate
monitoring for this component. Funnel/Tailscale connectivity itself isn't
covered by that heartbeat (it checks Docker container health, not the
tailnet) — a gap worth knowing about, not yet addressed.

## Not backed up, deliberately

`~/hike-izer-web-app/srv/` isn't covered by the M8's existing backup job
(`photo-library-backup.sh` is Immich-only). Everything here is regenerable
from the real sources of truth (the Google Sheets pipeline + Immich) —
same reasoning already accepted for Hike-izer's local photo cache
(CARD-0084).

## Related

- CARD-0088 (this component's tracking card — full architecture reasoning)
- CARD-0094 (the deferred switch to Cloudflare Tunnel + a custom domain)
- CARD-0093 (the DNS cleanup that would unblock CARD-0094)
- CARD-0081 (HTML rendering, Done — produces the files this serves)
- CARD-0084 (photo integration — the `_photos/` directories this also serves)
- CARD-0086 (automatic triggering — future home for this pipeline's MQTT
  publish-visibility logging, not added here since the deploy step
  currently runs on Joseph's Windows machine, which has no MQTT capability)
- CARD-0092 (calendar home page — the eventual real index, replacing the
  interim Caddy directory listing)
