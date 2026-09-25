# Back Patio Temp Sensor — Flashing

## Prerequisites

- ESPHome CLI installed (`pip install esphome` or via Home Assistant Add-on)
- `secrets.yaml` filled in (from `secrets.yaml.template`)
- ESP32 connected to your computer via USB-C
- Perfboard wiring complete and visually verified (`wiring.md` checklist done — this build goes straight to perfboard, no breadboard stage)

---

## First Flash — USB Only

OTA is not available until the device has been flashed at least once.

**1. Confirm `secrets.yaml` exists**

```
components/back-patio-temp-sensor/
  back-patio-temp-sensor.yaml
  secrets.yaml          ← must exist and be filled in
  secrets.yaml.template
```

**2. Connect the ESP32 via USB-C**

Plug the ESP32 into your computer. The board will power on and power the BME280
and BH1750 via the 3.3V rail — this is expected.

**3. Run the flash command**

> **Windows path note:** The ESP-IDF compiler cannot handle spaces in file paths.
> The repo path (`JCT Documents`) contains a space, which causes a compile error.
> Always flash from `C:\esphome\back-patio-temp-sensor\` — a space-free copy of
> the YAML and secrets maintained for this purpose.

```
cd C:\esphome\back-patio-temp-sensor
esphome run back-patio-temp-sensor.yaml
```

If you edit `back-patio-temp-sensor.yaml` or `secrets.yaml` in the repo, re-copy
to the flash directory before flashing:

```
copy "C:\jctsh\components\back-patio-temp-sensor\back-patio-temp-sensor.yaml" C:\esphome\back-patio-temp-sensor\
copy "C:\jctsh\components\back-patio-temp-sensor\secrets.yaml" C:\esphome\back-patio-temp-sensor\
```

ESPHome will:
1. Validate the YAML
2. Compile the firmware (~2–5 minutes first time)
3. Detect the ESP32 serial port and upload over USB
4. Open the serial monitor after flashing

> **If ESPHome cannot find the port:** On Windows, check Device Manager for the CP2102
> USB-to-serial port (listed as `COM3`, `COM4`, etc.). Add `--device COM3` if needed.

**4. Watch the serial log**

After flashing, look for:

```
[I][wifi:283]: WiFi connected
[I][mqtt:xxx]: MQTT Connected
[I][i2c:xxx]: Found I2C device at address 0x23   ← BH1750
[I][i2c:xxx]: Found I2C device at address 0x76   ← BME280
```

The `scan: true` setting on the I2C bus causes ESPHome to log all discovered
devices at boot. Both 0x23 and 0x76 must appear — if either is missing, check
wiring for that sensor.

WiFi will loop until in range. If the fallback AP (`back-patio-temp-sensor-fallback`)
appears, WiFi credentials in `secrets.yaml` are wrong.

**5. Verify in Home Assistant**

Once MQTT connects, HA auto-discovers the device via MQTT discovery:

- Settings → Devices & Services → MQTT → back-patio-temp-sensor
- Four entities should appear: Temperature, Humidity, Pressure, Illuminance

If the device does not appear within 2 minutes of MQTT connecting, confirm
`discovery: true` and `discovery_prefix: homeassistant` are set in the YAML.

---

## Subsequent Flashes — OTA

> **Do not reboot the device within ~60 s of an OTA flash (added 2026-09-24, CARD-0333).** ESP32 OTA has automatic rollback: if the new image reboots before it is marked valid (about 60 s, when the log prints `Boot seems successful; resetting boot loop counter`), the bootloader silently reverts to the previous firmware. A restart button press, a power-cycle, or a second flash inside that window undoes the update while every tool still reports success. After flashing, wait past the 60 s mark, then confirm the device's *reported* config hash (the `sw` field of its retained discovery message, `homeassistant/sensor/<name>/temperature/config`) matches the build's `config_hash`.

After the first USB flash, all future updates can be done wirelessly:

```
esphome run back-patio-temp-sensor.yaml
```

ESPHome detects the device on the network and offers OTA upload. To force OTA:

```
esphome run --device back-patio-temp-sensor.local back-patio-temp-sensor.yaml
```

---

## Validation Checklist

After flashing, confirm all of the following before proceeding to mounting:

- [ ] **Temperature** — plausible reading (not 0, not NaN). Expected range in Tucson: 70–115°F
- [ ] **Humidity** — plausible reading (not NaN). If NaN, sensor is a BMP280 counterfeit — swap required. (Verify chip ID even though this unit's genuine per allocation — the same BME280-labeled-as-BMP280 mislabeling bit front-porch's original batch.)
- [ ] **Pressure** — plausible reading. Tucson is ~750m elevation; expect ~925 hPa (not sea-level ~1013 hPa)
- [ ] **Illuminance** — changes when a light source is moved near/away from the BH1750
- [ ] **All four entities** visible in HA under the back-patio-temp-sensor device
- [ ] **Log messages** appearing in dashboard at `http://pi1.local/` (Basic Auth, user: `jctsh`)
- [ ] **Heartbeat** appearing in log dashboard every 5 minutes

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Serial port not found | Driver not installed | Install CP2102 driver from Silicon Labs |
| WiFi loops, never connects | Wrong credentials | Re-check `wifi_ssid` / `wifi_password` in `secrets.yaml` |
| MQTT not connecting | Wrong credentials or account not created | Re-check `mqtt_*` values; confirm the MQTT account setup step is complete |
| I2C device 0x76 not found | BME280 wiring issue | Check SDA/SCL connections; confirm VCC is 3.3V not VIN |
| I2C device 0x23 not found | BH1750 wiring issue | Check ADDR pin tied to GND; check SDA/SCL |
| Humidity reads NaN | Counterfeit BMP280 (not BME280) | Replace sensor module |
| Pressure ~1013 hPa | Sea-level pressure reported | Not an error — sensor is working; Tucson reading is correct at ~925 hPa |
| HA device not discovered | MQTT discovery off | Verify `discovery: true` in YAML |
| Log messages not in dashboard | MQTT account issue or log server down | Check `http://pi1.local/` — confirm log server running |

---

## Actual Results

*(Fill in after first flash.)*

| Sensor | Reading | Notes |
|---|---|---|
| Temperature | | |
| Humidity | | |
| Pressure | | |
| Illuminance | | |

All entities visible in HA:
Log messages visible in dashboard:
Heartbeat visible in dashboard:

**Deviations from expected:**
