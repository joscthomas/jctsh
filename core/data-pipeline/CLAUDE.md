# core/data-pipeline — Context

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

