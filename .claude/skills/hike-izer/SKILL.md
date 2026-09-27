---
name: hike-izer
description: Generate an HTML summary of a JCTsh hiking trip from sensor, GPS, and observation data (Google Sheets). Use when Joseph asks to summarize, narrate, recap, or review a specific hike or hiking trip by date -- e.g. "summarize the June 15 hike", "write up last week's trip", "how did the hiking monitor do on the camping trip".
---

# Hike-izer

Generates an HTML summary of a hiking trip using JCTsh's hiking-monitor
data pipeline (Environmental Data, Hiking Observations, GPS Track, Hike Start
Forecast -- all in the "JCTsh Environmental Data" Google Sheets workbook).
CARD-0073 on `kanban-board.md` is this skill's tracking card; its v1 scope note
there is the source of truth for what's in/out of scope if this doc and the
card ever disagree. CARD-0083 tracks the weather-forecast-at-hike-start feature
specifically (step 4 below). **HTML is the sole output format** (CARD-0091,
2026-07-28) -- v1 (CARD-0073) originally also produced a `.md` file, dropped
once CARD-0088 gave the HTML output a real public URL and made it unambiguously
the deliverable Joseph actually reads/shares.

## Most hikes: check the published page first, don't re-run the manual flow below

**CARD-0086/CARD-0348 already automate all of this.** For any hike where
GPSLogger's `stopped` webhook fired (the normal case whenever the hiking-monitor
phone workflow was used), a full page -- photos, place naming, Nearby Named
Features -- has already been published automatically at
`https://hikes.jctnet.com/<date>_hike-summary.html` (`<date>-2`, `-3`, ... for
additional same-day sessions, CARD-0113's naming), and a daily catch-up pass
at 17:00 automatically re-checks it for anything that synced late (new
photos, late sensor readings). Check there first before falling back to this
skill's own manual `fetch_hike_data.py` flow below, which duplicates work
already done and risks producing a second, inconsistent copy.

**"Regenerate the hike page now" / "force it to re-check" for an
already-published hike, instead of waiting for the 17:00 pass, means, on the M8:**

```
ssh jct@100.111.16.14 "docker exec hike-izer-orchestrator python3 generation.py --step2 <date-stem>"
```

(Kept under the `--step2` name for compatibility with the JCTsh Menu's own
"Run Step 2" Tasker entry -- CARD-0348 unified what used to be two separate
processing paths into one, so this now runs the identical, complete
generation pass every other trigger runs, not a distinct "step 2.")

The fully manual flow below (steps 1-7, calling `fetch_hike_data.py` directly)
is for hikes with **no automatic trigger at all** -- historical/backfill hikes,
or ones where the webhook didn't fire -- not the normal path for a recent,
already-triggered hike. Narrative generation (a Claude-written prose story)
was retired CARD-0348, 2026-09-27 -- opt-in-only from the start (CARD-0123)
and Joseph won't use it again; this skill (manual or automatic) no longer
produces one.

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
  normal single-day event -- `coverage.window_truncated_to_now` will be `true`
  in the fetched JSON, which just means the coverage numbers were computed
  through the current time rather than the full calendar day. Expected on
  essentially every same-day-generated page; CARD-0176 dropped the prose
  caveat that used to call this out explicitly (Joseph's call, cluttered the
  page without being genuinely informative) -- no special
  treatment needed, just don't be surprised by a lower-than-usual expected
  count on a same-day page.

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

4. **Render the page sections.** First check `coverage.gps_track.hike_confirmed` --
   if `false`, follow "What counts as a hike" above instead of the normal
   structure below. Otherwise, produce the HTML output with the following
   parts, in this order.

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

   **Environmental Data Tracking (CARD-0176, renamed from "Data
   Summary")** -- the actual sensor numbers: temperature range, humidity
   range, pressure range (`stats.pressure_hpa`, in hPa -- found missing from
   this table entirely, CARD-0204, 2026-08-24), UV index range, battery
   voltage range, and **Battery Discharge Rate** (`stats.battery_window_crossing_min`,
   CARD-0207, 2026-08-24) -- render as `"{X:.1f} min per 0.30V (4.00V→3.70V)"`
   when not `None`, else `"not available"` (same convention as every other
   row here). This row's *label* (not the value) is a hyperlink to
   `battery-trend.html` (the cross-hike trend page, same served directory)
   -- the one label in this table that isn't plain text. A rough field
   indicator, not a precision measurement -- it's
   the time this specific hike's own field-mode battery readings took to
   cross a *fixed* reference voltage window, comparable across hikes because
   the window itself never changes (see `fetch_hike_data.py`'s own comment
   on `BATTERY_TREND_WINDOW_HIGH_V`/`_LOW_V` for why a fixed window matters
   here, not each hike's own start/end range). `None` means this hike's data
   didn't fully bracket both reference points (too short, or started already
   below 4.00V) -- report "not available", don't estimate from a partial
   window. Elevation range/gain **in feet** (`stats.altitude_ft`) and
   duration belong in the hero stat row (step 5), not repeated here.
   Observation count by category no longer belongs in this table -- see the
   Full observations table below. Append one more row at the end of this
   same table: Environmental Data readings recorded vs. expected (and
   coverage %), from `coverage.environmental_data` -- this is the old
   "Expected vs. actual data coverage" section's Environmental Data half,
   now folded into this table instead of living in its own separate section.
   If `coverage.environmental_data.gaps_over_6min` is non-empty, report
   those gaps (with timestamps) directly under this table too. **Omit this
   whole section when there's no environmental sensor data at all for the
   day** (temperature/humidity/pressure/UV/battery all null) -- same "no
   empty scaffolding" convention Photos follows, checked against the
   underlying stats, not against a formatted "not available" string. This is
   where precise figures belong, not restated anywhere else on the page.

   **Environmental Data (CARD-0204, renamed from "Environmental Data
   Chart" and moved into `.hike-visuals-col`, stacked with Elevation &
   Speed in the same grid column rather than after the Environmental Data
   Tracking table, CARD-0207 -- Joseph's call, so a data point's location
   is easy to cross-reference against the adjacent Route Map, and so both
   charts render at matching size since they share the same column
   width):** fill the `{{ENVIRONMENTAL_DATA_CHART}}` placeholder by calling
   `build_hike_chart.build_env_chart_html(hike_data['chart_series'])` --
   temp/humidity/pressure/UV plotted against the same distance axis as the
   Elevation & Speed chart above, reusing `chart_series`' own per-point
   `temp_f`/`humidity_pct`/`pressure_hpa`/`uv_index` fields (already
   correlated onto the GPS-derived points by `fetch_hike_data.py`, no
   separate step needed here). Returns complete, ready-to-embed markup
   (legend-toggle between two preset pairings, SVG with baked-in geometry
   for both, hover `<script>`) -- splice it in verbatim, don't hand-author
   or edit it per hike, same convention as `{{ROUTE_MAP}}`/
   `{{ELEVATION_SPEED_CHART}}` above. Returns `''` when the hike had no
   environmental sensor data at all (device not carried that day) -- omit
   the whole `<section>` in that case, same "no empty scaffolding"
   convention as everything else here. This section's presence is
   independent of the Environmental Data Tracking table further down the
   page (both are omitted on their own actual content, not on each
   other's), though in practice they'll almost always agree since both
   come from the same `env_rows`.

   **Full observations table (added 2026-07-23):** the complete list of that
   day's Hiking Observations as its own table -- columns Time (local, MST,
   not the sheet's raw UTC), Observation (the raw text as logged, don't
   paraphrase or clean it up), and Categories (comma-joined, or an em dash if
   the categories array is empty). One row per observation, in chronological
   order. This is the complete, unabridged list of that day's observations. Include this table whenever `hiking_observations` is
   non-empty, including on the `hike_confirmed: false` path -- it's exactly
   the kind of "other data that does exist" that path already calls for
   reporting. **Observation count by category (CARD-0176, moved here from
   part b above)** goes directly beneath this table, as its own line, not a
   second table -- it's a breakdown of the table immediately above it, not an
   environmental sensor reading. Always present whenever this section is
   (every observation without categories buckets into "uncategorized"), so no
   "not available" fallback is needed.

   **Voice-to-text place-name correction (CARD-0194, added 2026-08-24).**
   Tasker's voice transcription occasionally mishears a place name (e.g.
   "The tortellito Preserve" for "Tortolita Preserve") -- when writing this
   table, cross-check any place/feature name in an observation against
   `place_context`'s already-researched real nearby named features (CARD-0108,
   fetched the same generation pass). If a name doesn't match anything in
   `place_context` but is clearly a phonetic near-miss of something that
   does, **substitute the corrected word in place, wrapped in `<em>` (italics)
   to mark it as an edited word** -- e.g. `hiking The <em>Tortolita</em>
   Preserve this morning with David`. Don't add a bracketed explanation
   or footnote; the italics alone are the signal that a word was corrected.
   This is a judgment call made fresh each generation, not a fuzzy-match
   algorithm -- only correct a genuine, confident near-miss against real
   `place_context` data, never guess at a name with no supporting evidence.
   Leave everything else in the observation exactly as transcribed --
   this only ever touches the specific mis-transcribed word(s), never
   reworded or cleaned-up surrounding text (same "raw text as logged"
   principle the rest of this table follows).

   **GPS Trackpoints, placed near the Route Map, not here (CARD-0176) --
   see step 5 below.** The old combined "Expected vs. actual data coverage"
   section is gone; its Environmental Data half moved into part b above, its
   GPS Trackpoints half moved next to the Route Map instead (a bare table row
   there had no room to explain what "expected" was even counting, which was
   the actual complaint -- now spelled out in prose: one GPS point roughly
   every 30 seconds, GPSLogger's configured interval, across that day's
   tracked GPS session(s)). Two of the old section's note lines were dropped
   outright, not relocated, per Joseph's explicit call: the generation-cutoff
   caveat (obvious/expected on every same-day-generated page, not worth
   stating) and the GPS-correlation line (how many Environmental Data
   readings had GPS coordinates successfully correlated vs. not -- rarely
   informative, cluttered the page).

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
   empty. Event markers on the Route Map (photos, observations, bird
   sightings) are the one piece still **out of scope here** -- tracked
   separately on `kanban-board.md` as CARD-0082's deferred Level 3.

   **Route Map (CARD-0082) + Elevation & Speed chart (CARD-0110), shown
   side-by-side:** the template wraps both in `<div class="hike-visuals">`
   so they render together (side-by-side at wide viewports, stacked on
   narrow ones) -- added 2026-08-01 after testing the two sections stacked
   and finding the hover-sync between them, while working correctly, wasn't
   visible without scrolling back and forth to see both halves. Fill the
   `{{ROUTE_MAP}}` placeholder by calling
   `build_hike_map.build_map_html(hike_data['chart_series'], thunderforest_api_key)`
   -- `thunderforest_api_key` comes from `credentials.local.md`'s
   "Thunderforest" entry, read the same way every other component reads its
   own credential. Fill `{{ELEVATION_SPEED_CHART}}` by calling
   `build_hike_chart.build_chart_html(hike_data['chart_series'])`. Both
   return complete, ready-to-embed markup (map: tooltip slot, Leaflet
   container, Leaflet init + hover-sync `<script>`; chart: legend, tooltip
   slot, SVG with baked-in geometry, hover `<script>`) -- splice both in
   verbatim, don't hand-author or edit either per hike. If `chart_series` is
   empty (`hike_confirmed` is `false`), both functions return `''` -- omit
   the **whole `<div class="hike-visuals">` wrapper**, both sections inside
   it together, same "no empty scaffolding" convention as Photos (they
   share the same empty condition, so there's never a case with one present
   and not the other). Also omit the template's `<link>`/`<script>` tags for
   vendored Leaflet in `<head>` when there's no map to show.

   **GPS Trackpoints note (CARD-0176), right after this `.hike-visuals`
   wrapper:** fill the template's `{{GPS_TRACKPOINTS_ACTUAL}}`/
   `{{GPS_TRACKPOINTS_EXPECTED}}`/`{{GPS_TRACKPOINTS_COVERAGE_PCT}}` from
   `coverage.gps_track` -- expected is the sum of `expected_points` across
   every session that day (`coverage.gps_track.sessions`, hike and rejected
   alike, one point roughly every 30 seconds), actual is
   `coverage.gps_track.total_trackpoints`. Omit this `<p>` entirely when
   `coverage.gps_track.sessions` is empty (no GPS session detected that day
   at all) -- same omit-when-empty convention as everything else here.

   **Richer pace stats (CARD-0110):**
   - Fill the `.stat-row--rich` "Pace & Elevation Detail" section from
     `stats`: **Moving Time** (`stats.moving_time_min`, format `Xm Ys`),
     **Stopped Time** (`stats.stopped_time_min`, same format), **Total
     Time** (same source as the hero row's Duration), **Pace**
     (`stats.pace_min_per_mi`, format `MM:SS /mi`), **Moving Speed**
     (`stats.moving_speed_mph`), **Avg Speed** (`stats.avg_speed_mph`),
     **Ascent** (`stats.ascent_ft`), **Descent** (`stats.descent_ft`). All
     `None` (show "not available") when `hike_confirmed` is `false`, same
     convention as every other stat on the page.

   Hosting/publishing is step 7 below (CARD-0088). Tell Joseph the
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
     --out-dir hike-izer/summaries/<start-date>_photos \
     --album-name "Hike <start-date>"
   ```

   CARD-0286: `--album-name` also adds every matched asset to an Immich album
   named `Hike <start-date>` (created if it doesn't exist yet), same
   convention `generation.py`'s automated pipeline uses -- so a manually-run
   hike ends up with the same per-hike Immich grouping as an automated one.

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
   scp hike-izer/summaries/<start-date>_hike-summary.html hike-izer/summaries/<start-date>_hike-summary.meta.json jct@m8.local:~/hike-izer-web-app/srv/
   scp -r hike-izer/summaries/<start-date>_photos jct@m8.local:~/hike-izer-web-app/srv/   # only if it exists
   ```

   Then rebuild the calendar home page (CARD-0092) so it picks up the new
   day -- runs inside the `hike-izer-orchestrator` container so the path
   matches what `build_calendar_index.py` expects regardless of whether
   it's triggered this way or by the automatic pipeline:

   ```
   ssh jct@m8.local "docker exec hike-izer-orchestrator python3 /app/build_calendar_index.py --srv-dir /srv/hike-izer"
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
- Event markers on the Route Map (photos, hike observations, bird
  sightings) -- CARD-0082's deferred Level 3, not yet built. The map itself
  (basemap + route line, hover-synced with the Elevation & Speed chart) and
  the chart itself are both now in scope and built (CARD-0082 and CARD-0110,
  steps 5-6 above). Basic styling and structured layout (Levels 1-2) are in
  scope per CARD-0081 above. (Hosting/publishing is now in scope -- step 8
  above, CARD-0088.)

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
