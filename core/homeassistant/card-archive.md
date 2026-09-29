# core/homeassistant — Card Archive

Historical record of archived Done/Defer kanban cards for this component (CARD-0193's archiving process, migrated to this dedicated file by CARD-0290 — previously these were appended directly into `CLAUDE.md`, which grew unboundedly and stopped being practical to read in full). **Not read as part of routine Session Start or component-session startup** (`JCTsh-Component-Session-Start.md`) — on-demand lookup only. See this component's own `CLAUDE.md` for current, curated context.

---

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 6781B, over the 5000B size threshold.

### CARD-0152 · [enhancement] [homeassistant] Expose Samsung Groom TV as its own HA device
**Status:** Done

**Raised 2026-08-12, follow-up from CARD-0150.** While closing out CARD-0150 (Traveling Mode TV alert), Joseph asked whether the Samsung TV should also be exposed as its own HA device rather than relying on the Chromecast (`media_player.groom_tv`) as a power-state proxy. Checked at the time: the TV is **not** registered in Joseph's SmartThings account, so the low-effort "enable exposure on the existing SmartThings integration" path (same pattern used for the salt-sensor switches) isn't available — the only route is HA's native Samsung TV integration (WebSocket, added by IP address, requiring a one-time pairing prompt accepted directly on the TV).

**Interviewed:** two motivations, both wanted —
1. **More reliable signal.** The Chromecast entity has proven noisy for alerting purposes during CARD-0150's testing: it churns through `playing`/`idle`/`paused`/`buffering` constantly during real use, and was directly observed dropping to `unavailable` for ~67s during confirmed active use (a Cast-protocol connectivity blip, not a real power change) — CARD-0150's automation had to build a delay-then-recheck debounce specifically to tolerate this. A direct TV entity should give a cleaner, more authoritative on/off signal.
2. **Remote control from HA.** Right now, CARD-0150's alert only notifies Joseph, who has to go turn the TV off himself via Google Home. Joseph wants HA to be able to actually turn the TV off itself when it detects an unexpected-on event, not just notify.

**Pairing readiness confirmed:** Joseph is ready to do the on-TV pairing step (physically at the TV with the remote) whenever this gets built — not a blocker.

**Open design questions for Planning:**
- Does the new TV entity **replace** `media_player.groom_tv` as CARD-0150's alert trigger, or does it supplement it (e.g. cross-check both before alerting)? Leans toward replace, given the whole point is a cleaner signal, but worth confirming once the new entity's real behavior is seen firsthand — no guarantee the native Samsung TV integration is itself perfectly clean (worth the same live-testing rigor CARD-0150 needed).
- Auto-remediation behavior: should the automation turn the TV off **immediately** on detecting an unexpected-on event, after some delay/confirmation, or still leave it as a manual step Joseph takes after the notification? This is a real behavior change from CARD-0150's notify-only design and needs a decision, not just an assumption.
- Does turning the TV off via the new integration also need to go through the same debounce/settle logic CARD-0150 built, or does a direct TV entity avoid that problem entirely (unknown until it's actually tested live)?

**Built 2026-08-12:** two integrations ended up involved, not one —
1. HA had already auto-discovered the TV via SSDP as a `dlna_dmr` (DLNA Digital Media Renderer) entry; Joseph enabled it, creating `media_player.tv_samsung_7_series_75`. Checked in the UI: playback controls only (play/pause/volume), no power control — DLNA doesn't expose that.
2. Added HA's native **Samsung Smart TV** (WebSocket) integration separately, manually, via IP (`192.168.1.152`) — Joseph completed the one-time pairing prompt on the TV itself. Created `media_player.tv_samsung_7_series_75_2` (the `_2` suffix is auto-generated, from the object-id collision with the DLNA entity above) and `remote.tv_samsung_7_series_75`. Confirmed via the recorder DB: reports a clean, plain `on` state — no playing/idle/paused churn like the Chromecast. Confirmed in the UI: has a real power/turn-off button, unlike the DLNA entity.

**Scope changed on Joseph's second thought, same session: CARD-0150's automation is staying exactly as it is — not wired to either new entity.** Reason: `media_player.groom_tv` (the Chromecast) also controls the AVR, a relationship the new Samsung TV entity doesn't capture — switching the trigger over would lose that. `core/homeassistant/automations.yaml` was not touched. Both new entities now exist in HA (confirmed working, on/off signal validated, turn-off capability confirmed) but aren't consumed by any automation yet.

**Done when:** revised down from the original scope — the TV is exposed as its own HA device with a working on/off signal and turn-off control, both confirmed for real (not just "added without errors"). **Met.** The CARD-0150 integration work (trigger swap, auto-remediation) is explicitly out of scope now per Joseph's call above; revisit under a fresh card if the Chromecast/AVR relationship is later understood well enough to combine both signals safely.

**Follow-up, same session:** the Samsung Smart TV integration's config entry pins a fixed IP (`192.168.1.152`) and MAC (`84:c0:ef:d8:5f:fb`) with no DHCP reservation on the router yet — if the TV's IP changes, the integration breaks silently. Joseph asked to reserve it; needs to be done on the router admin UI (`192.168.1.1`, TP-Link Archer AXE75) directly, no access to that from this session. Once reserved, add the entry to `jctsh-network.md` alongside the other reserved devices.

**Joseph also added the Denon AVR-X6400H to HA, same session** — auto-discovered via SSDP (`denonavr` integration), entity `media_player.avr`, confirmed reporting a clean plain `on` state like the new Samsung TV entity. This is the same AVR referenced in the "leave the automation alone" decision above (the Chromecast controls it). Same DHCP-reservation gap applies: fixed IP `192.168.1.204`, MAC `00:05:cd:e4:58:3e` (pulled from the Pi's ARP cache, since `denonavr` doesn't populate MAC into HA's device registry) — needs reserving on the router alongside the TV's.

**Both reserved on the router and recorded in `jctsh-network.md`, same session.** No longer a loose end.

**Closed out 2026-08-12 on Joseph's go-ahead.** Scope ended up smaller than raised — the TV is exposed and both new entities (playback via DLNA, real on/off + power control via the native Samsung Smart TV integration) are confirmed working for real, but per Joseph's own call mid-build, none of it got wired into CARD-0150's alert automation, since the Chromecast already captures the TV+AVR relationship as a single signal and switching away from it would lose that. Both the TV and the newly-added Denon AVR are DHCP-reserved and documented in `jctsh-network.md`. Reopens under a fresh card if the Chromecast/AVR relationship is ever understood well enough to safely combine signals, or if either new entity turns out to need its own live-testing rigor the way CARD-0150's did.

**Related:** CARD-0150 (the TV alert automation this was originally meant to extend, ultimately left untouched), `jctsh-network.md`.

---

**Archived from `tos/kanban-board.md` on 2026-09-10 (CARD-0193)** — 7094B, over the 5000B size threshold.

### CARD-0240 · [enhancement] [homeassistant] Home Assistant container update available: 2026.9.0 → 2026.9.1 — RESOLVED 2026-09-05 13:47 MST

**Status:** Done

**Raised via automated maintenance finding (PR #64, jctsh-core), 2026-09-05** — routine container-version-bump finding from the scheduled maintenance check.

**Interviewed 2026-09-05.** Same scope as CARD-0233/CARD-0236 through CARD-0238: evaluate first, decide whether to update, then apply and verify live in this same card — not a bare decision-only record.

**2026.9.1's own release notes checked** (`gh release view 2026.9.1 --repo home-assistant/core`) — 28 items, entirely small per-integration bug fixes and dependency bumps for integrations this instance doesn't use (SMTP, backup, Miele, Roborock, Vizio, Amber Electric, UniFi Protect, device registry, Daikin, Besen, orjson, Flo, serial, Environment Canada, Hot Spring, KNX, MotionEye, Tradfri, frontend, Reolink, LitterRobot). Nothing touching MQTT, SmartThings, Google, or the recorder — the pieces this instance actually depends on per `CLAUDE.md` ("Home Assistant is the bridge to SmartThings — there is no other path"). **Decision: safe to update.**

**Plan:**
1. Bump the image tag in `core/homeassistant/docker-compose.yml` (or confirm it already tracks `:stable` and just pull fresh).
2. `docker compose pull && docker compose up -d` on the Pi.
3. Verify live: `/api/config` reports `2026.9.1`, Docker health check `healthy`, SmartThings-domain entities still present/responding, no new MQTT/recorder errors in `docker logs`.

**Executed and verified live, 2026-09-05 13:47 MST.** `docker-compose.yml` already tracked `:stable` — no file change needed, just `docker compose pull && docker compose up -d` on the Pi. **Real complication, not a routine bump:** this Pi has only 905MB total RAM and is chronically swap-constrained (599MB swap in use, ~70% iowait observed mid-pull) — the same slow-USB2.0-drive pattern CARD-0233 already documented, this time compounded by memory pressure. The pull/extract took **~67 minutes** (vs. a normal few-minute bump), genuinely progressing the whole time (confirmed via live disk-I/O and log-freshness checks, not just assumed) — no outage during that window, the old container stayed `Up`/`healthy` until the new one was ready to swap in.

**All four verification points confirmed live:**
- Version: `2026.9.1` via `/api/config`.
- Docker health check: `Up 4 minutes (healthy)`.
- SmartThings: 8 `smartthings`-domain entities present, none in the unavailable list.
- JCTsh MQTT/ESPHome entities spot-checked (garage-radar, salt-sensor, front-porch-temp-sensor) — all reporting live real values, not stale/unavailable.
- No new MQTT or recorder errors: recorder logged one expected "not shutdown cleanly" warning from the forced container restart, self-healed immediately (`Ended unfinished session`) — not a real error. Bluetooth `NET_ADMIN` errors are the same already-documented longstanding non-issue (this file, `~line 2697`). A handful of one-time `firebase_messaging` push-notification errors logged right at startup, no recurrence since.

**Real finding, investigated and mostly resolved live, 2026-09-05 (Joseph's hypothesis, confirmed correct):** immediately post-update, 203 entities were `unavailable` instance-wide. Joseph's read — the SmartThings/Ring cloud integrations likely needed a reload after the forced container restart, not a real device problem — was confirmed exactly right: `POST /api/config/config_entries/entry/<id>/reload` for both `smartthings` (`01KTC1XQWRG3B0R72110KFBJJA`) and `ring` (`01M0BKP9RTZ8BJE9XMZXESD5KF`) via the HA REST API (both had reported `state: loaded` despite the stale entities — a reload still forced a fresh re-sync) brought the count from **203 down to 53**, confirmed via a live `/api/states` recheck. The remaining 53 are SmartThings-hub-bridged Zigbee/Z-Wave devices (`side_yard`, `patio_door`, `guest_lamp`, several seasonal "peanut" switches, a smoke detector) — physical hub-to-device mesh connectivity, which an HA-side integration reload can't reach, consistent with genuinely offline/battery/seasonal devices rather than anything this update broke. The two automation entities CARD-0233 already flagged as pre-existing stale registry leftovers (`Traveling Lights - Night Off`, `CARD-0158 - Reboot Health Check Reminder`) are unaffected either way (reloads don't touch automations). No pre-update entity snapshot exists, so the original 203 can't be proven identical to CARD-0233's own finding, but the release notes touching nothing Ring/SmartThings-related plus the clean reload recovery both point the same direction: not a regression from 2026.9.1. Joseph's call: leave the remaining 53 as-is, no separate cleanup card.

**Done when:** the update is applied and all four verification points above are confirmed live — not just that the container restarted. **Met.**

**Durable lesson captured, 2026-09-05 (Joseph's call — folded into this card rather than a separate one).** Added a standing "Post-update entity-availability check" to `CLAUDE.md`'s Home Assistant Docker Setup section: after any future `docker compose up -d`/recreate, check `/api/states` for unavailable entities, and if any are SmartThings/Ring-domain, reload those config entries via the HA REST API (`POST /api/config/config_entries/entry/<id>/reload`) before assuming a real device problem — a `state: loaded` config entry doesn't guarantee it actually resynced after a restart. This makes the reload step part of every future HA-update card's own verification checklist (CARD-0233/CARD-0236 through CARD-0240's repeating pattern), not something to rediscover next time.

**Generalized 2026-09-06, prompted by Joseph asking about `samsungtv` specifically.** Checked: `samsungtv` (`Samsung 7 Series (75)`, entry_id `01KZVHJT8CHBD6TA60FMF6676R`) appeared in this same update's own "Waiting for integrations to complete setup" boot-log line alongside `smartthings`/`ring` — confirming this is a **generic HA behavior** (any config entry can report `loaded` without having actually resynced), not something specific to the two integrations first found. `CLAUDE.md`'s check rewritten accordingly: look at the boot log's slow-loading list for *whichever* integrations are named, not a fixed SmartThings/Ring pair. `samsungtv` happened to be healthy at check time (no reload needed), but the mechanism is confirmed to apply identically. Separately noticed, unrelated to this card: a duplicate `media_player.tv_samsung_7_series_75_2` entity exists — same "_2" legacy-duplicate pattern already known for Ring, likely pre-existing, not investigated further here.

**Related:** `CLAUDE.md` (Home Assistant Docker Setup section, `core/homeassistant/docker-compose.yml` — now also the post-update entity-availability check this card added), CARD-0233/CARD-0236/CARD-0237/CARD-0238 (the identical routine-update pattern this repeats, including CARD-0233's own precedent for the two stale automation entities and the slow-USB2.0-drive pull behavior).

---

**Archived from `tos/kanban-board.md` on 2026-09-10 (CARD-0193)** — 5684B, over the 5000B size threshold.

### CARD-0233 · [enhancement] [homeassistant] Home Assistant container update available: 2026.8.2 → 2026.8.3 (landed on 2026.9.0) — RESOLVED 2026-09-02
**Status:** Done

**Raised via automated maintenance finding (PR #44, jctsh-core), 2026-08-29** — routine container-version-bump finding from the scheduled maintenance check.

**Interviewed 2026-08-29.** Joseph's call on scope: **evaluate first, decide whether to update** — this card's "done" is the decision + reasoning, not necessarily the update itself (that may follow as a separate step once decided). No particular concern flagged for this specific bump — routine patch update, not prompted by any known issue.

**Standard care warranted regardless of "no particular concern":** HA is the sole bridge to SmartThings → Google Home/Pixels/voice control per `CLAUDE.md` ("there is no other path") — any HA update carries real downstream blast radius if it breaks that integration, even a routine-looking patch bump.

**Plan:**
1. Read 2026.8.3's release notes (Home Assistant's own release blog / changelog) for breaking changes, deprecations, or anything touching MQTT, the SmartThings/Google integration, or the recorder — the pieces this instance actually depends on.
2. Decide: update now, or hold and note why (e.g. a flagged breaking change, or simply "nothing notable, safe to update on next convenient window").
3. If updating: bump the image tag in `core/homeassistant/docker-compose.yml`, `docker compose pull && docker compose up -d`, verify live — HA reachable, SmartThings-bridged entities still responding, no new recorder/MQTT errors in `docker logs`.

**2026.8.3's own release notes checked** (`gh release view 2026.8.3 --repo home-assistant/core`) — entirely small per-integration bug fixes and dependency bumps for integrations this instance doesn't use (Sonos, Supla, Shelly, Ecovacs, Overkiz, Vizio, Reolink, Enphase, Volvo, LG webOS TV). Nothing touching MQTT, SmartThings, Google, or the recorder. Decision: safe to update.

**Real-world execution turned into a much longer story than a routine bump, across several real problems, each found and fixed live rather than assumed away:**
1. **First attempt failed silently overnight.** A plain inline `ssh pi1.local "docker compose pull && up -d"`, left running unattended via the autonomous loop, had its SSH connection reset mid-extraction (`client_loop: send disconnect: Connection reset by peer`) — the remote command died with it (no `nohup`/session persistence). Checked the actual live state afterward: HA was untouched, still on 2026.8.2, no harm done — a Pi reboot in between just restarted the old image via `restart: unless-stopped`. See the general lesson saved from this (long SSH commands need `nohup`/persistence to survive a dropped connection).
2. **Retried properly (`nohup ... & disown`, detached)** — genuinely survived this time, but the image itself was very slow to pull/extract on this specific host: Docker's data root (`/mnt/jctsh-logs/docker`) turned out to be on a USB-attached SanDisk Cruzer flash drive over **USB 2.0** (confirmed via `lsusb`/link-speed check, 480 Mbps ceiling) — not the SD card, an assumption stated out loud and self-corrected once actually checked. Slow but genuinely progressing the whole time, not stalled.
3. **The `docker compose up -d` step itself then failed**, once the (very slow) pull finally finished: `"cannot stop container: ... tried to kill container, but did not receive an exit event"`. The old container was left in a broken/zombie state — `docker exec` into it failed (`error executing setns process`), and HA was genuinely unreachable (`curl localhost:8123` connection-refused), a real live outage, not just a stalled update. Root-caused enough to recover: retried `docker compose up -d homeassistant` (image already pulled, so fast) — this time it stopped/removed the broken container cleanly and started a fresh one.
4. **Landed on a different version than originally vetted.** By the time the retry succeeded, `:stable` had moved forward again during the extended delay — the container came up on **2026.9.0**, a full minor version past the 2026.8.3 originally checked. Re-checked *that* release's real breaking changes before calling this done (a minor bump can carry more than a patch release): Flexit Nordic/KNX/UniFi Protect/Vacuum/Z-Wave JS changes, none of which are integrations this instance uses; MQTT's only change was an additive settings-page UI feature; no recorder or Google/SmartThings changes at all. Clean.
5. **Cosmetic cleanup:** the recovery left the container named `26519c2de4d1_homeassistant` (an artifact of Compose's interrupted rename-swap) instead of the compose file's intended `homeassistant` — renamed back via `docker rename`, confirmed still healthy/reachable afterward.

**Verified live, final state:** `homeassistant` container `Up` and `(healthy)`, `curl http://localhost:8123/manifest.json` returns 200, running **2026.9.0**.

**Done when:** the release notes have been read and a decision recorded, and if updating, it's verified live — **met**, through a materially harder path than the original routine-bump framing expected.

**Related:** `CLAUDE.md` (Home Assistant Docker Setup section, `core/homeassistant/docker-compose.yml`; "Home Assistant is the bridge to SmartThings — there is no other path"), CARD-0153 (a separate, unrelated HA-infrastructure discussion — recorder database engine — surfaced around the same general area, not a dependency of this card), CARD-0238 (the M8 maintenance work done the same day, same "verify release notes before applying, verify live after" discipline).

---

**Archived from `tos/kanban-board.md` on 2026-09-27 (CARD-0193)** — 8650B, over the 5000B size threshold.

### CARD-0295 · [enhancement] [homeassistant] Home Assistant container update available: 2026.9.2 → 2026.9.3

**Status:** Done -- RESOLVED 2026-09-27 18:07 MST

**Auto-opened 2026-09-18 from jctsh-core's maintenance check (CARD-0128).** Raw finding: `Container image updates: home-assistant: 2026.9.3 available (running 2026.9.2)`.

**Risk assessment, checked 2026-09-18 09:57 MST (corrected 2026-09-22 — written `16:57`, 7h fast via the `TZ=` clock bug, see CARD-0329) against the real upstream release notes (github.com/home-assistant/core/releases/tag/2026.9.3):** patch release, bug-fixes and dependency bumps only — no breaking changes, no database migrations. Notable fixes: EnergyZero market-price regression, Private BLE Device now requires an IRK in its config flow, Bond retains known-host info on repeated zeroconf announcements, Matter/Shelly cover-entity creation when the tilt attribute is null, Nest Climate `turn_on` made idempotent, Spotify reauth crash when a config entry lacks an `id` field, Airthings BLE duplicate device entries from incomplete reads, better DNS/API error handling for Google Tasks and WAQI, onboarding username validation. Dependency bumps: holidays, pylutron, hassil, waterfurnace, aioamazondevices, reolink_aio. Also redacts API keys in debug logs. **None of these touch an integration this install actually depends on** (SmartThings, Ring, MQTT, Matter/Cync, SamsungTV) — low-risk upgrade.

**Deploy per `CLAUDE.md`'s standing Pi rule (CARD-0266/CARD-0268/CARD-0269) — never `docker pull`/`docker compose pull` on this host** (hangs indefinitely on this Pi's Docker 29.6.1 via a confirmed OCI-referrers bug, and risks starving the live container's I/O on the Pi 3B+'s shared USB 2.0 bus):
```bash
sudo pi-image-pull.py ghcr.io/home-assistant/home-assistant:stable --recreate homeassistant
```
Optionally add `--schedule "<time>"` to defer it to the Mon 3 AM reboot window; the deliberate default is still to run it in the foreground and watch it.

**Post-update check required (CARD-0240, generalized):** after the recreate, check `/api/states` for unavailable entities and `docker logs homeassistant` for the `homeassistant.bootstrap` "Waiting for integrations to complete setup" line. Any integration named there is a candidate for a config-entry reload via the HA REST API before investigating real device failure — a config entry can report `state: loaded` without having actually re-synced its entities.

**Done when:** the Pi's `homeassistant` container is running 2026.9.3 (confirmed via the HA UI or `/api/config`), the container reports healthy after the recreate, and the post-update entity-availability check above comes back clean (or any affected integration has been reloaded and confirmed resynced).

**Scheduled run completed successfully -- checked 2026-09-27 18:07 MST.** The transient one-shot unit fired on time and self-removed (as designed) -- confirmed from the dashboard log rather than `systemctl`: `2026-09-27 03:30:05` Image pull starting -> `04:40:51` Image pull complete (4246s -- slow but clean, no stall/kill this time) -> `04:47:35` Container 'homeassistant' recreated and healthy. **Version note:** the container is running **2026.9.4**, not 2026.9.3 -- a newer patch landed upstream between this card's last check and the scheduled run; not re-vetted against 2026.9.4's own release notes before the pull (the schedule was unattended), worth a quick look after the fact but the update already happened.
**Post-update checks, 2026-09-27 18:07 MST:**
- Bootstrap log: no `homeassistant.bootstrap` "Waiting for integrations to complete setup" line -- no candidate integration flagged by CARD-0240's own detector.
- Only recurring error since recreate: the `habluetooth` "Failed to force stop scanner" one, already known and logged as a longstanding non-issue (this file, ~L4098) -- container has no Bluetooth hardware access, unrelated to this update.
- Config entries: 28 total, **27 loaded**, only `bluetooth` in `setup_retry` (the same known non-issue above). `smartthings`, `ring`, `samsungtv`, `matter` all `loaded`.
- Entity comparison against yesterday's saved baseline (1,003 entities / 110 unavailable-or-unknown, CARD-0295's 09-26 attempt): now **1,004 entities / 111 unavailable-or-unknown** -- a net **+1** each way, not the ~150-entity SmartThings/Ring resync spike CARD-0240 originally found on 2026-09-05. Read via the HA token from `/home/pi/.node-red/environment`, inside the remote command only, never printed (Joseph re-authorised this specific read).
- `RestartCount=0`, `OOMKilled=false`.

**Conclusion: update completed successfully, no regression found.** The small unavailable-count delta reads as ordinary noise (a transient sensor at scrape time), not a resync failure, given config entries all report loaded and there's no large-domain spike. Not independently re-verified per-entity (no saved baseline file existed to diff against, only yesterday's two aggregate numbers) -- if anything looks off later, check `smartthings`/`ring` specifically first per CARD-0240.
**Related:** CARD-0266 (the immediately prior HA update, 2026.9.1 → 2026.9.2, same shape), CARD-0269 (`pi-image-pull.py`, the required pull mechanism), CARD-0268 (the I/O-contention rationale behind it), CARD-0240 (the post-update entity-availability check this card inherits), CARD-0128 (the auto-PR intake pipeline this was raised by), `core/homeassistant/docker-compose.yml`.


**Re-notification 2026-09-25 (PR #134, jctsh-core): the same pending 2026.9.2 → 2026.9.3 update, folded into this card rather than landed separately.** Still Backlog, still low risk per the assessment above. **Hold until after Saturday's 2026-09-26 hike (Joseph, 2026-09-25):** HA carries the Sheet-health and watchdog pushes to the Pixel and the hiking-monitor's Replay Hike Log / Restart buttons, and Saturday is the first real test of two firmware changes -- no extra restarts of things the hike depends on. Apply afterwards with `pi-image-pull.py` as above, then the post-update entity-availability check.

**Update attempt 2026-09-26 ~15:50-16:30 MST -- stalled, aborted, HA untouched (Joseph: "apply the updates before the rehearsal, one at a time"; "Option 1, read the token").** Risk re-verified first: upstream latest is still 2026.9.3 (nothing newer); release notes re-read (none of the fixes touch the integrations this install uses); open post-release issues are for Tuya/Hue/Plex/Tibber/Yeelight/Alexa Devices/Deebot and a USB Bluetooth adapter on HAOS -- still low risk. Safeguards taken: rollback tag `ha-rollback:2026.9.2` (image a1bc133af84e) on the Pi; HA entity baseline saved (1,003 entities, 110 already unavailable/unknown -- snapshot buttons, scenes, update entities etc.) using the HA token Joseph authorised reading for this check. `sudo pi-image-pull.py ghcr.io/home-assistant/home-assistant:stable --recreate homeassistant` was run in the foreground; after ~40 min `ctr -n moby content active` showed **no active ingest** (the pull was stuck before downloading; the registry itself is reachable, `ghcr.io/v2/` = 401 in 0.28 s) so the puller was killed. **Nothing changed on the host:** HA stayed on 2026.9.2 throughout, and three API probes (before, during, after) show the same 1,003 entities, 0 newly unavailable. **Finding:** at that moment the Pi was I/O- and memory-starved -- load average ~5.3, **46% iowait, 677 of 905 MB swap in use, ~35 MB free**, `usb-storage` in D state -- exactly the condition CARD-0268/CARD-0269 describe. Next: retry when the Pi is quiet (`--schedule "<Sun/Mon ~03:30>"` per the card) or defer until after the next hike; the Pi's memory/swap pressure is worth its own look (not carded yet).

**Scheduled 2026-09-26 (Joseph: "1" -- schedule it).** `sudo pi-image-pull.py ghcr.io/home-assistant/home-assistant:stable --recreate homeassistant --schedule "2026-09-27 03:30:00"` -> one-shot transient unit `pi-image-pull-home-assistant-stable.timer`, fires **Sun 2026-09-27 03:30 MST**; it logs `Image pull starting/complete/FAILED` and `Container 'homeassistant' recreated and healthy` to the dashboard (FAILED and unhealthy are Alerts). Rollback if it goes wrong: `docker tag ha-rollback:2026.9.2 ghcr.io/home-assistant/home-assistant:stable` then recreate. **Morning-after check (Sunday):** dashboard lines above, `systemctl status`/`journalctl -u pi-image-pull-home-assistant-stable`, HA on 2026.9.3 via `/api/config`, then rerun the entity comparison against the saved baseline (1,003 entities, 110 already unavailable/unknown). If it stalls again the pull just hangs, HA keeps running 2026.9.2, and this card stays open.
---

### CARD-0341 · [bug] [salt-sensor] [homeassistant] `switch.salt_critical_alert` can never stay on -- its `turn_on` action is followed by a `turn_off` that undoes it, and it has no `turn_off` action — RESOLVED 2026-09-25 20:32 MST

Archived in full to `components/salt-sensor/card-archive.md` on 2026-09-27 (CARD-0193) — 10682B, over the 5000B size threshold. Also tagged here; this is a pointer only, not a duplicate.

### CARD-0328 · [enhancement] [mqtt] [node-red] [homeassistant] Version-controlled-copy directories have no drift check — generalize CARD-0326's one-line diff

Archived in full to `core/mqtt/card-archive.md` on 2026-09-27 (CARD-0193) — 19459B, over the 5000B size threshold. Also tagged here; this is a pointer only, not a duplicate.

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 4480B, over the 2000B size threshold.

### CARD-0266 · [enhancement] [homeassistant] Home Assistant update available: 2026.9.1 → 2026.9.2 — RESOLVED 2026-09-14 09:20 MST
**Status:** Done

**Raised via automated maintenance finding (PR #77, jctsh-core), 2026-09-12.** Routine version-bump finding: Home Assistant 2026.9.2 available, running 2026.9.1.

**Evaluated 2026-09-13 — release notes checked, looks safe, not applied yet (Joseph's call — evaluate first, decide separately whether/when to apply).** 2026.9.2 is a patch release, entirely small per-integration bug fixes and dependency bumps (Hive, Roomba, Openhome, WebOS TV, Vizio, Tesla Fleet, Nest, ViCare, UniFi, Reolink, Weheat, MELCloud, Enphase, ZHA, ESPHome-setup robustness, frontend bump). Nothing touching MQTT, the SmartThings integration, the Matter integration/Matter Server (CARD-0262), Google Assistant, or the recorder — the pieces this instance actually depends on.

**Applied 2026-09-14, per Joseph's explicit go-ahead ("apply updates for 266 and 267, let scheduled reboot handle it") — far more painful than any prior HA update on this project (CARD-0233/0236-0240), for reasons unrelated to the update itself.** `docker compose pull homeassistant` hung indefinitely — this surfaced two distinct real bugs, both fully root-caused and documented on CARD-0268 rather than here (that card is the durable home for the Docker/containerd investigation): (1) live confirmation that a Pi 3B+'s shared USB 2.0 bus lets an image pull starve HA's own I/O and make it briefly unhealthy; (2) a separate, unrelated dockerd bug (Docker 29.6.1) where an OCI "referrers" 404 + manifest 404 double-miss makes `docker pull`'s own orchestration hang silently for 5+ minutes, reproducing every time and surviving a full host reboot.

**Resolved via `sudo ctr -n moby images pull ghcr.io/home-assistant/home-assistant:stable`** (containerd's own lower-level pull CLI, bypassing dockerd's stuck orchestration entirely — see CARD-0268 for the full investigation and the revised procedure this establishes for future updates). Completed cleanly after ~50 minutes (mostly slow extraction off the USB 2.0 bus). `docker compose up -d homeassistant` then recreated the container (after working around a stale-report/naming rough edge, also logged on CARD-0268) — confirmed healthy and running **2026.9.2** via `docker exec homeassistant python3 -c "import homeassistant.const as c; print(c.__version__)"`.

**Post-update entity-availability check run per root `CLAUDE.md`'s Home Assistant Docker Setup section.** Immediately after restart: 997 total entities, 253 unavailable/unknown — matching the documented pattern where a config entry reports `loaded` without having actually resynced. Reloaded `smartthings` (`Home Main`) and `ring` (`joscthomas@gmail.com`) config entries via `POST /api/config/config_entries/entry/<id>/reload` — both came back to `loaded` state, and unavailable count dropped to 123. **One real gotcha hit doing this reload, worth remembering for next time:** the first `smartthings` reload attempt was issued with a 30s client-side HTTP timeout, which was too short — the client gave up and closed the connection while HA was still mid-setup, which left the config entry in genuine `setup_error` state (worse than the stale-but-loaded state it started in) rather than just failing to reload. Fixed by retrying with a 120s timeout, which let it complete and land back on `loaded` correctly. **A reload's HTTP client needs a long timeout (120s+), not the usual quick-API-call assumption — the entry can be left in a worse state than before if the client aborts mid-setup.** The remaining 123 unavailable entities were checked and are all explainable by normal, non-update causes, not this integration-resync pattern: scenes and buttons structurally show `unknown`/`unavailable` until first triggered/pressed (21 scenes, most of the 15 buttons), several "peanut"-branded outlets are seasonal Christmas decorations genuinely unplugged in September, a handful of media players are simply powered off, and the Nabu Casa backup/cloud-voice entities have never been configured on this instance (present in every check all session, unrelated to this update).

**Related:** CARD-0128 (the auto-PR intake pipeline this came through), root `CLAUDE.md` (Home Assistant Docker Setup, the post-update check run), CARD-0268 (full root-cause investigation and the revised Docker-pull procedure this update's difficulty established).

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3208B, over the 2000B size threshold.

### CARD-0185 · [enhancement] [homeassistant] Upgrade CARD-0145's trigger to ring-mqtt's binary_sensor.*_motion (near-instant, vs. ~30-90s poll delay) — SUPERSEDED 2026-08-20 by CARD-0187
**Status:** Defer

**Raised 2026-08-18 18:23 MST (Joseph), while building CARD-0146.** CARD-0145's Ring motion announcement currently triggers on `sensor.*_last_activity` (CARD-0184's fix for the durably-broken native `ring` integration `event.*` platform) — reliable, but polled at ~60s intervals, so real delay can run 30-90+ seconds between an actual motion event and the announcement.

`ring-mqtt` (installed this session for CARD-0146) publishes its own independent `binary_sensor.<camera>_motion` entities, separate codebase/connection from the broken native integration. Live-tested today on the doorbell (`binary_sensor.doorbell_ding`/`binary_sensor.doorbell_motion`): near-instant, on within a few seconds of a real event — confirmed reliable across all of today's CARD-0146 testing. Confirmed the same entities exist for CARD-0145's other 4 cameras too: `binary_sensor.path_motion`, `binary_sensor.gate_motion`, `binary_sensor.front_porch_motion`, `binary_sensor.front_door_motion` (all present, all `off` at check time).

**Not yet decided/scoped:** swapping CARD-0145's trigger from `sensor.*_last_activity` to `binary_sensor.*_motion` for all 5 cameras (gate, path, front_door, front_porch, doorbell) — mechanically similar to CARD-0184's own swap, but the reverse direction. The `category == 'motion'` filter condition CARD-0184 added would no longer be needed (`binary_sensor.*_motion` entities are motion-only by construction, same reasoning as the original native-integration `event.*_motion` entities). Needs a live test pass on all 5 cameras (not just doorbell, which is all that's been proven so far) before trusting it as a full swap, plus the debounce/cooldown logic reconsidered for a fast-push source (the current 3s trailing delay and 30s entry-cluster window were tuned against a poll-based source's own timing characteristics).

**Done when:** CARD-0145's automation trigger is swapped to `binary_sensor.*_motion`, live-tested against real events on multiple cameras (not just doorbell), and confirmed both correctly-triggered and correctly-debounced — or a decision to keep the current poll-based trigger is recorded instead, with reasoning.

**Superseded 2026-08-20 16:18 MST.** A real field event the same day surfaced two more findings (a doorbell voice/video coordination problem, and a premature CARD-0146 stream termination) that don't fit this card's narrow trigger-swap scope — rather than keep bolting new findings onto this and CARD-0145/CARD-0184, all of it (including this card's own trigger-swap scope, unchanged) is consolidated into CARD-0187. No work here was wasted — the `binary_sensor.*_motion` entity confirmation and scoping notes above carry forward directly.

**Related:** CARD-0145 (the automation this would have upgraded), CARD-0184 (introduced the current `sensor.*_last_activity` fallback this would have replaced), CARD-0146 (the build that surfaced ring-mqtt's own motion entities as a viable alternative), CARD-0187 (supersedes this card).

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 4879B, over the 2000B size threshold.

### CARD-0170 · [enhancement] [homeassistant] Container image updates: home-assistant: 2026.8.2 available (running 2026.8.1) — auto-opened from jctsh-core — RESOLVED 2026-08-16 18:00 MST

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

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 2131B, over the 2000B size threshold.

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

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 4010B, over the 2000B size threshold.

### CARD-0168 · [bug] [homeassistant] Remove deprecated `http:` YAML block, resync stale configuration.yaml — RESOLVED 2026-08-14 19:28 MST (corrected 2026-09-22, see CARD-0329 — written `2026-08-15 02:28`, 7h fast via the `TZ=` clock bug)
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

**Verified and resolved, 2026-08-14 19:28 MST (corrected 2026-09-22 — written `2026-08-15 02:28`, 7h fast via the `TZ=` clock bug, see CARD-0329).** Checked the live migrated config directly (`.storage/http` on the Pi, via `sudo cat`) before touching anything: `use_x_forwarded_for: true` and `trusted_proxies: ["127.0.0.1/32", "::1/128"]` both confirmed carried over correctly, `yaml_migration_done: true` — didn't just trust the warning text. Removed the `http:` block from the live `configuration.yaml`.

**Restart hit the known s6-supervised gotcha** (`docker restart` failed — "tried to kill container, but did not receive an exit event"; container exited but didn't auto-restart despite `unless-stopped`) — recovered with a plain `docker start`. Docker's own healthcheck reported `healthy` well before HA's actual startup finished (`/api/config` showed `state: NOT_RUNNING`, only 127 of the eventual 772 entities loaded, `automation.*` domain briefly empty) — waited for `state: RUNNING` before treating anything as confirmed, avoiding a false "it's broken" read on `automation.card_0145_ring_motion_announcement` mid-boot.

**All "Done when" criteria verified live, not just configured:** `.storage/http` unchanged post-restart (`error: null`); nginx-fronted HTTPS login (`https://pi1.tailfe828a.ts.net/`) returns HTTP 200; HA logs since the restart contain no "ignored after migration" warning; `automation.card_0145_ring_motion_announcement` reloaded correctly with its trigger history intact; repo's `core/homeassistant/configuration.yaml` diffed byte-for-byte identical against the live file (no edit needed — the repo copy already lacked the block).

**Related:** CARD-0096 (the rename that put nginx in front of HA), CARD-0141 (HA HTTPS/reverse-proxy setup this trust config supports), CARD-0145 (automation whose survival through this restart was directly verified).

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3699B, over the 2000B size threshold.

### CARD-0130 · [enhancement] [homeassistant] Container image updates: home-assistant: 2026.7.4 available (running 2026.5.1) — auto-opened from jctsh-core — RESOLVED 2026-08-13 21:50 MST
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

