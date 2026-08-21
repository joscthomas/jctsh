# Outdoor Presence Detection

HA-only component (no ESP32, no Node-RED) covering two automations built on top
of the existing Ring camera hardware: a spoken Google Home announcement when
motion fires on any of 5 outdoor cameras, and live doorbell video automatically
cast to the Gathering Room TV.

**Status:** Production, actively being consolidated (CARD-0187)
**Hardware:** None — the Ring devices themselves (doorbell + cameras) are
existing hardware, not part of this build; this component is the HA-side
automation logic on top of them.
**Created 2026-08-20** (CARD-0187) — these automations (CARD-0145, CARD-0146)
existed since 2026-08-07/08-14 with no documented home anywhere outside
`kanban-board.md`'s card history and `automations.yaml`'s own inline comments.
See `JCTsh-Build-Standards.md` §7.1a — every automation app now gets a
component directory, this is one of the two that motivated writing that rule
down.

---

## Sub-Features

| Sub-feature | Automation | What it does |
|---|---|---|
| **Ring Motion Announcement** | `CARD-0145 - Ring Motion Announcement` | Spoken TTS announcement on 3 Google Home speakers when motion fires on any of 5 cameras (gate, path, front door, front porch, doorbell) |
| **Doorbell Live Video** | `CARD-0146 - Doorbell Live Video on Gathering Room TV` | Interrupts the Gathering Room TV with the doorbell's real live video feed whenever it rings or detects motion, reverting once activity clears |

Both currently trigger off **ring-mqtt** — a third-party Docker container
(`tsightler/ring-mqtt`) running on the M8, a separate, independently-maintained
connection to Ring's cloud API from HA's own native `ring` integration. This
matters: two different Ring data pipelines exist in this house, and it's easy
to get them confused (see "Two Ring Pipelines" below).

**Not yet built:** coordination between the two sub-features for the doorbell
specifically (skip the voice announcement when video successfully shows), a fix
for a premature video-stream termination, and an investigation into a real gap
where a motion event was never seen by either Ring pipeline at all — see
`kanban-board.md` CARD-0187 for the active plan.

---

## Two Ring Pipelines — Don't Confuse Them

| | Native `ring` integration | `ring-mqtt` |
|---|---|---|
| What it is | HA's official built-in integration | Third-party Docker container on the M8 |
| Entities | `sensor.*_last_activity` (polled ~60s), `event.*_motion`/`_ding` (push, **durably broken since 2026-08-15**, CARD-0184) | `binary_sensor.*_motion`/`*_ding` (MQTT push, near-instant) |
| Used by | Nothing currently (both automations moved off it) | Both sub-features |
| Also provides | — | RTSP video gateway (go2rtc) that CARD-0146's live video depends on |

The native integration's push-based `event.*` entities have been confirmed
durably dead (matches upstream bug home-assistant/core#128597) — its
poll-based `sensor.*_last_activity` was used as a fallback for CARD-0145 from
2026-08-18 to 2026-08-20, but real field data showed real-world delays as bad
as ~3 minutes, well past its own documented ~30-90s estimate. As of CARD-0187
(2026-08-20), both automations are on ring-mqtt exclusively.

---

## Sub-Feature 1 — Ring Motion Announcement

### Cameras Covered

Gate, Path, Front Door, Front Porch, Doorbell — narrowed down from an original
9 (Garage, Gathering Room, Backyard, View Fence, and Patio were all removed by
Joseph's own call after live use, see `CLAUDE.md` for why each was dropped).

### Behavior

- **Trigger:** `binary_sensor.*_motion` going `on` (ring-mqtt, near-instant).
- **Debounce/spacing:** first announcement plays immediately, `mode: queued`
  (max 20) so only one announcement plays system-wide at a time, a 3-second
  trailing delay between queued announcements.
- **Entry-cluster suppression:** Front Porch, Front Door, and Doorbell are
  physically clustered at the same entry point — if two or three fire within
  30 seconds of each other, only the first announces (avoids 3 back-to-back
  phrases for one visitor walking up).
- **Targets:** `garage_speaker`, `groom_speaker`, `master_bedroom_speaker`
  (narrowed from an original 5 — Patio and a second Master Bedroom speaker were
  dropped for being offline; the Pixel Tablet was dropped after live testing,
  Joseph's call).

### How You'll Know It's Working

A spoken "Motion at \<camera\>" plays on the 3 target speakers. Check Settings →
Automations → **CARD-0145 - Ring Motion Announcement** → Traces for run history.

---

## Sub-Feature 2 — Doorbell Live Video

### Behavior

- **Trigger:** `binary_sensor.doorbell_ding`/`binary_sensor.doorbell_motion`
  going `on` (ring-mqtt).
- **Action:** `camera.play_stream` against `camera.192_168_1_165` (HA's Generic
  Camera integration, pointed at ring-mqtt's go2rtc RTSP gateway) targeting
  `media_player.groom_tv` — interrupts whatever was playing.
- **Revert:** captures the TV's prior state/content before switching; once both
  doorbell sensors clear (`wait_template`, 4-minute timeout), attempts to
  resume the prior content, falling back to a plain stop if nothing usable was
  captured. Best-effort, not guaranteed — session-based streaming apps
  (YouTube TV, etc.) don't reliably resume from a captured content ID, an
  accepted known gap.

### Why Not HA's Native `ring` Integration for Video

Tried first and confirmed a dead end: `camera.play_stream` against the native
integration's own camera entity fails outright (WebRTC-only, no
`stream_source()`), and the community-known fallback
(`media_player.play_media` against `camera_proxy_stream`) only serves a cached
recording, not live video. `ring-mqtt`'s RTSP gateway + HA's Generic Camera
integration is what actually delivers genuine live video — see `CLAUDE.md` for
the full investigation.

### How You'll Know It's Working

The Gathering Room TV switches to live doorbell video within a few seconds of
a ring/motion event, reverting once the visit ends.

### Known Issue — Premature Stream Termination

A real field event (2026-08-20) showed the live stream dying on its own after
only ~93 seconds — well under Ring's live-view session limits — before the
automation's own revert logic had a chance to run cleanly. Root cause not yet
diagnosed; tracked under CARD-0187.

---

## Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | Full automation YAML for both sub-features, design rationale, full investigation/revision history |
| `../../core/homeassistant/automations.yaml` | Deployed automation source (this component has no automations of its own outside the shared HA config) |

**Related kanban cards:** CARD-0145, CARD-0146, CARD-0184, CARD-0185
(superseded), CARD-0187 (active consolidation plan).
