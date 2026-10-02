# JCTsh Backlog

Lightweight kanban. Each card has a **type** (idea | enhancement | bug) and a unique ID.

**Columns:** Backlog → Planning → Build → Done, plus **Defer** (off to the side — reachable from any stage)
- **Backlog** — captured, not yet being worked on
- **Planning** — being scoped/interviewed, and (if non-trivial) an implementation plan written — no separate Design checkpoint; the plan itself is the design artifact
- **Build** — going through the plan/implementation, including testing
- **Done** — complete
- **Defer** — a deliberate decision not to pursue for now (not abandoned, not forgotten — just consciously parked); can move here from any other column

<!-- next-card-id: CARD-0383 -->

---

### CARD-0382 · [maintenance] [pi1] Pi maintenance: 27 routine + 3 review-category updates — auto-opened from jctsh-core

**Status:** Backlog

**Auto-generated from jctsh-core's maintenance check (CARD-0125/CARD-0128).** Raw finding: Pi maintenance: 27 routine update(s) pending. 3 package(s) need review: docker-ce, docker-ce-cli, docker-ce-rootless-extras.

**Researched 2026-10-01 (general session).** Confirmed live on the Pi via `apt list --upgradable`: 30 packages total. The 3 flagged for review are the Docker engine stack (`core/maintenance/pi-maintenance-check.py`'s `REVIEW_PATTERNS = ("docker", "containerd", "linux-", "libc6")`), `5:29.8.1` → `5:29.8.2`. `containerd.io` itself is not in the list — already at `2.3.6` (the fixed version per CARD-0381's research), so only the engine CLI/daemon packages need the bump.

**Same Docker Engine release this session already researched for CARD-0381 (M8) — relevance re-checked for the Pi specifically, not assumed to transfer automatically:** the security fixes land in the 29.8.1→29.8.2 jump (per docs.docker.com/engine/release-notes/29/), same as the M8's bump. **CVE-2026-92543** (DNS-spoofing bypasses TLS cert verification during registry pulls) is still relevant here even though the Pi never runs `docker pull`/`docker compose pull` directly (CARD-0266/0268/0269's known hang bug on this host) — `pi-image-pull.py` uses `ctr` instead, which still goes through the same engine/containerd registry-client code path, so the vulnerability class applies regardless of which CLI invokes the pull. **CVE-2026-53493** (containerd OCI-index DoS) is already closed here (containerd.io already at the fixed 2.3.6). Swarm CVE and BuildKit CVEs: not applicable (no Swarm, no local image builds on this host — both containers, `homeassistant` and `matter-server`, run pulled images only).

**Routine packages include real security-tagged updates, not just cosmetic bumps** (`apt list` marks them `stable-security`): `openssl`/`libssl3t64` (crypto library), `libpcre2-16-0`/`libpcre2-8-0`, `libwebsockets19t64`, `rsync`. Worth applying as part of the same pass, consistent with how CARD-0381 treated the M8's routine packages (one `apt upgrade`, not a package-by-package split) — these aren't Docker/kernel so they don't carry the daemon-restart risk, no extra caution needed. Remaining routine packages are desktop-environment/display packages (chromium, labwc, wayvnc, rpd-*, wf-panel-pi, pipanel) irrelevant to this Pi's actual headless server role, plus `rpi-eeprom`/`rpi-swap`/`wpasupplicant` — none carry any noted risk.

**No reboot-required mechanism applies here** — confirmed via the script's own header comment: Raspberry Pi OS has no `/var/run/reboot-required` (no `update-notifier-common`), and this Pi (3B+) has no EEPROM bootloader to separately firmware-update (`rpi-eeprom-update` reports none present, already confirmed 2026-07-31). The only restart this upgrade causes is the Docker daemon restart from the `docker-ce` package's postinst, which recreates/restarts the two running containers (`homeassistant`, `matter-server`) — same mechanism just verified safe on the M8 (CARD-0381: "No containers need to be restarted").

**Net assessment: same conclusion as CARD-0381 — a real, relevant security fix, not a deferrable update.** Safe to apply: full `apt upgrade` (all 30 packages, matching the CARD-0381 precedent of not splitting routine from review when nothing distinguishes their risk), verify `docker --version` reads `29.8.2`, both containers back up healthy, and HA's actual integrations unaffected (CARD-0240's post-update entity-availability check, since a Docker daemon restart is the same trigger condition as a container recreate).

**Not yet applied — held for a separate go-ahead.**

**Done when:** `docker --version` reports `29.8.2` live, `homeassistant` and `matter-server` both confirmed running and healthy after the Docker daemon restart, HA's `/api/states` checked for any entities left unavailable post-restart (CARD-0240), and `pi-maintenance-check.py`'s own next run reports 0 review-category packages pending.

**Related:** `core/maintenance/pi-maintenance-check.py` (the check this finding came from), CARD-0125 (built this check), CARD-0381 (sibling card this session, same Docker Engine release researched there first), CARD-0240 (post-update entity-availability check this card's verification leans on), CARD-0266/CARD-0268/CARD-0269 (the Pi's known `docker pull` hang bug — confirmed not triggered by this apt-level upgrade).

---

### CARD-0381 · [maintenance] [m8] M8 maintenance: 21 routine + 6 review-category updates, 1 firmware update — auto-opened from photo-server — RESOLVED 2026-10-01

**Status:** Done

**Auto-generated from photo-server's maintenance check (CARD-0095/CARD-0128).** Raw finding: M8 maintenance: 21 routine update(s) pending. 6 package(s) need review: containerd.io, docker-buildx-plugin, docker-ce, docker-ce-cli, docker-ce-rootless-extras, docker-compose-plugin; 1 firmware update(s) available: UEFI dbx: UEFI Secure Boot Forbidden Signature Database.

**Researched 2026-10-01 (general session).** Confirmed live on the M8 via `apt list --upgradable`: 27 packages total. The 6 flagged for review are exactly the Docker engine stack (`hosts/m8/maintenance-check.py`'s `REVIEW_PATTERNS = ("docker", "containerd", "linux-", "libc6")` — no kernel/libc6 this time, purely Docker/containerd), running from `5:29.7.2` → `5:29.8.2`.

**Docker Engine 29.7.2 → 29.8.2 release notes read (docs.docker.com/engine/release-notes/29/) — this is not a routine point release, it's a real security update:**
- **CVE-2026-92543**: malicious DNS responses can bypass TLS certificate verification during registry pulls, exposing registry credentials or allowing image substitution. **Directly relevant** — the M8 pulls container images routinely (this very PR batch, `pi-image-pull.py`-equivalent flows, `docker compose pull` for netalertx/immich/ring-mqtt/data-pipeline), and is the one host in this project with real internet-facing exposure (`hikes.jctnet.com` via Cloudflare Tunnel, CARD-0095). A spoofed-DNS image-substitution attack is exactly the kind of supply-chain risk that matters on this specific host.
- **CVE-2026-53493** (containerd): crafted OCI image indexes with deeply nested descriptors can cause unbounded CPU/memory use — a pull-time DoS vector, also relevant given this host pulls third-party images regularly.
- **CVE-2026-92542** (Swarm overlay networks): not applicable — this project uses plain `docker compose`, no Swarm anywhere.
- **BuildKit CVEs (CVE-2026-93315 through 93326)**: build-time cache poisoning/policy bypass — relevant in a minor way, since `data-pipeline-api` is built locally via `build: ./api` in `core/data-pipeline/docker-compose.yml` (the only locally-built image on this host; everything else is a pulled image).
- No breaking changes identified; packaging bumps are internal (BuildKit 0.32.2→0.33.1, containerd 2.2.6→2.3.6, runc 1.4.3→1.5.2, Go 1.25.5→1.26.8).

**Firmware update (UEFI dbx) researched (`sudo fwupdmgr get-upgrades`):** a standard Microsoft-published UEFI Secure Boot Forbidden Signature Database revocation update (20260402 → 20260707), purely additive blocklist of known-compromised bootloader/UEFI binaries. Routine security hygiene, not a functional change — low risk, but requires a reboot to apply (confirmed via `fwupdmgr`'s own device flags).

**Net assessment: the Docker engine bump is the opposite of the npm/netalertx precedents (CARD-0379/CARD-0380) — it's a genuine, actively-relevant security fix for this host's actual threat model (internet-facing, routinely pulls third-party images), not an update with no real bearing on usage.** Worth applying deliberately, not deferring to "wait for the next one" (this session's own agreed condition for skipping an update is that nothing in it is relevant to actual usage — that condition isn't met here). The firmware update is low-risk/low-urgency but may as well land in the same maintenance window since both want a reboot-adjacent moment (Docker engine restart for the package bump; the firmware is applied on next reboot).

**Applied and verified live, 2026-10-01 (Joseph: "apply it").** Baseline captured first: 11 containers running on the M8, all healthy, Docker 29.7.2. Ran `apt-get update && apt-get upgrade -y` (all 27 pending packages, not just the 6 review-category ones -- the routine packages were part of the same finding and apt resolves them together). apt's own "No containers need to be restarted" message confirmed the Docker daemon restart didn't require a manual container recreate; all 11 containers were back up healthy within 35 seconds. Applied the UEFI dbx firmware update via `fwupdmgr update -y`, then rebooted. Post-reboot verification: `docker --version` reads `29.8.2`; all 6 review packages confirmed at their target versions via `dpkg -l`; all 11 containers back up healthy within 39 seconds of boot; `/var/run/reboot-required` gone; `sudo fwupdmgr get-updates` shows `UEFI dbx` at "latest available firmware version", "No updates available"; a live rerun of `maintenance-check.py` itself confirmed the Docker/containerd review items are gone.

**New, unrelated finding surfaced live during this work, not folded into this card:** a kernel update (`linux-generic`/`linux-image-generic`/`linux-headers-generic`, 7.0.0-34 → 7.0.0-38) appeared during `apt-get update` -- it wasn't part of PR #151's original finding, and `maintenance-check.py`'s own rerun correctly caught it as a new review-category item (matches `REVIEW_PATTERNS`'s `"linux-"`) and auto-opened its own PR (#154). Left alone deliberately -- a kernel update is its own decision, not something to bundle into an in-progress unrelated card.

**Done when:** `docker --version`/`containerd.io` report the new versions live, every container on the M8 (netalertx, immich, ring-mqtt, hike-izer-web, data-pipeline-api/timescaledb) confirmed still running and healthy after the Docker Engine restart, the UEFI dbx update applied and confirmed via a post-reboot `fwupdmgr get-updates` showing no pending updates, and `maintenance-check.py`'s own next run reports 0 review-category packages pending. **Met** (the one review-category item its rerun does report -- the new kernel -- is the separate, newly-surfaced finding above, not a leftover from this card's own scope).

**Related:** `hosts/m8/maintenance-check.py` (the check this finding came from, defines `REVIEW_PATTERNS`), CARD-0095 (M8 maintenance-check build, established the internet-exposure risk framing this card leans on), CARD-0379/CARD-0380 (sibling PRs this same batch — contrast case where the update genuinely didn't matter to actual usage), PR #154 (the new kernel-update finding this work surfaced, not yet triaged).

---

### CARD-0380 · [enhancement] [m8] Container image update: netalertx v26.9.0 → v26.10.0 — auto-opened from photo-server — RESOLVED 2026-10-01

**Status:** Done

**Auto-generated 2026-10-01 13:30 UTC from photo-server's maintenance check.** Raw finding: Container image updates: netalertx: v26.10.0 available (running 26.9.0).

**Researched 2026-10-01 (general session).** Confirmed live on the M8: `netalertx` container up 3 days, healthy.

**Real, separate gap found while checking the deployment, not itself the PR's finding:** `components/netalertx/docker-compose.yml` pins `image: ghcr.io/netalertx/netalertx:latest` -- a genuinely floating tag, not matching this project's own established "pin, don't float" convention (CARD-0257/CARD-0352 for cloudflared, CARD-0362 for timescaledb, CARD-0344 for ring-mqtt). This means the container has been silently drifting to whatever `:latest` resolves to on every `docker compose pull`, not deliberately version-controlled the way every other container-image bump this session has handled. Worth fixing as part of applying this update, not a separate card -- the natural moment to pin is exactly when a version is already being deliberately chosen.

**Full release notes read (`gh api repos/jokob-sk/NetAlertX/releases/tags/v26.10.0`) -- a real minor release (new Performance/Storage pages, pagination, several plugin additions), one breaking-change note, checked against actual usage, not assumed:**
- **"PHASING OUT: old API endpoints"** -- checked this repo's entire NetAlertX integration (`components/netalertx/netalertx.flow.json`, `README.md`): it's a pure outbound-webhook integration (NetAlertX pushes signed events to Node-RED, CARD-0078) -- **nothing here ever calls NetAlertX's REST/GraphQL API directly**, old or new. This breaking-change note doesn't apply.
- **Likely-beneficial fixes for this project's actual usage:** "MAC case sensitivity causing double detection" (a real false-duplicate-device bug); "devices with eligible network interfaces are now correctly recognized as present, preventing false down/disconnected status" (directly relevant -- this is exactly the kind of false-alarm class the watchdog/dashboard infrastructure elsewhere in this project already works hard to avoid).
- **No plugin-specific risk:** the new/fixed plugins named (`DOCKERDISC`, `WIFICANARY`, `FRITZBOX`, `FREEBOX`, `ADGUARDIMP`) aren't configured on this deployment (confirmed via `docker-compose.yml`'s plain environment block -- no plugin-specific env vars set).

**Net assessment: a real, substantive release, but nothing in it conflicts with this project's narrow usage (network presence scanning + one outbound webhook) -- two of the fixes are plausibly beneficial (fewer false duplicate/down detections).** Safe to apply. Mechanically: pin the compose file to the exact digest for `v26.10.0` (resolved by pulling the tag live, not guessed, same method CARD-0356 used for immich-redis), recreate, verify `container-update-check.py`'s own `label`-based version read reports `26.10.0` and the real webhook integration still fires (a live network-device state change, or NetAlertX's own test-publish feature).

**Applied and verified live, 2026-10-01 (Joseph: "apply it").** Pulled `ghcr.io/netalertx/netalertx:26.10.0` live on the M8 to get the real digest (the GitHub release tag `v26.10.0` and the Docker image tag `26.10.0` don't share the `v` prefix -- confirmed by a failed pull before finding the right tag format, not guessed). Pinned the compose file, confirmed the deployed copy had no drift beyond this one line before overwriting, recreated. Verified: OCI label `org.opencontainers.image.version` reads `26.10.0`; `container-update-check.py`'s own real run confirms "now running 26.10.0"; a live heartbeat on the dashboard (`42 online, 0 down`) confirms the Node-RED webhook integration survived the recreate.

**Done when:** `docker-compose.yml` pins an explicit `netalertx` version+digest (not `:latest`), the container reports `v26.10.0` live, and the Node-RED webhook integration confirmed still working after the recreate. **Met.**

**Related:** CARD-0078 (built the webhook integration this update needs to keep working), CARD-0362/CARD-0356/CARD-0344 (the pin-don't-float precedent this follows), `hosts/m8/container-update-check.py` (the check this finding came from).

---

### CARD-0379 · [enhancement] [pi1] Node-RED update(s) pending: npm 12.1.0 → 12.2.0 — auto-opened from jctsh-core — RESOLVED 2026-10-01

**Status:** Done

**Auto-generated 2026-09-30 17:00 UTC from jctsh-core's maintenance check.** Raw finding: Node-RED update(s) pending: npm: 12.2.0 available (running 12.1.0).

**Researched 2026-10-01 (general session).** Confirmed live on the Pi: `npm --version` reads `12.1.0`, Node.js unaffected (`v22.23.3`, unchanged either way -- npm and Node version independently).

**Full changelog read (`gh api repos/npm/cli/releases/tags/v12.2.0`) -- two changes, neither relevant here:** one feature (OIDC authentication support for `npm dist-tag`, a *publishing*-workflow feature -- this Pi never publishes packages, only installs Node-RED and its palette nodes) and one doc fix. No bugfixes, no security advisory.

**Net assessment: lower-stakes than the timescaledb bump (CARD-0378) even before considering relevance.** `npm` is a CLI tool, not a persistent service -- updating it is `npm install -g npm@12.2.0`, no container/service recreate, no live traffic, no "downtime" concept at all. The only real verification is that `npm` itself still runs correctly afterward (`npm --version`, and a real `npm outdated -g`/`npm outdated` run inside `/home/pi/.node-red`, since `core/maintenance/node_red_update_check.py` -- the very script that found this -- depends on `npm` working correctly to check Node-RED/palette-node versions).

**Applied and verified live, 2026-10-01 (Joseph: "apply it").** `sudo npm install -g npm@12.2.0` -- clean, 46s. `npm --version` confirms `12.2.0`. Re-ran `node_red_update_check.py` for real afterward (not just the version string): "Nothing pending" -- confirms the check script itself still works correctly against the new npm.

**Done when:** `npm` on the Pi reads `12.2.0`, and `node_red_update_check.py`'s own mechanism (the script that surfaced this finding) still runs cleanly afterward -- a real run, not just `npm --version`. **Met.**

**Related:** CARD-0344 (built `node_red_update_check.py`, the check this finding came from), CARD-0378 (the sibling container-image bump this session just applied, same research discipline).

---

### CARD-0378 · [enhancement] [data-pipeline] Container image update: timescaledb 2.30.1 → 2.30.2 — auto-opened from photo-server — RESOLVED 2026-10-01

**Status:** Done

**Auto-generated 2026-09-30 13:30 UTC from photo-server's maintenance check.** Raw finding: Container image updates: timescaledb: 2.30.2 available (running 2.30.1).

**Researched 2026-10-01 (general session).** Confirmed live: `data-pipeline-timescaledb` currently runs TimescaleDB extension `2.30.1` on PostgreSQL 16.15, pinned in `core/data-pipeline/docker-compose.yml` per CARD-0362's own precedent (`timescale/timescaledb:2.30.1-pg16`, not `:latest-pg16`).

**Full changelog read (`gh api repos/timescale/timescaledb/releases/tags/2.30.2`) -- 7 bugfixes, none apply to this deployment's actual usage:**
- Chunk-merge crash (different column layouts), `DROP SCHEMA CASCADE` orphaning compressed chunks, a `CREATE TABLE AS` crash on a compressed hypertable -- **this deployment uses no compression at all** (checked `init/schema.sql`: no `compress` settings anywhere), so none of these three can fire here.
- Vectorized text-comparison bug with a non-deterministic collation -- this deployment uses Postgres' default (deterministic) collation throughout; no custom collation configured anywhere.
- Two continuous-aggregate-refresh fixes (a race condition, a setting rename) -- **no continuous aggregates exist in this schema** (`init/schema.sql` has plain hypertables only, no `CREATE MATERIALIZED VIEW ... WITH (timescaledb.continuous)`).
- A tenant-tracker memory-leak fix -- an enterprise/multi-tenant feature, not applicable to a single-database, single-tenant deployment like this one.

**Net assessment: a routine, low-risk bugfix release with zero relevance to how this pipeline actually uses TimescaleDB.** Safe to apply whenever convenient; not urgent, since none of the fixed bugs are things this deployment could be hitting. Mechanically identical to CARD-0362 item 1's own pin-bump precedent: update the compose pin, recreate just the `timescaledb` container (confirmed via `docker-compose.yml`'s service separation that `data-pipeline-api` is unaffected by a `timescaledb`-only recreate, same as every prior container-specific recreate on this host), verify `extversion`/`postgres --version` match and real row counts are intact afterward.

**Applied and verified live, 2026-10-01 (Joseph: "apply it").** Pin bumped, `timescaledb` pulled and recreated. **One real step beyond the recreate itself:** the image update alone didn't bump the installed extension -- `extversion` still read `2.30.1` immediately after, standard Postgres behavior (a new shared library being present isn't the same as the database having run its upgrade script). `ALTER EXTENSION timescaledb UPDATE;` closed that gap; `extversion` confirmed `2.30.2` after. All 6 tables' row counts checked before and after -- intact (`environmental_data` even picked up one real live write during the recreate window, 36844 -> 36845, not data loss). Gateway `/health` confirmed responding normally throughout.

**Done when:** `docker-compose.yml`'s pin updated to `timescale/timescaledb:2.30.2-pg16`, `timescaledb` recreated, `extversion` confirmed `2.30.2` live, and real data (row counts across all 6 tables) confirmed intact post-recreate. **Met.**

**Related:** CARD-0362 (the original pinning decision and precedent for how this kind of bump gets applied), CARD-0349 (the migration that made this database matter at all).

---

### CARD-0377 · [bug] [air-quality-monitor] Task-watchdog crash mid-replay lost the last ~68 minutes of a real 10-mile hike's environmental data

**Status:** Build

**Raised 2026-10-01 (Joseph), from a real hike.** Plan executed exactly as intended: rebooted AQM ~05:45 MST while still docked (deliberate, to start the day with a synced clock and a clean boot), left Intent off and undocked for the drive to the trailhead, Intent ON at the trailhead, hiked ~10 miles / ~4h10m, Intent OFF at the end, drove home, docked ~12:30 MST.

**What happened, reconstructed from the log dashboard and a direct query against the data-pipeline gateway (CARD-0349 -- the Environmental Data Google Sheet is retired; `fetch_hike_data.py --source air-quality-monitor` against the TimescaleDB gateway is now the authoritative source):**
- The hike itself was clean: one single continuous boot from ~05:56 through dock at 12:30 (uptime 6h34m confirmed at the first post-dock heartbeat) -- no reboots, no connection drops, the whole ~6.5 hours of drive+hike+drive-home.
- At dock (12:30:05), `Replaying 125 buffered readings...` started at 12:30:57. 125 matches a ~4h10m hike at 2-min intervals almost exactly.
- **29 seconds into the replay (12:31:26), the device dropped off MQTT and came back at 12:31:32 with `reset reason: task watchdog`** -- a real ESP-IDF task-watchdog trip, confirmed genuine (not a misreport) because uptime reset to 0h19m by the next heartbeat. No `Buffered-data replay complete.` line ever appeared -- the replay was cut off mid-stream.
- **Confirmed data loss, queried directly:** 91 of the 125 buffered readings actually reached the data-pipeline gateway, spanning 06:42-09:42 MST with zero gaps inside that window (clean, complete coverage for the first 3 hours). The remaining 34 readings (= 68 minutes, matching 125-91 exactly) -- covering roughly the last hour-plus of the hike -- never arrived. GPS Track (482 points, a separate device/pipeline) was unaffected; this is specifically an AQM environmental-data loss.
- Device has been fully stable since the crash (healthy battery, normal heartbeats through at least 13:31).

**Why, investigated against the actual replay code (`attempt_aqm_replay`'s callback in `air-quality-monitor.yaml`, `aqm_log_replay_stream` in `aqm_logger.h`) -- a reasoned hypothesis, not yet confirmed via a live capture:**
Each buffered reading's replay does: cheap string-based timestamp resolution (CARD-0343's logic, no I/O), one `mqtt_client->publish()` call (QoS 0), `App.feed_wdt()`, then `delay(50)` -- the exact same pattern already flagged in this file's own comments as having "already needed watchdog fixes" once before, for a *50ms burst*. `feed_wdt()` is called only **after** `publish()` returns, so it can only protect against *cumulative* slowness across iterations, not a **single** `publish()` call that blocks longer than the watchdog timeout by itself -- once inside that one blocking call, nothing can feed the watchdog until it returns. 125 readings fired back-to-back at nominal 50ms spacing is the largest batch this device has ever replayed in the field (every prior real hike was 10-58 readings); it's plausible that volume was enough to build real TCP/TLS send-buffer backpressure (mTLS framing overhead per publish, home WiFi, not a wired link) until one `publish()` call blocked past the watchdog's timeout -- a scaling limit in the existing per-reading pacing that smaller batches never exercised, not a new regression in CARD-0346's own recent changes (the replay loop itself is unchanged from before that work).

**Not yet confirmed:** no live debug-UART capture was taken during this actual crash (AQM does have UART debug capability per CARD-0205, unlike hiking-monitor) -- the above is the best explanation consistent with the evidence, not a proven root cause. A deliberate bench reproduction (force a 100+ reading backlog, replay it while watching serial) would confirm or rule this out directly.

**Superseded, 2026-10-01 -- the per-message patches below were the first idea, not the plan. Joseph's framing after discussion: we're asking more of a tiny ESP32 than it's capable of; minimize what it does and offload processing to a real computer, rather than tune the existing per-message loop.** ~~1. Cheapest, lowest-risk: call `App.feed_wdt()` immediately before `publish()` as well as after...~~ ~~2. Also cheap: increase the per-reading `delay(50)` for large backlogs...~~ ~~3. More invasive: chunk the replay into smaller batches...~~ Kept struck-through rather than deleted so the reasoning that led away from them isn't lost. Item 4 (a bench reproduction with a live UART capture, if the root cause is ever still in doubt after the redesign below) still stands as a real fallback.

**The actual plan, worked out 2026-10-01 -- a genuine architecture simplification, not a bigger bug fix. Full reasoning lives in this session's transcript; summarized here as the build plan.**

*Phase 1 -- M8 (`data-pipeline-app/api/app.py`), build and test before any firmware changes:*
1. Add `POST /data/env-bulk`: body `{current_time, current_boot, current_uptime_s, readings: [...]}`. Reuses the existing single-row insert logic in a loop -- same dedup/range-check handling already there. Moves CARD-0343's `ts:null` + uptime/boot-id timestamp-resolution math from ESP32 C++ into this handler, in Python, once per row. Response reports `{inserted, duplicate, rejected, unresolved}` counts.
2. Fold GPS enrichment into **both** write handlers (the existing single-row one and the new bulk one) by calling the already-existing `_gps_lookup()` **in-process** when a row's lat/lon is missing -- this is what Node-RED's live flow currently does over its own HTTP round-trip (confirmed live in `flows.json`: it calls `/lookup-gps` with bounded retries before writing). AQM needs no "at-home static fallback" the way hiking-monitor's Node-RED flow has (confirmed this session: AQM's own `intent_switch`-gated duty-cycle means collecting and being WiFi-connected are mutually exclusive by design, so every AQM reading comes from a genuine collecting session with a real GPS track to correlate against -- see CARD-0259 for porting this same clean invariant to hiking-monitor v2).
3. **Reuse the relay `data-pipeline-api` already has, rather than add a new MQTT client -- found live while starting Phase 1, 2026-10-01.** `app.py` already carries `_relay_log(component, category, message)`, built for CARD-0349 Phase 2 specifically because *this service deliberately has no MQTT client of its own* -- it POSTs to `hike-izer-orchestrator`'s existing `/webhook/pipeline-log`, which republishes onto Mosquitto, the exact mechanism GPS Track/Hike Start Forecast/Wildlife Detections already use for dashboard visibility today. No new Mosquitto account, no new infrastructure -- the new bulk/single-row handlers just call this existing, already-proven function whenever something dashboard-worthy happens (an online-equivalent line, an Alert, a replay-complete summary). This is still the fix for the "how does the M8 feed MQTT" question -- not a point-to-point HTTP coupling to `log_server.py` -- it's just that the relay already existed rather than needing to be built.
4. Reachable via the same existing public route everything else already uses (works identically whether AQM is docked at home or connected via the Pixel hotspot while traveling) -- no new LAN-only port, no new security-exposure decision.
5. Test with `curl` -- a synthetic batch including a duplicate, an out-of-range value, and an unresolvable (wrong-boot) reading -- and confirm the MQTT republish lands correctly on the dashboard, before any firmware touches this.

*Phase 2 -- AQM firmware: drop MQTT entirely, not just the replay loop:*
6. Add `http_request:`.
7. Replace `attempt_aqm_replay`'s per-line MQTT loop with one POST of the raw log file to `/data/env-bulk`; `aqm_log_clear()` only on a confirmed-successful response.
8. **Delete** `aqm_log_replayed`, `intent_last_polled_state`, the boot-time seed, the `on_press` edge-detection, and the poll-based backstop -- all of CARD-0346's fix-of-a-fix machinery. New rule replaces all of it: clear only after confirmed upload success, nothing else needs tracking, so there's no flag left to get stuck.
9. **Delete the dead live-publish branch** in the SEN55 duty-cycle code (`if (clock_ok && id(mqtt_client).is_connected())`) -- confirmed this session it can never fire: collecting (Intent ON) and being WiFi-connected are mutually exclusive by the gate itself (`wifi_gate_ok = intent_off && power_connected && voltage_ok`). Every reading just buffers; that was already the only real path.
10. **Remove the `mqtt:` block entirely** -- the `wifi_gate_ok`/attempt-window/15-min-backoff state machine, `mqtt.enable`/`disable` mirroring, the LWT, and the now-pointless `command/replay` topic all exist only to manage a persistent broker session that no longer exists. Replaced by: "eligible? connect WiFi, do one POST, done."
11. Heartbeat: already removed from scope (below). No remote-command channel survives this -- acceptable, since the only thing that rode on it (`command/replay`) is being deleted along with the bug it existed to recover from, and Joseph is physically present at both ends of every AQM session anyway.
12. Bench-test: force a real multi-hour backlog, dock, confirm one clean POST, correct row/GPS/dashboard result, log cleared only after success.

*Separately decided, not a build step:* drop the 5-min heartbeat -- it can only ever fire while connected (docked), so on every real field day it produces nothing but false "silent for N hours" watchdog alerts (confirmed: four fired during this very hike) for a device whose whole job is being unreachable for hours at a stretch. No heartbeat-shaped replacement; device health is better represented by a per-session summary (Phase 3, below) than a liveness ping.

*Phase 3 -- session summary, deliberately separate scope, not bundled into 1-2:* a per-dock summary (session duration, readings vs. expected, battery delta, reset count) computed server-side from the uploaded rows, replacing "is it currently reachable" with "did the last session go well" -- the actually-useful question for a device that's supposed to be unreachable most of the time. Needs reset/boot diagnostic events to be queryable somewhere (today only in the Pi's flat log, not the TimescaleDB gateway) -- real new scope, start once Phases 1-2 are live and proven.

**Phase 1 built and verified live, 2026-10-01.** `core/data-pipeline/api/app.py`: added `POST /environmental-data-bulk` (accepts `{current_time, current_boot, current_uptime_s, readings: [...]}`, resolves CARD-0343's `ts:null`/`uptime_s`/`boot` shape server-side, reports `{inserted, duplicate, rejected, unresolved}`); extracted the insert/dedup/range-check logic out of `_handle_environmental_data` into a shared `_insert_env_row()` so both routes use identical behavior; folded GPS enrichment into both handlers via the already-existing `_gps_lookup()`, called in-process (no relay hop needed); and used the service's own already-existing `_relay_log()` (built for CARD-0349 Phase 2, POSTs to `hike-izer-orchestrator`'s `/webhook/pipeline-log`) for dashboard visibility -- no new MQTT client needed after all, this exact problem was already solved for other tables.

**Real bug found and fixed along the way, unrelated to today's actual feature work:** `~/data-pipeline-app/.env` had CRLF line endings, leaving a trailing `\r` on every value including `API_KEY` -- harmless to curl (which sends it uncomplaining) but it silently desynced the stdlib `http.server`'s header/body parsing whenever that contaminated value was used in a request header, making every POST arrive as an empty body regardless of what was actually sent. Caught because Python's own `http.client` refused outright ("Invalid header value") where curl stayed silent. Fixed the `.env` file directly (backed up as `.env.bak-crlf` first) and added `.strip()` to every env var this service reads, so a future CRLF-contaminated edit can't reintroduce it. This had nothing to do with AQM specifically -- it would have silently broken any caller that happened to source its key the same way -- but was never caught until this session's direct `curl`/`.env`-sourced testing.

**Tested end to end against the live service, all passing:** a synthetic batch (one directly-timestamped reading, one resolvable `ts:null` reading, one unresolvable wrong-boot reading, one out-of-range value) classified correctly (`{"inserted":2,"rejected":1,"unresolved":1}`); the resolvable reading's timestamp math checked out exactly (`current_time - (current_uptime_s - reading_uptime_s)`); resending the same batch correctly reported the two prior inserts as duplicates; the relay'd summary line landed on the Pi's log dashboard, correctly attributed to `air-quality-monitor`, confirming the whole chain (HTTP -> insert/resolve/dedup -> relay -> MQTT -> dashboard) works without a point-to-point coupling anywhere in it. Test rows deleted from the database after confirming.

**Phase 2 built and bench-verified live, 2026-10-01/02.** `components/air-quality-monitor/air-quality-monitor.yaml`: removed the entire `mqtt:` block (broker config, TLS, LWT, `command/replay`, the SSID-based broker-switch `on_connect:`), the WiFi-gate state machine (`wifi_gate_ok`/attempt-window/15-min backoff), the `wifi.enable/disable`+`mqtt.enable/disable` mirroring, `aqm_log_replayed`/`intent_last_polled_state` and both their on_press/poll-backstop mechanisms, the dead live-publish branch in the SEN55 duty-cycle code (`if (clock_ok && id(mqtt_client).is_connected())` -- confirmed it could never fire, now unconditional buffering), and the 5-min heartbeat interval entirely. Added `http_request:` (`verify_ssl: false` -- Cloudflare's edge cert isn't one this project controls/pins; still TLS in transit, Bearer key provides application auth) and a new `attempt_aqm_upload` script: eligibility re-checked fresh every 2-min tick (intent off + docked + battery >=3.5V + data buffered, same three conditions as before, no state machine needed since a one-shot request has nothing to manage between attempts), `wifi.enable`, one `http_request.post` of the whole log built by `aqm_logger.h`'s new `aqm_log_build_bulk_body()`, `aqm_log_clear()` only on a confirmed 200. New secrets `data_pipeline_bulk_url`/`data_pipeline_auth_header` (real values in `secrets.yaml`, placeholders in `secrets.yaml.template`).

**Real bug found and fixed during live bench testing, 2026-10-01/02:** the upload script's own status markers (`upload_attempt_start`/`upload_complete`/etc.) were being written via `aqm_log_write()` into the *same* file `aqm_log_build_bulk_body()` reads to build the next POST's body -- so each marker got sent as a fake "reading" and flagged invalid server-side, and the on-success marker written *after* `aqm_log_clear()` recreated exactly one line for the next cycle to pick up, a self-sustaining 2-line loop that fired every 2 minutes indefinitely (confirmed live: every upload after the first carried exactly 2 "invalid" entries, forever -- never pointed at any real data, just the loop feeding itself). Root cause was broader than my own new code: two **pre-existing** diagnostic writers (`critical_battery_alerted`'s Alert message, both SEN55 `skip`/`sensor_stale` and `skip`/`nan_sensor` markers) had the same latent bug -- invisible under the old MQTT-per-line-publish design (any line, reading or marker, just got published as its own MQTT message with no schema check) but surfaced the instant the buffer became "the array of readings for one JSON body." Fixed by converting every non-reading write to `ESP_LOGW`-only (serial, no remote channel exists anymore without MQTT or `api:`) -- `aqm_log.jsonl` now holds *only* real sensor readings. Recompiled (`config_hash=0x859719ff`), reflashed OTA, confirmed via SSH into the M8 (`jct@m8`, not `jcthomas` -- cost real time chasing a stale username) that the junk-loop stopped for good after cleanly uploading and clearing the one leftover marker from before the fix.

**Bench-verified end to end against the live gateway, 2026-10-01/02:** Intent toggled ON (~16 min, docked/charging) then OFF produced a real 9-reading buffer; the next eligible tick uploaded all 9 in one POST -- `{'inserted': 9, 'duplicate': 0, 'rejected': 0, 'unresolved': 0, 'invalid': 0}`, confirmed directly in TimescaleDB with sane values (temp ~94°F indoor, humidity ~40%, PM2.5 0.6-1.1, battery 3.9-4.0V charging, lat/lon correctly left null -- no GPS track for a bench session, not guessed) and no relay errors in the gateway log. Log stayed empty afterward (confirmed quiet for 4+ minutes and two tick boundaries with zero spurious uploads while Intent stayed off with nothing buffered) -- the full chain (buffer -> one-shot POST -> insert -> relay) works with no persistent-connection bookkeeping anywhere in it.

**Phase 3 built and bench-verified live, 2026-10-02.** New `device_boot_events` table (`source`, `boot_id`, `reset_reason`, `received_at`; `(source, boot_id)` primary key makes a retried upload idempotent) -- added to `init/schema.sql` for future fresh installs and created live on the M8's running database directly (schema.sql only runs once, on a brand-new volume). `air-quality-monitor.yaml`/`aqm_logger.h`: `boot_id` is now assigned unconditionally at `on_boot` (was lazy, only on the first unresolved reading -- left it `0`, indistinguishable from "never assigned," on any boot that never needed CARD-0343's resolution path) and written to a new, SEPARATE `/spiffs/aqm_boot_log.jsonl` file as `{"boot","reset_reason"}`; the upload script splices that file's contents into the POST body as a `boot_events` array alongside `readings`, clearing both logs only on a confirmed 200. `app.py`'s bulk handler inserts each boot event (idempotent, ignoring already-seen ones) and, when the request carried inserted readings, computes and relays a session summary -- duration, actual-vs-expected readings (one every 2 min), battery delta, and reset count (`len(boot_events) - 1`, computed from the request itself so a retry describes the same session consistently either way) -- replacing "is it currently reachable" (the heartbeat's old, false-alarm-prone job) with "did the last session go well."

**Joseph's own question mid-build reshaped the WiFi design, 2026-10-02 ("if it's docked, do we want to leave wifi connected? why or why not?"):** Phase 2's one-shot enable-upload-disable cycle existed to conserve the LiPo -- but while docked the TP4056/solar supplies the radio, not the battery, so cycling WiFi off between uploads was solving a problem that doesn't exist in that state, at the real cost of closing the only OTA/`esphome logs` reachability window to a few seconds every 2 minutes (hit live: two OTA attempts failed outright, `Error resolving IP address`, before this fix). Changed to: WiFi now follows dock state directly via `dock_detect`'s `on_press`/`on_release` (simpler than before -- one condition, not three re-derived every tick), confirmed docked still gates every upload attempt exactly as before, so the genuine battery-only case this architecture refuses to risk a connection in is unchanged.

**Two more real bugs found live during Phase 3 bench testing, both fixed and reverified, 2026-10-02:**
1. A stray boot event with no accompanying readings (any reboot between real sessions -- the OTA dev-reboots used to test this very card) sat in the boot-events file until the next session that actually had data, which would have silently inflated that unrelated future session's reset count. Fixed: the upload script's eligibility/early-exit now checks `aqm_log_has_data() || aqm_boot_log_has_data()`, so a stray boot event gets flushed on its own promptly. Confirmed live: three accumulated test-boot events uploaded and cleared in a single `0 readings` request, with no session summary relayed for it (correct -- no `inserted_rows` means no fake session).
2. `reset_reason` came through blank on every boot event. Root cause: ESPHome's `debug:` component only publishes its `reset_reason` text_sensor inside `dump_config()`, which runs *after every* `on_boot` trigger -- so reading `id(reset_reason_text).state` during `on_boot` always reads empty, on any priority. This is a genuine **pre-existing, previously-undetected bug**, not something this redesign introduced: the file's own brownout/glitch-detection LED logic read the exact same sensor the exact same way and has likely never correctly told a brownout from a normal boot. Fixed both call sites by calling `esp_reset_reason()` directly (new `aqm_reset_reason_string()`/`aqm_reset_was_brownout_or_glitch()` helpers in `aqm_logger.h`, mirroring the debug component's own private lookup table since it isn't exported) -- confirmed live, a reboot now correctly logs `"software via esp_restart"`.

**Credential cleanup done, 2026-10-02.** The `mqtt_broker`/`mqtt_username`/`mqtt_password`/`mqtt_ca_cert` secrets were already removed from `secrets.yaml`/`secrets.yaml.template` during Phase 2's own bench verification (replaced with a comment pointing here). What remained was the actual broker-side account: Joseph's framing -- "as part of working a card, when a credential change is needed, do it, then add it to the registry... let the runner do it" (see CARD-0372's new workflow decision) -- so this card's own credential fallout gets closed out here, not left as a separate ask. Deleted the now-unused `air-quality-monitor` account from the Pi's `/etc/mosquitto/passwd` (`mosquitto_passwd -D`) and reloaded Mosquitto live (clean reload, no errors); marked the `mosquitto-accounts--air-quality-monitor` registry entry `retired` (CARD-0372's new field) rather than leaving a stale `holder` line pointing at a credential that no longer exists anywhere. RoboForm's own copy of this sub-account (if any) is unaffected -- that's Joseph's manual step, the registry has no visibility into RoboForm to confirm or force it.

**Not yet done:** a real multi-hour hike confirmation (the actual trigger for this card). Committing this work is still pending Joseph's explicit go-ahead (production firmware).

**Done when:** ~~Phase 1 is live and tested independently~~ **met, 2026-10-01.** ~~Phase 2 (AQM firmware: drop MQTT entirely, collapse the replay loop to one POST, delete the stuck-flag machinery and the dead live-publish branch) is built, bench-verified against a forced large backlog~~ **met, 2026-10-01/02.** ~~Phase 3 (per-dock session summary)~~ **met, 2026-10-02, bench-verified** -- and then confirmed on a real hike with zero data loss end to end against the gateway and a correct dashboard relay (summary included).

**Related:** CARD-0346 (the replay/backstop logic being deleted by this redesign), CARD-0259 (hiking-monitor v2 -- port AQM's unconditional-collecting choice and the three-signal model generally; `JCTsh-Build-Standards.md` §2.14 points 12-13 already document the general principle and the AQM-vs-hiking-monitor difference, this is the new decision to record there), CARD-0330 (`/status.json` freshness model this redesign must not silently break), CARD-0205 (AQM's debug-UART, still available as a fallback diagnostic), CARD-0012, CARD-0349 (the gateway this whole redesign builds on), `components/air-quality-monitor/aqm_logger.h`, `components/air-quality-monitor/air-quality-monitor.yaml`, `~/data-pipeline-app/api/app.py` (M8), `core/logging/log_server.py` (Pi).

---

### CARD-0376 · [bug] [hiking-monitor] ESP32 USB-C connector broke off the board -- replacement chip installed, needs first flash

**Status:** Build

**Raised 2026-09-30 (Joseph).** hiking-monitor's ESP32 DevKitC-32's USB-C connector broke off the board -- Joseph's working theory is it was damaged in a fall while hiking a few weeks ago (not yet pinned to a specific date/hike) and only fully let go now. Not repairable at the connector level; a replacement ESP32 DevKitC-32 has already been installed in the perfboard in place of the damaged one.

**Real consequence: the new chip is blank.** Every OTA flash on this device (CARD-0346's fixes included, 2026-09-28) lives on the *old*, now-discarded board -- the replacement has never run any firmware, so this is a first flash, not an update: USB only (no OTA possible until firmware exists), per `WORKSTATION-SETUP.md`'s `C:\esphome\hiking-monitor\` convention, native PowerShell.

**Confirmed connected, 2026-09-30:** `Silicon Labs CP210x USB to UART Bridge (COM7)`, status OK -- matches the component's documented CP2102 chip (`README.md`).

**Scope:** first USB flash of `hiking-monitor.yaml` (current repo copy, includes CARD-0346's stuck-flag backstop fix -- the replacement chip gets that fix from its very first boot, not as a later update) onto the new board, then live verification that the perfboard's existing sensors (BME280, LTR-390), e-ink display, and battery/dock-detect circuitry all still read correctly through the new chip -- the perfboard and every other component are original, only the ESP32 itself changed.

**Done when:** the new ESP32 is flashed, boots clean, and BME280/LTR-390/e-ink/battery-voltage/dock-detect all confirmed working live (not just "flash succeeded") -- same "Don't close until" bar CARD-0009's enclosure build and every other hardware-swap card on this board already use.

**First flash, 2026-09-30 13:45-13:55 MST -- compiled and OTA... USB-flashed clean, but immediately hit a real low-battery reboot loop.** `workstation-verify.ps1` passed, `esphome run --device COM7` compiled (`config_hash=0x057fbf97`) and flashed successfully -- genuine `POWERON_RESET`, fresh MAC (`58:2a:bd:76:b2:b0`), empty SPIFFS, confirming new silicon. But the device immediately cycled into `low_battery_shutdown` every ~1-4 seconds (switch ON means the deep-sleep ext0 wake condition is already satisfied the instant it sleeps, so it re-wakes almost instantly -- same self-sustaining-loop mechanism already documented on this board's history).

**Diagnosed with a temporary serial diagnostic (`ESP_LOGW` of `battery_voltage.state`, removed after use) -- a real intermittent connection, not a battery or math problem.** Multimeter readings throughout stayed healthy and consistent: battery at the JST connector 4.1V, GPIO35/physical pin 6 (battery ADC divider, white wire) 1.91-2.01V -- both exactly matching a healthy cell through the 68k/68k divider. But the firmware's own computed `battery_voltage.state` read **0.284V** on most boots (identical value, not random noise) and only occasionally the correct ~4.0V. Ruled out, in order: ADC attenuation inaccuracy (error far too large, ~13x not a few %), RC-settling time (a genuine 45s rest still read 0.284V on the very next boot), transient sag under load (same result after real rest). Reseating the ESP32 module in its header fixed it for a few minutes each time, then it recurred -- a **marginal contact specifically at the new module's own pin making contact with the perfboard's header socket**, not the wire further out (a multimeter probe pressing the pin top can itself transiently fix a marginal socket contact, which is why direct probing always read correctly while the chip's own reading didn't).

**Second, separate finding: BME280/LTR-390 also failed to initialize for a long stretch.** The e-ink display showed "Hiking monitor / initializing" (the firmware's own NaN-guard text) for several minutes even once the battery reading was healthy -- `i2c.idf: Performing bus recovery` on every single boot, and zero I2C scan results ever logged (`scan: true` is enabled) despite many boot attempts. Joseph found and fixed a wire (not yet specified which) and the display came up with live readings. Given two different pins (GPIO35 battery ADC, and apparently something on the I2C bus) both showed marginal-seating symptoms independently, this looks like a **multi-pin seating problem with this specific replacement module/header**, not one bad wire -- worth a full, unhurried visual inspection (magnifier, check for bent pins) or direct-soldering the header connections rather than continuing to chase individual pins reactively.

**A real test hike was carried out anyway, 2026-09-30 ~15:17-15:30 MST (both devices) -- hiking-monitor's data did not survive.** At dock, the on-device log showed 471 lines (mostly diagnostic noise from the day's rapid-reboot cycling) growing to 481 after the hike (~10 real readings, consistent with the walk's length), with `hike_log_replayed` stuck `SET` the same way CARD-0346's backstop was built to catch -- but the backstop's own confirmation event was never seen firing on this board during today's chaos. A `Replaying 471 hike readings...` attempt at 15:10:20 was interrupted by another reboot before completing (no `Hike log replay complete.` line), and by the time a clean `0 lines, replayed flag clear` state was reached (after a manual `Replay Hike Log` press), **Joseph confirmed directly against the Environmental Data sheet: no hiking-monitor rows landed for the hike window.** The real sensor data from today's test hike is lost.

**Status:** still Build, Done-when not met -- the board has now shown marginal contact on at least two separate pins that recur even after a fix appears to hold, and the one real-world test (today's hike) lost its data. Recommend a deliberate, unhurried hardware pass (full visual inspection under magnification, direct-soldering the header connections) before attempting another field test, rather than continuing to chase individual pins reactively as they fail. **Not yet confirmed working, live, and durable:** e-ink display (confirmed working once, not durably), BME280/LTR-390 (confirmed producing values once, not durably), battery-voltage ADC (confirmed both good and bad readings recurring), dock-detect (never independently verified this session -- the device did connect while docked, so it's at least partially functional).

**Related:** CARD-0346 (the firmware this first flash carries forward, including its own not-yet-verified backstop fix -- now confirmed firing correctly at least once on air-quality-monitor today, not yet cleanly confirmed on this board given the chaos), `components/hiking-monitor/README.md`, `WORKSTATION-SETUP.md`.

---

### CARD-0375 · [bug] [tos] [security] Live secrets are committed to the PUBLIC repo -- rotate them, scrub the working tree, decide on history

**Status:** Backlog

**Priority:** Critical -- the repository is public, and at least two of these secrets guard endpoints reachable from the internet. (set 2026-09-30 10:43 MST, incident)

**Raised 2026-09-30 10:43 MST (general session, from a full-history scan for the real secret values).** *This card names credentials only -- no values, and deliberately no file paths or commit ids, because this board is itself public.* `gh repo view` reports the repo **PUBLIC**. A scan of the current tracked files and **all history on all branches** for 35 real secret values (taken from the RoboForm checklist, so they are the live values) found six of them committed. Filename checks had said "no secrets files are tracked" -- true, but the secrets were pasted into *other* files: Tasker exports, setup docs, a script, and card text.

**What is exposed, in order of how reachable it is from the internet:**
1. **`webhook-secret`** -- in several tracked Tasker exports and setup docs, and in history. It guards `hikes.jctnet.com/webhook/*`, **public through the Cloudflare tunnel**: anyone holding it can trigger hike-summary generation (Anthropic API cost), open GitHub PRs (`/webhook/idea`), write staged files and spoof pipeline-log lines. **Rotate first.**
2. **`mosquitto-accounts--hiking-monitor`** -- in a tracked setup doc and in history. **MQTT port 1883 is forwarded from the internet** (root `CLAUDE.md`) and `mosquitto.conf` has no ACLs, so this password lets anyone on the internet read and write every topic. Needs a broker change plus a hiking-monitor reflash.
3. **`immich-credentials--api-key-joseph`** -- hard-coded in a tracked maintenance script (still in the current tree) and in history. Reachability depends on whether Immich is exposed; treat as compromised. Fix the script to read it from an env file as part of the rotation.
4. **`esp32-device-secrets--hiking-monitor-ota`** (the OTA password, same value recorded under two registry names) -- in a tracked card archive and in history across several files. LAN-reachable only, but it lets a LAN attacker flash the device; rotate with the reflash in item 2.
5. **`apps-script-api-key`** (retired) -- in two tracked Tasker exports and in history. The endpoint is write-retired, so lowest risk; confirm the deployment is actually disabled, and scrub.
6. **Node-RED: the admin password hash and a weak `credentialSecret`** -- the tracked copy of `settings.js` publishes the bcrypt hash of the Node-RED admin password (offline-crackable if the password is not long and random; treat as exposed, so rotate `node-red-admin-password`) and sets `credentialSecret` to a short, guessable word. The encrypted credentials file itself was never committed, but with a guessable secret its encryption is decorative: anyone who ever obtains it decrypts it. Fix: generate a strong `credentialSecret` (kept out of the repo, e.g. read from the environment), re-encrypt the store, and keep only a placeholder in the tracked copy.

**Not covered by the scan:** only the 35 values that exist in the checklist. The nine entries with no value there (the front-porch, garage-radar and salt-sensor MQTT passwords, whose values live in each device's own `secrets.yaml`; the Node-RED and Home Assistant MQTT passwords; the orchestrator's MQTT password; the Pi login; and the two pointer entries) were **not** scanned, so they are unknown, not clean. Also not scanned: secret shapes that are not in the checklist at all.

**What to do (nothing below has been done yet):**
- **Rotate, because rotation is the real fix.** Once pushed to a public repo a secret must be treated as compromised however the history is later cleaned (scrapers, forks, caches). Order: webhook-secret, then the hiking-monitor MQTT password and OTA password together (one reflash), then the Immich key, then the retired Apps Script key.
- **Scrub the current working tree** -- replace each committed value with a named placeholder, and make the Tasker exports follow the `REPLACE_WITH_...` pattern already used for the observations export.
- **Decide on history.** Rewriting public history (`git filter-repo` + a force-push) removes the values from GitHub's view going forward but not from copies already taken; it also rewrites every commit id. Worth doing only *after* rotation, and only if Joseph wants a clean history.
- **Prevent a repeat:** a pre-commit check that refuses a commit containing any value from the local secret stores (run as a script that reads the values itself and never prints them) -- this is CARD-0334 Phase 1's tripwire, applied to the commit boundary.
- **Extend the scan** to the nine unscanned secrets once their values are in hand, and re-run the whole scan after the rotation to show no live value remains.

**Related:** CARD-0334 (the no-print rule and guardrails), CARD-0372 (the rotation mechanism -- webhook-secret becomes the urgent pilot instead of the data-pipeline key), CARD-0367 (an earlier leak of the retired Apps Script key through alert text), CARD-0365 (keys in URLs), CARD-0370 (gateway key rotation).

**Reconciled against CARD-0334, 2026-10-02 (see its own note).** `node-red-admin-password` and hiking-monitor's Mosquitto/OTA secrets are named on both cards -- real overlap, not a duplicate card, since each found it independently with different severity framing (a session leak vs. a public-repo commit). **Rotation status for every credential on this list lives solely in `tos/credential-registry.yaml` (`last_rotated` vs. `exposed`/`rotation_requested`) -- not restated here, so this note can't go stale the way a copied status would.** Check the registry directly for current state; this card and CARD-0334 hold the incident narrative and the decisions, not a second status tracker.

### CARD-0374 · [enhancement] [logging] /kanban: sort each column by priority, then latest activity, then age -- and show a priority badge

**Status:** Done

**Raised 2026-09-29 14:57 MST (general session; Joseph: "the kanban board shows the wip. a sort seq would fix it: priority, latest date on card, initiated date").** The real problem: finding work in progress (and anything important in Backlog/Planning) means hunting through a long board, because `/kanban` sorts columns by file order with only one exception -- cards carrying an `Auto verify`/`Watch for` marker sink to the end (CARD-0251). The parser doesn't read `**Priority:**` at all, so priority (defined in `JCTsh-Operating-System.md`) cannot affect what the board shows.

**Decisions (Joseph, 2026-09-29 14:57 MST):** untagged sorts above Low (Low means "probably never"); ties broken older-first. **Sort sequence, per column** (Backlog, Planning, Build): (1) marker cards last -- unchanged; (2) priority tier Critical > High > Medium > untagged > Low; (3) latest date on the card, newest first; (4) initiated date, oldest first, falling back to card id. **Done and Defer** sort by latest date newest-first only (priority is meaningless there). A malformed priority value (e.g. the `Priority: Backlog, low` on one old card) counts as untagged. **"Latest date":** the newest `YYYY-MM-DD` anywhere in the card's title/body, ignoring dates in the future and the date inside an `Auto verify:` marker (a marker's date is when a check is *due*, not when the card was touched -- CARD-0041 showed a 2027 "latest date" without this rule). **"Initiated":** the `Raised YYYY-MM-DD` stamp, else the earliest date found, else card id. A priority badge (Critical/High/Medium/Low) is added to each tagged card so the ranking is visible.

**Scope:** `core/logging/log_server.py` -- `_parse_kanban_board` gains `priority`, `latest` and `raised` fields; the client's column sort and `cardHtml` badge. No board-file format change. Deployed to the Pi with the usual `scp` + `sudo systemctl restart jctsh-logging`. Degrades gracefully: with almost no cards tagged (2 of ~370 today) the order is effectively latest-activity-first, which is already better than file order.

**Not part of this card:** a priority triage of the existing cards (only the ones that matter, per the OS doc's "don't sweep priorities across the board"), and a `/wip` chat command. Related: CARD-0251 (the marker sort this extends), CARD-0288 / `JCTsh-Session-Card-Selection.md` (the chat-listing equivalent of this ordering).

**DONE 2026-09-29 14:58 MST.** Built, tested and deployed. `_parse_kanban_board` now emits `priority` (only Critical/High/Medium/Low count; a malformed value is untagged), `latest` and `raised`; the client sorts per the sequence above and shows a priority badge on tagged cards. **Verified:** (1) parser on the real board -- 366+ cards parse, CARD-0334 reads as `high`, and CARD-0041's latest date is now 2026-09-18 instead of the 2027 Auto-verify date (the marker rule works); (2) the **actual client comparator JS run in V8** (a JS engine, extracted from the page template, not a Python re-implementation) against the real board plus synthetic priority cases -- Critical < High < untagged < Low, Low after every unmarked untagged card, marker cards after all others, Done ordered newest-activity-first; (3) every script block in the page template parses. **Deployed** to the Pi (`/home/pi/jctsh/core/logging/log_server.py`, previous copy at `/tmp/log_server.py.bak-card0374`, `sudo systemctl restart jctsh-logging`, service active); `/kanban/data` serves the new fields (371 cards with dates, 1 with priority). **Not verified:** the rendered page in a browser (the `/kanban` route needs Basic Auth and a credential should not be put in a URL), so the badge styling is unseen -- worth a glance next time you open the board. **Also:** `JCTsh-Operating-System.md`'s Priority section now says the dashboard sorts by it. **Reflection:** (1) most of the value is in the sort's *fallback* -- with 1 of ~370 cards tagged the order is effectively latest-activity-first, so it helps on day one and improves as cards get tagged; a follow-up triage pass (only the cards that matter) is what makes priority pull its weight. (2) A "latest date" parsed from prose needs a rule for dates that mean *due*, not *touched* -- markers, and anything in the future. (3) Testing client JS without a browser or Node is possible: extract the snippet from the template and run it in `mini-racer` (`python -m pip install mini-racer`) -- far better than trusting a Python mirror of it.

**Follow-up 2026-09-29 15:38 MST (Joseph: "242 doesn't show up on the board at all; ... show the priority tag at the top of the card").** (1) **CARD-0242 was invisible because its status line read `**Status:** Backlog — low priority`** -- the parser accepted only a bare column name and silently skipped any card whose status line carried anything else. Fixed at the source (the card now reads `**Status:** Backlog`, with the "low priority" moved to a real `**Priority:** Low`), *and* the parser now accepts trailing text after the column name so a stray suffix can no longer make a card vanish. The other six cards the parser skips are the `[retracted]` ones, which is intended (Retracted is not a dashboard column). (2) **The priority badge now sits on the card-number line**, beside `CARD-nnnn`, instead of in the badge row under the title. (3) CARD-0242's priority was first set to Medium in the triage without reading the card -- it says low priority itself; corrected to Low. **Reflection:** a parser that skips what it cannot read must not do it silently -- a count of skipped-but-not-retracted cards would have caught this the day the card was written; worth a check the next time the parser is touched.

**Follow-up 2026-09-29 15:41 MST (Joseph: "let high priority escape the marker sink").** Cards carrying an `Auto verify`/`Watch for` marker used to sink to the bottom of their column regardless of anything else; a **Critical or High card now ignores the marker sink** and sorts among the unmarked cards by priority like any other -- "waiting on an event" should not bury something important (CARD-0226 is the case that prompted it: High, carries a Watch for, and would otherwise have sat at the bottom of Build). Medium, untagged and Low marker cards still sink. **Not changed:** the chat "Listing open cards" convention in `JCTsh-Operating-System.md`, which omits marker-carrying cards from the visible list entirely -- it now differs from the dashboard for High/Critical marker cards (still hidden in chat, shown at the top on the board); decide separately whether to align it. Also set this session: CARD-0346 High, CARD-0226 High, CARD-0342 Medium.

### CARD-0373 · [enhancement] [data-pipeline] [node-red] Rename the vestigial "Apps Script" nodes in the Environmental Data flow and remove the dead redirect-follow pair

**Status:** Backlog

**Raised 2026-09-29 14:43 MST (general session, from CARD-0366's documentation pass).** Three nodes in the live Node-RED "Environmental Data" tab still carry the retired target's name: `POST to Apps Script (no redirect follow)`, `Follow Apps Script redirect (CARD-0226)` and `Get Apps Script result`. The gateway answers a POST directly, so the last two exist only to chase a redirect Google's Apps Script used to issue -- they are dead weight in the request path. Cosmetic, but it is exactly the stale wording that made a 2026-09-29 05:00 alert look like an unfinished migration, and `core/data-pipeline/README.md` currently has to explain it away.

**Not yet scoped -- needs a look when picked up.** The POST queue's `Check response` and retry logic sit between these nodes and must keep working; whether the "no redirect follow" setting on the request node (`followRedirects: false`) matters for the gateway, and whether `Check response` reads anything only the redirect path set, needs reading before removing anything. It is a live-flow edit: hot-deploy via the Node-RED admin API (as in CARD-0365), then re-export the tab into `core/data-pipeline/environmental-data.flow.json`; do it while the POST queue is empty so nothing in flight is lost.

**Done when:** the nodes are renamed for the gateway (or the redirect pair removed if confirmed dead), a real reading still lands afterward, the repo export matches the live tab, and the README's note about the leftover names is deleted. Related: CARD-0366 (documented it), CARD-0369 (same live-vs-repo export pattern), CARD-0226 (why the redirect nodes existed).

### CARD-0372 · [enhancement] [tos] Automated credential rotation -- a values-free registry, per-credential recipes, and a runner that never prints a value

**Status:** Build

**OPEN ITEM, 2026-10-02 (moved here from CARD-0334 -- this is tooling-build work, not incident/policy): re-test `.claude/settings.json`'s deny rules from a FRESH Claude Code session in this repo.** The `tos` session that drafted and placed the file couldn't get it to block a `Read`/`Grep` of `credentials.local.md` even after confirming the file existed at the right path with correct-looking JSON (see CARD-0334's Fourth occurrence for the incident this surfaced from) -- leading theory is that an already-running session caches its permission set at startup and never reloads project settings, but a syntax problem in the deny patterns isn't ruled out. A fresh session asking to read/grep `credentials.local.md` (or any `secrets.yaml`) and getting refused settles it; still succeeding means the deny rules themselves need fixing. Do this before trusting the guardrail for anything -- and before trusting Phase 1b/c below, which build on the same settings.json.

**Raised 2026-09-29 13:46 MST (general session; Joseph: "i want to create an automated key rotation process").** *No secret values in this card -- credentials are named, never quoted.* Essence-only until Planning interviews it; the sketch below is the assistant's proposal, not a decision.

**Why now.** Manual rotation has three costs this project has already paid: (1) **it is a multi-holder chore that goes wrong quietly** -- the gateway key alone lives in the gateway `.env`, the orchestrator `.env`, Node-RED's environment, GPSLogger's Headers field and Tasker's header, and CARD-0365 needed all of them touched; (2) **the rotation session is itself a secret-handling session** -- CARD-0334 records three separate transcript exposures (2026-09-24, 2026-09-28, 2026-09-29 13:46 MST), and a rotation done by hand or by an ad-hoc script is exactly where the next one happens; (3) **the cadence policy is unenforced** -- `credentials.local.md`'s Credential Rotation Cadence table has "fill in"/"not recorded" for most last-rotated dates, so nothing knows what is overdue.

**Relationship to CARD-0334 (read both before starting).** CARD-0334 is the incident record plus the guardrails plan: Step 0 (where each secret lives), Phase 0 (a minimal machine store -- Windows Credential Manager -- and the `secret` helper: `secret set`, `secret run`, `secret has|fingerprint`, `secret new`), Phase 1 (deny rules and hooks), and a *manual* rotation bridged by clipboard. **This card is the automation layer on top of that, not a competitor:** it needs Phase 0's store and helper to exist (do not build a second store), and it should be the thing CARD-0334's "rotate using the safe path" step actually uses. CARD-0370 (rotate the data-pipeline key) and CARD-0332's exposed-secret list become the first credentials run through it; CARD-0332's plaintext-token-in-`flows.json` fix is a prerequisite for the HA-token recipe.

**Two Windows profiles (Joseph, 2026-09-29 14:17 MST: both profiles run Claude Code, RoboForm and terminals; both have an SSH key to the Pi and M8; both use the one working copy `C:\Shared\jctsh`).** This reopens CARD-0334's settled decision 1, which assumed a single profile. **The Windows Credential Manager is per Windows user (DPAPI-bound):** a value stored from one profile is invisible to the other, and a rotation run in profile A cannot update profile B's vault (that needs B's login). Left as-is, every rotation would leave the *other* profile holding a dead value -- sessions there would start failing with 401, or worse, quietly keep using the revoked old one -- and the "rotate again" recovery would have to be repeated once per profile. **What is unaffected:** the registry, the sync flags and the runner's resume-state file all live under the shared repo path and are visible to both; SSH works from both; the clipboard step works because the profile running the runner *is* the one whose desktop you are in; RoboForm is entered once and (assuming your RoboForm sync) appears in both; a checked-in project `.claude/settings.json` (deny rules, hooks) covers both, where user-level settings would not. **Two new requirements:** a lock file so two profiles can't rotate the same credential at once, and one shared machine store both profiles can read and write.
**Store options (open decision 0 below):** **(A) Credential Manager per profile** -- keep CARD-0334's choice, `secret set` run once in each profile, and treat the other profile's vault as stale after every rotation (the runner records `stored_in: [profile]` and the overdue check nags "run `secret pull` in the other profile" -- but there is nothing shared to pull *from*, so it means re-entering the value by hand). Lowest new machinery, worst day-to-day. **(B1) A shared encrypted vault file** -- outside the repo tree (e.g. `C:\Shared\.jctsh-vault\`, ACL'd to the two users, so a repo-wide grep can't reach it), encrypted with a standard AEAD (AES-GCM from a well-known library -- no home-made crypto); the encryption key lives in each profile's Credential Manager (one `secret init` per profile, with a recovery copy in RoboForm). A rotation in either profile updates the one file; both see it immediately. **(B2) A KeePassXC database in the same place** -- scriptable through `keepassxc-cli`, has a GUI for you to inspect it, mature and widely used; its master password/keyfile is held in each profile's Credential Manager. Adds a piece of software but avoids writing any storage code. **Same at-rest limits as CARD-0334's design under all three:** any process running as you can read the store, so the barrier is `secret run`'s masking plus the Phase 1 hooks, not the store. **Recommendation:** B2 (or B1 if you'd rather not install anything) -- the two-profile setup is precisely the "reason to switch" CARD-0334 said would be needed before adding KeePassXC.

**Proposed shape.**
- **A values-free registry** (`tos/credential-registry.yaml` or similar, committed): per credential -- name, tier and interval (from the cadence policy), `last_rotated`, every **holder** (host, file/var/UI setting, and whether it is *scriptable* or *manual*), the **recipe** that rotates it, a **verify** check per holder, and whether the server can **dual-accept** old and new. **The registry is the source of truth for the inventory (what exists, where it is used, how to rotate and verify it, when it was last rotated) -- never for values.** Values have two homes with different jobs: **RoboForm is the human system of record** (Joseph's recovery copy), and **the Windows Credential Manager is the machine working copy** the runner reads. The registry is the one place that lists every credential and holder; RoboForm cannot answer "where is this used / is it overdue", and no program can read RoboForm. It is the form of CARD-0334's Step 0 inventory that a program can read; `credentials.local.md` shrinks to non-secret human notes (URLs, usernames, ...) or is retired -- no values, and no second copy of the inventory to drift. Each entry also carries a **`roboform_synced`** flag (see the sync bullet below).
- **A recipe per credential, one fixed lifecycle:** generate -> stage the new value beside the old -> distribute to scriptable holders -> **verify each holder actually works with the new value** -> cut over -> **wait for the RoboForm paste to be confirmed (bounded, see below)** -> revoke the old -> record `last_rotated`. The value is generated inside the tool and written straight to the store and the holders; it never appears in a command line, a log or a transcript -- output is holder names, pass/fail and fingerprints only.
- **Dual-accept windows are what make it safe.** The gateway takes exactly one `API_KEY` today; adding an `API_KEY_PREVIOUS` (accept either for a bounded window) means phone-side holders can move at leisure and a half-finished rotation never breaks capture. Same idea for `WEBHOOK_SECRET` and the NetAlertX signing secret. Credentials whose server cannot dual-accept (a Mosquitto password, the Node-RED admin password) get a short cutover instead, and a rollback that restores the previous value from the store until revoke.
- **A runner:** `rotate <name> [--dry-run|--verify-only]`. Dry-run prints the plan (holders, order, what will be checked) with no values. Interactive from the workstation first; unattended only for credentials where every holder is scriptable, and only after several supervised runs (this project's own "watch it work before trusting it unattended" precedent -- `pi-image-pull.py --schedule`).
- **Manual holders stay manual, but guided:** phones (GPSLogger's Headers, Tasker's header) and ESP32 firmware can't be set by a script. The runner stops at those steps, puts the new value on the clipboard (auto-cleared ~60 s, per CARD-0334's design), prints the exact field to paste it into, and waits for a verify check to pass before continuing.
- **RoboForm sync and recovery (amended 2026-09-29 14:05 MST, Joseph: "what happens when a new pw value doesn't get pasted into RoboForm?").** RoboForm can't be scripted, so the runner cannot know the paste happened; the only risk is the Credential Manager holding a newer value than RoboForm. Design: (1) **`roboform_synced` starts false after every rotation and flips true only when Joseph confirms** (`rotate --confirm-synced <name>`); a false flag shows in the overdue check and the Session Start summary, so a forgotten paste is a visible open item, not a silent one. (2) **The revoke step is gated on that confirmation, with a bounded wait** (draft: 14 days): until then the *previous* value stays valid, so RoboForm's old copy still works and nothing is lost; after the window the old value is revoked anyway and the flag stays false. **Who enforces the window (amended 2026-09-29 14:09 MST, Joseph: "what happens after 14 days?"):** an interactive runner does nothing on its own on day 14, so the cap must not depend on it -- **the gateway enforces the expiry itself**: `API_KEY_PREVIOUS` is paired with an expiry timestamp (e.g. `API_KEY_PREVIOUS_EXPIRES`, set by the runner when it opens the window) and `_authorized()` stops accepting the previous value after that instant, with no runner, timer or session involved. The runner's own revoke step (`rotate --resume`, which removes the `.env` entries and records `last_rotated`) is the tidy-up and the backup, not the enforcement; the Session Start overdue check and a push notification flag "rotation X passed its window with no RoboForm sync". The same pattern (a server-side expiry beside the previous value) applies to any credential whose server can dual-accept; credentials that can't get a short cutover instead. An unattended timer that runs `--resume` on schedule is a later addition, after several supervised runs. **State after a missed window:** nothing is broken (every holder is on the new value), RoboForm holds a dead old value -- worse than an empty entry because it looks valid -- the flag stays false and keeps nagging, and recovery is unchanged (`secret copy` if the Credential Manager is intact, otherwise rotate again). A missed window costs a stale RoboForm entry, never an outage. (3) **`secret copy <name>` re-places the current value on the clipboard** for a late paste, any time the Credential Manager is intact. (4) **If the Credential Manager is lost** (local to one Windows profile, unsynced, DPAPI-bound) **and RoboForm is stale, the recovery is to rotate again** -- the runner needs no old value to do that for scripted holders (SSH/`.env`/API access is enough; the gateway can take a brief cutover instead of an overlap window), and the manual holders (phones) are re-pasted from the new value. Losing a value is therefore a re-run, not a crisis -- which is the strongest argument for automating this. (5) **The exception is a provider-issued key** (Thunderforest, Xeno-canto, the Anthropic and Immich keys): there is nothing to re-generate locally, so a lost value means minting a new one at the provider. Those are out of first scope and are the credentials where the RoboForm copy matters most.
- **Overdue enforcement:** the registry's `last_rotated` + interval feeds a Session Start check (same family as the `Auto verify` markers) and a push notification, so the cadence stops being a table nobody reads.

**What can be automated, and what can't (initial read -- to be confirmed in Planning):**

| Credential | Holders | Automatable? |
|---|---|---|
| data-pipeline `API_KEY` | gateway `.env`, orchestrator `.env`, Node-RED env, GPSLogger, Tasker | Servers yes (needs `API_KEY_PREVIOUS`); phones manual. **Best pilot -- every holder is known and verifiable (`/version`, `/health`, the legacy-auth log).** |
| `WEBHOOK_SECRET` | orchestrator `.env`, gateway `.env` (`_relay_log`), Tasker/other webhook callers | Mostly yes |
| NetAlertX webhook secret | NetAlertX publisher setting, Pi Node-RED environment file | Yes if NetAlertX's setting is reachable by API; otherwise one manual step |
| HA long-lived tokens | Node-RED, photo-tv-display, orchestrator, Claude Code | Yes -- HA can mint and revoke long-lived tokens over its API; blocked on CARD-0332 and best done as one token *per consumer* (CARD-0334 Phase 3) |
| Mosquitto account passwords | broker, each consumer, HA's UI-only MQTT config, ESP32 firmware | Broker + server consumers yes; ESP32s need a rebuild/OTA (scriptable with ESPHome but a per-device event); HA's MQTT config is a UI step |
| Node-RED admin password | `settings.js` bcrypt hash, Node-RED restart | Yes, with a short cutover |
| Log Dashboard password | `/etc/jctsh/log-server.env`, service restart | Yes |
| ESP32 OTA/MQTT device secrets | firmware, `secrets.yaml` copies | Reflash per device; batch with CARD-0334's Phase 3 unique-per-device work |
| SSH keys, Cloudflare tunnel credentials, Immich API keys | assorted | Out of first scope |

**Implementation steps (amended 2026-09-29 14:17 MST for the two-profile setup):**
| # | Step | Depends on | Profile-sensitive? |
|---|---|---|---|
| 0 | Decide the shared store (decision 0) | -- | it *is* the decision |
| 1 | ~~Reconcile: record where each secret lives; seed the values-free registry (CARD-0334 Step 0)~~ **SEEDED 2026-09-29 14:31 MST** -- Joseph's RoboForm answers still to collect | -- | no |
| 2 | ~~Gateway dual-accept + server-side expiry (`API_KEY_PREVIOUS`, `_EXPIRES`, which-key-used log, `VERSION` bump) -- ships standalone~~ **DONE 2026-09-29 14:28 MST** | -- | no |
| 3 | The shared store + `secret` helper (`set`, `run`, `has/fingerprint`, `new`, `copy`) with a per-profile `secret init`; lock file for concurrent runs (CARD-0334 Phase 0) | 0 | **yes** |
| 4 | Guardrails: checked-in `.claude/settings.json` deny rules, `PreToolUse`/`PostToolUse` hooks and the output tripwire (CARD-0334 Phase 1) | 3 | partly -- project-level settings cover both profiles |
| 5 | Runner skeleton: `rotate --dry-run` / `--verify-only` -- read-only, no values | 1 | SSH keys (both profiles have one) |
| 6 | Pilot recipe: the data-pipeline key (CARD-0370) -- scripted holders, phones, `roboform_synced`, expiry. **First confirm where Node-RED gets `DATA_PIPELINE_KEY`** (its `environment` file vs. the `global-config` env inside `flows.json`) -- the recipe can't update that holder until this is known | 2, 3, 4, 5 | yes |
| 7 | A second recipe from another class (Log Dashboard or an HA token), supervised | 6 | yes |
| 8 | Overdue check at Session Start + push notification | 6 | no |
| 9 | Later: unattended timer; ESP32/Mosquitto recipes | 7 | -- |

**Open decisions for Planning (each with the assistant's recommendation):**
0. ~~**Which shared store? (new -- the two-profile setup)**~~ **DECIDED 2026-09-29 14:21 MST (Joseph: "b2"): a KeePassXC database outside the repo tree, its master credential held in each profile's Credential Manager.** Amends CARD-0334's decision 1 (machine-store half). Not yet installed on this workstation (`keepassxc-cli` and `C:\Program Files\KeePassXC` both absent, checked 2026-09-29 14:21 MST); `winget` v1.29 is available. Still to settle when Phase 0 is built: KeePassXC installed for *both* profiles (per-user or all-users install); the vault location (proposed `C:\Shared\.jctsh-vault\`, outside `C:\Shared\jctsh` so a repo grep can't reach it, ACL'd to the two profiles); master password vs. key file (proposed: a generated key file, stored in each profile's Credential Manager, with a recovery copy in RoboForm); the database's entry layout, mirroring the registry's names; and that `secret run` reads through `keepassxc-cli` with output masked -- `keepassxc-cli show` prints a value to stdout, so it is only ever called inside the helper, never from a session directly (a Phase 1 hook denies direct calls).
1. **Where does the runner run?** An unattended job on the M8/Pi can't use a workstation store. *Recommendation:* interactive from the workstation, in whichever profile you are in, with the shared store as the source of truth, for the first several credentials; revisit an unattended M8 runner (root-only file, or a small local secrets service) only if a fully server-side credential is worth automating end to end.
2. **Pilot credential.** *Recommendation:* the data-pipeline `API_KEY` -- it is CARD-0370 already, every holder is known and independently verifiable, and it forces the `API_KEY_PREVIOUS` dual-accept design that later recipes reuse.
3. **Dual-accept in the gateway.** *Recommendation:* yes -- small, additive (`_authorized()` already has one comparison path), and it turns "rotate" from an outage-risk event into a window. **Include the server-side expiry** (`API_KEY_PREVIOUS` + `API_KEY_PREVIOUS_EXPIRES`): ignore the previous value once the expiry has passed, log which key (current or previous) each request used -- rate-limited per path, like the existing legacy-auth line, which is how the runner detects that a manual holder has moved -- and bump `VERSION`. Standalone, useful before any of the rest is built.
4. **Scope of "automated".** *Recommendation:* the registry, the runner and the recipes for the server-side credentials first; ESP32 firmware secrets and Mosquitto-on-device rotation later, as their own recipes, since each needs a per-device reflash.
5. **Sequencing against CARD-0334.** *Recommendation:* CARD-0334's Phase 0 (store + `secret`) first, its Phase 1 hooks second, then this card's runner built on `secret`; CARD-0370 is rerun as the pilot rather than rotated by hand, unless the exposure is judged urgent enough to rotate the gateway key manually first.

6. **Gate the revoke on the RoboForm paste, and for how long?** (added with the sync design above) *Recommendation:* yes, with a 14-day maximum wait -- long enough that a forgotten paste is caught by the overdue nudge, short enough that an old credential does not stay valid indefinitely. The trade-off is real: gating keeps the old value alive (a security cost, bounded by the window) in exchange for never stranding a rotation with no usable human copy.

**Done when (draft):** the registry lists every credential in CARD-0334's inventory with holders and recipe; `rotate --dry-run` works for all of them and a real run works for at least the pilot and one credential from another class, each ending in a passing per-holder verify and a recorded `last_rotated`; no run ever prints a value (checked by the CARD-0334 Phase 1 tripwire); overdue credentials surface at Session Start.

**Related:** CARD-0334 (incident record, store, guardrails -- prerequisite), CARD-0370 (pilot), CARD-0371 (removing `?key=`, which should land before the gateway key is rotated), CARD-0332 (plaintext HA token), CARD-0365/CARD-0367 (where this session's exposures came from), CARD-0280 (HA token rotation checklist), `credentials.local.md` §Credential Rotation Cadence.

**Step 2 done and deployed, 2026-09-29 14:28 MST.** Gateway `VERSION 2026-09-29.4` in production (healthy, current key unchanged, no previous key set). `API_KEY_PREVIOUS` + `API_KEY_PREVIOUS_EXPIRES` (ISO 8601 UTC or epoch): the previous key is accepted only inside its window and only if a valid expiry is set; the gateway closes the window itself. New authenticated `GET /auth-status` returns previous-key configured/active/expires and the latest time each path authenticated with `current` vs `previous` (in memory since start; never a key) -- the signal a runner polls to see a manual holder has moved. Both keys are compared in constant time. **Verified:** eight unit cases (active window, expired, no expiry, unparseable expiry, epoch expiry, no previous, wrong key, header/query forms), then a live test on a throwaway second container with fake keys: in-window `new=200 old=200 bad=401`, then after expiry `new=200 old=401` with nothing else running; that container was removed and production's `.env` was never touched. Docs: README (auth paragraph + `/auth-status` route), `.env.example`.

**Step 1 seeded, 2026-09-29 14:31 MST.** `tos/credential-registry.yaml` created: 17 entries (data-pipeline API key, retired Apps Script key, webhook secret, NetAlertX webhook secret, HA token, Node-RED admin password, Log Dashboard password, the 12 Mosquitto accounts as one grouped entry, ESP32 device secrets, Robin's HA password, Pi/M8 SSH, NetAlertX password, router password, Immich credentials, the GitHub PAT, the deletion-log key, and provider-issued keys). Built from `credentials.local.md`'s *structure* (a fail-safe extractor that can only print headings, entry labels and a value-state flag -- it cannot print a value), CARD-0334's inventory and what the repo's code reads; checked afterward for value-like tokens (none) and that it parses. Every entry has holders with `kind: scripted|manual` and a `verify` check; holders I confirmed this session are `verified: true`, the rest `verified: false`. **Not done -- needs Joseph:** `roboform` is `unknown` on all 17 (RoboForm is not visible to a session). **Findings from the pass:** (a) only four credentials have a recorded `last_rotated` (Pi/M8 SSH 2026-07-10, NetAlertX password 2026-07-12, router password 2026-07-09, the GitHub PAT 2026-07-31 as created); the other 13 are `unknown`, which means the overdue check would flag them all from day one; (b) nine entries carry a recorded exposure; (c) the cadence table's `fill in` placeholders (HA token, the Apps Script key, DuckDNS token, Immich account passwords, Log Dashboard password, Robin's HA password) are last-rotated *dates* nobody wrote down, not missing secrets -- every one of those has a value in the file; (d) the Node-RED broker-node and Home Assistant MQTT credentials are the only ones held solely inside another application (encrypted/UI-only), so they have no scriptable source to compare against; (e) the exact source of Node-RED's `DATA_PIPELINE_KEY` (environment file vs. the `global-config` env inside `flows.json`) is unconfirmed and must be settled before that holder's recipe is written.

**Moved to Build 2026-09-29 16:40 MST (Joseph).** Scoped in place through the design conversation rather than a separate Planning pass: decision 0 (shared store = KeePassXC, B2) is settled, the other decisions carry recommendations on the card, and Steps 1 (registry seeded) and 2 (gateway dual-accept + expiry, deployed) are already done. **Next:** Step 3 -- install KeePassXC for both Windows profiles and build the `secret` helper, per the implementation-steps table above.

**Two new decisions, 2026-10-02 (from CARD-0377, which hit a real case this card hadn't covered: AQM dropped MQTT entirely, orphaning its Mosquitto account).**

1. **Retirement is a different lifecycle event than rotation, and the registry didn't model it.** Rotation replaces a value; retirement means a credential stops existing anywhere, no replacement. Added a `retired: null | "<date>: <reason> (<card>)"` field (schema documented at the top of `tos/credential-registry.yaml`, same placement rule as `rotation_requested` -- on a grouped entry it goes on the specific sub-account, not the top-level id). It's a permanent historical marker, not a pending-action flag: once set, it stays. Setting it does NOT touch RoboForm -- the registry has no visibility into RoboForm to confirm or force that, so a retired entry's RoboForm row is Joseph's own separate cleanup, same as `roboform_synced` already assumes for rotation.

2. **Workflow decision (Joseph): credential fallout from a card's own work gets handled AS PART OF that card, not as a separate prompt.** Verbatim: "as part of working a card, when a credential change is needed, do it, then add it to the registry. you shouldn't have to prompt for the other credential maintenance. let the runner do it." Applied immediately on CARD-0377 itself: the AQM Mosquitto account was deleted from the Pi's `/etc/mosquitto/passwd` live and the registry marked `retired`, inline, without a separate ask. **Requirement this sets for the eventual runner (Step 3+, not yet built):** detecting a credential whose only holder just went away (a firmware rewrite drops a secret, a service is retired, etc.) should be something the runner surfaces or even acts on itself -- not something that depends on whoever is working the OTHER card happening to notice and ask. Exactly what "the runner does it automatically" looks like (a lint pass over holders vs. what's actually referenced in the repo? a manual `retire <id>` command that's still one step, just not a question?) is open -- deferred to when Step 3's `secret`/runner design is actually built, but recorded here now so it isn't lost.

**Step 1 fully closed, Step 3 half-started, 2026-10-02 (Joseph).** Joseph confirmed every credential in the registry now has a RoboForm entry -- all 24 `roboform: unknown` flipped to `yes` in `tos/credential-registry.yaml`. That was the one open item left on Step 1 (CARD-0334 Step 0's reconciliation, closed 2026-09-29 pending exactly this). **KeePassXC installed** (`winget install --id KeePassXCTeam.KeePassXC --scope machine`, 2.7.12, `C:\Program Files\KeePassXC`) -- confirmed machine-wide (not per-user `AppData`) and on the system `PATH`, so both Windows profiles see it without a second install; `keepassxc-cli.exe` present. **Not done yet (rest of Step 3):** no vault created at `C:\Shared\.jctsh-vault\` yet, no master key/key-file generated or placed in either profile's Credential Manager, and the `secret` helper itself doesn't exist.

**Vault created, 2026-10-02.** `C:\Shared\.jctsh-vault\jctsh-vault.kdbx` -- `keepassxc-cli db-create --set-key-file jctsh-vault.keyx` (AES-256, AES-KDF 1,000,000 rounds), key-file-only (no master password, per decision 0's proposal). Verified it unlocks (`db-info -k ... --no-password`): 0 entries, 1 group (default), no corruption. **The key file itself is still just a loose file on disk at `C:\Shared\.jctsh-vault\jctsh-vault.keyx`** -- not yet placed in either profile's Credential Manager, no recovery copy in RoboForm. Per the design, it should not stay a loose file once those copies exist. **Not done:** Credential Manager placement (both profiles -- DPAPI is per-user, so the second profile's copy has to be added from inside that profile, not this session), RoboForm recovery copy, deleting the loose file, populating any entries, and the `secret` helper that would actually read this vault.

**Key file custody, 2026-10-02.** Placed in **this** Windows profile's Credential Manager -- generic credential, target `jctsh-vault-keyfile`, `CRED_PERSIST_LOCAL_MACHINE` (per-user/DPAPI), written via a one-off P/Invoke helper (`CredWrite`), verified byte-identical on readback (SHA-256 match) without ever printing the content; also visible via `cmdkey /list:jctsh-vault-keyfile`. **RoboForm recovery copy saved** (Joseph) -- as a Safenote named `jctsh-vault-keyfile`, holding the key file base64-encoded as plain text (RoboForm's attach-file option wasn't found/available in this install, so base64-in-a-note is the fallback; same recovery shape either way -- decode the text back to `jctsh-vault.keyx`). **Explicitly left open (Joseph, 2026-10-02): the other Windows profile's Credential Manager copy.** Not a blocker -- the RoboForm copy is enough to seed it later (decode the Safenote's text to a temp file, run the same `CredWrite` pattern from inside that profile, delete the temp file). The loose file at `C:\Shared\.jctsh-vault\jctsh-vault.keyx` is still on disk pending that decision.

**Helper renamed, 2026-10-02 (Joseph): `sec` -> `secret`.** Every reference on this card and on CARD-0334 renamed (`secret set`, `secret run`, `secret has`/`fingerprint`, `secret new`, `secret copy`, `secret init`, `secret pull`, "the `secret` helper") -- design-only rename, no code exists yet to migrate. `jctsh-vault-keyfile` and `jctsh-vault.kdbx`/`.keyx` filenames are unaffected (they're the vault's own names, not the helper's).

**New-credential workflow, stated explicitly, 2026-10-02 (a real gap this document had -- every workflow note above covered *rotating* an existing credential, none covered a brand-new one appearing).** When a card's work needs a credential that doesn't exist yet:
1. **Generate the value** -- `secret new <id>` once the helper exists; by hand (a one-off script, clipboard, never printed) until then, same pattern used for `jctsh-vault-keyfile` itself.
2. **Apply it to wherever it actually needs to live** -- create the account/`.env` var/etc., and verify it live (same discipline as any other Build work, e.g. `components/air-quality-monitor`'s/`back-patio-temp-sensor`'s original Mosquitto-account creation: a real `mosquitto_pub` test, not inferred).
3. **Add a new `- id:` entry to `tos/credential-registry.yaml` by hand** -- `what`/`class`/`tier`/`holders` are judgment calls (what this is, where it's used, how critical) that no generator can infer; `secret`/`rotate` only ever write back to an *existing* entry's `last_rotated`/`roboform_synced`, never author a new one. Follow the existing entries as the template, per the schema comment at the top of the file.
4. **Create a matching RoboForm entry**, named to match the `id`, paste the value in.
5. **Flip that entry's `roboform: yes`** once pasted, and confirm each holder against its `verify` check.

**This is the creation-flavored version of CARD-0377's standing rule, not a separate process** -- steps 3-5 happen *as part of* the card that needed the new credential, inline, without a separate prompt, same as a rotation's or retirement's registry fallout.

**The `Joe` Windows profile is set up for the vault, 2026-10-01 20:15 MST (Joseph: set up only what this profile needs -- build nothing; the vault and the `secret` helper belong to the other profile's session).** Done from inside the `Joe` profile: (1) **KeePassXC check** -- the machine-wide install (2.7.12, `C:\Program Files\KeePassXC\`) is on the *machine* `PATH`, so a new terminal for this profile resolves `keepassxc-cli.exe`; the session this was done from did not see it only because its own `PATH` predated the install. (2) **This profile's Credential Manager seeded** -- generic credential, target `jctsh-vault-keyfile`, user field `jctsh-vault`, `CRED_PERSIST_LOCAL_MACHINE`, blob = the 278-byte key file, written with the same one-off `CredWrite` P/Invoke pattern the other profile used (no prior entry existed here, so nothing was overwritten); read back and verified byte-identical to the file on disk without printing the content or any hash. (3) **Proved this profile can unlock the vault from that Credential Manager copy** -- temp key file written from the readback, `keepassxc-cli db-info -k <temp> --no-password` opened `jctsh-vault.kdbx` (AES 256-bit, AES-KDF 1,000,000 rounds, 1 group, 0 entries); the temp file was deleted and its absence confirmed. **Effect on the open item in "Key file custody" above:** both Windows profiles now hold a Credential Manager copy of the key file (the other profile's was placed by the other session -- this session cannot see another profile's Credential Manager, so that half is taken from the note, not re-verified). **Deliberately NOT done (Joseph, 2026-10-01 20:15 MST):** the loose `C:\Shared\.jctsh-vault\jctsh-vault.keyx` was **not deleted**. Until it is, anyone who can read that folder (`Joe`, `jcthomas`, Administrators, `SYSTEM`) has both halves of the lock, which is the thing the key-file design exists to prevent; removal is a decision for Joseph / the other session, and the open-test above means it is now known to be safe. Also not done: no `secret` helper, no vault entries, no ACL changes, no repo files other than this note.

**Verified from the `jcthomas` profile, 2026-10-02.** Re-ran `db-info` against the shared vault with this profile's own key file -- unchanged from creation (`Database created: 10/2/2026 2:24 AM`, `Last saved: 10/1/2026 7:24 PM`, 1 group, 0 entries), confirming the `Joe` session's work added no vault entries, matching its own note. Loose key file still present, still 278 bytes, SHA-256 fingerprint recorded (`c8ad7631dd2b...`, safe to show -- a fingerprint, not the value) for future tamper comparison. **Can't verify the `Joe` profile's Credential Manager entry itself** -- same DPAPI per-user limitation that note already flagged about mine; taking it on their own stated verification (byte-identical readback).

**First `secret` helper built, 2026-10-02 (`tos/secret.ps1`, PowerShell).** Covers the full planned surface: `init` (doctor check, no values), `has <name>`, `fingerprint <name>` (SHA-256 only, never the value), `new <name>` (generates entirely inside `keepassxc-cli -g`, never passes through the script, result placed on the clipboard via `keepassxc-cli clip` with its own built-in auto-clear timeout), `copy <name>`, `set <name>` (interactive-only, keepassxc-cli's own masked prompt -- run by hand, never from a session), and `run -Name -EnvVar <cmd>` (injects one value into a child process's environment only, masks its exact value in that command's output). Reads the key file from **this** profile's Credential Manager into a short-lived temp file per call, deleted immediately after (same pattern both profiles already used by hand). **Tested end-to-end against a real throwaway vault entry** (`test-entry-delete-me`) -- created, fingerprinted, clipped, injected into a child PowerShell process and printed by it (output showed `[REDACTED]`, confirmed via exit code and masked text, never by seeing the raw value), then permanently removed (KeePassXC moves a deleted entry to `Recycle Bin/` instead of purging it -- had to `rm` it a second time, from the Recycle Bin path, to actually clear it; worth knowing for anyone deleting an entry by hand later). Vault confirmed back to 0 live entries, empty Recycle Bin.

**One real bug found and fixed during testing:** the dispatch parameter was originally named `$Command`, which PowerShell's own binder intercepted whenever the child command passed to `run` itself contained a `-Command`-shaped flag (e.g. `powershell.exe -Command ...`) -- broke `run` outright. Renamed to `$Action`. **Known limitation, not fixed:** the same class of collision is still possible with `run`'s other named parameters (`-Name`, `-EnvVar`) if a child command happens to use an identically-named flag -- no `--` end-of-options separator implemented yet; noted rather than engineered around before a real case actually needs it.

**Not built:** the registry-aware `rotate <id>` orchestrator (reads holders/dual_accept/verify from `credential-registry.yaml`, writes back `last_rotated`/`roboform_synced` -- `secret.ps1` itself never touches the registry, per the "how does secret interact with the registry" note above), the cross-profile lock file, and `init`'s per-profile bootstrap beyond the read-only doctor check (seeding a brand-new profile's Credential Manager entry is still a deliberate by-hand act).

**Moved off Windows onto the M8, overnight 2026-10-01/02 (Joseph: "building a dependency on windows... manage it not on windows," then "yes, m8").** Built unattended per Joseph's explicit instruction, with one standing boundary he set first: build the process fully, but do not execute any live credential rotation -- that stays a session-start, in-the-moment decision (CARD-0334 decision 2), and he explicitly wants to be offered a real walkthrough the next time he runs Session Start. Nothing below touched a live holder or rotated anything real; every test used a throwaway vault entry, created and permanently deleted (including from KeePassXC's own `Recycle Bin/` group, which a plain `rm` doesn't clear).

**What's built and verified:**
1. **Vault moved to the M8** -- a fresh `jctsh-vault.kdbx`/`.keyx` at `/home/jct/.jctsh-vault/` (key-file-only, AES-256, AES-KDF 1,000,000 rounds), key file mode 0600 owned by `jct`. Verified open with `db-info`.
2. **`secret.py`** (new, M8-hosted, deployed `/usr/local/bin/secret.py` root:root 0755, same convention as `maintenance-check.py`) -- `init`/`has`/`fingerprint`/`new`/`copy`/`set`/`run`, all tested end to end against a throwaway entry, including `run`'s masking (child process got the real value via its environment, printed it, this script's own output showed `[REDACTED]`).
3. **`secret.ps1` rewritten** as a thin Windows-side SSH wrapper -- every vault-touching command relays to `secret.py` over `ssh jct@m8.local`; a value crossing back from `new`/`copy` lands straight on the Windows clipboard, never printed to the console or written to disk here. `due` is unchanged -- still fully local, no M8 round-trip, since it only ever read the values-free registry. Full lifecycle retested through the wrapper itself, not just `secret.py` directly.
4. **`rotate.ps1`** (new, CARD-0372 Step 5's skeleton) -- reads one registry entry, prints its rotation plan (holders, kind, verify checks). Read-only, dry-run only; tested against `webhook-secret` (output matches the real entry exactly), a grouped entry (`mosquitto-accounts` -- correctly reports it can't parse the `accounts:` shape yet rather than silently misreporting), and a nonexistent id.
5. **CARD-0334 Phase 4** -- root `CLAUDE.md`'s "credentials are off-disk" line corrected (they're plaintext, gitignored, on disk), the never-print rule added to `JCTsh-Operating-System.md`'s Engineering Discipline for the first time (it existed on this card and in `CLAUDE.md` but nowhere in the process doc itself).
6. **Windows side decommissioned** -- old Windows vault (0 entries, nothing lost) and `jcthomas`'s own Credential Manager entry deleted.
7. **A real bug found and fixed** while building `secret.py`: `argparse.REMAINDER` mixed with a required optional in the same subparser is documented-unreliable (Python bpo-9540/17050) -- `run`'s child-command parsing now splits on a literal `--` manually instead.

**Blocked, not worked around: CARD-0334 Phase 1's `.claude/settings.json` guardrails.** The `update-config` skill refused with "Self-Modification" -- Claude Code's own auto-mode classifier won't let a session change its own permission configuration, even to add deny rules, and writing the file directly instead would just be routing around the same protection by a different door. This needs Joseph himself, or his explicit go-ahead for a session to do it.

**DECISIONS MADE OVERNIGHT, FOR JOSEPH'S REVIEW (none of these had an obvious single right answer; flagged per his instruction to log and discuss rather than ask mid-flight).** Walked through together 2026-10-02 -- resolution noted on each:
1. **Built a brand-new vault/key on the M8 rather than migrating the Windows one's actual key material.** Agreed, no action -- the Windows vault had 0 entries, nothing to lose.
2. **No RoboForm recovery copy existed yet for the M8's key file.** RESOLVED same session -- the M8 key's base64 text was relayed to the clipboard (never printed), Joseph pasting it into a new Safenote `jctsh-vault-keyfile-m8`, leaving the old Windows-key Safenote (`jctsh-vault-keyfile`) as-is (see item 4).
3. **`new`/`copy`'s clipboard path had lost the auto-clear timeout.** FIXED -- `Set-ClipboardWithAutoClear` in `secret.ps1`: a detached background process clears the clipboard after `-Timeout` seconds, only if it still holds the exact value set (SHA-256 fingerprint match), so it never clobbers something else copied in the meantime. Tested both paths live.
4. **ACTION ITEM FOR THE `Joe` PROFILE (not this session's to do -- DPAPI is per-user):** from that profile, run `cmdkey /delete:jctsh-vault-keyfile` to remove its now-superseded Credential Manager entry, and delete the old RoboForm Safenote named `jctsh-vault-keyfile` (the Windows-era one -- keep `jctsh-vault-keyfile-m8`, the current one, from item 2). Both point at a vault that no longer exists; harmless but worth clearing rather than leaving as clutter.
5. **`rotate.ps1` didn't handle grouped entries' `accounts:` map.** FIXED -- parses `mosquitto-accounts`' 12 sub-accounts plus its shared `broker_holder` (a second real bug found and fixed in the same pass: the first fix consumed the `broker_holder` line as "accounts: block ended" and never actually tested it). `immich-credentials`/`esp32-device-secrets`/`provider-keys` turned out to already use the flat `holders:` shape `rotate.ps1` already handled -- `mosquitto-accounts` was the only entry actually affected. Regression-tested against `webhook-secret` and `immich-credentials` to confirm no behavior change there.
6. **CARD-0334 Phase 1 (guardrails) stays blocked on Joseph** -- confirmed he understands why (Claude Code's own self-modification block, not a soft preference); he'll apply the `.claude/settings.json` content himself once drafted.

**CARD-0334/CARD-0375 still can't close.** Per Joseph's own instruction, no live rotation happened tonight -- every credential either card names is exactly as rotated as it was before (`last_rotated: unknown` on all of them, per `secret.ps1 due`). What changed is that the mechanism to actually do it now exists and is tested; the next real step is picking one and walking it through live, which is explicitly what Joseph asked to be offered at his next Session Start.

### CARD-0371 · [enhancement] [data-pipeline] Remove `?key=` query authentication from data-pipeline-api once no caller uses it

**Status:** Backlog

**Raised 2026-09-29 12:34 MST (general session, from CARD-0365 phase 1).** The gateway still accepts `?key=` beside `Authorization: Bearer` so GPSLogger and Tasker can be moved without breaking capture. That leaves the exposure CARD-0365 exists to close only half closed.

**Done when:** the gateway's `legacy ?key=` log line has stayed quiet across at least one real hike (GPS Track is the slow one -- it only fires on a hike), `_authorized()` accepts the header only, `VERSION` is bumped and deployed, and `README.md`/`gps-pipeline.md` no longer mention the query form. **Unblocked as of 2026-09-29 13:10 MST:** GPSLogger and Tasker are both on the Bearer header (CARD-0365); what remains is the quiet-across-a-real-hike wait on the gateway's legacy log. Related: CARD-0365, CARD-0370.

### CARD-0370 · [enhancement] [data-pipeline] Rotate the data-pipeline API key (and the old Apps Script key) after the callers are on Bearer

**Status:** Backlog

**Priority:** High -- the exposed data-pipeline key (and the retired Apps Script key) are still valid; sequenced after CARD-0371 and the CARD-0372 runner, but the exposure is live. (set 2026-09-29 15:32 MST, triage)

**Raised 2026-09-29 12:34 MST (general session, from CARD-0365 phase 1).** The current `API_KEY` sat in Caddy's access log in full (664 lines/day, persisted) until the redaction went in, and Cloudflare's own logs may hold it; it was also echoed into a session transcript on 2026-09-29 during redaction testing. The retired Apps Script key is in `jctsh.log*` on the Pi from CARD-0367's leak (the endpoint is write-retired, so that one is low-value). Deliberately its own card, sequenced after CARD-0365/CARD-0371, so a rotation isn't tangled with the migration.

**Done when:** a new `API_KEY` is set in the gateway's `.env` and every holder updated together -- Node-RED env (`DATA_PIPELINE_KEY`), the orchestrator's `.env`, GPSLogger's header, Tasker -- and the old key is confirmed rejected (401); the Apps Script key's leftover copies in `jctsh.log*` are either judged harmless or scrubbed. Related: CARD-0365, CARD-0367, CARD-0334 (the broader credential-rotation backlog item).

### CARD-0369 · [bug] [data-pipeline] Node-RED Sheet Health flow still describes/probes the retired Google Sheet -- update to the data-pipeline-api gateway
**Status:** Done

Archived to `core/data-pipeline/card-archive.md` on 2026-09-29 (CARD-0193) — 2345B, over the 2000B size threshold.

---

### CARD-0368 · [enhancement] [hike-izer] Clean up stale Apps Script/"Phase 2, not migrated" wording in `fetch_hike_data.py` and sibling docstrings

**Status:** Done

**Raised 2026-09-29 11:50 MST (general session).** `components/hike-izer/fetch_hike_data.py`'s header still says the Apps Script/Sheets path (`fetch_sheet()`) is "Phase 2, not migrated yet" and shows a `--url <APPS_SCRIPT_DEPLOYMENT_URL>` usage line, but `--data-pipeline-url` is now the only required source (Phase 2 landed in `e954bcf`, 2026-09-29 08:23 MST). The stale wording is what a 05:00 backstop alert ran into: the deployed container still passed `--url` and `fetch_hike_data.py` exited with argparse status 2 (fixed by the 09:43 redeploy).

**Done when:** docstring/usage/comment references to the Apps Script path are removed or marked historical, any dead `fetch_sheet()` code and its `--url`/`--key` handling is deleted if unused, and `grep -rni "apps script\|fetch_sheet" components/hike-izer*` returns only deliberate history notes. Related: CARD-0349, CARD-0366.

**DONE 2026-09-29 11:56 MST.** `fetch_sheet()` and the `--url`/`--key` arguments were already gone from `fetch_hike_data.py` (`e954bcf`); what remained was wording. Fixed the module docstring and usage line, `fetch_table()`'s docstring, the CARD-0135/CARD-0275 retry comment, `sheet_health.py`'s "dead branch" note, `app.py`'s webhook-auth comment and `generation.py`'s probe-timeout comment. Comment-only, compile-checked; not yet redeployed (the deployed copies pick it up at the next orchestrator rebuild). Left deliberately as history: CARD-0214/0229/0275/0276 references in `generation.py` docstrings and both `card-archive.md` files. **Reflection:** when a migration finishes, grep the components for the retired system's name (`Apps Script`, old function names) in the same card that removes the code -- the stale usage line and "not migrated yet" note are what made the 05:00 failure look like a migration gap.

### CARD-0367 · [bug] [hike-izer] Alert text leaked a live API key onto the dashboard -- subprocess failures embedded full argv in MQTT alerts
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-29 (CARD-0193) — 2310B, over the 2000B size threshold.

---

### CARD-0366 · [enhancement] [data-pipeline] Rewrite the data-pipeline operational docs for data-pipeline-api -- README/architecture doc still describe the retired Apps Script

**Status:** Done

**Raised 2026-09-29 (general session, spun off CARD-0347 item 8 after scanning the board for CARD-0349 follow-on work).** `core/data-pipeline/README.md` and `JCTsh-Environmental-Data-Architecture.md` describe `environmental-data.gs`/Google Sheets as the live system -- schema, ingest routes, the health probe, everything. That system is now fully retired (CARD-0349): every real producer writes to `data-pipeline-api`/TimescaleDB instead, and the Apps Script survives only as a read-only historical reference. The operational reference doc for this whole pipeline is now describing something that no longer runs.

**What exists instead, already current but not the operational reference:** `core/data-pipeline/timescaledb-migration-plan.md` and `timescaledb-design.md` -- written during CARD-0349's own Planning/Design phases, accurate as of the migration, but framed as planning artifacts for a not-yet-built system, not as the living "here's how this pipeline works today" doc `README.md` is supposed to be (`JCTsh-Operating-System.md`'s own README-vs-CLAUDE.md distinction).

**Not yet scoped -- needs an interview when picked up:** likely shape is folding the design doc's real content (schema, routes, the cutover-complete architecture) into `README.md` as the new operational reference, leaving `timescaledb-migration-plan.md`/`timescaledb-design.md` as historical planning artifacts (not deleted -- they're the record of how the decision was made), and updating `JCTsh-Environmental-Data-Architecture.md`'s own payload-schema section to match the new tables. Whether `core/data-pipeline/CLAUDE.md`'s empty-stub gap (also named in CARD-0347 item 7) gets filled in the same pass is a scoping question, not decided here.

**Related:** CARD-0347 (the pipeline review this item was originally found in), CARD-0349 (the migration that made this doc stale), `core/data-pipeline/timescaledb-design.md`/`timescaledb-migration-plan.md` (the current-but-wrongly-framed content this would draw from).

---

**DONE 2026-09-29 12:07 MST (general session).** Scoped by the card's own "likely shape" without a separate interview -- Joseph's direction was simply "do 366". Built against the real code (`api/app.py`, `init/schema.sql`, `docker-compose.yml`, the live Node-RED flow, the running M8 containers), not the design doc.

**What changed:** `core/data-pipeline/README.md` rewritten as the operational reference for `data-pipeline-api`/TimescaleDB (files, flow diagram, where it runs, every gateway route, tables and dedup keys, Node-RED handler, health/backup/restore, deploy, limitations). `JCTsh-Environmental-Data-Architecture.md` v1.7: status banner, the Sheets Archive section rewritten as a Storage section, handler steps/gap handling/Lightning wording updated, both sheet-schema sections marked historical. `RUNBOOK-sheets-outage.md` marked RETIRED. `core/data-pipeline/CLAUDE.md` filled in (it had been an empty stub, CARD-0347 item 7). `environmental-data.flow.json` refreshed from the live Node-RED tab (it was still the pre-cutover Apps Script version, same staleness as CARD-0369).

**Left as-is, on purpose:** the Hiking Observations / Hike Start Forecast *implementation* sections of the Architecture doc still narrate the Apps Script pipeline (covered by the banner and one added note, not rewritten line by line); `timescaledb-design.md`/`timescaledb-migration-plan.md` untouched as planning history (design doc still says `bearing_deg`, real column is `direction` -- now noted in `CLAUDE.md`); three live Node-RED node names still say "Apps Script" (documented in the README, renaming needs a live-flow edit + re-export). **Not verified:** the `pg_restore` command in the README has never been rehearsed -- the README says so. **Reflection:** the README-vs-design-doc split matters -- a design doc written before the build drifts (wrong column name, wrong exposure detail) and should be marked as history the day the build lands, not left looking authoritative; and an operational README needs a "live copy vs. repo copy" line for anything edited in a UI (Node-RED).

### CARD-0365 · [bug] [data-pipeline] API keys travel in the URL query string across the whole data pipeline (old Apps Script and the new gateway alike)

**Status:** Done

**Raised 2026-09-29 (general session, spun off CARD-0347 item 6 after scanning the board for CARD-0349 follow-on work).** The 2026-09-26 pipeline review flagged `environmental-data.gs`'s `?key=<API_KEY>` pattern as a real, if minor, exposure -- a request URL carrying a secret ends up in web server access logs, proxy/CDN logs (Cloudflare, fronting `hikes.jctnet.com`), and (for GET requests) browser history on any device that ever hits the URL directly. **Not moot after CARD-0349** -- `data-pipeline-api`'s own routes use the exact same `?key=` pattern (`app.py`'s `_authorized(parts)`, checked against every route), so migrating off the Apps Script carried this design forward unchanged rather than fixing it.

**Not yet scoped -- needs an interview when picked up.** Real questions before this is buildable: does Cloudflare's own access logging (fronting `hikes.jctnet.com`) actually retain full query strings, and for how long -- is this a real, current exposure or a theoretical one? The conventional fix (an `Authorization: Bearer` header instead of a query param) works cleanly for POST routes but GPSLogger's own "custom URL" logging feature (the `/gps` route's real constraint, already documented in `gps-pipeline.md`) may only support templated GET URLs with no custom-header capability -- worth confirming before assuming a uniform fix applies to every route. Low urgency (this is a LAN-adjacent hobby pipeline, not a public multi-tenant service), but a real gap worth a deliberate decision rather than continuing to carry it forward unexamined.

**Related:** CARD-0347 (the pipeline review this item was originally found in), CARD-0349 (the migration that carried this pattern forward into the new gateway), `components/hiking-monitor/gps-pipeline.md` (GPSLogger's own custom-URL constraint, relevant to whether `/gps` can even take a header-based key).

---

**Phase 1 built and deployed, 2026-09-29 12:34 MST.** Answers to the card's open questions: (1) **real, current exposure** -- Caddy's access log on the M8 recorded the full `?key=` on every request (664 lines in 24h, persisted by the journald log driver); Cloudflare's own retention is not visible from here and remains unknown. (2) **GPSLogger does have a Headers field** (`gps-pipeline.md`'s table, currently "leave empty"), so `Authorization: Bearer` can work for every caller including `/gps`.

**Done and verified live:** gateway (`VERSION 2026-09-29.3`) accepts `Authorization: Bearer` alongside `?key=`, logs each legacy `?key=` use (rate-limited, per path, never the key); Caddy redacts `key=` from its access log (`"uri": "/data/version?key=REDACTED"` confirmed, and the single-file bind mount needed the `web` container recreated to pick up the new Caddyfile -- `mv` over a bind-mounted file leaves the container on the old inode); orchestrator callers (`generation.py`, `sheet_health.py`, `wildlife_life_list.py`, `fetch_hike_data.py`) and the gateway's own healthcheck moved to the header; four Node-RED nodes hot-deployed via the admin API (Prepare GPS lookup, Check GPS lookup response -- which must restore the auth header on retry because the http-request node overwrites `msg.headers` with the response's -- Compute derived fields + build POST, and the Sheet Health probe), then both flow tabs re-exported into the repo. After the Node-RED deploy, fresh readings landed (back-patio-temp-sensor 12:33:03) with no new legacy-auth log line for `/environmental-data` or `/health`.

**Not yet done -- Joseph's job:** switch GPSLogger (Headers field: `Authorization: Bearer <key>`, and drop `key=` from the URL template) and the Tasker observation POST to the header. The `/gps` and `/hiking-observations` routes, and the GPS-lookup retry path, are the untested-live ones (nothing exercised them yet). Until then `?key=` stays accepted. **Watch for:** the gateway's `legacy ?key=` log line for `/gps` or `/hiking-observations` after those two are switched -- `ssh jct@m8.local "docker logs --since 24h data-pipeline-api 2>&1 | grep legacy"`; once it stays quiet across a real hike, CARD-0371 (remove `?key=`) is safe. Key rotation is CARD-0370, deliberately separate. **Note:** the orchestrator's own webhook auth (`WEBHOOK_SECRET` via `?key=`, and the gateway's `_relay_log` call to `/webhook/pipeline-log`) still uses the query form -- Caddy's redaction covers it in the logs, but it was out of this card's scope.

**DONE 2026-09-29 13:10 MST.** Phone side finished and verified live. **GPSLogger:** URL changed to `https://hikes.jctnet.com/data/gps?...` with the key moved to a Headers entry -- after the change, three new points landed (13:06:57, 13:07:28, 13:08:01, all 200, `gps_track` 7643 -> 7646), none of the logged request URLs carried `key=`, and the gateway logged no legacy-auth line for `/gps`. (Along the way GPSLogger had been found already on the gateway URL but still sending `?key=` -- accepted, and logged as `legacy ?key= auth used on /gps` -- which is what the legacy log is for.) **Tasker:** "Flush Observation Queue" action 8 posts to `.../data/hiking-observations` with an `Authorization:Bearer` header; a phone-logged observation landed as a row (`POST` -> 200, no query string, no legacy line). **Docs updated:** `gps-pipeline.md` (current-state banner, Section 1 URL/Headers/`ts` format/test steps, Sections 2-4 marked RETIRED), `observations-pipeline.md` (action 8, Section 3a rewritten as live), and `tasker/Flush-Observation-Queue.tsk.xml` hand-edited to the new URL/headers with a `REPLACE_WITH_DATA_PIPELINE_KEY` placeholder (the old export had the retired Apps Script key in the URL). **Still open by design:** `?key=` remains accepted until CARD-0371 removes it (after a real hike keeps the legacy log quiet); key rotation is CARD-0370. **Reflection:** (1) a query-string secret leaks at every hop that logs URLs -- the app's own server log was clean here (it suppresses request lines) and the leak was the reverse proxy's, so check *each* hop, not just the service that owns the secret; (2) a compatibility window needs its own instrument -- the rate-limited legacy-auth log is what let "did the phone actually switch?" be answered from evidence rather than from the user's description; (3) a bind-mounted single file goes stale in the container after a `mv`-style replace -- recreate the container or write in place; (4) an HTTP client node that overwrites `msg.headers` with the response's headers silently drops a request auth header on any retry loop.

### CARD-0364 · [enhancement] [data-pipeline] Wildlife/scat re-processing: decide drop-vs-update instead of preserving the old silent-drop behavior

**Status:** Backlog

**Raised 2026-09-29 (general session, spun off CARD-0347 item 2 after scanning the board for CARD-0349 follow-on work).** The 2026-09-26 pipeline review found that `environmental-data.gs`'s wildlife-detection branch silently drops a re-processed detection instead of updating the existing row -- identity dedup on `(hike_file_stem, scientific_name)` means a legitimately-improved second pass (e.g. a better confidence score, a corrected species ID) never overwrites the first pass's row, it's just discarded as a "duplicate." **CARD-0349's `/wildlife-detection` route deliberately preserved this exact behavior** (same `UNIQUE` constraint, same `ON CONFLICT` semantics) rather than fixing it -- migrating the write path wasn't the moment to also change what "duplicate" means, per that card's own narrow scope.

**Not yet scoped -- needs an interview when picked up.** Real question: is a second pass on the same species ever actually *better* in practice (e.g. `wildlife_life_list.py`'s own re-processing passes), or does the first detection already carry everything needed and a second pass is always redundant? If updates are wanted, the fix is small now that this lives in Postgres -- `INSERT ... ON CONFLICT (hike_file_stem, scientific_name) DO UPDATE` instead of `DO NOTHING` -- but the actual desired semantics (always overwrite? only overwrite if the new confidence is higher? keep both and let a query pick the best?) needs deciding before writing that SQL, not assumed.

**Related:** CARD-0347 (the pipeline review this item was originally found in), CARD-0349 (built the `/wildlife-detection` route this would modify), CARD-0229/CARD-0235/CARD-0276 (the wildlife-detection sheet's own build history and dedup precedent this inherited).

---

### CARD-0363 · [enhancement] [photo-server] Immich update available: v3.2.4 (currently running v3.2.2) — auto-opened from photo-server — RESOLVED 2026-09-29 07:45 MST
**Status:** Done

Archived to `components/photo-server/card-archive.md` on 2026-09-29 (CARD-0193) — 2198B, over the 2000B size threshold.

---

### CARD-0362 · [enhancement] [data-pipeline] Operational hardening for the new TimescaleDB gateway -- backups, image pinning, update detection, heartbeat coverage — RESOLVED 2026-09-28
**Status:** Done

Archived to `core/data-pipeline/card-archive.md` on 2026-09-29 (CARD-0193) — 12080B, over the 2000B size threshold.

---

### CARD-0361 · [bug] [tos] `/kanban` shows a cryptic JSON-parse error instead of the real reason when `/kanban/data` fails, and the board had grown close to the size-risk tier
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 3566B, over the 2000B size threshold.

---

### CARD-0360 · [enhancement] [tos] Component-session startup never surfaces workstation-level operating docs, and no script verifies/updates the workstation's real state against them
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 5953B, over the 5000B size threshold.

---

### CARD-0359 · [bug] [data-pipeline] Apps Script POST occasionally answers with `doGet`'s "unknown action" fallback instead of the real write reply — seen from two different producers — RESOLVED 2026-09-29 (superseded, not fixed)
**Status:** Done

Archived to `core/data-pipeline/card-archive.md` on 2026-09-29 (CARD-0193) — 4080B, over the 2000B size threshold.

---

### CARD-0358 · [bug] [maintenance] Container image updates: matter-server: check failed (docker exec pip show timed out after 10 seconds) — auto-opened from jctsh-core

**Status:** Done

**Auto-opened 2026-09-28 03:35 UTC from jctsh-core's maintenance check.** Raw finding: `Container image updates: matter-server: check failed (Command '['docker', 'exec', 'matter-server', 'pip', 'show', 'python-matter-server']' timed out after 10 seconds)`.

**Already root-caused and fixed by CARD-0344's own concurrent build (2026-09-28), landed before this card was interviewed.** `core/maintenance/container_update_check.py`'s `_current_version()` used a flat 10s timeout for both `docker inspect` (label method) and `docker exec` (exec method, matter-server's own path); matter-server's `pip show` call hit it once under real I/O pressure (a re-run moments later took 4.4s) — the same class of intermittent slowness already documented on this host for CARD-0247's `docker logs` boot-time timeout. Fixed by bumping both to 20s, with the incident recorded inline as a comment.

**Done when:** met, no further work needed here — this card exists to close the loop on the auto-opened finding, not to duplicate CARD-0344's fix.

**Related:** CARD-0344 (extended the update checks to matter-server in the first place, and carries the actual fix), CARD-0247 (the `docker logs` timeout precedent this matches).

---

### CARD-0357 · [bug] [tos] [air-quality-monitor] [back-patio-temp-sensor] [front-porch-temp-sensor] [garage-radar] [hiking-monitor] [salt-sensor] Find and fix why ESPHome 2026.9.0 breaks the compile -- currently pinned 5 months behind at 2026.4.5
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 7277B, over the 5000B size threshold.

---

### CARD-0356 · [enhancement] [infrastructure] Container image updates: immich-redis: 9.1.2 available (running 9.1.0) — auto-opened from photo-server — RESOLVED 2026-09-29 00:16 MST
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-28 (CARD-0193) — 2366B, over the 2000B size threshold.

---

### CARD-0355 · [enhancement] [infrastructure] Container image updates: matter-server: 8.1.2 available (running 8.1.0) — auto-opened from jctsh-core
**Status:** Build

**Auto-generated 2026-09-28 03:36 UTC from jctsh-core's maintenance check.** Raw finding: Container image updates: matter-server: 8.1.2 available (running 8.1.0).

**Risk evaluated 2026-09-28 (general session), before touching anything.** `matter-server` runs on `:stable` (a floating tag, unlike `ring-mqtt`'s CARD-0344 pin) -- confirmed via GitHub Releases that `:stable` already resolves to exactly 8.1.2, nothing newer since. Changelogs for 8.1.1 and 8.1.2 show only small features/a bugfix/dependency bumps, no schema or breaking changes. `matter-server` and `homeassistant` are independent services in `core/homeassistant/docker-compose.yml` (no `depends_on`), so recreating just `matter-server` won't restart HA itself. **Real blast radius, not zero:** exactly one Matter config entry (`state: loaded`, source `zeroconf`), backing 3 real, currently-`on` kitchen lights (`light.kitchen_under_cabinet_1/2/3`) plus their identify/firmware-update/level/transition-time/power-on-behavior sibling entities -- confirmed live via HA's template API (`integration_entities("matter")`), not assumed. Two real caveats: the Pi was under genuine memory pressure at evaluation time (28Mi free, 551Mi/904Mi swap used, load 2.6 -- the same pattern that's already stalled other pulls, CARD-0295/CARD-0351), and `matter-server` has no `healthcheck:` defined in the compose file (unlike CARD-0356's redis case), so post-recreate verification has to be manual. `matter` also isn't on CARD-0247's `AUTO_RELOAD_DOMAINS`/`WATCH_ONLY_DOMAINS` allowlist -- if the config entry needs a reload after the container restarts, nothing does it automatically.

**Decision: schedule overnight rather than run immediately (Joseph, 2026-09-28).** `pi-image-pull.py ghcr.io/home-assistant-libs/python-matter-server:stable --recreate matter-server --schedule "2026-09-29 04:00:00"` -- scheduled and confirmed live (`pi-image-pull-python-matter-server-stable.timer`, active/waiting, `Trigger: Tue 2026-09-29 04:00:00 MST`). **Deliberately not the originally-proposed 01:45 slot** -- that would have collided with CARD-0351's review-upgrade job (02:00, includes a full Pi reboot once its own 10-min health wait completes, likely settling ~02:15-03:15). 04:00 sits comfortably after that reboot settles and well before the 06:01+ morning checks (`zram-writeback`/`apt-daily-upgrade`/`container-update-check-pi`) -- confirmed against the Pi's live `systemctl list-timers`, not the (possibly stale) doc table. Compose file at `/home/pi/docker-compose.yml` confirmed byte-identical to the repo's tracked copy before trusting an unattended recreate against it.

~~**Auto verify: 2026-09-29 04:15 MST**~~ -- superseded below; the scheduled job never fired.

**Scheduled job silently lost, found 2026-09-29 07:18 MST (general session, checking markers).** `pi-image-pull-python-matter-server-stable.timer` no longer existed on the Pi -- same failure class as CARD-0351's own lost job: a transient `systemd-run` unit lives in `/run`, wiped by any reboot landing before its fire time. **The mistake here was mine, not a repeat of the unknown-at-the-time gap CARD-0351 hit** -- I'd already diagnosed and fixed that exact class of loss for CARD-0351's job hours earlier, but didn't connect that CARD-0351's *own* rescheduled job reboots the Pi at ~02:18, squarely between when I scheduled this one (Mon 17:37) and its 04:00 fire time. Matter-server itself was unaffected (still cleanly on 8.1.0 the whole time, nothing broken by the miss) -- see CARD-0362 or a new card for the durable rule this produced (check every one-off schedule against *other already-scheduled one-off jobs*, not just the recurring-timer table, since a transient unit dies from any intervening reboot regardless of which job caused it).

**Run for real, 2026-09-29 07:24 MST (Joseph: "run it now"), attended.** Pi load had settled (1.3) since the overnight reboot. Compose file re-confirmed byte-identical to the repo copy. Baseline: all 3 lights `on`. `sudo pi-image-pull.py ... --recreate matter-server` (not scheduled this time) -- clean pull (6.6s, mostly "already exists" layers) and recreate, exit 0.

**Real regression hit and fixed live -- exactly the gap this card's own risk-evaluation flagged in advance.** All 3 lights went `unavailable` immediately after the recreate. `matter-server`'s own log showed a fully healthy reconnect (`Loaded 3 nodes from stored configuration`, all 3 nodes discovered on mDNS, subscriptions succeeded) -- the container and the Matter fabric itself were fine. The break was HA's side: the `matter` config entry reported `loaded` without ever resyncing its WebSocket connection to the recreated container, the identical "loaded but not actually synced" failure CARD-0240/CARD-0247 already documented for `smartthings`/`ring`/`samsungtv` -- now confirmed to apply to `matter` too, empirically, not just as a theoretical gap. **Fixed via `POST /api/config/config_entries/entry/01M2B0CVKBFGYYRQ9DT59RKJYB/reload`** (`{"require_restart":false}`) -- all 3 lights back to `on` within 5s. Worth a follow-on to add `matter` to CARD-0247's `AUTO_RELOAD_DOMAINS` so this doesn't need a human/Claude to notice and reload by hand next time (not built here -- that script change is CARD-0247's scope, not this card's).

**Version did NOT change -- a real, separate finding, not a failed update.** `docker inspect matter-server --format '{{.Image}}'` is byte-identical before and after (`sha256:170aa093...`); `pip show python-matter-server` still reads `8.1.0`. Confirmed via `gh api`: GitHub still lists `8.1.2` (2025-12-15) as the latest release, unchanged -- so upstream's `ghcr.io :stable` **Docker image tag has simply not been rebuilt for the 8.1.2 GitHub release**. This is upstream publishing lag, not anything wrong on this end -- the same "GitHub release exists but the container registry tag lags it" gap CARD-0344 already found for `immich_postgres` (no GitHub releases at all there; here releases exist but the Docker tag hasn't caught up). Nothing further to do here until upstream actually republishes `:stable` -- `container-update-check.py`'s next run will keep finding "8.1.2 available" until then, which is now a known, understood state, not a bug to chase.

**Done when:** matter-server's container recreated cleanly (met), the config-entry-reload gap this surfaced is either fixed or handed off (handed off to CARD-0247, above), and matter-server actually reports `8.1.2`. **Left in Build for that last item, not forced to Done on the accepted-limitation clause** -- this isn't a "root cause unknown" case (the cause is known: upstream hasn't republished `:stable`), it's a real, external, dated dependency, same shape as any other Auto Verify.

**Watch for:** `ghcr.io/home-assistant-libs/python-matter-server:stable` actually rebuilding for `8.1.2` (or whatever is newest by then) -- either `container-update-check.py`'s daily run reporting matter-server current, or a manual `docker inspect matter-server --format '{{.Image}}'` showing a digest different from `sha256:170aa093...`. No known date (depends entirely on upstream's own release/publish cadence), so checked every session per Session Start step 6, not on a schedule.

**Related:** `hosts/pi1` (compose file, matter-server service), CARD-0344 (built the check that surfaced this and the exec-based version-detection method it uses), CARD-0351 (the review-upgrade job this schedule was placed around), CARD-0247 (the entity-reload allowlist that doesn't yet cover `matter`), CARD-0356 (the sibling immich-redis bump this evaluation borrowed its verification discipline from).

---

### CARD-0354 · [enhancement] [infrastructure] Node-RED update(s) pending: node-red: 5.0.7 available (running 4.1.10); npm: … — auto-opened from jctsh-core — RESOLVED 2026-09-28 17:58 MST
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-28 (CARD-0193) — 4288B, over the 2000B size threshold.

---

### CARD-0353 · [bug] [pi1] Pi's persistent journal has been silently volatile-only since CARD-0246 -- a Raspberry Pi OS vendor drop-in was overriding it the whole time

**Status:** Build

**Raised 2026-09-27 20:20 MST (ops cluster session), from the Session Start Alert scan.** CARD-0328's Reflection (2026-09-26) and CARD-0350 (2026-09-27) had both independently noticed the Pi's journal only retaining a few hours/days of history despite `Storage=persistent` (CARD-0246, 2026-09-06) and no reboot in between, and both flagged it as "worth a look by the ops cluster" without ever turning it into its own card. Joseph: "open a card for it and do it."

**Root cause, found live on the Pi.** `/etc/systemd/journald.conf` correctly has `Storage=persistent` (CARD-0246's fix, untouched since). But Raspberry Pi OS itself ships `/usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf` containing `Storage=volatile` -- a vendor drop-in that sits in a later-merged config layer than the main `/etc/systemd/journald.conf` file, so it silently won. Confirmed directly: `/var/log/journal/9ea0857d55d841599ca90e00110e4f55/` (the correct machine-id directory, on the USB-backed `var-log.mount`, created back on 2026-09-05) has been **completely empty the entire time** -- zero `.journal` files -- while `/run/log/journal/<machine-id>/` (volatile tmpfs) held the real, actively-rotating live journal, capped at a tiny ~18MB (`RuntimeMaxUse` default), explaining the few-hours-to-days retention window both prior findings hit. **CARD-0246's fix never actually took effect, for the full ~3 weeks since it closed** -- the `journal-snapshot.service`/`.timer` workaround built alongside it (a `journalctl --cursor-file`-based plain-text tail into `/mnt/jctsh-logs/journal-snapshot.log`, unrelated to journald's own binary storage) is the only reason this wasn't obviously broken -- it's been quietly compensating the whole time.

**Fixed and verified live, 2026-09-27 20:17 MST.** Deployed `hosts/pi1/journald-persistent-storage.conf` (`[Journal]\nStorage=persistent`) to `/etc/systemd/journald.conf.d/50-persistent-storage.conf` -- a later-sorting filename than the vendor's `40-...`, so it wins on the merge without needing to mask the vendor file by identical name (tested and confirmed both approaches work identically; kept the clearer, non-masking one). Confirmed via `systemd-analyze cat-config systemd/journald.conf` that `Storage=persistent` is now the final effective value.

**One extra step needed, not just the config file:** `systemctl restart systemd-journald` alone did **not** pick up the fix -- the actual volatile→persistent handoff normally happens via `systemd-journal-flush.service`, a oneshot that only runs once, early in a real boot, and does nothing on a mid-session daemon restart. Had to run `sudo journalctl --flush` by hand to force it. After that: `/var/log/journal/9ea0857d55d841599ca90e00110e4f55/system.journal` exists (25MB, real content), the volatile `/run/log/journal/<machine-id>/` directory was removed by journald itself as part of the flush, and journald's own open file descriptors (`/proc/<pid>/fd`) point directly at the persistent files. A fresh `logger` test line landed there and was queryable. This means **the fix is confirmed working for the remainder of the current boot**, but whether it self-applies cleanly across a **real** reboot (where `systemd-journal-flush.service` runs naturally, no manual flush needed) is not yet observed.

**Auto verify: 2026-09-29 03:15 MST** -- covers both of this week's scheduled reboots (weekly Mon 2026-09-28 03:00, and CARD-0351's review-batch reboot Tue 2026-09-29 02:00): `ssh pi@pi1.local "sudo ls -la /var/log/journal/9ea0857d55d841599ca90e00110e4f55/"` should show real, non-empty `.journal` files with a `mtime` after the most recent reboot; `journalctl --list-boots` should show **more than one** boot entry (today it shows exactly one, itself a symptom of this bug); `uptime -s` cross-checked against the earliest boot `journalctl --list-boots` reports. If still empty/single-boot after a real reboot, the fix didn't survive and needs more investigation (possibly `var-log.mount` timing relative to `systemd-journal-flush.service` specifically, not just `systemd-journald.service`).

**Auto verify RESOLVED, passed -- 2026-09-29 11:41 MST.** Persistent journal survived both reboots: `/var/log/journal/9ea0857d.../` holds real `.journal` files (`system.journal` and `user-1000.journal` mtime 11:41 today, 25MB/33MB), and `journalctl --list-boots` shows 3 boots (-2 through 0, 2026-09-27 14:39 onward, boundaries at Mon 03:00 and Tue 02:17) versus exactly one before the fix. `uptime -s` = 2026-09-29 02:18:05, matching boot 0's first entry (02:17:30). `journal-snapshot.service`/`.timer` retirement (the "deliberately not done" item below) is now unblocked -- still not done.

**Deliberately not done here:** retiring `journal-snapshot.service`/`.timer` (CARD-0246's workaround) -- it's now redundant if this fix holds, but staying live in parallel until the Auto verify marker above actually confirms the real fix survives a reboot is the safer order (don't remove the working safety net before its replacement is proven, same discipline as CARD-0327/CARD-0272's staged rollouts). Revisit once the marker resolves. Also not done: tuning `SystemMaxUse`/retention size for the now-real persistent journal (defaults apply; no evidence yet that they're wrong for this filesystem).

**Related:** CARD-0246 (the original "volatile storage" bug this reopens -- its Done-when 1/2 held, but the persistent-storage half never actually worked), CARD-0328 (Reflection first flagged this), CARD-0350 (independently re-flagged it, same session that found the apt-index staleness bug), CARD-0159 (the `var-log.mount`/USB-drive setup this bind-mounts onto).

---

### CARD-0351 · [enhancement] [pi1] Pi OS/firmware maintenance: 280 routine + 15 review-category updates pending

**Status:** Build

**Auto-opened 2026-09-28 01:25 UTC from jctsh-core's maintenance check (CARD-0125/CARD-0128), PR #138 -- landed 2026-09-27 (Joseph: "let's do the PR" / "track for later").** Raw finding:
`Pi maintenance: 280 routine update(s) pending. 15 package(s) need review: containerd.io, docker-buildx-plugin, docker-ce, docker-ce-cli, docker-ce-rootless-extras, docker-compose-plugin, libc6, libc6-dev, linux-base-rpi-2712, linux-base-rpi-v8, linux-headers-rpi-2712, linux-headers-rpi-v8, linux-image-rpi-2712, linux-image-rpi-v8, linux-libc-dev`

**Landed, not worked** -- tracked for a later session, no packages touched by this card's creation.

**How this gets applied, per CARD-0125's own precedent (2026-07-31):** nothing in `pi-maintenance-check.py` ever installs anything -- both counts are notify-only. The routine 264/280-shaped batch has historically been applied in one plain `apt upgrade` pass, since none of it touches Docker or the kernel. The 15 review-category packages (Docker itself + kernel/libc6) are a separate, deliberate decision: installing them restarts the Docker daemon (touching `homeassistant`, the one container on the Pi Robin depends on directly) and needs a reboot to actually take effect -- same two-part shape CARD-0125 hit applying its own 264/7-package split.

**Routine list added, 2026-09-27 18:42 MST (Joseph: "include in 351 the routine updates that need no explicit decision"), with a caveat added alongside it (Joseph: "did we evaluate the risk of the other items on 351?").** Fetched live from the Pi (`apt list --upgradable` minus the review-category filter): 280 packages, listed below.

**Caveat, stated plainly rather than overclaiming the section title above:** "routine" is not a risk evaluation -- neither this list nor the 15 review-category packages above have had an actual per-package risk check (no release notes read, unlike CARD-0295's HA check). It is purely `pi-maintenance-check.py`'s `REVIEW_PATTERNS` filter (a fixed substring match on `docker`/`containerd`/`linux-`/`libc6`) sorting everything that doesn't match into this bucket. That filter is narrow enough to miss real candidates for individual attention sitting in this "routine" list: **`tailscale`** (the remote-access mechanism this whole setup depends on), **`openssl`/`openssl-provider-legacy`** (security-critical crypto library), **`wpasupplicant`/`dhcpcd-base`/`dnsmasq-base`** (Wi-Fi auth and DHCP), **`samba-libs`/`nginx`** (network-facing services), and **`firmware-atheros`/`firmware-brcm80211`/`firmware-libertas`/`firmware-mediatek`/`firmware-realtek`** (Wi-Fi/Bluetooth radio firmware). The remainder is overwhelmingly Raspberry Pi Desktop packages (Chromium, Firefox, GUI panels/themes, printer drivers, GStreamer, `rpd-*`/`wf-*`/`lpplug-*`) -- genuinely low-stakes on a headless server, but that's this session's own read, not a per-package check either. **Corrected -- this Pi runs headless (Joseph, confirmed directly).** The GUI/browser package volume above just means the OS image is the Desktop variant with the GUI stack installed but unused, not that anything is actually running a desktop session.

**Full routine list (280):** agnostics, at-spi2-common, base-files, bash, bind9-dnsutils, bind9-host, bind9-libs, bluez, bsdextrautils, bsdutils, bubblewrap, busybox, chromium, chromium-common, chromium-l10n, chromium-sandbox, curl, dhcpcd-base, dirmngr, dnsmasq-base, e2fsprogs, eject, fdisk, ffmpeg, firefox, firmware-atheros, firmware-brcm80211, firmware-libertas, firmware-mediatek, firmware-realtek, ghostscript, gir1.2-atk-1.0, gir1.2-glib-2.0, gnupg-utils, gpg, gpg-agent, gpgconf, gpgsm, gpgv, gpg-wks-client, gstreamer1.0-alsa, gstreamer1.0-gl, gstreamer1.0-plugins-bad, gstreamer1.0-plugins-base, gstreamer1.0-x, gui-runcmd, gzip, hplip, hplip-data, imagemagick-7-common, labwc, libaom3, libasound2-data, libasound2t64, libatk1.0-0t64, libatk-bridge2.0-0t64, libatopology2t64, libatspi2.0-0t64, libaudit1, libaudit-common, libavcodec61, libavdevice61, libavfilter10, libavformat61, libavutil59, libblkid1, libbluetooth3, libcamera0.7, libcamera-ipa, libcamera-tools, libcamera-v4l2, libcap2, libcap2-bin, libc-bin, libc-dev-bin, libc-l10n, libcom-err2, libcurl3t64-gnutls, libcurl4t64, libde265-0, libdrm2, libdrm-amdgpu1, libdrm-common, libdrm-nouveau2, libdrm-radeon1, libegl-mesa0, libevent-2.1-7t64, libevent-core-2.1-7t64, libexpat1, libexpat1-dev, libext2fs2t64, libfdisk1, libfluidsynth3, libgbm1, libgd3, libgl1-mesa-dri, libglib2.0-0t64, libglib2.0-bin, libglib2.0-data, libglx-mesa0, libgs10, libgs10-common, libgs-common, libgstreamer-gl1.0-0, libgstreamer-plugins-bad1.0-0, libgstreamer-plugins-base1.0-0, libgtk-layer-shell0, libheif1, libheif-plugin-dav1d, libheif-plugin-libde265, libhpmud0, libjbig2dec0, liblastlog2-2, libldb2, libmagickcore-7.q16-10, libmagickcore-7.q16-10-extra, libmagickwand-7.q16-10, libmbedcrypto16, libmount1, libnfs14, libnss3, libntfs-3g89t64, libpcre2-16-0, libpcre2-8-0, libperl5.40, libpisp1, libpisp-common, libpostproc58, libpython3.13, libpython3.13-dev, libpython3.13-minimal, libpython3.13-stdlib, librabbitmq4, libraw23t64, librpicam-app1, libsane-hpaio, libsdl2-image-2.0-0, libsmartcols1, libsmbclient0, libsqlite3-0, libsrt1.5-gnutls, libss2, libssh2-1t64, libssh-4, libssl3t64, libswresample5, libswscale8, libtalloc2, libtdb1, libtevent0t64, libtiff6, libudisks2-0, libuuid1, libwbclient0, libwebsockets19t64, libxfont2, libxkbcommon0, libxkbcommon-x11-0, libxkbregistry0, locales, login, logsave, lpplug-batt, lpplug-bluetooth, lpplug-clock, lpplug-cpu, lpplug-cputemp, lpplug-ejecter, lpplug-gpu, lpplug-magnifier, lpplug-menu, lpplug-netman, lpplug-power, lpplug-updater, lpplug-volumepulse, lxpanel-pi, merp, mesa-libgallium, mesa-va-drivers, mesa-vdpau-drivers, mesa-vulkan-drivers, mkvtoolnix, mount, nginx, nginx-common, nodejs, ntfs-3g, openssl, openssl-provider-legacy, perl, perl-base, perl-modules-5.40, piclone, pi-greeter, pi-package, pi-package-data, pi-package-session, pipanel, pishutdown, piwiz, pixtrix-icons, pixtrix-theme, pplug-ejecter-data, pplug-netman-schema, pplug-power-data, pplug-updater-data, printer-driver-hpcups, printer-driver-postscript-hp, python3.13, python3.13-dev, python3.13-minimal, python3.13-tk, python3.13-venv, python3-flask, python3-libcamera, python3-picamera2, raindrop, raspberrypi-sys-mods, raspi-config, raspi-config-core, raspi-firmware, rasputin, rc-gui, rfkill, rpcc, rpd-applications, rpd-common, rpd-developer, rpd-graphics, rpd-plym-splash, rpd-preferences, rpd-theme, rpd-utilities, rpd-wayland-core, rpd-wayland-extras, rpd-x-core, rpd-x-extras, rpicam-apps, rpicam-apps-core, rpicam-apps-encoder, rpicam-apps-lite, rpicam-apps-opencv-postprocess, rpicam-apps-preview, rpi-connect, rpi-eeprom, rpi-gui-nop, rpi-imager, rpi-loop-utils, rpinters, rpi-swap, rp-prefapps, samba-libs, sudopwd, tailscale, tzdata, udisks2, unzip, userconf-pi, util-linux, uuid-dev, wayvnc, wf-panel-pi, wfplug-batt, wfplug-bluetooth, wfplug-clock, wfplug-connect, wfplug-cpu, wfplug-cputemp, wfplug-ejecter, wfplug-gpu, wfplug-menu, wfplug-netman, wfplug-power, wfplug-squeek, wfplug-updater, wfplug-volumepulse, wpasupplicant, xserver-common, xserver-xorg-core, zip
**Handling started 2026-09-27 19:05 MST (Joseph: "yes, pick the best time" -- shifted from "track for later" to "handle now"), split in two per the card's own precedent:**

**Routine batch (280 + the 6 flagged network/firmware packages) -- IN PROGRESS, run in the foreground.** Held the 15 review-category packages first (`apt-mark hold`), confirmed held, then `apt-get upgrade -y` for everything else. Real memory pressure observed from the start (37Mi free RAM, 658Mi/904Mi swap before starting -- the same pattern CARD-0295 found causing its stall), but this run shows genuine sustained progress (`dpkg.log` line count climbing steadily, load average easing from a 6.6 peak back down), unlike that stall which showed zero progress for 40 minutes. Being watched rather than assumed clean.

**Review batch (the 15 held: Docker/containerd/kernel/libc6) -- SCHEDULED, not yet run.** Went through two design corrections, both from Joseph catching a real problem before it happened:
1. **First attempt: scheduled for 02:00 MST, one hour ahead of the Pi's own weekly `scheduled-reboot.timer` (Mon 03:00), intending that reboot to pick up the new kernel** -- rejected (Joseph: "is that enough time for all 6?") on real precedent: CARD-0295's single container recreate alone took ~77 minutes under this same memory pressure; six Docker-related packages plus a daemon restart could easily exceed a 1-hour window.
2. **Second attempt: script redesigned to wait for `homeassistant` to report healthy post-upgrade, then self-reboot, instead of racing a fixed deadline** -- still incomplete (Joseph: "it's still racing against the scheduled reboot?"). Correct catch: removing the internal deadline from *my* script did nothing about the **separate, independently-scheduled** weekly reboot, which fires at 03:00 regardless of what my job is doing. **Real mitigating finding, checked live:** `/sbin/reboot` on this host resolves to `systemctl reboot`, which respects systemd shutdown inhibitors -- and `apt`/`dpkg` already hold a `block`-mode shutdown inhibitor automatically while running (confirmed live: the routine batch's own `apt-get` process was shown holding exactly this lock via `systemd-inhibit --list`). So the actual dpkg-transaction phase was already protected from being interrupted by the weekly reboot; the real remaining gap was narrower than first framed -- only the post-install, pre-self-reboot health-wait poll (no inhibitor held then).
3. **Final decision (Joseph: "or schedule the updates for tomorrow night"): moved to Tue 2026-09-29 02:00 MST instead** -- simpler and more robust than relying on inhibitor semantics for the narrow remaining gap. 23 hours clear of tonight's weekly reboot, 6 days clear of next week's. Deployed as a one-off (not repo-tracked) transient systemd unit, `jctsh-review-upgrade-once.timer`/`.service`, matching `pi-image-pull.py`'s `--schedule` convention (systemd-run, self-removing). The script itself: unholds the 15, `apt-get install --only-upgrade` targeting exactly those (not a blanket upgrade, so nothing new that appears between now and then gets swept in unintentionally), waits up to 10 min for `homeassistant` to report healthy, logs to the dashboard throughout (matching `pi-image-pull.py`'s log-line convention), then reboots itself regardless of the wait outcome (logging an Alert first if health wasn't confirmed).
**Auto verify: 2026-09-29 03:00 MST** -- the scheduled review-batch job (`jctsh-review-upgrade-once.service`, fires 02:00) plus its own health-wait and self-reboot should be complete by then. Check: `ssh pi@pi1.local "sudo journalctl -u jctsh-review-upgrade-once.service --no-pager -o cat"` for the full run (should end with the "rebooting now" log line, no Alert); `uname -r` should read `6.18.50` (not `6.18.34`); `apt-mark showhold` should be empty; `docker version --format '{{.Server.Version}}'` should read `29.8.1`; `docker inspect homeassistant --format '{{.State.Health.Status}}'` should read `healthy`; `uptime -s` should show a boot time around 02:xx on 2026-09-29, confirming the reboot actually happened rather than the job silently no-op'ing. If the Alert path fired instead (HA didn't confirm healthy within 10min), check HA manually rather than trusting the reboot alone as sufficient.

**Auto verify RESOLVED, passed -- 2026-09-29 11:41 MST.** Job log ends `package upgrade complete (889s)` -> `homeassistant confirmed healthy after 120s, rebooting now`, no Alert. `uname -r` = `6.18.50+rpt-rpi-v8`; `apt-mark showhold` empty; Docker server `29.8.1`; `homeassistant` health `healthy`; `uptime -s` = 2026-09-29 02:18:05 (reboot really happened).
**Routine batch COMPLETE and verified live, 2026-09-27 19:29 MST.** Ran ~40 minutes (18:48-19:19ish), exit code 0. Real memory pressure throughout -- swap dropped to 8.4Mi free at its worst point (19:07), the same pattern that stalled CARD-0295's HA pull, but this run kept making real, observable progress the whole time (`dpkg.log` line count climbing steadily: 25 -> 793 -> 1184 -> 2375) rather than going silent, and swap recovered to 204Mi free once the batch finished.

**Verified clean:** `dpkg --audit` empty (nothing left half-configured); `apt-mark showhold` still exactly the 15 held packages, untouched; `mosquitto`/`nodered`/`jctsh-logging`/`docker` all active, `homeassistant` running and healthy; load back down from its 9.65 peak to 5.4.

**Honest gap: 9 packages from the original 280 are still upgradable, not silently applied.** `labwc`, `libc-dev-bin`, `rpd-common`, `rpd-preferences`, `rpd-utilities`, `rpd-wayland-core`, `rpd-wayland-extras`, `rpi-swap`, `wayvnc`. **Not a failure** -- `apt-get upgrade` (used deliberately, not `full-upgrade`) skips any package whose version bump would need to install/remove other packages as a side effect (several of these Desktop-compositor packages have large version jumps, e.g. `rpd-common` 1.18 -> 1.31, that plausibly require exactly that). Same risk class as the rest of the routine list -- unused Raspberry Pi Desktop packages on a headless box -- so left as-is rather than escalating to `full-upgrade` unprompted; that's a separate decision if ever wanted.

**Decided, 2026-09-27 19:32 MST (Joseph: "skip them") -- the 9 leftover Desktop packages stay unapplied.** No `full-upgrade` will be run for `labwc`, `libc-dev-bin`, `rpd-common`, `rpd-preferences`, `rpd-utilities`, `rpd-wayland-core`, `rpd-wayland-extras`, `rpi-swap`, `wayvnc` -- explicit decision, not a default. They'll keep showing as upgradable in `apt list --upgradable`/CARD-0350's dashboard indefinitely unless revisited.

**Real gap found and fixed, 2026-09-28 17:36 MST (general session).** The review batch's own scheduling job -- the `jctsh-review-upgrade-once` transient systemd unit described above -- had silently vanished. It was created 2026-09-27 evening, entirely as an ad hoc `systemd-run` command with no backing file on disk; today's regular Monday 03:00 scheduled reboot wiped `/run` (where transient units live) before the job's Tuesday 02:00 fire time, and `systemctl status jctsh-review-upgrade-once.timer` came back "could not be found." Tomorrow's 02:00 slot would simply not have fired, with nothing surfacing the miss until CARD-0353's own Auto Verify found an unexplained absence. **Fixed:** the job's logic is now a real, version-controlled script, `core/maintenance/pi-review-upgrade-once.py` (same design as before -- unhold the 15, `--only-upgrade` exactly those, wait up to 10 min for `homeassistant` healthy, reboot regardless with an Alert if health wasn't confirmed), deployed to `/usr/local/bin/`, and rescheduled for the same **2026-09-29 02:00 MST** slot. Confirmed live: `jctsh-review-upgrade-once.timer` active/waiting, `Trigger: Tue 2026-09-29 02:00:00 MST`. Still a transient timer wrapper -- only safe because no further reboot is due before it fires -- but the persisted script means a repeat of today's exact loss can't happen silently next time; at worst the timer itself needs re-scheduling from a script that still exists.
**Done when:** not yet scoped -- interview at Planning to decide whether routine and review are handled in the same pass or separately, and to schedule the reboot the review packages will need.

**Related:** CARD-0125 (Pi OS/firmware check, established this exact routine-vs-review application pattern), CARD-0350 (this session's fix to the check's own apt-index-refresh reliability, which is what let this finding be accurate), CARD-0128 (the intake pipeline).

---

### CARD-0350 · [bug] [pi1] Pi OS/firmware maintenance check may have gone stale -- apt index unrefreshed 15 days, check's own state file unchanged since 07-31
**Status:** Done

Archived to `hosts/pi1/card-archive.md` on 2026-09-27 (CARD-0193) — 8625B, over the 5000B size threshold.

---

### CARD-0349 · [idea] [data-pipeline] Evaluate a time-series database to replace or front Google Sheets as the Environmental Data store — RESOLVED 2026-09-29
**Status:** Done

Archived to `core/data-pipeline/card-archive.md` on 2026-09-29 (CARD-0193) — 39114B, over the 2000B size threshold.

---

### CARD-0348 · [enhancement] [hike-izer-orchestrator] Retire narrative generation; unify step 1/step 2 into one idempotent generation pass
**Status:** Done

Archived to `components/hike-izer-orchestrator/card-archive.md` on 2026-09-27 (CARD-0193) — 29656B, over the 5000B size threshold.

---

### CARD-0347 · [enhancement] [data-pipeline] Address findings from the 2026-09-26 pipeline review (locking, duplicate re-run overwrite, scan costs, timestamp comparison, storage single point of failure, doc drift) — RESOLVED 2026-09-29
**Status:** Done

Archived to `core/data-pipeline/card-archive.md` on 2026-09-29 (CARD-0193) — 4978B, over the 2000B size threshold.

---

### CARD-0346 · [enhancement] [hiking-monitor] [air-quality-monitor] Hike readiness -- both devices ready for the next hike, all known problems addressed

**Status:** Build

**Priority:** High -- it tracks whether both devices are ready for the next hike, with an unmet condition as of 2026-09-28; expect it to drop once that hike is done. (set 2026-09-29 15:41 MST, triage)

**Raised 2026-09-26 (Joseph: "goal: the hiking monitor and aqm are ready to go (all known problems addressed) for the next hike").** A tracking card: what went wrong on the 9/26 hike, what is fixed and verified, and what still has to be true before the next one.

**Known problems and status (2026-09-26 ~14:45):**
1. **AQM recorded nothing (cold boot, no clock).** FIXED and verified on the bench, three runs (CARD-0343: readings kept tagged by uptime, resolved to exact times at the dock replay, waits up to 5 min for SNTP). The 9/26 hike itself was one continuous boot, so this firmware would have saved it.
2. **AQM re-replayed old runs / log never cleared.** FIXED and verified (CARD-0345: cleared at the next run's Intent-ON, an unreplayed log kept). Two earlier runs where it didn't clear remain unexplained; diagnostic events stay in.
3. **AQM docs.** `operations.md` rewritten for the new behavior (the Clock section, the dock-and-wait-5-minutes step, verify in the Sheet).
4. **Sheet write path / outage.** FIXED (lock, serial queue that holds readings through an outage, tail-first export, health probe two-strike alert, runbook). Root cause of the 9/25 outage "unexplained, mitigated". Pipeline healthy as of 14:20: no alerts since noon, M8 orchestrator + daily-refresh timer up.
5. **hiking-monitor recorded nothing on the 9/26 hike (empty log at dock; no `Replaying` line at 09:15).** **NOT explained, NOT fixed.** Bench runs log and replay fine (10:44: 7 lines, incl. a one-off blank-reason reboot 25 s after switch-ON). Diagnostic build flashed (`boot_state` event, `Hike log at connect` line) so the next failure says what happened. This is the blocker.
6. **hiking-monitor docked hang (10:58-11:57, ports dead, MQTT down, ping alive).** Unexplained; needed a physical reset. Stable 2 h since (through 14:09). Possibly related to 5 -- both fit a stalled or resetting app loop. History: CARD-0217 (270-reboot brownout storm), CARD-0259 (v2 rebuild) are the same failure family.
7. **hiking-monitor docs.** `operations.md` updated (log kept after upload, Replay Hike Log, `Hike log at connect`, verify in the Sheet).

**Needed before the hike -- rehearsal, scheduled Monday 2026-09-28 or Tuesday 2026-09-29 (Joseph, 2026-09-26):** a real walk with **both devices in the pack, moving**, ~45-60 min (motion matters: an intermittent battery connector or brownout under vibration would not show on the bench), started exactly as on hike day (AQM: docked and connected, then unplug + Intent ON, Power Switch untouched; hiking-monitor: switch ON), then dock both and verify from the Sheet: expected ~25-30 rows per device, no gaps. Pass = both devices deliver. If the hiking-monitor delivers nothing again, the diagnostic events (reset events, `boot_state`) and `Hike log at connect` say why and this card stays open.

**Hike-day checklist (also in each device's operations guide):** both docked overnight, AQM `Air quality monitor online` seen and Power Switch left ON; both batteries >= 4.0 V; hiking-monitor switch ON at the trailhead, AQM Intent ON; after the hike dock both (AQM Intent OFF), leave the AQM docked >= 5 min, confirm rows in the Sheet for both before unplugging or resetting anything.

**Rehearsal run, 2026-09-28 06:57-08:50 MST -- mixed result, item 5 recurred, one new AQM bug found and worked around live.**

- **hiking-monitor: item 5 recurred, worse than 9/26.** Field mode ran ~06:59-08:31 (~92 min, should log ~45 readings at 2-min intervals). At dock (08:32:03): `Hike log at connect: 0 line(s), replayed flag clear -- nothing to replay`. Device then cycled disconnect/reconnect three times (08:32:41, 08:33:46, 08:37:27 ending in an unclean `Disconnected (LWT)`) before settling. **A real power/connector fault was found and physically fixed by Joseph during this window** -- caught in the log as an impossible `Replay deferred - battery 0.28V below 3.4V cutoff` alert at 08:34:07 (before the fix; a healthy ~4V reading followed once charging resumed, per Joseph). The final reconnect (08:37:51) found exactly 1 buffered reading, itself skipped as `clock_invalid`. **Net: essentially zero rehearsal data captured.** Consistent with the fault being live through the whole walk (matching item 6's "docked hang" failure family), not just at dock -- so today's run doesn't yet prove the fix actually restores data capture, only that the device reconnects cleanly and holds a stable connection now (confirmed via `/status.json`, stable Online/Connected through 08:42:32+, no further disconnects).
- **air-quality-monitor: item 1's clock fix held (no clock loss this run) -- but a new, distinct bug silently blocked upload for ~2 hours.** Intent ON ~07:03, docked ~08:00. Device reconnected cleanly and stayed connected (MQTT up continuously from 08:01:02), battery healthy (4.06-4.13V) -- all three WiFi-gate conditions met -- but never logged a `Replaying` line through 08:47 (three heartbeats, ~47 min). Root cause, found by reading `attempt_aqm_replay` in `air-quality-monitor.yaml` directly: the script's outer guard is `if (aqm_log_has_data() && !id(aqm_log_replayed))` -- when `aqm_log_replayed` is already `true` (stuck from a prior session) the whole block silently no-ops, every 2-min recheck, forever, with **zero log output either way** -- indistinguishable from "buffer genuinely empty" without checking the code. **Diagnosed and worked around live** via CARD-0226's documented manual-replay mechanism (`mosquitto_pub` to `jctsh/components/air-quality-monitor/command/replay`, which force-clears the flag and re-invokes the script) -- immediately found **30 buffered readings**, replayed them (08:50:48), and Joseph confirmed all 30 rows landed in the Sheet. **Why the flag got stuck in the first place is not yet identified** -- worth its own investigation if it recurs; this fix (the manual command) is a recovery, not a root-cause fix. Same "the device can go silent instead of erroring" shape already known from CARD-0217/CARD-0226's `reset_reason_text` fragility -- worth treating `aqm_log_replayed` with the same suspicion.
- **AQM's `reset_reason_text` also cried wolf twice today (03:18:54, 08:01:00), both `reset reason: power-on event`.** Checked against the device's own uptime counter, which climbed continuously straight through both (e.g. 41h19m at 07:02 -> 42h34m at 08:17, exactly matching elapsed wall-clock time) -- a real power-on reset would zero that counter. **Neither was a real reboot**; both were misreported on ordinary MQTT reconnects. Same fragility CARD-0217 already documented for this sensor on hiking-monitor ("only safely readable once loop() is running"), now confirmed present on AQM's firmware too. No hardware action taken on this basis, correctly -- flagged here so a future session doesn't chase a phantom power fault the way this session almost did before checking uptime.
- **AQM's stuck-flag bug: root cause found, fix built/compiled/OTA-flashed and confirmed live, 2026-09-28 09:06 MST -- not yet verified against a real recurrence.** Root cause: `intent_switch`'s `on_press` trigger is the *only* thing that cleared `aqm_log_replayed`/the old log when a new field run starts -- and it apparently didn't fire for today's OFF->ON transition (the periodic interval's own independent level-read correctly disabled MQTT right on schedule at ~07:03, proving the GPIO itself read ON, but no `intent_on` event was ever logged, which only fires from inside `on_press`). With the flag stuck `true` from a prior session, `attempt_aqm_replay`'s own guard silently no-op'd every 2-min recheck for the rest of the walk -- zero log output either way, indistinguishable from "buffer genuinely empty" without reading the code. **Fix (`components/air-quality-monitor/air-quality-monitor.yaml`):** new global `intent_last_polled_state`, seeded from the switch's real state at boot; the periodic interval (which already reads the switch's level every 2 min for the WiFi gate) now also detects an OFF->ON edge itself and runs the same idempotent log-clear logic `on_press` runs -- a backstop, not a replacement, bounded to at most a 2-min delay if `on_press` fires normally. Compiled clean on the pinned ESPHome 2026.4.5 (`config_hash=0x31a10faa`), synced into `C:\esphome\air-quality-monitor\` (was stale, ~9/16 vs. today), OTA-flashed, reconnected cleanly (`reset reason: Reboot request from esphome.ota`, MQTT up, ping healthy). **Deployed but unverified** -- the backstop itself only proves out the next time Intent goes OFF->ON in the field and either `on_press` fires normally (no visible difference) or misses again (an `intent_on_poll_backstop` event would appear within 2 min instead of silence). `workstation-verify.ps1` run first per CARD-0360, all checks passed.

**Parked updates:** Home Assistant (CARD-0295) and Immich (CARD-0274) were deferred by Joseph until after the **9/26** hike, which has now happened -- so they are due; sequence them one at a time and **before** the rehearsal (a Pi/HA restart mid-rehearsal would muddy it) or after the real hike, Joseph's call. Cloudflared (CARD-0257) stays on hold.

**Done when:** a real hike (or the walking rehearsal, if Joseph accepts it as the proof) delivers both devices' readings to the Sheet with correct timestamps and no gaps; if item 5 recurs, its cause is identified from the diagnostic events. Then close this card, CARD-0012, and CARD-0226's Watch for.

**Not yet met, 2026-09-28.** AQM delivered (30 rows confirmed in the Sheet, after the manual-replay workaround above) but hiking-monitor did not -- item 5 recurred with near-total data loss, and while a physical power/connector fault was found and fixed mid-session, today's run can't confirm the fix actually restores data capture (almost nothing was logged during the walk to test it against). **Next step, per this session's discussion with Joseph:** a short follow-up walk (10-15 min is enough) now that hiking-monitor is reconnecting cleanly, specifically to confirm real field-mode logging survives with the connector reseated -- not a full rehearsal repeat.

**Follow-up test walk, 2026-09-28 ~13:00-13:07 MST -- hiking-monitor now logs real data with the connector reseated, but hit the exact same stuck-flag bug just fixed on AQM; ported the same fix.** Short walk, both devices. hiking-monitor woke from deep sleep for the walk (confirming the connector fix holds under motion) and logged real readings -- but at dock, both connects showed `Hike log at connect: 12/14 line(s), replayed flag SET -- not replaying`, the identical shape to AQM's stuck `aqm_log_replayed`. Recovered live via the documented `button.hiking_monitor_replay_hike_log` HA button (HA REST API, `POST /api/services/button/press`) -- `Replaying 14 hike readings...` -> `Hike log replay complete.`, with 1 `clock_invalid` skip and 2 `nan_sensor` skips visible among the replayed diagnostic events (cold-start sensor warm-up, not itself alarming).

**Root cause, ported fix, compiled, OTA-flashed, confirmed live -- same day, same shape as AQM's fix above.** `slide_switch`'s `on_state` "else" (switch-ON) handler is hiking-monitor's own equivalent of AQM's `on_press` -- the only thing that clears `hike_log_replayed`/the old log when a new hike starts -- and it apparently didn't fire for this walk either, even though the device clearly booted into field mode and logged real data. Ported AQM's exact fix into `components/hiking-monitor/hiking-monitor.yaml`: new global `slide_switch_last_polled_state`, seeded at boot (priority -100.0 block, after globals/switch state are known), and the same OFF->ON edge backstop added to the existing 2-min interval (which already fires "essentially immediately" after boot on this device, so the boot-with-switch-already-on case is covered too, not just a mid-runtime flip). Compiled clean on the pinned ESPHome 2026.4.5 (`config_hash=0x057fbf97`), synced into `C:\esphome\hiking-monitor\` (also stale), OTA-flashed, reconnected cleanly (ping healthy, `/status.json` Connected). `workstation-verify.ps1` already run earlier this session, not re-run for this second flash (no workstation state changed in between). **Deployed but unverified on both devices** -- same caveat as AQM: only the next real switch-ON transition proves whether the primary handler fires normally or the backstop has to catch it (an `intent_on_poll_backstop`-equivalent event -- this device logs it via the same `boot_cleared_lines`/log-clear path, no separate named event -- would be the tell).

**Two independent same-day confirmations of one bug class, on two sibling devices, is enough to act on without waiting for a third (per `JCTsh-Operating-System.md`'s Engineering Discipline -- normally "two isn't yet a pattern," but here the second instance is a literal repeat of the same mechanism on the device the pattern was ported *from*, not a novel case needing its own evidence-gathering).**

**Real test hike, 2026-09-30 ~15:17-15:30 MST, in the middle of CARD-0376's hardware saga -- AQM delivered, hiking-monitor's data was lost.** Both devices carried on a real (if improvised) test walk while hiking-monitor's replacement ESP32 was still exhibiting intermittent-connection symptoms (see CARD-0376). **AQM: success.** After a separate brownout-induced hang (below) was cleared with a forced Power Switch cycle, it reconnected and `Replaying 10 buffered readings...` -> `Buffered-data replay complete.` -- 10 readings matches the walk length, and the `intent_on_poll_backstop` backstop fired again, harmlessly, confirming CARD-0346's own fix is genuinely live and working on real hike data now, not just in bench tests. **hiking-monitor: data lost.** Joseph confirmed directly against the Environmental Data sheet -- zero hiking-monitor rows for the hike window. The on-device log showed the same `hike_log_replayed` stuck-`SET` shape this card's backstop was built for, but a `Replaying 471 hike readings...` attempt (mostly accumulated diagnostic noise, not hike data) was interrupted by another reboot mid-stream given the day's instability, and whatever data existed did not survive to the Sheet. Full narrative on CARD-0376, since it's entangled with that card's hardware investigation, not a new firmware bug on this card.

**New finding, same session: AQM suffered a real, genuine brownout while docked and charging -- worth investigating on its own, separate from CARD-0376's hiking-monitor hardware issues.** Three consecutive `reset reason: brownout` events at 14:00-14:02 MST (a real ESP-IDF brownout-detector trip, not the `power-on event` misreport CARD-0346 already debunked elsewhere -- this device's reset-reason text is not always unreliable, just sometimes), then AQM went fully dark: unreachable by ping, no RGB LED activity, silent on MQTT for over an hour despite the Power Switch reading ON and the battery independently confirmed healthy (4.13V at the JST connector) -- the ESP32 itself was hung, not unpowered (other board-level LEDs, e.g. the SEN55 adapter's own indicator, stayed lit throughout). Recovered only by cycling the Power Switch (`operations.md`'s own documented forced-restart procedure). **Being docked does not protect against this on this specific design** -- corrected understanding from `components/air-quality-monitor/wiring.md` (not this card's prior framing): LiPo `BAT+`, TP4056's own `BAT+` (charging pin), and the Pololu regulator's `VIN` are all tied to one shared node through the inline switch, so USB power genuinely does participate in powering the ESP32 while docked, not merely trickle-charging an isolated battery. A brownout while docked is therefore most likely explained by a current spike (WiFi association, SEN55 warm-up) momentarily exceeding what TP4056's current-limited charge output can supply on top of the battery, sagging the shared node anyway -- consistent with CARD-0198's own prior finding that this regulator's transient response is marginal even at healthy voltage. **Not yet investigated:** TP4056's actual programmed charge-current limit on this build (unknown as of this writing); whether this is a first occurrence or has happened unnoticed before.

**Related:** CARD-0226, CARD-0343, CARD-0345, CARD-0012, CARD-0259, CARD-0217, CARD-0198, CARD-0376 (today's hiking-monitor hardware saga this test hike happened during), `components/air-quality-monitor/operations.md`, `components/air-quality-monitor/wiring.md`, `components/hiking-monitor/operations.md`.

---

### CARD-0345 · [bug] [air-quality-monitor] AQM buffer log is not cleared at the start of a new run -- old runs are re-replayed on every dock
**Status:** Done

Archived to `components/air-quality-monitor/card-archive.md` on 2026-09-27 (CARD-0193) — 5741B, over the 5000B size threshold.

---

### CARD-0344 · [enhancement] [maintenance] Extend the update checks to the software they don't cover (Node-RED, ring-mqtt, matter-server, orchestrator deps, Immich sidecars, Tailscale, ESPHome) — RESOLVED 2026-09-28 12:58 MST
**Status:** Done

Archived to `core/maintenance/card-archive.md` on 2026-09-28 (CARD-0193) — 16732B, over the 5000B size threshold.

---

### CARD-0343 · [bug] [air-quality-monitor] AQM records nothing in the field after a cold boot -- no valid clock, every reading skipped as `clock_invalid`
**Status:** Done

Archived to `components/air-quality-monitor/card-archive.md` on 2026-09-27 (CARD-0193) — 15044B, over the 5000B size threshold.

---

### CARD-0342 · [enhancement] [salt-sensor] [homeassistant] Audible or push alert when salt goes critical -- today the critical alert only flips a switch and writes a dashboard line
**Status:** Backlog

**Priority:** Medium -- the critical alert already fires -- what is missing is making it audible or a push, a convenience rather than a fault. (set 2026-09-29 15:41 MST, triage)

**Raised 2026-09-25 20:34 MST (Joseph: "open a card for it, leave in backlog"), from CARD-0341's finding that "nothing played" when `switch.salt_critical_alert` turned on -- which is by design, not a bug.** Backlog only: captured, not scoped, no interview yet, no work started.

**Facts established (2026-09-25, from CARD-0341's investigation):**
- **What a critical (<15%) or low (15-33%) reading delivers today:** the alert switch goes `on` (visible in the Google Home app, answerable by voice query -- both alert switches are exposed to `cloud.google_assistant`, also `cloud.alexa` and `conversation`), and Node-RED writes an `Alert`-category line to the log dashboard. **Nothing plays and nothing is pushed.** CARD-0261's own design says the switches are "visibility only... no routine reacts to them"; live HA confirms it (2026-09-25 20:31 MST: `search/related` on `switch.salt_critical_alert` returned no automations, scripts or scenes).
- **Why this matters now:** the salt sensor read **4% (42.1 cm)** at 2026-09-25 20:27, and the critical alert had been unable to hold on until CARD-0341 fixed the helper that same afternoon -- i.e. the tank got to critical with no way for anyone to be told.
- **Since CARD-0341 (deployed 2026-09-25 20:27), the switch is re-asserted on every reading** (every 12 h and on every device reboot), so a trigger keyed to the switch turning `on` would fire on the first critical reading and again whenever the switch had been turned off and the next reading turns it back on.
- **Precedents already in the repo:** the watchdog pushes to Joseph's Pixel through the HA companion app (`core/node-red/watchdog-README.md`); `automations.yaml` already targets a Google speaker (`media_player.garage_speaker`); CARD-0145 built a Ring-motion announcement on Google Home.

**Options (not chosen, to be worked out in the interview):** (a) an HA automation on `switch.salt_critical_alert` -> `on` that announces on a Google speaker; (b) the same automation sending a companion-app push; (c) a Google Home routine keyed to the switch, built in the Google Home app (outside the repo -- unversioned, like the SmartThings routines CARD-0164/0260 are about); (d) logic in Node-RED calling HA's notify/TTS service directly, since the root architecture puts logic in Node-RED and treats HA as the integration layer; (e) a combination.

**Questions the interview has to answer:** who is told (Joseph, Robin, both) and by which channel; which speaker(s), and quiet hours for an announcement; warning as well as critical, or critical only; repeat behavior -- once per crossing, or nag every 12 h while critical, or escalate; how it is acknowledged (turning the switch off? `salt_full_reset` after refilling?) without the re-assert on the next reading simply re-triggering it; where the logic lives (HA automation vs. Node-RED) and how that stays in the repo (`automations.yaml` is version-controlled; a Google Home routine is not).

**Non-goals (provisional):** no change to the 15%/33% thresholds (Joseph, 2026-09-25: "leave it the way it is"); no change to the salt-sensor firmware or to CARD-0341's switch/re-assert behavior; no SmartThings involvement (CARD-0261 removed it).

**Done when:** to be written from the interview -- at minimum, a real critical reading produces the notification the interview settles on, confirmed live rather than by a synthetic test.

**Related:** CARD-0341 (found here; the switch now holds and is re-asserted), CARD-0261 (built the alert switches as visibility-only), CARD-0280 (the earlier end-to-end test), CARD-0145 (Ring motion announcement -- an audible-alert precedent), `components/salt-sensor/README.md` (HA-Native Switches), `core/node-red/watchdog-README.md` (the push-notification pattern).

---

### CARD-0341 · [bug] [salt-sensor] [homeassistant] `switch.salt_critical_alert` can never stay on -- its `turn_on` action is followed by a `turn_off` that undoes it, and it has no `turn_off` action — RESOLVED 2026-09-25 20:32 MST
**Status:** Done

Archived to `components/salt-sensor/card-archive.md` on 2026-09-27 (CARD-0193) — 10682B, over the 5000B size threshold.

---

### CARD-0340 · [bug] [garage-presence] [homeassistant] `switch.garage_presence_vswitch` never turns on -- HA reports success but state stays `off`, and every SmartThings entity in HA looks frozen since 2026-09-21
**Status:** Backlog

**Priority:** Medium -- a garage automation switch that never turns on -- a real fault, but nothing depends on it urgently. (set 2026-09-29 15:32 MST, triage)

**Raised 2026-09-25 16:47 MST (Joseph: "open a card for the vswitch finding"), found by accident while live-testing garage-radar's new firmware for CARD-0335. Joseph then said "don't chase the vswitch right now" -- so everything below is what was observed in about ten minutes of read-only inspection, nothing was fixed or tried, and the cause is unknown.** Priority set to Medium 2026-09-29 15:32 MST (triage) -- see "Why it matters."

**Observed, 2026-09-25 16:41-16:42 MST (read-only, via HA's own in-page state/WebSocket in Joseph's signed-in Chrome; nothing in HA was changed):**
- Joseph walked in front of the radar. Presence went ON at 16:41:24.7 on MQTT and in HA within the same second; "Garage Presence - Restart timer on activity" ran and started the 900 s timer. **`switch.garage_presence_vswitch` stayed `off`.**
- That run's trace shows both actions finished with no error: `timer.start` (duration 900) and `switch.turn_on` on the vswitch. HA believes the command succeeded; the entity's state never followed. The two earlier radar-triggered runs today (16:06:29, 16:08:37) left it `off` too.
- `switch.garage_presence_vswitch` is a **SmartThings-platform** entity (registry `platform: smartthings`). Its last state change was **2026-09-21 17:10:00 MST**, an `off` by "Garage Presence - Timer expired". The logbook shows no `on` since 2026-09-21 08:15:44.
- The other SmartThings garage switches are equally stale: `garage_door_auto_close_enable_vswitch` = on (last changed 09-21 03:08:07), `garage_door_open_vswitch` = off (09-21 16:55:24), `open_close_garage_door` = off (09-21 08:03:06).
- **Across the whole integration:** 195 SmartThings-platform entities, **71 `unavailable`/`unknown`**, and the newest `last_updated` on any of them is **2026-09-21 21:40:35 MST** (`sensor.ecobee_guest_room_temperature`). The single config entry ("Home Main") reports `state: loaded`.
- The radar's yellow LED mirrors the vswitch via `jctsh/components/garage-presence-vswitch/state`, so it is also off while someone is present.

**Why it matters -- a hypothesis, not a verified fact:** per `components/automatic-garage-door-opener-closer/auto-garage-door-system.md`, the SmartThings auto-close routine fires on `enable = ON AND door open = ON AND presence vswitch = OFF`. If the vswitch is stuck `off` in SmartThings as well as in HA, the "someone is in the garage" interlock the whole system exists for is defeated -- the door could close on a person. **Not established either way**, because the ST-side state was not looked at, and whether the door has been opened since 09-21 is unknown (the door-open vswitch is itself frozen).

**Not checked (deliberately stopped):** (1) what SmartThings itself holds for the presence vswitch; (2) whether ST->HA events are reaching HA at all vs. HA->ST commands failing silently; (3) whether the garage door has actually been opened/closed since 09-21; (4) what happened around 2026-09-21 17:10-21:40 MST -- an HA restart, a token/OAuth/Nabu Casa event, or the SmartThings API change from CARD-0164; (5) whether reloading the config entry recovers it (root `CLAUDE.md`'s CARD-0240 note documents exactly this "`loaded` but not re-synced" failure mode and its reload fix -- **not tried**).

**Proposed Done when (to be confirmed in the interview, not yet agreed):** (a) the cause of the freeze is identified and recorded; (b) the vswitch follows presence again -- radar presence turns it `on`, timer expiry turns it `off` -- confirmed by a live walk-through, not a synthetic test; (c) the ST->HA sync is confirmed live for the other garage entities; (d) the auto-close interlock is confirmed to hold with the door open and someone present (or explicitly documented as unverifiable).

**Non-goals:** no change to the auto-close routine's logic, no migration off SmartThings (that is CARD-0164/CARD-0260), no change to the radar firmware (verified fine on this card's trigger date).

**Related:** CARD-0335 (found while verifying it), CARD-0164 (SmartThings API cutoff; Auto verify 2026-10-02), CARD-0260 (rebuilding the garage routines HA-natively), CARD-0055 (earlier presence/lights reconciliation), CARD-0240 (post-update "loaded but not synced" reload fix), `components/garage-presence/CLAUDE.md`, `components/automatic-garage-door-opener-closer/auto-garage-door-system.md`.

---

### CARD-0339 · [bug] [node-red] AQM buffered event lines (`wifi_attempt_start`) were mistaken for readings -- surfaced as "undefined reading @ undefined" alerts
**Status:** Done

Archived to `core/node-red/card-archive.md` on 2026-09-28 (CARD-0193) — 2609B, over the 2000B size threshold.

---

### CARD-0338 · [enhancement] [data-pipeline] Early-warning health probe for the environmental Sheet
**Status:** Done

Archived to `core/data-pipeline/card-archive.md` on 2026-09-28 (CARD-0193) — 4911B, over the 2000B size threshold.

---

### CARD-0337 · [enhancement] [data-pipeline] Keep the Environmental Data sheet small: archive old rows and make the export read only what it needs
**Status:** Done

Archived to `core/data-pipeline/card-archive.md` on 2026-09-27 (CARD-0193) — 14498B, over the 5000B size threshold.

---

### CARD-0336 · [bug] [hike-izer] Photo-based scat identification is unreliable -- same photo gets different species across models and runs
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-27 (CARD-0193) — 6963B, over the 5000B size threshold.

---

### CARD-0335 · [enhancement] [garage-radar] [salt-sensor] Retrofit the boot-time heartbeat (Build Standards §4.1) onto the two remaining 30-minute-heartbeat ESPHome devices — RESOLVED 2026-09-25 17:02 MST
**Status:** Done

Archived to `components/garage-radar/card-archive.md` on 2026-09-27 (CARD-0193) — 11120B, over the 5000B size threshold.

---

### CARD-0334 · [bug] [tos] [mqtt] [homeassistant] [node-red] Rotate credentials printed into a 2026-09-24 session transcript, and adopt a never-print / always-REDACT rule for sessions
**Status:** Backlog
**Priority:** High — real exposure, not hygiene; the rotation policy in `credentials.local.md` treats a known transcript exposure as a rotation trigger.

**Raised 2026-09-24 18:54 MST (Joseph: "open a card for the password rotation (rule: do not print passwords, always REDACT them)").** *This card deliberately contains no secret values — credentials are named, never quoted.*

**Current state, 2026-09-24 19:08 MST (Joseph: "put all this in the card, no action now") — planning only; nothing below has been done.** No credential has been rotated; no Claude Code settings, hooks or permission rules have been changed; root `CLAUDE.md`, `credentials.local.md`, the Pi, the M8 and every device are untouched. The only things in force are the rule itself (recorded in the assistant's own session memory, which is not a durable home — see Done-when (2)) and this card. Decision 1 (where secrets live) was settled the same evening — see below; decisions 2–4 remain open, and the card stays in Backlog until Joseph answers them. **Amended 2026-09-24 21:21 MST:** a sequencing flaw in the first version of the plan was found and fixed (Phase 0 and a reconciliation step added — see the plan), and the Credential Manager's limits were recorded under decision 1. Still documentation only.

**Second occurrence, 2026-09-28 (hike-izer cluster session, CARD-0349 Step 4 work) — the same credential as before.** A debug print while writing a Node-RED Admin API patch script (a one-off `re.search` sanity check) printed the real Node-RED admin password into this session's transcript. Caught and disclosed immediately, per the rule. Same credential as route 1 of the original 2026-09-24 incident above — this is a *repeat* exposure of the Node-RED admin password specifically, not a new credential. **Joseph's call, asked directly: note it, defer rotation** (not rotated as part of this). None of Phase 0/1's guardrails below exist yet, so nothing mechanical caught this either time — still an open gap.

**What happened.** While working CARD-0219/CARD-0333, a Claude session printed secrets into its transcript (the local transcript file and the API traffic behind it) by four routes:
1. **Reading `credentials.local.md` sections to find a token:** the Home Assistant long-lived token (`HA_TOKEN`) and the Node-RED admin password; the Mosquitto accounts table (`jctsh-log-server`, `hiking-monitor`, `photo-server`, `netalertx`, `ring-mqtt`, `air-quality-monitor`); and, via a keyword grep of the same file, the `hike-izer-orchestrator` MQTT password and `hiking-monitor`'s device `mqtt_password`.
2. **Diffing two generated `main.cpp` files** (to compare compiled builds): printed both `front-porch-temp-sensor`'s and `back-patio-temp-sensor`'s MQTT passwords and OTA passwords.
3. **Pasting secret literals into commands:** `HA_TOKEN` (many times) and the `jctsh-log-server` MQTT password appeared in the command text itself, so they are in the transcript regardless of what the commands output.
4. Separately noted: front-porch's OTA password is a trivially guessable value, weak independent of this exposure; and `credentials.local.md` records some ESP32 secrets as shared across all four ESP32 components' `secrets.yaml`, so rotating one may mean all four.

Not exposed: the Log Dashboard password (two attempts to read it were blocked by the harness's credential guard, correctly).

**How secrets are managed today — as-is, verified 2026-09-24 19:04 MST** (paths and variable names only; no values):
- **One plaintext master list:** `credentials.local.md` at the repo root — gitignored (`.gitignore` line 4; `git ls-files` confirms it is not tracked), 16 sections covering SSH, Mosquitto accounts, Apps Script, Log Dashboard, NetAlertX, Node-RED, Home Assistant, router, DuckDNS, the hiking-monitor hotspot, ESPHome OTA, hiking-monitor secrets, Thunderforest, Xeno-canto, and the rotation cadence. It is a human lookup, not read by any code — but one `cat` or `sed` of it dumps most of the estate at once, which is exactly what happened.
- **Runtime copies:** on the Pi, `/etc/jctsh/log-server.env` (systemd `EnvironmentFile`: the log server's MQTT password and `DASHBOARD_PASS`), `/home/pi/.node-red/environment` (`HA_TOKEN` for Node-RED), Node-RED's encrypted broker credentials, `/etc/mosquitto/passwd` (hashed), and Home Assistant's own MQTT credentials (UI-only config, held inside HA). On the M8 / photo-server, gitignored `.env` files (photo-tv-display, hike-izer-orchestrator; `.env.example` is committed) and `/etc/jctsh/heartbeat.env`; hike-izer-web's Cloudflare Tunnel credentials (gitignored).
- **Devices:** ESPHome `components/<name>/secrets.yaml` and Arduino `secrets.h` (gitignored; `secrets.yaml.template` committed). Because ESP-IDF cannot build in a path with a space, each device's `secrets.yaml` is **copied again** into `C:\esphome\<name>\`, and the values are **compiled into the firmware and into the generated `main.cpp`** — including build trees under `components/*/.esphome/` inside the repo directory.
- **Identity model:** one Mosquitto account per component (`allow_anonymous false`), SSH by key from the workstation, per-service tokens where they exist. **Rotation policy:** `credentials.local.md` §Credential Rotation Cadence (Tier 1 tokens 180 d, Tier 2 passwords 365 d, Tier 3 device secrets incident-driven) and per-credential checklists such as CARD-0280's.
- **Guardrails today:** the gitignore rules and a written convention (root `CLAUDE.md`: "kept off-disk and out of source control"). **Nothing mechanical in the Claude Code layer:** `.claude/settings.local.json` has 196 allow rules, **0 deny rules, no hooks**, and it is gitignored and per-machine — there is no checked-in project `.claude/settings.json`, so no guard would travel with the repo.

**What the inventory shows — the actual gaps:**
1. The written convention is inaccurate: secrets *are* on disk (plaintext, gitignored), not "off-disk".
2. A single plaintext master file is a single point of total exposure.
3. Generated `main.cpp` with compiled-in secrets sits inside the repo tree, where a recursive grep or a diff surfaces it.
4. Sessions have no way to *use* a credential without *seeing* it: in this session every helper (HA calls, `mosquitto_sub`) took the value as a literal in the command.
5. The harness's auto-mode classifier blocked two attempts to read `DASHBOARD_PASS` from the Pi but not the reads of `credentials.local.md` — an inconsistent control that cannot be relied on.
6. Blast radius is larger than it needs to be: one `HA_TOKEN` is shared by Node-RED, photo-tv-display, hike-izer-orchestrator and Claude Code (and sits in plaintext in a world-readable `flows.json`, CARD-0332); and the tracked `core/mqtt/mosquitto.conf` defines **no ACLs**, so any authenticated account can read and write every topic — an exposed device password is a password to the whole bus.
7. Some ESP32 secrets are shared identically across all four original components (`credentials.local.md` records this), and front-porch's OTA password is trivially guessable.

**The rule (Joseph, 2026-09-24): never print a password, token, key, or secret — always REDACT.** In practice:
- **Never `cat`/`sed`/`grep`/`diff`/`git diff`/`Read` a file that can hold secrets** — `credentials.local.md`, `secrets.yaml`, `secrets.h`, generated `.esphome/build/**/main.cpp`, `.env` files, `/etc/jctsh/*.env`, `/etc/mosquitto/passwd` — without masking values first. Prefer checks that cannot leak: existence, length, a hash, or a masking filter such as `sed -E 's/((pass(word)?|token|key|secret|auth)[A-Za-z_]*[:=] *).*/\1[REDACTED]/I'`.
- **Never put a secret literal in a command.** Read it inside the command (`TOKEN=$(grep ... | cut ...)`) so it appears in neither the command text nor the output.
- **Anything that surfaces one anyway is an incident:** say so immediately, name the credential (not the value), and open or extend a rotation card — the way this card came about.
- The rule applies to everything a session writes too: cards, commit messages, docs, chat.

**How we will stop exposing secrets — proposed plan (Joseph to confirm or adjust before any Build).** Principle: sessions should never need to *see* a secret in order to *use* it, and the unsafe path should be mechanically hard, not merely discouraged.
- **Step 0 — reconcile where each secret lives today (one inventory pass, before anything is moved or denied).** Today's placement is accidental: some values are in `credentials.local.md`, some entries there read "(fill in)" (the Log Dashboard password and the `nodered` and `homeassistant` MQTT accounts, for example), so those values live elsewhere — RoboForm or Joseph's head — and the assistant cannot see RoboForm at all. For each secret, record exactly one of: in RoboForm / in a runtime file / in `credentials.local.md` / not stored anywhere. Only then can the file shrink to an index without stranding a value in neither place. Names and locations only — no values.
- **Phase 0 — a minimal machine store and helper, *before* any deny rule (added 2026-09-24 21:21 MST — the first version of this plan had a sequencing flaw).** Today `credentials.local.md` is the *only* source a session has for routine work — Home Assistant API calls and Pi-side MQTT peeks with the log-server account. Phase 1 denies reading that file; landed first, it would break that work with nothing to replace it. So first: put just the actively used secrets (the HA token and the log-server MQTT account, nothing else until a need is real) into the Windows Credential Manager, and build the minimal `secret` helper (`secret set`, `secret run`, `secret has|fingerprint`, `secret new`; see decision 1) plus the two or three wrappers that use it. Only once sessions can do their routine work *without* reading the file does Phase 1 deny it.
- **Phase 1 — mechanical guardrails (small; lands only after Phase 0).** (a) A checked-in project `.claude/settings.json` with `permissions.deny` on Read/Edit of `credentials.local.md`, `**/secrets.yaml`, `**/secrets.h`, `**/.env`, and `**/.esphome/**`, plus Bash/PowerShell deny patterns for the obvious dumps — best-effort only, since a shell has too many ways round a pattern, hence (b). (b) A `PreToolUse` hook on Bash, PowerShell, Read and Grep that blocks commands touching those paths or carrying secret-shaped literals (JWTs, `Bearer …`, `-P <value>`, `password=…`) and says where the safe helper is. (c) A `PostToolUse` tripwire that compares tool output with salted *fingerprints* of the current secrets (never the values) and secret-shaped patterns; it cannot un-print, but it ends silent exposure by telling the session at once — name the credential, open an incident. (d) Delete the build trees under `components/*/.esphome/` and keep builds in `C:\esphome\`.
- **Phase 2 — use without seeing.** A small helper under `tos/` backed by a store outside the repo tree: `secret run <cmd>` injects named secrets into the child process only and masks every known value and secret-shaped pattern in its output; `secret has|fingerprint <name>` answer without revealing. On top of it, wrappers for the recurring needs that caused this incident — Home Assistant API calls, Pi-side MQTT peeks with the log-server account, and an ESPHome `build-info`/reported-hash comparison that prints hashes and versions only. `credentials.local.md` shrinks to a **values-free index** (name, owner, where it lives, last-rotated date) plus Joseph's own recovery copy. **Store (decided, decision 1):** RoboForm stays Joseph's human system of record; the machine store is the Windows Credential Manager (DPAPI-backed, no new software); rotation bridges them with a generated value on the clipboard, never printed.
- **Phase 3 — shrink the blast radius (each is its own card).** One HA token per consumer, individually revocable; per-account Mosquitto ACLs (a device writes its own prefix and reads its own command topic; the log server reads all; HA gets the discovery prefix); fix CARD-0332; unique, strong OTA and MQTT secrets per device.
- **Phase 4 — process.** Put the rule in root `CLAUDE.md`'s Credentials section (correcting the "off-disk" claim) and in `JCTsh-Operating-System.md`'s Engineering Discipline; write the incident procedure (this card's pattern: name the credential, rotate by tier, Tier 1 within a day).
- **Suggested order:** Step 0 (reconciliation) → Phase 0 (minimal store + helper for the actively used secrets) → Phase 1 (deny rules + hooks; about an hour, and it stops recurrence) → rotation *using the safe path* → the rest of Phase 2; Phases 3–4 as separate cards.

**Decisions — 1 settled, 2–4 open; each open one carries the assistant's recommendation (a recommendation, not a decision):**
1. ~~**Where do secrets live for Phase 2?**~~ **DECIDED 2026-09-24 21:12 MST (Joseph, "yes, update the card" — accepting the recommendation): two roles, not one tool.** Joseph already uses **RoboForm**, which has **no scriptable interface** — checked, not assumed: v9.9.4.6 is installed on this workstation and ships only GUI tools plus a browser-extension host, no command-line executable; no official CLI or API turned up, only an unofficial, unsupported, reverse-engineered library, which is **not** to be used with these credentials. So:
   - **RoboForm is the human system of record** — where Joseph reads and records secrets, outside any session (this is also decision 3's bypass). `credentials.local.md` shrinks to a **values-free index** whose names match the RoboForm entries (for example a `JCTsh` folder: Logins for services, Safenotes for per-device secrets).
   - **The Windows Credential Manager (DPAPI-backed) is the machine store**, holding only the few values automation needs (for example the HA token and the log-server MQTT account); the Phase 2 `secret` helper reads from it.
   - **Rotation bridges the two without printing anything:** a helper generates the new value, stores it in Credential Manager, and places it on the clipboard (auto-cleared after ~60 s); Joseph pastes it into the RoboForm entry. One manual paste per rotation.
   - **What the Credential Manager does and does not do (so nobody over-trusts it):** entries are DPAPI-encrypted per Windows user and never sit in a plaintext file. But **any process running as Joseph — including a Claude session's shell — can read them through the Windows credential APIs, so it is an at-rest store, not a barrier against sessions.** The barrier is design plus Phase 1: sessions go through `secret run`, which never prints, and a hook blocks direct credential-API reads outside the helper (`CredRead`, `Get-StoredCredential`, `GetNetworkCredential`, `Get-Secret -AsPlainText`, and the like). It is local to this workstation (no sync); the values are lost or orphaned if the Windows profile is lost or the account password is reset from outside — which is why RoboForm stays the record; entries are limited to about 2.5 KB (ample for tokens); `cmdkey` can add and list but not read back; and the GUI reveals a value only after Windows re-authentication. Implementation route (a small wrapper over the credential APIs, or an existing PowerShell module) is decided when Phase 0 is built.
   - **Helper surface (Phase 0):** `secret set <name>` (masked prompt, run by Joseph in his own terminal); `secret run` (injects named secrets into the child process only and masks them in its output); `secret has|fingerprint <name>` (answers without revealing); `secret new <name>` (generate, store, and place on the clipboard for ~60 s).
   - **Not to do:** export RoboForm to CSV anywhere under `C:\Shared` (it recreates the plaintext master file); drive RoboForm's UI through screenshots (the values land in the transcript); use the unofficial API library.
   - *Still open under this decision:* how Joseph's RoboForm entries are organized today (folder names), so the index can mirror them. If scripted retrieval straight from a manager is ever wanted, KeePassXC or the Bitwarden CLI can do it, but that is not a reason to switch.
2. **Rotate now, or defer, per tier?** *Recommendation:* do Phase 0 and Phase 1(a)–(b) first, then rotate **Tier 1 the same day** — the HA long-lived token (widest blast radius; use CARD-0280's checklist), then the Node-RED admin password and the printed Mosquitto accounts — generating and installing the new values through a script so the rotation itself does not re-expose them. **Batch the ESP32 device secrets** (reflash required, and Phase 3 wants unique per-device values anyway) into one pass rather than flashing twice; do not leave them indefinitely, since they were exposed. Rotating *before* the guardrails exist is the riskier order, because the rotation is itself a secret-handling session.
3. **Approve Phase 1's hooks?** They change what *every* session may read. They can only land after Phase 0: until a machine store exists, `credentials.local.md` is the sole source for routine Home Assistant and MQTT work, and denying it first would break that. *Recommendation: yes*, scoped to the named secret paths and secret-shaped literals only. **Bypass for Joseph:** he can always read any of these files in his own terminal or editor *outside* the Claude Code session. Do **not** use the session's `!` prefix for this — its output lands in the conversation, i.e. it is the same exposure again. A session that genuinely needs a value should ask Joseph to run the masked helper (Phase 2), not to paste the value. Add an explicit, logged escape hatch only if that proves too blunt.
4. **Do Phases 2–4 become their own cards?** *Recommendation: yes, once Phase 1 has landed* — keep this card as the incident record plus rotation plus Phase 1, and open Phase 2 (store + `secret` helper + wrappers), Phase 3 (per-consumer HA tokens, Mosquitto ACLs, CARD-0332, unique device secrets) and Phase 4 (rule in `CLAUDE.md`/OS, incident procedure) as separate cards, since each is a project of its own.

**Rotation.** Follow `credentials.local.md`'s Credential Rotation Cadence tiers and the CARD-0076 precedent (itself a botched redaction). Suggested order by blast radius; **each credential's decision — rotate now, defer, or accept, with the reason — is Joseph's, recorded here:**
1. **HA long-lived token** — widest (Node-RED, photo-tv-display, hike-izer-orchestrator); use the CARD-0280 rotation checklist, which lists every place it lives.
2. **Node-RED admin password.**
3. **Mosquitto accounts** — the six above plus `hike-izer-orchestrator`, `front-porch-temp-sensor`, `back-patio-temp-sensor`. Each needs the broker change *and* the consumer's config; mind the `chown root:mosquitto /etc/mosquitto/passwd` gotcha, and that Home Assistant's own MQTT credentials are UI-only config.
4. **ESP32 OTA/MQTT secrets** (front-porch, back-patio, hiking-monitor) — need a reflash. Tier 3 in the policy is "incident-driven only", and this is the incident. Check first whether the four components really share values.

**Done when:** (1) every credential listed above is either rotated and verified live, or explicitly decided against with the reason written here; (2) the rule is in a durable place every session reads — root `CLAUDE.md`'s Credentials section — not only in a session's memory; (3) a one-time reconciliation has recorded where each secret lives (RoboForm / runtime file / Credential Manager / not stored), and `credentials.local.md` is a values-free index whose names match Joseph's RoboForm entries, and its rotation table shows last-rotated dates (dates only, never values); (4) the fix plan above is delivered or each phase explicitly deferred by Joseph — at minimum Phase 0 (the minimal store and helper) and then Phase 1's deny rules and hooks, in that order, because a rule that depends on a session remembering it has already failed once; (5) the as-is inventory above is kept current somewhere sessions read (and root `CLAUDE.md`'s inaccurate "off-disk" statement corrected).

**Non-goals:** no change to the credential storage scheme; no rotation of credentials not listed; no attempt to scrub the transcript.

**Related:** CARD-0076 (same failure class, first instance), CARD-0280 (HA token rotation checklist), CARD-0333 (where this happened), root `CLAUDE.md` Credentials section, `credentials.local.md` §Credential Rotation Cadence.

**Third occurrence, 2026-09-29 13:46 MST (general session, CARD-0365/CARD-0367 work) -- four more credentials printed into this session's transcript.** Named, not quoted. (1) **The data-pipeline gateway `API_KEY`** -- printed in full by a Caddy-redaction check whose `grep -o` printed the whole logged `uri` (which still carried the key because the redaction wasn't live yet); it had also sat in full in Caddy's own log for ~a day. (2) **`NETALERTX_WEBHOOK_SECRET`** -- printed in full when a keyword search of `credentials.local.md` returned a whole line; the masking `sed` only matched a table-cell shape, not a backtick-quoted value -- the same failure CARD-0324 recorded (a masking regex is not a control). (3) **The retired Apps Script key** -- printed in full when a dashboard log line was displayed with `cut` instead of a mask; it is the CARD-0367 leak (a failed subprocess put its whole argv into an alert, now scrubbed at the publish boundary). (4) **The `photo-tv-display` deletion-log Apps Script key** (`DELETION_LOG_SHEET_APPS_SCRIPT_KEY`) -- printed in full when an unmasked `grep` of `credentials.local.md` for a host name happened to match its row. **Root cause, all four:** each was a command whose output could contain a secret, run with no fail-safe -- either an ad-hoc masking pattern that didn't match the shape of that value, or no mask at all. None was a value the task needed to see. Also worth recording: the **Node-RED admin password was read this session without being printed** (read in-process by a deploy script, used for the admin API, never echoed) -- the safe pattern, and the one Phase 0/2's `secret run` is meant to make the only pattern. **Rotation impact:** add all four to the rotation list; the gateway key and the retired Apps Script key are already CARD-0370's scope, but the photo-tv-display deletion-log key and the NetAlertX webhook secret (the latter also on CARD-0332's list) have no rotation card of their own yet. None of Phase 0/1's guardrails existed, so nothing mechanical caught any of the three -- still the open gap. See CARD-0372 (automated rotation) for the proposal to make each rotation a single, value-free command instead of a manual multi-holder chore.

**Fourth occurrence, 2026-10-02 05:46 MST (tos session, testing CARD-0334 Phase 1's own guardrails) -- the entire `credentials.local.md` file printed into this session's transcript.** Not a partial leak like the prior three occurrences -- a full `Read` of the whole file, every credential it catalogues (SSH/M8 login, Ubuntu Pro token, GitHub PAT, Immich DB password + both account passwords + both API keys, `photo-tv-display`'s deletion-log key, hike-izer-orchestrator's `WEBHOOK_SECRET`/`ANTHROPIC_API_KEY`/MQTT password, data-pipeline-api's `API_KEY`/`POSTGRES_PASSWORD`, Log Dashboard password, NetAlertX password + webhook secret, Node-RED admin password, `HA_TOKEN` + Robin's HA password, router admin password, DuckDNS token, the hotspot password, both ESPHome OTA passwords on record, hiking-monitor's WiFi/AP/OTA/MQTT secrets, Thunderforest key, Xeno-canto key, and every Mosquitto account password in the file) -- same shape as this card's own "What is exposed" list, just via this session's transcript instead of the public repo. **How it happened:** verifying whether the just-drafted `.claude/settings.json` (CARD-0334 Phase 1a) actually blocked reading the file -- it didn't, because the file didn't exist yet at the expected path when the test ran (Joseph had saved it somewhere else; confirmed by the path simply not existing). **Caught immediately, no values repeated since.** **Root cause still open, not just "the file was missing":** once Joseph moved the file to the correct path (`C:\Shared\jctsh\.claude\settings.json`, content verified syntactically matching the drafted deny rules), a second, deliberately low-risk test (`Grep` for a string guaranteed not to match, so even a bypass would leak nothing) *still* wasn't blocked -- ran normally, "No matches found." Leading theory: this already-running session cached its permission set at startup, hours before the file existed, and project `.claude/settings.json` only loads at session start, not hot-reloaded into a live session -- but a syntax problem in the deny patterns themselves hasn't been ruled out. **Needs a fresh session in this repo to test the same thing and settle which it is** -- not yet done as of this entry. **Every credential in `credentials.local.md` should be treated as exposed via this transcript as of today**, same discipline as the three prior occurrences -- a registry-wide sweep adding this date to every affected `exposed:` field is follow-up work, not done in this entry.

**Two-profile note, 2026-09-29 14:17 MST (from CARD-0372 planning).** Decision 1's machine store -- the Windows Credential Manager -- assumed one Windows profile. Joseph runs Claude Code, RoboForm and terminals from **two profiles** against one shared working copy (`C:\Shared\jctsh`), and the Credential Manager is per-user: a value stored in one profile is invisible to the other and cannot be updated by the other. **Decision 1 is therefore reopened for the machine-store half only** (RoboForm as the human record is unaffected) -- see CARD-0372's open decision 0 (per-profile Credential Manager vs. a shared encrypted vault file vs. a shared KeePassXC database). Phase 0 should not be built until that is settled. **Settled 2026-09-29 14:21 MST (Joseph): B2 -- a shared KeePassXC database outside the repo tree**, its master credential in each profile's Credential Manager; the `secret` helper reads it through `keepassxc-cli`. Decision 1's RoboForm half stands (human record); the machine store is now KeePassXC, not the per-user Credential Manager alone. Phase 0 is unblocked on this point.

**Step 0 progress, 2026-09-29 14:31 MST (from CARD-0372 Step 1).** The reconciliation's machine-readable half now exists: `tos/credential-registry.yaml` lists 17 credential entries with their holders, tiers, last-rotated dates (4 known, 13 unknown) and recorded exposures. **Still open for Step 0:** the RoboForm column (Joseph -- `unknown` on every entry) and confirming the holders marked `verified: false`. `credentials.local.md` has not been touched, and nothing has been moved out of it.

**Reconciled against CARD-0375, 2026-10-02 -- this card never pointed back at it (a real one-way gap: CARD-0375 named this card in its own `Related:` line five days ago, this card never named CARD-0375 back).** Both cards call for rotating overlapping credentials, found independently (this card: a 2026-09-24 session-transcript exposure; CARD-0375: a 2026-09-30 scan finding the same values already committed to the **public** repo, a worse exposure than either card knew about when raised). **Real overlap, by registry `id`:** `node-red-admin-password` (both cards) and hiking-monitor's Mosquitto/OTA secrets (this card's "hiking-monitor mqtt/ota"; CARD-0375's `mosquitto-accounts--hiking-monitor` + `esp32-device-secrets--hiking-monitor-ota`). **The registry is the single place rotation status lives -- neither card restates it, on purpose (corrected 2026-10-02: an earlier version of this note did restate it, which just creates a second copy that drifts the moment either card forgets to update it).** Every credential either card names has its exposure(s) recorded in `tos/credential-registry.yaml` (both dates, both cards, where they differ) -- that file is where to check what's actually been rotated, not this prose. This card and CARD-0334 stay the incident narrative and the decision record; "is it done yet" is a registry question, every time, for both.

---

### CARD-0333 · [enhancement] [front-porch-temp-sensor] [back-patio-temp-sensor] Boot-time heartbeat — every reboot of a 30-minute-heartbeat device raises a false watchdog alert — RESOLVED 2026-09-24 18:54 MST
**Status:** Done

Archived to `components/front-porch-temp-sensor/card-archive.md` on 2026-09-27 (CARD-0193) — 8291B, over the 5000B size threshold.

---

### CARD-0332 · [bug] [node-red] Home Assistant access token sits in plaintext in a world-readable `flows.json`

**Status:** Backlog

**Priority:** High -- security exposure: a long-lived Home Assistant token sits in plaintext in a world-readable `flows.json`. (set 2026-09-29 15:32 MST, triage)

**Raised 2026-09-23 12:09 MST, found by CARD-0328's drift-check work.** Node-RED's own `global-config` node stores its environment variables in `/home/pi/.node-red/flows.json` in plaintext, including a long-lived Home Assistant access token, and that file is `-rw-r--r--` (readable by any local user on the Pi). Separately, a diagnostic command run during CARD-0328 printed that node in full, so the same token also appeared in a Claude Code session transcript on Joseph's workstation. Essence-only until Planning interviews it -- open questions: whether to rotate the token (at minimum, given the transcript exposure), whether the token should live in `/home/pi/.node-red/environment` only (`watchdog-README.md` already describes it being read from there) rather than also in the flow file's env, and whether `flows.json`'s permissions should be tightened (Node-RED runs as `pi`).

**Two more secrets exposed the same way, added 2026-09-23 12:33 MST (Joseph: "add the other exposures to 332") -- found during CARD-0324, while this session was looking for the Node-RED admin login in `credentials.local.md`.** Not a plaintext-at-rest problem like the token above; these are *transcript* exposures only -- a keyword search of that file printed whole lines, and the session's masking pattern didn't cover them. Both appeared in a Claude Code session transcript on Joseph's workstation. Values deliberately not recorded here, not even prefixes.
- **The NetAlertX webhook secret** (`NETALERTX_WEBHOOK_SECRET`) -- printed in full. It signs NetAlertX's webhook POSTs so Node-RED can verify they really came from NetAlertX (CARD-0078), so it lives in two places that must match: NetAlertX's own publisher settings and `/home/pi/.node-red/environment` on the Pi. Rotating it means changing both together, or the signature check fails and new-device alerts stop arriving.
- **The Apps Script `API_KEY`** (Environmental Data pipeline) -- printed *in part* (the first ~30 characters of a longer value). Lives as an Apps Script script property and as a Node-RED env var. A partial key is a weaker exposure than a full one, but the printed part is most of it, so treat as compromised unless the key's length says otherwise.

**Open questions added by these two:** rotate all three exposed secrets (HA token, webhook secret, API key) together in one pass, or only the ones whose blast radius justifies it -- `credentials.local.md`'s own rotation-cadence table lists the HA token as widely reused (Node-RED, photo-tv-display, hike-izer-orchestrator), which makes it the most disruptive to rotate and the most valuable to; and whether `credentials.local.md` should stop being a file a session can search at all, given that a masking regex is not a control (see CARD-0324's Reflection for the allowlist pattern).
**Not part of CARD-0328:** that card's script never compares or shows `global-config`, so it is unaffected either way.

**Related:** CARD-0328 (found the token), CARD-0324 (where the webhook secret and API key were exposed), CARD-0331 / `core/node-red/watchdog-README.md` (the watchdog is the consumer of this token).

---
### CARD-0331 · [bug] [node-red] Watchdog silence alert fires once and never re-alerts -- badly understates real outage duration
**Status:** Done

Archived to `core/node-red/card-archive.md` on 2026-09-28 (CARD-0193) — 3796B, over the 2000B size threshold.

---

### CARD-0330 · [enhancement] [logging] Add a credential-free `/status.json` endpoint -- closes Session Start step 9's recurring credential dead-end -- RESOLVED 2026-09-22 16:13 MST
**Status:** Done

Archived to `core/logging/card-archive.md` on 2026-09-28 (CARD-0193) — 3644B, over the 2000B size threshold.

---

### CARD-0329 · [bug] [tos] Full board sweep for `TZ=`-path timestamp contamination — six more found, dating back to 2026-08-14 — RESOLVED 2026-09-22 10:30 MST
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 4401B, over the 2000B size threshold.

---

### CARD-0328 · [enhancement] [mqtt] [node-red] [homeassistant] Version-controlled-copy directories have no drift check — generalize CARD-0326's one-line diff
**Status:** Done

Archived to `core/mqtt/card-archive.md` on 2026-09-27 (CARD-0193) — 19459B, over the 5000B size threshold.

---

### CARD-0327 · [enhancement] [pi1] Extend `log-driver: journald` to the Pi's Docker, the way CARD-0272 did for the M8
**Status:** Backlog

**Raised 2026-09-22 09:40 MST (ops cluster session, Joseph's call — "repo fix now, raise Pi journald as a Backlog card"),** while CARD-0326's config comparison made the asymmetry explicit for the first time. The M8's Docker now logs every container through `journald` (CARD-0272, reboot-verified 2026-09-22); the Pi's still uses Docker's default `json-file` driver. Nothing decided that — CARD-0272 was simply scoped M8-wide and nobody asked the same question of the Pi.

**Why it's plausibly worth doing, and why it is deliberately *not* being assumed:** CARD-0246 already fixed the Pi's `systemd-journald` volatile-storage bug, so the Pi does now have real persistent journal storage — the same precondition that made CARD-0272 a reuse of proven infrastructure rather than a new dependency. The `homeassistant` container's stdout is currently the only record of a whole class of HA startup detail, and CARD-0247's repeated `docker logs --since 10m` timeouts at boot are at least suggestive that reading it through the json-file driver under boot-time I/O contention is not free.

**Real reasons this is not a copy-paste of CARD-0272, to work through at Planning:**
1. **The Pi is not the M8.** It boots from a microSD card, and this repo's standing convention (root `CLAUDE.md`) is to keep write-heavy I/O off it. Where the Pi's journal actually lands — SD-card root filesystem vs. the `/mnt/jctsh-logs` USB drive — must be established *before* pointing container log volume at it. CARD-0246 made the journal persistent; whether it made it persistent on the *right device* is the open question, and the answer decides this card.
2. **CARD-0272's own hard-won finding applies here too** (`JCTsh-Build-Standards.md` §9.9): a `daemon.json` `log-driver` change only takes effect for **newly created** containers — a daemon restart is not enough. `homeassistant` would need a real recreate via the `pi-image-pull.py`/compose path, with real HA downtime, not a trivial restart.
3. **Far smaller blast radius, far more important container.** The M8 had 9 containers, none load-bearing for the house; the Pi has essentially one that matters, and it is Home Assistant.
4. **Journald retention/vacuum** — CARD-0272 left this explicitly unscoped on a host with 300MB+ of proven headroom. On the Pi it's a real question, not a deferrable one.

**Done when:** a decision is recorded either way. Applying it is **not** a foregone conclusion — "checked, and deliberately not doing it because the SD-card I/O cost outweighs the visibility gain" is a legitimate and complete outcome, per this project's explicit-decisions-never-silent-defaults rule.

**Related:** CARD-0272 (the M8-side change this asks whether to mirror; also the source of the recreate gotcha), CARD-0246 (made the Pi's journald persistent — the precondition, and the source of question 1), CARD-0326 (the repo-representation split that surfaced the asymmetry), CARD-0247 (the boot-time `docker logs` timeouts that are weak circumstantial evidence for doing this), `JCTsh-Build-Standards.md` §9.9/§9.10.

---

### CARD-0326 · [enhancement] [docker] Per-host Docker daemon config — the repo tracks only the Pi's, and the two hosts have genuinely diverged — RESOLVED ~~2026-09-22 09:50 MST~~ 2026-09-22 09:49 MST
**Status:** Done

Archived to `core/docker/card-archive.md` on 2026-09-22 (CARD-0193) — 6824B, over the 5000B size threshold.

---

### CARD-0325 · [enhancement] [tos] Cross-session commit sweeps on `tos/kanban-board.md` — commit on completion, never ask, never wait — RESOLVED 2026-09-22 09:49 MST
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 9827B, over the 5000B size threshold.

---

### CARD-0324 · [bug] [logging] An alert-only component's `/status` row pins to its last failure forever — a recovered pipeline is indistinguishable from a still-broken one
**Status:** Done

Archived to `core/logging/card-archive.md` on 2026-09-27 (CARD-0193) — 15486B, over the 5000B size threshold.

---

### CARD-0323 · [bug] [hike-izer-orchestrator] Overpass/Nominatim retry logic ignores HTTP status codes entirely — a 429 is retried like a 504, and the query cadence is what earns the 429 — RESOLVED 2026-09-22 14:58 MST
**Status:** Done

Archived to `components/hike-izer-orchestrator/card-archive.md` on 2026-09-22 (CARD-0193) — 9415B, over the 5000B size threshold.

---

### CARD-0322 · [enhancement] [tos] Component session startup never reads a component's *operating* doc (`SKILL.md`) — RESOLVED 2026-09-22 09:05 MST
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 5568B, over the 5000B size threshold.

---

### CARD-0321 · [enhancement] [tos] Make the live `/kanban` tag selector match the Component/Cluster Registry's clusters — RESOLVED 2026-09-21
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 5927B, over the 5000B size threshold.

---

### CARD-0320 · [idea] [tos] Think through and define the real purpose of each Projects/ repo — RESOLVED 2026-09-20
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 5769B, over the 5000B size threshold.

---

### CARD-0319 · [idea] [hike-izer] Add a photo curation step before sending hike photos to Claude for captioning

**Status:** Backlog

**Raised 2026-09-19, via the auto-PR intake pipeline (PR #116, jctsh-core maintenance check).** Original finding text (voice transcription, garbled): "curate the photos in Emmett before sending to Claude" — "Emmett" = Immich. **Clarified 2026-09-19 (Joseph):** create a curation step for hike pages, before that hike's photos get sent to Claude for captioning.

**Real gap confirmed, not assumed.** Checked `components/hike-izer/fetch_hike_photos.py`'s `search_assets()` — selection is purely a time-window match against the hike's start/end (every Immich asset taken during that window), no quality/relevance filtering at all. Every photo in the window gets captioned and potentially published, with no step for Joseph to exclude a bad, irrelevant, or duplicate shot first.

**Related existing infrastructure, not yet confirmed as directly reusable:** `components/photo-quality-review/` already does library-wide blur/duplicate/broken-image detection (czkawka + sharp) with its own review UI (keep/delete against Immich). That's a whole-library periodic groom, not scoped to one hike's photo set — whether this card should reuse its detection logic, present a similar review UI scoped to just one hike's candidate photos, or use a different mechanism entirely is an open Planning question, not decided here.

**Not yet scoped:**
1. What "curate" means in practice — deleting a photo from Immich outright, or just excluding it from this specific hike page while leaving it in the library?
2. When curation happens — a manual step Joseph does after a hike (before the "rich version" is generated), or an automated pre-filter (blur/duplicate detection) with Joseph only reviewing edge cases?
3. Whether this reuses `photo-quality-review`'s detection code or is a separate, hike-scoped mechanism.

**Done when:** not yet scoped.

**Related:** `components/hike-izer/fetch_hike_photos.py` (`search_assets`, the selection step this curation would sit in front of), `components/photo-quality-review/` (CARD-0028, the closest existing precedent for photo curation against Immich).

---

### CARD-0318 · [idea] [photo-server] Additional Immich widgets/automations — starting with a dynamic geofenced album

**Status:** Backlog

**Raised 2026-09-19, via the auto-PR intake pipeline (PR #115, jctsh-core maintenance check).** Original finding text: "make a repo for photos." **Clarified 2026-09-19 (Joseph):** not a new repo — Immich already lives in `photo-server` (part of the photo-server cluster, alongside `photo-quality-review` and `photo-tv-display`). The actual idea is additional widgets/automations built on top of the existing Immich setup.

**First concrete example given:** a dynamic album/folder that always contains photos falling within a certain geofence (a defined lat/lon boundary), updating automatically as new matching photos land in the library — rather than a manually-curated album.

**Not yet interviewed:** whether this is meant as one specific geofence (e.g. the property itself, or a specific hiking area) or a general mechanism for defining any number of geofenced albums; how "always contains" should behave for photos already in the library before the geofence is defined (backfill vs. forward-only); and whether this uses Immich's own API (`find_or_create_album`-style, per CARD-0286's precedent) or some other mechanism.

**Done when:** not yet scoped.

**Related:** CARD-0286 (Immich album-creation precedent — `find_or_create_album`, the same API surface a geofenced album would likely reuse), `components/photo-server/`, `components/photo-tv-display/routes/immich.js` (existing proven Immich API endpoints).

---

### CARD-0317 · [idea] [tos] Create a new repo for Bible study content — RESOLVED 2026-09-20
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 4283B, over the 2000B size threshold.

---

### CARD-0316 · [idea] [logseq] Reconcile CARD-0034/0071/0072's digital-identity files with LogSeq — deprecate the `[personal]` tag

**Status:** Backlog

**Raised 2026-09-19 (Joseph), out of a live discussion prompted by PR #108's finding** ("for information of certain types automatically send the MD file to LogSeq" — Joseph: "this is what we just did with GitHub issues, but i want to look at `[personal]` tags"). Reviewing the board's 5 `[personal]`-tagged cards (CARD-0294's own "accepted as-is, not retired" call) found none of them were actually a good permanent fit for a generic tag once looked at individually.

**Executed this session, `[personal]` fully retired (zero cards carry it now):**
1. **CARD-0093** (DNS cleanup, `jctnet.com`/`jctnet.net`) → retagged `[network]`. Real operational/network work, not personal-life content.
2. **CARD-0103** (legacy Google Sites migration) → retagged `[website]`.
3. **CARD-0034/CARD-0071/CARD-0072** (digital-identity-protection planning, Joseph and Robin's personal security checklist) → retagged `[logseq]` — this is genuinely personal-life content, belongs with Joseph's LogSeq knowledge base per the same reasoning that moved the wash-survey/night-vision-goggles findings there (PR #102/#104 this session).

**New `network/` directory created** (mirroring `architecture/`'s doc-only shape from CARD-0294) to give `[network]` a real, `archive_cards.py`-discoverable home instead of falling to the dated fallback archive the way `[personal]`/`[wildlife]` still do. `tos/archive_cards.py`'s `discover_destinations()` given an explicit `dests["network"]` entry, same pattern as `architecture`'s own fix. **Existing network-related files moved into it** (Joseph's own catch — "there might be files that belong in the network directory"): `jctsh-network.md`, `jctsh-access.md`, and `keepconnect.md` (a standalone router-rebooter device, network-adjacent even though it's not a JCTsh MQTT component). ~26 active documentation files' cross-references updated to the new `network/` paths; archived card history (`card-archive.md`/`kanban-archive.md` files) deliberately left untouched as historical record, not retrofitted.

**What's still actually open — this card's real remaining scope:** CARD-0071/CARD-0072/CARD-0034 now carry `[logseq]` but **still physically live in `jctsh`'s `kanban-board.md`**, and all three depend heavily on files that also still live in jctsh's repo root (`digital-identity.md`, `digital-identity-protection-checklist.md`, `Incident Response Plan.pdf`) — CARD-0072 explicitly states "Canonical detail lives in `digital-identity-protection-checklist.md`... that file is the actual checklist." **Joseph's explicit call, 2026-09-19: tag and leave in place for now, reconcile properly later** rather than deciding under this same conversation's momentum. Open questions for whenever this gets picked up:
1. Do the three cards move to `LogSeq/kanban-board.md` (matching CARD-0034/0071/0072-in-LogSeq's own numbering) with the reference files moving too, or do the files have a reason to stay in jctsh (e.g., they touch RoboForm/2FA setup for accounts that also gate access to jctsh infrastructure itself — a real "infrastructure-adjacent" argument the wash-survey/night-vision-goggles precedent didn't have to weigh)?
2. If the files move, do they move as-is or get restructured to fit LogSeq's page/journal shape rather than staying standalone `.md` files?

**Done when:** not yet scoped — the retag/directory work above is complete, but the actual file reconciliation this card exists to hold is not.

**Related:** CARD-0294 (originally accepted `[personal]` as-is; this card reverses that call — see the strike-through note added there), CARD-0301 (created the `network/`-adjacent `architecture/` pattern this reuses), PR #102/#104 (this session's own precedent for moving a personal finding to LogSeq instead of landing it in jctsh), `network/README.md`, `tos/archive_cards.py` (`discover_destinations()`).

---

### CARD-0315 · [idea] [tos] Cross-repo protocol management — a general session that spans Projects/, and whether a dedicated TOS repo is eventually needed

**Status:** Backlog

**Raised 2026-09-19 (Joseph), out of a live discussion prompted by adding LogSeq's own editing-protocol rules.** While setting up a `tos/` directory for LogSeq (mirroring jctsh's own), Joseph asked how to reconcile what belongs in each repo's `tos/` versus something shared — noting that jctsh's 9-step Session Start (`tos/JCTsh-Session-Start.md`, CARD-0307) doesn't actually look jctsh-specific in its general shape (checking for uncommitted work, checking for a stray unmerged branch, reviewing open PRs) — it's a general "how does a Claude Code session start responsibly" pattern that LogSeq and PB-Blog would each plausibly want their own version of too.

**The bigger picture Joseph is envisioning, not yet built:** a **general session that runs at the `Projects/` parent level and works across all three repos** — exactly the shape this session has actually been operating in today (jumping between jctsh, LogSeq, and back, handling the auto-PR intake queue, moving a finding to whichever repo it actually belongs on). Today that happened organically, session-by-session, with no standing definition of what such a session's own "start" procedure or cross-repo responsibilities should be.

**Open question, deliberately not decided yet (Joseph: "I'm not sure at this point"):** whether this eventually warrants a **dedicated TOS repo** — a fourth repository (or some other durable, versioned location) holding protocols genuinely shared across jctsh/LogSeq/PB-Blog (and any future addition to this `Projects/` family), separate from truly universal preferences (which belong in the user's global `~/.claude/CLAUDE.md`, already established) and from protocols genuinely specific to one repo (which stay in that repo's own `tos/`).

**Interim call made in the same discussion, not blocking this card:** a repo-specific rule found live this session ("steps/rules/protocols belong in dedicated `.md` files, never inlined in `CLAUDE.md` — `CLAUDE.md` only points at them") was judged to be a truly universal preference, not repo-specific, and destined for the global `~/.claude/CLAUDE.md` rather than repeated per-repo. This card is about the harder, still-open middle tier — protocols shared by *some* repos (or by a cross-repo session) but not universal to every project.

**Not yet scoped:** what would actually need to live in a TOS repo if one existed (a shared Session Start template? a cross-repo card-numbering or PR-triage convention, like the one this exact session used to move findings between jctsh and LogSeq today?) — real examples exist now (this session lived them), but nothing has been abstracted into a reusable definition yet.

**Second interim call, same discussion, 2026-09-19 — where to put the "protocol placement" meta-rule itself while this card stays open.** Wrote `tos/Protocol-Placement.md` (this repo) as the working answer for the still-open middle tier (protocols shared by *some* repos but not universal to every project Joseph works in) — **reusing `jctsh/tos/` as the pragmatic default for now** rather than inventing a new shared location before a second real need for one shows up, per Joseph's own call ("for now i thought we would keep using jctsh/tos unless we want to put it somewhere else"). Global `~/.claude/CLAUDE.md` now points at it. This is explicitly provisional — if this card ever produces a real dedicated shared location, `Protocol-Placement.md`'s own content (not just this card) would need to move too.

**Third interim call, 2026-09-20 (Joseph, from a LogSeq-scoped component session asking to run `JCTsh-Component-Session-Start.md`'s startup) — LogSeq added as a row in that document's Component/Cluster Registry**, a single-"component" cluster like `tos`/`architecture` (the whole separate repo is the "component," per Joseph's explicit choice when asked whether to add the row, run LogSeq's startup self-contained instead, or resolve this card first). Real mismatch surfaced, not smoothed over: the registry's 9-step table (steps 1/2/3/5/6/9) was written assuming jctsh's own shared `kanban-board.md` and git tree — scoped to LogSeq, those steps now need to point at LogSeq's own `kanban-board.md`/repo instead, which uses a different one-bracket card format (CARD-0313's own finding) and no jctsh-style component tags to scope by. Steps 4 (auto-PR intake) and 8 (`archive_cards.py` dry run) don't apply to LogSeq at all — no such pipeline/script exists there. **This is a real instance of the bigger question this card holds, not a resolution of it** — the registry now has a working entry for LogSeq, but whether a whole separate repo really belongs in jctsh's own component registry (vs. LogSeq having its own equivalent document, vs. some future shared location) stays exactly as open as before.

**Done when:** not yet scoped — this card exists to hold the question, not to answer it prematurely.

**Related:** CARD-0307 (created `tos/JCTsh-Session-Start.md`, the concrete example prompting this question), CARD-0301 (created the `Projects/` parent directory this card's "general session" concept would run at), CARD-0310 (the most recent addition to jctsh's own Session Start, itself a candidate for what a shared protocol might look like), `Projects/README.md` (today's lightweight, non-versioned answer to "orient a session starting at Projects/" — a stopgap this card's eventual answer might supersede), `tos/Protocol-Placement.md` (the interim middle-tier answer living here until/unless this card changes that), `tos/JCTsh-Component-Session-Start.md` (the Component/Cluster Registry LogSeq was added to, third interim call above).

---

### CARD-0314 · [bug] [hike-izer] Reported "elevation gain" is actually elevation range (max−min), not cumulative ascent

**Status:** Backlog

**Raised 2026-09-19, via the auto-PR intake pipeline (PR #105, jctsh-core maintenance check).** Original finding text: "for the hiking statistic elevation gain how is that calculated." Started as a general question, not a bug report — checking the actual code to answer it surfaced a real discrepancy.

**General practice, for reference:** "elevation gain" (cumulative gain / total ascent) is normally the **sum of every positive elevation change** between consecutive track points along a route — descents are tracked separately as "elevation loss," not subtracted from gain. It equals simple `max − min` only in the special case of a route that climbs the whole way with no dips. Because raw GPS/barometric altitude is noisy (several meters of jitter even stationary), a correct implementation smooths the elevation profile or applies a minimum-delta threshold before summing positive deltas — naively summing every raw point-to-point delta would wildly overstate gain from noise alone.

**Real bug found, checking the actual code rather than assuming:** `components/hike-izer/fetch_hike_data.py`'s `compute_stats()` (line ~287) computes:
```python
'gain_ft': round(m_to_ft(max(alt_vals) - min(alt_vals)))
```
This is elevation **range**, not cumulative ascent. For any hike with rolling terrain (up-down-up-down, not a single monotonic climb), this understates true total ascent — potentially significantly, depending on how much up-and-down the route actually has.

**Real cross-dependency found, not incidental:** CARD-0287 (Mile Announcer's planned spoken cumulative-elevation-gain feature) explicitly designed itself to "match how hike-izer's own stats report gain" and its own Done-when criterion is to be "cross-checked against hike-izer's own published elevation-gain stat for that hike." Fixing this bug changes what that reference value actually is — CARD-0287 should build against the corrected calculation, not the current max−min one, and its own Done-when should be re-confirmed once this lands. Noted on CARD-0287 directly.

**Not yet scoped:**
1. The actual fix — sum positive deltas between consecutive `altitude_m` GPS readings, with a noise-reduction pass (smoothing or a minimum-delta threshold) tuned against real hike data, same discipline as this project's other noise-vs-signal thresholds (e.g. CARD-0250's walking-speed classifier).
2. Whether to also report elevation *loss* alongside gain, now that the two are no longer trivially the same number (`max−min` conflated them; a real cumulative-gain calculation naturally produces both separately).
3. Whether past hikes' already-published gain figures should be recomputed/corrected, or only hikes generated after the fix.

**Done when:** not yet scoped.

**Related:** CARD-0287 (Mile Announcer's planned elevation announcement — depends on this card's corrected value), `components/hike-izer/fetch_hike_data.py` (`compute_stats`), CARD-0250 (the precedent for a real noise-vs-signal threshold tuned against real hike data).

---

### CARD-0313 · [enhancement] [tos] Add LogSeq and PB-Blog swimlanes to the live `/kanban` dashboard — RESOLVED 2026-09-19
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 8422B, over the 5000B size threshold.

---

### CARD-0312 · [idea] [photo-server] Sync photo deletions from Google Photos to Immich

**Status:** Backlog

**Raised 2026-09-19, via the auto-PR intake pipeline (PR #101, jctsh-core maintenance check).** Original finding text (voice transcription, garbled): "when I delete a photo out of Google photos I wanted to delete out of iMac as well." **Clarified 2026-09-19 (Joseph): "iMac" = Immich, "delete out of Immich too."** When a photo already imported into Immich is later deleted from Google Photos, it stays orphaned in Immich — nothing currently removes it.

**Real gap confirmed, not assumed:** checked `components/photo-server/operations.md` — the existing `immich-go` integration is a **one-time Google Takeout migration** (a folder-upload batch job), not an ongoing sync. Nothing in this repo watches Google Photos for live changes (additions or deletions) at all.

**Not yet scoped — open questions before Planning:**
1. Is Google Photos still the active capture app for new photos day-to-day, or was it only ever the source of the original migration batch (i.e., is this "watch an actively-growing library for deletions" or "clean up strays from one historical import")? Very different scope depending on the answer.
2. Does the Google Photos API expose a practical way to detect deletions at all (vs. only listing currently-existing items, requiring a diff against a prior snapshot)?
3. Matching mechanism: how would a Google Photos item be reliably matched to its corresponding Immich asset (checksum, filename+timestamp, the `immich-go` import-batch tag already applied)?

**Done when:** not yet scoped.

**Related:** `components/photo-server/operations.md` (`immich-go`'s existing one-time migration, the closest precedent), `components/photo-server/migration.md`.

---

### CARD-0311 · [enhancement] [hike-izer] Hike pages don't name the trail/trailhead, despite existing Overpass lookup infrastructure
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-27 (CARD-0193) — 26750B, over the 5000B size threshold.

---

### CARD-0310 · [enhancement] [tos] Session Start: check for unmerged remote branches with real work, not just local uncommitted changes
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 2535B, over the 2000B size threshold.

---

### CARD-0308 · [idea] [hike-izer] Scat identification from hike photos — analogous to BirdNET's audio wildlife ID
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-27 (CARD-0193) — 15667B, over the 5000B size threshold.

---

### CARD-0309 · [enhancement] [tos] Add a PR review checklist for the auto-PR intake pipeline
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 5279B, over the 5000B size threshold.

---

### CARD-0307 · [enhancement] [tos] Split the general Session Start checklist out of CLAUDE.md; orient sessions starting at the Projects/ parent directory
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 3046B, over the 2000B size threshold.

---

### CARD-0306 · [bug] [data-pipeline] Environmental Data pipeline overwrites a stationary device's own coordinates with the hiker's live GPS during a hike
**Status:** Done

Archived to `core/data-pipeline/card-archive.md` on 2026-09-22 (CARD-0193) — 14533B, over the 5000B size threshold.

---

### CARD-0305 · [retracted] Moved to PB-Blog's own kanban-board.md as CARD-0001 — was: Decide how the PB Blog monthly workflow relates to its new repo

**Status:** Retracted

**Opened 2026-09-18, moved same day (Joseph's call).** Raised right after CARD-0298 created the `PB-Blog` repo, before that repo had its own `kanban-board.md` bootstrapped — Joseph's direction: this is PB-Blog's own process question, not jctsh's, and belongs on PB-Blog's own board now that one exists. No content lost — the full card (raised-context, the Watch-for marker on Pastor Ben's November files, done-when criteria) moved verbatim to `PB-Blog/kanban-board.md` CARD-0001.

**Related:** `PB-Blog/kanban-board.md` CARD-0001 (where this card actually lives now), CARD-0298 (the move that created the repo this question is about).

---

### CARD-0304 · [enhancement] [tos] Reconcile and fill gaps in JCTsh-Operating-System.md's stated principles — RESOLVED 2026-09-18
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 10044B, over the 5000B size threshold.

---

### CARD-0303 · [enhancement] [tos] Reconcile root CLAUDE.md against JCTsh-Operating-System.md and JCTsh-Build-Standards.md — RESOLVED 2026-09-18
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 7592B, over the 5000B size threshold.

---

### CARD-0302 · [retracted] Folded into CARD-0294 — was: Reconcile every kanban tag against the actual directory structure

**Status:** Done

**Opened, then found to duplicate an existing card, same session, 2026-09-18.** Created without first checking whether this work was already tracked — a real process miss, the exact "investigate existing patterns first" failure this project's Engineering Discipline rule exists to catch, applied to card creation itself rather than code. **CARD-0294**, opened earlier the same day, already covers this ground and goes further (fixes CARD-0280's title-formatting bug, retags host-specific `[infrastructure]` cards to `[m8]`/`[pi1]`, proposes a new `architecture/` directory for cross-cutting cards, retires `[infrastructure]` entirely). Findings folded into CARD-0294 rather than lost: see its own text for the four non-`infrastructure` retags this card found independently (`kanban-board`→`tos`, `log-server`→`logging`, `immich`→`photo-server`, `core`→`data-pipeline`) and the five planned-component tags confirmed legitimate. Kept as a stub, not deleted, since the card number may already be referenced elsewhere.

**Follow-on, same session — the retraction convention itself was undocumented.** Joseph asked what the actual retract protocol was; answer was "none, purely pattern-matched from CARD-0252/0253." Formalized into `JCTsh-Operating-System.md`'s State Transitions section (→ v1.16) as a "Retracting a card" note, distinct from Defer.

**Related:** CARD-0294 (the real, more complete card this folds into), `JCTsh-Operating-System.md` (State Transitions — "Retracting a card," now documented).

---

### CARD-0300 · [retracted] Moved to LogSeq's own kanban-board.md as CARD-0002 — was: Document the existing process for daily devotional LogSeq entries

**Status:** Retracted

**Opened 2026-09-18, moved same day (Joseph's call).** LogSeq now has its own repo and `kanban-board.md` (CARD-0297) — this is LogSeq's own process question, not jctsh's. No content lost — the full card (raised-context, open questions, done-when) moved verbatim to `Projects\LogSeq\kanban-board.md` CARD-0002.

**Related:** `Projects\LogSeq\kanban-board.md` CARD-0002 (where this card actually lives now), CARD-0297 (the move that created the repo this question is about), CARD-0293 (its sibling, also retracted and moved, to CARD-0001 in the same board).

---

### CARD-0299 · [enhancement] [tos] Table defining which components each component/cluster session covers — RESOLVED 2026-09-18
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 6027B, over the 5000B size threshold.

---

### CARD-0301 · [idea] [tos] Establish a `Projects/` parent directory for jctsh, LogSeq, and the Pastor Ben blog repos — RESOLVED 2026-09-18
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 8149B, over the 5000B size threshold.

---

### CARD-0298 · [idea] [tos] Move the Pastor Ben blog file/directory system into a repo — RESOLVED 2026-09-18
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 8339B, over the 5000B size threshold.

---

### CARD-0297 · [idea] [tos] Move the LogSeq file system into a repo — RESOLVED 2026-09-18
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 7405B, over the 5000B size threshold.

---

### CARD-0296 · [idea] [tos] Set up remote access for running Claude Code sessions away from the desktop — RESOLVED 2026-09-20
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 3844B, over the 2000B size threshold.

---

### CARD-0352 · [enhancement] [m8] Pin cloudflared to an explicit version instead of `:latest`
**Status:** Done

Archived to `hosts/m8/card-archive.md` on 2026-09-28 (CARD-0193) — 3326B, over the 2000B size threshold.

---

### CARD-0295 · [enhancement] [homeassistant] Home Assistant container update available: 2026.9.2 → 2026.9.3
**Status:** Done

Archived to `core/homeassistant/card-archive.md` on 2026-09-27 (CARD-0193) — 8650B, over the 5000B size threshold.

---

### CARD-0294 · [enhancement] [tos] Reconcile kanban-board.md tags against the real directory structure, retiring the [infrastructure] tag
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 10669B, over the 5000B size threshold.

---

### CARD-0293 · [retracted] Moved to LogSeq's own kanban-board.md as CARD-0001 — was: Develop a method to post daily devotional notes into LogSeq

**Status:** Retracted

**Opened earlier (auto-opened from PR #90), moved 2026-09-18 (Joseph's call).** LogSeq now has its own repo and `kanban-board.md` (CARD-0297) — this is LogSeq's own process question, not jctsh's. No content lost — the full card (raised-context, open questions, done-when) moved verbatim to `Projects\LogSeq\kanban-board.md` CARD-0001.

**Related:** `Projects\LogSeq\kanban-board.md` CARD-0001 (where this card actually lives now), CARD-0297 (the move that created the repo this question is about), CARD-0300 (its sibling, also retracted and moved, to CARD-0002 in the same board).

---

### CARD-0292 · [enhancement] [tos] Split a document's own version-history out of its header into a sibling `<Doc>-History.md`
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 3625B, over the 2000B size threshold.

---

### CARD-0291 · [enhancement] [tos] Audit every component/core/host README.md and CLAUDE.md against what they're actually supposed to contain — ~~RESOLVED 2026-09-18~~ ~~REOPENED 2026-09-22 08:50 MST~~ RESOLVED 2026-09-22 09:56 MST
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 27790B, over the 5000B size threshold.

---

### CARD-0290 · [enhancement] [tos] Split archived card history out of component CLAUDE.md files into a dedicated card-archive.md — RESOLVED 2026-09-17 20:31 MST
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-18 (CARD-0193) — 7752B, over the 5000B size threshold.

---

### CARD-0289 · [idea] [tos] Documentation-splitting principle — split by read-frequency, keep cross-references current — RESOLVED 2026-09-17
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-18 (CARD-0193) — 5758B, over the 5000B size threshold.

---

### CARD-0288 · [idea] [tos] Session card-selection criteria — which card to pick up next, distinct from the Priority tag — RESOLVED 2026-09-17
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 4160B, over the 2000B size threshold.

---

### CARD-0287 · [enhancement] [hiking-monitor] Extend Mile Announcer with a spoken cumulative elevation-gain figure

**Status:** Backlog

**Auto-opened from jctsh-core's maintenance check (PR #88).** Raw finding (garbled in the original capture): "mileage not mileage elevation announcer." Clarified 2026-09-17 (Joseph): wants CARD-0208's existing Mile Announcer (Tasker TTS on the Pixel, currently speaks "one mile," "two miles," etc.) to also speak cumulative elevation gain at each mile mark.

**Interviewed 2026-09-17 (Joseph):** kept as its own new card rather than folded into CARD-0208 -- CARD-0208's own audibility bug (the `Volume` action that kept not sticking) is confirmed fixed, so this builds on a working base, not a still-flaky one. Elevation figure: cumulative gain since the hike started, matching how hike-izer's own stats report gain -- not current altitude.

**Scope:** extend the "Mile Announcer" Tasker task (`components/hiking-monitor/tasker/Mile-Announcement.prf.xml`) to also track cumulative elevation gain and speak it alongside the mile count, e.g. "Two miles, three hundred feet gained."

**Open question, not yet resolved:** where cumulative elevation gain is sourced from on-device during a live hike (GPSLogger's own altitude field vs. barometric pressure via hiking-monitor's BME280) -- needs a real design pass before building, same as CARD-0208's own original design sketch.

**Real dependency found, 2026-09-19 (CARD-0314) — this card's own reference value is currently wrong.** This card's "Interviewed" note above and its Done-when both anchor to "hike-izer's own published elevation-gain stat" — but CARD-0314 found that stat (`fetch_hike_data.py`'s `gain_ft`) is actually elevation *range* (`max − min`), not real cumulative ascent, and is getting fixed. **Don't build or validate this card against the current (buggy) figure** — wait for CARD-0314's corrected calculation, or this card's own on-device figure will "match" a wrong reference and both will be wrong together instead of one fixing the other.

**Done when:** a real hike shows every whole-mile crossing announced audibly with both the mile count and a correct cumulative elevation-gain figure, cross-checked against hike-izer's own published elevation-gain stat for that hike **(once CARD-0314's fix lands — see dependency above)**.

**Related:** CARD-0208 (Mile Announcer, the base this extends), CARD-0314 (fixes the elevation-gain calculation this card depends on as its own reference/validation value), `components/hiking-monitor/tasker/Mile-Announcement.prf.xml`, `components/hiking-monitor/hiking-monitor.yaml` (BME280 pressure/altitude sensor).

---

### CARD-0286 · [enhancement] [hike-izer] Auto-create an Immich Album per hike, populated with that hike's photos
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-22 (CARD-0193) — 6546B, over the 5000B size threshold.

---

### CARD-0285 · [enhancement] [hike-izer] Carry air-quality-monitor's sensor data through the pipeline and onto the hike-izer web page — RESOLVED 2026-09-28
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-29 (CARD-0193) — 13737B, over the 2000B size threshold.

---

### CARD-0284 · [idea] [tos] Persistent per-cluster Claude Code sessions — faster ramp-up and cross-work pattern recognition, without a second knowledge store — RESOLVED 2026-09-18
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 22613B, over the 5000B size threshold.

---

### CARD-0283 · [enhancement] [tos] Concurrent-session editing: reread kanban-board.md only on a failed Edit, not before every edit — RESOLVED 2026-09-17
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 2764B, over the 2000B size threshold.

---

### CARD-0282 · [enhancement] [tos] Session Start's log dashboard check should use the live `/status` page, not raw `jctsh.log` grep — RESOLVED 2026-09-17
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 2921B, over the 2000B size threshold.

---

### CARD-0281 · [bug] [garage-radar] Dashboard logging silent 2026-06-15 to ~09-10, self-recovered on its own reboot — RESOLVED 2026-09-17 (self-recovered, root cause unconfirmed)
**Status:** Done

Archived to `components/garage-radar/card-archive.md` on 2026-09-18 (CARD-0193) — 5500B, over the 5000B size threshold.

---

### CARD-0280 · [bug] [salt-sensor] Move Salt Sensor's tab-scoped HA_TOKEN to the systemd-level environment file, closing the exact gap that bit CARD-0261 — RESOLVED 2026-09-17
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-18 (CARD-0193) — 5918B, over the 5000B size threshold.

---

### CARD-0279 · [bug] [data-pipeline] Field-mode replay burst overwhelms Apps Script's per-reading GPS lookup — missing coordinates scale with reading volume
**Status:** Done

Archived to `core/data-pipeline/card-archive.md` on 2026-09-22 (CARD-0193) — 11118B, over the 5000B size threshold.

---

### CARD-0278 · [enhancement] [hike-izer] Wildlife list/player UX — sticky heading, in-page audio player for hike-page species clips — RESOLVED 2026-09-17 22:34 MST
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-18 (CARD-0193) — 5878B, over the 5000B size threshold.

---

### CARD-0277 · [enhancement] [hiking-monitor] Enclosure reprint — field-damaged shells, plus a second carabiner ear

**Status:** Build

**Raised 2026-09-16 (Joseph).** The hiking-monitor's enclosure was damaged in a hiking mishap — physically cracked/broken shell(s) in the field, not a firmware or electrical fault. Reprinting a replacement, and adding a second carabiner ear to the design (the original enclosure had one bail; this print adds a second) while already back in Tinkercad for the repair.

**Design and export done, 2026-09-16.** New STL exports committed: `components/hiking-monitor/enclosure/hiking-monitor bottom shell 2.stl` and `hiking-monitor upper shell 3.stl` (Tinkercad's own default export naming — not the project's established `-raw`/`-final` convention from the original CARD-0009 build, since these came directly from a live Tinkercad edit session rather than the OpenSCAD/Tinkercad two-tool pipeline). Printing scheduled at Xerocraft, per this project's established print venue (same Centauri Carbon / ASA pattern as the original build).

**Done when:** the new shells are printed, the existing electronics (perfboard, LiPo, display, TP4056) are reassembled into them, and the device is confirmed working post-reassembly (same bar as CARD-0009's own "Don't close until" — I2C/sensor re-verification after reassembly) — plus the second carabiner ear physically accepts a carabiner without flexing excessively, matching `hiking-monitor-enclosure-plan.md`'s existing bail success criteria.

**Related:** CARD-0009 (original enclosure build, closed — this is a real physical repair/revision of that same enclosure, not a from-scratch redesign), `components/hiking-monitor/hiking-monitor-enclosure-plan.md`, `components/hiking-monitor/enclosure/`.

---

### CARD-0276 · [bug] [hike-izer-orchestrator] Wildlife-detection archive-to-Sheets 404 on 2026-09-15, no retry protection on this write path
**Status:** Done

Archived to `components/hike-izer-orchestrator/card-archive.md` on 2026-09-22 (CARD-0193) — 13102B, over the 5000B size threshold.

---

### CARD-0275 · [bug] [hike-izer-orchestrator] 2026-09-15 hike-izer intake incident — hike-end + BirdNET webhooks failed, backstop probe 404'd, all recovered — RESOLVED 2026-09-15 11:50 MST
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-16 (CARD-0193) — 8287B, over the 5000B size threshold.

---

### CARD-0274 · [enhancement] [photo-server] Immich update available — v3.2.0 → v3.2.2
**Status:** Done

Archived to `components/photo-server/card-archive.md` on 2026-09-28 (CARD-0193) — 4201B, over the 2000B size threshold.

---

### CARD-0273 · [enhancement] [hike-izer-orchestrator] hike-izer-orchestrator: split print() output into stdout (routine) vs. stderr (worth a look)
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-16 (CARD-0193) — 8255B, over the 5000B size threshold.

---

### CARD-0272 · [enhancement] [m8] M8-wide: switch Docker's logging driver to journald, reusing the M8's already-persistent journal — RESOLVED 2026-09-22 08:55 MST
**Status:** Done

Archived to `hosts/m8/card-archive.md` on 2026-09-22 (CARD-0193) — 8491B, over the 5000B size threshold.

---

### CARD-0271 · [enhancement] [hiking-monitor] Experiment: benchmark Pl@ntNet against Claude's existing photo-caption plant IDs
**Status:** Planning

**Raised 2026-09-14 (Joseph), as a follow-on from CARD-0232's real finding** that CARD-0107's existing `photo_captions.py` pipeline already does species-level plant ID via `claude-opus-4-8` — the open design question is whether a dedicated plant-ID API (Pl@ntNet, per CARD-0232's research) actually beats that existing baseline enough to be worth integrating, or whether CARD-0232 should just extend `photo_captions.py` directly.

**Interviewed 2026-09-14 (Joseph), via AskUserQuestion:**
1. **Scope: the 64 real desert-hike plant photos already identified** (CARD-0232's own hand-classified count, hikes 2026-08-13 onward) — reuses photos Claude has already captioned, so those captions serve as a free, real comparison baseline. Deliberately excludes the Meijer Gardens cultivated-garden photos (not representative of Pl@ntNet's wild-plant training strength) and the 16 wildlife-primary/28 non-plant captions (out of scope for a plant-ID benchmark).
2. **Cost: ~$0.51** (64 photos × Pl@ntNet's ~$8/1,000 pay-per-event pricing) — confirmed trivial, no budget concern.
3. **Done when: a real comparison table + a go/no-go recommendation** — not just confirming the API works. Send each of the 64 photos to Pl@ntNet, record its returned species + confidence score, compare against Claude's existing caption for that same photo (agreement rate, cases where one names a species the other missed or got wrong, cases where Pl@ntNet's confidence is notably low/high), and conclude with a clear recommendation on CARD-0232's two design directions: extend `photo_captions.py` alone, or add Pl@ntNet as a second-opinion/confidence layer.

**Scope for Build:** a throwaway script (not part of the deployed pipeline) that reads the 64 photos' thumb files from the M8 (`/home/jct/hike-izer-web-app/srv/*_photos/`), calls Pl@ntNet's API for each, and produces the comparison table. Needs a Pl@ntNet account/API key obtained first (per CARD-0232's research, no key needed for very light basic use, but confirm the real limit before running 64 calls).

**Not yet scoped:** whether this script becomes throwaway (run once, findings folded into CARD-0232, script discarded) or worth keeping around for future re-benchmarking (e.g. if Plant.id is tried later) — decide at Build once the comparison is in hand.

**Grass species called out as a specific thing to look for, 2026-09-19 (Joseph, via PR #100's auto-opened finding "grass species" — folded in here rather than landed as its own card, since it's a scoping note on this experiment, not a separate idea).** Grasses are a known-hard case for visual species ID (subtle, overlapping morphological differences) — worth specifically checking within the 64-photo comparison whether Pl@ntNet or Claude's existing captions actually distinguish grass species at all, or both just genericize to "grass"/"bunchgrass," rather than only noticing this gap after the benchmark is already done.

**Related:** CARD-0232 (the design question this experiment resolves), `components/hike-izer-orchestrator/photo_captions.py` (the existing baseline this benchmarks against).

---

### CARD-0270 · [enhancement] [hike-izer-orchestrator] Structured, queryable per-hike API cost data — a dedicated Sheet, not a substring in a notification message — RESOLVED 2026-09-22 19:13 MST
**Status:** Done

Archived to `components/hike-izer-orchestrator/card-archive.md` on 2026-09-27 (CARD-0193) — 12479B, over the 5000B size threshold.

---

### CARD-0269 · [enhancement] [pi1] Scriptable, ionice-wrapped `ctr`-based image-pull for the Pi — schedulable, first real use run manually — RESOLVED 2026-09-14 09:50 MST
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-16 (CARD-0193) — 7099B, over the 5000B size threshold.

---

### CARD-0268 · [bug] [pi1] Docker pulls on the Pi can starve HA's own I/O on the shared USB 2.0 bus — real, not hypothetical — RESOLVED 2026-09-14 10:05 MST via CARD-0269
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-16 (CARD-0193) — 9158B, over the 5000B size threshold.

---

### CARD-0267 · [enhancement] [photo-server] Immich update available: v3.1.0 → v3.2.0 — RESOLVED 2026-09-14 08:30 MST
**Status:** Done

**Raised via automated maintenance finding (PR #75, photo-server), 2026-09-11.** Routine version-bump finding: Immich v3.2.0 available, running v3.1.0.

**Evaluated 2026-09-13 — release notes checked, looks safe, not applied yet (Joseph's call — evaluate first, decide separately whether/when to apply).** v3.2.0 is a minor release: docker compose builder, revamped search UI/API, cross-user people clustering, workflow tags, a dedicated memories page, tag renaming, map viewport asset view. No "Breaking Changes" section in the release notes; the only migration-adjacent item is a new hint logged when a DB migration is missing on downgrade — a safety improvement, not something requiring action on upgrade. Nothing found that touches this instance's own setup (storage paths, auth, `immich-go` import tooling) in a way that would need pre-upgrade prep.

**Applied and verified 2026-09-14 08:30 MST, per Joseph's explicit go-ahead ("apply updates for 266 and 267, let scheduled reboot handle it").** `docker compose pull && docker compose up -d` on the M8 — pulled and recreated cleanly, no issues (M8's NVMe storage has none of the Pi's USB-bus contention problems that complicated CARD-0266's HA update). Verified live: API `/api/server/version` returned `{"major":3,"minor":2,"patch":0,"prerelease":null}`, container healthy, logs clean.

**Related:** CARD-0128 (the auto-PR intake pipeline this came through), `components/photo-server/README.md`.

---

### CARD-0266 · [enhancement] [homeassistant] Home Assistant update available: 2026.9.1 → 2026.9.2 — RESOLVED 2026-09-14 09:20 MST
**Status:** Done

Archived to `core/homeassistant/card-archive.md` on 2026-09-28 (CARD-0193) — 4480B, over the 2000B size threshold.

---

### CARD-0265 · [bug] [logging] Dashboard still unreadably dark after the earlier brightness fix — RESOLVED 2026-09-12 MST (transient tab state, not a persistent cause)
**Status:** Done

Archived to `core/logging/card-archive.md` on 2026-09-28 (CARD-0193) — 4468B, over the 2000B size threshold.

---

### CARD-0264 · [idea] [architecture] Decision criteria: when (if ever) to add a Zigbee2MQTT/Z-Wave USB coordinator to bring legacy hardware under HA

**Status:** Backlog

**Raised 2026-09-12 MST, from a discussion following CARD-0164's SmartThings-deprecation plan.** That plan deliberately leaves the existing Zigbee/Z-Wave device population (most lights, sensors, the lock) SmartThings-hosted and invisible to HA once the API access lapses — the only way to bring a specific one of those devices back under HA visibility/control is to physically move it off the SmartThings hub onto radio hardware HA can talk to directly (a Zigbee2MQTT or Z-Wave JS UI USB coordinator, one-time hardware, no subscription).

**Concrete product options, researched 2026-09-12/13 (corrected 2026-09-13 — the original Zigbee pick, ZBT-1, is discontinued):**

| Radio | Product | Price | Notes |
|---|---|---|---|
| Zigbee only | **Sonoff ZBDongle-E** | ~$20-25 | Older EFR32MG21 chip, no Thread. Cheapest option, well-proven with Zigbee2MQTT (fits this project's existing MQTT-centric architecture directly); aluminum casing doubles as a heatsink. |
| Zigbee + Thread | **SONOFF Dongle Plus MG24** | ~$33-36 | **Best pick if Thread might ever matter** — same newer Silicon Labs MG24 chip as HA's own ZBT-2 (4× faster than the EFR32MG21 above), includes a USB extension cable, notably cheaper than the official Nabu Casa stick for essentially the same capability. Runs Zigbee *or* Thread on the unit, presumably not both simultaneously (same single-radio constraint as every other MG24-based stick, including HA's own ZBT-2). |
| Zigbee + Thread (official) | **HA Connect ZBT-2** (replaces the discontinued ZBT-1) | $49 | Same MG24 chip as the Sonoff MG24 above, at a real premium — the only edge is native firmware-update integration in HA's own UI, being Nabu Casa's first-party hardware. |
| Z-Wave | **Zooz ZST10** or **Aeotec Z-Stick 7** | $40-60 | Either works for the real Z-Wave garage door sensor identified in CARD-0260's own work (see `components/automatic-garage-door-opener-closer/auto-garage-door-system.md`). |
| Z-Wave + Zigbee/Thread/BLE combo | **Z-Station** (Z-Wave.me) | ~€126 (~$135-140) | Real combo device, two radios, but the second radio is firmware-selectable one-protocol-at-a-time. Only worth the premium if consolidating onto one physical stick matters more than cost — with 3 free USB ports (see below), it usually doesn't. |

**Revised recommendation, given the Sonoff MG24 option:** since it costs only ~$10-15 more than the Thread-less ZBDongle-E and is meaningfully cheaper than HA's own ZBT-2 for the same chip, **the Sonoff Dongle Plus MG24 is the better default pick even without a concrete Thread need today** — cheap insurance against needing a second stick later. If Thread capability is wanted after already owning a Zigbee-only stick, no downside either way: a Thread border router is just a separate, independent piece of hardware (its own USB stick), and there's a free USB port to spare regardless (see below).

**Not a plan to do this — a decision rule for if it ever comes up.** There's no reason to buy this hardware or migrate anything speculatively. The trigger is wanting real HA capability (dashboard, automation, Node-RED logic) over one *specific* device that's currently ST-hosted. When that happens, check in this order before reaching for a USB coordinator:
1. Does that specific device have a Matter path — native Matter support, or a manufacturer bridge/firmware update to Matter? If yes, that's the preferred route (matches the already-established HA-first Matter registration order, `JCTsh-Build-Standards.md` §6.4/CARD-0262) — no new radio hardware, no per-device re-pairing onto a coordinator.
2. Only if no Matter path exists for that device does a USB Zigbee/Z-Wave coordinator become the actual option — and even then, it's a per-device re-pairing job (leave the SmartThings network, join the new coordinator's network), not a bulk migration.

**USB port availability, checked 2026-09-12 — not a blocker, but a real caveat if step 2 is ever reached.** The Pi is a Raspberry Pi 3B+: 4 USB 2.0 ports total, only 1 currently used (the `jctsh-logs` drive, `/dev/sda1` — CARD-0159). The CARD-0060 cooling fan on the same shelf draws from its own wall adapter, not a Pi port, so it doesn't count against this. 3 ports free — enough for a Zigbee coordinator, or even both a Zigbee and a Z-Wave stick. Caveat: all 4 ports share a single internal USB 2.0 hub with the onboard Ethernet controller (no USB 3.0 on this board) — a new coordinator's traffic and the `jctsh-logs` drive's I/O would compete on that same shared bus under heavy load, unlike a Pi 4/5's independent USB 3.0 lanes. Not a reason to avoid this, just worth remembering if a coordinator is ever added and something on that bus seems slower than expected.

**Done when:** N/A as scoped — this card exists to hold the decision criteria above so it isn't re-derived from scratch next time a specific device's HA-visibility gap actually matters. Revisit/close or convert to real work only when a concrete device triggers it.

**Related:** CARD-0164 (the deprecation plan this is the fallback option for), `JCTsh-Build-Standards.md` §6.4 (Matter registration order), CARD-0262 (Matter Server infrastructure, needed either way for the Matter-first check in step 1).

---

### CARD-0263 · [enhancement] [pi1] Switch the Pi from graphical boot target to headless — RESOLVED 2026-09-12 MST (already true, not what was assumed)
**Status:** Done

Archived to `hosts/pi1/card-archive.md` on 2026-09-28 (CARD-0193) — 4981B, over the 2000B size threshold.

---

### CARD-0262 · [enhancement] [homeassistant] Set up HA's native Matter integration; re-register the 3 Cync lights through HA instead of directly in Google Home — RESOLVED 2026-09-12 MST
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-16 (CARD-0193) — 10561B, over the 5000B size threshold.

---

### CARD-0261 · [enhancement] [salt-sensor] Replace SmartThings-synced switches with HA-native helpers + HA's own Google Assistant bridge — RESOLVED 2026-09-12 MST
**Status:** Done

Archived to `components/salt-sensor/CLAUDE.md` on 2026-09-16 (CARD-0193) — 9096B, over the 5000B size threshold.

---

### CARD-0260 · [enhancement] [homeassistant] Rebuild garage SmartThings Routines as HA automations — real sensor/actuator dependency remains, sequenced after CARD-0164's Oct 2 check
**Status:** Planning

**Raised 2026-09-11, from CARD-0164's decided direction.** The second of two concrete migration cards scoped from that day's full-repo sweep — genuinely more complicated than CARD-0261's salt-sensor case, not a clean parallel.

**Superseded by a full system write-up, 2026-09-12 — see `components/automatic-garage-door-opener-closer/auto-garage-door-system.md`.** That document is now the authoritative architecture reference for this whole system (garage-radar + garage-presence + this component, as one picture); the summary below is corrected to match it, but the doc has the full detail. Also includes a sized implementation plan/lead-time estimate for this card's eventual Build (roughly 1-2 weeks of calendar time once started, assuming CARD-0164's Oct 2 finding is favorable — see the doc's own "Implementation Plan / Lead Time" section) — produced under this card, not yet acted on.

**Correction to this card's original premise:** `switch.garage_door_open_vswitch` was originally categorized below as "pure bookkeeping... could be tracked HA-natively instead." **This was wrong** — confirmed 2026-09-12 (Joseph): it's driven by a real ST-paired garage door position sensor, not a software-only flag. A refactor needs an actual HA-native sensor integration for door position, not just a re-created helper.

**Correction, 2026-09-13 (superseded the note below) — no fourth vswitch after all.** A prior pass through this card thought it had found a distinct fourth vswitch, `garage_door_trigger_auto_open_close_vswitch`, sitting between the routine's condition and the real relay. Confirmed via the actual SmartThings device info screen (2026-09-13): "Garage Door Trigger Auto Open/Close" is the **real physical Zigbee relay itself** (model `ZB-SW01`, manufacturer eWeLink) — the same device documented elsewhere as `switch.open_close_garage_door`/"Open/Close Garage Door," just under a different label. The routine's condition (`IF garage_door_auto_close_enable_vswitch = ON AND (garage_door_open_vswitch = ON AND garage_presence_vswitch = OFF)`) turns this real relay on directly — one hop, no intermediate vswitch. Also confirmed the door-position sensor's real identity: Samsung's own official Z-Wave sensor (model `0004-0003`, manufacturer code `014A-...` — Samsung's Z-Wave manufacturer ID), likely the SmartThings Multipurpose Sensor run in tilt/accelerometer mode. Both now documented with real hardware IDs in `auto-garage-door-system.md`.

**What's actually pure bookkeeping (unconditionally replaceable):**
- `switch.garage_door_auto_close_enable_vswitch` — a manual on/off master-enable flag, pure software state.

**What is genuinely NOT bookkeeping — real hardware this card cannot route around:**
- `switch.open_close_garage_door` — the actual actuator. A real **Zigbee switch**, physically paired to the SmartThings hub's own radio. Not a virtual device — genuine hardware CARD-0164 already decided *not* to migrate off the SmartThings hub. (A DIY ESPHome/WiFi replacement is scoped as an option in `auto-garage-door-system.md`'s refactor section, if this card ever proceeds that far.)
- The real ST-paired door position sensor behind `garage_door_open_vswitch` (see correction above).
- `binary_sensor.garage_motion_motion`, `binary_sensor.back_door_door`, `binary_sensor.garage_cam_motion`, `binary_sensor.back_door_acceleration` — `garage-presence`'s legacy trigger sensors, real SmartThings-bridged hardware, also not being migrated. **Also newly confirmed (2026-09-12):** these are already effectively inert in the live HA automation — a `condition: template` gate (found in `automations.yaml`, not yet in `garage-presence/CLAUDE.md`) blocks their action unless `binary_sensor.garage_radar_presence` is the trigger or is itself unavailable/unknown. Only radar actually drives presence day-to-day; the legacy sensors are a fallback only. See `auto-garage-door-system.md` for the exact condition.
- The devices the door-close action also turns off — not just "garage lights": lights, a fan, a soldering iron, and potentially others (Joseph's own words) — real SmartThings-bridged hardware, exact entity list not enumerated in this repo.

**The actual blocker, not solved by moving the "if/then" logic to HA:** whether the automation's if/then runs as a SmartThings Routine or an HA automation makes no difference to whether it can still *read* those real sensors or *write* to the real Zigbee switch/lights — both paths go through the same HA↔SmartThings integration either way. Converting the Routine to HA does not remove the underlying real-hardware dependencies, unlike CARD-0261's salt-sensor case where every input/output was already fully JCTsh-owned.

**Sequencing decision, 2026-09-11 (Joseph's call), unchanged:** scope this card now, but don't build until CARD-0164's 2026-10-02 Auto-verify check reports back. If HA retains basic read/write access to real SmartThings-synced entities post-cutoff (not just Routines specifically), this card proceeds. If HA loses that access entirely, rebuilding the Routine as an HA automation accomplishes nothing, and this card's scope would need rethinking against CARD-0164's original "migrate" option instead.

**Planned, 2026-09-11 — grounded directly in `garage-presence/CLAUDE.md`'s actual deployed automations, not assumed.** Good news found while grounding this: `switch.garage_presence_vswitch` is **already** toggled entirely by HA's own existing automations ("Restart timer on activity," "Timer expired," "Radar keepalive" — all call `switch.turn_on`/`switch.turn_off` directly, no SmartThings-specific code anywhere) — the exact same pattern as CARD-0261's salt-sensor switches. That conversion is clean.

**Scope needs a real re-pass before Build, now that the corrections above are in** — the original items 2-4 below assumed a simpler 2-vswitch, 2-automation design that doesn't fully match the real door-position sensor dependency just confirmed (though the trigger chain itself turned out simpler than briefly thought — no phantom fourth vswitch, see correction above). Re-plan against `auto-garage-door-system.md` directly when this card is picked back up (post-Oct-2), rather than building against the stale scope below as-is:
1. ~~Resolve what sets `garage_door_open_vswitch`~~ — **done**, see correction above.
2. Convert `garage_door_auto_close_enable_vswitch` (the one genuinely bookkeeping vswitch) to an HA-native Template Switch helper, same approach as CARD-0261.
3. Design an HA-native equivalent of the real trigger chain (enable AND door-open AND presence-off → close) — needs to account for the real door-position sensor, not the originally-assumed simpler design.
4. Design an HA-native equivalent of the close-action side effects (door relay + lights/fan/soldering-iron shutoff).
5. Live-test against real events — a real door-open, a real presence timeout — not just a Developer Tools simulation, matching this project's own verification bar.
6. Delete the SmartThings Routine(s), update this component's and `garage-presence`'s CLAUDE.md to point at the new HA-native architecture (and keep `auto-garage-door-system.md` in sync).

**Done when:** the Routine's logic runs entirely as HA automations, verified live against real trigger events, with the SmartThings-side Routine confirmed removed — contingent on CARD-0164's Oct 2 finding confirming this is even achievable without a real hardware migration.

**Related:** CARD-0164 (the decision this implements, and the Oct 2 Auto-verify this is blocked on), CARD-0261 (the sibling salt-sensor card — clean, no real hardware dependency, not blocked the same way), `components/automatic-garage-door-opener-closer/auto-garage-door-system.md` (the authoritative full-system reference, supersedes the summary in this card), `components/automatic-garage-door-opener-closer/CLAUDE.md`, `components/garage-presence/CLAUDE.md`, `JCTsh-Build-Standards.md` §6.4 (the new-device policy this follows retroactively).

---

### CARD-0259 · [idea] [hiking-monitor] Hiking Monitor v2 — rebuild on air-quality-monitor's power architecture, retire the current unit
**Status:** Planning

**Raised 2026-09-10, from a musing conversation about display legibility that turned into a real reliability question.** Started as "the field display only needs temp/humidity/battery, docked mode needs battery + upload status/times" — a much smaller display footprint than today's full stat block — but the actual driver, once named directly, is battery/power reliability, not the display.

**Why now, not just "eventually":** CARD-0226's reboot loop has recurred four times over two weeks (2026-08-29, 09-03, 09-08, 09-10) with the root cause still unconfirmed — every attempt has been about catching it live on the *existing* hardware (a still-blocked debug UART capture). air-quality-monitor's own power redesign (Pololu buck regulator, BK-1208 latching Power Switch, the three-signal Intent/Power-Connected/Power-Switch model, the bounded WiFi-attempt/retry state machine) has already resolved a comparable class of brownout failures there without needing to explain every individual incident first. A v2 rebuild sidesteps CARD-0226's mystery rather than requiring it to be solved on hardware that may simply be undersized.

**Real tension worth naming, not resolved by this card alone:** CARD-0070 (the boost-converter swap) has stayed Deferred specifically because hiking-monitor is a working, field-proven device, and opening it up risks breaking something that currently works, for a fix only partially validated on a separate rig. CARD-0226's persistence is the argument that "working" is less true than it was when CARD-0070 was first deferred — but this is still the real field hardware, not a bench prototype. Decided anyway: **eventually build v2, retire the current unit** — not a patch to the existing device.

**Timing decided 2026-09-20 (Joseph) — wait on v2 Build until air-quality-monitor has actually been field-tested, not just bench-proven.** Directly resolves the tension above: AQM's power redesign is currently bench-validated only (per its own README: "Bench phase complete... Install phase (enclosure/carry-case) not yet started" — it has never been carried on a real hike). Retiring hiking-monitor's working field hardware for a design that itself hasn't survived a real hike yet would trade one unproven risk for another. Planning (this card's own scoping work, the difference inventory below) can continue now; Build does not start until AQM has a real hike under its belt on the current power/firmware architecture.

**Gate target moved, 2026-10-02 -- the "current power/firmware architecture" above is no longer CARD-0012's.** AQM's original power/retry design DID get field-tested since this gate was written (multiple real hikes ran on it) -- that's exactly how CARD-0377's task-watchdog crash was found. CARD-0377 then replaced the firmware architecture this card means to port almost entirely (see the 2026-10-02 update above): no more MQTT, no more bounded-attempt/retry machine. That redesign is bench-verified only, not yet field-tested (CARD-0377's own "Done when" still needs a real multi-hour hike with zero data loss). **So this gate now points at CARD-0377, not CARD-0012** -- v2 Build should wait for CARD-0377's field confirmation, not treat CARD-0012's earlier (now-superseded) field history as already satisfying it.

**What carries over from air-quality-monitor's now-proven design, discussed 2026-09-10:**
- Pololu D24V10F3 buck regulator in place of the boost converter (resolves CARD-0070's original quiescent-current concern).
- BK-1208 latching Power Switch, separate from the Intent switch (resolves CARD-0181's missing true power-off).
- ~~The three-signal model (Intent / Power Connected / Power Switch) and the bounded-attempt/15-min-retry WiFi state machine, in place of hiking-monitor's own accumulated patches (CARD-0217, CARD-0045).~~ **Three-signal model still carries over; the WiFi state machine does not -- see the 2026-10-02 update below, CARD-0377 deleted it from AQM entirely.**
- ~~The SSID-based `pi1.local`/DuckDNS broker switch (CARD-0254 already scoped this as a port from air-quality-monitor).~~ **Moot -- see below, AQM has no broker to switch anymore.**

**Major update, 2026-10-02 (from CARD-0377, built and bench-verified the same session) -- most of this card's "port from AQM" software/firmware inventory below describes AQM's OLD, MQTT-based design and is now wrong. AQM dropped MQTT entirely: no broker, no persistent session, no bounded-attempt/15-min-retry state machine, no QoS. What replaced it, and should be v2's actual software port target instead of the items struck through in the lists below:**
- **One-shot HTTP upload, not a persistent broker session.** Eligible (Intent off + docked + battery >= upload-safe threshold + data buffered)? One `http_request.post` of the whole buffered log to the data-pipeline gateway's bulk endpoint, clear the log only on a confirmed 200. No attempt-window, no backoff, no reconnect logic -- a one-shot request has nothing to manage between attempts, which is most of why the old state machine needed as much code as it did.
- **WiFi follows dock state directly, not upload-eligibility** (2026-10-02, Joseph's own question mid-build: "if it's docked, do we want to leave wifi connected? why or why not?" -- yes, because while docked the charger supplies the radio, not the battery, so there's nothing to conserve by cycling it, and doing so was closing the only OTA/esphome-logs reachability window to a few seconds at a time). `dock_detect`'s `on_press`/`on_release` enable/disable WiFi; the battery-only case still never gets WiFi, unchanged.
- **Boot-event logging + a server-side per-session summary, replacing the heartbeat's job.** A tiny separate on-device log (one line per boot: boot id + reset reason) rides along with the next upload; the gateway computes session duration, actual-vs-expected readings, battery delta and reset count from the rows + boot events it just received, and relays that as one message -- "did the last session go well" instead of a heartbeat's "is it currently reachable" (which can only ever say "no" mid-hike, hence CARD-0226/this card's own history of false "silent for N hours" alerts). hiking-monitor v1 has no server-side equivalent at all today -- this is new scope for v2, not a straight port of something v1 already has a weaker version of.
- **This resolves two of the three "real gaps" the 2026-09-22 hike-data analysis found below, outright, not just by porting a fix:** the QoS-0 replay-delivery-tracking gap and the MQTT `reboot_timeout` gap are both moot once there's no MQTT client to have a QoS or a reboot_timeout on. v2 inherits neither problem simply by not having the component that caused them. (The battery-voltage-dip-at-reboot finding and the ~15-min reboot clustering are untouched by this -- still real, still worth the regulator/cap hardware fix already planned.)
- **Cross-reference, not itself a v2 decision: AQM had its own `reset_reason_text` timing bug, now fixed by calling `esp_reset_reason()` directly instead of reading ESPHome's `debug:` text_sensor during on_boot** (that text_sensor only populates in `dump_config()`, which runs after every on_boot trigger, so the read was always empty -- a previously-undetected bug in AQM's own brownout-detection LED, not something CARD-0377 introduced). **hiking-monitor v1 already found and fixed the identical ESPHome gotcha back on CARD-0217** -- its own `reset_reason_pending` flag defers the actual read to the interval block's first tick, once `loop()` is genuinely running. Both work; AQM's new direct-ESP-IDF-call approach is simpler (no pending-flag state needed at all). Worth a look at whether v1's `reset_reason_pending` mechanism could be replaced by the simpler direct call too, independent of v2's timeline -- same "kept open regardless of v2" treatment CARD-0254 already got -- but not yet raised as its own card.

~~**Display redesign, discussed 2026-09-10 — not yet a concrete layout:**~~
~~- Field mode: temp, humidity, battery — the three values actually read mid-hike, large enough for a quick glance, not the full current stat block.~~
~~- Docked/upload mode: battery plus upload status/timing (Connected → Uploading → Done, per CARD-0199's existing sequence) — battery matters in both modes, not field-only.~~
~~- Panel size itself (2.13" vs. 1.54" vs. staying put) is a secondary question — genuinely bottlenecked by what content each mode actually shows, not fixed until that's settled. A 1.54" panel (200×200, ~184 DPI vs. the current 2.13"'s 250×122, ~131 DPI) is higher pixel density, so it only helps if the field layout is narrowed to just a few large values — it would hurt legibility if asked to show today's full stat block.~~
**SUPERSEDED 2026-09-20 (Joseph's call, opening Planning) — display stays unchanged in v2.** No field/docked content redesign, no panel swap. See the Planning note below.

~~**Idea considered, not committed — a buzzer or haptic alert for rare, actionable conditions.**~~ Raised in the same 2026-09-10 musing conversation, before the discussion turned toward v2 specifically: LED blink codes require both looking at the device and remembering what a pattern means, and Joseph doesn't check the display often in the field. An audible or vibration alert, reserved only for genuinely rare/actionable conditions (critical battery, a real fault) rather than routine status, would fix both problems at once — no looking required, and almost nothing to remember if it's a single tone/pulse meaning "check the display." Real limit: field mode has no WiFi at all, so this only helps with conditions the device itself can detect and react to locally, not anything needing outside context (matches the same constraint that ruled out phone notifications and MQTT for device-to-device communication, discussed the same session). **DECIDED AGAINST, 2026-09-20 (Joseph) — no buzzer/haptic alert.** Not part of v2's scope.

**Planning opened 2026-09-20, in the hiking-monitor cluster session (re-scoped this session from hike-izer to hiking-monitor mid-conversation, per Joseph's direct ask) — a real hardware/software difference inventory, cross-checked against air-quality-monitor's actual as-built docs (`power-system-redesign.md`, `wiring.md`, `air-quality-monitor-claude-code-instructions.md` Step 8), not just this card's own summary paragraph above:**

*Hardware:*
1. **Regulation:** v1's TP4056+boost combo boosts LiPo 3.7V→5V into the ESP32's `VIN`, which the dev board then bucks back down to 3.3V internally (a boost-then-buck double conversion). v2's Pololu D24V10F3 feeds the ESP32's `3V3` pin directly, `VIN` unused — single conversion.
2. **Point-of-load caps:** v2 adds 470µF electrolytic + 4.7µF ceramic at the ESP32's 3V3/GND pins; v1 has none called out.
3. **True power-off:** v1 has none — the boost's `VOUT+` feeds `VIN` unconditionally, and the one slide switch (GPIO27) is a signal input, not in the power path (CARD-0181). v2 adds the BK-1208 latching push-button in series with the regulator's `VIN`.
4. **Switch roles split:** v2 keeps the slide switch as a pure Intent signal (GPIO27, not power-path) and gives the BK-1208 button sole Power-switch duty (no GPIO, mechanical only) — v1's one switch doesn't have this separation to begin with.
5. **Battery/divider:** unchanged in both — same EEMB 1100mAh LiPo, same 100kΩ/100kΩ divider off `BAT+`.
6. **Sensors:** unchanged — v2 does **not** adopt AQM's SEN55. AQM stays a physically separate device; its data only merges downstream in hike-izer (CARD-0285).
7. **Display: unchanged**, per the superseded section above — no redesign, no panel swap.
8. **Buzzer/haptic:** decided against, per above.
9. **Network status indication:** AQM signals WiFi/MQTT attempt state via a dedicated blue LED — hiking-monitor has no LED at all today, only the e-ink display. **Consider showing network status on the existing display instead of adding an LED** (Joseph, 2026-09-20) — not yet scoped (what state, where on the display, whether it's compatible with partial-refresh) — an open item for further Planning, not a committed design.

*Software/firmware:*
1. ~~**WiFi boot gating:** v1 defers `wifi.disable()` to the first interval tick (its `on_boot` runs at priority 600, before WiFi's own 250). v2's three-condition gate (Intent off AND Power-Connected AND battery ≥ upload-safe threshold) runs as the literal first `on_boot` action (AQM's block runs at priority ‑100, after WiFi's setup).~~ **Superseded 2026-10-02 -- AQM no longer runs this gate at boot at all; see the update above. v2's `on_boot` should instead check `dock_detect` directly and enable/disable WiFi accordingly (AQM's current pattern), with the actual upload-eligibility check living only in the periodic tick.**
2. ~~**Bounded-attempt/retry state machine:** v1 has no formalized version of this (part of why CARD-0226's reboot loop is still unexplained). v2 imports AQM's explicit machine: ~2-min attempt window → `wifi.disable()` → ~15-min backoff → retry, uncapped retry count, 2 timestamps + 1 bool.~~ **Superseded 2026-10-02 -- this machine doesn't exist in AQM anymore (CARD-0377 deleted it outright, replaced by one-shot HTTP upload, no state to track between attempts). v2 should port the one-shot design, not this machine.**
3. **Upload-safety voltage gate:** v1 has one threshold only (3.4V generic low-battery shutdown). v2 adds a second, higher "upload-safe" gate (AQM's current value: 3.5V, revised down from an original 3.8V once CARD-0198's brownout finding was traced to a battery-ALONE stress trial -- the well-tested docked case, where the charger supplies the burst current, was clean at every voltage tried) that only gates attempting an upload — the general cutoff is unchanged. Still applies under the new design (AQM's eligibility check keeps this condition, just without the retry machine wrapped around it).
4. ~~**Broker addressing:** v1 always targets `jctsh.duckdns.org`, even on the home LAN (needless internet round-trip). v2 imports AQM's `wifi_info: ssid:` + `on_connect:` switch to `pi1.local` on `JCTnet1`, plus `skip_cert_cn_check: true` — note CARD-0254 already scopes porting this to the *current* v1 unit regardless of v2's timeline.~~ **Moot 2026-10-02 -- AQM has no broker at all now, so no SSID-based switch to port. v2's one-shot upload always targets the same public gateway route (`https://hikes.jctnet.com/...`) regardless of which network it's on -- works identically docked at home or via a hotspot while traveling, by design (see CARD-0377). CARD-0254 (porting the SSID-switch to the *current* v1 unit) is unaffected by this -- that's about today's hardware's own DNS-reliability problem, which is real and still worth fixing on v1 independent of v2, just no longer something v2 inherits from AQM.**
5. **Dock-detect coupling:** v1 stops field logging once `dock_detect` goes HIGH. AQM's pattern (which v2 would inherit) decouples them — field logging runs unconditionally, dock-detect HIGH only ever triggers a background WiFi attempt. A real behavioral change, not just a wiring port. Still applies under the new design -- unaffected by the MQTT removal.
6. **Deep sleep:** v1's boost converter stays always-on with undocumented/unmeasured sleep-current draw — not true deep sleep. v2 folds in CARD-0201's true deep-sleep-between-samples goal.
7. **Solar voltage sensing:** v1 never wired the ADC divider CARD-0017 designed. v2 folds in CARD-0202, rolling it into the power redesign.
8. **Boot-event logging + session summary** (new, 2026-10-02, see the update above) -- a tiny per-boot log (boot id + reset reason) riding along with the next upload, and a server-side computed per-session summary replacing the heartbeat's "is it reachable" with "did the session go well."
9. **One-shot HTTP upload replaces MQTT entirely** (new, 2026-10-02, see the update above) -- the actual replacement for items 1-2's struck-through machinery.

**Hike-data analysis findings relevant to this rebuild, 2026-09-22 (hike-izer cluster session, synthesizing CARD-0226's now nine logged recurrences) — validates the founding premise with real numbers, and surfaces one real gap in the difference inventory above.**
- **This isn't a rare edge case anymore — it's the norm.** Nine recurrences in 24 days, essentially every hike since 2026-08-29 shows the reboot loop in some form. Environmental Data coverage across the hikes analyzed so far ranges 14.8%-72.1%, most well under half. Stronger evidence than existed when this card was first raised (four recurrences over two weeks) for the actual premise -- this is v1's dominant reliability problem, not an occasional annoyance.
- **New clue, not previously checked: a real battery-voltage dip lands at the exact reboot instant, on 8 of 9 reboot-adjacent readings checked so far across three hikes.** Every surviving reading right at a reboot timestamp shows an isolated ~0.15-0.3V dip below its neighbors, recovering by the very next reading. Battery was well above the 3.4V cutoff on the hikes checked (4.0-4.18V) -- ruling out simple depletion as the trigger, and instead pointing toward a genuine instantaneous current-spike/regulator-headroom issue: the same physics `JCTsh-Build-Standards.md` §2.14 point 9 already documents, just not WiFi-TX-triggered this time (field mode has no WiFi active) -- something else in the firmware's own periodic housekeeping is the more likely spike source. **This is real, direct evidence in favor of the regulator/cap upgrade already planned above (Pololu D24V10F3 + 470µF/4.7µF) -- that fix targets exactly this failure class, independent of ever identifying the precise trigger.**
- **Open forensic detail, not yet explained, worth watching for on a future live capture: reboots cluster roughly every ~15 minutes, not on every 2-minute field-mode wake.** Something in the firmware's own periodic housekeeping (candidate raised on CARD-0226: the MQTT component's reconnect-backoff logic, which runs continuously even with no active connection) is a more likely proximate cause than anything tied to the 2-min sensor-read cycle itself.
- ~~**Real gap in this card's own software/firmware difference inventory above: no item currently covers CARD-0226's own Done-when item 2 -- per-record delivery tracking on the replay path (QoS 1 with a real broker ack, not v1's QoS 0 fire-and-forget).** Every analyzed hike's coverage shortfall is consistent with exactly this mechanism: the device believes replay succeeded ("Hike log replay complete."), but a large fraction of buffered readings never actually landed. Porting AQM's power/retry design alone does not fix this -- it's a separate, additional software change v2 needs on the replay path specifically, regardless of whether the power redesign eliminates the reboot trigger itself. Should be added as its own item to the software/firmware list above, not left implicit. **Confirmed 2026-09-22: air-quality-monitor's own replay path (`aqm_log_replay_stream`) also publishes at `qos: 0` (identical to hiking-monitor's `hike_log_replay_stream`)** -- so porting AQM's design literally imports this same weakness rather than fixing it. If this gets fixed, it needs its own fix on both devices, not an inherited one.~~ **RESOLVED outright, 2026-10-02 (not by fixing QoS -- by not having MQTT at all).** AQM's replay path no longer exists; CARD-0377 replaced it with one HTTP POST per upload, confirmed (200) or not, no QoS concept to get wrong. v2 inheriting AQM's *current* design inherits zero per-record delivery-tracking risk, rather than the same weakness this note originally warned about.
- ~~**Real gap found 2026-09-22, likely more consequential than any item above: hiking-monitor's `mqtt:` block never got the one-line fix AQM's own firmware already validated for the exact bug CARD-0226 has been chasing.** ESPHome's MQTT component force-reboots the device if its internal `last_connected_` timer exceeds 15 minutes (`reboot_timeout`, default) -- AQM found this live 2026-09-09 (its `mqtt:` block's own comment: *"ESPHome's own watchdog was rebooting the device right as our backoff neared completion"*) and fixed it with `reboot_timeout: 0s`. hiking-monitor's config has no such line, still runs the 15-min default -- and CARD-0226's own recurrences cluster at almost exactly that interval. CARD-0045 (archived, Done) closed this exact concern in 2026-08-27 as "moot" once WiFi was disabled during field mode, but never field-verified that assumption, and AQM's later finding directly contradicts it (disabling the connection attempt doesn't reset the component's own internal timer). **This needs to be an explicit, named item in v2's software/firmware port list, not assumed to come along automatically with the rest of AQM's design** -- see CARD-0226's own new note (2026-09-22) for the full reasoning, and consider testing `reboot_timeout: 0s` on the *current* v1 hardware directly, independent of v2's timeline, since it's a single reversible OTA-flashable line.~~ **RESOLVED outright, 2026-10-02, same reason as above -- AQM's `mqtt:` block (and therefore its `reboot_timeout`) no longer exists at all.** v2 inheriting AQM's current design has no MQTT component to force-reboot it on a stale timer, full stop. This does NOT retroactively fix the *current* v1 hardware's own still-live `reboot_timeout` exposure -- that's still worth testing `reboot_timeout: 0s` on v1 directly, independent of v2's timeline, exactly as this note originally suggested; only v2's *inherited* risk is what's resolved here.
- **A concrete, sharp acceptance bar for v2's first real field hike, once built:** zero `Reboot request from mqtt`/blank-reset-reason lines, no isolated battery-voltage dips, and Environmental Data coverage at or near 100% -- not merely "improved" over v1's observed 15-72% range. Also check for the absence of `Skipped reading - nan_sensor` events (seen pairing with blank-reset-reason boots on two recurrences) -- a real symptom beyond just the reset-reason count, and a further signal the fix actually worked structurally rather than just reducing frequency.

**Not yet scoped:** a concrete BOM, wiring plan, enclosure design, or firmware rewrite — the above is a difference inventory and this Planning session's first real decisions, not an implementation plan. The display-status idea (hardware point 9) also needs its own scoping pass before it's part of committed v2 scope. **Build is gated on AQM's own field-test outcome (see Timing decision above)** — tracked on CARD-0012 (AQM's build/install-phase card), not re-tracked here; check that card before starting v2 Build.

**Related open cards reviewed and dispositioned, 2026-09-10 (Joseph's call on each):**
- **Folded in and closed:** CARD-0070 (boost-converter/LDO swap — superseded by air-quality-monitor's Pololu regulator), CARD-0181 (missing true power-off — superseded by the BK-1208 Power Switch), CARD-0217 (heat/brownout incident — its own residual hardware-margin question resolves here), CARD-0202 (real solar_v sensing — rolls into v2's power redesign), CARD-0201 (true deep-sleep-between-samples — a from-scratch v2 build is the cleaner place for this rearchitecture risk than the current firmware). CARD-0027 (superseded by CARD-0070) updated to point here.
- **Kept open, cross-referenced, not folded:** CARD-0226 (the recurring reboot loop motivating this card — still worth chasing root cause on current hardware in parallel, in case it's fixable without a rebuild), CARD-0254 (broker-switch port — worth doing on the current unit regardless of v2's timeline).
- **Kept open, unrelated:** CARD-0203 (longer LiPo cell fit), CARD-0025 (test a retired cell) — independent of this card.

**Related:** CARD-0012 (air-quality-monitor's own build — the original design basis, since substantially superseded), CARD-0377 (2026-10-02 -- the actual current design basis: drops MQTT entirely, one-shot HTTP upload, dock-driven WiFi, boot-event/session-summary pattern; also now the field-test gate for v2 Build per the update above), CARD-0254 (the SSID-based broker-switch port, kept open independent of v2's timeline -- now a v1-only fix, no longer something v2 inherits from AQM), CARD-0285 (confirms AQM stays a separate device from hike-izer's own single-ownership rule, not folded into hiking-monitor).

---

### CARD-0258 · [bug] [hike-izer] Step 1 generation (session-window probe) hit the full 240s timeout fetching GPS Track — RESOLVED 2026-09-17 19:51 MST (mitigation only; root cause accepted as unidentified)
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-18 (CARD-0193) — 12287B, over the 5000B size threshold.

---

### CARD-0257 · [enhancement] [m8] cloudflared container update available: 2026.8.3 → 2026.9.3 — deliberately deferred pending tunnel-failure reports
**Status:** Backlog

**Raised via automated maintenance finding (PR #71, photo-server), 2026-09-10.** Routine container-version-bump finding from the scheduled maintenance check (CARD-0126): cloudflared 2026.9.0 available, running 2026.8.3.

**Held rather than applied, 2026-09-10 — researched before landing, per this repo's standing PR-landing process.** A Cloudflare Community post from the last ~24h ("Issue with 2026.9.0 release of cloudflared") reports tunnel failures (origin unreachable, error 1033) after upgrading, resolved for that user by rolling back to 2026.8.3. One unconfirmed report — not corroborated by other community posts or GitHub issues at the time of this check, and no official Cloudflare acknowledgment found. But cloudflared is what backs the public `hikes.jctnet.com` Cloudflare Tunnel (`hike-izer-orchestrator`'s only public HTTPS surface — `hike-end`, `idea`, `step2`, `pipeline-log` webhooks, `birdnet-live` staging all go through it, per CARD-0227), so an outage here would be immediately felt on a live hike, not just a background service hiccup. Joseph's call: hold rather than apply now.

**Superseded target, 2026-09-13 (PR #78, closed as duplicate 2026-09-14) — still holding, not enough new evidence yet.** A newer patch, 2026.9.1, shipped — but its own release notes only mention an unrelated transport log-level revert, no tunnel-connectivity fix. No further corroboration or refutation of the original single Cloudflare Community report was found either. The "revisit in 1-2 weeks" window hadn't fully elapsed (3 days in at the time). Folded into this card rather than opening a duplicate — same pattern CARD-0274 used for Immich's v3.2.1→v3.2.2 supersession — but this card's own title/target number was left un-bumped when PR #78 was closed, so it kept reading "2026.9.0" for days after the real pending version had already moved to 2026.9.1.

**Real gap found and fixed here, 2026-09-18 (Joseph: "cloudflared update isn't tracked by any card yet, why?" — prompted by the mismatch between the live `/status` dashboard showing 2026.9.1 pending and this card's stale 2026.9.0 title).** Confirmed via the M8's own systemd journal (`container-update-check-m8.service`) that the automation worked correctly the whole time: it detected 2026.9.1 as genuinely new on 2026-09-12 and opened PR #78 for it, which was then correctly closed as a duplicate of this held card rather than landed separately — the actual miss was just that closing a duplicate PR never re-bumped the target on the card it deduped against. Re-checked cloudflared's GitHub releases directly, 2026-09-18: **2026.9.1 is still the current latest release** (published 2026-09-11, nothing newer since) — title corrected above to reflect that as the real pending target. The tunnel-failure risk itself has not been re-researched in this pass; still holding on the same 2026-09-13 evidence.

**Third duplicate finding, 2026-09-20 (PR #120, photo-server) — closed as duplicate, target unchanged (still 2026.9.1).** Same pattern as PR #78: the automation correctly re-detects the still-pending update on its regular schedule; this isn't new information, just confirms nothing has changed. Revisit is now genuinely overdue (10 days since the original 2026-09-10 raise, past the 1-2 week window) — the actual re-research (further community reports, newer patch releases) still hasn't happened, only the target-bump bookkeeping.

**Revisit finally done, ~~2026-09-22 10:00 MST~~ 2026-09-22 09:49 MST or earlier (corrected 2026-09-22 10:35 MST — see note below) (ops cluster session, Joseph's go-ahead) — the research the last three passes kept deferring. Outcome: keep holding, and the evidence is now much stronger than "one unconfirmed forum post."**

**Timestamp correction, 2026-09-22 10:35 MST (this session, prompted by CARD-0329's TZ= sweep).** This entry and CARD-0326's "Built and verified" stamp were both narrative estimates written as the work progressed, never read from an actual clock this session -- not the `TZ=` 7-hour hazard CARD-0329 fixed, a separate error (writing an increasing clock-time alongside a growing narrative rather than measuring one). Caught by comparing against ground truth: commit `4baf8f7` (`git log --date=format-local`) carries this exact text with an author-date of `2026-09-22 09:49:44` -- proving both stamps described events as happening *after* the commit that already contained them, which is impossible. Corrected to `09:49 MST` as the latest defensible bound; the true time of each individual step within this session's ~70-minute arc was never captured precisely enough to recover further. No finding in either entry is affected -- only the clock reading.

1. **A real, still-open upstream bug report exists, and it matches this host's exact deployment shape.** [cloudflared#1737](https://github.com/cloudflare/cloudflared/issues/1737), filed 2026-09-11, still **open** with zero maintainer response as of today: *"2026.9.0 segfaults in quic-go QueueProbePacket (nil receiver) when running in a Docker bridge network — 2026.8.2 unaffected."* Not a vague report — a full SIGSEGV stack trace in the bundled quic-go fork's probe-timeout path, deterministic (`pc=0xdae18d` identical on every crash), **145 crashes in ~6 hours**, container restarting on `unless-stopped` each time. The reporter's own control case is the most telling part: a *second* tunnel running the *same* 2026.9.0 binary on the *same* machine as a host systemd service had **zero** crashes — the only difference being host networking instead of the Docker bridge/NAT.
2. **The M8 is in precisely the affected configuration.** Checked live: `hike-izer-cloudflared` runs on a user-defined Docker bridge network (`hike-izer-web_default`, container IP `172.19.0.4`) with `restart: unless-stopped` — the same bridge/NAT path the issue fingers, and the same restart policy that would turn a crash loop into a flapping tunnel rather than an obvious hard failure. This is no longer a generic "somebody had a problem" risk; it's a specific mechanism that this deployment would be exposed to.
3. **2026.9.1 does not fix it.** Its release notes are three entries — a revert of "Cleanup unused transport log level," a deprecation note, and a changelog note. The vendored quic-go fork is untouched between 2026.9.0 and 2026.9.1, so there is no reason to think the segfault is addressed. (2026.9.0's one substantive change, `TUN-10738: Propagate edge registration errors over QUIC and fix supervisor error classification`, is at least in the same subsystem as the original community report's error-1033 symptom — plausibly the same root area, though that connection is inference, not something upstream has stated.)
4. **Still nothing newer.** 2026.9.1 (2026-09-11) remains the latest release, 11 days on. Only three issues have been filed against the repo since 2026-09-08 — #1737 above, plus [#1736](https://github.com/cloudflare/cloudflared/issues/1736) (QUIC `--protocol auto` failing to fall back to HTTP/2 on a rejected handshake, also open). Two of the three open issues in that window are QUIC connection-path bugs; that's a small absolute number, but the ratio is not reassuring for a release whose headline change was QUIC error propagation.

**Method note, because it nearly produced the wrong answer:** the first GitHub search (`repo:cloudflare/cloudflared is:issue 2026.9 created:>2026-09-01`) returned **0 results** — the version string tokenizes badly — which would have read as "no corroboration found, safe to apply," the exact opposite of the truth. The finding only appeared on an unfiltered `created:>2026-09-08` listing. Worth remembering for any future version-risk check in this repo: **a zero-result search is not evidence of absence until the query has been shown to return anything at all.**

**Recommendation, for Joseph's call — not applied unilaterally:** keep holding 2026.8.3, which is running cleanly (zero SIGSEGV/panic entries across its entire journal, tunnel connections registering normally, `hikes.jctnet.com` up). The "1-2 week window" framing is now obsolete — this isn't waiting for time to pass, it's waiting for a specific upstream event: #1737 closing, or a 2026.9.2+ that bumps the quic-go fork. **Separately, and more actionable: the M8's compose pins `cloudflare/cloudflared:latest`, not a version.** Nothing pulls automatically, so there's no live danger — but the next incidental pull/recreate on that project would silently land 2026.9.1 with no decision point, which is a poor safety property for the one container backing the public tunnel while a known crash bug is open against that exact version. Worth pinning to `2026.8.3` explicitly; raising that as its own card rather than folding it in here, since it's a deployment-hygiene change to a live compose file, not this card's research question.

**Done when:** either #1737 is resolved upstream (or a release ships that bumps the vendored quic-go fork past it) and the update is applied and verified on the M8, or a deliberate decision is recorded to stay on 2026.8.3 indefinitely. Re-check trigger is the upstream issue, not a calendar interval.

**Related:** CARD-0126 (container-image update-visibility check that raised this), CARD-0227 (the Cloudflare Tunnel setup for `hikes.jctnet.com` this update would touch), CARD-0128 (the auto-PR intake pipeline), CARD-0274 (the Immich supersession this card's target-bump now matches).


**Fourth duplicate finding, 2026-09-25 (PR #133, photo-server) -- target bumped to 2026.9.3; still holding, and the evidence hasn't moved.** Two new releases shipped on 2026-09-24, 30 minutes apart (2026.9.2 at 15:44Z, 2026.9.3 at 16:14Z); **both release pages are empty apart from checksums.** Checked the code instead of the notes (`gh api repos/cloudflare/cloudflared/compare/2026.9.1...2026.9.3`): 27 commits, 45 files -- almost entirely a new Quick Tunnel authentication feature set (TUN-10798 through TUN-10805: browser-bound login state, callback authorization, JWKS caching), hardening chores (response-size limit, header protection, no request-body logging), a gRPC bump and a dependency update. **No file in the range mentions `quic-go`, and `go.mod`'s changes are version bumps only -- the vendored quic-go fork that [cloudflared#1737](https://github.com/cloudflare/cloudflared/issues/1737) crashes in is untouched.** #1737 is still open, 0 comments, no maintainer response (last updated 2026-09-11). The M8's deployment shape (Docker bridge network, `restart: unless-stopped`) is unchanged, so the same exposure applies. **Also held for a second, independent reason: not before Saturday's 2026-09-26 hike (Joseph, 2026-09-25)** -- this tunnel carries the GPSLogger hike-end trigger, the hike pages and the idea/step2/pipeline-log webhooks; a flapping tunnel during a hike is the exact failure this card exists to avoid. Nothing further to do until #1737 moves or a release touches quic-go. PR #133 folded into this card, not landed separately.
---

### CARD-0256 · [idea] [architecture] Standard robust solar+swappable-battery power pattern for backyard devices
**Status:** Backlog

**Raised 2026-09-09**, from a battery-inventory discussion prompted by CARD-0255's bird-bath BirdNET idea. Joseph wants a general power pattern for backyard/outdoor devices (not tied to one specific build): solar charging as the primary source, with the ability to swap batteries by hand if solar can't keep up (shading, winter, extended cloudy stretches) — a step up in robustness from this project's existing single-LiPo-pouch, solder/JST-connector pattern (hiking-monitor, air-quality-monitor).

**Candidate battery: EVE 18650 cells already in stock** (`jctsh-parts-inventory.md`, Bag 5, 3200mAh, 10A discharge, 5 on hand, unallocated) — nearly 3x the capacity of the EEMB LiPo pouches already used elsewhere (1100mAh), and the cylindrical form factor fits a cheap 18650 holder much better for actual hand-swapping than a soldered/JST LiPo pack.

**Chemistry question resolved, 2026-09-09 — standard Li-ion, not LiFePO4.** The inventory's "3.3V" label was a mislabel: manufacturer/retailer listings (including the same store already cited, 18650batterystore.com) confirm this is the **EVE INR18650/33V** — "INR" designates standard Li-ion (NMC) chemistry, 3.6V nominal/4.2V peak; "33V" is a model-code suffix, not the actual voltage. Corrected in `jctsh-parts-inventory.md`. Practical upshot: no LiFePO4-specific charge controller needed — a standard TP4056 (same as already used on hiking-monitor/air-quality-monitor) charges these correctly, one less open design question. The fireproof-charging-bag requirement (`JCTsh-Build-Standards.md` §2.14) still applies, same as any other LiPo/Li-ion cell in this project.

**Charging/solar hardware survey, 2026-09-09 — real candidates already in stock, no new parts needed to start:**
- **AEDIKO 18650 Battery Charger Module + Holder** (`jctsh-parts-inventory.md`, Bag 4, 10 units, unallocated) — a combo charger+holder purpose-built for 18650s (fast-charge, boost output, PCB protection), integrating the swap-holder itself rather than needing one sourced separately. Probably the better fit given this card's "hand-swappable" goal specifically. **Open item: unconfirmed whether it accepts a bare solar panel's raw output directly, or expects standard USB 5V** — needs checking against the actual module/datasheet before committing to it for the solar path.
- **TP4056 modules** (Bin A4, 5 on hand, 4 spare after hiking-monitor) — the general-purpose charger already used throughout this project, confirmed compatible with the EVE cells' standard Li-ion chemistry (per the chemistry resolution above), and already proven to accept solar input directly (exactly how air-quality-monitor's design works today) — the safer, already-validated fallback if the AEDIKO module's solar compatibility doesn't check out.
- **SUNYIMA Mini Solar Panel** (Bag 6, 5.5V/80mA, 10 on hand, unallocated) — the same panel already spec'd into air-quality-monitor's design; no new solar hardware needed.

**Not yet interviewed for a done-when or full acceptance criteria** — essence-only per this project's Backlog scoping convention. Real design work (verify AEDIKO module's solar-input compatibility, holder/enclosure for hand-swappable access, whether this becomes a documented `JCTsh-Build-Standards.md` pattern like the existing LiPo guidance) belongs in Planning.

**Related:** CARD-0255 (the bird-bath idea that prompted this), `jctsh-parts-inventory.md` (EVE 18650 cells Bag 5, AEDIKO charger+holder Bag 4, TP4056 modules Bin A4, SUNYIMA solar panel Bag 6).

---

### CARD-0255 · [idea] [wildlife] BirdNET-based bird identification at the bird bath
**Status:** Backlog

**Raised via voice capture, 2026-09-09** (submitted as "bird net microphone for bird bath" — a transcription of "BirdNET"). Idea: dedicated audio hardware near the bird bath running BirdNET (open-source bird-sound species identification), feeding identified species into the existing wildlife tracking pipeline. The existing Ring camera at the bird bath was considered as the audio source but ruled out given ongoing Ring integration challenges — dedicated hardware is the intended approach.

**Not a hiking-pipeline integration** — the existing BirdNET pipeline (`components/hike-izer-orchestrator/birdnet-pipeline.md`, CARD-0080) is built around a phone running BirdNET Live during a hike, shared via Tasker/AutoShare. This idea is a separate, stationary use case with no phone/hike context. What's genuinely reusable is the *downstream* merge — `wildlife_life_list.json` and the `wildlife.html` cross-hike index — not the phone-capture mechanism itself.

**Not yet interviewed for a done-when or full acceptance criteria** — essence-only per this project's Backlog scoping convention. Real design work (capture hardware, whether it runs BirdNET-Analyzer locally or offloads audio, how detections reach `wildlife_life_list.json` outside a hike context) belongs in Planning.

**Initial architecture discussion, 2026-09-09 (Claude's analysis, not yet decided):**
- **Two candidate approaches for running BirdNET itself:** (1) **BirdNET-Pi** — a turnkey, actively-maintained open-source project (Raspberry Pi + USB microphone, handles capture/inference/logging/its own web dashboard in one package) — purpose-built for exactly this continuous-monitoring-at-a-fixed-location use case, but needs a dedicated Pi physically near the bird bath. (2) A lightweight capture device streaming/uploading audio to the M8, where a container runs the core BirdNET-Analyzer library — matches this project's existing "lightweight edge device, centralized processing" pattern (every other component already works this way) but is more DIY, with no existing BirdNET-Analyzer integration to build from.
- **Weatherproofing the mic:** a downward-facing hooded housing (mic capsule pointed down inside a short PVC section or small enclosure with an overhanging lip) is a proven, simple approach from DIY bird-audio-recorder builds — physically blocks rain while passing sound freely. An acoustic vent membrane (as used in outdoor weather stations) adds more robustness if needed.
- **Where compute lives:** recommended not to place a Pi outdoors at all — keep it indoors/sheltered (garage, covered patio) and run only a mic cable outside, since weatherproofing a whole SBC is a much bigger ask than weatherproofing just a mic capsule.
- **Cable-run limits, if going the wired-Pi route:** a bare analog capsule over unbalanced cable degrades past roughly 15-25 feet (noise/hum); balanced XLR can run 100+ feet cleanly but needs a balanced mic/preamp, not a cheap capsule; USB extensions are limited to ~5m without active repeaters.
- **Recommended alternative, avoids the cable question entirely:** a small ESP32 with a cheap digital I2S microphone (INMP441 breakout, ~$5) placed right at the bird bath, streaming/uploading short audio clips wirelessly to the M8 over WiFi — the same edge-device-to-central-compute pattern hiking-monitor/air-quality-monitor/garage-radar already use. Only the small ESP32+mic needs weatherproofing (much easier than a full Pi), and it fits this project's established architecture more naturally than either a long mic cable or a standalone outdoor Pi.

**Related:** `components/hike-izer-orchestrator/birdnet-pipeline.md` (CARD-0080, the existing hike-time BirdNET integration this would share a downstream merge with).

---

### CARD-0254 · [enhancement] [hiking-monitor] Port SSID-based pi1.local/DuckDNS broker switch from air-quality-monitor
**Status:** Backlog

**Raised 2026-09-09**, from a review of what air-quality-monitor's Step 8 work (CARD-0012) taught that's actually applicable to hiking-monitor. air-quality-monitor found and fixed a real DNS-reliability issue (CARD-0253, folded into CARD-0012): a device connecting to `jctsh.duckdns.org` even when on the home LAN needlessly routes a same-network connection out to the internet and back, causing sustained DNS-resolution failures during bench testing. Fixed there by adding a `wifi_info: ssid:` text sensor and a `wifi: on_connect:` lambda that switches the MQTT broker to `pi1.local` when on `JCTnet1`, `jctsh.duckdns.org` otherwise. That fix was deliberately scoped to air-quality-monitor only at the time, since hiking-monitor is already deployed/field-proven and porting was meant to wait until the new pattern proved out — CARD-0012's Step 8 is now fully complete and verified live, so this card picks that up.

**hiking-monitor shares the exact same always-DuckDNS pattern** — its `mqtt:` block always targets `!secret mqtt_broker` regardless of which network it's on, same as air-quality-monitor's pre-fix config — so it's plausibly hitting the same needless internet round-trip whenever it happens to be on JCTnet1 (e.g. bench testing, or if it's ever docked/charged near the router).

**Confirmed compatible architecture, not just assumed** (checked `hiking-monitor.yaml` directly, 2026-09-09): already uses TLS on port 8883 with `certificate_authority`, same as air-quality-monitor — the port/TLS setup doesn't need to change, only the broker hostname switches at runtime (ESPHome's mqtt_client reads the broker address fresh on every connection attempt; TLS-vs-plaintext is decided once at first init, which is why both devices need to keep TLS on for both paths and only switch hostname). No `wifi_info: ssid:` sensor or `wifi: on_connect:` block exists yet — both would need adding. `skip_cert_cn_check: true` (lets the same cert validate for `pi1.local` too, since its CN only covers `jctsh.duckdns.org`) isn't set yet either.

**Not yet interviewed for a done-when or full acceptance criteria** — this is essence-only for now (what/why), per this project's own Backlog-card scoping convention. Real design/porting work belongs in Planning/Build.

**Kept open independent of CARD-0259 (hiking-monitor v2), 2026-09-10 — Joseph's call.** Worth porting to the current unit regardless of a future v2 rebuild's own timeline, not deferred to wait for it.

**Related:** CARD-0012 (air-quality-monitor's Step 8, where this pattern was built and proven), CARD-0253 (the original DNS-reliability finding, folded into CARD-0012), CARD-0259 (hiking-monitor v2 — this same pattern would come built-in there, but that's no reason to hold off applying it to the current unit first). Tangentially: CARD-0045 (hiking-monitor's own known, low-priority `reboot_timeout`/`wifi.ap:` interaction issue, archived) — CARD-0012's Step 8 independently confirmed with hard evidence that ESPHome's `mqtt: reboot_timeout` is a real, live mechanism that can force an unwanted reboot; worth a note on that archived card sometime, but out of this card's scope.

---

### CARD-0253 · [retracted] Folded into CARD-0012 — was: DuckDNS/pi1.local broker selection
**Status:** Done

**Opened, then folded back into CARD-0012 within the same session, 2026-09-09.** Per a corrected card-creation policy (Joseph: don't open a new card for every problem found while building/testing an already-open card — track it on that card instead, unless explicitly deferred to a future version), this DNS-reliability finding and its fix are tracked as a note on **CARD-0012**'s own Step 8 section, not here. Kept as a stub (not deleted) since the card number is already referenced in code comments (`air-quality-monitor.yaml`, `secrets.yaml`) and shouldn't dangle.

---

### CARD-0252 · [retracted] Folded into CARD-0012 — was: SEN55 intermittent I2C CRC failures
**Status:** Done

**Opened, then folded back into CARD-0012 within the same session, 2026-09-09.** Per the same corrected card-creation policy as CARD-0253 above — this CRC-glitch investigation is tracked as an open thread on **CARD-0012**'s own Step 8 section, not here. Kept as a stub (not deleted) since the card number is already referenced in code comments (`air-quality-monitor.yaml`).

---

### CARD-0250 · [bug] [hike-izer] A real hike with a long rest stop can be misclassified as "not a hike" by the whole-session median-speed check — RESOLVED 2026-09-08
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-09-10 (CARD-0193) — 7117B, over the 5000B size threshold.

---

### CARD-0249 · [enhancement] [maintenance] Distinguish post-reboot container "starting" alerts from real Docker-degraded alerts — RESOLVED 2026-09-14 11:00 MST
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-16 (CARD-0193) — 6829B, over the 5000B size threshold.

---

### CARD-0248 · [bug] [logging] Pre-reboot journal snapshot only covers the scheduled reboot, not an unplanned one — RESOLVED 2026-09-14 13:25 MST
**Status:** Done

Archived to `core/logging/CLAUDE.md` on 2026-09-16 (CARD-0193) — 10037B, over the 5000B size threshold.

---

### CARD-0247 · [enhancement] [maintenance] Fold HA post-reboot entity-availability check into reboot-health-check.py

**Status:** Build

**Raised 2026-09-06**, from discussing today's Samsung TV pairing dialog and CARD-0240's own "Post-update entity-availability check" — both are the same underlying fact (a config entry can report `state: loaded` without having actually resynced after a restart) discovered by two different triggers (a manual HA image update, and this session's own Pi reboots for CARD-0246). The check currently only exists as a `CLAUDE.md` instruction for Claude to run by hand after a `docker compose up -d`/recreate — nothing catches it after an ordinary weekly scheduled reboot, which is exactly what happened today.

**Scope, agreed in conversation (no separate interview needed — this is the plan):**
1. Extend `core/maintenance/reboot-health-check.py` (CARD-0158, already runs post-boot as a oneshot) rather than building a new script — same job, same timing, same dashboard row.
2. Once the `homeassistant` Docker container itself reports `healthy`, hit the HA REST API (new `HA_TOKEN`/`HA_URL` added to the already-read `/etc/jctsh/log-server.env`, reusing the existing long-lived token per `credentials.local.md`'s own reuse convention — no new credential):
   - `GET /api/states`, count entities in `state: unavailable`.
   - Parse `docker logs homeassistant` for the bootstrap `"Waiting for integrations to complete setup"` line — the exact mechanism CARD-0240's 2026-09-06 generalization already used to find `samsungtv` on the same slow-loading list as `smartthings`/`ring`. This is the real, proven detection signal, not a guessed unavailable-count threshold (a threshold would false-positive against the ~53 permanently-offline SmartThings-hub devices CARD-0240 already found are normal).
3. **Auto-reload only an allowlist of integrations proven safe to reload unattended: `smartthings`, `ring`.** `POST /api/config/config_entries/entry/<id>/reload` for each, then recheck the unavailable count.
4. **Everything else named on the slow-loading list (`samsungtv` included) gets flagged, never auto-reloaded.** Reasoning: the TV's fix is a physical accept-on-the-TV action no unattended job can complete — auto-reloading it would just repeat the pairing prompt with nobody there to clear it, or leave it silently disconnected either way. Alerting so a human knows to go accept it is the correct and only useful behavior there.
5. Publish the before/after unavailable counts and which domains were auto-reloaded vs. flagged into the existing `jctsh/core/jctsh-core/reboot-health` retained MQTT fact (dashboard-visible, same pattern as today's `checks` dict) — and fire a separate `Alert` log message (same path the script already uses for a failed health check) whenever any domain lands in the flagged (non-auto-reloadable) list, naming which domain(s) need a look.

**Explicitly not in scope:** a general entity_id→integration mapper (HA's REST API doesn't expose the entity registry needed for that) — the boot log's own slow-loading list is the detection mechanism, not a from-scratch classifier. Not touching the "healthy" boolean's existing meaning (container/service liveness) — the entity check is an additive, separately-reported fact, not a redefinition of the existing pass/fail.

**Auto verify marker resolved 2026-09-14 (was: `2026-09-14 03:15 MST`) — checked live, found a real unhandled crash, fixed same session.** `systemctl status reboot-health-check.service` showed the service **failed** at 03:03:21 (today's actual scheduled-reboot run) — `subprocess.TimeoutExpired: Command '['docker', 'logs', '--since', '10m', 'homeassistant']' timed out after 15 seconds` inside `_slow_loading_domains()`. The `except (urllib.error.URLError, KeyError, ValueError)` around the entity-check block didn't catch `subprocess.TimeoutExpired`, so the exception propagated all the way up and crashed the script **before it ever published the retained MQTT fact or the plain `healthy` check** — worse than just losing the entity_check half, the whole reboot-health report silently never went out this reboot. (The `docker logs` call itself is fast under normal conditions — re-ran it manually afterward, 0.87s — so this looks like a real, if transient, boot-time slowdown, not a broken command.)

**Watch for:** a real reboot where `smartthings`/`ring`/`samsungtv` (or anything else) actually lands on HA's "Waiting for integrations to complete setup" slow-loading list within the 10-minute `docker logs --since 10m` window — confirms the auto-reload/Alert path end-to-end on real data, not just that the crash is fixed. Today's crash masked whatever the real list was (if any), so this is still fully unobserved, not just unlucky timing.

**Checked 2026-09-15 via CLAUDE.md's Session Start Watch-for check — the underlying condition genuinely recurred, but the automated path is still unconfirmed, not because it's untested but because it hit another timeout.** During the CARD-0248 shutdown-hook debugging session the day before (2026-09-14, five back-to-back `docker restart homeassistant` calls between 13:04-13:27 MST, not a real Pi reboot), `docker logs homeassistant` independently confirmed (checked directly, not via the script) that `smartthings` (13:10:03), then `samsungtv`+`ring` together (13:21:52), then `stream` (13:28:43) all genuinely landed on the slow-loading list — exactly the scenario this Watch-for exists to catch. But `reboot-health-check.py` itself, which did run each time (`jctsh-core | System | Docker containers starting after scheduled reboot - homeassistant:starting` logged five times in that window), hit the entity-availability check's `docker logs` call timing out again at 13:28:08 MST — `jctsh-core | Alert | Reboot health check: entity-availability check failed (timed out).` This is the *new*, already-fixed graceful-degradation behavior (an Alert instead of a crash — confirms that part of the 2026-09-14 fix works), but it also means the actual question this Watch-for asks — did `smartthings`/`ring` get auto-reloaded and did `samsungtv` get correctly flagged, not auto-reloaded — is **still unconfirmed**, masked by a second timeout rather than the first one. Current entity-availability count wasn't re-checked as part of this pass. Worth deciding whether the 15s `docker logs` timeout itself is too tight for boot-time conditions (this is now two masked attempts in a row) rather than continuing to wait passively for a cleaner window.

**Checked 2026-09-22 08:55 MST (ops cluster session startup) against the 2026-09-21 real scheduled reboot — the crash/timeout fix holds, but the Watch-for is *still* unobserved, and this pass found a third, different way the check can silently report a false all-clear.** The good news first, checked live: `systemctl status reboot-health-check.service` on the Pi shows the 2026-09-21 run completed cleanly — `Active: inactive (dead) since Mon 2026-09-21 03:06:48 MST`, `status=0/SUCCESS`, no crash and no timeout, the first fully clean real-reboot run since CARD-0249's fix. The retained `jctsh/core/jctsh-core/reboot-health` fact published correctly and reads: `{"last_reboot": "2026-09-21 03:00:48", "healthy": true, "checks": {"homeassistant": "healthy", "nodered": "active", "mosquitto": "active"}, "entity_check": {"unavailable_before": 0, "unavailable_after": 0, "auto_reloaded": {}, "watch_domains": []}}`. So the mechanism ran end-to-end — but with an empty `watch_domains`, meaning nothing landed on HA's slow-loading list inside the 10-minute window, so the actual question (does `smartthings`/`ring` auto-reload fire, does `samsungtv` get flagged-not-reloaded) remains **unobserved for a third consecutive real reboot**. Marker stays open; card stays in Build.
- **New finding — `unavailable_before: 0` is not credible, and the script can't currently tell "0 unavailable" from "entities don't exist yet."** Checked the same API live this session: HA now reports **54 unavailable of 998 entities**, consistent with CARD-0240's known-normal ~52–53 SmartThings-hub baseline (and the 52 this script itself recorded on 2026-09-06 and 2026-09-14). A genuine 0 at 03:06 MST — six minutes after a 03:00:48 boot — would mean those ~53 permanently-offline devices briefly came online and went away again, which is not plausible. Far more likely: at six minutes post-boot the SmartThings entities had not been registered in `/api/states` *at all* yet, so they counted as absent rather than `unavailable`. The script only records the unavailable **count**, never the **total** entity count, so nothing in the published fact distinguishes those two cases — a genuinely clean boot and a boot where HA simply hadn't finished populating the state machine both serialize to `unavailable_before: 0`. Cheap fix in the same spirit as the existing fields: also publish `total_entities` alongside `unavailable_before`/`unavailable_after` (a run reporting `0 unavailable of ~120` is obviously premature; `0 unavailable of ~998` would be real), and consider whether the check should wait on a settled entity count rather than firing a fixed interval after the container reports healthy. ~~Not yet decided or built — recorded here rather than acted on, since it changes a deployed scheduled script (runtime code) and warrants Joseph's go-ahead.~~ **Built and deployed same session — Joseph's go-ahead given 2026-09-22 09:15 MST ("do it"), see below.**

**`total_entities` built, deployed, and verified live, 2026-09-22 09:25 MST.** `_unavailable_count()` in `core/maintenance/reboot-health-check.py` became `_entity_counts()`, returning `(unavailable, total)`; `entity_check` now publishes `total_before`/`total_after` alongside the existing `unavailable_before`/`unavailable_after`, and the `watch_domains` Alert message now reads "N of M entities unavailable at boot" instead of the bare count. Purely additive — no existing field renamed or removed, and `log_server.py` was checked directly (it consumes only `healthy`/`last_reboot`/`checks` from this fact and ignores `entity_check` entirely), so nothing downstream could break. Deployed to `/usr/local/bin/reboot-health-check.py` via `sudo install -m 755`, syntax-checked on the Pi with the target interpreter, then **run for real**: exit 0, and a direct `mosquitto_sub` read of the retained fact returned `"unavailable_before": 54, "total_before": 998, "unavailable_after": 54, "total_after": 998`. That single run is itself the proof the diagnosis was right — the same code path that published `0` six minutes after the 2026-09-21 boot reports 54 of 998 at a settled time.

**Deliberately *not* added: any "total looks too low" threshold or alert.** There is no history of real per-boot totals to derive one from — one settled-state reading is not a baseline — and this project's Engineering Discipline explicitly calls for a measured threshold over a guessed one (CARD-0193's own precedent). The field is what starts collecting that history; revisit once a few real scheduled reboots have recorded their totals, at which point "premature read" becomes a number rather than a judgment call. Recorded in the function's own docstring so the reasoning doesn't have to be rediscovered from this card.
- Config-entry state re-checked the same pass, so the allowlist is confirmed still meaningful: 28 config entries, with `smartthings`, `ring`, and `samsungtv` all present and `loaded` — `AUTO_RELOAD_DOMAINS`/`WATCH_ONLY_DOMAINS` still name integrations this install actually has. (`bluetooth` is in `setup_retry`, unrelated to this card and outside this cluster's scope — noted only so the observation isn't lost.)

**Fixed and deployed 2026-09-14, same session:** broadened the except clause in `core/maintenance/reboot-health-check.py` to also catch `subprocess.SubprocessError` (covers `TimeoutExpired`/`CalledProcessError`) and `OSError`, so a `docker logs` hiccup now degrades to a logged/alerted `entity_check.error` instead of crashing the whole script before the core `checks`/`healthy` fact publishes. Deployed to `/usr/local/bin/reboot-health-check.py`, syntax-checked, and run manually — completed cleanly this time: `{"healthy": true, "checks": {...}, "entity_check": {"unavailable_before": 52, "unavailable_after": 52, "auto_reloaded": {}, "watch_domains": []}}`, confirmed via a direct `mosquitto_sub` read of the retained fact. `unavailable_before`/`after` of 52 matches CARD-0240's known-normal SmartThings-hub baseline — not a new problem.

**Done when:** deployed to the Pi, and confirmed live against a real reboot — **partially met**. The fix is deployed and proven not to crash on a manual re-run, but this specific manual run happened ~14.5 hours after the actual boot (past the 10-minute `docker logs --since 10m` detection window for whatever caused today's original slow-loading list, if anything did) — so it confirms the crash is fixed, not that `smartthings`/`ring` auto-reload or a `samsungtv`-class Alert actually fires correctly end-to-end against a real slow-loading boot. Left in Build pending confirmation against the *next* real scheduled reboot, this time without the crash masking the result.

**Real bug caught and fixed before this could be called verified, 2026-09-06.** The boot log's actual format, checked against the Pi's own real logs, isn't the bracketed list assumed above — it's a dict-of-tuples (`{('samsungtv', '01KZ...'): 233.7, ('mqtt', '01KS...'): 442198.3, ...}`), which the original `\[(.*?)\]` regex would never have matched — `_slow_loading_domains()` would have silently always returned empty. Fixed with a tuple-extracting regex, verified against real captured log lines. **Second, more important correction found from that same real data:** a normal boot routinely lists several perfectly healthy integrations on this same line (`met`, `google_translate`, `cast`, `mqtt`, `denonavr`, `dlna_dmr`) that just took a little longer to finish setup — not integrations with CARD-0240's bug. Treating "anything named on this list" as suspect (the original framing) would have fired a false-positive Alert on nearly every reboot. Narrowed to two short, evidence-based lists instead: `AUTO_RELOAD_DOMAINS = (smartthings, ring)` and a new `WATCH_ONLY_DOMAINS = (samsungtv,)` — only intersected against the boot log's raw domain set, not the raw set itself.

**Deployed and verified live, short of forcing a real restart, 2026-09-06.** `HA_TOKEN`/`HA_URL` added to `/etc/jctsh/log-server.env` on the Pi (reusing the existing long-lived token). Script deployed to `/usr/local/bin/reboot-health-check.py`, run manually: correctly read `/api/states` (52 unavailable entities — consistent with CARD-0240's own known-normal SmartThings-hub baseline) and published the full `entity_check` fact (`unavailable_before`/`unavailable_after`/`auto_reloaded`/`watch_domains`) to the retained `jctsh/core/jctsh-core/reboot-health` topic, confirmed via a direct `mosquitto_sub` read. The domain-parsing regex was separately verified against real captured boot-log lines from today's actual HA restarts (correctly extracted `ring`+`samsungtv` from a mixed real line, correctly ignored `cast`/`mqtt` alongside them). The reload call itself (`POST /api/config/config_entries/entry/<id>/reload`) is proven working for both `smartthings` and `ring` specifically via CARD-0240's own manual use of the identical endpoint earlier the same day (203 → 53 unavailable). **Not yet triggered end-to-end live** — that needs a real `homeassistant` restart within the 10-minute detection window, and Joseph's call was to wait for the next real one (the Monday scheduled reboot, or any other real restart) rather than force one now, given restarting HA is the same action that caused today's Samsung TV pairing dialog. Left in Build pending that passive confirmation.

**Related:** CARD-0158 (`reboot-health-check.py`, the script this extends), CARD-0240 (the manual check and the boot-log-parsing detection technique this generalizes into an automated, scheduled-reboot-covering form), CARD-0246 (the session this was raised during, after the TV pairing dialog followed a Pi reboot), `CLAUDE.md` (Home Assistant Docker Setup section — the manual instruction this makes automatic for the reboot case specifically; the manual `docker compose up -d` case stays as-is since that's not this script's trigger).

---

### CARD-0246 · [bug] [pi1] Pi's systemd-journald uses volatile storage — all system logs wiped on every weekly reboot — RESOLVED 2026-09-06
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-10 (CARD-0193) — 7418B, over the 5000B size threshold.

---

### CARD-0245 · [bug] [data-pipeline] Hike Start Forecast session-gap check compares against the wrong row — 48 spurious forecast captures on one real hike — RESOLVED 2026-09-06
**Status:** Done

Archived to `core/data-pipeline/CLAUDE.md` on 2026-09-10 (CARD-0193) — 5954B, over the 5000B size threshold.

---

### CARD-0244 · [bug] [data-pipeline] Hiking Observations ingest (`doPost`, `component=hiking-observations`) has no de-duplication — same class of gap as CARD-0243's GPS Track fix — RESOLVED 2026-09-06
**Status:** Done

Archived to `core/data-pipeline/card-archive.md` on 2026-09-28 (CARD-0193) — 4660B, over the 2000B size threshold.

---

### CARD-0243 · [bug] [data-pipeline] GPS Track ingest (`doGet`, `action=gps`) has no de-duplication — 29.5% of the 2026-09-03 hike's trackpoints are exact duplicates — RESOLVED 2026-09-06
**Status:** Done

Archived to `core/data-pipeline/CLAUDE.md` on 2026-09-10 (CARD-0193) — 10848B, over the 5000B size threshold.

---

### CARD-0242 · [bug] [hiking-monitor] `Hike-izer Done` Tasker Profile has no Extra filter — Task fires (and misleadingly Flashes "publish triggered") on every GPSLogger event, not just `stopped`

**Status:** Backlog

**Priority:** Low -- the card itself says low priority: a Tasker profile that misfires on every GPSLogger event is misleading, not harmful. (set 2026-09-29 15:38 MST; first set to Medium in the triage without reading the card, corrected here)

**Raised 2026-09-06**, found while exporting/reading the real `Hike-izer Done` Profile XML (CARD-0231's pattern; `components/hike-izer-orchestrator/tasker/Hike-izer-Done.prf.xml`) against `tasker-setup.md`'s own claim that the Profile has an `Extra: gpsloggerevent:stopped` filter. **It doesn't** — the exported Profile's Event condition has empty Extra name/value fields, so the `Hike-izer Webhook` Task fires on every GPSLogger broadcast (`started`/`stopped`/`fileuploaded`), not just the stop event.

**Not a correctness/data-integrity risk** — `app.py`'s `_handle_hike_end()` already restricts real hike-summary generation to `gpsloggerevent == "stopped"` server-side, so no bad data or duplicate generation results. Two real but low-stakes side effects:
1. **Misleading Flash.** "Hike-izer: publish triggered" fires on every event, including hike **start** — confusing, since nothing is actually published then.
2. **Wasted network calls.** `started`/`fileuploaded` events also POST to the public webhook, logged and discarded server-side — harmless noise, not a real cost.

**Fix:** re-add the `gpsloggerevent:stopped` Extra filter on the `Hike-izer Done` Profile itself (Tasker, phone-side — Joseph's own edit, matching this project's established division of labor for Tasker-side changes). Once done, re-export the Profile, replace `components/hike-izer-orchestrator/tasker/Hike-izer-Done.prf.xml`, and correct `tasker-setup.md`'s "server-side-only filtering" note back to "filtered at the Profile, working as originally designed."

**Done when:** the Extra filter is added on-device, a real test confirms the Flash/POST no longer fire on `started`/`fileuploaded` (only on `stopped`), and the re-exported Profile XML + doc note are updated to match.

**Related:** CARD-0086 (this Profile/Task's original build), CARD-0231 (the export-to-repo pattern that surfaced this), `components/hike-izer-orchestrator/tasker-setup.md`, `components/hike-izer-orchestrator/tasker/Hike-izer-Done.prf.xml`.

---

### CARD-0241 · [enhancement] [tos] Move Tasker build instructions out of component READMEs into dedicated docs, organized by conceptual owner not hosting container — RESOLVED 2026-09-05
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-09-10 (CARD-0193) — 6253B, over the 5000B size threshold.

---

### CARD-0240 · [enhancement] [homeassistant] Home Assistant container update available: 2026.9.0 → 2026.9.1 — RESOLVED 2026-09-05 13:47 MST
**Status:** Done

Archived to `core/homeassistant/CLAUDE.md` on 2026-09-10 (CARD-0193) — 7094B, over the 5000B size threshold.

---

### CARD-0239 · [enhancement] [hike-izer] Remote, phone-only trigger for hike-izer's step-2 gap-fill pass — no SSH required — RESOLVED 2026-09-06
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-09-10 (CARD-0193) — 6740B, over the 5000B size threshold.

---

### CARD-0238 · [enhancement] [m8] M8 OS maintenance: 25 routine updates, 10 flagged for review — includes Docker itself and linux-firmware — RESOLVED 2026-09-02
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-10 (CARD-0193) — 8225B, over the 5000B size threshold.

---

### CARD-0237 · [enhancement] [m8] cloudflared container update available: 2026.8.2 → 2026.8.3 — RESOLVED 2026-09-02
**Status:** Done

Archived to `hosts/m8/card-archive.md` on 2026-09-28 (CARD-0193) — 2430B, over the 2000B size threshold.

---

### CARD-0236 · [enhancement] [netalertx] NetAlertX container update available: 26.8.5 → v26.9.0 — RESOLVED 2026-09-02
**Status:** Done

Archived to `components/netalertx/card-archive.md` on 2026-09-28 (CARD-0193) — 2479B, over the 2000B size threshold.

---

### CARD-0235 · [idea] [hike-izer] BirdNET Live tracks continuous GPS during every hike — evaluate turning it off, but check the species-ID accuracy tradeoff first — RESOLVED 2026-09-02
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-09-10 (CARD-0193) — 13601B, over the 5000B size threshold.

---

### CARD-0234 · [bug] [hiking-monitor] GPSLogger errors "file didn't exist" on a normal hike start, self-heals on restart — RESOLVED 2026-09-28 17:36 MST
**Status:** Done

Archived to `components/hiking-monitor/card-archive.md` on 2026-09-28 (CARD-0193) — 5877B, over the 5000B size threshold.

---

### CARD-0233 · [enhancement] [homeassistant] Home Assistant container update available: 2026.8.2 → 2026.8.3 (landed on 2026.9.0) — RESOLVED 2026-09-02
**Status:** Done

Archived to `core/homeassistant/CLAUDE.md` on 2026-09-10 (CARD-0193) — 5684B, over the 5000B size threshold.

---

### CARD-0232 · [idea] [hiking-monitor] Photo-based plant identification, integrated into Hiking Observations
**Status:** Planning

**Raised via idea email (PR #46, joscthomas+kbc@gmail.com), 2026-08-29** — raw finding text was just "plant identification"; not yet interviewed for what triggered it or what "done" would look like.

**Interviewed 2026-09-14 (Joseph), via AskUserQuestion — real scope now confirmed:**
1. **Trigger for the idea:** wanted to identify a specific plant encountered on a hike, not general curiosity or copying another app.
2. **Mechanism: API-based, integrated into the pipeline** — not just pointing at an off-the-shelf phone app (Google Lens, PictureThis). A plant-ID API call, in the same spirit as BirdNET's audio-ID precedent (CARD-0080/`birdnet-pipeline.md`), confirming the "likely context" guess below.
3. **Integration: feeds into Hiking Observations**, not a standalone tool — identified plants should land in the existing `vegetation`-category data alongside other hike observations (`core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`).
4. **Trigger flow: automatic** — every photo taken while hiking-monitor's field mode is active gets run through the ID pipeline, no manual per-photo action required.
5. **Done when (confirmed):** one real hike where a real plant photo is correctly identified end-to-end and the result lands in the Hiking Observations data — a live field test, not just a bench-level API check.

**Current stopgap, noted 2026-09-14 (Joseph):** all hike photos are currently already being sent to Claude, which sometimes correctly identifies a plant — informal, no structured output, not integrated into Hiking Observations. This is the real baseline a dedicated API needs to beat/replace, not a cold start.

**Real finding, 2026-09-14 (Claude, reading the actual code) — this "stopgap" is not ad hoc, it's CARD-0107's existing photo-captioning pipeline, and it already does plant ID.** `components/hike-izer-orchestrator/photo_captions.py` calls `claude-opus-4-8` (line 26) via `client.messages.parse()` with structured output (`PhotoObservation`: `caption` + `sign_text` fields, `max_tokens=400`) on every hike photo, prompted to name "a specific plant or wildlife species... but ONLY if that identification adds something a viewer can't already see." Real captured examples already include species-level plant IDs: `"Trumpet vine (Campsis radicans) in bloom"`, two distinct Rose of Sharon captions (CARD-0107 archive, `components/hike-izer/CLAUDE.md`). This changes the shape of this card considerably:
- **Photo resizing already happens and is proven not to hurt accuracy for this purpose.** `fetch_hike_photos.py` (`components/hike-izer/fetch_hike_photos.py:151`) downloads Immich's `thumbnail?size=preview` (~1440px long edge JPEG), not the original — `photo_captions.py` sends only that thumb to Claude. A real CARD-0107 test (2026-07-28, 3 photos) found identical identification quality at ~24% lower cost vs. the original, though that's a small sample, not a rigorous eval.
- **Cost is already tracked per-hike for real** (`cost_tracking.py`: $5/$25 per 1M tokens for opus-4-8), and **captions are cached** — a photo already captioned is never re-sent (CARD-0214), so this already-running pipeline costs nothing extra per repeat pass.
- **Gap vs. this card's goal:** `photo_captions.py`'s output is a display caption + alt text, not structured species data, and it never touches the Hiking Observations `vegetation` category — the plumbing from "Claude named a plant" to "it's in the vegetation data" doesn't exist yet.
- **Revised design direction, not yet confirmed with Joseph:** this may not need a whole new dedicated plant-ID API pipeline. Two options worth weighing at real Planning: (a) extend `photo_captions.py` to also emit a structured species field (when confidently identified) and write it into Hiking Observations directly — no new API, reuses a pipeline already proven accurate and already paid for; or (b) keep Pl@ntNet/Plant.id as a second-opinion/confidence-booster specifically for photos where Claude's caption comes back empty on the plant front. Either way, Claude's existing captioning is the real baseline to beat, not a naive substitute for it.

**API research, 2026-09-14 (Claude, web search) — candidates compared:**
- **Pl@ntNet — leading candidate to try first.** No account/API key needed for basic use; pay-per-event pricing, roughly $8 per 1,000 identifications. Trained specifically on crowdsourced *wild* plant photos (not houseplants/nursery stock) across 81,693 species — a good match for desert trail flora (saguaro/ocotillo/palo verde already in the `vegetation` taxonomy). Returns a structured species + confidence score, which is far easier to feed into a pipeline automatically than parsing Claude's freeform text.
- **Plant.id (Kindwise)** — a real, credible alternative. Independent academic studies found it outperformed PlantNet, iNaturalist, and Google Lens for British flora and for alien street-tree ID specifically. Also does plant health/disease detection (not needed here). Pricing tiers weren't confirmed by the search — would need to check `admin.kindwise.com` directly before committing.
- **iNaturalist — ruled out.** Its full species-classification computer vision model is kept private (IP reasons); only small ~500-taxon on-device research models are public, not a general hosted identification API. Extra work to make usable, no clear win over Pl@ntNet/Plant.id.
- **Real photo/cost data pulled from the M8, 2026-09-14 (Claude, `ssh jct@m8.local`, reading the actual manifest files under `/home/jct/hike-izer-web-app/srv/`)** — across 20 real hikes (2026-06-18 through 2026-09-10): **139 total photos, 116 actually captioned** (23 sat on hikes where only the data-only "step 1" page was ever published). Of 108 non-empty captions, hand-classified: **64 are genuine plant-species identifications**, 16 are wildlife-primary captions naming a plant substrate (e.g. "Carpenter bee foraging on white hydrangea blossoms"), 28 are non-plant subjects (mostly Chihuly glass sculptures from one Meijer Gardens hike, plus a scarecrow, a car, a trail marker, coyote scat). **Caveat:** the July 29 Meijer Gardens hike is a cultivated botanical garden, not wild desert trail flora — its plant IDs (dahlias, hardy hibiscus cultivars) are a different test case than Pl@ntNet's wild-plant training strength; the desert hikes (Aug 13 onward) are the representative sample for this card's actual use case.
- **Real cost figure not available — a genuine gap, now tracked separately as CARD-0270.** The orchestrator container's stdout (the only place `CostTracker.summary()` ever printed) was wiped by an M8 reboot/container-log reset before this could be pulled. Estimated from real token math instead (opus-4-8, high-res tier, ~1440px thumbs, ~1500-2000 image tokens + ~300 prompt tokens/call, $5/$25 per 1M): **roughly $1-$2 total spent captioning all 116 photos to date** — genuinely trivial regardless of the exact figure.
- **Generic vision APIs (Google Cloud Vision, etc.) — ruled out.** Object/label detection only, not species-level plant ID — a step backward from what Claude already does today.
- **Recommendation, not yet confirmed with Joseph:** try Pl@ntNet first against a batch of real desert hike photos (including ones Claude got wrong or missed) as a real accuracy/cost check before committing; benchmark Plant.id only if Pl@ntNet's accuracy disappoints on local species.

**Still not yet scoped for Planning:** which design direction to take (extend `photo_captions.py` vs. bolt on a dedicated API vs. both — see revised design direction above), confirming API choice against real photos if a dedicated API is still wanted, how a hike photo actually reaches an external API automatically if needed (`photo_captions.py`'s existing per-hike-photo loop may already solve this for free), and how a returned/identified species gets written into the Hiking Observations `vegetation` category data shape either way.

**Related:** `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md` (Hiking Observations `vegetation` category), `components/hike-izer-orchestrator/birdnet-pipeline.md` (the audio-ID precedent this parallels), `components/hike-izer-orchestrator/photo_captions.py` (CARD-0107's existing photo-captioning pipeline this card may extend rather than replace).

---

### CARD-0231 · [idea] [tos] Investigate Tasker's task import/export capabilities — get profiles/tasks into a reviewable format — RESOLVED 2026-09-06
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-09-10 (CARD-0193) — 13278B, over the 5000B size threshold.

---

### CARD-0229 · [idea] [hike-izer] Review BirdNET data architecture — storage and MQTT messaging — RESOLVED 2026-09-02
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-09-10 (CARD-0193) — 19190B, over the 5000B size threshold.

---

### CARD-0228 · [bug] [tos] email-idea-check.py failures are invisible to the log dashboard — only successful PR-opens get logged — RESOLVED 2026-09-02
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 4240B, over the 2000B size threshold.

---

### CARD-0227 · [enhancement] [tos] Support an image attachment on `jctsh-idea` emails, surfaced in the resulting PR — RESOLVED 2026-08-29
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-09-10 (CARD-0193) — 12511B, over the 5000B size threshold.

---

### CARD-0226 · [bug] [hiking-monitor] Rapid MQTT-attributed reboot loop during hike-data replay -- trigger unconfirmed, replay path not robust to it
**Status:** Build

**Priority:** High -- a real data-loss risk on hike-data replay; the per-record delivery-tracking fix is decided and ready to build, only the root-cause hunt is blocked on an event. (set 2026-09-29 15:41 MST, triage)

**Moved to Build 2026-09-08 (Joseph's call, after discussion).** Item 1 (root cause identification) is genuinely blocked on the Watch for event below, but item 2 (per-record delivery tracking on the replay path -- QoS 1 with a real broker ack, per the design already specified below) is a decided, ready-to-implement fix that doesn't depend on that event at all. Matches this board's own precedent (CARD-0217/CARD-0196/CARD-0224) -- a card stays in Build with one part noted as blocked-on-event rather than sitting in Planning because of it.

**Raised 2026-08-29, split out of CARD-0221/CARD-0222** once investigating those two cards' shared root cause (a reboot loop during replay) turned into real, standalone firmware-design work rather than a one-line fix -- distinct enough to need its own thread.

**Confirmed, from hiking-monitor's own log history (`/mnt/jctsh-logs/state.json` on the Pi) for the 2026-08-29 hike:** the device reconnected at 08:45:23 MST and announced "Replaying 116 hike readings..." In the next 35 seconds it logged **10 separate field-mode boots** -- the first `reset reason: exiting deep sleep mode`, every one after that `reset reason: Reboot request from mqtt` (9 in a row).

**What "Reboot request from mqtt" actually means, confirmed by reading ESPHome's own debug component source (`debug_esp32.cpp`), not assumed:** on a graceful software restart (`App.reboot()`), ESPHome stores whichever component was "currently active" in the main loop at that instant into a flash preference; the *next* boot reads it back and prints `"Reboot request from <component>"`. So this string means **the mqtt component's own code was executing** when something called `App.reboot()` -- it does NOT mean an external MQTT command told the device to restart. Confirmed this is a deliberate, graceful restart, not a crash: a hardware watchdog panic reports its own reset reason directly (`"task watchdog"`, `"interrupt watchdog"`) and never goes through this reboot_source lookup at all.

**Three candidate triggers checked and ruled out, not assumed clear:**
1. **CARD-0180's HA-exposed restart button** (`button.hiking_monitor_restart`) -- ruled out via Home Assistant's own history API for the exact incident window: the entity's state has been `unknown`, completely unchanged, since 04:09 UTC that day, hours before the hike even started. Never pressed.
2. **ESPHome's built-in MQTT `reboot_timeout`** (15 minutes if the client can't reconnect, confirmed live in `mqtt_client.cpp`: `set_reboot_timeout(900000)`) -- ruled out by the math. The device *was* reconnecting successfully each cycle (real replay activity followed every reboot); 15 minutes doesn't fit a reboot every 3-4 seconds.
3. **A recurrence of CARD-0211's already-fixed task-watchdog crash** -- ruled out by the reset-reason mechanism itself (see above; a watchdog panic wouldn't route through the graceful-restart reboot_source path at all).
4. **Grepped the entire firmware for every `App.reboot()`/`App.safe_reboot()` call site** -- confirmed CARD-0180's button is the *only* explicit call anywhere in `hiking-monitor.yaml`. Since that's ruled out by (1), the actual trigger must be internal to ESPHome's own framework code, not yet identified.

**Not yet confirmed: the actual trigger.** All log-and-source-level investigation available without a live capture has been exhausted. Needs an actual live debug-UART capture (CARD-0205's whole purpose) during a real occurrence -- either the next time this happens naturally on a hike, or a deliberate bench reproduction (e.g. force a large buffered-reading count and trigger a replay while watching serial output live).

**Second, related but separable finding -- the replay path itself isn't robust to this kind of interruption, whatever the trigger turns out to be.** `hiking-monitor.yaml`'s replay logic (`hike_log_replay_stream`, around line 318) publishes every buffered reading with **MQTT QoS 0** (fire-and-forget, no delivery confirmation) in one continuous loop, and only clears the on-device SPIFFS buffer (`hike_log_clear()`) *after* the entire loop finishes without interruption. Two consequences: (a) a reboot mid-replay means nothing was marked as sent, so the *whole* buffer replays again from the top on the next successful pass, not a clean resume from where it left off; (b) QoS 0 gives zero delivery confirmation, so the device can't actually tell whether any individual reading reached the broker before moving on to clear the buffer. This is very plausibly why CARD-0221 (61.8% Environmental Data coverage) and CARD-0222 (84% GPS-correlation miss rate) both came out short despite the device eventually believing it had successfully replayed everything -- though whether the shortfall is genuine data loss vs. correctly-deduped repeated re-transmissions of the same early readings (per CARD-0215's duplicate-rejection guard) hasn't been fully disentangled yet.

**Second recurrence, found 2026-09-06 while analyzing the 2026-09-03 hike's data for anomalies — broadens the scope of what this bug even is.** `hiking-monitor`'s device log for that hike shows the identical anomalous signature — repeated `Field-mode boot, reset reason: Reboot request from mqtt` — but in a materially different shape than the 2026-08-29 incident this card was originally raised from:
- **Not confined to post-hike replay.** All 2026-08-29's reboots happened in one 35-second burst right after reconnect, during "Replaying N hike readings." The 2026-09-03 occurrence shows 8 field-mode boots with this same reset reason **spread across ~105 minutes of the live hike itself** (real event times, recovered from each boot's own "Display refreshed (field mode) at `<ISO timestamp>`" line: 15:21:23Z, 15:36:26Z, 15:51:23Z, 16:06:24Z, 16:21:28Z, 16:36:29Z, 16:53:27Z, 17:06:30Z) — not clustered in a single post-hike burst at all. All log lines were *relayed* together at 17:24 MST when the device docked, but the events they describe happened live, roughly 15 minutes apart, throughout the hike.
- **Ruled out as the device's normal field-mode cycle before treating this as a recurrence** — normal field mode wakes from deep sleep every 2 minutes (a different, expected reset reason) and only refreshes the display every ~20 minutes (`FIELD_DISPLAY_REFRESH_CYCLES = 10`, `hiking-monitor.yaml` line 930); every boot here instead carries the same "Reboot request from mqtt" signature CARD-0226 already established means an unexplained `App.reboot()` while the mqtt component was active — not a deep-sleep wake.
- **Direct, quantified consequence confirmed via `hike_data.json`'s own coverage numbers for this hike:** Environmental Data coverage was **7.3%** (9 of 124 expected readings), with gaps of 34/76/21/41/13 minutes — and three of the reboot-loop's own "Display refreshed at X" timestamps (`15:51:23`, `16:53:27`, `17:06:30`) exactly match environmental-data row timestamps, i.e. the device only got a reading out in the brief window right after each reboot before falling back into the loop. Same causal chain CARD-0221/CARD-0222 already suspected, now pinned to a specific hike with exact timestamp correlation rather than inferred.
- **Open scoping question this raises, not yet decided:** if the trigger fires during normal live operation and not just during the replay codepath, this card's title/framing ("during hike-data replay") may be narrower than the actual bug — worth revisiting whether the live-capture plan (below) should specifically try to catch a live-hike occurrence, not only a post-hike-replay one, since they may share one root cause or be two distinct triggers with the same symptom.
- **Real correction to this card's own Done-when item (2), surfaced by this recurrence's different shape:** the QoS-1/per-record-delivery-tracking fix is scoped specifically to `hike_log_replay_stream` — the post-reconnect catch-up mechanism for previously-*buffered* readings. It does essentially **nothing** for the 2026-09-03 shape of this bug: those gaps came from live readings that never got taken/published in the first place because the device kept rebooting *during* normal live operation, not from a buffered replay getting interrupted afterward. There was no buffer to make delivery-robust — the reading simply never happened. For this shape, item (1) (find and eliminate the actual trigger) is the only lever that helps; item (2) only addresses the 2026-08-29 shape (a rapid post-reconnect replay burst). Both shapes may share one root cause, but "fix item 2" cannot be treated as resolving the 2026-09-03 occurrence even after item 2 ships.
- **The reset-reason evidence itself is weaker than it first appears — worth not over-trusting it going forward.** `"Reboot request from mqtt"` doesn't mean an MQTT session was active or that MQTT-specific code caused the reboot — per this card's own finding above, it just names whichever ESPHome component happened to be "currently active" in the main loop's round-robin dispatch at the instant `App.reboot()` was called. The mqtt component's own reconnect-backoff housekeeping runs continuously regardless of actual connection state, so this label can appear whether the device is connected, disconnected, or has no signal at all — it doesn't actually implicate MQTT as the cause, just as whichever component happened to hold the CPU. Compounding that: **2 of the 8 field-mode boots on 2026-09-03 show a completely empty reset-reason string**, not attributed to any component — meaning the attribution mechanism itself doesn't always populate (possibly the same read-timing fragility CARD-0217 already flagged: `reset_reason_text` is "only safely readable once loop() is" running). Any future analysis should treat the reset-reason field as an unreliable, partial clue, not a diagnosis — reinforcing why a live UART capture (not more log-reading) is the only way this actually gets solved.

**Third recurrence, found 2026-09-08 while analyzing that day's hike data for anomalies — same shape as the 2026-09-03 occurrence, not the original 2026-08-29 replay-burst shape.** `hiking-monitor`'s device log for the 2026-09-08 hike shows 2 of its 4 field-mode wake cycles carrying the `Reboot request from mqtt` reset reason, ~15 minutes apart, during live hiking rather than a post-reconnect replay burst:
- Boot 1: `exiting deep sleep mode` → `Display refreshed (field mode) at 2026-09-08T14:29:38Z` (normal, the hike's first wake).
- Boot 2: **`Reboot request from mqtt`** → `2026-09-08T14:44:40Z`.
- Boot 3: **`Reboot request from mqtt`** → `2026-09-08T14:59:40Z`.
- Boot 4: `exiting deep sleep mode` → `2026-09-08T16:24:45Z` (normal — Joseph deliberately powered the device down for an extended rest-break battery-conservation stretch between boots 3 and 4, confirmed by him directly and consistent with the device's own `Entering deep sleep` log line at 07:26:58 MST/14:26:58Z lining up with the hike's very start, not with this gap specifically).
All log lines were relayed together at 09:38 MST when the device reconnected, but the boot events themselves happened live, matching the 2026-09-03 recurrence's "spread across the hike, not clustered post-replay" shape, not 2026-08-29's tight 35-second burst. No new information on the actual trigger — still consistent with everything already established above, just a third confirmed sighting.

**Fourth recurrence, found 2026-09-10 via CLAUDE.md's Session Start Watch-for check — same "spread through the live hike" shape as the 09-03 and 09-08 occurrences.** `hiking-monitor`'s device log for the 2026-09-10 hike shows 4 of its 5 field-mode wake cycles carrying an anomalous reset reason (2 blank, 2 `Reboot request from mqtt`), spaced roughly 13-17 minutes apart:
- Boot 1: `exiting deep sleep mode` → `Display refreshed (field mode) at 2026-09-10T13:06:03Z` (normal, the hike's first wake).
- Boot 2: **blank reset reason** → `2026-09-10T13:23:00Z`.
- Boot 3: **`Reboot request from mqtt`** → `2026-09-10T13:36:03Z`.
- Boot 4: **blank reset reason** → `2026-09-10T13:53:03Z`.
- Boot 5: **`Reboot request from mqtt`** → `2026-09-10T14:06:06Z`.
All log lines were relayed together at 07:20 MST when the device reconnected, but the boot events themselves happened live across a full hour (13:06Z-14:06Z), matching the 09-03/09-08 spread-through-the-hike shape, not 08-29's tight post-replay burst. Four occurrences in 12 days now — no new information on the actual trigger, still not caught on a live UART capture. **CARD-0205's debug UART setup should run on the next hike**, per this card's own Watch-for instruction — a caught-live occurrence is still the only thing that advances item (1) past ruled-out candidates.

**Direct, quantified consequence confirmed via `hike_data.json`'s own coverage numbers for this hike, same analysis as the 2026-09-03 recurrence.** Environmental Data coverage was **18.4%** (7 of 38 expected readings), with four gaps of 13.0/21.1/21.0/8.0 minutes. Two of the seven surviving readings (`13:23:00Z`, `14:06:06Z`) land at the *exact same timestamp* as boots 2 and 5's own "Display refreshed" events — the device only got a reading out in the brief window right after each reboot, same pattern as 09-03. Notably, **GPS Track was unaffected** — all 148 expected trackpoints landed (98% coverage, no gaps over 62s, no duplicates) straight through the same reboot loop; only the slower/less-frequent environmental-sensor upload path took the hit. This is corroborating evidence for the existing causal chain (CARD-0221/CARD-0222), not a new bug.

**Done when:** (1) the actual reboot trigger is identified via a real live capture, not just ruled-out candidates, and fixed or confirmed benign; (2) the replay path tracks delivery per-record (e.g. QoS 1 with a real broker ack, removing just that one line once confirmed) instead of all-or-nothing, so a mid-replay interruption -- from this bug or any future one -- can't cost real data; (3) verified live against a real hike with a large buffered-reading count, confirming no reboot loop and no data shortfall. **Still not met** — nine recurrences now confirmed (2026-08-29, 2026-09-03, 2026-09-08, 2026-09-10, 2026-09-15, 2026-09-17, 2026-09-19, 2026-09-21, 2026-09-22), all adding evidence and confirming this isn't a one-off (2026-09-21/22 back-to-back, plus the new battery-dip-at-reboot-timestamp correlation found on those two), but none resolving anything: no live UART capture has happened yet (CARD-0205's debug setup isn't wired for this device at all, per the 2026-09-17 correction below), and the replay-path robustness fix (per-record delivery tracking) hasn't been built.

**Fifth recurrence, found 2026-09-15 via CLAUDE.md's Session Start Watch-for check — same "spread through the live hike" shape as 09-03/09-08/09-10, and the largest boot count yet.** `hiking-monitor`'s device log for the 2026-09-15 hike shows 15 of its 16 field-mode wake cycles carrying an anomalous reset reason (6 blank, 9 `Reboot request from mqtt`), roughly 15 minutes apart across nearly 4 hours:
- Boot 1: `exiting deep sleep mode` → `Display refreshed (field mode) at 2026-09-15T13:11:04Z` (normal, the hike's first wake).
- Boots 2-6: **`Reboot request from mqtt`** → `13:26:08Z`, `13:41:08Z`, `13:56:07Z`, `14:11:10Z`, `14:26:13Z`.
- Boots 7-8: **blank reset reason** → `14:41:10Z`, `14:56:11Z`.
- Boot 9: **`Reboot request from mqtt`** → `15:11:13Z`.
- Boots 10-12: **blank reset reason**, each also logging `Skipped reading - nan_sensor (temp=null, hum=null, pres=null)` → `15:28:13Z`, `15:43:14Z`, `15:58:15Z`.
- Boots 13-16: **`Reboot request from mqtt`** → `16:11:19Z`, `16:26:22Z`, `16:41:20Z`, `16:56:22Z`.
All log lines were relayed together at 10:42 MST when the device reconnected (159 buffered hike readings replayed), but the boot events themselves happened live across 13:11Z-16:56Z, matching the spread-through-the-hike shape, not 08-29's tight post-replay burst. Five occurrences in 17 days now. **New symptom, not seen on the prior four recurrences:** three of this hike's blank-reset-reason boots (10-12) each paired with a `Skipped reading - nan_sensor` line — the environmental sensor read out all-null immediately after those particular reboots, distinct from the already-understood "no reading published at all" pattern. Not yet analyzed against `hike_data.json` coverage numbers for this hike, and CARD-0205's debug UART still hasn't been run on a real occurrence — no new information on the actual trigger.

**Watch for (RESOLVED 2026-09-24, see the 2026-09-24 result below):** hiking-monitor's durable log showing a `"Reboot request from mqtt"` (or any blank/empty) field-mode reset-reason line from a hike **after 2026-09-22** — a tenth recurrence beyond the nine now logged above. Nine occurrences in 24 days suggests this happens on essentially every hike now; if it shows up, log it the same way as the prior nine (exact reset-reason text, real event timestamps via "Display refreshed" lines, which shape it matches, plus a check of whether the battery-dip-at-reboot-timestamp correlation found on the eighth/ninth recurrences holds again). ~~CARD-0205's debug UART setup is still flagged to run on the next hike regardless, so the next occurrence has a real chance of being caught live~~ — **corrected below, 2026-09-17: this was never actually possible on this device.**

**Real correction, 2026-09-17 (Joseph): hiking-monitor's current hardware is not wired to support UART capture at all.** Every recurrence note above (2026-09-10's, this Watch for, and others) repeated the same wrong assumption — that CARD-0205's debug-UART setup could simply be run against hiking-monitor on its next hike. CARD-0205 was built specifically for **air-quality-monitor** (its own card tag, archived to `components/air-quality-monitor/CLAUDE.md`) — hiking-monitor's own perfboard was never wired for a debug UART tap, so there has never actually been a way to "just run it on the next hike" as five separate notes above assumed. This isn't a missing step that was merely skipped; it's been impossible on this specific, already-assembled hardware the whole time. **Practical consequence:** a live capture of the actual trigger is not available without either (a) a physical rework of the current perfboard to add UART wiring — same category of cost as CARD-0070/CARD-0201/CARD-0202, all deliberately deferred to the v2 rebuild rather than reopening the field-proven current build — or (b) waiting for CARD-0259 (hiking-monitor v2, built on air-quality-monitor's proven power/debug architecture, UART included by design). The "Kept open independent of CARD-0259" call below was made assuming a cheaper live-capture path existed in parallel; worth Joseph revisiting whether that's still the right call now that the only two real paths are "rework this hardware" or "wait for v2," not "catch it live on the next ordinary hike."

**Durable fact moved to its real home, same date.** This is a hardware-capability attribute of the component itself, not really investigation history — burying it only in this card's narrative (which eventually archives away) means the next person/session to ask "can we UART-debug this?" has to rediscover it from scratch. Documented properly in `components/hiking-monitor/wiring.md`'s new **Debug UART — Not Wired On This Device** section (concrete cause: GPIO17, the exact pin air-quality-monitor's debug UART uses, is already committed here to the E-ink display's DC line) — this card's own text stays as the investigation record of how it was found, `wiring.md` is now the authoritative reference for the fact itself.

**Sixth recurrence, found 2026-09-17 via CLAUDE.md's Session Start Watch-for check — same "spread through the live hike" shape as 09-03/09-08/09-10/09-15, smallest boot count of the spread-shape occurrences so far.** `hiking-monitor`'s device log for the 2026-09-17 hike shows 4 of its 6 field-mode wake cycles carrying an anomalous reset reason (1 blank, 3 `Reboot request from mqtt`), roughly 15 minutes apart across ~75 minutes:
- Boot 1: `exiting deep sleep mode` → `Display refreshed (field mode) at 2026-09-17T13:29:08Z` (normal, the hike's first wake).
- Boot 2: **`Reboot request from mqtt`** → `13:44:13Z`.
- Boot 3: **blank reset reason** → `13:59:10Z`.
- Boot 4: **`Reboot request from mqtt`** → `14:14:12Z`.
- Boot 5: **`Reboot request from mqtt`** → `14:29:12Z`.
All log lines were relayed together at 07:53 MST when the device reconnected (57 buffered hike readings replayed), but the boot events themselves happened live across 13:29Z-14:29Z, matching the established spread-through-the-hike shape. Six occurrences in 19 days now — still no live UART capture (CARD-0205 not yet run on an actual occurrence), no new information on the trigger. **`hike_data.json` coverage numbers, filled in 2026-09-22:** Environmental Data coverage 72.1% (31 of 43 expected readings), 1 gap over 6min. Battery voltage shows a real, isolated dip at three of the five reboot timestamps (13:59:10Z 3.97V, 14:14:12Z 3.94V, 14:29:12Z 3.91V -- each ~0.2V below its immediate neighbors, recovering by the next reading), a pattern later found to generalize across other recurrences too (see the ninth recurrence's note below). **Possibly relevant:** this same hike's whole-day session probe also hit CARD-0258's 240s GPS Track timeout, ~3 minutes after this reboot loop's log lines relayed (07:56:34 MST) — a third instance of the two cards' loosely-correlated "load right at reconnect" timing, per CARD-0258's own note.

**Seventh recurrence, found 2026-09-19 via CLAUDE.md's Session Start Watch-for check — same "spread through the live hike" shape as 09-03/09-08/09-10/09-15/09-17, largest boot count yet.** `hiking-monitor`'s device log for the 2026-09-19 hike shows 14 of its 15 field-mode wake cycles carrying an anomalous reset reason (2 blank, 12 `Reboot request from mqtt`), roughly 15 minutes apart across ~3.5 hours:
- Boot 1: `exiting deep sleep mode` → `Display refreshed (field mode) at 2026-09-19T13:06:55Z` (normal, the hike's first wake).
- Boots 2-13: **`Reboot request from mqtt`** → `13:21:56Z`, `13:36:55Z`, `13:51:57Z`, `14:06:57Z`, `14:21:58Z`, `14:37:02Z`, `14:52:02Z`, `15:07:03Z`, `15:22:05Z`, `15:37:07Z`, `15:52:07Z`, `16:07:08Z`.
- Boots 14-15: **blank reset reason** → `16:22:07Z`, `16:36:28Z`.
All log lines were relayed together at 09:43 MST when the device reconnected (138 buffered hike readings replayed, "Hike log replay complete." logged), but the boot events themselves happened live across 13:06Z-16:36Z, matching the established spread-through-the-hike shape. Seven occurrences in 21 days now — still no live UART capture (CARD-0205 not wired for this device, per the 2026-09-17 correction above), no new information on the trigger. **`hike_data.json` coverage numbers, filled in 2026-09-22:** Environmental Data coverage 18.4% (19 of 103 expected readings), 11 gaps over 6min -- the worst coverage of any recurrence analyzed so far, consistent with this being the largest boot-count recurrence (12 of 15 wake cycles anomalous). Battery voltage shows an isolated dip at one reboot timestamp with a surviving reading (13:51:57Z, 3.88V vs 4.10-4.15V neighbors); most of the other reboot timestamps have no surviving reading at all to check, consistent with the theory that on the worst recurrences the affected reading is lost entirely rather than merely reading low. **Checked for CARD-0224 overlap:** no `"Replay deferred - battery..."` line this session — battery was healthy (4.26V at 06:03 MST, well above the 3.4V cutoff) going into the hike, so this recurrence doesn't bear on CARD-0224's own still-open Watch for.

**Eighth recurrence, found 2026-09-22 (hike-izer cluster session, analyzing the last two hikes for anomalies) — the 2026-09-21 hike, same "spread through the live hike" shape as recurrences 2-7.** `hiking-monitor`'s device log for the 2026-09-21 hike shows 5 of its 6 field-mode wake cycles carrying an anomalous reset reason (1 blank, 4 `Reboot request from mqtt`), roughly 15 minutes apart across ~75 minutes:
- Boot 1: `exiting deep sleep mode` → `Display refreshed (field mode) at 2026-09-21T13:32:38Z` (normal, the hike's first wake).
- Boot 2: **`Reboot request from mqtt`** → `13:47:36Z`.
- Boot 3: **`Reboot request from mqtt`** → `14:02:39Z`.
- Boot 4: **`Reboot request from mqtt`** → `14:17:38Z`.
- Boot 5: **blank reset reason**, also logging `Skipped reading - nan_sensor (temp=null, hum=null, pres=null)` → `14:34:39Z`.
- Boot 6: **`Reboot request from mqtt`** → `14:47:43Z`.
All log lines were relayed together at 07:54 MST when the device reconnected (56 buffered hike readings replayed, "Hike log replay complete." logged), but the boot events themselves happened live across 13:32Z-14:47Z, matching the established spread-through-the-hike shape (this took a careful re-read to see: the local relay timestamps all cluster within one 10-second window at 07:54:47-07:54:57 MST, which reads at first glance like the original 08-29 tight-burst shape, but the *embedded* "Display refreshed" timestamps are what actually matter, per this card's own established methodology, and those are spread 15 minutes apart same as every recurrence since 09-03). **`hike_data.json` coverage numbers:** Environmental Data coverage 58.1% (25 of 43 expected readings), 2 gaps over 6min (8.0min, 7.0min). **New corroborating angle — battery voltage dips line up exactly with reboot timestamps:** three of this hike's readings show an isolated ~0.15-0.3V dip below both neighbors, recovering by the next reading, and all three land on an exact reboot timestamp: `13:47:36Z` (4.02V vs 4.16/4.14V neighbors), `14:02:39Z` (3.98V vs 4.11/4.12V), `14:47:43Z` (3.75V vs 4.03/4.02V, the sharpest). This wasn't checked on the earlier recurrences at the time they were logged — worth treating as a real clue going forward, not just a coincidence: a voltage sag at the exact instant of an unexplained `App.reboot()` is consistent with a brownout-style trigger (the same physics `JCTsh-Build-Standards.md` §2.14 point 9 documents for WiFi-burst current spikes, though these are field-mode readings with no WiFi active, so the current-spike source here would have to be something else — the sensor read/SPIFFS-write cycle itself, most likely). No new information on the actual trigger's identity — still not caught on a live UART capture.

**Ninth recurrence, found 2026-09-22 (same session) — the 2026-09-22 hike, same day this analysis was run, same shape again.** `hiking-monitor`'s device log for the 2026-09-22 hike shows 5 of its 6 field-mode wake cycles carrying `Reboot request from mqtt` (none blank this time), roughly 15 minutes apart across ~75 minutes:
- Boot 1: `exiting deep sleep mode` → `Display refreshed (field mode) at 2026-09-22T13:33:17Z` (normal).
- Boot 2: **`Reboot request from mqtt`** → `13:48:15Z`.
- Boot 3: **`Reboot request from mqtt`** → `14:03:20Z`.
- Boot 4: **`Reboot request from mqtt`** → `14:18:19Z`.
- Boot 5: **`Reboot request from mqtt`** → `14:33:18Z`.
- Boot 6: **`Reboot request from mqtt`** → `14:48:22Z`.
Relayed together at 07:59 MST on reconnect (58 buffered hike readings replayed). **`hike_data.json` coverage numbers:** Environmental Data coverage 61.4% (27 of 44 expected readings), 1 gap over 6min (9.0min) — no missing-GPS-coordinate readings this time (0 of 27), unlike the 09-21 hike (2 of 25), so this recurrence's data loss is cleanly attributable to the reboot loop alone, not compounded by a separate GPS-correlation miss. **The battery-dip correlation from the eighth recurrence holds again, this time at every single reboot:** all five post-normal-boot readings show the same isolated dip-and-recover pattern, and all five land exactly on a reboot timestamp — `13:48:15Z` (3.98V vs 4.15/4.12V), `14:03:20Z` (3.93V vs 4.10/4.09V), `14:18:19Z` (looked but this reading's own value wasn't itself a standout dip, listed for completeness), `14:33:18Z` (3.71V vs 4.03/4.03V, the sharpest of either hike), `14:48:22Z` (3.84V vs 4.00/4.00V). Two hikes in a row, 8 of 9 reboot-adjacent readings checked so far show this exact pattern — strong enough now to treat as a real, reproducible signature of the trigger event, not noise. Still no live UART capture; still no new information on the trigger's actual identity.

**Major new lead, 2026-09-22 (same session, prompted by Joseph's own follow-up questions) — the `reboot_timeout`/`wifi.ap:` interaction CARD-0045 closed as "moot" in 2026-08-27 may not actually be moot, and air-quality-monitor's own firmware already found and fixed the identical symptom two weeks later.**

**What CARD-0045 actually concluded, re-read closely:** its resolution reasoned that once WiFi is genuinely `wifi.disable()`'d during field mode (CARD-0217's fix, same day), "there's no unbounded retry loop for that ESPHome bug to ever interact with in the first place" -- i.e., disabling WiFi makes ESPHome's built-in MQTT `reboot_timeout` (default 15min, confirmed via `mqtt_client.cpp`) moot, since nothing is ever trying to connect. **This was never field-verified** -- the card's own text says so directly ("confirmed correct by direct code inspection... not yet a live field observation"). CARD-0226's very first recurrence came two days later (2026-08-29).

**Checked against `components/air-quality-monitor/air-quality-monitor.yaml` directly, 2026-09-22.** AQM's own `mqtt:` block carries this comment: *"Bug found live 2026-09-09: ESPHome's mqtt component has its own built-in reboot_timeout (default 15min) that force-reboots the device if it can't connect within that window -- confirmed via mqtt_client.cpp's loop(), 'Can't connect; restarting'. This directly fights our own Step 8 bounded-attempt/15min-backoff state machine... ESPHome's own watchdog was rebooting the device right as our backoff neared completion, since nothing in our design ever calls the MQTT component's own enable() again to reset its last_connected_ timer."* Fixed there with a single line: `reboot_timeout: 0s`. **hiking-monitor's `mqtt:` block has no such line — it still runs ESPHome's 15-minute default**, confirmed by direct grep of `hiking-monitor.yaml` (only `wifi.disable`/`wifi.enable` calls exist, nothing touching `reboot_timeout`).

**Why this fits the observed evidence better than "unconfirmed, no failure observed" (CARD-0045's own 2026-07-09 assessment) ever anticipated:** AQM found, empirically, that disabling the underlying connection attempt does *not* stop the MQTT component's own internal `last_connected_` timer from accumulating -- it isn't reset just because nothing is actively trying. hiking-monitor's own multi-hour field-mode sessions (WiFi genuinely off the whole time, per CARD-0217/CARD-0045's fix) would accumulate exactly this kind of unreset elapsed time, and once it crosses 15 minutes, ESPHome's own framework code calls `App.reboot()` -- which is precisely why the reset reason reads `"Reboot request from mqtt"` (literally, accurately: the mqtt component itself requested it) rather than needing the more roundabout "whichever component happened to be active" explanation this card settled for earlier. It also matches the observed ~15-minute periodicity across every spread-shape recurrence far more precisely than anything else considered so far, and explains why it recurs regardless of battery health (a software timer, not a power event) -- consistent with both hikes checked today starting well above the 3.4V cutoff.

**Not yet confirmed as the actual root cause** -- this is a strong, evidence-backed hypothesis from cross-referencing a sibling device's own already-fixed identical bug, not a live capture (still not possible on this hardware, per the correction above). But unlike the live-capture path, **this is trivially, cheaply, reversibly testable on the current hardware right now:** add `reboot_timeout: 0s` to `hiking-monitor.yaml`'s `mqtt:` block (the exact line AQM already validated) and OTA-flash it -- no rebuild, no hardware change, one line. If the next hike shows zero `Reboot request from mqtt`/blank-reset-reason lines and full Environmental Data coverage, this closes CARD-0226 outright. Not yet done -- needs Joseph's go-ahead before flashing production firmware.

**Also worth revisiting: CARD-0045 itself** (archived, Done) -- its "moot" resolution rested on an assumption this new evidence directly contradicts. Not reopening it retroactively (it's archived, and the actual live investigation continues here), but worth Joseph knowing the closure reasoning there didn't hold up.

**Fixed and deployed, 2026-09-22 (same session, staged intentionally in two parts) — `mqtt.disable`/`mqtt.enable` mirrored alongside the existing `wifi.disable`/`wifi.enable` calls, porting AQM's own Step 9 (2026-09-14) validated fix.** ESPHome's `mqtt:` component keeps its own independent reconnect logic running regardless of radio state -- AQM's debug-UART capture proved this directly (a repeating "Couldn't resolve IP address" cycle with WiFi genuinely disabled the whole time) -- so `wifi.disable()` alone was never enough. Two call sites mirrored: the interval block's field-mode gate (`wifi.disable:` → now also `mqtt.disable:`) and `dock_detect`'s on_state handler (`wifi.enable:` → now also `mqtt.enable:`). Full file audited first for any other `id(mqtt_client)` usage that could interact badly with the component being explicitly disabled -- clean, every other reference just reads `.is_connected()` or calls `.publish()`.

**`reboot_timeout` deliberately left untouched, at ESPHome's default -- not bundled into this same fix, on purpose.** Real risk found and discussed before making any change: unlike air-quality-monitor (which has its own periodic bounded-retry state machine as a genuine replacement safety net, justifying its own `reboot_timeout: 0s`), hiking-monitor has no such mechanism yet (CARD-0259's own difference inventory confirms this is a v2-only addition). More importantly, **hiking-monitor has no physical power-cycle path in the field at all** -- confirmed via `README.md`: `VOUT+` feeds the ESP32's `VIN` unconditionally, not gated by the slide switch, so the only true power-off is disconnecting the battery JST inside the sealed enclosure. ESPHome's `reboot_timeout`-triggered `App.reboot()` is therefore the *only* self-recovery mechanism this device has for any stuck-connection state, with no field-accessible fallback (CARD-0180's HA restart button needs MQTT connectivity to receive the command -- useless in exactly the scenario it would need to help with). Removing that safety net before confirming the mirroring fix alone actually eliminates the underlying reboot loop would risk trading a partially-working (if broken) recovery mechanism for none at all. **Staged plan:** ship the mirroring fix alone first, verify against a real hike; only remove `reboot_timeout` as a separate, later step if the reboot loop still recurs despite mirroring being live (real evidence it's needed), rather than removing it speculatively now.

**Deployed and verified live, 2026-09-22 18:24 MST.** `esphome config` validated clean; full compile succeeded (`config_hash=0xabe4d2eb`, `build_time_str=2026-09-22 18:07:22 -0700`) -- required pinning ESPHome to 2026.4.5 in this session's environment (the freshly-installed 2026.9.0/ESP-IDF 5.5.5 hit an unrelated, newer-toolchain SPIFFS-component-REQUIRES build error; 2026.4.5 matches what's actually running on the real device and compiled clean with zero code changes needed beyond this fix). OTA-flashed (`esphome upload --device 192.168.1.161`, "OTA successful"). Confirmed live on the log dashboard -- clean single reconnect, no Alert, no crash loop: `18:24:44 MST MQTT disconnected` → `18:24:46 MST Connected.` → `Hiking monitor online - ESPHome 2026.4.5, IP: 192.168.1.161` → `MQTT connected`.

**Not yet verified: whether this actually stops the reboot loop.** That only gets tested on the next real hike (field mode specifically) -- watch for whether the next hike's log shows clean `exiting deep sleep mode` reset reasons throughout, versus the `Reboot request from mqtt`/blank pattern recurrences 1-9 all showed.

**Result, 2026-09-24 -- first real hike after the 2026-09-22 mqtt-mirroring flash: the reboot loop did not recur.** The 2026-09-24 hike (06:43-10:26 MST, 7.73 mi) is the first hike since the fix went live, and hiking-monitor's durable log shows exactly **one** field-mode boot for the whole day -- `Field-mode boot, reset reason: exiting deep sleep mode` at 12:43:52 MST, on reconnecting at home -- and **zero** `Reboot request from mqtt`/blank reset reasons, versus 4-15 boots per hike on recurrences 1-9. The device's own `Display refreshed (field mode)` lines replayed as one clean, evenly-spaced 20-minute cadence (13:45Z through 17:05Z), with none of the clustered/repeated refresh timestamps the earlier recurrences showed. One clean hike is a strong signal (nine of nine prior hikes reproduced it), not yet proof -- leaving this in Build for a second/third clean hike before closing, per this card's own discipline.

**Same day, related and not yet fixed -- replay data loss (cause not yet isolated), 2026-09-24:** the device logged `Replaying 121 hike readings...` and `Hike log replay complete.`, but only **23** of those 121 reached the Environmental Data Sheet (~19%, scattered timestamps, not a prefix); the 2026-09-19 hike showed the same shape (138 replayed, 19 in the Sheet). No Alert was logged by the data handler. **`hike_log_clear()` (`hiking_logger.h`) truncates the SPIFFS log right after the publish loop with no delivery confirmation, so the ~98 missing readings are unrecoverable from the device and almost certainly everywhere else** (the log server records only the `/log` topic, not `/data`; not searched for other copies). **Narrowed the same day, evidence against the QoS 0 theory:** (1) all 12 non-reading records in the same replay stream (11 `display_refresh` + the boot `reset`, which ride the identical `/data` topic and QoS 0 burst) arrived and were logged -- if the device->broker hop randomly dropped ~80%, ~2 of 12 would have survived, not 12; (2) a 121-message QoS 0/1 burst at 50 ms from a test client through the real broker arrived 121/121 (test topic `jctsh/test/replay-probe/data`, nothing written to Sheets). So the loss is most likely on the *reading* path only: Node-RED's GPS-lookup/POST leg or Apps Script (lock timeout / execution limits under the burst). **`env-data-check-response` (`environmental-data.flow.json`) silently `return null`s on any 405/302 or any response it can't parse as JSON, so a failed POST leaves no trace anywhere** -- consistent with zero Alerts despite ~98 missing rows. QoS 1 on the device may not fix this; make failures visible in `check-response` first, then re-measure on the next replay. (Node-RED's GPS throttle was checked: it queues, does not drop.) (AQM's QoS 0->1 change is a precaution only -- that device hasn't been used, so there is no loss evidence for it.)

**Isolated 2026-09-24 by a 5-hop end-to-end test -- the loss is in the Apps Script write path, reproduced without the device.** Test client published 121 readings (component `replay-test`, QoS 0, 50 ms apart -- the device's replay shape) through the real pipeline: **121/121 reached the broker, only 24 rows reached the Sheet (~20%, matching the real hike's 23/121 = 19%), zero Alerts logged.** Direct probes of the Apps Script: GPS lookups (hop 3) were healthy (121 x HTTP 200, slowest 31.5 s); **direct POSTs at Node-RED's 2/s pace (hops 4-5) returned 35 `ok`, 62 client timeouts (90 s), 24 HTML error pages -- yet only 11 rows persisted, i.e. ~24 `ok` responses wrote nothing.** Cause: the `else` (Environmental Data) branch of `doPost` in `environmental-data.gs` has **no `LockService` lock** around its full-column duplicate scan + `appendRow` (the wildlife/cost/scat/observation branches all lock), so concurrent executions under a burst overwrite each other's rows while still returning `ok`; each execution also scans the entire sheet, so executions run long and pile up into timeouts/error pages. Node-RED cannot see any of it: `env-data-check-response` counts a 405/302 (the redirect Apps Script always answers with) as success and silently ignores non-JSON bodies. **Ruled out: device QoS 0, the broker, the GPS lookup/throttle. The firmware QoS 1 change would not have helped.** Fix direction (not yet built): (1) `LockService` around the env branch's dedup+append; (2) Node-RED POSTs serially with the *real* response body checked, retrying anything not `ok`/`duplicate` (safe -- the (ts, source) dedup makes retries idempotent), and alerting on final failure; (3) optionally a batch POST (one execution appending many rows). Independently, Joseph's proposal to defer `hike_log_clear()` to the next switch-on (plus a replayed flag) makes any future loss recoverable. Test rows left in Environmental Data for Joseph to delete: source `replay-test` (24) and `replay-test-direct` (11).

**Fixes built and deployed 2026-09-24 (Joseph: "do fixes 1 and 2, then re-run the test", then "do fix 4" / "flash it").** (1) Apps Script Environmental Data write now takes a `LockService` lock and scans only the last 2000 rows for the duplicate check (`SCRIPT_VERSION 2026-09-24.1-env-write-lock`, redeployed by Joseph, confirmed via `?action=version`). (2) Node-RED (live tab `d15dbc9164b2dce9`, deployed via the Admin API; the repo file's readable node IDs differ from the live auto-generated ones, matched by name, no function drift) now POSTs through a serial queue: redirect-following disabled and the real reply fetched with a GET, replies classified ok/duplicate/rejected/retry, up to 5 retries with backoff, an Alert on final failure (mocked 16-check test passed). **Re-test, same 121-reading burst through the real pipeline: 121/121 rows landed twice (`replay-test2`, `replay-test3`; was 24/121), no alerts, ~5-8 min because posts are now serial.** The failure/retry path has not yet fired on a real error. (4) hiking-monitor firmware (`hiking-monitor.yaml`, ESPHome 2026.4.5, config_hash 0x126279d0, OTA-flashed 16:27 MST, came back online cleanly): the SPIFFS log is no longer cleared after replay -- a `restore_value` `hike_log_replayed` flag is set instead, replay is gated on it, and the log is cleared only when the intent switch turns ON *and* the log was already replayed (an unreplayed log is kept and appended to). New exposed HA button **Replay Hike Log** clears the flag and re-replays (safe to repeat -- Apps Script rejects an exact (ts, source) duplicate). Caveat: the switch-on hook also runs on any boot with the switch ON, so a reboot with it ON after a replay clears the retained log early. The firmware QoS 1 change originally proposed for this loss was dropped -- the test ruled QoS 0 out as the cause -- and the AQM's never-flashed QoS 1 change (`cf6b484`) was reverted to QoS 0 for the same reason. AQM carry-over noted on CARD-0012.

**Watch for:** the next real hike (after 2026-09-24) -- hiking-monitor's log shows exactly one `Replaying N hike readings...` at reconnect and no second replay on later connects, and the Environmental Data sheet then holds N rows for that hike (not ~20%); and after the following hike starts (switch ON) the retained log is gone (no stale readings replayed). If the counts still don't match, the Alert path now names the failing reading.

**Incident 2026-09-25 (reported by `jctsh-6a`) -- Environmental Data POSTs failing since ~10:07 MST; a Google-side Sheets problem, made worse by the serial queue's failure behavior (fixed).** Every Apps Script call that touches the spreadsheet (env POST, GPS lookup, even a tiny-sheet export) either hangs until timeout or intermittently returns a fast identical 5.6 KB error page, while `action=version` (never touches the sheet) answers in ~1 s -- so the spreadsheet backend is unhealthy, not the lock or the bounded scan (the export path takes no lock). Not yet resolved at the time of writing; whether Google recovers on its own, or something in the script is wedged, needs Joseph to look at the Apps Script Executions page (which a session cannot). **What was ours and is now fixed:** the serial queue gave up on a reading after 5 attempts (~11 min at 120 s per timeout), so an outage both **dropped readings permanently** and left the queue grinding one reading per ~11 min (queue was 46 deep, the oldest reading nearly 2 h old). Now a reading that exhausts its retries is *held*, probed once every 5 min, alerted at most once per 30 min, and only discarded after 24 h (poison-reading guard; queue also capped at 5000). The queue's held readings were snapshotted and re-injected across the redeploy (46 readings, nothing lost; Apps Script rejects duplicates). Also stripped URLs from the alert detail -- Node-RED's timeout text includes the full request URL (deployment id + key), which reached the log (relevant to CARD-0334). Open: an alert `undefined reading @ undefined` / `GPS lookup failed ... undefined reading` was seen once -- a /data message with no component or ts entered the pipeline; source not identified. Readings that were already dropped before this fix (from ~10:07 MST) are not in the sheet unless a late server-side execution completed; a backfill from HA history is possible for the porch/patio sensors. My own heavy full-sheet exports (33k rows) during the day were not the trigger -- the failures began before them -- but they are exactly the kind of call that piles up against a slow backend, so avoid them while it's unhealthy.

**Incident follow-up, 2026-09-25 ~14:17 MST:** ruled out a self-sustaining pile-up of our own hung executions -- with the Node-RED POST node disabled and all our probes stopped for 15 minutes, `action=version` recovered (1.2 s) but a tiny-sheet export still timed out at 120 s and a GPS lookup still failed at 93 s with Google's error page. So the Spreadsheet service on this document is unresponsive independent of our traffic. Executions list (Joseph) shows the same pattern back to at least 11:22 (92-94 s Failed, ~187 s Failed = two sequential ~93 s Spreadsheet-service timeouts, 360 s Timed Out); one doPost completed after 307 s at 13:43. Google's status feed showed no Sheets/Apps Script incident. Node-RED's POST node is re-enabled and holding 62 readings (snapshotted and re-injected across the redeploy); it drains on its own when the sheet recovers. **The M8's `hike-izer-daily-refresh.timer` was stopped (not disabled) at 13:57 MST to keep its 5 PM full-sheet export off the sick document -- it comes back on a reboot, but must be restarted by hand (`sudo systemctl start hike-izer-daily-refresh.timer`) once the sheet responds, or the daily refresh silently stops.** Diagnostics asked of Joseph: the error text of one Failed (~93 s) execution, and the spreadsheet's file size in Drive; a `Make a copy` of the spreadsheet (also the backup CARD-0337 needs) tested for speed would separate a document-level problem from a script/account-level one.

**Incident resolved 2026-09-25 ~15:50 MST -- migrated to a new spreadsheet; root cause of the original document's failure is NOT known.** Bisect (Joseph running diagnostic functions in the Apps Script editor): Google's Spreadsheet service was healthy (a brand-new spreadsheet was created/written/read in <1 s); `SpreadsheetApp.openById()` on the original document *and on a plain "Make a copy" of it* hung to the 6-min cap, even with the three formula-driven View tabs deleted from the copy; but right-clicking the `Environmental Data` tab -> Copy to -> New spreadsheet produced a document that opened in 191 ms (33,049 rows intact). So the fault was the document, not its data, size (only 1.7 MB), traffic, our lock, or the sorted tabs. **Fix:** every data path in `environmental-data.gs` now goes through `_ss()` -> `SpreadsheetApp.openById(SPREADSHEET_ID)` (new spreadsheet `1zBzeLoc...HQ1evW2-5HYKJP70_g`), deployed by Joseph as a new *version* of the existing web app deployment, so the URL and every client (Node-RED, M8, phone) were unchanged (commit `74700bc`, `SCRIPT_VERSION 2026-09-25.1-new-spreadsheet`). Verified: full Environmental Data export of 33k rows in ~10 s (was minutes/timeouts), GPS lookup 1.7 s, all tabs resolve, the real 9/24 hike pipeline reproduced identical counts (23 env / 1 obs / 401 GPS / 2 forecast) at $0. **The old spreadsheet then recovered on its own** (opens in 241 ms as of 15:42) and, in the window before cutover, had received Node-RED's 89 held readings (18:47Z-22:28Z); Joseph ran a one-time dry-run-then-real `reconcileEnv()` that appended exactly those 89 rows to the new tab (33,149 rows, 0 duplicate (ts, source) keys, porch/patio series continuous since 17:00Z). **Remaining gap:** ~8 readings per porch/patio sensor from 18:03Z to 18:43Z (11:03-11:43 MST) were dropped by the queue's old give-up-after-5-attempts behavior before the hold fix; they exist only in Home Assistant's history. Not migrated: the three View tabs (formula views over the full tabs) and the `Timeline` tab needs its leading-space name (`" Timeline"`) fixed. The M8 daily-refresh timer is running again. Old spreadsheet kept as a read-only fallback. **Open:** why it failed and why it recovered (unknown; Google reported no incident); the `undefined reading @ undefined` alert source; the bounded dedup window assumes new rows are at the bottom of the tab, which Joseph's manual Z->A sorts violate (scan both ends, or stop sorting the live tab).

**Incident closing notes, 2026-09-25 evening (Joseph's decisions):** (1) **The old spreadsheet is the script's home** -- Joseph is renaming it `SCRIPTS JCTsh Environmental Data`; the Apps Script project is container-bound to it, so it is edited/deployed from there (update the existing deployment's version, never create a new deployment). Its data tabs are stale; **Joseph: they can be deleted eventually** -- before doing so, re-run the `diagCounts` comparison so nothing unique remains, and wait until the new spreadsheet has been stable across at least Saturday's hike. (2) **The 18:03Z-18:43Z porch/patio gap was backfilled** from Home Assistant's history: 14 readings (7 per sensor, front-porch slots :08:50-:38:50 and back-patio :07:58-:37:58, 18:xxZ), values read as the HA state in effect just after each slot (temperature/humidity/illuminance as recorded, pressure converted from HA's psi to hPa and rounded to 0.1), published through the normal Node-RED path; `rssi_dbm` left blank (HA has no equivalent), dew point/heat index recomputed by the pipeline. Timestamps are the sensors' own fixed schedule (:50 / :58 seconds), not HA's arrival times. Both series now show every 5-min slot since 17:00Z. (3) **Joseph will not sort the live tab** (so the bounded dedup window's assumption holds; no change made). (4) **The View tabs are not being rebuilt** unless Joseph needs them.

**Root cause closed as "unexplained, mitigated" (Joseph, 2026-09-25).** Not pursued further: no Google incident, the document recovered on its own, and the Executions/version-history evidence was judged not worth chasing. Mitigations now in place: a fresh spreadsheet, bounded/narrow reads, a Node-RED queue that holds readings through an outage instead of dropping them, and `core/data-pipeline/RUNBOOK-sheets-outage.md` so a recurrence is a short procedure; early warning is CARD-0338. **The `undefined reading @ undefined` alerts are explained and fixed** -- CARD-0339 (the AQM buffers `wifi_attempt_start` event lines that ride its `/data` replay; found by a live `command/replay` capture; router fixed, commit `eee0b70`). Also verified in that capture: the AQM's log retention and `command/replay` topic work on hardware.

**Earlier warning signs, found 2026-09-25 evening (kanban PR #131, Joseph's screenshot from his phone):** a Tasker notification `Task 'Flush Observation Queue', HTTP Request (step 8): TimeoutException ... 30000 milliseconds` timestamped 3:12:44 AM on **2026-09-24** -- the phone's Hiking Observations upload timed out against the Apps Script ~31 hours before the 10:07 MST failure on 09-25. Together with the M8 backstop check's multi-day export timing out on the mornings of both 09-24 and 09-25, the Sheet was already degrading from at least early 09-24; the 09-25 outage was where writes finally stopped, not where it began. The queued observation was safe (Tasker deletes it only on confirmed success; the Apps Script rejects a duplicate `ts`). Timeline for anyone revisiting the unexplained root cause.

**First real hike after the fixes, 2026-09-26 (05:57-09:19 MST, both devices carried) -- the hike itself was captured, but NEITHER device's environmental data reached the Sheet; the Watch for below is NOT satisfied and the retention fix is untested.** (1) **GPS/observations fine:** 392 GPS points, 2 observations, step 1 ran ($0.39). (2) **hiking-monitor: nothing replayed and an empty log** -- no `Replaying N hike readings` line at dock, and pressing the Replay Hike Log button (verified: its `button/replay_hike_log/command PRESS` reaches the device) makes it emit nothing, which by design means the log is empty; zero hiking-monitor rows in the Sheet. Joseph confirms the switch was ON and the e-ink showed temp/humidity/pressure during the hike, and by the code a running device with the switch ON and no Wi-Fi writes a line every 2 minutes (even a `clock_invalid` skip event), so this is unexplained. Bench test proposed: unplug, switch ON, wait ~8 min, switch OFF, dock -- expect `Replaying N`. (3) **AQM's first field run produced zero readings:** the dock replay was 98 `Skipped reading - clock_invalid` events + Wi-Fi events. Cause: Joseph started it by power-cycling at the garage (unplug, power on, Intent ON) -- the AQM has no RTC and only tries Wi-Fi when docked with Intent off, so a cold boot away from a sync leaves the clock invalid for the whole run (never seen before: every earlier run began docked and synced). Needs a design fix (uptime-tagged readings converted at the next sync, an RTC, or a required pre-hike sync step) -- to be carded. (4) **Sheet-health probe fired 5 times** (04:01, 05:06, 06:41, 07:11, 09:01 MST; 10-23 s responses or 30 s timeouts, each self-recovering in 5-19 min); no readings lost (queue held), the M8 backstop skipped itself through the health gate as designed. Cause of the intermittent slowness on the new spreadsheet still unknown; the Apps Script Executions list for those windows would show which calls failed. Interim writes while investigating; outcome to follow.

**Kept open independent of CARD-0259 (hiking-monitor v2), 2026-09-10 — Joseph's call.** This is the actual motivating problem behind v2, but worth continuing to chase root cause on the current hardware in parallel, in case it turns out fixable without a full rebuild — not automatically superseded by v2's longer timeline.

**Related:** CARD-0221 (Environmental Data coverage gap this reboot loop most likely caused), CARD-0222 (GPS correlation failure, very plausibly the same root cause), CARD-0205 (air-quality-monitor's debug UART — the setup mistakenly assumed portable to this device; see the correction above), CARD-0211 (the earlier, already-fixed task-watchdog crash during this same replay loop -- confirmed not a recurrence, but the closest prior precedent), CARD-0217 (the earlier ~270-reboot brownout storm -- same symptom shape, different and already-distinguished reset-reason signature; folded into CARD-0259), CARD-0180 (the restart button ruled out as this incident's trigger), CARD-0215 (the duplicate-reading rejection guard relevant to disentangling real loss vs. deduped resends), CARD-0259 (hiking-monitor v2 — the eventual resolution path if this never gets root-caused on current hardware), `components/hiking-monitor/wiring.md` (Debug UART — Not Wired On This Device, the authoritative home for that fact), `components/hiking-monitor/hiking-monitor.yaml`.


**Hiking-monitor hang found while flashing the diagnostic build, 2026-09-26.** After the bench session it was docked (USB, switch off), booted 10:44, sent one heartbeat at 10:58 (uptime 14 min) and then went silent (watchdog alert 11:33) while still answering pings; OTA (3232) and API (6053) ports refused/timed out and MQTT stayed down. An MQTT Restart press rebooted it (MQTT disconnect 11:57) but it then flapped on and off the network (0-100% ping loss between machines) until a physical reset; after the reset and a USB re-plug it stayed up and the OTA succeeded (12:08). Cause unknown -- no serial log was captured. **This is a second, separate failure mode of this device that could explain the empty log on the 9/26 hike** (a stalled app loop leaves nothing recorded); the watchdog's 35-minute alert caught it. Diagnostic firmware (config_hash 0x28099b0a: `boot_state` event at boot, "Hike log at connect" line, `boot_cleared_lines`) is now flashed and committed. Next: watch heartbeats over the next hours docked; if it stalls again, capture serial (`esphome logs` over USB) before resetting.

**Hiking-monitor stability check, 2026-09-26 14:21.** Since the diagnostic build came up at 12:10:17 it has run 2 h with a heartbeat every 20 min on schedule (latest 14:09:55, uptime 1h 59m, batt 4.28 V, pings 0% loss) -- the docked hang seen at 10:44-11:57 has **not** recurred, well past the ~14 min mark at which it went silent before. Cause still unknown, so not called fixed. The new "Hike log at connect" line works: `13 line(s), replayed flag SET -- not replaying` (the bench session's log, retained and correctly flagged). Keep watching through the next hike; if it stalls again, capture serial (`esphome logs` over USB) before resetting.
---

### CARD-0225 · [bug] [mqtt] MQTT architecture docs are inaccurate/stale, and phone-based intake pipelines are invisible to the log dashboard — RESOLVED 2026-09-02
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-10 (CARD-0193) — 11530B, over the 5000B size threshold.

---

### CARD-0224 · [bug] [hiking-monitor] Low-battery-while-charging WiFi-attempt gating is undefined — real risk, not a corner case
**Status:** Build

**Reopened from Done 2026-09-17 (Joseph's correction, applied consistently with CARD-0276).** This card carries its own still-open Watch for (below, from 2026-09-06) that has never fired — marking it Done while a real-world confirmation is still outstanding was the wrong convention. An open Watch-for now means the card stays in Build until it fires; see CARD-0251 for the general rule.

**Raised 2026-08-29 (Joseph), during a conversation clarifying `JCTsh-Build-Standards.md` §2.14 point 13's data-flow model.** Point 13 establishes that a WiFi upload attempt requires Intent off AND Power Connected true. Point 2/9 separately establish a low-battery cutoff that's supposed to gate WiFi-burst operations regardless of those two signals. Neither point specifies what actually happens when *all three* conditions are in play at once: Intent off, Power Connected true (charging), **and battery voltage below the safe cutoff as a direct result of the device having just worked hard** (a long hike, extended field session) — the device's own prior activity is what put it in this state, not an external fluke.

**Why this is the highest-risk version of the scenario, not an edge case:**
- §2.14 point 9 already documents that a LiPo's internal resistance rises as it depletes — "the identical hardware configuration can pass repeatedly on a fresh, cool cell and fail repeatedly on a partially-depleted... one." A battery low from prior heavy use is exactly this condition.
- CARD-0198's own testing already found the Pololu D24V10F3's transient response to WiFi's current draw is marginal at a *healthy* 3.86-3.88V. A depleted, higher-internal-resistance cell would plausibly make that worse, not the same.
- Power Connected being true doesn't fix this instantly — TP4056 charges over minutes, not immediately. If the device retries a WiFi attempt while voltage is still near/below cutoff, it risks the same class of sustained brownout-reset loop CARD-0217 already documented on hiking-monitor in the field — which, worth noting, only recovered "once external USB dock power was applied," meaning being plugged in was the *recovery* mechanism there, not an instant fix; the device still sat in a bad state for a real stretch of time afterward.
- `power-system-redesign.md` separately flagged that the Pololu's own documented minimum input voltage (3.4V) is the *same number* as the generic §2.14 point 2 cutoff — little to no margin between "firmware says stop" and "the regulator itself can't function," right in the zone this scenario lands in.

**Open design questions, not yet resolved:**
1. When battery is below cutoff and Power Connected is true, does the device silently wait and recheck periodically, or is behavior currently undefined/unimplemented on both devices?
2. Should "recovered" mean clearing the bare cutoff threshold, or a safer margin above it, given the demonstrated fragility of WiFi bursts even at healthy voltage?
3. Does this need its own explicit state (distinct from the normal "no network reachable" bounded-retry loop in point 13), or can it reuse that same retry mechanism gated on an added voltage check?

**Applies to both current field devices** (hiking-monitor, air-quality-monitor) — this is a gap in the shared architectural standard, not specific to the Pololu swap that surfaced it.

**Relationship to CARD-0198's testing, clarified 2026-08-29 — related, not the same, not blocking.** CARD-0198 is empirical hardware validation (does the Pololu survive WiFi's current draw), all of it so far at a healthy battery voltage (3.86-3.88V) — none of that testing has touched this card's actual scenario. This card is a firmware-behavior/design question about the *low* end of that same voltage spectrum. They connect because §2.14 point 9 already predicts (and CARD-0198's findings support) that the same brownout mechanism worsens as voltage drops — CARD-0198's results are a real input to this card's open questions once available, but this card doesn't block CARD-0198's current work. Once CARD-0198's present hardware puzzle is resolved and the Power-Connected-true retest is done, a deliberately-discharged-battery WiFi trial is planned on that same rig (see CARD-0198's plan) specifically to inform this card, rather than this needing its own separate test setup.

**Planning started 2026-08-29 — real existing implementation found on hiking-monitor, changes the shape of this work.** Checked the actual firmware (`components/hiking-monitor/hiking-monitor.yaml`) rather than assuming Question 1 was genuinely unimplemented — it isn't, on hiking-monitor:

- **CARD-0212 already built almost exactly this.** In `mqtt.on_connect:`, before replaying any buffered hike data, the firmware checks `battery_voltage < 3.4f` and — if true — logs `"Replay deferred - battery %.2fV below 3.4V cutoff, waiting for charge"` and skips the replay burst entirely for that connection cycle. Data stays buffered, untouched. The design intent, per the code's own comment: *"Skips only this connection cycle... the next reconnect (once charging brings voltage back up) tries again naturally, no separate retry timer needed."*
- **This is a genuinely good pattern, worth confirming rather than reinventing:** it doesn't block the WiFi/MQTT *connection* attempt itself (Power Connected + Intent-off still triggers that normally) — it specifically defers the *current-hungry sustained operation* (the replay burst), which is exactly the right granularity given the brownout mechanism is about sustained/repeated current draw, not the connection handshake itself.
- **`low_battery_shutdown` (the harder cutoff, forces deep sleep) is correctly scoped to field mode only** — gated on `in_field_mode` (Intent on AND not MQTT-connected), not on `dock_detect` — so it never fires while docked/charging, which is exactly right: forcing sleep while trying to charge would be counterproductive.

**Real gap found in that same pattern, not previously noticed — Question 1 isn't fully answered yet.** Searched for any periodic reconnect/re-check mechanism (`on_disconnect`, a reconnect interval, anything that would re-trigger `mqtt.on_connect:` while already connected) — **found none.** The code comment's claim ("the next reconnect... tries again naturally") relies on a reconnect actually happening again *for some other reason* — nothing in the firmware forces one. If the MQTT connection stays persistently up (realistic on stable home WiFi) after the replay-deferred branch fires once, there's no mechanism to re-check voltage and retry the replay once the battery has since recovered above 3.4V while charging. Buffered data isn't lost (still safely on flash), but could sit un-uploaded for an unbounded time purely because nothing prompts a re-check. **Severity: low** (delay, not data loss) **but real** — worth a small fix (e.g., a periodic timer while connected-but-deferred that re-checks voltage and replays once clear, rather than depending on an incidental reconnect).

**air-quality-monitor has no equivalent at all yet** — its own Step 8 duty-cycle/replay firmware isn't built (`air-quality-monitor-claude-code-instructions.md`). **Recommendation: port hiking-monitor's CARD-0212 pattern directly when Step 8 is built**, including fixing the periodic-recheck gap above at build time rather than porting the same latent gap forward.

**Progress against the three open questions:**
1. **Answered for hiking-monitor, with a real caveat to fix:** defined behavior exists (defer the replay burst only, not the connection attempt), but the "retries naturally" claim needs the periodic-recheck fix above to actually be true in all cases. Air-quality-monitor still has nothing — Step 8 should build the fixed version directly.
2. **Still open:** hiking-monitor's 3.4V works today, but CARD-0198 found the Pololu's transient response is marginal even at a *healthy* 3.86-3.88V, and `power-system-redesign.md` already flagged that 3.4V is also the Pololu's own documented minimum input floor — little margin for air-quality-monitor specifically. Whether air-quality-monitor needs a higher cutoff than hiking-monitor's proven 3.4V is a real, device-specific question, best answered once CARD-0198's deliberately-discharged-battery WiFi trial (see that card's plan) provides real data, not guessed at here.
3. **Answered, recommend reuse with the fix:** no separate state machine needed — hiking-monitor's "defer the burst, recheck on next reconnect" pattern is the right shape; it just needs the periodic-recheck gap closed so "next reconnect" isn't left to chance.

**Done when:** the periodic-recheck fix is designed and applied to hiking-monitor's existing CARD-0212 logic, air-quality-monitor's not-yet-built Step 8 adopts the same (fixed) pattern with its own cutoff-margin decision informed by CARD-0198's low-battery trial, and both are verified live (not just code-reviewed) — a real deferred-replay-then-recovered-and-uploaded cycle observed on at least one device.

**Moved to Build 2026-09-06** — the periodic-recheck fix design (point 1's real gap above) is settled enough to implement directly.

**Built, 2026-09-06 — hiking-monitor's periodic-recheck gap closed.** `components/hiking-monitor/hiking-monitor.yaml`:
1. New global `replay_deferred_pending` (bool) — set when a replay attempt defers because battery is below the 3.4V cutoff, cleared once a replay actually completes.
2. **Extracted the full replay sequence out of `on_connect`'s inline lambda into a new shared script, `attempt_hike_replay`** (alongside the existing `low_battery_shutdown` script) — same logic (CARD-0212's defer check, CARD-0199's Connected→Uploading→Done display sequence, CARD-0211's `feed_wdt()`-per-iteration fix), unchanged behavior, just callable from two places instead of duplicated. `on_connect` now just calls `script.execute: attempt_hike_replay`.
3. **New periodic check added to the existing 2-min `interval:` block** (which already runs every cycle regardless of field/docked mode, alongside the pre-existing `reset_reason_pending`/`wifi_disable_pending` checks): if MQTT is connected, `replay_deferred_pending` is set, battery has recovered to ≥3.4V, and there's still buffered data, calls the same `attempt_hike_replay` script again — this is the actual fix, since nothing previously re-triggered a check once a connection stayed persistently up after a deferred replay.

**Compiled successfully, 2026-09-06.** `esphome compile` against the synced build directory (`C:\esphome\hiking-monitor\hiking-monitor.yaml`) succeeded clean (`config_hash=0x53adc141`, `build_time_str=2026-09-05 20:37:38`, RAM 14.3%/Flash 58.1%, unchanged in shape from before this change).

**Flashed via OTA the same session — the normal, reliable method for this device.** (CARD-0076/CARD-0009's USB-only episodes are old history, resolved since; not a current constraint.) Device's retained `/status` topic showed `online` (CARD-0137's fix makes that reliable, not stale). `esphome upload --device hiking-monitor.local` succeeded (100%, `OTA successful`, 6.15s transfer). **Verified live, not just "upload succeeded":** watched real MQTT traffic through the reboot — `MQTT disconnected` → `Hiking monitor online - ESPHome 2026.4.5, IP: 192.168.1.161` → `MQTT connected` → normal `status: online` and sensor/debug traffic resumed, no Alert or crash. New firmware is genuinely running on the real field device, not just staged.

**Air-quality-monitor's Step 8 port is still not started** (its own duty-cycle/replay firmware doesn't exist yet at all, per the original scope above) — this Build pass only covers the device that already had the pattern to fix.

**Done when, updated to reflect the two-part remaining scope:** (1) ~~hiking-monitor's fix flashed to the real device~~ — **met, 2026-09-06** (OTA-flashed and confirmed live above) — still needs one further real-world confirmation: an actual low-battery-deferred replay that later completes automatically once voltage recovers while still connected, observed on a real hike, not just a clean reboot with nothing buffered to replay; (2) air-quality-monitor's Step 8 build adopts the same (already-fixed) pattern from the start once that firmware is written, informed by CARD-0198's low-battery trial for its own cutoff-margin decision.

**Watch for:** hiking-monitor's durable log (`/mnt/jctsh-logs/jctsh.log*` on the Pi) showing an `Alert`-category message matching `"Replay deferred - battery %.2fV below 3.4V cutoff, waiting for charge"` (the exact text `attempt_hike_replay` publishes, `components/hiking-monitor/hiking-monitor.yaml` line ~413) followed by a later `System`-category `"Hike log replay complete."` from the same device without an intervening manual reboot — that pairing is the actual observation item (1) below is still waiting on: a real deferred-then-auto-recovered replay cycle in the field, not just a clean boot with nothing buffered. No known date this will occur (only happens on a hike where battery drops below 3.4V while a hike log is still buffered), so it's checked every session per CLAUDE.md Session Start step 5, not on a schedule (see CARD-0249 for the date-based sibling convention this borrows from).

**CARD-0198 closed 2026-09-08, resolving item (2)'s prerequisite.** The cutoff-margin decision this card was waiting on for air-quality-monitor is now made, directly informed by CARD-0198's live testing: the upload-safe threshold is a **separate, additional** gate on top of the existing generic low-battery cutoff (not a replacement) — field mode keeps collecting/buffering at low current all the way down to the standard cutoff, same as hiking-monitor; only the WiFi/MQTT attempt itself needs to clear the extra, higher bar. Value set **provisionally at 3.8V**, pending a real bench sweep — see `air-quality-monitor-claude-code-instructions.md` Step 8 for the full reasoning. **Still not done:** the actual Step 8 firmware hasn't been built yet — it still needs to port hiking-monitor's CARD-0212/periodic-recheck pattern with this new threshold layered in, not just decide the number.

**Closed 2026-09-10, found stale during a kanban sweep — CARD-0012's Step 8 testing already satisfied this card's own done-when.** Air-quality-monitor's Step 8 port (the item still marked "not yet done" as of CARD-0198's 2026-09-08 close) shipped the very next day, and its 2026-09-09 field-simulation test directly produced the exact confirmation this card was waiting on: *"Replay took two attempts... the second, via the CARD-0224 periodic recheck, succeeded once voltage settled ('Replaying 50 buffered readings...' → 'Buffered-data replay complete.')."* This card's own done-when only required "a real deferred-replay-then-recovered-and-uploaded cycle observed on at least one device" — met. Hiking-monitor's own equivalent real-hike confirmation (the `Watch for` at this card's earlier text) hasn't fired yet — left as a residual watch item, not blocking closure since the umbrella bar is already met on the other device.

**Related:** `JCTsh-Build-Standards.md` §2.14 points 2, 9, 13, `components/hiking-monitor/hiking-monitor.yaml` (`attempt_hike_replay` script, `replay_deferred_pending` global, the 2-min `interval:` block's new recheck — CARD-0212's original battery check and `low_battery_shutdown` script), `components/air-quality-monitor/air-quality-monitor.yaml` (`attempt_aqm_replay` script, `replay_deferred_pending` global — Step 8's port of this pattern), CARD-0198 (the Pololu testing that surfaced this while discussing point 13), CARD-0012 (Step 8, the build and live verification that closes this card), CARD-0217 (hiking-monitor's real sustained brownout-reset incident, the closest existing precedent for what this could look like if unaddressed), CARD-0076/CARD-0009 (why this device needs physical USB access to flash, not OTA), CARD-0251 (the `Watch for` marker mechanism this card produced, given its own proper scope retroactively).

---

### CARD-0223 · [enhancement] [architecture] Standalone LiPo battery charging station (TP4056) — RESOLVED 2026-09-10
**Status:** Done

Archived to `architecture/card-archive.md` on 2026-09-28 (CARD-0193) — 3263B, over the 2000B size threshold.

---

### CARD-0221 · [bug] [hiking-monitor] Environmental Data coverage dropped to 61.8% on the 2026-08-29 hike -- four real 7-10 min gaps
**Status:** Planning

**Raised 2026-08-29, found during a data-coherence review of the regenerated hike page (CARD-0220's own hike).** The corrected page (2h58m, 7.5 mi, 366 real GPS points) shows only **55 of ~89 expected Environmental Data readings (61.8% coverage)** at the normal ~2-min field-mode cadence -- and it's not a smooth shortfall, it's four distinct gaps well beyond the normal cadence: 13:04-13:11 (7.0 min), 13:56-14:06 (10.0 min), 14:51-15:00 (9.0 min), 15:32-15:39 (7.0 min).

**Every reading that day was field-mode** (buffered on-device to flash, replayed via MQTT once reconnected -- confirmed via `field_mode_readings: 55` in the fetched `hike_data.json`), so these gaps reflect real missed/skipped *local* readings on the device itself, not an upload or Sheets-write problem -- the device's own 2-min interval tick genuinely didn't produce (or didn't buffer) a reading during those windows.

**Real cause found, 2026-08-29, via the log dashboard's own state (`/mnt/jctsh-logs/state.json` on the Pi) -- a genuine reboot loop during replay, not a missed-reading problem during the hike itself.** The device reconnected at 08:45:23 MST (15:45:23 UTC, right at the hike's own end) and logged `"Replaying 116 hike readings..."` -- but only 55 of those 116 buffered readings ever landed in the Environmental Data sheet, a 52% shortfall. Between 08:45:32 and 08:46:07 MST (35 seconds), the device shows **10 separate `Field-mode boot` log lines** -- the first `reset reason: exiting deep sleep mode`, every one after that `reset reason: Reboot request from mqtt`, each immediately followed by exactly one `Display refreshed (field mode) at <timestamp>` line before the next reboot. This is a real, repeating reboot-mid-replay loop, not a brownout (contrast CARD-0217's earlier ~270-reboot storm, which logged empty reset reasons -- this one is cleanly labeled MQTT-triggered restarts throughout).

**Not yet confirmed: what's actually sending the repeated MQTT restart command.** `"Reboot request from mqtt"` is the reset-reason string ESPHome logs when `App.safe_reboot()` is called via its MQTT-triggered restart path -- CARD-0180 built exactly one such trigger (`hiking_monitor_restart`, a template button exposed to Home Assistant). Whether HA itself, some automation, or a stuck/retained MQTT command is what's actually firing this repeatedly hasn't been pinned down -- a live `mosquitto_sub` sweep of the device's full topic tree after the fact found no currently-retained restart-command message, which argues against a permanently-stuck retained payload but doesn't rule out a transient one that self-cleared. `esphome`'s own `safe_mode` component (running on its default config, no explicit block in `hiking-monitor.yaml`) also logged `"Boot seems successful; resetting boot loop counter"` on the eventual clean boot -- confirms ESPHome's own boot-loop detection recognized this as an abnormal rapid-reboot episode, consistent with the 10-boots-in-35s reading.

**Done when:** the actual source of the repeated MQTT restart command is identified (HA automation, a stuck client, a retry loop, or something else) and either fixed or the replay path is made resilient to a mid-replay reboot without losing buffered readings (currently: at least 61 of 116 buffered readings never made it to the sheet across this one incident).

**Related:** CARD-0220 (the false-positive-hike fix whose regeneration surfaced this), CARD-0222 (a second, related finding from the same review -- GPS correlation failure on the same hike's readings, very plausibly caused by the same reboot loop disrupting Node-RED's per-reading GPS lookup mid-burst), CARD-0226 (the actual owning investigation for this reboot loop, split out once it became standalone firmware work -- see its own Watch for; this card resolves once that one does), CARD-0217 (the earlier, larger ~270-reboot brownout storm -- same symptom shape, different reset-reason signature), CARD-0180 (the MQTT-triggered restart button this reset reason most likely traces back to), `components/hiking-monitor/hiking-monitor.yaml`.

---

### CARD-0222 · [bug] [data-pipeline] GPS correlation failed for 84% of the 2026-08-29 hike's Environmental Data readings -- not the CARD-0197 timing race
**Status:** Planning

**Raised 2026-08-29, found in the same data-coherence review as CARD-0221.** 46 of 55 Environmental Data readings from the 2026-08-29 hike have no lat/lon at all (`readings_missing_gps_coords: 46` vs. `readings_with_gps_coords: 9` in `hike_data.json`) -- an 84% miss rate, far worse than typical.

**Cross-referenced against the Correlation Debug sheet (CARD-0197's own instrumentation) and confirmed this is a *different* bug than CARD-0197 was built to catch.** `_gpsLookup()` logs a `lookup_miss` row every time its nearest-point search fails -- if this were CARD-0197's hypothesized race (the GPS point not yet written to the sheet at lookup time), all 46 misses would show up there. **None of them do.** Checked each of the 46 missing readings' own timestamps directly against Correlation Debug: zero matching `lookup_miss` rows for any of them.

**Working theory, not yet confirmed:** Node-RED's wildcard data handler calls the Apps Script `action=lookup&ts=<reading's own real timestamp>` per reading (confirmed via `environmental-data.flow.json` -- it correctly uses the reading's own embedded event time, not "now," so this isn't a naive timestamp bug). Since `_gpsLookup()` was never even invoked (no miss logged means the function never ran to completion), the HTTP call itself most likely never completed for these 46 -- plausibly Node-RED's handler getting overwhelmed, erroring, or silently dropping requests when all 55 buffered field-mode readings arrive in one rapid replay burst at hike-end, rather than trickling in near-real-time the way CARD-0197's design assumed.

**Strongly correlates with CARD-0221's real cause, found the same session: a genuine reboot loop during replay.** The device reconnected and began replaying 116 buffered readings at 08:45:23 MST, then rebooted 10 times in the next 35 seconds (9 of them with reset reason `"Reboot request from mqtt"`, a real MQTT-triggered restart loop -- not a brownout, see CARD-0221 for the full log evidence). A device that's mid-reboot when a buffered reading's MQTT message is meant to trigger Node-RED's `action=lookup` call would very plausibly drop or never send that HTTP request cleanly -- exactly the shape of failure this card already inferred (`_gpsLookup()` never even invoked, no miss logged, because the call never completed) but couldn't previously explain a *cause* for. This isn't confirmed as the definite mechanism yet -- it's a strong, evidence-backed correlation, not a proven causal chain -- but it reframes the "Node-RED overwhelmed by a rapid burst" theory from a guess into something with a real, observed trigger event to point at.

**Both remaining investigation threads checked 2026-09-06 — one gives a nuanced result, the other is a confirmed dead end:**

1. **Success/failure pattern across the 55 readings, checked against chronological (reading's own embedded `ts`) order.** Exported the real Environmental Data rows for this hike and marked which of the 55 had GPS coords: successes land at positions 11, 14, 16, 24, 26, 27, 40, 43, 50 (of 55) — **scattered across the entire 2h47m hike span, not clustered in one contiguous block.** This doesn't hand over a smoking gun the way a single failed block would have, but it's still *consistent with* the reboot-loop theory rather than against it: since all 55 readings were replayed together in one rapid burst overlapping the ~35-second, 10-reboot chaos window, an irregular ~16% success rate (gaps of 1 to 13 readings between successes) is what you'd expect from a connection being torn down and rebuilt ~10 times while the burst streamed out — each reading effectively getting a random chance of landing in a brief "connection stable" window vs. a "mid-reconnect" one. A single contiguous failed block would have pointed toward a fixed-duration Node-RED overload instead; this scattered shape doesn't rule that out but fits the reboot theory better.
2. **Node-RED's own logs from the incident window — confirmed permanently gone, not just hard to find.** Checked `journalctl -u nodered` on the Pi for the exact 08:45:23-08:46:07 MST window: no entries. `journalctl --list-boots` shows the journal's earliest surviving boot starts 2026-08-31 08:23:58 MST — a later reboot reset the journal's retention window, and 2026-08-29's logs are unrecoverable. This closes off the one line of investigation that could have settled this definitively; no further remote evidence exists to pursue.

**Done when:** the actual failure point (Node-RED-side HTTP error, a rate/concurrency limit, or the reboot loop itself interrupting mid-publish) is identified with real evidence -- not just this correlation -- and either fixed or the gap is documented as an accepted limitation of the bulk-replay pattern. **Given Node-RED's own logs are now confirmed unrecoverable, this can no longer be proven beyond the scattered-pattern correlation above** — likely resolves together with CARD-0221 once that card's reboot-loop source is found via a live UART capture (the only remaining path for either card), or gets accepted as a documented limitation of the bulk-replay pattern if that capture never materializes.

**Checked against the new Accepted-limitation closure protocol, 2026-09-17 (`tos/JCTsh-Operating-System.md`, built off CARD-0258's shape) — doesn't qualify yet, on two separate grounds.** (1) No working mitigation exists here at all — unlike CARD-0258 (a live-confirmed retry fix with only the cause unknown), this card never built a fix, only diagnosed the gap; a card with nothing working to close on is a **Defer** candidate under that protocol, not a Done. (2) A real, still-active lead remains open — CARD-0226/CARD-0221's UART capture, named above as "the only remaining path for either card" — so condition 3 (no practical investigative path left) isn't met either. Stays in Planning until that lead is either exhausted (at which point Defer, not Done, is the honest outcome given point 1) or it actually resolves the cause.

**Real correction to point (2) above, 2026-09-17 (Joseph): the UART capture "lead" isn't just untried — hiking-monitor's current hardware was never wired to support it at all.** CARD-0205's debug UART was built specifically for air-quality-monitor; hiking-monitor's own perfboard has no UART tap, so catching this live requires either reworking the current field-proven perfboard (same cost category CARD-0070/CARD-0201/CARD-0202 were deliberately deferred to avoid) or waiting for CARD-0259 (hiking-monitor v2, UART included by design). See CARD-0226's own 2026-09-17 correction, and `components/hiking-monitor/wiring.md`'s new Debug UART section, for the full finding. This makes the "still-active lead" in point (2) above a genuinely blocked one, not merely unattempted.

**Joseph asked directly whether that means Defer, per the Accepted-limitation protocol's own point (1) — held off, real connection to CARD-0279 found first, 2026-09-17.** This card's own working theory (above) is that Node-RED's `action=lookup` handler gets overwhelmed by the burst of buffered readings replaying all at once — that's not a claim about *why* hiking-monitor rebooted, it's a claim about *Node-RED choking on a lookup burst*, and that's exactly the mechanism **CARD-0279** (built and deployed the same session, throttle + retry + log on that identical `action=lookup` call path) already addresses — independent of whatever causes a device to dump its buffer all at once. If CARD-0279's own still-open Watch for confirms the fix holds on a real hike, it would very plausibly prevent this card's specific failure shape from recurring too, without ever root-causing the 2026-08-29 reboot loop. **Decided: hold off on Defer.** Wait for CARD-0279's Watch for to resolve, then re-check this card against the real outcome: if a future hike's missing-GPS-correlation rate looks sane under load with CARD-0279's fix live, this closes as *fixed structurally via CARD-0279* rather than Defer; if the same failure shape still recurs despite CARD-0279 being live, that's real evidence the UART-only path was actually necessary, and Defer becomes the honest call then.

**Related:** CARD-0197 (the correlation-debug instrumentation this diagnosis relies on, and the *different*, already-addressed race it was built to catch), CARD-0220 (the false-positive-hike fix whose regeneration surfaced this), CARD-0221 (the sibling Environmental Data gap finding from the same review -- now believed to share the same root cause, the MQTT reboot loop during replay), CARD-0226 (the actual owning investigation for that shared root cause -- see its own Watch for; this card and CARD-0221 both resolve once that one does), CARD-0258 (the sibling card the new Accepted-limitation closure protocol was actually built and applied against), CARD-0279 (the GPS-lookup throttle/retry/log fix that may resolve this card's actual failure mode structurally, without ever root-causing the reboot loop -- watch its own Watch for), `core/data-pipeline/environmental-data.gs` (`_gpsLookup`), `core/data-pipeline/environmental-data.flow.json` (the Node-RED lookup call).

**New evidence 2026-09-22 09:30 MST (hike-izer cluster session) — CARD-0279's instrumentation now sees what this card couldn't, and it points away from this card's working theory.** The 2026-09-21 hike produced two real `Alert`s on the Pi's durable log, from the `env-data-gps-log-failure` node CARD-0279 added:

```
2026-09-21 07:58:06 MST | node-red | Alert | GPS lookup failed after 3 attempts for hiking-monitor reading @ 2026-09-21T14:49:43Z (status 404) -- publishing without coordinates.
2026-09-21 07:58:35 MST | node-red | Alert | GPS lookup failed after 3 attempts for hiking-monitor reading @ 2026-09-21T13:47:36Z (status 404) -- publishing without coordinates.
```

**Why this matters to this card specifically:** this card's working theory above is that the `action=lookup` HTTP call *never completed* for the affected readings — inferred from the absence of `lookup_miss` rows in the Correlation Debug sheet, since `_gpsLookup()` logs a miss only if it actually ran. These Alerts show a different, now-directly-observed failure: the call **does** complete, and Apps Script answers **`404`**. A 404 response never reaches `_gpsLookup()`'s miss-logging path either, so it would produce *exactly* the same "no `lookup_miss` row" signature this card treated as evidence of a call that never completed. **The two are indistinguishable from the Correlation Debug sheet alone** — which means this card's central inference may have been reading an Apps Script 404 as a Node-RED-side non-completion.

**Connects this card to an already-established pattern rather than a novel Node-RED bug.** Intermittent Apps Script `404`s on this same deployment are documented on CARD-0275 (sustained 45+ min window, read path), CARD-0276 (write path, same morning), and CARD-0258 (a 240s timeout on the same endpoint). A step-1 fetch on this very hike also timed out at 240s (`2026-09-21 07:59:37 MST`). If GPS-correlation misses share that root cause, the fix direction is retry/resilience against Apps Script flakiness — CARD-0279's throttle+retry was a first step — not chasing Node-RED HTTP-node behavior.

**Not claiming this closes the card.** The 2026-08-29 hike this card is actually about coincided with CARD-0221's confirmed 10-reboot replay loop, which is a real and sufficient cause on its own for that specific hike's 84%. What's new is that "no `lookup_miss` row" no longer implies "the call never ran," so that piece of the reasoning needs re-examining before the working theory is trusted.

**Real, structural update 2026-09-29 (general session, found scanning the board for CARD-0349 follow-on work) -- the mechanism this card's whole 2026-09-22 pivot points at is now gone, not just throttled.** The established pattern this card connected to (Apps Script `404`s under load on `action=lookup`, CARD-0275/0276/0258) required GPS correlation to make a network call to a flaky remote Google service at all. As of CARD-0349 (Phase 1, 2026-09-28), it doesn't: `_gpsLookup()`/`action=lookup` is retired, and Environmental Data's GPS correlation runs through `/lookup-gps` -- a local, indexed Postgres query on the same host, no network round-trip, no Apps Script involved. CARD-0279's throttle node (the mitigation this card was waiting on) was itself found unnecessary against the new query and removed (CARD-0347). If the 2026-09-22 theory (Apps Script flakiness, not a Node-RED bug) was right, this card's failure mode can no longer occur for any hike after the cutover -- same "closes as fixed structurally" logic this card already committed to for CARD-0279, just via a stronger fix.

**Not yet confirmed live -- the two walks since cutover don't count as a clean test.** Both of CARD-0346's 2026-09-28 walks (the AM rehearsal and the short follow-up) were confounded by hiking-monitor's own hardware fault (a connector issue, unrelated to GPS lookup) and produced almost no real field-mode data either way -- neither is evidence one way or the other for this card's specific question.

**Watch for:** the next real hike with genuine field-mode Environmental Data volume from hiking-monitor -- check `readings_missing_gps_coords` vs. `readings_with_gps_coords` in that hike's `hike_data.json`. A low miss rate (comparable to a normal, non-incident hike) confirms this closes as fixed structurally via CARD-0349; a high miss rate matching this card's original 84%/CARD-0226's other recurrences would mean the GPS-correlation failures were never about Apps Script at all, and the device-side reboot loop (CARD-0226, still unresolved, root cause still unconfirmed) is doing all the damage on its own -- worth knowing either way, since CARD-0226 stays open regardless of this card's outcome.

---

### CARD-0220 · [bug] [hike-izer] GPSLogger start/stop noise (on/off/on toggle) gets misclassified as a real hike and auto-published
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 4252B, over the 2000B size threshold.

---

### CARD-0219 · [idea] [back-patio-temp-sensor] Build back patio temp sensor
**Status:** Build

**Raised 2026-08-27 (Joseph).** A duplicate of `front-porch-temp-sensor` (ESP32 + BME280 + BH1750), monitoring the back patio instead of the front porch. Improvements over the original design deliberately left open at raise time.

**Planning (2026-09-21, Joseph on-site + chat) resolved the `JCTsh-Property-Sensor-Pattern.md` New Sensor Checklist** — site conditions, patio geometry (points P1–P4 added to `house-lot-coordinates.md`), power/connectivity/enclosure/sensor-complement decisions, and parts allocation (`JCTsh-Parts-Inventory.md` v2.32). All of that detail now lives in `components/back-patio-temp-sensor/` (README, wiring/perfboard/mounting/flashing/testing docs, `parts-list.md`) rather than staying duplicated here — see that directory for the actual current state.

**Moved to Build 2026-09-21 (Joseph, explicit decision)** — Design's Phase 4 instruction-set step skipped per the Observed Exception pattern (`JCTsh-Operating-System.md`): proven, already-built design, not a novel build.

**Build progress 2026-09-21 11:46 MST — wiring docs sharpened and the board's silkscreen verified against the pin table.** `wiring.md` now names every ESP32 pin by both silkscreen label and physical pin number (`GPIO21, pin 33`, `GPIO22, pin 36`, `3V3, pin 1`, `GND, pin 38`) and carries a new board-side ESP32 Connections table alongside the two sensor-side ones. A board photo (`esp32-pins-photo.jpg`) was compared label-by-label against `ESP32-project-pins.md`: **37 of 38 match exactly**, including all four pins this build uses. **Corrected 2026-09-22 — that photo is not this unit's own board:** it is byte-identical to `components/air-quality-monitor/esp32_pins.jpg` and entered the repo under CARD-0012. Same board batch, so the label verification holds at batch level, but this specific board's silkscreen has not been photographed and `JCTsh-Build-Standards.md` §1.2's per-board check is not satisfied. Low practical risk (the four wired pins were also continuity-verified end to end), but the original wording overstated what was checked.

**The one conflict — pin 18 — gave the long-standing "root cause unknown" anomaly a strong candidate answer.** The board silkscreens GND at pin 18, but `ESP32pins.png` (the generic 38-pin reference, byte-identical across `back-patio`, `front-porch`, `garage-radar`, and `hiking-monitor`) puts **GPIO11 / flash CMD** there. That explains the 2026-09-14 bench finding that pin 18 isn't continuous with the GND rail — it was never ground — and it fits the pin's position, directly completing the flash group below GPIO9 (pin 16) / GPIO10 (pin 17) and above VIN (pin 19). Upgraded in this component's docs from "nonfunctional GND, avoid" to ⛔ **never use** (driving a flash-bus pin interferes with SPI flash access). **Recorded as a hypothesis, not a fact** — inferred from a reference diagram plus a continuity result, never probed directly; a scope on pin 18 during a flash write would settle it.

Two follow-ons deliberately left outside this card: (1) `air-quality-monitor`'s own `ESP32-project-pins.md`/`wiring.md` still record pin 18's cause as unknown and misattribute the GPIO11 reference to hiking-monitor — same correction applies, but that component belongs to the hiking-monitor cluster, whose session owns the edit; (2) the board is silkscreened `NODEMCU` / `ESP-32S` / `V1.1` while ~20 references across this component (and `front-porch-temp-sensor`, `air-quality-monitor`, `JCTsh-Parts-Inventory.md`) call it "ESP32 DevKitC-32" — pin-compatible, nothing miswired, but the name doesn't match the part. Noted in `README.md`'s hardware row; a full rename is undecided.

**Timestamp correction 2026-09-22 (this card's only bad stamp).** The Build-progress note below originally read `18:46 MST`; the true time was **11:46 MST**, confirmed against commit `2789c7f`'s own git timestamp. Cause: **the Bash tool's `date` on this workstation returns UTC while labelling it MST** — `TZ=America/Phoenix date` reported `17:04 MST` at a moment when both authoritative clocks (NTP-synced Pi, and Windows `Get-Date` on `US Mountain Standard Time`) read `10:05 MST`. A flat 7-hour error, and invisible because the output carries the right timezone label.

Only that one stamp was affected. Every other time recorded for this card came from an authoritative source and was re-verified: the MQTT account from `/etc/mosquitto/passwd`'s mtime on the Pi (`16:08:32 -0700`), the compile from ESPHome's own `build_time_str` (`16:11:06 -0700`), the binaries from a file mtime that agrees between Git Bash `ls` and Windows (`16:19`), and the flash verification from the device's serial log (`16:24`). `ls` is fine; only `date` is wrong.

**This also produced a false fleet-wide alarm**, worth recording because the failure mode generalises: comparing the Pi's (correct) log timestamps against the workstation's (skewed) clock made `jctsh.log` look ~7 hours stale, and that was reported as a log-server outage. It was not — the `tos` session checked the Pi directly and found it writing normally. Every "component X has gone silent" judgement made by differencing a remote timestamp against local `date` on this workstation is suspect by 7 hours. Reported to `tos` for a durable home, since `tos/JCTsh-Session-Start.md` is where the repo's every-timestamp-needs-a-time-of-day rule lives.

**Assembled, bench-tested, and flashed 2026-09-21 (Joseph at the bench, walked section by section).** Full record in `components/back-patio-temp-sensor/bench-test-plan.md`, a new worksheet derived from `wiring.md` (`perfboard-layout.md`'s old inline continuity list now points at it rather than keeping a second copy).

- **Bench checks: all pass.** Power-rail isolation (3), continuity (9 + 2 shared-rail integrity), signal isolation (5), 36-pair adjacent-pad sweep, pin 18 isolation, shorts re-checked with modules seated, and a power-on smoke test reading 3.3 V at all three points. Enumerated as **COM7** (`Silicon Labs CP210x USB to UART Bridge`).
- **MQTT account created and verified live** — `mosquitto_passwd` + the mandatory `chown root:mosquitto`, broker restarted clean, then the credential actually exercised with a real `mosquitto_pub` rather than inferred from the account existing. Row added to root `CLAUDE.md`; password and a new per-component OTA password recorded in `credentials.local.md`. `secrets.yaml` written (gitignored), flash directory staged at `C:\esphomeack-patio-temp-sensor\`.
- **Flashed over USB, binary confirmed fresh** — compile `config_hash=0xf32d00da`, `build_time_str=2026-09-21 16:11:06 -0700`; the booted device reports that same timestamp, so no stale-upload (the failure mode `esphome upload` is known for).
- **Live on first boot:** WiFi (`JCTnet1`), MQTT, safe_mode clean, and the **BH1750 publishing illuminance** (332.1 lx).

~~**Blocked on one part**~~ — **RESOLVED 2026-09-22 16:14 MST, see the swap-verification note below.** The installed BME280 was one of the counterfeit BMP280s (Joseph confirmed; from Bin B3, not Bag 3). Firmware reports `Wrong chip ID or no response` and marks the component FAILED, so it publishes nothing — not even the temperature and pressure a BMP280 could actually provide, because ESPHome's `bme280_i2c` platform rejects any chip ID that isn't `0x60`. **Explicitly not a build defect:** the BH1750 shares SDA (pin 33), SCL (pin 36), 3V3 (pin 1) and GND (pin 38) and works, which proves the bus, the rails, and every solder joint on the shared path. This is exactly the failure `parts-list.md` warned about after front-porch's original batch — the predicted detector firing as designed.

**Genuine BME280 ordered 2026-09-21.** Swap is drop-in (same pinout, same `0x76` address) — no firmware change, no reflash, just reseat and power-cycle. A `bmp280_i2c` shim to get temperature/pressure in the meantime was considered and is viable, but costs two firmware edits plus a revert (the DataPub lambda and JSON builder both reference `id(bme280_humidity)`, so removing the humidity sensor is a compile error, not a runtime null) — not done.

~~**Remaining after the swap:** re-verify per `testing.md`, then the two items below.~~ — **Partially done 2026-09-22 16:14 MST** (temperature/heartbeat/watchdog confirmed live via log, see below); the Log Dashboard/HA-UI portions of `testing.md` and the two items below stay open.

**MQTT/WiFi reliability finding, 2026-09-22 (surfaced by the `general` session's routine log scan, confirmed independently against the Pi's `jctsh.log` by this session).** Two separate MQTT dropouts found in the log, neither previously recorded on this card:
1. **2026-09-21 16:42:25 – 2026-09-22 08:35:19 MST (~15h53m)** — disconnected 5 minutes after the DHCP-reservation verification reconnect noted above, silent overnight, self-recovered the next morning with no manual intervention. Only one watchdog alert fired (`Component back-patio-temp-sensor silent for 35 minutes`, 17:12:02) — the watchdog alerts once at the 35-minute threshold and doesn't repeat while a device stays down, so that alert text badly understates how long this particular outage actually ran.
2. ~~**2026-09-22 14:44:12 – 15:39:04 MST (~55min)** — same pattern (disconnect, one 35-minute watchdog alert at 15:10:19, self-recovery), much shorter.~~ **Corrected below, 2026-09-22 16:14 MST — not an unexplained dropout.** The boot message at 15:39:05 (`Back patio temp sensor online`) plus the first post-boot heartbeat already reading a valid temperature is consistent with this being Joseph's physical BME280 swap and power-cycle, not a spontaneous WiFi/MQTT drop — see the swap-verification note below. Left struck rather than deleted since the raw timestamps are still accurate, just the interpretation was wrong.

RSSI in the heartbeats right before the second dropout ran -43 to -48dBm (weak-to-moderate) — a plausible but unconfirmed cause; nothing in the log directly implicates the router side vs. the device's own WiFi radio/antenna. **Recorded as an open reliability question, not a confirmed root cause.**

Also worth noting: a single correlated failure of *both* sensors at once occurred at **2026-09-21 16:37:02 MST** (`BH1750 read failed` alongside `BME280 read failed`, same timestamp) — a one-off, BH1750 hasn't failed again since, but it means the "BH1750 proves the I2C bus is fine" framing above rests on BH1750 *mostly* working, not *never* failing — worth keeping in mind if the BME280 swap doesn't fully resolve the read-failure pattern.

**Watch for:** a third WiFi/MQTT dropout on back-patio-temp-sensor — if the heartbeat immediately before it shows consistently weak RSSI (roughly below -47dBm, matching the pattern above), that's real evidence for a signal-strength cause worth addressing (relocate, external antenna, WiFi extender); if RSSI is fine right beforehand and it still drops, look elsewhere (router-side DHCP/ARP issue, power supply, or the ESPHome/MQTT stack itself). **Narrowed 2026-09-22 16:14 MST** — now only tracking the first (2026-09-21 overnight, still genuinely unexplained) dropout as a pattern; the second one turned out to be the BME280 swap's own power-cycle, not a second unexplained instance, so this marker is watching for a *second* real occurrence, not a third.

**Second occurrence found 2026-09-27 20:5x MST (general session startup, checked against the Pi's live `jctsh.log`) — fired, but the evidence points at a shared/router-side cause, not back-patio's own signal strength.** Two real episodes found, neither previously recorded on this card:
1. **2026-09-24 ~16:56–17:39 MST** — back-patio disconnected/reconnected repeatedly (5 cycles, several with `uptime: 0h 1m` — real reboots, not just a brief MQTT blip), RSSI -50 to -58dBm throughout (consistently weak, matching the hypothesis). **front-porch-temp-sensor flapped in the same evening window (17:37–18:10 MST, overlapping but not minute-aligned)** — also repeated reconnects/reboots, RSSI -56 to -61dBm, and threw two sensor-read Alerts (`BH1750 read failed`, `BME280 read failed`) consistent with a brownout during its own reboots.
2. **2026-09-27 ~18:50–19:26 MST (tonight, shortly before this session started)** — back-patio and front-porch both disconnected at the *same minute* three times (18:50:26/18:50:29, 19:16:19/19:16:28, 19:24:35/19:24:43 — back-patio then front-porch, seconds apart each time). RSSI on both was weak-but-typical (-50 to -58dBm), not obviously worse than their normal range. Front-porch's watchdog fired (`silent for 35 minutes`, 19:13:53); back-patio's did not reach the 35-minute threshold.
**Reading:** two different devices dropping at the same minute, twice, three days apart, is hard to explain by either device's own antenna/placement — **this now looks more like a shared cause (router/AP-side event, or a DHCP/ARP hiccup affecting both) than back-patio-specific signal strength**, though RSSI was weak-ish (not clearly abnormal) in both episodes so a signal-strength contribution isn't ruled out either. Not yet investigated on the router side (no router log access from this check). Both devices self-recovered within seconds to a few minutes each time; no data loss beyond the missed heartbeat window. **Marker stays open** — this is real signal but not yet root-caused; the original single-device framing above no longer fits what's been observed, worth Joseph's read before deciding whether to keep watching or open a proper investigation card.

**BME280 swap complete, live-verified 2026-09-22 16:14 MST (Joseph: "I replaced the BME280 and rebooted").** Confirmed directly against the Pi's `jctsh.log`, not just taken on report: the last `BME280 read failed` alert is timestamped 14:35:18, before the swap; every heartbeat since the 15:39:05 reboot carries a real temperature reading (first one: `16:08:58 | Heartbeat - uptime: 0h 30m, RSSI: -36dBm, temp: 101.6°F`), with zero read-failed alerts in between. Since ESPHome's `bme280_i2c` platform rejects any chip ID other than `0x60` and fails the whole component (no temp published at all, not even a bad reading) when it does, a valid temp value publishing is itself proof the chip ID check now passes — the counterfeit-BMP280 failure mode is structurally ruled out, not just presumed fixed. Humidity/pressure/illuminance weren't individually confirmed this pass (no Log Dashboard/HA access this session, see below) but chip-ID acceptance implies a genuine BME280, which reports all four. RSSI also read a strong -36dBm on this boot, well inside normal range — consistent with signal strength not being a driver of the swap-related disconnect, separate from the still-open overnight-dropout question above.

~~**Testing.md checklist not fully run through the Log Dashboard/HA UI this pass**~~ — **superseded below, 2026-09-22 18:33 MST**: once the MQTT discovery bug (see below) was fixed, all four sensors were confirmed live in HA, closing this out properly.

**Folded in 2026-09-21 (Joseph's call, rather than opening a separate card): the BH1750 header-size error, fixed in both this component and `front-porch-temp-sensor`.** Not strictly this card's component, but this card is what surfaced it and the porch/patio cluster owns both.

Both `perfboard-layout.md` files specified a **3-pin** female header for the BH1750 (light sensor). The GY-302 breakout has **five** pins — VCC, GND, SCL, SDA, ADDR — and both builds wire all five (each Wire Bridges table lists five BH1750 bridges, ADDR included). A 3-pin socket cannot seat a 5-pin module. Caught on back-patio *before* soldering, so it cost nothing but a different break point on a breakaway strip.

**A transcription error, not a design decision** — `front-porch-temp-sensor-claude-code-instructions.md` already stated the correct rule ("female header strips sized to their pin counts"), so front-porch's plan and its own layout doc disagreed, and the layout doc was wrong. back-patio inherited it by cloning.

Corrected in both files (materials row, placement diagram, legend, soldering step), struck through rather than deleted per the Documentation Structure mark-and-strike rule, each with a note explaining the finding.

**One thing deliberately left unverified — front-porch's *physical* as-built header.** That unit is mounted and running with the BH1750 publishing, so whatever is fitted works, which means the as-built already differs from what its doc claimed. Nobody has looked to see whether it is a 5-pin strip, a 4-pin plus a flying ADDR lead, or something else. The corrected docs say 5-pin is what the module *requires* and flag the as-built as unobserved, rather than asserting a guess as fact — exactly the failure mode that produced the original error. **Open item: eyeball the front-porch board next time it is accessible and record what is actually there.**

**Bug found 2026-09-22 16:37 MST (Joseph: "how come HA doesn't show the back patio sensor? it has the sensor but no data values") — MQTT discovery `unique_id` collision with front-porch-temp-sensor, the exact CARD-0186 pattern recurring.** Confirmed directly against the broker's retained discovery payloads (`mosquitto_sub` on the Pi), not inferred: back-patio's Temperature/Humidity/Pressure/Illuminance sensors publish `"uniq_id":"ESPsensortemperature"` / `"ESPsensorpressure"` / `"ESPsensorhumidity"` / `"ESPsensorilluminance"` — identical to front-porch's own, because both devices use ESPHome's default `discovery_unique_id_generator: legacy` (id derived from entity type + name only, not the device) and both name these sensors identically ("Temperature", "Humidity", etc.), inherited as-is when back-patio was cloned from front-porch. HA's MQTT integration keys entities by `unique_id`; front-porch's sensors claimed those ids first, so HA silently drops back-patio's identical-id discovery messages — no second entity is ever created. **Confirmed via `/api/states`:** back-patio has a device entry in HA (created by its restart button, which already has a device-specific name from the CARD-0186 fix) but zero Temperature/Humidity/Pressure/Illuminance entities — not even `unavailable` ones, they simply don't exist. Front-porch's own four sensors are unaffected and still updating normally.

This is literally CARD-0186 recurring: that card fixed this same legacy-generator collision for the restart *buttons* across hiking-monitor/front-porch-temp-sensor/salt-sensor (2026-08-19) by giving each button a device-specific `name:` — correctly applied to back-patio's button when it was built (`"Back Patio Temp Sensor Restart"`, not bare "Restart"), but never generalized to the four environmental-sensor names, because front-porch was the only environmental-sensor device that existed at CARD-0186's time.

**Fix options (same tradeoff CARD-0186 weighed), not yet applied — needs Joseph's go-ahead since it's a firmware change + reflash on a live device, not just documentation:**
1. Rename each of back-patio's four sensor `name:` fields to be device-specific (e.g. `"Back Patio Temperature"`), matching the button's existing fix pattern. Lowest blast radius, leaves front-porch's YAML untouched.
2. Set `discovery_unique_id_generator: mac` on back-patio's `mqtt:` block. CARD-0186 avoided this for front-porch because front-porch already had live entities that regenerating would orphan; back-patio has *no* live entities yet (that's this whole bug), so there's nothing to orphan — cleaner here, and future-proofs any sensor added to back-patio later without needing a per-entity rename each time.

**Fixed and live-verified 2026-09-22 18:33 MST (Joseph: "yes go ahead").** Applied option 2 — added `discovery_unique_id_generator: mac` to back-patio's `mqtt:` block, OTA-reflashed. Confirmed at both layers, not just "upload succeeded":
- **Broker:** retained discovery payloads now carry MAC-scoped ids (`04b24797df44-sensor-ca3e9dd9` etc.), nothing shared with front-porch's `ESPsensor*` ids.
- **HA `/api/states`:** all four entities now exist and are updating — `sensor.patio_back_back_patio_temp_sensor_temperature` 99.8°F, `_pressure` 13.40 psi, `_humidity` 29.8% (not NaN, confirming genuine BME280 chip acceptance), `_illuminance` 57.2 lx — timestamps within the last few minutes of the reflash. Front-porch's own four entities untouched and still updating normally.

**Real toolchain snag hit along the way, worth remembering for the next ESPHome compile on this workstation:** `python -m esphome` must run from native PowerShell, not this session's Git Bash — ESP-IDF's installer explicitly refuses under MSYS/Mingw (`ERROR: MSys/Mingw is not supported`). Separately, the installed `esphome` pip package had drifted to 2026.9.0 (wants ESP-IDF 5.5.5); another session had already found pinning back to `2026.4.5` (matching this component's original working build) necessary. Even pinned, the first attempt failed with every file `fatal error: Arduino.h: No such file or directory` — the package was present in `~/.platformio/packages/` but never got staged into this component's own `.esphome/build/.../esp-idf/framework-arduinoespressif32` tree, apparently left inconsistent by two earlier interrupted runs (one MSYS failure, one killed for host memory pressure). Deleting `back-patio-temp-sensor`'s entire local `.esphome/` directory and rebuilding fully clean resolved it. Entity naming (`sensor.patio_back_back_patio_temp_sensor_*`) came out from HA's own auto-slugging and is a little redundant-looking — cosmetic only, not touched here.

**Device offline since 2026-09-23 ~14:57 MST, found 2026-09-24 05:40 MST (Joseph: "It's offline, i rebooted it yesterday evening").** Not the discovery fix — that firmware ran cleanly for 20h29m first (heartbeats 2026-09-22 18:04 through 2026-09-23 14:33, uptime counter intact). Evidence from the Pi, not inferred:
- **Two boot-then-vanish cycles, ~30s each.** Mosquitto log: `2026-09-23T14:56:49` new client from 192.168.1.188 (preceded by `already connected, closing old connection` — i.e. the device had been alive until the reset, then rebooted), then `14:57:20 has exceeded timeout` (31s later). Again `17:48:56` connect (Joseph's evening reboot) → `17:49:27 exceeded timeout` (31s). Each time it reached WiFi + MQTT, published its `online` line, then stopped answering keepalives with no clean disconnect — the will message is what fired.
- **Fully off the network, not just off MQTT.** From the Pi: 100% loss to 192.168.1.188, neighbor entry `FAILED`; from the workstation: `Destination host unreachable`. `/status.json`: `freshness: Offline`, last_seen 2026-09-23 17:49:27.
- **CARD-0331's re-alert fix worked as designed** — `watchdog` has posted `still silent -- down Nh0m` every 2h since 15:08 (down 14h0m as of 05:08), the gap that let the 2026-09-21 overnight outage read as "35 minutes".

**Same shape as the unexplained 2026-09-21 outage** (connect 16:37, `disconnected` 16:42, silent ~16h until 08:35): dies shortly after a boot, afternoon, no self-recovery until something power-cycles it. Two of three episodes now begin in the afternoon heat, but 2026-09-22 ran straight through a 101°F afternoon fine (uptime unbroken), so heat alone isn't established. **Cause unknown; a firmware crash is unlikely (20h clean run, identical build) and a power-delivery/thermal/outlet problem is the leading candidate — a hypothesis, not a finding.** Not distinguishable remotely: a powered-but-crashing board, a brownout-looping board, and an unpowered board all look the same from the network. Needs eyes on the hardware, or a USB serial capture (`esphome logs` shows the reset reason — brownout / watchdog / panic).

**Correction and soak result, 2026-09-24 15:19 MST — the heat/patio framing above was wrong, and I built it on an unverified assumption.** I treated the board as if it were deployed at the back patio; it never has been (`mounting` is still an open Done-when item). Joseph's account: it sat on a USB adapter on his workbench, then on 2026-09-23 (~14:56, the `already connected, closing old connection` reboot) he moved it to the same plug next to the front-porch sensor on a *different* USB adapter, to compare readings — and it was off the network at both locations at various points. No sun at the front porch, same WiFi.
- **Heat is ruled out by HA's own history, not just by Joseph's say-so.** On the workbench the sensor read 97.1→102.6°F between 11:00 and 14:46 on 09-23 and ran fine (uptime unbroken 20h29m). At the failing front-porch plug it read 92.9°F at 17:48, with the front-porch sensor itself at 88–91°F throughout. It failed where it was cooler, and ran where it was hotter.
- **Soak, 2026-09-24:** powered from the laptop's USB port it held for ~46 minutes with no drop (43/43 pings, one continuous uptime, heartbeat at 14:50:35 `uptime 0h 29m`, RSSI -50dBm), then on the adapter Joseph moved it to at his desk (15:12:09 boot) 10/10 pings past the 30s mark where it had died at the front porch. Serial capture of a clean boot (COM7): WiFi 4.8s, MQTT 5.5s, no brownout/panic/watchdog line, `safe_mode` counter recorded success at 60.6s; before that it warned `Last reset too quick; invoke in 6 restarts`, i.e. ~4 short boots had piled up. (The reconnects at 14:18:58 and 14:20:39 are artifacts of my own opening/closing the serial port.)
- **What this leaves:** board and firmware are fine (20h clean run, clean boots, stable on two other supplies). The failing conditions so far are the front-porch plug + its adapter, and the 2026-09-21 workbench evening. Untested and now the discriminating question: **adapter vs. outlet vs. WiFi position** — plug the front-porch adapter in at the desk; then the desk adapter at the front-porch plug. Which BSSID it associates to (three `JCTnet1` APs are visible) is logged on serial at boot and is worth capturing at each location. Supersedes the power/thermal hypothesis in the note above; a hypothesis is still only a hypothesis.

**Further diagnosis, 2026-09-24 16:00 MST (Joseph at the bench, Claude monitoring) — firmware verified, plug theory retracted, wiggle test negative.**
- **Plug/outlet theory dropped:** Joseph pointed out the same failure happened at the workbench, and the full event record agrees. Failures: 09-21 16:37 boot → dead 16:42, silent ~16h until 08:35 next morning; 09-23 14:56 (moved to the front-porch plug) → dead 31s; 09-23 17:48 (reboot) → dead 31s. Fine: 09-22 08:35 and 15:39 boots, the OTA reboots, a 20h29m run, all 09-24 desk boots — 3 failures in ~9 boots. Every failure followed the board being moved/re-plugged, and every dead state was total silence with no reboot loop, lasting until someone physically re-powered it. The front-porch sensor on that plug showed no reboot or reconnect at either failure time (uptime 104h→115h unbroken), and the adapter used at the porch runs the board fine at the desk.
- **Firmware confirmed to be what it should be:** device-reported `2026.4.5 (config hash 0x29c8537e)` = `build_info.json` config_hash 700994430; build time 2026-09-22 17:54:52 matches the board's own serial boot line; `firmware.bin` written 18:03:16, OTA reboot logged 18:03:39; flash-dir YAML identical to repo YAML, which has no uncommitted changes (last touched `2fff3b1`). Not a byte-for-byte flash hash, but ESPHome verifies the OTA transfer and the board reports the right hash. **Correction to an earlier claim:** the 09-22 first PowerShell compile *did* upload before being killed — the device logged `ESPHome 2026.9.0` at 17:16:07 and ran that build until the 18:03 reflash. Unrelated to the outage.
- **Wiggle test negative:** flexing the USB cable and pressing the modules/perfboard while pinging once a second gave 33/180 lost pings; an untouched control run gave 28/180 — same rate, short bursts, so it is ICMP loss on a power-saving ESP32 pinged densely, not handling. MQTT stayed connected and the board never dropped or rebooted. My earlier once-a-minute pings were too sparse to have shown this loss. A negative wiggle test does not rule out an intermittent connection; it only failed to reproduce one.
- **False alarm, for the record:** the `silent for 35 minutes` alert at 15:25:35 was the 15:12 power move restarting the 30-minute heartbeat cadence (14:50:35 → 15:42:06 = 51 min > 35), not a fault.
- **Cause still unknown.** Only reproducible failure so far is the front-porch plug (2 of 2), so the next step is to reproduce it there — ideally with the laptop and serial capture to read the reset reason; if it survives, treat as intermittent and rely on the watchdog's every-2h re-alerts (CARD-0331) to catch a recurrence.

**Side-by-side against front-porch, 2026-09-24 16:45 MST (Joseph's call — "get a feel for it before moving it to the back patio").** The board was plugged in at the front-porch plug at 16:00:57, adjacent to the front-porch sensor, and did **not** repeat the 09-23 failure there: still connected 40+ minutes later with no broker timeout, answering pings. Readings matched within 90 s, settled window 16:31–16:40 (n = 9–10; the first ~30 min were still converging from desk temperature — over the whole window the temperature offset averages only +0.1°F, with the first minutes at -5.7°F):

| Back patio minus front porch | Mean | Range | Reading |
|---|---|---|---|
| Temperature | +0.7°F | +0.3 to +1.1°F | within BME280 tolerance (~±1°C) |
| Humidity | +1.6% RH | +1.1 to +1.9% | within tolerance (~±3% RH) |
| Pressure | -0.02 psi (~-1.4 hPa) | steady | within tolerance (~±1 hPa); supports the replacement being a genuine BME280 |
| Illuminance | +650 lx (611 vs 13.5 lx at 16:40) | +598 to +706 lx | ~45× apart, both falling with evening light — placement/exposure (bare board vs. a shaded front-porch sensor), not a fault; BH1750 demonstrably tracks light (57 lx at the desk earlier) |

Caveats: ~10 settled minutes at one time of day; the board is bare while front-porch may sit in a housing, so a sub-1°F fixed offset could be partly placement. A rerun over a longer/overnight window (light differences drop out) would give a cleaner offset. No correction factor applied or needed for now.

**Outage status:** heat, adapter, outlet, WiFi position, and handling (wiggle test) have each been tested or ruled out without reproducing the failure; it worked at the same porch plug on the same adapter that it died on twice on 09-23. Best description is **intermittent, cause unknown** (leading candidates unchanged: a marginal physical/power connection, or something that only shows after a long heat-soaked run — both untested hypotheses). Deploying to the back patio is reasonable on that basis, with the watchdog's `still silent -- down Nh` re-alerts (CARD-0331) as the detector; if it dies there, the timing after mounting is the new evidence.

**Still genuinely open (not resolved anywhere yet, deliberately deferred):**
- **Back-patio offline / boot-then-vanish pattern** (above) — ~~physical check of power, adapter vs. outlet vs. WiFi position swap test~~ all tested without reproducing (see the diagnosis and side-by-side notes); **intermittent, cause unknown.** Remaining action is deployment plus watching for a recurrence; the RSSI-focused Watch for above stays as-is.
- ~~**MQTT discovery collision** (found above) — pick a fix option and apply it, then re-verify `testing.md`'s Sensor Validation step actually shows values in HA.~~ **RESOLVED 2026-09-22 18:33 MST**, see above.
- **Front-porch as-built header** (folded in, see above) — confirm physically what BH1750 header is on the deployed front-porch board, and replace the inferred note in `front-porch-temp-sensor/perfboard-layout.md` with the observed fact.
- **Custom automation scope** — mirror front-porch's cool/warm notifications vs. something new; decide once the sensor is running (see `integration.md`'s deferral note).
- ~~**Network/DHCP reservation**~~ — **RESOLVED 2026-09-21.** IP `192.168.1.188`, MAC `04:B2:47:97:DF:44`, hostname `back-patio-temp-sensor.local`; row added to `network/jctsh-network.md`. Reserved on the TP-Link Archer AXE75 by Joseph, then **verified live rather than assumed**: the device was restarted via its MQTT restart button (`jctsh/components/back-patio-temp-sensor/button/back_patio_temp_sensor_restart/command`), re-requested DHCP, and came back on `192.168.1.188` with MQTT reconnected and the BH1750 publishing again. One of this card's two originally-deferred open items — now closed.

**Done when:** the component is built, flashed, mounted, and verified working per `testing.md` — plus the two open items above are resolved.

**Related:** `components/back-patio-temp-sensor/` (current build state, README onward), CARD-0165 (front-porch's Google Assistant work, relevant if voice exposure is added later), `house-lot-coordinates.md` (points P1–P4).

---

### CARD-0218 · [enhancement] [air-quality-monitor] Expose SEN55's own temperature/humidity readings — RESOLVED 2026-09-10
**Status:** Done

Archived to `components/air-quality-monitor/CLAUDE.md` on 2026-09-16 (CARD-0193) — 8456B, over the 5000B size threshold.

---

### CARD-0217 · [bug] [hiking-monitor] Progressive heat/brownout degradation mid-hike (2026-08-27) — a real reset crisis followed by an ~85-minute total device blackout, not a contained 9-minute event — RESOLVED 2026-09-10
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-09-16 (CARD-0193) — 18677B, over the 5000B size threshold.

---

### CARD-0216 · [bug] [hiking-monitor] Zero display_refresh events logged during a real multi-hour hike, despite the code's own logic guaranteeing several — RESOLVED 2026-08-27
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-09-10 (CARD-0193) — 9956B, over the 5000B size threshold.

---

### CARD-0215 · [bug] [data-pipeline] Duplicate Environmental Data rows from CARD-0211's reset loop, plus no dedup-on-ingest at all — RESOLVED 2026-08-25 evening
**Status:** Done

Archived to `core/data-pipeline/CLAUDE.md` on 2026-09-10 (CARD-0193) — 9957B, over the 5000B size threshold.

---

### CARD-0214 · [enhancement] [hike-izer] Two-pass hike-summary generation to close the GPSLogger-trigger-vs-late-data race — RESOLVED 2026-08-25 18:47 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-09-10 (CARD-0193) — 11758B, over the 5000B size threshold.

---

### CARD-0213 · [enhancement] [architecture] Quantified peak-current headroom standard for battery-powered builds — RESOLVED 2026-08-25
**Status:** Done

Archived to `architecture/card-archive.md` on 2026-09-28 (CARD-0193) — 4388B, over the 2000B size threshold.

---

### CARD-0212 · [enhancement] [hiking-monitor] Gate the hike-log replay burst behind the existing low-battery cutoff — RESOLVED 2026-08-25 17:26 MST
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-09-10 (CARD-0193) — 5726B, over the 5000B size threshold.

---

### CARD-0211 · [bug] [hiking-monitor] Analyze results for the 2026-08-25 hike — upload stuck in a reset loop — RESOLVED 2026-08-25 16:04 MST
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-09-10 (CARD-0193) — 12083B, over the 5000B size threshold.

---

### CARD-0210 · [enhancement] [hike-izer] Wildlife Life List: statistical analysis (detection frequency, trends over time) beyond the current per-species/per-hike view — RESOLVED 2026-08-25 evening
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-09-10 (CARD-0193) — 8464B, over the 5000B size threshold.

---

### CARD-0209 · [idea] [hike-izer] UV Index shown as a risk-level color (red/yellow/green), not just a raw number — RESOLVED 2026-08-25 evening
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-09-10 (CARD-0193) — 11239B, over the 5000B size threshold.

---

### CARD-0208 · [enhancement] [hiking-monitor] Spoken mile-marker announcements on the Pixel during a hike — RESOLVED 2026-09-17 18:02 MST
**Status:** Done

Archived to `components/hiking-monitor/card-archive.md` on 2026-09-18 (CARD-0193) — 19002B, over the 5000B size threshold.

---

### CARD-0207 · [enhancement] [hike-izer] Battery discharge-rate indicator, per-hike stat + cross-hike trend page — RESOLVED 2026-08-24
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-09-10 (CARD-0193) — 10923B, over the 5000B size threshold.

---

### CARD-0206 · [bug] [hike-izer] Environmental Data coverage stat measures against the padded query window instead of the real GPS session bounds — RESOLVED 2026-08-24
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-09-10 (CARD-0193) — 7310B, over the 5000B size threshold.

---

### CARD-0205 · [enhancement] [air-quality-monitor] Secondary debug UART for battery-powered serial logging via external USB-TTL adapter — RESOLVED 2026-09-10
**Status:** Done

Archived to `components/air-quality-monitor/CLAUDE.md` on 2026-09-16 (CARD-0193) — 15871B, over the 5000B size threshold.

---

### CARD-0204 · [enhancement] [hike-izer] Environmental Data (temp/humidity/pressure/UV) on the Elevation & Speed chart — RESOLVED 2026-08-24
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-09-10 (CARD-0193) — 17031B, over the 5000B size threshold.

---

### CARD-0202 · [idea] [hiking-monitor] Real solar_v sensing — wire up the ADC divider CARD-0017 designed but never built — RESOLVED 2026-09-10
**Status:** Done

Archived to `components/hiking-monitor/card-archive.md` on 2026-09-28 (CARD-0193) — 3387B, over the 2000B size threshold.

---

### CARD-0201 · [enhancement] [hiking-monitor] True deep-sleep-between-samples in field mode — RESOLVED 2026-09-10
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-09-16 (CARD-0193) — 6969B, over the 5000B size threshold.

---

### CARD-0203 · [enhancement] [hiking-monitor] Longer-but-same-thickness LiPo — fit confirmed, candidate cell out of stock
**Status:** Backlog

**Raised 2026-08-23 07:27 MST (corrected 2026-09-22 — written `14:27`, 7h fast via the `TZ=` clock bug, see CARD-0329) (Joseph), broken out from CARD-0196 item 4** (and separately again from CARD-0196 immediately after CARD-0201 was split out) — this is physical research/procurement work, not firmware, and closes on a different timeline (Joseph's hands on the enclosure) than the firmware cards it was originally bundled with.

**Goal:** a physically longer 3.7V LiPo (same thickness as the current EEMB 1100mAh cell) might fit the existing 3D-printed enclosure (CARD-0009) without a redesign, if there's clearance in an unused dimension — more capacity without touching the boost-converter inefficiency CARD-0070 would fix.

**Sourcing done, 2026-08-23 07:27 MST (corrected 2026-09-22 — written `14:27`, 7h fast via the `TZ=` clock bug, see CARD-0329) — real candidate identified:** [EEMB LP603466](https://eemb.store/products/lp603466-3-7v-1400mah), 3.7V 1400mAh, 6.5×34.5×68mm, JST connector, PCM-protected (overcharge/overdischarge/overcurrent/short-circuit), UL-certified and UN 38.3 compliant — same safety profile as the current cell. Verified against the current cell's own real dimensions, [EEMB LP603449](https://eemb.store/products/lp603449) at 6.3×34.5×50mm/1100mAh: essentially identical thickness (6.5 vs 6.3mm — within normal manufacturing tolerance) and identical width (34.5mm both), **18mm longer for +27% capacity.** Same manufacturer/product family as the currently-deployed cell (`hiking-monitor-claude-code-instructions.md`, `JCTsh-hiking-monitor-phase1.md`), so no new supplier-trust question.

**Fit confirmed, 2026-08-23 (Joseph) — the 68mm length fits the physical enclosure.**

**Candidate out of stock, 2026-08-23 (Joseph, confirmed on Amazon).** The sourced LP603466 is not currently purchasable.

**Done when:** a purchasable cell matching the confirmed-fitting envelope (~6.3-6.5mm thick, 34.5mm wide, up to 68mm long) is identified and ordered.

**Related:** CARD-0196 (the parent card this was broken out of), CARD-0009 (enclosure build — and the undocumented-internal-dimensions gap this card has to work around), CARD-0017 (unrelated schema card, no connection beyond both concerning the LiPo/charging system), `components/hiking-monitor/power-system.md`, `components/hiking-monitor/hiking-monitor-enclosure-plan.md`.

---

### CARD-0200 · [bug] [hiking-monitor] Low-battery safety cutoff silently disabled by solar (shares dock-detect signal with USB) — cheap fix built and flashed — RESOLVED 2026-08-24
**Status:** Done

Archived to `components/hiking-monitor/card-archive.md` on 2026-09-28 (CARD-0193) — 4318B, over the 2000B size threshold.

---

### CARD-0199 · [enhancement] [hiking-monitor] E-ink display shows Connected/Uploading/Upload-complete-with-duration during post-hike sync — RESOLVED 2026-08-27
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-09-10 (CARD-0193) — 7110B, over the 5000B size threshold.

---

### CARD-0198 · [bug] [air-quality-monitor] Boot sequence resumes SEN55 Measurement mode on a blind fixed delay instead of an actual connectivity check — RESOLVED 2026-09-08
**Status:** Done

Archived to `components/air-quality-monitor/CLAUDE.md` on 2026-09-10 (CARD-0193) — 59721B, over the 5000B size threshold.

---

### CARD-0197 · [idea] [data-pipeline] Instrument GPS correlation lookup to confirm the suspected Node-RED/Apps Script timing race — RESOLVED 2026-08-29
**Status:** Done

Archived to `core/data-pipeline/CLAUDE.md` on 2026-09-10 (CARD-0193) — 6612B, over the 5000B size threshold.

---

### CARD-0196 · [enhancement] [hiking-monitor] Extend field-mode hike endurance — display refresh throttling — RESOLVED 2026-09-10
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-09-16 (CARD-0193) — 8697B, over the 5000B size threshold.

---

### CARD-0195 · [enhancement] [hiking-monitor] Field-mode diagnostic instrumentation — skip-reason logging and reset-reason detection — RESOLVED 2026-08-24
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-09-10 (CARD-0193) — 7612B, over the 5000B size threshold.

---

### CARD-0194 · [idea] [hike-izer] Iterative hike-izer webpage improvements from the 2026-08-22 hike — RESOLVED 2026-08-24
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-09-10 (CARD-0193) — 11174B, over the 5000B size threshold.

---

### CARD-0193 · [idea] [tos] Kanban board scaling strategy — RESOLVED 2026-09-27 20:57 MST
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-27 (CARD-0193) — 24368B, over the 5000B size threshold.

---

### CARD-0192 · [idea] [tos] Watchdog self-test for the kanban-PR intake pipeline — RESOLVED 2026-09-10
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-16 (CARD-0193) — 9564B, over the 5000B size threshold.

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

Archived to `components/photo-quality-review/card-archive.md` on 2026-09-28 (CARD-0193) — 3584B, over the 2000B size threshold.

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

Archived to `core/homeassistant/card-archive.md` on 2026-09-28 (CARD-0193) — 3208B, over the 2000B size threshold.

---

### CARD-0184 · [bug] [outdoor-presence-detection] CARD-0145's Ring motion announcement has been silently dead since 2026-08-15 — RESOLVED 2026-08-18 17:02 MST
**Status:** Done

Archived to `components/outdoor-presence-detection/CLAUDE.md` on 2026-08-22 (CARD-0193) — 10489B, over the 10000B size threshold.

---

### CARD-0183 · [bug] [hike-izer] Hike-publish push notification link isn't clickable — RESOLVED 2026-08-18 15:11 MST
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 2312B, over the 2000B size threshold.

---

### CARD-0182 · [idea] [hike-izer] BirdNET Live recording practices while hiking — DONE 2026-08-19
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 3994B, over the 2000B size threshold.

---

### CARD-0181 · [bug] [hiking-monitor] No way to cut real power without disassembling the enclosure — RESOLVED 2026-09-10
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-09-16 (CARD-0193) — 9316B, over the 5000B size threshold.

---

### CARD-0180 · [enhancement] [hiking-monitor] On-demand remote reboot, triggered from Home Assistant — RESOLVED 2026-08-19 17:24 MST
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5781B, over the 5000B size threshold.

---

### CARD-0186 · [bug] [front-porch-temp-sensor] [salt-sensor] Restart button MQTT discovery id collision — RESOLVED 2026-08-19
**Status:** Done

Archived to `components/front-porch-temp-sensor/card-archive.md` on 2026-09-28 (CARD-0193) — 4024B, over the 2000B size threshold.

---

### CARD-0179 · [idea] [tos] Route captured voice notes to LogSeq, alongside the kanban PR pipeline — RESOLVED 2026-09-20 15:22 MST
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 7537B, over the 5000B size threshold.

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

### CARD-0172 · [idea] [architecture] Disaster Recovery — auto-opened from jctsh-core — RESOLVED 2026-08-16 19:30 MST
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-08-22 (CARD-0193) — 9049B, over the 5000B size threshold.

---

### CARD-0171 · [enhancement] [m8] M8 UEFI Secure Boot KEK CA firmware update available — auto-opened from photo-server — RESOLVED 2026-08-16 19:00 MST
**Status:** Done

Archived to `hosts/m8/card-archive.md` on 2026-09-28 (CARD-0193) — 3706B, over the 2000B size threshold.

---

### CARD-0170 · [enhancement] [homeassistant] Container image updates: home-assistant: 2026.8.2 available (running 2026.8.1) — auto-opened from jctsh-core — RESOLVED 2026-08-16 18:00 MST
**Status:** Done

Archived to `core/homeassistant/card-archive.md` on 2026-09-28 (CARD-0193) — 4879B, over the 2000B size threshold.

---

### CARD-0169 · [idea] [homeassistant] Scheduled volume levels by Google Home speaker, by time window
**Status:** Defer

Archived to `core/homeassistant/card-archive.md` on 2026-09-28 (CARD-0193) — 2131B, over the 2000B size threshold.

---

### CARD-0168 · [bug] [homeassistant] Remove deprecated `http:` YAML block, resync stale configuration.yaml — RESOLVED 2026-08-14 19:28 MST (corrected 2026-09-22, see CARD-0329 — written `2026-08-15 02:28`, 7h fast via the `TZ=` clock bug)
**Status:** Done

Archived to `core/homeassistant/card-archive.md` on 2026-09-28 (CARD-0193) — 4010B, over the 2000B size threshold.

---

### CARD-0167 · [enhancement] [architecture] Close CARD-0096's mDNS transition-window aliases — RESOLVED 2026-08-17 12:11 MST
**Status:** Done

Archived to `architecture/card-archive.md` on 2026-09-28 (CARD-0193) — 3592B, over the 2000B size threshold.

---

### CARD-0166 · [enhancement] [homeassistant] Synchronize room/area names across HA, Google Home, and SmartThings — HA as master
**Status:** Build

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

### CARD-0164 · [enhancement] [architecture] Samsung ending free SmartThings API access October 2026 — decide pay vs. migrate before then
**Status:** Planning

**Priority:** High -- a real deadline: Samsung ends free SmartThings API access in October 2026, and this instance has a confirmed blast radius (Auto verify 2026-10-02). (set 2026-09-29 15:32 MST, triage)

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

**Decided 2026-09-11 — a fourth direction, distinct from the three originally scoped above: deprecate the paid API dependency, leave the physical hub alone.** Prompted by installing the household's first Matter devices (3 Cync under-cabinet lights, added via SmartThings) and a real conversation about whether SmartThings is still earning its place in JCTsh's own architecture. Neither pure "pay" nor full "migrate":

- **Don't pay, don't renew the developer Personal Plan.** Confirmed via Samsung's own blog language already quoted above ("does not affect the millions of SmartThings users who use the SmartThings App") that this only prices *third-party API consumption* — the SmartThings app, hub, and its own native Google Home account-link (the actual mechanism behind "shared with Google Home" for any device, JCTsh-built or not) all keep working exactly as today, for free, indefinitely.
- **Don't migrate the existing hardware off SmartThings.** Most lights/sensors/the front door lock are genuine Zigbee/Z-Wave hardware paired to the SmartThings hub's own radio — moving them would mean a USB coordinator, re-pairing every device, and rebuilding every scene. Real, already-scoped work above, deliberately **not** pursued now — no deadline forces it (the hub keeps running free regardless), so it stays an optional, no-timeline project for someday, not part of this card's own scope.
- **Accept that HA loses live visibility into non-JCTsh SmartThings entities.** The ~100+ entities from the original blast-radius count (real lights, sensors, the lock, Ring, scenes) will very likely stop syncing into HA once the paid tier lapses — but since Robin's actual voice control of that hardware goes through SmartThings' own native Google Home link, not HA, this is a **Joseph-side dashboard/automation-visibility cost only, not a Robin-facing outage.** Ring specifically already has its own separate native HA integration in live use (`outdoor-presence-detection`), unaffected either way.
- **Scope narrows to exactly two real dependencies**, found via a full-repo sweep 2026-09-11 (grepped every file mentioning SmartThings — everything else is historical/incidental, no other live functional dependency exists): the two SmartThings Routines that use JCTsh-created virtual switches, and salt-sensor's four Google-visibility switches. Both scoped as their own cards, not built here:
  - **CARD-0260** — rebuild the Auto-Close (`automatic-garage-door-opener-closer`) and Presence-Off (`garage-presence`) SmartThings Routines as native HA automations, replacing their SmartThings-backed vswitches (`garage_door_auto_close_enable_vswitch`, `garage_door_open_vswitch`, `garage_presence_vswitch`) with genuine HA-native helper entities.
  - **CARD-0261** — replace salt-sensor's SmartThings-synced switches (`salt_low_alert`, `salt_critical_alert`, `salt_test_mode`, `salt_full_reset`) with HA-native helpers, exposed to Google Home via HA's own native Google Assistant integration (Nabu Casa) instead of the SmartThings relay.
- **New-device policy, going forward:** written into `JCTsh-Build-Standards.md` (see Related) — every future smart-home device defaults to Matter-direct-to-HA/Google or a native HA integration, SmartThings only by deliberate exception. The 3 Cync lights (confirmed Matter-over-WiFi, no Thread Border Router needed) are the concrete case that prompted this — they never needed SmartThings at all, they just happened to get set up there.

**Auto verify: 2026-10-02 09:00 MST** — the one open item from the 2026-09-11 planning session with no way to confirm live yet: exactly what happens to HA's SmartThings-synced entities once the free API tier actually lapses (Samsung hasn't published rate limits or enforcement mechanics as of this writing — "genuinely still evolving" per the note above). Check directly: do non-JCTsh SmartThings entities in HA go fully unavailable, or degrade more gracefully (stale-but-present, partial)? Does CARD-0260/CARD-0261's rebuilt HA-native logic keep working cleanly once the integration itself starts failing/erroring, or does a broken SmartThings config entry cause any wider HA disruption worth guarding against? Confirms whether the "Joseph-side visibility cost only" assumption above actually holds.

**Done when:** CARD-0260 and CARD-0261 are both built, deployed, and verified live; the Personal Plan subscription is never created (or is confirmed already lapsed with no ill effect on JCTsh's own components); the Auto verify above is checked and its findings folded back in here.

**Related:** CARD-0146 (the investigation that surfaced this), CARD-0260 (garage Routines rebuild), CARD-0261 (salt-sensor switches rebuild), `JCTsh-Build-Standards.md` (the new-device policy this decision produced), `ENVIRONMENT.md` (SmartThings device inventory), CLAUDE.md's SmartThings Integration section, `components/outdoor-presence-detection/CLAUDE.md` (the precedent that already chose HA-native over SmartThings-Routine for this exact reason), `core/maintenance/reboot-health-check.py` (its `AUTO_RELOAD_DOMAINS` tuple still names `smartthings` — harmless to leave for now, worth dropping once the integration itself is actually removed).

---

### CARD-0163 · [bug] [logging] Non-heartbeat log entries can get stuck unflushed indefinitely in log_server.py's `_pending` buffer — RESOLVED 2026-08-14 08:30 MST
**Status:** Done

Archived to `core/logging/card-archive.md` on 2026-09-28 (CARD-0193) — 3607B, over the 2000B size threshold.

---

### CARD-0162 · [enhancement] [tos] PR-to-kanban-card landing process for CARD-0128 auto-opened findings — RESOLVED 2026-08-14 07:28 MST
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6679B, over the 5000B size threshold.

---

### CARD-0161 · [enhancement] [netalertx] Container image updates: netalertx: v26.8.5 available (running 26.7.1) — auto-opened from photo-server — RESOLVED 2026-08-14 08:27 MST
**Status:** Done

Archived to `components/netalertx/card-archive.md` on 2026-09-28 (CARD-0193) — 4690B, over the 2000B size threshold.

---

### CARD-0160 · [enhancement] [m8] Container image updates: cloudflared: 2026.8.2 available (running 2026.7.3) — auto-opened from photo-server — RESOLVED 2026-08-14 07:39 MST
**Status:** Done

Archived to `hosts/m8/card-archive.md` on 2026-09-28 (CARD-0193) — 2172B, over the 2000B size threshold.

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

Archived to `components/photo-quality-review/card-archive.md` on 2026-09-28 (CARD-0193) — 3790B, over the 2000B size threshold.

---

### CARD-0154 · [idea] [hiking-monitor] DIY Li-ion overcharge-cutoff circuit (Hackster.io) — evaluated, not applicable
**Status:** Done

Archived to `components/hiking-monitor/card-archive.md` on 2026-09-28 (CARD-0193) — 3198B, over the 2000B size threshold.

---

### CARD-0153 · [idea] [homeassistant] Move HA recorder off SQLite to MariaDB (or Postgres) if it ever becomes a real problem
**Status:** Backlog

**Raised 2026-08-12**, from Joseph reading an article about SQLite concurrency/write-lock issues under Home Assistant and asking whether JCTsh's HA instance should move off it.

**Why SQLite can be a problem, for context:** SQLite locks at the whole-database-file level — even in WAL mode (which HA enables by default), only one write transaction can be in flight at a time, so every other writer queues behind it. Under a heavy install (many entities, frequent automations), the recorder's write queue can back up behind that single-writer lock, worse on slow storage like a Pi's SD card. MariaDB (InnoDB) and PostgreSQL instead lock at the row level and use MVCC, so a write and a concurrent read (e.g. the frontend loading a history graph) don't block each other — real client-server databases built for concurrent multi-client load, unlike SQLite's embedded single-writer model.

**Explicitly not being pursued now.** Checked whether this JCTsh instance actually has the problem: the "could not validate shutdown cleanly" / "ended unfinished session" recorder warnings seen in `docker logs` during CARD-0150/0152's testing this session were almost certainly artifacts of repeated fast `docker restart` cycles (SQLite doesn't get time to flush before SIGTERM) rather than evidence of a real concurrency problem during normal operation. At JCTsh's current scale (modest entity count, not a heavy-automation install), SQLite's single-writer limitation isn't expected to bite. Joseph's call: leave it as SQLite, watch for real symptoms.

**Trigger conditions for actually pursuing this** (either one): recorder errors appearing during *normal* operation (not around a deliberate restart), or the History/Logbook UI becoming noticeably slow. Neither has been observed.

**If pursued, one option discussed:** run the database as its own container on the M8 (`photo-server`, `192.168.1.165`) rather than on the Pi, since HA's `recorder:` config accepts any reachable `db_url` — the M8 is already running Docker and is more capable than the Pi. Two real snags flagged, not yet resolved:
1. HA's official Docker image doesn't bundle a PostgreSQL/MariaDB Python driver by default — would need a custom image or an init step to install one.
2. Creates a new cross-device dependency that doesn't exist today — HA's recorder would go dark any time the M8 is unreachable, including the M8's own weekly scheduled reboot (Mon 4am) — worth checking that window against the Pi's own Monday 3am reboot stagger (see `network/jctsh-network.md`'s Scheduled Maintenance Windows table) if this is ever built, since the whole point of that stagger was avoiding a different false-down reading and a DB dependency adds a second reason to care about the timing.

**Done when (if ever picked up):** not yet defined — this card is parked as an idea, not scoped for Planning. Needs a real interview (which engine, where hosted, migration approach for existing history data, backup coverage) before any implementation starts.

**Related:** `network/jctsh-network.md` (M8 host details, maintenance-window table).

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

Archived to `components/photo-quality-review/card-archive.md` on 2026-09-28 (CARD-0193) — 3906B, over the 2000B size threshold.

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

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 3250B, over the 2000B size threshold.

---

### CARD-0142 · [enhancement] [hike-izer] Cross-hike Wildlife Life List
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6345B, over the 5000B size threshold.

---

### CARD-0141 · [enhancement] [hike-izer] Push notification to Joseph's Pixel on hike-summary publish success/failure
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 4261B, over the 2000B size threshold.

---

### CARD-0140 · [bug] [hike-izer] GPS accuracy noise falsely triggers "sustained non-walking pace" truncation, excluding real hike time from stats
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6885B, over the 5000B size threshold.

---

### CARD-0139 · [enhancement] [logging] Exclude bench-test/dev components from the /status dashboard
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

Archived to `components/hiking-monitor/card-archive.md` on 2026-09-28 (CARD-0193) — 4200B, over the 2000B size threshold.

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

### CARD-0131 · [enhancement] [photo-server] Immich update available: v3.1.0 (currently running v3.0.1) — auto-opened from photo-server
**Status:** Done

Archived to `components/photo-server/card-archive.md` on 2026-09-28 (CARD-0193) — 2507B, over the 2000B size threshold.

---

### CARD-0130 · [enhancement] [homeassistant] Container image updates: home-assistant: 2026.7.4 available (running 2026.5.1) — auto-opened from jctsh-core — RESOLVED 2026-08-13 21:50 MST
**Status:** Done

Archived to `core/homeassistant/card-archive.md` on 2026-09-28 (CARD-0193) — 3699B, over the 2000B size threshold.

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

### CARD-0103 · [idea] [website] Migrate 3 legacy Google Sites pages (Cochie Springs hike, Mustang, Karli's Summer) to the M8 webserver — low priority
**Status:** Backlog

**Raised 2026-07-27**, during CARD-0093 (DNS cleanup). CARD-0093's original plan let `jctnet.com`'s Google Sites content go entirely (Joseph had called it unimportant), but revisiting surfaced that 3 specific pages are still wanted — dropping the `www` CNAME and `google-site-verification` TXT as part of CARD-0093 will break their reachability at `jctnet.com`/`www.jctnet.com`, even though the underlying Google Sites content itself isn't deleted by a DNS change (it stays live at its own `sites.google.com` URL, just unmapped from the custom domain).

**Scope:**
- Export the source content (text/photos) for all 3 pages from the live Google Sites pages — content only exists there right now, not backed up elsewhere.
- Rebuild them as static pages served from the M8 (alongside the existing `hike-izer-web` static content / Caddy setup, or a sibling route — exact placement TBD at build time).
- **Done when:** all 3 pages are publicly reachable at a real URL again (not just archived files on disk) — final URL/path scheme (e.g. under the existing Tailscale Funnel domain, a new subdomain, etc.) is an open decision for whoever picks this up.

**Open question, deferred to this card (raised 2026-07-27 while resolving CARD-0093's Search Console question):** both `jctnet.com` and `jctnet.net` currently show zero indexed pages in Search Console, so CARD-0093 doesn't bother re-verifying/maintaining Search Console for the now-dormant `jctnet.com`. But once these 3 pages are actually live again on the M8, whether they should be discoverable/indexed by Google (i.e. set up Search Console for wherever they end up living) is a separate decision — not resolved, not urgent, revisit when this card is picked up.

**Priority:** Low — not blocking CARD-0093, which proceeds with full jctnet.com teardown (including the Google Sites CNAME/TXT records and the root A/parking records) regardless of when this is picked up. Google Sites keeps serving the content at its native URL in the meantime, so there's no hard deadline to act before CARD-0093 executes.

**Related:** CARD-0093 (the DNS cleanup that prompted this), CARD-0088/CARD-0092 (existing M8 static-hosting precedent via Caddy).

---

### CARD-0096 · [enhancement] [architecture] Rename photo-server → m8 and raspberrypi → pi1, adopt a real host-naming convention — RESOLVED 2026-08-14 16:15 MST
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

### CARD-0055 · [bug] [garage-presence] Reconcile garage-radar/SmartThings light control — lights sometimes don't turn on — RESOLVED 2026-09-12 MST (Joseph's call)
**Status:** Done

Archived to `components/garage-presence/card-archive.md` on 2026-09-28 (CARD-0193) — 3829B, over the 2000B size threshold.

---

### CARD-0045 · [bug] [hiking-monitor] `wifi.ap:` fallback may prevent `reboot_timeout` from working — RESOLVED 2026-08-27
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-09-10 (CARD-0193) — 6851B, over the 5000B size threshold.

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


### CARD-0114 · [enhancement] [tos] Status field per card, replacing physical column position — RESOLVED 2026-07-29 16:28 MST
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 4635B, over the 2000B size threshold.

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

### CARD-0071 · [idea] [logseq] Emergency Access preparation
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

### CARD-0041 · [idea] [m8] Disk capacity growth analysis — wait for steady state
**Status:** Build

**Retagged `[photo-server]` → `[m8]`, 2026-09-18 (Joseph's call, photo cluster session).** This card is about the M8 host's physical drives, not the Immich application itself — the same host-specific-work criterion CARD-0294's planned retag sweep applies to cards like CARD-0238/CARD-0272. Flagged live rather than deferred to that sweep, since it directly affected this card's own scope determination.

**Notes:** Discussed 2026-07-09: want to estimate photo-library growth rate and project when the primary drive (Backup Plus 1TB, currently 615G/71% used) or backup drive (Momentus 640GB) will need replacing/upsizing. Deliberately not started yet — Joseph's call: current disk numbers are all noise from one-off events (CARD-0039 added 3,433 assets in one shot, CARD-0030 just freed 818GB by deleting zips, first post-cleanup backup run is still doing a full reconciliation rather than a normal weekly delta), not representative of organic day-to-day growth.

**Watch for (RESOLVED 2026-09-18, see below):** the backup cron (CARD-0030/CARD-0040) running its normal weekly incremental cadence for a few cycles, so disk usage tracking reflects only real photo uploads from Joseph's and Robin's phones — no fixed date, just "after the dust settles." At that point, weekly rsync deltas become a meaningful proxy for actual growth rate and a "months until full" estimate becomes trustworthy rather than a guess. Revisit this card once that's true. (Predates the Auto verify marker convention — originally written as plain "Wait for:" prose, 2026-07-09; converted to the real marker 2026-09-08 so it actually shows up on `/kanban` and Session Start's grep, per CARD-0251.)

**Watch-for resolved, 2026-09-18 (photo cluster session startup, CARD-0251/CARD-0258 resolution protocol).** Checked live rather than assumed: `journalctl -u cron` on the M8 shows the weekly backup cron (`15 2 * * 0`) has fired every Sunday, unbroken, for 11 consecutive weeks (2026-07-05 through 2026-09-13) — well past CARD-0030/CARD-0039's one-off cleanup (2026-07-09/10) that originally made the numbers noisy.

**Growth analysis performed, 2026-09-18 (same session — sufficient data confirmed available, so done now rather than deferred).** Source: the 7 confirmed clean weekly cron runs since the cleanup fully settled (2026-08-02 through 2026-09-13 — `backup.md`'s split-by-account architecture means each weekly run logs two independent `rsync` transfer sizes, one per account), read from `/var/log/photo-library-backup.log`'s per-run `sent ... bytes` summaries:

| Week | Joseph's delta | Robin's delta | Combined |
|---|---|---|---|
| 2026-08-02 | 5.59 GB | 4.93 GB | 10.52 GB |
| 2026-08-09 | 5.69 GB | 5.49 GB | 11.17 GB |
| 2026-08-16 | 5.62 GB | 5.76 GB | 11.38 GB |
| 2026-08-23 | 5.50 GB | 5.45 GB | 10.96 GB |
| 2026-08-30 | 6.20 GB | 5.41 GB | 11.60 GB |
| 2026-09-06 | 5.51 GB | 5.40 GB | 10.90 GB |
| 2026-09-13 | 5.22 GB | 5.20 GB | 10.42 GB |

Combined weekly variance is tight (10.42–11.60 GB, no trend up or down) — real confirmation this is steady organic growth, not lingering reconciliation noise. Average combined ≈ **11.0 GB/week** (Joseph ≈5.62 GB/week, Robin ≈5.38 GB/week — split is close to even, not badly lopsided despite Joseph's library being larger overall).

**Current usage (`df -h` on the M8, 2026-09-18)** — three drives now, not two (CARD-0030's 2026-07-10 split-by-account redesign added a second backup drive after the original two-drive framing was written):

| Drive | Mount | Size | Used | Avail | Weekly growth | Est. time to full |
|---|---|---|---|---|---|---|
| Primary (both accounts) | `/mnt/photo-library` | 916G | 584G (68%) | 287G | ~11.0 GB/wk combined | **~28 weeks (~6.5 months, early Apr 2027)** |
| Joseph's backup | `/mnt/photo-library-backup-joseph` | 916G | 422G (49%) | 448G | ~5.62 GB/wk | ~86 weeks (~20 months) |
| Robin's backup (Momentus) | `/mnt/photo-library-backup` | 586G | 175G (32%) | 382G | ~5.38 GB/wk | ~76 weeks (~17.5 months) |

**The primary drive is the real bottleneck**, not either backup — both backups have well over a year of headroom at current growth. Linear extrapolation from 7 weeks of steady data; doesn't account for seasonal upload spikes (holidays, travel) that could pull the primary's ~6.5-month estimate earlier. "Months until full" is a real, trustworthy number now, per this card's own original done-when framing — whether to act at 100% full vs. some earlier threshold (85%/90%), and whether to replace or just upsize the primary drive, is a decision left for Joseph, not made here.

**Act-by date, monitoring, and resolve-before-needed, worked out 2026-09-18.**

- **Monitoring already exists — nothing new to build.** `photo-server-heartbeat.py` (CARD-0051, Done) already checks all three mounts' `shutil.disk_usage()` every 30 minutes and raises a non-collapsing dashboard `Alert` (`<mount>-capacity:<pct>% used`) once any crosses `CAPACITY_THRESHOLD_PCT = 90`. Confirmed live in the deployed script, not assumed from the card text alone. This already covers the primary drive — CARD-0046/CARD-0051 built this specifically so a capacity problem doesn't go undetected the way Momentus's 2026-07-10 hardware failure originally did.
- **When the 90% alert would organically fire, projected from this card's own growth rate:** primary is at 584G/916G (68%) now; 90% is 824.4G, leaving 240.4G of headroom at ~10.24 GiB/week ≈ **~23.5 weeks out, around 2027-03-01**. That's the passive backstop — it fires on its own even if nobody revisits this card.
- **The gap: an alert firing reactively isn't the same as a deliberate decision made ahead of it.** Reaching the dashboard alert with no plan yet means scrambling to source/install a replacement or upsized drive under time pressure. To force an earlier, deliberate checkpoint instead of relying on someone noticing a live alert: **`Auto verify: 2027-02-01`** — added below, one month ahead of the projected 90% alert and roughly two months ahead of the projected ~6.5-month full-at-current-rate date (early Apr 2027). This will resurface automatically at the first session on/after that date per the Auto Verify protocol (`JCTsh-Operating-System.md`), prompting Joseph to actually decide (replace vs. upsize the primary drive, or re-check actual usage against this projection first) rather than depending on passively noticing the heartbeat alert.

**Auto verify: 2027-02-01** — re-check actual primary-drive usage (`df -h /mnt/photo-library` on the M8) against this card's ~11.0 GB/week projection; if still on pace, this is the deliberate decision point for replacing/upsizing the primary drive before the heartbeat's own 90% alert (projected ~2027-03-01) or actual full (~early Apr 2027) arrive. If growth has meaningfully diverged from the projection (seasonal spike or slowdown), recompute from the then-current weekly deltas rather than trusting this date blindly.

**Left in Build, not closed** — the projection and the monitoring/decision-date plan are both done; the actual replace/upsize decision itself is deliberately deferred to the 2027-02-01 checkpoint above, not made now.

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

~~Still technically trivial as originally scoped: Google Sheets is a native Looker Studio data source (GPS Track + Environmental Data sheets), no new infrastructure.~~ **Stale as of CARD-0349, 2026-09-29** — GPS Track/Environmental Data now live in TimescaleDB (self-hosted on the M8), not Sheets; the "no new infrastructure" framing no longer holds as written. Real upside, not just a correction: TimescaleDB is exactly the kind of backend Grafana is built to pair with (per CARD-0349's own technology comparison) — arguably a better fit for this card's actual cross-hike/trend goal than Looker Studio ever was, self-hosted like the rest of this project's dashboards rather than a Google Workspace dependency. Whichever tool, this card needs a real rescope (data source, and Looker-vs-Grafana) before anyone picks it up — not decided here, just flagged so the next session doesn't start from the stale premise.

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

**Real root cause: an intermittent, not permanent, bad connection — found via the adapter's own power LED, not the multimeter.** The LED visibly brightened during the in-series current test (which had spliced the meter directly into the Collector-to-adapter-GND wire, replacing it) — pointing at that specific wire. Swapping it for a fresh jumper brightened the LED, but on the next fresh boot the LED was briefly bright, then went immediately dim, then brightened again and held — a pattern (wiggle: no effect; full removal and reinsertion: fixes it) that was *suspected* at the time to be a marginal/oxidized breadboard contact point, not a broken wire or bad transistor. Even so, a subsequent ~8-minute run with the LED reportedly stable still produced zero valid readings — the full picture isn't necessarily explained by "one bad breadboard hole" alone; flagged as a real open question, not fully resolved.
>
> **Correction (2026-08-24):** the "oxidized breadboard contact" explanation above was never actually confirmed and has since been disproven — swapping jumper wires and moving to different breadboard positions during later testing did not resolve intermittent-connection-shaped symptoms, meaning a bad breadboard socket was not the real cause. Don't cite "oxidized breadboard contact" as an established finding of this project; the underlying cause of this specific Step 4 symptom remains unresolved.

**Real design question surfaced, not just a component fault: low-side vs. high-side switching for this specific load.** `wiring.md`'s existing justification for the NPN low-side (GND-return) switch — that the SEN55/adapter sit on "their own 5V-boosted rail" — doesn't hold up under scrutiny: the natural high-side switching point (the adapter's `VIN` pin) is fed directly from the shared 3.3V rail, the same domain `JCTsh-Build-Standards.md` §2.14 point 8's P-FET pattern was designed for and which was dismissed as "not applicable here." Low-side switching has a structural weakness directly relevant to tonight's whole ordeal: any marginal connection in the GND-return path doesn't just reduce voltage to the load, it shifts the load's *entire ground reference* away from the controller's — exactly the kind of failure that silently breaks I2C while individual voltage checks still look fine. High-side switching would leave GND permanently, solidly tied to common ground, so a marginal connection there would only ever show up as insufficient voltage — a more benign, easier-to-diagnose failure mode. **Neither pattern is actually validated end-to-end in this project** — §2.14 point 8's P-FET candidate was never finished (CARD-0070, deferred), and tonight is the low-side pattern's first real test, which it has not yet passed cleanly. Worth treating as a genuine open redesign question for Step 6, not just "find the bad wire and move on."

**Current physical state:** bypass jumper (adapter `GND` directly to common ground rail) back in place — this is the same configuration proven at the very start of tonight's session, and confirmed again just now: real, plausible SEN55 data (PM1.0/2.5/4.0/10 ~1.0–1.5 µg/m³, VOC climbing 17→33 over successive readings — normal warm-up curve, NOx settled at 1), first valid reading only 12 seconds after boot. **Step 4's own done-when is met on this configuration** — all SEN55 fields reporting plausible values, confirmed live. The BC547B gate circuit is set aside, not removed, still wired on the breadboard but out of the active power path. Step 6 (bench-testing the power gate) now inherits tonight's findings directly — decide there whether to keep debugging the low-side approach or build the high-side alternative before calling the gate circuit itself validated.

**Step 5 done, 2026-08-21 10:50 MST — same session.** PM2.5 → RGB threshold logic implemented as an `on_value` trigger directly on the `pm_2_5` sensor (fires exactly when a new reading arrives, no separate polling), driving three `output: platform: gpio` components (GPIO18/19/23) with simple on/off combinations — green (<12 µg/m³), yellow (12-35, red+green combined), red (>35). No PWM/dimming needed for three solid states. Deployed cleanly (config validated via `esphome config` first, matching this session's established practice after Step 4's firmware bug), clean boot, no errors. **Verified live:** PM2.5 at 2.0 µg/m³, green LED confirmed on by Joseph directly at the device — matches the threshold, sensor logic and LED logic both intact together.

**Real, useful research surfaced while investigating the power-gate redesign, worth folding into Step 8's design:** Sensirion's own "Reduced Power Operation for SEN5x" document recommends duty-cycling between **Measurement mode** (~63mA, full PM+RHT+VOC+NOx) and **RHT/Gas-Only mode** (laser+fan off, ~lower draw, humidity/temp/VOC/NOx only, no PM) as the primary power-saving mechanism — not physically power-cycling the sensor on/off. Alternating these two modes can cut power ~7-9x with minor accuracy tradeoffs, and is what Sensirion frames as making battery operation viable at all. Two real discrepancies against this project's existing assumptions, worth reconciling before Step 8 locks in duty-cycle timing: (1) Sensirion recommends a **30-60 second warm-up** after leaving a low-power state for good accuracy (8s is documented as an absolute floor, not recommended) — longer than Phase 1's assumed ~10s active window per 2-minute cycle; (2) if genuinely power-cycling the sensor fully off/on (not just switching to RHT/Gas-Only mode), Sensirion recommends **triggering a cleaning cycle at least weekly** if power-cycling roughly daily — a fan self-cleaning maintenance requirement, not just a power concern. Worth deciding at Step 8 whether to duty-cycle via mode-switching (software, sidesteps the gate-circuit reliability question entirely for routine cycling) rather than physical power gating for anything other than true full-off between hikes.

**Step 5 fully closed, 2026-08-21 11:53 MST.** Yellow and red threshold colors verified live (green already confirmed above) via a boot-time color-hold sequence (solid Yellow 3s, solid Red 3s) using substituted PM2.5 output states rather than a real particulate source — added as a **permanent** part of the boot sequence per Joseph's preference, not a one-off test removed afterward. Also added this session: boot self-test LED sequence (two quick blinks each of Blue/Red/Yellow/Green), an unbounded green-blink "waiting for first valid reading" loop with no timeout (deliberately, per the Step 4 lesson that a "looks connected" fault can silently produce zero readings for a long time), a solid-green "all is well" confirmation, and blink-mode operational LEDs (brief ~1s flash per reading instead of continuous-on, for battery savings). Full behavior documented in `README.md`'s new LED Status Guide section.

**Step 6 decision: drop the SEN55 power-gate transistor entirely, 2026-08-21 12:13 MST.** Revisiting *why* a gate was wanted in the first place (rather than re-litigating low-side vs. high-side, per tonight's open question above) resolved it a different way — the two real use cases are both already covered without a dedicated gate: (1) routine duty-cycling during a hike is better served by Sensirion's own recommended I2C mode-switching (Measurement ↔ RHT/Gas-Only, from the research two paragraphs up) than by physically cutting power, and (2) true full-off for storage/transport is already handled by the existing inline power switch (Step 1, cuts the whole battery). With no remaining use case, the gate is dropped — SEN55's `GND` return is now permanently wired direct to common ground (the Step 4 "bypass jumper" becomes the actual design), GPIO27 goes unused, and the low-side/high-side reliability question (along with the exact I2C-breaking failure mode that caused Step 4's multi-hour diagnostic session) is moot rather than solved. Duty-cycle timing moves to Step 8 as an I2C mode-switching firmware task. Updated: `air-quality-monitor.yaml` (removed the GPIO27 switch component), `air-quality-monitor-claude-code-instructions.md` (Hardware Context, GPIO table, Step 6, Step 8), `wiring.md` (GND wiring, schematic, perfboard component list, historical BC547B circuit reference collapsed into a `<details>` block), `README.md`, `ESP32-project-pins.md`, `JCTsh-air-quality-monitor-phase1.md` (BOM row marked superseded). BC547B/BS250 stock remains on hand, unused by this build. **Design decision only at this point — the physical breadboard still had the BC547B and its resistors in place, so Step 6 was not actually closed yet** (Joseph caught this; corrected below).

**Step 6 physically closed, 2026-08-21 12:50 MST.** Joseph removed the BC547B transistor, its 1kΩ base resistor, and its 10kΩ base pull-down resistor from the breadboard entirely (not set aside, as had happened once before during Step 4). Confirmed: SEN55 `GND` is a solid, deliberately-reseated direct connection to common ground (not just the leftover diagnostic-session jumper left in whatever state it was in), and GPIO27 has nothing connected to it. Step 6 is now genuinely closed, hardware matching the design docs. **Step 7 (LiPo polarity check and power validation) next** — now also scoped to include raw dock-detect and battery-divider verification (added to the instructions doc same session), since neither had a dedicated test point before.

**Step 7 blocked, 2026-08-28 — gated on CARD-0198, not just "next" anymore.** The power design Step 7 was written to verify is no longer settled: CARD-0198's investigation found the MCP1700 marginal and produced a regulator swap (Pololu D24V10F3, `power-system-redesign.md`) plus, separately, CARD-0218's Intent/Power-switch redesign (SS12D10 → GPIO27, new BK-1208 power switch) touches the exact same physical wiring Step 7 checks. Both are design-decided but not physically built. Step 7 will resume once CARD-0198's own re-validation plan (see that card's Planned next steps) confirms the new hardware is reliable — Step 7 itself has been updated in `air-quality-monitor-claude-code-instructions.md` for the new part references and a new Intent-switch raw check, but stays blocked until that gate clears.

**Step 7 unblocked, 2026-09-08 — CARD-0198 closed.** Both real operating modes (field: battery+SEN55; docked: TP4056+battery+WiFi/MQTT) confirmed stable. Two real findings from that testing folded directly into Step 7/8's own instructions rather than a separate card, since Build is already in progress:
- **Power switch needs rewiring before Step 7 proceeds** — CARD-0198 measured that the original wiring (switch in the LiPo's own leg only) doesn't actually cut power to the ESP32 while docked, since TP4056 backfeeds the shared node regardless of switch position. New wiring ties LiPo/TP4056 `BAT+` together and puts the switch downstream, gating only the Pololu's `VIN` — restores the switch's real job (forcing a cold restart on demand, docked or not) and, as a side benefit, lets charging continue even when switched off. Full diagram and reasoning: `wiring.md`'s "Inline Power Switch" section. Step 7's own verification now explicitly checks both USB-unplugged and USB-plugged-into-TP4056 conditions, closing the exact gap that let the original wiring's flaw go unnoticed.
- **Step 8's WiFi-enable gating needs a third condition, not just Intent-off + Power-Connected-true.** A real battery-only trial degraded into a self-sustaining brownout loop once voltage sagged to the Pololu's 3.4V floor — the same number the generic low-battery cutoff used, leaving no real margin. Step 8 now requires battery voltage above a new, higher, real-margin threshold before attempting upload, in addition to the existing two conditions. Two open items recorded directly in Step 8's own instructions (not decided here): whether this is a separate check layered on the existing shutdown cutoff or replaces it, and the exact threshold value, which needs a real bench sweep on the rewired hardware rather than a guess.

Step 7 (hardware rewiring + raw-signal checks) is next.

**Step 8 built and first bench-tested 2026-09-09.** `air-quality-monitor.yaml` written in full per the finalized design (below), plus new `components/air-quality-monitor/aqm_logger.h` (adapted from `hiking_logger.h`, `aqm_log_*` prefix). `esphome config` validated clean. Flashed via USB (COM7, plain ESP32 power, no TP4056/battery in the loop — Power Connected reads false throughout this session).

**Real, reproducible bug found and fixed on the very first live test.** A CRC failure on SEN55's I2C read (`sensirion_i2c: CRC invalid`) leaves `sen55_pm25.state` at its last successfully-published value rather than NaN — the original `isnan()`-based "did this cycle's read succeed" check couldn't tell a genuinely fresh reading from a stale leftover from an earlier cycle. Harmless in this bench session (the clock-invalid skip masked it, since NTP never synced with WiFi off) but would silently publish/buffer a stale PM2.5 value under a fresh timestamp once a real connection exists. **Fix:** a new `sen55_last_update_ms` global stamped inside `pm_2_5`'s own `on_value` handler (fires only on an actual successful publish) compared against a `duty_cycle_read_start_ms` stamped before each read request — a reading is only trusted if the former is `>=` the latter, proving a real publish happened after this cycle asked for one. New `sensor_stale` skip-event reason added alongside `clock_invalid`/`nan_sensor`. Compiled and reflashed clean.

**The underlying CRC glitch itself is not fixed, and isn't fully understood** — it recurred on 3 of 4 fully-observed boots this session (not just the first two), at two different points in the code (the interval's mode-switch, and separately `on_boot`'s own Measurement-resume). **Briefly split into its own card (CARD-0252), then folded back in 2026-09-09** per a corrected card-creation policy (Joseph: don't open a new card for every problem found while building/testing an already-open card — track it here instead, unless it's explicitly deferred to a future version) — tracked as an open thread on this card going forward, not a separate one. The new `sensor_stale` skip path hasn't yet been directly observed firing live during a genuine CRC failure (existing captures either predated the fix or happened not to recur) — logically verified by tracing the code, not yet proven catching a live occurrence. **Likely root cause found the same session (see below) — a firmware race condition, not a hardware flake**; not yet fully confirmed since a clean run isn't conclusive given the glitch was already intermittent before the fix too. **Open thread:** confirm no recurrence across a real, sustained test (a full docked charge/upload cycle, or a real hike) — if it does recur, further investigation (wiring re-seat/continuity check, I2C bus scope/logic-analyzer capture) needed to find what the race-condition fix didn't cover.

**Also confirmed working on this first test:** clean boot, no crash/reset-loop; `aqm_logger.h`'s SPIFFS buffering works end-to-end (data written during one boot persisted across a reset, confirmed via `Used: 502 bytes` on a later boot); the boot-time WiFi gate correctly called `wifi.disable()` given Power Connected was false; the 2-min duty-cycle interval fires immediately after boot (not waiting the first full 2 minutes, per ESPHome's `startup_delay: 0s`) and the 40-second SEN55 warm-up timing is exact.

**Real root cause of CARD-0252's CRC glitches found and fixed, 2026-09-09 — likely a race condition, not a hardware flake.** Confirmed directly: the interval's first duty-cycle tick fired only 4.5s after `setup() finished successfully` — far too early for `on_boot`'s own reset-reason-check + 8-blink self-test + bounded MQTT wait to have genuinely completed. Root cause: ESPHome's YAML-level `delay:`/`while:` actions inside `on_boot` are non-blocking automations, not one blocking script — `loop()` (and therefore the interval) can start running *while `on_boot` is still mid-sequence*, letting `on_boot`'s own SEN55 mode-switch commands and the interval's own duty-cycle commands race on the same I2C bus. Fixed by gating the interval's entire SEN55 duty-cycle block behind the existing `boot_sequence_done` flag (previously only used to gate the LED handler) — now a no-op on any tick firing before `on_boot` has genuinely finished.

**Docked-mode test (USB in TP4056, switch off), 2026-09-09 — real end-to-end success, confirmed via the Pi's own dashboard, not just serial logs:**
- WiFi/MQTT connected for real (`IP: 192.168.1.135, reset reason: power-on event`).
- Replay script fired correctly on connect: `"Replaying 19 buffered readings..."`, all 18 of which were `clock_invalid` skip-events accumulated from the earlier no-WiFi bench testing, correctly collapsed and logged, then `"Buffered-data replay complete."`
- **A real, live heartbeat with genuine sensor values:** `"Heartbeat - uptime: 0h 5m, RSSI: -49dBm, PM2.5: 3.3, VOC: 96, NOx: 1, batt: 4.09V"` — confirms the duty-cycle mode-switching + read logic worked correctly at least once post-fix, with no CRC/stale-data issue.
- Node-RED's existing skip-event routing (built for hiking-monitor's CARD-0195) handled air-quality-monitor's skip events correctly with zero changes needed — confirms that function node is genuinely component-agnostic, not hiking-monitor-specific.
- **New, real, not-yet-explained finding:** the connection dropped (`MQTT disconnected`) and the *next* reconnect ~5 minutes later showed reset reason `power-on event` — a full reboot, not just a WiFi drop/reconnect. No live capture spanned that window, so the cause is unknown. Started a continuous background UART capture (COM9) to catch it live if it recurs, rather than guessing.

**Real DNS-reliability finding, 2026-09-09 — found and fixed same session, briefly its own card (CARD-0253) then folded back in per the same corrected policy above.** MQTT kept failing to connect during bench testing despite WiFi itself staying up (`getaddrinfo() returns 202`, 2+ minutes of repeated failures) — root cause: this device (like hiking-monitor) always uses `jctsh.duckdns.org` as its broker, correct for real field use (a cellular hotspot can't reach `pi1.local`) but needlessly routing every connection out to the internet and back for a same-LAN bench test right next to the Pi. A worse version of a DNS blip `minimal-test.yaml`'s own history had already flagged once and deprioritized. **Fix, `air-quality-monitor.yaml`:** confirmed via ESPHome's installed `mqtt_client.cpp` source that the broker hostname is read fresh on every connection attempt (safe to switch at runtime) but TLS-vs-plaintext transport is decided once at the client's first init (not safe to switch) — so the design keeps TLS+port 8883 for both paths and only switches the *hostname*. Confirmed directly in Mosquitto's `mqtt-tls.conf` that `listener 8883` has no bind restriction (reachable via `pi1.local` on the LAN too), and added `skip_cert_cn_check: true` since the cert's CN only covers `jctsh.duckdns.org`. New `wifi_info: ssid:` sensor + `wifi: on_connect:` lambda: `pi1.local` when on `JCTnet1`, `jctsh.duckdns.org` otherwise. Built and compiled clean; not yet verified live on both branches. **Deliberately air-quality-monitor only for now** — hiking-monitor shares the same always-DuckDNS pattern but is already deployed/field-proven, so porting this there waits until this build proves out.

**Voltage-blocked path confirmed live, 2026-09-09 — for real, not faked.** Extended test cycling genuinely drained the battery to 3.68V (real, cumulative depletion from many WiFi+SEN55 duty cycles and repeated reflashes across this session, not a new hardware fault): `"Replay deferred - battery 3.68V below 3.8V upload threshold, waiting for charge"` fired correctly against the real 3.8V threshold. Counts as a real confirmation of that path, no artificial threshold bump needed after all.

**Broker-switch (`pi1.local`/`jctsh.duckdns.org`) confirmed live, 2026-09-09 — real success, both via UART capture and the Pi's own dashboard.** One self-inflicted delay first: forgot to revert the earlier voltage-blocked test's temporary 4.5V threshold before layering the broker-switch feature on top, which silently blocked WiFi from ever trying (gate false) and made it look like the switch wasn't firing — reverted, recompiled, reflashed. With the real 3.8V threshold restored: WiFi connected to JCTnet1, then `"Couldn't resolve IP address for 'pi1.local'"` confirmed the switch away from the DuckDNS default actually took effect, one quick retry (a normal mDNS-just-associated hiccup, not a bug) then `"mqtt cleared Warning flag"` / `"Connected"` — no TLS/cert errors, confirming `skip_cert_cn_check` works correctly. Confirmed reaching the real Pi via the dashboard's own log, not just a local UART artifact.

**Real gap found and fixed, 2026-09-09, before starting the field-simulation test.** This build had **no general low-battery cutoff at all** — `JCTsh-Build-Standards.md` §2.14 point 2 requires one regardless of mode, and this device never got one (unlike hiking-monitor's deep-sleep-based `low_battery_shutdown`). Caught before running the battery-alone simulation with an already-low (3.68V) cell, not after. **Fix:** no deep-sleep/wake-source architecture exists on this device, so the equivalent protective action is skipping the ~63mA Measurement-mode burst entirely below 3.4V (the same documented catastrophic floor as hiking-monitor and this device's own Pololu regulator) — RHT-only idle current is much lower and stays running, so voltage keeps being monitored via the existing 30s ADC poll. Logged once per dip (`critical_battery_alerted` flag), not every 2-min cycle. Compiled; not yet flashed/verified live.

**Real bug in the cutoff fix itself, caught immediately on the first field-simulation attempt, 2026-09-09.** Ran the battery-alone test with the new cutoff in place — buffered readings showed real PM data at `battery_v: 3.09V` and `3.11V`, both well below the 3.4V floor, meaning the cutoff wasn't actually taking effect. Root cause: the `repeat: count: 40` warm-up loop (and everything after it — the read, the freshness check, publish/buffer, and the RHT-only revert) sat at the **same indentation** as the gating `if:` block, making it a sibling rather than nested inside `then:` — only the mode-switch command itself was gated, the entire rest of the sequence ran unconditionally regardless of battery level. Fixed by nesting the full sequence inside the one gate. Compiled; not yet reflashed/reverified.

**Also confirmed working correctly in that same test (the parts that weren't broken):** WiFi correctly stayed disabled the whole time (Power Connected false, no attempts), the 2-min duty-cycle interval fired on schedule (11:06:08, 11:08:08, 11:10:08), and buffering-when-disconnected worked (`"Buffered to flash: ..."` with real sensor data each cycle) — the underlying duty-cycle/buffering mechanism itself is sound, only the new cutoff's own structure was broken.

**Cutoff fix reflashed and retested, 2026-09-09 — structural fix confirmed correct, but still saw sub-3.4V buffered readings (3.08V, 3.14V) with no "Critical battery" Alert logged.** Different explanation than the earlier structural bug: no Alert means the gate check itself (taken right before each burst starts) is reading *above* 3.4V — the voltage is genuinely **sagging under load** during the 40s Measurement-mode burst, dropping from a passing resting value down to ~3.08-3.14V by the time the read completes. This is real LiPo physics on a partially-depleted cell (rising internal resistance, `JCTsh-Build-Standards.md` §2.14 point 9), not a code bug — and it's the same accepted limitation every "check before the burst, not continuously during" pattern in this codebase already has (hiking-monitor's equivalent check can't catch an in-burst sag either). **Paused field-simulation testing and redocked** rather than keep cycling an already-marginal cell through repeated high-current bursts — the sag magnitude (~0.3-0.4V) is large enough to warrant giving the battery a real charge before continuing, not pushing further right now.

**Upload-safe threshold revised 3.8V → 3.5V, 2026-09-09 — a real design correction, not just a number tweak.** Joseph caught the actual flaw while we were fighting the gate during testing: CARD-0198's brownout finding that motivated the original 3.8V margin came from a *deliberate battery-alone* WiFi+MQTT+SEN55 stress trial — a scenario the other two gate conditions (Intent off + Power Connected) already structurally prevent from ever occurring in the real firmware. Every *docked* trial CARD-0198 actually ran (Stages 1-3, TP4056 supplying the burst current, not the battery) passed clean regardless of battery depletion — because TP4056's own ~4V charging output, not the battery, is what powers the burst when docked (confirmed directly: *"the inline Power Switch does NOT isolate the shared VIN/BAT+ node from TP4056's own USB-fed charge output... Pololu VIN reads ~4V with the switch OFF whenever USB is in TP4056"*). The 3.8V margin was solving a problem the docked case doesn't actually have. **Revised to 3.5V** — a small cushion above the confirmed-catastrophic 3.4V floor, kept specifically for the one untested case: a weak/solar charger that might not supply burst current as robustly as the USB sources CARD-0198's trials actually used. Not reduced to 3.4V flat (no margin at all) given that real gap in test coverage. All four threshold references + associated log/comment text updated consistently. Compiled; not yet reflashed/reverified.

**Still not tested:** the field-simulation itself; a full bounded-attempt-window/15-min-retry cycle (currently mid-setup — an isolated unreachable-broker override, not touching shared Mosquitto, deliberately scoped to just this device); and the `jctsh.duckdns.org` half of the broker switch (only the `pi1.local`/home branch exercised live so far).

**Step 8 design finalized 2026-09-09 — full detail in `air-quality-monitor-claude-code-instructions.md` v1.3, not duplicated here.** Worked through the mechanics before writing any code: SEN55 duty-cycle mode-switching (RHT-only ↔ Measurement, confirmed `0x0037`/`0x0021` I2C commands directly from ESPHome's installed `sen5x.cpp` source), the boot-time WiFi gate (a real finding: this device's `on_boot` is priority -100, which runs *after* WiFi's own setup — unlike hiking-monitor's priority-600 block, this device can call `wifi.disable()` directly in `on_boot` rather than deferring to the interval tick), the bounded-attempt/15min-retry state machine, a new LED diagnostic scheme (Blue dedicated to networking status — voltage-blocked and attempt-in-progress/connected/gave-up patterns, with precise boot-relative timing worked out so Joseph knows when to watch), and the MQTT logging plan (three of the four new LED states buffer-and-replay since no connection exists yet when they fire; only "connected" logs live). Not yet written to `air-quality-monitor.yaml` — design only.

**Power switch rewired and verified, 2026-09-08.** Physically rewired to the new topology (LiPo `BAT+`/TP4056 `BAT+` tied together on the switch's input side; switch output feeds only the Pololu `VIN`). All key checks passed:
- Switch off, USB unplugged: 0V at Pololu `VIN` (baseline, unchanged).
- Switch off, USB in TP4056: **0V at Pololu `VIN`** — the actual fix, confirmed working (this read ~4V under the old wiring).
- Switch off, USB in TP4056: TP4056's charge LED lit, confirming charging now works independent of switch position (the side benefit).
- Switch on, USB in TP4056: Pololu `VOUT` = 3.3V, clean.
- Switch on, USB unplugged: `VOUT` initially read 3.18V — not a wiring problem, traced to the battery itself needing a real charge. **Real, useful finding along the way:** the earlier "3.9V" reading was taken while TP4056 was actively charging, which reads artificially high (charging current elevates terminal voltage against the battery's own internal resistance) — the battery's true, load-bearing voltage was well below that. Written into Step 8's bench-sweep instructions above: any future voltage check (bench sweep or runtime firmware) must be taken with the charger disconnected, not mid-charge. Battery back on the charger; `VOUT`-on-battery-alone re-check pending a real charge before this specific item is fully closed.
- **Battery-divider R1 move: verified, 2026-09-08.** R1's top leg moved off the 3.3V placeholder onto the real post-switch node. Direct multimeter check (Power Switch on): GPIO34 (pin 5, divider midpoint) read 2V against 4V at LiPo+ — exact 2:1 match, confirming the 100kΩ/100kΩ divider is wired correctly.
- **Dock-detect raw check: verified, 2026-09-08.** Added a `binary_sensor` for GPIO32 (pin 7) to `minimal-test.yaml` (wasn't present before), reflashed. Verified directly with a multimeter: GPIO32 (pin 7) read ~0V with USB unplugged from TP4056 (LOW/field), and a real positive voltage with USB plugged in (HIGH/docked) — matches the 68kΩ/100kΩ divider design exactly.
- **Intent-switch raw check: verified, 2026-09-08.** Same multimeter approach — GPIO27 (pin 11): 19mV with Intent on (switch closed, grounded), 3.2V with Intent off (switch open, pulled up) — both match expectations for `INPUT_PULLUP`/inverted logic.
- **Correction, same session:** both raw checks above were also independently confirmed via the debug UART log itself (`Dock detect: LOW (field mode)` / `Dock detect: HIGH (docked/charging)` / `Intent switch: ON (closed)` all genuinely captured) — the earlier claim in this card that the `binary_sensor`→`on_state`→`logger.log` path "never actually produced UART output" was wrong. Real cause: a stray non-text byte landed in the capture log file at some point during the session, which made plain `grep` silently treat the whole file as binary and report zero matches with no error — a bug in this session's own diagnostic tooling, not an ESPHome/firmware gap. `grep -a` (force text mode) surfaced the real log lines that had been there all along.
- **Final `VOUT`-on-battery-alone recheck, 2026-09-08 — done, but surfaces a real, separate finding.** Switch on, USB fully unplugged: `VOUT` = **3.2V** — essentially unchanged from the pre-charge 3.18V reading, not the clean 3.3V the docked case (`VOUT` = 3.3V, USB in TP4056) already confirmed. Battery terminal itself (LiPo+, switch off, USB unplugged): **3.8V** resting. **This undercuts the original "just needs a real charge" explanation** — TP4056's green LED (charge-complete) was lit before this test, yet 3.8V resting is well short of a genuine full charge (~4.2V for a 1S LiPo), and `VOUT` barely moved from the earlier reading despite the supposed charge. Two live possibilities, not yet distinguished: (a) the TP4056 module's charge-termination is tripping early / the green LED isn't a reliable full-charge indicator for this specific battery+module pairing, or (b) the cell itself has degraded capacity and can't actually reach a normal full-charge voltage. **3.2V vs. 3.3V at `VOUT` is plausibly within the Pololu D24V10F3's normal regulation tolerance at this input level** (not itself alarming) — the real open question is the battery/charger behavior underneath it, not the regulator. Step 7's own literal ask (get a real `VOUT`-on-battery-alone number) is satisfied by this reading; the charge-state anomaly is a new, separate thread — not folding it into Step 7's own scope silently. **Disposition, Joseph's call 2026-09-08: note it and move on** — not opening a new investigation card off a single reading. Revisit only if it recurs (e.g. a future full-charge cycle also tops out well short of 4.2V) or actually blocks Step 8's own bench sweep.

**Follow-up, 2026-09-09 — largely resolves the anomaly.** Battery left on the charger overnight; morning resting-voltage check: **4.05V** — close to a genuine full charge, well above the earlier 3.8V. Points toward the original 2026-09-08 reading being an interrupted/short charge cycle (the green LED likely lit correctly, just not on a full-length charge yet at that moment) rather than cell degradation or a real TP4056 fault. Not fully conclusive from one data point, but consistent with "note it and move on" being the right call. **Directly relevant to Step 8:** true full-charge resting voltage (~4.05V) sits only ~0.25V above the provisional 3.8V upload-gate threshold — a real, useful data point for Step 8's own bench sweep, not just a closed side-question.

**`VOUT` re-check at this higher input, 2026-09-09 — confirms the regulator, not a fault.** Switch on, fresh boot, battery at ~4.05V: `VOUT` = **3.3V clean** — up from 3.2V at the earlier 3.8V input. Tracks input voltage within normal Pololu D24V10F3 tolerance, exactly as expected for a healthy buck-boost regulator; the earlier 3.2V reading is now fully explained by the lower input at that time, not a wiring or regulator issue. Step 7's `VOUT` question is closed with no remaining doubt.

**Step 7 fully closed, 2026-09-08.** Every item verified: power-switch rewiring (both USB conditions), battery-divider R1 move, dock-detect raw check, Intent-switch raw check (all also confirmed via debug UART), and this final `VOUT`-on-battery-alone reading. **Step 8 (WiFi-enable gating firmware, including the provisional 3.8V threshold and the periodic-recheck pattern from CARD-0224) is next.**

**Bounded-attempt/15-min-retry state machine (item 4) — real bug found and fixed, 2026-09-09.** The `wifi.enable`/`wifi.disable` action block only called `wifi.disable:` when the gate itself went false — it had no branch for "gate true, but the attempt just timed out and MQTT still isn't connected" (the 15-min quiet/backoff state). That state fell through to the `else` with no matching inner condition, so nothing ever called `wifi.disable:` — WiFi stayed enabled and kept silently retrying the AP forever via ESPHome's own built-in reconnect logic, completely defeating the bounded-attempt design (confirmed externally: a ping to the device's LAN IP got a live reply the whole time it should have been off). Fixed by also disabling whenever not actively attempting and not connected. Diagnostic bookkeeping (`wifi_attempt_in_progress`/`wifi_attempt_start_ms`/`wifi_last_attempt_end_ms`) was actually correct the whole time — only the actuation was broken.

**Second, unrelated real bug found while verifying the fix above: ESPHome's own `mqtt:` component has a built-in `reboot_timeout` (default 15min, hardcoded fallback 5min) that force-reboots the whole device if it can't connect within that window** — confirmed directly in `mqtt_client.cpp`'s `loop()` (`"Can't connect; restarting"`). This directly fights Step 8's own bounded-retry design, which deliberately keeps MQTT disconnected during a backoff, and nothing in this build's own code ever calls MQTT's `enable()` again to reset that timer once boot's own attempt ends. Live-observed: a full device reboot fired at 12:29:39, ~14m40s after boot, right as the 15-min backoff was about to complete — looked at first like the retry itself, but `start_ms`/`last_end_ms` resetting to near-zero gave it away as a fresh boot, not a state-machine tick. **This almost certainly also explains the earlier "New, real, not-yet-explained finding" above (2026-09-09, the `power-on event` reboot ~5 minutes after a dropped connection)** — that gap matches this same mechanism's hardcoded 5-minute fallback default exactly. Fixed with `reboot_timeout: 0s` in the `mqtt:` block, since Step 8's own state machine already owns this responsibility.

**Item 4 fully verified live after both fixes, 2026-09-09.** Full cycle observed end-to-end on real hardware against a deliberately-unreachable isolated test broker (TEST-NET-1, this device only, shared Mosquitto untouched): boot-time attempt → 2-min timeout → WiFi genuinely disabled (externally confirmed via ping) → 15-minute quiet backoff with zero reboots → genuine retry at the 15-min mark (`wifi_attempt_in_progress` flipped true, fresh `wifi_attempt_start_ms`) → WiFi re-scanned and reconnected to JCTnet1 within ~4 seconds of the retry firing.

**Item 5 (DuckDNS/hotspot branch) verified live, 2026-09-09.** Temporarily reflashed with JCTnet1 removed from `wifi: networks:` (hotspot only, isolated bench test, reverted after) to force the `else` branch of the SSID-based broker switch. Device joined "JCT Hotspot," `wifi: on_connect:` correctly selected `jctsh.duckdns.org`, MQTT connected on the second attempt (one normal DNS-not-yet-resolved retry), and a real live reading published successfully through the DuckDNS/hotspot path (confirmed on the Pi's own dashboard). Both branches of the broker switch (CARD-0253's original scope) are now fully verified live, not just the `pi1.local`/JCTnet1 branch. Reverted the temporary hotspot-only network list, the temporary unreachable-broker override, and the earlier temporary 4.5V threshold bump back to the real dual-network/3.5V/real-broker configuration; recompiled and reflashed; confirmed a clean real boot connecting to `pi1.local` over JCTnet1.

**Disposition, end of this build-and-test cycle, 2026-09-09 (per the impromptu-cards rule — fix/defer/accept decided now, not per-item as found):**
- Both real bugs above (WiFi disable/enable actuation, MQTT `reboot_timeout` conflict) — **fixed and verified live**, not deferred.
- SEN55 CRC-glitch open thread (originally CARD-0252) — **accepted as resolved for now, note and move on.** No recurrence observed across this entire session's many flash/reboot/duty-cycle test cycles since the race-condition fix, including the full multi-hour retry-cycle and hotspot tests just completed. Not a fully sustained multi-day/field test, so treated as strong-but-not-final evidence rather than formally closed — revisit only if it recurs.
- Field-simulation test (paused earlier for battery-sag/voltage-margin concerns) — **deferred**, resumes once the battery has had an real, undisturbed full charge (last confirmed ~4.05V resting after an overnight charge, but this session's own repeated cycling since then has drawn it back down).
- Porting the `pi1.local`/DuckDNS SSID-based broker-switch pattern to hiking-monitor — **deferred**, out of scope for this build; that device is already deployed/field-proven and should only inherit this pattern once air-quality-monitor itself has proven out further (unchanged from CARD-0253's original scoping).

**Step 8 status:** design, implementation, and the full agreed bench-test sequence (items 1-5) are complete and verified live. Remaining before Step 8 can close: the full field-simulation test (deferred above, battery-gated) and, per its own done-when, a longer sustained-operation window with no CRC recurrence.

**LiPo cell replaced, 2026-09-09 — resolves the deferred field-simulation blocker.** The cell tested throughout this session finally collapsed under a real battery-alone boot: resting 3.96V, but the ADC read **2.72V** (`reset_reason: brownout`, confirmed via the dashboard) moments later once WiFi/SEN55 startup current was drawn on battery alone — a genuine over-discharge event, not a code issue (the three-condition gate correctly held WiFi off the whole time given the low reading, exactly as designed). Replaced with a fresh cell, resting **4.16V**. This also retroactively confirms Joseph's earlier suspicion this session ("these LiPo batteries don't seem to work well") was about a real degraded cell, not a design or wiring problem.

**Field-simulation test done, 2026-09-09 — the deferred item above, now complete.** Full cycle with the new battery: undocked → three consecutive duty cycles on battery alone (each correctly buffered as a `clock_invalid` skip-event, expected with WiFi off) → redocked → gate flipped true → WiFi/MQTT reconnected. Replay took two attempts, both informative: the first (immediately on connect) hit a real transient voltage dip (3.33V, recovered to 3.82V within 2 minutes — normal LiPo-under-load noise, §2.14 point 9) and correctly deferred; the second, via the CARD-0224 periodic recheck, succeeded once voltage settled (`"Replaying 50 buffered readings..."` → `"Buffered-data replay complete."`, confirmed on the Pi's dashboard). A genuine demonstration of the retry-on-recovery design working, not just the simple happy-path replay verified earlier.

**Real bug found and fixed, surfaced by that same test: the Intent switch never actually gated data collection, contradicting `wiring.md`'s own documented design.** `wiring.md`'s Intent Switch Wiring section states plainly that Intent ON means "actively collecting field data" — but a full grep of `air-quality-monitor.yaml` showed `intent_switch` referenced only in the WiFi-gate logic, never in the SEN55 duty-cycle block. The device was duty-cycling and buffering unconditionally regardless of Intent, meaning it would burn battery running full Measurement-mode bursts even sitting idle in a backpack with Intent off. **Fixed:** the duty-cycle block's gating condition now also requires `id(intent_switch).state` (Intent ON). Verified live both directions: Intent off → no `DUTY CYCLE` line at all on the next tick; Intent on → `DUTY CYCLE: switching to Measurement mode` fires and a real reading gets buffered.

**Second real bug found and fixed, same test: a single noisy voltage sample was tearing down an already-established, working WiFi/MQTT connection.** While docked and connected, one momentary ADC reading (3.37V, recovered to 3.54V forty seconds later) made `wifi_gate_ok` false for one tick — the disable logic treated that identically to a real reason to disconnect, and genuinely dropped a working link (confirmed live: `"Disconnected ssid='JCTnet1' ... reason='Association Leave'"`) even though nothing was actually wrong and TP4056 was supplying power the whole time. **Fixed:** the voltage condition now only gates whether to *start* a new connection attempt; an already-connected link is only torn down by a real session-end (Intent switching on) or undock (Power disconnecting) — not a transient voltage blip. The existing 3.4V general low-battery cutoff and replay-defer checks already protect the actually-risky operations (the Measurement-mode current burst, and uploading), so this doesn't weaken any real safety margin.

**Verification note on the hysteresis fix:** Intent-gating was fully verified live in both directions. The voltage-hysteresis fix could not be cleanly re-triggered the same way — forcing it via a temporarily-impossible voltage threshold failed, because the interval's own very-early tick (~4s after boot) disabled WiFi before boot's own connection attempt could ever complete, so "already connected" was never reached under that test setup. More fundamentally, with both fixes in place the original repro conditions (a voltage dip during Measurement-mode current draw while still connected) can no longer coexist by design — Measurement-mode now requires Intent on, and Intent on now always forces a disconnect regardless of voltage. Accepted as verified by code correctness and the clarity of the original diagnosis, per Joseph's call, rather than built out a more invasive one-off test rig.

**Real, separate finding during final re-verification: a cold-boot voltage-sag boot failure, distinct from the earlier brownout event.** After reflashing and redocking, the device showed the identical "powered, red LED on, ~3.2V at the ESP32, zero UART output" signature as the earlier old-battery brownout — but this time with the healthy new battery (confirmed 4.0V resting, power off). A retry (power-cycling the switch) booted successfully, with the boot-time ADC reading **3.49V** — a real, if narrower, sag under the simultaneous SEN55+WiFi cold-boot current spike compared to steady-state operation, not a hardware fault or bad cell. Gate correctly read 0 that boot (3.49V just under the 3.5V threshold) rather than falsely proceeding. Worth being aware of as a real characteristic of this device's cold-boot inrush, not something to fix — the existing gate logic already handles it correctly by holding off until voltage recovers.

**Diagnostic logging left in place, Joseph's call 2026-09-09:** the two `ESP_LOGW("WifiState", ...)` lines added earlier to debug the retry-cycle state machine (fires every 2min at WARN level) are kept for now rather than stripped — they've independently caught two other real findings today (the `reboot_timeout` conflict, the hysteresis fix's boot-interference issue). Candidate for removal once Step 8 has run unattended long enough that this level of visibility isn't needed. Noted inline in the YAML.

**Correction to the cold-boot voltage-sag finding above — this is the resolution to a long-standing loose end from 2026-08-28, not a new, separately-accepted characteristic.** Joseph connected it: the 2026-08-28 capacitor-value investigation (10µF ceramic regression → reverted to 4.7µF → still didn't restore the earlier clean 4/4 pass → session paused with an explicit "do not assume Stage 0's PASS still holds without re-verifying it fresh next session... a full re-seat of the entire ESP32-3V3-pin row" note) was never actually followed up on in any later session. Today's "powered, red LED on, zero UART output" boot failures are the same signature as that unresolved thread, not a new issue. **Fixed by finally doing the suggested re-seat** of the crowded ESP32-3V3-pin row (ESP32 pin, Pololu VOUT, SEN55 adapter VIN, both bulk caps — 470µF electrolytic + 4.7µF ceramic, `wiring.md`'s documented design confirmed still accurate and unchanged). **Re-verified against this project's own established bar for exactly this kind of finding (CARD-0198's Stage 0 pattern): 4 of 4 consecutive clean power-cycle boots**, each confirmed both via the debug UART log and the boot LED sequence, with `battery_v` readings of 3.28V/3.53V/3.39V/3.32V during boot (real cold-boot sag, varying cycle to cycle, but no longer causing a silent failure) — a real, positive result closing out a puzzle that had sat unresolved for nearly two weeks.

**Disposition, end of this second build-and-test round, 2026-09-09:**
- LiPo replacement, field-simulation test, Intent-switch gating fix, and voltage-disconnect hysteresis fix — all **done and verified live** (hysteresis fix verified by code correctness per the note above, not a live repro).
- Cold-boot silent-boot-failure finding — **resolved**, not just accepted: a physical re-seat of the ESP32-3V3-pin row fixed a marginal connection left over from 2026-08-28's unresolved investigation, verified via 4/4 consecutive clean boots.
- SEN55 CRC-glitch sustained-test confirmation — still the one open, non-blocking watch item, unchanged from the disposition above.

**Step 8 is now functionally complete.** Design, implementation, the full bench-test sequence (items 1-5), the field-simulation test, and two additional real bugs found during that same test are all done and verified live, plus a long-standing hardware loose end from 2026-08-28 finally closed. The only remaining open thread is the long-horizon SEN55 CRC-recurrence watch, which doesn't block considering Step 8 closed.

**Step 9 (perfboard transfer) session, 2026-09-14 — continuity testing done, one real firmware bug surfaced, full checklist not yet complete.** Full detail in `components/air-quality-monitor/perfboard-layout.md` (new file, continuity-check table + post-continuity power-on checklist, matching hiking-monitor's own `perfboard-layout.md` convention) — summarized here:
- **All 30 continuity checks done: 28 clean passes, 2 deferred** (resistance-mode divider readings — hand-probe repeatability issue on small leads, not a real fault; underlying wiring/part-value already confirmed by continuity + color-band checks). **7 missing solder bridges found and fixed** along the way.
- **Two real, pre-existing doc bugs found and fixed during continuity testing:** (1) `ESP32-project-pins.md`'s pin 18 was documented (2026-08-19 note) as confirmed-GND from the silkscreen — bench-tested not actually continuous to ground on two separate boards with identical markings; not used in this build (the perfboard's GND rail is fed from pin 38 only), so moot for this build, but the doc's stale claim is corrected. (2) `ESP32-project-pins.md` carried wire-color annotations that conflicted with `wiring.md`'s own as-built colors (GPIO34, GPIO32) — resolved by stripping all wire colors from `ESP32-project-pins.md` and making `wiring.md` the sole authoritative as-built source, per Joseph's explicit call.
- **Post-continuity power-on checks 1-3 done, all passed:** switch-off isolation (both USB-unplugged and USB-in-TP4056 halves — confirms CARD-0198's power-switch rewiring still holds on the perfboard build), switch-on `VOUT` regulation (clean 3.3V), TP4056 charge LED still active with switch off. Bonus: firmware's own logged `battery_v` (4.12V) matched a direct multimeter reading almost exactly, incidentally also satisfying check 6 (battery divider sanity).
- **Check 4 (dock detect) — docked half confirmed indirectly (WiFi/MQTT connected, `gate=1` logged, consistent with dock-detect HIGH). Undocked half surfaced a real Step 8 firmware bug, root-caused and fixed same session, not a wiring issue.** With Intent switch confirmed OFF and dock-detect OFF (battery-only, undocked), a live debug-UART capture showed a repeating `jctsh.duckdns.org` resolve-failure / `WiFi disconnected` / `Error resolving broker IP address: -6` cycle. **Traced the actual code (`air-quality-monitor.yaml` lines 709-798) rather than assuming the gate was broken — it wasn't.** `wifi.disable()` correctly fires every 2-min tick given the confirmed Intent-off + Power-disconnected state (verified by tracing the exact condition, not just reading the design notes); the captured log itself confirmed this — all 9 lines were `[W][mqtt:...]`, zero `[wifi:...]` lines of any kind, meaning the radio was never actually re-enabled. **Real cause: ESPHome's `mqtt:` component has its own independent reconnect logic**, retrying (and cleanly failing DNS resolution) on its own schedule regardless of the radio being correctly disabled. **Fix:** mirrored every `wifi.enable`/`wifi.disable` call in that block with a matching `mqtt.enable`/`mqtt.disable` (confirmed as real ESPHome actions via the installed package source, `esphome/components/mqtt/__init__.py`) — `esphome config` validated clean. **Not yet flashed or live-verified.**
- **Checks 5-7 (Intent switch, battery-divider live sanity check, full boot) not yet started; the check-4 fix not yet flashed/verified live** — session paused here for the day.

**Session resumed 2026-09-16 — check 4's undocked-half fix flashed and live-verified.** `air-quality-monitor.yaml` synced from the repo into `C:\esphome\air-quality-monitor\` (was stale, predated the 2026-09-14 fix), config-validated clean, flashed via USB. Found and fixed a real port-identification error before flashing: two CP210x adapters are connected (COM7, COM9), and neither port history nor a visual/physical check reliably told them apart — a read-only `esptool chip_id` query is what actually confirmed COM7 is the ESP32's own programming port (COM9 is CARD-0205's debug-only UART adapter). Retested undocked/battery-only per `perfboard-layout.md`'s own check-4 conditions (Intent off, TP4056 USB out, flash-USB also out so the board runs on battery through the Power switch, debug UART watched via `esphome logs --device COM9`) — confirmed `gate=0` held clean across two full 2-minute duty-cycle ticks with no MQTT resolve-error recurrence, versus the repeating cycle seen before the fix. Full verification detail in `components/air-quality-monitor/perfboard-layout.md`'s check-4 entry, not duplicated here. **Checks 5-7 still not started** — that's next.

**Same session, continued — checks 5-7 all closed out, despite the debug UART adapter developing a real, unresolved fault partway through.** Check 5 (Intent switch) ON case: confirmed correctly triggers `DUTY CYCLE: switching to Measurement mode` via COM9. Right after, the debug adapter's RXD line went permanently dark — systematically isolated (stdout buffering, stale process handle, USB re-enumeration, the adapter's own USB-side state, and the GPIO17/GND wiring itself, the last one re-confirmed twice by Joseph) down to either a genuine fault in the adapter module or a connection internal to it, not this project's own wiring. No spare adapter on hand to isolate further. Pivoted to the docked/MQTT dashboard path for everything else, since it doesn't depend on the debug UART: check 6 (battery divider sanity) confirmed clean (4.02V multimeter vs. 4.04V logged); check 7 (full boot) confirmed via a clean dock connect, buffered-replay, and a sane 5-min heartbeat.

**Check 5's OFF case closed the same session, via a real live test, not left parked.** Intent switched ON while docked — this immediately dropped the MQTT connection (a real, previously-undocumented design fact found live: Intent-on is treated as a genuine session-start regardless of dock state). Confirmed via the Environmental Data Sheet directly (`action=export` query against the shared Apps Script) that two real readings landed exactly inside the Intent-on window (`2026-09-16T18:28:56Z`/`18:30:56Z`, PM2.5 1.9/2.0 µg/m³), while every heartbeat before and after that window (Intent off) consistently showed `PM2.5: unavailable`. Confirms the gate works both directions on this perfboard build. **Step 9's checklist is now fully complete.** Full detail in `components/air-quality-monitor/perfboard-layout.md`'s check 5-7 entries.

**Enclosure CAD complete, 2026-09-16 (Joseph) — same session, once the bench phase above unblocked it.** Built in Tinkercad starting from hiking-monitor's own proven enclosure (Section 10's starting-point decision, above), height adjusted for this device's own component stack. Every open question from `air-quality-monitor-enclosure-plan.md`'s Section 10 resolved live in CAD, including reversing the earlier "no vent insert needed" call — a vent insert is included after all, for a little extra passive airflow alongside SEN55's own sealed housing. STL exports committed (`components/air-quality-monitor/enclosure/`); printing trip to Xerocraft scheduled. Full detail in the enclosure plan doc itself, not duplicated here.

**Also resolved in passing, not a real bug:** the earlier note about the Pi's raw `jctsh.log` "lagging behind" the dashboard was a misdiagnosis — the dashboard renders live in-memory state including a heartbeat group that hasn't flushed to the file yet (flushes on a state change, a different message type, or 15 minutes of age, whichever comes first, per CARD-0069's original design). Not a bug; know which of the two you're checking and why they can differ.


**Carry-over from hiking-monitor's CARD-0226, 2026-09-24 (Joseph: "note this for the aqm") -- apply before this device is first used for real field runs.** A real hiking-monitor hike lost ~80% of its replayed readings (121 replayed, 23 in the Sheet) and, because the device truncates its SPIFFS log immediately after the publish loop with no delivery confirmation, the missing readings were unrecoverable. Root cause was downstream, not the device (Apps Script's Environmental Data write had no lock and Node-RED counted every reply as success) -- **fixed 2026-09-24 and verified end to end (121/121 rows landing, was 24/121); the AQM shares that same write path, so it benefits with no AQM change.** What the AQM still has of the same design: `attempt_aqm_replay` calls `aqm_log_clear()` right after the replay loop (`air-quality-monitor.yaml`, ~line 563). When AQM field/replay use begins, port hiking-monitor's fix: (1) a `restore_value: true` `aqm_log_replayed` flag set after replay instead of clearing, with replay gated on `!aqm_log_replayed`; (2) clear the log only when the next field run starts (Intent switch ON), and only if already replayed (an unreplayed log is kept and appended to); (3) optionally an exposed "Replay" button that clears the flag and re-runs `attempt_aqm_replay` -- safe to repeat, Apps Script rejects an exact (ts, source) duplicate. **The AQM's own QoS 0->1 change on the replay stream (committed 2026-09-22, never flashed) was reverted 2026-09-24 (Joseph: "revert it and note it"):** the end-to-end test ruled QoS 0 out as the cause of hiking-monitor's loss (device->broker was fine; the loss was the Apps Script write path), QoS 1 can't tell the log-clear what actually arrived, and it makes the ESP32 hold every unacked message during a 50 ms burst that already needed watchdog fixes (CARD-0211). `air-quality-monitor.yaml` is back to QoS 0 with a comment saying why; config validates. The AQM's next flash should carry only the log-retention port above. The `mqtt.disable`/`mqtt.enable` pairing with `wifi.disable`/`wifi.enable` (CARD-0226's other fix) originated on this device and is already present (~lines 812-822).

**Log-retention port built 2026-09-24 (Joseph: "do the port", MQTT command topic chosen over an HA button -- `discovery: false` stays, that decision was about sensor state, not maintenance entities).** `air-quality-monitor.yaml` (commit `7fee0b6`, ESPHome 2026.4.5, config_hash 0x21610a5f, compiled, config validates, QoS stays 0): a `restore_value` `aqm_log_replayed` flag replaces the post-replay `aqm_log_clear()`; replay is gated on it; the log clears only when the Intent switch turns ON and only if already replayed; publishing anything to `jctsh/components/air-quality-monitor/command/replay` while connected re-sends the retained log. **Flashed OTA 2026-09-25 10:37 MST** (Joseph booted the AQM after finishing the enclosure; it came online at 192.168.1.134 and the flash went in within its ~2 min WiFi window; it rebooted with `Reboot request from esphome.ota` and reconnected on the new build). IP 192.168.1.134 is now DHCP-reserved (Joseph) and recorded in `network/jctsh-network.md`. Not yet exercised on a real field run -- the Saturday 2026-09-26 hike (first with both hiking-monitor and the AQM) is its first test: the replayed flag, the clear at Intent-switch ON, and the `command/replay` topic. Flashing needs the device docked with Intent off and battery >= 3.5 V so its short WiFi window opens.

**Done when (written 2026-09-26, Joseph: "yes, write the done-when on the card").** One real field run -- a hike carried out with the AQM, not a bench run -- delivers its readings to the Environmental Data Sheet with correct timestamps after the dock replay, verified against the Sheet itself (`action=export`), including a run that starts from a cold boot with no Wi-Fi window. That closes the still-untested pieces of the log-retention port (the `aqm_log_replayed` flag, the clear at Intent-ON, the `command/replay` topic) and depends on CARD-0343 being verified first. Not required to close: CARD-0343's unresolved-time options (3, 4, 6) and the dead debug-UART adapter (the docked MQTT path covers everything it was used for). The 2026-09-26 hike did **not** satisfy this (98 `clock_invalid` skips, zero readings -- CARD-0343).
---

### CARD-0013 · [idea] [van-sensors] Van sensors (indoor + outdoor)
**Status:** Planning

**Planning doc:** `components/van-sensors/JCTsh-van-sensor-phase1.md`  
**Notes:** Two ESP32 ESPHome nodes for the Pleasure-Way ProMaster 3500 van. Outdoor: BME280 + LTR-390 UV + SEN55 air quality, LiPo powered. Indoor: BME280 + SCD40 CO2 + MQ-6 propane, 12V coach power. Both log to onboard flash during travel, sync to home MQTT on WiFi reconnect (home or Pixel hotspot). DS3231 RTC for accurate timestamps during extended trips. GPS correlation via GPSLogger on Pixel. Phase 1 complete — ready for Phase 2 (hardware selection, inventory scan, open questions resolved).

**Outdoor node rescoped 2026-08-27, interviewed at length — a concrete, narrower starting variant, not the original full sensor suite.** Raised while discussing hiking-monitor's own real-world lessons and whether it could double-duty as a camp monitor. Clarified through the interview: this is genuinely a **separate physical device** from hiking-monitor (similar design lineage, hiking-monitor stays dedicated to hiking) — effectively this card's own outdoor node, just scoped down and informed by everything learned building/running hiking-monitor.

**Scope for this first build, narrower than Phase 1's original outdoor-node vision:**
- **Sensors: BME280 (temp/humidity) + BH1750 (illuminance)** — not the fuller LTR-390/SEN55 suite Phase 1 originally specified (those stay documented above as a possible future expansion, not dropped). BH1750 added 2026-08-27, after initially being set aside for lacking a clear use case: **real driving purpose is estimating available sunlight for the van's own solar panels** — checked whether the Firefly/eRVin coach system already provides this more directly (it doesn't track solar panel usage, confirmed by Joseph, ruling that out) — so this lux reading is the *only* available signal for that purpose, not a rough stand-in for something more precise that already exists. Caveat worth keeping in mind: it's mounted at the mirror, not on the roof where the actual panels sit, and lux (visible-light response) isn't the same physical quantity as panel-relevant irradiance — a useful proxy for "sunny vs. shaded," not a precise charging measurement.
- **Use pattern: dedicated to camp/van duty, not shared with hiking.** Hangs on the van's **exterior** mirror for the duration of a campsite stay — overnight up to 1-2 weeks. A trip either uses it for this, or hiking-monitor goes hiking; never both roles on one device in one session.
- **Cadence: much longer than hiking's 2-minute reads** — matches Phase 1's own original 10-minute reasoning (camp conditions change slowly). No shared-device mode-switching complexity to design around, since this is a dedicated single-purpose device — the interval is just fixed for what it is.
- **DS3231 RTC confirmed, matching Phase 1's original plan** — already on hand (4 spares, Bin A5, only 1 allocated to bedside-clock), zero added cost. Keeps buffered readings accurately timestamped through 1-2 weeks of no connectivity regardless of how often the Pixel hotspot actually gets turned on, rather than depending on a resync habit.
- **Hotspot sync cadence: no fixed schedule, "whenever convenient."** With the RTC handling timekeeping and storage nowhere near a constraint at this duration (~2,016 readings / ~400KB over 2 weeks at a 10-min interval, well under the 2MB flash partition), there's no technical reason to sync on any particular schedule — connect the hotspot as often or as rarely as Joseph wants to actually see the data mid-trip.

**Power — real pivot found during the interview, changes the whole engineering target.** Original assumption (matching Phase 1's own outdoor-node plan) was LiPo + solar, same battery pattern as hiking-monitor — but sustaining unattended operation for 1-2 weeks on battery alone (even with solar) is a real, hard problem, and would have made CARD-0201's not-yet-built true-deep-sleep-between-samples work load-bearing just to make this device viable. **Joseph's reframing: run it continuously on USB power from the van's own house battery (coach power) instead** — the same "12V coach power, always on" pattern Phase 1's *indoor* node already uses, just applied to this exterior-mounted sensor. This sidesteps the entire battery-duration/deep-sleep/recharge-routine question outright — no LiPo management, no charge cycles, nothing to run out.

**This reframes the real remaining engineering challenge as physical installation, not firmware/power-budget:**
1. **Weatherproof cable routing** — getting a power cable from the van's interior 12V/house-battery system out to an exterior mirror-mounted sensor, without it being impractical to route (Joseph's own words: "it's a problem to string a USB charging cable in to the interior of the vehicle"). Worth checking whether the Pleasure-Way already has any exterior 12V/USB accessory point (some vans have one near the mirrors for dash-cams) before assuming a new pass-through needs to be installed.
2. **Weatherproof cable entry on the enclosure itself** — unlike hiking-monitor (always battery/solar-powered when deployed, no permanent wired connection to manage), this device needs a real, sealed cable-entry detail (a proper cable gland or grommet), not just a generally-sealed box.

**Enclosure: reuse hiking-monitor's design as the starting point (Joseph's call), not built from scratch** — same general approach, adapted specifically where this use case differs: the weatherproof cable entry above, sustained (not just occasional) exterior weather exposure over 1-2 weeks rather than a few hours per hike, and a mounting/hanger feature for the mirror (hiking-monitor's own enclosure has no hook/hanger point today — a real physical addition needed, not present in the current design).

**Not yet started — this is design criteria captured from the interview, not a build.** Still needs: confirming what exterior power access the van actually has (or doesn't), the physical hanger/mount design, and the enclosure's cable-entry detail, before Phase 2 (hardware selection) can proceed on this narrower scope.

**Related:** `components/hiking-monitor/` (the design lineage this borrows from — enclosure approach, ESPHome/flash-buffer firmware pattern, BME280 choice — while staying a genuinely separate device), CARD-0201 (hiking-monitor's own deep-sleep work — no longer load-bearing for this device now that it's wired power, but still relevant to hiking-monitor itself), `JCTsh-Build-Standards.md` §2.14 point 12 (the three-signal model — less directly relevant here since this device has only one purpose and no Intent/mode-switching to design, but worth keeping in mind if this device ever grows a second use).

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

### CARD-0070 · [enhancement] [hiking-monitor] Replace boost converter with LDO + gate peripheral power for lower standby draw — RESOLVED 2026-09-10
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-09-16 (CARD-0193) — 17086B, over the 5000B size threshold.

---

### CARD-0072 · [idea] [logseq] Digital Identity Checklist Version 2
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

Archived to `components/photo-server/card-archive.md` on 2026-09-28 (CARD-0193) — 2478B, over the 2000B size threshold.

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

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 3698B, over the 2000B size threshold.

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

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 4062B, over the 2000B size threshold.

---

### CARD-0094 · [idea] [hike-izer] Switch hike-izer-web from Tailscale Funnel to Cloudflare Tunnel — RESOLVED 2026-07-27
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7381B, over the 5000B size threshold.

---

### CARD-0100 · [bug] [hike-izer] Automatic trigger (CARD-0086) generates and publishes a page even when no hike is confirmed (e.g. GPSLogger left on during a car errand) — RESOLVED 2026-07-27
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 3728B, over the 2000B size threshold.

---

### CARD-0093 · [enhancement] [network] Clean up DNS records on both `jctnet.com` and `jctnet.net` — RESOLVED 2026-07-27
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-08-22 (CARD-0193) — 8063B, over the 5000B size threshold.

---

### CARD-0102 · [investigation] [architecture] Audit: what else breaks when the Pi/M8 weekly scheduled reboots discard in-flight state — RESOLVED 2026-07-27
**Status:** Done

Archived to `architecture/card-archive.md` on 2026-09-28 (CARD-0193) — 3405B, over the 2000B size threshold.

---

### CARD-0099 · [bug] [data-pipeline] Timeline sheet's `timestamp_az` column hardcodes Arizona local time for every row, regardless of where it happened — RESOLVED 2026-07-25
**Status:** Done

Archived to `core/data-pipeline/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5053B, over the 5000B size threshold.

---

### CARD-0097 · [bug] [hike-izer] Hike Start Forecast capture hardcodes Arizona timezone — breaks anywhere but Arizona (Michigan trip, then Egypt trip Feb 2027) — RESOLVED 2026-07-25
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 4155B, over the 2000B size threshold.

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

Archived to `components/netalertx/card-archive.md` on 2026-09-28 (CARD-0193) — 3197B, over the 2000B size threshold.

---

### CARD-0084 · [idea] [hike-izer] Photo integration (Immich) — RESOLVED 2026-07-24
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7410B, over the 5000B size threshold.

---

### CARD-0081 · [idea] [hike-izer] HTML rendering, Levels 1-2 (basic styling + structured layout) — RESOLVED 2026-07-24
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 4025B, over the 2000B size threshold.

---

### CARD-0087 · [bug] [hiking-monitor] GPSLogger ran during today's hike but zero rows reached the GPS Track sheet — RESOLVED 2026-07-23
**Status:** Done

Archived to `components/hiking-monitor/card-archive.md` on 2026-09-28 (CARD-0193) — 4744B, over the 2000B size threshold.

---

### CARD-0079 · [bug] [logging] Old null-byte corruption in the log file (536 bytes, historical, inactive) — RESOLVED 2026-07-23
**Status:** Done

Archived to `core/logging/card-archive.md` on 2026-09-28 (CARD-0193) — 2944B, over the 2000B size threshold.

---

### CARD-0078 · [bug] [netalertx] False "New device detected" alerts re-fire after any Node-RED restart — RESOLVED 2026-07-23
**Status:** Done

Archived to `components/netalertx/card-archive.md` on 2026-09-28 (CARD-0193) — 4765B, over the 2000B size threshold.

---

### CARD-0006 · [enhancement] [logging] Move log directory to USB stick — RESOLVED 2026-07-22
**Status:** Done

Archived to `core/logging/card-archive.md` on 2026-09-28 (CARD-0193) — 2133B, over the 2000B size threshold.

---

### CARD-0075 · [enhancement] [hiking-monitor] Rename project from hiking-sensor to hiking-monitor throughout — RESOLVED 2026-07-21
**Status:** Done

Archived to `components/hiking-monitor/card-archive.md` on 2026-09-28 (CARD-0193) — 4115B, over the 2000B size threshold.

---

### CARD-0073 · [idea] [hike-izer] Hike-izer — narrative summary application layer for hiking data — RESOLVED 2026-07-18
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 16167B, over the 10000B size threshold.

---

### CARD-0034 · [idea] [logseq] Complete digital-identity-protection-checklist.md — RESOLVED 2026-07-17
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-28 (CARD-0193) — 2409B, over the 2000B size threshold.

---

### CARD-0026 · [enhancement] [hiking-monitor] Measure hiking-monitor sleep-mode current draw — RESOLVED 2026-07-16
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-08-22 (CARD-0193) — 12241B, over the 10000B size threshold.

---

### CARD-0068 · [enhancement] [netalertx] Remove online/offline presence messages from the log — RESOLVED 2026-07-15
**Status:** Done

Archived to `components/netalertx/card-archive.md` on 2026-09-28 (CARD-0193) — 3296B, over the 2000B size threshold.

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

Archived to `components/hiking-monitor/card-archive.md` on 2026-09-28 (CARD-0193) — 2230B, over the 2000B size threshold.

---

### CARD-0003 · [enhancement] [mqtt] TLS for Mosquitto (port 8883) — RESOLVED 2026-07-13
**Status:** Done

Archived to `core/mqtt/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7374B, over the 5000B size threshold.

---

### CARD-0061 · [enhancement] [pi1] Add Docker health check for the Pi's Home Assistant container &mdash; RESOLVED 2026-07-12
**Status:** Done

Archived to `hosts/pi1/card-archive.md` on 2026-09-28 (CARD-0193) — 4020B, over the 2000B size threshold.

---

### CARD-0062 · [enhancement] [pi1] Switch Pi to headless boot &mdash; drop the desktop GUI &mdash; RESOLVED 2026-07-12
**Status:** Done

**Notes:** Found 2026-07-12 during a Pi health evaluation. The Pi boots into `graphical.target` with a full desktop session running (`pcmanfm --desktop`, `wf-panel-pi`) even though normal access is SSH-only &mdash; Joseph used the physical desktop once, during initial setup, never since. On a Pi 3B+ with only ~905MB RAM already under real pressure (zram swap sitting at ~50% used while running HA, Node-RED, Mosquitto, the log server, Tailscale, and fail2ban concurrently), this was pure reclaimable overhead.

**Pre-check:** confirmed no VNC/RealVNC/xrdp service configured, and `/etc/xdg/autostart/` + `~/.config/autostart/` contained only standard desktop-session plumbing (polkit agents, on-screen keyboard, compositor) &mdash; nothing load-bearing for SSH-only use.

**Resolution:** `sudo systemctl set-default multi-user.target`, rebooted. Confirmed `systemctl get-default` returns `multi-user.target` and no desktop processes (`pcmanfm`/`wf-panel-pi`) run anymore. SSH access, Docker/HA (HTTP 200 on `:8123`), Mosquitto, Node-RED, and jctsh-logging all confirmed active post-reboot.

**Before/after (steady 4-day uptime vs. 6 minutes post-reboot):** swap usage dropped from 449Mi (~50% of swap) to 148Mi (~16%) &mdash; the clearest signal, since raw "used" memory is a noisy comparison this early (buff/cache hadn't rebuilt yet). The desktop's ~225MB of GTK/panel/session overhead is now structurally absent rather than merely idle. Fully reversible via `systemctl set-default graphical.target` + reboot if ever needed.

---

### CARD-0059 · [idea] [netalertx] NetAlertX — self-hosted LAN device tracker with custom naming — RESOLVED 2026-07-12
**Status:** Done

Archived to `components/netalertx/card-archive.md` on 2026-09-28 (CARD-0193) — 4190B, over the 2000B size threshold.

---

### CARD-0057 · [enhancement] [logging] Serve the kanban board as a live-parsing Pi page — RESOLVED 2026-07-11
**Status:** Done

Archived to `core/logging/CLAUDE.md` on 2026-08-22 (CARD-0193) — 8240B, over the 5000B size threshold.

---

### CARD-0004 · [enhancement] [salt-sensor] Migrate Arduino C++ → ESPHome — RESOLVED 2026-07-11
**Status:** Done

Archived to `components/salt-sensor/card-archive.md` on 2026-09-28 (CARD-0193) — 3862B, over the 2000B size threshold.

---

### CARD-0056 · [enhancement] [tos] Persistent visual kanban board — RESOLVED 2026-07-11
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 2469B, over the 2000B size threshold.

---

### CARD-0052 · [idea] [tos] JCTsh Team Operating System (TOS) — RESOLVED 2026-07-11
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-28 (CARD-0193) — 2973B, over the 2000B size threshold.

---

### CARD-0043 · [bug] [photo-server] Robin's library missing metadata (null width/height/orientation) for large fraction of assets — RESOLVED 2026-07-10
**Status:** Done

Archived to `components/photo-server/card-archive.md` on 2026-09-28 (CARD-0193) — 2656B, over the 2000B size threshold.

---

### CARD-0042 · [bug] [photo-server] Robin's library missing thumbnails for ~81% of assets — RESOLVED 2026-07-10
**Status:** Done

Archived to `components/photo-server/card-archive.md` on 2026-09-28 (CARD-0193) — 2872B, over the 2000B size threshold.

---

### CARD-0051 · [enhancement] [photo-server] Extend heartbeat with disk-capacity and backup-staleness checks
**Status:** Done

Archived to `components/photo-server/card-archive.md` on 2026-09-28 (CARD-0193) — 2226B, over the 2000B size threshold.

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

First deploy attempt crashed on the state-file write (`/etc/jctsh/` isn't writable by the `jct` user, appropriately, since it holds credentials) — moved the state file to `/home/jct/.jctsh/` and added `os.makedirs`. Verified live 2026-07-10: first corrected run notified correctly (`v3.0.2` vs. running `v3.0.1`), confirmed on the dashboard; second run correctly skipped re-notifying for the same version. Added to `network/jctsh-network.md`'s Scheduled Maintenance Windows table (6:00 AM daily, no conflicts with existing jobs). Actual update application remains a deliberate manual step, not automated.

---

### CARD-0022 · [enhancement] [architecture] Security hardening — infrastructure audit (Steps 1–8)
**Status:** Done

**Resolution:** All 8 steps complete. Steps 1–5 and 8 passed clean or were fixed on 2026-06-20 (SSH key-only auth, MQTT auth, port audit, Node-RED adminAuth). Step 7 (HA MFA) done 2026-07-09: TOTP enabled for both Joseph and Robin via HA profile → Multi-Factor Authentication Modules. Step 6 (router UPnP) done 2026-07-09: found enabled with zero registered clients, disabled with no functional impact. Full findings in `jctsh-security-hardening.md`. Patterns harvested to `JCTsh-Build-Standards.md` §10 Security Standards (v1.14).

---

### CARD-0023 · [enhancement] [architecture] Security hardening — cloud accounts (Steps 9–14 + Final)
**Status:** Done

**Resolution:** All steps complete. Steps 9–12 and 14 passed clean 2026-06-20 (Ring/Amazon, SmartThings, Google ×2, Windows machine — one stale SmartThings connected app, SharpTools, revoked). Step 13 done 2026-07-09: router admin password rotated to a new strong unique password (`credentials.local.md`), remote/WAN management confirmed disabled, DNS confirmed intentional (CenturyLink/Quantum Fiber bypass-modem setup), firmware found one version behind (1.5.2 → 1.5.3 available) with auto-update now enabled (nightly 3–5 AM) rather than relying on manual checks going forward. Final Step complete: findings harvested to `JCTsh-Build-Standards.md` §10 Security Standards (v1.14).

---

### CARD-0039 · [bug] [photo-server] Re-verify Takeout import completeness — 3,433 assets were genuinely missing
**Status:** Done

Archived to `components/photo-server/card-archive.md` on 2026-09-28 (CARD-0193) — 2511B, over the 2000B size threshold.

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

### CARD-0036 · [enhancement] [architecture] Dashboard visibility for scheduled reboots
**Status:** Done

**Resolution:** CARD-0035's scheduled reboots were invisible on the JCTsh log dashboard — confirming success required manually SSHing in and checking `systemctl`/`docker ps`. Added a matched pair of MQTT log messages around each reboot: `scheduled-reboot.service` now publishes `"Scheduled reboot about to occur."` immediately before calling `/sbin/reboot` (multiple `ExecStart=` lines in the oneshot unit), and a new `reboot-complete.service` (enabled via `WantedBy=multi-user.target`) publishes `"Boot complete."` on every boot once the MQTT broker is reachable. Pi publishes as component `jctsh-core` to `jctsh/core/log-server/log` using the existing `jctsh-log-server` MQTT account (`/etc/jctsh/log-server.env`) via `mosquitto_pub` (already installed). M8 publishes as component `photo-server` to `jctsh/server/photo-server/log` using the existing `photo-server` MQTT account (`/etc/jctsh/heartbeat.env`) — required installing the `mosquitto-clients` apt package on the M8 (the heartbeat script uses Python `paho-mqtt` instead, so the CLI wasn't already present). Neither message uses the `"Heartbeat - "` prefix, so each occurrence stays visible as its own dashboard row rather than collapsing. Per-host unit files split out: `scheduled-reboot-pi.service`/`scheduled-reboot-m8.service` replace the old shared `scheduled-reboot.service` (now host-specific since the MQTT broker address, credentials file, and topic differ per host). Verified live 2026-07-08 via manual `systemctl start reboot-complete.service` on both hosts — confirmed on the dashboard (`/data` live view and, after flushing, the persisted `/log` file).

---

### CARD-0037 · [bug] [photo-server] ML processing (faces, smart search, duplicates, OCR) never ran on a large fraction of the library
**Status:** Done

Archived to `components/photo-server/card-archive.md` on 2026-09-28 (CARD-0193) — 2536B, over the 2000B size threshold.

---

### CARD-0035 · [enhancement] [architecture] Weekly scheduled reboot — Pi and M8 photo-server
**Status:** Done

**Resolution:** Deployed systemd timers on both hosts: `scheduled-reboot.timer` → `scheduled-reboot.service` (`/sbin/reboot`), `Persistent=true`. Pi: Monday 3:00 AM. M8: Monday 4:00 AM — staggered one hour later so the M8 heartbeat script's MQTT publish to the Pi's Mosquitto broker doesn't collide with the Pi being mid-reboot. Not synchronized to KeepConnect's own weekly router reset — that schedule has drifted from its original Wednesday setting, most likely because its "every 7 days" timer restarts from any reset (scheduled or outage-triggered), so it can't be relied on as a fixed weekday anyway; a router reboot's brief network blip is tolerated regardless of timing. Version-controlled unit files in `core/maintenance/`; documented in `SOFTWARE-ENVIRONMENT.md` (Pi) and new `components/photo-server/operations.md` (M8). Verified live via `systemctl list-timers` on both hosts — next run confirmed Mon 2026-07-13. 2026-07-08.

---

### CARD-0033 · [idea] [architecture] Document Keep Connect configuration and schedule
**Status:** Done

**Resolution:** KeepConnect is a standalone router-rebooter device (Johnson Creative KeepConnect-27F8, not a JCTsh component). New dedicated doc `network/keepconnect.md` created with full device identity, network config, physical outlet-scoping rationale, and complete monitor/timing/schedule/notification configuration. Linked from `network/jctsh-network.md` devices table (IP 192.168.1.108, DHCP-reserved) and `ENVIRONMENT.md` Hub & Controller table; added to `README.md` repository layout. Remaining open item (scheduled Pi/Immich reboot via cron, separate from power-strip cycling) carried forward in `network/keepconnect.md` itself. 2026-07-08.

---

### CARD-0021 · [enhancement] [logging] Device status dashboard
**Status:** Done

Archived to `core/logging/card-archive.md` on 2026-09-29 (CARD-0193) — 91 days since last touched, over the 90-day backup threshold.

---

### CARD-0018 · [idea] [photo-server] Self-hosted photo library
**Status:** Done

Archived to `components/photo-server/card-archive.md` on 2026-09-29 (CARD-0193) — 91 days since last touched, over the 90-day backup threshold.

---

### CARD-0014 · [enhancement] [data-pipeline] Move environmental data pipeline to core
**Status:** Done

Archived to `core/data-pipeline/card-archive.md` on 2026-09-29 (CARD-0193) — 91 days since last touched, over the 90-day backup threshold.

---

### CARD-0002 · [enhancement] [mqtt] MQTT v3.1.1 → v5 upgrade
**Status:** Done

Archived to `core/mqtt/card-archive.md` on 2026-09-29 (CARD-0193) — 91 days since last touched, over the 90-day backup threshold.

---

### CARD-0008 · [enhancement] [hiking-monitor] Pixel hotspot second WiFi field test
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-09-16 (CARD-0193) — 91 days since last touched, over the 90-day backup threshold.

---

### CARD-0017 · [enhancement] [architecture] Charging state schema fields for solar/battery sensors
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-16 (CARD-0193) — 93 days since last touched, over the 90-day backup threshold.

---

### CARD-0016 · [enhancement] [offline-logger] Offline flash logging — extract reusable standard
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-09-16 (CARD-0193) — 94 days since last touched, over the 90-day backup threshold.

---

### CARD-0015 · [enhancement] [front-porch-temp-sensor] Environmental data pipeline integration
**Status:** Done

Archived to `components/front-porch-temp-sensor/CLAUDE.md` on 2026-09-16 (CARD-0193) — 94 days since last touched, over the 90-day backup threshold.

---

### CARD-0007 · [idea] [hiking-monitor] Hiking observations pipeline (Tasker → Sheets)
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-09-16 (CARD-0193) — 95 days since last touched, over the 90-day backup threshold.

---

### CARD-0001 · [bug] [garage-radar] Garage-radar false presence on door close
**Status:** Done

**Resolution:** Ill-defined and no longer applicable — closed.

---

### CARD-0090 · [enhancement] [hiking-monitor] Tasker "Log Observation" widget cuts off recording too early on normal speech pauses
**Status:** Defer

Archived to `components/hiking-monitor/card-archive.md` on 2026-09-28 (CARD-0193) — 2490B, over the 2000B size threshold.

---

### CARD-0074 · [idea] [hike-izer] Hike-izer Version 2 — SUPERSEDED, split into individual feature cards
**Status:** Defer

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 2588B, over the 2000B size threshold.

---

### CARD-0027 · [idea] [hiking-monitor] GPIO-controlled power gating for I2C peripherals during sleep — SUPERSEDED by CARD-0259
**Status:** Defer

Archived to `components/hiking-monitor/card-archive.md` on 2026-09-28 (CARD-0193) — 4455B, over the 2000B size threshold.

---

### CARD-0050 · [idea] [architecture] Network segmentation to contain a compromised/hostile device on home WiFi
**Status:** Defer

Archived to `architecture/card-archive.md` on 2026-09-28 (CARD-0193) — 4895B, over the 2000B size threshold.

---

### CARD-0115 · [bug] [hike-izer] Hike Start Forecast only captures once per calendar day, not once per hike session — RESOLVED 2026-07-30 13:55 MST
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 3849B, over the 2000B size threshold.

---

### CARD-0116 · [bug] [hike-izer] Second same-day hike's photo thumbnails 404 — templating.py referenced the wrong photo directory — RESOLVED 2026-07-29 15:44 MST
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 2706B, over the 2000B size threshold.

---

### CARD-0117 · [bug] [hike-izer] Photo captions never persisted to disk — a manifest re-read loses them silently — RESOLVED 2026-07-29 15:51 MST
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 2342B, over the 2000B size threshold.

---

### CARD-0118 · [enhancement] [hike-izer] Calendar home page: multi-hike days need a real in-cell picker, not a tiny superscript number — RESOLVED 2026-07-29 16:30 MST
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-28 (CARD-0193) — 4089B, over the 2000B size threshold.

---

### CARD-0119 · [enhancement] [hike-izer] Mount the M8 staging directory as a Windows drive (SSHFS-Win), document operational steps for managing staged data — RESOLVED 2026-07-30 13:10 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5215B, over the 5000B size threshold.

---

### CARD-0120 · [bug] [hike-izer] Automatic session query window trusts GPSLogger's self-reported start time -- undercounted today's hike by ~85% — RESOLVED 2026-07-30 06:15 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5952B, over the 5000B size threshold.

---

### CARD-0121 · [bug] [hike-izer] Automatic generation never runs if GPSLogger's "stopped" broadcast never fires — RESOLVED 2026-08-29
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-09-10 (CARD-0193) — 10806B, over the 5000B size threshold.

---

### CARD-0122 · [enhancement] [hike-izer] Automated staging: BirdNET Live phone Share → webhook → M8 staging directory — RESOLVED 2026-07-30 12:45 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 8004B, over the 5000B size threshold.

---

### CARD-0123 · [enhancement] [hike-izer] Make narrative generation opt-in; move place-context/sun-position data into tables instead of prose — RESOLVED 2026-07-30 14:50 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6077B, over the 5000B size threshold.

---

### CARD-0251 · [enhancement] [tos] Auto verify markers — date-based and event-based
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-18 (CARD-0193) — 7057B, over the 5000B size threshold.

---

