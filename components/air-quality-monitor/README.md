# Air Quality Monitor

Planned portable clip-mounted sensor measuring PM1.0, PM2.5, PM4.0, PM10, VOC index,
and NOx index — carried on hikes alongside the hiking monitor to capture personal air
quality exposure on the trail.

**Status:** Bench phase underway (see [air-quality-monitor-claude-code-instructions.md](air-quality-monitor-claude-code-instructions.md) for full step tracking) — Steps 1–6 confirmed: SEN55 validated on breadboard, RGB LED boot/threshold logic implemented and confirmed live. Step 6 dropped the SEN55 power-gate transistor entirely (SEN55 is hard-wired always-on; duty-cycling moves to I2C mode-switching in Step 8). Step 7 (LiPo/LDO power validation) next.

---

## What It Solves

Fixed AQI stations miles away don't capture actual trail exposure to wildfire smoke,
haboobs, trail dust (silica), and summer ozone in the Tucson area. This device provides
a timestamped personal exposure record for every hike, correlated to GPS track and
hiking monitor environmental data in Google Sheets for post-hike analysis. A single RGB
LED gives immediate field awareness of PM2.5 level without a display.

---

## Planning

Phase 1 (discovery and feature decisions) is complete. Sensor selection, power system,
carry/enclosure approach, firmware pattern (follows hiking monitor exactly — do not
re-derive), and JCTsh integration are all decided. SEN55, Adafruit #5964 adapter, and
JST GH cable are all received and confirmed on hand.

See [JCTsh-air-quality-monitor-phase1.md](JCTsh-air-quality-monitor-phase1.md) for the
full Phase 1 planning document.

Build begins after the hiking monitor is complete.

---

## Planned Hardware

| Component | Details |
|---|---|
| Microcontroller | ESP32 DevKitC-32 (on hand) |
| Air quality | Sensirion SEN55 (PM1.0/2.5/4.0/10, VOC, NOx) via Adafruit #5964 adapter |
| Field indicator | RGB LED — see [LED Status Guide](#led-status-guide) below |
| Battery | EEMB LiPo pouch 603449, 1100mAh (on hand) |
| Power module | TP4056 + boost combined module (on hand) |
| Enclosure | 3D-printed with air intake/exhaust ports for SEN55 fan |

---

## LED Status Guide

The single RGB LED (GPIO18/19/23) communicates device state through color and blink
pattern, not just a static PM2.5 color. On power-up it runs a fixed self-test sequence,
then hands off to an ongoing operational pattern:

| Phase | Behavior | Meaning |
|---|---|---|
| 1. Self-test | Two blinks each, in order: **Blue → Red → Yellow → Green** (300ms on/off) | Confirms all three color channels (and their combinations) drive correctly — a bad solder joint or dead channel shows up here as a missing color |
| 2. Waiting for data | **Green blinks** steadily, 400ms on/off, **no timeout** | SEN55 hasn't produced a valid PM2.5 reading yet. Deliberately unbounded — a "looks connected" wiring fault can silently produce zero valid readings for minutes (seen during Step 4 bench debugging), so a timeout here would let the device falsely claim "all is well" while actually broken. If this runs more than ~30s, suspect a physical connection issue (see `wiring.md`'s SEN55 wiring section — the SEN55 power-gate transistor was dropped in Step 6, so this is no longer a gate-circuit issue, just the direct GND/VIN/I2C wiring). |
| 3. Ready | **Solid green, 2 seconds**, then off | One-time confirmation: boot finished, first valid reading received, handing off to normal operation |
| 4. Threshold-color check | **Solid Yellow (3s), then solid Red (3s)** | Confirms the Yellow and Red threshold colors themselves display correctly, on every boot — not just Green, and without needing a real particulate source in range. Permanent, not a one-off test. |
| 5. Operational (ongoing) | Brief ~1s flash on every new reading (~every 10s): **Green** (<12 µg/m³, Good), **Yellow** (12–35, Moderate), **Red** (>35, Unhealthy) | Current air quality. Flashes rather than stays lit to save power on battery — same information, most of the continuous-LED power draw eliminated |

**Design note:** this color/blink vocabulary (self-test sequence, unbounded "still waiting" blink vs. bounded confirmation, brief operational flash) is generic enough to reuse for other status conditions if this device or a future one needs to communicate more than PM2.5 alone — e.g. low battery, WiFi/MQTT connection trouble. Not implemented yet; noted here as a pattern worth extending rather than re-deriving if that need comes up.
