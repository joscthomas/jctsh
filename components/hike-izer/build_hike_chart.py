#!/usr/bin/env python
"""
CARD-0110: renders the ready-to-embed "Elevation & Speed" chart for a hike-izer
HTML page from fetch_hike_data.py's `chart_series` output.

Geometry (axes, gridlines, the two polylines, hover hit-targets) is computed
here in Python and emitted as static SVG markup -- not built client-side.
The one bit of real JS this produces (build_chart_script()) only wires up
hover events and reads pre-baked data-* attributes; it does no geometry or
math of its own. This is hike-izer's one deliberate, narrow exception to its
otherwise zero-JS template convention (see CARD-0110's Planning notes) --
kept as small as it is on purpose.

Standard library only -- no pip install required, matching fetch_hike_data.py.

Usage (as a library, called from the hike-izer generation step):
    from build_hike_chart import build_chart_html
    chart_html = build_chart_html(hike_data['chart_series'])
    # splice chart_html into html-template.html's {{ELEVATION_SPEED_CHART}}
"""

import json
from datetime import datetime, timedelta, timezone

# America/Phoenix, no DST -- the default because it's right for every hike
# taken from home. NOT right for a hike taken elsewhere (e.g. traveling) --
# caught 2026-08-01 generating a real Michigan hike's page, where GPS
# coordinates put it in Eastern time, not Arizona. build_chart_html() takes
# an explicit tz_offset_hours override for exactly that case; there's no
# automatic lat/lon-to-timezone detection yet (would need a real geo-timezone
# lookup, its own scoped card, not a silent addition here) -- whoever's
# generating a hike's page has to notice the hike wasn't local and pass the
# right offset by hand, the same kind of judgment call SKILL.md's
# cross-midnight caveat already documents.
DEFAULT_TZ_OFFSET_HOURS = -7

VIEWBOX_W = 640
VIEWBOX_H = 220
MARGIN = {'top': 10, 'right': 40, 'bottom': 22, 'left': 42}


def _local_time_str(iso_ts, tz_offset_hours):
    """12-hour local time, e.g. '9:14:00 AM' -- avoids strftime's non-portable
    '%-I'/'%#I' no-leading-zero flags (glibc vs. Windows) by formatting the
    hour by hand."""
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


