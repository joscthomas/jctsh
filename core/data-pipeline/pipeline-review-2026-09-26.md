# Data Pipeline Review -- 2026-09-26
**Reviewer:** Claude (Claude Code), at JCT's request
**Scope:** Design and implementation of the environmental data pipeline, with emphasis on the Apps Script insert path.
**Files reviewed:** `environmental-data.gs` (`SCRIPT_VERSION` `2026-09-25.5-export-tail-first`), `environmental-data.flow.json`, `README.md`, `JCTsh-Environmental-Data-Architecture.md` (v1.6), `RUNBOOK-sheets-outage.md`
**Status:** Findings only -- no code or docs were changed.

---

## Summary

The design is sound for a home project, and the recent fixes (CARD-0215, CARD-0226, CARD-0243, CARD-0338) were real improvements:

- **Bad data is rejected at the door.** Range checks and duplicate rejection happen before the row is written, not cleaned up afterwards.
- **Retries are safe end to end.** Every writer can resend because the script answers `duplicate` instead of writing twice.
- **Node-RED sends one POST at a time and holds readings through an outage.** It handles the Apps Script redirect correctly and strips the key from logged URLs.
- **It can be checked and recovered.** `?action=version` confirms which script is live, `?action=health` warns early, and the runbook covers a Sheets outage.

The remaining problems fall into two groups:

1. The GPS and Hiking Observations paths never received the lock-and-scan-window fix that Environmental Data got in CARD-0226.
2. The storage layer, one Google Sheet as the permanent record, has already failed once (2026-09-25), and Node-RED's buffer against that failure lives only in memory.

---

## Findings

Ranked most serious first. Line numbers refer to `environmental-data.gs` unless noted.

### 1. GPS and observation writes have no lock, so duplicates can still get in

| Path | Lines | Check-then-write | Lock |
|---|---|---|---|
| `doGet` `action=gps` | 1309-1322 | yes | **no** |
| `doPost` `hiking-observations` | 131-145 | yes | **no** |
| `doPost` Environmental Data | 436-488 | yes | yes |
| `doPost` wildlife / cost / scat | 170-244, 251-316, 325-377 | yes | yes |

Without a lock, two executions can both find no existing row and both append. This is the same race that CARD-0226 found on Environmental Data, where a 121-reading replay landed only about 20% of its rows.

The scenario that triggers it is the one CARD-0243 was about. GPSLogger retries when Apps Script is slow, and a slow original request is exactly when the retry overlaps it. The duplicate check then does nothing.

**Fix:** wrap each check-and-append in `LockService.getScriptLock()`, with `SpreadsheetApp.flush()` before releasing, as the other branches already do. Keep the Open-Meteo forecast call (`_maybeCaptureHikeStartForecast`) and `_relayLog` **outside** the lock, because both make network calls.

### 2. Scat and wildlife re-runs are silently dropped

The scat branch comment (lines 342-349) says a hike has one canonical count per species, with the most recent processing winning, as in `scat_life_list.py`'s `update_from_hike()`. The code does the opposite. It keeps the first row written and answers `duplicate` to every later one. Wildlife (lines 213-231) works the same way.

**Effect:** when a hike is re-processed with a corrected count or confidence, the sheet keeps the stale value, and the client sees `duplicate` and treats it as success.

**Fix:** when the key matches, overwrite that row in place (the loop already knows its index), and return a new `updated` status. Node-RED's "Check response" node and the hike-izer clients then need to treat `updated` as success.

### 3. Every GPS point does several full-sheet scans

Per GPS point (every ~30 s while hiking):

- **Duplicate check:** reads the full timestamp column of `GPS Track` (line 1310).
- **Session-gap check:** reads the full timestamp column again (line 953).
- **Two appends:** one to `GPS Track` and one to `Correlation Debug` (line 1325).

Per hiking-monitor reading without coordinates (Node-RED `action=lookup`, bursts of 100+ on replay):

