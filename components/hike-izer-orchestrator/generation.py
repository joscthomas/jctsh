#!/usr/bin/env python
"""
Hike-izer generation pipeline (CARD-0086 stage 2; unified into one process
by CARD-0348, 2026-09-27 -- Joseph: "the process should be identical for
both the initial and the 1700 run").

One generation pass (generate(), below), called identically every time:
right after a real hike (the webhook-triggered first pass), automatically
again that evening (run_daily_refresh_and_log, the systemd-timer-fired
catch-up pass, CARD-0214), and on demand (run_step2_and_log, a forced
regeneration -- the JCTsh Menu's "Run Step 2" entry, kept under that name
for Tasker's sake, not because the underlying process still differs).
generate() always re-fetches Environmental Data/Hiking Observations/GPS
fresh from the Apps Script (CARD-0214: late-arriving Sheet data is exactly
what a later pass exists to catch) and re-checks Immich for photos
(captioning only genuinely new ones); it skips only the place-naming
(CARD-0311) Overpass lookup once a prior pass already got a real answer
for this hike (see the places-state cache in generate() itself). Safe to
call any number of times.

_bootstrap_from_webhook() is the one genuinely first-pass-only piece: it
parses the webhook payload, detects the session window, allocates the
hike's file stem, decides whether a real hike was even confirmed, and
writes its first meta.json -- there's no way to make that part identical
to a later re-run of an already-published hike, since a later run starts
from a file stem that already exists.

Determines "today" from the webhook payload's own local_datetime (never
Arizona-hardcoded) -- a hike can happen anywhere Joseph is carrying his
phone. The daily catch-up pass follows the same discipline: it finds hikes
to refresh by file recency, not by computing "today" against the M8
server's own fixed TZ -- see _stems_recently_published.

CARD-0348 also retired the narrative-generation pipeline (narrative.py,
place_context.py's Claude+web_search research layers, the --narrative
flag) -- opt-in-only from the start (CARD-0123) and Joseph won't use it
again. Every published page is now the page that used to require asking
for "the rich version."
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta, timezone

import birdnet
import cost_tracking
import ha_notify
import mqtt_log
import photo_captions
import hike_places
import templating
import sheet_health
import wildlife_life_list

SRV_DIR = "/srv/hike-izer"
# CARD-0112: hike_data.json (raw GPS trackpoints, full Environmental Data)
# reveals far more than the curated HTML summary -- notably the exact home
# address, via every hike's own start/end coordinates -- so it's persisted
# here instead, a directory never mounted into the `web` service at all,
# rather than relying on a Caddyfile exclusion rule for every internal file.
PRIVATE_DIR = "/srv/hike-izer-private"
FETCH_DATA_SCRIPT = "/app/fetch_hike_data.py"
FETCH_PHOTOS_SCRIPT = "/app/fetch_hike_photos.py"
BUILD_CALENDAR_SCRIPT = "/app/build_calendar_index.py"
BUILD_WILDLIFE_SCRIPT = "/app/build_wildlife_index.py"
BUILD_BATTERY_TREND_SCRIPT = "/app/build_battery_trend_index.py"
# CARD-0174: build_wildlife_index.py used to be pure computation (fast,
# no network) -- the 30s timeout below was generous for that. It now does
# one live Xeno-canto lookup per species in the life list (cache misses
# only; hits are a local JSON read). Real failure hit live 2026-08-16
# regenerating the 8/15 hike, the very first run against a life list with
# ~50 species and an empty cache -- every single one was a cache miss,
# and 30s wasn't enough. Each xeno_canto._query() call has its own 15s
# cap, so this is a generous ceiling for a full cold-cache run across the
# whole life list, not a per-species budget -- normal runs after the
# first (cache mostly warm) finish in a few seconds.
WILDLIFE_INDEX_TIMEOUT = 300

# CARD-0258: a transient failure (e.g. the whole-day session probe hanging
# on a slow Apps Script call) used to go straight to an Alert + push
# notification on the very first failure -- confirmed 2026-09-10 to be a
# one-off, since an identical retry an hour later succeeded cleanly with no
# code change. Retrying automatically before bothering Joseph avoids that
# false alarm; the cap still surfaces a real, persistent failure rather than
# retrying forever silently. 5 total attempts (1 initial + 4 retries) at
# 15-minute spacing = a 1-hour window before giving up.
GENERATION_MAX_ATTEMPTS = 5
GENERATION_RETRY_INTERVAL_SEC = 15 * 60

# CARD-0113: the automatic path's own webhook payload already carries the
# session's exact start/end (startedtimestamp + duration), unlike the
# interactive Skill flow which only ever knows which calendar day to
# summarize. Padding covers Environmental Data readings or voice
# observations landing a few minutes outside GPSLogger's own reported
# bounds -- not a guess at how imprecise those bounds are, just slack for
# ordinary clock/logging jitter between independent devices.
SESSION_QUERY_PADDING = timedelta(minutes=10)

# CARD-0120: how close a gap-detected session's own end time must be to the
# webhook's local_datetime (the stop event's "right now") to be trusted as
# *this* hike, not some other same-day hike. Wider than the 10-minute gap
# threshold _gps_sessions itself splits on (covers a stop broadcast firing a
# few minutes after the last GPS point, e.g. a brief stationary pause before
# GPSLogger's own stop-detection trips), but far tighter than the gap between
# two genuinely separate same-day hikes, which real traces (2026-07-29) show
# are hours apart, not minutes.
SESSION_MATCH_TOLERANCE = timedelta(minutes=15)


def _env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} not set in environment")
    return value


def _post_wildlife_detection(row, file_stem):
    """CARD-0229, cut over to data-pipeline-api CARD-0349 Phase 2: archives
    one species-per-hike row via the new gateway's explicit /wildlife-detection
    route (no more hidden "component" key -- Phase 1's own redesign decision,
    applied here too). Direct HTTP, not MQTT -- no fan-out need, same fixed
    one-producer-one-consumer shape GPS Track/Hiking Observations already
    use. Raises on failure; caller decides how to handle it."""
    payload = {
        "ts": row["first_timestamp"],
        "hike_file_stem": file_stem,
        "common_name": row["common_name"],
        "scientific_name": row["scientific_name"],
        "count": row["count"],
        "best_confidence": row["best_confidence"],
        # CARD-0235: birdnet.py's own per-detection GPS (when the export
        # has it) -- None on older exports, same as every other optional
        # field this pipeline already sends.
        "lat": row.get("lat"),
        "lon": row.get("lon"),
    }
    url = _env("DATA_PIPELINE_URL") + "/wildlife-detection?key=" + _env("DATA_PIPELINE_KEY")
    req = urllib.request.Request(
        url, method="POST", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "jctsh-hike-izer/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read())
    # CARD-0276: "duplicate" (the gateway's own dedup guard on
    # (hike_file_stem, scientific_name)) counts as success, not failure --
    # this is what makes _archive_new_wildlife_detections' per-row retry
    # actually safe. Without server-side dedup, a client-side retry after
    # a read timeout (the write can commit before the response makes it
    # back) silently double-posted real rows -- confirmed live 2026-09-17
    # (2x Verdin, 3x House Finch on one hike) before this guard existed.
    if result.get("status") not in ("ok", "duplicate"):
        raise RuntimeError(f"data-pipeline-api rejected wildlife-detection POST: {result}")


def _post_hike_cost(file_stem, run_type, tracker):
    """CARD-0270: posts one generation run's real API cost to the
    dedicated "Hike-izer Costs" sheet, via the same Apps Script doPost
    every other component already posts to -- structured and queryable
    (a plain SUM formula for "total cost to date"), instead of a substring
    buried in a free-text notification message. Same dedup-on-the-server
    pattern as wildlife-detection: "duplicate" (the (file_stem, run_type)
    guard) counts as success here too, protecting against a retried
    generation run (GENERATION_MAX_ATTEMPTS) double-posting the same run's
    cost. Never raises to the caller -- see the three call sites below,
    which treat a failure here as non-fatal telemetry, not a reason to
    fail an otherwise-successful publish."""
    payload = {
        "component": "hike-izer-cost",
        "ts": datetime.now(timezone.utc).isoformat(),
        "file_stem": file_stem,
        "run_type": run_type,
        "dollars": round(tracker.dollars, 4),
        "calls": tracker.calls,
        "input_tokens": tracker.input_tokens,
        "output_tokens": tracker.output_tokens,
        "web_searches": tracker.web_searches,
    }
    url = _env("APPS_SCRIPT_URL") + "?key=" + _env("APPS_SCRIPT_KEY")
    req = urllib.request.Request(
        url, method="POST", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read())
    if result.get("status") not in ("ok", "duplicate"):
        raise RuntimeError(f"Apps Script rejected hike-izer-cost POST: {result}")


def _post_hike_cost_and_log(file_stem, run_type, tracker):
    """Wraps _post_hike_cost() so a Sheet-write failure (Apps Script
    flakiness, per CARD-0275/0276's own established pattern) can never
    turn an otherwise-successful hike-summary publish into a failure --
    this is enrichment/telemetry, not core functionality, same
    graceful-degradation principle place_context.py's own module docstring
    states for its layer. Logs an Alert so a persistent gap is still
    visible on the dashboard, rather than failing silently."""
    try:
        _post_hike_cost(file_stem, run_type, tracker)
    except Exception as e:
        mqtt_log.publish_log(
            "Alert",
            f"Failed to post hike-izer-cost for {file_stem} ({run_type}) to Sheets: {e}",
        )


WILDLIFE_ARCHIVE_RETRY_ATTEMPTS = 3

WILDLIFE_ARCHIVE_RETRY_DELAY_SEC = 10


def _archive_new_wildlife_detections(file_stem, birdnet_rows):
    """CARD-0229: best-effort archive of this hike's species to Sheets --
    never blocks page publication (an Apps Script outage shouldn't break
    basic hike-page generation), logged both ways (a System confirmation
    on success, matching Node-RED's own convention of confirming every
    successful Sheets append, not just an Alert on failure).

    Only archives species not already recorded (and actually archived --
    see wildlife_life_list's own "archived" flag, CARD-0276) for this
    file_stem, checked against the local life-list cache *before*
    wildlife_life_list.update_from_hike() (called right after this, by
    both callers) mutates it -- generate() can re-run for the same hike
    on every CARD-0214 daily catch-up pass, and a plain unconditional
    appendRow would duplicate rows on each one. The local cache already
    tracks "which species were recorded on which hikes" for exactly this
    idempotency reason, so this reuses it rather than adding a second,
    separate dedup scan on the Apps Script side.

    CARD-0276: real data loss (23 of 27 species across two real hikes,
    2026-09-15/17) was found from this loop's original all-or-nothing
    shape -- one species' POST failing (a transient Apps Script 404 or
    timeout) raised past the whole for-loop, so every row after the
    failing one was never even attempted, and the exception was caught
    one level up with no per-row detail. Worse, the caller's own
    update_from_hike() call ran unconditionally right after regardless of
    what actually reached Sheets, so a failed row was marked done in the
    local cache and never retried by any later pass. Fixed here: each
    row gets its own bounded retry, a genuine failure is named by species
    (not just the first exception hit), and only rows that actually
    succeed are reported back to the caller for update_from_hike() to
    mark archived -- everything else stays retry-eligible."""
    if not birdnet_rows:
        return set()

    life_list = wildlife_life_list.load()
    new_rows = [
        row for row in birdnet_rows
        if not any(
            h["file_stem"] == file_stem and h.get("archived", True)
            for h in life_list.get(row["scientific_name"], {}).get("hikes", [])
        )
    ]
    if not new_rows:
        return set()

    archived_species = set()
    failed = []
    for row in new_rows:
        last_error = None
        for attempt in range(1, WILDLIFE_ARCHIVE_RETRY_ATTEMPTS + 1):
            try:
                _post_wildlife_detection(row, file_stem)
                last_error = None
                break
            except Exception as e:
                last_error = e
                if attempt < WILDLIFE_ARCHIVE_RETRY_ATTEMPTS:
                    time.sleep(WILDLIFE_ARCHIVE_RETRY_DELAY_SEC)
        if last_error is None:
            archived_species.add(row["scientific_name"])
        else:
            failed.append((row["common_name"], last_error))

    if archived_species:
        mqtt_log.publish_log(
            "System",
            f"Archived {len(archived_species)} species detection(s) for {file_stem} to Wildlife Detections.",
        )
    if failed:
        detail = "; ".join(f"{name}: {err}" for name, err in failed)
        mqtt_log.publish_log(
            "Alert",
            f"Failed to archive {len(failed)} species detection(s) for {file_stem} to Sheets "
            f"after {WILDLIFE_ARCHIVE_RETRY_ATTEMPTS} attempts each: {detail}",
        )
    return archived_species


def _log_birdnet_parse_outcome(staging_dir, file_stem, birdnet_rows):
    """CARD-0229 (Finding #1): birdnet.py's own parse functions silently
    swallow a corrupted/unreadable export (_load_export()'s broad except
    clause) and just return no detections -- indistinguishable on the
    published page from a hike where no birds were genuinely heard. Logs
    only the case actually worth a human's attention: a file WAS staged
    but produced zero detections. No staged file at all is the common,
    unremarkable case in step 1 and stays quiet, same as today."""
    if birdnet_rows or not birdnet.has_staged_export(staging_dir):
        return
    mqtt_log.publish_log(
        "Alert",
        f"BirdNET export staged for {file_stem} but parsing produced zero detections -- "
        f"possibly a corrupted/truncated export, possibly a genuinely birdless hike.",
    )


def _hike_location_hint(hike_data):
    """A plain-language anchor for photo_captions.py's vision prompt to weigh
    species plausibility against when captioning wildlife or wildlife sign
    (kept from CARD-0308 after the structured scat feature was removed --
    CARD-0336), built from
    this hike's own first GPS point (place_context.py's own
    _first_gps_point() pattern -- not imported from there since it's a
    3-line dict lookup, not worth a cross-module dependency for). Raw
    coordinates only, deliberately no Nominatim reverse-geocoding call --
    step 1 doesn't otherwise touch place_context.py at all, and Claude's
    vision call already reasons fine about species ranges from a lat/lon
    pair alone. None if the hike has no GPS track yet (step 1, right after
    a hike start, before any points have logged)."""
    gps_rows = hike_data.get("gps_track") or []
    if not gps_rows:
        return None
    sorted_rows = sorted(gps_rows, key=lambda r: r.get("timestamp") or "")
    point = sorted_rows[0]
    lat, lon = point.get("lat"), point.get("lon")
    if lat is None or lon is None:
        return None
    return f"{lat:.4f}, {lon:.4f}"


def _wildlife_index_cmd():
    # CARD-0174: --xeno-canto-key is optional, unlike THUNDERFOREST_API_KEY
    # above -- deliberately soft (os.environ.get, not _env()) so the
    # pipeline keeps working with the speaker icon simply absent until
    # XENO_CANTO_API_KEY is actually deployed to this host's environment.
    cmd = [sys.executable, BUILD_WILDLIFE_SCRIPT,
           "--life-list", wildlife_life_list.LIFE_LIST_PATH, "--srv-dir", SRV_DIR]
    xeno_canto_key = os.environ.get("XENO_CANTO_API_KEY")
    if xeno_canto_key:
        cmd += ["--xeno-canto-key", xeno_canto_key]
    return cmd


def _local_date_and_offset(local_datetime):
    # e.g. "2026-07-24T17:25:14-07:00" -> ("2026-07-24", "-07:00")
    date_str = local_datetime[:10]
    offset_str = local_datetime[-6:]
    if offset_str[0] not in "+-" or ":" not in offset_str:
        raise ValueError(f"Unexpected local_datetime format (no parseable UTC offset): {local_datetime!r}")
    return date_str, offset_str


def _session_query_window_from_payload(payload, date_str, offset_str):
    """CARD-0113's original approach, now used only as a defensive fallback
    (see _detect_session_window): bound the query to GPSLogger's own
    self-reported session start/end (startedtimestamp + local_datetime, from
    the webhook payload) plus SESSION_QUERY_PADDING. Falls back further, to
    the full calendar day, if the payload is missing the fields this needs
    (defensive, not expected in practice -- every real 'stopped' payload
    observed so far carries both)."""
    try:
        session_end_utc = datetime.fromisoformat(payload["local_datetime"]).astimezone(timezone.utc)
        session_start_utc = datetime.fromtimestamp(
            int(payload["startedtimestamp"]) / 1000, tz=timezone.utc
        )
    except (KeyError, ValueError, TypeError) as e:
        print(
            f"_session_query_window_from_payload: payload missing usable session bounds ({e}) "
            f"-- falling back to full-day query window",
            file=sys.stderr,
        )
        return f"{date_str}T00:00:00{offset_str}", f"{date_str}T23:59:59{offset_str}"

    start_utc = session_start_utc - SESSION_QUERY_PADDING
    end_utc = session_end_utc + SESSION_QUERY_PADDING
    return start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _detect_session_window(payload, date_str, offset_str):
    """CARD-0120: GPSLogger's own startedtimestamp (carried in the 'stopped'
    payload) isn't reliable -- it can be reset by a spurious extra 'started'
    broadcast mid-hike. Confirmed live 2026-07-30: GPSLogger sent a second
    'started' event for the same file, one second before 'stopped', which
    silently shifted startedtimestamp 36 minutes late and truncated that
    day's report down to its last 10 minutes (0.2 mi reported vs. a real
    1.33 mi). Trusting any GPSLogger self-reported timestamp for session
    bounds is what broke, so this doesn't -- it derives the real bounds from
    the GPS trace itself, the same gap-based session detection
    fetch_hike_data.py already does and CARD-0101/CARD-0113 already proved
    out.

    Probes the whole local day, then picks whichever detected is_hike
    session's own end is closest to the webhook's local_datetime (the one
    genuinely trustworthy signal in the payload -- "a hike just ended, right
    now"). Falls back to _session_query_window_from_payload if no confirmed
    session is found within SESSION_MATCH_TOLERANCE of the stop time
    (defensive, not expected in practice)."""
    day_start_iso = f"{date_str}T00:00:00{offset_str}"
    day_end_iso = f"{date_str}T23:59:59{offset_str}"

    fd, probe_path = tempfile.mkstemp(suffix="_session_probe.json")
    os.close(fd)
    try:
        subprocess.run(
            [
                sys.executable, FETCH_DATA_SCRIPT,
                "--start", day_start_iso, "--end", day_end_iso,
                "--data-pipeline-url", _env("DATA_PIPELINE_URL"), "--data-pipeline-key", _env("DATA_PIPELINE_KEY"),
                "--out", probe_path,
            ],
            # CARD-0135: fetch_hike_data.py's own fetch_sheet() now retries
            # transient failures internally (up to 3 attempts, 2s/4s
            # backoff, per sheet), so a run touching all 4 sheets can
            # legitimately take much longer worst-case than before that
            # existed -- confirmed live 2026-08-03, a run hit the old 120s
            # ceiling on a day Apps Script needed a retry on nearly every
            # sheet. 240s covers that worst case with real headroom.
            check=True, timeout=240,
        )
        with open(probe_path, "r", encoding="utf-8") as f:
            probe_data = json.load(f)
    finally:
        os.remove(probe_path)

    try:
        stop_utc = datetime.fromisoformat(payload["local_datetime"]).astimezone(timezone.utc)
    except (KeyError, ValueError, TypeError):
        stop_utc = None

    matched = None
    if stop_utc is not None:
        candidates = [s for s in probe_data["coverage"]["gps_track"]["sessions"] if s["is_hike"]]

        def _end_delta_sec(s):
            end_utc = datetime.fromisoformat(s["end"].replace("Z", "+00:00"))
            return abs((end_utc - stop_utc).total_seconds())

        if candidates:
            best = min(candidates, key=_end_delta_sec)
            if _end_delta_sec(best) <= SESSION_MATCH_TOLERANCE.total_seconds():
                matched = best

    if matched is None:
        print(
            "_detect_session_window: no confirmed GPS session found near the webhook's "
            "stop time -- falling back to startedtimestamp-based window",
            file=sys.stderr,
        )
        return _session_query_window_from_payload(payload, date_str, offset_str)

    start_utc = datetime.fromisoformat(matched["start"].replace("Z", "+00:00")) - SESSION_QUERY_PADDING
    end_utc = datetime.fromisoformat(matched["end"].replace("Z", "+00:00")) + SESSION_QUERY_PADDING
    return start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _next_file_stem(date_str):
    """CARD-0113: a day can now produce more than one hike-summary -- the
    first keeps the plain '<date>' stem (no rename of existing files),
    each subsequent one gets '<date>-2', '<date>-3', etc."""
    stem = date_str
    n = 1
    while os.path.exists(os.path.join(SRV_DIR, f"{stem}_hike-summary.html")):
        n += 1
        stem = f"{date_str}-{n}"
    return stem


def _date_str_from_stem(file_stem):
    # '2026-07-29' -> '2026-07-29'; '2026-07-29-2' -> '2026-07-29'
    return file_stem[:10]


def latest_file_stem():
    """CARD-0122: resolve which hike a staged file belongs to when the
    source (a phone Share sheet, via the /webhook/stage-file endpoint) has
    no notion of file_stem at all -- that's a server-side idea (CARD-0113).
    Deliberately NOT 'today's date' on the M8's own clock: a hike's real
    local date comes from GPSLogger's own local_datetime, which can differ
    from the M8's fixed server TZ (America/Phoenix) whenever Joseph is
    hiking somewhere else (e.g. Eastern time, as this week) -- there's no
    single safe definition of "today" to anchor a date-based lookup on.
    Picking whichever *_hike-summary.html has the most recent mtime instead
    sidesteps that entirely: a file gets shared within minutes of the hike
    it belongs to ending, so its page is reliably the most recently
    published one. Returns None if no hike has ever been published."""
    candidates = glob.glob(os.path.join(SRV_DIR, "*_hike-summary.html"))
    if not candidates:
        return None
    latest = max(candidates, key=os.path.getmtime)
    return os.path.basename(latest)[: -len("_hike-summary.html")]


# CARD-0214: how far back the daily refresh pass looks for hikes to re-run
# run_step2 against. Comfortably wider than the ~24h gap between one daily
# cron firing and the next, so a hike published right before or right after
# a firing still gets exactly one refresh pass either way.
DAILY_REFRESH_LOOKBACK_HOURS = 30
# CARD-0338: the unattended refresh re-checks the Sheet's health this many times,
# this far apart, before giving up for the day. Skipping outright would be unsafe:
# the lookback above is only 30 h, so a hike published in the morning is out of
# range of the *next* day's 17:00 run and would never be refreshed.
SHEET_HEALTH_CHECKS = 3
SHEET_HEALTH_RETRY_SEC = 600


def _stems_recently_published(within_hours=DAILY_REFRESH_LOOKBACK_HOURS):
    """CARD-0214: every hike-summary first published within the last
    `within_hours`, by *meta.json's* mtime -- deliberately not the .html
    file's. run_step2 rewrites the .html every single pass (its mtime would
    keep resetting, making a hike look "recently published" forever and
    never age out of the lookback window); meta.json, by contrast, is
    written once by step 1 and never touched again by an ordinary
    run_step2 call (the one exception -- backfilling query_start_iso/
    query_end_iso into a pre-CARD-0214 file -- only ever fires once per
    file, so it doesn't reintroduce the same problem), so its mtime is a
    genuinely stable "first published" signal.

    Deliberately NOT a calendar-date lookup either -- this module's own
    rule (see the file docstring) is that nothing here assumes the M8
    server's fixed TZ (America/Phoenix) is Joseph's current one, since a
    hike can happen anywhere he's carrying his phone. A recency window
    sidesteps needing to know what "today" even means for any given hike,
    the same reasoning latest_file_stem() already uses for a single lookup,
    generalized here to "every recent one." """
    cutoff = time.time() - within_hours * 3600
    candidates = glob.glob(os.path.join(SRV_DIR, "*_hike-summary.meta.json"))
    return sorted(
        os.path.basename(p)[: -len("_hike-summary.meta.json")]
        for p in candidates if os.path.getmtime(p) >= cutoff
    )


# CARD-0135: latest_file_stem()'s mtime lookup can only ever resolve to a
# hike that's already published -- while step 1 (run(), below) is still
# running, nothing has been published yet for the hike currently in
# progress, so a file staged in that window would otherwise silently
# misattribute to the previous hike. This marker names whichever hike run()
# is actively generating (empty/absent the rest of the time).
_IN_PROGRESS_MARKER = os.path.join(PRIVATE_DIR, "in_progress_stem.txt")


def _set_in_progress_stem(file_stem):
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    with open(_IN_PROGRESS_MARKER, "w", encoding="utf-8") as f:
        f.write(file_stem)


def _clear_in_progress_stem():
    try:
        os.remove(_IN_PROGRESS_MARKER)
    except FileNotFoundError:
        pass


def current_or_latest_file_stem():
    """CARD-0135: used by app.py's stage-file webhook instead of calling
    latest_file_stem() directly -- prefers the hike step 1 is actively
    generating (if any) over the mtime-based "most recently published"
    lookup, so a file staged mid-step-1 attaches to the right hike."""
    if os.path.exists(_IN_PROGRESS_MARKER):
        with open(_IN_PROGRESS_MARKER, "r", encoding="utf-8") as f:
            stem = f.read().strip()
        if stem:
            return stem
    return latest_file_stem()


# CARD-0136: BirdNET Live's own share can reach /webhook/stage-file *before*
# the hike-end webhook does (confirmed live 2026-08-03 -- a share landed 27s
# ahead of the "stopped" event for the same hike) -- at that instant nothing
# yet exists to attribute the file to, not even CARD-0135's in-progress
# marker, since no file_stem has been assigned yet. app.py stages a birdnet
# file into one of these (keyed by the file's own local calendar date,
# parsed from a local_datetime the BirdNET AutoShare Tasker profile now
# sends alongside it) instead of guessing at an unrelated already-published
# hike. run() below claims whatever's waiting here once it knows its own
# real file_stem.
_PENDING_BIRDNET_PREFIX = "pending_birdnet_"


def pending_birdnet_dir(date_str):
    return os.path.join(SRV_DIR, f"{_PENDING_BIRDNET_PREFIX}{date_str}")


def _claim_pending_birdnet(date_str, staging_dir):
    pending_dir = pending_birdnet_dir(date_str)
    if not os.path.isdir(pending_dir):
        return
    for name in os.listdir(pending_dir):
        shutil.move(os.path.join(pending_dir, name), os.path.join(staging_dir, name))
    try:
        os.rmdir(pending_dir)
    except OSError:
        pass  # non-empty (unexpected) or a race with another writer -- leave it, not worth failing generation over


def _fetch_hike_data(start_iso, end_iso, hike_data_path):
    """CARD-0214/CARD-0348: extracted so every generate() call -- the first
    pass and every later catch-up pass alike -- issues the identical query,
    not one inline subprocess call duplicated across two separate functions. fetch_hike_data.py is a
    pure, stateless query against data-pipeline-api (CARD-0349: all 5
    tables, as of 2026-09-29) for a fixed window -- safe and correct to
    re-run any number of times; a later call just naturally picks up
    whatever rows have landed since the previous one, no merge logic
    needed on this side."""
    subprocess.run(
        [
            sys.executable, FETCH_DATA_SCRIPT,
            "--start", start_iso, "--end", end_iso,
            "--data-pipeline-url", _env("DATA_PIPELINE_URL"), "--data-pipeline-key", _env("DATA_PIPELINE_KEY"),
            "--out", hike_data_path,
        ],
        # CARD-0135: see _detect_session_window's identical comment -- same
        # retry-latency reasoning applies here.
        check=True, timeout=240,
    )


def _fetch_photos(hike_data_path, photos_dir, file_stem):
    """Shared by step 1 (best-effort attempt) and every later gap-filling
    pass (CARD-0111/CARD-0112/CARD-0214). Returns a manifest dict with at
    least one asset, or None.

    CARD-0214: fetch_hike_photos.py always rewrites manifest.json fresh
    from Immich's current listing (with no captions of its own) -- so on a
    second or later call, any caption a prior pass already paid for is
    recovered from the on-disk manifest before that overwrite and reapplied
    after, keyed by Immich's own stable asset id. photo_captions.caption_photos()
    then only processes assets that still have no 'caption' key -- i.e.
    genuinely new photos -- never redoing an already-paid-for caption.

    CARD-0286: also passes an album name ("Hike <file_stem>") through to
    fetch_hike_photos.py so this hike's photos land in their own Immich
    album -- the same file_stem every other per-hike path (photos_dir
    itself, the published HTML/meta.json) already keys off of, so the
    album name can't drift out of sync with which hike this actually is."""
    existing_manifest_path = os.path.join(photos_dir, "manifest.json")
    prior_captions = {}
    if os.path.exists(existing_manifest_path):
        try:
            with open(existing_manifest_path, "r", encoding="utf-8") as f:
                prior_manifest = json.load(f)
            for asset in prior_manifest.get("assets", []):
                if "caption" in asset:
                    prior_captions[asset["id"]] = (asset["caption"], asset.get("sign_text", ""))
        except (OSError, json.JSONDecodeError):
            pass  # no usable prior manifest -- treat this as a first pass

    try:
        subprocess.run(
            [
                sys.executable, FETCH_PHOTOS_SCRIPT,
                "--data", hike_data_path,
                "--immich-url", _env("IMMICH_URL"), "--immich-key", _env("IMMICH_KEY"),
                "--out-dir", photos_dir,
                "--album-name", f"Hike {file_stem}",
            ],
            check=True, timeout=180,
        )
        with open(existing_manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        for asset in manifest.get("assets", []):
            if asset["id"] in prior_captions:
                asset["caption"], asset["sign_text"] = prior_captions[asset["id"]]
        return manifest if manifest.get("assets") else None
    except subprocess.CalledProcessError as e:
        # Photos are a nice-to-have (CARD-0084) -- never let a photo-fetch
        # failure block the summary itself, same as the interactive Skill's
        # "omit the Photos section" handling for a failed/empty manifest.
        print(f"fetch_hike_photos.py failed ({e}) -- continuing without photos", file=sys.stderr)
        return None


def _read_staging(file_stem):
    """CARD-0112: whatever Joseph has dropped into this hike's staging
    directory (mounted as a Windows drive via SSHFS-Win) -- read here
    instead of relaying file content through chat text. Returns a dict with
    whichever of the known keys were actually found; a key is simply absent
    if that resource hasn't been staged (or doesn't apply to this hike)."""
    staging_dir = os.path.join(SRV_DIR, f"{file_stem}_staging")
    staged = {}
    # CARD-0119: .txt, not .html -- plain text is easier to create/paste an
    # iframe snippet into from Windows than a .html file, which content
    # here still is regardless of the extension on disk.
    gaia_path = os.path.join(staging_dir, "gaia_embed.txt")
    if os.path.exists(gaia_path):
        with open(gaia_path, "r", encoding="utf-8") as f:
            staged["gaia_embed_html"] = f.read()
    # BirdNET Live export(s) (CARD-0080): not a fixed filename like the two
    # keys above -- birdnet.parse_detections() scans this same staging_dir
    # itself for any .zip/.json export, called directly from generate()
    # rather than threaded through this dict.
    return staged


def _apply_observation_overrides(hike_data, file_stem):
    """CARD-0194: apply any manual observation-text corrections (made via
    the live page's hidden edit UI, POSTed to app.py's
    /webhook/edit-observation) on top of the freshly-fetched Sheet data,
    every time this hike gets (re)generated. The Sheet itself is never
    written to -- corrections live in a small per-hike overrides file
    (SRV_DIR, keyed by the observation's own raw timestamp, the same
    stable identifier the live page's data-obs-ts attribute uses), applied
    here as a patch step so a future regeneration doesn't silently discard
    a correction by re-pulling the original mis-transcribed text."""
    overrides_path = os.path.join(SRV_DIR, f"{file_stem}_hike-summary.overrides.json")
    try:
        with open(overrides_path, "r", encoding="utf-8") as f:
            overrides = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return
    if not overrides:
        return
    applied = 0
    for o in hike_data.get("hiking_observations", []):
        ts = o.get("timestamp")
        if ts in overrides:
            o["observation"] = overrides[ts]
            applied += 1
    if applied:
        print(f"Applied {applied} observation override(s) for {file_stem}", flush=True)


def _places_state_path(file_stem):
    return os.path.join(PRIVATE_DIR, f"{file_stem}_places_state.json")


def _load_places_state(file_stem):
    try:
        with open(_places_state_path(file_stem), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _save_places_state(file_stem, state):
    with open(_places_state_path(file_stem), "w", encoding="utf-8") as f:
        json.dump(state, f)


def _bootstrap_from_webhook(payload):
    """Everything genuinely specific to a brand-new hike, triggered by
    GPSLogger's 'stopped' webhook (CARD-0086): parse the payload, detect
    the session window, allocate this hike's own file stem, decide whether
    a real hike was even confirmed, and write its first meta.json + staging
    directory. Returns the new file_stem, or None if no hike was confirmed
    (nothing to generate -- e.g. GPSLogger ran during a car errand).

    Distinct from generate() below on purpose (CARD-0348): a file_stem has
    to exist, with a meta.json describing its query window, before
    generate() has anything to operate on -- there's no way to make this
    part identical between a brand-new hike and a later re-run of one
    that's already published. Once this returns, every later pass over the
    same hike (this same webhook's own first call, the daily catch-up, a
    manual re-run) is the identical generate(file_stem) call."""
    local_datetime = payload.get("local_datetime")
    if not local_datetime:
        raise ValueError("payload missing local_datetime -- cannot determine which day to generate")
    date_str, offset_str = _local_date_and_offset(local_datetime)

    # CARD-0113: query window is scoped to this specific session (not the
    # full calendar day) -- see _detect_session_window for why.
    start_iso, end_iso = _detect_session_window(payload, date_str, offset_str)

    os.makedirs(SRV_DIR, exist_ok=True)
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    # CARD-0113: a day can produce more than one hike-summary -- decide this
    # run's own file stem ('<date>' for the first, '<date>-2' etc. for any
    # later same-day hike) before anything gets written.
    file_stem = _next_file_stem(date_str)

    # CARD-0135: set before any slow work starts, cleared in the finally
    # below regardless of how this run ends -- see current_or_latest_file_stem()
    # for why this needs to exist at all.
    _set_in_progress_stem(file_stem)
    try:
        hike_data_path = os.path.join(PRIVATE_DIR, f"{file_stem}_hike_data.json")
        _fetch_hike_data(start_iso, end_iso, hike_data_path)
        with open(hike_data_path, "r", encoding="utf-8") as f:
            hike_data = json.load(f)

        # CARD-0100: don't publish a live page for a day with no confirmed
        # hike (e.g. GPSLogger left running during a car errand).
        if not hike_data["coverage"]["gps_track"]["hike_confirmed"]:
            print(f"No hike confirmed for {file_stem} -- skipping generation", flush=True)
            mqtt_log.publish_log(
                "System",
                f"GPSLogger stopped, no hike confirmed for {file_stem} -- skipped generation.",
            )
            os.remove(hike_data_path)  # nothing for a later pass to ever reuse for this non-hike
            return None

        # CARD-0112: staging directory created up front so Joseph's
        # SSHFS-Win-mounted drive shows a real folder to drop files into
        # immediately. CARD-0119: chmod explicitly -- a plain os.makedirs()
        # defaults to owner-only write inside this root-run container, and
        # the SSHFS-Win mount connects as `jct`, who could read/traverse but
        # never actually drop a file in via the mount otherwise.
        staging_dir = os.path.join(SRV_DIR, f"{file_stem}_staging")
        os.makedirs(staging_dir, exist_ok=True)
        os.chmod(staging_dir, 0o777)

        # CARD-0136: claim anything the BirdNET stage-file webhook parked
        # for this calendar date before this run's own file_stem existed to
        # attach to. Keyed by date_str, not file_stem, since the pending
        # side can't know yet whether this'll be the day's first hike or a
        # later one.
        _claim_pending_birdnet(date_str, staging_dir)

        confirmed_sessions = [s for s in hike_data["coverage"]["gps_track"]["sessions"] if s["is_hike"]]
        start_ts = min((s["start"] for s in confirmed_sessions), default=None)
        with open(os.path.join(SRV_DIR, f"{file_stem}_hike-summary.meta.json"), "w", encoding="utf-8") as f:
            json.dump({
                "hike_confirmed": True, "offset_str": offset_str, "start_ts": start_ts,
                "query_start_iso": start_iso, "query_end_iso": end_iso,
            }, f)

        return file_stem
    finally:
        _clear_in_progress_stem()


def generate(file_stem):
    """The one, idempotent, safely-repeatable hike-page generation pass
    (CARD-0348) -- called identically whether this is the very first pass
    right after a hike (from the webhook) or a later catch-up pass (the
    daily timer, or a manual re-run). Always re-fetches sensor data and
    photos fresh, since catching whatever's synced since the last pass is
    the whole point of running this more than once; skips only the
    place-naming (CARD-0311) Overpass lookup once a prior pass already got
    a real answer for this hike (see the places-state cache below).
    Everything else is either cheap (local file reads, an idempotent
    photo-caption merge) or needs to run every time by design (the Sheet
    fetch itself)."""
    tracker = cost_tracking.CostTracker()
    date_str = _date_str_from_stem(file_stem)

    meta_path = os.path.join(SRV_DIR, f"{file_stem}_hike-summary.meta.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    offset_str = meta["offset_str"]

    hike_data_path = os.path.join(PRIVATE_DIR, f"{file_stem}_hike_data.json")
    # CARD-0214: re-issue the same query the first pass ran, using its
    # persisted exact window -- picks up anything that's landed in the
    # Sheet since. query_start_iso/query_end_iso won't exist in meta.json
    # for a hike published before this card; fall back to a full local-day
    # window in that case, and backfill meta.json right now so every later
    # pass on this same file uses the tight window.
    if "query_start_iso" not in meta:
        start_iso = f"{date_str}T00:00:00{offset_str}"
        end_iso = f"{date_str}T23:59:59{offset_str}"
        meta["query_start_iso"], meta["query_end_iso"] = start_iso, end_iso
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f)
    else:
        start_iso, end_iso = meta["query_start_iso"], meta["query_end_iso"]
    _fetch_hike_data(start_iso, end_iso, hike_data_path)
    with open(hike_data_path, "r", encoding="utf-8") as f:
        hike_data = json.load(f)
    _apply_observation_overrides(hike_data, file_stem)

    # Photos: merges in whatever a prior pass already downloaded/captioned,
    # only paying to caption genuinely new ones (photo_captions.caption_photos'
    # own job) -- safe and cheap to redo every pass, since Immich's own
    # upload-sync timing is exactly what a later pass exists to catch.
    photos_dir = os.path.join(SRV_DIR, f"{file_stem}_photos")
    photos_manifest = _fetch_photos(hike_data_path, photos_dir, file_stem)
    if photos_manifest:
        photos_manifest = photo_captions.caption_photos(
            photos_manifest, photos_dir, _env("ANTHROPIC_API_KEY"), cost_tracker=tracker,
            location_hint=_hike_location_hint(hike_data),
        )

    staging_dir = os.path.join(SRV_DIR, f"{file_stem}_staging")
    birdnet_rows = birdnet.parse_detections(staging_dir)
    # CARD-0133: per-occurrence view of the same staged export(s), for the
    # Route Map's bird markers.
    birdnet_occurrences = birdnet.parse_occurrences(staging_dir)
    _log_birdnet_parse_outcome(staging_dir, file_stem, birdnet_rows)
    # CARD-0229: must run before update_from_hike() below mutates the local
    # cache -- see that function's own docstring for why.
    archived_species = _archive_new_wildlife_detections(file_stem, birdnet_rows)

    # CARD-0311/CARD-0348: area/trail(s)/trailhead/town, one rate-limited
    # Overpass lookup. Skipped on a later pass once it already got a real
    # answer for this hike (CARD-0348's places-state cache). CARD-0348,
    # 2026-09-27: the Nearby Named Features table this used to run
    # alongside (place_context.py) was retired outright -- across all 10
    # real hikes published before this change it had returned a result
    # exactly once, and that result only duplicated what this lookup
    # already names better (Joseph's call: "the value of nearby features
    # seems dubious... a nearby feature that describes the same thing is
    # not desireable"). One lookup left means nothing to keep in sync
    # against a second one's own success/failure -- no more all-or-nothing
    # tradeoff to make here at all.
    places_state = _load_places_state(file_stem)
    if places_state and places_state.get("ok"):
        places = places_state["places"]
    else:
        places, places_ok = hike_places.gather_hike_places(hike_data)
        _save_places_state(file_stem, {"ok": places_ok, "places": places})

    # CARD-0142: idempotent -- a hike already recorded by a prior pass just
    # re-adds its own file_stem to each species' hikes list rather than
    # duplicating it. Runs BEFORE render_html() below so a brand-new
    # species' own debut hike correctly shows its "NEW" badge (CARD-0176).
    wildlife_life_list.update_from_hike(file_stem, date_str, birdnet_rows, archived_species=archived_species)

    html_text = templating.render_html(
        hike_data, date_str, offset_str, photos_manifest,
        file_stem=file_stem,
        birdnet_rows=birdnet_rows,
        places=places,
        thunderforest_api_key=_env("THUNDERFOREST_API_KEY"),
        birdnet_occurrences=birdnet_occurrences,
        life_list=wildlife_life_list.load(),
        xeno_canto_key=os.environ.get("XENO_CANTO_API_KEY"),
    )

    with open(os.path.join(SRV_DIR, f"{file_stem}_hike-summary.html"), "w", encoding="utf-8") as f:
        f.write(html_text)

    subprocess.run(
        [sys.executable, BUILD_CALENDAR_SCRIPT, "--srv-dir", SRV_DIR],
        check=True, timeout=30,
    )
    if birdnet_rows:
        subprocess.run(_wildlife_index_cmd(), check=True, timeout=WILDLIFE_INDEX_TIMEOUT)
    # CARD-0207: rebuild the battery-trend page unconditionally -- this
    # hike's own hike_data.json (just re-fetched above) always carries
    # stats.battery_window_crossing_min, no optional data source to gate on.
    subprocess.run(
        [sys.executable, BUILD_BATTERY_TREND_SCRIPT, "--srv-dir", SRV_DIR, "--private-dir", PRIVATE_DIR],
        check=True, timeout=30,
    )

    print(f"Generation complete for {file_stem} -- {tracker.summary()}", flush=True)
    return file_stem, tracker


def run_and_log(payload):
    """The webhook's own entry point -- called by app.py on every real
    GPSLogger 'stopped' event. Bootstraps the new hike (see
    _bootstrap_from_webhook), then runs the identical generate() every
    later pass also runs.

    CARD-0258: retries a failure up to GENERATION_MAX_ATTEMPTS times,
    GENERATION_RETRY_INTERVAL_SEC apart, before alerting -- runs in its own
    daemon thread (app.py's _handle_hike_end), so blocking here on
    time.sleep() for up to an hour costs nothing else."""
    for attempt in range(1, GENERATION_MAX_ATTEMPTS + 1):
        try:
            file_stem = _bootstrap_from_webhook(payload)
            if file_stem is None:
                # CARD-0100: no hike confirmed -- _bootstrap_from_webhook
                # already published its own quiet skip log.
                return
            file_stem, tracker = generate(file_stem)
            print(f"Publishing MQTT log line for {file_stem}...", flush=True)
            mqtt_log.publish_log(
                "System",
                f"Published hike summary for {file_stem}: "
                f"https://hikes.jctnet.com/{file_stem}_hike-summary.html "
                f"(API cost: {tracker.summary()}). A daily catch-up pass runs automatically "
                f"at 17:00 to pick up anything that syncs later (new photos, late sensor "
                f"readings); use \"Run Step 2\" on the JCTsh Menu to force it sooner.",
            )
            _post_hike_cost_and_log(file_stem, "step1", tracker)
            ha_notify.send_push(
                "Hike-izer",
                f"Hike summary published: https://hikes.jctnet.com/{file_stem}_hike-summary.html",
                url=f"https://hikes.jctnet.com/{file_stem}_hike-summary.html",
            )
            return
        except Exception as e:
            print(f"Hike summary generation failed (attempt {attempt}/{GENERATION_MAX_ATTEMPTS}): {e}", file=sys.stderr)
            if attempt < GENERATION_MAX_ATTEMPTS:
                mqtt_log.publish_log(
                    "System",
                    f"Hike summary generation failed (attempt {attempt}/{GENERATION_MAX_ATTEMPTS}), "
                    f"retrying in 15 min: {e}",
                )
                time.sleep(GENERATION_RETRY_INTERVAL_SEC)
            else:
                mqtt_log.publish_log(
                    "Alert",
                    f"Hike summary generation failed after {GENERATION_MAX_ATTEMPTS} attempts: {e}",
                )
                ha_notify.send_push(
                    "Hike-izer", f"Hike summary generation failed after {GENERATION_MAX_ATTEMPTS} attempts: {e}"
                )


def run_step2_and_log(file_stem):
    """Force an immediate re-run of generate() for an already-published
    hike, instead of waiting for the next automatic catch-up pass -- called
    from the CLI (`--step2 FILE_STEM`, see main()) and from app.py's
    /webhook/step2 (the JCTsh Menu's "Run Step 2" entry). Kept under this
    name/flag/URL for compatibility with the Tasker task that calls it and
    with Joseph's own muscle memory -- the underlying process is identical
    to every other call to generate(), CARD-0348.

    CARD-0258: same retry-before-alert treatment as run_and_log -- see its
    docstring. Still re-raises after the final failed attempt so a direct
    CLI invocation exits non-zero."""
    for attempt in range(1, GENERATION_MAX_ATTEMPTS + 1):
        try:
            file_stem, tracker = generate(file_stem)
            mqtt_log.publish_log(
                "System",
                f"Published hike summary for {file_stem} (regenerated on request): "
                f"https://hikes.jctnet.com/{file_stem}_hike-summary.html "
                f"(API cost: {tracker.summary()}).",
            )
            _post_hike_cost_and_log(file_stem, "step2", tracker)
            ha_notify.send_push(
                "Hike-izer",
                f"Hike summary regenerated: https://hikes.jctnet.com/{file_stem}_hike-summary.html",
                url=f"https://hikes.jctnet.com/{file_stem}_hike-summary.html",
            )
            return
        except Exception as e:
            print(f"Hike summary regeneration failed for {file_stem} (attempt {attempt}/{GENERATION_MAX_ATTEMPTS}): {e}", file=sys.stderr)
            if attempt < GENERATION_MAX_ATTEMPTS:
                mqtt_log.publish_log(
                    "System",
                    f"Hike summary regeneration failed for {file_stem} "
                    f"(attempt {attempt}/{GENERATION_MAX_ATTEMPTS}), retrying in 15 min: {e}",
                )
                time.sleep(GENERATION_RETRY_INTERVAL_SEC)
            else:
                mqtt_log.publish_log(
                    "Alert",
                    f"Hike summary regeneration failed for {file_stem} "
                    f"after {GENERATION_MAX_ATTEMPTS} attempts: {e}",
                )
                ha_notify.send_push(
                    "Hike-izer",
                    f"Hike summary regeneration failed for {file_stem} after {GENERATION_MAX_ATTEMPTS} attempts: {e}",
                )
                raise


def run_daily_refresh_and_log():
    """CARD-0214's time-triggered catch-up pass -- entry point for the
    daily systemd timer (see tos/hike-izer-daily-refresh.service/.timer).
    Runs the identical generate() (CARD-0348) for every hike published in
    the last DAILY_REFRESH_LOOKBACK_HOURS, so anything that synced since
    the webhook-triggered first pass (or since yesterday's catch-up) gets
    picked up without anyone having to ask -- and, per generate()'s own
    places-state cache, without re-running an Overpass lookup that already
    succeeded.

    Deliberately quieter than a manual regenerate: a routine day with
    nothing new to add still logs a System line per hike (dashboard/audit
    visibility), but doesn't push an HA notification on success -- this
    runs unattended every day and most days are genuinely a no-op. A
    failure on any individual hike still gets a real Alert + push, same as
    every other unattended job in this codebase -- this loops per-hike so
    one failure doesn't stop the rest from being checked.

    CARD-0258: unlike run_and_log/run_step2_and_log's own per-call retry,
    this runs every hike due for a check in one pass first, then retries
    only the ones that failed as a group, GENERATION_RETRY_INTERVAL_SEC
    apart, up to GENERATION_MAX_ATTEMPTS each -- so one persistently-failing
    hike's retries don't delay checking the others."""
    # CARD-0338: don't pile a full-range export onto a Sheet that is already
    # struggling (2026-09-25 outage). A manually-requested --step2 is not gated.
    for check_no in range(1, SHEET_HEALTH_CHECKS + 1):
        healthy, detail = sheet_health.check(_env("DATA_PIPELINE_URL") + "/health", _env("DATA_PIPELINE_KEY"))
        if healthy:
            break
        print(f"run_daily_refresh: Sheet not healthy ({detail}), check {check_no}/{SHEET_HEALTH_CHECKS}", flush=True)
        if check_no < SHEET_HEALTH_CHECKS:
            time.sleep(SHEET_HEALTH_RETRY_SEC)
    else:
        mqtt_log.publish_log(
            "Alert",
            f"Hike-izer daily catch-up SKIPPED: the environmental Sheet stayed unhealthy across "
            f"{SHEET_HEALTH_CHECKS} checks ({detail}). Re-run it by hand once the Sheet responds -- "
            f"generation.py --daily-refresh -- or a morning hike falls out of tomorrow's lookback.",
        )
        return

    stems = _stems_recently_published()
    if not stems:
        print("run_daily_refresh: no recently-published hikes -- nothing to do", flush=True)
        return

    pending = {file_stem: 1 for file_stem in stems}  # file_stem -> attempt about to run
    while pending:
        still_failing = {}
        for file_stem, attempt in pending.items():
            try:
                file_stem, tracker = generate(file_stem)
                print(f"Daily catch-up complete for {file_stem} -- {tracker.summary()}", flush=True)
                mqtt_log.publish_log(
                    "System",
                    f"Daily catch-up pass complete for {file_stem}: "
                    f"https://hikes.jctnet.com/{file_stem}_hike-summary.html "
                    f"(API cost: {tracker.summary()}).",
                )
                _post_hike_cost_and_log(file_stem, "daily-refresh", tracker)
            except Exception as e:
                print(f"Daily catch-up failed for {file_stem} (attempt {attempt}/{GENERATION_MAX_ATTEMPTS}): {e}", file=sys.stderr, flush=True)
                if attempt < GENERATION_MAX_ATTEMPTS:
                    still_failing[file_stem] = attempt + 1
                else:
                    mqtt_log.publish_log(
                        "Alert",
                        f"Hike-izer daily catch-up failed for {file_stem} after {GENERATION_MAX_ATTEMPTS} attempts: {e}",
                    )
                    ha_notify.send_push(
                        "Hike-izer",
                        f"Daily hike-summary catch-up failed for {file_stem} after {GENERATION_MAX_ATTEMPTS} attempts: {e}",
                    )
        pending = still_failing
        if pending:
            print(
                f"run_daily_refresh: {len(pending)} hike(s) still failing, retrying in 15 min: {sorted(pending)}",
                file=sys.stderr, flush=True,
            )
            time.sleep(GENERATION_RETRY_INTERVAL_SEC)


def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--step2", metavar="FILE_STEM",
        help="Force an immediate regeneration of an already-published hike (photos, "
             "place naming), instead of waiting for the next automatic daily catch-up "
             "pass -- e.g. 2026-07-29 or 2026-07-29-2 for a second same-day hike. Safe "
             "to run any number of times.",
    )
    ap.add_argument(
        "--daily-refresh", action="store_true",
        help="CARD-0214: run the catch-up pass against every hike published in the last "
             "DAILY_REFRESH_LOOKBACK_HOURS. Normally fired by the daily systemd timer, but "
             "safe to run manually any number of times -- it only ever pays for what's "
             "actually new since the last pass.",
    )
    args = ap.parse_args()
    if args.daily_refresh:
        run_daily_refresh_and_log()
        return
    if not args.step2:
        ap.error("nothing to do -- pass --step2 <file_stem> or --daily-refresh")
    run_step2_and_log(args.step2)


if __name__ == "__main__":
    main()
