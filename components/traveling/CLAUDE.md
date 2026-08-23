# Traveling — Component Context

HA-only component. No ESP32, no Node-RED. Covers two sub-features gated on the
same "away from home" toggle: **Traveling Lights** (occupancy simulation via a
nightly randomized on/off time with per-light staggering) and **Unexpected TV
Activity** (CARD-0150, alerts if the Gathering Room TV turns on while nobody
should be home). See `jctsh/CLAUDE.md` for monorepo-wide conventions.

**Renamed from `traveling-lights` 2026-08-20 (CARD-0187).** Originally this
directory only covered the lights sub-feature; "Traveling Mode - Unexpected TV
Activity" (CARD-0150, built 2026-08-12) had no documented home anywhere outside
`kanban-board.md` and `automations.yaml`'s own inline `description:` comments.
Folded in here rather than given its own directory since both sub-features
already share the same `automation.traveling_lights_evening_on` gating toggle —
this is now a proper standing convention, see `JCTsh-Build-Standards.md` §7.1a.

---

# Sub-Feature 1 — Traveling Lights

## Origin — CARD-0098

Raised 2026-07-25, same session as CARD-0097 (Hike-izer timezone fix). Design went
through five rounds of critique before landing:

1. **First cut:** all 5 entities via a single `homeassistant.turn_on`/`turn_off`
   call at one randomized time per night (using two `input_datetime` helpers
   re-randomized daily). Rejected once Joseph pointed out all 5 lights are in the
   same room — firing them all simultaneously looks like a single master-switch
   flip, not occupancy, regardless of how random the clock time is.
2. **Staggering fix:** each entity gets its own random 1–5 min delay and the
   firing order is shuffled fresh every run (`| shuffle` Jinja filter +
   `repeat: for_each`), so lights come on/off gradually and in a different order
   each night.
3. **Remote visibility:** Joseph asked how he'd know the automation actually ran
   while away from home with no dashboard to check — same problem class as
   CARD-0036 (scheduled reboots) and front-porch-temp-sensor's threshold
   automations. Added a push notification (both Pixels, `notify.mobile_app_*`)
   at the end of each run's action sequence, stating the fire time and which
   lights were turned on/off.
4. **Sunset-relative on-time:** Joseph noted the household normally turns lights
   on before it gets fully dark, not at a fixed clock time — and Tucson's real
   sunset swings from ~5:25pm (Dec) to ~7:35pm (Jun), so a fixed 6:45–8:15pm
   window would look wrong for a large part of the year (dark house during
   actual dusk in winter, lights on while still bright in summer). Switched the
   on-time calculation to `sun.sun`'s `next_setting` attribute + a random 0–35
   min offset, computed fresh each night at the same 3am randomization step.
   Off-time stays a fixed 10:00–11:30pm window since bedtime doesn't track the
   seasons the way dusk does.
5. **Single toggle + entity trim:** after live-testing the two-automation design
   (Evening On / Night Off as separate automation entities), Joseph asked why
   two switches were needed instead of one, and separately asked to drop
   `light.overhead_light` and `switch.kitchen_overhead` from the controlled set
   (down to 3: nook, pendants, chandelier). Merged the two direction-specific
   automations into a single **Traveling Lights** automation with two named
   triggers (`id: 'on'` / `id: 'off'`) and a `choose:` block picking the branch —
   one entity, one toggle, covers both directions.
6. **Round 6 (2026-07-27):** after the round-5 merge got a full live on+off run
   (see Testing below), Joseph flagged the notification text showing raw entity
   IDs instead of readable names, asked to drop `light.chandelier` (down to 2:
   nook, pendants), and asked why the automation had reset to disabled overnight.
   Root cause was `initial_state: false` combined with the pre-existing weekly
   `scheduled-reboot.timer` (CARD-0036) restarting the Pi/Docker/HA container at
   3am — see the `initial_state` section below. Fixed all three.

## Why Two Helpers Instead of a Native Random Trigger

Home Assistant's `time` trigger requires an exact clock value (or an
`input_datetime` entity to read one from) — there's no built-in "random time"
trigger. The community-standard workaround is a small always-on automation that
recomputes a random target time into an `input_datetime` helper once daily, which
the actual action automation then triggers from. That's what
"Traveling Lights - Randomize Daily Times" does. (This part stayed a separate
automation even after the round-5 merge — it serves a different toggle state,
always-on regardless of whether a trip is active.)

## HA Helpers
| Helper | Entity ID | Purpose |
|---|---|---|
| Traveling Lights On Time | `input_datetime.traveling_lights_on_time` | Set nightly to sunset + random 0-35 min |
| Traveling Lights Off Time | `input_datetime.traveling_lights_off_time` | Set nightly to a random time in 22:00-23:30 |

