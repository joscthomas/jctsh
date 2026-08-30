#!/usr/bin/env python3
"""CARD-0121: daily backstop check for missed hike generation.

app.py's only real generation trigger is GPSLogger's own 'stopped'
webhook (CARD-0086) -- if that broadcast never fires (GPSLogger crashes,
gets force-killed by Android, Tasker's exit condition never runs), no
page is ever generated for that hike, silently, with nothing surfacing
the gap anywhere. This module is the fix: run once a day, probe recent
GPS Track data the same way generation._detect_session_window() already
does for every normal run (real hike-shaped sessions via
fetch_hike_data.py's own gap-based classification, not raw point counts
-- CARD-0120's own hard-learned reason GPSLogger's self-reported timing
can't be trusted), and for any confirmed session with no matching
published page, generate it and flag the recovery distinctly on the
MQTT dashboard so it's never indistinguishable from a normal generation.

Deliberately NOT a per-calendar-day scan. generation.py has an explicit,
twice-documented rule that nothing here assumes the M8's fixed server TZ
(America/Phoenix) is Joseph's actual current one -- a hike can happen
anywhere he's carrying his phone (real cited case: Eastern time). A
per-local-day design would need to guess an offset just to pick day
boundaries, exactly the assumption that rule exists to avoid. Instead,
this probes one continuous rolling UTC window and checks each confirmed
session's own [start, end] (already UTC) for overlap against every
existing hike page's own persisted query_start_iso/query_end_iso
(CARD-0214) -- the same recency/range-based philosophy
_stems_recently_published()/latest_file_stem() already use for the
identical ambiguity, generalized here to "was this UTC time range ever
queried by a real generation."

Real, accepted limitation: recovering a hike this way still has to hand
generation.run() *some* local_datetime to compute file_stem/offset_str/
displayed times from, and the true local offset is unrecoverable -- it
only ever arrives via the webhook payload this whole card exists to
handle the absence of. Uses UTC (+00:00) rather than guessing Phoenix,
deliberately: a wrong-but-obviously-wrong offset (all displayed times
shifted by a suspicious round number) is safer than a wrong-but-
plausible one that could pass an unsuspecting glance -- exactly the
failure mode generation.py's own docstring already warns about.

Run as a background thread inside the orchestrator container (app.py
starts it once at boot) rather than a separate cron+docker-exec script
-- this needs direct access to generation.py's own SRV_DIR mount,
FETCH_DATA_SCRIPT, and run(), all already living in this same process;
a separate script would just re-import the same module anyway.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import generation
import mqtt_log

# CARD-0121: not yet confirmed against real-world firing frequency --
# daily is the card's own stated starting assumption. Scheduled for
# 5:00 AM Phoenix time specifically to sit clear of every other
# recurring job in jctsh-network.md's "Scheduled Maintenance Windows"
# table (M8's own weekly reboot is Mon 4:00 AM) and comfortably before
# any realistic hike start -- avoids the (rare, low-consequence, but
# real) chance of this thread's own generation.run() call colliding
# with a genuine live webhook-triggered run() over the shared
# _IN_PROGRESS_MARKER file generation.py uses.
DAILY_RUN_HOUR = 5
LOOKBACK_DAYS = 5  # CARD-0121: wide enough to catch a miss even if this check itself was down/deploying for a day or two -- cheap, since a session that already has a matching page is skipped before any real generation work happens.


def _probe_recent_sessions():
    """Same subprocess call generation._detect_session_window() makes for
    a single day, widened to one rolling UTC window covering the last
    LOOKBACK_DAYS. Returns the list of is_hike sessions found in it
    (possibly empty), each with UTC 'start'/'end' fields."""
    end_utc = datetime.now(timezone.utc)
    start_utc = end_utc - timedelta(days=LOOKBACK_DAYS)
    fd, probe_path = tempfile.mkstemp(suffix="_backstop_probe.json")
    os.close(fd)
    try:
        subprocess.run(
            [
                sys.executable, generation.FETCH_DATA_SCRIPT,
                "--start", start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "--end", end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "--url", generation._env("APPS_SCRIPT_URL"),
                "--key", generation._env("APPS_SCRIPT_KEY"),
                "--out", probe_path,
            ],
            check=True, timeout=240,
        )
        with open(probe_path, "r", encoding="utf-8") as f:
            probe_data = json.load(f)
    finally:
        os.remove(probe_path)
    return [s for s in probe_data["coverage"]["gps_track"]["sessions"] if s["is_hike"]]


def _existing_query_windows():
    """[(start_utc, end_utc), ...] for every published hike's own recorded
    query window (meta.json's query_start_iso/query_end_iso, CARD-0214).
    A meta.json without that field (published before CARD-0214, or by a
    very old pre-offset_str build) is skipped rather than guessed at --
    treating an unreadable window as "can't tell, assume covered" avoids
    ever re-generating and duplicating a hike that's already real and
    published, the more costly mistake of the two."""
    windows = []
    for meta_path in Path(generation.SRV_DIR).glob("*_hike-summary.meta.json"):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            start = datetime.fromisoformat(meta["query_start_iso"]).astimezone(timezone.utc)
            end = datetime.fromisoformat(meta["query_end_iso"]).astimezone(timezone.utc)
        except (OSError, KeyError, ValueError):
            continue
        windows.append((start, end))
    return windows


def _already_covered(session, existing_windows):
    session_start = datetime.fromisoformat(session["start"].replace("Z", "+00:00"))
    session_end = datetime.fromisoformat(session["end"].replace("Z", "+00:00"))
    return any(
        session_start < w_end and session_end > w_start
        for w_start, w_end in existing_windows
    )


def _recover_session(session):
    end_utc = datetime.fromisoformat(session["end"].replace("Z", "+00:00"))
    # See module docstring: UTC, not a guessed local offset -- the real
    # one is unrecoverable by the time this check runs.
    local_datetime = end_utc.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00"

    try:
        file_stem, tracker = generation.run({"local_datetime": local_datetime})
    except Exception as e:
        print(f"Backstop check: generation failed for session ending {session['end']}: {e}", file=sys.stderr)
        mqtt_log.publish_log(
            "Alert",
            f"Backstop check: found a missed hike (session ending {session['end']}) "
            f"but generation failed: {e}",
        )
        return

    if file_stem is None:
        # generation.run()'s own hike_confirmed re-check disagreed with
        # this probe's classification -- already logged by run() itself
        # (CARD-0100's existing skip-log path), nothing more to do.
        return

    print(f"Backstop check: recovered missed hike {file_stem}", file=sys.stderr, flush=True)
    mqtt_log.publish_log(
        "Alert",
        f"Backstop check: a hike's 'stopped' webhook was never received -- generated "
        f"{file_stem} late from GPS Track data alone (displayed times are UTC, not "
        f"local -- the real offset was never captured): "
        f"https://hikes.jctnet.com/{file_stem}_hike-summary.html "
        f"(API cost: {tracker.summary()}).",
    )


def run_once():
    """One backstop pass. Recovers oldest-first so an early recovery's own
    new meta.json is available (as an existing_windows entry) before a
    later, potentially-overlapping session in the same pass is checked --
    not expected to matter in practice (real hikes don't overlap) but
    cheap to get right."""
    try:
        sessions = _probe_recent_sessions()
    except Exception as e:
        print(f"Backstop check: probe failed: {e}", file=sys.stderr)
        mqtt_log.publish_log("Alert", f"Backstop check itself failed to probe GPS Track data: {e}")
        return

    sessions.sort(key=lambda s: s["end"])
    for session in sessions:
        existing_windows = _existing_query_windows()  # re-read each time -- cheap, and picks up this loop's own prior recoveries
        if _already_covered(session, existing_windows):
            continue
        _recover_session(session)


def _seconds_until_next_run():
    now = datetime.now()
    target = now.replace(hour=DAILY_RUN_HOUR, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def start_background_thread():
    def _loop():
        while True:
            time.sleep(_seconds_until_next_run())
            try:
                run_once()
            except Exception as e:
                print(f"Backstop check: unhandled error in run_once(): {e}", file=sys.stderr)
    threading.Thread(target=_loop, daemon=True).start()
