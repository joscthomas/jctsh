---
name: hike-checkout
description: Read-only health check of a hike across the whole data/publishing stack (GPS Track, hiking-monitor, air-quality-monitor, observations, wildlife/BirdNET, hike-end trigger, generation, infrastructure) -- diagnoses what happened and produces a summary, never fixes anything itself. Use when Joseph asks to check, inspect, verify, or "what happened with" a specific hike, or asks why a hike's data/page/upload looks wrong or missing.
---

# Hike Checkout

A diagnostic pass over one hike, built 2026-10-03 after a real credential
rotation silently broke AQM's uploads for ~27 hours and a missing GPSLogger
`stopped` broadcast meant that same hike's page never generated -- both real,
both found by hand, neither caught by anything until asked to look. This
skill exists so that "inspect the data and determine what happened" is a
repeatable procedure, not a fresh investigation every time.

**Read-only by design.** This skill inspects and reports. It never writes to
a database, never reflashes a device, never fires a webhook, never edits the
registry -- it only runs read queries and greps logs. If a check finds a
problem with a known, safe recovery action (the `/webhook/hike-end` retrigger
is the one documented case so far), **name the action and ask before running
it, every time** -- never run it as part of "finish the checkout."

Credential-handling note: this skill reads logs and queries data, never a
secret value. Where a check needs an authenticated call (the manual
`hike-end` retrigger, if Joseph approves it), source the relevant `.env`
remotely and never let the value cross back into this session's own output
-- same standing rule `rotate-credentials` follows.

## 0. Determine the hike

If Joseph names a date, use it. If he says "today" or doesn't specify,
default to today. Either way, **confirm the actual hike window from data,
don't assume it** -- query GPS Track for that calendar day first (`SELECT
min(ts), max(ts), count(*) FROM gps_track WHERE ts > '<date>' AND ts <
'<date+1>'`) and use its time range as the hike window for every check
below. If GPS Track has zero rows for the day, say so plainly up front --
most of the checks below will have nothing to check, and that's itself the
finding, not a reason to silently stop.

Reuse `fetch_hike_data.py`'s own day-vs-session distinction
(`components/hike-izer/SKILL.md`'s "Core model" section) if the day turns
out to have more than one real session, or a session crossing midnight --
don't re-derive that logic here, just be aware of it so a multi-session day
doesn't get misread as "missing data" when it's actually two hikes.

## 1. Raw data sources -- did each device actually produce and ship its data?

Run each of these for the hike window determined in step 0. `jct@m8` is the
data-pipeline gateway/TimescaleDB host; `pi@pi1.local` is the dashboard/log
host; both are already key-authorized from this workstation.

**GPS Track** (already queried in step 0 to set the window) -- row count and
range are the baseline everything else gets compared against.

**air-quality-monitor:**
```
ssh jct@m8 "docker exec -i \$(docker ps --filter name=timescaledb --format '{{.Names}}' | head -1) psql -U jctsh -d jctsh -c \"SELECT count(*), min(ts), max(ts), min(battery_v), max(battery_v) FROM environmental_data WHERE source='air-quality-monitor' AND ts > '<date>' AND ts < '<date+1>';\""
```
Compare the row count to ~1 reading every 2 minutes across the window (same
math the server's own session-summary uses: `duration_minutes / 2 + 1`). A
big shortfall with GPS Track showing a normal hike window means check
whether the device actually uploaded at all -- see step 3's auth-failure
check before assuming data loss; AQM only clears its on-device buffer on a
confirmed upload, so a missing row is very often "not uploaded yet," not
"lost." Also pull boot events for the window:
```
ssh jct@m8 "docker exec -i \$(docker ps --filter name=timescaledb --format '{{.Names}}' | head -1) psql -U jctsh -d jctsh -c \"SELECT * FROM device_boot_events WHERE received_at > '<date>' ORDER BY received_at;\""
```
**A reset recorded here is only meaningful if it happened during the actual
hike window from step 0** -- a reset from someone reflashing the device
hours later (exactly what happened 2026-10-02/03 while fixing the credential
bug) is not a hike-time fault. Check the boot event's `received_at` against
the hike window, not just its presence.

**hiking-monitor:** same category of check (readings, battery range,
reset/reboot evidence) against its own table/source name -- adapt the query
above. hiking-monitor still uses MQTT/replay as of this writing (CARD-0377
hasn't reached it yet), so also check the dashboard log (step 2) for its
heartbeat lines during the window as a connectivity signal this device still
has that AQM deliberately no longer does.

**Hiking Observations / Wildlife Detections / Hike Start Forecast:**
```
ssh jct@m8 "docker exec -i \$(docker ps --filter name=timescaledb --format '{{.Names}}' | head -1) psql -U jctsh -d jctsh -c \"SELECT count(*) FROM hiking_observations WHERE ts > '<date>' AND ts < '<date+1>';\""
ssh jct@m8 "docker exec -i \$(docker ps --filter name=timescaledb --format '{{.Names}}' | head -1) psql -U jctsh -d jctsh -c \"SELECT * FROM wildlife_detections WHERE hike_file_stem LIKE '<date>%';\""
ssh jct@m8 "docker exec -i \$(docker ps --filter name=timescaledb --format '{{.Names}}' | head -1) psql -U jctsh -d jctsh -c \"SELECT * FROM hike_start_forecast WHERE date_local = '<date>';\""
```
Zero rows for any of these is often normal (Joseph doesn't always record a
voice note, BirdNET isn't always run) -- report as "none captured," not as a
failure, unless something else (e.g. a staged-pending BirdNET file, below)
suggests data exists but didn't land.

**Staged/pending BirdNET files waiting on a hike that doesn't exist yet
(exactly today's 2026-10-03 finding):**
```
ssh jct@m8 "ls -la /srv/hike-izer/pending_birdnet_<date>* 2>/dev/null"
```
A file here means BirdNET data arrived but had no matching hike to attach
to at the time -- note it, and check step 3 (generation) to see whether it
got picked up once the hike was published, or is still orphaned.

## 2. Dashboard relay -- did the expected log lines actually show up?

```
ssh -o ConnectTimeout=5 pi@pi1.local "grep -i 'air-quality-monitor\|hiking-monitor' /mnt/jctsh-logs/jctsh.log | grep '<date>'"
```
Look for: AQM's `Bulk upload: ...` and `Session complete: ...` lines (the
second is CARD-0377 Phase 3's own session summary -- read it directly rather
than recomputing coverage/battery-delta by hand, it's already correct);
hiking-monitor's heartbeat lines at roughly its own cadence. A real upload
with **no** corresponding log line here is itself a finding (the relay
chain -- gateway to `hike-izer-orchestrator`'s `/webhook/pipeline-log` to
MQTT to the Pi's log service -- has its own failure modes, separate from the
gateway accepting the data).

## 3. The trigger and generation -- did a hike page actually get produced?

```
ssh jct@m8 "docker logs --since 48h hike-izer-orchestrator 2>&1 | grep -i 'hike-end\|Published hike summary\|reject\|unauthor\|missing or incorrect'"
```
Three distinct outcomes, tell them apart:
- **A `hike-end` call logged, generation published** -- normal case, confirm
  the public page actually loads: `curl -sI https://hikes.jctnet.com/<date>_hike-summary.html`
  (expect `200`, not `404`).
