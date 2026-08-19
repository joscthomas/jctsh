# photo-server — Operations Guide

Immich-specific day-to-day maintenance. For build steps see `photo-server-claude-code-instructions.md`; for monitoring see `heartbeat.md`. For anything about the underlying M8 machine itself (scheduled reboot, router-reboot coordination, OS/firmware maintenance), see `hosts/m8/operations.md` — **split out from this file 2026-08-19** (`kanban-board.md` CARD-0096's addendum).

## Immich Update Check (added 2026-07-10)

| Property | Value |
|---|---|
| Managed by | systemd timer (`immich-update-check.timer` → `immich-update-check.service`) |
| Schedule | Daily, 6:00 AM (`America/Phoenix`) |
| Action | Compare `/api/server/version` against `/api/server/version-check`; publish an MQTT notice if a newer release is available |

Version-controlled files: `components/photo-server/immich-update-check.py` (deployed to
`/usr/local/bin/`), `core/maintenance/immich-update-check.service`,
`core/maintenance/immich-update-check.timer`.

**Deliberately notify-only, not auto-update.** Immich is actively developed and this
instance has already surfaced real bugs in a single patch version (the CARD-0037/0042/0043
gaps, the HEIC distortion issue) — auto-applying updates unattended on a library holding
irreplaceable family photos isn't worth the risk. The actual update (`docker compose pull
&& docker compose up -d` in `~/immich-app`) stays a deliberate, manual step.

**De-duplicated by design** — a state file (`/home/jct/.jctsh/immich-update-check.state`,
not `/etc/jctsh/` since that directory isn't writable by the `jct` user and caused the
first deploy attempt to crash) stores the last-notified version, so the same pending
update doesn't re-fire every day. It only notifies again if an even newer version becomes
available after the first notice.

Message published as component `photo-server`, category `System`, e.g. `"Immich update
available: v3.0.2 (currently running v3.0.1)"`. Verified live 2026-07-10: first run
notified correctly, second run correctly skipped re-notifying for the same version.

## Immich Tags Feature (People Tags from Google Photos)

The Tags feature is **disabled by default** in Immich — nothing shows in the sidebar, the
asset info panel has no Tags section, and `tag` doesn't appear as a search filter option
until it's turned on. Enable via: profile avatar menu → **Account Settings** → **Features**
section → enable **Tags**.

Once enabled, two top-level tags exist: `People` (332 children, one per name Google Photos
had already identified/tagged in the original account, carried over via `immich-go`'s
`--people-tag` flag reading each photo's Takeout JSON `people` field) and
`takeout-20260703T160953Z-3` (the import-batch tag `immich-go` applies automatically,
single label, no children).

**Important: these tags are a separate system from Immich's own ML face-recognition Person
clusters** (`faceDetection`/`facialRecognition`, see CARD-0037 in `kanban-board.md`). Tagging
`People/<name>` here does not automatically name or link to the corresponding ML cluster —
they don't talk to each other. Tags are static labels carried over from Google's own
historical face-tagging (instant, already complete, searchable by tag once the feature is
on); ML clusters are Immich's own ongoing face-detection/recognition pipeline (needs manual
naming per cluster, catches people Google never had tagged). Use both — tags for what's
already labeled, cluster-naming for the rest.

Also note: Immich's main search bar does **CLIP semantic search** on free text, not a
literal tag/name lookup — typing a person's name there returns whatever the model judges
loosely similar, which is close to random for a name it has no way to recognize. To find
photos by tag, browse the Tags view directly (once enabled) rather than typing the name
into search.

## Standard Photo Import (external source, not Google Takeout)

For any batch of photos found outside the Google Photos/Immich ecosystem (an old drive, a
folder rescued from a dead computer, etc.) that need checking against and adding to Immich —
the "standard job": `immich-go`'s generic folder-upload mode does the same dedup-and-load
work the original Takeout migration used, minus the Takeout-specific JSON sidecar handling.

1. Get the source folder onto `photo-server` if it isn't already (`scp -r <source>
   jct@photo-server.local:~/import-staging/<batch-name>`).
2. Run, from the M8:
   ```bash
   immich-go upload from-folder ~/import-staging/<batch-name> \
     -s http://localhost:2283 \
     -k <account's API key — see credentials.local.md> \
     --on-errors continue \
     --pause-immich-jobs=false \
     --session-tag
   ```
3. `--session-tag` applies an automatic `{immich-go}/YYYY-MM-DD HH-MM-SS` tag to everything
   uploaded in that run — same tagging behavior as the original migration's per-batch tags
   (see "Immich Tags Feature" above), gives an easy way to find/review exactly what a given
   import added. Immich's own checksum-based dedup skips anything already present — no
   separate pre-check needed, matches the "self-correcting" reasoning already established in
   `migration.md`.
4. Confirm which account (Joseph's or Robin's) the batch belongs to before running — API key
   selects the destination account, there's no folder-level choice.
5. Report back the final asset count `immich-go` uploaded vs. skipped (dedup) so it's clear
   what actually landed.
