#!/usr/bin/env python
"""
Hike-izer wildlife life-list page builder (CARD-0142).

Reads the persisted cross-hike species list (written by
components/hike-izer-orchestrator/wildlife_life_list.py every time a hike's
BirdNET Live export is parsed) and renders a single static page,
wildlife.html, listing every species ever heard while hiking -- one row per
species, sorted alphabetically by common name, each linking back to the
hike it was first heard on.

Deliberately zero-JS, same philosophy as build_calendar_index.py, which
this is modeled on directly (same inline _STYLE, copied verbatim for visual
consistency across Hike-izer's own generated pages).

Meant to be re-run after every publish that has BirdNET data, alongside
build_calendar_index.py; see components/hike-izer-orchestrator/generation.py
for the two call sites.

Standard library only -- matches fetch_hike_data.py's/build_calendar_index.py's
convention.
"""

import argparse
import json
import sys
from pathlib import Path

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
  }
  tr:last-child td { border-bottom: none; }
  td.scientific { font-style: italic; color: var(--ink-muted); }
  td a { color: var(--accent); text-decoration: none; }
  td a:hover { text-decoration: underline; }

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


def _render_page(life_list):
    species = sorted(life_list.values(), key=lambda e: e["common_name"].lower())

    if not species:
        body = '<p class="empty">No wildlife identified yet.</p>'
    else:
        rows = "".join(
            f"<tr>"
            f"<td>{e['common_name']}</td>"
            f"<td class=\"scientific\">{e['scientific_name']}</td>"
            f"<td><a href=\"{_hike_url(e['first_heard_file_stem'])}\">{e['first_heard_date']}</a></td>"
            f"<td>{len(e['hikes'])}</td>"
            f"</tr>"
            for e in species
        )
        body = (
            "<table><thead><tr>"
            "<th>Common Name</th><th>Scientific Name</th><th>First Heard</th><th>Hikes</th>"
            "</tr></thead><tbody>"
            f"{rows}"
            "</tbody></table>"
        )

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
  <footer>hike-izer</footer>
</main>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--life-list", required=True, help="Path to the persisted wildlife_life_list.json")
    ap.add_argument("--srv-dir", required=True, help="Directory to write wildlife.html into")
    args = ap.parse_args()

    try:
        with open(args.life_list, "r", encoding="utf-8") as f:
            life_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        life_list = {}

    out_path = Path(args.srv_dir) / "wildlife.html"
    out_path.write_text(_render_page(life_list), encoding="utf-8")

    print(f"Wrote {out_path}: {len(life_list)} species indexed.", file=sys.stderr)


if __name__ == "__main__":
    main()
