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


def build_map_html(chart_series, thunderforest_api_key, map_id='hikeMap', tz_offset_hours=DEFAULT_TZ_OFFSET_HOURS):
    """Returns the full Route Map <section>-ready markup (tooltip slot, map
    container, and the map init + hover-sync script) as one HTML string.
    Returns an empty string if chart_series is empty (hike_confirmed is
    False) -- caller should omit the whole "Route Map" section entirely in
    that case, same "no empty scaffolding" convention as Photos and the
    Elevation & Speed chart."""
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