- **A `hike-end` call logged but rejected** (401/"missing or incorrect
  key") -- a credential problem on the webhook-secret itself. Cross-check
  `tos/credential-registry.yaml` for a recent rotation of `webhook-secret`
  with `verified_live: null` -- this is the same failure *shape* CARD-0372's
  AQM holder note already flagged as a real risk, just a different
  credential.
- **Nothing logged for `hike-end` at all** (exactly 2026-10-03's finding) --
  the webhook never reached the server. Rule out a credential cause first:
  if *other* webhook routes on this same container (`/webhook/idea`,
  `/webhook/step2`) succeeded during the hike window, the shared
  `webhook-secret` is fine and the gap is phone-side (GPSLogger's `stopped`
  broadcast, or Tasker's `Hike-izer Done` profile, didn't fire) -- see
  `components/hike-izer-orchestrator/tasker-setup.md` for exactly what's
  supposed to happen there. This is NOT something to fix from here (no SSH
  access to Joseph's phone) -- it's a finding to report, with the one safe
  recovery action named in step 5.

Also check `hike_izer_cost` for a sane entry if generation did run
(`SELECT * FROM hike_izer_cost WHERE ts > '<date>'` via the same psql
pattern as step 1) -- catches a generation run that billed without actually
publishing, or an unexpectedly expensive one.

## 4. Infrastructure underneath all of it

- **Gateway health + any auth failures in the hike window:**
  ```
  ssh jct@m8 "docker logs --since 48h data-pipeline-api 2>&1 | grep -i '<date>\|missing or incorrect\|401\|error'"
  ```
  Repeated "missing or incorrect key" lines are the exact signature of a
  rotation that broke a holder's header format (2026-10-02's AQM incident) --
  if seen, check `tos/credential-registry.yaml` for `data-pipeline-api-key`'s
  holders and whether every one shows a recent `verified_live`, not just
  `verified: true` on the recipe itself (the gap between those two is
  precisely what caused the incident).
- **Container health generally:** `ssh jct@m8 "docker ps --format '{{.Names}} {{.Status}}'"`
  -- everything should read `Up ... (healthy)`.
- **Public reachability:** `curl -sI https://hikes.jctnet.com/` (expect
  `200`) -- rules out a Cloudflare Tunnel problem (CARD-0257 tracks a known
  ongoing crash-bug risk on this exact tunnel) before blaming anything else.
- **Credential cross-check:** if any check above smells like an auth
  problem, run `.\tos\secret.ps1 due` (read-only, no vault touch) and look
  for anything touching this pipeline specifically (`data-pipeline-api-key`,
  `webhook-secret`, `mosquitto-accounts--air-quality-monitor` or
  `--hiking-monitor`) with a recent rotation and an unconfirmed
  `verified_live`.

## 5. Cross-checks and anomalies worth flagging

- **GPS correlation sanity:** spot-check a handful of AQM/hiking-monitor
  rows' `lat`/`lon` against the GPS Track points for the same timestamp --
  they should be close. A device with real readings but all-null lat/lon for
  an otherwise-tracked hike is a correlation gap worth naming, not silently
  passing through.
- **Coverage %:** actual vs. expected reading count per device, same math as
  AQM's own session summary (step 2) -- compute the same way for
  hiking-monitor if its own summary doesn't already report it.
- **Sensor anomalies:** scan for PM2.5/VOC/NOx/temperature values well
  outside the rest of that hike's own range (a sharp, brief spike like
  2026-10-03's 414 µg/m³ PM2.5 reading is a real-world event worth
  surfacing, not an error to explain away -- report it as "worth a look,"
  with the timestamp, and let Joseph judge it against what he remembers).
- **In-hike vs. out-of-hike resets:** already covered in step 1's boot-event
  check -- repeat the reminder here because it's the easiest thing to get
  wrong when skimming a report: a reset timestamped hours after the hike
  ended is not a hike-time reliability problem.

## 6. Produce the summary

One pass/fail/notable line per area above (raw data per device, dashboard
relay, trigger+generation, infrastructure, cross-checks) -- don't bury a
real finding in a wall of query output. Explicitly state, every time:
whether any data appears lost (vs. merely delayed/unpublished -- these read
very differently to Joseph and the distinction matters), and whether
anything found has a known recovery action.

## 7. Recovery actions -- name them, then ask. Never run one unprompted.

The only one documented so far: if step 3 found a missing `hike-end` trigger
but the underlying GPS Track + environmental data are intact, the safe,
idempotent recovery is:
```
ssh jct@m8 'set -a; source ~/hike-izer-web-app/.env; set +a; curl -s -X POST "https://hikes.jctnet.com/webhook/hike-end?key=$WEBHOOK_SECRET" -H "Content-Type: application/json" -d "{\"gpsloggerevent\":\"stopped\",\"local_datetime\":\"<hike-end time, local, ISO8601 with UTC offset>\"}"'
```
This triggers a real `generate()` run -- Nominatim/Overpass/Immich calls and
a billed Anthropic API call for the summary (tracked in `hike_izer_cost`),
not a free retry. State that cost plainly when asking, same as any other
real action this project tracks spend for.

If a problem instead points at a credential (rotation gone wrong, auth
failing) -- **don't attempt a fix here.** Report the finding and hand it to
whichever session owns that credential's rotation (per CARD-0372's "handle
credential fallout as part of the card that caused it" rule) -- this skill
diagnoses, it doesn't rotate or patch secrets.

## Related

CARD-0377 (AQM's redesign -- the session-summary line this skill reads
directly in step 2, and the credential-rotation incident that motivated this
skill), CARD-0372 (the rotation runner/registry this skill cross-checks
rather than duplicates), `.claude/skills/hike-izer/SKILL.md` (generation --
run that, not this, to actually produce/regenerate a hike page),
`.claude/skills/rotate-credentials/SKILL.md` (fixes a credential problem
this skill only diagnoses and hands off), `components/hike-izer-orchestrator/README.md`
and `tasker-setup.md` (the webhook contract and phone-side trigger this
skill's step 3 checks against).
