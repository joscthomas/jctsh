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
Skill's steps 3/6 do, builds the mechanical HTML output
(`templating.py`, a direct port of `html-template.html`'s field mapping),
makes one Claude API call for just the narrative paragraphs
(`narrative.py`, reading the deployed `SKILL.md` copy at call time so
future edits to the real Skill apply here too), and writes the result
straight into `srv/` — no `scp` step, since the orchestrator and the served
directory are on the same host. Publishes success/failure to
`jctsh/hike-izer/publish/log` (`mqtt_log.py`).

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
scp components/hike-izer-orchestrator/*.py components/hike-izer-orchestrator/Dockerfile components/hike-izer-orchestrator/requirements.txt jct@m8.local:~/hike-izer-web-app/orchestrator/
scp components/hike-izer/fetch_hike_data.py components/hike-izer/fetch_hike_photos.py components/hike-izer/build_hike_map.py components/hike-izer/build_hike_chart.py jct@m8.local:~/hike-izer-web-app/orchestrator/
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
as every other optional section, not a generation failure). The MQTT
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
(parseable via Python's `datetime.fromisoformat`) is what stage 2 will use
to determine "today" for the hike and to render every timestamp in the
output as explicit local time, rather than hardcoding `America/Phoenix` the
way the stationary-sensor pipeline (`environmental-data.gs`) does.

## Building the Tasker profile (Joseph)

Mirrors the existing "Log Observation" task's HTTP POST pattern
(`components/hiking-monitor/hiking-monitor-claude-code-instructions.md`,
Step 24), but as an event-triggered Profile instead of a manually-tapped
Task, since this has to fire itself the instant GPSLogger stops.

**1. Create the Task first** — Tasker → Tasks tab → **+** → name it
`Hike-izer Webhook`:

1. **Action 1 — Date Time Format** (search "Format" or "Date Time" in the
   action picker; the action that formats the current or a given date/time):
   - Input Type: `Now`
   - Output Format Type: `Custom`
   - Custom Format: `yyyy-MM-dd'T'HH:mm:ssZZ`
   - Output Variable: `local_datetime` (no `%` — Tasker adds it)
   - This gets the phone's *current* local date/time with UTC offset — e.g.
     `2026-07-24T14:32:10-07:00` — never a hardcoded timezone.

2. **Action 2 — HTTP Post** (older Tasker versions may only offer "HTTP Post"
   rather than "HTTP Request" — same purpose, but it splits the URL into two
   separate fields instead of one):
   - Method: `POST`
   - Server:Port: `https://hikes.jctnet.com`
   - Path: `/webhook/hike-end?key=G3sOgsf6Ly5N9XwYN2cb1r0qokkHkmug`
     *(`WEBHOOK_SECRET` from `credentials.local.md`. **Both fields matter** —
     a Server:Port-only URL with the path/key crammed in wrong silently fails
     to reach the receiver at all, with no Tasker-visible error; confirmed via
     live `docker logs` debugging 2026-07-28.)*
   - Headers: `Content-Type: application/json`
   - Body:
     ```
     {"gpsloggerevent":"%gpsloggerevent","filename":"%filename","startedtimestamp":"%startedtimestamp","duration":"%duration","distance":"%distance","local_datetime":"%local_datetime"}
     ```
     Tasker's "Intent Received" context (below) exposes each broadcast extra
     as a same-named local variable automatically — `%gpsloggerevent`,
     `%filename`, etc. need no separate assignment.

3. **Action 3 — Flash (optional):**
   - Text: `Hike-izer: publish triggered`

**Test the task manually before wiring the trigger:** tap the play button
next to `Hike-izer Webhook` in the Tasks list. `%gpsloggerevent` etc. will
be unset outside a real broadcast, so the JSON body will have empty
strings for those fields — that's fine for this step, it's only testing
that the HTTP POST itself reaches the receiver. Check
`docker logs hike-izer-orchestrator` on the M8 for a matching log line.

**2. Create the Profile** — Tasker → Profiles tab → **+** → **Event** →
**System** → **Intent Received**:

- Action: `com.mendhak.gpslogger.EVENT`
- Extra: `gpsloggerevent:stopped` — filters so this Profile only fires on
  the stop broadcast, not `started`/`fileuploaded` (the receiver also
  checks this server-side as a backup, but filtering here means Tasker
  never even POSTs for the events we don't care about)
- Assign Task: `Hike-izer Webhook` (created above)

**Real end-to-end test:** start GPSLogger logging, let it run briefly, stop
it. Confirm `docker logs hike-izer-orchestrator` on the M8 shows a real
`stopped` event with real `filename`/`local_datetime` values — not the
empty-field manual test above. This is the one verification step that
can't be done from a desk (CARD-0086's stage 1 verification, step 3).

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

## Staging data for step 2

See `staging.md` for the day-to-day runbook: where the Gaia GPS embed
snippet and BirdNET Live exports go, how to find the right hike's staging
directory, and the SSHFS-Win mount that gets them there from Windows.

## Related

- CARD-0086 (this component's tracking card — full architecture reasoning)
- CARD-0088 (hosting — this component rides its Funnel URL/Caddy/compose project)
- CARD-0007 (Hiking Observations pipeline — the Tasker HTTP-POST pattern this profile copies)
- CARD-0084 (photo integration — `fetch_hike_photos.py`, same behavior reused here)
- CARD-0082 / CARD-0110 / CARD-0134 (Route Map + Elevation & Speed chart — `templating.py` imports `build_hike_map.py`/`build_hike_chart.py` directly, same deployed-copy pattern as `fetch_hike_data.py`; CARD-0134 wired them into this pipeline, replacing the Gaia embed as this pipeline's default map)
- `.claude/skills/hike-izer/SKILL.md` (the narrative-writing rules `narrative.py` calls Claude with, and the mechanical-output rules `templating.py` ports)
- `components/hike-izer/fetch_hike_data.py` / `fetch_hike_photos.py` / `build_hike_map.py` / `build_hike_chart.py` (run as subprocesses or imported directly by `generation.py`/`templating.py`)
- `components/hike-izer/vendor/leaflet/` (deployed once to `~/hike-izer-web-app/srv/vendor/leaflet/` by CARD-0082 — this pipeline's pages reference it by the same relative path, no separate deployment needed here)
- `components/hike-izer/html-template.html` (the styling `templating.py`'s `_HTML_STYLE` constant ports verbatim)
