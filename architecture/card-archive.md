# architecture — Card Archive

Historical record of archived Done/Defer kanban cards for this component (CARD-0193). Not read as part of routine Session Start or component/cluster-session startup (JCTsh-Component-Session-Start.md) -- on-demand lookup only. See this component's own CLAUDE.md for current, curated context.

## Card History

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3263B, over the 2000B size threshold.

### CARD-0223 · [enhancement] [architecture] Standalone LiPo battery charging station (TP4056) — RESOLVED 2026-09-10
**Status:** Done

**Raised 2026-08-28 (Joseph), during CARD-0198's extended air-quality-monitor bench session** — needed a way to charge/top-off spare LiPo cells without disturbing whatever device's circuit a cell happens to be wired into at the time.

**Interviewed 2026-08-28 — essence only, per this project's own new-card convention:**
- **Purpose:** charge spare/backup LiPo cells independently, not integrated into any one device's own build — a shared bench tool, not tied to a specific component.
- **Scope:** one battery at a time, sized for the same EEMB 1100mAh cells (Bag 7) already standardized on across this project's battery-powered builds (hiking-monitor, air-quality-monitor).
- **Form factor:** bare breadboard/perfboard — functional, no enclosure. Consistent with this being a bench tool, not a field-deployed device.
- **Parts availability confirmed, no ordering needed:** TP4056 Battery Charger Modules (`jctsh-parts-inventory.md`, Bin A4) — 5 on hand, spares available beyond what's already wired into existing device builds.

**Wiring plan, 2026-08-28 — a genuinely minimal, two-connection build:**
1. **Battery → the module's `BAT+`/`BAT-` pads.** Verify polarity with a multimeter before connecting — same standard precaution used before any first LiPo connection elsewhere in this project.
2. **USB power → the module's own onboard USB port.** Plug in from a wall adapter or PC — no wiring needed, the module has its own connector.

Everything else stays unconnected:
- **`IN+`/`IN-` breakout pads** — not needed; an alternate input path for hardwired/solar sources, unused since the module's own onboard USB jack is doing that job directly.
- **`OUT+`/`OUT-` (boost output)** — leave fully unconnected. That's the boosted-voltage output for powering a downstream device, which this standalone charger doesn't have — same "only the charging half of the module is used" principle as air-quality-monitor's own build.

Once wired, the module's own onboard LED indicates charge status (charging vs. done) — standard TP4056 behavior, no additional components needed for that.

**Open item before Build, resolved:** the EEMB cell used has a JST connector, matching the original wiring plan — no bare-lead handling needed.

