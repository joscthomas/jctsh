#!/usr/bin/env python
"""
Hike-izer generation pipeline (CARD-0086 stage 2, split into two steps by
CARD-0112).

Step 1 (run/run_and_log) fires automatically on a real GPSLogger "stopped"
event and publishes a **data-only** page immediately -- no narrative, since
photos (Immich's own background-upload delay), a Gaia GPS embed (a manual
per-hike step Joseph does himself), and BirdNET bird-ID data (CARD-0080) are
all things this pipeline can't force or reliably predict the timing of.
Trying to retry/backfill around each of those individually fights the
actual limitation; publishing what's genuinely available right now and
enriching later doesn't.

Step 2 (run_step2) is triggered conversationally, whenever Joseph has staged
what he can (opened Immich, dropped a Gaia embed snippet or BirdNET export
into that hike's staging directory) and asks for "the rich version" of a
hike. It reuses step 1's persisted hike_data.json (no re-querying the Apps
Script), re-fetches photos, reads the staging directory, and runs the one
narrative-generation call -- with everything actually available, instead of
one written blind before anything else was ready.

Determines "today" from the webhook payload's own local_datetime (never
Arizona-hardcoded) -- a hike can happen anywhere Joseph is carrying his
phone.
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import birdnet
import cost_tracking
import ha_notify
import mqtt_log
import narrative
import photo_captions
import place_context as place_context_module
import templating

SRV_DIR = "/srv/hike-izer"
# CARD-0112: hike_data.json (raw GPS trackpoints, full Environmental Data)
# reveals far more than the curated HTML summary -- notably the exact home
# address, via every hike's own start/end coordinates -- so it's persisted
# here instead, a directory never mounted into the `web` service at all,
# rather than relying on a Caddyfile exclusion rule for every internal file.
PRIVATE_DIR = "/srv/hike-izer-private"
SKILL_MD_PATH = "/app/SKILL.md"
FETCH_DATA_SCRIPT = "/app/fetch_hike_data.py"
FETCH_PHOTOS_SCRIPT = "/app/fetch_hike_photos.py"
BUILD_CALENDAR_SCRIPT = "/app/build_calendar_index.py"

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
                "--url", _env("APPS_SCRIPT_URL"), "--key", _env("APPS_SCRIPT_KEY"),
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


def _fetch_photos(hike_data_path, photos_dir):
    """Shared by step 1 (best-effort attempt) and step 2 (the real fetch,
    now that Immich has hopefully caught up -- CARD-0111/CARD-0112). Returns
    a manifest dict with at least one asset, or None."""
    try:
        subprocess.run(
            [
                sys.executable, FETCH_PHOTOS_SCRIPT,
                "--data", hike_data_path,
                "--immich-url", _env("IMMICH_URL"), "--immich-key", _env("IMMICH_KEY"),
                "--out-dir", photos_dir,
            ],
            check=True, timeout=180,
        )
        with open(os.path.join(photos_dir, "manifest.json"), "r", encoding="utf-8") as f:
            manifest = json.load(f)
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
    # itself for any .zip/.json export, called directly from run_step2()
    # rather than threaded through this dict.
    return staged


def run(payload):
    """Step 1 (CARD-0112): fully automatic, unchanged trigger (CARD-0086's
    GPSLogger 'stopped' webhook). Publishes a data-only page immediately --
    no place_context, no narrative call. Photos still get a best-effort
    attempt (cheap, in case they happen to already be uploaded), but the
    real photo pass is step 2's job."""
    tracker = cost_tracking.CostTracker()
    local_datetime = payload.get("local_datetime")
    if not local_datetime:
        raise ValueError("payload missing local_datetime -- cannot determine which day to generate")
    date_str, offset_str = _local_date_and_offset(local_datetime)

    # CARD-0113: query window is scoped to this specific session (not the
    # full calendar day) -- see _detect_session_window for why. date_str/
    # offset_str themselves are unaffected; they still name and localize
    # the output the same way regardless of query width.
    start_iso, end_iso = _detect_session_window(payload, date_str, offset_str)

    os.makedirs(SRV_DIR, exist_ok=True)
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    # CARD-0113: a day can produce more than one hike-summary now -- decide
    # this run's own file stem ('<date>' for the first, '<date>-2' etc. for
    # any later same-day hike) before anything gets written, so every output
    # path (HTML, meta.json, photos dir) uses it consistently.
    file_stem = _next_file_stem(date_str)

    # CARD-0135: set before any slow work starts, cleared in the finally
    # below regardless of how this run ends -- see current_or_latest_file_stem()
    # for why this needs to exist at all (a file staged while this run is
    # still in flight has nothing published yet to attach to otherwise).
    _set_in_progress_stem(file_stem)
    try:
        # CARD-0112: persisted in PRIVATE_DIR (never web-exposed, see that
        # constant's own comment), not /tmp -- so step 2 can reuse it hours or
        # days later, even across a container restart, without re-querying the
        # Apps Script for data that can't have changed since the hike happened.
        hike_data_path = os.path.join(PRIVATE_DIR, f"{file_stem}_hike_data.json")
        subprocess.run(
            [
                sys.executable, FETCH_DATA_SCRIPT,
                "--start", start_iso, "--end", end_iso,
                "--url", _env("APPS_SCRIPT_URL"), "--key", _env("APPS_SCRIPT_KEY"),
                "--out", hike_data_path,
            ],
            # CARD-0135: see _detect_session_window's identical comment --
            # same retry-latency reasoning applies here.
            check=True, timeout=240,
        )
        with open(hike_data_path, "r", encoding="utf-8") as f:
            hike_data = json.load(f)

        # CARD-0100: don't spend a real Claude API call or publish a live page
        # for a day with no confirmed hike (e.g. GPSLogger left running during a
        # car errand) -- fetch_hike_data.py's own classification already knows
        # this, the automatic path just wasn't checking it before doing real
        # work. This gate is specific to the automatic webhook path; the
        # interactive Skill correctly still reports "no hike" when Joseph
        # explicitly asks, since that's a wanted answer, not a bug.
        if not hike_data["coverage"]["gps_track"]["hike_confirmed"]:
            print(f"No hike confirmed for {file_stem} -- skipping generation", file=sys.stderr, flush=True)
            mqtt_log.publish_log(
                "System",
                f"GPSLogger stopped, no hike confirmed for {file_stem} -- skipped generation.",
            )
            os.remove(hike_data_path)  # nothing for step 2 to ever reuse for this non-hike
            return None, tracker

        # CARD-0112: staging directory created up front (even though nothing's
        # in it yet) so Joseph's SSHFS-Win-mounted drive shows a real folder to
        # drop files into immediately, rather than needing to create it himself
        # before staging anything for this hike.
        #
        # CARD-0119: this process runs as root inside the container, so a plain
        # os.makedirs() defaults to owner-only write (0755) -- the SSHFS-Win
        # mount connects as the `jct` Linux user, which isn't root and isn't in
        # its group, so it could read/traverse but never actually drop a file
        # in via the mount (confirmed live 2026-07-30). chmod explicitly,
        # rather than passing mode= to makedirs(), since mode= is masked by the
        # container's umask and doesn't reliably produce 0o777 either way.
        _staging_dir = os.path.join(SRV_DIR, f"{file_stem}_staging")
        os.makedirs(_staging_dir, exist_ok=True)
        os.chmod(_staging_dir, 0o777)

        # CARD-0136: claim anything the BirdNET stage-file webhook parked
        # for this calendar date before this run's own file_stem existed to
        # attach to (a share arriving ahead of this very webhook -- confirmed
        # live 2026-08-03). Keyed by date_str, not file_stem, since the
        # pending side can't know yet whether this'll be the day's first
        # hike or a later one.
        _claim_pending_birdnet(date_str, _staging_dir)

        # hike_confirmed is true past this point (checked above). Photos: best-
        # effort only -- CARD-0111 confirmed Immich's own upload almost never
        # happens this fast, but it costs nothing to check.
        photos_dir = os.path.join(SRV_DIR, f"{file_stem}_photos")
        photos_manifest = _fetch_photos(hike_data_path, photos_dir)
        if photos_manifest:
            photos_manifest = photo_captions.caption_photos(
                photos_manifest, photos_dir, _env("ANTHROPIC_API_KEY"), cost_tracker=tracker
            )

        # CARD-0135: same best-effort spirit as the photos fetch above --
        # cheap to check, and now that current_or_latest_file_stem() lets a
        # file staged mid-run correctly target this hike, worth checking
        # rather than always leaving bird data to step 2. Rare that anything
        # is here yet (the common case is still step 2), but no harm either
        # way -- parse_detections()/parse_occurrences() both just return
        # empty when the staging dir has no BirdNET export in it.
        birdnet_rows = birdnet.parse_detections(_staging_dir)
        birdnet_occurrences = birdnet.parse_occurrences(_staging_dir)

        # CARD-0112: no place_context, no narrative call in step 1 -- mechanical
        # rendering only. templating.render_html omits the whole narrative
        # section when narrative_paragraphs is empty, same convention as the
        # Photos section's own omit-when-empty handling.
        # CARD-0134: thunderforest_api_key passed here too (not just step 2) --
        # the Route Map + Elevation & Speed chart need no manual staging, unlike
        # the Gaia embed they replaced, so every automatically-published page
        # gets a real map/chart from this very first publish.
        html_text = templating.render_html(
            hike_data, [], date_str, offset_str, photos_manifest, file_stem=file_stem,
            thunderforest_api_key=_env("THUNDERFOREST_API_KEY"),
            birdnet_rows=birdnet_rows, birdnet_occurrences=birdnet_occurrences,
        )

        with open(os.path.join(SRV_DIR, f"{file_stem}_hike-summary.html"), "w", encoding="utf-8") as f:
            f.write(html_text)

        # CARD-0092: sidecar manifest for the calendar home page. Always
        # hike_confirmed: true here -- CARD-0100 already returned early above
        # for any day that isn't a confirmed hike, so this automatic path only
        # ever reaches this point on a real hike. offset_str is carried along so
        # step 2 (run hours/days later, from just a file stem) doesn't need to
        # re-derive it. start_ts (CARD-0118) is the earliest confirmed session's
        # raw UTC start, so build_calendar_index.py can label this hike's
        # calendar-cell link with its actual local start time.
        confirmed_sessions = [s for s in hike_data["coverage"]["gps_track"]["sessions"] if s["is_hike"]]
        start_ts = min((s["start"] for s in confirmed_sessions), default=None)
        with open(os.path.join(SRV_DIR, f"{file_stem}_hike-summary.meta.json"), "w", encoding="utf-8") as f:
            json.dump({"hike_confirmed": True, "offset_str": offset_str, "start_ts": start_ts}, f)

        subprocess.run(
            [sys.executable, BUILD_CALENDAR_SCRIPT, "--srv-dir", SRV_DIR],
            check=True, timeout=30,
        )

        print(f"Step 1 complete for {file_stem} -- {tracker.summary()}", file=sys.stderr, flush=True)
        return file_stem, tracker
    finally:
        _clear_in_progress_stem()


