# Runbook -- the environmental Google Sheet stops accepting writes

Written 2026-09-25 after the CARD-0226 incident. Symptoms: node-red Alerts such as
`Environmental Data POSTs failing (...)`, gaps in the porch/patio/hiking-monitor rows,
hike pages built with no environmental data, Apps Script Executions showing `Timed Out`
(360 s) or `Failed` (~93 s / ~187 s).

## 0. Nothing is being lost -- don't rush

- **Node-RED holds readings** (serial queue, one POST in flight, retries every 5 min, alerts at
  most once per 30 min, discards a reading only after 24 h). The queue is **in memory**:
  a redeploy of the Environmental Data tab, or a Node-RED restart, empties it (see section 5).
- The phone apps (GPSLogger, Tasker observations) queue their own posts and retry.
- hiking-monitor and the AQM keep their logs on the device until the *next* run starts
  (CARD-0226), and can re-send them (hiking-monitor: "Replay Hike Log" button in HA; AQM:
  publish anything to `jctsh/components/air-quality-monitor/command/replay` while connected).

## 1. Triage (2 minutes)

| Check | Command / place | Reads as |
|---|---|---|
| Script alive? | `GET <web-app-url>?action=version&key=<key>` | fast (~1 s) but sheet calls hang = the *spreadsheet* is the problem, not the script/network |
| Sheet call | `action=export` of a tiny tab (e.g. `Scat Detections`) | 93 s error page or timeout = Spreadsheet service unresponsive on this document |
| Google incident? | `https://www.google.com/appsstatus/dashboard/incidents.json` (Sheets / Apps Script entries) | an open incident = wait, don't migrate |
| Node-RED queue | Node-RED Admin API `GET /context/node/<POST queue node id>?store=memory` | queued count, oldest reading |

**Do not** spray diagnostic exports/lookups at it. Every call that touches the sheet becomes an
execution that hangs until the 6-minute cap; several of the executions on 2026-09-25 were ours.
Tell any other session to stop probing too. Pause heavy jobs: on the M8,
`sudo systemctl stop hike-izer-daily-refresh.timer` (restart it afterwards -- it is only stopped, not
disabled, but a stopped timer does not fire).

## 2. Find out whether it is the document (10 minutes, from the Apps Script editor)

Run from the editor of the project that owns the web app (the spreadsheet named
`SCRIPTS JCTsh Environmental Data`). `console.log` streams live; the last `BEFORE` without an
`AFTER` is where it stalls. Paste the copy's id where marked (make it first with File -> Make a copy).

```js
function diagSpeed() {
  var COPY_ID = 'PASTE_COPY_ID_HERE';
  function step(label, f) {
    console.log('BEFORE ' + label);
    var t = Date.now();
    try { console.log('AFTER  ' + label + ': ' + (Date.now() - t) + ' ms -> ' + f()); }
    catch (e) { console.log('FAILED ' + label + ' after ' + (Date.now() - t) + ' ms: ' + e); }
  }
  var blank;
  step('create BRAND-NEW blank spreadsheet', function () { blank = SpreadsheetApp.create('diag-blank-delete-me'); return blank.getId(); });
  step('write+read a cell in the blank one', function () { var s = blank.getSheets()[0]; s.getRange('A1').setValue('x'); SpreadsheetApp.flush(); return s.getRange('A1').getValue(); });
  step('trash the blank one', function () { DriveApp.getFileById(blank.getId()).setTrashed(true); return 'ok'; });
  var copy;
  step('openById(copy)', function () { copy = SpreadsheetApp.openById(COPY_ID); return copy.getName(); });
  step('ORIGINAL getSheetByName', function () { return !!SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Environmental Data'); });
}
```

| Result | Meaning |
|---|---|
| Blank works, `openById(copy)` and the original hang | **the document's state is the problem** -> section 3 |
| Blank also hangs | Google/account side -> section 4 (waiting is the only fix) |
| Everything is fast in the editor, only the web app fails | redeploy a new *version* of the existing deployment |

