#!/usr/bin/env python
"""
Hike-izer calendar home page builder (CARD-0092).

Scans a served directory for <date>_hike-summary.meta.json sidecar files
(one per published summary, written by both the interactive Skill and the
automatic orchestrator alongside their HTML output) and rebuilds index.html
as a month-by-month calendar grid, most recent month first. Confirmed-hike
days link to their summary and render distinctly from published-but-not-
confirmed days (the interactive Skill still publishes "couldn't confirm a
hike" reports -- CARD-0100 made the automatic path skip those entirely, so
this distinction only ever shows up for interactively-published days).

Deliberately zero-JS, matching html-template.html's philosophy -- a plain
CSS grid is enough for a calendar. Meant to be re-run after every publish
(both paths); see .claude/skills/hike-izer/SKILL.md step 7 and
components/hike-izer-orchestrator/generation.py for the two call sites.

Standard library only -- matches fetch_hike_data.py's convention.
"""

import argparse
import calendar
import json
import re
import sys
from pathlib import Path

META_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})_hike-summary\.meta\.json$")

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
  .subtitle { color: var(--ink-muted); font-size: 0.85rem; margin: 0 0 2rem; }
  .empty { color: var(--ink-faint); font-style: italic; }

  .month {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 1.1rem 1.1rem 1.3rem;
    margin-bottom: 1.5rem;
  }
  .month h2 {
    font-size: 1rem;
    margin: 0 0 0.85rem;
    color: var(--ink-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 0.3rem;
  }
  .cal-dow {
    font-size: 0.65rem;
    text-align: center;
    color: var(--ink-faint);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding-bottom: 0.2rem;
  }
  .cal-day {
    aspect-ratio: 1 / 1;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    font-size: 0.85rem;
  }
  .cal-day--empty { visibility: hidden; }
  .cal-day--none { color: var(--ink-faint); }
  .cal-day--not-confirmed {
    color: var(--ink-muted);
    border: 1px solid var(--line-strong);
    text-decoration: none;
  }
  .cal-day--hike {
    background: var(--accent);
    color: var(--accent-ink);
    font-weight: 700;
    text-decoration: none;
    box-shadow: var(--shadow);
  }
  .cal-day--hike:hover, .cal-day--not-confirmed:hover { filter: brightness(1.08); }

  footer {
    color: var(--ink-faint);
    font-size: 0.75rem;
    margin-top: 2rem;
    border-top: 1px solid var(--line);
    padding-top: 1rem;
  }
""".strip("\n")


def scan_summaries(srv_dir):
    """Returns {(year, month, day): hike_confirmed_bool}, one entry per
    <date>_hike-summary.meta.json found directly in srv_dir."""
    entries = {}
    for p in Path(srv_dir).glob("*_hike-summary.meta.json"):
        m = META_RE.match(p.name)
        if not m:
            continue
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        entries[(y, mo, d)] = bool(data.get("hike_confirmed"))
    return entries


def _render_month(year, month, days_in_month_map):
    dow_headers = "".join(f'<div class="cal-dow">{d}</div>' for d in ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"])
    first_weekday_sun0 = (calendar.monthrange(year, month)[0] + 1) % 7  # Python's Mon=0 -> Sun=0
    num_days = calendar.monthrange(year, month)[1]

    cells = ['<div class="cal-day cal-day--empty"></div>' for _ in range(first_weekday_sun0)]
    for day in range(1, num_days + 1):
        state = days_in_month_map.get(day)
        if state is True:
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
            cells.append(
                f'<a class="cal-day cal-day--hike" href="{date_str}_hike-summary.html">{day}</a>'
            )
        elif state is False:
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
            cells.append(
                f'<a class="cal-day cal-day--not-confirmed" href="{date_str}_hike-summary.html">{day}</a>'
            )
        else:
            cells.append(f'<div class="cal-day cal-day--none">{day}</div>')

    month_name = calendar.month_name[month]
    return (
        f'<div class="month"><h2>{month_name} {year}</h2>'
        f'<div class="cal-grid">{dow_headers}{"".join(cells)}</div></div>'
    )


def build_index_html(entries):
    if not entries:
        body = '<p class="empty">No hike summaries published yet.</p>'
    else:
        by_month = {}
        for (y, mo, d), confirmed in entries.items():
            by_month.setdefault((y, mo), {})[d] = confirmed
        months_sorted = sorted(by_month.keys(), reverse=True)
        body = "".join(_render_month(y, mo, by_month[(y, mo)]) for y, mo in months_sorted)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hike-izer</title>
<style>
{_STYLE}
</style>
</head>
<body>
<main>
  <h1>Hike-izer</h1>
  <p class="subtitle">Confirmed hikes are highlighted and link to their summary. Days with a published but unconfirmed report show outlined.</p>
  {body}
  <footer>hike-izer &middot; CARD-0092</footer>
</main>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--srv-dir", required=True, help="Directory containing published *_hike-summary.meta.json files")
    ap.add_argument("--out", default=None, help="Output path (default: <srv-dir>/index.html)")
    args = ap.parse_args()

    entries = scan_summaries(args.srv_dir)
    html = build_index_html(entries)

    out_path = args.out or str(Path(args.srv_dir) / "index.html")
    Path(out_path).write_text(html, encoding="utf-8")
    print(f"Wrote {out_path}: {len(entries)} summar{'y' if len(entries) == 1 else 'ies'} indexed.", file=sys.stderr)


if __name__ == "__main__":
    main()
