#!/usr/bin/env python
"""
Hike-izer data fetcher and analyzer.

Fetches Environmental Data, Hiking Observations, and GPS Track from the JCTsh
Apps Script `action=export` endpoint for a given UTC date range, computes
expected-vs-actual data coverage stats, and computes sun position (elevation,
azimuth, compass direction) sampled along the GPS track. Writes one JSON blob
for the hike-izer Skill to turn into a narrative -- this script does the data
wrangling and math; narrative writing stays with Claude.

Usage:
    python fetch_hike_data.py --start 2026-06-15T00:00:00Z --end 2026-06-29T23:59:59Z \
        --url <APPS_SCRIPT_DEPLOYMENT_URL> --key <API_KEY> --out hike_data.json

Standard library only -- no pip install required.
"""

import argparse
import json
import math
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone


def fetch_sheet(base_url, api_key, sheet, start, end):
    params = {
        'key': api_key,
        'action': 'export',
        'sheet': sheet,
        'start': start,
        'end': end,
    }
    url = base_url + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    if data.get('status') != 'ok':
        raise RuntimeError(f"Export failed for sheet={sheet}: {data.get('message')}")
    return data['rows']


def parse_ts(ts):
    if not ts:
        return None
    ts = ts.replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def to_float(v):
    if v in (None, ''):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Solar position -- NOAA Solar Calculator algorithm (Meeus-based)
# ---------------------------------------------------------------------------

def _julian_day(dt_utc):
    a = (14 - dt_utc.month) // 12
    y = dt_utc.year + 4800 - a
    m = dt_utc.month + 12 * a - 3
    jdn = dt_utc.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    frac = (dt_utc.hour - 12) / 24 + dt_utc.minute / 1440 + dt_utc.second / 86400
    return jdn + frac


def solar_position(dt_utc, lat, lon):
    """Returns (elevation_deg, azimuth_deg) for the given UTC datetime and lat/lon.
    Azimuth is degrees clockwise from north (0=N, 90=E, 180=S, 270=W)."""
    jd = _julian_day(dt_utc)
    jc = (jd - 2451545.0) / 36525.0

    geom_mean_long_sun = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    geom_mean_anom_sun = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    eccent_earth_orbit = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)

    gma_rad = math.radians(geom_mean_anom_sun)
    sun_eq_of_ctr = (
        math.sin(gma_rad) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
        + math.sin(2 * gma_rad) * (0.019993 - 0.000101 * jc)
        + math.sin(3 * gma_rad) * 0.000289
    )

    sun_true_long = geom_mean_long_sun + sun_eq_of_ctr
    sun_app_long = sun_true_long - 0.00569 - 0.00478 * math.sin(math.radians(125.04 - 1934.136 * jc))

    mean_obliq_ecliptic = 23 + (26 + (
        21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))
    ) / 60) / 60
    obliq_corr = mean_obliq_ecliptic + 0.00256 * math.cos(math.radians(125.04 - 1934.136 * jc))

    sun_declin = math.degrees(math.asin(
        math.sin(math.radians(obliq_corr)) * math.sin(math.radians(sun_app_long))
    ))

    var_y = math.tan(math.radians(obliq_corr / 2)) ** 2
    eq_of_time = 4 * math.degrees(
        var_y * math.sin(2 * math.radians(geom_mean_long_sun))
        - 2 * eccent_earth_orbit * math.sin(gma_rad)
        + 4 * eccent_earth_orbit * var_y * math.sin(gma_rad) * math.cos(2 * math.radians(geom_mean_long_sun))
        - 0.5 * var_y * var_y * math.sin(4 * math.radians(geom_mean_long_sun))
        - 1.25 * eccent_earth_orbit * eccent_earth_orbit * math.sin(2 * gma_rad)
    )

    time_offset = eq_of_time + 4 * lon
    true_solar_time = (dt_utc.hour * 60 + dt_utc.minute + dt_utc.second / 60 + time_offset) % 1440

    hour_angle = (true_solar_time / 4 - 180) if true_solar_time >= 0 else (true_solar_time / 4 + 180)

    lat_rad = math.radians(lat)
    decl_rad = math.radians(sun_declin)
    ha_rad = math.radians(hour_angle)

    cos_zenith = (
        math.sin(lat_rad) * math.sin(decl_rad)
        + math.cos(lat_rad) * math.cos(decl_rad) * math.cos(ha_rad)
    )
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    zenith_rad = math.acos(cos_zenith)
    elevation = 90 - math.degrees(zenith_rad)

    az_denom = math.cos(lat_rad) * math.sin(zenith_rad)
    if abs(az_denom) < 1e-6:
        azimuth = 180.0 if lat > 0 else 0.0
    else:
        az_cos = (
            math.sin(lat_rad) * math.cos(zenith_rad) - math.sin(decl_rad)
        ) / az_denom
        az_cos = max(-1.0, min(1.0, az_cos))
        azimuth = math.degrees(math.acos(az_cos))
        if hour_angle > 0:
            azimuth = 360 - azimuth

    return elevation, azimuth


