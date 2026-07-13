# photo-server — Verify and Retire an External Photo Source

Procedure for checking whether a batch of photos/videos (an old USB drive, external HDD, phone backup, etc.) is already in Immich before deleting or wiping the source. Generalized from CARD-0066 (2026-07-13, a 941-photo legacy USB archive) — see that card in `kanban-board.md` for the original worked example. For the much larger original library import, see `migration.md`.

**Why this is safe:** Immich's dedup is checksum-based (see the "How does Immich identify a match" discussion — filename, path, and metadata play no role). Running `immich-go upload` against a source is self-correcting: files already present are recognized and skipped, files genuinely missing are uploaded. There's no need for a separate "check first, then decide" step — the upload run *is* the check, and nothing on the source is ever modified or deleted by `immich-go` itself.

## Prerequisites

- `immich-go` is already installed on the M8 (`/usr/local/bin/immich-go`) — no need to install it elsewhere; it just needs network access to the Immich server.
- Per-account API keys: `credentials.local.md` → "API keys (for immich-go migration)".
- Enough free space on the M8 for a staging copy (`df -h /home` — normally hundreds of GB free, trivial for anything short of another full library).

## Procedure

1. **Inventory the source first.** Count files, and note the actual extensions present — check **case-insensitively** (`find <path> -iname "*.jpg" | wc -l` etc.). Also check for filename collisions within the batch (`find ... -printf "%f\n" | sort | uniq -d`) so you know whether same-named files exist before copying (they'll just overwrite in a flat staging folder).

2. **Copy to a staging directory on the M8** (e.g. `/home/jct/verify-batch-<date>/`), not anywhere on the source machine and not directly into an Immich-watched folder.

   ⚠️ **Gotcha (found in CARD-0066):** shell globs like `*.jpg` are case-sensitive by default. A drive with mixed `.jpg`/`.JPG` extensions will silently lose files to a case-sensitive copy command, with no error. Either glob per-case explicitly and combine (`*.jpg` and `*.JPG` separately) or enable case-insensitive globbing first (`shopt -s nocaseglob` in bash) before copying.

3. **Verify the copy is complete before telling anyone it's safe to delete the source.**

   ⚠️ **Gotcha (found in CARD-0066):** `du -cb <glob> | tail -1` is not reliable for a total-size comparison — if the command batches internally, `tail -1` can silently show only the last batch's subtotal, not the true grand total. It also inherits the same case-sensitivity trap as the copy step if the glob is re-typed instead of reused. Use a per-file byte sum instead, with the same case-insensitive file selection on both sides:
   ```
   find <path> -iname "*.jpg" -printf "%s\n" | awk '{s+=$1} END{print s}'
   ```
   Compare file *count* and *total bytes* independently on both sides — a count match alone isn't sufficient (e.g. if some files were truncated in transfer), and a byte-total match alone isn't sufficient either (a coincidental match on a small file count is unlikely but not impossible).

4. **Once verified, it's safe to tell the source owner to delete/wipe the original** — this doesn't need to wait for the `immich-go` run below to finish. Copy verification and Immich verification are independent checkpoints.

5. **Run `immich-go`** against the staged copy:
   ```
   immich-go upload from-folder <staging-path> \
     --api-key <account's key> \
     --server http://localhost:2283 \
     --on-errors continue \
     --session-tag \
     --log-file <staging-path>/immich-go-verify.log
   ```
   - `--on-errors continue` — don't abort the whole run over a handful of bad files (default behavior stops the entire job).
   - `--session-tag` — tags every genuinely-*uploaded* asset with a timestamped `{immich-go}/YYYY-MM-DD HH-MM-SS` tag, so you can browse exactly what's new afterward in the Immich web UI. Preferred over `--into-album` — that flag's help text doesn't clearly say whether skipped duplicates also land in the album, while `--session-tag` explicitly only tags uploads.
   - `--log-file` — always capture one. The console summary alone isn't enough to close out a verification card (see Don't-close-until convention below).
   - Run detached if the batch is large enough to take a while (`nohup ... & disown`, then confirm with `ps aux | grep immich-go` on the remote host — don't trust a local background-task wrapper's own exit status for *remote* detached work; see `migration.md`'s "killed background processes didn't actually die" lesson).
   - **Leave the staged copy and log on the M8 afterward.** Don't add a cleanup step unless specifically asked — the copy is cheap insurance and the log is the audit trail.

6. **Review the results — the actual log, not just the console summary.**
   - Reconcile: `uploaded + server-duplicates + local-duplicates` should equal the total file count. If it doesn't, something was miscounted or the run didn't finish cleanly.
   - `grep -iE "error|warn|fail"` the log directly rather than trusting a zero-error count in the summary.
   - Matching is exact-checksum only — a re-compressed/re-processed copy of a photo that's *visually* the same but not byte-identical (e.g. one exported through Google Photos vs. the original camera file) will **not** match and will upload as a "new" asset despite being a duplicate in spirit. Not a bug, just the limitation of checksum matching — worth a manual glance through the tagged new uploads if you suspect this applies to a given batch.
   - If the source has old/unusual EXIF, check for date-fallback warnings in the log — `immich-go`'s `--date-from-name` fallback only helps if the filename itself encodes a date; camera-original filenames (`CIMG0002.jpg`, `IMG_1234.jpg`) generally don't, so a file missing EXIF entirely may land in Immich with an inaccurate date.

## Reference: CARD-0066 worked example

941 `.jpg` files from a USB drive, verified against Joseph's library:

| Outcome | Count |
|---|---|
| Uploaded (new) | 902 |
| Server duplicates | 37 |
| Local duplicates (same photo, two filenames within the batch) | 2 |
| **Total** | **941** |

Zero errors, ~1 minute runtime. Full detail (including the copy gotchas as they were actually discovered) in `kanban-board.md` CARD-0066.
