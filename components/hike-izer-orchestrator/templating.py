#!/usr/bin/env python
"""
Hike-izer mechanical output builder (CARD-0086 stage 2).

Ports the field-by-field mapping described in
.claude/skills/hike-izer/SKILL.md and components/hike-izer/html-template.html
to Python, for everything except the narrative prose. Given fetch_hike_data.py's
JSON, a list of narrative paragraphs (from the one Claude API call), the local
calendar date being summarized, and the hike's local UTC offset (never
hardcoded Arizona -- see CARD-0086), produces the same HTML a human following
the interactive Skill would produce by hand.

CARD-0134 (2026-08-01): the Route Map (CARD-0082) and Elevation & Speed chart
(CARD-0110) are ported here the same way -- build_hike_map.py/build_hike_chart.py
are deployed copies from components/hike-izer/ (same pattern as
fetch_hike_data.py/fetch_hike_photos.py, see the Dockerfile), imported
directly rather than subprocessed since both are pure functions over
hike_data['chart_series'], which fetch_hike_data.py already computes and this
module already receives -- no new data-fetching step needed.

Standard library only -- matches fetch_hike_data.py's convention (both new
imports below are themselves stdlib-only).
"""

import json
from datetime import datetime, timedelta, timezone

import build_hike_chart
import build_hike_map

NA = "not available"


# ---------------------------------------------------------------------------
# Local-time helpers -- a hike's own UTC offset, supplied by the Tasker
# webhook payload at trigger time, not a hardcoded Arizona assumption.
# ---------------------------------------------------------------------------

def _parse_offset(offset_str):
    sign = 1 if offset_str[0] == "+" else -1
    hh, mm = offset_str[1:].split(":")
    return timedelta(hours=sign * int(hh), minutes=sign * int(mm))


def _to_local(ts_iso, offset_delta):
    if not ts_iso:
        return None
    ts = ts_iso.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc) + offset_delta


def offset_label(offset_str):
    return f"UTC{offset_str}"


