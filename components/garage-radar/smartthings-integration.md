# Garage Radar — SmartThings Integration (Step 4.5)

## Decision: no direct SmartThings device for the radar

The garage radar does not appear as a device in SmartThings. It integrates with
SmartThings indirectly through the existing garage presence automation in HA:

```
LD2412 → ESPHome → MQTT → HA (binary_sensor.garage_radar_presence)
    → triggers "Garage Presence - Restart timer on activity" automation
    → restarts timer.garage_presence_timer (20 min)
    → controls switch.garage_presence_vswitch
    → SmartThings sees garage presence on/off (existing vswitch)
```

SmartThings observes the outcome — garage presence active or not — through the
existing `switch.garage_presence_vswitch` it already knows about. The radar is
one of several inputs that feed that outcome. SmartThings does not need to know
which sensor triggered it.

## Why not a direct SmartThings device

- The HA SmartThings integration syncs SmartThings devices into HA — it does not
  push HA entities back to SmartThings as new devices. There is no "expose entities"
  feature in the standard integration.
- Calling the SmartThings REST API directly requires a SmartThings Personal Access
  Token, which this project does not use (see CLAUDE.md — SmartThings Integration).
- A virtual switch in SmartThings was rejected — the existing Garage Presence Vswitch
  already represents garage occupancy state. A second switch for the radar alone would
  be redundant.

## What this means in practice

The radar's numeric sensors (distances, energies) and binary presence state are visible
in HA — dashboard, Developer Tools → States, history graphs. SmartThings sees only
the garage presence outcome, which is the correct abstraction level for automations
on the SmartThings side.
