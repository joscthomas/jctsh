# Outdoor Presence Detection — Component Context

HA-only component. No ESP32, no Node-RED. Two sub-features built on top of
existing Ring hardware (doorbell + 6 other cameras): a spoken motion
announcement, and live doorbell video cast to the Gathering Room TV. See
`jctsh/CLAUDE.md` for monorepo-wide conventions.

**Created 2026-08-20 (CARD-0187).** These automations existed since
2026-08-07 (CARD-0145 raised) / 2026-08-14 (CARD-0146 raised) with no
documented home outside `kanban-board.md`'s card history and
`automations.yaml`'s own inline `description:` comments — unlike
garage-presence, front-porch-temp-sensor, and the renamed `traveling`
component, which already followed the directory-per-app pattern. Codified as
a standing rule in `JCTsh-Build-Standards.md` §7.1a at the same time.

---

# Sub-Feature 1 — Ring Motion Announcement (CARD-0145)

## Origin

Raised 2026-08-07 14:18 MST: play a spoken announcement on Google Home
whenever motion is detected on any of the (originally 7, later found to be 10)
Ring cameras — not just the doorbell. Interview settled: broadest possible
trigger scope, TTS not just a chime, all speakers/displays in the house, no
subset excluded initially.

## Design Decision — HA, Not SmartThings/Google Home Native

Two approaches researched 2026-08-14:
- **HA (chosen):** one automation triggering on the motion `binary_sensor`
  entities, calling `tts.cloud_say` (Nabu Casa) against all target
  `media_player` entities, with a templated per-camera message. Single
  automation, portable if the underlying sensor source ever changes.
