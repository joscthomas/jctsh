# JCTsh Air Quality Monitor — Claude Code Instructions
**Author:** Joseph C Thomas (JCT)
**Purpose:** Step-by-step build instructions for `air-quality-monitor`, converting the decisions made in `JCTsh-air-quality-monitor-phase1.md` (Phases 1–3) into an executable build.
**Project:** JCT Smart Home (JCTsh)
**Version:** 1.1
**Version description:** Step 1 resolved (2026-08-19, Joseph): dock-detect-only for mode-switching confirmed, plus a new inline power switch (wired directly into the battery path, no GPIO) added for true transport/storage off — kept deliberately separate from mode-switching, per the CARD-0181 lesson that a GPIO-tapped switch only sets a mode flag rather than cutting power. Power architecture also changed from the originally-planned TP4056+boost combined module to a direct LiPo-to-LDO design (MCP1700) per `JCTsh-Build-Standards.md` §2.14 point 7 — recalculated runtime accordingly (see Hardware Context).
**Related files:** `JCTsh-air-quality-monitor-phase1.md`, `CLAUDE.md`, `JCTsh-Build-Standards.md`, `components/hiking-monitor/` (reference implementation — read before any firmware work, do not re-derive its patterns)

---

## Overview

`air-quality-monitor` is a portable, clip-mounted air quality sensor (PM1.0/2.5/4.0/10, VOC index, NOx index via a Sensirion SEN55) carried on hikes alongside hiking-monitor. Field-mode duty-cycle logging to onboard flash runs unconditionally, regardless of dock-detect state (**superseded 2026-08-20** — see Timeout policy below); dock-detect only triggers a background WiFi connection attempt (home or Pixel hotspot), and logging only pauses once that connection actually succeeds, at which point stored readings replay to MQTT. A single RGB LED gives real-time PM2.5 field awareness without a display.

This project inherits hiking-monitor's *firmware architecture* — it does not depend on hiking-monitor's physical enclosure, which remains a separate, unfinished, unrelated deliverable (CARD-0009).

---

## Working Pattern

Claude Code creates documentation and configuration files. Joseph follows those documents to perform physical assembly, wiring, flashing, and configuration work outside of Claude Code. Joseph reports results back, and Claude Code updates documentation to reflect actual findings, deviations, and lessons learned. Do not proceed to the next step until Joseph confirms the current step is complete.

---

## Hardware Context

