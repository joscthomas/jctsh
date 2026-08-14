# photo-tv-display — Phone Controller View

`public/controller.html` + `public/controller.js`. Accessed directly at
`http://m8.local:3000/controller`, bookmarked by both Joseph and
Robin — no app install, no login. Both have full, equal access to every
action and setting (Phase 1 spec — no role restrictions).

## "Who's using this phone?"

The only identity concept in this component: on first load, `controller.js`
asks (a plain `prompt()`) which person is using this phone, and stores it in
`localStorage`. This is used **only** to attribute deletion-log rows
(`deleted_by`) — it is not auth, and nothing is gated behind it.

## WebSocket message protocol

Client → server:

| Message | Purpose |
|---|---|
| `{type:'nav', direction:'next'\|'prev'}` | Advance/rewind the slideshow |
| `{type:'setFilter', filter}` | Change what pool the slideshow draws from — see filter shapes below |
| `{type:'setSettings', settings}` | Partial merge into server settings (display duration, transition, metadata fields/behavior, delete confirm, idle timeout) |
| `{type:'favorite', value}` | Toggle favorite on the currently displayed asset |
| `{type:'delete', albumFolder, actingUser}` | Delete the currently displayed asset (moves to Immich trash) + writes the deletion log |
| `{type:'addToAlbum', albumId}` | Add current asset to an existing album |
| `{type:'createAlbum', albumName}` | Create a new album with the current asset |
| `{type:'startSlideshow'}` | Manual cast trigger (same HA call the idle auto-start uses) |
| `{type:'flashMetadata'}` | Ephemeral: briefly reveal the TV's metadata overlay ("on demand" behavior) |

Server → client: always `{type:'state', filter, settings, pool, index}` after
any handled message (last-write-wins — the most recent change simply
overwrites and broadcasts, no conflict resolution, per Phase 2 spec) or
`{type:'flashMetadata'}` (relayed, not part of persisted state).

## Filter shapes

`personId`/`albumId` are scoped to one Immich account each (separate
face-recognition/album records per account — see `routes/immich.js`'s file
header) — the controller UI makes the user pick "Joseph's library" or
"Robin's library" explicitly for those two modes before it can populate the
person/album picker.

| Mode | Filter object |
|---|---|
| `random` | `{mode:'random'}` |
| `owner` | `{mode:'owner', accounts:['joseph']\|['robin']\|['joseph','robin']}` |
| `favorites` | `{mode:'favorites'}` |
| `person` | `{mode:'person', ownerLabel, personId}` |
| `concept` | `{mode:'concept', query, accounts?}` |
| `location` | `{mode:'location', city?, state?, country?}` |
| `album` | `{mode:'album', ownerLabel, albumId}` |
| `dateRange` | `{mode:'dateRange', start, end}` (ISO timestamps) |
| `onThisDay` | `{mode:'onThisDay'}` (today's month/day, last 20 years) |

## UI notes

Kept deliberately plain (no build step, no framework) — a handful of
`<select>`/`<input>` elements and `prompt()`/`confirm()` for the album picker
and delete confirmation, matching Phase 1's "no app, browser bookmark only"
simplicity goal. Revisit only if real use on Robin's Pixel 7 shows this is
too clunky.
