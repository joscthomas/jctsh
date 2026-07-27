# Traveling Lights — Component Context

HA-only component. No ESP32, no Node-RED. Simulates occupancy for a same-room
group of lights while Joseph is traveling, via a nightly randomized on/off time
with per-light staggering. See `jctsh/CLAUDE.md` for monorepo-wide conventions.

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
