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
from datetime import datetime


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


# ---------------------------------------------------------------------------
# Coverage analysis
# ---------------------------------------------------------------------------

def _gps_sessions(gps_rows, session_gap_min=10):
    """Split GPS Track rows into discrete hiking sessions, splitting wherever the
    gap between consecutive points exceeds session_gap_min. GPSLogger only runs
    during actual hikes, not continuously across a multi-day trip, so comparing
    point count against a full-date-range 30s-cadence expectation is misleading
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
        result.append({
            'start': s[0]['timestamp'],
            'end': s[-1]['timestamp'],
            'duration_minutes': round(dur_sec / 60, 1),
            'points': len(s),
            'expected_points': expected,
            'coverage_pct': round(100 * len(s) / expected, 1),
        })
    return result


def analyze_coverage(env_rows, gps_rows, obs_rows, start_dt, end_dt):
    duration_min = (end_dt - start_dt).total_seconds() / 60

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
            'sessions': gps_sessions,
            'note': (
                "GPSLogger only runs during actual hiking sessions, not continuously "
                "across the requested date range, so coverage is reported per detected "
                "session (split wherever a gap exceeds 10 minutes) rather than against "
                "a misleading full-range 30s-cadence expectation."
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
    args = ap.parse_args()

    start_dt = parse_ts(args.start)
    end_dt = parse_ts(args.end)
    if start_dt is None or end_dt is None:
        sys.exit('ERROR: --start/--end must be ISO 8601, e.g. 2026-06-15T00:00:00Z')

    print('Fetching Environmental Data...', file=sys.stderr)
    env_rows = fetch_sheet(args.url, args.key, 'Environmental Data', args.start, args.end)
    print(f'  {len(env_rows)} rows', file=sys.stderr)

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
        sun_samples.append({
            'timestamp': r.get('timestamp'),
            'lat': lat, 'lon': lon, 'alt_m': to_float(r.get('altitude_m')),
            'sun_elevation_deg': round(elevation, 1),
            'sun_azimuth_deg': round(azimuth, 1),
            'sun_direction': compass_dir(azimuth),
            'daylight': elevation > 0,
        })

    out = {
        'query': {'start': args.start, 'end': args.end},
        'counts': {
            'environmental_data': len(env_rows),
            'hiking_observations': len(obs_rows),
            'gps_track': len(gps_rows),
        },
        'coverage': coverage,
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
