# Garage Radar — HA Integration (Step 8)

## What this does

Adds `binary_sensor.garage_radar_presence` as a new trigger in the existing
"Garage Presence - Restart timer on activity" automation. The radar becomes an
additive presence input — nothing existing is removed or modified.

---

## Verify the radar entity before editing

In HA → Developer Tools → States, confirm this entity exists and is reporting:

```
binary_sensor.garage_radar_presence
```

State should be `on` when someone is in the detection zone, `off` otherwise (with
~30 second holdoff on the falling edge).

If the entity is not found, check:
- ESP32 is powered and connected (MQTT Connected in ESPHome log)
- HA MQTT integration is connected to `192.168.1.117` port `1883`
- Device appears at Settings → Devices & Services → MQTT → garage-radar

---

## Edit the automation

HA → Settings → Automations & Scenes → **Garage Presence - Restart timer on activity**
→ three-dot menu → **Edit in YAML**

Add this trigger block to the `triggers:` list:

```yaml
  - entity_id: binary_sensor.garage_radar_presence
    to: "on"
    trigger: state
```

### Full automation after the edit

```yaml
alias: Garage Presence - Restart timer on activity
triggers:
  - entity_id: binary_sensor.garage_motion_motion
    to: "on"
    trigger: state
  - entity_id: binary_sensor.back_door_door
    trigger: state
  - entity_id: binary_sensor.garage_cam_motion
    to: "on"
    trigger: state
  - entity_id: binary_sensor.garage_radar_presence
    to: "on"
    trigger: state
actions:
  - target:
      entity_id: timer.garage_presence_timer
    data:
      duration: "{{ (states('input_number.garage_timer_duration') | int) * 60 }}"
    action: timer.start
  - action: switch.turn_on
    target:
      entity_id: switch.garage_presence_vswitch
mode: restart
```

Click **Save**.

---

## Verify

1. Set `input_number.garage_timer_duration` to `1` (1 minute) for quick testing
2. Move in front of the radar — confirm `binary_sensor.garage_radar_presence` goes `on`
3. Check the automation trace: Settings → Automations → Garage Presence - Restart timer
   on activity → last triggered should update
4. Confirm `timer.garage_presence_timer` starts counting down
5. Confirm `switch.garage_presence_vswitch` turns `on`
6. Step out of the detection zone — wait ~30 seconds for `garage_radar_presence` to
   go `off`, then wait 1 minute for the timer to expire
7. Confirm `switch.garage_presence_vswitch` turns `off`

Restore `input_number.garage_timer_duration` to `20` after testing.

---

## Next step

Proceed to `end-to-end-test.md` (Step 9).
