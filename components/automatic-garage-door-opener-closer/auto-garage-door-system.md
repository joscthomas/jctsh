# Auto Garage Door — System Architecture

**Status:** Production, working well. Documented 2026-09-12 to build shared understanding
before any future refactor — not a plan to change anything now. If/when SmartThings API
access goes away (CARD-0164), the pieces below are what a refactor would need to replace.

This system spans three component directories plus HA/SmartThings glue that lives in
neither: `garage-radar` (presence sensing), `garage-presence` (presence timer/logic),
and `automatic-garage-door-opener-closer` (the physical actuation + SmartThings routine).
No single file describes the whole thing today — that's the gap this document closes.

---

## The Goal

Auto-close the garage door when nobody has been in the garage for N minutes (currently a
configurable value, default 20 — see "The Timer" below), without closing on top of someone
who's still in there. A master on/off switch lets the whole capability be disabled. Closing
the door also turns off other garage devices left running — lights, a fan, a soldering
iron, etc. (the specific device list lives in SmartThings, not enumerated in this repo).

---

## Full Pipeline

```
LD2412 radar (garage-radar) ──MQTT/ESPHome discovery──▶ binary_sensor.garage_radar_presence
                                                                    │
Legacy sensors (motion/door/accel) ──ST sync──▶ binary_sensor.*    │  (see "Legacy Sensors" —
  (garage_motion_motion, back_door_door,                            │   effectively inert now)
   garage_cam_motion, back_door_acceleration)                       │
                                                                    ▼
                                    HA automation: "Garage Presence - Restart timer on activity"
                                                                    │
                                                          starts/restarts
                                                                    ▼
                                              timer.garage_presence_timer (HA, duration =
                                              input_number.garage_timer_duration, default 20 min)
                                                                    │
                                                    on start ──▶ switch.garage_presence_vswitch = ON
                                                    on expiry ──▶ switch.garage_presence_vswitch = OFF
                                                    (HA automation: "Garage Presence - Timer expired")
                                                                    │
                                                        synced to SmartThings
                                                        (HA → ST integration)
                                                                    ▼
Real ST-paired garage door position sensor ──▶ garage_door_open_vswitch (ON=open/OFF=closed)
  (also triggers a separate Google Home open/closed voice announcement — unrelated to auto-close)
                                                                    │
                                                                    ▼
                                            SmartThings Auto-Close Routine (lives in ST, not HA)
                     IF garage_door_auto_close_enable_vswitch = ON
                        AND (garage_door_open_vswitch = ON AND garage_presence_vswitch = OFF)
                     THEN garage_door_trigger_auto_open_close_vswitch = ON
                                                                    ▼
                                    (this vswitch turning on triggers the Zigbee relay —
                                     exact ST-internal hop to switch.open_close_garage_door
                                     not fully detailed; see note under Component 3)
                                                                    ▼
                                          Zigbee low-voltage switch relay closes momentarily
                                                                    ▼
                                          CreaCity remote PCB (button contacts bridged)
                                                                    ▼
                                          Security+ 2.0 RF signal → LiftMaster opener toggles
```

---

## Component 1: garage-radar (presence sensing)

- **Hardware:** HLK-LD2412 24GHz mmWave radar + ESP32, ESPHome firmware.
- **Path to HA:** plain MQTT with `discovery: true` — ESPHome publishes Home Assistant MQTT
  Discovery payloads directly, so `binary_sensor.garage_radar_presence` is created and
  updated in HA with **no Node-RED involvement at all**. Node-RED's own
  `garage-radar.flow.json` only handles this device's log/dashboard/watchdog traffic.
- **Smoothing:** a `delayed_off: 30s` filter keeps the entity `on` for 30s after the radar
  actually clears, absorbing brief detection gaps.
- **Why it exists:** replaced PIR-based motion sensors (heat detectors), which stuck `on`
  in Arizona summer heat and gave unreliable *ongoing*-presence signal. Radar solves
  continuous-presence detection reliably; the PIR sensors could not.
- **No direct SmartThings device** — deliberately. The radar's presence signal only ever
  reaches SmartThings indirectly, through the same `switch.garage_presence_vswitch`
  SmartThings already watches (see `garage-radar/integration-notes.md`'s own rationale for
  rejecting a direct SmartThings integration).

