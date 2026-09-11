# Air Quality Monitor — Operations Guide

Day-to-day operation and interpretation. For build steps see
`air-quality-monitor-claude-code-instructions.md`; for physical wiring see
`wiring.md`; for the full build/debugging history see `tos/kanban-board.md`
(CARD-0012 and its related cards) and `components/air-quality-monitor/CLAUDE.md`.

## Hardware Overview

| Component | Role |
|---|---|
| ESP32 + SEN55 | Reads PM1.0/2.5/4.0/10.0, VOC Index, NOx Index, temperature, humidity every 2 minutes |
| EEMB 1100mAh LiPo + TP4056 + Pololu D24V10F3 | Power system — TP4056 charges the battery only (its boost stage is unused); the Pololu buck regulator supplies the ESP32 directly from the battery |
| BK-1208 latching push button (Power Switch) | True hard off / forced cold restart — gates the regulator's `VIN`, not TP4056's charge path |
| SS12D10 slide switch (Intent, GPIO27) | Signals "actively collecting field data" when closed |
| Dock detect (GPIO32 divider) | Detects external power (USB or solar) on TP4056's charge input |
| RGB LED (KY-016) | Boot self-test, PM2.5 threshold color, and networking-status diagnostics (Blue) |

This is a version-2 design relative to hiking-monitor — same underlying philosophy, evolved with a genuinely different signal architecture. See "The Three-Signal Model" below for the key difference.

---

## The Three-Signal Model

Unlike hiking-monitor (which conflates "docked" with "session over"), this device tracks three independent signals, per `JCTsh-Build-Standards.md` §2.14 point 12 — none ever stands in for another:

| Signal | What it means | How it's read |
|---|---|---|
| **Intent** | Are you actively collecting field data right now? | SS12D10 slide switch, GPIO27. Closed (ON) = collecting. |
| **Power Connected** | Is external power (USB or solar) present? | Dock detect, GPIO32. Says nothing about whether a session is over — solar can connect mid-hike. |
| **Power Switch** | Is the device powered at all? | BK-1208 latching button, inline in the battery path. Off = true zero-draw. |

**The key consequence:** field data collection runs whenever Intent is ON, regardless of whether power is connected — plugging in a power bank or the solar panel mid-collection does not end the session or trigger an upload. Only a WiFi/upload attempt cares about Power Connected, and only when Intent is OFF at the same time.

---

## Operating Modes

### Off (Power Switch open)
- True zero-draw — nothing runs, nothing drains.
- TP4056 still charges the battery in this state (charging is upstream of the Power Switch) — leaving it off in storage with USB connected still tops off the battery.
- Also the way to force a cold restart if the device ever hangs or loops: switch off, then on.

### Collecting (Intent ON)
- SEN55 duty-cycles every 2 minutes: warms into full Measurement mode (~40s), takes a reading, drops back to low-power RHT/Gas-Only mode until the next cycle.
- Runs unconditionally regardless of Power Connected — collecting on battery alone, or collecting while charging via USB/solar, both work identically.
- No WiFi attempt happens while Intent is ON, full stop — same as hiking-monitor's field mode, for the same reason (no unnecessary radio current while the thing you actually care about is sensor accuracy and battery life).
- Readings buffer to flash if there's no active MQTT connection; buffered readings replay automatically once one exists (see Upload Behavior below).

### Idle / Docked (Intent OFF)
- No sensor duty-cycling.
- If Power Connected and battery is healthy (≥3.5V), the device attempts WiFi/MQTT and replays anything buffered. See Upload Behavior below for the exact gate and retry timing.
- If Power Connected but battery is still low, WiFi is deliberately not attempted — see Battery & Charging below.

---

## Upload Behavior (WiFi Gate)

A WiFi/MQTT attempt requires **all three** to be true simultaneously — checked fresh every 2 minutes, not just at boot:

1. Intent OFF (collecting session genuinely over)
2. Power Connected (docked/charging via USB or solar)
3. Battery ≥ 3.5V

If all three hold and there's no existing connection, the device attempts for up to **2 minutes**; if it can't connect in that window, it gives up and waits **15 minutes** before trying again — indefinitely, not a fixed number of retries. An already-established connection is only torn down by a real Intent-on or Power-disconnected event, never by a momentary voltage dip — a brief under-load sag no longer kills a working link (a real bug found and fixed 2026-09-09).

Buffered readings replay automatically once connected, and also re-check on every 2-minute tick afterward — so if a replay was deferred for low battery while docked, it doesn't need a fresh disconnect/reconnect cycle to retry once voltage recovers.

**Why 3.5V, not the regulator's 3.4V floor:** the regulator's absolute minimum input is 3.4V, confirmed by a real brownout-loop failure at exactly that voltage during battery-alone bench testing. 3.5V keeps a small margin above that catastrophic floor specifically for a weak/solar charging source that might not supply burst current as robustly as USB — not a large safety margin, a deliberate small one.

---

## Battery & Charging

| Voltage | Meaning |
|---|---|
| ~4.2V | Fully charged |
| ~3.7V | Nominal — plenty of capacity |
| 3.5V | WiFi/upload gate — below this, no networking is attempted, everything just keeps buffering to flash |
| 3.4V | Critical — Measurement-mode sampling itself is suspended (RHT/Gas-Only idle continues, voltage keeps being monitored) until it recovers |

