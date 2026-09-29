# hosts/m8 — Card Archive

Historical record of archived Done/Defer kanban cards for this component (CARD-0193). Not read as part of routine Session Start or component/cluster-session startup (JCTsh-Component-Session-Start.md) -- on-demand lookup only. See this component's own CLAUDE.md for current, curated context.

## Card History

**Archived from `tos/kanban-board.md` on 2026-09-22 (CARD-0193)** — 8491B, over the 5000B size threshold.

### CARD-0272 · [enhancement] [m8] M8-wide: switch Docker's logging driver to journald, reusing the M8's already-persistent journal — RESOLVED 2026-09-22 08:55 MST
**Status:** Done

**Auto verify (RESOLVED 2026-09-22 08:55 MST, see below):** ~~2026-09-21 05:00 MST~~ — the M8's next scheduled Monday 4am reboot. Once past, confirm `docker logs hike-izer-orchestrator` (or `journalctl CONTAINER_NAME=hike-izer-orchestrator`) still shows real pre-reboot history, not a gap starting at the reboot — same check CARD-0270 was originally trying to run when this whole thread started. Only move Status to Done once this is confirmed live; don't close it from inference alone.

**Auto verify resolved 2026-09-22 08:55 MST (ops cluster session startup) — the residual reboot test passed, checked live rather than inferred.** The M8's scheduled reboot did occur on the marked date: `journalctl --list-boots` shows boot `-1` ending **Mon 2026-09-21 04:00:13 MST** and the current boot starting **04:00:25 MST**. Post-reboot, `docker logs -t hike-izer-orchestrator` returns a continuous range from **2026-09-19T18:22:45Z** (the container's own start line, two days *before* the reboot) through **2026-09-22T15:02:51Z** — **11 lines before the reboot boundary and 86 after**, so real pre-reboot history survived and there is no gap starting at the reboot. The native path was confirmed the same way: `journalctl CONTAINER_NAME=hike-izer-orchestrator` reaches back further still, to **2026-09-15 05:00:20 MST** — spanning a *prior* container ID (`37e94cd12935`) as well as the current one (`a70a41dbef7e`), i.e. the journal outlives both the reboot and a container recreate, which the old `json-file` driver could not do. All 9 M8 containers re-confirmed still on the `journald` driver after the reboot via `docker inspect -f '{{.Name}} {{.HostConfig.LogConfig.Type}}'` — the setting survived the restart, not just the config file. Build's criteria are now fully met; moved to Done.

**Raised 2026-09-14 (Joseph), as a general follow-on from CARD-0270's investigation.** CARD-0270 fixed cost data specifically (a dedicated Sheet), deliberately leaving the broader class of gap unfixed: hike-izer-orchestrator's other diagnostic-only messages (retry/failure notes in `fetch_hike_data.py`, `fetch_hike_photos.py`, `place_context.py`'s Nominatim/Overpass failures, `backstop_check.py`/`generation.py`'s per-attempt failures) still only exist in Docker's default `json-file` container logs, whose content didn't survive today's M8 reboot (root cause not fully isolated, per CARD-0270's notes) — and the same exposure applies to any future container/script on this host that logs to stdout without a dedicated durable store.

**Grounded in CARD-0246's own finding, not a new investigation.** CARD-0246 (Pi journald volatile-storage bug) explicitly checked the M8 at the time and found its journald **healthy and persistent**: `/var/log/journal` populated with a real machine-id directory, `journalctl --list-boots` showing 5 boots spanning back to 2026-08-17, 302.9M of retained data. That's real, already-proven-durable storage on this exact host, sitting unused by Docker's containers, which default to the separate `json-file` driver instead.