- **No-HA alternative (rejected):** a SmartThings virtual switch + routine per
  camera + a Google Home Automation per camera — 21 separately-maintained
  pieces for 7 cameras, and increases reliance on SmartThings specifically
  (relevant given CARD-0164's SmartThings paid-tier deadline).

**Live entity check before Build (2026-08-15):** found 10 real motion sources,
not the 7 named in `ENVIRONMENT.md` (stale) — Side Yard alone had two distinct
cameras (Gate, Path), Back Yard alone had two (Backyard, View Fence). Decided
to include all 10, trigger off HA's native `ring` integration's `event.*`
entities at the time (fire once per discrete motion clip, no separate on/off
state — "once per event" satisfied for free).

## Camera List — Narrowed From 10 to 5, By Joseph's Own Calls

Each removal was a deliberate decision after live use, not a technical
necessity:
1. **Pixel Tablet** dropped from speaker targets (2026-08-15, after the first
   live-fire test) — Joseph's call.
2. **Garage** dropped from the trigger list entirely (2026-08-15).
3. **Gathering Room** dropped (2026-08-15).
4. **Backyard, View Fence, Patio** all dropped in one pass (2026-08-15).

Final 5: **Gate, Path, Front Door, Front Porch, Doorbell.**

Speaker targets similarly narrowed: `master_bath_display` and `patio_speaker`
removed (patio confirmed `unavailable`/offline), `master_bedroom_speaker`
added (confirmed reachable). `master_bedroom_speaker_2` was briefly added,
then removed again after checking it was `unavailable`, same as
`master_bedroom_tv` at the time. Final 3: `garage_speaker`, `groom_speaker`,
`master_bedroom_speaker`.

## Debounce/Queue/Entry-Cluster Design — Three Real Bugs Found Live

**1. Double-fire on a single visit (2026-08-15).** The "event entities fire
once per discrete clip, no debounce needed" assumption was wrong — a real
doorbell visit fired `event.doorbell_motion` twice, 4.9s apart, both
genuinely Ring-originated, producing two stacked "garbled" announcements.
Fixed initially with `for: 10 seconds` on the trigger.

**2. `mode: parallel` allowed overlapping audio (2026-08-15).** The `for: 10s`
fix also delayed every legitimate first announcement by a full 10 seconds, and
separately `mode: parallel` let near-simultaneous different-camera triggers
overlap their `tts.cloud_say` calls on the same speakers — two messages
talking over each other. **Redesigned:** no `for:` on the trigger (first
announcement plays immediately), `mode: queued` (max 20) so only one
announcement plays system-wide at a time, and a trailing `delay:` action after
each TTS call so the next queued announcement can't start until some interval
after the previous one began. Tuned down across live tests: 10s → 5s → 3s,
the 3s figure chosen after confirming even the longest phrase ("Motion at
Gathering Room," since removed) finishes with margin — not mathematically
airtight against a worst-case slow-dispatch + long-phrase combination, but
every real test has been clean. Known tradeoff: a genuine same-camera re-fire
for one visit (like the original 4.9s doorbell double-fire) now plays as two
separate announcements 3s apart rather than being collapsed, traded against
the zero-delay-on-first-play requirement.

**3. Entry-cluster stacking (2026-08-15).** Front Porch, Front Door, and
Doorbell are physically clustered at one entry point — a single visitor
commonly trips two or three in sequence, producing 2-3 near-simultaneous
announcements that read as one run-on phrase. **Fix:** `entry_cluster` (those
3 entity IDs) + a template condition — if a trigger is a cluster member and
another cluster member changed state within the last 30 seconds, suppress
this run (first-one-wins). Only applies to this 3-camera cluster; the other
2 cameras (Gate, Path) are unaffected and always get their own independent
announcement.

## Trigger Source History — Two Full Switches

The trigger source has changed three times, driven by real reliability
findings each time — this is the most-revised piece of either sub-feature.

**v1 (2026-08-15 original build): `event.*_motion`** — HA's native `ring`
integration's push-based entities. Fires once per discrete motion clip.

**v2 (2026-08-15, same day, reverted same day): briefly `sensor.*_last_activity`**
— tried after `event.*_motion` appeared to stop delivering entirely. Introduced
two new problems: the sensor reflects ANY camera activity, not just motion
(fixed with a `category == 'motion'` filter after a false "Motion at Gathering
Room" announcement from an `on_demand_link` activity type), and it's polled at
~60-90s intervals rather than pushed — confirmed via multiple cameras'
`last_activity` updating within 11ms of each other, consistent with a shared
poll cycle. That delay was worse than the outage it worked around, so
**reverted back to `event.*_motion` same day** — working theory then was a
transient Ring/HA cloud-relay issue, with an explicit note to revisit if still
frozen after 2026-08-16.

**v3 (2026-08-18, CARD-0184): back to `sensor.*_last_activity`, permanently.**
`event.*_motion` was found still frozen on 2026-08-18 — 2 days past the
revisit point. Diagnosed live: `event.*_motion` state values were stuck on
2026-08-15 timestamps across two independent real-world tests, surviving both
a full HA restart (`docker restart homeassistant`) and a full Ring integration
delete-and-re-authenticate — ruling out both a stuck process and a stale auth
session. Matches a known upstream bug,
[home-assistant/core#128597](https://github.com/home-assistant/core/issues/128597).
Source inspection of the installed `ring` integration (HA 2026.8.2,
`ring_doorbell` 0.9.14) confirmed the push path runs through a separate
`RingListenCoordinator`/`RingEventListener` that only logs a WARNING if it
fails to start, with no visible retry logic — consistent with a silent,
permanent stall. `sensor.*_last_activity`'s poll cadence comes from
`RingDataCoordinator`'s `SCAN_INTERVAL = timedelta(minutes=1)`, hardcoded in
HA core, not user-configurable. Switched permanently, `category == 'motion'`
filter restored.

**v4 (2026-08-20, CARD-0187): `binary_sensor.*_motion` via ring-mqtt,
permanently.** A real field event the same day measured this automation
firing ~2m56s after the actual motion (22:00:54 UTC actual → 22:03:50 fire) —
far worse than CARD-0184's own ~30s measured baseline. Since `ring-mqtt`
(installed 2026-08-18 for CARD-0146) already publishes its own independent,
near-instant `binary_sensor.*_motion` entities — a separate codebase/
connection from the durably-broken native integration, confirmed reliable
across all of CARD-0146's own testing — switched to it for good, standardizing
both sub-features on one Ring pipeline. `to: 'on'` added to the trigger (not
needed for the old timestamp-valued `sensor.*_last_activity`, but required
here or the automation would also fire on the off transition). `category ==
'motion'` condition removed (not applicable — motion-only by construction).

## Current HA Automation (as of CARD-0187, 2026-08-20)

```yaml
alias: CARD-0145 - Ring Motion Announcement
triggers:
  - trigger: state
    entity_id:
      - binary_sensor.gate_motion
      - binary_sensor.path_motion
      - binary_sensor.front_door_motion
      - binary_sensor.front_porch_motion
      - binary_sensor.doorbell_motion
    to: 'on'
variables:
  camera_names:
    binary_sensor.gate_motion: Gate
    binary_sensor.path_motion: Path
    binary_sensor.front_door_motion: Front Door
    binary_sensor.front_porch_motion: Front Porch
    binary_sensor.doorbell_motion: Doorbell
  camera_messages: {}
  camera_quiet_hours: {}
  quiet_hours: "{{ camera_quiet_hours.get(trigger.entity_id) }}"
  in_quiet_hours: >-
    {{ quiet_hours is not none and (
         (quiet_hours.start < quiet_hours.end and quiet_hours.start <= now().strftime('%H:%M') < quiet_hours.end)
         or
         (quiet_hours.start >= quiet_hours.end and (now().strftime('%H:%M') >= quiet_hours.start or now().strftime('%H:%M') < quiet_hours.end))
       ) }}
  entry_cluster:
    - binary_sensor.front_porch_motion
    - binary_sensor.front_door_motion
    - binary_sensor.doorbell_motion
  entry_cluster_suppressed: >-
    {% set ns = namespace(suppress=false) %}
    {% if trigger.entity_id in entry_cluster %}
      {% for eid in entry_cluster if eid != trigger.entity_id %}
        {% set lc = states[eid].last_changed if states[eid] else none %}
        {% if lc is not none and (now() - lc).total_seconds() < 30 %}
          {% set ns.suppress = true %}
        {% endif %}
      {% endfor %}
    {% endif %}
    {{ ns.suppress }}
conditions:
  - condition: template
    value_template: "{{ not in_quiet_hours }}"
  - condition: template
    value_template: "{{ not entry_cluster_suppressed }}"
actions:
  - action: tts.cloud_say
    target:
      entity_id:
        - media_player.garage_speaker
        - media_player.groom_speaker
        - media_player.master_bedroom_speaker
    data:
      message: >-
        {{ camera_messages.get(trigger.entity_id, 'Motion at ' ~
        camera_names.get(trigger.entity_id, trigger.entity_id)) }}
  - delay:
      seconds: 3
mode: queued
max: 20
```

`camera_messages` and `camera_quiet_hours` are empty dicts by design (standard
message, no quiet hours for all 5 to start) but structured as per-entity-id
lookups so either can be set for an individual camera later without
restructuring the automation.

## v4 Trigger Swap — Confirmed Live, 2026-08-21

Joseph reports real-world use: voice notifications are working great. The
v4 switch (`binary_sensor.*_motion` via ring-mqtt, 2026-08-20) is confirmed
live-tested, not just deployed — closes the open item noted under CARD-0187.

---

# Sub-Feature 2 — Doorbell Live Video (CARD-0146)

## Origin

Raised 2026-08-07 14:18 MST: automatically show the Ring doorbell's live video
feed on the Gathering Room TV when it detects activity, interrupting whatever
was playing, reverting once activity clears. Scope: doorbell only (not the
other 6+ cameras), live video not a static snapshot, automatic interrupt not
voice-command-only.

## Path-Finding — Three Dead Ends Before The Real Solution

**Dead end 1 — Google Home native casting.** Confirmed a hard limitation, not
worth further investigation: Google Home has never supported viewing Ring
video via native camera-to-Chromecast casting (a longstanding Amazon/Google
rivalry limitation — Ring integrates with Alexa/Echo Show, not Google Home).

**Dead end 2 — HA's native `ring` integration.** HA ships `camera.play_stream`
built for exactly this pattern, but real testing (2026-08-14) found it doesn't
work for Ring specifically:
- `camera.play_stream` against the native integration's own camera entity
  (`camera.doorbell_live_view`) fails outright — `does not support play
  stream service`. Reading the installed integration's source directly
  (`homeassistant/components/ring/camera.py`) confirmed it has no
  `stream_source()` method at all; live view is WebRTC-only
  (`async_handle_async_webrtc_offer`), architecturally incompatible with the
  RTSP/HLS pathway `camera.play_stream` requires.
- The community-known fallback, `media_player.play_media` against the
  camera's `camera_proxy_stream` endpoint, succeeded (HTTP 200, did put
  something on the TV) but Joseph confirmed live it showed **a recording from
  the previous day, not a live feed** — this endpoint surfaces cached/recorded
  content for this entity, not real-time video.

**Dead end 3 — SmartThings' own live view.** Checked whether HA's SmartThings
bridge could expose Ring video as a `camera.*` entity, since the SmartThings
app itself shows live video. Confirmed live via `integration_entities
("smartthings")`: zero camera/video-domain entities anywhere. SmartThings'
new camera support (2026.2+) is tied to its Matter 1.5 camera rollout,
currently limited to a small set of Matter-partner cameras (Aqara, Eve,
Xthings) — Ring isn't Matter and isn't among them.

## The Actual Solution — `ring-mqtt`

`tsightler/ring-mqtt` (third-party, actively maintained, 2,671+ commits, 780
stars) bridges Ring's cloud API to MQTT plus an RTSP gateway (`go2rtc`) for
video. Two new pieces required, not one: `ring-mqtt` itself exposes plain
RTSP URLs (not an HA camera entity), so HA's **Generic Camera** integration
is layered on top, pointed at that RTSP URL, to get a real `camera.*` entity
with genuine `stream_source()` support — the one thing the native `ring`
integration's camera entity lacks.

**Deployment (2026-08-18):** own Docker container on the M8 (alongside
NetAlertX/Immich), own bind-mounted config dir, own dedicated Mosquitto
account (`ring-mqtt`, recorded in `credentials.local.md`). Auth via the same
Ring account already used by the native integration, full 2FA support, via
`ring-mqtt`'s interactive CLI init flow (`init-ring-mqtt.js` — a one-time,
Joseph-driven step, not something automatable). Generates `ring-state.json`
(refresh token) + `config.json` in `~/ring-mqtt/config/` on the M8.

**Confirmed live 2026-08-18:** clean container startup, Ring API connected via
the saved refresh token, MQTT connected, 10 devices published via HA MQTT
discovery including an independent `_motion`/`_ding` pair per camera (separate
from the native integration's own entities) and a `Live Stream`/`Event
Stream` switch. `go2rtc` RTSP gateway confirmed listening on `:8554`.

**Generic Camera added** via HA's config-flow REST API directly (no UI
click-through needed), pointed at
`rtsp://192.168.1.165:8554/3ca30803f9b4_live` (`3ca30803f9b4` = the doorbell's
ring-mqtt device ID) with the `ring-mqtt` livestream credentials — created
`camera.192_168_1_165`. **Smoke test passed:** `camera.play_stream` against
`media_player.groom_tv` returned HTTP 200, HA transcoded RTSP→HLS and cast it,
`media_duration: -1` (live-stream indicator, not a fixed-length recording) —
**Joseph confirmed live at the TV: real live video, not a recording.**

## Live Testing — Two Real Bugs Found

**1. `mode: restart` + either-sensor-off wait caused an invisible non-revert
(2026-08-18).** Original design used `mode: restart` (matching the Traveling
component's own lesson at the time) and `wait_for_trigger` on *either* the
ding or motion sensor going off, reasoning a repeat ring wouldn't re-fire
`to: "on"` since the entity would already be "on." That missed that ding and
motion are two **independent** entities with independent timers: motion fired
after ding had already started the automation, and `mode: restart` cancelled
the ding-triggered run and started a fresh one — which re-captured "prior
state" **while the live stream was already playing**, so `prior_content_id`
ended up being the live stream's own HLS URL. The eventual "revert" just
silently resumed the live stream — no actual revert happened. Separately, the
either-sensor-off wait let the run finish once whichever sensor's window was
shorter cleared, even while the other was still active. **Fix:** `mode:
single` (a redundant second trigger during an active interruption is
correctly ignored — unlike the Traveling component's TV-alert case, nothing is
lost by ignoring it, since the original run's own wait already covers full
doorbell-activity clearing) and `wait_template` requiring **both** sensors
off, not either.

**2. Empty `media_content_id` treated as resumable (2026-08-18).** YouTube
TV's Cast session reports `media_content_id` as an empty string, not null —
the original `is not none` check passed on it, which would have called
`play_media` with a blank ID. Fixed to also require non-empty content after
trimming.

## Automation YAML — Deactivated 2026-08-21, This Is The Restore Point

No longer present in `automations.yaml` (removed, see "Status — Deactivated"
above). This is the last-known-good version, preserved here to paste back in
and redeploy when video work resumes.

```yaml
alias: CARD-0146 - Doorbell Live Video on Gathering Room TV
triggers:
  - trigger: state
    entity_id:
      - binary_sensor.doorbell_ding
      - binary_sensor.doorbell_motion
    to: 'on'
variables:
  prior_state: "{{ states('media_player.groom_tv') }}"
  prior_content_id: "{{ state_attr('media_player.groom_tv', 'media_content_id') }}"
  prior_content_type: "{{ state_attr('media_player.groom_tv', 'media_content_type') }}"
actions:
  - action: camera.play_stream
    data:
      entity_id: camera.192_168_1_165
      media_player: media_player.groom_tv
  - wait_template: >-
      {{ is_state('binary_sensor.doorbell_ding', 'off') and
         is_state('binary_sensor.doorbell_motion', 'off') }}
    timeout: '00:04:00'
    continue_on_timeout: true
  - choose:
      - conditions:
          - "{{ (prior_content_id | default('', true) | trim | length > 0) and prior_state in ['playing', 'paused', 'buffering', 'idle'] }}"
        sequence:
          - action: media_player.play_media
            target:
              entity_id: media_player.groom_tv
            data:
              media_content_id: "{{ prior_content_id }}"
              media_content_type: "{{ prior_content_type }}"
    default:
      - action: media_player.media_stop
        target:
          entity_id: media_player.groom_tv
mode: single
```

`ring-mqtt`'s own `number.doorbell_ding_duration`/`number.doorbell_motion_duration`
(180s each) hold each `binary_sensor` "on" for a plateau after its last real
activity — relevant to understanding the trigger's own timing characteristics.

## Known Issue — Premature Stream Termination (Not Yet Fixed)

A real field event (2026-08-20, pulled from HA's history/states API) showed
the live-view stream self-terminating at ~93 seconds into playback — well
before the doorbell sensors cleared (`binary_sensor.doorbell_motion` stayed on
for another ~73s after the stream died) and well under Ring's documented
~10-minute live-view session limit. Root cause not yet diagnosed — candidates:
`ring-mqtt`/`go2rtc`'s own RTSP session handling, HA's own HLS transcode
pipeline timing out independently, or a shorter real Ring-side session limit
than previously documented. Tracked under CARD-0187 Step 3.

## Status — Deactivated (2026-08-21)

Joseph reports video is not working today — "not ready for prime time." Per
Joseph's instruction, the automation itself was deactivated, not just left
running while broken: removed entirely from `automations.yaml` (deployed +
`automation/reload`'d), confirmed via HA's states API that
`automation.card_0146_doorbell_live_video_on_gathering_room_tv` is now
`unavailable`/`restored: true` (no longer config-backed). The doorbell will
not attempt to interrupt the Gathering Room TV at all until this is restored.

The full automation YAML is preserved below ("Current HA Automation") as the
restore point — paste it back into `automations.yaml`, deploy, and reload to
reactivate. CARD-0187's Steps 2-4 (doorbell coordination, stream-drop fix,
missed-event investigation) remain the valid plan for when this is picked
back up; no further diagnosis done this session beyond what's already
tracked below (premature stream termination, missed-first-event gap).

## Known Gap — Missed First Event

The same 2026-08-20 field event showed a real motion event (a delivery
drop-off) that triggered a genuine Ring phone push + Google Home notification,
but left **zero trace** in either Ring pipeline's HA entities across a
4.5-hour history window — neither this sub-feature nor Sub-Feature 1 reacted
to it. Since the native `ring` integration is no longer in use by either
sub-feature, this isn't the already-diagnosed CARD-0184 bug — it's a new,
undiagnosed gap. Tracked under CARD-0187 Step 4; needs a time-anchor from
Ring's own app notification history before container logs can be searched.

---

## Related Kanban Cards

CARD-0145 (motion announcement build), CARD-0146 (live video build), CARD-0184
(diagnosed the native integration's dead `event.*` platform), CARD-0185
(superseded — early trigger-swap proposal, fully absorbed into CARD-0187),
CARD-0187 (active consolidation: shared trigger — done; doorbell voice/video
coordination, stream-drop fix, missed-event investigation — not yet done).

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 18495B, over the 10000B size threshold.

### CARD-0187 · [bug] [outdoor-presence-detection] Ring motion/video pipeline consolidation — shared trigger, doorbell voice/video coordination, missed-event investigation
**Status:** Defer (voice/trigger-source portion confirmed complete — see 2026-08-21 note below; video coordination/fix work deferred)

**Raised 2026-08-20 16:18 MST (Joseph), via live field observation of a real delivery + package pickup at the front door.** Consolidates CARD-0185's scope plus three fresh findings from pulling real HA history/state data for that event, replacing continued piecemeal edits to the already-closed CARD-0145/CARD-0184. **Supersedes and closes CARD-0185** — its trigger-swap scope is fully absorbed here, see that card for its own closing note.

**Why consolidate now, not another incremental card:** CARD-0145 (voice) and CARD-0146 (video) were built independently against two different, separately-maintained Ring integrations — HA's native `ring` integration (`sensor.*_last_activity`, CARD-0184's fix) and the third-party `ring-mqtt` container (`binary_sensor.*_motion`/`*_ding`, CARD-0146's own build) — with zero coordination between them. Four cards (CARD-0145, CARD-0146, CARD-0184, CARD-0185) already cross-reference each other across two weeks on this one feature; two of them are marked Done and kept accumulating new findings anyway. This card is the single place to finish reconciling it.

**Real field data behind this card — a genuine delivery + pickup event, 2026-08-20, pulled directly from HA's history/states API (not estimated from memory):**

1. **The delivery drop-off itself was never seen by either Ring pipeline.** Your phone got a real Ring push + Google Home notification for it, confirming Ring's own cloud detected it — but neither `binary_sensor.doorbell_motion`/`_ding` (ring-mqtt) nor `sensor.doorbell_last_activity` (native integration) show any trace of it anywhere in a 4.5-hour history window. Both independent codebases missed the same event, which points upstream of either integration's own code — a real motion-zone/sensitivity/cooldown setting on the camera itself, or something about how Ring classifies that particular event type, not an integration bug.
2. **The second event (Joseph walking up to retrieve the package) is what both automations actually reacted to** — real timestamps: motion detected 22:00:54 UTC → `binary_sensor.doorbell_motion` on at 22:00:55 → CARD-0146's automation fired within ~1s → TV stabilized on live video at 22:01:21 (~27s after the actual event, matches expectation) → **video stream died on its own at 22:02:42, only ~93s after starting, well before `binary_sensor.doorbell_motion` cleared at 22:03:55** (the automation's own `wait_template` restore condition never got a clean chance to run) → CARD-0145's voice announcement fired at 22:03:50, **~2m56s after the actual motion** — far worse than CARD-0184's own measured ~30s baseline, and not the quick-after-video timing it felt like live.
3. **Net user experience:** live video appeared roughly on schedule, then died prematurely, then an unrelated-feeling voice announcement fired almost 3 minutes later, disconnected from the video that had already come and gone — motivating the coordination work below, not just a trigger-speed fix.

**Scope, decided via interview 2026-08-20:**

1. **Shared trigger source.** Move CARD-0145's trigger from `sensor.*_last_activity` (native integration, polled, ~60-90s+ real-world lag per the finding above) to ring-mqtt's `binary_sensor.*_motion` for all 5 cameras (gate, path, front_door, front_porch, doorbell) — CARD-0185's original scope. Drop the `category == 'motion'` filter (not needed — these entities are motion-only by construction). Re-tune the 3s trailing delay / 30s entry-cluster suppression window against a fast-push source's own timing characteristics, not a poll-based source's. Live-test on all 5 cameras, not just doorbell.
2. **Doorbell voice/video coordination — decided behavior: skip voice entirely if video shows.** For the doorbell only (the one camera with both), video is the notification — if `camera.play_stream` successfully renders on `media_player.groom_tv`, no voice announcement plays for that event. Voice fires as a fallback only if video fails to start. The other 4 voice-only cameras are unaffected — this logic is doorbell-specific, added as a condition on CARD-0145's automation (not a merge of the two automations — kept separate for failure isolation and complexity reasons, see design discussion this session).
3. **Fix CARD-0146's premature stream termination.** Diagnose why the live-view stream self-terminated at ~93s (well under Ring's documented ~10min live-view session limit) — check ring-mqtt's own `number.doorbell_motion_duration`/`_ding_duration` plateau settings, go2rtc/RTSP gateway logs, and whether the automation's `wait_template`/restore logic needs to react to the stream dying on its own rather than assuming it only ends via the motion-cleared path.
4. **Investigate the missed-first-event gap — root cause required, not just documented.** Check Ring app-side motion zone/sensitivity/frequency settings for the doorbell, whether a cooldown/snooze window is suppressing rapid back-to-back detections, and whether ring-mqtt/the native integration's own logs show anything around the delivery's actual timestamp (unknown — only the phone notification confirms it happened; no HA-side timestamp exists to search from). May take a few more real-world events to catch it recurring before a cause can be confirmed.

**Done when:**
- CARD-0145 triggers on `binary_sensor.*_motion` for all 5 cameras, live-tested and correctly debounced.
- Doorbell events: video plays and voice is correctly suppressed when video succeeds; voice correctly fires as fallback when video fails (both paths live-tested, not just configured).
- CARD-0146's stream no longer terminates prematurely mid-visit, confirmed against a real live event lasting past the ~93s mark previously observed.
- The missed-first-event gap has a confirmed root cause (not just a plausible theory) and, if fixable, a fix in place — or, if genuinely undiagnosable after reasonable investigation, that's recorded here explicitly with what was ruled out, not left silently open.

**Related:** CARD-0145 (voice automation being retargeted), CARD-0146 (video automation being fixed/coordinated), CARD-0184 (diagnosed the native integration's dead `event.*` platform, whose `sensor.*_last_activity` fallback this card retires as a trigger source), CARD-0185 (superseded — see below).

**Step 1 deployed, 2026-08-20 18:00 MST.** CARD-0145's trigger swapped from `sensor.*_last_activity` to ring-mqtt's `binary_sensor.*_motion` (all 5 cameras), `to: 'on'` added, `category == 'motion'` condition removed, `camera_names`/`entry_cluster` updated — deployed via `scp` + `automation/reload`, confirmed live via HA's own config API (loaded description matches the deployed file byte-for-byte). **Not yet live-tested against real motion on all 5 cameras** — only the doorbell was proven reliable pre-swap. Steps 2-4 (doorbell coordination, stream-drop fix, missed-event investigation) not yet started.

**Documentation gap closed, same session.** CARD-0187's own investigation surfaced that neither Traveling Mode's TV alert (CARD-0150) nor either Ring automation (CARD-0145, CARD-0146) had a documented home outside this file and `automations.yaml`'s own inline comments — unlike garage-presence/front-porch-temp-sensor/traveling-lights, which already followed a directory-per-app pattern without it being written down as a rule. Fixed both the gap and the missing rule:
- **New standing convention:** `JCTsh-Build-Standards.md` §7.1a — every HA-only automation app gets a `components/<name>/` directory (README + CLAUDE.md), same as any hardware component (v1.20 → v1.21).
- **`components/traveling-lights/` renamed to `components/traveling/`** (`git mv`) and its README/CLAUDE.md restructured into two sub-features — Traveling Lights (unchanged content) and Unexpected TV Activity (CARD-0150's full investigation/design/bug history, previously only in this file, moved in verbatim from the card history above).
- **New `components/outdoor-presence-detection/`** created — README + CLAUDE.md covering both Ring sub-features (Motion Announcement, Doorbell Live Video), full path-finding/dead-end history, both automations' current YAML, and the two known-issue writeups (premature stream drop, missed first event) from this card.
- Root `README.md`'s System Status table updated (new `outdoor-presence-detection` row, `traveling-lights` link corrected to `traveling`).
- All 4 affected automations in `automations.yaml` got a one-line "See components/.../CLAUDE.md" pointer added to their existing inline `description:` blocks, deployed and reloaded — closes the loop from the quick-reference YAML comment back to the full documented history, and vice versa.

**Voice confirmed, video deferred — 2026-08-21 18:57 MST.** Joseph reports real-world use: voice notifications (Step 1's shared trigger source, `binary_sensor.*_motion`) are working great — satisfies the first "Done when" bullet above (live-tested, not just deployed). Video (Steps 2-4 — doorbell voice/video coordination, the premature stream-termination fix, and the missed-first-event investigation) is not working today and "not ready for prime time" — deferred, not abandoned. Closing this card's voice/trigger-source scope as done in spirit; the card as a whole stays open at Defer status since the remaining "Done when" bullets (video coordination, stream fix, missed-event root cause) are unmet and not being actively worked. Revisit video scope when there's appetite to pick it back up — Steps 2-4 above are still the valid plan, just not started.

**Video automation actually deactivated, same session, 19:00 MST.** Not just documented as deferred — CARD-0146's automation (`id: '1786800000002'`) removed entirely from `automations.yaml`, deployed to the Pi, and reloaded. Confirmed live via HA's states API: `automation.card_0146_doorbell_live_video_on_gathering_room_tv` now reports `state: unavailable` / `restored: true` (no longer config-backed, just a leftover registry entry) — the doorbell will no longer attempt to interrupt the Gathering Room TV at all until this is restored. Full automation YAML preserved in `components/outdoor-presence-detection/CLAUDE.md`'s "Current HA Automation" section for Sub-Feature 2 — restore from there when video work resumes. Voice (CARD-0145) untouched, still active.

---

## Implementation Plan (Planning, 2026-08-20)

Written against the actual current YAML in `core/homeassistant/automations.yaml` (ids `1786800000001` CARD-0145, `1786800000002` CARD-0146), not from memory. Four steps, in dependency order — Step 2 depends on Step 1's entity IDs, Step 3 and Step 4 are independent of the other two and can happen in any order.

### Step 1 — Shared trigger source (CARD-0145 → ring-mqtt)

**Change the `triggers:` block** from `sensor.*_last_activity` (5 entities) to `binary_sensor.*_motion` (5 entities), **with `to: 'on'` added** — this is a real correction, not just a rename. `sensor.*_last_activity` is a timestamp string that gets a new value on every poll, so a bare `trigger: state` (no `to:`) only ever fires on genuine value changes. `binary_sensor.*_motion` toggles on/off; without `to: 'on'` the automation would also fire on the off transition, doubling every announcement. Also update the `camera_names` and `entry_cluster` variable dicts/lists to the new entity IDs (same structure, new keys).

**Drop the `category == 'motion'` condition** — not applicable to `binary_sensor.*_motion` (motion-only by construction, confirmed in CARD-0185's own research; matches the same reasoning already used for the old native-integration `event.*_motion` entities before CARD-0184's fix).

**Debounce/queue logic — evaluate, likely no change needed.** The `mode: queued` (max 20) + trailing `delay: 3s` exists to space out TTS calls across *different* cameras system-wide, and the entry-cluster 30s suppression exists because Front Porch/Front Door/Doorbell are physically clustered — both are about cross-camera behavior, not about the trigger source's own timing characteristics, so neither should need retuning just from the source swap. The one real question: does ring-mqtt's `binary_sensor.*_motion` ever double-fire (on→off→on) for a single real visit the way the old native `event.*_motion` platform did (the original 2026-08-15 doorbell double-fire, 4.9s apart)? Not yet known — ring-mqtt holds each `binary_sensor` "on" for a plateau (`number.<camera>_motion_duration`, 180s for the doorbell) after its last real detection, which should collapse rapid re-triggers into one continuous "on" span rather than distinct on/off/on cycles — but confirm this live rather than assume it, since it directly affects whether the debounce logic actually needs anything new.

**Deploy and test:** `scp` to `/mnt/jctsh-logs/homeassistant/automations.yaml`, `automation/reload` (per `CLAUDE.md`'s standard deploy pattern). Live-test against real motion on all 5 cameras, not just the doorbell (the only one proven so far, per CARD-0185's own note) — confirm each announces correctly, confirm entry-cluster suppression still only allows one announcement when Front Porch/Front Door/Doorbell fire close together, confirm no double-announcements.

### Step 2 — Doorbell voice/video coordination (skip voice when video succeeds)

**New helper entity required:** `input_boolean.doorbell_video_live`, defined in `core/homeassistant/configuration.yaml` (version-controlled, not a UI-only helper) so it survives a from-scratch HA rebuild like the rest of this repo's tracked config.

**CARD-0146 sets it:** turn `input_boolean.doorbell_video_live` **on** immediately after the `camera.play_stream` action (that action either succeeds or the automation raises/stops — no separate success check needed, since a raised error already halts the sequence before reaching the "on" step). Turn it **off** at the end of the automation, in both branches of the existing `choose` (the resume-prior-content branch and the `default`/`media_stop` branch) — guarantees the flag always clears whether the run finished via `wait_template` success or the 4-minute timeout.

**CARD-0145 checks it, doorbell-only:** add a `choose` inside the doorbell trigger's action path — actually, since the existing `actions:` block is a flat `tts.cloud_say` + `delay` shared by all 5 cameras, restructure to: for the doorbell trigger specifically, first `delay` a few seconds (long enough for CARD-0146's `camera.play_stream` call to have committed one way or the other — today's data showed CARD-0146 firing within ~1s of the trigger, so a 3-5s wait should be enough margin, but this needs live-tuning, not a guessed-right-first-time constant) then check `input_boolean.doorbell_video_live`: if **on**, skip the TTS action entirely (video succeeded, it's the notification); if **off**, proceed with the announcement (video failed to start — fallback). The other 4 cameras keep their existing immediate-fire behavior unchanged, no delay, no condition — this logic only branches for `trigger.entity_id == 'binary_sensor.doorbell_motion'`.

**This is the fiddliest step in this plan** — coordinating two independently-triggered automations via a shared helper always has a race-condition edge (what if CARD-0146's own trigger is suppressed or delayed for some unrelated reason and the helper flips on *after* CARD-0145's wait already expired?). Budget real live-test iteration here, not a one-shot deploy-and-done — this file's own history shows every piece of CARD-0145/CARD-0146's existing logic went through 2-4 rounds of live-test-and-fix before landing.

### Step 3 — Fix CARD-0146's premature stream termination

**Investigate first, don't guess a fix.** Root cause unknown — candidates: ring-mqtt/go2rtc's own RTSP session handling dropping early (check `docker logs ring-mqtt` on the M8 around the already-captured 2026-08-20 22:02:42 UTC timestamp — logs may still be in scrollback from this exact incident, worth checking before waiting for a fresh repro), HA's own HLS transcode pipeline timing out independent of Ring's side (check `docker logs homeassistant` same window), or a Ring-side live-view session limit shorter than the ~10min figure previously documented from ring-mqtt's own docs.

**Once root cause is known**, the fix is either a config change (e.g., a go2rtc/session-duration setting) or a firmware-side accommodation (e.g., the automation detects the stream ending early via a `wait_template` on `media_player.groom_tv` leaving `playing`/`buffering` state, not just on the doorbell sensors clearing, and either restarts `camera.play_stream` once or falls through to the existing resume/stop logic immediately rather than sitting on a dead feed until the 4-minute timeout). Exact fix is not specified further here — depends entirely on Step 3's own investigation findings.

### Step 4 — Missed-first-event investigation

**Needed from Joseph first:** a rough time anchor for when the delivery notification actually arrived on your phone (check the Ring app's own notification history, which has its own timestamp independent of anything HA-side) — without that, there's no window to search logs against. The HA-side history pull already confirmed there's nothing to find on the HA/ring-mqtt side without an external anchor.

**Once a time window is known:** check `docker logs ring-mqtt` and `docker logs homeassistant` (both M8/Pi respectively) around that window for any error/warning; check the Ring app itself (Joseph-does step, not queryable via HA) for the doorbell's motion zone, sensitivity, and motion-frequency/snooze settings — a delivery drop-off (brief presence, no lingering) is a plausible case for a motion-zone or minimum-duration filter to reject while a slower, more deliberate approach (Joseph walking up) passes.

**If no root cause emerges from the first pass**, this is an explicit "watch and wait" per the interview decision — don't close this scope item on a guess; wait for a recurrence with a known timestamp and repeat the log check, and record each attempt (successful repro or not) here rather than letting the investigation go silent.

---

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 10489B, over the 10000B size threshold.

### CARD-0184 · [bug] [outdoor-presence-detection] CARD-0145's Ring motion announcement has been silently dead since 2026-08-15 — RESOLVED 2026-08-18 17:02 MST
**Status:** Done

**Raised 2026-08-18 22:15 MST (Joseph):** a visitor walked up to the front porch; Ring's own app sent a phone notification, but no Google Home voice announcement played.

**Root cause investigated live, 2026-08-18 22:15-22:25 MST:** not front-porch-specific — `automation.card_0145_ring_motion_announcement`'s `last_triggered` was `2026-08-15T02:09:19`, over 3 days stale, for **every** camera, not just this one. Every `event.<camera>_motion` entity (the automation's trigger source) is frozen at a `state` value (the event's own reported timestamp) from the night of 2026-08-15 — right when CARD-0145 was originally built and verified. Meanwhile `sensor.<camera>_last_activity` entities (a separate, poll-driven Ring sensor) are updating normally and recently across every camera (front door 11:16 UTC, garage 21:41 UTC, doorbell/gathering room ~22:02 UTC, front porch's own camera showing a fresh cloud connection at 22:05 UTC — right in the reported visit window) — confirming Ring's cloud connection and HA's underlying Ring integration are both fine. Specifically the `event.*` platform's live-push path has been broken for over 3 days.

**This is not new — it's the exact scenario `automations.yaml`'s own CARD-0145 description already anticipated.** On 2026-08-15, this same `event.*_motion` freeze was hit during the original build, worked around by switching triggers to `sensor.*_last_activity`, which introduced two real problems: false announcements from non-motion activity categories (`category` attribute needed a `== 'motion'` filter) and a 60-90+ second polling delay (multiple cameras' `last_activity` updating within 11ms of each other, consistent with a shared poll cycle, not live per-event delivery). Joseph reverted to `event.*_motion` the same day, on a working theory that the freeze was a transient Ring/HA cloud-relay issue, with an explicit note to **revisit if still frozen after 2026-08-16.** It is now 2026-08-18 and still frozen — two days past that revisit point, confirmed not self-clearing.

**Reload attempted, 2026-08-18 22:24 MST — did not actually fix the underlying issue.** Reloading the Ring integration made the automation fire (Joseph heard a voice announcement) and bumped every `event.*_motion` entity's `last_updated` simultaneously — but their `state` **values** (the actual event timestamps) are unchanged, still stuck on 2026-08-15. This means the reload just re-wrote/re-registered the entities from stale cached data, which the automation's plain `state` trigger fired on regardless of the value not changing — not evidence of a genuine new event getting through. The underlying breakage in the `event.*` platform is still present as of this note.

**Not yet decided:** how to actually fix this, now that the "revisit" condition has been hit. Options on the table: (1) re-attempt the `sensor.*_last_activity` trigger, this time keeping the `category == 'motion'` filter from the start and accepting the 60-90s delay as better than 3+ days of silence; (2) dig further into why `event.*` specifically stopped updating (HA `ring` integration version/known-issue check, full HA restart rather than just an integration reload, re-authenticating the Ring integration); (3) something else. Revisit at Planning with Joseph.

**Dig-in requested 2026-08-18 15:30ish MST (Joseph):** a 60-90s polling delay (the `sensor.*_last_activity` alternative) isn't acceptable — investigate the `event.*` platform freeze itself rather than switch trigger sources.

**Root cause confirmed via web research, 2026-08-18 15:35ish MST:** matches a known upstream Home Assistant `ring` integration bug ([home-assistant/core#128597](https://github.com/home-assistant/core/issues/128597) — "Ring integration stops updating motion event requiring integration reload"). Ring's real-time push delivery runs over a persistent outbound connection to port 5228, separate from the regular polled REST calls `sensor.*_last_activity` etc. use — when that connection drops without cleanly reconnecting, the event platform goes silent while everything else on the integration keeps looking healthy, exactly what's observed here. Community reports point to a full HA restart (not just an integration-config-entry reload) as the standing workaround.

**Confirmed HA version 2026.8.2, `ring_doorbell` library 0.9.14** — current versions, not an old/unpatched build.

**Important complication found before restarting:** the Pi's weekly scheduled reboot (`scheduled-reboot.timer`, Mon 3:00 AM MST) already ran once since the freeze started — Mon 2026-08-17 03:00 MST, confirmed via HA container's own `StartedAt` timestamp (2026-08-17T10:01:54 UTC = 03:01:54 MST). That's a full OS/process restart, the same class of fix the community reports point to — and the `event.*` entities were *still* frozen with 2026-08-15 values over 34 hours later, right up until today's manual restart. So a full restart alone did not hold last time; either it doesn't fully fix this, or the underlying port-5228 connection re-breaks on its own again after some period.

**Manual full restart performed, 2026-08-18 15:35 MST.** `docker restart homeassistant` on the Pi failed outright (`Error response from daemon: Cannot restart container homeassistant: tried to kill container, but did not receive an exit event`) — the kill half completed (container exited, code 137) but the daemon didn't proceed to the start half. Recovered with a manual `docker start homeassistant`; HA back up and answering API calls within ~15s, container confirmed `running`/`healthy`. Automation and Ring entities re-registered on startup as expected, but `event.*_motion` state **values** are still showing the same stale 2026-08-15 timestamps immediately post-restart — expected right after a restart (last-known cached value until a genuinely new event arrives), not itself a sign of failure or success.

**Not yet verified — needs a real motion event to actually test.** Given the weekly-reboot precedent above, this restart can't be called a fix on restart alone; it has to be confirmed against a real, live Ring motion event actually producing a fresh `event.*_motion` state value and a prompt (not delayed) announcement. Next real visit/motion at a covered camera is the test. If it fails again, likely worth: re-checking after another few days in case the reconnect is just slow this time, or filing/following #128597 upstream for a real fix rather than continuing to work around it locally.

**Done when:** the Ring motion announcement fires reliably and promptly on a real, current motion event (not a reload/restart artifact), verified live against an actual visit — and the outcome (holds, or breaks again) is documented here either way, plus the chosen fix in `automations.yaml`'s own CARD-0145 description alongside its existing revision history.

**Second live test: a full Ring integration delete-and-re-authenticate (Joseph's own action, 2026-08-18 ~16:30 MST) also failed to fix `event.*`.** Two confirmed real walk-bys (gate + front porch) after the fresh re-auth both registered correctly on `sensor.*_last_activity` within about a minute, but `event.gate_motion`/`event.front_porch_motion` never updated and the automation never fired for either. This rules out a stuck process (already ruled out by the restart) *and* a stale/corrupted auth session as the cause — two independent, different-mechanism fixes both failed against live, confirmed-real tests.

**Joseph's call, 2026-08-18 ~16:35 MST: options 1 + 2 + 3 from the list above.** Investigated in order:
1. **Poll interval configurability (option 2) — not configurable.** Read the installed `ring` integration's source directly in the container (HA 2026.8.2): `RingDataCoordinator` (drives `sensor.*_last_activity`) uses `update_interval=SCAN_INTERVAL`, `SCAN_INTERVAL = timedelta(minutes=1)` in `const.py` — hardcoded, no options flow exists for it anywhere in `config_flow.py`. Not adjustable without patching HA core source directly, which isn't sustainable against upstream updates. Also found the likely root cause while in there: the *push* path runs through a separate `RingListenCoordinator`/`RingEventListener`, whose `_async_start_listen()` logs only a `_LOGGER.warning` if the listener fails to start and has no visible retry logic in the coordinator itself — consistent with a silent, permanent stall rather than a transient blip, and matching the two failed-fix results above.
2. **Switched the automation for good (option 1).** `core/homeassistant/automations.yaml`'s CARD-0145 automation trigger changed from `event.*_motion` to `sensor.*_last_activity` (5 entities: gate, path, front door, front porch, doorbell) with the `category == 'motion'` filter restored from the 2026-08-15 attempt (as a template condition this time, evaluated against `trigger.to_state.attributes`) — `camera_names`/`entry_cluster` variables updated to match, all debounce/queue/quiet-hours/message logic otherwise unchanged. Deployed via `scp` + `automation/reload`, confirmed the automation picked up the new config (`state: on`).
3. **Verified live, 2026-08-18 17:01 MST.** Joseph did one more real walk-by; `last_triggered` moved to a genuinely new timestamp (`2026-08-19T00:01:00`, not stale carryover) within the poll cycle, no errors in the HA log around that time, and **Joseph confirmed hearing the announcement clearly, ~30 second delay** — well within what he'd already said was acceptable once the alternative was proven durably broken rather than just slow.
4. **Option 3 (file findings upstream on home-assistant/core#128597) — drafted, pending Joseph's review before posting** (public GitHub comment, confirming before it goes out). See next message/commit for the draft.

**Resolved 2026-08-18 17:02 MST.** Working, verified announcement restored on `sensor.*_last_activity` with the motion-category filter, ~30s delay accepted as the tradeoff against a real-time path now confirmed durably broken two different ways. `automations.yaml`'s own CARD-0145 description block carries the full history (2026-08-15 attempt, 2026-08-18 dig-in and permanent switch) so this doesn't get relitigated from scratch if it resurfaces.

**Related:** CARD-0145 (the announcement automation this is a regression of).

---

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 22393B, over the 10000B size threshold.

### CARD-0145 · [idea] [outdoor-presence-detection] Audible Ring motion notification on Google Home — RESOLVED 2026-08-18 17:14 MST
**Status:** Done

**Raised 2026-08-07 14:18 MST.** Play a spoken announcement on Google Home whenever motion is detected on any of the 7 Ring cameras (garage, side yard, side gate, back porch, front porch, front door, gathering room) — not just the doorbell. Announcement plays on all Google Home speakers/displays in the house (garage, gathering room, back porch speakers, master bath Nest Display, gathering room Pixel Tablet), not just a subset.

**Interview notes (2026-08-07):**
- Trigger: any motion event on any of the 7 cameras (broader than doorbell-only) — Ring/SmartThings/HA already carries these as entities per `ENVIRONMENT.md`, no new sensor hardware needed.
- Form: spoken TTS announcement (not just a chime) — needs HA's Google Cast/TTS path to Google Home wired up if not already.
- Scope: all speakers/displays, no subset excluded (including master bath and garage).
- **Open design question, not yet resolved:** "any motion on any of 7 cameras" firing to every speaker in the house has real noise/nuisance potential (wind, cars, mail carrier, pets) — worth deciding during Planning whether the announcement identifies which camera triggered (e.g. "Motion at back porch") and whether any throttling/cooldown is needed to avoid repeated announcements for the same ongoing event.

**Two viable approaches researched 2026-08-14, decided: go with HA.**
- **HA approach (chosen)**: one automation triggering on any of the 7 motion `binary_sensor` entities (already live via the existing SmartThings bridge, no new integration needed — unlike CARD-0146, this needs zero new infrastructure), calling `tts.cloud_say` (Nabu Casa's already active, no separate TTS setup) against all 5 target `media_player` entities, with a templated message naming the triggering camera. Single automation, maintainable, and keeps the logic portable if the underlying sensor source ever changes later (e.g. if CARD-0164's SmartThings decision eventually moves these sensors off SmartThings, only the trigger entity_ids need updating, not the whole automation).
- **No-HA alternative (documented, not chosen)**: SmartThings virtual switch per camera (7) → SmartThings routine (motion → switch on) → Google Home Automation (switch on → broadcast message), all UI-configured in the SmartThings/Google Home apps, zero HA involvement. Real tradeoff against this: 21 separately-maintained pieces (7 switches + 7 routines + 7 automations) with hardcoded per-camera messages, and it *increases* reliance on SmartThings' own routine engine specifically — relevant to CARD-0164, since these routines would need rebuilding too if SmartThings is ever migrated away from, unlike HA-side logic.
- Exact entity IDs for both the 7 motion sensors and 5 speakers/displays still need live confirmation against real HA state before Build (some cameras appear to have both a standalone motion sensor and a separate camera-motion entity — needs disambiguating, not assumed) — see CARD-0146's research for the same discipline applied there.

**Interview, 2026-08-15 (resolving the open design question above):**
- **Cooldown:** once per event, not a fixed timer. Trigger on the rising edge of each motion `binary_sensor` (motion detected); stay silent while that sensor's motion stays active/re-triggers; only fires again once it's cleared and a new motion event starts. No cross-camera suppression — simultaneous motion on two different cameras both announce.
- **Message content:** standard templated message for all 7 to start ("Motion at \<camera\>"), no per-camera wording differentiation yet — but build the template as a lookup (e.g. a dict/variable mapping camera entity_id → message, defaulting to the standard phrase) so a custom message can be set per camera later without restructuring the automation.
- **Quiet hours:** no quiet hours, standard for all 7 cameras to start — but built as a per-camera lookup/option (same pattern as the message content above, e.g. a dict/variable mapping camera entity_id → quiet-hours window, defaulting to "none") so a specific camera's hours can be set later without restructuring the automation.

**Live entity check before Build, 2026-08-15 (via HA's WS admin API, entity/device/area registries):** found 10 real motion sources, not the 7 named in `ENVIRONMENT.md` — that doc is stale. Side Yard alone has two distinct cameras (Gate, Path); Back Yard alone has two (Backyard, View Fence). Also discovered HA's native `ring` integration is now live (`camera.*_live_view`/`event.*_motion` entities exist with proper area assignments) — CARD-0146's "zero camera entities" research finding from the day before is now out of date; worth a quick re-check there. Decided in a follow-up interview: include all 10 (doorbell included), trigger off the native `event.*` entities rather than the older SmartThings-bridged `binary_sensor.*_motion` ones — event entities fire once per discrete motion clip with no separate on/off state, so "once per event" is satisfied for free with no extra debounce logic.

**Built and deployed, 2026-08-15.** New automation `CARD-0145 - Ring Motion Announcement` (id `1786800000001`) in `core/homeassistant/automations.yaml`: state trigger on all 10 `event.*_motion` entities (garage, gate, path, patio, backyard, view_fence, front_door, front_porch, gathering_room, doorbell) → `tts.cloud_say` targeting the 5 speakers/displays (`garage_speaker`, `groom_speaker`, `jct_pixel_tablet`, `master_bath_display`, `patio_speaker`) with a templated "Motion at \<camera\>" message. `camera_messages` and `camera_quiet_hours` are both empty dicts keyed by entity_id — per-camera message and per-camera quiet-hours are both live mechanisms already wired into the template/condition logic, just unpopulated, so either can be set for one camera later without restructuring the automation. `mode: parallel` (max 10) so simultaneous motion on different cameras doesn't get dropped or queued, per the "no cross-camera suppression" decision. Deployed via `scp` + `automation/reload`, confirmed live (`state: on`).

**Verified live, 2026-08-15:**
- Message-templating Jinja rendered correctly via `/api/template` for known and unmapped entity IDs (graceful fallback confirmed).
- Real `tts.cloud_say` call against all 5 target speakers: 4 of 5 (Garage speaker, Groom speaker, JCT Pixel Tablet, Master Bath Display) showed genuine `idle → buffering → playing` state transitions with real generated TTS audio (unique `/api/tts_proxy/*.mp3` URL each) — actual playback, not just a clean API response.
- **Real finding, not yet resolved:** `media_player.patio_speaker` (back porch, the target for Patio/back-porch motion) is currently `state: unavailable` — offline/unreachable independent of this automation. The `tts.cloud_say` call didn't error, it silently skipped that one target. Back porch motion won't announce anywhere until this speaker is back online; worth checking why it's down (Cast/WiFi issue vs. actually offline) before closing this card.
**Confirmed live end-to-end, 2026-08-15 01:14:57 UTC — a real Ring doorbell motion event** (`event.doorbell_motion`, not a synthetic test) fired the automation and all 4 then-reachable speakers (Garage, Groom, Master Bath Display, JCT Pixel Tablet) genuinely played TTS audio — real `idle → buffering → playing` transitions with a unique `/api/tts_proxy/*.mp3` per speaker, confirmed via HA's history API. `patio_speaker` stayed `unavailable` throughout, consistent with the standalone finding above. Trigger and TTS mechanics are both now proven against real production events, not just manual smoke tests.

**Pixel Tablet removed from the announcement targets, 2026-08-15** (Joseph's call, after the above live-fire test) — `media_player.jct_pixel_tablet` dropped from the `tts.cloud_say` target list.

**Real bug found from the live-fire test's own data, 2026-08-15: reported as "garbled and not clear" in practice.** Checked the history around the 01:14:57 trigger and found `event.doorbell_motion` actually changed state *twice* for that one visit — 01:14:52.173 and 01:14:57.113, 4.9s apart, both genuine Ring-originated state changes — so the automation fired twice and every speaker played two "Motion at Doorbell" announcements stacked ~2.3s apart. The original "event entities fire once per discrete clip, no debounce needed" assumption (written into the automation's own description) was wrong. **Fix:** added `for: 10 seconds` to the state trigger — collapses repeat fires per camera (tracked independently per entity_id) without suppressing simultaneous-but-different-camera announcements, so `mode: parallel`'s cross-camera behavior is unaffected. Deployed and reloaded, confirmed `state: on`.

**Target list finalized, 2026-08-15** — `master_bath_display` and `patio_speaker` (still `unavailable`) both removed; `media_player.master_bedroom_speaker` added instead (confirmed reachable, `state: off`/idle, not unavailable). `master_bedroom_speaker_2` was briefly added too, then checked against Master Bedroom's full media_player inventory (3 entities: `master_bedroom_speaker` reachable, `master_bedroom_speaker_2` and `master_bedroom_tv` both `unavailable`) and removed again — Joseph's call, not carrying an offline entity in this target list. Final target list: `garage_speaker`, `groom_speaker`, `master_bedroom_speaker`.

**Debounce fix verified, 2026-08-15 01:26 MST** — simulated a Gate motion event (`POST /api/states/event.gate_motion` with a fresh timestamp, mimicking the real Ring event format) to test without waiting for real motion. Automation fired exactly once, 10.01s after the simulated write (`last_triggered` timing and `context.parent_id` both trace directly back to the simulated state change) — confirms the `for: 10s` debounce is working as designed. All 3 final targets (`garage_speaker`, `groom_speaker`, `master_bedroom_speaker`) played the TTS exactly once each, single clean `idle → buffering → playing → idle` cycle, no doubling — the garbled/doubled-announcement bug from the earlier real doorbell event is fixed.

**Cross-camera sequence tested, 2026-08-15 01:27 MST** — simulated Front Porch, Front Door, and Doorbell motion 2s apart (mimicking someone walking up: porch → door → doorbell). All three fired independently on their own 10s debounce clocks (~10s after each one's own simulated event, confirmed via history) — no cross-camera suppression, matching the Planning decision. Each individual announcement played cleanly once. Real observed side effect: because the source events were only 2s apart, the three announcements landed back-to-back on the same speakers with almost no gap (as little as 0.08s between one ending and the next starting on `garage_speaker`) — three distinct phrases in rapid succession, which could read as one run-on if a real visitor triggers multiple cameras walking up. **Decided, 2026-08-15: leave as-is** — no global minimum gap between different cameras' announcements, matches the original no-cross-camera-suppression decision from Planning.

**Garage camera removed from the trigger list, 2026-08-15** (Joseph's call) — `event.garage_motion` dropped from both the trigger's `entity_id` list and the `camera_names` lookup. 9 cameras remain: Gate, Path, Patio, Backyard, View Fence, Front Door, Front Porch, Gathering Room, Doorbell. Garage motion no longer produces an announcement at all (not just muted at the speaker end — the trigger itself is gone). Deployed and reloaded.

**Debounce model redesigned, 2026-08-15** — two real complaints after live use: the `for: 10s` trigger delay made every single announcement (including the first, legitimate one) wait a full 10 seconds, and separately `mode: parallel` let near-simultaneous triggers overlap their `tts.cloud_say` calls on the same speakers (unacceptable — more than one message voiced at once). Replaced with: no `for:` on the trigger (first announcement plays immediately), `mode: queued` (max 20) so only one announcement plays system-wide at any time, and a trailing `delay: 10s` action after the TTS call so the next queued announcement can't start until 10s after the previous one began. Scope is global across all 9 cameras, not per-camera (Joseph's explicit call this round, superseding the earlier "leave cross-camera stacking as-is" decision from the sequence test above). Known tradeoff, called out directly: a real same-camera re-fire for one visit (like the original doorbell double-fire, 4.9s apart) will now play as two separate announcements 10s apart rather than being collapsed into one — accepted in exchange for zero delay on first play and a hard guarantee against overlapping audio.

**Verified live, 2026-08-15 01:34 MST** — simulated Front Porch then Front Door 2s apart. Front Porch played immediately (`buffering` within 0.4s of the simulated event). Front Door queued and did not start until exactly 10s after Front Porch began (`01:34:43.44` → `01:34:53.5`) — confirmed via `garage_speaker`'s playback history. No overlap, correct immediate-first/10s-queued-after behavior.

**Trailing delay shortened to 5s, 2026-08-15** (Joseph's call) — same immediate-first/queued-after model, just a tighter gap. Re-verified live with the identical two-camera test: Front Porch played immediately (`01:35:50.92`), Front Door queued and started exactly 5s later (`01:35:55.95`). No overlap.

**Shortened further to 2s, then 3s, 2026-08-15.** At 2s: retested the same two-camera sequence — no overlap, but only by a ~0.2s margin (the delay timer starts when the TTS call is issued, not when audio finishes, so it's not mathematically guaranteed safe for a longer phrase). Flagged the risk directly; **bumped to 3s** (Joseph's call). Retested against the worst case — the longest phrase (`event.gathering_room_motion`, "Motion at Gathering Room") followed by another camera — and confirmed via the actual trigger/finish timestamps (not just speaker buffering timestamps, which include variable cloud-TTS dispatch lag and were initially misleading): Gathering Room's audio genuinely finished at `01:39:43.479`, Front Door's TTS call landed at `01:39:43.581`, 0.1s after — no overlap. Residual risk not fully eliminated (a slow-dispatch + long-phrase worst case could theoretically still exceed 3s), but every real test so far has been clean; a true "wait for actual playback to finish" design was offered and not chosen in favor of this simpler fixed-delay tradeoff.

**Entry-cluster suppression added, 2026-08-15** — Front Porch, Front Door, and Doorbell are physically clustered at the same entry point; a single visitor walking up commonly trips two or three of them for what should be one announcement, not three. Added `entry_cluster` (those 3 entity_ids) and `entry_cluster_suppressed` variables plus a second template condition: if a trigger is one of the 3 cluster entities and another cluster member changed state within the last 30 seconds (Joseph's chosen window), this run is suppressed — first one wins. Evaluated at trigger time (before queuing), not at whenever the run would eventually be dequeued. Only applies to this 3-camera cluster; the other 6 cameras are unaffected and still each get their own independent announcement.

**Verified live, 2026-08-15 01:44 MST** — simulated the full walk-up sequence: Front Porch, Front Door, Doorbell, 2s apart each. Checked `garage_speaker`'s playback history across the whole window: exactly **one** `buffering → playing → idle` cycle (Front Porch, the first of the three) — Front Door and Doorbell were both correctly suppressed, no second or third announcement.

**Real gap found, 2026-08-15: initially thought Patio/Path-specific, actually universal.** Joseph observed the physical blue "motion detected" light activate on Patio and Path in real life, but no announcement played. Checked `event.patio_motion`/`event.path_motion` directly — both stuck at `state: unknown` since the `ring` integration first loaded (2026-08-14T21:37:13), never recording a real event. Initially assumed Patio/Path-specific (Ring app motion zone/sensitivity/snooze) — **then Joseph reported the same gap (real Ring push notifications + video on his phone, no voice announcement) for Gate, Front Porch, Front Door, and Doorbell too**, the same four cameras just verified working via simulation. Checked all four `event.*_motion` entities directly: every one was still frozen at the timestamp of my own last simulated test write (`context.user_id` matching my own token), meaning **no real event had reached any of them since**, despite genuine concurrent Ring activity.

**Root cause confirmed: the native `ring` integration's live-event platform (`event.*_motion`) had stopped delivering events entirely** — not a per-camera Ring-app setting. Cross-checked against `sensor.*_last_activity` (a separately-polled entity from the same integration) for the same cameras — all showed fresh, correct real-world timestamps matching Joseph's phone notifications in real time (Front Porch `01:53:17`, Gate `01:52:55`, Doorbell `01:53:28`, Gathering Room `01:53:12`, Patio `01:46:22`, Path `01:46:11`). The one earlier "confirmed live" doorbell trigger (01:14:57, recorded above) may have been the last live event to get through before this broke.

**Fix, 2026-08-15: switched the trigger source from `event.*_motion` to `sensor.*_last_activity`** for all 9 cameras — same debounce/queue/entry-cluster suppression logic, just retargeted to the entity domain confirmed still working. `camera_names` and `entry_cluster` variables updated to match. Deployed and reloaded, confirmed `state: on`.

**Real regression found immediately after, 2026-08-15: false "Motion at Gathering Room" announcement.** Joseph reported hearing it despite that camera's `switch.gathering_room_motion_detection` being confirmed `off`. Root cause: `sensor.*_last_activity` reflects ANY camera activity, not just motion — its `category` attribute was `on_demand_link` (a live-view access), not `motion`. Confirmed real motion events do carry `category: motion` by checking several other cameras' current values. **Fix: added a leading condition, `trigger.to_state.attributes.category == 'motion'`**, filtering out non-motion activity categories. Deployed and reloaded. Verified live with two direct tests on `sensor.gate_last_activity`: a synthetic `on_demand_link` write left `last_triggered` unchanged (correctly blocked), a synthetic `motion` write correctly fired (`last_triggered` updated, `current: 1`).

**Second real regression found, 2026-08-15: same "no voice message" complaint returned for gate/porch/door/doorbell, plus a genuine one arrived "more than a minute" late.** Investigated: `sensor.front_porch_last_activity`'s own event timestamp was `02:07:49`, but its HA `last_changed` (and the automation's matching `last_triggered`) was `02:09:19` — a 90-second lag. Confirmed this is a **polling** artifact, not a one-off: `sensor.doorbell_last_activity` updated within 11ms of `sensor.front_porch_last_activity` at that same moment, consistent with a shared poll cycle refreshing several cameras at once rather than live per-event push. Also found `sensor.front_door_last_activity` stuck on a stale `2026-08-11` value entirely. **`sensor.*_last_activity` trades the `event.*_motion` outage for a ~60-90+ second delay — worse than the problem it was working around.**

**Reverted back to `event.*_motion`, 2026-08-15** (Joseph's call) — working theory is a transient Ring/HA cloud-side relay issue that may clear on its own; revisit if `event.*_motion` is still frozen after 2026-08-16. Trigger list, `camera_names`, and `entry_cluster` all reverted to the `event.*_motion` domain; the `category` filter condition was removed (not applicable — `event.*_motion` entities are motion-only by construction, no non-motion contamination possible the way `sensor.*_last_activity` had). Deployed and reloaded, confirmed `state: on`. All debounce/queue/entry-cluster logic is unchanged throughout both switches.

**Gathering Room camera removed from the trigger list, 2026-08-15** (Joseph's call) — `event.gathering_room_motion` dropped from both the trigger's `entity_id` list and `camera_names`, same pattern as the earlier Garage removal. 7 cameras remain: Gate, Path, Patio, Backyard, View Fence, Front Door, Front Porch, Doorbell. Deployed and reloaded.

**Backyard, View Fence, and Patio removed, 2026-08-15** (Joseph's call) — same pattern, all three dropped from the trigger's `entity_id` list and `camera_names`. 5 cameras remain: Gate, Path, Front Door, Front Porch, Doorbell. Deployed and reloaded.

**Done when:** the Patio/Path real-event gap above is investigated (Ring app settings) and `patio_speaker` and/or the two other offline Master Bedroom entities (`master_bedroom_speaker_2`, `master_bedroom_tv`) come back online and get reconsidered for the target list. Everything else — trigger, queuing/spacing, message content, TTS delivery — is now confirmed working end-to-end against a real event and multiple simulated ones.

**Closed out, 2026-08-18 17:14 MST, via CARD-0184.** The Patio/Path gap was never a Ring-app-settings issue — it was the same `event.*_motion` freeze CARD-0184 diagnosed and fixed (switched trigger to `sensor.*_last_activity`). `sensor.path_last_activity` confirms Path's own motion detection was always working (`category: motion` recorded 2026-08-15, before the freeze); Patio itself was already dropped from the trigger list that same day, so moot either way. Speaker recheck: `patio_speaker` and `master_bedroom_speaker_2` still `unavailable`; `master_bedroom_tv` is now `idle`/available (new) but **Joseph's call, 2026-08-18: leave the target list as-is** (`garage_speaker`, `groom_speaker`, `master_bedroom_speaker`) rather than add it.

**Related:** CARD-0146 (companion card — Ring doorbell live video on the Gathering room TV, same Ring/HA/Google Home integration surface; its "zero camera entities" finding needs a re-check now that the native `ring` integration is confirmed live), `ENVIRONMENT.md` (stale — camera list needs updating to the real 10-device inventory found here).

---

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 23472B, over the 10000B size threshold.

### CARD-0146 · [idea] [outdoor-presence-detection] Show Ring doorbell live video on Gathering room TV
**Status:** Defer (deactivated 2026-08-21 — see CARD-0187)

**Raised 2026-08-07 14:18 MST.** When the Ring doorbell detects activity, automatically show its live video feed on the Gathering room TV (the Chromecast/Google TV, per `ENVIRONMENT.md`), interrupting whatever is currently playing. Feed stays up for as long as there's motion/activity at the door, then automatically returns to whatever was playing before.

**Interview notes (2026-08-07):**
- Scope: doorbell only (not the other 6 Ring cameras) — live video, not a static snapshot.
- Trigger: automatic interrupt, not on-demand/voice-command-only.
- Return-to-previous-content condition: tied to the doorbell's own motion/person-detected state clearing, not a fixed timer.

**Open technical question resolved, 2026-08-14 (researched, then checked live against this HA instance):**
- **Google Home's native camera-to-Chromecast casting does not support Ring** — confirmed dead end. Longstanding Amazon/Google rivalry limitation: Ring integrates well with Alexa/Echo Show, but Google Home has never supported viewing Ring video, including current 2026 behavior. Not worth further investigation.
- **Home Assistant is the viable path.** HA ships an official `ring` integration providing `camera.live_view`/`camera.last_recording` entities and a `camera.play_stream` action built for exactly this pattern — HA's own docs use "doorbell event → play stream on a media player" as the canonical example.
- **Real gap found by checking this HA instance directly (`/api/states`): zero `camera.*` entities exist right now.** JCTsh's Ring devices are integrated via SmartThings only (per `ENVIRONMENT.md`), and that bridge exposes motion/presence/battery for Ring (`binary_sensor.front_doorbell_motion`, `event.front_doorbell_doorbell`, `binary_sensor.gathering_room_cam_motion`, all confirmed live) but never video. **This card requires adding HA's native `ring` integration (direct Ring cloud account auth) alongside the existing SmartThings bridge** — new infrastructure, not a toggle in an existing integration. Known real-world friction to expect: Ring's cloud API needs periodic re-auth/2FA handling, and some users report Cast-protocol/stream-format mismatches — worth an early Build-phase smoke test before wiring the full automation.
- **Target entity confirmed, already exists, already automated:** `media_player.groom_tv` ("GRoom TV Chromecast") — confirmed via HA's area registry to be in the "GRoom" (Gathering Room) area, the same entity the Traveling Mode TV automation already manipulates. No new discovery needed for the cast target.

**Plan, written 2026-08-14 (not yet built):**
1. **Add HA's native `ring` integration** (Settings → Devices & Services → Add Integration → Ring), authenticating with the same Ring account already tied to the physical devices (not a new account) — expect a 2FA prompt during setup. Credential handling: no separate password needed beyond the Ring account login itself; note in `credentials.local.md` that HA now holds a direct Ring session alongside the existing SmartThings bridge, since a future SmartThings credential rotation won't affect this new integration and vice versa.
2. **Confirm the real camera entity ID** once the integration is live — don't assume a name (e.g. `camera.front_door_live_view`); read it from `/api/states` the same way the target `media_player.groom_tv` was confirmed above. Also check whether the integration adds its own motion/person `binary_sensor`/`event` entities for the doorbell, duplicating `binary_sensor.front_doorbell_motion`/`event.front_doorbell_doorbell` from the SmartThings bridge — decide which source drives the automation (likely the native Ring entities, to stay in one integration's event timing rather than mixing two).
3. **Manual smoke test before building the automation**: call `camera.play_stream` by hand (Developer Tools → Actions) targeting `media_player.groom_tv` with the new camera entity, confirm live video actually renders on the physical TV — the research above flagged real-world reports of Cast-protocol/stream-format mismatches with Ring's feed, so this needs to be proven working in isolation before it's wired into an automation that also has to handle interrupt/restore logic.
4. **Build the automation**, informed by the real bugs already found building `media_player.groom_tv`'s other automation (Traveling Mode TV alert, CARD-0117-ish — see `automations.yaml`):
   - Trigger: the doorbell motion/person-detected entity chosen in step 2.
   - Action: capture `media_player.groom_tv`'s current state/source (template variable, same pattern as needed for accurate restore) → `camera.play_stream` with the Ring camera entity as target.
   - Reversion: second trigger on the same entity's activity clearing → restore the captured prior state. Use `mode: restart` from the start (not `mode: single`) — CARD-117-ish's own history found `single` silently drops a rapid re-trigger (e.g. a second doorbell ring while the feed is already showing), exactly the failure mode to avoid here.
   - Open judgment call for Build time, not decided here: whether to add a max-timeout safety net in case the motion/person entity gets stuck "on" (Cast-integration connectivity blips have caused stuck/false states elsewhere in this repo) — interview notes say tied to state-clearing not a fixed timer, but a safety-net upper bound may still be worth it. Confirm with Joseph before adding one, since it changes the stated acceptance criteria.
5. **Real live test, not just config validation** — actually trigger the doorbell for real, confirm the TV interrupts with live video and reverts correctly, and specifically test the rapid-re-ring case given the `mode: restart` lesson above.

**Steps 1-2 done, 2026-08-14:** native `ring` integration connected (Joseph, via HA UI with his existing Ring account + 2FA). Confirmed via `/api/states`: camera entity is `camera.doorbell_live_view` ("Doorbell Live view") — distinct from `camera.front_door_live_view`, a separate physical camera. The integration also created its own `event.doorbell_ding` (press) and `event.doorbell_motion` (motion), separate from the old SmartThings-sourced `binary_sensor.front_doorbell_motion`/`event.front_doorbell_doorbell` — using the native Ring entities for the automation trigger per the plan's stated preference (stay within one integration's event timing).

**Step 3 (smoke test) found a hard blocker, 2026-08-14 — both paths through HA's official `ring` integration are dead ends, not just risky:**
1. `camera.play_stream` targeting `media_player.groom_tv` with `camera.doorbell_live_view` **failed outright**: `camera.doorbell_live_view does not support play stream service`. Read the actual installed source (`homeassistant/components/ring/camera.py`) directly — it has no `stream_source()` method at all. Live view is implemented via **WebRTC** signaling (`async_handle_async_webrtc_offer`), not the RTSP/HLS pathway `camera.play_stream` requires. This is architectural, not a config problem — confirmed by reading HA core's own `_async_stream_endpoint_url`, which raises exactly this error whenever `camera.async_create_stream()` returns nothing.
2. Tried the community-known fallback instead: `media_player.play_media` pointed at the camera's `camera_proxy_stream` endpoint. The call succeeded (HTTP 200) and did put something on the physical TV — but Joseph confirmed live: **it showed a recording from the previous day, not a live feed.** Matches the entity's own attributes (`video_url` pointing at a downloaded MP4 of the *last recorded event*, `last_video_id`) — this proxy endpoint surfaces cached/recorded content, not real-time video, for this entity. Stopped the playback immediately once confirmed (`media_player.media_stop`) rather than leaving a random old clip on the TV.

**Net finding: HA's official `ring` integration cannot deliver genuine live view to a Chromecast/TV via any standard HA mechanism.** Ring's real live view is a WebRTC point-to-point session (what the Ring app and HA's own dashboard camera card use) — not something exposable through `stream_source()` or a static proxy URL.

**Third path researched in detail, 2026-08-14 (checked against the project's own docs/wiki, not just search summaries):** `tsightler/ring-mqtt` — actively maintained (2,671+ commits, 780 stars), bridges Ring's cloud API to MQTT plus an RTSP gateway for video.
- **Two new pieces, not one.** It exposes plain RTSP URLs (`rtsp://<ip>/<camera_id>_live`), not an HA camera entity by itself — needs HA's **Generic Camera** integration layered on top pointed at that URL to get a real `camera.*` entity with actual `stream_source()` support (Generic Camera does support `camera.play_stream`; the official `ring` integration doesn't — that's the whole point of this path).
- **Deployment scope**: its own Docker container (naturally alongside NetAlertX/Immich on the M8), its own bind-mounted config dir, its own MQTT account — comparable onboarding effort to NetAlertX itself, not a quick add-on.
- **Auth**: Ring account login with full 2FA support; Docker's install path uses a CLI-based auth flow specifically (different from the HA add-on's web-based one). Whether it needs periodic re-auth isn't documented — treat as unknown, test early.
- **Streaming behavior, more precise than initially found**: on-demand, not a background feed — starts automatically when a client connects, ends ~5-10s after the last client disconnects. Ring's hardware/cloud is designed for short interactive viewing (~10 min), and continuous/long streaming risks battery drain and overheating — the project's own docs call this out specifically for **battery-powered cameras**. Directly relevant here: the doorbell reports a battery percentage (`sensor.doorbell_battery`, currently 49%) — it's battery-powered, so this constraint is real, not hypothetical. Should be fine for a doorbell-visit-length interruption (well under 10 min); not designed for anything longer.
- No documented Chromecast-specific casting issues in the project's own docs (the earlier "community reports of reliability challenges" was from third-party forum threads, not the project's own documentation — worth an early smoke test rather than assuming either way).

**Fourth path checked and also ruled out, 2026-08-14:** Joseph noted SmartThings' own app shows live video for Ring cameras — checked whether HA's SmartThings bridge could expose that as a `camera.*` entity instead of the direct Ring integration. Confirmed live: queried `integration_entities("smartthings")` against this HA instance directly — zero camera/video-domain entities anywhere in it, only the same motion/battery/lock/switch set `ENVIRONMENT.md` already documented. Confirmed why, not just that: HA's SmartThings integration's new camera support (2026.2+) is tied to SmartThings' Matter 1.5 camera rollout, currently limited to a small set of new Matter-partner cameras (Aqara, Eve, Xthings) — Ring isn't Matter and isn't among them. SmartThings' own live view is a SmartThings-app-native capability, not something its HA bridge exposes.

**Decision needed before continuing — not made here:** pursue `ring-mqtt` as new infrastructure, or park this card (Backlog/Defer) given the added scope/uncertainty this discovery introduced.

**Interim clarification, 2026-08-18 (surfaced while closing CARD-0145):** Joseph observed a Ring video playing on the Gathering room TV and asked whether that meant live video was already working. Confirmed it was the already-documented `media_player.play_media`/`camera_proxy_stream` fallback from Step 3 above (cached/recorded content, not live) — no new mechanism, matches the existing "Net finding" that HA's official `ring` integration cannot deliver genuine live view to a Chromecast target via any standard mechanism (WebRTC-only, no `stream_source()`). A second possible path was floated (display HA's own dashboard, where the camera card does render real WebRTC, directly on the TV via some app/kiosk-browser on the Google TV hardware, rather than routing Ring's raw stream through native Chromecast casting) but not pursued.

**Decided, 2026-08-18 17:20 MST (Joseph): pursue `ring-mqtt`.** Moving to Build.

**Progress, 2026-08-18 17:23 MST — infrastructure staged, blocked on Joseph's interactive Ring login for the next step:**
- Dedicated Mosquitto account `ring-mqtt` created on the Pi broker, verified live (`mosquitto_pub` auth test succeeded). Recorded in `credentials.local.md`.
- `~/ring-mqtt/{config,docker-compose.yml}` created on the M8. Compose file: `tsightler/ring-mqtt:latest`, `./config:/data` bind mount, RTSP gateway port `8554:8554` published, `restart: unless-stopped` — matches the M8's existing Docker-app conventions (netalertx/hike-izer-web-app patterns).
- Confirmed via the project's own wiki (not assumed): RTSP stream URL format is `rtsp://<host>/<camera_id>_live` on port 8554; `config.json`'s `mqtt_url` field takes a full connection URL (`mqtt://user:pass@host:port`); `livestream_user`/`livestream_pass` are optional but recommended since this will be LAN-reachable — a password for that was generated, not yet applied (blocked on init, see below).

**Blocked on Joseph — the Ring account init step is interactive by design and needs his own login/2FA, not something to run on his behalf:**
```
cd ~/ring-mqtt
docker run -it --rm --mount type=bind,source="$(pwd)/config",target=/data \
  --entrypoint /app/ring-mqtt/init-ring-mqtt.js tsightler/ring-mqtt
```
Run on the M8 (SSH in first: `ssh jct@100.111.16.14`). Prompts for the Ring account email/password already tied to the physical devices (same account CARD-0145's native `ring` integration already uses) and a 2FA code. Generates `ring-state.json` (refresh token) and a default `config.json` in `~/ring-mqtt/config/`. Once that's done, next step is editing `config.json` to add the `ring-mqtt` MQTT account + livestream credentials above, then `docker compose up -d`.

**Not yet done:** the init step above, bringing the container up, confirming it actually creates a camera/RTSP stream for the doorbell, adding HA's Generic Camera integration pointed at the RTSP URL, the Step 3 smoke test (`camera.play_stream` against `media_player.groom_tv`, this time via Generic Camera's entity rather than the native `ring` integration's), and the automation build/live-test from the original plan above.

**Hard blocker solved — real live video confirmed on the TV, 2026-08-18 17:35 MST.** Joseph completed the interactive Ring login (`init-ring-mqtt.js`, prompted for the same account CARD-0145's native integration already uses, plus 2FA) — `ring-state.json`/`config.json` generated in `~/ring-mqtt/config/` on the M8. `config.json`'s `mqtt_url` set to the new `ring-mqtt` account (`mqtt://ring-mqtt:...@192.168.1.117:1883`) during the init prompt itself; `livestream_user`/`livestream_pass` added afterward (container writes `/data` as root, needed `sudo` to edit — file ownership restored to `jct` after). `docker compose up -d` — clean startup confirmed in logs: Ring API connected via the saved refresh token, MQTT connected, one location (`Marana`) discovered, 10 devices published via HA MQTT discovery including a `Live Stream`/`Event Stream` switch and an independent `_motion`/`_ding` pair per camera (separate from the native `ring` integration's own entities — a second, independently-maintained data path into Ring's API). `go2rtc` RTSP gateway confirmed listening on `:8554`.

Added HA's **Generic Camera** integration via its config-flow REST API (`POST /api/config/config_entries/flow`, handler `generic`) — no UI click-through needed. Pointed at `rtsp://192.168.1.165:8554/3ca30803f9b4_live` (`3ca30803f9b4` = the doorbell's ring-mqtt device ID, matches its MAC) with the `ring-mqtt` livestream credentials; validated cleanly (no `stream_source` error) and created `camera.192_168_1_165` (`state: loaded`). **Smoke test: `camera.play_stream` targeting `media_player.groom_tv` returned HTTP 200** (vs. the native integration's outright `does not support play stream service` failure) — HA transcoded the RTSP feed to HLS and cast it, `media_duration: -1` (live-stream indicator, not a fixed-length recording, confirming this isn't a repeat of the cached-recording dead end). **Joseph confirmed live at the TV: real live video, not a recording.** Stopped via `media_player.media_stop` once confirmed, per `ring-mqtt`'s own guidance against leaving streams open longer than needed.

**Automation built and live, 2026-08-18 18:21 MST** — `core/homeassistant/automations.yaml`, `CARD-0146 - Doorbell Live Video on Gathering Room TV` (id `1786800000002`). Triggers on `binary_sensor.doorbell_ding`/`binary_sensor.doorbell_motion` (ring-mqtt's own, per the reliability finding above) going `to: 'on'`; captures `media_player.groom_tv`'s prior `media_content_id`/`media_content_type`/state; calls `camera.play_stream`; waits for both sensors off; best-effort resumes the captured content via `media_player.play_media`, falling back to `media_player.media_stop` if nothing usable was captured (Joseph's call, 2026-08-18 — resume isn't guaranteed for session-based streaming apps, accepted known gap).

**Two real logic bugs found and fixed via live testing, 2026-08-18:**
1. **Empty `media_content_id` treated as resumable.** YouTube TV's Cast session reports `media_content_id` as an empty string, not null — the original `is not none` check passed on it, which would have called `play_media` with a blank ID. Fixed to also require non-empty content after trimming.
2. **Premature revert from independent-entity re-trigger.** Original design used `mode: restart` (matching the Traveling Mode TV automation's own lesson) and a `wait_for_trigger` on *either* sensor going off, reasoning a repeat ring wouldn't re-fire `to: "on"` since the entity would already be on. That missed that ding and motion are two independent entities with independent timers — motion firing after ding was already active caused `mode: restart` to cancel the run and re-capture "prior" state *while the live stream was already playing* (capturing the stream's own URL as "prior"), and the either-sensor-off wait let the run finish once whichever entity's window was shorter cleared, even while the other was still active. Fixed: `mode: single` (a redundant second trigger during an active interruption is correctly ignored, nothing is lost by ignoring it) and `wait_template` requiring both sensors off. Re-verified live after the fix — automation correctly waited for both to clear and correctly fell to the `media_stop` branch (YouTube TV, no resumable content).

**Video reliability: intermittent, not fully solved — 3 live tests, 1 clean success.** Test 1 (2026-08-18 17:35 MST, manual `camera.play_stream`): worked end-to-end, Joseph confirmed real live video on the TV. Tests 2 and 3 (via the automation, then a manual pre-warm-the-stream-switch-first retry): both failed the same way — video never rendered, TV stuck showing the stream-receiver app without playing content. Debug logging (`homeassistant.components.stream`/`generic`/`camera`) enabled temporarily to diagnose, reset back to `warning` afterward.

Root-caused as far as current access allows:
- Test 2's failure: HA's stream worker (FFmpeg) logged `Error opening stream (Invalid data found when processing input, rtsp://...)` ~5s after `Started stream`, retried every 10s per its own built-in retry logic, gave up after ~65s (`Stopped stream`).
- Test 3 (pre-warmed via `switch.doorbell_live_stream` before calling `play_stream`, to rule out a go2rtc cold-start race): the RTSP side ran clean this time, no "Invalid data" error — but still failed. HA gave up after 40s with no client ever successfully pulling the HLS output, then ~8s later logged `Failed to cast media ... from internal_url (http://192.168.1.117:8123)`.
- Traced that log line to HA's `cast/media_player.py` source directly: it fires when the Chromecast's own Cast-protocol status reports `player_is_idle` + `idle_reason: "ERROR"` — a generic "the receiver couldn't play this" signal from the device itself, not a diagnosed reachability failure (HA's message text is boilerplate covering common causes, not an actual diagnosis).
- Tested the HLS endpoint's reachability/correctness directly: fetching the live playlist URL from this machine returned HTTP 200 but garbled binary — turned out the response carries `Content-Encoding: gzip` even though the request didn't ask for it (no `Accept-Encoding` sent); decompressing manually gives a perfectly valid `#EXTM3U` playlist. The response is only 108 bytes, unusually small to trigger typical opportunistic compression middleware, suggesting this may be deliberate/unconditional behavior in HA's `stream` component's HLS serving rather than generic aiohttp compression. Real-world HLS serving guidance generally warns against gzip-compressing `.m3u8`/segment responses for exactly this class of compatibility reason with minimal embedded media clients (which is what a Chromecast's built-in "Default Media Receiver" is, not a full browser). **Leading hypothesis, not confirmed** — would need either a way to disable/test without this compression, or actual visibility into what the Chromecast's request/response looked like (packet capture), neither available in this session. A 2020 HA GitHub issue with the identical "Failed to cast media ... from internal_url" log line (home-assistant/core#41579) turned out to be a different cause (AVC codec profile too high for an old Home Hub speaker) — checked our own playlist's codec string (`avc1.640028,mp4a.40.2`, High Profile/Level 4.0) and it's a standard combination, not obviously the same issue, and Joseph's target is a full Google TV device, not a small speaker/display, so this doesn't look like a match.

**Decided, 2026-08-18 18:21 MST (Joseph): leave the automation live as-is.** It genuinely works when the relay chain cooperates (test 1), and the automation's own logic is now correct and verified. Accepting intermittent video reliability as a known, documented gap rather than disabling the feature — revisit with deeper access (packet capture, or a way to test with compression disabled) in a future session if it's worth chasing further.

**Remaining before this card can fully close:** the intermittent video-reliability gap above (gzip hypothesis unconfirmed) — otherwise the trigger source, automation logic, and resume/fallback behavior are all decided, built, and verified live.

**Unrelated but significant finding surfaced during this research:** Samsung is ending free SmartThings API access in October 2026 — affects the entire SmartThings bridge (100+ entities), not just Ring. Spun out to its own card: CARD-0164.

**Done when:** doorbell motion/person-detected reliably interrupts the Gathering room TV with live doorbell video, and playback automatically reverts to the prior content once the doorbell's activity state clears.

**Related:** CARD-0145 (companion card — audible Ring motion notification on Google Home), CARD-0164 (SmartThings API deadline, surfaced while researching this card), `ENVIRONMENT.md` (existing Ring camera + Chromecast/Google TV inventory).

---
