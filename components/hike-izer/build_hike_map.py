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

# CARD-0085: sun-position gadget -- solid/filled bold arrow (Joseph's call,
# 2026-08-08: wanted a chunkier, more visible glyph than the thin hollow
# line-art originally used here). Points "up" (north, 0deg) at rest. Hand-
# drawn (not traced from any stock asset) as one filled path: a wide
# triangular head (wings at x=4/x=20, apex at y=2) over a thick rectangular
# shaft (x=9-15, down to y=22) -- deliberately kept vertically balanced
# around the viewBox's y=12 center (spans y=2 to y=22, same ~20px extent the
# old line-art arrow had), NOT anchored to the bottom edge: templating.py's
# `.sun-gadget-arrow` CSS pivots this on `transform-origin: center`, not the
# arrow's base (see that file's own comment for why -- a bottom anchor
# looked fine for the elevation tilt alone, but the same anchor also governs
# the compass rotation, causing the whole arrow to sweep like a clock hand
# instead of spinning in place). A shape anchored at its own base instead of
# balanced around center would look off-pivot under that rotation.
_SUN_GADGET_ARROW_SVG = (
    '<svg viewBox="0 0 24 24" fill="currentColor">'
    '<path d="M9 22 L9 13 L4 13 L12 2 L20 13 L15 13 L15 22 Z"/></svg>'
)

# CARD-0147: 8-point sunburst behind the gadget's gold circle, per Joseph's
# reference image (a classic sun icon: circle plus radiating pointed rays) --
# the plain gold circle alone read as "a warm badge", not specifically a sun.
# Points computed offline (r_outer=47, r_inner=25 in a 0-100 viewBox,
# 8 spikes) rather than hand-typed, then pasted here as a static constant --
# no runtime math needed, this shape never changes. r_inner is deliberately
# smaller than the circle's own radius (~29 viewBox units once the two
# elements' real pixel sizes are compared) so the valleys between spikes sit
# fully underneath the circle and only the tips poke out -- see the DOM
# structure in the sun-gadget control below for how that layering is done
# (paint order, not z-index: a child element's own background can never
# paint behind its parent's, so the rays and the circle are siblings under a
# plain wrapper, rays first, opaque circle second).
_SUN_GADGET_RAYS_SVG = (
    '<svg viewBox="0 0 100 100">'
    '<polygon points="50.0,3.0 59.6,26.9 83.2,16.8 73.1,40.4 97.0,50.0 73.1,59.6 '
    '83.2,83.2 59.6,73.1 50.0,97.0 40.4,73.1 16.8,83.2 26.9,59.6 3.0,50.0 26.9,40.4 '
    '16.8,16.8 40.4,26.9" fill="#f7941e"/></svg>'
)

# CARD-0085 Part B: travel-direction arrows placed along the route line
# itself (Joseph: "It's not a row but a tiny arrow on the map" -- a table
# row was tried first and explicitly rejected in favor of this). Same
# hollow-arrow visual vocabulary as _SUN_GADGET_ARROW_SVG (this map's one
# other rotating-arrow indicator) but plain 2D -- no perspective/tilt, since
# travel direction has no elevation-angle analog. Points "up" (0deg) at rest,
# rotated in-plane via a plain CSS rotate() to each point's own
# travel_bearing_deg.
# CARD-0147: lighter stroke (was 2.5) -- Joseph's call, the original read as
# too visually heavy sitting directly on the route line.
_TRAVEL_ARROW_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="12" y1="19" x2="12" y2="7"/>'
    '<path d="M7 12 L12 5 L17 12"/></svg>'
)

# CARD-0147: perpendicular offset (px, in the marker's own rotated local
# frame) so arrows read as running parallel to the track instead of sitting
# directly on top of it, obscuring the route line itself. Applied via CSS
# transform order (see the JS below) -- Joseph's call: a consistent *rule*
# (always offset to the same side, relative to each arrow's own direction of
# travel) is what matters, not a single fixed absolute compass side, which
# would look arbitrary as the route curves.
# CARD-0147 (second pass): the rotation angle itself moved from the stored
# travel_bearing_deg (a real GPS-reported heading) to the drawn route line's
# own local on-screen tangent, computed client-side from points[] the same
# way the event-marker callouts find their offset direction. A real compass
# heading can visibly diverge from the straight segment between two plotted
# points -- device orientation noise, a pause, a tight switchback between
# samples -- and Joseph's requirement ("always parallel to the track, never
# touching it") is a promise about what's drawn, not about the device's
# instantaneous heading. Deriving the angle from the same points[] the
# polyline itself is drawn from is the only way to guarantee that promise
# unconditionally rather than relying on the two happening to agree.
TRAVEL_ARROW_OFFSET_PX = 9

