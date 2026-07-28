# hike-izer-web

Publishes Hike-izer's generated HTML summaries (CARD-0081) at a real public
URL — `https://hikes.jctnet.com` — instead of a local file.
Tracking cards: **CARD-0088** (original hosting) and **CARD-0094** (switch
to this Cloudflare-fronted domain) on `kanban-board.md`.

---

## What runs where

Three containers, deployed on the M8 (`photo-server`), one compose project:

- **`web`** (`caddy:2-alpine`) — serves `~/hike-izer-web-app/srv/` (on the
  M8) as static files. Also published to `127.0.0.1:8090` on the host for
  local debugging — not reachable from the LAN or WAN via that port.
- **`orchestrator`** (`python:3.12-alpine`, `components/hike-izer-orchestrator/`,
  CARD-0086) — webhook receiver for automatic hike-end triggering, not
  published to the host at all. Reachable only via Caddy's `/webhook/*`
  route on this same domain (`web`'s `reverse_proxy`).
  See `components/hike-izer-orchestrator/README.md`.
- **`cloudflared`** (`cloudflare/cloudflared`, CARD-0094) — Cloudflare
  Tunnel client. No published ports at all; makes an outbound-only
  connection to Cloudflare's edge and routes `hikes.jctnet.com` to `web`
  over this compose project's default Docker network
  (`cloudflared-config.yml`'s `service: http://web:80`). Credentials
  (`cert.pem`, the tunnel's own credentials JSON) live in the gitignored
  `~/hike-izer-web-app/cloudflared/` on the M8 — generated via
  `cloudflared tunnel login` / `tunnel create`, never committed.

**Originally shipped on Tailscale Funnel** (CARD-0088, 2026-07-24) —
Cloudflare's free-tier onboarding didn't support adding a subdomain as its
own independent zone at the time (it insisted on the full `jctnet.com`
apex), which would have meant migrating the domain's nameservers to
Cloudflare while it still had live Zoho email running through it. Too risky
for what CARD-0088 needed, so it fell back to Tailscale Funnel instead.

**Switched to Cloudflare Tunnel 2026-07-27 (CARD-0094)**, once CARD-0093
cleaned up `jctnet.com`'s DNS and disabled its email — the nameserver
migration was no longer a real risk (nothing left on the domain to break).
`jctnet.com`'s nameservers now point at Cloudflare
(`damon.ns.cloudflare.com` / `sandra.ns.cloudflare.com`, set at GoDaddy),
and Cloudflare is authoritative for its DNS. Tailscale Funnel was turned
off as part of the same cutover — `hikes.jctnet.com` is now the only public
path.

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
2. Add `jctnet.com` as a zone in Cloudflare (Free plan) and point its
   registrar nameservers at the two Cloudflare assigns — see
   `credentials.local.md` for the values actually in use.
3. `mkdir -p ~/hike-izer-web-app/cloudflared && chmod 777 ~/hike-izer-web-app/cloudflared`
   (the `cloudflared` image runs as a non-root user; the mounted host dir
   needs to be writable by it) — then, from any machine with SSH access to
   the M8:
   ```
   docker run -d --name cloudflared-login -v ~/hike-izer-web-app/cloudflared:/home/nonroot/.cloudflared cloudflare/cloudflared:latest tunnel login
   docker logs cloudflared-login   # gives an authorization URL -- open it, log into Cloudflare, approve the jctnet.com zone
   docker rm -f cloudflared-login  # once "You have successfully logged in" appears in the logs
   docker run --rm -v ~/hike-izer-web-app/cloudflared:/home/nonroot/.cloudflared cloudflare/cloudflared:latest tunnel create hike-izer
   docker run --rm -v ~/hike-izer-web-app/cloudflared:/home/nonroot/.cloudflared cloudflare/cloudflared:latest tunnel route dns hike-izer hikes.jctnet.com
   ```
   The `tunnel create` output gives a tunnel ID — put it in
   `cloudflared-config.yml`'s `tunnel:`/`credentials-file:` fields.
4. `docker compose up -d` — brings up `web`, `orchestrator`, and `cloudflared`.

## Checking it's up

```
docker ps                                   # all 3 containers should show Up (healthy)
docker logs hike-izer-cloudflared --tail 20 # should show "Registered tunnel connection" x4, no errors
curl -s https://hikes.jctnet.com/           # should return the directory listing
```

Docker health for the containers rides the M8's existing 30-minute
heartbeat (`components/photo-server/photo-server-heartbeat.py`) — no
separate monitoring for this component. The tunnel's own connectivity
(distinct from the container just being "Up") isn't covered by that
heartbeat — a gap worth knowing about, not yet addressed.

## Not backed up, deliberately

`~/hike-izer-web-app/srv/` isn't covered by the M8's existing backup job
(`photo-library-backup.sh` is Immich-only). Everything here is regenerable
from the real sources of truth (the Google Sheets pipeline + Immich) —
same reasoning already accepted for Hike-izer's local photo cache
(CARD-0084).

## Related

- CARD-0088 (original hosting card — full architecture reasoning for the Tailscale Funnel-era design)
- CARD-0094 (Done — the switch to this Cloudflare Tunnel + custom domain setup)
- CARD-0093 (Done — the DNS cleanup that unblocked CARD-0094)
- CARD-0081 (HTML rendering, Done — produces the files this serves)
- CARD-0084 (photo integration — the `_photos/` directories this also serves)
- CARD-0086 (automatic triggering — future home for this pipeline's MQTT
  publish-visibility logging, not added here since the deploy step
  currently runs on Joseph's Windows machine, which has no MQTT capability)
- CARD-0092 (calendar home page — the eventual real index, replacing the
  interim Caddy directory listing)
