# photo-quality-review — Card Archive

Historical record of archived Done/Defer kanban cards for this component (CARD-0193's archiving process, migrated to this dedicated file by CARD-0290 — previously these were appended directly into `CLAUDE.md`, which grew unboundedly and stopped being practical to read in full). **Not read as part of routine Session Start or component-session startup** (`JCTsh-Component-Session-Start.md`) — on-demand lookup only. See this component's own `CLAUDE.md` for current, curated context.

---

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 5412B, over the 5000B size threshold.

### CARD-0178 · [enhancement] [photo-quality-review] Auto-select the larger photo for same-owner near-duplicate pairs, sort groups by size — RESOLVED 2026-08-17 12:05 MST

**Status:** Done

**Raised 2026-08-16 (Joseph):** "New rule for photo review: if two photos have the same owner, auto select the largest photo." Genuinely new logic — `maybeAutoSelectGroup()` (`public/review.js`) currently has three tie-breaker steps (Motion Photo integrity → album membership → cross-account identical-size), and every one of them either applies regardless of owner or explicitly requires the two photos to have *different* owners (CARD-0155's cross-account tie-breaker and Super Rule). There's no existing same-owner branch, and file size is currently only ever compared for exact equality, never "pick the bigger one" — a same-owner pair that's merely near-duplicate (not byte-identical) currently gets no auto-select at all and sits for manual review indefinitely.

**Interviewed 2026-08-16:**
- New step inserted into `maybeAutoSelectGroup()`'s existing priority chain, right after the album-membership check (and its disagree-with-motion abstain), before the cross-account identical-size tie-breaker — same "only fires once stronger signals are inconclusive" gating the existing steps already use.
- Condition: both members share the same `ownerLabel`, both have a non-null `size`, and the sizes differ. Auto-select the larger.
- If sizes are exactly equal (no "larger" to pick): abstain, leave for manual review — same "can't decide, don't guess" behavior the existing steps already use when signals disagree.
- **Not asked, decided here and flagged for confirmation at Build/verify time:** unlike the cross-account tie-breaker, this rule does *not* require czkawka `difference === 0`. Reasoning: the group is already czkawka-near-duplicate by construction (that's why it's a group at all), this only ever touches one person's own library (lower consequence than the cross-account case, which is why that one demanded byte-identical certainty before touching someone else's collection), and "larger file = likely the original/higher-quality version, smaller = a resized or re-compressed copy" is a common-sense heuristic that doesn't need byte-level identity to be reasonable. Worth Joseph confirming this reasoning holds before/while building, not fixed in stone from this interview alone.

**Scope grew mid-build, 2026-08-16 (Joseph):** "Sort duplicate photos by size with largest photo last" — a display-order change for how a group's members are laid out, folded into this same card rather than opened separately (same component, same duplicate-group area, same session).

**Acceptance criteria:**
1. New tie-breaker step added to `maybeAutoSelectGroup()`, matching the priority placement and gating above.
2. `autoReason` text for this case clearly distinguishes it from the existing cross-account reason (e.g. "same owner, kept the larger file") — the UI surfaces this reason, per the existing pattern.
3. Verified live against a real same-owner near-duplicate pair in the actual review UI (not just unit logic) — correct member auto-selected, correct reason shown, and an equal-size same-owner pair correctly abstains instead of guessing.
4. Confirm this doesn't interact badly with the Super Rule's own static/server-side structural checks (`isSuperRuleStaticCandidate()`/`isSuperRuleCandidate()`) — Super Rule is cross-account by definition, so this new same-owner step should never overlap with it, but worth confirming rather than assuming.
5. Group members render sorted by file size ascending, largest last.

**Built 2026-08-16:**
- New tie-breaker branch in `maybeAutoSelectGroup()` (`public/review.js`), inserted exactly where interviewed — after the album-membership check, before the cross-account tie-breaker's `else`. Equal-size same-owner pairs correctly fall through to that final `else` too (its own `isCrossAccount` check fails for a same-owner pair), landing on "still nothing decisive" and abstaining — no special-casing needed, the existing fallthrough already does the right thing.
- `renderDuplicateGroup()` now renders from a sorted *copy* of `group.members` (ascending by `size`, nulls sorted first), not an in-place sort — `group.members` itself is left untouched since other code reads it order-sensitively elsewhere (the group-list's own date sort uses `members[0]` as a representative timestamp; `maybeAutoSelectGroup`'s `a`/`b` pair is already order-agnostic by construction, but no reason to couple the two regardless).
- No Node available locally to syntax-check — used the M8 itself (`node --check`, it already has Node for this service) before deploying. This is a static frontend file served via plain `express.static`, no server restart needed; confirmed the *actually-served* file (not just the copied one) contains the new code via a live HTTP fetch.

**Verified live 2026-08-17 12:05 MST (Joseph):** confirmed against a real same-owner near-duplicate pair in the actual review UI — correct member auto-selected, reason text correct, sort order (largest last) correct. No-`difference`-gate reasoning confirmed to still hold.

**Related:** CARD-0155 (the existing cross-account tie-breaker and Super Rule this new step sits alongside, same file/function), CARD-0148 (perf/debounce work on the same `maybeAutoSelectGroup()` call path).

---

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 7056B, over the 5000B size threshold.

### CARD-0148 · [bug] [photo-quality-review] Confirm & Delete and auto-select are both slow -- redundant/blocking work, not real API limits
**Status:** Done

**Raised 2026-08-11**, from Joseph asking how to run two instances of the review app -- the real motivation turned out to be that Confirm & Delete takes a long time, which surfaced a second, related slowness in auto-select once diagnosed. Two independent root causes found by reading the actual code (not guessed):

**1. Confirm & Delete (`server.js` `/api/confirm`).** The per-item delete loop is fully sequential: `await immich.deleteAsset(...)` then `await deletionLog.logDeletion(...)` for every item, one at a time. `deleteAsset` is a fast local call (M8 -> its own Immich container), but `logDeletion` includes `await postToSheet(record)` -- a real internet round-trip to Google Apps Script per item. The code's own comment already establishes this POST is best-effort ("A Sheet POST failure must never block or roll back an already-confirmed Immich delete") and its failure is already caught and just logged -- so awaiting it before moving to the next item buys nothing, it's just blocking for no correctness reason.

**2. Auto-select (`public/review.js` `maybeAutoSelectGroup`).** Once both members' Motion Photo status and album membership are known for a 2-member duplicate group, an unambiguous case gets auto-decided -- fires `/api/decide/duplicate` then `refreshTally()`. On a page with dozens of groups, many can auto-select in a tight burst as badge fetches (already concurrency-capped at 6) resolve. Each auto-select independently triggers a full `refreshTally()` -> `/api/preview` -> `pendingDeletions()`, which re-reads and re-parses `report.json` (whole-library scan data), the entire deletion-log CSV, and `decisions.json` from disk, then loops the whole library -- on *every single call*, no caching. 20-30 auto-selects landing close together means 20-30 redundant full-library reloads, competing with the still-in-flight badge fetches on the same single-threaded Node server.

**Fix, agreed with Joseph:**
1. Stop awaiting the Sheet POST inline in the confirm loop -- fire it, keep the same catch-and-warn behavior via `.catch()` instead of blocking try/catch. Add a small bounded concurrency (e.g. 5) on the main per-item loop as a safety margin, not because Immich itself is currently slow.
2. Debounce `refreshTally()` during auto-select bursts -- coalesce multiple auto-selects landing close together into one refresh shortly after the last one, instead of one full expensive refresh per group.

**Done when:** both fixes are deployed to the M8 and verified against real behavior (a real Confirm & Delete batch and a real page with multiple auto-selectable groups), not just "code looks right" -- matching this project's own verification standard elsewhere. Server-side caching of `pendingDeletions()`'s disk reads is a known further optimization, deliberately out of scope here unless the debounce alone doesn't get far enough.

**Built 2026-08-11:**
1. `deletion-log.js`'s `logDeletion()` no longer awaits `postToSheet()` -- fires it with a `.catch()` instead, same warn-on-failure behavior, off the critical path.
2. `server.js`'s `/api/confirm` delete loop now runs through a small `mapWithConcurrency` (limit 5) instead of a plain sequential `for` loop, mirroring `scan.js`'s own existing helper of the same shape.
3. `review.js`'s `maybeAutoSelectGroup()` now calls a new `scheduleTallyRefreshDebounced()` (200ms) instead of `refreshTally()` directly, so a burst of auto-selects collapses into one tally refresh instead of one per group.

All three syntax-checked with real `node -c` on the M8 (no local Node available on Joseph's machine) before deploying. `server.js`/`deletion-log.js` deployed and require a `sudo systemctl restart photo-quality-review` to take effect (handed to Joseph to run interactively -- this session's tools can't supply a sudo password over SSH); `review.js` is served statically and takes effect on next page load, no restart needed.

**Addendum, same session:** Joseph also asked to add the photo's taken-date to the review page itself (unrelated to the performance fix, folded into this card rather than opened separately since it's the same file/page and came up in the same breath -- flag if you'd rather it be its own card). `fileCreatedAt` was already present on every item (comes straight through from Immich's own asset record via `routes/immich.js`'s `buildPathIndex`) but never rendered anywhere. Added a `formatPhotoDate()` helper (viewer's own local timezone, `toLocaleDateString`) and wired it into both `duplicateMeta()` (duplicate-group thumbnails) and `renderSingle()` (broken/blurry thumbnails). Deployed; no server restart needed (static file).

**Service restarted 2026-08-11, confirmed `active`** -- `server.js`/`deletion-log.js` fixes are now genuinely live, not just deployed to disk.

**Confirm & Delete exercised for real, 2026-08-11 ~13:00 MST -- Joseph ran several real batches from 2017 duplicates, reported "lightning fast."** Speed alone doesn't prove correctness given the concurrency + fire-and-forget changes, so verified each leg independently rather than trusting the feel of it:
- **Immich delete:** queried the Immich API directly for 3 asset IDs from the batch -- all 3 confirmed `isTrashed: true`. The concurrency change didn't cause anything to silently skip.
- **Local CSV log:** `/mnt/photo-library/deletion-log.csv` shows a dense cluster of new rows, all timestamped within the same second matching the batch. `appendLocalCsv()` is still `await`ed per item regardless of concurrency, so this was never actually at risk.
- **Google Sheet log:** the one leg that's fire-and-forget, and the one thing not directly verifiable from the M8 (no read access to the Sheet from here) -- Joseph pasted the Sheet's own last-10-rows, which match the local CSV's entries exactly (same filenames/timestamps/asset IDs/reasons). Confirms the fire-and-forget POST isn't silently dropping rows.
- No `Google Sheet POST failed` warnings anywhere in the service's journal since the restart (this app does no per-request logging otherwise, so silence here specifically means no failures fired, not an absence of monitoring).

Fix 1 (Confirm & Delete) is now fully verified end-to-end against real data, not just "code looks right."

**Closed out 2026-08-11 13:10 MST on Joseph's go-ahead.** Fix 2 (auto-select debounce) and the photo-date addition were deployed and syntax-checked but not separately re-exercised against real behavior the way Fix 1 was -- both are low-risk, small, self-contained changes (a debounce timer and a new display-only field), and Joseph chose to close rather than hold the card open for that. Reopens under a fresh card if either turns out not to behave as expected live.

**Related:** CARD-0028 (the review app this extends), `components/photo-quality-review/server.js`, `components/photo-quality-review/routes/deletion-log.js`, `components/photo-quality-review/public/review.js`.

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3584B, over the 2000B size threshold.

### CARD-0189 · [bug] [photo-quality-review] "Super rule" bulk-delete marking phase is very slow — RESOLVED 2026-08-22 17:20 MST
**Status:** Done

**Raised 2026-08-22 17:07 MST (Joseph), live during a review session** — after choosing "Delete all N in Robin's library" (CARD-0155's super-rule bulk-delete box), the "Marking decisions: X of Y…" phase is very slow, well before the actual Immich delete step even starts.

**Root cause, found via code read of `server.js`/`public/review.js`:** the client's Phase 1 loop calls `/api/decide/duplicate` once per qualifying group (6-way concurrency via `forEachWithConcurrency`), but every one of those calls does a full read-parse-mutate-write of the *entire* `decisions.json` file (`loadDecisions()` → mutate → `saveDecisions()`), and all such writes are serialized through a single global lock (`withDecisionsLock`, added by CARD-0028 to fix a real race condition). So N groups means N sequential full-file I/O round trips, not N fast in-memory updates — and it gets slower over time as `decisions.json` accumulates decisions across the whole multi-year review. This is a *different* bottleneck than CARD-0148's already-known-and-accepted `refreshTally()`/`pendingDeletions()` cost.

**Scope, decided via interview 2026-08-22:** fix only the super-rule bulk-delete marking phase — add a new bulk endpoint (e.g. `POST /api/decide/duplicates-bulk`) that takes the full list of qualifying groupKeys in one request, does a single `loadDecisions()` → mutate all → single `saveDecisions()`, still under the existing lock. `openSuperRuleModal`'s Phase 1 in `review.js` switches to this one call instead of the per-group loop. Regular one-at-a-time manual clicks (radio/skip/keep-all/delete-all buttons) are explicitly out of scope — a human clicking one at a time doesn't expose the same N-round-trip cost the way a tight programmatic loop does.

**Done when:** marking all qualifying groups for a real year with a meaningful `qualifiedCount` completes in roughly the time of one file write (not N round trips), confirmed live against real data — not just code review. `decisions.json` after the bulk-mark matches what N individual `/api/decide/duplicate` calls would have produced (same keys, same `{ keepAssetId, auto: true, autoReason }` shape) — no regression in the correctness CARD-0028's locking fix established.

**Related:** CARD-0155 (super-rule bulk-delete feature this bug is in), CARD-0028 (review app, `decisions.json` locking discipline), CARD-0148 (separate, already-known `refreshTally()` cost — not what this card fixes).

**Fixed and deployed, 2026-08-22 17:20 MST.** Added `POST /api/decide/duplicates-bulk` to `server.js` (single load → mutate all → single save under the existing lock) and switched the super-rule modal's Phase 1 in `review.js` to call it once instead of looping `/api/decide/duplicate` per group. **Found live on the first deploy:** the new client loop called `findDuplicateGroup()` — a linear scan over the whole library's 38,258 duplicate groups — once per qualifying key with no yielding, which froze the tab for the entire loop and was worse than the original (Joseph: "even slower than before"). Fixed by building a one-time `groupKey → group` lookup Map before the loop (O(M) once, O(1) per key) instead of repeated linear scans. Deployed both fixes to the M8 (`server.js` + `sudo systemctl restart photo-quality-review` for the first; `review.js` alone, no restart needed, for the second — static file). Confirmed fast live by Joseph against real data.

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3790B, over the 2000B size threshold.

### CARD-0155 · [enhancement] [photo-quality-review] "Super rule" bulk-delete for exact cross-account duplicates (identical filename/date/size, diff 0) — RESOLVED 2026-08-13 14:02 MST
**Status:** Done

**Raised 2026-08-12 17:54 MST**, Joseph's request mid-session while reviewing the existing auto-select duplicate logic.

**What "done" looks like:** For each year in the review UI, any duplicate group that is:
- exactly 2 members, one in Joseph's Immich library and one in Robin's,
- identical `originalFileName`,
- identical `fileCreatedAt`,
- identical file size,
- czkawka `difference: 0` for both members (exact perceptual-hash match — the same qualifying signal the existing cross-account tie-breaker in `maybeAutoSelectGroup()` already uses),
- and not already decided,

...gets pulled out of the normal per-group Duplicates list for that year (the individual photos are never rendered) and instead counted into a single "Super Rule" summary box: total count + one "Delete all in Robin's library" button.

**Album-check gate (Joseph's call, interviewed live):** before a candidate qualifies, still check each member's Immich album membership (same live `/api/albums/:assetId` call the normal auto-select flow already makes) — if Robin's copy is the one linked to an album and Joseph's isn't, exclude that pair from the Super Rule bucket entirely (falls back to normal per-group manual review, same as today) rather than deleting something that would silently lose an album link. Motion Photo video-integrity checks are explicitly **not** part of this gate — ignored for this rule, unlike normal auto-select.

**Delete action:** clicking "Delete all in Robin's library" deletes Robin's copy of every qualifying photo via the existing Immich delete pipeline (soft-trash, `force: false`, same as Confirm & Delete) and logs each to the existing deletion-log CSV/Sheet, same as every other deletion path in this app. Joseph's copy is always the one kept.

**Explicitly open for the build:** whether the button gets its own confirmation step — "don't show the photos" rules out a Preview-style itemized list, but some in-page confirmation (count + an explicit second click) is still expected before an irreversible-feeling bulk action.

**Built, deployed to the M8, and verified live.** Confirmation modal deliberately count-only (no itemized list, per "don't show the photos"), reusing the existing `/api/decide/duplicate` + `/api/confirm` pipeline rather than a new delete path.

**Found and fixed live during first real use:** the bulk "Delete all" button scoped `/api/confirm` to every qualifying groupKey for the year in one request — fine for the normal per-page Confirm & Delete flow (capped at ~100 groups by pagination) but not for this button, which can legitimately scope thousands. A real 2,529-group year 413'd (`PayloadTooLargeError`, Express's default 100kb JSON body limit) *before* the request reached the route handler, so nothing was deleted and nothing was corrupted — only the (harmless, idempotent) per-group decide calls had already landed. Raised `express.json()`'s limit to 5mb in `server.js`. Verified by replaying the exact same oversized payload against the fixed server (200 OK, all 2,529 items resolved correctly), then Joseph re-ran Confirm & Delete live: all 2,529 deleted from Robin's library, logged correctly, `decisions.json` left valid with the resolved groupKeys cleared.

**Related:** `components/photo-quality-review/public/review.js`'s existing `maybeAutoSelectGroup()` cross-account tie-breaker (2026-08-08) — this is a stricter, UI-different variant of the same underlying "identical size + diff 0, keep Joseph's copy" rule, scoped per-year and skipping individual review entirely instead of auto-checking a radio button.

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3906B, over the 2000B size threshold.

### CARD-0149 · [enhancement] [photo-quality-review] Retain historical report.json snapshots for comparison
**Status:** Done

**Raised 2026-08-11**, after Joseph asked about a rescan's completion notification (38,258 duplicate groups) and wanted to know whether that was more than the previous scan turned up -- there was no way to tell, since `scan.js` overwrites `report.json` in place on every run, with no history kept.

**Scope: retention only, not comparison.** Joseph explicitly deferred the diff/comparison half ("38,258 duplicate groups (312 new since last scan)" in the notification) to build later -- this card is just making sure the data exists to compare against, not building the comparison itself.

**Design:** confirmed `groupKey()` (`server.js`) is already stable across rescans -- it's the sorted set of member asset IDs, not scan order or position, so two snapshots really can be diffed meaningfully once this exists. Before `scan.js` overwrites `report.json`, move the existing one into a new `data/report-history/` subdirectory under a filename timestamped from *that report's own* `generatedAt` field (not "now" -- "now" is when it's being retired, not when it was actually generated). `report.json` stays the one filename the app reads; nothing else in `server.js` changes. Deliberately no pruning/retention cap for now -- each snapshot is ~36MB and scans look ad-hoc/infrequent (this was the first rescan since the app's original build), so it would take dozens of scans before size is worth worrying about; simpler to add a cap later if it actually becomes a problem than to guess at a number now.

**Done when:** `scan.js` archives the previous `report.json` into `data/report-history/` (timestamped from its own `generatedAt`) before writing a new one, deployed to the M8, and verified with a real scan run that the history file lands correctly and `report.json`/the app itself are unaffected.

**Built 2026-08-11.** New `archivePreviousReport()` in `scan.js`, called right before the final `fs.writeFile(REPORT_PATH, ...)`: reads the existing `report.json`, pulls its `generatedAt` (falls back to current time if the file's malformed/older-format), then `fs.rename`s it into `data/report-history/report-<timestamp>.json` -- a same-filesystem move, not a copy, so no need to duplicate a ~36MB file on disk just to relocate it.

**Verified in isolation against real Node on the M8, not just "code looks right"** -- `scan.js` itself runs a full ~12.6-minute real scan with no way to unit-test just this one function in place (no `require.main` guard, importing it kicks off the whole scan), so the exact function body was run standalone against synthetic data in a scratch directory: (1) first-ever scan, no existing `report.json` -- no-op, no error; (2) normal case, valid `generatedAt` -- correctly archived as `report-2026-08-10T13-38-44.864Z.json`, original `report.json` confirmed gone; (3) malformed JSON -- falls back to a current-time stamp rather than crashing; (4) repeated archiving -- no filename collisions, all snapshots preserved distinctly. Deployed to `~/photo-quality-review/scan.js` on the M8 (syntax-checked with real `node -c` first), test scratch directory cleaned up afterward.

**Closed out 2026-08-11 on Joseph's go-ahead -- "leave it, it'll run naturally."** Not yet exercised end-to-end against a real scan run (`scan.js` isn't a persistent service, so no restart needed either -- it just takes effect on the next invocation); deliberately not forced today given the isolated test already covers the actual logic faithfully and a full run costs ~12.6 minutes. Real end-to-end proof arrives the next time a rescan runs naturally -- reopens under a fresh card if the history file doesn't land correctly then.

**Related:** CARD-0028 (the review app this extends), CARD-0148 (same component, prior round), `components/photo-quality-review/scan.js`.

---

