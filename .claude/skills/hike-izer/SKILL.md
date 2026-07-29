---
name: hike-izer
description: Generate a narrative HTML summary of a JCTsh hiking trip from sensor, GPS, and observation data (Google Sheets). Use when Joseph asks to summarize, narrate, recap, or review a specific hike or hiking trip by date -- e.g. "summarize the June 15 hike", "write up last week's trip", "how did the hiking monitor do on the camping trip".
---

# Hike-izer

Generates a narrative HTML summary of a hiking trip using JCTsh's hiking-monitor
data pipeline (Environmental Data, Hiking Observations, GPS Track, Hike Start
Forecast -- all in the "JCTsh Environmental Data" Google Sheets workbook).
CARD-0073 on `kanban-board.md` is this skill's tracking card; its v1 scope note
there is the source of truth for what's in/out of scope if this doc and the
card ever disagree. CARD-0083 tracks the weather-forecast-at-hike-start feature
specifically (step 4 below). **HTML is the sole output format** (CARD-0091,
2026-07-28) -- v1 (CARD-0073) originally also produced a `.md` file, dropped
once CARD-0088 gave the HTML output a real public URL and made it unambiguously
the deliverable Joseph actually reads/shares.

## Core model: a hiking event is a detected hike session, not a calendar day

**A hiking event is a single detected hike session** (`is_hike: true` in
`coverage.gps_track.sessions`) -- **not** a calendar day (revised CARD-0113; a day
is just the query unit used to find sessions, same reasoning the automatic
pipeline now applies). Two real hikes on the same day are two events, not one
merged report -- summing their distances or blending their elevation ranges into
a single figure is exactly the bug CARD-0113 fixed. A multi-day backpacking or
camping trip is a *series* of single-day query windows, each of which may itself
contain more than one real session.

- Query a day's window as that day's 00:00:00Z-23:59:59Z (the interactive flow has
  no webhook-precise session bounds to narrow to, unlike the automatic path) --
  but generate one summary file **per `is_hike` session found**, not one per day
  queried.
- **Naming (CARD-0113):** the first hike-summary for a given date keeps the plain
  `<date>_hike-summary.html` stem; a second real hike on that same date gets
  `<date>-2_hike-summary.html`, a third `<date>-3_hike-summary.html`, etc. Never
  rename an existing file to make room for this -- the first hike found keeps
  stem `1` (no `-1` suffix) regardless of discovery order.
- If Joseph names a multi-day trip (e.g., "summarize the June 15 camping trip"),
  identify which individual days within that range actually have at least one
  **confirmed hike** (see "What counts as a hike" below, not just any GPS
  activity), and within each such day, one summary per session found. Don't
  generate summaries for days with zero activity.
