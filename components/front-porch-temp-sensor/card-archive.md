# front-porch-temp-sensor — Card Archive

Historical record of archived Done/Defer kanban cards for this component (CARD-0193's archiving process, migrated to this dedicated file by CARD-0290 — previously these were appended directly into `CLAUDE.md`, which grew unboundedly and stopped being practical to read in full). **Not read as part of routine Session Start or component-session startup** (`JCTsh-Component-Session-Start.md`) — on-demand lookup only. See this component's own `CLAUDE.md` for current, curated context.

---

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 5639B, over the 5000B size threshold.

### CARD-0165 · [enhancement] [front-porch-temp-sensor] Ask Google Home for the front porch temperature — RESOLVED 2026-08-14
**Status:** Done

**Raised 2026-08-14, mid-CARD-0159 session.** Voice query — "Hey Google, what's the front porch temperature?" — should answer from the existing sensor, no new hardware.

**Confirmed low-effort, entity already exists and already in production use:** `sensor.front_porch_temp_sensor_temperature`, published via the `front-porch-temp-sensor` ESPHome component's MQTT discovery (`discovery_prefix: homeassistant` in `components/front-porch-temp-sensor/front-porch-temp-sensor.yaml`). Already consumed by two real HA automations (`automation-front-porch-cool-open-door.yaml`, `automation-front-porch-warm-close-door.yaml`), so the entity is known-reliable, not something to newly trust.

**Approach:** expose this one entity to Google Assistant via the Nabu Casa integration already active on this HA instance (Settings → Home Assistant Cloud → Google Assistant → expose entity) — no new integration, no SmartThings involvement, same mechanism CARD-0146/CARD-0164's research identified as available for voice-bridging without SmartThings as a middleman.

**Interview note (2026-08-14):** set a clean voice alias (e.g. "Front Porch Temperature") rather than exposing under the entity's auto-generated friendly name — Joseph's preference, for natural voice matching and a sensible spoken response. **Turned out unnecessary** — checked the entity registry directly and its `name` is already "Front Porch Temperature" (overriding `original_name: "Temperature"`), already clean for voice purposes.

**Built 2026-08-14 — exposure toggle done via HA's WebSocket admin API** (the entity-exposure setting lives in the entity registry's `options.cloud.google_assistant.should_expose` field, not reachable through the plain REST API — used the `homeassistant/expose_entity` WS command instead of the UI). Confirmed via the registry directly: `cloud.google_assistant.should_expose` flipped `false` → `true`. No manual "sync now" service exists in this HA version (`2026.8.1` — the old `cloud.google_actions_sync` service is gone from the `cloud` domain's service list); exposure changes appear to sync automatically now.

**Area assigned, 2026-08-14.** Checked and found neither the entity nor its parent device had an HA Area — meaning it would show up "unassigned" in the Google Home app and room-based phrasing wouldn't work (only the direct entity-name phrasing would). Assigned the parent device (`Front Porch Sensor`) to the area. **Real mistake caught and fixed in the same pass**: an exact-string area-name check missed the existing `Porch (Front)` area (already used by the doorbell/front-door entities) due to word-order difference, and created a duplicate `Front Porch` area instead. Caught immediately, device reassigned to the correct existing `Porch (Front)` area, duplicate deleted — confirmed via `area_name()` template that the entity now correctly resolves to `Porch (Front)`, no orphaned duplicate left behind.

**Real blocker found and fixed: Google Assistant was never actually linked to HA at all.** Checked HA Cloud's status directly (`cloud/status` over the WS API) — `"google_registered": false`. Nabu Casa Cloud itself was connected (remote access, SmartThings OAuth callback), but the Google Assistant link specifically — a separate one-time step inside the Google Home app itself (Settings → linked services → link "Home Assistant") — had never been completed. Every exposure/area change up to that point was real but inert, since nothing was actually syncing to Google. Joseph completed that linking step; the device then appeared in Google Home.

**Second issue, voice-query-specific: Google answered from the wrong device even with an exact name/phrase match.** Asking "what's the front porch temperature" (matching the device's exact Google-side name) kept answering with a pre-existing SmartThings front-door sensor's reading instead — confirmed that sensor is a SmartThings multi-purpose contact sensor (door open/close + temperature + battery), not Ring, and explicitly *not* exposed via HA's Google Assistant setting, so the collision wasn't an HA-side config problem. Root cause: Google Assistant appears to route temperature-type queries by room/context rather than literal device name, unlike most other device queries — confirmed by testing "what's the **porch** temperature" (dropping "front") and getting the correct answer. The word "front" itself was steering Google toward the front-door sensor via some room/primary-sensor association on Google's own side, outside HA's or this repo's control.

**Verified live, 2026-08-14 — Joseph confirmed "what's the porch temperature" correctly returns the front porch sensor's reading.** Satisfies the card's own "or a natural phrasing close to it" clause. The literal "front porch temperature" phrasing still collides with the SmartThings sensor on Google's side; not pursued further since a working natural phrasing already exists and the collision lives entirely in Google's room-routing logic, not anything this repo can fix.

**Done when:** "Hey Google, what's the front porch temperature?" (or a natural phrasing close to it) reliably returns the current reading, tested live, not just configured. ✅ — via "what's the porch temperature."

**Related:** `components/front-porch-temp-sensor/` (the existing sensor this exposes), CARD-0146/CARD-0164 (where Nabu Casa's Google Assistant bridge was identified as an alternative to SmartThings for reaching Google Home).

---

**Archived from `tos/kanban-board.md` on 2026-09-16 (CARD-0193)** — 94 days since last touched, over the 90-day backup threshold.

### CARD-0015 · [enhancement] [front-porch-temp-sensor] Environmental data pipeline integration
**Status:** Done

**Resolution:** Added SNTP, humidity/pressure IDs, and 5-min `/data` publish to firmware (temp, humidity, pressure, illuminance, lat/lon H8, rssi, ISO 8601 UTC). Added `illuminance_lx` to the environmental data schema and Apps Script. Node-RED wildcard caught it automatically — no flow changes. OTA flashed 2026-06-14.

---

**Archived from `tos/kanban-board.md` on 2026-09-27 (CARD-0193)** — 8291B, over the 5000B size threshold.

### CARD-0333 · [enhancement] [front-porch-temp-sensor] [back-patio-temp-sensor] Boot-time heartbeat — every reboot of a 30-minute-heartbeat device raises a false watchdog alert — RESOLVED 2026-09-24 18:54 MST
**Status:** Done

**Raised 2026-09-24 17:10 MST (Joseph: "yes, open a card for it, then do it for both"), moved straight to Build on the same explicit decision** — the plan is small and fully specified below, no separate Planning pass needed.

**Problem.** Both ESPHome devices publish their heartbeat from `interval: 30min`, which counts from *boot*. The Node-RED watchdog alerts at 35 minutes without one. So any reboot that lands more than ~5 minutes after a heartbeat leaves a gap of up to ~60 minutes before the next one, and a `silent for 35 minutes` alert fires even though the device is up. Not theoretical — three false alerts on 2026-09-24 alone, each landing exactly heartbeat + 35 min after a deliberate reboot/move of the back-patio board (15:25:35, 16:17:06, 17:05:53), each verified against pings and the broker log as a healthy, connected device. ~~Same mechanism also leaves `/status` showing `Offline` for up to 30 minutes after every reboot~~ **(wrong, corrected 2026-09-24: the log server's freshness threshold is 70 minutes, `_HOME_HB_THRESHOLD_MIN`, so a reboot alone never flips `/status` to Offline — it showed Offline only after the real outages)**, and these alerts teach everyone that a silence alert is noise, which is how the real 2026-09-21 outage got read as a ~35-minute blip.

**Fix.** Move the heartbeat publishes (log line, `.../heartbeat` topic, and the two read-failed Alerts) into an ESPHome `script`, called from both the existing 30-minute `interval` and a new `esphome: on_boot` that waits 90 s first. 90 s is deliberate: the BME280/BH1750 poll every 60 s, so by then a real reading exists and the read-failed Alerts stay meaningful instead of firing on every boot. **As shipped, one addition:** after the 90 s delay the boot automation does `wait_until: mqtt.connected` before calling the script, because `mqtt.publish` silently drops when disconnected and a post-boot reconnect at the patio was observed to take ~54 s (front-porch takes ~5 s). Net effect: the first heartbeat arrives ~90 s after boot instead of ~30 min, and the 30-minute cadence continues unchanged after that.

**Scope.** `front-porch-temp-sensor.yaml` and `back-patio-temp-sensor.yaml` — they share the heartbeat block apart from names and coordinates, verified by diff. Both get OTA-flashed. Front-porch is a production device (it drives the warm/close-door and cool/open-door notifications), so its flash is checked for entity continuity afterward.

**Non-goals.** No change to the watchdog flow or its 35-minute threshold; no change to the 30-minute cadence; no change to heartbeat payload formats; no change to front-porch's discovery `unique_id`s (they stay on the legacy generator, per CARD-0186's reasoning about orphaning live entities). Other ESPHome devices very likely have the same gap — not touched here, see follow-up.

**Done when:** (1) both devices flashed and the new firmware confirmed running (reported config hash matches the build); (2) after a deliberate reboot of each, a heartbeat appears within ~2 minutes and no watchdog alert follows (~~and `/status.json` reports Online without waiting 30 minutes~~ — struck, see the corrected Problem paragraph: it never went Offline on a reboot); (3) the 30-minute cadence still continues afterward; (4) front-porch's four HA entities are unchanged — same entity ids, still updating; (5) both YAMLs committed.

**Built and verified live, 2026-09-24 18:15 MST.** Both YAMLs changed by ~20 lines (`esphome: on_boot` + a shared `script: send_heartbeat`), committed with this card. Flashed OTA: back-patio config hash `0x8e2c0226`, front-porch `0x5921875a`, each confirmed from the device's own retained discovery message and (back-patio) by recompiling the committed YAML to the identical hash.
- **Boot heartbeat arrives ~90 s after boot, with a real temperature, on both:** back-patio restarts at 17:20:15, 17:37:56 → heartbeats 17:21:45, 17:39:26 (+90 s exactly); front-porch OTA boot ~18:06:08 → 18:07:38, and a deliberate restart 18:08:47 → 18:10:17.
- **No watchdog alert followed any of ~8 reboots** (last alert on the board is the 17:05:53 false alarm that prompted this card).
- **30-minute cadence continues:** back-patio's next beat landed 18:07:57, exactly boot + 30:00. Front-porch's is due ~18:38:47 (boot 18:08:47 + 30:00) — see the marker below.
- **Front-porch continuity:** all four sensor entities keep their entity ids and update normally; the warm/close and cool/open automations are untouched.
- **Reflection — an OTA gotcha that cost real time here: do not reboot a device within ~60 s of flashing it.** ESP32 OTA has automatic rollback: if the new image reboots before it is marked valid (~60 s, the `safe_mode` "Boot seems successful" line), the bootloader silently reverts to the previous firmware. I pressed restart on front-porch 12 s and then 19 s after two flashes, so it rolled back to its original firmware (`0xbd1d7376`) both times; every "front-porch didn't send a heartbeat" observation in between was the OLD firmware, and an `on_connect`-triggered variant I tried in that window was never actually running — untested, not disproven, and reverted in favor of the design that was verified on back-patio. Verify the *reported* config hash after every flash and wait past the ~60 s mark before restarting. Recorded in both components' `flashing.md`.

**Auto verify (RESOLVED 2026-09-24 18:54 MST, see the resolution note below):** — confirm front-porch's own 30-minute interval heartbeat arrived around 18:38:47 (`grep 'front-porch-temp-sensor | System   | Heartbeat' /mnt/jctsh-logs/jctsh.log*` on the Pi, or `/status.json` `last_seen` advancing), i.e. that moving the heartbeat into a script did not break the regular cadence there. If it did, `interval: 30min` → `script.execute` is the suspect. Once confirmed, edit this marker line so it stops matching, and move the card to Done.

**Resolution, 2026-09-24 18:54 MST.** The Auto verify passed: front-porch's own 30-minute beat landed at 18:38:50 (its restart at 18:08:47 + 30:00) and back-patio's at 18:37:57 (17:37:56 + 30:01), so moving the heartbeat into a script did not disturb the regular cadence. All five Done-when criteria are met, and the two devices' reported config hashes (`0x5921875a` front-porch, `0x8e2c0226` back-patio) equal the builds of the committed YAMLs. **The standards question is answered and landed:** `JCTsh-Build-Standards.md` v1.40 §4.1 now requires the boot-time heartbeat (with its three conditions and a reference snippet), and §2.5 carries the OTA-rollback gotcha. Still open, deliberately not this card: retrofitting the other ESPHome devices that use a 30-minute heartbeat (`garage-radar`, `salt-sensor`, `hiking-monitor`, `air-quality-monitor`, and any other) — the standard now makes that a compliance gap rather than a discovery.

**Follow-up scoped 2026-09-24 → CARD-0335** (only `garage-radar` and `salt-sensor` need it: `hiking-monitor` and `air-quality-monitor` run 5-minute heartbeats and cannot hit the false alert; `photo-server` and `p-w-firefly` already send a boot heartbeat via `OnBootSec=2min`). The list in the paragraph below is the original, broader guess. **Follow-up (not this card):** check `garage-radar`, `salt-sensor`, `hiking-monitor`, `air-quality-monitor` and any other ESPHome device with a `30min` heartbeat interval for the same gap. **Standards question raised by Joseph ("do we want this to be a standard?") — recommendation: yes, add to `JCTsh-Build-Standards.md` §4.1** (first heartbeat shortly after boot, after the first valid sensor reading and once MQTT is connected; same guards as the regular heartbeat; deep-sleep devices need a note) **plus a line about the OTA-rollback gotcha above** — pending Joseph's go-ahead, since §4.1 is read by every session.

**Related:** CARD-0219 (found while diagnosing back-patio's outage; the false alerts are documented there), CARD-0331 (watchdog re-alert gap — the sibling watchdog finding), CARD-0186 (why front-porch's `unique_id`s are left alone).

---

### CARD-0357 · [bug] [tos] [air-quality-monitor] [back-patio-temp-sensor] [front-porch-temp-sensor] [garage-radar] [hiking-monitor] [salt-sensor] Find and fix why ESPHome 2026.9.0 breaks the compile -- currently pinned 5 months behind at 2026.4.5

Archived in full to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 7277B, over the 5000B size threshold. Also tagged here; this is a pointer only, not a duplicate.

