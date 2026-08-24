#!/usr/bin/env python
"""
Hike-izer battery discharge-rate trend page builder (CARD-0207).

Rough field indicator of hiking-monitor's battery drain, tracked across
hikes over time -- explicitly not a substitute for a real bench current
measurement (CARD-0026's own method remains the precise way to validate a
specific firmware change in isolation). This page exists so the trend is
visible on the site itself rather than something that has to be asked for
and recomputed by hand each time.

Scans a served directory for <date>_hike-summary.meta.json sidecars (same
source-of-truth convention build_calendar_index.py already uses) to get the
list of published hikes, then reads each hike's own persisted
<file_stem>_hike_data.json (PRIVATE_DIR, written by generation.py's step 1)
for stats.battery_window_crossing_min -- minutes for that hike's own
field-mode battery readings to cross a *fixed* reference voltage window
(BATTERY_TREND_WINDOW_HIGH_V/_LOW_V, fetch_hike_data.py). A fixed window
(not each hike's own start/end range) is the whole point: a LiPo's
discharge curve is non-linear, so comparing different hikes' own ranges
conflates curve-position with real draw -- confirmed live, 2026-08-24: two
real hikes' raw full-range rates looked ~62% apart, but the identical
4.00V->3.70V slice in both narrowed the real gap to ~19%.

Only hikes with a computable rate get a row (Joseph's call, 2026-08-24,
revising the original complete-index design) -- a hike that's too short,
started below 4.00V, or predates this pipeline and has no persisted
hike_data.json left is hidden rather than shown as "not available," since
a trend page mostly made of empty rows isn't a useful trend to look at.
The subtitle still names how many earlier hikes are hidden, so their
existence isn't silently lost, just not cluttering the table itself.

Modeled directly on build_wildlife_index.py (same inline _STYLE, same
click-to-sort JS pattern -- the one deliberate exception to this project's
zero-JS convention, needed because a viewer picking their own sort order
can't be done statically).

Meant to be re-run after every publish, alongside build_calendar_index.py;
see components/hike-izer-orchestrator/generation.py for the call site.

Standard library only -- matches fetch_hike_data.py's/build_calendar_index.py's
convention.
"""

import argparse
import json
import re
import sys
from html import escape as _esc_attr
from pathlib import Path

# Same naming convention as build_calendar_index.py's META_RE -- the
# trailing group is None for a day's first hike, "2"/"3"/... for later
# same-day hikes (CARD-0113).
META_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}(?:-\d+)?)_hike-summary\.meta\.json$")

_STYLE = """
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
    --shadow: 0 1px 2px rgba(30,30,20,0.06), 0 6px 16px -8px rgba(30,30,20,0.18);
    --radius: 8px;
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
  .subtitle { color: var(--ink-muted); font-size: 0.85rem; margin: 0 0 1.5rem; }
  .caveat { color: var(--ink-faint); font-size: 0.8rem; margin: -1rem 0 1.5rem; }
  .empty { color: var(--ink-faint); font-style: italic; }

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

  table {
    width: 100%;
    border-collapse: collapse;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
    font-size: 0.9rem;
  }
  th, td {
    text-align: left;
    padding: 0.6rem 0.8rem;
    border-bottom: 1px solid var(--line);
  }
  th {
    background: var(--surface-2);
    color: var(--ink-muted);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    cursor: pointer;
    user-select: none;
  }
  th:hover { background: var(--line); }
  th.sort-asc::after { content: " ▲"; }
  th.sort-desc::after { content: " ▼"; }
  tr:last-child td { border-bottom: none; }

  footer {
    color: var(--ink-faint);
    font-size: 0.75rem;
    margin-top: 2rem;
    border-top: 1px solid var(--line);
    padding-top: 1rem;
  }
""".strip("\n")


def _hike_url(file_stem):
    return f"{file_stem}_hike-summary.html"


_MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _date_display(file_stem):
    # file_stem is YYYY-MM-DD or YYYY-MM-DD-N; the date portion alone is
    # enough for this page (no time-of-day claim needed, unlike the hero
    # stat row on a hike's own page). Built by hand, not strftime("%-d") --
    # that flag is a Linux/glibc extension only (Windows needs "%#d"
    # instead), the same non-portability CARD-0110's own chart code already
    # hit and worked around.
    parts = file_stem.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    suffix = f" (#{parts[3]})" if len(parts) > 3 else ""
    return f"{_MONTH_ABBR[month - 1]} {day}, {year}" + suffix


def _collect_rows(srv_dir, private_dir):
    srv = Path(srv_dir)
    priv = Path(private_dir)
    stems = []
    for meta_path in srv.glob("*_hike-summary.meta.json"):
        m = META_RE.match(meta_path.name)
        if m:
            stems.append(m.group(1))
    stems.sort(reverse=True)  # most recent hike first, same as the calendar page

    rows = []
    for stem in stems:
        crossing_min = None
        data_path = priv / f"{stem}_hike_data.json"
        if data_path.exists():
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    hike_data = json.load(f)
                crossing_min = hike_data.get("stats", {}).get("battery_window_crossing_min")
            except (json.JSONDecodeError, OSError):
                pass  # leave as not-available rather than fail the whole page
        rows.append((stem, crossing_min))
    return rows


