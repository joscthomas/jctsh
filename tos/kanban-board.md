# JCTsh Backlog

Lightweight kanban. Each card has a **type** (idea | enhancement | bug) and a unique ID.

**Columns:** Backlog → Planning → Build → Done, plus **Defer** (off to the side — reachable from any stage)
- **Backlog** — captured, not yet being worked on
- **Planning** — being scoped/interviewed, and (if non-trivial) an implementation plan written — no separate Design checkpoint; the plan itself is the design artifact
- **Build** — going through the plan/implementation, including testing
- **Done** — complete
- **Defer** — a deliberate decision not to pursue for now (not abandoned, not forgotten — just consciously parked); can move here from any other column

<!-- next-card-id: CARD-0337 -->

---

### CARD-0336 · [bug] [hike-izer] Photo-based scat identification is unreliable -- same photo gets different species across models and runs

**Status:** Backlog

**Raised 2026-09-24 (Joseph: "the scat identified horse dung. that's a false positive... not doing so well with scat recognition"; then "is this current state and experiment in a card? make it so. no action now").** CARD-0308 (photo-based scat ID, Done 2026-09-23) has now produced a second wrong species in two hikes. Recording current state and the experiment so far; **no fix decided or built.**

**Current state (CARD-0308's pipeline, as deployed).** `photo_captions.py` makes one vision call per photo (`MODEL = "claude-opus-4-8"`, `max_tokens=400`), returning `caption`/`sign_text`/`scat_common_name`/`scat_scientific_name`; a species is reported whenever the model names one ("don't guess" is the only gate, no numeric confidence). CARD-0308's 2026-09-23 follow-up added the hike's GPS coordinates to the prompt so the model weighs geographic plausibility. Deliberately no species whitelist (Joseph, 2026-09-23: "location context first, watch it, no whitelist yet").

**The false positives so far.**
1. **2026-09-19, American Black Bear** -- no black bears in the Tucson/Marana area. Also the same physical pile as a photo already (correctly, per Joseph) identified as coyote, 6 s apart: two species for one object, no cross-photo consistency. The location hint fixed this one -- bear became implausible.
2. **2026-09-24 (15:12Z), "Horse dung"** -- Joseph: not horse ("everyone knows what horse scat looks like"), and **not cow either.** Looking at the photo: one dark, wet-looking, fibrous mass with ants, no separate balls. The location hint cannot help here (horse and cattle are both plausible locally). **Ground truth is unknown -- open question for Joseph: what was it?** Javelina is a strong candidate (two of the three models below say so; common in that desert) but that is unconfirmed.

**Experiment, 2026-09-24 -- three newer models on the same 10 scat-flagged photos (9/19 and 9/24), same prompt + location hint, run on the M8 via a standalone script against the thumbnails already on disk (no manifest/Sheet/page writes).** Baseline is the stored `claude-opus-4-8` result.
- **Not stable run to run.** Across two runs, Opus 5.5 said "none" then "Coyote" for `937777ae`, and Fable said "Coyote" then "none" for the same photo. Single-photo scat ID is close to a coin flip on hard cases; results shift with sampling, not just model.
- **Agreement (all three models, second run):** rabbit pellets -> desert cottontail (or rabbit-family); Coyote for `3aa57d64`, `053391e0`, `23312305`.
- **Disagreement:** horse photo `90184f24` -> Opus 5.5 and Fable "Javelina (Collared Peccary)", Sonnet 5 "Coyote", none "Horse"; the 9/19 coyote/"bear" pile (`88f129c4`, `15008cea`) -> Fable "Javelina", Opus 5.5 none, Sonnet 5 "Coyote"; `13c8eb5c` -> Sonnet 5 "Javelina", the other two none.
- **Opus 5.5 abstains most** (none on 5 of 10) and named no species I could identify as wrong -- consistent with "don't guess".
- **Gotcha:** the current `max_tokens=400` truncates the newer models (they spend part of it on reasoning before the answer) -- the first run hit `EOF while parsing` / `parsed_output is None` on many photos for exactly that reason and was discarded; the numbers above are from the rerun at `max_tokens=3000`. Any switch to a newer model must raise the cap.
- **Cost:** not priced (no dollar figures for the newer models on hand). Tokens for the 10 photos: Opus 5.5 47k in / 4k out, Fable 5.1 47k / 5k, Sonnet 5 47k / 2.8k. Input dominates (~4.7k tokens per photo image).

**Ideas discussed, none chosen:**
1. **Two stages** -- stage 1 stays as today but only flags "this is scat" (cheap); stage 2 runs only on flagged photos (~5 per hike) with a scat-specific prompt. Needed because a required "describe the scat first" field on the existing single call would be paid on *every* photo (Joseph: scat isn't known until the photo has been analyzed).
2. **Consensus** -- in stage 2, N independent calls (different models); report a species only when all agree, else leave it blank and caption "Animal scat". Applied retroactively to the 10 photos above, it would have suppressed the horse, the bear pair, and `13c8eb5c`, and kept the cottontail and the three agreed coyotes. ~15 extra calls per hike.
3. **Livestock** -- the prompt never mentions cattle/horses, which graze/ride locally; and whether domestic livestock dung belongs on the scat list at all is a Joseph decision (CARD-0308's page is framed as wildlife).
4. **Manual override file** (like the hiking-observations overrides) so Joseph can correct a wrong ID once and have the page and life list follow.
5. **Describe-before-naming** prompt field, applied in stage 2 only.

**Open questions:** (a) what the 9/24 horse photo actually is, and whether the cottontail and the other coyote calls are right (needed as ground truth to evaluate any of the above); (b) whether livestock dung is in or out of scope; (c) accept consensus-abstention as the answer, or invest in a stronger single pass.

**Data currently on the published pages (not corrected):** 2026-09-24's scat table lists Horse (1), and the Scat Detections Sheet/`scat_life_list.json` carry that row. Fix once the true ID is known.

**Related:** CARD-0308 (the pipeline this concerns, Done), `components/hike-izer-orchestrator/photo_captions.py`, `scat_life_list.py`, `generation.py`'s `_scat_location_hint()`.

---

### CARD-0335 · [enhancement] [garage-radar] [salt-sensor] Retrofit the boot-time heartbeat (Build Standards §4.1) onto the two remaining 30-minute-heartbeat ESPHome devices
**Status:** Backlog

**Raised 2026-09-24 19:04 MST (Joseph: "open card for Retrofitting the other ESPHome devices"), as the follow-up CARD-0333 named.** CARD-0333 proved the pattern on `front-porch-temp-sensor` and `back-patio-temp-sensor` and landed it as a standard (`JCTsh-Build-Standards.md` §4.1); this card applies it where the standard now says it is required.

**Current state, 2026-09-24 19:08 MST: Backlog — no work started, no device touched** (Joseph: "no action now"). Everything below is the scoping and procedure, ready for whenever the card is picked up.

**Scope, worked out rather than assumed — the false watchdog alert needs 2 × the heartbeat interval + reboot downtime > 35 min, i.e. an interval above ~15 min:**
| Device | Heartbeat | Verdict |
|---|---|---|
| `garage-radar` | 30 min | **Retrofit.** Has an `on_boot` already (priority -100: 2 s delay, then 3 LED blinks) — the new boot trigger has to coexist with it, which means converting `on_boot:` to a list of two entries. Heartbeat state key is `presence`. |
| `salt-sensor` | 30 min | **Retrofit.** Has an `on_boot` (runs the `led_self_test` script). Publishes under `jctsh/sensors/salt-sensor/…`, not `components/` (the watchdog wildcard `jctsh/+/+/heartbeat` covers it). Its reading interval is 12 h, so check what `current_status` holds at boot+90 s so the first heartbeat does not report something misleading. |
| `hiking-monitor` | 5 min | **Exempt.** Worst-case gap ≈ 10 min + downtime, well inside 35. (Home/upload-mode gating and deep sleep make its `on_boot` delicate — another reason not to touch it without need.) |
| `air-quality-monitor` | 5 min | **Exempt**, same reasoning; same delicate `on_boot`. |
| `photo-server`, `p-w-firefly` (non-ESP32, systemd timers) | 30 min | **Already compliant** — `OnBootSec=2min` + `OnUnitActiveSec=30min`. An independent precedent for the pattern. |

**Found while scoping — a documentation conflict to reconcile in this card:** `core/node-red/watchdog-README.md` says every ESP32 component publishes a heartbeat *every 5 minutes* and that the 35-minute window is "5-minute interval × 7", while `JCTsh-Build-Standards.md` §4.1 says 30 minutes and derives 35 as 30 + 5. Reality is both: four devices at 30 min, two at 5 min. The README's statement is stale and should say so.

**Procedure (each step exists because it went wrong on CARD-0333):**
1. Compile and flash from **native PowerShell**, never Git Bash (ESP-IDF refuses MSYS), in the space-free flash directory `C:\esphome\<name>\`, with the ESPHome pip package **pinned to 2026.4.5** (2026.9.0 broke the compile), using `--no-logs` so the command exits after upload.
2. **Both flash directories already hold old `.esphome` build caches** (from before the `jcthomas` → `Joe` profile change); front-porch's identical situation failed with `Access is denied` on the old profile path. Delete `C:\esphome\<name>\.esphome` (regenerable) before compiling.
3. Implement as CARD-0333 did: move the heartbeat publishes into a shared `script`, called by the `interval` and by a boot trigger that does `delay: 90s` → `wait_until: mqtt.connected` → `script.execute`.
4. **After flashing, wait past ~60 s before touching the device** (OTA rollback silently reverts an image that reboots inside that window), then confirm the device's *reported* config hash (retained discovery `sw` field) equals the build's `config_hash`.
5. Verify with a deliberate restart (button over MQTT): heartbeat at boot + ~90 s, no watchdog alert, 30-minute cadence continues, entities unchanged. **Compare builds by hash — never diff generated source** (CARD-0334's rule; a `main.cpp` diff is what printed device passwords last time).

**Non-goals:** no change to the heartbeat payload, the 30-minute cadence, or the watchdog flow; the two 5-minute devices and the two timer-based hosts are left alone.

**Done when:** (1) both devices flashed, the new firmware confirmed by reported hash; (2) after a deliberate restart of each, the heartbeat arrives ~90 s after boot with no watchdog alert, and the 30-minute cadence is seen to continue; (3) each device's HA/MQTT entities and consumers are unchanged (garage-radar's presence entities and automations; salt-sensor's HA switches and the Node-RED flow that owns its thresholds); (4) both YAMLs committed; (5) `watchdog-README.md`'s "every 5 minutes / × 7" statement reconciled with §4.1.

**Related:** CARD-0333 (pattern, evidence, and the OTA-rollback lesson), CARD-0331 (watchdog re-alert), CARD-0334 (never print secrets — applies to the flashing work), `JCTsh-Build-Standards.md` §4.1 v1.41.

---

### CARD-0334 · [bug] [tos] [mqtt] [homeassistant] [node-red] Rotate credentials printed into a 2026-09-24 session transcript, and adopt a never-print / always-REDACT rule for sessions
**Status:** Backlog
**Priority:** High — real exposure, not hygiene; the rotation policy in `credentials.local.md` treats a known transcript exposure as a rotation trigger.

**Raised 2026-09-24 18:54 MST (Joseph: "open a card for the password rotation (rule: do not print passwords, always REDACT them)").** *This card deliberately contains no secret values — credentials are named, never quoted.*

**Current state, 2026-09-24 19:08 MST (Joseph: "put all this in the card, no action now") — planning only; nothing below has been done.** No credential has been rotated; no Claude Code settings, hooks or permission rules have been changed; root `CLAUDE.md`, `credentials.local.md`, the Pi, the M8 and every device are untouched. The only things in force are the rule itself (recorded in the assistant's own session memory, which is not a durable home — see Done-when (2)) and this card. Decision 1 (where secrets live) was settled the same evening — see below; decisions 2–4 remain open, and the card stays in Backlog until Joseph answers them. **Amended 2026-09-24 21:21 MST:** a sequencing flaw in the first version of the plan was found and fixed (Phase 0 and a reconciliation step added — see the plan), and the Credential Manager's limits were recorded under decision 1. Still documentation only.

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
- **Phase 0 — a minimal machine store and helper, *before* any deny rule (added 2026-09-24 21:21 MST — the first version of this plan had a sequencing flaw).** Today `credentials.local.md` is the *only* source a session has for routine work — Home Assistant API calls and Pi-side MQTT peeks with the log-server account. Phase 1 denies reading that file; landed first, it would break that work with nothing to replace it. So first: put just the actively used secrets (the HA token and the log-server MQTT account, nothing else until a need is real) into the Windows Credential Manager, and build the minimal `sec` helper (`sec set`, `sec run`, `sec has|fingerprint`, `sec new`; see decision 1) plus the two or three wrappers that use it. Only once sessions can do their routine work *without* reading the file does Phase 1 deny it.
- **Phase 1 — mechanical guardrails (small; lands only after Phase 0).** (a) A checked-in project `.claude/settings.json` with `permissions.deny` on Read/Edit of `credentials.local.md`, `**/secrets.yaml`, `**/secrets.h`, `**/.env`, and `**/.esphome/**`, plus Bash/PowerShell deny patterns for the obvious dumps — best-effort only, since a shell has too many ways round a pattern, hence (b). (b) A `PreToolUse` hook on Bash, PowerShell, Read and Grep that blocks commands touching those paths or carrying secret-shaped literals (JWTs, `Bearer …`, `-P <value>`, `password=…`) and says where the safe helper is. (c) A `PostToolUse` tripwire that compares tool output with salted *fingerprints* of the current secrets (never the values) and secret-shaped patterns; it cannot un-print, but it ends silent exposure by telling the session at once — name the credential, open an incident. (d) Delete the build trees under `components/*/.esphome/` and keep builds in `C:\esphome\`.
- **Phase 2 — use without seeing.** A small helper under `tos/` backed by a store outside the repo tree: `sec run <cmd>` injects named secrets into the child process only and masks every known value and secret-shaped pattern in its output; `sec has|fingerprint <name>` answer without revealing. On top of it, wrappers for the recurring needs that caused this incident — Home Assistant API calls, Pi-side MQTT peeks with the log-server account, and an ESPHome `build-info`/reported-hash comparison that prints hashes and versions only. `credentials.local.md` shrinks to a **values-free index** (name, owner, where it lives, last-rotated date) plus Joseph's own recovery copy. **Store (decided, decision 1):** RoboForm stays Joseph's human system of record; the machine store is the Windows Credential Manager (DPAPI-backed, no new software); rotation bridges them with a generated value on the clipboard, never printed.
- **Phase 3 — shrink the blast radius (each is its own card).** One HA token per consumer, individually revocable; per-account Mosquitto ACLs (a device writes its own prefix and reads its own command topic; the log server reads all; HA gets the discovery prefix); fix CARD-0332; unique, strong OTA and MQTT secrets per device.
- **Phase 4 — process.** Put the rule in root `CLAUDE.md`'s Credentials section (correcting the "off-disk" claim) and in `JCTsh-Operating-System.md`'s Engineering Discipline; write the incident procedure (this card's pattern: name the credential, rotate by tier, Tier 1 within a day).
- **Suggested order:** Step 0 (reconciliation) → Phase 0 (minimal store + helper for the actively used secrets) → Phase 1 (deny rules + hooks; about an hour, and it stops recurrence) → rotation *using the safe path* → the rest of Phase 2; Phases 3–4 as separate cards.

**Decisions — 1 settled, 2–4 open; each open one carries the assistant's recommendation (a recommendation, not a decision):**
1. ~~**Where do secrets live for Phase 2?**~~ **DECIDED 2026-09-24 21:12 MST (Joseph, "yes, update the card" — accepting the recommendation): two roles, not one tool.** Joseph already uses **RoboForm**, which has **no scriptable interface** — checked, not assumed: v9.9.4.6 is installed on this workstation and ships only GUI tools plus a browser-extension host, no command-line executable; no official CLI or API turned up, only an unofficial, unsupported, reverse-engineered library, which is **not** to be used with these credentials. So:
   - **RoboForm is the human system of record** — where Joseph reads and records secrets, outside any session (this is also decision 3's bypass). `credentials.local.md` shrinks to a **values-free index** whose names match the RoboForm entries (for example a `JCTsh` folder: Logins for services, Safenotes for per-device secrets).
   - **The Windows Credential Manager (DPAPI-backed) is the machine store**, holding only the few values automation needs (for example the HA token and the log-server MQTT account); the Phase 2 `sec` helper reads from it.
   - **Rotation bridges the two without printing anything:** a helper generates the new value, stores it in Credential Manager, and places it on the clipboard (auto-cleared after ~60 s); Joseph pastes it into the RoboForm entry. One manual paste per rotation.
   - **What the Credential Manager does and does not do (so nobody over-trusts it):** entries are DPAPI-encrypted per Windows user and never sit in a plaintext file. But **any process running as Joseph — including a Claude session's shell — can read them through the Windows credential APIs, so it is an at-rest store, not a barrier against sessions.** The barrier is design plus Phase 1: sessions go through `sec run`, which never prints, and a hook blocks direct credential-API reads outside the helper (`CredRead`, `Get-StoredCredential`, `GetNetworkCredential`, `Get-Secret -AsPlainText`, and the like). It is local to this workstation (no sync); the values are lost or orphaned if the Windows profile is lost or the account password is reset from outside — which is why RoboForm stays the record; entries are limited to about 2.5 KB (ample for tokens); `cmdkey` can add and list but not read back; and the GUI reveals a value only after Windows re-authentication. Implementation route (a small wrapper over the credential APIs, or an existing PowerShell module) is decided when Phase 0 is built.
   - **Helper surface (Phase 0):** `sec set <name>` (masked prompt, run by Joseph in his own terminal); `sec run` (injects named secrets into the child process only and masks them in its output); `sec has|fingerprint <name>` (answers without revealing); `sec new <name>` (generate, store, and place on the clipboard for ~60 s).
   - **Not to do:** export RoboForm to CSV anywhere under `C:\Shared` (it recreates the plaintext master file); drive RoboForm's UI through screenshots (the values land in the transcript); use the unofficial API library.
   - *Still open under this decision:* how Joseph's RoboForm entries are organized today (folder names), so the index can mirror them. If scripted retrieval straight from a manager is ever wanted, KeePassXC or the Bitwarden CLI can do it, but that is not a reason to switch.
2. **Rotate now, or defer, per tier?** *Recommendation:* do Phase 0 and Phase 1(a)–(b) first, then rotate **Tier 1 the same day** — the HA long-lived token (widest blast radius; use CARD-0280's checklist), then the Node-RED admin password and the printed Mosquitto accounts — generating and installing the new values through a script so the rotation itself does not re-expose them. **Batch the ESP32 device secrets** (reflash required, and Phase 3 wants unique per-device values anyway) into one pass rather than flashing twice; do not leave them indefinitely, since they were exposed. Rotating *before* the guardrails exist is the riskier order, because the rotation is itself a secret-handling session.
3. **Approve Phase 1's hooks?** They change what *every* session may read. They can only land after Phase 0: until a machine store exists, `credentials.local.md` is the sole source for routine Home Assistant and MQTT work, and denying it first would break that. *Recommendation: yes*, scoped to the named secret paths and secret-shaped literals only. **Bypass for Joseph:** he can always read any of these files in his own terminal or editor *outside* the Claude Code session. Do **not** use the session's `!` prefix for this — its output lands in the conversation, i.e. it is the same exposure again. A session that genuinely needs a value should ask Joseph to run the masked helper (Phase 2), not to paste the value. Add an explicit, logged escape hatch only if that proves too blunt.
4. **Do Phases 2–4 become their own cards?** *Recommendation: yes, once Phase 1 has landed* — keep this card as the incident record plus rotation plus Phase 1, and open Phase 2 (store + `sec` helper + wrappers), Phase 3 (per-consumer HA tokens, Mosquitto ACLs, CARD-0332, unique device secrets) and Phase 4 (rule in `CLAUDE.md`/OS, incident procedure) as separate cards, since each is a project of its own.

**Rotation.** Follow `credentials.local.md`'s Credential Rotation Cadence tiers and the CARD-0076 precedent (itself a botched redaction). Suggested order by blast radius; **each credential's decision — rotate now, defer, or accept, with the reason — is Joseph's, recorded here:**
1. **HA long-lived token** — widest (Node-RED, photo-tv-display, hike-izer-orchestrator); use the CARD-0280 rotation checklist, which lists every place it lives.
2. **Node-RED admin password.**
3. **Mosquitto accounts** — the six above plus `hike-izer-orchestrator`, `front-porch-temp-sensor`, `back-patio-temp-sensor`. Each needs the broker change *and* the consumer's config; mind the `chown root:mosquitto /etc/mosquitto/passwd` gotcha, and that Home Assistant's own MQTT credentials are UI-only config.
4. **ESP32 OTA/MQTT secrets** (front-porch, back-patio, hiking-monitor) — need a reflash. Tier 3 in the policy is "incident-driven only", and this is the incident. Check first whether the four components really share values.

**Done when:** (1) every credential listed above is either rotated and verified live, or explicitly decided against with the reason written here; (2) the rule is in a durable place every session reads — root `CLAUDE.md`'s Credentials section — not only in a session's memory; (3) a one-time reconciliation has recorded where each secret lives (RoboForm / runtime file / Credential Manager / not stored), and `credentials.local.md` is a values-free index whose names match Joseph's RoboForm entries, and its rotation table shows last-rotated dates (dates only, never values); (4) the fix plan above is delivered or each phase explicitly deferred by Joseph — at minimum Phase 0 (the minimal store and helper) and then Phase 1's deny rules and hooks, in that order, because a rule that depends on a session remembering it has already failed once; (5) the as-is inventory above is kept current somewhere sessions read (and root `CLAUDE.md`'s inaccurate "off-disk" statement corrected).

**Non-goals:** no change to the credential storage scheme; no rotation of credentials not listed; no attempt to scrub the transcript.

**Related:** CARD-0076 (same failure class, first instance), CARD-0280 (HA token rotation checklist), CARD-0333 (where this happened), root `CLAUDE.md` Credentials section, `credentials.local.md` §Credential Rotation Cadence.

---

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

### CARD-0332 · [bug] [node-red] Home Assistant access token sits in plaintext in a world-readable `flows.json`

**Status:** Backlog

**Raised 2026-09-23 12:09 MST, found by CARD-0328's drift-check work.** Node-RED's own `global-config` node stores its environment variables in `/home/pi/.node-red/flows.json` in plaintext, including a long-lived Home Assistant access token, and that file is `-rw-r--r--` (readable by any local user on the Pi). Separately, a diagnostic command run during CARD-0328 printed that node in full, so the same token also appeared in a Claude Code session transcript on Joseph's workstation. Essence-only until Planning interviews it -- open questions: whether to rotate the token (at minimum, given the transcript exposure), whether the token should live in `/home/pi/.node-red/environment` only (`watchdog-README.md` already describes it being read from there) rather than also in the flow file's env, and whether `flows.json`'s permissions should be tightened (Node-RED runs as `pi`).

**Two more secrets exposed the same way, added 2026-09-23 12:33 MST (Joseph: "add the other exposures to 332") -- found during CARD-0324, while this session was looking for the Node-RED admin login in `credentials.local.md`.** Not a plaintext-at-rest problem like the token above; these are *transcript* exposures only -- a keyword search of that file printed whole lines, and the session's masking pattern didn't cover them. Both appeared in a Claude Code session transcript on Joseph's workstation. Values deliberately not recorded here, not even prefixes.
- **The NetAlertX webhook secret** (`NETALERTX_WEBHOOK_SECRET`) -- printed in full. It signs NetAlertX's webhook POSTs so Node-RED can verify they really came from NetAlertX (CARD-0078), so it lives in two places that must match: NetAlertX's own publisher settings and `/home/pi/.node-red/environment` on the Pi. Rotating it means changing both together, or the signature check fails and new-device alerts stop arriving.
- **The Apps Script `API_KEY`** (Environmental Data pipeline) -- printed *in part* (the first ~30 characters of a longer value). Lives as an Apps Script script property and as a Node-RED env var. A partial key is a weaker exposure than a full one, but the printed part is most of it, so treat as compromised unless the key's length says otherwise.

**Open questions added by these two:** rotate all three exposed secrets (HA token, webhook secret, API key) together in one pass, or only the ones whose blast radius justifies it -- `credentials.local.md`'s own rotation-cadence table lists the HA token as widely reused (Node-RED, photo-tv-display, hike-izer-orchestrator), which makes it the most disruptive to rotate and the most valuable to; and whether `credentials.local.md` should stop being a file a session can search at all, given that a masking regex is not a control (see CARD-0324's Reflection for the allowlist pattern).
**Not part of CARD-0328:** that card's script never compares or shows `global-config`, so it is unaffected either way.

**Related:** CARD-0328 (found the token), CARD-0324 (where the webhook secret and API key were exposed), CARD-0331 / `core/node-red/watchdog-README.md` (the watchdog is the consumer of this token).

---
### CARD-0331 · [bug] [node-red] Watchdog silence alert fires once and never re-alerts -- badly understates real outage duration

**Status:** Done — RESOLVED 2026-09-23

**Raised 2026-09-22 16:13 MST, found live cross-checking a "back-patio-temp-sensor silent for 35 minutes" alert against the Pi's actual log (the porch/patio component session, `jctsh-6a`, and the general session working together).** The real outage was **~15h53m** (2026-09-21 16:42:25 -> 2026-09-22 08:35:19), not the ~35 minutes the alert text implies -- the watchdog (`core/node-red/watchdog.flow.json`, `fn_timer_manager`'s per-component silence timers) only ever fires once, at the 35-minute threshold, and never re-alerts while a component stays down. As currently designed, a device down for 35 minutes and a device down for 16 hours are indistinguishable from the alert stream alone. **Correction, 2026-09-22 (folded in after `jctsh-6a` verified live on CARD-0219):** this card originally also cited a second, ~55min same-day gap (14:44-15:39) as a corroborating instance -- that one wasn't an unexplained dropout at all, it was Joseph's own BME280 physical swap and reboot, and it still produced the identical generic one-line alert text despite being a known, deliberate event. Kept as a weaker supporting data point (even a known-cause restart gets the same undifferentiated alert), not as a second real mystery -- the 2026-09-21 overnight ~15h53m gap is this card's actual motivating evidence. Full incident detail lives on CARD-0219, not repeated here.

**Interviewed 2026-09-23 (Joseph) -- two decisions:**
1. **Fix direction: periodic re-alert** (not duration-on-recovery, not both) -- keep re-firing while a component stays silent, until it recovers.
2. **Interval: every 2 hours.**

**Built and deployed, 2026-09-23:**
1. `core/node-red/watchdog.flow.json`, `fn_timer_manager`: on heartbeat receipt, now clears both the 35-min silence timer *and* any active re-alert interval (needed so a component that recovers mid-outage stops getting "still silent" pushes). When the 35-min timer fires, it now also starts a `setInterval` (2h) that re-sends every 2 hours while still silent, carrying the accumulated downtime in minutes -- cleared the moment a heartbeat arrives.
2. `fn_build_alert`: now branches on payload shape -- a plain component-name string (the original 35-min alert, unchanged wording) vs. an object carrying `component`/`downtimeMinutes` (a repeat alert, worded "still silent -- down 2h15m" via a new `formatDuration()` helper).
3. `watchdog-README.md`: updated How It Works, Alert Message, and Testing sections to document the repeat-alert behavior and its message format.

**Deployed live via Node-RED's Admin API** (`PUT /flow/tab_watchdog`, not a manual UI import) -- fetched the live flow, applied the same two function-node edits, pushed back, confirmed 200 and re-fetched to verify the new code is what's actually running on the Pi. A function-node syntax error would have failed this deploy outright, so the successful PUT is itself a validity check, not just a file write.

**Not independently verified end-to-end** (a real multi-hour outage, confirming an actual repeat push arrives on the Pixel with correct wording) -- that requires either a real outage or a manual timer-shortening test per the README's own Testing section, neither performed this session. The mechanism is deployed and live; a real silent-component event is this feature's next real test.

**Related:** CARD-0219 (the concrete incident this generalizes from), `core/node-red/watchdog.flow.json` / `watchdog-README.md` (the mechanism itself), CARD-0330 (found and fixed in the same session, unrelated mechanism -- that one's the Session Start credential gap, this one's the watchdog's own alerting design).

---

### CARD-0330 · [enhancement] [logging] Add a credential-free `/status.json` endpoint -- closes Session Start step 9's recurring credential dead-end -- RESOLVED 2026-09-22 16:13 MST

**Status:** Done

**Raised and built same session, 2026-09-22 (Joseph: "let's implement the real fix").** Both this session and the concurrently-running porch/patio component session (`jctsh-6a`) independently hit the same wall running `JCTsh-Session-Start.md`/`JCTsh-Component-Session-Start.md`'s step 9 (the `/status` dashboard scan, CARD-0282): it requires the Log Dashboard's HTTP Basic Auth password (`DASHBOARD_PASS`), which lives in `/etc/jctsh/log-server.env` on the Pi and isn't cached anywhere a session can reach non-interactively. Every attempt to read it -- grepping the env file over SSH, curling the authenticated endpoints through SSH to localhost, checking for a local `.netrc` -- was correctly blocked by Claude Code's own auto-mode credential-materialization classifier. Net effect: step 9 wasn't actually a silent automated check like steps 1/2/3/5/6 -- it was a guaranteed interruption asking Joseph for the password, every session, general or component-scoped, just to answer "is component X alive right now."

**Built.** `core/logging/log_server.py` gained `_build_status_json()` (reuses the exact same `_compute_status()`/`_snapshot()`/`_EXCLUDED_COMPONENTS` path the existing `/status` HTML page already uses) and a new `/status.json` route in `_Handler.do_GET`, checked *before* the Basic Auth gate -- deliberately the only unauthenticated route on this server. Returns only non-secret per-component `freshness` (Online/Offline/n/a), `connection` (Connected/Disconnected/null), `is_remote`, and `last_seen` -- no log message content, no Alert text, nothing else currently behind auth on `/status`/`/log`/`/kanban`/`/data`, which all keep requiring `DASHBOARD_PASS` unchanged. Not a security regression: port 80 is LAN/Tailscale-only, never forwarded to the internet (only MQTT 1883 is, per root `CLAUDE.md`'s Internet Exposure section), and bare online/offline state carries nothing sensitive on its own.

**Deployed and verified live, 2026-09-22 16:13 MST.** `scp` to `/home/pi/jctsh/core/logging/log_server.py`, `sudo systemctl restart jctsh-logging` (came back `active`). Confirmed directly: `curl http://localhost/status.json` on the Pi returns HTTP 200 with real per-component data (no `Authorization` header sent) including `back-patio-temp-sensor` correctly showing `Online`/`Connected` after its own recent MQTT dropout recovered; `curl` against `/status`, `/log`, and `/kanban` still return HTTP 401 unchanged, confirming the new route didn't loosen anything else.

**Docs updated to match:** `tos/JCTsh-Session-Start.md` step 9 and `tos/JCTsh-Component-Session-Start.md`'s per-step table now point the freshness/connection half of step 9 at `/status.json` (no credential needed), while making explicit that the fuller Alert/log scan still needs `DASHBOARD_PASS` from Joseph -- so a future session stops attempting the same blocked workarounds this one and `jctsh-6a` both tried.

**Done when:** met -- built, deployed, verified live against the real Pi (not just "should work"), and the docs that would otherwise keep steering sessions into the same dead end are updated.

**Related:** CARD-0282 (established `/status` over raw-log grep for "is it alive now" -- this closes the credential gap that check still had), CARD-0219 (the porch/patio session that hit this dead-end running its own component-scoped step 9), CARD-0331 (found in the same session, the watchdog's own alerting-design gap -- unrelated mechanism).

---

### CARD-0329 · [bug] [tos] Full board sweep for `TZ=`-path timestamp contamination — six more found, dating back to 2026-08-14 — RESOLVED 2026-09-22 10:30 MST

**Status:** Done

**Raised 2026-09-22 10:15 MST (Joseph, "what must be done to fix this timestamp issue?"), after the porch/patio session found and fixed one bad stamp on CARD-0219** (`18:46 MST` written, `11:46 MST` true — `TZ=America/Phoenix date` silently returns UTC in this environment, no zoneinfo database, right zone label, wrong time, no error) and this session documented the mechanism in `tos/JCTsh-Session-Start.md`. One known instance raised the obvious question: was that the only casualty, or had the bug been running longer than today?

**Method.** `git blame --date=format-local` every timestamp-bearing line in `tos/kanban-board.md`, compare each embedded `HH:MM MST` stamp against the *introducing commit's own local time* (git's author-date offset is always numeric and correct — established as ground truth earlier today). Flag any stamp **5–9 hours ahead** of its commit — the `TZ=` bug's exact signature, since git commits are unaffected but Bash-tool-generated prose stamps are. **Validated against the known-bad CARD-0219 case before trusting a zero result** (a first pass found nothing due to a blame-parsing bug, not a clean board — re-run after fixing the parser reproduced the known case exactly: 7.0h ahead, confirming the method before it was applied to the live file).

**Six more contaminated stamps found, none from today — all pre-dating this session's own discovery of the bug:**

| Card | Stamp written | True time | Commit | Commit local time |
|---|---|---|---|---|
| CARD-0295 | `2026-09-18 16:57 MST` | `09:57 MST` | `2b58ffc1` | `10:00` |
| CARD-0202 | `2026-08-23 14:27 MST` | `07:27 MST` | `3c448118` | `07:45` |
| CARD-0203 (×2) | `2026-08-23 14:27 MST` | `07:27 MST` | `3c448118` | `07:45` |
| CARD-0200 | `2026-08-23 14:16 MST` | `07:16 MST` | `02461309` | `07:22` |
| CARD-0168 (×2: title + resolution note) | `2026-08-15 02:28 MST` | `2026-08-14 19:28 MST` | `d5299bc0` | `19:29` |

Every corrected time lands within 1–18 minutes *before* its own commit — the pattern expected if a session read the (broken) clock, wrote the stamp, then committed shortly after. **This has been live since at least 2026-08-14** — over five weeks — not a today-only defect; it simply took today's porch/patio finding to know to look.

**Fixed in place, not silently rewritten** — each stamp corrected inline with a short `(corrected 2026-09-22 ... see CARD-0329)` note, per this document's "mark and strike through, don't silently delete" convention, rather than erasing the evidence a five-week-old bug existed.

**Re-swept after fixing — zero suspects remain** in `tos/kanban-board.md`. Not extended to component `card-archive.md`/`kanban-archive.md` files or other repos (LogSeq/PB-Blog) this pass — same method applies if ever warranted, not done speculatively.

**Done when:** met. Root cause and detection already documented in `tos/JCTsh-Session-Start.md` (this card's prerequisite, not its own scope); this card is the one-time retroactive sweep, complete, with zero remaining suspects confirmed by re-running the same detector against the corrected file.

**Reflection.** A tool bug with no error output can run for weeks before anyone notices, because each individual stamp looks plausible in isolation — it took a *second* observer's arithmetic (porch/patio's own 1.4-vs-7-hour cross-check) to surface the first instance, and only a mechanical sweep, not casual review, found the other six. The generalizable point: once a systematic-but-silent corruption source is confirmed, check for its blast radius immediately rather than assuming a single caught instance was the only one — the same discipline `JCTsh-Operating-System.md`'s Engineering Discipline section already states ("verify a claimed completion directly"), applied here to a claim of scope ("that was the only one") rather than a claim of done-ness.

**Related:** `tos/JCTsh-Session-Start.md` (root cause, detection method, and the timestamp rule this bug undermines), CARD-0219 (the first instance, found and fixed by the porch/patio session), CARD-0291 (this session's own three forward-estimated — not `TZ=`-caused — stamps, a related but distinct failure mode fixed the same morning).

---

### CARD-0328 · [enhancement] [mqtt] [node-red] [homeassistant] Version-controlled-copy directories have no drift check — generalize CARD-0326's one-line diff

**Status:** Build

**Raised 2026-09-22 10:04 MST — found by the ops cluster session in CARD-0326's own reflection, routed here because no initiated session owns the affected directories.** `core/mqtt/`, `core/node-red/` and `core/homeassistant/` are each "version-controlled copy of a file that actually lives on the Pi" directories, and nothing verifies the copy still matches the live file. CARD-0326 just fixed exactly this exposure for Docker (splitting `daemon.json` per host), and its fix was a one-line `diff` command in the README — which generalizes to all three directly.

**This drifts in practice, it isn't hypothetical:** CARD-0291's fourth pass found `core/docker/daemon.json` missing CARD-0272's `journald` logging-driver setting, which had been applied live on the M8 and never brought back to the repo. That is the same failure these three directories are currently unguarded against, and root `CLAUDE.md` already states the rule they're supposed to satisfy ("the repo is the source of truth... do not edit on the Pi directly or the repo will fall out of sync") with nothing checking it.

**Ownership, stated because it isn't this session's:** `core/mqtt` and `core/node-red` belong to the network/infra-visibility cluster, `core/homeassistant` to the HA automations cluster (`JCTsh-Component-Session-Start.md`'s registry) — neither is initiated. Opened from the `tos` session because the board is where a finding goes when no session owns it yet, not because `tos` owns the work. Tagged per-directory rather than by cluster, per CARD-0294's convention.

**Not scoped, deliberately:** whether a README `diff` line per directory is sufficient (cheap, matches CARD-0326's precedent, but only runs when someone remembers), or whether this wants one scripted check covering every version-controlled-copy directory at once — which would live in `core/maintenance/` and make it ops scope instead. That choice is the Planning question.

**Interviewed 2026-09-23 11:27 MST (Joseph, network/infra-visibility session) -- moved Backlog -> Planning; three scope decisions:**
1. **Approach: one scripted check, not per-README `diff` lines.** Covers every version-controlled-copy directory in scope at once. The README-line option was rejected as the exact weakness the card names (only runs when someone remembers) and because it cannot cleanly handle Node-RED (below).
2. **Runs on the Pi, unattended, via a systemd timer** -- same pattern as the existing `core/maintenance` timers (`pi-maintenance-check`, `container-update-check-*`).
3. **On drift: auto-open a kanban PR** through CARD-0128's `tos/open_kanban_pr.py` intake, same as container-update findings, reviewed via `tos/pr-review-checklist.md`. Not a log-only Alert, not report-only.
4. **Directories in scope: `core/mqtt`, `core/node-red`, `core/homeassistant`** -- exactly the three named above. `core/docker`/`hosts/` are already covered by CARD-0326's one-line diffs and stay out.

**Findings from Planning's first pass (2026-09-23, before any design):**
- **`core/mqtt` maps 1:1** onto `/etc/mosquitto/` (`mosquitto.conf`; `jctsh.conf` and `mqtt-tls.conf` in `conf.d/`; the cert hook at `/etc/letsencrypt/renewal-hooks/deploy/`) -- a plain file diff works.
- **`core/node-red` does not map 1:1.** The repo holds separate `core.flow.json`/`watchdog.flow.json` (plus component flows elsewhere, e.g. `components/netalertx/netalertx.flow.json`); live Node-RED keeps everything merged in one `/home/pi/.node-red/flows.json`. A file diff can't work -- the comparison has to be per flow tab/node set (e.g. via the Node-RED admin API or by splitting `flows.json` by tab). `settings.js` is 1:1 but holds a bcrypt hash, so it needs a hash-aware or exclude rule, not a blind diff-and-PR of its contents.
- **Ownership wrinkle:** the script itself would live in `core/maintenance` (ops cluster's directory, already-initiated session) while two of the three directories it checks belong to this cluster and the third to the not-yet-initiated HA automations cluster. Build should be coordinated with the ops session rather than done unilaterally from here.
- Live paths are unverified: SSH from this workstation to the Pi's Tailscale IP failed host-key verification and `pi1.local` didn't resolve (off-LAN at the time), so nothing above about *live* file locations has been read from the Pi yet.

**Non-goals (stated so scope can't drift back in):**
- No auto-sync or auto-deploy in either direction -- the check detects drift and opens a PR for a person to decide; it never overwrites the repo or the Pi.
- Not a general config-management system, and no new file-watching daemon -- a timer-driven comparison only.
- Not replacing CARD-0326's `daemon.json` diffs for `core/docker`/`hosts/`.
- Doesn't decide *which side is right* when they differ (repo says "source of truth", but a live hotfix may be the correct one) -- that's the PR reviewer's call.

**Done when:** (scoped 2026-09-23 -- refine in Planning)
1. A script in `core/maintenance` compares the live Pi files against the repo copies for `core/mqtt`, `core/node-red` and `core/homeassistant`, handling Node-RED's merged `flows.json` correctly and excluding/handling secrets (`settings.js` hash, tokens, credential files) without ever putting them in a PR body.
2. A systemd timer on the Pi runs it on a schedule; on drift it opens a kanban PR via `open_kanban_pr.py` naming the directory, the file, and the diff; no drift means no PR and no noise.
3. **Verified live, not synthetically:** deliberately introduce a real drift on the Pi (e.g. a harmless comment in a live conf), confirm exactly one PR opens, revert it, confirm the next run stays quiet -- plus a first clean run against today's real state, with any *pre-existing* drift it finds reported to Joseph rather than silently fixed.
4. Documented in the `core/maintenance` README and each covered directory's README (how it's checked, how to run it by hand).

**Open Planning questions:** how the Pi gets the repo copy to compare against (a checkout on the Pi vs. fetching raw files from GitHub `main`); the Node-RED comparison mechanism; dedupe so one persistent drift doesn't open a PR every run; how the ops session and (later) the HA cluster session pick this up.

**Build started 2026-09-23 11:34 MST (Joseph: "build it") -- Planning's open questions answered by reading existing code, not by asking:**
- **Repo copy:** fetched from GitHub `main` with the Pi's existing `/etc/jctsh/github.env` token via `open_kanban_pr._get_file_text` (size-safe raw fetch) -- no checkout needed on the Pi.
- **Node-RED comparison:** read the live `/home/pi/.node-red/flows.json` file and compare node-by-node by id (editor x/y ignored); also reports live tabs/config nodes present in *no* repo flow file, using every `*.flow.json` in the repo as the reference set so other components' flows aren't false orphans.
- **Dedup:** same fingerprint + 7-day reminder throttle (same as every other check); a clean run resets it. `open_finding_pr` alone would re-open a PR every run once the previous one was closed.
- **Secrets:** diffs rendered from a masked copy (bcrypt hashes, `credentialSecret`/password/token-style values); a secret-only difference is reported as "content withheld".
- **Schedule:** daily 09:00 on the Pi (1hr clear of the Pi's 1st-of-month 08:00 OS check; row added to `network/jctsh-network.md`'s Maintenance Windows table).
- **Ops-cluster coordination:** the ops session is not live (`ListAgents` 2026-09-23 showed only general/porch-patio/hike-izer peers), so nothing to notify; the files land in `core/maintenance` and the ops session should be told at its next startup.

**Built offline, NOT yet deployed or verified live** -- `core/maintenance/config-drift-check.py` + `.service` + `.timer`, README section, Maintenance Windows row. 18 synthetic fixture checks pass (identical->quiet, CRLF-only ignored, file/flow/orphan drift found, secrets never in message, message capped, missing live file and repo-fetch failure surface as findings rather than crashes). **Synthetic is not the Done bar** (Done-when 3 requires the real thing). Files held uncommitted pending Joseph's review -- runtime code, per the commit rules.

**Still to do, all needing the Pi:** (a) verify the live paths in `MANIFEST` (three are unverified guesses: the cert-deploy-hook filename, `docker-compose.yml`'s location, and whether `open_kanban_pr.py`/`github.env` are present in `/usr/local/bin`/`/etc/jctsh`); (b) `--dry-run` on the Pi and report any pre-existing drift to Joseph rather than fixing it; (c) deploy script/service/timer, enable the timer; (d) the live drift test from Done-when 3. **Blocked right now:** SSH from this workstation to the Pi's Tailscale IP fails host-key verification and `pi1.local` doesn't resolve off-LAN.

**Live check on the Pi, 2026-09-23 11:55 MST (SSH restored via Tailscale IP after Joseph accepted the host key; key fingerprint matched the already-trusted pi1.local ED25519):**
- **Live paths verified.** Mosquitto files, `flows.json`, `settings.js`, HA config, `open_kanban_pr.py` and `github.env` are all where `MANIFEST` says. Two guesses were wrong and are fixed: the cert hook is installed as `mosquitto-reload.sh` (repo name is `mosquitto-cert-deploy-hook.sh`), and HA's `docker-compose.yml` is `/home/pi/docker-compose.yml` (the running container's own compose label says so), not under the HA config dir.
- **Real gap found while checking paths, added to the script:** `/etc/mosquitto/conf.d/local.conf` (the 1883 listener + auth settings) exists live and is tracked nowhere in the repo. The first build only walked repo files, so it could never have noticed a live-only file -- now checks `conf.d/*.conf` for untracked files.
- **`--dry-run` on the real Pi, first pass, found two false positives in the script, both fixed:** Node-RED adds load-time defaults (`inputs: 0`) that aren't drift, and its own `global-config` node is auto-created. Two tabs looked orphaned only because their repo tab ids differ from the live ids (one repo flow file has no tab node at all); orphan matching now also uses label and member-node ids.
- **Correction to this card's own earlier claim:** the design said nothing secret can appear in `flows.json` because Node-RED keeps credentials separately. **False** -- the live `global-config` node holds `HA_TOKEN` in plaintext in `flows.json`, which is world-readable on the Pi. Found when a diagnostic command by this session printed that node in full, exposing the token in the session transcript (not recorded here). Script now never compares or shows `global-config`, adds JWT masking, and masks the final message once more. Whether to rotate the token / lock down `flows.json`'s permissions is Joseph's call and is not part of this card's scope.
- **Second dry-run (hardened) -- three real, pre-existing drift items, reported and deliberately NOT fixed (Done-when 3):** (1) `core/mqtt/jctsh.conf` -- live copy lacks the repo's header comments (comment-only); (2) `core/mqtt/mqtt-tls.conf` -- live comment says `hiking-sensor`, repo says `hiking-monitor` (comment-only); (3) `/etc/mosquitto/conf.d/local.conf` -- live-only, untracked. Everything else compared clean: `mosquitto.conf`, `settings.js` (hash excluded), both core Node-RED flow files, HA `automations.yaml`/`configuration.yaml`/`docker-compose.yml`, the two HA scripts, the cert hook.
- **Not yet done:** deploy + enable the timer, and the deliberate-drift live test. Deploying means the first scheduled run will open a PR for the three items above unless they're resolved first -- Joseph's call on order.
**Pre-existing drift fixed, 2026-09-23 12:02 MST (Joseph: "fix the three drift items first") -- first clean run:** (1) `jctsh.conf` and (2) `mqtt-tls.conf`: repo copy deployed to the Pi (both were comment-only differences, repo had the better content; backups of the old live files in `/tmp/drift-fix-backup` on the Pi; Mosquitto deliberately not restarted -- its `ActiveEnterTimestamp` is still 2026-09-21). (3) `local.conf`: the reverse direction -- live-only, so brought *into* the repo (`0a35db4`), documented in `core/mqtt/README.md`, added to the script's manifest. Re-ran `--dry-run` on the Pi against `main`: **`No drift.`**, exit 0. Note the write to `/etc/mosquitto/conf.d/` was run by Joseph in his own shell -- the auto-mode classifier denied it from this session, and it wasn't worked around.
**Deployed and enabled, 2026-09-23 12:04 MST (Joseph: "deploy it and enable the timer"):** `config-drift-check.py` -> `/usr/local/bin/` (sha256 matches the repo copy), `.service`/`.timer` -> `/etc/systemd/system/`, `systemctl enable --now config-drift-check.timer`; next scheduled run Thu 2026-09-24 09:00 MST. Ran the installed service once via `systemctl start` to prove the real systemd path (root, deployed `open_kanban_pr.py` import, GitHub token): `Result=success`, journal `No drift.`, no state file written (clean run, nothing to throttle), no PR. Files committed with this update. **Still open for Done:** the deliberate-drift live test (Done-when 3), then Reflection.
**Live drift test PASSED, 2026-09-23 12:09 MST (Joseph: "add the one line change, run it now"):** first added the check's own script and both units to `MANIFEST` (a live edit to the checker itself must not go unnoticed; pushed to `main` before redeploying, or it would flag itself). Then, on the real Pi via the installed systemd service: (1) baseline `No drift.`; (2) appended a harmless comment to the live `/etc/mosquitto/conf.d/jctsh.conf`; (3) real run -> `Opened kanban PR: .../pull/128` + `Notified: Config drift: 1 item(s) ...`, and the PR body showed exactly the one added line, nothing else; (4) immediate second run -> `Same drift already notified -- next reminder in 6d.`, **no second PR**; (5) reverted the comment, next run -> `No drift.` and the state file reset to `{}`; (6) closed PR #128 and deleted its branch. Mosquitto's `ActiveEnterTimestamp` unchanged throughout (2026-09-21) -- never restarted. Done-when 1, 2, 3 met; 4 met (READMEs for `core/maintenance`, `core/mqtt`, `core/homeassistant`, and a new `core/node-red/README.md` -- that directory previously had none).

**Reflection (2026-09-23 12:09 MST):**
- **A drift check that only walks the tracked side can never see the other direction.** The first design iterated repo files, so a config that exists only on the Pi (`local.conf`, which held the 1883 listener and auth settings) was structurally invisible -- found only because path-verification happened to list the directory. Any future "repo vs live" check needs both directions (repo file missing live, live file missing from repo), for Node-RED tabs as well as files.
- **"Nothing secret can be in this file" was asserted from how the tool is documented, not checked -- and was false.** Node-RED's `global-config` node keeps its env (incl. an HA token) in plaintext in `flows.json`. Same class as the Engineering Discipline rule "verify, don't guess": read the actual live data before designing the masking. A diagnostic command then printed that node in full into the session (token exposed in the transcript, not recorded here) -- when inspecting live config on this Pi, print ids/types/keys, never whole nodes.
- **Real-data dry-runs before deploy paid off twice.** Synthetic fixtures (all passing) missed two false-positive classes only the real Pi produced: Node-RED load-time default props (`inputs: 0`) and tab-id mismatches between repo and live. Fixtures now cover both, but the lesson is that a green fixture suite is not a green check.
- **Tool gotchas for this workstation:** (1) Windows OpenSSH (PowerShell) rejects `~/.ssh/id_ed25519` on ACL grounds where Git Bash's ssh (the `Bash` tool, and Joseph's `!` shell) works -- use Bash for Pi access. (2) `C:\Shared` is a junction, so the `Read`/`Write`/`Glob` tools refuse it; PowerShell reads/writes fine. (3) The `!` shell can't answer an ssh host-key prompt -- use `-o StrictHostKeyChecking=accept-new` after comparing the fingerprint against the already-trusted `pi1.local` key. (4) The auto-mode classifier denied a `sudo` write to `/etc/mosquitto/conf.d/` from a session; Joseph ran it in his own shell, and later `/etc` installs for this card's own deployment were allowed once explicitly requested.
- **Process slip worth naming:** one commit was pushed before its test result was read (a stale fixture, not a script bug -- `local.conf` had become tracked). The chain was written as `commit; push` with no gate on the test output. Gate pushes of code on the test result.

**Auto verify: 2026-09-24 09:30 MST** -- the daily timer's first real scheduled firing (`config-drift-check.timer`, 09:00): `ssh pi@pi1.local "sudo journalctl -u config-drift-check.service --since '2026-09-24 08:55' --no-pager -o cat"` should show a `No drift.` run near 09:00. Everything else was verified live above by starting the installed service manually; only the timer itself firing unattended is unobserved. On a clean result, resolve per the marker protocol (edit this line to `**Auto verify (RESOLVED <date>, see below):**`) and move the card to Done.
**Related:** CARD-0326 (the per-host `daemon.json` split whose reflection found this, and the one-line diff pattern to generalize), CARD-0272 (the `journald` setting that drifted), CARD-0291 (pass 4, which caught that drift and honestly noted it rather than fixing it), CARD-0294 (per-directory tagging convention).

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

**Status:** Build

**Raised 2026-09-22 09:30 MST (Joseph's direct instruction, "new card for jctsh-pr-selftest"), from a real misread made in this same session — the finding is the misread, not the thing misread.** The `/status` dashboard showed:

```
jctsh-pr-selftest | — | n/a | — | Kanban-PR intake pipeline self-test FAILED at 2026-09-11T04:32:43.058948+00:0… | 11d ago | — | —
```

Read straight, that says the auto-PR intake pipeline's own daily canary (CARD-0192) failed eleven days ago and has said nothing since — i.e. either the self-test is dead or the pipeline it watches is. It was reported to Joseph in exactly those terms ("dark for 11 days").

**That reading is wrong, confirmed by checking the Pi directly rather than trusting the dashboard:**
- `systemctl list-timers kanban-pr-selftest.timer` — enabled, active, **last ran 2026-09-22 00:00:00 MST**, next 2026-09-23 00:00:00 MST.
- `systemctl status kanban-pr-selftest.service` — `code=exited, status=0/SUCCESS` on that run.

The self-test is healthy and has been running daily the whole time.

**Root cause, confirmed by reading `tos/kanban-pr-selftest.py`: `_publish_log()` is called only on the failure path.** A successful run publishes nothing to MQTT at all — it just records `last_success_at` in local state. So for any component that only speaks up when something is wrong, `/status`'s "Last Message" column is pinned to its most recent failure **permanently**, and its "ago" timestamp measures *time since that failure*, not *time since last check*. There is no rendering difference between:
- a component that failed 11 days ago and is still broken, and
- a component that failed 11 days ago, recovered the next day, and has run clean every day since.

**Why this is worth a card rather than a note.** `/status` exists precisely so a session doesn't have to infer liveness from raw-log greps (CARD-0282 established it as the authority for "is X alive right now"). This is a real hole in that authority for one whole class of component — alert-only ones — and it produces **false alarms that look exactly like true ones**, which is the expensive direction to be wrong in. It already cost real investigation time in this session, and a future session reading the same row would reasonably reach the same wrong conclusion.

**Scope deliberately left open — essence-only per CARD-0256, this is Backlog not Planning.** At least three plausible directions, not yet chosen and not yet interviewed: (a) have alert-only components publish a periodic success/heartbeat line so silence means something, (b) have `/status` render "last checked" separately from "last message" so a stale failure can't masquerade as current state, or (c) have the dashboard treat a known-scheduled component's timer/unit state as the liveness signal instead of its last MQTT message. Which of these is right depends on how general the problem is — worth first checking **which other components are alert-only**, since `jctsh-pr-selftest` is the one that happened to be noticed, not necessarily the only one affected.

**Deliberately not in scope:** anything about the auto-PR intake pipeline itself, which is working. `tos/JCTsh-Session-Start.md` step 4's "never surface the `jctsh-pr-selftest` PR" rule is also unrelated — that's about PRs the self-test opens, not about this dashboard row.

**Interviewed 2026-09-23 12:26 MST (Joseph, network/infra-visibility session) -- moved Backlog -> Planning -> Build in one pass ("build straight through"); three decisions:**
1. **Approach: a success line at the source** -- each alert-only component logs a normal `System` message on a clean run. No `log_server.py` change. Rejected: a retained "Last Check" MQTT state + new `/status` column (right shape, CARD-0127/0158 pattern, but new topic convention + column for a class of two), and a render-only "no successes reported" label (stops the misread but can't show the check is still running).
2. **Scope: both alert-only components** -- `jctsh-pr-selftest` and `watchdog`.
3. **Wording rule:** the success lines must not start with `Heartbeat - ` or `Watchdog: ` -- `log_server` treats those as heartbeats (`_compute_status`'s `is_hb`) and would expect one every ~70 minutes, showing a daily job Offline.

**Survey answering this card's own "which other components are alert-only?" question (2026-09-23, from the Pi's durable log, ~35k lines across `jctsh.log` + 4 rotations):** exactly two components have *only* `Alert` messages in their whole history -- `jctsh-pr-selftest` (1 message: the 2026-09-11 failure) and `watchdog` (109 `Alert` lines, all "X silent for 35 minutes"). Every other non-heartbeat component (`gps-track`, `hike-*`, `scat-detection`, `node-red`, `hike-izer-orchestrator`) also logs ordinary `System` events, so a failure can't stay pinned the same way. The problem is a class of two today, not a broad one. Adjacent, **not this card:** `cardtest-0225`, `cardtest-0225-direct` and `aqm-minimal-test` are leftover dev rows still on `/status` (CARD-0139's exclusion list only holds `hiking-monitor-test`). **Corrected 2026-09-23 12:34 MST:** this note originally listed a fourth, `livecheck` -- wrong; it is one old `Test`-category log line, never a `/status` row (verified against live `/status.json`).

**Built, part 1 -- `jctsh-pr-selftest`: DONE and verified live, 2026-09-23 12:26 MST.** `tos/kanban-pr-selftest.py` now publishes `Kanban-PR intake pipeline self-test passed -- PR #N opened and confirmed.` (category `System`) after a confirmed-good run, in its own inner `try` so a failed publish can never fall into the failure branch and raise a false pipeline-failure Alert. Deployed to `/usr/local/bin/` (sha256 matches the repo copy), then ran the installed service once by hand: `Result=success`, opened PR #129 (closing #126 as designed), and the live `/status.json` row's `last_seen` moved from `2026-09-10` (the pinned failure) to `12:23:01` today, freshness still `n/a` as intended. **Ownership:** this script belongs to the `tos` cluster and that session wasn't live to sign off -- it needs telling at its next startup.

**Built, part 2 -- `watchdog`: BUILT, NOT YET DEPLOYED.** `core/node-red/watchdog.flow.json` gains, additively (`fn_timer_manager`, the alerting path, is untouched): `fn_track_heartbeats` (a third output on the existing heartbeat subscription, recording last-heartbeat time per component in flow context) and `inject_daily_check` (cron `00 07 * * *`) -> `fn_daily_check` -> the existing `mqtt_out_watchdog_log`, which logs e.g. `Daily check: 6 components reporting, 1 silent (hiking-monitor)` as a `System` line. Also a dead-man's switch: if Node-RED dies the line stops appearing. Components unheard-from for 7 days are dropped from the count.
- **Why undeployed:** the Node-RED Admin API needs the admin login, and the auto-mode classifier blocked reading it from `credentials.local.md` in this session ("Credential Materialization"); it then also blocked a plain `node --version`, so the two function nodes have not been exercised locally either. Not worked around. Added `core/node-red/deploy_flow.py` instead: run in Joseph's own terminal, it prompts for the password (never written anywhere), shows add/change/remove by node id, asks to confirm, PUTs only that tab, re-fetches and verifies every function node's code, and can fire the daily inject once (`--trigger inject_daily_check`).
- **Held out of `main` on purpose:** `watchdog.flow.json` stays uncommitted until deployed. If it reached `main` first, CARD-0328's drift check (daily 09:00) would flag repo != live and open a PR, and would muddy that card's own "No drift." verification.
- **Side effect to expect on deploy:** replacing the tab restarts that flow, so the watchdog's in-memory silence timers reset and re-arm on each component's next heartbeat (same as CARD-0331's deploy). A component already silent at that moment gets no alert until it next heartbeats.

**Still to do:** (a) Joseph runs the deploy helper; (b) confirm the first `Daily check` line reaches the dashboard (trigger it once with `--trigger`), and that the drift check then reports `No drift.` with the flow file committed; (c) update `watchdog-README.md` for the daily check; (d) tell the `tos` session about the self-test change; (e) Reflection, then Done. **Watch for / Auto verify:** the first 07:00 scheduled `Daily check` line, once deployed.
**Part 2 DEPLOYED and verified live, 2026-09-23 12:31 MST (Joseph ran `deploy_flow.py` in his own terminal):** `PUT /flow/tab_watchdog` -> HTTP 200; helper re-fetched and confirmed all 13 nodes present and every function node's code identical to the repo; add = `comment_daily_header`/`fn_daily_check`/`fn_track_heartbeats`/`inject_daily_check`, change = `mqtt_in_heartbeat` (the extra output wire), remove = none. The `--trigger` step then crashed in *the helper* (Node-RED answers `POST /inject` with plain text; the helper tried to parse JSON after the request had already gone through) -- fixed in the helper. The inject *had* fired: the `watchdog` row's `last_seen` moved from `2026-09-22 18:21` to `12:29:03`, and the durable log shows `watchdog | System | Daily check: no component heartbeats seen since Node-RED started`. That wording is the intended empty-state text (the tab had restarted seconds earlier, so flow context was empty) -- so the manual trigger exercised only the empty path. Then committed the flow file to `main` *after* it was live; the installed CARD-0328 drift check's `--dry-run` reports `No drift.`, i.e. the new nodes match the repo under its rules. Part 1's line also confirmed in the log: `jctsh-pr-selftest | System | Kanban-PR intake pipeline self-test passed -- PR #129 opened and confirmed.`

**Reflection (2026-09-23 12:31 MST):**
- **A one-shot inject proves the path, not the logic behind it.** The manual trigger ran seconds after the flow restarted, so it only proved the "nothing seen yet" branch; the reporting/silent counting is unobserved until a real scheduled run with real heartbeats. That is why the marker below exists rather than closing on the trigger. Next time, when a feature's logic depends on accumulated state, trigger it *after* the state has had time to accumulate, or say up front which branch the trigger can and can't reach.
- **Never grep a credentials file, even with a "masking" regex -- use a positive allowlist.** The mask I wrote covered `pass/secret/token` followed by `:`/`=`/`|`, but the file also stores secrets in table cells and under other labels, so two unrelated secrets (a webhook secret and an API-key prefix) were printed. The safe pattern is: list headings only; print a section's lines with every backticked value replaced; and never run a keyword search that returns whole lines. (Same class as CARD-0328's lesson about not printing whole `flows.json` nodes.)
- **Design around a credential the session can't hold, don't fight the block.** After the classifier refused to materialize the Node-RED login (and then, briefly, refused an unrelated `node --version`), the working path was an interactive helper run in Joseph's own terminal -- which is also better hygiene, since the password never touches the transcript. Independent work (the self-test deploy) was unaffected and continued.
- **Automation on the same files interacts.** CARD-0328's daily drift check compares repo `main` to live, so a flow change committed *before* it's live would have opened a PR and muddied 0328's own verification. Rule of thumb now in `core/node-red/README.md`: deploy first, commit to `main` after.
- **A real run found a helper bug a syntax check couldn't** (non-JSON response) -- the deploy had already succeeded, so it cost nothing, but it is the same "green compile != working" lesson as CARD-0328's fixtures.
- **Ownership gap, unresolved:** `tos/kanban-pr-selftest.py` is the `tos` cluster's and its session wasn't live to sign off -- change is deployed, committed and verified, but that session still needs to be told at its next startup.

**Auto verify: 2026-09-24 07:30 MST** -- the watchdog's first *scheduled* `Daily check` (cron `00 07 * * *`, fires at 07:00 with several hours of accumulated heartbeats): `ssh pi@pi1.local "sudo grep -h 'Daily check' /mnt/jctsh-logs/jctsh.log | tail -3"` should show a line like `Daily check: N components reporting, M silent (...)` with N > 0 and a ~07:00 timestamp. If it still says "no component heartbeats seen", the tracking function isn't receiving heartbeats and the fix is incomplete. On a good result, resolve per the marker protocol, tell the `tos` session about the self-test change if not yet done, and move the card to Done. (Note the durable log can lag up to ~15 min; `/status.json`'s `watchdog.last_seen` moving to ~07:00 is the fast signal.)
**Stale test rows removed as part of this card, 2026-09-23 12:36 MST (Joseph: "just do it as a quick change, as part of 324"):** `cardtest-0225`, `cardtest-0225-direct` and `aqm-minimal-test` added to `_EXCLUDED_COMPONENTS` in `core/logging/log_server.py` (that set was CARD-0139's, previously just `hiking-monitor-test`). Checked first that the deployed file was byte-identical to the repo's, so nothing Pi-only was overwritten. Deployed, restarted `jctsh-logging` (`active`, `Restored 1000 entries, 22 known components` -- state survived), and confirmed live: `/status.json` **21 -> 18 rows**, the three gone, real rows (`netalertx`, `watchdog`, `jctsh-pr-selftest`, `salt-sensor`, `hiking-monitor`) intact, deployed sha256 == repo. `aqm-minimal-test` was the only misleading one (a bench sketch showing *Disconnected* beside real devices). Left alone deliberately: the hourly `Watchdog: alive. Active:` list, which is built from the last-200 entries and lets stale components age out on its own. The names stay in `state.json` -- excluded from display, not deleted.
**Related:** CARD-0192 (built the self-test; `tos/kanban-pr-selftest.py`'s alert-only `_publish_log` is the mechanism here), CARD-0282 (`/status` as the authority for live component state — this is a limitation of that same page), CARD-0256 (essence-only Backlog scoping, why this card stops here), `core/logging/log_server.py` (`/status` rendering), `tos/kanban-pr-selftest.py`.

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

**Raised 2026-09-19, via the auto-PR intake pipeline (PR #110, jctsh-core maintenance check).** Original finding text: "create a repo for the Bible study and a tool that examines the questions for the feedback items I've received."

**Scope:** create a new, separate repo for Bible study content — same pattern as CARD-0297 (LogSeq) and CARD-0298 (Pastor Ben blog), which each moved a distinct content domain into its own dedicated repo under `Projects/` rather than folding it into jctsh or an existing repo.

**Note for whoever picks this up:** the original finding also mentions "a tool that examines the questions for the feedback items I've received" — not yet scoped or interviewed at all; captured here so it isn't lost, but it's a separate piece of work from the repo creation itself and needs its own interview before any building starts.

**Prerequisite written 2026-09-19, folded in here (Joseph's call) rather than its own card** — `tos/New-Repo-Setup-Protocol.md`, the step-by-step procedure extracted from CARD-0297/CARD-0298's own execution (interview, secrets sweep, cruft cleanup, sync-service handling, backup-conflict check, `.gitignore` categories, kanban bootstrap, README, private GitHub repo, session note). This card's own execution should follow that protocol directly rather than rediscovering its steps.

**Scoped 2026-09-20 — content answer, not what was assumed.** "Bible study content" is documents Joseph writes and manages as Google Docs, not local files. Interviewed directly ("Doesn't make sense to put these docs in the repo? How can I think about this?") before assuming a migration: three options laid out (Google Docs stays authoritative/repo holds process only; periodic export into the repo; full migration into repo-native files like LogSeq/PB-Blog). **Joseph's decision: Google Docs stays authoritative** — collaborative editing, comments, and Google's own revision history are load-bearing here, unlike LogSeq's/PB-Blog's local-file cases. This repo holds process tracking (a kanban board) and, eventually, an index of links to the Docs — not a copy of their content.

**Real deviation from `tos/New-Repo-Setup-Protocol.md`, worth noting there too:** that protocol's every step assumes an existing unversioned folder being migrated (interview about sync services, secrets sweep, cruft cleanup, a physical move Joseph performs). This card had no such folder — the repo was created fresh, directly, since the actual content intentionally never enters git at all. Not a gap in the protocol, just a case its steps don't apply to; noted on the protocol doc itself so a future reader doesn't assume every "new repo" card is a folder migration.

**Built 2026-09-20:** `Rethinking Scripture Bible Study` directory created under `Projects/` (in `JCT Documents not synced`, already excluding it from Google Drive's backup by inheriting `Projects/`'s own location — no separate backup-conflict check needed), `git init`, `kanban-board.md` bootstrapped from `tos/Portable-Kanban-Template.md` (CARD-0001: building an index of the study's Docs once they exist, plus the still-unscoped "tool that examines the questions for the feedback items" from the original finding), `README.md` documenting the architecture decision and the options considered, private GitHub repo (`github.com/joscthomas/Rethinking-Scripture-Bible-Study`, confirmed `PRIVATE`), pushed.

**The "tool that examines the questions for the feedback items I've received"** from the original finding is carried into the new repo's own CARD-0001 rather than closed here — still not scoped, needs its own interview whenever Joseph picks it up.

**Done when:** met — repo exists, private, pushed; `kanban-board.md` bootstrapped; the content-location decision made and documented, not left implicit.

**Related:** CARD-0297 (LogSeq → repo, the precedent this follows), CARD-0298 (Pastor Ben blog → repo, same shape), CARD-0301 (created the `Projects/` parent directory and portable kanban template these repo-creation cards use), `tos/New-Repo-Setup-Protocol.md` (the procedure whose folder-migration assumption this card didn't fit, noted there).

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

**Status:** Backlog

**Raised 2026-09-19, via the auto-PR intake pipeline (PR #99, jctsh-core maintenance check).** Original finding text (voice transcription, garbled): "make a Kaiser more spatially aware so of trailheads and names." **Clarified 2026-09-19 (Joseph): "Kaiser" = "hike-izer"** (a transcription artifact — the two are phonetically close). Interviewed the actual gap: hike-izer's published hike pages don't name the specific trail or trailhead a hike used.

**Confirmed live, not assumed — checked today's real page.** `components/hike-izer-orchestrator/place_context.py` (CARD-0108) already exists specifically for this: its own module docstring states the base layer (OpenStreetMap Overpass, named park/school/trail features near the hike's coordinates) is "Always gathered (free, no cost) -- feeds the Location/Nearby Named Features page sections directly (CARD-0123), independent of whether narrative is on." But the real, just-published `2026-09-19_hike-summary.html` page has **no Location/Nearby Named Features section at all** — confirmed by direct inspection, not inferred.

**Open question ANSWERED 2026-09-22 09:30 MST (hike-izer cluster session), and the answer is neither of the two branches below — it's a third case.** Checked against a real *enriched* (step-2) page for the 2026-09-22 hike, which is exactly the check the open question below asks for:

1. **Not a wiring gap.** `place_context.py` **is** invoked, and the Location section renders. The 2026-09-19 page this card examined was a **data-only step-1** page, which is why it had no Location section at all — step 1 doesn't run place context. Comparing a step-1 page against a feature that only exists on step-2 pages is what made this look like a wiring gap.
2. **Not (yet) a proven OSM data gap either.** Overpass never returned an answer to be judged: every mirror and retry failed on infrastructure grounds — `504`, `429 Too Many Requests`, then read timeouts on the `kumi.systems` fallback, ending in `all mirrors/retries exhausted`. So "OSM has nothing tagged here" remains untested for this hike, not disproven. **That failure is now its own card, CARD-0323** (the retry logic ignores HTTP status codes entirely and the query cadence provokes the 429).
3. **The thing this card actually wants is already on the page, from a different source.** Nominatim's reverse geocode — which succeeded — returned **`West Cape Final Trail, Marana, Pima County, Arizona, United States`**, rendered verbatim as the Location line. The trail name is *already being fetched and displayed today*; it just isn't surfaced as a named "Trail/Trailhead" field, and nothing in the page's structure calls it out as the trail.

**What this changes about this card's likely shape, for whoever picks up Planning:** the expensive interpretation (build out Overpass-based trail/trailhead lookup) may not be needed at all. The cheap interpretation — parse/surface the trail name Nominatim already returns into a first-class field, and treat Overpass named-features as optional enrichment on top — should be evaluated first. Worth confirming across several hikes before relying on it, since Nominatim's `display_name` leading with a trail name depends on what OSM has nearest the queried point and won't always be a trail (it could equally be a road or an address).

**Open question for Planning, not yet answered:** is `place_context.py` simply not being invoked for this page's generation tier (today's was explicitly a "data-only" summary, before photos/Gaia/bird data were staged — `hike-izer-orchestrator`'s own log message: "Ask for the rich version once photos/Gaia/bird data are staged"), or is it invoked but Overpass genuinely has no named trail/trailhead feature tagged near this hike's specific coordinates (a real OpenStreetMap data gap, not a code gap)? These have very different fixes — the first is a wiring gap in this pipeline, the second is either accepting the gap or falling back to something else (a manually-maintained trail-name lookup, e.g.) when OSM has nothing. Needs checking against the "rich" version of a recent hike (which does run the full pipeline) before assuming which case this is.

**Done when:** not yet scoped — pending Planning's root-cause investigation above.

**Related:** CARD-0108 (built the Overpass/Nominatim place-context infrastructure this gap sits inside), CARD-0123 (the Location/Nearby Named Features page section this should feed), `components/hike-izer-orchestrator/place_context.py`, `components/hike-izer-orchestrator/generation.py` (where the data-only vs. rich generation tiers diverge).

---

### CARD-0310 · [enhancement] [tos] Session Start: check for unmerged remote branches with real work, not just local uncommitted changes

**Status:** Done — RESOLVED 2026-09-19 18:47 MST

**Raised 2026-09-19 (Joseph, direct instruction: "what can we do to make the mobile session work like it should," after "yes, add it" confirming the recommendation) — real incident-driven, not speculative.** CARD-0309 (a PR review checklist, genuinely built, verified, and marked Done) was completed entirely on a branch a mobile/cloud session pushed to (`claude/pr-review-handling-t5b3ck`) but never merged into `main`. Nothing in the existing Session Start checklist would have caught this — step 1's `git status --short` only sees the current session's own local working tree, not other branches sitting on `origin`. This session only found it by chance, via a `git fetch` run for an unrelated reason (reconciling a `next-card-id` collision with CARD-0308).

**Root cause left genuinely open, not assumed:** whether the mobile session's branch-based workflow (instead of committing straight to `main`, as this desktop session does) is a fixable choice or an inherent platform behavior for mobile/cloud Claude Code sessions wasn't determined — out of scope for a repo-level doc to control either way. This card's fix is a **catch-it-every-session safety net**, not a prevention of the underlying cause.

**Built:** extended `tos/JCTsh-Session-Start.md` step 1 with a second check — `git fetch` then `git branch -r --no-merged origin/main`, explicitly excluding the auto-generated `maintenance-alert/*` branches (CARD-0128's intake pipeline, expected to sit unmerged until reviewed via `tos/pr-review-checklist.md`, not a miss). Anything else found gets summarized to Joseph and merged in if it looks complete, same care as reconciling local uncommitted changes.

**Done when:** the check is documented as a standing part of Session Start step 1. **Met, 2026-09-19.** (Real-world effectiveness — whether this actually catches the next stray branch — will only be confirmed the next time one exists; not a live-verified fix in the CARD-0279/0286 sense, since there's no stray branch to test against right now.)

**Related:** CARD-0309 (the incident this responds to), CARD-0307 (created `tos/JCTsh-Session-Start.md` this card extends), CARD-0128/CARD-0190 (the `maintenance-alert/*` branch pattern this check must not false-positive on), `tos/pr-review-checklist.md` (where a real found branch/PR gets handled once surfaced).

---

### CARD-0308 · [idea] [hike-izer] Scat identification from hike photos — analogous to BirdNET's audio wildlife ID

**Status:** Done — RESOLVED 2026-09-23

**Raised 2026-09-19, via the auto-PR intake pipeline (PR #98, jctsh-core maintenance check).** Original finding text: "scat identification." Interviewed via PR review: Joseph wants automatic identification of animal scat photographed during a hike, analogous to how the existing BirdNET Live integration (CARD-0080, `birdnet-pipeline.md`) already does audio-based wildlife identification — the phone app does the actual classification, and hike-izer's pipeline just parses/renders the already-identified results into the hike page and the cross-hike Wildlife Life List.

**Mechanism decided, 2026-09-22 — an AI vision call inside hike-izer's own pipeline, not a BirdNET-style export-parse.** Researched whether an existing app already does scat ID the way BirdNET Live does bird calls (an on-device classifier hike-izer could just parse an export from). Several consumer "Animal Scat Identifier" apps exist (iOS/Android, AI-powered), but all of them are closed, in-app-only experiences with no visible export format, API, or file hike-izer could ingest -- nothing shaped like BirdNET Live's shareable export. The viable path is the other one this card already named: extend hike-izer's own existing vision call (`photo_captions.py`, CARD-0107) to also flag scat, rather than integrate a third-party app.

**Interviewed 2026-09-22 (Joseph) -- two real decisions:**
1. **Data destination: mirror BirdNET's whole pipeline shape (own Sheet, own dedup, own cross-hike life-list) -- but render it on a genuinely separate page, not merged into the existing "Wildlife Detections"/`wildlife.html`.** Audio-based bird ID and photo-based scat ID are different evidence qualities (BirdNET's classifier confidence isn't comparable to a vision call's), so keep them structurally parallel, not combined into one list.
2. **Confidence handling: same "don't guess" discipline `photo_captions.py`'s existing `caption`/`sign_text` fields already use.** No partial-confidence reporting -- either the model is confident enough to name it, or the field stays empty. No numeric confidence score surfaced or stored.

**Concrete scope, following the interview above, file by file (mirroring the exact BirdNET-pipeline shape, not reusing its rows):**
1. **`photo_captions.py`:** add `scat_common_name`/`scat_scientific_name` fields to `PhotoObservation` and a third numbered PROMPT instruction (same "don't guess, leave empty if not confident" wording pattern as the existing two fields). `caption` itself needs no change -- its existing "name the clear focal subject... a specific plant or wildlife species" wording already covers captioning a confidently-identified scat photo on the photo grid; the new fields are purely the structured record for the pipeline below, kept separate from the display caption the same way `sign_text` already is.
2. **New `core/data-pipeline/environmental-data.gs` branch**, `payload.component === 'scat-detection'` -- self-provisioning "Scat Detections" sheet (columns: timestamp, hike_file_stem, common_name, scientific_name, count, lat, lon -- no confidence column, matching decision 2 above), dedup on (hike_file_stem, scientific_name) before appendRow, same lock/CARD-0235 bare-date-string defenses as the `wildlife-detection` branch this mirrors.
3. **New `scat_life_list.py`**, a close structural mirror of `wildlife_life_list.py` (`load`/`update_from_hike`/`rebuild_from_sheets`), own persisted life-list JSON file, keyed by scientific_name same as the sibling module.
4. **New `_post_scat_detection()`/`_archive_new_scat_detections()`** in `generation.py`, mirroring `_post_wildlife_detection()`/`_archive_new_wildlife_detections()` exactly -- same retry-then-log pattern, same "duplicate counts as success" handling.
5. **New `build_scat_index.py`**, a close mirror of `build_wildlife_index.py` -- own standalone static page (e.g. `scat.html`), same `_STYLE`/click-to-sort convention, re-run alongside `build_calendar_index.py`/`build_wildlife_index.py` after every publish. No `xeno_canto`-equivalent (that's audio reference calls, doesn't apply here).
6. **Wire into `generation.py`'s existing photo-captioning step:** after `caption_photos()` runs, scan the manifest for assets carrying a non-empty `scat_common_name`, build detection rows from them, call step 4's archive function, rebuild `scat.html`.

**Explicitly out of scope, per decision 1:** any merge into `wildlife_life_list.py`/`wildlife.html`/the existing "Wildlife Detections" sheet -- scat gets its own sheet, own life-list file, own page, sharing only the *pattern*, not the data.

**Not yet scoped:** whether the standalone `scat.html` page gets linked from the calendar home page / main hike-izer nav the same way `wildlife.html`/`battery-trend.html` currently are, or found some other way -- a small Build-stage detail, not a real open design question.

**Built, 2026-09-22, matching the scope above exactly:**
1. `photo_captions.py`: `PhotoObservation` gained `scat_common_name`/`scat_scientific_name`; PROMPT gained a third instruction (same "don't guess" wording as the existing two fields) and a small addition to the `caption` instruction itself ("...or an identifiable wildlife sign such as tracks or scat") -- found live during build that the original caption wording could plausibly read "species" as the animal itself, not evidence it left behind, and skip captioning a scat photo without the explicit call-out. Also extended `generation.py`'s CARD-0214 photo-recovery mechanism (`_fetch_photos()`), which previously only carried `caption`/`sign_text` forward across a second pass -- without this fix, a photo captioned on step 1 would have had its real scat identification silently dropped the moment step 2 or a daily refresh re-ran, a real, non-obvious data-loss bug caught before it ever shipped.
2. `core/data-pipeline/environmental-data.gs`: new `scat-detection` branch, mirroring `wildlife-detection` almost exactly -- self-provisioning "Scat Detections" sheet, same CARD-0235 bare-date defense, dedup on `(hike_file_stem, scientific_name)` (identity-based, per the interview's own decision 1 -- deliberately not CARD-0270's full-content-match dedup, since a hike genuinely has one canonical count per species, unlike repeatable cost-tracking events). `SCRIPT_VERSION` bumped, redeployed by Joseph, verified live (see below).
3. `scat_life_list.py` (new, `components/hike-izer-orchestrator/`): near-exact structural mirror of `wildlife_life_list.py` -- `load`/`update_from_hike`/`rebuild_from_sheets`, same CARD-0276 archived-flag discipline.
4. `generation.py`: new `_scat_rows_from_manifest()` (the photo-based equivalent of `birdnet.parse_detections()` -- aggregates per-species count/first-timestamp/lat-lon across a hike's photos), `_post_scat_detection()`/`_archive_new_scat_detections()` (mirroring the wildlife pair exactly, reusing the existing `WILDLIFE_ARCHIVE_RETRY_*` tuning rather than a duplicate knob), `_scat_index_cmd()`. Wired into both `run()`/step1 and `run_step2()` call sites, right alongside the existing wildlife archiving/index-rebuild calls.
5. `build_scat_index.py` (new, `components/hike-izer/`): deliberately a leaner v1 than `build_wildlife_index.py` -- same core species table and `_STYLE`, but without that page's later-added seasonality tables (CARD-0210), sticky-header JS (CARD-0278), or Xeno-canto audio widget (CARD-0174), each of which was a real, separately-motivated addition built after actual use of the *wildlife* page specifically. Same iterative discipline applied here: ship the core table now, add equivalent features later only if real use of *this* page shows they're actually wanted.
6. `Dockerfile`: both new files added to the COPY list.

**Verified, both synthetically and against a real hike -- not just "the code runs":**
- Synthetic (mocked HTTP layer): `_scat_rows_from_manifest()` correctly aggregates multiple photos of the same species into one row with the right count/earliest-timestamp/matching-lat-lon, and correctly returns nothing for an empty or non-scat manifest; `_post_scat_detection()`'s payload shape, duplicate-as-success handling, and real-rejection raising all confirmed; `_archive_new_scat_detections()` confirmed to archive a genuinely new species and, separately, to correctly skip (zero POST attempts) a species already archived for that exact hike.
- Live, against the real Apps Script: version check confirmed `2026-09-22.3-scat-detection-sheet` deployed; a direct test POST came back `ok`, an identical resend came back `duplicate`; `action=export` confirmed the real row landed with correct fields.
- **Real end-to-end test against an actual hike with actual scat photos, 2026-09-19 (Joseph: "hike of Sept 19 has scat photos")** -- deployed to the M8 (all five files checksum-verified, container rebuilt, healthy), then ran a real `--step2 2026-09-19` pass (its 36 photos had to be forced through a fresh captioning call first -- they were already captioned from a prior pass before this feature existed, and CARD-0214's own "skip already-captioned assets" logic has no way to know new fields were added since; a real, one-time re-pay of that hike's captioning cost, $0.8817 for 36 photos, not an ongoing cost). Result: **`Wrote scat.html: 2 species indexed`** -- Coyote (4 identifications) and American Black Bear (1 identification), both with correct real timestamps/coordinates, cross-checked consistent between the live Sheet and the rendered page, correct Wikipedia links, correct per-hike counts.

**Not independently verifiable by this session:** whether the specific bear-scat photo identification is actually correct -- that's a real-world judgment only Joseph, looking at the actual photo, can make. The pipeline's own mechanics (extraction, dedup, Sheet write, page render) are fully verified; the vision model's specific species call on this one photo is not something code review can confirm either way.

**Joseph's own check found exactly the gap that note anticipated, 2026-09-23: "there is no black bear in this area, how do we validate the found species?"** Confirmed real: black bears don't range in the Tucson/Marana area this hike is in. Root cause: the vision prompt (`photo_captions.py`) gave the model zero geographic context, so it had nothing to weigh species plausibility against. Follow-up finding, also from Joseph, sharpened the diagnosis further: the "bear scat" photo is a close-up of the same physical pile as an adjacent photo already correctly identified as coyote scat, taken 6 seconds apart (`88f129c4...` 14:02:00 vs. `15008cea...` 14:02:06) -- not just a plausibility gap, the model gave two different species names to the same object across two photos with no cross-photo consistency check.

**Fix scoped by Joseph: "location context first, watch it, no whitelist yet"** -- explicitly declined building a curated species whitelist/validation-list for now; just give the vision call real location data and watch how much that alone helps.
1. `photo_captions.py`: new `_LOCATION_CLAUSE`/`_prompt_for(location_hint)` -- when a location hint is supplied, the scat instruction now names the hike's approximate location and tells the model to weigh whether a species is genuinely plausible there before naming it, leaving both fields empty rather than naming an implausible species. `_caption_one()`/`caption_photos()` both gained a `location_hint` parameter.
2. `generation.py`: new `_scat_location_hint(hike_data)` -- builds a plain `"lat, lon"` string from the hike's own first GPS point (same source data as `place_context.py`'s `_first_gps_point()`, not imported from there since it's a 3-line lookup not worth a cross-module dependency for). Deliberately raw coordinates only, no Nominatim reverse-geocoding call -- step 1 doesn't otherwise touch `place_context.py` at all, and the vision model already reasons fine about species ranges from a lat/lon pair alone. Wired into both `caption_photos()` call sites (step 1 and step 2).
3. **Validated live before deploying to production data**, on the exact flagged pair, via a standalone script calling `_caption_one()` directly on the two thumb files (no manifest/Sheet/life-list writes, ~4 vision calls, not a full 36-photo re-run): without the location hint, the coyote photo identified as Coyote and the bear photo (mis)identified as American Black Bear, reproducing the original bug; with the location hint, **both photos converged on Coyote** -- the fix didn't just leave the implausible one blank, it corrected the actual species call.
4. **Separate gap found live by Joseph the same session ("i cannot see the scat data on the Sep 19 hike page" / "how do i see the scat data... i can see the photos identified as such"):** scat identifications only ever surfaced as scattered photo captions among dozens of other photos -- unlike BirdNET, which gets an explicit per-hike table, despite CARD-0308 having been explicitly scoped to "use the birdnet pattern." Fixed: new `scat_table_rows()`/`scat_section` in `templating.py`, a lean static-table mirror of the existing `birdnet_table_rows()`/`birdnet_section` (no click-to-sort JS, no audio widget -- same "leaner v1" call already made for `build_scat_index.py` vs. `build_wildlife_index.py`), wired into `render_html()` and both `generation.py` call sites. Omitted entirely when a hike has no scat identified, same convention as the Photos/BirdNET sections.
5. **2026-09-19's bad data corrected end-to-end, after Joseph deleted the bad Sheet row and a stray test row himself:** `manifest.json`'s one bad asset (`15008cea...`) corrected in place to the fix's own validated output (caption + `scat_common_name`/`scat_scientific_name` all now Coyote/*Canis latrans*); the stale `Ursus americanus` entry removed from the local `scat_life_list.json` cache (the one piece `update_from_hike()`'s merge-only logic wouldn't have cleaned up on its own); `--step2 2026-09-19` re-run to regenerate the hike page and `scat.html` from the corrected sources. Confirmed **$0.0000, 0 API calls** both re-render passes -- CARD-0214's skip-already-captioned logic meant correcting and re-rendering never re-paid for a single vision call. Final state verified: hike page's new table shows Coyote only (count 5, up from 4 now that the corrected photo counts too), no "Bear"/"Ursus" anywhere on the page or `scat.html` (1 species indexed, down from 2) -- matching the Sheet Joseph corrected by hand. The Sheet's own Coyote row was deliberately left untouched (still count 4) -- Joseph asked specifically to "fix the page," and the existing dedup-by-identity guard correctly skipped re-posting an already-archived species for this hike, so no Sheet write was attempted for it.

**Done when:** the pipeline mechanics are fully verified end-to-end (met 2026-09-22) AND Joseph has personally checked the actual identified species (met 2026-09-23 -- his own check is exactly what caught the bear/coyote false positive above, validating why this card stayed in Build until now). **Resolved 2026-09-23.**



**Related:** `components/hike-izer-orchestrator/birdnet-pipeline.md` (the audio-ID pattern this is modeled after), `components/hike-izer-orchestrator/birdnet.py`, `components/hike-izer-orchestrator/wildlife_life_list.py`.

---

### CARD-0309 · [enhancement] [tos] Add a PR review checklist for the auto-PR intake pipeline
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 5279B, over the 5000B size threshold.

---

### CARD-0307 · [enhancement] [tos] Split the general Session Start checklist out of CLAUDE.md; orient sessions starting at the Projects/ parent directory

**Status:** Done — RESOLVED 2026-09-19 11:55 MST

**Raised and built 2026-09-19 (Joseph, two direct instructions in the same thread) — small enough to interview-by-instruction rather than a separate scoping pass.**

**Part 1: "move the steps to an md file in tos, and point to them in CLAUDE.md."** Root `CLAUDE.md`'s Session Start section had grown to ~90 lines of inlined checklist (the same "read every session" content genuinely belongs there, but per `JCTsh-Operating-System.md`'s Documentation Structure section, a large block like this benefits from the same split-by-topic treatment already applied to `JCTsh-Operating-System.md` and `JCTsh-Component-Session-Start.md` — still read every session, just no longer bloating the file a session opens first). Moved the full 9-step list plus the timestamp-format rule verbatim into new `tos/JCTsh-Session-Start.md`; `CLAUDE.md`'s Session Start section is now a short pointer. **Updated the one file that referenced the old location by name:** `JCTsh-Component-Session-Start.md`'s Purpose line said "instead of `CLAUDE.md`'s general Session Start" — corrected to point at `tos/JCTsh-Session-Start.md`, version-bumped (1.12 → 1.13) with the superseded description moved into `JCTsh-Component-Session-Start-History.md`, per that document's own established convention. The 9-step numbering `JCTsh-Component-Session-Start.md`'s own table maps against is unchanged, so that table itself needed no edits.

**Part 2: "note that a general session is likely to start at the Projects directory in addition to the JCTsh directory."** Real gap CARD-0301 never addressed when it created the shared `Projects/` parent for `jctsh`/`LogSeq`/`PB Blog` — nothing oriented a session that starts one level up, at `Projects/` itself, before any repo's own `CLAUDE.md` is even in view. Added `Projects/README.md` (untracked — `Projects/` isn't a git repo, purely a filesystem convenience per CARD-0301) listing the three repos and directing a session that starts there to identify the relevant repo, `cd` in, and follow that repo's own process — explicitly not assuming jctsh's process applies to LogSeq/PB Blog work.

**Done when:** `tos/JCTsh-Session-Start.md` exists with the moved content, `CLAUDE.md` points to it, `JCTsh-Component-Session-Start.md`'s reference is corrected and versioned, and `Projects/README.md` orients a session landing at the parent directory. **Met — all four, this session.**

**Related:** CARD-0301 (created the `Projects/` parent this card's second half orients sessions within), CARD-0292 (the version-history-split precedent this card's `JCTsh-Component-Session-Start.md` edit followed), CARD-0289 (documentation-splitting-by-read-frequency, the principle this card's first half applies to `CLAUDE.md` itself), `tos/JCTsh-Session-Start.md`, `tos/JCTsh-Component-Session-Start.md`, `Projects/README.md`.

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

**Auto-opened 2026-09-18 from jctsh-core's maintenance check (CARD-0128).** Raw finding: "Set up remote access for Claude Code" — the finding body also carried a pasted walkthrough (from another assistant session, not a decision made here) proposing OpenSSH Server on the Windows machine + Tailscale + Termux on the Pixel, with a note that the author had no access to this repo and was guessing at the setup.

**Goal, as captured:** be able to run Claude Code against this repo from the Pixel while away from the desktop, rather than only from the Windows machine the working tree lives on.

**Approach deliberately left open, 2026-09-18 (Joseph's call) — the pasted SSH/Termux/Tailscale walkthrough is one candidate, not the decision.** Open questions to resolve during planning:
1. **First-party options not yet evaluated.** Claude Code has its own remote paths that the pasted walkthrough predates or ignores — Claude Code on the web (`claude.ai/code`), and Remote Control driving a session on another machine. Either could make a hand-rolled SSH setup unnecessary. Evaluate these before building anything.
2. **If SSH is still the answer:** Tailscale is already installed and working on the Pi and the RV Pi (`CLAUDE.md`'s Remote Access section) — a Windows node would join the same tailnet with no port forwarding, which is strictly better than the walkthrough's port-forward-22 alternative. The walkthrough's port-forward option should not be adopted.
3. **What "running Claude Code" actually needs to mean here** — a shell for git/status/commits only, versus genuinely doing editing work from a phone screen. These have very different setup costs and the walkthrough itself flags phone-screen editing as rough.
4. **Whether the working tree should even live on the Windows box for this** — a session run from elsewhere against a different checkout raises the same concurrent-edit questions `CLAUDE.md`'s Concurrent Sessions section already covers, and CARD-0283 already tuned for.

**Approach decided, 2026-09-20 — first-party Remote Control**, resolving open question #1. Joseph's 2026-09-19 attempt (opening the Claude Android app cold) created a new, disconnected cloud session rather than reaching a desktop one — root cause confirmed via `claude-code-guide` research: Remote Control has to be started explicitly on the desktop side first (`/remote-control` inside an existing session, `claude --remote-control`, or standalone server mode) before the phone can see and connect to it. Full mechanics, multi-session behavior (yes — each session running `/remote-control` independently is reachable at once; server mode as a heavier pooling option not needed at this project's scale), and setup steps written up in `tos/Remote-Control-Setup.md`. `/remote-control` run inside this very session as the live test.

**Phone-side connection confirmed live, 2026-09-20** — Joseph connected to this exact session from the Android app and drove a message through it ("Yes, confirming now remotely"), received and acted on inside this same session. Real end-to-end proof, not just the desktop side being enabled.

**Done when:** met. An approach is decided and written down (first-party Remote Control, `tos/Remote-Control-Setup.md`), and a real Claude Code session has been run against this repo from the Pixel end to end — confirmed live, both directions.

**Related:** CARD-0128 (the auto-PR intake pipeline this was raised by), `CLAUDE.md` (Remote Access section — the existing Tailscale footprint any SSH approach would build on; Concurrent Sessions section), CARD-0283 (concurrent-session editing discipline, relevant if a second checkout enters the picture).

---

### CARD-0295 · [enhancement] [homeassistant] Home Assistant container update available: 2026.9.2 → 2026.9.3

**Status:** Backlog

**Auto-opened 2026-09-18 from jctsh-core's maintenance check (CARD-0128).** Raw finding: `Container image updates: home-assistant: 2026.9.3 available (running 2026.9.2)`.

**Risk assessment, checked 2026-09-18 09:57 MST (corrected 2026-09-22 — written `16:57`, 7h fast via the `TZ=` clock bug, see CARD-0329) against the real upstream release notes (github.com/home-assistant/core/releases/tag/2026.9.3):** patch release, bug-fixes and dependency bumps only — no breaking changes, no database migrations. Notable fixes: EnergyZero market-price regression, Private BLE Device now requires an IRK in its config flow, Bond retains known-host info on repeated zeroconf announcements, Matter/Shelly cover-entity creation when the tilt attribute is null, Nest Climate `turn_on` made idempotent, Spotify reauth crash when a config entry lacks an `id` field, Airthings BLE duplicate device entries from incomplete reads, better DNS/API error handling for Google Tasks and WAQI, onboarding username validation. Dependency bumps: holidays, pylutron, hassil, waterfurnace, aioamazondevices, reolink_aio. Also redacts API keys in debug logs. **None of these touch an integration this install actually depends on** (SmartThings, Ring, MQTT, Matter/Cync, SamsungTV) — low-risk upgrade.

**Deploy per `CLAUDE.md`'s standing Pi rule (CARD-0266/CARD-0268/CARD-0269) — never `docker pull`/`docker compose pull` on this host** (hangs indefinitely on this Pi's Docker 29.6.1 via a confirmed OCI-referrers bug, and risks starving the live container's I/O on the Pi 3B+'s shared USB 2.0 bus):
```bash
sudo pi-image-pull.py ghcr.io/home-assistant/home-assistant:stable --recreate homeassistant
```
Optionally add `--schedule "<time>"` to defer it to the Mon 3 AM reboot window; the deliberate default is still to run it in the foreground and watch it.

**Post-update check required (CARD-0240, generalized):** after the recreate, check `/api/states` for unavailable entities and `docker logs homeassistant` for the `homeassistant.bootstrap` "Waiting for integrations to complete setup" line. Any integration named there is a candidate for a config-entry reload via the HA REST API before investigating real device failure — a config entry can report `state: loaded` without having actually re-synced its entities.

**Done when:** the Pi's `homeassistant` container is running 2026.9.3 (confirmed via the HA UI or `/api/config`), the container reports healthy after the recreate, and the post-update entity-availability check above comes back clean (or any affected integration has been reloaded and confirmed resynced).

**Related:** CARD-0266 (the immediately prior HA update, 2026.9.1 → 2026.9.2, same shape), CARD-0269 (`pi-image-pull.py`, the required pull mechanism), CARD-0268 (the I/O-contention rationale behind it), CARD-0240 (the post-update entity-availability check this card inherits), CARD-0128 (the auto-PR intake pipeline this was raised by), `core/homeassistant/docker-compose.yml`.

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

**Raised 2026-09-17 (Joseph), directly from watching `JCTsh-Operating-System.md`'s own "Version description" field keep growing across this session's own edits.** Every version bump had been prepending new text while keeping every prior "Prior version description" entry chained inline — the field had reached ~6KB, over 20% of a 29KB file, the exact same unbounded-growth shape `kanban-board.md` (CARD-0193) and component `CLAUDE.md` files (CARD-0290) already hit and were fixed for, one layer up (a doc's own changelog, not just its subject matter).

**Interviewed 2026-09-17.** "Put doc version tracking in a separate file and point at it... make this a pattern and apply when appropriate" — a standing Documentation Structure rule, not a one-off fix to a single file. Scope decided by measuring actual size (Engineering Discipline — verify, don't assume) rather than applying it everywhere reflexively:

| Document | Version-history size | Action |
|---|---|---|
| `JCTsh-Operating-System.md` | ~6KB header chain (21% of 29KB file) | Split |
| `JCTsh-Component-Session-Start.md` | ~2.5KB header chain (22% of 11KB file) | Split proactively — same pattern, would hit the same growth soon |
| `JCTsh-Build-Standards.md` | 14.6KB dedicated table (12% of 122KB file) | Split |
| `JCTsh-Session-Card-Selection.md` | 301B header field (10% of 3KB file) | Left alone — not yet a real problem |

**Built, 2026-09-17.** Three new sibling `<Doc>-History.md` files created, one per qualifying document, each holding the complete version-by-version changelog as a table. Each live document's header now states only its **current** version's description — never chained prior ones — plus a `**Version history:**` pointer line to its history file. For `JCTsh-Operating-System.md` and `JCTsh-Component-Session-Start.md`, the existing prose chains were parsed and reconstructed into per-version table rows; versions 1.2–1.5 of `JCTsh-Operating-System.md` had been bundled into a single unrecoverable paragraph (each of those four edits fully restated the field before the chaining habit began, rather than prefixing a "Prior version description"), noted honestly in the history file rather than assigning fabricated individual version numbers. `JCTsh-Build-Standards.md`'s existing table already carried real per-version numbers throughout, so that split was a clean cut-and-move.

**Documented as a standing pattern, `JCTsh-Operating-System.md`'s Documentation Structure section** (→ v1.15): a document's version-tracking splits into `<Doc>-History.md` once it stops being a short header field — a real "Prior version description" chain or dedicated table, not a vague sense of "too long." Applied immediately to the three qualifying documents above.

**Done when:** the three qualifying documents each have a `<Doc>-History.md` sibling, their own headers trimmed to current-version-only, and the pattern is documented in `JCTsh-Operating-System.md` for future use. **Met.**

**Related:** CARD-0193 (`kanban-board.md`/`kanban-archive.md`, the original instance of this same growth pattern), CARD-0290 (component `CLAUDE.md`/`card-archive.md`, the same pattern one layer down), CARD-0289 (the general documentation-splitting-by-read-frequency principle this extends to a document's own changelog), `tos/JCTsh-Operating-System-History.md`, `tos/JCTsh-Component-Session-Start-History.md`, `JCTsh-Build-Standards-History.md` (the three new files this card produced).

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

**Raised 2026-09-17 (Joseph), this session.** Wants a documented, repeatable answer to "given several candidate cards, which one does a session actually pick up" — separate from the existing Priority tag (`JCTsh-Operating-System.md`'s Priority section), which describes urgency, not selection order.

**Interviewed 2026-09-17.** Basis: a real prior pick (CARD-0286 over CARD-0258/0276/0279/0287/0278) and the reasoning behind it, generalized into an ordered rule:
1. **Actionable now vs. blocked on something else** — skip a card, even one in Build, if there's nothing left for Claude to do on it right now (waiting on a real-world recurrence, a manual deploy step, etc.), not on more work from this session.
2. **Whose job it is** — skip a card whose next step belongs to Joseph by this project's established division of labor (e.g. Tasker profile build/confirm); Claude's part there is already done at the scoping stage.
3. **Already scoped beats not yet scoped** — a card with a full interview and concrete acceptance criteria already sitting in Backlog/Planning is cheaper to pick up than one still essence-only, needing a Planning pass before any code gets written.
4. **Bugs before enhancements — a tiebreaker only, decided 2026-09-17.** Applied only when two or more candidates tie on all three factors above; does not override factor 1 (a blocked bug still loses to an actionable enhancement).

**Explicitly not weighed:** raw severity beyond the bug/enhancement tiebreaker, card age, business impact — can be added later if they prove genuinely load-bearing, not swept in preemptively.

**Scope, revised 2026-09-17 (Joseph) — a standalone file, not an embedded section.** Claude's original recommendation was a new "Session Card Selection" section inside `JCTsh-Operating-System.md` itself, next to Priority; Joseph asked for it as its own file instead. Landed on `tos/JCTsh-Session-Card-Selection.md`, matching the existing precedent of `JCTsh-Component-Planning-Pattern.md`/`JCTsh-Build-Standards.md` — standalone `JCTsh-*.md` docs referenced *from* the Operating System doc rather than embedded in it. `JCTsh-Operating-System.md` gets a short pointer paragraph (in the same Priority-adjacent location) plus a version bump instead of the full text; `CLAUDE.md`'s Session Start pointer names the new file directly.

**Done when:** `tos/JCTsh-Session-Card-Selection.md` documents the four ordered factors, `JCTsh-Operating-System.md` points to it, and `CLAUDE.md` points to it from Session Start.

**Follow-on, 2026-09-17 (Joseph) — a consistent table format for a requested open-cards listing, combining Priority with this card's ordering.** Raised after a plain flat-list answer to "list the open cards" felt inconsistent. Decided via interview: always render as a table (ID/Status/Title); order by Priority tier first (Critical → High → Medium → Low → unset), then by this card's four factors within each tier. Doesn't reopen this card's own "severity wasn't weighed" stance for *selection* — that's about which card a session picks up next, a different question from how a requested *listing* gets displayed. Documented in both places: `JCTsh-Operating-System.md`'s Listing open cards convention (→ v1.12) states the table/ordering rule itself; `JCTsh-Session-Card-Selection.md` (→ v1.1) gets a short note on how it combines with Priority for display, without changing what it weighs for selection.

**Done when (extended):** as above, plus both documents state the combined table/ordering rule and cross-reference each other for it. ✓

**Related:** `tos/JCTsh-Session-Card-Selection.md` (the new doc this card produced), `JCTsh-Operating-System.md` (Priority section, the adjacent-but-distinct existing concept; also its Listing open cards convention, now combined with this card for display ordering), CARD-0286 (the real pick this rule generalizes from), CARD-0258 (originated the Listing open cards convention this follow-on extends).

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

### CARD-0285 · [enhancement] [hike-izer] Carry air-quality-monitor's sensor data through the pipeline and onto the hike-izer web page

**Status:** Build

**Auto-opened from jctsh-core's maintenance check (PR #86).** Raw finding: adjustments to hikizer for air quality monitor.

**Interviewed 2026-09-17 (Joseph).** Now that air-quality-monitor's core build (Step 8 firmware/duty-cycle/replay, live-verified; Step 9 perfboard, confirmed done) is far enough along, its sensor readings (PM1.0, PM2.5, PM4.0, PM10, VOC Index, NOx Index) captured during a hike should flow through to the hike-izer web page, not just hiking-monitor's existing temp/humidity/pressure/UV.

**Real gap found while scoping:** `fetch_hike_data.py`'s Environmental Data pull is hardcoded to `--source hiking-monitor` (its own `--source` arg help text warns that omitting the filter would otherwise mix in another device's readings) -- air-quality-monitor's readings are filtered out entirely today, not merely unused.

**Scope:**
1. Extend `fetch_hike_data.py` to also pull air-quality-monitor's Environmental Data rows for the hike window, alongside (not instead of) hiking-monitor's -- both devices are carried on the same hike.
2. Carry all six AQM fields through the pipeline (PM1.0, PM2.5, PM4.0, PM10, VOC Index, NOx Index) -- no subset.
3. Display them by extending the existing Environmental Data chart/table (`html-template.html`, the CARD-0204/CARD-0207 pattern) rather than building a separate section.

**Built, 2026-09-17.** `fetch_hike_data.py` now fetches air-quality-monitor's rows into their own `aqm_rows` list, kept separate from hiking-monitor's `env_rows` throughout -- a real correctness risk found while building this: air-quality-monitor's firmware publishes `temp_f`/`humidity_pct`/`battery_v` under those *same* column names (its own SEN55/battery, not hiking-monitor's), so merging the two devices' rows into one list would have silently blended two different devices' readings into `compute_stats()`'s existing temp/humidity/battery figures. `_correlate_environmental_series()` generalized to take a `fields` tuple, called a second time with the new `AQM_CHART_FIELDS` against `aqm_rows` to add all six fields to `chart_series` without touching `env_rows`/`ENV_CHART_FIELDS`'s existing path. `build_hike_chart.py` gained three new toggle-able pairings (PM2.5/PM10, PM1.0/PM4.0, VOC/NOx), same two-per-mode pattern as the existing Temp/Humidity and Pressure/UV pairings; `html-template.html` gained matching CSS tokens (light+dark) for the six new lines. Verified with a synthetic smoke test (fake GPS+sensor rows, including planted sentinel values in fake AQM rows to confirm they don't leak into hiking-monitor's stats) -- not yet run against the real Google Sheet or a real hike.

**Watch for:** the next real hike where both hiking-monitor and air-quality-monitor are carried -- confirm the published hike-izer page's Environmental Data chart shows real, sane values (not zeros/nulls) on the three new PM2.5/PM10, PM1.0/PM4.0, and VOC/NOx toggle pairings, and confirm hiking-monitor's own existing temp/humidity/pressure/UV/battery figures on that same page look unaffected (no cross-device contamination in practice, not just in the synthetic test). This card stays in Build until observed. Not yet observed as of 2026-09-17 (no hike since this was built).

**Still unobserved as of 2026-09-22 08:40 MST, and the reason is now known — this is blocked, not merely unlucky (hike-izer cluster session startup).** Two real hikes have run since this was built (2026-09-21, 2026-09-22) and neither produced a single air-quality-monitor row: `fetch_hike_data.py`'s own count line in `docker logs hike-izer-orchestrator` reads `0 from source='air-quality-monitor'` on both, and both hikes' `_hike_data.json` on the M8 confirm `environmental_data_air_quality_monitor: []`. **Cause: air-quality-monitor is not operational yet** (Joseph, 2026-09-22) — CARD-0012 is still in Build. Nothing on this card's side is wrong: the deployed orchestrator code was checked directly and is current (`/app/fetch_hike_data.py` and `/app/build_hike_chart.py` byte-size-match the repo copies, 70722/32018 — explicitly verified rather than assumed, per CARD-0286's own deploy-gap lesson).

**Therefore: this Watch-for can't fire until CARD-0012 lands.** A future session should check CARD-0012's status before re-investigating the empty AQM series — the absence of data is expected until then, not a pipeline fault.

**Done when:** a real hike with both hiking-monitor and air-quality-monitor active shows all six AQM fields on the published hike-izer page, in the same Environmental Data area as the existing temp/humidity/pressure/UV lines, verified against real MQTT-logged data for that hike.

**Related:** CARD-0012 (air-quality-monitor's own build), `components/hike-izer/fetch_hike_data.py` (`ENV_CHART_FIELDS`, `AQM_CHART_FIELDS`, `--source` filtering), `components/hike-izer/build_hike_chart.py` (`ENV_CHART_MODES`), `components/hike-izer/html-template.html` (Environmental Data chart).

---

### CARD-0284 · [idea] [tos] Persistent per-cluster Claude Code sessions — faster ramp-up and cross-work pattern recognition, without a second knowledge store — RESOLVED 2026-09-18
**Status:** Done

Archived to `tos/card-archive.md` on 2026-09-22 (CARD-0193) — 22613B, over the 5000B size threshold.

---

### CARD-0283 · [enhancement] [tos] Concurrent-session editing: reread kanban-board.md only on a failed Edit, not before every edit — RESOLVED 2026-09-17

**Status:** Done

**Raised 2026-09-17 (Joseph), from a discussion about what's actually clunky in the current concurrent-session workflow.** Not real collisions — the friction is that `CLAUDE.md`'s existing "Concurrent Sessions" guidance has every session reread `tos/kanban-board.md` fresh immediately before *every single edit*, as a precaution, even though the overwhelming majority of edits have zero real contention with another session. That's a real, continual cost (a full reread round-trip per edit) paid regardless of whether anything actually changed underneath.

**Decided 2026-09-17 (Joseph's call) — try the lazy/reactive alternative first, before anything heavier (a lock file, etc.):** stop rereading preemptively. Attempt an edit against the content already in hand; `Edit`'s own exact-string match already fails safely if another session changed that text in the meantime. Only reread (the specific affected section, then retry) when an `Edit` call actually fails due to a stale match. Same safety guarantee as today — a stale write still can't silently clobber another session's change — just no wasted reread when there was never any real contention. A heavier fix (a session-scoped `.kanban.lock` file, claimed once per multi-edit pass rather than per edit) was discussed as the next lever if this alone doesn't cut it, not adopted now.

**Scope:** update `CLAUDE.md`'s "Concurrent Sessions" section — replace "Re-read shared files fresh immediately before editing them, especially `tos/kanban-board.md`" with the reactive convention above. No code/tooling change, no new files — a pure convention change for how Claude Code sessions (this one included) behave when editing shared files going forward.

**Done when:** `CLAUDE.md` reflects the new convention, and it's been used at least once in a real session without incident (an Edit failing due to genuine staleness, caught and retried correctly, or simply many edits going through with fewer rereads than the old convention would have required). **Met, 2026-09-17** — `CLAUDE.md`'s "Concurrent Sessions" section already reflects the convention, and this very `tos` component session exercised it live: a long string of `Edit` calls against `tos/kanban-board.md` (this same file), no preemptive reread before any of them, zero stale-match failures — the "many edits going through with fewer rereads" branch of the done-when, satisfied in practice rather than left to a future session.

**Related:** `CLAUDE.md` ("Concurrent Sessions" section), `tos/kanban-board.md` (the shared file this convention protects).

---

### CARD-0282 · [enhancement] [tos] Session Start's log dashboard check should use the live `/status` page, not raw `jctsh.log` grep — RESOLVED 2026-09-17

**Status:** Done

**Raised 2026-09-17 (Joseph), directly from CARD-0281's false alarm.** That card's original "garage-radar silent for 3 months" finding came from grepping the raw `/mnt/jctsh-logs/jctsh.log*` file for a component's activity — but this project already has a documented convention (memory: "Dashboard vs raw log") that the raw file only gets a line written after a flush trigger (a state change, 15 minutes, or another message), while the live `/status` page reflects real, current per-component connection/freshness state directly. Querying `/status` in this same investigation immediately showed the device `Connected`/`Online` with a recent heartbeat — the raw-grep method gave a materially wrong picture that a `/status` check would have caught immediately.

**Essence:** `CLAUDE.md`'s Session Start step 8 ("Examine the JCTsh Log Dashboard... for system problems or data issues") should explicitly point at `/status` (or another live, current-state view) as the way to check "is component X actually alive right now" — not a raw-log grep, which is the wrong tool for that specific question even though it's a fine tool for "what did component X say recently."

**Interviewed 2026-09-17 (Joseph), in the `tos` component session — added a second dimension beyond the original essence.** This is also a new general-session-vs-component-session distinction, the same shape as CARD-0284's kanban-tag scoping: a **general** session's device-health check scans `/status` across every device; a **component** session scans it for only the device(s)/component(s) it actually covers, not the whole fleet.

**Scope:**
1. `CLAUDE.md`'s Session Start step 9 (the actual current step number — the card's original "step 8" reference was already stale) points at `/status` for a liveness check, explicitly contrasted with the raw-log grep's different purpose ("what did X say recently," not "is X alive now").
2. `tos/JCTsh-Component-Session-Start.md` gains a new step 5, mirroring step 3's kanban-scoping principle: a component session scopes the `/status` check to its own covered component(s) only.

**Built, 2026-09-17.** `CLAUDE.md` step 9 updated in place with the `/status`-vs-raw-log distinction and the general-vs-component-session scoping note. `JCTsh-Component-Session-Start.md` → v1.5, new step 5 added.

**Done when:** both documents state the `/status`-for-liveness rule and the general-vs-component scoping distinction. **Met.**

**Related:** CARD-0281 (the false alarm that raised this), CARD-0284 (the analogous kanban-scoping precedent this generalizes to device health), `CLAUDE.md` (Session Start step 9), `core/logging/log_server.py` (`/status` endpoint), `tos/JCTsh-Component-Session-Start.md` (new step 5, now v1.5).

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

**Status:** Backlog

**Auto-opened 2026-09-15 from photo-server's maintenance check (CARD-0128).** Raw finding: Immich update available: v3.2.1 (currently running v3.2.0).

**Risk assessment, checked 2026-09-15 against the real upstream release notes (github.com/immich-app/immich/releases/tag/v3.2.1):** patch release, bug-fixes only, no breaking changes or database migrations mentioned. Notable fixes: connection-pool exhaustion during sync, search modal functionality, partner-shared assets now visible on the people page, person-merge restored for named individuals, timeline/archive behavior corrected, face-detection/metadata extraction improvements, password-reset flag handling. Low-risk upgrade.

**Superseded target, 2026-09-17 — a second maintenance-check finding (PR #84) landed for v3.2.2 before v3.2.1 was ever applied.** Checked the new release's notes too rather than assuming: v3.2.2 (2026-09-15) is a single-issue bug-fix patch (face-reassignment now correctly skips other users' faces during reassignment) — no breaking changes, no database migration, same low-risk profile as v3.2.1. Folded into this card rather than opening a duplicate; target bumped straight to v3.2.2 since applying it supersedes v3.2.1 entirely.

**Update stays a deliberate manual step, per `components/photo-server/operations.md`'s existing "notify-only, not auto-update" policy** (Immich has surfaced real bugs in single patch versions before — CARD-0037/0042/0043, the HEIC distortion issue — auto-applying unattended on a library holding irreplaceable family photos isn't worth the risk): `docker compose pull && docker compose up -d` in `~/immich-app` on the M8.

**Done when:** the M8's `immich-app` stack is running v3.2.2 (confirmed via `/api/server/version` or the Immich UI), all Immich containers (`immich_server`, `immich_machine_learning`, `immich_postgres`, `immich_redis`) report Docker-healthy after the recreate, and a spot-check of the web UI (login, browse a library) confirms nothing regressed.

**Related:** `components/photo-server/operations.md` (the Immich Update Check mechanism that raised this), `components/photo-server/immich-update-check.py`, CARD-0128 (`open_finding_pr()`, the auto-open mechanism).

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

**Raised 2026-09-14 (Joseph)**, after asking for the real total API cost of all hike-photo captioning to date and finding the number effectively unavailable.

**Original framing corrected same day, 2026-09-14 (Joseph caught it) — this is not a lost-data bug, CARD-0246 already covers durability.** First pass at this card assumed `docker logs hike-izer-orchestrator` (which only went back to today's M8 reboot) was the *only* record of `CostTracker.summary()`, and proposed a new durable file to fix it. Wrong — `generation.py` already calls `mqtt_log.publish_log("System", f"...(API cost: {tracker.summary()})")` on every publish, a real MQTT publish (not stdout) to the Pi's broker, persisted by `log_server.py` into `/mnt/jctsh-logs/jctsh.log` (CARD-0246's own durable, journald-independent log). Confirmed live by reading that file directly: real historical cost figures already exist there, e.g. `2026-09-05 19:35:22 MST | hike-izer-orchestrator | System | Published enriched hike summary for 2026-09-03: ... (API cost: $0.1984 (9 API calls, 38,052 in / 326 out tokens)).` So today's M8 Docker-log gap, while real, never actually put this data at risk — it was durably captured elsewhere the whole time. No M8-side persistence fix needed; this card is retitled and rescoped to the two real, narrower gaps found while checking that:

1. **Not structured.** The cost figure is a substring inside a free-text notification message — getting "total spent to date" means grepping and regex-parsing log lines, not querying a field.
2. **The Pi's `jctsh.log` itself only goes back to 2026-09-03** (5,611 lines total, all components, checked live) — so cost data for most of the 20 real hikes this session found (2026-06-18 through 2026-08-29) is already gone from this channel too, for an unrelated reason (log retention window, not the M8 reboot). A structural fix needs to store cost data somewhere with its own real retention, not depend on the general log's window.

**Decided 2026-09-14 (Joseph's call) — a dedicated Google Sheet, matching this project's existing data architecture.** Every other structured JCTsh data type (Environmental Data, Hiking Observations, GPS Track, Wildlife Detections, Hike Start Forecast) already lives in a named Sheet, written via `core/data-pipeline/environmental-data.gs`'s `doPost` dispatching on `payload.component`, with an auto-provisioned sheet, an `appendRow`, and (per the `wildlife-detection` branch's existing convention) a `_relayLog(...)` call for dashboard visibility alongside the sheet write. A "Hike-izer Costs" sheet follows this exact pattern rather than introducing a new mechanism.

**Scope, grounded in the real existing code (`environmental-data.gs`, `generation.py`, `cost_tracking.py`):**
1. `environmental-data.gs`: new `doPost` branch, `payload.component === 'hike-izer-cost'` — auto-provisions a `Hike-izer Costs` sheet (columns: `ts`, `file_stem`, `run_type` [step1/step2/daily-refresh], `dollars`, `calls`, `input_tokens`, `output_tokens`, `web_searches`), dedup-checked before `appendRow` (decided below), then `_relayLog('hike-izer-cost', 'System', ...)` matching the `wildlife-detection` branch's own pattern.
2. `cost_tracking.py` or `generation.py`: alongside the existing `mqtt_log.publish_log(...)` call (kept as-is for dashboard visibility), POST the same `CostTracker` fields to the Apps Script endpoint as `component: 'hike-izer-cost'`.
3. **Backfill the ~9 real cost figures still recoverable from `jctsh.log`** (2026-09-03 onward) into the new sheet once it exists, decided 2026-09-14 (Joseph) — grep them out of the log and add them manually rather than starting the sheet's history from scratch.

**Decided 2026-09-14 (Joseph) — dedup like GPS Track/Hiking Observations.** Same pattern CARD-0243/CARD-0244 established: check for an existing `(file_stem, run_type)` match before `appendRow`, return `{"status": "duplicate", ...}` on a match — protects against a retried generation run (`GENERATION_MAX_ATTEMPTS`) double-posting the same run's cost.

**Not yet scoped:** whether `run_type` needs finer granularity than step1/step2/daily-refresh.

**Built, 2026-09-22 (hike-izer cluster session).** `environmental-data.gs`: new `doPost` branch for `payload.component === 'hike-izer-cost'`, mirroring the wildlife-detection branch's own pattern exactly -- self-provisions the `Hike-izer Costs` sheet (`ts`/`file_stem`/`run_type`/`dollars`/`calls`/`input_tokens`/`output_tokens`/`web_searches`), applies the same CARD-0235 bare-date-string defense (file_stem is the identical shape that bug hit), dedups on `(file_stem, run_type)` before `appendRow`, then `_relayLog(...)`. `SCRIPT_VERSION` bumped. `generation.py`: new `_post_hike_cost()` helper (POSTs the tracker's real fields, treats `"duplicate"` as success same as wildlife-detection) plus `_post_hike_cost_and_log()`, a non-fatal wrapper -- a Sheet-write failure logs an `Alert` but never turns an otherwise-successful hike-summary publish into a failure, same graceful-degradation principle as `place_context.py`. Wired into all three call sites (`run_and_log`/step1, `run_step2_and_log`/step2, `run_daily_refresh_and_log`/daily-refresh), alongside their existing `mqtt_log.publish_log(...)` calls, exactly as scoped -- not replacing them.

**Verified so far:** `generation.py` compiles clean (`py_compile`); a synthetic smoke test (mocked HTTP layer) confirms the payload shape matches the sheet's columns exactly, `"duplicate"` is treated as success, a real Apps Script rejection raises, and the non-fatal wrapper swallows a connection failure and logs an `Alert` instead of propagating. `environmental-data.gs`'s new branch checked for balanced braces/parens across the whole file (no Node/clasp available in this environment for a real syntax check).

**Not yet done -- a real ordering dependency, not just "remaining work":** the Apps Script change requires Joseph to paste it into the bound editor and redeploy (this repo's own established process -- no automated deploy path exists) *before* `generation.py` goes live on the M8. Deploying the Python side first would mean every `hike-izer-cost` POST falls through to `doPost`'s final `else` (the general Environmental Data branch, since `payload.component` wouldn't match anything yet) and writes a garbage row into the real Environmental Data sheet -- checked directly against that branch's own logic, not assumed. Sequence: (1) Joseph deploys `environmental-data.gs`, verified via `?action=version` showing `2026-09-22.1-hike-izer-cost-sheet`; (2) `generation.py` deployed to the M8 orchestrator; (3) backfill the ~9 recoverable historical cost figures from `jctsh.log` (2026-09-03 onward) via the now-live endpoint; (4) verified against a real generation run writing a real row, confirmed directly in the Sheet.

**Deployed and backfilled, 2026-09-22/23 (same session, Joseph redeployed `environmental-data.gs`).** `?action=version` confirmed `2026-09-22.1-hike-izer-cost-sheet` live (needed a retry -- this endpoint's own well-documented occasional flakiness, CARD-0275/0258/0222, not a real problem). Real end-to-end test through the actual `generation.py` code path (not curl -- curl's own POST-through-redirect handling hit an unrelated 405/artifact against this same endpoint, worth knowing about if anyone else tries to curl-test this Apps Script directly): first `_post_hike_cost()` call returned `ok`, an identical second call returned `duplicate` with no exception -- confirms the row landed and the dedup guard matched a real row, not just that the POST didn't error. `generation.py` deployed to the M8 orchestrator (checksum-verified, container rebuilt, healthy).

**Backfill done -- smaller than originally scoped, and that's expected, not a problem.** `jctsh.log`'s retention window has rotated well past 2026-09-14 (when this card estimated "~9 recoverable figures back to 2026-09-03") -- only 6 `API cost:` lines remain, covering 2026-09-21/09-22 only. Posted the 4 unique `(file_stem, run_type)` combinations found (2026-09-21 step1 $0.0220, 2026-09-21 daily-refresh $0, 2026-09-22 step1 $0, 2026-09-22 step2 $0), all confirmed `ok`. Verified twice via `action=export&sheet=Hike-izer%20Costs` (Python urllib, not curl -- same redirect quirk) -- both reads show exactly these 4 rows with correct fields and correct UTC-converted timestamps.

**Real limitation surfaced live, worth recording rather than silently working around:** the 6th log line was a second `step2` run for 2026-09-22 (14:57:44 MST -- this session's own CARD-0323 verification pass, re-running step2 on the same hike). Posting it correctly came back `duplicate` under the current `(file_stem, run_type)` dedup key -- harmless *this time* since both runs cost $0.0000, but if a future repeated step2 run on the same hike ever has a genuinely different cost the second time, that second real figure would be silently discarded, not recorded as an error. This is exactly the "not yet scoped: whether run_type needs finer granularity" question this card already flagged -- not fixing it now (iterative discipline: no real case has actually lost real data yet), but now there's a concrete, observed instance of the tradeoff instead of a hypothetical one.

**Fixed, same session, on Joseph's direct instruction ("fix it now") rather than left as an accepted limitation.** Widened the dedup guard from matching just `(file_stem, run_type)` to requiring every cost field to match too (`dollars`/`calls`/`input_tokens`/`output_tokens`/`web_searches`) -- so it now only treats a POST as a duplicate when it's an exact resend of an already-recorded event (the real risk the guard exists for -- a client resending after a read-timeout-but-server-actually-wrote scenario, CARD-0276's own established failure class), never when a second, legitimately different run happens to share the same `(file_stem, run_type)`. `SCRIPT_VERSION` bumped to `2026-09-22.2-hike-izer-cost-dedup-fix`. Redeployed by Joseph and verified live via three direct calls against the real endpoint: an exact resend (identical file_stem/run_type/every cost field) correctly came back `duplicate`; a new (file_stem, run_type, cost) combination came back `ok`; and -- the exact bug this fix targets -- a second post sharing the same `(file_stem, run_type)` but with a genuinely different cost (`calls: 3, dollars: 0.15` vs. the first's `calls: 1, dollars: 0.0042`) also came back `ok`, confirmed as a real new row rather than being silently swallowed as a false duplicate.



**One small, non-blocking loose end:** a manual test POST (`file_stem: "TEST-0270-verify"`) made through the real `_post_hike_cost()` function returned `ok` then `duplicate` on a repeat, exactly as expected -- but doesn't actually appear in a subsequent `action=export` read of the sheet. Not chased further (disposable test data, not a real-data or dedup-correctness question -- the 4 real backfilled rows and the real 5th-entry duplicate check above already demonstrate both write and dedup work correctly against genuine data). Worth deleting that stray test row from the Sheet directly next time it's open, and worth a second look only if the same unexplained gap ever shows up on real data.

**Done when:** a real hike-izer generation run writes a real row to the `Hike-izer Costs` sheet with correct fields, confirmed via the Sheet directly (not just "the POST returned 200"), and a "total cost to date" figure can be computed with a plain Sheets formula (e.g. `SUM`) rather than log-parsing. **Met, 2026-09-22/23** -- four real rows confirmed via two independent `action=export` reads, `=SUM(D2:D)` over the `dollars` column now gives a real total-cost-to-date figure without any log-parsing.



**Related:** CARD-0246 (the Pi log durability this card initially, incorrectly, thought needed re-solving — it doesn't), `core/data-pipeline/environmental-data.gs` (`doPost`, the `wildlife-detection` branch this new branch mirrors), `components/hike-izer-orchestrator/cost_tracking.py`, `components/hike-izer-orchestrator/generation.py` (`mqtt_log.publish_log` call sites this adds a Sheet POST alongside), CARD-0232 (the investigation that surfaced this gap while trying to answer "how much has captioning cost so far").

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

**Raised via automated maintenance finding (PR #77, jctsh-core), 2026-09-12.** Routine version-bump finding: Home Assistant 2026.9.2 available, running 2026.9.1.

**Evaluated 2026-09-13 — release notes checked, looks safe, not applied yet (Joseph's call — evaluate first, decide separately whether/when to apply).** 2026.9.2 is a patch release, entirely small per-integration bug fixes and dependency bumps (Hive, Roomba, Openhome, WebOS TV, Vizio, Tesla Fleet, Nest, ViCare, UniFi, Reolink, Weheat, MELCloud, Enphase, ZHA, ESPHome-setup robustness, frontend bump). Nothing touching MQTT, the SmartThings integration, the Matter integration/Matter Server (CARD-0262), Google Assistant, or the recorder — the pieces this instance actually depends on.

**Applied 2026-09-14, per Joseph's explicit go-ahead ("apply updates for 266 and 267, let scheduled reboot handle it") — far more painful than any prior HA update on this project (CARD-0233/0236-0240), for reasons unrelated to the update itself.** `docker compose pull homeassistant` hung indefinitely — this surfaced two distinct real bugs, both fully root-caused and documented on CARD-0268 rather than here (that card is the durable home for the Docker/containerd investigation): (1) live confirmation that a Pi 3B+'s shared USB 2.0 bus lets an image pull starve HA's own I/O and make it briefly unhealthy; (2) a separate, unrelated dockerd bug (Docker 29.6.1) where an OCI "referrers" 404 + manifest 404 double-miss makes `docker pull`'s own orchestration hang silently for 5+ minutes, reproducing every time and surviving a full host reboot.

**Resolved via `sudo ctr -n moby images pull ghcr.io/home-assistant/home-assistant:stable`** (containerd's own lower-level pull CLI, bypassing dockerd's stuck orchestration entirely — see CARD-0268 for the full investigation and the revised procedure this establishes for future updates). Completed cleanly after ~50 minutes (mostly slow extraction off the USB 2.0 bus). `docker compose up -d homeassistant` then recreated the container (after working around a stale-report/naming rough edge, also logged on CARD-0268) — confirmed healthy and running **2026.9.2** via `docker exec homeassistant python3 -c "import homeassistant.const as c; print(c.__version__)"`.

**Post-update entity-availability check run per root `CLAUDE.md`'s Home Assistant Docker Setup section.** Immediately after restart: 997 total entities, 253 unavailable/unknown — matching the documented pattern where a config entry reports `loaded` without having actually resynced. Reloaded `smartthings` (`Home Main`) and `ring` (`joscthomas@gmail.com`) config entries via `POST /api/config/config_entries/entry/<id>/reload` — both came back to `loaded` state, and unavailable count dropped to 123. **One real gotcha hit doing this reload, worth remembering for next time:** the first `smartthings` reload attempt was issued with a 30s client-side HTTP timeout, which was too short — the client gave up and closed the connection while HA was still mid-setup, which left the config entry in genuine `setup_error` state (worse than the stale-but-loaded state it started in) rather than just failing to reload. Fixed by retrying with a 120s timeout, which let it complete and land back on `loaded` correctly. **A reload's HTTP client needs a long timeout (120s+), not the usual quick-API-call assumption — the entry can be left in a worse state than before if the client aborts mid-setup.** The remaining 123 unavailable entities were checked and are all explainable by normal, non-update causes, not this integration-resync pattern: scenes and buttons structurally show `unknown`/`unavailable` until first triggered/pressed (21 scenes, most of the 15 buttons), several "peanut"-branded outlets are seasonal Christmas decorations genuinely unplugged in September, a handful of media players are simply powered off, and the Nabu Casa backup/cloud-voice entities have never been configured on this instance (present in every check all session, unrelated to this update).

**Related:** CARD-0128 (the auto-PR intake pipeline this came through), root `CLAUDE.md` (Home Assistant Docker Setup, the post-update check run), CARD-0268 (full root-cause investigation and the revised Docker-pull procedure this update's difficulty established).

---

### CARD-0265 · [bug] [logging] Dashboard still unreadably dark after the earlier brightness fix — RESOLVED 2026-09-12 MST (transient tab state, not a persistent cause)

**Status:** Done

**Raised 2026-09-12 MST (Joseph), reopening the legibility complaint** — the brightness-only CSS fix (deployed as `daefc73`, "Improve legibility of / and /status dashboard pages") did not resolve it. New evidence this time, ruling out what was previously suspected: it's the **only** browser tab/window on the laptop with this problem (every other site renders normally), and the dashboard **was fine until recently** — not a longstanding Windows/HDR condition, and not a global browser dark-mode toggle (already checked off, per the earlier session's troubleshooting).

**Real finding, checked directly against `core/logging/log_server.py`, not assumed:** none of the three served pages (`/`, `/status`, `/kanban`) declare a `color-scheme` anywhere — no `<meta name="color-scheme">` tag, no CSS `color-scheme` property on `:root`/`html`/`body`. All three use hardcoded dark palettes (`background:#1a1a1a`, etc. on `/`/`/status`; CSS-variable light/dark on `/kanban`) but never tell the browser "this page already implements its own theme."

**Why this plausibly explains every symptom that ruled out the earlier hypotheses:** Chrome's "Automatically darken web content" (force-dark) feature decides **per page** whether a site already has its own dark theme; a page with no `color-scheme` declaration can get misjudged and have Chrome's own darkening/inversion filter applied on top of the page's already-dark palette — producing exactly this symptom (isolated to one specific site, since the heuristic runs per-origin; explains why the earlier brightness bump did nothing, since that filter operates on the *rendered* colors, not the source values; and is consistent with "recently," since a Chrome update changing the heuristic, or the feature getting toggled at some point, would explain the timing without anything in JCTsh's own code changing).

**Fix:** add an explicit `color-scheme` declaration to all three pages so Chrome (and any browser implementing the same standard) knows not to second-guess the theme — `<meta name="color-scheme" content="dark">` for `/` and `/status` (always-dark, no light variant), `content="light dark"` for `/kanban` (which already supports both via its own `@media (prefers-color-scheme: dark)` block).

**`color-scheme` fix built and deployed, 2026-09-12 — did not resolve it.** Added `<meta name="color-scheme" content="dark">` (`/`, `/status`) / `content="light dark"` (`/kanban`), deployed to the Pi, confirmed present in the served source. Joseph's browser still showed the dashboard too dark after a hard refresh (Ctrl+Shift+R).

**Narrowed decisively away from server-side, 2026-09-12.** Joseph opened the dashboard in a Brave **private window** and it rendered fine — ruling out JCTsh's code and the missing `color-scheme` declaration (real, worth having, but not the actual cause here) as the source. Checked `brave://extensions` (no dark-mode/reader extension present) and the site-info permissions panel for `pi1.local` (no dark-mode-related entry exposed there) in a normal window — both came back clean, ruling out the two most likely persistent culprits before a Brave-specific global setting (`brave://settings/appearance`'s "Automatically darken web content") could even be checked.

**Resolved itself, 2026-09-12, before that last check completed — closing the affected tab and opening a fresh one fixed it.** No persistent setting or extension was ever confirmed as the cause. Best-supported explanation given everything ruled out: a **transient per-tab rendering glitch** in that specific Brave tab/renderer process, not a persistent extension, site setting, browser-wide setting, or JCTsh code issue.

**Done when:** the dashboard renders correctly — **met**, confirmed in a fresh tab. Root cause not conclusively identified (ruled out: JCTsh's own CSS, missing `color-scheme`, extensions, per-site permissions) — if this recurs, check `brave://settings/appearance`'s "Automatically darken web content" toggle next, the one remaining unchecked hypothesis. The `color-scheme` meta tag addition stays regardless — correct practice, harmless, and worth having even though it wasn't the actual fix here.

**Related:** the earlier (insufficient) brightness fix, `core/logging/log_server.py`.

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
**Priority:** Medium

**Raised 2026-09-12, from a discussion about whether the Pi's hardware is still adequate for its assigned role** (MQTT broker, Node-RED, HA, log server). Conclusion of that discussion: no evidence of the Pi actually straining — no performance complaints anywhere in this project's history, the real write-heavy state is already routed to the USB drive (CARD-0159), and CARD-0164's own direction reduces HA's SmartThings-entity load going forward rather than growing it. This card is the one concrete, already-identified inefficiency worth fixing regardless — not evidence the hardware needs replacing.

**Current state, per `project_jctsh.md`'s own note (2026-07-12):** the Pi boots into `graphical.target` with a full desktop session running (X11/Wayland, desktop panel widgets, `rpi-connect`, etc. — confirmed as installed cruft during CARD-0125's own apt-upgradable audit). Day-to-day access is SSH-only — the physical desktop GUI was used exactly once, during initial setup, never since. Pure overhead for a host whose real job has nothing to do with a local display.

**Scope:**
1. `sudo systemctl set-default multi-user.target` on the Pi.
2. Reboot and verify every Pi-native service comes back clean: Mosquitto, Node-RED, the `homeassistant` Docker container (reaching its own `healthy` state, not just "container exists" — same bar CARD-0158's reboot-health-check already applies), `jctsh-logging`.
3. Confirm nothing actually depended on the desktop session running (unlikely, per the "used once during setup" history, but verify rather than assume).
4. If a local display/desktop is ever needed again for troubleshooting, `sudo systemctl start graphical.target` (or `startx`) works on demand without needing to boot into it every time — document this in `SOFTWARE-ENVIRONMENT.md` or similar as the "how to get a desktop back if you ever need one" note.

**Real finding, checked live before touching anything, 2026-09-12 — the premise was already stale.** `systemctl get-default` showed `multi-user.target` (headless) already set as the persistent default, and `uptime` showed the Pi had been running over a day since its last reboot — meaning it already booted headless successfully, with no action from this card. The desktop-environment packages (`lightdm`, `xserver-xorg-core`, etc.) are still installed as leftover cruft (matches CARD-0125's own finding), but the boot target itself was never actually graphical by the time this card was worked — the 2026-07-12 `project_jctsh.md` note this card was raised from had simply gone stale in the two months since. Steps 1-3 of the original scope needed no action; confirmed all relevant services healthy on the already-booted system instead of forcing an unnecessary second reboot: `mosquitto`/`nodered`/`jctsh-logging` all `active`, `homeassistant` Docker container `healthy` — this retroactively satisfies "verified via a real reboot test," since the current live state *is* the result of the last real cold boot.

**Step 4 done and actually verified, not just written down.** The first pass documented `systemctl start graphical.target` alone, but that's not sufficient on its own — the Pi has no monitor attached (shelf-mounted, laundry room), so nothing would be there to view it. Found and fixed: activated **Raspberry Pi Connect** (already installed, per CARD-0125's own audit, but never signed in) via `rpi-connect on` + `rpi-connect signin` (a device-link flow — had to redo it once, since the first attempt died when the SSH command hit its own timeout before the user could approve it; the fix was running it detached via `nohup`). Live-tested end to end: a real browser screen-share session at `connect.raspberrypi.com` initially failed ("Failed to connect to screen sharing server") until `graphical.target` was started first — confirmed that dependency directly, not assumed — then reconnected successfully to a real, interactive desktop. `SOFTWARE-ENVIRONMENT.md`'s "Boot Target" section now documents the complete, verified procedure.

**Done when:** the Pi boots headless by default, verified via a real reboot test (not just a manual `systemctl isolate`) — matching this project's own standing convention (CARD-0158, CARD-0129) of confirming a boot-time change against an actual cold boot, not a simulated one — with every service listed in step 2 confirmed healthy afterward. **Met**, via the already-occurred reboot rather than a newly-forced one — same verification bar, no unnecessary service interruption.

**Related:** `project_jctsh.md` (the original 2026-07-12 observation), CARD-0125 (the apt-upgradable audit that found the desktop-environment packages), CARD-0158 (the reboot-health-check this reuses for post-reboot verification), `SOFTWARE-ENVIRONMENT.md`.

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

**What carries over from air-quality-monitor's now-proven design, discussed 2026-09-10:**
- Pololu D24V10F3 buck regulator in place of the boost converter (resolves CARD-0070's original quiescent-current concern).
- BK-1208 latching Power Switch, separate from the Intent switch (resolves CARD-0181's missing true power-off).
- The three-signal model (Intent / Power Connected / Power Switch) and the bounded-attempt/15-min-retry WiFi state machine, in place of hiking-monitor's own accumulated patches (CARD-0217, CARD-0045).
- The SSID-based `pi1.local`/DuckDNS broker switch (CARD-0254 already scoped this as a port from air-quality-monitor).

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
1. **WiFi boot gating:** v1 defers `wifi.disable()` to the first interval tick (its `on_boot` runs at priority 600, before WiFi's own 250). v2's three-condition gate (Intent off AND Power-Connected AND battery ≥ upload-safe threshold) runs as the literal first `on_boot` action (AQM's block runs at priority ‑100, after WiFi's setup).
2. **Bounded-attempt/retry state machine:** v1 has no formalized version of this (part of why CARD-0226's reboot loop is still unexplained). v2 imports AQM's explicit machine: ~2-min attempt window → `wifi.disable()` → ~15-min backoff → retry, uncapped retry count, 2 timestamps + 1 bool.
3. **Upload-safety voltage gate:** v1 has one threshold only (3.4V generic low-battery shutdown). v2 adds a second, higher "upload-safe" gate (AQM's provisional value: 3.8V, unconfirmed by bench sweep) that only gates attempting WiFi — the general cutoff is unchanged.
4. **Broker addressing:** v1 always targets `jctsh.duckdns.org`, even on the home LAN (needless internet round-trip). v2 imports AQM's `wifi_info: ssid:` + `on_connect:` switch to `pi1.local` on `JCTnet1`, plus `skip_cert_cn_check: true` — note CARD-0254 already scopes porting this to the *current* v1 unit regardless of v2's timeline.
5. **Dock-detect coupling:** v1 stops field logging once `dock_detect` goes HIGH. AQM's pattern (which v2 would inherit) decouples them — field logging runs unconditionally, dock-detect HIGH only ever triggers a background WiFi attempt. A real behavioral change, not just a wiring port.
6. **Deep sleep:** v1's boost converter stays always-on with undocumented/unmeasured sleep-current draw — not true deep sleep. v2 folds in CARD-0201's true deep-sleep-between-samples goal.
7. **Solar voltage sensing:** v1 never wired the ADC divider CARD-0017 designed. v2 folds in CARD-0202, rolling it into the power redesign.

**Hike-data analysis findings relevant to this rebuild, 2026-09-22 (hike-izer cluster session, synthesizing CARD-0226's now nine logged recurrences) — validates the founding premise with real numbers, and surfaces one real gap in the difference inventory above.**
- **This isn't a rare edge case anymore — it's the norm.** Nine recurrences in 24 days, essentially every hike since 2026-08-29 shows the reboot loop in some form. Environmental Data coverage across the hikes analyzed so far ranges 14.8%-72.1%, most well under half. Stronger evidence than existed when this card was first raised (four recurrences over two weeks) for the actual premise -- this is v1's dominant reliability problem, not an occasional annoyance.
- **New clue, not previously checked: a real battery-voltage dip lands at the exact reboot instant, on 8 of 9 reboot-adjacent readings checked so far across three hikes.** Every surviving reading right at a reboot timestamp shows an isolated ~0.15-0.3V dip below its neighbors, recovering by the very next reading. Battery was well above the 3.4V cutoff on the hikes checked (4.0-4.18V) -- ruling out simple depletion as the trigger, and instead pointing toward a genuine instantaneous current-spike/regulator-headroom issue: the same physics `JCTsh-Build-Standards.md` §2.14 point 9 already documents, just not WiFi-TX-triggered this time (field mode has no WiFi active) -- something else in the firmware's own periodic housekeeping is the more likely spike source. **This is real, direct evidence in favor of the regulator/cap upgrade already planned above (Pololu D24V10F3 + 470µF/4.7µF) -- that fix targets exactly this failure class, independent of ever identifying the precise trigger.**
- **Open forensic detail, not yet explained, worth watching for on a future live capture: reboots cluster roughly every ~15 minutes, not on every 2-minute field-mode wake.** Something in the firmware's own periodic housekeeping (candidate raised on CARD-0226: the MQTT component's reconnect-backoff logic, which runs continuously even with no active connection) is a more likely proximate cause than anything tied to the 2-min sensor-read cycle itself.
- **Real gap in this card's own software/firmware difference inventory above: no item currently covers CARD-0226's own Done-when item 2 -- per-record delivery tracking on the replay path (QoS 1 with a real broker ack, not v1's QoS 0 fire-and-forget).** Every analyzed hike's coverage shortfall is consistent with exactly this mechanism: the device believes replay succeeded ("Hike log replay complete."), but a large fraction of buffered readings never actually landed. Porting AQM's power/retry design alone does not fix this -- it's a separate, additional software change v2 needs on the replay path specifically, regardless of whether the power redesign eliminates the reboot trigger itself. Should be added as its own item to the software/firmware list above, not left implicit. **Confirmed 2026-09-22: air-quality-monitor's own replay path (`aqm_log_replay_stream`) also publishes at `qos: 0` (identical to hiking-monitor's `hike_log_replay_stream`)** -- so porting AQM's design literally imports this same weakness rather than fixing it. If this gets fixed, it needs its own fix on both devices, not an inherited one.
- **Real gap found 2026-09-22, likely more consequential than any item above: hiking-monitor's `mqtt:` block never got the one-line fix AQM's own firmware already validated for the exact bug CARD-0226 has been chasing.** ESPHome's MQTT component force-reboots the device if its internal `last_connected_` timer exceeds 15 minutes (`reboot_timeout`, default) -- AQM found this live 2026-09-09 (its `mqtt:` block's own comment: *"ESPHome's own watchdog was rebooting the device right as our backoff neared completion"*) and fixed it with `reboot_timeout: 0s`. hiking-monitor's config has no such line, still runs the 15-min default -- and CARD-0226's own recurrences cluster at almost exactly that interval. CARD-0045 (archived, Done) closed this exact concern in 2026-08-27 as "moot" once WiFi was disabled during field mode, but never field-verified that assumption, and AQM's later finding directly contradicts it (disabling the connection attempt doesn't reset the component's own internal timer). **This needs to be an explicit, named item in v2's software/firmware port list, not assumed to come along automatically with the rest of AQM's design** -- see CARD-0226's own new note (2026-09-22) for the full reasoning, and consider testing `reboot_timeout: 0s` on the *current* v1 hardware directly, independent of v2's timeline, since it's a single reversible OTA-flashable line.
- **A concrete, sharp acceptance bar for v2's first real field hike, once built:** zero `Reboot request from mqtt`/blank-reset-reason lines, no isolated battery-voltage dips, and Environmental Data coverage at or near 100% -- not merely "improved" over v1's observed 15-72% range. Also check for the absence of `Skipped reading - nan_sensor` events (seen pairing with blank-reset-reason boots on two recurrences) -- a real symptom beyond just the reset-reason count, and a further signal the fix actually worked structurally rather than just reducing frequency.

**Not yet scoped:** a concrete BOM, wiring plan, enclosure design, or firmware rewrite — the above is a difference inventory and this Planning session's first real decisions, not an implementation plan. The display-status idea (hardware point 9) also needs its own scoping pass before it's part of committed v2 scope. **Build is gated on AQM's own field-test outcome (see Timing decision above)** — tracked on CARD-0012 (AQM's build/install-phase card), not re-tracked here; check that card before starting v2 Build.

**Related open cards reviewed and dispositioned, 2026-09-10 (Joseph's call on each):**
- **Folded in and closed:** CARD-0070 (boost-converter/LDO swap — superseded by air-quality-monitor's Pololu regulator), CARD-0181 (missing true power-off — superseded by the BK-1208 Power Switch), CARD-0217 (heat/brownout incident — its own residual hardware-margin question resolves here), CARD-0202 (real solar_v sensing — rolls into v2's power redesign), CARD-0201 (true deep-sleep-between-samples — a from-scratch v2 build is the cleaner place for this rearchitecture risk than the current firmware). CARD-0027 (superseded by CARD-0070) updated to point here.
- **Kept open, cross-referenced, not folded:** CARD-0226 (the recurring reboot loop motivating this card — still worth chasing root cause on current hardware in parallel, in case it's fixable without a rebuild), CARD-0254 (broker-switch port — worth doing on the current unit regardless of v2's timeline).
- **Kept open, unrelated:** CARD-0203 (longer LiPo cell fit), CARD-0025 (test a retired cell) — independent of this card.

**Related:** CARD-0012 (air-quality-monitor's own build — the design basis), CARD-0254 (the SSID-based broker-switch port, kept open independent of v2's timeline), CARD-0285 (confirms AQM stays a separate device from hike-izer's own single-ownership rule, not folded into hiking-monitor).

---

### CARD-0258 · [bug] [hike-izer] Step 1 generation (session-window probe) hit the full 240s timeout fetching GPS Track — RESOLVED 2026-09-17 19:51 MST (mitigation only; root cause accepted as unidentified)
**Status:** Done

Archived to `components/hike-izer/card-archive.md` on 2026-09-18 (CARD-0193) — 12287B, over the 5000B size threshold.

---

### CARD-0257 · [enhancement] [m8] cloudflared container update available: 2026.8.3 → 2026.9.1 — deliberately deferred pending tunnel-failure reports
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

**Raised 2026-09-06**, found while auditing every `appendRow` call site in `environmental-data.gs` for the same missing-dedup pattern CARD-0243 just fixed for GPS Track. **Confirmed real gap, not yet exploited:** `doPost`'s `hiking-observations` branch appends unconditionally with no timestamp check — checked the full live sheet (all 69 rows, entire project history) and found **zero existing duplicates**, unlike GPS Track's real 29.5%. The gap is latent, not yet manifested — worth fixing proactively rather than waiting for it to bite.

**Why the exposure exists despite the device-side design already guarding against it:** `Flush Observation Queue` (`observations-pipeline.md`, CARD-0156) only deletes a queued voice-note file after a *confirmed* HTTP success (`Continue Task After Error: off` on the HTTP Request action). That protects against the common case (no response at all). It does **not** protect against the row being genuinely written server-side while the success response itself is lost or delayed before reaching the phone — Tasker would see that as a failure, leave the file queued, and resend the identical observation on the next flush trigger, with nothing on the server side to catch it. Same failure shape as GPS Track's real-world exposure, just a narrower window (a single HTTP Request's response going missing, vs. GPSLogger's own more trigger-happy retry behavior against a slow endpoint) and a much smaller dataset (69 rows vs. thousands of GPS points) — which is almost certainly why this hasn't actually happened yet.

**Dedup key: `ts` alone**, same reasoning as CARD-0243 — confirmed via a full repo grep that every real caller of `component: "hiking-observations"` sends `"source":"voice"` (there is exactly one producer, the phone's voice-note pipeline); no `(ts, source)` compound key needed the way Environmental Data's multi-source sheet requires.

**Built, 2026-09-06 — mirrors CARD-0243's exact pattern, no design deviation:** `core/data-pipeline/environmental-data.gs`'s `doPost` `hiking-observations` branch now checks `obsSheet`'s column A (timestamps only, cheap read) for an existing match immediately after `ts` is normalized and before the `_gpsLookup` call — placed before the lookup specifically to skip that extra sheet-read work on a duplicate, not just before the final `appendRow`. Returns `{"status": "duplicate", "ts": ...}` on a match, matching CARD-0243's response shape exactly. `SCRIPT_VERSION` bumped to `2026-09-06.2-hiking-obs-dedup`.

**No cleanup function needed** — zero existing duplicates confirmed live, so there's nothing for a `cleanupDuplicateHikingObservations()` to do. If this changes before deploy (unlikely, small/infrequent dataset), re-check before assuming this holds.

**Deployed and verified live, 2026-09-06.** `?action=version` confirmed `2026-09-06.2-hiking-obs-dedup` (one initial check hit a brief propagation lag showing the prior version, resolved on immediate retry — not a real deploy failure). **Real-world dedup test, stronger than planned:** a client-side curl/redirect-chain quirk made several genuine repeat POSTs of the same test observation look like client failures (405s), while the requests were actually reaching the server the whole time — confirmed by checking the sheet directly afterward: **exactly 1 row** exists for that timestamp despite multiple real resends, and a clean follow-up POST to the same `ts` returned `{"status":"duplicate",...}`. This validated the dedup against real repeated submissions, not just one deliberate pair. Synthetic test row confirmed deleted afterward (`action=export` on that window returns `count: 0`).

**Done when:** the `hiking-observations` branch rejects a duplicate-timestamp resubmission instead of appending it (verified via a real repeated test POST, same "send twice, confirm second is rejected" pattern CARD-0243 used, with the resulting synthetic test row deleted afterward) and `?action=version` confirms the redeploy took effect. **Met.**

**Related:** CARD-0243 (the identical fix, one hop earlier — this card is its Hiking Observations sibling), CARD-0215 (the original dedup pattern both cards descend from), CARD-0156 (the Flush Observation Queue design whose "confirmed success" gap this card closes), `components/hiking-monitor/observations-pipeline.md`, `core/data-pipeline/environmental-data.gs` (`doPost()`'s `hiking-observations` branch).

---

### CARD-0243 · [bug] [data-pipeline] GPS Track ingest (`doGet`, `action=gps`) has no de-duplication — 29.5% of the 2026-09-03 hike's trackpoints are exact duplicates — RESOLVED 2026-09-06
**Status:** Done

Archived to `core/data-pipeline/CLAUDE.md` on 2026-09-10 (CARD-0193) — 10848B, over the 5000B size threshold.

---

### CARD-0242 · [bug] [hiking-monitor] `Hike-izer Done` Tasker Profile has no Extra filter — Task fires (and misleadingly Flashes "publish triggered") on every GPSLogger event, not just `stopped`

**Status:** Backlog — low priority

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

**Raised via automated maintenance finding (PR #55, photo-server), 2026-09-01** — routine container-version-bump finding, same shape as CARD-0233's Home Assistant finding.

**Checked before deciding, not assumed safe:** `cloudflared`'s own GitHub release notes for 2026.8.3 (`cloudflare/cloudflared`, automated `cloudflare-warp-bot` release) — no changelog body, just build checksums, consistent with how this project's routine automated releases normally look (no flagged breaking changes or notable fixes called out).

**Real reason to still be a little careful, unlike a fully isolated bump:** this is the Cloudflare Tunnel client that `hikes.jctnet.com` runs through — the same tunnel CARD-0227 built its whole idea-image hosting feature on this session (`/webhook/idea-image`, served from the same `srv/` directory Caddy roots at). A tunnel restart is brief but real — anything hitting `hikes.jctnet.com` (Tasker's `/webhook/idea`, the idea-image upload path, the public hike pages themselves) would see a short interruption during the restart, not silent risk otherwise.

**Plan:** `docker compose pull cloudflared && docker compose up -d cloudflared` in `~/hike-izer-web-app/` on the M8 (same compose project as `web`/`orchestrator`, per `components/hike-izer-web/README.md`), verify live afterward — `docker logs` shows "Registered tunnel connection" with no errors, and `curl https://hikes.jctnet.com/` still returns 200.

**Folded into the same 2026-09-02 M8 maintenance window as CARD-0238, at Joseph's request, rather than waiting.** Pulled and recreated cleanly — `docker compose up -d cloudflared` also recreated `hike-izer-web` (same compose project, expected). Verified live: `curl https://hikes.jctnet.com/` returned 200 both immediately after the update and again after the M8's reboot; `hike-izer-cloudflared` shows healthy/running in `docker ps` post-reboot alongside all 8 other containers.

**Done when:** updated and verified live (tunnel reconnects cleanly, site still reachable) — **met**.

**Related:** `components/hike-izer-web/README.md` (the Cloudflare Tunnel setup this updates), CARD-0227 (the idea-image feature this tunnel now also serves), CARD-0233/CARD-0236/CARD-0238 (the same 2026-09-02 M8 maintenance window this was folded into).

---

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

### CARD-0235 · [idea] [hike-izer] BirdNET Live tracks continuous GPS during every hike — evaluate turning it off, but check the species-ID accuracy tradeoff first — RESOLVED 2026-09-02
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-09-10 (CARD-0193) — 13601B, over the 5000B size threshold.

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

Archived to `tos/CLAUDE.md` on 2026-09-10 (CARD-0193) — 12511B, over the 5000B size threshold.

---

### CARD-0226 · [bug] [hiking-monitor] Rapid MQTT-attributed reboot loop during hike-data replay -- trigger unconfirmed, replay path not robust to it
**Status:** Build

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

**Kept open independent of CARD-0259 (hiking-monitor v2), 2026-09-10 — Joseph's call.** This is the actual motivating problem behind v2, but worth continuing to chase root cause on the current hardware in parallel, in case it turns out fixable without a full rebuild — not automatically superseded by v2's longer timeline.

**Related:** CARD-0221 (Environmental Data coverage gap this reboot loop most likely caused), CARD-0222 (GPS correlation failure, very plausibly the same root cause), CARD-0205 (air-quality-monitor's debug UART — the setup mistakenly assumed portable to this device; see the correction above), CARD-0211 (the earlier, already-fixed task-watchdog crash during this same replay loop -- confirmed not a recurrence, but the closest prior precedent), CARD-0217 (the earlier ~270-reboot brownout storm -- same symptom shape, different and already-distinguished reset-reason signature; folded into CARD-0259), CARD-0180 (the restart button ruled out as this incident's trigger), CARD-0215 (the duplicate-reading rejection guard relevant to disentangling real loss vs. deduped resends), CARD-0259 (hiking-monitor v2 — the eventual resolution path if this never gets root-caused on current hardware), `components/hiking-monitor/wiring.md` (Debug UART — Not Wired On This Device, the authoritative home for that fact), `components/hiking-monitor/hiking-monitor.yaml`.

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

**Raised 2026-08-23 07:27 MST (corrected 2026-09-22 — written `14:27`, 7h fast via the `TZ=` clock bug, see CARD-0329) (Joseph), broken out from CARD-0200's "proper fix" note.** CARD-0200 fixed the low-battery cutoff's immediate bug (gating it on `dock_detect`, which solar shares with USB, rather than real charging state) with a cheap firmware-only patch. The properly-designed fix — a real `solar_v` ADC reading compared against `battery_v` (`solar_v > battery_v + ~0.3V` = actually charging) — was already fully specified by **CARD-0017** (marked Done, 2026-06-15), but only the Sheets/Apps Script half of that card was ever built. Confirmed by grep: no `solar_v` sensor exists anywhere in `hiking-monitor.yaml`, and `power-system.md` documents no voltage divider on the solar panel's own output — only `battery_v` (via `BAT+`) and the digital-ish `dock_detect` divider exist today.

**Confirmed, per Joseph's question this same session: yes, this is a version-2/perfboard-rewiring item, not a firmware-only fix.** Populating `solar_v` for real requires a *new* physical voltage divider circuit — tapping the panel's raw output (or the TP4056 `IN+` line) through a new resistor pair into a spare ADC-capable GPIO — which means opening the already-assembled, field-proven perfboard. That's the same category of cost CARD-0070 (LDO swap) and CARD-0201 (sleep rearchitecture, if it turns out to need rewiring) are being deliberately kept out of this build pass for. Filed in **Defer**, matching CARD-0070's precedent, not Backlog — this isn't next-in-line work, it's a deliberately-parked future hardware pass.

**Scope, if/when revisited:** design and add a new resistor-divider circuit from the solar panel's `IN+` line to a spare ADC GPIO (GPIO33 or another unused pin — check `ESP32-project-pins.md` for what's actually free), add a corresponding `sensor: platform: adc` block in `hiking-monitor.yaml` publishing `solar_v`, and replace CARD-0200's `in_field_mode`-gated cutoff condition with the real `solar_v > battery_v + 0.3V` check CARD-0017 already designed. Natural pairing with CARD-0070 and/or CARD-0201 if either of those also ends up requiring the perfboard opened — one physical rework session covering all pending hardware changes, rather than three separate teardowns.

**Folded into CARD-0259 (hiking-monitor v2), closed 2026-09-10 — this card's own "version-2/perfboard-rewiring item" framing turned out to name the actual eventual card before it existed.** No longer a deferred hypothetical pairing with CARD-0070 — CARD-0259 is that v2 rebuild, now formally opened, and this design (the `solar_v` divider + real `solar_v > battery_v + 0.3V` comparison) rolls into its power redesign directly.

**Related:** CARD-0200 (the cheap patch this would properly replace), CARD-0017 (the schema/comparison-logic design this reuses, marked Done but only half-built), CARD-0070 (the "v2 rebuild" precedent this named before CARD-0259 existed — both folded together), CARD-0201 (folded into CARD-0259 alongside this), CARD-0259 (hiking-monitor v2 — where this actually gets built), `components/hiking-monitor/power-system.md`, `components/hiking-monitor/ESP32-project-pins.md`.

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

**Raised 2026-08-23 07:16 MST (corrected 2026-09-22 — written `14:16`, 7h fast via the `TZ=` clock bug, see CARD-0329) (Joseph), found during a discussion of how connecting the SUNYIMA solar panel affects hiking-monitor's firmware.** The 3.4V low-battery cutoff (`hiking-monitor.yaml`, the 2-min interval lambda) was gated on `!id(dock_detect).state` — but solar wires into the same `IN+`/`IN-` pads as USB (`power-system.md:17,24-25,138-139`), so `dock_detect` goes HIGH identically whether it's a stable USB charger or a ~55-80mA solar panel in variable field conditions. Net effect: **connecting solar while actively hiking silently disables the one safety net protecting the LiPo from over-discharge**, with no check on whether the panel is actually outpacing drain.

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

### CARD-0193 · [idea] [tos] Kanban board scaling strategy — RESOLVED 2026-08-22 20:17 MST
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-08-22 (CARD-0193) — 17933B, over the 5000B size threshold.

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

### CARD-0160 · [enhancement] [m8] Container image updates: cloudflared: 2026.8.2 available (running 2026.7.3) — auto-opened from photo-server — RESOLVED 2026-08-14 07:39 MST
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

### CARD-0131 · [enhancement] [photo-server] Immich update available: v3.1.0 (currently running v3.0.1) — auto-opened from photo-server
**Status:** Done

**Auto-generated 2026-07-31 23:01 UTC from photo-server's maintenance check.** Raw finding: Immich update available: v3.1.0 (currently running v3.0.1).

**Scoped 2026-08-01 — release notes reviewed before deciding, not just applied blindly.** Pulled the real release bodies via the GitHub API (not an AI-summarized fetch — an earlier WebFetch attempt got the release years wrong, 2024 instead of 2026, so it wasn't trusted) for v3.0.2, v3.0.3, and v3.1.0 (the three releases between the running version and the target). Only breaking change across all three: v3.1.0 drops iOS 14 support on the *mobile app* — irrelevant to the server. No database migration or schema change mentioned in any of the three. v3.0.2 added a fix wrapping migrations in a transaction (a safety improvement, not a new required step); v3.0.3 noted a narrow, self-healing Live Photos thumbnail caveat (fixed by the nightly job). Nothing resembling the CARD-0037/0042/0043-era bugs `operations.md` warns Immich has shipped before. Judged low-risk enough to do remotely, same reasoning as CARD-0095's M8 reboot (which was also done remotely without incident) — unlike the Pi's CARD-0129, an Immich container update never touches host networking/SSH/Tailscale, so remote access isn't at stake regardless of outcome.

**Built and verified live, 2026-08-01:** pre-checked all four containers healthy on v3.0.1 (`docker compose ps`, `/api/server/version`) before touching anything. `docker compose pull && docker compose up -d` in `~/immich-app` — only `immich-server` and `immich-machine-learning` recreated (Postgres/Valkey stay pinned by digest per this repo's own convention, untouched). Both back to `healthy` within ~1 minute. `/api/server/version` confirmed `3.1.0`. `immich-server` startup log clean — no errors/warnings, "Adding 3.1.0 to upgrade history," Nest application started successfully. Re-ran `immich-update-check.py` afterward: reports "Up to date: v3.1.0" and correctly re-published the retained pending-update state as `pending=False` — confirmed via CARD-0132's own mechanism, closing the loop between the two cards.

**Related:** CARD-0132 (the Pending Update mechanism this verifies), `components/photo-server/operations.md` (Immich update-check pattern, notify-only policy and its rationale), live dashboard entry at time of generation.

---

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

**Priority:** Backlog, low — not blocking CARD-0093, which proceeds with full jctnet.com teardown (including the Google Sites CNAME/TXT records and the root A/parking records) regardless of when this is picked up. Google Sites keeps serving the content at its native URL in the meantime, so there's no hard deadline to act before CARD-0093 executes.

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

**Closed 2026-09-12 — no longer a problem, especially when the SmartThings/HA integration is working, or refreshed if it isn't.** This matches the already-documented, generic pattern in root `CLAUDE.md`'s "Post-update entity-availability check" (and CARD-0240's own precedent): a SmartThings config entry can report `state: loaded` without actually having resynced its entities — including, presumably, the vswitch state the "presence on" lights routine depends on — and a manual `POST /api/config/config_entries/entry/<id>/reload` clears it. The intermittent "lights sometimes don't come on" symptom is consistent with this known sync-staleness class of issue rather than a distinct routine-logic bug worth auditing separately. The original audit plan (capture the undocumented SmartThings "presence on" routine, correlate HA/ST history on a real failure) is no longer needed — reload-when-it-happens is the accepted fix.

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

### CARD-0093 · [enhancement] [network] Clean up DNS records on both `jctnet.com` and `jctnet.net` — RESOLVED 2026-07-27
**Status:** Done

Archived to `tos/kanban-archive.md` on 2026-08-22 (CARD-0193) — 8063B, over the 5000B size threshold.

---

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

### CARD-0034 · [idea] [logseq] Complete digital-identity-protection-checklist.md — RESOLVED 2026-07-17
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

### CARD-0061 · [enhancement] [pi1] Add Docker health check for the Pi's Home Assistant container &mdash; RESOLVED 2026-07-12
**Status:** Done

**Notes:** Found 2026-07-12 during a Pi health evaluation. The `homeassistant` Docker container had no configured `HEALTHCHECK` &mdash; `docker ps`/`docker inspect` only reflected process liveness, not actual HA responsiveness. Same class of blind spot already found and fixed on photo-server (CARD-0032/CARD-0046: Docker's own health check only pings the API, doesn't verify real functionality) &mdash; HA is arguably the single most critical container on the Pi, since it's the sole bridge to SmartThings/Google Home for the whole house.

**Resolution:** added a `healthcheck` block to `core/homeassistant/docker-compose.yml`: `curl -f http://localhost:8123/manifest.json` (lightweight, unauthenticated, confirmed working) every 60s, 10s timeout, 3 retries, 90s start period to cover HA's own boot time. Deployed to the Pi (`/home/pi/docker-compose.yml`) and recreated the container &mdash; the existing `homeassistant` container predated this compose project (no compose labels), so it had to be stopped and removed before `docker compose up -d` would take over management of it; HA's actual config lives in the bind-mounted `/home/pi/homeassistant` volume, not the container, so nothing was lost.

**Live-tested 2026-07-12** using the same deliberately-break-it discipline as CARD-0029/CARD-0032/CARD-0046: confirmed `(healthy)` immediately after recreation, then froze HA's actual process inside the container (`kill -STOP` on the main `python3 -m homeassistant` PID &mdash; a genuine hang, not a container-level action, since that's exactly the failure mode this card exists to catch) and waited for the check to notice. Docker correctly flagged `unhealthy` with `FailingStreak: 3` after three consecutive failed checks. Resumed the process (`kill -CONT`); Docker correctly returned to `(healthy)`. Full Docker-level cycle (healthy &rarr; unhealthy on real hang &rarr; healthy again) verified end to end.

**Dashboard-visibility gap found and closed (2026-07-12):** the Docker-level fix alone only fixed `docker ps`/`docker inspect` locally on the Pi &mdash; it did not surface anything on the JCTsh log dashboard, unlike the photo-server pattern this card was modeled on, which pairs a health check with a heartbeat script that publishes the result to MQTT. Built `core/homeassistant/pi-heartbeat.py`, checking `docker inspect homeassistant`'s health status and publishing to the existing `jctsh/core/log-server/log` topic under the `jctsh-core` component identity (same identity/topic/credentials already used by the Pi's boot/reboot notifications &mdash; `/etc/jctsh/log-server.env`, reused rather than a new dedicated MQTT account, since this is the same host's own infrastructure). Deployed via `core/maintenance/pi-heartbeat.service`/`.timer` (30 min, matching the fleet-wide heartbeat cadence). Hit one real bug during first deploy: initially built the topic from the component variable (`jctsh/core/jctsh-core/log`) instead of the fixed `jctsh/core/log-server/log` topic the log server actually expects &mdash; component name and topic segment are decoupled in this convention and are easy to conflate; fixed and redeployed.

**End-to-end live-tested 2026-07-12:** repeated the freeze/resume test with the heartbeat script run manually at each stage, confirmed via the dashboard's actual `/data` endpoint (not the flushed-only `/log` text file, which delayed visibility of the healthy-state message inside an unflushed collapse group during testing and briefly looked like a bug before being traced to normal flush-timing behavior, not a real defect) &mdash; healthy (`System`, `Heartbeat - Docker containers healthy.`) &rarr; unhealthy (`Alert`, `Docker degraded - homeassistant:unhealthy`, visible immediately since Alert messages don't collapse) &rarr; healthy again, all three states confirmed present and correctly categorized on the live dashboard.

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

**Notes:** Raised 2026-07-12. Motivated by the router (TP-Link Archer AXE75) listing most connected devices with meaningless names, with no built-in way to rename them — the JCTsh-managed fleet already has this solved via DHCP reservations + `network/jctsh-network.md`'s device table + ESPHome hostnames, but third-party/commercial devices (Ring, Ecobee, Cast devices, guest phones) aren't part of that convention and the router won't let their names be overridden.

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

### CARD-0056 · [enhancement] [tos] Persistent visual kanban board — RESOLVED 2026-07-11
**Status:** Done

**Notes:** Raised 2026-07-11: every time the board gets summarized in chat, it comes out in a different ad hoc format and scrolls out of view while working, with no stable place to return to it. Agreed approach: a browser-hosted Artifact with a persistent URL, redeployed to the same link whenever `kanban-board.md` changes, rather than a fresh chat message each time.

Built as a single self-contained HTML page (no external requests, per the Artifact sandbox) — a blueprint-styled board with one column per kanban state (Backlog, Planning, Design, Build, Done, Defer), each independently scrollable and collapsible, card tiles that expand in place for full notes, a live text search across id/title/tag/notes, and type filter chips (bug/enhancement/idea). Card data is baked into the page at build time as a JSON blob, not read live from the repo — so it goes stale exactly the way any snapshot does, and needs a manual regenerate-and-republish pass after edits, same discipline as keeping any other doc in sync.

`backlog.md` was renamed to `kanban-board.md` in this same session (2026-07-11), with references updated across README.md, CLAUDE.md, JCTsh-Operating-System.md, and the photo-server docs that pointed to it by name.

**Live-parsing alternative considered, not pursued (2026-07-11):** discussed serving the board from the Pi's existing `log_server.py` with a route that parses `kanban-board.md` live on each request instead of reading baked-in JSON, which would remove the manual-regenerate step entirely. Real cost surfaced in the same discussion: the repo isn't cloned on the Pi (deploys there are one-off `scp`, per `SOFTWARE-ENVIRONMENT.md`), so `kanban-board.md` would still need to be pushed to the Pi on every edit — the live-parsing win only fully lands once that push is also automated. Decision: stick with the manual artifact-regenerate workflow for now and see how the discipline holds up in practice; revisit the Pi version if manual regeneration turns out to be too easy to forget.

**Resolution:** page published and confirmed viewable at a stable claude.ai URL. Regenerate-after-edit discipline exercised twice already (title/collapse-default fix, then a CARD-0056 text sync) and explicitly agreed to as the ongoing approach. Closed 2026-07-11 — Joseph confirmed sticking with this version and directed the commit.

---

### CARD-0052 · [idea] [tos] JCTsh Team Operating System (TOS) — RESOLVED 2026-07-11
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

### CARD-0036 · [enhancement] [architecture] Dashboard visibility for scheduled reboots
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

**Resolution:** Added `/status` endpoint to `core/logging/log_server.py`. Two-section layout: Home (Online/Offline/? per component based on heartbeat presence and 70-min threshold) and Remote (`coachproxyos` always shows last-activity + `?`). Auto-detects heartbeat-capable components — salt-sensor shows `?` until CARD-0004 ESPHome migration adds heartbeats. Deployed to Pi 2026-06-30. Added CARD-0024 (coachproxy remote health monitoring via Tailscale ping).

---

### CARD-0018 · [idea] [photo-server] Self-hosted photo library
**Status:** Done

**Resolution:** Superseded. Hardware (GMKtec M8) in hand. Replaced by `components/photo-server/` (Immich install + immich-go migration) and `components/photo-tv-display/` (Node.js TV slideshow + phone companion) — full planning docs committed 2026-06-30.

---

### CARD-0014 · [enhancement] [data-pipeline] Move environmental data pipeline to core
**Status:** Done

**Resolution:** Moved `environmental-data.gs` → `core/data-pipeline/`, `JCTsh-Environmental-Data-Architecture.md` → `core/data-pipeline/`, and `core/node-red/environmental-data.flow.json` → `core/data-pipeline/`. Updated references across 15 files (CLAUDE.md, README.md, Node-RED-workflow.md, JCTsh-Build-Standards.md, JCTsh-Component-Planning-Pattern.md, JCTsh-Property-Sensor-Pattern.md, all component planning docs, hiking-monitor instructions). 2026-06-30.

---

### CARD-0002 · [enhancement] [mqtt] MQTT v3.1.1 → v5 upgrade
**Status:** Done

**Resolution:** Mosquitto 2.0.21 already supports v5 — no broker config change needed. Changed `protocolVersion` from 4 → 5 in the Node-RED broker config node (`core/node-red/core.flow.json`) and updated the live Pi flows.json in place. Confirmed via Mosquitto log: client `nodered-saltlevel` connected with `p5`. ESP32/ESPHome devices unaffected (remain on v3.1.1). 2026-06-30.

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

### CARD-0027 · [idea] [hiking-monitor] GPIO-controlled power gating for I2C peripherals during sleep — SUPERSEDED by CARD-0259
**Status:** Defer

**Superseded 2026-07-17 by CARD-0070, then again 2026-09-10 by CARD-0259** — folded into CARD-0070 (LDO swap) first, which covered both the boost-to-LDO replacement and this card's peripheral power-gating idea as one combined power redesign; CARD-0070 itself has now closed and folded into CARD-0259 (hiking-monitor v2), which adopts air-quality-monitor's own power architecture (no P-FET gate needed at all — see that card). Kept here for the original observation and P-FET background reference.

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

