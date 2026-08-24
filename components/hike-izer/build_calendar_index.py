#!/usr/bin/env python
"""
Hike-izer calendar home page builder (CARD-0092, reworked CARD-0105).

Scans a served directory for <date>_hike-summary.meta.json sidecar files
(one per published summary, written by both the interactive Skill and the
automatic orchestrator alongside their HTML output) and rebuilds one static
page per month that has at least one entry: calendar-<year>-<month>.html,
plus a copy of the most recent month at index.html so it's the site root.

Every day with a published summary renders the same way (highlighted,
linked) regardless of its hike_confirmed value (CARD-0105, 2026-07-28,
Joseph's call) -- the manifest's hike_confirmed field is still read and
kept for possible future use, it just no longer drives calendar styling.
The earlier confirmed/unconfirmed visual distinction was a Claude design
choice reported after the fact rather than agreed with Joseph up front;
this rework replaces it with an explicit decision instead.

Deliberately zero-JS, matching html-template.html's philosophy. Month
navigation (Prev/Next arrows) steps between months that actually have at
least one published summary, in chronological order -- not strict calendar-
month adjacency, so there's never a link to a page that doesn't exist. The
year picker is a native <details>/<summary> disclosure list (looks like a
dropdown, no JavaScript) linking each year to its most recent month page.

Meant to be re-run after every publish (both paths); see
.claude/skills/hike-izer/SKILL.md step 7 and
components/hike-izer-orchestrator/generation.py for the two call sites.

Standard library only -- matches fetch_hike_data.py's convention.
"""