# How many arrows to place along the whole route, regardless of hike length
# or point density -- Joseph confirmed "arrows, more than 1" (i.e. several
# spaced along the trail, not a single indicator). Small enough to stay
# readable on a phone-width map, large enough to actually convey the route's
# direction changes.
TRAVEL_ARROW_COUNT = 10


def _select_travel_arrow_points(chart_series):
    """Evenly-spaced subset of chart_series points that carry a real
    GPS-reported bearing (older data, or a GPSLogger config not sending
    %DIRECTION, leaves travel_bearing_deg None -- those points are skipped
    entirely), used only to decide *where* an arrow gets placed -- a point
    with no reported heading is treated as not confirmed as a real waypoint
    for this feature, even though its lat/lon is perfectly usable. The
    bearing value itself is no longer used for the arrow's rotation (see
    CARD-0147, below) -- kept only as this presence/absence gate. Returns
    each match as `(index, point)`, `index` being its position in the full
    chart_series/points[] array (the two are 1:1, same order), needed so the
    JS side can look up the point's real on-screen neighbors and compute a
    rotation that's guaranteed to match the drawn route line, rather than
    re-deriving lat/lon from the point alone. Returns [] if no point in the
    whole hike has one, same "no empty scaffolding" convention as the rest
    of this module -- caller just renders zero arrows."""
    candidates = [(i, p) for i, p in enumerate(chart_series) if p.get('travel_bearing_deg') is not None]
    if not candidates:
        return []
    if len(candidates) <= TRAVEL_ARROW_COUNT:
        return candidates
    step = (len(candidates) - 1) / (TRAVEL_ARROW_COUNT - 1)
    indices = sorted(set(round(i * step) for i in range(TRAVEL_ARROW_COUNT)))
    return [candidates[i] for i in indices]


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
            'sunAzimuth': p.get('sun_azimuth_deg'),
            'sunElevation': p.get('sun_elevation_deg'),
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

    # 'idx' is the point's own position in points[] (chart_series and
    # points[] are 1:1) -- the JS side uses it to look up the point's real
    # on-screen neighbors and derive a rotation angle straight from the
    # drawn route line, not from 'bearing' (kept only to select *which*
    # points get an arrow at all -- see _select_travel_arrow_points).
    travel_arrows_js = [
        {'idx': i, 'lat': p['lat'], 'lon': p['lon']}
        for i, p in _select_travel_arrow_points(chart_series)
    ]

    script = f'''<script>
(function () {{
  var points = {json.dumps(points_js)};
  var segments = {json.dumps(segments_js)};
  var tooltipSlot = document.getElementById("{map_id}-tooltip");

  // CARD-0147: zoomSnap (Leaflet default: 1, whole-number-only zoom levels)
  // lowered so fitBounds() can pick the exact best-fit zoom instead of
  // rounding down to the nearest whole step (which leaves unused padding
  // any time the ideal fit falls between two integer levels), and so
  // scroll/pinch zoom feels continuous rather than snapping in visible
  // jumps. 0.25 rather than 0 (fully continuous) -- map tiles are only
  // ever rendered at specific zoom levels, so fully continuous zoom means
  // more of the view is CSS-upscaled/blurry between native tile levels;
  // 0.25 is a reasonable middle ground, smooth in practice without giving
  // up much tile sharpness.
  var map = L.map("{map_id}", {{scrollWheelZoom: false, zoomSnap: 0.25}});
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

  // CARD-0085: sun-position gadget, a proper Leaflet control (not a raw
  // absolutely-positioned div) so it's placed in a map corner the same safe,
  // collision-free way Leaflet's own zoom control is -- no manual z-index
  // guessing.
  //
  // Transform order matters here, confirmed live (Joseph found a real
  // hike whose arrow pointed correctly east but showed zero 3D tilt):
  // "rotateX(tilt) rotateZ(azimuth)" -- tilt applied *outermost*, in the
  // world/screen frame -- foreshortens correctly for a N/S-pointing arrow,
  // but for an azimuth near 90/270 (E/W) the rotateZ has already spun the
  // arrow's shaft to align almost exactly with the very axis rotateX pivots
  // around, so rotateX can't shorten it at all (rotating a stick around its
  // own long axis doesn't make it look shorter). Verified by hand via the
  // actual rotation matrices, not just guessed. Fix: "rotateZ(azimuth)
  // rotateX(tilt)" -- rotateX applies *innermost* now, tilting the arrow
  // while it's still in its own rest orientation (shaft along the axis
  // rotateX actually foreshortens), and rotateZ then spins that already-
  // foreshortened shape to point at the compass bearing -- a pure in-plane
  // spin preserves whatever length the tilt already produced, regardless of
  // azimuth.
  //
  // TILT_EXAGGERATION: a literal elevation_deg tilt is real physics but
  // visually subtle for most of a hike's actual elevation range (e.g. 24
  // degrees only foreshortens to ~91% of full length -- barely perceptible
  // at icon size) -- exaggerated so the gadget reads clearly at a glance,
  // which is the point of it, over strict physical accuracy. Capped short
  // of 90 so the arrow never quite vanishes edge-on.
  var TILT_EXAGGERATION = 2.2;

  var SunGadgetControl = L.Control.extend({{
    options: {{position: "topright"}},
    onAdd: function () {{
      var container = L.DomUtil.create("div", "sun-gadget");
      container.innerHTML =
        '<div class="sun-gadget-rays">' + {json.dumps(_SUN_GADGET_RAYS_SVG)} + '</div>' +
        '<div class="sun-gadget-core"><div class="sun-gadget-arrow">' + {json.dumps(_SUN_GADGET_ARROW_SVG)} + '</div></div>';
      L.DomEvent.disableClickPropagation(container);
      return container;
    }}
  }});
  var sunGadget = new SunGadgetControl().addTo(map);
  var sunArrowEl = sunGadget.getContainer().querySelector(".sun-gadget-arrow");

  function updateSunGadget(p) {{
    if (p.sunAzimuth == null || p.sunElevation == null) return;
    var tilt = Math.max(0, Math.min(85, p.sunElevation * TILT_EXAGGERATION));
    // CARD-0085: the arrow represents the direction of the sun's *rays* --
    // which way the light is shining, i.e. away from the sun -- not the
    // direction to look to find the sun in the sky. Those are opposite:
    // a sun sitting in the east shines its light toward the west. Confirmed
    // wrong by Joseph on a real hike (sun_azimuth_deg 89.4, arrow pointed
    // east -- should point west, the direction the light actually travels).
    var rayDirection = (p.sunAzimuth + 180) % 360;
    sunArrowEl.style.transform = "rotateZ(" + rayDirection + "deg) rotateX(" + tilt + "deg)";
  }}

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
    updateSunGadget(p);
  }}

  function hide() {{
    highlight.setStyle({{opacity: 0, fillOpacity: 0}});
    tooltipSlot.innerHTML = '<span class="tt-time">Hover the route</span><span class="tt-metric">&mdash;</span>';
    tooltipSlot.classList.remove("is-active");
    updateSunGadget(points[0]); // default/rest state: the hike's own start
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
  //
  // CARD-0147: markers are no longer plotted at their real lat/lon directly
  // -- found live (Joseph, both a real photo and a real screenshot) that
  // several markers can legitimately share nearly the same real position
  // (e.g. multiple BirdNET detections logged seconds apart while
  // stationary), and any real-world-distance-based separation is
  // fundamentally zoom-dependent: the same few meters of offset reads as
  // plenty of separation zoomed in, and as total overlap zoomed out. Fixed
  // by decoupling display position from geography entirely: each marker
  // renders as a "callout" nudged into the open space beside the route (a
  // fixed *pixel* offset, perpendicular to the route's own local direction
  // at the nearest point -- reusing the same rotate-90-degrees idea the
  // travel arrows already use, just computed in JS against projected pixel
  // coordinates instead of CSS transforms), with further pixel-space
  // spreading for any callouts that would still land close together.
  // Recomputed on every zoomend/moveend, since a fixed pixel offset only
  // stays "off the route" if it's re-derived against the *current*
  // projection -- it would drift arbitrarily relative to the route
  // otherwise. The real point itself is never shown by default; hovering a
  // callout draws a thin leader line back to it and highlights it (reusing
  // the same circleMarker visual language as the chart-hover `highlight`
  // dot above), so the association is only made explicit on demand rather
  // than cluttering the map permanently.
  var eventMarkers = {json.dumps(markers_js)};
  var markerIcons = {json.dumps(_MARKER_ICONS)};
  var defaultMarkerIcon = {json.dumps(_DEFAULT_MARKER_ICON)};
  var MARKER_OFFSET_PX = 22;
  var MARKER_CLUSTER_PX = 18;
  var MARKER_SPREAD_STEP_PX = 16;
  var markerRealLatLngs = eventMarkers.map(function (m) {{ return L.latLng(m.lat, m.lon); }});
  var markerLayers = []; // {{leafletMarker, leaderLine, highlightCircle}}

  function nearestPointIndex(latlng) {{
    var best = 0, bestDist = Infinity;
    for (var i = 0; i < points.length; i++) {{
      var dLat = points[i].lat - latlng.lat, dLon = points[i].lon - latlng.lng;
      var d = dLat * dLat + dLon * dLon;
      if (d < bestDist) {{ bestDist = d; best = i; }}
    }}
    return best;
  }}

  // Perpendicular unit vector (in screen pixels) to the route's own local
  // direction at a given points[] index -- used to push event-marker
  // callouts off to the side of the route. Shares its a/b neighbor lookup
  // with tangentAngleDeg() below (the travel arrows' own equivalent), both
  // reading the route's actual on-screen direction straight from points[]
  // rather than any separately-stored bearing value.
  function perpendicularPx(idx) {{
    var a = points[Math.max(0, idx - 1)];
    var b = points[Math.min(points.length - 1, idx + 1)];
    var p1 = map.latLngToContainerPoint([a.lat, a.lon]);
    var p2 = map.latLngToContainerPoint([b.lat, b.lon]);
    var dx = p2.x - p1.x, dy = p2.y - p1.y;
    var len = Math.sqrt(dx * dx + dy * dy) || 1;
    return {{x: -dy / len, y: dx / len}};
  }}

  // CSS-rotate degrees (0 = up, clockwise -- matching how the travel-arrow
  // glyph is drawn pointing "up" at rest) for the route's own local
  // on-screen direction at a given points[] index. atan2(dx, -dy): screen
  // y grows downward, so "up" is (0,-1) -- swapping/negating the usual
  // atan2(y, x) arguments like this measures the angle clockwise from that
  // "up" vector directly, matching what CSS rotate() expects with no
  // separate conversion step.
  function tangentAngleDeg(idx) {{
    var a = points[Math.max(0, idx - 1)];
    var b = points[Math.min(points.length - 1, idx + 1)];
    var p1 = map.latLngToContainerPoint([a.lat, a.lon]);
    var p2 = map.latLngToContainerPoint([b.lat, b.lon]);
    var dx = p2.x - p1.x, dy = p2.y - p1.y;
    return Math.atan2(dx, -dy) * 180 / Math.PI;
  }}

  function layoutEventMarkers() {{
    markerLayers.forEach(function (layer) {{
      map.removeLayer(layer.leafletMarker);
      if (layer.leaderLine) map.removeLayer(layer.leaderLine);
      if (layer.highlightCircle) map.removeLayer(layer.highlightCircle);
    }});
    markerLayers = [];

    var placedPx = [];
    eventMarkers.forEach(function (m, i) {{
      var realLatLng = markerRealLatLngs[i];
      var realPx = map.latLngToContainerPoint(realLatLng);
      var dir = perpendicularPx(nearestPointIndex(realLatLng));
      var offset = MARKER_OFFSET_PX;
      var calloutPx = L.point(realPx.x + dir.x * offset, realPx.y + dir.y * offset);
      var tries = 0;
      while (tries < 8 && placedPx.some(function (p) {{ return calloutPx.distanceTo(p) < MARKER_CLUSTER_PX; }})) {{
        offset += MARKER_SPREAD_STEP_PX;
        calloutPx = L.point(realPx.x + dir.x * offset, realPx.y + dir.y * offset);
        tries++;
      }}
      placedPx.push(calloutPx);
      var calloutLatLng = map.containerPointToLatLng(calloutPx);

      var iconHtml = markerIcons[m.type] || defaultMarkerIcon;
      var icon = L.divIcon({{
        html: '<span class="map-marker-icon map-marker-icon--' + m.type + '">' + iconHtml + '</span>',
        className: 'map-marker',
        iconSize: [16, 16],
        iconAnchor: [8, 8]
      }});
      // The leader line drawn on hover runs from the callout back toward
      // realLatLng -- i.e. in the *opposite* direction from `dir` (the
      // callout was pushed out along +dir). A fixed "top" tooltip direction
      // sat on top of that line in almost every case, since the line just
      // as often ran upward as any other way. Pointing the tooltip along
      // +dir instead -- the same side the callout was already pushed toward,
      // away from the route -- keeps it clear of its own leader line
      // regardless of which way the route happens to curve here.
      var tooltipDir = Math.abs(dir.x) >= Math.abs(dir.y)
        ? (dir.x >= 0 ? "right" : "left")
        : (dir.y >= 0 ? "bottom" : "top");
      var TOOLTIP_OFFSET_PX = 10;
      var tooltipOffset = {{
        top: [0, -TOOLTIP_OFFSET_PX], bottom: [0, TOOLTIP_OFFSET_PX],
        left: [-TOOLTIP_OFFSET_PX, 0], right: [TOOLTIP_OFFSET_PX, 0]
      }}[tooltipDir];
      var mk = L.marker(calloutLatLng, {{icon: icon}}).addTo(map);
      mk.bindTooltip(m.tooltipHtml, {{direction: tooltipDir, offset: tooltipOffset}});
      if (m.clickUrl) {{
        mk.on("click", function () {{ window.open(m.clickUrl, "_blank"); }});
      }}

      var layer = {{leafletMarker: mk, leaderLine: null, highlightCircle: null}};
      mk.on("mouseover", function () {{
        layer.leaderLine = L.polyline([calloutLatLng, realLatLng], {{className: "marker-leader-line", interactive: false}}).addTo(map);
        layer.highlightCircle = L.circleMarker(realLatLng, {{className: "marker-real-point", radius: 5, interactive: false}}).addTo(map);
      }});
      mk.on("mouseout", function () {{
        if (layer.leaderLine) {{ map.removeLayer(layer.leaderLine); layer.leaderLine = null; }}
        if (layer.highlightCircle) {{ map.removeLayer(layer.highlightCircle); layer.highlightCircle = null; }}
      }});
      markerLayers.push(layer);
    }});
  }}

  layoutEventMarkers();
  map.on("zoomend moveend", layoutEventMarkers);

  // CARD-0085 Part B: travel-direction arrows along the route -- plain 2D
  // rotate() per marker (no hover/tilt behavior, unlike the sun gadget
  // above), non-interactive so they never intercept the route's own
  // mouseover hit-targets.
  // CARD-0147: transform order matters here -- rotate() outermost,
  // translateX() innermost. translateX applies first, shifting the marker
  // along its own (still-unrotated) local x-axis; rotate() then carries
  // that offset along with the glyph itself, landing the *visual* shift 90
  // degrees off whichever way the arrow is pointing -- "beside the track"
  // rather than on it, regardless of the route's own absolute compass
  // direction at that point. The rotation angle itself now comes from
  // tangentAngleDeg(t.idx) -- the drawn route line's own local on-screen
  // direction at that point -- not a stored bearing, so the arrow is
  // guaranteed to read as parallel to what's actually drawn (Joseph:
  // "should always be parallel to the track, but not touch the track").
  var travelArrows = {json.dumps(travel_arrows_js)};
  var travelArrowOffsetPx = {json.dumps(TRAVEL_ARROW_OFFSET_PX)};
  travelArrows.forEach(function (t) {{
    var angleDeg = tangentAngleDeg(t.idx);
    var icon = L.divIcon({{
      html: '<div class="travel-arrow-icon" style="transform: rotate(' + angleDeg + 'deg) translateX(' + travelArrowOffsetPx + 'px)">'
        + {json.dumps(_TRAVEL_ARROW_SVG)} + '</div>',
      className: 'travel-arrow-marker',
      iconSize: [14, 14],
      iconAnchor: [7, 7]
    }});
    L.marker([t.lat, t.lon], {{icon: icon, interactive: false}}).addTo(map);
  }});

  // CARD-0147: click-to-expand -- physically relocates this *same* Leaflet
  // instance's container into the modal on open rather than building a
  // second map to keep in sync (route/sun-gadget/travel-arrows all stay
  // correct automatically, since nothing was duplicated). A Leaflet
  // control (bottomright -- topright is the sun gadget, topleft is
  // Leaflet's own zoom control, so this is the one open corner) rather
  // than a raw button over the map, same collision-free reasoning as the
  // sun gadget's own control. invalidateSize() + re-fitBounds() on both
  // open and close: Leaflet caches its container size internally and
  // won't notice the DOM move/resize on its own, and the aspect ratio
  // genuinely changes between the small inline card and the large modal,
  // so simply preserving the current center (invalidateSize()'s own
  // default) would leave the route off-center or partly cropped at the
  // new size instead of nicely reframed.
  var mapContainer = document.getElementById("{map_id}");
  var mapOriginalParent = mapContainer.parentNode;
  var modalBackdrop = document.getElementById("{map_id}-modal-backdrop");
  var modalContainer = document.getElementById("{map_id}-modal-container");
  var modalCloseBtn = document.getElementById("{map_id}-modal-close");

  // Found live (Joseph): the modal box itself grew, but the map/route
  // rendering inside it stayed the same size, just floating in a bigger
  // empty container -- exactly the signature of invalidateSize()/
  // fitBounds() running before the browser had actually finished laying
  // out the just-shown, just-resized container. A bare setTimeout(fn, 0)
  // doesn't reliably guarantee that layout has settled by the time it
  // fires. Fixed with a forced synchronous reflow instead (reading
  // offsetHeight forces the browser to compute layout immediately, a
  // standard technique for exactly this) -- by the time refit() runs, the
  // container's *actual* final size is guaranteed available, so
  // invalidateSize() picks up the real new dimensions and fitBounds()
  // computes zoom against them, not stale ones.
  function refit() {{
    map.invalidateSize();
    if (allLatLngs.length) map.fitBounds(allLatLngs, {{padding: [24, 24]}});
  }}

  function openMapModal() {{
    modalBackdrop.classList.add("open");
    modalContainer.appendChild(mapContainer);
    void modalContainer.offsetHeight; // force layout before refit() reads the new size
    refit();
  }}
  function closeMapModal() {{
    modalBackdrop.classList.remove("open");
    mapOriginalParent.appendChild(mapContainer);
    void mapOriginalParent.offsetHeight; // force layout before refit() reads the new size
    refit();
  }}

  var ExpandControl = L.Control.extend({{
    options: {{position: "bottomright"}},
    onAdd: function () {{
      var btn = L.DomUtil.create("button", "map-expand-btn");
      btn.type = "button";
      btn.setAttribute("aria-label", "Expand map to full size");
      btn.title = "Expand map";
      btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        + 'stroke-linecap="round" stroke-linejoin="round">'
        + '<path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/>'
        + '<path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>';
      L.DomEvent.disableClickPropagation(btn);
      L.DomEvent.on(btn, "click", openMapModal);
      return btn;
    }}
  }});
  new ExpandControl().addTo(map);

  modalCloseBtn.addEventListener("click", closeMapModal);
  modalBackdrop.addEventListener("click", function (e) {{
    if (e.target === modalBackdrop) closeMapModal();
  }});
  document.addEventListener("keydown", function (e) {{
    if (e.key === "Escape" && modalBackdrop.classList.contains("open")) closeMapModal();
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
<!-- CARD-0147: click-to-expand modal. Holds no map of its own -- the *same*
     Leaflet instance's container gets physically relocated in here on open
     (see the script below) rather than building/keeping a second, duplicate
     map in sync. Deliberately map-only (no Elevation & Speed chart pairing
     in here, Joseph's call): the chart would either need its own carved-out
     space in the modal (working against maximizing map size, the whole
     point of expanding) or hover-sync events would target an on-page chart
     hidden behind the modal's own backdrop -- invisible, so pointless
     either way. -->
<div class="map-modal-backdrop" id="{map_id}-modal-backdrop">
  <div class="map-modal">
    <button class="map-modal-close" id="{map_id}-modal-close" aria-label="Close">&times;</button>
    <div id="{map_id}-modal-container" class="map-modal-container"></div>
  </div>
</div>
{script}'''
