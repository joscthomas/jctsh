# Traveling

HA-only component (no ESP32, no Node-RED) covering two related automations that
both key off the same "we're away from home" toggle: simulating occupancy with
randomized lighting, and alerting if the Gathering Room TV turns on unexpectedly
while nobody should be home.

**Status:** Production (CARD-0098, CARD-0150)
**Hardware:** None — Home Assistant automations only
**Renamed from `traveling-lights` 2026-08-20** (CARD-0187 investigation surfaced
that "Traveling Mode - Unexpected TV Activity" had no documented home anywhere
outside `kanban-board.md`/`automations.yaml`'s own comments) — folded in here
since both sub-features already share the same gating toggle and traveling
concept, rather than getting a second, separate directory.

---

## Sub-Features

| Sub-feature | Automation(s) | What it does |
|---|---|---|
| **Traveling Lights** | `Traveling Lights - Randomize Daily Times`, `Traveling Lights` | Simulates occupancy — turns kitchen/dining lights on/off at a randomized, staggered time each evening |
| **Unexpected TV Activity** | `Traveling Mode - Unexpected TV Activity` | Alerts both ways if the Gathering Room TV's power state changes while traveling, since nobody should be home to use it |

Both are gated on the same toggle: **Traveling Lights** (the automation entity
itself, `automation.traveling_lights_evening_on`) is the single on/off switch
for "traveling mode" — enabling it both starts the presence-simulation lighting
*and* arms the unexpected-TV-activity alert. There is no separate toggle for
each sub-feature.

---

## Sub-Feature 1 — Traveling Lights

### What It Solves

While traveling, an empty house is more obvious if its lights never turn on. A
naive fixed-time timer is itself a tell (exact same clock time every night). This
component randomizes the on/off time nightly and staggers each light with its own
delay and shuffled order, so it reads as someone actually moving through the room
rather than a single master-switch flip.

### Entities Controlled

Both in the same room (kitchen/dining area):

| Entity | Friendly Name |
|---|---|
| `light.nook` | Nook |
| `light.pendants` | Pendants |

(`light.overhead_light`/`switch.kitchen_overhead` were part of the original
5-entity set, removed 2026-07-25; `light.chandelier` was in a later 3-entity
set, removed 2026-07-27 — see `CLAUDE.md` for the full history.)

### HA Helpers

Both created via HA UI: Settings → Devices & Services → Helpers → + Create Helper → Date and/or time.

| Helper | Entity ID | Purpose |
|---|---|---|
| Traveling Lights On Time | `input_datetime.traveling_lights_on_time` | Tonight's randomized "on" time |
| Traveling Lights Off Time | `input_datetime.traveling_lights_off_time` | Tonight's randomized "off" time |

Not in `configuration.yaml` — created via UI only, same convention as every other
JCTsh input helper (see `garage-presence` for precedent).

### How It Works

1. **Traveling Lights - Randomize Daily Times** (always enabled) runs every night at
   3am and picks a new random on-time and off-time, writing them into the two
   helpers above:
   - **On-time** = actual sunset (`sun.sun`'s `next_setting`) + a random 0–35 min,
     so it tracks Tucson's real seasonal sunset swing instead of firing at a fixed
     clock time that would look wrong in a different season.
   - **Off-time** = random time in a fixed 10:00–11:30pm window.
2. **Traveling Lights** (single automation, two triggers tagged `on`/`off`) fires
   at whichever time comes due, shuffles the entities into a random order, turns
   them on (or off) one at a time with a random 1–5 minute gap, then sends a push
   notification confirming which lights changed and when — the message also
   appends the Gathering Room TV's current Chromecast state as a passive check-in
   (added for CARD-0150, see Sub-Feature 2 below).

### How You'll Know It Ran While Traveling

Each run ends with a push notification to both Pixels — "Traveling Lights" with
the time, which entities changed, and the TV's current state. No notification
within ~35 min of sunset (on) or by 11:30pm (off) means something didn't fire —
check Settings → Automations → **Traveling Lights** → Traces, or confirm the two
`input_datetime` helpers still have valid values.

### Turning It On/Off For a Trip

Settings → Automations & Scenes → search `traveling` → toggle **Traveling
Lights** on before leaving, off after returning. This single toggle also arms/
disarms Sub-Feature 2 below. Leave **Traveling Lights - Randomize Daily Times**
enabled always — harmless when the other one is off.

**Note:** the automation's entity ID is `automation.traveling_lights_evening_on`
(a leftover from before the on/off directions were merged into one automation) —
cosmetic only, see `CLAUDE.md` for why.

---

## Sub-Feature 2 — Unexpected TV Activity

### What It Solves

Raised after the Gathering Room TV was found on when the family returned from a
17-day trip (2026-07-25 to 2026-08-11) with no findable cause — every source
checkable (HA automations, JCTsh/ESP32 logs, Google Home cast activity, TV
timers, SmartThings routines) came back clean, and HA's own history for the TV
entity had an unexplained 24-hour gap over the incident window. Root cause was
never conclusively found (see `CLAUDE.md` for the full investigation). Rather
than keep chasing an unfindable cause, this automation exists so a **repeat is
caught live** instead of reconstructed after the fact.

### How It Works

Keys off `media_player.groom_tv` (the physical Chromecast plugged into the TV
via HDMI) transitioning between an off-ish state (off/unavailable/unknown) and
an in-use state (playing/idle/paused/buffering) — gated on the same **Traveling
Lights** toggle above being on. Each direction (TV turning on unexpectedly, and
TV turning back off — the expected response after Joseph remotely powers it off
via Google Home) waits 2 minutes then re-checks the entity is still in the new
category before notifying, filtering out real Cast-integration connectivity
blips (confirmed live: a genuine ~67s dropout during active use would otherwise
have triggered a false alert). `mode: restart` so a rapid back-and-forth
collapses into one notification for the final settled state rather than losing
both — see `CLAUDE.md` for the two real bugs this took to get right.

### How You'll Know It's Working

Push notification to both Pixels — "Traveling Mode - TV Alert" — whenever the TV
turns on or off while the Traveling Lights toggle is armed. No dedicated
dashboard; check Settings → Automations → **Traveling Mode - Unexpected TV
Activity** → Traces for run history.

### Known Limitation

Notify-only — Joseph still has to manually turn the TV off via Google Home after
an alert. A follow-on idea (HA turning the TV off itself, or exposing it as its
own device rather than relying on the Chromecast as a power-state proxy) was
discussed but not pursued — see `CLAUDE.md`.

---

## Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | Full automation YAML for both sub-features, design rationale, full revision/bug history |
| `../../core/homeassistant/automations.yaml` | Deployed automation source (this component has no automations of its own outside the shared HA config) |