**Built and verified live, 2026-09-10.** Standalone TP4056 charging station wired per the plan above (battery on `BAT+`/`BAT-` via JST, USB power into the module's onboard port, `IN+`/`IN-` and `OUT+`/`OUT-` left unconnected). A real EEMB 1100mAh cell was charged start to finish on it, confirmed via the module's own onboard LED going from charging to done.

**Done when:** a standalone TP4056 charging circuit is built (perfboard/breadboard, USB-powered, JST connector for the battery), and verified live by actually charging a real EEMB 1100mAh cell from a partial charge to full (TP4056's own onboard LED indicates charge status/completion, per its standard behavior) — not just wired and assumed to work. **Met.**

**Related:** `jctsh-parts-inventory.md` (TP4056 modules, Bin A4; EEMB LiPo cells, Bag 7), CARD-0198 (the session this need surfaced during).

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 4388B, over the 2000B size threshold.

### CARD-0213 · [enhancement] [architecture] Quantified peak-current headroom standard for battery-powered builds — RESOLVED 2026-08-25
**Status:** Done

**Raised 2026-08-25 (Joseph)**, stepping back after two separate same-night incidents (CARD-0198's air-quality-monitor brownout investigation, CARD-0211's hiking-monitor reset loop) hit the identical underlying physics: a WiFi TX/association current spike (100s of mA, millisecond-scale) landing on a battery+regulator chain without enough peak headroom, sagging the rail below the ESP32's brownout threshold. Asked directly: why does this keep happening, is it common, and what does a genuinely robust design look like — scoped as a **general JCTsh reference standard** (not just a fix for these two devices), since the same physics will hit every future battery-powered build.

**Existing `JCTsh-Build-Standards.md` §2.14 already covers cell protection (point 1), a low-battery firmware cutoff (point 2), charging safety (point 3), and a qualitative LDO-vs-boost preference (point 7) — but has no quantified rule for how much current headroom a regulator needs against real transient loads, and no bulk-capacitance guidance at all.** air-quality-monitor's MCP1700 (250mA rated) turned out marginal against WiFi+SEN55 combined; hiking-monitor's boost converter was directly measured (CARD-0026) brownout-looping under a 100-250mA WiFi burst on a rig, a mechanism now suspected to have hit the real field device for the first time today (CARD-0211).

**Scope:** write a new, numbers-grounded point in §2.14 covering:
1. **Regulator current rating margin** — size for the peak coincident load (WiFi spike + any active peripheral + baseline draw), not the average/idle draw. A rule of thumb multiplier (e.g. 2-3x), grounded in CARD-0026's real measured WiFi-burst range (100-250mA on this exact hardware) and tonight's SEN55 (~63mA) and boost-quiescent (22.6mA) numbers, not an abstract guess.
2. **Bulk capacitance at the point of load** — a real minimum value (electrolytic + ceramic combination) for absorbing millisecond-scale transients, explicitly framed as a complement to adequate regulator headroom, not a substitute for it (a cap can't manufacture sustained current a regulator can't supply).
3. **Extend point 2's low-battery cutoff to cover WiFi-burst operations specifically**, not just continuous field/logging operation — closing the exact gap CARD-0211/CARD-0212 found (hiking-monitor's cutoff protected the hike loop but not the upload-mode replay burst).
4. **Sequence current-hungry startup operations in firmware** — don't let WiFi association and a peripheral's own power-up coincide; generalize the pattern air-quality-monitor's SEN55-idle-during-boot logic already uses.

**Done when:** §2.14 has a new point with concrete numbers (not just qualitative preference) covering all four items above, cross-referenced from both CARD-0198 and CARD-0211/CARD-0212.

**Standard written, 2026-08-25 — `JCTsh-Build-Standards.md` bumped to v1.22.** All four scope items addressed:
1. Regulator peak-current headroom — new §2.14 point 9, 2-3x the coincident peak load, grounded in CARD-0026's real measured 109-154mA WiFi-burst current on hiking-monitor's own hardware plus tonight's SEN55 (~63mA) and boost-quiescent (22.6mA) numbers.
2. Bulk capacitance at the point of load — same point 9, a real minimum (few hundred µF electrolytic + small ceramic) explicitly framed as a complement to headroom, not a substitute — noting tonight's own finding that a bulk cap alone didn't reliably fix an undersized regulator.
3. Low-battery cutoff extended to WiFi-burst operations — point 2 amended directly, citing CARD-0211/CARD-0212's exact gap (hike-loop cutoff existed, replay-burst cutoff didn't).
4. Firmware sequencing of current-hungry startup operations — new §2.14 point 10, generalizing air-quality-monitor's SEN55-idle-during-boot pattern.

**Done.**

**Related:** CARD-0198 (air-quality-monitor's own brownout investigation, the immediate trigger), CARD-0211/CARD-0212 (hiking-monitor's matching incident, same night), CARD-0026 (the real measured WiFi-burst current numbers this standard is grounded in), CARD-0070 (the deferred hardware-side fix for hiking-monitor specifically — this card is the general standard, not a replacement for actually applying it to either device).

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3592B, over the 2000B size threshold.

### CARD-0167 · [enhancement] [architecture] Close CARD-0096's mDNS transition-window aliases — RESOLVED 2026-08-17 12:11 MST
**Status:** Done

**Raised 2026-08-14 16:15 MST**, split out from CARD-0096 (Done) so this last step doesn't get lost inside an already-closed card. Two systemd units are still deliberately running: `raspberrypi-mdns-alias.service` (Pi) and `photo-server-mdns-alias.service` (M8), each publishing the old hostname as a static mDNS alias for the unchanged real IP, per CARD-0096's own transition-window design.

**Due date reasoning:** 2026-08-17 (Monday) 09:00 MST — chosen specifically so both hosts' weekly scheduled reboots (Pi Mon 3:00 AM, M8 Mon 4:00 AM — `network/jctsh-network.md`) happen first. A clean reboot survival is a real stability test, not just elapsed time — if anything were silently still depending on the old name in a way the alias masks, a reboot is exactly the kind of event likely to surface it. 09:00 gives buffer after both.

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

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3405B, over the 2000B size threshold.

### CARD-0102 · [investigation] [architecture] Audit: what else breaks when the Pi/M8 weekly scheduled reboots discard in-flight state — RESOLVED 2026-07-27
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

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 4895B, over the 2000B size threshold.

### CARD-0050 · [idea] [architecture] Network segmentation to contain a compromised/hostile device on home WiFi
**Status:** Defer

