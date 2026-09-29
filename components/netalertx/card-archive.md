# netalertx — Card Archive

Historical record of archived Done/Defer kanban cards for this component (CARD-0193's archiving process, migrated to this dedicated file by CARD-0290 — previously these were appended directly into `CLAUDE.md`, which grew unboundedly and stopped being practical to read in full). **Not read as part of routine Session Start or component-session startup** (`JCTsh-Component-Session-Start.md`) — on-demand lookup only. See this component's own `CLAUDE.md` for current, curated context.

---

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

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 6739B, over the 5000B size threshold.

### CARD-0064 · [enhancement] [netalertx] Device checking & naming workflow — RESOLVED 2026-07-14
**Status:** Done

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

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 2479B, over the 2000B size threshold.

### CARD-0236 · [enhancement] [netalertx] NetAlertX container update available: 26.8.5 → v26.9.0 — RESOLVED 2026-09-02
**Status:** Done

**Raised via automated maintenance finding (PR #59, photo-server), 2026-09-02** — routine container-version-bump finding, same shape as CARD-0233/CARD-0237.

**Checked before deciding, not assumed safe — a real breaking change found, but confirmed not applicable here.** v26.9.0's own release notes (`netalertx/NetAlertX` on GitHub) flag one breaking change: the plugins directory moved from `/front/plugins` to `/server/plugins` — "if you use custom plugin mappings in your docker-compose files, you will need to update them." Checked JCTsh's actual `components/netalertx/docker-compose.yml` directly: only two volume mounts exist (`./data:/data`, `/etc/localtime:/etc/localtime:ro`) — **no custom plugin path mapping at all**, so this breaking change doesn't apply to this deployment.

**Also checked, given a "NetAlertX v26.9.0 exploit" forum thread surfaced in the same search:** the referenced CVEs (CVE-2024-46506 unauthenticated RCE, CVE-2024-48766 file read, CVE-2025-32440/CVE-2025-48952 auth bypass) are all old, already fixed well before the currently-running 26.8.5 (fixed versions: 24.10.12, 25.4.14, 25.6.7) — not new to v26.9.0, not a live concern either way.

**Other changes in this release:** a versioning-scheme shift (CalVer, cosmetic), new multi-instance Pi-hole/AdGuard/UniFi features (not used by this deployment), network-map visual updates, several notification/timezone/theme bugfixes — nothing else flagged as breaking.

**Plan:** `docker compose pull netalertx && docker compose up -d netalertx` in `components/netalertx/` on the M8, verify live — dashboard reachable, device list intact, no new errors in `docker logs`.

**Folded into the same 2026-09-02 M8 maintenance window as CARD-0238, at Joseph's request, rather than waiting.** `docker compose pull netalertx && docker compose up -d netalertx` run in `~/netalertx-app/` (the actual deploy path, not the repo path in the plan above), pulled cleanly, container recreated. Verified live post-reboot: `netalertx` shows `Up ... (healthy)` in `docker ps` alongside all 8 other M8 containers.

**Done when:** updated and verified live — **met**.

**Related:** `components/netalertx/docker-compose.yml` (confirmed no custom plugin mapping), CARD-0233/CARD-0237/CARD-0238 (the same 2026-09-02 M8 maintenance window this was folded into).

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 4690B, over the 2000B size threshold.

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

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3197B, over the 2000B size threshold.

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

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 4765B, over the 2000B size threshold.

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

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3296B, over the 2000B size threshold.

### CARD-0068 · [enhancement] [netalertx] Remove online/offline presence messages from the log — RESOLVED 2026-07-15
**Status:** Done

**Notes:** Raised 2026-07-14, follow-up to CARD-0063. With the translation flow live for a bit, the online/offline presence transition messages (`<device> came online` / `went offline`) turned out to be noisy and not actionable — mobile/known-flappy devices dominate, and even a real device flip doesn't carry enough context (how long, why it matters) to be worth a log line. New-device alerts and the heartbeat are working well and stay. No future use anticipated for presence data elsewhere (NetAlertX's own UI already covers online/offline if ever needed) — clean removal, not a toggle/config flag.

**Scope:** in `components/netalertx/netalertx.flow.json` — remove the `mqtt_in_netalertx_binary` node (`system-sensors/binary_sensor/+/state` subscription) and the `fn_presence` function node entirely. Also remove the `devinfo_<mac>` vendor/model caching in `fn_device_info`, since it only existed to label presence messages that won't exist anymore. New-device alert messages already build their label directly from the per-device sensor payload (`payload.model || payload.vendor`), not from that cache, so no functional change there. Heartbeat and new-device detection otherwise untouched.

**Progress (2026-07-14):** `netalertx.flow.json` updated (11 nodes, `mqtt_in_netalertx_binary` + `fn_presence` + dead `devinfo_<mac>` caching removed), `netalertx-README.md` updated to match, deployed to the live Node-RED instance via the tab-clear-and-reimport procedure. **Leaving open on Joseph's call** — wants to live with it for a few days before confirming the change actually feels right day to day, rather than closing on the first clean deploy. Resume here: check back after a few days that no online/offline messages have reappeared and new-device alerts/heartbeat are still behaving.

**Deploy verification note (2026-07-14):** checked the log dashboard right after deploy and initially saw presence messages at 20:36 (`Front Porch Sensor went offline`, etc.) — looked like the redeploy failed. Confirmed with Joseph there's only one NetAlertX tab, no duplicate flow; the 20:36 batch was actually from the last scan cycle *before* the redeploy, since scan cycles land roughly every 30 minutes and no new cycle had run yet at the time of checking. Real confirmation needs the *next* scan cycle (~21:06) to show no presence messages — not yet observed as of this note. Also surfaced (unrelated, not investigated): a watchdog alert `Component front-porch-temp-sensor silent for 35 minutes` at 20:59.

**Resolution (2026-07-15):** lived with it about a day as planned. No online/offline presence messages have reappeared since the redeploy — confirmed repeatedly, including incidentally during CARD-0069's investigation (which needed to read netalertx's real log history in detail and found only heartbeats and new-device alerts, no presence noise). New-device alerts and heartbeat continued working correctly throughout, including through CARD-0069's own restarts and redeploys of the log server itself. The change holds up in real use, not just on a clean deploy.

