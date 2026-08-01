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

from datetime import datetime, timedelta, timezone

MST_OFFSET = timedelta(hours=-7)  # America/Phoenix, no DST -- project convention

VIEWBOX_W = 640
VIEWBOX_H = 220
MARGIN = {'top': 10, 'right': 40, 'bottom': 22, 'left': 42}


def _mst_time_str(iso_ts):
    """12-hour MST time, e.g. '9:14:00 AM' -- avoids strftime's non-portable
    '%-I'/'%#I' no-leading-zero flags (glibc vs. Windows) by formatting the
    hour by hand."""
    dt = datetime.fromisoformat(iso_ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(timezone.utc) + MST_OFFSET
    hour_12 = local.hour % 12 or 12
    ampm = 'AM' if local.hour < 12 else 'PM'
    return f'{hour_12}:{local.minute:02d}:{local.second:02d} {ampm}'


def _esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def build_chart_html(chart_series, chart_id='hikeChart'):
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
    for p in chart_series:
        time_str = _esc(_mst_time_str(p['timestamp']))
        ex, ey = x(p['distance_mi']), y_elev(p['altitude_ft'])
        svg_parts.append(
            f'<circle class="hit-target" cx="{ex:.1f}" cy="{ey:.1f}" r="10" '
            f'data-metric="elevation" data-time="{time_str}" data-value="{round(p["altitude_ft"])}"/>'
        )
        if p['speed_mph'] is not None:
            sx, sy = x(p['distance_mi']), y_speed(p['speed_mph'])
            svg_parts.append(
                f'<circle class="hit-target" cx="{sx:.1f}" cy="{sy:.1f}" r="10" '
                f'data-metric="speed" data-time="{time_str}" data-value="{p["speed_mph"]:.1f}"/>'
            )

    svg_markup = '\n      '.join(svg_parts)
    script = build_chart_script(chart_id)

    return f'''<div class="chart-card">
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
{script}'''


def build_chart_script(chart_id):
    """The one narrow bit of real JS in hike-izer's output -- event wiring
    and tooltip text/visibility only. All geometry and per-point data (time,
    value, coordinates) is already baked into the SVG's own attributes by
    build_chart_html(), so this never recomputes anything."""
    return f'''<script>
(function () {{
  var svg = document.getElementById("{chart_id}");
  var tooltipSlot = document.getElementById("{chart_id}-tooltip");
  var guide = svg.querySelector(".hover-guide");
  var elevDot = svg.querySelector(".hover-dot.elevation");
  var speedDot = svg.querySelector(".hover-dot.speed");

  function show(circle) {{
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

  function hide() {{
    guide.setAttribute("opacity", 0);
    elevDot.setAttribute("opacity", 0);
    speedDot.setAttribute("opacity", 0);
    tooltipSlot.innerHTML = '<span class="tt-time">Hover the chart</span><span class="tt-metric">&mdash;</span>';
    tooltipSlot.classList.remove("is-active");
  }}

  var targets = svg.querySelectorAll(".hit-target");
  for (var i = 0; i < targets.length; i++) {{
    targets[i].addEventListener("mouseenter", (function (c) {{ return function () {{ show(c); }}; }})(targets[i]));
    targets[i].addEventListener("mouseleave", hide);
  }}
}})();
</script>'''
