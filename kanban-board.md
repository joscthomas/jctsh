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

### CARD-0060 · [bug] [infrastructure] Pi running in active soft thermal throttling &mdash; no cooling
**Notes:** Found 2026-07-12 during a Pi health evaluation. `vcgencmd get_throttled` returns `0x80008` (bit 3: soft temperature limit *currently active*; bit 19: has occurred) at a measured 63&ndash;64&deg;C, confirmed on two separate checks. No under-voltage bits set &mdash; power supply is fine, this is purely thermal. No heatsink/fan apparent on this Pi 3B+. Likely compounded by an enclosed/warm install location, matching the pattern of other JCTsh closet-installed devices (photo-server M8, KeepConnect).

**Impact:** the Pi is right now running with reduced ARM clock speed to manage heat. Not causing instability (uptime is solid, no OOM/crash pattern), but is a real, currently-active performance ceiling on the device that hosts Home Assistant, Node-RED, Mosquitto, and the JCTsh log/watchdog server for the whole fleet.

**Resolution path:** add a heatsink and/or small fan (or improve ventilation if it's in an enclosed space), then verify `vcgencmd get_throttled` returns `0x0` (or at minimum clears the "currently active" bit 3) under normal and sustained-load conditions.

---

### CARD-0061 · [enhancement] [infrastructure] Add Docker health check for the Pi's Home Assistant container
**Notes:** Found 2026-07-12 during a Pi health evaluation. The `homeassistant` Docker container has no configured `HEALTHCHECK` &mdash; `docker ps`/`docker inspect` only reflect process liveness, not actual HA responsiveness. Same class of blind spot already found and fixed on photo-server (CARD-0032/CARD-0046: Docker's own health check only pings the API, doesn't verify real functionality) &mdash; HA is arguably the single most critical container on the Pi, since it's the sole bridge to SmartThings/Google Home for the whole house.

**Resolution path:** add a `HEALTHCHECK` to the HA container definition (e.g. curl against HA's own `/api/` or a lightweight endpoint, on an interval), following the same live-test-by-deliberately-breaking-it discipline already used for CARD-0029/CARD-0032/CARD-0046 before closing.

---

---

### CARD-0063 · [idea] [infrastructure] NetAlertX MQTT event richness experiment + log dashboard wiring
**Notes:** Raised 2026-07-12, deferred from CARD-0059. Whether NetAlertX's MQTT plugin publishes rich, human-readable event text (new device / down / reconnected, with name/MAC/IP) or only structured Home-Assistant-discovery-style state (per-device online/offline binary sensor + aggregate counts) is genuinely unclear from the docs — there was an open GitHub feature request (#1339) to bring MQTT up to webhook-level richness, closed with a "next release/in dev image" label, but not confirmed against the exact `ghcr.io/netalertx/netalertx:latest` image pulled for this deployment.

**Resolution path — a 5-minute live test, not more research:** enable the MQTT plugin in NetAlertX's Settings, point it at the `netalertx` broker account (`credentials.local.md`), unplug or disconnect something on the LAN, and watch what actually publishes to the Pi's Mosquitto broker (`mosquitto_sub -u netalertx -P ... -t '#'` or similar). That resolves the uncertainty directly.

**If rich event text comes through natively:** straightforward — point it at `jctsh/components/netalertx/log` (or translate topic if NetAlertX's own topic naming doesn't match) and it shows up on the existing log dashboard like every other component.

**If it's state-only:** needs a small Node-RED translation flow — subscribe to NetAlertX's HA-discovery-style topics, detect the online/offline transitions and new-device flags, and republish as proper `{"component":"netalertx","category":...,"message":...}` JSON to the `jctsh/` topic the log dashboard expects.

**Sequencing — validate through practical use before doing this work:** a one-time naming pass isn't the bar. Don't start this card until NetAlertX has actually been lived with for a while — checked periodically, devices named as new ones show up, genuinely relied on instead of ignored — and it's held up as worth keeping. CARD-0059 closed on the naming workflow being confirmed, not on weeks of real usage, so that confirmation is a starting signal, not proof this integration is worth building. If the tool quietly stops getting used, this card should stay parked, not get built on the strength of day-one enthusiasm.

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

### CARD-0045 · [bug] [hiking-sensor] `wifi.ap:` fallback may prevent `reboot_timeout` from working
**Notes:** Found 2026-07-09 while researching a timeout decision for air-quality-monitor (which follows hiking-sensor's firmware pattern). `hiking-sensor.yaml`'s `wifi:` block has no explicit `reboot_timeout` override, so it relies on ESPHome's default (15 minutes before rebooting on failed WiFi connection). However, ESPHome's own issue tracker (esphome/issues#7222) documents that `reboot_timeout` does not apply when a `wifi.ap:` fallback block is configured — and hiking-sensor's config does have one (`ap: ssid: "hiking-monitor-fallback"`). So the 15-minute default may not actually be functioning as designed on the currently-deployed device.

**Priority: low.** Hiking-sensor's upload/home mode requires USB dock power to stay awake (same architecture as air-quality-monitor's charging-based home mode) — if the bug does prevent the reboot from firing, the device would get stuck awake trying to reconnect, but on USB power, not draining battery. No confirmed real-world failure — CARD-0008's actual field test (2026-06-17 camping trip) succeeded without issue. Worst case is a minor operational annoyance (stuck device needing a physical USB reflash to recover), not data loss or a safety risk.

**Resolution path:** confirm whether hiking-sensor actually needs the `ap:` fallback block at all (original rationale not documented in current firmware/docs — may be leftover from early development). If not needed, remove it and the default `reboot_timeout` should function normally. If needed, find an alternative bounded-recovery mechanism that doesn't conflict with the AP fallback.

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

### CARD-0027 · [idea] [hiking-sensor] GPIO-controlled power gating for I2C peripherals during sleep
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

### CARD-0025 · [enhancement] [hiking-sensor] Test retired LiPo battery — good or bad?
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
4. For a more representative load matching the real device's WiFi-connect current spike (rather than just baseline boot current), optionally flash the spare ESP32 with `hiking-sensor.yaml` first — but change `esphome: name:` first (e.g. `hiking-monitor-test`) so it doesn't collide with the real device's hostname/MQTT identity while both exist.

**Caveat:** neither tier can rule out a slow-forming internal short with full certainty — that needs a proper battery analyzer/ESR meter, probably not worth owning for an ~$8 cell when 2 known-good spares are already on hand.

**Outcome:** Passes both tiers → may be returned to spare stock (log that it had this incident, in case it recurs). Fails either tier → retire and recycle per JCTsh-Build-Standards.md §2.14 (tape JST terminals, recycle at a battery drop-off — Home Depot/Lowe's/Batteries Plus — never household trash).

**Related:** CARD-0026 (measure hiking-monitor sleep-mode current draw) uses the same tester rig built for Tier 2 here — do them together in one bench session rather than building the rig twice.

---

### CARD-0026 · [enhancement] [hiking-sensor] Measure hiking-monitor sleep-mode current draw
**Notes:** The hiking-monitor's actual standby battery life is unknown. The ESP32's own deep-sleep draw is negligible (~10µA), but `VOUT+` runs directly to the ESP32's `VIN` with the switch NOT in the power path, so the TP4056+boost module stays active even while the ESP32 sleeps — its quiescent current (undocumented by the manufacturer, plausibly 1-5mA for a cheap module) is almost certainly the real bottleneck. This measurement gives an actual number instead of a guess.

**Reuses the CARD-0025 tester rig** (spare ESP32 from Bag 1 + spare TP4056 from Bag 8) — build both cards in the same bench session.

**Setup:**
1. Flash the spare ESP32 with `hiking-sensor.yaml`, but change `esphome: name:` first (e.g. `hiking-monitor-test`) so it doesn't collide with the real device's hostname/MQTT identity. First flash must be via USB.
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

*Hiking sensor connection:*
Trail elevation makes frost far more likely than at home — the Santa Catalinas rise from ~2,500 ft (Tucson) to 9,000+ ft, roughly 3.5°F cooler per 1,000 ft of gain (~23°F colder at the summit). The hiking sensor measures actual temp and humidity at trail elevation, so it has everything needed to compute dew point and frost point in the field. Two integration points:
- **E-ink display** — add frost point or a frost risk indicator to the display when temp is below a threshold (currently shows temp, humidity, pressure trend, UV, battery)
- **Replay pipeline** — after a hike, the archived temp/humidity records correlated with the GPS track show where on the trail frost conditions existed, for future planning
- **Hike selection** — frost conditions at home (front porch sensor) combined with known elevation lapse rate could inform which trail to choose. If overnight low at 2,500 ft was 42°F, frost point was 28°F, and a trail peaks at 7,000 ft, surface frost is likely above ~5,500 ft. This becomes a reason to seek out a higher-elevation hike specifically to experience frost conditions in the desert.

**UV alert** — LTR-390 already reports UV index. Notify when UV index exceeds a threshold (e.g., 6+) for outdoor activity or plant protection planning.

**Plant protection reminder** — when frost risk is non-zero, notify to cover sensitive plants. Seasonal (December–February in Tucson).

---

### CARD-0044 · [idea] [remote-temp-sensor-01] Backyard solar/battery environmental sensor
**Planning docs:** `components/remote-temp-sensor-01/JCTsh-remote-temp-sensor-01-phase1.md` (Phases 1–3), `components/remote-temp-sensor-01/remote-temp-sensor-01-claude-code-instructions.md` (Phase 4)
**Notes:** Started 2026-07-09 as a "replicant" of front-porch-temp-sensor, diverged into a separate component once the location moved from the sheltered porch to full-sun backyard. Phases 1–4 complete. Sensors: BME280 + BH1750 + LTR-390. Power: single swappable EVE 18650 + AEDIKO charger/holder + SUNYIMA solar panel — everything on hand, zero purchases. Firmware: 5-minute wake/publish/deep-sleep cycle (continuous WiFi not viable on this solar panel — ~10x power shortfall). Sensor power gated during sleep via an on-hand BC557B PNP transistor high-side switch (substitutes for a P-FET, same CARD-0027 pattern from hiking-sensor). AEDIKO module's own quiescent current is unmeasured — bench Step 6 of the instructions doc tests it, with a TPL5111 nanopower timer as a contingent (not assumed) mitigation if it's significant. SmartThings/Google Home exposure planned; no LEDs. Deliberately scoped smaller than weather-station (CARD-0011) — no wind/rain/lightning.

**Split into two phases of work, same pattern as hiking-sensor:** the Phase 4 instructions cover only the bench electronics/firmware build (breadboard → perfboard, sensors, power switch, deep-sleep cycle, battery/solar validation). Enclosure design (real weatherproof build with a sun-shielding vent reusing hiking-sensor's louvered vent-insert pattern, plus a separate battery-access hatch) and backyard installation are deliberately deferred to a follow-on planning pass once the electronics are proven — mirrors the CARD-0009 split on hiking-sensor. Second entry in the 3D-printing backlog behind hiking-sensor's enclosure. Ready for Phase 5 (execution) when directed.

---

### CARD-0020 · [enhancement] [hiking-sensor] Hike data visualization (Looker Studio)
**Notes:** Build a Google Looker Studio dashboard connected to the GPS Track and Environmental Data Google Sheets. GPS route on a map, sensor readings (temp/humidity/pressure/battery) over hike duration. Review-after-the-fact use case — no real-time requirement. No new infrastructure needed.

---

### CARD-0012 · [idea] [air-quality-monitor] Air quality monitor
**Planning docs:** `components/air-quality-monitor/JCTsh-air-quality-monitor-phase1.md` (Phases 1–3), `components/air-quality-monitor/air-quality-monitor-claude-code-instructions.md` (Phase 4)  
**Notes:** Portable clip-mounted SEN55 air quality sensor (PM1.0/2.5/4.0/10, VOC, NOx) carried on hikes alongside the hiking monitor. Phases 1–4 complete (2026-07-09). Parts confirmed on hand: SEN55, Adafruit #5964 adapter, JST GH cable — `jctsh-parts-inventory.md`'s SparkFun SEN-23715 entry was mislabeled "SEN54," corrected to reflect it's the genuine SEN55. SEN55 sensor reading uses ESPHome's native `sen5x` platform (no custom component needed there); a custom component is still needed for onboard flash logging + WiFi replay, adapted from hiking-sensor's `hiking_logger.h`. SEN55 power-gated via an on-hand BC547B NPN transistor (same substitution pattern as remote-temp-sensor-01's BC557B) — bench-tested current draw, not just calculated, in Phase 4 Step 6. Follows hiking-monitor's firmware pattern (onboard flash logging, WiFi replay, field/home mode) exactly — that pattern is field-proven (CARD-0008), and the dependency is architectural only, **not** gated by hiking-sensor's still-open enclosure (CARD-0009). Phase 3 timeout policy matches hiking-sensor but explicitly avoids inheriting CARD-0045's `wifi.ap:`/`reboot_timeout` bug. Perfboard footprint measurement and LiPo polarity check moved from Phase 2 planning blockers to Phase 4 bench steps. Clip-case enclosure (with SEN55 intake/exhaust ports — orientation guidance currently flagged low-confidence, needs re-verification) deferred to a follow-on card, same split as hiking-sensor/remote-temp-sensor-01. Ready for Phase 5 (execution) when directed.

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

### CARD-0034 · [idea] [personal] Complete digital-identity-protection-checklist.md
**Notes:** Work through `digital-identity-protection-checklist.md` (repo root) — Joseph and Robin's personal security checklist closing single-point-of-failure risks (carrier port-out PIN, 2FA off SMS, credit freezes, password manager, household verification protocol, incident response plan). Almost entirely manual actions by Joseph/Robin themselves (phone calls to carriers/bureaus, account settings changes) — not something Claude Code can execute directly, but worth tracking to completion since it's currently all unchecked. Also has an "Open Items to Fill In" section (list specific banks/brokerages in use, confirm current password manager/2FA setup, set a 6-month review date) that needs input from Joseph before those parts can be finished.

**Blocked (2026-07-11):** waiting on delivery of Google Titan Security Key hardware authenticators (3 ordered) — needed for the hardware-key 2FA portion of the checklist before those items can be checked off.

---

### CARD-0003 · [enhancement] [infrastructure] TLS for Mosquitto (port 8883)
**Notes:** Port 1883 is internet-exposed via DuckDNS/port-forward with fail2ban, but credentials and sensor data are cleartext for any device using that path. TLS on 8883 eliminates this — scoped as a **split-port design**, not a fleet-wide switch: 1883 stays plaintext and LAN-only (not forwarded through the router), continuing to serve stationary home devices (garage-radar, salt-sensor, front-porch-temp-sensor, remote-temp-sensor-01, etc.) with no `secrets.yaml`/firmware changes needed. 8883 (TLS) becomes the *only* port forwarded via DuckDNS, used exclusively by devices that actually leave the home network — hiking-sensor today, air-quality-monitor once built (CARD-0012, "carried on hikes alongside the hiking monitor"). Steps: get Let's Encrypt cert for the DuckDNS hostname (certbot with duckdns plugin), add a TLS listener on port 8883 in mosquitto.conf, change the router port-forward from 1883→8883, add CA-cert trust config + updated broker port to the remote-capable devices' `secrets.yaml`/`mqtt:` block, reflash those devices only, update Node-RED broker node / HA MQTT integration if either connects over the forwarded path. CARD-0002 prerequisite complete.

**Decision rationale (2026-07-10):** considered reflashing the whole fleet uniformly vs. this split; chose the split because most devices are stationary and never traverse the internet-facing path, so fleet-wide TLS would add CA-cert config/maintenance to every device for no real exposure reduction on the stationary ones. This card protects only the internet-exposed path (roaming devices via DuckDNS/port-forward); it does not encrypt LAN-local port 1883 traffic for stationary devices — that residual, accepted risk is documented under CARD-0050, which was deprioritized 2026-07-10 on its own risk-analysis merits (see that card — CARD-0003 was mistakenly framed there at first as a substitute for it and later corrected).

**Unblocked (2026-07-10):** CARD-0004 (salt-sensor Arduino → ESPHome migration) is complete except one open verification item (12h reading cycle hasn't fired naturally yet) — doesn't block this card either way, since salt-sensor is a stationary device staying on plaintext LAN-only 1883 under the split-port design.

**Execution plan:** `C:\Users\jcthomas\.claude\plans\misty-fluttering-porcupine.md` (Claude Code plan file, not in this repo) — five phases: A) Pi/certbot cert issuance, B) Mosquitto TLS listener, C) router port-forward, D) hiking-sensor CA-trust config + OTA reflash, E) cutover + doc updates. Approved 2026-07-10.

**Progress (2026-07-10):** Phases A–C complete, Phase D in progress. Moved Planning → Build to reflect that this card skipped straight from an approved execution plan into live implementation, rather than following the Design (ESPHome Claude Code instructions) step that column normally implies.
- **Phase A (cert):** done. Retried past the earlier DuckDNS DNS flakiness (see prior note, now resolved) — cert issued for `jctsh.duckdns.org`, expires 2026-10-08. Deploy-hook (`core/mqtt/mosquitto-cert-deploy-hook.sh`, deployed to `/etc/letsencrypt/renewal-hooks/deploy/mosquitto-reload.sh`) copies renewed certs into `/etc/mosquitto/certs/` and restarts Mosquitto; `certbot renew --dry-run` and `certbot.timer` both confirmed working.
- **Phase B (Mosquitto TLS listener):** done. `core/mqtt/mqtt-tls.conf` deployed to `/etc/mosquitto/conf.d/`. Hit and fixed a real gotcha: `password_file`/`allow_anonymous` can't be redeclared per-listener when `per_listener_settings` is false (the default, and true here) — they're global once set in `local.conf`; redeclaring caused a "Duplicate password_file value" error. Fixed by dropping those lines from the new file. Verified: both 1883 and 8883 listening, TLS handshake against `localhost:8883` and against the public `jctsh.duckdns.org:8883` (from the Pi, exercising the real router path) both return a valid cert chain (`Verify return code: 0`).
- **Phase C (router forward):** done. New `8883 → 192.168.1.117:8883` rule added (Joseph, manually, via the router admin UI — browser automation couldn't drive this router's admin SPA, it never reached an "idle" state for the extension's tooling). Existing 1883 rule deliberately left in place until Phase E cutover.
- **Phase D (hiking-sensor):** in progress. `secrets.yaml` (`mqtt_ca_cert`, ISRG Root X1, expires 2030-06-04) and `hiking-sensor.yaml`'s `mqtt:` block (`port: 8883`, `certificate_authority`, `idf_send_async: false`) updated and compile clean. **Blocked:** OTA upload timed out — device is currently off/in a drawer, not on WiFi. Needs to be on USB dock power (upload mode) before the reflash can proceed.
- **Phase E (cutover + docs):** not started.

Execution detail/history: `C:\Users\jcthomas\.claude\plans\misty-fluttering-porcupine.md`.

---

### CARD-0009 · [enhancement] [hiking-sensor] Enclosure design and build
**Notes:** Design and build the permanent enclosure. Field prototype (two-board sandwich) documented in `components/hiking-sensor/enclosure-prototype.md`. Standoffs arrive 2026-06-14; temp enclosure build before camping trip departure 2026-06-15. Device will be used in the field for ~2 weeks on that trip — hiking and van sensor simulation. Full 3D-printed permanent enclosure is a later step.

**LTR-390 rewiring (2026-07-12):** in progress. Replacing the LTR-390's soldered 0.1" male headers with a 150mm STEMMA QT / Qwiic cable (Adafruit #4209, `jctsh-parts-inventory.md` Bag 31) plugged into the sensor's STEMMA QT port, with the male-header end going into the perfboard's existing LTR-390 female header (unchanged). Gives slack to mount the sensor at the correct sky-facing orientation in the enclosure independent of the perfboard's own orientation — this is what the enclosure build actually needed the flexibility for. Only the sensor-side segment changes; perfboard-to-ESP32 traces (GPIO21/GPIO22) untouched. Docs updated: `wiring.md` (new wire-color table — STEMMA QT cable colors are SDA/SCL-swapped from the old breadboard colors, flagged explicitly), `perfboard-layout.md` (dated addendum on the LTR-390 header row, original build history kept intact).

**Don't close until:** rewiring physically complete and I2C communication re-verified (LTR-390 still detected at 0x53, UV/light readings sane) after reassembly.

---

### CARD-0049 · [enhancement] [salt-sensor] Move from breadboard to perfboard
**Progress (2026-07-10):** Follow-on to CARD-0004 (ESPHome migration). Moved all three LEDs off their original breadboard pins onto a perfboard-friendly layout: Red GPIO2→GPIO32, Yellow GPIO15→GPIO33, Green GPIO4→GPIO27 — gets Red/Yellow off strapping pins entirely and lines all three LEDs up on the same header row (left pins 7/8/11) for easier soldering. GPIO25/26 (DAC1/DAC2) were considered since they sit physically between GPIO32/33 and GPIO27, but ruled out — GPIO25 is confirmed broken for digital output in ESPHome/Arduino, GPIO26 avoided as a precaution for the same DAC-reinit reason. Trig (GPIO5) and Echo (GPIO18) unchanged.

Updated `salt-sensor.yaml` (wiring comment + `output:` block), `components/salt-sensor/CLAUDE.md`, and `components/salt-sensor/ESP32-project-pins.md` to match. Physical rewiring done; reflashed over OTA and field-verified — LEDs confirmed matching the `ok` status (green solid, red/yellow off) on the new pins, MQTT `/data` and `/status` reporting normally post-flash.

**Don't close until:** perfboard is actually soldered (current state is rewired breadboard, not yet transferred to perfboard) and the sensor survives a reboot/power-cycle on the new pins without issue.

---

## Done

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
**Resolution:** Moved `environmental-data.gs` → `core/data-pipeline/`, `JCTsh-Environmental-Data-Architecture.md` → `core/data-pipeline/`, and `core/node-red/environmental-data.flow.json` → `core/data-pipeline/`. Updated references across 15 files (CLAUDE.md, README.md, Node-RED-workflow.md, JCTsh-Build-Standards.md, JCTsh-Component-Planning-Pattern.md, JCTsh-Property-Sensor-Pattern.md, all component planning docs, hiking-sensor instructions). 2026-06-30.

---

### CARD-0002 · [enhancement] [infrastructure] MQTT v3.1.1 → v5 upgrade
**Resolution:** Mosquitto 2.0.21 already supports v5 — no broker config change needed. Changed `protocolVersion` from 4 → 5 in the Node-RED broker config node (`core/node-red/core.flow.json`) and updated the live Pi flows.json in place. Confirmed via Mosquitto log: client `nodered-saltlevel` connected with `p5`. ESP32/ESPHome devices unaffected (remain on v3.1.1). 2026-06-30.

---

### CARD-0008 · [enhancement] [hiking-sensor] Pixel hotspot second WiFi field test
**Notes:** Confirmed 2026-06-17 during camping trip. Device connected to JCT Hotspot (IP 10.57.172.159 — Pixel hotspot subnet), reached home MQTT broker via jctsh.duckdns.org over cellular, replayed 7 SPIFFS readings on reconnect. DuckDNS + port 1883 forward confirmed working in the field.

---

### CARD-0017 · [enhancement] [infrastructure] Charging state schema fields for solar/battery sensors
**Resolution:** Added `solar_v` (solar panel voltage, V, ADC voltage divider) to the environmental data schema. Decision: `solar_v` chosen over `charging` boolean (not universally available on all charge controllers) and `charge_current_ma` (requires INA219, overkill). Combined with `battery_v`, charging state is derivable in Node-RED or Sheets as `solar_v > battery_v + ~0.3V`. Added to field reference and Sheets schema in `JCTsh-Environmental-Data-Architecture.md` (v1.4), column Z in `components/hiking-sensor/environmental-data.gs`, and Apps Script redeployed. 2026-06-15.

---

### CARD-0016 · [enhancement] [infrastructure] Offline flash logging — extract reusable standard
**Resolution:** Created `core/offline-logger/sensor_logger.h` — generic template header with `sensor_log_*` function prefix (adapt by renaming to `<name>_log_*` and updating the log file path). Added "Offline Flash Logging" section to `JCTsh-Property-Sensor-Pattern.md` with template adaptation instructions, on_boot mount snippet, on_connect replay block (500ms settle delay), and interval guard (connected → publish, offline → log_write). Removed CARD-0016 from pattern doc Open Gaps. 2026-06-14.

---

### CARD-0015 · [enhancement] [front-porch-temp-sensor] Environmental data pipeline integration
**Resolution:** Added SNTP, humidity/pressure IDs, and 5-min `/data` publish to firmware (temp, humidity, pressure, illuminance, lat/lon H8, rssi, ISO 8601 UTC). Added `illuminance_lx` to the environmental data schema and Apps Script. Node-RED wildcard caught it automatically — no flow changes. OTA flashed 2026-06-14.

---

### CARD-0007 · [idea] [hiking-sensor] Hiking observations pipeline (Tasker → Sheets)
**Resolution:** Tasker widget → Android speech recognition → HTTP POST to Apps Script → Hiking Observations sheet with automatic category classification. No keyword prefix — widget tap is the intent signal. Steps 23–26 complete 2026-06-13.

---

### CARD-0001 · [bug] [garage-radar] Garage-radar false presence on door close
**Resolution:** Ill-defined and no longer applicable — closed.

---

## Defer

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

**Relationship to CARD-0003 (corrected 2026-07-10):** these are NOT substitutes for each other, despite both touching MQTT/network security. CARD-0003 (TLS on 8883) only covers the *internet-exposed* path used by roaming devices (hiking-sensor, air-quality-monitor) — it deliberately leaves LAN-local port 1883 traffic in plaintext for stationary devices (see `CLAUDE.md` "LAN security": "Acceptable for a home network; no mitigation planned"). CARD-0050 was about a different threat — an already-on-LAN attacker sniffing/spoofing that same plaintext 1883 traffic — which CARD-0003 does nothing for. CARD-0050 is deprioritized on its own risk-analysis merits above, not because CARD-0003 covers it. Revisit CARD-0050 only if a future router/hardware upgrade makes real VLAN segmentation available, or if the device inventory or threat picture changes such that the cost/benefit shifts.