Both created via HA UI (Settings → Devices & Services → Helpers → **Date and/or
time**, with **Has date** off / **Has time** on — the helper type is labeled "Date
and/or time" in this HA version, not a separate "Time" type). Not in
`configuration.yaml` — `configuration.yaml` is flagged do-not-modify in the root
`CLAUDE.md`, and there's no REST endpoint to create helpers programmatically, so
this is a one-time manual step for whoever stands the component up.

## Entities Controlled
Both in the same room (kitchen/dining) — this is *why* staggering matters here in a
way it might not for lights spread across different rooms:
- `light.nook`
- `light.pendants`

`light.overhead_light` and `switch.kitchen_overhead` were part of the original
5-entity design (see round 1 above) but removed 2026-07-25 at Joseph's request.
`light.chandelier` was part of the round-5 3-entity set but removed 2026-07-27
(round 6) at Joseph's request, after the 3-entity design got its full live
on+off verification (see Testing below). `homeassistant.turn_on`/`turn_off` (the
domain-agnostic service) is still used instead of `light.turn_on` even though
the remaining 2 are both `light.*`, in case a future addition brings back a
mixed-domain entity.

## HA Automations
All added directly to `core/homeassistant/automations.yaml` (raw YAML edit, not
built through the HA UI editor) and deployed via the standard `scp` + reload
pattern from the root `CLAUDE.md`.

**Traveling Lights - Randomize Daily Times** (`mode: single`, always enabled)
```yaml
alias: Traveling Lights - Randomize Daily Times
triggers:
  - trigger: time
    at: '03:00:00'
actions:
  - action: input_datetime.set_datetime
    target:
      entity_id: input_datetime.traveling_lights_on_time
    data:
      time: "{{ as_local(as_datetime(state_attr('sun.sun', 'next_setting')) + timedelta(minutes=range(0,36)|random)).strftime('%H:%M:%S') }}"
  - action: input_datetime.set_datetime
    target:
      entity_id: input_datetime.traveling_lights_off_time
    data:
      time: "{{ (today_at('22:00') + timedelta(minutes=range(0,91)|random)).strftime('%H:%M:%S') }}"
mode: single
```
`next_setting` is UTC (`as_datetime` parses it as an aware UTC datetime);
`as_local(...)` converts back to HA's configured timezone before formatting, so
the stored `HH:MM:SS` is genuinely local wall-clock time. At 3am the upcoming
`next_setting` is always today's sunset (today's hasn't happened yet), so this
doesn't need any "which day" guard the way a naive date-based calc would.

**Traveling Lights** (`mode: single`, toggle state persists across restarts —
see `initial_state` section below) — merged, single toggle
```yaml
alias: Traveling Lights
triggers:
  - trigger: time
    at: input_datetime.traveling_lights_on_time
    id: 'on'
  - trigger: time
    at: input_datetime.traveling_lights_off_time
    id: 'off'
actions:
  - variables:
      lights_order: "{{ ['light.nook', 'light.pendants'] | shuffle }}"
      lights_names: "{{ lights_order | map('state_attr', 'friendly_name') | join(', ') }}"
  - choose:
      - conditions:
          - condition: trigger
            id: 'on'
        sequence:
          - repeat:
              for_each: "{{ lights_order }}"
              sequence:
                - delay: "00:0{{ range(1,6) | random }}:00"
                - action: homeassistant.turn_on
                  target:
                    entity_id: "{{ repeat.item }}"
          - data:
              title: Traveling Lights
              message: "{{ now().strftime('%I:%M %p') }} — Turned on: {{ lights_names }}."
            action: notify.mobile_app_pixel_10_pro_xl
          - data:
              title: Traveling Lights
              message: "{{ now().strftime('%I:%M %p') }} — Turned on: {{ lights_names }}."
            action: notify.mobile_app_pixel_7_pro
      - conditions:
          - condition: trigger
            id: 'off'
        sequence:
          - repeat:
              for_each: "{{ lights_order }}"
              sequence:
                - delay: "00:0{{ range(1,6) | random }}:00"
                - action: homeassistant.turn_off
                  target:
                    entity_id: "{{ repeat.item }}"
          - data:
              title: Traveling Lights
              message: "{{ now().strftime('%I:%M %p') }} — Turned off: {{ lights_names }}."
            action: notify.mobile_app_pixel_10_pro_xl
          - data:
              title: Traveling Lights
              message: "{{ now().strftime('%I:%M %p') }} — Turned off: {{ lights_names }}."
            action: notify.mobile_app_pixel_7_pro
mode: single
```
`lights_order` (shuffled once per run, before the `choose:` branches) is shared
by whichever branch executes, so the same random order is used for both the
turn on/off sequence and the notification. `lights_names` maps that entity-ID
list to each entity's `friendly_name` (round 6 fix, 2026-07-27) — the
notification used to read raw IDs like "light.nook, light.pendants" instead of
"Nook, Pendants".

## Entity ID Is Stale — Cosmetic Only
This automation kept its config `id: '1785200000002'` across the round-5 merge
(previously "Traveling Lights - Evening On"). HA preserves entity IDs across a
`automation.reload` even when the alias changes substantially — it does **not**
re-slugify the entity ID to match a new alias. So the live entity ID is still
`automation.traveling_lights_evening_on`, even though its `friendly_name`
(from `alias:`) is now "Traveling Lights" and it covers both directions. Purely
cosmetic — rename via Settings → Entities if desired, no functional impact.

A second entity, `automation.traveling_lights_night_off` (the old id
`1785200000003`, removed from the YAML during the merge), is now an orphaned
`unavailable` entity in the registry. Harmless — delete via Settings → Entities
if it's confusing to see in the entity list, or leave it.

## initial_state — Removed 2026-07-27 (Round 6)
Originally documented (rounds 1-4) as: "`initial_state: false` only controls
enable state at HA startup with no prior registry entry; toggling via the UI
persists across `automation.reload`." That held for minor content-only reloads
(round 3's notification actions, round 4's sunset-relative calc), but turned out
to be **wrong in general** — it happened to hold in those cases only because no
full HA restart occurred between them.

**What actually happened, diagnosed 2026-07-27:** the automation was manually
enabled and live-tested the evening of 2026-07-26 (confirmed via HA logbook: on
branch fired 19:35 local, off branch fired 22:02 local, both staggering the 3
lights correctly). The next morning it was found disabled. Root cause: the Pi
runs a pre-existing weekly `scheduled-reboot.timer` (CARD-0036), which fired at
03:00 local on 2026-07-27 and restarted Docker — confirmed via `docker inspect
homeassistant` (`StartedAt` matched) and HA's own logbook showing "Home
Assistant stopped" / "started" 3 minutes apart at that time. Per HA's actual
documented behavior, `initial_state`, when present, forces that state on
**every** startup (not just first-ever load with no registry entry) — overriding
whatever the toggle was set to. The round-5 "reload resets toggle" finding above
was really the same mechanism showing up a different way, not a
reload-vs-restart distinction.

**Fix:** removed `initial_state: false` from the YAML entirely. Without that
key, HA restores the automation's last toggle state across any restart
(reload or full restart), so enabling it before a trip now survives the weekly
Monday 3am reboot instead of silently reverting.

## Testing
1. Create both `input_datetime` helpers (see above) before enabling anything.
2. Set `input_datetime.traveling_lights_on_time` a couple minutes in the future via
   Developer Tools → States → Set State (or `input_datetime.set_datetime`).
3. Enable **Traveling Lights**.
4. Confirm the entities turn on one at a time over the following ~1–10 minutes,
   in a different order than last time, followed by a push notification showing
   readable light names.
5. Repeat using `traveling_lights_off_time` to test the off branch.
6. Disable again after testing, until an actual trip. Fastest way to check what
   actually happened without watching the house live: HA's `/api/logbook`
   endpoint filtered to each light entity plus
   `automation.traveling_lights_evening_on` — shows exact fire times per light
   and which trigger (`on`/`off`) caused them.

**Live-tested 2026-07-25** (pre-merge, 5-entity design): manually triggered the
randomizer against real `sun.sun` data (actual sunset 19:27 local → computed
on-time 19:33, 6 min after sunset, correctly inside the 0-35 min window).
Set `traveling_lights_on_time` to a near-future value and enabled
Evening On — confirmed `light.overhead_light`, `light.pendants`, and
`light.chandelier` turned on with real staggering (different times, not
simultaneous).

**Live-verified end-to-end 2026-07-26/27** (post-merge, 3-entity design, before
the round-6 trim): via HA logbook — on branch triggered 19:35:22 local,
chandelier/pendants/nook fired at 19:38/19:41/19:42 (staggered, different
order than the pre-merge test); off branch triggered 22:02:00 local (inside the
fixed 22:00–23:30 window), same 3 lights turned off at 22:06/22:10/22:12.
Confirms the merged single-automation `choose:` structure works correctly for
both directions.

**Not yet re-verified after round 6** (chandelier dropped, friendly-name
notifications, `initial_state` removed) — re-enabled 2026-07-27 with today's
already-randomized on/off times (~19:58/22:14 local) so it will exercise the
new 2-entity/friendly-name design on its own tonight; check the logbook the
next day to confirm.

---

# Sub-Feature 2 — Unexpected TV Activity

## Origin — CARD-0150

Raised 2026-08-12 05:48 MST, from Joseph finding the Gathering Room TV on when
the family returned from the airport the night before (~2026-08-11 22:30 MST)
after a 17-day trip (July 25–Aug 11), with no known reason for it to have
turned on.

## Root-Cause Investigation — Inconclusive

Every source checkable was investigated and ruled out, not assumed clean:

- **`media_player.groom_tv`** (the physical Chromecast plugged into the TV via
  HDMI, exposed via HA's Google Cast integration — not SmartThings) is the
  actual entity. Arrival time independently confirmed via garage-radar presence
  events (22:27:49–22:33:53 MST), matching Joseph's recollection.
- **HA automations ruled out** — queried every `call_service` event HA logged
  the entire day; zero touched `media_player`/`cast`/`smartthings`/`scene`
  domains, and `automations.yaml` had no TV reference anywhere at the time.
- **No local power blip** — JCTsh component logs checked across the window, no
  reconnect/reboot events on any device.
- **Chromecast's own Activity/cast history** (checked directly in the Google
  Home app) shows nothing around the arrival window; no Google Home automations
  reference the TV at all.
- **No power outage during the full 17-day window** — every ESP32 component's
  heartbeat uptime counter checked across the entire trip, none show a reset.
  (The Pi itself rebooted once, 2026-08-10 03:00 MST, but no ESP32 rebooted
  alongside it — reads as a routine scheduled reboot, not a house-wide power
  event.)
- **No TV-native on-timer or SmartThings routine configured** (confirmed with
  Joseph), and no one else had house/TV access during the trip.
- **The one place that might have shown something — HA's own Cast history for
  the TV — has an unexplained ~24-hour recording gap** covering exactly the
  incident window (last row before the gap: `off` at Aug 11 03:06 MST; next row:
  Aug 12 03:23 MST). Initially misread as "confirmed off the whole time" — it's
  actually a genuine recorder blackout, inconclusive rather than exculpatory.

**Points toward** a TV-side or Chromecast-side spontaneous wake (Samsung
Anynet+/CEC glitches and Chromecast standby/update-check CEC signals are both
known, documented causes of unprompted TV power-on that leave no trace in
Google Home's activity log or HA) — plausible but not provable with the
telemetry available. **Joseph's call, 2026-08-12: pivot to detection/alerting
rather than keep chasing an unfindable root cause.**

## Design

New automation gated on the existing `automation.traveling_lights_evening_on`
toggle (Sub-Feature 1's own on/off switch) so it only fires while nobody's
expected home. Keys off `media_player.groom_tv`'s Cast-integration state
crossing between off/unavailable/unknown and an in-use state (playing/idle/
paused/buffering). Two directions, per Joseph's explicit ask: notify when the
TV turns **on** unexpectedly, and notify when it turns **off** again (the
expected response once Joseph turns it off remotely via Google Home) — so he
gets confirmation the remote power-off actually took, not just the initial
warning. The existing Traveling Lights on/off notifications also now append the
TV's current state to their message text, as a passive check-in independent of
this dedicated alert.

## HA Automation

Added directly to `core/homeassistant/automations.yaml`, deployed via the
standard `scp` + reload pattern from the root `CLAUDE.md`.

**Traveling Mode - Unexpected TV Activity** (`mode: restart` — see the
mode-history section below for why)
```yaml
alias: Traveling Mode - Unexpected TV Activity
triggers:
  - trigger: state
    entity_id: media_player.groom_tv
    from: ['off', unavailable, unknown]
    to: [playing, idle, paused, buffering]
    id: 'on'
  - trigger: state
    entity_id: media_player.groom_tv
    from: [playing, idle, paused, buffering]
    to: ['off', unavailable, unknown]
    id: 'off'
conditions:
  - condition: state
    entity_id: automation.traveling_lights_evening_on
    state: 'on'
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: 'on'
        sequence:
          - delay: 00:02:00
          - condition: state
            entity_id: media_player.groom_tv
            state: [playing, idle, paused, buffering]
          - data:
              title: Traveling Mode - TV Alert
              message: "{{ now().strftime('%I:%M %p') }} — Groom TV turned on (Chromecast status: {{ states('media_player.groom_tv') }}) while traveling."
            action: notify.mobile_app_pixel_10_pro_xl
          - data:
              title: Traveling Mode - TV Alert
              message: "{{ now().strftime('%I:%M %p') }} — Groom TV turned on (Chromecast status: {{ states('media_player.groom_tv') }}) while traveling."
            action: notify.mobile_app_pixel_7_pro
      - conditions:
          - condition: trigger
            id: 'off'
        sequence:
          - delay: 00:02:00
          - condition: state
            entity_id: media_player.groom_tv
            state: ['off', unavailable, unknown]
          - data:
              title: Traveling Mode - TV Alert
              message: "{{ now().strftime('%I:%M %p') }} — Groom TV turned off (Chromecast status: {{ states('media_player.groom_tv') }})."
            action: notify.mobile_app_pixel_10_pro_xl
          - data:
              title: Traveling Mode - TV Alert
              message: "{{ now().strftime('%I:%M %p') }} — Groom TV turned off (Chromecast status: {{ states('media_player.groom_tv') }})."
            action: notify.mobile_app_pixel_7_pro
mode: restart
```

**Why the 2-minute delay-then-recheck, not a plain `for:`.** HA's `for:`
requires the exact same state *value* to hold the whole time, but
`media_player.groom_tv` legitimately churns between playing/idle/paused/
buffering several times a second during real use — a same-value `for` would
rarely if ever be satisfied during genuine use, silently breaking the 'on'
alert. The delay-then-recheck-category pattern (fire on the transition, wait
2 minutes, confirm the entity is *still* in the new category before actually
notifying) tolerates that churn while still filtering out short-lived blips.

## Live Testing — Three Real Bugs Found, in Order

Every fix below was caught by Joseph's own live testing, not by config
validation alone, consistent with this project's verification standard
elsewhere. Five rounds total before a fully clean pass.

**1. Cast-integration connectivity blip → false alert (first live test,
2026-08-12 07:15 MST).** Turning the TV off/on both worked, but a 3rd,
unprompted notification arrived — "Groom TV turned off (unavailable)" — while
the TV was still on. Recorder DB showed `media_player.groom_tv` dropped from
`playing` straight to `unavailable` for ~67s (a genuine Cast-integration
connectivity blip during confirmed active use, not a real power change), which
would also have triggered a false follow-up "turned on" alert on recovery.
**Fix:** the 2-minute delay-then-recheck pattern above (first instinct was a
trigger-level `for: 00:02:00`, caught and rejected before deploying — see
"Why the 2-minute delay" above for why `for:` doesn't work here). Also relabeled
both notification messages to say `(Chromecast status: ...)` explicitly rather
than a bare state value, so it's clear this is the Chromecast's own reported
status, not a literal TV-power reading.

**2. `mode: single` silently drops a rapid re-trigger (second live test,
2026-08-12 07:35 MST).** TV went off then back on 14 seconds later — zero
notifications, both directions lost. Root cause: `mode: single` silently
*drops* a new trigger event while a run is already in progress rather than
queuing it, so the 'on' transition (14s after 'off' started its 2-minute delay)
was ignored entirely; and by the time the 'off' branch's own delayed recheck
ran, the TV was on again, so its own condition failed too. **Fix:**
`mode: single` → `mode: restart` — a newer trigger now cancels the in-flight
delay and restarts from the latest transition, so rapid back-and-forth
collapses into one notification for the final settled state instead of losing
both.

**3. False alarm traced to HA's own startup race, not a logic bug (third live
test, 2026-08-12 ~07:44 MST).** Off then on again, zero notifications — but the
automation's own Trace view showed "No traces found" (the trigger never matched
at all, not that it matched and failed downstream). Cross-referenced against
`docker logs`: the real state transitions landed while HA was still finishing
startup from the `mode: restart` deploy's container restart — Docker's
healthcheck only confirms the web server responds, not that every integration/
automation listener has finished wiring up. No code change needed; confirmed by
waiting for HA to be genuinely settled and re-testing clean.

**Fourth test (well-separated on/off) and fifth test (quick-toggle within the
2-minute window, the specific scenario `mode: restart` hadn't been re-verified
against since the fix) both passed clean**, the fifth confirmed against
sub-second recorder-DB timestamps rather than just the notification outcome —
TV went `playing`→`off`, then back to `idle` 4.68s later; under `mode: restart`
this correctly cancelled the in-flight 'off' countdown and started a fresh 'on'
one, which fired at its own 2-minute recheck since the TV was genuinely still
on-ish by then. The original 'off' branch's own recheck never ran, since it was
superseded — correctly explains why exactly one notification (not zero, not
two) is the right outcome for this case.

## Known Limitation — Notify-Only

Joseph still has to manually turn the TV off via Google Home after an "on"
alert — this automation only detects and notifies, it doesn't remediate. A side
question (expose the Samsung TV as its own HA device instead of relying on the
Chromecast as a power-state proxy, and/or have HA turn it off automatically) was
discussed but not pursued — the TV isn't currently registered in Joseph's
SmartThings account, so the low-effort exposure path isn't available; the only
route would be HA's separate native Samsung TV integration (added by IP,
one-time pairing prompt). Worth a future card if a more direct/authoritative
signal or auto-remediation is wanted later.

## Closed Out

2026-08-12 ~08:35 MST on Joseph's go-ahead. Reopens under a fresh card if a
repeat isn't caught live, or if the TV-as-its-own-device idea gets picked up.

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 18219B, over the 10000B size threshold.

### CARD-0150 · [bug] [traveling] Samsung TV was on when we got home — investigate and fix
**Status:** Done

**Raised 2026-08-12 05:48 MST**, from Joseph finding the Samsung TV on when he and family returned from the airport last night (~2026-08-11 22:30 MST) — no known reason for it to have turned on. Not yet confirmed whether the TV is even integrated into HA/SmartThings as a controllable/queryable entity; that's the first thing to check.

**Investigation starting point:** Joseph's own suspicion, unconfirmed — the HA light automation routine (whichever one runs around arrival/dusk) is "the only thing I can think of that was different" around that time. Worth checking `core/homeassistant/automations.yaml` for anything that could plausibly cross-trigger the TV (e.g. a scene, a SmartThings routine bundling lights+TV, an HDMI-CEC signal from another device the automation does control) — not assumed to be the actual cause, just the lead to start from. TV is also referred to as "Groom TV."

**Scope:**
1. Determine whether the TV is an HA/SmartThings entity at all; if so pull its on/off history around 2026-08-11 22:30 MST from HA logbook/history.
2. Identify what actually turned it on (an HA automation, a SmartThings routine, HDMI-CEC from another device, a TV-native schedule/feature, etc.).
3. Once root cause is confirmed, implement a fix so it doesn't happen again (exact fix depends on what's found — could be an automation condition, a SmartThings routine edit, disabling a TV-side feature, etc.).

