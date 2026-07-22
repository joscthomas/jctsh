# JCTsh Backlog

Lightweight kanban. Each card has a **type** (idea | enhancement | bug) and a unique ID.

**Columns:** Backlog → Planning → Design → Build → Done, plus **Defer** (off to the side — reachable from any stage)
- **Backlog** — captured, not yet being worked on
- **Planning** — plan is being laid out
- **Design** — Claude Code instructions being written
- **Build** — going through Claude Code instructions, including testing
- **Done** — complete
- **Defer** — a deliberate decision not to pursue for now (not abandoned, not forgotten — just consciously parked); can move here from any other column

---

## Backlog

---

### CARD-0058 · [idea] [presence] BLE room-detection for the Pixel 7 via Bermuda
**Notes:** Raised 2026-07-12. Goal: know which room the Pixel 7 is in (`sensor.pixel7_room` in HA) using BLE signal strength from ESPHome nodes already deployed around the house — no new hardware, no dedicated firmware.

**How it works:** each stationary ESPHome node runs an ESPHome `bluetooth_proxy:` component, listening for the phone's BLE advertisements and reporting RSSI to Home Assistant. The **Bermuda** integration (HACS) compares RSSI across all proxies and picks the strongest as the phone's room. Candidate proxy nodes (already deployed, just need `bluetooth_proxy:` added to their YAML): `front-porch-temp-sensor`, `garage-radar`, `salt-sensor`, and `remote-temp-sensor-01` once built (CARD-0044) — needs an ESP32 variant with BLE (the project's standard ESP32 DevKitC-32 qualifies; ESP8266 and ESP32-S2 nodes don't).

**Phone-side requirement:** Android randomizes BLE MAC addresses, so the bare Pixel 7 is untrackable without a stable beacon ID. Fix: enable the HA Companion app's **BLE Transmitter** feature on the phone, which broadcasts a consistent identifier for Bermuda to lock onto.

**Why Bermuda over ESPresense:** ESPresense is the other common option but requires flashing dedicated firmware onto each room's ESP32. Bermuda reuses the existing ESPHome nodes' own YAML via `bluetooth_proxy:`, so it's the lower-effort experiment given the fleet already deployed — try this first before considering ESPresense or new hardware.

**Realistic expectations:** room-level accuracy, not centimeter-level — expect occasional flapping between adjacent rooms from walls/body blocking/phone orientation, damped via Bermuda's per-room RSSI threshold tuning and smoothing/timeout settings. Not a one-shot config; needs an actual tuning pass per room.

**Background — UWB, and why it's not the near-term path here:** Ultra-wideband (UWB, e.g. Qorvo DW3000-based boards like Makerfabs/DWM3001C) does time-of-flight ranging accurate to ~10cm, spoof-resistant (same tech as car keyless-entry and Apple AirTag Precision Finding) — the "killer" version of this idea, enabling actual coordinates/zones (within 1m of the workbench, etc.), not just room buckets. Two blockers make it a separate, later idea rather than this card's scope: (1) hobbyist UWB firmware (Makerfabs/Arduino-style DW3000 boards) does simple two-way ranging between its own tags/anchors and doesn't speak the FiRa session protocol phones actually use, so off-the-shelf anchors and phones ignore each other even though the radios are compatible at the 802.15.4z level — would need FiRa-capable anchor firmware (Qorvo's DWM3001C stack) plus a custom Android app using the Jetpack `androidx.core.uwb` API to bridge to MQTT; (2) hardware gate — the Pixel 10 Pro XL has a UWB chip, but the **Pixel 7 does not** (only the 7 Pro does), so UWB is off the table for this specific phone regardless. If pursued later, UWB tags on things (keys, tool bag, robot vacuum, pets) sidesteps the phone-compatibility problem entirely, at the cost of needing every tracked thing to carry a powered tag.

---

### CARD-0055 · [bug] [garage-presence] Reconcile garage-radar/SmartThings light control — lights sometimes don't turn on
**Notes:** Joseph reports lights sometimes don't come on when entering the garage. Found during a components-vs-backlog reconciliation pass (2026-07-11): the repo fully documents the "presence off" SmartThings routine (closes door, turns off lights — `garage-presence/CLAUDE.md`) but has **no documentation anywhere of the "presence on" routine** presumably responsible for turning lights on when `switch.garage_presence_vswitch` turns on. `garage-radar/README.md` and `garage-presence/README.md` both reference "lights on" only as an outcome label on the vswitch, never as a documented ST routine with its own trigger/conditions — it exists only inside the SmartThings app, unaudited.

**Known chain (from `garage-radar/integration-notes.md`):** LD2412 radar → `binary_sensor.garage_radar_presence` (30s `delayed_off` filter) → triggers HA's "Garage Presence - Restart timer on activity" automation → starts `timer.garage_presence_timer` and turns on `switch.garage_presence_vswitch` → HA is the sole owner of the vswitch state (SmartThings routines must not set it directly, since ST→HA sync is documented unreliable for other sensors — `garage-presence/CLAUDE.md`) → SmartThings observes the vswitch turning on and is presumed to fire a "lights on" routine, which is undocumented and unverified.

**Suspected failure points (not yet confirmed):**
- HA→SmartThings state propagation lag/unreliability for the vswitch itself — existing docs only warn about the *reverse* direction (ST→HA sync unreliable for `binary_sensor.back_door_door` and the PIR motion sensors); nothing confirms the HA→ST direction this flow actually depends on is solid.
- Radar/PIR detection gaps delaying the first `binary_sensor.garage_radar_presence` → on transition (same class of issue already documented for `binary_sensor.garage_motion_motion`/`garage_cam_motion` sticking in Arizona heat).
- Whatever conditions the SmartThings "presence on" routine actually has configured today — unknown, never captured in the repo.

**Resolution path:** (1) audit the SmartThings app directly to capture and document the actual "presence on"/lights-on routine (trigger, conditions, actions), mirroring how the "presence off" routine is already documented in `garage-presence/CLAUDE.md`; (2) next time lights fail to come on, correlate HA logbook history for `switch.garage_presence_vswitch` against SmartThings app history to determine whether the vswitch turned on but ST didn't react, or the vswitch itself never turned on; (3) once root cause is identified, fix it (likely an ST routine condition or a sync-timing issue) and add the missing documentation so this chain is fully traceable end to end.

---

### CARD-0045 · [bug] [hiking-monitor] `wifi.ap:` fallback may prevent `reboot_timeout` from working
**Notes:** Found 2026-07-09 while researching a timeout decision for air-quality-monitor (which follows hiking-monitor's firmware pattern). `hiking-monitor.yaml`'s `wifi:` block has no explicit `reboot_timeout` override, so it relies on ESPHome's default (15 minutes before rebooting on failed WiFi connection). However, ESPHome's own issue tracker (esphome/issues#7222) documents that `reboot_timeout` does not apply when a `wifi.ap:` fallback block is configured — and hiking-monitor's config does have one (`ap: ssid: "hiking-monitor-fallback"`). So the 15-minute default may not actually be functioning as designed on the currently-deployed device.

**Priority: low.** Hiking-monitor's upload/home mode requires USB dock power to stay awake (same architecture as air-quality-monitor's charging-based home mode) — if the bug does prevent the reboot from firing, the device would get stuck awake trying to reconnect, but on USB power, not draining battery. No confirmed real-world failure — CARD-0008's actual field test (2026-06-17 camping trip) succeeded without issue. Worst case is a minor operational annoyance (stuck device needing a physical USB reflash to recover), not data loss or a safety risk.

**Resolution path:** confirm whether hiking-monitor actually needs the `ap:` fallback block at all (original rationale not documented in current firmware/docs — may be leftover from early development). If not needed, remove it and the default `reboot_timeout` should function normally. If needed, find an alternative bounded-recovery mechanism that doesn't conflict with the AP fallback.

---

### CARD-0038 · [idea] [garage-entry-hallway] Direction-of-travel sensor for hallway to garage entry door
**Notes:** Detect which direction a person is walking through the hallway leading to the garage entry door (coming in from the garage vs. heading out to it) — e.g. for automations like arming/disarming, lighting, or logging comings and goings. Discussed 2026-07-09: single HLK-LD2412 mmWave radar (already proven in `components/garage-radar/garage-radar.yaml`) recommended over a two-JSN-SR04T ultrasonic beam-gate — direction derived from the `moving_distance` trend (falling = approaching, rising = receding) via ESPHome's native `ld2412` component, rather than needing two sensors racing to trigger first. Two JSN-SR04T-V3.0 units already in inventory (Bag 30) but better reserved for a point-distance use case (e.g. tank level) rather than this one. No planning doc yet — not started.

---

### CARD-0031 · [bug] [p-w-firefly] Fix coachproxyos heartbeat's same publish/disconnect race condition
**Notes:** While debugging false "photo-server silent for 35 minutes" watchdog alerts (2026-07-06), found the root cause: `photo-server-heartbeat.py` published its `/log` and `/heartbeat` MQTT messages (QoS 1) back-to-back then called `client.disconnect()` immediately without running the network loop — occasionally the second publish's packet hadn't fully flushed before the socket closed, silently dropping the `/heartbeat` message while `/log` (published first) always got through. Fixed in photo-server's script via `client.loop_start()` + `wait_for_publish(timeout=5)` on both messages before `loop_stop()`/`disconnect()`. See `components/photo-server/heartbeat.md` for full root-cause writeup.

`components/p-w-firefly/jctsh-heartbeat.py` (coachproxyos, the RV Pi) uses the identical publish-then-disconnect pattern and almost certainly has the same latent bug — just less noticeable since a stray "coachproxyos silent" alert is easy to dismiss for a device that's expected to roam in and out of Tailscale range. Apply the same fix: `loop_start()` → publish both → `wait_for_publish()` on both → `loop_stop()` → `disconnect()`.

**Blocked:** RV Pi wasn't reachable (Tailscale down / not home) when this was found — deploy next time `coachproxyos` is reachable at `100.90.246.43` or `192.168.1.219`.

---

---

### CARD-0028 · [idea] [photo-server] Automated post-import quality scan (blur/duplicate detection)
**Notes:** Decided during photo-server migration (2026-07-04) to skip a manual pre-import quality pass entirely — importing everything as-is and relying on Immich's built-in duplicate detection (CLIP-embedding-based visual similarity, not just byte-hash) plus an ongoing "favorites" curation habit over time. This card captures the option to add an *automated* (no manual photo review) quality pass later, run after the Immich import so you can see real results first before deciding if it's worth doing.

**Tools considered (all scriptable, no manual visual review required):**
- **czkawka** — free, open source (Rust), finds exact + visually-similar duplicates, plus blurry/broken images; has a CLI, could run directly on the M8 against the Immich library folder
- **imagededup** (Python, by Idealo) — perceptual-hash + CNN-based near-duplicate detection, scriptable
- **fdupes** / **rdfind** — simple exact-byte-duplicate finders (fast, catches literal copies only, not near-duplicates)
- **DIY blur-score script** — e.g. OpenCV Laplacian-variance blur detection, a small Python script with a numeric threshold; could be built on request, nothing off-the-shelf needed
- (Commercial alternatives exist — Aftershoot, Narrative Select — but are built for photographers culling shoots, overkill for a one-time family library pass)

**CLIP note:** Immich's own duplicate detection and smart search are both powered by CLIP (Contrastive Language-Image Pre-training, OpenAI) — specifically `ViT-B-32__openai` on this install. Duplicate detection compares visual embeddings (catches near-duplicates like burst shots), not just identical files, and never auto-deletes — it surfaces candidates in a "Duplicates" review screen for manual confirm.

**Important constraint:** any of these tools can run and *report* findings anytime, including post-import, directly against files on disk. But once Immich owns the library, actually *deleting/archiving* anything found must go through Immich itself (its UI/API) — not direct filesystem deletion — since Immich tracks every asset in its Postgres DB and a raw file delete would desync the DB (broken thumbnails, orphaned references). Ties into the planned deletion-logging system (photo-server Step 14).

**Sequencing:** wait until after Joseph's (and later Robin's) Immich import completes and ML processing (duplicate detection, facial recognition) has run. See what Immich's own built-in detection surfaces first, then decide whether an additional automated tool is worth adding.

---

### CARD-0025 · [enhancement] [hiking-monitor] Test retired LiPo battery — good or bad?
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
**Notes:** The coachproxy heartbeat (every 30 min via Tailscale) confirms the RV Pi and Tailscale link are alive, but it can't distinguish between "Pi is powered off" vs "Tailscale is down" vs "RV is in a dead zone." A more useful health check would poll the Tailscale status directly from the home Pi: `tailscale ping 100.90.246.43` or checking the Tailscale admin API for last-seen timestamp. This gives richer diagnostic output (latency, path) without depending on the RV Pi to actively publish. Implement as a scheduled script on the home Pi that posts results to the log dashboard. Alternative: use Tailscale's built-in status API at `localhost:41112` on the home Pi to check peer state without any external requests.

---

### CARD-0005 · [enhancement] [p-w-firefly] Overlay filesystem
**Notes:** The Pi in the RV runs continuously, accumulating writes from logs, Tailscale state, and OS housekeeping — SD cards have a finite write cycle life and will eventually fail silently. An overlay filesystem makes the SD card effectively read-only during normal operation: all writes go to RAM, the card is only written during a deliberate shutdown sequence.

**Tailscale complication:** Tailscale stores its node identity and keys in `/var/lib/tailscale/`. If that directory is in the overlay (RAM-only), Tailscale loses its identity on every reboot and needs to re-authenticate. Fix: a persistent bind mount (small USB stick or dedicated partition) mapped to `/var/lib/tailscale/` so it survives reboots.

**eRVin image complication:** Raspbian Buster's modified `raspi-config` does not expose the overlay option in its UI — must be set up manually with `bilibop-lockfs` or equivalent.

**Interim protection:** SanDisk MAX Endurance card already installed.

---


### CARD-0006 · [enhancement] [logging] Move log directory to USB stick
**Priority:** low  
**Notes:** Move LOG_DIR in log_server.py from the SD card to a USB stick plugged into the Pi for better write endurance. Add an /etc/fstab entry so it auto-mounts at boot before the jctsh-logging service starts.

---

### CARD-0019 · [idea] [vu-meter] Home theater VU meters
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


## Planning

### CARD-0074 · [idea] [hike-izer] Hike-izer Version 2
**Notes:** Raised 2026-07-18, split out from CARD-0073's closure (v1 done). Carries forward the items v1 explicitly deferred, not forgotten:

- **Photos** — Immich integration (`photo-server`) unbuilt; would need an API query matched to a confirmed hike's date/time range and GPS bounding box.
- **Historical weather** — no source picked yet. Note: for a past hike, this means an actual-conditions lookup, not a live forecast.
- **Hiker's own compass/heading** — still a real gap; no sensor captures which way the hiker was facing (v1 only computes the *sun's* compass direction, from pure astronomy). Would need new instrumentation or a different data source, not just more analysis.
- **Automatic triggering** — v1 is on-demand only.
- **Rendered web page output** — v1 is Markdown only; if this happens, output goes in `hike-izer/summaries/` alongside the Markdown, per the code/output separation already established (`components/hike-izer/README.md`).

