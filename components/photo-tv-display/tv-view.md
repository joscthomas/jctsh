# photo-tv-display — TV View

`public/tv.html` + `public/tv.js`. Fullscreen, no visible chrome — passive
display surface only, per Phase 1 spec.

## Image source

Displays the Immich `thumbnail?size=preview` variant (not `original`) via the
server's `/photo/:ownerLabel/:id/thumbnail` proxy — confirmed live to be a
real full-size JPEG (~500KB for a 1440×2560 source), plenty for a TV display
and much lighter than pulling `original` over WiFi for every photo.

`object-fit: contain` is used deliberately (not `cover`) — never crops a
curated family photo to fill the screen; black letterboxing is preferred over
losing part of the image.

## Transitions

Two stacked `<img>` layers (`layerA`/`layerB`) are double-buffered: the next
image preloads into the *inactive* layer before it's swapped in, so there's
never a flash of a half-loaded image.

| Style | Implementation |
|---|---|
| Crossfade | CSS `opacity` transition (1.2s) between the two layers |
| Ken Burns | CSS `@keyframes kenburns` (scale 1 → 1.08 + slight pan), `animation-duration` set inline to match the current display duration |
| Cut | `#stage.cut` class disables the layer's opacity transition — instant swap |
| Fade to black | Active layer fades to 0 first (revealing the black `#stage` background), *then* the new image loads into the same layer and fades back in — sequenced, not overlapping, which is what makes it visually distinct from crossfade |

## Metadata overlay

Built from `settings.metadataFields` (date / location / people / folder /
owner / description) — each independently toggleable, matching Phase 1.
`folder` shows Immich album membership (there's no separate filesystem-folder
concept in Immich to surface instead — see `routes/immich.js`'s
`getAlbums(ownerLabel, assetId)`).

Three display behaviors (`settings.metadataBehavior`):
- `always` — visible continuously
- `fadeInOut` — shown on each new photo, auto-hides after 4s
- `onDemand` — hidden unless a `flashMetadata` WebSocket message arrives
  (sent by the phone controller's "Show info now" button) — this is relayed
  server-side as an ephemeral broadcast, not part of the persisted `state`
  object, so it doesn't get echoed back on reconnect.

## Navigation / auto-advance

The TV view does **not** run its own independent auto-advance loop against
local state — it sets a local `setTimeout` for `settings.displayDurationSec`
that, when it fires, sends the exact same `{type:'nav', direction:'next'}`
message a phone controller's "Next" button sends. Both paths go through the
same server-side index update and broadcast, so the TV and every connected
phone always agree on what's currently showing.

## WebSocket reconnection

`ws` does not reconnect automatically (documented risk in Phase 2 planning).
`tv.js` implements a minimal manual retry (`onclose` → reconnect after 3s) —
not the Socket.IO fallback the planning doc names as the real fix if this
proves unreliable in practice. Revisit only if Step 11 live testing shows the
basic retry isn't good enough.