**Investigated 2026-08-12 06:10 MST, real HA recorder DB + JCTsh component logs on the Pi, not guessed:**
- Entity is `media_player.groom_tv` — exposed via HA's **Google Cast integration**, not SmartThings. (`binary_sensor.samsung_tv_is_present`/`device_tracker.samsung_tv_is_home` are separate NetAlertX network-presence entities per CARD-0078, unrelated to control.)
- Arrival time independently confirmed via garage-radar presence events: 22:27:49–22:33:53 MST — matches Joseph's recollection.
- **HA automation is ruled out as the cause.** Queried every `call_service` event HA logged that entire day (midnight–6am next day): only Traveling Lights (`light.pendants`/`light.nook`, on 19:35 off 22:08 — Joseph's suspected lead), garage-presence switch, and Front Porch notifications ever ran. Zero service calls touched `media_player`, `cast`, `smartthings`, or `scene` domains all day, and `automations.yaml` has no TV reference anywhere. Traveling Lights only ever targets the two lights.
- No local power blip either — checked JCTsh component logs (`/mnt/jctsh-logs/jctsh.log`) across the same window for reconnect/reboot events on any device; none found.
- One red herring investigated and dismissed: the TV's network-presence sensor was continuously "home" from 03:36 MST Aug 11 through 22:35:56 (disconnecting ~5 min after arrival, consistent with Joseph powering it off) — but the same always-connected pattern with a ~30min blip near 3am repeats on other nights too, so it's normal WiFi-standby behavior, not a signal of when the display itself turned on.
- Confirmed with Joseph: no TV-native on-timer or SmartThings-app routine configured, and no one else had access to the house/TV during the trip (rules out a person).

**Trip window corrected 2026-08-12 06:25 MST — travel was July 25 to Aug 11, 17 days, not just one evening.** Re-scoped the investigation to the full trip rather than just the arrival hour:
- There **is** a physical Chromecast plugged into the TV via HDMI (Joseph confirmed) — `media_player.groom_tv` is that Chromecast's HA entity, not a TV-native integration. A Chromecast can wake a TV via HDMI-CEC and switch input the moment anything casts to it, independent of any Google Home smart-home linking or Routine.
- Checked directly in the Google Home app (Joseph): the Chromecast's own Activity/cast history shows **nothing** around the arrival window. Also confirmed no Google Home automations reference the TV at all.
- **No power outage during the full July 25–Aug 11 window.** Checked every ESP32 component's heartbeat uptime counter (which resets to a low value on any reboot) across the entire trip in `/mnt/jctsh-logs/jctsh.log`/`.log.1` — none show a reset; `garage-radar`, `salt-sensor`, `front-porch-temp-sensor` all have continuous uptime spanning well before July 25 through today. (The Pi itself did reboot once, 2026-08-10 03:00 MST via `journalctl --list-boots`, but since no ESP32 device rebooted alongside it, that reads as a routine/scheduled Pi reboot, not a house-wide power event — rules out the "power restored, TV defaults on" theory.)
- Confirmed with Joseph: TV was off when they left on July 25 (not a case of it simply never being turned off).

**Correction 2026-08-12 06:40 MST — the "no Cast activity all day" read above was wrong; it was a data gap, not evidence of nothing happening.** Pulled `media_player.groom_tv`'s *full* history (not just the incident window): it's normally very active — 800+ state records since Aug 3, cycling `playing`/`idle`/`paused`/`off` constantly on a typical day (confirmed real activity happening again as of this morning, Aug 12 08:57 onward). But for the incident window specifically, the last recorded row before the trip's end is `off` at **Aug 11 03:06 MST**, then **literally nothing** — no rows at all — until `unavailable`/`off` at **Aug 12 03:23 MST**, over 24 hours later. That's not "recorded off the whole time," it's a genuine recording blackout spanning the entire arrival window. HA's own history for this entity is therefore **inconclusive** for this incident, not exculpatory — it can neither confirm nor rule out when the TV actually turned on.

**Investigation is now inconclusive from every source checkable remotely** — HA automations (real event-log check, still solid), JCTsh/ESP32 logs, Google Home cast activity, TV-native timers, SmartThings routines, and other-person access have all been checked and ruled out, with no trigger event found in the 17-day window. HA's own Cast history for the TV, the one place that might have shown something, has an unexplained 24-hour gap covering exactly the relevant time. This points toward a TV-side or Chromecast-side spontaneous wake (both Samsung Anynet+/CEC glitches and Chromecast standby/update-check CEC signals are known, documented causes of unprompted TV power-on that leave no trace in Google Home's activity log or HA) — plausible but not provable with the telemetry available.