def build_chart_html(chart_series, chart_id='hikeChart', tz_offset_hours=DEFAULT_TZ_OFFSET_HOURS):
    """Returns the full chart <section>-ready markup (legend, tooltip slot,
    SVG with baked-in geometry + hover hit-targets, and the small hover
    script) as one HTML string. Returns an empty string if chart_series is
    empty (e.g. hike_confirmed is False) -- caller should omit the whole
    "Elevation & Speed" section entirely in that case, same "no empty
    scaffolding" convention CARD-0084's Photos section already follows."""
    if not chart_series:
        return ''

    plot_w = VIEWBOX_W - MARGIN['left'] - MARGIN['right']
    plot_h = VIEWBOX_H - MARGIN['top'] - MARGIN['bottom']

    max_dist = chart_series[-1]['distance_mi'] or 0.001
    alt_vals = [p['altitude_ft'] for p in chart_series]
    min_alt, max_alt = min(alt_vals) - 4, max(alt_vals) + 4
    if max_alt == min_alt:
        max_alt += 1
    speed_vals = [p['speed_mph'] for p in chart_series if p['speed_mph'] is not None]
    max_speed = max(3.5, (max(speed_vals) if speed_vals else 0) + 0.5)

    def x(d):
        return MARGIN['left'] + (d / max_dist) * plot_w

    def y_elev(ft):
        return MARGIN['top'] + plot_h - ((ft - min_alt) / (max_alt - min_alt)) * plot_h

    def y_speed(mph):
        return MARGIN['top'] + plot_h - (max(0, mph) / max_speed) * plot_h

    svg_parts = []

    # Gridlines + axis labels
    for frac in (0, 0.5, 1):
        v = min_alt + frac * (max_alt - min_alt)
        yy = y_elev(v)
        svg_parts.append(f'<line class="gridline" x1="{MARGIN["left"]}" x2="{VIEWBOX_W - MARGIN["right"]}" y1="{yy:.1f}" y2="{yy:.1f}"/>')
        svg_parts.append(f'<text class="axis-label" x="{MARGIN["left"] - 6}" y="{yy + 3:.1f}" text-anchor="end">{round(v)}ft</text>')
    for v in (0, max_speed / 2, max_speed):
        yy = y_speed(v)
        svg_parts.append(f'<text class="axis-label" x="{VIEWBOX_W - MARGIN["right"] + 6}" y="{yy + 3:.1f}" text-anchor="start">{v:.1f}mph</text>')
    for frac in (0, 0.25, 0.5, 0.75, 1):
        d = frac * max_dist
        xx = x(d)
        svg_parts.append(f'<text class="axis-label" x="{xx:.1f}" y="{VIEWBOX_H - 6}" text-anchor="middle">{d:.2f}mi</text>')
    svg_parts.append(f'<line class="axis-line" x1="{MARGIN["left"]}" x2="{VIEWBOX_W - MARGIN["right"]}" y1="{MARGIN["top"] + plot_h}" y2="{MARGIN["top"] + plot_h}"/>')

    # Split into per-session segments wherever 'session_break' is set (two
    # separate hike sessions the same day, e.g. a morning and an evening
    # walk) -- points never connect across a break, on the line or the fill,
    # since that gap is real elapsed time with no GPS track, not movement.
    segments = []
    for p in chart_series:
        if p.get('session_break') or not segments:
            segments.append([])
        segments[-1].append(p)

    floor_y = MARGIN['top'] + plot_h

    # Elevation area fill + line -- one closed fill shape and one line
    # subpath per segment, joined into a single <path> each (multiple M...
    # subpaths in one `d` render independently, no connecting stroke between
    # them, so this stays one <path> per series rather than N).
    elev_line_parts, fill_parts = [], []
    for seg in segments:
        pts = [(x(p['distance_mi']), y_elev(p['altitude_ft'])) for p in seg]
        line = ' '.join(f'{"M" if i == 0 else "L"}{px:.1f},{py:.1f}' for i, (px, py) in enumerate(pts))
        elev_line_parts.append(line)
        fill_parts.append(f'{line} L{pts[-1][0]:.1f},{floor_y} L{pts[0][0]:.1f},{floor_y} Z')
    svg_parts.append(f'<path class="line-elevation-fill" d="{" ".join(fill_parts)}"/>')
    svg_parts.append(f'<path class="line-elevation" d="{" ".join(elev_line_parts)}"/>')

    # Speed line -- same per-segment split, and within a segment only across
    # points with a real speed value (the very first point of any segment
    # has none, since it has no prior point in that segment to measure an
    # interval against).
    speed_line_parts = []
    for seg in segments:
        pts = [(x(p['distance_mi']), y_speed(p['speed_mph'])) for p in seg if p['speed_mph'] is not None]
        if pts:
            speed_line_parts.append(' '.join(f'{"M" if i == 0 else "L"}{px:.1f},{py:.1f}' for i, (px, py) in enumerate(pts)))
    if speed_line_parts:
        svg_parts.append(f'<path class="line-speed" d="{" ".join(speed_line_parts)}"/>')

    # Hover guide + the two dots hover toggles between (created once, shown/hidden by JS)
    svg_parts.append(f'<line class="hover-guide" x1="0" x2="0" y1="{MARGIN["top"]}" y2="{MARGIN["top"] + plot_h}" opacity="0"/>')
    svg_parts.append('<circle class="hover-dot elevation" r="4" opacity="0"/>')
    svg_parts.append('<circle class="hover-dot speed" r="4" opacity="0"/>')

    # Hit-targets: one invisible larger circle per point per line, each
    # carrying its own hover data pre-baked as attributes -- the hover
    # script just reads these, it never computes a value or a coordinate.
    # data-index (CARD-0082) is this point's position in chart_series -- the
    # one thing the Route Map needs to look up the *same* point in its own
    # markup for hover-sync, since both are generated from the same list.
    for i, p in enumerate(chart_series):
        time_str = _esc(_local_time_str(p['timestamp'], tz_offset_hours))
        ex, ey = x(p['distance_mi']), y_elev(p['altitude_ft'])
        svg_parts.append(
            f'<circle class="hit-target" cx="{ex:.1f}" cy="{ey:.1f}" r="10" data-index="{i}" '
            f'data-metric="elevation" data-time="{time_str}" data-value="{round(p["altitude_ft"])}"/>'
        )
        if p['speed_mph'] is not None:
            sx, sy = x(p['distance_mi']), y_speed(p['speed_mph'])
            svg_parts.append(
                f'<circle class="hit-target" cx="{sx:.1f}" cy="{sy:.1f}" r="10" data-index="{i}" '
                f'data-metric="speed" data-time="{time_str}" data-value="{p["speed_mph"]:.1f}"/>'
            )

    svg_markup = '\n      '.join(svg_parts)
    script = build_chart_script(chart_id)

    return f'''<div class="chart-card">
  <button type="button" class="map-expand-btn chart-expand-btn" id="{chart_id}-expand-btn" aria-label="Expand chart to full size" title="Expand chart">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/>
      <path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/>
    </svg>
  </button>
  <div class="chart-legend">
    <span><i class="dot-elevation"></i>Elevation</span>
    <span><i class="dot-speed"></i>Speed</span>
  </div>
  <div class="chart-tooltip-slot" id="{chart_id}-tooltip">
    <span class="tt-time">Hover the chart</span>
    <span class="tt-metric">&mdash;</span>
  </div>
  <div class="chart-svg-wrap">
    <svg class="hike-chart" id="{chart_id}" viewBox="0 0 {VIEWBOX_W} {VIEWBOX_H}" preserveAspectRatio="xMidYMid meet">
      {svg_markup}
    </svg>
  </div>
</div>
<!-- CARD-0194: click-to-expand, same pattern CARD-0147 built for the Route
     Map -- the *same* chart-card DOM node (legend, tooltip slot, SVG) gets
     physically relocated into this modal on open and back out on close (see
     build_chart_script()'s openChartModal()/closeChartModal()), rather than
     building/keeping a second chart in sync. No invalidateSize()-equivalent
     needed here the way the Leaflet map required one: this is a plain SVG
     with viewBox + preserveAspectRatio, so it re-scales to whatever
     container it's sitting in automatically, purely via CSS layout. -->
<div class="map-modal-backdrop" id="{chart_id}-modal-backdrop">
  <div class="map-modal">
    <button class="map-modal-close" id="{chart_id}-modal-close" aria-label="Close">&times;</button>
    <div id="{chart_id}-modal-container" class="map-modal-container"></div>
  </div>
</div>
{script}'''