**Blocking dependency: the hiking-monitor device needs to be operational.** V1's real test data came from the June 15 trip (June 17/18 hikes) — that's the only confirmed-good dataset that exists. The 2026-07-18 run found the device producing **zero** Environmental Data readings that day despite real observations/GPS activity happening (see CARD-0073's resolution) — status unconfirmed: deployed? charged? powered on? V2 needs fresh real hiking data to build and verify against, the same way v1 was built against real data rather than assumptions — so getting the device back in active, confirmed-working rotation is a prerequisite, not a parallel task.

**Related:** CARD-0073 (v1, Done) for the full build history and what's already working; `components/hike-izer/README.md`, `.claude/skills/hike-izer/SKILL.md`, `components/hike-izer/fetch_hike_data.py`.

---

### CARD-0071 · [idea] [personal] Emergency Access preparation
**Notes:** Raised 2026-07-17, split out from CARD-0034's closure. Covers the "both Joseph and Robin unavailable at once" gap that the rest of `digital-identity-protection-checklist.md` doesn't — since both spouses already have the RoboForm master password memorized, each already has full independent access if something happens to the other, so Emergency Access only matters for the joint-unavailability case.

**Scope:**
1. Evaluate and configure RoboForm Emergency Access — decide the designated contact (reasoning already in the checklist: should be a third party, most likely one of the adult children, not each other — still need to pick which child) and the waiting period.
2. Set up Google Inactive Account Manager (Security settings) — the Google-side equivalent of #1, currently untouched.
3. Test both flows end-to-end once configured — trigger a request, confirm deny/delay notifications work, confirm the waiting period is actually tuned right. Don't just configure and assume it works.
4. Examine documentation needs — what would the designated contact actually need beyond vault/account access (e.g., a will, power of attorney, other estate paperwork) to act on Joseph and Robin's behalf; currently out of scope of the checklist entirely and worth deciding whether it belongs there or elsewhere.
5. Meet personally with the designated contact to walk through everything — what Emergency Access is, how/when it triggers, and what they're expected to do — rather than leaving it as a silent technical configuration nobody but Joseph knows exists.

**Related:** `digital-identity-protection-checklist.md` (Phase 2, Password manager section) and `digital-identity.md` ("What NOT to Store in RoboForm" section) hold the reasoning this card executes against.

---

### CARD-0067 · [enhancement] [salt-sensor] Design and build a 3D-printed enclosure
**Notes:** Raised 2026-07-13, following CARD-0049's perfboard build. Salt-sensor is installed near the water softener, where salt loading creates real splash risk — per `JCTsh-Build-Standards.md`'s enclosure decision rule ("installed outdoors or in a weather-exposed location → use a weatherproof project box"), this triggers an actual enclosure rather than the default open standoff mount. Board/components to house: ESP32 (SparkleIoT XH-32S), 3 status LEDs (Red/Yellow/Green, need visibility), JSN-SR04T connector (cable exit toward the tank), USB power port.

**Explicitly a skills-practice build, not just a functional requirement:** Joseph wants to drive the actual Tinkercad/OpenSCAD CAD work hands-on — same interactive Claude-Code-guides/Joseph-executes pattern as CARD-0009's hiking-monitor enclosure (`hiking-monitor-enclosure-instructions.md`), not something handed off or auto-generated.

**Candidate techniques already discussed:** LED light pipes (clear PETG, ~5mm diameter matching the standard LED assortment, interference-fit press into the wall — see earlier session discussion on hiking-monitor's card) for the three status LEDs' visibility through the enclosure wall.

**Sequencing:** CARD-0009 (hiking-monitor's enclosure) is still in progress and its Reflection step is expected to produce `JCTsh-3D-Enclosure-Instructions-Template.md`, generalizing the enclosure-build process the same way `JCTsh-Perfboard-Build-Template.md` just did for perfboard builds. If that template exists by the time this card starts, use it as the skeleton; if not, this card can proceed independently (using `hiking-monitor-enclosure-instructions.md` directly as a model) and become the second data point that template gets generalized from.

**Planning note (2026-07-13):** confirmed no generic enclosure planning template exists yet — the only precedent is `components/hiking-monitor/hiking-monitor-enclosure-plan.md`, a specific instance for that component, not a generalized template. CARD-0009's own Reflection step is where `JCTsh-3D-Enclosure-Instructions-Template.md` is meant to come from, and that hasn't happened yet. Planning for this card will use `hiking-monitor-enclosure-plan.md` directly as an ad hoc model in the meantime, same way salt-sensor's perfboard build used hiking-monitor's perfboard-layout.md before `JCTsh-Perfboard-Build-Template.md` existed.

**Done when:** enclosure designed and printed (PLA test print, then final material — ASA/PETG per Xerocraft availability, same pattern as CARD-0009), test-fit against the actual soldered perfboard (not just CAD dimensions), LEDs visible through the wall, JSN-SR04T cable and USB power port both accessible, adequate splash protection for the water-softener installation location, and physically mounted.

---

### CARD-0041 · [idea] [photo-server] Disk capacity growth analysis — wait for steady state
**Notes:** Discussed 2026-07-09: want to estimate photo-library growth rate and project when the primary drive (Backup Plus 1TB, currently 615G/71% used) or backup drive (Momentus 640GB) will need replacing/upsizing. Deliberately not started yet — Joseph's call: current disk numbers are all noise from one-off events (CARD-0039 added 3,433 assets in one shot, CARD-0030 just freed 818GB by deleting zips, first post-cleanup backup run is still doing a full reconciliation rather than a normal weekly delta), not representative of organic day-to-day growth.

**Wait for:** the backup cron (CARD-0030/CARD-0040) running its normal weekly incremental cadence for a few cycles, so disk usage tracking reflects only real photo uploads from Joseph's and Robin's phones. At that point, weekly rsync deltas become a meaningful proxy for actual growth rate and a "months until full" estimate becomes trustworthy rather than a guess. Revisit this card once that's true — no fixed date, just "after the dust settles."

---

### CARD-0010 · [enhancement] [front-porch-temp-sensor] Use case definition
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
**Planning docs:** `components/remote-temp-sensor-01/JCTsh-remote-temp-sensor-01-phase1.md` (Phases 1–3), `components/remote-temp-sensor-01/remote-temp-sensor-01-claude-code-instructions.md` (Phase 4)
**Notes:** Started 2026-07-09 as a "replicant" of front-porch-temp-sensor, diverged into a separate component once the location moved from the sheltered porch to full-sun backyard. Phases 1–4 complete. Sensors: BME280 + BH1750 + LTR-390. Power: single swappable EVE 18650 + AEDIKO charger/holder + SUNYIMA solar panel — everything on hand, zero purchases. Firmware: 5-minute wake/publish/deep-sleep cycle (continuous WiFi not viable on this solar panel — ~10x power shortfall). Sensor power gated during sleep via an on-hand BC557B PNP transistor high-side switch (substitutes for a P-FET, same CARD-0027 pattern from hiking-monitor). AEDIKO module's own quiescent current is unmeasured — bench Step 6 of the instructions doc tests it, with a TPL5111 nanopower timer as a contingent (not assumed) mitigation if it's significant. SmartThings/Google Home exposure planned; no LEDs. Deliberately scoped smaller than weather-station (CARD-0011) — no wind/rain/lightning.

**Split into two phases of work, same pattern as hiking-monitor:** the Phase 4 instructions cover only the bench electronics/firmware build (breadboard → perfboard, sensors, power switch, deep-sleep cycle, battery/solar validation). Enclosure design (real weatherproof build with a sun-shielding vent reusing hiking-monitor's louvered vent-insert pattern, plus a separate battery-access hatch) and backyard installation are deliberately deferred to a follow-on planning pass once the electronics are proven — mirrors the CARD-0009 split on hiking-monitor. Second entry in the 3D-printing backlog behind hiking-monitor's enclosure. Ready for Phase 5 (execution) when directed.

---

### CARD-0020 · [enhancement] [hiking-monitor] Hike data visualization (Looker Studio)
**Notes:** Build a Google Looker Studio dashboard connected to the GPS Track and Environmental Data Google Sheets. GPS route on a map, sensor readings (temp/humidity/pressure/battery) over hike duration. Review-after-the-fact use case — no real-time requirement. No new infrastructure needed.

---

### CARD-0012 · [idea] [air-quality-monitor] Air quality monitor
**Planning docs:** `components/air-quality-monitor/JCTsh-air-quality-monitor-phase1.md` (Phases 1–3), `components/air-quality-monitor/air-quality-monitor-claude-code-instructions.md` (Phase 4)  
**Notes:** Portable clip-mounted SEN55 air quality sensor (PM1.0/2.5/4.0/10, VOC, NOx) carried on hikes alongside the hiking monitor. Phases 1–4 complete (2026-07-09). Parts confirmed on hand: SEN55, Adafruit #5964 adapter, JST GH cable — `jctsh-parts-inventory.md`'s SparkFun SEN-23715 entry was mislabeled "SEN54," corrected to reflect it's the genuine SEN55. SEN55 sensor reading uses ESPHome's native `sen5x` platform (no custom component needed there); a custom component is still needed for onboard flash logging + WiFi replay, adapted from hiking-monitor's `hiking_logger.h`. SEN55 power-gated via an on-hand BC547B NPN transistor (same substitution pattern as remote-temp-sensor-01's BC557B) — bench-tested current draw, not just calculated, in Phase 4 Step 6. Follows hiking-monitor's firmware pattern (onboard flash logging, WiFi replay, field/home mode) exactly — that pattern is field-proven (CARD-0008), and the dependency is architectural only, **not** gated by hiking-monitor's still-open enclosure (CARD-0009). Phase 3 timeout policy matches hiking-monitor but explicitly avoids inheriting CARD-0045's `wifi.ap:`/`reboot_timeout` bug. Perfboard footprint measurement and LiPo polarity check moved from Phase 2 planning blockers to Phase 4 bench steps. Clip-case enclosure (with SEN55 intake/exhaust ports — orientation guidance currently flagged low-confidence, needs re-verification) deferred to a follow-on card, same split as hiking-monitor/remote-temp-sensor-01. Ready for Phase 5 (execution) when directed.

---

### CARD-0013 · [idea] [van-sensors] Van sensors (indoor + outdoor)
**Planning doc:** `components/van-sensors/JCTsh-van-sensor-phase1.md`  
**Notes:** Two ESP32 ESPHome nodes for the Pleasure-Way ProMaster 3500 van. Outdoor: BME280 + LTR-390 UV + SEN55 air quality, LiPo powered. Indoor: BME280 + SCD40 CO2 + MQ-6 propane, 12V coach power. Both log to onboard flash during travel, sync to home MQTT on WiFi reconnect (home or Pixel hotspot). DS3231 RTC for accurate timestamps during extended trips. GPS correlation via GPSLogger on Pixel. Phase 1 complete — ready for Phase 2 (hardware selection, inventory scan, open questions resolved).

---

### CARD-0053 · [idea] [photo-tv-display] Ambient photo slideshow + phone controller
**Planning docs:** `components/photo-tv-display/photo-tv-display-phase1-planning.md` (Phase 1), `components/photo-tv-display/photo-tv-display-phase2-planning.md` (Phase 2), `components/photo-tv-display/photo-tv-display-claude-code-instructions.md` (Phase 4)
**Notes:** Two views of one web app: a fullscreen ambient photo slideshow cast to the gathering room Google TV, and a touch-based phone controller (Joseph's/Robin's Pixel, browser bookmark, no app install) for curation/control. Node.js backend runs on the `photo-server` M8 alongside Immich, serving the web app, syncing TV↔phone over WebSocket (`ws`), and making all Immich API calls on the controller's behalf (including asset deletion, logged before/after the Immich delete confirms per the instructions doc). Hard dependency: `photo-server` must be operational (Immich running, both accounts created, at least a test subset of photos importable) before this build starts — already satisfied. Phase 1–2 planning and Phase 4 Claude Code instructions all complete; instructions doc status is "Ready for execution." Build (Phase 5) has not yet started — no code, service files, or deploy activity yet, this card exists to track that upcoming work.

---

### CARD-0054 · [idea] [bedside-clock] Battery-powered tap-to-wake bedside clock for camper van
**Planning docs:** `components/bedside-clock/bedside-clock-planning.md` (Phase 1, v1.2), `components/bedside-clock/bedside-clock-hardware-selection.md` (Phase 2, v1.3)
**Notes:** DS3231 RTC-based bedside clock for the Pleasure-Way van — tap/short-press wakes an SH1106 OLED to show time (DS3231 read/display/sleep), long-press triggers a WiFi-hotspot + NTP resync used only for timezone changes (not routine drift correction — DS3231 alone is accurate to ~1-2 min/year). Original "zero network footprint" BLE Current Time Service sync plan was found not viable (stock Android has no CTS server) and superseded by this DS3231+occasional-NTP approach in Phase 1 v1.2. No MQTT, SmartThings, HA, or watchdog registration — narrowest network footprint of any JCTsh component. Hardware confirmed on hand or ordered: 2 spare ESP32 DevKitC-32, EEMB 603449 LiPo + TP4056 (same combo as hiking-monitor), HiLetgo DS3231 5-pack (avoiding a documented trickle-charge/CR2032 safety hazard on generic combo boards), hiBCTR SH1106 OLED, Twidec panel-mount pushbutton. §2.14 battery-safety compliance table complete — point 7 (boost vs. direct-LDO) decided 2026-07-03 to keep TP4056+boost (matches on-hand stock, van's low over-discharge risk since it's usually shelved near USB power). Only remaining pre-build item is firmware low-battery cutoff design, explicitly deferred to Phase 4.

Phases 1–3 (planning, hardware selection, architecture/integration) all complete. Ready for Phase 4 (Claude Code instructions). Build has not started — no code, firmware, or deploy activity yet.

---

### CARD-0011 · [idea] [weather-station] Weather station
**Planning doc:** `components/weather-station/jctsh-weather-station-planning.md`  
**Notes:** Full DIY outdoor weather station — BME280 (temp/humidity/pressure), VEML6075 (UV), SI1145 (solar irradiance), SparkFun Weather Meter Kit (wind/rain), AS3935 lightning detector, DS3231 RTC, SD card backup, solar+LiPo power. Posts to Weather Underground and Google Sheets. Phase 3 (architecture) complete — MQTT topics, payload schema, SmartThings integration, and six-phase build strategy all decided. Ready for Phase 4 (Claude Code instructions) when directed. Most parts to purchase (~$227 estimated).

---

## Build

### CARD-0076 · [bug] [hiking-monitor] Rotate all secrets exposed via a botched redaction command, and finish outstanding device re-flashes
**Notes:** Raised 2026-07-21. During CARD-0070's debugging session (2026-07-20), a `sed` redaction command intended to mask `secrets.yaml` values before display used a pattern (`key=value`) that didn't match the file's actual `key: "value"` YAML syntax — the redaction silently failed and the **entire** `hiking-monitor-test/secrets.yaml` file printed in plaintext into the conversation transcript: WiFi password, hotspot password, AP fallback password, MQTT password, and OTA password. (Process fix for the redaction mistake itself already logged separately, so this doesn't recur.) The repo's own copy of this file is confirmed gitignored (`components/hiking-monitor/.gitignore`) and was never committed/pushed — the exposure is contained to this session's transcript, not a public leak, but is still being treated as a real exposure event since transcripts can be logged/reviewed outside this conversation.

**Scope (confirmed 2026-07-21):** all secrets from the exposed file, not just OTA as originally asked — since the whole file printed, every value in it is equally exposed regardless of which one prompted the request:
1. WiFi password (`wifi_password` — appears to be the actual home network password, `JCTnet1`'s network, not device-specific — check whether this is shared by other devices/people before rotating, since it has a wider blast radius than a single-device credential)
2. Hotspot password (`hotspot_password`)
3. AP fallback password (`ap_password` — used for hiking-monitor-test's/hiking-monitor's own fallback AP, `hiking-monitor-test-fallback` / equivalent)
4. MQTT password (`mqtt_password`)
5. OTA password (`ota_password`) — **already rotated 2026-07-21**, see Progress below.

**Progress (2026-07-21):** OTA password rotated to a new value in all three places that held the old one: `C:\esphome\hiking-monitor-test\secrets.yaml`, `C:\esphome\hiking-monitor\secrets.yaml` (real device's local build dir), and `components/hiking-monitor/secrets.yaml` (repo copy, gitignored). **Not yet reflashed to either device** — the test rig went to sleep after its last successful test with no wake source wired, so it's currently unreachable for OTA (needs the GPIO32→3.3V wake trick, then OTA push, or a USB flash); the real field-deployed hiking-monitor is physically elsewhere and can't be reached at all right now. Both devices are **still running their old OTA password** until reflashed — the new password only exists in the secrets files so far, not on the hardware.

**WiFi/hotspot/AP/MQTT passwords: not yet touched.** Rotating the WiFi password in particular has a wider blast radius than device-specific secrets (likely shared across other devices/people on the network) — confirm actual scope/impact before rotating, not just swap the value.

**Done when:** all five secrets above are rotated to new values; both the test rig and the real field-deployed hiking-monitor are confirmed running the new OTA password (not just the secrets file updated); WiFi/hotspot/AP/MQTT rotation is either completed or explicitly deferred with a documented reason; and this card's "still running old password" gap is closed for both devices, not just the test rig.

---

### CARD-0077 · [bug] [photo-server] Weekly backup cron collided with Immich's nightly DB dump, causing stale-backup alert
**Notes:** Found 2026-07-22 via the CARD-0051 heartbeat check: `Immich degraded - backup:stale (10.3d since last success)`. Confirmed live via SSH — Docker containers all healthy, no data loss, disk usage normal on all three mounts (primary 73%, backups 39%/49%) — this was a stamp-write failure, not an actual backup outage.

**Root cause:** `photo-library-backup.sh` runs weekly via cron at `0 2 * * 0`. Immich's built-in nightly DB dump also runs at 02:00 daily (confirmed by `immich-db-backup-*-020000-*.sql.gz` filenames). On the 2026-07-19 run, rsync caught the DB dump's temp file mid-write/rename on both legs — Joseph's leg exited code 23, Robin's exited code 24 ("file has vanished... immich-db-backup-20260719T020000...sql.gz.tmp"), the same vanished-temp-file race already visible as a stale log entry from 2026-07-05. Since the script only touches `/home/jct/photo-library-backup-success.stamp` when both rsync legs return 0, this run's failure silently skipped the stamp (and correctly fired an MQTT "Backup failed" alert that apparently wasn't seen standing alone).

**Fix applied 2026-07-22:**
1. Rescheduled the cron entry from `0 2 * * 0` to `15 2 * * 0` (`crontab -e` on photo-server) so the weekly rsync starts 15 minutes after the DB dump, clear of the collision window.
2. Manually reran `/usr/local/bin/photo-library-backup.sh` to write a fresh success stamp and clear the alert immediately, rather than waiting a full week for the next scheduled run.

**Manual rerun confirmed clean 2026-07-22 09:39** — both rsync legs exited 0, stamp file updated (`/home/jct/photo-library-backup-success.stamp` now Jul 22 09:39), alert cleared.

**Done when:** the next scheduled run (Sunday 2026-07-26, 02:15) completes clean with no vanished-file errors, confirming the reschedule actually fixed the collision rather than this being a one-off clean retry.

---

### CARD-0070 · [enhancement] [hiking-monitor] Replace boost converter with LDO + gate peripheral power for lower standby draw
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

### CARD-0072 · [idea] [personal] Digital Identity Checklist Version 2
**Notes:** Raised 2026-07-17, split out from CARD-0034's closure as the next layer of hardening on top of the v1-done core (phone/SIM-swap single point of failure closed). Works through `digital-identity-protection-checklist.md`'s remaining open items, targeting v3.0 (checklist is currently at v2.1).

**Scope (in rough priority order):**
1. **ID document photo cleanup** — the new "ID document photos" section: RoboForm Identity digital copies of DL/passport, then find and delete scattered copies in Google Photos, Immich, camera roll, email/messages, including trash/recently-deleted retention windows. Live exposure, not a future risk — highest priority in this card.
2. **Robin's app-password and third-party app/service review** — Joseph's side is done; Robin's isn't, leaving an asymmetric bypass (app passwords skip 2FA entirely) on one account.
3. **Google Recovery Contacts** — set Robin ↔ Joseph and both children; unblocked for a while (kids confirmed independent adults) but never executed.
4. **Walk through the checklist together with Robin** — cheap, high-leverage: the household verbal protocol (codeword, voice-confirm-before-moving-money) only works if Robin actually knows it exists, not just that Joseph configured it.
5. **ChexSystems and LexisNexis freezes** — ChexSystems covers new bank-account fraud that the other 3 bureaus don't; worth troubleshooting the registration error rather than abandoning. LexisNexis is lower value (insurance underwriting/background checks) — decide deliberately whether to skip rather than leave it drifting.
6. **Remaining Phase 2 items:** "Skip password when possible" decision (currently under consideration), physically storing ID copies in the safe (Safe Contents manifest's one remaining open item), travel-copy/outside-contact-copy decision for the offline vault.
7. **Phase 4/5 prep:** print/place an offline copy of the Incident Response Plan somewhere actually accessible in an emergency; Phase 5 travel items can wait until a trip is actually upcoming.
8. **Accounts Without 2FA section** — blocked on listing specific banks/brokerages/payment apps in use (still an open item); needed before this section can be worked at all.

**Note:** Emergency Access and Google Inactive Account Manager are deliberately **not** in this card's scope — split out to CARD-0071.

**Related:** `digital-identity-protection-checklist.md` (repo root), `digital-identity.md` (companion reference doc).

---

### CARD-0009 · [enhancement] [hiking-monitor] Enclosure design and build
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

**Follow-up needed before `hiking-monitor-enclosure-plan.md` Section 0 can be updated to match:** these were live Tinkercad edits — exact new values weren't captured during the session. Section 0 exists specifically as the reproduction record (Tinkercad edits can't be replayed automatically), so it needs: the USB port's new wall/position, the new M3/solar hole diameters, what the removed "lip" was and why, and the floor reference line's exact position/dimensions relative to the perfboard. Get these from Joseph (re-opening the Tinkercad project or checking with calipers) before updating the plan doc.

**Next print planned: white ASA, Session 2** (`hiking-monitor-enclosure-instructions.md` Part 6, Steps 37+) — the final-material print per the doc's existing PLA-test-then-ASA-final pattern. Joseph's expectation going in: should be close given Session 1's fit corrections, with another print iteration available if needed. Section 0's dimension updates (above) should ideally be captured before Session 2 slices the files, so the ASA print reflects the corrected design rather than repeating any not-yet-documented fixes from memory.

---

## Done

### CARD-0075 · [enhancement] [hiking-monitor] Rename project from hiking-sensor to hiking-monitor throughout — RESOLVED 2026-07-21
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
**Notes:** Raised 2026-07-18. JCTsh's hiking-monitor pipeline already covers data collection (ESP32 sensors — BME280, LTR-390 UV; GPS track via Pixel GPSLogger) and data storage (GPS Track and Environmental Data Google Sheets, per CARD-0020). Hike-izer adds the missing layers on top: a controller layer (rules/analysis) and a rudimentary presentation layer, turning raw hike data into a narrative story of the hiking event rather than just charts.

**Relationship to CARD-0020:** complementary, not competing (Joseph's call). CARD-0020's Looker Studio dashboard stays scoped to raw charts/maps; Hike-izer's output is the narrative layer, generated from the same underlying Sheets data. Neither supersedes the other.

**Data source inventory (2026-07-18):** confirmed against the real pipeline code/docs, not assumption —
- **Environmental Data sheet** — full column set is A–Z, not A–X as `data-pipeline.md` previously (incorrectly) documented; `illuminance_lx`/`solar_v` were missing from that doc, now fixed.
- **Hiking Observations sheet — exists and works.** There IS a capture mechanism (Tasker voice-widget → Apps Script → auto-categorized row), built and field-confirmed in Steps 23–26.
- **GPS Track sheet** (via GPSLogger, not GaiaGPS — GaiaGPS was the superseded original plan and several docs still stale-reference it) — includes `alt` (altitude), which covers "height" without new hardware.
- **Timeline sheet** — existing manual-menu action already merges Environmental Data + Hiking Observations into one time-sorted sheet.
- **Compass/heading** — still a real gap, no sensor and not derivable cleanly from GPS Track alone (direction of travel ≠ which way the hiker was facing). Deferred, see scope below.
- Confirmed target trip for prototyping: the **2026-06-15 two-week trip**. GPS pipeline was redeployed 2026-06-12 (before the trip) so GPS Track data is very likely present; observations pipeline's exact completion date relative to June 15 isn't pinned down in the docs — check the real sheet before assuming observation rows exist for this window.

**Build step taken (2026-07-18):** extended `core/data-pipeline/environmental-data.gs` with a new read-only `action=export` on `doGet` — returns any sheet (Environmental Data / Hiking Observations / GPS Track) as JSON, optionally filtered by an ISO 8601 timestamp range, reusing the existing API_KEY auth. Documented in `data-pipeline.md`.

**Deployment saga (2026-07-18) — resolved.** The normal "Manage deployments → pencil → New version → Deploy" flow silently failed three times in a row: the Active deployment kept serving old code with zero errors, no indication anything was wrong. Root-caused by adding a `SCRIPT_VERSION` constant returned in every `doGet` response (including the "unknown action" fallback) — confirmed via `Deploy → Test deployments` (`/dev` URL, always runs Head/latest-saved code) that the *saved code* was correct the whole time; the problem was isolated specifically to the versioning step not promoting to the Active deployment. Fix: created an entirely new deployment (`Deploy → New deployment`) rather than continuing to fight the existing one — worked immediately, confirmed via `action=version` and a real `action=export` call that pulled all 6,202 real Environmental Data rows for the June 15 trip window.

**New deployment URL migrated everywhere the old one was referenced:** `credentials.local.md`, `data-pipeline.md`, Node-RED's `APPS_SCRIPT_URL` (found to live in `/home/pi/.node-red/environment`, a systemd `EnvironmentFile` — **not** the Node-RED editor's Settings → Environment Variables panel, which only covers flow/global-scoped vars, not OS-level ones; updated via SSH over Tailscale, `nodered` service restarted, verified via the live process's own `/proc/<pid>/environ` that the new URL is actually loaded, not just written to disk), and GPSLogger's custom URL setting on the Pixel (Joseph updated manually). Old deployment now fully unreferenced — left in place, harmless if idle.

**v1 scope — locked 2026-07-18 (Joseph's call, no separate Phase 1 planning doc; this card is the plan, given the scope's size — revisit if Hike-izer grows past v1 into photos/weather/automation):**
- **Mechanism:** a Claude Skill.
- **Trigger:** on-demand, with the **date/date-range as a prompt parameter** — not hardcoded to June 15. June 15 is the first test case, not the only one; Joseph may want to run this against other hikes later.
- **Inputs:** Environmental Data + Hiking Observations + GPS Track (lat/lon/alt), pulled for the requested date range via `action=export`.
- **Computed:** sun position (from lat/lon + timestamp), using GPS `alt` for height.
- **Output:** one Markdown document per run, including:
  1. A narrative story of the hike.
  2. Data tables/summaries as appropriate.
  3. **An explicit "expected vs. actual" data-coverage section** — not just an aside, a first-class part of the output. What was expected (sensor readings at ~2-min cadence, one observation stream, GPS trackpoints every ~30s, over the requested date range) versus what's actually present. This is meant to double as a health check on the whole hiking-monitor pipeline every time a summary is generated.
- **Explicitly deferred, not forgotten:** photos (Immich integration unbuilt), historical weather (no source picked), compass/heading (no data source), automatic triggering, rendered web page output.

**v1 built and verified end-to-end (2026-07-18).** Built as a real Claude Skill: `.claude/skills/hike-izer/SKILL.md` (instructions: determine date range, read credentials from `credentials.local.md`, run the fetch script, write the narrative in three parts, save to `hike-izer/summaries/`) plus `components/hike-izer/fetch_hike_data.py` (stdlib-only Python: fetches all three sheets via `action=export`, computes coverage stats, computes sun position via the NOAA/Meeus solar algorithm sampled along the GPS track). Code and generated output deliberately kept apart: code under `components/hike-izer/`, results under the top-level `hike-izer/summaries/` — so a future HTML presentation layer doesn't end up mixed in with source.

**Two real bugs found and fixed by testing against the real June 15 trip data, not left on paper:**
1. GPS Track's actual columns are `accuracy_m`/`altitude_m` (confirmed in `gps-pipeline.md`) — the script initially used `acc`/`alt`, silently returning `None` for every altitude. Fixed.
2. The GPS Track coverage calc originally compared point count against a full-date-range 30-second-cadence expectation, which produced a misleading "~1% coverage" — GPSLogger only runs during actual hikes, not continuously across a multi-day camping trip. Replaced with session detection (splits on >10min gaps, reports per-session coverage) — correctly showed 2 real sessions at 85.9% and 95.6% coverage instead of one alarming, wrong number.

**First real output generated:** `hike-izer/summaries/2026-06-15_hike-summary.md`. Genuine findings surfaced by the coverage section (not fabricated for demonstration) — UV index never exceeded 0.1 across the whole trip despite 110°F+ heat, consistent with the LTR-390 validation concern already tracked in CARD-0065; battery voltage dropped to 2.85V, lining up with the documented field LiPo failure (`README.md`, 2026-07-03); zero Hiking Observations rows despite the pipeline being confirmed working, worth a conscious check on whether the voice widget just wasn't used; only 2 GPS sessions (~4.3 hours total) detected across the full 2-week window. This is exactly the "awareness of how components are operating" goal from the original ask — not hypothetical, it found real things on the very first run.

**Second test round (2026-07-18), deliberately an edge case: today's date, still in progress.** Found and fixed two more real bugs:
3. **Future-window truncation.** Requesting a window extending into the future (e.g. today, before the day is over) computed "expected readings" against the full nominal window, producing a misleadingly low coverage % that wasn't a real problem. Fixed: `analyze_coverage` now caps the expected-calculation window at the actual current time when the requested end is in the future, and the output JSON carries `window_truncated_to_now` so the narrative can say so explicitly. `SKILL.md` updated to call this out when true.
4. **Cross-sensor contamination — more serious, and retroactive.** The Environmental Data sheet is shared across every JCTsh environmental sensor (`source` column distinguishes them), and the fetch script wasn't filtering by it. Testing today's date turned up 270 rows that were **entirely** `front-porch-temp-sensor`, not hiking-monitor — which would have been reported as hiking-monitor activity. Re-checked the already-published June 15 summary against this: **4,270 of its original 6,202 "hiking-monitor" rows were actually front-porch-temp-sensor.** Added a `--source` filter (default `hiking-monitor`) to `fetch_hike_data.py`, defaulting out any other source and reporting what else was seen but excluded. **`hike-izer/summaries/2026-06-15_hike-summary.md` regenerated with corrected numbers** (coverage 57.4%→17.9%, temp/humidity ranges narrowed, and a real ~10-hour Environmental Data gap on June 17 surfaced that had been masked by the other sensor's readings filling the same time slots) — the file carries its own correction note.

**Second real output, and a genuinely different kind of finding:** `hike-izer/summaries/2026-07-18_hike-summary.md`. Zero hiking-monitor Environmental Data readings all day, despite 7 Hiking Observations and 1 GPS point clearly showing a real walk happened (phone-based logging, no device). Since the same shared sheet has 270 `front-porch-temp-sensor` readings for the same day, this points at the hiking-monitor device itself (not deployed/charged/powered on?), not the pipeline — a different, useful class of signal than the coverage-percentage findings from the June 15 run.

**Model + presentation refinement (2026-07-18, Joseph's direction):**
1. **Feet is now the primary (only) unit for elevation** — `fetch_hike_data.py` converts `altitude_m` to `alt_ft`/`stats.altitude_ft` internally; the raw meters value from the sheet is never surfaced in output. Added a `compute_stats()` function to the script so temp/humidity/pressure/UV/battery/altitude ranges are computed once, consistently, rather than re-derived ad hoc each time.
2. **A hiking event is now defined as a single calendar day**, even a multi-day trip is a *series* of single-day events, not one combined report. `SKILL.md` rewritten around this: fetch the full requested range once, identify which individual days have real activity (a GPS session in practice), generate one `<date>_hike-summary.md` per active day. **Edge case handled:** a GPS session crossing UTC midnight (June 17 23:51 → June 18 02:59, confirmed real) is attributed to the day it *started*, not split into two partial, confusing day-summaries — verified by testing that querying June 17 alone only caught the first 8 minutes of that session.
3. **Non-redundant narrative rule added to `SKILL.md`:** the data table carries the numbers; the narrative synthesizes/interprets/draws conclusions rather than restating figures already sitting in a table two sections down.

**Summaries restructured to match:** the old combined `2026-06-15_hike-summary.md` (spanning the whole ~2-week query range) removed, replaced with `2026-06-17_hike-summary.md` and `2026-06-18_hike-summary.md` — the two actual hiking days, computed by partitioning the already-fetched dataset (Environmental Data bucketed by calendar day, GPS sessions attributed by start day) rather than re-querying per day, exactly as `SKILL.md` now prescribes. New finding from the properly-split data: **battery voltage declined day-over-day (3.97–4.36V on June 17 → 3.00–4.00V on June 18)** — a real trend, not noise, and an earlier data point in the same LiPo failure this trip is already known for.

**Hike-vs-not-a-hike classification added (2026-07-18, Joseph's direction).** Raised directly by the June 17 session: Joseph doesn't hike at night, so a gap-based GPS cluster alone isn't good enough evidence that a hike happened — it could be a drive, camp-site GPS drift, or (worth naming, since it's the actual constraint) genuinely happening in the dark. Added `_classify_hike()` to `fetch_hike_data.py`: every candidate GPS session must pass **both** a daylight check (≥80% of points at civil twilight or brighter, sun elevation > -6°) and a walking-pace check (median point-to-point speed 0.15–3.0 m/s / ~0.3–6.7 mph, computed via haversine distance) to count as `is_hike: true`. Sessions that fail carry `rejection_reasons` rather than being silently dropped — including a distinct "insufficient data" reason for single-point sessions (a session with 1 point has no speed pairs to compute; defaulting that to "0 m/s = stationary" would overstate what's actually known, so it gets its own honest reason instead). `coverage.gps_track.hike_confirmed` is `true` if any session that day passes both checks.

**Verified against real data both directions:** the two known-real hikes (June 17 evening, June 18 morning) both correctly classify `is_hike: true` (June 17's median speed came out to a low-but-passing 0.15 m/s — right at the threshold, consistent with a stop-and-start evening hike, not a red flag). July 18's lone GPS point correctly classifies `is_hike: false` with the new "insufficient data" reason rather than a misleading "stationary" one.

**`SKILL.md` updated with a new "What counts as a hike" section and an explicit "unable to confirm" output path** — when `hike_confirmed` is `false` for a requested day, the Skill must say so plainly and explain why (using the real `rejection_reasons`), rather than writing a normal hike narrative or silently producing nothing. `hike-izer/summaries/2026-07-18_hike-summary.md` rewritten to follow this path properly, now citing the actual classification output instead of the ad hoc framing used before this logic existed.

**Related:** `components/hiking-monitor/gps-pipeline.md`, `components/hiking-monitor/data-pipeline.md`, `components/hiking-monitor/hiking-logger.md`, CARD-0020 (Looker Studio dashboard, complementary).

**Resolution (2026-07-18):** closing as **version 1 done**. Core loop fully built and verified against real data, not left on paper: fetch → source-filter (`hiking-monitor` only) → hike classification (daylight + walking-pace checks, honest "unable to confirm" path when nothing passes) → single-day narrative with non-redundant tables and an explicit expected-vs-actual coverage/health section, elevation in feet throughout. Along the way, found and fixed real bugs — wrong GPS column names, misleading multi-day coverage math, future-window truncation, and cross-sensor contamination that had silently corrupted the first published summary — exactly the "awareness of how components are operating" goal from the original ask, working in practice, not hypothetically. Remaining ideas (photos, historical weather, hiker's compass/heading, automatic triggering, rendered HTML output) are real but represent v2, not blockers on calling v1 done — split out to **CARD-0074**, which also needs the hiking-monitor device itself operational again (it produced zero readings on 2026-07-18) before it can be built against fresh real data.

**Closed 2026-07-18 — Joseph directed the close.**

---

### CARD-0034 · [idea] [personal] Complete digital-identity-protection-checklist.md — RESOLVED 2026-07-17
**Notes:** Work through `digital-identity-protection-checklist.md` (repo root) — Joseph and Robin's personal security checklist closing single-point-of-failure risks (carrier port-out PIN, 2FA off SMS, credit freezes, password manager, household verification protocol, incident response plan). Almost entirely manual actions by Joseph/Robin themselves (phone calls to carriers/bureaus, account settings changes) — not something Claude Code can execute directly, but worth tracking to completion since it's currently all unchecked. Also has an "Open Items to Fill In" section (list specific banks/brokerages in use, confirm current password manager/2FA setup, set a 6-month review date) that needs input from Joseph before those parts can be finished.

**Blocked (2026-07-11):** waiting on delivery of Google Titan Security Key hardware authenticators (3 ordered) — needed for the hardware-key 2FA portion of the checklist before those items can be checked off.

**Resolution (2026-07-17):** closing as **version 1 done**, not "everything checked off" — the checklist reached v2.1 and the core mission (closing the phone/SIM-swap single point of failure the TIME article exposed) is solidly closed: carrier port-out locks on both lines, Google recovery phone and security question removed, recovery email cross-set between spouses, all 3 Titan keys ordered/registered on Google and RoboForm/PIN-set-and-tested/labeled/backed-up-in-the-safe, Google Account password and 2-Step Verification confirmed hardened with no phone-based fallback remaining, master password memorized redundantly by both Joseph and Robin, 3 of 5 credit bureaus frozen, and the household verbal-verification protocol agreed. Remaining open items (RoboForm Emergency Access + Google Inactive Account Manager, ID document photo cleanup, Robin's app-password/third-party-app review, Google Recovery Contacts, ChexSystems/LexisNexis, walking the checklist through with Robin, Phase 4/5 offline-copy prep) are real but represent the next layer of hardening, not blockers on calling v1 done — split out to CARD-0071 (Emergency Access preparation) and CARD-0072 (Digital Identity Checklist Version 2) rather than holding this card open indefinitely.

**Closed 2026-07-17 — Joseph directed the close.**

---

### CARD-0026 · [enhancement] [hiking-monitor] Measure hiking-monitor sleep-mode current draw — RESOLVED 2026-07-16
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

### CARD-0068 · [enhancement] [netalertx] Remove online/offline presence messages from the log — RESOLVED 2026-07-15
**Notes:** Raised 2026-07-14, follow-up to CARD-0063. With the translation flow live for a bit, the online/offline presence transition messages (`<device> came online` / `went offline`) turned out to be noisy and not actionable — mobile/known-flappy devices dominate, and even a real device flip doesn't carry enough context (how long, why it matters) to be worth a log line. New-device alerts and the heartbeat are working well and stay. No future use anticipated for presence data elsewhere (NetAlertX's own UI already covers online/offline if ever needed) — clean removal, not a toggle/config flag.

**Scope:** in `components/netalertx/netalertx.flow.json` — remove the `mqtt_in_netalertx_binary` node (`system-sensors/binary_sensor/+/state` subscription) and the `fn_presence` function node entirely. Also remove the `devinfo_<mac>` vendor/model caching in `fn_device_info`, since it only existed to label presence messages that won't exist anymore. New-device alert messages already build their label directly from the per-device sensor payload (`payload.model || payload.vendor`), not from that cache, so no functional change there. Heartbeat and new-device detection otherwise untouched.

**Progress (2026-07-14):** `netalertx.flow.json` updated (11 nodes, `mqtt_in_netalertx_binary` + `fn_presence` + dead `devinfo_<mac>` caching removed), `netalertx-README.md` updated to match, deployed to the live Node-RED instance via the tab-clear-and-reimport procedure. **Leaving open on Joseph's call** — wants to live with it for a few days before confirming the change actually feels right day to day, rather than closing on the first clean deploy. Resume here: check back after a few days that no online/offline messages have reappeared and new-device alerts/heartbeat are still behaving.

**Deploy verification note (2026-07-14):** checked the log dashboard right after deploy and initially saw presence messages at 20:36 (`Front Porch Sensor went offline`, etc.) — looked like the redeploy failed. Confirmed with Joseph there's only one NetAlertX tab, no duplicate flow; the 20:36 batch was actually from the last scan cycle *before* the redeploy, since scan cycles land roughly every 30 minutes and no new cycle had run yet at the time of checking. Real confirmation needs the *next* scan cycle (~21:06) to show no presence messages — not yet observed as of this note. Also surfaced (unrelated, not investigated): a watchdog alert `Component front-porch-temp-sensor silent for 35 minutes` at 20:59.

**Resolution (2026-07-15):** lived with it about a day as planned. No online/offline presence messages have reappeared since the redeploy — confirmed repeatedly, including incidentally during CARD-0069's investigation (which needed to read netalertx's real log history in detail and found only heartbeats and new-device alerts, no presence noise). New-device alerts and heartbeat continued working correctly throughout, including through CARD-0069's own restarts and redeploys of the log server itself. The change holds up in real use, not just on a clean deploy.

**Closed 2026-07-15 — Joseph confirmed and directed the close.**

---

### CARD-0069 · [bug] [infrastructure] log_server.py silently drops heartbeat-only components' messages — RESOLVED 2026-07-15
**Notes:** Raised 2026-07-15, found while checking on CARD-0068's netalertx changes at Xerocraft (accessed remotely via Tailscale). `netalertx` appeared completely silent on the log dashboard since 20:36 the prior evening — 14+ hours, no heartbeat displayed anywhere — despite `/status` showing it "Online, 4m ago." Root-caused directly on the Pi (SSH via Tailscale), not guessed:

1. Confirmed Node-RED's flow is healthy and correct — `netalertx.flow.json`'s wiring matches the source exactly (pulled the live `flows.json` and diffed against the repo copy), the watchdog's own timer-reset log entries prove the machine-readable heartbeat (`jctsh/components/netalertx/heartbeat`) fires every 5 minutes as designed.
2. Live-captured MQTT traffic with `mosquitto_sub` and directly observed a real `Heartbeat - 35 online, 0 down, 49 total, 1 new` message hit `jctsh/components/netalertx/log` — the publish is genuinely happening.
3. Confirmed via `state.json`'s mtime that `log_server.py` *does* receive and process the message (`_store_entry` runs to completion, updates `_last_seen` — which is why `/status` looked fresh) — but it never reaches `_entries` or the log file.

**Root cause:** `_store_entry()`'s heartbeat-collapsing logic (`core/logging/log_server.py`) only flushes a component's pending heartbeat group to the visible log when either (a) `_heartbeat_state_key()` detects a state change — only fires for ON/OFF-style or `Watchdog: `-prefixed messages, not netalertx's "N online, N down" text, which always collapses to the same key — or (b) a *different, non-heartbeat* message arrives from that component, which flushes the pending group as a side effect before processing the new one. There is no periodic/timeout-based flush anywhere — `_flush_all_hb_groups()` is only ever called from the server's shutdown path.

Before CARD-0068, netalertx's frequent online/offline presence messages incidentally served as that flush trigger, which is why heartbeats always eventually appeared. CARD-0068 removed those (correctly, per that card's own reasoning), leaving netalertx with *only* same-shape heartbeats and a rare new-device alert — nothing left to ever trigger a flush. The heartbeat group now accumulates silently in memory indefinitely. This is a latent gap in `log_server.py` that CARD-0068 exposed, not a defect introduced by CARD-0068's own change — any future component that only ever sends constant-text heartbeats (no periodic non-heartbeat traffic) would hit the same silent-drop behavior.

**Fix direction:** add a periodic background flush — a lightweight thread (similar to the existing `_heartbeat_thread`) that walks `_hb_groups` and flushes any group whose last update is older than a threshold, regardless of whether new traffic arrives. General fix, not netalertx-specific — protects any current or future heartbeat-only component.

**Correction while checking the live dashboard (2026-07-15):** the main `/` dashboard was actually **not** silent — `_snapshot()` already renders unflushed `_hb_groups` entries live, so netalertx's heartbeat was visible there the whole time, just as one never-rotating accumulating line (confirmed: `Heartbeat ×180 [20:41–11:31] — 35 online, 0 down, 49 total, 1 new` before the fix). The actual gap is narrower than first framed: the `/log` raw-text history, the persisted `state.json` (lost on restart), and `/status`'s "last message" column never update, because none of those read from the live in-memory group — only from `_entries`, which the group never reaches without a flush trigger. Root cause and fix direction are unchanged; only the "completely silent" framing needed correcting.

**Implemented and deployed (2026-07-15):** added `HB_GROUP_STALE_SEC` (900s) and a new `_hb_flush_thread` (checks every 60s via `HB_FLUSH_CHECK_INTERVAL`) that calls `_flush_stale_hb_groups()` — walks `_hb_groups`, flushes any group whose `_last_update` (new field, stamped on every heartbeat update) is 15+ minutes stale, regardless of whether new traffic arrives. Also generalized the internal-field filtering in `_flush_hb_group`, `_save_state`, and `_snapshot` from the narrow `k != "_state_key"` check to `not k.startswith("_")`, so the new `_last_update` field (and any future internal field) doesn't leak into persisted state or rendered output automatically.

Deployed via `scp` to the Pi, syntax-verified (`py_compile`), `sudo systemctl restart jctsh-logging`. The restart itself exercised the existing shutdown-flush path and correctly wrote the accumulated `Heartbeat ×180 [20:41–11:31]` group to `jctsh.log` for the first time — direct proof the flush mechanism works end-to-end, not just unit-level reasoning. Going forward, new heartbeat groups will self-flush every ~15 minutes instead of accumulating indefinitely.

**Regression check across other components (2026-07-15) — bug turned out to be system-wide, not netalertx-specific.** The same restart-triggered flush surfaced multi-hour stuck heartbeat groups for *every* other component, not just netalertx:
- `garage-radar`: `Heartbeat ×11 [06:18–11:18]` — 5 hours stuck (its heartbeat only flushes on an actual presence ON/OFF flip in the message text; Sensor-category presence-detected/cleared messages are explicitly excluded from triggering a flush, by design, so a long stretch of steady presence never flushed)
- `salt-sensor`: `Heartbeat ×41 [15:28–11:28]` — 20 hours stuck
- `front-porch-temp-sensor`: `Heartbeat ×29 [21:04–11:04]` — 14 hours stuck
- `photo-server`: `Heartbeat ×41 [15:07–11:09]` — 20 hours stuck

All five flushed cleanly with formatting identical to the pre-fix collapse pattern (`Heartbeat ×N [start–end] — ...`) — no corruption, no stray internal fields leaking, no double-counting. This confirms the fix is a genuine systemic correction (every component's history was going stale for arbitrarily long stretches whenever nothing flush-triggering happened to occur), not a netalertx-only patch, and validates itself against real production data across five components at once rather than just netalertx's case. No regressions found.

**Real bug found in the first fix itself (2026-07-15, checked ~4 hours later per Joseph's request).** No new flush had happened in almost 4 hours — the first implementation was broken. Root cause: it compared elapsed time against `_last_update`, a field stamped on **every** incoming heartbeat, including the "same state, update in place" branch. Since netalertx heartbeats arrive every 5 minutes without fail, `_last_update` never got more than ~5 minutes old — the staleness clock kept getting reset by the very heartbeats it was supposed to eventually flush, so the group could never reach the 15-minute threshold. Functionally identical to the original bug this card exists to fix, just with a much longer (but still infinite) timeout.

**Corrected (2026-07-15):** switched from an idle-time check (`_last_update`, refreshed every message) to an age-based check (`_started_at`, stamped only once when a group is first created, never touched again). `_flush_aged_hb_groups()` (renamed from `_flush_stale_hb_groups`) now flushes a group once it's been open `HB_GROUP_MAX_AGE_SEC` (900s), regardless of how recently it was last updated — forcing periodic rotation even for a component that heartbeats forever without ever going quiet.

**Live-verified with a fast, deterministic test rather than another blind multi-hour wait** — temporarily dropped `HB_GROUP_MAX_AGE_SEC` to 90s (same "shorten the timeout, verify, restore" pattern the watchdog flow's own README already documents for testing its 35-minute timeout), redeployed, and within ~5 minutes observed a brand-new group (a single fresh heartbeat, `count=1`, no `×N [range]` collapse — proof it hadn't been accumulating) get flushed immediately once it crossed the 90-second age mark: `2026-07-15 15:16:20 MST | netalertx | System | Heartbeat - 39 online, 0 down, 49 total, 1 new`. This is unambiguous proof the age-based flush fires independent of continued traffic, not just reasoning about the code. Restored `HB_GROUP_MAX_AGE_SEC` to 900, redeployed, confirmed service running cleanly.

**Confirmed at real production cadence (2026-07-15).** A fresh group formed right after the 15:21:11 restart and self-flushed exactly 15 minutes later with no manual trigger, no shortened threshold, no other message arriving to force it: `2026-07-15 15:36:20 MST | netalertx | System | Heartbeat ×4 [15:21–15:36] — 39 online, 0 down, 49 total, 1 new`. This is the real-world confirmation the card was waiting on — mechanism verified at both the fast test threshold and the actual production threshold. All closing criteria met: fix implemented, deployed, a genuine bug in the first attempt found and corrected, verified live twice (fast deterministic test + real cadence), and regression-checked clean across every other component (garage-radar, salt-sensor, front-porch-temp-sensor, photo-server).

**Resolution:** `log_server.py`'s heartbeat-collapse logic now rotates any pending group after 15 minutes regardless of continued traffic, closing a systemic gap that was silently truncating history for every component, not just netalertx. Verified live at both a fast test threshold and the real 15-minute production cadence, with a genuine bug in the first fix attempt found and corrected along the way rather than assumed working.

**Closed 2026-07-15 — Joseph confirmed and directed the close.**

---

### CARD-0060 · [bug] [infrastructure] Pi running in active soft thermal throttling &mdash; no cooling &mdash; RESOLVED 2026-07-15
**Notes:** Found 2026-07-12 during a Pi health evaluation. `vcgencmd get_throttled` returns `0x80008` (bit 3: soft temperature limit *currently active*; bit 19: has occurred) at a measured 63&ndash;64&deg;C, confirmed on two separate checks. No under-voltage bits set &mdash; power supply is fine, this is purely thermal. No heatsink/fan apparent on this Pi 3B+. Likely compounded by an enclosed/warm install location, matching the pattern of other JCTsh closet-installed devices (photo-server M8, KeepConnect).

**Impact:** the Pi is right now running with reduced ARM clock speed to manage heat. Not causing instability (uptime is solid, no OOM/crash pattern), but is a real, currently-active performance ceiling on the device that hosts Home Assistant, Node-RED, Mosquitto, and the JCTsh log/watchdog server for the whole fleet.

**Location context (2026-07-12):** the Pi sits on a shelf near a 9-foot ceiling in the laundry room, in a plastic case of unknown internal heatsink status &mdash; Joseph doesn't want to open the case to check/add an internal heatsink. Chose an external-airflow approach instead of a case teardown: some of the heat load is plausibly ambient hot air pooling at ceiling height (heat rises) rather than purely the case trapping the Pi's own heat, so moving air across the whole shelf addresses both causes at once and benefits every device up there, not just the Pi.

**Resolution path (revised, no disassembly):** install a continuous-duty USB-powered fan on the shelf, aimed to move air across the shelf and out toward open room space (not just recirculate warm air in place against the ceiling). Recommended: **AC Infinity MULTIFAN S5** (single 80mm, ~52 CFM, dual ball bearings rated ~67,000 hours/~7.6 years continuous duty, USB powered, includes speed controller) &mdash; purpose-built for quiet electronics-cabinet cooling, enough real airflow to matter across an open shelf, unlike gentler terrarium-style USB fans. Step up to the **MULTIFAN S7** (multi-fan set) if one fan's throw doesn't cover the full shelf width. Power the fan from its own USB wall adapter or hub, not from the Pi's own USB ports, to avoid adding current draw to the Pi's own power rail (it currently shows no under-voltage flags &mdash; keep it that way). One ongoing maintenance item: it's a laundry room, so dryer lint will accumulate on the fan grille/blades over months of continuous running &mdash; an occasional wipe-down keeps airflow effective.

**Don't close until:** fan is physically installed and `vcgencmd get_throttled` is re-checked under normal and sustained-load conditions, confirming bit 3 ("soft temperature limit currently active") clears. **Holding verification until Joseph has the fan in place** &mdash; not yet done.

**Pre-install baseline (2026-07-14):** checked temps across the equipment shelf before the fan goes in, both to confirm the Pi's condition is unchanged and as a data point on the shelf-wide-heat-pooling theory.

- **Pi:** 64.5&deg;C, `throttled=0x80008` &mdash; unchanged from the 2026-07-12 finding, still actively soft-throttling.
- **M8 (photo-server), also on this shelf:** running well within normal range &mdash; CPU (real `k10temp` sensor, not the unreliable `acpitz` dummy) 39.3&deg;C, NVMe 40.9/41.9/33.9&deg;C, GPU 38.0&deg;C, 2.5GbE controllers 39.5/43.5&deg;C, WiFi 6E 38.0&deg;C. Worth noting against the shelf-wide-heat-pooling theory: if ambient heat pooling at ceiling height were the dominant factor, expected the M8 to be running warmer too. Doesn't rule the theory out &mdash; the Pi's plastic case with no heatsink at all is far more heat-sensitive than the M8's own active cooling &mdash; but the M8 isn't showing any distress from the shared shelf environment.
- **External USB HDDs (Backup Plus, Momentus, spare Seagate) &mdash; could not check:** needs `smartctl`, not installed; `sudo` on the M8's `jct` account requires an interactive password not available here.
- **Router (TP-Link Archer AXE75) &mdash; could not check:** no SSH/API access on this consumer router; admin web UI already confirmed undrivable via browser automation during CARD-0003.

**Post-install check (2026-07-14, a few hours after fan install):** significant improvement.

- **Pi:** 64.5&deg;C &rarr; **48.9&deg;C** (15.6&deg;C drop). `throttled`: `0x80008` &rarr; **`0x80000`** &mdash; bit 3 ("soft temperature limit *currently active*") is now clear, meeting the card's closing criteria. Remaining bit 19 is just the sticky "has occurred since boot" historical flag; it stays set until next reboot regardless of current temp and doesn't indicate ongoing throttling.
- **M8:** unchanged, still healthy (CPU 39.1&deg;C, NVMe 41.9&deg;C, GPU 37.0&deg;C) &mdash; as expected, confirms it was never the concern.

**Still open before closing:** this check was under normal conditions a few hours post-install, not explicitly a sustained-load test as the closing criteria also calls for. Pi's steady 24/7 workload (HA, Node-RED, Mosquitto, log/watchdog server) arguably already constitutes real sustained load rather than a synthetic spike, but worth a check-in after a longer period (a day or more) to confirm bit 3 stays clear rather than closing on a single few-hours-later reading.

Joseph is installing the fan next; re-check `vcgencmd get_throttled` afterward per the closing criteria above.

**Progress (2026-07-12):** Joseph ordered the **AC Infinity MULTIFAN S7** &mdash; dual 120mm (larger than the single-80mm S5 suggested above), UL-certified, marketed for receiver/DVR/console/computer cabinet cooling. Larger fans, more shelf coverage &mdash; a reasonable upgrade over the original suggestion. Not yet installed; verification still pending arrival/install.

**Sustained-load re-check (2026-07-15), checked remotely via Tailscale (Joseph at Xerocraft):** roughly a day after the 2026-07-14 post-install check, under the Pi's normal steady 24/7 workload &mdash; the sustained-load condition the earlier check was missing.

- **Pi:** `throttled=0x80000` &mdash; bit 3 ("soft temperature limit *currently active*") still clear, confirming the 2026-07-14 result wasn't a fluke. Temp **47.2&deg;C**, consistent with the post-install reading (48.9&deg;C), not drifting back up. Bit 19 remains set (sticky "has occurred since boot" flag) &mdash; expected, clears only on next reboot, not a sign of ongoing throttling.
- **M8 (photo-server):** still healthy &mdash; CPU (`k10temp` Tctl) 40.8&deg;C, GPU 36.0&deg;C, NVMe 40.9/31.9&deg;C, 2.5GbE 41.5/37.0&deg;C, WiFi 6E 34.0&deg;C. `lm-sensors` was reinstalled on photo-server for this check (it wasn't present in this session; installed via `apt-get install lm-sensors`, same real `k10temp` source as the 2026-07-14 baseline, not the unreliable `acpitz` dummy).

**Resolution:** fan install (AC Infinity MULTIFAN S7) confirmed effective across two separate checks a day apart &mdash; both under real sustained load, not just a synthetic spike. Soft thermal throttling is no longer active. Closing criteria fully met.

**Closed 2026-07-15 &mdash; Joseph confirmed and directed the close.**

---

### CARD-0063 · [idea] [infrastructure] NetAlertX MQTT event richness experiment + log dashboard wiring — RESOLVED 2026-07-14
**Notes:** Raised 2026-07-12, deferred from CARD-0059. Whether NetAlertX's MQTT plugin publishes rich, human-readable event text (new device / down / reconnected, with name/MAC/IP) or only structured Home-Assistant-discovery-style state (per-device online/offline binary sensor + aggregate counts) is genuinely unclear from the docs — there was an open GitHub feature request (#1339) to bring MQTT up to webhook-level richness, closed with a "next release/in dev image" label, but not confirmed against the exact `ghcr.io/netalertx/netalertx:latest` image pulled for this deployment.

**Resolution path — a 5-minute live test, not more research:** enable the MQTT plugin in NetAlertX's Settings, point it at the `netalertx` broker account (`credentials.local.md`), unplug or disconnect something on the LAN, and watch what actually publishes to the Pi's Mosquitto broker (`mosquitto_sub -u netalertx -P ... -t '#'` or similar). That resolves the uncertainty directly.

**If rich event text comes through natively:** straightforward — point it at `jctsh/components/netalertx/log` (or translate topic if NetAlertX's own topic naming doesn't match) and it shows up on the existing log dashboard like every other component.

**If it's state-only:** needs a small Node-RED translation flow — subscribe to NetAlertX's HA-discovery-style topics, detect the online/offline transitions and new-device flags, and republish as proper `{"component":"netalertx","category":...,"message":...}` JSON to the `jctsh/` topic the log dashboard expects.

**Sequencing gate cleared (2026-07-14):** originally deferred until NetAlertX was "lived with for a while — checked periodically, devices named as new ones show up, genuinely relied on instead of ignored." CARD-0064's 2026-07-13 session (every NetAlertX-reported device identified, using and validating the documented naming workflow) plus a real performance bug found and fixed (scan schedule widened from `*/5` to `*/30 * * * *`, resolving the sluggish-UI issue) together satisfy that bar — moved from Backlog to Planning.

**Live test run (2026-07-14) — question resolved: state-only, not rich text.** Enabled the MQTT publisher plugin (`MQTT_BROKER=192.168.1.117`, `MQTT_USER/PASSWORD=netalertx` account, `MQTT_RUN=always_after_scan`), temporarily shortened `ARPSCAN_RUN_SCHD` to `*/5 * * * *` for faster iteration during testing, then captured the actual publish via `mosquitto_sub` on the Pi. Confirmed three message shapes per scan cycle, none containing human-readable text:
1. One aggregate sensor — `system-sensors/sensor/netalertx/state`: `{"online": 39, "down": 0, "all": 47, "archived": 0, "new": 1, "unknown": 1}`
2. One `sensor` topic per device (~47) — raw attributes: `{"last_ip":..., "is_new":"0", "alert_down":"0", "vendor":..., "model":..., "last_connection":..., "first_connection":..., ...}`
3. One `binary_sensor` topic per device — `{"is_present": "ON"/"OFF"}`

Topic root `system-sensors` confirms this plugin targets Home Assistant's community "system-sensors" MQTT convention specifically, not a generic/human-readable event feed — matches the "state-only" branch anticipated above, not the "rich event text" branch. **~95 messages publish every single scan cycle regardless of whether anything changed** — worth designing the translation flow to diff against previous state and republish only real transitions, not mirror all ~95 messages every cycle, which would flood the log dashboard with noise.

**Real snag hit during setup, not blocking:** the MQTT plugin was invisible in Settings' Publishers overview (which only lists already-*enabled* publishers via a `<PREFIX>_RUN != disabled` filter) until found via the full Settings search instead. Also found `RUN=once` mode is a process-lifetime flag (only fires on the very first main-loop iteration after container start, not on save) — not useful for ad hoc testing; `always_after_scan` was used instead and is very likely the right mode for production too. Also hit a stuck "Importing settings and reinitializing..." frontend spinner after one save — backend stayed healthy throughout (confirmed via `docker stats`/logs, actively serving other requests); resolved with a hard refresh, not a real problem.

**Schedule reverted (2026-07-14):** `ARPSCAN_RUN_SCHD` confirmed back to `*/30 * * * *` (verified directly in `app.conf`); `MQTT_RUN=always_after_scan` left in place. **Moved to Build (2026-07-14)** — past experimentation, into actual implementation.

**Scope expanded (2026-07-14) — health/heartbeat, not just event translation.** Directly resolves the `?` status found on the JCTsh log dashboard's Device Status page: `netalertx` currently has no `Heartbeat - `-prefixed message in its log history (only a stray one-off from CARD-0059's original MQTT connectivity test), so `log_server.py`'s `_compute_status()` can never classify it as Online/Offline — it falls back to `?` (see `core/logging/log_server.py` around line 508-518: status defaults to `?` when `has_hb` is false). The Node-RED flow should publish a periodic heartbeat message (matching every other component's `Heartbeat - uptime: ..., ...` pattern) alongside the event-transition translation, not just the latter.

**Remaining work:**
1. Design and build the Node-RED translation flow per the "state-only" resolution path above — diff against previous state, republish only real transitions (not all ~95 messages every cycle) as proper `{"component":"netalertx","category":...,"message":...}` JSON to the log dashboard's expected topic.
2. Add a periodic health/heartbeat message for `netalertx` itself (uptime or last-successful-scan-based, matching the `Heartbeat - ` prefix convention every other component uses) so it gets a real Online/Offline status instead of permanently showing `?`.

**Flow built (2026-07-14):** `components/netalertx/netalertx.flow.json` + `components/netalertx/netalertx-README.md` written, following `watchdog.flow.json`'s node/style conventions and referencing the shared `mqtt_broker` config node from `core.flow.json`. Design:
- Two `mqtt in` nodes subscribe to NetAlertX's raw `system-sensors/sensor/+/state` and `system-sensors/binary_sensor/+/state`.
- `fn_device_info` caches per-device vendor/model attrs and the scan-wide aggregate stats (from the one `.../sensor/netalertx/state` topic mixed into that same subscription), and fires a one-time `category: "Alert"` "New device detected" message when `is_new` flips on for a MAC it hasn't already flagged (clears the flag if NetAlertX later clears `is_new`, so a genuine future re-appearance can fire again).
- `fn_presence` diffs each device's `is_present` against Node-RED context and only emits a `category: "System"` came-online/went-offline message on an actual flip — first sighting after a Node-RED restart just sets the baseline silently, avoiding a false "everyone came online" burst.
- Both feed `jctsh/components/netalertx/log` (plus a debug sidebar node for initial verification).
- `inject_heartbeat` fires every 5 minutes (matches every other component's cadence and the watchdog's 35-min/7-heartbeat timeout) → `fn_heartbeat` builds a `Heartbeat - N online, N down, N total` message to `.../log` and a small stats payload to `jctsh/components/netalertx/heartbeat`, which the watchdog's `jctsh/+/+/heartbeat` wildcard picks up automatically — no watchdog-side changes needed.

JSON validated (`ConvertFrom-Json`, 13 nodes). **Not yet imported/deployed to the running Node-RED instance on the Pi** — next step is importing via Node-RED's own UI/admin API (not a simple file copy+restart like the Python log server) and verifying live against a real scan cycle per the Testing section of `netalertx-README.md`.

**Deployed and verified live (2026-07-14).** Imported into the running Node-RED instance via the editor's Import dialog (new tab, deployed). Two real bugs found and fixed during live verification, both harvested back into `netalertx.flow.json`:
1. **Double-JSON-parse.** The `mqtt in` nodes use `datatype: "auto-detect"`, which already parses valid JSON payloads into objects — the function nodes were then calling `JSON.parse()` on those objects again, throwing on every single message (`"Bad JSON on ..."` for all ~47 devices). Fixed by only parsing when `typeof payload === 'string'`.
2. **Node-scoped vs. flow-scoped context.** `fn_device_info` cached `agg_stats` and `devinfo_<mac>` via `context.get`/`context.set`, which defaults to a *node-private* store in Node-RED — `fn_heartbeat` and `fn_presence` are different nodes, so they were reading their own empty private context and never saw what `fn_device_info` wrote. Symptom: heartbeat stuck on "no scan data yet," transition messages showed raw MAC addresses instead of device names. Fixed by switching all cross-node cache keys (`agg_stats`, `devinfo_<mac>`, `newflag_<mac>`, `presence_<mac>`) to `flow.get`/`flow.set`.

After the fix, live-verified end to end: heartbeat shows real stats (`Heartbeat - 37 online, 0 down, ...`), real presence transitions logged with correct device names via the cached vendor/model lookup (`Front Porch Sensor`, `Water Valve Controller`, `Ring Doorbell`, `View Fence Camera`), the watchdog's `jctsh/+/+/heartbeat` wildcard picked up `netalertx` automatically with zero watchdog-side changes, and `curl .../status` confirms the Device Status page now shows `netalertx` as **Online** instead of `?`. Both original scope items (translation flow + heartbeat) are done and confirmed working against real data, not just deployed.

**Files relocated (2026-07-14):** originally placed under `core/node-red/` by directly mirroring `watchdog.flow.json`'s location, but that doesn't match the actual convention — `garage-radar.flow.json`, `hiking-hike-events.flow.json`, and `salt-sensor.flow.json` all live inside their own component directory, not centralized; `core/node-red/` is really reserved for genuinely cross-cutting infrastructure (the shared broker, the all-component watchdog). Moved `netalertx.flow.json` + `netalertx-README.md` to `components/netalertx/` to match. `Node-RED-workflow.md`'s tracking table updated to reflect actual file locations for all flows, not just the two that happened to live in `core/node-red/`.

**Resolution (2026-07-14):** the state-only vs. rich-text question was resolved by direct MQTT capture (state-only, matching Home Assistant's "system-sensors" convention), the translation flow was designed, built, deployed to the Pi's Node-RED instance, and verified against real live data — including finding and fixing two real bugs (double-JSON-parse against `auto-detect` payloads, node-scoped vs. flow-scoped context breaking cross-node caching) rather than declaring success after a clean-looking deploy. `netalertx` now reports real transition/new-device events and a working heartbeat; the log dashboard's Device Status page confirms **Online** instead of the long-standing `?`.

**Closed 2026-07-14 — Joseph confirmed and directed the close.**

---

### CARD-0064 · [enhancement] [netalertx] Device checking & naming workflow — RESOLVED 2026-07-14
**Notes:** Raised 2026-07-12. CARD-0059 deployed NetAlertX and confirmed the one-time naming setup works, but never established a *repeatable* process for ongoing use &mdash; and CARD-0063 explicitly holds off further NetAlertX/dashboard integration work until the tool is "checked periodically, devices named as new ones show up, genuinely relied on instead of ignored." This card is that missing piece: a concrete, repeatable workflow, not another one-time pass.

**Content:** `components/netalertx/naming-workflow.md` &mdash; access details, a weekly check cadence, the actual per-device steps (vendor-guess first, cross-reference `jctsh-network.md` before assuming a device is new, assign a name/icon), a documented gotcha (Android/iOS MAC randomization can make one physical phone look like repeated "new" devices unless switched to a stable per-network MAC), and an explicit rule against naming drift between NetAlertX and `jctsh-network.md` for devices that exist in both.

**Don't close until:** Joseph has reviewed `components/netalertx/naming-workflow.md` and confirmed it matches how he actually wants to work the tool &mdash; and, per CARD-0063's own sequencing note, this needs to hold up over real periodic use before being treated as done-done, not just a plausible process on paper.

**Progress (2026-07-12):** First real usability pass surfaced a genuine bug rather than a naming-workflow question: nearly every device on the Devices list showed "Offline" despite `SCAN_SUBNETS` (`192.168.1.0/24 --interface=eno1`) and the ARPSCAN plugin working correctly &mdash; confirmed via Maintenance logs, which showed clean hourly scans finding ~33 real devices (including the SmartThings Hub at `192.168.1.112`, MAC `24:fd:5b:01:72:23`). Root cause: `Settings &rarr; General &rarr; TIMEZONE` was left at the default `Europe/Berlin` instead of `America/Phoenix`, throwing off the online/offline recency comparison. Corrected to `America/Phoenix`. After the fix, most ARPSCAN-detected devices flipped from "Offline" to "Flapping" &mdash; expected, since the timezone correction created a one-time discontinuity in each device's last-seen timeline (read as a flap) on top of NetAlertX only having a few hours of real scan history so far. Should settle to steady "Online" for wired/always-on devices (router, Pi, SmartThings hub) over the next several scan cycles.

**Follow-up needed:** re-check the Devices list after several more scan cycles. If wired/always-on devices are still "Flapping" at that point (not just newly-added Wi-Fi/IoT devices), investigate the flap-detection window/threshold setting rather than assuming it's still settling.

**Progress (2026-07-13):** Login stopped working &mdash; submitting the password just blanked the field and re-presented the login dialog, no error shown. Diagnosed directly on photo-server rather than guessing: confirmed `SETPWD_password` hash was correctly stored, confirmed php-fpm's socket and PHP session storage were both working correctly (session files were being created in `/tmp/run/tmp` on every login attempt) &mdash; ruled out the `read_only: true` container hardening as the cause. The empty (0-byte) session files on failed attempts pointed to the login POST being rejected outright, i.e. a real password mismatch, not a plumbing failure. Temporarily disabled login (`SETPWD_enable_password=False` in `data/config/app.conf`, then `docker compose restart`) so Joseph could test without being locked out. Confirmed: the original password (`@eBPk^d68qo^LA6n`) never worked at login; switching to an alphanumeric-only password (no `@`/`^`) fixed it immediately. Login re-enabled with the working password; `credentials.local.md` updated (gitignored, not committed here).

**Real usage session (2026-07-13):** Joseph worked through identifying every device NetAlertX reported, using the documented workflow (vendor-guess first, cross-reference `jctsh-network.md`) plus a few new techniques worth folding back into `naming-workflow.md`: checking the Google Home app's per-device "Device information" section for MAC address as a positive cross-reference (more reliable than IP, since MAC is stable across DHCP renewals), and elimination-by-OUI for a non-Google device (Rain Bird ESP-TM2 irrigation module, Espressif-based, identified as the only unnamed Espressif-vendor device once all known JCTsh components were excluded). Also fixed two "(Unknown: locally administered)" entries by turning off MAC randomization on the affected phone/tablet for the home network — confirming the exact gotcha the doc already flagged. **Result: all NetAlertX-reported devices identified.** This is real evidence toward the "genuinely relied on, not ignored" bar CARD-0063 set as the trigger for further integration work.

**Separate finding — real performance bug, not yet confirmed fixed:** the plugin scan pipeline (ARPSCAN/SYNC/INTRNT, all scheduled `*/5 * * * *`) was found running nearly back-to-back with almost no idle time (~5m11s cycle time against a 5-minute schedule), causing SQLite lock contention that made the whole web UI (including the Settings page) sluggish. Root cause confirmed via log timestamps and `docker stats`/`uptime` (M8 itself was nearly idle — load 0.09–0.27 on 12 cores — ruling out host resource starvation; the bottleneck is I/O contention from near-continuous scanning, not CPU/RAM). Fix recommended: widen the three schedules to `*/30 * * * *`. **Could not apply directly** — the container's hardened setup (`ReadonlyRootfs: true`, dropped capabilities from the original CARD-0059 deploy) blocks even `docker exec` as root from writing `app.conf`; needs to go through NetAlertX's own Settings UI instead. **Confirmed applied (2026-07-14)** — Joseph made the change through the Settings UI.

**Resolution (2026-07-14):** folded a third real-usage technique into `naming-workflow.md` — the Google Nest app's per-device "Device information" MAC lookup (separate app from Google Home; positively identified two "(name not found)" Google-vendor entries as Nest Protect smoke detectors) — alongside the Google Home app MAC cross-reference and OUI-elimination techniques already noted. New "Identification techniques" section added to the doc, dated 2026-07-13/14. Both closing criteria now met: the workflow held up over real periodic use (every NetAlertX-reported device identified, a real performance bug found and fixed along the way), and the doc has been reviewed/refined based on that actual use rather than left as an untested plan on paper.

**Closed 2026-07-14 — Joseph confirmed and directed the close.**

---

### CARD-0049 · [enhancement] [salt-sensor] Move from breadboard to perfboard — RESOLVED 2026-07-13
**Progress (2026-07-10):** Follow-on to CARD-0004 (ESPHome migration). Moved all three LEDs off their original breadboard pins onto a perfboard-friendly layout: Red GPIO2→GPIO32, Yellow GPIO15→GPIO33, Green GPIO4→GPIO27 — gets Red/Yellow off strapping pins entirely and lines all three LEDs up on the same header row (left pins 7/8/11) for easier soldering. GPIO25/26 (DAC1/DAC2) were considered since they sit physically between GPIO32/33 and GPIO27, but ruled out — GPIO25 is confirmed broken for digital output in ESPHome/Arduino, GPIO26 avoided as a precaution for the same DAC-reinit reason. Trig (GPIO5) and Echo (GPIO18) unchanged.

Updated `salt-sensor.yaml` (wiring comment + `output:` block), `components/salt-sensor/CLAUDE.md`, and `components/salt-sensor/ESP32-project-pins.md` to match. Physical rewiring done; reflashed over OTA and field-verified — LEDs confirmed matching the `ok` status (green solid, red/yellow off) on the new pins, MQTT `/data` and `/status` reporting normally post-flash.

**Planning (2026-07-13):** wrote `components/salt-sensor/perfboard-layout.md` — modeled on hiking-monitor's perfboard-layout.md (Assembly Sequence → Pre-Power Checks → power-on/reboot verification), scaled down for salt-sensor's much simpler circuit (no I2C, no battery chain, no display). Worked through bus planning explicitly before the soldering steps: a ground bus is warranted (5 consumers: 3 LEDs, JSN-SR04T GND, Echo divider) and gets built with 2 spare tap points for future additions; a 5V/VIN bus is *not* warranted (only one consumer beyond the source — a direct point-to-point wire is equivalent and simpler); confirmed no other net (each LED drive line, Trig, Echo) has 3+ consumers, so no other bus is warranted either. 12-step assembly sequence, 18-check pre-power continuity/resistance table, and an explicit power-cycle verification section (cold USB unplug/replug, not just an OTA soft reboot — twice clean, minimum) all written into the doc.

**Build (2026-07-13):** Soldered per `perfboard-layout.md`'s Assembly Sequence — walked step by step interactively (each solder joint confirmed before proceeding to the next).

**Real issue found and fixed:** the physical ESP32 board in hand is a **SparkleIoT XH-32S** module, whose silkscreen pin *order* doesn't match `ESP32-project-pins.md`'s documented position numbering — same GPIO count, different physical layout, despite both nominally being "38-pin ESP32 DevKitC-32" boards. This wasn't caught until mid-build: the Trig wire had been soldered to the pad labeled `RX2` instead of `D5` (the two sit adjacent in a crowded cluster — `D18, D5, TX2, RX2, D4`), found only because Pre-Power Checks were done by reading the actual printed labels rather than trusting the documented table. Fixed by re-soldering Trig to the correct `D5` pad. `D18` (Echo) was double-checked at the same time and confirmed correct. Reference photo of the actual board saved to `components/salt-sensor/sparkleiot-xh-32s-pinout-photo.jpg`.

**Pre-Power Checks:** 19 checks run (not the originally-planned 18) — 2 checks from the hiking-monitor-derived template were dropped as not applicable (this board has no separate USB power-in header; power enters through the ESP32's own onboard USB port), and 3 new isolation checks were added on the spot (`D32`↔`D33`, `D5`↔`D18`, `D5`↔`RX2`, each expected open/no-beep) prompted directly by the `RX2`/`D5` mistake — confirming no solder bridge existed between visually-adjacent pins. **All 19 passed.**

**Power-on test:** LED self-test observed, `Online — ESPHome 2026.4.5, IP: 192.168.1.181, MQTT connected`, `/data` publishing `Salt: 95% (21.5 cm)` — same value as CARD-0049's original 2026-07-10 breadboard field verification, confirming the Echo divider (part of what got fixed) is producing sane readings. LED status confirmed matching (`ok` → solid green, red/yellow off).

**Resolution — reboot/power-cycle verification:** two clean cold power-cycles (physical USB unplug/replug, not just an OTA soft reboot, since this board is USB-powered not battery — a cold cycle exercises WiFi/MQTT reconnect and the LED self-test's boot path a warm reboot wouldn't). Cycle 1 (15:06 MST) and Cycle 2 (15:08 MST) both clean: LED self-test, MQTT reconnect, `Salt: 95% (21.5 cm)` both times. Both closing criteria (perfboard soldered + verified, survives power-cycle on new pins) now met.

**Reflection:** `components/salt-sensor/perfboard-layout.md` rewritten to reference pins by printed label instead of the wrong position numbers, with a prominent Board Note explaining the mismatch, all check results recorded, and the 3 new isolation checks made permanent. Harvested the generalizable lesson into `JCTsh-Build-Standards.md` §1.2 (v1.15): verify against a board's actual silkscreen labels rather than trusting a documented reference table, and add isolation checks between visually-adjacent pin labels to Pre-Power Checks as standard practice.

**Follow-up (2026-07-13):** `ESP32-project-pins.md` rewritten to match the actual SparkleIoT XH-32S board, organized by printed label with GPIO cross-reference (photo saved alongside it). `JCTsh-Perfboard-Build-Template.md` (new, repo root, Build Standards v1.16) generalizes the proven Assembly Sequence → Bus Planning → Pre-Power Checks → Reboot/Power-Cycle structure into a reusable skeleton for future perfboard builds, now that there are two real examples (hiking-monitor, salt-sensor) to draw from.

**Closed 2026-07-13 — Joseph confirmed and directed the close.**

---

### CARD-0066 · [enhancement] [photo-server] Verify legacy USB photo archive against Joseph's Immich library — RESOLVED 2026-07-13
**Notes:** Raised 2026-07-13. Joseph has a USB stick drive (E:) with a legacy photo archive — 941 `.jpg` files at the drive root (camera-original filenames like `CIMG0002.jpg`, dated 2002-2009), plus one unrelated `.exe` and several empty placeholder folders (`Documents/Pictures`, `Documents/Videos`, `Documents/Downloads`, `Documents/Music`, `System/Apps`, `System Volume Information`) — confirmed via direct inspection, no duplicate filenames within the 941. Wants to verify these are already in Immich (or upload whatever's missing) before wiping the drive, using the same checksum-based matching approach already established for the original Takeout migration (`components/photo-server/migration.md`) — matches skip, gaps upload, no separate dry-run needed.

**Plan:**
1. Copy the 941 `.jpg` files from `E:\` to `/home/jct/verify-batch-2026-07-13/` on the M8 (422G free, well clear of the ~164MB archive size).
2. Verify the copy (file count + total size match source) and notify Joseph once confirmed — he's wiping the USB drive himself right after, independent of the immich-go run finishing.
3. Run `immich-go upload from-folder` against Joseph's Immich library (API key in `credentials.local.md`) with `--session-tag` (tags newly-uploaded assets with a timestamped `{immich-go}/...` tag for review — chosen over `--into-album` since its semantics are unclear on whether skipped duplicates would also get swept into the album) and `--log-file /home/jct/verify-batch-2026-07-13/immich-go-verify.log`.
4. Report matched/uploaded/error counts back to Joseph.
5. Leave the staged copy and log **intact** on the M8 afterward — no cleanup step. This is a one-off ad hoc batch job, not a recurring/scheduled task.

**Other considerations flagged:**
- Matching is exact-checksum only (per the earlier discussion in this session) — if any of these camera-original files were also captured by the 2026 Google Takeout import in a re-compressed/re-processed form, they won't match here despite being the same photo content, and will upload as new assets. Not a bug, just a known limitation of checksum matching worth being aware of when reviewing the tagged results.
- These are old camera JPGs (2002-2009) — likely have usable EXIF dates for correct chronological placement; `immich-go`'s `--date-from-name` fallback (default on) wouldn't help here since these filenames don't encode dates, so any file missing EXIF may land with an inaccurate date. Worth a spot-check on a few results.

**Copy gotcha found and fixed (2026-07-13):** first `scp` pass used a case-sensitive `*.jpg` glob and silently copied only 787 of 941 files — the drive has a mix of `.jpg` and `.JPG` extensions, and Git Bash's default glob is case-sensitive, so all uppercase-extension files were skipped with no error. A first size-check also gave false confidence (`du -cb *.jpg | tail -1` on both sides was comparing the same case-filtered 787-file subset to itself, matching perfectly while still being wrong). Caught by cross-checking file *count* (941 via `find -iname`, case-insensitive) against the glob-based copy, which didn't match. Fixed: copied the missing 154 files with `shopt -s nocaseglob`, then re-verified with a case-insensitive, per-file byte sum (`find -iname '*.jpg' -printf '%s\n' | awk '{s+=$1} END{print s}'`) on both sides — confirmed exact match: 941 files, 154,096,152 bytes identical source and destination. General lesson: when verifying a copy, use case-insensitive matching consistently on both sides, and prefer a per-file byte sum over `du -cb | tail -1` (batching can silently truncate to the last chunk's total). Joseph confirmed the copy and wiped the USB drive.

**Resolution:** `immich-go upload from-folder` ran detached on the M8 (verified via `ps aux` after launch, not just the launcher's own exit code — same discipline as `migration.md`'s "killed background processes didn't actually die" lesson), completed in ~1 minute, zero errors. Reconciles exactly: **902 uploaded + 37 server-duplicates + 2 local-duplicates (two files in the batch were byte-identical to each other under different filenames) = 941.** All 902 new uploads tagged `{immich-go}/2026-07-13 10-...` for review in the Immich UI. Full log reviewed directly (not just the console summary) via `grep -iE 'error|warn|fail'` — no real errors; the only two "unknown file" warnings were the job's own `immich-go-console.out`/`immich-go-verify.log` files sitting in the scan directory, correctly recognized and skipped as non-photo files. Checked for the EXIF-date-fallback concern flagged above — zero matches for any date-fallback/no-EXIF warning pattern in the log, so no evidence any of the 902 uploads landed with an inaccurate date. Staged copy and log left intact at `/home/jct/verify-batch-2026-07-13/` on the M8 per the plan.

**Reflection:** generalized this into a reusable procedure — `components/photo-server/verify-and-retire-source.md` — covering the copy/verify/upload/review steps and both gotchas found here (case-sensitive glob dropping mixed-case extensions, `du -cb | tail -1` giving false confidence on a total). Indexed in `components/photo-server/README.md`'s doc table.

**Note for later:** Joseph spotted some visual duplicates by eye among the photos; not addressed by this card (out of scope — checksum matching only catches exact-byte duplicates, not near-duplicates/re-saves). Pointed to Immich's own built-in Duplicates view (CLIP-embedding based, already running, no new tooling) as the first thing to check whenever he's ready, with CARD-0028 already in Backlog for a more thorough standalone-tool pass if needed beyond that.

**Closed 2026-07-13 — Joseph confirmed and directed the close.**

---

### CARD-0065 · [bug] [hiking-monitor] Validate LTR-390 UV Index readings in real sunlight — RESOLVED 2026-07-13
**Notes:** Raised 2026-07-13. During post-CARD-0009-rework field testing, UVI read 0 (then 0.01) when the device was taken off dock power into "direct sunshine," raising concern about a wiring fault introduced by CARD-0009's STEMMA QT rework on the LTR-390. Split out as its own card rather than folded into CARD-0009, since that card scopes the enclosure/build work specifically and this is a sensor-correctness question that outlived it.

**Investigation:** ruled out, in order — enclosure/case blocking the sensor (device wasn't in the box), SDA/SCL swap from the STEMMA QT rework (wiring confirmed correct by direct inspection), and a loose STEMMA QT connector. BME280 (shared I2C bus) read normally throughout, narrowing any real fault to the LTR-390 itself. Sensor pointed straight at the sun and left to complete a full `update_interval: 2min` cycle — UVI climbed to **6.90**, a plausible value for clear midday sun. No hardware fault; the earlier near-zero readings were just pre-settle values from before the sensor had a clean, unobstructed, correctly-oriented exposure.

**Side finding:** the 5-minute heartbeat log message (`jctsh/components/hiking-monitor/log`) only reported uptime/RSSI/temp/battery — humidity, pressure, and UV index were invisible on the dashboard, which is why this diagnosis required reading the physical OLED instead of checking remotely. Expanded the heartbeat lambda in `hiking-monitor.yaml` to include all five BME280/LTR-390 readings (temp, humidity, pressure, UVI) plus battery, each NaN-safe.

**Resolution:** config validated clean (`esphome config`), OTA-reflashed successfully — device back online at 09:32:41 (`Online — ESPHome 2026.4.5, IP: 192.168.1.161, MQTT connected`). First post-reflash heartbeat (09:37:18) confirmed live on the dashboard: `Heartbeat - uptime: 0h 5m, RSSI: -59dBm, temp: 99.9°F, humidity: 32.7%, pressure: 931.7hPa, UVI: 6.92, batt: 4.00V` — all readings present, UVI holding steady near the earlier 6.90 reading.

**Closed 2026-07-13 — Joseph confirmed the new heartbeat message showed up on the log.**

---

### CARD-0003 · [enhancement] [infrastructure] TLS for Mosquitto (port 8883) — RESOLVED 2026-07-13
**Notes:** Port 1883 is internet-exposed via DuckDNS/port-forward with fail2ban, but credentials and sensor data are cleartext for any device using that path. TLS on 8883 eliminates this — scoped as a **split-port design**, not a fleet-wide switch: 1883 stays plaintext and LAN-only (not forwarded through the router), continuing to serve stationary home devices (garage-radar, salt-sensor, front-porch-temp-sensor, remote-temp-sensor-01, etc.) with no `secrets.yaml`/firmware changes needed. 8883 (TLS) becomes the *only* port forwarded via DuckDNS, used exclusively by devices that actually leave the home network — hiking-monitor today, air-quality-monitor once built (CARD-0012, "carried on hikes alongside the hiking monitor"). Steps: get Let's Encrypt cert for the DuckDNS hostname (certbot with duckdns plugin), add a TLS listener on port 8883 in mosquitto.conf, change the router port-forward from 1883→8883, add CA-cert trust config + updated broker port to the remote-capable devices' `secrets.yaml`/`mqtt:` block, reflash those devices only, update Node-RED broker node / HA MQTT integration if either connects over the forwarded path. CARD-0002 prerequisite complete.

**Decision rationale (2026-07-10):** considered reflashing the whole fleet uniformly vs. this split; chose the split because most devices are stationary and never traverse the internet-facing path, so fleet-wide TLS would add CA-cert config/maintenance to every device for no real exposure reduction on the stationary ones. This card protects only the internet-exposed path (roaming devices via DuckDNS/port-forward); it does not encrypt LAN-local port 1883 traffic for stationary devices — that residual, accepted risk is documented under CARD-0050, which was deprioritized 2026-07-10 on its own risk-analysis merits (see that card — CARD-0003 was mistakenly framed there at first as a substitute for it and later corrected).

**Unblocked (2026-07-10):** CARD-0004 (salt-sensor Arduino → ESPHome migration) is complete except one open verification item (12h reading cycle hasn't fired naturally yet) — doesn't block this card either way, since salt-sensor is a stationary device staying on plaintext LAN-only 1883 under the split-port design.

**Execution plan:** `C:\Users\jcthomas\.claude\plans\misty-fluttering-porcupine.md` (Claude Code plan file, not in this repo) — five phases: A) Pi/certbot cert issuance, B) Mosquitto TLS listener, C) router port-forward, D) hiking-monitor CA-trust config + OTA reflash, E) cutover + doc updates. Approved 2026-07-10.

**Progress (2026-07-10):** Phases A–C complete, Phase D in progress. Moved Planning → Build to reflect that this card skipped straight from an approved execution plan into live implementation, rather than following the Design (ESPHome Claude Code instructions) step that column normally implies.

**Progress (2026-07-13):** Phases A–D complete. Only Phase E (cutover + docs) remains.
- **Phase A (cert):** done. Retried past the earlier DuckDNS DNS flakiness (see prior note, now resolved) — cert issued for `jctsh.duckdns.org`, expires 2026-10-08. Deploy-hook (`core/mqtt/mosquitto-cert-deploy-hook.sh`, deployed to `/etc/letsencrypt/renewal-hooks/deploy/mosquitto-reload.sh`) copies renewed certs into `/etc/mosquitto/certs/` and restarts Mosquitto; `certbot renew --dry-run` and `certbot.timer` both confirmed working.
- **Phase B (Mosquitto TLS listener):** done. `core/mqtt/mqtt-tls.conf` deployed to `/etc/mosquitto/conf.d/`. Hit and fixed a real gotcha: `password_file`/`allow_anonymous` can't be redeclared per-listener when `per_listener_settings` is false (the default, and true here) — they're global once set in `local.conf`; redeclaring caused a "Duplicate password_file value" error. Fixed by dropping those lines from the new file. Verified: both 1883 and 8883 listening, TLS handshake against `localhost:8883` and against the public `jctsh.duckdns.org:8883` (from the Pi, exercising the real router path) both return a valid cert chain (`Verify return code: 0`).
- **Phase C (router forward):** done. New `8883 → 192.168.1.117:8883` rule added (Joseph, manually, via the router admin UI — browser automation couldn't drive this router's admin SPA, it never reached an "idle" state for the extension's tooling). Existing 1883 rule deliberately left in place until Phase E cutover.
- **Phase D (hiking-monitor):** done. `secrets.yaml` (`mqtt_ca_cert`, ISRG Root X1, expires 2030-06-04) and `hiking-monitor.yaml`'s `mqtt:` block (`port: 8883`, `certificate_authority`, `idf_send_async: false`) updated and compile clean. Device came back online 2026-07-13, unblocking the reflash. Hit two real snags getting the OTA to actually run: (1) `esphome run` from the repo path failed with `Detected a whitespace character in project paths` — same class of issue as the garage-radar build (`DEVLOG.md` 2026-05-20) — worked around via the existing whitespace-free mirror at `C:\esphome\hiking-monitor\`, but that mirror was stale (missing the TLS config/CA-cert changes entirely) and had to be re-synced from the repo copies of `hiking-monitor.yaml`/`secrets.yaml` before flashing, or it would have silently pushed the old plaintext-1883 config; (2) a leftover locked file in `.esphome/build/hiking-monitor/.pioenvs` from an earlier interrupted build blocked the clean step until manually removed. OTA upload succeeded, device rebooted. **Verified via Mosquitto log on the Pi:** old plaintext-1883 session (`hiking-monitor-04b24797df2c`) timed out at 08:59:25, new TLS session on port 8883 connected at 08:59:26 and has stayed up with no disconnects since (15s keepalive, so a real problem would already show).
- **Phase E (cutover + docs):** done. Docs updated 2026-07-13 to reflect 8883/TLS as the roaming-device path: `jctsh-network.md`, `components/hiking-monitor/wifi-config.md`, `credentials.local.md`, `jctsh-security-hardening.md` (dated superseded-note on the original port-inventory finding, history kept intact). Confirmed via `p-w-firefly/heartbeat.md` that coachproxyos reaches MQTT via Tailscale (`100.70.162.24:1883`), not the DuckDNS/port-forward path, so retiring the 1883 forward has no impact there. Old 1883 → 192.168.1.117 router-forward rule removed by Joseph (manual, router admin UI — same as Phase C, browser automation can't drive this router's admin SPA).

**Resolution:** all five phases complete. **Verified live 2026-07-13** from the LAN against the public `jctsh.duckdns.org` hostname (this router does hairpin NAT, confirmed in `wifi-config.md`, so a LAN-sourced test against the public hostname reflects the real forwarding table): port 1883 now returns connection refused (forward removed), port 8883 accepts a TCP connection (TLS listener still reachable). Cross-checked against the live Mosquitto log on the Pi: `hiking-monitor-04b24797df2c` has held a stable TLS session on 8883 since 08:59:26 with no disconnects (15s keepalive). The one 09:10 SSL "unexpected eof" log entry is this verification probe itself (a raw TCP connect with no TLS handshake), not a device problem.

Execution detail/history: `C:\Users\jcthomas\.claude\plans\misty-fluttering-porcupine.md`.

**Closed 2026-07-13 — Joseph confirmed and directed the close.**

---

### CARD-0061 · [enhancement] [infrastructure] Add Docker health check for the Pi's Home Assistant container &mdash; RESOLVED 2026-07-12
**Notes:** Found 2026-07-12 during a Pi health evaluation. The `homeassistant` Docker container had no configured `HEALTHCHECK` &mdash; `docker ps`/`docker inspect` only reflected process liveness, not actual HA responsiveness. Same class of blind spot already found and fixed on photo-server (CARD-0032/CARD-0046: Docker's own health check only pings the API, doesn't verify real functionality) &mdash; HA is arguably the single most critical container on the Pi, since it's the sole bridge to SmartThings/Google Home for the whole house.

**Resolution:** added a `healthcheck` block to `core/homeassistant/docker-compose.yml`: `curl -f http://localhost:8123/manifest.json` (lightweight, unauthenticated, confirmed working) every 60s, 10s timeout, 3 retries, 90s start period to cover HA's own boot time. Deployed to the Pi (`/home/pi/docker-compose.yml`) and recreated the container &mdash; the existing `homeassistant` container predated this compose project (no compose labels), so it had to be stopped and removed before `docker compose up -d` would take over management of it; HA's actual config lives in the bind-mounted `/home/pi/homeassistant` volume, not the container, so nothing was lost.

**Live-tested 2026-07-12** using the same deliberately-break-it discipline as CARD-0029/CARD-0032/CARD-0046: confirmed `(healthy)` immediately after recreation, then froze HA's actual process inside the container (`kill -STOP` on the main `python3 -m homeassistant` PID &mdash; a genuine hang, not a container-level action, since that's exactly the failure mode this card exists to catch) and waited for the check to notice. Docker correctly flagged `unhealthy` with `FailingStreak: 3` after three consecutive failed checks. Resumed the process (`kill -CONT`); Docker correctly returned to `(healthy)`. Full Docker-level cycle (healthy &rarr; unhealthy on real hang &rarr; healthy again) verified end to end.

**Dashboard-visibility gap found and closed (2026-07-12):** the Docker-level fix alone only fixed `docker ps`/`docker inspect` locally on the Pi &mdash; it did not surface anything on the JCTsh log dashboard, unlike the photo-server pattern this card was modeled on, which pairs a health check with a heartbeat script that publishes the result to MQTT. Built `core/homeassistant/pi-heartbeat.py`, checking `docker inspect homeassistant`'s health status and publishing to the existing `jctsh/core/log-server/log` topic under the `jctsh-core` component identity (same identity/topic/credentials already used by the Pi's boot/reboot notifications &mdash; `/etc/jctsh/log-server.env`, reused rather than a new dedicated MQTT account, since this is the same host's own infrastructure). Deployed via `core/maintenance/pi-heartbeat.service`/`.timer` (30 min, matching the fleet-wide heartbeat cadence). Hit one real bug during first deploy: initially built the topic from the component variable (`jctsh/core/jctsh-core/log`) instead of the fixed `jctsh/core/log-server/log` topic the log server actually expects &mdash; component name and topic segment are decoupled in this convention and are easy to conflate; fixed and redeployed.

**End-to-end live-tested 2026-07-12:** repeated the freeze/resume test with the heartbeat script run manually at each stage, confirmed via the dashboard's actual `/data` endpoint (not the flushed-only `/log` text file, which delayed visibility of the healthy-state message inside an unflushed collapse group during testing and briefly looked like a bug before being traced to normal flush-timing behavior, not a real defect) &mdash; healthy (`System`, `Heartbeat - Docker containers healthy.`) &rarr; unhealthy (`Alert`, `Docker degraded - homeassistant:unhealthy`, visible immediately since Alert messages don't collapse) &rarr; healthy again, all three states confirmed present and correctly categorized on the live dashboard.

---

### CARD-0062 · [enhancement] [infrastructure] Switch Pi to headless boot &mdash; drop the desktop GUI &mdash; RESOLVED 2026-07-12
**Notes:** Found 2026-07-12 during a Pi health evaluation. The Pi boots into `graphical.target` with a full desktop session running (`pcmanfm --desktop`, `wf-panel-pi`) even though normal access is SSH-only &mdash; Joseph used the physical desktop once, during initial setup, never since. On a Pi 3B+ with only ~905MB RAM already under real pressure (zram swap sitting at ~50% used while running HA, Node-RED, Mosquitto, the log server, Tailscale, and fail2ban concurrently), this was pure reclaimable overhead.

**Pre-check:** confirmed no VNC/RealVNC/xrdp service configured, and `/etc/xdg/autostart/` + `~/.config/autostart/` contained only standard desktop-session plumbing (polkit agents, on-screen keyboard, compositor) &mdash; nothing load-bearing for SSH-only use.

**Resolution:** `sudo systemctl set-default multi-user.target`, rebooted. Confirmed `systemctl get-default` returns `multi-user.target` and no desktop processes (`pcmanfm`/`wf-panel-pi`) run anymore. SSH access, Docker/HA (HTTP 200 on `:8123`), Mosquitto, Node-RED, and jctsh-logging all confirmed active post-reboot.

**Before/after (steady 4-day uptime vs. 6 minutes post-reboot):** swap usage dropped from 449Mi (~50% of swap) to 148Mi (~16%) &mdash; the clearest signal, since raw "used" memory is a noisy comparison this early (buff/cache hadn't rebuilt yet). The desktop's ~225MB of GTK/panel/session overhead is now structurally absent rather than merely idle. Fully reversible via `systemctl set-default graphical.target` + reboot if ever needed.

---

### CARD-0059 · [idea] [infrastructure] NetAlertX — self-hosted LAN device tracker with custom naming — RESOLVED 2026-07-12
**Notes:** Raised 2026-07-12. Motivated by the router (TP-Link Archer AXE75) listing most connected devices with meaningless names, with no built-in way to rename them — the JCTsh-managed fleet already has this solved via DHCP reservations + `jctsh-network.md`'s device table + ESPHome hostnames, but third-party/commercial devices (Ring, Ecobee, Cast devices, guest phones) aren't part of that convention and the router won't let their names be overridden.

**What it is:** NetAlertX (formerly Pi.Alert) — open-source, self-hosted LAN device scanner and presence tracker. Maintains its own device database independent of the router, so naming lives there regardless of what the router shows.

**How it works:** periodic ARP scanning (plus optional plugins — mDNS, SNMP against the router, DHCP lease-file parsing, nmap) discovers devices; each MAC gets a persistent record (first-seen, last-seen, IP history, OUI-based vendor guess) in its own SQLite DB. A web dashboard lets you assign a friendly name/icon/group to each MAC once, permanently — independent of router support. Also flags brand-new unknown devices joining the network (security-relevant) and always-on devices going silent, with notifications via MQTT, webhooks, email, Pushover/Telegram/ntfy/Apprise.

**Planning (2026-07-12) — host decision reversed on real data:** initially figured the Pi as the natural fit (LAN hub, classic Pi.Alert project) and Joseph agreed — but checking the Pi directly first (good thing) found it's a Raspberry Pi 3 B+ already under real memory pressure: 34MB free, 315MB available, swap at 462MB/904MB (51%) — already running Docker for Home Assistant itself, plus Mosquitto, Node-RED, and `log_server.py` natively, all things other devices actively depend on (MQTT broker, automations). Adding periodic ARP/nmap scanning there risked contending for the little headroom left. Checked the M8 instead: 12 cores, 9.2GB available RAM, swap barely touched (109MB/4GB), Docker already running Immich's 4 containers cleanly. Switched the plan to the M8. No VLAN segmentation on this network (confirmed during CARD-0050), so the M8 sees the same broadcast domain the Pi would — no ARP-visibility loss from the switch. Skipped a separate Design phase — this checked-before-deciding pass is the plan; went straight to Build.

**Build (2026-07-12):** MQTT account (`netalertx`) created on the Pi's Mosquitto broker, recorded in `credentials.local.md`, verified working. `components/netalertx/docker-compose.yml` deployed to `~/netalertx-app` on the M8 (its own compose project, alongside but separate from `~/immich-app`).

Two real deploy bugs found and fixed: (1) my first compose file was based on a lossy AI-summarized version of the upstream reference, missing `read_only: true` and the specific `cap_drop`/`cap_add` set the entrypoint's own self-check requires — container crash-looped (exit 126) until fetched and matched the literal upstream file. (2) the upstream file's ARP-flux-mitigation `sysctls:` block isn't allowed by Docker under `network_mode: host` (`runc create failed: sysctl ... not allowed in host network namespace`) — removed from compose; the real fix is setting those two sysctls on the M8's host kernel directly, which needs interactive `sudo` (deferred — `jct@photo-server.local`'s sudo requires an interactive password, unlike the Pi's account; captured as a follow-up, not blocking).

**Resolution:** container deployed, healthy, zero restarts, image `ghcr.io/netalertx/netalertx:latest`. Login secured (Settings → System → Set Password, credential in `credentials.local.md` — default install ships with auth disabled entirely, closed that gap). Joseph completed the manual first-run setup and confirmed the naming workflow. MQTT/log-dashboard integration deliberately deferred, not because it's blocked but because it needs its own experiment first — split out to CARD-0063 rather than holding this card open for it.

**Closed 2026-07-12 — Joseph confirmed and directed the close.**

---

### CARD-0057 · [enhancement] [kanban-board] Serve the kanban board as a live-parsing Pi page — RESOLVED 2026-07-11
**Notes:** Raised 2026-07-11. The manual regenerate-after-edit discipline agreed to when closing CARD-0056 is already slipping — updates to `kanban-board.md` aren't reliably followed by a republish. That's exactly the condition CARD-0056 named as the trigger to revisit this alternative, and it's now been hit. There's a second, measured cost beyond just forgetting: a regenerate cycle means re-reading the full ~600-line file (multiple large reads once the board grows) plus manually cross-checking it against the embedded JSON, which alone runs over 20k tokens — expensive as well as easy to skip.

**Skipped Planning/Design (2026-07-11):** the card's own architecture sketch below already functioned as the plan, and the one open question (getting `kanban-board.md` onto the Pi) already had a settled answer — same situation the TOS doc calls out for CARD-0003/CARD-0034, so this went straight from Backlog to Build.

**Approach:**
- New route on the Pi's existing `log_server.py` (e.g. `/kanban`), alongside the existing `/status` endpoint — reuses the running process/port rather than standing up anything new.
- A small regex-based parser matching `kanban-board.md`'s consistent card format (`### CARD-XXXX · [type] [tag] Title`, `**Notes:**`/`**Resolution:**`/`**Blocked:**` blocks, `## ColumnName` section headers) into the same card-object structure the artifact's JSON currently holds.
- Serve either full server-rendered HTML (reusing the existing blueprint-styled CSS) or a JSON endpoint the current client-side JS/CSS fetches instead of reading a baked-in `<script type="application/json">` block — the JSON route is less rework since the front end barely changes.
- Reachable on the LAN and via Tailscale, matching how `/status` is already scoped — no internet exposure needed.

**Resolved gap, superseded (2026-07-11):** originally planned as `scp`ing `kanban-board.md` to the Pi alongside `log_server.py` on deploy, repeated on every future edit. Built and briefly live-tested that way, then reconsidered — see "Architecture changed" below for what replaced it.

**Relationship to CARD-0056:** CARD-0056 built and closed the claude.ai Artifact version, explicitly deferring this Pi-hosted alternative and naming "manual regeneration turns out to be too easy to forget" as the specific revisit trigger. That trigger has now occurred.

**Built (2026-07-11):** added `_parse_kanban_board()`, `_KANBAN_TEMPLATE`, and `/kanban` + `/kanban/data` routes to `core/logging/log_server.py`, reusing the artifact's existing blueprint-styled front end (client-side search/filter/collapse unchanged) but swapping its data source from a baked-in JSON blob to a `fetch('/kanban/data')` call, auto-refreshed every 30s. Added cross-links from the `/` and `/status` pages' nav lines, matching the existing pattern.

**Sync automated, then superseded (2026-07-11):** first automated the remaining manual step (`scp`ing `kanban-board.md` to the Pi after every edit) as a project-level `PostToolUse` hook (`Write|Edit` matcher) that fired on file edits and `scp`'d the file if it matched. Built, pipe-tested, and schema-validated correctly, but the live proof-test failed: the settings watcher doesn't hot-reload a `hooks` section added mid-session to a file that already existed at session start, so it never actually fired this session.

**Architecture changed (2026-07-11):** while debugging the hook, Joseph asked why push at all rather than having the Pi pull the file itself. Real answer: this Windows machine isn't a server (not always on/reachable), but the repo's GitHub remote is, and it's public — so `_load_kanban_cards()` now fetches `https://raw.githubusercontent.com/joscthomas/jctsh/main/kanban-board.md` directly over HTTPS on every request via `urllib.request`, instead of reading a local file. Removed `KANBAN_FILE`, the local copy on the Pi, and the now-unneeded hook entirely — no push mechanism of any kind. Freshness is now tied to `git push`, not to individual edits or Claude Code sessions; the header label changed from "Updated" (file mtime) to "Fetched" (request time) since GitHub's raw-content endpoint doesn't expose a real last-modified time and the GitHub API's per-file-commit endpoint risks its 60-req/hour unauthenticated rate limit under the page's 30s auto-refresh.

Two real parser bugs found and fixed during local testing, both edge cases exposed by CARD-0057's own text describing its own conventions: a naive `"### CARD-"` substring sanity-check falsely flagged a mismatch because the card's own body quotes the format (`` `### CARD-XXXX · ...` ``) as documentation — the real line-anchored regex was correct all along, the *test* was wrong. Separately, a naive `"**Blocked" in body` heuristic false-flagged this same card as blocked because its body quotes `` `**Blocked:**` `` as an example of a recognized label; fixed by requiring the pattern at the start of a line (`^\*\*Blocked`), which also means CARD-0003's `**Blocked:**` — buried mid-bullet inside its Phase D progress narrative, not its own paragraph — doesn't get auto-flagged either. Accepted as a known limitation: the flag is a best-effort scanning aid, not authoritative; full text is always visible in the expanded card regardless.

**Verified — local-file version (2026-07-11, superseded):** local end-to-end HTTP test (real handler, real auth, a throwaway port) confirmed all 57 cards parse correctly, 401 without credentials, 200 with them, existing `/` and `/status` routes unaffected, and a missing-file case returns 503 instead of crashing. Deployed via the documented pattern (`scp log_server.py` + `kanban-board.md` to the Pi, `ssh ... sudo systemctl restart jctsh-logging`) — service came back up clean. Live-fetched `/kanban` and `/kanban/data` over the real network afterward: byte-identical sizes to the local test, 57 cards, timestamp matching the actual deploy moment.

**Re-verified — pull-from-GitHub version (2026-07-11):** same local end-to-end HTTP test re-run against the new `_load_kanban_cards()` (fetches the public repo's raw content instead of a local file) — 56 cards parsed correctly (one short of the local 57, since CARD-0057's own latest edits weren't pushed yet at test time, exactly the new expected behavior), `/kanban` and existing `/`/`/status` routes all unaffected. Deployed the updated `log_server.py` alone (no `kanban-board.md` to push anymore) and confirmed live: `/kanban/data` over the real network returned byte-identical output to the local test. Removed the now-obsolete local `kanban-board.md` copy from the Pi's disk.

**Reflection:** the "small regex-based parser" scope held up — no need for anything heavier. The two parser bugs found were both self-referential (the card describing the parser's own conventions tripped naive substring checks), a class of edge case worth remembering for any future text-based parser tested against a corpus that documents its own format. The bigger lesson was architectural: the first instinct (push on edit, via a Claude Code hook) solved the wrong layer — it made *editing* trigger sync, when the real question was *which side is reliably reachable*. The Pi is always-on; this laptop isn't. Once reframed as "have the always-on side pull from something else that's always-on" (GitHub, already in place as the git remote), the whole push/hook/scp mechanism became unnecessary rather than needing to be fixed. Worth asking "which side should own the pull" before reaching for a push mechanism next time. Separately: `sudo` commands over SSH to the Pi still prompted for approval despite the `ssh pi@raspberrypi.local *` allowlist rule, likely a safety layer above simple pattern-matching for privileged commands against shared physical infrastructure — reasonable to leave as-is.

**Autonomous build (2026-07-11):** Joseph configured project permissions (`.claude/settings.local.json`) so this build/deploy could run without per-operation confirmation — see progress notes below.

**Closed 2026-07-11 — live on GitHub push, re-verified working, no known open items.**

---

### CARD-0004 · [enhancement] [salt-sensor] Migrate Arduino C++ → ESPHome — RESOLVED 2026-07-11
**Resolution:** `salt-sensor.yaml` written and compiles clean (RAM 13.2%, Flash 52.3%). Direct translation of the Arduino sketch — same 15-sample-median 12h reading cycle, same MQTT topics/payloads (`jctsh/sensors/salt-sensor/data`, `/status`, `/log`), same LED state machine (GPIO2/15/4, unchanged pins), same thresholds (still owned entirely by Node-RED — flow untouched). Added a 30-min heartbeat (`.../heartbeat`) that didn't exist before, closing the gap CARD-0021 flagged (salt-sensor showing `?` on the status dashboard). `secrets.yaml` created from `secrets.h`'s values; old v3 Arduino sketch archived to `archive/salt-sensor-v3-arduino/`; `C:\esphome\salt-sensor\` flash path set up matching the other ESPHome components.

**Two real compile bugs found and fixed during translation** (both are ESPHome `globals:` gotchas, not obvious from the docs): a fixed-size C array global (`float[15]`) fails to compile (`GlobalsComponent` can't take an array by value — decays to a pointer); switched to `std::vector<float>`. Its `initial_value: '{}'` was then ambiguous between two constructor overloads; fixed with an explicit `std::vector<float>()` initializer.

**One design decision worth flagging:** ESPHome's default MQTT birth topic is `<topic_prefix>/status`, which would have silently collided with this component's existing `.../status` topic (Node-RED → ESP32, drives the LEDs). `birth_message:` is explicitly disabled in the yaml to prevent this — a real footgun for any future component whose topic convention includes `/status`.

**Field verification (2026-07-10):** USB-flashed and confirmed end to end — LED self-test visible on boot, `/data` publishes a real retained reading, `/status` round-trips correctly from Node-RED and drives the LEDs (`ok` → solid green, confirmed visually), `/log` messages flowing to the dashboard. See CARD-0049 for the follow-on LED pin move (GPIO2/15/4 → GPIO32/33/27), also verified working over OTA.

**Heartbeat confirmed (2026-07-10 13:06 MST):** first natural 30-min heartbeat landed — `Heartbeat - uptime: 0h 30m, RSSI: -50dBm, status: ok`. Watchdog wildcard pickup confirmed.

**Removed the `Status: X -> Y` log line (2026-07-10):** the `on_message` handler used to log every status transition to `.../log`, but review found it added no real value — Node-RED's own `fn_threshold` logging (`[Sensor] Salt: X% (Y cm)`, `CRITICAL — salt at X%...`) already covers the meaningful transitions in plain language, and the ESP32-side log was actively misleading: dashboard history showed `unknown -> offline` / `offline -> ok` entries that never came from Node-RED (confirmed — `offline` doesn't appear anywhere in `salt-sensor.flow.json`). Root cause: a fossil from early migration testing, before `birth_message:` was disabled — ESPHome's default birth/will strings (`online`/`offline`) briefly collided with this same `/status` topic. Not reproducible under current firmware, but the confusion it already caused wasn't worth the code. Removed `prev_status`/`status_changed` globals along with it; `current_status` still drives the LEDs, just silently.

**12h natural reading cycle confirmed (2026-07-11):** the last open verification item — the 15-sample-median 12h reading firing on its own timer, not just via the on-connect immediate-reading code path — is now confirmed. Two standalone readings (no adjacent MQTT connected/disconnected/online event, unlike every on-connect-triggered reading in the log) landed exactly 12 hours apart: `2026-07-11 01:17:37 MST — Salt: 98% (20.9 cm)` and `2026-07-11 13:17:37 MST — Salt: 95% (21.5 cm)`. Periodicity confirmed via the dashboard log (`http://192.168.1.117/log`), closing the card's last open condition.

---

### CARD-0056 · [enhancement] [kanban-board] Persistent visual kanban board — RESOLVED 2026-07-11
**Notes:** Raised 2026-07-11: every time the board gets summarized in chat, it comes out in a different ad hoc format and scrolls out of view while working, with no stable place to return to it. Agreed approach: a browser-hosted Artifact with a persistent URL, redeployed to the same link whenever `kanban-board.md` changes, rather than a fresh chat message each time.

Built as a single self-contained HTML page (no external requests, per the Artifact sandbox) — a blueprint-styled board with one column per kanban state (Backlog, Planning, Design, Build, Done, Defer), each independently scrollable and collapsible, card tiles that expand in place for full notes, a live text search across id/title/tag/notes, and type filter chips (bug/enhancement/idea). Card data is baked into the page at build time as a JSON blob, not read live from the repo — so it goes stale exactly the way any snapshot does, and needs a manual regenerate-and-republish pass after edits, same discipline as keeping any other doc in sync.

`backlog.md` was renamed to `kanban-board.md` in this same session (2026-07-11), with references updated across README.md, CLAUDE.md, JCTsh-Operating-System.md, and the photo-server docs that pointed to it by name.

**Live-parsing alternative considered, not pursued (2026-07-11):** discussed serving the board from the Pi's existing `log_server.py` with a route that parses `kanban-board.md` live on each request instead of reading baked-in JSON, which would remove the manual-regenerate step entirely. Real cost surfaced in the same discussion: the repo isn't cloned on the Pi (deploys there are one-off `scp`, per `SOFTWARE-ENVIRONMENT.md`), so `kanban-board.md` would still need to be pushed to the Pi on every edit — the live-parsing win only fully lands once that push is also automated. Decision: stick with the manual artifact-regenerate workflow for now and see how the discipline holds up in practice; revisit the Pi version if manual regeneration turns out to be too easy to forget.

**Resolution:** page published and confirmed viewable at a stable claude.ai URL. Regenerate-after-edit discipline exercised twice already (title/collapse-default fix, then a CARD-0056 text sync) and explicitly agreed to as the ongoing approach. Closed 2026-07-11 — Joseph confirmed sticking with this version and directed the commit.

---

### CARD-0052 · [idea] [infrastructure] JCTsh Team Operating System (TOS) — RESOLVED 2026-07-11
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
**Notes:** Discovered 2026-07-09 following up on CARD-0042 — Joseph reported a specific HEIC photo (`IMG_20260625_165423.heic`, Robin's account) with a fine-looking thumbnail but a visibly distorted full image (elongated heads). Checked the asset directly via `/api/assets/{id}`: `width`, `height`, `exifImageWidth`, `exifImageHeight`, and `orientation` all `null` — Immich never successfully extracted this file's real dimensions/orientation, which plausibly explains the distortion (wrong aspect-ratio assumption during preview rendering). Sampled 100 assets per account: **Joseph 0/100 null width; Robin 89/100 (89%)** — same lopsided pattern as CARD-0037/CARD-0039/CARD-0042, again far worse for Robin despite her "clean" import history.

Triggered `metadataExtraction` via `PUT /api/jobs/metadataExtraction` (`{"command":"start"}`) — unlike CARD-0042's thumbnail gap, this one *is* partially caught by the normal queue trigger: 13,311 assets queued immediately. However this is likely not the full picture — some assets (like the specific HEIC file that started this) may be marked "complete" in the database despite holding null values, the same DB-vs-reality mismatch pattern as CARD-0042, which would need the same forced per-asset fix (`refresh-metadata`, another valid job name on the same `/api/assets/jobs` endpoint used for CARD-0042's `regenerate-thumbnail`).

**Paused here by design (2026-07-09):** M8 load hit 12.64/12 cores with CARD-0030's backup, CARD-0042's thumbnail regen, and this metadata extraction all running concurrently — Immich API was still responsive (45ms ping) so nothing was failing, but Joseph asked to let the current jobs finish before adding a full forced `refresh-metadata` sweep across Robin's ~77,123 assets. The 13,311 already queued will keep processing in the background regardless.

**Closed 2026-07-10 — all four conditions verified live:** (1) `metadataExtraction` queue confirmed fully drained via `GET /api/jobs` (0 waiting/active/failed); (2) a fresh 150-asset sample of Robin's library showed 0/150 null width (top-level `width` field — the list endpoint doesn't return `exifInfo` inline, this superseded the original per-asset `exifImageWidth` check method but confirms the same thing); (3) `IMG_20260625_165423.heic` re-checked directly: `exifImageWidth 4032`, `exifImageHeight 3024`, `orientation 1` — all populated, no longer null; (4) Robin's null-width rate (0%) now matches Joseph's baseline (0%).

---

### CARD-0042 · [bug] [photo-server] Robin's library missing thumbnails for ~81% of assets — RESOLVED 2026-07-10
**Notes:** Discovered 2026-07-09 while troubleshooting Robin's phone backup — Joseph noticed "Error Loading Image" on several thumbnails, both in the phone's local gallery view and (critically) in the web UI too, which ruled out a phone-side rendering glitch. Diagnosed via direct HTTP checks against `/api/assets/{id}/thumbnail`: a 150-asset sample came back 122/150 (81%) returning `404` for Robin, versus **0/150** for Joseph — confirmed real, server-side, and isolated to Robin's account. Root cause not pinned down (her import was the "clean" one per `migration.md`, yet has by far the worse thumbnail gap — consistent with the same pattern already seen in CARD-0037/CARD-0039 where Robin's account had the larger gap despite the cleaner import history). The standard `thumbnailGeneration` job queue didn't surface these (`waiting: 1` when triggered normally) because Immich's database already considered them complete — the gap is between DB state and actual thumbnail files on disk, not a "job never ran" situation like CARD-0037.

**Fix:** used the per-asset job endpoint (`POST /api/assets/jobs`, `{"name":"regenerate-thumbnail","assetIds":[...]}` — found via the same schema-discovery trick as CARD-0037/CARD-0039, sending an invalid body and reading the validation error's allowed values) to force-regenerate every one of Robin's 77,123 assets in 155 batches of 500. Confirmed working on a small scale first (9 known-broken assets, all fixed, verified via HTTP 200) before committing to the full-library run. Submitted successfully in full — `thumbnailGeneration` queue confirmed at 76,996 waiting immediately after. Verified live at every step (new photo from Robin's phone arrived with a working thumbnail, confirming upload itself was never broken — only historical thumbnails were affected).

Running concurrently with CARD-0030's backup verification and the tail end of CARD-0037/039's work; checked M8 load before committing to the bulk job (5.04/12 cores, comfortable).

**Closed 2026-07-10:** `thumbnailGeneration` queue confirmed fully drained (0 waiting/active/failed). Fresh 150-asset sample of Robin's library: 140/140 image/photo assets returned `200` on thumbnail (0% broken, matching Joseph's baseline). The sample also included 10 `.MP.mp4` assets (Pixel Motion Photo video sidecars) that returned `404` — investigated and confirmed **not a regression**: these are `visibility: hidden` linked video components, never meant to be fetched directly (the paired still-image asset each links to via `livePhotoVideoId` has its own working `200` thumbnail, which is what actually displays in the gallery/timeline). This is normal Immich behavior for motion photos, not the bug this card tracked.

---

### CARD-0051 · [enhancement] [photo-server] Extend heartbeat with disk-capacity and backup-staleness checks
**Notes:** Found 2026-07-11 during a health check + log-dashboard history review. CARD-0032/CARD-0046 made the heartbeat check that storage is *readable/writable*, but two real gaps remained:
1. **Disk capacity** — nothing checked how *full* a mount was. A drive filling up (primary or either backup) would degrade Immich or fail backups with no advance warning.
2. **Backup staleness** — CARD-0040 made `photo-library-backup.sh` report its own per-run success/failure, but nothing watched for the run simply not happening at all (cron broken, script missing, host down over a scheduled run) — an absence-of-signal gap the per-run report can't cover.

**Resolution:** `photo-server-heartbeat.py` now checks `shutil.disk_usage()` on all three mounts (`/mnt/photo-library`, `/mnt/photo-library-backup`, `/mnt/photo-library-backup-joseph`) every 30-min cycle, flagging degraded via the existing `unhealthy`/Alert path if any exceeds 90% used. `photo-library-backup.sh` now touches `/home/jct/photo-library-backup-success.stamp` only on the fully-successful path (both rsync jobs exit 0); the heartbeat script checks that marker's age and flags degraded if missing or older than 9 days (one missed weekly Sunday 2am run + 2-day grace). Both reuse the existing `unhealthy` list / dashboard Alert / `status: degraded` payload — no new MQTT topics or schema.

**Live-tested 2026-07-11:** staleness check fired correctly (`backup:stale (no successful run recorded)`) immediately after deploy since no stamp existed yet — confirmed on the dashboard. Capacity check verified by temporarily dropping the live deployed threshold to 1% and confirming all three mounts correctly reported (`primary-capacity:68% used, backup-robin-capacity:35% used, …`), then restored to 90% and diffed byte-for-byte against the repo version. Ran the real `photo-library-backup.sh` end-to-end (not a simulated success) — both rsync legs completed, stamp file written, and a final heartbeat run confirmed `status=online` with no unhealthy items, leaving the live system in a genuinely healthy state post-test.

---

### CARD-0046 · [enhancement] [photo-server] Extend storage-health check to cover backup drive(s), not just primary
**Resolution:** `photo-server-heartbeat.py`'s storage check now also writes/reads/removes a marker file directly on both backup mounts (`/mnt/photo-library-backup`, `/mnt/photo-library-backup-joseph`) every 30-minute cycle — plain host-level file I/O, not `docker exec`, since these mounts aren't inside any container (Immich itself never touches them, only the standalone backup script does). Failures reported as `backup-robin:<error>` / `backup-joseph:<error>` in the same non-collapsing `Alert` path already used for the primary library and container checks.

**Live-tested 2026-07-10** using the same safe `mount -o remount,ro` technique as the original CARD-0032 test, applied to each backup drive in turn: both correctly triggered `Immich degraded - backup-<name>:[Errno 30] Read-only file system` on the dashboard, and both recovered cleanly to normal status after `mount -o remount,rw`. Closes the exact visibility gap that let Momentus's real hardware failure go undetected for over 2 hours earlier the same day. Full detail in `components/photo-server/heartbeat.md`.

---

### CARD-0040 · [enhancement] [photo-server] Dashboard visibility for backup runs
**Resolution:** `photo-library-backup.sh` publishes MQTT log messages so backup success/failure is visible on the JCTsh log dashboard without SSHing in — `"Backup starting."` before either rsync job, `"Backup complete."` (category `System`) if both succeed, or `"Backup failed (joseph exit <code>, robin exit <code>)."` (category `Alert`, non-collapsing) if either fails. Same pattern as CARD-0036's reboot notifications, reusing the existing `photo-server` MQTT account.

**Both paths confirmed live 2026-07-10.** The failure path fired correctly earlier in the day when both rsync jobs were killed mid-run while debugging CARD-0030 (`"Backup failed (joseph exit 20, robin exit 11)."` — exit 20 being rsync's SIGTERM code). Once CARD-0030's `--delete-before --delete-excluded` fix was in place and both accounts were already fully synced, ran the actual script end-to-end (not manual isolated rsync calls) to verify the success path: `"Backup starting."` at launch, both jobs completed with zero errors, `"Backup complete."` at the end.

---

### CARD-0030 · [bug] [photo-server] Re-enable weekly backup cron once Takeout zips are cleared
**Resolution:** Zips deleted 2026-07-09 (818GB reclaimed), cron re-enabled. The manual verification run then failed overnight — `No space left on device` — revealing the primary library (624GB) had genuinely outgrown Momentus (586GB usable), not just a slow first run as assumed.

**Fix: split backup by account across two drives.** Deployed a second backup drive (Seagate 1TB, formatted, mounted at `/mnt/photo-library-backup-joseph`) and rewrote `photo-library-backup.sh` to run two UUID-filtered `rsync` jobs — Joseph's account to the new drive, Robin's to Momentus. Getting this working cleanly took two more rsync flag fixes: `--delete-before` (plain `--delete` defaults to `--delete-during`, which deletes incrementally by directory-walk order — the shared `backups/` dir gets walked before the per-user dirs where the actual space-freeing deletions live, causing a chicken-and-egg failure on an already-full destination) and `--delete-excluded` (none of rsync's `--delete*` variants touch files matched by `--exclude` by default — a protective rsync behavior that meant Joseph's excluded files were never actually being removed from Momentus across two earlier attempts).

**Final verified state (2026-07-10):** both jobs completed with zero errors — Robin's Momentus job dropped from 556G to 207G (matching her ~187GB actual usage), Joseph's new-drive job landed at 420G (matching his ~403GB usage). Full incident writeup in `components/photo-server/backup.md` and `DEVLOG.md`.

**Still open, tracked separately:** CARD-0040 (dashboard visibility not yet verified through a full end-to-end script run — both jobs above were run manually/isolated while debugging) and CARD-0046 (backup drives still have no continuous storage-health monitoring, unlike the primary library).

---

### CARD-0048 · [bug] [photo-server] Stale Immich container bind mount after drive remounts — "Error loading image" on both accounts
**Resolution:** Discovered 2026-07-10 when Joseph reported "beaucoup" thumbnail and full-image load failures on his account, then confirmed Robin had the same issue. Initial theory (I/O contention from the actively-running backup rsync) was wrong — killing the backup didn't fix anything. Root cause: the `immich_server` container's bind mount had gone stale after the day's repeated remounting (read-only, I/O errors, primary library's device path changing `sda`→`sdd`). Confirmed via a specific 404ing asset: the file was genuinely present on disk with correct content, ruling out real data loss — the container just had a broken cached view of the mount. The storage-health check (CARD-0032) had actually been correctly alerting on this the whole time (recurring `Input/output error` every 30-minute cycle for 2+ hours) — the miss was diagnostic, not detection; time was spent chasing the wrong theory first.

**Fix:** `docker compose restart` (all four containers) from `~/immich-app`. Verified immediately: every previously-404ing asset (thumbnail and original) on both accounts returned to `200`. Also confirmed by Joseph directly in the Immich web UI on both accounts.

Runbook note added to `components/photo-server/heartbeat.md`: if storage alerts recur across multiple heartbeat cycles (not just once), especially after any drive remount/unplug/replug event, check the container's actual data access first — a clean host-side mount does not guarantee the running container is looking at it correctly.

---

### CARD-0047 · [enhancement] [photo-server] Daily Immich update-availability check with dashboard notification
**Resolution:** Joseph noticed an Immich update available in the web UI and asked how to manage updates going forward — discussed and agreed on notify-only (not auto-update), given this instance has already surfaced real bugs in a single patch version this week (CARD-0037/0042/0043, the HEIC distortion issue) and the data at stake (irreplaceable family photos) doesn't justify unattended auto-updates.

Built `immich-update-check.py` (deployed to `/usr/local/bin/`) + `immich-update-check.service`/`.timer` (daily, 6:00 AM `America/Phoenix`), following the same MQTT dashboard-notification pattern as CARD-0036/CARD-0040: compares `/api/server/version` against `/api/server/version-check`, publishes `"Immich update available: <latest> (currently running <current>)"` (component `photo-server`, category `System`) when they differ. De-duplicated via a state file so the same pending update doesn't re-notify daily — only fires again if an even newer version appears after the first notice.

First deploy attempt crashed on the state-file write (`/etc/jctsh/` isn't writable by the `jct` user, appropriately, since it holds credentials) — moved the state file to `/home/jct/.jctsh/` and added `os.makedirs`. Verified live 2026-07-10: first corrected run notified correctly (`v3.0.2` vs. running `v3.0.1`), confirmed on the dashboard; second run correctly skipped re-notifying for the same version. Added to `jctsh-network.md`'s Scheduled Maintenance Windows table (6:00 AM daily, no conflicts with existing jobs). Actual update application remains a deliberate manual step, not automated.

---

### CARD-0022 · [enhancement] [infrastructure] Security hardening — infrastructure audit (Steps 1–8)
**Resolution:** All 8 steps complete. Steps 1–5 and 8 passed clean or were fixed on 2026-06-20 (SSH key-only auth, MQTT auth, port audit, Node-RED adminAuth). Step 7 (HA MFA) done 2026-07-09: TOTP enabled for both Joseph and Robin via HA profile → Multi-Factor Authentication Modules. Step 6 (router UPnP) done 2026-07-09: found enabled with zero registered clients, disabled with no functional impact. Full findings in `jctsh-security-hardening.md`. Patterns harvested to `JCTsh-Build-Standards.md` §10 Security Standards (v1.14).

---

### CARD-0023 · [enhancement] [infrastructure] Security hardening — cloud accounts (Steps 9–14 + Final)
**Resolution:** All steps complete. Steps 9–12 and 14 passed clean 2026-06-20 (Ring/Amazon, SmartThings, Google ×2, Windows machine — one stale SmartThings connected app, SharpTools, revoked). Step 13 done 2026-07-09: router admin password rotated to a new strong unique password (`credentials.local.md`), remote/WAN management confirmed disabled, DNS confirmed intentional (CenturyLink/Quantum Fiber bypass-modem setup), firmware found one version behind (1.5.2 → 1.5.3 available) with auto-update now enabled (nightly 3–5 AM) rather than relying on manual checks going forward. Final Step complete: findings harvested to `JCTsh-Build-Standards.md` §10 Security Standards (v1.14).

---

### CARD-0039 · [bug] [photo-server] Re-verify Takeout import completeness — 3,433 assets were genuinely missing
**Resolution:** Following up on the original migration verification discussion, and given CARD-0037 had just found a large ML-processing gap from the same import, re-ran `immich-go upload from-google-photos` (real run, not `--dry-run`, so gaps found would get fixed immediately) against all retained Takeout zips for both accounts — `/mnt/photo-library-backup/takeout-staging/joseph/` (9 zips), `/home/jct/takeout-staging/joseph/` (3 zips), `/home/jct/takeout-staging/robin/` (5 zips). Used the same `--on-errors continue --pause-immich-jobs=false` flags that fixed the original migration's crash patterns, plus `--no-ui --log-file=...` this time for a persisted per-pass log (a gap in the original run). Launched fully detached via `nohup ... & disown` directly on the M8 so it survived independent of the SSH session — relevant since the home internet/network was intermittently down around this time.

**Result:** ran clean in a single pass, no restarts needed, zero upload errors. Found **3,433 assets that were genuinely missing** from Immich and uploaded them (zero data loss risk — upload-only, nothing deleted): 58 (Joseph, backup-drive zips), 119 (Joseph, NVMe-staged zips), 3,256 (Robin). Also found 109 cases where the server's copy was upgraded (better-quality version found in the zip) and 160,701 correctly-matching duplicates confirmed (skipped, no re-upload).

**Notable finding:** Robin's pass had by far the largest gap (3,256 missing) despite her original import being documented as the "clean" one with no crashes/restarts (see `components/photo-server/migration.md`) — this means the missing-asset gap was not caused solely by Joseph's chaotic 5-restart import as originally assumed. Combined with CARD-0037's finding that Robin's ML-processing gap was also worse than Joseph's (96% vs ~80% zero-face rate), there's a consistent pattern that something affected both imports similarly regardless of which one crashed — most likely some shared infrastructure/timing factor from both multi-day imports running through the same M8 around the same period. Root cause not further investigated since the fix (re-run to catch anything missing) resolves it regardless of cause, same reasoning as CARD-0037.

Full run logs retained on the M8 at `/home/jct/immich-go-verify-20260709/` (`joseph-backup.log`, `joseph-home.log`, `robin.log`, `run.out`).

---

### CARD-0032 · [bug] [photo-server] Heartbeat doesn't detect real storage failures (found 2026-07-08)
**Resolution:** `photo-server-heartbeat.py` now writes, reads back, and removes a marker file (`/data/upload/.heartbeat_check`) *inside* the `immich_server` container on every run where the container itself is confirmed up, catching the exact class of failure Docker's own health check misses (it only pings the Immich API, never touches `/data`). A failure is appended to the same `unhealthy` list and reported as `Alert - storage:<error text>`, using the identical non-collapsing path CARD-0029 established for degraded containers. Immediate fix (remount, container restart) and root-cause mitigation (udev auto-remount rule) from the original incident were already in place; this closes the actual monitoring gap.

Live-tested 2026-07-08 by remounting `/mnt/photo-library` read-only (`mount -o remount,ro`) — chosen over physically disconnecting the drive, and over a plain `chmod` on the host-side directory (tried first; silently didn't work, since the container runs as root and root bypasses POSIX permission bits — a read-only remount is enforced at the VFS level instead). Dashboard correctly showed `Immich degraded - storage:sh: 1: cannot create /data/upload/.heartbeat_check: Read-only file system`; remounting read-write restored normal status on the next run. Full writeup in `components/photo-server/heartbeat.md`.

**Still unknown:** the original root physical cause of the USB drive disconnecting in the first place (no clear `dmesg` evidence was captured at the time). Worth checking/reseating the USB cable and capturing full `dmesg` as root if it recurs — not blocking, since the monitoring gap that made it dangerous is now closed.

---

### CARD-0029 · [enhancement] [photo-server] Live-test Immich degraded-heartbeat alert path
**Resolution:** Live-tested 2026-07-08 now that the Immich migration is complete. `docker stop immich_redis` produced `Immich degraded - immich_redis:unhealthy` (then `:starting` during the restart race) as a non-collapsing `Alert` row on the dashboard; `docker start immich_redis` restored normal `System`/online status on the next run. Combined with the CARD-0032 storage-check test in the same session. Full writeup in `components/photo-server/heartbeat.md`.

---

### CARD-0036 · [enhancement] [infrastructure] Dashboard visibility for scheduled reboots
**Resolution:** CARD-0035's scheduled reboots were invisible on the JCTsh log dashboard — confirming success required manually SSHing in and checking `systemctl`/`docker ps`. Added a matched pair of MQTT log messages around each reboot: `scheduled-reboot.service` now publishes `"Scheduled reboot about to occur."` immediately before calling `/sbin/reboot` (multiple `ExecStart=` lines in the oneshot unit), and a new `reboot-complete.service` (enabled via `WantedBy=multi-user.target`) publishes `"Boot complete."` on every boot once the MQTT broker is reachable. Pi publishes as component `jctsh-core` to `jctsh/core/log-server/log` using the existing `jctsh-log-server` MQTT account (`/etc/jctsh/log-server.env`) via `mosquitto_pub` (already installed). M8 publishes as component `photo-server` to `jctsh/server/photo-server/log` using the existing `photo-server` MQTT account (`/etc/jctsh/heartbeat.env`) — required installing the `mosquitto-clients` apt package on the M8 (the heartbeat script uses Python `paho-mqtt` instead, so the CLI wasn't already present). Neither message uses the `"Heartbeat - "` prefix, so each occurrence stays visible as its own dashboard row rather than collapsing. Per-host unit files split out: `scheduled-reboot-pi.service`/`scheduled-reboot-m8.service` replace the old shared `scheduled-reboot.service` (now host-specific since the MQTT broker address, credentials file, and topic differ per host). Verified live 2026-07-08 via manual `systemctl start reboot-complete.service` on both hosts — confirmed on the dashboard (`/data` live view and, after flushing, the persisted `/log` file).

---

### CARD-0037 · [bug] [photo-server] ML processing (faces, smart search, duplicates, OCR) never ran on a large fraction of the library
**Resolution:** Discovered 2026-07-08 while answering Joseph's question about why most photos showed no identified people in Properties. Diagnosed via the Immich API (not guesswork): a random sample showed ~80% of assets with zero detected faces; a targeted CLIP-search sample of clearly-portrait photos still showed clean detection (26/30 correct), ruling out a model-confidence issue. Definitive proof came from a duplicate pair — the exact same restaurant photo (Immich's own duplicate-detection linked the two copies) had 7 faces detected on one copy and 0 on the other.

**Not specific to Joseph's chaotic import:** checked Robin's library too (via her own API key, since search is scoped per-user) — 96% zero-face rate, even higher than Joseph's ~80%, despite her import running clean with no crashes/restarts (see `components/photo-server/migration.md`). This ruled out the 5-restart-import theory as the sole cause and confirmed the gap was server-wide, affecting both accounts roughly equally.

**Fix:** triggered all five affected ML jobs (`faceDetection`, `facialRecognition`, `smartSearch`, `ocr`, `duplicateDetection`) via `PUT /api/jobs/{name}` (`{"command":"start"}`) — Immich has no dry-run mode, so starting each job was simultaneously the diagnostic (revealing real backlogs: ~140,000 for faces, 33,201 for duplicates, ~17,000 each for smartSearch/OCR) and the fix. Checked load average and `vmstat` before/during (CPU-bound at ~60% user time, only 3-7% iowait — not I/O-bound, plenty of headroom on the 12-core M8) to confirm it was safe to run all five concurrently.

**Confirmed complete 2026-07-09** (ran overnight, unaffected by an unrelated home-internet outage since the jobs run locally on the M8): all five queues back to 0 waiting/active, 0 failed for the entire run. M8 uptime at completion check was 19h36m — never rebooted, confirming genuine completion rather than a state reset. Total people clusters grew 2,626 → 3,331 (+705) as full coverage let previously-under-threshold clusters (`minFaces: 3`) surface. Final spot-check: the `868900f1` duplicate that started the whole investigation at 0 faces now shows all 7, with Joseph and Robin correctly matched by name. `duplicateDetection` found 2,197 duplicate groups total once it had full coverage — worth a manual review pass in the Duplicates view when convenient, not urgent.

---

### CARD-0035 · [enhancement] [infrastructure] Weekly scheduled reboot — Pi and M8 photo-server
**Resolution:** Deployed systemd timers on both hosts: `scheduled-reboot.timer` → `scheduled-reboot.service` (`/sbin/reboot`), `Persistent=true`. Pi: Monday 3:00 AM. M8: Monday 4:00 AM — staggered one hour later so the M8 heartbeat script's MQTT publish to the Pi's Mosquitto broker doesn't collide with the Pi being mid-reboot. Not synchronized to KeepConnect's own weekly router reset — that schedule has drifted from its original Wednesday setting, most likely because its "every 7 days" timer restarts from any reset (scheduled or outage-triggered), so it can't be relied on as a fixed weekday anyway; a router reboot's brief network blip is tolerated regardless of timing. Version-controlled unit files in `core/maintenance/`; documented in `SOFTWARE-ENVIRONMENT.md` (Pi) and new `components/photo-server/operations.md` (M8). Verified live via `systemctl list-timers` on both hosts — next run confirmed Mon 2026-07-13. 2026-07-08.

---

### CARD-0033 · [idea] [infrastructure] Document Keep Connect configuration and schedule
**Resolution:** KeepConnect is a standalone router-rebooter device (Johnson Creative KeepConnect-27F8, not a JCTsh component). New dedicated doc `keepconnect.md` created at repo root with full device identity, network config, physical outlet-scoping rationale, and complete monitor/timing/schedule/notification configuration. Linked from `jctsh-network.md` devices table (IP 192.168.1.108, DHCP-reserved) and `ENVIRONMENT.md` Hub & Controller table; added to `README.md` repository layout. Remaining open item (scheduled Pi/Immich reboot via cron, separate from power-strip cycling) carried forward in `keepconnect.md` itself. 2026-07-08.

---

### CARD-0021 · [enhancement] [logging] Device status dashboard
**Resolution:** Added `/status` endpoint to `core/logging/log_server.py`. Two-section layout: Home (Online/Offline/? per component based on heartbeat presence and 70-min threshold) and Remote (`coachproxyos` always shows last-activity + `?`). Auto-detects heartbeat-capable components — salt-sensor shows `?` until CARD-0004 ESPHome migration adds heartbeats. Deployed to Pi 2026-06-30. Added CARD-0024 (coachproxy remote health monitoring via Tailscale ping).

---

### CARD-0018 · [idea] [immich] Self-hosted photo library
**Resolution:** Superseded. Hardware (GMKtec M8) in hand. Replaced by `components/photo-server/` (Immich install + immich-go migration) and `components/photo-tv-display/` (Node.js TV slideshow + phone companion) — full planning docs committed 2026-06-30.

---

### CARD-0014 · [enhancement] [core] Move environmental data pipeline to core
**Resolution:** Moved `environmental-data.gs` → `core/data-pipeline/`, `JCTsh-Environmental-Data-Architecture.md` → `core/data-pipeline/`, and `core/node-red/environmental-data.flow.json` → `core/data-pipeline/`. Updated references across 15 files (CLAUDE.md, README.md, Node-RED-workflow.md, JCTsh-Build-Standards.md, JCTsh-Component-Planning-Pattern.md, JCTsh-Property-Sensor-Pattern.md, all component planning docs, hiking-monitor instructions). 2026-06-30.

---

### CARD-0002 · [enhancement] [infrastructure] MQTT v3.1.1 → v5 upgrade
**Resolution:** Mosquitto 2.0.21 already supports v5 — no broker config change needed. Changed `protocolVersion` from 4 → 5 in the Node-RED broker config node (`core/node-red/core.flow.json`) and updated the live Pi flows.json in place. Confirmed via Mosquitto log: client `nodered-saltlevel` connected with `p5`. ESP32/ESPHome devices unaffected (remain on v3.1.1). 2026-06-30.

---

### CARD-0008 · [enhancement] [hiking-monitor] Pixel hotspot second WiFi field test
**Notes:** Confirmed 2026-06-17 during camping trip. Device connected to JCT Hotspot (IP 10.57.172.159 — Pixel hotspot subnet), reached home MQTT broker via jctsh.duckdns.org over cellular, replayed 7 SPIFFS readings on reconnect. DuckDNS + port 1883 forward confirmed working in the field.

---

### CARD-0017 · [enhancement] [infrastructure] Charging state schema fields for solar/battery sensors
**Resolution:** Added `solar_v` (solar panel voltage, V, ADC voltage divider) to the environmental data schema. Decision: `solar_v` chosen over `charging` boolean (not universally available on all charge controllers) and `charge_current_ma` (requires INA219, overkill). Combined with `battery_v`, charging state is derivable in Node-RED or Sheets as `solar_v > battery_v + ~0.3V`. Added to field reference and Sheets schema in `JCTsh-Environmental-Data-Architecture.md` (v1.4), column Z in `components/hiking-monitor/environmental-data.gs`, and Apps Script redeployed. 2026-06-15.

---

### CARD-0016 · [enhancement] [infrastructure] Offline flash logging — extract reusable standard
**Resolution:** Created `core/offline-logger/sensor_logger.h` — generic template header with `sensor_log_*` function prefix (adapt by renaming to `<name>_log_*` and updating the log file path). Added "Offline Flash Logging" section to `JCTsh-Property-Sensor-Pattern.md` with template adaptation instructions, on_boot mount snippet, on_connect replay block (500ms settle delay), and interval guard (connected → publish, offline → log_write). Removed CARD-0016 from pattern doc Open Gaps. 2026-06-14.

---

### CARD-0015 · [enhancement] [front-porch-temp-sensor] Environmental data pipeline integration
**Resolution:** Added SNTP, humidity/pressure IDs, and 5-min `/data` publish to firmware (temp, humidity, pressure, illuminance, lat/lon H8, rssi, ISO 8601 UTC). Added `illuminance_lx` to the environmental data schema and Apps Script. Node-RED wildcard caught it automatically — no flow changes. OTA flashed 2026-06-14.

---

### CARD-0007 · [idea] [hiking-monitor] Hiking observations pipeline (Tasker → Sheets)
**Resolution:** Tasker widget → Android speech recognition → HTTP POST to Apps Script → Hiking Observations sheet with automatic category classification. No keyword prefix — widget tap is the intent signal. Steps 23–26 complete 2026-06-13.

---

### CARD-0001 · [bug] [garage-radar] Garage-radar false presence on door close
**Resolution:** Ill-defined and no longer applicable — closed.

---

## Defer

### CARD-0027 · [idea] [hiking-monitor] GPIO-controlled power gating for I2C peripherals during sleep — SUPERSEDED by CARD-0070
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