**Joseph's call 2026-08-12 06:50 MST: pivot to detection/alerting rather than keep chasing an unfindable root cause.** Re-scoped `Done when` accordingly (see below).

**Design, interviewed:** a new HA automation gated on the existing `automation.traveling_lights_evening_on` (the CARD-0098 Traveling Lights toggle Joseph already flips on/off around trips) so it only fires while nobody's expected home. Keys off `media_player.groom_tv`'s Cast-integration state crossing between off/unavailable/unknown and an in-use state (playing/idle/paused/buffering). Two directions, per Joseph's explicit follow-up ask: notify when the TV turns **on** unexpectedly, and notify when it turns **off** again (the expected response once Joseph turns it off remotely via Google Home after seeing the "on" alert) — so he gets confirmation the remote power-off actually took, not just the initial warning. Also, per Joseph's ask, the existing Traveling Lights on/off notifications (the routine ones already sent when the presence-simulation lights toggle) now append the TV's current state to their message text, as a passive check-in independent of the dedicated alert.

**Built and deployed 2026-08-12 07:05 MST:**
- New automation `Traveling Mode - Unexpected TV Activity` (`automation.traveling_mode_unexpected_tv_activity`) in `core/homeassistant/automations.yaml` — two triggers tagged `on`/`off` (mirroring Traveling Lights' own trigger-id/choose-block pattern), condition on the Traveling Lights toggle, push notifications to both phones (`mobile_app_pixel_10_pro_xl`, `mobile_app_pixel_7_pro`) for each direction.
- Existing `Traveling Lights` automation's four notify actions (on x2 phones, off x2 phones) extended to append `TV: {{ states('media_player.groom_tv') }}.` to the message text.
- YAML syntax-checked locally (`python -c "import yaml; yaml.safe_load(...)"`) before deploying, `scp`'d to `/home/pi/homeassistant/automations.yaml`, HA container restarted (no long-lived API token available in this session to use the lighter-weight `automation.reload` service, so a full `docker restart homeassistant` was used instead — same net effect for picking up config changes). Confirmed clean: container reports `healthy`, no config-load errors in `docker logs` (excluding known pre-existing unrelated noise — SmartThings light KeyError, Bluetooth scanner errors, a Chromecast connect failure for an unrelated speaker — none from this change), and the new automation shows up in the entity registry (`automation.traveling_mode_unexpected_tv_activity`, not disabled).

**Joseph's live test, 2026-08-12 07:15 MST — both directions confirmed working, and it immediately surfaced a real bug.** Turned the TV off: got "Groom TV turned off (off)." Turned it back on: got "Groom TV turned on (idle) while traveling." — mechanism validated end-to-end, the gap noted above (no API token for a synthetic test) is moot now that a real test happened. But a 3rd, unprompted notification arrived — "Groom TV turned off (unavailable)" — **while the TV was still on.** Pulled the exact state timeline from the recorder DB to confirm: `media_player.groom_tv` dropped from `playing` straight to `unavailable` at 09:47:46, then recovered to `idle`/`playing` by 09:48:54 — a genuine ~67s Cast-integration connectivity blip during confirmed active use, not a real power change. That recovery would also have matched the 'on' trigger's criteria, so a false follow-up "turned on" alert was likely imminent too — the entity is noisier than the design accounted for.

**Fix, interviewed and built 2026-08-12 07:20 MST:** two changes, both per Joseph's direction —
1. Both notification messages now label the parenthetical explicitly as `(Chromecast status: ...)` rather than a bare state value, so it's clear this is the Chromecast's own reported status, not a literal TV-power reading.
2. **Debounce redesigned, not just added.** First instinct was a trigger-level `for: 00:02:00`, but that was caught and rejected before deploying: HA's `for` requires the *exact same state value* to hold the whole time, and this entity legitimately churns between playing/idle/paused/buffering several times a second during real use — a same-value `for` would rarely if ever be satisfied during genuine use, silently breaking the 'on' alert. Replaced with a delay-then-recheck-category pattern instead: each branch fires immediately on the category transition, waits 2 minutes, then re-checks the entity is *still* in the new category (off-ish or on-ish, any value within it) before actually notifying. This tolerates the normal churn while still filtering the observed blip (the 09:47:46 `unavailable` had recovered to `idle` well within the 2-minute window, so a repeat of that exact scenario would now correctly send nothing).

**Deployed and verified clean 2026-08-12 07:25 MST:** YAML syntax-checked locally, `scp`'d, HA container restarted (`docker restart homeassistant` — no long-lived API token available in this session for the lighter `automation.reload`), confirmed `healthy` with no config-load errors and the automation still registered/enabled (`automation.traveling_mode_unexpected_tv_activity`).

**Joseph's second live test, 2026-08-12 07:35 MST — off then back on, "just like last time" — produced zero notifications, exposing a second real bug.** Pulled the exact timeline again: TV went `playing` → `off` at 10:01:46 (starting the 'off' branch's 2-minute delay), then bounced back to `idle` just 14 seconds later at 10:02:00. Two compounding failures under `mode: single`: (1) the 'on' transition at 10:02:00 fired while the 'off' branch's delay was still in progress — `single` mode silently *drops* a new trigger event while already running, it does not queue it, so the 'on' notification never had a chance; (2) the 'off' branch's own delayed recheck (due ~10:03:46) found the TV back on by then, so its condition failed too — no 'off' notification either. Both directions lost, matching exactly what Joseph reported.

