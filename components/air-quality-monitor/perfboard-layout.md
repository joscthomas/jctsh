# Air Quality Monitor — Perfboard Layout (Step 9)

## Session status, 2026-09-14 (paused here for the day)

- **Continuity checks 1-30: all done.** 28 clean passes, 2 (resistance-mode divider readings) deferred to live checks due to hand-probe repeatability, not a real fault. **7 missing solder bridges found and fixed** along the way — a real, meaningful yield.
- **Post-continuity power-on checks 1-3: done, all passed** (switch-off isolation both halves, switch-on regulation, TP4056 charge LED). Bonus: firmware's own `battery_v` reading (4.12V) matched a direct multimeter reading almost exactly, incidentally also satisfying check 6.
- **Check 4 (dock detect): both halves now confirmed.** Docked half confirmed (indirectly, from earlier); undocked half's firmware bug (MQTT's own independent reconnect loop, not the WiFi gate) is flashed and live-verified 2026-09-16 — see its own entry below.
- **Check 5 (Intent switch): ON case confirmed 2026-09-16; OFF case parked** on a debug-UART adapter fault (see check 5's own entry) — not a wiring or firmware issue, isolation narrowed to the adapter module itself or a connection internal to it.
- **Checks 6-7 (battery divider sanity, full boot): both done, 2026-09-16** — via the docked/MQTT path once the debug UART became unavailable. See their own entries below.
- **Step 9 checklist is now complete except check 5's parked OFF-case confirmation.**
- **Logged to `tos/kanban-board.md`** — full session write-up added to CARD-0012.

## Status

Footprint measurement not yet formally reported/recorded here — physical perfboard transfer and wiring are already complete as of this session (2026-09-14), and continuity testing is in progress. Board-size confirmation (working assumption: the same 5×7cm Chanzon FR4 hiking-monitor uses) can be filled in once reported, per `air-quality-monitor-claude-code-instructions.md` Step 9.

Full wiring reference (pin assignments, wire colors, per-signal detail) lives in `wiring.md` — that's the authoritative as-built source. This file is the Step 9 continuity-check procedure, kept here so it survives past one bench session, matching `components/hiking-monitor/perfboard-layout.md`'s own convention.

---

## Continuity Check Procedure

**Before starting: battery disconnected, power switch off, nothing plugged into USB.** DMM in continuity (beep) mode unless a row says "Resistance."

**Testing methodology (2026-09-14):** all soldering is on the underside of the perfboard; every component (ESP32, Pololu, TP4056, resistors, switches, LED, adapters) sits on top. **Probe directly at the component's own pin/lead on the top side, not at a solder joint on the underside.** This is both easier (no need to flip the board or hunt for a specific joint) and strictly more thorough — it validates the complete path (component lead → solder joint → trace → next component lead) in one probe, rather than just the joint itself. Test 2 below already caught a real missing solder bridge this way. Every "pad"/"pin"/"leg" reference in the tables below means the component's own lead where it's accessible from the top, not the underside copper.

### Pre-power short check

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 0 | Pololu `VIN` pin | Any GND rail point | Resistance | High/open — no beep | PASS |

### Ground rail

**The perfboard has one physical GND bus rail. ESP32 pin 38 is the sole ESP32 pin feeding it** — confirmed 2026-09-14 (see `wiring.md`'s GND Rail note). Pins 32/14/18 are not used as GND taps on this build; pin 18 is confirmed **not** actually continuous with ground despite being silkscreened GND (a real board finding, documented in `wiring.md`/`ESP32-project-pins.md`, but moot for this build since it's unused).

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 1 | ESP32 pin 38 | Perfboard GND rail (any point) | Continuity | Beep | PASS |
| 2 | GND rail (via ESP32 pin 38) | Pololu GND pin | Continuity | Beep | PASS — found and fixed a missing solder bridge first |
| 3 | GND rail (via ESP32 pin 38) | TP4056 `VOUT−` pin | Continuity | Beep | PASS |
| 4 | GND rail (via ESP32 pin 38) | R2 bottom leg (battery divider) | Continuity | Beep | PASS |
| 5 | GND rail (via ESP32 pin 38) | R4 bottom leg (dock-detect divider) | Continuity | Beep | PASS |
| 6 | GND rail (via ESP32 pin 38) | SS12D10 terminal 2 (Intent switch, black wire) | Continuity | Beep | PASS |
| 7 | GND rail (via ESP32 pin 38) | RGB LED module `-` pin | Continuity | Beep | PASS |
| 8 | GND rail (via ESP32 pin 38) | SEN55 adapter `GND` pin | Continuity | Beep | PASS |
| 9 | GND rail (via ESP32 pin 38) | Debug UART adapter GND (orange wire) | Continuity | Beep | PASS |

### Power path — battery through switch to the Pololu

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 10 | LiPo `BAT+` tie point | TP4056 `BAT+` pin | Continuity | Beep (always tied, upstream of switch) | PASS |
| 11 | LiPo `BAT+` tie point | BK-1208 power switch, one lead | Continuity | Beep | PASS |
| 12 | BK-1208 power switch, other lead | Pololu `VIN` pin | Continuity, tested both switch positions | Switch ON: beep. Switch OFF: no beep (confirms the switch actually gates this path, not just static continuity) | PASS — both positions confirmed |
| 13 | Pololu `VOUT` pin | ESP32 pin 1 (3V3) | Continuity | Beep | PASS |
| 14 | ESP32 pin 1 (3V3) | SEN55 adapter `VIN` pin | Continuity | Beep | PASS |

### Battery voltage divider (Green dot — R1 + R2, per `wiring.md`'s Battery Voltage Divider Wiring section)

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 15 | Pololu `VIN` node (post-switch) | Battery divider (green dot) R1 top leg | Continuity | Beep | PASS |
| 16 | Battery divider (green dot) R1/R2 midpoint | ESP32 pin 5 (GPIO34) | Continuity | Beep | PASS — found and fixed 3 more missing solder bridges first |
| 17 | Pololu `VIN` node | GND rail | Resistance | ~200kΩ (R1+R2 in series) | **Not resolved as a stable number, and treated as not blocking.** Two measurement rounds gave wildly different, internally-inconsistent results (178k/68.3k/94.4k, then 83.4k/69.8k/67.8k for VIN→GND / VIN→mid / mid→GND respectively) — not a real fault (a genuine short/bad joint gives a wrong-but-repeatable number), but hand-probe contact variability on small resistor leads. Continuity (tests 15/16) and color-band value confirmation (both R1/R2 = 100kΩ ±1%) already validate what actually matters; the real functional check is post-continuity check #6 (live `battery_v` sensor vs. direct multimeter reading at the battery, under real power) — deferred to there rather than chased further here. |
| 18 | Battery divider (green dot) R1/R2 midpoint | GND rail | Resistance | ~100kΩ (R2 only) | See test 17's note — not a stable/trustworthy reading across repeats, deferred to the live post-continuity divider check instead. |

### Dock-detect divider (Blue dot — R3 + R4, per `wiring.md`'s Dock Detect Wiring section)

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 19 | TP4056 `IN+` pin | Dock-detect divider (blue dot) R3 top leg | Continuity | Beep | PASS |
| 20 | Dock-detect divider (blue dot) R3/R4 midpoint | ESP32 pin 7 (GPIO32) | Continuity | Beep | PASS |
| 21 | TP4056 `IN+` pin | GND rail | Resistance | ~168kΩ (R3+R4 in series) | Deferred — same hand-probe repeatability issue found on tests 17/18; real validation is post-continuity check #4 (live dock-detect HIGH/LOW). Values confirmed by color band instead (see result of test 22). |
| 22 | Dock-detect divider (blue dot) R3/R4 midpoint | GND rail | Resistance | ~100kΩ (R4 only) | Deferred, same reason as test 21 — but R3 and R4 confirmed correct by color band: R3 = blue-grey-black-red-brown = 68kΩ ±1% (matches expected), R4 = 100kΩ (same markings as the already-confirmed battery-divider resistors). |

### Intent switch

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 23 | SS12D10 terminal 1 (blue wire) | ESP32 pin 11 (GPIO27) | Continuity | Beep | PASS |

### I2C bus (SEN55 adapter)

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 24 | SEN55 adapter `SDA` pin | ESP32 pin 33 (GPIO21) | Continuity | Beep | PASS |
| 25 | SEN55 adapter `SCL` pin | ESP32 pin 36 (GPIO22) | Continuity | Beep | PASS |

### RGB LED (KY-016)

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 26 | LED module `R` pin | ESP32 pin 30 (GPIO18) | Continuity | Beep | PASS — found and fixed 2 more missing solder bridges first |
| 27 | LED module `G` pin | ESP32 pin 31 (GPIO19) | Continuity | Beep | PASS |
| 28 | LED module `B` pin | ESP32 pin 37 (GPIO23) | Continuity | Beep | PASS |

### Debug UART (transmit-only — confirm the VCC pin is NOT connected)

| # | Probe A | Probe B | Mode | Expected | Result |
|---|---|---|---|---|---|
| 29 | ESP32 pin 28 (GPIO17) | Adapter RXD (yellow wire) | Continuity | Beep | PASS — found and fixed 1 more missing solder bridge first |
| 30 | CP2102 USB to TTL module `VCC`/`3V3` pin | Pololu `VOUT` (= ESP32 pin 1, 3V3) | Visual (no probe needed) | **No connection at all** — must be floating | PASS — only 2 wires exist to the module (orange GND, yellow signal/RXD), no third wire to VCC/3V3 present |

---

## Post-continuity power-on checks (Step 9 → Step 7 re-verification)

Once every row above passes, before connecting the battery for real:

1. **Switch-off isolation** — with the battery connected and switch OFF, confirm zero voltage at the Pololu `VIN` pin, both with TP4056's USB unplugged and plugged in.
   - **1a (USB unplugged): PASS — 0V.** Battery baseline confirmed healthy at 4.12V.
   - **1b (USB plugged into TP4056): PASS — 0.4V.** Not a clean 0V, but far from the ~4.1V (near-full-battery) reading that would indicate a reproduction of CARD-0198's original pre-rewire backfeed bug — consistent with minor floating-node leakage, not a wiring regression. Not enough to power the Pololu or ESP32.
2. **Switch-on regulation** — switch ON, confirm Pololu `VOUT` reads a clean 3.3V under load (device booted, WiFi/SEN55 active at some point during the check).
   - **PASS — VOUT = 3.3V** (with TP4056 USB left plugged in from check 1b). VIN separately confirmed ~4V, matching battery voltage as expected.
3. **TP4056 charge LED** — confirm it still indicates charging with the switch OFF and USB connected (proves charging doesn't depend on switch position, per the Inline Power Switch rewiring).
   - **PASS — green lit, red dim, switch OFF.** LED color convention not documented anywhere in the repo (checked hiking-monitor's wiring.md too, same physical module) — likely standard TP4056 red=charging/green=complete, consistent with the 4.12V battery reading being near a full ~4.2V charge. What actually matters for this check is confirmed either way: the LED shows an active charge-related state with the switch off, proving charging doesn't depend on switch position.
4. **Dock detect** — connect/disconnect USB from TP4056 while watching the serial log (`esphome logs`, over the debug UART) — confirm `dock_detect` flips HIGH/LOW.
   - **Docked half (USB in TP4056): confirmed indirectly.** Real boot captured over the CP2102 debug UART — WiFi scanned/connected to `JCTnet1`, MQTT connected, `gate=1` logged (the 3-condition gate: Intent-off AND Power-Connected AND battery-above-threshold, all true) — consistent with dock-detect reading HIGH. `logger: level: INFO` means the binary_sensor's own state-change log doesn't show directly (that's DEBUG level), so this is inference from the gate value, not a literal `dock_detect: ON` line.
   - **Bonus, same capture:** firmware's own logged `batt=4.12` matches the direct multimeter reading (4.12V) almost exactly — effectively also satisfies post-continuity check #6 (battery divider sanity check) as a side effect.
   - **Undocked half (USB out, battery alone, switch ON) — two findings, in sequence:**
     - **First attempt failed to boot at all** — later retries booted fine (normal boot sequence, strong/steady onboard power LED, no brownout-loop signature). Not reproduced on retry; likely a one-off (switch position uncertainty at the time, or a transient), not treated as a real defect pending recurrence.
     - **Once actually captured over the debug UART (after several failed capture attempts due to timing, not a hardware fault — see below), a real firmware bug surfaced:** with **Intent switch confirmed OFF** and `dock_detect` OFF (battery-only, undocked), the device should take the "else" branch of the Step 8 on_boot gate — one `wifi.disable()` call, then nothing else ever attempts WiFi again per the design. Instead, the captured log showed a **repeating WiFi-disconnect / MQTT-reconnect-attempt cycle** (`jctsh.duckdns.org` resolve failures, `WiFi disconnected`, `Error resolving broker IP address: -6`, repeating) — something is re-enabling WiFi after the boot-time disable, in a state where it should never attempt at all. **Root-caused and fixed, same session.** Traced the actual code (`air-quality-monitor.yaml` lines 709-798) rather than assuming the gate logic was broken — it isn't. `wifi.disable()` correctly fires every 2-min tick given Intent-off + Power-disconnected (confirmed by tracing the exact condition against the confirmed device state). Checked the captured log content directly: all 9 lines were `[W][mqtt:...]`, zero `[wifi:...]` lines of any kind — the radio was never actually re-enabled. **Real cause: ESPHome's `mqtt:` component has its own independent reconnect logic**, retrying (and cleanly failing DNS resolution) on its own schedule regardless of `wifi.disable()` having correctly turned the radio off. **Fix:** mirrored every `wifi.enable`/`wifi.disable` call in that block with a matching `mqtt.enable`/`mqtt.disable` (both confirmed as real ESPHome actions via the installed package source, `esphome/components/mqtt/__init__.py`), so MQTT stops attempting entirely while the gate is closed. `esphome config` validated clean.

     - **Flashed and live-verified, 2026-09-16.** Flashed via USB (COM7, the ESP32's own onboard programming port — confirmed via a read-only `esptool chip_id` query rather than assumed from port history, after an initial mix-up over which of two connected CP210x adapters was which; COM9 is the separate CARD-0205 debug-only UART adapter, no EN/GPIO0 lines). Retested with the exact undocked/battery-only conditions this bug needs: Intent switch off, TP4056 USB unplugged, flash-USB also unplugged (so the board runs on battery alone through the Power switch), debug UART adapter connected and watched via `esphome logs --device COM9`. First capture attempt returned zero bytes despite a confirmed real power cycle and confirmed-good GND/TX-wire continuity and a steady (booted) onboard power LED — root-caused to a Python/esphome stdout block-buffering artifact when output is redirected to a file rather than a terminal, not a hardware fault. Re-ran with `PYTHONUNBUFFERED=1 python -u -m esphome logs`, which flushes live. **Result: `gate=0` (Intent-off + Power-disconnected, as expected) held clean across two full 2-minute duty-cycle interval ticks (~4 minutes) with zero `Error resolving broker IP address` / `WiFi disconnected` lines after the one-time setup-time attempt** — before this fix, the identical undocked/gate=0 state produced a repeating resolve-failure cycle at every tick. Confirms the fix.
     - **Also worth noting:** `jctsh.duckdns.org` (the fallback broker address, used when off `JCTnet1`) appearing rather than `pi1.local` suggests the device isn't actually on home WiFi during this bench session — expected at the workbench, not itself a finding.
     - **Debug UART capture reliability, separate thread worth remembering:** multiple capture attempts returned "no data" despite the device actually running — root cause was capture-window **timing** (starting the capture after asking for a reboot, rather than before), not a hardware/GND problem. A GND-wire-wiggle initially looked like it fixed it but didn't reproduce on a second wiggle — retracted, coincidental timing was the real explanation both times. The CP2102 module is powered independently from the PC's USB (not from the board) — confirmed not a factor either.
5. **Intent switch — ON case confirmed 2026-09-16, OFF case parked.** Watched via debug UART (COM9): Intent ON produced `DUTY CYCLE: switching to Measurement mode` at the next tick, confirming the switch is read correctly in that direction. Immediately after, the debug adapter's RXD line went permanently dark (no bytes at all, board itself confirmed still running via a steady power LED throughout) — ruled out, in order: log-capture stdout buffering (fixed with `python -u`/`PYTHONUNBUFFERED=1`, confirmed the fix works via the check-4 retest above before this happened), a stale process/serial handle (killed and restarted fresh, no change), USB re-enumeration (adapter's `DeviceID` unchanged), the adapter's own USB-side state (unplugged/replugged from the PC, no change), and the GPIO17/RXD + GND wiring itself (continuity re-confirmed twice, both by Joseph). Remaining candidates: the adapter module has a genuine internal fault (plausibly from being physically bumped mid-session), or a marginal connection internal to the adapter breakout that a multimeter probe at its accessible header wouldn't catch. **Parked, Joseph's call** — the Intent-OFF/silent-duty-cycle confirmation is the one open item from this check; picks up with a spare adapter swap (fastest real isolation test) whenever this component is revisited.
6. **Battery divider sanity check — done, 2026-09-16.** Direct multimeter reading at the battery terminals (switch on, docked/charging — see `wiring.md`'s caution that a charging reading is inflated, not resting voltage): **4.02V.** Compared against the same-moment logged `battery_v` from the dashboard heartbeat: **4.04V.** Well within tolerance — confirms the perfboard's divider (R1/R2) and ADC reading are correct, matching CARD-0012's earlier breadboard-stage finding of a near-exact match.
7. **Full boot — done, 2026-09-16, via the docked path** (the debug-UART path used for checks 4/5 was unavailable by this point, per check 5's parked finding above). Docked and switched on: clean connect (`Connected.` → `Air quality monitor online... reset reason: power-on event` → `MQTT connected`), buffered readings replayed and completed cleanly (`Replaying 10 buffered readings...` → one correctly-skipped `clock_invalid` entry from the earlier battery-only stretch → `Buffered-data replay complete.`), and the 5-min heartbeat reported sane values (PM2.5 unavailable — expected, RHT-only mode between ticks — VOC 101, NOx 1, batt 4.04V, RSSI -45dBm). Operates correctly end-to-end on the perfboard build. **Caveat added 2026-09-14, still applies:** "identically" doesn't mean byte-identical firmware — the check-4 fix (`mqtt.disable`/`mqtt.enable` mirroring) wasn't present in the original breadboard-tested build. Read as "operates correctly, matching the breadboard version's *intended* behavior."

---

## Open items carried from this session (2026-09-14)

- Pin 18 electrical anomaly — confirmed not continuous to GND on two ESP32 boards despite silkscreen printing GND; not used in this build, but `ESP32-project-pins.md` corrected and root cause still unexplained.
- Two wire-color conflicts between `wiring.md` (as-built, authoritative) and `ESP32-project-pins.md` (now stripped of colors per this session) — GPIO34 and GPIO32 — resolved by removing colors from the pin-assignment file entirely rather than reconciling two sources of truth.