| Component | Detail |
|---|---|
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102 USB-C (Bag 1, 1 remaining after hiking-monitor) |
| Air quality sensor | Sensirion SEN55 (SparkFun SEN-23715 — corrected 2026-07-09, was mislabeled SEN54 in inventory). PM1.0/2.5/4.0/10, VOC index, NOx index. I2C address 0x69 (fixed). Integrated fan. ~59mm × 37mm × 23mm. |
| Adapter | Adafruit SEN54/SEN55 Adapter Breakout (#5964) — JST GH connector, onboard 5V boost (100mA), level shifting, STEMMA QT/0.1" I2C output. Lets 3.3V ESP32 logic drive the 5V SEN55 with no separate 5V supply. |
| ESPHome sensor driver | **Native `sen5x` platform** (esphome.io/components/sensor/sen5x/) — supports SEN50/54/55 directly over I2C. No custom component needed for the sensor itself. |
| Field indicator | RGB LED (Greekcreit kit, Plastic Box) — PM2.5 threshold color: green (<12 µg/m³), yellow (12–35), red (>35) |
| Power | EEMB LiPo pouch 603449 1100mAh (Bag 7) + TP4056 charging module (Bag 8, its boost stage unused) + MCP1700-3302E/TO LDO (Bag 32, on hand, same part validated on the CARD-0026/CARD-0070 rig) — direct LiPo-to-LDO architecture per `JCTsh-Build-Standards.md` §2.14 point 7, decided 2026-08-19 (**not** the boost-then-buck pattern originally planned in Phase 1 — see Power Budget note below for why this matters for real-world runtime). LDO `VIN` taps the battery+ node in parallel with TP4056's `BAT+` input, not fed from the boost module's output; LDO `VOUT` → ESP32 `3V3` pin directly. TP4056 continues managing charging/solar input unchanged — only its boost/`OUT+`/`OUT-` pads go unused. The Adafruit #5964 adapter's own onboard 5V boost (separate, self-contained, takes 3.3V logic in) is unaffected by this change — it never depended on the system-level boost module. |
| SEN55 power gate | **Dropped, 2026-08-21 (Step 6 decision).** SEN55 is hard-wired always-on (adapter `GND` directly to common ground — the Step 4 "bypass jumper" is now the permanent design, not a workaround) whenever the device itself has power. No BC547B/gate transistor, no GPIO27 involvement. Reasoning: Sensirion's own "Reduced Power Operation for SEN5x" doc recommends I2C mode-switching (Measurement ↔ RHT/Gas-Only) as the primary duty-cycle power-saving mechanism, not physically cutting power — and the inline power switch below already covers true full-off for storage/transport. That leaves no real use case for a dedicated gate, and eliminates the low-side-vs-high-side reliability question Step 4's diagnostic session surfaced (see CARD-0012 kanban notes for the full trail). Duty-cycling is now a Step 8 firmware task (I2C mode-switching), not a Step 6 hardware task. |
| Inline power switch | Gebildet SS12D10 slide switch (SPDT, wired as SPST — Bag 23, on hand) wired **directly into the battery+ path**, ahead of the TP4056/LDO, no GPIO involved. True hard off for transport/storage — decided 2026-08-19 directly from CARD-0181's hiking-monitor finding (a GPIO-tapped switch only sets a mode flag, it doesn't cut power). Kept deliberately separate from dock-detect: dock-detect answers "which firmware mode," this switch answers "is the device powered at all." Pre-satisfies `JCTsh-Build-Standards.md` §1.7 before enclosure design even starts. |
| Custom firmware component | Required for onboard flash logging + WiFi replay only (SEN55 reading itself uses the native platform above) — reuse `components/hiking-monitor/hiking_logger.h`, rename prefix per its own template instructions |
| Perfboard | Chanzon FR4, size TBD — measured in Step 3 below (SEN55 + adapter footprint is the dominant constraint) |
| Enclosure | **Deferred to a follow-on card** — clip case + carabiner, 3D-printed. **SEN55 mounts externally (decided 2026-08-20)**, 3M double-sided foam tape (on hand, Plastic Box) to the enclosure's smooth outer surface, cabled to the internal Adafruit #5964 adapter via the existing 100mm JST-GH cable through a small pass-through hole — no custom intake/exhaust venting needed, the SEN55's own sealed metal housing/fan shield handles its own airflow. See Future Enhancement section and `JCTsh-air-quality-monitor-phase1.md`'s Carry and Enclosure section. |

**GPIO assignments:**
| GPIO | Assignment |
|---|---|
| GPIO21 | I2C SDA (SEN55 via Adafruit adapter) — blue |
| GPIO22 | I2C SCL — yellow |
| GPIO34 | `battery_v` ADC — voltage divider midpoint (input-only pin, ADC1), 100kΩ/100kΩ divider, same pattern as hiking-monitor. **Corrected 2026-08-19** — this row previously said 68kΩ/68kΩ, but hiking-monitor's actual `wiring.md` uses 100kΩ/100kΩ for its battery divider; 68kΩ/100kΩ is the *dock-detect* divider, a different one (see the GPIO32 row below, unaffected). |
| GPIO32 | Dock-detect divider — same 68kΩ/100kΩ pattern and pin as hiking-monitor's `IN+` divider (USB present → HIGH, absent → LOW) |
| GPIO27 | **Unused** — previously reserved for the SEN55 power-gate transistor base, dropped 2026-08-21 (see Hardware Context table above) |
| GPIO18 | RGB LED — Red |
| GPIO19 | RGB LED — Green |
| GPIO23 | RGB LED — Blue |

