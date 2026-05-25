# Front Porch Temp Sensor — Flashing (Step 5)

## Prerequisites

- ESPHome CLI installed (`pip install esphome` or via Home Assistant Add-on)
- `secrets.yaml` filled in (already done — located in this directory)
- ESP32 connected to your computer via USB-C
- Breadboard wiring complete and visually verified (`wiring.md` checklist done)

---

## First Flash — USB Only

OTA is not available until the device has been flashed at least once.

**1. Confirm `secrets.yaml` exists**

```
components/front-porch-temp-sensor/
  front-porch-temp-sensor.yaml
  secrets.yaml          ← must exist and be filled in
  secrets.yaml.template
```

**2. Connect the ESP32 via USB-C**

Plug the ESP32 into your computer. The board will power on and power the BME280
and BH1750 via the 3.3V rail — this is expected.

**3. Run the flash command**

> **Windows path note:** The ESP-IDF compiler cannot handle spaces in file paths.
> The repo path (`JCT Documents`) contains a space, which causes a compile error.
> Always flash from `C:\esphome\front-porch-temp-sensor\` — a space-free copy of
> the YAML and secrets maintained for this purpose.

```
cd C:\esphome\front-porch-temp-sensor
esphome run front-porch-temp-sensor.yaml
```

If you edit `front-porch-temp-sensor.yaml` or `secrets.yaml` in the repo, re-copy
to the flash directory before flashing:

```
copy "C:\jctsh\components\front-porch-temp-sensor\front-porch-temp-sensor.yaml" C:\esphome\front-porch-temp-sensor\
copy "C:\jctsh\components\front-porch-temp-sensor\secrets.yaml" C:\esphome\front-porch-temp-sensor\
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

WiFi will loop until in range. If the fallback AP (`front-porch-temp-sensor-fallback`)
appears, WiFi credentials in `secrets.yaml` are wrong.

**5. Verify in Home Assistant**

Once MQTT connects, HA auto-discovers the device via MQTT discovery:

- Settings → Devices & Services → MQTT → front-porch-temp-sensor
- Four entities should appear: Temperature, Humidity, Pressure, Illuminance

If the device does not appear within 2 minutes of MQTT connecting, confirm
`discovery: true` and `discovery_prefix: homeassistant` are set in the YAML.

---

## Subsequent Flashes — OTA

After the first USB flash, all future updates can be done wirelessly:

```
esphome run front-porch-temp-sensor.yaml
```

ESPHome detects the device on the network and offers OTA upload. To force OTA:

```
esphome run --device front-porch-temp-sensor.local front-porch-temp-sensor.yaml
```

---

## Validation Checklist

After flashing, confirm all of the following before proceeding to Step 6:

- [ ] **Temperature** — plausible reading (not 0, not NaN). Expected range in Tucson: 70–115°F
- [ ] **Humidity** — plausible reading (not NaN). If NaN, sensor is a BMP280 counterfeit — swap required
- [ ] **Pressure** — plausible reading. Tucson is ~750m elevation; expect ~925 hPa (not sea-level ~1013 hPa)
- [ ] **Illuminance** — changes when a light source is moved near/away from the BH1750
- [ ] **All four entities** visible in HA under the front-porch-temp-sensor device
- [ ] **Log messages** appearing in dashboard at `http://raspberrypi.local/` (Basic Auth, user: `jctsh`)
- [ ] **Heartbeat** appearing in log dashboard every 5 minutes

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Serial port not found | Driver not installed | Install CP2102 driver from Silicon Labs |
| WiFi loops, never connects | Wrong credentials | Re-check `wifi_ssid` / `wifi_password` in `secrets.yaml` |
| MQTT not connecting | Wrong credentials or account not created | Re-check `mqtt_*` values; confirm Step 2 complete |
| I2C device 0x76 not found | BME280 wiring issue | Check SDA/SCL connections; confirm VCC is 3.3V not VIN |
| I2C device 0x23 not found | BH1750 wiring issue | Check ADDR pin tied to GND; check SDA/SCL |
| Humidity reads NaN | Counterfeit BMP280 (not BME280) | Replace sensor module |
| Pressure ~1013 hPa | Sea-level pressure reported | Not an error — sensor is working; Tucson reading is correct at ~925 hPa |
| HA device not discovered | MQTT discovery off | Verify `discovery: true` in YAML |
| Log messages not in dashboard | MQTT account issue or log server down | Check `http://raspberrypi.local/` — confirm log server running |

---

## Actual Results (2026-05-25)

| Sensor | Reading | Notes |
|---|---|---|
| Temperature | 85.5°F | Plausible for Tucson, May 25 |
| Humidity | Unknown | BMP280 counterfeit — no humidity sensor. Restore when genuine BME280 arrives. |
| Pressure | 13.46 psi (~928 hPa) | HA displays in psi (US unit system). 928 hPa correct for Tucson ~750m elevation. |
| Illuminance | 75.9 lx | Plausible shade reading |

All entities visible in HA: yes (humidity shows Unknown — expected)
Log messages visible in dashboard: yes
Heartbeat visible in dashboard: yes — firing every 5 minutes

**Deviations from expected:**
- Podazz BME280 3-pack (all 3 units) are counterfeit BMP280 — "Wrong chip ID" error on BME280 driver. Temporarily running `bmp280_i2c` platform. Genuine BME280 modules ordered; swap back documented in YAML comments.
- First 1–2 heartbeats after boot report `temp: unavailable` — expected. BMP280 `update_interval: 60s` means the first reading hasn't completed before the 5-minute heartbeat fires immediately at boot. Third heartbeat correctly shows temperature.
- `raspberrypi.local` occasionally fails DNS resolution on first attempt (IPv6/mDNS issue). MQTT reconnects automatically via IP on retry — not a blocker.
