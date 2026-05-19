# Garage Radar — Flashing (Step 3)

## Prerequisites

- ESPHome CLI installed (`pip install esphome` or via Home Assistant Add-on)
- `secrets.yaml` filled in (copy `secrets.yaml.template`, fill values, save in this directory)
- ESP32 connected to your computer via USB-C
- Breadboard assembly complete and visually verified (`wiring.md` checklist done)

---

## First Flash — USB Only

OTA is not available until the device has been flashed at least once. The first flash
must be done over USB.

**1. Confirm `secrets.yaml` exists**

The file must be in the same directory as `garage-radar.yaml`:

```
components/garage-radar/
  garage-radar.yaml
  secrets.yaml          ← must exist and be filled in
  secrets.yaml.template
```

**2. Connect the ESP32 via USB-C**

Plug the ESP32 into your computer. The board will power on (and power the LD2412 via VIN).
This is expected — the LD2412 does not need to be disconnected for flashing.

**3. Run the flash command**

From the `components/garage-radar/` directory:

```
esphome run garage-radar.yaml
```

ESPHome will:
1. Validate the YAML
2. Compile the firmware (~2–5 minutes first time)
3. Detect the ESP32 serial port and upload over USB
4. Monitor the serial log output after flashing

> **If ESPHome cannot find the port:** On Windows, check Device Manager for the CP2102
> USB-to-serial port. It will appear as `COM3`, `COM4`, etc. ESPHome should detect it
> automatically; if not, add `--device COM3` (substitute your actual port number).

**4. Watch the serial log**

After flashing, ESPHome opens the serial monitor. Look for these lines to confirm success:

```
[I][app:029]: Running on ESP32
[I][wifi:283]: WiFi connected
[I][mqtt:xxx]: MQTT Connected
[I][ld2412:xxx]: LD2412 initialized
```

A WiFi connection attempt will loop until the ESP32 is in range of your network.
If it falls back to AP mode (`garage-radar-fallback` SSID appears), WiFi credentials
in `secrets.yaml` are wrong — double-check them.

**5. Verify in Home Assistant**

Once MQTT is connected, HA should auto-discover the device via MQTT discovery:

- Settings → Devices & Services → MQTT → garage-radar
- Entities should appear: Presence, Moving Target, Still Target, Moving Distance,
  Still Distance, Moving Energy, Still Energy, Detection Distance

If the device does not appear within 2 minutes of MQTT connecting, check that
`discovery: true` and `discovery_prefix: homeassistant` are set in `garage-radar.yaml`
(they are by default).

---

## Subsequent Flashes — OTA

After the first USB flash, all future updates can be done wirelessly:

```
esphome run garage-radar.yaml
```

ESPHome will detect the device on the network and offer OTA upload. You can also
force OTA explicitly:

```
esphome run --device garage-radar.local garage-radar.yaml
```

The device reboots automatically after OTA. Watch the log for the boot sequence
to confirm the update took effect.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Compile error: `ld2412` unknown | ESPHome version < 2025.8.0 | `pip install --upgrade esphome` |
| Serial port not found | Driver not installed | Install CP2102 driver from Silicon Labs |
| WiFi loops, never connects | Wrong credentials in `secrets.yaml` | Re-check `wifi_ssid` / `wifi_password` |
| MQTT not connecting | Wrong broker/username/password | Re-check `mqtt_*` values in `secrets.yaml` |
| HA device not discovered | MQTT discovery off or wrong prefix | Verify `discovery: true` in YAML |

---

## Next Step

Proceed to `testing.md` (Step 4) — sensor validation.
