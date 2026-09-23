#!/usr/bin/env python
"""
Hike-izer scat life-list page builder (CARD-0308).

Reads the persisted cross-hike species list (written by
components/hike-izer-orchestrator/scat_life_list.py every time a hike's
photos are captioned) and renders a single static page, scat.html, listing
every species whose scat has been confidently identified while hiking --
one row per species, sorted alphabetically by common name, each linking
back to the hike it was first identified on.

Deliberately a leaner v1 than build_wildlife_index.py (CARD-0142), not a
full feature-for-feature copy -- that page's seasonality tables
(CARD-0210), sticky-header JS (CARD-0278), and Xeno-canto audio widget
(CARD-0174) were each real, separately-motivated additions built after
real use of the *wildlife* page specifically, not part of its original
build. Following this project's own iterative-not-speculative discipline,
this page starts with the same core species table and matching visual
_STYLE for site-wide consistency, and picks up equivalent features later
only if real use of *this* page shows they're actually wanted here too.

Meant to be re-run after every publish that has scat data, alongside
build_calendar_index.py/build_wildlife_index.py; see
components/hike-izer-orchestrator/generation.py for the call sites.

Standard library only -- matches fetch_hike_data.py's/build_calendar_index.py's
convention.
"""

import argparse
import json
from html import escape as _esc_attr
from pathlib import Path
from urllib.parse import quote

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
    border-collapse: separate;
    border-spacing: 0;
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
  }
  tr:last-child td { border-bottom: none; }
  td.scientific { font-style: italic; color: var(--ink-muted); }
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
    """Same construction as build_wildlife_index.py's own helper (CARD-0143)
    -- built directly from scientific_name, no HTTP call/verification at
    build time. Wikipedia article titles use underscores for spaces; its
    own redirect/search handling covers the rare scientific-name mismatch."""
    return f"https://en.wikipedia.org/wiki/{quote(scientific_name.replace(' ', '_'))}"


def _total_identifications(entry):
    return sum(h["count"] for h in entry["hikes"])


def _render_page(life_list):
    species = sorted(life_list.values(), key=lambda e: e["common_name"].lower())

    if not species:
        body = '<p class="empty">No scat identified yet.</p>'
    else:
        rows = "".join(
            f"<tr>"
            f"<td><a href=\"{wikipedia_url(e['scientific_name'])}\" target=\"_blank\" rel=\"noopener\">{_esc_attr(e['common_name'])}</a></td>"
            f"<td class=\"scientific\">{_esc_attr(e['scientific_name'])}</td>"
            f"<td><a href=\"{_hike_url(e['first_identified_file_stem'])}\">{e['first_identified_date']}</a></td>"
            f"<td>{len(e['hikes'])}</td>"
            f"<td>{_total_identifications(e)}</td>"
            f"</tr>"
            for e in species
        )
        body = (
            "<table><thead><tr>"
            "<th>Common Name</th>"
            "<th>Scientific Name</th>"
            "<th>First Identified</th>"
            "<th>Hikes</th>"
            "<th>Identifications</th>"
            "</tr></thead><tbody>"
            f"{rows}"
            "</tbody></table>"
        )

    count = len(species)
    subtitle = (
        f"{count} species' scat confidently identified from hike photos so far."
        if count else "Nothing identified yet -- check back after a hike with a confidently-identified scat photo."
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hike-izer &mdash; Scat Life List</title>
<style>
{_STYLE}
</style>
</head>
<body>
<main>
  <h1>Scat Life List</h1>
  <p class="subtitle">{subtitle}</p>
  <div class="top-nav"><a href="index.html">&larr; Calendar</a></div>
  {body}
  <footer>hike-izer</footer>
</main>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--life-list", required=True, help="Path to the persisted scat_life_list.json")
    ap.add_argument("--srv-dir", required=True, help="Directory to write scat.html into")
    args = ap.parse_args()

    try:
        with open(args.life_list, "r", encoding="utf-8") as f:
            life_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        life_list = {}

    out_path = Path(args.srv_dir) / "scat.html"
    out_path.write_text(_render_page(life_list), encoding="utf-8")

    print(f"Wrote {out_path}: {len(life_list)} species indexed.")


if __name__ == "__main__":
    main()
