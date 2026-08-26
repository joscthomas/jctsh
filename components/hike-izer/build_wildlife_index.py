#!/usr/bin/env python
"""
Hike-izer wildlife life-list page builder (CARD-0142).

Reads the persisted cross-hike species list (written by
components/hike-izer-orchestrator/wildlife_life_list.py every time a hike's
BirdNET Live export is parsed) and renders a single static page,
wildlife.html, listing every species ever heard while hiking -- one row per
species, sorted alphabetically by common name, each linking back to the
hike it was first heard on.

Modeled on build_calendar_index.py (same inline _STYLE, copied verbatim for
visual consistency across Hike-izer's own generated pages), which is
deliberately zero-JS. This page carries one small, self-contained exception
(CARD-0147): click-to-sort table columns, which genuinely needs client-side
interactivity -- there's no static-HTML way to let a viewer pick their own
sort order after the page is already rendered.

Meant to be re-run after every publish that has BirdNET data, alongside
build_calendar_index.py; see components/hike-izer-orchestrator/generation.py
for the two call sites.

Standard library only -- matches fetch_hike_data.py's/build_calendar_index.py's
convention.
"""

import argparse
import json
import sys
from html import escape as _esc_attr
from pathlib import Path
from urllib.parse import quote

import xeno_canto

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
  /* CARD-0210: Detections by Month / Life List Growth section headers */
  h2 { font-size: 1.15rem; margin: 2rem 0 0.5rem; }
  .subtitle { color: var(--ink-muted); font-size: 0.85rem; margin: 0 0 1.5rem; }
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
  td.scientific { font-style: italic; color: var(--ink-muted); }
  /* CARD-0174: reference-call speaker icon (xeno_canto.render_button_html()) */
  .audio-btn { background: none; border: none; cursor: pointer; font-size: 0.85em; padding: 0 0.2em; vertical-align: middle; line-height: 1; }
  .audio-btn:hover { opacity: 0.65; }

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


def wikipedia_url(scientific_name):
    """CARD-0143: built directly from scientific_name, no HTTP call/
    verification at build time -- constructed optimistically, same
    best-effort philosophy used elsewhere in this pipeline. Wikipedia
    article titles use underscores for spaces; its own redirect/search
    handling covers the rare scientific-name mismatch.

    CARD-0147: public (no leading underscore) -- templating.py imports this
    directly to link species names the same way on the per-hike Wildlife
    Heard (BirdNET) table, not just this page's own life-list table."""
    return f"https://en.wikipedia.org/wiki/{quote(scientific_name.replace(' ', '_'))}"


# CARD-0210: entry["hikes"] items are normally {"file_stem": ..., "count": ...}
# dicts -- these two accessors tolerate a not-yet-backfilled entry still
# holding a bare file_stem string (count assumed 1, unknown) rather than
# crashing on it, so a partially-migrated life list still renders.
def _hike_stem(h):
    return h["file_stem"] if isinstance(h, dict) else h


def _hike_count(h):
    return h["count"] if isinstance(h, dict) else 1


def _total_detections(entry):
    return sum(_hike_count(h) for h in entry["hikes"])


_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _detections_by_month(species):
    """CARD-0210: seasonality, collapsed across years per Joseph's own
    framing ("by month/season", not "by month in a specific year") --
    every hike a species was heard on contributes its detection count to
    that hike's own calendar month, regardless of which year it fell in."""
    detections = [0] * 12
    species_seen = [set() for _ in range(12)]
    for e in species:
        for h in e["hikes"]:
            month_idx = int(_hike_stem(h)[5:7]) - 1
            detections[month_idx] += _hike_count(h)
            species_seen[month_idx].add(e["scientific_name"])
    return [
        {"month": _MONTH_NAMES[i], "detections": detections[i], "species": len(species_seen[i])}
        for i in range(12)
    ]


def _new_species_by_year(species):
    """CARD-0210: "how the life list has grown over time" -- new species
    first heard per calendar year, from first_heard_file_stem's own year
    prefix. No new data needed -- every entry already carries this."""
    counts = {}
    for e in species:
        year = e["first_heard_file_stem"][:4]
        counts[year] = counts.get(year, 0) + 1
    return sorted(counts.items())