## 3. Recovery: move to a fresh spreadsheet (this is what worked on 2026-09-25)

1. Right-click each tab of the sick spreadsheet -> **Copy to -> New spreadsheet** (first tab), then
   **Copy to -> Existing spreadsheet** for the rest. Rename each `Copy of X` back to exactly `X`
   (a leading space, as happened to `Timeline`, creates a second tab). Do this *before* any write can
   reach the new spreadsheet -- the script auto-creates a missing tab, empty.
2. Confirm it opens fast: `SpreadsheetApp.openById('<new id>')` should be ~200 ms.
3. In `environmental-data.gs` set `SPREADSHEET_ID` to the new id, bump `SCRIPT_VERSION`, commit.
4. Paste the file into the Apps Script project **that owns the deployment** (the `SCRIPTS ...`
   spreadsheet's Extensions -> Apps Script), then **Deploy -> Manage deployments -> edit the existing
   deployment -> New version**. Never create a new deployment: it changes the URL, which Node-RED
   (`APPS_SCRIPT_URL`), the M8, GPSLogger and Tasker all hold.
5. Verify: `?action=version` shows the new version; a full `Environmental Data` export returns quickly;
   a 3-reading test lands; run `generation.py --step2 <recent hike stem>` on the M8 and compare its row
   counts with the previous run (2026-09-24: 23 env / 1 obs / 401 GPS / 2 forecast).
6. **Reconcile.** If the old spreadsheet recovered, it may hold rows the new one lacks (readings that
   drained into it before the cutover). Run a dry-run-first function comparing `(timestamp, source)`
   keys and appending only the missing rows in one `setValues` under `LockService.getScriptLock()`;
   compare tab row counts old vs new (`diagCounts`-style) to find every tab that differs.
7. **Backfill gaps** from Home Assistant history for the porch/patio sensors: read the four sensor
   entities' states in effect just after each 5-min slot (the sensors' fixed :50 / :58 second offsets),
   convert pressure psi -> hPa (x 68.9476), publish each as a normal `/data` message; the pipeline
   recomputes dew point / heat index and the (ts, source) dedup prevents duplicates.
8. Restart the M8 timer, delete any stray test rows, record it on the board.

## 4. Google/account side (blank spreadsheets hang too)

Wait. Keep Node-RED's queue running (it probes every 5 min and drains itself). Do not migrate --
a new document would not help. Re-check the incident feed. After recovery, look for gaps
(section 3 steps 6-7).

## 5. Node-RED queue: snapshot before touching the Environmental Data tab

A `PUT /flow/<tab>` or a deploy that modifies a node in that tab **resets the queue's memory**.
If readings are held (`queued` > 0), first read them from
`/context/node/<POST queue node id>?store=memory` (the `st` value: `cur` + `q`), save each item's
`msg.topic` + `msg.payload`, deploy, then re-publish them to their own `jctsh/components/<name>/data`
topics (QoS 1). Re-injection is safe -- Apps Script rejects an exact `(ts, source)` duplicate.
The tab's live id and node ids differ from the repo copy's readable ids; match by node name.

## 6. Facts from 2026-09-25 (so nobody re-derives them)

- Cause of the original failure is **unknown** (Google reported no incident; the document recovered by
  itself hours later; it was only 1.7 MB / ~33k rows x 26 cols; formula View tabs and sorting were ruled
  out). Only the *document* was affected -- `openById` on it and on a plain copy hung, while a new
  spreadsheet, and a copy made with tab-level **Copy to**, opened in ~200 ms.
- Apps Script spreadsheet calls fail at ~93 s each (two in a row = ~187 s), the execution cap is 360 s.
- Write path: the Environmental Data branch of `doPost` takes `LockService`, scans only the last 2000
  rows for duplicates (assumes new rows are at the bottom -- **do not sort the live tab**), then
  `appendRow`. Node-RED never follows Apps Script's redirect with POST; it fetches the Location with GET
  to read the real JSON reply.
- Related: CARD-0226 (incident record), CARD-0337 (keep the sheet small -- optional tidy-up),
  the health-probe card (early warning).
