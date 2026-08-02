#!/usr/bin/env python
"""
CARD-0082: renders the ready-to-embed "Route Map" for a hike-izer HTML page
from fetch_hike_data.py's `chart_series` output -- the same series
CARD-0110's Elevation & Speed chart reads, now also carrying lat/lon.

Uses Leaflet (vendored under components/hike-izer/vendor/leaflet/, not a
live CDN reference) for the map itself: tile layer, pan/zoom, route
polylines, and hover are all real interactivity -- hike-izer's second
deliberate exception to its zero-JS-by-default convention, after CARD-0110's
chart. Route geometry (polyline coordinates, hover hit-target positions) is
baked in from chart_series at generation time; the map's own script only
initializes Leaflet and wires up hover/sync events, it never recomputes a
coordinate.

Standard library only on the Python side -- no pip install required,
matching fetch_hike_data.py. Leaflet itself is a vendored static JS/CSS
asset, not a Python package.

Usage (as a library, called from the hike-izer generation step):
    from build_hike_map import build_map_html
    map_html = build_map_html(hike_data['chart_series'], thunderforest_api_key)
    # splice map_html into html-template.html's {{ROUTE_MAP}}
"""

import json
from datetime import datetime, timedelta, timezone

# See build_hike_chart.py's own DEFAULT_TZ_OFFSET_HOURS comment -- same
# caveat applies here: right for a hike taken from home, not for one taken
# elsewhere. build_map_html() takes an explicit override for that case.
DEFAULT_TZ_OFFSET_HOURS = -7