def build_chart_script(chart_id):
    """The one narrow bit of real JS in hike-izer's output -- event wiring
    and tooltip text/visibility only. All geometry and per-point data (time,
    value, coordinates) is already baked into the SVG's own attributes by
    build_chart_html(), so this never recomputes anything.

    CARD-0082: also dispatches/listens for hikeizer-chart-hover(unhover) and
    hikeizer-map-hover(unhover) window CustomEvents (detail: {index}) so the
    Route Map (built independently by build_hike_map.py from the same
    chart_series) can stay in sync without either module knowing anything
    about the other's internals -- the shared point index is the only
    contract between them."""
    return f'''<script>
(function () {{
  var svg = document.getElementById("{chart_id}");
  var tooltipSlot = document.getElementById("{chart_id}-tooltip");
  var guide = svg.querySelector(".hover-guide");
  var elevDot = svg.querySelector(".hover-dot.elevation");
  var speedDot = svg.querySelector(".hover-dot.speed");

  function showOne(circle) {{
    var metric = circle.getAttribute("data-metric");
    var time = circle.getAttribute("data-time");
    var value = circle.getAttribute("data-value");
    var cx = circle.getAttribute("cx");
    var cy = circle.getAttribute("cy");
    guide.setAttribute("x1", cx);
    guide.setAttribute("x2", cx);
    guide.setAttribute("opacity", 1);
    var dot = metric === "elevation" ? elevDot : speedDot;
    var otherDot = metric === "elevation" ? speedDot : elevDot;
    dot.setAttribute("cx", cx);
    dot.setAttribute("cy", cy);
    dot.setAttribute("opacity", 1);
    otherDot.setAttribute("opacity", 0);
    var unit = metric === "elevation" ? " ft elevation" : " mph";
    tooltipSlot.innerHTML = '<span class="tt-time">' + time + '</span>' +
      '<span class="tt-metric ' + metric + '">' + value + unit + "</span>";
    tooltipSlot.classList.add("is-active");
  }}

  // Used when the hover originated on the map, which has no "which line"
  // concept -- shows both dots at once with a combined tooltip line instead
  // of picking one metric the way a chart-originated hover does.
  function showBoth(index) {{
    var elevCircle = svg.querySelector('.hit-target[data-index="' + index + '"][data-metric="elevation"]');
    var speedCircle = svg.querySelector('.hit-target[data-index="' + index + '"][data-metric="speed"]');
    if (!elevCircle) return;
    guide.setAttribute("x1", elevCircle.getAttribute("cx"));
    guide.setAttribute("x2", elevCircle.getAttribute("cx"));
    guide.setAttribute("opacity", 1);
    elevDot.setAttribute("cx", elevCircle.getAttribute("cx"));
    elevDot.setAttribute("cy", elevCircle.getAttribute("cy"));
    elevDot.setAttribute("opacity", 1);
    var parts = ['<span class="tt-time">' + elevCircle.getAttribute("data-time") + '</span>',
      '<span class="tt-metric elevation">' + elevCircle.getAttribute("data-value") + ' ft</span>'];
    if (speedCircle) {{
      speedDot.setAttribute("cx", speedCircle.getAttribute("cx"));
      speedDot.setAttribute("cy", speedCircle.getAttribute("cy"));
      speedDot.setAttribute("opacity", 1);
      parts.push('<span class="tt-metric speed">' + speedCircle.getAttribute("data-value") + ' mph</span>');
    }} else {{
      speedDot.setAttribute("opacity", 0);
    }}
    tooltipSlot.innerHTML = parts.join(" ");
    tooltipSlot.classList.add("is-active");
  }}

  function hide() {{
    guide.setAttribute("opacity", 0);
    elevDot.setAttribute("opacity", 0);
    speedDot.setAttribute("opacity", 0);
    tooltipSlot.innerHTML = '<span class="tt-time">Hover the chart</span><span class="tt-metric">&mdash;</span>';
    tooltipSlot.classList.remove("is-active");
  }}

  var targets = svg.querySelectorAll(".hit-target");
  for (var i = 0; i < targets.length; i++) {{
    targets[i].addEventListener("mouseenter", (function (c) {{
      return function () {{
        showOne(c);
        window.dispatchEvent(new CustomEvent("hikeizer-chart-hover", {{detail: {{index: Number(c.getAttribute("data-index"))}}}}));
      }};
    }})(targets[i]));
    targets[i].addEventListener("mouseleave", function () {{
      hide();
      window.dispatchEvent(new CustomEvent("hikeizer-chart-unhover"));
    }});
  }}

  // Mirror a hover that started on the Route Map (CARD-0082). Calling
  // showBoth()/hide() directly here never touches the .hit-target elements'
  // own mouseenter/mouseleave listeners, so this can't loop back into
  // re-dispatching hikeizer-chart-hover for a hover the map already knows about.
  window.addEventListener("hikeizer-map-hover", function (e) {{ showBoth(e.detail.index); }});
  window.addEventListener("hikeizer-map-unhover", hide);

  // CARD-0204: mirror a hover that started on the new Environmental Data
  // chart panel (build_env_chart_html/build_env_chart_script below) -- it
  // dispatches the same hikeizer-chart-hover/-unhover events this chart
  // itself already dispatches on its own hover, so listening here picks up
  // its hovers too. This chart also receives its own dispatched event back
  // (window-level CustomEvents aren't scoped per-origin) -- harmless, just a
  // redundant showBoth() call with the index it just set.
  window.addEventListener("hikeizer-chart-hover", function (e) {{ showBoth(e.detail.index); }});
  window.addEventListener("hikeizer-chart-unhover", hide);

  // CARD-0194: click-to-expand, mirrors CARD-0147's Route Map modal.
  var chartCard = svg.closest(".chart-card");
  var chartOriginalParent = chartCard.parentNode;
  var chartModalBackdrop = document.getElementById("{chart_id}-modal-backdrop");
  var chartModalContainer = document.getElementById("{chart_id}-modal-container");
  var chartModalClose = document.getElementById("{chart_id}-modal-close");
  var chartExpandBtn = document.getElementById("{chart_id}-expand-btn");

  function openChartModal() {{
    chartModalBackdrop.classList.add("open");
    chartModalContainer.appendChild(chartCard);
  }}
  function closeChartModal() {{
    chartModalBackdrop.classList.remove("open");
    chartOriginalParent.appendChild(chartCard);
  }}

  chartExpandBtn.addEventListener("click", openChartModal);
  chartModalClose.addEventListener("click", closeChartModal);
  chartModalBackdrop.addEventListener("click", function (e) {{
    if (e.target === chartModalBackdrop) closeChartModal();
  }});
  document.addEventListener("keydown", function (e) {{
    if (e.key === "Escape" && chartModalBackdrop.classList.contains("open")) closeChartModal();
  }});
}})();
</script>'''