def format_date_display(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"


def format_time_local(ts_iso, offset_delta):
    local = _to_local(ts_iso, offset_delta)
    if not local:
        return NA
    hour12 = local.hour % 12 or 12
    return f"{hour12}:{local.minute:02d} {'AM' if local.hour < 12 else 'PM'}"


def format_duration_minutes(total_minutes):
    if total_minutes is None:
        return NA
    total_minutes = round(total_minutes)
    h, m = divmod(total_minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


# ---------------------------------------------------------------------------
# Hero stats / GPS confirmation
# ---------------------------------------------------------------------------

def hike_sessions(coverage):
    return [s for s in coverage["gps_track"]["sessions"] if s["is_hike"]]


def rejected_sibling_sessions(coverage):
    """CARD-0123: sessions detected but NOT classified as the hike -- e.g. a
    trailing drive truncated off the end (CARD-0101) -- alongside a
    genuinely confirmed hike that same day. gps_confirmation_explanation()
    below already covers the case where EVERY session that day was
    rejected; this covers the previously-unsurfaced case where some were
    rejected right alongside a real, confirmed hike. Returns [] if there's
    nothing to report."""
    if not coverage["gps_track"]["hike_confirmed"]:
        return []
    return [s for s in coverage["gps_track"]["sessions"] if not s["is_hike"]]


def gps_confirmation_explanation(coverage):
    sessions = coverage["gps_track"]["sessions"]
    if not sessions:
        return "No GPS activity was recorded for this day."
    parts = []
    for s in sessions:
        if s["rejection_reasons"]:
            reasons = "; ".join(s["rejection_reasons"])
            parts.append(f"session {s['start']} to {s['end']}: {reasons}")
    if not parts:
        return "No GPS session met the criteria for a confirmed hike."
    return "Every GPS session that day was rejected -- " + " | ".join(parts)


def hero_time_display(hike_data, offset_delta):
    # CARD-0111: hero box combines start/end/duration into one figure rather
    # than a bare "Date" (redundant with the H1, which now carries the date --
    # see render_html) and a separate "Duration" box next to it.
    coverage = hike_data["coverage"]
    sessions = hike_sessions(coverage)
    if sessions:
        start_ts = min(s["start"] for s in sessions)
        end_ts = max(s["end"] for s in sessions)
        duration = format_duration_minutes(sum(s["duration_minutes"] for s in sessions))
        return {
            "start": format_time_local(start_ts, offset_delta),
            "end": format_time_local(end_ts, offset_delta),
            "duration": duration,
        }
    obs = hike_data.get("hiking_observations", [])
    if obs:
        times = sorted(o["timestamp"] for o in obs if o.get("timestamp"))
        if len(times) >= 2:
            start = datetime.fromisoformat(times[0].replace("Z", "+00:00"))
            end = datetime.fromisoformat(times[-1].replace("Z", "+00:00"))
            return {
                "start": format_time_local(times[0], offset_delta),
                "end": format_time_local(times[-1], offset_delta),
                "duration": format_duration_minutes((end - start).total_seconds() / 60),
            }
    return {"start": NA, "end": NA, "duration": NA}


def distance_display(stats):
    if stats.get("distance_mi") is None:
        return NA
    return f"{stats['distance_mi']:.1f}"


def elevation_gain_display(stats):
    alt = stats.get("altitude_ft")
    if not alt:
        return NA
    return str(alt["gain_ft"])


# ---------------------------------------------------------------------------
# Weather forecast at hike start (CARD-0083)
# ---------------------------------------------------------------------------

def forecast_view(hike_start_forecast):
    if not hike_start_forecast:
        return {k: NA for k in ("temp_f", "precip_pct", "wind_mph", "humidity_pct", "uv_index")}
    f = hike_start_forecast[0]
    return {
        "temp_f": f"{f['temp_f']:.0f}",
        "precip_pct": f"{f['precip_pct']:.0f}",
        "wind_mph": f"{f['wind_mph']:.0f}",
        "humidity_pct": f"{f['humidity_pct']:.0f}",
        "uv_index": f"{f['uv_index']:.0f}",
    }


# ---------------------------------------------------------------------------
# Data summary table
# ---------------------------------------------------------------------------

def _range_display(rng, unit="", decimals=1):
    if not rng:
        return NA
    fmt = f"{{:.{decimals}f}}"
    return f"{fmt.format(rng['min'])}–{fmt.format(rng['max'])}{unit}"


def _sun_direction_display(stats):
    start = stats.get("sun_direction_start")
    end = stats.get("sun_direction_end")
    if not start or not end:
        return NA
    return start if start == end else f"{start} → {end}"


def category_counts(hiking_observations):
    counts = {}
    for o in hiking_observations:
        cats = _parse_categories(o.get("categories"))
        if not cats:
            counts["uncategorized"] = counts.get("uncategorized", 0) + 1
        for c in cats:
            counts[c] = counts.get(c, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def _parse_categories(raw):
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return []


def data_summary_rows(hike_data):
    # Duration and Elevation Gain deliberately excluded -- both already appear
    # verbatim in the hero stat row at the top of the page (CARD-0109); this
    # table is the hiking-sensor readings (temp/humidity/UV/battery) plus the
    # elevation range and observation breakdown, not a second copy of the
    # hero stats. Sun position has its own table (sun_summary_rows) for the
    # same reason -- it's not a sensor reading, and doesn't belong mixed in.
    stats = hike_data["stats"]
    coverage = hike_data["coverage"]
    rows = [
        ("Temperature", _range_display(stats.get("temp_f"), "°F")),
        ("Humidity", _range_display(stats.get("humidity_pct"), "%")),
        ("UV Index", _range_display(stats.get("uv_index"))),
        ("Battery Voltage", _range_display(stats.get("battery_v"), "V", decimals=2)),
    ]
    counts = category_counts(hike_data.get("hiking_observations", []))
    if counts:
        rows.append(("Observations by Category", ", ".join(f"{k} ({v})" for k, v in counts.items())))
    else:
        rows.append(("Observations by Category", NA))
    return rows


GOLDEN_HOUR_MAX_ELEVATION_DEG = 10  # common rule-of-thumb upper bound for warm, low-angle "golden" light


def sun_summary_rows(stats, sun_position_samples=None, offset_delta=None):
    rows = [
        ("Sun Elevation Range", _range_display(stats.get("sun_elevation_deg"), "°")),
        ("Sun Direction", _sun_direction_display(stats)),
    ]
    # CARD-0123: everything below is derived from sun_position_samples, the
    # same data _sun_direction_display/elevation range already use -- just
    # not surfaced before now. All deterministic (real solar-position math
    # off real GPS timestamps), no API/LLM cost either way.
    samples = sun_position_samples or []
    if not samples:
        return rows

    azimuths = [s["sun_azimuth_deg"] for s in samples if s.get("sun_azimuth_deg") is not None]
    if azimuths:
        rows.append(("Sun Azimuth Range", f"{min(azimuths):.0f}°–{max(azimuths):.0f}°"))

    daylight_count = sum(1 for s in samples if s.get("daylight"))
    rows.append(("Daylight", f"{round(100 * daylight_count / len(samples))}% of sampled points"))

    peak = max(samples, key=lambda s: s.get("sun_elevation_deg", float("-inf")))
    if peak.get("sun_elevation_deg") is not None and offset_delta is not None:
        rows.append(("Peak Sun Elevation Time", format_time_local(peak.get("timestamp"), offset_delta)))

    golden = [
        s for s in samples
        if s.get("sun_elevation_deg") is not None and 0 <= s["sun_elevation_deg"] <= GOLDEN_HOUR_MAX_ELEVATION_DEG
    ]
    if golden and offset_delta is not None:
        golden_sorted = sorted(golden, key=lambda s: s.get("timestamp") or "")
        start = format_time_local(golden_sorted[0].get("timestamp"), offset_delta)
        end = format_time_local(golden_sorted[-1].get("timestamp"), offset_delta)
        rows.append(("Golden Hour", start if start == end else f"{start} – {end}"))
    else:
        rows.append(("Golden Hour", "No"))

    return rows


# ---------------------------------------------------------------------------
# Full observations table
# ---------------------------------------------------------------------------

def observations_table_rows(hiking_observations, offset_delta):
    rows = []
    for o in sorted(hiking_observations, key=lambda r: r.get("timestamp") or ""):
        cats = _parse_categories(o.get("categories"))
        rows.append({
            "time": format_time_local(o.get("timestamp"), offset_delta),
            "observation": o.get("observation", ""),
            "categories": ", ".join(cats) if cats else "—",
        })
    return rows


def _build_event_markers(hike_data, photos_manifest, photos_dir, offset_delta, chart_series, birdnet_occurrences):
    """CARD-0133: assembles the generic marker list build_hike_map.build_map_html()
    renders on the Route Map. Type-specific knowledge (what a photo tooltip
    looks like, which fields an observation shows) lives here, not in
    build_hike_map.py -- that module only ever renders whatever generic
    {type, lat, lon, tooltip_html, click_url} list it's handed, keeping it
    agnostic to what a "photo" or "bird sighting" even is (CARD-0082's
    original "generic, not hardcoded types" design intent)."""
    markers = []

    # Photos -- real per-asset EXIF GPS (fetch_hike_photos.py), can be None
    # when a given asset's EXIF has no GPS at all; skip those rather than
    # guess. Reuses the exact same photos_dir/thumb/original relative-path
    # scheme the Photos gallery section below already uses -- no new file
    # handling.
    if photos_manifest and photos_manifest.get("assets"):
        for a in photos_manifest["assets"]:
            if a.get("lat") is None or a.get("lon") is None:
                continue
            markers.append({
                "type": "photo", "lat": a["lat"], "lon": a["lon"],
                "tooltip_html": f'<img src="{_esc(photos_dir)}/{_esc(a["thumb"])}" alt="">',
                "click_url": f"{photos_dir}/{a['original']}",
            })

    # Observations -- lat/lon already populated at write time
    # (environmental-data.gs's _gpsLookup(), nearest GPS-track point within
    # +-5 min) for anything logged from 2026-07-28 onward (confirmed live
    # against the real sheet, 2026-08-02). Older rows carry lat: ""/lon: ""
    # and simply get no marker -- same "not available, omit" convention used
    # everywhere else on this page, not an error. No interpolation is
    # attempted for this type; if it's not already on the row, it's skipped.
    for o in hike_data.get("hiking_observations", []):
        lat, lon = o.get("lat"), o.get("lon")
        if lat in (None, "") or lon in (None, ""):
            continue
        cats = _parse_categories(o.get("categories"))
        tooltip = (
            f'<strong>{_esc(format_time_local(o.get("timestamp"), offset_delta))}</strong> '
            f'{_esc(o.get("observation", ""))}'
            f'<br><span class="map-marker-tooltip-meta">'
            f'{_esc(", ".join(cats) if cats else "—")} &middot; approximate location</span>'
        )
        markers.append({
            "type": "observation", "lat": float(lat), "lon": float(lon),
            "tooltip_html": tooltip, "click_url": None,
        })

    # Bird occurrences -- only present once step 2 has run and staged a real
    # BirdNET export (same as the existing Wildlife Heard table). Unlike
    # Photos/Observations, BirdNET never carries any GPS of its own -- each
    # occurrence's own representative_timestamp gets interpolated against the
    # GPS track; occurrences too far from any session (interpolate_position()
    # returning None) are skipped rather than guessed.
    for occ in (birdnet_occurrences or []):
        pos = build_hike_map.interpolate_position(chart_series, occ["representative_timestamp"])
        if pos is None:
            continue
        lat, lon = pos
        tooltip = (
            f'<strong>{_esc(occ["common_name"])}</strong> <em>({_esc(occ["scientific_name"])})</em>'
            f'<br><span class="map-marker-tooltip-meta">{round(occ["best_confidence"] * 100)}% confidence '
            f'&middot; heard {occ["count"]}x &middot; approximate location</span>'
        )
        markers.append({
            "type": "bird", "lat": lat, "lon": lon,
            "tooltip_html": tooltip, "click_url": None,
        })

    return markers


def birdnet_table_rows(birdnet_rows, offset_delta, life_list=None, file_stem=None):
    # CARD-0080: birdnet.py already grouped/sorted these by first-detection
    # time and returns raw UTC timestamps -- this is the one place that
    # converts to local, same division of labor as every other time value
    # on this page. common_name/scientific_name pass through as-is: not
    # filtered by taxon (birds/amphibians/mammals/insects all included,
    # Joseph's call) since the model itself doesn't distinguish them either.
    #
    # CARD-0147: is_new -- a species this hike is the first-ever sighting
    # of. Checked via first_heard_file_stem == this hike's own file_stem,
    # NOT "absent from life_list entirely" -- tried that first, reasoning
    # that render_html() always runs before wildlife_life_list.
    # update_from_hike() in generation.py's own pipeline, so a genuinely new
    # species would have no entry yet. True on a hike's very first render,
    # but breaks on any *regeneration* of an already-processed hike (this
    # project regenerates pages in place routinely -- CARD-0140/144/0085 all
    # did it) -- by then update_from_hike() has already run once for this
    # hike, merging its species in, so every one of them would wrongly read
    # "already known" forever after. first_heard_file_stem is a stable fact
    # recorded once per species (update_from_hike() only ever moves it
    # earlier, for genuine backfill, never on a same-hike reprocess) --
    # correct regardless of how many times this page gets rebuilt. life_list
    # is the caller's already-loaded wildlife_life_list.json content,
    # scientific_name -> entry -- keyed the same way that file itself is.
    life_list = life_list or {}
    return [
        {
            "species": r["common_name"],
            "scientific_name": r["scientific_name"],
            "count": r["count"],
            "confidence": f"{round(r['best_confidence'] * 100)}%",
            "time": format_time_local(r["first_timestamp"], offset_delta),
            "is_new": life_list.get(r["scientific_name"], {}).get("first_heard_file_stem") == file_stem,
        }
        for r in birdnet_rows
    ]


# ---------------------------------------------------------------------------
# Coverage panel
# ---------------------------------------------------------------------------

def coverage_table_rows(coverage):
    # CARD-0111: GPS Trackpoints previously hardcoded Expected/Coverage to
    # "not available" -- a leftover placeholder, never actually finished.
    # _build_session_entry already computes expected_points/coverage per
    # session (same 30s-cadence assumption as the note below); sum across
    # every detected session that day (hike or rejected) to match
    # total_trackpoints, which itself counts all of that day's raw GPS rows.
    env = coverage["environmental_data"]
    gps = coverage["gps_track"]
    gps_sessions = gps["sessions"]
    gps_expected = sum(s["expected_points"] for s in gps_sessions)
    gps_actual = gps["total_trackpoints"]
    gps_coverage_pct = round(100 * gps_actual / gps_expected, 1) if gps_expected else None
    rows = [
        ("Environmental Data", str(env["expected_readings"]), str(env["actual_readings"]),
         f"{env['coverage_pct']}%" if env["coverage_pct"] is not None else NA),
        ("GPS Trackpoints (sessions)",
         str(gps_expected) if gps_sessions else NA,
         str(gps_actual),
         f"{gps_coverage_pct}%" if gps_coverage_pct is not None else NA),
    ]
    return rows


def _format_gap_bound(ts_iso, offset_delta, offset_str):
    return f"{format_time_local(ts_iso, offset_delta)} {offset_label(offset_str)}"


def coverage_notes(coverage, offset_delta, offset_str):
    notes = []
    env = coverage["environmental_data"]
    if coverage.get("window_truncated_to_now"):
        # CARD-0111: reworded from a vague "window extends into the future"
        # (technically true but reads like an anomaly) to name the actual
        # generation-time cutoff -- this fires on essentially every
        # automatically-generated page, since generation always runs the same
        # day, well before midnight, so it's worth stating plainly rather than
        # as an alarming-sounding edge case.
        effective_end_local = _format_gap_bound(
            coverage["effective_end_used_for_expected_calc"], offset_delta, offset_str
        )
        notes.append(
            f"Expected-reading counts reflect data through {effective_end_local} "
            f"(when this summary was generated) -- the rest of that calendar day "
            f"hadn't happened yet."
        )
    notes.append(
        f"{env['readings_with_gps_coords']} of {env['actual_readings']} Environmental Data "
        f"readings correlated to a GPS position; {env['readings_missing_gps_coords']} did not."
    )
    if env["gaps_over_6min"]:
        gap_strs = "; ".join(
            f"{_format_gap_bound(g['from'], offset_delta, offset_str)} → "
            f"{_format_gap_bound(g['to'], offset_delta, offset_str)} ({g['gap_minutes']} min)"
            for g in env["gaps_over_6min"]
        )
        notes.append(f"Gaps over 6 minutes in Environmental Data: {gap_strs}.")
    return notes


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------

# Ported verbatim from components/hike-izer/html-template.html's <style> block.
_HTML_STYLE = """
  :root {
    --bg: #f7f5f0;
    --surface: #ffffff;
    --surface-2: #eef0e8;
    --ink: #2b2f27;
    --ink-muted: #5b6156;
    --ink-faint: #8b9186;
    --line: #ddded4;
    --line-strong: #c3c5b7;
    --accent: #4b7a3f;
    --accent-ink: #fbfff8;
    --good: #3f7248;
    --warning: #93701a;
    --warning-bg: #fbf3df;
    --danger: #a8503f;
    --shadow: 0 1px 2px rgba(30,30,20,0.06), 0 6px 16px -8px rgba(30,30,20,0.18);
    --radius: 8px;
    --mono: ui-monospace, "Cascadia Code", "JetBrains Mono", "SF Mono", Consolas, "Liberation Mono", monospace;
    --sans: ui-sans-serif, -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    --chart-elevation: #96723f; --chart-elevation-fill: rgba(150, 114, 63, 0.12); --chart-speed: #3f6a8a; --chart-speed-fill: rgba(63, 106, 138, 0.10);
    --marker-photo: #7a4f8a; --marker-observation: #3f8a7a; --marker-bird: #c17d2e;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #171d16;
      --surface: #212a1f;
      --surface-2: #28331f;
      --ink: #eef1ea;
      --ink-muted: #b7c2ae;
      --ink-faint: #7f8b76;
      --line: #35402f;
      --line-strong: #46543c;
      --accent: #8fc47a;
      --accent-ink: #16210f;
      --good: #7ab982;
      --warning: #e0bd57;
      --warning-bg: #332c17;
      --danger: #e0897a;
      --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 20px -10px rgba(0,0,0,0.5);
      --chart-elevation: #cda978; --chart-elevation-fill: rgba(205, 169, 120, 0.14); --chart-speed: #7bb4d9; --chart-speed-fill: rgba(123, 180, 217, 0.12);
      --marker-photo: #c9a0d9; --marker-observation: #7ad9c4; --marker-bird: #e0a768;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: var(--sans);
    -webkit-font-smoothing: antialiased;
    line-height: 1.55;
  }
  main { max-width: 46rem; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
  h1 { font-size: 1.7rem; margin: 0 0 0.15rem; }
  .subtitle { color: var(--ink-muted); font-size: 0.85rem; margin: 0 0 1.75rem; }
  .subtitle code { font-family: var(--mono); font-size: 0.92em; }

  /* CARD-0147: back-to-home link -- same .top-nav convention already used
     by build_wildlife_index.py's own "&larr; Calendar" link, copied
     verbatim for visual consistency rather than inventing a second style. */
  .top-nav { margin-bottom: 1.25rem; }
  .top-nav a {
    font-size: 0.9rem;
    text-decoration: none;
    color: var(--ink);
    padding: 0.4rem 0.7rem;
    border: 1px solid var(--line);
    border-radius: var(--radius);
  }
  .top-nav a:hover { background: var(--surface-2); }
  .stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: 0.75rem; margin-bottom: 2rem; }
  .stat { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); padding: 0.85rem 1rem; }
  .stat__label { font-family: var(--mono); font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink-muted); margin-bottom: 0.3rem; }
  .stat__value { font-size: 1.35rem; font-weight: 700; }
  .stat__value--na { font-size: 1rem; font-weight: 400; color: var(--ink-faint); font-style: italic; }
  .forecast-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr)); gap: 0.75rem; }
  .stat-row--rich { display: grid; grid-template-columns: repeat(auto-fill, minmax(7.5rem, 1fr)); gap: 0.75rem; }
  .chart-card { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); padding: 1rem 1.15rem 0.85rem; }
  .chart-legend { display: flex; gap: 1.25rem; font-family: var(--mono); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-muted); margin-bottom: 0.6rem; }
  .chart-legend span { display: inline-flex; align-items: center; gap: 0.4rem; }
  .chart-legend i { width: 0.7rem; height: 0.7rem; border-radius: 2px; display: inline-block; }
  .chart-legend .dot-elevation { background: var(--chart-elevation); }
  .chart-legend .dot-speed { background: var(--chart-speed); }
  .chart-tooltip-slot { height: 2.5rem; display: flex; align-items: center; font-family: var(--mono); font-size: 0.82rem; color: var(--ink-faint); font-variant-numeric: tabular-nums; border-bottom: 1px solid var(--line); margin-bottom: 0.5rem; transition: color 0.1s ease; }
  .chart-tooltip-slot.is-active { color: var(--ink); }
  .chart-tooltip-slot .tt-time { color: var(--ink-muted); margin-right: 0.9rem; }
  .chart-tooltip-slot .tt-metric { font-weight: 700; }
  .chart-tooltip-slot .tt-metric.elevation { color: var(--chart-elevation); }
  .chart-tooltip-slot .tt-metric.speed { color: var(--chart-speed); }
  .chart-svg-wrap { width: 100%; overflow-x: auto; }
  svg.hike-chart { width: 100%; height: auto; display: block; cursor: crosshair; }
  .axis-label { font-family: var(--mono); font-size: 9px; fill: var(--ink-faint); }
  .axis-line { stroke: var(--line); stroke-width: 1; }
  .gridline { stroke: var(--line); stroke-width: 1; stroke-dasharray: 2 3; }
  .line-elevation { fill: none; stroke: var(--chart-elevation); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
  .line-elevation-fill { fill: var(--chart-elevation-fill); stroke: none; }
  .line-speed { fill: none; stroke: var(--chart-speed); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
  .hit-target { fill: transparent; cursor: pointer; }
  .hover-dot { r: 4; fill: var(--surface); stroke-width: 2.5; transition: opacity 0.08s ease; pointer-events: none; }
  .hover-dot.elevation { stroke: var(--chart-elevation); }
  .hover-dot.speed { stroke: var(--chart-speed); }
  .hover-guide { stroke: var(--ink-faint); stroke-width: 1; stroke-dasharray: 2 2; pointer-events: none; }
  .map-card { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); padding: 1rem 1.15rem 0.85rem; }
  .hike-map { height: 20rem; border-radius: var(--radius); border: 1px solid var(--line); }
  /* CARD-0147: click-to-expand. .map-expand-btn matches Leaflet's own
     control-button look (white square, border, shadow) rather than
     inventing a new visual language for it. The modal itself holds no map
     markup of its own -- build_hike_map.py's script physically moves the
     *same* Leaflet container into .map-modal-container on open (and back
     out again on close, see that file's own comment for why), so this CSS
     is only ever about the overlay chrome, not map internals. */
  .map-expand-btn {
    background: var(--surface); width: 30px; height: 30px; display: flex;
    align-items: center; justify-content: center; border: none; cursor: pointer;
    color: var(--ink-muted);
  }
  .map-expand-btn:hover { background: var(--surface-2); color: var(--ink); }
  .map-expand-btn svg { width: 16px; height: 16px; }
  .map-modal-backdrop {
    display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    align-items: center; justify-content: center; z-index: 20; padding: 1.5rem;
  }
  .map-modal-backdrop.open { display: flex; }
  .map-modal {
    position: relative; background: var(--surface); border-radius: var(--radius);
    box-shadow: var(--shadow); width: 100%; height: 100%; max-width: 75rem;
    padding: 0.75rem;
  }
  .map-modal-container { width: 100%; height: 100%; }
  .map-modal-container .hike-map { height: 100%; }
  .map-modal-close {
    position: absolute; top: -0.9rem; right: -0.9rem; z-index: 21;
    width: 2rem; height: 2rem; border-radius: 50%; border: 1px solid var(--line);
    background: var(--surface); color: var(--ink); font-size: 1.3rem; line-height: 1;
    cursor: pointer; box-shadow: var(--shadow);
  }
  .map-modal-close:hover { background: var(--surface-2); }
  .route-line { stroke: var(--accent); stroke-width: 3; }
  .route-highlight { fill: var(--surface); stroke: var(--accent); stroke-width: 2.5; }
  .map-marker-icon { display: flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 50%; background: var(--surface); border: 1.5px solid currentColor; box-shadow: var(--shadow); }
  .map-marker-icon svg { width: 16px; height: 16px; }
  .map-marker-icon--photo { color: var(--marker-photo); }
  .map-marker-icon--observation { color: var(--marker-observation); }
  .map-marker-icon--bird { color: var(--marker-bird); }
  .leaflet-tooltip { background: var(--surface); color: var(--ink); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); font-size: 0.82rem; max-width: 12rem; }
  .leaflet-tooltip img { display: block; max-width: 8rem; border-radius: 4px; }
  .leaflet-tooltip-top:before { border-top-color: var(--surface); }
  .map-marker-tooltip-meta { color: var(--ink-faint); font-size: 0.75rem; }
  /* CARD-0085: sun-position gadget -- a Leaflet control (topright), so
     Leaflet's own positioning keeps it clear of the zoom control, no manual
     offsets needed. perspective on the container + preserve-3d/transform-
     origin on the arrow are what let build_hike_map.py's JS-set
     rotateZ(rayDirection) rotateX(tilt) read as a real 3D tilt rather than
     a flat 2D spin. transform-origin is dead center, not the arrow's base --
     found live (Joseph's screenshot) that a bottom-anchored origin was fine
     for the elevation tilt alone, but the *same* anchor also governs the
     compass rotation, so the whole arrow swept around that off-center point
     like a clock hand as azimuth changed, instead of spinning in place like
     a normal compass needle -- a real bug, not a one-off tuning choice. */
  .sun-gadget { background: var(--surface); border: 1px solid var(--line); border-radius: 50%; box-shadow: var(--shadow); width: 2.75rem; height: 2.75rem; margin: 10px; display: flex; align-items: center; justify-content: center; perspective: 60px; }
  .sun-gadget-arrow { width: 20px; height: 20px; color: var(--accent); transform-style: preserve-3d; transform-origin: center; transition: transform 0.15s ease; filter: drop-shadow(0 2px 2px rgba(0,0,0,0.25)); }
  .sun-gadget-arrow svg { width: 100%; height: 100%; overflow: visible; }
  /* CARD-0085 Part B: travel-direction arrows along the route -- plain 2D
     rotate(), each set inline per-marker by build_hike_map.py's JS since the
     bearing differs per arrow (unlike the single sun gadget above, these
     can't share one class-level transform). transparent marker background/
     border keeps only the arrow glyph visible, no circular badge like the
     photo/observation/bird markers -- these are a route-line annotation, not
     a discrete clickable event. */
  .travel-arrow-marker { background: transparent; border: none; }
  /* CARD-0147: smaller + lighter (was 18px/heavier shadow) -- Joseph's
     call, the original read as too visually heavy directly on the route
     line. Now also offset to run parallel with the track rather than on
     it -- see build_hike_map.py's own JS comment for the transform-order
     mechanics (perpendicular offset via translateX() before rotate()). */
  .travel-arrow-icon { width: 14px; height: 14px; color: var(--accent); opacity: 0.85; filter: drop-shadow(0 1px 1px rgba(0,0,0,0.25)); }
  .travel-arrow-icon svg { width: 100%; height: 100%; overflow: visible; }
  .hike-visuals { display: grid; grid-template-columns: 1fr; gap: 1.25rem; margin-bottom: 2.25rem; }
  .hike-visuals section { margin-bottom: 0; }
  @media (min-width: 52rem) { .hike-visuals { grid-template-columns: 1fr 1fr; align-items: start; } .hike-visuals .hike-map { height: 15rem; } }
  @media (prefers-reduced-motion: reduce) { .chart-tooltip-slot, .hover-dot { transition: none; } }
  .callout { background: var(--warning-bg); border: 1px solid var(--warning); border-radius: var(--radius); padding: 1rem 1.15rem; margin-bottom: 1.75rem; font-size: 0.95rem; }
  .callout strong { color: var(--warning); }
  section { margin-bottom: 2.25rem; }
  section > h2 { font-size: 1.05rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--ink-muted); border-bottom: 1px solid var(--line); padding-bottom: 0.4rem; margin: 0 0 1rem; }
  .narrative p { margin: 0 0 1rem; font-size: 1.02rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.92rem; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
  th, td { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--line); }
  thead th { background: var(--surface-2); font-family: var(--mono); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-muted); }
  tbody tr:last-child td { border-bottom: none; }
  tbody tr:nth-child(even) { background: color-mix(in srgb, var(--surface-2) 40%, transparent); }
  .obs-table thead th { position: sticky; top: 0; }
  /* CARD-0147: species heard for the first time ever, on this hike (see
     templating.birdnet_table_rows() for the is_new determination). */
  .new-species-badge {
    display: inline-block; font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.04em; background: var(--accent); color: var(--accent-ink);
    padding: 0.1rem 0.4rem; border-radius: 999px; vertical-align: middle;
  }
  .photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr)); gap: 0.6rem; }
  .photo-item { display: flex; flex-direction: column; border-radius: var(--radius); overflow: hidden; border: 1px solid var(--line); box-shadow: var(--shadow); }
  .photo-item img, .photo-item video { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; display: block; }
  .photo-time { font-size: 0.65rem; color: var(--ink-faint); padding: 0.35rem 0.5rem 0; }
  .photo-caption { font-size: 0.75rem; line-height: 1.3; color: var(--ink-muted); padding: 0.15rem 0.5rem 0.35rem; min-height: 2.6em; }
  .coverage-panel { background: var(--surface-2); border: 1px solid var(--line-strong); border-radius: var(--radius); padding: 1rem 1.15rem; }
  .coverage-panel table { background: transparent; border: none; }
  .coverage-panel thead th { background: transparent; }
  .map-embed { border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow); }
  .map-embed iframe { display: block; width: 100%; border: none; }
  footer { color: var(--ink-faint); font-size: 0.75rem; font-family: var(--mono); margin-top: 2.5rem; border-top: 1px solid var(--line); padding-top: 1rem; }
"""


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _stat_card(label, value, na=False):
    cls = "stat__value stat__value--na" if na else "stat__value"
    return f'<div class="stat"><div class="stat__label">{_esc(label)}</div><div class="{cls}">{_esc(value)}</div></div>'


def render_html(hike_data, narrative_paragraphs, date_str, offset_str, photos_manifest=None,
                 gaia_embed_html=None, file_stem=None, birdnet_rows=None,
                 address=None, named_features=None, thunderforest_api_key=None,
                 birdnet_occurrences=None, life_list=None):
    offset_delta = _parse_offset(offset_str)
    coverage = hike_data["coverage"]
    stats = hike_data["stats"]
    hike_confirmed = coverage["gps_track"]["hike_confirmed"]
    # CARD-0113/CARD-0115: computed here (not just inside photos_section
    # below) since CARD-0133's event markers also need it -- see that
    # section's own comment for why this is keyed on file_stem, not date_str.
    photos_dir = f"{file_stem or date_str}_photos"

    hero_time = hero_time_display(hike_data, offset_delta)
    time_na = hero_time["start"] == NA
    time_value = NA if time_na else f"{hero_time['start']} – {hero_time['end']} ({hero_time['duration']})"
    distance = distance_display(stats)
    elevation_gain = elevation_gain_display(stats)

    stat_row = "".join([
        _stat_card("Time", time_value, na=time_na),
        _stat_card("Distance", f"{distance} mi" if distance != NA else NA, na=(distance == NA)),
        _stat_card("Elevation Gain", f"{elevation_gain} ft" if elevation_gain != NA else NA, na=(elevation_gain == NA)),
    ])

    callout = ""
    if not hike_confirmed:
        callout = (
            f'<div class="callout"><strong>GPS confirmation: unable to confirm.</strong> '
            f'{_esc(gps_confirmation_explanation(coverage))}</div>'
        )

    forecast = forecast_view(hike_data.get("hike_start_forecast"))
    forecast_row = "".join([
        _stat_card("Temp", f"{forecast['temp_f']}°F" if forecast['temp_f'] != NA else NA, na=(forecast['temp_f'] == NA)),
        _stat_card("Precip Chance", f"{forecast['precip_pct']}%" if forecast['precip_pct'] != NA else NA, na=(forecast['precip_pct'] == NA)),
        _stat_card("Wind", f"{forecast['wind_mph']} mph" if forecast['wind_mph'] != NA else NA, na=(forecast['wind_mph'] == NA)),
        _stat_card("Humidity", f"{forecast['humidity_pct']}%" if forecast['humidity_pct'] != NA else NA, na=(forecast['humidity_pct'] == NA)),
        _stat_card("UV Index", forecast['uv_index'], na=(forecast['uv_index'] == NA)),
    ])

    # CARD-0112: step 1 publishes with no narrative at all yet -- omit the
    # whole section rather than show an empty "The Hike" heading over
    # nothing, same convention as the Photos section's own omit-when-empty
    # handling. Step 2 re-renders with real paragraphs once they exist.
    narrative_section = ""
    if narrative_paragraphs:
        narrative_html = "".join(f"<p>{_esc(p)}</p>" for p in narrative_paragraphs)
        narrative_section = f"""
  <section class="narrative">
    <h2>The Hike</h2>
    {narrative_html}
  </section>"""

    # CARD-0112/CARD-0104: Gaia GPS embed, staged by Joseph and inserted by
    # step 2 -- right after the hero stat-row, before Weather Forecast, per
    # CARD-0104's decided placement. Gaia's own inline iframe styles are
    # left untouched; just given the same card framing as the rest of the
    # page via the wrapper below. CARD-0134: no longer populated by
    # generation.py's own calls (the native map below replaced it as this
    # pipeline's default), but left intact -- still renders correctly if a
    # caller ever passes gaia_embed_html again.
    gaia_section = ""
    if gaia_embed_html:
        gaia_section = f"""
  <section>
    <h2>Route Map</h2>
    <div class="map-embed">{gaia_embed_html}</div>
  </section>"""

    # CARD-0134: Route Map (CARD-0082) + Elevation & Speed chart (CARD-0110),
    # side-by-side in .hike-visuals -- same wrapper the interactive Skill's
    # html-template.html uses. Computed from hike_data['chart_series'],
    # which fetch_hike_data.py already produces (shared with the Skill), so
    # this needs no new data-fetching step. Needs zero manual staging,
    # unlike the Gaia embed above, so it's present from step 1 onward --
    # every automatically-generated page gets a real map/chart immediately,
    # not just ones Joseph later enriches by hand.
    offset_hours = offset_delta.total_seconds() / 3600
    chart_series = hike_data.get("chart_series") or []
    chart_html = (
        build_hike_chart.build_chart_html(chart_series, tz_offset_hours=offset_hours) if chart_series else ""
    )
    # CARD-0133: event markers (photos/observations/bird occurrences) --
    # computed regardless of whether there's a map to put them on (cheap),
    # only actually used when map_html ends up non-empty below.
    event_markers = _build_event_markers(
        hike_data, photos_manifest, photos_dir, offset_delta, chart_series, birdnet_occurrences
    )
    map_html = (
        build_hike_map.build_map_html(
            chart_series, thunderforest_api_key, tz_offset_hours=offset_hours, markers=event_markers
        )
        if chart_series and thunderforest_api_key else ""
    )
    hike_visuals_section = ""
    if map_html or chart_html:
        map_part = f'<section><h2>Route Map</h2>{map_html}</section>' if map_html else ""
        chart_part = f'<section><h2>Elevation and Speed</h2>{chart_html}</section>' if chart_html else ""
        hike_visuals_section = f"""
  <div class="hike-visuals">{map_part}{chart_part}
  </div>"""

    # CARD-0123: Location/Nearby Named Features -- previously only ever woven
    # into narrative prose (and so invisible whenever narrative was off).
    # Both come from place_context.py's deterministic, free layers
    # (Nominatim address, Overpass named features), gathered regardless of
    # whether narrative is on. Omit-when-empty, same convention as every
    # other optional section on this page.
    location_section = ""
    if address or named_features:
        address_html = f"<p>{_esc(address)}</p>" if address else ""
        features_html = ""
        if named_features:
            feature_rows = "".join(
                f"<tr><td>{_esc(f['name'])}</td><td>{_esc(f.get('type') or NA)}</td>"
                f"<td>{_esc(f.get('operator') or NA)}</td></tr>"
                for f in named_features
            )
            features_html = f"""
    <table><thead><tr><th>Name</th><th>Type</th><th>Operator</th></tr></thead>
    <tbody>{feature_rows}</tbody></table>"""
        location_section = f"""
  <section>
    <h2>Location</h2>
    {address_html}{features_html}
  </section>"""

    summary_rows = "".join(
        f"<tr><td>{_esc(label)}</td><td>{_esc(value)}</td></tr>"
        for label, value in data_summary_rows(hike_data)
    )

    sun_rows = "".join(
        f"<tr><td>{_esc(label)}</td><td>{_esc(value)}</td></tr>"
        for label, value in sun_summary_rows(stats, hike_data.get("sun_position_samples"), offset_delta)
    )

    # CARD-0123: a session detected but not classified as the hike, sitting
    # right alongside a genuinely confirmed one that same day (e.g. a
    # trailing drive truncated off the end, CARD-0101) -- rejection_reasons
    # was already computed for every session, just never shown on the page
    # unless the ENTIRE day was rejected (see the callout above). Reuses the
    # same warning-styled .callout treatment for visual consistency.
    rejected_section = ""
    rejected = rejected_sibling_sessions(coverage)
    if rejected:
        rejected_items = "".join(
            f"<p>{_esc(format_time_local(s['start'], offset_delta))}"
            f"–{_esc(format_time_local(s['end'], offset_delta))}: "
            f"{_esc('; '.join(s['rejection_reasons']))}</p>"
            for s in rejected
        )
        rejected_section = (
            '<div class="callout"><strong>Other GPS activity that day, not part of this hike:</strong>'
            f'{rejected_items}</div>'
        )

    obs = hike_data.get("hiking_observations", [])
    obs_section = ""
    if obs:
        obs_rows = "".join(
            f"<tr><td>{_esc(r['time'])}</td><td>{_esc(r['observation'])}</td><td>{_esc(r['categories'])}</td></tr>"
            for r in observations_table_rows(obs, offset_delta)
        )
        obs_section = f"""
  <section>
    <h2>Full Observations Log</h2>
    <table class="obs-table">
      <thead><tr><th>Time ({_esc(offset_label(offset_str))})</th><th>Observation</th><th>Categories</th></tr></thead>
      <tbody>{obs_rows}</tbody>
    </table>
  </section>"""

    photos_section = ""
    # CARD-0113/CARD-0115: the photos directory on disk is named after the
    # file stem ('<date>' for the first hike of a day, '<date>-2' etc. for a
    # later one), not the plain date -- a second same-day hike's photos live
    # in '<date>-2_photos/', so referencing '<date>_photos/' here (found live
    # 2026-07-29, broken thumbnails + 404s on click for exactly this case)
    # pointed at the wrong directory whenever more than one hike published on
    # the same day. (photos_dir itself is computed near the top of this
    # function now, CARD-0133 -- event markers need it too.)
    if photos_manifest and photos_manifest.get("assets"):
        items = []
        for a in photos_manifest["assets"]:
            photo_time = format_time_local(a.get("takenAt"), offset_delta)
            time_span = f'<span class="photo-time">{_esc(photo_time)}</span>' if photo_time != NA else ""
            if a["type"] == "VIDEO":
                # Empty photo-caption span here too, even though videos never
                # get one -- keeps every tile's height equal (image + reserved
                # caption space) regardless of media type, same reason images
                # always reserve the space below.
                items.append(
                    f'<a class="photo-item" href="{photos_dir}/{a["original"]}">'
                    f'<video src="{photos_dir}/{a["original"]}" poster="{photos_dir}/{a["thumb"]}" muted></video>'
                    f'{time_span}<span class="photo-caption"></span></a>'
                )
            else:
                # CARD-0107: caption doubles as real alt text -- previously
                # every photo shipped with alt="", a real accessibility gap --
                # and renders visibly below the thumbnail. photo-caption
                # always reserves its space (min-height, even when empty) so
                # grid rows stay aligned regardless of which photos have a
                # caption.
                caption = a.get("caption", "")
                items.append(
                    f'<a class="photo-item" href="{photos_dir}/{a["original"]}">'
                    f'<img src="{photos_dir}/{a["thumb"]}" alt="{_esc(caption)}" loading="lazy">'
                    f'{time_span}<span class="photo-caption">{_esc(caption)}</span></a>'
                )
        photos_section = f"""
  <section>
    <h2>Photos</h2>
    <div class="photo-grid">{"".join(items)}</div>
  </section>"""

    # CARD-0080: table only, no narrative integration (Joseph's call) --
    # omit-when-empty, same convention as every other optional section here.
    # CARD-0147: new_badge built as its own variable, not inlined into the
    # f-string below -- nesting a differently-quoted literal directly inside
    # an f-string's {} expression is fragile across Python versions (only
    # reliably allowed from 3.12's PEP 701 onward), not worth risking for a
    # one-line badge span.
    birdnet_section = ""
    if birdnet_rows:
        new_species_badge = ' <span class="new-species-badge">NEW</span>'
        birdnet_html_rows = "".join(
            f"<tr><td>{_esc(r['species'])}"
            f"{new_species_badge if r['is_new'] else ''}"
            f" <em>({_esc(r['scientific_name'])})</em></td>"
            f"<td>{_esc(r['count'])}</td><td>{_esc(r['confidence'])}</td><td>{_esc(r['time'])}</td></tr>"
            for r in birdnet_table_rows(birdnet_rows, offset_delta, life_list, file_stem)
        )
        birdnet_section = f"""
  <section>
    <h2>Wildlife Heard (BirdNET)</h2>
    <table class="obs-table">
      <thead><tr><th>Species</th><th>Count</th><th>Confidence</th><th>Time ({_esc(offset_label(offset_str))})</th></tr></thead>
      <tbody>{birdnet_html_rows}</tbody>
    </table>
  </section>"""

    coverage_rows = "".join(
        f"<tr><td>{_esc(s)}</td><td>{_esc(e)}</td><td>{_esc(a)}</td><td>{_esc(p)}</td></tr>"
        for s, e, a, p in coverage_table_rows(coverage)
    )
    coverage_note_html = "".join(f"<p>{_esc(n)}</p>" for n in coverage_notes(coverage, offset_delta, offset_str))

    # CARD-0134: vendored Leaflet, same relative path CARD-0082 already
    # deployed to ~/hike-izer-web-app/srv/vendor/leaflet/ -- this pipeline
    # writes its HTML into that same srv/ directory, so no new deployment
    # was needed for the assets themselves, just this reference to them.
    # Omitted entirely when there's no map to show, same convention
    # SKILL.md documents for the interactive Skill's own template.
    leaflet_head = (
        '\n<link rel="stylesheet" href="vendor/leaflet/leaflet.css">'
        '\n<script src="vendor/leaflet/leaflet.js"></script>'
    ) if map_html else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hike Summary for {_esc(format_date_display(date_str))}</title>{leaflet_head}
<style>{_HTML_STYLE}</style>
</head>
<body>
<main>
  <h1>Hike Summary for {_esc(format_date_display(date_str))}</h1>
  <p class="subtitle">Generated automatically by hike-izer-orchestrator &middot; data from the JCTsh Environmental Data pipeline</p>
  <div class="top-nav"><a href="index.html">&larr; All Hikes</a></div>
  <div class="stat-row">{stat_row}</div>
  {callout}
  {rejected_section}
  {hike_visuals_section}
  {gaia_section}
  {location_section}
  <section>
    <h2>Weather Forecast at Hike Start</h2>
    <div class="forecast-row">{forecast_row}</div>
  </section>
  {narrative_section}
  <section>
    <h2>Data Summary</h2>
    <table><tbody>{summary_rows}</tbody></table>
  </section>
  <section>
    <h2>Sun Position</h2>
    <table><tbody>{sun_rows}</tbody></table>
  </section>
  {obs_section}
  {photos_section}
  {birdnet_section}
  <section>
    <h2>Expected vs. Actual Data Coverage</h2>
    <div class="coverage-panel">
      <table>
        <thead><tr><th>Source</th><th>Expected</th><th>Actual</th><th>Coverage</th></tr></thead>
        <tbody>{coverage_rows}</tbody>
      </table>
      {coverage_note_html}
    </div>
  </section>
  <footer>hike-izer-orchestrator</footer>
</main>
</body>
</html>
"""