- **`_gpsLookup`:** reads every row and every column of `GPS Track` with `getDataRange()` (line 856).
- **On a miss:** appends to `Correlation Debug` (line 870).

Environmental Data now scans only its newest 2,000 rows (`DEDUP_WINDOW_ROWS`). `GPS Track`, `Hiking Observations`, `Wildlife Detections`, `Scat Detections` and `Hike-izer Costs` still scan every row, so every write gets slower as the sheets grow. `Correlation Debug` gains a row for every GPS point and every lookup miss, is never trimmed, and was meant as a temporary CARD-0197 diagnostic.

**Fixes:**
- Limit the duplicate check and session-gap check to a recent window. GPS rows can arrive out of order (CARD-0245), so the window has to be generous, but it can still be bounded (for example, the newest 5,000 rows).
- In `_gpsLookup`, read only columns A-C, not `getDataRange()`.
- Stop logging `gps_append` to `Correlation Debug`, or remove the tab if CARD-0197 is closed.
- Longer term: have Node-RED fetch the hike's GPS range once per replay batch (`action=export&sheet=GPS Track&start=..&end=..`) and match readings to GPS points locally, instead of making one lookup call per reading.

### 4. The duplicate check may miss duplicates

The Environmental Data, GPS and observation checks compare timestamps as **strings**:

```js
existingTs = (existingTs instanceof Date) ? existingTs.toISOString() : String(existingTs);
if (existingTs === tsStr ...)
```

If Sheets stores an incoming ISO string as a date, reading it back produces `...:00.000Z`. An incoming `...:00Z` (no milliseconds) then doesn't match, and the duplicate is written. **Not verified live**: whether Sheets auto-converts these strings depends on the exact format each producer sends.

**Fix:** compare the numeric time on both sides (`new Date(x).getTime()`), which ignores both formatting differences and date-typed cells.

### 5. Storage is the single point of failure

- **The permanent record is one Google Sheet,** and on 2026-09-25 it became unopenable from Apps Script because of the document's internal state, not its data. `SPREADSHEET_ID` now points at a fresh copy, but nothing prevents a repeat.
- **Node-RED's POST queue is in memory.** `RUNBOOK-sheets-outage.md` §0 says so: a Node-RED restart or a redeploy of the Environmental Data tab during an outage loses every held reading.
- **Environmental Data keeps growing.** It is about 33k rows × 26 columns today, adding about 350 rows a day plus each hike's replay, and exports were already slow enough to need CARD-0337.

**Fixes, cheapest first:**
1. Keep the POST queue in a file-backed context store (`contextStorage` in `core/node-red/settings.js`) so it survives a restart.
2. Before posting, have Node-RED append every reading to a local log on the Pi (a JSONL file or SQLite). The Pi then holds a copy that doesn't depend on Google, and any gap can be backfilled from it.
3. Start a new Environmental Data tab or workbook each year, keeping the current one small. `action=export` would need to know which tab covers a given date range.

### 6. Smaller issues