**Step 1 — resolved 2026-08-19 (Joseph):** dock-detect-only for firmware mode-switching, confirmed — no GPIO-based manual mode switch. Separately, a real inline power switch was added to the design (see Hardware Context table above) purely for transport/storage true-off, wired directly into the battery path with no GPIO involvement at all — so it doesn't appear in the GPIO table below and doesn't affect mode-switching logic. This mirrors the design lesson from CARD-0181 (hiking-monitor's own switch only sets a GPIO mode flag, never actually cutting power) — the two concerns (which firmware mode vs. is the device powered) are kept deliberately separate here rather than repeating that conflation.

**I2C addressing:** SEN55 only (0x69, fixed) — no other I2C devices on this bus, no conflicts, no bus-sharing concerns.

**Power budget — recalculated for the LDO swap, 2026-08-19:** `JCTsh-air-quality-monitor-phase1.md`'s existing estimate (~13-15mA average → ~58-68 hours) totals SEN55 duty-cycled draw + SEN55 idle + ESP32 light-sleep average, but — same blind spot CARD-0026 found on hiking-monitor — never included the boost module's *own* quiescent current. Hiking-monitor's real measured figure for that combined TP4056+boost module was ~22.6mA, continuous, regardless of sleep state. Had this build kept the originally-planned boost module, real-world runtime would likely have landed closer to 1100mAh ÷ (~14mA + ~22.6mA) ≈ **~30 hours** — notably worse than the Phase 1 doc's stated 58-68h, not because the consumer-side estimate was wrong, but because the regulator's own overhead was never in the total.

With the LDO swap (MCP1700's own quiescent draw is ~1.6µA — negligible), that hidden overhead goes away entirely. Runtime should land close to what the original consumer-side budget alone implies: 1100mAh ÷ ~13-15mA ≈ **~73-85 hours (roughly 3-3.5 days)** of continuous field-mode operation — comfortably beyond any realistic hike duration, and a real, concrete benefit of the LDO decision beyond just matching the standing §2.14 point 7 recommendation. Treat both figures as estimates pending Step 6's actual bench-measured current draw, same as hiking-monitor's own numbers were corrected from calculated to measured.

---

## Network / Integration Architecture

```
SEN55 (I2C 0x69, via Adafruit #5964 adapter) ── ESP32 DevKitC-32 (ESPHome)
                                                      │
                        Field-mode duty-cycle log to flash: always running
                        Dock-detect HIGH (home dock, USB charging, or solar):
                          triggers a bounded-window WiFi attempt (home WiFi or
                          Pixel hotspot) in the background — logging keeps
                          running until that attempt actually succeeds
                                                      │ MQTT (once connected)
                                                      ▼
                              Mosquitto broker (jctsh.duckdns.org:8883, TLS)
                                         │
                                         └──► Node-RED
                                                │ routes /log → Python log server
                                                │ watchdog on /heartbeat
                                                │ wildcard /data handler → Google Sheets
```

**MQTT topics:**
- `jctsh/components/air-quality-monitor/data`
- `jctsh/components/air-quality-monitor/log`
- `jctsh/components/air-quality-monitor/heartbeat` (home mode only)

**No SmartThings, no Home Assistant integration** — no real-time state to expose (per Phase 3 decision).

**Timeout policy — superseded 2026-08-20** (see `JCTsh-air-quality-monitor-phase1.md`'s JCTsh Integration table for the full decision history): the original 2026-07-09 decision assumed home mode only happens docked/charging at home, USB-powered — false, since solar and field USB charging share the dock-detect (`IN+`) signal with the home dock, so dock-detect can go HIGH mid-hike, on battery, with no home WiFi in range.

Current design: field duty-cycle logging runs unconditionally, independent of dock-detect state. Dock-detect HIGH only triggers a background WiFi connection *attempt* against both configured networks (`JCTnet1` and the Pixel hotspot — see the new `hotspot_ssid`/`hotspot_password` secrets), bounded to a target 2-minute window before disabling the WiFi radio (`wifi.disable`) rather than retrying indefinitely, then re-attempting periodically (target 15–20 minutes) for as long as dock-detect stays HIGH. No cap on the number of periodic retry cycles — only on how long each individual attempt window runs. Logging only pauses once WiFi **and** MQTT actually connect, at which point the device replays the SPIFFS backlog and switches to publishing live, exactly like hiking-monitor's home mode. Implementation (interval/lambda structure for the attempt window and radio disable/enable) is a Step 4/Step 8 task, not specified further here. Still explicitly does not inherit hiking-monitor's `wifi.ap:` + `reboot_timeout` bug interaction (CARD-0045) — confirm in Step 4 whether an `ap:` fallback block is actually needed before including one.

---

## Step 0 — Read Build Standards

**Claude Code does:**
Read `JCTsh-Build-Standards.md` in full. This build touches: §2 ESPHome standards (boilerplate, MQTT publishing patterns, GPIO assignment, deep-sleep/duty-cycle sequencing per §2.13), §2.10 onboard flash logging (field mode pattern), §2.14 battery safety standards, §3 MQTT standards, §4 observability standards, §8 LED indicator standards (RGB threshold pattern). Also read `components/hiking-monitor/` in full — this build must match its firmware pattern, not re-derive it. State explicitly which standards apply before writing any code or config.

**Joseph confirms:**
Acknowledged — proceed.

---

## BENCH PHASE

All steps in this section are performed on the workbench, on breadboard first per JCTsh-Build-Standards.md §1.2, before any perfboard transfer.

## Step 1 — Confirm mode-switching design

**Resolved 2026-08-19.** Dock-detect-only for firmware mode-switching, confirmed — no GPIO-based manual mode switch. A real inline power switch was added separately for transport/storage true-off (wired directly into the battery path, no GPIO involved) — see Hardware Context above for the full reasoning. GPIO table unaffected by the switch addition.

---

## Step 2 — Create MQTT account and secrets.yaml

**Claude Code does:**
Generate a strong random password, document the `mosquitto_passwd` command for the `air-quality-monitor` account (JCTsh-Build-Standards.md §2.11), create `secrets.yaml.template`, confirm `.gitignore` coverage.

**Joseph does:**
Run the account-creation command on the Pi; populate `secrets.yaml`.

**Joseph confirms:**
Account created, secrets file in place and untracked by git.

---

## Step 3 — Breadboard wiring

**Claude Code does:**
Create `wiring.md` and `ESP32-project-pins.md` (full 38-pin table) covering: I2C bus to the SEN55/adapter, the BC547B SEN55 power-gate circuit, the `battery_v` divider, the dock-detect divider (matching hiking-monitor's exact values), the MCP1700 LDO wiring (`VIN` to battery+ node in parallel with TP4056's `BAT+`, `VOUT` to ESP32 `3V3` directly, per the CARD-0026/CARD-0070 rig pattern), and the inline power switch (in-line on the battery+ path, ahead of both the TP4056 and the LDO tap point). Also document the perfboard footprint measurement procedure in `wiring.md` (SEN55 module + Adafruit adapter physical dimensions, laid out to determine minimum board size) — **for use at Step 9, not this step** (superseded 2026-08-20: measuring footprint this early was premature, before there's a real perfboard layout to size against; moved to where it's actually actionable).

**Joseph does:**
Wire on breadboard, powered via USB.

**Joseph confirms:**
Wiring complete.

**Claude Code does:**
Record the confirmed perfboard size in this doc and the BOM.

---

## Step 4 — ESPHome base config and SEN55 validation

**Claude Code does:**
Write the initial `air-quality-monitor.yaml` — standard boilerplate (§2.8), I2C bus, native `sen5x` sensor platform, standard `on_connect`/heartbeat MQTT patterns (§2.7). `wifi: networks:` lists both `wifi_ssid`/`wifi_password` and `hotspot_ssid`/`hotspot_password` (added 2026-08-20 — see Timeout policy above), matching hiking-monitor's pattern. `mqtt:` block uses `port: 8883` with `certificate_authority: !secret mqtt_ca_cert` (TLS, matching hiking-monitor's CARD-0003 config) — not plaintext 1883, now that `mqtt_broker` points at `jctsh.duckdns.org`. Resolve Step 1's mode-switching design into the `wifi:` block — per the timeout policy above, do not include a `wifi.ap:` fallback unless Step 1 established a real need for it.

**Joseph does:**
Flash via USB. Confirm PM/VOC/NOx readings on the log dashboard.

**Joseph confirms:**
All SEN55 fields reporting plausible values. **Met 2026-08-21 10:33 MST** — after a real multi-hour diagnostic session (see CARD-0012's kanban entry for the full trail): a firmware bug (`sen5x:` block missing its `id:`, referenced by `on_boot`) was found and fixed first, then an extensive hardware fault chase on the SEN55 power-gate transistor circuit (BC547B) — every individual component/connection checked out (resistor, base voltage, VIN, transistor swap, relocation, Collector/Emitter continuity) yet the circuit still wouldn't reliably power the sensor, eventually traced to an intermittent breadboard contact via the adapter's own power LED, though not fully/durably resolved. **Confirmed via the bypass jumper configuration** (adapter `GND` wired directly to common ground, bypassing the transistor entirely) — this is a legitimate, temporary substitute for the gate circuit specifically for the purpose of validating the SEN55/adapter/I2C wiring itself, which is genuinely proven now. The gate circuit itself remains unresolved and is deferred to Step 6, which now also inherits a real open design question (low-side vs. high-side switching) surfaced during tonight's debugging — see that step's updated notes.

---

## Step 5 — RGB LED threshold logic

**Claude Code does:**
Implement the PM2.5 → RGB color mapping (green <12, yellow 12–35, red >35 µg/m³) on GPIO18/19/23.

**Joseph does:**
Verify LED color changes correctly across the three PM2.5 ranges (can simulate with a known particulate source, or verify logic against manually-set test values).

**Joseph confirms:**
All three color states verified. **Green state met 2026-08-21 10:50 MST** — deployed cleanly, live PM2.5 at 2.0 µg/m³ correctly showing green. **Yellow and red states met 2026-08-21 11:53 MST** — verified via a boot-time color-hold sequence (solid Yellow 3s, solid Red 3s, added permanently rather than as a one-off test — Joseph's preference, confirms both colors on every boot without needing a real particulate source in range). Step 5 fully closed.

---

## Step 6 — SEN55 power-gate transistor bench test — DROPPED and CLOSED, 2026-08-21

**Design decision made and physical breadboard confirmed to match. Step 6 is closed.**

Step 4's diagnostic session had left this step inheriting a real open design question — low-side (BC547B) vs. high-side (P-FET) switching — after the BC547B gate circuit failed to reliably power the SEN55 across multiple boot cycles (see CARD-0012 kanban entry for the full trail). Revisiting *why* a gate was wanted at all resolved the question a different way:

- **Routine duty-cycling** (the original motivation — SEN55 draws ~63mA in Measurement mode, too much to leave running the whole hike): Sensirion's own "Reduced Power Operation for SEN5x" doc recommends I2C mode-switching (Measurement ↔ RHT/Gas-Only) as the primary power-saving mechanism, not physically cutting power. That's a Step 8 firmware task against the native `sen5x` platform, not a hardware gate.
- **True full-off** (storage/transport between hikes): already covered by the inline power switch (Hardware Context table, wired directly into the battery+ path, decided Step 1) — that's a whole-device cutoff, no SEN55-specific gate needed.

With both real use cases already covered elsewhere, there's nothing left for a dedicated GPIO27 gate to do — and dropping it also eliminates the low-side/high-side reliability question outright, along with the exact failure mode (marginal GND-return connection silently breaking I2C) that caused Step 4's multi-hour diagnostic session. The former "bypass jumper" (adapter `GND` directly to common ground) is now the permanent design, not a workaround — reflected in `air-quality-monitor.yaml`, `wiring.md`, and the Hardware Context/GPIO tables above. GPIO27 is unused. BC547B/BS250 stock remains on hand, unused by this build.

**Claude Code does:**
Update all build docs to remove the gate-transistor design (done — this entry, Hardware Context table, GPIO table, `air-quality-monitor.yaml`, `wiring.md`).

**Joseph does:**
Update the physical breadboard to match: remove the BC547B transistor, its 1kΩ base resistor, and its 10kΩ base pull-down resistor from the circuit entirely (not just set aside — they were already "set aside, not removed" once before, during Step 4, which is part of how the board ended up in an ambiguous state). Confirm the SEN55 adapter's `GND` pin has a solid, direct connection to the common ground rail — not the original diagnostic-session jumper left in place by chance, but a wire placed deliberately as the permanent design. GPIO27 (pin 11) should have nothing connected to it.

**Joseph confirms:**
**Met 2026-08-21 12:50 MST.** Transistor and both resistors physically removed from the breadboard; SEN55 `GND` verified as a direct, solid connection to common ground; GPIO27 confirmed unconnected. Step 6 closed.

---

## Step 7 — LiPo polarity check and power validation

**Claude Code does:**
Document the JST polarity verification procedure (same requirement as hiking-monitor) before first battery connection. Include confirming the LDO's `VOUT` reads a clean 3.3V under load and the inline power switch actually breaks the circuit in both positions (measure for zero voltage/current downstream when off, not just "the LED goes out"). Note that the inline switch is what satisfies `wiring.md`'s "never power from USB and the LDO at the same time" caution — switching it off removes the LDO's `VIN` entirely, equivalent to unplugging it, so USB flashing just requires the switch off rather than any physical disconnect. This isn't a one-time Step 7 concern: once the battery/LDO are wired in here, it applies to every subsequent USB connection for the rest of the build and field life of the device — Step 8's and Step 9's USB flashes below, and any future re-flash over USB, all need the switch off first.

**Also added 2026-08-21: dock-detect and battery-divider raw checks belong here, not Step 8.** Both dividers were wired at Step 3 and referenced in firmware since Step 4, but neither has been checked on its own — dock-detect's only exercise so far would be buried inside Step 8's much more complex WiFi-attempt/retry logic, and the battery divider is still reading off the 3.3V rail placeholder rather than the real LiPo. Step 7 is when the real battery goes in and USB gets connected/disconnected anyway, so it's the cheap, isolated place to confirm both raw signals before Step 8 adds behavior on top of them.

**Joseph does:**
Verify polarity, connect the EEMB LiPo pouch to the TP4056 module, confirm normal charge behavior (TP4056 side) and normal 3.3V power delivery via the LDO (not the boost module's old 5V→onboard-regulator path). Confirm the inline power switch cuts power cleanly in both directions. **Battery divider:** first **rewire R1's top leg from the 3.3V rail placeholder to the real LiPo `BAT+` (post-switch)** — per `wiring.md`'s Battery Voltage Divider Wiring section, this move was always deferred to "when the power system is integrated," which is now — then compare the `battery_v` sensor's logged value (heartbeat or serial log) against a multimeter reading taken directly at the battery terminals to confirm they're close (the 100kΩ/100kΩ divider's `multiply: 2.0` filter should reconstruct the true battery voltage). **Dock detect:** connect and disconnect USB (or briefly bridge the divider's input node to 3.3V, if easier) while watching the serial log during an `esphome run` session — confirm `dock_detect`'s logged state flips HIGH/LOW as expected, independent of any WiFi-attempt behavior (that's Step 8's concern, not this check's).

**Joseph confirms:**
Polarity correct, battery connected, LDO delivering clean 3.3V, inline switch verified to actually cut power (not just visually "off"), everything functioning normally. Battery divider reading confirmed close to a direct multimeter measurement. Dock-detect confirmed flipping HIGH/LOW correctly in the serial log on USB connect/disconnect.

---

## Step 8 — Field/home mode duty-cycle and WiFi replay firmware

**Claude Code does:**
Implement the field-mode duty-cycle logging via **I2C mode-switching** (Measurement ↔ RHT/Gas-Only, per Step 6's 2026-08-21 decision — not physical power-gating, since SEN55 is now hard-wired always-on). Reconcile timing against Sensirion's own guidance surfaced during that decision: a **30–60s warm-up** is recommended after leaving RHT/Gas-Only mode for good PM accuracy (8s is documented as an absolute floor, not a target) — longer than the Phase 1 power budget's original ~10s active window per 2-minute cycle, so confirm the actual cycle timing against this before locking it in, not the old assumption. Reading via the native `sen5x` platform, logged to flash via the adapted `hiking_logger.h` pattern — **this runs unconditionally, independent of dock-detect state** (superseded 2026-08-20 Timeout policy decision above; deviates from hiking-monitor's exact pattern, which stops field logging as soon as dock-detect goes HIGH — call this deviation out explicitly in code comments so a future reader doesn't assume it's identical).

Dock-detect HIGH triggers a background WiFi connection attempt (against both `JCTnet1` and the hotspot networks) via an interval/lambda: bounded to a ~2-minute attempt window, then `wifi.disable()` if not connected rather than retrying indefinitely, then re-enable and retry roughly every 15–20 minutes for as long as dock-detect stays HIGH. No cap on the number of these periodic cycles.

Once WiFi **and** MQTT actually connect (whether via `JCTnet1` at home or the hotspot in the field), switch to home-mode behavior: replay the SPIFFS backlog to MQTT using original timestamps, then publish new readings live instead of buffering (per hiking-monitor's exact pattern from that point on). Include the 5-minute heartbeat in home mode only.

**Joseph does:**
Switch the inline power switch off before connecting USB (battery/LDO are wired in as of Step 7 — see that step's note), then flash via USB, simulate a field session (undock, wait through a few duty cycles) then redock and confirm replay. Additionally test the new field-WiFi-attempt path: with the device undocked and running on battery, trigger dock-detect (e.g. connect USB or solar) with no `JCTnet1`/hotspot in range, and confirm logging continues uninterrupted through at least one full attempt-window-then-backoff cycle rather than stalling.

**Joseph confirms:**
Field-mode logging and home-mode replay both work as expected, matching hiking-monitor's proven behavior — plus the new bounded-retry behavior confirmed not to interrupt logging or get stuck when no network is reachable.

---

## Step 9 — Perfboard footprint measurement and transfer

**Claude Code does:**
N/A until Joseph reports the footprint measurement below — then create `perfboard-layout.md` using it.

**Joseph does:**
**First, measure the footprint** (moved here 2026-08-20 from Step 3, where it was premature): follow `wiring.md`'s Perfboard Footprint Measurement Procedure — physically measure the SEN55 module + Adafruit #5964 adapter, lay out the full component set, and confirm whether the standard 5×7cm Chanzon FR4 board (Bag 9) is sufficient. **Working assumption: the same 5×7cm size hiking-monitor uses will probably work here too** (`hiking-monitor/perfboard-layout.md` confirms that's what it used) — treat the measurement as confirming/adjusting that assumption, not starting from zero. Report the result back.

Then transfer the validated breadboard circuit to perfboard: ESP32 + SEN55/adapter + BC547B gate + RGB LED + both dividers. Continuity-check before power-on. Switch off before connecting USB for any post-transfer USB flash/debug, same as Step 8.

**Joseph confirms:**
Footprint measured, perfboard size confirmed (or corrected from the 5×7cm assumption); perfboard build complete, device boots and operates identically to the breadboard version.

---

## Step 10 — Heartbeat/watchdog registration

**Claude Code does:**
Confirm the existing Node-RED watchdog wildcard subscription and `/data` wildcard handler catch this device automatically — no new flows needed.

**Joseph does:**
Confirm in the Node-RED editor and Google Sheets.

**Joseph confirms:**
Device appears in the watchdog's tracked component list; readings appearing in the Environmental Data sheet after a simulated home-mode sync.

---

## Bench Phase Complete — Install Phase Begins

All bench steps above are confirmed complete. The device has been:
- Fully wired and perfboard-built with the SEN55/adapter, power-gate transistor, RGB LED, and both dividers
- Validated on USB power and on battery power
- Running field-mode duty-cycle logging and home-mode WiFi replay, matching hiking-monitor's proven pattern
- Integrated with the log dashboard, watchdog, and Google Sheets

Do not proceed to any install/carry-case work until every bench step above is confirmed complete.

---

## INSTALL PHASE

**Deliberately not detailed in this instruction set** — same split as hiking-monitor (CARD-0009) and remote-temp-sensor-01. Enclosure/carry-case design depends on measurements and confirmations this bench phase produces (actual perfboard footprint, confirmed power-gate transistor behavior, confirmed mode-switching design) that don't exist yet.

See "Future Enhancement" below.

---

## Future Enhancement — Clip Case Enclosure

**Planning started 2026-08-20** — `air-quality-monitor-enclosure-plan.md` captures what's already decided and the open questions still needing physical measurement, following the same process used for `hiking-monitor-enclosure-plan.md`/`hiking-monitor-enclosure-instructions.md`. CAD work itself does not begin until the bench phase below is confirmed complete.

Once the bench phase above is complete, open a follow-on planning pass covering:
- 3D-printed clip case with carabiner attachment, independent of hiking-monitor's own enclosure
- ~~Air intake/exhaust port placement for the SEN55 fan~~ **Moot — resolved 2026-08-20.** SEN55 mounts externally via 3M double-sided foam tape to the enclosure's smooth outer surface (its own sealed metal housing/fan shield handles airflow directly from ambient, not through the JCTsh enclosure), cabled to the internal Adafruit #5964 adapter via the existing 100mm JST-GH cable. No custom venting to design; the low-confidence Sensirion orientation research no longer needs re-verification for this build.
- **New:** small cable pass-through hole for the SEN55's JST-GH cable, sized/positioned so the sensor sits flush against the exterior mounting point — same pattern as the solar JST exit hole
- White ASA for final print (corrected 2026-08-20 from Phase 1's original PETG call — matches hiking-monitor's own upgrade for Tucson UV/heat resistance) to minimize solar gain
- Micro USB charging port and external JST solar port placement (SUNYIMA panel, backpacking use)
- Screw/fastening hardware — confirm actual length needed once enclosure dimensions exist, same caution as remote-temp-sensor-01 and hiking-monitor (don't assume on-hand kit screws are long enough)

## Future Enhancement — Deferred Features (from Phase 1)

| Feature | Status |
|---|---|
| Bluetooth/real-time data share to hiking monitor display | Evaluated and deferred — added field-failure modes not justified by the data value |
| NOx threshold LED indicator | Deferred — VOC index covers field awareness adequately; NOx is more useful in post-hike Sheets analysis |
| Solar panel mount/clip design | Deferred to the enclosure design phase above |
| Disable onboard power LEDs (ESP32 red PWR LED, Adafruit #5964 adapter green "on" LED) | Deferred, for consideration later. Adapter LED has a documented cuttable trace on the back silkscreened "LED" (learn.adafruit.com/adafruit-sen54-or-sen55-adapter-breakout/pinouts) — cut with a hobby knife, reversible by re-bridging with solder. ESP32 DevKitC-32's red PWR LED has no such jumper — disabling it means desoldering the series resistor (or the LED itself), real SMD work for a few mA of savings. Revisit at Step 7 (battery install) or Step 9 (perfboard transfer), when the board is already being handled directly. |

---

## Notes for Claude Code

- Step 0 is mandatory: read `JCTsh-Build-Standards.md` in full and `components/hiking-monitor/` in full before writing any code — this build must match hiking-monitor's pattern, not re-derive it
- SEN55 uses ESPHome's native `sen5x` platform — do not write a custom component for the sensor itself
- Custom component is still needed for onboard flash logging + WiFi replay — adapt `components/hiking-monitor/hiking_logger.h`, do not rewrite from scratch
- Do not copy hiking-monitor's `wifi.ap:` fallback block without confirming it's actually needed (CARD-0045) — if included, be aware `reboot_timeout` may not function as expected
- Log format: JSON to `jctsh/components/air-quality-monitor/log`
- `lat`/`lon` are always `null` in this payload — no GPS hardware, timestamp correlation with GaiaGPS/hiking-monitor happens post-hike
- `rssi_dbm` is 0 for field-mode readings (no WiFi at time of logging) — same convention as hiking-monitor
- MQTT account: create dedicated `air-quality-monitor` Mosquitto account before first flash
- Add new account to credentials table in root `CLAUDE.md`
- Record new device IP, hostname, and MAC in `jctsh-network.md` once ready to flash
- Update `jctsh-parts-inventory.md` at the end of the bench phase — deduct all used parts, record the Step 6 measured power-gate current
- Bench-first: all bench steps must be confirmed complete before any install-phase work begins