Charging is via TP4056 (micro-USB or the SUNYIMA solar panel, both feed the same charge-input node) and is completely independent of the Power Switch position — a device left switched off in storage still charges if plugged in.

**"Replay deferred" log messages are not an error.** Seeing `Replay deferred - battery X.XXV below 3.5V upload threshold, waiting for charge` on the dashboard just means the device woke, checked, found itself under the upload-safe margin, and correctly declined to spend battery on a WiFi attempt — not a fault. If the device then goes fully silent, that's expected too: below 3.5V it stops even trying to connect, so there's nothing further to report until it's recharged past that line (or, if the deeper 3.4V critical floor is reached, until it's recharged past that instead).

---

## The Measurements

SEN55 reports 8 values — this is the complete set the sensor is physically capable of producing:

| Measurement | What it is |
|---|---|
| **PM1.0, PM2.5, PM4.0, PM10.0** (µg/m³) | Airborne particle mass concentration at four size cutoffs. PM2.5 is the one most health guidance cites (wildfire smoke, vehicle exhaust, cooking) — fine enough to reach deep into lungs. PM10 is coarser (dust, pollen). Each size bucket is cumulative — PM10 includes everything PM2.5 counts plus larger particles. |
| **VOC Index** | Volatile organic compounds (paints, cleaning products, cooking, off-gassing). **Not a concentration** — Sensirion's own relative index, 1–500, self-calibrating to "typical recent average for this location," centered on 100. Rising well above 100 means something is actively off-gassing more than usual right now, not an absolute hazard level. |
| **NOx Index** | Nitrogen oxides (combustion — gas stoves, vehicle exhaust). Same index convention as VOC (1–500, baseline ~100, self-calibrating), not ppm. |
| **Temperature / Humidity** | SEN55's own onboard reading, independent of hiking-monitor's BME280 — kept as a second, independent reference for cross-checking that device's readings over time (CARD-0218), not redundant data. |

Both index values take a while to "learn" a baseline after power-on, so readings in the first few minutes of a fresh session are less meaningful than ones taken once it's been running a while.

---

## LED Reference (RGB module)

| Pattern | Meaning |
|---|---|
| Solid red, 3s (boot) | Reset reason was a brownout/glitch — a real power fault caused this boot |
| Solid blue, 1s (boot) | Normal reset reason — ordinary boot |
| 2× blue blink, 2× red blink, 2× yellow (red+green) blink, 2× green blink (boot self-test) | Sensor/system self-test sequence running |
| Green blinking, no timeout (boot) | Waiting for SEN55's first valid reading |
| Solid yellow 3s, then solid red 3s (boot) | Threshold-color demo — confirms the PM2.5 indicator LEDs actually work, not a live reading |
| Green (steady, on a reading) | PM2.5 < 12 µg/m³ — good |
| Yellow (red+green, on a reading) | PM2.5 12–35 µg/m³ — moderate |
| Red (on a reading) | PM2.5 > 35 µg/m³ — high |
| 3× fast blue+red blink (boot, docked) | Voltage-blocked — docked and idle, but battery below 3.5V, deliberately not attempting WiFi |
| Slow blue blink (~1s cycle) | WiFi attempt actively in progress |
| Solid blue, 1s | MQTT just connected |
| 2× quick blue blink | WiFi attempt window expired without connecting — giving up until the next 15-min retry |

---

## Standard Workflows

### Before outdoor use
1. Confirm the Power Switch is on.
2. Turn Intent ON — collection begins within 2 minutes.

### During use
- No action needed — the device duty-cycles automatically, charging (if plugged into a power bank or solar) doesn't interrupt anything.
- Watch the PM2.5 threshold LED for a quick at-a-glance air-quality read.

### Ending a session / uploading
1. Turn Intent OFF.
2. If not already connected to power, dock it (USB into TP4056).
3. Once battery is ≥3.5V, the device connects and replays automatically — no manual trigger needed.

### Storage
1. Turn Intent OFF.
2. Switch the Power Switch off (true zero-draw) — battery still charges normally if left plugged in.

---

## Log Dashboard Messages

| Message | Category | Meaning |
|---|---|---|
| `Air quality monitor online - ESPHome ..., IP: ..., reset reason: ...` | System | Device booted and connected |
| `MQTT connected` / `MQTT disconnected` | MQTT | Broker connection state |
| `Replaying N buffered readings...` | System | Uploading buffered field data |
| `Buffered-data replay complete.` | System | All buffered data uploaded |
| `Replay deferred - battery X.XXV below 3.5V upload threshold, waiting for charge` | Alert | Normal — see Battery & Charging above, not an error |
| `Critical battery X.XXV - Measurement mode suspended until charge recovers` | Alert | Battery below 3.4V — sensor sampling paused until it recovers |
| `Heartbeat - uptime: Xh Ym, RSSI: ..., PM2.5: ..., VOC: ..., NOx: ..., batt: ...` | System | Alive, connected, 5-minute cadence |

---

## Data Pipeline

Readings publish to `jctsh/components/air-quality-monitor/data` (Environmental Data schema) whenever connected, or buffer to flash and replay per Upload Behavior above. Each row carries all 8 SEN55 measurements plus `battery_v` and `rssi_dbm` — no separate `lat`/`lon` (this device is not GPS-tracked the way hiking-monitor is).
