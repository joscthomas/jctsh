# Garage Presence

HA-only component that tracks presence in the garage using a countdown timer, and
exposes the result to SmartThings to drive lights-off and door-close routines.

**Status:** Production
**Hardware:** None — Home Assistant automations only

---

## What It Solves

PIR and camera motion sensors are unreliable for extended garage presence — they can't
detect someone sitting still at a workbench, and Arizona summer heat causes PIR sensors
to stick `on`. A timer-based approach solves both problems: any garage activity resets a
countdown, and when the countdown expires without new activity, presence is declared over.
The presence signal is decoupled from what it triggers, so the garage door and lights are
controlled by SmartThings independently of this component.

---

## Architecture

```
SmartThings sensors (motion, door, camera)
  binary_sensor.garage_motion_motion
  binary_sensor.back_door_door
  binary_sensor.garage_cam_motion
  binary_sensor.garage_radar_presence  ← primary signal (garage-radar component)
          │
          ▼
  Home Assistant automations
  ├── Restart timer on activity
  ├── Radar keepalive (every 5 min while radar is on)
  ├── Sync timer to vswitch (HA restart recovery)
  └── Timer expired
          │
          ▼
  timer.garage_presence_timer (countdown)
          │ on expire
          ▼
  switch.garage_presence_vswitch
          │
          ▼
  SmartThings
  ├── Lights off
  └── Close garage door (automatic-garage-door-opener-closer component)
```

---

## HA Helpers

Both created via HA UI: Settings → Devices & Services → Helpers.

| Helper | Entity ID | Purpose |
|---|---|---|
| Garage Presence Timer | `timer.garage_presence_timer` | Countdown timer |
| Garage Timer Duration | `input_number.garage_timer_duration` | Duration in minutes (default 20) |

---

## How It Works

Any garage activity — motion, door state change, camera motion, or radar presence —
restarts the countdown timer. The timer duration is read from
`input_number.garage_timer_duration` at the moment each trigger fires. When the timer
expires without a new trigger, `switch.garage_presence_vswitch` is turned off, which
fires a SmartThings routine that turns off the garage lights and closes the door.

The **radar keepalive** automation fires every 5 minutes while
`binary_sensor.garage_radar_presence` is `on`, restarting the timer. This prevents
expiry during extended still presence at the workbench — the `off→on` trigger alone
would not re-fire if the radar stayed continuously on for longer than the timer duration.

### Adjusting the Timer Duration

Change `input_number.garage_timer_duration` in HA: Settings → Devices & Services →
Helpers. Takes effect on the next trigger. To affect a currently running timer: cancel
it first (Developer Tools → Actions → `timer.cancel`), then re-trigger a sensor.

### SmartThings Sensors

| Sensor | Entity ID | Notes |
|---|---|---|
| Garage motion | `binary_sensor.garage_motion_motion` | PIR — may stick `on` in Arizona summer heat |
| Back door | `binary_sensor.back_door_door` | SmartThings → HA sync can be slow |
| Garage camera | `binary_sensor.garage_cam_motion` | PIR — same heat caveat as motion sensor |
| Garage radar | `binary_sensor.garage_radar_presence` | Primary signal — mmWave, unaffected by heat |

---

## Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | Full automation YAML, HA entity details, architecture decisions |