**Closed 2026-07-15 — Joseph confirmed and directed the close.**

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 4190B, over the 2000B size threshold.

### CARD-0059 · [idea] [netalertx] NetAlertX — self-hosted LAN device tracker with custom naming — RESOLVED 2026-07-12
**Status:** Done

**Notes:** Raised 2026-07-12. Motivated by the router (TP-Link Archer AXE75) listing most connected devices with meaningless names, with no built-in way to rename them — the JCTsh-managed fleet already has this solved via DHCP reservations + `network/jctsh-network.md`'s device table + ESPHome hostnames, but third-party/commercial devices (Ring, Ecobee, Cast devices, guest phones) aren't part of that convention and the router won't let their names be overridden.

**What it is:** NetAlertX (formerly Pi.Alert) — open-source, self-hosted LAN device scanner and presence tracker. Maintains its own device database independent of the router, so naming lives there regardless of what the router shows.

**How it works:** periodic ARP scanning (plus optional plugins — mDNS, SNMP against the router, DHCP lease-file parsing, nmap) discovers devices; each MAC gets a persistent record (first-seen, last-seen, IP history, OUI-based vendor guess) in its own SQLite DB. A web dashboard lets you assign a friendly name/icon/group to each MAC once, permanently — independent of router support. Also flags brand-new unknown devices joining the network (security-relevant) and always-on devices going silent, with notifications via MQTT, webhooks, email, Pushover/Telegram/ntfy/Apprise.

**Planning (2026-07-12) — host decision reversed on real data:** initially figured the Pi as the natural fit (LAN hub, classic Pi.Alert project) and Joseph agreed — but checking the Pi directly first (good thing) found it's a Raspberry Pi 3 B+ already under real memory pressure: 34MB free, 315MB available, swap at 462MB/904MB (51%) — already running Docker for Home Assistant itself, plus Mosquitto, Node-RED, and `log_server.py` natively, all things other devices actively depend on (MQTT broker, automations). Adding periodic ARP/nmap scanning there risked contending for the little headroom left. Checked the M8 instead: 12 cores, 9.2GB available RAM, swap barely touched (109MB/4GB), Docker already running Immich's 4 containers cleanly. Switched the plan to the M8. No VLAN segmentation on this network (confirmed during CARD-0050), so the M8 sees the same broadcast domain the Pi would — no ARP-visibility loss from the switch. Skipped a separate Design phase — this checked-before-deciding pass is the plan; went straight to Build.

**Build (2026-07-12):** MQTT account (`netalertx`) created on the Pi's Mosquitto broker, recorded in `credentials.local.md`, verified working. `components/netalertx/docker-compose.yml` deployed to `~/netalertx-app` on the M8 (its own compose project, alongside but separate from `~/immich-app`).

Two real deploy bugs found and fixed: (1) my first compose file was based on a lossy AI-summarized version of the upstream reference, missing `read_only: true` and the specific `cap_drop`/`cap_add` set the entrypoint's own self-check requires — container crash-looped (exit 126) until fetched and matched the literal upstream file. (2) the upstream file's ARP-flux-mitigation `sysctls:` block isn't allowed by Docker under `network_mode: host` (`runc create failed: sysctl ... not allowed in host network namespace`) — removed from compose; the real fix is setting those two sysctls on the M8's host kernel directly, which needs interactive `sudo` (deferred — `jct@photo-server.local`'s sudo requires an interactive password, unlike the Pi's account; captured as a follow-up, not blocking).

**Resolution:** container deployed, healthy, zero restarts, image `ghcr.io/netalertx/netalertx:latest`. Login secured (Settings → System → Set Password, credential in `credentials.local.md` — default install ships with auth disabled entirely, closed that gap). Joseph completed the manual first-run setup and confirmed the naming workflow. MQTT/log-dashboard integration deliberately deferred, not because it's blocked but because it needs its own experiment first — split out to CARD-0063 rather than holding this card open for it.

**Closed 2026-07-12 — Joseph confirmed and directed the close.**

---