**Decided 2026-09-14 (Joseph's call, via AskUserQuestion):**
1. **Driver: switch to `journald`**, not a new log-shipping aggregator (fluentd/syslog/etc.) — reuses proven-durable storage already on this host, no new infrastructure.
2. **Scope: all 9 M8 containers** (`immich_server`, `immich_postgres`, `immich_machine_learning`, `immich_redis`, `hike-izer-orchestrator`, `netalertx`, `hike-izer-cloudflared`, `hike-izer-web`, `ring-mqtt`), applied globally via `/etc/docker/daemon.json`'s `log-driver` key (currently only sets `"dns": [...]`, confirmed by reading the file directly) rather than editing each container's compose config individually.

**Real blast radius to plan around, not just a config edit:** `/etc/docker/daemon.json` changes require `systemctl restart docker` to take effect, which restarts **every container on the host** at once — same category of disruption CARD-0238 planned a deliberate maintenance window around for the Docker engine upgrade. Should be batched into a scheduled M8 maintenance window (per `network/jctsh-network.md`'s existing convention), not run ad hoc, and verified live afterward the same way CARD-0238 did (`docker ps` healthy for all 9 containers, `https://hikes.jctnet.com/` reachable).

**Real behavior to confirm during Build, not assumed:** `docker logs <container>` should keep working transparently against the journald driver (Docker reads back through it), and existing tooling (`docker logs hike-izer-orchestrator | grep ...`, used throughout this session's own investigation) shouldn't need to change to `journalctl CONTAINER_NAME=...` — worth a real check before considering this done, not just trusting the docs.

**Not yet scoped:** whether journald's own retention/vacuum settings need adjusting given 9 containers' worth of additional log volume landing there.

**Timing decided 2026-09-14 (Joseph's call) — proceed now, not the scheduled window.** Real, brief disruption across all 9 M8 services accepted directly rather than waiting for Monday 4am.

**Real gap found and fixed during Build, not assumed away — the original plan's "just restart the daemon" step doesn't actually work.** `/etc/docker/daemon.json`'s `log-driver` only applies to **newly created** containers — a plain `systemctl restart docker` restarts the daemon and then restarts (not recreates) already-existing containers per their `restart: unless-stopped` policy, leaving each one on whatever driver it was created with. Confirmed live: after `systemctl restart docker`, all 9 containers came back healthy, but `docker inspect` showed every one still `json-file`. The actual fix needs every container **recreated** — `docker compose up -d --force-recreate`, once per compose project (`hike-izer-web-app`, `immich-app`, `netalertx-app`, `ring-mqtt`) — a bigger, if similarly brief, disruption than the original plan described. Documented as a new standing gotcha, `JCTsh-Build-Standards.md` §9.9.

**Second real gap found during the recreate pass:** `netalertx`'s compose file carried a per-service `logging: options: {max-size, max-file}` block (leftover from before this switch) — journald doesn't support those json-file-specific options, so its recreate failed outright (`unknown log opt 'max-file' for journald log driver`) until the block was removed entirely from `components/netalertx/docker-compose.yml` (the canonical, version-controlled source) and redeployed. The other three compose projects had no such override and recreated cleanly on the first pass. Also documented in §9.9.

**Built and verified live, 2026-09-14:** `/etc/docker/daemon.json` set (`"log-driver": "journald"`, alongside the existing DNS pinning), backed up first, validated as real JSON before installing. All four compose projects recreated in turn. Post-recreate: all 9 containers confirmed healthy (`docker ps`), `https://hikes.jctnet.com/` returned 200, and every container's `LogConfig.Type` confirmed `journald` via `docker inspect` (not assumed from the config alone). `docker logs hike-izer-orchestrator` confirmed still working transparently, and a native `journalctl CONTAINER_NAME=hike-izer-orchestrator` query confirmed returning real, current container output — both halves of the "Real behavior to confirm" check above, met.

**Residual, not yet checked:** survival across a real subsequent M8 reboot (the scheduled Monday 4am window, or a deliberate one) — the mechanism itself (journald capturing container output) is confirmed working right now, and rides on the same journald CARD-0246 already proved persistent across real reboots at the host level, but this specific container-output path through it hasn't yet been reboot-tested. Move to Done once that's confirmed, not before — matching this project's own "real reboot test, not a live-state check" standard (`JCTsh-Build-Standards.md` §9.10).

**Related:** CARD-0246 (the Pi's journald fix — this card reuses the M8's own already-confirmed-healthy journald from that investigation, doesn't re-solve the Pi's problem), CARD-0270 (the narrower, already-decided cost-specific fix this generalizes), CARD-0238 (the M8-wide Docker-engine-upgrade precedent for planning a whole-host restart's blast radius and verification).

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3326B, over the 2000B size threshold.

### CARD-0352 · [enhancement] [m8] Pin cloudflared to an explicit version instead of `:latest`

**Status:** Done -- RESOLVED 2026-09-27 19:15 MST

**Raised 2026-09-27 19:12 MST, from CARD-0257's own recommendation (2026-09-22).** `components/hike-izer-web/docker-compose.yml` line 91 pins `cloudflare/cloudflared:latest`, not a version. Nothing currently pulls automatically, so there's no live danger today -- but the next incidental `docker compose pull`/recreate on that project (e.g. alongside an unrelated `hike-izer-web`/`hike-izer-orchestrator` update, same compose project) would silently land whatever's newest, with no decision point. CARD-0257 is actively holding this exact container back from 2026.9.x specifically because of an open, unaddressed upstream crash bug ([cloudflared#1737](https://github.com/cloudflare/cloudflared/issues/1737)) that matches this deployment's exact shape (Docker bridge network, `restart: unless-stopped`) -- a silent version bump would undo that held decision without anyone choosing it to.

**Essence-only per CARD-0256 -- not yet interviewed.** The fix itself is small (pin to `2026.8.3`, the version CARD-0257 confirmed is running cleanly), but open questions for Planning: whether `container_update_check.py`'s generic version-check (which currently can't compare against a floating `:latest` tag meaningfully) should gain a pinned-tag-aware mode once this lands; whether any other JCTsh-managed compose file has the same `:latest` exposure (not surveyed here -- this card only names the one CARD-0257 already found).

**Done when:** not yet scoped -- essence-only until Planning interviews it.

**Built and verified live, 2026-09-27 19:15 MST (Joseph: "do 352").** Confirmed the deployed compose file was byte-identical to the repo before touching it. Pinned `components/hike-izer-web/docker-compose.yml`'s `cloudflared` service to `2026.8.3` (the version CARD-0257 confirmed running cleanly), with an inline comment pointing back at both cards so a future editor knows why it's pinned rather than `:latest`. **Digest check before recreating:** `cloudflare/cloudflared:latest` (already running) and the newly-pulled `:2026.8.3` resolved to the identical image id (`sha256:51c9cefc...`) -- confirms the pin changes nothing about what's actually running today, only closes the "next incidental pull silently moves it" gap. Recreated only the `cloudflared` service (`docker compose up -d cloudflared`): the two sibling containers in the same compose project (`hike-izer-web`, `hike-izer-orchestrator`) were untouched (uptimes unaffected), `cloudflared` restarted clean -- `docker inspect` shows image `cloudflare/cloudflared:2026.8.3`, `cloudflared --version` confirms `2026.8.3`, no panic/error/segv lines in the post-recreate logs, `hikes.jctnet.com` returns HTTP 200. Not surveyed: whether any other JCTsh-managed compose file has the same `:latest` exposure -- out of scope per the card's own note, not investigated here.

**Done when:** met -- the pin is live and verified; CARD-0257's held-version decision can no longer be silently undone by an incidental pull on this project.
**Related:** CARD-0257 (found this gap, holds the reason it matters), CARD-0128/CARD-0126 (the update-check/PR pipeline this interacts with), `components/hike-izer-web/docker-compose.yml`.

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 2430B, over the 2000B size threshold.

### CARD-0237 · [enhancement] [m8] cloudflared container update available: 2026.8.2 → 2026.8.3 — RESOLVED 2026-09-02
**Status:** Done

**Raised via automated maintenance finding (PR #55, photo-server), 2026-09-01** — routine container-version-bump finding, same shape as CARD-0233's Home Assistant finding.

**Checked before deciding, not assumed safe:** `cloudflared`'s own GitHub release notes for 2026.8.3 (`cloudflare/cloudflared`, automated `cloudflare-warp-bot` release) — no changelog body, just build checksums, consistent with how this project's routine automated releases normally look (no flagged breaking changes or notable fixes called out).

**Real reason to still be a little careful, unlike a fully isolated bump:** this is the Cloudflare Tunnel client that `hikes.jctnet.com` runs through — the same tunnel CARD-0227 built its whole idea-image hosting feature on this session (`/webhook/idea-image`, served from the same `srv/` directory Caddy roots at). A tunnel restart is brief but real — anything hitting `hikes.jctnet.com` (Tasker's `/webhook/idea`, the idea-image upload path, the public hike pages themselves) would see a short interruption during the restart, not silent risk otherwise.

**Plan:** `docker compose pull cloudflared && docker compose up -d cloudflared` in `~/hike-izer-web-app/` on the M8 (same compose project as `web`/`orchestrator`, per `components/hike-izer-web/README.md`), verify live afterward — `docker logs` shows "Registered tunnel connection" with no errors, and `curl https://hikes.jctnet.com/` still returns 200.

**Folded into the same 2026-09-02 M8 maintenance window as CARD-0238, at Joseph's request, rather than waiting.** Pulled and recreated cleanly — `docker compose up -d cloudflared` also recreated `hike-izer-web` (same compose project, expected). Verified live: `curl https://hikes.jctnet.com/` returned 200 both immediately after the update and again after the M8's reboot; `hike-izer-cloudflared` shows healthy/running in `docker ps` post-reboot alongside all 8 other containers.

**Done when:** updated and verified live (tunnel reconnects cleanly, site still reachable) — **met**.

**Related:** `components/hike-izer-web/README.md` (the Cloudflare Tunnel setup this updates), CARD-0227 (the idea-image feature this tunnel now also serves), CARD-0233/CARD-0236/CARD-0238 (the same 2026-09-02 M8 maintenance window this was folded into).

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3706B, over the 2000B size threshold.

### CARD-0171 · [enhancement] [m8] M8 UEFI Secure Boot KEK CA firmware update available — auto-opened from photo-server — RESOLVED 2026-08-16 19:00 MST

**Status:** Done

**Auto-generated 2026-08-01 14:00 MST from photo-server's maintenance check** (GitHub PR #5). Raw finding: "M8 maintenance: 2 firmware update(s) available: KEK CA: UEFI Secure Boot Key Exchange Key; KEK CA: UEFI Secure Boot Key Exchange Key."

**Scoped 2026-08-16, not yet built.** Re-checked live via `fwupdmgr get-upgrades` on the M8 — still genuinely pending (not stale like PRs #7/#8 were for the HA finding). This is a single KEK CA device with two candidate release variants (AMI, ASUS) — the auto-generated "2 firmware updates" title is fwupdmgr listing both candidates for the same device, not two separate items. **Urgency: High** — a Secure Boot Key Exchange Key update, same class of finding as the dbx update CARD-0095 already applied, but not covered by that pass (which handled UEFI CA + dbx only).

**Acceptance criteria:**
1. Stage the update: `fwupdmgr update -y --no-reboot-check` (finalizes on next boot, same as CARD-0095's dbx update — UEFI-level fwupd updates apply via a staged capsule).
2. Reboot the M8 to finalize.
3. Verify live: `fwupdmgr get-upgrades` no longer lists the KEK CA update, all 8 containers back to Docker `healthy`, Tailscale reconnected, `hikes.jctnet.com` (Cloudflare Tunnel → hike-izer-web) reachable — same verification checklist CARD-0095 used for its own reboot.

**Real blocker found, 2026-08-16: no passwordless sudo on the M8.** Unlike the Pi's `pi` user (blanket `NOPASSWD: ALL`, a Raspberry Pi OS default), the M8's `jct` user needed an interactive sudo password — couldn't stage the firmware update from this session at all until that was resolved. Joseph added the same blanket `NOPASSWD: ALL` for `jct` (`/etc/sudoers.d/jct-nopasswd`, run by Joseph directly since it needed his password once, validated with `visudo -c` before relying on it), matching the Pi's existing posture. Documented in `CLAUDE.md`'s SSH section, since this is a real, standing change to the M8's security posture — worth being visible given the M8's real internet-facing surface area (`hikes.jctnet.com`), not a routine detail to bury in a closed card.

**Update applied and verified live, 2026-08-16 ~19:00 MST — clean, no incident this time** (unlike CARD-0170's HA update the same session):
1. Staged: `sudo fwupdmgr update -y --no-reboot-check` — "Successfully installed firmware."
2. Baseline recorded before reboot: all 8 containers healthy.
3. `sudo reboot` — M8 back reachable over SSH within the poll window, no manual intervention needed.
4. `fwupdmgr get-upgrades`: KEK CA now listed under "no available firmware updates," overall "No updates available" — firmware confirmed finalized.
5. All 8 containers came back automatically, briefly `health: starting`, settled to `healthy` within under a minute — no manual restart needed.
6. Tailscale: `m8` shows normal status, a live ping to the Pi over Tailscale succeeded.
7. `https://hikes.jctnet.com/` — `HTTP 200`, confirmed reachable from outside the M8 itself (through the full Cloudflare Tunnel path, not just a local check).

**Done when:** KEK CA firmware confirmed updated and M8 confirmed fully healthy post-reboot per the checklist above. **Met**, all seven checks above passed clean.

**Related:** CARD-0095 (M8 OS/firmware maintenance backlog — established the update policy and verification pattern this follows; that pass covered UEFI CA/dbx but not this KEK CA item), CARD-0170 (the same session's HA update, which hit a real Docker daemon incident — this one, by contrast, went cleanly).

---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 2172B, over the 2000B size threshold.

### CARD-0160 · [enhancement] [m8] Container image updates: cloudflared: 2026.8.2 available (running 2026.7.3) — auto-opened from photo-server — RESOLVED 2026-08-14 07:39 MST
**Status:** Done

**Auto-generated 2026-08-14 06:30 MST from photo-server's maintenance check (PR #11).** Raw finding: Container image updates: cloudflared: 2026.8.2 available (running 2026.7.3). Landed as a real kanban card via the old `resolve_and_merge()` path before the interviewed `land_pr_card.py` process (CARD-0162) existed — this note backfills the research and verification that process would normally require up front.

**Risk research (checked against cloudflared's actual GitHub releases, not just the raw finding):** `2026.7.3` → `2026.8.0` → `2026.8.1` → `2026.8.2`. Both `2026.8.0` and `2026.8.1` shipped with explicit "Do not use this version" warnings from Cloudflare — `2026.8.0` strips trailing slashes from HTTP-origin requests, causing redirect loops for anything needing canonical trailing-slash URLs (`cloudflare/cloudflared#1717`); `2026.8.1` normalizes request paths, breaking apps that need the raw encoded URL (`cloudflare/cloudflared#1719`). `2026.8.2` is the fix for both, with no further warnings. So this update lands past two known-bad releases straight onto the one that fixes them, not just a routine bump.

**Built and verified live, 2026-08-14 07:39 MST:** baseline confirmed (`hikes.jctnet.com` → HTTP 200 on `cloudflared:latest` pulled 2026-07-23, i.e. `2026.7.3`) before touching anything. `docker compose pull cloudflared && docker compose up -d cloudflared` on the M8 (`~/hike-izer-web-app`). Post-update: `cloudflared version 2026.8.2` confirmed via `docker exec`, tunnel reconnected clean (4/4 edge connections registered, connectivity pre-checks all PASS, `quic` protocol), and — specifically checking for the exact regression class `2026.8.2` fixes — `hikes.jctnet.com` returns `HTTP 200` both with and without a trailing slash, no redirect loop.

**Related:** CARD-0094 (original Cloudflare Tunnel setup), CARD-0162 (the interviewed PR-landing process this update predates), `components/hike-izer-web/docker-compose.yml`.

---