def _local_time_str(iso_ts, tz_offset_hours):
    """12-hour local time, e.g. '9:14:00 AM'. Same logic as
    build_hike_chart.py's own helper -- duplicated rather than imported, so
    the two modules stay independently generated/testable per this card's
    Planning notes (they're only meant to be coupled at runtime, through the
    two hikeizer-*-hover CustomEvents, not through Python-level imports of
    each other's internals)."""
    dt = datetime.fromisoformat(iso_ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(timezone.utc) + timedelta(hours=tz_offset_hours)
    hour_12 = local.hour % 12 or 12
    ampm = 'AM' if local.hour < 12 else 'PM'
    return f'{hour_12}:{local.minute:02d}:{local.second:02d} {ampm}'


def _esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


THUNDERFOREST_URL_TEMPLATE = 'https://{{s}}.tile.thunderforest.com/outdoors/{{z}}/{{x}}/{{y}}.png?apikey={api_key}'
THUNDERFOREST_ATTRIBUTION = (
    'Maps &copy; <a href="https://www.thunderforest.com">Thunderforest</a>, '
    'Data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
)

# CARD-0133: event markers (photos, hiking observations, bird sightings).
# Simple single-color inline line-art SVGs -- no external icon CDN, matching
# this module's own "vendored, no CDN" convention for Leaflet itself. Colored
# via `currentColor`, driven by the .map-marker-icon--<type> CSS class the
# caller's stylesheet defines (see html-template.html/templating.py's
# _HTML_STYLE) -- this module only supplies the shape, never a hardcoded
# color, keeping it agnostic to which theme/palette it's embedded in.
# Unknown/future event types (per CARD-0082's "generic, not hardcoded types"
# intent) fall back to _DEFAULT_MARKER_ICON, a plain dot.
_MARKER_ICONS = {
    'photo': (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 8h3l1.5-2h7L17 8h3a1 1 0 011 1v9a1 1 0 01-1 1H4a1 1 0 01-1-1V9a1 1 0 011-1z"/>'
        '<circle cx="12" cy="13" r="3.2"/></svg>'
    ),
    'observation': (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 5h16a1 1 0 011 1v9a1 1 0 01-1 1H10l-4.5 3.5V16H4a1 1 0 01-1-1V6a1 1 0 011-1z"/></svg>'
    ),
    'bird': (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M2 13c2.2-3 4.6-3 7 0 2.2-3.6 4.8-4 7.5-2.6M9 13c1.8-2.6 4-2.9 6.2-1.6"/></svg>'
    ),
}
_DEFAULT_MARKER_ICON = '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="6" fill="currentColor"/></svg>'


def _segments(chart_series):
    """Same session_break split build_hike_chart.py uses -- kept as its own
    small copy rather than a shared import, since the two modules are
    deliberately independent (see CARD-0082's Planning notes): they're only
    coupled at runtime through two plain DOM CustomEvents, not through
    Python-level dependencies on each other's internals."""
    segments = []
    for p in chart_series:
        if p.get('session_break') or not segments:
            segments.append([])
        segments[-1].append(p)
    return segments


def _parse_ts(iso_ts):
    dt = datetime.fromisoformat(iso_ts.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# CARD-0133: how far outside every session's own start/end a target
# timestamp may fall and still be trusted as "basically part of that
# session" (clamped to the nearest endpoint rather than interpolated) --
# same 10-minute figure generation.py's own SESSION_QUERY_PADDING already
# uses for "ordinary clock/logging jitter between independent devices", not
# a new guess. Anything farther than this from every session isn't a
# plausible match (e.g. a stray BirdNET export left in the wrong hike's
# staging directory) -- interpolate_position() returns None rather than
# placing a marker based on a wild guess.
MAX_INTERPOLATION_GAP_SEC = 600.0


def interpolate_position(chart_series, target_iso_ts):
    """Turns a bare timestamp into a (lat, lon) tuple for CARD-0133's event
    markers -- e.g. a BirdNET detection, which has a precise time but no GPS
    of its own. Session-safe: groups chart_series the same way _segments()
    does and only ever interpolates within one such group, since a straight
    line across the multi-hour gap between two separate same-day hikes would
    be meaningless. A target that falls within a session's own time range
    gets a real linear interpolation between its two bracketing points; one
    that falls just outside every session gets clamped to that session's
    nearest endpoint (see MAX_INTERPOLATION_GAP_SEC); one nowhere near any
    session returns None -- callers should skip that marker, not guess.

    No existing bracket-and-interpolate helper exists anywhere in this
    codebase to reuse (the closest precedent, environmental-data.gs's
    _gpsLookup(), is nearest-point only) -- this is genuinely new."""
    if not chart_series:
        return None

    target = _parse_ts(target_iso_ts)
    best = None  # (distance_sec, lat, lon) -- smallest distance wins across all sessions

    for seg in _segments(chart_series):
        seg_start, seg_end = _parse_ts(seg[0]['timestamp']), _parse_ts(seg[-1]['timestamp'])

        if target <= seg_start:
            candidate = ((seg_start - target).total_seconds(), seg[0]['lat'], seg[0]['lon'])
        elif target >= seg_end:
            candidate = ((target - seg_end).total_seconds(), seg[-1]['lat'], seg[-1]['lon'])
        else:
            candidate = None
            for a, b in zip(seg, seg[1:]):
                a_ts, b_ts = _parse_ts(a['timestamp']), _parse_ts(b['timestamp'])
                if a_ts <= target <= b_ts:
                    span = (b_ts - a_ts).total_seconds()
                    frac = (target - a_ts).total_seconds() / span if span > 0 else 0.0
                    lat = a['lat'] + (b['lat'] - a['lat']) * frac
                    lon = a['lon'] + (b['lon'] - a['lon']) * frac
                    candidate = (0.0, lat, lon)
                    break

        if candidate is not None and (best is None or candidate[0] < best[0]):
            best = candidate

    if best is None or best[0] > MAX_INTERPOLATION_GAP_SEC:
        return None
    return (best[1], best[2])


def build_map_html(chart_series, thunderforest_api_key, map_id='hikeMap',
                    tz_offset_hours=DEFAULT_TZ_OFFSET_HOURS, markers=None):
    """Returns the full Route Map <section>-ready markup (tooltip slot, map
    container, and the map init + hover-sync script) as one HTML string.
    Returns an empty string if chart_series is empty (hike_confirmed is
    False) -- caller should omit the whole "Route Map" section entirely in
    that case, same "no empty scaffolding" convention as Photos and the
    Elevation & Speed chart.

    `markers` (CARD-0133, optional) is a list of already-positioned, already-
    typed event markers -- this function deliberately doesn't know what a
    "photo" or a "bird sighting" is, it just renders whatever the caller
    (templating.py, which does know) hands it:
        {"type": str, "lat": float, "lon": float,
         "tooltip_html": str, "click_url": str | None}
    `type` looks up an icon via _MARKER_ICONS, falling back to a plain dot
    for anything not in that table -- keeps this generic/extensible per
    CARD-0082's original design intent, one new type needs no code change
    here. `tooltip_html` shows on hover (Leaflet's own .bindTooltip, not the
    route's own chart-sync tooltip-slot mechanism above -- these are
    unrelated pieces of UI on the same map). `click_url`, when present
    (photos only), opens in a new tab on click."""
    if not chart_series:
        return ''

    segments = _segments(chart_series)

    # One JS object per point, index-matched 1:1 with build_hike_chart.py's
    # own data-index attributes -- this array, plus that shared index, is
    # the entire hover-sync contract between the two independently
    # generated modules.
    points_js = []
    for p in chart_series:
        points_js.append({
            'lat': p['lat'], 'lon': p['lon'],
            'time': _local_time_str(p['timestamp'], tz_offset_hours),
            'elevFt': round(p['altitude_ft']),
            'speedMph': round(p['speed_mph'], 1) if p['speed_mph'] is not None else None,
        })

    segments_js = [[[p['lat'], p['lon']] for p in seg] for seg in segments]

    tile_url = THUNDERFOREST_URL_TEMPLATE.format(api_key=_esc(thunderforest_api_key))

    markers_js = [
        {
            'type': m['type'], 'lat': m['lat'], 'lon': m['lon'],
            'tooltipHtml': m['tooltip_html'], 'clickUrl': m.get('click_url'),
        }
        for m in (markers or [])
    ]

    script = f'''<script>
(function () {{
  var points = {json.dumps(points_js)};
  var segments = {json.dumps(segments_js)};
  var tooltipSlot = document.getElementById("{map_id}-tooltip");

  var map = L.map("{map_id}", {{scrollWheelZoom: false}});
  L.tileLayer({json.dumps(tile_url)}, {{
    maxZoom: 18,
    attribution: {json.dumps(THUNDERFOREST_ATTRIBUTION)}
  }}).addTo(map);

  var allLatLngs = [];
  segments.forEach(function (seg) {{
    var line = L.polyline(seg, {{className: "route-line"}}).addTo(map);
    allLatLngs = allLatLngs.concat(seg);
  }});
  map.fitBounds(allLatLngs, {{padding: [24, 24]}});

  var highlight = L.circleMarker(points[0], {{
    className: "route-highlight", radius: 7, opacity: 0, fillOpacity: 0, interactive: false
  }}).addTo(map);

  function showIndex(i) {{
    var p = points[i];
    highlight.setLatLng([p.lat, p.lon]);
    highlight.setStyle({{opacity: 1, fillOpacity: 1}});
    var parts = ['<span class="tt-time">' + p.time + '</span>',
      '<span class="tt-metric elevation">' + p.elevFt + ' ft</span>'];
    if (p.speedMph !== null) {{
      parts.push('<span class="tt-metric speed">' + p.speedMph + ' mph</span>');
    }}
    tooltipSlot.innerHTML = parts.join(" ");
    tooltipSlot.classList.add("is-active");
  }}

  function hide() {{
    highlight.setStyle({{opacity: 0, fillOpacity: 0}});
    tooltipSlot.innerHTML = '<span class="tt-time">Hover the route</span><span class="tt-metric">&mdash;</span>';
    tooltipSlot.classList.remove("is-active");
  }}
  hide();

  points.forEach(function (p, i) {{
    L.circleMarker([p.lat, p.lon], {{radius: 10, opacity: 0, fillOpacity: 0}})
      .addTo(map)
      .on("mouseover", function () {{
        showIndex(i);
        window.dispatchEvent(new CustomEvent("hikeizer-map-hover", {{detail: {{index: i}}}}));
      }})
      .on("mouseout", function () {{
        hide();
        window.dispatchEvent(new CustomEvent("hikeizer-map-unhover"));
      }});
  }});

  // Mirror a hover that started on the Elevation & Speed chart (CARD-0110).
  window.addEventListener("hikeizer-chart-hover", function (e) {{ showIndex(e.detail.index); }});
  window.addEventListener("hikeizer-chart-unhover", hide);

  // CARD-0133: event markers (photos, observations, bird sightings) --
  // entirely separate from the hover-sync machinery above, no interaction
  // with the chart-hover CustomEvents. Icon per type, falling back to a
  // plain dot for anything not in markerIcons (CARD-0082's "generic, not
  // hardcoded types" intent).
  var eventMarkers = {json.dumps(markers_js)};
  var markerIcons = {json.dumps(_MARKER_ICONS)};
  var defaultMarkerIcon = {json.dumps(_DEFAULT_MARKER_ICON)};
  eventMarkers.forEach(function (m) {{
    var iconHtml = markerIcons[m.type] || defaultMarkerIcon;
    var icon = L.divIcon({{
      html: '<span class="map-marker-icon map-marker-icon--' + m.type + '">' + iconHtml + '</span>',
      className: 'map-marker',
      iconSize: [26, 26],
      iconAnchor: [13, 13]
    }});
    var mk = L.marker([m.lat, m.lon], {{icon: icon}}).addTo(map);
    mk.bindTooltip(m.tooltipHtml, {{direction: "top", offset: [0, -14]}});
    if (m.clickUrl) {{
      mk.on("click", function () {{ window.open(m.clickUrl, "_blank"); }});
    }}
  }});
}})();
</script>'''

    return f'''<div class="map-card">
  <div class="chart-tooltip-slot" id="{map_id}-tooltip">
    <span class="tt-time">Hover the route</span>
    <span class="tt-metric">&mdash;</span>
  </div>
  <div id="{map_id}" class="hike-map"></div>
</div>
{script}'''
