# photo-server — Google Takeout Migration Results

**Migration window:** 2026-07-03 through 2026-07-06
**Tool:** immich-go v0.32.0, run directly against the Takeout zip files (no extraction needed — immich-go reads zips natively)

## Final Counts

| Account | Discovered (raw Takeout) | Uploaded (unique) | Local duplicates discarded | Server duplicates (already uploaded) |
|---|---|---|---|---|
| Joseph | 129,520 (126,690 images + 2,830 videos) | 80,392 (78,849 images + 1,543 videos) | 42,163 | 79,745 |
| Robin | 96,822 (94,435 images + 2,387 videos) | 73,696 (71,877 images + 1,819 videos) | 17,647 | 233 |
| **Combined** | **226,342** | **154,088** | — | — |

Joseph's "server duplicates" count is inflated by the migration itself needing 5 restarts (see Issues below) — each restart re-scanned all 12 zips from scratch and correctly re-recognized everything uploaded in prior runs as already-present. Robin's migration completed in a single clean run, so her much lower server-duplicate count (233) is the more representative number for how much overlap a from-scratch import naturally has.

**Verification:** Joseph's Google Photos app reports 75,865 photos on-device, close to Immich's 78,849 images (~4% difference, expected from edited-copy variants and burst-photo stack counting differences — see below).

## Why the duplicate counts are so high

Google Takeout exports **every album a photo has ever been added to as a separate physical copy**, in addition to its one chronological "Photos from `<year>`" copy. A photo added to 5 albums over the years exports as 6 identical files. Confirmed directly: `Brian Kidd.jpg` appears 20+ times across the export, once in its date folder and once per album (`Brian Kidd(2)`, `1984 Christmas`, `Joseph, Robin & 9 others`, `LJ Thomas Family`, etc.) — all the same photo. `immich-go`'s duplicate detection correctly collapsed these down to one asset each. This is normal Google Takeout behavior, not an import error, and scales with how much a family has historically organized photos into albums.

## Process Used