- **No validation on `action=gps` coordinates** (lines 1274-1277). A missing or garbled `lat`/`lon` becomes `NaN`, which is written to the sheet and passed to Open-Meteo. That produces a "Forecast capture failed" alert instead of rejecting the point.
- **`setNumberFormat('B:B')` runs on every write** (lines 200, 267, 340, 986). Once at sheet creation is enough; the apostrophe prefix already covers existing cells.
- **The comments describe `flush()` inside the lock as "harmless" and "not the actual fix"** (lines 158-169, 238-240). With the lock-guarded duplicate check, flushing before releasing the lock is what guarantees the next execution sees the row. Don't remove it; the comments should say why it's needed.
- **Hiking observation timestamps in milliseconds are stored as-is.** The regex `/^\d{1,10}$/` (line 115) only converts epoch seconds; a 13-digit millisecond value is written raw. The GPS path (line 1288) handles both.
- **The tail-first export comment overstates its safety** (lines 1114-1123). It checks only three rows (the first row, the row just before the tail, and the tail's oldest). It is safe as long as rows are appended in time order, which the code already assumes; it isn't strictly "provable."
- **Keys travel in the URL query string** (`?key=`, and `?key=` on the `_relayLog` call). Apps Script web apps can't read request headers, so the choice is limited, but `doPost` could take the key from the JSON body so it stays out of URL logs. Node-RED already strips URLs from its alert text.

### 7. Maintainability

- **`doPost` has four near-identical branches** (wildlife, cost, scat, environmental), each with its own lock, self-provisioning, text-column format, key scan, append and `flush()`. A table-driven helper would replace them. Each sheet would get one entry: name, header, text columns, duplicate key, scan window, and whether a match is skipped or updated. That would also make findings 1-3 a one-place fix.
- **The JSON response code is repeated about 25 times.** A `_json(obj)` helper would remove that repetition.
- **About half the file is incident history.** The long CARD narratives belong in `card-archive.md`. The data-pipeline `CLAUDE.md` is still an empty stub, and it is the intended home for the rules that still apply, for example:
  - Do not sort the live tabs (the export and the duplicate window both assume rows are in time order).
  - Keep `flush()` inside the lock.
  - Force text format on hike-file-stem and date columns so Sheets doesn't convert them to dates.
  - Redeploy after every paste, and confirm with `?action=version`.

---

## Documentation drift

`README.md` and `JCTsh-Environmental-Data-Architecture.md` v1.6 were reconciled against the script on 2026-09-22 (CARD-0291), but they have fallen behind since. Neither mentions:

| Missing from the docs | Where it lives in code |
|---|---|
| `Scat Detections` sheet and the `scat-detection` route | lines 319-378 |
| `Hike-izer Costs` sheet and the `hike-izer-cost` route | lines 246-317 |
| `action=health` probe | lines 1355-1366 |
| Write locking (`LockService`) and the 2,000-row duplicate window | lines 433-488 |
| Node-RED serial POST queue (retry, outage hold, 24 h discard) | `environmental-data.flow.json`, "POST queue" node |
| Opening the spreadsheet by `SPREADSHEET_ID` after the 2026-09-25 outage | lines 19-30 |
| `action=export` parameters `full`, `tail`, `timing` | lines 1351-1353 |

Two statements are also wrong:
- The architecture doc's "Handler Responsibilities" says Node-RED routes `hiking-observations` to the Observations sheet. The phone posts those directly to the Apps Script, and Node-RED never sees them.
- The `_exportSheet` header comment still says `Timeline` column A is "Arizona-local"; since CARD-0099 it is each row's own local time.

---

## Recommended order

| # | Change | Effort | Addresses |
|---|---|---|---|
| 1 | Lock the GPS and observation check-and-append | Small | Finding 1 |
| 2 | Update the matching row instead of dropping it for wildlife and scat | Small | Finding 2 |
| 3 | Compare timestamps numerically in every duplicate check | Small | Finding 4 |
| 4 | File-backed context store for the Node-RED POST queue | Small | Finding 5 |
| 5 | Scan windows on GPS / observations / detections; lookup reads A-C only; stop `gps_append` debug rows | Medium | Finding 3 |
| 6 | Bring README and the architecture doc up to date | Medium | Documentation drift |
| 7 | Local reading log on the Pi | Medium | Finding 5 |
| 8 | Table-driven write helper; move history to `card-archive.md`; fill in the data-pipeline `CLAUDE.md` | Medium | Finding 7 |
| 9 | Yearly tab or workbook rollover for Environmental Data | Larger | Finding 5 |

Items 1-3 are all in `environmental-data.gs` and can ship in one redeploy. Bump `SCRIPT_VERSION` and confirm it with `?action=version`.
