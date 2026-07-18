---
name: hike-izer
description: Generate a narrative Markdown summary of a JCTsh hiking trip from sensor, GPS, and observation data (Google Sheets). Use when Joseph asks to summarize, narrate, recap, or review a specific hike or hiking trip by date -- e.g. "summarize the June 15 hike", "write up last week's trip", "how did the hiking monitor do on the camping trip".
---

# Hike-izer

Generates a Markdown narrative summary of a hiking trip using JCTsh's hiking-sensor
data pipeline (Environmental Data, Hiking Observations, GPS Track -- all in the
"JCTsh Environmental Data" Google Sheets workbook). CARD-0073 on `kanban-board.md`
is this skill's tracking card; its v1 scope note there is the source of truth for
what's in/out of scope if this doc and the card ever disagree.

## When invoked

1. **Determine the date range.** If Joseph names a specific date or trip, use that.
   If ambiguous, ask for a start/end date (ISO 8601, UTC). Known trip: 2026-06-15
   through approximately 2026-06-29/07-03 is the first proven test case with full
   data (confirmed 6,202 Environmental Data rows during initial testing).

2. **Get credentials.** Read `credentials.local.md` (gitignored, repo root) for the
   Apps Script `Deployment URL` and `API_KEY` under "Google Apps Script --
   Environmental Data Pipeline". Never hardcode these in this skill file, in the
   helper script, or in the generated summary -- they're gitignored for a reason.

3. **Fetch and analyze the data.** Run the helper script (lives in `components/hike-izer/`, not this skill's own directory -- code and generated output are kept separate: code under `components/hike-izer/`, results under the top-level `hike-izer/summaries/`):

   ```
   python components/hike-izer/fetch_hike_data.py \
     --start <ISO8601 start> --end <ISO8601 end> \
     --url <Deployment URL> --key <API_KEY> \
     --out <scratch path>/hike_data.json
   ```

   This fetches all three sheets via the `action=export` endpoint, computes
   expected-vs-actual data coverage, and computes sun position (elevation,
   azimuth, compass direction) sampled every 20th GPS trackpoint (override with
   `--sun-sample-every` for a denser or sparser sample). Read the resulting JSON
   to build the summary -- don't re-fetch or re-derive any of this by hand.

4. **Write the narrative.** Produce one Markdown file with these three parts, in
   this order:

   **a. Narrative story of the hike** -- a genuinely readable account of the trip
   using the real data: temperature/humidity/UV trends, elevation changes (from
   GPS `altitude_m`), sun position at key moments (e.g., "the sun was low in the eastern
   sky, about 15deg above the horizon" near the start, or note if a stretch
   happened after sunset -- `daylight: false` in a sun sample), and the hiker's
   own voice observations woven in chronologically (they're already categorized --
   vegetation, wildlife, weather, sky, trail, etc. -- use that). Write this as a
   story, not a data dump.

   **b. Data tables/summary** -- key stats: temperature range, humidity range, UV
   index range, elevation range/gain, battery voltage trend, duration, observation
   count by category.

   **c. Expected vs. actual data coverage** -- an explicit, clearly labeled
   section (not buried in a footnote) reporting the `coverage` block from the
   fetched JSON: Environmental Data readings expected vs. actual (and coverage
   %), GPS trackpoints expected vs. actual, any gaps over 6 minutes with their
   timestamps, and how many Environmental Data readings had GPS coordinates
   successfully correlated vs. not. Frame this as a pipeline health check, not
   just a stat -- call out explicitly if coverage looks poor or GPS correlation
   looks broken, since surfacing exactly that is the point of this section.

5. **Save the output** to `hike-izer/summaries/<start-date>_hike-summary.md`
   (create the directory if it doesn't exist). Tell Joseph the file path when done.

## Explicitly out of scope for v1 (deferred -- see CARD-0073)

- Photos (Immich integration not built)
- Live/historical weather API (no source picked)
- Compass/heading of the *hiker* -- only the sun's compass direction is computed,
  from pure astronomy, not which way the hiker was facing (not tracked by any
  sensor)
- Automatic triggering -- this only runs when asked
- Rendered web page output -- Markdown only

## Notes on the data

- Environmental Data's `lat`/`lon` are often blank even when GPS Track has real
  coordinates for that time window -- a known correlation gap (Node-RED's GPS
  lookup only matches within +/-5 minutes; see `components/hiking-sensor/data-pipeline.md`).
  The fetch script uses GPS Track directly for sun-position calculations, so this
  gap doesn't block sun position -- but it's worth surfacing in the coverage
  section since a high miss rate might indicate a real pipeline issue.
- `rssi_dbm == 0` means the reading was taken while the device had no WiFi (normal
  "field mode" while hiking, not an error).
- Full Environmental Data schema (A-Z) and the `action=export` API reference:
  `components/hiking-sensor/data-pipeline.md`.
