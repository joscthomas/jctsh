# photo-tv-display

Ambient photo slideshow for the gathering room Google TV, plus a phone-browser
controller for Joseph and Robin (no app install — bookmark only). Backed by a
Node.js server running on the `photo-server` M8, which is the sole caller of
both the Immich API (photo library) and the Home Assistant REST API (casting).

## URLs (home WiFi only)

| View | URL |
|---|---|
| TV (cast target, no visible UI) | `http://photo-server.local:3000/tv` |
| Phone controller | `http://photo-server.local:3000/controller` |

## Dependencies

- **`photo-server`** — Immich must be running and reachable at `http://localhost:2283` from the M8 (this component runs on the same host, so it talks to Immich over localhost, not the LAN).
- **Home Assistant** — `media_player.groom_tv` (the gathering room Google TV's Cast integration entity) and a long-lived access token. This build reuses the existing shared `HA_TOKEN` already used by Node-RED/Claude Code rather than minting a dedicated one.
- **Google Apps Script** — a dedicated Sheet + `doPost` deployment for the deletion log (separate from the JCTsh environmental data pipeline's sheet). See `setup.md`.

## Architecture

```
Immich REST API ──────────┐
Home Assistant REST API ──┤── Node.js server (M8, port 3000) ── WebSocket ── TV view / phone controller(s)
```

Two Immich accounts (Joseph's, Robin's) are queried with their own API keys and
merged server-side, tagged with the real owner (resolved once at startup via
`GET /users/me`, not "whichever key happened to fetch it" — see `routes/immich.js`
for why that distinction matters for shared albums). Every per-asset write
(favorite/delete/album) uses that asset's actual owning account's key.

## Known deviations from the original planning docs

Found while building against the real, current Immich API (v3.1.0) rather than
the API shape assumed at planning time — see `components/photo-tv-display/photo-tv-display-claude-code-instructions.md`
and Phase 1/2 docs for the original plan, and `routes/immich.js`'s file header
for the full technical explanation:

- Immich's asset-filter DTOs have no `ownerId` field — confirms (doesn't just
  suggest) that the multi-account merge design is required, not optional.
- `isArchived` was replaced by a `visibility` enum; "exclude archived by
  default" is now `visibility: 'timeline'`.
- Location `country` comes back as `"United States of America"`, not
  `"United States"`/`"USA"` as the planning doc assumed — `formatLocation()`
  matches with `startsWith('United States')`.
- Used the built-in Node.js 18+ global `fetch` instead of the planned
  `node-fetch` dependency — Node v24.18 is already installed on the M8 and
  `node-fetch` v3 is ESM-only, which would have forced `"type": "module"`
  friction for no real benefit.
- Delete uses Immich's own trash (`force: false`) rather than an immediate
  permanent delete — a free extra safety net on top of the planning doc's
  "removes it from our home library" framing, not a deviation from it.

## Status

Code built and verified against the real M8/Immich/HA instances (Immich API
calls, WebSocket state sync, image proxy, favorite toggle all exercised live
and round-tripped safely). **Live as of 2026-08-03**: systemd service
installed and running (enabled, survives reboot) and the deletion-log Apps
Script is deployed and confirmed reachable. **Still outstanding**: live device
testing (actual TV casting, both phones, HA idle-state observation) requires
Joseph physically at the devices — see `testing.md`.
