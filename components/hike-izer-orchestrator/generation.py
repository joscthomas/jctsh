#!/usr/bin/env python
"""
Hike-izer generation pipeline (CARD-0086 stage 2).

Runs on a real GPSLogger "stopped" event: fetches the day's data exactly as
SKILL.md's interactive steps 3/6 do, builds the mechanical output
(templating.py) plus one narrative-generation call (narrative.py), and
writes the result straight into the directory hike-izer-web already serves
-- no scp step, unlike the interactive Skill's Windows-based flow.

Determines "today" from the webhook payload's own local_datetime (never
Arizona-hardcoded) -- a hike can happen anywhere Joseph is carrying his
phone.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import cost_tracking
import mqtt_log
import narrative
import photo_captions
import place_context as place_context_module
import templating

SRV_DIR = "/srv/hike-izer"
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


def _session_query_window(payload, date_str, offset_str):
    """CARD-0113: bound the query to this specific hike session (its own
    start/end, from the webhook payload, plus SESSION_QUERY_PADDING) instead
    of the full calendar day. Narrowing per-trigger is what actually fixes
    two same-day hikes getting merged into one report -- each webhook fire
    only ever sees its own session's data. Falls back to the old full-day
    window if the payload is missing the fields this needs (defensive, not
    expected in practice -- every real 'stopped' payload observed so far
    carries both)."""
    try:
        session_end_utc = datetime.fromisoformat(payload["local_datetime"]).astimezone(timezone.utc)
        session_start_utc = datetime.fromtimestamp(
            int(payload["startedtimestamp"]) / 1000, tz=timezone.utc
        )
    except (KeyError, ValueError, TypeError) as e:
        print(
            f"_session_query_window: payload missing usable session bounds ({e}) "
            f"-- falling back to full-day query window",
            file=sys.stderr,
        )
        return f"{date_str}T00:00:00{offset_str}", f"{date_str}T23:59:59{offset_str}"

    start_utc = session_start_utc - SESSION_QUERY_PADDING
    end_utc = session_end_utc + SESSION_QUERY_PADDING
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


def run(payload):
    tracker = cost_tracking.CostTracker()
    local_datetime = payload.get("local_datetime")
    if not local_datetime:
        raise ValueError("payload missing local_datetime -- cannot determine which day to generate")
    date_str, offset_str = _local_date_and_offset(local_datetime)

    # CARD-0113: query window is scoped to this specific session (not the
    # full calendar day) -- see _session_query_window for why. date_str/
    # offset_str themselves are unaffected; they still name and localize
    # the output the same way regardless of query width.
    start_iso, end_iso = _session_query_window(payload, date_str, offset_str)

    os.makedirs(SRV_DIR, exist_ok=True)
    # CARD-0113: a day can produce more than one hike-summary now -- decide
    # this run's own file stem ('<date>' for the first, '<date>-2' etc. for
    # any later same-day hike) before anything gets written, so every output
    # path (HTML, meta.json, photos dir, temp fetch file) uses it
    # consistently.
    file_stem = _next_file_stem(date_str)

    hike_data_path = f"/tmp/hike_data_{file_stem}.json"
    subprocess.run(
        [
            sys.executable, FETCH_DATA_SCRIPT,
            "--start", start_iso, "--end", end_iso,
            "--url", _env("APPS_SCRIPT_URL"), "--key", _env("APPS_SCRIPT_KEY"),
            "--out", hike_data_path,
        ],
        check=True, timeout=120,
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
        return None, tracker

    # hike_confirmed is true past this point (checked above) -- fetch photos
    photos_manifest = None
    photos_dir = os.path.join(SRV_DIR, f"{file_stem}_photos")
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
        if manifest.get("assets"):
            photos_manifest = manifest
    except subprocess.CalledProcessError as e:
        # Photos are a nice-to-have (CARD-0084) -- never let a photo-fetch
        # failure block the summary itself, same as the interactive Skill's
        # "omit the Photos section" handling for a failed/empty manifest.
        print(f"fetch_hike_photos.py failed ({e}) -- continuing without photos", file=sys.stderr)

    if photos_manifest:
        photos_manifest = photo_captions.caption_photos(
            photos_manifest, photos_dir, _env("ANTHROPIC_API_KEY"), cost_tracker=tracker
        )

    with open(SKILL_MD_PATH, "r", encoding="utf-8") as f:
        skill_md_text = f.read()

    # CARD-0108: runs after photo captioning so sign_text (if any) is
    # already on the manifest and available as search-anchor material.
    place_context = place_context_module.gather_place_context(
        hike_data, photos_manifest, _env("ANTHROPIC_API_KEY"),
        regional_cache_path=os.path.join(SRV_DIR, "regional_context_cache.json"),
        cost_tracker=tracker,
    )

    paragraphs = narrative.generate_narrative(
        hike_data, skill_md_text, _env("ANTHROPIC_API_KEY"), place_context=place_context, cost_tracker=tracker
    )

    html_text = templating.render_html(hike_data, paragraphs, date_str, offset_str, photos_manifest)

    with open(os.path.join(SRV_DIR, f"{file_stem}_hike-summary.html"), "w", encoding="utf-8") as f:
        f.write(html_text)

    # CARD-0092: sidecar manifest for the calendar home page. Always
    # hike_confirmed: true here -- CARD-0100 already returned early above
    # for any day that isn't a confirmed hike, so this automatic path only
    # ever reaches this point on a real hike.
    with open(os.path.join(SRV_DIR, f"{file_stem}_hike-summary.meta.json"), "w", encoding="utf-8") as f:
        json.dump({"hike_confirmed": True}, f)

    subprocess.run(
        [sys.executable, BUILD_CALENDAR_SCRIPT, "--srv-dir", SRV_DIR],
        check=True, timeout=30,
    )

    print(f"Generation complete for {file_stem} -- {tracker.summary()}", file=sys.stderr, flush=True)
    return file_stem, tracker


def run_and_log(payload):
    try:
        file_stem, tracker = run(payload)
        if file_stem is None:
            # CARD-0100: no hike confirmed -- run() already published its own
            # quiet skip log, nothing more to do here.
            return
        print(f"Publishing MQTT log line for {file_stem}...", file=sys.stderr, flush=True)
        mqtt_log.publish_log(
            "System",
            f"Published hike summary for {file_stem}: "
            f"https://hikes.jctnet.com/{file_stem}_hike-summary.html "
            f"(API cost: {tracker.summary()})",
        )
    except Exception as e:
        print(f"Generation failed: {e}", file=sys.stderr)
        mqtt_log.publish_log("Alert", f"Hike summary generation failed: {e}")
