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

## Not Yet Live-Tested Against the v4 Trigger Swap

The v4 switch (2026-08-20) has been deployed and confirmed loaded via HA's
config API, but not yet live-tested against real motion on all 5 cameras (only
the doorbell was proven reliable pre-swap, during CARD-0146's own testing) —
tracked as an open item under CARD-0187.

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

## Current HA Automation (as of CARD-0187 Step 1, 2026-08-20 — CARD-0146's
own logic unchanged so far, only CARD-0145 was touched in that step)

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
