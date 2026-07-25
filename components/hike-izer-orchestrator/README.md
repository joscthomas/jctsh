# hike-izer-orchestrator

Webhook receiver (and, eventually, generator) for automatic Hike-izer
triggering. Tracking card: **CARD-0086** on `kanban-board.md`. Companion to
CARD-0081 (HTML rendering) and CARD-0088 (hosting) — this is what makes
Hike-izer run without Joseph asking for it.

---

## Status: Stage 1 (trigger + connectivity) only

`app.py` currently just validates the shared secret and logs what it
received — no generation yet. Stage 2 (Python templating for the mechanical
output + one Claude API call for narrative prose) is a follow-up build once
stage 1 is proven with a real phone-triggered event, not a synthetic curl
test.

## How it's deployed

Not its own Docker Compose project. `app.py` runs as a second service
(`orchestrator`) inside `components/hike-izer-web/docker-compose.yml`, so it
shares that project's default Docker network and is reachable from Caddy by
service name (`orchestrator:8080`) — no second Tailscale Funnel port. See
`components/hike-izer-web/Caddyfile`'s `/webhook/*` route.

On the M8, the deployed source lives at
`~/hike-izer-web-app/orchestrator/app.py` (same project directory as the
`web` service's `srv/`/`Caddyfile`). To update:

```
scp components/hike-izer-orchestrator/app.py jct@photo-server.local:~/hike-izer-web-app/orchestrator/app.py
ssh jct@photo-server.local "cd ~/hike-izer-web-app && docker compose up -d orchestrator"
```

## Webhook contract

`POST https://photo-server.tailfe828a.ts.net/webhook/hike-end?key=<WEBHOOK_SECRET>`

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

2. **Action 2 — HTTP Request:**
   - Method: `POST`
   - URL: `https://photo-server.tailfe828a.ts.net/webhook/hike-end?key=G3sOgsf6Ly5N9XwYN2cb1r0qokkHkmug`
     *(from `credentials.local.md` — `WEBHOOK_SECRET`)*
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
curl -s -X POST "https://photo-server.tailfe828a.ts.net/webhook/hike-end?key=<WEBHOOK_SECRET>" \
    -H "Content-Type: application/json" \
    -d '{"gpsloggerevent":"stopped","local_datetime":"2026-07-24T14:32:10-07:00"}'
docker logs hike-izer-orchestrator --tail 20                          # confirm it logged the event
```

## Related

- CARD-0086 (this component's tracking card — full architecture reasoning)
- CARD-0088 (hosting — this component rides its Funnel URL/Caddy/compose project)
- CARD-0007 (Hiking Observations pipeline — the Tasker HTTP-POST pattern this profile copies)
- `.claude/skills/hike-izer/SKILL.md` (the narrative-writing rules stage 2 will call Claude with)
- `components/hike-izer/fetch_hike_data.py` / `fetch_hike_photos.py` (stage 2 will run these as subprocesses)
