# Back Patio Temp Sensor

ESP32 environmental sensor for the back patio — monitors temperature, pressure, and
light level. Duplicate of `front-porch-temp-sensor`'s design (CARD-0219), same hardware
and firmware pattern, different location.

**Status:** Build — perfboard assembled, bench-tested, and flashed (2026-09-21). WiFi, MQTT, and the BH1750 (light sensor) all confirmed live. Blocked on one part: the installed BME280 is a counterfeit BMP280 and is rejected by the firmware; genuine replacement ordered, swap is drop-in.
**Hardware:** ESP32 + BME280 + BH1750

---

## What It Solves

Same purpose as front-porch-temp-sensor: Tucson summers are dangerously hot, and this
sensor gives visibility into back patio conditions. Custom automation (e.g. door
open/close notifications) is deliberately undecided for now — see `integration.md`.

---

## Hardware

| Component | Details |
|---|---|
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102, USB-C — silkscreened `NODEMCU` / `ESP-32S` / `V1.1` on the underside (same board batch as air-quality-monitor's). All 38 silkscreen labels verified against `ESP32-project-pins.md` on 2026-09-21 — **against a photo of a same-batch board, not this unit's own** (corrected 2026-09-22: `esp32-pins-photo.jpg` is byte-identical to `air-quality-monitor/esp32_pins.jpg` and originates from CARD-0012). Valid for the batch; this specific board's silkscreen has not been photographed. See that file's pin 18 note for the one conflict found, unused by this build. |
| Temp / humidity / pressure | BME280 (genuine GY-BME280), I2C at GPIO21/22 |
| Light | BH1750 (GY-302), I2C at GPIO21/22, ADDR pin → GND (address 0x23) |
| Power | USB-C from back patio outlet |
| Firmware | ESPHome |

Both sensors share the I2C bus. See [wiring.md](wiring.md) for full wiring checklist
and [ESP32-project-pins.md](ESP32-project-pins.md) for the complete pin table.

---

## Architecture

```
BME280 (temp/humidity/pressure)  +  BH1750 (light)
                  │  I2C
                  ▼
        ESP32 / ESPHome
                  │  MQTT: jctsh/components/back-patio-temp-sensor/...
                  ▼
        Mosquitto broker (Raspberry Pi)
                  │
          ┌───────┼───────────────┐
          ▼       ▼               ▼
   Home      Node-RED          Node-RED
   Assistant log router +      env data handler
   sensor    watchdog          (wildcard .../data)
   entities                         │
                               Google Sheets
                               (Environmental Data)
```

**Location:** Back patio, at the outlet mount point — point P2 in
[house-lot-coordinates.md](../../house-lot-coordinates.md) (32.4614183, -111.1184405).

---

## Quick Start

1. Copy `secrets.yaml.template` → `secrets.yaml` and fill in credentials from
   `credentials.local.md` (after `mqtt-account-setup.md`'s account is created)
2. See [flashing.md](flashing.md) for flash procedure
3. See [integration.md](integration.md) for HA entity setup
4. See [testing.md](testing.md) to verify end-to-end operation

---

## How It Works

Temperature, pressure, and illuminance are published to MQTT every 60 seconds.
HA auto-discovers all entities via MQTT discovery.

Every 5 minutes the device publishes a JSON payload to
`jctsh/components/back-patio-temp-sensor/data`. The Node-RED environmental data handler
(wildcard `jctsh/components/+/data`) routes this to Google Sheets via Apps Script —
no Node-RED changes needed.

Every 30 minutes the device publishes a heartbeat to
`jctsh/components/back-patio-temp-sensor/heartbeat`. The Node-RED watchdog monitors
this and sends a push notification if silent for more than 35 minutes.

No custom threshold/notification automation exists yet — deliberately deferred, see
`integration.md`.

---

## Files

| File | Purpose |
|---|---|
| `back-patio-temp-sensor.yaml` | ESPHome firmware config |
| `parts-list.md` | Consolidated bill of materials |
| `secrets.yaml` | Credentials — gitignored, never commit |
| `secrets.yaml.template` | Credential template |
| `wiring.md` | Perfboard wiring checklist |
| `ESP32-project-pins.md` | Full 38-pin assignment table |
| `ESP32pins.png` | Generic 38-pin ESP32 reference pinout — **top view**, the orientation every pin number in this component is stated in |
| `esp32-pins-photo.jpg` | Board silkscreen photo, **underside** (so left/right are mirrored against the table and reference above). **A same-batch board, not this unit's own** — byte-identical copy of `air-quality-monitor/esp32_pins.jpg`. |
| `perfboard-layout.md` | Perfboard build layout |
| `flashing.md` | Flash procedure |
| `integration.md` | HA entity setup; custom automation deferral notes |
| `bench-test-plan.md` | Pre-flash bench worksheet — continuity, isolation, and power-on smoke test, derived from `wiring.md` |
| `testing.md` | End-to-end test procedure (post-flash) |
| `mounting.md` | Physical mounting instructions |
| `mqtt-account-setup.md` | Dedicated Mosquitto account creation |
| `CLAUDE.md` | Claude Code context — constraints and gotchas |