def compass_dir(azimuth):
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    idx = int((azimuth + 11.25) // 22.5) % 16
    return dirs[idx]


def m_to_ft(meters):
    return meters * 3.28084


# ---------------------------------------------------------------------------
# Stats -- computed once here so the narrative-writing step doesn't have to
# re-derive ranges by hand each time. Feet is the primary unit for elevation
# throughout Hike-izer's output, per Joseph's call -- meters isn't reported.
# ---------------------------------------------------------------------------

def _rows_in_hike_sessions(rows, sessions):
    """CARD-0113: rows (GPS or otherwise) whose timestamp falls within any
    is_hike session's own [start, end] window -- lets a stat be scoped to
    the confirmed hike itself rather than the full query window, which can
    include non-hike time. Falls back to returning every row unchanged if
    there are no is_hike sessions (caller is expected to only invoke this
    when hike_confirmed is true)."""
    windows = [(parse_ts(s['start']), parse_ts(s['end'])) for s in sessions if s['is_hike']]
    if not windows:
        return rows
    result = []
    for r in rows:
        ts = parse_ts(r.get('timestamp'))
        if ts is None:
            continue
        if any(start <= ts <= end for start, end in windows):
            result.append(r)
    return result


def compute_stats(env_rows, gps_rows):
    def rng(rows, key):
        vals = [to_float(r.get(key)) for r in rows]
        vals = [v for v in vals if v is not None]
        return {'min': min(vals), 'max': max(vals)} if vals else None

    alt_vals = [to_float(r.get('altitude_m')) for r in gps_rows]
    alt_vals = [v for v in alt_vals if v is not None]
    altitude_ft = (
        {'min': round(m_to_ft(min(alt_vals))), 'max': round(m_to_ft(max(alt_vals))),
         'gain_ft': round(m_to_ft(max(alt_vals) - min(alt_vals)))}
        if alt_vals else None
    )

    return {
        'temp_f': rng(env_rows, 'temp_f'),
        'humidity_pct': rng(env_rows, 'humidity_pct'),
        'pressure_hpa': rng(env_rows, 'pressure_hpa'),
        'uv_index': rng(env_rows, 'uv_index'),
        'battery_v': rng(env_rows, 'battery_v'),
        'altitude_ft': altitude_ft,
    }


# ---------------------------------------------------------------------------
# Coverage analysis
# ---------------------------------------------------------------------------

def _haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in meters between two lat/lon points."""
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


# Hiking-plausibility thresholds. Both must pass for a GPS cluster to be
# classified as a real hike, not just "GPS was active." Tuned conservatively
# (wide walking-pace range, civil-twilight daylight allowance) rather than
# tightly, since false negatives ("that was a hike but got rejected") are worse
# than false positives here -- rejections are reported with reasons, not
# silently dropped, so an overly strict check would just produce more
# "couldn't confirm" days than necessary.
DAYLIGHT_MIN_FRACTION = 0.8       # >=80% of points must be at civil twilight or brighter
DAYLIGHT_ELEVATION_DEG = -6.0     # civil twilight
WALKING_SPEED_MIN_MPS = 0.15      # below this: effectively stationary (camp/parked), not hiking
WALKING_SPEED_MAX_MPS = 3.0       # above this (~6.7 mph sustained): too fast for walking, likely a vehicle

# CARD-0101: a session with no 10-min gap (e.g. hike -> straight into a car,
# no stop) blends walking- and vehicle-pace points into one cluster. These
# control _truncate_trailing_fast_activity()'s detection of a real, sustained
# transition to non-walking pace, as distinct from a brief jog or a single
# noisy GPS point. Tuned 2026-07-29 against a real trailing-drive trace (the
# first attempt, a trailing rolling-median classifier, failed on it -- real
# stop-and-go driving interleaves near-zero speeds at traffic stops among the
# fast ones, which drags a windowed median down for much of the drive; a
# forward-looking count of raw-fast points is robust to that, since it
# doesn't matter how many slow points are interspersed as long as enough
# genuinely fast ones show up within the confirmation window).
TRAILING_ACTIVITY_CONFIRM_WINDOW_MIN = 8.0  # how far forward to look for corroborating fast points
REGIME_MIN_DURATION_MIN = 3.0     # the fast points found must span at least this long -- excludes a brief jog
REGIME_MIN_POINTS = 3             # ...and there must be at least this many of them


def _classify_hike(points):
    """Given one candidate GPS cluster, decide whether it plausibly represents a
    hike (per Joseph's rule: hikes happen in daylight, at walking pace -- not at
    night, not stationary, not vehicle speed). Returns (is_hike, reasons,
    details) -- reasons is a list of human-readable strings explaining any
    rejection; empty if is_hike is True. Never silently drops a cluster --
    every rejection carries its reason for the narrative to report."""
    elevations = []
    for r in points:
        ts = parse_ts(r.get('timestamp'))
        lat, lon = to_float(r.get('lat')), to_float(r.get('lon'))
        if ts is not None and lat is not None and lon is not None:
            elev, _ = solar_position(ts, lat, lon)
            elevations.append(elev)
    daylight_fraction = (
        sum(1 for e in elevations if e > DAYLIGHT_ELEVATION_DEG) / len(elevations)
        if elevations else 0.0
    )

    speeds_mps = []
    for a, b in zip(points, points[1:]):
        ts_a, ts_b = parse_ts(a.get('timestamp')), parse_ts(b.get('timestamp'))
        lat_a, lon_a = to_float(a.get('lat')), to_float(a.get('lon'))
        lat_b, lon_b = to_float(b.get('lat')), to_float(b.get('lon'))
        if None in (ts_a, ts_b, lat_a, lon_a, lat_b, lon_b):
            continue
        dt = (ts_b - ts_a).total_seconds()
        if dt <= 0:
            continue
        speeds_mps.append(_haversine_m(lat_a, lon_a, lat_b, lon_b) / dt)
    speeds_mps.sort()
    have_speed_data = len(speeds_mps) > 0
    median_speed_mps = speeds_mps[len(speeds_mps) // 2] if have_speed_data else None

    reasons = []
    if daylight_fraction < DAYLIGHT_MIN_FRACTION:
        reasons.append(
            f"only {daylight_fraction * 100:.0f}% of GPS points occurred in daylight "
            f"(sun above {DAYLIGHT_ELEVATION_DEG:.0f}deg) -- hikes are expected during "
            f"daylight hours"
        )
    if not have_speed_data:
        reasons.append(
            f"only {len(points)} GPS point(s) in this cluster -- not enough data to "
            f"determine a movement pattern"
        )
    elif median_speed_mps < WALKING_SPEED_MIN_MPS:
        reasons.append(
            f"median movement speed {median_speed_mps:.2f} m/s "
            f"({median_speed_mps * 2.23694:.1f} mph) is too slow to be walking -- "
            f"likely stationary (camp, parked) rather than a hike"
        )
    elif median_speed_mps > WALKING_SPEED_MAX_MPS:
        reasons.append(
            f"median movement speed {median_speed_mps:.2f} m/s "
            f"({median_speed_mps * 2.23694:.1f} mph) is too fast for walking -- "
            f"likely vehicle travel, not a hike"
        )

    details = {
        'daylight_fraction': round(daylight_fraction, 2),
        'median_speed_mps': round(median_speed_mps, 2) if median_speed_mps is not None else None,
        'median_speed_mph': round(median_speed_mps * 2.23694, 1) if median_speed_mps is not None else None,
    }
    return len(reasons) == 0, reasons, details


def _build_session_entry(s, sub_segmented=False, force_reject_reason=None):
    """Build one session's result dict from its points -- shared by the normal
    per-session path and by each CARD-0101 sub-segment, so both report the
    same shape (duration, coverage, distance, classification).

    force_reject_reason: CARD-0101 -- for a trailing block truncated off by
    _truncate_trailing_fast_activity(), skip the normal median-speed
    classification entirely rather than re-running it. The same problem that
    broke median-based classification of the *whole* session (a real drive's
    near-zero traffic-stop points can drag the median back under the walking
    threshold) applies just as much to classifying the truncated block in
    isolation -- we already know why this piece was cut off, so trust that
    reason instead of asking a classifier that's known not to handle
    interleaved stop-and-go pace well."""
    start = parse_ts(s[0]['timestamp'])
    end = parse_ts(s[-1]['timestamp'])
    dur_sec = max(1, (end - start).total_seconds())
    expected = max(1, round(dur_sec / 30))
    if force_reject_reason:
        is_hike, reasons, classify_details = False, [force_reject_reason], None
    else:
        is_hike, reasons, classify_details = _classify_hike(s)

    distance_m = 0.0
    for a, b in zip(s, s[1:]):
        lat_a, lon_a = to_float(a.get('lat')), to_float(a.get('lon'))
        lat_b, lon_b = to_float(b.get('lat')), to_float(b.get('lon'))
        if None in (lat_a, lon_a, lat_b, lon_b):
            continue
        distance_m += _haversine_m(lat_a, lon_a, lat_b, lon_b)

    entry = {
        'start': s[0]['timestamp'],
        'end': s[-1]['timestamp'],
        'duration_minutes': round(dur_sec / 60, 1),
        'points': len(s),
        'expected_points': expected,
        'coverage_pct': round(100 * len(s) / expected, 1),
        'distance_mi': round(distance_m / 1609.34, 2),
        'is_hike': is_hike,
        'rejection_reasons': reasons,
        'classification_details': classify_details,
    }
    if sub_segmented:
        entry['sub_segmented_from_trailing_activity'] = True
    return entry


def _truncate_trailing_fast_activity(points):
    """CARD-0101, redesigned 2026-07-29 against a real trailing-drive trace:
    finds the first point whose raw point-to-point speed exceeds walking pace
    AND is corroborated by at least REGIME_MIN_POINTS more raw-fast points
    within the next TRAILING_ACTIVITY_CONFIRM_WINDOW_MIN minutes, spanning at
    least REGIME_MIN_DURATION_MIN minutes -- confirming a real, sustained
    transition rather than a brief jog or a single noisy GPS point. Truncates
    the session there: everything from that point to the end is treated as
    one trailing non-hike block, regardless of how speed fluctuates
    afterward (e.g. stopping at a traffic light mid-drive). Returns [points]
    unchanged if no sustained transition is found.

    Run unconditionally on every session now, not just ones _classify_hike
    already rejected for excess speed -- a real trace showed a ~7-minute
    drive inside a 138-minute session, far too brief to move the *whole-
    session median* into outright rejection (the old gate), while still
    inflating the reported distance via the plain sum. A first redesign
    attempt used a trailing rolling-median classifier (mirroring the
    original bidirectional version this replaced) and failed on that same
    real trace: genuine stop-and-go driving interleaves several near-zero-
    speed points (traffic stops) among the fast ones, which drags a windowed
    median down for most of the drive's actual duration. Counting raw-fast
    points within a forward window, rather than requiring a windowed median
    to itself read fast, is robust to that -- it doesn't matter how many
    slow points are interspersed as long as enough genuinely fast ones show
    up nearby. One-directional by design, not bidirectional: once a
    transition is confirmed, nothing after it is re-considered as hiking
    data, which also sidesteps misreading a stop-light pause as "back to
    walking" and fragmenting one real drive into several pieces."""
    if len(points) < REGIME_MIN_POINTS:
        return [points]

    ts_list = [parse_ts(p.get('timestamp')) for p in points]
    if any(t is None for t in ts_list):
        return [points]

    # speeds[i] = speed of the interval ending at points[i]; speeds[0] unused
    speeds = [None] * len(points)
    for i in range(1, len(points)):
        lat_a, lon_a = to_float(points[i - 1].get('lat')), to_float(points[i - 1].get('lon'))
        lat_b, lon_b = to_float(points[i].get('lat')), to_float(points[i].get('lon'))
        dt = (ts_list[i] - ts_list[i - 1]).total_seconds()
        if None in (lat_a, lon_a, lat_b, lon_b) or dt <= 0:
            continue
        speeds[i] = _haversine_m(lat_a, lon_a, lat_b, lon_b) / dt

    fast = [s is not None and s > WALKING_SPEED_MAX_MPS for s in speeds]

    n = len(points)
    i = 0
    while i < n:
        if not fast[i]:
            i += 1
            continue
        window_end_epoch = ts_list[i].timestamp() + TRAILING_ACTIVITY_CONFIRM_WINDOW_MIN * 60
        fast_in_window = [
            j for j in range(i, n)
            if ts_list[j].timestamp() <= window_end_epoch and fast[j]
        ]
        if len(fast_in_window) >= REGIME_MIN_POINTS:
            span_min = (ts_list[fast_in_window[-1]].timestamp() - ts_list[fast_in_window[0]].timestamp()) / 60
            if span_min >= REGIME_MIN_DURATION_MIN:
                # speeds[0] (and so fast[0]) is always undefined -- there's no
                # prior point to compute it from -- so the earliest a real
                # transition can be detected is i=1, not i=0. A prefix that
                # short isn't a walking segment worth rescuing either; require
                # at least REGIME_MIN_POINTS points before treating this as a
                # real split, otherwise the whole thing opens already fast
                # (e.g. a genuine all-drive session, CARD-0100) and should
                # stay one single session for _classify_hike to reject as a
                # whole, not a degenerate near-empty "prefix" plus the rest.
                if i < REGIME_MIN_POINTS:
                    return [points]
                return [points[:i], points[i:]]
        i += 1

    return [points]


def _gps_sessions(gps_rows, session_gap_min=10):
    """Split GPS Track rows into discrete candidate sessions, splitting wherever
    the gap between consecutive points exceeds session_gap_min, then classify
    each as a real hike or not (see _classify_hike). GPSLogger only runs during
    actual hikes, not continuously across a multi-day trip, so comparing point
    count against a full-date-range 30s-cadence expectation is misleading
    (produces a scary-looking ~1% "coverage" that isn't a real problem). Session
    detection gives a per-session cadence check instead, which is meaningful."""
    sorted_gps = sorted((r for r in gps_rows if r.get('timestamp')), key=lambda r: r['timestamp'])
    sessions = []
    current = []
    prev_ts = None
    for r in sorted_gps:
        ts = parse_ts(r.get('timestamp'))
        if ts is None:
            continue
        if prev_ts is not None and (ts - prev_ts).total_seconds() / 60 > session_gap_min:
            sessions.append(current)
            current = []
        current.append(r)
        prev_ts = ts
    if current:
        sessions.append(current)

    result = []
    for s in sessions:
        # CARD-0101, extended 2026-07-29: run the trailing-fast-activity
        # check on every session, not just ones already rejected for speed --
        # a short trailing drive (e.g. straight into a car with no 10-min
        # stop) can be too brief to move the whole-session median into
        # outright rejection, while still inflating the reported distance if
        # left in. Truncation only fires on a sustained regime change (see
        # _truncate_trailing_fast_activity), so a normal hike with ordinary
        # pace variation is unaffected.
        segments = _truncate_trailing_fast_activity(s)
        if len(segments) > 1:
            # segments[0] is the walking prefix -- classify normally (it can
            # still be rejected for other reasons, e.g. insufficient
            # daylight). segments[1] is the truncated trailing block -- we
            # already know why it was cut off, so force-reject it rather
            # than re-running median-speed classification on it in
            # isolation, which is exactly the check that's unreliable here
            # (see _build_session_entry's force_reject_reason docstring).
            result.append(_build_session_entry(segments[0], sub_segmented=True))
            result.append(_build_session_entry(
                segments[1], sub_segmented=True,
                force_reject_reason=(
                    "sustained non-walking pace detected partway through this GPS session "
                    "(e.g. driving after the hike ended) -- excluded from the hike's own stats"
                ),
            ))
        else:
            result.append(_build_session_entry(s))
    return result


# ---------------------------------------------------------------------------
# CARD-0110: richer per-point hiking stats (ascent/descent, moving vs.
# stopped time, pace, moving/avg speed) and the elevation+speed chart series.
# All derived from one shared walk over the GPS points so the aggregate
# stats and the chart series can't silently drift from each other.
# ---------------------------------------------------------------------------

# GPS altitude is noisy enough that a naive point-to-point positive/negative
# sum wildly overcounts both ascent and descent. Only count a delta once it
# clears this threshold -- same tuned-constant pattern as WALKING_SPEED_MIN_MPS
# below, not a smoothing pass (simpler, stdlib-only, one knob to retune later
# if it's over/under-filtering on a real hike).
ASCENT_DESCENT_NOISE_FT = 5.0


def _hike_point_series(gps_rows):
    """Sorted per-point series for the confirmed hike's own GPS rows --
    timestamp, cumulative distance (mi), altitude (ft), and the speed (mph)
    of the interval ending at this point (None for the first point, which
    has no prior point to measure an interval against, and for any point
    with a non-positive dt from a duplicate/out-of-order timestamp)."""
    sorted_rows = sorted((r for r in gps_rows if r.get('timestamp')), key=lambda r: r['timestamp'])
    series = []
    cum_dist_m = 0.0
    prev = None
    for r in sorted_rows:
        ts = parse_ts(r.get('timestamp'))
        lat, lon = to_float(r.get('lat')), to_float(r.get('lon'))
        alt_m = to_float(r.get('altitude_m'))
        if ts is None or lat is None or lon is None or alt_m is None:
            continue
        speed_mph, dt_sec = None, None
        if prev is not None:
            dt_sec = (ts - prev['ts']).total_seconds()
            if dt_sec > 0:
                seg_m = _haversine_m(prev['lat'], prev['lon'], lat, lon)
                cum_dist_m += seg_m
                speed_mph = (seg_m / dt_sec) * 2.23694
        series.append({
            'ts': ts, 'lat': lat, 'lon': lon, 'alt_ft': m_to_ft(alt_m),
            'distance_mi': cum_dist_m / 1609.34,
            'speed_mph': speed_mph, 'dt_sec': dt_sec,
        })
        prev = {'ts': ts, 'lat': lat, 'lon': lon}
    return series


def _ascent_descent_ft(series, noise_ft=ASCENT_DESCENT_NOISE_FT):
    ascent = descent = 0.0
    last_counted_alt = series[0]['alt_ft'] if series else None
    for p in series[1:]:
        delta = p['alt_ft'] - last_counted_alt
        if abs(delta) >= noise_ft:
            if delta > 0:
                ascent += delta
            else:
                descent += -delta
            last_counted_alt = p['alt_ft']
    return round(ascent), round(descent)


def _moving_stopped_time_min(series, min_speed_mps):
    """min_speed_mps: the caller's own moving-vs-stationary cutoff (this
    file reuses WALKING_SPEED_MIN_MPS, defined below, rather than a second
    threshold) -- an interval counts as moving if its speed meets or exceeds
    it, stopped otherwise."""
    min_speed_mph = min_speed_mps * 2.23694
    moving_sec = stopped_sec = 0.0
    for p in series:
        if p['dt_sec'] is None or p['speed_mph'] is None:
            continue
        if p['speed_mph'] >= min_speed_mph:
            moving_sec += p['dt_sec']
        else:
            stopped_sec += p['dt_sec']
    return round(moving_sec / 60, 1), round(stopped_sec / 60, 1)


def _session_point_series(gps_rows, sessions):
    """Splits gps_rows (already scoped to is_hike sessions via
    _rows_in_hike_sessions) back into per-session point series, one
    _hike_point_series() per session, using each session's own [start, end]
    window. The flat scoped list on its own carries no session-boundary
    information -- caught on real multi-session data (two separate walks
    hours apart on the same day): a naive sort-and-walk across the whole
    flat list treats the multi-hour gap *between* sessions as one giant
    near-zero-speed "stopped" interval, wildly inflating stopped time and
    (for the chart) drawing a phantom line connecting the end of one walk to
    the start of a different one. Returns a list of non-empty series, one
    per is_hike session that actually had usable points."""
    windows = [(parse_ts(s['start']), parse_ts(s['end'])) for s in sessions if s['is_hike']]
    groups = [[] for _ in windows]
    for r in gps_rows:
        ts = parse_ts(r.get('timestamp'))
        if ts is None:
            continue
        for i, (start, end) in enumerate(windows):
            if start <= ts <= end:
                groups[i].append(r)
                break
    return [s for s in (_hike_point_series(g) for g in groups) if s]


def compute_hike_detail_stats(gps_rows, sessions, distance_mi, duration_min):
    """CARD-0110: ascent_ft/descent_ft/moving_time_min/stopped_time_min/
    pace_min_per_mi/moving_speed_mph/avg_speed_mph -- distance_mi and
    duration_min are the caller's already-computed, session-scoped figures
    (stats['distance_mi'], the confirmed sessions' summed duration), reused
    rather than re-derived here so every figure on the page agrees. Summed
    across each is_hike session independently (see _session_point_series) so
    a gap between two separate sessions on the same day is never counted as
    time spent stopped."""
    all_series = _session_point_series(gps_rows, sessions)
    if not all_series or not distance_mi or not duration_min:
        return {
            'ascent_ft': None, 'descent_ft': None,
            'moving_time_min': None, 'stopped_time_min': None,
            'pace_min_per_mi': None, 'moving_speed_mph': None, 'avg_speed_mph': None,
        }
    ascent_ft = descent_ft = 0
    moving_time_min = stopped_time_min = 0.0
    for series in all_series:
        a, d = _ascent_descent_ft(series)
        m, s = _moving_stopped_time_min(series, WALKING_SPEED_MIN_MPS)
        ascent_ft += a
        descent_ft += d
        moving_time_min += m
        stopped_time_min += s
    moving_time_min = round(moving_time_min, 1)
    stopped_time_min = round(stopped_time_min, 1)
    avg_speed_mph = distance_mi / (duration_min / 60) if duration_min > 0 else None
    moving_speed_mph = distance_mi / (moving_time_min / 60) if moving_time_min > 0 else None
    pace_min_per_mi = duration_min / distance_mi if distance_mi > 0 else None
    return {
        'ascent_ft': ascent_ft, 'descent_ft': descent_ft,
        'moving_time_min': moving_time_min, 'stopped_time_min': stopped_time_min,
        'pace_min_per_mi': round(pace_min_per_mi, 2) if pace_min_per_mi is not None else None,
        'moving_speed_mph': round(moving_speed_mph, 1) if moving_speed_mph is not None else None,
        'avg_speed_mph': round(avg_speed_mph, 1) if avg_speed_mph is not None else None,
    }


def build_chart_series(gps_rows, sessions, max_points=80):
    """CARD-0110: downsampled elevation+speed-vs-distance series for the
    Elevation & Speed chart -- resampled by cumulative distance rather than
    plotting every raw ~30s GPS point, which would make for a cluttered
    hover-target density on a typical hike (see CARD-0110's Planning notes).
    Distance accumulates across session breaks (matching stats['distance_mi'],
    which sums all is_hike sessions), but each session is downsampled and
    endpoint-preserved independently -- same reasoning as
    compute_hike_detail_stats, so the chart never implies movement during the
    gap between two separate sessions. Each session's first point after the
    first carries 'session_break': true so the renderer can start a new line
    segment there instead of connecting it to the prior session's last point.

    CARD-0082: also carries lat/lon per point (already computed by
    _hike_point_series, just not previously passed through) -- this is the
    one shared series the Route Map reads too, so the map and the chart can
    never disagree about what a given point actually is."""
    all_series = _session_point_series(gps_rows, sessions)
    if not all_series:
        return []

    out = []
    dist_offset = 0.0
    for gi, series in enumerate(all_series):
        total_mi = series[-1]['distance_mi']
        if total_mi <= 0 or len(series) <= max_points:
            picked = series
        else:
            step_mi = total_mi / (max_points - 1)
            picked, next_target = [series[0]], step_mi
            for i in range(1, len(series)):
                if series[i]['distance_mi'] >= next_target:
                    picked.append(series[i])
                    next_target += step_mi
            if picked[-1] is not series[-1]:
                picked.append(series[-1])
        for i, p in enumerate(picked):
            out.append({
                'timestamp': p['ts'].isoformat(),
                'distance_mi': round(p['distance_mi'] + dist_offset, 3),
                'altitude_ft': round(p['alt_ft']),
                'speed_mph': round(p['speed_mph'], 1) if p['speed_mph'] is not None else None,
                'lat': round(p['lat'], 6),
                'lon': round(p['lon'], 6),
                'session_break': gi > 0 and i == 0,
            })
        dist_offset += total_mi
    return out


def analyze_coverage(env_rows, gps_rows, obs_rows, start_dt, end_dt):
    # If the requested window extends into the future (e.g. "today," still in
    # progress), cap the "expected" calculation at now -- otherwise a normal,
    # fully-caught-up device looks like it has bad coverage simply because part
    # of the requested day hasn't happened yet. The originally *requested* end
    # is kept separately so the narrative can note the window was truncated.
    now_dt = datetime.now(timezone.utc)
    window_truncated = end_dt > now_dt
    effective_end_dt = min(end_dt, now_dt)

    duration_min = (effective_end_dt - start_dt).total_seconds() / 60

    expected_env = max(1, round(duration_min / 2))
    actual_env = len(env_rows)

    gps_sessions = _gps_sessions(gps_rows)
    actual_gps = len(gps_rows)

    env_with_coords = sum(1 for r in env_rows if r.get('lat') not in (None, ''))
    field_mode_rows = sum(1 for r in env_rows if r.get('rssi_dbm') == 0)

    # Flag gaps > 3x the expected 2-min cadence in Environmental Data
    gaps = []
    sorted_env = sorted((r for r in env_rows if r.get('timestamp')), key=lambda r: r['timestamp'])
    prev_ts = None
    for r in sorted_env:
        ts = parse_ts(r.get('timestamp'))
        if ts is None:
            continue
        if prev_ts is not None:
            gap_min = (ts - prev_ts).total_seconds() / 60
            if gap_min > 6:
                gaps.append({
                    'from': prev_ts.isoformat(),
                    'to': ts.isoformat(),
                    'gap_minutes': round(gap_min, 1),
                })
        prev_ts = ts

    return {
        'duration_hours': round(duration_min / 60, 1),
        'window_truncated_to_now': window_truncated,
        'requested_end': end_dt.isoformat(),
        'effective_end_used_for_expected_calc': effective_end_dt.isoformat(),
        'environmental_data': {
            'expected_readings': expected_env,
            'actual_readings': actual_env,
            'coverage_pct': round(100 * actual_env / expected_env, 1) if expected_env else None,
            'readings_with_gps_coords': env_with_coords,
            'readings_missing_gps_coords': actual_env - env_with_coords,
            'field_mode_readings': field_mode_rows,
            'gaps_over_6min': gaps,
        },
        'gps_track': {
            'total_trackpoints': actual_gps,
            'sessions_detected': len(gps_sessions),
            'hike_confirmed': any(s['is_hike'] for s in gps_sessions),
            'sessions': gps_sessions,
            'note': (
                "GPSLogger only runs during actual hiking sessions, not continuously "
                "across the requested date range, so coverage is reported per detected "
                "session (split wherever a gap exceeds 10 minutes) rather than against "
                "a misleading full-range 30s-cadence expectation. Each session is also "
                "classified as is_hike or not, per Joseph's rule that hikes happen in "
                "daylight at walking pace -- not at night, stationary, or vehicle speed. "
                "Rejected sessions carry rejection_reasons rather than being dropped."
            ),
        },
        'hiking_observations': {
            'count': len(obs_rows),
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--start', required=True, help='ISO 8601 UTC start, e.g. 2026-06-15T00:00:00Z')
    ap.add_argument('--end', required=True, help='ISO 8601 UTC end, e.g. 2026-06-29T23:59:59Z')
    ap.add_argument('--url', required=True, help='Apps Script deployment URL (ends in /exec)')
    ap.add_argument('--key', required=True, help='API_KEY for the Apps Script endpoint')
    ap.add_argument('--out', required=True, help='Path to write the output JSON')
    ap.add_argument('--sun-sample-every', type=int, default=20,
                     help='Compute sun position on every Nth GPS trackpoint (default 20)')
    ap.add_argument('--source', default='hiking-monitor',
                     help='Environmental Data "source" column value to keep (default hiking-monitor). '
                          'The Environmental Data sheet is shared across every JCTsh environmental '
                          'sensor -- without this filter, another device\'s readings (e.g. '
                          'front-porch-temp-sensor) get mixed in and reported as if they were the '
                          'hiking monitor\'s.')
    args = ap.parse_args()

    start_dt = parse_ts(args.start)
    end_dt = parse_ts(args.end)
    if start_dt is None or end_dt is None:
        sys.exit('ERROR: --start/--end must be ISO 8601, e.g. 2026-06-15T00:00:00Z')

    print('Fetching Environmental Data...', file=sys.stderr)
    env_rows_all = fetch_sheet(args.url, args.key, 'Environmental Data', args.start, args.end)
    other_sources = sorted({r.get('source') for r in env_rows_all if r.get('source') != args.source})
    env_rows = [r for r in env_rows_all if r.get('source') == args.source]
    print(f'  {len(env_rows_all)} rows total, {len(env_rows)} from source={args.source!r}'
          + (f' (also saw: {other_sources})' if other_sources else ''), file=sys.stderr)

    print('Fetching Hiking Observations...', file=sys.stderr)
    obs_rows = fetch_sheet(args.url, args.key, 'Hiking Observations', args.start, args.end)
    print(f'  {len(obs_rows)} rows', file=sys.stderr)

    print('Fetching GPS Track...', file=sys.stderr)
    gps_rows = fetch_sheet(args.url, args.key, 'GPS Track', args.start, args.end)
    print(f'  {len(gps_rows)} rows', file=sys.stderr)

    print('Fetching Hike Start Forecast...', file=sys.stderr)
    try:
        forecast_rows = fetch_sheet(args.url, args.key, 'Hike Start Forecast', args.start, args.end)
    except RuntimeError as e:
        # The sheet is self-provisioning (created by environmental-data.gs on
        # first capture) -- until a forecast has ever been captured, it may
        # not exist yet. Treat that as "no forecast for this window," not a
        # hard failure.
        if 'unknown sheet' in str(e):
            forecast_rows = []
        else:
            raise
    print(f'  {len(forecast_rows)} rows', file=sys.stderr)

    coverage = analyze_coverage(env_rows, gps_rows, obs_rows, start_dt, end_dt)

    # Sun position sampled along the GPS track (GPS Track has real lat/lon/alt on
    # every row, unlike Environmental Data where lat/lon correlation can be blank)
    sun_samples = []
    sorted_gps = sorted((r for r in gps_rows if r.get('timestamp')), key=lambda r: r['timestamp'])
    for i, r in enumerate(sorted_gps):
        if i % args.sun_sample_every != 0:
            continue
        ts = parse_ts(r.get('timestamp'))
        lat, lon = to_float(r.get('lat')), to_float(r.get('lon'))
        if ts is None or lat is None or lon is None:
            continue
        elevation, azimuth = solar_position(ts, lat, lon)
        alt_m = to_float(r.get('altitude_m'))
        sun_samples.append({
            'timestamp': r.get('timestamp'),
            'lat': lat, 'lon': lon,
            'alt_ft': round(m_to_ft(alt_m)) if alt_m is not None else None,
            'sun_elevation_deg': round(elevation, 1),
            'sun_azimuth_deg': round(azimuth, 1),
            'sun_direction': compass_dir(azimuth),
            'daylight': elevation > 0,
        })

    # CARD-0113: altitude/elevation-gain scoped to the confirmed hike
    # session's own points, not every GPS row in the query window -- the
    # window can include non-hike time (e.g. sitting in a car before/after
    # a session-narrowed automatic trigger), which would otherwise inflate
    # the reported elevation gain with points that aren't part of the hike.
    altitude_gps_rows = (
        _rows_in_hike_sessions(gps_rows, coverage['gps_track']['sessions'])
        if coverage['gps_track']['hike_confirmed'] else gps_rows
    )
    stats = compute_stats(env_rows, altitude_gps_rows)
    # Sun elevation range + start/end compass direction, for the Data Summary
    # table (CARD-0109) -- moved out of narrative prose, same treatment as
    # every other measured range (temp, humidity, elevation). sun_samples is
    # already chronologically ordered (built by iterating sorted_gps above).
    if sun_samples:
        elevations = [s['sun_elevation_deg'] for s in sun_samples]
        stats['sun_elevation_deg'] = {'min': min(elevations), 'max': max(elevations)}
        stats['sun_direction_start'] = sun_samples[0]['sun_direction']
        stats['sun_direction_end'] = sun_samples[-1]['sun_direction']
    else:
        stats['sun_elevation_deg'] = None
        stats['sun_direction_start'] = None
        stats['sun_direction_end'] = None
    # Total on-trail distance, summed only across sessions classified as a real
    # hike -- not all GPS activity for the day (e.g. driving between
    # trailheads, or GPS drift while stationary at camp, shouldn't count).
    stats['distance_mi'] = (
        round(sum(s['distance_mi'] for s in coverage['gps_track']['sessions'] if s['is_hike']), 2)
        if coverage['gps_track']['hike_confirmed'] else None
    )
    # CARD-0110: ascent/descent, moving-vs-stopped time, pace, moving/avg
    # speed -- same is_hike-session scoping as distance_mi/altitude_ft above,
    # and reuses stats['distance_mi'] plus the summed session duration so
    # every figure on the page is derived from the same numbers, not
    # separately re-measured.
    hike_duration_min = (
        sum(s['duration_minutes'] for s in coverage['gps_track']['sessions'] if s['is_hike'])
        if coverage['gps_track']['hike_confirmed'] else None
    )
    hike_sessions = coverage['gps_track']['sessions']
    stats.update(compute_hike_detail_stats(altitude_gps_rows, hike_sessions, stats['distance_mi'], hike_duration_min))
    chart_series = (
        build_chart_series(altitude_gps_rows, hike_sessions) if coverage['gps_track']['hike_confirmed'] else []
    )

    out = {
        'query': {'start': args.start, 'end': args.end, 'source_filter': args.source},
        'counts': {
            'environmental_data': len(env_rows),
            'environmental_data_other_sources_seen_but_excluded': other_sources,
            'hiking_observations': len(obs_rows),
            'gps_track': len(gps_rows),
            'hike_start_forecast': len(forecast_rows),
        },
        'coverage': coverage,
        'stats': stats,
        'chart_series': chart_series,
        'sun_position_samples': sun_samples,
        'environmental_data': env_rows,
        'hiking_observations': obs_rows,
        'gps_track': gps_rows,
        'hike_start_forecast': forecast_rows,
    }

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)

    print(
        f"Wrote {args.out}: {len(env_rows)} env rows, {len(obs_rows)} observations, "
        f"{len(gps_rows)} GPS points, {len(sun_samples)} sun-position samples, "
        f"{len(forecast_rows)} hike-start forecast row(s).",
        file=sys.stderr,
    )


if __name__ == '__main__':
    main()
