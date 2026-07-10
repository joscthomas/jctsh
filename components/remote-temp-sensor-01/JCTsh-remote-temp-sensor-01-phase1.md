# JCTsh Remote Temp Sensor 01 — Phase 1–2 Planning Document
**Author:** Joseph C Thomas (JCT)
**Purpose:** Phase 1 discovery/feasibility and Phase 2 hardware selection for `remote-temp-sensor-01` — a standalone, solar+battery-powered outdoor environmental sensor for the backyard, in full sun (not sheltered, unlike front-porch-temp-sensor).
**Version:** 1.3
**Version description:** Added Phase 3 — Architecture and Integration Design. Power-budget analysis, sleep-cycle firmware decision, MQTT/heartbeat/watchdog/SmartThings/LED checklist, timeout locations, bench/install boundary. Added GPIO sensor power-gating decision (P-FET, reusing hiking-sensor's CARD-0027 design) and a full test-and-mitigation plan for the AEDIKO charger module's unmeasured quiescent current, including the TPL5111-class nanopower timer contingency. Phase 4 (Claude Code instructions) written — see `remote-temp-sensor-01-claude-code-instructions.md`; sensor power switch resolved as an on-hand BC557B PNP transistor rather than a purchased P-FET.
**Project:** JCTsh Remote Temp Sensor 01
**Status:** Phase 1–4 Complete — Ready for Phase 5 (Execution)
**Related files:** `README.md`, `CLAUDE.md`, `ENVIRONMENT.md`, `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`, `JCTsh-Build-Standards.md`, `JCTsh-Component-Planning-Pattern.md`, `jctsh-network.md`, `jctsh-parts-inventory.md`, `house-lot-coordinates.md`, `components/front-porch-temp-sensor/`, `components/hiking-sensor/`

---

## What This Component Is

A standalone outdoor environmental sensor node, sensor-wise similar to `front-porch-temp-sensor` (BME280 + BH1750) plus a UV sensor (LTR-390), but architecturally distinct: it is **not** sheltered — it lives in the backyard in full sun rather than under a porch overhang. That single difference cascades into a different power system (solar + swappable battery instead of wall USB power) and a different physical build (a real weatherproof, sun-shielded enclosure instead of the open standoff mount used on the porch).

The `-01` suffix is deliberate: this is meant to be a reusable pattern, not a one-off — intended as the first of potentially several remote (non-wall-powered) environmental sensor nodes at different property locations.

This component is part of the JCTsh environmental sensor family defined in `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md` and must conform to the standard payload and MQTT topic convention defined there.

---

## Context

- **Location:** Backyard, full sun exposure — not under any overhang or shade structure (this is the deciding factor that ruled out reusing front-porch-temp-sensor's open-standoff, wall-powered design as-is)
- **Origin:** Started as a conversation about building a "replicant" of front-porch-temp-sensor; diverged once the location changed from sheltered porch to open backyard
- **Relationship to other components:** Not a variant of front-porch-temp-sensor — separate component directory, separate MQTT account, separate hostname, per JCTsh-Build-Standards.md convention (same pattern as hiking-sensor vs. front-porch-temp-sensor, which share sensor types but are fully independent components)
- **Relationship to weather-station (CARD-0011):** Deliberately scoped smaller. Weather-station is planned as the comprehensive outdoor station (wind, rain, lightning, solar irradiance). Remote-temp-sensor-01 stays a simple, repeatable "remote environmental point" — temp/humidity/pressure/light/UV only. Wind, rain, and lightning sensing are explicitly out of scope here and remain weather-station's job, to avoid the two components competing for the same scope.

---

## Resolved Decisions

### Sensors

| Sensor | Decision | Rationale |
|---|---|---|
| Temperature / Humidity / Pressure | BME280 (genuine GY-BME280) | Same proven sensor as front-porch-temp-sensor and hiking-sensor; on hand |
| Ambient light | BH1750 (GY-302) | Same as front-porch-temp-sensor; on hand |
| UV Index | LTR-390 (Adafruit #4831) | Same sensor proven on hiking-sensor; directly useful outdoors (plant sun exposure, UV alert ideas already noted against CARD-0010); on hand (1 spare) |

**Explicitly deferred (not this build):** soil moisture, waterproof DS18B20 soil/surface probe — considered during Phase 1 discussion, cheap and would fit a backyard use case, but deferred to keep this build to the proven three-sensor pattern. Can be added as a future enhancement without redesigning the core.

**Explicitly out of scope (belongs to weather-station instead):** wind speed/direction, rain gauge, lightning detection, solar irradiance sensor.

### Power

| Decision | Rationale |
|---|---|
| Single EVE 18650 cell (INR18650/33V, 3.6V nominal, 3200mAh) — **not** the EEMB LiPo used elsewhere | ~3× the capacity of the EEMB 1100mAh pouch; full-sun location can support the larger battery's longer refill-from-empty time; on hand (5 spare, Bag 5) |
| AEDIKO 18650 charger + holder module | On hand (5 pairs, Bag 4); holder provides physically removable cell — required for the swap requirement below; onboard PCB protection compensates for the EVE cell being sold unprotected |
| SUNYIMA mini solar panel (5.5V 80mA) | On hand (10 spare, Bag 6); full-sun backyard placement should realize much closer to the panel's rated output than a shaded location would |
| **Cell must be user-swappable** | Joseph wants the ability to exchange the cell for a freshly-charged spare without disassembling the whole enclosure — drives the Phase 3 requirement for a dedicated small battery-access hatch, separate from the main enclosure seam (see Open Questions) |
| `battery_v` ADC monitoring via 68kΩ/68kΩ voltage divider | Same pattern as hiking-sensor; resistors on hand (Bag 17 assortment) |
| `solar_v` ADC monitoring | Per `JCTsh-Environmental-Data-Architecture.md` §solar_v — lets Node-RED/Sheets derive charging state (`solar_v > battery_v + ~0.3V`) without a dedicated charge-controller status pin |

Chemistry note (verified, not assumed): despite the misleading "3.3V" label on the inventory line (an artifact of EVE's part-number scheme — "33V" is their capacity-class code, not voltage), the EVE INR18650/33V is a standard Li-ion cell — 3.6V nominal, 4.2V peak charge — same charge profile as the EEMB LiPo. No charger incompatibility between the two chemistries in stock.

### Enclosure

| Decision | Rationale |
|---|---|
| Real weatherproof enclosure required — **not** open standoff mount | Full-sun, unsheltered backyard location; per JCTsh-Build-Standards.md §1.1, open standoff mount is only the default when the location is not weather-exposed |
| BME280 needs a radiation-shielded vent (Stevenson-screen style) | Direct sun on an exposed sensor biases temperature readings high; hiking-sensor's louvered `vent-insert.stl` design already solved this exact problem and is directly reusable/adaptable rather than a from-scratch design |
| Solar panel mounts external to the enclosure, wire routed in through a dedicated weatherproof-oriented hole | Same pattern as hiking-sensor's solar wire hole (bottom-of-enclosure entry, oriented to shed water) |
| Dedicated small battery-access hatch, separate from the main shell seam | Enables swapping the 18650 without opening the full enclosure — avoids repeatedly loosening the main seal/screws for routine battery swaps |
| CAD approach | Reuse hiking-sensor's proven toolchain and patterns (OpenSCAD parametric body + Tinkercad cutout work, M3 heat-set inserts for shell fastening) rather than starting a new design process from zero |

This is a real CAD/print project — the second entry in the 3D-printing backlog Joseph wants queued up behind hiking-sensor's Session 1 PLA test-fit.

---

## Confirmed Bill of Materials (Phase 2 — inventory scan complete)

Full inventory scan performed against `jctsh-parts-inventory.md` before any purchasing discussion, per JCTsh-Component-Planning-Pattern.md. **Every electronic and build-hardware component needed is already on hand — zero purchases required** for the electronics/build-hardware BOM below.

| Category | Part | Stock | Qty needed |
|---|---|---|---|
| Compute | ESP32 DevKitC-32 (38-pin, CP2102) | 2 spare, Bag 1 | 1 |
| Sensors | BME280 (genuine GY-BME280) | 2 spare, Bag 3 | 1 |
| | BH1750 (GY-302) | 5 spare, Bag 19 | 1 |
| | LTR-390 (Adafruit #4831) | 1 spare, Bag 22 | 1 |
| Power | EVE 18650 cell (INR18650/33V, 3200mAh) | 5 spare, Bag 5 | 1 |
| | AEDIKO 18650 charger+holder module | 5 pairs, Bag 4 | 1 |
| | SUNYIMA mini solar panel (5.5V 80mA) | 10 spare, Bag 6 | 1 |
| | Resistors (68kΩ pair — `battery_v`/`solar_v` dividers) | Assortment, Bag 17 | 4 |
| Build hardware | Perfboard 5×7cm | Bag 9 | 1 |
| | Female pin header strips | Plastic Box | as needed |
| | M3 brass standoffs (internal board mount) | ZYAMY kit, Plastic Box | 4 |
| | M3 heat-set threaded inserts (enclosure bosses) | 300 pcs, Plastic Box | 4 |
| | 24 AWG hookup wire | Shelf | as needed |

**Not tracked in inventory / to be sourced separately:**
- **Enclosure screws** — the on-hand ZYAMY kit's M3×6 screws are almost certainly too short once wall thickness + insert depth stack up (hiking-sensor hit this exact issue and needed 30mm screws). Do not assume the kit screws work — confirm actual length needed once enclosure dimensions exist in Phase 4/CAD, then source separately.
- **3D printing filament** (PLA for test-fit, ASA for final print) — not tracked in `jctsh-parts-inventory.md`. Joseph will purchase what's needed at Xerocraft at print time — no inventory action needed here.

No USB-C cable or wall power adapter needed — solar+battery replaces wall power entirely for this build (unlike front-porch-temp-sensor).

---

## Standard Environmental Payload

Conforms to `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`. Fixed-location sensor — `lat`/`lon` are hardcoded constants (specific point TBD from `house-lot-coordinates.md` during Phase 3/install), not GPS-derived.

```json
{
  "component": "remote-temp-sensor-01",
  "ts": "2026-07-09T14:32:00Z",
  "lat": 32.xxxxx,
  "lon": -110.xxxxx,
  "temp_f": 92.4,
  "humidity_pct": 24.1,
  "pressure_hpa": 1009.8,
  "illuminance_lx": 48200.0,
  "uv_index": 8.3,
  "battery_v": 3.91,
  "solar_v": 4.35,
  "rssi_dbm": -62
}
```

---

## MQTT Component Name

`remote-temp-sensor-01`

Topics:
- `jctsh/components/remote-temp-sensor-01/data`
- `jctsh/components/remote-temp-sensor-01/log`
- `jctsh/components/remote-temp-sensor-01/heartbeat`

Dedicated Mosquitto account `remote-temp-sensor-01` to be created per JCTsh-Build-Standards.md §2.11, added to CLAUDE.md credentials table. Hostname/IP reservation to be added to `jctsh-network.md` in Phase 3/4.

---

## Phase 3 — Architecture and Integration Design

### Power Budget (drives the firmware architecture decision below)

| Scenario | Average draw | Daily energy |
|---|---|---|
| Continuous WiFi-connected (front-porch-temp-sensor's pattern) | ~120mA | ~2,880mAh/day |
| SUNYIMA panel realistic full-sun yield (derated for angle mismatch through the day, temperature) | — | ~250–300mAh/day |
| Wake/publish/deep-sleep cycle, 5-minute interval, ~5–8s awake per wake | — | ~120mAh/day |

**Continuous operation is not viable on this solar panel** — roughly a 10× shortfall against realistic solar income, regardless of how sunny the mounting location is. A hiking-sensor-style wake/publish/deep-sleep firmware architecture is required, not optional. At a 5-minute wake interval, daily consumption (~120mAh) sits comfortably inside the solar budget, and the 3200mAh battery gives ~26 days of pure-battery runtime as a cloudy-week buffer even with zero solar input.

### Resolved Decisions

| Item | Decision | Rationale |
|---|---|---|
| Firmware architecture | Wake → connect to JCTnet1 → read sensors → publish → deep sleep, repeat | Power-budget-driven, see above |
| Wake/publish interval | 5 minutes | Matches front-porch-temp-sensor's cadence and the standard JCTsh publish interval; ~120mAh/day, well inside solar budget; also satisfies the heartbeat requirement below with no separate always-on timer needed |
| Offline flash logging | **Not needed** | Unlike hiking-sensor, this is a fixed backyard location expected to have a solid JCTnet1 signal at all times — no field-mode/replay-on-reconnect complexity required. Simpler firmware than hiking-sensor's dual-mode design. If real-world signal turns out weaker than expected once installed, hiking-sensor's flash-log pattern (`core/offline-logger/sensor_logger.h`) is available as a fallback to add later. |
| MQTT topic naming | `jctsh/components/remote-temp-sensor-01/data`, `/log`, `/heartbeat` | Standard environmental sensor family convention |
| MQTT account | Dedicated `remote-temp-sensor-01` Mosquitto account, created per JCTsh-Build-Standards.md §2.11 | Per-component account isolation, same as every other JCTsh device |
| Heartbeat | Folded into the 5-minute wake/publish cycle — every successful wake that publishes data also satisfies the heartbeat requirement | No separate always-on interval timer needed, unlike hiking-sensor's field-mode (10min log) vs. heartbeat (30min) split — this device only has one cadence |
| Message logging | Standard JSON to `/log`; Node-RED wildcard subscription routes automatically | No new Node-RED flow needed |
| Watchdog | Heartbeat topic `jctsh/components/remote-temp-sensor-01/heartbeat` — caught automatically by existing Node-RED watchdog wildcard | Gaps beyond ~1-2 missed 5-minute cycles should alert, since (unlike hiking-sensor) this device is never expected to be out of range |
| SmartThings / Google Home | Expose via HA SmartThings integration's entity-exposure feature (temp, humidity, UV at minimum) | Fixed, always-reporting sensor — reasonable to surface in Google Home, same as front-porch-temp-sensor could; no virtual switches needed, just entity exposure config |
| LED indicators | None | Matches front-porch-temp-sensor's decision; saves power on every wake cycle (now power-constrained, unlike the wall-powered porch sensor); avoids adding a light source to an otherwise dark backyard at night |
| Timeout/timer logic | WiFi/MQTT connect timeout lives in ESPHome firmware — if not connected within ~20–30s of waking, abandon the attempt and return to deep sleep rather than draining the battery holding a connection open | Protects the power budget from a bad-signal edge case; no Node-RED or HA-side timer logic needed — this is passive data, same as front-porch/hiking-sensor |
| Battery-access hatch — architecture level | Enclosure has two independent internal cavities: a main electronics cavity (ESP32, sensors, perfboard) and a separate battery cavity with its own small access hatch | Swapping the 18650 must never require opening the main electronics enclosure; exact hatch fastening mechanism (thumbscrew panel vs. friction-fit door) is a CAD-level decision, deferred to Phase 4 — same treatment as hiking-sensor's screw-length question |
| Solar panel orientation | Fixed tilt facing true south, roughly latitude angle (~32°, Tucson) for balanced year-round yield | Standard fixed-panel solar design guidance; exact mounting bracket geometry is a Phase 4/CAD detail |
| Sensor power gating during sleep | **Include a GPIO-controlled high-side load switch on the 3.3V rail feeding BME280/BH1750/LTR-390 from the start** — same architectural pattern as hiking-sensor's CARD-0027 (P-FET), but implemented with an **on-hand BC557B PNP transistor substituting for the P-FET** (resolved in Phase 4 — see instructions doc). Buying a dedicated P-FET remains available as an alternative later if the BC557B proves inadequate (lower on-resistance and zero static gate current vs. the BC557B's small continuous base-current draw while switched on) — not needed by default at this build's current level, a known trade-off rather than an oversight. | ESP32 deep sleep only stops CPU execution — it does not cut power to downstream peripherals (confirmed by hiking-sensor's CARD-0027 finding). This device is asleep ~99%+ of the time by design (5-min wake, ~5-8s awake), unlike hiking-sensor where sleep was mostly transport/storage — so un-gated sensor quiescent draw runs against the power budget almost continuously. Worth building in from day one rather than deferring, unlike hiking-sensor's "measure first" sequencing. Switch sits between the ESP32's `3.3V` pin and the sensors, gated active-low by GPIO27. |
| Charger/boost module quiescent current — **unresolved, needs measurement** | Cannot be gated by the ESP32 (same constraint as hiking-sensor — the ESP32 is powered *from* the AEDIKO module's boost output, so cutting it would cut the ESP32 itself) | hiking-sensor's CARD-0026 found the TP4056+boost module's own undocumented quiescent current (plausibly 1-5mA) was likely the dominant sleep-mode drain — bigger than the sensors themselves. The AEDIKO 18650 charger+holder module here is the same class of device. If it draws similarly, that's ~24-120mAh/day running 24/7, comparable in magnitude to the entire wake-cycle power budget above. **This must be measured on the actual AEDIKO module before the power budget in this doc can be trusted** — same bench measurement CARD-0026 already worked out for hiking-sensor's tester rig is directly reusable here. Carried into Phase 4 as a required bench step, not deferred. See "Charger Module Quiescent Current — Test and Mitigation Plan" below for the full procedure and contingency. |

### Charger Module Quiescent Current — Test and Mitigation Plan

**Test procedure (bench, adapted from hiking-sensor's CARD-0026 tester rig):**
1. Wire one EVE 18650 cell into the AEDIKO charger+holder module. Connect the boost output to a spare ESP32 flashed to go straight into deep sleep on boot (reuse the CARD-0026 forced-sleep firmware trick — tie the dock-detect-equivalent pin so the boot logic reliably proceeds into sleep rather than floating awake).
2. Break the battery's positive lead and insert a multimeter in series (DC current mode, µA/mA jack — not the unfused high-current jack).
3. Take two readings: **(a)** module output completely unloaded (nothing connected to the boost output at all) and **(b)** module driving the spare ESP32 in deep sleep (~10µA baseline). The difference between (b) and the ESP32's known ~10µA isolates how much the AEDIKO module itself is adding.
4. Record the result in this doc and in `jctsh-parts-inventory.md`'s AEDIKO module entry — this is currently undocumented by the manufacturer, same gap hiking-sensor found for its TP4056+boost module.

**Mitigation — contingent on what the measurement shows:**

| Result | Action |
|---|---|
| Small (tens to low hundreds of µA) | Do nothing — at ~300µA continuous that's only ~7mAh/day, negligible against the ~250-300mAh/day solar budget. This is the expected/hoped-for outcome and requires no design change. |
| Significant (low-mA range, matching hiking-sensor's suspicion for its own module) | The P-FET sensor-gating decision above does **not** help here — it only gates the sensors, not the charger/boost module itself, since the ESP32 controlling the P-FET is powered *by* that module and can't cut its own supply. Real fix: replace the always-on ESP32-managed sleep architecture with a **nanopower timer IC** (e.g., TI TPL5111/TPL5110) sitting between the battery and everything downstream (boost module + ESP32 + sensors). These draw only ~35nA themselves and physically cut power to the entire circuit except during scheduled wake windows; the ESP32 pulls a `DONE` pin when finished to let the timer cut power again. Eliminates the boost module's quiescent draw entirely, since nothing downstream stays powered between wakes. **Bigger architectural change** — the ESP32 no longer owns its own wake schedule — and **not currently in parts inventory** (would need to be purchased, the first BOM item to break the "zero purchases" Phase 2 result). Only pursue if the measurement actually shows a problem. |

**Philosophy:** measure first, exactly as CARD-0026 established for hiking-sensor — don't add TPL5111-class complexity preemptively for a problem that might not exist.

### Bench/Install Boundary

**Bench:** perfboard assembly and soldering, ESPHome flash and firmware verification, sensor read verification (BME280/BH1750/LTR-390 over I2C), WiFi/MQTT publish verification, deep-sleep wake-cycle timing verification, solar/battery charge circuit verification (lamp or partial sun, not final placement).

**Install:** final enclosure assembly (including the battery hatch), backyard mounting at the confirmed full-sun location, solar panel final orientation/angle, and multi-day real-sun verification that the battery net-charges rather than net-drains at the 5-minute wake interval — this last check can only happen at the real install location under real sun, not on the bench.

---

## Open Questions for Phase 4

1. **Exact backyard mounting location:** which point from `house-lot-coordinates.md`, and confirm true full-sun exposure at that spot (no fence/tree shade at any time of day) — needed for the `lat`/`lon` constants in the payload and to validate the full-sun assumption the power budget depends on.
2. **Battery hatch fastening mechanism:** thumbscrew panel, friction-fit door, or something else — CAD-level decision once enclosure dimensions exist.
3. **Vent insert adaptation:** hiking-sensor's louvered vent was sized for its own enclosure opening — dimensions need re-deriving for this enclosure's BME280 opening, not copied verbatim.
4. **Screw length:** confirm actual M3 screw length needed once enclosure wall/insert dimensions exist (see Phase 2 BOM note) — do not assume the on-hand M3×6 kit screws are sufficient.
5. **Hostname/IP reservation:** assign and record in `jctsh-network.md` once the device is ready to flash.
6. **Measure AEDIKO 18650 charger+holder module's quiescent current** — required before the power budget above can be trusted; reuses the same bench tester-rig approach as hiking-sensor's CARD-0026 (break the battery's positive lead, multimeter in series, read steady-state current with the ESP32 in deep sleep).
7. ~~P-FET sensor-gating circuit~~ **Resolved in Phase 4:** GPIO27 drives an on-hand BC557B PNP transistor as the high-side sensor power switch, substituting for a purchased P-FET. Buying a dedicated P-FET remains available as a future alternative if the BC557B proves inadequate during bench testing — not assumed necessary by default.

---

## Phase 4 Entry Criteria

Phase 1 (feasibility, sensor scope), Phase 2 (hardware BOM), and Phase 3 (architecture) are complete. Phase 4 (Claude Code instructions) begins when Joseph directs it — at that point, produce the full step-by-step instruction set following the `JCTsh-Component-Planning-Pattern.md` template, bench steps before install steps, with Step 0 reading `JCTsh-Build-Standards.md` in full.

---

*Phase 1–3 completed through interactive planning session, 2026-07-09. Sensor set, power system, full BOM, sleep-cycle firmware architecture, and full Phase 3 integration checklist all resolved.*