**Fix, 2026-08-12 07:40 MST:** changed the automation's `mode: single` → `mode: restart`. A newer trigger now cancels the in-flight delay and restarts from the latest transition, so rapid back-and-forth collapses into one notification reflecting the final settled state instead of both getting silently lost. Deployed the same way as the prior fixes (YAML syntax-checked, `scp`'d, `docker restart homeassistant`, confirmed `healthy`/no config errors/automation still registered).

**Joseph's third live test, 2026-08-12 ~07:44 MST — off then on, zero notifications again, but a different cause this time.** Checked the automation's Trace view directly (Settings > Automations > Traveling Mode - Unexpected TV Activity > Traces) on Joseph's own request path — "No traces found," meaning the trigger never matched at all, not that it matched and failed downstream. Cross-referenced against `docker logs`: the real state transitions (10:05:58, 10:06:26) landed while HA was still finishing its own startup from the `mode: restart` deploy's container restart — a burst of unrelated SmartThings light entity-setup errors (`KeyError: Capability.SWITCH`, pre-existing issue with some SmartThings lights, unrelated to this card) and recorder DB session-recovery warnings were still running as late as 10:06:27, a full minute-plus after Docker's healthcheck had already reported "healthy." Docker's healthcheck only confirms the web server responds, not that every integration/automation listener has finished wiring up — so the real test landed in a startup race, not a logic bug. No code change needed; confirmed by waiting for HA to be genuinely settled (13+ min uptime, no further restarts) and re-testing.