def run_step2(file_stem, with_narrative=False):
    """Step 2 (CARD-0112): conversationally triggered, once Joseph has
    staged what he can (opened Immich, dropped a Gaia embed/BirdNET export
    into the staging directory). Re-fetches photos for real, reads staging,
    runs place_context (always the free deterministic layers; the research
    layers + the narrative call only if with_narrative, CARD-0123 -- off by
    default, since those are the only real cost here beyond photo
    captioning), and republishes the full page in place of step 1's
    data-only version."""
    tracker = cost_tracking.CostTracker()
    date_str = _date_str_from_stem(file_stem)

    hike_data_path = os.path.join(PRIVATE_DIR, f"{file_stem}_hike_data.json")
    with open(hike_data_path, "r", encoding="utf-8") as f:
        hike_data = json.load(f)

    meta_path = os.path.join(SRV_DIR, f"{file_stem}_hike-summary.meta.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    offset_str = meta["offset_str"]

    # Real photo fetch this time, not step 1's best-effort attempt.
    photos_dir = os.path.join(SRV_DIR, f"{file_stem}_photos")
    photos_manifest = _fetch_photos(hike_data_path, photos_dir)
    if photos_manifest:
        photos_manifest = photo_captions.caption_photos(
            photos_manifest, photos_dir, _env("ANTHROPIC_API_KEY"), cost_tracker=tracker
        )

    staged = _read_staging(file_stem)

    # CARD-0080: parsing only, no API call -- see birdnet.py for why no
    # location correlation is attempted (Joseph's call: table only).
    staging_dir = os.path.join(SRV_DIR, f"{file_stem}_staging")
    birdnet_rows = birdnet.parse_detections(staging_dir)
    # CARD-0133: separate, per-occurrence view of the same staged export(s)
    # -- for the Route Map's bird markers, which do need a real (if
    # approximate, interpolated) position per sighting, unlike the table
    # above. Only ever populated here in step 2, same as birdnet_rows itself
    # -- step 1 never has a staged BirdNET export to read yet.
    birdnet_occurrences = birdnet.parse_occurrences(staging_dir)

    # CARD-0108/CARD-0112: runs after photo captioning so sign_text (if any)
    # is already on the manifest, and now with real photo locations
    # available to ground named_features() along the actual route (see
    # place_context.py's own CARD-0112 fix) rather than just the hike's
    # first GPS point. include_research=with_narrative (CARD-0123): the
    # deterministic address/named-features layers always run (free, feed
    # the Location/Nearby Named Features sections below either way) -- only
    # the Claude+web_search research layers are gated.
    place_context = place_context_module.gather_place_context(
        hike_data, photos_manifest, _env("ANTHROPIC_API_KEY"),
        regional_cache_path=os.path.join(SRV_DIR, "regional_context_cache.json"),
        cost_tracker=tracker, include_research=with_narrative,
    )

    # CARD-0123: narrative off by default -- SKILL.md is only ever read for
    # narrative writing, so skip that too when it's not needed.
    paragraphs = []
    if with_narrative:
        with open(SKILL_MD_PATH, "r", encoding="utf-8") as f:
            skill_md_text = f.read()
        narrative_facts = place_context_module.flatten_for_narrative(place_context)
        paragraphs = narrative.generate_narrative(
            hike_data, skill_md_text, _env("ANTHROPIC_API_KEY"), place_context=narrative_facts, cost_tracker=tracker
        )

    # CARD-0134: gaia_embed_html deliberately not passed anymore -- the
    # native Route Map (CARD-0082) replaced it as this pipeline's default,
    # since it needs no manual staging. _read_staging() above still reads
    # gaia_embed.txt if present (untouched), but this call no longer uses
    # it; templating.render_html's gaia_section stays available for a
    # future caller, just unused by this one now.
    html_text = templating.render_html(
        hike_data, paragraphs, date_str, offset_str, photos_manifest,
        file_stem=file_stem,
        birdnet_rows=birdnet_rows,
        address=place_context.get("address"), named_features=place_context.get("named_features"),
        thunderforest_api_key=_env("THUNDERFOREST_API_KEY"),
        birdnet_occurrences=birdnet_occurrences,
    )

    with open(os.path.join(SRV_DIR, f"{file_stem}_hike-summary.html"), "w", encoding="utf-8") as f:
        f.write(html_text)

    subprocess.run(
        [sys.executable, BUILD_CALENDAR_SCRIPT, "--srv-dir", SRV_DIR],
        check=True, timeout=30,
    )

    print(f"Step 2 complete for {file_stem} -- {tracker.summary()}", file=sys.stderr, flush=True)
    return file_stem, tracker


def run_and_log(payload):
    """Step 1's entry point -- called by app.py on every real webhook."""
    try:
        file_stem, tracker = run(payload)
        if file_stem is None:
            # CARD-0100: no hike confirmed -- run() already published its own
            # quiet skip log, nothing more to do here.
            return
        print(f"Publishing MQTT log line for {file_stem}...", file=sys.stderr, flush=True)
        mqtt_log.publish_log(
            "System",
            f"Published data-only hike summary for {file_stem}: "
            f"https://hikes.jctnet.com/{file_stem}_hike-summary.html "
            f"(API cost: {tracker.summary()}). Ask for the rich version once photos/Gaia/bird data are staged.",
        )
        ha_notify.send_push(
            "Hike-izer",
            f"Hike summary published: https://hikes.jctnet.com/{file_stem}_hike-summary.html",
        )
    except Exception as e:
        print(f"Step 1 generation failed: {e}", file=sys.stderr)
        mqtt_log.publish_log("Alert", f"Hike summary step 1 generation failed: {e}")
        ha_notify.send_push("Hike-izer", f"Hike summary generation failed: {e}")


def run_step2_and_log(file_stem, with_narrative=False):
    """Step 2's entry point -- called from the CLI (see main()) when Joseph
    asks, conversationally, for the rich version of a specific hike."""
    try:
        file_stem, tracker = run_step2(file_stem, with_narrative=with_narrative)
        mqtt_log.publish_log(
            "System",
            f"Published enriched hike summary for {file_stem}: "
            f"https://hikes.jctnet.com/{file_stem}_hike-summary.html "
            f"(API cost: {tracker.summary()}).",
        )
        ha_notify.send_push(
            "Hike-izer",
            f"Enriched hike summary published: https://hikes.jctnet.com/{file_stem}_hike-summary.html",
        )
    except Exception as e:
        print(f"Step 2 generation failed: {e}", file=sys.stderr)
        mqtt_log.publish_log("Alert", f"Hike summary step 2 generation failed for {file_stem}: {e}")
        ha_notify.send_push("Hike-izer", f"Hike summary generation failed for {file_stem}: {e}")
        raise


def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--step2", metavar="FILE_STEM",
        help="Run step 2 (photos + place context +, if --narrative, the researched "
             "narrative prose) for an already-published file stem, e.g. 2026-07-29 or "
             "2026-07-29-2 for a second same-day hike.",
    )
    ap.add_argument(
        "--narrative", action="store_true",
        help="CARD-0123: include full narrative generation -- place-context research "
             "(Claude + web_search) plus the Claude-written prose paragraphs. Opt-in, "
             "real added cost; off by default leaves only photo-caption cost.",
    )
    args = ap.parse_args()
    if not args.step2:
        ap.error("nothing to do -- pass --step2 <file_stem> (step 1 runs via the webhook, not this CLI)")
    run_step2_and_log(args.step2, with_narrative=args.narrative)


if __name__ == "__main__":
    main()