- **Session-crosses-midnight edge case:** a GPS session that starts before UTC
  midnight and continues after it (e.g., an evening hike that runs past midnight)
  belongs to the day it *started* on -- don't split one real hike into two
  day-summaries at the UTC boundary.
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
Data readings, Hiking Observations, and the Hike Start Forecast section per
CARD-0083 below if a forecast was captured) if any -- the day isn't necessarily
uneventful, just not confirmable as a hike. This is a legitimate, expected output
shape, not an error -- state plainly what's missing and why, same as any other
section.

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

   This fetches all four sheets (Environmental Data, Hiking Observations, GPS
   Track, and Hike Start Forecast) via the `action=export` endpoint, computes
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
   structure below. Otherwise, produce the HTML output with the following
   parts, in this order. **Target roughly 250 words total across all
   paragraphs (added 2026-07-29, after review of a real 471-word narrative
   that restated several tables and gave a tangential landmark a full
   paragraph)** -- a tight, well-chosen set of observations beats an
   exhaustive one; if it's running long, cut before padding. **Tables and prose
   must not repeat each other -- including
   paraphrased restatement.** The data table/summary (part b) is where the raw
   numbers and ranges live. The narrative (part a) should read those numbers as
   context to build the story from, not restate them -- interpret, connect, and
   draw conclusions instead ("the trail climbed steadily through the afternoon"
   rather than "elevation ranged from X ft to Y ft, see table"; "conditions
   stayed comfortably mild all day" rather than restating the exact temperature
   range that's already in the table two sections down). **Restating a number in
   softer words is still restating it** -- "wrapped up in a little over half an
   hour" for a 32-minute duration, or "roughly two miles of ground" for a 2.0 mi
   distance, tell the reader nothing they can't already see in the stat row
   above; avoiding digits doesn't make a sentence an exception to this rule. The
   Weather Forecast at Hike Start section (below) is its own table too --
   don't re-describe conditions ("cool and calm," "no chance of rain") in the
   narrative just because it's phrased as prose there instead of numbers; the
   same non-redundancy rule applies across section boundaries, not just within
   one table.
   Before including a sentence built from a table number, ask: does this connect
   the number to something else -- what it felt like, why it happened, what it
   enabled or prevented -- or does it just describe the number in prose? If it's
   the latter, cut it. **This applies to empty-data reporting too, more strictly
   than before (tightened 2026-07-29):** if a data source came back empty, the
   Data Summary table and Coverage section already show that plainly (a blank
   "not available" cell, an actual/expected count of zero) -- don't add a prose
   sentence that just restates the absence ("the sensor logged nothing this
   session, so there's no temperature story to tell" tells the reader nothing
   the table doesn't already show). Only mention an empty data source in prose
   if there's something genuinely narrative to say *about why*, not just *that*
   it's empty. Never point ahead to
   "detailed in the coverage section below" -- that section already exists and
   speaks for itself; a forward-reference like that is a tell that the sentence
   shouldn't be in the narrative at all. Same principle for GPS confirmation:
   don't editorialize that the GPS track "confirmed a steady walking pace" or
   similar -- `hike_confirmed: true` is exactly what put the page in this normal
   narrative path rather than the `false` path above, so it's already implied,
   and trackpoint coverage itself belongs to the Coverage section (part c), not
   the story. Detailed pace/speed commentary is reserved for the richer stats a
   future card is expected to add (CARD-0110) -- don't anticipate it here.

   **Weather forecast at hike start (added 2026-07-24, CARD-0083)** -- shown
   before part (a), since it's context the reader wants before the story
   itself ("here's what was forecast going in"). **Applies on both the
   normal and `hike_confirmed: false` paths** -- the forecast is captured
   independently of hike-confirmation status (it fires off the first raw GPS
   point of the day, before any hike-vs-not-hike classification happens --
   moved from the first Hiking Observation by CARD-0106, since that was
   optional and arbitrarily timed relative to when the hike actually started),
   so it counts as "other data that does
   exist" per the `hike_confirmed: false` handling above and should be
   included there too, not just in the three-part normal structure. If `hike_start_forecast` has
   an entry, report its five fields plainly: temperature, precipitation
   chance, wind, humidity, UV index. This is a live snapshot captured the
   moment the hike began (the first GPS point of the day triggers an
   Open-Meteo fetch server-side, using that point's own coordinates) -- not
   a forecast checked whenever the summary happens to be
   generated later, and not actual observed conditions (a separate,
   still-undecided item under CARD-0074). If `hike_start_forecast` is empty
   (the hike predates this feature, or the capture failed that day), still
   include this section, but say plainly that no forecast was captured --
   never fabricate a value. This section is **always rendered** (never
   omitted the way Photos is) -- with five values it's the same "not
   available" convention as the hero stat row, not the gallery-omission
   convention; see `html-template.html`'s comments.

   **a. Narrative story of the hike** -- a genuinely readable account of the day
   using the real data: how conditions evolved, elevation change described
   qualitatively (climbing, descending, flat) rather than by restating the exact
   figures, sun position at key moments described the same qualitative way (e.g.,
   "the sun was still low in the eastern sky, casting long morning light" rather
   than quoting the exact elevation degrees -- those now live in the Data
   Summary table's Sun Elevation Range / Sun Direction rows, CARD-0109 --
   or note if a stretch happened after sunset -- `daylight: false` in a sun
   sample), and the hiker's own voice observations woven in chronologically
   (they're already categorized -- vegetation, wildlife, weather, sky, trail,
   etc. -- use that). Write this as a story, not a data dump. **Sun position and
   route shape are optional color, not required beats (added 2026-07-29)** --
   include them only if there's something genuinely worth saying (a notably
   dramatic light or an unusual route shape); a routine "gently undulating loop"
   or "the sun climbed gradually over the half hour" adds length without adding
   anything the reader couldn't guess. When in doubt, cut it rather than include
   it for completeness.

   **Place context (added 2026-07-28, CARD-0108)** -- `place_context` is a flat
   list of independently-true facts about where the hike happened: named
   park/school/trail and its operator, researched history, answers to things
   the hiker wondered aloud. Gathered before this call specifically so it can
   be woven into the story, not bolted on as a separate section -- weave it in,
   don't list it. If an observation is a genuine open question (e.g. "wonder
   what that stands for"), don't report that the question was asked -- it's
   already visible in the Full Observations Log table -- just answer it, tied
   to that moment in the story. Apply the same non-redundancy discipline here
   as with the data tables: never state the same fact twice, even phrased
   differently or arrived at from two different original sources (e.g. an
   operator confirmed by both the location data and a researched fact appears
   once, not twice). **Weight space by how central a fact is to *this* hike's
   actual route, not by how much material was found about it (added 2026-07-29,
   after a real narrative gave a full paragraph -- founding year, mascot
   history -- to a school from a *different* day's hike from the same starting
   point, while the school actually passed today got one clause).** A
   well-documented public landmark with lots of searchable history is not
   automatically more relevant than an obscure one that's actually on today's
   path -- if it's uncertain whether something was genuinely encountered versus
   just nearby the start, say less about it, not more. (`place_context.py`'s own
   accuracy here is tracked separately, CARD-0112 -- this is the writing-side
   guard regardless of how good the underlying data gets.) If `place_context` is empty, say nothing about it --
   unlike the weather forecast, there's no standing reader expectation that
   this exists for every hike, so there's nothing to report the absence of.

   **b. Data tables/summary** -- the actual numbers: temperature range, humidity
   range, UV index range, elevation range/gain **in feet** (`stats.altitude_ft`),
   battery voltage range, duration, observation count by category. This is where
   precise figures belong -- the narrative shouldn't need to repeat them.

   **Full observations table (added 2026-07-23):** in addition to the observation
   *count* by category above, include the complete list of that day's Hiking
   Observations as its own table -- columns Time (local, MST, not the sheet's raw
   UTC), Observation (the raw text as logged, don't paraphrase or clean it up),
   and Categories (comma-joined, or an em dash if the categories array is empty).
   One row per observation, in chronological order. This is the raw record the
   narrative draws its color from -- the narrative interprets and weaves a
   selection of these into a story (per the non-redundant rule above), but the
   table is where the complete, unabridged list lives. Include this table whenever
   `hiking_observations` is non-empty, including on the `hike_confirmed: false`
   path -- it's exactly the kind of "other data that does exist" that path already
   calls for reporting.

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

5. **Generate the styled HTML output (CARD-0081, Levels 1-2)** at
   `hike-izer/summaries/<start-date>_hike-summary.html` (create the directory
   if it doesn't exist). Use `components/hike-izer/html-template.html` as the
   fixed structural/CSS reference: copy its `<style>` block **verbatim** (this
   is what keeps output visually consistent across independent runs -- don't
   restyle it per hike), then fill in its sections with the content from step
   4 above. On top of that content, the template has a stat-row hero up top
   (Date, Duration, Distance, Elevation Gain):
   - **Distance** -- `stats.distance_mi` (only present when
     `coverage.gps_track.hike_confirmed` is `true`; `null` otherwise)
   - **Elevation Gain** -- `stats.altitude_ft.gain_ft`
   - **Duration** -- the confirmed hike session's `duration_minutes` from
     `coverage.gps_track.sessions`, or the Hiking Observations time span if
     GPS is unavailable (see the `hike_confirmed: false` path)
   - Any stat with no real source for that day must show as **"not
     available"** (`.stat__value--na` in the template), never a blank or a
     misleading zero.
   See `components/hike-izer/html-template.html`'s own comments for the exact
   section-by-section mapping. The Weather Forecast at Hike Start section
   (CARD-0083, step 4 above) uses the template's `.forecast-row` -- always
   rendered (unlike Photos), with each card showing **"not available"**
   (`.stat__value--na`) instead of a value when `hike_start_forecast` is
   empty. Levels 3-5 (embedded maps/charts, interactive hover-sync) are
   **out of scope here** -- tracked separately on `kanban-board.md` as
   CARD-0082. Hosting/publishing is step 7 below (CARD-0088). Tell Joseph the
   file path when done.

   **Also write the calendar sidecar (CARD-0092)** at
   `hike-izer/summaries/<start-date>_hike-summary.meta.json`:
   ```json
   {"hike_confirmed": true}
   ```
   (or `false` on the `hike_confirmed: false` path above). This is what the
   calendar home page (step 7) reads to tell real hikes from published-but-
   unconfirmed reports -- don't skip it even on a `hike_confirmed: false` day.

6. **Fetch and embed photos/videos (CARD-0084).** Read Joseph's Immich API
   key from `credentials.local.md` ("Immich (Docker, on photo-server)" --
   Joseph's key, not Robin's) and the Immich Web UI URL from the same
   section. Run:

   ```
   python components/hike-izer/fetch_hike_photos.py \
     --data <scratch path>/hike_data.json \
     --immich-url <Immich Web UI URL> --immich-key <Joseph's API key> \
     --out-dir hike-izer/summaries/<start-date>_photos
   ```

   This queries each `is_hike`-confirmed session's own time window
   separately and matches Immich assets by timestamp only -- **no GPS
   bounding-box filter.** The hike's time window already comes from the real
   GPS-confirmed session, so any photo Joseph takes inside it was taken
   during the hike by definition; a location filter would only risk dropping
   legitimate photos that lack GPS EXIF (location services off, etc.). It
   writes a `manifest.json` in the output directory listing every matched
   asset alongside the thumbnail and full-resolution files it downloaded.

   **Cross-midnight caveat -- same edge case as this doc's day-scoping rule
   above:** a session can appear to "start" right at a query day's midnight
   boundary (e.g. `00:00:03`) while actually being the tail of a hike that
   started the evening before -- the script can't detect this on its own
   (see `fetch_hike_photos.py`'s docstring). Apply the same judgment already
   used for that day's stats: if adjacent-day context (e.g. a same-trip
   evening hike the day before) shows a manifest entry actually belongs to a
   different day, exclude it from the gallery by hand rather than including
   it uncritically.

   Read `manifest.json`. If it has zero assets (no confirmed hike, no
   Immich matches, or the fetch step failed/Immich was unreachable), **omit
   the Photos section from the HTML entirely** -- same "not available"
   philosophy as the stat row, no empty gallery scaffolding. Otherwise, add
   the Photos section to the HTML per `html-template.html`'s gallery markup
   (one `.photo-item` per manifest entry, `<img>` for `type: IMAGE`, `<video>`
   for `type: VIDEO`, paths relative to the HTML file pointing into the
   sibling `<date>_photos/` directory).

7. **Publish to the M8 (CARD-0088).** Copy the day's HTML file, its
   `.meta.json` sidecar (CARD-0092), and, if present, its sibling
   `<date>_photos/` directory to the M8 so the summary is reachable at a
   real public URL, not just a local file:

   ```
   scp hike-izer/summaries/<start-date>_hike-summary.html hike-izer/summaries/<start-date>_hike-summary.meta.json jct@photo-server.local:~/hike-izer-web-app/srv/
   scp -r hike-izer/summaries/<start-date>_photos jct@photo-server.local:~/hike-izer-web-app/srv/   # only if it exists
   ```

   Then rebuild the calendar home page (CARD-0092) so it picks up the new
   day -- runs inside the `hike-izer-orchestrator` container so the path
   matches what `build_calendar_index.py` expects regardless of whether
   it's triggered this way or by the automatic pipeline:

   ```
   ssh jct@photo-server.local "docker exec hike-izer-orchestrator python3 /app/build_calendar_index.py --srv-dir /srv/hike-izer"
   ```

   Uses the SSH key-based access to the M8 already set up from this
   machine -- no password, no new credentials. Tell Joseph the live URL when done:
   `https://hikes.jctnet.com/<start-date>_hike-summary.html`
   (Cloudflare Tunnel + custom domain, CARD-0094 -- previously Tailscale
   Funnel under CARD-0088). See `components/hike-izer-web/README.md` for
   how this is hosted. The calendar home page itself (CARD-0092) is at
   `https://hikes.jctnet.com/`.

## Explicitly out of scope for v1 (deferred -- see CARD-0073)

- Historical/actual-conditions weather lookup -- separate, still-undecided item
  under CARD-0074. (The forecast-*at-hike-start* piece is now in scope, via
  CARD-0083 -- see step 4 above; don't confuse the two, they're deliberately
  different things.)
- Compass/heading of the *hiker* -- only the sun's compass direction is computed,
  from pure astronomy, not which way the hiker was facing (not tracked by any
  sensor)
- Automatic triggering -- this only runs when asked (CARD-0086)
- Embedded maps/charts and interactivity for the HTML output -- basic
  styling and structured layout (Levels 1-2) are in scope per CARD-0081
  above; the rest is CARD-0082. (Hosting/publishing is now in scope --
  step 8 above, CARD-0088.)

## Notes on the data

- Environmental Data's `lat`/`lon` are often blank even when GPS Track has real
  coordinates for that time window -- a known correlation gap (Node-RED's GPS
  lookup only matches within +/-5 minutes; see `components/hiking-monitor/data-pipeline.md`).
  The fetch script uses GPS Track directly for sun-position calculations, so this
  gap doesn't block sun position -- but it's worth surfacing in the coverage
  section since a high miss rate might indicate a real pipeline issue.
- `rssi_dbm == 0` means the reading was taken while the device had no WiFi (normal
  "field mode" while hiking, not an error).
- `hike_start_forecast` (CARD-0083) is captured server-side by
  `environmental-data.gs` on the first Hiking Observation of each Arizona-local
  day, provider Open-Meteo (no API key needed). It will normally be a 0- or
  1-entry list for a single-day query. `lat`/`lon` on that entry are the actual
  grid point Open-Meteo used (from its response, not the input coordinates) --
  see `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`'s "Hike
  Start Forecast Architecture" section for the full schema/trigger design.
- Full Environmental Data schema (A-Z) and the `action=export` API reference:
  `components/hiking-monitor/data-pipeline.md`.
