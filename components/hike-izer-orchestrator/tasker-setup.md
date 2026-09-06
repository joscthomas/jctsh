# Tasker setup — hike-izer-orchestrator

CARD-0241: build procedure, split out of `README.md` (which stays a
scannable reference doc — what this component does, its webhook
contract, how it's deployed) per `JCTsh-Build-Standards.md` §7.1's own
README-vs-procedure-doc convention, already followed by `hiking-monitor`
(`hiking-monitor-claude-code-instructions.md`) but never applied here
until now.

This file covers the one Tasker item that's genuinely specific to this
component: the `Hike-izer Webhook` event Profile, which calls this
component's own `/webhook/hike-end` route (see `README.md`'s Webhook
contract section for the payload shape). `Log Idea` and `JCTsh Menu` also
hit routes hosted in this same container, but for infrastructure
convenience only (a free public HTTPS endpoint) — they're documented at
`tos/tasker-setup.md` and `components/jctsh-menu/README.md` respectively,
where they conceptually belong.

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
**System** → **Intent Received**, name it `Hike-izer Done`:

- Action: `com.mendhak.gpslogger.EVENT`
- Assign Task: `Hike-izer Webhook` (created above)

**Real built behavior, corrected 2026-09-06 from the exported Profile
XML (`tasker/Hike-izer-Done.prf.xml`) — differs from what an earlier
version of this doc claimed.** The Profile carries **no** Extra filter
(`gpsloggerevent:stopped` was never actually set on it) — it fires on
every GPSLogger broadcast (`started`/`stopped`/`fileuploaded` alike), and
the Task's own HTTP Post isn't gated by an `If` either (only the
`%GPS_ACTIVE` reset is). So filtering to `stopped`-only happens **only**
server-side, in `app.py`'s `_handle_hike_end()` (`if event != "stopped":
... ignored`) — that's the sole safety net, not a backup to a
Tasker-side filter. Functionally fine (confirmed working in production),
just worth knowing precisely where the real gate lives if this ever
needs debugging or an Extra filter gets added for real.

`tasker/Hike-izer-Done.prf.xml` (this directory) is the real exported
Profile + Task together — the authoritative source for the correction
above; `tasker/Hike-izer-Webhook.tsk.xml` (Task-only, exported earlier)
is kept alongside it as the pre-existing artifact, not removed.

**Real end-to-end test:** start GPSLogger logging, let it run briefly, stop
it. Confirm `docker logs hike-izer-orchestrator` on the M8 shows a real
`stopped` event with real `filename`/`local_datetime` values — not the
empty-field manual test above. This is the one verification step that
can't be done from a desk (CARD-0086's stage 1 verification, step 3).

**`tasker/Hike-izer-Webhook.tsk.xml`** (this directory) is the real
exported Task, per CARD-0231. Diffing it against the walkthrough above
found the on-device Task carries two more actions past the optional
Flash, undocumented here until now (CARD-0208 territory, not this
component's own concern — noted for completeness, not duplicated as a
build step):
- Unconditionally resets `%LAST_ANNOUNCED_MILE` to `0` on every run —
  confirms CARD-0208's own open question (whether this reset is tied to
  the `stopped` broadcast) as **yes**, found by reading the exported XML
  directly rather than needing another live hike test for that specific
  point.
- Inside an `If %gpsloggerevent Eq stopped` block, also resets
  `%GPS_ACTIVE` to `0` — a variable not referenced in any doc in this
  repo before this export. Its counterpart, the `GPS Active` Profile +
  `GPS Active Flag` task (`components/hiking-monitor/tasker/GPS-Active.prf.xml`),
  sets it back to `1` on GPSLogger's `started` event — confirmed tracking
  "GPSLogger running" correctly end to end. `CARD-0208`'s "Mile
  Announcer" was confirmed reading it via a `State: %GPS_ACTIVE Eq 1`
  context on its own `Mile Announcement` Profile — see that card.

## Other exported Tasker items for this component

- **`Share BirdNET`** (`tasker/Share-BirdNET.prf.xml`) — the AutoShare → Tasker → `/webhook/stage-file?kind=birdnet` path (`birdnet-pipeline.md`), previously undocumented by exact task name until this export. Saves the shared file, formats `local_datetime` the same way `Hike-izer Webhook` does, then an `HTTP Request` (guarded by an `If %asfile(1) Exists`) uploads it as a file attachment to the webhook, followed by a confirmation Flash.

## Related

- `README.md` (this component's reference doc — webhook contract, deploy steps)
- `birdnet-pipeline.md` (the pipeline `Share BirdNET` feeds into)
- CARD-0086 (this component's tracking card)
- CARD-0231 (Tasker export/import research)
- CARD-0241 (the doc split this file is a result of)