---

## Component 2: garage-presence (the timer / "how long is nobody there")

- **Entirely HA-side.** No Node-RED, no custom hardware of its own — it consumes signals
  from garage-radar (and the legacy sensors) and manages one HA `timer` helper.
- **The adjustable delay parameter you want (currently 20 min default) is
  `input_number.garage_timer_duration`** — already exactly the kind of changeable parameter
  described. Change it via Settings → Helpers, or Developer Tools → States (trust States
  over the Overview card if they disagree — the card can lag). Changing it takes effect on
  the *next* timer start, not a currently-running timer.
- **Core loop:** any qualifying activity restarts `timer.garage_presence_timer` and turns
  `switch.garage_presence_vswitch` **on**; timer expiry turns that switch **off**. This
  switch is the one SmartThings actually watches — garage-presence doesn't touch
  SmartThings directly at all (HA → SmartThings sync happens automatically via the existing
  integration, same as every other exposed entity).
- **A recovery automation** ("Sync timer to vswitch") re-starts the timer on HA restart if
  the vswitch is already on but the timer isn't running — covers the case where HA reboots
  mid-session.
- **A radar keepalive** re-fires every 5 minutes while radar still shows presence, so a
  single long, continuous stay doesn't let the timer expire just because the radar's own
  `to: "on"` trigger only fires once at the start of a visit.
- **A newer addition, found live in `automations.yaml` but not yet in this component's own
  CLAUDE.md** — the presence vswitch's state is now also mirrored to MQTT
  (`jctsh/components/garage-presence-vswitch/state`), presumably for dashboard visibility.
  Worth folding into `garage-presence/CLAUDE.md` at some point (not done as part of this doc).

### Legacy Sensors — real code, but effectively inert now

This is the most important piece of drift found while writing this up, confirmed directly
against the live `automations.yaml` (not the older, now-stale prose in
`garage-presence/CLAUDE.md` and `garage-radar/integration-notes.md`, which still describe
all sensors as equal peers):

The "Restart timer on activity" automation still lists `binary_sensor.garage_motion_motion`,
`binary_sensor.back_door_door`, `binary_sensor.garage_cam_motion`, and
`binary_sensor.back_door_acceleration` (a **fourth legacy trigger not documented anywhere
else in the repo**) as triggers — but a `condition: template` gate added since
`integration-notes.md` was written now blocks the automation's actions unless the trigger
was `binary_sensor.garage_radar_presence` itself, **or** the radar is `unavailable`/`unknown`:

```yaml
conditions:
  - condition: template
    value_template: >
      {{ trigger.entity_id == 'binary_sensor.garage_radar_presence'
         or is_state('binary_sensor.garage_radar_presence', 'unavailable')
         or is_state('binary_sensor.garage_radar_presence', 'unknown') }}
```

This is the actual mechanism behind "initially this worked with motion sensors... but they
are no longer used; garage-radar replaced them" — the old sensors were never removed as
triggers, they were **conditionally neutered**: they still fire the automation, but the
condition silently blocks the action unless radar is down, in which case they become a
genuine fallback. This is real, working, deliberate design (not a leftover bug) — but it's
undocumented anywhere until now.

---

## Component 3: automatic-garage-door-opener-closer (actuation + the ST routine)

- **No ESP32, no Node-RED, no HA automation of its own** — purely hardware + a SmartThings
  Routine.
- **The physical chain:** SmartThings/Google Home command → Zigbee low-voltage switch
  (relay closes momentarily) → CreaCity universal remote's PCB (button contacts bridged
  directly to the relay's output terminals) → standard Security+ 2.0 RF signal → LiftMaster
  opener. The LiftMaster is never modified and never knows this isn't a real remote button
  press.
- **Critical property: the command is a toggle, not an open/close command.** The Zigbee
  switch firing always just makes the LiftMaster reverse whatever it's currently doing —
  the same signal opens a closed door and closes an open one. This is *why* the system needs
  to track real door position at all — firing the relay at the wrong moment opens instead
  of closing.
