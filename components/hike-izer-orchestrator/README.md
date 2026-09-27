# hike-izer-orchestrator

Webhook receiver and generator for automatic Hike-izer triggering. Tracking
card: **CARD-0086** on `kanban-board.md`. Companion to
CARD-0081 (HTML rendering) and CARD-0088 (hosting) — this is what makes
Hike-izer run without Joseph asking for it.

---

## Status: Stage 1 verified, stage 2 built 2026-07-24

Stage 1 (trigger + connectivity) was proven end-to-end with a real
GPSLogger stop event before stage 2 was built. Stage 2 adds the actual
generation pipeline (`generation.py`): on a real `stopped` event, it runs
`fetch_hike_data.py`/`fetch_hike_photos.py` exactly as the interactive
Skill's steps 3/6 do, builds the mechanical HTML output (`templating.py`,
a direct port of `html-template.html`'s field mapping), and writes the
result straight into `srv/` — no `scp` step, since the orchestrator and the
served directory are on the same host. Publishes success/failure to
`jctsh/hike-izer/publish/log` (`mqtt_log.py`).

## One process, not two (CARD-0348, 2026-09-27)

Originally split into a fast "step 1" (mechanical, webhook-triggered) and a
richer "step 2" (photos/place-naming/narrative, asked for or run nightly) —
retired in favor of one process, `generation.generate(file_stem)`, called
identically every time:

- **`_bootstrap_from_webhook()`** — the one genuinely first-time-only piece.
  Parses the webhook payload, detects the session window, allocates the
  hike's file stem, decides whether a real hike was even confirmed, and
  writes its first `meta.json`. Then calls `generate()`.
- **`generate(file_stem)`** — always re-fetches Environmental Data/GPS/
  Hiking Observations fresh (late-arriving Sheet data is exactly what a
  later pass exists to catch) and re-checks Immich for photos (captioning
  only genuinely new ones). It skips only the CARD-0311 place-naming
  Overpass lookup once a prior pass already got a real answer — tracked
  in a small `<file_stem>_places_state.json` sidecar in `PRIVATE_DIR`
  (`{"ok": bool, "places": {...}}`). CARD-0348, same day: the separate
  Nearby Named Features Overpass lookup this used to run alongside was
  retired outright (see "Location naming" below) — one lookup now, so
  there's no second flag to keep in sync.