**Priority: low (deprioritized 2026-07-10) — accepted as a residual risk, not offloaded onto CARD-0003.**

**Notes:** Raised 2026-07-10 during CARD-0003 (MQTT TLS) discussion. WPA2/3-Personal on `JCTnet1` only protects the radio hop and doesn't stop a device that's already authenticated on the LAN — anyone holding the shared PSK can capture another client's handshake and derive its session key, and more practically, any device on the same `192.168.1.x` subnet can ARP-spoof to MITM traffic between other devices, bypassing WiFi encryption entirely since that attack happens at L2/L3, not over the air. Right now there's no segmentation at all — every JCTsh device, guest device, and IoT gadget shares one flat subnet, confirmed via `network/jctsh-network.md` and `jctsh-security-hardening.md` (no VLAN/isolation findings from CARD-0022/0023's audit). Note HA's existing HTTPS proxy (nginx on 443, cert for `raspberrypi.tailfe828a.ts.net`) is Tailscale-only — it doesn't protect LAN-side access today (cert error on direct LAN hit).

**Original proposed fix (not pursued — see Decision below):** put IoT/guest devices (SmartThings-paired gadgets, guest phones, anything not a trusted JCTsh host) on the router's built-in IoT/guest network with client isolation enabled, so they're on a separate broadcast domain and can't reach or ARP-spoof JCTsh devices (Pi, ESP32s, M8) at all. Router is a TP-Link Archer AXE75 (`network/jctsh-network.md`).

**Decision (2026-07-10) — deprioritized, not executed:** scoping this out surfaced that the original framing no longer fits current reality:
- Guest phones already have their own separate network (existing Guest network, confirmed by Joseph) — the original guest-phone isolation target is already handled.
- Joseph decided Ring, Ecobee, and Google Cast devices (Chromecast, Google TV, Google Home speakers, Nest Display, Pixel Tablet) should stay on the main network — moving them risks breaking phone-to-device casting (mDNS/SSDP needs same subnet), and their actual access pattern (Ring app, Ecobee app, SmartThings/Google Home integration) is cloud-to-cloud, not LAN-dependent, so isolating them buys little anyway.
- The remaining alternative — inverting the approach to isolate the JCTsh devices themselves instead — was scoped and rejected: real, certain ongoing costs (re-IP the whole fleet in `network/jctsh-network.md`, update every ESPHome `secrets.yaml` MQTT broker address, update the DuckDNS port-forward target, lose casual LAN access to photo-server's web UI for Joseph/Robin, and require Joseph's laptop to temporarily join that network for every future OTA reflash) against a threat that's low-probability and low-consequence given the hardening already completed in CARD-0022/0023 (SSH key-only auth, HA TOTP MFA, Node-RED adminAuth, router admin password rotation, UPnP disabled).
- Router capability is also limited: TP-Link Archer AXE75 has no VLAN support, and community reports (TP-Link forums) flag its Guest/IoT-network client isolation as sometimes leaky — any attempt would need empirical verification before being trusted, on top of the migration cost.

**Risk analysis:** getting a hostile device onto `JCTnet1` at all requires either cracking a strong WPA2/3 PSK or a real exploited vulnerability in an existing IoT device — uncommon for a non-targeted residential home. Even if achieved, the highest-value JCTsh surfaces (SSH, HA, Node-RED) are already independently hardened (key-only auth, TOTP MFA, adminAuth). The only real remaining exposure is cleartext MQTT sensor telemetry on the LAN — low-stakes (salt %, temp, garage presence; the garage door itself is actuated via a Zigbee switch through SmartThings, not exposed via this MQTT path). Low probability × low consequence doesn't justify the migration cost, on its own — independent of CARD-0003.

**Relationship to CARD-0003 (corrected 2026-07-10):** these are NOT substitutes for each other, despite both touching MQTT/network security. CARD-0003 (TLS on 8883) only covers the *internet-exposed* path used by roaming devices (hiking-monitor, air-quality-monitor) — it deliberately leaves LAN-local port 1883 traffic in plaintext for stationary devices (see `CLAUDE.md` "LAN security": "Acceptable for a home network; no mitigation planned"). CARD-0050 was about a different threat — an already-on-LAN attacker sniffing/spoofing that same plaintext 1883 traffic — which CARD-0003 does nothing for. CARD-0050 is deprioritized on its own risk-analysis merits above, not because CARD-0003 covers it. Revisit CARD-0050 only if a future router/hardware upgrade makes real VLAN segmentation available, or if the device inventory or threat picture changes such that the cost/benefit shifts.

---
