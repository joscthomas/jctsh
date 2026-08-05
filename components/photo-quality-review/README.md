# photo-quality-review

CARD-0028: finds duplicate, blurry, and broken images across both Joseph's
and Robin's Immich libraries, and provides a small review UI to mark
keep/delete decisions and submit confirmed deletions to Immich -- plus a
standing manual-groom list for cleaning up the separate Google Photos
backup with the same findings.

## Architecture

```
czkawka (image, broken) ────┐
sharp (blur, hand-rolled)  ─┼── scan.js (batch, run manually/periodically)
Immich REST API (path idx)─┘         │
                                       ▼
                                 data/report.json
                                       │
                                       ▼
                        Node.js server (M8, port 3001) ── review.html/js
                                       │
                                       ▼
                        Immich delete API + deletion-log
                        (same CSV/Sheet photo-tv-display writes to)
```

- **`scan.js`** — the batch job. Three passes over `/mnt/photo-library/upload/`
  (both accounts' files in one tree, since czkawka doesn't know or care about
  the per-account split): czkawka `image` (near-duplicates, has its own
  built-in cache -- confirmed live, re-scans are naturally incremental),
  czkawka `broken -c IMAGE` (corrupted files), and a hand-rolled
  Laplacian-variance blur pass via `sharp` (czkawka has **no** blur detector
  -- checked its real `--help` output directly; only `image` and `broken`
  exist). The blur pass keeps its own mtime-keyed cache
  (`data/blur-cache.json`) since `sharp` has no built-in one. Every flagged
  file is resolved to its Immich asset ID before being written to
  `data/report.json`, via a full path index built from `/search/metadata`
  (paginated) for both accounts -- `originalPath` (`/data/upload/...` inside
  the Immich container) maps to the host path (`/mnt/photo-library/upload/...`)
  by simple prefix substitution, confirmed directly from
  `~/immich-app/.env`'s `UPLOAD_LOCATION=/mnt/photo-library` and its
  `docker-compose.yml`'s `${UPLOAD_LOCATION}:/data` mount -- not assumed from
  directory-structure similarity alone.

- **`server.js`** — serves the review UI (`/review`) and its API: `/api/report`
  (report + persisted decisions, grouped by year), `/api/decide/duplicate`
  and `/api/decide/single` (instant-save, no explicit "save" step),
  `/api/preview` (dry-run: exact list of what's currently marked, without
  deleting anything), `/api/confirm` (actually deletes via Immich's API --
  `force: false`, so items land in Immich's own recoverable trash, same
  safety net `photo-tv-display`'s `deleteAsset()` already established -- then
  logs each one and clears it from the pending-decisions state).

- **`routes/immich.js`** — API helper (path index, delete, thumbnail proxy),
  same account-merge pattern as `photo-tv-display/routes/immich.js`.

- **`routes/deletion-log.js`** — writes to the **same** CSV
  (`/mnt/photo-library/deletion-log.csv`) and Google Sheet Apps Script
  `photo-tv-display` already uses (same env var names/values) -- this is
  what makes CARD-0028's "standing Google Photos manual-groom list" one
  converged record rather than a second, separate list. `album_folder` is
  repurposed as a short reason string (`"duplicate, kept <filename>"` /
  `"blurry (variance N)"` / `"broken (...)"`) -- confirmed safe by reading
  the deployed Apps Script (`components/photo-tv-display/apps-script.gs`):
  it's a plain pass-through column, no schema validation on content.

## Review UI, screen by screen

1. **Year picker** (landing page) -- browsing aid only, **not** a commit
   boundary (Joseph's correction, CARD-0028 interview): Preview/Confirm act
   on whatever is currently marked across however much has been reviewed in
   a session, regardless of year boundaries.
2. **Duplicates** -- one row per group, radio button marks which to *keep*
   (the rest become delete candidates), or "Skip for now."
3. **Blurry & Broken** -- a grid, one toggle per item (unset -> delete ->
   keep -> delete -> ...).
4. Every thumbnail's "View original" link deep-links to that asset's own
   page in Immich's existing web UI (`/view/:assetId` -> redirects to
   `IMMICH_SERVER_URL/photos/:assetId`) rather than building a custom viewer.