def _render_page(rows):
    # CARD-0207, revised 2026-08-24 (Joseph): hikes with no computable rate
    # (predates this stat, too short, or started below 4.00V) are hidden
    # from the table entirely rather than shown as "not available" rows --
    # a deliberate reversal of this page's original complete-index design,
    # since a trend page mostly made of empty rows isn't a useful trend to
    # look at. total_count is kept for the subtitle so it's still visible
    # *that* older hikes exist and just aren't shown, not silently absent.
    total_count = len(rows)
    rows = [(stem, crossing_min) for stem, crossing_min in rows if crossing_min is not None]

    if not rows:
        body = '<p class="empty">No hikes with a computable rate yet.</p>'
    else:
        table_rows = "".join(
            f"<tr>"
            f"<td data-sort-value=\"{stem}\"><a href=\"{_hike_url(stem)}\">{_esc_attr(_date_display(stem))}</a></td>"
            f"<td data-sort-value=\"{crossing_min}\">{crossing_min:.1f} min per 0.30V</td>"
            f"</tr>"
            for stem, crossing_min in rows
        )
        body = (
            "<table><thead><tr>"
            "<th data-sort-type=\"text\">Hike</th>"
            "<th data-sort-type=\"number\">Battery Discharge Rate (4.00V→3.70V)</th>"
            "</tr></thead><tbody>"
            f"{table_rows}"
            "</tbody></table>"
        )

    with_data = len(rows)
    hidden = total_count - with_data
    if with_data:
        subtitle = f"{with_data} hike(s) with a computable rate."
        if hidden:
            subtitle += f" ({hidden} earlier hike(s) not shown -- predate this stat or too short to measure.)"
    else:
        subtitle = (
            "Nothing published yet -- check back after a hike."
            if total_count == 0
            else "No hikes with a computable rate yet."
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hike-izer &mdash; Battery Trend</title>
<style>
{_STYLE}
</style>
</head>
<body>
<main>
  <h1>Battery Discharge Trend</h1>
  <p class="subtitle">{subtitle}</p>
  <p class="caveat">A rough field indicator (minutes for the hiking-monitor's own field-mode battery readings to cross a fixed 4.00V&rarr;3.70V window each hike) -- not a substitute for a real bench current measurement. Lower is better (drained that slice faster).</p>
  <div class="top-nav"><a href="index.html">&larr; Calendar</a></div>
  {body}
  <footer>hike-izer</footer>
</main>
<script>
(function () {{
  var table = document.querySelector("table");
  if (!table) return;
  var tbody = table.querySelector("tbody");
  var ths = Array.prototype.slice.call(table.querySelectorAll("th"));
  // Rows already arrive sorted by hike date descending (Python's own sort
  // above) -- state starts matching that so the header's arrow reflects
  // reality on first load, not just after the first click.
  var state = {{col: 0, dir: -1}};

  function sortBy(colIndex) {{
    var type = ths[colIndex].dataset.sortType;
    var dir = (state.col === colIndex) ? -state.dir : 1;
    state = {{col: colIndex, dir: dir}};

    var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));
    rows.sort(function (a, b) {{
      var av = a.children[colIndex].dataset.sortValue;
      var bv = b.children[colIndex].dataset.sortValue;
      var cmp = type === "number" ? (parseFloat(av) - parseFloat(bv)) : av.localeCompare(bv);
      return cmp * dir;
    }});
    rows.forEach(function (r) {{ tbody.appendChild(r); }});

    ths.forEach(function (th, i) {{
      th.classList.remove("sort-asc", "sort-desc");
      if (i === colIndex) th.classList.add(dir === 1 ? "sort-asc" : "sort-desc");
    }});
  }}

  ths.forEach(function (th, i) {{
    th.addEventListener("click", function () {{ sortBy(i); }});
  }});
  ths[0].classList.add("sort-desc");
}})();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--srv-dir", required=True, help="Directory with *_hike-summary.meta.json sidecars, and where battery-trend.html is written")
    ap.add_argument("--private-dir", required=True, help="Directory with persisted <file_stem>_hike_data.json files")
    args = ap.parse_args()

    rows = _collect_rows(args.srv_dir, args.private_dir)

    out_path = Path(args.srv_dir) / "battery-trend.html"
    out_path.write_text(_render_page(rows), encoding="utf-8")

    with_data = sum(1 for _, c in rows if c is not None)
    print(f"Wrote {out_path}: {len(rows)} hikes indexed, {with_data} with a computable rate.", file=sys.stderr)


if __name__ == "__main__":
    main()
