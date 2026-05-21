# Garage Radar — Sensor Validation (Step 4)

## Prerequisites

- ESP32 flashed and connected (WiFi + MQTT confirmed)
- All 8 entities visible in HA under the garage-radar device
- HA Developer Tools → States accessible

---

## Test 1 — Baseline (no presence)

With nobody in front of the radar:

| Entity | Expected |
|---|---|
| Presence | `off` |
| Moving Target | `off` |
| Still Target | `off` |
| Moving Distance | 0 or unavailable |
| Still Distance | 0 or unavailable |
| Moving Energy | low or 0 |
| Still Energy | low or 0 |
| Detection Distance | 0 or unavailable |

If Presence is stuck `on` with no one present, the radar may be detecting a wall or
object. Reposition or angle the sensor slightly.

---

## Test 2 — Moving presence

Walk in front of the radar at a distance of roughly 1–3 meters:

| Entity | Expected |
|---|---|
| Presence | `on` |
| Moving Target | `on` |
| Still Target | `off` (may flicker) |
| Moving Distance | updates in cm as you move |
| Moving Energy | > 0 |

---

## Test 3 — Still presence

Stand or sit still in front of the radar for 5–10 seconds:

| Entity | Expected |
|---|---|
| Presence | `on` |
| Moving Target | `off` (may take a few seconds) |
| Still Target | `on` |
| Still Distance | stable cm reading |
| Still Energy | > 0 |

The LD2412 uses both motion and micro-motion (breathing, small movements) for still
detection. Standing completely rigid may reduce still energy — normal slight movement
is enough.

---

## Test 4 — Delayed off (30-second holdoff)

Walk in front of the radar, confirm Presence is `on`, then leave the detection zone:

- Presence should remain `on` for approximately 30 seconds after you leave
- After 30 seconds, Presence should go `off`

This confirms the `delayed_off: 30s` filter is working. If Presence drops immediately
when you leave, check the filter in `garage-radar.yaml`.

---

## Test 5 — Detection range

Walk toward the radar from outside the room and note the distance (Moving Distance)
at which Presence first goes `on`. Walk back and note where it drops off (after the
30s holdoff). Adjust the radar's physical angle or position if the range is too short
or too wide for the garage.

> The LD2412 has a detection range of up to ~9 meters in moving mode and ~6 meters in
> still mode. In a typical garage, 4–6 meters is a reasonable working range.

---

## Watching values in real time

**Option A — HA Developer Tools:**
Developer Tools → States → filter by `garage_radar` → watch values update live.

**Option B — MQTT:**
From the Pi or any machine with mosquitto_sub:
```
mosquitto_sub -h 192.168.1.117 -u jctsh-log-server -P <password-from-log-server.env> \
  -t "jctsh/components/garage-radar/#" -v
```

---

## Pass criteria

All 5 tests pass when:
- [ ] Baseline shows no presence with empty detection zone
- [ ] Moving presence detected within 1–3 meters
- [ ] Still presence detected after stopping
- [ ] 30-second holdoff confirmed on departure
- [ ] Detection range appropriate for garage installation point

---

## Next Step

If all tests pass, proceed to `perfboard-layout.md` (Step 5) to plan the permanent
soldered build. If repositioning is needed, adjust now before soldering.
