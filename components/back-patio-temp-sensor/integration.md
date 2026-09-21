# Back Patio Temp Sensor — HA Integration

Home Assistant configuration for this component. Follow sections in order.

---

## Step 1 — Verify HA Device Discovery

ESPHome MQTT discovery registers the device automatically on first MQTT connect.

Confirm in HA:
- Settings → Devices & Services → MQTT → back-patio-temp-sensor
- Entities present: Temperature, Humidity, Pressure, Illuminance

No manual HA configuration needed for discovery.

---

## Step 2 — Overview Page Card

Add the back patio sensors to the HA Overview page:

1. Open the Overview page → Edit
2. Add a favorite entity for each sensor:
   - Temperature (`sensor.back_patio_temp_sensor_temperature`)
   - Pressure (`sensor.back_patio_temp_sensor_pressure`)
   - Humidity (`sensor.back_patio_temp_sensor_humidity`)
   - Illuminance (`sensor.back_patio_temp_sensor_illuminance`)
3. Customize summaries as desired

> **HA entity ID note:** ESPHome MQTT discovery generates entity IDs from device name +
> sensor name. The IDs above are expected based on the device name `back-patio-temp-sensor`
> and sensor names `Temperature` / `Humidity` / `Pressure` / `Illuminance`. Verify in
> Developer Tools → States after flashing — if the actual IDs differ, update this document.

---

## Custom Automation — Deliberately Deferred (CARD-0219, Planning)

Front-porch-temp-sensor's automation pattern (cool/warm ±2°F threshold notifications,
`input_number` helper, time-windowed HA automations) is the natural template if the same
kind of automation is wanted here — but Joseph explicitly deferred deciding this until
after the sensor is up and running, not during Planning. If/when a custom automation is
decided:

1. Reference `components/front-porch-temp-sensor/integration.md` Steps 7–9 and its two
   `automation-front-porch-*.yaml` files as the template.
2. If Google Assistant voice exposure is wanted (CARD-0165's pattern), check for a
   Google-side naming collision first — CARD-0165 hit exactly this with an unrelated
   SmartThings sensor answering "front porch temperature" queries.
3. Create `components/back-patio-temp-sensor/automation-*.yaml` files and an
   `input_number.back_patio_temp_threshold` helper as needed, following the same
   structure as front-porch's.

Not built yet — no files exist for this until the decision is made.