**Fourth live test, 2026-08-12 ~07:52-07:54 MST — clean pass, both directions.** TV on at 10:21:42 → "on" notification received. TV off at 10:24:17 → "off" notification received. HA fully settled (no restart since 10:05:20), no startup contention this time. This is the first fully clean end-to-end pass since the mode:restart fix.

**Side question from Joseph, same session: should the Samsung TV also be exposed as its own HA device** (rather than relying on the Chromecast as a power-state proxy)? Discussed, not pursued as part of this card — Joseph confirmed the TV is not currently registered in his SmartThings account, so the low-effort "enable exposure on the existing SmartThings integration" path (same pattern as the salt-sensor switches) isn't available; the only route would be HA's separate native Samsung TV integration (added by IP, one-time pairing prompt on the TV). Worth a future card if Joseph wants a more direct/authoritative signal than the Chromecast's Cast-session state, or wants HA to be able to actually turn the TV off itself on an alert rather than just notifying — not needed for this card's own done-when, which the Chromecast proxy now satisfies.

**Fifth live test, 2026-08-12 ~08:31 MST — the quick-toggle case specifically, the one scenario mode:restart hadn't actually been re-verified against yet** (the earlier quick-bounce test that surfaced the mode:single bug predates the restart fix; every test since then was a well-separated on/off). Pulled the exact sub-second timeline from the recorder DB rather than trusting the outcome alone: TV went `playing`→`off` at **10:31:04.852**, starting the 'off' branch's 2-minute countdown, then back to `idle` just **4.68 seconds later** at **10:31:09.531** — under `mode: restart`, this cancelled the in-flight 'off' countdown and started a fresh one for 'on'. State stayed on-ish continuously after that; at the 'on' branch's recheck (~10:33:09) it was still on, so the "on" notification fired — exactly what Joseph received. The original 'off' branch's own recheck (due ~10:33:04) never ran, since it was superseded 4.7s after starting — correctly explains zero 'off' notification. Mechanism confirmed by data, not just a correct-looking result.

