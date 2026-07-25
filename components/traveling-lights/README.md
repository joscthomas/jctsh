# Traveling Lights

HA-only component that simulates occupancy by turning a group of same-room lights
on and off at a randomized, staggered time each evening while Joseph is traveling.

**Status:** Production (CARD-0098)
**Hardware:** None — Home Assistant automations only

---

## What It Solves

While traveling, an empty house is more obvious if its lights never turn on. A
naive fixed-time timer is itself a tell (exact same clock time every night). This
component randomizes the on/off time nightly and staggers each light with its own
delay and shuffled order, so it reads as someone actually moving through the room
rather than a single master-switch flip.

---

## Entities Controlled

All in the same room (kitchen/dining area):

| Entity | Friendly Name |
|---|---|
| `light.nook` | Nook |
| `light.pendants` | Pendants |
| `light.chandelier` | Chandelier |

(`light.overhead_light` and `switch.kitchen_overhead` were part of the original
5-entity set but removed 2026-07-25 at Joseph's request — narrowed to just these 3.)

---

## HA Helpers

Both created via HA UI: Settings → Devices & Services → Helpers → + Create Helper → Time.

| Helper | Entity ID | Purpose |
|---|---|---|
| Traveling Lights On Time | `input_datetime.traveling_lights_on_time` | Tonight's randomized "on" time |
| Traveling Lights Off Time | `input_datetime.traveling_lights_off_time` | Tonight's randomized "off" time |

Not in `configuration.yaml` — created via UI only, same convention as every other
JCTsh input helper (see `garage-presence` for precedent).

---

## How It Works

1. **Traveling Lights - Randomize Daily Times** (always enabled) runs every night at
   3am and picks a new random on-time and off-time, writing them into the two
   helpers above:
   - **On-time** = actual sunset (`sun.sun`'s `next_setting`) + a random 0–35 min,
     so it tracks Tucson's real seasonal sunset swing (~5:25pm in December to
     ~7:35pm in June) instead of firing at a fixed clock time that would look
     wrong — still bright out in summer, already dark for an hour in winter.
   - **Off-time** = random time in a fixed 10:00–11:30pm window (bedtime doesn't
     shift with the seasons the way dusk does).
2. **Traveling Lights** (single automation, two triggers tagged `on`/`off`) fires
   at whichever time comes due. A `choose:` block runs the matching branch: it
   shuffles the 3 entities into a random order and turns them on (or off) one at
   a time with a random 1–5 minute gap between each, then sends a push
   notification (both Pixels) confirming which lights changed and when.

### How You'll Know It Ran While Traveling
Each run ends with a push notification to `notify.mobile_app_pixel_10_pro_xl` and
`notify.mobile_app_pixel_7_pro` — "Traveling Lights" with the time and which
entities were turned on/off. No notification within ~35 min of sunset for the on
side, or by 11:30pm for the off side, means something didn't fire — check
Settings → Automations → **Traveling Lights** → Traces for the run history, or
confirm the two `input_datetime` helpers still have valid values.

**Traveling Lights** ships **disabled by default** — this single toggle is the
standing on/off switch for "traveling mode," covering both directions.

### Turning It On/Off For a Trip
Settings → Automations & Scenes → search `traveling` → toggle **Traveling
Lights** on before leaving, off after returning. Leave **Traveling Lights -
Randomize Daily Times** enabled always — it's harmless when the other one is off.

**Note:** the automation's entity ID is `automation.traveling_lights_evening_on`
(a leftover from before the two directions were merged into one automation — HA
preserves entity IDs across a config reload rather than renaming them to match a
changed alias). Its display name is "Traveling Lights" and it now covers both
directions; the entity ID itself is cosmetic and can be renamed via Settings →
Entities if desired. A second, now-orphaned entity,
`automation.traveling_lights_night_off`, is left over from before the merge and
shows `unavailable` — safe to delete via Settings → Entities, or just ignore it.

---

## Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | Full automation YAML, design rationale |
| `../../core/homeassistant/automations.yaml` | Deployed automation source (this component has no automations of its own outside the shared HA config) |
