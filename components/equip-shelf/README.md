# Equipment Shelf

Physical shelf housing the home's core networking and automation infrastructure hardware.

**Status:** Production
**Hardware:** No microcontroller, no firmware — a physical mounting/organization location plus 3D-printed cooling-fan brackets.

---

## What It Houses

| Item | Role |
|---|---|
| Raspberry Pi (`pi1`) | Runs Mosquitto, Node-RED, the Python log server, Home Assistant (Docker) — see root `CLAUDE.md` |
| M8 | Docker host for hike-izer-orchestrator, NetAlertX, Immich, photo-server, and other containerized apps |
| Samsung SmartThings hub | SmartThings integration bridge (see root `CLAUDE.md`'s SmartThings Integration section) |
| Garage door relay switch / opener hardware | See `components/automatic-garage-door-opener-closer/` |
| Router | Home network (JCTnet1) |
| Router power reset device | Remote power-cycle capability for the router |
| Cooling fan(s) | Active cooling for the shelf's equipment — see Cooling below |

This directory documents the shelf itself and its cooling hardware; each hosted device/service has its own component directory or root-level doc for its actual function.

---

## Cooling

Two fan-bracket designs live in this directory's STL files:

| File | Notes |
|---|---|
| `fan_bracket_ACInfinity_S7.stl` | Original bracket, for an AC Infinity S7 fan |
| `Fan bracket.stl` | Newer bracket design, added 2026-09-16 |

No further build documentation exists yet for these — added here as a real, if minimal, home for a component that previously had STL files in the repo with no README at all.

---

## Related

`automatic-garage-door-opener-closer` (the garage relay hardware hosted here), root `CLAUDE.md` (Pi/M8 infrastructure and services), `jctsh-network.md` (network topology).
