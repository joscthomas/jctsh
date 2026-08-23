# hiking-monitor — Context

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 10452B, over the 10000B size threshold.

### CARD-0076 · [bug] [hiking-monitor] Rotate all secrets exposed via a botched redaction command, and finish outstanding device re-flashes — RESOLVED 2026-08-18 14:33 MST
**Status:** Done

**Notes:** Raised 2026-07-21. During CARD-0070's debugging session (2026-07-20), a `sed` redaction command intended to mask `secrets.yaml` values before display used a pattern (`key=value`) that didn't match the file's actual `key: "value"` YAML syntax — the redaction silently failed and the **entire** `hiking-monitor-test/secrets.yaml` file printed in plaintext into the conversation transcript: WiFi password, hotspot password, AP fallback password, MQTT password, and OTA password. (Process fix for the redaction mistake itself already logged separately, so this doesn't recur.) The repo's own copy of this file is confirmed gitignored (`components/hiking-monitor/.gitignore`) and was never committed/pushed — the exposure is contained to this session's transcript, not a public leak, but is still being treated as a real exposure event since transcripts can be logged/reviewed outside this conversation.

**Scope (confirmed 2026-07-21, revised 2026-07-22):** all secrets from the exposed file, not just OTA as originally asked — since the whole file printed, every value in it is equally exposed regardless of which one prompted the request:
1. ~~WiFi password~~ — **rotation declined 2026-07-22, risk accepted**, see below.
2. Hotspot password (`hotspot_password`) — new value staged 2026-07-22, awaiting reflash.
3. ~~AP fallback password~~ — same value as WiFi password (see below); **rotation declined 2026-07-22, risk accepted** alongside it.
4. MQTT password (`mqtt_password`) — new value staged 2026-07-22, awaiting reflash.
5. OTA password (`ota_password`) — **already rotated 2026-07-21**, see Progress below.

**Progress (2026-07-21):** OTA password rotated to a new value in all three places that held the old one: `C:\esphome\hiking-monitor-test\secrets.yaml`, `C:\esphome\hiking-monitor\secrets.yaml` (real device's local build dir), and `components/hiking-monitor/secrets.yaml` (repo copy, gitignored). **Not yet reflashed to either device** — the test rig went to sleep after its last successful test with no wake source wired, so it's currently unreachable for OTA (needs the GPIO32→3.3V wake trick, then OTA push, or a USB flash); the real field-deployed hiking-monitor is physically elsewhere and can't be reached at all right now. Both devices are **still running their old OTA password** until reflashed — the new password only exists in the secrets files so far, not on the hardware.

**Progress (2026-07-22) — work done while both devices remain physically unreachable for OTA:**
- **Blast-radius question resolved:** confirmed `wifi_password` is byte-identical across all four ESP32 components' `secrets.yaml` (`front-porch-temp-sensor`, `garage-radar`, `hiking-monitor`, `salt-sensor`) — it is the real JCTnet1 router password, not a device-specific credential. Rotating it means the router itself plus every device and every person's phone/laptop on JCTnet1, not just hiking-monitor — a much bigger operation than this card's other four secrets. **New finding:** hiking-monitor's `ap_password` field is also set to this exact same value (the fallback AP reuses the real WiFi password rather than having its own independent one) — the two must be rotated together, or the fallback AP keeps the old exposed password even after WiFi itself is rotated.
- **`hotspot_password` and `mqtt_password` confirmed device-scoped** (not shared with any other component) — safe to stage new values now without affecting anything else. Generated and written into all three `secrets.yaml` copies (`components/hiking-monitor/secrets.yaml`, `C:\esphome\hiking-monitor\secrets.yaml`, `C:\esphome\hiking-monitor-test\secrets.yaml`): new `hotspot_password` and `mqtt_password` staged, current live values unchanged on both actual devices. **Do not rotate the Pixel's "JCT Hotspot" password or the Mosquitto broker-side `hiking-monitor` account yet** — both must change in lockstep with the reflash, not before, or the device loses connectivity before it has the new credential. See `credentials.local.md` ("hiking-monitor secrets (CARD-0076 rotation, in progress)") for live-vs-staged values and the exact reflash-time steps.
- **Doc-drift fix (unrelated to rotation, found while cross-checking):** `credentials.local.md`'s OTA password entry (`LxgD4hkAIysR7p6UdWM2`) didn't match what's actually in any of the three `secrets.yaml` files (`w5Akzi3hiXQWhufFXNL5`) — corrected the reference doc to the real value.

**WiFi/AP password rotation declined 2026-07-22 — risk accepted, not blocked/pending.** Reasoning: the exposure is confined to this session's private transcript (Joseph's local machine + Anthropic's backend logging, retained for abuse monitoring, not human-reviewed or indexed in the normal course) — never committed to git, never posted publicly, no evidence of any actual access attempt. The realistic attack vectors (local-machine compromise, or an Anthropic-side breach) either already expose the same plaintext value via `credentials.local.md`/`secrets.yaml` on this same machine regardless of this incident, or are outside Joseph's control and not specifically targeted at this household. Consistent with the same low-probability/low-consequence reasoning already applied to CARD-0050's LAN-security risk acceptance. No further action planned on WiFi/AP unless the threat picture changes (e.g., evidence of actual unauthorized access, or the transcript surfacing somewhere public).

**Done when:** OTA, hotspot, and MQTT passwords are rotated on both the test rig and the real field-deployed hiking-monitor (secrets files already updated for all three — reflash is the only remaining step, blocked on physical device access); Mosquitto broker-side password and the Pixel's "JCT Hotspot" setting updated in lockstep with each device's reflash (see `credentials.local.md` for the exact steps). WiFi/AP rotation is explicitly out of scope per the risk-acceptance decision above, not a remaining gap.

**Blocked as of 2026-08-03 19:10 MST — both devices must be online/reachable to be reflashed, and neither currently is.** Test rig is asleep with no wake source wired (needs the GPIO32→3.3V wake trick, OTA, or a USB flash); the real field-deployed hiking-monitor is physically elsewhere. New passwords are already staged in all three `secrets.yaml` copies — reflash is the only remaining step once a device is accessible.

**Real field-deployed hiking-monitor: rotated 2026-08-17 17:36 MST**, discovered/completed as a side effect of CARD-0009's display-rotation flash (device came back on the bench for that, so this rode along). USB serial flash (OTA was still on the old, unrecorded password — this rotation had never actually reached the device, exactly the risk this card's own "Done when" line was written to catch). `ota_password` and `mqtt_password` now live on the device; Mosquitto broker-side `hiking-monitor` account updated to match in the same session, device confirmed reconnected (`Connected.` on the dashboard). **`hotspot_password` rotation declined, Joseph's call 2026-08-17** — the Pixel's hotspot password was never going to change alongside it, so that field was reverted to its current live value in `secrets.yaml` before this flash rather than deployed half-coordinated. See `credentials.local.md` for the live values.

**Standing lesson from this — the order matters.** The original 2026-07-21 rotation wrote the new `ota_password` into every `secrets.yaml`/doc copy *before* either device could be reflashed, so by the time a device came back on the bench, nobody could say what password it actually expected — the recorded value had moved on without it. New rule going forward (Joseph, 2026-08-17): change the device first, confirm it, then update the record. Never write down a new password before the device it describes has already been changed to match.

**Test rig (`hiking-monitor-test`) still not reflashed** — remains blocked exactly as before, unaffected by the above.

