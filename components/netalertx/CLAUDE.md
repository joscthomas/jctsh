# netalertx — Context

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 11177B, over the 10000B size threshold.

### CARD-0063 · [idea] [netalertx] NetAlertX MQTT event richness experiment + log dashboard wiring — RESOLVED 2026-07-14
**Status:** Done

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
