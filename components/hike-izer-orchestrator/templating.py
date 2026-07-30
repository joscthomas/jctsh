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

Standard library only -- matches fetch_hike_data.py's convention.
"""

import json
from datetime import datetime, timedelta, timezone

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


def sun_summary_rows(stats):
    return [
        ("Sun Elevation Range", _range_display(stats.get("sun_elevation_deg"), "°")),
        ("Sun Direction", _sun_direction_display(stats)),
    ]


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


def birdnet_table_rows(birdnet_rows, offset_delta):
    # CARD-0080: birdnet.py already grouped/sorted these by first-detection
    # time and returns raw UTC timestamps -- this is the one place that
    # converts to local, same division of labor as every other time value
    # on this page. common_name/scientific_name pass through as-is: not
    # filtered by taxon (birds/amphibians/mammals/insects all included,
    # Joseph's call) since the model itself doesn't distinguish them either.
    return [
        {
            "species": r["common_name"],
            "scientific_name": r["scientific_name"],
            "count": r["count"],
            "confidence": f"{round(r['best_confidence'] * 100)}%",
            "time": format_time_local(r["first_timestamp"], offset_delta),
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
  .stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: 0.75rem; margin-bottom: 2rem; }
  .stat { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); padding: 0.85rem 1rem; }
  .stat__label { font-family: var(--mono); font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink-muted); margin-bottom: 0.3rem; }
  .stat__value { font-size: 1.35rem; font-weight: 700; }
  .stat__value--na { font-size: 1rem; font-weight: 400; color: var(--ink-faint); font-style: italic; }
  .forecast-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr)); gap: 0.75rem; }
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
  .photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr)); gap: 0.6rem; }
  .photo-item { display: flex; flex-direction: column; border-radius: var(--radius); overflow: hidden; border: 1px solid var(--line); box-shadow: var(--shadow); }
  .photo-item img, .photo-item video { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; display: block; }
  .photo-caption { font-size: 0.75rem; line-height: 1.3; color: var(--ink-muted); padding: 0.35rem 0.5rem; min-height: 2.6em; }
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
                 gaia_embed_html=None, file_stem=None, birdnet_rows=None):
    offset_delta = _parse_offset(offset_str)
    coverage = hike_data["coverage"]
    stats = hike_data["stats"]
    hike_confirmed = coverage["gps_track"]["hike_confirmed"]

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
    # page via the wrapper below.
    gaia_section = ""
    if gaia_embed_html:
        gaia_section = f"""
  <section>
    <h2>Route Map</h2>
    <div class="map-embed">{gaia_embed_html}</div>
  </section>"""

    summary_rows = "".join(
        f"<tr><td>{_esc(label)}</td><td>{_esc(value)}</td></tr>"
        for label, value in data_summary_rows(hike_data)
    )

    sun_rows = "".join(
        f"<tr><td>{_esc(label)}</td><td>{_esc(value)}</td></tr>"
        for label, value in sun_summary_rows(stats)
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
    # the same day. Falls back to date_str if file_stem isn't given (should
    # only happen if a caller is missed -- keeps this from hard-crashing).
    photos_dir = f"{file_stem or date_str}_photos"
    if photos_manifest and photos_manifest.get("assets"):
        items = []
        for a in photos_manifest["assets"]:
            if a["type"] == "VIDEO":
                # Empty photo-caption span here too, even though videos never
                # get one -- keeps every tile's height equal (image + reserved
                # caption space) regardless of media type, same reason images
                # always reserve the space below.
                items.append(
                    f'<a class="photo-item" href="{photos_dir}/{a["original"]}">'
                    f'<video src="{photos_dir}/{a["original"]}" poster="{photos_dir}/{a["thumb"]}" muted></video>'
                    f'<span class="photo-caption"></span></a>'
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
                    f'<span class="photo-caption">{_esc(caption)}</span></a>'
                )
        photos_section = f"""
  <section>
    <h2>Photos</h2>
    <div class="photo-grid">{"".join(items)}</div>
  </section>"""

    # CARD-0080: table only, no narrative integration (Joseph's call) --
    # omit-when-empty, same convention as every other optional section here.
    birdnet_section = ""
    if birdnet_rows:
        birdnet_html_rows = "".join(
            f"<tr><td>{_esc(r['species'])} <em>({_esc(r['scientific_name'])})</em></td>"
            f"<td>{_esc(r['count'])}</td><td>{_esc(r['confidence'])}</td><td>{_esc(r['time'])}</td></tr>"
            for r in birdnet_table_rows(birdnet_rows, offset_delta)
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

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hike Summary for {_esc(format_date_display(date_str))}</title>
<style>{_HTML_STYLE}</style>
</head>
<body>
<main>
  <h1>Hike Summary for {_esc(format_date_display(date_str))}</h1>
  <p class="subtitle">Generated automatically by hike-izer-orchestrator &middot; data from the JCTsh Environmental Data pipeline</p>
  <div class="stat-row">{stat_row}</div>
  {callout}
  {gaia_section}
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
