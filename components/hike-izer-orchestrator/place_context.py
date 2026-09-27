#!/usr/bin/env python
"""
Shared OpenStreetMap/HTTP-retry helpers for hike-izer's place lookups
(CARD-0108's original module).

CARD-0348, 2026-09-27: this module's own Nearby Named Features Overpass
lookup and its research/regional-enrichment layers (a Claude + web_search
call, feeding the now-retired narrative pipeline) have both been removed.
Across all 10 real hikes published to date, Nearby Named Features had
returned a result exactly once -- and that one result (2026-09-03's
Douglas Spring Trail) was the hike's own trail, already named more
accurately by hike_places.py's own dedicated lookup (CARD-0311). Zero net
new information in ten real hikes, for three extra rate-limited Overpass
calls every time -- not worth keeping (Joseph, 2026-09-27: "the value of
nearby features seems dubious... a nearby feature that describes the same
thing is not desireable").

What remains here is genuinely shared infrastructure: the Nominatim
reverse-geocode call, the Overpass mirror list/User-Agent/retry-backoff
helper, and the hike-session-GPS-points helper -- all consumed by
hike_places.py (`import place_context as pc`), which does its own single
Overpass bounding-box call rather than this module's old per-point loop.
Stdlib-only, no `anthropic` dependency.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
# Two independent public Overpass mirrors, tried in order by hike_places.py.
# overpass-api.de returned 504 Gateway Timeout on two consecutive real runs
# several minutes apart during CARD-0108's own testing (2026-07-28) -- that
# gap plus two straight failures reads as a sustained outage on that
# specific instance, not a random blip, so a same-server retry wouldn't
# have helped; a second, independently-run mirror (Kumi Systems, speaks
# the same Overpass QL/response format) is the fix that actually addresses
# what was observed.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
USER_AGENT = "jctsh-hike-izer/1.0 (personal project, https://hikes.jctnet.com)"


def _retry_after_seconds(headers, default):
    """Parses an HTTP `Retry-After` response header (delay-seconds, or an
    HTTP-date -- RFC 9110 allows either) into a sleep duration, falling
    back to `default` when the header is absent or malformed (CARD-0323:
    a server-supplied wait is better information than a guess, but there
    must always be a floor for when the server doesn't supply one)."""
    value = headers.get("Retry-After") if headers else None
    if not value:
        return default
    try:
        return max(0, int(value))
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(value)
        if dt is None:
            return default
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, (dt - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return default


def _hike_session_points(hike_data):
    """CARD-0112: every GPS point belonging to a confirmed is_hike session,
    chronologically ordered. Timestamps are compared as plain ISO 8601
    strings (not parsed to datetime) -- they sort correctly lexicographically
    since every timestamp in this pipeline shares the same format/offset, and
    this avoids a second parsing convention alongside fetch_hike_data.py's
    own. Returns [] if there's no confirmed hike."""
    coverage = hike_data.get("coverage", {})
    gps_track_coverage = coverage.get("gps_track", {})
    if not gps_track_coverage.get("hike_confirmed"):
        return []
    windows = [
        (s["start"], s["end"]) for s in gps_track_coverage.get("sessions", [])
        if s.get("is_hike")
    ]
    if not windows:
        return []
    gps_rows = hike_data.get("gps_track") or []
    points = [
        r for r in gps_rows
        if r.get("timestamp") and any(start <= r["timestamp"] <= end for start, end in windows)
    ]
    return sorted(points, key=lambda r: r["timestamp"])


def _nominatim_reverse(lat, lon):
    """Raw Nominatim reverse-geocode call -- one HTTP request on the happy
    path. Retries once on genuine failure only (CARD-0323, closing this
    function's prior single-point-of-failure gap) -- this is resilience
    against a transient drop, never a second routine call, so a successful
    first attempt never triggers a retry. Returns the parsed response body,
    or None."""
    url = f"{NOMINATIM_URL}?lat={lat}&lon={lon}&format=jsonv2&zoom=16&addressdetails=1"
    last_error = None
    for attempt in range(2):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_error = e
            print(f"_nominatim_reverse attempt {attempt + 1} failed: HTTP {e.code} {e.reason}", file=sys.stderr)
            if attempt == 0:
                # Nominatim's usage policy caps requests at ~1/s -- honor a
                # server-supplied Retry-After if given, else a fixed pause
                # that alone already respects that policy for one retry.
                time.sleep(_retry_after_seconds(e.headers, default=2))
        except (urllib.error.URLError, ValueError, TimeoutError) as e:
            last_error = e
            print(f"_nominatim_reverse attempt {attempt + 1} failed: {e}", file=sys.stderr)
            if attempt == 0:
                time.sleep(2)
    print(f"_nominatim_reverse failed after retry: {last_error}", file=sys.stderr)
    return None