**Done when:** a real on/off cycle (both a normal, well-separated toggle and a quick back-and-forth within 2 minutes) produces the correct notification(s) with no drops and no false alerts. **Met** — both the well-separated case (fourth test) and the quick-toggle case (fifth test, above) now confirmed against real sub-second data, on top of the earlier confirmed handling of the connectivity-blip false positive.

**Closed out 2026-08-12 ~08:35 MST on Joseph's go-ahead.** Original root cause was never conclusively found despite exhausting every source checkable (HA automations, JCTsh/ESP32 logs, HA recorder history, Google Home cast activity, TV-native timers, SmartThings routines, other-person access) across the full July 25–Aug 11 trip window — Joseph's call to pivot from root-cause elimination to detection/alerting rather than keep chasing it. The resulting `Traveling Mode - Unexpected TV Activity` automation went through five rounds of real live testing and three real bugs found/fixed along the way (a Cast-integration connectivity-blip false positive, a `mode: single` dropped-notification bug, and one false alarm traced to HA's own startup race rather than the automation) — each one caught by Joseph's own testing, not by config validation alone, consistent with this project's verification standard elsewhere. Reopens under a fresh card if a repeat isn't caught live, or if the TV-as-its-own-device idea (noted above) gets picked up later.

**Related:** CARD-0078 (NetAlertX network-presence entities referenced during investigation), CARD-0098 (Traveling Lights, the toggle this card's alert automation is gated on), `core/homeassistant/automations.yaml`.

---
