# JCTsh Backlog

Lightweight kanban. Each card has a **type** (idea | enhancement | bug) and a unique ID.

**Columns:** Backlog → Planning → Build → Done, plus **Defer** (off to the side — reachable from any stage)
- **Backlog** — captured, not yet being worked on
- **Planning** — being scoped/interviewed, and (if non-trivial) an implementation plan written — no separate Design checkpoint; the plan itself is the design artifact
- **Build** — going through the plan/implementation, including testing
- **Done** — complete
- **Defer** — a deliberate decision not to pursue for now (not abandoned, not forgotten — just consciously parked); can move here from any other column

<!-- next-card-id: CARD-0198 -->

---

### CARD-0197 · [idea] [data-pipeline] Instrument GPS correlation lookup to confirm the suspected Node-RED/Apps Script timing race
**Status:** Backlog

**Raised 2026-08-23 04:39 MST (Joseph), following up on the blank-lat/lon investigation from the 2026-08-22 hike's data-gap review.** 6 of 97 Environmental Data readings that hike came back with blank lat/lon, all clustered in the last ~50 minutes. The working theory (not yet proven): `_gpsLookup()` (`environmental-data.gs:276-295`) scans the "GPS Track" sheet for the nearest point *at query time*, ±5 minutes — if the hiking-monitor's buffered-reading correlation call fires before GPSLogger's own webhook-triggered write for the matching point has landed in the sheet, the lookup finds nothing nearby yet and returns null, even though the real point shows up seconds later. Joseph's call: **not worth fixing** (already a known, accepted, low-impact gap per hike-izer's own docs — see the "fixing the correlation timing" discussion, declined as its own card) — but wants confirmation the theory is actually correct, not just plausible.

**Instrumentation plan, designed in this conversation — small, additive, no behavior change to the correlation logic itself:**

1. **New "Correlation Debug" sheet tab** in the "JCTsh Environmental Data" workbook — one row per logged event: `[logged_at (real wall-clock ISO timestamp, not the reading's own ts), event_type, target_ts, best_diff_sec]`.

2. **In `_gpsLookup()`** (`environmental-data.gs:276-295`), right before the final `return`, log only misses (keeps row volume low):
   ```js
   if (bestDiff > fiveMin || bestRow === null) {
     ss.getSheetByName('Correlation Debug').appendRow(
       [new Date().toISOString(), 'lookup_miss', tsISO, bestRow ? bestDiff/1000 : null]);
   }
   ```

3. **In the `action=gps` handler** (`environmental-data.gs:511-536`), right after the existing `gpsSheet.appendRow(...)` at line 536, log every GPS point landing:
   ```js
   ss.getSheetByName('Correlation Debug').appendRow([new Date().toISOString(), 'gps_append', tsISO]);
   ```

**How this proves (or disproves) the theory — a direct comparison, not another inference.** For any `lookup_miss` row (reading timestamp X, wall-clock time T1), find the `gps_append` row whose own point timestamp is closest to X, and check its wall-clock time T2. If T2 > T1 — the matching GPS point landed in the sheet *after* the lookup already gave up — that's conclusive proof of the race. If T2 < T1, the theory is wrong and something else is causing the blanks, which is worth knowing too.

**Scope is diagnostic only — no fix implied or required.** This card is done once the instrumentation is deployed and has captured at least one real blank-lat/lon occurrence on a future hike with enough data to make the T1-vs-T2 comparison — confirming or refuting the theory either way counts as done. Whether to act on a confirmed race (vs. continue accepting it) is a separate future decision, not part of this card.

**Related:** the 2026-08-22 hike's blank-lat/lon investigation (this conversation), the declined "fix the correlation timing" discussion (same conversation, Joseph's call not to pursue a fix — this card only pursues *confirmation*), `core/data-pipeline/environmental-data.gs`, `.claude/skills/hike-izer/SKILL.md` ("Notes on the data" section, which already documents this as a known gap).

---

### CARD-0196 · [enhancement] [hiking-monitor] Extend field-mode hike endurance — true sleep-between-samples, display refresh throttling, longer-LiPo fit check
**Status:** Backlog

**Raised 2026-08-23 04:36 MST (Joseph), from a battery-usage analysis of the 2026-08-22 hike.** Field mode's actual current draw was reconstructed from the hike's own voltage curve: continuous 4.11V → 3.55V decline over 2h53m of active hiking, projecting to roughly **3h40m of continuous field-mode endurance per full charge** before hitting the firmware's hard-coded 3.4V low-battery cutoff (`hiking-monitor.yaml:531-532`). Root cause: during field mode the ESP32 never actually sleeps between samples — the 2-minute read/log cycle is a plain `interval: 2min` timer (`hiking-monitor.yaml:518-607`) with the whole chip continuously awake for the entire hike, not a wake-sample-sleep pattern. Four candidate fixes were discussed; Joseph's calls on each, interviewed 2026-08-23:

1. **True deep-sleep-between-samples for field mode — in scope, firmware-only, gated on not requiring rewiring.** Real ESP32 hardware deep sleep (~10µA) between the 2-minute reads instead of staying continuously awake is the single largest available lever — Joseph's framing: "if sleep mode can be implemented to help without rewiring, perhaps." This is believed feasible as a pure firmware change: unlike CARD-0070's peripheral-gating design (which needed a new P-FET switch physically wired between the 3.3V rail and the sensors), a wake-read-sleep cycle can use the sensors exactly as continuously wired today — no new hardware, just the ESP32 itself actually sleeping instead of idling. Known technical considerations to work through at Planning/Build, not yet resolved:
   - SPIFFS (`hike_logger.h`) needs to remount on every wake — currently mounted once at boot and assumed to stay mounted.
   - The pressure-trend circular buffer (`id(pressure_buf)`, `hiking-monitor.yaml:538-549`) lives in plain RAM, which real deep sleep wipes — needs to move to RTC memory (`RTC_DATA_ATTR`) to survive across sleep cycles, or the 30-minute trend comparison breaks every wake.
   - Sensor settle time after waking (BME280/LTR-390 need a brief moment post-wake before a valid read) needs to be accounted for in the wake sequence.
   - Wake source: a timed RTC wake (ESP32 `esp_sleep_enable_timer_wakeup`), not the existing dock-detect/slide-switch external wake sources (those stay as-is, unrelated).
   - **If this genuinely can't be done without rewiring once actually scoped, it's out — Joseph explicitly does not want the perfboard disturbed for this**, unlike CARD-0070 which he's deliberately treating as a future "v2" rebuild, not something to revisit now.

2. **Throttle e-ink display refresh frequency — in scope, confirmed ("this'll work").** Currently refreshes every single 2-minute cycle (`component.update: hiking_display`, `hiking-monitor.yaml:607`) — ~90 refreshes over a 3-hour hike, each with its own current spike, for a display that doesn't need that resolution. Reduce to every Nth cycle (exact N to be decided at Planning) or on-demand via the existing display button.

3. **Solar panel used on day hikes, not just multi-day trips — noted, not committed ("maybe").** No engineering work involved (the SUNYIMA panel already exists and is documented for multi-day use in `power-system.md`) — just a possible operational habit change, not a deliverable of this card. Not part of "done" criteria.

4. **Longer-but-same-thickness LiPo, contingent on enclosure fit — in scope as a research/procurement thread, bundled into this card per Joseph's call (one card, not split).** A physically longer 3.7V LiPo (same thickness as the current EEMB 1100mAh cell) might fit the existing 3D-printed enclosure (CARD-0009) without a redesign, if there's clearance in an unused dimension. Needs: measuring actual internal clearance in the built enclosure, sourcing candidate cells matching the current thickness/connector but higher mAh, and confirming fit before ordering.

**Explicitly excluded — CARD-0070 (LDO swap replacing the always-on boost converter) stays deferred, reframed as a future "v2" rebuild, not reopened by this card.** Joseph's reasoning: that fix requires meaningfully rewiring the perfboard, which is a bigger disruption than he wants for this pass — the sleep-mode and display fixes above are explicitly scoped to avoid that same cost.

**Verification approach — bench-measurable, unlike CARD-0195's diagnostic card.** Unlike field-mode failure conditions (rare, hard to trigger on demand), the actual current-draw improvement from sleep-between-samples can be measured directly on the bench the same way CARD-0026 measured the original boost-module baseline (multimeter in series on the battery lead). Done when: firmware changes 1-2 above are built and bench-measured to show a real reduction in average current during a simulated multi-cycle field-mode run (not just "should be lower" by inspection), sensor data integrity is confirmed intact across wake/sleep transitions (no NaN reads or lost samples introduced by waking too fast), and the longer-LiPo fit check (item 4) has a concrete yes/no answer with candidate part(s) identified if yes.

**Related:** the 2026-08-22 hike battery-usage analysis (this conversation), CARD-0070 (deferred boost-converter/LDO swap, the explicitly-excluded "v2" item), CARD-0026 (original sleep-current bench measurement methodology, to be reused here), CARD-0009 (enclosure build/dimensions, relevant to the LiPo fit check), CARD-0195 (the sibling diagnostic-instrumentation card from the same investigation), `components/hiking-monitor/hiking-monitor.yaml`, `components/hiking-monitor/hiking_logger.h`, `components/hiking-monitor/power-system.md`.

---

### CARD-0195 · [enhancement] [hiking-monitor] Field-mode diagnostic instrumentation — skip-reason logging and reset-reason detection
**Status:** Backlog

**Raised 2026-08-23 04:20 MST (Joseph), found while investigating three data gaps (totaling ~22 missed 2-minute samples) in the 2026-08-22 hike — the first real field deployment.** The 2-minute sensor-read interval (`hiking-monitor.yaml:520-607`) has two explicit silent-skip branches, and field mode has zero telemetry (no WiFi, so `ESP_LOGW` output never reaches anywhere durable) — so after the fact there's no way to tell which of several possible causes (I2C sensor glitch, clock-invalid state, or a full device reset) produced any given gap. This card makes those causes visible on the next hike instead of staying invisible.

**Scope, confirmed via interview 2026-08-22/23 — both pieces together, not split across cards:**

1. **Skip-reason logging.** The two silent `return;` branches currently discard the skip with no trace:
   - `hiking-monitor.yaml:552-556` — clock/NTP not valid at that tick.
   - `hiking-monitor.yaml:564-567` — BME280 read came back NaN on temp/humidity/pressure.

   Change both to call `hike_log_write()` with a small diagnostic JSON record before returning (e.g. `{"event":"skip","reason":"clock_invalid"}` / `{"event":"skip","reason":"nan_sensor","temp":...,"hum":...,"pres":...}`) instead of doing nothing. These ride the same flash-buffer-then-MQTT-replay path (`hike_logger.h`) real readings already use — no new transport needed on the device side.

2. **Reset-reason detection.** On boot, read `esp_reset_reason()`. If the device boots into field mode (switch on, no dock) with an abnormal reason (`ESP_RST_BROWNOUT`, `ESP_RST_PANIC`, `ESP_RST_TASK_WDT`, etc. — not `ESP_RST_DEEPSLEEP`/`ESP_RST_POWERON`), write that to the hike log the same way, so a mid-hike reset is distinguishable from a sensor glitch after the fact.

3. **Node-RED/Apps Script routing addition needed on the receiving side:** once replayed, a `"event":"skip"` record isn't a sensor reading — the environmental-data wildcard handler needs to route these to the `/log` topic (System or a new diagnostic category) rather than attempting to treat them as an Environmental Data sheet row.

**Verification, confirmed via interview 2026-08-23 — deploy-and-wait, not forced bench testing.** These failure conditions (a real NaN sensor read, a real brownout/panic) are hard to trigger reliably on demand. Done criteria: firmware builds clean, deploys to the real field device via OTA/USB, boots and logs normally in the ordinary case (no false-positive skip/reset records under normal operation) — real validation of the diagnostic paths themselves happens naturally whenever a future hike actually hits one of these conditions, not forced synthetically before closing this card.

**Related:** the 2026-08-22 hike's data-gap investigation (this conversation — not yet a card of its own, the gaps themselves were left unexplained, this card is the follow-up), `components/hiking-monitor/hiking-monitor.yaml`, `components/hiking-monitor/hiking_logger.h`, `core/data-pipeline/environmental-data.flow.json` (Node-RED routing that needs the new branch).

---

### CARD-0194 · [idea] [hike-izer] Method to fix voice-to-text errors in hiking observations
**Status:** Backlog

**Raised 2026-08-23 03:55 MST (Joseph), found while reviewing the 2026-08-22 hike's data gaps.** The first observation of today's hike reads "hiking The tortellito Preserve this morning with David" — almost certainly a Tasker voice-to-text mishearing of "Tortolita Preserve" (a real preserve in the Marana, AZ area matching the hike's actual GPS location). Left uncorrected on the published summary page rather than silently edited.

**Interviewed 2026-08-22:** scope is a **general mechanism** for catching/fixing this class of error across future hikes, not a one-off fix to today's observation text. Where the correction should actually happen (source Sheet edit vs. an annotation applied at hike-izer render time) was discussed but **explicitly deferred, not decided** — Joseph's call, to revisit later rather than design it now.

**Two candidate approaches surfaced during discussion, neither committed to:**
1. **Render-time annotation.** Leave the raw observation text in the Hiking Observations sheet untouched (it's the source record, and this matches hike-izer's own existing rule that its Full Observations table shows "the raw text as logged, don't paraphrase or clean it up" — auto-rewriting at render time would contradict that deliberate rule). Instead, cross-check named entities in observations against `place_context.py`'s already-fetched real nearby named features (CARD-0108) and flag a likely near-miss with something like "[likely: Tortolita Preserve]" next to the raw text.
2. **Manual review habit, no automation.** Skim observations when a hike page is generated and hand-add an annotation only when something's actually wrong — cheaper, matches this project's general bias against building machinery ahead of demonstrated need (this is the first occurrence).

Claude's lean, offered but not acted on: start with the manual approach (2) given this has only happened once so far, and only build the `place_context` fuzzy-matching automation (1) if it turns out to recur across hikes.

**Related:** `.claude/skills/hike-izer/SKILL.md` (the "don't paraphrase" rule this has to respect), `components/hike-izer/place_context.py` (CARD-0108, the data source a render-time approach would reuse), the 2026-08-22 hike-summary page (`https://hikes.jctnet.com/2026-08-22_hike-summary.html`, the motivating instance).

---

### CARD-0193 · [idea] [tos] Kanban board scaling strategy — RESOLVED 2026-08-22 20:17 MST
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-08-22 (CARD-0193) — 17933B, over the 5000B size threshold.

---

### CARD-0192 · [idea] [infrastructure] Watchdog self-test for the kanban-PR intake pipeline
**Status:** Backlog

**Raised 2026-08-22 18:24 MST (Joseph), during a strategy discussion following CARD-0190.** CARD-0190's root bug (the Tasker "Log Idea" widget silently failing while hiking) was only discovered because Joseph happened to check the PR list afterward — nothing surfaced the failure on its own. Addresses the top-priority weakness identified in that discussion: the auto-PR intake pipeline (`open_finding_pr()`/CARD-0128/CARD-0173) runs unattended (a webhook always listening, `email-idea-check.py` polling on a timer) but has no monitoring of its own, unlike this project's other unattended services.

**Proposed approach, not yet interviewed/scoped:** mirror the existing Node-RED watchdog pattern (`core/node-red/watchdog.flow.json` — alerts via HA companion-app push notification if a component goes silent for 10 minutes) rather than inventing a new alerting mechanism. A periodic synthetic self-test — e.g. a scheduled job that calls `open_finding_pr()` with a recognizable test fingerprint, confirms a PR actually opened, then either auto-closes it or leaves it for `resolve_and_merge()`'s own idempotent handling — with a failure routed into the same MQTT log / HA-notification path every other component's health check already uses, so a broken pipeline pages Joseph instead of waiting to be noticed by chance.

**Open questions for interview before Build:** test cadence (hourly? daily?); where the self-test job runs (a new systemd timer alongside `email-idea-check.py` on the M8, or folded into an existing maintenance-check script); whether a failed self-test should also be evidence that a *real* idea/finding might have been silently dropped during the same window (CARD-0190's actual incident) and whether that's worth surfacing distinctly; whether the test PR needs cleanup automation or can just accumulate and get closed manually/occasionally.

**Related:** CARD-0190 (the incident this directly addresses), CARD-0128 (`open_finding_pr()`, what's being tested), CARD-0173 (Tasker "Log Idea" widget, the path that failed silently), `core/node-red/watchdog.flow.json` (the existing pattern this mirrors).

---

### CARD-0191 · [idea] [tos] Consolidate TOS (Team Operating System) tooling into its own directory — RESOLVED 2026-08-22 18:54 MST
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-08-22 (CARD-0193) — 9453B, over the 5000B size threshold.

---

### CARD-0190 · [bug] [tos] Auto-opened kanban PRs (CARD-0128/CARD-0173) broken by kanban-board.md crossing GitHub's 1MB Contents API limit — RESOLVED 2026-08-22 17:48 MST
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7612B, over the 5000B size threshold.

---

### CARD-0189 · [bug] [photo-quality-review] "Super rule" bulk-delete marking phase is very slow — RESOLVED 2026-08-22 17:20 MST
**Status:** Done

**Raised 2026-08-22 17:07 MST (Joseph), live during a review session** — after choosing "Delete all N in Robin's library" (CARD-0155's super-rule bulk-delete box), the "Marking decisions: X of Y…" phase is very slow, well before the actual Immich delete step even starts.

**Root cause, found via code read of `server.js`/`public/review.js`:** the client's Phase 1 loop calls `/api/decide/duplicate` once per qualifying group (6-way concurrency via `forEachWithConcurrency`), but every one of those calls does a full read-parse-mutate-write of the *entire* `decisions.json` file (`loadDecisions()` → mutate → `saveDecisions()`), and all such writes are serialized through a single global lock (`withDecisionsLock`, added by CARD-0028 to fix a real race condition). So N groups means N sequential full-file I/O round trips, not N fast in-memory updates — and it gets slower over time as `decisions.json` accumulates decisions across the whole multi-year review. This is a *different* bottleneck than CARD-0148's already-known-and-accepted `refreshTally()`/`pendingDeletions()` cost.

**Scope, decided via interview 2026-08-22:** fix only the super-rule bulk-delete marking phase — add a new bulk endpoint (e.g. `POST /api/decide/duplicates-bulk`) that takes the full list of qualifying groupKeys in one request, does a single `loadDecisions()` → mutate all → single `saveDecisions()`, still under the existing lock. `openSuperRuleModal`'s Phase 1 in `review.js` switches to this one call instead of the per-group loop. Regular one-at-a-time manual clicks (radio/skip/keep-all/delete-all buttons) are explicitly out of scope — a human clicking one at a time doesn't expose the same N-round-trip cost the way a tight programmatic loop does.

**Done when:** marking all qualifying groups for a real year with a meaningful `qualifiedCount` completes in roughly the time of one file write (not N round trips), confirmed live against real data — not just code review. `decisions.json` after the bulk-mark matches what N individual `/api/decide/duplicate` calls would have produced (same keys, same `{ keepAssetId, auto: true, autoReason }` shape) — no regression in the correctness CARD-0028's locking fix established.

**Related:** CARD-0155 (super-rule bulk-delete feature this bug is in), CARD-0028 (review app, `decisions.json` locking discipline), CARD-0148 (separate, already-known `refreshTally()` cost — not what this card fixes).

**Fixed and deployed, 2026-08-22 17:20 MST.** Added `POST /api/decide/duplicates-bulk` to `server.js` (single load → mutate all → single save under the existing lock) and switched the super-rule modal's Phase 1 in `review.js` to call it once instead of looping `/api/decide/duplicate` per group. **Found live on the first deploy:** the new client loop called `findDuplicateGroup()` — a linear scan over the whole library's 38,258 duplicate groups — once per qualifying key with no yielding, which froze the tab for the entire loop and was worse than the original (Joseph: "even slower than before"). Fixed by building a one-time `groupKey → group` lookup Map before the loop (O(M) once, O(1) per key) instead of repeated linear scans. Deployed both fixes to the M8 (`server.js` + `sudo systemctl restart photo-quality-review` for the first; `review.js` alone, no restart needed, for the second — static file). Confirmed fast live by Joseph against real data.

---

### CARD-0188 · [idea] [shower-temp-sensor] Shower water temperature logging — XIAO ESP32-C3 relay node via ESP-NOW to a host ESP32
**Status:** Planning

**Raised 2026-08-20 20:31 MST (Joseph), via informal Phase 0 exploration in Claude chat** — started from "how can I measure the temperature of the water while I'm showering," worked through feasibility and approach before any hardware was ordered or files changed, per `JCTsh-Component-Planning-Pattern.md`'s Phase 0. This card captures that discovery — decisions made, options explored and ruled out with reasoning, and what's still genuinely open — so Planning picks up from real findings rather than re-deriving them.

**Immediate, separate fix already given (not part of this card):** a plain inline analog dial shower thermometer (threads between shower arm and showerhead, no battery, always-on readout) solves the "I just want to glance at the temperature" need today, independent of whether this component ever gets built.

**Goal, confirmed via interview:** historical logging/tracking to the existing environmental data pipeline (`core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`) — not real-time in-shower feedback (a phone/dashboard isn't practical to check mid-shower) and not a safety/scald alert. Same general shape as `front-porch-temp-sensor`/`remote-temp-sensor-01`: always-connected, no field/home mode split needed (unlike `hiking-monitor`), since this lives at a fixed indoor location with home WiFi in range — of the *host* node, at least (see below).

**Location: master bath — decided.**

**Sensor: waterproof DS18B20 probe, contact-type — decided.** Chosen over a non-contact IR sensor (e.g. MLX90614): more accurate for a moving water stream, cheap (~$2-5), fully submersible stainless probe on a cable, and ESPHome has a native `dallas` platform for it — no custom component needed, consistent with every other JCTsh sensor. IR was ruled out — reads surface temp of whatever it's pointed at, gets thrown off by steam/mist, exactly the wrong tradeoff for a shower environment. 1-Wire wiring (3-wire external power, 4.7kΩ pull-up, not parasitic power) — standard reference wiring already sketched during this exploration, not yet written into a real `wiring.md`.

**Specific probe selected: BOJACK DS18B20 1M Temperature Sensor Probe, Stainless Steel, Pack of 2** ([Amazon](https://www.amazon.com/BOJACK-DS18B20-Temperature-Stainless-Waterproof/dp/B0CP7SYGPP)). Confirmed real DS18B20 spec range (-55°C to +125°C, matches datasheet). Wire convention per listing: Yellow=DATA, Red=VCC, Black=GND — verify with multimeter against the physical part before wiring, same discipline as every other new battery/module pairing in this project. Pack of 2 gives a spare. 1m cable is considerably longer than the wall-mounted design actually needs (only a few inches to reach the water stream) — not a problem, just plan to coil/trim the excess. Bare probe+cable only, no onboard pull-up — the external 4.7kΩ pull-up above is still required.

**Board confirmed: Seeed Studio XIAO ESP32-C3** — matches the board already selected above (built-in TP4056 charging circuit + JST-PH connector, confirmed during the battery decision).

**Placement problem that shaped the whole architecture: PEX plumbing, no accessible pipe segment anywhere in the house.** Ruled out clamp-on/exterior pipe sensing (the easiest install option in general) for that reason — the only good measurement point is directly in the water stream at the showerhead, which is exactly where running a wire back to a dry, powered location becomes impractical.

**Existing product researched and ruled out — Longriver MX08 "Bluetooth" shower thermometer.** Investigated whether its wireless link could be intercepted/decoded instead of building a sensor from scratch. Findings: every listing repeats identical "connects to your smartphone via Bluetooth" marketing boilerplate, but no verifiable companion app exists anywhere, and the product's own spec ("display within 6.56ft of the sensor") describes a dedicated sensor-to-its-own-display link, not a phone pairing range. Strong signal this is generic/inaccurate marketing text for a proprietary point-to-point RF link, not real BLE. **Not pursued** — recommended checking the unit's FCC ID (discloses real radio tech) before ever trying to sniff it, but didn't block on that since the DIY sensor path is more reliable regardless.

**Consumer BLE sensor tags (Xiaomi Mijia, Govee, SwitchBot-style) also ruled out** — built for room-ambient monitoring, not waterproof/submersible; mounting one in the actual spray path would likely kill it, and even if it survived it would read air temperature, not water temperature. Wrong tool for measuring the water itself.

**Decided architecture — the ESP32 becomes the remote node, not a hub something else reports back to:**
- A small board (Seeed XIAO ESP32-C3 or similar ESP32-C3 SuperMini — ~21×18mm) in a small waterproof enclosure, DS18B20 probe wired directly to it with only a few inches of cable (short enough to route/hide cleanly — this is what actually solves the "can't run a wire across the room" problem, not a wireless link on the sensor's own data path).
- **Mounted on the wall above the shower arm, not clamped directly to the metal pipe.** Originally considered pipe-clamping; corrected after realizing a small board's onboard PCB antenna held right against a large metal pipe risks serious signal degradation (a real, documented RF issue, not a hypothetical). Wall-mounting avoids it — walls (tile/grout/drywall) don't have that problem, and the probe cable only needs a few inches of slack to still reach into the water stream from a position just above the shower arm.
- Enclosure needs an **IPX5/6 (spray/splash-rated) enclosure, not IPX7 (submersible)** — only the probe itself contacts water directly, the enclosure sits in the spray/steam zone but isn't submerged.
- **Mounting method:** wet-rated adhesive (the shower-caddy/soap-dish grade specifically — generic Command-strip-style adhesive is not rated for constant humidity and will fail) or a suction cup, plus a cheap physical tether/cord as a fail-safe against the mount eventually letting go, so the unit doesn't fall into the shower pan/tub if adhesion fails months later.

**Communication: ESP-NOW to a second, mains-powered "host" ESP32 — decided, with reasoning.** Not full WiFi+MQTT directly from the shower node — ESP-NOW skips WiFi association/DHCP/TCP/MQTT-connect overhead entirely, so the radio only needs to key up for tens of milliseconds per reading instead of 1-3+ seconds, which is the single biggest lever on battery life here. It also sidesteps needing strong WiFi signal *in the bathroom itself* (notoriously bad WiFi terrain — tile, pipes, moisture) — the shower node only needs to reach a *nearby* second board, not the home router directly. The host ESP32 receives the ESP-NOW packet and forwards it to MQTT like any other JCTsh component.

**ESP32-C6 with Zigbee/Thread instead of WiFi — explored and ruled out.** Both are mesh protocols expecting real network infrastructure, not point-to-point links: Zigbee needs a coordinator (a USB dongle + Zigbee2MQTT service — the proven path — or custom non-ESPHome coordinator firmware on the host board); Thread needs a Border Router plus HA's Matter integration, a bigger lift still. Both would add genuinely new standing infrastructure to this project to solve a problem ESP-NOW between two plain ESP32s solves with zero new infrastructure. Ruled out as disproportionate to the size of this one sensor node.

**Board choice: Seeed XIAO ESP32-C3 — decided for the first build.** Nordic nRF52-series (e.g. XIAO nRF52840) was considered — genuinely better BLE sleep/burst power efficiency than ESP32's WiFi-centric radio, and a real candidate if battery life becomes the actual bottleneck — but ESPHome doesn't support Nordic chips, meaning custom Arduino/Nordic-SDK firmware instead of this project's established ESPHome workflow. Not chosen for the first build; worth revisiting only if real bench-measured battery life on the ESP32-C3 turns out to be inadequate.

**Power — decided 2026-08-20: small rechargeable LiPo pouch, board choice confirmed too.**

**Board's own charging circuit, confirmed during this decision (correction to earlier assumption in this card):** the XIAO ESP32-C3 has a **built-in TP4056 charging circuit and onboard JST-PH (2.0mm) connector** — no separate charge-management circuit needed, just plug a compatible cell in. Seeed's own documentation recommends **500-1500mAh** for that circuit — bigger than the ~150-250mAh range assumed earlier in this exploration; the enclosure size estimate should account for a cell at the low end of that range, not smaller.

**Specific battery selected: AKZYTUE 3.7V 500mAh 503035 LiPo, JST-PH 2.0mm connector** ([Amazon](https://www.amazon.com/Battery-Rechargeable-Lithium-Polymer-Connector/dp/B07S84SBV3)). PCM protection confirmed directly from the product's own listing text (not a secondhand/assistant summary — that distinction mattered and was checked): *"PCM protection (overcharge, over-discharge, overcurrent, short circuit, and over-temperature protection)... no leaks."* Satisfies all 5 protections `JCTsh-Build-Standards.md` §2.14 point 1 requires, confirmed from the listing before purchase per that same standard. 500mAh sits at the low end of the XIAO's recommended range, reasonable for this low-power design. This component's own §2.14 safety standards (LDO not boost — moot here since the XIAO's onboard TP4056 circuit handles this directly; firmware low-battery cutoff) still apply once firmware is written.

**CR2032 primary coin cell + coin-cell-format supercapacitor was considered and passed on** (Cornell Dubilier/Knowles EDC/EDS series, DigiKey-stocked, ~$4-8 total for both parts) — smaller/thinner, but non-rechargeable (periodic physical cell swap requiring the waterproof enclosure to be opened each time — worse for both convenience and long-term seal integrity than the LiPo's external-USB-port recharge path) and adds real unproven design complexity (inrush-limiting resistor, correctly sizing the supercap, needs bench validation before trusting it — same "measure, don't calculate" discipline this project already learned the hard way twice, CARD-0026/CARD-0070). Right choice if enclosure size later proves to be a hard constraint the LiPo can't meet — not the starting assumption.

**Deferred as a real v2 idea, not part of this build:** a micro-hydro turbine (F50-style, ~$5-15, generates ~1-2.6W only while water flows) trickle-charging a rechargeable cell/supercap during each actual shower — elegant in principle (generates power exactly when the sensor needs to be active) but needs real rectification/charge-management circuitry this project hasn't built before. Revisit once a battery-powered version exists and works.

**Open items still needing resolution before Build:**
- Real bench current-draw measurement of the AKZYTUE 503035 + XIAO ESP32-C3 + firmware, once built — battery type is decided, but actual runtime should still be measured, not calculated, same discipline as every other battery-powered component in this project.
- Whether "a shower is happening" needs active detection (to conserve power and keep logged data meaningful) or whether simple periodic polling is acceptable — materially affects the battery-life design either way, not yet resolved.
- Identity of the "host" ESP32 — a new dedicated board, or could an existing always-on JCTsh device absorb the ESP-NOW-receive-and-MQTT-forward role?
- Real waterproof enclosure sourcing/design, and the specific wet-rated adhesive/mounting product — neither chosen yet.
- MQTT topic naming, payload schema, and Node-RED/environmental-data-pipeline integration per the Phase 3 Required Checklist (`JCTsh-Component-Planning-Pattern.md`) — not yet touched at all; this exploration stayed in Phase 0/1 feasibility territory.
- Real DS18B20 probe cable length/routing measured against the actual bathroom, once a specific shower is chosen.

**Related:** `front-porch-temp-sensor`, `remote-temp-sensor-01` (closest existing reference patterns), `hiking-monitor` (battery safety standards precedent), `JCTsh-Build-Standards.md` §2.14 (battery safety, applies once a battery is chosen), `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md` (payload schema this must conform to).

---

### CARD-0187 · [bug] [outdoor-presence-detection] Ring motion/video pipeline consolidation — shared trigger, doorbell voice/video coordination, missed-event investigation
**Status:** Defer

Archived to `components/outdoor-presence-detection/CLAUDE.md` on 2026-08-22 (CARD-0193) — 18495B, over the 10000B size threshold.

---

### CARD-0185 · [enhancement] [homeassistant] Upgrade CARD-0145's trigger to ring-mqtt's binary_sensor.*_motion (near-instant, vs. ~30-90s poll delay) — SUPERSEDED 2026-08-20 by CARD-0187
**Status:** Defer

**Raised 2026-08-18 18:23 MST (Joseph), while building CARD-0146.** CARD-0145's Ring motion announcement currently triggers on `sensor.*_last_activity` (CARD-0184's fix for the durably-broken native `ring` integration `event.*` platform) — reliable, but polled at ~60s intervals, so real delay can run 30-90+ seconds between an actual motion event and the announcement.

`ring-mqtt` (installed this session for CARD-0146) publishes its own independent `binary_sensor.<camera>_motion` entities, separate codebase/connection from the broken native integration. Live-tested today on the doorbell (`binary_sensor.doorbell_ding`/`binary_sensor.doorbell_motion`): near-instant, on within a few seconds of a real event — confirmed reliable across all of today's CARD-0146 testing. Confirmed the same entities exist for CARD-0145's other 4 cameras too: `binary_sensor.path_motion`, `binary_sensor.gate_motion`, `binary_sensor.front_porch_motion`, `binary_sensor.front_door_motion` (all present, all `off` at check time).

**Not yet decided/scoped:** swapping CARD-0145's trigger from `sensor.*_last_activity` to `binary_sensor.*_motion` for all 5 cameras (gate, path, front_door, front_porch, doorbell) — mechanically similar to CARD-0184's own swap, but the reverse direction. The `category == 'motion'` filter condition CARD-0184 added would no longer be needed (`binary_sensor.*_motion` entities are motion-only by construction, same reasoning as the original native-integration `event.*_motion` entities). Needs a live test pass on all 5 cameras (not just doorbell, which is all that's been proven so far) before trusting it as a full swap, plus the debounce/cooldown logic reconsidered for a fast-push source (the current 3s trailing delay and 30s entry-cluster window were tuned against a poll-based source's own timing characteristics).

**Done when:** CARD-0145's automation trigger is swapped to `binary_sensor.*_motion`, live-tested against real events on multiple cameras (not just doorbell), and confirmed both correctly-triggered and correctly-debounced — or a decision to keep the current poll-based trigger is recorded instead, with reasoning.

**Superseded 2026-08-20 16:18 MST.** A real field event the same day surfaced two more findings (a doorbell voice/video coordination problem, and a premature CARD-0146 stream termination) that don't fit this card's narrow trigger-swap scope — rather than keep bolting new findings onto this and CARD-0145/CARD-0184, all of it (including this card's own trigger-swap scope, unchanged) is consolidated into CARD-0187. No work here was wasted — the `binary_sensor.*_motion` entity confirmation and scoping notes above carry forward directly.

**Related:** CARD-0145 (the automation this would have upgraded), CARD-0184 (introduced the current `sensor.*_last_activity` fallback this would have replaced), CARD-0146 (the build that surfaced ring-mqtt's own motion entities as a viable alternative), CARD-0187 (supersedes this card).

---

### CARD-0184 · [bug] [outdoor-presence-detection] CARD-0145's Ring motion announcement has been silently dead since 2026-08-15 — RESOLVED 2026-08-18 17:02 MST
**Status:** Done

Archived to `components/outdoor-presence-detection/CLAUDE.md` on 2026-08-22 (CARD-0193) — 10489B, over the 10000B size threshold.

---

### CARD-0183 · [bug] [hike-izer] Hike-publish push notification link isn't clickable — RESOLVED 2026-08-18 15:11 MST
**Status:** Done

**Raised 2026-08-18 (Joseph, via voice note, PR #25).** The push notification sent on hike-summary publish (CARD-0141) includes the published page's URL as plain text inside the message body — confirmed in `components/hike-izer-orchestrator/generation.py`'s two success call sites (`run_and_log()`, `run_step2_and_log()`), both of which build the URL into the `message` string passed to `ha_notify.send_push()`. `ha_notify.py`'s `send_push()` only sends `title`/`message` to HA's notify service — no `data.clickAction` (or `data.url`), the field the HA companion app actually uses to make a notification tap open a link. Tapping the notification today does nothing; the URL has to be manually copied out of the notification text.

**Fix:** add an optional `url` parameter to `send_push()` that sets `data: {"clickAction": url}` in the HA notify service call; pass the hike page URL through from both success call sites in `generation.py`.

**Done when:** `ha_notify.send_push()` accepts a `url` param and sets `clickAction`; both success call sites pass it; deployed to the M8 orchestrator; and a real test notification confirmed tapping it opens the hike page in the browser on Joseph's Pixel.

**Built, deployed, and verified live, 2026-08-18 15:11 MST.** `ha_notify.send_push()` now accepts an optional `url` param and sets `data: {"clickAction": url}` in the HA notify payload when provided. Both success call sites in `generation.py` (`run_and_log()`, `run_step2_and_log()`) pass the hike page URL through — failure branches unchanged, nothing to link to on a failure. Deployed via `scp` to `~/hike-izer-web-app/orchestrator/` on the M8 (Tailscale IP) and `docker compose up -d --build orchestrator`. Verified with a real test push (`ha_notify.send_push('Hike-izer test', ..., url='https://hikes.jctnet.com/')` run inside the rebuilt container) — Joseph confirmed the notification arrived and tapping it opened the link in the browser. The generation-pipeline call sites themselves will get exercised for real on the next hike, same as CARD-0141's own original verification pattern.

**Related:** CARD-0141 (introduced the push notification this fixes).

---

### CARD-0182 · [idea] [hike-izer] BirdNET Live recording practices while hiking — DONE 2026-08-19
**Status:** Done

**Raised 2026-08-18 (Joseph, via voice note, PR #26).** BirdNET Live's phone-side bird-call recognition is degraded by trail noise (wind, footsteps, breathing) and phone mic/recording setup while hiking. JCTsh's pipeline only consumes BirdNET Live's already-identified detections after the fact (`components/hike-izer-orchestrator/birdnet-pipeline.md`) — it does no audio processing itself, so this is a practices/documentation item, not a pipeline code change.

**Scope, confirmed 2026-08-18:** research and document phone/app-side practices to reduce noise and improve recording quality (mic placement/carrying position, BirdNET Live app settings) as a new section in `components/hike-izer-orchestrator/birdnet-pipeline.md`.

**Done when:** best-practice recommendations are researched and documented there, and Joseph has a concrete checklist to try on the next hike.

**Researched 2026-08-19 — significant finding, not just a checklist.** Every hike so far has used BirdNET Live's **Live Mode**, not Survey Mode as CARD-0080's original docs/code comments assumed (never actually verified, confirmed wrong by Joseph directly). Checked BirdNET Live's own source on GitHub: Survey Mode and ARU Mode both wire in Android's `flutter_foreground_task` background-survival mechanism via dedicated notification files; no equivalent exists for Live Mode, whose own docs describe it as an actively-open, on-screen-only experience. Strong (not 100% certain) evidence that **Live Mode likely stops listening whenever the phone screen locks or another app gets focus** — meaning every past hike may have had silent gaps beyond the trail-noise problem this card set out to fix. Functionally nothing in the pipeline broke from the wrong mode assumption — verified the Route Map's per-sighting location comes from the hike's own independent GPS track (`build_hike_map.interpolate_position()`), not from anything BirdNET Live itself reports.

**Decided 2026-08-19 (Joseph): switch to Survey Mode for hiking going forward** — purpose-built for this, confirmed background survival, own GPS track. Full writeup, general field-recording checklist (carry position, wind, clothing, handling noise), and Survey Mode setup/Detection-Sampling notes now in `components/hike-izer-orchestrator/birdnet-pipeline.md` Section 4. `birdnet-pipeline.md` and `birdnet.py`'s docstring corrected to stop claiming Survey Mode was ever in use. **Not yet field-tested** — first real Survey Mode hike will confirm.

**Standing constraint, confirmed 2026-08-19 (Joseph): there is no manual review/curation step, ever.** "There is no review at the end of a session. I just take it as it comes. I have no expertise for any review." Whatever BirdNET Live confidently reports flows straight through export → this pipeline → the published hike's "Wildlife Heard" table and the cross-hike Wildlife Life List, with no human filtering anywhere in between. This reversed part of the settings guidance already given (confidence threshold, sensitivity — see `birdnet-pipeline.md` Section 4's correction) and should be assumed true for any future recommendation touching this pipeline: nothing gets curated after the fact, so detection-quality settings need to be conservative on their own, not "good enough, we'll catch mistakes at review."

**Closed 2026-08-19 (Joseph).** Research, checklist, mode-switch decision, and settings are all documented and applied where actionable today. Field verification — does Survey Mode actually close the gaps, do the applied settings hold up in practice — happens naturally on the next real hike; not gating this card's closure. Revisit `birdnet-pipeline.md` Section 4 with results if anything needs adjusting after that hike, new card if it turns into real follow-up work.

**Related:** CARD-0157 (BirdNET Live pipeline documentation, the doc this extends).

---

### CARD-0181 · [bug] [hiking-monitor] No way to cut real power without disassembling the enclosure
**Status:** Defer

**Raised 2026-08-17 18:04 MST (Joseph), called a "major design failure."** Discovered while reassembling the enclosure post-CARD-0009: the only true hard-off state for this device is disconnecting the LiPo's JST connector from the TP4056 (per `operations.md`'s Power Switch Behavior table — "Storage — fully off" requires "Disconnected" battery, no other row reaches true off). That connector is inside the sealed enclosure with no external access, so once assembled, there is no way to actually cut power without taking it apart again.

**Compounding issue:** the device's slide switch reads as a power switch but isn't one — `operations.md` line 79: "VOUT+ runs directly to ESP32 VIN — the switch is not in the power path." It only sets a GPIO-read mode flag (field vs. upload mode); the lowest-power reachable state via the switch is deep sleep (~10µA), not true off. For most purposes (avoiding activity while handling the device) that's sufficient, but it is not the same guarantee as no power draw at all, and the UI/labeling (a slide switch on the outside of the case) actively implies otherwise.

**Not yet decided — fix approach deferred to Planning, Joseph's call 2026-08-17:** candidates raised but not chosen: (1) an accessible inline power switch, wired directly into the battery path (not the existing mode-select switch), reachable from outside the enclosure — true hard off on demand; (2) a JST pigtail extended from the battery connector to an external access cutout, so the existing connector can be reached and unplugged without disassembly, no new switch hardware. Neither confirmed; revisit at Planning.

**Deferred 2026-08-19 (Joseph).** No fix approach chosen, no work started. Revisit at Planning when the enclosure is next opened (CARD-0180's remote-reboot work covers the reboot half of the accessible-control need in the meantime; this card is only about true power-off).

**Standard raised from this, 2026-08-18 14:35 MST:** `JCTsh-Build-Standards.md` §1.7 (Accessible Power Control for Enclosed Devices, v1.19) now makes this a required decision for every future enclosed build, made before the enclosure is sealed — this card and CARD-0180 are its origin case. §1.7 lists both candidate approaches above as acceptable patterns for requirement 1 (true hard off); whichever gets chosen here should also be reflected there if it changes/refines the general pattern.

**Done when:** the real hiking-monitor can be put into a genuine zero-draw off state without opening the enclosure, verified live (not just wired correctly) — and the chosen mechanism is documented in `operations.md`'s Power Switch Behavior table alongside the existing modes.

**Related:** CARD-0009 (the final-assembly work this surfaced during), CARD-0180 (on-demand remote reboot — a related but distinct need; that card is about forcing a *restart*, this one is about achieving true *power-off*).

---

---

### CARD-0180 · [enhancement] [hiking-monitor] On-demand remote reboot, triggered from Home Assistant — RESOLVED 2026-08-19 17:24 MST
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5781B, over the 5000B size threshold.

---

### CARD-0186 · [bug] [front-porch-temp-sensor] [salt-sensor] Restart button MQTT discovery id collision — RESOLVED 2026-08-19
**Status:** Done

**Raised 2026-08-19 (Joseph, while closing CARD-0180):** "What about front-porch-temp-sensor and salt-sensor?" — asked after CARD-0180's investigation found hiking-monitor's restart button colliding with these two devices' restart buttons on the exact same auto-generated MQTT discovery `unique_id` (`ESPbuttonrestart`, from ESPHome's default `discovery_unique_id_generator: legacy`, which derives the id from the entity's type + name alone — any two devices with an entity of the same type sharing the literal name "Restart" collide). All three devices' restart buttons are named plain `"Restart"`.

**Confirmed live before starting:** checked HA directly — `button.front_porch_temp_sensor_restart` exists (currently the collision "winner"); `button.salt_sensor_restart` returns "Entity not found" (the silent loser — has never worked from HA, unnoticed until now).

**Scope decision:** hiking-monitor's own fix used `discovery_unique_id_generator: mac` at the device's `mqtt:` block level — safe there because that device exposes only one entity (everything else `internal: true`). front-porch-temp-sensor is not the same shape: it discovers several live entities (temperature/humidity/pressure, light level) feeding the environmental data pipeline, and the generator setting is device-wide, not per-entity — flipping it would regenerate *every* entity's unique_id on that device, orphaning current HA registrations (same duplication mess as CARD-0180's own bug, but on live sensor data instead of an unused button). salt-sensor only discovers the button (its SmartThings switches are separate virtual entities, not published by this device) so either fix is equally safe there. **Decided:** apply the surgical, lower-blast-radius fix to both — give each device's restart button a distinct `name:` (device-specific, not the shared literal "Restart") so the existing legacy generator naturally produces distinct ids. No `mqtt:` block changes, no other entities touched on either device.

**Done when:** both devices reflashed, `button.salt_sensor_restart` (or its post-rename entity_id) appears live in HA for the first time, `button.front_porch_temp_sensor_restart`'s entity confirmed still intact/no duplicate created, verified via live `mosquitto_sub` + HA state check same as CARD-0180.

**Built and verified live, 2026-08-19.** Both devices reflashed OTA. Confirmed via `mosquitto_sub` on `homeassistant/button/#` that each device now publishes a distinct `uniq_id` (`ESPbuttonfront_porch_temp_sensor_restart`, `ESPbuttonsalt_sensor_restart`) — no more collision with each other or with hiking-monitor. Old stale retained discovery topics (`.../restart/config`, `uniq_id: ESPbuttonrestart`) cleared on both via `mosquitto_pub -n -r` so HA drops the orphaned pre-fix entities.

**Result:** `button.salt_sensor_salt_sensor_restart` now exists and works — first time ever (previously silently dropped, confirmed "Entity not found" before this fix). `button.porch_front_front_porch_temp_sensor_front_porch_temp_sensor_restart` (front-porch) also works, no duplication.

**Known cosmetic side effect, not fixed by this card:** naming both buttons with the device name already included (e.g. "Salt Sensor Restart") caused HA to double up device-name + entity-name when generating entity_id/friendly_name — both ended up more verbose/mangled than intended (front-porch's especially, from a brief three-way collision window while the stale topic was being cleared). Functionally correct, cosmetically ugly. **Joseph is doing the entity_id cleanup himself** via HA's UI (Settings → Devices & Services → Entities → rename entity ID) — not scripted, since HA's entity registry rename isn't exposed over the REST API, only the frontend's WS API.

**Related:** CARD-0180 (hiking-monitor — origin case, found this collision as a side effect).

---

---

### CARD-0179 · [idea] [infrastructure] Route captured voice notes to LogSeq, alongside the kanban PR pipeline — low priority

**Status:** Backlog

**Priority:** Low — marked 2026-08-19 (Joseph). No hard deadline; revisit at Planning whenever Joseph wants to pick it up.

**Raised 2026-08-17 12:03 MST (Joseph, via voice note):** Originally arrived as PR #21 (CARD-XXX) from the email-idea-check pipeline (CARD-0151/CARD-0173) with the garbled transcribed subject "sending notes to log seek" — asked Joseph directly, actual idea is "sending notes to LogSeq." PR #21 closed without merging; this card replaces it with a real interview pass.

**Interviewed 2026-08-17:**
- LogSeq setup: points at a local folder of markdown files, kept in sync across devices via LogSeq's own built-in Sync (not Syncthing/Dropbox/Git). That folder does not yet exist on either the Pi or the M8 — LogSeq Sync has no Linux CLI/daemon, so there's no obvious server-side hook into it yet. **Open design problem, not yet solved:** how does a script running on Pi/M8 get a note into a graph that only LogSeq's proprietary Sync touches? Candidates to evaluate at Planning time: a git-backed LogSeq graph (LogSeq supports this natively as an alternative to LogSeq Sync) that the pipeline commits/pushes into; some other cloud-synced folder LogSeq Sync itself can be pointed at; or accepting this only works if Joseph moves off LogSeq Sync for this graph. None of these confirmed yet.

**Researched 2026-08-19 — leading candidate found.** LogSeq has a local HTTP API (Settings → Features → "HTTP APIs server", listens on `127.0.0.1:12315/api`, Bearer-token auth, exposes the plugin SDK — `logseq.Editor.insertBlock` etc., full method list at plugins-doc.logseq.com) — but it's local to wherever the app is actively running, not a cloud API. The candidate this unlocks: run the actual LogSeq app headlessly in a Docker container on the M8 (Xvfb virtual display + noVNC/HTTP API — community pattern, not an official LogSeq deployment mode), signed into Joseph's account with LogSeq Sync enabled as normal. Since it's the literal same client, Sync would keep it in sync with laptop, Pixel 10, and Pixel Tablet exactly like a desktop install — Sync operates at the app/account level, not tied to a physical desktop. And because the API and the app share a host, the M8's own pipeline script can hit `localhost:12315` directly, no cross-device dependency.

Checked two candidate Docker images for this pattern:
- **`CorrectRoadH/docker-logseq`** — actively maintained. Last commit 2026-06-06 (tracks LogSeq's latest release, merged an outside contributor's PR), 0 open issues, 9 stars.
- **`SimonTheCoder/logseq_in_container`** — effectively abandoned. Two commits total, both from its 2024-04-30 creation, one unaddressed open issue, no activity since.

`CorrectRoadH/docker-logseq` is the only real candidate between the two — but worth being honest that even it is a small, lightly-used project (9 stars, essentially one maintainer plus one contributor), so this stays in "unofficial community pattern" territory regardless of which image gets picked; not something with broad verification behind it.

Real caveats before this becomes the plan (not yet resolved): unofficial/unsupported deployment mode (crashes, LogSeq updates breaking Sync, would need a restart policy/health check like any other JCTsh Docker service); heavier footprint than the M8's other Docker apps (NetAlertX, Immich, hike-izer-web are lightweight web services, a full Electron+Chromium container is not); the HTTP API must stay off `hikes.jctnet.com`'s Cloudflare Tunnel — localhost/Tailscale-only, same posture as everything else on the M8.
- Relationship to the existing kanban pipeline: **alongside, not a replacement.** CARD-0151/0173's voice-idea → email → kanban PR path stays as-is for actionable work items. LogSeq becomes a second destination for looser notes/thoughts that aren't necessarily a card.
- Routing (how the pipeline tells "this is a LogSeq note" apart from "this is a kanban idea"): leaning toward a second Gmail plus-alias (e.g. `joscthomas+logseq@gmail.com`) alongside the existing `+kbc` one, so which inbox it lands in decides the route with no parsing needed — **but Joseph flagged this as still undecided**, not locked in.

**Acceptance criteria:** not yet written — the LogSeq-folder-access mechanism above needs to be resolved first; real acceptance criteria depend on which mechanism gets picked. Revisit at Planning.

**Done when:** a voice note sent to the LogSeq-routed address lands as a note in Joseph's actual LogSeq graph, verified live (not just "the pipeline ran without erroring").

**Related:** CARD-0151 (email-to-kanban-card watcher this reuses/sits alongside), CARD-0173 (voice idea capture, Pixel to kanban PR — the existing pipeline this is *not* replacing).

---

### CARD-0178 · [enhancement] [photo-quality-review] Auto-select the larger photo for same-owner near-duplicate pairs, sort groups by size — RESOLVED 2026-08-17 12:05 MST
**Status:** Done

Archived to `components/photo-quality-review/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5412B, over the 5000B size threshold.

---

### CARD-0177 · [enhancement] [maintenance] Back up Pi1's HA + Mosquitto state to the M8 — RESOLVED 2026-08-16 18:50 MST
**Status:** Done

Archived to `core/maintenance/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5197B, over the 5000B size threshold.

---

### CARD-0176 · [idea] [hike-izer] Website tweaks: clean up verbiage, hide sections with no data — auto-opened from jctsh-core — RESOLVED 2026-08-16 20:35 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6792B, over the 5000B size threshold.

---

### CARD-0175 · [idea] [photo-server] Geofence album for Immich — auto-opened from jctsh-core

**Status:** Backlog

**Raised 2026-08-15 15:00 MST**, via CARD-0151's email-idea pipeline (GitHub PR #16). Raw idea: a geofence album for Immich.

**Interviewed 2026-08-16.** Concretely: identify a place by name or lat/lon, define a radius around it, and have an album auto-collect every photo (existing and future) whose GPS EXIF falls within that radius — not a one-time manual curation. Multiple such geofenced places over time, not just home.

**Acceptance criteria:**
1. Check Immich's own map/search/smart-album features first — confirm whether a built-in capability (geo search, saved search as album, etc.) already covers "define a point+radius, auto-populate an album from it" before assuming custom tooling against Immich's API is needed.
2. If native support is insufficient, scope the custom-tooling approach (API-driven: query photos by GPS radius, maintain album membership as new photos land).
3. Prove it live: define at least one real place (e.g. home) with a radius, confirm existing matching photos populate the album, then confirm a newly imported photo within that radius gets added automatically without manual intervention.

**Done when:** at least one geofenced album is live on the real Immich instance, verified to both backfill existing matches and auto-add new ones.

**Related:** CARD-0151 (the email-idea capture pipeline this came in through), Immich (runs on the M8).

---

### CARD-0174 · [idea] [hike-izer] Add a speaker icon to the web page for hearing the birds — auto-opened from jctsh-core — RESOLVED 2026-08-16 20:35 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6391B, over the 5000B size threshold.

---

### CARD-0173 · [idea] [tos] Voice input for a new kanban card from my phone — auto-opened from jctsh-core — RESOLVED 2026-08-16 20:20 MST
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7174B, over the 5000B size threshold.

---

### CARD-0172 · [idea] [infrastructure] Disaster Recovery — auto-opened from jctsh-core — RESOLVED 2026-08-16 19:30 MST
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-08-22 (CARD-0193) — 9049B, over the 5000B size threshold.

---

### CARD-0171 · [enhancement] [infrastructure] M8 UEFI Secure Boot KEK CA firmware update available — auto-opened from photo-server — RESOLVED 2026-08-16 19:00 MST

**Status:** Done

**Auto-generated 2026-08-01 14:00 MST from photo-server's maintenance check** (GitHub PR #5). Raw finding: "M8 maintenance: 2 firmware update(s) available: KEK CA: UEFI Secure Boot Key Exchange Key; KEK CA: UEFI Secure Boot Key Exchange Key."

**Scoped 2026-08-16, not yet built.** Re-checked live via `fwupdmgr get-upgrades` on the M8 — still genuinely pending (not stale like PRs #7/#8 were for the HA finding). This is a single KEK CA device with two candidate release variants (AMI, ASUS) — the auto-generated "2 firmware updates" title is fwupdmgr listing both candidates for the same device, not two separate items. **Urgency: High** — a Secure Boot Key Exchange Key update, same class of finding as the dbx update CARD-0095 already applied, but not covered by that pass (which handled UEFI CA + dbx only).

**Acceptance criteria:**
1. Stage the update: `fwupdmgr update -y --no-reboot-check` (finalizes on next boot, same as CARD-0095's dbx update — UEFI-level fwupd updates apply via a staged capsule).
2. Reboot the M8 to finalize.
3. Verify live: `fwupdmgr get-upgrades` no longer lists the KEK CA update, all 8 containers back to Docker `healthy`, Tailscale reconnected, `hikes.jctnet.com` (Cloudflare Tunnel → hike-izer-web) reachable — same verification checklist CARD-0095 used for its own reboot.

**Real blocker found, 2026-08-16: no passwordless sudo on the M8.** Unlike the Pi's `pi` user (blanket `NOPASSWD: ALL`, a Raspberry Pi OS default), the M8's `jct` user needed an interactive sudo password — couldn't stage the firmware update from this session at all until that was resolved. Joseph added the same blanket `NOPASSWD: ALL` for `jct` (`/etc/sudoers.d/jct-nopasswd`, run by Joseph directly since it needed his password once, validated with `visudo -c` before relying on it), matching the Pi's existing posture. Documented in `CLAUDE.md`'s SSH section, since this is a real, standing change to the M8's security posture — worth being visible given the M8's real internet-facing surface area (`hikes.jctnet.com`), not a routine detail to bury in a closed card.

**Update applied and verified live, 2026-08-16 ~19:00 MST — clean, no incident this time** (unlike CARD-0170's HA update the same session):
1. Staged: `sudo fwupdmgr update -y --no-reboot-check` — "Successfully installed firmware."
2. Baseline recorded before reboot: all 8 containers healthy.
3. `sudo reboot` — M8 back reachable over SSH within the poll window, no manual intervention needed.
4. `fwupdmgr get-upgrades`: KEK CA now listed under "no available firmware updates," overall "No updates available" — firmware confirmed finalized.
5. All 8 containers came back automatically, briefly `health: starting`, settled to `healthy` within under a minute — no manual restart needed.
6. Tailscale: `m8` shows normal status, a live ping to the Pi over Tailscale succeeded.
7. `https://hikes.jctnet.com/` — `HTTP 200`, confirmed reachable from outside the M8 itself (through the full Cloudflare Tunnel path, not just a local check).

**Done when:** KEK CA firmware confirmed updated and M8 confirmed fully healthy post-reboot per the checklist above. **Met**, all seven checks above passed clean.

**Related:** CARD-0095 (M8 OS/firmware maintenance backlog — established the update policy and verification pattern this follows; that pass covered UEFI CA/dbx but not this KEK CA item), CARD-0170 (the same session's HA update, which hit a real Docker daemon incident — this one, by contrast, went cleanly).

---

### CARD-0170 · [enhancement] [infrastructure] Container image updates: home-assistant: 2026.8.2 available (running 2026.8.1) — auto-opened from jctsh-core — RESOLVED 2026-08-16 18:00 MST

**Status:** Done

**Auto-generated 2026-08-15 13:30 MST from jctsh-core's maintenance check** (GitHub PR #13). Raw finding: Container image updates: home-assistant: 2026.8.2 available (running 2026.8.1).

**Scoped 2026-08-16, not yet built.** Landed as a proper Backlog card rather than left as a raw auto-opened stub. Superseded two earlier stale findings for the same underlying update chain (PR #7: 2026.8.0 available when HA was still on 2026.5.1; PR #8: 2026.8.1 available, same baseline — both closed 2026-08-16 once HA was confirmed already running 2026.8.1, past both).

**Release notes checked, 2026-08-16 (Joseph confirmed home before proceeding, per CARD-0130's established gating).** 2026.8.2's full changelog (32 items, checked against the actual GitHub release, not just the raw finding text) is a pure bugfix patch — Teslemetry, Husqvarna, TP-Link Omada, SMTP, Tado, Midea, KNX, Matter, and similar integration-specific fixes, none of which this deployment uses. Zero items touch MQTT, `automations.yaml` schema, SmartThings, Docker, or reverse proxies/HTTP. Confirmed still genuinely current: HA was still running 2026.8.1 live at check time.

**Update applied, 2026-08-16 ~18:00 MST:** `docker compose pull homeassistant` (clean), then `docker compose up -d homeassistant`.

**Real incident during the recreate, not just a routine restart — Docker's own daemon failed to stop the old container cleanly:** `cannot stop container: ...: tried to kill container, but did not receive an exit event`. Confirmed via `docker ps`/`docker info`/`journalctl -u docker`: SIGTERM (10s) then SIGKILL (10s) both timed out against the running container before Docker's own compose command gave up and errored out — HA was briefly still up on the old image at that point (lucky timing), but containerd finished the kill moments later regardless, and HA went fully down (`Exited (137)`, HTTP not responding) independent of what compose's own error message suggested. **This was a real, if brief, live outage on the household's HA**, not a no-op failed command — caught immediately by checking actual container/HTTP state rather than trusting the compose error text at face value.

**Recovery:** re-ran `docker compose up -d homeassistant` once the old container had actually fully exited — this started the new image successfully, but under a temporary rename Compose had created mid-swap (`a21509cd7bb9_homeassistant`) instead of the real service name. Fixed with a plain `docker rename` (no restart needed, zero additional downtime) once the container was confirmed healthy. `docker ps -a` confirmed clean afterward — exactly one container, correctly named.

**Verified live, real device, all four checks:**
- Version: `2026.8.2` via `/api/config` (not just "the container restarted").
- Docker health check: `healthy`.
- Automations: 13 loaded (10 enabled), confirmed via `/api/states` — but this needed a second look, since the *first* check (run too soon after the healthcheck passed) showed **0 automations and 339 total entities**, against 772 total entities and 13 automations a few checks later. Real startup-timing lag on this memory-constrained Pi (905Mi RAM, seen down to 43Mi free mid-recorder-migration), not a regression — Docker's `healthy` state reflects the container process/port being up, not that HA has finished loading YAML-based platforms like `automation:`. Re-verified stable on a second pass before trusting it.
- SmartThings: 8 `smartthings`-domain entities present.
- Two automation entities show `unavailable` (`Traveling Lights - Night Off`, `CARD-0158 - Reboot Health Check Reminder`) — confirmed **pre-existing, not caused by this update**: neither appears anywhere in the live `automations.yaml` (grep, zero matches), consistent with CARD-0158's own reminder-removal commit from earlier — these are stale entity-registry leftovers from an already-completed prior removal, not a new regression.

**Done when:** HA is confirmed running 2026.8.2 with the above verification complete, no regressions found. **Met** — the daemon-level stop failure and brief outage were a real incident along the way, but root-caused, recovered cleanly, and confirmed to have left no lasting damage (correct version, correct name, correct health, no automation/SmartThings regression).

**Related:** CARD-0130 (the same recurring HA-image-update pattern, template for acceptance criteria and verification steps here), CARD-0158 (the reminder automation whose stale registry entry was ruled out as a regression here; also `reboot-health-check.py`, not used this time since a manual check was already in progress when the real incident surfaced).

---

### CARD-0169 · [idea] [homeassistant] Scheduled volume levels by Google Home speaker, by time window
**Status:** Defer

**Raised 2026-08-15**, surfaced while testing CARD-0145's Ring motion announcements — Joseph asked whether HA can fix each speaker's volume by time window (e.g. quieter overnight), separate from that card's own announcement logic.

**Interview so far, 2026-08-15 (partial — specific windows/levels not yet gathered):**
- **Scope: audio speakers only**, not displays or TVs — `media_player.garage_speaker`, `media_player.groom_speaker`, `media_player.master_bedroom_speaker`, `media_player.master_bedroom_speaker_2`, `media_player.patio_speaker`. (Two of these, `master_bedroom_speaker_2` and `patio_speaker`, were confirmed `unavailable`/offline during CARD-0145's testing — not blocking for this card, same as there.)
- **Outside any defined window, enforce a default/baseline level** — not left unmanaged. Every device gets both a scheduled level per window and a default for all other times.
- **Confirmed technical feasibility**: Cast/Google Home volume is a persistent device-level setting, not a per-message one — `media_player.volume_set` (also `volume_up`/`volume_down`/`volume_mute`) confirmed available on this HA instance. Once set, a level holds for all subsequent playback (TTS, music, anything) until changed again — observed indirectly during CARD-0145 testing, where each speaker's `volume_level` stayed consistent across multiple TTS calls without being re-set each time. This means implementation is straightforward: one automation (or per-window automations) calling `volume_set` at each window's start time, holding until the next transition.

**Still needed before Planning:** the actual per-device volume levels and time windows — not yet gathered.

**Done when:** each of the 5 speakers holds its scheduled volume level during its defined time windows and its default level otherwise, verified live (not just configured) against real device state.

**Related:** CARD-0145 (the Ring announcement automation this surfaced during; shares 3 of the 5 target speakers).

---

### CARD-0168 · [bug] [homeassistant] Remove deprecated `http:` YAML block, resync stale configuration.yaml — RESOLVED 2026-08-15 02:28 MST
**Status:** Done

**Raised 2026-08-14, surfaced mid-CARD-0145 build** by a live HA repair warning: "HTTP YAML configuration is ignored after migration... this stops working in version 2027.2.0... remove the http: block from your configuration.yaml. Manage the HTTP configuration from the UI under Settings > System > Network."

**Live config on the Pi** (`/mnt/jctsh-logs/homeassistant/configuration.yaml`):
```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 127.0.0.1
    - ::1
```
This is the nginx reverse-proxy trust setting from CARD-0096/CARD-0141's HTTPS work — HA already migrated it into its own UI-managed storage and is ignoring the YAML, per the warning.

**Real gap found while investigating:** the repo's tracked `core/homeassistant/configuration.yaml` doesn't contain this block at all — it's out of sync with the live Pi file, meaning the repo copy has drifted from reality more broadly than just this one setting.

**Interview, 2026-08-14:**
- Verify before removing: check Settings → System → Network on the live HA UI confirms `use_x_forwarded_for` + `trusted_proxies` (127.0.0.1, ::1) actually carried over correctly, don't just trust the warning text — then delete the `http:` block from `configuration.yaml` and restart HA, confirming the nginx-fronted login (Tailscale HTTPS path, CARD-0096/CARD-0141) still works afterward.
- Same card also resyncs the whole repo copy of `configuration.yaml` from the live Pi file (not just the `http:` block) while it's already being pulled down for this fix, so the repo stops being stale more broadly.

**Done when:** the UI-side migration is confirmed correct, the `http:` block is gone from both the live Pi config and the repo's tracked copy, HA restarts clean, the nginx-fronted HTTPS login still works, and the repo's `configuration.yaml` matches the live file end-to-end.

**Verified and resolved, 2026-08-15 02:28 MST.** Checked the live migrated config directly (`.storage/http` on the Pi, via `sudo cat`) before touching anything: `use_x_forwarded_for: true` and `trusted_proxies: ["127.0.0.1/32", "::1/128"]` both confirmed carried over correctly, `yaml_migration_done: true` — didn't just trust the warning text. Removed the `http:` block from the live `configuration.yaml`.

**Restart hit the known s6-supervised gotcha** (`docker restart` failed — "tried to kill container, but did not receive an exit event"; container exited but didn't auto-restart despite `unless-stopped`) — recovered with a plain `docker start`. Docker's own healthcheck reported `healthy` well before HA's actual startup finished (`/api/config` showed `state: NOT_RUNNING`, only 127 of the eventual 772 entities loaded, `automation.*` domain briefly empty) — waited for `state: RUNNING` before treating anything as confirmed, avoiding a false "it's broken" read on `automation.card_0145_ring_motion_announcement` mid-boot.

**All "Done when" criteria verified live, not just configured:** `.storage/http` unchanged post-restart (`error: null`); nginx-fronted HTTPS login (`https://pi1.tailfe828a.ts.net/`) returns HTTP 200; HA logs since the restart contain no "ignored after migration" warning; `automation.card_0145_ring_motion_announcement` reloaded correctly with its trigger history intact; repo's `core/homeassistant/configuration.yaml` diffed byte-for-byte identical against the live file (no edit needed — the repo copy already lacked the block).

**Related:** CARD-0096 (the rename that put nginx in front of HA), CARD-0141 (HA HTTPS/reverse-proxy setup this trust config supports), CARD-0145 (automation whose survival through this restart was directly verified).

---

### CARD-0167 · [enhancement] [infrastructure] Close CARD-0096's mDNS transition-window aliases — RESOLVED 2026-08-17 12:11 MST
**Status:** Done

**Raised 2026-08-14 16:15 MST**, split out from CARD-0096 (Done) so this last step doesn't get lost inside an already-closed card. Two systemd units are still deliberately running: `raspberrypi-mdns-alias.service` (Pi) and `photo-server-mdns-alias.service` (M8), each publishing the old hostname as a static mDNS alias for the unchanged real IP, per CARD-0096's own transition-window design.

**Due date reasoning:** 2026-08-17 (Monday) 09:00 MST — chosen specifically so both hosts' weekly scheduled reboots (Pi Mon 3:00 AM, M8 Mon 4:00 AM — `jctsh-network.md`) happen first. A clean reboot survival is a real stability test, not just elapsed time — if anything were silently still depending on the old name in a way the alias masks, a reboot is exactly the kind of event likely to surface it. 09:00 gives buffer after both.

**Interactive, not automated** — Joseph explicitly declined an autonomous/scheduled agent run for this (2026-08-14): do this in a live session with him present, same human-in-the-loop pattern as the rest of CARD-0096, not unattended.

**Closing steps (from CARD-0096's own Phase 1/Phase 2 step 9):**
1. Fresh repo-wide grep for `raspberrypi`/`photo-server` — confirm nothing new started depending on the old names since CARD-0096 landed.
2. Stop, disable, and remove both alias systemd units (`raspberrypi-mdns-alias.service` on the Pi, `photo-server-mdns-alias.service` on the M8).
3. Confirm the old `.local` names now correctly **fail** to resolve — proof nothing was silently still depending on them. Run this check from a Linux box (the Pi or M8 itself via SSH), not this Windows laptop, per CARD-0096's own noted mDNS-reliability caveat on this specific machine.
4. Both hosts' core services (HA, MQTT, Node-RED, Immich, NetAlertX, hike-izer-web) still healthy post-cleanup.

**Done when:** both alias services are removed, both old `.local` names confirmably no longer resolve, and nothing broke in the process.

**Closed 2026-08-17 12:11 MST:**
1. Fresh repo-wide grep for `raspberrypi`/`photo-server` — no live/runtime config depends on the old names. The 3 ESP32 devices flagged as load-bearing in CARD-0096's own audit (`front-porch-temp-sensor`, `garage-radar`, `salt-sensor`) already use the IP (`192.168.1.117`) in their `secrets.yaml`, not the hostname. Remaining hits are stale doc references only (`components/m8/README.md`, `network.md`, `operations.md`, the phase2-planning/claude-code-instructions docs, an archived Arduino sketch's `secrets.h`, a `.claude/settings.local.json` permission string) — pre-existing drift from before this card, not new dependencies, and out of this card's scope.
2. Both alias units stopped, disabled, and removed (`raspberrypi-mdns-alias.service` on the Pi, `photo-server-mdns-alias.service` on the M8), `daemon-reload` run on both.
3. Confirmed from each host itself (not this Windows laptop, per the mDNS-reliability caveat): `avahi-resolve -n raspberrypi.local` (on the Pi) and `avahi-resolve -n photo-server.local` (on the M8) both now fail with "Timeout reached" — the old names no longer resolve.
4. Both hosts' core services healthy post-cleanup: Pi — `homeassistant` container healthy, `mosquitto`/`nodered`/`jctsh-logging` all active. M8 — all 8 containers (`immich_*`, `netalertx`, `hike-izer-*`) up and healthy.

**Related:** CARD-0096 (the rename this closes out).

**Related:** CARD-0096 (the rename this closes out).

---

### CARD-0166 · [enhancement] [infrastructure] Synchronize room/area names across HA, Google Home, and SmartThings — HA as master
**Status:** Backlog

**Raised 2026-08-14**, directly motivated by CARD-0165's real collision: the front porch temperature sensor's Google Assistant exposure was correctly named and area-assigned, but "what's the front porch temperature" kept answering with a pre-existing SmartThings front-door sensor instead — root-caused to Google routing temperature-type queries by room/context rather than literal device name, and the word "front" alone was enough to misroute. Also directly surfaced a duplicate-area mistake caught and fixed live during that same card (created `Front Porch` when `Porch (Front)` already existed).

**Scope: that collision class specifically, plus a general room-name audit/cleanup while in there** — not a fully open-ended reorganization.

**Approach: HA as the source of truth, one-time manual audit and fix, no ongoing sync automation** (decided 2026-08-14 — not building a recurring drift-checker for this).
1. Enumerate HA's Areas (`config/area_registry/list` over the WS API, same method used in CARD-0165) as the canonical list.
2. Enumerate SmartThings' own room names and Google Home's own room names (both live outside HA — SmartThings has its own separate room concept independent of HA's Areas per CARD-0164's research, and Google Home's rooms are populated by the `roomHint` HA sends *plus* whatever SmartThings' own separate direct Google Home link contributes).
3. Identify mismatches/overlaps — especially near-miss collisions like `Porch (Front)` vs. a SmartThings-side "front door"-ish room that could plausibly still confuse Google's room-based query routing, not just exact-string duplicates.
4. Align SmartThings and Google Home's naming to match HA's Area names exactly, fixing mismatches at the source (SmartThings app / Google Home app), not by renaming HA's side to match them.
5. Re-test the exact failure mode CARD-0165 hit (a voice query whose wording overlaps two differently-roomed devices) after alignment, to confirm the fix actually holds — not just that names now match on paper.

**Known constraint carried over from CARD-0165's research:** Google Home's room assignment for HA-exposed entities is a one-way push (HA Area → Google `roomHint`) with no reverse sync — confirmed against HA's own docs. SmartThings' side is a separate, independent room concept with its own direct Google Home link, unrelated to HA's Areas. This card is a manual alignment across three genuinely separate systems, not a technical integration fix.

**Done when:** HA's Areas, SmartThings' rooms, and Google Home's rooms agree by name for every shared device (Ring, the front-porch sensor, and anything else spanning more than one of the three systems), and a live voice-query re-test of CARD-0165's specific collision confirms it no longer misroutes.

**Related:** CARD-0165 (the collision that surfaced this), CARD-0146/CARD-0164 (prior research into HA/SmartThings/Google Home's room and voice-routing behavior).

---

### CARD-0165 · [enhancement] [front-porch-temp-sensor] Ask Google Home for the front porch temperature — RESOLVED 2026-08-14
**Status:** Done

Archived to `components/front-porch-temp-sensor/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5639B, over the 5000B size threshold.

---

### CARD-0164 · [enhancement] [infrastructure] Samsung ending free SmartThings API access October 2026 — decide pay vs. migrate before then
**Status:** Backlog

**Raised 2026-08-14 08:35 MST**, found while researching CARD-0146's Ring-live-view question (checking whether SmartThings could expose Ring camera entities to HA — it can't, but that research surfaced this instead). Confirmed directly against HA's own official integration docs (`home-assistant.io/integrations/smartthings/`), not a secondhand summary:

> "Samsung has announced that free access to the SmartThings API will be phased out starting in October 2026. After this date, the SmartThings API access will require a paid Personal Plan subscription ($4.99/month)."
>
> "If you use this integration, you will need to either subscribe to Samsung's Personal Plan or migrate your devices (like local Zigbee/Z-Wave devices) before October 2026 to avoid a service disruption."

**Blast radius, confirmed live against this HA instance (not estimated):** queried `integration_entities("smartthings")` directly — well over 100 entities, spanning nearly every category JCTsh depends on SmartThings for: all door/motion/moisture/acceleration sensors, most lights, the garage door open/close switches (`components/automatic-garage-door-opener-closer/`), the front door lock, all Ring presence/motion/doorbell entities, every scene (`good_morning`, `not_home_lights_off`, etc.), the salt-sensor's SmartThings-facing switches, smoke/CO detectors, and more. If the integration breaks, this isn't a narrow feature loss — it's most of the household's automation surface.

**Subscription details, confirmed against Samsung's own blog post (`blog.smartthings.com`), not just the HA docs summary:**
- $4.99/month for individual/non-commercial developers; separate, undisclosed commercial tier pricing exists for larger integrators.
- Samsung's own words: *"Free access will remain available through Q3. We will not begin applying the new usage limits or phasing out free access until October 2026."*
- **Only affects third-party API consumers like HA's integration** — Samsung's post explicitly says this *"does not affect the millions of SmartThings users who use the SmartThings App."* The native SmartThings app stays free regardless.
- Rate limits and exact Personal Plan feature scope aren't published yet — genuinely still evolving; worth re-checking closer to October rather than deciding on today's information alone.

**Prior history, per Joseph's recollection 2026-08-14 (not independently verified against repo history — predates this repo's own documentation, worth capturing regardless):** a direct SmartThings API approach (raw Personal Access Token) was tried before HA's OAuth-based integration was adopted, and abandoned because the PAT's tokens expired too quickly to be workable. HA's integration was the fallback that actually worked — but it required Nabu Casa specifically because SmartThings' OAuth setup needs an externally reachable HTTPS callback URL (`CLAUDE.md`'s own documented reasoning for why Nabu Casa is required here). Relevant now: Nabu Casa isn't a *new* cost either the "pay" or "migrate" path would introduce — it's already a sunk dependency for other reasons (the SmartThings OAuth callback itself, HA's external HTTPS URL generally), so using its Google Assistant bridge for any migrated devices (see the `*_vswitch` point below) adds no additional subscription on top of what's already committed. Also means: don't reconsider a raw-PAT approach as an alternative to paying the new $4.99/mo fee — already tried, already found unworkable for reasons unrelated to price.

**Not yet decided — captured for a deliberate decision before the deadline, not decided here (Joseph's call, 2026-08-14):**
- **Pay** ($4.99/mo, ~$60/year) — simplest, keeps everything working exactly as-is, no migration effort.
- **Migrate** — move devices to local protocols where the hardware supports it. Mapped against this household's actual entity mix, not generically:
  - **Ecobee is a free win regardless of the broader decision** — `climate.ecobee` and its sensors are bridged through SmartThings today, but Ecobee has its own independent, official HA integration via Ecobee's own cloud API. No protocol re-pairing, no hardware — just swap integrations.
  - **Most lights, most sensors, the front door lock** are likely genuine Zigbee/Z-Wave hardware (e.g. Sengled is Zigbee, Inovelli is Z-Wave) currently paired to a SmartThings hub, not SmartThings-proprietary — could migrate to a local Zigbee2MQTT/Z-Wave JS setup (needs a USB coordinator). Removes cloud dependency, but real cost: each device needs a physical reset-and-repair, mesh routing rebuilds, and every scene (`good_morning`, `not_home_lights_off`, etc.) needs rebuilding as a native HA scene/script.
  - **The `*_vswitch` entities are a bridge pattern worth rethinking, not just migrating.** These aren't hardware at all — they're `CLAUDE.md`'s own documented pattern of SmartThings virtual switches created specifically to reach Google Home voice control (salt sensor, garage door, etc.). This household already has **Nabu Casa active**, which includes HA's own native Google Assistant Smart Home integration — a direct path to Google Home that doesn't need SmartThings as a middleman. If the underlying devices move to local control, this bridge pattern could be replaced outright, not preserved.
  - **Ring stays cloud-dependent regardless** — SmartThings or the native `ring` integration, both go through Ring's cloud (see CARD-0146's research). Migrating away from SmartThings doesn't reduce Ring's own cloud dependency.
- **Hybrid** — pay short-term while migrating the highest-value/easiest devices opportunistically (Ecobee first, since it's free), not an all-or-nothing choice.

**Timeline:** deadline is October 2026 — roughly 2 months out from when this card was raised. Worth revisiting well before then, not at the last minute, given the entity count involved if migration ends up being the direction.

**Done when:** a direction is chosen (pay, migrate, or hybrid) and, if migrating any devices, each migrated device is confirmed still working via its new integration path before its SmartThings entity is retired — never cut over blind.

**Related:** CARD-0146 (the investigation that surfaced this), `ENVIRONMENT.md` (SmartThings device inventory), CLAUDE.md's SmartThings Integration section.

---

### CARD-0163 · [bug] [logging] Non-heartbeat log entries can get stuck unflushed indefinitely in log_server.py's `_pending` buffer — RESOLVED 2026-08-14 08:30 MST
**Status:** Done

**Found 2026-08-14 08:17 MST**, while verifying CARD-0161's webhook fix in production. A real, correctly-signed NetAlertX "New device detected" webhook was captured live: HMAC verification confirmed correct three independent ways (Node-RED's own JS re-verification, an independent Python recomputation, and a direct MQTT capture on `jctsh/components/netalertx/log` showing the exact right message with correct event-time). The message never appeared on the log dashboard or in `jctsh.log` despite all of that working correctly — the webhook/Node-RED pipeline was not the problem.

**Root cause, found by reading `log_server.py` directly:** `_store_entry()` buffers every *non-heartbeat* message (any component, any category) in a single-slot module-level `_pending` variable. It only gets written to `_entries`/disk when a **different** `(component, category, message)` arrives afterward and triggers `_flush_pending()`. Heartbeat-prefixed messages go through a completely separate mechanism (`_hb_groups`) and never touch or flush `_pending`. Confirmed live: `state.json`'s `_last_seen.netalertx` held the exact right entry (`count: 3`, correctly deduping two manual replays against the original) — sitting correctly in memory, genuinely never flushed, because nothing else non-heartbeat happened anywhere in the system afterward to bump it out.

**Same class of bug as CARD-0068/CARD-0079, but not covered by that fix.** Those cards added a 15-minute forced-rotation timeout specifically for `_hb_groups` (stuck heartbeat-collapse groups). The general `_pending` singleton has no equivalent timeout safeguard — any single non-heartbeat message, from any component, can sit invisible on the dashboard indefinitely if no other differing message happens to arrive after it. Not netalertx-specific and not webhook-specific; it's a gap in the core buffering logic any component's Alert/System/Sensor message could hit.

**Built and verified live, 2026-08-14:** added `PENDING_MAX_AGE_SEC = 60` and `_flush_aged_pending()` (mirrors `_flush_aged_hb_groups()`'s pattern exactly) to `core/logging/log_server.py`. Deliberately much shorter than `HB_GROUP_MAX_AGE_SEC`'s 15 minutes — these are discrete one-off events meant to be promptly visible, not a collapsing counter tuned for a steady heartbeat stream. The periodic flush thread (renamed `_hb_flush_thread` → `_flush_thread` since it now covers both) checks every `HB_FLUSH_CHECK_INTERVAL` (60s), so worst-case latency is ~60-120s, not indefinite. `_flush_pending()` also fixed to strip the new internal `_started_at` field before writing to `_entries`/disk, matching `_flush_hb_group()`'s existing pattern.

Deployed (`scp` + `sudo systemctl restart jctsh-logging`), confirmed clean restart (`Restored 1000 entries, 10 known components` — state survived). **Live test**: published a one-off Alert message with nothing else to bump it out — confirmed absent from `jctsh.log` immediately after (correctly still pending), then confirmed present after the periodic thread caught it, landing within the expected ~60-120s window. Exactly the failure mode this fixes, reproduced and verified closed.

**Related:** CARD-0161 (webhook fix verification that surfaced this), CARD-0068/CARD-0079 (the analogous `_hb_groups` timeout fix this generalizes), CARD-0078 (original webhook HMAC workaround, confirmed unaffected by this bug), `core/logging/log_server.py`.

---

### CARD-0162 · [enhancement] [tos] PR-to-kanban-card landing process for CARD-0128 auto-opened findings — RESOLVED 2026-08-14 07:28 MST
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6679B, over the 5000B size threshold.

---

### CARD-0161 · [enhancement] [netalertx] Container image updates: netalertx: v26.8.5 available (running 26.7.1) — auto-opened from photo-server — RESOLVED 2026-08-14 08:27 MST

**Status:** Done

**Raised 2026-08-13 06:30 MST**, auto-generated from photo-server's maintenance check (PR #10). The raw finding bundled two updates in one run — `cloudflared: 2026.8.0 available` and `netalertx: v26.8.5 available (running 26.7.1)`. The cloudflared half is stale: CARD-0160 already landed cloudflared 2026.8.2 (newer) from PR #11. This card covers the still-live half: the NetAlertX update.

**Risk assessment (researched against NetAlertX's actual GitHub release notes, not just the raw finding text):** Single-version jump, `v26.7.1` → `v26.8.5` — no intermediate releases. Upstream's own "Breaking changes" section lists a bridge-mode container-capability requirement (`NET_RAW`/`NET_ADMIN`/`NET_BIND_SERVICE`); not a risk here — `components/netalertx/docker-compose.yml` already grants all three (plus `CHOWN`/`SETUID`/`SETGID`), and this deployment runs `network_mode: host`, the mode the warning says isn't even affected. No MQTT-related changes in either release, so `components/netalertx/netalertx.flow.json`'s MQTT integration is low risk. A plugins-directory move is flagged "next release," not this one, and doesn't apply anyway since no custom plugins are mounted.

**One change directly relevant to this repo's history:** upstream fixed `netalertx/NetAlertX#1720` — the webhook payload serialization bug CARD-0078 found and worked around (Node-RED currently re-serializes NetAlertX's payload to match its *buggy* signature before verifying HMAC). CARD-0089 already tested this exact fix against `netalertx-dev-unsafe` on 2026-07-24 and confirmed it three independent ways, including a live HMAC recompute that matched byte-for-byte. v26.8.5's changelog wording ("payloads are serialized once for consistent logging and signature generation") matches that confirmed fix exactly, so this is a known-good fix landing in a real release, not an unknown.

**Not a host-reboot update — doesn't need CARD-0129/CARD-0130's home-LAN gating.** That mitigation existed because HA is the household coordination hub and kernel/Docker-engine updates require a host reboot. This is a container-only update with a trivial rollback (redeploy the previous image tag); no reboot involved.

**Done when (all verified live, 2026-08-14):**
1. ✅ Container updated to 26.8.5, confirmed via `[Version check] Running the latest version` log line.
2. ✅ Device database intact — 49 devices before and after, DB migration ran clean.
3. ✅ MQTT publishing confirmed working (live `mosquitto_sub` capture matched device counts).
4a. ✅ **Webhook signature verification confirmed correct in production, three independent ways**: Node-RED's own re-verification passing (200 OK, only returned post-verification), an independent Python HMAC recompute against the real captured payload, and a direct MQTT capture of the correctly-composed resulting log message. Found and fixed a real, separate bug along the way (CARD-0163 — the message was correctly verified/composed but got stuck unflushed in the log server's own buffering, not a webhook problem).
4b. ✅ **Workaround removed and live.** `pyJsonDumps()`'s compact-reserialization reconstruction is gone from `netalertx.flow.json` — HMAC now verifies directly against the raw received bytes, since NetAlertX no longer has the serialization mismatch. Deployed to the running Node-RED instance via the Admin API (`PUT /flow/tab_netalertx`, node-set diffed against live first to confirm only `fn_webhook_new_devices` changed), confirmed deployed (live `func` no longer contains the `pyJsonDumps` function definition), and verified both directions: the real captured payload still gets `200 OK`, and a tampered signature correctly gets `401 unauthorized`.
5. ✅ CARD-0132's pending-update dashboard state cleared (confirmed via retained MQTT topic: `pending: false, current: "26.8.5"`).

**Related:** CARD-0078 (the webhook HMAC workaround this update's fix let us simplify), CARD-0089 (pre-release confirmation of the same fix against `netalertx-dev-unsafe`, including reporting that confirmation back to upstream issue `netalertx/NetAlertX#1720`), CARD-0132 (the pending-update dashboard mechanism this closes out), CARD-0160 (the cloudflared sibling finding from the same maintenance-check run, already landed), CARD-0163 (the log-server flush bug this verification surfaced and fixed), `components/netalertx/docker-compose.yml`, `components/netalertx/netalertx.flow.json`, [PR #10](https://github.com/joscthomas/jctsh/pull/10).

---

### CARD-0160 · [enhancement] [infrastructure] Container image updates: cloudflared: 2026.8.2 available (running 2026.7.3) — auto-opened from photo-server — RESOLVED 2026-08-14 07:39 MST
**Status:** Done

**Auto-generated 2026-08-14 06:30 MST from photo-server's maintenance check (PR #11).** Raw finding: Container image updates: cloudflared: 2026.8.2 available (running 2026.7.3). Landed as a real kanban card via the old `resolve_and_merge()` path before the interviewed `land_pr_card.py` process (CARD-0162) existed — this note backfills the research and verification that process would normally require up front.

**Risk research (checked against cloudflared's actual GitHub releases, not just the raw finding):** `2026.7.3` → `2026.8.0` → `2026.8.1` → `2026.8.2`. Both `2026.8.0` and `2026.8.1` shipped with explicit "Do not use this version" warnings from Cloudflare — `2026.8.0` strips trailing slashes from HTTP-origin requests, causing redirect loops for anything needing canonical trailing-slash URLs (`cloudflare/cloudflared#1717`); `2026.8.1` normalizes request paths, breaking apps that need the raw encoded URL (`cloudflare/cloudflared#1719`). `2026.8.2` is the fix for both, with no further warnings. So this update lands past two known-bad releases straight onto the one that fixes them, not just a routine bump.

**Built and verified live, 2026-08-14 07:39 MST:** baseline confirmed (`hikes.jctnet.com` → HTTP 200 on `cloudflared:latest` pulled 2026-07-23, i.e. `2026.7.3`) before touching anything. `docker compose pull cloudflared && docker compose up -d cloudflared` on the M8 (`~/hike-izer-web-app`). Post-update: `cloudflared version 2026.8.2` confirmed via `docker exec`, tunnel reconnected clean (4/4 edge connections registered, connectivity pre-checks all PASS, `quic` protocol), and — specifically checking for the exact regression class `2026.8.2` fixes — `hikes.jctnet.com` returns `HTTP 200` both with and without a trailing slash, no redirect loop.

**Related:** CARD-0094 (original Cloudflare Tunnel setup), CARD-0162 (the interviewed PR-landing process this update predates), `components/hike-izer-web/docker-compose.yml`.

---

### CARD-0159 · [enhancement] [docker] Move Docker's data-root from the Pi's SD card to the existing USB drive — RESOLVED 2026-08-14 14:36 MST
**Status:** Done

Archived to `core/docker/CLAUDE.md` on 2026-08-22 (CARD-0193) — 8334B, over the 5000B size threshold.

---

### CARD-0158 · [enhancement] [maintenance] Automated post-reboot health check on the Device Status dashboard — RESOLVED 2026-08-17 12:14 MST
**Status:** Done

Archived to `core/maintenance/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6777B, over the 5000B size threshold.

---

### CARD-0157 · [enhancement] [hike-izer] Document the BirdNET Live pipeline — RESOLVED 2026-08-13 20:38 MST
**Status:** Done

**Raised 2026-08-13 20:38 MST**, Joseph asked how many BirdNET files came in for the 2026-08-13 hike (answer: 1, `birdnet_20260813T170639Z.zip`), then asked whether BirdNET is its own pipeline and where it's documented. Investigation found: fully integrated into hike-izer's own generation pass (not a standalone service — `birdnet.py` is imported directly into `generation.py`, called inline alongside narrative/place-context/photo-captions), and never had a single consolidated architecture doc — the real design was scattered across `birdnet.py`'s own module docstring, `staging.md`'s operational-runbook mentions, and eight separate kanban cards (CARD-0080, 0112, 0119, 0122, 0133, 0136, 0142, 0147), never brought together in one place.

**Done when:** a standing reference doc exists covering the real, current data flow end to end — phone share → webhook → staging (including the CARD-0136 race-condition handling) → parsing (`parse_detections()` for the table, `parse_occurrences()` for Route Map markers) → rendering → the cross-hike Wildlife Life List — verified against the actual source files, not just the kanban cards' own summaries.

**Built:** new file `components/hike-izer-orchestrator/birdnet-pipeline.md`, same shape as the Hiking Observations pipeline's own reference doc from earlier tonight (CARD-0156) — architecture diagram, numbered sections, function-level citations. Cross-referenced from `staging.md`'s own Related section.

**Related:** CARD-0080 (original BirdNET integration), CARD-0112 (staging mechanism), CARD-0119 (staging.md + SSHFS-Win mount), CARD-0122 (automatic phone→server path), CARD-0133 (Route Map occurrence markers), CARD-0136 (hike-end race condition), CARD-0147 (life-list "NEW species" badge), CARD-0156 (same-night companion doc for the Hiking Observations pipeline, same format).

---

### CARD-0156 · [bug] [hiking-monitor] "Log Observation" silently loses voice notes when offline — no retry/queue, unlike GPSLogger — RESOLVED 2026-08-13 19:34 MST
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7489B, over the 5000B size threshold.

---

### CARD-0155 · [enhancement] [photo-quality-review] "Super rule" bulk-delete for exact cross-account duplicates (identical filename/date/size, diff 0) — RESOLVED 2026-08-13 14:02 MST
**Status:** Done

**Raised 2026-08-12 17:54 MST**, Joseph's request mid-session while reviewing the existing auto-select duplicate logic.

**What "done" looks like:** For each year in the review UI, any duplicate group that is:
- exactly 2 members, one in Joseph's Immich library and one in Robin's,
- identical `originalFileName`,
- identical `fileCreatedAt`,
- identical file size,
- czkawka `difference: 0` for both members (exact perceptual-hash match — the same qualifying signal the existing cross-account tie-breaker in `maybeAutoSelectGroup()` already uses),
- and not already decided,

...gets pulled out of the normal per-group Duplicates list for that year (the individual photos are never rendered) and instead counted into a single "Super Rule" summary box: total count + one "Delete all in Robin's library" button.

**Album-check gate (Joseph's call, interviewed live):** before a candidate qualifies, still check each member's Immich album membership (same live `/api/albums/:assetId` call the normal auto-select flow already makes) — if Robin's copy is the one linked to an album and Joseph's isn't, exclude that pair from the Super Rule bucket entirely (falls back to normal per-group manual review, same as today) rather than deleting something that would silently lose an album link. Motion Photo video-integrity checks are explicitly **not** part of this gate — ignored for this rule, unlike normal auto-select.

**Delete action:** clicking "Delete all in Robin's library" deletes Robin's copy of every qualifying photo via the existing Immich delete pipeline (soft-trash, `force: false`, same as Confirm & Delete) and logs each to the existing deletion-log CSV/Sheet, same as every other deletion path in this app. Joseph's copy is always the one kept.

**Explicitly open for the build:** whether the button gets its own confirmation step — "don't show the photos" rules out a Preview-style itemized list, but some in-page confirmation (count + an explicit second click) is still expected before an irreversible-feeling bulk action.

**Built, deployed to the M8, and verified live.** Confirmation modal deliberately count-only (no itemized list, per "don't show the photos"), reusing the existing `/api/decide/duplicate` + `/api/confirm` pipeline rather than a new delete path.

**Found and fixed live during first real use:** the bulk "Delete all" button scoped `/api/confirm` to every qualifying groupKey for the year in one request — fine for the normal per-page Confirm & Delete flow (capped at ~100 groups by pagination) but not for this button, which can legitimately scope thousands. A real 2,529-group year 413'd (`PayloadTooLargeError`, Express's default 100kb JSON body limit) *before* the request reached the route handler, so nothing was deleted and nothing was corrupted — only the (harmless, idempotent) per-group decide calls had already landed. Raised `express.json()`'s limit to 5mb in `server.js`. Verified by replaying the exact same oversized payload against the fixed server (200 OK, all 2,529 items resolved correctly), then Joseph re-ran Confirm & Delete live: all 2,529 deleted from Robin's library, logged correctly, `decisions.json` left valid with the resolved groupKeys cleared.

**Related:** `components/photo-quality-review/public/review.js`'s existing `maybeAutoSelectGroup()` cross-account tie-breaker (2026-08-08) — this is a stricter, UI-different variant of the same underlying "identical size + diff 0, keep Joseph's copy" rule, scoped per-year and skipping individual review entirely instead of auto-checking a radio button.

---

### CARD-0154 · [idea] [hiking-monitor] DIY Li-ion overcharge-cutoff circuit (Hackster.io) — evaluated, not applicable
**Status:** Done

**Raised 2026-08-12 21:55 MST**, auto-opened from an email Joseph forwarded to `joscthomas+kbc@gmail.com` via CARD-0151's new email-idea watcher (the first real card this pipeline produced) — the article: [DIY 3.7V Lithium Battery Automatic Charger Circuit](https://www.hackster.io/electroniclovers/diy-3-7v-lithium-battery-automatic-charger-circuit-7dda92).

**Interviewed 2026-08-12 22:05 MST.** Joseph's real question: given several past conversations about battery charging for JCTsh's battery-powered builds, could this circuit replace or improve on what's already in use.

**Circuit fetched and evaluated** (WebFetch was blocked by Hackster.io's bot protection; retrieved via a reader-mode proxy instead): a discrete overcharge-**cutoff** add-on, not a full charger — LM358 op-amp as a voltage comparator, BD140 PNP transistor as a high-side switch, Zener reference + trim pot set the 4.2V threshold, hysteresis resistor to avoid chatter at the cutoff point. When the cell hits 4.2V, the comparator flips and the transistor hard-cuts charging current. That's the entire function — no CC/CV charge-current regulation, no boost/buck conversion, no solar input handling.

**Compared against real current hardware, not the stale doc first checked.** `components/hiking-monitor/power-system.md` (TP4056+boost, 5V boost output to ESP32 VIN) turned out to be out of date — Joseph corrected this: CARD-0070 (`Replace boost converter with LDO + gate peripheral power for lower standby draw`) already replaced that path. TP4056 stays exactly as-is for charging (regulation + solar input, unchanged); only the boost stage was removed, since boosting to 5V just to have the ESP32's own onboard regulator step it back down to 3.3V was wasteful — measured at 22.6mA quiescent draw, the dominant factor in a ~2-day standby life. Replaced with an LDO tapping the battery+ node directly, feeding the ESP32's 3V3 pin, plus a P-FET to gate peripheral power during sleep.

**Conclusion: not applicable, reference only.** CARD-0070's LDO swap is about the *discharge* side (delivering battery power to the ESP32 efficiently) — a different part of the system than what this article addresses (the *charge* side, terminating charging safely at 4.2V). TP4056 already handles that unchanged, with full CC/CV regulation and solar input support this discrete circuit doesn't have. The article's circuit wouldn't replace or improve on anything currently in use; it would just be a more primitive, worse-equipped version of what TP4056 already does. No action needed beyond this evaluation.

**Related:** CARD-0151 (the email-watcher that opened this card), CARD-0070 (the real current power-path design this was evaluated against), CARD-0026/0027 (the standby-current measurements CARD-0070 was built on), `components/hiking-monitor/power-system.md` (now known stale re: the boost stage -- worth a correction pass if anyone reads it expecting current behavior, not opened as a separate card here since it is a docs-accuracy nice-to-have, not blocking anything).

---

### CARD-0153 · [idea] [homeassistant] Move HA recorder off SQLite to MariaDB (or Postgres) if it ever becomes a real problem
**Status:** Backlog

**Raised 2026-08-12**, from Joseph reading an article about SQLite concurrency/write-lock issues under Home Assistant and asking whether JCTsh's HA instance should move off it.

**Why SQLite can be a problem, for context:** SQLite locks at the whole-database-file level — even in WAL mode (which HA enables by default), only one write transaction can be in flight at a time, so every other writer queues behind it. Under a heavy install (many entities, frequent automations), the recorder's write queue can back up behind that single-writer lock, worse on slow storage like a Pi's SD card. MariaDB (InnoDB) and PostgreSQL instead lock at the row level and use MVCC, so a write and a concurrent read (e.g. the frontend loading a history graph) don't block each other — real client-server databases built for concurrent multi-client load, unlike SQLite's embedded single-writer model.

**Explicitly not being pursued now.** Checked whether this JCTsh instance actually has the problem: the "could not validate shutdown cleanly" / "ended unfinished session" recorder warnings seen in `docker logs` during CARD-0150/0152's testing this session were almost certainly artifacts of repeated fast `docker restart` cycles (SQLite doesn't get time to flush before SIGTERM) rather than evidence of a real concurrency problem during normal operation. At JCTsh's current scale (modest entity count, not a heavy-automation install), SQLite's single-writer limitation isn't expected to bite. Joseph's call: leave it as SQLite, watch for real symptoms.

**Trigger conditions for actually pursuing this** (either one): recorder errors appearing during *normal* operation (not around a deliberate restart), or the History/Logbook UI becoming noticeably slow. Neither has been observed.

**If pursued, one option discussed:** run the database as its own container on the M8 (`photo-server`, `192.168.1.165`) rather than on the Pi, since HA's `recorder:` config accepts any reachable `db_url` — the M8 is already running Docker and is more capable than the Pi. Two real snags flagged, not yet resolved:
1. HA's official Docker image doesn't bundle a PostgreSQL/MariaDB Python driver by default — would need a custom image or an init step to install one.
2. Creates a new cross-device dependency that doesn't exist today — HA's recorder would go dark any time the M8 is unreachable, including the M8's own weekly scheduled reboot (Mon 4am) — worth checking that window against the Pi's own Monday 3am reboot stagger (see `jctsh-network.md`'s Scheduled Maintenance Windows table) if this is ever built, since the whole point of that stagger was avoiding a different false-down reading and a DB dependency adds a second reason to care about the timing.

**Done when (if ever picked up):** not yet defined — this card is parked as an idea, not scoped for Planning. Needs a real interview (which engine, where hosted, migration approach for existing history data, backup coverage) before any implementation starts.

**Related:** `jctsh-network.md` (M8 host details, maintenance-window table).

---

### CARD-0152 · [enhancement] [homeassistant] Expose Samsung Groom TV as its own HA device
**Status:** Done

Archived to `core/homeassistant/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6781B, over the 5000B size threshold.

---

### CARD-0151 · [idea] [tos] Remote creation of kanban cards from phone
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7701B, over the 5000B size threshold.

---

### CARD-0150 · [bug] [traveling] Samsung TV was on when we got home — investigate and fix
**Status:** Done

Archived to `components/traveling/CLAUDE.md` on 2026-08-22 (CARD-0193) — 18219B, over the 10000B size threshold.

---

### CARD-0149 · [enhancement] [photo-quality-review] Retain historical report.json snapshots for comparison
**Status:** Done

**Raised 2026-08-11**, after Joseph asked about a rescan's completion notification (38,258 duplicate groups) and wanted to know whether that was more than the previous scan turned up -- there was no way to tell, since `scan.js` overwrites `report.json` in place on every run, with no history kept.

**Scope: retention only, not comparison.** Joseph explicitly deferred the diff/comparison half ("38,258 duplicate groups (312 new since last scan)" in the notification) to build later -- this card is just making sure the data exists to compare against, not building the comparison itself.

**Design:** confirmed `groupKey()` (`server.js`) is already stable across rescans -- it's the sorted set of member asset IDs, not scan order or position, so two snapshots really can be diffed meaningfully once this exists. Before `scan.js` overwrites `report.json`, move the existing one into a new `data/report-history/` subdirectory under a filename timestamped from *that report's own* `generatedAt` field (not "now" -- "now" is when it's being retired, not when it was actually generated). `report.json` stays the one filename the app reads; nothing else in `server.js` changes. Deliberately no pruning/retention cap for now -- each snapshot is ~36MB and scans look ad-hoc/infrequent (this was the first rescan since the app's original build), so it would take dozens of scans before size is worth worrying about; simpler to add a cap later if it actually becomes a problem than to guess at a number now.

**Done when:** `scan.js` archives the previous `report.json` into `data/report-history/` (timestamped from its own `generatedAt`) before writing a new one, deployed to the M8, and verified with a real scan run that the history file lands correctly and `report.json`/the app itself are unaffected.

**Built 2026-08-11.** New `archivePreviousReport()` in `scan.js`, called right before the final `fs.writeFile(REPORT_PATH, ...)`: reads the existing `report.json`, pulls its `generatedAt` (falls back to current time if the file's malformed/older-format), then `fs.rename`s it into `data/report-history/report-<timestamp>.json` -- a same-filesystem move, not a copy, so no need to duplicate a ~36MB file on disk just to relocate it.

**Verified in isolation against real Node on the M8, not just "code looks right"** -- `scan.js` itself runs a full ~12.6-minute real scan with no way to unit-test just this one function in place (no `require.main` guard, importing it kicks off the whole scan), so the exact function body was run standalone against synthetic data in a scratch directory: (1) first-ever scan, no existing `report.json` -- no-op, no error; (2) normal case, valid `generatedAt` -- correctly archived as `report-2026-08-10T13-38-44.864Z.json`, original `report.json` confirmed gone; (3) malformed JSON -- falls back to a current-time stamp rather than crashing; (4) repeated archiving -- no filename collisions, all snapshots preserved distinctly. Deployed to `~/photo-quality-review/scan.js` on the M8 (syntax-checked with real `node -c` first), test scratch directory cleaned up afterward.

**Closed out 2026-08-11 on Joseph's go-ahead -- "leave it, it'll run naturally."** Not yet exercised end-to-end against a real scan run (`scan.js` isn't a persistent service, so no restart needed either -- it just takes effect on the next invocation); deliberately not forced today given the isolated test already covers the actual logic faithfully and a full run costs ~12.6 minutes. Real end-to-end proof arrives the next time a rescan runs naturally -- reopens under a fresh card if the history file doesn't land correctly then.

**Related:** CARD-0028 (the review app this extends), CARD-0148 (same component, prior round), `components/photo-quality-review/scan.js`.

---

### CARD-0148 · [bug] [photo-quality-review] Confirm & Delete and auto-select are both slow -- redundant/blocking work, not real API limits
**Status:** Done

Archived to `components/photo-quality-review/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7056B, over the 5000B size threshold.

---

### CARD-0147 · [idea] [hike-izer] Hike-izer iterative improvement for hike of Aug 10, 2026
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 29145B, over the 10000B size threshold.

---

### CARD-0145 · [idea] [outdoor-presence-detection] Audible Ring motion notification on Google Home — RESOLVED 2026-08-18 17:14 MST
**Status:** Done

Archived to `components/outdoor-presence-detection/CLAUDE.md` on 2026-08-22 (CARD-0193) — 22393B, over the 10000B size threshold.

---

### CARD-0146 · [idea] [outdoor-presence-detection] Show Ring doorbell live video on Gathering room TV
**Status:** Defer

Archived to `components/outdoor-presence-detection/CLAUDE.md` on 2026-08-22 (CARD-0193) — 23472B, over the 10000B size threshold.

---

### CARD-0144 · [bug] [hike-izer] Sun azimuth/direction systematically wrong (North/South swapped) since the feature was built
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5342B, over the 5000B size threshold.

---

### CARD-0143 · [enhancement] [hike-izer] Wikipedia link per species on the Wildlife Life List
**Status:** Done

**Raised 2026-08-05 07:57 MST:** Joseph wants each entry on the Wildlife Life List (CARD-0142) to link somewhere showing a photo and more information about that species.

**Approach recommended by Claude, confirmed by Joseph:** link to that species' English Wikipedia article, built directly from its `scientific_name` (spaces -> underscores, URL-encoded) -- e.g. `https://en.wikipedia.org/wiki/Progne_subis`. Rejected alternative: a custom page built from Joseph's own trail photos -- most life-list entries are audio-only BirdNET detections with no corresponding photo, so most species would end up with an empty page; Wikipedia guarantees a populated page (photo + description) for every entry today, and works uniformly across taxa (the list already includes non-birds like Coyote and American Bullfrog, ruling out a birds-only source like Cornell's All About Birds). No link-verification at build time (no HTTP call, no new failure mode in an otherwise pure-local render step) -- constructed optimistically, same "best-effort" philosophy already used elsewhere in this pipeline; Wikipedia's own redirects/search cover the rare mismatch.

**Scope:** `build_wildlife_index.py`'s per-species row gets a new "More Info" column linking to the constructed Wikipedia URL (`target="_blank" rel="noopener"`, since it leaves the site) -- distinct from the existing "First Heard" column, which stays an internal link to that species' first hike page.

**Done when:** every row on the live `https://hikes.jctnet.com/wildlife.html` has a working Wikipedia link for its species, confirmed against a sample of real entries (including at least one non-bird), deployed to the M8.

**Built, deployed, and verified live, 2026-08-05 08:03 MST.** New `_wikipedia_url()` helper in `build_wildlife_index.py`; new "More Info" column added to the species table (`target="_blank" rel="noopener"`). Verified before deploying: URL construction checked against both bird and non-bird scientific names, then spot-checked live against real Wikipedia (`Progne_subis`, `Canis_latrans`, `Lithobates_catesbeianus`, `Cyanocitta_cristata` all returned HTTP 200).

Deployed to the M8 (`scp` + `docker compose up -d --build orchestrator`), then rebuilt `wildlife.html` from the existing persisted life list (no data change needed, `wildlife_life_list.json` already had all 31 species from CARD-0142). Confirmed live: all 31 rows on `https://hikes.jctnet.com/wildlife.html` carry a unique, correctly-formed Wikipedia link, including the two non-bird entries (Coyote -> `Canis_latrans`, American Bullfrog -> `Lithobates_catesbeianus`).

**Revised, 2026-08-05 08:05 MST (Joseph's call):** dropped the separate "More Info" column -- the Wikipedia link now lives directly on the Common Name cell instead (`target="_blank" rel="noopener"` carried over). Re-deployed and re-verified live: `wildlife.html`'s header row is back to four columns (Common Name, Scientific Name, First Heard, Hikes), and e.g. "Coyote" links straight to `Canis_latrans` on Wikipedia.

**Related:** CARD-0142 (the Wildlife Life List this adds to), `components/hike-izer/build_wildlife_index.py`.

---

### CARD-0142 · [enhancement] [hike-izer] Cross-hike Wildlife Life List
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6345B, over the 5000B size threshold.

---

### CARD-0141 · [enhancement] [hike-izer] Push notification to Joseph's Pixel on hike-summary publish success/failure
**Status:** Done

**Raised 2026-08-05 07:30 MST:** today `hike-izer-orchestrator` only reports publish success/failure via an MQTT log line (`jctsh/hike-izer/publish/log`), which only surfaces on the log dashboard -- nothing pushes to Joseph's phone the way the existing heartbeat watchdog already does for component silence. Joseph wants the same HA-companion-app push-notification pattern extended to hike-summary generation itself.

**Scope, decided 2026-08-05 (Joseph's call):**
- Notify on **both** success and failure (not success-only) -- mirrors the existing MQTT System/Alert split in `generation.py`'s `run_and_log()` (step 1) and `run_step2_and_log()` (step 2).
- **Joseph's Pixel only** (`notify.mobile_app_pixel_10_pro_xl`) -- hike-izer is single-user, no reason to also notify Robin's phone the way some other JCTsh automations do.
- New `components/hike-izer-orchestrator/ha_notify.py`, same "best-effort, log-and-continue" convention as `mqtt_log.py` -- a push-notification failure must never break generation itself.
- Reuses the existing shared `HA_TOKEN` (`credentials.local.md` → "Home Assistant") -- no new token minted. New `HA_URL` env var pointed at the Pi's LAN IP (`http://192.168.1.117:8123`), not `raspberrypi.local` (mDNS unreliable cross-host) -- matches `mqtt_log.py`'s own hardcoded `BROKER = "192.168.1.117"`, already confirmed working live from this same M8 orchestrator container to reach the Pi, so no new cross-host reachability assumption is being introduced.
- Wired into both existing call sites in `generation.py` alongside (not replacing) the existing `mqtt_log.publish_log()` calls.

**Done when:** `ha_notify.send_push()` exists and is called from both success and failure branches of `run_and_log()` and `run_step2_and_log()`; `HA_TOKEN`/`HA_URL` are set in the M8's orchestrator `.env` and documented in `credentials.local.md`; the orchestrator is rebuilt/redeployed; and a real push notification is confirmed arriving on Joseph's Pixel (a direct `ha_notify.send_push()` test call is sufficient to verify the HA_URL/HA_TOKEN/notify-service mechanism itself -- the next real hike will exercise the generation-pipeline call sites for real, same as any other day-one code path).

**Built, deployed, and verified live, 2026-08-05 07:33 MST.** New `components/hike-izer-orchestrator/ha_notify.py` (`send_push(title, message)`, best-effort/log-and-continue, same convention as `mqtt_log.py`) calling `notify.mobile_app_pixel_10_pro_xl` via HA's REST API. Wired into both success and failure branches of `generation.py`'s `run_and_log()` (step 1) and `run_step2_and_log()` (step 2), alongside the existing `mqtt_log.publish_log()` calls. `Dockerfile` updated to copy the new module.

Deployed: `scp`'d `ha_notify.py`, `generation.py`, `Dockerfile` to `~/hike-izer-web-app/orchestrator/` on the M8 (via its Tailscale IP -- `.local` mDNS and the LAN IP were both unreachable from this Windows machine, same finding as CARD-0140), appended `HA_TOKEN` (reused shared token) and `HA_URL=http://192.168.1.117:8123` (the Pi's LAN IP -- same address `mqtt_log.py`'s own hardcoded `BROKER` already reaches successfully from this container) to the M8's shared `.env`, then `docker compose up -d --build orchestrator`. Documented both new vars in `credentials.local.md`.

Verified with a direct `ha_notify.send_push()` test call from inside the rebuilt container -- Joseph confirmed the push notification arrived on his Pixel 10 Pro XL. The generation-pipeline call sites themselves will get exercised for real on the next hike (same code path as the pre-existing MQTT logging, not separately re-tested end-to-end here).

**Related:** `core/node-red/watchdog.flow.json` / `core/node-red/watchdog-README.md` (the existing HA-companion-app push pattern this reuses), `components/hike-izer-orchestrator/generation.py` (`run_and_log`, `run_step2_and_log`), `components/hike-izer-orchestrator/mqtt_log.py` (the existing best-effort logging convention `ha_notify.py` mirrors), CARD-0140 (the same session's fix, same Tailscale-IP-for-deploy finding), CARD-0086 (automatic triggering, the pipeline this extends).

---

### CARD-0140 · [bug] [hike-izer] GPS accuracy noise falsely triggers "sustained non-walking pace" truncation, excluding real hike time from stats
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6885B, over the 5000B size threshold.

---

### CARD-0139 · [enhancement] [log-server] Exclude bench-test/dev components from the /status dashboard
**Status:** Done

**Raised 2026-08-03 17:46 MST**, superseding CARD-0138 (Deferred): `log_server.py`'s `/status` page has no concept of "not a real monitored asset" — anything publishing to the watched MQTT topics gets surfaced automatically, so `hiking-monitor-test` (a bench test rig, per Joseph) was showing up with equal billing to real deployed sensors. That's dashboard noise at best and misleading at worst (as CARD-0138's now-moot investigation showed).

**Scope, decided 2026-08-03 (Joseph's call):**
- New excluded-components set in `core/logging/log_server.py`, same pattern as the existing `_REMOTE_COMPONENTS` set — a small, explicit, hand-maintained list, not a naming-convention guess (a "-test" suffix rule would be fragile/surprising for any future component that isn't actually a test rig).
- `hiking-monitor-test` added as the first entry.
- Filtered out of `_build_status_html()`'s rendering entirely — not shown in either the Always-on or Mobile tables.

**Done when:** `hiking-monitor-test` no longer appears anywhere on `/status`, verified live; excluding it doesn't affect any other component's rendering.

**Built, deployed, and verified live, 2026-08-03 17:50 MST.** New `_EXCLUDED_COMPONENTS` set (mirrors `_REMOTE_COMPONENTS`'s pattern), filtered in `_build_status_html()` before splitting into home/remote tables. Verified locally first (`hiking-monitor-test` absent from rendered HTML, `hiking-monitor` still present and correct), then deployed and confirmed on the real dashboard — `hiking-monitor-test` no longer appears in either table, `hiking-monitor` unaffected.

**Related:** `core/logging/log_server.py` (`_REMOTE_COMPONENTS`, `_build_status_html()`), CARD-0138 (Deferred — the investigation this makes unnecessary), CARD-0137 (Done — introduced the Connection/Freshness columns this exclusion applies to).

---

### CARD-0138 · [bug] [hiking-monitor] hiking-monitor-test's retained /status never corrected to offline — compare its firmware against hiking-monitor.yaml
**Status:** Defer

**Raised 2026-08-03 17:40 MST**, found while working CARD-0137 (log-server status-display bug): `hiking-monitor`'s retained `jctsh/components/hiking-monitor/status` correctly reads `offline` (both units have been unpowered on the workbench for over a week, `hiking-monitor` even longer than `hiking-monitor-test`), but `hiking-monitor-test/status` was stuck retained at `online` — confirmed directly via `mosquitto_sub --retained-only`, not just a dashboard-display issue (CARD-0137 fixed the log server's handling; this is the broker's own retained value being factually wrong). Manually corrected with a one-off retained publish (`mosquitto_pub ... -t jctsh/components/hiking-monitor-test/status -m offline -r`) so the dashboard reflects reality now — confirmed live, `hiking-monitor-test` shows `Disconnected` as of this publish. That's a point-in-time fix only; it'll go stale again exactly the same way if the underlying device-side cause isn't fixed before the unit is ever reconnected and disconnected again.

**Partial investigation, not a full diagnosis:** `components/hiking-monitor/hiking-monitor.yaml`'s `mqtt:` block overrides `will_message` to target `jctsh/components/hiking-monitor/log` (a connection-event log message: `{"category":"MQTT","message":"MQTT disconnected"}`) rather than the `/status` topic at all — `on_connect` similarly publishes its own "MQTT connected"/"Hiking monitor online..." lines straight to `/log`, not through ESPHome's built-in availability mechanism. Despite that override, `hiking-monitor/status` still correctly resolves to `offline` in practice — the exact ESPHome-internals reason why (whether a default `/status` Will still gets registered underneath a custom `will_message`, or something else entirely) wasn't traced with certainty; flagged here rather than guessed at further.

**Open hypotheses to check, not yet confirmed:**
1. `hiking-monitor-test` might be running older/different firmware than the current `hiking-monitor.yaml` (no separate `hiking-monitor-test.yaml` exists in the repo — worth confirming what's actually flashed on that physical unit).
2. The stale `online` value could simply be old residue from before the current `will_message` setup existed on that unit, rather than evidence of an active ongoing config problem — i.e. it may correct itself cleanly the next time that unit actually reconnects, without needing a firmware change at all.
3. If it turns out to be a genuine config gap, compare against `hiking-monitor.yaml`'s real, current MQTT block field-by-field once the actual flashed firmware is known.

**Done when:** it's understood *why* one unit's `/status` self-corrected on disconnect and the other's didn't, and (if a real firmware/config difference is confirmed) `hiking-monitor-test` is reflashed or reconfigured to match, verified by actually power-cycling it and confirming `/status` flips to `offline` on its own, no manual retained-publish workaround needed.

**Deferred 2026-08-03 17:46 MST — wrong problem, not worth solving.** Joseph's own framing reset this: `hiking-monitor-test` is a bench test rig, not a deployed asset — it was only ever showing up on `/status` because `log_server.py` tracks anything that happens to publish to the watched MQTT topics, with no concept of "this isn't a real monitored component." Chasing why its firmware doesn't self-correct its LWT was solving the wrong layer — the actual fix is CARD-0139 (exclude test-bed components from the dashboard entirely), which makes this card's whole question moot. Not abandoned as in "forgot about it" — a deliberate call that this was never worth fixing in the first place.

**Related:** `components/hiking-monitor/hiking-monitor.yaml`, CARD-0137 (the log-server-side bug this is distinct from — that one's Done), CARD-0139 (the actual fix — exclusion, not firmware correction), `core/logging/log_server.py` (`_connection_state`, the new Connection column this bug is now visible through, accurately, for the first time).

---

### CARD-0137 · [bug] [logging] Retained-message redelivery on restart resets dashboard "last seen" ages, masking true staleness
**Status:** Done

Archived to `core/logging/CLAUDE.md` on 2026-08-22 (CARD-0193) — 11712B, over the 10000B size threshold.

---

### CARD-0136 · [bug] [hike-izer] BirdNET share can race ahead of the hike-end webhook — misattributes to the wrong hike
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 8233B, over the 5000B size threshold.

---

### CARD-0135 · [enhancement] [hike-izer] Iterative improvements from the 2026-08-03 Michigan hike incident
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 8092B, over the 5000B size threshold.

---

### CARD-0134 · [enhancement] [hike-izer] Wire the Route Map + Elevation & Speed chart into the automatic orchestrator pipeline
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7353B, over the 5000B size threshold.

---

### CARD-0133 · [idea] [hike-izer] Route Map event markers — photos, hike observations, bird sightings
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 12781B, over the 10000B size threshold.

---

### CARD-0132 · [enhancement] [logging] Extend CARD-0127's retained Pending-Update state to the generic container-image checker (HA, NetAlertX, Caddy, cloudflared)
**Status:** Done

Archived to `core/logging/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6381B, over the 5000B size threshold.

---

### CARD-0131 · [enhancement] [infrastructure] Immich update available: v3.1.0 (currently running v3.0.1) — auto-opened from photo-server
**Status:** Done

**Auto-generated 2026-07-31 23:01 UTC from photo-server's maintenance check.** Raw finding: Immich update available: v3.1.0 (currently running v3.0.1).

**Scoped 2026-08-01 — release notes reviewed before deciding, not just applied blindly.** Pulled the real release bodies via the GitHub API (not an AI-summarized fetch — an earlier WebFetch attempt got the release years wrong, 2024 instead of 2026, so it wasn't trusted) for v3.0.2, v3.0.3, and v3.1.0 (the three releases between the running version and the target). Only breaking change across all three: v3.1.0 drops iOS 14 support on the *mobile app* — irrelevant to the server. No database migration or schema change mentioned in any of the three. v3.0.2 added a fix wrapping migrations in a transaction (a safety improvement, not a new required step); v3.0.3 noted a narrow, self-healing Live Photos thumbnail caveat (fixed by the nightly job). Nothing resembling the CARD-0037/0042/0043-era bugs `operations.md` warns Immich has shipped before. Judged low-risk enough to do remotely, same reasoning as CARD-0095's M8 reboot (which was also done remotely without incident) — unlike the Pi's CARD-0129, an Immich container update never touches host networking/SSH/Tailscale, so remote access isn't at stake regardless of outcome.

**Built and verified live, 2026-08-01:** pre-checked all four containers healthy on v3.0.1 (`docker compose ps`, `/api/server/version`) before touching anything. `docker compose pull && docker compose up -d` in `~/immich-app` — only `immich-server` and `immich-machine-learning` recreated (Postgres/Valkey stay pinned by digest per this repo's own convention, untouched). Both back to `healthy` within ~1 minute. `/api/server/version` confirmed `3.1.0`. `immich-server` startup log clean — no errors/warnings, "Adding 3.1.0 to upgrade history," Nest application started successfully. Re-ran `immich-update-check.py` afterward: reports "Up to date: v3.1.0" and correctly re-published the retained pending-update state as `pending=False` — confirmed via CARD-0132's own mechanism, closing the loop between the two cards.

**Related:** CARD-0132 (the Pending Update mechanism this verifies), `components/photo-server/operations.md` (Immich update-check pattern, notify-only policy and its rationale), live dashboard entry at time of generation.

---

### CARD-0130 · [enhancement] [infrastructure] Container image updates: home-assistant: 2026.7.4 available (running 2026.5.1) — auto-opened from jctsh-core — RESOLVED 2026-08-13 21:50 MST
**Status:** Done

**Auto-generated 2026-07-31 22:52 UTC from jctsh-core's maintenance check.** Raw finding: Container image updates: home-assistant: 2026.7.4 available (running 2026.5.1). Needs a human/Claude interview pass to scope real acceptance criteria — this stub only captures that something was found, not what "done" looks like.

**Blocked — deferred until Joseph is physically home (2026-08-05 10:28 MST).** Same reasoning as CARD-0129/CARD-0096: HA is the household coordination hub Robin depends on directly, and an image update plus container restart is exactly the class of higher-stakes change that mitigation exists for — being on the home LAN removes Tailscale/remote-access as a dependency for the recovery path if anything goes wrong mid-update.

**Resolved 2026-08-13 evening, Joseph home on the LAN as planned.** By the
time this was actually picked up, the live dashboard's pending-update state
showed `2026.8.1` available, not the stale `2026.7.4` this card's auto-
generated title still named — HA had released another version since this
card was opened. **Checked release notes for all three intervening months
(2026.6, 2026.7, 2026.8) before touching anything**, specifically looking
for anything relevant to MQTT, automations.yaml schema, SmartThings, Docker,
or reverse proxies: renamed purpose-specific automation triggers/conditions
(none used in this repo's `automations.yaml`), ~20 removed integrations
(none used here), a device-merging behavior change (automatic, non-
destructive, and this repo's automations all use `entity_id` not `device_id`
so the one manual-review caveat didn't apply), and a default-port-8123
change (explicitly new-installs-only, confirmed via the official release
post — zero effect on this already-running instance). Nothing found that
blocked proceeding.

**Update applied:** `docker compose pull homeassistant` (one transient
registry hiccup mid-pull — `short read ... unexpected EOF` on one layer,
resolved by simply retrying; already-downloaded layers were cached, not
re-fetched) + `docker compose up -d homeassistant`.

**Verified live, real device:** `reboot-health-check.py` (CARD-0158, run
manually rather than duplicating its own polling-for-healthy logic) reported
`homeassistant: healthy` via Docker's real health check; confirmed running
version actually changed (`2026.8.1` via `/api/config`, not just "the
container restarted"); all 11 automation entities present and loaded
(including tonight's new Traveling Lights dashboard addition and the
CARD-0158 reminder); SmartThings integration correctly went through its own
normal post-restart reconnection (`not_loaded` → `loaded`, confirmed by
polling, not a failure — cloud integrations take a beat longer to
reconnect than the core API does). One pre-existing, unrelated log item
noticed and deliberately not chased: Bluetooth permission errors from HA's
bundled `habluetooth` integration, caused by the container never being
granted `NET_ADMIN`/`NET_RAW` capabilities — this JCTsh setup doesn't use
Bluetooth for anything, longstanding non-issue, not a regression from this
update.

**Related:** live dashboard entry at time of generation, CARD-0129 (the Pi-update sibling with the same "wait until home" block), CARD-0096 (original precedent for this reasoning), CARD-0158 (`reboot-health-check.py`, reused here to verify this update instead of writing a one-off check), CARD-0159 (the SD-card-wear idea this same session surfaced, opened but not built).

---

### CARD-0129 · [enhancement] [maintenance] Apply Pi's remaining Docker/kernel packages and reboot — RESOLVED 2026-08-13 20:51 MST
**Status:** Done

Archived to `core/maintenance/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6407B, over the 5000B size threshold.

---

### CARD-0128 · [enhancement] [tos] Maintenance findings auto-open a PR against kanban-board.md instead of just logging an Alert
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-08-22 (CARD-0193) — 17078B, over the 10000B size threshold.

---

### CARD-0127 · [enhancement] [logging] Reliable "Pending Update" indicator on Device Status page (MQTT retained state, not last-message-wins)
**Status:** Done

Archived to `core/logging/CLAUDE.md` on 2026-08-22 (CARD-0193) — 10597B, over the 10000B size threshold.

---

### CARD-0126 · [enhancement] [maintenance] Container-image update visibility for floating-tag services (NetAlertX, HA, Caddy, cloudflared)
**Status:** Done

Archived to `core/maintenance/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6109B, over the 5000B size threshold.

---

### CARD-0125 · [enhancement] [maintenance] Pi OS/firmware maintenance check — CARD-0095's Pi-side counterpart
**Status:** Done

Archived to `core/maintenance/CLAUDE.md` on 2026-08-22 (CARD-0193) — manually forced (--force).

---

### CARD-0124 · [enhancement] [photo-server] Detect host-side mount loss and auto-remount photo-library drives (guarded restart for primary)
**Status:** Done

Archived to `components/photo-server/CLAUDE.md` on 2026-08-22 (CARD-0193) — 10111B, over the 10000B size threshold.

---

### CARD-0110 · [idea] [hike-izer] Hiking stats — elevation graph, elevation summary, speed graph, other stats
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 22500B, over the 10000B size threshold.

---

### CARD-0103 · [idea] [personal] Migrate 3 legacy Google Sites pages (Cochie Springs hike, Mustang, Karli's Summer) to the M8 webserver — low priority
**Status:** Backlog

**Raised 2026-07-27**, during CARD-0093 (DNS cleanup). CARD-0093's original plan let `jctnet.com`'s Google Sites content go entirely (Joseph had called it unimportant), but revisiting surfaced that 3 specific pages are still wanted — dropping the `www` CNAME and `google-site-verification` TXT as part of CARD-0093 will break their reachability at `jctnet.com`/`www.jctnet.com`, even though the underlying Google Sites content itself isn't deleted by a DNS change (it stays live at its own `sites.google.com` URL, just unmapped from the custom domain).

**Scope:**
- Export the source content (text/photos) for all 3 pages from the live Google Sites pages — content only exists there right now, not backed up elsewhere.
- Rebuild them as static pages served from the M8 (alongside the existing `hike-izer-web` static content / Caddy setup, or a sibling route — exact placement TBD at build time).
- **Done when:** all 3 pages are publicly reachable at a real URL again (not just archived files on disk) — final URL/path scheme (e.g. under the existing Tailscale Funnel domain, a new subdomain, etc.) is an open decision for whoever picks this up.

**Open question, deferred to this card (raised 2026-07-27 while resolving CARD-0093's Search Console question):** both `jctnet.com` and `jctnet.net` currently show zero indexed pages in Search Console, so CARD-0093 doesn't bother re-verifying/maintaining Search Console for the now-dormant `jctnet.com`. But once these 3 pages are actually live again on the M8, whether they should be discoverable/indexed by Google (i.e. set up Search Console for wherever they end up living) is a separate decision — not resolved, not urgent, revisit when this card is picked up.

**Priority:** Backlog, low — not blocking CARD-0093, which proceeds with full jctnet.com teardown (including the Google Sites CNAME/TXT records and the root A/parking records) regardless of when this is picked up. Google Sites keeps serving the content at its native URL in the meantime, so there's no hard deadline to act before CARD-0093 executes.

**Related:** CARD-0093 (the DNS cleanup that prompted this), CARD-0088/CARD-0092 (existing M8 static-hosting precedent via Caddy).

---

### CARD-0096 · [enhancement] [infrastructure] Rename photo-server → m8 and raspberrypi → pi1, adopt a real host-naming convention — RESOLVED 2026-08-14 16:15 MST
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-08-22 (CARD-0193) — 40575B, over the 10000B size threshold.

---

### CARD-0095 · [enhancement] [photo-server] M8 OS/firmware maintenance backlog
**Status:** Done

Archived to `components/photo-server/CLAUDE.md` on 2026-08-22 (CARD-0193) — 11076B, over the 10000B size threshold.

---

### CARD-0085 · [idea] [hike-izer] Direction of travel (GPS bearing) + sun-position Route Map gadget
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 17297B, over the 10000B size threshold.

---

### CARD-0082 · [idea] [hike-izer] Visual track + elevation graphic, Gaia-GPS-style
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 15970B, over the 10000B size threshold.

---

### CARD-0058 · [idea] [presence] BLE room-detection for the Pixel 7 via Bermuda
**Status:** Backlog

**Notes:** Raised 2026-07-12. Goal: know which room the Pixel 7 is in (`sensor.pixel7_room` in HA) using BLE signal strength from ESPHome nodes already deployed around the house — no new hardware, no dedicated firmware.

**How it works:** each stationary ESPHome node runs an ESPHome `bluetooth_proxy:` component, listening for the phone's BLE advertisements and reporting RSSI to Home Assistant. The **Bermuda** integration (HACS) compares RSSI across all proxies and picks the strongest as the phone's room. Candidate proxy nodes (already deployed, just need `bluetooth_proxy:` added to their YAML): `front-porch-temp-sensor`, `garage-radar`, `salt-sensor`, and `remote-temp-sensor-01` once built (CARD-0044) — needs an ESP32 variant with BLE (the project's standard ESP32 DevKitC-32 qualifies; ESP8266 and ESP32-S2 nodes don't).

**Phone-side requirement:** Android randomizes BLE MAC addresses, so the bare Pixel 7 is untrackable without a stable beacon ID. Fix: enable the HA Companion app's **BLE Transmitter** feature on the phone, which broadcasts a consistent identifier for Bermuda to lock onto.

**Why Bermuda over ESPresense:** ESPresense is the other common option but requires flashing dedicated firmware onto each room's ESP32. Bermuda reuses the existing ESPHome nodes' own YAML via `bluetooth_proxy:`, so it's the lower-effort experiment given the fleet already deployed — try this first before considering ESPresense or new hardware.

**Realistic expectations:** room-level accuracy, not centimeter-level — expect occasional flapping between adjacent rooms from walls/body blocking/phone orientation, damped via Bermuda's per-room RSSI threshold tuning and smoothing/timeout settings. Not a one-shot config; needs an actual tuning pass per room.

**Background — UWB, and why it's not the near-term path here:** Ultra-wideband (UWB, e.g. Qorvo DW3000-based boards like Makerfabs/DWM3001C) does time-of-flight ranging accurate to ~10cm, spoof-resistant (same tech as car keyless-entry and Apple AirTag Precision Finding) — the "killer" version of this idea, enabling actual coordinates/zones (within 1m of the workbench, etc.), not just room buckets. Two blockers make it a separate, later idea rather than this card's scope: (1) hobbyist UWB firmware (Makerfabs/Arduino-style DW3000 boards) does simple two-way ranging between its own tags/anchors and doesn't speak the FiRa session protocol phones actually use, so off-the-shelf anchors and phones ignore each other even though the radios are compatible at the 802.15.4z level — would need FiRa-capable anchor firmware (Qorvo's DWM3001C stack) plus a custom Android app using the Jetpack `androidx.core.uwb` API to bridge to MQTT; (2) hardware gate — the Pixel 10 Pro XL has a UWB chip, but the **Pixel 7 does not** (only the 7 Pro does), so UWB is off the table for this specific phone regardless. If pursued later, UWB tags on things (keys, tool bag, robot vacuum, pets) sidesteps the phone-compatibility problem entirely, at the cost of needing every tracked thing to carry a powered tag.

---

### CARD-0055 · [bug] [garage-presence] Reconcile garage-radar/SmartThings light control — lights sometimes don't turn on
**Status:** Backlog

**Notes:** Joseph reports lights sometimes don't come on when entering the garage. Found during a components-vs-backlog reconciliation pass (2026-07-11): the repo fully documents the "presence off" SmartThings routine (closes door, turns off lights — `garage-presence/CLAUDE.md`) but has **no documentation anywhere of the "presence on" routine** presumably responsible for turning lights on when `switch.garage_presence_vswitch` turns on. `garage-radar/README.md` and `garage-presence/README.md` both reference "lights on" only as an outcome label on the vswitch, never as a documented ST routine with its own trigger/conditions — it exists only inside the SmartThings app, unaudited.

**Known chain (from `garage-radar/integration-notes.md`):** LD2412 radar → `binary_sensor.garage_radar_presence` (30s `delayed_off` filter) → triggers HA's "Garage Presence - Restart timer on activity" automation → starts `timer.garage_presence_timer` and turns on `switch.garage_presence_vswitch` → HA is the sole owner of the vswitch state (SmartThings routines must not set it directly, since ST→HA sync is documented unreliable for other sensors — `garage-presence/CLAUDE.md`) → SmartThings observes the vswitch turning on and is presumed to fire a "lights on" routine, which is undocumented and unverified.

**Suspected failure points (not yet confirmed):**
- HA→SmartThings state propagation lag/unreliability for the vswitch itself — existing docs only warn about the *reverse* direction (ST→HA sync unreliable for `binary_sensor.back_door_door` and the PIR motion sensors); nothing confirms the HA→ST direction this flow actually depends on is solid.
- Radar/PIR detection gaps delaying the first `binary_sensor.garage_radar_presence` → on transition (same class of issue already documented for `binary_sensor.garage_motion_motion`/`garage_cam_motion` sticking in Arizona heat).
- Whatever conditions the SmartThings "presence on" routine actually has configured today — unknown, never captured in the repo.

**Resolution path:** (1) audit the SmartThings app directly to capture and document the actual "presence on"/lights-on routine (trigger, conditions, actions), mirroring how the "presence off" routine is already documented in `garage-presence/CLAUDE.md`; (2) next time lights fail to come on, correlate HA logbook history for `switch.garage_presence_vswitch` against SmartThings app history to determine whether the vswitch turned on but ST didn't react, or the vswitch itself never turned on; (3) once root cause is identified, fix it (likely an ST routine condition or a sync-timing issue) and add the missing documentation so this chain is fully traceable end to end.

---

### CARD-0045 · [bug] [hiking-monitor] `wifi.ap:` fallback may prevent `reboot_timeout` from working
**Status:** Backlog

**Notes:** Found 2026-07-09 while researching a timeout decision for air-quality-monitor (which follows hiking-monitor's firmware pattern). `hiking-monitor.yaml`'s `wifi:` block has no explicit `reboot_timeout` override, so it relies on ESPHome's default (15 minutes before rebooting on failed WiFi connection). However, ESPHome's own issue tracker (esphome/issues#7222) documents that `reboot_timeout` does not apply when a `wifi.ap:` fallback block is configured — and hiking-monitor's config does have one (`ap: ssid: "hiking-monitor-fallback"`). So the 15-minute default may not actually be functioning as designed on the currently-deployed device.

**Priority: low (original assessment, superseded below).** Hiking-monitor's upload/home mode requires USB dock power to stay awake (same architecture as air-quality-monitor's charging-based home mode) — if the bug does prevent the reboot from firing, the device would get stuck awake trying to reconnect, but on USB power, not draining battery. No confirmed real-world failure — CARD-0008's actual field test (2026-06-17 camping trip) succeeded without issue. Worst case is a minor operational annoyance (stuck device needing a physical USB reflash to recover), not data loss or a safety risk.

**Reopened 2026-08-20 11:12 MST — priority assessment was wrong.** Surfaced while designing air-quality-monitor's own solar/dock-detect handling (CARD-0012): the "USB dock power, not draining battery" reasoning above assumed dock-detect only goes HIGH at the physical home dock. It doesn't — hiking-monitor's SUNYIMA solar panel wires into the same `IN+`/`IN−` pads as the dock (`power-system.md`, `perfboard-layout.md`'s "IN+ / IN− — solar/USB charging input; IN+ also tapped for dock detect"). So dock-detect can go HIGH mid-hike, on battery, exactly the scenario this card's priority call assumed couldn't happen. If the `reboot_timeout`/`wifi.ap:` bug does prevent recovery, a solar-triggered stuck reconnect *would* drain field battery, with no dock nearby to physically reflash. Raising to **medium** — still no confirmed real-world failure (CARD-0008 succeeded, but that test wasn't solar-triggered), but the "no real cost" justification for deprioritizing no longer holds.

**Resolution path — concrete design from the air-quality-monitor solar/timeout work (2026-08-20), not yet implemented on hiking-monitor:** rather than relying on `reboot_timeout` at all (sidestepping the `wifi.ap:` interaction bug entirely instead of deciding whether to remove the AP fallback), decouple field sensor logging from dock-detect state — keep the sensor-read/SPIFFS-log loop (and e-ink field display) running unconditionally whenever the hiking switch is ON, regardless of dock-detect. Let dock-detect HIGH trigger only a background WiFi connection attempt, bounded to a ~2-minute window, then `wifi.disable()` rather than retrying indefinitely, then re-enable and retry roughly every 15–20 minutes for as long as dock-detect stays HIGH (no cap on the number of these periodic cycles). Only switch to actual replay+live-publish once WiFi and MQTT both actually connect. This is a change to already-deployed, field-proven firmware — treat as its own scoped implementation pass, not a quick edit; matching air-quality-monitor's parallel implementation (`air-quality-monitor-claude-code-instructions.md` Step 8) once that's built and field-tested may be the lower-risk order of operations, since it validates the approach on hardware that hasn't shipped yet first.

---

### CARD-0038 · [idea] [garage-entry-hallway] Direction-of-travel sensor for hallway to garage entry door
**Status:** Backlog

**Notes:** Detect which direction a person is walking through the hallway leading to the garage entry door (coming in from the garage vs. heading out to it) — e.g. for automations like arming/disarming, lighting, or logging comings and goings. Discussed 2026-07-09: single HLK-LD2412 mmWave radar (already proven in `components/garage-radar/garage-radar.yaml`) recommended over a two-JSN-SR04T ultrasonic beam-gate — direction derived from the `moving_distance` trend (falling = approaching, rising = receding) via ESPHome's native `ld2412` component, rather than needing two sensors racing to trigger first. Two JSN-SR04T-V3.0 units already in inventory (Bag 30) but better reserved for a point-distance use case (e.g. tank level) rather than this one. No planning doc yet — not started.

---

### CARD-0031 · [bug] [p-w-firefly] Fix coachproxyos heartbeat's same publish/disconnect race condition
**Status:** Backlog

**Notes:** While debugging false "photo-server silent for 35 minutes" watchdog alerts (2026-07-06), found the root cause: `photo-server-heartbeat.py` published its `/log` and `/heartbeat` MQTT messages (QoS 1) back-to-back then called `client.disconnect()` immediately without running the network loop — occasionally the second publish's packet hadn't fully flushed before the socket closed, silently dropping the `/heartbeat` message while `/log` (published first) always got through. Fixed in photo-server's script via `client.loop_start()` + `wait_for_publish(timeout=5)` on both messages before `loop_stop()`/`disconnect()`. See `components/photo-server/heartbeat.md` for full root-cause writeup.

`components/p-w-firefly/jctsh-heartbeat.py` (coachproxyos, the RV Pi) uses the identical publish-then-disconnect pattern and almost certainly has the same latent bug — just less noticeable since a stray "coachproxyos silent" alert is easy to dismiss for a device that's expected to roam in and out of Tailscale range. Apply the same fix: `loop_start()` → publish both → `wait_for_publish()` on both → `loop_stop()` → `disconnect()`.

**Blocked:** RV Pi wasn't reachable (Tailscale down / not home) when this was found — deploy next time `coachproxyos` is reachable at `100.90.246.43` or `192.168.1.219`.

---

---

### CARD-0028 · [idea] [photo-server] Automated post-import quality scan (blur/duplicate detection)
**Status:** Done

Archived to `components/photo-server/CLAUDE.md` on 2026-08-22 (CARD-0193) — 28837B, over the 10000B size threshold.

---

### CARD-0025 · [enhancement] [hiking-monitor] Test retired LiPo battery — good or bad?
**Status:** Backlog

**Notes:** The hiking-monitor's original LiPo battery failed in the field (2026-07-03) with no advance warning and was replaced from spare stock (2 EEMB 603449 cells remain in Bag 7). Before permanently retiring/recycling the original cell, run this test to determine whether it's actually damaged or just tripped its built-in PCM protection circuit (which would reset after a proper recharge).

**Tier 1 — recharge-and-rest check:**
1. Place the cell in a fireproof/non-flammable spot (LiPo charging bag once purchased — see JCTsh-Build-Standards.md §2.14 — or a ceramic plate/metal tray in the meantime).
2. Connect to a TP4056 module and charge for 30-60 minutes. Watch for the charge-complete LED signal. **Stop immediately if any swelling, heat, or smell appears at any point** — that's a hard "bad," no further testing.
3. Disconnect from the charger, let it rest unloaded for 10-15 minutes, then measure resting voltage at the TP4056's board-level pads (not the tiny JST pins — those give unreliable/drifting readings).
4. Stable ~3.7-4.2V with no drift → passes Tier 1, proceed to Tier 2. Anything else (still unstable, near 0V, or any physical warning sign) → retire and recycle now, don't proceed further.

**Tier 2 — isolated load test (tester rig, not the real hiking-monitor):**
1. Use one of the 2 spare unused ESP32 DevKitC-32 boards (Bag 1) and one of the 4 spare TP4056 modules (Bag 8) — fully isolated from the working hiking-monitor, zero risk to it.
2. Wire minimally: battery JST → TP4056 battery input; TP4056 boost output (VOUT+/VOUT−) → spare ESP32's VIN/GND.
3. Power on in the fireproof spot and watch the spare ESP32's onboard LED: steady = pass, blinking/resetting (brownout under load) = fail.
4. For a more representative load matching the real device's WiFi-connect current spike (rather than just baseline boot current), optionally flash the spare ESP32 with `hiking-monitor.yaml` first — but change `esphome: name:` first (e.g. `hiking-monitor-test`) so it doesn't collide with the real device's hostname/MQTT identity while both exist.

**Caveat:** neither tier can rule out a slow-forming internal short with full certainty — that needs a proper battery analyzer/ESR meter, probably not worth owning for an ~$8 cell when 2 known-good spares are already on hand.

**Outcome:** Passes both tiers → may be returned to spare stock (log that it had this incident, in case it recurs). Fails either tier → retire and recycle per JCTsh-Build-Standards.md §2.14 (tape JST terminals, recycle at a battery drop-off — Home Depot/Lowe's/Batteries Plus — never household trash).

**Related:** CARD-0026 (measure hiking-monitor sleep-mode current draw) uses the same tester rig built for Tier 2 here — do them together in one bench session rather than building the rig twice.

---

### CARD-0024 · [enhancement] [p-w-firefly] Coachproxy remote health monitoring
**Status:** Backlog

**Notes:** The coachproxy heartbeat (every 30 min via Tailscale) confirms the RV Pi and Tailscale link are alive, but it can't distinguish between "Pi is powered off" vs "Tailscale is down" vs "RV is in a dead zone." A more useful health check would poll the Tailscale status directly from the home Pi: `tailscale ping 100.90.246.43` or checking the Tailscale admin API for last-seen timestamp. This gives richer diagnostic output (latency, path) without depending on the RV Pi to actively publish. Implement as a scheduled script on the home Pi that posts results to the log dashboard. Alternative: use Tailscale's built-in status API at `localhost:41112` on the home Pi to check peer state without any external requests.

---

### CARD-0005 · [enhancement] [p-w-firefly] Overlay filesystem
**Status:** Backlog

**Notes:** The Pi in the RV runs continuously, accumulating writes from logs, Tailscale state, and OS housekeeping — SD cards have a finite write cycle life and will eventually fail silently. An overlay filesystem makes the SD card effectively read-only during normal operation: all writes go to RAM, the card is only written during a deliberate shutdown sequence.

**Tailscale complication:** Tailscale stores its node identity and keys in `/var/lib/tailscale/`. If that directory is in the overlay (RAM-only), Tailscale loses its identity on every reboot and needs to re-authenticate. Fix: a persistent bind mount (small USB stick or dedicated partition) mapped to `/var/lib/tailscale/` so it survives reboots.

**eRVin image complication:** Raspbian Buster's modified `raspi-config` does not expose the overlay option in its UI — must be set up manually with `bilibop-lockfs` or equivalent.

**Interim protection:** SanDisk MAX Endurance card already installed.

---


### CARD-0019 · [idea] [vu-meter] Home theater VU meters
**Status:** Backlog

**Notes:** VU meter displays for home theater speakers — Left, Right, Center, Subwoofer (4 channels). Circuit to be breadboarded first to validate the analog front end before any JCTsh integration work begins.

**Hardware:**
- One ESP32 for all 4 channels — GPIO32/33/34/35 are all ADC1 pins and don't conflict with WiFi
- Display: WS2812B addressable RGB LED strips (color gradient green→yellow→red, software-configurable). Alternatives considered: discrete LEDs, OLED, LED matrix, NeoPixel rings
- Sub input: tap AV receiver RCA (line-level, ~1–2V peak) if powered sub — much simpler than speaker level. Speaker-level tap if passive sub

**Analog front-end circuit (per channel — speaker level):**
- High-side resistor divider ≥100kΩ to avoid loading the amp (speaker load is 4–8Ω; parallel impedance must stay negligible)
- Full-wave rectifier + peak detector capacitor — converts bipolar AC audio signal to positive DC level proportional to loudness
- 10kΩ series resistor before each ADC pin
- Schottky or TVS clamping diodes at ADC pin (to GND and 3.3V) — protect against transients and voltage excursions
- Keep resistor power dissipation in check: at 20V across 100kΩ = 4mW, well within ¼W rating

**Protection concerns:**
- Impedance loading: high-side ≥100kΩ ensures microamp draw; receiver can't tell it's there
- Voltage: speaker level can reach 20–30V peak — divider must scale to 0–3.3V; audio is bipolar so rectification is required before ADC
- Transients: amp spikes at power-on/off — clamping diodes + series resistor handle this
- Ground loops: ESP32 USB ground may differ from audio system ground → 60Hz hum injected into audio. Mitigation: isolated USB wall adapter, high-value sense resistors, or optical isolation (most robust)
- RF noise: ESP32 WiFi radiates RF — keep sense wiring physically separated from speaker cables; consider shielding

**JCTsh smart integration:**
- MQTT topics: `jctsh/components/vu-meter/data` (levels), `jctsh/components/vu-meter/log`, `jctsh/components/vu-meter/cmd` (remote control)
- Publish: per-channel audio level, `is_playing` boolean (derived from threshold + 1s hold)
- Node-RED: detect play/stop transitions → dim/restore theater lighting, turn off AV receiver after N min silence, notify if audio playing after midnight
- Remote display control via cmd topic: brightness, color scheme, sensitivity — adjustable from phone without touching hardware
- Optional: level logging to Google Sheets

**Division of labor:**
- Claude writes: ESPHome YAML (ADC reading, peak detection, WS2812B driving), MQTT schema, Node-RED flows, HA entities
- Physical validation: breadboard analog front end, measure actual output voltage range at typical listening volume, then tune firmware divider constants to match

**Resources:** No single tutorial covers this full stack. Pieces: Hackaday/Instructables (VU meter projects, WS2812B), Andreas Spiess YouTube (ESP32 audio/ADC), EEVblog forums or r/diyelectronics (circuit review before connecting to real equipment), ESPHome docs (firmware). Speaker-level input with proper protection is under-documented — this is an original design.

**Next step:** Breadboard and validate the analog front-end circuit. Measure voltage range at the ADC pin at low, medium, and high listening volumes. Report back before firmware work begins.

---


### CARD-0114 · [enhancement] [kanban-board] Status field per card, replacing physical column position — RESOLVED 2026-07-29 16:28 MST
**Status:** Done

**Raised 2026-07-29 07:59 MST**, after tonight's CARD-0106/0108/0104 move to Done briefly corrupted a large stretch of `kanban-board.md` — a script assumed a fixed line-offset for the insertion point instead of a real content marker, and a second recovery attempt made the same mistake in reverse (discarding everything before a search anchor). Both were caught and repaired, but the underlying problem is structural: a card's column is encoded as *physical location in a 2000+ line file*, so every status change requires relocating a whole prose block — exactly the operation that's error-prone for both a script and a human eyeballing large diffs.

**Confirmed via discussion:** Joseph never reads `kanban-board.md`'s raw file directly — he only ever views it through the live-parsing Pi page (CARD-0057, `/kanban`). So raw-file top-to-bottom column grouping has no reader-facing value; it only exists for whoever (or whatever) parses the file, and is the thing actually causing the risk.

**Decided approach:**
1. **Add `**Status:** <Column>` as a line directly under every card's header**, values being exactly the 5 existing column names (Backlog, Planning, Build, Done, Defer). This becomes the single source of truth for a card's state.
2. **Remove the `## ColumnName` section headers from `kanban-board.md` entirely** — once status lives on the card itself, physical position is redundant and risks disagreeing with the real status field. Cards become one flat, append-only list.
3. **Never physically relocate a card block again.** Moving a card between columns becomes a one-line edit to its `**Status:**` field. New cards get appended to the end of the file; existing cards are never moved once written.
4. **Drop the stale status word from cross-references.** Lines like "CARD-0104 (Backlog — the Gaia-embed precedent...)" go stale the moment the referenced card's status changes, and hunting these down by hand after every move is its own recurring chore (done 3 times tonight alone). Change the convention to omit the status word — just "CARD-0104 (the Gaia-embed precedent...)".
5. **Add a `<!-- next-card-id: CARD-XXXX -->` marker near the top of the file**, so creating a new card never requires grepping for the current highest ID.

**Required dependency, found while scoping this:** `core/logging/log_server.py`'s `_parse_kanban_board()` (the Pi's live `/kanban` page, CARD-0057) currently finds a card's column by locating physical `## ColumnName` section boundaries via `_KANBAN_COLUMN_RE` — removing those headers would break it outright (zero columns found). Must be updated in the same change to instead read each card's `**Status:**` line, and redeployed to the Pi, or the live board goes dark.

**Explicitly out of scope, considered and rejected:** splitting into one file per card (would also solve the relocation-risk problem, but breaks the single-file `kanban-board.md` convention referenced throughout the repo and CARD-0057's parser far more invasively, for no benefit beyond what the status-field change already achieves).

**Done when:** every existing card carries a `**Status:**` line matching its current column, the `## ColumnName` headers are gone, `log_server.py`'s parser is updated and redeployed to the Pi with the live `/kanban` page confirmed still grouping cards correctly, stale status words are stripped from cross-references, and the next-card-id marker is in place.

**Verified complete, 2026-07-29 16:28 MST:** all 5 "Done when" criteria checked directly against the live file and the Pi. No `## ColumnName` headers remain; all 118 cards carry a `**Status:**` line; `log_server.py`'s `_KANBAN_STATUS_RE` parser is deployed and the `jctsh-logging` service is active on the Pi (confirmed directly via SSH); the `next-card-id` marker is present and current. One real gap found on review: the "omit the status word from cross-references" convention (item 4) was applied retroactively to references stale at the time this card was raised, but wasn't actually followed going forward — CARD-0115 through CARD-0118's own `Related:` lines kept writing `(Done — ...)`. Fixed those four (Joseph's call: fix the four, leave the convention as symmetric guidance rather than adding enforcement).

**Related:** CARD-0057 (the Pi-hosted live parser this depends on and must update), CARD-0056 (original persistent-board effort, superseded by CARD-0057's dynamic fetch), CARD-0111 (the card-move work that surfaced this problem).

---

### CARD-0113 · [bug] [hike-izer] Session-scoped generation — one summary per detected hike, not per calendar day — RESOLVED 2026-07-29 14:46 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 9856B, over the 5000B size threshold.

---

### CARD-0112 · [enhancement] [hike-izer] Two-step generation — automatic data-only publish, then manually-triggered enrichment + narrative — RESOLVED 2026-07-29 14:38 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 9269B, over the 5000B size threshold.

---

### CARD-0080 · [idea] [hike-izer] Integrate bird species identified via Merlin Sound ID / BirdNET Live — RESOLVED 2026-07-29 17:18 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 12923B, over the 10000B size threshold.

---

### CARD-0071 · [idea] [personal] Emergency Access preparation
**Status:** Planning

**Notes:** Raised 2026-07-17, split out from CARD-0034's closure. Covers the "both Joseph and Robin unavailable at once" gap that the rest of `digital-identity-protection-checklist.md` doesn't — since both spouses already have the RoboForm master password memorized, each already has full independent access if something happens to the other, so Emergency Access only matters for the joint-unavailability case.

**Designated outside contact: a nephew** (decided 2026-07-22) — not one of the adult children as originally assumed; supersedes the "still need to pick which child" open question below. Same person covers both roles this card and CARD-0072 identified as needing a trusted third party outside the household: RoboForm Emergency Access designee, and holder of the outside-contact copy of the offline backup codes (moved here from CARD-0072, item #6 — see `digital-identity-protection-checklist.md`'s "Outside-Contact Copy Pattern" note).

**Scope:**
1. Evaluate and configure RoboForm Emergency Access for the nephew and the waiting period.
2. Set up Google Inactive Account Manager (Security settings) — the Google-side equivalent of #1, currently untouched.
3. Test both flows end-to-end once configured — trigger a request, confirm deny/delay notifications work, confirm the waiting period is actually tuned right. Don't just configure and assume it works.
4. Examine documentation needs — what would the nephew actually need beyond vault/account access (e.g., a will, power of attorney, other estate paperwork) to act on Joseph and Robin's behalf; currently out of scope of the checklist entirely and worth deciding whether it belongs there or elsewhere.
5. Meet personally with the nephew to walk through everything — what Emergency Access is, how/when it triggers, and what he's expected to do — rather than leaving it as a silent technical configuration nobody but Joseph knows exists.
6. **Outside-contact copy of backup codes** (moved from CARD-0072): give the nephew a third duplicate of the Google 2-Step Verification backup codes, held outside the household — covers a household-level event (fire, burglary, both spouses traveling and losing the same bag) that the home safe and the in-progress travel copy don't. Not yet implemented; natural to hand over at the same in-person meeting as item 5.

**Related:** `digital-identity-protection-checklist.md` (Phase 2, Password manager section, and Phase 2 "Offline hardcopy vault" / "Outside-Contact Copy Pattern" note) and `digital-identity.md` ("What NOT to Store in RoboForm" section) hold the reasoning this card executes against.

---

### CARD-0067 · [enhancement] [salt-sensor] Design and build a 3D-printed enclosure
**Status:** Planning

**Notes:** Raised 2026-07-13, following CARD-0049's perfboard build. Salt-sensor is installed near the water softener, where salt loading creates real splash risk — per `JCTsh-Build-Standards.md`'s enclosure decision rule ("installed outdoors or in a weather-exposed location → use a weatherproof project box"), this triggers an actual enclosure rather than the default open standoff mount. Board/components to house: ESP32 (SparkleIoT XH-32S), 3 status LEDs (Red/Yellow/Green, need visibility), JSN-SR04T connector (cable exit toward the tank), USB power port.

**Explicitly a skills-practice build, not just a functional requirement:** Joseph wants to drive the actual Tinkercad/OpenSCAD CAD work hands-on — same interactive Claude-Code-guides/Joseph-executes pattern as CARD-0009's hiking-monitor enclosure (`hiking-monitor-enclosure-instructions.md`), not something handed off or auto-generated.

**Candidate techniques already discussed:** LED light pipes (clear PETG, ~5mm diameter matching the standard LED assortment, interference-fit press into the wall — see earlier session discussion on hiking-monitor's card) for the three status LEDs' visibility through the enclosure wall.

**Sequencing:** CARD-0009 (hiking-monitor's enclosure) is still in progress and its Reflection step is expected to produce `JCTsh-3D-Enclosure-Instructions-Template.md`, generalizing the enclosure-build process the same way `JCTsh-Perfboard-Build-Template.md` just did for perfboard builds. If that template exists by the time this card starts, use it as the skeleton; if not, this card can proceed independently (using `hiking-monitor-enclosure-instructions.md` directly as a model) and become the second data point that template gets generalized from.

**Planning note (2026-07-13):** confirmed no generic enclosure planning template exists yet — the only precedent is `components/hiking-monitor/hiking-monitor-enclosure-plan.md`, a specific instance for that component, not a generalized template. CARD-0009's own Reflection step is where `JCTsh-3D-Enclosure-Instructions-Template.md` is meant to come from, and that hasn't happened yet. Planning for this card will use `hiking-monitor-enclosure-plan.md` directly as an ad hoc model in the meantime, same way salt-sensor's perfboard build used hiking-monitor's perfboard-layout.md before `JCTsh-Perfboard-Build-Template.md` existed.

**Done when:** enclosure designed and printed (PLA test print, then final material — ASA/PETG per Xerocraft availability, same pattern as CARD-0009), test-fit against the actual soldered perfboard (not just CAD dimensions), LEDs visible through the wall, JSN-SR04T cable and USB power port both accessible, adequate splash protection for the water-softener installation location, and physically mounted.

---

### CARD-0041 · [idea] [photo-server] Disk capacity growth analysis — wait for steady state
**Status:** Planning

**Notes:** Discussed 2026-07-09: want to estimate photo-library growth rate and project when the primary drive (Backup Plus 1TB, currently 615G/71% used) or backup drive (Momentus 640GB) will need replacing/upsizing. Deliberately not started yet — Joseph's call: current disk numbers are all noise from one-off events (CARD-0039 added 3,433 assets in one shot, CARD-0030 just freed 818GB by deleting zips, first post-cleanup backup run is still doing a full reconciliation rather than a normal weekly delta), not representative of organic day-to-day growth.

**Wait for:** the backup cron (CARD-0030/CARD-0040) running its normal weekly incremental cadence for a few cycles, so disk usage tracking reflects only real photo uploads from Joseph's and Robin's phones. At that point, weekly rsync deltas become a meaningful proxy for actual growth rate and a "months until full" estimate becomes trustworthy rather than a guess. Revisit this card once that's true — no fixed date, just "after the dust settles."

---

### CARD-0010 · [enhancement] [front-porch-temp-sensor] Use case definition
**Status:** Planning

**Notes:** Perfboard transfer complete. No enclosure planned. Sensor publishes temp, humidity, pressure, illuminance every 5 min. Perfboard layout: `components/front-porch-temp-sensor/perfboard-layout.md`.

Existing automations: Temp Alert (above threshold+2°F for 10 min) and Temp Dropping (below threshold−2°F for 10 min). Threshold: `input_number.front_porch_temp_threshold` (currently 90°F).

**Candidate use cases:**

**Pre-cooling alert** — temp dropping fast in the evening signals a good time to open windows. Node-RED computes rate of change; notify when drop exceeds X°F in Y minutes after sunset.

**Morning warm-up alert** — temp rising rapidly; close windows before the house heats up.

**Frost likelihood** — frost in the Arizona desert is rare but nuanced.

*Two mechanisms:*
- **Frozen dew** — dew (liquid) forms first when air temp drops to the dew point, then freezes if temp continues below 32°F. Requires dew point above 32°F. Rare in the desert.
- **Deposition frost** — water vapor deposits directly as ice, skipping the liquid phase entirely. This is the relevant type for the Arizona desert, where dew point is almost always below 32°F in winter. Governed by the **frost point** (a separate value from dew point, slightly higher than dew point at sub-freezing temperatures — meaning deposition frost can form at a higher temperature than liquid dew would).

*What matters for the sensor:*
- Dew point already computed by Node-RED from temp + humidity
- Frost point derivable from same inputs via a Node-RED function node
- Radiative cooling on clear nights (illuminance near zero = clear sky proxy) can drop surface temps 5–7°F below air temp — frost on surfaces can occur at 36–38°F air temp in still, clear conditions
- *Frost risk index*: notify when air temp < 38°F AND frost point < 32°F AND nighttime (illuminance ~0)

*Hiking monitor connection:*
Trail elevation makes frost far more likely than at home — the Santa Catalinas rise from ~2,500 ft (Tucson) to 9,000+ ft, roughly 3.5°F cooler per 1,000 ft of gain (~23°F colder at the summit). The hiking monitor measures actual temp and humidity at trail elevation, so it has everything needed to compute dew point and frost point in the field. Two integration points:
- **E-ink display** — add frost point or a frost risk indicator to the display when temp is below a threshold (currently shows temp, humidity, pressure trend, UV, battery)
- **Replay pipeline** — after a hike, the archived temp/humidity records correlated with the GPS track show where on the trail frost conditions existed, for future planning
- **Hike selection** — frost conditions at home (front porch sensor) combined with known elevation lapse rate could inform which trail to choose. If overnight low at 2,500 ft was 42°F, frost point was 28°F, and a trail peaks at 7,000 ft, surface frost is likely above ~5,500 ft. This becomes a reason to seek out a higher-elevation hike specifically to experience frost conditions in the desert.

**UV alert** — LTR-390 already reports UV index. Notify when UV index exceeds a threshold (e.g., 6+) for outdoor activity or plant protection planning.

**Plant protection reminder** — when frost risk is non-zero, notify to cover sensitive plants. Seasonal (December–February in Tucson).

---

### CARD-0044 · [idea] [remote-temp-sensor-01] Backyard solar/battery environmental sensor
**Status:** Planning

**Planning docs:** `components/remote-temp-sensor-01/JCTsh-remote-temp-sensor-01-phase1.md` (Phases 1–3), `components/remote-temp-sensor-01/remote-temp-sensor-01-claude-code-instructions.md` (Phase 4)
**Notes:** Started 2026-07-09 as a "replicant" of front-porch-temp-sensor, diverged into a separate component once the location moved from the sheltered porch to full-sun backyard. Phases 1–4 complete. Sensors: BME280 + BH1750 + LTR-390. Power: single swappable EVE 18650 + AEDIKO charger/holder + SUNYIMA solar panel — everything on hand, zero purchases. Firmware: 5-minute wake/publish/deep-sleep cycle (continuous WiFi not viable on this solar panel — ~10x power shortfall). Sensor power gated during sleep via an on-hand BC557B PNP transistor high-side switch (substitutes for a P-FET, same CARD-0027 pattern from hiking-monitor). AEDIKO module's own quiescent current is unmeasured — bench Step 6 of the instructions doc tests it, with a TPL5111 nanopower timer as a contingent (not assumed) mitigation if it's significant. SmartThings/Google Home exposure planned; no LEDs. Deliberately scoped smaller than weather-station (CARD-0011) — no wind/rain/lightning.

**Split into two phases of work, same pattern as hiking-monitor:** the Phase 4 instructions cover only the bench electronics/firmware build (breadboard → perfboard, sensors, power switch, deep-sleep cycle, battery/solar validation). Enclosure design (real weatherproof build with a sun-shielding vent reusing hiking-monitor's louvered vent-insert pattern, plus a separate battery-access hatch) and backyard installation are deliberately deferred to a follow-on planning pass once the electronics are proven — mirrors the CARD-0009 split on hiking-monitor. Second entry in the 3D-printing backlog behind hiking-monitor's enclosure. Ready for Phase 5 (execution) when directed.

**Enclosure shape guidance (2026-07-22):** looked at off-the-shelf parametric Stevenson-screen designs (e.g. [pauldaoust's on Thingiverse](https://www.thingiverse.com/thing:6437460)) as a possible base shell. **Don't use one of those as the whole enclosure** — they're sized for a bare thermometer on a shelf, not a full perfboard plus ESP32/battery/solar-charging circuit, and a fully-louvered shell offers little protection from wind-driven rain for electronics that aren't themselves weatherproof. Stick with the plan already in this card: a custom two-shell box sized to the actual perfboard footprint (same measurement-driven process as `hiking-monitor-enclosure-instructions.md` Steps 6–7), with hiking-monitor's `vent-insert.stl` louver geometry reused/rescaled as a small vent plug over just the BME280 opening — not the whole shell.

**LTR-390 sky exposure (2026-07-22):** needs the same treatment hiking-monitor used, for the same reason — a Stevenson-style louvered vent is designed to *block* direct radiation, which is exactly wrong for a sensor that needs to measure it. Two-part fix: (1) wire the LTR-390 to the perfboard via a STEMMA QT/Qwiic cable (Adafruit #4209) instead of soldering it directly, decoupling the sensor's physical position from wherever it lands on the perfboard; (2) flush-mount it at a plain cutout on the enclosure's top face — no acrylic/PETG window, since standard filament blocks UV and hiking-monitor deliberately avoided depending on a UV-transmissive material. Measure the desired top-face position the same way as hiking-monitor Step 6, once the perfboard is built.

**BH1750 sky exposure — not yet planned, same underlying problem.** BH1750 (ambient light) needs real sky exposure just like LTR-390 does, and nothing in this card's plan currently addresses it — likely needs the same STEMMA-cable-plus-flush-cutout treatment, but hasn't been decided. Resolve at the same Phase 4/CAD step as the LTR-390 mount, not as an afterthought.

---

### CARD-0020 · [enhancement] [hiking-monitor] Hike data visualization (Looker Studio)
**Status:** Backlog

**Rescoped 2026-08-02:** original scope (single-hike GPS route on a map + sensor readings over that hike's duration) is now superseded by Hike-izer's own evolution — CARD-0082 (interactive Route Map), CARD-0110 (hover-synced Elevation & Speed chart), and CARD-0133 (event markers) all landed since this card was written, and together already do a per-hike visualization better than a generic Looker Studio chart would (interactive, narrated, markered). Building that same thing again in Looker Studio would be a worse duplicate, not new value.

**What's still genuinely doable and meaningful — a cross-hike/aggregate view, which no single hike-izer page can ever provide (one page per hike, no memory across hikes):**
- Mileage/elevation-gain trends across the season (distance and gain per hike, plotted over time).
- A cumulative map of every route hiked, not just one at a time.
- Sensor/device health over the hiking-monitor's lifetime — battery voltage drift, UV sensor behavior — across many trips, the same "watch a metric over time" instinct this project already applies to container/dependency health elsewhere.

Still technically trivial as originally scoped: Google Sheets is a native Looker Studio data source (GPS Track + Environmental Data sheets), no new infrastructure. Review-after-the-fact use case, no real-time requirement.

---

### CARD-0012 · [idea] [air-quality-monitor] Air quality monitor
**Status:** Build

**Planning docs:** `components/air-quality-monitor/JCTsh-air-quality-monitor-phase1.md` (Phases 1–3), `components/air-quality-monitor/air-quality-monitor-claude-code-instructions.md` (Phase 4)  
**Notes:** Portable clip-mounted SEN55 air quality sensor (PM1.0/2.5/4.0/10, VOC, NOx) carried on hikes alongside the hiking monitor. Phases 1–4 complete (2026-07-09). Parts confirmed on hand: SEN55, Adafruit #5964 adapter, JST GH cable — `jctsh-parts-inventory.md`'s SparkFun SEN-23715 entry was mislabeled "SEN54," corrected to reflect it's the genuine SEN55. SEN55 sensor reading uses ESPHome's native `sen5x` platform (no custom component needed there); a custom component is still needed for onboard flash logging + WiFi replay, adapted from hiking-monitor's `hiking_logger.h`. SEN55 power-gated via an on-hand BC547B NPN transistor (same substitution pattern as remote-temp-sensor-01's BC557B) — bench-tested current draw, not just calculated, in Phase 4 Step 6. Follows hiking-monitor's firmware pattern (onboard flash logging, WiFi replay, field/home mode) exactly — that pattern is field-proven (CARD-0008), and the dependency is architectural only, **not** gated by hiking-monitor's still-open enclosure (CARD-0009). Phase 3 timeout policy matches hiking-monitor but explicitly avoids inheriting CARD-0045's `wifi.ap:`/`reboot_timeout` bug. Perfboard footprint measurement and LiPo polarity check moved from Phase 2 planning blockers to Phase 4 bench steps. Clip-case enclosure (with SEN55 intake/exhaust ports — orientation guidance currently flagged low-confidence, needs re-verification) deferred to a follow-on card, same split as hiking-monitor/remote-temp-sensor-01.

**Phase 5 execution started, 2026-08-19 12:03 MST.** Step 0 (Build Standards + hiking-monitor read) done. **Step 1 resolved:** dock-detect-only for mode-switching confirmed; a new inline power switch (Gebildet SS12D10, Bag 23, wired directly into the battery+ path, no GPIO) added for true transport/storage off, deliberately kept separate from mode-switching — directly informed by CARD-0181's hiking-monitor finding that a GPIO-tapped switch only sets a mode flag rather than cutting power, and pre-satisfies `JCTsh-Build-Standards.md` §1.7 before enclosure design even starts.

**Power architecture also changed, 2026-08-19:** originally-planned TP4056+boost combined module → direct LiPo-to-LDO (MCP1700, Bag 32, on hand — same part validated on the CARD-0026/CARD-0070 rig) per `JCTsh-Build-Standards.md` §2.14 point 7. TP4056's charging half is unchanged; only its boost stage is unused. The Adafruit #5964 adapter's own onboard 5V boost for the SEN55 is unaffected either way (self-contained, was never fed by the system-level boost module). P-FET peripheral gating (§2.14 point 8) considered and declined — still unvalidated/candidate-only, and designed for 3.3V-rail I2C peripherals, not SEN55's 5V domain; SEN55's existing BC547B low-side gate is the electrically correct approach and there's no other sensor on this build to gate.

**Runtime recalculated for the LDO swap:** Phase 1's own ~58-68h estimate never included the boost module's own quiescent draw (same blind spot CARD-0026 found on hiking-monitor, ~22.6mA measured there) — with the boost module as originally planned, real-world runtime likely would have been closer to **~30 hours**. With the LDO (≈1.6µA quiescent, negligible), runtime should land close to the original consumer-side budget alone: 1100mAh ÷ ~13-15mA ≈ **~73-85 hours (roughly 3-3.5 days)** — comfortably beyond any realistic hike, and a concrete benefit of the LDO decision beyond just matching the standing standard. Both figures remain estimates pending Step 6's actual bench-measured current draw.

All decisions written into `air-quality-monitor-claude-code-instructions.md` (bumped to v1.1) and cross-noted in the Phase 1 doc.

**Step 2 done, 2026-08-19 12:05 MST.** `air-quality-monitor` Mosquitto account created on the Pi and verified live (`mosquitto_pub` auth test). `components/air-quality-monitor/secrets.yaml.template` and `secrets.yaml` both created — `wifi_ssid`/`wifi_password` reused (JCTnet1, shared across all ESP32 components), `ap_password`/`ota_password` freshly generated and unique to this component (deliberately **not** reusing `wifi_password` for `ap_password` the way hiking-monitor's original secrets.yaml did — that was flagged as a real gap during CARD-0076). `mqtt_broker: pi1.local` (LAN-only, no DuckDNS/TLS cert needed — this device's home mode only ever happens docked at home, unlike hiking-monitor's cellular-hotspot scenario). Account added to `CLAUDE.md`'s credentials table (also caught and fixed a miss: `ring-mqtt`'s account from CARD-0146 was never added there either).

**Step 3 done, 2026-08-19 12:10 MST.** `components/air-quality-monitor/wiring.md` and `ESP32-project-pins.md` written, covering: SEN55/adapter I2C wiring, the BC547B SEN55 power-gate circuit (NPN low-side switch, 1kΩ base resistor + a 10kΩ base pull-down added as a direct lesson from CARD-0070's BS250 floating-gate finding — the active-high/NPN equivalent precaution), the dock-detect divider, the battery voltage divider, the new MCP1700 LDO wiring (VIN parallel off battery+, VOUT straight to ESP32 3V3, per the CARD-0026/CARD-0070 rig pattern), and the new inline power switch (wired directly in the battery+ path ahead of both the TP4056 and the LDO tap, no GPIO). **Real error caught and corrected while writing this:** the instructions doc's Hardware Context table said the battery divider was 68kΩ/68kΩ "same as hiking-monitor" — hiking-monitor's actual `wiring.md` uses 100kΩ/100kΩ for that divider; 68kΩ/100kΩ is the *separate* dock-detect divider. Corrected in both docs rather than propagating the error.

**Step 3 done (breadboard), 2026-08-20 11:12 MST.** Joseph reports breadboard wiring complete, USB-powered per `wiring.md`. Perfboard footprint measurement **moved out of Step 3 to Step 9** (also fixed in `wiring.md`, the Phase 1 doc's BOM, and the instructions doc) — measuring it this early was premature, before there's a real layout to size against. Working assumption for Step 9: the same 5×7cm Chanzon FR4 board hiking-monitor uses will probably work here too.

**Same session:** solar/field-USB charging found to share the dock-detect signal with the home dock (same as hiking-monitor's own wiring), so the Phase 1 Timeout/timer decision was superseded — field logging now runs unconditionally, dock-detect only triggers a bounded-window/backoff WiFi attempt against both `JCTnet1` and a newly-added Pixel hotspot network, `mqtt_broker` corrected from `pi1.local` to `jctsh.duckdns.org`+TLS (matching hiking-monitor's actual CARD-0003 config, which this component's own template had drifted from). Full writeup in the Phase 1 doc's JCTsh Integration table and the instructions doc's Timeout policy section. Cross-posted the same latent gap to CARD-0045 (hiking-monitor also shares solar with dock-detect, raised that card's priority).

**Step 4 (Claude Code half) done, 2026-08-20.** `air-quality-monitor.yaml` written — SEN55 base validation scope only (continuous power via GPIO27, PM/VOC/NOx logged every 30s), not the full field/home duty-cycle firmware (still Step 8). Includes the corrected MQTT/TLS config and the new hotspot network. **Handed to Joseph:** flash via USB from `C:\esphome\air-quality-monitor\` and confirm plausible PM/VOC/NOx values on the log dashboard.

**Enclosure planning started, 2026-08-20 (same session).** `air-quality-monitor-enclosure-plan.md` created, following the same process/structure as `hiking-monitor-enclosure-plan.md`. Biggest structural difference from hiking-monitor: SEN55 mounts externally to the enclosure (3M tape, own sealed housing handles airflow) rather than needing internal venting, which removes the dominant footprint constraint and the low-confidence intake/exhaust design question entirely — see the Phase 1 doc's Carry and Enclosure section. Plan doc captures what's decided plus a full open-questions list (mount face/cable routing, RGB LED window vs. flush-mount, final print material PETG vs. hiking-monitor's ASA upgrade, carabiner, solar JST hole, etc.). **CAD work explicitly does not start until the bench phase (Steps 0-9) is confirmed complete** — this is planning only, not yet active build.

**Step 4 closed 2026-08-21 10:33 MST — a real, multi-hour hardware diagnostic session, not a clean pass.** Initial flash caught and fixed a real firmware bug first: `on_boot`'s `component.update: sen55` referenced an ID that didn't exist — the `sen5x:` platform block had no top-level `id:`, only its sub-sensors did (`sen55_pm1` etc.). Added `id: sen55` to the platform block; fixed and redeployed cleanly.

**Real hardware fault found and diagnostically chased at length: the SEN55 power-gate transistor circuit.** With the BC547B in-circuit, the SEN55 never produced a single valid reading across 20+ minutes and multiple boot cycles — I2C bus needed "recovery" at boot, `Found i2c device at 0x69` never appeared in any scan, and the adapter's power-indicator LED ran visibly dim. Systematic elimination, each step confirmed independently, all passing individually: base resistor value (0.98kΩ, on spec), base voltage (0.722V, healthy Vbe), VIN (3.2V, healthy), transistor swapped for a fresh unit from the Music Response bin stock (identical symptom persisted), the whole gate circuit relocated to an unused breadboard region (identical symptom persisted, ruling out that specific breadboard area), Collector-to-adapter-GND continuity confirmed solid, Emitter-to-common-GND continuity confirmed solid, no stray/duplicate wires found on physical inspection, bypass jumper confirmed fully removed. A direct current measurement in series read only **8.4mA** — far *below* the ~70mA design assumption, ruling out an over-current explanation for the ~2V sitting on the switched node. VDD/GND measured directly at the SEN55's own connector (not the adapter) both came back individually healthy (5V / 0V relative to true ground, a full clean differential) — yet the sensor still didn't respond, meaning even conclusively-correct power at the sensor's own pins wasn't sufficient on its own.

**Real root cause: an intermittent, not permanent, bad connection — found via the adapter's own power LED, not the multimeter.** The LED visibly brightened during the in-series current test (which had spliced the meter directly into the Collector-to-adapter-GND wire, replacing it) — pointing at that specific wire. Swapping it for a fresh jumper brightened the LED, but on the next fresh boot the LED was briefly bright, then went immediately dim, then brightened again and held — a pattern (wiggle: no effect; full removal and reinsertion: fixes it) consistent with a marginal/oxidized breadboard contact point, not a broken wire or bad transistor. Even so, a subsequent ~8-minute run with the LED reportedly stable still produced zero valid readings — the full picture isn't necessarily explained by "one bad breadboard hole" alone; flagged as a real open question, not fully resolved.

**Real design question surfaced, not just a component fault: low-side vs. high-side switching for this specific load.** `wiring.md`'s existing justification for the NPN low-side (GND-return) switch — that the SEN55/adapter sit on "their own 5V-boosted rail" — doesn't hold up under scrutiny: the natural high-side switching point (the adapter's `VIN` pin) is fed directly from the shared 3.3V rail, the same domain `JCTsh-Build-Standards.md` §2.14 point 8's P-FET pattern was designed for and which was dismissed as "not applicable here." Low-side switching has a structural weakness directly relevant to tonight's whole ordeal: any marginal connection in the GND-return path doesn't just reduce voltage to the load, it shifts the load's *entire ground reference* away from the controller's — exactly the kind of failure that silently breaks I2C while individual voltage checks still look fine. High-side switching would leave GND permanently, solidly tied to common ground, so a marginal connection there would only ever show up as insufficient voltage — a more benign, easier-to-diagnose failure mode. **Neither pattern is actually validated end-to-end in this project** — §2.14 point 8's P-FET candidate was never finished (CARD-0070, deferred), and tonight is the low-side pattern's first real test, which it has not yet passed cleanly. Worth treating as a genuine open redesign question for Step 6, not just "find the bad wire and move on."

**Current physical state:** bypass jumper (adapter `GND` directly to common ground rail) back in place — this is the same configuration proven at the very start of tonight's session, and confirmed again just now: real, plausible SEN55 data (PM1.0/2.5/4.0/10 ~1.0–1.5 µg/m³, VOC climbing 17→33 over successive readings — normal warm-up curve, NOx settled at 1), first valid reading only 12 seconds after boot. **Step 4's own done-when is met on this configuration** — all SEN55 fields reporting plausible values, confirmed live. The BC547B gate circuit is set aside, not removed, still wired on the breadboard but out of the active power path. Step 6 (bench-testing the power gate) now inherits tonight's findings directly — decide there whether to keep debugging the low-side approach or build the high-side alternative before calling the gate circuit itself validated.

**Step 5 done, 2026-08-21 10:50 MST — same session.** PM2.5 → RGB threshold logic implemented as an `on_value` trigger directly on the `pm_2_5` sensor (fires exactly when a new reading arrives, no separate polling), driving three `output: platform: gpio` components (GPIO18/19/23) with simple on/off combinations — green (<12 µg/m³), yellow (12-35, red+green combined), red (>35). No PWM/dimming needed for three solid states. Deployed cleanly (config validated via `esphome config` first, matching this session's established practice after Step 4's firmware bug), clean boot, no errors. **Verified live:** PM2.5 at 2.0 µg/m³, green LED confirmed on by Joseph directly at the device — matches the threshold, sensor logic and LED logic both intact together.

**Real, useful research surfaced while investigating the power-gate redesign, worth folding into Step 8's design:** Sensirion's own "Reduced Power Operation for SEN5x" document recommends duty-cycling between **Measurement mode** (~63mA, full PM+RHT+VOC+NOx) and **RHT/Gas-Only mode** (laser+fan off, ~lower draw, humidity/temp/VOC/NOx only, no PM) as the primary power-saving mechanism — not physically power-cycling the sensor on/off. Alternating these two modes can cut power ~7-9x with minor accuracy tradeoffs, and is what Sensirion frames as making battery operation viable at all. Two real discrepancies against this project's existing assumptions, worth reconciling before Step 8 locks in duty-cycle timing: (1) Sensirion recommends a **30-60 second warm-up** after leaving a low-power state for good accuracy (8s is documented as an absolute floor, not recommended) — longer than Phase 1's assumed ~10s active window per 2-minute cycle; (2) if genuinely power-cycling the sensor fully off/on (not just switching to RHT/Gas-Only mode), Sensirion recommends **triggering a cleaning cycle at least weekly** if power-cycling roughly daily — a fan self-cleaning maintenance requirement, not just a power concern. Worth deciding at Step 8 whether to duty-cycle via mode-switching (software, sidesteps the gate-circuit reliability question entirely for routine cycling) rather than physical power gating for anything other than true full-off between hikes.

**Step 5 fully closed, 2026-08-21 11:53 MST.** Yellow and red threshold colors verified live (green already confirmed above) via a boot-time color-hold sequence (solid Yellow 3s, solid Red 3s) using substituted PM2.5 output states rather than a real particulate source — added as a **permanent** part of the boot sequence per Joseph's preference, not a one-off test removed afterward. Also added this session: boot self-test LED sequence (two quick blinks each of Blue/Red/Yellow/Green), an unbounded green-blink "waiting for first valid reading" loop with no timeout (deliberately, per the Step 4 lesson that a "looks connected" fault can silently produce zero readings for a long time), a solid-green "all is well" confirmation, and blink-mode operational LEDs (brief ~1s flash per reading instead of continuous-on, for battery savings). Full behavior documented in `README.md`'s new LED Status Guide section.

**Step 6 decision: drop the SEN55 power-gate transistor entirely, 2026-08-21 12:13 MST.** Revisiting *why* a gate was wanted in the first place (rather than re-litigating low-side vs. high-side, per tonight's open question above) resolved it a different way — the two real use cases are both already covered without a dedicated gate: (1) routine duty-cycling during a hike is better served by Sensirion's own recommended I2C mode-switching (Measurement ↔ RHT/Gas-Only, from the research two paragraphs up) than by physically cutting power, and (2) true full-off for storage/transport is already handled by the existing inline power switch (Step 1, cuts the whole battery). With no remaining use case, the gate is dropped — SEN55's `GND` return is now permanently wired direct to common ground (the Step 4 "bypass jumper" becomes the actual design), GPIO27 goes unused, and the low-side/high-side reliability question (along with the exact I2C-breaking failure mode that caused Step 4's multi-hour diagnostic session) is moot rather than solved. Duty-cycle timing moves to Step 8 as an I2C mode-switching firmware task. Updated: `air-quality-monitor.yaml` (removed the GPIO27 switch component), `air-quality-monitor-claude-code-instructions.md` (Hardware Context, GPIO table, Step 6, Step 8), `wiring.md` (GND wiring, schematic, perfboard component list, historical BC547B circuit reference collapsed into a `<details>` block), `README.md`, `ESP32-project-pins.md`, `JCTsh-air-quality-monitor-phase1.md` (BOM row marked superseded). BC547B/BS250 stock remains on hand, unused by this build. **Design decision only at this point — the physical breadboard still had the BC547B and its resistors in place, so Step 6 was not actually closed yet** (Joseph caught this; corrected below).

**Step 6 physically closed, 2026-08-21 12:50 MST.** Joseph removed the BC547B transistor, its 1kΩ base resistor, and its 10kΩ base pull-down resistor from the breadboard entirely (not set aside, as had happened once before during Step 4). Confirmed: SEN55 `GND` is a solid, deliberately-reseated direct connection to common ground (not just the leftover diagnostic-session jumper left in whatever state it was in), and GPIO27 has nothing connected to it. Step 6 is now genuinely closed, hardware matching the design docs. **Step 7 (LiPo polarity check and power validation) next** — now also scoped to include raw dock-detect and battery-divider verification (added to the instructions doc same session), since neither had a dedicated test point before.

---

### CARD-0013 · [idea] [van-sensors] Van sensors (indoor + outdoor)
**Status:** Planning

**Planning doc:** `components/van-sensors/JCTsh-van-sensor-phase1.md`  
**Notes:** Two ESP32 ESPHome nodes for the Pleasure-Way ProMaster 3500 van. Outdoor: BME280 + LTR-390 UV + SEN55 air quality, LiPo powered. Indoor: BME280 + SCD40 CO2 + MQ-6 propane, 12V coach power. Both log to onboard flash during travel, sync to home MQTT on WiFi reconnect (home or Pixel hotspot). DS3231 RTC for accurate timestamps during extended trips. GPS correlation via GPSLogger on Pixel. Phase 1 complete — ready for Phase 2 (hardware selection, inventory scan, open questions resolved).

---

### CARD-0053 · [idea] [photo-tv-display] Ambient photo slideshow + phone controller
**Status:** Build

**Build started 2026-08-03.** Pre-build checklist resolved: `media_player.groom_tv` confirmed (via HA API) as the gathering room Google TV; existing shared `HA_TOKEN` reused rather than minting a new one; Node.js v24.18.0 already installed on the M8; Immich API keys for both accounts already exist. `apps-script.gs` will be written as part of this build and handed to Joseph to deploy to a new Sheet afterward (URL fed back into `.env`). Live device testing (TV cast, both phones, HA idle-state observation) requires Joseph physically at the devices — flagged as a handoff step once the code is built and deployed.

**Code built and verified live, 2026-08-03.** Full Node.js server (`server.js`, `routes/{immich,homeassistant,deletion-log}.js`, `public/{tv,controller}.{html,js}`, `apps-script.gs`) written, deployed to the M8 (`~/photo-tv-display/`), `npm install`ed, and exercised end-to-end against the real Immich (v3.1.0) and HA instances — server boot, `/tv`/`/controller`/image proxy, album/people listing, WebSocket state sync, `nav`/`setFilter`/`favorite` round-trips (favorite toggled and restored on a real asset) all confirmed working with no errors. Found and fixed two real API-shape gaps the planning docs got wrong at plan time: Immich's `country` field returns `"United States of America"` (not `"United States"`/`"USA"`) so `formatLocation()` needed a `startsWith` match; Immich's asset-filter DTOs have no `ownerId` field, confirming (not just assuming) that the multi-account merge design is required. Full deviation list in `components/photo-tv-display/README.md`.

**systemd + Apps Script both done, 2026-08-03 19:01 MST.** Joseph ran the systemd install himself (`enabled`, `active (running)`, survives reboot — the harness's auto-mode classifier blocks Claude Code from piping the M8's `sudo` password non-interactively, by design, so this step needed an interactive session; the staged unit file at `/tmp/photo-tv-display.service` had to be rewritten once since the first staging attempt was itself part of a blocked compound command and never actually ran). Apps Script deployed to a new dedicated Sheet, `DELETION_LOG_SHEET_APPS_SCRIPT_URL` live in `.env` on the M8, `?action=version` confirmed reachable. Both `/tv` and `/controller` verified responding through the systemd-managed process.

**Remaining before this card closes:** live Step 11 validation (TV cast, both phones, HA idle-state observation — `IDLE_STATES` in `routes/homeassistant.js` is a documented placeholder pending this), which requires Joseph physically at the devices. See `components/photo-tv-display/testing.md` for the full verified/not-yet-verified split.

**Blocked as of 2026-08-03 19:04 MST — waiting on Joseph being physically home.** The service is already live and running in production on the M8 in the meantime; this is purely a "not yet observed/confirmed" gap, not a broken or paused deploy.

**Planning docs:** `components/photo-tv-display/photo-tv-display-phase1-planning.md` (Phase 1), `components/photo-tv-display/photo-tv-display-phase2-planning.md` (Phase 2), `components/photo-tv-display/photo-tv-display-claude-code-instructions.md` (Phase 4)
**Notes:** Two views of one web app: a fullscreen ambient photo slideshow cast to the gathering room Google TV, and a touch-based phone controller (Joseph's/Robin's Pixel, browser bookmark, no app install) for curation/control. Node.js backend runs on the `photo-server` M8 alongside Immich, serving the web app, syncing TV↔phone over WebSocket (`ws`), and making all Immich API calls on the controller's behalf (including asset deletion, logged before/after the Immich delete confirms per the instructions doc). Hard dependency: `photo-server` must be operational (Immich running, both accounts created, at least a test subset of photos importable) before this build starts — already satisfied. Phase 1–2 planning and Phase 4 Claude Code instructions all complete; instructions doc status is "Ready for execution."

---

### CARD-0054 · [idea] [bedside-clock] Battery-powered tap-to-wake bedside clock for camper van
**Status:** Planning

**Planning docs:** `components/bedside-clock/bedside-clock-planning.md` (Phase 1, v1.2), `components/bedside-clock/bedside-clock-hardware-selection.md` (Phase 2, v1.3)
**Notes:** DS3231 RTC-based bedside clock for the Pleasure-Way van — tap/short-press wakes an SH1106 OLED to show time (DS3231 read/display/sleep), long-press triggers a WiFi-hotspot + NTP resync used only for timezone changes (not routine drift correction — DS3231 alone is accurate to ~1-2 min/year). Original "zero network footprint" BLE Current Time Service sync plan was found not viable (stock Android has no CTS server) and superseded by this DS3231+occasional-NTP approach in Phase 1 v1.2. No MQTT, SmartThings, HA, or watchdog registration — narrowest network footprint of any JCTsh component. Hardware confirmed on hand or ordered: 2 spare ESP32 DevKitC-32, EEMB 603449 LiPo + TP4056 (same combo as hiking-monitor), HiLetgo DS3231 5-pack (avoiding a documented trickle-charge/CR2032 safety hazard on generic combo boards), hiBCTR SH1106 OLED, Twidec panel-mount pushbutton. §2.14 battery-safety compliance table complete — point 7 (boost vs. direct-LDO) decided 2026-07-03 to keep TP4056+boost (matches on-hand stock, van's low over-discharge risk since it's usually shelved near USB power). Only remaining pre-build item is firmware low-battery cutoff design, explicitly deferred to Phase 4.

Phases 1–3 (planning, hardware selection, architecture/integration) all complete. Ready for Phase 4 (Claude Code instructions). Build has not started — no code, firmware, or deploy activity yet.

---

### CARD-0011 · [idea] [weather-station] Weather station
**Status:** Planning

**Planning doc:** `components/weather-station/jctsh-weather-station-planning.md`  
**Notes:** Full DIY outdoor weather station — BME280 (temp/humidity/pressure), VEML6075 (UV), SI1145 (solar irradiance), SparkFun Weather Meter Kit (wind/rain), AS3935 lightning detector, DS3231 RTC, SD card backup, solar+LiPo power. Posts to Weather Underground and Google Sheets. Phase 3 (architecture) complete — MQTT topics, payload schema, SmartThings integration, and six-phase build strategy all decided. Ready for Phase 4 (Claude Code instructions) when directed. Most parts to purchase (~$227 estimated).

---

### CARD-0101 · [bug] [hike-izer] A real hike can be misclassified as "not a hike" if GPSLogger keeps running into a trailing car drive — RESOLVED 2026-07-29 15:23 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 9237B, over the 5000B size threshold.

---

### CARD-0076 · [bug] [hiking-monitor] Rotate all secrets exposed via a botched redaction command, and finish outstanding device re-flashes — RESOLVED 2026-08-18 14:33 MST
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-08-22 (CARD-0193) — 10452B, over the 10000B size threshold.

---

### CARD-0070 · [enhancement] [hiking-monitor] Replace boost converter with LDO + gate peripheral power for lower standby draw — DEFERRED 2026-08-14
**Status:** Defer

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-08-22 (CARD-0193) — 15751B, over the 10000B size threshold.

---

### CARD-0072 · [idea] [personal] Digital Identity Checklist Version 2
**Status:** Build

**Notes:** Raised 2026-07-17, split out from CARD-0034's closure as the next layer of hardening on top of the v1-done core (phone/SIM-swap single point of failure closed). Works through `digital-identity-protection-checklist.md`'s remaining open items, targeting v3.0.

**Scope (in rough priority order):**
1. **ID document photo cleanup** — **fully done 2026-07-22, both accounts**: Google Photos copies moved to Locked Folder, RoboForm locator note added, Immich searched and cleared, camera roll/email/messages checked, trash/recently-deleted confirmed empty.
2. **Robin's app-password review** — **fully done 2026-07-22**: third-party apps cleared for both accounts (`myaccount.google.com/permissions`); Robin's App passwords checked via `myaccount.google.com/apppasswords` — none exist.
3. **Google Recovery Contacts** — Robin ↔ Joseph **done 2026-07-22**; adding the children **declined 2026-07-22** — decided not to add anyone else as a recovery contact at this time.
4. **Walk through the checklist together with Robin** — cheap, high-leverage: the household verbal protocol (codeword, voice-confirm-before-moving-money) only works if Robin actually knows it exists, not just that Joseph configured it.
5. **ChexSystems and LexisNexis freezes** — **both done 2026-07-22, both accounts** (ChexSystems' earlier registration error resolved).
6. **Remaining Phase 2 items:** "Skip password when possible" — **enabled 2026-07-22, both accounts**. ID copies in the safe — **done 2026-07-22**, Safe Contents manifest now fully placed. Outside-contact copy of backup codes — **moved to CARD-0071** (nephew designated as outside contact 2026-07-22, covers both Emergency Access and this). Travel copy — still open, plan decided but not yet implemented: unlabeled hard copy of half the backup codes in each of Joseph's and Robin's passport folders.
7. **Phase 4/5 prep:** Incident Response Plan — **done 2026-07-22**, printed and placed in the safe (`Incident Response Plan.pdf`, repo root). Phase 5 travel items still wait until a trip is actually upcoming.
8. **Accounts Without 2FA section** — **resolved 2026-07-22, not applicable**: confirmed all financial accounts, including the credit union originally flagged as the example, already have 2FA enabled.

**Note:** Emergency Access and Google Inactive Account Manager are deliberately **not** in this card's scope — split out to CARD-0071.

**Canonical detail lives in `digital-identity-protection-checklist.md`** (now v3.0, the version this card was targeting) — this card summarizes status, that file is the actual checklist.

**Related:** `digital-identity-protection-checklist.md` (repo root), `digital-identity.md` (companion reference doc).

---

### CARD-0009 · [enhancement] [hiking-monitor] Enclosure design and build — RESOLVED 2026-08-18 14:33 MST
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-08-22 (CARD-0193) — 13458B, over the 10000B size threshold.

---

### CARD-0077 · [bug] [photo-server] Weekly backup cron collided with Immich's nightly DB dump, causing stale-backup alert — RESOLVED 2026-07-28
**Status:** Done

**Notes:** Found 2026-07-22 via the CARD-0051 heartbeat check: `Immich degraded - backup:stale (10.3d since last success)`. Confirmed live via SSH — Docker containers all healthy, no data loss, disk usage normal on all three mounts (primary 73%, backups 39%/49%) — this was a stamp-write failure, not an actual backup outage.

**Root cause:** `photo-library-backup.sh` runs weekly via cron at `0 2 * * 0`. Immich's built-in nightly DB dump also runs at 02:00 daily (confirmed by `immich-db-backup-*-020000-*.sql.gz` filenames). On the 2026-07-19 run, rsync caught the DB dump's temp file mid-write/rename on both legs — Joseph's leg exited code 23, Robin's exited code 24 ("file has vanished... immich-db-backup-20260719T020000...sql.gz.tmp"), the same vanished-temp-file race already visible as a stale log entry from 2026-07-05. Since the script only touches `/home/jct/photo-library-backup-success.stamp` when both rsync legs return 0, this run's failure silently skipped the stamp (and correctly fired an MQTT "Backup failed" alert that apparently wasn't seen standing alone).

**Fix applied 2026-07-22:**
1. Rescheduled the cron entry from `0 2 * * 0` to `15 2 * * 0` (`crontab -e` on photo-server) so the weekly rsync starts 15 minutes after the DB dump, clear of the collision window.
2. Manually reran `/usr/local/bin/photo-library-backup.sh` to write a fresh success stamp and clear the alert immediately, rather than waiting a full week for the next scheduled run.

**Manual rerun confirmed clean 2026-07-22 09:39** — both rsync legs exited 0, stamp file updated (`/home/jct/photo-library-backup-success.stamp` now Jul 22 09:39), alert cleared.

**Closing criterion confirmed 2026-07-28, via direct SSH check on the M8:**
- Success stamp updated Jul 26 02:21:06 MST — only gets touched when both rsync legs exit 0.
- Cron fired exactly on the rescheduled time: `CRON[2399490]` ran the script at 02:15:01 on 2026-07-26.
- No vanished-file errors in that run — every `vanished` line in the 10.8MB backup log traces back to the old 2026-07-05/2026-07-19 runs already documented above; the 2026-07-26 run's own tail (DB dump backup, normal delete/sync output, final rsync summary) is clean.

The reschedule held on its first real scheduled run, not just the manual rerun — closing out.

---

### CARD-0108 · [enhancement] [hike-izer] Grounded external context for the narrative (place identification, scoped search, regional knowledge) — RESOLVED 2026-07-29 07:44 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 15764B, over the 10000B size threshold.

---

### CARD-0106 · [bug] [hike-izer] Hike Start Forecast has captured zero rows since at least June 2026, despite CARD-0083/CARD-0097 shipping and being verified live — RESOLVED 2026-07-29 07:44 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7278B, over the 5000B size threshold.

---

### CARD-0104 · [idea] [hike-izer] Embed Gaia GPS's own track/map view instead of building a custom route+elevation renderer — option 1 verified live on 2 real hikes 2026-07-28 — RESOLVED 2026-07-29 07:44 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7938B, over the 5000B size threshold.

---

### CARD-0086 · [idea] [hike-izer] Automatic triggering — RESOLVED 2026-07-28
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 18619B, over the 10000B size threshold.

---

### CARD-0098 · [enhancement] [traveling] Randomized/staggered occupancy-simulation lighting while traveling — RESOLVED 2026-07-28
**Status:** Done

Archived to `components/traveling/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7811B, over the 5000B size threshold.

---

### CARD-0105 · [enhancement] [hike-izer] Continuous improvement — running list of small Hike-izer enhancements — RESOLVED 2026-07-29 05:35 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 8178B, over the 5000B size threshold.

---

### CARD-0111 · [enhancement] [hike-izer] Iterative refinement resulting from hike of July 29 — RESOLVED 2026-07-29 07:37 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6838B, over the 5000B size threshold.

---

### CARD-0109 · [enhancement] [hike-izer] Tighten the narrative's non-redundancy rule — RESOLVED 2026-07-28
**Status:** Done

**Raised 2026-07-28**, split out of CARD-0105 after Joseph's review of today's automatically-generated narrative: it mostly restates numbers and facts already present in the Data Summary / Coverage tables, in prose, with added words but not much added value — despite `SKILL.md`'s narrative-writing step already containing a non-redundancy rule ("don't restate numbers that belong in the data tables — interpret and connect instead").

**Diagnosed against real evidence:** compared today's actual narrative to the tables it's meant not to repeat. Four sentences were restatement in different words, not the digit-quoting the existing rule's examples focused on — "wrapped up in a little over half an hour" (Duration: 32m), "a gentle undulation of a few dozen feet" (Elevation Range/Gain), "roughly two miles of ground" (Distance: 2.0 mi), and, most tellingly, "the environmental sensor logged nothing... **detailed in the coverage section below**" — the narrative itself pointing at the exact section it duplicates. Root cause: the rule's worked examples only covered elevation and temperature; for other stats the model satisfied a literal reading of "turn it into an observation" with a soft paraphrase instead of real interpretation.

**Fixed — `SKILL.md` rule rewrite:** tightened the non-redundancy rule to explicitly cover paraphrase ("restating a number in softer words is still restating it"), added a concrete test ("does this connect the number to something else... or does it just describe the number in prose?"), and specifically addressed the coverage-section case (brief mention only if it limits the story, no forward-references to sections that already exist).

**Scope grew mid-card, 2026-07-28 (Joseph):** sun position in the narrative had the identical problem (raw degree values quoted in prose — "about ten degrees above the horizon... swings from east-southeast toward due east"), directly in tension with the rule just tightened. Fix: move sun elevation/direction into the Data Summary table, same treatment as every other measured range — **this was not actually prompt-only** (corrected mid-implementation after checking `templating.py`): the Data Summary table is deterministically templated from computed `stats`, not freely written, so this needed real code:
1. `components/hike-izer/fetch_hike_data.py` — compute `sun_elevation_deg` (min/max range) and `sun_direction_start`/`sun_direction_end` from `sun_position_samples`, added to `stats`.
2. `components/hike-izer-orchestrator/templating.py` — new `_sun_direction_display()` helper, two new Data Summary rows ("Sun Elevation Range", "Sun Direction").
3. `SKILL.md` part (a) — removed the instruction to quote sun degrees in prose, replaced with the same qualitative treatment already used for elevation.

**Verified against real data 2026-07-28:** ran `fetch_hike_data.py` fresh against today's real hike, rendered `templating.py`'s `data_summary_rows()` against the output — `Sun Elevation Range: 10.7–16.0°`, `Sun Direction: ESE → E`, matching the original narrative's own description almost exactly, confirming both the astronomy computation and the new table rows work correctly end-to-end.

**Related:** CARD-0105 (the unscoped idea this splits out of), `.claude/skills/hike-izer/SKILL.md`, `components/hike-izer/fetch_hike_data.py`, `components/hike-izer-orchestrator/templating.py`.

**Moved to Done 2026-07-29 05:14 MST** — no open items remained; both fixes (SKILL.md rule rewrite and sun-position table move) were verified against real data.

---

### CARD-0107 · [enhancement] [hike-izer] Vision-based photo identification — captions, not narrative — RESOLVED 2026-07-28
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6920B, over the 5000B size threshold.

---

### CARD-0092 · [idea] [hike-izer] Calendar view on a home page, clickable through to hike summaries — RESOLVED 2026-07-28
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5863B, over the 5000B size threshold.

---

### CARD-0091 · [idea] [hike-izer] Drop Markdown output, HTML becomes the sole format — RESOLVED 2026-07-28
**Status:** Done

**Raised 2026-07-24**, during CARD-0083 planning — Joseph questioned the ongoing value of generating `.md` alongside `.html` now that HTML had become the richer format: CARD-0081 gave it real styling/structured layout, CARD-0084's photo gallery was already HTML-only (no equivalent in the Markdown), and CARD-0088 was standing up real public hosting specifically for the HTML output.

**Trigger condition met:** the card's own "recommended timing" was to wait until CARD-0088 (HTML hosting) actually shipped — it had, well before this was picked up, and had been live/verified through several subsequent cards (CARD-0086, CARD-0093, CARD-0094, CARD-0100, CARD-0101).

**Real scope was bigger than the card originally described.** The original "Scope when picked up" note only mentioned `.claude/skills/hike-izer/SKILL.md` — written before CARD-0086 (automatic triggering) existed. Auditing the actual current codebase found `components/hike-izer-orchestrator/generation.py`/`templating.py` independently duplicating the same `.md` + `.html` generation, and unlike the interactive Skill (which explicitly documented "the Markdown file is not copied"), the automatic path wrote both straight into the M8's publicly-served directory — a real, live inconsistency found via `docker logs`/`ssh` inspection, not something the original card anticipated.

**Executed 2026-07-28:**
1. **SKILL.md:** removed the standalone "save to `.md`" step, merged HTML generation into what's now a single step 5, renumbered steps 6-7 accordingly, dropped every "Markdown" reference (frontmatter description, step 4's structure framing, the weather-forecast "applies to both formats" clause, the publish step's "Markdown file is not copied" note, the file-extension example in the multi-day-trip handling), and removed a stale pointer to an example `.md` file that's now deleted.
2. **`templating.py`:** removed `render_markdown()` entirely (53 lines) and its section header; updated the module docstring.
3. **`generation.py`:** removed the `md_text` generation and file-write; updated a stale "SKILL.md's interactive steps 3/7" docstring reference to the new step numbers (3/6).
4. **`narrative.py`:** updated the system prompt's "ignore every other step... (data fetching, HTML/Markdown mechanics...)" to drop "Markdown" — left the separate, unrelated "no Markdown formatting" instruction alone (that one's about prose syntax within the narrative paragraphs, not the output file format).
5. **Both hike-izer READMEs** (`components/hike-izer/README.md`, `components/hike-izer-orchestrator/README.md`): dropped remaining "Markdown"/`.md` references, fixed the same stale step-number reference.
6. **Existing `.md` files — deleted** (Joseph's call): 4 local files under `hike-izer/summaries/` (`2026-06-17`, `2026-06-18`, `2026-07-18`, `2026-07-23`) plus the one stray copy already live-published on the M8 (`2026-06-18_hike-summary.md`, a leftover from CARD-0086 stage 2's test run against real data).
7. **Deployed and verified:** `generation.py`/`templating.py`/`narrative.py`/`SKILL.md` redeployed to the M8, orchestrator rebuilt, confirmed healthy and `hikes.jctnet.com` still serving correctly, confirmed no `.md` files remain in the M8's served directory. Also smoke-tested `templating.render_html()` locally against a synthetic `hike_data` fixture post-edit to confirm no leftover reference to the removed `render_markdown` broke anything (a first attempt caught a fixture bug, not a code bug — fixed and re-ran clean).

**Related:** CARD-0088 (HTML hosting, this card's trigger condition), CARD-0081 (HTML rendering, the format this card made sole), CARD-0084 (Photos, HTML-only, the existing precedent), CARD-0073 (Hike-izer v1, original `.md`-only scope), CARD-0086 (automatic triggering, the component whose duplicate `.md` generation this card also had to catch), CARD-0083 (the card whose planning surfaced this question).

---

### CARD-0094 · [idea] [hike-izer] Switch hike-izer-web from Tailscale Funnel to Cloudflare Tunnel — RESOLVED 2026-07-27
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7381B, over the 5000B size threshold.

---

### CARD-0100 · [bug] [hike-izer] Automatic trigger (CARD-0086) generates and publishes a page even when no hike is confirmed (e.g. GPSLogger left on during a car errand) — RESOLVED 2026-07-27
**Status:** Done

**Raised 2026-07-25**, Joseph asked what happens if GPSLogger is accidentally left running in a car and then stopped.

**Already handled, confirmed via code read:** `fetch_hike_data.py` already classifies each GPS session by median speed (`WALKING_SPEED_MIN_MPS`/`MAX_MPS`, ~0.15–3.0 m/s) plus daylight/stationary checks, marking anything outside walking pace `is_hike: false` with a rejection reason (e.g. "likely vehicle travel, not a hike") — a car trip's data is not mistaken for a hike at the classification level.

**Real gap that existed:** the automatic webhook path (`hike-izer-orchestrator/generation.py`) didn't act on that classification before doing real work. `hike_data["coverage"]["gps_track"]["hike_confirmed"]` only gated whether photos got fetched — regardless of its value, `run()` unconditionally made a real Claude API call, wrote and published an `.html`/`.md` page to the live public URL, and logged `"Published hike summary for <date>"` to MQTT. A car errand that was the only GPS activity for a day would still produce a real published page and a real API charge.

**Fixed 2026-07-27** in `generation.py`: `run()` now checks `hike_data["coverage"]["gps_track"]["hike_confirmed"]` immediately after the `fetch_hike_data.py` subprocess call, before photos/narrative/templating/publish. If false, it publishes a quiet `System`-category log (`"GPSLogger stopped, no hike confirmed for <date> -- skipped generation."`) and returns `None`; `run_and_log()` treats a `None` return as "already logged, nothing more to do" so it doesn't also publish a "Published hike summary" message. Scoped to the automatic webhook path only — the interactive Skill still correctly reports "no hike" when Joseph explicitly asks, since that's a wanted answer, not a bug. The old redundant `if hike_confirmed:` photos-gate was removed since it's now always true past the new early return. `_build_session_entry`/etc. untouched — this card only touches control flow in `generation.py`, not classification.

**Mock-verified 2026-07-27** (subprocess/API/MQTT all mocked, no real cost): no-hike-confirmed case skips narrative/templating entirely and publishes exactly one skip log; `run_and_log()` publishes nothing extra on that path; hike-confirmed case still reaches narrative/templating unaffected — new gate doesn't touch the working path.

**Live-verified 2026-07-27, real deployment.** Rebuilt and redeployed the `hike-izer-orchestrator` Docker image on the M8 (`docker compose up -d --build orchestrator` — also picked up the CARD-0101 `fetch_hike_data.py` fix, whose copy on the M8 was stale until this deploy). Sent a real `POST` to the live webhook (`https://photo-server.tailfe828a.ts.net/webhook/hike-end`) for a date with zero GPS/environmental activity: `docker logs` showed 0 rows fetched → immediate `"No hike confirmed ... skipping generation"` with no narrative step in between; `curl` against the would-be published page returned `404` (nothing written); the exact skip message showed up live on the JCTsh log dashboard (`http://100.70.162.24/data`, component `hike-izer-orchestrator`, category `System`) via the real MQTT path, not just a mock.

**Related:** CARD-0086 (the automatic-triggering component this gap lived in), CARD-0101 (the sibling GPS-classification fix deployed in the same M8 rebuild), `components/hike-izer-orchestrator/generation.py`, `components/hike-izer/fetch_hike_data.py` (the existing car-vs-hike classification this card builds on, not replaces).

---

### CARD-0093 · [enhancement] [personal] Clean up DNS records on both `jctnet.com` and `jctnet.net` — RESOLVED 2026-07-27
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-08-22 (CARD-0193) — 8063B, over the 5000B size threshold.

---

### CARD-0102 · [investigation] [infrastructure] Audit: what else breaks when the Pi/M8 weekly scheduled reboots discard in-flight state — RESOLVED 2026-07-27
**Status:** Done

**Raised 2026-07-27**, prompted by the CARD-0098 finding that the Pi's `scheduled-reboot.timer` (CARD-0035) silently disabled the Traveling Lights automation via HA's `initial_state:` key. Joseph asked what else that same weekly-reboot blast radius could be quietly breaking, on both hosts CARD-0035 covers.

**Confirmed the reboot's actual scope on the Pi:** it's a full `/sbin/reboot` (not a targeted Docker/HA bounce) — `uptime -s`, and `mosquitto`/`nodered`/`jctsh-logging`/`docker` `ActiveEnterTimestamp` all landed within the same ~90 sec window as `scheduled-reboot.timer`'s last run (2026-07-27 03:00 MST).

**Pi audit:**
- **HA automations:** grepped all of `automations.yaml` for `initial_state:` — Traveling Lights was the only automation using it (fixed under CARD-0098). No other automation carries the same "forced state on every restart" risk.
- **Garage Presence countdown timer** (`timer.garage_presence_timer`): HA's native `timer` domain always resets to idle on any restart (never resumes a countdown) — but "Garage Presence - Sync timer to vswitch" already anticipates this, re-arming the timer at full duration on a `homeassistant: event: start` trigger if `switch.garage_presence_vswitch` is still "on" (regular switches do restore their last state). Already resilient, no fix needed.
- **Mosquitto:** `persistence true` set in `mosquitto.conf` — retained messages/subscriptions survive the broker restart.
- **Docker:** only one container runs on the Pi (`homeassistant`) — no other containerized service in scope.
- **Node-RED:** `contextStorage` is commented out in `settings.js` (in-memory only) — grepped all flow JSON for `context.get/set` and found only the watchdog's per-component 35-min silence timers (`fn_timer_manager`). Those are inherently ephemeral `setTimeout` handles anyway and self-heal on each component's next heartbeat (30 min cadence) — a reboot just means a brief re-arm window, not lost tracking.

**M8 audit** (its own `scheduled-reboot.timer`, Monday 4:00 AM local — staggered 1 hr after the Pi's 3:00 AM specifically so its heartbeat's MQTT publish doesn't collide with the Pi mid-reboot, per CARD-0035): all 7 containers (`hike-izer-orchestrator`, `hike-izer-web`, `netalertx`, `immich_server`, `immich_postgres`, `immich_machine_learning`, `immich_redis`) run `unless-stopped`/`always` restart policies and came back healthy after this morning's reboot. No equivalent to HA's `initial_state:` exists anywhere in the M8 stack — there's no "disabled by default, manually armed before use" toggle pattern the way Traveling Lights has. App-level settings (Immich job state, NetAlertX config) live in Postgres/SQLite on persisted volumes, not restart-time config, so they aren't at risk the same way. The weekly backup cron (Sun 2:15 AM) doesn't overlap the Monday 4:00 AM reboot.

**Conclusion:** the Traveling Lights `initial_state:` bug (fixed under CARD-0098) was the only real gap found. Everything else either doesn't use the risky "force a state on every startup" pattern or was already designed with the weekly reboot in mind.

**Related:** [[project-jctsh]], CARD-0098, CARD-0035 (weekly reboot origin), CARD-0036 (reboot dashboard visibility).

---

### CARD-0099 · [bug] [data-pipeline] Timeline sheet's `timestamp_az` column hardcodes Arizona local time for every row, regardless of where it happened — RESOLVED 2026-07-25
**Status:** Done

Archived to `core/data-pipeline/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5053B, over the 5000B size threshold.

---

### CARD-0097 · [bug] [hike-izer] Hike Start Forecast capture hardcodes Arizona timezone — breaks anywhere but Arizona (Michigan trip, then Egypt trip Feb 2027) — RESOLVED 2026-07-25
**Status:** Done

**Raised 2026-07-25**, originally scoped ahead of a planned Egypt hiking trip in February. **Re-scoped same day:** this is not a US-vs-international issue — Phoenix is fixed UTC-7 with no DST, so *any other timezone*, including Michigan (Eastern, UTC-4/-5 depending on DST), hits the same bug. Moved to Build immediately because Joseph is traveling to Michigan and needs Hike-izer working correctly there before the Egypt trip.

**Fix written and desk-verified 2026-07-25** — `core/data-pipeline/environmental-data.gs`'s `_maybeCaptureHikeStartForecast` now calls Open-Meteo with `timezone=auto` (server-side IANA lookup from lat/lon) instead of hardcoded `America/Phoenix`, and derives both the day-bucket and the nearest-hour match from the returned `utc_offset_seconds` instead of a fixed `-07:00`. `SCRIPT_VERSION` bumped to `2026-07-25.1-hike-start-forecast-timezone-fix`. Verified via a standalone Python port of the exact date arithmetic (Apps Script can't run outside its own editor) covering: Egypt/Giza (UTC+2), Michigan winter (EST, UTC-5), and a Michigan near-midnight edge case — all bucketed to the correct local calendar day and matched the correct local hour. A regression check confirmed the *old* hardcoded logic would have picked a forecast hour ~8.75 hours off for the Egypt case, i.e. the bug was real, not theoretical.

**Deployed and confirmed live 2026-07-25** — Joseph pasted the updated file into the Apps Script editor and redeployed (Deploy → Manage deployments → pencil → New version). Confirmed via `curl` against the live deployment URL: response `version` field reads `2026-07-25.1-hike-start-forecast-timezone-fix`, matching the fix. Same deployment URL, no Node-RED/Tasker changes needed.

**Scope confirmed via code read:** the webhook/orchestrator path (`app.py`, `generation.py`, `fetch_hike_data.py`) already threads the phone's real local UTC offset through correctly — no hardcoded-timezone assumption there. The one real gap is `core/data-pipeline/environmental-data.gs`'s `_maybeCaptureHikeStartForecast` (built for CARD-0083), which hardcodes Arizona in two places:
1. Buckets "first observation of the day" using Arizona's calendar date (`_azString`) regardless of where the hike actually is — for any other timezone this can capture on the wrong day relative to the hike's real local date.
2. The Open-Meteo request hardcodes `&timezone=America%2FPhoenix`, then parses the returned hourly timestamps with a hardcoded `-07:00` offset — so the "closest hour to hike start" match is computed against Arizona wall-clock hours mislabeled as if local to the hike, picking the wrong hour's forecast and mislabeling the times shown in the summary output.

Open-Meteo itself is a global provider (not US-only), so this is a fix, not a provider swap: derive both the day-bucket and the API's `timezone` param from the hike's actual local offset (Open-Meteo supports `timezone=auto` given lat/lon), instead of hardcoding Phoenix.

**Acceptance criteria (desk-verified, not requiring a live trip to close):** feed the function synthetic non-Arizona coordinates/timestamps — at minimum Michigan (Eastern, UTC-4/-5) and Egypt-like (Giza, ~UTC+2) — and confirm the captured forecast row picks the correct local hour and correct calendar-day bucket in each case, not Arizona's.

**General principle (Joseph, 2026-07-25):** no component Hike-izer touches should assume a fixed home timezone or location — every timezone/location-dependent computation must derive from the hike's actual coordinates/local offset, never a hardcoded Phoenix/home default. This fix is the one confirmed instance; if another hardcoded-Arizona assumption turns up elsewhere in the Hike-izer path later, it's an instance of this same principle, not a separate one-off.

**Related:** CARD-0083 (original Hike Start Forecast feature, source of the hardcoded assumption), `core/data-pipeline/environmental-data.gs`.

---

### CARD-0088 · [idea] [hike-izer] HTML output hosting (real URL, not an email attachment) — RESOLVED 2026-07-24
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7070B, over the 5000B size threshold.

---

### CARD-0083 · [idea] [hike-izer] Show the weather forecast as it stood at hike start — RESOLVED 2026-07-24
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7945B, over the 5000B size threshold.

---

### CARD-0089 · [bug] [netalertx] Test upstream fix for the webhook HMAC signature bug (netalertx/NetAlertX#1720) — RESOLVED 2026-07-24
**Status:** Done

**Notes:** Raised 2026-07-24. Maintainer response to the upstream bug filed during CARD-0078 (compact-vs-default JSON serialization mismatch between what NetAlertX signs and what it actually transmits in `_publisher_webhook/webhook.py`) — said it's fixed in an unreleased build and asked for confirmation testing against `ghcr.io/netalertx/netalertx-dev-unsafe` before merging/releasing, or the fix may be reverted.

**Not blocking JCTsh:** the production webhook consumer (Node-RED, CARD-0078) already works around this bug independently (re-serializes to match NetAlertX's buggy signature before verifying) — this test was purely to help the upstream fix land for the wider NetAlertX community, not something JCTsh needed.

**Test setup (photo-server/M8, 2026-07-24):** isolated compose project (`netalertx-test`), fresh/empty data dir (own DB/config, production instance never touched), unique ports (`PORT=20213`, `GRAPHQL_PORT=20214` vs. production's `20211`/`20212` — required since both use `network_mode: host`), image `ghcr.io/netalertx/netalertx-dev-unsafe:next_release` (the actual available tag — no `:latest` exists for this repo; found via GHCR's anonymous token + tags/list API after a docker-compose pull failure). Torn down completely afterward (container, capture listener, test directory) — `docker ps` confirms only production `netalertx` running.

**Confirmed fixed, three independent ways:**
1. **Source read directly** — `_publisher_webhook/webhook.py` now computes `payload_json = json.dumps(_json_payload, separators=(',', ':'))` **once** and reuses it for both the actual curl transmission and the HMAC signature, with an explicit comment: *"Serialize once so the transmitted payload and HMAC signature always match."* This is the exact bug from #1720, fixed at the root, not worked around.
2. **Live trigger, not just code reading** — inserted a synthetic `Notifications` row directly (matching the schema `NotificationInstance.getNew()` reads), set a real `WEBHOOK_SECRET` via the Settings DB table (found via `config.json`'s `WEBHOOK_SECRET` field after the Settings UI publishers tab never populated for an unclear reason — a live app quirk, not a fix-verification blocker), and ran `webhook.py` directly to produce a real outbound signed POST, captured via a local raw-HTTP listener.
3. **Independently recomputed the HMAC** from the exact captured body bytes (893 bytes, matching `Content-Length`) against the received `X-Webhook-Signature` header — **exact match** (`e2984a7d7ae3ea61349db39fe44149e76eabc373f98687a23f023a78d7489d23` both computed and received).

**Confirmation reported back to the GitHub issue same day (2026-07-24)** — maintainer acknowledged and kept it open until the production release, closing it 2026-08-04 when v26.8.5 shipped with the fix. See CARD-0161 for the production landing of that release.

**Related:** CARD-0078 (where the bug was found and worked around), `netalertx/NetAlertX#1720` (upstream issue), `components/netalertx/docker-compose.yml`.

---

### CARD-0084 · [idea] [hike-izer] Photo integration (Immich) — RESOLVED 2026-07-24
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7410B, over the 5000B size threshold.

---

### CARD-0081 · [idea] [hike-izer] HTML rendering, Levels 1-2 (basic styling + structured layout) — RESOLVED 2026-07-24
**Status:** Done

**Notes:** Raised 2026-07-23. Current output (v1, CARD-0073) was Markdown only. Goal: improve readability and shareability via HTML rendering, built iteratively — start simple, layer in complexity over successive passes rather than one big build. Originally scoped as a 5-level iteration path in this one card; narrowed 2026-07-23 to just Levels 1-2 per Joseph's preference for shorter-running cards, with Levels 3-5 (embedded visuals, interactive, hosting) split out to **CARD-0088**. CARD-0088 was itself narrowed 2026-07-24 after its embedded-visuals/interactive scope turned out to be pure duplicate of CARD-0082 (visuals) and CARD-0084 (photos) — it now covers only hosting.

**Scope (this card):**
1. **Basic styling** — real typography, readable width, light/dark support via CSS custom properties + `@media (prefers-color-scheme: dark)` (same convention as `core/logging/log_server.py`'s `_KANBAN_TEMPLATE`, no new dependency — no Markdown→HTML library exists anywhere in this repo). Same content as the `.md` output, just legible and presentable.
2. **Structured layout** — a stat-row hero (Date, Duration, Distance, Elevation Gain) before the narrative, distinct visually-separated sections (narrative / data tables / full observations / pipeline-health coverage).

**Implementation:**
- `components/hike-izer/fetch_hike_data.py` — added `stats.distance_mi`, a new data-layer figure that didn't exist before (only altitude range/gain was computed). Summed per-session via `_haversine_m` in `_gps_sessions()`, then totaled across `is_hike`-confirmed sessions only in `main()` (not all GPS activity for the day — driving between trailheads or GPS drift at camp shouldn't count). `None` when `hike_confirmed` is false, never a fake zero.
- `components/hike-izer/html-template.html` (new) — the static CSS/structure reference the Skill copies from on every run, keeping output visually consistent across independently-authored invocations rather than restyled each time.
- `.claude/skills/hike-izer/SKILL.md` — added a step generating `<date>_hike-summary.html` alongside the Markdown, with the stat-row field mapping and the "not available" rule for missing figures (never blank/zero).
- `components/hike-izer/README.md` — updated file listing.

**Verified (2026-07-23):** re-ran `fetch_hike_data.py` for 2026-06-18 (confirmed hike) — `stats.distance_mi` computed correctly (3.16mi across two sessions in the fetched window, one being June 17's midnight-crossing tail; same pre-existing whole-window scope as elevation/temp stats, not a new bug — the June-18-only session is 2.03mi/112ft, matching the existing `.md`). Hand-authored two real `.html` files and opened both in Chrome:
- `hike-izer/summaries/2026-06-18_hike-summary.html` — confirmed-hike day, full stat row (2.0mi, 112ft, 68.3min), light-mode colors correct, dark-mode CSS-variable cascade confirmed correct across body/stat-cards/tables, mobile breakpoint rule (`@media max-width:640px`, 4→2 columns) confirmed present and correct in the parsed stylesheet.
- `hike-izer/summaries/2026-07-23_hike-summary.html` — `hike_confirmed: false` day, Distance/Elevation Gain correctly render as styled "not available" (muted italic) while Date/Duration still show real values, GPS-confirmation callout renders, all 19 observation rows present.

**Polish (2026-07-24):** dropped the date from the H1 (`html-template.html` and both generated files) — it was redundant with the Date stat card immediately below it, the first two lines of the page repeating the same figure.

**Related:** CARD-0088 (HTML output hosting — the one remaining piece of the original Levels 3-5 scope, narrowed), CARD-0082 (Visual track + elevation graphic — owns embedded-visuals/interactive scope directly), CARD-0084 (Photo integration — owns photo scope directly), CARD-0073 (Hike-izer v1, Done).

---

### CARD-0087 · [bug] [hiking-monitor] GPSLogger ran during today's hike but zero rows reached the GPS Track sheet — RESOLVED 2026-07-23
**Status:** Done

**Notes:** Found 2026-07-23 while running Hike-izer for today. Requested a Hike-izer summary for today's hike; `fetch_hike_data.py` returned zero GPS Track rows. Joseph confirmed GPSLogger was actively running for the entire hike today, and — importantly — **was not running on any other day in the past week**. So the only day with a real, confirmed expectation of GPS Track data was today, and today produced none. This was one concrete failure instance, not evidence of a long-running continuous outage — the GPS Track sheet's most recent row before today was 2026-06-18, but that gap likely just reflected GPSLogger not being used in between, not the pipeline being broken that whole time.

**Confirmed via direct investigation:** queried the GPS Track sheet's `action=export` endpoint with no date filter — 806 total rows, most recent timestamp 2026-06-18T21:55:32Z, nothing since. Meanwhile the Hiking Observations sheet *did* receive 19 real rows today (5:45–8:28 AM MST, clearly a real hike) via the same Apps Script deployment — so today's break was isolated to GPSLogger's specific upload path, not a general Apps Script/Sheets outage.

**Root cause — confirmed 2026-07-23:**
1. Server-side ingestion tested directly with a synthetic well-formed request (`action=gps&lat=...&key=<current API_KEY>`) — returned `{"status":"ok"}` and appended cleanly. Current deployment, current API key, and the `action=gps` code path were all confirmed working correctly.
2. Joseph checked GPSLogger's actual configured Custom Logging URL — it was the **bare deployment URL with no query string at all**: no `action=gps`, no `lat`/`lon`/`acc`/`alt`/`ts` placeholders, and no `key`. Every request GPSLogger sent had zero parameters, which the script correctly rejected as `{"status":"error","message":"unauthorized"}` — **but returns that as an HTTP 200**, so GPSLogger had no signal anything was wrong.
3. Fixed: full correct URL (`.../exec?action=gps&lat=%LAT&lon=%LON&acc=%ACC&alt=%ALT&ts=%TIME&key=<API_KEY>`) given to Joseph to paste into GPSLogger's Custom Logging URL field, replacing the bare URL.

**How this happened despite being on the documented migration checklist:** `components/hiking-monitor/data-pipeline.md`'s 2026-07-18 redeploy note *does* correctly list GPSLogger's custom URL as one of the places to update during any future redeploy — this wasn't a case of nobody knowing to check it. The gap was verification, not identification. Every other consumer on that list has a way to machine-confirm the update actually stuck: Node-RED's env var was checked live via `/proc/<pid>/environ`, the read/export side was checked via `action=version`. GPSLogger's config lives only on the phone, outside anything checkable remotely — the only real verification is a live field test, and the *original* Step 19 build instructions (`hiking-monitor-claude-code-instructions.md`) actually required exactly that ("take a short outdoor walk... verify trackpoints appearing in the sheet") when the pipeline was first built. That same discipline wasn't re-applied when the URL was later swapped during the 2026-07-18 migration — a URL update felt lower-risk than the original build, but for a manually-typed URL with five placeholder tokens in it, it isn't.

**Field-test confirmation (2026-07-23):** Joseph did a short verification walk near the house with the corrected URL in place. Confirmed via direct `action=export` query against the GPS Track sheet: six real trackpoints landed at 18:27:06–18:30:18 UTC, ~30s apart (matching GPSLogger's normal upload cadence), clustered around 32.4614, -111.1185 — within ~15m of the house footprint centroid (`house-lot-coordinates.md`), with naturally varying accuracy (9–25m) and altitude (721–744m) values consistent with real phone GPS rather than synthetic test data. This is distinct from the earlier synthetic debug row at 20:00:00 UTC (suspiciously round `lat: 32.4321, lon: -111, accuracy_m: 10, altitude_m: 800`). Confirms the corrected URL works end-to-end with the real GPSLogger app.

**Process fix, so this doesn't recur:** `data-pipeline.md`'s migration checklist should flag GPSLogger specifically as requiring a live field-test confirmation, not just "update the URL" — it's the one consumer on that list with no machine-checkable verification path.

**Related:** CARD-0073 (Hike-izer v1, Done — original GPSLogger URL migration), `components/hiking-monitor/gps-pipeline.md`, `components/hiking-monitor/data-pipeline.md` (redeploy checklist), `components/hike-izer/fetch_hike_data.py`.

---

### CARD-0079 · [bug] [logging] Old null-byte corruption in the log file (536 bytes, historical, inactive) — RESOLVED 2026-07-23
**Status:** Done

**Notes:** Found 2026-07-22 while testing CARD-0078's webhook fix. Initial concern was that a confirmed-published MQTT message never appeared in `/mnt/jctsh-logs/jctsh.log` or the live `/log` endpoint — **resolved as a false alarm, not a bug:** `log_server.py` holds the most recent non-heartbeat message in a single global `_pending` slot and only flushes it to disk once a *different* non-heartbeat message displaces it (`_store_entry()`, `core/logging/log_server.py`). The live `/data` endpoint (which includes `_pending`) had the message the whole time; sending a second distinct test payload immediately flushed the first to the file, confirmed directly. Working as designed.

**What was real:** while investigating, found genuine null-byte corruption in the log file — 536 bytes total, in two small contiguous runs (367 and 169 bytes), confirmed via direct Python byte-level scan (`/mnt/jctsh-logs/jctsh.log`). The earlier "7,634" figure quoted from `grep -c $'\x00'` was wrong — that shell substitution doesn't actually pass a null byte as a grep pattern, so it silently matched an empty pattern and just counted total lines in the file, not corruption. Both null-byte runs sat in **old content from around 2026-07-03** (real log lines resumed immediately after each run) — not recent, not growing, not connected to CARD-0006's log-directory migration or that night's testing.

**Surgical cleanup done (2026-07-23):** backed up the live file first (`/mnt/jctsh-logs/jctsh.log.bak-20260723-precard0079`), then re-scanned to get exact byte offsets — 367-byte run at offset 340640, 169-byte run at offset 360279 (offsets shifted slightly from the original find since the file kept growing between the initial report and cleanup). Confirmed both runs sat cleanly between two complete log lines with no partial-line truncation, then spliced them out (removing from the highest offset first so lower offsets stayed valid) and rewrote the file. Verified: 0 null bytes remaining, byte count dropped by exactly 536 (823545 → 823009), and both seams rejoin correctly (`...Log server connected.\n2026-07-01 03:11:54...` and `...Log server connected.\n2026-07-03 07:58:52...` both found intact, no merged/split lines).

**Deliberately out of scope, not a remaining gap:** root-causing *why* the corruption happened around 2026-07-03 (crash/kill mid-`RotatingFileHandler`-write is the likely mechanism, but never confirmed against git history/deploy log for that date) — low priority, only worth revisiting if similar corruption recurs. Also unrelated: two harmless fake test entries from CARD-0078 verification (`Test Vendor Inc` / `aa:bb:cc:dd:ee:ff`, `Second Test Vendor` / `11:22:33:44:55:66`) are still in the real log — left in place, clean up manually if it bothers you.

---

### CARD-0078 · [bug] [netalertx] False "New device detected" alerts re-fire after any Node-RED restart — RESOLVED 2026-07-23
**Status:** Done

**Notes:** Found 2026-07-22, triggered by CARD-0006's Pi reboot test. Three devices showed "New device detected" alerts timestamped that night despite NetAlertX's own history showing they first connected 07-14, 07-18, and 07-20. Confirmed NetAlertX's own Notifications system correctly computed zero new devices in its latest batch — the false alert wasn't coming from NetAlertX's detection logic.

**Root cause (confirmed):** `components/netalertx/netalertx.flow.json`'s old `fn_device_info` node did its own new-device dedup against NetAlertX's raw per-scan MQTT firehose, tracked via Node-RED's in-memory `flow.set('newflag_'+mac, ...)` — which resets on any Node-RED restart. NetAlertX's own `is_new` field stays true until a device is acknowledged/named in its UI, so the first scan after any restart re-fired alerts for every still-unacknowledged device. CARD-0006's Pi reboot restarted Node-RED, directly causing that night's false alerts.

**Fix:** rebuilt the flow to consume NetAlertX's own Notifications webhook (`_publisher_webhook`, calls `NotificationInstance.getNew()` — persistent, SQLite-backed, correctly deduped) instead of re-deriving "is this new" from the firehose. New `POST /netalertx-webhook` endpoint parses `new_devices` from the real notification and composes each log message with the event's actual `eveDateTime` (CLAUDE.md's Event-time convention), not the relay's post time. Added HMAC-SHA256 request signing (`X-Webhook-Signature`) since this is the only inbound HTTP webhook anywhere in JCTsh. Settings configured in NetAlertX (`LOADED_PLUGINS` += `WEBHOOK`, `WEBHOOK_RUN=on_notification` — defaults to `disabled`, easy to miss). Secret in `credentials.local.md` and `/home/pi/.node-red/environment` (`NETALERTX_WEBHOOK_SECRET`, same pattern as `APPS_SCRIPT_KEY`).

**Two real bugs found and fixed during verification, both confirmed via direct testing against a live NetAlertX instance (not assumed):**
1. **Node-RED has no `msg.req.rawBody`** in this version (v4.1.10) — confirmed by reading `21-httpin.js` directly on the Pi. Fixed by enabling the `http in` node's `skipBodyParsing` property, which delivers the untouched body as `msg.payload` (a Buffer) instead of a pre-parsed object.
2. **Genuine upstream bug in NetAlertX v26.7.1's `_publisher_webhook/webhook.py`**: it signs `json.dumps(payload, separators=(',', ':'))` (compact) but transmits `json.dumps(payload)` (Python's default, spaced) — two different byte sequences for the same data, so the signature can never match the actual body. Proved this by capturing a real rejected request, reconstructing the compact form by hand, and reproducing NetAlertX's exact signature. Worked around in Node-RED: parse the body, re-serialize it to match Python's `json.dumps(...,separators=(',', ':'))` output byte-for-byte (including `ensure_ascii=True` escaping of emoji as UTF-16 surrogate-pair `\uXXXX` sequences — validated against real payload data before deploying), and verify against that reconstruction instead of the raw bytes. **Filed upstream 2026-07-23: [netalertx/NetAlertX#1720](https://github.com/netalertx/NetAlertX/issues/1720)** — JCTsh's own workaround doesn't depend on this being fixed, filed for the benefit of other NetAlertX users hitting the same thing.
3. **Third bug, not upstream — mine:** `body.attachments[0].text` isn't a nested object like assumed, it's a JSON-encoded *string* (NetAlertX embeds its Notifications table's `json` column as text, not re-parsed) — needed a second `JSON.parse()` to actually reach `new_devices`. First synthetic tests missed this because they built the payload structure differently than NetAlertX's real code does.

**Verified end-to-end against a real, NetAlertX-originated event** (not just synthetic tests): deleted a device, waited for NetAlertX's own scan to rediscover it and generate a genuine notification, confirmed a real signed webhook POST arrived, was accepted (HTTP 200, confirmed in NetAlertX's own `Plugins_Objects` table), and the correctly-composed message — `"New device detected: Google, Inc. (b0:e4:d5:e0:1f:a2, 192.168.1.143) — connected 7/23/2026, 09:05:40 MST"` — landed on `jctsh/components/netalertx/log` with the right event time.

**Housekeeping:** a few obviously-fake test entries from verification are in the real log (harmless, see CARD-0079). Two currently-generic/unnamed devices (`b0:e4:d5:e0:1f:a2`, `48:d6:d5:8e:1a:6a` — both Google Inc, lost their custom names during test-deletion rounds) will re-acquire sensible names next time they're recognized or can be renamed manually in NetAlertX's UI.

---

### CARD-0006 · [enhancement] [logging] Move log directory to USB stick — RESOLVED 2026-07-22
**Status:** Done

**Notes:** Moved `LOG_DIR` in `log_server.py` from the SD card to a dedicated USB stick plugged into the Pi for better write endurance. Sizing check beforehand found the actual log volume (jctsh.log + state.json) under 1MB after 1.5 months across all 8 heartbeat components — capacity was never the constraint, write endurance was.

**Before formatting the drive:** it was a reused spare, not blank — checked its 19 existing files (an old personal photo archive, 47.5MB) against both Immich libraries by filename (zero matches), then ran the newly-established standard `immich-go upload from-folder` import into Joseph's account per `components/photo-server/operations.md`: 12 genuinely new assets uploaded and tagged, 7 caught as checksum-based duplicates Immich already had under different filenames. Confirmed safe to reuse only after that.

**Resolution:** formatted the drive (`/dev/sda1`, ext4, label `jctsh-logs`), mounted at `/mnt/jctsh-logs` via a UUID-based `/etc/fstab` entry (not a `/dev/sdX` path — avoids the device-letter-shift class of bug CARD-0032 hit on photo-server), migrated the existing log history over, and repointed `LOG_DIR`. **Found and fixed a real gap during deployment:** the `jctsh-logging.service` unit had no `RequiresMountsFor=/mnt/jctsh-logs`, meaning a reboot could race the service ahead of the mount and silently recreate the log directory back on the SD card underneath the mount point — the same class of blind spot as photo-server's Immich bind-mount incident (CARD-0032/CARD-0048). Added the dependency and committed the unit file to the repo (`core/logging/jctsh-logging.service`) since it wasn't tracked before.

**Verified via a real reboot test:** mount came back automatically, service correctly waited for it (state restored from `/mnt/jctsh-logs/state.json`, not recreated fresh), and new log entries flowed normally post-boot (garage-radar, salt-sensor, netalertx all confirmed logging). Stale SD-card copy deleted once the new path was confirmed live.

---

### CARD-0075 · [enhancement] [hiking-monitor] Rename project from hiking-sensor to hiking-monitor throughout — RESOLVED 2026-07-21
**Status:** Done

**Notes:** Raised 2026-07-21. Resolved the folder/prose-vs-device-name mismatch CARD-0009's Reflection step flagged as worth capturing: the real device's firmware had always identified itself as `hiking-monitor` (`esphome: name: hiking-monitor`, confirmed in the real yaml before this rename) and its MQTT username was `hiking-monitor` — but the git repo's folder, several filenames, and most prose throughout the project still said "hiking-sensor" / "hiking sensor." This rename brought the project's own naming into line with what the device had called itself all along.

**Confirmed low-risk, documentation/repo-organization only:** since the device's `esphome:name` was already `hiking-monitor`, this rename did **not** require re-flashing the real field-deployed device or the test rig — no firmware, MQTT identity, or OTA/wake behavior changes. Pure file/folder/text rename.

**Scope (confirmed 2026-07-21):**
1. **Git repo folder:** `components/hiking-sensor/` → `components/hiking-monitor/`, via `git mv` to preserve history.
2. **Filenames within that folder:** `hiking-sensor.yaml` → `hiking-monitor.yaml`, `hiking-sensor-claude-code-instructions.md` → `hiking-monitor-claude-code-instructions.md`, `JCTsh-hiking-sensor-phase1.md` → `JCTsh-hiking-monitor-phase1.md`. (Other files in the folder — `wiring.md`, `testing.md`, `perfboard-layout.md`, the `hiking-monitor-enclosure-*.md` files, etc. — already used the `hiking-monitor` name or were name-agnostic; no rename needed for those, only content review.)
3. **All text references repo-wide:** every occurrence of `hiking-sensor` / `hiking sensor` (39 files found in a 2026-07-21 scan) updated to `hiking-monitor` / `hiking monitor`, including hardcoded paths inside currently-open cards on this board (CARD-0009, CARD-0070, CARD-0067 all referenced `components/hiking-sensor/...` paths, updated to match).
4. **Local ESPHome build directory (outside the git repo):** `C:\esphome\hiking-sensor\` → `C:\esphome\hiking-monitor\` — the real device's separate local working directory, kept in sync with (but distinct from) the repo copy. Included in this card's scope per 2026-07-21 decision, for full consistency.
5. **Build cache handling:** `components/hiking-sensor/.esphome/` (compiled build cache) — confirmed disposable/regenerable per its own `.gitignore` (`/.esphome/` excluded); deleted rather than renamed, since ESPHome regenerates it from the yaml on next compile.

**Sequencing:** done alongside CARD-0070's continued work, which already referenced `components/hiking-sensor/` paths in its own notes — those references were updated in the same pass.

**Execution note (2026-07-21):** the folder rename (`git mv`) initially failed repeatedly with "Permission denied" — root-caused to Windows holding directory-watch handles open on the folder: first PyCharm (open project), then, after closing PyCharm didn't resolve it, two File Explorer windows open on the parent `jctsh` folder (Explorer holds live handles on visible subfolders for icon/thumbnail refresh, a known cause of exactly this symptom). Closing both resolved it. Worth remembering for any future folder rename in this repo while PyCharm or Explorer windows are open on it.

**Resolution:** folder and the three filenames above renamed via `git mv`; every occurrence of `hiking-sensor`/`hiking sensor` in the repo (prose and paths alike) now reads `hiking-monitor`/`hiking monitor` instead; `C:\esphome\hiking-sensor\` renamed to match, including its internal file/comment references; all currently-open cards referencing the old path (CARD-0009, CARD-0070, CARD-0067, CARD-0076) updated to the new path; a repo-wide grep for `hiking-sensor`/`hiking sensor` (case-insensitive) confirmed to return no results outside CARD-0009's own Reflection note describing the origin of the mismatch and its Doc-fix note describing a since-corrected past bug — both accurate history, deliberately kept as-is.

---

### CARD-0073 · [idea] [hike-izer] Hike-izer — narrative summary application layer for hiking data — RESOLVED 2026-07-18
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 16167B, over the 10000B size threshold.

---

### CARD-0034 · [idea] [personal] Complete digital-identity-protection-checklist.md — RESOLVED 2026-07-17
**Status:** Done

**Notes:** Work through `digital-identity-protection-checklist.md` (repo root) — Joseph and Robin's personal security checklist closing single-point-of-failure risks (carrier port-out PIN, 2FA off SMS, credit freezes, password manager, household verification protocol, incident response plan). Almost entirely manual actions by Joseph/Robin themselves (phone calls to carriers/bureaus, account settings changes) — not something Claude Code can execute directly, but worth tracking to completion since it's currently all unchecked. Also has an "Open Items to Fill In" section (list specific banks/brokerages in use, confirm current password manager/2FA setup, set a 6-month review date) that needs input from Joseph before those parts can be finished.

**Blocked (2026-07-11):** waiting on delivery of Google Titan Security Key hardware authenticators (3 ordered) — needed for the hardware-key 2FA portion of the checklist before those items can be checked off.

**Resolution (2026-07-17):** closing as **version 1 done**, not "everything checked off" — the checklist reached v2.1 and the core mission (closing the phone/SIM-swap single point of failure the TIME article exposed) is solidly closed: carrier port-out locks on both lines, Google recovery phone and security question removed, recovery email cross-set between spouses, all 3 Titan keys ordered/registered on Google and RoboForm/PIN-set-and-tested/labeled/backed-up-in-the-safe, Google Account password and 2-Step Verification confirmed hardened with no phone-based fallback remaining, master password memorized redundantly by both Joseph and Robin, 3 of 5 credit bureaus frozen, and the household verbal-verification protocol agreed. Remaining open items (RoboForm Emergency Access + Google Inactive Account Manager, ID document photo cleanup, Robin's app-password/third-party-app review, Google Recovery Contacts, ChexSystems/LexisNexis, walking the checklist through with Robin, Phase 4/5 offline-copy prep) are real but represent the next layer of hardening, not blockers on calling v1 done — split out to CARD-0071 (Emergency Access preparation) and CARD-0072 (Digital Identity Checklist Version 2) rather than holding this card open indefinitely.

**Closed 2026-07-17 — Joseph directed the close.**

---

### CARD-0026 · [enhancement] [hiking-monitor] Measure hiking-monitor sleep-mode current draw — RESOLVED 2026-07-16
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-08-22 (CARD-0193) — 12241B, over the 10000B size threshold.

---

### CARD-0068 · [enhancement] [netalertx] Remove online/offline presence messages from the log — RESOLVED 2026-07-15
**Status:** Done

**Notes:** Raised 2026-07-14, follow-up to CARD-0063. With the translation flow live for a bit, the online/offline presence transition messages (`<device> came online` / `went offline`) turned out to be noisy and not actionable — mobile/known-flappy devices dominate, and even a real device flip doesn't carry enough context (how long, why it matters) to be worth a log line. New-device alerts and the heartbeat are working well and stay. No future use anticipated for presence data elsewhere (NetAlertX's own UI already covers online/offline if ever needed) — clean removal, not a toggle/config flag.

**Scope:** in `components/netalertx/netalertx.flow.json` — remove the `mqtt_in_netalertx_binary` node (`system-sensors/binary_sensor/+/state` subscription) and the `fn_presence` function node entirely. Also remove the `devinfo_<mac>` vendor/model caching in `fn_device_info`, since it only existed to label presence messages that won't exist anymore. New-device alert messages already build their label directly from the per-device sensor payload (`payload.model || payload.vendor`), not from that cache, so no functional change there. Heartbeat and new-device detection otherwise untouched.

**Progress (2026-07-14):** `netalertx.flow.json` updated (11 nodes, `mqtt_in_netalertx_binary` + `fn_presence` + dead `devinfo_<mac>` caching removed), `netalertx-README.md` updated to match, deployed to the live Node-RED instance via the tab-clear-and-reimport procedure. **Leaving open on Joseph's call** — wants to live with it for a few days before confirming the change actually feels right day to day, rather than closing on the first clean deploy. Resume here: check back after a few days that no online/offline messages have reappeared and new-device alerts/heartbeat are still behaving.

**Deploy verification note (2026-07-14):** checked the log dashboard right after deploy and initially saw presence messages at 20:36 (`Front Porch Sensor went offline`, etc.) — looked like the redeploy failed. Confirmed with Joseph there's only one NetAlertX tab, no duplicate flow; the 20:36 batch was actually from the last scan cycle *before* the redeploy, since scan cycles land roughly every 30 minutes and no new cycle had run yet at the time of checking. Real confirmation needs the *next* scan cycle (~21:06) to show no presence messages — not yet observed as of this note. Also surfaced (unrelated, not investigated): a watchdog alert `Component front-porch-temp-sensor silent for 35 minutes` at 20:59.

**Resolution (2026-07-15):** lived with it about a day as planned. No online/offline presence messages have reappeared since the redeploy — confirmed repeatedly, including incidentally during CARD-0069's investigation (which needed to read netalertx's real log history in detail and found only heartbeats and new-device alerts, no presence noise). New-device alerts and heartbeat continued working correctly throughout, including through CARD-0069's own restarts and redeploys of the log server itself. The change holds up in real use, not just on a clean deploy.

**Closed 2026-07-15 — Joseph confirmed and directed the close.**

---

### CARD-0069 · [bug] [logging] log_server.py silently drops heartbeat-only components' messages — RESOLVED 2026-07-15
**Status:** Done

Archived to `core/logging/CLAUDE.md` on 2026-08-22 (CARD-0193) — 9677B, over the 5000B size threshold.

---

### CARD-0060 · [bug] [pi1] Pi running in active soft thermal throttling &mdash; no cooling &mdash; RESOLVED 2026-07-15
**Status:** Done

Archived to `hosts/pi1/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7237B, over the 5000B size threshold.

---

### CARD-0063 · [idea] [netalertx] NetAlertX MQTT event richness experiment + log dashboard wiring — RESOLVED 2026-07-14
**Status:** Done

Archived to `components/netalertx/CLAUDE.md` on 2026-08-22 (CARD-0193) — 11177B, over the 10000B size threshold.

---

### CARD-0064 · [enhancement] [netalertx] Device checking & naming workflow — RESOLVED 2026-07-14
**Status:** Done

Archived to `components/netalertx/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6739B, over the 5000B size threshold.

---

### CARD-0049 · [enhancement] [salt-sensor] Move from breadboard to perfboard — RESOLVED 2026-07-13
**Status:** Done

Archived to `components/salt-sensor/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5696B, over the 5000B size threshold.

---

### CARD-0066 · [enhancement] [photo-server] Verify legacy USB photo archive against Joseph's Immich library — RESOLVED 2026-07-13
**Status:** Done

Archived to `components/photo-server/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5890B, over the 5000B size threshold.

---

### CARD-0065 · [bug] [hiking-monitor] Validate LTR-390 UV Index readings in real sunlight — RESOLVED 2026-07-13
**Status:** Done

**Notes:** Raised 2026-07-13. During post-CARD-0009-rework field testing, UVI read 0 (then 0.01) when the device was taken off dock power into "direct sunshine," raising concern about a wiring fault introduced by CARD-0009's STEMMA QT rework on the LTR-390. Split out as its own card rather than folded into CARD-0009, since that card scopes the enclosure/build work specifically and this is a sensor-correctness question that outlived it.

**Investigation:** ruled out, in order — enclosure/case blocking the sensor (device wasn't in the box), SDA/SCL swap from the STEMMA QT rework (wiring confirmed correct by direct inspection), and a loose STEMMA QT connector. BME280 (shared I2C bus) read normally throughout, narrowing any real fault to the LTR-390 itself. Sensor pointed straight at the sun and left to complete a full `update_interval: 2min` cycle — UVI climbed to **6.90**, a plausible value for clear midday sun. No hardware fault; the earlier near-zero readings were just pre-settle values from before the sensor had a clean, unobstructed, correctly-oriented exposure.

**Side finding:** the 5-minute heartbeat log message (`jctsh/components/hiking-monitor/log`) only reported uptime/RSSI/temp/battery — humidity, pressure, and UV index were invisible on the dashboard, which is why this diagnosis required reading the physical OLED instead of checking remotely. Expanded the heartbeat lambda in `hiking-monitor.yaml` to include all five BME280/LTR-390 readings (temp, humidity, pressure, UVI) plus battery, each NaN-safe.

**Resolution:** config validated clean (`esphome config`), OTA-reflashed successfully — device back online at 09:32:41 (`Online — ESPHome 2026.4.5, IP: 192.168.1.161, MQTT connected`). First post-reflash heartbeat (09:37:18) confirmed live on the dashboard: `Heartbeat - uptime: 0h 5m, RSSI: -59dBm, temp: 99.9°F, humidity: 32.7%, pressure: 931.7hPa, UVI: 6.92, batt: 4.00V` — all readings present, UVI holding steady near the earlier 6.90 reading.

**Closed 2026-07-13 — Joseph confirmed the new heartbeat message showed up on the log.**

---

### CARD-0003 · [enhancement] [mqtt] TLS for Mosquitto (port 8883) — RESOLVED 2026-07-13
**Status:** Done

Archived to `core/mqtt/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7374B, over the 5000B size threshold.

---

### CARD-0061 · [enhancement] [infrastructure] Add Docker health check for the Pi's Home Assistant container &mdash; RESOLVED 2026-07-12
**Status:** Done

**Notes:** Found 2026-07-12 during a Pi health evaluation. The `homeassistant` Docker container had no configured `HEALTHCHECK` &mdash; `docker ps`/`docker inspect` only reflected process liveness, not actual HA responsiveness. Same class of blind spot already found and fixed on photo-server (CARD-0032/CARD-0046: Docker's own health check only pings the API, doesn't verify real functionality) &mdash; HA is arguably the single most critical container on the Pi, since it's the sole bridge to SmartThings/Google Home for the whole house.

**Resolution:** added a `healthcheck` block to `core/homeassistant/docker-compose.yml`: `curl -f http://localhost:8123/manifest.json` (lightweight, unauthenticated, confirmed working) every 60s, 10s timeout, 3 retries, 90s start period to cover HA's own boot time. Deployed to the Pi (`/home/pi/docker-compose.yml`) and recreated the container &mdash; the existing `homeassistant` container predated this compose project (no compose labels), so it had to be stopped and removed before `docker compose up -d` would take over management of it; HA's actual config lives in the bind-mounted `/home/pi/homeassistant` volume, not the container, so nothing was lost.

**Live-tested 2026-07-12** using the same deliberately-break-it discipline as CARD-0029/CARD-0032/CARD-0046: confirmed `(healthy)` immediately after recreation, then froze HA's actual process inside the container (`kill -STOP` on the main `python3 -m homeassistant` PID &mdash; a genuine hang, not a container-level action, since that's exactly the failure mode this card exists to catch) and waited for the check to notice. Docker correctly flagged `unhealthy` with `FailingStreak: 3` after three consecutive failed checks. Resumed the process (`kill -CONT`); Docker correctly returned to `(healthy)`. Full Docker-level cycle (healthy &rarr; unhealthy on real hang &rarr; healthy again) verified end to end.

**Dashboard-visibility gap found and closed (2026-07-12):** the Docker-level fix alone only fixed `docker ps`/`docker inspect` locally on the Pi &mdash; it did not surface anything on the JCTsh log dashboard, unlike the photo-server pattern this card was modeled on, which pairs a health check with a heartbeat script that publishes the result to MQTT. Built `core/homeassistant/pi-heartbeat.py`, checking `docker inspect homeassistant`'s health status and publishing to the existing `jctsh/core/log-server/log` topic under the `jctsh-core` component identity (same identity/topic/credentials already used by the Pi's boot/reboot notifications &mdash; `/etc/jctsh/log-server.env`, reused rather than a new dedicated MQTT account, since this is the same host's own infrastructure). Deployed via `core/maintenance/pi-heartbeat.service`/`.timer` (30 min, matching the fleet-wide heartbeat cadence). Hit one real bug during first deploy: initially built the topic from the component variable (`jctsh/core/jctsh-core/log`) instead of the fixed `jctsh/core/log-server/log` topic the log server actually expects &mdash; component name and topic segment are decoupled in this convention and are easy to conflate; fixed and redeployed.

**End-to-end live-tested 2026-07-12:** repeated the freeze/resume test with the heartbeat script run manually at each stage, confirmed via the dashboard's actual `/data` endpoint (not the flushed-only `/log` text file, which delayed visibility of the healthy-state message inside an unflushed collapse group during testing and briefly looked like a bug before being traced to normal flush-timing behavior, not a real defect) &mdash; healthy (`System`, `Heartbeat - Docker containers healthy.`) &rarr; unhealthy (`Alert`, `Docker degraded - homeassistant:unhealthy`, visible immediately since Alert messages don't collapse) &rarr; healthy again, all three states confirmed present and correctly categorized on the live dashboard.

---

### CARD-0062 · [enhancement] [infrastructure] Switch Pi to headless boot &mdash; drop the desktop GUI &mdash; RESOLVED 2026-07-12
**Status:** Done

**Notes:** Found 2026-07-12 during a Pi health evaluation. The Pi boots into `graphical.target` with a full desktop session running (`pcmanfm --desktop`, `wf-panel-pi`) even though normal access is SSH-only &mdash; Joseph used the physical desktop once, during initial setup, never since. On a Pi 3B+ with only ~905MB RAM already under real pressure (zram swap sitting at ~50% used while running HA, Node-RED, Mosquitto, the log server, Tailscale, and fail2ban concurrently), this was pure reclaimable overhead.

**Pre-check:** confirmed no VNC/RealVNC/xrdp service configured, and `/etc/xdg/autostart/` + `~/.config/autostart/` contained only standard desktop-session plumbing (polkit agents, on-screen keyboard, compositor) &mdash; nothing load-bearing for SSH-only use.

**Resolution:** `sudo systemctl set-default multi-user.target`, rebooted. Confirmed `systemctl get-default` returns `multi-user.target` and no desktop processes (`pcmanfm`/`wf-panel-pi`) run anymore. SSH access, Docker/HA (HTTP 200 on `:8123`), Mosquitto, Node-RED, and jctsh-logging all confirmed active post-reboot.

**Before/after (steady 4-day uptime vs. 6 minutes post-reboot):** swap usage dropped from 449Mi (~50% of swap) to 148Mi (~16%) &mdash; the clearest signal, since raw "used" memory is a noisy comparison this early (buff/cache hadn't rebuilt yet). The desktop's ~225MB of GTK/panel/session overhead is now structurally absent rather than merely idle. Fully reversible via `systemctl set-default graphical.target` + reboot if ever needed.

---

### CARD-0059 · [idea] [infrastructure] NetAlertX — self-hosted LAN device tracker with custom naming — RESOLVED 2026-07-12
**Status:** Done

**Notes:** Raised 2026-07-12. Motivated by the router (TP-Link Archer AXE75) listing most connected devices with meaningless names, with no built-in way to rename them — the JCTsh-managed fleet already has this solved via DHCP reservations + `jctsh-network.md`'s device table + ESPHome hostnames, but third-party/commercial devices (Ring, Ecobee, Cast devices, guest phones) aren't part of that convention and the router won't let their names be overridden.

**What it is:** NetAlertX (formerly Pi.Alert) — open-source, self-hosted LAN device scanner and presence tracker. Maintains its own device database independent of the router, so naming lives there regardless of what the router shows.

**How it works:** periodic ARP scanning (plus optional plugins — mDNS, SNMP against the router, DHCP lease-file parsing, nmap) discovers devices; each MAC gets a persistent record (first-seen, last-seen, IP history, OUI-based vendor guess) in its own SQLite DB. A web dashboard lets you assign a friendly name/icon/group to each MAC once, permanently — independent of router support. Also flags brand-new unknown devices joining the network (security-relevant) and always-on devices going silent, with notifications via MQTT, webhooks, email, Pushover/Telegram/ntfy/Apprise.

**Planning (2026-07-12) — host decision reversed on real data:** initially figured the Pi as the natural fit (LAN hub, classic Pi.Alert project) and Joseph agreed — but checking the Pi directly first (good thing) found it's a Raspberry Pi 3 B+ already under real memory pressure: 34MB free, 315MB available, swap at 462MB/904MB (51%) — already running Docker for Home Assistant itself, plus Mosquitto, Node-RED, and `log_server.py` natively, all things other devices actively depend on (MQTT broker, automations). Adding periodic ARP/nmap scanning there risked contending for the little headroom left. Checked the M8 instead: 12 cores, 9.2GB available RAM, swap barely touched (109MB/4GB), Docker already running Immich's 4 containers cleanly. Switched the plan to the M8. No VLAN segmentation on this network (confirmed during CARD-0050), so the M8 sees the same broadcast domain the Pi would — no ARP-visibility loss from the switch. Skipped a separate Design phase — this checked-before-deciding pass is the plan; went straight to Build.

**Build (2026-07-12):** MQTT account (`netalertx`) created on the Pi's Mosquitto broker, recorded in `credentials.local.md`, verified working. `components/netalertx/docker-compose.yml` deployed to `~/netalertx-app` on the M8 (its own compose project, alongside but separate from `~/immich-app`).

Two real deploy bugs found and fixed: (1) my first compose file was based on a lossy AI-summarized version of the upstream reference, missing `read_only: true` and the specific `cap_drop`/`cap_add` set the entrypoint's own self-check requires — container crash-looped (exit 126) until fetched and matched the literal upstream file. (2) the upstream file's ARP-flux-mitigation `sysctls:` block isn't allowed by Docker under `network_mode: host` (`runc create failed: sysctl ... not allowed in host network namespace`) — removed from compose; the real fix is setting those two sysctls on the M8's host kernel directly, which needs interactive `sudo` (deferred — `jct@photo-server.local`'s sudo requires an interactive password, unlike the Pi's account; captured as a follow-up, not blocking).

**Resolution:** container deployed, healthy, zero restarts, image `ghcr.io/netalertx/netalertx:latest`. Login secured (Settings → System → Set Password, credential in `credentials.local.md` — default install ships with auth disabled entirely, closed that gap). Joseph completed the manual first-run setup and confirmed the naming workflow. MQTT/log-dashboard integration deliberately deferred, not because it's blocked but because it needs its own experiment first — split out to CARD-0063 rather than holding this card open for it.

**Closed 2026-07-12 — Joseph confirmed and directed the close.**

---

### CARD-0057 · [enhancement] [logging] Serve the kanban board as a live-parsing Pi page — RESOLVED 2026-07-11
**Status:** Done

Archived to `core/logging/CLAUDE.md` on 2026-08-22 (CARD-0193) — 8240B, over the 5000B size threshold.

---

### CARD-0004 · [enhancement] [salt-sensor] Migrate Arduino C++ → ESPHome — RESOLVED 2026-07-11
**Status:** Done

**Resolution:** `salt-sensor.yaml` written and compiles clean (RAM 13.2%, Flash 52.3%). Direct translation of the Arduino sketch — same 15-sample-median 12h reading cycle, same MQTT topics/payloads (`jctsh/sensors/salt-sensor/data`, `/status`, `/log`), same LED state machine (GPIO2/15/4, unchanged pins), same thresholds (still owned entirely by Node-RED — flow untouched). Added a 30-min heartbeat (`.../heartbeat`) that didn't exist before, closing the gap CARD-0021 flagged (salt-sensor showing `?` on the status dashboard). `secrets.yaml` created from `secrets.h`'s values; old v3 Arduino sketch archived to `archive/salt-sensor-v3-arduino/`; `C:\esphome\salt-sensor\` flash path set up matching the other ESPHome components.

**Two real compile bugs found and fixed during translation** (both are ESPHome `globals:` gotchas, not obvious from the docs): a fixed-size C array global (`float[15]`) fails to compile (`GlobalsComponent` can't take an array by value — decays to a pointer); switched to `std::vector<float>`. Its `initial_value: '{}'` was then ambiguous between two constructor overloads; fixed with an explicit `std::vector<float>()` initializer.

**One design decision worth flagging:** ESPHome's default MQTT birth topic is `<topic_prefix>/status`, which would have silently collided with this component's existing `.../status` topic (Node-RED → ESP32, drives the LEDs). `birth_message:` is explicitly disabled in the yaml to prevent this — a real footgun for any future component whose topic convention includes `/status`.

**Field verification (2026-07-10):** USB-flashed and confirmed end to end — LED self-test visible on boot, `/data` publishes a real retained reading, `/status` round-trips correctly from Node-RED and drives the LEDs (`ok` → solid green, confirmed visually), `/log` messages flowing to the dashboard. See CARD-0049 for the follow-on LED pin move (GPIO2/15/4 → GPIO32/33/27), also verified working over OTA.

**Heartbeat confirmed (2026-07-10 13:06 MST):** first natural 30-min heartbeat landed — `Heartbeat - uptime: 0h 30m, RSSI: -50dBm, status: ok`. Watchdog wildcard pickup confirmed.

**Removed the `Status: X -> Y` log line (2026-07-10):** the `on_message` handler used to log every status transition to `.../log`, but review found it added no real value — Node-RED's own `fn_threshold` logging (`[Sensor] Salt: X% (Y cm)`, `CRITICAL — salt at X%...`) already covers the meaningful transitions in plain language, and the ESP32-side log was actively misleading: dashboard history showed `unknown -> offline` / `offline -> ok` entries that never came from Node-RED (confirmed — `offline` doesn't appear anywhere in `salt-sensor.flow.json`). Root cause: a fossil from early migration testing, before `birth_message:` was disabled — ESPHome's default birth/will strings (`online`/`offline`) briefly collided with this same `/status` topic. Not reproducible under current firmware, but the confusion it already caused wasn't worth the code. Removed `prev_status`/`status_changed` globals along with it; `current_status` still drives the LEDs, just silently.

**12h natural reading cycle confirmed (2026-07-11):** the last open verification item — the 15-sample-median 12h reading firing on its own timer, not just via the on-connect immediate-reading code path — is now confirmed. Two standalone readings (no adjacent MQTT connected/disconnected/online event, unlike every on-connect-triggered reading in the log) landed exactly 12 hours apart: `2026-07-11 01:17:37 MST — Salt: 98% (20.9 cm)` and `2026-07-11 13:17:37 MST — Salt: 95% (21.5 cm)`. Periodicity confirmed via the dashboard log (`http://192.168.1.117/log`), closing the card's last open condition.

---

### CARD-0056 · [enhancement] [kanban-board] Persistent visual kanban board — RESOLVED 2026-07-11
**Status:** Done

**Notes:** Raised 2026-07-11: every time the board gets summarized in chat, it comes out in a different ad hoc format and scrolls out of view while working, with no stable place to return to it. Agreed approach: a browser-hosted Artifact with a persistent URL, redeployed to the same link whenever `kanban-board.md` changes, rather than a fresh chat message each time.

Built as a single self-contained HTML page (no external requests, per the Artifact sandbox) — a blueprint-styled board with one column per kanban state (Backlog, Planning, Design, Build, Done, Defer), each independently scrollable and collapsible, card tiles that expand in place for full notes, a live text search across id/title/tag/notes, and type filter chips (bug/enhancement/idea). Card data is baked into the page at build time as a JSON blob, not read live from the repo — so it goes stale exactly the way any snapshot does, and needs a manual regenerate-and-republish pass after edits, same discipline as keeping any other doc in sync.

`backlog.md` was renamed to `kanban-board.md` in this same session (2026-07-11), with references updated across README.md, CLAUDE.md, JCTsh-Operating-System.md, and the photo-server docs that pointed to it by name.

**Live-parsing alternative considered, not pursued (2026-07-11):** discussed serving the board from the Pi's existing `log_server.py` with a route that parses `kanban-board.md` live on each request instead of reading baked-in JSON, which would remove the manual-regenerate step entirely. Real cost surfaced in the same discussion: the repo isn't cloned on the Pi (deploys there are one-off `scp`, per `SOFTWARE-ENVIRONMENT.md`), so `kanban-board.md` would still need to be pushed to the Pi on every edit — the live-parsing win only fully lands once that push is also automated. Decision: stick with the manual artifact-regenerate workflow for now and see how the discipline holds up in practice; revisit the Pi version if manual regeneration turns out to be too easy to forget.

**Resolution:** page published and confirmed viewable at a stable claude.ai URL. Regenerate-after-edit discipline exercised twice already (title/collapse-default fix, then a CARD-0056 text sync) and explicitly agreed to as the ongoing approach. Closed 2026-07-11 — Joseph confirmed sticking with this version and directed the commit.

---

### CARD-0052 · [idea] [infrastructure] JCTsh Team Operating System (TOS) — RESOLVED 2026-07-11
**Status:** Done

**Notes:** Defines how the team works — the conceptual process governing all work, independent of any single component. Written up 2026-07-11 at Joseph's direction after a series of card/backlog/commit/push questions surfaced that this process was implicit (living in `backlog.md`'s column definitions and the user's global CLAUDE.md workflow notes) but never stated as its own document.

**Resolution:** `JCTsh-Operating-System.md` (repo root, v1.0 — this card's full output *is* version 1 of the doc) defines:
- All work tracked as a card on the kanban board; columns are synonyms for states, representing a process of state transitions with explicit triggers (Backlog → Planning → Design → Build → Done, plus Defer reachable from any state).
- **Where Work Happens:** Claude chat is informal, pre-card thinking only — no planning documents, no board state. The decision to build something is the trigger to move to Claude Code, create the card, and file it in Backlog; Claude Code handles Planning through Done from there in one continuous process.
- **Planning** may be a single document or multiple sequential phases/documents depending on the work (per `JCTsh-Component-Planning-Pattern.md`'s Phases 1–3 for hardware/software builds).
- **Build** includes per-step manual work/confirmation by Joseph wherever required, not just Claude Code executing alone, and a required closing **Reflection** step — capturing what was learned so it doesn't get relearned by trial and error later.
- **Deliverables per state** identified: Backlog → the card itself; Planning → planning document(s); Design → the design doc/Claude Code instructions; Build → the implementation + verification evidence + reflection artifact; Done → the Resolution note; Defer → the Decision note.
- **Commit/Push:** the card, not `git add`, is the organizing concept. A commit is the action that enacts the Build → Done transition (requires Build's criteria satisfied first, typically bundles the card's Done-move into the same atomic commit); push is release-level, separate and always confirmed.
- **Applying TOS to Pre-Existing Work:** cards predating this doc that don't cleanly match a column aren't inconsistencies to fix — reconciling any specific one is a per-card judgment call, not a retroactive mandate.

Cross-checked against `JCTsh-Component-Planning-Pattern.md` (CPP) during development — found and fixed a real inconsistency (CPP still assigned Phases 1–4 to "Claude chat," contradicting the Where-Work-Happens model above) and realigned CPP to match (bumped to v2.4: Phases 1–5 now all happen in Claude Code, chat limited to pre-card Phase 0 thinking).

**Closed 2026-07-11 — Joseph reviewed and directed every addition across the drafting conversation and confirmed readiness to commit**, satisfying the original close condition.

---

### CARD-0043 · [bug] [photo-server] Robin's library missing metadata (null width/height/orientation) for large fraction of assets — RESOLVED 2026-07-10
**Status:** Done

**Notes:** Discovered 2026-07-09 following up on CARD-0042 — Joseph reported a specific HEIC photo (`IMG_20260625_165423.heic`, Robin's account) with a fine-looking thumbnail but a visibly distorted full image (elongated heads). Checked the asset directly via `/api/assets/{id}`: `width`, `height`, `exifImageWidth`, `exifImageHeight`, and `orientation` all `null` — Immich never successfully extracted this file's real dimensions/orientation, which plausibly explains the distortion (wrong aspect-ratio assumption during preview rendering). Sampled 100 assets per account: **Joseph 0/100 null width; Robin 89/100 (89%)** — same lopsided pattern as CARD-0037/CARD-0039/CARD-0042, again far worse for Robin despite her "clean" import history.

Triggered `metadataExtraction` via `PUT /api/jobs/metadataExtraction` (`{"command":"start"}`) — unlike CARD-0042's thumbnail gap, this one *is* partially caught by the normal queue trigger: 13,311 assets queued immediately. However this is likely not the full picture — some assets (like the specific HEIC file that started this) may be marked "complete" in the database despite holding null values, the same DB-vs-reality mismatch pattern as CARD-0042, which would need the same forced per-asset fix (`refresh-metadata`, another valid job name on the same `/api/assets/jobs` endpoint used for CARD-0042's `regenerate-thumbnail`).

**Paused here by design (2026-07-09):** M8 load hit 12.64/12 cores with CARD-0030's backup, CARD-0042's thumbnail regen, and this metadata extraction all running concurrently — Immich API was still responsive (45ms ping) so nothing was failing, but Joseph asked to let the current jobs finish before adding a full forced `refresh-metadata` sweep across Robin's ~77,123 assets. The 13,311 already queued will keep processing in the background regardless.

**Closed 2026-07-10 — all four conditions verified live:** (1) `metadataExtraction` queue confirmed fully drained via `GET /api/jobs` (0 waiting/active/failed); (2) a fresh 150-asset sample of Robin's library showed 0/150 null width (top-level `width` field — the list endpoint doesn't return `exifInfo` inline, this superseded the original per-asset `exifImageWidth` check method but confirms the same thing); (3) `IMG_20260625_165423.heic` re-checked directly: `exifImageWidth 4032`, `exifImageHeight 3024`, `orientation 1` — all populated, no longer null; (4) Robin's null-width rate (0%) now matches Joseph's baseline (0%).

---

### CARD-0042 · [bug] [photo-server] Robin's library missing thumbnails for ~81% of assets — RESOLVED 2026-07-10
**Status:** Done

**Notes:** Discovered 2026-07-09 while troubleshooting Robin's phone backup — Joseph noticed "Error Loading Image" on several thumbnails, both in the phone's local gallery view and (critically) in the web UI too, which ruled out a phone-side rendering glitch. Diagnosed via direct HTTP checks against `/api/assets/{id}/thumbnail`: a 150-asset sample came back 122/150 (81%) returning `404` for Robin, versus **0/150** for Joseph — confirmed real, server-side, and isolated to Robin's account. Root cause not pinned down (her import was the "clean" one per `migration.md`, yet has by far the worse thumbnail gap — consistent with the same pattern already seen in CARD-0037/CARD-0039 where Robin's account had the larger gap despite the cleaner import history). The standard `thumbnailGeneration` job queue didn't surface these (`waiting: 1` when triggered normally) because Immich's database already considered them complete — the gap is between DB state and actual thumbnail files on disk, not a "job never ran" situation like CARD-0037.

**Fix:** used the per-asset job endpoint (`POST /api/assets/jobs`, `{"name":"regenerate-thumbnail","assetIds":[...]}` — found via the same schema-discovery trick as CARD-0037/CARD-0039, sending an invalid body and reading the validation error's allowed values) to force-regenerate every one of Robin's 77,123 assets in 155 batches of 500. Confirmed working on a small scale first (9 known-broken assets, all fixed, verified via HTTP 200) before committing to the full-library run. Submitted successfully in full — `thumbnailGeneration` queue confirmed at 76,996 waiting immediately after. Verified live at every step (new photo from Robin's phone arrived with a working thumbnail, confirming upload itself was never broken — only historical thumbnails were affected).

Running concurrently with CARD-0030's backup verification and the tail end of CARD-0037/039's work; checked M8 load before committing to the bulk job (5.04/12 cores, comfortable).

**Closed 2026-07-10:** `thumbnailGeneration` queue confirmed fully drained (0 waiting/active/failed). Fresh 150-asset sample of Robin's library: 140/140 image/photo assets returned `200` on thumbnail (0% broken, matching Joseph's baseline). The sample also included 10 `.MP.mp4` assets (Pixel Motion Photo video sidecars) that returned `404` — investigated and confirmed **not a regression**: these are `visibility: hidden` linked video components, never meant to be fetched directly (the paired still-image asset each links to via `livePhotoVideoId` has its own working `200` thumbnail, which is what actually displays in the gallery/timeline). This is normal Immich behavior for motion photos, not the bug this card tracked.

---

### CARD-0051 · [enhancement] [photo-server] Extend heartbeat with disk-capacity and backup-staleness checks
**Status:** Done

**Notes:** Found 2026-07-11 during a health check + log-dashboard history review. CARD-0032/CARD-0046 made the heartbeat check that storage is *readable/writable*, but two real gaps remained:
1. **Disk capacity** — nothing checked how *full* a mount was. A drive filling up (primary or either backup) would degrade Immich or fail backups with no advance warning.
2. **Backup staleness** — CARD-0040 made `photo-library-backup.sh` report its own per-run success/failure, but nothing watched for the run simply not happening at all (cron broken, script missing, host down over a scheduled run) — an absence-of-signal gap the per-run report can't cover.

**Resolution:** `photo-server-heartbeat.py` now checks `shutil.disk_usage()` on all three mounts (`/mnt/photo-library`, `/mnt/photo-library-backup`, `/mnt/photo-library-backup-joseph`) every 30-min cycle, flagging degraded via the existing `unhealthy`/Alert path if any exceeds 90% used. `photo-library-backup.sh` now touches `/home/jct/photo-library-backup-success.stamp` only on the fully-successful path (both rsync jobs exit 0); the heartbeat script checks that marker's age and flags degraded if missing or older than 9 days (one missed weekly Sunday 2am run + 2-day grace). Both reuse the existing `unhealthy` list / dashboard Alert / `status: degraded` payload — no new MQTT topics or schema.

**Live-tested 2026-07-11:** staleness check fired correctly (`backup:stale (no successful run recorded)`) immediately after deploy since no stamp existed yet — confirmed on the dashboard. Capacity check verified by temporarily dropping the live deployed threshold to 1% and confirming all three mounts correctly reported (`primary-capacity:68% used, backup-robin-capacity:35% used, …`), then restored to 90% and diffed byte-for-byte against the repo version. Ran the real `photo-library-backup.sh` end-to-end (not a simulated success) — both rsync legs completed, stamp file written, and a final heartbeat run confirmed `status=online` with no unhealthy items, leaving the live system in a genuinely healthy state post-test.

---

### CARD-0046 · [enhancement] [photo-server] Extend storage-health check to cover backup drive(s), not just primary
**Status:** Done

**Resolution:** `photo-server-heartbeat.py`'s storage check now also writes/reads/removes a marker file directly on both backup mounts (`/mnt/photo-library-backup`, `/mnt/photo-library-backup-joseph`) every 30-minute cycle — plain host-level file I/O, not `docker exec`, since these mounts aren't inside any container (Immich itself never touches them, only the standalone backup script does). Failures reported as `backup-robin:<error>` / `backup-joseph:<error>` in the same non-collapsing `Alert` path already used for the primary library and container checks.

**Live-tested 2026-07-10** using the same safe `mount -o remount,ro` technique as the original CARD-0032 test, applied to each backup drive in turn: both correctly triggered `Immich degraded - backup-<name>:[Errno 30] Read-only file system` on the dashboard, and both recovered cleanly to normal status after `mount -o remount,rw`. Closes the exact visibility gap that let Momentus's real hardware failure go undetected for over 2 hours earlier the same day. Full detail in `components/photo-server/heartbeat.md`.

---

### CARD-0040 · [enhancement] [photo-server] Dashboard visibility for backup runs
**Status:** Done

**Resolution:** `photo-library-backup.sh` publishes MQTT log messages so backup success/failure is visible on the JCTsh log dashboard without SSHing in — `"Backup starting."` before either rsync job, `"Backup complete."` (category `System`) if both succeed, or `"Backup failed (joseph exit <code>, robin exit <code>)."` (category `Alert`, non-collapsing) if either fails. Same pattern as CARD-0036's reboot notifications, reusing the existing `photo-server` MQTT account.

**Both paths confirmed live 2026-07-10.** The failure path fired correctly earlier in the day when both rsync jobs were killed mid-run while debugging CARD-0030 (`"Backup failed (joseph exit 20, robin exit 11)."` — exit 20 being rsync's SIGTERM code). Once CARD-0030's `--delete-before --delete-excluded` fix was in place and both accounts were already fully synced, ran the actual script end-to-end (not manual isolated rsync calls) to verify the success path: `"Backup starting."` at launch, both jobs completed with zero errors, `"Backup complete."` at the end.

---

### CARD-0030 · [bug] [photo-server] Re-enable weekly backup cron once Takeout zips are cleared
**Status:** Done

**Resolution:** Zips deleted 2026-07-09 (818GB reclaimed), cron re-enabled. The manual verification run then failed overnight — `No space left on device` — revealing the primary library (624GB) had genuinely outgrown Momentus (586GB usable), not just a slow first run as assumed.

**Fix: split backup by account across two drives.** Deployed a second backup drive (Seagate 1TB, formatted, mounted at `/mnt/photo-library-backup-joseph`) and rewrote `photo-library-backup.sh` to run two UUID-filtered `rsync` jobs — Joseph's account to the new drive, Robin's to Momentus. Getting this working cleanly took two more rsync flag fixes: `--delete-before` (plain `--delete` defaults to `--delete-during`, which deletes incrementally by directory-walk order — the shared `backups/` dir gets walked before the per-user dirs where the actual space-freeing deletions live, causing a chicken-and-egg failure on an already-full destination) and `--delete-excluded` (none of rsync's `--delete*` variants touch files matched by `--exclude` by default — a protective rsync behavior that meant Joseph's excluded files were never actually being removed from Momentus across two earlier attempts).

**Final verified state (2026-07-10):** both jobs completed with zero errors — Robin's Momentus job dropped from 556G to 207G (matching her ~187GB actual usage), Joseph's new-drive job landed at 420G (matching his ~403GB usage). Full incident writeup in `components/photo-server/backup.md` and `DEVLOG.md`.

**Still open, tracked separately:** CARD-0040 (dashboard visibility not yet verified through a full end-to-end script run — both jobs above were run manually/isolated while debugging) and CARD-0046 (backup drives still have no continuous storage-health monitoring, unlike the primary library).

---

### CARD-0048 · [bug] [photo-server] Stale Immich container bind mount after drive remounts — "Error loading image" on both accounts
**Status:** Done

**Resolution:** Discovered 2026-07-10 when Joseph reported "beaucoup" thumbnail and full-image load failures on his account, then confirmed Robin had the same issue. Initial theory (I/O contention from the actively-running backup rsync) was wrong — killing the backup didn't fix anything. Root cause: the `immich_server` container's bind mount had gone stale after the day's repeated remounting (read-only, I/O errors, primary library's device path changing `sda`→`sdd`). Confirmed via a specific 404ing asset: the file was genuinely present on disk with correct content, ruling out real data loss — the container just had a broken cached view of the mount. The storage-health check (CARD-0032) had actually been correctly alerting on this the whole time (recurring `Input/output error` every 30-minute cycle for 2+ hours) — the miss was diagnostic, not detection; time was spent chasing the wrong theory first.

**Fix:** `docker compose restart` (all four containers) from `~/immich-app`. Verified immediately: every previously-404ing asset (thumbnail and original) on both accounts returned to `200`. Also confirmed by Joseph directly in the Immich web UI on both accounts.

Runbook note added to `components/photo-server/heartbeat.md`: if storage alerts recur across multiple heartbeat cycles (not just once), especially after any drive remount/unplug/replug event, check the container's actual data access first — a clean host-side mount does not guarantee the running container is looking at it correctly.

---

### CARD-0047 · [enhancement] [photo-server] Daily Immich update-availability check with dashboard notification
**Status:** Done

**Resolution:** Joseph noticed an Immich update available in the web UI and asked how to manage updates going forward — discussed and agreed on notify-only (not auto-update), given this instance has already surfaced real bugs in a single patch version this week (CARD-0037/0042/0043, the HEIC distortion issue) and the data at stake (irreplaceable family photos) doesn't justify unattended auto-updates.

Built `immich-update-check.py` (deployed to `/usr/local/bin/`) + `immich-update-check.service`/`.timer` (daily, 6:00 AM `America/Phoenix`), following the same MQTT dashboard-notification pattern as CARD-0036/CARD-0040: compares `/api/server/version` against `/api/server/version-check`, publishes `"Immich update available: <latest> (currently running <current>)"` (component `photo-server`, category `System`) when they differ. De-duplicated via a state file so the same pending update doesn't re-notify daily — only fires again if an even newer version appears after the first notice.

First deploy attempt crashed on the state-file write (`/etc/jctsh/` isn't writable by the `jct` user, appropriately, since it holds credentials) — moved the state file to `/home/jct/.jctsh/` and added `os.makedirs`. Verified live 2026-07-10: first corrected run notified correctly (`v3.0.2` vs. running `v3.0.1`), confirmed on the dashboard; second run correctly skipped re-notifying for the same version. Added to `jctsh-network.md`'s Scheduled Maintenance Windows table (6:00 AM daily, no conflicts with existing jobs). Actual update application remains a deliberate manual step, not automated.

---

### CARD-0022 · [enhancement] [infrastructure] Security hardening — infrastructure audit (Steps 1–8)
**Status:** Done

**Resolution:** All 8 steps complete. Steps 1–5 and 8 passed clean or were fixed on 2026-06-20 (SSH key-only auth, MQTT auth, port audit, Node-RED adminAuth). Step 7 (HA MFA) done 2026-07-09: TOTP enabled for both Joseph and Robin via HA profile → Multi-Factor Authentication Modules. Step 6 (router UPnP) done 2026-07-09: found enabled with zero registered clients, disabled with no functional impact. Full findings in `jctsh-security-hardening.md`. Patterns harvested to `JCTsh-Build-Standards.md` §10 Security Standards (v1.14).

---

### CARD-0023 · [enhancement] [infrastructure] Security hardening — cloud accounts (Steps 9–14 + Final)
**Status:** Done

**Resolution:** All steps complete. Steps 9–12 and 14 passed clean 2026-06-20 (Ring/Amazon, SmartThings, Google ×2, Windows machine — one stale SmartThings connected app, SharpTools, revoked). Step 13 done 2026-07-09: router admin password rotated to a new strong unique password (`credentials.local.md`), remote/WAN management confirmed disabled, DNS confirmed intentional (CenturyLink/Quantum Fiber bypass-modem setup), firmware found one version behind (1.5.2 → 1.5.3 available) with auto-update now enabled (nightly 3–5 AM) rather than relying on manual checks going forward. Final Step complete: findings harvested to `JCTsh-Build-Standards.md` §10 Security Standards (v1.14).

---

### CARD-0039 · [bug] [photo-server] Re-verify Takeout import completeness — 3,433 assets were genuinely missing
**Status:** Done

**Resolution:** Following up on the original migration verification discussion, and given CARD-0037 had just found a large ML-processing gap from the same import, re-ran `immich-go upload from-google-photos` (real run, not `--dry-run`, so gaps found would get fixed immediately) against all retained Takeout zips for both accounts — `/mnt/photo-library-backup/takeout-staging/joseph/` (9 zips), `/home/jct/takeout-staging/joseph/` (3 zips), `/home/jct/takeout-staging/robin/` (5 zips). Used the same `--on-errors continue --pause-immich-jobs=false` flags that fixed the original migration's crash patterns, plus `--no-ui --log-file=...` this time for a persisted per-pass log (a gap in the original run). Launched fully detached via `nohup ... & disown` directly on the M8 so it survived independent of the SSH session — relevant since the home internet/network was intermittently down around this time.

**Result:** ran clean in a single pass, no restarts needed, zero upload errors. Found **3,433 assets that were genuinely missing** from Immich and uploaded them (zero data loss risk — upload-only, nothing deleted): 58 (Joseph, backup-drive zips), 119 (Joseph, NVMe-staged zips), 3,256 (Robin). Also found 109 cases where the server's copy was upgraded (better-quality version found in the zip) and 160,701 correctly-matching duplicates confirmed (skipped, no re-upload).

**Notable finding:** Robin's pass had by far the largest gap (3,256 missing) despite her original import being documented as the "clean" one with no crashes/restarts (see `components/photo-server/migration.md`) — this means the missing-asset gap was not caused solely by Joseph's chaotic 5-restart import as originally assumed. Combined with CARD-0037's finding that Robin's ML-processing gap was also worse than Joseph's (96% vs ~80% zero-face rate), there's a consistent pattern that something affected both imports similarly regardless of which one crashed — most likely some shared infrastructure/timing factor from both multi-day imports running through the same M8 around the same period. Root cause not further investigated since the fix (re-run to catch anything missing) resolves it regardless of cause, same reasoning as CARD-0037.

Full run logs retained on the M8 at `/home/jct/immich-go-verify-20260709/` (`joseph-backup.log`, `joseph-home.log`, `robin.log`, `run.out`).

---

### CARD-0032 · [bug] [photo-server] Heartbeat doesn't detect real storage failures (found 2026-07-08)
**Status:** Done

**Resolution:** `photo-server-heartbeat.py` now writes, reads back, and removes a marker file (`/data/upload/.heartbeat_check`) *inside* the `immich_server` container on every run where the container itself is confirmed up, catching the exact class of failure Docker's own health check misses (it only pings the Immich API, never touches `/data`). A failure is appended to the same `unhealthy` list and reported as `Alert - storage:<error text>`, using the identical non-collapsing path CARD-0029 established for degraded containers. Immediate fix (remount, container restart) and root-cause mitigation (udev auto-remount rule) from the original incident were already in place; this closes the actual monitoring gap.

Live-tested 2026-07-08 by remounting `/mnt/photo-library` read-only (`mount -o remount,ro`) — chosen over physically disconnecting the drive, and over a plain `chmod` on the host-side directory (tried first; silently didn't work, since the container runs as root and root bypasses POSIX permission bits — a read-only remount is enforced at the VFS level instead). Dashboard correctly showed `Immich degraded - storage:sh: 1: cannot create /data/upload/.heartbeat_check: Read-only file system`; remounting read-write restored normal status on the next run. Full writeup in `components/photo-server/heartbeat.md`.

**Still unknown:** the original root physical cause of the USB drive disconnecting in the first place (no clear `dmesg` evidence was captured at the time). Worth checking/reseating the USB cable and capturing full `dmesg` as root if it recurs — not blocking, since the monitoring gap that made it dangerous is now closed.

---

### CARD-0029 · [enhancement] [photo-server] Live-test Immich degraded-heartbeat alert path
**Status:** Done

**Resolution:** Live-tested 2026-07-08 now that the Immich migration is complete. `docker stop immich_redis` produced `Immich degraded - immich_redis:unhealthy` (then `:starting` during the restart race) as a non-collapsing `Alert` row on the dashboard; `docker start immich_redis` restored normal `System`/online status on the next run. Combined with the CARD-0032 storage-check test in the same session. Full writeup in `components/photo-server/heartbeat.md`.

---

### CARD-0036 · [enhancement] [infrastructure] Dashboard visibility for scheduled reboots
**Status:** Done

**Resolution:** CARD-0035's scheduled reboots were invisible on the JCTsh log dashboard — confirming success required manually SSHing in and checking `systemctl`/`docker ps`. Added a matched pair of MQTT log messages around each reboot: `scheduled-reboot.service` now publishes `"Scheduled reboot about to occur."` immediately before calling `/sbin/reboot` (multiple `ExecStart=` lines in the oneshot unit), and a new `reboot-complete.service` (enabled via `WantedBy=multi-user.target`) publishes `"Boot complete."` on every boot once the MQTT broker is reachable. Pi publishes as component `jctsh-core` to `jctsh/core/log-server/log` using the existing `jctsh-log-server` MQTT account (`/etc/jctsh/log-server.env`) via `mosquitto_pub` (already installed). M8 publishes as component `photo-server` to `jctsh/server/photo-server/log` using the existing `photo-server` MQTT account (`/etc/jctsh/heartbeat.env`) — required installing the `mosquitto-clients` apt package on the M8 (the heartbeat script uses Python `paho-mqtt` instead, so the CLI wasn't already present). Neither message uses the `"Heartbeat - "` prefix, so each occurrence stays visible as its own dashboard row rather than collapsing. Per-host unit files split out: `scheduled-reboot-pi.service`/`scheduled-reboot-m8.service` replace the old shared `scheduled-reboot.service` (now host-specific since the MQTT broker address, credentials file, and topic differ per host). Verified live 2026-07-08 via manual `systemctl start reboot-complete.service` on both hosts — confirmed on the dashboard (`/data` live view and, after flushing, the persisted `/log` file).

---

### CARD-0037 · [bug] [photo-server] ML processing (faces, smart search, duplicates, OCR) never ran on a large fraction of the library
**Status:** Done

**Resolution:** Discovered 2026-07-08 while answering Joseph's question about why most photos showed no identified people in Properties. Diagnosed via the Immich API (not guesswork): a random sample showed ~80% of assets with zero detected faces; a targeted CLIP-search sample of clearly-portrait photos still showed clean detection (26/30 correct), ruling out a model-confidence issue. Definitive proof came from a duplicate pair — the exact same restaurant photo (Immich's own duplicate-detection linked the two copies) had 7 faces detected on one copy and 0 on the other.

**Not specific to Joseph's chaotic import:** checked Robin's library too (via her own API key, since search is scoped per-user) — 96% zero-face rate, even higher than Joseph's ~80%, despite her import running clean with no crashes/restarts (see `components/photo-server/migration.md`). This ruled out the 5-restart-import theory as the sole cause and confirmed the gap was server-wide, affecting both accounts roughly equally.

**Fix:** triggered all five affected ML jobs (`faceDetection`, `facialRecognition`, `smartSearch`, `ocr`, `duplicateDetection`) via `PUT /api/jobs/{name}` (`{"command":"start"}`) — Immich has no dry-run mode, so starting each job was simultaneously the diagnostic (revealing real backlogs: ~140,000 for faces, 33,201 for duplicates, ~17,000 each for smartSearch/OCR) and the fix. Checked load average and `vmstat` before/during (CPU-bound at ~60% user time, only 3-7% iowait — not I/O-bound, plenty of headroom on the 12-core M8) to confirm it was safe to run all five concurrently.

**Confirmed complete 2026-07-09** (ran overnight, unaffected by an unrelated home-internet outage since the jobs run locally on the M8): all five queues back to 0 waiting/active, 0 failed for the entire run. M8 uptime at completion check was 19h36m — never rebooted, confirming genuine completion rather than a state reset. Total people clusters grew 2,626 → 3,331 (+705) as full coverage let previously-under-threshold clusters (`minFaces: 3`) surface. Final spot-check: the `868900f1` duplicate that started the whole investigation at 0 faces now shows all 7, with Joseph and Robin correctly matched by name. `duplicateDetection` found 2,197 duplicate groups total once it had full coverage — worth a manual review pass in the Duplicates view when convenient, not urgent.

---

### CARD-0035 · [enhancement] [infrastructure] Weekly scheduled reboot — Pi and M8 photo-server
**Status:** Done

**Resolution:** Deployed systemd timers on both hosts: `scheduled-reboot.timer` → `scheduled-reboot.service` (`/sbin/reboot`), `Persistent=true`. Pi: Monday 3:00 AM. M8: Monday 4:00 AM — staggered one hour later so the M8 heartbeat script's MQTT publish to the Pi's Mosquitto broker doesn't collide with the Pi being mid-reboot. Not synchronized to KeepConnect's own weekly router reset — that schedule has drifted from its original Wednesday setting, most likely because its "every 7 days" timer restarts from any reset (scheduled or outage-triggered), so it can't be relied on as a fixed weekday anyway; a router reboot's brief network blip is tolerated regardless of timing. Version-controlled unit files in `core/maintenance/`; documented in `SOFTWARE-ENVIRONMENT.md` (Pi) and new `components/photo-server/operations.md` (M8). Verified live via `systemctl list-timers` on both hosts — next run confirmed Mon 2026-07-13. 2026-07-08.

---

### CARD-0033 · [idea] [infrastructure] Document Keep Connect configuration and schedule
**Status:** Done

**Resolution:** KeepConnect is a standalone router-rebooter device (Johnson Creative KeepConnect-27F8, not a JCTsh component). New dedicated doc `keepconnect.md` created at repo root with full device identity, network config, physical outlet-scoping rationale, and complete monitor/timing/schedule/notification configuration. Linked from `jctsh-network.md` devices table (IP 192.168.1.108, DHCP-reserved) and `ENVIRONMENT.md` Hub & Controller table; added to `README.md` repository layout. Remaining open item (scheduled Pi/Immich reboot via cron, separate from power-strip cycling) carried forward in `keepconnect.md` itself. 2026-07-08.

---

### CARD-0021 · [enhancement] [logging] Device status dashboard
**Status:** Done

**Resolution:** Added `/status` endpoint to `core/logging/log_server.py`. Two-section layout: Home (Online/Offline/? per component based on heartbeat presence and 70-min threshold) and Remote (`coachproxyos` always shows last-activity + `?`). Auto-detects heartbeat-capable components — salt-sensor shows `?` until CARD-0004 ESPHome migration adds heartbeats. Deployed to Pi 2026-06-30. Added CARD-0024 (coachproxy remote health monitoring via Tailscale ping).

---

### CARD-0018 · [idea] [immich] Self-hosted photo library
**Status:** Done

**Resolution:** Superseded. Hardware (GMKtec M8) in hand. Replaced by `components/photo-server/` (Immich install + immich-go migration) and `components/photo-tv-display/` (Node.js TV slideshow + phone companion) — full planning docs committed 2026-06-30.

---

### CARD-0014 · [enhancement] [core] Move environmental data pipeline to core
**Status:** Done

**Resolution:** Moved `environmental-data.gs` → `core/data-pipeline/`, `JCTsh-Environmental-Data-Architecture.md` → `core/data-pipeline/`, and `core/node-red/environmental-data.flow.json` → `core/data-pipeline/`. Updated references across 15 files (CLAUDE.md, README.md, Node-RED-workflow.md, JCTsh-Build-Standards.md, JCTsh-Component-Planning-Pattern.md, JCTsh-Property-Sensor-Pattern.md, all component planning docs, hiking-monitor instructions). 2026-06-30.

---

### CARD-0002 · [enhancement] [infrastructure] MQTT v3.1.1 → v5 upgrade
**Status:** Done

**Resolution:** Mosquitto 2.0.21 already supports v5 — no broker config change needed. Changed `protocolVersion` from 4 → 5 in the Node-RED broker config node (`core/node-red/core.flow.json`) and updated the live Pi flows.json in place. Confirmed via Mosquitto log: client `nodered-saltlevel` connected with `p5`. ESP32/ESPHome devices unaffected (remain on v3.1.1). 2026-06-30.

---

### CARD-0008 · [enhancement] [hiking-monitor] Pixel hotspot second WiFi field test
**Status:** Done

**Notes:** Confirmed 2026-06-17 during camping trip. Device connected to JCT Hotspot (IP 10.57.172.159 — Pixel hotspot subnet), reached home MQTT broker via jctsh.duckdns.org over cellular, replayed 7 SPIFFS readings on reconnect. DuckDNS + port 1883 forward confirmed working in the field.

---

### CARD-0017 · [enhancement] [infrastructure] Charging state schema fields for solar/battery sensors
**Status:** Done

**Resolution:** Added `solar_v` (solar panel voltage, V, ADC voltage divider) to the environmental data schema. Decision: `solar_v` chosen over `charging` boolean (not universally available on all charge controllers) and `charge_current_ma` (requires INA219, overkill). Combined with `battery_v`, charging state is derivable in Node-RED or Sheets as `solar_v > battery_v + ~0.3V`. Added to field reference and Sheets schema in `JCTsh-Environmental-Data-Architecture.md` (v1.4), column Z in `components/hiking-monitor/environmental-data.gs`, and Apps Script redeployed. 2026-06-15.

---

### CARD-0016 · [enhancement] [infrastructure] Offline flash logging — extract reusable standard
**Status:** Done

**Resolution:** Created `core/offline-logger/sensor_logger.h` — generic template header with `sensor_log_*` function prefix (adapt by renaming to `<name>_log_*` and updating the log file path). Added "Offline Flash Logging" section to `JCTsh-Property-Sensor-Pattern.md` with template adaptation instructions, on_boot mount snippet, on_connect replay block (500ms settle delay), and interval guard (connected → publish, offline → log_write). Removed CARD-0016 from pattern doc Open Gaps. 2026-06-14.

---

### CARD-0015 · [enhancement] [front-porch-temp-sensor] Environmental data pipeline integration
**Status:** Done

**Resolution:** Added SNTP, humidity/pressure IDs, and 5-min `/data` publish to firmware (temp, humidity, pressure, illuminance, lat/lon H8, rssi, ISO 8601 UTC). Added `illuminance_lx` to the environmental data schema and Apps Script. Node-RED wildcard caught it automatically — no flow changes. OTA flashed 2026-06-14.

---

### CARD-0007 · [idea] [hiking-monitor] Hiking observations pipeline (Tasker → Sheets)
**Status:** Done

**Resolution:** Tasker widget → Android speech recognition → HTTP POST to Apps Script → Hiking Observations sheet with automatic category classification. No keyword prefix — widget tap is the intent signal. Steps 23–26 complete 2026-06-13.

---

### CARD-0001 · [bug] [garage-radar] Garage-radar false presence on door close
**Status:** Done

**Resolution:** Ill-defined and no longer applicable — closed.

---

### CARD-0090 · [enhancement] [hiking-monitor] Tasker "Log Observation" widget cuts off recording too early on normal speech pauses
**Status:** Defer

**Notes:** Raised 2026-07-24. Joseph reports the Tasker voice-observation widget (CARD-0007, Steps 24-25 — "Log Observation" task, **Get Voice** action → `%VOICE` → POST to Apps Script) stops recording too eagerly, not allowing enough time for normal mid-sentence pauses while speaking an observation.

**Root cause investigated:** confirmed via Tasker's own action documentation that **Get Voice** only exposes two configuration fields — a **Language Model** hint and an overall **Timeout** (max wait before giving up if nothing is heard at all). Neither controls mid-speech pause tolerance. That behavior is governed one level down, by the underlying Android speech recognizer's own silence-detection threshold, which Get Voice doesn't expose or let you configure.

**Fix path identified, not yet built:** swap the task's first action from **Get Voice** to Tasker's **Send Intent** action, targeting `android.speech.action.RECOGNIZE_SPEECH` directly with a custom extra:
- Key: `android.speech.extras.SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS`
- Value: a larger millisecond figure (e.g. `3000`) than whatever the recognizer's current default is

**Real caveat, not just an implementation detail:** Android's own documentation for this extra explicitly warns it's rarely used and *"may have no effect"* depending on the recognizer implementation (on-device vs. Google's cloud recognizer may not honor it identically) — this is not a guaranteed fix, just the one real lever that exists.

**Alternatives if the above doesn't pan out (not evaluated further):** break a long observation into multiple quick separate widget taps instead of one continuous dictation; or replace Get Voice with the **AutoVoice** plugin (same Tasker developer), which has its own recognition settings that might expose pause tuning more reliably — not confirmed, would need its own investigation.

**Deferred 2026-07-24 — Joseph's explicit call:** "I'll live with it as it is." Not worth the Send Intent rebuild (and its uncertain payoff) right now. Revisit if it becomes enough of a real pain during actual hikes.

**Related:** CARD-0007 (Hiking observations pipeline — the task this widget belongs to, Done), `components/hiking-monitor/hiking-monitor-claude-code-instructions.md` (Steps 24-25, original Tasker task build instructions).

---

### CARD-0074 · [idea] [hike-izer] Hike-izer Version 2 — SUPERSEDED, split into individual feature cards
**Status:** Defer

**Superseded 2026-07-23:** Joseph decided to move away from batching features into a versioned release after v1 — feature-driven instead, each item tracked as its own card. Split as follows: **Photos** → CARD-0084, **Hiker's own compass/heading** → CARD-0085, **Automatic triggering** → CARD-0086. **Historical weather** dropped entirely (not carried into any new card — distinct from CARD-0083, which covers forecast-at-hike-start, not actual-conditions history). **Rendered web page output** already covered by CARD-0081 (filed independently, same day, before this split happened). Kept here for the original batch's context and reasoning; the "Version 2" grouping concept itself is retired, not just this card.

**Notes:** Raised 2026-07-18, split out from CARD-0073's closure (v1 done). Carried forward the items v1 explicitly deferred, not forgotten:

- **Photos** — Immich integration (`photo-server`) unbuilt; would need an API query matched to a confirmed hike's date/time range and GPS bounding box.
- **Historical weather** — no source picked yet. Note: for a past hike, this means an actual-conditions lookup, not a live forecast.
- **Hiker's own compass/heading** — still a real gap; no sensor captures which way the hiker was facing (v1 only computes the *sun's* compass direction, from pure astronomy). Would need new instrumentation or a different data source, not just more analysis.
- **Automatic triggering** — v1 is on-demand only.
- **Rendered web page output** — v1 is Markdown only; if this happens, output goes in `hike-izer/summaries/` alongside the Markdown, per the code/output separation already established (`components/hike-izer/README.md`).

**Blocking dependency: the hiking-monitor device needs to be operational.** V1's real test data came from the June 15 trip (June 17/18 hikes) — that's the only confirmed-good dataset that exists. The 2026-07-18 run found the device producing **zero** Environmental Data readings that day despite real observations/GPS activity happening (see CARD-0073's resolution) — status unconfirmed: deployed? charged? powered on? Carried forward individually into each split-out card above, since each still needs fresh real hiking data to build and verify against.

**Related:** CARD-0073 (v1, Done) for the full build history and what's already working; `components/hike-izer/README.md`, `.claude/skills/hike-izer/SKILL.md`, `components/hike-izer/fetch_hike_data.py`.

---

### CARD-0027 · [idea] [hiking-monitor] GPIO-controlled power gating for I2C peripherals during sleep — SUPERSEDED by CARD-0070
**Status:** Defer

**Superseded 2026-07-17:** folded into CARD-0070 (LDO swap), which now covers both the boost-to-LDO replacement and this card's peripheral power-gating idea as one combined power redesign — see CARD-0070 for the current part choice (BS250), wiring plan, and status. Kept here for the original observation and P-FET background reference.

**Notes:** Observed 2026-07-03: after putting the device to sleep (display correctly shows "Hiking monitor asleep"), the ESP32's and LTR-390's onboard power-indicator LEDs stayed lit. These are hardwired to their respective 3.3V rails, not GPIO-controlled — ESP32 deep sleep only stops the CPU from executing, it does not cut power to anything downstream. Since `VOUT+` runs directly to ESP32 `VIN` (switch not in the power path) and nothing gates the I2C peripherals' power, BME280 and LTR-390 stay fully powered and drawing their own operating current for the entire "sleep" duration, in addition to the boost module's own quiescent draw (see CARD-0026).

**Idea:** add a small P-FET (or similar high-side load switch) on the 3.3V rail feeding BME280 + LTR-390 (and possibly the e-ink display), gated by a spare GPIO, so the firmware can fully cut peripheral power during deep sleep and re-enable it on wake. Would reduce real standby current beyond what CARD-0026 measures for the current design.

**Sequencing:** do CARD-0026 (measure actual sleep current) first — if the measured number is already acceptable for realistic storage durations, this added complexity may not be worth it. Only pursue if CARD-0026 reveals standby drain is a real problem.

**What a P-FET is (for later reference):** a P-channel Field-Effect Transistor — a transistor that acts as a switch, well-suited to sit on the *positive* supply line and turn power on/off to something downstream (a "high-side switch"). The GPIO does not carry power to the rail itself — it only controls the P-FET's gate (a control signal, negligible current). The actual power path is the P-FET's own source-to-drain channel, wired in-line on the 3.3V rail between the supply and the sensors:

```
3.3V rail ──► P-FET source ──► P-FET drain ──► Sensors (BME280, LTR-390)
                      │
GPIO pin ─────────────┘ (controls the gate only)
```

GPIO pulls the gate low (relative to source) → P-FET turns on → 3.3V flows through to the sensors. GPIO drives the gate high (same as source) → P-FET turns off → sensors disconnected, no power reaches them. P-FET specifically (not the more common N-FET) because P-FETs turn on with the gate pulled low relative to source, which is the natural way to switch a high-side/positive-rail connection with a simple GPIO pin; N-FETs are easier to use on the low side (switching the ground return), which doesn't fit well here since you generally don't want to float the ground of a shared I2C bus. Practically: one small transistor (a few cents) plus maybe a resistor.

**Where exactly to place it:** confirmed via `wiring.md` — the TP4056+boost module's 5.7V output feeds the ESP32's `VIN` pin, and the ESP32 dev board's own onboard regulator steps that down to 3.3V, exposed on its `3.3V` pin. That `3.3V` pin (not the boost module's output directly) is the actual source of the rail feeding BME280, LTR-390, and the e-ink display today. The P-FET must go **between the ESP32's `3.3V` pin and the sensors** — not between the boost module and the ESP32's `VIN`. Gating the boost-to-`VIN` connection instead would cut power to the ESP32 itself, which can't work, since the ESP32 needs to stay powered and running in order to control the gate signal in the first place. Gating only the downstream sensor branch keeps the ESP32 awake and in control throughout, switching off only the sensors.

**Standards cross-reference:** logged as a candidate pattern in `JCTsh-Build-Standards.md` §2.14 point 8 (v1.11) — flagged `[CANDIDATE — not yet required, pending validation]`, not a mandatory requirement yet. Once this card is built and measured, promote §2.14 point 8 to a real required numbered standard if it proves worthwhile.

---

### CARD-0050 · [idea] [infrastructure] Network segmentation to contain a compromised/hostile device on home WiFi
**Status:** Defer

**Priority: low (deprioritized 2026-07-10) — accepted as a residual risk, not offloaded onto CARD-0003.**

**Notes:** Raised 2026-07-10 during CARD-0003 (MQTT TLS) discussion. WPA2/3-Personal on `JCTnet1` only protects the radio hop and doesn't stop a device that's already authenticated on the LAN — anyone holding the shared PSK can capture another client's handshake and derive its session key, and more practically, any device on the same `192.168.1.x` subnet can ARP-spoof to MITM traffic between other devices, bypassing WiFi encryption entirely since that attack happens at L2/L3, not over the air. Right now there's no segmentation at all — every JCTsh device, guest device, and IoT gadget shares one flat subnet, confirmed via `jctsh-network.md` and `jctsh-security-hardening.md` (no VLAN/isolation findings from CARD-0022/0023's audit). Note HA's existing HTTPS proxy (nginx on 443, cert for `raspberrypi.tailfe828a.ts.net`) is Tailscale-only — it doesn't protect LAN-side access today (cert error on direct LAN hit).

**Original proposed fix (not pursued — see Decision below):** put IoT/guest devices (SmartThings-paired gadgets, guest phones, anything not a trusted JCTsh host) on the router's built-in IoT/guest network with client isolation enabled, so they're on a separate broadcast domain and can't reach or ARP-spoof JCTsh devices (Pi, ESP32s, M8) at all. Router is a TP-Link Archer AXE75 (`jctsh-network.md`).

**Decision (2026-07-10) — deprioritized, not executed:** scoping this out surfaced that the original framing no longer fits current reality:
- Guest phones already have their own separate network (existing Guest network, confirmed by Joseph) — the original guest-phone isolation target is already handled.
- Joseph decided Ring, Ecobee, and Google Cast devices (Chromecast, Google TV, Google Home speakers, Nest Display, Pixel Tablet) should stay on the main network — moving them risks breaking phone-to-device casting (mDNS/SSDP needs same subnet), and their actual access pattern (Ring app, Ecobee app, SmartThings/Google Home integration) is cloud-to-cloud, not LAN-dependent, so isolating them buys little anyway.
- The remaining alternative — inverting the approach to isolate the JCTsh devices themselves instead — was scoped and rejected: real, certain ongoing costs (re-IP the whole fleet in `jctsh-network.md`, update every ESPHome `secrets.yaml` MQTT broker address, update the DuckDNS port-forward target, lose casual LAN access to photo-server's web UI for Joseph/Robin, and require Joseph's laptop to temporarily join that network for every future OTA reflash) against a threat that's low-probability and low-consequence given the hardening already completed in CARD-0022/0023 (SSH key-only auth, HA TOTP MFA, Node-RED adminAuth, router admin password rotation, UPnP disabled).
- Router capability is also limited: TP-Link Archer AXE75 has no VLAN support, and community reports (TP-Link forums) flag its Guest/IoT-network client isolation as sometimes leaky — any attempt would need empirical verification before being trusted, on top of the migration cost.

**Risk analysis:** getting a hostile device onto `JCTnet1` at all requires either cracking a strong WPA2/3 PSK or a real exploited vulnerability in an existing IoT device — uncommon for a non-targeted residential home. Even if achieved, the highest-value JCTsh surfaces (SSH, HA, Node-RED) are already independently hardened (key-only auth, TOTP MFA, adminAuth). The only real remaining exposure is cleartext MQTT sensor telemetry on the LAN — low-stakes (salt %, temp, garage presence; the garage door itself is actuated via a Zigbee switch through SmartThings, not exposed via this MQTT path). Low probability × low consequence doesn't justify the migration cost, on its own — independent of CARD-0003.

**Relationship to CARD-0003 (corrected 2026-07-10):** these are NOT substitutes for each other, despite both touching MQTT/network security. CARD-0003 (TLS on 8883) only covers the *internet-exposed* path used by roaming devices (hiking-monitor, air-quality-monitor) — it deliberately leaves LAN-local port 1883 traffic in plaintext for stationary devices (see `CLAUDE.md` "LAN security": "Acceptable for a home network; no mitigation planned"). CARD-0050 was about a different threat — an already-on-LAN attacker sniffing/spoofing that same plaintext 1883 traffic — which CARD-0003 does nothing for. CARD-0050 is deprioritized on its own risk-analysis merits above, not because CARD-0003 covers it. Revisit CARD-0050 only if a future router/hardware upgrade makes real VLAN segmentation available, or if the device inventory or threat picture changes such that the cost/benefit shifts.

---

### CARD-0115 · [bug] [hike-izer] Hike Start Forecast only captures once per calendar day, not once per hike session — RESOLVED 2026-07-30 13:55 MST
**Status:** Done

**Raised 2026-07-29 15:30 MST**, investigating why the day's second hike (CARD-0113's Frederik Meijer Gardens hike) had no Weather Forecast at Hike Start section at all.

**Confirmed directly against real data:** re-fetched the whole day's data — exactly one `Hike Start Forecast` row exists for 2026-07-29, timestamped `11:07:57Z`, matching the *first* (morning) hike. The afternoon hike's own first GPS point (`16:31:21Z`) never captured its own forecast.

**Root cause, confirmed in `core/data-pipeline/environmental-data.gs`:** `_maybeCaptureHikeStartForecast()`'s dedup check scanned the `Hike Start Forecast` sheet for any existing row matching `date_local` — i.e. it captures at most once per *calendar day*, full stop, regardless of how many separate real hikes happen that day. This is the same "event = a day, not a session" gap CARD-0113 already fixed on the Python/hike-izer side, just not yet extended to this Apps Script mechanism, which still runs on the old model. Two real hikes hours apart can have genuinely different weather (morning vs. afternoon); silently reusing (or in this case, simply omitting) the first hike's snapshot for the second was wrong.

**Fixed in the repo, 2026-07-29 (`core/data-pipeline/environmental-data.gs`, not yet deployed — see below):**
1. Replaced the `date_local`-based dedup scan with a session-gap check against `GPS Track`'s own history: if the gap since the immediately preceding GPS point exceeds `SESSION_GAP_MIN` (10 minutes — deliberately kept in sync with `fetch_hike_data.py`'s own `session_gap_min=10`, since this is approximating the same "is this a new hiking session" judgment in real time that the Python pipeline later makes in batch), this is a new session and a forecast is captured. Fewer than 2 real rows in `GPS Track` (i.e. the very first GPS point ever) is trivially a new session too.
2. Moved the new gap check to the very start of the function, before the sheet-creation work and the Open-Meteo call — avoids wasting an external API call on every single GPS point during an active hike, not just avoiding the dedup bug.
3. `date_local` is still recorded in the output row (useful for reading the sheet), it's just no longer what dedup is keyed on.
4. `SCRIPT_VERSION` bumped to `2026-07-29.1-hike-start-forecast-session-scoped`.

**Deployment note:** this is Apps Script, deployed by pasting into the Apps Script editor (no `clasp`/CI tooling in this repo) — I can't deploy it myself. **Needs Joseph to paste the updated `_maybeCaptureHikeStartForecast` function (and the new `SESSION_GAP_MIN` constant above it) into the Apps Script editor and redeploy**, same as CARD-0106's own deployment.

**Deployed and confirmed 2026-07-29 15:36 MST** — Joseph pasted and redeployed; `action=version` confirmed live at `2026-07-29.1-hike-start-forecast-session-scoped`.

**Verified against a real multi-hike day, 2026-07-30 13:55 MST.** Joseph did a genuine second hike today (16:33–16:46 local, generated as `2026-07-30-2` per CARD-0113's naming). Re-fetched the whole day's data: exactly **two** `Hike Start Forecast` rows, one per hike, each matching its own real start time — `11:36:28Z` (63.1°F, 81% humidity, UV 0.45) for the morning hike, `20:33:29Z` (84.4°F, 34% humidity, UV 5.25) for the afternoon one. Physically consistent morning-vs-afternoon weather, not a dedup artifact reusing one snapshot. Closing criterion met.

**Related:** CARD-0113 (the session-vs-day redesign this extends to the Apps Script side), CARD-0106 (original GPS-triggered capture this builds on), CARD-0083/CARD-0097 (original feature and its timezone fix), `core/data-pipeline/environmental-data.gs`.

---

### CARD-0116 · [bug] [hike-izer] Second same-day hike's photo thumbnails 404 — templating.py referenced the wrong photo directory — RESOLVED 2026-07-29 15:44 MST
**Status:** Done

**Raised 2026-07-29 15:40 MST** — Joseph reported no thumbnails displayed on the second hike's page, and clicking a photo produced a 404.

**Root cause, confirmed directly:** `2026-07-29-2_photos/` on the M8 has the real files (confirmed via `ls`), but the live `2026-07-29-2_hike-summary.html` referenced `2026-07-29_photos/...` — missing the `-2` — for every `<img src>` and `<a href>`. `templating.py`'s `render_html()` built the photo directory reference from `date_str` (the plain calendar date), not from `file_stem` (the actual on-disk directory name, `<date>` for the first hike of a day, `<date>-2` etc. for a later one). This is a real gap in CARD-0113's own work: `file_stem` was threaded through `generation.py` for every file-*writing* path, but `templating.py` — which builds the *reference* paths inside the rendered HTML — was never updated to receive or use it, so it silently fell back to the plain date. Invisible on any day with only one hike (file_stem and date_str are identical then), which is why this wasn't caught until a real second-hike day happened.

**Fixed 2026-07-29:**
1. `templating.py`'s `render_html()` gained a `file_stem=None` parameter; `photos_dir` is now built from `file_stem or date_str` (falls back to the old behavior if a caller is ever missed, rather than hard-crashing).
2. `generation.py`'s two `render_html()` call sites (step 1 and step 2) both now pass `file_stem=file_stem`.

**Verified locally:** re-rendered against the real second-hike data — without `file_stem`, photo paths read `2026-07-29_photos/...` (the bug); with `file_stem='2026-07-29-2'` passed, they correctly read `2026-07-29-2_photos/...`. Title/H1 unaffected (still correctly date-only, via `format_date_display(date_str)` — confirmed no crash from a `file_stem` with a `-N` suffix reaching date parsing anywhere).

**Deployed and confirmed live 2026-07-29 15:44 MST.** `2026-07-29-2_hike-summary.html` was re-rendered locally (reusing the existing narrative text and photo manifest — zero additional API cost, no narrative regeneration) with the fixed `templating.py`, then pushed into place on the M8. Verified: a real thumbnail URL now returns `200`, not `404`; the live page's `<a href>`/`<img src>` all correctly read `2026-07-29-2_photos/...`.

**Related:** CARD-0113 (introduced `file_stem`/multi-hike naming; this closes the one place it didn't get threaded through), `components/hike-izer-orchestrator/templating.py`, `components/hike-izer-orchestrator/generation.py`.

---

### CARD-0117 · [bug] [hike-izer] Photo captions never persisted to disk — a manifest re-read loses them silently — RESOLVED 2026-07-29 15:51 MST
**Status:** Done

**Raised 2026-07-29 15:51 MST** — Joseph reported the CARD-0116 photo-path fix lost the real captions on `2026-07-29-2_hike-summary.html`.

**Root cause, confirmed directly:** `photo_captions.py`'s `caption_photos()` adds `caption`/`sign_text` to the in-memory manifest dict and returns it, but never writes the update back to `<photos_dir>/manifest.json` on disk. The originally-published page rendered fine because it used that in-memory object directly in the same run — but `manifest.json` itself, checked directly, never had a `caption` key at all. CARD-0116's fix re-rendered the page from a freshly-read `manifest.json`, which silently carried forward the caption-less version fetch_hike_photos.py originally wrote, discarding real, already-paid-for caption data with no error or warning.

**Fixed 2026-07-29** in `components/hike-izer-orchestrator/photo_captions.py`: `caption_photos()` now writes the captioned manifest back to `<photos_dir>/manifest.json` after captioning (wrapped in its own try/except — a write failure doesn't affect the current run, which already has captions in memory regardless; it only risks a *future* re-render missing them, same failure mode this card exists to close).

**Verified:** local test (temp dir, mocked captioning call) confirms the on-disk `manifest.json` correctly gains the `caption` field after calling `caption_photos()`. Deployed to the M8, container healthy.

**Recovered the lost captions, 2026-07-29 15:51 MST:** the original page's real captions were still recoverable from an HTML snapshot saved locally before CARD-0116's re-render — extracted all 41, matched cleanly to every asset in the manifest by ID, merged back in, and re-published `2026-07-29-2_hike-summary.html` a final time (captions restored, photo paths and distance both still correct from the two prior fixes). Also overwrote the stale on-disk `manifest.json` itself with the caption-restored version, so any future re-render of this same page won't lose them again.

**Related:** CARD-0116 (the fix whose re-render exposed this), CARD-0107 (original photo-captioning feature), `components/hike-izer-orchestrator/photo_captions.py`.

---

### CARD-0118 · [enhancement] [hike-izer] Calendar home page: multi-hike days need a real in-cell picker, not a tiny superscript number — RESOLVED 2026-07-29 16:30 MST
**Status:** Done

**Raised 2026-07-29 16:12 MST** — Joseph, looking at today's real two-hike day on the calendar home page: the date links to hike 1, and a tiny "2" (CARD-0113's `.cal-day-extra`, 0.6rem, corner-positioned) links to hike 2. Hard to notice, hard to tap, and doesn't scale past 2-3 hikes.

**Discussed and agreed design:** every logged day's cell shows the day number, then each hike for that day stacked below it as its own small link labeled with its local start time (e.g. `29` / `7:07a` / `12:31p`) instead of a bare index number. Zero-JS (matches the calendar's existing convention) and needs no extra click or page — CSS Grid rows auto-size to their tallest cell, so only a week containing a multi-hike day gets taller; other weeks are unaffected. Applies uniformly to every logged day (including single-hike ones) rather than special-casing hike #1 vs. later hikes, so there's one code path and one visual pattern.

**Acceptance criteria:**
1. `generation.py`'s step 1 (`run()`) records each hike's confirmed local start time (`start_ts`, raw UTC ISO) alongside `offset_str` in `<file_stem>_hike-summary.meta.json`.
2. `build_calendar_index.py` reads `start_ts`/`offset_str` per hike and renders a compact local time label (`7:07a` / `12:31p`) as that hike's link text, in place of the old day-number-is-hike-1 / tiny-extra-number scheme. Falls back gracefully (still a real, clickable link) for any existing meta.json written before this card that lacks `start_ts`.
3. Cell layout/CSS updated so day number + one-or-more stacked hike-time links render legibly at the calendar's small cell size, on both light and dark themes.
4. Verified locally against synthetic meta.json fixtures (0, 1, 2, 3 hikes/day) before deploying.
5. Deployed (orchestrator image rebuilt) and confirmed live — including backfilling today's two already-published hikes so the real motivating case renders correctly, not just future hikes.

**Implemented and verified locally, 2026-07-29 16:20 MST:** `generation.py`'s `run()` now records each hike's earliest confirmed session start (`start_ts`, raw UTC) alongside `offset_str` in the meta.json sidecar. `build_calendar_index.py` gained `_format_time_compact()` (stdlib-only, matching its existing convention) and now renders every logged day's cell as a day-number label plus one stacked link per hike, labeled with local start time (`7:07a`) instead of the old day-number-is-hike-1/tiny-corner-number scheme — applies uniformly whether a day has 1, 2, or 3+ hikes. Tested locally against synthetic fixtures for 0/1/2/3-hike days plus a meta.json missing `start_ts` (pre-CARD-0118 file) — falls back to a plain `#N` link, still real and clickable, not broken. Joseph reviewed the rendered size directly and called it "tiny but okay for now" — left as shipped; can be bumped later if it becomes a real problem in practice.

**Deployed and confirmed live 2026-07-29 16:30 MST.** `build_calendar_index.py`/`generation.py` scp'd to the M8, orchestrator image rebuilt and recreated (`docker compose build orchestrator && docker compose up -d orchestrator`). Backfilled today's two already-published hikes (their meta.json predates this card, so had no `start_ts`) by reading each page's own rendered `Time` stat (`7:07 AM` / `12:31 PM`) and writing the corresponding UTC `start_ts` directly via `docker exec` (container runs as root, matching the existing root-owned sidecar files), then re-ran `build_calendar_index.py` inside the container. Verified on both the M8 directly and the real public URL (`https://hikes.jctnet.com/`): today's cell now reads `29` / `7:07a` / `12:31p`, both links correctly pointing at their respective hike pages.

**Related:** CARD-0113 (introduced the multi-hike-per-day file-stem scheme and the tiny-number UI this replaces), `components/hike-izer/build_calendar_index.py`, `components/hike-izer-orchestrator/generation.py`.

---

### CARD-0119 · [enhancement] [hike-izer] Mount the M8 staging directory as a Windows drive (SSHFS-Win), document operational steps for managing staged data — RESOLVED 2026-07-30 13:10 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5215B, over the 5000B size threshold.

---

### CARD-0120 · [bug] [hike-izer] Automatic session query window trusts GPSLogger's self-reported start time -- undercounted today's hike by ~85% — RESOLVED 2026-07-30 06:15 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5952B, over the 5000B size threshold.

---

### CARD-0121 · [bug] [hike-izer] Automatic generation never runs if GPSLogger's "stopped" broadcast never fires
**Status:** Backlog

**Raised 2026-07-30 05:18 MST**, spun off from CARD-0120's investigation. `app.py`'s webhook handler only ever calls `generation.run_and_log()` in response to a `gpsloggerevent=stopped` POST — nothing else triggers automatic report generation. If GPSLogger crashes, gets force-killed by Android, or its Tasker exit condition never fires, no webhook arrives and no page is ever generated for that hike — silently, with no error or alert surfaced anywhere.

**Not solved by CARD-0120.** That card only changes how session bounds are computed once a `stopped` event is actually received; it does nothing for the case where one never arrives at all. Both the old (Option A) and new (Option B) designs for CARD-0120 are equally exposed to this — it's a gap in the trigger itself, not in session-bounds calculation.

**Scope not yet defined** — needs interview/design before moving to Planning. Rough shape: some periodic or backstop check that notices "real GPS trace data exists in the Sheet consistent with a hike, but no corresponding page was ever generated for it," and either generates it late or at minimum surfaces a visible alert (dashboard log line) rather than the gap staying invisible.

**Related:** CARD-0086 (automatic triggering, the system this gap is in), CARD-0120 (the investigation that surfaced this), `components/hike-izer-orchestrator/app.py`.

---

### CARD-0122 · [enhancement] [hike-izer] Automated staging: BirdNET Live phone Share → webhook → M8 staging directory — RESOLVED 2026-07-30 12:45 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 8004B, over the 5000B size threshold.

---

### CARD-0123 · [enhancement] [hike-izer] Make narrative generation opt-in; move place-context/sun-position data into tables instead of prose — RESOLVED 2026-07-30 14:50 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6077B, over the 5000B size threshold.

---

