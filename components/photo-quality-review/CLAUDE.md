# photo-quality-review — Context

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