# CARD-0204: Environmental Data (temp/humidity/pressure/UV) chart -- reuses
# chart_series' own per-point temp_f/humidity_pct/pressure_hpa/uv_index
# fields (fetch_hike_data.py's _correlate_environmental_series, linear
# interpolation between bracketing real readings within a capped gap). Two
# preset pairings share one panel via a legend-toggle, decided over either
# 4 lines on one axis (unit spread makes that unreadable) or a free-pick-any-2
# UI (real complexity for a combination nobody asked for) -- see CARD-0204's
# own interview notes on kanban-board.md.
ENV_CHART_MODES = [
    {
        'key': 'temp-humidity',
        'label': 'Temp & Humidity',
        'left': {'field': 'temp_f', 'unit': '°F', 'css': 'temp'},
        'right': {'field': 'humidity_pct', 'unit': '%', 'css': 'humidity'},
    },
    {
        'key': 'pressure-uv',
        'label': 'Pressure & UV',
        'left': {'field': 'pressure_hpa', 'unit': 'hPa', 'css': 'pressure'},
        'right': {'field': 'uv_index', 'unit': '', 'css': 'uv'},
    },
]


def build_env_chart_html(chart_series, chart_id='hikeEnvChart', tz_offset_hours=DEFAULT_TZ_OFFSET_HOURS):
    """Returns the Environmental Data chart's <div class="chart-card">...
    markup, or '' if chart_series is empty or carries no environmental
    values at all for any of the 4 fields (e.g. the hiking-monitor device
    wasn't carried that day) -- same "no empty scaffolding" convention
    build_chart_html() itself follows. Both preset pairings' full geometry
    is precomputed here and shipped in the same SVG as two sibling <g>
    elements; the legend-toggle only ever flips which one is visible
    (build_env_chart_script()), no client-side math."""
    env_fields = ('temp_f', 'humidity_pct', 'pressure_hpa', 'uv_index')
    if not chart_series or not any(p.get(f) is not None for p in chart_series for f in env_fields):
        return ''

    plot_w = VIEWBOX_W - MARGIN['left'] - MARGIN['right']
    plot_h = VIEWBOX_H - MARGIN['top'] - MARGIN['bottom']
    max_dist = chart_series[-1]['distance_mi'] or 0.001

    def x(d):
        return MARGIN['left'] + (d / max_dist) * plot_w

    segments = []
    for p in chart_series:
        if p.get('session_break') or not segments:
            segments.append([])
        segments[-1].append(p)

    mode_groups = []
    for mi, mode in enumerate(ENV_CHART_MODES):
        left, right = mode['left'], mode['right']
        left_vals = [p[left['field']] for p in chart_series if p.get(left['field']) is not None]
        right_vals = [p[right['field']] for p in chart_series if p.get(right['field']) is not None]
        left_min, left_max = (min(left_vals) - 1, max(left_vals) + 1) if left_vals else (0, 1)
        right_min, right_max = (min(right_vals) - 1, max(right_vals) + 1) if right_vals else (0, 1)
        if left_max == left_min:
            left_max += 1
        if right_max == right_min:
            right_max += 1

        def y_left(v, lo=left_min, hi=left_max):
            return MARGIN['top'] + plot_h - ((v - lo) / (hi - lo)) * plot_h

        def y_right(v, lo=right_min, hi=right_max):
            return MARGIN['top'] + plot_h - ((v - lo) / (hi - lo)) * plot_h

        svg_parts = []
        for frac in (0, 0.5, 1):
            v = left_min + frac * (left_max - left_min)
            yy = y_left(v)
            svg_parts.append(f'<line class="gridline" x1="{MARGIN["left"]}" x2="{VIEWBOX_W - MARGIN["right"]}" y1="{yy:.1f}" y2="{yy:.1f}"/>')
            svg_parts.append(f'<text class="axis-label" x="{MARGIN["left"] - 6}" y="{yy + 3:.1f}" text-anchor="end">{v:.0f}{left["unit"]}</text>')
        for frac in (0, 0.5, 1):
            v = right_min + frac * (right_max - right_min)
            yy = y_right(v)
            svg_parts.append(f'<text class="axis-label" x="{VIEWBOX_W - MARGIN["right"] + 6}" y="{yy + 3:.1f}" text-anchor="start">{v:.0f}{right["unit"]}</text>')
        for frac in (0, 0.25, 0.5, 0.75, 1):
            d = frac * max_dist
            xx = x(d)
            svg_parts.append(f'<text class="axis-label" x="{xx:.1f}" y="{VIEWBOX_H - 6}" text-anchor="middle">{d:.2f}mi</text>')
        svg_parts.append(f'<line class="axis-line" x1="{MARGIN["left"]}" x2="{VIEWBOX_W - MARGIN["right"]}" y1="{MARGIN["top"] + plot_h}" y2="{MARGIN["top"] + plot_h}"/>')

        for field_info, y_fn in ((left, y_left), (right, y_right)):
            line_parts = []
            for seg in segments:
                pts = [(x(p['distance_mi']), y_fn(p[field_info['field']])) for p in seg if p.get(field_info['field']) is not None]
                if pts:
                    line_parts.append(' '.join(f'{"M" if i == 0 else "L"}{px:.1f},{py:.1f}' for i, (px, py) in enumerate(pts)))
            if line_parts:
                svg_parts.append(f'<path class="line-{field_info["css"]}" d="{" ".join(line_parts)}"/>')

        svg_parts.append(f'<line class="hover-guide" x1="0" x2="0" y1="{MARGIN["top"]}" y2="{MARGIN["top"] + plot_h}" opacity="0"/>')
        svg_parts.append(f'<circle class="hover-dot {left["css"]}" data-metric="{left["css"]}" r="4" opacity="0"/>')
        svg_parts.append(f'<circle class="hover-dot {right["css"]}" data-metric="{right["css"]}" r="4" opacity="0"/>')

        for i, p in enumerate(chart_series):
            time_str = _esc(_local_time_str(p['timestamp'], tz_offset_hours))
            for field_info, y_fn in ((left, y_left), (right, y_right)):
                v = p.get(field_info['field'])
                if v is None:
                    continue
                px, py = x(p['distance_mi']), y_fn(v)
                svg_parts.append(
                    f'<circle class="hit-target" cx="{px:.1f}" cy="{py:.1f}" r="10" data-index="{i}" '
                    f'data-metric="{field_info["css"]}" data-time="{time_str}" data-value="{v:.1f}" data-unit="{field_info["unit"]}"/>'
                )

        svg_markup = '\n      '.join(svg_parts)
        display = '' if mi == 0 else ' style="display:none"'
        mode_groups.append(f'<g class="env-mode-group" id="{chart_id}-mode-{mode["key"]}"{display}>\n      {svg_markup}\n    </g>')

    groups_markup = '\n    '.join(mode_groups)
    toggle_buttons = ''.join(
        f'<button type="button" class="chart-toggle-btn{" active" if i == 0 else ""}" data-mode="{mode["key"]}">{_esc(mode["label"])}</button>'
        for i, mode in enumerate(ENV_CHART_MODES)
    )
    script = build_env_chart_script(chart_id, [m['key'] for m in ENV_CHART_MODES])

    return f'''<div class="chart-card">
  <button type="button" class="map-expand-btn chart-expand-btn" id="{chart_id}-expand-btn" aria-label="Expand chart to full size" title="Expand chart">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/>
      <path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/>
    </svg>
  </button>
  <div class="chart-toggle" id="{chart_id}-toggle">{toggle_buttons}</div>
  <div class="chart-tooltip-slot" id="{chart_id}-tooltip">
    <span class="tt-time">Hover the chart</span>
    <span class="tt-metric">&mdash;</span>
  </div>
  <div class="chart-svg-wrap">
    <svg class="hike-chart" id="{chart_id}" viewBox="0 0 {VIEWBOX_W} {VIEWBOX_H}" preserveAspectRatio="xMidYMid meet">
      {groups_markup}
    </svg>
  </div>
</div>
<div class="map-modal-backdrop" id="{chart_id}-modal-backdrop">
  <div class="map-modal">
    <button class="map-modal-close" id="{chart_id}-modal-close" aria-label="Close">&times;</button>
    <div id="{chart_id}-modal-container" class="map-modal-container"></div>
  </div>
</div>
{script}'''


