# Garage Radar — End-to-End Validation (Step 9)

## Before you start

**Set timer to 2 minutes for testing** — do not run these tests at 20 minutes.

HA → Developer Tools → Actions → `input_number.set_value`:
- Entity: `input_number.garage_timer_duration`
- Value: `2`

Confirm via Developer Tools → States that `input_number.garage_timer_duration` = `2.0`.

**Restore to 20 minutes after all tests pass.**

---

## How to clear presence quickly

To simulate "nobody present" without waiting 30 seconds + timer:
- Step **behind or to the side** of the radar beyond the ±75° detection cone, OR
- Cover the LD2412 antenna face (blank side) with cardboard — presence clears
  immediately

After clearing, `binary_sensor.garage_radar_presence` goes `off` within ~30 seconds
(delayed_off filter). The timer then counts down from there.

---

## What to monitor

Keep **HA → Developer Tools → States** open, filtered to these entities:

| Entity | Watch for |
|---|---|
| `binary_sensor.garage_radar_presence` | on / off |
| `timer.garage_presence_timer` | active / idle, time remaining |
| `switch.garage_presence_vswitch` | on / off |

To monitor the SmartThings side: open the SmartThings app → Devices →
**Garage Presence Vswitch** and watch its state change in parallel.

---

## Test 1 — Still presence keeps timer alive

**Scenario:** someone sitting still at the workbench for an extended period.

> **This test uses a different timer value.** The keepalive fires every 10 minutes.
> The timer must be set longer than 10 minutes so you can observe the keepalive reset
> it before it expires. Set the timer to **11 minutes** for this test only.

**Setup:**
- HA → Developer Tools → Actions → `input_number.set_value` → value: `11`

**Steps:**
1. Stand or sit in front of the radar — confirm `garage_radar_presence` = `on`
2. Confirm `timer.garage_presence_timer` starts at 11 minutes and `garage_presence_vswitch` = `on`
3. Remain in the detection zone and watch the timer count down
4. At the next clock time divisible by 10 (:00, :10, :20, :30, :40, or :50) the keepalive
   fires — the timer resets back to 11 minutes
5. Confirm `garage_presence_vswitch` stays `on` throughout

**Pass:** timer resets at the 10-minute clock boundary; vswitch never turns off.

**After Test 1:** set timer back to `2` for Tests 2–4.

---

## Test 2 — Presence clears after leaving

**Scenario:** leave the garage, confirm everything turns off.

1. Confirm `garage_radar_presence` = `on` and timer is running
2. Step out of the detection zone (or cover antenna face)
3. Wait ~30 seconds — confirm `garage_radar_presence` goes `off`
4. Wait for timer to expire (2 minutes from when you stepped out, or 1 if set to 1)
5. Confirm `garage_presence_vswitch` turns `off`
6. Confirm SmartThings Garage Presence Vswitch shows off

**Pass:** vswitch turns off after timer expires with no one present.

---

## Test 3 — Second person enters while first is present

**Scenario:** someone enters the garage while presence is already active — lights
should not flicker or turn off.

1. Confirm `garage_radar_presence` = `on` and vswitch = `on`
2. Have a second person enter the garage (or simulate by walking in and out of view)
3. Confirm vswitch stays `on` throughout — no off→on toggle

**Pass:** vswitch remains on without any interruption.

---

## Test 4 — Keepalive stops when presence clears

**Scenario:** confirm the keepalive does not extend presence after someone leaves.

1. Confirm `garage_radar_presence` = `on` and timer is running
2. Step out of detection zone — wait for `garage_radar_presence` to go `off`
3. Wait for the timer to expire (do not re-enter the detection zone)
4. Confirm `garage_presence_vswitch` turns `off`
5. Confirm it does NOT turn back on at the next 10-minute mark

**Pass:** keepalive stops firing once radar is off; vswitch stays off.

---

## If a test fails

| Symptom | Check |
|---|---|
| Timer not starting | Automation trace: Settings → Automations → Garage Presence - Restart timer on activity → last triggered |
| Timer not resetting every 10 min | Automation trace: Garage Presence - Radar keepalive → last triggered |
| Vswitch not turning off | Automation trace: Garage Presence - Timer expired → last triggered |
| Vswitch off in SmartThings but not HA (or vice versa) | ST→HA sync lag — wait 30s and recheck both |
| `garage_radar_presence` not going off | Check `delayed_off: 30s` filter in `garage-radar.yaml`; confirm person is outside ±75° cone |

---

## After all tests pass

Restore timer duration:

HA → Developer Tools → Actions → `input_number.set_value`:
- Entity: `input_number.garage_timer_duration`
- Value: `20`

Confirm via States that `input_number.garage_timer_duration` = `20.0`.

---

## Next step

Proceed to Step 10 — final documentation (`README.md`).