**Second, separate exposure event — Immich API keys, 2026-08-11.** Different component (`photo-quality-review`, not hiking-monitor) and a different root cause, tracked here rather than under a new card since it's the same category of issue -- a botched redaction printing real secrets into a Claude Code session transcript. While answering a question about running a second review-app instance, a `sed` redaction command (`s/(PASS|TOKEN|SECRET|KEY)=.*/\1=****/`) meant to mask sensitive `.env` values before display only matches a variable name that *ends* in one of those words immediately followed by `=` -- `IMMICH_API_KEY_JOSEPH=` and `IMMICH_API_KEY_ROBIN=` have `KEY` in the middle of the name, not at the end, so the pattern silently didn't match and both full API keys printed in plaintext into the transcript. Same containment profile as the hiking-monitor exposure above: confined to this session's private transcript, never committed/pushed, no evidence of actual access.

**Immich API key rotation declined, Joseph's call 2026-08-18 14:33 MST — risk accepted, not blocked/pending.** Same containment profile and reasoning as the WiFi/AP decision above: confined to this session's private transcript, never committed/pushed, no evidence of actual access. Not rotating now; if it ever becomes relevant it'll be handled alongside the test-rig reflash below (see that note), not as a standalone action.

**Test rig (`hiking-monitor-test`) reflash — deferred, not blocking closure, Joseph's call 2026-08-18 14:33 MST.** Still asleep/unreachable, unchanged from the 2026-08-03 blocked note above. Whatever secrets need rotating on it (OTA/hotspot/MQTT, already staged in its `secrets.yaml`) will be handled together, whenever that device next comes back for other work — same lockstep-with-reflash discipline as the real device followed. Not treating this as an open item on this card going forward.

**Card closed 2026-08-18 14:33 MST.** Real field-deployed hiking-monitor fully rotated and verified (2026-08-17 note above) — that was this card's actual operational risk (a live, internet-exposed device). The two remaining loose ends (test rig, Immich keys) are both deliberate, recorded risk-acceptance/deferral decisions, not unfinished work.

---

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 15751B, over the 10000B size threshold.

### CARD-0070 · [enhancement] [hiking-monitor] Replace boost converter with LDO + gate peripheral power for lower standby draw — DEFERRED 2026-08-14
**Status:** Defer

**Deferred 2026-08-14, Joseph's call.** Not pursuing the rewiring on the real field device's perfboard. **Neither fix was ever ported to the real hiking-monitor** — per this card's own Sequencing plan, both the LDO and the peripheral gate were only ever built and tested on the CARD-0026 rig prototype (spare ESP32 + spare TP4056), with porting to the real device explicitly planned as the step *after* the rig proved out. The rig confirmed the LDO half works (fixes CARD-0026's ~22.6mA boost-converter quiescent draw); the gate half turned into a real parts-quality debugging saga on the rig (a persistent ~2.78-2.9V leak traced to likely-counterfeit BS250 stock, replacement genuine units ordered but never re-tested) and was never fully proven even there. Given that, opening up the real field device's hand-soldered perfboard for a fix that's only partially validated on a separate rig isn't worth it — **the real hiking-monitor keeps running its original, unmodified boost converter**, exactly as it always has. Living with it as-is.

**Not lost, though — lessons carry forward to future builds:** the MCP1700/BS250 TO-92 pinout identifications, the LDO wiring pattern (`VOUT` → ESP32's `3V3` pin directly, never power from USB and the LDO simultaneously), the gate pull-up requirement (a floating BS250 gate can stay conductive through deep sleep without one), and the counterfeit-parts gotcha (empirically diode-test incoming MOSFET stock, don't trust the datasheet pinout alone against unverified suppliers) are all real, validated findings worth applying the next time this project does a battery-powered sensor build, even though they're not being retrofitted here.

**Notes:** Raised 2026-07-16, directly motivated by CARD-0026's measurement — the test rig's TP4056+boost module draws 22.6mA steady in deep sleep, dominated by the boost stage's always-on quiescent current (est. ~48.7hr / ~2 day runtime on a 1100mAh cell). This matches the existing recommendation in `JCTsh-Build-Standards.md` §2.14 point 7 (prefer direct LiPo→LDO over boost-then-buck) — this card is the concrete follow-through on that recommendation.

**Expanded 2026-07-17 to absorb CARD-0027** (GPIO-controlled peripheral power gating, moved to Defer as superseded — see that card for the original writeup and P-FET/high-side-switch background). CARD-0026's closing note flagged why these two fixes belong together: once the LDO removes the boost stage's ~22.6mA quiescent draw, BME280 + LTR-390's own ungated idle current (previously negligible next to the boost module, estimated tens to a few hundred µA) becomes the largest remaining contributor to sleep current. Doing the LDO swap without also gating the peripherals would leave real savings on the table.

