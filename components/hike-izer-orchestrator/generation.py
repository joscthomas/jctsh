#!/usr/bin/env python
"""
Hike-izer generation pipeline (CARD-0086 stage 2).

Runs on a real GPSLogger "stopped" event: fetches the day's data exactly as
SKILL.md's interactive steps 3/7 do, builds the mechanical output
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

import mqtt_log
import narrative
import templating

SRV_DIR = "/srv/hike-izer"
SKILL_MD_PATH = "/app/SKILL.md"
FETCH_DATA_SCRIPT = "/app/fetch_hike_data.py"
FETCH_PHOTOS_SCRIPT = "/app/fetch_hike_photos.py"


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


def run(payload):
    local_datetime = payload.get("local_datetime")
    if not local_datetime:
        raise ValueError("payload missing local_datetime -- cannot determine which day to generate")
    date_str, offset_str = _local_date_and_offset(local_datetime)

    # Query window uses the hike's own local offset, not a hardcoded Z
    # boundary -- SKILL.md's "query 00:00:00Z-23:59:59Z, attribute a session
    # by its start timestamp" convention is a manual-judgment workaround for
    # the fact that a Z-bounded window doesn't line up with any real local
    # day. With no human in the loop to apply that judgment in the automated
    # path, bounding the query by the hike's *actual* local offset avoids
    # the ambiguity outright: a session that truly belongs to the previous
    # local day (e.g. an evening session that only looks "cross-midnight"
    # because UTC and local calendar days don't line up) is correctly
    # excluded by the window itself, no reattachment logic needed. (Verified
    # 2026-07-24 against a real multi-session day -- an initial test using
    # the wrong offset for that trip's actual location/DST state looked like
    # this approach was dropping real data; it wasn't, the offset was just
    # wrong. The Apps Script itself confirms live data is unaffected -- see
    # CARD-0086 notes.)
    start_iso = f"{date_str}T00:00:00{offset_str}"
    end_iso = f"{date_str}T23:59:59{offset_str}"

    hike_data_path = f"/tmp/hike_data_{date_str}.json"
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
        print(f"No hike confirmed for {date_str} -- skipping generation", file=sys.stderr, flush=True)
        mqtt_log.publish_log(
            "System",
            f"GPSLogger stopped, no hike confirmed for {date_str} -- skipped generation.",
        )
        return None

    # hike_confirmed is true past this point (checked above) -- fetch photos
    photos_manifest = None
    photos_dir = os.path.join(SRV_DIR, f"{date_str}_photos")
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

    with open(SKILL_MD_PATH, "r", encoding="utf-8") as f:
        skill_md_text = f.read()

    paragraphs = narrative.generate_narrative(hike_data, skill_md_text, _env("ANTHROPIC_API_KEY"))

    md_text = templating.render_markdown(hike_data, paragraphs, date_str, offset_str)
    html_text = templating.render_html(hike_data, paragraphs, date_str, offset_str, photos_manifest)

    os.makedirs(SRV_DIR, exist_ok=True)
    with open(os.path.join(SRV_DIR, f"{date_str}_hike-summary.md"), "w", encoding="utf-8") as f:
        f.write(md_text)
    with open(os.path.join(SRV_DIR, f"{date_str}_hike-summary.html"), "w", encoding="utf-8") as f:
        f.write(html_text)

    print(f"Generation complete for {date_str}", file=sys.stderr, flush=True)
    return date_str


def run_and_log(payload):
    try:
        date_str = run(payload)
        if date_str is None:
            # CARD-0100: no hike confirmed -- run() already published its own
            # quiet skip log, nothing more to do here.
            return
        print(f"Publishing MQTT log line for {date_str}...", file=sys.stderr, flush=True)
        mqtt_log.publish_log(
            "System",
            f"Published hike summary for {date_str}: "
            f"https://photo-server.tailfe828a.ts.net/{date_str}_hike-summary.html",
        )
    except Exception as e:
        print(f"Generation failed: {e}", file=sys.stderr)
        mqtt_log.publish_log("Alert", f"Hike summary generation failed: {e}")
