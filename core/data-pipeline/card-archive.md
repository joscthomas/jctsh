# core/data-pipeline — Card Archive

Historical record of archived Done/Defer kanban cards for this component (CARD-0193's archiving process, migrated to this dedicated file by CARD-0290 — previously these were appended directly into `CLAUDE.md`, which grew unboundedly and stopped being practical to read in full). **Not read as part of routine Session Start or component-session startup** (`JCTsh-Component-Session-Start.md`) — on-demand lookup only. See this component's own `CLAUDE.md` for current, curated context.

---

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 5053B, over the 5000B size threshold.

### CARD-0099 · [bug] [data-pipeline] Timeline sheet's `timestamp_az` column hardcodes Arizona local time for every row, regardless of where it happened — RESOLVED 2026-07-25
**Status:** Done

**Raised 2026-07-25**, discovered while confirming CARD-0097's fix — Joseph asked "are there any other columns in any sheet so named," which surfaced this second, more serious instance of the same standing principle ([[feedback_no_location_assumptions]]).

**Real gap, not just a stale label (unlike `date_az` in Hike Start Forecast, which CARD-0097 already made cosmetic-only):** `refreshTimeline()` (JCTsh menu → Refresh Timeline) merges Environmental Data + Hiking Observations into the "Timeline" sheet, and unconditionally formatted every row's display time via `_azString()` — hardcoded Arizona (UTC-7, no DST) — regardless of where that reading/observation actually happened. A Michigan or Egypt hike's rows would have silently shown the wrong wall-clock time, mislabeled as if it were correct.

**Fix:** replaced `_azString()` with `_localString(utcDate, lat, lon, offsetCache)`, resolving each row's real UTC offset *and* IANA zone name via Open-Meteo's `timezone=auto` (same provider/mechanism as CARD-0097), cached per rounded `(lat,lon)` for the life of one `refreshTimeline()` run so repeated locations (a fixed home sensor, or many readings from one hike) cost one real HTTP call, not one per row. Column renamed `timestamp_az` → `timestamp_local` — and since this sheet is fully rewritten (`clearContents()` + header) on every refresh, the rename actually takes effect immediately, unlike the Hike Start Forecast header which only sets its header once at sheet creation.

**Format iterated twice at Joseph's request:** first cut appended just the raw UTC offset (e.g. `+03:00`) — Joseph pointed out a bare offset means nothing without already knowing which place maps to it. Switched to leading with the IANA zone name (e.g. `Africa/Cairo`), which Open-Meteo already resolves as part of the same lookup at no extra cost — then added the raw offset back in parentheses alongside it, since that's still useful for quick arithmetic between rows. Final format: `YYYY-MM-DD HH:MM:SS Zone/Name (±HH:MM)`, e.g. `2026-07-25 17:24:37 Africa/Cairo (+03:00)`. Rows with no GPS correlation yet, or where the Open-Meteo lookup itself fails, fall back to an explicit `... UTC` label rather than a wrong guess.

**Live-verified 2026-07-25** against real production data (14,545 rows, spanning 2019–2026): after redeploying and running Refresh Timeline, Joseph confirmed directly from the Sheet that the real Giza test coordinate (29.9792, 31.1342, left over from CARD-0097's verification) now shows `2026-07-25 17:26:45 Africa/Cairo (+03:00)`, while a real fixed Arizona sensor (lat 32.4612997, lon -111.1184154) correctly shows `America/Phoenix (-07:00)` — different locations resolving to their own correct zone, not one hardcoded assumption for everything. Sort order also confirmed correct: the Giza row's true UTC instant (14:26:45 UTC) sorts just before the Arizona rows (14:31:44 UTC onward), confirming the sort key is still the real timestamp, not the display string.

**Troubleshooting note during verification:** the first "Refresh Timeline" click produced no corresponding entry in the Apps Script Executions log at all — the menu click hadn't actually invoked the function (likely a stale menu binding in an already-open browser tab from before the redeploy). Fully reloading the Sheet tab and re-clicking fixed it; the resulting execution (`Head`/`Menu`/`refreshTimeline`, 38.9s, Completed) is what actually produced the correct data. Worth remembering for any future Apps Script custom-menu debugging in this repo: check the Executions log for a *matching* entry before assuming a run happened at all.

**Related discovery, not yet acted on:** verifying this fix via the `action=export` HTTP endpoint turned out to be unreliable in a way that goes beyond the endpoint's already-documented Timeline caveat — `_exportSheet` silently drops (not just mis-filters) any row whose column A doesn't parse as a valid JS `Date`, and this happens *unconditionally*, even when no `start`/`end` filter is requested. The old Arizona-only format happened to still parse via V8's lenient date parsing; the new zone-name format (e.g. `... Africa/Cairo (+03:00)`) does not, so the export endpoint was quietly hiding exactly the rows needed to verify this fix. Verification was completed instead by having Joseph read the Sheet directly. Not fixed as part of this card — flagged for a possible follow-up if `action=export` needs to reliably return Timeline rows in the future.

**Related:** CARD-0097 (same standing principle, same Open-Meteo `timezone=auto` mechanism, found first), [[feedback_no_location_assumptions]] (the standing principle both cards are instances of), `core/data-pipeline/environmental-data.gs`, `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`, `components/hiking-monitor/data-pipeline.md`.

---

**Archived from `tos/kanban-board.md` on 2026-09-10 (CARD-0193)** — 5954B, over the 5000B size threshold.

### CARD-0245 · [bug] [data-pipeline] Hike Start Forecast session-gap check compares against the wrong row — 48 spurious forecast captures on one real hike — RESOLVED 2026-09-06

**Status:** Done

**Raised 2026-09-06**, found while auditing every sheet tab in "JCTsh Environmental Data" for inappropriate duplicates, following the CARD-0243/CARD-0244 dedup fixes. Not a byte-identical-duplicate issue like those two — this is a different shape: **48 spurious forecast rows for a single continuous hike (2026-08-13)**, each just 30 seconds to a few minutes apart, when every other hike in the sheet's history correctly produced exactly 1-2 forecast rows (2 only when a calendar day genuinely contained two separate real hikes, hours apart).

**Root cause, confirmed directly:** `_maybeCaptureHikeStartForecast`'s session-gap check (`environmental-data.gs`, CARD-0115) compares the new GPS point's timestamp against `gpsSheet.getRange(lastRow - 1, 1)` — whichever row is *physically* second-to-last in GPS Track — not the truly closest-preceding point in time. This assumes GPS Track's insertion order matches chronological order, which CARD-0243 already disproved for 2026-09-03 (182/684 rows out of order) and which is **even worse** for 2026-08-13: exporting that hike's raw GPS Track data and checking insertion order found **242 of 242 consecutive rows (100%) out of chronological sequence**. With insertion order this scrambled, the "gap" computed is effectively comparing against a near-random other point, repeatedly producing an apparent gap > `SESSION_GAP_MIN` (10 min) for points that were really only seconds apart from their true predecessor — misfiring "new session" 48 times.

**Distinct from, and not fixed by, CARD-0243/CARD-0244.** Those fixed exact-*duplicate* insertion (rejecting a resend of the same point). This bug is about insertion *order* — a genuinely new, non-duplicate point can still land out of chronological sequence under network jitter/retries even with dedup in place, and this check would misfire again the next time that happens on a flaky-connectivity hike. Both root causes trace back to the same underlying reality (GPSLogger's retries against a slow endpoint don't arrive in the order they were captured), but this is a separate bug needing its own fix.

**Real, quantified cost:** 48 wasted Open-Meteo API calls and 48 near-duplicate rows cluttering Hike Start Forecast for what should have been 1 row, on the 2026-08-13 hike specifically (already independently known as a bad-connectivity day, per CARD-0156's own investigation of that same hike's voice-observation losses).

**Fix:** replace the physically-adjacent-row comparison with a true chronological scan — find the maximum timestamp *strictly less than* the current point's `tsISO` across all of GPS Track's column A (same full-column-read cost class `_gpsLookup` and CARD-0243's own dedup check already accept, not a new performance tier), and compute the gap against that value instead of `getRange(lastRow - 1, 1)`. If no such prior timestamp exists (this point is chronologically the earliest on record, or the very first point ever), fall through to capturing a new forecast — same conservative default the current code already has for the "first point ever" case.

**Built, 2026-09-06.** `_maybeCaptureHikeStartForecast` in `core/data-pipeline/environmental-data.gs` updated: reads column A once (`getRange(2, 1, lastRow - 1, 1)`), scans for the maximum value strictly less than the target timestamp, uses that as the true "previous point" for the gap calculation. `SCRIPT_VERSION` bumped to `2026-09-06.3-forecast-session-gap-fix`.

**No cleanup of existing spurious rows planned as part of this card** — the 47 extra 2026-08-13 rows are harmless clutter (each is a real, valid Open-Meteo response, just redundant), not corrupted data; removing them is a separate, optional manual Sheet edit Joseph can do at his discretion, not gated on this fix.

**Deployed and verified live, 2026-09-06 — a real test constructed to reproduce the exact failure mode, not just re-checked the fix by inspection.** `?action=version` confirmed `2026-09-06.3-forecast-session-gap-fix`. Test sequence: inserted point A (`20:00:00Z`), then point Z (`19:00:00Z` — chronologically *before* A, but inserted *after* it, deliberately setting the "physically previous row" trap), then point B (`20:03:00Z` — only 3 minutes after A, should continue A's session). Result: **A and Z each correctly got their own forecast row** (both genuinely isolated when inserted); **B got no forecast row at all** — correctly recognized as continuing A's session via the true 3-minute gap, despite sitting physically right after Z. Under the old code, B would have been compared against Z (the physically-previous row) — a 63-minute gap, exceeding `SESSION_GAP_MIN` — and spuriously fired a third forecast row, exactly reproducing the 2026-08-13 failure shape. All 3 synthetic GPS Track rows and 2 synthetic Hike Start Forecast rows confirmed deleted afterward (`action=export` on that window returns `count: 0` for both sheets).

**Done when:** a real or simulated GPS point arriving out of physical-row-order (e.g., inserted after a point with a later timestamp) no longer triggers a false new-session forecast capture when a truly-recent prior point exists elsewhere in the sheet, verified via a real test rather than assumed from the fix alone; `?action=version` confirms the redeploy took effect. **Met.**

**Related:** CARD-0243 (the GPS Track dedup fix that first found the out-of-order-insertion pattern this bug depends on), CARD-0244 (Hiking Observations' sibling dedup fix), CARD-0115 (the original session-gap design this corrects), CARD-0156 (the 2026-08-13 hike's independently-known connectivity problems, now also explaining this bug's worst occurrence), `core/data-pipeline/environmental-data.gs` (`_maybeCaptureHikeStartForecast`).

---

**Archived from `tos/kanban-board.md` on 2026-09-10 (CARD-0193)** — 10848B, over the 5000B size threshold.

### CARD-0243 · [bug] [data-pipeline] GPS Track ingest (`doGet`, `action=gps`) has no de-duplication — 29.5% of the 2026-09-03 hike's trackpoints are exact duplicates — RESOLVED 2026-09-06

**Status:** Done

**Raised 2026-09-06**, found while analyzing the 2026-09-03 hike's full dataset for anomalies. Of 685 raw GPS Track rows for that hike, **202 (29.5%) are byte-identical duplicates** — same ISO timestamp, same lat/lon, same accuracy, same altitude, same direction. Duplicate-group sizes ranged from 2 up to **6 copies of a single point**. This is a genuinely new finding, not previously tracked.

**Root cause, confirmed by reading the code (`core/data-pipeline/environmental-data.gs`, `doGet()`, `action === 'gps'`):** the handler unconditionally does `gpsSheet.appendRow([tsISO, lat, lon, acc, alt, direction])` on every call — there is no check for an existing row with a matching timestamp before appending. This is the exact same class of gap CARD-0215 already fixed for `doPost()`'s Environmental Data branch (range + dedup checks added there, `SCRIPT_VERSION` bumped to `2026-08-25.1-ingest-validation`) — but the fix was scoped to Environmental Data only and never extended to the GPS Track branch, which uses a completely separate code path (`doGet`, not `doPost`).

**Likely trigger, not yet confirmed:** GPSLogger's custom-URL logging almost certainly retries a point's GET request when it doesn't receive a fast/confirmed response — Google Apps Script web apps are known to have slow, variable response times, and cellular signal in canyon/mountain terrain (this hike's own location) compounds that. Each retry that Apps Script actually processes lands as a brand-new duplicate row with no way to tell it apart from a genuinely new point at the ingest layer.

**Real but limited impact — confirmed, not assumed:** does **not** corrupt the actual hike statistics. `hike_data.json`'s reported distance (6.79 mi), pace, and elevation gain all matched the chart series' own post-processed 80-point series exactly — a duplicate point at zero distance from itself doesn't add spurious mileage. The concrete costs are: (1) wasted Sheet storage/bloat, same category of problem CARD-0211/CARD-0215 already treated as worth fixing for Environmental Data; (2) a misleading `coverage_pct` metric in the hike page's own GPS-session reporting (this hike showed "139%"/"128.6%" coverage — more points than the 30s cadence should produce — which is really duplication inflating the raw count, not denser-than-expected real tracking).

**Plan for Build, written 2026-09-06 — the exact change, adapted from CARD-0215's own committed pattern (`doPost`'s Environmental Data branch, lines ~208-229) rather than reinvented:**

1. **Dedup key: `ts` alone, not `(ts, source)`.** Environmental Data dedups on `(ts, source)` because multiple sensor sources feed that sheet. GPS Track has exactly one producer (GPSLogger's custom-URL POST) and no `source` column at all — `tsISO` alone is a sufficient and correct key here; a real duplicate submission always carries the identical timestamp (confirmed directly: all 134 duplicate-timestamp groups found in the 2026-09-03 data had byte-identical coordinates too, zero cases of two different real points sharing one timestamp).
2. **Insert point:** in `doGet()`'s `action === 'gps'` branch (`environmental-data.gs`, currently around line 777-802), immediately before the existing `gpsSheet.appendRow([tsISO, lat, lon, acc, alt, direction])` call — after `tsISO` is computed (needed as the dedup key) but before the row is written.
3. **Cheap column-only read, same discipline CARD-0215 used:** `gpsSheet.getRange(2, 1, gpsSheet.getLastRow() - 1, 1).getValues()` — column A only (timestamps), not the full row — so the check stays cheap as the sheet grows, same reasoning as Environmental Data's own dedup check.
4. **Concrete code:**
   ```javascript
   if (gpsSheet.getLastRow() > 1) {
     var existingTs = gpsSheet.getRange(2, 1, gpsSheet.getLastRow() - 1, 1).getValues();
     for (var i = 0; i < existingTs.length; i++) {
       var val = existingTs[i][0];
       val = (val instanceof Date) ? val.toISOString() : String(val);
       if (val === tsISO) {
         return ContentService
           .createTextOutput(JSON.stringify({status: 'duplicate', ts: tsISO}))
           .setMimeType(ContentService.MimeType.JSON);
       }
     }
   }
   ```
   **Decided 2026-09-06 (Joseph):** placed *before* the `_maybeCaptureHikeStartForecast(...)` call — a rejected duplicate returns immediately and does not reach that call, so a resent first point can't risk a second forecast-capture attempt even if that function's own internal logic turns out to already be idempotent (not separately checked, since it no longer matters once dedup short-circuits first).
5. **`SCRIPT_VERSION` bump** (currently `2026-09-02.6-wildlife-file-stem-fix`) — mandatory per this script's own established convention, so `?action=version` can confirm a redeploy actually took effect.
6. **Deployment — same manual path every other change to this file uses; Claude cannot deploy it.** Paste the updated `environmental-data.gs` into the Apps Script editor, **Deploy → Manage deployments → pencil → Version: New version → Save**.

**No range/plausibility validation added here** — deliberately out of scope. This card is about the missing dedup guard specifically (mirroring CARD-0215's dedup half only, not its range-check half); GPS lat/lon/accuracy range validation, if ever wanted, would be its own separate card rather than scope creep onto this one.

**One-time cleanup — decided 2026-09-06 (Joseph): yes, add it, same pattern as CARD-0215's `cleanupDuplicateEnvironmentalData()`.** New `cleanupDuplicateGpsTrack()`, added to the JCTsh custom menu (`Cleanup Duplicate GPS Track (CARD-0243, one-time)`), run once after the ingest fix is deployed:
```javascript
function cleanupDuplicateGpsTrack() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('GPS Track');
  var data = sheet.getDataRange().getValues();
  var header = data[0];

  function keyOf(row) {
    var ts = row[0];
    return (ts instanceof Date) ? ts.toISOString() : String(ts);
  }

  var seen = {};
  var kept = [header];
  var droppedDuplicates = 0;

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    var key = keyOf(row);
    if (seen[key]) { droppedDuplicates++; continue; }
    seen[key] = true;
    kept.push(row);
  }

  sheet.clearContents();
  sheet.getRange(1, 1, kept.length, header.length).setValues(kept);

  Logger.log('Original rows: ' + (data.length - 1));
  Logger.log('Kept rows: ' + (kept.length - 1));
  Logger.log('Dropped as duplicates: ' + droppedDuplicates);
  SpreadsheetApp.getUi().alert(
    'Cleanup complete.\n' +
    'Original rows: ' + (data.length - 1) + '\n' +
    'Kept: ' + (kept.length - 1) + '\n' +
    'Dropped as duplicates: ' + droppedDuplicates
  );
}
```
Simpler than Environmental Data's own cleanup — no `isBadRow`/corrupted-row-dropping half, since this card carries no range-validation scope (see above); first-seen-wins dedup only. Same "run once, safe to remove afterward" lifecycle as CARD-0215's version — the permanent protection lives in the ingest-side fix (steps 1-4), not in this menu function.

**Built, 2026-09-06 — code written exactly per the plan above, not yet deployed.** `core/data-pipeline/environmental-data.gs` updated: the dedup check inserted in `doGet`'s `action=gps` branch (before `appendRow`, before `_maybeCaptureHikeStartForecast`, per the decided ordering), `cleanupDuplicateGpsTrack()` added alongside `cleanupDuplicateEnvironmentalData()` with a matching new JCTsh menu item, `SCRIPT_VERSION` bumped to `2026-09-06.1-gps-track-dedup`. Reviewed by eye for balanced braces/correct scoping (no `node`/syntax-checker available in this environment, unlike CARD-0215's own `node --check` verification) — one `var i` loop variable in the new dedup check, confirmed not colliding with any other `var i` elsewhere in `doGet`.

**Deployment note — this is Apps Script, deployed by pasting into the Apps Script editor (no `clasp`/API tooling in this repo) — Claude can't deploy or run it.** Needs Joseph to: paste the updated `environmental-data.gs` into the Apps Script editor, **Deploy → Manage deployments → pencil → Version: New version → Save**, confirm `?action=version` returns `2026-09-06.1-gps-track-dedup`, then run **JCTsh menu → Cleanup Duplicate GPS Track (CARD-0243, one-time)** once.

**Verified live end-to-end, 2026-09-06 — all four criteria met against real data, not synthetic-only:**
- **Dedup rejection confirmed live:** a real test GPS point sent twice — first `{"status":"ok"}`, second (identical `ts`) `{"status":"duplicate","ts":"..."}`, never appended a second time. The one real synthetic row this created was manually deleted afterward, confirmed gone via `action=export`.
- **Cleanup run and internally consistent:** `cleanupDuplicateGpsTrack()` reported **Original: 5328 · Kept: 4934 · Dropped as duplicates: 394** (4934 + 394 = 5328, exact).
- **2026-09-03 hike re-checked post-cleanup:** GPS Track export for that hike's window now returns **483 rows, zero duplicate timestamps** (was 685 rows / 202 duplicates before the fix) — exactly matching the 483 unique timestamps the original investigation found.
- **`coverage_pct` re-verified against a real regeneration**, not just the raw row count: re-ran `--step2`/`/webhook/step2` against the now-deduplicated data — the hike session's own `coverage_pct` dropped from a nonsensical **139.0%** to a sane **97.1%** (the trailing driving-session's own 128.6% → 100.0%).

**Done when:** `doGet`'s `action=gps` branch rejects a duplicate-timestamp resubmission instead of appending it (verified via a real repeated test GET, same "send twice, confirm second is rejected" pattern CARD-0215 used); `cleanupDuplicateGpsTrack()` has been run once against the live sheet and its reported before/after counts are internally consistent (kept + dropped = original); a real hike's GPS Track data shows zero duplicate timestamps post-fix; and the hike page's own `coverage_pct` metric reports a sane value (not >100%) against real data. **Met.**

**Related:** CARD-0215 (the identical dedup pattern already built for Environmental Data — this card is its GPS Track sibling), CARD-0211 (the reset-loop incident that originally motivated CARD-0215's dedup work), CARD-0226 (a separate, unrelated finding from this same 2026-09-03 investigation — a hiking-monitor reboot-loop recurrence), `core/data-pipeline/environmental-data.gs` (`doGet()`'s `action=gps` branch), `components/hike-izer/fetch_hike_data.py` (the consumer that surfaced this via `hike_data.json`'s raw `gps_track` array).

---

**Archived from `tos/kanban-board.md` on 2026-09-10 (CARD-0193)** — 9957B, over the 5000B size threshold.

### CARD-0215 · [bug] [data-pipeline] Duplicate Environmental Data rows from CARD-0211's reset loop, plus no dedup-on-ingest at all — RESOLVED 2026-08-25 evening
**Status:** Done

**Raised 2026-08-25 (Claude, found while live-testing CARD-0214's gap-fill re-fetch).** The 2026-08-25 hike-summary page's Environmental Data section, after CARD-0214's fresh re-fetch, showed "10196 of 103 expected (9899.0% coverage)" — implausible on its face. Checked directly: the hike has exactly **103 unique `(timestamp, source)` readings** (matching the expected 2-minute-cadence count for a 3h26m hike), but up to **159 duplicate rows per timestamp**, concentrated in the 13:37-13:56Z stretch. Root cause is CARD-0211's reset loop: before the watchdog fix landed, the device repeatedly retried the same buffered-reading replay and crashed partway through each attempt — every failed attempt still published whatever readings it got through before crashing, so early-buffer readings got re-published dozens of times across the repeated attempts (159 → 155 → ... tapering as the crash point drifted).

**Real scope, pulled from a full-sheet export (`action=export&sheet=Environmental%20Data`, all 33,932 rows, not just today's hike) — the same day this was found, not estimated:**

| Date | Duplicated keys | Excess rows |
|---|---|---|
| 2026-08-25 | 94 | 10,093 |
| 2026-08-22 | 14 | 27 |
| 2026-06-12 | 1 | 2 |
| 2020-01-01 | 1 | 2 |
| **Total** | **110** | **10,124** (of 33,932 total rows — ~30%) |

2026-08-25 is CARD-0211's incident and accounts for the overwhelming majority.

**Second finding, same day, raised directly by Joseph reviewing the live page: some of those duplicated readings aren't just repeated, they're corrupted.** The 2026-08-25 hike's Environmental Data section showed implausible ranges (temp 80.2-370.6°F, pressure down to -174.9 hPa, UV index up to 7294.4). Checked directly: exactly **one** distinct `(timestamp, source)` key — `2026-08-25T16:03:06Z` — carries genuinely impossible values (`temp_f: 370.6, humidity_pct: 100, pressure_hpa: -174.9, uv_index: 7294.44`), duplicated **74 times**, almost certainly a mid-crash MQTT publish during CARD-0211's reset loop writing garbage into the payload as the device reset partway through serializing it. This is a distinct problem from plain duplication — deduplicating this key down to "one copy" would still leave one bad row; **Joseph's explicit call: don't allow corrupted data into the store at all, dedup alone isn't the fix.**

**2026-08-22's 14 keys / 27 excess rows, investigated directly rather than left as a guess:** all 14 have real, plausible sensor values (temp 93-99°F, real GPS coordinates) and each is duplicated exactly **3** times — same signature as CARD-0211's reset loop (a failed replay attempt re-publishing readings before crashing), just a much smaller episode, 3 failed attempts instead of dozens. A real, previously-undiagnosed earlier instance of the same class of firmware bug, three days before CARD-0211 — not root-caused further (the watchdog-timeout fix already covers whatever caused both), just now identified rather than silently swept into the cleanup.

**2026-06-12 and 2020-01-01, checked directly, not assumed:** both are the *same* fixed placeholder reading (`temp_f: 85, humidity_pct: 20, pressure_hpa: 925, uv_index: 0`, no GPS), each tripled — not the `clock_invalid` skip-logging hypothesis originally guessed (that path just logs a skip event, no data write), but the same small-scale retry/duplicate signature as 2026-08-22, landing on a boot where the device's clock hadn't been set yet and fell back to a fixed default reading. Same underlying pattern family, different trigger condition.

**Decided 2026-08-25 (Joseph), directly rejecting Claude's first-draft "dedupe at read time" proposal, then again rejecting "just dedup" once the corrupted-data finding came in:** the Sheet itself is the canonical data store — bad data shouldn't be allowed in at all, and cleanup-at-read-time would leave every future reader needing to independently know to filter it. **Two-part fix:**
1. **One-time cleanup** — rewrite the live "Environmental Data" sheet keeping exactly one row per valid unique `(timestamp, source)` key (first-seen wins); any key whose values are physically implausible is dropped **entirely** (zero rows kept), not deduplicated to one.
2. **Ingest validation, structural, permanent** — `environmental-data.gs`'s `doPost()` now rejects (`{status: 'rejected', reason: 'out_of_range', ...}`) a payload with any of `temp_f` (-20 to 130°F), `humidity_pct` (0-100%), `pressure_hpa` (800-1100 hPa), or `uv_index` (0-20) outside sane physical bounds, and separately rejects (`{status: 'duplicate', ...}`) an exact `(ts, source)` repeat — both checked before ever reaching `appendRow`. Neither check is specific to CARD-0211's already-fixed watchdog bug; both guard the sheet against *any* future cause of a bad or repeated publish.

**Built 2026-08-25 evening:**
- `environmental-data.gs`: range + dedup checks added to `doPost()`'s Environmental Data branch (dedup check reads only columns A/B via `getRange(2,1,lastRow-1,2)`, not the full row, to keep it cheap as the sheet grows — the performance question from the original open-questions list resolved this way rather than left unmeasured). `SCRIPT_VERSION` bumped to `2026-08-25.1-ingest-validation`. New `cleanupDuplicateEnvironmentalData()` — one-time function, added to the Sheet's own `JCTsh` custom menu (`Cleanup Duplicate Environmental Data (CARD-0215, one-time)`) so it's a menu click, not a trip into the Apps Script editor's function picker. Rewrites the sheet in one bulk `setValues()` call (not thousands of individual `deleteRow` calls), logs and alerts a real before/after summary (original/kept/dropped-duplicate/dropped-corrupted counts) so the result is confirmed against this card's own numbers, not trusted blind. Syntax-checked clean (`node --check`).
- **Deployment note — this is Apps Script, deployed by pasting into the Apps Script editor (no `clasp`/API tooling in this repo, confirmed no automated path exists) — Claude can't deploy or run it.** Needs Joseph to: paste the updated `environmental-data.gs` into the Apps Script editor, **Deploy → Manage deployments → pencil → Version: New version → Save**, then reload the Sheet tab and run **JCTsh menu → Cleanup Duplicate Environmental Data** once. File is on the clipboard, ready to paste.

**Redeployed and cleanup run by Joseph, verified live end-to-end, 2026-08-25 evening:**
- `?action=version` confirmed `2026-08-25.1-ingest-validation` — redeploy live.
- Range-validation confirmed live via a real test POST (`temp_f: 999`): rejected with `{"status":"rejected","reason":"out_of_range","field":"temp_f","value":999}`, never reached the sheet.
- Duplicate-rejection confirmed live via a real test POST sent twice (same `ts`/`source`): first attempt `{"status":"ok"}`, second `{"status":"duplicate",...}` — not appended a second time. (The one real synthetic row this necessarily created was manually deleted afterward.)
- Cleanup run reported **Original: 33,937 · Kept: 23,812 · Dropped as duplicates: 10,051 · Dropped as corrupted: 74** — internally consistent (23,812 + 10,051 + 74 = 33,937, exact).
- **A real verification wrinkle, caught rather than glossed over:** the post-cleanup `action=export` scan initially showed only 23,077 rows — 735 short of the cleanup's own reported 23,812. Rather than assume real data loss from a destructive rewrite, checked the actual ground truth: Joseph confirmed the Sheet's own row count directly (23,812, exact match) via the Sheets UI itself, not the export endpoint. The gap was `_exportSheet`'s own **pre-existing, already-documented bug** (CARD-0099: silently drops any row whose column A doesn't parse as a valid JS `Date`, even unfiltered) resurfacing after the cleanup's bulk `setValues()` rewrite changed how some cells' timestamps are typed — not a new problem this card introduced, and no real data was lost. Worth remembering: trust the Sheet UI's own row count over `action=export` for anything where the exact total matters.
- **Final proof the whole fix (CARD-0214 + CARD-0215 together) works as designed:** re-ran `--step2 2026-08-25` against the now-clean sheet — environmental fetch dropped from 10,196 rows to **102** (vs. 103 expected), with zero code changes needed beyond the two cards' own fixes; CARD-0214's re-fetch-on-every-pass design meant the page self-corrected the moment the underlying data did. Live page confirmed: **"102 of 103 expected (99.0% coverage)"**, Temperature 80.2-114.1°F, Humidity 13.7-53.2%, Pressure 902.2-926.4hPa, UV Index 0.0-7.1 — all physically sane, matching a real hot Arizona summer hike.

**Done when:** the Apps Script redeploy and cleanup run are confirmed live (`?action=version` returns `2026-08-25.1-ingest-validation`; a fresh full-sheet duplicate scan shows zero duplicate keys and zero out-of-range values remaining); the dedup/range checks are confirmed working via a real repeated/out-of-range test payload (rejected, not appended); and the 2026-08-25 hike-summary page, regenerated afterward, shows a sane coverage figure (103/103, not 9899%) with no implausible temperature/pressure/UV values. **Met, 2026-08-25 evening** — all criteria verified live, per above.

**Related:** CARD-0211 (the reset-loop incident that caused the overwhelming majority of this, including the corrupted reading), CARD-0214 (the gap-fill re-fetch that made this visible for the first time — step 2 never used to re-query real Environmental Data at all, so nobody had looked at this hike's true row count or value ranges until now), `core/data-pipeline/environmental-data.gs` (`doPost()`'s Environmental Data append branch, `cleanupDuplicateEnvironmentalData()`), `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`.

---

**Archived from `tos/kanban-board.md` on 2026-09-10 (CARD-0193)** — 6612B, over the 5000B size threshold.

### CARD-0197 · [idea] [data-pipeline] Instrument GPS correlation lookup to confirm the suspected Node-RED/Apps Script timing race — RESOLVED 2026-08-29
**Status:** Done

**Built and deployed, verified live 2026-08-24 00:21 MST.** Implemented as designed, with one refinement: rather than duplicating the get-or-create-sheet + appendRow logic at both call sites, added a shared helper `_logCorrelationDebug(ss, eventType, targetTs, bestDiffSec)` (`environmental-data.gs`, right above `_gpsLookup`) that gets or creates the "Correlation Debug" tab (writing a header row on first creation: `logged_at, event_type, target_ts, best_diff_sec`) and appends one row. `_gpsLookup()` calls it with `'lookup_miss'` on a miss (before its final `return`); the `action=gps` handler calls it with `'gps_append'` right after its existing `gpsSheet.appendRow(...)`.

**Deployment confirmed, not just assumed:** `SCRIPT_VERSION` bumped to `2026-08-24.1-correlation-debug` (missed on the first pass, caught when Joseph asked about it directly), then verified live via `curl "...?action=version"` — returned `{"status":"ok","version":"2026-08-24.1-correlation-debug"}`, exact match, confirming the redeploy actually took effect rather than trusting the editor's own "saved" state (per this file's own established gotcha, CARD-0099's card history).

**Remaining before this card is fully Done:** capture at least one real blank-lat/lon occurrence on a future hike with both a `lookup_miss` and a matching `gps_append` row, and do the T1-vs-T2 wall-clock comparison this card exists to enable. Instrumentation is live and ready to catch it; nothing more to build until that happens.

**Raised 2026-08-23 04:39 MST (Joseph), following up on the blank-lat/lon investigation from the 2026-08-22 hike's data-gap review.** 6 of 97 Environmental Data readings that hike came back with blank lat/lon, all clustered in the last ~50 minutes. The working theory (not yet proven): `_gpsLookup()` (`environmental-data.gs:276-295`) scans the "GPS Track" sheet for the nearest point *at query time*, ±5 minutes — if the hiking-monitor's buffered-reading correlation call fires before GPSLogger's own webhook-triggered write for the matching point has landed in the sheet, the lookup finds nothing nearby yet and returns null, even though the real point shows up seconds later. Joseph's call: **not worth fixing** (already a known, accepted, low-impact gap per hike-izer's own docs — see the "fixing the correlation timing" discussion, declined as its own card) — but wants confirmation the theory is actually correct, not just plausible.

**Instrumentation plan, designed in this conversation — small, additive, no behavior change to the correlation logic itself:**

1. **New "Correlation Debug" sheet tab** in the "JCTsh Environmental Data" workbook — one row per logged event: `[logged_at (real wall-clock ISO timestamp, not the reading's own ts), event_type, target_ts, best_diff_sec]`.

2. **In `_gpsLookup()`** (`environmental-data.gs:276-295`), right before the final `return`, log only misses (keeps row volume low):
   ```js
   if (bestDiff > fiveMin || bestRow === null) {
     ss.getSheetByName('Correlation Debug').appendRow(
       [new Date().toISOString(), 'lookup_miss', tsISO, bestRow ? bestDiff/1000 : null]);
   }
   ```

3. **In the `action=gps` handler** (`environmental-data.gs:511-536`), right after the existing `gpsSheet.appendRow(...)` at line 536, log every GPS point landing:
   ```js
   ss.getSheetByName('Correlation Debug').appendRow([new Date().toISOString(), 'gps_append', tsISO]);
   ```

**How this proves (or disproves) the theory — a direct comparison, not another inference.** For any `lookup_miss` row (reading timestamp X, wall-clock time T1), find the `gps_append` row whose own point timestamp is closest to X, and check its wall-clock time T2. If T2 > T1 — the matching GPS point landed in the sheet *after* the lookup already gave up — that's conclusive proof of the race. If T2 < T1, the theory is wrong and something else is causing the blanks, which is worth knowing too.

**Scope is diagnostic only — no fix implied or required.** This card is done once the instrumentation is deployed and has captured at least one real blank-lat/lon occurrence on a future hike with enough data to make the T1-vs-T2 comparison — confirming or refuting the theory either way counts as done. Whether to act on a confirmed race (vs. continue accepting it) is a separate future decision, not part of this card.

**Resolved 2026-08-29 — theory refuted, via CARD-0222, not the literal T1-vs-T2 comparison this card originally envisioned.** The 2026-08-29 hike produced exactly the real blank-lat/lon occurrence this card's instrumentation was waiting for: 46 of 55 Environmental Data readings came back with no lat/lon (CARD-0222). Cross-checked each of the 46 readings' own timestamps directly against this card's own Correlation Debug sheet — **zero matching `lookup_miss` rows for any of them.** That's a direct answer, not an absence of data: if this card's race theory were correct, a failing lookup would still have *fired* and logged a `lookup_miss` row (with `_gpsLookup()` reaching its own final `return`) before losing the race against a GPS point that landed moments later. Instead, `_gpsLookup()` was never even invoked for these 46 — the correlation call itself never completed, most likely because the device was mid-reboot-loop during buffered-reading replay at the time (CARD-0221/CARD-0222's real, separately-diagnosed cause). **This structurally rules out the race hypothesis for this occurrence** — the instrumentation this card built is exactly what made that determination possible, even though the actual failure mode turned out to be a different bug than the one this card set out to catch. Per this card's own bar ("confirming or refuting the theory either way counts as done"), that's satisfied. Follow-on work (finding and fixing the reboot loop itself) continues under CARD-0221/CARD-0222, not here.

**Related:** the 2026-08-22 hike's blank-lat/lon investigation (this conversation), the declined "fix the correlation timing" discussion (same conversation, Joseph's call not to pursue a fix — this card only pursues *confirmation*), `core/data-pipeline/environmental-data.gs`, `.claude/skills/hike-izer/SKILL.md` ("Notes on the data" section, which already documents this as a known gap), CARD-0221/CARD-0222 (the real 2026-08-29 blank-lat/lon occurrence this card's instrumentation resolved against, and the actual root cause it pointed to instead).

---

**Archived from `tos/kanban-board.md` on 2026-09-22 (CARD-0193)** — 14533B, over the 5000B size threshold.

### CARD-0306 · [bug] [data-pipeline] Environmental Data pipeline overwrites a stationary device's own coordinates with the hiker's live GPS during a hike

**Status:** Done — RESOLVED 2026-09-19 18:37 MST

**Retitled 2026-09-19 (Joseph's question: "front porch sensor is stationary, why is it making GPS lookup calls?").** The original framing below (repeated HTTP 404s) turned out to be a minor symptom of a much more real problem this question surfaced — a stationary device's own correct coordinates silently getting overwritten by wherever the hiker currently is, whenever a hike happens to overlap in time. The 404 investigation is kept intact below as the thread that led here; the actual fix addresses the real bug, not the 404s.

**Raised 2026-09-19, from CLAUDE.md's Session Start dashboard scan — not yet interviewed, captured as a finding pending investigation.** Three occurrences on three consecutive days, all the same Alert shape from `core/data-pipeline/environmental-data.flow.json`'s `env-data-gps-log-failure` node (CARD-0279):
- `2026-09-17 20:37:21 MST` — `GPS lookup failed after 3 attempts for front-porch-temp-sensor reading @ 2026-09-18T03:35:55Z (status 404)`
- `2026-09-18 04:43:15 MST` — same, reading @ `2026-09-18T11:40:55Z`
- `2026-09-19 06:48:23 MST` — same, reading @ `2026-09-19T13:46:06Z`

All three timestamps fall well outside any hike window (front-porch-temp-sensor is a stationary device, not carried) — no burst context like CARD-0279's hiking-monitor replay scenario, just a single isolated `action=lookup` call each time.

**Checked `core/data-pipeline/environmental-data.gs`'s `doGet` `action === 'lookup'` handler directly, rather than assuming a code-level cause:** it unconditionally returns `ContentService.createTextOutput(JSON.stringify(coords))` — always HTTP 200, whether `_gpsLookup` finds a match or returns `{lat:null, lon:null}`. There is no code path in this script that produces a 404. **This rules out "expected no-match for a non-hiking reading" as the explanation** — a genuine miss would come back 200 with null coordinates, not 404, and CARD-0279's own retry/log logic already treats a 200-with-null as resolved, not retried. A literal HTTP 404 has to be coming from Apps Script's own web-app infrastructure (stale/misrouted deployment, a transient Google-side failure, or the same general Apps-Script-under-load flakiness already tracked across CARD-0258/0270/0275/0276/0279), not from this script's own logic.

**Open questions 1-3 answered, 2026-09-19, via `action=export` against the real Environmental Data sheet (not inferred):** exported the full 2026-09-17T00:00Z–2026-09-19T18:00Z window (66 hours, spanning all three occurrences) and counted sources directly: **788 `front-porch-temp-sensor` readings vs. 50 `hiking-monitor` readings in the same window** — front-porch-temp-sensor reports roughly every 5 minutes, 24/7, making it by far the highest-volume caller of `action=lookup` on any non-hike day (a ~16:1 call-volume ratio here). 3 final-failures out of 788 calls is a **0.38% failure rate** — small enough to plausibly be ordinary exposure to the same baseline Apps-Script transient-failure rate already documented across CARD-0258/0270/0275/0276, not a distinct failure mode or anything device-specific. No rotated log backup (`jctsh.log.1`/`.2`/etc.) carries this Alert text at all — consistent with it being new since CARD-0279's `env-data-gps-log-failure` node was deployed 2026-09-17 evening, not evidence of a longer-running problem. No timing pattern found across the three (20:37, 04:43, 06:48 MST) beyond "whenever this device's ~5-minute cadence happens to draw a bad call."
1. **Answered:** not concurrent-load-specific — front-porch-temp-sensor's sheer call volume, not a distinct trigger, explains why it's the device that surfaces this.
2. **Answered:** no evidence of any other device hitting this in the same window (hiking-monitor: 0 of 50; no other source appeared in the export at all) — consistent with front-porch-temp-sensor's outsized call volume being the actual reason, not a device-specific fault.
3. **Answered:** no timing pattern found; treat as background rate, not schedule-correlated.
4. **Superseded by the real finding below** — the answer turns out to be "don't call it at all for this device," which also makes question 4's Alert-suppression question moot (zero calls means zero chance of a lookup Alert).

**Real bug found 2026-09-19, answering Joseph's actual question.** Checked `components/front-porch-temp-sensor/front-porch-temp-sensor.yaml` (lines 148/181/189): the device hardcodes and self-reports its own correct, fixed coordinates in every MQTT payload it sends (`lat:32.4612997, lon:-111.1184154`, "H8 front porch" per `house-lot-coordinates.md`) — it was never supposed to need a GPS lookup at all. But `core/data-pipeline/environmental-data.flow.json`'s `Check GPS lookup response (CARD-0279)` node does `d.lat = gps.lat` **unconditionally** whenever `_gpsLookup` finds any match, with no check for whether the reading already carried a known-good coordinate. Confirmed live via the real Environmental Data sheet: during today's hike, front-porch-temp-sensor's own "location" drifted through the hike almost exactly tracking the hiker's real position (e.g. `32.4570349,-111.1130772` at 13:51:06Z, essentially the same spot hiking-monitor logged at 13:51:57Z) — a real geotagging-correctness bug, not just wasted API calls. It only shows its correct fixed coordinate when no hike happens to be running (the 3 known 404s were also just noise from this same unnecessary call path).

**Scope-checked the other two devices that reference coordinates, not assumed:** `air-quality-monitor.yaml` sends `"lat":null,"lon":null"` explicitly — it's carried on hikes and correctly wants the lookup fill-in. `hiking-monitor.yaml` also wants the lookup (the whole point of this pipeline), and its own "at home" fallback is already special-cased in the same function node. **Only front-porch-temp-sensor is affected** — the one device that's both stationary and already self-reports a real coordinate.

**Fix built 2026-09-19: skip the GPS-Track lookup entirely when a reading already carries non-null `lat`/`lon`.** `env-data-gps-prep` ("Prepare GPS lookup") gained a second output — `outputs: 2`, with a new guard at the top of its function: `if (d.lat !== null && d.lat !== undefined) { msg.payload = d; return [null, msg]; }`, wired straight to `env-data-process` ("Compute derived fields + build POST"), bypassing the throttle/lookup/check-response chain entirely for a device that already knows its own location. The normal lookup path (output 0, unchanged) still runs for anything sending `null` coordinates (air-quality-monitor, hiking-monitor).

**Deployed live 2026-09-19 (Joseph's explicit go-ahead — the harness's own auto-mode classifier blocked the first attempt as a "Production Deploy" and required it).** Used the Node-RED admin API directly rather than the UI import procedure, to avoid `Node-RED-workflow.md`'s documented duplicate-tab risk. **Real gotcha found along the way, worth keeping for next time:** the live flow's actual node IDs (e.g. `c0208e8454c6d1d9` for this node) do **not** match the human-readable IDs in this repo's checked-in JSON (`env-data-gps-prep`) — Node-RED reassigns its own IDs on import, so a direct API patch has to match nodes by **name**, fetch the live ID, and rewrite `wires` to point at live IDs of the target nodes, not the repo file's IDs. Documented as its own method in `Node-RED-workflow.md`. `curl -X POST /flows` with the corrected full array returned `204`; `journalctl -u nodered` showed a clean `Stopping flows → Updated flows → Starting flows → Started flows` with MQTT reconnecting, no errors, and every other tab's timers still firing normally afterward.

**Verified live against real production data, not inferred from the deploy succeeding.** Checked Apps Script's own Correlation Debug sheet (CARD-0197) directly — it logs a row for every `_gpsLookup` call, hit or miss, completely independent of Node-RED's own success/failure reporting:
- **Pre-deploy reading** (`front-porch-temp-sensor` @ `2026-09-19T18:36:06Z`, before the 18:38:18Z deploy): **2 `lookup_miss` rows** in Correlation Debug — the old code called the lookup, as expected.
- **Post-deploy reading** (`front-porch-temp-sensor` @ `2026-09-19T18:41:06Z`): **zero rows** in Correlation Debug — proof the lookup was never called, not just that it happened to find nothing.

**Forward-fix done when:** front-porch-temp-sensor's readings stop calling `action=lookup` at all, verified against live production data rather than inferred from the deploy alone. **Met, 2026-09-19 — see the before/after Correlation Debug proof above.** (The original geotagging-during-a-hike scenario itself will get a final live confirmation on the next real hike, same as any Build-verified fix without a hike to test against today; not blocking on that specifically — a skipped call can't overwrite anything, regardless of whether a hike happens to be running.)

**Historical scope checked, 2026-09-19 (Joseph: "what about the front porch sensor data?") — this bug predates CARD-0279 entirely.** The unconditional `d.lat = gps.lat` overwrite was already in the GPS-lookup function (then named "Apply GPS coords") since front-porch-temp-sensor was first wired into this shared pipeline — `git log`: commit `d298abf1`, 2026-06-14. Exported the full Environmental Data history (`action=export`, 2026-06-14 through today, 30,434 rows) and compared every `front-porch-temp-sensor` row against its known-correct fixed coordinate: **569 of 27,625 rows carry a drifted, wrong coordinate**, spanning 2026-06-17 through today, tracking almost every hike date since (06-18, 07-29, 08-15, 08-18, 08-22, 08-25, 08-27, 08-29, 09-03, 09-08, 09-10, 09-15, 09-17, 09-19).

**Practical impact assessed, not just row-counted.** Checked every consumer of Environmental Data's `lat`/`lon` columns in `environmental-data.gs`: the only one is `_localString()` (line ~473), which uses a row's coordinate solely to resolve which timezone to display that row's local timestamp in (CARD-0097's fix). Every drifted coordinate is still a few miles from home, well inside `America/Phoenix` either way, so this has never actually produced a visibly wrong result. `hike-izer`'s `fetch_hike_data.py` never touches these rows at all — it's hardcoded to `--source hiking-monitor` (CARD-0285's own finding). **Net effect: real but low-stakes** — factually wrong data sitting in the sheet, no functional consequence found anywhere it's actually used.

**Joseph's call, 2026-09-19: fix it, run in the background (not blocking on a live conversation turn).** Correction is unambiguous — front-porch-temp-sensor's coordinate is always the same fixed constant, so any row where it doesn't match is wrong and gets reset, nothing else touched.

**Built, 2026-09-19, following this repo's own established Apps Script deployment convention (confirmed via `card-archive.md`: no `clasp`/API tooling exists here — Claude cannot deploy or run Apps Script changes, Joseph has to paste-and-deploy manually, same as CARD-0215/CARD-0243 before it).** Added `fixFrontPorchCoordinates()` to `core/data-pipeline/environmental-data.gs`, same one-time-menu-item pattern as `cleanupDuplicateEnvironmentalData`/`cleanupDuplicateGpsTrack` right above it: iterates every `Environmental Data` row, and for any `front-porch-temp-sensor` row whose `lat`/`lon` doesn't already match the known-correct constant, overwrites just those two cells. Logs a summary (rows fixed / already correct / other sources untouched) via `Logger.log` and a UI alert. New menu item: **JCTsh → Fix Front-Porch-Temp-Sensor Coordinates (CARD-0306, one-time)**.

**Deployed and run by Joseph, 2026-09-19.** One real gap caught along the way: the original build never bumped `SCRIPT_VERSION`, so there was no reliable way to confirm the paste-and-deploy had actually taken effect (Joseph: "not seeing the updated environmental-data.gs" — deploy had silently not landed yet). Fixed by bumping `SCRIPT_VERSION` to `2026-09-19.1-front-porch-coord-fix` and confirming `?action=version` returned it live before proceeding — exactly the tool this constant exists for, per its own comment. Once confirmed live, the menu item ran and reported:
```
Front-Porch-Temp-Sensor coordinate fix complete.
Rows corrected: 569
Already correct: 27137
Other sources (untouched): 3467
```
**569 — matches this card's own predicted count exactly.**

**Independently re-verified against the live sheet, not just the alert text.** Re-ran the full `action=export` history scan (2026-06-14–2026-09-19, 27,687 front-porch-temp-sensor rows by now, more having landed since the original 27,625-row count): **0 rows remain drifted from the known-correct coordinate.** Both the forward fix (no new drift can occur) and the historical correction (no drift remains) are now confirmed live, independently, not inferred from either the deploy succeeding or the menu's own report alone.

`fixFrontPorchCoordinates()` and its menu item left in place for now, same as `cleanupDuplicateEnvironmentalData`/`cleanupDuplicateGpsTrack` beside it — safe to remove, not yet done, matching actual practice on this file rather than the stated convention.

**Done when:** the forward-fix (met, see above) **and** the one-time historical correction has actually been run and confirmed. **Both met, 2026-09-19.**

**Related:** CARD-0279 (the retry/log mechanism that originally surfaced the 404s; same `env-data-gps-log-failure` node, now unreachable for this device), CARD-0258/CARD-0270/CARD-0275/CARD-0276 (the broader Apps-Script-under-load flakiness thread the 404s turned out not to really belong to), `core/data-pipeline/environmental-data.gs` (`doGet` action=lookup handler, `_gpsLookup`), `core/data-pipeline/environmental-data.flow.json` (`env-data-gps-prep`), `components/front-porch-temp-sensor/front-porch-temp-sensor.yaml` (the hardcoded coordinate this fix protects), `Node-RED-workflow.md` (the new API-patch deploy method this used), CARD-0215/CARD-0243 (the one-time-menu-item cleanup pattern `fixFrontPorchCoordinates` follows), CARD-0097 (the timezone-resolution consumer that's the only reason this data's correctness matters at all), CARD-0285 (confirms `hike-izer` never touches these rows, bounding this card's real-world impact).

---

**Archived from `tos/kanban-board.md` on 2026-09-22 (CARD-0193)** — 11118B, over the 5000B size threshold.

### CARD-0279 · [bug] [data-pipeline] Field-mode replay burst overwhelms Apps Script's per-reading GPS lookup — missing coordinates scale with reading volume

**Status:** Done — RESOLVED 2026-09-19 11:15 MST

**Raised 2026-09-17 (Joseph + Claude), from investigating why today's 2026-09-17 hike showed 17 of 31 (55%) Environmental Data readings with no GPS coordinates.** Initially suspected as a consequence of CARD-0226's hiking-monitor reboot loop (today was that card's 6th recurrence) — **ruled out as the general explanation, confirmed by Joseph's own observation and real data.** Checked missing-GPS rate across hikes with zero CARD-0226 occurrence, well before that reboot loop ever started:

| Hike | Readings | Missing GPS |
|---|---|---|
| 2026-08-27 | 14 | 0% |
| 2026-08-24 | 44 | 5% |
| 2026-08-22 | 97 | 6% |
| 2026-08-25 | 102 | 9% |

A clean volume trend with no reboot loop anywhere nearby — the real mechanism is unrelated to CARD-0226.

**Mechanism, confirmed by reading the actual code (`core/data-pipeline/environmental-data.flow.json`'s "GPS lookup"/"Apply GPS coords" nodes) and cross-checking the "Correlation Debug" sheet (CARD-0197's own diagnostic tooling):** hiking-monitor has zero WiFi/MQTT connectivity during an actual hike (field mode, confirmed via the flow's own `rssi_dbm: 0` comment) — every reading buffers on-device and only reaches Node-RED in one tight burst at reconnect (today: all 31 readings within ~4 seconds, 07:53:31-35 MST). Each reading fires its own separate `action=lookup` HTTP GET to Apps Script. The "Apply GPS coords" function node only fills in `lat`/`lon` on a clean `msg.statusCode === 200` response — any timeout, error, or non-200 status from that individual call silently falls through with **no retry and no error logging**, leaving that reading's coordinates permanently blank. A burst of many near-simultaneous requests against one Apps Script deployment is exactly the load pattern already shown flaky this week under different symptoms (CARD-0258's GPS Track timeouts, CARD-0275's incident, CARD-0276's slow-response-but-succeeds finding) — some fraction of the burst's individual lookup calls fail, roughly proportional to burst size.

**One real exception, not covered by this card:** 2026-08-29 (55 readings, 84% missing) is a large outlier against the volume trend above — that hike is where CARD-0226's reboot loop happened *during the replay itself* (10 reboots in 35 seconds while actively streaming), a distinct and more severe failure mode (the replay stream interrupted mid-flight, not just Apps Script choking on volume). That finding stays on CARD-0226; this card covers the general, always-present volume-driven gap.

**Design direction, decided via conversation 2026-09-17 (Joseph's question: "which approach is best? both?") — three complementary fixes, not competing alternatives:**
1. **Throttle** — space out the outgoing `action=lookup` calls during a replay burst (e.g. a Node-RED rate-limiting delay node) instead of firing them all within the same few seconds, reducing peak concurrent load on Apps Script. Addresses the actual root cause, not just the symptom.
2. **Retry** — a short retry-on-failure for an individual lookup call that still fails despite throttling (network blip, one slow execution) — catches stragglers without needing the whole burst redesigned.
3. **Log** — a failed lookup currently leaves zero trace anywhere. At minimum, log when a lookup ultimately fails after retries, so a pattern like today's 55% miss rate is visible without manually diffing `hike_data.json`.

**Bigger alternative considered and deliberately held in reserve:** a single batched Apps Script endpoint resolving N timestamps in one call instead of N separate `action=lookup` requests would eliminate the burst entirely — the most architecturally correct fix, but a much bigger lift (new Apps Script action, new Node-RED batching/response-correlation logic, more surface to test) for a problem throttling + retry should resolve at far lower cost. Revisit only if the smaller fix doesn't hold.

**Moved to Build and flow changes drafted, 2026-09-17.** `core/data-pipeline/environmental-data.flow.json` updated, all three fixes wired into the existing GPS-lookup path between "Prepare GPS lookup" and "Compute derived fields + build POST":
1. **Throttle:** new `env-data-gps-throttle` delay node (Node-RED core `delay`, `pauseType: "rate"`) inserted between "Prepare GPS lookup" and "GPS lookup" — caps outgoing `action=lookup` calls at 2/sec (`drop: false`, so messages queue rather than get silently dropped under load) instead of firing a whole burst within the same second or two.
2. **Retry:** "Apply GPS coords" renamed to "Check GPS lookup response (CARD-0279)", rewritten with 3 outputs instead of 1. A 200 response (real match, or a confirmed miss — `_gpsLookup()` already logs a genuine miss server-side via Correlation Debug, CARD-0197, so that's resolved, not retried) continues downstream immediately. A non-200 (timeout/error/Apps-Script-overload) retries by looping back through the same throttle node, up to 3 total attempts (`msg._lookupAttempt`, seeded in "Prepare GPS lookup").
3. **Log:** once retries are exhausted, a new `env-data-gps-log-failure` mqtt-out node (same `jctsh/core/log-server/log` topic/pattern as the flow's existing "Log success/error" node) publishes an `Alert` naming the component, reading timestamp, and last HTTP status — the reading still publishes with no coordinates rather than being dropped, but the failure is now visible on the dashboard instead of silent.

**Verified so far:** the full JSON parses (13 nodes, up from 8); all 5 function nodes' JS bodies syntax-checked clean (`node --check`, run on the M8, one file per function node).

**Import/deploy done, with a real duplicate-tab detour along the way (the general Node-RED import-safety findings from this are now in `Node-RED-workflow.md`).** The import created a genuine duplicate "Environmental Data" tab (the old, cleared tab plus a fresh one holding the new nodes) — confirmed directly via the Node-RED admin API (`GET /flows`, authenticated via `/auth/token`), not just visually: the new tab (`d15dbc9164b2dce9`) correctly holds all 12 nodes including the three new CARD-0279 ones. The stale empty tab was deleted and deploy re-run 2026-09-17; a follow-up API check confirmed exactly one "Environmental Data" tab remains, 12 nodes, no leftover duplicate.

**Still not yet verified:** the throttle/retry/log path exercised against a real or simulated burst — no hike has happened since the deploy. **Done when:** a real hike with a large reading-volume burst shows a meaningfully lower missing-GPS rate than the pre-fix volume trend predicts, and a deliberately-forced lookup failure is confirmed to retry, exhaust, and produce a real Alert on the dashboard rather than failing silently. **Met, 2026-09-19 — see resolution below.**

**Resolved 2026-09-19, via CLAUDE.md's Session Start Watch-for check against the 2026-09-19 hike (Joseph's ask, checked directly against the exported Environmental Data sheet, not inferred).** `action=export` on the Environmental Data sheet for the hike's window (`2026-09-19T12:00:00Z`–`17:00:00Z`) returned 19 `hiking-monitor` readings, **1 missing GPS coordinates (5.3%)** — a large drop from the pre-fix volume trend's ~50%+ prediction for a hike this size (table above). The one gap (`2026-09-19T16:36:28Z`) lands 7 minutes after the hike's own `gpsloggerevent=stopped` webhook (09:29:13 MST) — outside any GPS Track point's ±5 minute match window, a genuine no-match (correctly resolved as `{lat:null,lon:null}`, no retry/Alert expected), not a lookup failure.

**Second Done-when criterion also met, via a real (not deliberately forced) production failure rather than a synthetic test — stronger evidence per this project's own "live beats synthetic" principle (`JCTsh-Operating-System.md`, Note on Build).** The `env-data-gps-log-failure` node's retry-then-Alert path fired for real on 2026-09-17, 2026-09-18, and 2026-09-19 (`front-porch-temp-sensor` readings, HTTP 404 after 3 attempts each) — confirms the throttle/retry/log mechanism itself works correctly end-to-end on live data. **Root cause of *why* those specific lookups 404 is a separate, still-open question** (checked `environmental-data.gs`'s `doGet` — it never returns 404 from script logic, so this is an Apps-Script-infrastructure-level failure, not a code-level miss) — tracked on its own as CARD-0306, deliberately not blocking this card's closure since it doesn't bear on whether CARD-0279's fix itself works.

**Deploy claim double-checked directly against the live Node-RED instance, 2026-09-19 (prompted by CARD-0286 turning out to have never actually been deployed despite near-identical "Import/deploy done" framing).** Authenticated to `pi1.local:1880`'s admin API and pulled `/flows` live: the "Environmental Data" tab is still `d15dbc9164b2dce9` (the exact id this card's own Import/deploy note names), 12 nodes, including `Throttle GPS lookups (CARD-0279)`, `Check GPS lookup response (CARD-0279)`, and `Log GPS lookup failure (CARD-0279)` by name. Unlike CARD-0286, this deploy claim holds up under direct verification — no gap found here.

~~**Watch for:** the next real hike's Environmental Data coverage — check its missing-GPS rate against the pre-fix volume trend documented above (a hike with ~30 readings previously implied ~50%+ missing; the fix should bring that down meaningfully). Also grep `/mnt/jctsh-logs/jctsh.log*` for a real `"GPS lookup failed after 3 attempts"` Alert line (from the new `env-data-gps-log-failure` node) — its appearance would confirm the retry-then-log path fires correctly on real data, and its absence on a hike with a low miss rate would just mean the throttle alone was enough that hike. Per CARD-0251's convention, this card stays in Build until this is observed.~~ **RESOLVED 2026-09-19, see above.**

**Related:** CARD-0226 (the reboot loop this was initially, incorrectly, thought to be part of — its own 2026-08-29 replay-interruption finding is the one real exception this card doesn't cover), CARD-0197 (the Correlation Debug diagnostic that made this investigation possible), CARD-0258/CARD-0275/CARD-0276 (this week's other Apps-Script-under-load findings, same underlying flakiness class), CARD-0222 (its diagnosed failure mode, a GPS-lookup burst overwhelming Node-RED, is the exact mechanism this card's throttle/retry/log fix targets — worth revisiting now that this card's fix is confirmed holding), CARD-0306 (the front-porch-temp-sensor 404s that proved this card's retry/log path fires for real — root cause of those specific failures is that card's own open question, not this one's), `core/data-pipeline/environmental-data.flow.json` ("Prepare GPS lookup"/"Throttle GPS lookups"/"GPS lookup"/"Check GPS lookup response" nodes), `core/data-pipeline/environmental-data.gs` (`_gpsLookup`), `Node-RED-workflow.md` (the manual import/deploy convention this fix depends on).

---

