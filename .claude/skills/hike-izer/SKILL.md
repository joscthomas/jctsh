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

## Core model: a hiking event is a single day

**A hiking event is, by definition, a single calendar day** -- even if it's only a
few hours within that day. A multi-day backpacking or camping trip is a *series*
of single-day hiking events, not one event spanning the whole trip. **Generate one
summary file per day, not one combined summary across a multi-day trip.**

- If Joseph names a multi-day trip (e.g., "summarize the June 15 camping trip"),
  identify which individual days within that range actually have a **confirmed
  hike** (see "What counts as a hike" below, not just any GPS activity) and
  generate a separate `<date>_hike-summary.md` for each such day. Don't generate
  summaries for days with zero activity.
- **Session-crosses-midnight edge case:** a GPS session that starts before UTC
  midnight and continues after it (e.g., an evening hike that runs past midnight)
  belongs to the day it *started* on -- don't split one real hike into two
  day-summaries at the UTC boundary. Query a day's window as that day's
  00:00:00Z-23:59:59Z, but attribute any session by its start timestamp.
- If Joseph asks about "today" and the day is still in progress, that's a fine,
  normal single-day event -- see the `window_truncated_to_now` handling below.

## What counts as a hike (not just "GPS was active")

GPS activity alone doesn't mean a hike happened -- it could be a drive between
trailheads, GPS drift while sitting at camp, or (per Joseph's explicit rule)
something that shouldn't be happening at all: **he doesn't hike at night.**
`fetch_hike_data.py` classifies every candidate GPS session (`_gps_sessions` ->
`_classify_hike`) against two checks before calling it a real hike:

1. **Daylight.** At least 80% of the session's points must fall at civil twilight
   or brighter (sun elevation > -6deg). A session that's mostly in darkness isn't
   a hike.
2. **Walking-pace movement.** Median point-to-point speed must be roughly
   0.15-3.0 m/s (~0.3-6.7 mph). Slower reads as stationary (camp, parked, GPS
   drift); faster reads as vehicle travel. A session with only 1 GPS point can't
   have a speed computed at all and is rejected as "insufficient data," not
   assumed to be either.

Each session in `coverage.gps_track.sessions` carries `is_hike` (bool) and, when
`false`, a `rejection_reasons` list explaining exactly why -- never silently
dropped. `coverage.gps_track.hike_confirmed` is `true` if *any* session that day
passed both checks.

**If `hike_confirmed` is `false` for a requested day** -- whether because there
were zero GPS sessions at all, or because every session that existed got
rejected -- **do not write a normal hike narrative.** Instead, the summary must
say plainly that a hike could not be confirmed for that day, and explain why,
using the specific `rejection_reasons` (or noting zero GPS activity if that's the
case). Still report the other data that does exist for the day (Environmental
Data readings, Hiking Observations) if any -- the day isn't necessarily
uneventful, just not confirmable as a hike. This is a legitimate, expected output
shape, not an error -- see `hike-izer/summaries/2026-07-18_hike-summary.md` for
the pattern (written before this classification logic existed, but the same
"state plainly what's missing and why" spirit applies).

## When invoked

1. **Determine the day(s).** If Joseph names a specific date, that's the one day to
   summarize. If Joseph names a multi-day trip, first fetch the whole range once to
   find which individual days have real activity (see Core model above), then
   generate one summary per day with activity -- don't ask Joseph to pre-identify
   the days, figure it out from the data. If ambiguous, ask. Known trip: 2026-06-15
   through approximately 2026-06-29/07-03 had hiking activity only on 2026-06-17
   and 2026-06-18 (confirmed during initial testing) -- the rest of that range was
   camping/travel with no GPS sessions.

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
   expected-vs-actual data coverage, computes the `stats` block (temp/humidity/
   pressure/UV/battery ranges, and altitude range **in feet** -- `stats.altitude_ft`,
   already converted, don't reconvert `altitude_m` by hand), and computes sun
   position (elevation, azimuth, compass direction, and `alt_ft`) sampled every
   20th GPS trackpoint (override with `--sun-sample-every` for a denser or sparser
   sample). Read the resulting JSON to build the summary -- don't re-fetch or
   re-derive any of this by hand. **Feet is the primary and only unit for
   elevation/altitude in Hike-izer's output -- never report meters.**

4. **Write the narrative.** First check `coverage.gps_track.hike_confirmed` --
   if `false`, follow "What counts as a hike" above instead of the normal
   three-part structure. Otherwise, produce one Markdown file with these three
   parts, in this order. **Tables and prose must not repeat each other.** The data
   table/summary (part b) is where the raw numbers and ranges live. The narrative
   (part a) should read those numbers as context to build the story from, not
   restate them -- interpret, connect, and draw conclusions instead ("the trail
   climbed steadily through the afternoon" rather than "elevation ranged from
   X ft to Y ft, see table"; "conditions stayed comfortably mild all day" rather
   than restating the exact temperature range that's already in the table two
   sections down). If a sentence in the narrative would just be a number already
   sitting in the table, cut it or turn it into an observation instead.

   **a. Narrative story of the hike** -- a genuinely readable account of the day
   using the real data: how conditions evolved, elevation change described
   qualitatively (climbing, descending, flat) rather than by restating the exact
   figures, sun position at key moments (e.g., "the sun was low in the eastern
   sky, about 15deg above the horizon" near the start, or note if a stretch
   happened after sunset -- `daylight: false` in a sun sample), and the hiker's
   own voice observations woven in chronologically (they're already categorized --
   vegetation, wildlife, weather, sky, trail, etc. -- use that). Write this as a
   story, not a data dump.

   **b. Data tables/summary** -- the actual numbers: temperature range, humidity
   range, UV index range, elevation range/gain **in feet** (`stats.altitude_ft`),
   battery voltage range, duration, observation count by category. This is where
   precise figures belong -- the narrative shouldn't need to repeat them.

   **c. Expected vs. actual data coverage** -- an explicit, clearly labeled
   section (not buried in a footnote) reporting the `coverage` block from the
   fetched JSON: Environmental Data readings expected vs. actual (and coverage
   %), GPS trackpoints expected vs. actual, any gaps over 6 minutes with their
   timestamps, and how many Environmental Data readings had GPS coordinates
   successfully correlated vs. not. Frame this as a pipeline health check, not
   just a stat -- call out explicitly if coverage looks poor or GPS correlation
   looks broken, since surfacing exactly that is the point of this section.
   If `coverage.window_truncated_to_now` is `true` (requesting a window that
   extends into the future, e.g. "today" while it's still in progress), say so
   plainly -- the coverage numbers were computed through the current time, not
   the full requested window, so a lower-than-usual figure isn't necessarily a
   problem.

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
