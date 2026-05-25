# Front Porch Temp Sensor — HA Integration (Steps 6–10)

All Home Assistant configuration for this component. Follow sections in order.

---

## Step 6 — Verify HA Device Discovery

ESPHome MQTT discovery registers the device automatically on first MQTT connect.

Confirm in HA:
- Settings → Devices & Services → MQTT → front-porch-temp-sensor
- Entities present: Temperature, Pressure, Illuminance (Humidity shows Unknown — expected with BMP280 substitution)

No manual HA configuration needed for discovery.

---

## Step 7 — Create Input Number Helpers

Create two helpers in HA UI: Settings → Devices & Services → Helpers → Add Helper → Number.

| Helper | Entity ID | Min | Max | Step | Default | Unit | Purpose |
|---|---|---|---|---|---|---|---|
| Front Porch Temp Threshold | `input_number.front_porch_temp_threshold` | 60 | 110 | 1 | 80 | °F | Temperature alert threshold |

> Lux threshold helper removed. Daytime restriction replaced with explicit time window: 6:00am–10:00pm. No notifications outside that window.

After creating, confirm both appear in Developer Tools → States.

---

## Step 8 — Confirm Phone Notify Entity IDs

Find the `notify.mobile_app_*` entity IDs for both phones:

HA → Developer Tools → Actions → search "notify.mobile_app"

Both phones must appear. If a phone is missing:
1. Install HA Companion app (Google Play: "Home Assistant" by Nabu Casa)
2. Connect to `http://raspberrypi.local:8123`
3. Grant notification permissions
4. Restart HA

**Confirmed entity IDs:**

| Phone | Entity ID |
|---|---|
| Joseph's Pixel 10 Pro XL | `notify.mobile_app_pixel_10_pro_xl` |
| Robin's Pixel 7 Pro | `notify.mobile_app_pixel_7_pro` |

---

## Step 9 — HA Automations

> **Note:** Complete Step 8 first. Automation YAML below uses placeholder notify entity IDs
> that will be replaced once Joseph confirms the actual IDs.

### Confirmed entity IDs

| Entity | ID | Notes |
|---|---|---|
| Temperature sensor | `sensor.front_porch_temp_sensor_temperature` | Confirm after flash in Developer Tools → States |
| Illuminance sensor | `sensor.front_porch_temp_sensor_illuminance` | Confirm after flash |
| Temp threshold helper | `input_number.front_porch_temp_threshold` | Created in Step 7 |
| Time window | 6:00am – 10:00pm | No notifications outside this window |
| Front door | `binary_sensor.front_door_door` | Not used in automations — retained for reference |
| Joseph notify | `notify.mobile_app_pixel_10_pro_xl` | |
| Robin notify | `notify.mobile_app_pixel_7_pro` | |

> **HA entity ID note:** ESPHome MQTT discovery generates entity IDs from device name +
> sensor name. The IDs above are expected based on the device name `front-porch-temp-sensor`
> and sensor names `Temperature` / `Illuminance`. Verify in Developer Tools → States after
> flashing — if the actual IDs differ, update this document before creating automations.

### Automation 1 — Front Porch Temp Alert + Reminder

File: `automation-temp-alert.yaml`

Create in HA: Settings → Automations → New Automation → Edit in YAML (top right) → paste contents of `automation-temp-alert.yaml`.

### Automation 2 — Front Porch Temp Dropping

File: `automation-temp-dropping.yaml`

Create in HA: Settings → Automations → New Automation → Edit in YAML (top right) → paste contents of `automation-temp-dropping.yaml`.

> **After Joseph confirms notify entity IDs in Step 8**, replace all instances of
> `notify.mobile_app_pixel_10_pro_xl` and `notify.mobile_app_pixel_7_pro` with the actual entity IDs
> (e.g. `notify.mobile_app_pixel_10_pro`).

---

## Step 10 — Overview Page Card

Add the front porch sensors to the HA Overview page:

1. Open the Overview page → Edit
2. Add a favorite entity for each sensor:
   - Temperature (`sensor.front_porch_temp_sensor_temperature`)
   - Pressure (`sensor.front_porch_temp_sensor_pressure`)
   - Humidity (`sensor.front_porch_temp_sensor_humidity`) — shows Unknown until genuine BME280 arrives
   - Illuminance (`sensor.front_porch_temp_sensor_illuminance`)
3. Customize summaries as desired

> `input_number` helpers (temp threshold, lux threshold) cannot be added as Overview
> favorites in the current HA UI. Adjust thresholds via Settings → Devices & Services
> → Helpers when needed.
>
> `dashboard-card.yaml` is retained as a reference for the entity list but is not
> directly pasteable into the new HA Overview UI.
