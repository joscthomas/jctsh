# JCTsh Backlog

Lightweight kanban. Each card has a **type** (idea | enhancement | bug) and a unique ID.

**Columns:** Backlog → Planning → Build → Done, plus **Defer** (off to the side — reachable from any stage)
- **Backlog** — captured, not yet being worked on
- **Planning** — being scoped/interviewed, and (if non-trivial) an implementation plan written — no separate Design checkpoint; the plan itself is the design artifact
- **Build** — going through the plan/implementation, including testing
- **Done** — complete
- **Defer** — a deliberate decision not to pursue for now (not abandoned, not forgotten — just consciously parked); can move here from any other column

<!-- next-card-id: CARD-0241 -->

---

### CARD-0240 · [enhancement] [homeassistant] Home Assistant container update available: 2026.9.0 → 2026.9.1

**Status:** Build

**Raised via automated maintenance finding (PR #64, jctsh-core), 2026-09-05** — routine container-version-bump finding from the scheduled maintenance check.

**Interviewed 2026-09-05.** Same scope as CARD-0233/CARD-0236 through CARD-0238: evaluate first, decide whether to update, then apply and verify live in this same card — not a bare decision-only record.

**2026.9.1's own release notes checked** (`gh release view 2026.9.1 --repo home-assistant/core`) — 28 items, entirely small per-integration bug fixes and dependency bumps for integrations this instance doesn't use (SMTP, backup, Miele, Roborock, Vizio, Amber Electric, UniFi Protect, device registry, Daikin, Besen, orjson, Flo, serial, Environment Canada, Hot Spring, KNX, MotionEye, Tradfri, frontend, Reolink, LitterRobot). Nothing touching MQTT, SmartThings, Google, or the recorder — the pieces this instance actually depends on per `CLAUDE.md` ("Home Assistant is the bridge to SmartThings — there is no other path"). **Decision: safe to update.**

**Plan:**
1. Bump the image tag in `core/homeassistant/docker-compose.yml` (or confirm it already tracks `:stable` and just pull fresh).
2. `docker compose pull && docker compose up -d` on the Pi.
3. Verify live: `/api/config` reports `2026.9.1`, Docker health check `healthy`, SmartThings-domain entities still present/responding, no new MQTT/recorder errors in `docker logs`.

**Done when:** the update is applied and all three verification points above are confirmed live — not just that the container restarted.

**Related:** `CLAUDE.md` (Home Assistant Docker Setup section, `core/homeassistant/docker-compose.yml`), CARD-0233/CARD-0236/CARD-0237/CARD-0238 (the identical routine-update pattern this repeats).

---

### CARD-0239 · [enhancement] [hike-izer] Remote, phone-only trigger for hike-izer's step-2 gap-fill pass — no SSH required

**Status:** Planning

**Raised via PR #62 (auto-opened maintenance-alert finding), 2026-09-04.** Raw finding: *"how can I remotely issue the second pass of hikiser."*

**Context.** CARD-0214 built the step-2 gap-fill pass (`generation.py --step2 <file_stem>`, idempotent, safe to re-run any number of times) with three existing ways to invoke it: the daily 5pm MST systemd timer, a manual SSH command on the M8, or asking Claude to run it during a session. None of those work when Joseph is away from a computer and just wants to nudge a specific hike's page to catch up on data that synced late.

**Interviewed 2026-09-05.** Real need is a home-screen tap on the phone, no SSH/computer required — same shape as the existing `Log Idea` Tasker widget (CARD-0173). Always targets the current/latest published hike (no date picker) — same `generation.current_or_latest_file_stem()` helper `/webhook/stage-file` already uses. Gap-fill only, no narrative — matches the daily cron's own behavior exactly; narrative stays the separate opt-in ask (CARD-0123), untouched by this.

**Design — reuses the existing webhook-receiver pattern, no new infrastructure:**
- New `POST /webhook/step2` route on `hike-izer-orchestrator` (`components/hike-izer-orchestrator/app.py`), auth via the existing `WEBHOOK_SECRET` `?key=` pattern shared by every other machine-triggered route (`hike-end`, `stage-file`, `idea`) — not `EDIT_PIN`, since this is a Tasker-fired request, not something Joseph types by hand.
- Resolves the target hike via `generation.current_or_latest_file_stem()`. If no published hike exists yet, responds `409` (matches `stage-file`'s existing behavior for the same case).
- Runs `generation.run_step2_and_log(file_stem, with_narrative=False)` in a background thread, same reasoning as `hike-end` — the underlying Sheet/Nominatim/Overpass/Immich calls aren't fast enough to hold the HTTP response open, and Tasker has its own request timeout.
- Responds `200` immediately once the background run is kicked off; failure visibility goes through the same MQTT `Alert`/`System` logging every other route already uses (`_log_mqtt_async`), not just `docker logs`.
- `README.md` gets a new webhook-contract entry plus a "Building the Tasker task (Joseph)" section mirroring `Log Idea`'s exact structure: one Task (`HTTP Post` to `https://hikes.jctnet.com/webhook/step2?key=<WEBHOOK_SECRET>`) added to the home screen via the Tasks tab's **Add to Launcher** (the route that actually works on this Tasker version, per CARD-0173's own finding — not the Widgets flow).

**Deploy:** `scp` the updated `app.py` (plus this component's other `.py` files per the existing deploy-copy list) to `jct@m8.local:~/hike-izer-web-app/orchestrator/`, then `docker compose up -d --build orchestrator` — per this component's own README deploy section.

**Done when:**
- The new `/webhook/step2` route is live on the M8, verified with a real `curl`/test hit (wrong key → 401; no published hike → 409; a real request → 200 and a real `run_step2` execution visible in `docker logs` and the MQTT dashboard).
- Joseph has built the Tasker task and home-screen icon, and a real tap on the icon (not just a desk-side `curl` test) produces a real step-2 run against the actual current hike.

**Related:** CARD-0214 (the two-pass design and `run_step2`/`run_step2_and_log` this reuses unchanged), CARD-0173 (the `Log Idea` Tasker task this mirrors, including the Add-to-Launcher home-screen-icon gotcha), `components/hike-izer-orchestrator/app.py`, `components/hike-izer-orchestrator/generation.py`, `components/hike-izer-orchestrator/README.md`.

---

### CARD-0238 · [enhancement] [infrastructure] M8 OS maintenance: 25 routine updates, 10 flagged for review — includes Docker itself and linux-firmware — RESOLVED 2026-09-02
**Status:** Done

**Raised via automated maintenance finding (PR #57, photo-server), 2026-09-01** — the M8's monthly OS/firmware maintenance check (CARD-0095). Full finding: *"M8 maintenance: 25 routine update(s) pending. 10 package(s) need review: containerd.io, docker-buildx-plugin, docker-ce, docker-ce-cli, docker-ce-rootless-extras, docker-compose-plugin, linux-firmware-intel-misc, linux-firmware-mediatek, linux-firmware-misc, linux-firmware-qualcomm-wireless."*

**Why the 10 are flagged, not just noise:** CARD-0095's own risk-tiering (`hosts/m8/maintenance-check.py`, `REVIEW_PATTERNS`) pulls out exactly two categories for deliberate human review rather than auto-lumping with the routine 25 — Docker-stack packages (a daemon restart touches every running container on the host) and kernel/firmware packages (why a reboot becomes required). This finding hits **both** categories at once, on a host that's currently running a lot of this session's own new/recently-touched infrastructure: `hike-izer-orchestrator` (CARD-0121's new backstop check, CARD-0227's new webhook route), `photo-server`/Immich, `netalertx`, `ring-mqtt`, and `cloudflared` (the tunnel CARD-0227's image hosting now depends on).

**Not a routine "just apply it" case, unlike CARD-0233/netalertx/cloudflared siblings raised the same week.** A Docker engine/CLI/compose-plugin update means every container on the M8 gets touched by the daemon restart, not just one — real blast radius across this host's whole stack, not an isolated per-service bump. `linux-firmware` updates typically require a reboot to actually take effect (dead firmware blobs otherwise), which is its own separate, deliberate step per `jctsh-network.md`'s Scheduled Maintenance Windows convention (M8's own reboot is already a tracked weekly Monday 4am job).

**Interviewed 2026-09-02 — decision: batch with the M8's next regular Monday reboot (2026-09-07), not a separate window.** Joseph's call: no known CVE flagged in this finding (just routine version availability), so there's no urgency pushing toward sooner — one combined disruption beats two.

**Real finding that narrows the actual action needed, checked directly rather than assumed:** the M8's own `unattended-upgrades` config (`/etc/apt/apt.conf.d/50unattended-upgrades`) only covers `Allowed-Origins` for the OS's own default archive + security repos (`${distro_id}:${distro_codename}[-security]`) — **Docker's packages (`docker-ce`, `containerd.io`, `docker-buildx-plugin`, `docker-ce-cli`, `docker-ce-rootless-extras`, `docker-compose-plugin`) come from Docker's own separate third-party APT origin, not in that list**, so they genuinely won't apply themselves; a deliberate `apt upgrade` is required. `linux-firmware-*`, by contrast, ships from the standard OS archive and isn't blacklisted (`Package-Blacklist`'s own `linux-` entry is commented out, i.e. disabled) — it's very likely already being auto-applied by `unattended-upgrades` on its own schedule and just sitting "pending, needs reboot" until Monday, no separate action needed for that half. **So the real remaining action is narrower than the original finding suggested: just the six Docker-stack packages**, applied manually.

**Plan for 2026-09-07:** shortly before (or immediately as part of) the scheduled 4:00 AM reboot window, run `apt upgrade` for the six Docker-stack packages on the M8 — this will restart the Docker daemon (and every container with it) once, immediately followed by the already-scheduled OS reboot moments later, functionally one combined maintenance window rather than two disruptions on different days. Verify live afterward: every container on the M8 (Immich's four, NetAlertX, hike-izer-web, hike-izer-orchestrator, ring-mqtt, cloudflared) confirmed healthy post-restart via `docker ps`, not just "the commands exited 0."

**Superseded same day — Joseph's call: don't wait for Monday, do the combined window today (2026-09-02) instead.** Same rationale as the original plan (one combined disruption beats two), just moved up rather than waiting five days. CARD-0236 (NetAlertX) and CARD-0237 (cloudflared) were folded into this same window at Joseph's request too, since it was already a deliberate M8-wide maintenance pass.

**Sequence actually run, in order:**
1. Published a manual pre-maintenance MQTT notice (`jctsh/server/photo-server/log`, same mechanism `scheduled-reboot.service` uses) so it's visible on the dashboard the same way the automatic weekly one is.
2. Ran `apt-get update && apt-get upgrade -y` for **all 35 pending packages** (not just the 6 Docker-stack ones the original plan scoped) — detached via `nohup`, since CARD-0233's earlier same-day attempt had already shown a plain inline `ssh host "long command"` can die silently if the connection drops mid-run. Completed clean, exit 0.
3. Updated `cloudflared` (CARD-0237) and `netalertx` (CARD-0236) via their own `docker compose pull/up`.
4. Rebooted the M8.

**Real process gap, caught by Joseph, not self-caught — worth being honest about.** Step 2 ran as a blanket `apt-get upgrade -y` without first reading release notes for the specific packages flagged for review (Docker Engine, `linux-firmware-*`) — skipping exactly the "check before applying" discipline this card's own plan called for and CARD-0233 had already established for Home Assistant. Caught only when Joseph asked directly: *"Did you do the research on all these upgrades to confirm risk level?"* Answered honestly (no, not for these), then did the check **retroactively**, after the fact:
- **Docker Engine: 29.7.1 → 29.7.2** (confirmed via `docker version` + the actual install log) — a single patch release. Checked Docker's own changelog: purely bugfixes (two regressions from 29.7.0 fixed — image pulls with absolute hardlink targets, `docker cp`/permission handling on older kernels — plus a `docker service create/update` panic fix, a BuildKit bump, an nftables compatibility tweak). No breaking changes.
- **`linux-firmware-*` (all four flagged packages):** confirmed via the install log that all four moved from the same firmware snapshot date (`20260319.git217ca6e4`) to a `.2`/`.1.2` *packaging* revision only — not a new firmware snapshot. Confirmed via Ubuntu's own `apt-get changelog`: the revision bump added one missing firmware blob for HP ISH on Intel Panther Lake systems (not this M8's hardware) plus a copyright-file cleanup. No functional firmware content changed.
- Both checks came back clean, but this was luck confirmed after the fact, not diligence applied before acting — a real gap, not a non-issue just because it worked out. Noted for next time: don't let "it's bundled into a broader apt upgrade" be a reason to skip checking the specific packages a risk-tiering system already flagged for review.

**Verified live, post-reboot:** all 9 M8 containers (`netalertx`, `hike-izer-cloudflared`, `hike-izer-web`, `hike-izer-orchestrator`, `ring-mqtt`, `immich_server`, `immich_machine_learning`, `immich_postgres`, `immich_redis`) confirmed `Up`/`healthy` via `docker ps`. `https://hikes.jctnet.com/` returned 200 both before and after. Dashboard shows the full expected sequence: pre-reboot notice → `"Boot complete."` → a transient `Alert` for Immich/hike-izer services `:starting` during the boot window (expected, resolved within the same check) → all healthy.

**Done when:** the flagged packages are upgraded, verified live post-reboot — **met**, moved up to 2026-09-02 rather than 2026-09-07.

**Related:** `hosts/m8/maintenance-check.py` (`REVIEW_PATTERNS`, CARD-0095's own risk-tiering reasoning), `jctsh-network.md` (Scheduled Maintenance Windows — M8's existing weekly reboot slot), `hosts/m8/operations.md` (the scheduled-reboot mechanism this borrowed its MQTT-notice convention from), CARD-0233 (the Home Assistant update this session, same evaluate-then-update discipline — the one this card's own execution fell short of, then corrected), CARD-0236/CARD-0237 (folded into this same window).

---

### CARD-0237 · [enhancement] [infrastructure] cloudflared container update available: 2026.8.2 → 2026.8.3 — RESOLVED 2026-09-02
**Status:** Done

**Raised via automated maintenance finding (PR #55, photo-server), 2026-09-01** — routine container-version-bump finding, same shape as CARD-0233's Home Assistant finding.

**Checked before deciding, not assumed safe:** `cloudflared`'s own GitHub release notes for 2026.8.3 (`cloudflare/cloudflared`, automated `cloudflare-warp-bot` release) — no changelog body, just build checksums, consistent with how this project's routine automated releases normally look (no flagged breaking changes or notable fixes called out).

**Real reason to still be a little careful, unlike a fully isolated bump:** this is the Cloudflare Tunnel client that `hikes.jctnet.com` runs through — the same tunnel CARD-0227 built its whole idea-image hosting feature on this session (`/webhook/idea-image`, served from the same `srv/` directory Caddy roots at). A tunnel restart is brief but real — anything hitting `hikes.jctnet.com` (Tasker's `/webhook/idea`, the idea-image upload path, the public hike pages themselves) would see a short interruption during the restart, not silent risk otherwise.

**Plan:** `docker compose pull cloudflared && docker compose up -d cloudflared` in `~/hike-izer-web-app/` on the M8 (same compose project as `web`/`orchestrator`, per `components/hike-izer-web/README.md`), verify live afterward — `docker logs` shows "Registered tunnel connection" with no errors, and `curl https://hikes.jctnet.com/` still returns 200.

**Folded into the same 2026-09-02 M8 maintenance window as CARD-0238, at Joseph's request, rather than waiting.** Pulled and recreated cleanly — `docker compose up -d cloudflared` also recreated `hike-izer-web` (same compose project, expected). Verified live: `curl https://hikes.jctnet.com/` returned 200 both immediately after the update and again after the M8's reboot; `hike-izer-cloudflared` shows healthy/running in `docker ps` post-reboot alongside all 8 other containers.

**Done when:** updated and verified live (tunnel reconnects cleanly, site still reachable) — **met**.

**Related:** `components/hike-izer-web/README.md` (the Cloudflare Tunnel setup this updates), CARD-0227 (the idea-image feature this tunnel now also serves), CARD-0233/CARD-0236/CARD-0238 (the same 2026-09-02 M8 maintenance window this was folded into).

---

### CARD-0236 · [enhancement] [infrastructure] NetAlertX container update available: 26.8.5 → v26.9.0 — RESOLVED 2026-09-02
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

### CARD-0235 · [idea] [hike-izer] BirdNET Live tracks continuous GPS during every hike — evaluate turning it off, but check the species-ID accuracy tradeoff first — RESOLVED 2026-09-02
**Status:** Done

**Raised 2026-08-29 (Joseph), via a forwarded idea email with a screenshot attachment (PR #52) — testing CARD-0227's new image-attachment feature surfaced a real question.** The screenshot showed BirdNET Live's "Survey Setup" screen: a Location step offering GPS/Manual/Skip, a real captured coordinate (32.4612, -111.1184) once GPS was selected, and a warning — *"Location only updates when the app is open. Tap here to grant background location permission in Settings."* That warning is the actual impetus for this card: it reveals that BirdNET Live doesn't just record a single starting location for the survey — in GPS mode it polls the phone's live location **continuously for the survey's whole duration**, including while the screen is locked or the app is backgrounded, which is exactly why it needs a separate background-location permission grant to keep working once the phone isn't actively on-screen. That's a real, ongoing battery cost (continuous GPS polling, not a one-time read), which is what prompted the question: is this tracking used for anything, or can it just be turned off?

**Confirmed against this project's own docs: the tracking itself was already known, just not investigated for necessity.** `components/hike-izer-orchestrator/birdnet-pipeline.md` Section 4 (CARD-0182) already documents Survey Mode's "own continuous GPS track (not needed by this pipeline, but no downside)" — the mode switch from Live to Survey was decided 2026-08-19 for an unrelated reason (background audio-recording survival, not GPS).

**The lat/lon data isn't just tracked on-device and discarded there — it's actually exported and forwarded all the way into this project's own data pipeline, then ignored once it arrives.** Same section confirms the mechanism precisely: "Survey Mode's exports carry *extra* fields on top (GPS track, spatial metadata) that Live Mode's don't, but `birdnet.py` only ever reads `data.get("detections", [])` from the top-level export and ignores every other key, so those extra fields are inert." Concretely — every hike's BirdNET export (the `.zip`/`.json` shared via AutoShare → Tasker → `/webhook/stage-file?kind=birdnet`, staged and parsed by `birdnet.py`, per Section 1 of the same doc) already carries the full GPS track as one of its top-level keys, travels the whole path from phone to the M8, and is then dropped on the floor at parse time — `birdnet.py` never even looks at that key. The Route Map's per-sighting location instead comes from the hike's own independent GaiaGPS track via `build_hike_map.interpolate_position()`, a completely separate source that has nothing to do with BirdNET's own reported coordinates. So the waste isn't hypothetical or on-device-only — it's a real field, generated continuously, transmitted in every export file, and thrown away by name at the very first parsing step on the receiving end. The only genuinely open question is whether it's *also* dead weight **inside BirdNET Live itself**, before it ever reaches this pipeline — i.e., whether disabling the GPS capture at the source would cost anything the app itself relies on.

**Real caveat found via research before assuming "yes, safe to disable" — this is not free.** BirdNET's species range model (V2.4) uses latitude/longitude + week-of-year as real inputs to filter/bias which species it considers plausible during identification itself — not just metadata alongside the audio. Per published comparisons of filtering strategies: unfiltered detection "suffered very low precision and poor overall performance," while spatio-temporal (location + week) filtering "greatly improved precision and overall performance" across most regions tested. So turning off location could plausibly degrade BirdNET's own on-device identification accuracy, a real cost that has nothing to do with whether *this project's pipeline* reads the exported GPS field.

**Question 1 resolved 2026-09-02 — confirmed against BirdNET Live's own published docs (`birdnet-team.github.io/birdnet-live-app/user/settings/`), not just the general-model research above:**
- **"Use GPS" toggle:** ON = continuously reads live location. OFF = the app "never reads the GPS or asks for location permission on its own" — a complete elimination of the background polling this card was raised about, not a reduction.
- **"Manual Coordinates":** a typed/pasted (or **"Pick on map"** — a full-screen map picker, tap to set, no typing decimal degrees required) fixed lat/lon, used whenever GPS is off.
- **Species filtering (Location Filter / Adaptive Location Filter / Location Weighting) doesn't care where the coordinate came from** — it filters continuously per detection against *whatever* location value is currently set, live GPS or static Manual. So the filtering-accuracy benefit found in the "real caveat" section above is available either way — this was the real crux of question 2, and it means there's no forced tradeoff between accuracy and battery: **Manual Coordinates gets the full filtering benefit with GPS never touched at all.** Since every JCTsh hike happens in the same general Arizona area, a fixed manual coordinate near home/trailhead falls in the same coarse filtering region a moving GPS fix would anyway — answering question 3 too (no meaningful accuracy cost from staying static across one hike's actual movement).

**A real, better alternative surfaced by Joseph 2026-09-02, reframing the whole card — not "turn GPS off," but "keep it on and actually use what it already produces."** Rather than disabling GPS to save battery, the alternative: leave "Use GPS" on and have `birdnet.py` consume the per-detection `latitude`/`longitude` this project's own pipeline already receives in every Survey Mode export (confirmed live 2026-09-02, CARD-0229 investigation — 29 distinct coordinate pairs across 39 detections in the 2026-08-29 export, real per-detection movement, not a static session value) **instead of** the current approach (`build_hike_map.interpolate_position()`, correlating a completely separate GPS Track/GPSLogger timestamp against each sighting). BirdNET's own coordinate is a more direct source — captured at the actual moment of detection, not interpolated after the fact from an unrelated app's 30-second-interval track — and it's already being transmitted into this pipeline every single hike; the interpolation step exists only because `birdnet.py` has never read the field that was already there.

**The battery question this reframing turns on, honestly answered:** no hard mAh-per-detection number is available — that requires real on-device battery telemetry, not something derivable from this codebase or from BirdNET's own docs (which don't address battery impact directly). But there's a strong, project-specific reason to expect the *marginal* cost of leaving BirdNET's GPS on is small: **GPSLogger already runs continuous GPS polling for the entire duration of every hike regardless of BirdNET's setting** (`gps-pipeline.md`: a trackpoint every 30 seconds, for the GPS Track sheet — a separate, already-running pipeline). A phone has one physical GPS radio; the OS's fused location provider serves concurrent apps requesting updates from that same active radio rather than powering it up twice. Since GPSLogger is already keeping GPS continuously active throughout every hike independent of anything BirdNET does, BirdNET's own concurrent GPS reads are very likely riding on a radio that's already on, not triggering meaningfully more hardware activity — the "real, ongoing battery cost" this card opened with may be substantially smaller in *this specific setup* than it would be for someone running BirdNET Survey Mode without a second app also holding GPS continuously open. Not a measured number, but a reasoned basis for not prioritizing the disable-GPS path.

**Genuinely unresolved, revised 2026-09-02:**
1. ~~Whether BirdNET Live wires Survey Mode's GPS into species-range filtering~~ — **resolved above.**
2. ~~Whether that filtering needs continuous polling vs. a one-time location~~ — **resolved above** (it doesn't; Manual Coordinates works identically).
3. **Which path to actually take: Manual Coordinates (guaranteed battery savings, simplest, no code change) vs. keep GPS on + build real per-detection-GPS consumption into `birdnet.py`/the Route Map (better data, likely-small-but-unmeasured marginal battery cost, requires build work)** — not decided yet. If the second path is chosen, it's a real scope addition: replacing or supplementing `interpolate_position()` for BirdNET sightings specifically, touching `birdnet.py`, `build_hike_map.py`, and potentially the Wildlife Detections sheet schema (CARD-0229) to carry real per-detection coordinates instead of (or alongside) the hike-level join it has today.
4. If real device battery measurement ever matters for this decision, that needs an actual on-device test (e.g., comparable-length hikes with GPS on vs. off, checked against the phone's own battery stats) — out of reach for me to produce directly.

**Decision made 2026-09-02 (Joseph): keep-GPS-and-consume-it.** Better data (a real fix at the actual moment of detection, not an interpolated estimate) for a marginal battery cost already reasoned to be small given GPSLogger's own concurrent continuous polling — see above. Scope expanded at Joseph's request to also carry real coordinates into the Wildlife Detections sheet archive (CARD-0229), not just the Route Map.

**Built, deployed, and verified live 2026-09-02:**
- `birdnet.py`: `parse_detections()` (feeds the Sheet) now carries a `lat`/`lon` per species row — the first detection's own coordinates, tracked alongside `first_timestamp` with the same "earlier detection found → update together" logic. `_occurrence_row()`/`parse_occurrences()` (feeds Route Map markers only) now carries `lat`/`lon` per occurrence — the raw detection nearest `representative_timestamp` (the same midpoint already computed for the timestamp, not a new concept). Both come back `None` on older exports with no per-detection GPS, verified against synthetic old-format/new-format detection lists before any live deploy.
- `templating.py`'s `_build_event_markers()`: bird markers use `occ["lat"]`/`occ["lon"]` directly when present (tooltip labeled "BirdNET GPS"), falling back to `build_hike_map.interpolate_position()` exactly as before when absent (tooltip stays "approximate location") — no change to marker shape or to `build_hike_map.py`/client-side JS, both already agnostic to how coordinates were derived.
- `generation.py`'s `_post_wildlife_detection()`: payload gains `lat`/`lon`.
- `environmental-data.gs`: Wildlife Detections sheet gained `lat`/`lon` columns (appended at the end — additive, no changes needed to `_exportSheet()` or `rebuild_from_sheets()`).
- **Real bug found and fixed along the way, not part of the original plan:** every bare-date `hike_file_stem` ("2026-08-29") was being silently reinterpreted by Google Sheets as a real Date cell and re-exported as "2026-08-29T07:00:00.000Z" — the exact bug class `_maybeCaptureHikeStartForecast()` already guards against for its own `date_local` column (`setNumberFormat('@')`), just never applied to this sheet. Fixed with the same double defense: column B forced to Plain Text plus a literal apostrophe prefix on the written value. This was silently breaking `wildlife_life_list.py`'s `rebuild_from_sheets()` recovery tool (groups rows by this exact string) — would have failed quietly if ever actually needed.
- **Historical backfill redone, not just left broken going forward:** all 164 rows (from CARD-0229's original backfill) re-posted with the file_stem fix and real lat/lon where recoverable — 14 of 15 hikes still had their original staging export on disk, re-parsed directly via `birdnet.parse_detections()` for real coordinates; the 15th (2026-08-25, whose export no longer exists) kept CARD-0229's derived-timestamp fallback with lat/lon left `None` (no BirdNET file left to read a coordinate from). Final verified count: 164 rows, 47 with real GPS, correct plain-text `hike_file_stem` on every row, confirmed via `action=export`.
- **Real end-to-end regeneration, not just unit checks:** re-ran step 2 for the 2026-08-29 hike (real staged GPS-carrying export, backed up first) — all 22 bird markers on the regenerated Route Map used real BirdNET GPS (0 fell back to interpolation), confirmed live in the rendered HTML, no errors, no duplicate Sheets rows from the re-run (dedup correctly skipped re-archiving already-cached species).

**Done when:** a real decision was made (keep-GPS-and-consume-it) — **met**. The `birdnet.py`/Route Map/Wildlife Detections change is built and verified live — **met**.

**Related:** `components/hike-izer-orchestrator/birdnet-pipeline.md` Section 4 (CARD-0182 — the Live→Survey Mode decision this follows on from), `components/hike-izer-orchestrator/build_hike_map.py` (`interpolate_position()`, unchanged but now only a fallback for BirdNET markers), CARD-0229 (the broader BirdNET data-architecture-and-MQTT review this was originally a narrower sibling to — this card ended up extending that same Wildlife Detections sheet directly), CARD-0227 (the image-attachment feature this PR tested, which is how the screenshot made it into the original finding).

---

### CARD-0234 · [bug] [hiking-monitor] GPSLogger errors "file didn't exist" on a normal hike start, self-heals on restart
**Status:** Build

**Raised 2026-08-29 (Joseph), live incident during a hike start.** Starting GPSLogger produced an error saying a file didn't exist. Restarting GPSLogger worked cleanly — the file apparently got created by the failed attempt, since the retry succeeded with no further error. **Confirmed: a normal hike start, nothing unusual beforehand** (no recent phone reboot, no GPSLogger/Android update, no reinstall) — so this isn't tied to a one-off device event, it's either intermittent or has some other trigger not yet identified.

**Screenshot reviewed and original offline-queue theory dropped — real cause narrowed down considerably.** The screenshot Joseph shared (GPSLogger's Simple View mid-session) shows a local CSV log actively in play: session `20260829`, path `/storage/emulated/0/Download`. Confirmed with Joseph: this CSV logging is **deliberate**, enabled for CARD-0208's Mile Announcer feature — not leftover/drifted config, and not something to turn off.

**Much better-grounded theory, from CARD-0208's own build notes.** CARD-0208 fixed the CSV file's Tasker-side path to `Download/%todays_date.csv` (`yyyyMMdd` format) — a fresh file per calendar day. GPSLogger's own `CSVFileLogger.java` (per CARD-0208's source reading) opens the file in append mode on each write. **The very first location write of a new day is the one moment that file genuinely doesn't exist yet** — if GPSLogger's own open/append logic references the file before creating it on that first write, "file does not exist" on the very first fix of the day, self-healing immediately after (file now exists) matches the observed symptom exactly, including "confirmed: normal hike start, nothing unusual" — this would recur on the first GPSLogger start *of any new day*, not tied to a device event.

**Practical guidance for next time it happens:** `gps-pipeline.md`'s own "Test Before Walking" section documents how to see GPSLogger's real log (swipe the bottom bar up) — capturing the exact error text next time would confirm this theory outright. Until then, restarting GPSLogger (as already worked) is a known, low-cost workaround.

**Low urgency, not currently blocking anything:** GPSLogger logs every 30 seconds; a one-time miss on the very first fix of the day costs at most one trackpoint, well within the kind of gap this pipeline already tolerates elsewhere (see CARD-0221's own coverage-gap analysis).

**Fix applied, 2026-08-29 (Joseph) — targets the theorized root cause directly, sidesteps rather than patches GPSLogger internals.** Changed GPSLogger's CSV output from the per-day `%todays_date.csv` name to a fixed custom filename, **`gpslogger`** (`gpslogger.csv`) — the file now only needs to be created once, ever, not fresh each calendar day, removing the specific moment ("first write of a new day") the theory pinned the error to. Updated the Tasker Mile Announcer task's Read File target to match the new fixed filename (was pointed at the old `%todays_date.csv` pattern, per CARD-0208's build notes). **Not yet verified — waiting on the next real hike** to confirm the error doesn't recur.

**Real follow-on risk surfaced by this change, worth watching, not yet a problem:** the file no longer rotates per day — it will now accumulate every hike's rows indefinitely across the file's entire lifetime, not just one day's worth. CARD-0208's own open question ("whether Tasker's read-last-line approach is cheap enough... `gps-pipeline.md`'s own estimate: ~1,200 rows / ~75KB for a *10-hour hike*") was scoped against a single day's file — Mile Announcer's task reads and splits the **entire file** into lines every 2 minutes while running (per CARD-0208's build notes), so this file's size is now unbounded across the device's whole hiking history rather than capped at one day. Likely fine for a long while given typical hike frequency, but worth a real check (file size, Tasker read/split latency) after a few months of accumulated hikes — not blocking this card, but worth a note on CARD-0208 too.

**Done when:** a real hike confirms GPSLogger starts cleanly with no "file does not exist" error using the new fixed filename — not just that the config change was made.

**Related:** `components/hiking-monitor/gps-pipeline.md` (Custom URL Logger config, the in-app log-viewing method), CARD-0208 (Mile Announcer — the reason local CSV logging is enabled at all; its own `%todays_date.csv` naming is now superseded by this card's fixed-filename change, and its file-size/read-cost assumption is now worth re-checking against an unbounded-growth file), CARD-0221 (the coverage-gap tolerance precedent this compares against).

---

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

### CARD-0232 · [idea] [hiking-monitor] Investigate photo-based plant identification alternatives
**Status:** Backlog

**Raised via idea email (PR #46, joscthomas+kbc@gmail.com), 2026-08-29** — raw finding text was just "plant identification"; not yet interviewed for what triggered it or what "done" would look like.

**Likely context, not yet confirmed with Joseph:** Hiking Observations already has a `vegetation` category in its keyword taxonomy (saguaro, bloom, cactus, tree, shrub, flower, plant, grass, palo verde, ocotillo — `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`), and BirdNET already gives the hiking pipeline an audio-based wildlife-ID precedent (CARD-0080/`birdnet-pipeline.md`). Photo-based plant ID would be the natural flora counterpart — but whether that's actually the intent here (an addition to the phone/hike workflow) versus something unrelated hasn't been confirmed.

**Done when:** not yet scoped — needs a real interview (what triggered this idea, phone-app vs. API-based identification, whether it's meant to integrate with the existing Hiking Observations pipeline or stand alone) before this moves to Planning.

**Related:** `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md` (Hiking Observations `vegetation` category), `components/hike-izer-orchestrator/birdnet-pipeline.md` (the audio-ID precedent this may be paralleling).

---

### CARD-0231 · [idea] [tos] Investigate Tasker's task import/export capabilities — get profiles/tasks into a reviewable format
**Status:** Planning

**Raised via idea email (PR #49, joscthomas+kbc@gmail.com), 2026-08-29** — Joseph's own framing: "investigating the import/export capabilities of Tasker. It would be nice to view the code."

**Why this is a real gap, not just curiosity:** every Tasker-side feature in this project (Log Observation queue/flush, GPSLogger flush, the Idea widget, etc.) is built and maintained entirely by hand on the phone — "Joseph builds and confirms the actual Tasker profile... matching this project's established division of labor for every prior Tasker-side feature" (per CARD-0156's own build notes). Unlike Node-RED, whose flows export to JSON and live in the repo (`core/node-red/*.flow.json`, `Node-RED-workflow.md`), no Tasker profile or task is ever captured anywhere Claude (or a future Joseph) can read it — every one of them is opaque outside the phone's own UI.

**What to investigate:** Tasker has a native Export action (profiles/tasks/projects to `.xml` — `.prj.xml`/`.tsk.xml`) via long-press → Export, or via a Task action. Worth checking: whether an exported XML is actually human/Claude-readable enough to be useful for review (vs. just a backup blob), whether it could be committed to the repo the same way Node-RED flows are (giving Claude real visibility into existing Tasker logic when debugging or extending it, instead of relying on Joseph's own transcription in kanban card write-ups), and whether re-import after an edit is reliable enough to make this a two-way sync rather than read-only documentation.

**Research done 2026-08-29 — Tasker's actual export/import mechanics, checked against this card's three open questions:**

**Mechanics:** long-press any Task, Profile, or Project in Tasker's UI → Export → writes an XML file (`<name>.tsk.xml` for a Task, `.prf.xml` for a Profile, `.prj.xml` for a whole Project), either to device storage or shared out through another app. Import is the reverse — open the XML with Tasker (or its own Import menu), which offers to add/merge/overwrite the matching-named object.

1. **Is the exported XML actually human/Claude-readable? Partially, not fully.** Literal content is readable — variable names (`%obs_ts`), string literals (URLs, file paths), and the overall action sequence/nesting (if/then blocks, loop boundaries) all show up as plain text, greppable/diffable. But each `<Action>` element identifies its *type* by an opaque numeric `code` attribute (Tasker's internal action-ID, not a name) — telling "HTTP Request" from "Variable Set" apart from the raw XML needs either a community-maintained code→name lookup table or opening it back in Tasker's own UI. Useful as a secondary, diffable ground-truth artifact — not a replacement for this project's existing prose write-ups (`observations-pipeline.md`-style) as the primary human-readable reference.
2. **Committable to the repo like Node-RED flows? Yes, no structural blocker.** Same shape as committing Node-RED's flow JSON. The only real gap is getting the file off the phone — Tasker's Export target can be a shared folder, email, or pulled via USB/adb; no blocker, just a step to establish (same category of thing BirdNET exports already do via AutoShare).
3. **Is re-import reliable enough for real two-way sync? Yes, and this is the strongest finding.** Export/import use Tasker's own native persistence format for that exact object type — not a lossy converter, it's literally how Tasker saves things internally, so round-trip fidelity should be solid. In practice, though, nobody hand-edits the XML directly — the natural workflow mirrors Node-RED's exactly: edit on-device in Tasker's own UI (unchanged from today's division of labor), then export and commit, not "edit the XML then re-import."

**Recommendation, not yet decided by Joseph:** adopt the exact Node-RED pattern (`Node-RED-workflow.md`) — Joseph keeps editing Tasker profiles/tasks on the phone as he does today, but after a change, exports and commits the XML to the repo (e.g. a new `components/hiking-monitor/tasker/` directory) so it's version-controlled and Claude has real ground-truth to read during debugging, alongside the prose docs that stay the primary explanation.

**Done when:** not yet scoped — still needs a real interview (does Joseph want to adopt the recommendation above; which existing Tasker profiles are in scope first — Log Observation/Flush Queue seem like the natural starting pair given they're already the most-documented-in-prose today) before a concrete build plan is written.

**Related:** `Node-RED-workflow.md` (the analogous export/version-control pattern already working for Node-RED), CARD-0156/`components/hiking-monitor/observations-pipeline.md` (an example of a Tasker profile currently undocumented except in prose), `tos/README.md` (the Tasker-originated webhook entry points into this project's automation).

---

### CARD-0229 · [idea] [hike-izer] Review BirdNET data architecture — storage and MQTT messaging — RESOLVED 2026-09-02
**Status:** Done

**Raised via idea email (PR #47, joscthomas+kbc@gmail.com), 2026-08-29** — voice-to-text mangled the original finding text to "where does the birthday to get stored" ("BirdNET" misheard). Confirmed with Joseph: the actual ask is a data-architecture review of BirdNET, same lens as CARD-0225's MQTT/docs-accuracy pass — where the data is stored, and how (or whether) it's represented in MQTT messaging — not a one-line factual answer. Deliberately not dug into in depth yet ("we'll deal with these later") — this card captures what's already been found so a later session doesn't re-derive it, plus the actual open question.

**Pipeline as it exists today**, per `components/hike-izer-orchestrator/birdnet-pipeline.md`:
```
BirdNET Live app (phone) → AutoShare → Tasker
    → POST /webhook/stage-file?kind=birdnet&key=<SECRET>
    → app.py _handle_stage_file()  →  <file_stem>_staging/
    → birdnet.py (generation time): parse_detections(), parse_occurrences()
    → templating.py: "Wildlife Heard" table + Route Map bird markers (baked into that hike's own published page)
    → wildlife_life_list.update_from_hike()
    → /srv/hike-izer-private/wildlife_life_list.json  (persisted cross-hike aggregate, on the M8)
    → components/hike-izer/build_wildlife_index.py → wildlife.html (standalone cross-hike index page)
```
Another instance of the "Tasker → direct HTTP webhook" family (like the Idea Tasker → `/webhook/idea` path from CARD-0225's discussion) — not MQTT, not Google Apps Script.

**Real difference from CARD-0225's three pipelines, found while reading `app.py`: this one already has MQTT log visibility, at least partially.** `_handle_stage_file()` calls `_log_mqtt_async(...)` (via `mqtt_log.py`, `jctsh/hike-izer/publish/log`) on both success (`"Staged {kind} file for {file_stem}."`) and every rejection path (missing key, invalid kind, empty body, no matching hike, write failure) — so this pipeline isn't blind on the dashboard the way Hiking Observations/GPS Track/email-idea-check.py were. Whether that existing logging is actually *sufficient* for a real architecture review (does it cover the per-hike parse step and the life-list JSON update, or only the webhook receipt itself?) is exactly what's still open — not yet checked.

**Review done 2026-09-02 — all four questions answered by reading the actual code, not inferred:**

**1. Parse-step outcome: not logged at all, confirmed.** `birdnet.py`'s `_load_export()` silently swallows `OSError`/`json.JSONDecodeError`/`zipfile.BadZipFile` and returns `None` on any corrupted or unreadable export — `_load_all_detections()` just `continue`s past it, no logging anywhere. `_load_all_detections()` itself also silently returns `[]` if the staging directory doesn't exist or nothing staged is a real BirdNET export. **Real, confirmed gap:** a genuinely corrupted BirdNET export (a truncated zip from a bad phone upload, say) produces an empty "Wildlife Heard" table on the published page — byte-for-byte indistinguishable from a hike where no birds were actually heard. No trace on the dashboard, no way to tell the two cases apart after the fact.

**2. `wildlife_life_list.update_from_hike()`: not logged either, and this one is a real data-loss risk, not just an observability gap.** `wildlife_life_list.load()` catches `FileNotFoundError` *and* `json.JSONDecodeError`, both silently returning `{}`. The write side (`update_from_hike()`) is **not atomic** — `open(path, "w")` truncates the file immediately, then `json.dump()` writes fresh content directly, no temp-file-plus-rename. If the orchestrator process dies mid-write (a real scenario — this container gets rebuilt/restarted routinely, including several times this session), the file is left truncated. The *next* hike's `update_from_hike()` call would then hit that truncated file, `load()`'s own fallback would silently treat it as an empty life list, and the entire cross-hike history (every species' first-heard date, every hike it's been heard on) would silently start over from zero — no error, no warning, nowhere.

**3. Should BirdNET data appear in the `jctsh/<type>/<component>/data` topic namespace? No — the current shape is actually correct, not a gap.** Unlike ESP32 environmental sensors (a live 30-second-interval stream Node-RED's wildcard handler consumes for Sheets/WU/HA in near-real-time), BirdNET data is parsed once, after the fact, from a batch export file staged well after the hike ends — there's no "live" moment for it to stream into, and nothing downstream would benefit from a topic that only ever fires once per hike. "Baked into the static page + the persisted life-list JSON, no live topic" matches the nature of this data. This is a judgment call, not a certainty — flagging for confirmation rather than closing outright.

**4. Is `/srv/hike-izer-private/wildlife_life_list.json` (and the private dir generally) durable? No — confirmed, and worse than just this one file.** Checked the M8's actual backup coverage (`components/photo-server/backup.md`): the weekly rsync backup only covers `/mnt/photo-library/` (Immich's library). **`/srv/hike-izer-private/` — the wildlife life list *and* every hike's own persisted `hike_data.json` — has zero backup coverage of any kind.** Combined with finding #2's non-atomic write, this is the real headline finding of this review: a single ill-timed container restart could silently wipe the entire cross-hike wildlife history, with no backup to recover from and no log line marking that it happened.

**Recommendation revised 2026-09-02, after Joseph pushed back on the first draft — the original "patch the local file's durability" framing didn't survive scrutiny.** First draft proposed an atomic write + bespoke backup coverage for `wildlife_life_list.json` in place. Challenged directly: why does this pipeline use a local JSON file at all instead of Google Sheets, like every other JCTsh data type? The two reasons originally given for that ("different data shape," "purpose-built consumer") don't actually hold up:

- **"Different data shape" was a conflation.** The *raw* per-hike detections (`parse_detections()`/`parse_occurrences()`'s own output — species, confidence, timestamp per detection/occurrence) are the exact same append-only shape as every other Sheets-backed data type (environmental readings, lightning strikes, hiking observations) — nothing structurally prevents a new "Wildlife Detections" sheet in the same "JCTsh Environmental Data" workbook, appended to the same way. Only the *cross-hike aggregate* genuinely needs update/merge semantics, and even that could be a **derived view** computed over the append-only Sheets data (a query/pivot, or `build_wildlife_index.py` computing "first heard" from raw Sheets rows) rather than requiring its own separately-maintained local store at all.
- **"Purpose-built consumer" doesn't distinguish BirdNET from anything else.** Environmental data already proves "Sheets archive + tailored webpage" isn't a contradiction — hike pages render environmental tables/charts by querying Sheets via Apps Script *at generation time* (`fetch_hike_data.py`'s `_fetch_hike_data()`). BirdNET's per-hike page could do the same.
- **"Avoids a network round-trip" doesn't hold either** — the generation pass already makes live Apps Script calls for environmental/GPS/observation data on every single hike; one more POST for BirdNET detections isn't new complexity, just more of what it already does.

**Honest conclusion: there's no real technical justification found for the local-JSON design — it looks like how BirdNET support simply got built (CARD-0080), not a deliberate architecture decision**, and it likely should have followed the same Sheets-archive pattern as everything else from the start. That reframes the fix: **the real problem isn't "the local file needs a backup," it's "this data shouldn't have a local file as its sole source of truth in the first place."** Sheets is already the durable, Google-backed archive every other data type relies on — routing BirdNET through it solves the durability question for free, instead of bolting on bespoke local-file backup handling for one pipeline.

**Implementation plan, 2026-09-02 — decisions resolved, two by mechanics (not real toss-ups), one by interview:**

1. **Write trigger: generation-parse time, not webhook-staging time.** `birdnet.py`'s `parse_detections()` output is already sitting in memory exactly where `generation.py`'s `run()` (line ~587) and `run_step2()` (line ~734) call it — adding the Sheets POST right there reuses that output directly. Parsing at webhook-staging time (`app.py`'s `_handle_stage_file()`) instead would mean parsing the export twice.
2. **Per-hike page's own read: unchanged.** Still reads the in-memory `birdnet_rows`/`birdnet_occurrences` directly, no Sheets round-trip — Sheets becomes an additional write (archive), not a new read dependency for the page itself.
3. **Cross-hike life list: interviewed, Joseph's call — keep `wildlife_life_list.json` as a fast local cache, not derive it fresh from Sheets on every build.** Avoids adding a network round-trip to every single hike publish (currently instant). Demoted from "sole source of truth" to "cache" — add a rebuild capability (regenerate from Sheets' full history) for the rare case it's ever lost, rather than treating the file itself as precious.
4. **Transport confirmed consistent with existing precedent, not a new pattern:** `generation.py` already makes direct HTTP calls to Apps Script for environmental/GPS/observation data during every hike generation — this is the exact same shape GPS Track and Hiking Observations already use (a fixed one-producer-one-consumer relationship, no MQTT/Node-RED involved, since there's no fan-out need). Not a special case.

**Concrete plan:**
1. **New "Wildlife Detections" sheet** in the "JCTsh Environmental Data" workbook — one row per species per hike, matching `parse_detections()`'s existing output shape directly (no transformation needed): `timestamp` (the species' own `first_timestamp`), `hike_file_stem` (join key back to the hike page/Environmental Data), `common_name`, `scientific_name`, `count`, `best_confidence`.
2. **New Apps Script write path** (`core/data-pipeline/environmental-data.gs`) — a new `doPost` branch (batch insert, since one call carries every species detected on a hike, unlike the existing single-row-per-call environmental payload), appending one row per `birdnet_rows` entry. **Read side needs no new code at all** — confirmed `action=export`'s `_exportSheet()` looks up sheets by name with no hardcoded allowlist, so the new sheet is immediately exportable via the existing generic mechanism.
3. **`generation.py` integration** — after `parse_detections()` returns in both `run()` and `run_step2()`, POST `birdnet_rows` to the new endpoint. **Best-effort, matching CARD-0227's/photo-fetch's existing convention** — wrapped in try/except, never blocks page publication (a Sheets outage shouldn't break basic hike-page generation). **Logged both ways, not just on failure** — an `Alert` if the POST fails, and (refined 2026-09-02, for real symmetry with Node-RED's own established pattern of confirming every successful Sheets append, not just failures) a routine `System` line on success too, e.g. `"Archived N species detections for {file_stem} to Wildlife Detections."` `generation.py` already has `mqtt_log.py` wired up for other log lines, so this is a direct, relay-free addition — unlike GPS Track/Hiking Observations (CARD-0225), which need a Node-RED relay since their phone-side callers have no MQTT access of their own.
4. **Finding #1 fix, folded into the same change since it's the same call site:** explicit logging distinguishing three states currently collapsed into one silent empty result — no staged file (not an error, nothing to report), a staged file present but zero detections parsed (worth flagging — possible corrupted export), and N species found (normal, worth a quiet confirmation).
5. **Rebuild capability** — a small new function/script that fetches the new sheet's full history via `action=export` (no date filter) and reconstructs `wildlife_life_list.json` from scratch, using the same merge logic `update_from_hike()` already has, seeded from Sheets instead of hike-by-hike. Manually invoked recovery tool, not part of the regular generation flow.
6. **Deploy:** paste the updated `environmental-data.gs` into the Apps Script editor, bump `SCRIPT_VERSION`, deploy a new version, verify via `action=version` (per this project's own established redeploy-verification gotcha, CARD-0099). Redeploy `generation.py`/`birdnet.py` to the M8 orchestrator, rebuild the container.

**Built, deployed, and verified 2026-09-02.** All six plan items above implemented as designed: new "Wildlife Detections" sheet + `doPost` branch in `environmental-data.gs`; `generation.py`'s `_archive_new_wildlife_detections()`/`_post_wildlife_detection()` wired into both `run()` and `run_step2()`, before `wildlife_life_list.update_from_hike()` mutates the local cache each call (dedup check reads the cache's pre-mutation state, avoiding duplicate Sheets rows on CARD-0214's daily refresh passes); `birdnet.py`'s `has_staged_export()` plus `generation.py`'s `_log_birdnet_parse_outcome()` for Finding #1 (a staged-but-unparseable export now gets an `Alert`, distinct from the ordinary no-file-staged case); `wildlife_life_list.py`'s `rebuild_from_sheets()` recovery tool. Deployed and confirmed identical to the repo: `environmental-data.gs` pasted/redeployed by Joseph (three iterations, see debugging story below), `generation.py`/`birdnet.py`/`wildlife_life_list.py` diffed byte-for-byte against `/app/*.py` inside the running `hike-izer-orchestrator` container.

**Historical-backfill design gap found before running anything, not live:** the dedup check in `_archive_new_wildlife_detections()` only consults the local `wildlife_life_list.json` cache — every hike processed before this feature existed is already "in the cache," so normal generation would never archive that pre-existing history to Sheets. Required a separate one-time backfill script (not part of the app, run via `docker exec` and deleted from `/tmp` afterward) reading the full local cache and POSTing every historical `(species, hike)` pair directly.

**Real debugging saga, 2026-09-02 — the first two fixes attempted were chasing the wrong bug entirely:**
1. **v1 (no locking):** first 164-row backfill attempt — `action=export` stayed at count 1 afterward. Diagnosed as a concurrent-`appendRow()` race (rapid-fire POSTs, the pattern Google's own docs warn about). Added `LockService.getScriptLock()`/`waitLock(30000)`, redeployed.
2. **v2 (locking):** retried the backfill, paced at 0.15s/row — `action=export` still stuck at the same pre-existing test-row count. Re-theorized as Apps Script's implicit end-of-execution `flush()` not committing reliably under back-to-back invocations. Added an explicit `SpreadsheetApp.flush()`, redeployed.
3. **v3 (locking + flush):** a small 10-row test batch worked. But three separate full 164-row reruns after that (492 POST calls total, every one reporting `{"status":"ok"}`) still showed `action=export` stuck at 12 rows — the flush() fix hadn't actually worked either.
4. **Joseph caught the real bug by looking at the live sheet directly, not through the API:** "I see 506 rows in the sheet" — followed by "All rows but your test data have blank timestamps." The rows had been there the entire time; nothing was ever lost. The actual defect was on the *read* side: `_exportSheet()` (`environmental-data.gs`, the function backing `action=export`) has `if (!tsRaw) continue;` — it silently skips any row with a blank column-A value. Every backfilled row had `ts: null` (the local cache never stored per-hike timestamps), so `action=export` filtered all of them out of every check I ran, while `appendRow()` had been working correctly the whole time. LockService and flush() were solving a problem that never existed — left in place since they're harmless and match the locking convention other write-heavy branches could reasonably want, but the misleading "found live" comments crediting them with a fix were corrected in `environmental-data.gs` to record the real story (no redeploy needed for that — comment-only).
5. **Real fix:** derive an actual timestamp for every backfilled row instead of sending `null`. 145 of 164 rows recovered their real per-detection timestamp by re-parsing the hike's own still-present staging export directly via `birdnet.parse_detections()` (14 of 15 hikes still had theirs on disk). The one exception — hike `2026-08-25`, whose staging export no longer exists — used a derived timestamp per Joseph's instruction ("derive a timestamp based on the other hike data"): the midpoint of that hike's real GPS session window (`2026-08-25T13:33:32Z` → `2026-08-25T16:59:49Z`, from the still-persisted `/srv/hike-izer-private/2026-08-25_hike_data.json`) = `2026-08-25T15:16:40Z`, applied to all 19 species recorded for that hike (`best_confidence` unrecoverable for these 19 — sent as `None`, a later column not implicated in the blank-column-A filtering bug).
6. Joseph manually cleared the sheet down to the header row (wiping both the test rows and the 491 blank-timestamp real-but-invisible rows together), and the corrected backfill was re-run once clean. **Final verified state, via `action=export`:** 164 rows, 0 blank timestamps, 15 distinct hikes — exactly matching the local life-list cache's own count.

**Done when:** the four original review questions all have real, code-verified answers — **met**. The implementation plan is written, decided, built, and deployed — **met**. The historical backfill is complete and verified against the live sheet, with every row carrying a real (not derived-as-a-placeholder-null) timestamp — **met**.

**Related, in addition to what's already listed above:** `core/data-pipeline/environmental-data.gs` (`doPost`, `_exportSheet`, `action=export`), `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md` (the schema/archive conventions this new sheet follows), CARD-0099 (the redeploy-verification gotcha this plan's deploy step follows).

**Related:** `components/hike-izer-orchestrator/birdnet-pipeline.md`, `components/hike-izer-orchestrator/app.py` (`_handle_stage_file`, `_log_mqtt_async`), `components/hike-izer-orchestrator/mqtt_log.py`, `components/hike-izer-orchestrator/wildlife_life_list.py`, `components/hike-izer/build_wildlife_index.py`, CARD-0225 (the sibling architecture-review card this generalizes the same lens from), CARD-0080 (original BirdNET integration), CARD-0182 (Live Mode → Survey Mode switch), CARD-0133 (interpolated-GPS occurrence markers), CARD-0147 (life-list "NEW species" badge). PR #47 (original idea-email finding, closed as covered by this card).

---

### CARD-0228 · [bug] [tos] email-idea-check.py failures are invisible to the log dashboard — only successful PR-opens get logged — RESOLVED 2026-09-02
**Status:** Done

**Raised 2026-08-29 (Joseph), during the same conversation that produced CARD-0225/CARD-0227** — checking whether `email-idea-check.py` (the `joscthomas+kbc@gmail.com` intake pipeline, CARD-0151) had the same MQTT-dashboard-invisibility problem CARD-0225 raised for three other phone-based pipelines. It doesn't, not fully — this is a narrower, partial version of that same class of gap, not the same card.

**What's already working:** the success path publishes to MQTT today — `_publish_log("System", 'Email idea -> kanban PR: "..." -- {pr_url}')` on `jctsh/core/log-server/log`, component `jctsh-core` — so a successfully-opened PR already shows up on the dashboard. This is why the pipeline wasn't included in CARD-0225's list of pipelines with zero MQTT presence.

**The real gap: the failure path has no equivalent.** In the main loop's `try/except` around `open_finding_pr()` and the Gmail "mark read" call, a caught exception only does `print(f"Failed to open PR for '{subject}': {e} -- leaving unread for retry")` — stdout/journal only, on the Pi. Nothing reaches MQTT, nothing reaches the dashboard. A silently-failing idea email (expired OAuth token, GitHub API hiccup, etc.) leaves no trace anywhere Joseph would normally look — the same shape of "looks fine, actually failed silently" problem CARD-0156 found and fixed for the Tasker observation queue, not yet caught here.

**Built, deployed, and verified live 2026-09-02.** Added an `Alert`-level `_publish_log()` call inside the existing `except` block around `open_finding_pr()`, wrapped in its own try/except so a broken MQTT publish can never mask the real failure by raising over it (`print("(also failed to publish...")` fallback). Deployed to the Pi (`/usr/local/bin/email-idea-check.py`, same `scp` + `sudo cp` pattern as every other Pi deploy this session).

**Real, deliberately-forced failure test, with a full backup/restore around it** — same discipline as CARD-0121's simulated-gap test:
1. Backed up the real `/etc/jctsh/github.env` (the GitHub PAT).
2. Needed a real unread `jctsh-idea` email to give the script something to process — re-marked an already-processed one unread. First attempt picked a message that had ended up in Trash, confirmed via a direct query that it doesn't match the script's own `to:kbc is:unread` search (Gmail excludes Trash by default) — found and used a different, still-in-INBOX one instead.
3. Overwrote `github.env` with a deliberately-invalid PAT, ran the real deployed script: `Failed to open PR for '(no subject)': HTTP Error 401: Unauthorized -- leaving unread for retry` — the failure path fired exactly as designed.
4. **Confirmed live on the real dashboard** (`/mnt/jctsh-logs/jctsh.log`, not just printed locally — same pending-buffer flush delay noted in CARD-0121/CARD-0227 encountered again here, resolved the same way, by waiting and rechecking): `2026-09-02 19:51:25 MST | jctsh-core | Alert | Email idea -> kanban PR failed for "(no subject)": HTTP Error 401: Unauthorized`.
5. **Fully restored afterward:** real PAT restored from backup, diffed byte-for-byte identical against the backup to confirm; both touched test emails marked back to their original read state; backup file removed. Final sanity run with the real PAT: `No new idea emails.` — clean, no leftover unread test messages that could get double-processed on the next real scheduled poll.

**Done when:** a deliberately-forced failure in this script (e.g. a bad GitHub PAT) produces a real, visible log entry on the live dashboard describing the failure, verified live — **met**.

**Related:** `tos/email-idea-check.py` (`_publish_log`, the `try/except` around `open_finding_pr()`), CARD-0151 (original build), CARD-0225 (the sibling card for the three pipelines with *no* MQTT presence at all — this card is deliberately kept separate since the mechanism and the fix are narrower), CARD-0156 (the analogous silent-failure fix on the Tasker side), CARD-0121 (the simulated-failure-test-with-backup/restore discipline this test followed).

---

### CARD-0227 · [enhancement] [tos] Support an image attachment on `jctsh-idea` emails, surfaced in the resulting PR — RESOLVED 2026-08-29
**Status:** Done

**Raised 2026-08-29 (Joseph), during a conversation about the email-idea-check.py intake pipeline** (`joscthomas+kbc@gmail.com`, CARD-0151) — wanting to attach a photo to an idea email and have it show up logged with the auto-opened PR, not just the text.

**Current gap, confirmed against the real code:** `email-idea-check.py`'s `_plain_body()` only ever walks the payload for a `text/plain` part — it never looks at attachment parts at all. Any image on a `jctsh-idea` email today is silently dropped; only the subject/body text reaches `open_finding_pr()`.

**What fetching it requires:** walk `msg["payload"]["parts"]` for a part with a `filename` and `mimeType` starting `image/`; if the data isn't inlined (`body.data`), a second Gmail API call against `body.attachmentId` (`GET .../messages/{id}/attachments/{attachmentId}`) to get the base64 bytes.

**Real wrinkle found in `open_kanban_pr.py`'s existing design:** `open_finding_pr()`'s PR body wraps the whole finding in a fenced code block (`` Finding:\n```\n{message}\n```\n\n ``), specifically so the raw finding renders verbatim. A markdown image reference (`![...](url)`) placed inside that fence does **not** render as an image — GitHub shows it as literal text. Making the image actually visible in the PR means restructuring the body template to place an image link *outside* the fence, not just appending it to `message`.

**The real open design question: where does the image get hosted?** A PR body can only carry a URL, not inline binary data, and that URL has to be fetchable by GitHub's renderer (i.e., reachable from the public internet). Options discussed, none decided:
- **Google Drive** — reuses the exact Google account/OAuth this pipeline already has, and the same Drive-folder pattern already used for Hiking Observations Path A. Upload via the Drive API, set link-sharing, embed the direct-content URL (`drive.google.com/uc?export=view&id=...`). Caveat: this hotlink format is a known-fragile, unofficial pattern — Google has changed/broken it before without notice.
- **Self-host on the M8** — already runs several Docker services (photo-server, Immich, NetAlertX) with an extensible serving pattern. Requires a new internet-facing exposure for GitHub's renderer to reach it — the same category of decision as the existing MQTT port-forward (`CLAUDE.md`'s "MQTT broker internet exposure" section), worth the same level of care.
- **Commit the image into the repo** — conflicts directly with CARD-0190's deliberate zero-file-diff PR design, and a direct write to `main` would likely be blocked by the same branch-protection rule that keeps this whole pipeline off `main` except through a reviewed PR.
- **A third-party image host** (e.g. Imgur) — new external account/dependency this project doesn't otherwise have.

**Decision made 2026-08-29 — self-host via the existing Cloudflare Tunnel, not Google Drive.** Checked `jctsh-network.md`/`components/hike-izer-web/README.md` before deciding: the M8 already has genuine, low-risk public exposure running today — `hikes.jctnet.com` (Cloudflare Tunnel, CARD-0094) serves `~/hike-izer-web-app/srv/` as static files. This is meaningfully different from the "new exposure" framing this card originally used (comparing it to the MQTT port-forward) — it's an outbound-only tunnel connection with no inbound firewall hole, already trusted and running for exactly this kind of purpose (serving hike photos/content publicly). Joseph's call: reuse it rather than add a Google Drive dependency and its hotlink fragility.

**Real wrinkle: `email-idea-check.py` runs on the Pi, not the M8** — the image has to cross hosts. Checked for an existing cross-host mechanism: `core/maintenance/pi1-backup-to-m8.py` already does a Pi→M8 push, but over a narrowly-scoped SSH key restricted (via `rrsync`) to one specific backup directory only — wrong scope to reuse as-is, and standing up a second dedicated SSH key/`rrsync` rule just for this is more infrastructure than the feature needs. Better fit: `hike-izer-orchestrator`'s `app.py` (already running on the M8, already accepts authenticated webhook POSTs with a secret key — same pattern as its existing `/webhook/stage-file` and `/webhook/idea` routes) is the natural receiver. Its current `_handle_stage_file()` is scoped specifically to a hike's own staging directory, so this needs a small new route alongside it, not a repurpose of that one.

**Plan:**
1. **New route in `app.py`** (M8, `hike-izer-orchestrator`) — e.g. `/webhook/idea-image?key=<SECRET>` — accepts a POST with image bytes, writes to `~/hike-izer-web-app/srv/idea-images/<id>.<ext>`, returns the resulting public URL (`https://hikes.jctnet.com/idea-images/<id>.<ext>`). Reuses the existing secret-key auth convention already used by every other route in `app.py`, and the existing `srv/` static-serving mechanism — no new SSH key, no new Cloudflare config.
2. **`email-idea-check.py`** (Pi): detect an image attachment part (per the "what fetching it requires" research above), fetch its bytes via the Gmail API, POST them to the new `/webhook/idea-image` route, get back the public URL.
3. **`open_kanban_pr.py`'s `open_finding_pr()`:** add an optional `image_url=None` parameter (keeps the other three existing callers — `pi-maintenance-check.py`, `maintenance-check.py`, the orchestrator's own `/webhook/idea` route — unaffected by default); when present, append a `![idea image](url)` markdown line to the PR body **outside** the existing fenced "Finding:" code block (the rendering wrinkle already found above), not appended into `message` itself.
4. **`email-idea-check.py`'s call site** passes the fetched image URL through to `open_finding_pr()` when an attachment was found.
5. Redeploy: `app.py` needs the M8's `hike-izer-orchestrator` container rebuilt (`docker compose up -d --build orchestrator`, per `components/hike-izer-orchestrator/README.md`'s existing deploy section); `email-idea-check.py` needs its own redeploy to the Pi (`scp` to `/usr/local/bin/email-idea-check.py`, per `tos/README.md`'s deploy table).

**Built and deployed, 2026-08-29 — all 5 plan steps done, server-side round-trip confirmed live:**
- `app.py`: new `_handle_idea_image()` handler + `/webhook/idea-image` route, `PUBLIC_SRV_BASE_URL` constant. Writes to `generation.SRV_DIR/idea-images/`, same directory Caddy's catch-all `file_server` block already serves at `hikes.jctnet.com` — confirmed no Caddyfile change needed (`components/hike-izer-web/Caddyfile`'s `/webhook/*` handle block already proxies anything under that path to the orchestrator, and the catch-all block already roots at `/srv/hike-izer`).
- `open_kanban_pr.py`: `open_finding_pr()` gained `image_url=None`; when present, a `![idea image](url)` line is appended to the PR body outside the "Finding:" fence, as planned. Existing callers (`pi-maintenance-check.py`, `maintenance-check.py`, orchestrator's own `/webhook/idea`) unaffected — parameter defaults to `None`.
- `email-idea-check.py`: `_find_image_part()` (recursive walk, same shape as the existing `_plain_body()`), `_ext_for_part()`, `_fetch_attachment_bytes()` (handles both inlined and separately-fetched Gmail attachments), `_upload_idea_image()`. Wired in as best-effort — a failed image fetch/upload logs a warning and the PR still opens text-only, doesn't lose the idea over an optional field.
- **Real cross-host wrinkle resolved during Build, not anticipated in the plan above:** `WEBHOOK_SECRET` (the same value already used by the Tasker "Log Idea" widget, `credentials.local.md`) had to be added to the Pi's own `/etc/jctsh/email-idea-check.env` — `email-idea-check.py` runs on a different host than the value was previously configured on. Added directly via SSH, confirmed present (`sudo grep -c` — exactly one occurrence, file permissions prevent a plain `grep` as the `pi` user).
- **Deployed:** `app.py`/`open_kanban_pr.py` → M8 (`~/hike-izer-web-app/orchestrator/`), `docker compose up -d --build orchestrator` — image built and container recreated cleanly. `email-idea-check.py`/`open_kanban_pr.py` → Pi's `/usr/local/bin/` (via `/tmp` + `sudo cp`, since that directory isn't writable by the `pi` user's own scp session).
- **Verified live:** a real 1×1 PNG POSTed directly to `https://hikes.jctnet.com/webhook/idea-image?key=...&ext=png` returned `{"status": "ok", "url": "https://hikes.jctnet.com/idea-images/<timestamp>.png"}`, and that URL fetched back `200 image/png` — the full server-side path (auth → write → public serve) works end to end. Test file cleaned up afterward. `email-idea-check.py` also run manually on the Pi post-deploy with real credentials — executed cleanly end to end (`WEBHOOK_SECRET` loaded, Gmail auth succeeded, correctly reported no pending emails).

**Real end-to-end test, 2026-08-29 — Joseph forwarded a real email (revised subject, attachment carried on the forward) to `joscthomas+kbc@gmail.com`.** Real MIME structure confirmed by inspecting the actual message: `multipart/mixed` → `multipart/alternative` (text/plain + text/html) + a sibling `image/png` part, `Content-Disposition: attachment; filename="Screenshot_20260829-055059.png"` — a genuine top-level attachment, not nested inside an embedded `message/rfc822` part and not inline-only. Confirms the forward/revised-subject scenario Joseph asked about works the same as a fresh email: the subject header is read as-is regardless of "Fwd:", and `_find_image_part()`'s recursive walk finds a top-level sibling attachment with no special-casing needed.

**First real run found and fixed a genuine bug, not anticipated in Build.** The email wasn't picked up on the first pass — not unread (Joseph had evidently opened it after sending; re-marked unread via the Gmail API to test properly). Once picked up, the image *was* correctly detected, but the upload itself failed: `HTTP Error 403: Forbidden`, caught by the best-effort fallback exactly as designed — PR #51 opened text-only rather than losing the idea. **Root-caused, not guessed:** compared `curl` (200) against Python's `urllib` (403, Cloudflare error code 1010) against the same endpoint from the same host — Cloudflare's bot-signature block was triggered specifically by urllib's default `User-Agent` header (`Python-urllib/3.x`), which is why the earlier direct-curl test during Build passed clean while the real script's first live run failed here. Fixed: added an explicit `User-Agent: jctsh-email-idea-check/1.0` header to `_upload_idea_image()`'s request — confirmed live this alone clears the block.

**Redeployed and re-verified against the same real email.** Closed the stale text-only PR #51 (superseded), re-marked the email unread, re-ran the real deployed script: no upload failure this time, opened **PR #52** with the image markdown line present and correctly placed outside the "Finding:" fence — `![idea image](https://hikes.jctnet.com/idea-images/20260829T235546028476.png)`. This is the real bar the "Done when" below asked for, met via an actual forwarded email, not a synthetic test.

**Done when:** a real `jctsh-idea` email with an attached photo produces a PR whose body shows the image actually rendered (not just linked as raw text inside the finding's code fence), verified live against a real sent email — **met**, PR #52.

**Related addition:** the `User-Agent` fix applies to every future upload through this path, not just this one test — no further action needed there.

**Known gap, deliberately out of scope for this card:** the image URL is only preserved in the PR body — `resolve_and_merge()`'s `_render_stub()` (the function that writes the final card text into `kanban-board.md` at merge time) doesn't currently carry `image_url` through, so an image visible during PR review would not appear in the permanent merged card. Worth a follow-up card if that persistence turns out to matter in practice.

**Related:** `tos/email-idea-check.py` (`_plain_body`, the Gmail polling loop), `tos/open_kanban_pr.py` (`open_finding_pr()`'s PR body template, `_render_stub()`), CARD-0151 (original email-idea pipeline build), CARD-0190 (the zero-file-diff PR design this must not break), `components/hiking-monitor/observations-pipeline.md` (the Drive-folder precedent for Hiking Observations Path A).

---

### CARD-0226 · [bug] [hiking-monitor] Rapid MQTT-attributed reboot loop during hike-data replay -- trigger unconfirmed, replay path not robust to it
**Status:** Planning

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

**Done when:** (1) the actual reboot trigger is identified via a real live capture, not just ruled-out candidates, and fixed or confirmed benign; (2) the replay path tracks delivery per-record (e.g. QoS 1 with a real broker ack, removing just that one line once confirmed) instead of all-or-nothing, so a mid-replay interruption -- from this bug or any future one -- can't cost real data; (3) verified live against a real hike with a large buffered-reading count, confirming no reboot loop and no data shortfall.

**Related:** CARD-0221 (Environmental Data coverage gap this reboot loop most likely caused), CARD-0222 (GPS correlation failure, very plausibly the same root cause), CARD-0205 (the debug UART this needs to actually catch the trigger live), CARD-0211 (the earlier, already-fixed task-watchdog crash during this same replay loop -- confirmed not a recurrence, but the closest prior precedent), CARD-0217 (the earlier ~270-reboot brownout storm -- same symptom shape, different and already-distinguished reset-reason signature), CARD-0180 (the restart button ruled out as this incident's trigger), CARD-0215 (the duplicate-reading rejection guard relevant to disentangling real loss vs. deduped resends), `components/hiking-monitor/hiking-monitor.yaml`.

---

### CARD-0225 · [bug] [infrastructure] MQTT architecture docs are inaccurate/stale, and phone-based intake pipelines are invisible to the log dashboard — RESOLVED 2026-09-02
**Status:** Done

**Raised 2026-08-29 (Joseph), during a conversation correcting/refining Claude's understanding of JCTsh's MQTT usage.** Two related but distinct problems surfaced, bundled into one card at Joseph's request rather than split.

**Part 1 — docs are wrong, not just incomplete:**
- `CLAUDE.md`'s architecture table (Mosquitto row) states "Nothing talks directly to anything else — everything publishes to a topic and subscribes to topics." False: both phone-based intake pipelines (Hiking Observations, GPS Track) talk directly to the Google Apps Script HTTP endpoint, no broker involved.
- `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`'s "Path B" still describes Tasker "publishing transcript text and recording timestamp directly to MQTT" for Hiking Observations — stale; the pipeline actually built (`components/hiking-monitor/observations-pipeline.md`, CARD-0156) posts straight to Apps Script over HTTP, no MQTT step at all. The two docs were never reconciled after the real build diverged from this plan.
- **No document states the actual governing principle** distinguishing when JCTsh uses MQTT vs. direct HTTP: a broker earns its place when a message needs fan-out to multiple (or future unknown) consumers — the ESP32 sensor pattern, one message consumed by Node-RED for Sheets + Weather Underground + HA/SmartThings. Direct HTTP is used where there's a fixed one-producer-one-consumer relationship — every phone-based pipeline talking to its one Apps Script/webhook endpoint. This is only inferable by comparing docs side-by-side today, not written down anywhere.

**Part 2 — real observability gap, not just a docs issue.** `core/logging/log_server.py` only ingests via MQTT subscribe (`jctsh/+/+/log`) — it has no HTTP ingest path at all, so anything not published to MQTT is invisible to the log dashboard that's supposed to be "persistent history of what every component has reported." Three phone-originated intake pipelines currently have no MQTT account and publish nothing to that topic space, confirmed against `CLAUDE.md`'s MQTT accounts table (no `hiking-observations`, no GPS-track, no orchestrator-webhook-idea entry beyond the orchestrator's existing unrelated account):
1. **Hiking Observations** (Tasker voice note → Apps Script `doPost`, `observations-pipeline.md`)
2. **GPS Track** (GPSLogger → Apps Script `action=gps`, `gps-pipeline.md`)
3. **Idea Tasker** (Tasker "Log Idea" widget → `/webhook/idea` → `hike-izer-orchestrator` → `open_finding_pr()`, `tos/README.md`)

**4. Hike Start Forecast — a gap nested inside gap #1, found 2026-09-02 while mapping MQTT visibility across the whole data pipeline (during CARD-0229's review).** `_maybeCaptureHikeStartForecast()` runs as a sub-step *inside* the same `action=gps`/GPS Track handler that item #2 above already covers — it's not a separate external caller, so it doesn't need its own relay mechanism. But it's a genuinely separate outcome (did the forecast snapshot actually get captured this call, or silently skipped/failed) nested inside a coarser one (did the GPS point land) — even once the Node-RED relay proposed below covers GPS Track generally, that would only confirm "the GPS point landed," not "the forecast was also captured." Needs its own explicit log call within the same relay, not assumed to be covered by GPS Track's own confirmation.

**Real platform constraint discovered, not just a design choice:** Google Apps Script has no MQTT client capability at all — it only has `UrlFetchApp` (HTTP/HTTPS request-response), no raw TCP sockets. So pipelines 1 and 2 (both Apps-Script-backed) cannot publish to MQTT directly under any circumstance; they need something reachable over plain HTTP that relays onward to MQTT on their behalf.

**Proposed mechanism, originally discussed but revised during Build 2026-09-02 after two real findings invalidated it (see below):**
- ~~Pipelines 1 & 2 (Apps Script-backed): a small new Node-RED flow (HTTP-in → MQTT-out)...~~
- **Pipeline 3 (hike-izer-orchestrator):** no bridge needed — the orchestrator already has its own MQTT account. Adding a publish call inside the existing `/webhook/idea` route handler is a direct addition to code that's already MQTT-connected.

**Built and verified live 2026-09-02 — two real findings changed the plan before any code was written:**

1. **The Idea Tasker gap (item 3) turned out to already be closed.** Reading `app.py`'s `_handle_idea()` (the real `/webhook/idea` handler, CARD-0173) found it already calls `_log_mqtt_async("System", ...)` on success and `_log_mqtt_async("Alert", ...)` on every failure path — full MQTT visibility already existed. This card's original claim that this pipeline "has no MQTT account and publishes nothing" was wrong when written (or the code changed since) — no new work was needed here.

2. **The proposed Node-RED relay mechanism can't actually work — a real network-reachability gap, not examined when the plan was drafted.** Apps Script runs on Google's own servers; only MQTT port 1883 is forwarded to the internet (DuckDNS + router port-forward, `CLAUDE.md`'s "MQTT broker internet exposure" section) — Node-RED's own HTTP-in port (1880) has no public path in at all. Apps Script's `UrlFetchApp` cannot reach it under any circumstance.

3. **Also found while verifying the "mirrors the ESP32 pattern" claim in the original plan: that claim was itself wrong**, a doc-accuracy problem inside the very card about doc accuracy. `data-pipeline.md` claimed "Node-RED also publishes a log message to MQTT confirming each row appended" — but the actual deployed `environmental-data.flow.json`'s `Check response` function only builds a message on the two failure paths; it returns `null` (no log) on every success. Corrected in `data-pipeline.md` directly (one-line wording fix, no code change).

**Revised mechanism, built instead:** `hike-izer-orchestrator` already had everything needed — a public HTTPS surface (`hikes.jctnet.com`, Cloudflare Tunnel, CARD-0227) and its own working MQTT connection (`mqtt_log.py`). A new `/webhook/pipeline-log` route (`app.py`, key-authenticated same as every other route there) accepts `{component, category, message}` and republishes to MQTT — `mqtt_log.publish_log()`/`_log_mqtt_async()` gained an optional `component` override (defaulting to this container's own identity for every existing call site) so relayed messages show up on the dashboard tagged as their own pipeline (`gps-track`, `hiking-observations`, `hike-start-forecast`), not lumped under `hike-izer-orchestrator`. No new port exposure, no Node-RED UI work needed at all — entirely Python, deployed by scp + `docker compose up -d --build orchestrator`, same as CARD-0229's changes.

`environmental-data.gs` gained `_relayLog(component, category, message)` — fire-and-forget, self-contained (swallows every failure mode internally so a relay hiccup can never break the actual write), calling the new orchestrator route via `UrlFetchApp`. `ORCHESTRATOR_WEBHOOK_KEY` added as a new Script Property (same value as the orchestrator's `WEBHOOK_SECRET`, `credentials.local.md`) so the endpoint URL itself stays out of source. Wired in at three points:
- **Hiking Observations** (`doPost`): logs `System` right after `appendRow()` succeeds.
- **GPS Track / Hike Start Forecast** (`_maybeCaptureHikeStartForecast`, called from `doGet`'s `action=gps` branch on every point): logs `gps-track` `System` **once per detected session**, not once per point — a GPS point lands every ~30s for a hike's full duration, so logging every single one would flood the dashboard for no benefit; this piggybacks on the exact same session-gap check the forecast feature already computes, so "a new session just started" is known cheaply without re-reading the sheet a second time. `hike-start-forecast` itself logs `System` on a successful capture and `Alert` on every distinct failure mode (Open-Meteo non-200, empty response, missing coordinates, any thrown exception) — the routine "continuing an existing session" skip stays silent, matching CARD-0229's Finding #1 precedent of only logging the notable case, not the routine no-op.

**Verified live 2026-09-02, real HTTP calls against the real deployed endpoints, not just code review:**
- Orchestrator relay tested in isolation first (`/webhook/pipeline-log` POST) — landed on the dashboard correctly tagged with a custom test component, confirming the override plumbing works end to end.
- A real test GPS Track point (`action=gps`, obviously-fake `acc=9999` for later cleanup) produced both `gps-track: New GPS session started.` and `hike-start-forecast: Captured hike-start forecast for 2026-09-02.` on the live dashboard.
- A real test Hiking Observation (`doPost`, source tagged `cardtest-0225`) landed the row correctly, but its relay log line didn't show up initially. Investigated rather than assumed: the row itself was confirmed written (`action=export`), and an isolated retest of the exact same component/message from the orchestrator landed cleanly seconds later — ruling out a mechanism bug. Root cause: the GPS and Observation test calls were fired about a second apart, tighter than any real usage pattern (real GPS points are 30s apart; voice observations are occasional) — the relay is deliberately fire-and-forget by design (same best-effort tolerance as MQTT QoS 0 elsewhere in this project), so an occasional dropped line under genuinely concurrent calls is an accepted trade-off, not a bug, and not realistic under real hike traffic.
- Test rows left in GPS Track / Hiking Observations / Hike Start Forecast from this verification — no delete endpoint exists (same situation as CARD-0229's backfill test rows); cleanup needs Joseph's manual pass over the Sheets UI.

**Done when:** the two doc inaccuracies are corrected and the fan-out-vs-fixed-pair principle is written down somewhere durable (`CLAUDE.md`'s new "MQTT vs. Direct HTTP" section) — **met**. All four original gaps produce a real log line visible on the live dashboard when exercised, verified against actual traffic — **met** (Idea Tasker was already met before this card; the other three verified live above).

**Related:** `CLAUDE.md` (architecture table, MQTT accounts table, new "MQTT vs. Direct HTTP" section), `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md` (Path A/B section rewritten to describe the actually-built direct-HTTP pipeline), `components/hiking-monitor/data-pipeline.md` (the "confirms each row appended" claim corrected to "error only"), `components/hiking-monitor/observations-pipeline.md`, `components/hiking-monitor/gps-pipeline.md`, `tos/README.md` (auto-PR intake pipeline diagram), `core/logging/log_server.py` (MQTT-subscribe-only ingest, no HTTP path), `components/hike-izer-orchestrator/app.py` (`_handle_pipeline_log`, `_handle_idea`), `components/hike-izer-orchestrator/mqtt_log.py` (`component` override), CARD-0156 (the build that made Path B's doc description stale), CARD-0227 (the Cloudflare Tunnel precedent this reused instead of new exposure), CARD-0229 (the BirdNET architecture review whose full-pipeline MQTT-visibility mapping surfaced the Hike Start Forecast gap, and whose Finding #1 "log the notable case, not the routine one" precedent this reused).

---

### CARD-0224 · [bug] [infrastructure] Low-battery-while-charging WiFi-attempt gating is undefined — real risk, not a corner case
**Status:** Planning

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

**Related:** `JCTsh-Build-Standards.md` §2.14 points 2, 9, 13, `components/hiking-monitor/hiking-monitor.yaml` (CARD-0212's existing `mqtt.on_connect:` battery check and `low_battery_shutdown` script — the pattern to fix and port), CARD-0198 (the Pololu testing that surfaced this while discussing point 13, and the source of real low-battery trial data once run), CARD-0217 (hiking-monitor's real sustained brownout-reset incident, the closest existing precedent for what this could look like if unaddressed), `components/air-quality-monitor/power-system-redesign.md` (the 3.4V cutoff-vs-dropout tension), `air-quality-monitor-claude-code-instructions.md` Step 8 (where air-quality-monitor's own version of this needs to be built).

---

### CARD-0223 · [enhancement] [infrastructure] Standalone LiPo battery charging station (TP4056)
**Status:** Planning

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

**Open item before Build:** confirm whether the EEMB cell(s) this gets used with already have a JST connector or bare leads — affects exactly how the battery-side connection is made.

**Done when:** a standalone TP4056 charging circuit is built (perfboard/breadboard, USB-powered, JST connector for the battery), and verified live by actually charging a real EEMB 1100mAh cell from a partial charge to full (TP4056's own onboard LED indicates charge status/completion, per its standard behavior) — not just wired and assumed to work.

**Related:** `jctsh-parts-inventory.md` (TP4056 modules, Bin A4; EEMB LiPo cells, Bag 7), CARD-0198 (the session this need surfaced during).

---

### CARD-0221 · [bug] [hiking-monitor] Environmental Data coverage dropped to 61.8% on the 2026-08-29 hike -- four real 7-10 min gaps
**Status:** Planning

**Raised 2026-08-29, found during a data-coherence review of the regenerated hike page (CARD-0220's own hike).** The corrected page (2h58m, 7.5 mi, 366 real GPS points) shows only **55 of ~89 expected Environmental Data readings (61.8% coverage)** at the normal ~2-min field-mode cadence -- and it's not a smooth shortfall, it's four distinct gaps well beyond the normal cadence: 13:04-13:11 (7.0 min), 13:56-14:06 (10.0 min), 14:51-15:00 (9.0 min), 15:32-15:39 (7.0 min).

**Every reading that day was field-mode** (buffered on-device to flash, replayed via MQTT once reconnected -- confirmed via `field_mode_readings: 55` in the fetched `hike_data.json`), so these gaps reflect real missed/skipped *local* readings on the device itself, not an upload or Sheets-write problem -- the device's own 2-min interval tick genuinely didn't produce (or didn't buffer) a reading during those windows.

**Real cause found, 2026-08-29, via the log dashboard's own state (`/mnt/jctsh-logs/state.json` on the Pi) -- a genuine reboot loop during replay, not a missed-reading problem during the hike itself.** The device reconnected at 08:45:23 MST (15:45:23 UTC, right at the hike's own end) and logged `"Replaying 116 hike readings..."` -- but only 55 of those 116 buffered readings ever landed in the Environmental Data sheet, a 52% shortfall. Between 08:45:32 and 08:46:07 MST (35 seconds), the device shows **10 separate `Field-mode boot` log lines** -- the first `reset reason: exiting deep sleep mode`, every one after that `reset reason: Reboot request from mqtt`, each immediately followed by exactly one `Display refreshed (field mode) at <timestamp>` line before the next reboot. This is a real, repeating reboot-mid-replay loop, not a brownout (contrast CARD-0217's earlier ~270-reboot storm, which logged empty reset reasons -- this one is cleanly labeled MQTT-triggered restarts throughout).

**Not yet confirmed: what's actually sending the repeated MQTT restart command.** `"Reboot request from mqtt"` is the reset-reason string ESPHome logs when `App.safe_reboot()` is called via its MQTT-triggered restart path -- CARD-0180 built exactly one such trigger (`hiking_monitor_restart`, a template button exposed to Home Assistant). Whether HA itself, some automation, or a stuck/retained MQTT command is what's actually firing this repeatedly hasn't been pinned down -- a live `mosquitto_sub` sweep of the device's full topic tree after the fact found no currently-retained restart-command message, which argues against a permanently-stuck retained payload but doesn't rule out a transient one that self-cleared. `esphome`'s own `safe_mode` component (running on its default config, no explicit block in `hiking-monitor.yaml`) also logged `"Boot seems successful; resetting boot loop counter"` on the eventual clean boot -- confirms ESPHome's own boot-loop detection recognized this as an abnormal rapid-reboot episode, consistent with the 10-boots-in-35s reading.

**Done when:** the actual source of the repeated MQTT restart command is identified (HA automation, a stuck client, a retry loop, or something else) and either fixed or the replay path is made resilient to a mid-replay reboot without losing buffered readings (currently: at least 61 of 116 buffered readings never made it to the sheet across this one incident).

**Related:** CARD-0220 (the false-positive-hike fix whose regeneration surfaced this), CARD-0222 (a second, related finding from the same review -- GPS correlation failure on the same hike's readings, very plausibly caused by the same reboot loop disrupting Node-RED's per-reading GPS lookup mid-burst), CARD-0217 (the earlier, larger ~270-reboot brownout storm -- same symptom shape, different reset-reason signature), CARD-0180 (the MQTT-triggered restart button this reset reason most likely traces back to), `components/hiking-monitor/hiking-monitor.yaml`.

---

### CARD-0222 · [bug] [data-pipeline] GPS correlation failed for 84% of the 2026-08-29 hike's Environmental Data readings -- not the CARD-0197 timing race
**Status:** Planning

**Raised 2026-08-29, found in the same data-coherence review as CARD-0221.** 46 of 55 Environmental Data readings from the 2026-08-29 hike have no lat/lon at all (`readings_missing_gps_coords: 46` vs. `readings_with_gps_coords: 9` in `hike_data.json`) -- an 84% miss rate, far worse than typical.

**Cross-referenced against the Correlation Debug sheet (CARD-0197's own instrumentation) and confirmed this is a *different* bug than CARD-0197 was built to catch.** `_gpsLookup()` logs a `lookup_miss` row every time its nearest-point search fails -- if this were CARD-0197's hypothesized race (the GPS point not yet written to the sheet at lookup time), all 46 misses would show up there. **None of them do.** Checked each of the 46 missing readings' own timestamps directly against Correlation Debug: zero matching `lookup_miss` rows for any of them.

**Working theory, not yet confirmed:** Node-RED's wildcard data handler calls the Apps Script `action=lookup&ts=<reading's own real timestamp>` per reading (confirmed via `environmental-data.flow.json` -- it correctly uses the reading's own embedded event time, not "now," so this isn't a naive timestamp bug). Since `_gpsLookup()` was never even invoked (no miss logged means the function never ran to completion), the HTTP call itself most likely never completed for these 46 -- plausibly Node-RED's handler getting overwhelmed, erroring, or silently dropping requests when all 55 buffered field-mode readings arrive in one rapid replay burst at hike-end, rather than trickling in near-real-time the way CARD-0197's design assumed.

**Strongly correlates with CARD-0221's real cause, found the same session: a genuine reboot loop during replay.** The device reconnected and began replaying 116 buffered readings at 08:45:23 MST, then rebooted 10 times in the next 35 seconds (9 of them with reset reason `"Reboot request from mqtt"`, a real MQTT-triggered restart loop -- not a brownout, see CARD-0221 for the full log evidence). A device that's mid-reboot when a buffered reading's MQTT message is meant to trigger Node-RED's `action=lookup` call would very plausibly drop or never send that HTTP request cleanly -- exactly the shape of failure this card already inferred (`_gpsLookup()` never even invoked, no miss logged, because the call never completed) but couldn't previously explain a *cause* for. This isn't confirmed as the definite mechanism yet -- it's a strong, evidence-backed correlation, not a proven causal chain -- but it reframes the "Node-RED overwhelmed by a rapid burst" theory from a guess into something with a real, observed trigger event to point at.

**Not yet investigated:** Node-RED's own execution/debug log around the exact 08:45:23-08:46:07 MST reboot-loop window (to see whether the `action=lookup` HTTP requests errored, timed out, or were never sent at all during that specific 35-second span), and whether the 46 GPS-correlation misses line up timestamp-for-timestamp with readings replayed during vs. between reboot cycles.

**Done when:** the actual failure point (Node-RED-side HTTP error, a rate/concurrency limit, or the reboot loop itself interrupting mid-publish) is identified with real evidence -- not just this correlation -- and either fixed or the gap is documented as an accepted limitation of the bulk-replay pattern. Likely resolves together with CARD-0221 once that card's reboot-loop source is found and fixed, rather than needing an independent fix.

**Related:** CARD-0197 (the correlation-debug instrumentation this diagnosis relies on, and the *different*, already-addressed race it was built to catch), CARD-0220 (the false-positive-hike fix whose regeneration surfaced this), CARD-0221 (the sibling Environmental Data gap finding from the same review -- now believed to share the same root cause, the MQTT reboot loop during replay), `core/data-pipeline/environmental-data.gs` (`_gpsLookup`), `core/data-pipeline/environmental-data.flow.json` (the Node-RED lookup call).

---

### CARD-0220 · [bug] [hike-izer] GPSLogger start/stop noise (on/off/on toggle) gets misclassified as a real hike and auto-published

**Status:** Done

**Raised 2026-08-29 (Joseph, via the "Log Idea" voice widget, PR #48: "clean up the false positives for starting hike"), then interviewed and fixed same session.** Real live incident: Joseph started GPSLogger for a hike, it errored and stopped 1.9 minutes later, then he restarted it 4 seconds afterward for the real ~3-hour hike. GPSLogger's own app-level events cleanly reported this as two distinct start/stop pairs -- pair 1 (12:48:36 -> 12:50:30 UTC, 1.9 min) and pair 2 (12:50:34 -> 15:46:42 UTC, the real hike). The automatic pipeline's first `stopped` webhook fired for pair 1 while it was the only data that existed yet, and `fetch_hike_data.py`'s `_classify_hike()` -- which only ever checked daylight and walking-pace -- had no floor on session length, so a 5-point, 0.03 mi, 0.9 mph cluster trivially passed both checks and was auto-published as `2026-08-29_hike-summary.html`, a real hike summary for something that wasn't a hike.

**Root cause confirmed directly from the orchestrator's own logs and a fresh Apps Script query**, not assumed: pair 1's 5 GPS points genuinely satisfied `DAYLIGHT_MIN_FRACTION` (1.0) and the walking-pace band (`WALKING_SPEED_MIN_MPS`/`WALKING_SPEED_MAX_MPS`, median 0.41 m/s / 0.9 mph) -- neither check has any concept of "long enough to plausibly be a walk someone set out on." A wider fetch of the full day's GPS Track confirmed the underlying trackpoints are physically continuous across both pairs (no gap over 10 minutes anywhere, since pair 2 started only 4 seconds after pair 1 stopped) -- one real ~178-minute, 7.48 mi hike, with a spurious ~2-minute false start at its own leading edge.

**Fix, `components/hike-izer/fetch_hike_data.py`:** new `MIN_HIKE_DURATION_MIN = 10.0` constant; `_classify_hike()` now computes each candidate session's own duration (first-to-last point timestamp) and rejects outright (`is_hike: False`, with its own explicit rejection reason) any session of **10 minutes or less** -- Joseph's explicit threshold, not a guess: "Any hike of duration 10 or less is not a hike." `duration_min` also added to the function's `details` dict alongside the existing `daylight_fraction`/`median_speed_mps` fields, for the same transparency every other classification signal already gets. This is the shared classification function used by both the interactive Skill and the automatic orchestrator pipeline (via the deployed copy in the M8's `hike-izer-orchestrator` container) -- one fix covers both paths, matching the established pattern from every prior hike-classification fix (CARD-0100/0101/0140).

**Verified against real data before deploying:**
- Pair 1's real 5-point, 2.0-minute blip: now correctly rejected (`is_hike: False`, reason cites the 10-min floor).
- The real full 177.6-minute session (366 points, 7.48 mi, 2.8 mph median): still classifies `is_hike: True`, unaffected.
- Checked against this project's own history for false positives: the shortest genuine hike ever recorded (~12.8 min, CARD-0140's card history) sits comfortably above the new 10-min floor.

**Deployed and confirmed live, 2026-08-29:** `fetch_hike_data.py` copied to the M8's `hike-izer-orchestrator` container directory, image rebuilt (`docker compose up -d --build orchestrator`), container healthy, `MIN_HIKE_DURATION_MIN`/the new `<=` check confirmed present in the running container's own copy of the file.

**Not part of this card's scope, deliberately:** recovering/correcting today's already-published `2026-08-29_hike-summary.html` (which reflects the now-known-wrong 2-minute blip, not the real 178-minute hike) -- that's a one-off data-recovery task for the specific hike already affected, tracked separately in conversation, not a repeat of this bug once the fix is live.

**Related:** CARD-0100/CARD-0101/CARD-0140/CARD-0144 (the file this shares `_classify_hike()`'s classification logic with, and the precedent for fixing hike-detection bugs there once and covering both the interactive Skill and the automatic pipeline), `components/hike-izer/fetch_hike_data.py`, `components/hike-izer-orchestrator/` (deployed copy).

---

### CARD-0219 · [idea] [back-patio-temp-sensor] Build back patio temp sensor
**Status:** Backlog

**Raised 2026-08-27 (Joseph).** A duplicate of `front-porch-temp-sensor` (ESP32 + BME280 + BH1750, temperature-threshold notifications for opening/closing doors — see that component's README for the full existing design), monitoring the back patio instead of the front porch.

**Interviewed 2026-08-27 — essence only, per this project's own new-card convention (deep design work is Planning-stage, not captured here):**
- **Purpose:** same as front-porch-temp-sensor — warm/cool threshold notifications for door open/close decisions, just for the back patio location.
- **Improvements over the original design:** deliberately left open. Joseph wants to "consider improvements" but has nothing specific in mind yet — a real look at `front-porch-temp-sensor`'s own design/card history (CARD-0165's Google Assistant work, any other lessons learned since it went to production) is worth doing at Planning, not guessed at here.

**Done when:** not yet defined — Planning will need to interview further (back patio's own location/mounting/power specifics, what if any improvements get chosen, notification/automation scope) before real acceptance criteria exist.

**Related:** `components/front-porch-temp-sensor/` (the design this duplicates and the source of whatever improvements get considered), CARD-0165 (front-porch-temp-sensor's own Google Assistant voice-query work, worth checking whether the same pattern should extend here).

---

### CARD-0218 · [enhancement] [air-quality-monitor] Expose SEN55's own temperature/humidity readings
**Status:** Build

**Raised 2026-08-27 (Joseph), during a conversation about SEN55's full sensor capabilities.** The SEN55 physically measures temperature and humidity alongside its main particulate/VOC/NOx readings, but `air-quality-monitor.yaml` deliberately left those two fields unconfigured in Phase 1 — documented reason (`sensor:` block comment): "those fields come from hiking-monitor, not this device's payload," avoiding two devices reporting redundant temp/humidity into the same Environmental Data schema.

**Motivation, interviewed 2026-08-27:** Joseph suspects air-quality-monitor's mounting/placement will give a *more accurate* temperature reading than hiking-monitor's BME280 (and possibly humidity too) — not redundant data, a genuinely useful second, independent reference. Intended use: compare the two devices' readings over time as a real calibration signal for hiking-monitor's own sensor, not just double-reporting the same thing.

**Scope, confirmed via interview:**
1. Configure `temperature` and `humidity` on the existing `sensor: platform: sen5x` block in `air-quality-monitor.yaml`, following the same pattern already used for `pm_1_0`/`pm_2_5`/etc. — `internal: false` (or otherwise however this device's other fields are exposed to its own MQTT payload/Environmental Data schema), reported the same way every other field in this device's payload already is (`source: air-quality-monitor`, same `temp_f`/`humidity_pct` field names the schema already uses for other sources like `front-porch-temp-sensor`/`hiking-monitor` — no new field-naming convention needed, this is an established wildcard-schema pattern).
2. **`temperature_compensation`/`acceleration_mode` explicitly left at default for now** (Joseph's call) — tuning either blind, before any real comparative data exists, would just be a guess. Revisit once real hiking-monitor-vs-SEN55 data is actually in hand.
3. **Out of scope for this card:** the actual calibration comparison/analysis itself (pulling both devices' readings for the same time window, checking agreement, drawing conclusions, possibly adjusting hiking-monitor's own BME280 reading or `temperature_compensation` based on findings) — that's real follow-on work once enough real data has accumulated from both devices, not part of this card's own "done."

**Rescoped 2026-08-27, same session — no `/data`/Environmental-Data path exists on this device yet.** Checked directly before implementing: `air-quality-monitor.yaml` has no `jctsh/components/air-quality-monitor/data` MQTT publish anywhere — this device currently only publishes to `/log` (30s bench-validation) and `/heartbeat` (5min). The real Environmental Data pipeline is Step 8 work (`air-quality-monitor-claude-code-instructions.md`), not yet built. Original Done criteria (Environmental Data sheet verification) couldn't be met as written for *any* of this device's readings, not just temp/humidity. **Joseph's call: keep it simple** — expose the fields and verify via the existing `/log` topic (what's actually possible today), not build Step 8's real pipeline as a side effect of this card.

**Built and compiled clean, 2026-08-27.** `temperature`/`humidity` added to the `sensor: platform: sen5x` block (`sen55_temp`/`sen55_humidity`, °F conversion filter matching this project's convention, `temperature_compensation`/`acceleration_mode` left at default per the interview decision above), both added to the existing 30s `/log` payload lambda alongside PM/VOC/NOx. `config_hash=0x0d0a09f4`, `build_time_str=2026-08-27 16:23:08 -0700`. **Not yet OTA-flashed or live-verified** — compile-clean only so far.

**Real, bigger finding surfaced while making sure Step 8's own design accounts for these fields (Joseph's follow-up ask, same session) — this device is missing a whole signal category, not just two sensor readings.** Step 8's design already planned a bounded-WiFi-retry-while-charging mechanism for this device — the exact same design mistake CARD-0045/CARD-0217 just found and fixed on hiking-monitor (using a charging/dock signal as a proxy for "safe to try networking," when it isn't one). Corrected Step 8's text to match the new standard (`JCTsh-Build-Standards.md` §2.14 point 11) — but doing so surfaced that air-quality-monitor has **no Intent signal at all**: its 2026-08-19 design decision was "dock-detect-only for firmware mode-switching... no GPIO-based manual mode switch," meaning `dock_detect` (Power Connected) has been standing in for Intent from the start, with nothing to actually distinguish them. Formalized as the three-signal model in §2.14 point 12 (Intent / Power Connected / Power Switch, each required independently) — this device has Power Switch (its inline battery-path cutoff) and Power Connected (`dock_detect`), but genuinely lacks Intent. **Resolved same session, 2026-08-27 — a real design decision, not just a flagged gap.** Confirmed via the actual instructions doc that the device is still breadboard-stage (battery/LDO wired per Step 7, perfboard transfer not yet reached) — the right moment to fix this before anything's soldered permanently. Decided: swap the existing Gebildet SS12D10 slide switch (currently wired as the inline Power Switch, no GPIO) onto **GPIO27** (previously unused) as a real, GPIO-readable **Intent switch**, matching hiking-monitor's own pin/pattern exactly — and give Power Switch its own distinct part instead, a **BK-1208 latching push button** (same part chosen for hiking-monitor's CARD-0181; one order covers both devices). Per §2.14 point 12, Power Switch and Intent can't safely share a physical control, and per the earlier switch-design discussion (CARD-0181), Power Switch specifically needs to feel different from whatever's doing Intent duty — since this device's *existing* switch was already a slide type, the fix here is the mirror image of hiking-monitor's: give Power Switch the new part, not Intent. `air-quality-monitor-claude-code-instructions.md`'s Hardware Context, GPIO table, Step 1, and Step 8 all updated to reflect this as the current wiring plan — not yet physically rewired on the breadboard, not yet ordered.

**Done when:** `temperature`/`humidity` are configured on the SEN55 sensor block (met), firmware compiles clean (met), deploys to the real device via OTA, and both fields are confirmed reporting live, sane, non-NaN values on the `/log` dashboard — verified against real data, not just a clean compile.

**Physical rewiring sequencing, 2026-08-28 — folded into CARD-0198 rather than scheduled separately.** CARD-0198 is about to rebuild this device's power wiring anyway (regulator swap), so this card's own SS12D10→GPIO27 move and the new BK-1208 (latching push-button power switch) installation happen as one physical pass under that card's plan, not as a separate teardown. **Not blocked on delivery** — BK-1208 ordered but not yet on hand; a spare SS12D10 (slide switch, Bin A3 assortment) fills the Power Switch role on the breadboard in the meantime, same wiring/node, swapped for the real part once it arrives.

**Related:** `components/air-quality-monitor/air-quality-monitor.yaml` (the `sensor: platform: sen5x` block, the `/log` payload), CARD-0198 (this device's own boot-sequence/reliability work, same firmware file — now also where this card's physical rewiring happens), `components/hiking-monitor/hiking-monitor.yaml` (the BME280 this will eventually be compared against), `air-quality-monitor-claude-code-instructions.md` (Step 8, corrected to match §2.14 point 11 and flagged for the Intent-signal gap), CARD-0045/CARD-0217 (the hiking-monitor fix this all traces back to), CARD-0181 (hiking-monitor's mirror-image gap — missing Power Switch instead of Intent, same BK-1208 ordering blocker), `JCTsh-Build-Standards.md` §2.14 points 11-12 (the standards this raised).

---

### CARD-0217 · [bug] [hiking-monitor] Progressive heat/brownout degradation mid-hike (2026-08-27) — a real reset crisis followed by an ~85-minute total device blackout, not a contained 9-minute event
**Status:** Build

**Raised 2026-08-27 (Claude, found investigating today's hike at Joseph's request).** Joseph asked for a look at hiking-monitor's performance and Mile Announcer (CARD-0208) from today's hike (field mode switched on ~05:30 MST). Checked the Pi's persistent log (`jctsh.log`, not just the rolling `state.json` window) for the whole session.

**What happened, reconstructed from real log data — corrected 2026-08-27, later the same day, once the actual Environmental Data readings and their timestamps were checked directly rather than relying on the first-pass summary below.** The original write-up (kept below, struck through in spirit though not in markup, for the record) understated this significantly — it wasn't an isolated 9-minute event with a clean recovery on either side:
- `~05:20` — field mode starts (GPS/webhook-confirmed: hike ran 5:20 AM–8:51 AM MST, 3h31m, 7.0 mi, 1201 ft gain).
- **From the very first readings, the device was already struggling** — the real Environmental Data readings that reached the Sheet show irregular gaps of 6, 17.6, 19.8, 23, and 30.2 minutes between readings that should be exactly 2 minutes apart, starting well before the acknowledged crisis window. Battery voltage fell steadily and continuously the whole time: 3.95V at 5:22 AM → 3.40V by 7:26 AM — a real, sustained decline under heat, not a blip.
- `07:22:36-07:30:56 MST` (~2 hours into the hike) — **the acute crisis**: buffered `{"event":"reset",...}` records (CARD-0216's just-deployed unconditional reset-reason logging) show roughly **273 reboots inside a ~9-minute window**, with `nan_sensor` skips (BME280/LTR-390 read failures) interleaved — the tail end of the same degradation trend above, not a separate event.
- **`07:30:56 MST` onward — total silence, ~85 minutes.** No further reset events, no display refreshes, no sensor readings of any kind appear anywhere in the buffered log after this point, even though the hike (per GPS) continued until 8:51 AM. The very last thing replayed from the device's buffer is a block of 126 consecutive, uninterrupted reset events with no successful cycle in between — consistent with the device dropping into a persistent brownout-reset loop it never broke out of on its own (the same failure mode CARD-0026 first characterized on the test rig: SPIFFS math rules out a full buffer as the cause — 745 lines at ~150 bytes each is ~112KB against a 1.47MB partition).
- `08:56:29 MST` — device reconnects and replays its buffer, **only once external USB dock power was applied** — strongly suggesting that's what finally let it complete a boot cycle, not that it recovered on its own sometime during the silent window.

**This changes the read on the incident: it wasn't a contained 9-minute crisis with a clean recovery on either side — it was a progressive heat/brownout failure across most of the hike, climaxing in an acute burst, followed by roughly a third of the hike's total duration (85 of ~211 minutes) with the device effectively down and producing zero data, only resolved by external power at the dock.** This is a stronger argument for revisiting CARD-0070 (the deferred LDO+gate hardware fix) than the original framing implied.

**A related, separate finding — resolved same day, not a hike-izer bug.** The hike-izer page initially showed only "1 of 106 expected" Environmental Data readings, though the Sheet had 14 real rows for hiking-monitor that day. Root cause, confirmed via the orchestrator's own logs: the automatic `stopped` webhook fired at 8:52:21 MST (right when GPS logging ended) — while the device was still down in its brownout loop — so step 1's generation ran and published immediately against whatever was in the Sheet at that instant (1 reading). The other 13 didn't land in the Sheet until the device's own replay completed at 8:56:31-8:57:11 MST, a few minutes after the page had already published. Joseph's own hypothesis on this, confirmed exactly: *"I think the webpage was generated before all the data was uploaded because the battery was dead and took a while before the data uploaded."* No code fix needed — CARD-0211/CARD-0214 already built exactly the mechanism for this (`run_step2`'s gap-fill re-fetch, re-issuing the same persisted query window). Triggered it manually (`docker exec hike-izer-orchestrator python3 generation.py --step2 2026-08-27`); the live page now correctly shows 14 of 106 (13.2% coverage), 91.4-111.2°F, battery 3.40-3.95V.

**Two distinct things to fix, not one (unchanged from the original scoping):**
1. **A real bug in CARD-0216's own new instrumentation, found by its first real use:** every single one of the ~270 reset events logged an **empty reset reason** (`"Field-mode boot, reset reason: "`, blank). The `debug:` component's `reset_reason_text` sensor is read very early in boot (`on_boot` priority 600, right after `hike_log_begin()`) — plausibly before that sensor has actually been populated with a real value for every reset path. This means we now have solid *evidence* the crisis happened, but no evidence of *why* (brownout vs. watchdog vs. something else) — exactly the diagnostic CARD-0216 was built to provide, undermined by reading the value too early.
2. **The underlying cause of the crisis itself, not yet root-caused.** Leading suspect: heat-driven brownout — later heartbeats the same morning show ambient temps in the 107-116°F range, matching this project's existing pattern (CARD-0198's air-quality-monitor brownout investigation, CARD-0211's hiking-monitor reset loop, CARD-0213's resulting peak-current-headroom standard). hiking-monitor's own hardware-side mitigation (CARD-0070, the LDO+gate swap) was deliberately deferred/not built — this incident is a real, concrete data point arguing for revisiting that decision, not just a firmware-side fix.

**Open questions for Planning:**
- Fix the reset-reason-text timing bug first (quick, mechanical — read the sensor later in boot, or re-read it if the first attempt comes back empty) so the *next* incident (if the underlying cause isn't fixed) is fully diagnosable, rather than waiting on the harder root-cause work.
- Whether to reopen/revisit CARD-0070 (the deferred LDO+gate hardware fix) given this is now a second real field incident of the same class, not just a bench-measured risk.
- Whether ~270 reboots in 9 minutes is even survivable without real risk to the LiPo cell (repeated brownout cycling under heat) — worth a real assessment, not just "it recovered fine this time."

**Item 1 (blank reset-reason bug) — root-caused, fixed, and deployed, 2026-08-27.** Confirmed against ESPHome's own `debug` component source (`esphome/components/debug/`) that `reset_reason_` is only ever populated inside `dump_config()` (via `publish_state()` in `get_device_info_()`), never during `setup()` — and ESPHome runs `dump_config()` for the whole app as a distinct, later pass, strictly after every component's `setup()` (which includes every `on_boot` trigger, regardless of its own `priority:` value — `on_boot` triggers are themselves `setup_priority`-ordered components, not a separate later phase). This is why the read was empty at *any* `on_boot` priority, not just the one CARD-0216 happened to pick — there's no priority number that fixes it.

**Fix:** `on_boot` (priority 600.0) no longer reads `reset_reason_text` directly — it only sets a new `reset_reason_pending` global (cheap, no dependency on the debug sensor) when the field-mode condition (switch on, dock off) is met. The actual read-and-log now happens on the first tick of the existing 2-min `interval:` block, gated on that flag — confirmed via ESPHome's own `interval` component source that its default `startup_delay` is `0s`, so the first tick fires essentially immediately once `loop()` starts, not after waiting a full 2 minutes. That timing mattered specifically because the real incident showed resets roughly every 2 seconds — a fix that only became safe to read after a full interval period would never have captured data during a rapid reset storm like this one.

Compiled clean (`config_hash=0x03da5a31`, `build_time_str=2026-08-27 10:44:22 -0700`), OTA-flashed to the real device at `192.168.1.161` (reachable, device happened to be in an upload-mode window), confirmed a clean reboot and reconnect to MQTT afterward — no crash loop. **Not yet verified against a real field-mode reset event** — that reboot was a normal OTA-triggered restart (switch off / on dock), which doesn't exercise the `reset_reason_pending` gate at all (field-mode condition not met), so whether `reset_reason_text` genuinely comes back non-empty under this new deferred-read approach still needs a real field-mode reset to confirm. Stays in Build, not Done, until that's observed.

**Item 2 (heat/brownout root cause) — a real firmware-level contributor found, fixed, and deployed same day, 2026-08-27** (hardware-side heat/brownout margin, CARD-0070, is still a separate open question — see below).

**Finding:** field mode never actually turned WiFi off. `in_field_mode` elsewhere in this file is just what gets *inferred* when a connection attempt happens to fail (no known network on the trail) — nothing was ever telling the WiFi component to stop trying. Grepped the whole file for `wifi.disable`/`wifi.enable`/any WiFi power control: zero matches, confirmed directly rather than assumed. Every failed association attempt during a multi-hour hike still powers up the radio and draws the same class of current spike CARD-0026 already found brownout-triggering on the test rig (180-250mA TX/RX bursts, cross-checked against Espressif's own datasheet figures) — plus a real, continuous 20-68mA "modem-sleep" baseline between attempts, for a radio that had zero chance of reaching anything out on a trail. This is very likely the actual trigger behind both the slow degradation through the whole hike and the acute crisis, not heat acting alone — this matches the intended design (Joseph: "switching off field mode and when the device is docked, that's when wifi or hotspot connection begins") that the firmware had just never actually implemented.

**Second, independent piece of evidence for the same finding, found while reviewing today's log more closely.** Joseph reported seeing the device's "Uploading" display sequence mid-hike, not just at the real dock event — checked directly against the Pi's log: at `05:22:51-05:23:18 MST`, only ~3.5 minutes after the last home-mode heartbeat and ~2 minutes into the hike, the device genuinely reconnected to MQTT, replayed 3 already-buffered readings (correctly triggering CARD-0199's Connected→Uploading→Done sequence), logged one reset, then disconnected again at `05:23:18` and stayed offline until the real 08:56 dock. Joseph confirmed the Pixel hotspot was never on during this hike, ruling that out; most likely explanation is the device was still physically near home (matching the hike's own starting GPS coordinates, shared with many other hikes' start/end points) in the few minutes before truly setting out, briefly within reach of home WiFi before losing it — not conclusively confirmed which network, but the underlying point holds regardless: nothing was stopping WiFi from opportunistically reconnecting to *any* reachable configured network the moment field mode started, triggering an unwanted premature upload cycle. Today's WiFi-disable fix should eliminate this too, not just the later brownout cascade.

**Fix:** `on_boot`'s existing field-mode block (switch on, dock off) now also sets a `wifi_disable_pending` global; the interval block's already-established-safe first tick (from item 1's fix) calls `wifi.disable` when that flag is set. Confirmed via ESPHome's own `core/config.py` that `on_boot` triggers are registered as real `Component`s in the normal `setup_priority`-ordered sequence (default/this file's priority 600.0) — and WiFi's own setup priority is 250.0 (`network/__init__.py`'s `NETWORK_PRIORITY_BASE`), which runs *later* in that ordering — so `wifi.disable` genuinely cannot be called safely from the priority-600 `on_boot` block itself, only from the interval's first tick (confirmed safe, post-setup).

Re-enabling on dock connect needed the same care: `dock_detect`'s `on_state` handler now calls `wifi.enable`, but gated on a `lambda: 'return App.is_setup_complete();'` check — confirmed via ESPHome's `gpio_binary_sensor.cpp` source that a GPIO binary_sensor's first `publish_state()` (and thus its `on_state` trigger) fires synchronously inside its own `setup()` at `HARDWARE` priority, before WiFi's own `setup()` has run — the common "device boots already plugged into USB" case hits this every time, and `WiFiComponent::enable()`'s own source (`wifi_component.cpp`) confirmed it genuinely depends on state `setup()` initializes (`pref_`, the driver) — unsafe to call that early, and also unnecessary in that exact case since a boot that starts already-docked never took the field-mode branch to begin with. `App.is_setup_complete()` is what distinguishes that unsafe/unneeded boot-time firing from a real later transition (the actual case this exists for: the device gets plugged in mid-hike or at hike's end *without* a reboot in between, same as today's own 08:56:29 MST dock-and-replay moment — without this handler it would just stay WiFi-disabled indefinitely once docked, never reconnecting).

Compiled clean (`config_hash=0xde781d15`, `build_time_str=2026-08-27 11:55:04 -0700`), OTA-flashed to the real device, confirmed clean reboot + MQTT reconnect (this boot happened to start already-docked — confirmed the new `App.is_setup_complete()` guard correctly didn't fire `wifi.enable` early, and WiFi/MQTT still connected normally since it was never disabled on this boot). **Not yet verified against a real field-mode hike** — the actual current-draw reduction and reset-avoidance still need a real trail session to confirm, not just a clean bench/dock boot.

**Follow-on fix, same day, closes CARD-0045 too.** The `dock_detect`-triggered `wifi.enable()` above was originally unconditional (any dock connect, regardless of switch position) — but `dock_detect` also goes HIGH from the SUNYIMA solar panel (shared IN+/IN- pads), which can happen mid-hike with the switch still on. Joseph asked the right question: *"What is the purpose of trying to connect wifi when in the field?"* — none; solar connecting mid-hike is a pure power event, uncorrelated with (if anything, inversely correlated with) network availability. Fixed by requiring `binary_sensor.is_off: slide_switch` alongside `App.is_setup_complete()` for the `wifi.enable()` call — WiFi now only ever re-enables on a genuine "hike is over" signal (switch off), never just because something got plugged in while still hiking. This directly resolves CARD-0045's long-open "unbounded WiFi retry via solar/dock_detect overlap" finding — see that card for the full resolution writeup. Compiled clean (`config_hash=0xb98022dc`, `build_time_str=2026-08-27 15:36:09 -0700`), OTA-flashed, confirmed clean reboot + MQTT reconnect.

**Hardware-side margin (CARD-0070) — still an open question, not resolved by the WiFi fix above.** Whether to also revisit the deferred LDO+gate swap remains on the table — the WiFi fix should remove the specific trigger this incident's evidence points to, but doesn't address the underlying boost-converter quiescent-current/margin issue CARD-0070 was raised for in the first place, and doesn't fully retire it as a live concern until a real field hike confirms resets are actually gone.

**Item 3 (hike-izer's "1 of 106" undercount) — resolved same day**, see the "related, separate finding" note above. No code change — CARD-0211/CARD-0214's existing `run_step2` gap-fill mechanism already handles this class of problem; just needed triggering.

**Related:** CARD-0216 (the reset-reason logging this incident is the first real test of — confirms its own underlying hypothesis about silent mid-hike resets, while exposing a bug in its own implementation), CARD-0211 (the prior reset-loop incident, different context — upload-time watchdog timeout, already fixed), CARD-0198/CARD-0213 (air-quality-monitor's own brownout investigation and the resulting peak-current-headroom standard — the same physics likely applies here), CARD-0070 (the deferred hiking-monitor hardware fix this incident is a real argument for revisiting), `components/hiking-monitor/hiking-monitor.yaml` (the `on_boot` reset-reason-pending flag, the `interval:` block's deferred read, `debug:` component).

---

### CARD-0216 · [bug] [hiking-monitor] Zero display_refresh events logged during a real multi-hour hike, despite the code's own logic guaranteeing several — RESOLVED 2026-08-27
**Status:** Done

**Raised 2026-08-25 (Joseph), pointing out that today's 2026-08-25 hike (6:33 AM-9:59 AM confirmed GPS session; device's own field-mode window 05:23-11:55 MST, ~6.5 hours per CARD-0211's timeline) was exactly the real multi-hour field session CARD-0196's own "done when" bar was waiting on — a natural moment to check whether the ~20-minute display-refresh cadence actually held.**

**It didn't get the chance to — zero `display_refresh` events exist anywhere in today's real hike data at all.** Checked directly against the log dashboard: the only two `"Display refreshed (field mode) at ..."` entries on record are both from this evening's separate ~3-minute CARD-0212 test walk (`2026-08-26T00:13:49Z`, `2026-08-26T00:17:46Z`). Nothing from the real 05:23-11:55 MST field session shows up at all — not even the mandatory refresh the code's own logic guarantees on the very first valid cycle after any boot (`field_display_cycle` starts at 0, and `0 % 10 == 0` is always true).

**Investigated directly, several plausible explanations checked and ruled out, root cause not found:**
- **Not a SPIFFS buffer/eviction issue** — `hiking_logger.h`'s `hike_log_write()`/`hike_log_replay_stream()` are plain append-only file operations (`fopen(..., "a")`, streamed read, no size cap, no ring-buffer eviction) — read directly, confirmed nothing could silently drop early entries before `hike_log_clear()` runs (which only fires after a full successful replay).
- **Not connectivity flicker resetting the counter** — `field_display_cycle` resets to 0 on any cycle where `in_field_mode` is false (i.e., MQTT connected), which could plausibly happen if hiking-monitor's cellular-hotspot MQTT path connected/disconnected repeatedly during the hike. Checked directly: **zero MQTT connect/disconnect events exist in the log for the entire 05:xx-09:xx MST window** — the device was purely, continuously offline throughout, so this reset path never should have fired.
- **Not a logic bug in the throttle check** — `hiking-monitor.yaml`'s interval block (`if (field_display_cycle % 10 == 0) { ...write refresh...; field_display_cycle++; } else { field_display_cycle++; }`) is straightforward; starting from any fresh 0 guarantees a refresh-and-log on the first valid cycle.
- **Not a broken clock** — the same `ts` variable (built from the NTP-synced clock) feeds both the regular sensor-reading payload and the refresh-event payload; today's 102 real Environmental Data readings (CARD-0215's own verification) all carry sane, correct real timestamps, ruling out a clock problem specifically breaking the refresh-event branch.

**Expected vs. actual:** ~111 valid (non-skip) cycles occurred during the real hike (matches a ~6.5hr session at 2-min cadence, consistent with the 125 buffered lines minus 13 `clock_invalid` skips and ~1 `nan_sensor` skip). At the code's own stated cadence, refreshes should have logged at roughly cycles 0, 10, 20, ... 110 — about 12 events. Zero appeared.

**Open for Build — no working hypothesis left after the above eliminations. Candidates worth checking, not yet investigated:**
- Whether `id(field_display_cycle)` is genuinely the same global instance being read/written across every path (an ESPHome id-scoping issue would be unusual but not yet ruled out by inspection alone).
- Whether the device reset one or more times *during* the real hike itself (not just during the later upload reset-loop) in a way that's still consistent with continuous field-mode operation but somehow prevents the counter from ever landing on a multiple of 10 — needs the actual reset-reason/boot-count evidence checked, not assumed.
- Whether `hike_log_write()`'s buffered refresh-event lines exist in the raw SPIFFS file but got mis-parsed or silently dropped somewhere in the replay-to-MQTT-to-Node-RED path specifically for this event type, despite the routing having been verified with synthetic test publishes (CARD-0196's own 2026-08-24 verification) — worth a byte-level check of the actual buffered file content on a future hike rather than trusting the routing test as still-representative.
- Whether this is somehow specific to a rare interaction with the corrupted-reading/reset-loop chaos from CARD-0211's incident later that same day (though the display-refresh gap is in the *morning* hike portion, well before the afternoon upload attempts began) — worth explicitly ruling in or out, not assumed unrelated just because the timing looks separate.

**Historical forensics hit a real dead end, 2026-08-25 evening.** The actual SPIFFS buffer from the real hike no longer exists (cleared after the successful replay); checked the scratchpad's earlier serial captures (`hiking_monitor_dump.log` and two siblings, saved during the CARD-0211 rescue) hoping for a byte-level look at the buffered content, but they turned out to be plain USB boot-log captures, not `hike_log_replay_stream()` dumps — no raw buffer evidence recoverable. Confirmed via `git log` that the display-throttle/logging code (`hiking-monitor.yaml`) hasn't been touched since the day before the hike (`f874063`, 2026-08-24), ruling out code drift as an explanation.

**Instead of continuing to guess at old data, made the next hike self-diagnosing — built and deployed 2026-08-25 evening:**
1. **Firmware:** `hiking-monitor.yaml`'s on_boot reset-reason check (CARD-0195) now logs `{"event":"reset","reason":"..."}` on **every** field-mode boot, not just ones matching the old `"rownout"/"anic"/"atchdog"` substring filter — the working hypothesis is a silent reboot on a reset reason that filter let through with zero trace, resetting `field_display_cycle` to 0 before it could reach a throttled refresh. Field mode only has one legitimate entry per hike (CARD-0201's true-deep-sleep-between-samples isn't built, so the device stays awake for the rest), so a clean hike should show exactly one reset-reason entry; a real mid-hike reboot would now show up as an extra one.
2. **Node-RED:** `environmental-data.flow.json`'s routing function moved the abnormal-keyword check from firmware into itself — a normal reset reason now logs as `System` (`"Field-mode boot, reset reason: ..."`), an abnormal one still posts a real `Alert` (`"Unexpected reset in field mode - ..."`), so widening the firmware doesn't turn every routine hike-start wake into a false alarm.
3. Compiled clean, OTA-flashed (`config_hash=0xd7affd19`), confirmed clean reconnect on the log dashboard. Node-RED flow redeployed by Joseph (delete-tab-then-import, per this project's own established method).
4. **Verified live end-to-end** via two real synthetic MQTT test payloads: a normal reason (`"Power on reset"`) correctly logged as `System`/`"Field-mode boot, reset reason: Power on reset"`; an abnormal reason (`"Task Watchdog got triggered"`) correctly logged as `Alert`/`"Unexpected reset in field mode - ..."`. Confirmed neither leaked into the Environmental Data sheet (`action=export` for that window shows only a real front-porch-temp-sensor row, nothing from either test).

**Resolved 2026-08-27 — found it, on the very next real multi-hour hike.** Today's hike (field mode ~05:30 MST) hit a real crisis at 07:22-07:31 MST: roughly **270 reboots inside a ~9-minute window**, captured directly by the reset-reason logging this card built. That single burst almost certainly explains the 2026-08-25 zero-`display_refresh` mystery too — a device silently rebooting on this scale mid-hike would reset `field_display_cycle` back to 0 over and over, exactly the mechanism this card hypothesized, now with real evidence rather than elimination-by-exclusion. Not a one-off fluke either: the fact it recurred (in a different, more severe form) on the very next real hike this instrumentation saw argues this is a genuine, recurring device-health problem, not a coincidence specific to 2026-08-25.

**One real gap found in the instrumentation itself, by this first real use:** every one of the ~270 reset events logged an empty reset reason — the fix built here correctly proved resets are happening, but not *why*. Follow-on work (fixing the reset-reason-text timing bug, and the deeper heat/brownout root-cause investigation) continues under **CARD-0217**, not reopened here — this card's own scope (get real reset evidence out of a silent mid-hike reboot) is complete.

**Done when:** the actual root cause is identified and fixed (or the mechanism is confirmed working via a real future hike showing the expected ~20-minute-spaced refresh events) — not just re-verified against another short test walk, which is too brief to distinguish "working correctly" from "the same gap recurring." **Met** — the diagnostic instrumentation caught a real, severe reset event on the very next hike, definitively confirming the hypothesis (not the "mechanism healthy" alternative).

**Related:** CARD-0196 (the display-refresh-throttle feature this bug is in — still open, since a device rebooting this severely defeats the throttle regardless of its own logic being correct), CARD-0217 (the 2026-08-27 incident that resolved this card — the reset-reason-text bug and root-cause investigation continue there), CARD-0211 (same class of prior incident, different context — upload-time watchdog timeout, already fixed), CARD-0215 (confirmed today's 102 real Environmental Data readings have sane timestamps, ruling out a clock explanation for this bug), CARD-0195 (the original reset-reason detection this widened), `components/hiking-monitor/hiking-monitor.yaml` (the interval block, `field_display_cycle`, the on_boot reset check), `components/hiking-monitor/hiking_logger.h`, `core/data-pipeline/environmental-data.flow.json` (`env-data-route-skip-reset`).

---

### CARD-0215 · [bug] [data-pipeline] Duplicate Environmental Data rows from CARD-0211's reset loop, plus no dedup-on-ingest at all — RESOLVED 2026-08-25 evening
**Status:** Done

**Raised 2026-08-25 (Claude, found while live-testing CARD-0214's gap-fill re-fetch).** The 2026-08-25 hike-summary page's Environmental Data section, after CARD-0214's fresh re-fetch, showed "10196 of 103 expected (9899.0% coverage)" — implausible on its face. Checked directly: the hike has exactly **103 unique `(timestamp, source)` readings** (matching the expected 2-minute-cadence count for a 3h26m hike), but up to **159 duplicate rows per timestamp**, concentrated in the 13:37-13:56Z stretch. Root cause is CARD-0211's reset loop: before the watchdog fix landed, the device repeatedly retried the same buffered-reading replay and crashed partway through each attempt — every failed attempt still published whatever readings it got through before crashing, so early-buffer readings got re-published dozens of times across the repeated attempts (159 → 155 → ... tapering as the crash point drifted).

**Real scope, pulled from a full-sheet export (`action=export&sheet=Environmental%20Data`, all 33,932 rows, not just today's hike) — the same day this was found, not estimated:**

| Date | Duplicated keys | Excess rows |
|---|---|---|
| 2026-08-25 | 94 | 10,093 |
| 2026-08-22 | 14 | 27 |
| 2026-06-12 | 1 | 2 |
| 2020-01-01 | 1 | 2 |
| **Total** | **110** | **10,124** (of 33,932 total rows — ~30%) |

2026-08-25 is CARD-0211's incident and accounts for the overwhelming majority.

**Second finding, same day, raised directly by Joseph reviewing the live page: some of those duplicated readings aren't just repeated, they're corrupted.** The 2026-08-25 hike's Environmental Data section showed implausible ranges (temp 80.2-370.6°F, pressure down to -174.9 hPa, UV index up to 7294.4). Checked directly: exactly **one** distinct `(timestamp, source)` key — `2026-08-25T16:03:06Z` — carries genuinely impossible values (`temp_f: 370.6, humidity_pct: 100, pressure_hpa: -174.9, uv_index: 7294.44`), duplicated **74 times**, almost certainly a mid-crash MQTT publish during CARD-0211's reset loop writing garbage into the payload as the device reset partway through serializing it. This is a distinct problem from plain duplication — deduplicating this key down to "one copy" would still leave one bad row; **Joseph's explicit call: don't allow corrupted data into the store at all, dedup alone isn't the fix.**

**2026-08-22's 14 keys / 27 excess rows, investigated directly rather than left as a guess:** all 14 have real, plausible sensor values (temp 93-99°F, real GPS coordinates) and each is duplicated exactly **3** times — same signature as CARD-0211's reset loop (a failed replay attempt re-publishing readings before crashing), just a much smaller episode, 3 failed attempts instead of dozens. A real, previously-undiagnosed earlier instance of the same class of firmware bug, three days before CARD-0211 — not root-caused further (the watchdog-timeout fix already covers whatever caused both), just now identified rather than silently swept into the cleanup.

**2026-06-12 and 2020-01-01, checked directly, not assumed:** both are the *same* fixed placeholder reading (`temp_f: 85, humidity_pct: 20, pressure_hpa: 925, uv_index: 0`, no GPS), each tripled — not the `clock_invalid` skip-logging hypothesis originally guessed (that path just logs a skip event, no data write), but the same small-scale retry/duplicate signature as 2026-08-22, landing on a boot where the device's clock hadn't been set yet and fell back to a fixed default reading. Same underlying pattern family, different trigger condition.

**Decided 2026-08-25 (Joseph), directly rejecting Claude's first-draft "dedupe at read time" proposal, then again rejecting "just dedup" once the corrupted-data finding came in:** the Sheet itself is the canonical data store — bad data shouldn't be allowed in at all, and cleanup-at-read-time would leave every future reader needing to independently know to filter it. **Two-part fix:**
1. **One-time cleanup** — rewrite the live "Environmental Data" sheet keeping exactly one row per valid unique `(timestamp, source)` key (first-seen wins); any key whose values are physically implausible is dropped **entirely** (zero rows kept), not deduplicated to one.
2. **Ingest validation, structural, permanent** — `environmental-data.gs`'s `doPost()` now rejects (`{status: 'rejected', reason: 'out_of_range', ...}`) a payload with any of `temp_f` (-20 to 130°F), `humidity_pct` (0-100%), `pressure_hpa` (800-1100 hPa), or `uv_index` (0-20) outside sane physical bounds, and separately rejects (`{status: 'duplicate', ...}`) an exact `(ts, source)` repeat — both checked before ever reaching `appendRow`. Neither check is specific to CARD-0211's already-fixed watchdog bug; both guard the sheet against *any* future cause of a bad or repeated publish.

**Built 2026-08-25 evening:**
- `environmental-data.gs`: range + dedup checks added to `doPost()`'s Environmental Data branch (dedup check reads only columns A/B via `getRange(2,1,lastRow-1,2)`, not the full row, to keep it cheap as the sheet grows — the performance question from the original open-questions list resolved this way rather than left unmeasured). `SCRIPT_VERSION` bumped to `2026-08-25.1-ingest-validation`. New `cleanupDuplicateEnvironmentalData()` — one-time function, added to the Sheet's own `JCTsh` custom menu (`Cleanup Duplicate Environmental Data (CARD-0215, one-time)`) so it's a menu click, not a trip into the Apps Script editor's function picker. Rewrites the sheet in one bulk `setValues()` call (not thousands of individual `deleteRow` calls), logs and alerts a real before/after summary (original/kept/dropped-duplicate/dropped-corrupted counts) so the result is confirmed against this card's own numbers, not trusted blind. Syntax-checked clean (`node --check`).
- **Deployment note — this is Apps Script, deployed by pasting into the Apps Script editor (no `clasp`/API tooling in this repo, confirmed no automated path exists) — Claude can't deploy or run it.** Needs Joseph to: paste the updated `environmental-data.gs` into the Apps Script editor, **Deploy → Manage deployments → pencil → Version: New version → Save**, then reload the Sheet tab and run **JCTsh menu → Cleanup Duplicate Environmental Data** once. File is on the clipboard, ready to paste.

**Redeployed and cleanup run by Joseph, verified live end-to-end, 2026-08-25 evening:**
- `?action=version` confirmed `2026-08-25.1-ingest-validation` — redeploy live.
- Range-validation confirmed live via a real test POST (`temp_f: 999`): rejected with `{"status":"rejected","reason":"out_of_range","field":"temp_f","value":999}`, never reached the sheet.
- Duplicate-rejection confirmed live via a real test POST sent twice (same `ts`/`source`): first attempt `{"status":"ok"}`, second `{"status":"duplicate",...}` — not appended a second time. (The one real synthetic row this necessarily created was manually deleted afterward.)
- Cleanup run reported **Original: 33,937 · Kept: 23,812 · Dropped as duplicates: 10,051 · Dropped as corrupted: 74** — internally consistent (23,812 + 10,051 + 74 = 33,937, exact).
- **A real verification wrinkle, caught rather than glossed over:** the post-cleanup `action=export` scan initially showed only 23,077 rows — 735 short of the cleanup's own reported 23,812. Rather than assume real data loss from a destructive rewrite, checked the actual ground truth: Joseph confirmed the Sheet's own row count directly (23,812, exact match) via the Sheets UI itself, not the export endpoint. The gap was `_exportSheet`'s own **pre-existing, already-documented bug** (CARD-0099: silently drops any row whose column A doesn't parse as a valid JS `Date`, even unfiltered) resurfacing after the cleanup's bulk `setValues()` rewrite changed how some cells' timestamps are typed — not a new problem this card introduced, and no real data was lost. Worth remembering: trust the Sheet UI's own row count over `action=export` for anything where the exact total matters.
- **Final proof the whole fix (CARD-0214 + CARD-0215 together) works as designed:** re-ran `--step2 2026-08-25` against the now-clean sheet — environmental fetch dropped from 10,196 rows to **102** (vs. 103 expected), with zero code changes needed beyond the two cards' own fixes; CARD-0214's re-fetch-on-every-pass design meant the page self-corrected the moment the underlying data did. Live page confirmed: **"102 of 103 expected (99.0% coverage)"**, Temperature 80.2-114.1°F, Humidity 13.7-53.2%, Pressure 902.2-926.4hPa, UV Index 0.0-7.1 — all physically sane, matching a real hot Arizona summer hike.

**Done when:** the Apps Script redeploy and cleanup run are confirmed live (`?action=version` returns `2026-08-25.1-ingest-validation`; a fresh full-sheet duplicate scan shows zero duplicate keys and zero out-of-range values remaining); the dedup/range checks are confirmed working via a real repeated/out-of-range test payload (rejected, not appended); and the 2026-08-25 hike-summary page, regenerated afterward, shows a sane coverage figure (103/103, not 9899%) with no implausible temperature/pressure/UV values. **Met, 2026-08-25 evening** — all criteria verified live, per above.

**Related:** CARD-0211 (the reset-loop incident that caused the overwhelming majority of this, including the corrupted reading), CARD-0214 (the gap-fill re-fetch that made this visible for the first time — step 2 never used to re-query real Environmental Data at all, so nobody had looked at this hike's true row count or value ranges until now), `core/data-pipeline/environmental-data.gs` (`doPost()`'s Environmental Data append branch, `cleanupDuplicateEnvironmentalData()`), `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`.

---

### CARD-0214 · [enhancement] [hike-izer] Two-pass hike-summary generation to close the GPSLogger-trigger-vs-late-data race — RESOLVED 2026-08-25 18:47 MST
**Status:** Done

**Raised 2026-08-25 (Joseph), found while checking whether today's rescued hiking-monitor data (CARD-0211's 111 recovered readings) made it onto the published hike summary.** It didn't — `hikes.jctnet.com/2026-08-25_hike-summary.html` was auto-published at 10:01 AM MST, right after GPSLogger's `stopped` webhook fired at 9:59 AM, but the reset loop that trapped the hiking-monitor's buffered readings wasn't fixed until ~16:04 MST that afternoon. The page has no Environmental Data Tracking section at all — it was generated hours before that data existed anywhere in the pipeline.

**Root cause is structural, not a one-off bug.** The existing pipeline (CARD-0086/CARD-0112) has exactly one trigger — GPSLogger's `stopped` webhook — firing step 1 (GPS + whatever's already in the Sheet) immediately. Step 2 exists ("finish the hike page") but only ever re-fetches **photos** (Immich sync lag) and runs enrichment against the *already-persisted* `hike_data.json` from step 1 — it never re-queries Environmental Data or Hiking Observations, so even running step 2 today wouldn't have picked up the recovered readings. Environmental data, photos, and Gaia/bird data (already referenced in `generation.py`'s own "ask for the rich version once photos/Gaia/bird data are staged" line) are all async sources that can lag the GPS-end trigger by anywhere from minutes (normal case) to hours (today) to indefinitely (device never docked).

**Design decided via interview 2026-08-25 — rejected an initial "trigger off the hiking-monitor's own replay-complete event" idea** (Claude's first proposal) because it wrongly assumes hiking-monitor sync is the *last* thing to finish — photos/Gaia/bird data have no such event either, and could still be the actual laggard. **Chosen instead: two time-based passes, both calling the same idempotent operation, not two different operations:**

1. **Pass 1 — unchanged.** GPSLogger `stopped` webhook fires immediately, generates whatever's available right then (same as today's step 1).
2. **Pass 2 — new, time-triggered, not event-triggered.** A daily cron (proposed 5pm MST, exact time TBD at Build) re-runs the *same* generation operation for any hike-summary published that day.
3. **Both passes are the same gap-filling operation, examined-and-fill-in, not blind regeneration.** The second pass looks at what pass 1 (or a prior pass 2) already produced and only adds what's missing — it does not redo processing that's already been done. Concretely:
   - **Environmental Data / Hiking Observations:** re-query the Sheet for the hike's window and merge in anything new — cheap, safe to always re-pull (Sheet reads have no real cost), but must not duplicate rows already in `hike_data.json`.
   - **Photo enrichment:** only process photos that are new compared to what pass 1 already enriched — diff the live Immich listing against whatever's already recorded in `hike_data.json` as done, skip anything already-enriched rather than reprocessing it. This is the real cost control (Nominatim/Overpass calls aren't free-as-Sheet-reads) and was Joseph's explicit correction to the first draft of this design.
   - **Narrative generation stays untouched by this card** — still the existing opt-in-only, ask-explicitly mechanism (CARD-0123), not something either automatic pass triggers on its own.
4. **Must be safely re-runnable any number of times, on demand, with no side effects — a hard design constraint, not a nice-to-have.** Joseph's own framing: "I could always request the second pass to be run again, this should cause no problems because the process just examines what's been done and fills in the gaps." The manual "ask for step 2" conversational path stays available alongside the new cron trigger, calling the identical operation.

**Explicitly accepted, not solved by this card:** if a data source is still unsynced past the cron's fixed time (e.g., today's outage had run past 5pm), the page stays incomplete until someone asks for another pass manually — the cron narrows the usual gap, it doesn't guarantee zero gap ever.

**Open questions resolved during Build, 2026-08-25:**
- **Cron time: 5pm MST, as proposed** — `hike-izer-daily-refresh.timer`, `OnCalendar=*-*-* 17:00:00`, `Persistent=true` (catches up on next boot if the M8 was down at 5pm). No per-trip time variation — not worth the complexity given the recency-window design below already tolerates a few days' slop.
- **"What's already been done" mechanism, decided differently than either original guess:** Environmental Data/Observations/GPS don't need incremental diffing at all — `fetch_hike_data.py` is a pure, stateless query against the Sheet for a fixed window, so simply re-running it with the *same* window (persisted in `meta.json` as `query_start_iso`/`query_end_iso`, set once by step 1) is safe and correct by construction; a later pass naturally picks up whatever's landed since. Only **photo captions** needed real incremental tracking, since that's the only step with genuine per-call cost (Claude API): `generation.py`'s `_fetch_photos()` now recovers any already-captioned asset's caption/sign_text (keyed by Immich's own stable asset id) from the on-disk `manifest.json` *before* `fetch_hike_photos.py` overwrites it with a fresh Immich listing, reapplies them after, and `photo_captions.caption_photos()` skips any asset that already carries a `caption` key — only genuinely new photos reach a real API call.
- **Per-day/per-session model (CARD-0113) composes cleanly, confirmed by construction, not assumed:** discovery for the daily pass (`_stems_recently_published()`) is **recency-based on file mtime, not calendar-date-based at all** — a real design correction found while implementing, not in the original interview: an earlier draft would have computed "today" on the M8's own fixed TZ to decide what to refresh, which is exactly the location-assumption this project's own standing rule (`[[feedback_no_location_assumptions]]`, and this very file's own docstring: "a hike can happen anywhere Joseph is carrying his phone") forbids. A 30-hour lookback window sidesteps needing to know what "today" means for any given hike at all, and naturally covers every session in a multi-day trip the same way it covers a single day.
- **Unified, not parallel:** `run_step2()` itself became the one idempotent gap-filling operation, called identically by the conversational "ask for step 2" path and the new automatic daily pass (`run_daily_refresh_and_log()`, `--daily-refresh` CLI flag) — not two different functions that happen to converge.

**A real subtlety caught and fixed during implementation, not in the original design:** the first draft of `_stems_recently_published()` checked the `*_hike-summary.html` file's own mtime — but `run_step2` rewrites that file on *every* pass, so a hike's mtime would keep resetting and it would look "recently published" forever, refreshing every single day indefinitely. Fixed by keying off `*_hike-summary.meta.json`'s mtime instead — written once by step 1 and (after one self-correcting exception, below) never touched again by an ordinary `run_step2` call, so it's a genuinely stable "first published" signal.

**Built and deployed, 2026-08-25 18:30-18:47 MST:**
- `generation.py`: `_fetch_hike_data()` extracted (shared by step 1 and every gap-fill pass); `run()` now persists `query_start_iso`/`query_end_iso` in `meta.json`; `run_step2()` re-fetches `hike_data.json` fresh every call instead of just reading step 1's stale copy (falls back to a full local-day window and backfills `meta.json` for a hike published before this card, so every later pass on that same file converges to the tight window); `_fetch_photos()` preserves prior captions across re-fetches; new `_stems_recently_published()` + `run_daily_refresh_and_log()` + `--daily-refresh` CLI flag.
- `photo_captions.py`: `caption_photos()` skips any asset that already carries a `caption` key.
- New `hike-izer-daily-refresh.service`/`.timer` (M8, `docker exec hike-izer-orchestrator python3 generation.py --daily-refresh`, daily 5pm MST) — installed, `daemon-reload`d, enabled.
- Deployed via `scp` + `docker compose up -d --build orchestrator` (M8), same pattern as every prior change to this component.

**Verified live against the real 2026-08-25 hike — not a synthetic test, the exact case this card exists to fix:**
1. **Gap-fill confirmed real**, `--step2 2026-08-25`: environmental fetch went from zero rows at original publish time to 10,196 real hiking-monitor rows found in the Sheet; the published page's Environmental Data Tracking section, previously entirely absent, now renders with real temp/humidity/pressure/UV/battery data across the whole hike.
2. **Idempotent/safely-repeatable confirmed**, same file re-run immediately after: `$0.0000 (0 API calls, 0 in / 0 out tokens)` — 9 photos found identical to the first run, none re-captioned, confirming the caption-preservation path works, not just that nothing crashed.
3. **The real systemd-timer path confirmed, not just the manual CLI:** `systemctl start hike-izer-daily-refresh.service` on the live M8 host ran the exact same `docker exec ... --daily-refresh` invocation the 5pm timer will use, `_stems_recently_published()` correctly discovered `2026-08-25` by its `meta.json` mtime, called `run_step2` on it, completed with `$0.0000` (already-refreshed, nothing new) — full trigger-to-completion path proven live, `code=exited, status=0/SUCCESS`.

**One real, separate, and larger finding surfaced by this fix, spun out as its own card rather than folded in here:** the "10,196 rows" figure above turned out to include large-scale duplication — only 103 are genuinely unique readings, the rest are repeated MQTT publishes from CARD-0211's reset loop (a failed replay attempt still publishes whatever it got through before crashing). This card's own job — making the real Environmental Data actually reach the page — is complete and correct; the data itself having duplicates is a separate, now-visible-for-the-first-time data-quality bug. See **CARD-0215**.

**Done when:** the cron-triggered pass is built, deployed, and demonstrated (a real hike or a realistic backfill test) to (1) never duplicate or reprocess anything pass 1 already completed, (2) correctly fill in Environmental Data and any newly-synced photos that weren't available at pass-1 time, and (3) be safely re-invoked multiple times in a row with no side effects — verified live, not just code-reviewed. **Met, 2026-08-25 18:47 MST** — all three verified live against the real stranded 2026-08-25 hike, per above.

**Related:** CARD-0211 (the incident that surfaced this gap), CARD-0215 (the duplicate-row data-quality issue this fix's own re-fetch made visible for the first time), CARD-0086/CARD-0112 (the original webhook-triggered step 1/step 2 automation this extends), CARD-0113 (the per-day/per-session model this stays compatible with by construction, via recency-based discovery), CARD-0156 (the analogous async-arrival race in the hiking-monitor observation-queue pipeline — same "just re-try later, safely, rather than chase a completion event" philosophy), CARD-0123 (the opt-in-narrative-cost precedent this card deliberately doesn't touch), [[feedback_no_location_assumptions]] (the standing rule that shaped the recency-based, not calendar-date-based, discovery design), `components/hike-izer-orchestrator/generation.py`, `components/hike-izer-orchestrator/photo_captions.py`, `.claude/skills/hike-izer/SKILL.md`.

---

### CARD-0213 · [enhancement] [infrastructure] Quantified peak-current headroom standard for battery-powered builds — RESOLVED 2026-08-25
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

### CARD-0212 · [enhancement] [hiking-monitor] Gate the hike-log replay burst behind the existing low-battery cutoff — RESOLVED 2026-08-25 17:26 MST
**Status:** Done

**Raised 2026-08-25 (Joseph), directly from CARD-0211's diagnosis.** hiking-monitor already has a low-battery safety cutoff (`low_battery_shutdown` script, `hiking-monitor.yaml`) that forces deep sleep below **3.4V** — but by design it only applies during field/hiking mode (`slide_switch on, dock_detect off`); it's deliberately skipped while docked so charging can proceed uninterrupted. The replay burst (`mqtt.on_connect:` handler, ~line 221-250 — publishes every buffered reading with a 50ms gap between each, real sustained WiFi/MQTT current draw for several seconds) has no equivalent gate at all. CARD-0211's incident is exactly this gap: device comes home from a hot, long hike already battery-warned, gets plugged in, and the replay burst attempts (and brownout-resets) repeatedly before the battery has recovered enough headroom, rather than waiting.

**Decided 2026-08-25 (interview):** reuse the existing 3.4V threshold rather than defining a new one — same battery, same physics, no reason for the replay burst to need a different safety margin than the field-mode cutoff already established.

**Scope (proposed, to be refined at Build):**
- In the `mqtt.on_connect:` handler, before starting `hike_log_replay_stream(...)`: check `id(battery_voltage).state >= 3.4f`. If below, skip the replay for this connection cycle (leave the buffered readings untouched — nothing is lost either way), log an Alert-category message noting the skip and current voltage, and let the device sit connected/charging rather than repeatedly attempting and resetting.
- **Retry mechanism not yet decided** — options to weigh at Build: periodically recheck voltage on an interval while docked and retry once above threshold; or simply rely on the natural reconnect-on-MQTT-drop behavior already happening (each reconnect re-triggers the check, so it self-heals once voltage recovers, same mechanism that's currently causing the reset loop but now gated safely instead of attempting the risky operation).
- Consider whether the e-ink display should show something distinct from the normal "Connected → Uploading → Done" sequence while skipped-for-low-battery (e.g., "Charging — low battery" instead of silently doing nothing), matching this device's existing pattern of surfacing state on the always-visible e-ink even with no WiFi.

**Built and OTA-flashed, 2026-08-25 16:20-16:24 MST.** In the `mqtt.on_connect:` handler, the replay block is now gated on `id(battery_voltage).state >= 3.4f`: below that, the burst is skipped entirely (buffered readings left untouched, nothing lost) and an Alert-category log message is published noting the skip and current voltage; at/above it, the existing Connected → Uploading → Done display sequence and replay logic run unchanged. Compiled clean (`config_hash=0x0d98cd39`), flashed via OTA to `192.168.1.161` (no USB/PC needed) — succeeded in 8.75s, device reconnected cleanly at 16:24:53-57 MST, confirmed via the Pi's log server (`connection_state.online: True`, normal "Upload mode — USB connected, switch off" status).

**Committed 2026-08-25 16:30 MST** (`7aabd42`).

**Skip path verified live, 2026-08-25 17:14-17:25 MST — a simulated bench test, not a real battery drain.** Generated real buffered data by taking the device (switch ON) outside JCTnet1's range for ~3 minutes, letting the 2-minute field-mode interval log a genuine reading to SPIFFS. Before bringing it back in range, temporarily flashed a test build (`C:\esphome\hiking-monitor\hiking-monitor.yaml` only — repo copy untouched) with the CARD-0212 threshold literal raised from 3.4f to 4.5f, above the device's real ~4.2V — forces the skip branch deterministically off today's real voltage, no need to actually drain the cell. Walking back through spotty edge-of-range coverage produced four separate MQTT reconnects (17:14:09, 17:17:52, 17:17:54, 17:20:50) — the gate correctly re-evaluated and deferred the replay on every single one (`"Replay deferred - battery 4.1x-4.28V below 4.5V cutoff, waiting for charge"`), confirming the check is a stateless per-connection guard, not something a flaky reconnect sequence could slip past. No reset loop, no Connected→Uploading→Done display sequence attempted, buffered data untouched throughout.

**Normal path re-verified immediately after, 2026-08-25 17:26 MST.** Reverted the test threshold back to 3.4f (diffed clean against the committed repo copy before reflashing), recompiled (`config_hash=0x0d98cd39`, matching the already-committed build), OTA-flashed back. Next reconnect replayed the same buffered data normally: `"Replaying 4 hike readings..."` → `"Hike log replay complete."` — confirms the new gate doesn't interfere with the existing working path.

**Done when:** a real low-battery dock/charge scenario (real device or reproduced on the bench) shows the replay burst deferred rather than attempted while below 3.4V, no reset loop, and resumes automatically once the battery has recovered — verified live, not just code-reviewed. **Met**, 2026-08-25 17:14-17:26 MST (simulated-threshold bench test, both skip and resume paths verified live per above).

**Related:** CARD-0211 (the 2026-08-25 incident this directly follows from), CARD-0026 (measured the boost-converter brownout-reset-loop mechanism this is meant to avoid triggering), CARD-0070 (deferred LDO+gate hardware fix for the same underlying weakness — this card is a firmware mitigation, not a replacement for that hardware fix), `components/hiking-monitor/hiking-monitor.yaml`.

---

### CARD-0211 · [bug] [hiking-monitor] Analyze results for the 2026-08-25 hike — upload stuck in a reset loop — RESOLVED 2026-08-25 16:04 MST
**Status:** Done

**Raised 2026-08-25 (Joseph)**, after using hiking-monitor for a hike today. Switched off at end of hike; display showed a low-battery warning. Got home, plugged in USB to charge (switch left off, per this device's normal upload-mode procedure — the switch is not in the power path, see `wiring.md`'s Slide Switch Wiring section). Watched the display show an "initialization" message 6-7 times, with nothing about uploading the data.

**Open-ended investigation** — scope covers getting today's 111 buffered readings uploaded and reviewed, confirming/refining the root-cause diagnosis below, and considering whether anything should change to prevent this on a future long/hot hike. Not closing until the root cause is actually confirmed, not just plausible.

**Diagnosis so far, from `/mnt/jctsh-logs/state.json` on the Pi:**

Reconstructed timeline:
| Time | Event |
|---|---|
| 8/24 evening → 8/25 05:22 | Previous charge/upload session — **completely stable for 8+ hours straight**, battery healthy the whole time (4.26–4.28V) |
| 8/25 05:22:43 | "Entering deep sleep" — device came off the charger for today's hike |
| 8/25 05:23 → 11:55 | **~6.5 hour gap — today's hike**, device logging in the field. Heartbeat temps logged in the 108-111°F range going into the hike, consistent with serious heat |
| 8/25 11:55:25 | Device reconnects, logs "Replaying 111 hike readings..." — **the reset loop starts here**, not later as first assumed from a narrower log window |

Since 11:55:25, the device has been cycling roughly every 27-30 seconds: connects to WiFi/MQTT, logs "Hiking monitor online," starts "Replaying 111 hike readings...", then disconnects and restarts the identical sequence — always restarting from all 111 readings, never completing a partial replay. Confirmed still ongoing as of ~12:52 MST (about an hour into the loop at that point, matching what Joseph observed), and continued past an hour of TP4056 charging without resolving.

**Working theory:** a battery that started the day fully charged (4.28V the night before), put through a ~6.5 hour hike in 108-111°F heat (heat increases LiPo internal resistance and accelerates apparent voltage sag under load), ending in a genuine low-battery warning on the device's own display. Publishing 111 buffered readings over WiFi/MQTT is real sustained current draw, on top of the TP4056+boost module's own known quiescent draw (a documented weak point on this exact hardware architecture, from CARD-0026/CARD-0070) — plausibly not enough headroom to get through a full replay before browning out and resetting, matching the consistent ~28s cycle time reasonably well. Last night's rock-solid 8-hour session on the identical hardware argues against a newly-introduced hardware fault.

**Not yet confirmed:** whether more charging time eventually lets the replay complete (the expected outcome if the battery-depletion theory is right), or whether something else is contributing given an hour of charging didn't resolve it. No data is at risk — the 111 readings are safely in onboard flash regardless of how many times the replay attempt restarts.

**Update, 2026-08-25 ~14:25 MST — still looping after ~2.5 hours total, over 2 hours of charging.** Confirmed via the log: identical pattern still ongoing (`14:23:35`-`14:25:06` shows the same ~27-30s connect/replay/disconnect cycle, still always "Replaying 111 hike readings..."). Over 2 hours of charging not resolving it starts to push against the pure "just needs more recovery time" read of the battery-depletion theory, or at minimum shows recovery is taking substantially longer than a typical partial-depletion scenario would suggest. **Checked whether a live battery voltage could be pulled via MQTT to confirm charging progress directly** (`hiking-monitor.yaml`'s `mqtt.on_connect:` handler) — it does not publish battery voltage anywhere before attempting the replay; the only live reading is the 20-minute heartbeat, which this loop never reaches, and the only battery data flowing at all is historical (embedded in the buffered readings themselves, from hike time). **A direct multimeter reading at the battery is the only way to get a current voltage right now** — not yet done as of this update.

**Real pivot, 2026-08-25 ~14:35-14:47 MST — battery/boost converter ruled out entirely as the cause.** With the battery physically unplugged from the TP4056 (boost converter therefore fully dead, no live source on the ESP32's `VIN` node) and the ESP32 powered directly from its own USB port instead, **the identical reset loop continued** — same ~27-30s cycle, same "Replaying 111 hike readings..." every time. This is a clean, controlled negative result: with no battery and no boost converter anywhere in the circuit, the failure persists, so tonight's entire battery-depletion/heat theory — however well it fit the circumstantial timeline — was not the actual cause of the loop. This is a firmware bug, not a power problem.

**Data rescued, 2026-08-25 ~14:47 MST — all 111 readings safely recovered independent of the broken replay path.** Added a temporary early-`on_boot` action (`hiking-monitor.yaml`, ahead of the WiFi/MQTT/display code that's crashing) dumping the full buffered hike log to USB serial via `ESP_LOGI` instead of MQTT. Flashed and captured over COM7 (USB moved from the wall adapter to this PC specifically for this). **All 111 readings captured, extracted, and validated as clean JSON** — zero parse errors. **One real data-quality flag: reading at `ts: 2026-08-25T16:03:06Z` is corrupted** (temp_f 370.6, pressure_hpa -174.9, uv_index 7294.44 — a sensor glitch during the hike itself, not an extraction artifact) — exclude or flag it before this data reaches the Sheets pipeline. Data is now safe regardless of the ongoing firmware bug, and ready to publish into the real MQTT pipeline via `mosquitto_pub` (same end destination — Node-RED → Google Sheets — as a normal on-device replay, just triggered from the PC instead) whenever wanted.

**Two new, real findings from the serial capture, beyond just the data rescue:**
1. **`Error resolving broker IP address: -6`** on this specific boot — MQTT/DNS resolution itself failed, and the device correctly gave up and entered deep sleep rather than attempting a replay it couldn't complete. This is a *different* failure signature than the Pi dashboard's usual pattern (a successful connect immediately followed by a mid-replay disconnect) — suggesting more than one thing may be wrong, not a single root cause.
2. **`[E][waveshare_epaper:163]: Timeout while displaying image!`** recurred — the same e-ink error CARD-0009 saw once and dismissed as a one-off transient. Seeing it again during this exact investigation strengthens (doesn't prove) the working theory that the two e-ink refreshes in the `on_connect:` sequence (Connected → Uploading, both immediately before the 111-message MQTT publish loop) are implicated in the crash, independent of power.

**Two real dead ends before the actual root cause, both worth recording so they aren't re-chased later:**
1. **Display-refresh theory (removing the e-ink update before the replay loop) — ruled out.** Tested clean (dump code removed) and the identical fast failure persisted. Root-caused separately: it only ever showed up while accidentally testing with `dock_detect` reading OFF (USB was only on the ESP32's own flashing port, not the TP4056's separate charging port) — an unrelated, unguarded `on_boot` priority -200 check (`slide_switch off AND dock_detect off` → immediate `deep_sleep.enter()`) was firing almost instantly on every boot, abruptly interrupting an in-flight display update and producing the "Timeout while displaying image!" error as a side effect, not a cause. The original CARD-0009 sighting of that same error was very likely the same mechanism, not a separate display hardware issue.
2. **Battery/boost-converter theory — genuinely ruled out** (unplugging the battery entirely didn't stop the loop), but this also meant most of the afternoon's testing wasn't reproducing the real bug at all, for the same `dock_detect`-off reason as above.

**Real root cause, found via an actual crash backtrace once `dock_detect` was correctly asserted (both the ESP32's own USB port AND the TP4056's charging port connected simultaneously) — a genuine ESP32 task watchdog timeout, not power-related at all:**
```
23.80s: MQTT Connected
23.91s: "mqtt took a long time for an operation (113 ms), max is 30 ms"
29.33s: E task_wdt: Task watchdog got triggered - loopTask (CPU 1) did not
        reset the watchdog in time. Aborting. Rebooting...
```
~5.4s between MQTT connect and the crash — matching the replay loop's own minimum runtime almost exactly (111 readings × 50ms explicit delay = 5.55s, already over the ESP32's default 5-second task watchdog window before any real per-message MQTT/TLS overhead is added). `delay(50)` yields the *CPU* to other tasks, but the watchdog specifically needs `loopTask` itself to return/make forward progress, which it never does across all 111 iterations inside one continuous `on_connect:` lambda call. Reproduced identically three times in one capture, each cycle landing within a second of ~29s — matching the Pi dashboard's original pattern precisely.

**Why this never showed up before today, confirmed not a regression:** git history shows zero changes to `hiking-monitor.yaml` between Saturday's successful hike (2026-08-22) and the start of this investigation — the exact same firmware that worked Saturday is what failed today. This is a latent bug that's likely always sat right at the watchdog's edge: any replay batch over roughly ~100 readings (100 × 50ms = 5.0s) risks tripping a 5-second watchdog before real network overhead is even counted. Saturday's hike almost certainly buffered meaningfully fewer readings (shorter hike, and/or some readings published live along the way rather than needing replay) than today's ~6.5-hour, fully-out-of-range hike, which produced 111.

**Fix: explicit `App.feed_wdt()` inside the replay loop** (`hiking-monitor.yaml`, `on_connect:` handler), satisfying the watchdog every iteration regardless of real per-message timing — makes the replay robust for any batch size, not dependent on staying under a fixed threshold by luck. Also restored the display-refresh call removed during the (ruled-out) display theory, now confirmed working correctly.

**Verified live, 2026-08-25 16:04:58 MST — real success, not inferred:** `"Hike log replay complete."` followed by `"Upload mode — USB connected, switch off"`, confirmed stable online for 7+ minutes afterward with no further disconnect. 125 readings replayed (the original 111 plus readings accumulated from tonight's own test reboots, all safely buffered the whole time). Data now needs to actually reach the Sheets pipeline (already-extracted rescue copy can be republished, or this live replay already delivered it) and the one corrupted reading (`16:03:06Z`) should be excluded/flagged when reviewed.

**Related:** `components/hiking-monitor/wiring.md` (Slide Switch Wiring, TP4056 Perfboard Connector sections — dock_detect specifically monitors the TP4056's own charging port), CARD-0026/CARD-0070 (hiking-monitor's own boost-converter quiescent-draw findings — considered as a theory, ruled out here), CARD-0213 (the general power-headroom standard this incident helped write — not actually the cause of *this* bug, but a real, separate, correct piece of work from the same night), CARD-0212 (the low-battery cutoff fix for the replay burst — still worth building independently, unrelated to the watchdog fix), tonight's separate air-quality-monitor CARD-0198 investigation (a genuinely different, power-related bug on different hardware — worth not conflating the two despite both surfacing the same night).

---

### CARD-0210 · [enhancement] [hike-izer] Wildlife Life List: statistical analysis (detection frequency, trends over time) beyond the current per-species/per-hike view — RESOLVED 2026-08-25 evening
**Status:** Done

**Raised 2026-08-24 (Joseph)**, via the "Log Idea" Tasker widget (PR #37, "statistical analysis for Life bird net page"). Interviewed same day — wants at least two kinds of stats on the Wildlife Life List page (`wildlife.html`, CARD-0142), and is open to more beyond these two:
1. **Detection frequency / most-common-species** — a ranked view of how often each species actually shows up, not just the existing "Hikes" column (number of distinct hikes a species was heard on at all, regardless of how many times per hike).
2. **Trends over time / seasonality** — when species are typically heard (by month/season), and/or how the life list has grown over time.

**Explicitly open to further stat ideas** beyond these two, to be gathered at Planning rather than guessed at here. **Seasonality specifically flagged as interesting** (Joseph, same session) — worth weighting toward when scoping which stats to build first at Planning, not just treated as one option among equals.

**What's already there vs. what's missing, checked against the current data model:** `wildlife_life_list.json` (per `wildlife_life_list.py`, CARD-0142) persists `common_name`, `scientific_name`, `first_heard_date`, `first_heard_file_stem`, and a deduped list of `hikes` — the page's "Hikes" column is just `len(hikes)`. Each individual hike's own BirdNET table (`birdnet.py`'s `parse_detections()`) already computes a **per-hike detection count** per species (the "Count" column, CARD-0080) — but that count is never carried into the cross-hike life list today, only used per-hike. Both stat ideas above would need the life list's data model extended to retain more than just "which hikes" per species (e.g. a per-hike count and date, not just a deduped hike-stem list) to compute frequency and time-based trends from.

**Designed 2026-08-25 evening, grounded in the real code (`wildlife_life_list.py`, `birdnet.py`, `build_wildlife_index.py` all read in full):**

**1. Data model change — the one extension that unlocks both requested stats.** `wildlife_life_list.py`'s `entry["hikes"]` is currently a plain deduped list of file_stems (`["2026-08-25", ...]`). Change to a list of `{"file_stem": ..., "count": ...}` dicts — `birdnet.parse_detections()` already computes a per-species `count` for every hike (the existing per-hike "Count" column, CARD-0080), it's just never carried into the persisted life list today. No new date field needed: every `file_stem` already starts with `YYYY-MM-DD` (the same trick the existing "First Heard" column's sort already relies on), so month/year is always derivable from it directly.
- **Idempotency, updated:** `update_from_hike()` currently just adds `file_stem` to the list if absent (a set). With counts, a hike can legitimately be reprocessed with a different count (step 1's best-effort BirdNET pass vs. step 2's real pass, CARD-0135) — so on a repeat `file_stem`, **overwrite that hike's stored count with the latest value** (last-processed-wins) rather than appending a duplicate or summing, keeping re-runs safe the same way the current design already is.

**2. Stat #1 (detection frequency) — one new column on the existing table.** `build_wildlife_index.py`'s table gains a **Detections** column (`sum(h["count"] for h in entry["hikes"])`), sortable via the existing click-to-sort mechanism (`data-sort-type="number"`, same pattern as the current "Hikes" column) — no new page section, no new JS.

**3. Stat #2 (seasonality/trends) — a new, separate, page-level "Detections by Month" table, not per-species.** Matches Joseph's own framing ("when species are typically heard... how the life list has grown") better than a per-species breakdown would, and stays within this page's existing zero-JS-except-sort convention (a real chart would be new scope beyond what's needed — a plain table answers "which months are busiest" directly). Walk every species' every hike entry, bucket by the month extracted from `file_stem` (collapsed across years — Joseph's own "by month/season" framing, not "by month in a specific year"), render:

| Month | Total Detections | Distinct Species Heard |
|---|---|---|

**4. "How the life list has grown over time" — smaller, lower-priority, v1-optional.** Joseph's phrasing framed this as an "and/or" alongside seasonality, not an equal-weight second requirement. If built: a simple **species-per-calendar-year** table (or a single cumulative-total-over-time figure), same derivation (bucket `first_heard_file_stem` by year). Flagged as a candidate first cut to trim if Build time is tight — the two items above are the real core of what was asked for.

**5. Real backfill required, not a placeholder.** Every already-published hike's staged BirdNET export still exists on disk (staged files are never deleted, per CARD-0112/CARD-0119's convention) — a one-time backfill script re-runs `birdnet.parse_detections()` against each hike's own `_staging/` directory and rebuilds `wildlife_life_list.json`'s `hikes` list from scratch with real counts, rather than migrating the old file in place with a synthetic count (e.g. count=1) that would understate every hike processed before this card. A full rebuild is simpler and more correct than a partial migration, since the old format never stored counts to migrate from.

**Built and deployed, 2026-08-25 evening — all four scope items, item 4 included rather than deferred (cheap enough to build alongside 2/3):**
- `wildlife_life_list.py`: `update_from_hike()` now stores `{"file_stem": ..., "count": ...}` per hike (last-processed-wins on a repeat `file_stem`, per the design).
- `build_wildlife_index.py`: `_hike_stem()`/`_hike_count()` tolerate a not-yet-backfilled entry still holding a bare file_stem string (treated as count=1) so a partial migration can't crash the page. New **Detections** column on the main table (sortable, same click-to-sort mechanism as every other column). New **Detections by Month** table (calendar order, not sortable — a static seasonality view doesn't need the interactivity exception this page otherwise reserves for the main table). New **Life List Growth** table (new species per calendar year), rendered only when more than one year of data exists — a single-row growth table says nothing, so it's omitted rather than shown empty.
- New `backfill_wildlife_counts.py` (one-time, re-runnable) — rebuilds `wildlife_life_list.json` from scratch by re-running `birdnet.parse_detections()` against every hike's still-present `<file_stem>_staging/` directory, recovering real historical counts rather than leaving pre-CARD-0210 hikes undercounted at the legacy count=1 fallback.

**Verified live, 2026-08-25 evening:**
- Synthetic smoke test first (three species across different months/years, plus one deliberately left in the old bare-string `hikes` shape) — confirmed correct month-bucketed totals, correct legacy-shape tolerance, no crash.
- Backfill run against the real M8 data: **13 hikes with BirdNET exports, 70 species, 635 total real detections recovered** — the actual historical counts, not placeholders.
- Real published `wildlife.html` confirmed live: Detections column showing real per-species totals (e.g. Verdin: 127 detections across 5 hikes); Detections by Month showing real seasonal skew (August: 534 detections/60 species, July: 101/22, all other months correctly 0 — matches this project's own hiking history, which only started in earnest in July 2026); Life List Growth correctly **absent** (all 13 hikes fall within 2026, a single year, so the one-row-says-nothing guard suppressed it as designed, not a bug).

**Related:** `components/hike-izer-orchestrator/wildlife_life_list.py` (the persisted cross-hike data model this extends — `update_from_hike()`'s `hikes` list shape, `entry["hikes"]`), `components/hike-izer/build_wildlife_index.py` (renders `wildlife.html` — new Detections column, Detections-by-Month and Life-List-Growth tables), `components/hike-izer-orchestrator/birdnet.py` (`parse_detections()`, the existing per-hike `count` this aggregates), `components/hike-izer-orchestrator/backfill_wildlife_counts.py` (the one-time real-count recovery script), PR #37 (the original voice-captured idea this scopes).

---

### CARD-0209 · [idea] [hike-izer] UV Index shown as a risk-level color (red/yellow/green), not just a raw number — RESOLVED 2026-08-25 evening
**Status:** Done

**Raised 2026-08-24 (Joseph)**, via the "Log Idea" Tasker widget (PR #36, "Uv light red yellow green"). Interviewed same day: about hiking-monitor's own UV Index readings (from the LTR-390 sensor) — "some thinking about what UV index means and how best to evaluate it as part of analyzing the hiking monitor data." A raw UV Index number (0–11+) isn't intuitively meaningful at a glance; a red/yellow/green (or the fuller standard EPA/WHO UV Index risk scale: Low/Moderate/High/Very High/Extreme) color coding would make it legible without knowing the numeric thresholds by heart.

**Not yet resolved — where this actually shows up:** could be hike-izer's own webpage display (the UV Index stat/range, and/or the Environmental Data chart's UV line) recolored by risk level, or something device-side (hiking-monitor has no RGB LED today, unlike air-quality-monitor). Leaning toward the hike-izer/display side given how it was described, but not settled — a real Planning-stage question, not decided here.

**Open question, raised 2026-08-24 (Joseph):** how does hiking direction relative to the sun affect the LTR-390's UV reading? Joseph's own observation: hiking into the sun reads noticeably higher than hiking away from it.

**First answer, 2026-08-24, was wrong — corrected 2026-08-25 (Joseph).** Claude's original explanation assumed the LTR-390 is mounted vertically on the front of the hiker's body (a forward-facing sensor, measuring a fundamentally different vertical-plane quantity than the standard horizontal-plane UV Index). **That's not how it's built.** The LTR-390 sits **horizontally on the top face of the enclosure, sky-facing, under a hole that lets light in** — exactly the geometry the UV Index standard is defined for, and exactly what this project's own enclosure docs have specified since Phase 1 planning (`JCTsh-hiking-monitor-phase1.md`: "must face open sky"; `hiking-monitor-enclosure-instructions.md` Step 17: "LTR-390 sky aperture," a cylindrical hole in the top face). The original explanation should have been checked against these docs before being written.

**Corrected physics, 2026-08-25 — still a real, physically-grounded directional effect, just a different mechanism, and one secondary to (not a redefinition of) the standard UV Index reading:**
- With a genuinely horizontal, sky-facing sensor, the reading should be largely independent of which way the hiker is facing, in principle — it's looking at roughly the same patch of overhead sky regardless of body orientation.
- **Most likely real cause: self-shadowing from the hiker's own body**, strongest at low sun elevation (morning/late afternoon — the actual conditions most of this project's hikes happen in). Hiking into the sun, it's out ahead and above the hiker's own silhouette — nothing blocks it from a body-mounted, upward-facing sensor. Hiking away, the sun is low and behind the hiker, and their own head/shoulders/pack can partially occlude the direct beam before it reaches an enclosure mounted on the front of the body.
- **Second plausible contributor: mounting tilt narrowing the effective field of view.** "A hole to allow light in" (rather than a fully open dome) matters here — a narrower aperture is more sensitive to any forward tilt in how the enclosure sits (a chest-mounted case angled slightly outward, or a hiker's natural forward lean on an incline) than a wide-open window would be, which could tip the effective acceptance cone toward or away from the sun depending on travel direction. Not yet checked against the enclosure's actual mounting geometry/tilt.
- **Revised consequence for this card's own idea, now more optimistic than the original wrong analysis:** since the sensor is genuinely trying to measure the standard horizontal-plane quantity (not something categorically different), the raw number is probably a reasonable proxy for true ambient UV Index most of the time — the directional effect is a real but secondary confound (occlusion/tilt at low sun angles), not a fundamental measurement-orientation mismatch. Still worth checking against real data before trusting a risk-color display at face value, especially for morning/evening hikes.
- **Path forward, still valid, not yet designed:** hike-izer's pipeline already computes both `travel_bearing_deg` (GPS heading) and `sun_azimuth_deg`/`sun_elevation_deg` per point (CARD-0085/CARD-0110) — correlating those against the real UV readings from an actual hike (particularly one with clear direction changes at low sun angles) would directly test the self-shadowing/tilt hypothesis, if worth pursuing at Planning.

**Real data check, 2026-08-25 — the path forward above, actually run against the real 2026-08-25 hike (80 usable `chart_series` points, `travel_bearing_deg`/`sun_azimuth_deg`/`sun_elevation_deg`/`uv_index` all already present per-point).** Result is more nuanced than either the original or corrected hypothesis assumed, and doesn't support building a correction:

- **Crude group comparison** (facing within 60° of the sun vs. 60-120° crosswise vs. 120°+ facing away) shows facing-away with the lowest mean UV (0.51 vs. 0.87 facing-sun) — and notably, the facing-away group also had the *highest* average sun elevation (38.4° vs. 22.4°) in this hike, which should mean naturally *higher* UV from elevation alone, not lower. Directionally consistent with real occlusion suppressing the reading, on the surface.
- **But a proper check doesn't hold it up.** Elevation-normalizing (UV ÷ sin(elevation), a rough air-mass correction) and computing the actual Pearson correlation between facing-angle and normalized UV across all 80 points: **r = -0.06** — essentially zero, no real linear relationship. The three-bucket group-mean pattern doesn't survive contact with the whole dataset.
- **Real limitations on this one check:** a single hike, 80 points, and — critically — this specific hike never had a low-sun-elevation-and-facing-away combination at all (zero data points there), exactly the condition where the hypothesized effect should be strongest. Cloud cover and terrain shading aren't controlled for either. This is a null result from one limited sample, not proof the effect can't exist.
- **Conclusion for this card, 2026-08-25:** don't build a direction-correction model on the strength of this — the real data doesn't show a clear, meaningful directional bias, consistent with the corrected sky-facing-mount physics (which predicted the effect should be secondary/weak, not dominant, unlike the original wrong vertical-mount analysis). **Recommendation for the actual display:** standard EPA/WHO UV Index color bands (Low/Moderate/High/Very High/Extreme) applied to the raw reading, no direction correction — and lead with the hike's *peak* UV value rather than an instantaneous/average one, since peak drives real sun-protection decisions and tends to occur near midday (high sun elevation, where any residual occlusion effect matters least) rather than during a low-sun facing-away stretch. Revisit the correction-model question only if a future hike with real low-sun-facing-away conditions shows this null result breaking down.

**Design decided, 2026-08-25 (Joseph) — the recommendation above, approved as-is:**
1. **Standard EPA/WHO UV Index color bands** (Low/Moderate/High/Very High/Extreme) applied to the raw reading — no direction correction, per the null result above.
2. **Lead with the hike's peak UV value**, not an instantaneous or average one.

**Build-stage decisions, resolved 2026-08-25 evening:**
- **Display location: the UV Index row in `data_summary_rows()` only** (Environmental Data Tracking table). The chart's UV line stays plain (no band-shading) — out of scope for this pass, not decided against, just not built.
- **Bands:** standard EPA/WHO cutoffs used as-is — Low 0-2, Moderate 3-5, High 6-7, Very High 8-10, Extreme 11+.
- **Colors:** two new CSS tokens (`--uv-high`, `--uv-extreme`); Low/Moderate/Very High reuse the existing `--good`/`--warning`/`--danger` severity tokens rather than inventing a parallel palette. A new shared `--badge-ink` token (light-mode white, dark-mode near-black) handles text contrast, since light-mode band colors are dark/saturated and dark-mode band colors are light pastels — same color can't use one fixed text color in both themes.
- **Peak definition:** literal max (`stats['uv_index']['max']`) — no rolling-window smoothing. Simple, and the value was already being computed for the existing min-max range display.

**Built and deployed, 2026-08-25 evening:** `templating.py` — `_UV_BANDS`/`_uv_band()`/`_uv_index_display()` (builds the `Peak X.X <badge>Band</badge> (range min–max)` HTML), `_env_row_value_cell()` (mirrors the existing `_env_row_label_cell()` pattern to bypass the table's generic `_esc()` for this one row's raw-HTML value), `.uv-band`/`.uv-band-*`/`.uv-range` CSS classes, and the new color tokens (light + dark). Deployed to the M8, container rebuilt.

**Verified live against the real 2026-08-25 hike page** (the same hike this whole investigation started from — now showing clean, non-duplicated data thanks to CARD-0215): **"Peak 7.1 Very High (range 0.0–7.1)"**, with a colored "Very High" badge, correctly landing just above the High/Very-High boundary. Temperature/Humidity/Pressure rows unaffected (plain text, unchanged).

**No incremental/caching logic needed, confirmed by design:** unlike photo captions (CARD-0214, which need cost-avoidance tracking across passes), the UV band and peak are cheap to compute and are simply recomputed fresh from `hike_data['stats']['uv_index']` on every render — pass 1 shows whatever the Sheet has at publish time, pass 2 (CARD-0214's gap-fill) naturally reflects whatever's landed since, with zero extra code.

**Known follow-up, not done:** `components/hike-izer/html-template.html` + `.claude/skills/hike-izer/SKILL.md` (the interactive-Skill's own template/instructions, used for manual/historical backfills) don't have the matching UV-band treatment — this project's usual "keep both templates in sync" convention (CARD-0204's precedent) wasn't applied here, since the automated pipeline (`templating.py`) is what serves every real published page. Worth porting if the interactive flow is used again.

**Related:** `components/hike-izer-orchestrator/templating.py` (UV Index stat display, `data_summary_rows()`, `_uv_index_display()`), `components/hike-izer/build_hike_chart.py` (Environmental Data chart's UV line — not band-shaded, out of scope here), `components/hiking-monitor/hiking-monitor.yaml` (LTR-390 UV sensor, the data source), `components/hiking-monitor/hiking-monitor-enclosure-instructions.md` Step 17 (the real sky-facing top-face mounting/aperture this card's corrected physics is grounded in), CARD-0214 (the gap-fill re-fetch this display recomputes against on every pass), CARD-0215 (the data-cleanup that made this hike's real peak/range meaningful to display), PR #36 (the original voice-captured idea this scopes).

---

### CARD-0208 · [enhancement] [hiking-monitor] Spoken mile-marker announcements on the Pixel during a hike
**Status:** Build

**Raised 2026-08-24 (Joseph)**, via the "Log Idea" Tasker widget (PR #35, "mile notifications"). Interviewed same day: wants a **voice** notification (TTS, spoken aloud) on the Pixel at each whole-mile mark during a hike, not a silent push notification — the original PR title undersold what was actually wanted.

**Interviewed 2026-08-24, two design decisions confirmed (via AskUserQuestion):**
1. **Announcement text: just the mile count** — "One mile," "Two miles," etc. Not mile + elapsed time (considered and passed over as extra distraction while hiking).
2. **Trigger: automatic, tied to GPSLogger running** — starts announcing as soon as GPSLogger starts tracking, no separate toggle to remember. Same enabling signal CARD-0086 already established for hike start/end.

**Mechanism, researched (not assumed) 2026-08-24 — real finding changes the design for the better.** GPSLogger only exposes a Tasker-catchable broadcast for its own **start/stop** events (`com.mendhak.gpslogger.EVENT`, already used by CARD-0086) — its per-point location logging (every 30s, this project's configured interval) goes straight to the Apps Script over HTTP with nothing else Tasker can listen to. So live mile-crossing detection can't piggyback on the custom-URL logging path directly.

**But GPSLogger's local CSV output can be reused instead of Tasker running its own independent GPS poll** — confirmed by reading the actual source (`CSVFileLogger.java`, `github.com/mendhak/gpslogger`), not assumed:
- `write(Location loc)` → `annotate()` opens the CSV in **append mode** (`new FileWriter(file, true)`) and writes one row **per logged point, in real time** — same cadence as every other output GPSLogger produces.
- The CSV already carries a **`distance` column** (`Session.getInstance().getTotalTravelled()`) — GPSLogger's own running cumulative-distance total in meters, recomputed and written fresh on every single row. **No haversine math needed on the Tasker side at all** — just read the number.
- Full column order (24 fields, `getCSVFileHeaders()`): `time, lat, lon, elevation, accuracy, bearing, speed, satellites, provider, hdop, vdop, pdop, geoidheight, ageofdgpsdata, dgpsid, activity, battery, annotation, timestamp_ms, time_offset, distance, starttimestamp_ms, profile_name, battery_charging` — `distance` is field 21 of 24.

**Delimiter — decided 2026-08-25, checked against the actual source rather than assumed comma.** `CSVFileLogger.java` doesn't hardcode a comma — it reads a `CSVDelimiter` preference (`PreferenceHelper.getCSVDelimiter()`) and writes rows via Apache Commons CSV's `printRecord()`, which applies proper RFC 4180 quoting/escaping automatically when a field needs it. **Chosen: pipe (`|`), not comma.** Reason: `annotation` (index 17, free text) sits *before* `distance` (index 20) in column order — if `annotation` ever contained a literal comma, Apache Commons CSV would quote that field correctly, but Tasker's plain "Variable Split" action isn't CSV-quote-aware and would split inside the quoted field anyway, shifting every later index and silently reading the wrong value as `distance`. A pipe is never typed into a field by accident, so there's nothing to quote and nothing to shift — costs nothing, since this CSV file has exactly one consumer (this Tasker automation), not shared with any tool expecting standard comma-CSV. Set on the same GPSLogger settings screen as the CSV-format checkbox itself (a "CSV Delimiter" field).

**Why this beats the originally-floated alternative (a second, independent Tasker GPS poll running alongside GPSLogger's own):** avoids the extra battery draw of duplicate GPS polling entirely, reuses a number GPSLogger is already computing for its own purposes, and needs no math logic in Tasker beyond unit conversion (meters → miles, `/1609.344`) and a simple "did this cross a new whole number" check.

**This project's own GPSLogger config currently has local file outputs disabled** (`gps-pipeline.md`: "Logging Details → uncheck all local file formats (GPX, KML, CSV) — Google Sheets is the only needed output") — re-enabling CSV output is a real, deliberate config change, not free, but a small one (an app setting, not new code).

**Design sketch, to confirm/adjust at Planning:**
1. Re-enable CSV local file logging in GPSLogger (alongside the existing custom-URL logging, which stays unchanged — this doesn't touch the Sheets pipeline), and set the CSV Delimiter preference to a pipe (`|`), per the decision above.
2. New Tasker Profile: **File Modified** trigger on the CSV file, active only while GPSLogger is running (gated the same way CARD-0086's own start/stop-driven profiles already are).
3. On each fire: read the file's last line, parse the `distance` field (index 20, 0-based) out of the pipe-split row, convert to miles.
4. Compare against a stored `%last_announced_mile` variable; if the new value's integer floor is greater, `Say` "\<N\> mile(s)" (Tasker's built-in offline TTS) and update the stored value.
5. On GPSLogger's `stopped` broadcast (already-used signal): reset `%last_announced_mile` for the next hike.

**Live test run, 2026-08-26 (Joseph) — both real-device open questions answered, confirmed not assumed:**
- **Delimiter confirmed live:** each row's fields are genuinely pipe (`|`)-separated (the CSV Delimiter setting from the design decision above took effect correctly) — `distance` is a real numeric value (meters) at the expected field position, and it increases row to row while walking, exactly as designed.
- **File-naming: one file, not one per session.** Starting GPSLogger a second time **appended to the same CSV file** rather than creating a new one — Tasker's "watch this file" target can stay fixed once set, no need to recompute it at each hike start.
- **Distance accumulator: confirmed resets to 0 per session**, even though the file itself persists across sessions — the second session's rows started back at 0, not continuing from session 1's ending value. Confirms `Session.getInstance().getTotalTravelled()` is scoped to the logging session, not the file, exactly as the design assumed (and needed, for `%last_announced_mile`'s reset-on-`stopped` logic to make sense against a persistent file).

**Open questions for Build — not yet resolved:**
- Whether GPSLogger's own `distance` accumulator does any accuracy/noise filtering, or sums every raw fix unfiltered — a real-time convenience feature can tolerate more noise than hike-izer's own precise post-hike mileage stat (CARD-0110's GPS-accuracy-filtering fixes), so this is a "note the discrepancy is possible, don't block on it" item, not a blocker.
- Whether Tasker's "read last line of a file" is cheap enough at typical hike-length CSV sizes (`gps-pipeline.md`'s own estimate: ~1,200 rows / ~75KB for a 10-hour hike) — almost certainly fine for local phone I/O, but worth a real spot-check once built.
- Exact Tasker action sequence (File Modified event availability/reliability, string-parsing the CSV line, the math/comparison actions) — Joseph builds and confirms the actual Tasker profile, matching this project's established division of labor for every prior Tasker-side feature (CARD-0007, CARD-0086, CARD-0122, CARD-0156).

**Done when:** GPSLogger's CSV output is confirmed live-appending with a real `distance` value during an actual test walk, the Tasker profile correctly speaks each new whole mile with no repeats/skips, and it correctly stays silent (no announcements) when GPSLogger isn't running.

**Implementation deviated from the design sketch above, discovered 2026-08-27 debugging session — noting for the record.** What actually got built is a **Time-based Profile** ("Mile Announcement," firing every 2 minutes) running a "Mile Announcer" task, not the sketched "File Modified" event trigger (step 2 above) — reads the CSV fresh on each timed tick rather than reacting to file-write events. Functionally equivalent for this purpose, just a different mechanism than originally planned; not worth reworking now that it's confirmed working.

**Real end-to-end debugging session, 2026-08-27 — four distinct real bugs found and fixed, working live by the end.** Investigated after today's hike (2026-08-27) was reported as "still not working" despite the design above already being built. Diagnosed collaboratively against real Tasker screenshots and live Flash-based value checks (not just log reading, which repeatedly proved ambiguous/truncated and cost real time before switching to direct value inspection):

1. **Private storage, confirmed actually fixed** — Joseph's earlier fix (moving GPSLogger's CSV export off the app-private `Android/data/...` sandbox to shared storage) is genuinely working; Read File succeeds with no error this session, unlike the original CARD-0208-era failure.
2. **Stale hardcoded filename.** The Read File action's File field was a literal `Download/20260826.csv` — yesterday's date, never updated. Fixed by adding a **Parse/Format Date and Time** step (same technique already used for the `local_datetime` field in the Hike-izer Webhook task) producing `%todays_date` in `yyyyMMdd` format, and changing the File field to `Download/%todays_date.csv`.
3. **`%current_mile` never actually computed.** Its Variable Set action (`floor(%distance_m / 1609.344)`) had **"Do Maths" unchecked** (so the formula was never evaluated, just stored as literal text) **and "Structure Output (JSON, etc)" wrongly checked** (silently failed to parse the non-JSON result). Fixed: checked Do Maths, unchecked Structure Output.
4. **The real root cause, found last and explaining everything upstream of it too: the Splitter field on the very first Variable Split (splitting the whole file into lines) contained the literal two characters `\n` (backslash, n) typed as text, not an actual newline character.** Confirmed directly: `%file_content(#)` (element count) read **1** — the entire file was one unsplit blob, so every downstream "get the last line" attempt (several were tried, including the officially-correct `%file_content(<)` syntax, verified against Tasker's own docs) kept returning the same single element, which happened to start with the CSV's own header row, making it look like a last-line-selection bug when the split itself had never worked at all. Root-caused per Tasker's own documentation, which explicitly warns about exactly this: *"For the sign \n, press carriage-return on the keyboard"* — the field needs a real inserted line break, not typed escape text. Fixed by clearing the field and pressing Enter directly in it. Confirmed: `%file_content(#)` jumped from 1 to **410** (a real, plausible line count for today's multi-hour session).

**Verified live, 2026-08-27:** with all four fixes in place, a real run against today's actual GPS data spoke **"seven miles"** aloud — correctly matching today's real hike distance (7.0 mi, confirmed independently via the hike-izer page). `%LAST_ANNOUNCED_MILE` (all-caps global, correctly scoped) updated accordingly.

**Not yet confirmed — stays in Build, not Done:** this was a single retroactive catch-up announcement (0→7 miles all at once, since the fix landed after the hike had already ended), not a live in-hike test of the intended one-mile-at-a-time cadence. Still open: (a) a real hike where it announces correctly at each individual mile as it's crossed, not just a bulk catch-up; (b) confirmation it stays silent when GPSLogger isn't running; (c) whether `%LAST_ANNOUNCED_MILE` actually resets between hikes (step 5 of the original design sketch — a reset tied to GPSLogger's `stopped` broadcast — wasn't observed/confirmed to exist in the built task during this session's debugging, worth checking before the next hike).

**Related:** CARD-0086 (the GPSLogger start/stop broadcast this reuses as the enabling signal), CARD-0110 (hike-izer's own server-side distance computation and GPS-noise-filtering — a different, more precise pipeline this doesn't need to match exactly), `components/hiking-monitor/gps-pipeline.md` (GPSLogger's current custom-URL-only configuration, the "local file outputs disabled" note this card reconsiders), PR #35 (the original voice-captured idea this scopes).

---

### CARD-0207 · [enhancement] [hike-izer] Battery discharge-rate indicator, per-hike stat + cross-hike trend page — RESOLVED 2026-08-24
**Status:** Done

**Raised 2026-08-24 (Joseph)**, following a conversation about whether the CARD-0196 display-refresh throttle is actually helping battery endurance. A bench current test (CARD-0026's original method) would give a precise, direct answer, but Joseph declined doing one right now — wants an ongoing, lower-effort field indicator instead, visible on the hike-izer webpage over time rather than something that has to be asked for and computed by hand each time.

**What this doesn't replace:** a real bench current measurement is still the only way to *prove* a specific firmware change's effect in isolation (no LiPo-curve confound, no weather/condition variance). This card is a rough, ongoing field trend signal — good for noticing "is this getting better or worse over months of real hikes," not for validating one specific commit.

**Design, worked out in conversation 2026-08-24:**
1. **Fixed reference voltage window, not a per-hike ad hoc one.** A LiPo's voltage-vs-charge curve is non-linear (steeper near full and near empty, flatter in the middle) — comparing each hike's own full start-to-end range makes hikes with different starting charge levels or lengths incomparable, confirmed directly: the 2026-08-22 hike's raw full-range rate (3.23 mV/min) vs. 2026-08-24's (5.23 mV/min) looked like a 62% regression, but re-measuring the identical 4.00V→3.70V slice in both hikes' own data narrowed the real gap to ~19% (75.1 min vs. 60.7 min to cross it) — most of the raw-range gap was curve-position artifact, not real. **Window chosen: 4.00V → 3.70V** — both of the two most recent real hikes happened to fully cross this range, and it sits clear of both the near-full "shoulder" and the near-cutoff (3.4V) steep zone.
2. **Per-hike stat:** for any hike whose field-mode `battery_v` readings fully bracket both 4.00V and 3.70V, linearly interpolate the crossing times (matching the method used live in this conversation) and report "minutes to cross 4.00V→3.70V." Hikes that don't fully span the window (too short, or started already below 4.00V) report "not available" rather than a misleading partial-window number — same "omit rather than guess" convention every other hike-izer stat already follows.
3. **Cross-hike trend page**, new standalone page (Joseph's call, via AskUserQuestion 2026-08-24) mirroring `build_wildlife_index.py`'s existing pattern (CARD-0142) — one row per hike with this stat, sortable, linked from the calendar page's nav alongside the existing Wildlife Life List link. Hikes with "not available" show as such, not omitted from the list entirely (keeps it a complete index, same convention as every other hike-izer index page).

**Open questions, resolved at Build 2026-08-24:**
- **Module home: `fetch_hike_data.py`'s `compute_stats()`, not `compute_hike_detail_stats()`.** The latter only takes `gps_rows`/`sessions`/distance/duration -- no `env_rows`, which is what the battery readings actually live in. `compute_stats(env_rows, gps_rows)` already computes the existing `battery_v` min/max range from the same rows, so the new `_battery_window_crossing_min()` helper lives right next to it and feeds a new `battery_window_crossing_min` key in that same returned dict.
- **Page name: `battery-trend.html`. No separate persistence file** -- `build_battery_trend_index.py` scans `SRV_DIR` for `*_hike-summary.meta.json` sidecars (same source-of-truth convention `build_calendar_index.py` already uses) and reads each hike's own persisted `<file_stem>_hike_data.json` in `PRIVATE_DIR` directly, avoiding a second accumulating source of truth like `wildlife_life_list.json` would have been.
- **Backfill: free, not a special step.** Since the trend page recomputes from whatever's in `PRIVATE_DIR` on every rebuild rather than accumulating incrementally, any past hike whose `hike_data.json` still exists is automatically covered the moment it's re-fetched. Did this live for the two hikes discussed in conversation (2026-08-22, 2026-08-24) by re-running `fetch_hike_data.py` against each one's own already-recorded query window (free re-query, no API cost) -- the other 13 already-published hikes' persisted files predate this field and correctly show "not available" rather than a guess; backfilling them is just re-running the same free fetch, not done today since nobody asked for the full history yet.
- **Units: `"{X:.1f} min per 0.30V (4.00V→3.70V)"`** -- literal minutes-to-cross-the-fixed-window, matching exactly what was already shown in conversation, not a further-normalized rate.

**Explicitly out of scope:** any bench current measurement (declined for now), any change to CARD-0196's actual throttle firmware, and using the new `display_refresh` MQTT log events (CARD-0196) as a data source — those live only in the Pi's log dashboard, not the Environmental Data/GPS Sheets pipeline hike-izer already reads from, and pulling them in would be new plumbing beyond this card's scope unless a real need for it comes up later.

**Built 2026-08-24:**
- `components/hike-izer/fetch_hike_data.py`: `BATTERY_TREND_WINDOW_HIGH_V`/`_LOW_V` constants (4.00/3.70), `_battery_window_crossing_min(env_rows)` (restricted to `rssi_dbm == 0` field-mode rows -- a docked/charging reading mixed into the same query window would rise instead of decline and corrupt the interpolation; returns `None` when the hike's data doesn't fully bracket both reference points), wired into `compute_stats()`'s returned dict.
- `components/hike-izer-orchestrator/templating.py`: new `_battery_discharge_display()` helper and a "Battery Discharge Rate" row appended to `data_summary_rows()`, right after Battery Voltage. Reuses the module's existing `NA` constant for the not-available case; the whole-table omit-when-empty gate (`has_env_data`) is untouched since it checks the underlying sensor stats, not this derived field.
- New `components/hike-izer/build_battery_trend_index.py` (stdlib-only, modeled directly on `build_wildlife_index.py` -- same inline `_STYLE`, same click-to-sort JS pattern). Scans `SRV_DIR` for meta.json sidecars, cross-references each `PRIVATE_DIR` hike_data.json, renders one sortable row per published hike (reverse-chronological), "not available" rows included rather than omitted (same complete-index convention as the calendar and wildlife pages). Date formatting done by hand rather than `strftime("%-d")` -- that flag is a Linux-only glibc extension, the exact non-portability CARD-0110's own chart code hit before.
- `components/hike-izer/build_calendar_index.py`: nav link added (`Battery Trend →`, next to the existing Wildlife Life List link) in both the populated and empty-state page templates.
- `components/hike-izer-orchestrator/generation.py`: new `BUILD_BATTERY_TREND_SCRIPT` constant, called unconditionally (unlike the wildlife index, no birdnet-style optional gate -- every hike's `hike_data.json` already has the stat computed) right after the calendar rebuild, in both `run()` (step 1) and `run_step2()`.
- `Dockerfile`/`README.md` updated for the new deployed-copy file, same pattern as `build_calendar_index.py`/`build_wildlife_index.py`.
- `.claude/skills/hike-izer/SKILL.md` updated in parallel (CARD-0204/CARD-0206's own "keep both templates in sync" discipline) with the same row-rendering instructions for the interactive-Skill path.

**Verified, 2026-08-24 — unit tests first, then real production data, not just "it compiles":**
- `_battery_window_crossing_min()` unit-tested against both real hikes' actual Environmental Data export: reproduced 75.1 min (2026-08-22) and 60.7 min (2026-08-24) exactly matching the numbers computed live in this same conversation, plus correctly returned `None` for an empty-data case.
- `build_battery_trend_index.py` unit-tested against synthetic meta.json/hike_data.json fixtures (2 hikes with a rate, 1 with a missing hike_data.json) -- correct sort values, correct `na` styling, correct subtitle count.
- Deployed to the M8 (`scp` + `docker compose up -d --build orchestrator`, confirmed healthy). Re-fetched both real hikes' `hike_data.json` fresh against their own already-recorded query windows (free, no API cost) to populate the new field, then ran `build_battery_trend_index.py` for real: **15 real published hikes indexed, 2 with a computable rate** (60.7 min / 75.1 min, exact matches), 13 correctly "not available." Confirmed live on the public site: `https://hikes.jctnet.com/battery-trend.html` (HTTP 200), `index.html`'s nav link present and working. Both hikes' own pages surgically re-rendered in place (reusing already-fetched photos manifests, no narrative call -- neither had step 2 run) and confirmed live showing `"Battery Discharge Rate: 75.1 min per 0.30V (4.00V→3.70V)"` / `"60.7 min..."` respectively.

**Done when:** ~~the per-hike stat renders correctly~~ — met, both real pages confirmed live. ~~the new trend page is live with at least the 2026-08-22 and 2026-08-24 hikes' real data points~~ — met. ~~linked from the calendar page's nav~~ — met.

**Two follow-on refinements, same session, both live-verified:**
1. **Battery Discharge Rate label hyperlinked to the trend page** (Joseph's ask, right after the initial build) — `templating.py`'s new `_env_row_label_cell()` renders that one row's label as `<a href="battery-trend.html">` instead of plain escaped text (every other label in this table stays plain, since only this one needs to link anywhere). Deployed and confirmed live on both real hike pages.
2. **Hikes with no computable rate eliminated from the trend page entirely, not shown as "not available" rows** (Joseph's ask, reversing the original complete-index design) — `build_battery_trend_index.py`'s `_render_page()` now filters them out in Python before the page is generated (not CSS-hidden), so they're genuinely absent from the HTML. The subtitle still names the hidden count and why ("13 earlier hike(s) not shown -- predate this stat or too short to measure") so their existence isn't silently lost, just not cluttering the table. Confirmed live: the real page went from 15 rows (13 "not available") to exactly 2 real data rows plus the header, byte-verified via a fresh `grep -o "<tr>"` count against the live HTML.

**Related:** CARD-0196 (the throttle change this indicator exists to help evaluate over time), CARD-0026 (the bench-measurement precedent this doesn't replace), CARD-0142 (Wildlife Life List, the cross-hike index pattern this mirrors), CARD-0206 (sibling stat-calculation fix, same session, same "regenerate in place" verification pattern), `components/hike-izer/fetch_hike_data.py`, `components/hike-izer/build_battery_trend_index.py`, `components/hike-izer-orchestrator/templating.py`, `components/hike-izer-orchestrator/generation.py`.

---

### CARD-0206 · [bug] [hike-izer] Environmental Data coverage stat measures against the padded query window instead of the real GPS session bounds — RESOLVED 2026-08-24
**Status:** Done

**Raised 2026-08-24 (Joseph)**, reviewing the 2026-08-24 hike ("Boulder Pass Loop") alongside the hiking-monitor Build cards. That page's Environmental Data Tracking table read "44 of 47 expected (93.6% coverage)" — looked like a real 3-sample gap worth explaining via CARD-0195's new skip-reason logging, but the skip/reset log stayed completely silent for the whole hike despite the firmware being confirmed flashed.

**Root cause, traced by pulling the real `coverage` object out of the hike's persisted `hike_data.json` on the M8:** `analyze_coverage()` (`components/hike-izer/fetch_hike_data.py`) computes `expected_env = round(duration_min / 2)` from the *entire requested query window* (`start_dt` to `effective_end_dt`) — which is the GPS session's own bounds padded ±10 min each side (`SESSION_QUERY_PADDING`, `generation.py`), not the session's real bounds. Confirmed exactly: real GPS session ran 82.4 min (13:38:16–15:00:40Z); the query window was `(session_start − 10min)` to `min(session_end + 10min, now)` — and since step 1 generation ran only ~1 minute after the hike ended, that padded end got truncated to "now" rather than the full +10min, landing at 93.27 min of window duration. `round(93.27 / 2) = 47` — an exact match for the reported figure, confirming the "47 expected" was measuring 10 minutes of dead time *before* the hiking-monitor was even switched on (plus a few more from the truncated tail padding), not a real reading gap. The real field-mode window (`hiking-monitor`'s own first-to-last reading, 13:40:16–14:56:49Z) was only ~76.6 min, against which 43 field-mode readings is at-or-above a clean 2-min cadence — no real deficit at all.

**Inconsistency this reveals:** `gps_track`'s own per-session coverage stat already does this correctly — `expected_points` is computed from each detected session's own real `start`/`end` (no padding), which is why it correctly showed 165/165 = 100% on the same hike. `environmental_data`'s coverage stat is the only one still measuring against the wider padded fetch window instead of matching that same session-scoped convention.

**Decided fix (interviewed 2026-08-24):** keep the ±10 min padding for what actually needs it — *fetching* data, so boundary-adjacent readings/observations aren't clipped — but compute the Environmental Data coverage denominator from the real GPS session bounds (summed `duration_minutes` across every session `_gps_sessions()` detects in the window, hike-classified or not — this is about real elapsed activity time, not hike/non-hike judgment) instead of the outer padded `start_dt`/`end_dt`. Falls back to the current whole-window behavior only when zero GPS sessions exist in range (e.g. environmental readings present with no GPS track at all) — no regression for that edge case.

**Accepted trade-off:** a reading that happens to land in the padding buffer (like this hike's one non-field-mode tail reading, captured after reconnecting post-hike) now counts as a small bonus against the narrower expected denominator rather than being absorbed into a bigger one — harmless, arguably more honest than the current behavior.

**Scope:**
1. `components/hike-izer/fetch_hike_data.py`'s `analyze_coverage()`: compute `env_expected_duration_min` from summed real GPS-session durations (falling back to the existing whole-window `duration_min` when no sessions exist), use it for `expected_env` instead of the padded-window `duration_min`. `duration_hours` (the top-level whole-window figure, used elsewhere) stays unchanged.
2. Verify against today's real persisted 2026-08-24 hike data (re-fetched via the same original query window, no new API cost) — expected should drop from 47 to something close to the real ~76.6 min field window (≈38-39), and coverage should read at or above 100%, not 93.6%.
3. Re-render and redeploy the already-published `2026-08-24_hike-summary.html` with the corrected figure once verified, same "regenerate in place, reuse already-fetched data" pattern this project always uses for a stat-only fix (CARD-0101, CARD-0120).

**Done when:** the fix is verified against today's real hike data showing a corrected, non-misleading expected/coverage figure, deployed to the M8 orchestrator, and the live `2026-08-24_hike-summary.html` page reflects the corrected numbers.

**Built and verified, 2026-08-24, same session.** `analyze_coverage()` now sums `duration_minutes` across every `_gps_sessions()`-detected session (real bounds, no padding) as the Environmental Data expected-readings denominator, falling back to the old whole-window `duration_min` only when zero GPS sessions exist. Unit-verified two ways before touching real data: a synthetic replica of today's hike shape (82.4-min session, 43 field-mode readings) dropped `expected_env` from 47 to 41 and coverage from 93.6% to 104.9%; the zero-session fallback case reproduced the exact old-behavior numbers (30/30/100%), confirming no regression for that path.

**Deployed and verified against the real 2026-08-24 hike, not just synthetic data.** Redeployed `fetch_hike_data.py` to the M8 orchestrator (`docker compose up -d --build orchestrator`, confirmed healthy). Re-ran it inside the container against the hike's own exact original query window (`2026-08-24T13:28:16Z`–`15:10:40Z`, pulled from the persisted `hike_data.json`'s own `query` field — a plain Apps Script re-fetch, no API cost) — real corrected output: **41 expected, 44 actual, 107.3% coverage** (was 47/44/93.6%), against a real GPS session of 82.4 min. Persisted the corrected `hike_data.json`, then regenerated `2026-08-24_hike-summary.html` in place (same "reuse already-fetched photos manifest, no narrative re-run" pattern as CARD-0140/CARD-0120 — this hike never had step 2/narrative run, so nothing else needed re-fetching). Confirmed live on the public page (`https://hikes.jctnet.com/2026-08-24_hike-summary.html`, HTTP 200): "Readings Recorded: 44 of 41 expected (107.3% coverage)" — all other sections (8 data-source labels, both env chart mode panels) confirmed present and unchanged, no regression from the surgical re-render.

**Reflection:** the durable fix lives in `analyze_coverage()`'s own code comment (why the denominator has to match `gps_track`'s session-scoped convention, not the padded fetch window) — no separate doc needed, this was a narrowly scoped stat-calculation bug, not a new pattern worth writing up elsewhere. The bug was only found because CARD-0195's skip-reason logging staying silent against an apparent 3-sample gap didn't add up — worth remembering that a "clean" diagnostic result is itself a signal worth chasing down, not just a relief.

**Related:** CARD-0195 (the skip-reason diagnostic this misleading stat was initially mistaken for evidence against), CARD-0113 (introduced the session-scoped query-window padding this fix has to respect while still fixing the denominator), CARD-0140/CARD-0120 (precedent for in-place stat-only page regeneration without a full re-render), `components/hike-izer/fetch_hike_data.py` (`analyze_coverage`, `_gps_sessions`).

---

### CARD-0205 · [enhancement] [air-quality-monitor] Secondary debug UART for battery-powered serial logging via external USB-TTL adapter
**Status:** Build

**Moved to Build 2026-08-24 (Joseph) — explicitly paused, not started.** "Move it to Build, but don't change any YAML until we are ready to use it. We'll pick up with testing the air-quality-monitor later." No firmware change made yet — the `logger:`/`hardware_uart:`/`tx_pin:` edit described below waits for Joseph's go-ahead to actually begin, not just for the physical adapter/wiring prep to be ready.

**Raised 2026-08-24 (Joseph), after receiving a HiLetgo CP2102 USB-to-TTL adapter with no defined purpose yet.** Interviewed to find a real use: air-quality-monitor's boot behavior is still under active investigation (CARD-0198 fixed a firmware boot race, but the underlying "power-on event" resets found in `state.json` earlier this session haven't been fully explained) — a serial console that works while the device is powered from its real LiPo/LDO path, not from the board's own onboard USB-C, is a genuine diagnostic gap this adapter can fill.

**Why the board's own onboard USB-C port doesn't already cover this:** `wiring.md`'s LDO section explicitly warns against powering the board from USB and the LDO simultaneously (risk of backfeeding both regulators) — the documented workaround is flipping the inline power switch off before flashing over USB, which also kills LDO/battery power entirely. That means the board's own USB-C port can never show boot logs while the device is genuinely running on battery power — exactly the power path the resets being investigated happen on.

**Why not just tap the onboard CP2102's own TX0/RX0 lines (GPIO1/GPIO3) with the new adapter:** those pins are already driven by the onboard CP2102 chip, which is powered by the board's own 3.3V rail (fed by the LDO) independent of whether anything's plugged into the USB-C port — so an external adapter wired to the same pins risks electrical contention with the onboard chip's own driver, not a clean tap.

**Design, from the pre-card discussion — corrected 2026-08-24, see dated update below:** move ESPHome's `logger:` to a second UART instead of GPIO1/3. **Originally planned for GPIO27** (freed 2026-08-21 when the SEN55 power-gate transistor was dropped) — **corrected same day: ESPHome's `logger:` component has no `tx_pin` option, so `hardware_uart: UART2` uses that peripheral's fixed pins, TX=GPIO17/RX=GPIO16, not GPIO27.** ESPHome's logger only transmits (device → computer), so only 2 wires are needed, not 4: `GPIO17 → adapter RXD`, `ESP32 GND → adapter GND`. The adapter's own VCC/3V3 output pin stays deliberately disconnected — the board must stay powered exclusively by its LDO/battery for this to test what it's meant to test, connecting the adapter's own power pin too would recreate the exact dual-power-source risk this design is built to avoid.

**Scope:**
1. `air-quality-monitor.yaml`: add `hardware_uart: UART2` to the existing `logger:` block (no `tx_pin` — see correction above; GPIO17 comes from UART2's own fixed pin assignment, not a config option).
2. Prep the physical adapter: install the CP210x driver if Windows doesn't auto-detect it (same driver already referenced in `front-porch-temp-sensor/flashing.md`/`garage-radar/flashing.md`), and **set its voltage-select jumper to 3.3V, not 5V** before ever connecting it to the board — the one step that actually matters for board safety.
3. Wire GPIO17 → adapter RXD, ESP32 GND → adapter GND, on the breadboard (device is still in breadboard/Phase 1 state, confirmed 2026-08-24 — not yet transferred to perfboard/enclosure, so this is a straightforward jumper addition, not a perfboard rework). **GND is the connection most worth double-checking** — a loose/disconnected GND produces silent zero-byte output with no other symptom, see the dated update below.
4. Flash the firmware change (OTA is fine — this isn't a bootloader-level change).
5. Verify: connect the adapter to a PC, confirm it enumerates as a COM port, and confirm real boot-time log lines actually appear (`esphome logs air-quality-monitor.yaml --device COMx` or an equivalent serial terminal at 115200 baud) while the board is powered only from its LiPo/LDO path, USB-C disconnected.
6. Document the addition in `components/air-quality-monitor/wiring.md` (new section, matching the existing pattern used for the Inline Power Switch / SEN55 Power Gate sections — what it's for and why the onboard USB-C port doesn't already cover it) and update `ESP32-project-pins.md`'s GPIO17 row to reflect the new debug-UART assignment (GPIO27 stays "Unused — SEN55 power-gate dropped 2026-08-21", unaffected by this correction).

**Explicitly out of scope (Joseph's call, 2026-08-24):** actually using this to diagnose the power-on-event resets. This card closes once the mechanism itself works — a real boot log observed coming through the adapter while the device runs on battery power. Using it to investigate the resets is real follow-on work, either a new card or folded into CARD-0198's own thread once it comes up.

**Done when:** the `logger:` UART2/GPIO17 change is flashed, the adapter is wired per the corrected design below, a real boot sequence's log output is confirmed arriving over the adapter while the board is powered exclusively from its LiPo/LDO (not USB-C), and both `wiring.md` and `ESP32-project-pins.md` reflect the change.

---

**Long troubleshooting arc, 2026-08-24 — picked up as part of CARD-0198's own investigation once a reproducible SEN55+battery failure made real diagnostic output worth having. Design corrected, wiring finally confirmed working; end-to-end log capture not yet verified.**

**Real design error found before any wiring even happened: GPIO27 was never actually usable for this.** ESPHome's `logger:` component has **no `tx_pin` option at all** — confirmed by reading the installed `esphome` package's own `logger/__init__.py` config schema directly rather than trusting the original plan. `hardware_uart: UART2` only selects one of the ESP32's fixed hardware UART peripherals; its pins aren't remappable through this component. On the original ESP32 (Arduino framework), UART2's pins are hardwired to **TX=GPIO17, RX=GPIO16** — not GPIO27. GPIO17 was confirmed unused on the board and is what's actually wired: `GPIO17 → adapter RXD`, `ESP32 GND → adapter GND` (RX/GPIO16 unused, logger is transmit-only). `air-quality-monitor.yaml` and this scope section corrected accordingly; `ESP32-project-pins.md` and `wiring.md` updated to match.

**The corrected wiring then produced zero bytes of output across every single test for the rest of the night** — including a clean side-by-side control test (the external adapter listening on one COM port, `esphome logs` running simultaneously over the ESP32's own onboard USB on another, both watching the identical boot event): the onboard channel showed full, real ESP-IDF bootloader and application log output; the external adapter showed nothing at all. That proved the fault was specifically in the external adapter's link, not the board's actual behavior — but didn't say what was wrong with it.

**Systematic isolation, in order:**
1. **Loopback test** — adapter's own TXD jumpered directly to its own RXD, disconnected from the ESP32 entirely. Sent known bytes to the COM port and read them back byte-for-byte. **Passed** — confirmed the adapter, its CP210x driver, and the COM port were all genuinely working; the fault had to be in the GPIO17/GND wiring to the board or the pin identity itself.
2. **Board swap** — the ESP32 itself was replaced with a fresh unit, and this time the pin numbers/assignments in `ESP32-project-pins.md` were directly confirmed against the new board's own physical silkscreen (rather than trusted from the table alone, since the original board's silkscreen wasn't legible enough to verify).
3. **GPIO17 pin-identity test** — a temporary firmware build (`logger:` reverted to default UART0, since it can't share GPIO17 with a plain GPIO output at the same time) toggling GPIO17 HIGH/LOW once per second, checked directly with a multimeter at the physical pin. **First two attempts showed a constant, non-toggling ~3.3V** — both times traced back to the exact same stale-build bug CARD-0198 already found once (`esphome upload` silently flashing an old cached `firmware.bin` instead of the just-edited config, because `esphome compile` wasn't run explicitly first). Once actually recompiled fresh each time, GPIO17 showed a genuine toggle.
4. **The real root cause, found last: the adapter's GND wire had come disconnected** (during the loopback test's rewiring) and was never reconnected before the pin-identity test began. Once GND was properly reconnected, the multimeter confirmed GPIO17 genuinely toggling, and — independently — **the adapter's own RXD activity LED started flashing in sync**, real physical confirmation the signal was reaching the adapter correctly. A missing GND reference would have silently broken every single UART byte this whole session, even on a perfectly wired TX line, since UART has no way to decode a signal with no common ground reference. This is almost certainly the actual explanation for the entire night's zero-byte results, including the side-by-side control test.

**Current state, 2026-08-24 ~16:25 MST:** temporary test scaffolding removed, `logger: hardware_uart: UART2` restored, config validated and freshly compiled (`config_hash=0xbb906098`, `build_time_str=2026-08-24 16:24:22 -0700`) and flashed to the new board. **Not yet verified end-to-end** — the pin-identity test confirmed the electrical path works, but a real captured boot-log line over the adapter (the card's actual done-when) hasn't been observed yet. That's the immediate next step next session.

**Correction, 2026-08-28 — the GND fix above did not turn out to be the full story.** Later the same day (2026-08-24 ~16:30-17:40 MST), CARD-0198's continued session tried to actually use this UART to capture a Stage 0 reset and got **zero bytes across many repeated attempts**, despite the GND-fix'd pin-identity test passing cleanly. Working theory there: a connection marginal enough to corrupt real 115200-baud UART framing could still pass a slow ~1Hz toggle test — untried next step is dropping to 9600 baud on both ends. This card's own "done when" (a real captured boot-log line) is still not met; further troubleshooting continues under CARD-0198's thread rather than here, since it's now entangled with that card's own hardware-swap plan.

**Resolved 2026-08-28 — real root cause found, not a wiring/baud problem at all.** Continuing under CARD-0198's minimal-test rig: 9600 baud produced the same zero-byte result as 115200, but with continuity independently confirmed good and the adapter's own RXD LED never once lighting despite confirmed real boot events — ruling out both the wiring and baud theories. A control test on the onboard USB port (COM8) then found two unrelated firmware bugs (logger.log: actions default to DEBUG level, silently filtered by this file's level: INFO; and the debug component's reset_reason_text is only populated during dump_config(), not setup()/on_boot — same bug CARD-0217 found on hiking-monitor). Fixing both still produced zero bytes on the external adapter specifically, which finally isolated the real cause: reading ESPHome's own installed `logger_esp32.cpp` source directly showed it calls `uart_param_config()`/`uart_driver_install()` for `hardware_uart: UART2` but **never `uart_set_pin()`** — UART1/UART2 have no fixed IO_MUX pin the way UART0 does, so without that call the peripheral is configured and running but never actually connected to GPIO17 through the GPIO matrix. This is a real gap in ESPHome's own UART2 support, not anything wrong with this project's wiring, board, or adapter. **Fixed with a manual `on_boot` lambda** (`uart_set_pin(UART_NUM_2, GPIO_NUM_17, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE)`) — confirmed live: clean `"BOOT - reset reason: power-on event"` text captured over the external adapter, RXD LED flashing in sync. Full pattern (all three fixes) recorded in `components/air-quality-monitor/minimal-test.yaml`'s header comment for reuse in the real component.

**Remaining before this card is fully Done:** the confirmed capture above was on USB power (COM8 board reachable, board running off USB during the control-test sequence) — this card's own "done when" specifically requires the board powered exclusively from LiPo/battery, not yet separately re-confirmed. Expected to happen naturally once CARD-0198's Stage 0 is re-run on battery power with this now-working UART, not planned as a standalone re-test.

**Second real intermittent-connection instance, 2026-08-28, same session — root-caused this time, not left as an open theory.** During CARD-0198's own battery-power reset investigation (same session), capture went from working cleanly to producing zero bytes across two separate reset attempts, with no firmware change in between — Joseph found the actual cause directly: **the adapter's own GND wire had disconnected.** Exactly the same failure signature this card already documented once before (missing GND reference silently breaks every UART byte, even on a perfectly wired TX line, no other symptom) — confirms that finding rather than contradicting it, and explains this whole investigation's history of intermittent results without needing a new theory. Reseated; capture confirmed working again immediately after (`"BOOT - reset reason: power-on event"`). **Standing caution for any future session using this adapter on breadboard:** the GND jumper is the single point most likely to work loose during handling and produces a completely silent failure (no error, no garbled data — just nothing) — worth a quick continuity check any time capture unexpectedly stops working, before assuming a firmware regression.

**Related:** CARD-0198 (the boot-race fix that surfaced the still-open "power-on event" reset question this tool is meant to help investigate — now actually able to, and the thread where the real UART2 root cause was found), `components/air-quality-monitor/wiring.md` (LDO/USB-power-conflict section this design works around; debug UART section corrected to GPIO17), `components/air-quality-monitor/ESP32-project-pins.md` (GPIO27 reverted to unused, GPIO17 now the debug-UART TX entry), `components/air-quality-monitor/minimal-test.yaml` (the working fix pattern: level: WARN, deferred reset-reason read, manual uart_set_pin() lambda).

---

### CARD-0204 · [enhancement] [hike-izer] Environmental Data (temp/humidity/pressure/UV) on the Elevation & Speed chart — RESOLVED 2026-08-24
**Status:** Done

**Raised 2026-08-24 (Joseph):** "I want to add the hiking monitor data to the graph: temp, humidity, pressure, UV." Currently the Elevation & Speed chart (CARD-0110) only plots GPS-track-derived series (elevation, speed) against distance — the JCTsh Hiking Monitor's own environmental readings (Environmental Data Tracking section) exist on the page as a summary table but never appear on any chart.

**Interviewed 2026-08-24, four design decisions made:**

1. **Own standalone card, not folded into CARD-0194.** This is a real new capability — a new data source feeding the visuals, plus a genuine timestamp-correlation problem to solve — distinct enough from CARD-0194's page-polish items to track separately.
2. **Single new chart panel, legend-toggle between two preset pairs** — not 4 lines on the existing chart (unit/scale mismatch would make that unreadable, per the original exploratory discussion), not a full pick-any-2 axis-assignment UI (real complexity for a combination nobody's asked for). One toggle switches the whole panel between **Temp + Humidity** and **Pressure + UV**, each its own pre-scaled dual-Y-axis pairing, same visual language as the existing Elevation/Speed chart. **Temp + Humidity shown by default** on page load.
3. **Gap handling: interpolate across missing stretches**, rather than splitting the line the way `session_break` does today — Joseph's explicit call, overriding Claude's initial lean toward splitting. Any interpolation still needs a sane cap so a long real gap (sensor not carried, device off) doesn't draw a misleadingly flat/linear line across hours of missing data — reuse `build_hike_map.py`'s existing `interpolate_position()` precedent (CARD-0133: linear interpolation between bracketing readings within a max gap, e.g. its existing `MAX_INTERPOLATION_GAP_SEC = 600`; beyond that, no line drawn through that stretch) rather than inventing new gap-handling logic. Exact cap value to confirm at Build — may differ from 600s given Environmental Data's own ~2-min native cadence, vs. GPS's ~30s.
4. **Full three-way hover-sync** with the Route Map and existing Elevation & Speed chart, via the same `hikeizer-chart-hover`/`hikeizer-map-hover` CustomEvent mechanism (CARD-0082/CARD-0110) — hovering any one of the three highlights the same moment everywhere. Real added complexity: environmental readings aren't on the same index as `chart_series` (different source/cadence), so the new panel's hit-targets need their own per-GPS-point interpolated value (from decision 3) to share the same `data-index` contract the sync already relies on — not a new sync mechanism, but a real correlation step to get there.

**Open questions from the interview, resolved during Build 2026-08-24:**
- **Module shape:** extended `build_hike_chart.py` (not a new sibling module) with `build_env_chart_html()`/`build_env_chart_script()` — reused the existing SVG geometry helpers, hit-target pattern, and CARD-0194 item 4's just-shipped expand/modal markup directly.
- **Click-to-expand:** yes, the new panel gets its own expand button/modal, same DOM-relocation pattern, its own `{chart_id}-modal-*` ids so it doesn't collide with the Elevation/Speed chart's.
- **Correlation step location:** `fetch_hike_data.py`, inside `build_chart_series()` itself (new `_correlate_environmental_series()` helper, called once per session) — every chart point gets `temp_f`/`humidity_pct`/`pressure_hpa`/`uv_index` added directly onto the same shared `chart_series` list the Route Map and Elevation/Speed chart already read, so both templates get it automatically with no separate wiring, and the hover-sync `data-index` contract stays intact by construction.
- **CARD-0197 interaction:** not investigated further — different correlation problem (observations→GPS timing vs. this card's environmental-readings→distance-axis), no blocking dependency found.
- **Interpolation cap:** `ENV_INTERPOLATION_MAX_GAP_SEC = 900` (15 min) — wider than `interpolate_position()`'s 600s GPS-to-event cap, sized for Environmental Data's coarser ~2-min native cadence (a routine single missed reading is already a ~240s gap; 900s clears that comfortably without also bridging a real multi-session gap, which starts at 600s by `_gps_sessions`' own threshold).

**Built 2026-08-24:**
- `fetch_hike_data.py`: `_correlate_environmental_series(chart_ts_list, env_rows, max_gap_sec)` — linear interpolation between the nearest real reading before/after each chart timestamp, per field independently (a field missing on one side falls back to the other alone within the cap; missing entirely or too far on both sides yields `None`, so the chart draws no line through that stretch). `build_chart_series()` now takes an `env_rows` parameter and adds the 4 interpolated fields to every point it emits.
- `build_hike_chart.py`: `ENV_CHART_MODES` (the two preset pairings), `build_env_chart_html()` (precomputes both pairings' full SVG geometry — gridlines, dual-axis labels, lines split at `session_break` same as the elevation chart, hit-targets — as two sibling `<g class="env-mode-group">`, one hidden via inline `style="display:none"`), `build_env_chart_script()` (hover wiring identical in shape to the existing chart's, plus `setMode()` for the toggle, plus the same click-to-expand JS). The **existing** `build_chart_script()` (elevation/speed chart) gained one addition: a listener for `hikeizer-chart-hover`/`-unhover` (previously only listened for `hikeizer-map-hover`) so it also reacts when the new env panel is hovered — true three-way sync, all three widgets now listen to and dispatch the same two event names.
- `templating.py`: new `--chart-temp`/`--chart-humidity`/`--chart-pressure`/`--chart-uv` CSS tokens (light + dark), `.line-*`/`.hover-dot.*`/`.tt-metric.*` color rules, `.chart-toggle`/`.chart-toggle-btn` styling; `env_chart_html`/`env_chart_section` computed alongside the existing `chart_html` and placed right after the Environmental Data Tracking table. Also fixed a real pre-existing gap found while working this card: **`data_summary_rows()` never included Pressure at all** (Joseph caught this directly: "Pressure is not shown in the Environmental Data Tracking table") — added it, and fixed the `has_env_data` omit-when-empty gate to check `pressure_hpa` too (it previously would have wrongly omitted the whole table on a hike with pressure data but nothing else).
- `html-template.html` + `SKILL.md`: same CSS tokens/rules ported, new `{{ENVIRONMENTAL_DATA_CHART}}` placeholder section added right after the Environmental Data Tracking table, `SKILL.md` documents calling `build_hike_chart.build_env_chart_html(hike_data['chart_series'])` to fill it — same "splice verbatim, don't hand-author" convention as `{{ROUTE_MAP}}`/`{{ELEVATION_SPEED_CHART}}`. SKILL.md's Environmental Data Tracking table instructions also updated to include Pressure, matching the `templating.py` fix.
- `python -m py_compile` clean on all three Python files.

**Verified against real production data, 2026-08-24 — not just synthetic.** Unit-tested `_correlate_environmental_series()` standalone first (interpolation between bracketing readings, nearest-side fallback near the edges, `None` when a gap exceeds the cap on both sides — all confirmed with synthetic timestamps). Then re-ran the **updated** `fetch_hike_data.py` against the real 2026-08-22 hike's exact persisted query window (`2026-08-22T12:37:22Z`–`15:58:30Z`, from that hike's own `hike_data.json`) inside the deployed orchestrator container — all 80 downsampled chart points came back with real correlated values (e.g. one real point: `temp_f: 97.0, humidity_pct: 28.5, pressure_hpa: 930.2, uv_index: 0.4`, timestamps/coordinates matching the real hike). Fed that through the updated `templating.render_html()` in the same container: confirmed both `env-mode-group` elements present, `Environmental Data Chart` heading present, `line-temp`/`line-pressure` both present, HTML brace-balanced (196/196) and all 3 expected `<script>` tags balanced (map/elevation-chart/env-chart plus the CARD-0194 manual-edit script — no map script since no Thunderforest key was passed in this scratch call). All output written to `/tmp` scratch paths inside the container only — no live/served file touched, cleaned up after.

**Deployed to the M8**, orchestrator rebuilt twice (once for the initial implementation, once for an `--accent-ink` color-token fix caught on review), healthcheck confirmed `healthy` both times.

**Real bug found and fixed during the live-browser click-through, 2026-08-24 — the expand modal for the Elevation & Speed chart showed the Route Map rendering in the foreground, on top of the modal.** Root-caused precisely, not guessed: `.hike-map` (the Route Map's own inline container) had no `position`/`isolation` CSS of its own, so Leaflet's internal pane z-indexes (tiles 200, markers 600, popups 700, controls up to 1000 — `vendor/leaflet/leaflet.css`) were compared directly against the page's root stacking context, including the *chart's* modal backdrop (`z-index: 20`). Since 200-1000 > 20, the inline Route Map rendered above a *different* element's modal. The Route Map's own modal never hit this, because CARD-0082/CARD-0147 physically relocate that same Leaflet DOM node into the modal on open — nothing is left on the page to leak through in that case. **Fix:** `isolation: isolate` added to `.hike-map` in both `templating.py` and `html-template.html`, containing Leaflet's internal z-indexes to their own local stacking context so they can never outrank anything elsewhere on the page.

**Live-browser verified, not just structurally, 2026-08-24** — the recurring "not yet clicked in a live browser" gap on several of this project's hike-izer cards is closed here for real:
- **Isolation fix confirmed via `document.elementFromPoint()`** at the Route Map's exact screen position with the chart modal open: before the fix this would have hit a Leaflet pane element; after the fix it correctly hits an element inside `.map-modal-backdrop` (`topIsInModal: true`, `topIsLeafletPane: false`).
- **Three-way hover-sync confirmed real, not just wired** — dispatched real `mouseenter` events on the Environmental Data chart's own hit-targets (`window.dispatchEvent`, not `document`, matching the actual code path) and confirmed the Route Map's `.route-highlight` marker's SVG `d` attribute genuinely changes position between two different hovered indices, proving the Route Map really does track the Environmental Data chart's hover location, answering Joseph's direct question about this.
- Both fixes/checks run against the real live `2026-08-24_hike-summary.html` on the public site, not a scratch copy.

**Three follow-on layout changes, same session, all Joseph's calls, iterated live:**
1. **Environmental Data chart moved to right after Elevation & Speed** (was after the Environmental Data Tracking table, further down) — "so the location of the data points can be easily seen on the Route Map" without scrolling. The Environmental Data Tracking *table* stays where it was; only the chart moved.
2. **Heading renamed "Environmental Data Chart" → "Environmental Data."**
3. **Weather Forecast at Hike Start section repositioned twice, landing between the hero stat row and Route Map** — first moved above the hero stat row, then corrected to its final position (stat row → Weather Forecast → Route Map) per Joseph's follow-up correction.

All four changes applied to both `templating.py` and `html-template.html` (`.claude/skills/hike-izer/SKILL.md` updated to match), deployed to the M8, and confirmed live via a fresh `grep` of the real page's `<h2>` sequence: Weather Forecast → Route Map → Elevation and Speed → Environmental Data → Environmental Data Tracking → Sun Position → ...

**Fourth follow-on, same session: Environmental Data stacked in the same grid column as Elevation & Speed, same size, not just adjacent in markup order** (Joseph's call). `.hike-visuals` is a 2-column CSS grid (Route Map | Elevation & Speed); Environmental Data now joins Elevation & Speed inside a new `.hike-visuals-col` flex wrapper occupying that same second column, instead of sitting as its own full-width section below the grid. New `.hike-visuals-col { display: flex; flex-direction: column; gap: 1.25rem; }` in both `templating.py` and `html-template.html`. "Same size" required no extra sizing logic — both charts' SVGs already use identical `viewBox`+`preserveAspectRatio` geometry (`build_hike_chart.py` reuses the same helpers for both), so matching column width alone makes them render at matching size. `env_chart_section` (the old standalone full-width variant) removed from `templating.py`, replaced by `env_chart_part` folded directly into `hike_visuals_section`'s own assembly.

**Verified with real geometry in a live browser, not just DOM structure** — the screenshot tool hit its usual recurring flakiness this session (same known issue several other hike-izer cards have hit), so verified via `getBoundingClientRect()` on the real live page instead: Elevation & Speed chart-card at `x:576, y:588, w:338, h:209`; Environmental Data chart-card at `x:576, y:893, w:338, h:216` — identical `x`/width (same column, same size), non-overlapping `y` (genuinely stacked), the small 7px height difference fully accounted for by the env chart's own mode-toggle buttons (Temp+Humidity / Pressure+UV) that the elevation/speed chart doesn't have. Also re-confirmed the Environmental Data chart's own expand-to-modal still works correctly after the added nesting (real click, modal opened, real SVG with all 4 line elements present inside it) — no regression from the extra wrapper div.

**Fifth follow-on, same session: Route Map vertically centered against the stacked column, desktop only** (Joseph's call — "that would make the Route Map easy to see for each chart," and "on mobile... that extra centering space isn't necessary"). Since Environmental Data now shares Elevation & Speed's column, that column is taller than Route Map's own card, leaving dead space below the map when both align to the row's top. Changed `.hike-visuals`'s `align-items: start` → `align-items: center`, in both `templating.py` and `html-template.html` — a one-line value change, since the rule was already correctly scoped inside the existing `@media (min-width: 52rem)` desktop breakpoint (the same block that turns the grid 2-column at all), so no separate mobile-exclusion logic was needed: on mobile the grid is single-column with nothing to center against, by construction.

**Desktop centering verified with real geometry, live:** `getBoundingClientRect()` on the real page shows Route Map's card at `y:614, h:394` inside a combined-column height of `h:595` (`y:514`–`1109`) — 100px of space above the map, 101px below, essentially exact centering. **Mobile confirmed on a real phone, 2026-08-24 (Joseph)** — "Looks fine on my phone." Closes the one gap this card's own automated tooling couldn't reach that session (`resize_window` reported success but never actually changed the tab's `innerWidth`, a tool limitation, not a page bug) — a real device is a stronger check than that emulation would have been anyway.

**Done when:** ~~the new panel renders on a real hike page with real Environmental Data~~ — met. ~~the legend toggle correctly switches between both pairings~~ — structurally confirmed; not separately re-tested live this session (no reason to suspect a regression, untouched by this session's fixes). ~~a real gap in sensor data is confirmed to interpolate~~ — met via unit test. ~~hovering the new panel correctly syncs the Route Map and existing chart's highlight~~ — **met, live-verified above.** ~~both templates render it identically~~ — met. **All items closed**, with the one honest caveat above (mobile centering-absence verified by CSS construction, not an actual narrow-viewport screenshot).

**Related:** CARD-0110 (the Elevation & Speed chart this extends), CARD-0082 (Route Map, the hover-sync partner — and the source of the `isolation` bug this session found and fixed), CARD-0133 (`interpolate_position()`, the interpolation-with-cap precedent this reuses), CARD-0194 item 4 (the chart-expand feature this reused directly, and whose z-index interaction with the Route Map went unnoticed until now), CARD-0197 (GPS-correlation-timing instrumentation — checked, no blocking interaction found), CARD-0207 (Battery Discharge Rate, the sibling stat whose own page-order/label changes rode along this same session), `components/hike-izer/build_hike_chart.py`, `components/hike-izer/fetch_hike_data.py`, `components/hike-izer-orchestrator/templating.py`, `components/hike-izer/html-template.html`, `.claude/skills/hike-izer/SKILL.md`.

---

### CARD-0202 · [idea] [hiking-monitor] Real solar_v sensing — wire up the ADC divider CARD-0017 designed but never built
**Status:** Defer

**Raised 2026-08-23 14:27 MST (Joseph), broken out from CARD-0200's "proper fix" note.** CARD-0200 fixed the low-battery cutoff's immediate bug (gating it on `dock_detect`, which solar shares with USB, rather than real charging state) with a cheap firmware-only patch. The properly-designed fix — a real `solar_v` ADC reading compared against `battery_v` (`solar_v > battery_v + ~0.3V` = actually charging) — was already fully specified by **CARD-0017** (marked Done, 2026-06-15), but only the Sheets/Apps Script half of that card was ever built. Confirmed by grep: no `solar_v` sensor exists anywhere in `hiking-monitor.yaml`, and `power-system.md` documents no voltage divider on the solar panel's own output — only `battery_v` (via `BAT+`) and the digital-ish `dock_detect` divider exist today.

**Confirmed, per Joseph's question this same session: yes, this is a version-2/perfboard-rewiring item, not a firmware-only fix.** Populating `solar_v` for real requires a *new* physical voltage divider circuit — tapping the panel's raw output (or the TP4056 `IN+` line) through a new resistor pair into a spare ADC-capable GPIO — which means opening the already-assembled, field-proven perfboard. That's the same category of cost CARD-0070 (LDO swap) and CARD-0201 (sleep rearchitecture, if it turns out to need rewiring) are being deliberately kept out of this build pass for. Filed in **Defer**, matching CARD-0070's precedent, not Backlog — this isn't next-in-line work, it's a deliberately-parked future hardware pass.

**Scope, if/when revisited:** design and add a new resistor-divider circuit from the solar panel's `IN+` line to a spare ADC GPIO (GPIO33 or another unused pin — check `ESP32-project-pins.md` for what's actually free), add a corresponding `sensor: platform: adc` block in `hiking-monitor.yaml` publishing `solar_v`, and replace CARD-0200's `in_field_mode`-gated cutoff condition with the real `solar_v > battery_v + 0.3V` check CARD-0017 already designed. Natural pairing with CARD-0070 and/or CARD-0201 if either of those also ends up requiring the perfboard opened — one physical rework session covering all pending hardware changes, rather than three separate teardowns.

**Related:** CARD-0200 (the cheap patch this would properly replace), CARD-0017 (the schema/comparison-logic design this reuses, marked Done but only half-built), CARD-0070 (the existing "v2 rebuild" precedent this follows), CARD-0201 (possible pairing if it also needs rewiring), `components/hiking-monitor/power-system.md`, `components/hiking-monitor/ESP32-project-pins.md`.

---

### CARD-0201 · [enhancement] [hiking-monitor] True deep-sleep-between-samples in field mode
**Status:** Planning

**Moved to Planning 2026-08-27, explicitly sequenced behind today's other changes.** Joseph's call: real-hike verification of today's CARD-0217 (reset-reason fix, WiFi-disable-during-field-mode fix) and CARD-0045 (switch-off-required-before-WiFi fix) comes first — see those cards' own results on a future hike before starting this one's firmware rearchitecture.

**WiFi is a confirmed non-issue for this card, settled 2026-08-27 — not a design consideration, not even a wrinkle.** Earlier same-day discussion first raised it as something CARD-0201 would need to handle on every wake cycle (deep-sleep wake = full reboot, so WiFi's own setup runs again each time) — Joseph correctly pointed out this doesn't apply: field mode never touches WiFi at all now, regardless of whether the chip is continuously awake (today) or truly deep-sleeping between samples (this card) — that's already fully resolved by CARD-0045/CARD-0217 and applies identically either way. Nothing for this card to design around.

**Pressure-trend buffer / RTC memory, explained in more detail 2026-08-27 (for whoever picks this up at Build):** `pressure_buf` is a 16-slot circular array (`hiking-monitor.yaml`) holding one pressure reading per 2-min cycle, compared against the oldest slot (~32 min back) each cycle to compute the `pressure_trend` indicator ("^"/"v"/"=>") shown on the display. It lives in plain SRAM, which deep sleep wipes on every wake (a wake is architecturally a full reboot) — without a fix, the trend would break every single cycle, not occasionally. The fix is NOT the same mechanism CARD-0199 used (`restore_value: true`, which ESPHome backs with flash/NVS storage — fine for something written once per hike, a poor fit for something rewritten every 2 minutes indefinitely, given flash write-endurance limits). This needs the ESP32's actual RTC memory domain instead — plain SRAM that stays powered through deep sleep specifically (unlike main SRAM), no wear-out concern, but doesn't survive a true power loss (fine, since it only needs to survive deep sleep). ESPHome's own `globals:` YAML doesn't expose RTC placement directly — likely needs a raw C++ global declared with the `RTC_DATA_ATTR` attribute (same general pattern `hiking_logger.h` already uses for its own plain globals), outside ESPHome's declarative `globals:` mechanism.

**Raised 2026-08-23 14:27 MST (Joseph), broken out from CARD-0196 item 1.** CARD-0196 originally bundled four hike-endurance items together; this is the one with real feasibility risk and firmware-rearchitecture scope, split out so the other three (display throttle, solar habit note, LiPo fit check) aren't blocked on it and CARD-0196 can close out once those are verified.

**Original framing (from the 2026-08-23 battery-usage analysis and interview, carried over verbatim):** during field mode the ESP32 never actually sleeps between samples — the 2-minute read/log cycle is a plain `interval: 2min` timer (`hiking-monitor.yaml`) with the whole chip continuously awake for the entire hike, projecting to roughly **3h40m of continuous field-mode endurance per full charge** before the low-battery cutoff fires. Real ESP32 hardware deep sleep (~10µA) between the 2-minute reads instead of staying continuously awake is the single largest available lever — Joseph's framing: "if sleep mode can be implemented to help without rewiring, perhaps." Believed feasible as a pure firmware change: unlike CARD-0070's peripheral-gating design (which needed a new P-FET switch physically wired between the 3.3V rail and the sensors), a wake-read-sleep cycle can use the sensors exactly as continuously wired today — no new hardware, just the ESP32 itself actually sleeping instead of idling.

**Known technical considerations to work through at Planning/Build, not yet resolved:**
- SPIFFS (`hike_logger.h`) needs to remount on every wake — currently mounted once at boot and assumed to stay mounted.
- The pressure-trend circular buffer (`id(pressure_buf)`, `hiking-monitor.yaml`) lives in plain RAM, which real deep sleep wipes — needs to move to RTC memory (`RTC_DATA_ATTR`) to survive across sleep cycles, or the 30-minute trend comparison breaks every wake.
- Sensor settle time after waking (BME280/LTR-390 need a brief moment post-wake before a valid read) needs to be accounted for in the wake sequence.
- Wake source: a timed RTC wake (ESP32 `esp_sleep_enable_timer_wakeup`), not the existing dock-detect/slide-switch external wake sources (those stay as-is, unrelated).
- **If this genuinely can't be done without rewiring once actually scoped, it's out — Joseph explicitly does not want the perfboard disturbed for this**, unlike CARD-0070 (and now CARD-0202) which he's deliberately treating as future "v2" rebuild items, not something to revisit now.

**Verification approach — bench-measurable, unlike CARD-0195's diagnostic card.** The actual current-draw improvement can be measured directly on the bench the same way CARD-0026 measured the original boost-module baseline (multimeter in series on the battery lead). **CARD-0195 should land and be verified before this card's own bench test**, since this card's own done-when criteria depend on it — CARD-0195's skip-reason logging is the tool needed to confirm "no NaN reads or lost samples introduced by waking too fast" rather than just assuming it from inspection.

**Done when:** built and bench-measured to show a real reduction in average current during a simulated multi-cycle field-mode run, and sensor data integrity is confirmed intact across wake/sleep transitions using CARD-0195's skip-reason logging (not just inspection).

**Related:** CARD-0196 (the parent card this was broken out of, now covering the lower-risk items), CARD-0070 and CARD-0202 (the two other "v2 hardware pass" items this could potentially share a perfboard-opening session with, if it turns out to need one), CARD-0026 (bench measurement methodology), CARD-0195 (diagnostic prerequisite for verification), `components/hiking-monitor/hiking-monitor.yaml`, `components/hiking-monitor/hiking_logger.h`.

---

### CARD-0203 · [enhancement] [hiking-monitor] Longer-but-same-thickness LiPo — fit confirmed, candidate cell out of stock
**Status:** Backlog

**Raised 2026-08-23 14:27 MST (Joseph), broken out from CARD-0196 item 4** (and separately again from CARD-0196 immediately after CARD-0201 was split out) — this is physical research/procurement work, not firmware, and closes on a different timeline (Joseph's hands on the enclosure) than the firmware cards it was originally bundled with.

**Goal:** a physically longer 3.7V LiPo (same thickness as the current EEMB 1100mAh cell) might fit the existing 3D-printed enclosure (CARD-0009) without a redesign, if there's clearance in an unused dimension — more capacity without touching the boost-converter inefficiency CARD-0070 would fix.

**Sourcing done, 2026-08-23 14:27 MST — real candidate identified:** [EEMB LP603466](https://eemb.store/products/lp603466-3-7v-1400mah), 3.7V 1400mAh, 6.5×34.5×68mm, JST connector, PCM-protected (overcharge/overdischarge/overcurrent/short-circuit), UL-certified and UN 38.3 compliant — same safety profile as the current cell. Verified against the current cell's own real dimensions, [EEMB LP603449](https://eemb.store/products/lp603449) at 6.3×34.5×50mm/1100mAh: essentially identical thickness (6.5 vs 6.3mm — within normal manufacturing tolerance) and identical width (34.5mm both), **18mm longer for +27% capacity.** Same manufacturer/product family as the currently-deployed cell (`hiking-monitor-claude-code-instructions.md`, `JCTsh-hiking-monitor-phase1.md`), so no new supplier-trust question.

**Fit confirmed, 2026-08-23 (Joseph) — the 68mm length fits the physical enclosure.**

**Candidate out of stock, 2026-08-23 (Joseph, confirmed on Amazon).** The sourced LP603466 is not currently purchasable.

**Done when:** a purchasable cell matching the confirmed-fitting envelope (~6.3-6.5mm thick, 34.5mm wide, up to 68mm long) is identified and ordered.

**Related:** CARD-0196 (the parent card this was broken out of), CARD-0009 (enclosure build — and the undocumented-internal-dimensions gap this card has to work around), CARD-0017 (unrelated schema card, no connection beyond both concerning the LiPo/charging system), `components/hiking-monitor/power-system.md`, `components/hiking-monitor/hiking-monitor-enclosure-plan.md`.

---

### CARD-0200 · [bug] [hiking-monitor] Low-battery safety cutoff silently disabled by solar (shares dock-detect signal with USB) — cheap fix built and flashed — RESOLVED 2026-08-24
**Status:** Done

**Raised 2026-08-23 14:16 MST (Joseph), found during a discussion of how connecting the SUNYIMA solar panel affects hiking-monitor's firmware.** The 3.4V low-battery cutoff (`hiking-monitor.yaml`, the 2-min interval lambda) was gated on `!id(dock_detect).state` — but solar wires into the same `IN+`/`IN-` pads as USB (`power-system.md:17,24-25,138-139`), so `dock_detect` goes HIGH identically whether it's a stable USB charger or a ~55-80mA solar panel in variable field conditions. Net effect: **connecting solar while actively hiking silently disables the one safety net protecting the LiPo from over-discharge**, with no check on whether the panel is actually outpacing drain.

**Two fix paths identified, interviewed 2026-08-23:**
1. **Cheap patch (built this session):** gate the cutoff on `in_field_mode` (switch on, MQTT not connected — the same bool CARD-0196's display throttle already computes) instead of `dock_detect`. Pure firmware, no new wiring — the safety net now stays active whenever genuinely out hiking, regardless of whether solar happens to be connected.
2. **Proper fix (not built — needs new hardware):** a real `solar_v` ADC reading compared against `battery_v` (`solar_v > battery_v + ~0.3V` = actually charging), letting the cutoff make a genuinely informed decision instead of treating "something's plugged in" as a proxy for "definitely safe." **CARD-0017 (marked Done, 2026-06-15) already designed this exact schema field and the comparison logic** — but only the Sheets/Apps Script half was ever built. Confirmed by grep: no `solar_v` sensor exists anywhere in `hiking-monitor.yaml`, and `power-system.md` documents no voltage divider on the panel's own output (only `battery_v` via `BAT+`, and the digital-ish `dock_detect` divider) — so populating it for real would mean adding a new physical divider circuit, the exact kind of perfboard rework this pass is explicitly avoiding (same reasoning CARD-0196 item 1 and CARD-0070 already apply).

**Decision:** ship the cheap patch now (low risk, built and config-validated); leave the proper `solar_v` fix as a future hardware-pass item, most naturally grouped with CARD-0070's "v2 rebuild" rather than reopening CARD-0017 today.

**Built and config-validated, 2026-08-23 14:16 MST.** `esphome config` clean against the synced `C:\esphome\hiking-monitor\` copy.

**Flashed 2026-08-24 (OTA), same broader hiking-monitor update that also carried CARD-0195/CARD-0196/CARD-0199** (all four live in the same `hiking-monitor.yaml`, confirmed via a real post-flash reconnect on the log dashboard). **Closed without a real low-battery firing test** — this is a simple boolean-condition swap (`dock_detect` → `in_field_mode`, the same flag CARD-0196's display throttle already computes and which ran correctly all through the real 2026-08-24 hike), and deliberately draining a real LiPo down to the 3.4V cutoff just to watch it fire isn't worth the real battery wear/risk for a low-risk patch like this. Genuine behavioral confirmation will come the first time the device is ever actually near cutoff while solar/USB happens to be connected — nothing to force in the meantime.

**Compounding risk worth naming (not part of this card's fix, cross-referenced on CARD-0045 too):** if CARD-0045's suspected stuck-WiFi-reconnect-loop bug ever fires while solar is connected mid-hike, this cutoff being disabled the whole time meant there was previously *no* backstop against draining the battery to nothing. This fix closes that half of the failure chain; CARD-0045 itself (unbounded WiFi retry) is still open and unfixed.

**Related:** CARD-0017 (the schema this fix reuses conceptually but doesn't implement in hardware), CARD-0045 (the compounding risk noted above), CARD-0196 (the sibling `in_field_mode` bool this reuses, from the same file's display-throttle logic), CARD-0070 (where the proper hardware fix would naturally land), `components/hiking-monitor/hiking-monitor.yaml`, `components/hiking-monitor/power-system.md`.

---

### CARD-0199 · [enhancement] [hiking-monitor] E-ink display shows Connected/Uploading/Upload-complete-with-duration during post-hike sync — RESOLVED 2026-08-27
**Status:** Done

**Closing confirmation, 2026-08-27.** Today's hike (2026-08-27) was exactly the "hike ends with buffered data → device sleeps/stays awake → gets docked later" scenario this card's last open item was waiting on — Joseph directly confirmed seeing the full 3-state sequence (Connected → Uploading → Done, with duration) on the real device display when docking at 8:56 AM after today's hike. The `restore_value: true` fix (2026-08-24) survives the real gap between hike-end and docking, as intended.

**Raised 2026-08-23 13:39 MST (Joseph).** Currently, when the device reconnects to WiFi after a hike and replays its buffered flash log, the e-ink display shows nothing about that process — it just keeps showing whatever it last displayed (stale field-mode readings, or "initializing") straight through connect and replay, then silently jumps to normal readings once done, with no visibility into what happened or how long it took.

**Interviewed 2026-08-23 — one real design fork, resolved:** how long should the final "upload complete" message stay on screen. **Chosen: until switch-on or dock-removed** (not a fixed timer) — matches upload mode's own existing idle-until-touched behavior rather than adding a new time-based mechanism.

**Design:** a 3-state sequence (`upload_display_state` global: 0=normal, 1=Connected, 2=Uploading, 3=Done), gated behind `hike_log_has_data()` being true at connect time — a plain reconnect with nothing buffered leaves the display untouched, since there's nothing to report. Hooks directly into the existing `mqtt.on_connect:` replay lambda (`hiking-monitor.yaml`) rather than adding a parallel code path:
1. **Connected** — set the moment there's confirmed data to replay, held visible ~1.5s (`delay(1500)` in the lambda) before the sequence moves on, so it's actually readable rather than flashing past.
2. **Uploading** — set right before `hike_log_replay_stream()` starts; `upload_start_ms = millis()` captured here.
3. **Done** — set right after replay completes and the flash log is cleared; `upload_duration_ms = millis() - upload_start_ms` computed and shown as `"%.1fs"` (e.g. "8.2s").

**Display lambda** (`hiking-monitor.yaml`, `display:` block) gets three new early-return branches for these states, checked after the existing `low_battery_pending`/`deep_sleep_pending` checks (unchanged priority — a critical battery/sleep state still wins over an upload-status message) and before the normal live-reading branch.

**Reset points, per the interview decision above:** `slide_switch`'s `on_state` gained an `else` branch (switch turned ON — previously only handled switch-OFF) that clears `upload_display_state` back to 0. `dock_detect`'s `on_state` else-branch (USB removed) now unconditionally clears it too, not just inside the existing "switch also off → sleep" path — covers unplugging while the switch is still on, which the prior code didn't touch at all.

**Verified:** `esphome config` — "Configuration is valid!" against the synced `C:\esphome\hiking-monitor\` copy. **Not yet flashed or live-tested** — no physical device access from this session. First real verification has to be a live dock/reconnect cycle confirming the three states actually appear in sequence and the elapsed time is plausible, plus confirming the reset paths (switch-on, dock-removed) actually clear the message rather than leaving it stuck.

**Real gap found and fixed after the first live hike this firmware ran on, 2026-08-24.** Flashed and exercised for real on the 2026-08-24 hike ("Boulder Pass Loop") — Joseph checked the display afterward and it showed normal live readings, not the expected "Upload complete" screen, despite the switch being off and USB still connected (neither documented reset trigger had fired).

**Root cause, traced through the actual firmware code, not guessed:** `upload_display_state`/`upload_duration_ms` were declared `restore_value: false` — plain RAM globals reset to their `initial_value` on every boot, **including waking from `deep_sleep.enter`**, which is a full reboot on next wake, not a low-power idle. The device always deep-sleeps between a hike ending (switch off, confirmed via the log: "Entering deep sleep" at 07:59:37 MST) and getting docked (woke again at 08:00:25 when USB was plugged in) — so `upload_display_state` silently reset from 3 (Done) back to 0 purely from that normal sleep/wake cycle, with neither switch-on nor dock-removed ever firing. The next home-mode 2-min interval tick then called `id(hiking_display).update()` unconditionally (the `!in_field_mode` branch, no check of `upload_display_state`) — with the global now back at 0, the display lambda fell straight through to the normal live-reading render, overwriting the still-correct e-ink image. This made the "stays until switch-on or dock-removed" design promise false in practice for every hike, since the device always sleeps in between.

**Also corrected, same investigation:** the earlier estimate of "Uploading" being sub-second (read off the log dashboard's 1-second-resolution timestamps) was wrong — `hike_log_replay_stream()`'s per-line `delay(50)` means a real ~2.1s+ for a typical ~40-reading hike, not sub-second. Doesn't change the fix, just corrects the record.

**Fix:** `upload_display_state` and `upload_duration_ms` changed to `restore_value: true` (`upload_start_ms` left `false` — only used transiently to compute the duration, doesn't need to survive sleep). ESPHome backs `restore_value: true` with flash-persisted NVS storage, which survives deep sleep/reboot — a few writes per hike is negligible flash wear. Now only the two documented triggers (switch-on, dock-removed) actually clear it, matching the original design intent for the first time. `esphome config` re-validated clean against the synced `C:\esphome\hiking-monitor\` copy.

**Flashed 2026-08-24 09:17 MST, OTA** (`esphome upload --device 192.168.1.161`, no physical USB access needed — the device was already docked and online) — "OTA successful," confirmed live by a real reconnect (`Hiking monitor online - ESPHome 2026.4.5`) on the log dashboard immediately after.

**Still needed to fully close this card:** a genuine repeat of tonight's exact scenario (hike ends with data buffered → device sleeps → gets docked later) to confirm Done now actually survives that cycle — nothing was buffered at flash time (already replayed and cleared earlier tonight), so this flash only proves the firmware boots clean, not yet that the fix works end-to-end. That confirmation has to wait for the next real hike.

**Related:** `components/hiking-monitor/hiking-monitor.yaml` (`mqtt.on_connect:`, `display:` lambda, `slide_switch`/`dock_detect` `on_state`), CARD-0196 (the sibling battery-endurance card touching the same display component's refresh *frequency* — a different concern, no overlap in the actual code touched).

---

### CARD-0198 · [bug] [air-quality-monitor] Boot sequence resumes SEN55 Measurement mode on a blind fixed delay instead of an actual connectivity check — base platform fixed and verified; SEN55+battery reliability still unresolved
**Status:** Build

**Raised 2026-08-23 12:01 MST (Joseph), asked for a full comparative boot-sequence analysis of hiking-monitor vs. air-quality-monitor** (steps, timing, sync vs. async, and how to control which subsystems come up first) **"while I'm away"** — worked fully autonomously per that instruction, including writing and validating a concrete code fix rather than stopping at analysis alone (deploy/flash left for Joseph, no physical device access from this session).

**ESPHome boot model (Arduino framework) — the mechanics behind everything below.** Boot has two phases. (1) `setup()`: every component's `setup()` runs once, synchronously, in descending `setup_priority` order (bus/hardware ~800-1000, sensors ~600, WiFi ~250, MQTT/OTA lower) — each must return before the next starts, but WiFi's `setup()` only *starts* its connection state machine, it doesn't block waiting for association. `on_boot:` triggers are themselves priority-ordered components — the YAML `priority:` value *is* a `setup_priority` on that same number line, so multiple `on_boot:` blocks (and where they fall relative to WiFi/MQTT's own setup) are ordered by it directly. (2) `loop()`: runs forever after setup completes — WiFi association, MQTT connect/TLS, and NTP sync all happen here as async state machines. A `delay:` inside an automation *yields* back to this loop rather than halting it, so other components keep running while a boot script "waits." Neither device's `on_boot` script literally blocks WiFi from connecting — what varies is whether the script's actions are *paced against* what WiFi/MQTT are actually doing, or run blind to it.

**hiking-monitor boot sequence:**

| Priority | Step | Sync/Async |
|---|---|---|
| ~1000 (implicit) | I2C, SPI bus init | Sync |
| 600.0 (`on_boot`) | `hike_log_begin()` — mount SPIFFS | Sync |
| ~600→250 (implicit) | Sensor components register (BME280, LTR-390, ADC, uptime, wifi_signal) | Sync |
| ~250 (implicit) | WiFi `setup()` — connection attempt starts here | Async begins |
| lower (implicit) | MQTT, OTA, display, deep_sleep setup — each just *prepares*, no blocking wait for network | Sync (per-call) |
| **-100.0 (`on_boot`)** | Force-update display + all sensors, `delay: 10s`, force-update display again | Sync script, runs concurrently with WiFi/MQTT's own async connect |
| **-200.0 (`on_boot`)** | Decide: sleep now, or low-battery shutdown, based on switch/dock state | Sync script |
| (event-driven) | `mqtt.on_connect:` — publish online status, replay flash-buffered readings, check switch/dock state | Fully async/event-driven — fires whenever MQTT actually connects, however long that takes |
| (event-driven) | `interval: 2min` — read sensors, log to flash or MQTT depending on connection state | Async, forever |

Key property: hiking-monitor's "do something once we're actually online" logic lives entirely in `mqtt.on_connect:` — the correct, event-driven pattern. Nothing in its `on_boot:` blocks guesses when WiFi/MQTT will be ready.

**air-quality-monitor boot sequence:**

| Priority | Step | Sync/Async |
|---|---|---|
| ~1000 (implicit) | I2C bus init | Sync |
| ~600→250 (implicit) | Sensor components register (SEN55 — **auto-starts full Measurement mode, ~63mA, right here**, ADC, uptime, wifi_signal) | Sync |
| ~250 (implicit) | WiFi `setup()` — connection attempt starts here | Async begins |
| lower (implicit) | MQTT, OTA setup (prepare only) | Sync (per-call) |
| -100.0 (`on_boot`, step 1) | Reset-reason LED — solid red 3s if reset reason matches "brownout"/"glitch", else solid blue 1s | Sync |
| -100.0 (`on_boot`, step 2) | Force SEN55 into Idle mode (~2.6mA), overriding its own auto-started Measurement mode from setup() | Sync |
| -100.0 (`on_boot`, step 3) | Self-test LED blink sequence — 2× each of Blue/Red/Yellow/Green, ~300ms on/off | Sync, **fixed ~4.8s delay** |
| -100.0 (`on_boot`, step 4, pre-fix) | `delay: 1s`, then blindly resume SEN55 Measurement mode on the assumption WiFi association is done | Sync, **blind fixed delay — the bug** |
| -100.0 (`on_boot`, step 4, post-fix) | Bounded wait on `id(mqtt_client).is_connected()` (250ms poll, 30s cap) before resuming SEN55 Measurement mode | Sync script, but now paced against WiFi/MQTT's real async state instead of guessing |
| -100.0 (`on_boot`, step 5) | `delay: 2s` sensor settle, force-update SEN55 + battery_voltage | Sync, fixed 2s delay |
| -100.0 (`on_boot`, step 6) | Unbounded `while` loop blinking green until first valid PM2.5 reading — **no timeout**, can run minutes per its own comment | Sync, **unbounded wait** |
| -100.0 (`on_boot`, step 7) | Solid green 2s confirmation, `boot_sequence_done = true` | Sync, fixed 2s delay |
| -100.0 (`on_boot`, step 8) | Threshold-color LED demo — solid Yellow 3s, solid Red 3s (permanent visual self-check, not test-only) | Sync, **fixed ~6.5s delay** |
| (event-driven) | `mqtt.on_connect:` — publish online status only | Async |
| (event-driven) | `pm_2_5.on_value:` — threshold LED, gated by `boot_sequence_done` | Async |
| (event-driven) | `interval: 5min` heartbeat, `interval: 30s` bench-log | Async |

**Comparison:**

| | hiking-monitor | air-quality-monitor |
|---|---|---|
| `on_boot:` blocks | 3, split by purpose (early flash mount / late sensor-force / very-late sleep decision) | 1, doing everything (LED diagnostics + power-mode sequencing + sensor force + threshold demo) |
| Total on_boot duration | ~10s (one fixed delay) | ~20-25s fixed, *plus* an unbounded wait — could be minutes |
| "Wait for network" pattern | None needed — deferred entirely to `mqtt.on_connect:` | **Blind fixed delay**, inside `on_boot`, guessing WiFi is done |
| High-current peripheral awareness | N/A (BME280/LTR-390 draw is negligible) | Explicitly manages SEN55's ~63mA Measurement mode vs. WiFi's association spike — the one place this actually matters |
| Diagnostic self-instrumentation | None | Reset-reason LED + MQTT report (added 2026-08-21, mid-diagnosis) |

hiking-monitor's design is simpler because it has no high-current peripheral to sequence around. air-quality-monitor does, and that's exactly where the blind-delay guess lives — this is the concrete instance of "how do we manage boot order so basics come first" the rest of this card addresses.

**What's actually "amiss," confirmed against real log data, not just code inspection.** The 2026-08-21 bench session (Step 6→7 of CARD-0012) already added an undocumented mitigation directly in `air-quality-monitor.yaml` — never written back to CARD-0012 or the instructions doc, only discoverable by reading the YAML's own comments — for a suspected LDO current-limit brownout: SEN55's ~63mA Measurement-mode draw stacking on top of WiFi's association current spike, both drawn from the same 250mA-rated MCP1700 LDO. The mitigation forces SEN55 into ~2.6mA Idle mode through boot, waits a **fixed ~10 seconds** of LED self-test delays, then blindly resumes full Measurement mode on the assumption "WiFi association should be past" by then.

**Pulled the Pi's log buffer for the same session (`/mnt/jctsh-logs/state.json`, `component=air-quality-monitor`) and found the fixed-delay guess is empirically wrong under real conditions:** repeated `"reset reason: power-on event"` reconnects on 2026-08-21, several under 2 minutes apart (13:28:18, 13:37:37, 13:39:04, 13:57:52, 15:51:23 MST) — a boot-loop-shaped pattern, not isolated incidents — followed by the device going completely silent for the next ~27 hours (last entry 15:52:58 MST 08-21 until 18:49:22 MST 08-22, a single bare reconnect with nothing since). Battery-voltage heartbeats in the same window are bouncy (3.14–3.59V, non-monotonic) rather than smoothly trending, consistent with either rail sag from repeated brownout events or the ADC still reading the Step-4-era placeholder tap rather than a real battery (Step 7, LiPo/LDO connection, was "next" per CARD-0012's last update at that point) — noted as an open uncertainty, not resolved by this card.

**A second, independent gap found in the existing mitigation's own diagnostic code:** the boot-time RGB LED reset-reason indicator (red=brownout, blue=normal) only pattern-matches `"rownout"` / `"glitch"` in the reset-reason string. Every reset actually observed in the field logs above reports `"power-on event"` or `"software via esp_restart"` — **neither string trips the red-LED path**, so the one visual tool built specifically to catch this class of failure would have shown blue (normal) through the entire boot-loop episode. **Deliberately not widened to also match "power-on event"**, after considering it: this device's normal, expected operation includes being switched fully off (inline power switch) between hikes, so a legitimate power-on always reports the identical string — broadening the match would make the red LED fire on every ordinary cold start, not just real faults, defeating its purpose. No cheap fix for this half found; flagged as a known, accepted limitation rather than silently left unmentioned.

**Fix implemented and config-validated (`esphome config` — "Configuration is valid!"), NOT yet flashed to real hardware:**
- Replaced the fixed ~10s blind delay with a bounded wait on `id(mqtt_client).is_connected()` (`air-quality-monitor.yaml`, `esphome.on_boot`, priority -100.0 block) — polls every 250ms, capped at 30s so a device with no reachable network doesn't idle SEN55 forever. New global `boot_wait_start` (uint32_t, `millis()`-based) added to track the wait window.
- This removes the actual race condition (SEN55 resuming Measurement mode while WiFi/MQTT association is still genuinely in progress) rather than trying to out-guess its duration — directly answers Joseph's "how do we manage boot order so basics come up first" question for this specific collision.

**Explicitly not done by this card — left for a physically-present session:** flashing the fix to the real device (USB, per this component's own first-flash convention — OTA needs the device already reachable, which it currently is not per the 27-hour silence above), live verification that the boot-loop pattern actually stops, and resolving the battery-voltage-source ambiguity noted above (whether Step 7's real LiPo is connected yet). CARD-0012 (Step 7, still open) is the parent thread this ultimately feeds back into — this card exists separately because it's a distinct, evidence-driven bug investigation, not a Step 7 sub-task list item.

---

**Long physically-present session, 2026-08-24 12:00-15:40 MST — real progress on the base platform, SEN55+battery reliability still not solved.** Picked up exactly where the above left off: Joseph reported the device still wouldn't boot on battery and suspected a firmware change was involved.

**Real process bug found before any actual testing could happen:** `esphome upload` flashed a stale, already-compiled `firmware.bin` from 2026-08-21 20:57 UTC — three days old, predating even this card's own fix — rather than rebuilding from the edited YAML. Caught by comparing the build artifact's timestamp against the YAML's edit time (nothing in `esphome upload`'s own console output indicated a recompile happened). Every test result from before this was caught is against the *old*, pre-fix firmware, including the initial "still same result" report after the reorder fix below. Fixed by always running `esphome compile` explicitly before `esphome upload` for the rest of the session.

**Second unbounded wait found and fixed, same shape as this card's original fix:** the boot script's first-valid-PM2.5-reading wait loop (`air-quality-monitor.yaml`, immediately after the MQTT-wait block) had no timeout at all — a deliberate decision at the time (a connected, healthy sensor can take a while to produce a first reading, and a timeout would falsely declare success), but with SEN55 physically disconnected during isolation testing, `pm_2_5` never leaves NaN and the loop ran forever, blocking `boot_sequence_done` permanently. Bounded to 30s via a new `pm25_wait_start` global, same `millis()`-based pattern as `boot_wait_start`.

**Base platform (SEN55 disconnected) verified solid once the real fix was actually flashed:** 4 consecutive clean, single-attempt power cycles on battery, each confirmed via the Pi's log dashboard (`MQTT Connected.` → `Air quality monitor online` → real periodic sensor-log lines, no repeated connect/disconnect cycling). This part of the investigation is genuinely done.

**Reconnecting SEN55 reintroduced the original brownout-loop signature** (reset-reason LED flashes blue once then nothing further; onboard ESP32 power LED pulsing, matching the pre-capacitor symptom) — even with the real fix flashed. Tried reordering the SEN55-idle-override I2C command to run as the literal first `on_boot` action (ahead of the reset-reason LED check, minimizing the window SEN55 sits in full ~63mA Measurement mode before being forced to Idle) — **no change, identical failure.** Rules out that specific exposure-window timing theory.

**CARD-0205 (debug UART) picked up mid-investigation, and its design turned out to be wrong.** ESPHome's `logger:` component has no `tx_pin` option at all — confirmed by reading the installed package's own `logger/__init__.py` config schema directly rather than assuming. `hardware_uart: UART2` only selects a fixed ESP32 hardware UART peripheral; on the original ESP32 (Arduino framework) UART2's pins are hardwired to TX=GPIO17/RX=GPIO16, not remappable to the originally-planned GPIO27. Corrected in both `air-quality-monitor.yaml` and `wiring.md` — GPIO17 (confirmed unused) is what's actually wired: `GPIO17 → adapter RXD`, `GND → GND`. **The adapter link itself never produced a single byte of output across every test run** — including a clean side-by-side control test (adapter listening on one COM port, `esphome logs` over the ESP32's own onboard USB on another, both watching the identical boot event): the onboard channel showed full real ESP-IDF bootloader + app output, the external adapter showed nothing. That proves the external adapter/wiring has a real, separate fault, independent of the board's actual behavior — deprioritized rather than chased further given the time already sunk with zero data returned.

**Capacitor experimentation, inconclusive on its own:** a 220µF bulk cap across the ESP32's 3V3/GND pins fixed the SEN55-disconnected case reliably (4/4) but was inconsistent once SEN55 was reconnected (some clean boots, some multi-minute total failures). Swapped for a 4700µF cap (top of the on-hand assortment) — same inconsistent pattern with SEN55 connected. Capacitance size was not the deciding variable.

**Real electrical fault found and fixed, unrelated to the capacitor/current-spike theory:** systematic multimeter continuity testing (battery isolated, not live) found the original LiPo's JST connector had a genuine **intermittent internal short** — continuity between BAT+ and BAT- that came and went unpredictably, localized to the connector body itself (not a reseating/mating issue — nothing to reseat). This is a real LiPo-safety-adjacent finding, not just a signal fault. The original battery was disconnected and set aside (should not be reconnected, charged, or left unattended — consider it compromised); swapped for one of the two spare EEMB 1100mAh cells in Bag 7 (`jctsh-parts-inventory.md`). **Even after this fix, SEN55+battery reliability remained inconsistent** — confirming the connector fault was real but not the sole cause of tonight's erratic behavior.

**New, unresolved data point: one recovery boot logged reset reason `"other watchdogs"`** instead of the `"power-on event"` seen on every other boot all night — a genuine ESP32 task/interrupt watchdog reset (firmware hang forcibly recovered), not a brownout. Investigated by reading the installed ESPHome package's actual I2C driver (`i2c_bus_esp_idf.cpp`) and SEN55 component (`sen5x.cpp`) source rather than guessing: the I2C layer has a bounded ~100ms timeout per transaction via ESP-IDF's `i2c_master_execute_defined_operations()`, and SEN55's own `setup()` is non-blocking (deferred via `set_timeout()`, not a synchronous call) — both weaken, without fully ruling out, a "blocking I2C call" hang theory. **The actual mechanism behind this watchdog reset is not confirmed** — would need live serial output at the moment it happens, which the still-broken debug UART can't currently provide.

**Also corrected during this session:** an unconfirmed "oxidized breadboard contact" hypothesis from this card's own Step 4 history (2026-08-21) had been cited early in tonight's session as if it were established precedent. Joseph corrected this — it was never actually confirmed and was later disproven (swapping jumper wires and breadboard positions didn't resolve the symptom it was meant to explain). Corrected in place, see Step 4's own entry above.

**Current state, 2026-08-24 ~15:40 MST — not resolved, session paused here:**
- ✅ Base platform (ESP32 + WiFi + MQTT + LDO + battery, no SEN55) — solid, verified.
- ✅ **Once the device boots successfully, SEN55 reliably reports data — every time, regardless of power source.** This isn't a "SEN55 works on USB but not battery" split; SEN55 itself has never once been the problem in any test tonight. The only place power source matters is *whether boot succeeds at all*: on USB power, boot succeeds every time (though only tested in two windows — an initial ~7-minute run and a later ~3-minute `esphome logs` session, not a large sample and not stress-tested with rapid cycling). On battery power, boot only succeeds intermittently. So the real open question this card is chasing is squarely "why does boot itself sometimes fail on battery," not anything about SEN55's own reliability once running.
- ✅ One real, fixed hardware fault (battery connector) and two real, fixed firmware bugs (unbounded PM2.5 wait; stale-build flashing process gap).
- ❌ SEN55 + battery power — still unreliable, root cause not confirmed. Neither capacitor size, switch condition, nor the battery connector fault (now fixed) fully explains it. The `"other watchdogs"` reset reason is a live, unresolved lead.
- ⏸️ CARD-0205's debug UART — wired per corrected pinout, but the link itself doesn't work; needs its own fresh troubleshooting session (continuity-check the actual GPIO17/GND wires, confirm the adapter itself works via a known-good loopback test) before it can help with anything else.
- **Uncommitted at session end:** `components/air-quality-monitor/air-quality-monitor.yaml` (PM2.5-wait bound, on_boot reorder, logger UART2/GPIO17 fix), `components/air-quality-monitor/wiring.md` (debug UART pin correction, LDO diagram fix), `tos/kanban-board.md` (this update).

---

**Same session continued, 2026-08-24 ~16:30-17:40 MST — pivoted to a minimal incremental-build test strategy after the full-firmware A/B testing above got tangled in too many simultaneous variables (capacitor size, switch condition, battery connector, board swap, UART presence, battery depletion) to isolate anything cleanly. New approach, Joseph's idea: start from the simplest possible firmware and add one subsystem at a time, testing battery-power reliability at each stage before adding the next, until the addition that breaks things is found.**

**New scratch build:** `components/air-quality-monitor/minimal-test.yaml` (component name `aqm-minimal-test`, kept in the repo so this test sequence survives past one session — flash from `C:\esphome\air-quality-monitor\` same as the real component, copy this file there first). Not the real component firmware, purely diagnostic.

**Stage 0 (boot + LED blink only — no WiFi, no MQTT, no I2C, no SEN55, no UART):** first battery-power test was clean (3 green blinks, boot confirmed). But the *next* finding is the most important one of this whole session so far: **the device spontaneously reset twice more on its own, at genuine idle** — once about 15 seconds after a clean boot, once again a few minutes later — with nothing running except the RGB LED sitting off after its initial blink. No WiFi, no MQTT, no SEN55, no UART, essentially the lowest possible current draw this board can have. That rules out every "current spike from X" theory this whole investigation has chased (WiFi association, SEN55 Measurement mode, UART2 claiming GPIO16/17) as the *sole* explanation — something in the raw power delivery chain itself (switch, LDO, capacitor, or a connection) is unstable even at rest. This is a strong, standalone lead independent of everything tested before it.

**Stage 0b (added):** debug UART (`logger: hardware_uart: UART2`, same confirmed GPIO17/GND wiring as CARD-0205) plus an explicit `logger.log` line printing the ESP32's own reset reason as the very first `on_boot` action — built specifically to catch one of Stage 0's spontaneous resets in the act and read its real reset-reason string, instead of only inferring one happened from a repeated blink count.

**Debug UART capture status — a real, still-unresolved problem, distinct from CARD-0205's original GND finding.** Despite CARD-0205's GPIO17 pin-identity test passing cleanly (multimeter confirmed toggling, adapter's own RXD LED flashing in sync), **not a single byte of real UART data has been captured from this build, across many repeated attempts** — including immediately after physically reseating and continuity-checking the GPIO17/GND wires mid-session. Verified this isn't a tooling problem: re-ran the adapter's own loopback test (already proven earlier) and switched to the already-proven capture script rather than a newly-written one — still zero bytes. **Working theory:** a slow ~1Hz digital toggle (CARD-0205's pin-identity test) and real 115200-baud UART framing have very different tolerances for a marginal connection — a connection resistive/noisy enough to corrupt fast serial bit timing could still pass a slow on/off toggle test cleanly. **Next diagnostic step, not yet tried:** drop the baud rate (e.g., to 9600) on both the firmware's `logger:` config and the capture script — if a lower rate succeeds where 115200 has consistently failed, that confirms a signal-integrity issue rather than a hard connection break.

**Current state, 2026-08-24 ~17:40 MST:**
- Stage 0 (bare boot) — confirmed **not fully stable even at idle**. This is now the single most important open lead in the whole investigation; worth prioritizing over continuing to add stages (WiFi, MQTT, SEN55) until this is understood, since a firmware-complexity theory can't explain a reset with essentially no firmware doing anything.
- Stage 0b's debug UART — still not delivering captured log text despite confirmed pin/GND connectivity; baud-rate test is the next concrete step.
- Stages 1 (+WiFi), 2 (+MQTT), 3 (+I2C/SEN55) — **not yet built or reached.**
- Battery voltage has been trending down across the session (3.9V early, 3.11V most recent heartbeat) from hours of repeated power cycling — a real, simple confound worth controlling for (fresh/rested battery vs. depleted) before trusting any more A/B comparisons. USB charging via the TP4056 was started but not yet given time to meaningfully recover before this write-up.

**Concrete redesign written, 2026-08-25 — applies CARD-0213's new §2.14 points 9-10 to this device's actual power path.** `components/air-quality-monitor/power-system-redesign.md` (new, design only, not yet built): swaps the MCP1700 LDO (250mA, the part CARD-0198 found repeatedly marginal) for a Pololu D24V10F3 (3.3V, 1A buck/switching regulator, breakout-board form factor) — sized against a calculated ~450mA coincident peak (WiFi TX burst + SEN55's ~63mA + ESP32 baseline), giving the 2-3x headroom the new standard requires. Adds a 4.7µF ceramic alongside the existing 470µF electrolytic at the ESP32's 3V3/GND pins. Explicitly not a boost-then-buck design (the thing §2.14 point 7 actually warns against) — a single direct buck stage from raw battery voltage, chosen over another LDO specifically because a linear regulator's only response to a spike beyond its rating is to sag, while a switching regulator handles the same transient far more gracefully at a comparable hand-solderable form factor. Everything downstream of the 3V3 pin (SEN55, RGB LED, both dividers, debug UART) is unchanged — a point-load swap, not a full rewire. **Not yet built, ordered, or bench-tested** — full open-items list in the doc itself.

**Planned next steps, reconciled 2026-08-28 — folds in CARD-0218's Intent/Power-switch redesign, since it touches the same physical wiring this card is about to rebuild anyway. Not yet started.**

1. ~~Debug UART, one more attempt, time-boxed~~ — **done and gone much further than planned, 2026-08-28.** Not a baud problem at all: continuity confirmed good and the adapter's RXD LED never lit at either 9600 or 115200 despite confirmed real boot events, ruling out both wiring and baud theories. Root-caused via a control test on the onboard USB port — three real bugs found and fixed (DEBUG-level log filtering, reset-reason read timing matching CARD-0217's hiking-monitor bug, and the actual cause: ESPHome's `logger_esp32.cpp` never calls `uart_set_pin()` for `hardware_uart: UART2`, so GPIO17 was never routed through the GPIO matrix regardless of anything on this project's side). Fixed with a manual `uart_set_pin()` lambda in `on_boot`. **Confirmed live: clean `"BOOT - reset reason: power-on event"` text captured over the external adapter, RXD LED flashing in sync** — full writeup on CARD-0205.
2. **Done, 2026-08-28 — clean, unambiguous result on the retest, real evidence now in hand.** First attempt (above) was inconclusive: a second reset ~58s after cold boot logged `"software via esp_restart"`, but Joseph flagged it may have been his own manual switch-off/on cycle rather than a spontaneous fault, and that reason string doesn't match what a genuine power interruption should report anyway — left unresolved pending a cleaner retest. **Retest run with the switch left completely untouched after a single initial power-on** (off → wait → on, then hands off for the full 5-minute window, no manual intervention): the very first cold-boot-on-battery event logged reset reason **`"brownout"`** — a genuine hardware brownout, unambiguous this time since no human action could have caused it. After that single reset the device booted clean and stayed fully stable for the rest of the 5-minute window, no further resets. **Independently corroborated, not just inferred from the log:** Joseph directly observed the onboard power LED (hardwired to the 3.3V rail, no firmware involved) pulsing right before the boot that finally succeeded, then settling solid once stable — a second, physical confirmation of the same brownout event, matching the mechanism exactly.
   - **Likely cause, given this firmware is minimal (LED blink + one interval tick + one debug-sensor read, no WiFi/SEN55 at all): inrush current at the moment the switch closes, not steady-state draw.** The MCP1700's own output capacitor, the ESP32 board's bulk capacitance, and the TP4056 module's bypass caps all charge simultaneously the instant power is first applied, on top of the MCP1700 potentially having imperfect transient response during its own startup/soft-start window — plausibly enough to sag the rail below the ESP32's brownout threshold before steady-state regulation settles in.
   - **Real, somewhat distinct finding from `power-system-redesign.md`'s original design rationale**, worth carrying into Phase 4: that doc's case for the Pololu D24V10F3 was built around the *steady-state* coincident-peak scenario (WiFi burst + SEN55 running together). This cold-power-on brownout is a different moment entirely — no WiFi, no SEN55, pure inrush — and it's real on the current hardware. Stage 0's re-run against the new regulator (Phase 4 below) should specifically confirm the Pololu handles *this* moment cleanly too, not just the steady-state peak it was explicitly sized for.
3. ~~Physical hardware swap, same board (not a separate rig)~~ — **done and verified electrically, 2026-08-28.** MCP1700 removed, Pololu D24V10F3 installed (VIN off the post-switch battery+ node, GND common, VOUT to ESP32 3V3); 470µF electrolytic + 4.7µF ceramic both landed directly in the ESP32 3V3 pin's own breadboard row (not the distant rail — proximity to the point of load matters for transient response, the exact mechanism behind the brownout finding above) alongside the SEN55 adapter's existing VIN wire, all fitting with zero spare holes. SS12D10 moved off Power Switch duty and rewired as the Intent switch (GPIO27/GND); a spare SS12D10 (Bin A3) installed as the temporary Power Switch in its place — BK-1208 still not on hand, no other rewiring needed once it arrives. **Verified:** zero volts/current downstream with the switch off; Pololu VOUT 3.31V unloaded, 3.27V at the ESP32's 3V3 pin under load (~40mV drop, normal wire/contact resistance, clean regulation); Intent switch continuity confirmed solid-closed/open-open directly at its two terminals (a proper HIGH/LOW logic-level check needs real firmware reading the pin, deferred to Phase 4 below — the ESP32's internal pull-up only activates under firmware configuration, not a hardware default, so a bare-voltage check on an unconfigured pin isn't meaningful).
4. **Re-run the minimal-test staged sequence against the new hardware**, 4 consecutive clean battery-power cycles per stage before advancing (matching this card's own 2026-08-24 base-platform bar), pausing to diagnose at any regression:
   - ~~Stage 0 re-run (boot+LED only)~~ — **PASS, 2026-08-28.** 4 of 4 consecutive clean battery-power cycles, one switch-on each, hands off. Cycles 1-3 logged a clean `"power-on event"` reset reason with no follow-up reset over a 60s window each; cycle 4 logged a blank reset reason (the same known intermittent debug-component reporting quirk seen earlier, not a new failure) but was equally a single, clean, stable boot. **The cold-power-on brownout that was 100% reproducible on the MCP1700 (item 2 above) did not recur once on the Pololu D24V10F3** — real, positive evidence the swap fixes the specific inrush-driven failure mode found on the old hardware, not just the steady-state coincident-peak scenario it was explicitly sized for.
   - Stage 0b — confirm reset-reason logging still works (or note it's still degraded) with the new hardware. **Reset-reason logging confirmed working** (see above, 3 of 4 cycles clean text, 1 blank — same as pre-swap reliability). GPIO27 Intent-switch binary_sensor also added to `minimal-test.yaml` this session (closes the deferred logic-level check from Phase 3's continuity-only test) — toggle verification pending, next step.
   - **Stage 1 (+WiFi) — NOT YET PASSING, 2026-08-28, real intermittent instability, root mechanism understood.** `wifi:` block added to `minimal-test.yaml` (home network only, no MQTT/OTA/API yet), compiled and flashed clean. Two trials:
     - **Trial 1:** onboard power LED pulsed continuously for 90+ seconds with zero UART output the whole time. Switched off (LiPo-safety judgment call) rather than let it keep cycling indefinitely — never confirmed whether it would have eventually recovered on its own.
     - **Battery ruled out as a confound:** measured 3.88V directly (~70-80% charge, healthy) before the retry, ruling out depletion as the explanation for trial 1.
     - **Continuity re-checked and confirmed good** across the entire freshly-rewired battery+/switch/regulator/cap chain (Power Switch both sides, TP4056 `BAT+`/Pololu `VIN`/divider `R1` junction, Pololu `GND`, Pololu `VOUT`→ESP32 3V3, both bulk cap leads) — ruled out a loose connection as trial 1's cause.
     - **Trial 2, clean capture, real mechanism confirmed:** this boot's own reset reason was `"brownout"` — a real brownout occurred right as WiFi began scanning, causing the reset that led into this attempt. That attempt then scanned, found `JCTnet1` (4 BSSIDs), connected in ~2.3s, and stayed stable the rest of a 90s window.
     - **Conclusion: WiFi association does trigger real brownouts on the Pololu, but recovery is usually fast (this trial needed exactly one retry) rather than a hard, sustained failure** — consistent with a genuinely marginal transient-response margin against WiFi's fast-edge RF-PA current bursts (a different current profile than the single decaying inrush transient Stage 0's bulk caps were proven against), not a wiring fault or a steady-state capacity shortfall. Real, if usually brief, gap between what the design was validated against (cold-boot inrush) and what it's now being asked to survive (repeated fast transients). Does not meet the 4-consecutive-clean-cycle bar Stage 0 passed.
     - **Characterized further, same session — 5 trials total, clean pattern.** Trials 2-5 (4 of 5) each showed the identical signature: this boot's own reset reason `"brownout"`, occurring right as WiFi scanning starts, then a clean scan → connect to `JCTnet1` (4 BSSIDs) in 2-4 seconds total, fully stable afterward. Only trial 1 hung significantly longer (90+s, switched off before confirming whether it would have self-resolved). **Working characterization: WiFi association reliably trips exactly one brownout on this hardware, and recovery is fast and consistent in the large majority of attempts** — real instability, not resolved by the Pololu swap, but far short of the sustained crash-looping the MCP1700 showed. Trial 1 remains an open outlier, not yet explained — worth watching for on future cycles rather than assumed to be a one-off. **Still does not meet the 4-consecutive-zero-reset bar Stage 0 passed**, but the failure mode is now well-characterized: a single, reliably-recovering brownout at WiFi scan start, not an open-ended hang.
     - **Firmware-delay experiment, same session, Joseph's call to try first — NEGATIVE RESULT, real and informative.** Tried disabling WiFi at `on_boot` priority 500.0 (above WiFi's own `setup_priority` ~250, so it should run first) and only calling `wifi.enable()` explicitly from the interval once `millis() > 3000`, hoping to separate WiFi's current draw in time from the boot-time inrush. **Didn't work as intended:** WiFi began scanning essentially immediately after `setup()` completed (before the 3s delay), and the brownout occurred at the same point in the boot sequence as every untouched trial — the explicit `wifi.enable()` call at t≈3s fired *after* WiFi had already scanned and was mid-connection on its own. **Conclusion: `wifi.disable()`/`wifi.enable()` are runtime controls for an already-initialized radio, not a way to suppress the automatic connection attempt `setup()` itself unconditionally kicks off.** This specific approach is closed off, not just unresolved — a genuinely different mechanism would be needed to delay WiFi's actual first current draw (if that's still worth pursuing), such as never declaring the `wifi:` networks at boot-time config at all and initiating the connection through some other API later, which is a larger change than this quick experiment.
     - **Decision point resolved, Joseph's call: try a hardware change (bulk capacitance) first.** 10µF ceramic (BOJACK kit, Plastic Box) chosen over the existing 4.7µF as the more targeted fix for WiFi's fast-edge RF-PA bursts (vs. bumping the 470µF electrolytic, which addresses burst *duration* rather than edge speed) — see the session's own reasoning for why each cap type addresses a different part of the mechanism, and the real caution carried over from CARD-0198's 2026-08-24 MCP1700 testing that capacitor size alone didn't reliably fix a similar problem there.
     - **10µF ceramic result: real regression, not an improvement — never even got to test the WiFi question.** Two attempts (initial power-on, then a manual EN/RESET on stable power) both failed to reach even the first LED self-test blink — worse than the 4.7µF's Stage 0 behavior (4/4 clean) and worse than any WiFi trial (all of which at least reached the LED sequence). Onboard power LED read steady (not flickering) during the hang, suggesting a stall rather than a brownout-reset loop. **Plausible mechanism:** more capacitance needs more charge to reach the same voltage, so bumping the ceramic likely increased the *inrush* current draw at power-on — reintroducing the exact cold-boot problem Stage 0 had already resolved with the smaller value, as a side effect of trying to fix a different (WiFi-burst) problem. Continuity confirmed good before concluding this was a real electrical/capacitance-value effect, not a loose connection.
     - **Reverted to 4.7µF — did NOT restore Stage 0's clean behavior, a second real puzzle.** Same nominal configuration that passed 4/4 cleanly hours earlier now also failed to reach the LED blink. Systematically checked, in order: continuity (good), battery voltage (3.86V, effectively unchanged from an earlier 3.88V reading, ruling out depletion), and a fresh, never-before-used 4.7µF ceramic from the same kit (ruling out physical damage to the specific part from repeated handling). **None of these explained it.** Working theory, not confirmed: cumulative contact wear across the whole ESP32-3V3-pin breadboard row (already identified earlier this session as packed with zero spare capacity) from the very large number of switch cycles and component insertions/removals this session performed — a general degradation not attributable to any single part, and not something a spot-check on individual connections would catch.
     - **Session paused here, 2026-08-28, Claude's recommendation given the length of this session and an unexplained result that doesn't fit any tested hypothesis.** Current physical state: fresh 4.7µF ceramic installed (same value Stage 0 passed with), but NOT currently reproducing that passing behavior — **do not assume Stage 0's PASS still holds without re-verifying it fresh next session.** Suggested first step next time: a full re-seat of the entire ESP32-3V3-pin row (not just the capacitor) before trusting any further result there, given how many different things share that one crowded row (ESP32 pin, Pololu VOUT, SEN55 adapter VIN, both bulk caps).
     - **Original decision point still open, now with less clean footing than before:** whether to accept the single-brownout-then-recover WiFi behavior (last cleanly established with the *original* 4.7µF, before any of today's cap-swap complications), pursue bulk electrolytic capacitance instead of ceramic (untried), or a more involved firmware approach to delay WiFi's first current draw. Needs Stage 0 re-verified clean again before any of these are worth pursuing further.
     - **Correction, 2026-08-29 — every Stage 1 trial to date tested a scenario the real firmware can never actually produce, per `JCTsh-Build-Standards.md` §2.14 point 13 (added same day).** All trials ran with USB unplugged from *both* the ESP32's own port and TP4056's charging port — pure battery, Power Connected false throughout. But WiFi only ever enables in the real gated firmware when Intent is off **and** Power Connected is true (both required) — a pure-battery WiFi boot is not a state the finished device would ever reach. `minimal-test.yaml`'s `wifi:` block connects unconditionally at boot with none of point 13's gating logic implemented, so this was always a narrower, component-level question ("can this power path survive WiFi's current draw at all") rather than a simulation of real firmware behavior — worth being explicit about rather than assuming the trials matched real conditions.
     - **Whether this invalidates the brownout finding: probably not, but genuinely untested.** The Pololu's `VIN` taps `TP4056 BAT+` directly, not the USB input — a bare TP4056 (no power-path management) doesn't give the Pololu clean pass-through power from USB while charging, so the load side draws from the same battery node regardless of Power Connected state, and the brownout mechanism (Pololu transient response vs. WiFi's fast current edges) shouldn't depend much on whether charging happens to be active at the same moment. **But simultaneous TP4056 charging current and Pololu WiFi-load current sharing that same `BAT+` node is a real, completely untested interaction** — could add noise/ripple, could be neutral, not yet measured either way.
     - **Required correction before Stage 1 can be called passing or failing for real:** re-run the trial sequence with USB actually plugged into **TP4056's charging port** (not the ESP32's own port) while triggering a WiFi association attempt, so Power Connected is genuinely true — the only condition the real firmware will ever actually produce. Battery-alone trials to date stay useful as a component-level data point, not as the final validation.
   - Stage 2 (+MQTT), Stage 3 (+I2C/SEN55) — not yet reached. Stage 3 should specifically try to provoke the coincident-load scenario the redesign targets (trigger WiFi association while SEN55 is actively in Measurement mode), not just let both run and hope they overlap. **All remaining stages, and any Stage 1 re-run, should have USB plugged into TP4056's charging port throughout (Power Connected true) — see the 2026-08-29 correction above. Pure-battery trials are not the real condition.**
   - **Future step, added 2026-08-29, once the current hardware puzzle is resolved and the Power-Connected-true retest is done: a deliberately-discharged-battery WiFi trial.** Every trial to date used a healthy battery (3.86-3.88V) — CARD-0224 (raised same day) is about what happens when battery is low specifically *because* the device just worked hard, combined with Intent-off + Power-Connected-true. Reuse this same rig/`minimal-test.yaml` at a real lower voltage rather than treating that as separate work needing its own setup — see CARD-0224 for the full reasoning and why this is expected to be the worst-case version of the brownout mechanism already being characterized here, not a different problem.
5. **Once Stage 3 is clean:** re-flash the real `air-quality-monitor.yaml` onto this same board and resume CARD-0012's Step 7 (LiPo polarity, regulator VOUT under load, BK-1208 cutoff verification, dock-detect raw check, battery-divider raw check, plus the new Intent-switch raw check) — see that card.

**Related:** CARD-0012 (parent air-quality-monitor build card, Step 7 now blocked on this card), CARD-0070/CARD-0026 (hiking-monitor's own LDO/boost-converter power investigations, the precedent this device's LDO choice was built on), CARD-0205 (debug UART — corrected 2026-08-28 to reflect that GND fix alone did not resolve capture, see that card), CARD-0211/CARD-0212 (hiking-monitor's matching same-night incident), CARD-0213 (the general `JCTsh-Build-Standards.md` §2.14 peak-current-headroom standard harvested from this investigation, resolved), CARD-0218 (Intent/Power-switch redesign, folded into this card's hardware-swap step above), CARD-0181 (hiking-monitor's own BK-1208 need — shared ordering blocker), `components/air-quality-monitor/power-system-redesign.md` (the concrete regulator swap applying that standard to this device, design only), `components/air-quality-monitor/minimal-test.yaml` (the incremental test build), `components/hiking-monitor/hiking-monitor.yaml` and `components/air-quality-monitor/air-quality-monitor.yaml` (both boot sequences tabulated above).

---

### CARD-0197 · [idea] [data-pipeline] Instrument GPS correlation lookup to confirm the suspected Node-RED/Apps Script timing race — RESOLVED 2026-08-29
**Status:** Done

**Built and deployed, verified live 2026-08-24 00:21 MST.** Implemented as designed, with one refinement: rather than duplicating the get-or-create-sheet + appendRow logic at both call sites, added a shared helper `_logCorrelationDebug(ss, eventType, targetTs, bestDiffSec)` (`environmental-data.gs`, right above `_gpsLookup`) that gets or creates the "Correlation Debug" tab (writing a header row on first creation: `logged_at, event_type, target_ts, best_diff_sec`) and appends one row. `_gpsLookup()` calls it with `'lookup_miss'` on a miss (before its final `return`); the `action=gps` handler calls it with `'gps_append'` right after its existing `gpsSheet.appendRow(...)`.

**Deployment confirmed, not just assumed:** `SCRIPT_VERSION` bumped to `2026-08-24.1-correlation-debug` (missed on the first pass, caught when Joseph asked about it directly), then verified live via `curl "...?action=version"` — returned `{"status":"ok","version":"2026-08-24.1-correlation-debug"}`, exact match, confirming the redeploy actually took effect rather than trusting the editor's own "saved" state (per this file's own established gotcha, CARD-0099's card history).

**Remaining before this card is fully Done:** capture at least one real blank-lat/lon occurrence on a future hike with both a `lookup_miss` and a matching `gps_append` row, and do the T1-vs-T2 wall-clock comparison this card exists to enable. Instrumentation is live and ready to catch it; nothing more to build until that happens.

**Raised 2026-08-23 04:39 MST (Joseph), following up on the blank-lat/lon investigation from the 2026-08-22 hike's data-gap review.** 6 of 97 Environmental Data readings that hike came back with blank lat/lon, all clustered in the last ~50 minutes. The working theory (not yet proven): `_gpsLookup()` (`environmental-data.gs:276-295`) scans the "GPS Track" sheet for the nearest point *at query time*, ±5 minutes — if the hiking-monitor's buffered-reading correlation call fires before GPSLogger's own webhook-triggered write for the matching point has landed in the sheet, the lookup finds nothing nearby yet and returns null, even though the real point shows up seconds later. Joseph's call: **not worth fixing** (already a known, accepted, low-impact gap per hike-izer's own docs — see the "fixing the correlation timing" discussion, declined as its own card) — but wants confirmation the theory is actually correct, not just plausible.

**Instrumentation plan, designed in this conversation — small, additive, no behavior change to the correlation logic itself:**

1. **New "Correlation Debug" sheet tab** in the "JCTsh Environmental Data" workbook — one row per logged event: `[logged_at (real wall-clock ISO timestamp, not the reading's own ts), event_type, target_ts, best_diff_sec]`.

2. **In `_gpsLookup()`** (`environmental-data.gs:276-295`), right before the final `return`, log only misses (keeps row volume low):
   ```js
   if (bestDiff > fiveMin || bestRow === null) {
     ss.getSheetByName('Correlation Debug').appendRow(
       [new Date().toISOString(), 'lookup_miss', tsISO, bestRow ? bestDiff/1000 : null]);
   }
   ```

3. **In the `action=gps` handler** (`environmental-data.gs:511-536`), right after the existing `gpsSheet.appendRow(...)` at line 536, log every GPS point landing:
   ```js
   ss.getSheetByName('Correlation Debug').appendRow([new Date().toISOString(), 'gps_append', tsISO]);
   ```

**How this proves (or disproves) the theory — a direct comparison, not another inference.** For any `lookup_miss` row (reading timestamp X, wall-clock time T1), find the `gps_append` row whose own point timestamp is closest to X, and check its wall-clock time T2. If T2 > T1 — the matching GPS point landed in the sheet *after* the lookup already gave up — that's conclusive proof of the race. If T2 < T1, the theory is wrong and something else is causing the blanks, which is worth knowing too.

**Scope is diagnostic only — no fix implied or required.** This card is done once the instrumentation is deployed and has captured at least one real blank-lat/lon occurrence on a future hike with enough data to make the T1-vs-T2 comparison — confirming or refuting the theory either way counts as done. Whether to act on a confirmed race (vs. continue accepting it) is a separate future decision, not part of this card.

**Resolved 2026-08-29 — theory refuted, via CARD-0222, not the literal T1-vs-T2 comparison this card originally envisioned.** The 2026-08-29 hike produced exactly the real blank-lat/lon occurrence this card's instrumentation was waiting for: 46 of 55 Environmental Data readings came back with no lat/lon (CARD-0222). Cross-checked each of the 46 readings' own timestamps directly against this card's own Correlation Debug sheet — **zero matching `lookup_miss` rows for any of them.** That's a direct answer, not an absence of data: if this card's race theory were correct, a failing lookup would still have *fired* and logged a `lookup_miss` row (with `_gpsLookup()` reaching its own final `return`) before losing the race against a GPS point that landed moments later. Instead, `_gpsLookup()` was never even invoked for these 46 — the correlation call itself never completed, most likely because the device was mid-reboot-loop during buffered-reading replay at the time (CARD-0221/CARD-0222's real, separately-diagnosed cause). **This structurally rules out the race hypothesis for this occurrence** — the instrumentation this card built is exactly what made that determination possible, even though the actual failure mode turned out to be a different bug than the one this card set out to catch. Per this card's own bar ("confirming or refuting the theory either way counts as done"), that's satisfied. Follow-on work (finding and fixing the reboot loop itself) continues under CARD-0221/CARD-0222, not here.

**Related:** the 2026-08-22 hike's blank-lat/lon investigation (this conversation), the declined "fix the correlation timing" discussion (same conversation, Joseph's call not to pursue a fix — this card only pursues *confirmation*), `core/data-pipeline/environmental-data.gs`, `.claude/skills/hike-izer/SKILL.md` ("Notes on the data" section, which already documents this as a known gap), CARD-0221/CARD-0222 (the real 2026-08-29 blank-lat/lon occurrence this card's instrumentation resolved against, and the actual root cause it pointed to instead).

---

### CARD-0196 · [enhancement] [hiking-monitor] Extend field-mode hike endurance — display refresh throttling
**Status:** Build

**Raised 2026-08-23 04:36 MST (Joseph), from a battery-usage analysis of the 2026-08-22 hike.** Field mode's actual current draw was reconstructed from the hike's own voltage curve: continuous 4.11V → 3.55V decline over 2h53m of active hiking, projecting to roughly **3h40m of continuous field-mode endurance per full charge** before hitting the firmware's hard-coded 3.4V low-battery cutoff (`hiking-monitor.yaml:531-532`). Four candidate fixes were originally discussed and interviewed 2026-08-23, since split into separate cards by risk/kind: **item 1 (true deep-sleep-between-samples) → CARD-0201** (highest risk, firmware rearchitecture); **item 4 (longer-LiPo fit check) → CARD-0203** (physical research/procurement, not firmware). This card now covers just item 2 (built) and item 3 (a non-deliverable note).

1. **Throttle e-ink display refresh frequency — in scope, confirmed ("this'll work"). Built and config-validated, 2026-08-23 13:42 MST — not yet flashed/verified.** Currently refreshes every single 2-minute cycle (`component.update: hiking_display`, `hiking-monitor.yaml:607`) — ~90 refreshes over a 3-hour hike, each with its own current spike, for a display that doesn't need that resolution. **Correction: there is no "existing display button"** — grepped the current `hiking-monitor.yaml` and confirmed the only `button:` platform is the HA restart button (CARD-0180); that on-demand-via-button alternative named when this card was raised doesn't exist in this codebase, so it was dropped rather than pursued. Implemented instead: a new `field_display_cycle` global counts 2-min cycles while in field mode (`slide_switch` on, MQTT not connected); the display refreshes on the first field-mode cycle and every `FIELD_DISPLAY_REFRESH_CYCLES`-th cycle after (constant set to 10, i.e. ~20 min cadence — Joseph's call 2026-08-23, revised up from the initial 5/~10min default — easy to retune further), skipped cycles leave the last-drawn e-ink frame on screen at zero extra power. Home/upload mode (docked, charging) is explicitly excluded from the throttle — refreshes every cycle as before, since battery isn't the constraint there. `esphome config` validates clean against the synced `C:\esphome\hiking-monitor\` copy; not flashed, no physical device access from this session.

**Flashed 2026-08-24 (OTA)** as part of the broader hiking-monitor firmware update that also carried CARD-0195/CARD-0200 (all three live in the same `hiking-monitor.yaml`). **Correction, found 2026-08-24 while reviewing Build-column cards for closure:** an earlier version of this note also listed CARD-0198 here — wrong, that's air-quality-monitor, a completely different device on its own separate YAML, never touched by this flash. Ran on the real 2026-08-24 hike ("Boulder Pass Loop") — Joseph reported not consciously noticing the refresh frequency, which is consistent with the design (only ~4 refreshes total over a ~76-min field session, ~20 min apart) but wasn't independently confirmable from any existing log data, since e-ink `update()` calls weren't logged anywhere.

**Refresh-event logging added, 2026-08-24, same session — real verification tool, not just inference from the design math.** `hiking-monitor.yaml`'s throttled-refresh branch now calls `hike_log_write("{\"event\":\"display_refresh\",\"ts\":\"<real NTP time>\"}")` right alongside each actual `hiking_display.update()` call — rides the same flash-buffer-then-MQTT-replay path CARD-0195's skip/reset records already use. Real event time is included deliberately (per this project's own event-time convention): every buffered record lands on the dashboard within the same ~1s bulk-replay burst at hike-end regardless of when it actually happened during the hike, so a bare receipt timestamp would show all refresh events at nearly the same moment and be useless for confirming the ~20min cadence. `core/data-pipeline/environmental-data.flow.json`'s "Route skip/reset events" function node (CARD-0195) extended to also match `d.event === 'display_refresh'`, converting it to a `System`-category `/log` message reading "Display refreshed (field mode) at \<ts\>" instead of letting it fall through into the GPS-lookup/Sheets pipeline as a malformed reading. `esphome config` re-validated clean, flashed OTA and confirmed live via a fresh reconnect on the dashboard (09:26:18 MST).

**Node-RED flow deployed and live-verified, 2026-08-24.** Imported by Joseph (delete-tab-then-import-whole-file, the same method that worked for CARD-0195 — not the straight-import-over-the-existing-tab approach first suggested here). Verified with two real synthetic MQTT publishes (`mosquitto_pub` on `jctsh/components/hiking-monitor/data`, not a real hike) rather than trusting "successfully deployed" alone: both correctly produced `"Display refreshed (field mode) at <real event time>"` on the log dashboard (confirmed via the Pi's `state.json`), and a direct check of the real Environmental Data sheet for that time window confirmed zero `hiking-monitor` rows — the events were correctly diverted away from the GPS-lookup/Sheets pipeline, not landing as malformed readings.

2. **Solar panel used on day hikes, not just multi-day trips — noted, not committed ("maybe").** No engineering work involved (the SUNYIMA panel already exists and is documented for multi-day use in `power-system.md`) — just a possible operational habit change, not a deliverable of this card. Not part of "done" criteria.

**Explicitly excluded — CARD-0070 (LDO swap), CARD-0201 (sleep rearchitecture), and CARD-0203 (LiPo fit) all stay separate**, split out by risk/kind rather than bundled here.

**Done when:** ~~the display throttle is flashed~~ — met, 2026-08-24. ~~the Node-RED routing works~~ — met, verified live with real synthetic MQTT events (above). **Still open, and now a confirmed real gap, not just "not yet exercised":** the 2026-08-25 hike (6:33 AM-9:59 AM confirmed, ~6.5hr field-mode window per CARD-0211's timeline) was exactly the real multi-hour hike this criterion was waiting on — checked directly, and it shows **zero** `display_refresh` log entries at all, where the code's own logic guarantees roughly a dozen. **Do not re-close this card on the strength of a future hike alone** — the mechanism has now failed its own real-world test once; see **CARD-0216** for the investigation (several plausible explanations checked and ruled out, root cause not yet found). This card stays open until CARD-0216 either finds and fixes the actual cause, or a real hike is confirmed showing the expected cadence.

**Related:** CARD-0201 (broken-out sleep rearchitecture), CARD-0203 (broken-out LiPo fit check), CARD-0070 (deferred boost-converter/LDO swap), CARD-0195 (sibling diagnostic-instrumentation card from the same investigation), CARD-0216 (the 2026-08-25 real-hike zero-refresh-events finding — blocks re-closing this card), `components/hiking-monitor/hiking-monitor.yaml`, `components/hiking-monitor/power-system.md`.

**Related:** the 2026-08-22 hike battery-usage analysis (this conversation), CARD-0201 (the broken-out sleep-rearchitecture item), CARD-0070 (deferred boost-converter/LDO swap), CARD-0009 (enclosure build/dimensions — and the undocumented-internal-dimensions gap the LiPo fit check now has to work around), CARD-0195 (the sibling diagnostic-instrumentation card from the same investigation), `components/hiking-monitor/hiking-monitor.yaml`, `components/hiking-monitor/power-system.md`.

---

### CARD-0195 · [enhancement] [hiking-monitor] Field-mode diagnostic instrumentation — skip-reason logging and reset-reason detection — RESOLVED 2026-08-24
**Status:** Done

**Built and config-validated, 2026-08-23 14:16 MST — not yet flashed/verified.** Identified as low-risk (small, additive, no behavior change to existing operation) during a broader reconciliation of hiking-monitor's open power/connectivity cards (CARD-0045, CARD-0070, CARD-0196, this card) — implemented alongside a related low-battery-cutoff bug fix from that same reconciliation (see the new small bug card below). All three scope items built:
1. Skip-reason logging — both silent-return branches (`hiking-monitor.yaml`, the 2-min interval lambda) now call `hike_log_write()` with `{"event":"skip","reason":"clock_invalid"}` or `{"event":"skip","reason":"nan_sensor","temp":...,"hum":...,"pres":...}` (NaN fields rendered as JSON `null`, matching this file's existing convention) before returning.
2. Reset-reason detection — added `debug:` component + a `text_sensor: platform: debug: reset_reason:` (`id: reset_reason_text`), same mechanism air-quality-monitor already uses. `esphome.on_boot`'s priority-600.0 block now checks, right after `hike_log_begin()`: if booting into field mode (switch on, dock off) with a reset reason matching "rownout"/"anic"/"atchdog" (positive-match on abnormal keywords, same approach as air-quality-monitor's LED check — not enumerating every normal-reason string), writes `{"event":"reset","reason":"<text>"}` to the hike log.
3. Node-RED routing — `core/data-pipeline/environmental-data.flow.json` gained a new function node ("Route skip/reset events") right after the `jctsh/components/+/data` MQTT-in, splitting into two outputs: `event:"skip"`/`event:"reset"` records get converted to a standard log message (`category: System` for skip, `category: Alert` for reset) and published to the component's own `/log` topic (component name derived from `msg.topic`, not a payload field — the skip/reset JSON records don't carry a `component` field, so this avoids needing to add one); everything else continues unchanged through the existing GPS-lookup/Sheets pipeline.

**Node-RED side deployed and live, 2026-08-23 (Joseph).** Real incident during the first import attempt, resolved same session, memory updated (`feedback_nodered_updates.md`) so it doesn't recur: the repo file was missing a `tab` node and had `broker: ""` instead of the shared `"mqtt_broker"` id every other flow file in this repo uses — without those, a whole-tab import couldn't match the existing "Environmental Data" tab and landed as a duplicate "Flow 1" instead. Fixed by adding the tab node (matching the live tab's exact id `873111e004dc4435`) and correcting the broker references; re-imported and deployed cleanly after that. **Confirmed no data was lost** — Joseph had deleted the live tab expecting the import to replace it, but nothing had been Deployed yet (verified read-only via the Pi's `flows.json` mtime/tab list before any fix was attempted), so the original tab was still intact underneath.

**Firmware flashed 2026-08-24 (OTA), same broader hiking-monitor update that also carried CARD-0196/CARD-0199/CARD-0200** (all four live in the same `hiking-monitor.yaml`). Exercised for real on the 2026-08-24 hike ("Boulder Pass Loop") — checked the log dashboard afterward and found **zero skip/reset diagnostic entries for the whole hike**, satisfying this card's own stated Done bar directly: "boots and logs normally in the ordinary case (no false-positive skip/reset records under normal operation)." (That same silence was initially mistaken for a possible bug during a real 3-sample Environmental Data coverage gap that hike — CARD-0206 traced the gap to an unrelated query-window padding artifact, not a missed skip/reset event, so this instrumentation's clean silence held up under scrutiny, not just by default.)

**Closed 2026-08-24, per this card's own explicitly-stated criteria** — a real NaN-sensor or clock-invalid skip, or a genuine mid-hike reset, still hasn't happened to actually exercise the diagnostic *content* (as the card always expected: "real validation... happens naturally whenever a future hike actually hits one of these conditions, not forced synthetically before closing this card"). If one ever does, the Node-RED routing (already live-proven working via CARD-0196's own `display_refresh` test today, which shares the exact same function node) will surface it correctly.

**Raised 2026-08-23 04:20 MST (Joseph), found while investigating three data gaps (totaling ~22 missed 2-minute samples) in the 2026-08-22 hike — the first real field deployment.** The 2-minute sensor-read interval (`hiking-monitor.yaml:520-607`) has two explicit silent-skip branches, and field mode has zero telemetry (no WiFi, so `ESP_LOGW` output never reaches anywhere durable) — so after the fact there's no way to tell which of several possible causes (I2C sensor glitch, clock-invalid state, or a full device reset) produced any given gap. This card makes those causes visible on the next hike instead of staying invisible.

**Scope, confirmed via interview 2026-08-22/23 — both pieces together, not split across cards:**

1. **Skip-reason logging.** The two silent `return;` branches currently discard the skip with no trace:
   - `hiking-monitor.yaml:552-556` — clock/NTP not valid at that tick.
   - `hiking-monitor.yaml:564-567` — BME280 read came back NaN on temp/humidity/pressure.

   Change both to call `hike_log_write()` with a small diagnostic JSON record before returning (e.g. `{"event":"skip","reason":"clock_invalid"}` / `{"event":"skip","reason":"nan_sensor","temp":...,"hum":...,"pres":...}`) instead of doing nothing. These ride the same flash-buffer-then-MQTT-replay path (`hike_logger.h`) real readings already use — no new transport needed on the device side.

2. **Reset-reason detection.** On boot, read `esp_reset_reason()`. If the device boots into field mode (switch on, no dock) with an abnormal reason (`ESP_RST_BROWNOUT`, `ESP_RST_PANIC`, `ESP_RST_TASK_WDT`, etc. — not `ESP_RST_DEEPSLEEP`/`ESP_RST_POWERON`), write that to the hike log the same way, so a mid-hike reset is distinguishable from a sensor glitch after the fact.

3. **Node-RED/Apps Script routing addition needed on the receiving side:** once replayed, a `"event":"skip"` record isn't a sensor reading — the environmental-data wildcard handler needs to route these to the `/log` topic (System or a new diagnostic category) rather than attempting to treat them as an Environmental Data sheet row.

**Verification, confirmed via interview 2026-08-23 — deploy-and-wait, not forced bench testing.** These failure conditions (a real NaN sensor read, a real brownout/panic) are hard to trigger reliably on demand. Done criteria: firmware builds clean, deploys to the real field device via OTA/USB, boots and logs normally in the ordinary case (no false-positive skip/reset records under normal operation) — real validation of the diagnostic paths themselves happens naturally whenever a future hike actually hits one of these conditions, not forced synthetically before closing this card.

**Related:** the 2026-08-22 hike's data-gap investigation (this conversation — not yet a card of its own, the gaps themselves were left unexplained, this card is the follow-up), `components/hiking-monitor/hiking-monitor.yaml`, `components/hiking-monitor/hiking_logger.h`, `core/data-pipeline/environmental-data.flow.json` (Node-RED routing that needs the new branch).

---

### CARD-0194 · [idea] [hike-izer] Iterative hike-izer webpage improvements from the 2026-08-22 hike — RESOLVED 2026-08-24
**Status:** Done

**Raised 2026-08-23 03:55 MST (Joseph), found while reviewing the 2026-08-22 hike's data gaps.** The first observation of that hike reads "hiking The tortellito Preserve this morning with David" — almost certainly a Tasker voice-to-text mishearing of "Tortolita Preserve" (a real preserve in the Marana, AZ area matching the hike's actual GPS location). Left uncorrected on the published summary page rather than silently edited.

**Reframed as an umbrella card, 2026-08-23 (Joseph):** "a series of iterative improvements for the hike-izer webpage" prompted by that same hike, not scoped to voice-to-text alone. Four sub-items so far:

**1. Voice-to-text place-name correction — built.** Interviewed: scope is a **general mechanism** for catching/fixing this class of error across future hikes, not a one-off fix. Three approaches were discussed (render-time `place_context` fuzzy-match annotation, a manual-review habit with no automation, and a third: apply the fix directly to the observation text at render time, marked as edited rather than silently rewritten). **Joseph chose option 3** — implemented in `.claude/skills/hike-izer/SKILL.md`: when writing the Full Observations table, cross-check any place/feature name against `place_context`'s already-researched real nearby named features and substitute the corrected word in place, wrapped in `<em>` to mark it as edited (e.g. "hiking The <em>Tortolita</em> Preserve"), with **no bracketed explanation or footnote** (Joseph's explicit instruction — the italics alone are the signal). This keeps the raw-text-in-the-Sheet rule intact (the correction is a render-time substitution, not a Sheet edit) while still respecting hike-izer's "don't paraphrase" convention, since only the specific misheard word is touched.

**2. Manual observation-text editing on the published page — built, deployed, and live-verified by Joseph, 2026-08-24.** Joseph: "I want to be able to manually fix text on the web page." Interviewed and scoped: **observations only** (not narrative or other sections); auth is a **simple shared PIN**, entered via **a secret method** rather than a visible button (Joseph's phrasing) — implemented as a hidden trigger: typing the keyword **"unlock"** anywhere on the page reveals the edit UI. Write-back mechanism: **option 3** — a per-hike JSON overrides file, not a direct Sheet edit and not narrative regeneration.

   Implementation, across `components/hike-izer-orchestrator/`:
   - `templating.py` — each observation row's text is wrapped in a `<span data-obs-ts="...">`; injected JS handles the "unlock" keyword trigger, PIN prompt (remembered in `localStorage` after first success), click-to-edit, and POSTs `{file_stem, timestamp, text}` to a new endpoint.
   - `app.py` — new `/webhook/edit-observation?key=<EDIT_PIN>` route (`EDIT_PIN` deliberately separate from `WEBHOOK_SECRET` — a short PIN Joseph can type on his phone, checked via `hmac.compare_digest`, not the long machine-to-machine secret). Validates the PIN and payload, writes the correction into `<file_stem>_hike-summary.overrides.json` in `SRV_DIR`, and additionally patches the already-published static HTML in place (string-replace on the same `data-obs-ts` marker) so the fix is visible immediately rather than waiting for a future regeneration.
   - `generation.py` — new `_apply_observation_overrides()`, called from both `run()` and `run_step2()` right after loading `hike_data`, so any future regeneration (a re-run, or step 2 enrichment) reapplies prior corrections instead of silently reverting them.
   - `python -m py_compile` clean on all three files.

   **Deployed 2026-08-23/24:** `EDIT_PIN` set directly on the M8's `~/hike-izer-web-app/.env` (not recorded here — device-first, per this project's standing credential-handling convention); `app.py`/`templating.py`/`generation.py` scp'd to `~/hike-izer-web-app/orchestrator/`; `docker compose up -d --build orchestrator` — rebuilt and started clean, healthcheck confirmed `healthy` ~35s after restart.

   **Explicitly scoped out:** syncing this feature to the parallel interactive-Skill template (`components/hike-izer/html-template.html`) — that template only ever renders during a live conversation with Claude, where a wording fix is just "say what to change"; there's no post-session gap for a live-editing UI to fill, and no backend route for it to POST to. The general "keep both templates in sync" convention still applies to layout/visual changes, not to this orchestrator-only feature.

   **Verified live end-to-end, 2026-08-24 (Joseph): "I tested item 2 and it works."** The real unlock → PIN → edit → save flow against a real published hike page, confirmed working — this was the one remaining gap keeping this whole card open.

**3. Per-section data-source attribution — built and deployed.** Joseph wanted each data section to note where its data actually comes from, rather than leaving readers to guess. **Correction, found 2026-08-24 while reviewing this card for closure:** this item's own heading previously said "not yet deployed," contradicted by its own body text below (which already said "Deployed 2026-08-24") — a stale heading, not a real gap. Since verified live and repeatedly on real pages this same day, well beyond the original deploy note (CARD-0204/CARD-0206/CARD-0207's own sessions all confirmed real `data-source` labels present on the live site). Confirmed the real source of each section (some assumed names weren't quite right) before labeling:

   | Section | Label added | Real source, confirmed by reading the pipeline code |
   |---|---|---|
   | Route Map, Elevation and Speed | "from GPSLogger" | The Android GPS-tracking app — the only track-point source anywhere in this pipeline |
   | Environmental Data Tracking | "from JCTsh Hiking Monitor" | The ESP32 device (temp/humidity/pressure/battery) |
   | Weather Forecast at Hike Start | "from Open-Meteo" | Not Weather Underground (that's used elsewhere in the environmental pipeline) — `environmental-data.gs`'s `_maybeCaptureHikeStartForecast()` calls `api.open-meteo.com` specifically |
   | Sun Position | "computed from GPS data" | Not sourced from any device or API — `fetch_hike_data.py` derives elevation/azimuth itself via its own solar-position math from GPS coordinates + timestamp |
   | Full Observations Log | "from field voice-to-text notes" | Joseph's chosen label — there's no standalone "Observation Logger" component in the codebase; the actual mechanism is the "Log Observation" Tasker task on the Pixel (part of hiking-monitor's phone-side workflow, not a separate named product) |
   | Photos | "from JCT via Immich" | Joseph's own phone/camera photos, served through the self-hosted Immich instance on the M8 |
   | Wildlife Heard | "from BirdNET Live" | Not "BirdNet" — `birdnet.py`'s own docstring confirms the real app name is "BirdNET Live" (capital NET), using the BirdNET+ model |

   Implementation: a new `.data-source` CSS class in `templating.py` (small italic muted line right under each section's `<h2>`, styled to sit clear of the heading's own uppercase/letter-spaced treatment) plus one `<p class="data-source">` literal per section. `python -m py_compile` clean. **Deployed 2026-08-24** (`templating.py` scp'd, `docker compose up -d --build orchestrator`, healthcheck confirmed `healthy`) — only affects future page generations, not already-published pages, since this changes the pipeline's template, not existing static HTML.

**4. Elevation & Speed chart click-to-expand, matching the Route Map's — built and deployed.** Joseph: "Just like the route map has an expand map, make the Elevation and Speed have one too." `components/hike-izer/build_hike_chart.py` (the single shared module both templates render through) gained an expand button and modal, following the exact DOM-relocation pattern CARD-0147 built for the Route Map — the same chart-card node (legend, tooltip slot, SVG) physically moves into the modal on open and back on close, no second chart to keep in sync. Simpler than the map's version: no `invalidateSize()`/`fitBounds()`-equivalent needed, since this is a plain SVG with `viewBox`+`preserveAspectRatio` that rescales to its container automatically via CSS layout alone. New CSS in `templating.py` (`.chart-expand-btn`, plus modal-fill rules for `.chart-card`/`.chart-svg-wrap`/`svg.hike-chart` mirroring the existing `.hike-map` modal-fill rule). `python -m py_compile` clean. Deployed to the M8 (`build_hike_chart.py` + `templating.py` scp'd, rebuilt, healthcheck confirmed `healthy`).

   **Real pre-existing gap found and fixed while porting this, 2026-08-24 — not introduced by this session's work.** `components/hike-izer/html-template.html` (the interactive-Skill's own template) embeds the Route Map's expand button/modal markup via `build_hike_map.py`'s shared output, but never actually had the CSS those elements need (`.map-expand-btn`, `.map-modal-backdrop`, `.map-modal`, etc.) — only `templating.py` (the orchestrator's template) had it, dating back to CARD-0147 (early August). This means the Route Map's expand feature was likely non-functional on any page generated through the manual/interactive Skill path, only working on the automatically-generated orchestrator pages. Fixed by porting the full modal CSS block (plus the new chart-expand additions) into `html-template.html` too, so both templates now genuinely match per the project's "keep both templates in sync" convention. This file has no deploy step of its own (read directly by Claude during interactive Skill sessions, not served anywhere) — the repo update is the whole fix.

**All four sub-items closed, 2026-08-24.** Item 1 (voice-to-text correction) is SKILL.md guidance, live from the moment it was written — no deploy step, nothing further to verify beyond a future hike actually needing it. Items 3 and 4 confirmed live and re-verified repeatedly across this same day's other card work. Item 2, the one real remaining gap, closed on Joseph's direct live test.

**Related:** CARD-0147 (built the Route Map's original expand/modal, the pattern item 4 mirrors and whose `html-template.html` CSS gap item 4 found and fixed), `.claude/skills/hike-izer/SKILL.md` (the "don't paraphrase" rule item 1 respects, and where its correction logic now lives), `components/hike-izer/place_context.py` (CARD-0108, the data source item 1 reuses), `components/hike-izer-orchestrator/` (`app.py`, `templating.py`, `generation.py` — items 2 and 3's implementation), `core/data-pipeline/environmental-data.gs` (item 3's Open-Meteo forecast source), `components/hike-izer-orchestrator/birdnet.py` (item 3's BirdNET Live confirmation), `components/hike-izer/build_hike_chart.py` (item 4's shared chart module), `components/hike-izer/html-template.html` (item 4's CSS-parity fix), the 2026-08-22 hike-summary page (`https://hikes.jctnet.com/2026-08-22_hike-summary.html`, the motivating instance for all four sub-items).

---

### CARD-0193 · [idea] [tos] Kanban board scaling strategy — RESOLVED 2026-08-22 20:17 MST
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-08-22 (CARD-0193) — 17933B, over the 5000B size threshold.

---

### CARD-0192 · [idea] [infrastructure] Watchdog self-test for the kanban-PR intake pipeline
**Status:** Build

**Built, 2026-08-24 00:33 MST — not yet deployed, no PR opened yet.** Implementation, per the interview decisions below:
- `tos/open_kanban_pr.py` gained `close_pr(pr_number, token)` — closes without merging and deletes the branch, tolerant of the PR already being closed/merged/gone (cleanup failing shouldn't block opening today's test).
- New `tos/kanban-pr-selftest.py` — daily oneshot script matching `email-idea-check.py`'s style/conventions. Each run: closes the *previous* run's test PR (tracked in its own state file, `/var/lib/jctsh/kanban-pr-selftest-state.json` — separate from `open_finding_pr()`'s own fingerprint-dedup state, which is deliberately *not* reused here since that mechanism is built for "same finding seen again," not "prove the pipeline works right now"); calls `open_finding_pr()` with a date-suffixed fingerprint and an obviously-synthetic message/component (`jctsh-pr-selftest`) so a human glancing at the PR list instantly knows it's not a real finding; re-fetches the new PR to confirm it's genuinely open (not just trusting no exception was raised); persists the new PR number + `last_success_at` for next time. On any failure, publishes an `Alert`-category MQTT message that explicitly names the risk window — "last confirmed-good run: X; any real idea/finding logged since then may have been silently lost" — directly implementing decision 3 below, not just "self-test failed."
- New `tos/kanban-pr-selftest.service` + `.timer` — `OnCalendar=daily`, mirrors `email-idea-check.service`/`.timer` exactly.
- Python syntax-validated (`python -m py_compile`) for both `.py` files.

**Deployed to the Pi and verified live end-to-end, 2026-08-24 00:39 MST — a real bug found and fixed during verification, not a clean first pass.** Installed to `/usr/local/bin/` (`open_kanban_pr.py`, `kanban-pr-selftest.py`) and `/etc/systemd/system/` (`.service`/`.timer`), state dir `/var/lib/jctsh/` created, timer enabled via `systemctl enable --now`.

**Real bug caught on the second manual run:** `close_pr()`'s branch-delete call failed with `Expecting value: line 1 column 1 (char 0)` — traced to `_api()` blindly calling `json.loads()` on every response, but GitHub's DELETE-ref endpoint returns `204 No Content` (empty body), which `json.loads(b'')` chokes on. Every existing caller before this card only ever hit GET/POST/PUT/PATCH endpoints that always return a body, so this was latent until the first DELETE caller. **Fixed at the source** (`_api()` now returns `None` for an empty body, benefiting any future caller, not just `close_pr()`) and `close_pr()`'s exception handling broadened from `except urllib.error.HTTPError` to `except Exception` in both its try blocks — matching its own stated design ("best-effort cleanup, never block opening today's test"), which the narrower catch didn't actually deliver on. Confirmed PATCH itself was never the problem (tested standalone, worked both via raw curl and isolated Python) before concluding the DELETE call was the real fault.

**Full lifecycle confirmed live, not just "deployed with no errors":** run 1 opened PR #30; run 2 (pre-fix) opened PR #31 but hit the DELETE bug trying to clean up #30 (caught, logged as a warning, didn't block opening #31 — the try/except was already doing its job, just for the wrong exception type); redeployed the fix; run 3 opened PR #32 *and* correctly closed PR #31 and deleted its branch (confirmed via the GitHub API: PR #31 `state: closed`, its branch ref `404`s). State file correctly tracks PR #32 as current. PR #30 closed manually during diagnosis, no stragglers left open. Timer's real first scheduled fire is tomorrow — today's three runs were manual (`systemctl start`) to verify the code before trusting the schedule.

**Deployment is a separate, explicit step — flagging deliberately, not bundling it into "built."** This script's normal, designed behavior is to open (and next-day, close) a real PR against the live `joscthomas/jctsh` repo, unattended, every day going forward. That's the whole point of the card, and the interview above already approved the design — but actually running it for the first time has a real, externally-visible effect (a real PR appears), so treating "deploy + enable the timer" as its own go-ahead moment rather than assuming today's interview covers it. **Joseph gave that go-ahead 2026-08-24 — see the deploy note below.**

**Raised 2026-08-22 18:24 MST (Joseph), during a strategy discussion following CARD-0190.** CARD-0190's root bug (the Tasker "Log Idea" widget silently failing while hiking) was only discovered because Joseph happened to check the PR list afterward — nothing surfaced the failure on its own. Addresses the top-priority weakness identified in that discussion: the auto-PR intake pipeline (`open_finding_pr()`/CARD-0128/CARD-0173) runs unattended (a webhook always listening, `email-idea-check.py` polling on a timer) but has no monitoring of its own, unlike this project's other unattended services.

**Approach:** mirror the existing Node-RED watchdog pattern (`core/node-red/watchdog.flow.json` — alerts via HA companion-app push notification if a component goes silent for 10 minutes) rather than inventing a new alerting mechanism. A periodic synthetic self-test calls `open_finding_pr()` with a recognizable test fingerprint, confirms a PR actually opened, then closes it — with a failure routed into the same MQTT log / HA-notification path every other component's health check already uses, so a broken pipeline pages Joseph instead of waiting to be noticed by chance.

**Interviewed 2026-08-24 00:30 MST — all four open questions resolved:**
1. **Cadence: daily.** Matches how infrequently this pipeline actually sees real traffic (occasional voice ideas / maintenance findings) — catches a silent failure within a day without adding noise. Hourly (the Node-RED watchdog's own aggressiveness) was considered and passed over — that pattern was built for continuously-active components, which this isn't.
2. **Job location: new systemd timer alongside `email-idea-check.py`**, not folded into `maintenance-check.py` — keeps this test's own failure mode isolated and visible, not buried inside a script built for a different purpose. **Correction, 2026-08-24 (found while deploying): `email-idea-check.py` actually runs on the Pi (`/usr/local/bin/`, confirmed via SSH), not the M8 as this interview note originally said** — the isolation reasoning holds, the host in this write-up was just wrong.
3. **Dropped-idea flag: yes.** A failed self-test's alert explicitly calls out the risk window (e.g. "pipeline broken since ~X — any real idea logged in this window may have been lost"), directly addressing what actually happened in CARD-0190, not just reporting "infra is down."
4. **Test PR cleanup: automatic.** The self-test recognizes its own prior test PR by fingerprint and closes it as part of each run — no manual accumulation to clean up later.

**Done when:** the systemd timer is built and deployed ~~on the M8~~ **on the Pi (corrected above) — met**; a successful run is confirmed to open-then-close its own test PR without leaving stragglers behind — **met** (see verification above); a real failure (e.g. a deliberately broken PAT) is confirmed to produce the dropped-idea-flagged alert via the existing MQTT/HA path — **not yet tested**, the one remaining item before this card is fully Done.

**Related:** CARD-0190 (the incident this directly addresses), CARD-0128 (`open_finding_pr()`, what's being tested), CARD-0173 (Tasker "Log Idea" widget, the path that failed silently), `core/node-red/watchdog.flow.json` (the existing pattern this mirrors), `core/maintenance/email-idea-check.py` (the sibling systemd timer this job runs alongside).

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

**Raised 2026-08-22 17:07 MST (Joseph), live during a review session** — after choosing "Delete all N in Robin's library" (CARD-0155's super-rule bulk-delete box), the "Marking decisions: X of Y…" phase is very slow, well before the actual Immich delete step even starts.

**Root cause, found via code read of `server.js`/`public/review.js`:** the client's Phase 1 loop calls `/api/decide/duplicate` once per qualifying group (6-way concurrency via `forEachWithConcurrency`), but every one of those calls does a full read-parse-mutate-write of the *entire* `decisions.json` file (`loadDecisions()` → mutate → `saveDecisions()`), and all such writes are serialized through a single global lock (`withDecisionsLock`, added by CARD-0028 to fix a real race condition). So N groups means N sequential full-file I/O round trips, not N fast in-memory updates — and it gets slower over time as `decisions.json` accumulates decisions across the whole multi-year review. This is a *different* bottleneck than CARD-0148's already-known-and-accepted `refreshTally()`/`pendingDeletions()` cost.

**Scope, decided via interview 2026-08-22:** fix only the super-rule bulk-delete marking phase — add a new bulk endpoint (e.g. `POST /api/decide/duplicates-bulk`) that takes the full list of qualifying groupKeys in one request, does a single `loadDecisions()` → mutate all → single `saveDecisions()`, still under the existing lock. `openSuperRuleModal`'s Phase 1 in `review.js` switches to this one call instead of the per-group loop. Regular one-at-a-time manual clicks (radio/skip/keep-all/delete-all buttons) are explicitly out of scope — a human clicking one at a time doesn't expose the same N-round-trip cost the way a tight programmatic loop does.

**Done when:** marking all qualifying groups for a real year with a meaningful `qualifiedCount` completes in roughly the time of one file write (not N round trips), confirmed live against real data — not just code review. `decisions.json` after the bulk-mark matches what N individual `/api/decide/duplicate` calls would have produced (same keys, same `{ keepAssetId, auto: true, autoReason }` shape) — no regression in the correctness CARD-0028's locking fix established.

**Related:** CARD-0155 (super-rule bulk-delete feature this bug is in), CARD-0028 (review app, `decisions.json` locking discipline), CARD-0148 (separate, already-known `refreshTally()` cost — not what this card fixes).

**Fixed and deployed, 2026-08-22 17:20 MST.** Added `POST /api/decide/duplicates-bulk` to `server.js` (single load → mutate all → single save under the existing lock) and switched the super-rule modal's Phase 1 in `review.js` to call it once instead of looping `/api/decide/duplicate` per group. **Found live on the first deploy:** the new client loop called `findDuplicateGroup()` — a linear scan over the whole library's 38,258 duplicate groups — once per qualifying key with no yielding, which froze the tab for the entire loop and was worse than the original (Joseph: "even slower than before"). Fixed by building a one-time `groupKey → group` lookup Map before the loop (O(M) once, O(1) per key) instead of repeated linear scans. Deployed both fixes to the M8 (`server.js` + `sudo systemctl restart photo-quality-review` for the first; `review.js` alone, no restart needed, for the second — static file). Confirmed fast live by Joseph against real data.

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

**Raised 2026-08-18 18:23 MST (Joseph), while building CARD-0146.** CARD-0145's Ring motion announcement currently triggers on `sensor.*_last_activity` (CARD-0184's fix for the durably-broken native `ring` integration `event.*` platform) — reliable, but polled at ~60s intervals, so real delay can run 30-90+ seconds between an actual motion event and the announcement.

`ring-mqtt` (installed this session for CARD-0146) publishes its own independent `binary_sensor.<camera>_motion` entities, separate codebase/connection from the broken native integration. Live-tested today on the doorbell (`binary_sensor.doorbell_ding`/`binary_sensor.doorbell_motion`): near-instant, on within a few seconds of a real event — confirmed reliable across all of today's CARD-0146 testing. Confirmed the same entities exist for CARD-0145's other 4 cameras too: `binary_sensor.path_motion`, `binary_sensor.gate_motion`, `binary_sensor.front_porch_motion`, `binary_sensor.front_door_motion` (all present, all `off` at check time).

**Not yet decided/scoped:** swapping CARD-0145's trigger from `sensor.*_last_activity` to `binary_sensor.*_motion` for all 5 cameras (gate, path, front_door, front_porch, doorbell) — mechanically similar to CARD-0184's own swap, but the reverse direction. The `category == 'motion'` filter condition CARD-0184 added would no longer be needed (`binary_sensor.*_motion` entities are motion-only by construction, same reasoning as the original native-integration `event.*_motion` entities). Needs a live test pass on all 5 cameras (not just doorbell, which is all that's been proven so far) before trusting it as a full swap, plus the debounce/cooldown logic reconsidered for a fast-push source (the current 3s trailing delay and 30s entry-cluster window were tuned against a poll-based source's own timing characteristics).

**Done when:** CARD-0145's automation trigger is swapped to `binary_sensor.*_motion`, live-tested against real events on multiple cameras (not just doorbell), and confirmed both correctly-triggered and correctly-debounced — or a decision to keep the current poll-based trigger is recorded instead, with reasoning.

**Superseded 2026-08-20 16:18 MST.** A real field event the same day surfaced two more findings (a doorbell voice/video coordination problem, and a premature CARD-0146 stream termination) that don't fit this card's narrow trigger-swap scope — rather than keep bolting new findings onto this and CARD-0145/CARD-0184, all of it (including this card's own trigger-swap scope, unchanged) is consolidated into CARD-0187. No work here was wasted — the `binary_sensor.*_motion` entity confirmation and scoping notes above carry forward directly.

**Related:** CARD-0145 (the automation this would have upgraded), CARD-0184 (introduced the current `sensor.*_last_activity` fallback this would have replaced), CARD-0146 (the build that surfaced ring-mqtt's own motion entities as a viable alternative), CARD-0187 (supersedes this card).

---

### CARD-0184 · [bug] [outdoor-presence-detection] CARD-0145's Ring motion announcement has been silently dead since 2026-08-15 — RESOLVED 2026-08-18 17:02 MST
**Status:** Done

Archived to `components/outdoor-presence-detection/CLAUDE.md` on 2026-08-22 (CARD-0193) — 10489B, over the 10000B size threshold.

---

### CARD-0183 · [bug] [hike-izer] Hike-publish push notification link isn't clickable — RESOLVED 2026-08-18 15:11 MST
**Status:** Done

**Raised 2026-08-18 (Joseph, via voice note, PR #25).** The push notification sent on hike-summary publish (CARD-0141) includes the published page's URL as plain text inside the message body — confirmed in `components/hike-izer-orchestrator/generation.py`'s two success call sites (`run_and_log()`, `run_step2_and_log()`), both of which build the URL into the `message` string passed to `ha_notify.send_push()`. `ha_notify.py`'s `send_push()` only sends `title`/`message` to HA's notify service — no `data.clickAction` (or `data.url`), the field the HA companion app actually uses to make a notification tap open a link. Tapping the notification today does nothing; the URL has to be manually copied out of the notification text.

**Fix:** add an optional `url` parameter to `send_push()` that sets `data: {"clickAction": url}` in the HA notify service call; pass the hike page URL through from both success call sites in `generation.py`.

**Done when:** `ha_notify.send_push()` accepts a `url` param and sets `clickAction`; both success call sites pass it; deployed to the M8 orchestrator; and a real test notification confirmed tapping it opens the hike page in the browser on Joseph's Pixel.

**Built, deployed, and verified live, 2026-08-18 15:11 MST.** `ha_notify.send_push()` now accepts an optional `url` param and sets `data: {"clickAction": url}` in the HA notify payload when provided. Both success call sites in `generation.py` (`run_and_log()`, `run_step2_and_log()`) pass the hike page URL through — failure branches unchanged, nothing to link to on a failure. Deployed via `scp` to `~/hike-izer-web-app/orchestrator/` on the M8 (Tailscale IP) and `docker compose up -d --build orchestrator`. Verified with a real test push (`ha_notify.send_push('Hike-izer test', ..., url='https://hikes.jctnet.com/')` run inside the rebuilt container) — Joseph confirmed the notification arrived and tapping it opened the link in the browser. The generation-pipeline call sites themselves will get exercised for real on the next hike, same as CARD-0141's own original verification pattern.

**Related:** CARD-0141 (introduced the push notification this fixes).

---

### CARD-0182 · [idea] [hike-izer] BirdNET Live recording practices while hiking — DONE 2026-08-19
**Status:** Done

**Raised 2026-08-18 (Joseph, via voice note, PR #26).** BirdNET Live's phone-side bird-call recognition is degraded by trail noise (wind, footsteps, breathing) and phone mic/recording setup while hiking. JCTsh's pipeline only consumes BirdNET Live's already-identified detections after the fact (`components/hike-izer-orchestrator/birdnet-pipeline.md`) — it does no audio processing itself, so this is a practices/documentation item, not a pipeline code change.

**Scope, confirmed 2026-08-18:** research and document phone/app-side practices to reduce noise and improve recording quality (mic placement/carrying position, BirdNET Live app settings) as a new section in `components/hike-izer-orchestrator/birdnet-pipeline.md`.

**Done when:** best-practice recommendations are researched and documented there, and Joseph has a concrete checklist to try on the next hike.

**Researched 2026-08-19 — significant finding, not just a checklist.** Every hike so far has used BirdNET Live's **Live Mode**, not Survey Mode as CARD-0080's original docs/code comments assumed (never actually verified, confirmed wrong by Joseph directly). Checked BirdNET Live's own source on GitHub: Survey Mode and ARU Mode both wire in Android's `flutter_foreground_task` background-survival mechanism via dedicated notification files; no equivalent exists for Live Mode, whose own docs describe it as an actively-open, on-screen-only experience. Strong (not 100% certain) evidence that **Live Mode likely stops listening whenever the phone screen locks or another app gets focus** — meaning every past hike may have had silent gaps beyond the trail-noise problem this card set out to fix. Functionally nothing in the pipeline broke from the wrong mode assumption — verified the Route Map's per-sighting location comes from the hike's own independent GPS track (`build_hike_map.interpolate_position()`), not from anything BirdNET Live itself reports.

**Decided 2026-08-19 (Joseph): switch to Survey Mode for hiking going forward** — purpose-built for this, confirmed background survival, own GPS track. Full writeup, general field-recording checklist (carry position, wind, clothing, handling noise), and Survey Mode setup/Detection-Sampling notes now in `components/hike-izer-orchestrator/birdnet-pipeline.md` Section 4. `birdnet-pipeline.md` and `birdnet.py`'s docstring corrected to stop claiming Survey Mode was ever in use. **Not yet field-tested** — first real Survey Mode hike will confirm.

**Standing constraint, confirmed 2026-08-19 (Joseph): there is no manual review/curation step, ever.** "There is no review at the end of a session. I just take it as it comes. I have no expertise for any review." Whatever BirdNET Live confidently reports flows straight through export → this pipeline → the published hike's "Wildlife Heard" table and the cross-hike Wildlife Life List, with no human filtering anywhere in between. This reversed part of the settings guidance already given (confidence threshold, sensitivity — see `birdnet-pipeline.md` Section 4's correction) and should be assumed true for any future recommendation touching this pipeline: nothing gets curated after the fact, so detection-quality settings need to be conservative on their own, not "good enough, we'll catch mistakes at review."

**Closed 2026-08-19 (Joseph).** Research, checklist, mode-switch decision, and settings are all documented and applied where actionable today. Field verification — does Survey Mode actually close the gaps, do the applied settings hold up in practice — happens naturally on the next real hike; not gating this card's closure. Revisit `birdnet-pipeline.md` Section 4 with results if anything needs adjusting after that hike, new card if it turns into real follow-up work.

**Related:** CARD-0157 (BirdNET Live pipeline documentation, the doc this extends).

---

### CARD-0181 · [bug] [hiking-monitor] No way to cut real power without disassembling the enclosure
**Status:** Defer

**Raised 2026-08-17 18:04 MST (Joseph), called a "major design failure."** Discovered while reassembling the enclosure post-CARD-0009: the only true hard-off state for this device is disconnecting the LiPo's JST connector from the TP4056 (per `operations.md`'s Power Switch Behavior table — "Storage — fully off" requires "Disconnected" battery, no other row reaches true off). That connector is inside the sealed enclosure with no external access, so once assembled, there is no way to actually cut power without taking it apart again.

**Compounding issue:** the device's slide switch reads as a power switch but isn't one — `operations.md` line 79: "VOUT+ runs directly to ESP32 VIN — the switch is not in the power path." It only sets a GPIO-read mode flag (field vs. upload mode); the lowest-power reachable state via the switch is deep sleep (~10µA), not true off. For most purposes (avoiding activity while handling the device) that's sufficient, but it is not the same guarantee as no power draw at all, and the UI/labeling (a slide switch on the outside of the case) actively implies otherwise.

**Not yet decided — fix approach deferred to Planning, Joseph's call 2026-08-17:** candidates raised but not chosen: (1) an accessible inline power switch, wired directly into the battery path (not the existing mode-select switch), reachable from outside the enclosure — true hard off on demand; (2) a JST pigtail extended from the battery connector to an external access cutout, so the existing connector can be reached and unplugged without disassembly, no new switch hardware. Neither confirmed; revisit at Planning.

**Deferred 2026-08-19 (Joseph), clarified 2026-08-27 — same reasoning as CARD-0070's "v2 rebuild" precedent, not just "not started yet."** No fix approach chosen, no work started. This is the real, already-built, field-proven hiking-monitor perfboard — adding a new inline switch means physically opening and reworking hardware that currently works, the same risk-of-disturbing-a-working-device reasoning that's kept CARD-0070 (LDO swap) parked too. Revisit at Planning when the enclosure is next opened for some other reason anyway (CARD-0180's remote-reboot work covers the reboot half of the accessible-control need in the meantime; this card is only about true power-off) — not a standalone teardown just for this.

**Standard raised from this, 2026-08-18 14:35 MST:** `JCTsh-Build-Standards.md` §1.7 (Accessible Power Control for Enclosed Devices, v1.19) now makes this a required decision for every future enclosed build, made before the enclosure is sealed — this card and CARD-0180 are its origin case. §1.7 lists both candidate approaches above as acceptable patterns for requirement 1 (true hard off); whichever gets chosen here should also be reflected there if it changes/refines the general pattern.

**Reframed 2026-08-27 under §2.14 point 12's three-signal model (Intent / Power Connected / Power Switch), added the same day.** This card is specifically hiking-monitor's missing **Power Switch** — a real, coarse-grained inline cutoff in the power path (not readable by firmware in its off state, by definition — no power means no code running to read anything). It's a genuinely different control than the existing slide switch, which is correctly the device's **Intent** signal (GPIO27, readable while powered on, field vs. idle) — the two can't be the same physical switch, since Power Switch's own off state structurally can't be GPIO-read. Whichever fix gets picked here (inline switch, or a JST pigtail) should be wired as a true cutoff *in addition to* the existing slide switch, not a replacement for it.

**Switch design decided, 2026-08-27 — interviewed through several candidates before landing here.** Requirement, refined through discussion: must feel unmistakably different from the existing slide Intent switch (never confusable by feel), must be protected from accidental actuation given it achieves *true* zero-draw off (a real consequence, unlike an Intent mode change), and must not need bulk hardware or enclosure complexity to get that protection.

Candidates considered and set aside, for the record:
- **Guarded/recessed toggle switch** — a spring-loaded flip guard or a recessed mount both genuinely protect against accidental actuation, but add real bulk (the guard hardware) or enclosure complexity (a recessed well/cutout) — ruled out on Joseph's explicit constraint.
- **Mini rotary switch** (Adafruit #2925 or similar) — twist action is genuinely distinct from a slide and inherently resists accidental actuation (a bump/brush applies lateral force, not rotational torque), low-profile, no guard needed. A solid option, but superseded by the choice below.

**Chosen: BK-1208, a mechanically-latching (self-lock) micro push button — 2-pin, DC 30V 1A, 12×8×8mm.** Confirmed as a genuine, real, widely-available part (verified against actual listings, not assumed): [Walmart, 50pcs black](https://www.walmart.com/ip/50Pcs-Black-Latching-Mini-ON-Off-Switch-Self-Lock-Micro-Push-Button-Switch-DC-30V-1A-for-Light-Lamp-Wall-Outlet-DIY-SMD-Flashlight-Type-BK-1208/17583453246), [Amazon, 10pcs black](https://us.amazon.com/Latching-Switch-Self-Lock-Flashlight-BK-1208/dp/B0F6LKBQ4Y), [Amazon, 50pcs mixed white/black (WBK-1208 variant)](https://www.amazon.com/mxuteuk-Self-Lock-flashlight-Latching-white%EF%BC%88can/dp/B0D3ZFGJPX). Same category commonly used in flashlight builds — press to latch closed, press again to release, purely mechanical, no supporting circuit needed.

Why this satisfies every constraint at once:
- **Genuinely different from the slide switch** — a firm press-and-release action, not a lateral slide.
- **True zero-draw off, no circuit** — mechanically bistable (latches on its own), unlike a plain momentary button (which would need an added latch circuit that itself draws standby current — defeating this whole card's purpose).
- **Naturally resistant to accidental actuation, with zero added bulk or enclosure work** — actuating it needs a firm *axial* press; a bump, brushing against something, or a pack strap catching would apply lateral force, which this switch simply doesn't respond to. No guard, no recess, no enclosure redesign.
- **Tiny** — 12×8×8mm, mounts through a simple hole, same practical footprint as the momentary push buttons already used elsewhere in this project (Bin C2).

**Wiring plan:** inline in the battery-positive path, upstream of everything else (the regulator included) — this is the actual hard cutoff, wired in addition to the existing slide switch (Intent), never replacing it. **Free bonus, no new part needed:** both hiking-monitor and air-quality-monitor's ESP32 dev boards already have their own onboard power LED (`operations.md`: "ESP32 power LED lights immediately" on boot) — wiring this switch upstream means that existing LED naturally goes dark whenever the switch is truly open and lights whenever closed, a free "is it really off" visual confirmation with no dedicated indicator LED to add.

**Ordered 2026-08-28** — one order, covers this card's own BK-1208 (latching push-button power switch) and air-quality-monitor's identical need (CARD-0218, folded into CARD-0198's near-term hardware-swap plan). Not yet arrived/on hand. Stays in Defer per the 2026-08-19 decision (revisit at Planning when the enclosure is next opened) — ordering ahead of that trigger was worth doing since CARD-0218 needed it sooner, but doesn't change this card's own sequencing; build/install here still waits for the enclosure to be reopened for some other reason.

**Done when:** the real hiking-monitor can be put into a genuine zero-draw off state without opening the enclosure, verified live (not just wired correctly) — and the chosen mechanism is documented in `operations.md`'s Power Switch Behavior table alongside the existing modes.

**Related:** CARD-0009 (the final-assembly work this surfaced during), CARD-0180 (on-demand remote reboot — a related but distinct need; that card is about forcing a *restart*, this one is about achieving true *power-off*), `JCTsh-Build-Standards.md` §2.14 point 12 (the three-signal framework this fills the Power Switch gap for), CARD-0218 (air-quality-monitor's mirror-image gap — missing Intent instead of Power Switch).

---

---

### CARD-0180 · [enhancement] [hiking-monitor] On-demand remote reboot, triggered from Home Assistant — RESOLVED 2026-08-19 17:24 MST
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5781B, over the 5000B size threshold.

---

### CARD-0186 · [bug] [front-porch-temp-sensor] [salt-sensor] Restart button MQTT discovery id collision — RESOLVED 2026-08-19
**Status:** Done

**Raised 2026-08-19 (Joseph, while closing CARD-0180):** "What about front-porch-temp-sensor and salt-sensor?" — asked after CARD-0180's investigation found hiking-monitor's restart button colliding with these two devices' restart buttons on the exact same auto-generated MQTT discovery `unique_id` (`ESPbuttonrestart`, from ESPHome's default `discovery_unique_id_generator: legacy`, which derives the id from the entity's type + name alone — any two devices with an entity of the same type sharing the literal name "Restart" collide). All three devices' restart buttons are named plain `"Restart"`.

**Confirmed live before starting:** checked HA directly — `button.front_porch_temp_sensor_restart` exists (currently the collision "winner"); `button.salt_sensor_restart` returns "Entity not found" (the silent loser — has never worked from HA, unnoticed until now).

**Scope decision:** hiking-monitor's own fix used `discovery_unique_id_generator: mac` at the device's `mqtt:` block level — safe there because that device exposes only one entity (everything else `internal: true`). front-porch-temp-sensor is not the same shape: it discovers several live entities (temperature/humidity/pressure, light level) feeding the environmental data pipeline, and the generator setting is device-wide, not per-entity — flipping it would regenerate *every* entity's unique_id on that device, orphaning current HA registrations (same duplication mess as CARD-0180's own bug, but on live sensor data instead of an unused button). salt-sensor only discovers the button (its SmartThings switches are separate virtual entities, not published by this device) so either fix is equally safe there. **Decided:** apply the surgical, lower-blast-radius fix to both — give each device's restart button a distinct `name:` (device-specific, not the shared literal "Restart") so the existing legacy generator naturally produces distinct ids. No `mqtt:` block changes, no other entities touched on either device.

**Done when:** both devices reflashed, `button.salt_sensor_restart` (or its post-rename entity_id) appears live in HA for the first time, `button.front_porch_temp_sensor_restart`'s entity confirmed still intact/no duplicate created, verified via live `mosquitto_sub` + HA state check same as CARD-0180.

**Built and verified live, 2026-08-19.** Both devices reflashed OTA. Confirmed via `mosquitto_sub` on `homeassistant/button/#` that each device now publishes a distinct `uniq_id` (`ESPbuttonfront_porch_temp_sensor_restart`, `ESPbuttonsalt_sensor_restart`) — no more collision with each other or with hiking-monitor. Old stale retained discovery topics (`.../restart/config`, `uniq_id: ESPbuttonrestart`) cleared on both via `mosquitto_pub -n -r` so HA drops the orphaned pre-fix entities.

**Result:** `button.salt_sensor_salt_sensor_restart` now exists and works — first time ever (previously silently dropped, confirmed "Entity not found" before this fix). `button.porch_front_front_porch_temp_sensor_front_porch_temp_sensor_restart` (front-porch) also works, no duplication.

**Known cosmetic side effect, not fixed by this card:** naming both buttons with the device name already included (e.g. "Salt Sensor Restart") caused HA to double up device-name + entity-name when generating entity_id/friendly_name — both ended up more verbose/mangled than intended (front-porch's especially, from a brief three-way collision window while the stale topic was being cleared). Functionally correct, cosmetically ugly. **Joseph is doing the entity_id cleanup himself** via HA's UI (Settings → Devices & Services → Entities → rename entity ID) — not scripted, since HA's entity registry rename isn't exposed over the REST API, only the frontend's WS API.

**Related:** CARD-0180 (hiking-monitor — origin case, found this collision as a side effect).

---

---

### CARD-0179 · [idea] [infrastructure] Route captured voice notes to LogSeq, alongside the kanban PR pipeline — low priority

**Status:** Backlog

**Priority:** Low — marked 2026-08-19 (Joseph). No hard deadline; revisit at Planning whenever Joseph wants to pick it up.

**Raised 2026-08-17 12:03 MST (Joseph, via voice note):** Originally arrived as PR #21 (CARD-XXX) from the email-idea-check pipeline (CARD-0151/CARD-0173) with the garbled transcribed subject "sending notes to log seek" — asked Joseph directly, actual idea is "sending notes to LogSeq." PR #21 closed without merging; this card replaces it with a real interview pass.

**Interviewed 2026-08-17:**
- LogSeq setup: points at a local folder of markdown files, kept in sync across devices via LogSeq's own built-in Sync (not Syncthing/Dropbox/Git). That folder does not yet exist on either the Pi or the M8 — LogSeq Sync has no Linux CLI/daemon, so there's no obvious server-side hook into it yet. **Open design problem, not yet solved:** how does a script running on Pi/M8 get a note into a graph that only LogSeq's proprietary Sync touches? Candidates to evaluate at Planning time: a git-backed LogSeq graph (LogSeq supports this natively as an alternative to LogSeq Sync) that the pipeline commits/pushes into; some other cloud-synced folder LogSeq Sync itself can be pointed at; or accepting this only works if Joseph moves off LogSeq Sync for this graph. None of these confirmed yet.

**Researched 2026-08-19 — leading candidate found.** LogSeq has a local HTTP API (Settings → Features → "HTTP APIs server", listens on `127.0.0.1:12315/api`, Bearer-token auth, exposes the plugin SDK — `logseq.Editor.insertBlock` etc., full method list at plugins-doc.logseq.com) — but it's local to wherever the app is actively running, not a cloud API. The candidate this unlocks: run the actual LogSeq app headlessly in a Docker container on the M8 (Xvfb virtual display + noVNC/HTTP API — community pattern, not an official LogSeq deployment mode), signed into Joseph's account with LogSeq Sync enabled as normal. Since it's the literal same client, Sync would keep it in sync with laptop, Pixel 10, and Pixel Tablet exactly like a desktop install — Sync operates at the app/account level, not tied to a physical desktop. And because the API and the app share a host, the M8's own pipeline script can hit `localhost:12315` directly, no cross-device dependency.

Checked two candidate Docker images for this pattern:
- **`CorrectRoadH/docker-logseq`** — actively maintained. Last commit 2026-06-06 (tracks LogSeq's latest release, merged an outside contributor's PR), 0 open issues, 9 stars.
- **`SimonTheCoder/logseq_in_container`** — effectively abandoned. Two commits total, both from its 2024-04-30 creation, one unaddressed open issue, no activity since.

`CorrectRoadH/docker-logseq` is the only real candidate between the two — but worth being honest that even it is a small, lightly-used project (9 stars, essentially one maintainer plus one contributor), so this stays in "unofficial community pattern" territory regardless of which image gets picked; not something with broad verification behind it.

Real caveats before this becomes the plan (not yet resolved): unofficial/unsupported deployment mode (crashes, LogSeq updates breaking Sync, would need a restart policy/health check like any other JCTsh Docker service); heavier footprint than the M8's other Docker apps (NetAlertX, Immich, hike-izer-web are lightweight web services, a full Electron+Chromium container is not); the HTTP API must stay off `hikes.jctnet.com`'s Cloudflare Tunnel — localhost/Tailscale-only, same posture as everything else on the M8.
- Relationship to the existing kanban pipeline: **alongside, not a replacement.** CARD-0151/0173's voice-idea → email → kanban PR path stays as-is for actionable work items. LogSeq becomes a second destination for looser notes/thoughts that aren't necessarily a card.
- Routing (how the pipeline tells "this is a LogSeq note" apart from "this is a kanban idea"): leaning toward a second Gmail plus-alias (e.g. `joscthomas+logseq@gmail.com`) alongside the existing `+kbc` one, so which inbox it lands in decides the route with no parsing needed — **but Joseph flagged this as still undecided**, not locked in.

**Acceptance criteria:** not yet written — the LogSeq-folder-access mechanism above needs to be resolved first; real acceptance criteria depend on which mechanism gets picked. Revisit at Planning.

**Done when:** a voice note sent to the LogSeq-routed address lands as a note in Joseph's actual LogSeq graph, verified live (not just "the pipeline ran without erroring").

**Related:** CARD-0151 (email-to-kanban-card watcher this reuses/sits alongside), CARD-0173 (voice idea capture, Pixel to kanban PR — the existing pipeline this is *not* replacing).

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

### CARD-0172 · [idea] [infrastructure] Disaster Recovery — auto-opened from jctsh-core — RESOLVED 2026-08-16 19:30 MST
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-08-22 (CARD-0193) — 9049B, over the 5000B size threshold.

---

### CARD-0171 · [enhancement] [infrastructure] M8 UEFI Secure Boot KEK CA firmware update available — auto-opened from photo-server — RESOLVED 2026-08-16 19:00 MST

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

### CARD-0170 · [enhancement] [infrastructure] Container image updates: home-assistant: 2026.8.2 available (running 2026.8.1) — auto-opened from jctsh-core — RESOLVED 2026-08-16 18:00 MST

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

### CARD-0168 · [bug] [homeassistant] Remove deprecated `http:` YAML block, resync stale configuration.yaml — RESOLVED 2026-08-15 02:28 MST
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

**Verified and resolved, 2026-08-15 02:28 MST.** Checked the live migrated config directly (`.storage/http` on the Pi, via `sudo cat`) before touching anything: `use_x_forwarded_for: true` and `trusted_proxies: ["127.0.0.1/32", "::1/128"]` both confirmed carried over correctly, `yaml_migration_done: true` — didn't just trust the warning text. Removed the `http:` block from the live `configuration.yaml`.

**Restart hit the known s6-supervised gotcha** (`docker restart` failed — "tried to kill container, but did not receive an exit event"; container exited but didn't auto-restart despite `unless-stopped`) — recovered with a plain `docker start`. Docker's own healthcheck reported `healthy` well before HA's actual startup finished (`/api/config` showed `state: NOT_RUNNING`, only 127 of the eventual 772 entities loaded, `automation.*` domain briefly empty) — waited for `state: RUNNING` before treating anything as confirmed, avoiding a false "it's broken" read on `automation.card_0145_ring_motion_announcement` mid-boot.

**All "Done when" criteria verified live, not just configured:** `.storage/http` unchanged post-restart (`error: null`); nginx-fronted HTTPS login (`https://pi1.tailfe828a.ts.net/`) returns HTTP 200; HA logs since the restart contain no "ignored after migration" warning; `automation.card_0145_ring_motion_announcement` reloaded correctly with its trigger history intact; repo's `core/homeassistant/configuration.yaml` diffed byte-for-byte identical against the live file (no edit needed — the repo copy already lacked the block).

**Related:** CARD-0096 (the rename that put nginx in front of HA), CARD-0141 (HA HTTPS/reverse-proxy setup this trust config supports), CARD-0145 (automation whose survival through this restart was directly verified).

---

### CARD-0167 · [enhancement] [infrastructure] Close CARD-0096's mDNS transition-window aliases — RESOLVED 2026-08-17 12:11 MST
**Status:** Done

**Raised 2026-08-14 16:15 MST**, split out from CARD-0096 (Done) so this last step doesn't get lost inside an already-closed card. Two systemd units are still deliberately running: `raspberrypi-mdns-alias.service` (Pi) and `photo-server-mdns-alias.service` (M8), each publishing the old hostname as a static mDNS alias for the unchanged real IP, per CARD-0096's own transition-window design.

**Due date reasoning:** 2026-08-17 (Monday) 09:00 MST — chosen specifically so both hosts' weekly scheduled reboots (Pi Mon 3:00 AM, M8 Mon 4:00 AM — `jctsh-network.md`) happen first. A clean reboot survival is a real stability test, not just elapsed time — if anything were silently still depending on the old name in a way the alias masks, a reboot is exactly the kind of event likely to surface it. 09:00 gives buffer after both.

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

### CARD-0166 · [enhancement] [infrastructure] Synchronize room/area names across HA, Google Home, and SmartThings — HA as master
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

### CARD-0164 · [enhancement] [infrastructure] Samsung ending free SmartThings API access October 2026 — decide pay vs. migrate before then
**Status:** Backlog

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

**Done when:** a direction is chosen (pay, migrate, or hybrid) and, if migrating any devices, each migrated device is confirmed still working via its new integration path before its SmartThings entity is retired — never cut over blind.

**Related:** CARD-0146 (the investigation that surfaced this), `ENVIRONMENT.md` (SmartThings device inventory), CLAUDE.md's SmartThings Integration section.

---

### CARD-0163 · [bug] [logging] Non-heartbeat log entries can get stuck unflushed indefinitely in log_server.py's `_pending` buffer — RESOLVED 2026-08-14 08:30 MST
**Status:** Done

**Found 2026-08-14 08:17 MST**, while verifying CARD-0161's webhook fix in production. A real, correctly-signed NetAlertX "New device detected" webhook was captured live: HMAC verification confirmed correct three independent ways (Node-RED's own JS re-verification, an independent Python recomputation, and a direct MQTT capture on `jctsh/components/netalertx/log` showing the exact right message with correct event-time). The message never appeared on the log dashboard or in `jctsh.log` despite all of that working correctly — the webhook/Node-RED pipeline was not the problem.

**Root cause, found by reading `log_server.py` directly:** `_store_entry()` buffers every *non-heartbeat* message (any component, any category) in a single-slot module-level `_pending` variable. It only gets written to `_entries`/disk when a **different** `(component, category, message)` arrives afterward and triggers `_flush_pending()`. Heartbeat-prefixed messages go through a completely separate mechanism (`_hb_groups`) and never touch or flush `_pending`. Confirmed live: `state.json`'s `_last_seen.netalertx` held the exact right entry (`count: 3`, correctly deduping two manual replays against the original) — sitting correctly in memory, genuinely never flushed, because nothing else non-heartbeat happened anywhere in the system afterward to bump it out.

**Same class of bug as CARD-0068/CARD-0079, but not covered by that fix.** Those cards added a 15-minute forced-rotation timeout specifically for `_hb_groups` (stuck heartbeat-collapse groups). The general `_pending` singleton has no equivalent timeout safeguard — any single non-heartbeat message, from any component, can sit invisible on the dashboard indefinitely if no other differing message happens to arrive after it. Not netalertx-specific and not webhook-specific; it's a gap in the core buffering logic any component's Alert/System/Sensor message could hit.

**Built and verified live, 2026-08-14:** added `PENDING_MAX_AGE_SEC = 60` and `_flush_aged_pending()` (mirrors `_flush_aged_hb_groups()`'s pattern exactly) to `core/logging/log_server.py`. Deliberately much shorter than `HB_GROUP_MAX_AGE_SEC`'s 15 minutes — these are discrete one-off events meant to be promptly visible, not a collapsing counter tuned for a steady heartbeat stream. The periodic flush thread (renamed `_hb_flush_thread` → `_flush_thread` since it now covers both) checks every `HB_FLUSH_CHECK_INTERVAL` (60s), so worst-case latency is ~60-120s, not indefinite. `_flush_pending()` also fixed to strip the new internal `_started_at` field before writing to `_entries`/disk, matching `_flush_hb_group()`'s existing pattern.

Deployed (`scp` + `sudo systemctl restart jctsh-logging`), confirmed clean restart (`Restored 1000 entries, 10 known components` — state survived). **Live test**: published a one-off Alert message with nothing else to bump it out — confirmed absent from `jctsh.log` immediately after (correctly still pending), then confirmed present after the periodic thread caught it, landing within the expected ~60-120s window. Exactly the failure mode this fixes, reproduced and verified closed.

**Related:** CARD-0161 (webhook fix verification that surfaced this), CARD-0068/CARD-0079 (the analogous `_hb_groups` timeout fix this generalizes), CARD-0078 (original webhook HMAC workaround, confirmed unaffected by this bug), `core/logging/log_server.py`.

---

### CARD-0162 · [enhancement] [tos] PR-to-kanban-card landing process for CARD-0128 auto-opened findings — RESOLVED 2026-08-14 07:28 MST
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6679B, over the 5000B size threshold.

---

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

### CARD-0160 · [enhancement] [infrastructure] Container image updates: cloudflared: 2026.8.2 available (running 2026.7.3) — auto-opened from photo-server — RESOLVED 2026-08-14 07:39 MST
**Status:** Done

**Auto-generated 2026-08-14 06:30 MST from photo-server's maintenance check (PR #11).** Raw finding: Container image updates: cloudflared: 2026.8.2 available (running 2026.7.3). Landed as a real kanban card via the old `resolve_and_merge()` path before the interviewed `land_pr_card.py` process (CARD-0162) existed — this note backfills the research and verification that process would normally require up front.

**Risk research (checked against cloudflared's actual GitHub releases, not just the raw finding):** `2026.7.3` → `2026.8.0` → `2026.8.1` → `2026.8.2`. Both `2026.8.0` and `2026.8.1` shipped with explicit "Do not use this version" warnings from Cloudflare — `2026.8.0` strips trailing slashes from HTTP-origin requests, causing redirect loops for anything needing canonical trailing-slash URLs (`cloudflare/cloudflared#1717`); `2026.8.1` normalizes request paths, breaking apps that need the raw encoded URL (`cloudflare/cloudflared#1719`). `2026.8.2` is the fix for both, with no further warnings. So this update lands past two known-bad releases straight onto the one that fixes them, not just a routine bump.

**Built and verified live, 2026-08-14 07:39 MST:** baseline confirmed (`hikes.jctnet.com` → HTTP 200 on `cloudflared:latest` pulled 2026-07-23, i.e. `2026.7.3`) before touching anything. `docker compose pull cloudflared && docker compose up -d cloudflared` on the M8 (`~/hike-izer-web-app`). Post-update: `cloudflared version 2026.8.2` confirmed via `docker exec`, tunnel reconnected clean (4/4 edge connections registered, connectivity pre-checks all PASS, `quic` protocol), and — specifically checking for the exact regression class `2026.8.2` fixes — `hikes.jctnet.com` returns `HTTP 200` both with and without a trailing slash, no redirect loop.

**Related:** CARD-0094 (original Cloudflare Tunnel setup), CARD-0162 (the interviewed PR-landing process this update predates), `components/hike-izer-web/docker-compose.yml`.

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

**Raised 2026-08-12 17:54 MST**, Joseph's request mid-session while reviewing the existing auto-select duplicate logic.

**What "done" looks like:** For each year in the review UI, any duplicate group that is:
- exactly 2 members, one in Joseph's Immich library and one in Robin's,
- identical `originalFileName`,
- identical `fileCreatedAt`,
- identical file size,
- czkawka `difference: 0` for both members (exact perceptual-hash match — the same qualifying signal the existing cross-account tie-breaker in `maybeAutoSelectGroup()` already uses),
- and not already decided,

...gets pulled out of the normal per-group Duplicates list for that year (the individual photos are never rendered) and instead counted into a single "Super Rule" summary box: total count + one "Delete all in Robin's library" button.

**Album-check gate (Joseph's call, interviewed live):** before a candidate qualifies, still check each member's Immich album membership (same live `/api/albums/:assetId` call the normal auto-select flow already makes) — if Robin's copy is the one linked to an album and Joseph's isn't, exclude that pair from the Super Rule bucket entirely (falls back to normal per-group manual review, same as today) rather than deleting something that would silently lose an album link. Motion Photo video-integrity checks are explicitly **not** part of this gate — ignored for this rule, unlike normal auto-select.

**Delete action:** clicking "Delete all in Robin's library" deletes Robin's copy of every qualifying photo via the existing Immich delete pipeline (soft-trash, `force: false`, same as Confirm & Delete) and logs each to the existing deletion-log CSV/Sheet, same as every other deletion path in this app. Joseph's copy is always the one kept.

**Explicitly open for the build:** whether the button gets its own confirmation step — "don't show the photos" rules out a Preview-style itemized list, but some in-page confirmation (count + an explicit second click) is still expected before an irreversible-feeling bulk action.

**Built, deployed to the M8, and verified live.** Confirmation modal deliberately count-only (no itemized list, per "don't show the photos"), reusing the existing `/api/decide/duplicate` + `/api/confirm` pipeline rather than a new delete path.

**Found and fixed live during first real use:** the bulk "Delete all" button scoped `/api/confirm` to every qualifying groupKey for the year in one request — fine for the normal per-page Confirm & Delete flow (capped at ~100 groups by pagination) but not for this button, which can legitimately scope thousands. A real 2,529-group year 413'd (`PayloadTooLargeError`, Express's default 100kb JSON body limit) *before* the request reached the route handler, so nothing was deleted and nothing was corrupted — only the (harmless, idempotent) per-group decide calls had already landed. Raised `express.json()`'s limit to 5mb in `server.js`. Verified by replaying the exact same oversized payload against the fixed server (200 OK, all 2,529 items resolved correctly), then Joseph re-ran Confirm & Delete live: all 2,529 deleted from Robin's library, logged correctly, `decisions.json` left valid with the resolved groupKeys cleared.

**Related:** `components/photo-quality-review/public/review.js`'s existing `maybeAutoSelectGroup()` cross-account tie-breaker (2026-08-08) — this is a stricter, UI-different variant of the same underlying "identical size + diff 0, keep Joseph's copy" rule, scoped per-year and skipping individual review entirely instead of auto-checking a radio button.

---

### CARD-0154 · [idea] [hiking-monitor] DIY Li-ion overcharge-cutoff circuit (Hackster.io) — evaluated, not applicable
**Status:** Done

**Raised 2026-08-12 21:55 MST**, auto-opened from an email Joseph forwarded to `joscthomas+kbc@gmail.com` via CARD-0151's new email-idea watcher (the first real card this pipeline produced) — the article: [DIY 3.7V Lithium Battery Automatic Charger Circuit](https://www.hackster.io/electroniclovers/diy-3-7v-lithium-battery-automatic-charger-circuit-7dda92).

**Interviewed 2026-08-12 22:05 MST.** Joseph's real question: given several past conversations about battery charging for JCTsh's battery-powered builds, could this circuit replace or improve on what's already in use.

**Circuit fetched and evaluated** (WebFetch was blocked by Hackster.io's bot protection; retrieved via a reader-mode proxy instead): a discrete overcharge-**cutoff** add-on, not a full charger — LM358 op-amp as a voltage comparator, BD140 PNP transistor as a high-side switch, Zener reference + trim pot set the 4.2V threshold, hysteresis resistor to avoid chatter at the cutoff point. When the cell hits 4.2V, the comparator flips and the transistor hard-cuts charging current. That's the entire function — no CC/CV charge-current regulation, no boost/buck conversion, no solar input handling.

**Compared against real current hardware, not the stale doc first checked.** `components/hiking-monitor/power-system.md` (TP4056+boost, 5V boost output to ESP32 VIN) turned out to be out of date — Joseph corrected this: CARD-0070 (`Replace boost converter with LDO + gate peripheral power for lower standby draw`) already replaced that path. TP4056 stays exactly as-is for charging (regulation + solar input, unchanged); only the boost stage was removed, since boosting to 5V just to have the ESP32's own onboard regulator step it back down to 3.3V was wasteful — measured at 22.6mA quiescent draw, the dominant factor in a ~2-day standby life. Replaced with an LDO tapping the battery+ node directly, feeding the ESP32's 3V3 pin, plus a P-FET to gate peripheral power during sleep.

**Conclusion: not applicable, reference only.** CARD-0070's LDO swap is about the *discharge* side (delivering battery power to the ESP32 efficiently) — a different part of the system than what this article addresses (the *charge* side, terminating charging safely at 4.2V). TP4056 already handles that unchanged, with full CC/CV regulation and solar input support this discrete circuit doesn't have. The article's circuit wouldn't replace or improve on anything currently in use; it would just be a more primitive, worse-equipped version of what TP4056 already does. No action needed beyond this evaluation.

**Related:** CARD-0151 (the email-watcher that opened this card), CARD-0070 (the real current power-path design this was evaluated against), CARD-0026/0027 (the standby-current measurements CARD-0070 was built on), `components/hiking-monitor/power-system.md` (now known stale re: the boost stage -- worth a correction pass if anyone reads it expecting current behavior, not opened as a separate card here since it is a docs-accuracy nice-to-have, not blocking anything).

---

### CARD-0153 · [idea] [homeassistant] Move HA recorder off SQLite to MariaDB (or Postgres) if it ever becomes a real problem
**Status:** Backlog

**Raised 2026-08-12**, from Joseph reading an article about SQLite concurrency/write-lock issues under Home Assistant and asking whether JCTsh's HA instance should move off it.

**Why SQLite can be a problem, for context:** SQLite locks at the whole-database-file level — even in WAL mode (which HA enables by default), only one write transaction can be in flight at a time, so every other writer queues behind it. Under a heavy install (many entities, frequent automations), the recorder's write queue can back up behind that single-writer lock, worse on slow storage like a Pi's SD card. MariaDB (InnoDB) and PostgreSQL instead lock at the row level and use MVCC, so a write and a concurrent read (e.g. the frontend loading a history graph) don't block each other — real client-server databases built for concurrent multi-client load, unlike SQLite's embedded single-writer model.

**Explicitly not being pursued now.** Checked whether this JCTsh instance actually has the problem: the "could not validate shutdown cleanly" / "ended unfinished session" recorder warnings seen in `docker logs` during CARD-0150/0152's testing this session were almost certainly artifacts of repeated fast `docker restart` cycles (SQLite doesn't get time to flush before SIGTERM) rather than evidence of a real concurrency problem during normal operation. At JCTsh's current scale (modest entity count, not a heavy-automation install), SQLite's single-writer limitation isn't expected to bite. Joseph's call: leave it as SQLite, watch for real symptoms.

**Trigger conditions for actually pursuing this** (either one): recorder errors appearing during *normal* operation (not around a deliberate restart), or the History/Logbook UI becoming noticeably slow. Neither has been observed.

**If pursued, one option discussed:** run the database as its own container on the M8 (`photo-server`, `192.168.1.165`) rather than on the Pi, since HA's `recorder:` config accepts any reachable `db_url` — the M8 is already running Docker and is more capable than the Pi. Two real snags flagged, not yet resolved:
1. HA's official Docker image doesn't bundle a PostgreSQL/MariaDB Python driver by default — would need a custom image or an init step to install one.
2. Creates a new cross-device dependency that doesn't exist today — HA's recorder would go dark any time the M8 is unreachable, including the M8's own weekly scheduled reboot (Mon 4am) — worth checking that window against the Pi's own Monday 3am reboot stagger (see `jctsh-network.md`'s Scheduled Maintenance Windows table) if this is ever built, since the whole point of that stagger was avoiding a different false-down reading and a DB dependency adds a second reason to care about the timing.

**Done when (if ever picked up):** not yet defined — this card is parked as an idea, not scoped for Planning. Needs a real interview (which engine, where hosted, migration approach for existing history data, backup coverage) before any implementation starts.

**Related:** `jctsh-network.md` (M8 host details, maintenance-window table).

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

**Raised 2026-08-11**, after Joseph asked about a rescan's completion notification (38,258 duplicate groups) and wanted to know whether that was more than the previous scan turned up -- there was no way to tell, since `scan.js` overwrites `report.json` in place on every run, with no history kept.

**Scope: retention only, not comparison.** Joseph explicitly deferred the diff/comparison half ("38,258 duplicate groups (312 new since last scan)" in the notification) to build later -- this card is just making sure the data exists to compare against, not building the comparison itself.

**Design:** confirmed `groupKey()` (`server.js`) is already stable across rescans -- it's the sorted set of member asset IDs, not scan order or position, so two snapshots really can be diffed meaningfully once this exists. Before `scan.js` overwrites `report.json`, move the existing one into a new `data/report-history/` subdirectory under a filename timestamped from *that report's own* `generatedAt` field (not "now" -- "now" is when it's being retired, not when it was actually generated). `report.json` stays the one filename the app reads; nothing else in `server.js` changes. Deliberately no pruning/retention cap for now -- each snapshot is ~36MB and scans look ad-hoc/infrequent (this was the first rescan since the app's original build), so it would take dozens of scans before size is worth worrying about; simpler to add a cap later if it actually becomes a problem than to guess at a number now.

**Done when:** `scan.js` archives the previous `report.json` into `data/report-history/` (timestamped from its own `generatedAt`) before writing a new one, deployed to the M8, and verified with a real scan run that the history file lands correctly and `report.json`/the app itself are unaffected.

**Built 2026-08-11.** New `archivePreviousReport()` in `scan.js`, called right before the final `fs.writeFile(REPORT_PATH, ...)`: reads the existing `report.json`, pulls its `generatedAt` (falls back to current time if the file's malformed/older-format), then `fs.rename`s it into `data/report-history/report-<timestamp>.json` -- a same-filesystem move, not a copy, so no need to duplicate a ~36MB file on disk just to relocate it.

**Verified in isolation against real Node on the M8, not just "code looks right"** -- `scan.js` itself runs a full ~12.6-minute real scan with no way to unit-test just this one function in place (no `require.main` guard, importing it kicks off the whole scan), so the exact function body was run standalone against synthetic data in a scratch directory: (1) first-ever scan, no existing `report.json` -- no-op, no error; (2) normal case, valid `generatedAt` -- correctly archived as `report-2026-08-10T13-38-44.864Z.json`, original `report.json` confirmed gone; (3) malformed JSON -- falls back to a current-time stamp rather than crashing; (4) repeated archiving -- no filename collisions, all snapshots preserved distinctly. Deployed to `~/photo-quality-review/scan.js` on the M8 (syntax-checked with real `node -c` first), test scratch directory cleaned up afterward.

**Closed out 2026-08-11 on Joseph's go-ahead -- "leave it, it'll run naturally."** Not yet exercised end-to-end against a real scan run (`scan.js` isn't a persistent service, so no restart needed either -- it just takes effect on the next invocation); deliberately not forced today given the isolated test already covers the actual logic faithfully and a full run costs ~12.6 minutes. Real end-to-end proof arrives the next time a rescan runs naturally -- reopens under a fresh card if the history file doesn't land correctly then.

**Related:** CARD-0028 (the review app this extends), CARD-0148 (same component, prior round), `components/photo-quality-review/scan.js`.

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

**Raised 2026-08-05 07:57 MST:** Joseph wants each entry on the Wildlife Life List (CARD-0142) to link somewhere showing a photo and more information about that species.

**Approach recommended by Claude, confirmed by Joseph:** link to that species' English Wikipedia article, built directly from its `scientific_name` (spaces -> underscores, URL-encoded) -- e.g. `https://en.wikipedia.org/wiki/Progne_subis`. Rejected alternative: a custom page built from Joseph's own trail photos -- most life-list entries are audio-only BirdNET detections with no corresponding photo, so most species would end up with an empty page; Wikipedia guarantees a populated page (photo + description) for every entry today, and works uniformly across taxa (the list already includes non-birds like Coyote and American Bullfrog, ruling out a birds-only source like Cornell's All About Birds). No link-verification at build time (no HTTP call, no new failure mode in an otherwise pure-local render step) -- constructed optimistically, same "best-effort" philosophy already used elsewhere in this pipeline; Wikipedia's own redirects/search cover the rare mismatch.

**Scope:** `build_wildlife_index.py`'s per-species row gets a new "More Info" column linking to the constructed Wikipedia URL (`target="_blank" rel="noopener"`, since it leaves the site) -- distinct from the existing "First Heard" column, which stays an internal link to that species' first hike page.

**Done when:** every row on the live `https://hikes.jctnet.com/wildlife.html` has a working Wikipedia link for its species, confirmed against a sample of real entries (including at least one non-bird), deployed to the M8.

**Built, deployed, and verified live, 2026-08-05 08:03 MST.** New `_wikipedia_url()` helper in `build_wildlife_index.py`; new "More Info" column added to the species table (`target="_blank" rel="noopener"`). Verified before deploying: URL construction checked against both bird and non-bird scientific names, then spot-checked live against real Wikipedia (`Progne_subis`, `Canis_latrans`, `Lithobates_catesbeianus`, `Cyanocitta_cristata` all returned HTTP 200).

Deployed to the M8 (`scp` + `docker compose up -d --build orchestrator`), then rebuilt `wildlife.html` from the existing persisted life list (no data change needed, `wildlife_life_list.json` already had all 31 species from CARD-0142). Confirmed live: all 31 rows on `https://hikes.jctnet.com/wildlife.html` carry a unique, correctly-formed Wikipedia link, including the two non-bird entries (Coyote -> `Canis_latrans`, American Bullfrog -> `Lithobates_catesbeianus`).

**Revised, 2026-08-05 08:05 MST (Joseph's call):** dropped the separate "More Info" column -- the Wikipedia link now lives directly on the Common Name cell instead (`target="_blank" rel="noopener"` carried over). Re-deployed and re-verified live: `wildlife.html`'s header row is back to four columns (Common Name, Scientific Name, First Heard, Hikes), and e.g. "Coyote" links straight to `Canis_latrans` on Wikipedia.

**Related:** CARD-0142 (the Wildlife Life List this adds to), `components/hike-izer/build_wildlife_index.py`.

---

### CARD-0142 · [enhancement] [hike-izer] Cross-hike Wildlife Life List
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6345B, over the 5000B size threshold.

---

### CARD-0141 · [enhancement] [hike-izer] Push notification to Joseph's Pixel on hike-summary publish success/failure
**Status:** Done

**Raised 2026-08-05 07:30 MST:** today `hike-izer-orchestrator` only reports publish success/failure via an MQTT log line (`jctsh/hike-izer/publish/log`), which only surfaces on the log dashboard -- nothing pushes to Joseph's phone the way the existing heartbeat watchdog already does for component silence. Joseph wants the same HA-companion-app push-notification pattern extended to hike-summary generation itself.

**Scope, decided 2026-08-05 (Joseph's call):**
- Notify on **both** success and failure (not success-only) -- mirrors the existing MQTT System/Alert split in `generation.py`'s `run_and_log()` (step 1) and `run_step2_and_log()` (step 2).
- **Joseph's Pixel only** (`notify.mobile_app_pixel_10_pro_xl`) -- hike-izer is single-user, no reason to also notify Robin's phone the way some other JCTsh automations do.
- New `components/hike-izer-orchestrator/ha_notify.py`, same "best-effort, log-and-continue" convention as `mqtt_log.py` -- a push-notification failure must never break generation itself.
- Reuses the existing shared `HA_TOKEN` (`credentials.local.md` → "Home Assistant") -- no new token minted. New `HA_URL` env var pointed at the Pi's LAN IP (`http://192.168.1.117:8123`), not `raspberrypi.local` (mDNS unreliable cross-host) -- matches `mqtt_log.py`'s own hardcoded `BROKER = "192.168.1.117"`, already confirmed working live from this same M8 orchestrator container to reach the Pi, so no new cross-host reachability assumption is being introduced.
- Wired into both existing call sites in `generation.py` alongside (not replacing) the existing `mqtt_log.publish_log()` calls.

**Done when:** `ha_notify.send_push()` exists and is called from both success and failure branches of `run_and_log()` and `run_step2_and_log()`; `HA_TOKEN`/`HA_URL` are set in the M8's orchestrator `.env` and documented in `credentials.local.md`; the orchestrator is rebuilt/redeployed; and a real push notification is confirmed arriving on Joseph's Pixel (a direct `ha_notify.send_push()` test call is sufficient to verify the HA_URL/HA_TOKEN/notify-service mechanism itself -- the next real hike will exercise the generation-pipeline call sites for real, same as any other day-one code path).

**Built, deployed, and verified live, 2026-08-05 07:33 MST.** New `components/hike-izer-orchestrator/ha_notify.py` (`send_push(title, message)`, best-effort/log-and-continue, same convention as `mqtt_log.py`) calling `notify.mobile_app_pixel_10_pro_xl` via HA's REST API. Wired into both success and failure branches of `generation.py`'s `run_and_log()` (step 1) and `run_step2_and_log()` (step 2), alongside the existing `mqtt_log.publish_log()` calls. `Dockerfile` updated to copy the new module.

Deployed: `scp`'d `ha_notify.py`, `generation.py`, `Dockerfile` to `~/hike-izer-web-app/orchestrator/` on the M8 (via its Tailscale IP -- `.local` mDNS and the LAN IP were both unreachable from this Windows machine, same finding as CARD-0140), appended `HA_TOKEN` (reused shared token) and `HA_URL=http://192.168.1.117:8123` (the Pi's LAN IP -- same address `mqtt_log.py`'s own hardcoded `BROKER` already reaches successfully from this container) to the M8's shared `.env`, then `docker compose up -d --build orchestrator`. Documented both new vars in `credentials.local.md`.

Verified with a direct `ha_notify.send_push()` test call from inside the rebuilt container -- Joseph confirmed the push notification arrived on his Pixel 10 Pro XL. The generation-pipeline call sites themselves will get exercised for real on the next hike (same code path as the pre-existing MQTT logging, not separately re-tested end-to-end here).

**Related:** `core/node-red/watchdog.flow.json` / `core/node-red/watchdog-README.md` (the existing HA-companion-app push pattern this reuses), `components/hike-izer-orchestrator/generation.py` (`run_and_log`, `run_step2_and_log`), `components/hike-izer-orchestrator/mqtt_log.py` (the existing best-effort logging convention `ha_notify.py` mirrors), CARD-0140 (the same session's fix, same Tailscale-IP-for-deploy finding), CARD-0086 (automatic triggering, the pipeline this extends).

---

### CARD-0140 · [bug] [hike-izer] GPS accuracy noise falsely triggers "sustained non-walking pace" truncation, excluding real hike time from stats
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6885B, over the 5000B size threshold.

---

### CARD-0139 · [enhancement] [log-server] Exclude bench-test/dev components from the /status dashboard
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

**Raised 2026-08-03 17:40 MST**, found while working CARD-0137 (log-server status-display bug): `hiking-monitor`'s retained `jctsh/components/hiking-monitor/status` correctly reads `offline` (both units have been unpowered on the workbench for over a week, `hiking-monitor` even longer than `hiking-monitor-test`), but `hiking-monitor-test/status` was stuck retained at `online` — confirmed directly via `mosquitto_sub --retained-only`, not just a dashboard-display issue (CARD-0137 fixed the log server's handling; this is the broker's own retained value being factually wrong). Manually corrected with a one-off retained publish (`mosquitto_pub ... -t jctsh/components/hiking-monitor-test/status -m offline -r`) so the dashboard reflects reality now — confirmed live, `hiking-monitor-test` shows `Disconnected` as of this publish. That's a point-in-time fix only; it'll go stale again exactly the same way if the underlying device-side cause isn't fixed before the unit is ever reconnected and disconnected again.

**Partial investigation, not a full diagnosis:** `components/hiking-monitor/hiking-monitor.yaml`'s `mqtt:` block overrides `will_message` to target `jctsh/components/hiking-monitor/log` (a connection-event log message: `{"category":"MQTT","message":"MQTT disconnected"}`) rather than the `/status` topic at all — `on_connect` similarly publishes its own "MQTT connected"/"Hiking monitor online..." lines straight to `/log`, not through ESPHome's built-in availability mechanism. Despite that override, `hiking-monitor/status` still correctly resolves to `offline` in practice — the exact ESPHome-internals reason why (whether a default `/status` Will still gets registered underneath a custom `will_message`, or something else entirely) wasn't traced with certainty; flagged here rather than guessed at further.

**Open hypotheses to check, not yet confirmed:**
1. `hiking-monitor-test` might be running older/different firmware than the current `hiking-monitor.yaml` (no separate `hiking-monitor-test.yaml` exists in the repo — worth confirming what's actually flashed on that physical unit).
2. The stale `online` value could simply be old residue from before the current `will_message` setup existed on that unit, rather than evidence of an active ongoing config problem — i.e. it may correct itself cleanly the next time that unit actually reconnects, without needing a firmware change at all.
3. If it turns out to be a genuine config gap, compare against `hiking-monitor.yaml`'s real, current MQTT block field-by-field once the actual flashed firmware is known.

**Done when:** it's understood *why* one unit's `/status` self-corrected on disconnect and the other's didn't, and (if a real firmware/config difference is confirmed) `hiking-monitor-test` is reflashed or reconfigured to match, verified by actually power-cycling it and confirming `/status` flips to `offline` on its own, no manual retained-publish workaround needed.

**Deferred 2026-08-03 17:46 MST — wrong problem, not worth solving.** Joseph's own framing reset this: `hiking-monitor-test` is a bench test rig, not a deployed asset — it was only ever showing up on `/status` because `log_server.py` tracks anything that happens to publish to the watched MQTT topics, with no concept of "this isn't a real monitored component." Chasing why its firmware doesn't self-correct its LWT was solving the wrong layer — the actual fix is CARD-0139 (exclude test-bed components from the dashboard entirely), which makes this card's whole question moot. Not abandoned as in "forgot about it" — a deliberate call that this was never worth fixing in the first place.

**Related:** `components/hiking-monitor/hiking-monitor.yaml`, CARD-0137 (the log-server-side bug this is distinct from — that one's Done), CARD-0139 (the actual fix — exclusion, not firmware correction), `core/logging/log_server.py` (`_connection_state`, the new Connection column this bug is now visible through, accurately, for the first time).

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

### CARD-0131 · [enhancement] [infrastructure] Immich update available: v3.1.0 (currently running v3.0.1) — auto-opened from photo-server
**Status:** Done

**Auto-generated 2026-07-31 23:01 UTC from photo-server's maintenance check.** Raw finding: Immich update available: v3.1.0 (currently running v3.0.1).

**Scoped 2026-08-01 — release notes reviewed before deciding, not just applied blindly.** Pulled the real release bodies via the GitHub API (not an AI-summarized fetch — an earlier WebFetch attempt got the release years wrong, 2024 instead of 2026, so it wasn't trusted) for v3.0.2, v3.0.3, and v3.1.0 (the three releases between the running version and the target). Only breaking change across all three: v3.1.0 drops iOS 14 support on the *mobile app* — irrelevant to the server. No database migration or schema change mentioned in any of the three. v3.0.2 added a fix wrapping migrations in a transaction (a safety improvement, not a new required step); v3.0.3 noted a narrow, self-healing Live Photos thumbnail caveat (fixed by the nightly job). Nothing resembling the CARD-0037/0042/0043-era bugs `operations.md` warns Immich has shipped before. Judged low-risk enough to do remotely, same reasoning as CARD-0095's M8 reboot (which was also done remotely without incident) — unlike the Pi's CARD-0129, an Immich container update never touches host networking/SSH/Tailscale, so remote access isn't at stake regardless of outcome.

**Built and verified live, 2026-08-01:** pre-checked all four containers healthy on v3.0.1 (`docker compose ps`, `/api/server/version`) before touching anything. `docker compose pull && docker compose up -d` in `~/immich-app` — only `immich-server` and `immich-machine-learning` recreated (Postgres/Valkey stay pinned by digest per this repo's own convention, untouched). Both back to `healthy` within ~1 minute. `/api/server/version` confirmed `3.1.0`. `immich-server` startup log clean — no errors/warnings, "Adding 3.1.0 to upgrade history," Nest application started successfully. Re-ran `immich-update-check.py` afterward: reports "Up to date: v3.1.0" and correctly re-published the retained pending-update state as `pending=False` — confirmed via CARD-0132's own mechanism, closing the loop between the two cards.

**Related:** CARD-0132 (the Pending Update mechanism this verifies), `components/photo-server/operations.md` (Immich update-check pattern, notify-only policy and its rationale), live dashboard entry at time of generation.

---

### CARD-0130 · [enhancement] [infrastructure] Container image updates: home-assistant: 2026.7.4 available (running 2026.5.1) — auto-opened from jctsh-core — RESOLVED 2026-08-13 21:50 MST
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

### CARD-0103 · [idea] [personal] Migrate 3 legacy Google Sites pages (Cochie Springs hike, Mustang, Karli's Summer) to the M8 webserver — low priority
**Status:** Backlog

**Raised 2026-07-27**, during CARD-0093 (DNS cleanup). CARD-0093's original plan let `jctnet.com`'s Google Sites content go entirely (Joseph had called it unimportant), but revisiting surfaced that 3 specific pages are still wanted — dropping the `www` CNAME and `google-site-verification` TXT as part of CARD-0093 will break their reachability at `jctnet.com`/`www.jctnet.com`, even though the underlying Google Sites content itself isn't deleted by a DNS change (it stays live at its own `sites.google.com` URL, just unmapped from the custom domain).

**Scope:**
- Export the source content (text/photos) for all 3 pages from the live Google Sites pages — content only exists there right now, not backed up elsewhere.
- Rebuild them as static pages served from the M8 (alongside the existing `hike-izer-web` static content / Caddy setup, or a sibling route — exact placement TBD at build time).
- **Done when:** all 3 pages are publicly reachable at a real URL again (not just archived files on disk) — final URL/path scheme (e.g. under the existing Tailscale Funnel domain, a new subdomain, etc.) is an open decision for whoever picks this up.

**Open question, deferred to this card (raised 2026-07-27 while resolving CARD-0093's Search Console question):** both `jctnet.com` and `jctnet.net` currently show zero indexed pages in Search Console, so CARD-0093 doesn't bother re-verifying/maintaining Search Console for the now-dormant `jctnet.com`. But once these 3 pages are actually live again on the M8, whether they should be discoverable/indexed by Google (i.e. set up Search Console for wherever they end up living) is a separate decision — not resolved, not urgent, revisit when this card is picked up.

**Priority:** Backlog, low — not blocking CARD-0093, which proceeds with full jctnet.com teardown (including the Google Sites CNAME/TXT records and the root A/parking records) regardless of when this is picked up. Google Sites keeps serving the content at its native URL in the meantime, so there's no hard deadline to act before CARD-0093 executes.

**Related:** CARD-0093 (the DNS cleanup that prompted this), CARD-0088/CARD-0092 (existing M8 static-hosting precedent via Caddy).

---

### CARD-0096 · [enhancement] [infrastructure] Rename photo-server → m8 and raspberrypi → pi1, adopt a real host-naming convention — RESOLVED 2026-08-14 16:15 MST
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

### CARD-0055 · [bug] [garage-presence] Reconcile garage-radar/SmartThings light control — lights sometimes don't turn on
**Status:** Backlog

**Notes:** Joseph reports lights sometimes don't come on when entering the garage. Found during a components-vs-backlog reconciliation pass (2026-07-11): the repo fully documents the "presence off" SmartThings routine (closes door, turns off lights — `garage-presence/CLAUDE.md`) but has **no documentation anywhere of the "presence on" routine** presumably responsible for turning lights on when `switch.garage_presence_vswitch` turns on. `garage-radar/README.md` and `garage-presence/README.md` both reference "lights on" only as an outcome label on the vswitch, never as a documented ST routine with its own trigger/conditions — it exists only inside the SmartThings app, unaudited.

**Known chain (from `garage-radar/integration-notes.md`):** LD2412 radar → `binary_sensor.garage_radar_presence` (30s `delayed_off` filter) → triggers HA's "Garage Presence - Restart timer on activity" automation → starts `timer.garage_presence_timer` and turns on `switch.garage_presence_vswitch` → HA is the sole owner of the vswitch state (SmartThings routines must not set it directly, since ST→HA sync is documented unreliable for other sensors — `garage-presence/CLAUDE.md`) → SmartThings observes the vswitch turning on and is presumed to fire a "lights on" routine, which is undocumented and unverified.

**Suspected failure points (not yet confirmed):**
- HA→SmartThings state propagation lag/unreliability for the vswitch itself — existing docs only warn about the *reverse* direction (ST→HA sync unreliable for `binary_sensor.back_door_door` and the PIR motion sensors); nothing confirms the HA→ST direction this flow actually depends on is solid.
- Radar/PIR detection gaps delaying the first `binary_sensor.garage_radar_presence` → on transition (same class of issue already documented for `binary_sensor.garage_motion_motion`/`garage_cam_motion` sticking in Arizona heat).
- Whatever conditions the SmartThings "presence on" routine actually has configured today — unknown, never captured in the repo.

**Resolution path:** (1) audit the SmartThings app directly to capture and document the actual "presence on"/lights-on routine (trigger, conditions, actions), mirroring how the "presence off" routine is already documented in `garage-presence/CLAUDE.md`; (2) next time lights fail to come on, correlate HA logbook history for `switch.garage_presence_vswitch` against SmartThings app history to determine whether the vswitch turned on but ST didn't react, or the vswitch itself never turned on; (3) once root cause is identified, fix it (likely an ST routine condition or a sync-timing issue) and add the missing documentation so this chain is fully traceable end to end.

---

### CARD-0045 · [bug] [hiking-monitor] `wifi.ap:` fallback may prevent `reboot_timeout` from working — RESOLVED 2026-08-27
**Status:** Done

**Resolved 2026-08-27, via CARD-0217's WiFi-disable work, with a simpler fix than the resolution path below ever proposed.** CARD-0217 (today's separate reset-crisis investigation) found and fixed the actual underlying gap this card was always circling: field mode never told the WiFi component to stop trying at all, `reboot_timeout`/`wifi.ap:` interaction aside. Once WiFi is genuinely disabled during field mode (switch on, dock off) and only re-enabled on a real dock event, this card's whole `reboot_timeout` question becomes moot — there's no unbounded retry loop for that ESPHome bug to ever interact with in the first place.

**The compounding solar/dock_detect risk (2026-08-20 reopening, 2026-08-23 compounding note) — closed the same day, by asking the right question instead of building the originally-planned mechanism.** The bounded-retry-every-15-20-minutes design below was about to be implemented for the case where `dock_detect` goes HIGH mid-hike from solar (switch still on) — until Joseph asked directly: *"What is the purpose of trying to connect wifi when in the field?"* Correct answer: none. Solar connecting mid-hike is a pure power event — it says nothing about network availability, and if anything correlates with being *further* from any network (solar is used for extended field time, not near-home charging), not closer to one. So the real fix isn't a smarter bounded retry, it's simpler: **only re-enable WiFi when the switch itself is off** — a deliberate "hike is over" signal — regardless of `dock_detect` state. `hiking-monitor.yaml`'s `dock_detect` on_state handler's `wifi.enable()` call now requires `binary_sensor.is_off: slide_switch` alongside the existing `App.is_setup_complete()` timing guard. Solar connecting while still hiking now correctly does nothing but charge the battery — no WiFi attempt, no retry cadence needed at all.

Compiled clean (`config_hash=0xb98022dc`, `build_time_str=2026-08-27 15:36:09 -0700`), OTA-flashed, confirmed clean reboot + MQTT reconnect. **Not yet verified against a real solar-connected-mid-hike event** — that's a genuinely rare real-world trigger (solar is only used on extended trips), so this is confirmed correct by direct code inspection and the same reasoning that closed the design conversation, not yet a live field observation. Low risk given the fix is a single added condition on an already-narrow, already-tested code path.

---

**Original card text, kept for the record below.**

**Notes:** Found 2026-07-09 while researching a timeout decision for air-quality-monitor (which follows hiking-monitor's firmware pattern). `hiking-monitor.yaml`'s `wifi:` block has no explicit `reboot_timeout` override, so it relies on ESPHome's default (15 minutes before rebooting on failed WiFi connection). However, ESPHome's own issue tracker (esphome/issues#7222) documents that `reboot_timeout` does not apply when a `wifi.ap:` fallback block is configured — and hiking-monitor's config does have one (`ap: ssid: "hiking-monitor-fallback"`). So the 15-minute default may not actually be functioning as designed on the currently-deployed device.

**Priority: low (original assessment, superseded below).** Hiking-monitor's upload/home mode requires USB dock power to stay awake (same architecture as air-quality-monitor's charging-based home mode) — if the bug does prevent the reboot from firing, the device would get stuck awake trying to reconnect, but on USB power, not draining battery. No confirmed real-world failure — CARD-0008's actual field test (2026-06-17 camping trip) succeeded without issue. Worst case is a minor operational annoyance (stuck device needing a physical USB reflash to recover), not data loss or a safety risk.

**Reopened 2026-08-20 11:12 MST — priority assessment was wrong.** Surfaced while designing air-quality-monitor's own solar/dock-detect handling (CARD-0012): the "USB dock power, not draining battery" reasoning above assumed dock-detect only goes HIGH at the physical home dock. It doesn't — hiking-monitor's SUNYIMA solar panel wires into the same `IN+`/`IN−` pads as the dock (`power-system.md`, `perfboard-layout.md`'s "IN+ / IN− — solar/USB charging input; IN+ also tapped for dock detect"). So dock-detect can go HIGH mid-hike, on battery, exactly the scenario this card's priority call assumed couldn't happen. If the `reboot_timeout`/`wifi.ap:` bug does prevent recovery, a solar-triggered stuck reconnect *would* drain field battery, with no dock nearby to physically reflash. Raising to **medium** — still no confirmed real-world failure (CARD-0008 succeeded, but that test wasn't solar-triggered), but the "no real cost" justification for deprioritizing no longer holds.

**Resolution path — concrete design from the air-quality-monitor solar/timeout work (2026-08-20), not yet implemented on hiking-monitor:** rather than relying on `reboot_timeout` at all (sidestepping the `wifi.ap:` interaction bug entirely instead of deciding whether to remove the AP fallback), decouple field sensor logging from dock-detect state — keep the sensor-read/SPIFFS-log loop (and e-ink field display) running unconditionally whenever the hiking switch is ON, regardless of dock-detect. Let dock-detect HIGH trigger only a background WiFi connection attempt, bounded to a ~2-minute window, then `wifi.disable()` rather than retrying indefinitely, then re-enable and retry roughly every 15–20 minutes for as long as dock-detect stays HIGH (no cap on the number of these periodic cycles). Only switch to actual replay+live-publish once WiFi and MQTT both actually connect. This is a change to already-deployed, field-proven firmware — treat as its own scoped implementation pass, not a quick edit; matching air-quality-monitor's parallel implementation (`air-quality-monitor-claude-code-instructions.md` Step 8) once that's built and field-tested may be the lower-risk order of operations, since it validates the approach on hardware that hasn't shipped yet first.

**Compounding risk found 2026-08-23 (CARD-0200) — this card's failure mode used to have zero backstop, now has one.** The low-battery safety cutoff was gated on the same `dock_detect` signal this card is about — meaning if this bug's stuck-retry scenario ever fired while solar was connected mid-hike, the cutoff was *also* silently disabled the whole time, so a stuck reconnect loop could have drained the battery to nothing with nothing to stop it. CARD-0200 fixed the cutoff side (now gated on field mode, not dock state) — this card (the actual unbounded-retry behavior) is still open and unfixed; the two together were a real failure chain, not independent risks.

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


### CARD-0114 · [enhancement] [kanban-board] Status field per card, replacing physical column position — RESOLVED 2026-07-29 16:28 MST
**Status:** Done

**Raised 2026-07-29 07:59 MST**, after tonight's CARD-0106/0108/0104 move to Done briefly corrupted a large stretch of `kanban-board.md` — a script assumed a fixed line-offset for the insertion point instead of a real content marker, and a second recovery attempt made the same mistake in reverse (discarding everything before a search anchor). Both were caught and repaired, but the underlying problem is structural: a card's column is encoded as *physical location in a 2000+ line file*, so every status change requires relocating a whole prose block — exactly the operation that's error-prone for both a script and a human eyeballing large diffs.

**Confirmed via discussion:** Joseph never reads `kanban-board.md`'s raw file directly — he only ever views it through the live-parsing Pi page (CARD-0057, `/kanban`). So raw-file top-to-bottom column grouping has no reader-facing value; it only exists for whoever (or whatever) parses the file, and is the thing actually causing the risk.

**Decided approach:**
1. **Add `**Status:** <Column>` as a line directly under every card's header**, values being exactly the 5 existing column names (Backlog, Planning, Build, Done, Defer). This becomes the single source of truth for a card's state.
2. **Remove the `## ColumnName` section headers from `kanban-board.md` entirely** — once status lives on the card itself, physical position is redundant and risks disagreeing with the real status field. Cards become one flat, append-only list.
3. **Never physically relocate a card block again.** Moving a card between columns becomes a one-line edit to its `**Status:**` field. New cards get appended to the end of the file; existing cards are never moved once written.
4. **Drop the stale status word from cross-references.** Lines like "CARD-0104 (Backlog — the Gaia-embed precedent...)" go stale the moment the referenced card's status changes, and hunting these down by hand after every move is its own recurring chore (done 3 times tonight alone). Change the convention to omit the status word — just "CARD-0104 (the Gaia-embed precedent...)".
5. **Add a `<!-- next-card-id: CARD-XXXX -->` marker near the top of the file**, so creating a new card never requires grepping for the current highest ID.

**Required dependency, found while scoping this:** `core/logging/log_server.py`'s `_parse_kanban_board()` (the Pi's live `/kanban` page, CARD-0057) currently finds a card's column by locating physical `## ColumnName` section boundaries via `_KANBAN_COLUMN_RE` — removing those headers would break it outright (zero columns found). Must be updated in the same change to instead read each card's `**Status:**` line, and redeployed to the Pi, or the live board goes dark.

**Explicitly out of scope, considered and rejected:** splitting into one file per card (would also solve the relocation-risk problem, but breaks the single-file `kanban-board.md` convention referenced throughout the repo and CARD-0057's parser far more invasively, for no benefit beyond what the status-field change already achieves).

**Done when:** every existing card carries a `**Status:**` line matching its current column, the `## ColumnName` headers are gone, `log_server.py`'s parser is updated and redeployed to the Pi with the live `/kanban` page confirmed still grouping cards correctly, stale status words are stripped from cross-references, and the next-card-id marker is in place.

**Verified complete, 2026-07-29 16:28 MST:** all 5 "Done when" criteria checked directly against the live file and the Pi. No `## ColumnName` headers remain; all 118 cards carry a `**Status:**` line; `log_server.py`'s `_KANBAN_STATUS_RE` parser is deployed and the `jctsh-logging` service is active on the Pi (confirmed directly via SSH); the `next-card-id` marker is present and current. One real gap found on review: the "omit the status word from cross-references" convention (item 4) was applied retroactively to references stale at the time this card was raised, but wasn't actually followed going forward — CARD-0115 through CARD-0118's own `Related:` lines kept writing `(Done — ...)`. Fixed those four (Joseph's call: fix the four, leave the convention as symmetric guidance rather than adding enforcement).

**Related:** CARD-0057 (the Pi-hosted live parser this depends on and must update), CARD-0056 (original persistent-board effort, superseded by CARD-0057's dynamic fetch), CARD-0111 (the card-move work that surfaced this problem).

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

### CARD-0071 · [idea] [personal] Emergency Access preparation
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

### CARD-0041 · [idea] [photo-server] Disk capacity growth analysis — wait for steady state
**Status:** Planning

**Notes:** Discussed 2026-07-09: want to estimate photo-library growth rate and project when the primary drive (Backup Plus 1TB, currently 615G/71% used) or backup drive (Momentus 640GB) will need replacing/upsizing. Deliberately not started yet — Joseph's call: current disk numbers are all noise from one-off events (CARD-0039 added 3,433 assets in one shot, CARD-0030 just freed 818GB by deleting zips, first post-cleanup backup run is still doing a full reconciliation rather than a normal weekly delta), not representative of organic day-to-day growth.

**Wait for:** the backup cron (CARD-0030/CARD-0040) running its normal weekly incremental cadence for a few cycles, so disk usage tracking reflects only real photo uploads from Joseph's and Robin's phones. At that point, weekly rsync deltas become a meaningful proxy for actual growth rate and a "months until full" estimate becomes trustworthy rather than a guess. Revisit this card once that's true — no fixed date, just "after the dust settles."

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

Still technically trivial as originally scoped: Google Sheets is a native Looker Studio data source (GPS Track + Environmental Data sheets), no new infrastructure. Review-after-the-fact use case, no real-time requirement.

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

### CARD-0070 · [enhancement] [hiking-monitor] Replace boost converter with LDO + gate peripheral power for lower standby draw — DEFERRED 2026-08-14
**Status:** Defer

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-08-22 (CARD-0193) — 15751B, over the 10000B size threshold.

---

### CARD-0072 · [idea] [personal] Digital Identity Checklist Version 2
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

**Notes:** Found 2026-07-22 via the CARD-0051 heartbeat check: `Immich degraded - backup:stale (10.3d since last success)`. Confirmed live via SSH — Docker containers all healthy, no data loss, disk usage normal on all three mounts (primary 73%, backups 39%/49%) — this was a stamp-write failure, not an actual backup outage.

**Root cause:** `photo-library-backup.sh` runs weekly via cron at `0 2 * * 0`. Immich's built-in nightly DB dump also runs at 02:00 daily (confirmed by `immich-db-backup-*-020000-*.sql.gz` filenames). On the 2026-07-19 run, rsync caught the DB dump's temp file mid-write/rename on both legs — Joseph's leg exited code 23, Robin's exited code 24 ("file has vanished... immich-db-backup-20260719T020000...sql.gz.tmp"), the same vanished-temp-file race already visible as a stale log entry from 2026-07-05. Since the script only touches `/home/jct/photo-library-backup-success.stamp` when both rsync legs return 0, this run's failure silently skipped the stamp (and correctly fired an MQTT "Backup failed" alert that apparently wasn't seen standing alone).

**Fix applied 2026-07-22:**
1. Rescheduled the cron entry from `0 2 * * 0` to `15 2 * * 0` (`crontab -e` on photo-server) so the weekly rsync starts 15 minutes after the DB dump, clear of the collision window.
2. Manually reran `/usr/local/bin/photo-library-backup.sh` to write a fresh success stamp and clear the alert immediately, rather than waiting a full week for the next scheduled run.

**Manual rerun confirmed clean 2026-07-22 09:39** — both rsync legs exited 0, stamp file updated (`/home/jct/photo-library-backup-success.stamp` now Jul 22 09:39), alert cleared.

**Closing criterion confirmed 2026-07-28, via direct SSH check on the M8:**
- Success stamp updated Jul 26 02:21:06 MST — only gets touched when both rsync legs exit 0.
- Cron fired exactly on the rescheduled time: `CRON[2399490]` ran the script at 02:15:01 on 2026-07-26.
- No vanished-file errors in that run — every `vanished` line in the 10.8MB backup log traces back to the old 2026-07-05/2026-07-19 runs already documented above; the 2026-07-26 run's own tail (DB dump backup, normal delete/sync output, final rsync summary) is clean.

The reschedule held on its first real scheduled run, not just the manual rerun — closing out.

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

**Raised 2026-07-28**, split out of CARD-0105 after Joseph's review of today's automatically-generated narrative: it mostly restates numbers and facts already present in the Data Summary / Coverage tables, in prose, with added words but not much added value — despite `SKILL.md`'s narrative-writing step already containing a non-redundancy rule ("don't restate numbers that belong in the data tables — interpret and connect instead").

**Diagnosed against real evidence:** compared today's actual narrative to the tables it's meant not to repeat. Four sentences were restatement in different words, not the digit-quoting the existing rule's examples focused on — "wrapped up in a little over half an hour" (Duration: 32m), "a gentle undulation of a few dozen feet" (Elevation Range/Gain), "roughly two miles of ground" (Distance: 2.0 mi), and, most tellingly, "the environmental sensor logged nothing... **detailed in the coverage section below**" — the narrative itself pointing at the exact section it duplicates. Root cause: the rule's worked examples only covered elevation and temperature; for other stats the model satisfied a literal reading of "turn it into an observation" with a soft paraphrase instead of real interpretation.

**Fixed — `SKILL.md` rule rewrite:** tightened the non-redundancy rule to explicitly cover paraphrase ("restating a number in softer words is still restating it"), added a concrete test ("does this connect the number to something else... or does it just describe the number in prose?"), and specifically addressed the coverage-section case (brief mention only if it limits the story, no forward-references to sections that already exist).

**Scope grew mid-card, 2026-07-28 (Joseph):** sun position in the narrative had the identical problem (raw degree values quoted in prose — "about ten degrees above the horizon... swings from east-southeast toward due east"), directly in tension with the rule just tightened. Fix: move sun elevation/direction into the Data Summary table, same treatment as every other measured range — **this was not actually prompt-only** (corrected mid-implementation after checking `templating.py`): the Data Summary table is deterministically templated from computed `stats`, not freely written, so this needed real code:
1. `components/hike-izer/fetch_hike_data.py` — compute `sun_elevation_deg` (min/max range) and `sun_direction_start`/`sun_direction_end` from `sun_position_samples`, added to `stats`.
2. `components/hike-izer-orchestrator/templating.py` — new `_sun_direction_display()` helper, two new Data Summary rows ("Sun Elevation Range", "Sun Direction").
3. `SKILL.md` part (a) — removed the instruction to quote sun degrees in prose, replaced with the same qualitative treatment already used for elevation.

**Verified against real data 2026-07-28:** ran `fetch_hike_data.py` fresh against today's real hike, rendered `templating.py`'s `data_summary_rows()` against the output — `Sun Elevation Range: 10.7–16.0°`, `Sun Direction: ESE → E`, matching the original narrative's own description almost exactly, confirming both the astronomy computation and the new table rows work correctly end-to-end.

**Related:** CARD-0105 (the unscoped idea this splits out of), `.claude/skills/hike-izer/SKILL.md`, `components/hike-izer/fetch_hike_data.py`, `components/hike-izer-orchestrator/templating.py`.

**Moved to Done 2026-07-29 05:14 MST** — no open items remained; both fixes (SKILL.md rule rewrite and sun-position table move) were verified against real data.

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

**Raised 2026-07-24**, during CARD-0083 planning — Joseph questioned the ongoing value of generating `.md` alongside `.html` now that HTML had become the richer format: CARD-0081 gave it real styling/structured layout, CARD-0084's photo gallery was already HTML-only (no equivalent in the Markdown), and CARD-0088 was standing up real public hosting specifically for the HTML output.

**Trigger condition met:** the card's own "recommended timing" was to wait until CARD-0088 (HTML hosting) actually shipped — it had, well before this was picked up, and had been live/verified through several subsequent cards (CARD-0086, CARD-0093, CARD-0094, CARD-0100, CARD-0101).

**Real scope was bigger than the card originally described.** The original "Scope when picked up" note only mentioned `.claude/skills/hike-izer/SKILL.md` — written before CARD-0086 (automatic triggering) existed. Auditing the actual current codebase found `components/hike-izer-orchestrator/generation.py`/`templating.py` independently duplicating the same `.md` + `.html` generation, and unlike the interactive Skill (which explicitly documented "the Markdown file is not copied"), the automatic path wrote both straight into the M8's publicly-served directory — a real, live inconsistency found via `docker logs`/`ssh` inspection, not something the original card anticipated.

**Executed 2026-07-28:**
1. **SKILL.md:** removed the standalone "save to `.md`" step, merged HTML generation into what's now a single step 5, renumbered steps 6-7 accordingly, dropped every "Markdown" reference (frontmatter description, step 4's structure framing, the weather-forecast "applies to both formats" clause, the publish step's "Markdown file is not copied" note, the file-extension example in the multi-day-trip handling), and removed a stale pointer to an example `.md` file that's now deleted.
2. **`templating.py`:** removed `render_markdown()` entirely (53 lines) and its section header; updated the module docstring.
3. **`generation.py`:** removed the `md_text` generation and file-write; updated a stale "SKILL.md's interactive steps 3/7" docstring reference to the new step numbers (3/6).
4. **`narrative.py`:** updated the system prompt's "ignore every other step... (data fetching, HTML/Markdown mechanics...)" to drop "Markdown" — left the separate, unrelated "no Markdown formatting" instruction alone (that one's about prose syntax within the narrative paragraphs, not the output file format).
5. **Both hike-izer READMEs** (`components/hike-izer/README.md`, `components/hike-izer-orchestrator/README.md`): dropped remaining "Markdown"/`.md` references, fixed the same stale step-number reference.
6. **Existing `.md` files — deleted** (Joseph's call): 4 local files under `hike-izer/summaries/` (`2026-06-17`, `2026-06-18`, `2026-07-18`, `2026-07-23`) plus the one stray copy already live-published on the M8 (`2026-06-18_hike-summary.md`, a leftover from CARD-0086 stage 2's test run against real data).
7. **Deployed and verified:** `generation.py`/`templating.py`/`narrative.py`/`SKILL.md` redeployed to the M8, orchestrator rebuilt, confirmed healthy and `hikes.jctnet.com` still serving correctly, confirmed no `.md` files remain in the M8's served directory. Also smoke-tested `templating.render_html()` locally against a synthetic `hike_data` fixture post-edit to confirm no leftover reference to the removed `render_markdown` broke anything (a first attempt caught a fixture bug, not a code bug — fixed and re-ran clean).

**Related:** CARD-0088 (HTML hosting, this card's trigger condition), CARD-0081 (HTML rendering, the format this card made sole), CARD-0084 (Photos, HTML-only, the existing precedent), CARD-0073 (Hike-izer v1, original `.md`-only scope), CARD-0086 (automatic triggering, the component whose duplicate `.md` generation this card also had to catch), CARD-0083 (the card whose planning surfaced this question).

---

### CARD-0094 · [idea] [hike-izer] Switch hike-izer-web from Tailscale Funnel to Cloudflare Tunnel — RESOLVED 2026-07-27
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7381B, over the 5000B size threshold.

---

### CARD-0100 · [bug] [hike-izer] Automatic trigger (CARD-0086) generates and publishes a page even when no hike is confirmed (e.g. GPSLogger left on during a car errand) — RESOLVED 2026-07-27
**Status:** Done

**Raised 2026-07-25**, Joseph asked what happens if GPSLogger is accidentally left running in a car and then stopped.

**Already handled, confirmed via code read:** `fetch_hike_data.py` already classifies each GPS session by median speed (`WALKING_SPEED_MIN_MPS`/`MAX_MPS`, ~0.15–3.0 m/s) plus daylight/stationary checks, marking anything outside walking pace `is_hike: false` with a rejection reason (e.g. "likely vehicle travel, not a hike") — a car trip's data is not mistaken for a hike at the classification level.

**Real gap that existed:** the automatic webhook path (`hike-izer-orchestrator/generation.py`) didn't act on that classification before doing real work. `hike_data["coverage"]["gps_track"]["hike_confirmed"]` only gated whether photos got fetched — regardless of its value, `run()` unconditionally made a real Claude API call, wrote and published an `.html`/`.md` page to the live public URL, and logged `"Published hike summary for <date>"` to MQTT. A car errand that was the only GPS activity for a day would still produce a real published page and a real API charge.

**Fixed 2026-07-27** in `generation.py`: `run()` now checks `hike_data["coverage"]["gps_track"]["hike_confirmed"]` immediately after the `fetch_hike_data.py` subprocess call, before photos/narrative/templating/publish. If false, it publishes a quiet `System`-category log (`"GPSLogger stopped, no hike confirmed for <date> -- skipped generation."`) and returns `None`; `run_and_log()` treats a `None` return as "already logged, nothing more to do" so it doesn't also publish a "Published hike summary" message. Scoped to the automatic webhook path only — the interactive Skill still correctly reports "no hike" when Joseph explicitly asks, since that's a wanted answer, not a bug. The old redundant `if hike_confirmed:` photos-gate was removed since it's now always true past the new early return. `_build_session_entry`/etc. untouched — this card only touches control flow in `generation.py`, not classification.

**Mock-verified 2026-07-27** (subprocess/API/MQTT all mocked, no real cost): no-hike-confirmed case skips narrative/templating entirely and publishes exactly one skip log; `run_and_log()` publishes nothing extra on that path; hike-confirmed case still reaches narrative/templating unaffected — new gate doesn't touch the working path.

**Live-verified 2026-07-27, real deployment.** Rebuilt and redeployed the `hike-izer-orchestrator` Docker image on the M8 (`docker compose up -d --build orchestrator` — also picked up the CARD-0101 `fetch_hike_data.py` fix, whose copy on the M8 was stale until this deploy). Sent a real `POST` to the live webhook (`https://photo-server.tailfe828a.ts.net/webhook/hike-end`) for a date with zero GPS/environmental activity: `docker logs` showed 0 rows fetched → immediate `"No hike confirmed ... skipping generation"` with no narrative step in between; `curl` against the would-be published page returned `404` (nothing written); the exact skip message showed up live on the JCTsh log dashboard (`http://100.70.162.24/data`, component `hike-izer-orchestrator`, category `System`) via the real MQTT path, not just a mock.

**Related:** CARD-0086 (the automatic-triggering component this gap lived in), CARD-0101 (the sibling GPS-classification fix deployed in the same M8 rebuild), `components/hike-izer-orchestrator/generation.py`, `components/hike-izer/fetch_hike_data.py` (the existing car-vs-hike classification this card builds on, not replaces).

---

### CARD-0093 · [enhancement] [personal] Clean up DNS records on both `jctnet.com` and `jctnet.net` — RESOLVED 2026-07-27
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-08-22 (CARD-0193) — 8063B, over the 5000B size threshold.

---

### CARD-0102 · [investigation] [infrastructure] Audit: what else breaks when the Pi/M8 weekly scheduled reboots discard in-flight state — RESOLVED 2026-07-27
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

### CARD-0099 · [bug] [data-pipeline] Timeline sheet's `timestamp_az` column hardcodes Arizona local time for every row, regardless of where it happened — RESOLVED 2026-07-25
**Status:** Done

Archived to `core/data-pipeline/CLAUDE.md` on 2026-08-22 (CARD-0193) — 5053B, over the 5000B size threshold.

---

### CARD-0097 · [bug] [hike-izer] Hike Start Forecast capture hardcodes Arizona timezone — breaks anywhere but Arizona (Michigan trip, then Egypt trip Feb 2027) — RESOLVED 2026-07-25
**Status:** Done

**Raised 2026-07-25**, originally scoped ahead of a planned Egypt hiking trip in February. **Re-scoped same day:** this is not a US-vs-international issue — Phoenix is fixed UTC-7 with no DST, so *any other timezone*, including Michigan (Eastern, UTC-4/-5 depending on DST), hits the same bug. Moved to Build immediately because Joseph is traveling to Michigan and needs Hike-izer working correctly there before the Egypt trip.

**Fix written and desk-verified 2026-07-25** — `core/data-pipeline/environmental-data.gs`'s `_maybeCaptureHikeStartForecast` now calls Open-Meteo with `timezone=auto` (server-side IANA lookup from lat/lon) instead of hardcoded `America/Phoenix`, and derives both the day-bucket and the nearest-hour match from the returned `utc_offset_seconds` instead of a fixed `-07:00`. `SCRIPT_VERSION` bumped to `2026-07-25.1-hike-start-forecast-timezone-fix`. Verified via a standalone Python port of the exact date arithmetic (Apps Script can't run outside its own editor) covering: Egypt/Giza (UTC+2), Michigan winter (EST, UTC-5), and a Michigan near-midnight edge case — all bucketed to the correct local calendar day and matched the correct local hour. A regression check confirmed the *old* hardcoded logic would have picked a forecast hour ~8.75 hours off for the Egypt case, i.e. the bug was real, not theoretical.

**Deployed and confirmed live 2026-07-25** — Joseph pasted the updated file into the Apps Script editor and redeployed (Deploy → Manage deployments → pencil → New version). Confirmed via `curl` against the live deployment URL: response `version` field reads `2026-07-25.1-hike-start-forecast-timezone-fix`, matching the fix. Same deployment URL, no Node-RED/Tasker changes needed.

**Scope confirmed via code read:** the webhook/orchestrator path (`app.py`, `generation.py`, `fetch_hike_data.py`) already threads the phone's real local UTC offset through correctly — no hardcoded-timezone assumption there. The one real gap is `core/data-pipeline/environmental-data.gs`'s `_maybeCaptureHikeStartForecast` (built for CARD-0083), which hardcodes Arizona in two places:
1. Buckets "first observation of the day" using Arizona's calendar date (`_azString`) regardless of where the hike actually is — for any other timezone this can capture on the wrong day relative to the hike's real local date.
2. The Open-Meteo request hardcodes `&timezone=America%2FPhoenix`, then parses the returned hourly timestamps with a hardcoded `-07:00` offset — so the "closest hour to hike start" match is computed against Arizona wall-clock hours mislabeled as if local to the hike, picking the wrong hour's forecast and mislabeling the times shown in the summary output.

Open-Meteo itself is a global provider (not US-only), so this is a fix, not a provider swap: derive both the day-bucket and the API's `timezone` param from the hike's actual local offset (Open-Meteo supports `timezone=auto` given lat/lon), instead of hardcoding Phoenix.

**Acceptance criteria (desk-verified, not requiring a live trip to close):** feed the function synthetic non-Arizona coordinates/timestamps — at minimum Michigan (Eastern, UTC-4/-5) and Egypt-like (Giza, ~UTC+2) — and confirm the captured forecast row picks the correct local hour and correct calendar-day bucket in each case, not Arizona's.

**General principle (Joseph, 2026-07-25):** no component Hike-izer touches should assume a fixed home timezone or location — every timezone/location-dependent computation must derive from the hike's actual coordinates/local offset, never a hardcoded Phoenix/home default. This fix is the one confirmed instance; if another hardcoded-Arizona assumption turns up elsewhere in the Hike-izer path later, it's an instance of this same principle, not a separate one-off.

**Related:** CARD-0083 (original Hike Start Forecast feature, source of the hardcoded assumption), `core/data-pipeline/environmental-data.gs`.

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

### CARD-0084 · [idea] [hike-izer] Photo integration (Immich) — RESOLVED 2026-07-24
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7410B, over the 5000B size threshold.

---

### CARD-0081 · [idea] [hike-izer] HTML rendering, Levels 1-2 (basic styling + structured layout) — RESOLVED 2026-07-24
**Status:** Done

**Notes:** Raised 2026-07-23. Current output (v1, CARD-0073) was Markdown only. Goal: improve readability and shareability via HTML rendering, built iteratively — start simple, layer in complexity over successive passes rather than one big build. Originally scoped as a 5-level iteration path in this one card; narrowed 2026-07-23 to just Levels 1-2 per Joseph's preference for shorter-running cards, with Levels 3-5 (embedded visuals, interactive, hosting) split out to **CARD-0088**. CARD-0088 was itself narrowed 2026-07-24 after its embedded-visuals/interactive scope turned out to be pure duplicate of CARD-0082 (visuals) and CARD-0084 (photos) — it now covers only hosting.

**Scope (this card):**
1. **Basic styling** — real typography, readable width, light/dark support via CSS custom properties + `@media (prefers-color-scheme: dark)` (same convention as `core/logging/log_server.py`'s `_KANBAN_TEMPLATE`, no new dependency — no Markdown→HTML library exists anywhere in this repo). Same content as the `.md` output, just legible and presentable.
2. **Structured layout** — a stat-row hero (Date, Duration, Distance, Elevation Gain) before the narrative, distinct visually-separated sections (narrative / data tables / full observations / pipeline-health coverage).

**Implementation:**
- `components/hike-izer/fetch_hike_data.py` — added `stats.distance_mi`, a new data-layer figure that didn't exist before (only altitude range/gain was computed). Summed per-session via `_haversine_m` in `_gps_sessions()`, then totaled across `is_hike`-confirmed sessions only in `main()` (not all GPS activity for the day — driving between trailheads or GPS drift at camp shouldn't count). `None` when `hike_confirmed` is false, never a fake zero.
- `components/hike-izer/html-template.html` (new) — the static CSS/structure reference the Skill copies from on every run, keeping output visually consistent across independently-authored invocations rather than restyled each time.
- `.claude/skills/hike-izer/SKILL.md` — added a step generating `<date>_hike-summary.html` alongside the Markdown, with the stat-row field mapping and the "not available" rule for missing figures (never blank/zero).
- `components/hike-izer/README.md` — updated file listing.

**Verified (2026-07-23):** re-ran `fetch_hike_data.py` for 2026-06-18 (confirmed hike) — `stats.distance_mi` computed correctly (3.16mi across two sessions in the fetched window, one being June 17's midnight-crossing tail; same pre-existing whole-window scope as elevation/temp stats, not a new bug — the June-18-only session is 2.03mi/112ft, matching the existing `.md`). Hand-authored two real `.html` files and opened both in Chrome:
- `hike-izer/summaries/2026-06-18_hike-summary.html` — confirmed-hike day, full stat row (2.0mi, 112ft, 68.3min), light-mode colors correct, dark-mode CSS-variable cascade confirmed correct across body/stat-cards/tables, mobile breakpoint rule (`@media max-width:640px`, 4→2 columns) confirmed present and correct in the parsed stylesheet.
- `hike-izer/summaries/2026-07-23_hike-summary.html` — `hike_confirmed: false` day, Distance/Elevation Gain correctly render as styled "not available" (muted italic) while Date/Duration still show real values, GPS-confirmation callout renders, all 19 observation rows present.

**Polish (2026-07-24):** dropped the date from the H1 (`html-template.html` and both generated files) — it was redundant with the Date stat card immediately below it, the first two lines of the page repeating the same figure.

**Related:** CARD-0088 (HTML output hosting — the one remaining piece of the original Levels 3-5 scope, narrowed), CARD-0082 (Visual track + elevation graphic — owns embedded-visuals/interactive scope directly), CARD-0084 (Photo integration — owns photo scope directly), CARD-0073 (Hike-izer v1, Done).

---

### CARD-0087 · [bug] [hiking-monitor] GPSLogger ran during today's hike but zero rows reached the GPS Track sheet — RESOLVED 2026-07-23
**Status:** Done

**Notes:** Found 2026-07-23 while running Hike-izer for today. Requested a Hike-izer summary for today's hike; `fetch_hike_data.py` returned zero GPS Track rows. Joseph confirmed GPSLogger was actively running for the entire hike today, and — importantly — **was not running on any other day in the past week**. So the only day with a real, confirmed expectation of GPS Track data was today, and today produced none. This was one concrete failure instance, not evidence of a long-running continuous outage — the GPS Track sheet's most recent row before today was 2026-06-18, but that gap likely just reflected GPSLogger not being used in between, not the pipeline being broken that whole time.

**Confirmed via direct investigation:** queried the GPS Track sheet's `action=export` endpoint with no date filter — 806 total rows, most recent timestamp 2026-06-18T21:55:32Z, nothing since. Meanwhile the Hiking Observations sheet *did* receive 19 real rows today (5:45–8:28 AM MST, clearly a real hike) via the same Apps Script deployment — so today's break was isolated to GPSLogger's specific upload path, not a general Apps Script/Sheets outage.

**Root cause — confirmed 2026-07-23:**
1. Server-side ingestion tested directly with a synthetic well-formed request (`action=gps&lat=...&key=<current API_KEY>`) — returned `{"status":"ok"}` and appended cleanly. Current deployment, current API key, and the `action=gps` code path were all confirmed working correctly.
2. Joseph checked GPSLogger's actual configured Custom Logging URL — it was the **bare deployment URL with no query string at all**: no `action=gps`, no `lat`/`lon`/`acc`/`alt`/`ts` placeholders, and no `key`. Every request GPSLogger sent had zero parameters, which the script correctly rejected as `{"status":"error","message":"unauthorized"}` — **but returns that as an HTTP 200**, so GPSLogger had no signal anything was wrong.
3. Fixed: full correct URL (`.../exec?action=gps&lat=%LAT&lon=%LON&acc=%ACC&alt=%ALT&ts=%TIME&key=<API_KEY>`) given to Joseph to paste into GPSLogger's Custom Logging URL field, replacing the bare URL.

**How this happened despite being on the documented migration checklist:** `components/hiking-monitor/data-pipeline.md`'s 2026-07-18 redeploy note *does* correctly list GPSLogger's custom URL as one of the places to update during any future redeploy — this wasn't a case of nobody knowing to check it. The gap was verification, not identification. Every other consumer on that list has a way to machine-confirm the update actually stuck: Node-RED's env var was checked live via `/proc/<pid>/environ`, the read/export side was checked via `action=version`. GPSLogger's config lives only on the phone, outside anything checkable remotely — the only real verification is a live field test, and the *original* Step 19 build instructions (`hiking-monitor-claude-code-instructions.md`) actually required exactly that ("take a short outdoor walk... verify trackpoints appearing in the sheet") when the pipeline was first built. That same discipline wasn't re-applied when the URL was later swapped during the 2026-07-18 migration — a URL update felt lower-risk than the original build, but for a manually-typed URL with five placeholder tokens in it, it isn't.

**Field-test confirmation (2026-07-23):** Joseph did a short verification walk near the house with the corrected URL in place. Confirmed via direct `action=export` query against the GPS Track sheet: six real trackpoints landed at 18:27:06–18:30:18 UTC, ~30s apart (matching GPSLogger's normal upload cadence), clustered around 32.4614, -111.1185 — within ~15m of the house footprint centroid (`house-lot-coordinates.md`), with naturally varying accuracy (9–25m) and altitude (721–744m) values consistent with real phone GPS rather than synthetic test data. This is distinct from the earlier synthetic debug row at 20:00:00 UTC (suspiciously round `lat: 32.4321, lon: -111, accuracy_m: 10, altitude_m: 800`). Confirms the corrected URL works end-to-end with the real GPSLogger app.

**Process fix, so this doesn't recur:** `data-pipeline.md`'s migration checklist should flag GPSLogger specifically as requiring a live field-test confirmation, not just "update the URL" — it's the one consumer on that list with no machine-checkable verification path.

**Related:** CARD-0073 (Hike-izer v1, Done — original GPSLogger URL migration), `components/hiking-monitor/gps-pipeline.md`, `components/hiking-monitor/data-pipeline.md` (redeploy checklist), `components/hike-izer/fetch_hike_data.py`.

---

### CARD-0079 · [bug] [logging] Old null-byte corruption in the log file (536 bytes, historical, inactive) — RESOLVED 2026-07-23
**Status:** Done

**Notes:** Found 2026-07-22 while testing CARD-0078's webhook fix. Initial concern was that a confirmed-published MQTT message never appeared in `/mnt/jctsh-logs/jctsh.log` or the live `/log` endpoint — **resolved as a false alarm, not a bug:** `log_server.py` holds the most recent non-heartbeat message in a single global `_pending` slot and only flushes it to disk once a *different* non-heartbeat message displaces it (`_store_entry()`, `core/logging/log_server.py`). The live `/data` endpoint (which includes `_pending`) had the message the whole time; sending a second distinct test payload immediately flushed the first to the file, confirmed directly. Working as designed.

**What was real:** while investigating, found genuine null-byte corruption in the log file — 536 bytes total, in two small contiguous runs (367 and 169 bytes), confirmed via direct Python byte-level scan (`/mnt/jctsh-logs/jctsh.log`). The earlier "7,634" figure quoted from `grep -c $'\x00'` was wrong — that shell substitution doesn't actually pass a null byte as a grep pattern, so it silently matched an empty pattern and just counted total lines in the file, not corruption. Both null-byte runs sat in **old content from around 2026-07-03** (real log lines resumed immediately after each run) — not recent, not growing, not connected to CARD-0006's log-directory migration or that night's testing.

**Surgical cleanup done (2026-07-23):** backed up the live file first (`/mnt/jctsh-logs/jctsh.log.bak-20260723-precard0079`), then re-scanned to get exact byte offsets — 367-byte run at offset 340640, 169-byte run at offset 360279 (offsets shifted slightly from the original find since the file kept growing between the initial report and cleanup). Confirmed both runs sat cleanly between two complete log lines with no partial-line truncation, then spliced them out (removing from the highest offset first so lower offsets stayed valid) and rewrote the file. Verified: 0 null bytes remaining, byte count dropped by exactly 536 (823545 → 823009), and both seams rejoin correctly (`...Log server connected.\n2026-07-01 03:11:54...` and `...Log server connected.\n2026-07-03 07:58:52...` both found intact, no merged/split lines).

**Deliberately out of scope, not a remaining gap:** root-causing *why* the corruption happened around 2026-07-03 (crash/kill mid-`RotatingFileHandler`-write is the likely mechanism, but never confirmed against git history/deploy log for that date) — low priority, only worth revisiting if similar corruption recurs. Also unrelated: two harmless fake test entries from CARD-0078 verification (`Test Vendor Inc` / `aa:bb:cc:dd:ee:ff`, `Second Test Vendor` / `11:22:33:44:55:66`) are still in the real log — left in place, clean up manually if it bothers you.

---

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

### CARD-0006 · [enhancement] [logging] Move log directory to USB stick — RESOLVED 2026-07-22
**Status:** Done

**Notes:** Moved `LOG_DIR` in `log_server.py` from the SD card to a dedicated USB stick plugged into the Pi for better write endurance. Sizing check beforehand found the actual log volume (jctsh.log + state.json) under 1MB after 1.5 months across all 8 heartbeat components — capacity was never the constraint, write endurance was.

**Before formatting the drive:** it was a reused spare, not blank — checked its 19 existing files (an old personal photo archive, 47.5MB) against both Immich libraries by filename (zero matches), then ran the newly-established standard `immich-go upload from-folder` import into Joseph's account per `components/photo-server/operations.md`: 12 genuinely new assets uploaded and tagged, 7 caught as checksum-based duplicates Immich already had under different filenames. Confirmed safe to reuse only after that.

**Resolution:** formatted the drive (`/dev/sda1`, ext4, label `jctsh-logs`), mounted at `/mnt/jctsh-logs` via a UUID-based `/etc/fstab` entry (not a `/dev/sdX` path — avoids the device-letter-shift class of bug CARD-0032 hit on photo-server), migrated the existing log history over, and repointed `LOG_DIR`. **Found and fixed a real gap during deployment:** the `jctsh-logging.service` unit had no `RequiresMountsFor=/mnt/jctsh-logs`, meaning a reboot could race the service ahead of the mount and silently recreate the log directory back on the SD card underneath the mount point — the same class of blind spot as photo-server's Immich bind-mount incident (CARD-0032/CARD-0048). Added the dependency and committed the unit file to the repo (`core/logging/jctsh-logging.service`) since it wasn't tracked before.

**Verified via a real reboot test:** mount came back automatically, service correctly waited for it (state restored from `/mnt/jctsh-logs/state.json`, not recreated fresh), and new log entries flowed normally post-boot (garage-radar, salt-sensor, netalertx all confirmed logging). Stale SD-card copy deleted once the new path was confirmed live.

---

### CARD-0075 · [enhancement] [hiking-monitor] Rename project from hiking-sensor to hiking-monitor throughout — RESOLVED 2026-07-21
**Status:** Done

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
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 16167B, over the 10000B size threshold.

---

### CARD-0034 · [idea] [personal] Complete digital-identity-protection-checklist.md — RESOLVED 2026-07-17
**Status:** Done

**Notes:** Work through `digital-identity-protection-checklist.md` (repo root) — Joseph and Robin's personal security checklist closing single-point-of-failure risks (carrier port-out PIN, 2FA off SMS, credit freezes, password manager, household verification protocol, incident response plan). Almost entirely manual actions by Joseph/Robin themselves (phone calls to carriers/bureaus, account settings changes) — not something Claude Code can execute directly, but worth tracking to completion since it's currently all unchecked. Also has an "Open Items to Fill In" section (list specific banks/brokerages in use, confirm current password manager/2FA setup, set a 6-month review date) that needs input from Joseph before those parts can be finished.

**Blocked (2026-07-11):** waiting on delivery of Google Titan Security Key hardware authenticators (3 ordered) — needed for the hardware-key 2FA portion of the checklist before those items can be checked off.

**Resolution (2026-07-17):** closing as **version 1 done**, not "everything checked off" — the checklist reached v2.1 and the core mission (closing the phone/SIM-swap single point of failure the TIME article exposed) is solidly closed: carrier port-out locks on both lines, Google recovery phone and security question removed, recovery email cross-set between spouses, all 3 Titan keys ordered/registered on Google and RoboForm/PIN-set-and-tested/labeled/backed-up-in-the-safe, Google Account password and 2-Step Verification confirmed hardened with no phone-based fallback remaining, master password memorized redundantly by both Joseph and Robin, 3 of 5 credit bureaus frozen, and the household verbal-verification protocol agreed. Remaining open items (RoboForm Emergency Access + Google Inactive Account Manager, ID document photo cleanup, Robin's app-password/third-party-app review, Google Recovery Contacts, ChexSystems/LexisNexis, walking the checklist through with Robin, Phase 4/5 offline-copy prep) are real but represent the next layer of hardening, not blockers on calling v1 done — split out to CARD-0071 (Emergency Access preparation) and CARD-0072 (Digital Identity Checklist Version 2) rather than holding this card open indefinitely.

**Closed 2026-07-17 — Joseph directed the close.**

---

### CARD-0026 · [enhancement] [hiking-monitor] Measure hiking-monitor sleep-mode current draw — RESOLVED 2026-07-16
**Status:** Done

Archived to `components/hiking-monitor/CLAUDE.md` on 2026-08-22 (CARD-0193) — 12241B, over the 10000B size threshold.

---

### CARD-0068 · [enhancement] [netalertx] Remove online/offline presence messages from the log — RESOLVED 2026-07-15
**Status:** Done

**Notes:** Raised 2026-07-14, follow-up to CARD-0063. With the translation flow live for a bit, the online/offline presence transition messages (`<device> came online` / `went offline`) turned out to be noisy and not actionable — mobile/known-flappy devices dominate, and even a real device flip doesn't carry enough context (how long, why it matters) to be worth a log line. New-device alerts and the heartbeat are working well and stay. No future use anticipated for presence data elsewhere (NetAlertX's own UI already covers online/offline if ever needed) — clean removal, not a toggle/config flag.

**Scope:** in `components/netalertx/netalertx.flow.json` — remove the `mqtt_in_netalertx_binary` node (`system-sensors/binary_sensor/+/state` subscription) and the `fn_presence` function node entirely. Also remove the `devinfo_<mac>` vendor/model caching in `fn_device_info`, since it only existed to label presence messages that won't exist anymore. New-device alert messages already build their label directly from the per-device sensor payload (`payload.model || payload.vendor`), not from that cache, so no functional change there. Heartbeat and new-device detection otherwise untouched.

**Progress (2026-07-14):** `netalertx.flow.json` updated (11 nodes, `mqtt_in_netalertx_binary` + `fn_presence` + dead `devinfo_<mac>` caching removed), `netalertx-README.md` updated to match, deployed to the live Node-RED instance via the tab-clear-and-reimport procedure. **Leaving open on Joseph's call** — wants to live with it for a few days before confirming the change actually feels right day to day, rather than closing on the first clean deploy. Resume here: check back after a few days that no online/offline messages have reappeared and new-device alerts/heartbeat are still behaving.

**Deploy verification note (2026-07-14):** checked the log dashboard right after deploy and initially saw presence messages at 20:36 (`Front Porch Sensor went offline`, etc.) — looked like the redeploy failed. Confirmed with Joseph there's only one NetAlertX tab, no duplicate flow; the 20:36 batch was actually from the last scan cycle *before* the redeploy, since scan cycles land roughly every 30 minutes and no new cycle had run yet at the time of checking. Real confirmation needs the *next* scan cycle (~21:06) to show no presence messages — not yet observed as of this note. Also surfaced (unrelated, not investigated): a watchdog alert `Component front-porch-temp-sensor silent for 35 minutes` at 20:59.

**Resolution (2026-07-15):** lived with it about a day as planned. No online/offline presence messages have reappeared since the redeploy — confirmed repeatedly, including incidentally during CARD-0069's investigation (which needed to read netalertx's real log history in detail and found only heartbeats and new-device alerts, no presence noise). New-device alerts and heartbeat continued working correctly throughout, including through CARD-0069's own restarts and redeploys of the log server itself. The change holds up in real use, not just on a clean deploy.

**Closed 2026-07-15 — Joseph confirmed and directed the close.**

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

**Notes:** Raised 2026-07-13. During post-CARD-0009-rework field testing, UVI read 0 (then 0.01) when the device was taken off dock power into "direct sunshine," raising concern about a wiring fault introduced by CARD-0009's STEMMA QT rework on the LTR-390. Split out as its own card rather than folded into CARD-0009, since that card scopes the enclosure/build work specifically and this is a sensor-correctness question that outlived it.

**Investigation:** ruled out, in order — enclosure/case blocking the sensor (device wasn't in the box), SDA/SCL swap from the STEMMA QT rework (wiring confirmed correct by direct inspection), and a loose STEMMA QT connector. BME280 (shared I2C bus) read normally throughout, narrowing any real fault to the LTR-390 itself. Sensor pointed straight at the sun and left to complete a full `update_interval: 2min` cycle — UVI climbed to **6.90**, a plausible value for clear midday sun. No hardware fault; the earlier near-zero readings were just pre-settle values from before the sensor had a clean, unobstructed, correctly-oriented exposure.

**Side finding:** the 5-minute heartbeat log message (`jctsh/components/hiking-monitor/log`) only reported uptime/RSSI/temp/battery — humidity, pressure, and UV index were invisible on the dashboard, which is why this diagnosis required reading the physical OLED instead of checking remotely. Expanded the heartbeat lambda in `hiking-monitor.yaml` to include all five BME280/LTR-390 readings (temp, humidity, pressure, UVI) plus battery, each NaN-safe.

**Resolution:** config validated clean (`esphome config`), OTA-reflashed successfully — device back online at 09:32:41 (`Online — ESPHome 2026.4.5, IP: 192.168.1.161, MQTT connected`). First post-reflash heartbeat (09:37:18) confirmed live on the dashboard: `Heartbeat - uptime: 0h 5m, RSSI: -59dBm, temp: 99.9°F, humidity: 32.7%, pressure: 931.7hPa, UVI: 6.92, batt: 4.00V` — all readings present, UVI holding steady near the earlier 6.90 reading.

**Closed 2026-07-13 — Joseph confirmed the new heartbeat message showed up on the log.**

---

### CARD-0003 · [enhancement] [mqtt] TLS for Mosquitto (port 8883) — RESOLVED 2026-07-13
**Status:** Done

Archived to `core/mqtt/CLAUDE.md` on 2026-08-22 (CARD-0193) — 7374B, over the 5000B size threshold.

---

### CARD-0061 · [enhancement] [infrastructure] Add Docker health check for the Pi's Home Assistant container &mdash; RESOLVED 2026-07-12
**Status:** Done

**Notes:** Found 2026-07-12 during a Pi health evaluation. The `homeassistant` Docker container had no configured `HEALTHCHECK` &mdash; `docker ps`/`docker inspect` only reflected process liveness, not actual HA responsiveness. Same class of blind spot already found and fixed on photo-server (CARD-0032/CARD-0046: Docker's own health check only pings the API, doesn't verify real functionality) &mdash; HA is arguably the single most critical container on the Pi, since it's the sole bridge to SmartThings/Google Home for the whole house.

**Resolution:** added a `healthcheck` block to `core/homeassistant/docker-compose.yml`: `curl -f http://localhost:8123/manifest.json` (lightweight, unauthenticated, confirmed working) every 60s, 10s timeout, 3 retries, 90s start period to cover HA's own boot time. Deployed to the Pi (`/home/pi/docker-compose.yml`) and recreated the container &mdash; the existing `homeassistant` container predated this compose project (no compose labels), so it had to be stopped and removed before `docker compose up -d` would take over management of it; HA's actual config lives in the bind-mounted `/home/pi/homeassistant` volume, not the container, so nothing was lost.

**Live-tested 2026-07-12** using the same deliberately-break-it discipline as CARD-0029/CARD-0032/CARD-0046: confirmed `(healthy)` immediately after recreation, then froze HA's actual process inside the container (`kill -STOP` on the main `python3 -m homeassistant` PID &mdash; a genuine hang, not a container-level action, since that's exactly the failure mode this card exists to catch) and waited for the check to notice. Docker correctly flagged `unhealthy` with `FailingStreak: 3` after three consecutive failed checks. Resumed the process (`kill -CONT`); Docker correctly returned to `(healthy)`. Full Docker-level cycle (healthy &rarr; unhealthy on real hang &rarr; healthy again) verified end to end.

**Dashboard-visibility gap found and closed (2026-07-12):** the Docker-level fix alone only fixed `docker ps`/`docker inspect` locally on the Pi &mdash; it did not surface anything on the JCTsh log dashboard, unlike the photo-server pattern this card was modeled on, which pairs a health check with a heartbeat script that publishes the result to MQTT. Built `core/homeassistant/pi-heartbeat.py`, checking `docker inspect homeassistant`'s health status and publishing to the existing `jctsh/core/log-server/log` topic under the `jctsh-core` component identity (same identity/topic/credentials already used by the Pi's boot/reboot notifications &mdash; `/etc/jctsh/log-server.env`, reused rather than a new dedicated MQTT account, since this is the same host's own infrastructure). Deployed via `core/maintenance/pi-heartbeat.service`/`.timer` (30 min, matching the fleet-wide heartbeat cadence). Hit one real bug during first deploy: initially built the topic from the component variable (`jctsh/core/jctsh-core/log`) instead of the fixed `jctsh/core/log-server/log` topic the log server actually expects &mdash; component name and topic segment are decoupled in this convention and are easy to conflate; fixed and redeployed.

**End-to-end live-tested 2026-07-12:** repeated the freeze/resume test with the heartbeat script run manually at each stage, confirmed via the dashboard's actual `/data` endpoint (not the flushed-only `/log` text file, which delayed visibility of the healthy-state message inside an unflushed collapse group during testing and briefly looked like a bug before being traced to normal flush-timing behavior, not a real defect) &mdash; healthy (`System`, `Heartbeat - Docker containers healthy.`) &rarr; unhealthy (`Alert`, `Docker degraded - homeassistant:unhealthy`, visible immediately since Alert messages don't collapse) &rarr; healthy again, all three states confirmed present and correctly categorized on the live dashboard.

---

### CARD-0062 · [enhancement] [infrastructure] Switch Pi to headless boot &mdash; drop the desktop GUI &mdash; RESOLVED 2026-07-12
**Status:** Done

**Notes:** Found 2026-07-12 during a Pi health evaluation. The Pi boots into `graphical.target` with a full desktop session running (`pcmanfm --desktop`, `wf-panel-pi`) even though normal access is SSH-only &mdash; Joseph used the physical desktop once, during initial setup, never since. On a Pi 3B+ with only ~905MB RAM already under real pressure (zram swap sitting at ~50% used while running HA, Node-RED, Mosquitto, the log server, Tailscale, and fail2ban concurrently), this was pure reclaimable overhead.

**Pre-check:** confirmed no VNC/RealVNC/xrdp service configured, and `/etc/xdg/autostart/` + `~/.config/autostart/` contained only standard desktop-session plumbing (polkit agents, on-screen keyboard, compositor) &mdash; nothing load-bearing for SSH-only use.

**Resolution:** `sudo systemctl set-default multi-user.target`, rebooted. Confirmed `systemctl get-default` returns `multi-user.target` and no desktop processes (`pcmanfm`/`wf-panel-pi`) run anymore. SSH access, Docker/HA (HTTP 200 on `:8123`), Mosquitto, Node-RED, and jctsh-logging all confirmed active post-reboot.

**Before/after (steady 4-day uptime vs. 6 minutes post-reboot):** swap usage dropped from 449Mi (~50% of swap) to 148Mi (~16%) &mdash; the clearest signal, since raw "used" memory is a noisy comparison this early (buff/cache hadn't rebuilt yet). The desktop's ~225MB of GTK/panel/session overhead is now structurally absent rather than merely idle. Fully reversible via `systemctl set-default graphical.target` + reboot if ever needed.

---

### CARD-0059 · [idea] [infrastructure] NetAlertX — self-hosted LAN device tracker with custom naming — RESOLVED 2026-07-12
**Status:** Done

**Notes:** Raised 2026-07-12. Motivated by the router (TP-Link Archer AXE75) listing most connected devices with meaningless names, with no built-in way to rename them — the JCTsh-managed fleet already has this solved via DHCP reservations + `jctsh-network.md`'s device table + ESPHome hostnames, but third-party/commercial devices (Ring, Ecobee, Cast devices, guest phones) aren't part of that convention and the router won't let their names be overridden.

**What it is:** NetAlertX (formerly Pi.Alert) — open-source, self-hosted LAN device scanner and presence tracker. Maintains its own device database independent of the router, so naming lives there regardless of what the router shows.

**How it works:** periodic ARP scanning (plus optional plugins — mDNS, SNMP against the router, DHCP lease-file parsing, nmap) discovers devices; each MAC gets a persistent record (first-seen, last-seen, IP history, OUI-based vendor guess) in its own SQLite DB. A web dashboard lets you assign a friendly name/icon/group to each MAC once, permanently — independent of router support. Also flags brand-new unknown devices joining the network (security-relevant) and always-on devices going silent, with notifications via MQTT, webhooks, email, Pushover/Telegram/ntfy/Apprise.

**Planning (2026-07-12) — host decision reversed on real data:** initially figured the Pi as the natural fit (LAN hub, classic Pi.Alert project) and Joseph agreed — but checking the Pi directly first (good thing) found it's a Raspberry Pi 3 B+ already under real memory pressure: 34MB free, 315MB available, swap at 462MB/904MB (51%) — already running Docker for Home Assistant itself, plus Mosquitto, Node-RED, and `log_server.py` natively, all things other devices actively depend on (MQTT broker, automations). Adding periodic ARP/nmap scanning there risked contending for the little headroom left. Checked the M8 instead: 12 cores, 9.2GB available RAM, swap barely touched (109MB/4GB), Docker already running Immich's 4 containers cleanly. Switched the plan to the M8. No VLAN segmentation on this network (confirmed during CARD-0050), so the M8 sees the same broadcast domain the Pi would — no ARP-visibility loss from the switch. Skipped a separate Design phase — this checked-before-deciding pass is the plan; went straight to Build.

**Build (2026-07-12):** MQTT account (`netalertx`) created on the Pi's Mosquitto broker, recorded in `credentials.local.md`, verified working. `components/netalertx/docker-compose.yml` deployed to `~/netalertx-app` on the M8 (its own compose project, alongside but separate from `~/immich-app`).

Two real deploy bugs found and fixed: (1) my first compose file was based on a lossy AI-summarized version of the upstream reference, missing `read_only: true` and the specific `cap_drop`/`cap_add` set the entrypoint's own self-check requires — container crash-looped (exit 126) until fetched and matched the literal upstream file. (2) the upstream file's ARP-flux-mitigation `sysctls:` block isn't allowed by Docker under `network_mode: host` (`runc create failed: sysctl ... not allowed in host network namespace`) — removed from compose; the real fix is setting those two sysctls on the M8's host kernel directly, which needs interactive `sudo` (deferred — `jct@photo-server.local`'s sudo requires an interactive password, unlike the Pi's account; captured as a follow-up, not blocking).

**Resolution:** container deployed, healthy, zero restarts, image `ghcr.io/netalertx/netalertx:latest`. Login secured (Settings → System → Set Password, credential in `credentials.local.md` — default install ships with auth disabled entirely, closed that gap). Joseph completed the manual first-run setup and confirmed the naming workflow. MQTT/log-dashboard integration deliberately deferred, not because it's blocked but because it needs its own experiment first — split out to CARD-0063 rather than holding this card open for it.

**Closed 2026-07-12 — Joseph confirmed and directed the close.**

---

### CARD-0057 · [enhancement] [logging] Serve the kanban board as a live-parsing Pi page — RESOLVED 2026-07-11
**Status:** Done

Archived to `core/logging/CLAUDE.md` on 2026-08-22 (CARD-0193) — 8240B, over the 5000B size threshold.

---

### CARD-0004 · [enhancement] [salt-sensor] Migrate Arduino C++ → ESPHome — RESOLVED 2026-07-11
**Status:** Done

**Resolution:** `salt-sensor.yaml` written and compiles clean (RAM 13.2%, Flash 52.3%). Direct translation of the Arduino sketch — same 15-sample-median 12h reading cycle, same MQTT topics/payloads (`jctsh/sensors/salt-sensor/data`, `/status`, `/log`), same LED state machine (GPIO2/15/4, unchanged pins), same thresholds (still owned entirely by Node-RED — flow untouched). Added a 30-min heartbeat (`.../heartbeat`) that didn't exist before, closing the gap CARD-0021 flagged (salt-sensor showing `?` on the status dashboard). `secrets.yaml` created from `secrets.h`'s values; old v3 Arduino sketch archived to `archive/salt-sensor-v3-arduino/`; `C:\esphome\salt-sensor\` flash path set up matching the other ESPHome components.

**Two real compile bugs found and fixed during translation** (both are ESPHome `globals:` gotchas, not obvious from the docs): a fixed-size C array global (`float[15]`) fails to compile (`GlobalsComponent` can't take an array by value — decays to a pointer); switched to `std::vector<float>`. Its `initial_value: '{}'` was then ambiguous between two constructor overloads; fixed with an explicit `std::vector<float>()` initializer.

**One design decision worth flagging:** ESPHome's default MQTT birth topic is `<topic_prefix>/status`, which would have silently collided with this component's existing `.../status` topic (Node-RED → ESP32, drives the LEDs). `birth_message:` is explicitly disabled in the yaml to prevent this — a real footgun for any future component whose topic convention includes `/status`.

**Field verification (2026-07-10):** USB-flashed and confirmed end to end — LED self-test visible on boot, `/data` publishes a real retained reading, `/status` round-trips correctly from Node-RED and drives the LEDs (`ok` → solid green, confirmed visually), `/log` messages flowing to the dashboard. See CARD-0049 for the follow-on LED pin move (GPIO2/15/4 → GPIO32/33/27), also verified working over OTA.

**Heartbeat confirmed (2026-07-10 13:06 MST):** first natural 30-min heartbeat landed — `Heartbeat - uptime: 0h 30m, RSSI: -50dBm, status: ok`. Watchdog wildcard pickup confirmed.

**Removed the `Status: X -> Y` log line (2026-07-10):** the `on_message` handler used to log every status transition to `.../log`, but review found it added no real value — Node-RED's own `fn_threshold` logging (`[Sensor] Salt: X% (Y cm)`, `CRITICAL — salt at X%...`) already covers the meaningful transitions in plain language, and the ESP32-side log was actively misleading: dashboard history showed `unknown -> offline` / `offline -> ok` entries that never came from Node-RED (confirmed — `offline` doesn't appear anywhere in `salt-sensor.flow.json`). Root cause: a fossil from early migration testing, before `birth_message:` was disabled — ESPHome's default birth/will strings (`online`/`offline`) briefly collided with this same `/status` topic. Not reproducible under current firmware, but the confusion it already caused wasn't worth the code. Removed `prev_status`/`status_changed` globals along with it; `current_status` still drives the LEDs, just silently.

**12h natural reading cycle confirmed (2026-07-11):** the last open verification item — the 15-sample-median 12h reading firing on its own timer, not just via the on-connect immediate-reading code path — is now confirmed. Two standalone readings (no adjacent MQTT connected/disconnected/online event, unlike every on-connect-triggered reading in the log) landed exactly 12 hours apart: `2026-07-11 01:17:37 MST — Salt: 98% (20.9 cm)` and `2026-07-11 13:17:37 MST — Salt: 95% (21.5 cm)`. Periodicity confirmed via the dashboard log (`http://192.168.1.117/log`), closing the card's last open condition.

---

### CARD-0056 · [enhancement] [kanban-board] Persistent visual kanban board — RESOLVED 2026-07-11
**Status:** Done

**Notes:** Raised 2026-07-11: every time the board gets summarized in chat, it comes out in a different ad hoc format and scrolls out of view while working, with no stable place to return to it. Agreed approach: a browser-hosted Artifact with a persistent URL, redeployed to the same link whenever `kanban-board.md` changes, rather than a fresh chat message each time.

Built as a single self-contained HTML page (no external requests, per the Artifact sandbox) — a blueprint-styled board with one column per kanban state (Backlog, Planning, Design, Build, Done, Defer), each independently scrollable and collapsible, card tiles that expand in place for full notes, a live text search across id/title/tag/notes, and type filter chips (bug/enhancement/idea). Card data is baked into the page at build time as a JSON blob, not read live from the repo — so it goes stale exactly the way any snapshot does, and needs a manual regenerate-and-republish pass after edits, same discipline as keeping any other doc in sync.

`backlog.md` was renamed to `kanban-board.md` in this same session (2026-07-11), with references updated across README.md, CLAUDE.md, JCTsh-Operating-System.md, and the photo-server docs that pointed to it by name.

**Live-parsing alternative considered, not pursued (2026-07-11):** discussed serving the board from the Pi's existing `log_server.py` with a route that parses `kanban-board.md` live on each request instead of reading baked-in JSON, which would remove the manual-regenerate step entirely. Real cost surfaced in the same discussion: the repo isn't cloned on the Pi (deploys there are one-off `scp`, per `SOFTWARE-ENVIRONMENT.md`), so `kanban-board.md` would still need to be pushed to the Pi on every edit — the live-parsing win only fully lands once that push is also automated. Decision: stick with the manual artifact-regenerate workflow for now and see how the discipline holds up in practice; revisit the Pi version if manual regeneration turns out to be too easy to forget.

**Resolution:** page published and confirmed viewable at a stable claude.ai URL. Regenerate-after-edit discipline exercised twice already (title/collapse-default fix, then a CARD-0056 text sync) and explicitly agreed to as the ongoing approach. Closed 2026-07-11 — Joseph confirmed sticking with this version and directed the commit.

---

### CARD-0052 · [idea] [infrastructure] JCTsh Team Operating System (TOS) — RESOLVED 2026-07-11
**Status:** Done

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
**Status:** Done

**Notes:** Discovered 2026-07-09 following up on CARD-0042 — Joseph reported a specific HEIC photo (`IMG_20260625_165423.heic`, Robin's account) with a fine-looking thumbnail but a visibly distorted full image (elongated heads). Checked the asset directly via `/api/assets/{id}`: `width`, `height`, `exifImageWidth`, `exifImageHeight`, and `orientation` all `null` — Immich never successfully extracted this file's real dimensions/orientation, which plausibly explains the distortion (wrong aspect-ratio assumption during preview rendering). Sampled 100 assets per account: **Joseph 0/100 null width; Robin 89/100 (89%)** — same lopsided pattern as CARD-0037/CARD-0039/CARD-0042, again far worse for Robin despite her "clean" import history.

Triggered `metadataExtraction` via `PUT /api/jobs/metadataExtraction` (`{"command":"start"}`) — unlike CARD-0042's thumbnail gap, this one *is* partially caught by the normal queue trigger: 13,311 assets queued immediately. However this is likely not the full picture — some assets (like the specific HEIC file that started this) may be marked "complete" in the database despite holding null values, the same DB-vs-reality mismatch pattern as CARD-0042, which would need the same forced per-asset fix (`refresh-metadata`, another valid job name on the same `/api/assets/jobs` endpoint used for CARD-0042's `regenerate-thumbnail`).

**Paused here by design (2026-07-09):** M8 load hit 12.64/12 cores with CARD-0030's backup, CARD-0042's thumbnail regen, and this metadata extraction all running concurrently — Immich API was still responsive (45ms ping) so nothing was failing, but Joseph asked to let the current jobs finish before adding a full forced `refresh-metadata` sweep across Robin's ~77,123 assets. The 13,311 already queued will keep processing in the background regardless.

**Closed 2026-07-10 — all four conditions verified live:** (1) `metadataExtraction` queue confirmed fully drained via `GET /api/jobs` (0 waiting/active/failed); (2) a fresh 150-asset sample of Robin's library showed 0/150 null width (top-level `width` field — the list endpoint doesn't return `exifInfo` inline, this superseded the original per-asset `exifImageWidth` check method but confirms the same thing); (3) `IMG_20260625_165423.heic` re-checked directly: `exifImageWidth 4032`, `exifImageHeight 3024`, `orientation 1` — all populated, no longer null; (4) Robin's null-width rate (0%) now matches Joseph's baseline (0%).

---

### CARD-0042 · [bug] [photo-server] Robin's library missing thumbnails for ~81% of assets — RESOLVED 2026-07-10
**Status:** Done

**Notes:** Discovered 2026-07-09 while troubleshooting Robin's phone backup — Joseph noticed "Error Loading Image" on several thumbnails, both in the phone's local gallery view and (critically) in the web UI too, which ruled out a phone-side rendering glitch. Diagnosed via direct HTTP checks against `/api/assets/{id}/thumbnail`: a 150-asset sample came back 122/150 (81%) returning `404` for Robin, versus **0/150** for Joseph — confirmed real, server-side, and isolated to Robin's account. Root cause not pinned down (her import was the "clean" one per `migration.md`, yet has by far the worse thumbnail gap — consistent with the same pattern already seen in CARD-0037/CARD-0039 where Robin's account had the larger gap despite the cleaner import history). The standard `thumbnailGeneration` job queue didn't surface these (`waiting: 1` when triggered normally) because Immich's database already considered them complete — the gap is between DB state and actual thumbnail files on disk, not a "job never ran" situation like CARD-0037.

**Fix:** used the per-asset job endpoint (`POST /api/assets/jobs`, `{"name":"regenerate-thumbnail","assetIds":[...]}` — found via the same schema-discovery trick as CARD-0037/CARD-0039, sending an invalid body and reading the validation error's allowed values) to force-regenerate every one of Robin's 77,123 assets in 155 batches of 500. Confirmed working on a small scale first (9 known-broken assets, all fixed, verified via HTTP 200) before committing to the full-library run. Submitted successfully in full — `thumbnailGeneration` queue confirmed at 76,996 waiting immediately after. Verified live at every step (new photo from Robin's phone arrived with a working thumbnail, confirming upload itself was never broken — only historical thumbnails were affected).

Running concurrently with CARD-0030's backup verification and the tail end of CARD-0037/039's work; checked M8 load before committing to the bulk job (5.04/12 cores, comfortable).

**Closed 2026-07-10:** `thumbnailGeneration` queue confirmed fully drained (0 waiting/active/failed). Fresh 150-asset sample of Robin's library: 140/140 image/photo assets returned `200` on thumbnail (0% broken, matching Joseph's baseline). The sample also included 10 `.MP.mp4` assets (Pixel Motion Photo video sidecars) that returned `404` — investigated and confirmed **not a regression**: these are `visibility: hidden` linked video components, never meant to be fetched directly (the paired still-image asset each links to via `livePhotoVideoId` has its own working `200` thumbnail, which is what actually displays in the gallery/timeline). This is normal Immich behavior for motion photos, not the bug this card tracked.

---

### CARD-0051 · [enhancement] [photo-server] Extend heartbeat with disk-capacity and backup-staleness checks
**Status:** Done

**Notes:** Found 2026-07-11 during a health check + log-dashboard history review. CARD-0032/CARD-0046 made the heartbeat check that storage is *readable/writable*, but two real gaps remained:
1. **Disk capacity** — nothing checked how *full* a mount was. A drive filling up (primary or either backup) would degrade Immich or fail backups with no advance warning.
2. **Backup staleness** — CARD-0040 made `photo-library-backup.sh` report its own per-run success/failure, but nothing watched for the run simply not happening at all (cron broken, script missing, host down over a scheduled run) — an absence-of-signal gap the per-run report can't cover.

**Resolution:** `photo-server-heartbeat.py` now checks `shutil.disk_usage()` on all three mounts (`/mnt/photo-library`, `/mnt/photo-library-backup`, `/mnt/photo-library-backup-joseph`) every 30-min cycle, flagging degraded via the existing `unhealthy`/Alert path if any exceeds 90% used. `photo-library-backup.sh` now touches `/home/jct/photo-library-backup-success.stamp` only on the fully-successful path (both rsync jobs exit 0); the heartbeat script checks that marker's age and flags degraded if missing or older than 9 days (one missed weekly Sunday 2am run + 2-day grace). Both reuse the existing `unhealthy` list / dashboard Alert / `status: degraded` payload — no new MQTT topics or schema.

**Live-tested 2026-07-11:** staleness check fired correctly (`backup:stale (no successful run recorded)`) immediately after deploy since no stamp existed yet — confirmed on the dashboard. Capacity check verified by temporarily dropping the live deployed threshold to 1% and confirming all three mounts correctly reported (`primary-capacity:68% used, backup-robin-capacity:35% used, …`), then restored to 90% and diffed byte-for-byte against the repo version. Ran the real `photo-library-backup.sh` end-to-end (not a simulated success) — both rsync legs completed, stamp file written, and a final heartbeat run confirmed `status=online` with no unhealthy items, leaving the live system in a genuinely healthy state post-test.

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

First deploy attempt crashed on the state-file write (`/etc/jctsh/` isn't writable by the `jct` user, appropriately, since it holds credentials) — moved the state file to `/home/jct/.jctsh/` and added `os.makedirs`. Verified live 2026-07-10: first corrected run notified correctly (`v3.0.2` vs. running `v3.0.1`), confirmed on the dashboard; second run correctly skipped re-notifying for the same version. Added to `jctsh-network.md`'s Scheduled Maintenance Windows table (6:00 AM daily, no conflicts with existing jobs). Actual update application remains a deliberate manual step, not automated.

---

### CARD-0022 · [enhancement] [infrastructure] Security hardening — infrastructure audit (Steps 1–8)
**Status:** Done

**Resolution:** All 8 steps complete. Steps 1–5 and 8 passed clean or were fixed on 2026-06-20 (SSH key-only auth, MQTT auth, port audit, Node-RED adminAuth). Step 7 (HA MFA) done 2026-07-09: TOTP enabled for both Joseph and Robin via HA profile → Multi-Factor Authentication Modules. Step 6 (router UPnP) done 2026-07-09: found enabled with zero registered clients, disabled with no functional impact. Full findings in `jctsh-security-hardening.md`. Patterns harvested to `JCTsh-Build-Standards.md` §10 Security Standards (v1.14).

---

### CARD-0023 · [enhancement] [infrastructure] Security hardening — cloud accounts (Steps 9–14 + Final)
**Status:** Done

**Resolution:** All steps complete. Steps 9–12 and 14 passed clean 2026-06-20 (Ring/Amazon, SmartThings, Google ×2, Windows machine — one stale SmartThings connected app, SharpTools, revoked). Step 13 done 2026-07-09: router admin password rotated to a new strong unique password (`credentials.local.md`), remote/WAN management confirmed disabled, DNS confirmed intentional (CenturyLink/Quantum Fiber bypass-modem setup), firmware found one version behind (1.5.2 → 1.5.3 available) with auto-update now enabled (nightly 3–5 AM) rather than relying on manual checks going forward. Final Step complete: findings harvested to `JCTsh-Build-Standards.md` §10 Security Standards (v1.14).

---

### CARD-0039 · [bug] [photo-server] Re-verify Takeout import completeness — 3,433 assets were genuinely missing
**Status:** Done

**Resolution:** Following up on the original migration verification discussion, and given CARD-0037 had just found a large ML-processing gap from the same import, re-ran `immich-go upload from-google-photos` (real run, not `--dry-run`, so gaps found would get fixed immediately) against all retained Takeout zips for both accounts — `/mnt/photo-library-backup/takeout-staging/joseph/` (9 zips), `/home/jct/takeout-staging/joseph/` (3 zips), `/home/jct/takeout-staging/robin/` (5 zips). Used the same `--on-errors continue --pause-immich-jobs=false` flags that fixed the original migration's crash patterns, plus `--no-ui --log-file=...` this time for a persisted per-pass log (a gap in the original run). Launched fully detached via `nohup ... & disown` directly on the M8 so it survived independent of the SSH session — relevant since the home internet/network was intermittently down around this time.

**Result:** ran clean in a single pass, no restarts needed, zero upload errors. Found **3,433 assets that were genuinely missing** from Immich and uploaded them (zero data loss risk — upload-only, nothing deleted): 58 (Joseph, backup-drive zips), 119 (Joseph, NVMe-staged zips), 3,256 (Robin). Also found 109 cases where the server's copy was upgraded (better-quality version found in the zip) and 160,701 correctly-matching duplicates confirmed (skipped, no re-upload).

**Notable finding:** Robin's pass had by far the largest gap (3,256 missing) despite her original import being documented as the "clean" one with no crashes/restarts (see `components/photo-server/migration.md`) — this means the missing-asset gap was not caused solely by Joseph's chaotic 5-restart import as originally assumed. Combined with CARD-0037's finding that Robin's ML-processing gap was also worse than Joseph's (96% vs ~80% zero-face rate), there's a consistent pattern that something affected both imports similarly regardless of which one crashed — most likely some shared infrastructure/timing factor from both multi-day imports running through the same M8 around the same period. Root cause not further investigated since the fix (re-run to catch anything missing) resolves it regardless of cause, same reasoning as CARD-0037.

Full run logs retained on the M8 at `/home/jct/immich-go-verify-20260709/` (`joseph-backup.log`, `joseph-home.log`, `robin.log`, `run.out`).

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

### CARD-0036 · [enhancement] [infrastructure] Dashboard visibility for scheduled reboots
**Status:** Done

**Resolution:** CARD-0035's scheduled reboots were invisible on the JCTsh log dashboard — confirming success required manually SSHing in and checking `systemctl`/`docker ps`. Added a matched pair of MQTT log messages around each reboot: `scheduled-reboot.service` now publishes `"Scheduled reboot about to occur."` immediately before calling `/sbin/reboot` (multiple `ExecStart=` lines in the oneshot unit), and a new `reboot-complete.service` (enabled via `WantedBy=multi-user.target`) publishes `"Boot complete."` on every boot once the MQTT broker is reachable. Pi publishes as component `jctsh-core` to `jctsh/core/log-server/log` using the existing `jctsh-log-server` MQTT account (`/etc/jctsh/log-server.env`) via `mosquitto_pub` (already installed). M8 publishes as component `photo-server` to `jctsh/server/photo-server/log` using the existing `photo-server` MQTT account (`/etc/jctsh/heartbeat.env`) — required installing the `mosquitto-clients` apt package on the M8 (the heartbeat script uses Python `paho-mqtt` instead, so the CLI wasn't already present). Neither message uses the `"Heartbeat - "` prefix, so each occurrence stays visible as its own dashboard row rather than collapsing. Per-host unit files split out: `scheduled-reboot-pi.service`/`scheduled-reboot-m8.service` replace the old shared `scheduled-reboot.service` (now host-specific since the MQTT broker address, credentials file, and topic differ per host). Verified live 2026-07-08 via manual `systemctl start reboot-complete.service` on both hosts — confirmed on the dashboard (`/data` live view and, after flushing, the persisted `/log` file).

---

### CARD-0037 · [bug] [photo-server] ML processing (faces, smart search, duplicates, OCR) never ran on a large fraction of the library
**Status:** Done

**Resolution:** Discovered 2026-07-08 while answering Joseph's question about why most photos showed no identified people in Properties. Diagnosed via the Immich API (not guesswork): a random sample showed ~80% of assets with zero detected faces; a targeted CLIP-search sample of clearly-portrait photos still showed clean detection (26/30 correct), ruling out a model-confidence issue. Definitive proof came from a duplicate pair — the exact same restaurant photo (Immich's own duplicate-detection linked the two copies) had 7 faces detected on one copy and 0 on the other.

**Not specific to Joseph's chaotic import:** checked Robin's library too (via her own API key, since search is scoped per-user) — 96% zero-face rate, even higher than Joseph's ~80%, despite her import running clean with no crashes/restarts (see `components/photo-server/migration.md`). This ruled out the 5-restart-import theory as the sole cause and confirmed the gap was server-wide, affecting both accounts roughly equally.

**Fix:** triggered all five affected ML jobs (`faceDetection`, `facialRecognition`, `smartSearch`, `ocr`, `duplicateDetection`) via `PUT /api/jobs/{name}` (`{"command":"start"}`) — Immich has no dry-run mode, so starting each job was simultaneously the diagnostic (revealing real backlogs: ~140,000 for faces, 33,201 for duplicates, ~17,000 each for smartSearch/OCR) and the fix. Checked load average and `vmstat` before/during (CPU-bound at ~60% user time, only 3-7% iowait — not I/O-bound, plenty of headroom on the 12-core M8) to confirm it was safe to run all five concurrently.

**Confirmed complete 2026-07-09** (ran overnight, unaffected by an unrelated home-internet outage since the jobs run locally on the M8): all five queues back to 0 waiting/active, 0 failed for the entire run. M8 uptime at completion check was 19h36m — never rebooted, confirming genuine completion rather than a state reset. Total people clusters grew 2,626 → 3,331 (+705) as full coverage let previously-under-threshold clusters (`minFaces: 3`) surface. Final spot-check: the `868900f1` duplicate that started the whole investigation at 0 faces now shows all 7, with Joseph and Robin correctly matched by name. `duplicateDetection` found 2,197 duplicate groups total once it had full coverage — worth a manual review pass in the Duplicates view when convenient, not urgent.

---

### CARD-0035 · [enhancement] [infrastructure] Weekly scheduled reboot — Pi and M8 photo-server
**Status:** Done

**Resolution:** Deployed systemd timers on both hosts: `scheduled-reboot.timer` → `scheduled-reboot.service` (`/sbin/reboot`), `Persistent=true`. Pi: Monday 3:00 AM. M8: Monday 4:00 AM — staggered one hour later so the M8 heartbeat script's MQTT publish to the Pi's Mosquitto broker doesn't collide with the Pi being mid-reboot. Not synchronized to KeepConnect's own weekly router reset — that schedule has drifted from its original Wednesday setting, most likely because its "every 7 days" timer restarts from any reset (scheduled or outage-triggered), so it can't be relied on as a fixed weekday anyway; a router reboot's brief network blip is tolerated regardless of timing. Version-controlled unit files in `core/maintenance/`; documented in `SOFTWARE-ENVIRONMENT.md` (Pi) and new `components/photo-server/operations.md` (M8). Verified live via `systemctl list-timers` on both hosts — next run confirmed Mon 2026-07-13. 2026-07-08.

---

### CARD-0033 · [idea] [infrastructure] Document Keep Connect configuration and schedule
**Status:** Done

**Resolution:** KeepConnect is a standalone router-rebooter device (Johnson Creative KeepConnect-27F8, not a JCTsh component). New dedicated doc `keepconnect.md` created at repo root with full device identity, network config, physical outlet-scoping rationale, and complete monitor/timing/schedule/notification configuration. Linked from `jctsh-network.md` devices table (IP 192.168.1.108, DHCP-reserved) and `ENVIRONMENT.md` Hub & Controller table; added to `README.md` repository layout. Remaining open item (scheduled Pi/Immich reboot via cron, separate from power-strip cycling) carried forward in `keepconnect.md` itself. 2026-07-08.

---

### CARD-0021 · [enhancement] [logging] Device status dashboard
**Status:** Done

**Resolution:** Added `/status` endpoint to `core/logging/log_server.py`. Two-section layout: Home (Online/Offline/? per component based on heartbeat presence and 70-min threshold) and Remote (`coachproxyos` always shows last-activity + `?`). Auto-detects heartbeat-capable components — salt-sensor shows `?` until CARD-0004 ESPHome migration adds heartbeats. Deployed to Pi 2026-06-30. Added CARD-0024 (coachproxy remote health monitoring via Tailscale ping).

---

### CARD-0018 · [idea] [immich] Self-hosted photo library
**Status:** Done

**Resolution:** Superseded. Hardware (GMKtec M8) in hand. Replaced by `components/photo-server/` (Immich install + immich-go migration) and `components/photo-tv-display/` (Node.js TV slideshow + phone companion) — full planning docs committed 2026-06-30.

---

### CARD-0014 · [enhancement] [core] Move environmental data pipeline to core
**Status:** Done

**Resolution:** Moved `environmental-data.gs` → `core/data-pipeline/`, `JCTsh-Environmental-Data-Architecture.md` → `core/data-pipeline/`, and `core/node-red/environmental-data.flow.json` → `core/data-pipeline/`. Updated references across 15 files (CLAUDE.md, README.md, Node-RED-workflow.md, JCTsh-Build-Standards.md, JCTsh-Component-Planning-Pattern.md, JCTsh-Property-Sensor-Pattern.md, all component planning docs, hiking-monitor instructions). 2026-06-30.

---

### CARD-0002 · [enhancement] [infrastructure] MQTT v3.1.1 → v5 upgrade
**Status:** Done

**Resolution:** Mosquitto 2.0.21 already supports v5 — no broker config change needed. Changed `protocolVersion` from 4 → 5 in the Node-RED broker config node (`core/node-red/core.flow.json`) and updated the live Pi flows.json in place. Confirmed via Mosquitto log: client `nodered-saltlevel` connected with `p5`. ESP32/ESPHome devices unaffected (remain on v3.1.1). 2026-06-30.

---

### CARD-0008 · [enhancement] [hiking-monitor] Pixel hotspot second WiFi field test
**Status:** Done

**Notes:** Confirmed 2026-06-17 during camping trip. Device connected to JCT Hotspot (IP 10.57.172.159 — Pixel hotspot subnet), reached home MQTT broker via jctsh.duckdns.org over cellular, replayed 7 SPIFFS readings on reconnect. DuckDNS + port 1883 forward confirmed working in the field.

---

### CARD-0017 · [enhancement] [infrastructure] Charging state schema fields for solar/battery sensors
**Status:** Done

**Resolution:** Added `solar_v` (solar panel voltage, V, ADC voltage divider) to the environmental data schema. Decision: `solar_v` chosen over `charging` boolean (not universally available on all charge controllers) and `charge_current_ma` (requires INA219, overkill). Combined with `battery_v`, charging state is derivable in Node-RED or Sheets as `solar_v > battery_v + ~0.3V`. Added to field reference and Sheets schema in `JCTsh-Environmental-Data-Architecture.md` (v1.4), column Z in `components/hiking-monitor/environmental-data.gs`, and Apps Script redeployed. 2026-06-15.

---

### CARD-0016 · [enhancement] [infrastructure] Offline flash logging — extract reusable standard
**Status:** Done

**Resolution:** Created `core/offline-logger/sensor_logger.h` — generic template header with `sensor_log_*` function prefix (adapt by renaming to `<name>_log_*` and updating the log file path). Added "Offline Flash Logging" section to `JCTsh-Property-Sensor-Pattern.md` with template adaptation instructions, on_boot mount snippet, on_connect replay block (500ms settle delay), and interval guard (connected → publish, offline → log_write). Removed CARD-0016 from pattern doc Open Gaps. 2026-06-14.

---

### CARD-0015 · [enhancement] [front-porch-temp-sensor] Environmental data pipeline integration
**Status:** Done

**Resolution:** Added SNTP, humidity/pressure IDs, and 5-min `/data` publish to firmware (temp, humidity, pressure, illuminance, lat/lon H8, rssi, ISO 8601 UTC). Added `illuminance_lx` to the environmental data schema and Apps Script. Node-RED wildcard caught it automatically — no flow changes. OTA flashed 2026-06-14.

---

### CARD-0007 · [idea] [hiking-monitor] Hiking observations pipeline (Tasker → Sheets)
**Status:** Done

**Resolution:** Tasker widget → Android speech recognition → HTTP POST to Apps Script → Hiking Observations sheet with automatic category classification. No keyword prefix — widget tap is the intent signal. Steps 23–26 complete 2026-06-13.

---

### CARD-0001 · [bug] [garage-radar] Garage-radar false presence on door close
**Status:** Done

**Resolution:** Ill-defined and no longer applicable — closed.

---

### CARD-0090 · [enhancement] [hiking-monitor] Tasker "Log Observation" widget cuts off recording too early on normal speech pauses
**Status:** Defer

**Notes:** Raised 2026-07-24. Joseph reports the Tasker voice-observation widget (CARD-0007, Steps 24-25 — "Log Observation" task, **Get Voice** action → `%VOICE` → POST to Apps Script) stops recording too eagerly, not allowing enough time for normal mid-sentence pauses while speaking an observation.

**Root cause investigated:** confirmed via Tasker's own action documentation that **Get Voice** only exposes two configuration fields — a **Language Model** hint and an overall **Timeout** (max wait before giving up if nothing is heard at all). Neither controls mid-speech pause tolerance. That behavior is governed one level down, by the underlying Android speech recognizer's own silence-detection threshold, which Get Voice doesn't expose or let you configure.

**Fix path identified, not yet built:** swap the task's first action from **Get Voice** to Tasker's **Send Intent** action, targeting `android.speech.action.RECOGNIZE_SPEECH` directly with a custom extra:
- Key: `android.speech.extras.SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS`
- Value: a larger millisecond figure (e.g. `3000`) than whatever the recognizer's current default is

**Real caveat, not just an implementation detail:** Android's own documentation for this extra explicitly warns it's rarely used and *"may have no effect"* depending on the recognizer implementation (on-device vs. Google's cloud recognizer may not honor it identically) — this is not a guaranteed fix, just the one real lever that exists.

**Alternatives if the above doesn't pan out (not evaluated further):** break a long observation into multiple quick separate widget taps instead of one continuous dictation; or replace Get Voice with the **AutoVoice** plugin (same Tasker developer), which has its own recognition settings that might expose pause tuning more reliably — not confirmed, would need its own investigation.

**Deferred 2026-07-24 — Joseph's explicit call:** "I'll live with it as it is." Not worth the Send Intent rebuild (and its uncertain payoff) right now. Revisit if it becomes enough of a real pain during actual hikes.

**Related:** CARD-0007 (Hiking observations pipeline — the task this widget belongs to, Done), `components/hiking-monitor/hiking-monitor-claude-code-instructions.md` (Steps 24-25, original Tasker task build instructions).

---

### CARD-0074 · [idea] [hike-izer] Hike-izer Version 2 — SUPERSEDED, split into individual feature cards
**Status:** Defer

**Superseded 2026-07-23:** Joseph decided to move away from batching features into a versioned release after v1 — feature-driven instead, each item tracked as its own card. Split as follows: **Photos** → CARD-0084, **Hiker's own compass/heading** → CARD-0085, **Automatic triggering** → CARD-0086. **Historical weather** dropped entirely (not carried into any new card — distinct from CARD-0083, which covers forecast-at-hike-start, not actual-conditions history). **Rendered web page output** already covered by CARD-0081 (filed independently, same day, before this split happened). Kept here for the original batch's context and reasoning; the "Version 2" grouping concept itself is retired, not just this card.

**Notes:** Raised 2026-07-18, split out from CARD-0073's closure (v1 done). Carried forward the items v1 explicitly deferred, not forgotten:

- **Photos** — Immich integration (`photo-server`) unbuilt; would need an API query matched to a confirmed hike's date/time range and GPS bounding box.
- **Historical weather** — no source picked yet. Note: for a past hike, this means an actual-conditions lookup, not a live forecast.
- **Hiker's own compass/heading** — still a real gap; no sensor captures which way the hiker was facing (v1 only computes the *sun's* compass direction, from pure astronomy). Would need new instrumentation or a different data source, not just more analysis.
- **Automatic triggering** — v1 is on-demand only.
- **Rendered web page output** — v1 is Markdown only; if this happens, output goes in `hike-izer/summaries/` alongside the Markdown, per the code/output separation already established (`components/hike-izer/README.md`).

**Blocking dependency: the hiking-monitor device needs to be operational.** V1's real test data came from the June 15 trip (June 17/18 hikes) — that's the only confirmed-good dataset that exists. The 2026-07-18 run found the device producing **zero** Environmental Data readings that day despite real observations/GPS activity happening (see CARD-0073's resolution) — status unconfirmed: deployed? charged? powered on? Carried forward individually into each split-out card above, since each still needs fresh real hiking data to build and verify against.

**Related:** CARD-0073 (v1, Done) for the full build history and what's already working; `components/hike-izer/README.md`, `.claude/skills/hike-izer/SKILL.md`, `components/hike-izer/fetch_hike_data.py`.

---

### CARD-0027 · [idea] [hiking-monitor] GPIO-controlled power gating for I2C peripherals during sleep — SUPERSEDED by CARD-0070
**Status:** Defer

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
**Status:** Defer

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

---

### CARD-0115 · [bug] [hike-izer] Hike Start Forecast only captures once per calendar day, not once per hike session — RESOLVED 2026-07-30 13:55 MST
**Status:** Done

**Raised 2026-07-29 15:30 MST**, investigating why the day's second hike (CARD-0113's Frederik Meijer Gardens hike) had no Weather Forecast at Hike Start section at all.

**Confirmed directly against real data:** re-fetched the whole day's data — exactly one `Hike Start Forecast` row exists for 2026-07-29, timestamped `11:07:57Z`, matching the *first* (morning) hike. The afternoon hike's own first GPS point (`16:31:21Z`) never captured its own forecast.

**Root cause, confirmed in `core/data-pipeline/environmental-data.gs`:** `_maybeCaptureHikeStartForecast()`'s dedup check scanned the `Hike Start Forecast` sheet for any existing row matching `date_local` — i.e. it captures at most once per *calendar day*, full stop, regardless of how many separate real hikes happen that day. This is the same "event = a day, not a session" gap CARD-0113 already fixed on the Python/hike-izer side, just not yet extended to this Apps Script mechanism, which still runs on the old model. Two real hikes hours apart can have genuinely different weather (morning vs. afternoon); silently reusing (or in this case, simply omitting) the first hike's snapshot for the second was wrong.

**Fixed in the repo, 2026-07-29 (`core/data-pipeline/environmental-data.gs`, not yet deployed — see below):**
1. Replaced the `date_local`-based dedup scan with a session-gap check against `GPS Track`'s own history: if the gap since the immediately preceding GPS point exceeds `SESSION_GAP_MIN` (10 minutes — deliberately kept in sync with `fetch_hike_data.py`'s own `session_gap_min=10`, since this is approximating the same "is this a new hiking session" judgment in real time that the Python pipeline later makes in batch), this is a new session and a forecast is captured. Fewer than 2 real rows in `GPS Track` (i.e. the very first GPS point ever) is trivially a new session too.
2. Moved the new gap check to the very start of the function, before the sheet-creation work and the Open-Meteo call — avoids wasting an external API call on every single GPS point during an active hike, not just avoiding the dedup bug.
3. `date_local` is still recorded in the output row (useful for reading the sheet), it's just no longer what dedup is keyed on.
4. `SCRIPT_VERSION` bumped to `2026-07-29.1-hike-start-forecast-session-scoped`.

**Deployment note:** this is Apps Script, deployed by pasting into the Apps Script editor (no `clasp`/CI tooling in this repo) — I can't deploy it myself. **Needs Joseph to paste the updated `_maybeCaptureHikeStartForecast` function (and the new `SESSION_GAP_MIN` constant above it) into the Apps Script editor and redeploy**, same as CARD-0106's own deployment.

**Deployed and confirmed 2026-07-29 15:36 MST** — Joseph pasted and redeployed; `action=version` confirmed live at `2026-07-29.1-hike-start-forecast-session-scoped`.

**Verified against a real multi-hike day, 2026-07-30 13:55 MST.** Joseph did a genuine second hike today (16:33–16:46 local, generated as `2026-07-30-2` per CARD-0113's naming). Re-fetched the whole day's data: exactly **two** `Hike Start Forecast` rows, one per hike, each matching its own real start time — `11:36:28Z` (63.1°F, 81% humidity, UV 0.45) for the morning hike, `20:33:29Z` (84.4°F, 34% humidity, UV 5.25) for the afternoon one. Physically consistent morning-vs-afternoon weather, not a dedup artifact reusing one snapshot. Closing criterion met.

**Related:** CARD-0113 (the session-vs-day redesign this extends to the Apps Script side), CARD-0106 (original GPS-triggered capture this builds on), CARD-0083/CARD-0097 (original feature and its timezone fix), `core/data-pipeline/environmental-data.gs`.

---

### CARD-0116 · [bug] [hike-izer] Second same-day hike's photo thumbnails 404 — templating.py referenced the wrong photo directory — RESOLVED 2026-07-29 15:44 MST
**Status:** Done

**Raised 2026-07-29 15:40 MST** — Joseph reported no thumbnails displayed on the second hike's page, and clicking a photo produced a 404.

**Root cause, confirmed directly:** `2026-07-29-2_photos/` on the M8 has the real files (confirmed via `ls`), but the live `2026-07-29-2_hike-summary.html` referenced `2026-07-29_photos/...` — missing the `-2` — for every `<img src>` and `<a href>`. `templating.py`'s `render_html()` built the photo directory reference from `date_str` (the plain calendar date), not from `file_stem` (the actual on-disk directory name, `<date>` for the first hike of a day, `<date>-2` etc. for a later one). This is a real gap in CARD-0113's own work: `file_stem` was threaded through `generation.py` for every file-*writing* path, but `templating.py` — which builds the *reference* paths inside the rendered HTML — was never updated to receive or use it, so it silently fell back to the plain date. Invisible on any day with only one hike (file_stem and date_str are identical then), which is why this wasn't caught until a real second-hike day happened.

**Fixed 2026-07-29:**
1. `templating.py`'s `render_html()` gained a `file_stem=None` parameter; `photos_dir` is now built from `file_stem or date_str` (falls back to the old behavior if a caller is ever missed, rather than hard-crashing).
2. `generation.py`'s two `render_html()` call sites (step 1 and step 2) both now pass `file_stem=file_stem`.

**Verified locally:** re-rendered against the real second-hike data — without `file_stem`, photo paths read `2026-07-29_photos/...` (the bug); with `file_stem='2026-07-29-2'` passed, they correctly read `2026-07-29-2_photos/...`. Title/H1 unaffected (still correctly date-only, via `format_date_display(date_str)` — confirmed no crash from a `file_stem` with a `-N` suffix reaching date parsing anywhere).

**Deployed and confirmed live 2026-07-29 15:44 MST.** `2026-07-29-2_hike-summary.html` was re-rendered locally (reusing the existing narrative text and photo manifest — zero additional API cost, no narrative regeneration) with the fixed `templating.py`, then pushed into place on the M8. Verified: a real thumbnail URL now returns `200`, not `404`; the live page's `<a href>`/`<img src>` all correctly read `2026-07-29-2_photos/...`.

**Related:** CARD-0113 (introduced `file_stem`/multi-hike naming; this closes the one place it didn't get threaded through), `components/hike-izer-orchestrator/templating.py`, `components/hike-izer-orchestrator/generation.py`.

---

### CARD-0117 · [bug] [hike-izer] Photo captions never persisted to disk — a manifest re-read loses them silently — RESOLVED 2026-07-29 15:51 MST
**Status:** Done

**Raised 2026-07-29 15:51 MST** — Joseph reported the CARD-0116 photo-path fix lost the real captions on `2026-07-29-2_hike-summary.html`.

**Root cause, confirmed directly:** `photo_captions.py`'s `caption_photos()` adds `caption`/`sign_text` to the in-memory manifest dict and returns it, but never writes the update back to `<photos_dir>/manifest.json` on disk. The originally-published page rendered fine because it used that in-memory object directly in the same run — but `manifest.json` itself, checked directly, never had a `caption` key at all. CARD-0116's fix re-rendered the page from a freshly-read `manifest.json`, which silently carried forward the caption-less version fetch_hike_photos.py originally wrote, discarding real, already-paid-for caption data with no error or warning.

**Fixed 2026-07-29** in `components/hike-izer-orchestrator/photo_captions.py`: `caption_photos()` now writes the captioned manifest back to `<photos_dir>/manifest.json` after captioning (wrapped in its own try/except — a write failure doesn't affect the current run, which already has captions in memory regardless; it only risks a *future* re-render missing them, same failure mode this card exists to close).

**Verified:** local test (temp dir, mocked captioning call) confirms the on-disk `manifest.json` correctly gains the `caption` field after calling `caption_photos()`. Deployed to the M8, container healthy.

**Recovered the lost captions, 2026-07-29 15:51 MST:** the original page's real captions were still recoverable from an HTML snapshot saved locally before CARD-0116's re-render — extracted all 41, matched cleanly to every asset in the manifest by ID, merged back in, and re-published `2026-07-29-2_hike-summary.html` a final time (captions restored, photo paths and distance both still correct from the two prior fixes). Also overwrote the stale on-disk `manifest.json` itself with the caption-restored version, so any future re-render of this same page won't lose them again.

**Related:** CARD-0116 (the fix whose re-render exposed this), CARD-0107 (original photo-captioning feature), `components/hike-izer-orchestrator/photo_captions.py`.

---

### CARD-0118 · [enhancement] [hike-izer] Calendar home page: multi-hike days need a real in-cell picker, not a tiny superscript number — RESOLVED 2026-07-29 16:30 MST
**Status:** Done

**Raised 2026-07-29 16:12 MST** — Joseph, looking at today's real two-hike day on the calendar home page: the date links to hike 1, and a tiny "2" (CARD-0113's `.cal-day-extra`, 0.6rem, corner-positioned) links to hike 2. Hard to notice, hard to tap, and doesn't scale past 2-3 hikes.

**Discussed and agreed design:** every logged day's cell shows the day number, then each hike for that day stacked below it as its own small link labeled with its local start time (e.g. `29` / `7:07a` / `12:31p`) instead of a bare index number. Zero-JS (matches the calendar's existing convention) and needs no extra click or page — CSS Grid rows auto-size to their tallest cell, so only a week containing a multi-hike day gets taller; other weeks are unaffected. Applies uniformly to every logged day (including single-hike ones) rather than special-casing hike #1 vs. later hikes, so there's one code path and one visual pattern.

**Acceptance criteria:**
1. `generation.py`'s step 1 (`run()`) records each hike's confirmed local start time (`start_ts`, raw UTC ISO) alongside `offset_str` in `<file_stem>_hike-summary.meta.json`.
2. `build_calendar_index.py` reads `start_ts`/`offset_str` per hike and renders a compact local time label (`7:07a` / `12:31p`) as that hike's link text, in place of the old day-number-is-hike-1 / tiny-extra-number scheme. Falls back gracefully (still a real, clickable link) for any existing meta.json written before this card that lacks `start_ts`.
3. Cell layout/CSS updated so day number + one-or-more stacked hike-time links render legibly at the calendar's small cell size, on both light and dark themes.
4. Verified locally against synthetic meta.json fixtures (0, 1, 2, 3 hikes/day) before deploying.
5. Deployed (orchestrator image rebuilt) and confirmed live — including backfilling today's two already-published hikes so the real motivating case renders correctly, not just future hikes.

**Implemented and verified locally, 2026-07-29 16:20 MST:** `generation.py`'s `run()` now records each hike's earliest confirmed session start (`start_ts`, raw UTC) alongside `offset_str` in the meta.json sidecar. `build_calendar_index.py` gained `_format_time_compact()` (stdlib-only, matching its existing convention) and now renders every logged day's cell as a day-number label plus one stacked link per hike, labeled with local start time (`7:07a`) instead of the old day-number-is-hike-1/tiny-corner-number scheme — applies uniformly whether a day has 1, 2, or 3+ hikes. Tested locally against synthetic fixtures for 0/1/2/3-hike days plus a meta.json missing `start_ts` (pre-CARD-0118 file) — falls back to a plain `#N` link, still real and clickable, not broken. Joseph reviewed the rendered size directly and called it "tiny but okay for now" — left as shipped; can be bumped later if it becomes a real problem in practice.

**Deployed and confirmed live 2026-07-29 16:30 MST.** `build_calendar_index.py`/`generation.py` scp'd to the M8, orchestrator image rebuilt and recreated (`docker compose build orchestrator && docker compose up -d orchestrator`). Backfilled today's two already-published hikes (their meta.json predates this card, so had no `start_ts`) by reading each page's own rendered `Time` stat (`7:07 AM` / `12:31 PM`) and writing the corresponding UTC `start_ts` directly via `docker exec` (container runs as root, matching the existing root-owned sidecar files), then re-ran `build_calendar_index.py` inside the container. Verified on both the M8 directly and the real public URL (`https://hikes.jctnet.com/`): today's cell now reads `29` / `7:07a` / `12:31p`, both links correctly pointing at their respective hike pages.

**Related:** CARD-0113 (introduced the multi-hike-per-day file-stem scheme and the tiny-number UI this replaces), `components/hike-izer/build_calendar_index.py`, `components/hike-izer-orchestrator/generation.py`.

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

**Raised 2026-07-30 05:18 MST**, spun off from CARD-0120's investigation. `app.py`'s webhook handler only ever calls `generation.run_and_log()` in response to a `gpsloggerevent=stopped` POST — nothing else triggers automatic report generation. If GPSLogger crashes, gets force-killed by Android, or its Tasker exit condition never fires, no webhook arrives and no page is ever generated for that hike — silently, with no error or alert surfaced anywhere.

**Not solved by CARD-0120.** That card only changes how session bounds are computed once a `stopped` event is actually received; it does nothing for the case where one never arrives at all. Both the old (Option A) and new (Option B) designs for CARD-0120 are equally exposed to this — it's a gap in the trigger itself, not in session-bounds calculation.

**Interviewed 2026-08-29.** Two design decisions confirmed (via AskUserQuestion):
1. **Recovery action: auto-generate the missed hike page**, not just alert-and-wait — it should show up late on its own rather than needing Joseph or Claude to notice and trigger it manually.
2. **Detection method: a periodic scan comparing GPS Track data against published hikes**, not a timeout tied to GPSLogger's own `started` event (its self-reported signals already can't be trusted for timing — see CARD-0120's own finding on `startedtimestamp`).
3. **Added same session, Joseph's call:** when a backstop recovery actually fires (step 3 below), publish a visible MQTT log line, not just a silent auto-generate — so a late-recovered hike is distinguishable on the dashboard from a normally-triggered one, not indistinguishable from business as usual.

**Real finding that simplifies this considerably: the detection logic this needs already exists and is already proven, not something new to build.** `generation.py`'s `_detect_session_window()` — already run today as part of *every normal* generation — probes the **whole local day's** GPS Track data and finds real hike-shaped sessions in it via gap-based detection (the same logic `fetch_hike_data.py`'s `is_hike` classification already proves out; built by CARD-0120 specifically because GPSLogger's own self-reported timestamps can't be trusted). Today it only ever runs *after* a `stopped` webhook arrives, to nail down session bounds — it never runs on its own initiative. This card is really "run that same day-wide probe proactively, on a schedule, instead of only reactively."

**Plan:**
1. **A daily scheduled check**, same shape as the existing `maintenance-check.py`/`pi-maintenance-check.py` pattern (a cron-driven script on the M8), probes each of the last few days' GPS Track data via the same day-wide session-detection `_detect_session_window()` already uses — real hike-shaped sessions, not raw point counts, so GPS noise (a car errand, GPSLogger left running) doesn't produce a false positive.
2. For each day that comes back with a confirmed hike session, check whether a matching published page already exists — same `*_hike-summary.meta.json` sidecar lookup `build_calendar_index.py`/`build_battery_trend_index.py` already use against `SRV_DIR`.
3. **A hike-shaped session with no matching page = the gap this card is about.** Auto-generate it: construct a synthetic payload with `local_datetime` set to the detected session's own end time, and call `generation.run()` — the same function the real webhook already calls, no separate code path needed. Since there's normally only one real hike per day, `_detect_session_window()`'s "closest session to the webhook's local_datetime" tie-break becomes moot when we're the ones supplying that value. **Publish an MQTT log line (`mqtt_log.publish_log`, category likely `Alert` or a distinct category — TBD at Build) noting a backstop recovery happened**, distinct from `run()`'s existing normal-path log lines, so it's visibly flagged as a late recovery, not silently indistinguishable from a normal generation.

**Real design snag found during Build, resolved — the plan's per-local-day approach turned out to conflict with an existing, explicit project rule.** `generation.py` has a twice-documented rule that nothing in it assumes the M8's fixed server TZ (America/Phoenix) is Joseph's actual current one — a hike can happen anywhere he's carrying his phone (the docstring's own cited real case: a hike on Eastern time). A per-local-calendar-day scan would need to guess an offset just to pick day boundaries, exactly the assumption that rule exists to prevent. **Redesigned around a rolling UTC window instead of calendar days** — one continuous probe (last `LOOKBACK_DAYS`, in UTC) rather than a per-day loop, and "does a page already exist" is checked by **time-range overlap** against every existing hike's own persisted `query_start_iso`/`query_end_iso` (`meta.json`, CARD-0214) rather than by guessed-date file existence — the same recency/range-based philosophy `_stems_recently_published()`/`latest_file_stem()` already use for this identical ambiguity, generalized here. Real, accepted limitation this doesn't solve (can't be solved): a backstop-recovered hike's displayed times use **UTC**, not a guessed local offset — the true one only ever arrives via the webhook payload this card exists to cover the absence of, and a wrong-but-plausible offset (e.g. silently assuming Phoenix) is worse than an honestly-wrong-looking one. Flagged in the recovery's own MQTT log line so it's never a silent surprise.

**Built and deployed, 2026-08-29:**
- New `components/hike-izer-orchestrator/backstop_check.py` — `_probe_recent_sessions()` (rolling-UTC-window version of `_detect_session_window()`'s day-wide probe), `_existing_query_windows()`/`_already_covered()` (the overlap check against `meta.json`), `_recover_session()` (constructs a UTC `local_datetime`, calls `generation.run()` — same function the real webhook already calls, no separate generation code path), `run_once()`. Scheduled via `start_background_thread()`, called once from `app.py`'s `main()`.
- **Cadence resolved:** daily at **5:00 AM** (Phoenix/container local time) — added as a new row in `jctsh-network.md`'s Scheduled Maintenance Windows table, chosen to sit clear of every other listed job (M8's own weekly reboot is Mon 4:00 AM) and comfortably before any realistic hike start, which also minimizes the (rare, low-consequence) chance of colliding with a genuine live webhook-triggered `run()` over `generation.py`'s shared `_IN_PROGRESS_MARKER` file.
- **Lookback resolved:** 5 days — wide enough to self-heal if the backstop check itself were down/deploying for a day or two, cheap since an already-covered session is skipped before any real work happens.
- **MQTT log category resolved:** `Alert` (not `System`) — a recovery firing at all means something upstream already failed silently (a missed webhook); the category should stand out on the dashboard, matching this project's existing convention for exactly that class of signal.
- Deployed: `components/hike-izer-orchestrator/*.py` (now including `backstop_check.py`) → M8, `docker compose up -d --build orchestrator` — image built, container recreated cleanly, confirmed no import/startup errors in `docker logs`.

**Verified live, 2026-08-29 — detection half.** Ran the actual detection logic (`_probe_recent_sessions()` + `_existing_query_windows()` + `_already_covered()`) against real production data via `docker exec`: found all 3 real hikes from the last 5 days (2026-08-25, 08-27, 08-29) and correctly matched every one against its existing published page — **zero false positives**, the more important direction to get right (a false positive would mean unwanted duplicate generation on a real, already-published hike).

**Recovery half verified live, 2026-08-29 — a real, deliberately simulated gap test, with a full backup/restore around it.** Joseph's go-ahead given. Backed up every file for the real 2026-08-25 hike (`.html`, `.meta.json`, `_photos/` — including real downloaded assets, `_staging/`, private `hike_data.json`) to a scratch directory on the M8, removed the live copies (so the check would see a genuine gap, not a simulation flag), then ran `backstop_check.run_once()` for real:

- Correctly detected 2026-08-25 as missing.
- `generation.run()` succeeded: re-fetched hike data, re-fetched 9 real photos from Immich, rebuilt the calendar and battery-trend indexes, **$0.0000 API cost** (step 1 only, as designed — no Claude call).
- Real, distinct MQTT Alert line confirmed on the live dashboard (`/mnt/jctsh-logs/jctsh.log`, not just printed locally): *"Backstop check: a hike's 'stopped' webhook was never received -- generated 2026-08-25 late from GPS Track data alone (displayed times are UTC, not local -- the real offset was never captured): https://hikes.jctnet.com/2026-08-25_hike-summary.html (API cost: $0.0000 ...)."*
- **Fully restored afterward**, not left in its recovered (data-only, non-enriched) state: copied all originals back via `docker cp` (sidesteps a host-vs-container file-ownership mismatch found along the way — the container writes these files as root, so host-level `jct`-user `rm`/`cp` couldn't touch them directly), rebuilt the calendar/battery-trend indexes once more against the restored data, then **diffed every restored file against the original backup byte-for-byte — all identical** (`.html`, `.meta.json`, `hike_data.json`, photos manifest). Confirmed live via the public site too (`curl` returned the original's exact byte size, 191485). Scratch backup directory cleaned up after confirming.

Both halves of the plan are now proven against real infrastructure, not just code review.

**Done when:** a real (or deliberately simulated) missed-`stopped`-event hike is auto-generated by the backstop check within one scheduled run of it actually being missed, with a distinct MQTT log line confirming the recovery — **met**, via the simulated test above.

**Related:** CARD-0086 (automatic triggering, the system this gap is in), CARD-0120 (the investigation that surfaced this, and the source of `_detect_session_window()`'s day-wide probe this design generalizes), CARD-0214 (the `query_start_iso`/`query_end_iso` persistence this design's coverage check depends on), `components/hike-izer-orchestrator/app.py`, `components/hike-izer-orchestrator/generation.py` (`_detect_session_window()`, `run()`, `_stems_recently_published()`/`latest_file_stem()` — the precedent for range/recency-based checks over calendar-date ones), `components/hike-izer-orchestrator/backstop_check.py` (new), `jctsh-network.md` (Scheduled Maintenance Windows — new row).

---

### CARD-0122 · [enhancement] [hike-izer] Automated staging: BirdNET Live phone Share → webhook → M8 staging directory — RESOLVED 2026-07-30 12:45 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 8004B, over the 5000B size threshold.

---

### CARD-0123 · [enhancement] [hike-izer] Make narrative generation opt-in; move place-context/sun-position data into tables instead of prose — RESOLVED 2026-07-30 14:50 MST
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 6077B, over the 5000B size threshold.

---