def build_env_chart_script(chart_id, mode_keys):
    """Mirrors build_chart_script()'s hover-sync contract exactly -- same
    data-index attribute, same hikeizer-chart-hover/-unhover window
    CustomEvents -- so this panel, the Route Map, and the Elevation & Speed
    chart all stay in sync regardless of which one a hover starts on. The
    one thing on top of that shared pattern: a legend-toggle switches which
    of the two pre-baked <g class="env-mode-group"> is visible; toggling
    only ever flips a style.display, no data recomputed client-side."""
    mode_keys_json = json.dumps(mode_keys)
    return f'''<script>
(function () {{
  var svg = document.getElementById("{chart_id}");
  var tooltipSlot = document.getElementById("{chart_id}-tooltip");
  var toggle = document.getElementById("{chart_id}-toggle");
  var modeKeys = {mode_keys_json};
  var activeMode = modeKeys[0];

  function activeGroup() {{ return document.getElementById("{chart_id}-mode-" + activeMode); }}

  function setMode(mode) {{
    activeMode = mode;
    modeKeys.forEach(function (k) {{
      document.getElementById("{chart_id}-mode-" + k).style.display = (k === mode) ? "" : "none";
    }});
    Array.prototype.forEach.call(toggle.querySelectorAll(".chart-toggle-btn"), function (btn) {{
      btn.classList.toggle("active", btn.getAttribute("data-mode") === mode);
    }});
    hide();
  }}

  Array.prototype.forEach.call(toggle.querySelectorAll(".chart-toggle-btn"), function (btn) {{
    btn.addEventListener("click", function () {{ setMode(btn.getAttribute("data-mode")); }});
  }});

  function showByIndex(index) {{
    var g = activeGroup();
    var targets = g.querySelectorAll('.hit-target[data-index="' + index + '"]');
    if (!targets.length) {{ hide(); return; }}
    var guide = g.querySelector(".hover-guide");
    var dots = g.querySelectorAll(".hover-dot");
    var firstCx = targets[0].getAttribute("cx");
    guide.setAttribute("x1", firstCx);
    guide.setAttribute("x2", firstCx);
    guide.setAttribute("opacity", 1);
    var shownMetrics = {{}};
    var parts = [];
    Array.prototype.forEach.call(targets, function (circle) {{
      var metric = circle.getAttribute("data-metric");
      shownMetrics[metric] = true;
      var dot = g.querySelector(".hover-dot." + metric);
      dot.setAttribute("cx", circle.getAttribute("cx"));
      dot.setAttribute("cy", circle.getAttribute("cy"));
      dot.setAttribute("opacity", 1);
      parts.push('<span class="tt-metric ' + metric + '">' + circle.getAttribute("data-value") + circle.getAttribute("data-unit") + '</span>');
    }});
    Array.prototype.forEach.call(dots, function (dot) {{
      var metric = dot.getAttribute("data-metric");
      if (!shownMetrics[metric]) dot.setAttribute("opacity", 0);
    }});
    tooltipSlot.innerHTML = '<span class="tt-time">' + targets[0].getAttribute("data-time") + '</span>' + parts.join("");
    tooltipSlot.classList.add("is-active");
  }}

  function hide() {{
    modeKeys.forEach(function (k) {{
      var g = document.getElementById("{chart_id}-mode-" + k);
      var guide = g.querySelector(".hover-guide");
      if (guide) guide.setAttribute("opacity", 0);
      Array.prototype.forEach.call(g.querySelectorAll(".hover-dot"), function (dot) {{ dot.setAttribute("opacity", 0); }});
    }});
    tooltipSlot.innerHTML = '<span class="tt-time">Hover the chart</span><span class="tt-metric">&mdash;</span>';
    tooltipSlot.classList.remove("is-active");
  }}

  Array.prototype.forEach.call(svg.querySelectorAll(".hit-target"), function (circle) {{
    circle.addEventListener("mouseenter", function () {{
      var index = Number(circle.getAttribute("data-index"));
      showByIndex(index);
      window.dispatchEvent(new CustomEvent("hikeizer-chart-hover", {{detail: {{index: index}}}}));
    }});
    circle.addEventListener("mouseleave", function () {{
      hide();
      window.dispatchEvent(new CustomEvent("hikeizer-chart-unhover"));
    }});
  }});

  // Three-way sync (CARD-0204): pick up hovers from the Route Map and the
  // Elevation & Speed chart the same way this panel's own hover reaches
  // them (both already listen for/dispatch these same event names).
  window.addEventListener("hikeizer-map-hover", function (e) {{ showByIndex(e.detail.index); }});
  window.addEventListener("hikeizer-map-unhover", hide);
  window.addEventListener("hikeizer-chart-hover", function (e) {{ showByIndex(e.detail.index); }});
  window.addEventListener("hikeizer-chart-unhover", hide);

  // CARD-0194-style click-to-expand, same DOM-relocation pattern build_chart_script() uses.
  var chartCard = svg.closest(".chart-card");
  var chartOriginalParent = chartCard.parentNode;
  var chartModalBackdrop = document.getElementById("{chart_id}-modal-backdrop");
  var chartModalContainer = document.getElementById("{chart_id}-modal-container");
  var chartModalClose = document.getElementById("{chart_id}-modal-close");
  var chartExpandBtn = document.getElementById("{chart_id}-expand-btn");

  function openChartModal() {{
    chartModalBackdrop.classList.add("open");
    chartModalContainer.appendChild(chartCard);
  }}
  function closeChartModal() {{
    chartModalBackdrop.classList.remove("open");
    chartOriginalParent.appendChild(chartCard);
  }}
  chartExpandBtn.addEventListener("click", openChartModal);
  chartModalClose.addEventListener("click", closeChartModal);
  chartModalBackdrop.addEventListener("click", function (e) {{
    if (e.target === chartModalBackdrop) closeChartModal();
  }});
  document.addEventListener("keydown", function (e) {{
    if (e.key === "Escape" && chartModalBackdrop.classList.contains("open")) closeChartModal();
  }});
}})();
</script>'''
