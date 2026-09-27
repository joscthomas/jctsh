#!/usr/bin/env python
"""
Hike-izer place-context gathering (CARD-0108).

Grounds the hike page in real facts about where the hike happened --
deterministic, free, no hallucination risk. OpenStreetMap Nominatim
(street/neighborhood address) + Overpass (named park/school/trail features
and their operator, containing or near the hike's own coordinates).
CARD-0108's own experiment found Nominatim reverse-geocoding alone never
surfaces a park/school name at any zoom level -- Overpass is the piece that
actually answers "what is this place called." Feeds the Location/Nearby
Named Features page sections (CARD-0123), and (via `nominatim_address`)
hike_places.py's own Where fallback (CARD-0311).

CARD-0348, 2026-09-27: this module's research/regional-enrichment layers
(a Claude + web_search call) and the narrative-writing pipeline they only
ever fed have both been retired -- narrative was opt-in-only from the start
(CARD-0123) and Joseph won't use it again. Everything below is the
deterministic base layer alone; stdlib-only, no `anthropic` dependency.
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
# Two independent public Overpass mirrors, tried in order. overpass-api.de
# returned 504 Gateway Timeout on two consecutive real runs several minutes
# apart during CARD-0108's own testing (2026-07-28) -- that gap plus two
# straight failures reads as a sustained outage on that specific instance,
# not a random blip, so a same-server retry wouldn't have helped; a second,
# independently-run mirror (Kumi Systems, speaks the same Overpass QL/
# response format) is the fix that actually addresses what was observed.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
USER_AGENT = "jctsh-hike-izer/1.0 (personal project, https://hikes.jctnet.com)"
# CARD-0112: caps total named-feature queries per hike (route samples +
# distinct photo locations combined) and paces them -- found necessary
# against a real hike (2026-07-29) where an uncapped, back-to-back run
# tripped Overpass's own "Too Many Requests" almost immediately.
# Widened 2026-09-22 (CARD-0323) -- even this cap+pace combination (5
# requests in ~12s from one IP) drew a real 429 from overpass-api.de on
# a later hike. Cadence is the cause, not just something to handle better
# once it happens, so both move: fewer requests, more spacing between them.
MAX_NAMED_FEATURE_QUERIES = 4
NAMED_FEATURE_QUERY_DELAY_S = 6


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


def _first_gps_point(hike_data):
    gps_rows = hike_data.get("gps_track") or []
    if not gps_rows:
        return None
    sorted_rows = sorted(gps_rows, key=lambda r: r.get("timestamp") or "")
    return sorted_rows[0]


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


def _sample_points(points, max_samples=3):
    """Evenly-spaced subset of points (always including the first and last),
    capped at max_samples -- enough to ground named-feature lookups along
    the whole route without one Overpass call per point."""
    if len(points) <= max_samples:
        return points
    step = (len(points) - 1) / (max_samples - 1)
    return [points[round(i * step)] for i in range(max_samples)]


def _dedupe_locations(points, precision=4):
    """Rounds lat/lon to `precision` decimals (~11m at 4 places) and drops
    repeats -- avoids firing near-identical Overpass queries for points
    that are effectively the same spot (e.g. several photos taken standing
    in one place, or a route sample landing close to another)."""
    seen = set()
    result = []
    for p in points:
        lat, lon = p.get("lat"), p.get("lon")
        if lat is None or lon is None:
            continue
        key = (round(lat, precision), round(lon, precision))
        if key in seen:
            continue
        seen.add(key)
        result.append(p)
    return result


def _nominatim_reverse(lat, lon):
    """Raw Nominatim reverse-geocode call -- one HTTP request on the happy
    path, used for both the display_name (fallback location context) and
    the region key (county/state, for regional-context caching), so a
    single hike costs one Nominatim call, not two, out of respect for
    their free-tier usage policy. Retries once on genuine failure only
    (CARD-0323, closing this function's prior single-point-of-failure gap)
    -- this is resilience against a transient drop, never a second routine
    call, so a successful first attempt never triggers a retry. Returns
    the parsed response body, or None."""
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


def named_features(lat, lon, radius_m=250):
    """Named parks, schools, and hiking-route relations containing or near
    the point, with operator where OSM has it. Returns ([], False) on any
    failure -- place context is enrichment, never allowed to block the
    pipeline. The bool is CARD-0348's success signal: True means Overpass
    actually answered (even with zero matches), False means every mirror/
    retry was exhausted -- only the latter is worth trying again later."""
    query = f"""
[out:json][timeout:25];
(
  way(around:{radius_m},{lat},{lon})["amenity"="school"];
  way(around:{radius_m},{lat},{lon})["leisure"="park"];
  relation(around:{radius_m},{lat},{lon})["amenity"="school"];
  relation(around:{radius_m},{lat},{lon})["leisure"="park"];
  relation(around:{radius_m},{lat},{lon})["route"="hiking"];
);
out tags center;
"""
    data = ("data=" + urllib.parse.quote(query)).encode("utf-8")

    # Up to 2 attempts per mirror, 2 mirrors -- a live direct test (2026-07-28)
    # found the second mirror timing out too, on its own, nothing else
    # running -- three timeouts across two independent providers this
    # session. That's broader than one instance being down, so retry alone
    # or fallback alone isn't enough confidence; this combines both. Still
    # not a guarantee -- free public Overpass access has no SLA, and the
    # real safety net is the [] graceful-degradation path below, not this
    # loop succeeding every time.
    #
    # Status-aware since CARD-0323: a 429 means *this* client is being
    # throttled, so a same-host retry cannot succeed and only deepens the
    # rate-limit window -- that case abandons the mirror immediately
    # instead of burning attempt #2 on it. Any other HTTP error still gets
    # one same-host retry, honoring the server's own Retry-After when it
    # sends one instead of guessing at a fixed 3s.
    body = None
    last_error = None
    for url in OVERPASS_URLS:
        for attempt in range(2):
            req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=35) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                last_error = e
                print(f"named_features: {url} attempt {attempt + 1} failed: HTTP {e.code} {e.reason}", file=sys.stderr)
                if e.code == 429:
                    break
                if attempt == 0:
                    time.sleep(_retry_after_seconds(e.headers, default=3))
            except (urllib.error.URLError, ValueError, TimeoutError) as e:
                last_error = e
                print(f"named_features: {url} attempt {attempt + 1} failed: {e}", file=sys.stderr)
                if attempt == 0:
                    time.sleep(3)
        if body is not None:
            break

    if body is None:
        print(f"named_features: all mirrors/retries exhausted, last error: {last_error}", file=sys.stderr)
        return [], False

    seen = set()
    features = []
    for el in body.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        features.append({
            "name": name,
            "type": tags.get("amenity") or tags.get("leisure") or tags.get("route"),
            "operator": tags.get("operator"),
        })
    return features, True


def gather_place_context(hike_data, photos_manifest):
    """Top-level entry point. Returns (dict, ok) -- dict is {'address',
    'nominatim_address', 'named_features'}, structured (not prose), feeding
    the Location/Nearby Named Features page sections and hike_places.py's
    own Where fallback (CARD-0311). ok (CARD-0348) is True only if every
    named_features() Overpass call this hike needed actually got an answer
    (even an empty one) -- False means at least one was rate-limited/timed
    out and is worth retrying wholesale on a later pass, same all-or-nothing
    simplicity as hike_places.gather_hike_places()'s own success signal."""
    empty = {"address": None, "nominatim_address": None, "named_features": []}
    point = _first_gps_point(hike_data)
    if not point or point.get("lat") is None or point.get("lon") is None:
        return empty, True  # nothing to look up, permanently -- not worth retrying
    lat, lon = point["lat"], point["lon"]

    # Address/region are about "where is this hike, broadly" -- the first
    # point is a fine anchor for that regardless of route shape, and using
    # it keeps this to one Nominatim call as before.
    nominatim_body = _nominatim_reverse(lat, lon)
    address = nominatim_body.get("display_name") if nominatim_body else None

    # CARD-0112: named-feature lookup, in contrast, is about "what's actually
    # along the route" -- querying only the first point confirmed wrong on a
    # real hike (a neighborhood loop that starts from the same spot every
    # day surfaced a landmark from a *different* day's hike, since the fixed
    # anchor doesn't reflect which direction that day's hike actually went).
    # Sample a handful of points along the confirmed hike session instead of
    # one, plus every distinct photo capture location when photos exist
    # (step 2) -- the strongest possible signal for what was near a specific
    # photographed moment. Deduped by rounded coordinate first (avoid
    # firing near-identical Overpass queries) and by feature name after.
    #
    # Capped and paced, found necessary against a real hike (2026-07-29):
    # an uncapped run fired 8+ Overpass queries back-to-back and tripped
    # its own "Too Many Requests" almost immediately, on top of Overpass's
    # already-documented flakiness (CARD-0108) -- MAX_NAMED_FEATURE_QUERIES
    # keeps the total request count sane, and the pause between calls gives
    # each a fair shot instead of queuing into the same rate limit. Route
    # samples are prioritized (they define the path); photo locations only
    # fill whatever budget remains.
    hike_points = _hike_session_points(hike_data)
    route_samples = _dedupe_locations(_sample_points(hike_points) if hike_points else [point])
    photo_points = _dedupe_locations((photos_manifest or {}).get("assets", []))
    already_queried = {(round(p["lat"], 4), round(p["lon"], 4)) for p in route_samples}
    photo_samples = [
        p for p in photo_points
        if (round(p["lat"], 4), round(p["lon"], 4)) not in already_queried
    ]
    query_points = (route_samples + photo_samples)[:MAX_NAMED_FEATURE_QUERIES]

    named = []
    seen_names = set()
    ok = True
    for i, p in enumerate(query_points):
        if i > 0:
            time.sleep(NAMED_FEATURE_QUERY_DELAY_S)
        features, point_ok = named_features(p["lat"], p["lon"])
        ok = ok and point_ok
        for f in features:
            if f["name"] not in seen_names:
                seen_names.add(f["name"])
                named.append(f)

    return {
        "address": address,
        "nominatim_address": (nominatim_body or {}).get("address"),
        "named_features": named,
    }, ok
