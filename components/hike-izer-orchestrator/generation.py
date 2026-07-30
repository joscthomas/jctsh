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

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import birdnet
import cost_tracking
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


def _date_str_from_stem(file_stem):
    # '2026-07-29' -> '2026-07-29'; '2026-07-29-2' -> '2026-07-29'
    return file_stem[:10]


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
    gaia_path = os.path.join(staging_dir, "gaia_embed.html")
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
    # full calendar day) -- see _session_query_window for why. date_str/
    # offset_str themselves are unaffected; they still name and localize
    # the output the same way regardless of query width.
    start_iso, end_iso = _session_query_window(payload, date_str, offset_str)

    os.makedirs(SRV_DIR, exist_ok=True)
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    # CARD-0113: a day can produce more than one hike-summary now -- decide
    # this run's own file stem ('<date>' for the first, '<date>-2' etc. for
    # any later same-day hike) before anything gets written, so every output
    # path (HTML, meta.json, photos dir) uses it consistently.
    file_stem = _next_file_stem(date_str)

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
        os.remove(hike_data_path)  # nothing for step 2 to ever reuse for this non-hike
        return None, tracker

    # CARD-0112: staging directory created up front (even though nothing's
    # in it yet) so Joseph's SSHFS-Win-mounted drive shows a real folder to
    # drop files into immediately, rather than needing to create it himself
    # before staging anything for this hike.
    os.makedirs(os.path.join(SRV_DIR, f"{file_stem}_staging"), exist_ok=True)

    # hike_confirmed is true past this point (checked above). Photos: best-
    # effort only -- CARD-0111 confirmed Immich's own upload almost never
    # happens this fast, but it costs nothing to check.
    photos_dir = os.path.join(SRV_DIR, f"{file_stem}_photos")
    photos_manifest = _fetch_photos(hike_data_path, photos_dir)
    if photos_manifest:
        photos_manifest = photo_captions.caption_photos(
            photos_manifest, photos_dir, _env("ANTHROPIC_API_KEY"), cost_tracker=tracker
        )

    # CARD-0112: no place_context, no narrative call in step 1 -- mechanical
    # rendering only. templating.render_html omits the whole narrative
    # section when narrative_paragraphs is empty, same convention as the
    # Photos section's own omit-when-empty handling.
    html_text = templating.render_html(hike_data, [], date_str, offset_str, photos_manifest, file_stem=file_stem)

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


def run_step2(file_stem):
    """Step 2 (CARD-0112): conversationally triggered, once Joseph has
    staged what he can (opened Immich, dropped a Gaia embed/BirdNET export
    into the staging directory). Re-fetches photos for real, reads staging,
    runs place_context + the one narrative call, and republishes the full
    page in place of step 1's data-only version."""
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
    birdnet_rows = birdnet.parse_detections(os.path.join(SRV_DIR, f"{file_stem}_staging"))

    with open(SKILL_MD_PATH, "r", encoding="utf-8") as f:
        skill_md_text = f.read()

    # CARD-0108/CARD-0112: runs after photo captioning so sign_text (if any)
    # is already on the manifest, and now with real photo locations
    # available to ground named_features() along the actual route (see
    # place_context.py's own CARD-0112 fix) rather than just the hike's
    # first GPS point.
    place_context = place_context_module.gather_place_context(
        hike_data, photos_manifest, _env("ANTHROPIC_API_KEY"),
        regional_cache_path=os.path.join(SRV_DIR, "regional_context_cache.json"),
        cost_tracker=tracker,
    )

    paragraphs = narrative.generate_narrative(
        hike_data, skill_md_text, _env("ANTHROPIC_API_KEY"), place_context=place_context, cost_tracker=tracker
    )

    html_text = templating.render_html(
        hike_data, paragraphs, date_str, offset_str, photos_manifest,
        gaia_embed_html=staged.get("gaia_embed_html"), file_stem=file_stem,
        birdnet_rows=birdnet_rows,
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
    except Exception as e:
        print(f"Step 1 generation failed: {e}", file=sys.stderr)
        mqtt_log.publish_log("Alert", f"Hike summary step 1 generation failed: {e}")


def run_step2_and_log(file_stem):
    """Step 2's entry point -- called from the CLI (see main()) when Joseph
    asks, conversationally, for the rich version of a specific hike."""
    try:
        file_stem, tracker = run_step2(file_stem)
        mqtt_log.publish_log(
            "System",
            f"Published enriched hike summary for {file_stem}: "
            f"https://hikes.jctnet.com/{file_stem}_hike-summary.html "
            f"(API cost: {tracker.summary()}).",
        )
    except Exception as e:
        print(f"Step 2 generation failed: {e}", file=sys.stderr)
        mqtt_log.publish_log("Alert", f"Hike summary step 2 generation failed for {file_stem}: {e}")
        raise


def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--step2", metavar="FILE_STEM",
        help="Run step 2 (photos + place context + narrative) for an already-published "
             "file stem, e.g. 2026-07-29 or 2026-07-29-2 for a second same-day hike.",
    )
    args = ap.parse_args()
    if not args.step2:
        ap.error("nothing to do -- pass --step2 <file_stem> (step 1 runs via the webhook, not this CLI)")
    run_step2_and_log(args.step2)


if __name__ == "__main__":
    main()