5. Every click saves immediately in the background.
6. A running tally at the bottom, with **Preview Deletions** (exact list,
   last sanity check) and **Confirm & Delete** (calls Immich's delete API +
   deletion-log for everything currently marked).

## Environment (`.env`, gitignored)

Reuses several values already deployed for `photo-tv-display` verbatim (see
that component's `.env` on the M8) so both tools converge on the same
deletion log:

| Var | Value |
|---|---|
| `IMMICH_SERVER_URL` | Same as `photo-tv-display` (`http://localhost:2283`) |
| `IMMICH_API_KEY_JOSEPH` / `_ROBIN` | Same as `photo-tv-display` |
| `DELETION_LOG_LOCAL_PATH` | Same as `photo-tv-display` (`/mnt/photo-library/deletion-log.csv`) |
| `DELETION_LOG_SHEET_APPS_SCRIPT_URL` / `_KEY` | Same as `photo-tv-display` |
| `PHOTO_LIBRARY_UPLOAD_ROOT` | `/mnt/photo-library/upload` |
| `CZKAWKA_CLI_PATH` | `/home/jct/photo-quality-review/bin/czkawka_cli` |
| `PHOTO_QUALITY_REVIEW_DATA_DIR` | `/home/jct/photo-quality-review/data` |
| `PORT` | `3001` (distinct from `photo-tv-display`'s `3000`) |
| `TZ` | `America/Phoenix` |

## czkawka

Installed as a plain binary (no system package manager, no sudo) from
[czkawka's GitHub releases](https://github.com/qarmin/czkawka/releases) --
`linux_czkawka_cli_x86_64`, **not** the `heif_raw_avif` variant, which needs
`libheif.so.1` installed system-wide (a `sudo apt install` step blocked from
non-interactive automation on this project -- see CARD-0053's precedent).
**Known gap:** HEIC/RAW/AVIF files aren't scanned by the `image`/`broken`
passes as a result. Revisit if that turns out to matter (would need Joseph
to run the one-line `apt install` himself, then swap in the `heif_raw_avif`
binary).

## Running a scan

```bash
cd ~/photo-quality-review && node scan.js
```

Not on a timer yet (CARD-0028's own scope: prove the pipeline works, not
build a fully automatic recurring job) -- run manually before a review
session. Safe to interrupt/re-run: czkawka's own cache and the blur pass's
`blur-cache.json` both make re-scans skip unchanged files.

## Deploy

```bash
scp package.json server.js scan.js .env jct@<M8 Tailscale IP>:~/photo-quality-review/
scp routes/*.js jct@<M8 Tailscale IP>:~/photo-quality-review/routes/
scp public/* jct@<M8 Tailscale IP>:~/photo-quality-review/public/
ssh jct@<M8 Tailscale IP> "cd ~/photo-quality-review && npm install"
```

No systemd service yet -- CARD-0028's "done" bar is proving the pipeline
end-to-end with a real review session, not a set up recurring/on-boot
service. Run with `node server.js` (foreground) or `nohup node server.js &`
for now; a systemd unit (same shape as `photo-tv-display`'s) is a natural
follow-up once this has seen real use, and needs Joseph's own interactive
`sudo` step to install regardless.

## Related

- CARD-0028 on `kanban-board.md` -- full interview history, scope decisions,
  and "done when" criteria.
- `components/photo-tv-display` -- the Node/Express stack, Immich
  multi-account pattern, and deletion-log this reuses/extends.
- `components/photo-server/backup.md` -- the
  `/mnt/photo-library/upload/<ownerId>/` structure this scans.