def _render_page(life_list, xeno_canto_key=None):
    species = sorted(life_list.values(), key=lambda e: e["common_name"].lower())

    if not species:
        body = '<p class="empty">No wildlife identified yet.</p>'
        month_section = ""
        year_section = ""
    else:
        # CARD-0174: reference-call speaker icon, right after the common
        # name -- see xeno_canto.py for the lookup/caching and shared
        # markup (same helper templating.py's per-hike Wildlife Heard
        # table uses, so both pages render identical markup).
        rows = "".join(
            f"<tr>"
            f"<td data-sort-value=\"{_esc_attr(e['common_name'].lower())}\">"
            f"<a href=\"{wikipedia_url(e['scientific_name'])}\" target=\"_blank\" rel=\"noopener\">{e['common_name']}</a>"
            f"{xeno_canto.render_button_html(xeno_canto.lookup(e['scientific_name'], xeno_canto_key), _esc_attr)}"
            f"</td>"
            f"<td class=\"scientific\" data-sort-value=\"{_esc_attr(e['scientific_name'].lower())}\">{e['scientific_name']}</td>"
            # first_heard_file_stem is already YYYY-MM-DD -- sorts correctly
            # as plain text, no separate date-parsing needed.
            f"<td data-sort-value=\"{e['first_heard_file_stem']}\">"
            f"<a href=\"{_hike_url(e['first_heard_file_stem'])}\">{e['first_heard_date']}</a></td>"
            f"<td data-sort-value=\"{len(e['hikes'])}\">{len(e['hikes'])}</td>"
            # CARD-0210: total detections across every hike, not just the
            # distinct-hike count the existing Hikes column already shows.
            f"<td data-sort-value=\"{_total_detections(e)}\">{_total_detections(e)}</td>"
            f"</tr>"
            for e in species
        )
        body = (
            "<table><thead><tr>"
            "<th data-sort-type=\"text\">Common Name</th>"
            "<th data-sort-type=\"text\">Scientific Name</th>"
            "<th data-sort-type=\"text\">First Heard</th>"
            "<th data-sort-type=\"number\">Hikes</th>"
            "<th data-sort-type=\"number\">Detections</th>"
            "</tr></thead><tbody>"
            f"{rows}"
            "</tbody></table>"
        )

        # CARD-0210: seasonality -- a plain calendar-order table, not a
        # chart. This page is deliberately zero-JS except the click-to-sort
        # exception above; a static month breakdown answers "which months
        # are busiest" without needing new interactivity, so it stays in
        # calendar order rather than being made sortable like the main table.
        month_rows = "".join(
            f"<tr><td>{m['month']}</td><td>{m['detections']}</td><td>{m['species']}</td></tr>"
            for m in _detections_by_month(species)
        )
        month_section = f"""
  <h2>Detections by Month</h2>
  <p class="subtitle">Collapsed across every year hiked -- shows which months tend to be most active, not any single year's own pattern.</p>
  <table><thead><tr><th>Month</th><th>Total Detections</th><th>Distinct Species Heard</th></tr></thead>
  <tbody>{month_rows}</tbody></table>"""

        year_data = _new_species_by_year(species)
        if len(year_data) > 1:
            year_rows = "".join(f"<tr><td>{y}</td><td>{n}</td></tr>" for y, n in year_data)
            year_section = f"""
  <h2>Life List Growth</h2>
  <table><thead><tr><th>Year</th><th>New Species First Heard</th></tr></thead>
  <tbody>{year_rows}</tbody></table>"""
        else:
            # Only one year of data so far -- a growth-over-time table with
            # a single row says nothing yet; omit rather than show it empty.
            year_section = ""

    count = len(species)
    subtitle = (
        f"{count} species identified via BirdNET Live across every hike so far."
        if count else "Nothing identified yet -- check back after a hike with BirdNET Live running."
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hike-izer &mdash; Wildlife Life List</title>
<style>
{_STYLE}
</style>
</head>
<body>
<main>
  <h1>Wildlife Life List</h1>
  <p class="subtitle">{subtitle}</p>
  <div class="top-nav"><a href="index.html">&larr; Calendar</a></div>
  {body}
  {month_section}
  {year_section}
  <footer>hike-izer</footer>
</main>
<script>
(function () {{
  var table = document.querySelector("table");
  if (!table) return;
  var tbody = table.querySelector("tbody");
  var ths = Array.prototype.slice.call(table.querySelectorAll("th"));
  // Rows already arrive sorted by common name ascending (Python's own
  // sort above) -- state starts matching that so the header's arrow
  // reflects reality on first load, not just after the first click.
  var state = {{col: 0, dir: 1}};

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
  ths[0].classList.add("sort-asc");

  // CARD-0174: speaker-icon click -> toggle play/pause on the button's own
  // next-sibling <audio> element (xeno_canto.render_button_html()'s
  // markup). Event delegation on the table, not a per-button listener.
  table.addEventListener("click", function (e) {{
    if (!e.target.classList || !e.target.classList.contains("audio-btn")) return;
    var audio = e.target.nextElementSibling;
    if (!audio) return;
    if (audio.paused) {{ audio.play(); }} else {{ audio.pause(); }}
  }});
}})();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--life-list", required=True, help="Path to the persisted wildlife_life_list.json")
    ap.add_argument("--srv-dir", required=True, help="Directory to write wildlife.html into")
    ap.add_argument("--xeno-canto-key", default=None, help="CARD-0174: Xeno-canto API key for reference-call speaker icons (optional -- icons omitted entirely when not provided)")
    args = ap.parse_args()

    try:
        with open(args.life_list, "r", encoding="utf-8") as f:
            life_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        life_list = {}

    out_path = Path(args.srv_dir) / "wildlife.html"
    out_path.write_text(_render_page(life_list, args.xeno_canto_key), encoding="utf-8")

    print(f"Wrote {out_path}: {len(life_list)} species indexed.", file=sys.stderr)


if __name__ == "__main__":
    main()