import argparse
import calendar
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# CARD-0113: a day can now produce more than one hike-summary -- the first
# keeps the plain '<date>' stem, each later same-day one is '<date>-2',
# '<date>-3', etc. The trailing '(?:-(\d+))?' group is None for the first.
META_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:-(\d+))?_hike-summary\.meta\.json$")

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

  .cal-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
  }
  .cal-nav a, .cal-nav span {
    font-size: 0.9rem;
    text-decoration: none;
    color: var(--ink);
    padding: 0.4rem 0.7rem;
    border: 1px solid var(--line);
    border-radius: var(--radius);
  }
  .cal-nav a:hover { background: var(--surface-2); }
  .cal-nav span.disabled { color: var(--ink-faint); border-color: var(--line); }

  .top-links { margin-bottom: 1.25rem; }
  .top-links a {
    font-size: 0.9rem;
    text-decoration: none;
    color: var(--ink);
    padding: 0.4rem 0.7rem;
    border: 1px solid var(--line);
    border-radius: var(--radius);
  }
  .top-links a:hover { background: var(--surface-2); }

  .cal-year-picker { position: relative; }
  .cal-year-picker summary {
    cursor: pointer;
    font-size: 0.9rem;
    padding: 0.4rem 0.7rem;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    list-style: none;
  }
  .cal-year-picker summary::-webkit-details-marker { display: none; }
  .cal-year-picker summary::after { content: " \\25BE"; }
  .cal-year-picker[open] summary { background: var(--surface-2); }
  .cal-year-list {
    position: absolute;
    right: 0;
    top: 100%;
    margin-top: 0.25rem;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 0.35rem;
    list-style: none;
    z-index: 1;
  }
  .cal-year-list li a {
    display: block;
    padding: 0.35rem 0.9rem;
    color: var(--ink);
    text-decoration: none;
    border-radius: 6px;
    white-space: nowrap;
  }
  .cal-year-list li a:hover { background: var(--surface-2); }

  .month {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 1.1rem 1.1rem 1.3rem;
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
  .cal-day--logged {
    background: var(--accent);
    color: var(--accent-ink);
    box-shadow: var(--shadow);
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.25rem 0.1rem;
  }
  .cal-day-num {
    font-weight: 700;
    line-height: 1;
  }
  /* CARD-0118: every hike that day (including the first) gets its own
     stacked link below the day number, labeled with its local start time --
     replaces the old day-number-is-hike-1 / tiny-corner-number scheme.
     CSS Grid rows auto-size to their tallest cell, so a multi-hike day only
     grows the one week it's in. */
  .cal-day-hike {
    font-size: 0.55rem;
    line-height: 1.3;
    color: var(--accent-ink);
    text-decoration: none;
    font-weight: 600;
    white-space: nowrap;
  }
  .cal-day-hike:hover { text-decoration: underline; }
  .cal-day--logged:hover { filter: brightness(1.08); }

  footer {
    color: var(--ink-faint);
    font-size: 0.75rem;
    margin-top: 2rem;
    border-top: 1px solid var(--line);
    padding-top: 1rem;
  }
""".strip("\n")


def _format_time_compact(start_ts, offset_str):
    """CARD-0118: '7:07a' / '12:31p' style local time label for a hike's
    calendar-cell link. Returns None if either input is missing/unparseable
    (e.g. a meta.json written before this card existed) -- callers fall back
    to a plain hike-number label in that case."""
    if not start_ts or not offset_str:
        return None
    try:
        sign = 1 if offset_str[0] == "+" else -1
        hh, mm = offset_str[1:].split(":")
        offset_delta = timedelta(hours=sign * int(hh), minutes=sign * int(mm))
        dt = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(timezone.utc) + offset_delta
    except (ValueError, IndexError):
        return None
    hour12 = local.hour % 12 or 12
    return f"{hour12}:{local.minute:02d}{'a' if local.hour < 12 else 'p'}"


def scan_summaries(srv_dir):
    """Returns {(year, month, day): [(hike number, compact local start time
    label or None), ...]}, one list entry per <date>[-N]_hike-summary.meta.json
    found directly in srv_dir (CARD-0113: a day can produce more than one).
    hike_confirmed itself is read but no longer drives calendar styling
    (CARD-0105) -- every entry here renders the same way regardless."""
    entries = {}
    for p in Path(srv_dir).glob("*_hike-summary.meta.json"):
        m = META_RE.match(p.name)
        if not m:
            continue
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hike_num = int(m.group(4)) if m.group(4) else 1
        try:
            meta = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        label = _format_time_compact(meta.get("start_ts"), meta.get("offset_str"))
        entries.setdefault((y, mo, d), []).append((hike_num, label))
    for key in entries:
        entries[key].sort(key=lambda t: t[0])
    return entries


def _month_filename(year, month):
    return f"calendar-{year:04d}-{month:02d}.html"


def _render_calendar_grid(year, month, days_with_entries):
    dow_headers = "".join(f'<div class="cal-dow">{d}</div>' for d in ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"])
    first_weekday_sun0 = (calendar.monthrange(year, month)[0] + 1) % 7  # Python's Mon=0 -> Sun=0
    num_days = calendar.monthrange(year, month)[1]

    cells = ['<div class="cal-day cal-day--empty"></div>' for _ in range(first_weekday_sun0)]
    for day in range(1, num_days + 1):
        hikes = days_with_entries.get(day)
        if hikes:
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
            # CARD-0118: day number is a plain label (not a link); every
            # hike that day -- including the first -- gets its own stacked
            # link below it, labeled with its local start time. Uniform
            # across 1-hike and multi-hike days, rather than special-casing
            # hike #1 vs. later ones (CARD-0113's original scheme).
            hike_links = "".join(
                f'<a class="cal-day-hike" href="{date_str}{"" if n == 1 else f"-{n}"}_hike-summary.html">'
                f'{label or f"#{n}"}</a>'
                for n, label in hikes
            )
            cells.append(
                f'<div class="cal-day cal-day--logged"><span class="cal-day-num">{day}</span>{hike_links}</div>'
            )
        else:
            cells.append(f'<div class="cal-day cal-day--none">{day}</div>')

    month_name = calendar.month_name[month]
    return (
        f'<div class="month"><h2>{month_name}</h2>'
        f'<div class="cal-grid">{dow_headers}{"".join(cells)}</div></div>'
    )


def _render_nav(months_sorted, index, years_latest_month):
    # months_sorted is chronological (oldest first); index is this page's position in it.
    current_year = months_sorted[index][0]
    prev_link = (
        f'<a href="{_month_filename(*months_sorted[index - 1])}">&larr; {calendar.month_abbr[months_sorted[index - 1][1]]} {months_sorted[index - 1][0]}</a>'
        if index > 0
        else '<span class="disabled">&larr;</span>'
    )
    next_link = (
        f'<a href="{_month_filename(*months_sorted[index + 1])}">{calendar.month_abbr[months_sorted[index + 1][1]]} {months_sorted[index + 1][0]} &rarr;</a>'
        if index < len(months_sorted) - 1
        else '<span class="disabled">&rarr;</span>'
    )
    year_items = "".join(
        f'<li><a href="{_month_filename(*years_latest_month[y])}">{y}</a></li>'
        for y in sorted(years_latest_month.keys(), reverse=True)
    )
    # Summary shows the year being viewed (not a generic "Year" label) --
    # doubles as the display, per Joseph's request (2026-07-28), not just the
    # dropdown trigger.
    year_picker = (
        f'<details class="cal-year-picker"><summary>{current_year}</summary>'
        f'<ul class="cal-year-list">{year_items}</ul></details>'
    )
    return f'<div class="cal-nav">{prev_link}{year_picker}{next_link}</div>'


def _render_page(months_sorted, index, by_month, years_latest_month):
    year, month = months_sorted[index]
    nav = _render_nav(months_sorted, index, years_latest_month)
    grid = _render_calendar_grid(year, month, by_month[(year, month)])
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
  <p class="subtitle">Days with a published summary are highlighted and link to it.</p>
  <div class="top-links"><a href="wildlife.html">Wildlife Life List &rarr;</a> <a href="battery-trend.html">Battery Trend &rarr;</a></div>
  {nav}
  {grid}
  <footer>hike-izer</footer>
</main>
</body>
</html>
"""


def _empty_page():
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
  <p class="empty">No hike summaries published yet.</p>
  <div class="top-links"><a href="wildlife.html">Wildlife Life List &rarr;</a> <a href="battery-trend.html">Battery Trend &rarr;</a></div>
  <footer>hike-izer</footer>
</main>
</body>
</html>
"""


def build_pages(entries):
    """Returns {filename: html}. Always includes 'index.html' (a copy of the
    most recent month, or the empty-state page if nothing's published yet),
    plus one calendar-<year>-<month>.html per month that has an entry."""
    if not entries:
        return {"index.html": _empty_page()}

    by_month = {}
    for (y, mo, d), hike_nums in entries.items():
        by_month.setdefault((y, mo), {})[d] = hike_nums
    months_sorted = sorted(by_month.keys())  # chronological, oldest first

    years_latest_month = {}
    for y, mo in months_sorted:
        if y not in years_latest_month or mo > years_latest_month[y][1]:
            years_latest_month[y] = (y, mo)

    pages = {}
    for i, (y, mo) in enumerate(months_sorted):
        pages[_month_filename(y, mo)] = _render_page(months_sorted, i, by_month, years_latest_month)

    latest_index = len(months_sorted) - 1
    pages["index.html"] = pages[_month_filename(*months_sorted[latest_index])]
    return pages


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--srv-dir", required=True, help="Directory containing published *_hike-summary.meta.json files")
    args = ap.parse_args()

    entries = scan_summaries(args.srv_dir)
    pages = build_pages(entries)

    out_dir = Path(args.srv_dir)
    for filename, html in pages.items():
        (out_dir / filename).write_text(html, encoding="utf-8")

    print(
        f"Wrote {len(pages)} page(s) ({', '.join(sorted(pages))}) to {out_dir}: "
        f"{len(entries)} summar{'y' if len(entries) == 1 else 'ies'} indexed.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