**Part 1 — LDO:** MCP1700-3302E/TO, TO-92 through-hole (3 legs: VIN, GND, VOUT), ~1.6µA quiescent current, 250mA max output. Chosen over AP2112K-3.3 (lower quiescent current margin isn't the issue — package is: SOT-23-5 SMD, impractical for this project's hand-solder/perfboard build convention without a breakout board) and over AMS1117-3.3 (5-10mA quiescent — same problem class as the boost module it's replacing, the wrong part family for a battery/sleep application). **On order, arrives 2026-07-17.**

**MCP1700 TO-92 lead identification** (confirmed against Microchip datasheet DS20001826F, cross-checked via two independent sources 2026-07-20 — this part's pinout is a known gotcha, reordered from the common 78xx VIN-GND-VOUT convention):

| Pin | Position (flat face toward you, legs down) | Signal |
|---|---|---|
| 1 | Left | GND |
| 2 | Middle | VIN |
| 3 | Right | VOUT |

**Part 2 — peripheral gate switch:** BS250 P-channel MOSFET, TO-92 through-hole. Vgs(th) typically ~-2.1V (worst case -3.5V), adequate for a 3.3V GPIO gate drive at the tiny currents involved (a few mA for BME280 + LTR-390, maybe tens of mA momentary for an e-ink refresh) — Rds(on) won't be fully enhanced at only 3.3V Vgs, but that's irrelevant at these current levels. **Ordered 2026-07-17.**

**BS250 TO-92 lead identification** (confirmed via two independent datasheet-sourced references, 2026-07-20):

| Pin | Position (flat face toward you, legs down) | Signal |
|---|---|---|
| 1 | Left | Source |
| 2 | Middle | Gate |
| 3 | Right | Drain |

**Sequencing:** prototype both changes together on the CARD-0026 test rig first (spare ESP32 + spare TP4056, Bag 8) — validates the LDO fix (including whether CARD-0026's brownout-reset-loop finding recurs with the LDO in place) and the peripheral-gating firmware logic together, before touching the real device. Once proven on the rig, port the identical changes to the real field-deployed hiking-monitor.

**Wiring plan — LDO:**
- TP4056 stays exactly as-is — continues managing battery charging (and solar input) unchanged. Only the boost stage is removed from the power path; the boost module's `OUT+`/`OUT-` pads go unused once the LDO is wired in.
- LDO `VIN` taps the same battery+ node as TP4056's `BAT+` input — a parallel connection straight off the raw battery, not fed from the boost module's output.
- LDO `GND` ties to common ground (same ground plane as TP4056/ESP32/battery−).
- LDO `VOUT` → ESP32 dev board's **3V3 pin directly** (not `VIN`) — `VIN` expects ~5V and routes through the board's own onboard regulator; feeding `3V3` bypasses that second regulation stage, which is the point of this change. This same `3V3` pin is now the peripheral supply rail the P-FET switches (see below) — previously it was the ESP32 board's own onboard-regulator output, now it's the LDO's output directly.
- **Caution:** never power the board from USB and the LDO at the same time — both would drive the `3V3` rail from separate unisolated sources, risking backfeeding either regulator. Disconnect the LDO before flashing over USB, and vice versa.

**Wiring plan — peripheral gate (BS250):**
```
3.3V rail (LDO VOUT / ESP32 3V3 pin) ──┬──► P-FET source ──► P-FET drain ──► Sensors (BME280, LTR-390)
                                        │            │
                                    R (100kΩ)         │
                                        │             │
GPIO pin ───────────────────────────────┴─────────────┘ (controls the gate only)
```
- P-FET sits **between the shared 3.3V rail and the sensors** — not between the LDO and the ESP32 itself. The ESP32 must stay powered continuously (straight off the LDO) so it can still control the gate; only the downstream sensor branch gets switched.
- GPIO pulls the gate low (relative to source) → P-FET turns on → 3.3V reaches the sensors. GPIO drives the gate high → P-FET turns off → sensors fully de-powered. Use a spare GPIO not already claimed by GPIO32 (dock detect) or GPIO27 (slide switch). Rig prototype uses GPIO33.
- **Gate-to-source pull-up resistor required (100kΩ, from the Bag 17 resistor assortment) — found missing 2026-07-20, see Progress note below.** Without it, the gate has nothing holding it off except the ESP32 actively driving GPIO high; once deep sleep halts the CPU, the GPIO output isn't guaranteed to hold its driven state, the gate floats, and a floating BS250 gate can sit past its ~-2.1V to -3.5V Vgs(th) and keep the FET on through the whole sleep period. The pull-up guarantees gate defaults HIGH (FET off) whenever GPIO33 isn't actively pulling it low — covering both deep sleep and the brief pre-boot window before the pin is configured. 100kΩ keeps the added leakage while sensors are on (~33µA) negligible against the LDO's own current budget.
- Firmware: drive the gate on before an I2C read, allow a brief settle time for the sensors to power up and initialize, then read; drive the gate off again before entering deep sleep.

**Progress (2026-07-20):** LDO and BS250 gate wired on the CARD-0026 breadboard rig (bare ESP32 only — no sensors attached for this phase, per the "done when" full-stack I2C check being a later step, not this one). Firmware updated (`C:\esphome\hiking-monitor-test\hiking-monitor-test.yaml`): `sensor_power` GPIO switch on GPIO33, active-low to match the BS250 gate, turns on with a 50ms settle delay before each wake's sensor-read block and turns off immediately before all three `deep_sleep.enter` call sites (normal sleep, low-battery cutoff, slide-switch-off). Reflashed via OTA using a temporary trick — briefly moved the GPIO32 dock-detect jumper from GND to 3.3V to hold the rig awake (defeating the immediate-sleep branch) long enough for a reliable OTA push, avoiding the USB/LDO dual-power conflict — then moved the jumper back to GND to restore the CARD-0026 sleep-forcing condition and reset the board.

**Result:** gate turns on correctly, rail holds steady 3.3V, no brownout/reset-looping under the WiFi-connect spike — LDO risk flagged above did not materialize. **But the gate does not turn off during sleep** — confirmed the board actually entered deep sleep (mDNS/ping stopped resolving), yet the gated rail stayed at a steady 3.3V throughout. Root-caused to the missing gate pull-up documented above. Fix identified, not yet installed/retested as of this note.

**Progress (2026-07-20, continued) — pull-up installed, then a second unrelated firmware bug found and fixed:** After wiring the 100kΩ gate pull-up, the rail still didn't drop during sleep. Traced to an unrelated pre-existing bug in `hiking-monitor-test.yaml`'s `slide_switch` binary_sensor: its `on_state` handler fires on ESPHome's initial state publish at every boot (not just on real transitions), and since the slide switch always reads "off" on this rig (GPIO27 unconnected, floats via internal pull-up), that handler ran unconditionally on every boot — calling its own independent `switch.turn_off` + `deep_sleep.enter`, regardless of `dock_detect`, racing against the separate (correctly dock-aware) decision in the `on_boot priority: -200` block. Fixed by adding `binary_sensor.is_off: dock_detect` to that handler's condition, matching the guard already used elsewhere. Reflashed via OTA (added a temporary `api:` component to `hiking-monitor-test.yaml` to pull live logs over WiFi mid-session — still present in the file, harmless to leave, remove before this config is considered final). Also found and fixed during this session: the gate pull-up's non-Gate leg and the BS250's Source leg had been wired to the *raw battery/LDO-input* tap instead of the LDO's regulated *output* — corrected to both land on the LDO output rail, per the wiring plan above.

**Progress (2026-07-20, continued) — systematic diagnosis of a persistent partial-conduction leak:** Even with all of the above fixed, the gated rail still wouldn't drop below ~2.78-2.9V during the "off" condition (against a 100kΩ Drain pull-down added specifically to give Drain a defined reference — it had no load/sensors attached to define this state otherwise). Ruled out, in order, each with a direct test rather than assumption:
- **Ground rail continuity** — checked with battery disconnected, confirmed continuous, not a rail split.
- **FET orientation** — user identified and corrected a Source/Drain swap (had been reading the TO-92 package from the wrong face).
- **GPIO33/firmware involvement** — disconnected GPIO33 from Gate entirely; leak persisted identically, so not a firmware or GPIO drive issue.
- **The resistor/wiring network itself** — pulled the FET out of the breadboard completely (pull-up, pull-down, and all other wiring left in place); Drain cleanly read 0V with no FET installed, confirming the passive network has no bridge or short of its own.
- **A second, physically different BS250** (still Bag 34 stock) substituted in — identical ~2.78V leak reproduced.
- **Empirical lead identification** (diode-test mode, battery disconnected, all 3 leg-pairs both polarities) on the second unit: the pin reading OL against both others in every direction is Gate; the Source/Drain pair showed a real ~0.56V diode drop in one direction only. Anode (current-sourcing/positive-probe leg) = Drain, cathode = Source, per the P-channel body-diode rule. Result confirmed Left=Source, Mid=Gate, Right=Drain — the original standard TO-92 convention from earlier in this card — and confirmed as matching the actual current wiring.
- **Vgs directly measured** (not assumed) in the passive "should be off" state (GPIO33 disconnected, Gate floating via the pull-up only): Source and Gate both read 3.2V — Vgs = 0 exactly, which should put a healthy enhancement-mode P-channel MOSFET solidly into cutoff (off-state resistance normally megaohms+, leakage in the nanoamp-to-low-µA range).

**Conclusion:** with wiring, orientation, GPIO/firmware, the resistor network, and Vgs all directly verified correct, the remaining ~15-19kΩ effective Source-Drain conduction at Vgs=0 (reproduced identically across two physically different units from Bag 34) is far too conductive to be normal MOSFET subthreshold leakage. This points to a **parts/batch quality issue** with the Bag 34 BS250 stock — possibly mismarked or counterfeit units not behaving as genuine enhancement-mode P-channel devices — rather than any remaining circuit fault. (This project has hit exactly this class of problem before: see the counterfeit Podazz BMP280 sensors in `jctsh-parts-inventory.md`.) **Next step: source/verify BS250 units from a different supplier or batch before re-attempting the gate-off verification** — not more rewiring of the current stock.

**Replacement parts ordered (2026-07-20):** genuine BS250P (Diodes Incorporated) from Jameco — an authorized distributor, sourced directly from the manufacturer, unlike the suspect Bag 34 stock's original source. Same part, same datasheet, same pinout convention already confirmed empirically this session (Source-Gate-Drain, standard TO-92). Plan on arrival: run the same diode-test lead/health check used tonight (Gate = OL to both other legs in both directions; Source-Drain pair shows one clean ~0.5-0.7V diode reading, OL the reverse) as an incoming-inspection step before wiring any unit in, then re-attempt the gate-off verification this card is still blocked on.

**Known risk (LDO):** MCP1700's 250mA max is a tighter margin than AP2112K's 600mA against the ESP32's active-WiFi current bursts (109-154mA observed on this same rig during CARD-0026, USB-powered). If the LDO can't sustain those bursts, the same class of brownout-reset loop CARD-0026 diagnosed on the boost module could reappear on the new LDO path — this is exactly what the rig-first prototype step is meant to catch before committing to the real device.

**Standards cross-reference:** inherited from CARD-0027 — logged as a candidate pattern in `JCTsh-Build-Standards.md` §2.14 point 8 (v1.11), flagged `[CANDIDATE — not yet required, pending validation]`. Promote to a real required standard once this card is built and both fixes are measured working.

**Done when:** LDO and P-FET gate both installed and wired per this plan on both the test rig and the real hiking-monitor; each boots cleanly and reaches deep sleep normally on battery power alone (no brownout-reset loop); and the peripheral gate demonstrably cuts sensor power during sleep and restores clean I2C communication (BME280/LTR-390 both respond) on wake.

**Moved to Build (2026-07-20)** — starting the rig-first prototype (LDO + BS250 gate) per the Sequencing note above.

---

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 13458B, over the 10000B size threshold.

### CARD-0009 · [enhancement] [hiking-monitor] Enclosure design and build — RESOLVED 2026-08-18 14:33 MST
**Status:** Done

**Notes:** Design and build the permanent enclosure. Field prototype (two-board sandwich) documented in `components/hiking-monitor/enclosure-prototype.md`. Standoffs arrive 2026-06-14; temp enclosure build before camping trip departure 2026-06-15. Device will be used in the field for ~2 weeks on that trip — hiking and van sensor simulation. Full 3D-printed permanent enclosure is a later step.

**LTR-390 rewiring (2026-07-12):** in progress. Replacing the LTR-390's soldered 0.1" male headers with a 150mm STEMMA QT / Qwiic cable (Adafruit #4209, `jctsh-parts-inventory.md` Bag 31) plugged into the sensor's STEMMA QT port, with the male-header end going into the perfboard's existing LTR-390 female header (unchanged). Gives slack to mount the sensor at the correct sky-facing orientation in the enclosure independent of the perfboard's own orientation — this is what the enclosure build actually needed the flexibility for. Only the sensor-side segment changes; perfboard-to-ESP32 traces (GPIO21/GPIO22) untouched. Docs updated: `wiring.md` (new wire-color table — STEMMA QT cable colors are SDA/SCL-swapped from the old breadboard colors, flagged explicitly), `perfboard-layout.md` (dated addendum on the LTR-390 header row, original build history kept intact).

**Reflection (required last Build step, per `JCTsh-Operating-System.md`):** once the enclosure is built and verified, two harvests before this card closes:

1. **3D-enclosure instruction template.** Generalize `hiking-monitor-enclosure-instructions.md` into a reusable template — e.g. `JCTsh-3D-Enclosure-Instructions-Template.md` at the repo root, following the same pattern `JCTsh-Component-Planning-Pattern.md` already establishes for component planning. Strip out hiking-monitor-specific content (exact dimensions, LTR-390/BME280/display specifics) and keep the reusable procedure: Tinkercad + OpenSCAD two-tool workflow, `-raw`/`-final` export naming convention, Xerocraft Bambu Studio/print-session steps, PLA-test-then-ASA-final print pattern, test-fit checklist structure. So the next component needing a printed enclosure (candidates already in the backlog: remote-temp-sensor-01, air-quality-monitor's clip-case) starts from a template instead of copying and hand-editing this component-specific doc from scratch.
2. **Any other pattern harvesting this card's work warrants** — not just the enclosure template. Sweep the full card history for anything worth capturing somewhere it'll be found again (per TOS's general Reflection rule, not limited to enclosures): the STEMMA QT/Dupont cable relocation fix for sensors that are rigid-socket-mounted facing the wrong way (a mounting-orientation pattern, not enclosure-specific — could recur on any future sensor with a fixed connector orientation); the `-raw`/`-final` STL naming convention and the `hiking-sensor` vs `hiking-monitor` (folder vs. ESPHome device name) confusion this card surfaced, in case anything beyond the enclosure-instructions doc references that ambiguity; and `hiking-monitor-enclosure-instructions.md` Step 56 already exists for build-standards-specific harvest (print orientation, insert types, ASA/PETG choice, etc.) — confirm it actually gets run, don't let this broader reflection substitute for it.

**Don't close until:** rewiring physically complete and I2C communication re-verified (LTR-390 still detected at 0x53, UV/light readings sane) after reassembly, AND both reflection items above are complete.

**Xerocraft trip prep (2026-07-13):** for the Session 1 PLA test print visit (`hiking-monitor-enclosure-instructions.md` Steps 30–33), bring:
- `components/hiking-monitor/enclosure/bottom-shell-final.stl`, `top-shell-final.stl`, `vent-insert-final.stl` — the current, ready-to-print exports.
- `hiking-monitor-enclosure-instructions.md` and `hiking-monitor-enclosure-plan.md` for on-site reference (Steps 30–36 cover this exact session; the plan doc's dimensions table is the fallback if a Step 34/35 test-fit check fails and you need the intended measurement to diagnose the offset).
- Physically: the main perfboard assembly (ESP32/BME280/LTR-390/switch) and the top-shell contents (display, TP4056+adapter, LiPo) — Steps 34–35 test-fit the freshly printed shells against the real hardware, not just visually.

**Doc fix (2026-07-13):** `hiking-monitor-enclosure-instructions.md` had stale STL filenames (`-cuts.stl` instead of the actual `-raw`/`-final` convention) and a wrong `components/hiking-monitor/enclosure/` path (should be `hiking-sensor`) throughout Steps 15, 16, 22, 23, 28, 29, 30, and 55. Corrected in the doc itself, including a naming-convention note near the top — see that file for the convention, not duplicated here.

**Xerocraft PLA test print session (2026-07-17):** Session 1 (Steps 30–33) complete — went very well. Test-fit against the actual soldered main perfboard and top-shell contents surfaced several changes, made live in Tinkercad during the session:
- USB-C charging port relocated — the main perfboard turned out to fit nicely stacked directly over the e-ink display board, changing the available wall space from what was planned.
- M3 screw holes and the solar panel wire hole enlarged (original clearance diameters too tight).
- M3 corner screw holes on the top shell corrected to actually pass all the way through.
- Lip on the bottom shell removed.
- A 1mm reference line added to the bottom shell floor, marking the perfboard's position and adjusted for the screw hole placement.

**Follow-up needed before `hiking-monitor-enclosure-plan.md` Section 0 can be updated to match:** these were live Tinkercad edits — exact new values weren't captured during the session. Section 0 exists specifically as the reproduction record (Tinkercad edits can't be replayed automatically), so it needs: the USB port's new wall/position, the new M3/solar hole diameters, what the removed "lip" was and why, and the floor reference line's exact position/dimensions relative to the perfboard. Get these from Joseph (re-opening the Tinkercad project or checking with calipers) before updating the plan doc. **Explicitly declined, Joseph's call 2026-08-17** (see the 12:20 MST progress note below) — not done, a deliberate skip, not blocking closure.

**Reflection items complete, 2026-08-18 14:33 MST:**
1. **3D-enclosure instruction template** — `JCTsh-3D-Enclosure-Instructions-Template.md` created at repo root, generalized from `hiking-monitor-enclosure-instructions.md` (hiking-monitor-specific dimensions/sensors stripped, reusable procedure kept: OpenSCAD+Tinkercad two-tool workflow, `-raw`/`-final` naming, open-face-down print orientation, PLA-test-then-final-material pattern, test-fit checklist structure).
2. **Broader pattern harvest** — `JCTsh-Build-Standards.md` bumped to v1.18: new §1.5 (3D-Printed Enclosure Build Pattern — Step 56's full candidate list, all now validated by the completed real build) and §1.6 (Sensor Cable Relocation for Mounting-Orientation Flexibility — the STEMMA QT/Dupont relocation pattern, generalized beyond this one sensor). The `hiking-sensor`/`hiking-monitor` folder-vs-device-name confusion was checked directly (grep across the repo) and confirmed already fully resolved in every hiking-monitor file since the 2026-07-13 doc fix — no stray references remain. `hiking-monitor-enclosure-instructions.md`'s own Step 56 is superseded by this broader harvest; confirmed it was never silently skipped, it just hadn't been run until now. `components/hiking-monitor/README.md` also updated with a new Enclosure section (files, planning doc, display rotation, BME280 offset, LTR-390 relocation, template/standards cross-references) and status line.

**Don't-close criteria met:** rewiring physically complete and I2C re-verified (12:14 MST note above), both reflection items complete (above). Closing.

**Next print planned: white ASA, Session 2** (`hiking-monitor-enclosure-instructions.md` Part 6, Steps 37+) — the final-material print per the doc's existing PLA-test-then-ASA-final pattern. Joseph's expectation going in: should be close given Session 1's fit corrections, with another print iteration available if needed. Section 0's dimension updates (above) should ideally be captured before Session 2 slices the files, so the ASA print reflects the corrected design rather than repeating any not-yet-documented fixes from memory.

**Progress, 2026-08-17 12:20 MST (Joseph):** LTR-390 STEMMA QT rewiring physically complete. Final ASA print (Session 2) done. **`hiking-monitor-enclosure-plan.md` Section 0 dimension capture — explicitly declined, Joseph's call:** the reproduction-record update flagged above (2026-07-17) will not be done; not an oversight, a deliberate skip. Currently doing final assembly of the perfboard/components into the printed enclosure. Next: retest that everything still works post-reassembly (I2C/sensor re-verification per this card's own "Don't close until" line).

**LTR-390 rewiring retest, 2026-08-17 12:14 MST — passed.** Live MQTT `data` topic reading captured post-reassembly: `uv_index: 0.00` (a real, non-null value — the firmware only ever publishes `null` for UV when the LTR-390 read comes back NaN/undetected, so a genuine `0.00` confirms I2C communication over the new STEMMA QT cable is working; zero itself is expected indoors, away from direct sky). BME280 (temp/humidity/pressure, unchanged wiring) and battery voltage (3.75V) also reporting sane non-NaN values.

**New follow-on, raised 2026-08-17 16:51 MST (Joseph): display needs to be rotated 180°** given the final mounting orientation from assembly. `hiking-monitor.yaml`'s `display:` rotation changed `90` → `270` (repo + `C:\esphome\hiking-monitor\` synced), compiled successfully. **Blocked on physical USB access** — the enclosure is already buttoned up post-final-assembly, and the device isn't reachable via OTA (see below), so flashing requires opening it back up. Joseph's call, 2026-08-17: hold off for now rather than reopen the enclosure immediately — flash whenever it's next open. Firmware change is committed to the working tree, ready to go the next time USB access is available.

**OTA blocked — CARD-0076 fallout, discovered 2026-08-17 while attempting to flash the rotation fix.** `secrets.yaml`'s `ota_password` was rotated 2026-07-21 (CARD-0076) but never actually pushed to the real device — both devices were physically unreachable at the time and the card sat blocked since 2026-08-03. The device is still running its old, unrecorded OTA password, so `esphome upload --device 192.168.1.161` fails with `Authentication invalid`. Confirms CARD-0076's own "reflash is the only remaining step once a device is accessible" — now that it will be, that reflash should carry the already-staged `ota_password`/`mqtt_password`/`hotspot_password` rotation too (coordinated with the Mosquitto broker account and the Pixel hotspot setting per `credentials.local.md`'s existing lockstep steps), not just the display fix, per the standing rule that a recorded password must never be updated before the device itself changes to match.

**USB serial flash completed 2026-08-17 17:31 MST.** Joseph disassembled the enclosure for USB access, connected via COM7 (Silicon Labs CP210x). First `esphome run` attempt hung ~24 min waiting for the ESP32's auto-reset to enter the bootloader (no CPU activity — classic hand-soldered-perfboard issue, no auto-program circuit); killed and retried with a manual BOOT/IO0 + EN/RESET bootloader-entry sequence, which caught successfully. Firmware uploaded, hash verified, rotation-270° display fix and the CARD-0076 password rotation (see that card) both now live on the device.

**Two things flagged in the post-flash boot log, worth checking:**
1. `Error resolving broker IP address: -6` on the very first boot attempt — likely just WiFi not associated yet that quickly after boot, not necessarily a real fault; device reconnected fine once the Mosquitto broker password was updated to match (confirmed live on the dashboard).
2. `[E][waveshare_epaper] Timeout while displaying image!` — the e-ink display timed out trying to refresh right after boot, before the device dropped to sleep. **Resolved by visual confirmation, 2026-08-17 17:54 MST (Joseph):** display looks right, rotated correctly. Treating the boot-time timeout as a one-off transient (device still settling immediately post-flash/reset), not a real wiring fault — the display is demonstrably working now.

**Full post-flash verification complete, 2026-08-17 17:54 MST:**
- Fresh live `data` topic reading captured (not retained — real-time, `ts: 2026-08-18T00:53:32Z`): `temp: 108.7°F, humidity: 16.0%, pressure: 927.5 hPa, UV index: 0.00, battery: 3.92V, RSSI: -47dBm` — BME280 and LTR-390 both reporting sane values post-reflash.
- A new live status message (`"Field session ended at 2026-08-18T00:51:32Z"`) confirmed real-time device activity, not stale state.
- MQTT stable since the CARD-0076 password fix — no repeat disconnects (the dashboard's "silent for 35 minutes" watchdog alert is a leftover from before the fix, hasn't recurred).
- Display confirmed visually correct (rotated properly, no display fault) — Joseph, 2026-08-17 17:54 MST.

Display-rotation follow-on: **done.**

---

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 12241B, over the 10000B size threshold.

### CARD-0026 · [enhancement] [hiking-monitor] Measure hiking-monitor sleep-mode current draw — RESOLVED 2026-07-16
**Status:** Done

**Notes:** The hiking-monitor's actual standby battery life is unknown. The ESP32's own deep-sleep draw is negligible (~10µA), but `VOUT+` runs directly to the ESP32's `VIN` with the switch NOT in the power path, so the TP4056+boost module stays active even while the ESP32 sleeps — its quiescent current (undocumented by the manufacturer, plausibly 1-5mA for a cheap module) is almost certainly the real bottleneck. This measurement gives an actual number instead of a guess.

**Reuses the CARD-0025 tester rig** (spare ESP32 from Bag 1 + spare TP4056 from Bag 8) — build both cards in the same bench session.

**Setup:**
1. Flash the spare ESP32 with `hiking-monitor.yaml`, but change `esphome: name:` first (e.g. `hiking-monitor-test`) so it doesn't collide with the real device's hostname/MQTT identity. First flash must be via USB.
2. Tie **GPIO32 (dock detect) directly to GND** with a plain jumper — no divider needed for this test. This deterministically signals "no USB present" so the boot logic reliably proceeds into sleep instead of possibly floating and staying awake.
3. Leave **GPIO27 (slide switch) unconnected** — its internal pull-up reads HIGH by default, which the inverted logic treats as "switch OFF," also matching the sleep condition.
4. Sensors (BME280, LTR-390, display) don't need to be attached — I2C read errors will log but won't block the boot sequence from reaching the sleep-entry check.
5. Wire power as in CARD-0025: battery → TP4056 BAT input, TP4056 boost output → spare ESP32 VIN/GND.

**Measurement:**
1. Break the battery's positive lead and insert a multimeter in series (DC current mode, mA/µA jack — not the unfused high-current jack).
2. Power on. The `on_boot` priority -200 block should take it into deep sleep within a few seconds.
3. Wait a few seconds past that point, then read the steady-state current — that's the real standby draw.
4. Runtime estimate = 1100mAh ÷ measured current (mA), in hours.

**Outcome:** If the reading confirms the boost module's quiescent current dominates (likely 1-5mA range), consider this as supporting evidence for JCTsh-Build-Standards.md §2.14 point 7 (prefer direct LiPo-to-LDO over boost-then-buck for future builds) — the always-on boost stage is exactly what that recommendation exists to eliminate.

**Progress (2026-07-14):** Bench session started.

- **Test build:** created `C:\esphome\hiking-monitor-test\hiking-monitor-test.yaml` (renamed copy of `hiking-monitor.yaml` — `esphome:name: hiking-monitor-test`, own MQTT topic prefix `jctsh/components/hiking-monitor-test`, no collision with the real device). Config validated clean.
- **First spare ESP32 (Bag 1) — confirmed defective, discarded.** USB flash consistently failed with `esptool`: "Failed to communicate with the flash chip" — same failure across two cables, two ports, and manual BOOT-button bootloader entry, ruling out cable/port/timing as the cause. Confirmed hardware fault by successfully flashing a second spare board with an identical setup. Logged in `jctsh-parts-inventory.md` (v2.17, qty 8→7, discarded not returned to stock).
- **Second spare ESP32 — flashed successfully.**
- **Setup Steps 2-5 complete:** GPIO32→GND jumper, GPIO27 left unconnected, sensors not attached, battery→TP4056 BAT→boost output→ESP32 VIN/GND wired.
- **First reading: 0.03mA (30µA), steady.** All 4 wiring checkpoints re-verified (battery→TP4056 connection solid, meter correctly in series on battery+ lead, TP4056 VOUT — not BAT input — wired to ESP32 VIN/GND, meter dial+jack correctly on DC mA/µA) — wiring confirmed correct.
- **Reading is suspiciously good, not yet trusted.** ESP32's own deep-sleep draw (with both ext0/ext1 wakeup active) is plausibly 10-150µA alone, which could account for most of 30µA — but generic boost-converter ICs in these cheap TP4056+boost modules typically draw >1mA just keeping their regulation loop alive when actively switching. 30µA total suggests the boost stage likely **isn't actually engaging** under this near-zero sleep load (may be passing raw battery voltage through rather than truly boosting), rather than the module being unusually efficient.
- **Also unexplained:** no board LED lit at any point, including during boot — inconsistent with the real hiking-monitor's own documented behavior (onboard power LED is hardwired to 3.3V rail, stays lit through deep sleep per the CARD-0027 observation that motivated this whole investigation).

**Don't trust the 0.03mA reading until verified.** Decided against troubleshooting the existing rig in place — going to rebuild clean instead, ruling out a marginal/bad TP4056 module or a bad connection entirely rather than just checking voltages on a possibly-faulty setup.

**Next steps (resume here):**
1. Rebuild with a **fresh spare TP4056** (Bag 8) and **all-new connections** — battery→TP4056 BAT, TP4056 boost output→ESP32 VIN/GND, meter in series on the battery+ lead. Same working ESP32 (already flashed, no need to reflash).
2. Re-run the measurement (Measurement Steps 1-4 above) on the rebuilt rig.
3. If the new build still reads implausibly low (~30µA) and still shows no board LED: measure TP4056 VOUT+/VOUT− voltage (expect ~5V boosted, not raw ~3.7-4.2V battery voltage) and ESP32's 3V3 pin voltage to pin down whether the boost stage is actually engaging.
4. If the new build reads meaningfully higher (closer to the originally-feared 1-5mA range): that's likely the real number — the first rig probably had a bad TP4056 or a marginal connection. Proceed to the runtime calculation (Measurement Step 4) and CARD-0027's sequencing decision.

**Progress (2026-07-16) — root cause of the suspicious 30µA reading found: a blown fuse in the ammeter itself, not the TP4056 or wiring.**

Rebuilt clean with a fresh TP4056 and all-new connections per Next Step 1 — got the *identical* 0.03mA reading again, and VOUT+/VOUT− measured only 0.02V (not ~5V boosted, not even raw ~3.7-4.2V battery voltage — essentially zero). Forcing an active boot (disconnecting the GPIO32→GND jumper) didn't change either reading, which ruled out "boost auto-shuts-off under near-zero load" as the explanation — a module that dynamically responds to load should have reacted to a forced active-boot current spike, and it didn't.

Traced it properly instead of re-guessing: measured raw battery voltage directly (3.8V, healthy) vs. voltage at the TP4056's BAT+ input terminal (0.02V) — a ~3.8V drop at only 30µA implies roughly 126kΩ of resistance somewhere in between. Confirmed by measuring directly across the ammeter's own two terminals: 3.86V, meaning nearly the entire battery voltage was dropping *inside the meter itself*. **The ammeter's mA/µA fuse was blown.** Every "suspiciously good" reading across two separate, freshly-wired TP4056 rebuilds was never real hiking-monitor current at all — the TP4056 and ESP32 had been starved of real power the whole session, which is exactly why nothing else lined up (no LED, ~0V at VOUT, current not responding to a forced active boot).

**Switched to a second multimeter for current measurement (same rig, no rewiring needed).** First real result: ESP32's onboard LED lit for the first time all session (real power finally reaching the board) — but current bounced 109-154mA continuously and never settled, even after a full minute-plus and even after power-cycling with GPIO32 freshly reconnected to GND.

**Diagnosed via USB serial log** (`esphome logs hiking-monitor-test.yaml`, one diagnostic power cycle — current reading invalid during this cycle since USB power dominates, that's expected and fine): boot proceeded cleanly on USB power — BME280/LTR-390 failed to respond (expected, sensors not attached for this test), MQTT failed to resolve the broker address (`Error resolving broker IP address: -6`, non-fatal, noted but not investigated further), and the device reached `[I][deep_sleep:057]: Beginning sleep` in about 1 second. Firmware sleep-entry logic is confirmed correct and fast.

Re-tested on battery power alone (USB disconnected, fresh reset): still bouncing 100+mA, never settling — same as before USB confirmed the firmware works. Since USB (stable 5V) sleeps cleanly every time and battery/boost power never does, root cause is almost certainly a **brownout-reset loop**: the boost module's output sags under the ESP32's active-boot/WiFi current spike (~100-250mA bursts), dips below the brownout threshold, forces a reset, and the cycle repeats indefinitely — the device never completes one full boot-to-sleep cycle on battery power alone.

**Worked around it with a hot-swap methodology** rather than trying to fix the module: booted on USB, let it reach `Beginning sleep` and settle for a couple seconds, then disconnected USB *without resetting the board* while the battery/TP4056/meter circuit stayed connected throughout (already powering the board in parallel). This sidesteps the problem entirely — the boost module only had to sustain deep sleep's tiny steady current, never the active-boot spike it can't handle.

**Result: 22.6mA steady, on the 200mA range (nowhere near overload), LED lit.** Confirmed LED-lit is *expected* for genuine sleep, not a red flag — deep sleep only stops the CPU, it doesn't cut power to the 3.3V rail the LED is hardwired to, exactly matching CARD-0027's original observation on the real device. Runtime estimate: 1100mAh ÷ 22.6mA ≈ **48.7 hours, roughly 2 days** — worse than the original 1-5mA estimate that motivated this measurement (which would have implied 9-46 days).

**Important caveat — this brownout-reset-loop behavior has never been observed on the real, field-deployed hiking-monitor** (carried on a two-week camping trip, field-proven per CARD-0008). That strongly suggests this specific failure mode belongs to *this test rig's spare TP4056 module* (Bag 8), not the real device's own installed module — plausibly the same kind of unit-quality issue as the spare ESP32 that had to be discarded earlier in this same bench session. Since this module also can't handle load the way the real device's module apparently does, its idle/quiescent characteristics may not be identical either — poor load regulation and higher quiescent draw often correlate in cheap parts, but it's not guaranteed. **22.6mA should be treated as a real, valid measurement of this test rig's specific module, not a confirmed number for the real hiking-monitor's own module.**

**Also not accounted for:** BME280 and LTR-390 aren't attached to this test rig. Per typical datasheet specs each would add roughly tens to a few hundred µA of additional idle draw on the real device — small relative to the 22.6mA boost-module-dominated total, but real. Net effect: the real device's actual sleep current is probably somewhat *higher* than 22.6mA, not lower, meaning real standby life is probably somewhat *less* than the 48.7-hour estimate.

**Worth flagging separately:** if Bag 8's spare TP4056 stock has a batch-quality issue, it's relevant to any other component build that reuses it (remote-temp-sensor-01, air-quality-monitor's clip-case).

**Outcome:** boost module's quiescent current confirmed as the dominant factor in standby drain, strong evidence for CARD-0027's proposed peripheral power-gating fix — though since the boost stage itself (not just the peripherals) is the measured bottleneck here, a fix that only gates BME280/LTR-390/display power wouldn't address the biggest contributor unless it also cuts the boost stage. Worth revisiting CARD-0027's scope with this in mind.

**Closed 2026-07-16:** measurement scope is complete — real number obtained (22.6mA), method verified, caveats documented. The open question of whether this number holds for the real device's own TP4056 module is no longer blocking closure: CARD-0070 (LDO swap) now owns that verification as part of its own "done when" criteria (real hiking-monitor must boot and reach sleep normally on the new power path), so it doesn't need a separate open card here.

---

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 5781B, over the 5000B size threshold.

### CARD-0180 · [enhancement] [hiking-monitor] On-demand remote reboot, triggered from Home Assistant — RESOLVED 2026-08-19 17:24 MST
**Status:** Done

**Raised 2026-08-17 18:01 MST (Joseph):** surfaced while closing out CARD-0009's final assembly — no way to reset the device without disassembling the enclosure (no exposed reset button, no remote-reboot mechanism in the current firmware). Deep sleep wake cycles already function as a full reset in normal operation, but there's no way to force one on demand.

**Interviewed 2026-08-17:**
- Trigger: **from Home Assistant** — a switch/button entity Joseph can press in HA, not a raw MQTT topic he'd have to publish to by hand.
- Log it: yes — publish a System-category message to the existing `/log` topic right before rebooting (`"Manual reboot triggered"` or similar), consistent with how every other action on this device already shows up on the dashboard.
- **Open question, not yet decided:** how to get an entity into HA at all. `hiking-monitor.yaml`'s `mqtt:` block currently has `discovery: false` with an explicit comment — "No HA discovery — hiking-monitor has no Home Assistant integration." Flipping that to `true` would auto-register just the new restart button via standard MQTT discovery (everything else stays `internal: true`, so nothing else gets exposed) with zero edits to `configuration.yaml`. Proposed 2026-08-17, **Joseph deferred the decision ("we'll figure this out later")** rather than approving or rejecting it outright — don't assume yes, revisit at Planning/Build time.

**Discovery approach decided and built, 2026-08-19 17:16 MST.** Confirmed: ESPHome's `internal: true` flag excludes an entity from discovery *and* the native API entirely, not just hides it in HA — so flipping the device-level `discovery: true` while every existing sensor/entity stays `internal: true` (unchanged) means only a new, deliberately-non-internal entity is exposed. `hiking-monitor.yaml` updated: `mqtt:` block's `discovery: false` → `discovery: true` + `discovery_prefix: homeassistant`; new `button: platform: restart` (`Hiking Monitor Restart`, not internal — the only entity this device exposes to HA), `on_press:` publishes the required System-category log message to `/log` before rebooting.

**Deployed and flashed via OTA, 2026-08-19** — device happened to be in an awake USB-connected upload-mode window, so the OTA-vs-USB blocker resolved itself without needing a decision. Live testing then surfaced two real bugs, neither visible from code review alone:

1. **MQTT discovery `unique_id` collision.** Renaming the button's `name:` from "Hiking Monitor Restart" to "Restart" (cosmetic cleanup) created a *new* discovery entity rather than renaming the old one in place — ESPHome derives the discovery unique_id from the entity name, not the YAML `id:`. The new auto-generated id (`ESPbuttonrestart`, from the default `discovery_unique_id_generator: legacy`) collided with identical ids already published by `front-porch-temp-sensor` and `salt-sensor`'s own restart buttons (confirmed live via `mosquitto_sub` on `homeassistant/button/#`), so HA silently dropped hiking-monitor's entity. Fixed by adding `discovery_unique_id_generator: mac` to the `mqtt:` block (folds the device's own MAC into the id) and clearing the stale retained discovery topic before reflashing. Verified via a fresh `mosquitto_sub` showing a MAC-scoped uniq_id and `button.hiking_monitor_restart` appearing correctly in HA. **This same legacy-generator collision risk applies to every other ESPHome device using MQTT discovery — see follow-up below.**
2. **`platform: restart`'s `press_action()` doesn't wait for `on_press:`.** First live test-press rebooted the device successfully, but the custom pre-reboot log message never reached the broker — only the platform's own built-in "Rebooting safely" line did. Root-caused: the `restart` platform's press action reboots immediately/independently of any `on_press:` automation attached to it. Fixed by switching to `platform: template` with an explicit `on_press:` sequence: publish the log message → `delay: 500ms` → `lambda: 'App.safe_reboot();'`.

**Verified live, 2026-08-19 17:24 MST:** re-flashed with both fixes, captured MQTT traffic during a real button press from HA — confirmed order `button/restart/command PRESS` → `log` message `"Manual reboot triggered from Home Assistant"` published → `debug` `"Rebooting safely"`. Entity `button.hiking_monitor_restart` shows correctly in HA with no duplication.

**Standard raised from this, 2026-08-18 14:35 MST:** `JCTsh-Build-Standards.md` §1.7 (Accessible Power Control for Enclosed Devices, v1.19) now makes an accessible reboot/reset trigger (requirement 2, physical or remote) a required decision for every future enclosed build, made before the enclosure is sealed — this card and CARD-0181 are its origin case. §1.7 notes a remote/software-triggered restart (what this card is pursuing) is generally preferable to a physical reset button for a battery-powered field device, since it avoids an extra enclosure penetration.

**Done when:** Joseph can trigger a hiking-monitor reboot from Home Assistant on demand, the action is visible on the log dashboard, and the mechanism for getting there (HA integration approach + deployment method) has been explicitly decided rather than assumed. — **Met, verified live 2026-08-19 17:24 MST.**

**Related:** CARD-0009 (the final-assembly session this surfaced during), CARD-0076 (the OTA-reliability finding — this device rarely has a catchable awake window for WiFi-based flashing), CARD-0186 (follow-up: front-porch-temp-sensor and salt-sensor already collide on the same legacy discovery unique_id this card found and fixed).

---

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 7489B, over the 5000B size threshold.

### CARD-0156 · [bug] [hiking-monitor] "Log Observation" silently loses voice notes when offline — no retry/queue, unlike GPSLogger — RESOLVED 2026-08-13 19:34 MST
**Status:** Done

**Raised 2026-08-13 14:34 MST**, found live: Joseph transcribed several voice observations during the 2026-08-13 hike, but the Hiking Observations sheet has zero rows for that day (confirmed directly against the sheet — last real entry 2026-08-05). Root cause traced during the same investigation: the phone likely lost connectivity for part of the hike (same session Immich's background sync also failed, Tailscale offline on the Pixel) — GPSLogger's trackpoints still came through at 96.8% coverage because `gps-pipeline.md`'s own setup has `Discard offline locations: off`, which explicitly "queues failed GETs and retries when connectivity returns." The "Log Observation" Tasker task (`hiking-monitor-claude-code-instructions.md` Step 24) has no equivalent — a plain synchronous `HTTP Request` POST with no queue, and its final `Flash: "Observation logged"` fires unconditionally regardless of whether the POST actually succeeded. So a failed send looked identical to a successful one, and the spoken text itself is unrecoverable — nothing was cached anywhere.

**Interviewed 2026-08-13.** Joseph's call on retry UX (asked via options: auto-queue-and-silently-retry-with-a-queued-notice vs. auto-queue-with-no-notice-until-actually-sent): **no flash on failure/queue at all — accumulate silently, flash only once actually confirmed sent** (immediately if online, or later when the queue flushes on reconnect). Simpler than either original option offered — one unified code path (always queue first, then always attempt a flush), not a "try direct send, fall back to queue on failure" branch.

**Decided design:**
1. **Log Observation task** (modified): Get Voice → Stop-if-no-input (unchanged) → append `{ts, observation}` to a local queue file (append-only) → call the new **Flush Observation Queue** task inline (covers the immediate-send case: queue of 1, sent right away, so this is not "queue-then-wait" when already online).
2. **New "Flush Observation Queue" task**: exit silently (no flash) if offline or the queue is empty. Otherwise POST each queued observation to the Apps Script, oldest first, stopping at the first failure (leaves the remainder queued, preserves order — don't skip ahead). Remove only the successfully-sent entries from the queue file. Flash **only** if at least one observation was actually sent this run: `"N observation(s) logged"`.
3. **New Tasker Profile**: State "Net Connected" (connectivity regained) → triggers Flush Observation Queue. This is what replaces GPSLogger's built-in offline-queue behavior for this pipeline — the actual resilience mechanism, not just the confirmation-message fix.
4. Build steps to be written as a new numbered continuation of `hiking-monitor-claude-code-instructions.md` (Step 27+), same "Joseph does: / Joseph confirms:" interview-driven format Steps 24–26 already used for CARD-0007 — Tasker configuration has to be done by hand on the Pixel, Claude can't remote into it.

**Done when:** the new steps are built and confirmed on the real device via a real offline test (airplane mode → speak an observation → confirm no flash, confirm nothing in the sheet yet → disable airplane mode → confirm the queued observation posts automatically and the "N observation(s) logged" flash appears), same "Joseph confirms" pattern as every prior step in that doc — not just written instructions.

**Explicitly not in scope here:** CARD-0090 (the recognizer cutting off mid-sentence on pauses) — a separate, already-Deferred issue with the *transcription* itself, not the *delivery* pipeline this card fixes.

**Built and verified live on the real device, 2026-08-13 evening — a much bumpier build than the design above suggested.** Real Tasker behavior on this Pixel diverged from reasonable assumptions in three separate ways, each found only by reading the actual Tasker run log after a failed test, not by inspection:
1. The For loop's variable had to be renamed from `%qf` to `%qfc` — Tasker flatly rejected `qf` as a variable name (`must be a variable or array name`) regardless of formatting; root cause unconfirmed, but the fix is simple.
2. List Files on this Tasker version has no bare-filename mode at all — `%queuefiles` items are always full paths. Read File/Delete File were built around that directly; an extra `Variable Search Replace` step was added to strip the path down to a bare epoch timestamp specifically for the outgoing `ts` field (a real test row's timestamp showed `/storage/e...` before this was caught).
3. Two different attempts at manually detecting HTTP failure (checking `%HTTPR`, then `%err`) both failed on real hardware — `%HTTPR` never resets on a genuine connection failure (stays stuck on the last real response received, even one from far earlier), and `%err` gets reset by *any* subsequent action (a leftover diagnostic Flash silently wiped it before the check could read it). Final design abandoned manual detection entirely: `Continue Task After Error` is off on the HTTP Request action, and Tasker's own native stop-on-error *is* the failure handling — simpler and, unlike the first two attempts, actually confirmed working. Accepted tradeoff: a mid-run failure means earlier successes in that same run don't get their own confirmation flash (data still correctly sent and cleaned up, just no flash that run).

Also found and fixed along the way: the deleted `HTTP Request` action had been pointing at a stale, pre-2026-07-18 Apps Script deployment URL (per `credentials.local.md`'s own redeploy note) — repointed at the current one while rebuilding the action anyway. The Step 27c auto-flush trigger became **two** Tasker Profiles, not one — this version has no unified "Net Connected" state, only per-type options (Wifi Connected, Mobile Network), and a real hiking use case needs both.

All three real-device paths confirmed via actual Tasker run logs: empty-queue silent no-op, successful online send (correct sheet row, correct originally-spoken timestamp), and a genuine offline failure (file remains queued, auto-retried on reconnect, no false-positive flash). Auto-flush-on-reconnect confirmed live via the Wifi Connected profile.

Full build history (including the dead ends) written up in `hiking-monitor-claude-code-instructions.md` Step 27; the resulting current-state architecture is now documented separately in new file `components/hiking-monitor/observations-pipeline.md`, cross-referenced from `data-pipeline.md`'s Hiking Observations Sheet section.

**One real remaining gap, not blocking:** the home-screen `Log Observation` widget got deleted mid-build and re-placing it was intermittently flaky (drag-to-home-screen not always prompting for a task) — testing was done via Tasker's own task list instead, which works identically. Re-placing the widget is a small follow-up, not a new card.

**Related:** CARD-0007 (original "Log Observation" build, Steps 19–26 in `hiking-monitor-claude-code-instructions.md`), CARD-0090 (the deferred, unrelated cutoff issue), `components/hiking-monitor/gps-pipeline.md` (the offline-queue precedent this generalizes), `components/hiking-monitor/phone-workflow.md`, `components/hiking-monitor/observations-pipeline.md` (new standing architecture reference this card produced).

---