`generate()` is called by the webhook's own first pass (via bootstrap), by
the daily systemd-timer catch-up (`run_daily_refresh_and_log`, CARD-0214,
unchanged trigger), and on demand (`run_step2_and_log`/`--step2`/
`/webhook/step2` — kept under that name for the Tasker task and Joseph's
own muscle memory, even though it now runs the identical process as every
other call, not a separate "step 2"). Narrative generation (`narrative.py`,
place_context.py's Claude+web_search research layers, `--narrative`) was
retired in the same change — opt-in-only from the start (CARD-0123), and
Joseph won't use it again. Every published page is now the page that used
to require asking for "the rich version."

## How it's deployed

Not its own Docker Compose project. This runs as a second service
(`orchestrator`) inside `components/hike-izer-web/docker-compose.yml`, so it
shares that project's default Docker network and is reachable from Caddy by
service name (`orchestrator:8080`) — no second Tailscale Funnel port. See
`components/hike-izer-web/Caddyfile`'s `/webhook/*` route.

Unlike stage 1 (a single bind-mounted `app.py` against the stock
`python:3.12-alpine` image), stage 2 needs pip packages (`anthropic`,
`paho-mqtt`) that image doesn't have, so this is now a real Docker build
(`Dockerfile`) rather than a bind mount. The build context also needs two
files this component doesn't own — `fetch_hike_data.py`/`fetch_hike_photos.py`
(canonical source: `components/hike-izer/`) and `SKILL.md` (canonical
source: `.claude/skills/hike-izer/SKILL.md`) — deployed as copies, same
"no git checkout on the M8" pattern used everywhere else in this repo.

On the M8, the deploy directory is `~/hike-izer-web-app/orchestrator/`
(same project directory as the `web` service's `srv/`/`Caddyfile`). To
update:

```
scp components/hike-izer-orchestrator/*.py components/hike-izer-orchestrator/Dockerfile components/hike-izer-orchestrator/requirements.txt components/hike-izer-orchestrator/known-places.json jct@m8.local:~/hike-izer-web-app/orchestrator/
scp components/hike-izer/fetch_hike_data.py components/hike-izer/fetch_hike_photos.py components/hike-izer/build_hike_map.py components/hike-izer/build_hike_chart.py components/hike-izer/build_calendar_index.py components/hike-izer/build_wildlife_index.py components/hike-izer/build_battery_trend_index.py components/hike-izer/xeno_canto.py jct@m8.local:~/hike-izer-web-app/orchestrator/
scp tos/open_kanban_pr.py jct@m8.local:~/hike-izer-web-app/orchestrator/
scp .claude/skills/hike-izer/SKILL.md jct@m8.local:~/hike-izer-web-app/orchestrator/
ssh jct@m8.local "cd ~/hike-izer-web-app && docker compose up -d --build orchestrator"
```

**Required `.env` keys** (`~/hike-izer-web-app/.env`, shared with `web`) —
see `components/hike-izer-web/.env.example` for the full list and
`credentials.local.md` for real values: `WEBHOOK_SECRET`,
`ANTHROPIC_API_KEY`, `APPS_SCRIPT_URL`, `APPS_SCRIPT_KEY`, `IMMICH_URL`,
`IMMICH_KEY`, `MQTT_USERNAME`, `MQTT_PASSWORD`, `THUNDERFOREST_API_KEY`
(CARD-0134 — the Route Map's basemap tiles; a missing/empty value just
means `render_html()` omits the map section, same "not available" pattern
as every other optional section, not a generation failure), `XENO_CANTO_API_KEY`
(CARD-0174 — the Wildlife Heard/Life List speaker icon's reference-call
audio, from `xeno_canto.org`'s Account Page; same optional/graceful-omission
pattern as `THUNDERFOREST_API_KEY` — a missing value just means no speaker
icons, not a generation failure), `GITHUB_PAT` (CARD-0173 — `/webhook/idea`'s
own direct-to-kanban-PR path; same GitHub PAT this M8's own host-level
`maintenance-check.py` already has at `/etc/jctsh/github.env`, reused here
as an env var since this container is a separate process and needs its own
copy — not required for anything else this component does, so a missing
value only breaks that one endpoint, same graceful-degradation convention).
The MQTT
account needs to be created on the Pi once (`sudo mosquitto_passwd ...` —
see `credentials.local.md`) before publish-visibility logging works;
everything else works without it (a missing MQTT account just means
`mqtt_log.py` prints a warning and skips the publish, not a generation
failure).

## Webhook contract

`POST https://hikes.jctnet.com/webhook/hike-end?key=<WEBHOOK_SECRET>`

JSON body, built by the Tasker profile from GPSLogger's own broadcast
extras (`com.mendhak.gpslogger.EVENT`) plus the phone's local date/time as
a single ISO 8601 string with UTC offset — **never assume Arizona**, since
a hike can happen anywhere Joseph is carrying his phone. Tasker builds this
field with its "Parse/Format Date and Time" action (input "Now", custom
output format `yyyy-MM-dd'T'HH:mm:ssZZ`) rather than concatenating separate
date/time/offset variables — one unambiguous field:

```json
{
    "gpsloggerevent": "stopped",
    "filename": "...",
    "startedtimestamp": "...",
    "duration": "...",
    "distance": "...",
    "local_datetime": "2026-07-24T14:32:10-07:00"
}
```

Only `gpsloggerevent=stopped` triggers anything; `started`/`fileuploaded`
are logged and ignored. Wrong/missing `key` gets a 401. `local_datetime`
(parseable via Python's `datetime.fromisoformat`) is what `generate()` uses
to determine "today" for the hike and to render every timestamp in the
output as explicit local time, rather than hardcoding `America/Phoenix` the
way the stationary-sensor pipeline (`environmental-data.gs`) does.

`POST https://hikes.jctnet.com/webhook/idea?key=<WEBHOOK_SECRET>`

CARD-0173: Tasker voice capture straight to a placeholder kanban PR, no
email in between (skips the `email-idea-check.py`/CARD-0151 path
entirely — same underlying `open_finding_pr()`, called directly).

```json
{"text": "the spoken idea, verbatim"}
```

Runs synchronously (unlike `hike-end`) — opening a PR is a handful of fast
GitHub API calls, so the response itself tells Tasker whether it actually
worked. Wrong/missing `key` gets a 401; missing/empty `text` gets a 400;
a GitHub API failure gets a 502 — all three are real, Tasker-visible
failures, not a silent drop. On success: `{"status": "ok", "pr_url":
"..."}`.

`POST https://hikes.jctnet.com/webhook/step2?key=<WEBHOOK_SECRET>`

CARD-0239: a phone-only, no-SSH way to force an immediate regeneration of
the current hike (CARD-0348: the same `generate()` every other trigger
calls) instead of waiting for the daily catch-up pass. No request body.
Resolves the target hike via `generation.current_or_latest_file_stem()`
(same helper `stage-file` uses) and runs `run_step2_and_log(file_stem)` in
a background thread — same reasoning as `hike-end`, the Sheet/Nominatim/
Overpass/Immich calls inside `generate()` aren't fast enough to hold the
HTTP response open. Wrong/missing `key` gets a 401; no published hike yet gets
a 409; a real request gets an immediate `{"status": "ok", "file_stem":
"...", "message": "step2 started"}` — the actual gap-fill result (success
or failure) shows up afterward via `run_step2_and_log`'s own MQTT
System/Alert line and HA push, not in this response.

## Building the Tasker tasks/profiles (Joseph)

CARD-0241: full step-by-step build guides moved out of this reference
doc into dedicated procedure docs, organized by which feature each one
conceptually belongs to rather than by which container happens to host
its webhook:

| Tasker item | Calls | Build guide |
|---|---|---|
| `Hike-izer Webhook` (event Profile) | `/webhook/hike-end` | `tasker-setup.md` (this component — genuinely hike-izer-specific) |
| `Log Idea` (manual task) | `/webhook/idea` | `tos/tasker-setup.md` (a TOS feature hosted here for the free endpoint) |
| `JCTsh Menu` → `Run Step 2` (manual task) | `/webhook/step2` | `components/jctsh-menu/README.md` (a cross-cutting, growable menu, not owned by this component) |

## Checking it's up

```
docker ps                                                              # orchestrator should show Up (healthy)
curl -s -X POST "https://hikes.jctnet.com/webhook/hike-end?key=<WEBHOOK_SECRET>" \
    -H "Content-Type: application/json" \
    -d '{"gpsloggerevent":"stopped","local_datetime":"2026-07-24T14:32:10-07:00"}'
docker logs hike-izer-orchestrator --tail 20                          # confirm it logged the event
```

## Checking generation worked

```
docker logs hike-izer-orchestrator --tail 30                          # look for "Published hike summary for <date>"
curl -s https://hikes.jctnet.com/<date>_hike-summary.html | head -5
```

A generation failure logs the exception to stdout (`docker logs`) and
publishes an `Alert`-category message to `jctsh/hike-izer/publish/log`
rather than crashing the webhook handler — the HTTP response to Tasker
already went out before generation started (see `app.py`'s background
thread), so a failure here is only visible via logs/MQTT, not an HTTP
error.

## Location naming (CARD-0311/CARD-0348)

The hike-intro block at the top of every page (CARD-0348, 2026-09-27 -- moved here from a
separate `Location` section further down, per Joseph's own redesign request) names, for the
hike, the **town/county/state**, the **area** (park/preserve), the **trailhead**, and the
**trails in the order hiked** (arrows between them, no distances), read top to bottom as
Time -> Location -> Distance -> Elevation Gain. `hike_places.py` does it with **one Overpass call** for the hike's
bounding box: `is_in()` at 10 points along the track picks the area (the named park polygon
containing the most of them) and the town/county/state; every path-type way in the box is
matched against the GPS track (25 m) to get the trails; the trailhead is a named
`highway=trailhead`, then a named parking lot or guidepost, within 150 m of where the track
**enters** the area (or of the first GPS point), else the nearest named street, shown as
"near X (street)". Streets are never trails. **A hike in a town or city** (no named park/preserve contains it) is named
differently: the Area is the neighborhood (an OSM neighborhood/suburb/quarter or named residential
polygon, else Nominatim's suburb/neighbourhood) and the segments are the named streets and paths
walked, in order, labeled "Streets"; no trailhead is claimed unless OSM tags a real
`highway=trailhead`. Known OSM typos (`Tral`) are corrected by a
token map at the top of `hike_places.py`. Any failure just omits the lines.

**Nearby Named Features (place_context.py's own separate Overpass lookup) retired
2026-09-27, CARD-0348.** It queried named parks/schools/hiking-routes near a few sampled
points and rendered as its own table below the Location block. Across all 10 real hikes
published before this change it returned a result exactly once, and that one result only
duplicated the hike's own trail -- already named better by the lookup above (Joseph: "the
value of nearby features seems dubious... a nearby feature that describes the same thing is
not desireable"). `place_context.py` now holds only the shared Nominatim/Overpass-retry
helpers `hike_places.py` itself depends on.

`known-places.json` (deployed with the `.py` files) holds Joseph's own names for spots he
hikes: a trailhead coordinate + radius (default 150 m) and any of `trailhead`, `area`, `trail`
(with `osm_trail` naming the OSM trail it renames). An entry applies when the track passes within
its radius, and overrides OSM's names for the fields it defines. Add a spot by adding an entry.

## Staging data for the generation pass

See `staging.md` for the day-to-day runbook: where the Gaia GPS embed
snippet and BirdNET Live exports go, how to find the right hike's staging
directory, and the SSHFS-Win mount that gets them there from Windows.

## Related

- CARD-0086 (this component's tracking card — full architecture reasoning)
- CARD-0088 (hosting — this component rides its Funnel URL/Caddy/compose project)
- CARD-0007 (Hiking Observations pipeline — the Tasker HTTP-POST pattern this profile copies)
- CARD-0084 (photo integration — `fetch_hike_photos.py`, same behavior reused here)
- CARD-0082 / CARD-0110 / CARD-0134 (Route Map + Elevation & Speed chart — `templating.py` imports `build_hike_map.py`/`build_hike_chart.py` directly, same deployed-copy pattern as `fetch_hike_data.py`; CARD-0134 wired them into this pipeline, replacing the Gaia embed as this pipeline's default map)
- `.claude/skills/hike-izer/SKILL.md` (the mechanical-output rules `templating.py` ports)
- CARD-0348 (retired narrative generation; unified step 1/step 2 into one idempotent `generate()`)
- `components/hike-izer/fetch_hike_data.py` / `fetch_hike_photos.py` / `build_hike_map.py` / `build_hike_chart.py` (run as subprocesses or imported directly by `generation.py`/`templating.py`)
- `components/hike-izer/vendor/leaflet/` (deployed once to `~/hike-izer-web-app/srv/vendor/leaflet/` by CARD-0082 — this pipeline's pages reference it by the same relative path, no separate deployment needed here)
- `components/hike-izer/html-template.html` (the styling `templating.py`'s `_HTML_STYLE` constant ports verbatim)