- **Master enable:** `switch.garage_door_auto_close_enable_vswitch` — a precondition
  checked by the SmartThings Auto-Close Routine. Turn this off to disable auto-close
  entirely without touching anything else.
- **Door position — confirmed 2026-09-12, real hardware, not bookkeeping.** A real
  **Z-Wave** garage door position sensor — a mechanical slide/tilt switch (mercury-switch
  style, not a two-part magnetic reed sensor) — sets `switch.garage_door_open_vswitch` on
  when the door opens and off when it closes. This also independently triggers a Google Home
  open/closed voice announcement (a separate ST behavior, unrelated to the auto-close
  logic). **This corrects CARD-0260's original categorization** of this vswitch as "pure
  bookkeeping... could be tracked HA-natively instead" — it's driven by real hardware, so a
  future HA-native rebuild needs to account for that sensor directly, not just recreate a
  software flag.
- **The actual trigger chain, confirmed 2026-09-12:** the SmartThings Auto-Close Routine's
  logic is `IF garage_door_auto_close_enable_vswitch = ON AND (garage_door_open_vswitch =
  ON AND garage_presence_vswitch = OFF) THEN garage_door_trigger_auto_open_close_vswitch =
  ON` — a **fourth vswitch**, not previously documented anywhere in this repo, distinct from
  `switch.open_close_garage_door`. Turning this trigger vswitch on is what fires the Zigbee
  relay. Being an `IF...AND(...)` condition rather than a single-event trigger resolves the
  original concern about the everyday case (door already open, presence drops out later) —
  the condition is presumably re-evaluated whenever either `garage_door_open_vswitch` or
  `garage_presence_vswitch` changes, not only when the door first opens. The exact internal
  hop from this trigger vswitch to `switch.open_close_garage_door` firing the real relay
  (same automation's second action, vs. a second chained ST Routine) is still unconfirmed —
  minor detail, doesn't change the overall picture.
- **Voice control:** the Zigbee switch itself is exposed to Google Home via SmartThings,
  so "Hey Google, turn on the garage door opener" fires the same relay/toggle path directly,
  independent of the auto-close logic.

---

## Where SmartThings Fits (and why it's hard to see the whole picture in one place)

SmartThings is the layer that actually *owns* the Auto-Close Routine's if/then logic — the
one piece of this whole system that isn't in this repo at all, isn't version-controlled,
and can't be inspected from here. Everything upstream of it (radar, presence timer) is
real, readable HA/ESPHome code; the routine itself is SmartThings-app-only configuration.
This is the core reason the system is hard to reason about as a whole — the logic is
genuinely split across three different places (ESPHome/MQTT, HA automations.yaml, and a
SmartThings Routine you can only view in the SmartThings app), each with its own
documentation gaps found while writing this up.

---

## Open Questions — resolved 2026-09-12, one minor detail left

Four questions were open when this doc was first written; three are now fully resolved
(folded into the sections above) and the fourth confirms existing understanding:

1. ~~What sets `switch.garage_door_open_vswitch`?~~ **Resolved** — a real ST-paired door
   position sensor, not bookkeeping (see Component 3 above; corrects CARD-0260).
2. ~~Does the routine trigger on presence-off or only door-open?~~ **Resolved** — it's an
   `IF...AND(...)` condition over the enable/door/presence vswitches via a fourth
   intermediary trigger vswitch, not a single door-open edge trigger (see Component 3).
3. ~~What does "garage lights" cover?~~ **Resolved, broader than lights** — lights, a fan,
   a soldering iron, and potentially other garage devices (see "The Goal" above).
4. ~~Is the HA timer the only delay?~~ **Confirmed yes** — `input_number.garage_timer_duration`
   is the one adjustable "how long with no presence" parameter in the whole system.

**Last detail confirmed 2026-09-12:** `garage_door_trigger_auto_open_close_vswitch` turning
on causes SmartThings to send the signal directly to the Zigbee device, which throws the
relay as a momentary switch — one hop, no second chained Routine. The door-position sensor
itself is a mechanical slide/tilt switch (mercury-switch-style), not magnetic reed.

Every piece of this system is now fully documented — no open questions remain.

---

## For a Future Refactor (CARD-0164 / CARD-0260 context)

If SmartThings API access lapses and this system needs rebuilding HA-native, the real
migration work is narrower than "everything" — garage-radar and garage-presence are
already fully HA/ESPHome-native and unaffected either way. What actually needs solving:
- Replacing the SmartThings Auto-Close Routine's if/then logic with an HA automation.
- Replacing the real ST-paired door-position sensor's path into HA — confirmed real
  hardware (see Component 3), so this needs an actual HA-native sensor integration in a
  refactor, not just a re-created software flag.
- The genuinely real hardware dependency CARD-0260 already identified:
  `switch.open_close_garage_door` is a real Zigbee device physically paired to the
  SmartThings hub's own radio — HA can only keep controlling it post-API-cutoff if HA
  retains basic read/write access to real SmartThings-bridged entities (the open question
  CARD-0164's 2026-10-02 Auto-verify is specifically checking).

**Concrete replacement options for that Zigbee switch, researched 2026-09-12 —
DIY-ESPHome is the primary recommendation, not a commercial Matter device:**

- **Preferred: a self-built ESP32 relay, plain ESPHome-over-WiFi, no Matter at all.**
  Joseph has already bought a second CreaCity visor remote, taken it apart, and worked out
  the momentary-switch-trip wiring — the actual hard part is already solved, and it's
  physically identical to what the current Zigbee switch already does (bridge the button
  PCB contacts). This means the replacement is just a standard JCTsh ESPHome build (ESP32 +
  a cheap relay module + `switch:`/`output:` GPIO config, same shape as every other
  component here) — no LiftMaster-specific logic needed anywhere in the firmware, since the
  ESP32 only ever has to close the relay momentarily, exactly like the Zigbee switch does
  today. Per `JCTsh-Build-Standards.md` §6.4's own preference order, ESPHome's native HA API
  integration ("no intermediary platform at all") ranks *above* Matter — Matter's real value
  is multi-ecosystem interop for a device you didn't build, which doesn't apply to something
  you're building yourself for your own HA. Voice control, if wanted, uses the same
  HA-native-Google-Assistant-exposure pattern already built this session for the
  salt-sensor switches (CARD-0261) — no Matter Server, no commissioning flow, no new
  infrastructure.
- **Fallback if DIY isn't wanted: the SONOFF MINI-D** — a Matter-over-WiFi dry-contact relay
  module, explicitly marketed for garage doors/gates/low-voltage motor control, hub-free.
  ~$17-20 from SONOFF/ITEAD's official store (third-party listings run higher, ~$40 CAD
  equivalent in some places) — buy direct if going this route. Would still remove the
  Zigbee/SmartThings-hub dependency, just with more up-front commissioning overhead and a
  device you didn't build, for no real benefit over the DIY option given Joseph already has
  the hardware knowledge this project needs. (Aqara's Dual Relay Module T2 is a similar
  dry-contact product but requires an Aqara-specific hub — worse fit than either option
  above, trades one hub dependency for another rather than removing it.)

**Options for the real Z-Wave door-position sensor, researched 2026-09-12:**

- **Keep the existing sensor, move it off SmartThings onto a local Z-Wave USB coordinator**
  (per CARD-0264's decision criteria) — a plain Z-Wave stick (Zooz ZST10, Aeotec Z-Stick 7,
  ~$40-60) reads the sensor directly into HA via Z-Wave JS, no replacement hardware needed
  at all. Cheapest option, since the sensor itself is already correct for the job.
- **Z-Station (Z-Wave.me)** — a real combo USB adapter, Z-Wave plus a second radio
  firmware-selectable as Zigbee/Thread/BLE, appearing as two USB serial devices. ~€126
  (~$135-140) — notably pricier than a plain Z-Wave stick, and only worth it if Thread
  capability is also wanted on the same physical device; with 3 free USB ports on the Pi
  (per CARD-0264), there's no port-scarcity reason to pay the premium otherwise.
- **Replace the sensor with a Matter-native one** (only relevant if not keeping the
  existing Z-Wave hardware): generic two-part magnetic reed contact sensors are Matter-over-
  **Thread** (needs a Thread Border Router somewhere on the network — unconfirmed whether
  the SmartThings hub's own Thread radio would keep working for this after the API cutoff,
  since that's a local-mesh function distinct from cloud API access) — IKEA Myggbett (~$8,
  cheapest), Aqara P2 (~$24), Eve Door & Window (~$44 single/~$110 for 3). None of these
  match the door's actual tilt/slide mechanism, though a reed sensor can still be mounted to
  work on a garage door with correct alignment.
  **ThirdReality makes a purpose-built garage door tilt sensor** (the mechanically correct
  match) but it's not available as a clean standalone Matter accessory — only as Zigbee
  (needs a Zigbee hub) standalone, or bundled into ThirdReality's own Matter-over-WiFi
  "Smart Garage Door Opener" kit alongside opener hardware not needed here.
  **Given all this, keeping the existing Z-Wave sensor and just moving its host coordinator
  is the clear simplest option** — replacing genuinely-working, mechanically-correct
  hardware for protocol reasons alone isn't a strong trade.

---

## Implementation Plan / Lead Time (if/when this refactor is undertaken)

Not scheduled — sized 2026-09-12 to know what lead time to expect, per Joseph's request.

**Parts inventory check, 2026-09-12:** 7 spare ESP32 DevKitC-32 boards already on hand
(`jctsh-parts-inventory.md`, Bag 1); a generic relay module is likely already on hand too,
in the "Greekcreit Sensor Module Kit for Arduino" (37-module kit, Plastic Box) — a
logic-level relay is sufficient, since the CreaCity remote's button contacts are
low-voltage, not mains. The relay-switch half of this refactor may need **zero new
purchasing** to start building.

**Gating item — no cost, no action, just waiting:** CARD-0164's 2026-10-02 Auto-verify
finding (whether HA retains any read/write access to real SmartThings-bridged entities
post-cutoff). This determines *scope*, not just timeline — if favorable (the expected
outcome), the plan below holds as scoped. If unfavorable, the "other devices" shutoff
(lights/fan/soldering iron — real SmartThings hardware, out of scope for this refactor)
would *also* need migrating, an unsized scope since that device list isn't enumerated
anywhere yet.

**No-regret purchase — can do now, doesn't wait on Oct 2:** a Z-Wave USB coordinator (Zooz
ZST10 or Aeotec Z-Stick 7, ~$40-60, 1-3 day Amazon shipping) — the only real purchase
needed for the relay+sensor half of this refactor.

