# photo-tv-display — Testing

## Verified during build (2026-08-03), against the real M8/Immich/HA instances

Run manually on the M8 (`node server.js`, before the systemd service existed)
and exercised over real HTTP/WebSocket connections from this dev machine:

1. **Server boots clean** — `resolveOwners()` (GET `/users/me` for both
   accounts) and the initial `reloadPool({mode:'random'})` both succeeded with
   no errors before the HTTP server started listening.
2. **`/tv`, `/controller`, `/public/*`** — all return 200 with real HTML/JS.
3. **Image proxy** (`/photo/:ownerLabel/:id/thumbnail`) — returns a real JPEG
   (549KB, `image/jpeg`) for a real asset.
4. **`/api/asset/:ownerLabel/:id`** — returns full metadata including a
   correctly computed `locationLabel` (`"White Rock, New Mexico"` — confirmed
   the `country.startsWith('United States')` fix works against real
   `"United States of America"` data) and `albumNames`.
5. **`/api/albums`, `/api/people`** — both return real data for both accounts.
6. **WebSocket connect** — client receives the initial `state` message
   immediately on connection.
7. **`nav` round-trip** — index advances correctly and is reflected in the
   next broadcast.
8. **`setFilter` round-trip** — switching to `{mode:'favorites'}` reloaded the
   pool with a new (non-empty) result set.
9. **`favorite` round-trip, full stack** — toggled a real asset's favorite
   status to `true` and back to `false` through the actual WebSocket message
   path (not just the underlying Immich call in isolation), confirmed via the
   Immich API response, no errors.
10. **Multi-account merge + shuffle** — `{mode:'random'}` returned 200 unique
    assets (100 requested per account, no overlap in this sample, interleaved
    by `shuffle()` rather than left as two concatenated blocks).

## Not yet verified — requires Joseph, live, at the devices

Per the instructions doc's Step 11 checklist, these need a human at the TV and
both phones and cannot be done from here:

1. **HA `media_player.groom_tv` idle/playing/off state observation** — the
   actual state strings HA reports while something is casting, sitting idle,
   and powered off are still unconfirmed. `routes/homeassistant.js`'s
   `IDLE_STATES = ['idle', 'off', 'paused']` is a documented placeholder, not
   an observed fact — **correct this once real values are known**.
2. **Manual "Start Slideshow" actually casts to the real TV** — the HA
   `media_player.play_media` service call was confirmed to exist and accept
   the right fields via `/api/services`, but was deliberately **not** fired
   for real during this build (it would have started playing on the family
   TV unannounced). First real invocation should happen with Joseph aware.
3. **Both phones as simultaneous controllers** — last-write-wins behavior,
   no crashes/desync, on real WiFi.
4. **Delete + deletion log end-to-end** — needs Joseph to designate a real
   spare/test photo (the underlying Immich delete call was verified to exist
   and accept the right shape via the OpenAPI spec, but not fired for real —
   deletion, even to trash, isn't something to test on an arbitrary real
   family photo without asking).
5. **All 4 transitions and all metadata field/behavior combinations**,
   visually, on the actual TV screen.
6. **WiFi reconnection** — disconnect a phone's WiFi mid-session, confirm the
   manual `ws` reconnect (see `tv-view.md`) recovers cleanly; if not,
   Socket.IO is the documented fallback.
7. **Idle auto-start actually triggers** after the configured duration,
   against the real (once-known) idle state.
