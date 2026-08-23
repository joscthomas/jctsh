# core/maintenance — Context

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — manually forced (--force).

### CARD-0125 · [enhancement] [maintenance] Pi OS/firmware maintenance check — CARD-0095's Pi-side counterpart
**Status:** Done

**Notes:** Raised 2026-07-31, immediately after CARD-0095 shipped the same thing for the M8. The Pi has the identical gap CARD-0095 just closed for the M8 — no visibility into `apt`-upgradable packages, the `reboot-required` flag, or pending firmware, despite having its own weekly scheduled reboot (Mon 3 AM, vs. the M8's Mon 4 AM, `SOFTWARE-ENVIRONMENT.md`) that this same information would make meaningful rather than blind. Arguably a bigger gap than the M8's was: the Pi is the actual household coordination hub (MQTT broker, Node-RED logic, HA integration, log server) — the highest-stakes host in the whole stack per CARD-0096's own risk ranking — yet currently has zero maintenance visibility, while the lower-stakes M8 now does.

**Live-checked on the Pi, 2026-07-31 (Planning) — corrects two assumptions from the original scoping:**
- **No `rpi-eeprom-update` firmware step needed at all.** Ran it live: `Device does not a have a Raspberry Pi bootloader EEPROM (e.g. Pi 4 or Pi 5). Skipping bootloader update.` — this Pi is a 3B+ (matches `jctsh-network.md`'s WiFi note), which has no separate flash-based EEPROM bootloader the way a Pi 4/5 does. Its boot firmware updates through the ordinary `raspi-firmware` **apt package** instead — already visible in the plain apt-upgradable list, no separate check mechanism required. Simpler than the M8's script, not a port of its `fwupdmgr` logic at all — that whole function can just be dropped for the Pi variant.
- **Docker scope confirmed narrow:** only `homeassistant` runs in Docker (`docker ps` shows exactly one container, "Up 4 days (healthy)"). Node-RED and Mosquitto are confirmed native systemd services (`active`/`enabled`, not containers). So the "a Docker update restarts the daemon and touches every running container" consideration from CARD-0095 still applies, but scoped to one container, not eight — lower blast radius by count, though HA is arguably more sensitive per-container since Robin depends on it directly.
- **275 packages currently upgradable** — startlingly more than the M8's 38, but not a red flag: this Pi runs the **full Raspberry Pi Desktop OS** (chromium, firefox, cups printing, X11/Wayland, `lpplug-*`/`wfplug-*` desktop panel widgets, `rpi-connect`, `piclone`, etc.), not a minimal headless server image, despite its actual role being MQTT/Node-RED/HA/log-server only. All of that desktop-environment cruft is genuinely unused for this host's real function — low functional risk either way, folds into the same "routine, low-ceremony" bucket the M8's `linux-firmware-*` blobs already use. (Reinstalling as Raspberry Pi OS Lite to shed it entirely would be a much bigger, separate infrastructure decision — explicitly not in scope here, just noted as an observation.)
- `reboot-required` currently **not set** (clean baseline) — unlike the M8 when CARD-0095 started.
- Review-pattern list carries over unchanged: `docker`, `containerd`, `linux-image`, `linux-generic`, `libc6` all still appear in the Pi's own upgradable list (e.g. `linux-image-rpi-2712`, `linux-image-rpi-v8`, `libc6`) and mean the same thing here as they did for the M8.

**Scope (revised, simpler than first scoped):**
1. Fork `components/photo-server/maintenance-check.py` → a Pi variant (or generalize into one script with a host-aware firmware step — decide at Build time which reads cleaner). Apt/reboot-required logic and the review-pattern list port unchanged.
2. Drop the `fwupdmgr`-based firmware function entirely for the Pi variant — nothing to check, per the live finding above.
3. Reuse CARD-0095's policy directly, no re-deriving: notify-only, never auto-apply; low-risk bulk applied routinely; Docker/kernel-class items get a deliberate human pass; security-relevant findings get a bias toward applying rather than indefinite deferral.
4. **Cadence: monthly, 1st of month, 8:00 AM** — one hour after the M8's own 7:00 AM check, so both land the same morning for a single review session without firing at the exact same moment. Add to `jctsh-network.md`'s Scheduled Maintenance Windows table alongside the M8's entry.

**Done when:** the check is built, deployed, and enabled on the Pi, verified live the same way CARD-0095's was (a real finding correctly published as a non-collapsing `Alert`, the throttle correctly skipping an unchanged finding on a second run), and the new job is recorded in `jctsh-network.md`.

**Built and verified, 2026-07-31.** New `core/maintenance/pi-maintenance-check.py` — went with a genuinely separate script rather than a shared/host-aware one, since the Pi version is meaningfully simpler (no firmware function at all) and matches the Pi's own existing conventions rather than the M8's: `mosquitto_pub` via subprocess instead of `paho-mqtt`, component `jctsh-core` and topic `jctsh/core/log-server/log` instead of a per-host dedicated account, broker `127.0.0.1`, credentials from `/etc/jctsh/log-server.env` — mirroring `core/homeassistant/pi-heartbeat.py` exactly rather than forcing the M8 script's shape onto a different host. `core/maintenance/pi-maintenance-check.service`/`.timer` follow `pi-heartbeat`'s pattern too (no `User=`, runs as root — matches `/etc/jctsh/log-server.env` being root-only, confirmed live when a plain non-root manual run hit `PermissionError` and the `sudo`-run one didn't).

Deployed and enabled on the Pi (no sudo password prompt needed at all, unlike every M8 deploy this session — the Pi has passwordless sudo for `pi`). **Verified live:** first run correctly found and published the real current state — `264 routine update(s) pending. 11 package(s) need review: containerd.io, docker-buildx-plugin, docker-ce, docker-ce-cli, docker-ce-rootless-extras, docker-compose-plugin, docker-model-plugin, libc6, libc6-dev, linux-image-rpi-2712, linux-image-rpi-v8` (264+11 = 275, matching the Planning-stage live count exactly) — confirmed on the dashboard as `jctsh-core`, category `Alert`. A second run (as root, matching how the timer actually invokes it) correctly recognized the unchanged fingerprint and skipped re-notifying ("next reminder in 6d"). Added to `jctsh-network.md`'s Scheduled Maintenance Windows table (1st of month, 8 AM — one hour after the M8's own check).

**Not done today, deliberately:** applying any of the 275 pending packages — that's a separate decision each month, same as CARD-0095's own low-risk-bulk-then-review-list pattern, not something to rush through just because the check now exists.

**Real incident found and fixed, 2026-07-31, same session — two bugs, both live-verified after the fix:**

1. **The review-pattern filter had a gap that let kernel/`libc6` through miscategorized as "routine."** When the 264 low-risk packages got applied (separately, per Joseph's go-ahead), the filter — `REVIEW_PATTERNS = ("docker", "containerd", "linux-image", "linux-generic", "libc6")` — used exact substrings that missed `linux-headers-rpi-2712`/`linux-headers-rpi-v8`/`linux-libc-dev`. Installing those pulled the actual kernel image (`linux-image-6.18.34+rpt-rpi-v8`/`-2712`) and `libc6`/`libc6-dev` in as **automatic apt dependencies** — exactly the packages the filter was supposed to hold back for CARD-0129's home-only pass. Confirmed via `/var/log/apt/history.log`. Nothing broke (the Pi kept running the old kernel until a reboot — HA/Node-RED/Mosquitto all confirmed healthy afterward), but the safety boundary was quietly crossed. **Fix:** broadened to `REVIEW_PATTERNS = ("docker", "containerd", "linux-", "libc6")` — every kernel-adjacent package on this system (`linux-image`, `linux-headers`, `linux-libc-dev`, `linux-base`, `linux-kbuild`) shares the `linux-` prefix, confirmed against the real installed package list. **Same latent bug existed in the M8's `maintenance-check.py`** (identical pattern list) — never actually triggered there (no `linux-headers` packages were pending on the M8), but fixed there too for consistency, redeployed and reverified `Nothing pending` (no regression).
2. **`/var/run/reboot-required` never exists on Raspberry Pi OS at all** — no `update-notifier-common` package (unlike Ubuntu, which the M8 runs), confirmed via `dpkg -l`. This Pi's `_reboot_required()` was therefore silently non-functional from the moment CARD-0125 shipped — it would report "no reboot needed" even with a brand-new unapplied kernel sitting there, which is exactly the state discovered by bug #1 above. **Fix:** replaced the file-existence check with a direct comparison — `uname -r` (running kernel) against every installed `linux-image-<version>` package via `dpkg --compare-versions`, flagging true if any installed version is newer than what's actually running. Verified live: correctly detected `reboot required` against the real post-bug-#1 state (kernel installed but not active), where the old check would have stayed silent forever.

Both fixes deployed and reverified end to end: a fresh run correctly reported `7 package(s) need review: containerd.io, docker-buildx-plugin, docker-ce, docker-ce-cli, docker-ce-rootless-extras, docker-compose-plugin, docker-model-plugin; reboot required` — the real, now-accurate remaining state (see CARD-0129, scope corrected accordingly).

**Related:** CARD-0095 (the M8 sibling this ports from, including its full policy writeup, and which shared the same review-pattern bug), CARD-0129 (the actual apply-and-reboot work this incident's fallout feeds into), CARD-0126 (raised alongside this one, the container-image-layer counterpart), CARD-0096 (unrelated functionally, but touches the same host — worth sequencing awareness if both are ever in Build at once), `core/homeassistant/pi-heartbeat.py` (the convention this script actually follows), `components/photo-server/maintenance-check.py` (the M8 sibling script), `SOFTWARE-ENVIRONMENT.md`.

---

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 5197B, over the 5000B size threshold.

### CARD-0177 · [enhancement] [maintenance] Back up Pi1's HA + Mosquitto state to the M8 — RESOLVED 2026-08-16 18:50 MST

**Status:** Done

**Raised 2026-08-16**, opened directly from CARD-0172's disaster-recovery audit — the one gap recommended *not* to accept. `/mnt/jctsh-logs/homeassistant` (87MB, full HA `/config` — `.storage/` entity+area registries, every integration's own OAuth/pairing state such as SmartThings and the Samsung TV, recorder history) and `/mnt/jctsh-logs/mosquitto` (308KB, broker persistence) have zero backup today. Both are small enough that a fix is cheap; the consequence of losing them (re-pairing every integration, losing all history, rebuilding dashboards from scratch) is real — same asymmetry argument CARD-0095 already used for security-patch cadence.

**Design sketch, matching this repo's existing `photo-library-backup.sh` pattern (`components/m8/backup.md`) — confirm/adjust at Build time, not fixed in stone here:**
- Weekly rsync (matching that job's cadence) of both directories from the Pi to a destination on the M8, which already has spare capacity and its own backup precedent.
- Direction and auth: cross-host (Pi→M8 or M8→Pi) needs its own SSH key trust — `CLAUDE.md`'s documented passwordless SSH is only from Joseph's own laptop to each host, not host-to-host. Needs a new key pair generated and authorized specifically for this job, scoped only to what it needs, not reusing either host's own general access.
- MQTT log visibility for success/failure, same convention every other maintenance script in this repo already uses (`Alert` category on failure, `System` on success).
- Retention: mirror, not versioned snapshots, unless a real reason emerges to keep history — same "steady state, not an ever-growing pile" reasoning `photo-library-backup.sh` already uses.

**Acceptance criteria:**
1. Cross-host SSH trust established, scoped narrowly (not reusing Joseph's own laptop-to-host keys).
2. Weekly backup job running (systemd timer, matching this repo's convention), rsyncing both directories to the M8.
3. MQTT log visibility for success/failure.
4. Verified live: a real backup runs successfully, and the M8-side copy is confirmed to actually match the Pi's live state (not just "the job exited 0").

**Built 2026-08-16, matching the design sketch above (Pi pushes to M8):**
- New dedicated SSH keypair (`/home/pi/.ssh/pi1_backup_ed25519`, no passphrase — runs unattended via systemd), authorized on the M8 via `rrsync` (`command="rrsync /home/jct/pi1-backup/",restrict` in `jct`'s `authorized_keys`). Confirmed live, not just assumed from `rrsync`'s docs: a shell attempt with this key (`ssh ... whoami`) is rejected outright (`SSH_ORIGINAL_COMMAND does not run rsync`), and a destination path outside the restricted directory doesn't escape it — `rrsync` silently re-roots *any* client-supplied path at its own restricted directory instead.
- **Real bug hit from that same re-rooting behavior**, live on the first actual run: the script's destination path was `.../home/jct/pi1-backup/homeassistant/`, which `rrsync` re-rooted into `/home/jct/pi1-backup/home/jct/pi1-backup/homeassistant/` — a directory that doesn't exist, so the first real run failed outright (`rsync error: error in file IO (code 11)`). Fixed by making the destination paths bare/relative (`jct@192.168.1.165:homeassistant/`), which resolve correctly inside the sandbox without repeating its root — confirmed with a manual dry-run before redeploying.
- New `core/maintenance/pi1-backup-to-m8.py` (+ matching `.service`/`.timer`) — same MQTT-log pattern as `pi-maintenance-check.py` (`mosquitto_pub`, `/etc/jctsh/log-server.env`, component `jctsh-core`). `RequiresMountsFor=/mnt/jctsh-logs` on the service unit, per `CLAUDE.md`'s standing convention for anything touching that drive. Timer: weekly, Sunday 3:00 AM — after the M8's own 2:15 AM photo backup, clear of both hosts' Monday reboots; added to `jctsh-network.md`'s Scheduled Maintenance Windows table.

**Verified live, real device, both the failure and the fix:**
- The failed first run correctly published an `Alert` to the log dashboard with the real rsync error text — confirmed via the dashboard itself (Basic Auth), not assumed from the script's own logic.
- After the fix: `systemctl start` succeeded, published a `System` "complete" message, also confirmed on the dashboard.
- **Real state match, not just exit-code trust**: `homeassistant/` — 89,563,774 bytes on both the Pi and the M8, byte-identical. `mosquitto/` — 309,428 bytes on both, byte-identical. 300 files total on both sides.
- Timer confirmed enabled (`systemctl list-timers`), next run correctly scheduled for the following Sunday.

**Done when:** a real backup has run successfully at least once, verified to contain a true mirror of both directories, and the recurring schedule is confirmed enabled. **Met** — byte-identical mirror confirmed live, timer enabled.

**Related:** CARD-0172 (the disaster-recovery audit this closes the one open gap from), `components/m8/backup.md` (the pattern this follows), CARD-0159/CARD-0006 (why this state lives on the USB drive in the first place).

---

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 6777B, over the 5000B size threshold.

### CARD-0158 · [enhancement] [maintenance] Automated post-reboot health check on the Device Status dashboard — RESOLVED 2026-08-17 12:14 MST
**Status:** Done

**Raised 2026-08-13 20:53 MST**, during CARD-0129's close-out. That card's pre-check found the Pi had already been rebooted 3 days earlier by its own `scheduled-reboot.timer` (2026-08-10) with nobody noticing — the reboot happened to go fine, but nothing would have surfaced it if it hadn't. Current coverage: the watchdog/heartbeat system (`core/logging/log_server.py` + Node-RED watchdog flow) catches MQTT/Node-RED/log-server going silent, but nothing watches Docker/container health specifically after a reboot — a bad `homeassistant` container recovery, for instance, would go unnoticed until someone happened to check by hand.

**Decided design — mirrors CARD-0127's retained-MQTT-state pattern exactly** (that card fixed the same underlying problem — a dashboard column reflecting "last message logged" instead of "current true state" — for pending updates; this applies the identical fix to reboot health):

1. A small systemd oneshot, triggered shortly after boot (`After=multi-user.target`, or timed a few minutes past the known reboot window), runs the same checklist CARD-0129's resolution used by hand: `docker ps` for `homeassistant` reaching Docker's own `healthy` state (not just "container exists"), `systemctl is-active nodered mosquitto`, HA reachable on the LAN.
2. Publishes the result as an **MQTT retained message** every run (not just on change), same convention as `immich-update-check.py`: topic `jctsh/core/raspberrypi/reboot-health`, payload along the lines of `{"last_reboot": "<iso ts>", "healthy": true/false, "checks": {...}}`.
3. `log_server.py` subscribes and tracks it in a dedicated state dict (extending the `_pending_updates`-style pattern CARD-0127 introduced — deliberately not folded into the history-based `_entries`), rendering a new "Last Reboot" column on `/status` that reflects current truth regardless of what else gets logged for that host afterward. Free correctness on log-server restart too, via MQTT's own retained-redelivery — no `_save_state()` work needed, per CARD-0127's own confirmed finding.
4. Goes one step further than CARD-0127 did: on `healthy: false`, also fire a push notification through the existing watchdog/Alert path — a failed reboot is worth proactively paging for, not just something to notice on the next dashboard visit.

**Open question for Build time:** should this be Pi-only (today's actual gap), or built generically enough to cover the M8's own weekly reboot too (same `scheduled-reboot.timer` pattern there, per `jctsh-network.md`'s Scheduled Maintenance Windows table) — not yet decided, lean toward designing the mechanism generically (component-parameterized, like CARD-0127's own topic ended up) even if only the Pi side is wired up first.

**Done when:** a real Pi reboot (the next scheduled one, 2026-08-17, or a manual test) produces a correct "Last Reboot" entry on `/status` reflecting genuine current health, survives being superseded by an unrelated log message for the same host (the exact CARD-0127 failure mode, re-verified here), survives a log-server restart with no gap, and a simulated `healthy: false` correctly triggers a push notification.

**Built same night, 2026-08-13 evening — everything short of a real reboot
verified live.** New `core/maintenance/reboot-health-check.py` +
`reboot-health-check.service` (oneshot, deployed and enabled on the Pi,
`WantedBy=multi-user.target` so it fires on every future boot). `log_server.py`
extended with the mirrored `_reboot_health` dict, `/reboot-health` topic
subscription, and a new "Last Reboot" column on `/status` — same pattern as
`_pending_updates`, deployed and confirmed live.

**Deviations from the sketch above, decided during Build:** topic ended up
`jctsh/core/jctsh-core/reboot-health` (component `jctsh-core`, not
`raspberrypi`) — put on the same dashboard row the existing watchdog
heartbeat already uses for this host, rather than inventing a second
pseudo-component row for the same physical Pi. No item-namespacing needed
(unlike Pending Update) — only ever one reboot-health fact per host. The
"push notification" piece is the same Alert-category MQTT log message every
other maintenance script here already uses to get Joseph's attention (not a
new, separately-verified push path) — consistent with the rest of this
codebase's notification convention, not a weaker version of what was asked.
The open question about M8 coverage was left alone — Pi-only for now, but
the mechanism (component read from the topic, not hardcoded) already
supports adding an M8 publisher later with zero `log_server.py` changes.

**Verified live on the real device:** a manual run of the script correctly
reported genuine current state (`homeassistant` reaching Docker's own
`healthy`, not just "container exists"; Node-RED/Mosquitto active) and the
*real* 2026-08-10 03:00 boot time, not "now." Dashboard renders both the
healthy state (green ✓) and a synthetic failure (red ✗, per-check
breakdown) correctly. Restarted `jctsh-logging` mid-test — the column
repopulated with zero gap, purely from MQTT's retained redelivery, same
property CARD-0127 already established for Pending Update.

**Deliberately left unverified tonight, Joseph's call:** an actual full
system reboot. `reboot-health-check.service` is enabled and will fire
automatically at the next real boot regardless — **check in 2026-08-17**
(the next `scheduled-reboot.timer` firing) to confirm it survives a genuine
cold boot, not just a manual script invocation, before moving this to Done.

**Verified live against the real cold boot, 2026-08-17 12:14 MST:** the
Pi's `scheduled-reboot.timer` fired at 03:00 MST as expected;
`reboot-health-check.service` ran automatically (03:01:58–03:02:52 MST,
`journalctl` confirms `code=exited, status=0/SUCCESS`) and correctly
reported `{'homeassistant': 'healthy', 'nodered': 'active', 'mosquitto':
'active'}` from genuine post-boot state, not a manual invocation. Dashboard
(`/status`) confirmed reflecting it correctly: `jctsh-core` row, Last Reboot
column shows `✓ 2026-08-17 03:00:42` — real boot timestamp, healthy state,
exactly the "current truth" design goal. Last remaining condition for Done
is satisfied.

**Related:** CARD-0129 (the check that surfaced this gap), CARD-0127 (the retained-MQTT-state pattern this generalizes, full implementation detail there), CARD-0126 (sibling dashboard-visibility work, container-image updates), `core/logging/log_server.py` (`_pending_updates`, `_build_status_html`), `jctsh-network.md` (Scheduled Maintenance Windows table, for the possible M8 extension).

---

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 6407B, over the 5000B size threshold.

### CARD-0129 · [enhancement] [maintenance] Apply Pi's remaining Docker/kernel packages and reboot — RESOLVED 2026-08-13 20:51 MST
**Status:** Done

**Blocked — deferred until Joseph is physically home (2026-07-31).** Same reasoning as CARD-0096's own block: the Pi is the household coordination hub (MQTT broker, Node-RED, HA, log server), Joseph is remote as of this writing, and this specific action (a Docker daemon restart plus a full reboot) is exactly the class of higher-stakes change that mitigation exists for — if Tailscale hiccups mid-action (already happened once this session), being on the home LAN removes it as a dependency for the recovery path.

**Notes:** Surfaced by CARD-0125's build/verification. The Pi has 275 pending packages total; the 264 low-risk routine ones were applied same session.

**Scope corrected, 2026-07-31 (see CARD-0125 for the full incident) — the "no Docker/kernel/libc6 involved" claim above was wrong.** The review-pattern filter used to apply the 264 had a real gap (`linux-image`/`linux-generic` as exact substrings missed `linux-headers-*`/`linux-libc-dev`) — installing those pulled the actual kernel image and `libc6` in as automatic apt dependencies, despite being meant to stay held back. **Already installed, not yet active:** the 6.18.34 kernel and `libc6`/`libc6-dev` are on disk, but the Pi is still *running* the old 6.12.75 kernel (`uname -r`) — nothing is currently broken (HA/Node-RED/Mosquitto all confirmed healthy after the fact), but a reboot is now needed to actually pick these up, not just for the Docker packages. **Genuinely still untouched, confirmed via a fresh `apt list --upgradable`:** only 7 pure Docker packages — `containerd.io`, `docker-buildx-plugin`, `docker-ce`, `docker-ce-cli`, `docker-ce-rootless-extras`, `docker-compose-plugin`, `docker-model-plugin`. Installing those restarts the daemon and touches the one Docker container on the Pi (`homeassistant` — Robin depends on this directly). The reboot itself briefly takes down MQTT, Node-RED, and the log server along with everything downstream (ESP32 heartbeats, HA, the dashboard itself) — same as before, just now needed regardless of the Docker packages too.

**Plan, once home (mirrors CARD-0095's own M8 sequence, already proven tonight):**
1. Pre-check: `docker ps` (confirm `homeassistant` healthy), `systemctl is-active nodered mosquitto`.
2. Apply the 7 remaining Docker packages via the same explicit `apt-get install --only-upgrade` pattern already used tonight — never a blanket `apt upgrade`.
3. Verify `homeassistant` recovers cleanly after the Docker daemon restart.
4. Reboot — clears the already-installed kernel/`libc6` (confirm via `uname -r` matching the newest installed `linux-image-*` package afterward) as well as anything the Docker install itself required.
5. Verify post-reboot: `homeassistant` healthy, Node-RED/Mosquitto active, MQTT broker accepting ESP32 connections again (watch the dashboard for continued heartbeats — garage-radar/salt-sensor/front-porch-temp-sensor/hiking-monitor), HA reachable both on the LAN and via Nabu Casa, log dashboard itself still up, `pi-maintenance-check.timer` survived the reboot.
6. Run `pi-maintenance-check.py` manually — should report "Nothing pending," same clean end-state CARD-0095 reached for the M8. (Its reboot-detection was itself buggy until fixed same session — see CARD-0125 — so this check is now actually trustworthy, not just optimistic.)

**Done when:** the 7 remaining packages applied, Pi rebooted, `uname -r` confirmed matching the newest installed kernel, every item in step 5's verification list confirmed live — not just "commands ran," the same standard CARD-0095/CARD-0124 held themselves to.

**Resolved 2026-08-13 evening, Joseph home on the LAN as planned — but the scope
turned out smaller than the plan above.** Pre-check found the card's own
documented state was stale: `uname -r` showed the Pi already running kernel
6.18.34 (the one this card said still needed a manual reboot to activate),
with `uptime` at only 3d17h. Traced to `scheduled-reboot.timer` — last fired
**2026-08-10 03:00 MST** (next due 2026-08-17) — the routine weekly reboot had
already picked up the pending kernel/`libc6` on its own, with nothing
special done for it. Only the 7 Docker packages were genuinely still
pending (confirmed fresh via `apt list --upgradable`).

**Joseph's call, given the kernel was already live:** apply just the 7
Docker packages, skip the full reboot — smaller blast radius (no MQTT/
Node-RED/log-server outage), and the weekly timer will cycle the Pi again in
4 days regardless. Applied via the same explicit
`apt-get install --only-upgrade` pattern as the earlier 264-package batch
(never a blanket `apt upgrade`) — `containerd.io`, `docker-buildx-plugin`,
`docker-ce`, `docker-ce-cli`, `docker-ce-rootless-extras`,
`docker-compose-plugin`, `docker-model-plugin`, all installed cleanly, no
errors.

**Verified live:** `homeassistant` container reached Docker's own `healthy`
health-check state after the daemon restart (polled, not just "container
exists"); Node-RED and Mosquitto both active; HA reachable on the LAN
(`200`); `pi-maintenance-check.timer` survived the Docker daemon restart
and re-armed correctly for its next monthly run (2026-09-01); a fresh
manual run of `pi-maintenance-check.py` reports **"Nothing pending."**

**Real gap surfaced, not yet closed:** there's no automated check that
confirms a *scheduled* reboot (like the one that already quietly fixed the
kernel on 2026-08-10, or the next one on 2026-08-17) actually came back
healthy — the existing watchdog/heartbeat system covers MQTT/Node-RED/
log-server silence, but nothing watches Docker/container health
specifically post-reboot. Discussed live; no card opened yet for a real
automated version — next scheduled reboot (2026-08-17) should at least get
a manual spot-check (`docker ps`, `systemctl is-active nodered mosquitto`,
dashboard heartbeats, HA reachability, `pi-maintenance-check.py`) using the
same commands this resolution used.

**Related:** CARD-0125 (the check that surfaced this and applied the routine batch), CARD-0095 (the M8 sibling — this is the exact sequence already proven there tonight, just not yet safe to run remotely on the Pi), CARD-0096 (the precedent for the "wait until home" block and its reasoning).

---

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 6109B, over the 5000B size threshold.

### CARD-0126 · [enhancement] [maintenance] Container-image update visibility for floating-tag services (NetAlertX, HA, Caddy, cloudflared)
**Status:** Done

**Notes:** Raised 2026-07-31, surfaced while explaining CARD-0095's monthly maintenance cycle to Joseph. Immich already has real update visibility — `components/photo-server/immich-update-check.py` compares actual version numbers via Immich's own API and notifies on the log dashboard, notify-only, no auto-apply. Everything else running in Docker across the stack has none at all:

| Component | Image tag | Update visibility |
|---|---|---|
| NetAlertX | `:latest` | None |
| Home Assistant | `:stable` | None |
| hike-izer-web (Caddy) | `:2-alpine` | None |
| cloudflared | `:latest` | None |
| Immich Postgres, Valkey/Redis | pinned by SHA256 digest | Deliberately fixed — no drift, but also no visibility into new upstream digests |

None of the floating-tag services have any check for "is a newer image available." If `docker compose pull` never runs for one of them, it silently stays on whatever was first deployed indefinitely, with no signal either way — the same "invisible until it matters" shape as CARD-0095's original apt backlog, just at the container-image layer instead of the OS layer.

**Not yet scoped — needs a Planning-stage interview before Build**, since there are several genuinely different viable approaches, not one obvious path the way CARD-0125 (its Pi-side OS sibling) is:
1. Compare the locally-running image's digest against the registry's current digest for that tag (`docker manifest inspect` or the registry API directly) — works regardless of whether a project uses real version tags, and catches "latest moved" even though the tag string itself never changes.
2. A dedicated purpose-built tool (Watchtower, diun) — more infrastructure to run, but designed exactly for this rather than a custom script per service.
3. Per-service, where a project publishes real version/release info (the way Immich does) — mirror `immich-update-check.py`'s pattern directly instead of a generic digest diff.

Also worth clarifying at Planning time: is the actual goal *detection* (know when something's outdated, still human-decides-when-to-pull, consistent with every other check in this repo), or is repeatedly re-pulling a `:latest` tag already an implicit form of auto-update in spirit — in which case the real gap might be *visibility into what changed and when*, not detection of staleness. Worth deciding before choosing an approach, since it changes which of the three options above actually fits.

**Resolved 2026-07-31 ~15:50 MST (Planning) — a fourth option, better than all three above:** none of digest-comparison, Watchtower/diun, or per-service custom APIs. NetAlertX, Home Assistant, Caddy, and cloudflared are all open-source projects hosted on GitHub with real published releases — **`GET /repos/{owner}/{repo}/releases/latest`** is one consistent, generic mechanism (unlike per-service APIs) that still gives a real version number (unlike a bare digest diff). Confirmed live before committing to it: all four containers carry an `org.opencontainers.image.source` label pointing at a real repo, and current version is determinable either from the matching `.image.version` label (NetAlertX, Caddy, HA) or, for cloudflared which sets `source` but not `version`, by exec-ing the binary's own `--version` flag inside the container. Goal is *detection*, not auto-pull — same notify-only policy as every other check in this repo.

**Built and verified live, 2026-07-31 ~16:00 MST:**
- New `core/maintenance/container_update_check.py` (shared, generic — takes a `SERVICES` list) plus two thin per-host wrappers: `components/photo-server/container-update-check.py` (M8: NetAlertX, Caddy, cloudflared) and `core/homeassistant/container-update-check.py` (Pi: Home Assistant). Same shared-module pattern as `open_kanban_pr.py`.
- **Real bug caught and fixed during the very first live run**: Caddy's own `org.opencontainers.image.source` label points at `caddyserver/caddy-docker` — confirmed via a direct API call that this repo has **no releases at all** (404), it's just the Dockerfile-packaging repo. The real releases (matching the running version's own label exactly) live at `caddyserver/caddy`. Fixed by hardcoding the correct source for Caddy specifically rather than trusting the label blindly; NetAlertX and cloudflared's labels were confirmed correct as-is.
- Deployed and enabled on both hosts, daily 6:30 AM (added to `jctsh-network.md`'s maintenance table). Verified: M8 correctly reports all three services up to date (`Nothing pending`) after the Caddy fix; the Pi found a **real, non-synthetic finding** — Home Assistant `2026.7.4` available, running `2026.5.1`.
- **Wired into CARD-0128's PR pipeline too** (Joseph's call, same session) — both wrappers now call `open_finding_pr()` exactly like the OS-level maintenance checks, using a `_pr` sub-key in their own state file (distinct from the per-service throttle keys) to track the dedup PR. Verified live against the real HA finding: **[PR #3](https://github.com/joscthomas/jctsh/pull/3)** opened correctly with a `CARD-XXX` placeholder stub, same design as CARD-0128's own fix.
- **Promoted to a repo-wide standard**: `JCTsh-Build-Standards.md` §9.7 (v1.17) — this pattern (verify the source label's repo actually has releases before trusting it, version from label or binary exec, normalize tag formats, notify-only) is now documented for any future Docker-based component, not just these four.

**Related:** CARD-0095 (M8 OS/firmware maintenance — the parallel problem this mirrors at the image layer, and the policy precedent: notify-only, never auto-apply), CARD-0125 (Pi's OS-layer sibling), CARD-0128 (the PR pipeline this now feeds into), `components/photo-server/immich-update-check.py` (the pre-existing precedent for project-specific version APIs — still the right tool when a project has its own, per §9.7's "not this pattern" note), `JCTsh-Build-Standards.md` §9.7 (the promoted standard).

---