1. Downloaded Google Takeout export (ZIP, 50GB chunks) to the Windows machine, transferred to `photo-server` via SCP as each part finished downloading (freed local disk space immediately after each verified transfer — Windows machine only had ~13GB free at the start of this).
2. Ran `immich-go upload from-google-photos` directly against the zip files (`takeout-*.zip` glob) — no extraction step needed, avoiding a ~2x disk space requirement extraction would have caused.
3. Decided to skip a manual pre-import quality pass (blurry/duplicate/screenshot review) — relied on Immich's built-in duplicate detection (CLIP-embedding based) and an ongoing "mark favorites" habit instead. See `kanban-board.md` CARD-0028 for optional automated post-import quality scanning tools if wanted later.
4. Generated a per-account API key by logging in as that user and calling `POST /api/api-keys` (admin cannot create a key on another user's behalf — must authenticate as that user).

## Issues Encountered

**Disk space crisis (Joseph's import, run 3):** `/mnt/photo-library` (916GB) filled to 100% and every upload started failing. Root cause: the raw Takeout zips (595GB Joseph + 222GB Robin = 817GB) and Immich's own copy of every uploaded asset were both competing for the same drive — a transient peak requirement that exceeds the drive's capacity, even though the final steady-state library (~650-700GB) fits comfortably once the zips are removed. Fixed by relocating the zips: 9 of Joseph's 12 files to `/mnt/photo-library-backup` (Momentus 640GB), the rest to the NVMe (`/home/jct/takeout-staging/`). See `kanban-board.md` CARD-0030 for cleanup once zips are no longer needed (Momentus can't hold both the zips and a real backup simultaneously).

**`immich-go` default `--on-errors stop`:** the tool's default behavior aborts the *entire* run after enough individual asset errors (a handful of oversized video uploads hitting connection resets). Fixed by adding `--on-errors continue` — lets it log the error and keep going rather than stopping the whole multi-hour job over a few bad files.

**Non-admin accounts can't pause Immich background jobs:** Robin's API key (standard user, not admin) doesn't have permission for `--pause-immich-jobs` (default true, admin-only). Fixed with `--pause-immich-jobs=false` — harmless, just means thumbnail/ML jobs ran concurrently with the upload instead of being paused.

**Killed background processes didn't actually die:** `nohup`'d remote processes (both a takeout-zip-transfer watcher and the zip-relocation `mv` jobs) kept running after the local monitoring tool was stopped, because stopping the *local* poller doesn't send a signal to the *detached remote* process. Caused two duplicate `mv` operations to race on the same files during the zip relocation — resolved by explicitly `kill -9`-ing the stale PIDs on the M8 directly (confirmed via `ps aux`) rather than assuming a local `TaskStop` had any effect on remote work.

**Multiple restarts needed for Joseph's import (not Robin's):** Joseph's import required 5 restarts total — 1 disk-space crash, 2 crashes from the `--on-errors stop` default (before the fix), and 2 clean completions of partial batches. Each restart re-scans all zips from scratch (no persistent resume checkpoint), costing ~30-40 minutes of re-indexing each time. Robin's import, run after both fixes were in place, completed in one clean pass.

## Post-Migration TODO

- ~~Spot-check the import before deleting the Takeout zips~~ — done properly (CARD-0039, 2026-07-09): full re-run of `immich-go` against all retained zips found **3,433 assets that had been genuinely missing** (58 Joseph/backup, 119 Joseph/NVMe, 3,256 Robin) and uploaded them; zero errors otherwise. See CARD-0039 resolution in `kanban-board.md` for full detail. Zips are still retained — see CARD-0030 for deletion timing.
- Once satisfied with the now-more-complete import: delete zips, re-enable weekly backup cron (CARD-0030)
- Optional: automated post-import quality scan for blur/near-duplicates (CARD-0028)
- Face naming (manual, in Immich web UI) — Step 13 of the original build plan
- Deletion-logging setup — Step 14
- `photo-tv-display` build — hard dependency on this migration being complete, which it now is

## Import Completeness Re-Verification (2026-07-09, CARD-0039)

Prompted by CARD-0037 (a large gap found in ML processing from this same import) — if background jobs were being dropped, it was worth checking whether raw asset uploads were too. Re-ran `immich-go upload from-google-photos` for real (not `--dry-run`) against every retained zip, using the same `--on-errors continue --pause-immich-jobs=false` flags plus `--no-ui --log-file=...` for a persisted log this time (the original run's console output wasn't captured anywhere). Immich's checksum-based dedup means a real run is self-correcting: matches get skipped, genuine gaps get uploaded — no separate dry-run-then-real-run cycle needed.

**Result:** single clean pass, no restarts, zero upload errors.

| Pass | Uploaded (missing) | Server upgraded | Already correct |
|---|---|---|---|
| Joseph — backup-drive zips | 58 | 17 | 69,571 |
| Joseph — NVMe-staged zips | 119 | 29 | 16,036 |
| Robin | 3,256 | 63 | 75,094 |
| **Total** | **3,433** | **109** | **160,701** |

**Robin's gap was the largest**, despite her original import being the "clean" one with no crashes/restarts — meaning the missing-asset problem wasn't caused solely by Joseph's chaotic 5-restart import as originally assumed. Combined with CARD-0037 (Robin's ML-processing gap was also worse than Joseph's — 96% vs ~80% zero-face), there's a consistent pattern across both accounts that points to something shared (likely M8-side infrastructure/timing under the load of both multi-day imports running close together) rather than either import's individual restart history. Not investigated further — the fix (re-run to catch anything missing) resolves it regardless of root cause.

Logs retained on the M8: `/home/jct/immich-go-verify-20260709/{joseph-backup,joseph-home,robin}.log` and `run.out`.
