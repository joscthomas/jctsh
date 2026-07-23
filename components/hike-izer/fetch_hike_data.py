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
        start = parse_ts(s[0]['timestamp'])
        end = parse_ts(s[-1]['timestamp'])
        dur_sec = max(1, (end - start).total_seconds())
        expected = max(1, round(dur_sec / 30))
        is_hike, reasons, classify_details = _classify_hike(s)

        distance_m = 0.0
        for a, b in zip(s, s[1:]):
            lat_a, lon_a = to_float(a.get('lat')), to_float(a.get('lon'))
            lat_b, lon_b = to_float(b.get('lat')), to_float(b.get('lon'))
            if None in (lat_a, lon_a, lat_b, lon_b):
                continue
            distance_m += _haversine_m(lat_a, lon_a, lat_b, lon_b)

        result.append({
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
        })
    return result


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

    stats = compute_stats(env_rows, gps_rows)
    # Total on-trail distance, summed only across sessions classified as a real
    # hike -- not all GPS activity for the day (e.g. driving between
    # trailheads, or GPS drift while stationary at camp, shouldn't count).
    stats['distance_mi'] = (
        round(sum(s['distance_mi'] for s in coverage['gps_track']['sessions'] if s['is_hike']), 2)
        if coverage['gps_track']['hike_confirmed'] else None
    )

    out = {
        'query': {'start': args.start, 'end': args.end, 'source_filter': args.source},
        'counts': {
            'environmental_data': len(env_rows),
            'environmental_data_other_sources_seen_but_excluded': other_sources,
            'hiking_observations': len(obs_rows),
            'gps_track': len(gps_rows),
        },
        'coverage': coverage,
        'stats': stats,
        'sun_position_samples': sun_samples,
        'environmental_data': env_rows,
        'hiking_observations': obs_rows,
        'gps_track': gps_rows,
    }

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)

    print(
        f"Wrote {args.out}: {len(env_rows)} env rows, {len(obs_rows)} observations, "
        f"{len(gps_rows)} GPS points, {len(sun_samples)} sun-position samples.",
        file=sys.stderr,
    )


if __name__ == '__main__':
    main()