**Build work — parallelizable, doesn't wait on Oct 2 either:**
1. ESPHome relay firmware + bench test — likely one focused session; the hard part
   (momentary-switch wiring) is already solved, same pattern as garage-radar/salt-sensor.
2. Z-Wave JS UI Docker container + re-pairing the door sensor off the SmartThings hub onto
   it — same shape as CARD-0262's Matter Server setup, likely another focused session. Real
   unknown: Z-Wave's exclude/re-include mechanics haven't been exercised in this project
   before (Matter commissioning was just learned via CARD-0262; Z-Wave's process is
   conceptually similar — exclude, then include — but untested here).

**Gated on Oct 2's answer:**
3. New HA automations replacing the SmartThings Routine's if/then logic, migrating the
   enable vswitch to a Template Switch, live-testing against real events — comparable scope
   to CARD-0261's salt-sensor work. Likely *simpler* in one respect (no Node-RED involved in
   this system at all, so none of CARD-0261's Node-RED-specific surprises apply), but real
   HA-automation debugging could still surface its own surprises.

**Overall estimate, assuming Oct 2 comes back favorable:** roughly **1-2 weeks of calendar
time** from whenever work actually starts — dominated by focused-session availability, not
hardware lead time, given how cheap/fast/possibly-already-on-hand the parts are. If Oct 2
comes back unfavorable, timeline is open-ended until the lights/fan/soldering-iron device
list is inventoried and a migration plan exists for those too.

---

## Related

- `components/garage-radar/integration-notes.md`, `components/garage-radar/garage-radar.yaml`
- `components/garage-presence/CLAUDE.md`, `core/homeassistant/automations.yaml`
- `components/automatic-garage-door-opener-closer/CLAUDE.md`, `README.md`
- `tos/kanban-board.md` CARD-0260 (the SmartThings-migration decision card this supports),
  CARD-0164 (the SmartThings API deprecation decision)
