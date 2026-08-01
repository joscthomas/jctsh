# JCTsh Backlog

Lightweight kanban. Each card has a **type** (idea | enhancement | bug) and a unique ID.

**Columns:** Backlog → Planning → Build → Done, plus **Defer** (off to the side — reachable from any stage)
- **Backlog** — captured, not yet being worked on
- **Planning** — being scoped/interviewed, and (if non-trivial) an implementation plan written — no separate Design checkpoint; the plan itself is the design artifact
- **Build** — going through the plan/implementation, including testing
- **Done** — complete
- **Defer** — a deliberate decision not to pursue for now (not abandoned, not forgotten — just consciously parked); can move here from any other column

<!-- next-card-id: CARD-0133 -->

---

### CARD-XXX · [enhancement] [infrastructure] M8 maintenance: 2 firmware update(s) available: KEK CA: UEFI Secure Boot Key … — auto-opened from photo-server
**Status:** Backlog

**Auto-generated 2026-08-01 14:00 UTC from photo-server's maintenance check.** Raw finding: M8 maintenance: 2 firmware update(s) available: KEK CA: UEFI Secure Boot Key Exchange Key; KEK CA: UEFI Secure Boot Key Exchange Key. Needs a human/Claude interview pass to scope real acceptance criteria — this stub only captures that something was found, not what "done" looks like.

**Related:** live dashboard entry at time of generation.

---

### CARD-0132 · [enhancement] [infrastructure] Extend CARD-0127's retained Pending-Update state to the generic container-image checker (HA, NetAlertX, Caddy, cloudflared)
**Status:** Done

**Raised 2026-08-01**, from Joseph noticing the `/status` Device Status page looked inconsistent: `jctsh-core` had logged "Container image updates: home-assistant: 2026.7.4 available (running 2026.5.1)" 14h ago, but its Pending Update column showed `—`, while `photo-server` correctly showed `immich: v3.1.0 available` in the same column for its own real pending update.

**Root cause, confirmed by code reading:** CARD-0127 built the retained-MQTT "Pending Update" mechanism (`jctsh/<type>/<component>/pending-update/<item>`, consumed by `log_server.py`'s `_pending_updates` dict) but scoped its Build pass to `immich-update-check.py` only — explicitly noted at the time as "worth deciding at Build time whether this pattern should extend to the M8 maintenance check and its Pi sibling too... not yet raised as a complaint the way Immich's was." CARD-0126 then shipped the generic container-image checker (`core/maintenance/container_update_check.py`, wrapped by `core/homeassistant/container-update-check.py` for Home Assistant and `components/photo-server/container-update-check.py` for NetAlertX/Caddy/cloudflared) the same day, but it only ever publishes the throttled log-dashboard notification — it never got the retained-state publish CARD-0127 added for Immich. So every service checked by the generic checker (home-assistant, netalertx, caddy, cloudflared) permanently shows `—` in Pending Update regardless of actual state, while only Immich (the one bespoke script) reflects reality. Not a dashboard bug — a real, reproducible gap between two otherwise-parallel checkers.

**Design — mirrors CARD-0127's Immich implementation exactly, applied to the shared module instead of a one-off script:**
1. `core/maintenance/container_update_check.py`'s `check_services()` gains a third return value, `pending_updates`: `{service_name: {"pending": bool, "current": str, "latest": str}}`, populated for every service where a current/latest version was actually determined (skipped for services whose check raised an exception — no real data to publish in that case), computed and returned unconditionally — independent of the existing 7-day notification throttle, same separation of concerns as Immich's own script (retained state always current; the throttled log message is a separate, secondary signal).
2. Both wrapper scripts publish one retained (`retain=True`, `qos=1`) MQTT message per entry in `pending_updates`, every run, regardless of whether `findings` is empty — topic `jctsh/core/jctsh-core/pending-update/home-assistant` for the HA wrapper (matching `jctsh-core`'s existing component name so it lands on the right dashboard row), `jctsh/server/photo-server/pending-update/{netalertx,caddy,cloudflared}` for the M8 wrapper (parallel to Immich's own `jctsh/server/photo-server/pending-update/immich`). Payload shape identical to Immich's: `{"pending": bool, "current": "...", "latest": "..."}`.
3. `core/homeassistant/container-update-check.py` uses `mosquitto_pub` (subprocess), not paho — needs `-r -q 1` added per publish call, not a client-object change like the M8 side.
4. No `log_server.py` changes needed — the `_pending_updates` dict, subscribe wildcard (`jctsh/+/+/pending-update/+`), and dashboard column are already generic per CARD-0127; this card is purely about getting the other four services to actually publish into that existing mechanism.

**Done when:** `/status` shows a correct Pending Update value for `jctsh-core` (currently a real, outstanding home-assistant update) without needing another unrelated log message to appear stale-but-still-shown. Verified live: both wrapper scripts run for real, retained state confirmed via a fresh dashboard load; the "unaffected by later unrelated log messages" check CARD-0127 used for Immich repeated here for at least `jctsh-core`; up-to-date services (netalertx, caddy, cloudflared, if none pending at test time) confirmed explicit `—`/`pending: false` rather than silently absent.

**Built and verified live, 2026-08-01:**
- `core/maintenance/container_update_check.py`'s `check_services()` now returns a third value, `pending_updates` — `{service_name: {"pending", "current", "latest"}}` for every service whose current/latest was actually determined, unconditionally, separate from the throttled `findings` list.
- Both wrapper scripts (`core/homeassistant/container-update-check.py` via `mosquitto_pub -r -q 1`, `components/photo-server/container-update-check.py` via paho `publish(..., qos=1, retain=True)`) now publish one retained message per service every run, regardless of whether `findings` is empty. Topics: `jctsh/core/jctsh-core/pending-update/home-assistant` (Pi) and `jctsh/server/photo-server/pending-update/{netalertx,caddy,cloudflared}` (M8), parallel to Immich's own `.../pending-update/immich`.
- Deployed to both hosts (`/usr/local/bin/container_update_check.py` + `/usr/local/bin/container-update-check.py`, root-owned, matching existing deployment convention) and run live, not just edited-and-assumed:
  - **Pi**: `mosquitto_sub` confirmed `jctsh/core/jctsh-core/pending-update/home-assistant {"pending": true, "current": "2026.5.1", "latest": "2026.7.4"}` retained and correct. `/status` re-fetched live — `jctsh-core`'s Pending Update column now reads `home-assistant: 2026.7.4 available`, the exact gap Joseph flagged, now closed.
  - **M8**: all four services confirmed publishing correctly — `immich` (`pending: true`, unchanged from CARD-0127), `netalertx`/`caddy`/`cloudflared` all genuinely up to date (`pending: false`, explicit rather than absent) at test time — so `netalertx`'s `/status` row still shows `—`, but now because the retained state is really `false`, not because nothing was ever published.
  - M8 deployment needed `jct`'s sudo password (M8's `sudo` isn't passwordless the way the Pi's is) — retrieved from `credentials.local.md` with Joseph's go-ahead, used only for the one deploy command, not stored anywhere new.

**Related:** CARD-0127 (the mechanism this extends, built for Immich only), CARD-0126 (the generic checker this card retrofits), CARD-0130 (the still-open home-assistant finding this fixes visibility for).

---

### CARD-0131 · [enhancement] [infrastructure] Immich update available: v3.1.0 (currently running v3.0.1) — auto-opened from photo-server
**Status:** Done

**Auto-generated 2026-07-31 23:01 UTC from photo-server's maintenance check.** Raw finding: Immich update available: v3.1.0 (currently running v3.0.1).

**Scoped 2026-08-01 — release notes reviewed before deciding, not just applied blindly.** Pulled the real release bodies via the GitHub API (not an AI-summarized fetch — an earlier WebFetch attempt got the release years wrong, 2024 instead of 2026, so it wasn't trusted) for v3.0.2, v3.0.3, and v3.1.0 (the three releases between the running version and the target). Only breaking change across all three: v3.1.0 drops iOS 14 support on the *mobile app* — irrelevant to the server. No database migration or schema change mentioned in any of the three. v3.0.2 added a fix wrapping migrations in a transaction (a safety improvement, not a new required step); v3.0.3 noted a narrow, self-healing Live Photos thumbnail caveat (fixed by the nightly job). Nothing resembling the CARD-0037/0042/0043-era bugs `operations.md` warns Immich has shipped before. Judged low-risk enough to do remotely, same reasoning as CARD-0095's M8 reboot (which was also done remotely without incident) — unlike the Pi's CARD-0129, an Immich container update never touches host networking/SSH/Tailscale, so remote access isn't at stake regardless of outcome.

**Built and verified live, 2026-08-01:** pre-checked all four containers healthy on v3.0.1 (`docker compose ps`, `/api/server/version`) before touching anything. `docker compose pull && docker compose up -d` in `~/immich-app` — only `immich-server` and `immich-machine-learning` recreated (Postgres/Valkey stay pinned by digest per this repo's own convention, untouched). Both back to `healthy` within ~1 minute. `/api/server/version` confirmed `3.1.0`. `immich-server` startup log clean — no errors/warnings, "Adding 3.1.0 to upgrade history," Nest application started successfully. Re-ran `immich-update-check.py` afterward: reports "Up to date: v3.1.0" and correctly re-published the retained pending-update state as `pending=False` — confirmed via CARD-0132's own mechanism, closing the loop between the two cards.

**Related:** CARD-0132 (the Pending Update mechanism this verifies), `components/photo-server/operations.md` (Immich update-check pattern, notify-only policy and its rationale), live dashboard entry at time of generation.

---

### CARD-0130 · [enhancement] [infrastructure] Container image updates: home-assistant: 2026.7.4 available (running 2026.5.1) — auto-opened from jctsh-core
**Status:** Backlog

**Auto-generated 2026-07-31 22:52 UTC from jctsh-core's maintenance check.** Raw finding: Container image updates: home-assistant: 2026.7.4 available (running 2026.5.1). Needs a human/Claude interview pass to scope real acceptance criteria — this stub only captures that something was found, not what "done" looks like.

**Related:** live dashboard entry at time of generation.

---

### CARD-0129 · [enhancement] [infrastructure] Apply Pi's remaining Docker/kernel packages and reboot — waiting until Joseph is home
**Status:** Build

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

**Related:** CARD-0125 (the check that surfaced this and applied the routine batch), CARD-0095 (the M8 sibling — this is the exact sequence already proven there tonight, just not yet safe to run remotely on the Pi), CARD-0096 (the precedent for the "wait until home" block and its reasoning).

---

### CARD-0128 · [enhancement] [infrastructure] Maintenance findings auto-open a PR against kanban-board.md instead of just logging an Alert
**Status:** Done

**Notes:** Raised 2026-07-31, from a conversation about whether maintenance-check findings (CARD-0095, CARD-0125) should do more than post a log-dashboard Alert — Joseph wants a real finding to land in the actual work queue (`kanban-board.md`), not just a status flag someone has to notice and manually turn into a card.

**The trust boundary this crosses, and why it needs its own card rather than a quick script tweak:** today, *nothing* writes to `kanban-board.md` except Claude, with Joseph's explicit go-ahead on every commit and push — a rule held all session. Making a maintenance-check script open cards automatically means giving an unattended cron job on the M8/Pi real git credentials, with no human in the loop at the moment it acts. Three options discussed, in increasing order of autonomy granted:
1. **Open a GitHub Issue instead of a kanban card** — separate queue/audit trail from the kanban board itself, but a much narrower credential (issue-create only) and no `main`-write risk at all. Downside: fragments tracking across two systems instead of one.
2. **Commit directly to `kanban-board.md` on `main`** — closest to "just add a card," but means a fully unattended process editing the same file every other card in this repo treats as human/Claude-reviewed territory, with a git push credential sitting in a file on a production box.
3. **Commit to a branch, open a PR, human/Claude merges it** — preferred direction discussed. The script's credential is scoped to "push branches and open PRs" only; a GitHub branch-protection rule on `main` (require PR review before merge) makes it *structurally* incapable of touching `main` directly, not just "trusted" not to. A PR sitting open is still a real, visible, queued item — better than a log line — without changing who's actually allowed to modify `main`.

**Scope, if built per option 3:**
- Maintenance-check scripts (`components/photo-server/maintenance-check.py`, `core/maintenance/pi-maintenance-check.py`) gain a narrowly-scoped GitHub credential (fine-grained PAT: contents write on a branch, pull-request create — explicitly not a broad/classic token) and `git`/`gh` availability on both hosts.
- On a finding, the script creates a branch (e.g. `maintenance-alert/m8-YYYY-MM-DD`), writes/updates a card in `kanban-board.md` (needs a template — see open question below), commits, pushes, and opens a PR via `gh pr create`.
- **`main` gets a GitHub branch-protection rule requiring PR review before merge** — the actual enforcement mechanism, not just a credential-scoping promise.
- Existing Alert/log-dashboard notification stays as-is alongside this — the PR is the queue item, the Alert is still the "something happened right now" signal.

**Open questions, resolved 2026-07-31 14:50 MST (Planning):**

1. **Card shape: a deliberately minimal stub, not hand-written-quality prose.** Auto-generating CARD-0095/CARD-0124-quality writeups from a script isn't realistic — that quality comes from an actual interview, which is the whole point of the "someone still has to flesh this out" step. Template:
   ```
   ### CARD-XXXX · [enhancement] [infrastructure] <first line of finding> — auto-opened from <component>
   **Status:** Backlog

   **Auto-generated <date> <time> <tz> from <component>'s maintenance check.** Raw finding: <message text verbatim>. Needs a human/Claude interview pass to scope real acceptance criteria — this stub only captures that something was found, not what "done" looks like.

   **Related:** `<script path>`, live dashboard entry at time of generation.
   ```
   Rendered in the exact same `### CARD-XXXX` / `**Status:**` format every hand-written card uses, so `/kanban` groups and displays it identically — just visibly marked as a stub via its own content, not a different structural format.

2. **Dedup — simpler than originally scoped, and doesn't actually need CARD-0127 as a prerequisite** (correcting the relationship note below, written before working through the mechanics): the maintenance-check scripts already maintain a fingerprint-keyed state file for their Alert throttle (`{fingerprint, notified_at}` — CARD-0095/CARD-0125). Extending that same state file with a `pr_number` field solves this directly: before opening a new PR, check whether the current fingerprint matches the stored one *and* the stored PR is still open (`gh pr view <number> --json state`); if so, do nothing — the existing PR already represents this finding. Only open a new PR when the fingerprint changed or the old PR was closed/merged. This is a same-process, sequential-runs question ("did I already open a PR for this"), not a cross-process "what's the current true state" question — CARD-0127's retained-MQTT mechanism solves the latter, for a different consumer (the dashboard), and isn't actually load-bearing here despite the earlier note below suggesting otherwise.

3. **Who merges — the same pattern as everything else tonight, not a new one.** Not "always a human clicking merge on GitHub," and not "Claude auto-merges unprompted" either — the PR sits open until asked about, same as every commit/push this session waited for an explicit go-ahead. In practice: `gh pr merge` run by Claude, during a normal session, when Joseph asks — the PR's real value is the audit trail and the branch-protection enforcement, not forcing a specific human-only UI action.

**Relationship to CARD-0127, discussed 2026-07-31, refined 2026-07-31 14:50 MST:** still complementary, not competing — different destinations for the same underlying finding (CARD-0127: operational visibility, "pending right now" on `/status`; this card: work-queue visibility, a trackable backlog item). That framing holds. The earlier claim that CARD-0127 should be built first as a prerequisite for this card's dedup logic **does not hold up** once actually scoped (see point 2 above) — the existing per-script state file already answers it, no cross-card dependency needed. Both cards can ship independently, in either order.

**Concrete design for Build (option 3 from above):**
- **PAT scope**: fine-grained, repo-limited to `jctsh`, permissions `Contents: Read and write` + `Pull requests: Read and write` only — explicitly not a classic token, not `admin` or org-wide scope.
- **Branch naming**: `maintenance-alert/<component>-<date>` (e.g. `maintenance-alert/photo-server-2026-08-01`), one branch per opened PR.
- **Flow**: `git checkout -b <branch>` → write/append the stub card via the same next-card-id-marker convention every manual card uses → `git commit` → `git push -u origin <branch>` → `gh pr create --title "..." --body "..."`.
- **Branch protection on `main`**: GitHub Settings → Branches → require PR review before merge — the actual enforcement, not just the PAT's scope being narrow.

**Built and verified live, 2026-07-31 15:10 MST — a real PR opened, not a synthetic test:**
- New `core/maintenance/open_kanban_pr.py`, a shared module (deployed to `/usr/local/bin/` on both hosts, imported by both `maintenance-check.py` and `pi-maintenance-check.py`) — pure GitHub REST API via stdlib `urllib.request`, no `gh` CLI or local git clone needed on either host (this session's own git access turned out to be plain `git push`, no `gh` installed anywhere, so there was nothing to reuse anyway). Creates a branch ref, updates `kanban-board.md` via the Contents API (which creates a commit on that branch), opens the PR.
- Dedup implemented exactly as scoped in point 2 above — extends each script's existing throttle-state file with `pr_fingerprint`/`pr_number`, checks the PR's still-open state via the API before deciding whether to open a new one.
- Wired into both scripts behind a soft dependency: `GITHUB_ENV` (`/etc/jctsh/github.env`) is read inside a `try`/`except FileNotFoundError`, so deploying this code was itself a no-op right up until the PAT existed — the existing Alert-notification path was never at risk of breaking because of an unfinished CARD-0128 dependency.
- Fine-grained PAT created (repo-limited to `jctsh`, `Contents` + `Pull requests` read/write only, no `Administration`), deployed to `/etc/jctsh/github.env` (mode 600, root-owned) on both hosts.
- **Live test on the Pi** (a genuine finding — 7 Docker packages + reboot required, not synthetic): first run opened **[PR #1](https://github.com/joscthomas/jctsh/pull/1)**, confirmed via the API to contain a correctly-formatted `CARD-0130` stub (right template, right `next-card-id` bump, matches every hand-written card's structure) in a real diff. Forced a second run past the Alert-throttle (backdated `notified_at` in the state file, same fingerprint) specifically to test the dedup path in isolation — correctly recognized the still-open PR and did **not** open a duplicate, confirmed via the API that only PR #1 exists.
- **Branch protection on `main` — done and confirmed active, 2026-07-31 15:30 MST.** Joseph added the rule via the web UI (one real gotcha: the "Require approvals" sub-checkbox has to stay *unchecked* for zero required reviewers — its number stepper only appears, and only allows 1+, once that sub-checkbox is on; there's no way to type "0" into it directly). Confirmed genuinely active by an unplanned real test: pushing tonight's own CARD-0128 commit directly to `main` (this session's normal git workflow all night) succeeded, but GitHub's own response included `Bypassed rule violations for refs/heads/main: - Changes must be made through a pull request` — proof the rule correctly flagged the push as a violation, and that repo owners/admins get a default bypass exemption (not blocked unless "enforce for administrators" is separately enabled, which most people leave off to avoid locking themselves out). The PAT sitting on the M8/Pi is a non-admin credential with no such exemption — though its own code path never attempts a direct push to `main` in the first place (`open_kanban_pr.py` only ever creates branches and opens PRs), so this is defense-in-depth rather than something the deployed automation could trigger day to day.
- **Known limitation found and actually solved, 2026-07-31 ~15:40 MST** (the note above originally called this "not yet solved" — it now is). Joseph caught that the race was worse than first described: since `main`'s `next-card-id` marker doesn't move until a PR actually merges, opening a PR never reserves its number — two concurrent findings from *different* hosts (M8 and Pi, now scheduled an hour apart) could both read the same "next" number and open two separately-numbered-the-same PRs before either merged. Safe (a real merge conflict on that line would block the second one), but messy and not what was documented. **Fix:** `open_finding_pr()` no longer reads or writes the `next-card-id` marker at all — the stub goes in with a literal `CARD-XXX` placeholder, and the PR's diff never touches the marker line, so concurrent PRs genuinely can't collide anymore. Real number assignment moved to a new `resolve_and_merge()` function, run at actual merge time (by Claude, when asked — matching the "who merges" answer above) — it reads `main`'s marker *then*, resolves the placeholder, sets the marker correctly, pushes that as a fixup commit on the PR's own branch, then merges — so the commit that lands on `main` is already fully correct.
- **A second, real bug caught live while verifying that fix**, before it could do any damage: the obvious implementation — a blind `branch_text.replace("CARD-XXX", card_id)` — would have also corrupted this repo's own documentation. CARD-0128's card notes (this text) mention the literal phrase "CARD-XXX placeholder" several times in prose, and a global replace doesn't know the difference between the real placeholder and someone talking *about* the placeholder. Caught via a dry-test before running it for real (6 occurrences found in a live branch, only 1 of which was the actual stub); fixed by anchoring the replacement on the stub's exact, structurally-unique header pattern (`"### CARD-XXX · "`) instead of the bare substring. Verified after the fix: exactly 1 occurrence resolved, the other 5 (this very prose) left untouched.
- **Both fixes verified live**, end to end, twice — PR #2 opened cleanly with the placeholder (diff confirmed to never touch the marker line), and a dry-run of `resolve_and_merge()`'s resolution logic against it produced the correct real ID (`CARD-0130`, matching `main`'s actual current marker) without touching the surrounding prose. Not actually merged — same reasoning as PR #1, this is the identical CARD-0129 finding, so merging it would just create a duplicate. Closed and its branch deleted, same as PR #1.
- **`immich-update-check.py` wired in, 2026-07-31 ~16:00 MST** — the one script this pipeline never covered, since it predates CARD-0128 entirely and was never retrofitted. Found while explaining to Joseph why Immich's pending update (real, still outstanding — `v3.1.0` vs. running `v3.0.1`) wasn't showing up as a PR the way CARD-0126's Home Assistant finding did; the difference had nothing to do with log category (both use `System`) — Immich's script simply never called `open_finding_pr()` at all. Added the same integration used by the other four scripts.
- **Real permissions bug caught live while testing that wiring, not a code bug**: `/etc/jctsh/github.env` on the M8 was deployed `600, root-owned` — but `maintenance-check.py` and `container-update-check.py` (M8) both run as `User=jct` per their `.service` files, same as the newly-wired Immich script. `jct` couldn't read a root-only file, so the PR step would have silently failed for *every* M8-based script the moment their timers fired for real — it only looked like it worked earlier tonight because those tests all happened to run on the Pi (root by default). Fixed to `640, owner root:jct`, matching this repo's own pre-existing convention for M8 credential files (`heartbeat.env`). Verified live against the real Immich finding after the fix: **[PR #4](https://github.com/joscthomas/jctsh/pull/4)** opened correctly.
- **Merged both real PRs (#3 and #4) and found the biggest gap in `resolve_and_merge()` yet — not a rare edge case, the *ordinary* case.** Every stub inserts at the exact same fixed anchor point in the file (the intro's first `---\n\n`), so when two PRs are open at the same time, git's 3-way merge sees identical surrounding context for both and can't tell "two independent additions" from "a real conflict" — it rejects the second merge outright (`mergeable: false, dirty`), and GitHub's own `update-branch` endpoint (a real git merge, not a content diff) hit the identical wall. This isn't a corner case that might come up occasionally — it's what happens *every time* more than one finding is open for review at once, which is a completely normal state for this system to be in. **Fix:** when the normal merge call fails, `resolve_and_merge()` now falls back automatically — constructs a genuine two-parent merge commit directly via the Git Data API (parents: `main`'s current tip + the PR branch's tip, tree: the already-correct fixed-up content), points the branch at it, then merges with `merge_method="merge"` (not `squash`, which would re-diff and hit the same conflict again). No more manual intervention needed for this case. Proven live: PR #3 merged cleanly on the first attempt (nothing else was open yet); PR #4 hit the conflict for real, was resolved with this exact manual sequence first (worked), then the sequence was generalized into the function itself so the next occurrence — which, given the insertion-point design, could be as soon as the very next time two findings overlap — doesn't need a human debugging session to get through.
- **Both cards live on `main`, confirmed correct, nothing reverted**: `CARD-0130` (Home Assistant update) and `CARD-0131` (Immich update), `next-card-id` marker correctly at `CARD-0132`. Worth naming the risk that was actually in play here, not just the annoyance: the *naive* version of this fallback (blindly trusting the PR branch's full stale file content, discovered mid-session as a separate bug and already fixed earlier in this same card) would have silently reverted PR #3's already-merged card if it had gone through — the conflict, frustrating as it was, is what caught that this was even a risk. Both merged branches deleted, repo working copy pulled to sync.

**Related:** CARD-0095 (M8 maintenance check — the finding source), CARD-0125 (Pi's sibling — the other finding source), CARD-0127 (the dashboard-side sibling of this same underlying idea — see relationship note above), CARD-0057-era kanban-parsing work (`log_server.py`'s `/kanban` page, which already fetches `kanban-board.md` straight from GitHub's `main` — relevant to how quickly a merged card would actually become visible there).

---

### CARD-0127 · [enhancement] [infrastructure] Reliable "Pending Update" indicator on Device Status page (MQTT retained state, not last-message-wins)
**Status:** Done

**Notes:** Raised 2026-07-31, while explaining how `immich-update-check.py`'s notification actually surfaces. Joseph specifically cares about seeing "an Immich update is available" reliably on the `/status` Device Status page — not just the main log dashboard.

**The gap:** `/status`'s "Last Reading" column (`log_server.py`'s `_compute_status()`) shows whichever non-heartbeat message was *most recently logged* for a component — it's derived from message history, not real current state. An Immich-update-available notice would show up there today, but only until some *other* non-heartbeat event fires for `photo-server` (e.g. a CARD-0095 maintenance Alert) — at which point the update notice silently falls out of view even though the update is still genuinely available. Best-effort, not a reliable indicator. Confirmed by direct code reading (`_build_status_html()`/`_compute_status()`), not yet observed live — no real Immich update has fired during this investigation.

**Proposed design — spans both the M8 and the Pi, not a one-line fix:**
1. **`components/photo-server/immich-update-check.py`** (M8): publish its result as an **MQTT retained message** on every run — not just when the finding changes, and not just the existing non-retained log-dashboard notification it already sends. Retained messages are MQTT's own mechanism for "give me the current true value regardless of history" — exactly the property needed here. Payload: something like `{"pending_update": true/false, "version": "vX.Y.Z", "current": "vA.B.C"}`.
2. **`core/logging/log_server.py`** (Pi): subscribe to that retained topic, track it as dedicated per-component state (separate from `_last_seen`/`_entries`, which are message-history-based), and add a genuinely new **"Pending Update" column** to `_build_status_html()`'s Always-on table — sourced from that retained state directly, not from "most recent non-heartbeat message." Should read correctly immediately on log-server restart too, since retained messages redeliver on subscribe (unlike the current history-based approach, which already needed the separate `_load_state()`/`_save_state()` persistence CARD-0057-era work to survive a restart at all).
3. Worth deciding at Build time whether this same retained-state pattern should extend to the M8 maintenance check (CARD-0095) and its eventual Pi sibling (CARD-0125) too, once built — same underlying problem (a `/status` summary that's really "last thing logged," not "current true state") likely applies there as well, just not yet raised as a complaint the way Immich's was.

**Implementation plan (2026-07-31, Planning) — grounded in the real code, both files re-read in full:**

- **Topic naming fits the existing convention exactly:** `jctsh/<type>/<component>/<message-type>` already covers `.../log` and `.../heartbeat` — `jctsh/server/photo-server/pending-update` is the natural third member, no new pattern invented.
- **`immich-update-check.py` change:** after the existing `current`/`latest` comparison (unchanged), add one new MQTT publish — `retain=True`, `qos=1` — **every run, regardless of whether anything changed**, unlike the existing throttled log-dashboard notification which stays as-is alongside it. Payload: `{"component": "photo-server", "pending": true/false, "current": "vA.B.C", "latest": "vX.Y.Z"}`. Publishing `pending: false` explicitly (not just skipping the publish, and not clearing the retained message) matters — an absent/cleared retained topic is ambiguous with "never checked yet," while an explicit `false` is unambiguous.
- **`log_server.py` changes:**
  1. New module-level dict, `_pending_updates = {}` (component → last payload + receipt time), separate from `_entries`/`_last_seen` — deliberately not folded into the existing history-based structures, since mixing "current state" with "message history" is the exact bug this card exists to fix.
  2. `_on_connect`: add `jctsh/+/+/pending-update` to the existing `client.subscribe([...])` call, alongside `MQTT_TOPIC` and `_STATUS_TOPIC`.
  3. `_on_message`: new branch (parallel to the existing `/status`-topic handling) matching topics ending in `/pending-update` — parse the 4-segment topic for the component name (same `msg.topic.split("/")` pattern already used for the `/status` branch), store straight into `_pending_updates[component]`.
  4. `_build_status_html()`: new `<th>Pending Update</th>` column in the Always-on table; each row pulls from `_pending_updates.get(comp)` — `"vX.Y.Z available"` if `pending: true`, `"—"` otherwise (matching the existing `dim`-class empty-state styling already used elsewhere on that page).
- **No `_save_state()`/`_load_state()` work needed** — confirmed `core/mqtt/mosquitto.conf` has `persistence true` (survives a *broker* restart too, not just a log-server one), and `_on_connect` already re-subscribes on every reconnect, so a retained message redelivers automatically on log-server startup with zero extra persistence code. Notably simpler than the history-based approach, which needed CARD-0057-era `_load_state()`/`_save_state()` specifically to survive a restart at all.
- **Scope for this card: wire up `immich-update-check.py` only.** The mechanism (topic pattern, `_pending_updates` dict, the new column) is generic — any script publishing to `jctsh/<type>/<component>/pending-update` would show up correctly — but actually publishing from `maintenance-check.py`/`pi-maintenance-check.py` too is explicitly left for later per point 3 above, not solved in the same pass.
- **Test plan for Done-when:** `mosquitto_pub -r` a synthetic test payload to simulate a pending update → confirm it appears on `/status` immediately. Post an unrelated `photo-server` log message (e.g. trigger the maintenance check) → confirm the Pending Update column is **unaffected** — this is the exact failure mode CARD-0127 exists to fix, so it's the one check that actually matters. Restart `log_server.py` → confirm the column repopulates correctly with no gap, proving the retained-redelivery mechanism actually works and no `_save_state()` equivalent was needed. Publish `pending: false` → confirm the column correctly clears to `—`.

**Done when:** the Device Status page shows a dedicated Pending Update indicator for `photo-server` that reflects Immich's actual current update state at all times — verified by triggering a real state change (or a manual test publish) and confirming it updates immediately and correctly, and confirming it survives being superseded by an unrelated log message for the same component (the exact failure mode that doesn't work today) and a log-server restart.

**Design corrected mid-Build, 2026-07-31 — topic namespaced by item, not just by host.** Joseph caught a real collision the original design didn't account for: MQTT retains exactly one value per topic, and a bare `.../pending-update` topic keyed only by component would let two different pending-update facts about the same host (Immich's version, CARD-0095's OS-level state if that's ever extended to publish retained state too — point 3 above) silently overwrite each other. Fixed before it could bite: topic became `jctsh/server/photo-server/pending-update/immich` (item as a 5th segment); `_pending_updates` became `{component: {item: state}}` instead of `{component: state}`; the subscribe wildcard became `jctsh/+/+/pending-update/+`; and the Device Status column now joins every currently-pending item for a row (`"immich: v3.1.0 available"`, extensible to `"immich: v3.1.0 available; os: 7 pkgs need review"` if CARD-0095's script is ever wired up the same way) instead of assuming exactly one fact per host.

**Built and verified, 2026-07-31 — all four test-plan checks passed live, plus one real bug caught mid-verification:**
- `immich-update-check.py`: added the retained publish alongside the existing throttled notification logic (unchanged) — `pending: true/false` published every run regardless of the throttle, using the namespaced topic above.
- `log_server.py`: new `_pending_updates` dict, updated subscribe pattern, new `_on_message` branch parsing component *and* item from the topic (matching the existing `/status` handler's pattern, not from the payload), new "Pending Update" column in `_build_status_html()`.
- **No `_save_state()` work needed, confirmed live**: restarted `jctsh-logging` mid-test and the column repopulated correctly with zero gap, purely from MQTT's own retained-message redelivery on reconnect.
- **The exact bug this card exists to fix, confirmed fixed**: published a real Immich pending-update state (`v3.1.0`, a genuine pending update discovered while testing — not synthetic), then published an unrelated `photo-server` log message. "Last Reading" updated to the new message as expected; "Pending Update" stayed correctly showing `immich: v3.1.0 available`, completely unaffected — this is the failure mode that doesn't work on the old "Last Reading" column, now verified working on the new one.
- Also verified the `pending: false` clearing case (synthetic publish → column correctly shows `—`) before restoring the real state.
- **Bug caught mid-verification, not a design flaw**: after making the topic-namespacing fix above, the corrected `immich-update-check.py` was edited locally but not actually redeployed/re-run on the M8 before the first `/status` check — so the column initially (and correctly, per the fix) showed nothing, since nothing had been published to the *new* topic yet. Redeployed and re-ran; confirmed working immediately after. A reminder that "edited the file" and "the live system reflects the edit" are two different facts worth checking separately, not an issue with the retained-message design itself.

**Related:** `components/photo-server/immich-update-check.py`, `core/logging/log_server.py` (`_compute_status`/`_build_status_html`), CARD-0095 (the M8 maintenance check — same underlying "last-message-wins" limitation on its own log messages, not fixed there, and deliberately not extended to publish retained state in this pass), CARD-0125 (Pi's sibling maintenance check — same consideration, not yet extended either), CARD-0128 (auto-opening kanban PRs from findings — shares the same "know current true state" problem, aimed at git instead of MQTT; build this card first if both are ever built, per CARD-0128's own relationship note).

---

### CARD-0126 · [enhancement] [infrastructure] Container-image update visibility for floating-tag services (NetAlertX, HA, Caddy, cloudflared)
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

### CARD-0125 · [enhancement] [infrastructure] Pi OS/firmware maintenance check — CARD-0095's Pi-side counterpart
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

### CARD-0124 · [enhancement] [photo-server] Detect host-side mount loss and auto-remount photo-library drives (guarded restart for primary)
**Status:** Done

**Raised 2026-07-31**, from a real incident found via the log dashboard: the primary Immich library drive (`/dev/sdd`, Seagate Backup Plus 1TB, bus-powered — `jctsh-parts-inventory.md`) dropped off the USB bus (`journalctl -k`: `usb 5-1: USB disconnect, device number 2` at 18:37:58, re-enumerated 5 seconds later) on 2026-07-30, but nothing remounted it at `/mnt/photo-library` — it sat as an empty, root-owned directory on the boot SSD for **~16.5 hours** until manually fixed. `immich_server`'s Docker health check stayed `healthy` throughout (it only pings the API, not storage); the existing 30-min storage heartbeat check (CARD-0032/CARD-0046) did fire non-collapsing `Alert` rows the whole time, but nobody acted on them until they were noticed by chance, and fixing it required two manual steps a human had to diagnose from scratch: remounting the host-side filesystem, then `docker compose restart` on the Immich stack (bind mounts don't pick up a host remount that happens after the container started — same root-cause class as the 2026-07-10 CARD-0046 incident).

**Root cause of the drop itself:** genuine USB disconnect/reconnect on a bus-powered drive — no I/O or hardware errors found anywhere in `journalctl -k`. Hardware fix (powered dock/enclosure for the primary drive) explicitly **out of scope for this card** — deferred, not rejected, per Joseph's call.

**Plan (extends `components/photo-server/photo-server-heartbeat.py`, no new services):**
1. **Detect:** add a host-side `mountpoint -q <path>` check for all three fstab-mounted drives (`/mnt/photo-library`, `/mnt/photo-library-backup`, `/mnt/photo-library-backup-joseph`) — distinct from the existing container-level write test, so an alert can say specifically "host mount missing" vs. "container has a stale view of a mount that's actually fine."
2. **Auto-remount:** if a mount is missing, immediately run `mount <path>` (replays the existing `/etc/fstab` entry — cheap, safe, idempotent).
3. **Guarded restart (primary only):** only `/mnt/photo-library` is bind-mounted into a container (`immich_server`) — the two backup drives are touched only by `photo-library-backup.sh`, never a running container, so they need no restart step. Immediately following a successful auto-remount of the primary, restart `immich_server` so it picks up the fresh mount. **Trigger only on that specific transition** (mount-was-missing → now-remounted) — never a blind retry-on-every-failed-check loop — so a genuinely flaky/dying drive produces repeated, visible "auto-remounted + restarted" log lines instead of being silently papered over.
4. **Always log**, success or failure, as a non-collapsing `Alert` — same visibility convention the existing checks already use.

**Implementation plan (2026-07-31, Planning):** read `components/photo-server/photo-server-heartbeat.py` in full to design against the real script rather than an assumed shape.

- **No cross-run state file needed.** Detect → remount → (if primary) restart all happen inline, synchronously, within one script invocation — the script already runs fresh every 30 min via systemd timer with no persistent process, so there's nothing to persist between runs. This also *is* the flap guard: worst case it fires once per 30-min tick if the drive keeps dropping, each occurrence separately logged, never a tight retry loop.
- **Insertion point:** new block right after `unhealthy = []` (current line 60), before the existing `for name in CONTAINERS:` docker-health loop. Running it first means that if the primary gets remounted + `immich_server` restarted here, the *existing* downstream checks (docker health status, the `/data/upload/.heartbeat_check` write test, capacity) naturally verify whether the fix actually worked this same cycle — no need to duplicate verification logic. A freshly-restarted container reporting `starting` in this same cycle's health-status check is expected and fine; CARD-0032's own live test already showed containers reach `healthy` well within a minute, so it'll read clean by the *next* cycle regardless.
- **Mount-presence check:** `os.path.ismount(path)` (stdlib, equivalent to `mountpoint -q`) for all three of `CAPACITY_MOUNTS` (already exists in the script, so reused as-is: `{"primary": "/mnt/photo-library", **BACKUP_MOUNTS}`). Missing → append `f"{label}-mount:missing"` to `unhealthy`.
- **Auto-remount:** `subprocess.run(["sudo", "-n", "mount", path], ...)` — the `-n` (non-interactive) flag is required so this fails fast with a clean nonzero exit if the sudoers prerequisite below isn't set up yet, instead of hanging forever with no TTY to prompt (confirmed live 2026-07-31: plain `sudo` on this box blocks waiting for a password when run non-interactively). Re-check `os.path.ismount` after; log `f"{label}-mount:auto-remounted"` on success or `f"{label}-mount:remount-failed(...)"` on failure.
- **Guarded restart, primary only:** only if the *primary* mount was both missing and successfully just remounted this cycle, run `docker restart immich_server` (no `sudo` needed — `jct` is already in the `docker` group per `heartbeat.md`) and log `"immich_server:auto-restarted-after-remount"`. The two backup mounts never get a restart — nothing but `photo-library-backup.sh` ever touches them, confirmed in the script's own existing `BACKUP_MOUNTS` comment.
- **New prerequisite — passwordless sudo for `mount`, three exact commands only:** the heartbeat service runs as `User=jct` (unprivileged), and `mount` needs root. One-time manual setup on the M8 (needs the account password, now known):
  ```
  sudo visudo -f /etc/sudoers.d/photo-server-heartbeat-mount
  ```
  ```
  jct ALL=(root) NOPASSWD: /usr/bin/mount /mnt/photo-library, /usr/bin/mount /mnt/photo-library-backup, /usr/bin/mount /mnt/photo-library-backup-joseph
  ```
  Scoped to these three exact invocations (not a wildcard) — confirm the real path to the `mount` binary via `command -v mount` on the M8 before writing the file, in case it differs from `/usr/bin/mount`.
- **Testing method for Done-when:** `sudo umount /mnt/photo-library` (clean, reversible, no need to physically unplug anything) reproduces "mount missing" directly, unlike the original `mount -o remount,ro` trick CARD-0032 used (that only reproduces read-only, not fully-unmounted). Run the heartbeat script manually afterward and confirm the full chain fires.

**Explicitly out of scope:** hardware change (powered dock/enclosure for the primary drive) — revisit if this recurs. A udev-triggered fast path (seconds instead of up to 30 min) was also considered and deferred — the existing 30-min heartbeat cadence is judged sufficient unless this proves to recur often.

**Done when:** a real drive-drop is simulated (e.g. `mount -o remount,ro` or a physical unplug/replug of the primary) and the dashboard shows the new distinct "host mount missing" alert, followed by an auto-remount + `immich_server` restart with no manual intervention, confirmed by a successful container-level storage write test on the next cycle — tested for the primary drive at minimum, with the auto-remount-only path (no restart) confirmed for both backup drives.

**Built and verified, 2026-07-31.** Implemented in `components/photo-server/photo-server-heartbeat.py`: host-side `os.path.ismount()` check for all three mounts (ahead of the existing container-health loop), `sudo -n mount` auto-remount (new NOPASSWD sudoers rule `/etc/sudoers.d/photo-server-heartbeat-mount` on the M8, scoped to exactly the three mount commands, syntax-validated via `visudo -c` before install), and a guarded `docker restart immich_server` triggered only by a same-cycle remount of the primary — never a blind retry loop.

**Messaging adjusted post-build (2026-07-31):** the first working version rendered a fully-self-healed cycle identically to a still-broken one (both just `"Immich degraded - ..."`, same orange `Alert` styling). Added a separate `recovered` list alongside `unhealthy`, and a three-way split: still-wrong → `Alert`/"degraded" (unchanged); fully self-healed this cycle → `System`/`"Immich recovered - ..."` (distinct wording, doesn't collapse, stays visible); nothing happened → unchanged `"Heartbeat - online."`. Also fixed a related false positive this surfaced: `immich_server` briefly reporting Docker health `starting` right after our own restart was going into `unhealthy` and would have kept a fully-recovered cycle marked "degraded" for no real reason — that transient now routes into `recovered` instead.

**Tested live end-to-end against the real failure, both before and after the messaging change:** `sudo umount /mnt/photo-library` (clean, reversible, no hardware touched) → ran the script manually → single message `"Immich recovered - primary-mount:auto-remounted, immich_server:auto-restarted-after-remount, immich_server:starting-after-restart"`, `status=online`, `category=System`. Verified the recovery was real, not just the log line: `immich_server` reached Docker-healthy, and the exact write-test the heartbeat itself uses (`touch/cat/rm .heartbeat_check`) passed. Ran the script again immediately after — stable `status=online`/`"Heartbeat - online."`, no flapping. Deployed to the M8 (`/usr/local/bin/photo-server-heartbeat.py`). This is the same failure that sat broken for ~16.5 hours undetected-in-practice on 2026-07-30 — it now self-heals within one 30-minute heartbeat cycle with zero manual intervention.

**Not built, per the Planning-stage scope decision:** hardware fix (powered dock/enclosure for the primary drive) and the udev-triggered fast path — both explicitly deferred, not lost.

**Related:** CARD-0032 (original storage-health check), CARD-0046 (extended to backup drives, same "container's cached view goes stale" root-cause class as this card), `components/photo-server/heartbeat.md` (mechanics of the existing checks this extends).

---

### CARD-0110 · [idea] [hike-izer] Hiking stats — elevation graph, elevation summary, speed graph, other stats
**Status:** Backlog

**Raised 2026-07-28**, distinct from CARD-0082 (route map + elevation profile, Gaia-GPS-style): this card is about the numeric/chart stats layer — no basemap, no route visualization, purely derived from data hike-izer's GPS Track already has.

**Reference material — Joseph's own Gaia GPS data-summary screenshot for today's hike:**
- A combined **Speed + Elevation chart**, both series plotted on one graph against Distance on the X-axis (Gaia also offers Time as an X-axis option) — Speed in one color, Elevation in another, distinct Y-axes (mph / ft).
- A **stats block** richer than hike-izer's current Duration + Elevation Gain: **Distance** (1.27 mi), **Moving Time** (29m 47s) vs **Total Time** (32m 23s) vs **Stopped Time** (2m 36s) as three distinct values — not just one duration, **Pace** (25:27 min/mi), **Moving Speed** (2.6 mph) vs **Avg Speed** (2.3 mph) as distinct values, and **Ascent** (49 ft) / **Descent** (40 ft) as separate numbers — richer than hike-izer's current single net "Elevation Gain."

**Scope:**
1. Elevation graph (distance or time on X-axis, elevation on Y-axis).
2. Elevation summary stats — likely Ascent/Descent as separate values, replacing or supplementing the current single Elevation Gain figure (CARD-0109 already removed the old Elevation Range row from Data Summary as prep for this).
3. Speed graph — new; hike-izer has no speed-over-time/distance visualization today.
4. Other stats — Moving Time/Stopped Time/Total Time as distinct values, Moving Speed/Avg Speed as distinct values, Pace.

**Data source:** existing GPS Track data (`fetch_hike_data.py`'s `gps_rows` — timestamp/lat/lon/altitude per point, already flowing through the same pipeline CARD-0082 uses) — ascent/descent, speed, and moving-vs-stopped time are all derivable from consecutive-point deltas; no new data collection needed.

**Build-vs-embed decision, not yet made:** CARD-0104 chose to embed Gaia GPS's own map/track view directly rather than building a custom route renderer, since Joseph already uses Gaia on every hike and Gaia's real widget is "authentically Gaia-GPS-style" for free. The same trade-off applies here, arguably more directly — Gaia is already computing and rendering exactly this chart and these stats today, per the reference screenshot. Worth evaluating the same lighter-weight "embed it" path before committing to a from-scratch native chart, though CARD-0104 already flagged that Gaia's embed requires Joseph to manually mark the track Public and copy embed code each time — not automatable — so a native render (zero-JS, matching this project's convention elsewhere) may still win out for the automatic (CARD-0086) pipeline path even if embedding is used for the interactive/manual path.

**Related:** CARD-0082 (route map + elevation profile, the visual/map-focused sibling of this stats-focused card, same underlying GPS Track data source), CARD-0104 (the Gaia-embed precedent and its "not automatable" caveat), CARD-0109 (removed the old single Elevation Range row from Data Summary, freeing that space for this card's richer stats), `components/hike-izer/fetch_hike_data.py`.

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

### CARD-0096 · [enhancement] [infrastructure] Rename photo-server → m8 and raspberrypi → pi0, adopt a real host-naming convention
**Status:** Planning

**Blocked — deferred until Joseph is physically home (2026-07-31).** Joseph is remote as of this writing (per this session — see the risk summary above, added the same day: Phase 2's own pre-check already calls for running the Pi rename from the home LAN rather than purely remote, given a real Tailscale reconnection hiccup earlier this same session). Plan is written and reviewed; execution holds until he's back on JCTnet1. Phase 0 (read-only audit) carries none of that risk and could technically run remotely — hasn't been started either, pending confirmation this is wanted before he's home rather than folded into one clean start-to-finish session.

**Sequencing update 2026-07-27: CARD-0094 landed** — hike-izer-web's public URL is now `hikes.jctnet.com` via Cloudflare Tunnel, no longer tied to the Tailscale hostname at all, so the original reason to sequence this rename *after* CARD-0094 (avoiding changing the public URL twice) no longer applies — a rename now wouldn't touch the public URL either way. Still not picked up, just no longer blocked/sequenced by anything. The Tailscale hostname (`photo-server.tailfe828a.ts.net`) touch-point below is accordingly lower-stakes than originally noted (it's admin/SSH access only now, not a live public dependency) — kept for completeness since Tailscale device identity still matters for remote access regardless.

**Notes:** Raised 2026-07-24. Motivation: both hosts' current names describe something true only at setup time, not their stable role, and both have already drifted —

- **`photo-server`** (GMKtec M8) was named for its original single purpose (Immich). It has since picked up NetAlertX, hike-izer-web, hike-izer-orchestrator, and (planned) photo-tv-display — "photo-server" no longer describes what it does.
- **`raspberrypi`** (Pi) was never renamed from its default vendor hostname — it describes the *hardware*, not the role. Despite being the actual coordination point of the whole stack (MQTT broker, Node-RED logic, Python log server, HA integration bridge), its name gives zero clue to that.

**New convention decided this session:** general-purpose compute hosts (this pair) get a `jct-` prefix (matches the `jct` Linux username already on both machines, and the `JCT Hotspot` WiFi SSID — ties to personal/household identity, chosen over a `jctsh-` project-branded alternative) plus a stable **role-class** suffix — what *kind* of thing the host is architecturally, not its current specific app list, so the name doesn't go stale again as services are added/removed. Single-purpose edge sensors (`garage-radar`, `salt-sensor`, `front-porch-temp-sensor`, `hiking-monitor`, etc.) are explicitly **not** in scope for this convention change — function-based naming is correct for them since their function is genuinely fixed for the device's life; only the two general-purpose hosts have this problem.

**New names (original decision, 2026-07-24):**
- `photo-server` → ~~`jct-server`~~ (general-purpose Docker application host)
- `raspberrypi` → ~~`jct-hub`~~ (the coordination point — broker/logic/log-server/integration-bridge)

**Naming reconsidered, 2026-07-31 — supersedes the `jct-` prefix + role-suffix convention above:** decided against role-based suffixes (`-server`/`-hub`) in favor of plain hardware nicknames — matches how both hosts are already referred to in every actual conversation, and "what runs on the M8?" is trivially answerable by looking rather than needing to be encoded in the name, so it can't go stale the way `photo-server` already did. Also dropped the `jct-` prefix — decided it doesn't add enough value to justify the extra characters.

- No collision risk against the RV's Pi — confirmed its real hostname/Tailscale name is `coachproxyos` (`jctsh-network.md`), not literally "RV Pi" (that's just the doc-friendly label), so there's already repo precedent for a casual name and the real hostname differing without confusion.
- `raspberrypi` → **`pi0`**, not bare `pi` — the Pi's Linux login user is already `pi` (`ssh pi@raspberrypi.local` today), so a bare `pi` hostname would read as the redundant `ssh pi@pi`. Changing the login user to `jct` instead (matching the M8's user, `ssh jct@m8`) was considered and rejected as out of scope for this card: unlike a hostname rename, the `pi` user's home directory is the live bind-mount path for HA's Docker config volume (`/home/pi/homeassistant/:/config`, per `CLAUDE.md`) — renaming it risks breaking that mount and touches ownership, systemd `User=` directives, cron, and `authorized_keys` on top of everything already scoped below, roughly doubling this card's already-large blast radius to fix something ultimately cosmetic. `pi0` sidesteps the redundancy for free.
- `photo-server` → **`m8`**, staying bare/unnumbered — no username collision (the M8's login user is `jct`, not `m8`), and no second M8 anticipated the way a second Pi plausibly could be. Asymmetric on purpose, not an oversight.
- Future duplicates handled reactively, not pre-numbered: if a second Pi or M8 ever joins the network, it becomes `pi1`/`m81` (or similar) at that time — renaming later costs the same as doing it now, so nothing is gained by numbering preemptively today.

**New names (current):**
- `photo-server` → **`m8`**
- `raspberrypi` → **`pi0`**

**Scope: full rename everywhere, both hosts** (explicitly decided over a docs-only/cosmetic option) — the real hostname, not just how it's referred to in conversation/docs. This is a large, genuinely disruptive, high-blast-radius piece of infrastructure work touching two live production machines — **do not execute without a real plan reviewed first**, not a routine edit. Known touch-points to account for when scoping the actual work (not exhaustive — audit before starting):

- **Physical hostname** on both devices (`sudo hostnamectl set-hostname ...`), mDNS/`.local` resolution
- **Tailscale device name/hostname** — `photo-server.tailfe828a.ts.net` is the M8's Tailscale FQDN, used for admin/SSH access. No longer a public-URL dependency as of CARD-0094 (hike-izer-web moved to `hikes.jctnet.com` via Cloudflare Tunnel, Tailscale Funnel turned off) — a rename here is now lower-stakes than originally scoped, just needs remote-access references (this repo's docs, any saved SSH configs) updated, not a live public URL. Same consideration for the Pi's Tailscale identity ("Home Pi" / `100.70.162.24` — check whether a hostname-based Tailscale reference exists anywhere, e.g. HA's Tailscale HTTPS URL).
- **DHCP reservations** on the router (both hosts, per `jctsh-network.md`'s Devices table) — reservation is by MAC so this likely doesn't need to change, but the *label* in the router UI should match.
- **MQTT**: broker address references (`raspberrypi.local` / `192.168.1.117` — check whether any config uses the hostname vs. the bare IP), the `jctsh/server/photo-server/...` topic segment and `photo-server` heartbeat/log MQTT account name, `jctsh-log-server` account name (does this get touched, or stays project-branded regardless of host rename?).
- **Docker**: `components/photo-server/` repo directory name and every doc link to it, `docker-compose.yml` project/container names, `~/hike-izer-web-app/` and other deployed-app directories living on the M8 (do their *paths* need to change, or just the host they're reached at?).
- **SSH access patterns** everywhere (`ssh jct@photo-server.local`, `ssh pi@raspberrypi.local`) — `credentials.local.md`, this file, component docs.
- **Home Assistant / Node-RED config** — any hostname-based (not IP-based) references to the Pi.
- **ESP32 `secrets.yaml` files** — check whether any reference `raspberrypi.local` by name (vs. IP or DuckDNS) for MQTT broker address.
- **DuckDNS** (`jctsh.duckdns.org`) — likely unaffected (points at the router's public IP via port-forward, not tied to the Pi's own hostname), but confirm.
- **All documentation**: `CLAUDE.md`, `jctsh-network.md`, `credentials.local.md`, every component's own docs, this kanban board (going-forward references — historical/Done card entries should probably keep their as-written host name for accuracy at the time, not be silently rewritten).

**Implementation plan (2026-07-31, Planning — written and reviewed, not yet executed on either live host).**

**Two scoping recommendations to confirm before Build starts** (not yet decided — flag if either is wrong):
1. **Leave the MQTT/log-dashboard component identity (`photo-server`) unchanged.** The topic segment (`jctsh/server/photo-server/...`), the Mosquitto `photo-server` account, and the log dashboard's component grouping are a separate concern from what the *host machine* is called — renaming that identity touches MQTT ACLs, breaks continuity with every historical log entry for this component, and risks the Node-RED watchdog flow's per-component matching, for no real gain (it's an internal message-routing label, not something anyone reads as "the hostname"). Recommend treating an MQTT-identity rename as its own separate, optional future card if ever wanted — out of scope here.
2. **`components/photo-server/` → `components/m8/` directory rename IS in scope** — same staleness problem as the hostname itself, and purely mechanical (a `git mv` plus a repo-wide doc-link sweep, zero live-system risk). Isolated to its own last phase below so it never blocks or gets tangled with the two live-host phases.

**Recommended order: M8 first, Pi second, directory/docs last.** M8 is the lower-stakes host (CARD-0094 already downgraded its Tailscale hostname to admin-only, no live public dependency) — doing it first validates the whole method on lower stakes before touching the Pi, which is the actual coordination hub everything else in the household depends on. Confirmed via direct check this session: Node-RED's MQTT broker node already connects via `"localhost"` (`core/node-red/core.flow.json`), not a hostname — one less thing to worry about on the Pi side.

**Risk summary (2026-07-31):**

*Low risk — no live-system impact:* Phase 0 (read-only audit), Phase 3 (repo-only `git mv` + doc sweep, never touches either live host), the router DHCP label (cosmetic, keyed by MAC not name), the transition-window aliases themselves (purely additive — worst case they just don't help, they don't break anything already working), and the rollback steps (low-risk by design).

*Medium risk:* the M8 hostname/Tailscale rename — a real change to a live host, but the lower-stakes one of the two (see ordering rationale above). Mitigated by the existing pre-check, transition window, instant rollback, and verification checkpoint.

*High risk:*
1. **The Pi hostname/Tailscale rename** — already called out in Phase 2 as the single highest-stakes step in the card. This is the actual household coordination hub (MQTT, Node-RED, the HA/SmartThings/Google Home bridge Robin also relies on), not just a JCTsh concern — a silent breakage here is worse than an obvious one.
2. **The unconfirmed assumption that all 4 ESP32s use IP, not hostname, for their MQTT broker address.** The single biggest unverified assumption in the whole plan. Mitigated by the transition window (buys time even if wrong) and by Phase 0's audit explicitly checking each of the 4 devices before Phase 2 runs.

**Two additional mitigations, folded into the phase pre-checks below:**
- **Timing:** avoid running either rename near a scheduled maintenance window — Pi reboots Mon 3 AM, M8 reboots Mon 4 AM, M8 backup Sun 2 AM, M8 Immich update-check daily 6 AM (`jctsh-network.md`'s table). A hostname change racing a reboot or backup job is an easy-to-avoid risk.
- **Do the Pi rename (Phase 2) while physically on the home LAN, not purely remote.** This session already hit a real Tailscale connectivity hiccup once (the "idle" reconnect earlier). If Tailscale itself hiccups mid-rename, being on JCTnet1 directly removes it as a dependency for the recovery path during the single highest-stakes step in the card.

---

**Phase 0 — audit, read-only, both hosts, before touching anything:**
- **Confirm MagicDNS is enabled tailnet-wide** (Tailscale admin console → DNS settings) before leaning on it as the primary verification method throughout Phases 1–2 below. Strong indirect evidence it already is — `tailscale ping raspberrypi` (bare name, no `.local`, no FQDN) already worked earlier this session, which only works with MagicDNS active — but not yet directly confirmed in the console itself.
- Repo-wide: `grep -rn "raspberrypi\|photo-server"` (already run once this session — 48 files hit `raspberrypi`/`192.168.1.117` alone; re-run fresh at Build time since files change). Bucket each hit into: *IP address (unaffected, skip)*, *historical/Done-card entry (leave as-written per this card's own convention)*, *live reference needing update*.
- On the Pi: check Node-RED's `settings.js` and any flow JSON for hostname (not IP) references; check HA's `configuration.yaml`/Tailscale integration for the same; check crontab and systemd units for embedded hostnames.
- On the M8: same sweep — `docker-compose.yml` files, `cloudflared-config.yml`, systemd units, crontab.
- Confirm each of the 4 ESP32 `secrets.yaml` files' MQTT broker address is IP-based, not `raspberrypi.local` — expected (per `jctsh-network.md`, the remote/DuckDNS path is already IP+port-forward-based) but not yet individually confirmed per device.

**Phase 1 — M8: `photo-server` → `m8`:**
1. Pre-check: `docker ps` on the M8 — confirm all containers currently healthy; confirm CARD-0124's heartbeat last reported clean `online`. Confirm the current time has clearance from M8's scheduled jobs (Mon 4 AM reboot, Sun 2 AM backup, daily 6 AM Immich update-check — `jctsh-network.md`).
2. `sudo hostnamectl set-hostname m8` — verify via `hostname` and a fresh shell prompt.
3. Rename Tailscale device: `sudo tailscale set --hostname=m8` — verify `tailscale status` shows `m8`, and confirm the Tailscale IP `100.111.16.14` is unchanged (it is — Tailscale IPs are stable across a hostname rename, so every IP-based reference, including this session's own SSH commands, keeps working through the entire process; only hostname-based references break, and only until updated).
4. **Transition window — keep the old name resolving alongside the new one, rather than an abrupt cutover.** Publish `photo-server.local` as a static mDNS alias for the M8's real IP (`avahi-publish -a -R photo-server.local 192.168.1.165 &`, or a small systemd one-shot unit for the duration — `avahi-daemon` only auto-advertises whatever the *current* hostname is, so the old `.local` name stops resolving the moment step 2 runs unless this is added). Tailscale's own MagicDNS doesn't support a true dual-name alias the same way — renaming replaces the old name outright — but the equivalent safety net already exists there for free: the Tailscale IP itself never changes, so anything using `100.111.16.14` directly is unaffected regardless of this step. Also add a `photo-server → 192.168.1.165` entry to this Windows laptop's own hosts file for the window's duration, covering any leftover muscle-memory SSH commands run from here specifically.
5. Router DHCP reservation label (cosmetic — reservation is keyed by MAC, not name) — update via router admin UI.
6. Update `jctsh-network.md` (Devices + Tailscale tables) and `credentials.local.md`'s SSH section.
7. **Verify reachability — MagicDNS as the primary check, `.local` mDNS only as secondary.** Primary: `ssh jct@100.111.16.14` (IP, unaffected throughout) and `ssh jct@m8` (MagicDNS — regular unicast DNS over the Tailscale tunnel, reliable on Windows, and the one that actually matters for day-to-day remote access). Secondary, informational only: `ssh jct@m8.local` and `ssh jct@photo-server.local` (should both work, the latter via step 4's alias) — but Windows' own mDNS resolver is known-unreliable on this specific laptop (multiple network adapters including Tailscale's own virtual one can cause the multicast query to go out the wrong interface), so treat a failure on either `.local` check as inconclusive rather than a real problem, and re-run them from the M8 itself (or another Linux box) for a trustworthy result before drawing any conclusion from them.
8. **Verification checkpoint:** Immich, hike-izer-web, hike-izer-orchestrator, and NetAlertX all still reachable and functioning (hostname change shouldn't touch running containers, but confirm rather than assume) — run the CARD-0124 heartbeat script manually, confirm a clean `status=online`.
9. **Close the transition window** once the verification checkpoint has stayed clean for a few days and a fresh repo-wide grep turns up nothing still referencing the old name on purpose: remove the avahi alias and the Windows hosts entry, then confirm `photo-server.local` now correctly fails to resolve — proof nothing was silently still depending on it. Run this specific confirmation from a Linux box (e.g. from the Pi, SSH'd in), not this Windows laptop, for the same mDNS-reliability reason as step 7 — a false "still resolves" from Windows here would wrongly block closing the window.
10. **Rollback, available at any point before the transition window is closed:** `sudo hostnamectl set-hostname photo-server` + `sudo tailscale set --hostname=photo-server` reverts immediately — the Tailscale IP never moves, so this is always a live, low-risk escape hatch, not a point of no return. (Step 4's alias is harmless either way if this happens — it just becomes redundant once the primary name reverts, and can be removed at leisure.)

**Phase 2 — Pi: `raspberrypi` → `pi0`, only after Phase 1 has run stable for a day or two:**
1. Pre-check: confirm MQTT broker, Node-RED, HA, and the log server are all currently healthy. Confirm clearance from the Pi's own Mon 3 AM scheduled reboot (`jctsh-network.md`). **Do this phase from the home LAN (JCTnet1), not purely remote** — this session already hit a real Tailscale reconnection hiccup once; being on the LAN directly removes Tailscale as a dependency for the recovery path during the single highest-stakes step in this card.
2. `sudo hostnamectl set-hostname pi0` — verify.
3. Rename Tailscale device `raspberrypi` → `pi0` — verify `tailscale status`, confirm `100.70.162.24` unchanged.
4. **Transition window, same technique as Phase 1 — and more important here, since this host has the most dependents of the two.** Publish `raspberrypi.local` as a static mDNS alias for the Pi's real IP (`avahi-publish -a -R raspberrypi.local 192.168.1.117 &`, or a systemd one-shot for the duration). Add `raspberrypi → 192.168.1.117` to this Windows laptop's hosts file for the window. If Phase 0's audit turns up *any* hostname-based reference that can't be fixed immediately (e.g., an ESP32 that turns out to use `raspberrypi.local` rather than the IP, contrary to expectation), this window is what prevents that device from going dark the instant step 2 runs — it keeps working via the alias while that specific reference gets updated on its own schedule, rather than forcing every single dependent to be fixed in lockstep with the rename itself.
5. Check every *hostname-based* (not IP-based) consumer specifically:
   - Node-RED MQTT broker node — already confirmed `localhost`, not affected.
   - HA's Tailscale/Nabu Casa config — confirm neither references the old hostname (expect IP/Nabu-Casa-URL-based already, per `jctsh-access.md`).
   - All 4 ESP32 `secrets.yaml` files — confirm IP-based per Phase 0's audit; if any aren't, the transition window (step 4) covers them until each is individually reflashed.
   - `core/logging/log_server.py` — `MQTT_BROKER = "localhost"` already confirmed via direct read this session; unaffected.
6. Router DHCP label, `jctsh-network.md` update.
7. **Verify reachability — MagicDNS as the primary check, same reasoning as Phase 1 step 7.** Primary: `ssh pi@100.70.162.24` (IP) and `ssh pi@pi0` (MagicDNS). Secondary/informational only: `ssh pi@pi0.local` and `ssh pi@raspberrypi.local` — treat a failure on either as inconclusive (Windows mDNS unreliability, not necessarily a real problem) and re-check from a Linux box before concluding anything from them.
8. **Verification checkpoint — the most important one in this card:** watch the log dashboard for continued heartbeats from garage-radar/salt-sensor/front-porch-temp-sensor/hiking-monitor (confirms ESP32→MQTT still works), confirm the Node-RED watchdog flow is still firing, confirm HA reachable both on the LAN and via Nabu Casa, confirm the log dashboard itself is still up.
9. **Close the transition window** once the verification checkpoint has stayed clean for a few days and a fresh repo-wide grep (plus a check of any ESP32s the step-5 audit flagged) confirms nothing is still depending on the old name: remove the avahi alias and the Windows hosts entry, confirm `raspberrypi.local` now correctly fails to resolve. Run this specific confirmation from a Linux box (e.g. from the M8, SSH'd in), not this Windows laptop, for the same mDNS-reliability reason as step 7.
10. **Rollback, available at any point before the transition window is closed:** same pattern as Phase 1 — `hostnamectl` + `tailscale set --hostname` both revert instantly, IP never changes. The step-4 alias is harmless either way and can be removed at leisure if this happens.

**Phase 3 — directory rename + final doc sweep, doc-only, zero live-system risk, do last:**
- `git mv components/photo-server components/m8`.
- Repo-wide find/replace of `components/photo-server/` path references across every doc that links to it.
- Final full-repo grep pass for any remaining `raspberrypi`/`photo-server` string, excluding IP addresses and historical Done-card entries (which stay as-written per this card's own convention, below).

---

**Done when:** both hosts respond to their new names for real (SSH, Tailscale, MQTT, HTTP) with no remaining `photo-server`/`raspberrypi` references in active documentation or live config, the hike-izer-web public URL is updated and reachable at its new address, and nothing that depended on the old names (ESP32 devices, HA, Node-RED, the heartbeat script, NetAlertX) broke in the process — verified live, not just "files edited."

**Related:** CARD-0088 (hike-izer-web hosting — owns the Funnel URL this rename breaks), `jctsh-network.md`, `components/photo-server/`.

---

### CARD-0095 · [enhancement] [photo-server] M8 OS/firmware maintenance backlog
**Status:** Done

**Notes:** Raised 2026-07-24, surfaced via the SSH login MOTD while working on CARD-0088. Four separate items, none acted on yet — all deserve deliberate, scheduled handling rather than an ad hoc mid-task fix, since this host runs live production services (Immich, NetAlertX, hike-izer-web):

1. **23 apt package updates pending** — `apt list --upgradable` for the list. Routine, but should be reviewed before blindly applying (check for anything touching Docker/kernel specifically).
2. **Ubuntu Pro / ESM Apps not enabled** — free for personal use up to 5 machines, would unlock additional security patches beyond standard Ubuntu updates. Worth deciding whether to opt in (`sudo pro status` for current state, https://ubuntu.com/esm).
3. **System restart required** — likely pending from a prior kernel/package update. The M8 already has a weekly scheduled reboot (`jctsh-network.md`, Mon 4:00 AM, `components/photo-server/operations.md`) — check whether that job actually reboots the host (vs. just restarting services) and whether it's still active; if so this may resolve itself, if not it needs a deliberate manual reboot with a check afterward that all `restart: unless-stopped`/`always` containers come back up cleanly.
4. **3 devices have a firmware upgrade available** — `fwupdmgr get-upgrades` for details; not yet investigated what they are or whether they're worth pursuing.

**Re-checked live, 2026-07-31:** confirms item 3's open question — uptime (4d 8h) lines up exactly with the Monday 2026-07-27 4 AM scheduled reboot, so **that job is a real full OS reboot**, not just a service restart. Numbers have grown in the week since raising: apt-upgradable is now 38 (not 23), and `reboot-required` is set again already (triggered by `libc6`, most likely from `unattended-upgrades` applying a security patch automatically since Monday's reboot) — a second sign the reboot cadence is doing real, useful work, just not caught up yet. Firmware findings are more specific than originally scoped: most devices (both backup drives, the boot SSD, System Firmware) report no updates; the real finding is the M8's own UEFI component, with a **Secure Boot forbidden-signature-database (dbx) update addressing CVE-2024-7344** — a known, real Secure Boot bypass vulnerability, the single most security-relevant item found.

**Update policy, decided 2026-07-31 — "keep up to date" vs. "if it ain't broke, don't fix it" is a false binary here:**
- A broken update announces itself immediately and gets fixed with full context. An unpatched vulnerability announces nothing — you find out when something exploits it, which is incident response, not maintenance. That asymmetry is why pure "don't fix it" is wrong for security-relevant items specifically, especially on this host: the M8 has real internet-facing surface area (`hikes.jctnet.com` via Cloudflare Tunnel), not a fully closed LAN device.
- But blind "always update everything immediately" is also wrong — most of what's pending (18 `linux-firmware-*` blobs for hardware that isn't even present, `ubuntu-*` meta-package version bookkeeping) carries no benefit either way, and unnecessary churn is its own risk.
- **The real argument for a regular cadence: deferral doesn't reduce risk, it concentrates it.** Small frequent updates are lower-risk than large infrequent ones — waiting longer means a bigger kernel jump, a bigger Docker jump, more changes bundled together, harder to isolate what broke something if it does. The 23→38 growth in one week is exactly that pattern starting.
- **Resulting policy:** low-risk bulk (firmware blobs, meta-packages, routine libs) applied routinely without much ceremony. Docker/kernel/`libc6`-class updates (and the reboot they often require) applied on a deliberate monthly pass, specifically *because* skipping months makes the eventual pass riskier, not because updating is a virtue in itself. Named-CVE security items (like the dbx update above) get a bias toward applying rather than indefinite deferral — using the same realistic-threat/probability/consequence reasoning this repo's own MQTT risk-acceptance already applies elsewhere (`CLAUDE.md`), not a blanket "any CVE is an emergency" reflex.

**Built and verified, 2026-07-31 — the recurring schedule (check-and-notify only, deliberately not auto-apply):**
- New `components/photo-server/maintenance-check.py`: checks `apt list --upgradable` (splitting into a routine count vs. a review list matching Docker/kernel/`libc6` patterns above), the `/var/run/reboot-required` flag, and `fwupdmgr get-upgrades --json`. Publishes a non-collapsing `Alert` if anything needs review/reboot/firmware, or a plain `System` line if only routine items are pending — same MQTT/log-dashboard pattern as every other check in this repo. A state file throttles repeat notifications for an *unchanged* finding set (7-day reminder interval) without ever suppressing a genuinely new finding.
- **Deliberately notify-only, not auto-apply** — matches every other maintenance script already in this repo (`immich-update-check.py`, the heartbeat scripts), and auto-running `apt upgrade`/`fwupdmgr update` unattended is a meaningfully bigger step than anything else automated so far; Docker/kernel/firmware specifically want a human's judgment per the policy above, not a script's.
- New `core/maintenance/maintenance-check.service` + `.timer`, monthly (1st of month, 7 AM — clear of the M8's Sun 2 AM backup, Mon 4 AM reboot, and daily 6 AM Immich check; added to `jctsh-network.md`'s Scheduled Maintenance Windows table). Deployed and enabled on the M8 (`systemctl enable --now maintenance-check.timer`).
- **Verified live, both paths:** first manual run correctly found and published all four current findings (32 routine, 6 review-list packages, reboot-required, 5 firmware items — confirmed on the dashboard as a non-collapsing `Alert`); an immediate second run correctly recognized the unchanged fingerprint and skipped re-notifying ("next reminder in 6d"), confirming the throttle works without ever silently going quiet on a real finding.
- Item 2 (Ubuntu Pro/ESM opt-in) is a one-time preference decision, not something the recurring check monitors — decided and completed below.

**Low-risk batch applied, 2026-07-31.** All 32 routine packages (everything outside the Docker/kernel/`libc6` review list) installed via `apt-get install --only-upgrade` with an explicit package list — not a blanket `apt upgrade`, specifically so the 6 Docker/containerd packages stayed untouched and held for a separate deliberate pass. Verified clean before and after: all 8 containers stayed running/healthy throughout (`needrestart` confirmed "No containers need to be restarted"), Tailscale itself was in this batch (1.98.8→1.98.10) and confirmed working post-upgrade (`tailscale ping` succeeded). Found and fixed a small gap in `maintenance-check.py` while verifying: the throttle fingerprint didn't include the routine count, so the dashboard's last message kept saying "32 routine pending" after they'd already been applied — added `routine_count` to the fingerprint so a routine-count change now correctly triggers a fresh notification, redeployed, confirmed the next run picked it up immediately.

**Remaining, deliberately not done today:** ~~the 6 Docker/containerd packages...~~ — see below, done same day after all.

**Docker packages, firmware, and reboot completed, 2026-07-31 (same session).** Pre-checked all 8 containers healthy, applied the 6 held-back Docker/containerd packages via the same explicit `--only-upgrade` pattern — Docker's own postinst restarted the daemon automatically this time (unlike the low-risk batch, where a restart was only *deferred*/recommended), which cleanly restarted every container via their existing `restart: unless-stopped`/`always` policies; all 8 back to `healthy` within about 30 seconds, matching the settle time CARD-0124's live test already established. Staged the Secure Boot firmware update with `fwupdmgr update -y --no-reboot-check` (`Successfully installed firmware` for both the UEFI CA and dbx updates — UEFI-level fwupd updates apply via a staged capsule that finalizes on next boot, hence `--no-reboot-check` rather than expecting it to take effect immediately). Rebooted to clear `libc6`'s `reboot-required` flag and finalize the firmware. **Verified fully clean post-reboot:** all 8 containers back to `healthy`, `reboot-required` cleared, `fwupdmgr get-upgrades` now reports "No updates available" (UEFI CA/dbx both show "latest available firmware version"), Tailscale reconnected on its own, the public `hikes.jctnet.com` (Cloudflare Tunnel → `hike-izer-web`) confirmed reachable (`HTTP 200`), and the `maintenance-check.timer` survived the reboot (`systemctl is-enabled` → enabled, next run correctly still 1st-of-month 7 AM). A final manual run of `maintenance-check.py` now reports **"Nothing pending"** — fully caught up, first time since this card was raised 2026-07-24.

**Ubuntu Pro decided and completed, 2026-07-31 — last open item, card closed out.** Decision: enable `esm-infra` + `esm-apps` (real, if narrower-than-it-first-looks, security value — covers Ubuntu's `universe` repo, which otherwise gets zero official patching; almost everything that actually matters on this box — Immich, hike-izer, NetAlertX — runs in Docker with independent base images, and Docker/Tailscale/Node.js are all third-party APT repos anyway, so ESM's real reach is the host OS layer specifically, not the applications). Skip `livepatch` (exists to avoid rebooting for kernel patches — not a problem this host actually has, given tonight's reboot was clean and fast) and `landscape`/`anbox-cloud` (fleet management and Android-in-cloud — not applicable to one home server). Free personal account created, attached via `sudo pro attach <token>` — `esm-apps`/`esm-infra` enabled automatically by the attach itself, `livepatch` came on by default too and was explicitly disabled afterward to match the decision. Verified both ESM repos active in `apt`'s own sources (`esm.ubuntu.com/apps` and `/infra` both present after `apt-get update`) — confirmed at the repository level, not just `pro status`'s own report. No new packages surfaced immediately (everything was already just fully updated), but future runs — including the monthly `maintenance-check.py` — will now catch anything ESM-only. Account and token recorded in `credentials.local.md`.

All four original items now resolved: apt backlog applied, Ubuntu Pro decided and attached, reboot done, firmware done. `maintenance-check.py` reports "Nothing pending," and the recurring monthly check (CARD-0095's actual lasting deliverable) keeps it that way going forward.

**Related:** `components/photo-server/operations.md` (existing M8 maintenance patterns — Immich update check, scheduled reboot), CARD-0088 (the work in progress when this surfaced).

---

### CARD-0085 · [idea] [hike-izer] Hiker's own compass/heading
**Status:** Backlog

**Notes:** Raised 2026-07-23, split out of CARD-0074 (Hike-izer v2, superseded) as an individually-tracked feature. Real gap, not just missing analysis: v1 only computes the *sun's* compass direction from pure astronomy — nothing currently captures which way the hiker was actually facing at any point on the route. Needs new instrumentation (e.g. a magnetometer/compass sensor added to the hiking-monitor hardware) or a different data source entirely — this is likely a hardware-scope card, not a pure software one, and may tie into hiking-monitor's own build cards once scoped.

**Blocking dependency (carried over from CARD-0074):** needs a fresh, confirmed-good real hiking dataset to build and verify against — hiking-monitor device must be back in confirmed-working rotation first (see CARD-0084 for the same note).

**Related:** CARD-0073 (Hike-izer v1, Done), CARD-0074 (superseded), `components/hike-izer/fetch_hike_data.py`.

---

### CARD-0082 · [idea] [hike-izer] Visual track + elevation graphic, Gaia-GPS-style
**Status:** Backlog

**Sequencing update 2026-07-28:** Joseph is trying **CARD-0104** (embedding Gaia GPS's own track view directly, since he already uses Gaia on every hike) first — much less engineering than this card's from-scratch render. This card stays available as the heavier fallback: fully automatable and self-contained (no dependency on Gaia's servers/account staying available), if CARD-0104's embed approach doesn't pan out or a fully-automatic/self-hosted version is wanted later. Not blocked, not deferred indefinitely — just not next.

**Notes:** Raised 2026-07-23. Add a visual graphic depicting the hike route and elevation profile, in the style of Gaia GPS's track view — route line plotted over a real topo/satellite basemap, paired with a distance-vs-elevation chart. This card owns the embedded-visuals and interactive-hover-sync work directly (CARD-0088, once scoped as an intermediary "embedded visuals" level, was narrowed 2026-07-24 to just HTML hosting after realizing it was pure duplicate scope of this card) — this is its own standalone artifact so it can potentially be embedded as a static image in the *current* Markdown output too, not gated on any other card's work landing first. (Note: the Markdown-output reference predates CARD-0091, 2026-07-28 — HTML is now the sole output format; this card's static-image level would embed there instead.)

**Target experience (end goal):** route line + elevation profile shown together, with interactive sync between them — hovering the elevation chart highlights the matching point on the map, matching Gaia GPS's actual behavior.

**Iteration path (agreed 2026-07-23):**
1. **Static image, real basemap** — starting point. A single PNG (or similar) with the GPS route plotted over an actual topo/satellite basemap, plus a separate (not yet linked) elevation profile chart. Embeddable in Markdown output today via standard image syntax.
2. **Interactive, hover-synced** — the real Gaia GPS experience (map ↔ elevation profile linked via hover/scroll). This requires JS/HTML, so naturally becomes an embed within the HTML output CARD-0081 established (Levels 1-2, Done), once this level is built, rather than a standalone file.
3. **Event markers** (added 2026-07-23) — drop markers on the map for photos, hike observations, and other timestamped/geotagged events (bird sightings once CARD-0080 lands are an explicitly confirmed case, not just a hypothetical). Design the marker system generically/extensibly rather than hardcoding a fixed list of event types — whatever ends up timestamped and geotagged in the pipeline should be markerable, not just the types known today. Markers for photos specifically are blocked on CARD-0084 (photo integration, not yet built) — the marker mechanism itself doesn't have to wait, but that particular marker type has nothing to plot until photo data exists.

**Basemap decision (agreed 2026-07-23):** a real topo/satellite basemap is required even for the first (static) iteration — not deferred. Candidate tile providers to evaluate when this is picked up (none confirmed yet):
- **OpenStreetMap tiles** — free, no API key, but subject to OSM's tile usage policy (fine for personal/low-volume use, not for heavy automation); would need a stitching library (e.g. Python `staticmap`) to render tiles + route overlay into one image.
- **Thunderforest "Outdoors" style** — topo/contour styling closest to Gaia GPS's actual look; free tier for personal/hobby use, needs an API key.
- **Mapbox Static Images API** — flexible styling, needs an API key, has a free tier (verify current terms/limits at implementation time, not assumed here).

**Data source:** existing GPS track pipeline (GPSLogger → GPS Track sheet, already wired into `components/hike-izer/fetch_hike_data.py`) — no new data collection needed, this is purely a new rendering of data hike-izer already has.

**Related:** CARD-0104 (the lighter Gaia-embed alternative being tried first), CARD-0081 (HTML rendering, Levels 1-2, Done — established the HTML output this eventually embeds into), CARD-0088 (HTML output hosting — separate, unrelated to this card's scope now), CARD-0084 (Photos, Done — unblocks the photo-marker case of Level 3), CARD-0080 (Bird ID — confirmed marker case of Level 3), CARD-0073 (Hike-izer v1, Done), `components/hike-izer/fetch_hike_data.py`.

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

### CARD-0045 · [bug] [hiking-monitor] `wifi.ap:` fallback may prevent `reboot_timeout` from working
**Status:** Backlog

**Notes:** Found 2026-07-09 while researching a timeout decision for air-quality-monitor (which follows hiking-monitor's firmware pattern). `hiking-monitor.yaml`'s `wifi:` block has no explicit `reboot_timeout` override, so it relies on ESPHome's default (15 minutes before rebooting on failed WiFi connection). However, ESPHome's own issue tracker (esphome/issues#7222) documents that `reboot_timeout` does not apply when a `wifi.ap:` fallback block is configured — and hiking-monitor's config does have one (`ap: ssid: "hiking-monitor-fallback"`). So the 15-minute default may not actually be functioning as designed on the currently-deployed device.

**Priority: low.** Hiking-monitor's upload/home mode requires USB dock power to stay awake (same architecture as air-quality-monitor's charging-based home mode) — if the bug does prevent the reboot from firing, the device would get stuck awake trying to reconnect, but on USB power, not draining battery. No confirmed real-world failure — CARD-0008's actual field test (2026-06-17 camping trip) succeeded without issue. Worst case is a minor operational annoyance (stuck device needing a physical USB reflash to recover), not data loss or a safety risk.

**Resolution path:** confirm whether hiking-monitor actually needs the `ap:` fallback block at all (original rationale not documented in current firmware/docs — may be leftover from early development). If not needed, remove it and the default `reboot_timeout` should function normally. If needed, find an alternative bounded-recovery mechanism that doesn't conflict with the AP fallback.

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
**Status:** Backlog

**Notes:** Decided during photo-server migration (2026-07-04) to skip a manual pre-import quality pass entirely — importing everything as-is and relying on Immich's built-in duplicate detection (CLIP-embedding-based visual similarity, not just byte-hash) plus an ongoing "favorites" curation habit over time. This card captures the option to add an *automated* (no manual photo review) quality pass later, run after the Immich import so you can see real results first before deciding if it's worth doing.

**Tools considered (all scriptable, no manual visual review required):**
- **czkawka** — free, open source (Rust), finds exact + visually-similar duplicates, plus blurry/broken images; has a CLI, could run directly on the M8 against the Immich library folder
- **imagededup** (Python, by Idealo) — perceptual-hash + CNN-based near-duplicate detection, scriptable
- **fdupes** / **rdfind** — simple exact-byte-duplicate finders (fast, catches literal copies only, not near-duplicates)
- **DIY blur-score script** — e.g. OpenCV Laplacian-variance blur detection, a small Python script with a numeric threshold; could be built on request, nothing off-the-shelf needed
- (Commercial alternatives exist — Aftershoot, Narrative Select — but are built for photographers culling shoots, overkill for a one-time family library pass)

**CLIP note:** Immich's own duplicate detection and smart search are both powered by CLIP (Contrastive Language-Image Pre-training, OpenAI) — specifically `ViT-B-32__openai` on this install. Duplicate detection compares visual embeddings (catches near-duplicates like burst shots), not just identical files, and never auto-deletes — it surfaces candidates in a "Duplicates" review screen for manual confirm.

**Important constraint:** any of these tools can run and *report* findings anytime, including post-import, directly against files on disk. But once Immich owns the library, actually *deleting/archiving* anything found must go through Immich itself (its UI/API) — not direct filesystem deletion — since Immich tracks every asset in its Postgres DB and a raw file delete would desync the DB (broken thumbnails, orphaned references). Ties into the planned deletion-logging system (photo-server Step 14).

**Sequencing:** wait until after Joseph's (and later Robin's) Immich import completes and ML processing (duplicate detection, facial recognition) has run. See what Immich's own built-in detection surfaces first, then decide whether an additional automated tool is worth adding.

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

**Raised 2026-07-29 06:59 MST**, during CARD-0111's investigation into the July 29 coverage-message wording. Surfaced two real problems with the current "a hiking event is a single calendar day" model (`SKILL.md`'s core model, written for the original interactive Skill flow):

1. **The automatic pipeline queries the full calendar day (`00:00:00`–`23:59:59` local) even though it doesn't need to.** That convention made sense for the *interactive* flow, where Claude only ever knows which day to summarize, never a precise session window. The automatic path is different — GPSLogger's own `stopped` webhook payload already carries `startedtimestamp` + `duration` (confirmed on the real July 29 payload), i.e. the exact session bounds, and queries the whole day anyway purely because `generation.py` reused `fetch_hike_data.py` unmodified.
2. **A real, confirmed bug, not hypothetical: two hike sessions on the same day get silently merged into one wrong report.** Checked directly in code:
   - `templating.py`'s `hero_time_display()` takes `min(start)`/`max(end)` across *every* `is_hike` session that day — two hikes at 8 AM and 2 PM would render as one nonsensical span like "8:00 AM – 2:30 PM (1h 45m)."
   - `fetch_hike_data.py`'s `stats['distance_mi']` sums distance across all `is_hike` sessions into a single figure — two unrelated hikes' distances get added and reported as one.
   - Elevation gain is computed from the **entire day's raw GPS altitude range**, not scoped to any session at all — even a single hike sharing a day with an unrelated car trip would blend the vehicle's altitude excursions into the reported hike elevation gain.

**Decided model, 2026-07-29 (Joseph):** a hike-izer "event" is a detected hike **session**, not a calendar day. A second hike on the same day doesn't get merged — **it just appends another hike-summary page to that day.**

**Scope to design/build:**
1. Narrow the automatic path's `fetch_hike_data.py` query to the specific session's own bounds (from the webhook's `startedtimestamp`/`duration` or `local_datetime`/`duration`), with a small padding margin (e.g. ±10 min) so near-boundary Environmental Data readings or voice observations aren't clipped. The interactive Skill flow keeps day-based querying — it has no webhook-precise session to narrow to.
2. All hero stats (time span, distance, duration) and elevation gain must be computed from **one session's own data only** — never summed or range-blended across multiple sessions in a day.
3. File-naming/addressing needs to support more than one summary per day — currently everything is keyed purely by date (`<date>_hike-summary.html`, `<date>_photos/`, `<date>_hike-summary.meta.json`). Exact convention for a second same-day hike (e.g. `<date>-2_hike-summary.html`) is an open decision at build time.
4. `build_calendar_index.py` currently assumes one page per day; needs to link to multiple pages on a day that has more than one.
5. Once queries are session-scoped, the "window extends into the future" coverage-truncation note (CARD-0111) shrinks to near-negligible magnitude — revisit whether it's still worth showing at all, especially once CARD-0112's step 1/step 2 model makes "incomplete on purpose" a first-class, expected part of the page rather than something to caveat inline.

**Sequencing, decided 2026-07-29:** build this **before** CARD-0112 (two-step generation redesign), not in parallel and not combined into one change. CARD-0112's staging-directory design and its "regenerate the rich version of `<date>`" conversational trigger phrase need to be built against the *corrected* session-keyed addressing scheme from the start — building 112 first against today's date-only keys would mean reworking its addressing scheme the moment this card lands. Keeping them as separate cards also keeps each independently testable, matching how every other card in this project has been scoped.

**File-naming decided, 2026-07-29 (Joseph):** first hike of a day keeps the plain `<date>_hike-summary.html` stem (no rename of existing files); a second same-day hike gets `<date>-2_hike-summary.html`, a third `<date>-3`, etc.

**Implemented 2026-07-29 (still Build — deployment and real-world validation pending, see below):**
1. `components/hike-izer-orchestrator/generation.py` — new `_session_query_window()` computes the query bounds from the webhook payload's own `startedtimestamp` + `duration` (session start/end) with a `SESSION_QUERY_PADDING` of ±10 min, replacing the full `00:00:00`–`23:59:59` calendar-day window; falls back to the old day-wide window if the payload is missing those fields (defensive, not expected in practice). New `_next_file_stem()` scans `SRV_DIR` for existing `<date>_hike-summary.html`/`<date>-2_...` etc. and picks the next unused stem, used consistently for the HTML, meta.json, photos dir, and temp fetch-data path.
2. `components/hike-izer/fetch_hike_data.py` — new `_rows_in_hike_sessions()` scopes altitude/elevation-gain computation to the confirmed `is_hike` session's own GPS points (via each session's own `[start, end]`), not every raw point in the query window — closes the "car time before/after the hike inflates elevation gain" gap. Distance/duration were already `is_hike`-scoped from CARD-0101; this was the one remaining unscoped stat.
3. `components/hike-izer/build_calendar_index.py` — `META_RE` now recognizes the `<date>-N` naming; `scan_summaries()` returns a list of hike numbers per day instead of a single bool; a day with more than one hike renders the day number linking to hike #1 plus a small sibling link per additional hike (never nested `<a>` tags — confirmed invalid HTML and avoided).
4. `.claude/skills/hike-izer/SKILL.md` — "Core model" section rewritten from "a hiking event is a single calendar day" to "a hiking event is a detected hike session" for consistency with the automatic path; documents the same `<date>`/`<date>-2` naming convention for the interactive flow (which still queries by full day — no webhook-precise session to narrow to — but must not merge multiple real sessions found within one day into a single summary either).

**Verified 2026-07-29, no regressions:**
- `_session_query_window()` against the real July 29 payload produces a ~50-minute window (10:57:58Z–11:47:44Z) instead of the previous ~24-hour one, correctly derived from `startedtimestamp`/`local_datetime`.
- `_next_file_stem()` tested against a temp directory: empty → `2026-07-29`, one existing → `2026-07-29-2`, two existing → `2026-07-29-3`.
- `_rows_in_hike_sessions()` re-run against the real July 29 `hike_data.json`: identical `altitude_ft` result (`min 604 / max 651 / gain 47`) before and after scoping, since that day's whole query window already belonged to the one confirmed session — confirms the fix is a no-op in the already-correct case and only changes behavior when non-hike points are actually present.
- `build_calendar_index.py` tested against synthetic two-hike-same-day data: both links render correctly, confirmed no nested-anchor HTML.

**Deployed 2026-07-29 08:18 MST** — `generation.py`, `fetch_hike_data.py`, `build_calendar_index.py`, and `SKILL.md` copied into the orchestrator's build context on the M8, image rebuilt and container recreated, confirmed healthy.

**Still needed before Done:** real-world validation against an actual multi-hike day and an actual session-narrowed automatic trigger (unit/synthetic tests above cover the logic, but neither the narrowed query window nor the multi-file naming has fired on a genuine live hike yet). Stays in Build until that happens.

**Closing criterion met 2026-07-29, for real, on a genuine second hike.** Joseph hiked twice today — a short morning neighborhood walk (`2026-07-29`) and a real afternoon hike at Frederik Meijer Gardens & Sculpture Park (2h 18m, 3.8 mi, 108 ft gain, 41 photos). The second `stopped` webhook correctly published to `2026-07-29-2_hike-summary.html` — confirmed via the durable MQTT log (`Published hike summary for 2026-07-29-2...`, 11:53:32 MST) and the live page itself — with no merging of the two hikes' stats. This is exactly the untested path this card was waiting on.

**One honest caveat, not a defect in this card's own work:** this second hike's `stopped` event (11:49 MST) fired in the window before CARD-0112's step-1/step-2 split was actually deployed to the M8 (confirmed by reading the container's live `generation.py`, which is correct now — no narrative/place_context call in step 1). So this particular page ran under the old single-shot pipeline (data + narrative + photos all at once, 43 API calls/$1.29, dominated by captioning 41 photos) rather than CARD-0112's data-only-then-enrich flow. That's a one-off artifact of tonight's deploy timing, not a bug in either card — the next automatic hike will exercise both cards' logic together correctly. The narrative itself reads cleanly on inspection, no issues found.

**Related addition:** CARD-0112 (the two-step split this page predates; the timing here is exactly why session-keyed addressing had to land first, per the sequencing decision above).

**Related:** CARD-0111 (the investigation that surfaced this), CARD-0112 (sequenced to follow this card), CARD-0086 (automatic triggering; the webhook payload this reads `startedtimestamp`/`duration` from), CARD-0101/CARD-0100 (existing session-detection/classification logic this builds on, doesn't replace), `components/hike-izer/fetch_hike_data.py`, `components/hike-izer-orchestrator/generation.py`, `components/hike-izer-orchestrator/templating.py`, `components/hike-izer/build_calendar_index.py`.

---

### CARD-0112 · [enhancement] [hike-izer] Two-step generation — automatic data-only publish, then manually-triggered enrichment + narrative — RESOLVED 2026-07-29 14:38 MST
**Status:** Done

**Raised 2026-07-29 06:31 MST**, during CARD-0111's investigation into the July 29 hike's missing photos. That investigation (SSH into the M8, direct Immich API query) confirmed the root cause isn't a code defect: Immich's Android background sync is documented as unreliable (multiple open Immich GitHub issues) — uploads only actually happen when the Immich app is opened/foregrounded, not on any predictable schedule or WiFi-arrival trigger. All 7 of that day's photos landed in Immich within the same ~12-second burst, regardless of when each was taken, confirming a single app-open event, not a rolling background upload.

**The bigger pattern this surfaced:** photos (Immich), the Gaia GPS route embed (CARD-0104), and the planned BirdNET Live bird-ID integration (CARD-0080) all share the same shape — each depends on Joseph manually touching another app or service, not something our own pipeline can force or reliably predict the timing of. Trying to fully automate around each source individually (retries, backfills, timing guesses) fights the actual limitation rather than designing for it.

**Decided approach — split generation into two explicit steps, replacing the current single-shot pipeline:**

**Step 1 — fully automatic, unchanged trigger (CARD-0086's existing GPSLogger `stopped` webhook).** Publishes a **data-only** page immediately, no narrative section at all:
- Everything `fetch_hike_data.py` already produces without any human step: Environmental Data, Hiking Observations, GPS Track + session/hike classification, sun position, Hike Start Forecast.
- Place context (CARD-0108's Nominatim/Overpass base layer + scoped Claude/web-search enrichment) — this is API-only today, no human app-touch required, so it stays in step 1 despite "feeling" like enrichment.
- Mechanical rendering only: hero stats, Data Summary, Sun Position, Full Observations Log, Coverage panel.
- Photos: **still attempts** the Immich fetch in step 1 (Joseph's explicit call, even knowing it'll likely come back empty) — cheap best-effort in case photos happen to already be uploaded for an unrelated reason.
- No Claude narrative call at all in step 1.

**Step 2 — conversationally triggered, to start.** Joseph stages what he can (opens Immich to force its upload, marks a Gaia track public and drops the embed snippet into a staging location, eventually exports BirdNET's CSV once CARD-0080 exists), then tells Claude something like "generate the rich version of July 29." At that point:
- Re-run `fetch_hike_photos.py` against Immich (now populated) and caption any newly-found photos (CARD-0107).
- Read whatever's present in that hike's staging location (see below) — no more relaying file content through chat text.
- Run `narrative.py` now that photos, place context, and any staged enrichment actually exist — a real chance for the narrative to reference actual photo subjects / confirmed route / bird IDs, not one written blind before anything else was ready.
- Re-render the full HTML and republish, replacing the step-1 data-only page.

**Staging mechanism, decided 2026-07-29:** a `<date>_staging/` directory under `/srv/hike-izer/` on the M8 (same convention as the existing `<date>_photos/` dirs), mounted as a Windows drive via **SSHFS-Win** (WinFsp + SSHFS-Win) at `\\sshfs\jct@100.111.16.14\home\jct\hike-izer-web-app\srv`. Deliberately addressed by the **Tailscale IP, not `photo-server.local`** — Tailscale resolves identically whether Joseph is on the home LAN or remote (confirmed relevant now — this card was raised while Joseph was in Michigan), whereas `.local` mDNS only resolves on the home LAN and would silently break remotely. Once mounted, Joseph just drags files into the staging folder in Explorer — no upload endpoint needs to be built.

**Open questions for build time — all resolved 2026-07-29:**
1. **Staged-file naming:** `gaia_embed.html`, `birdnet_export.csv` — implemented as decided.
2. **Step 2 structure:** stayed one `generation.py` module, not a separate script — `run()` is step 1 only (data-only), new `run_step2(file_stem)` handles enrichment + narrative, with a `--step2 <file_stem>` CLI entry point for conversational/manual invocation via `docker exec`.
3. **Persistence:** `hike_data.json` is now written during step 1 and reused by step 2 — but into a **new `PRIVATE_DIR` (`/srv/hike-izer-private`), not `SRV_DIR`**, a decision made while implementing this: `SRV_DIR` is served world-readable by Caddy's `file_server browse` (confirmed by reading the live Caddyfile), and raw GPS trackpoints reveal the exact home address via every hike's start/end coordinates — far more exposure than the curated HTML summary. `PRIVATE_DIR` is mounted only into the `orchestrator` service, never into `web`, so it's never web-reachable at all, rather than relying on a Caddyfile path-exclusion rule that would need remembering to update for every new internal file. `docker-compose.yml` updated accordingly.
4. **CARD-0107 decoupling:** left as-is, not revisited. The core two-step split doesn't need this change to work, and it wasn't worth the scope expansion tonight.
5. **CARD-0080 (BirdNET):** staging directory supports `birdnet_export.csv` landing there once that card exists; no consumption logic built, as decided.
6. **`named_features()` first-point-anchor bug — fixed and verified live against real data.** `place_context.py` now samples named features along the whole confirmed hike session (up to 3 evenly-spaced points, not just the first) plus every distinct photo capture location once photos exist (step 2) — deduped by rounded coordinate and by feature name. **Confirmed working on the real July 29 re-run:** the narrative now correctly centers Grand Rapids Christian High School ("sits right along this stretch of Plymouth Avenue... dating to 1920") — the school actually on that day's route — and demotes Ottawa Hills HS to a brief "close by as well" mention, instead of the wrong full-paragraph treatment it got before.

**Two bugs found and fixed during real-world testing, beyond the original scope:**
- **Overpass rate-limiting, self-inflicted by the fix above.** Sampling multiple points per hike (up to 3 route + several photo locations) fired 8+ Overpass queries back-to-back on a real run and tripped `429 Too Many Requests` almost immediately, on top of Overpass's already-known flakiness. Fixed: capped total queries per hike at `MAX_NAMED_FEATURE_QUERIES = 5` (route samples prioritized, photo locations fill remaining budget) with a 3s pause between each (`NAMED_FEATURE_QUERY_DELAY_S`). Re-verified live: no more 429s, only Overpass's pre-existing occasional 504s (already handled by the existing retry/mirror-fallback, unchanged).
- **`narrative.py` had no retry for transient Anthropic errors, unlike every other API call in this pipeline.** A real step-2 run died outright on a `529 Overloaded` — the SDK's own default retries were already exhausted, meaning this was a real (if brief) overload window, not a one-off blip. `photo_captions.py` and `place_context.py`'s research calls already degrade gracefully on failure, but narrative *is* the point of step 2, so the right fix is retry-with-backoff, not skip-and-continue: added `NARRATIVE_MAX_RETRIES = 3` at `[15, 30, 60]`s backoff, catching `anthropic.APIStatusError`/`APIConnectionError`. **Verified live, same day:** the very next real run hit the identical `529` and the new retry logic caught it, retried after 15s, and succeeded.

**Verified end-to-end against real July 29 data (re-run after the two fixes above), full step 2 succeeded:** Immich re-fetch found all 7 real photos (uploaded since CARD-0111's investigation), 4/7 captioned successfully (3 hit transient 529s, degraded gracefully per existing design), narrative generated on the second attempt (529 retry), full page republished. Total cost **$0.5052** (6 API calls, 4 web searches). Narrative dropped from 471 to 298 words. One residual narrative-quality miss found in this same real output — a forward-reference to the Coverage section survived despite tonight's `SKILL.md` tightening (same "doesn't 100%-reliably catch every instance" pattern already noted on CARD-0108) — **left for a later review pass, per Joseph.**

**Sequencing:** built after CARD-0113 as planned — this card's session-keyed staging design was built against CARD-0113's already-landed addressing scheme, no rework needed.

**Related:** CARD-0111 (the July 29 photo-bug investigation that surfaced this), CARD-0113 (session-scoped generation, sequenced ahead of this card), CARD-0104 (Gaia GPS embed, the original manual-step precedent this generalizes), CARD-0080 (BirdNET bird ID, same manual-step shape — staging directory ready for it), CARD-0108 (place context, stays in step 1; the `named_features` fix landed here without reopening that card), CARD-0107 (photo captions; decoupling from narrative left as-is, not revisited), CARD-0086 (automatic triggering; its webhook now only fires step 1, not full generation as originally built).

---

### CARD-0080 · [idea] [hike-izer] Integrate bird species identified via Merlin Sound ID / BirdNET Live — RESOLVED 2026-07-29 17:18 MST
**Status:** Done

**Moved to Build, 2026-07-29 17:07 MST** — design and module architecture finalized above; implementation starting now.

**Notes:** Raised 2026-07-23. Joseph has been using Cornell Lab's Merlin Bird ID app (Sound ID feature — real-time audio-based species identification, 2000+ species) while hiking and wants that data folded into Hike-izer's narrative summaries, correlated with GPS location and time on the route (e.g. "heard a Canyon Wren near the summit around 2pm") — same treatment the existing GPS track and Environmental Data sources already get, not just a flat species list.

**Data source options considered 2026-07-23 (eBird-based, ruled out):**
1. **eBird bulk export** — "My eBird" → Download My Data → emailed link to a zipped `MyEBirdData.csv` covering all personal observations. Manual/periodic, not automatable on a per-hike basis without extra steps.
2. **eBird per-checklist export** — open a specific checklist → Checklist tools → Download → CSV for just that outing. More precise for matching one hike, still a manual per-hike action.
3. **eBird API** — programmatic access via a personal API key (same credential pattern already used elsewhere in this project — Immich, Apps Script). Described as "designed for limited, recent and summary outputs," not a full data-dump API. **Fundamental grain problem, not just an access-method detail:** eBird's core unit is a checklist tied to one location (or a rough traveling track), not a GPS point per species — even a per-checklist export wouldn't give per-detection coordinates, so this path can't actually deliver "heard near the summit around 2pm"-style correlation regardless of which export/API option is used.

**Key dependency — resolved 2026-07-24:** the eBird path requires Merlin's Sound ID results to actually be **submitted to eBird** as a checklist, which Joseph hasn't done and wasn't planning to commit to for this. Combined with the grain problem above, eBird is not the path.

**Fallback data source investigated 2026-07-24: Merlin's Life List, via screenshot.** Merlin itself has no export/API at all (confirmed, browsing-only). Its **Life List** (cumulative all-time record, not per-session) shows **date + precise address + species per entry directly in the scrollable list view** — no need to tap into individual entries. Workflow would be: after a hike, screenshot that day's Life List entries; Claude reads the screenshot directly (native multimodal vision — no OCR tooling, no transcription). Merlin gives **no time of day, date only** — the design worked out to compensate for this: geocode each entry's address to lat/lon, match to the **nearest point on that day's confirmed GPS track**, and borrow *that trackpoint's own timestamp* as the inferred sighting time. This is a real, workable fallback, but adds a geocoding dependency (service not yet picked) and inherently approximate timing.

**Delivery mechanism considered and rejected:** Quick Share (Android↔Windows, AirDrop-like) requires both devices awake and physically nearby at transfer time — real friction for reviewing a hike's sightings whenever convenient rather than immediately upon getting home. Better direction: auto-backup screenshots to Immich (photo-server) so delivery is decoupled from the laptop's state entirely — but `fetch_hike_photos.py`'s existing matching logic only searches within the hike's own GPS-tracked time window, and a post-hike Life List screenshot wouldn't fall inside that window, so bird-screenshot lookup would need separate matching logic (e.g. same-day screenshots taken after the hike ended) if this path is used.

**Primary path now under evaluation, 2026-07-24: BirdNET Live.** Same Cornell Lab research lineage as Merlin's Sound ID (shared underlying identification tech). Confirmed via research: real-time on-device offline bird ID, a **Survey Mode** built for exactly this (GPS tracking alongside continuous audio detection during a transect), and **direct export to CSV/JSON/GPX/ZIP** — structured data, not a screenshot. **Not yet confirmed:** whether the export has lat/lon + timestamp on each individual detection row, or only session/survey-level GPS — this is the one open question that determines whether it fully replaces the Merlin screenshot-and-geocode fallback above. **Next step: Joseph tries Survey Mode on a real hike, exports a CSV, and reports the actual column structure** — that decides which of the two data-source designs above this card actually builds against. iNaturalist was also considered (clean per-observation API with real per-sighting GPS+timestamp) but its workflow is deliberate/manual per-sighting rather than continuous background listening like Merlin/BirdNET Live, so it's a weaker fit for preserving the current hands-free hiking UX.

**Integration approach (decided):** correlate each bird ID with GPS location + timestamp from the existing hike-izer pipeline (`components/hike-izer/fetch_hike_data.py`), matching the treatment other data sources already get — not a flat unlinked species list.

**Scope:** kept as its own standalone card, not folded into CARD-0074 (Hike-izer v2) — distinct data source with its own open questions worth resolving independently. Not blocked on the hiking-monitor device being back in active rotation (CARD-0074's blocker) — the bird-ID app runs on Joseph's phone, independent of the ESP32 sensor hardware.

**Confirmed via real export, 2026-07-29 16:59 MST:** Joseph ran BirdNET Live Survey Mode on both of today's hikes and provided the exports. Real format is **JSON** (not CSV — the `.gpx` sibling is metadata-only, no track points; `.selections.txt` is a redundant flat duplicate of the same detection fields). Per detection: precise UTC `timestamp`, `commonName`, `scientificName`, `confidence` — but **no per-detection GPS**, only one session-level lat/lon for the whole survey. Resolves the open question from the note above: BirdNET Live doesn't hand us per-sighting GPS directly, but its precise per-detection timestamp is enough to correlate against hike-izer's own already-fetched raw GPS track (`hike_data['gps_track']`, ~30s-resolution points) the same way other data sources are — no separate geocoding dependency needed at all, unlike the Merlin screenshot fallback above.

Also confirmed: the model in use (BirdNET+ V3.0-preview3.1) is a single unified acoustic classifier trained across 9,789 species spanning birds, amphibians, mammals, and insects (not birds-only, unlike the original free BirdNET) — today's real hike 2 export included an American Bullfrog and an Eastern Screech Owl alongside 11 actual bird species. The detection record itself carries no taxon field distinguishing these.

**Design finalized, 2026-07-29 16:59 MST (Joseph's calls):**
1. **Scope:** everything the model reports, no bird-only filtering — avoids building/maintaining our own taxon lookup.
2. **Confidence:** no code-side filter. The app's own capture-time `confidenceThreshold` (35% on today's two exports) is the only floor; Joseph will raise it to 50% in the app going forward.
3. **Output:** a table only, no narrative integration — which also means no GPS correlation is actually needed after all: with no "near the summit"-style place mention to generate, each detection just needs its UTC `timestamp` converted to local time (same `_to_local`/`format_time_local` pattern `templating.py` already uses elsewhere), not matched against the track.
4. **Columns:** Species | Count | Confidence | Time. One row per species, deduplicated (today's hike 2 alone had 27 raw Goldfinch detections) — same collapsing instinct as the log dashboard's Heartbeat convention and CARD-0109's non-redundancy rule, not one row per raw detection. **Time is the first detection** for that species (earliest `timestamp` in its group), not last or an average. **Confidence is the highest confidence value** among that species' grouped detections, not a range or average.
5. **Ingestion:** new `birdnet.py` module (matching `place_context.py`/`photo_captions.py`'s per-source pattern), reading from `<file_stem>_staging/` — same manual-staging convention Gaia's embed already uses (CARD-0112). Accepts either the bare `.json` or the whole exported `.zip` (auto-extracted), so Joseph doesn't need to unzip anything before dropping it in.

**Module architecture, 2026-07-29 17:02 MST:** `birdnet.py` sits at the same tier as `photo_captions.py`/`place_context.py`/`narrative.py` — imported directly into `generation.py` (not subprocessed like `fetch_hike_data.py`, which is shared with the interactive Skill). It **parses only** — finds the staged export, groups `detections[]` by species (name, count, highest confidence, first detection's *raw UTC* timestamp), returns structured data, does no local-time formatting and makes no API calls (no `cost_tracker` needed, unlike the other three). `run_step2()` gets one new call reading `<file_stem>_staging/`, same optional-resource treatment as Gaia's embed (empty/`None` if nothing's staged, not a failure). `templating.py`'s `render_html()` gets a new `birdnet_rows=None` parameter and owns all formatting — converts each row's raw UTC timestamp to local via the same `_to_local`/`format_time_local` helpers already used for hero stats/coverage notes, then renders the table. Keeps one time-formatting source of truth instead of three modules each doing it slightly differently. The staged export file itself is left in place after parsing (not deleted) — same as `hike_data.json`/the photos manifest, so a page can be safely re-rendered later without needing anything re-staged.

**Built and verified, 2026-07-29 17:13 MST.** New `birdnet.py` (parsing only, no API calls) plus `templating.py`'s new `birdnet_rows` parameter/table and `generation.py`'s `run_step2()` wiring, all matching the finalized architecture above. Deployed (orchestrator image rebuilt, `birdnet.py` added to the Dockerfile's `COPY` list). Verified against real production data inside the actual deployed container: staged both of today's real BirdNET Live exports (scp'd directly into each hike's `_staging/` directory — the SSHFS-Win mount referenced in CARD-0112 isn't actually set up yet, see the open question above), parsed correctly (6 species for hike 1, matching the real detection counts/confidences found during design review), rendered a clean table with correct local times — without touching either already-published live page (this adds new content, not a bug fix, so republishing needed Joseph's go-ahead first, unlike CARD-0116/0117's fixes).

**Republished both of today's live pages, 2026-07-29 17:18 MST, Joseph's go-ahead.** Scoped re-render only — no photo re-fetch, no `place_context`, no narrative regeneration, zero additional API cost: reused each page's already-persisted `hike_data.json`/photos manifest, extracted the already-published narrative paragraphs straight from the live HTML (unescaped, so `render_html` doesn't double-escape them), and added the new `birdnet_rows`. **Hike 2 gap found and fixed along the way:** it never got a persisted `PRIVATE_DIR/hike_data.json` (ran under the old single-shot pipeline, before CARD-0112's step-1/step-2 split was deployed) — re-fetched it fresh via `fetch_hike_data.py` (a plain data query, no API cost) using a window bracketing just hike 2's session (11 AM–7 PM local, wide enough to safely include the trailing-drive detection window CARD-0101 depends on, narrow enough to exclude hike 1's unrelated morning session — a full-day window was tried first and correctly rejected, since it would have re-triggered the exact multi-session-blending bug CARD-0113 fixed). Sanity-checked the refetch against the already-published, human-verified values before writing anything: session bounds/distance matched exactly (12:31 PM–2:40 PM, 2.48mi ≈ 2.5mi, trailing drive still correctly force-rejected). Now persisted to `PRIVATE_DIR` for any future re-render. **Verified live on both pages:** Wildlife Heard table present and correct on both (`hikes.jctnet.com`), hike 2's photo captions and `2026-07-29-2_photos/` paths confirmed intact (no repeat of CARD-0117's caption-loss regression).

**Related:** CARD-0073 (Hike-izer v1, Done), CARD-0074 (Hike-izer v2, has its own separate deferred-items list), CARD-0081 (HTML output — undecided yet whether bird sightings surface in Markdown, HTML, or both), CARD-0084 (Photos — same Immich-backend pattern under consideration for screenshot delivery, if that path is used), CARD-0112 (the staging-directory convention this reuses), CARD-0109 (the non-redundancy rule this table-collapsing follows), `components/hike-izer/README.md`, `components/hike-izer/fetch_hike_data.py`.

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
**Status:** Planning

**Notes:** Build a Google Looker Studio dashboard connected to the GPS Track and Environmental Data Google Sheets. GPS route on a map, sensor readings (temp/humidity/pressure/battery) over hike duration. Review-after-the-fact use case — no real-time requirement. No new infrastructure needed.

---

### CARD-0012 · [idea] [air-quality-monitor] Air quality monitor
**Status:** Planning

**Planning docs:** `components/air-quality-monitor/JCTsh-air-quality-monitor-phase1.md` (Phases 1–3), `components/air-quality-monitor/air-quality-monitor-claude-code-instructions.md` (Phase 4)  
**Notes:** Portable clip-mounted SEN55 air quality sensor (PM1.0/2.5/4.0/10, VOC, NOx) carried on hikes alongside the hiking monitor. Phases 1–4 complete (2026-07-09). Parts confirmed on hand: SEN55, Adafruit #5964 adapter, JST GH cable — `jctsh-parts-inventory.md`'s SparkFun SEN-23715 entry was mislabeled "SEN54," corrected to reflect it's the genuine SEN55. SEN55 sensor reading uses ESPHome's native `sen5x` platform (no custom component needed there); a custom component is still needed for onboard flash logging + WiFi replay, adapted from hiking-monitor's `hiking_logger.h`. SEN55 power-gated via an on-hand BC547B NPN transistor (same substitution pattern as remote-temp-sensor-01's BC557B) — bench-tested current draw, not just calculated, in Phase 4 Step 6. Follows hiking-monitor's firmware pattern (onboard flash logging, WiFi replay, field/home mode) exactly — that pattern is field-proven (CARD-0008), and the dependency is architectural only, **not** gated by hiking-monitor's still-open enclosure (CARD-0009). Phase 3 timeout policy matches hiking-monitor but explicitly avoids inheriting CARD-0045's `wifi.ap:`/`reboot_timeout` bug. Perfboard footprint measurement and LiPo polarity check moved from Phase 2 planning blockers to Phase 4 bench steps. Clip-case enclosure (with SEN55 intake/exhaust ports — orientation guidance currently flagged low-confidence, needs re-verification) deferred to a follow-on card, same split as hiking-monitor/remote-temp-sensor-01. Ready for Phase 5 (execution) when directed.

---

### CARD-0013 · [idea] [van-sensors] Van sensors (indoor + outdoor)
**Status:** Planning

**Planning doc:** `components/van-sensors/JCTsh-van-sensor-phase1.md`  
**Notes:** Two ESP32 ESPHome nodes for the Pleasure-Way ProMaster 3500 van. Outdoor: BME280 + LTR-390 UV + SEN55 air quality, LiPo powered. Indoor: BME280 + SCD40 CO2 + MQ-6 propane, 12V coach power. Both log to onboard flash during travel, sync to home MQTT on WiFi reconnect (home or Pixel hotspot). DS3231 RTC for accurate timestamps during extended trips. GPS correlation via GPSLogger on Pixel. Phase 1 complete — ready for Phase 2 (hardware selection, inventory scan, open questions resolved).

---

### CARD-0053 · [idea] [photo-tv-display] Ambient photo slideshow + phone controller
**Status:** Planning

**Planning docs:** `components/photo-tv-display/photo-tv-display-phase1-planning.md` (Phase 1), `components/photo-tv-display/photo-tv-display-phase2-planning.md` (Phase 2), `components/photo-tv-display/photo-tv-display-claude-code-instructions.md` (Phase 4)
**Notes:** Two views of one web app: a fullscreen ambient photo slideshow cast to the gathering room Google TV, and a touch-based phone controller (Joseph's/Robin's Pixel, browser bookmark, no app install) for curation/control. Node.js backend runs on the `photo-server` M8 alongside Immich, serving the web app, syncing TV↔phone over WebSocket (`ws`), and making all Immich API calls on the controller's behalf (including asset deletion, logged before/after the Immich delete confirms per the instructions doc). Hard dependency: `photo-server` must be operational (Immich running, both accounts created, at least a test subset of photos importable) before this build starts — already satisfied. Phase 1–2 planning and Phase 4 Claude Code instructions all complete; instructions doc status is "Ready for execution." Build (Phase 5) has not yet started — no code, service files, or deploy activity yet, this card exists to track that upcoming work.

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

**Raised 2026-07-25**, same conversation as CARD-0100 — Joseph asked the mirror-image question: what if he hikes normally, forgets to stop GPSLogger, gets in the car, and starts driving?

**Real gap, opposite failure mode from CARD-0100:** CARD-0100 is a false *trigger* (no real hike, but the pipeline still runs/publishes). This one risks **losing a real hike's summary entirely.** `fetch_hike_data.py`'s `_gps_sessions()` only split candidate sessions on a time gap (10+ min of no GPS activity) — never sub-segmented one continuous recording by a *speed change* within it. If Joseph walked straight from the trailhead to his parked car (no 10-min pause) and drove off, GPSLogger recorded one unbroken session; `_classify_hike()`'s single median-speed-across-the-whole-session check could then tip into "too fast for walking" if the drive contributed enough fast intervals relative to the hike's walking ones (a longer drive, or a shorter hike), rejecting the real hike along with the drive.

**Implemented 2026-07-27** in `components/hike-izer/fetch_hike_data.py`. New `_sub_segment_by_speed()`: for a session `_classify_hike()` already rejected specifically for excess speed (not daylight or too-slow — narrow, targeted trigger), builds a local rolling-median speed per point (trailing `REGIME_WINDOW_MIN`=3 min window, reusing the existing `WALKING_SPEED_MIN_MPS`/`MAX_MPS` thresholds to label each point slow/walking/fast), run-length-encodes the labels, and absorbs any run shorter than `REGIME_MIN_DURATION_MIN`=3 min / `REGIME_MIN_POINTS`=3 into a neighboring run so a brief downhill jog or GPS jitter can't itself create a false regime boundary. Surviving regime boundaries split the session; each sub-segment is independently re-classified through the existing (unmodified) `_classify_hike()`. `_gps_sessions()` only keeps the split if it actually rescues a hike (at least one sub-segment classifies `is_hike: true`) — otherwise the original single rejected entry is reported unchanged, so a genuine all-drive session (CARD-0100's case) isn't affected. Refactored the per-session dict-building into a shared `_build_session_entry()` helper used by both the normal path and each sub-segment, avoiding duplicating that logic.

**Synthetic-verified 2026-07-27** (no real trailing-drive GPX trace was available — Joseph opted to proceed with documented default parameters now rather than wait): three constructed cases against real Dove Mountain coordinates (`house-lot-coordinates.md`) at a real daylight timestamp —
1. 15-min walk (~1.3 m/s) directly into a 40-min drive (~15 m/s), no gap: whole-session median tips to "too fast" as the bug describes; sub-segmentation correctly rescues the walking portion (`is_hike: true`) and reports the drive as its own correctly-rejected segment.
2. An all-drive session (CARD-0100's case): stays a single correctly-rejected entry, not spuriously split — confirms the "only keep the split if it rescues a hike" guard doesn't regress the existing behavior.
3. A real hike with one brief (1.5 min) fast burst in the middle (simulating a downhill jog or GPS jitter): burst is absorbed into the surrounding walking run per `REGIME_MIN_DURATION_MIN`/`REGIME_MIN_POINTS`, session stays one unsplit `is_hike: true` entry — confirms the false-positive-split concern from the original design discussion is handled.

**Not yet done — needs a real trailing-drive trace before fully closing.** All three constructed cases pass, but `REGIME_WINDOW_MIN`/`REGIME_MIN_DURATION_MIN`/`REGIME_MIN_POINTS` are documented-provisional defaults, same caveat the card always had: synthetic data alone risks tuning them wrong in either direction. **Done when:** a genuine hike-that-rolled-into-a-drive event happens naturally and the resulting GPS Track sheet data confirms the split lands in the right place — or Joseph decides the synthetic validation above is sufficient to close it without waiting for a real occurrence.

**The real trace arrived, 2026-07-29 — and it broke the original design.** Joseph's second hike that day (CARD-0113's Frederik Meijer Gardens hike) deliberately left GPSLogger running through a real drive home. The published page reported 3.8 mi; Gaia GPS reported 2.3 mi for the actual walk — a ~1.5 mi discrepancy that led straight back to this card.

**Root cause of the gap, found by inspecting the real GPS Track data directly:** the trailing drive was only ~7 minutes inside a 138-minute session — far too brief to move the *whole-session median* speed above the walking-pace ceiling, so `_classify_hike()` correctly accepted the session as `is_hike: true`. But the old design (`_sub_segment_by_speed()`) only ever ran its regime-detection scan on sessions `_classify_hike()` had **already rejected** for excess speed — since this session wasn't rejected, sub-segmentation never triggered at all, and the drive's real distance got silently summed into the reported hike distance.

**First redesign attempt failed too, against the same real data — a second, more revealing finding.** Simply removing the "only if rejected" gate wasn't enough: the real drive included genuine stop-and-go driving (accelerate, stop at a light, accelerate again), with several near-zero-speed points from traffic stops interleaved among the fast ones. A trailing rolling-median classifier — mirroring the original bidirectional design's own approach — got dragged back under the walking threshold by those interleaved stops for most of the drive's actual duration, so it still failed to detect a sustained regime.

**Redesigned and verified against real data, 2026-07-29:**
1. `_truncate_trailing_fast_activity()` replaces `_sub_segment_by_speed()` — instead of a windowed median, it scans for the first raw-fast point corroborated by at least `REGIME_MIN_POINTS` more raw-fast points within `TRAILING_ACTIVITY_CONFIRM_WINDOW_MIN` (8 min) forward, spanning at least `REGIME_MIN_DURATION_MIN` (3 min) — robust to interleaved slow points, since it only cares how many genuinely fast points show up nearby, not what the smoothed local average reads. Runs unconditionally on every session now, not gated behind prior rejection.
2. Deliberately **one-directional**: once a transition is confirmed, everything from that point to the end of the session is truncated as a single trailing block, full stop — it doesn't hunt for a "return to walking" afterward, which sidesteps misreading a stop-light pause as resumed hiking.
3. `_build_session_entry()` gained `force_reject_reason` — the truncated trailing block is marked `is_hike: false` directly rather than being re-classified by the same median-speed test that's unreliable on real stop-and-go driving in isolation too.
4. Guard against a degenerate near-empty "prefix": since the very first point in any session has no prior point to compute a speed from, the earliest a transition can be detected is index 1, not 0 — a confirmed transition before `REGIME_MIN_POINTS` keeps the whole session as one entry (an all-drive session, CARD-0100's case, stays a single correctly-rejected entry rather than splitting off a 1-point degenerate stub).

**Verified against all 4 cases — the original 3 synthetic scenarios (corrected for a unit bug in the synthetic-point generator found while re-testing) plus the real trace:**
1. 15-min walk → 40-min drive, no gap: splits correctly, walking rescued (`is_hike: true`), drive rejected.
2. All-drive session (CARD-0100's case): stays one correctly-rejected entry, not spuriously split.
3. Real hike with a brief 2-min jog burst mid-hike: stays one unsplit `is_hike: true` entry — the burst is correctly too short to trigger truncation.
4. **The real July 29 trace:** splits into a 129.3-min/270-point walking session (2.48 mi) and an 8.3-min/17-point rejected trailing block, explicitly reasoned as "sustained non-walking pace detected... e.g. driving after the hike ended." 2.48 mi lines up closely with Gaia's 2.3 mi (the small residual gap is normal cross-app GPS variance, not a bug) — a dramatic improvement over the original 3.8 mi.

**Deployed 2026-07-29 15:23 MST** to the M8's orchestrator.

**Live page corrected 2026-07-29 15:46 MST, Joseph's call.** Initially left the already-published `2026-07-29-2_hike-summary.html` untouched (same reasoning as CARD-0101's own record-preservation instinct), but Joseph asked directly for the distance to be fixed. Re-fetched the real GPS Track data fresh through the now-corrected pipeline and re-rendered (existing narrative/photos reused, zero additional API cost) — live page now correctly shows **2.5 mi** (was 3.8 mi) and **2h 9m** (was 2h 18m, also now correctly excluding the drive time, not just distance).

**Related:** CARD-0100 (the mirror-image false-trigger case, raised same session), CARD-0113 (the session-scoped generation whose real second-hike test surfaced this), `components/hike-izer/fetch_hike_data.py` (`_gps_sessions`/`_classify_hike`/`_truncate_trailing_fast_activity`/`_build_session_entry`).

---

### CARD-0076 · [bug] [hiking-monitor] Rotate all secrets exposed via a botched redaction command, and finish outstanding device re-flashes
**Status:** Build

**Notes:** Raised 2026-07-21. During CARD-0070's debugging session (2026-07-20), a `sed` redaction command intended to mask `secrets.yaml` values before display used a pattern (`key=value`) that didn't match the file's actual `key: "value"` YAML syntax — the redaction silently failed and the **entire** `hiking-monitor-test/secrets.yaml` file printed in plaintext into the conversation transcript: WiFi password, hotspot password, AP fallback password, MQTT password, and OTA password. (Process fix for the redaction mistake itself already logged separately, so this doesn't recur.) The repo's own copy of this file is confirmed gitignored (`components/hiking-monitor/.gitignore`) and was never committed/pushed — the exposure is contained to this session's transcript, not a public leak, but is still being treated as a real exposure event since transcripts can be logged/reviewed outside this conversation.

**Scope (confirmed 2026-07-21, revised 2026-07-22):** all secrets from the exposed file, not just OTA as originally asked — since the whole file printed, every value in it is equally exposed regardless of which one prompted the request:
1. ~~WiFi password~~ — **rotation declined 2026-07-22, risk accepted**, see below.
2. Hotspot password (`hotspot_password`) — new value staged 2026-07-22, awaiting reflash.
3. ~~AP fallback password~~ — same value as WiFi password (see below); **rotation declined 2026-07-22, risk accepted** alongside it.
4. MQTT password (`mqtt_password`) — new value staged 2026-07-22, awaiting reflash.
5. OTA password (`ota_password`) — **already rotated 2026-07-21**, see Progress below.

**Progress (2026-07-21):** OTA password rotated to a new value in all three places that held the old one: `C:\esphome\hiking-monitor-test\secrets.yaml`, `C:\esphome\hiking-monitor\secrets.yaml` (real device's local build dir), and `components/hiking-monitor/secrets.yaml` (repo copy, gitignored). **Not yet reflashed to either device** — the test rig went to sleep after its last successful test with no wake source wired, so it's currently unreachable for OTA (needs the GPIO32→3.3V wake trick, then OTA push, or a USB flash); the real field-deployed hiking-monitor is physically elsewhere and can't be reached at all right now. Both devices are **still running their old OTA password** until reflashed — the new password only exists in the secrets files so far, not on the hardware.

**Progress (2026-07-22) — work done while both devices remain physically unreachable for OTA:**
- **Blast-radius question resolved:** confirmed `wifi_password` is byte-identical across all four ESP32 components' `secrets.yaml` (`front-porch-temp-sensor`, `garage-radar`, `hiking-monitor`, `salt-sensor`) — it is the real JCTnet1 router password, not a device-specific credential. Rotating it means the router itself plus every device and every person's phone/laptop on JCTnet1, not just hiking-monitor — a much bigger operation than this card's other four secrets. **New finding:** hiking-monitor's `ap_password` field is also set to this exact same value (the fallback AP reuses the real WiFi password rather than having its own independent one) — the two must be rotated together, or the fallback AP keeps the old exposed password even after WiFi itself is rotated.
- **`hotspot_password` and `mqtt_password` confirmed device-scoped** (not shared with any other component) — safe to stage new values now without affecting anything else. Generated and written into all three `secrets.yaml` copies (`components/hiking-monitor/secrets.yaml`, `C:\esphome\hiking-monitor\secrets.yaml`, `C:\esphome\hiking-monitor-test\secrets.yaml`): new `hotspot_password` and `mqtt_password` staged, current live values unchanged on both actual devices. **Do not rotate the Pixel's "JCT Hotspot" password or the Mosquitto broker-side `hiking-monitor` account yet** — both must change in lockstep with the reflash, not before, or the device loses connectivity before it has the new credential. See `credentials.local.md` ("hiking-monitor secrets (CARD-0076 rotation, in progress)") for live-vs-staged values and the exact reflash-time steps.
- **Doc-drift fix (unrelated to rotation, found while cross-checking):** `credentials.local.md`'s OTA password entry (`LxgD4hkAIysR7p6UdWM2`) didn't match what's actually in any of the three `secrets.yaml` files (`w5Akzi3hiXQWhufFXNL5`) — corrected the reference doc to the real value.

**WiFi/AP password rotation declined 2026-07-22 — risk accepted, not blocked/pending.** Reasoning: the exposure is confined to this session's private transcript (Joseph's local machine + Anthropic's backend logging, retained for abuse monitoring, not human-reviewed or indexed in the normal course) — never committed to git, never posted publicly, no evidence of any actual access attempt. The realistic attack vectors (local-machine compromise, or an Anthropic-side breach) either already expose the same plaintext value via `credentials.local.md`/`secrets.yaml` on this same machine regardless of this incident, or are outside Joseph's control and not specifically targeted at this household. Consistent with the same low-probability/low-consequence reasoning already applied to CARD-0050's LAN-security risk acceptance. No further action planned on WiFi/AP unless the threat picture changes (e.g., evidence of actual unauthorized access, or the transcript surfacing somewhere public).

**Done when:** OTA, hotspot, and MQTT passwords are rotated on both the test rig and the real field-deployed hiking-monitor (secrets files already updated for all three — reflash is the only remaining step, blocked on physical device access); Mosquitto broker-side password and the Pixel's "JCT Hotspot" setting updated in lockstep with each device's reflash (see `credentials.local.md` for the exact steps). WiFi/AP rotation is explicitly out of scope per the risk-acceptance decision above, not a remaining gap.

---

### CARD-0070 · [enhancement] [hiking-monitor] Replace boost converter with LDO + gate peripheral power for lower standby draw
**Status:** Build

**Notes:** Raised 2026-07-16, directly motivated by CARD-0026's measurement — the test rig's TP4056+boost module draws 22.6mA steady in deep sleep, dominated by the boost stage's always-on quiescent current (est. ~48.7hr / ~2 day runtime on a 1100mAh cell). This matches the existing recommendation in `JCTsh-Build-Standards.md` §2.14 point 7 (prefer direct LiPo→LDO over boost-then-buck) — this card is the concrete follow-through on that recommendation.

**Expanded 2026-07-17 to absorb CARD-0027** (GPIO-controlled peripheral power gating, moved to Defer as superseded — see that card for the original writeup and P-FET/high-side-switch background). CARD-0026's closing note flagged why these two fixes belong together: once the LDO removes the boost stage's ~22.6mA quiescent draw, BME280 + LTR-390's own ungated idle current (previously negligible next to the boost module, estimated tens to a few hundred µA) becomes the largest remaining contributor to sleep current. Doing the LDO swap without also gating the peripherals would leave real savings on the table.

**Part 1 — LDO:** MCP1700-3302E/TO, TO-92 through-hole (3 legs: VIN, GND, VOUT), ~1.6µA quiescent current, 250mA max output. Chosen over AP2112K-3.3 (lower quiescent current margin isn't the issue — package is: SOT-23-5 SMD, impractical for this project's hand-solder/perfboard build convention without a breakout board) and over AMS1117-3.3 (5-10mA quiescent — same problem class as the boost module it's replacing, the wrong part family for a battery/sleep application). **On order, arrives 2026-07-17.**

**MCP1700 TO-92 lead identification** (confirmed against Microchip datasheet DS20001826F, cross-checked via two independent sources 2026-07-20 — this part's pinout is a known gotcha, reordered from the common 78xx VIN-GND-VOUT convention):

| Pin | Position (flat face toward you, legs down) | Signal |
|---|---|---|
| 1 | Left | GND |
| 2 | Middle | VIN |
| 3 | Right | VOUT |

**Part 2 — peripheral gate switch:** BS250 P-channel MOSFET, TO-92 through-hole. Vgs(th) typically ~-2.1V (worst case -3.5V), adequate for a 3.3V GPIO gate drive at the tiny currents involved (a few mA for BME280 + LTR-390, maybe tens of mA momentary for an e-ink refresh) — Rds(on) won't be fully enhanced at only 3.3V Vgs, but that's irrelevant at these current levels. **Ordered 2026-07-17.**

**BS250 TO-92 lead identification** (confirmed via two independent datasheet-sourced references, 2026-07-20):

| Pin | Position (flat face toward you, legs down) | Signal |
|---|---|---|
| 1 | Left | Source |
| 2 | Middle | Gate |
| 3 | Right | Drain |

**Sequencing:** prototype both changes together on the CARD-0026 test rig first (spare ESP32 + spare TP4056, Bag 8) — validates the LDO fix (including whether CARD-0026's brownout-reset-loop finding recurs with the LDO in place) and the peripheral-gating firmware logic together, before touching the real device. Once proven on the rig, port the identical changes to the real field-deployed hiking-monitor.

**Wiring plan — LDO:**
- TP4056 stays exactly as-is — continues managing battery charging (and solar input) unchanged. Only the boost stage is removed from the power path; the boost module's `OUT+`/`OUT-` pads go unused once the LDO is wired in.
- LDO `VIN` taps the same battery+ node as TP4056's `BAT+` input — a parallel connection straight off the raw battery, not fed from the boost module's output.
- LDO `GND` ties to common ground (same ground plane as TP4056/ESP32/battery−).
- LDO `VOUT` → ESP32 dev board's **3V3 pin directly** (not `VIN`) — `VIN` expects ~5V and routes through the board's own onboard regulator; feeding `3V3` bypasses that second regulation stage, which is the point of this change. This same `3V3` pin is now the peripheral supply rail the P-FET switches (see below) — previously it was the ESP32 board's own onboard-regulator output, now it's the LDO's output directly.
- **Caution:** never power the board from USB and the LDO at the same time — both would drive the `3V3` rail from separate unisolated sources, risking backfeeding either regulator. Disconnect the LDO before flashing over USB, and vice versa.

**Wiring plan — peripheral gate (BS250):**
```
3.3V rail (LDO VOUT / ESP32 3V3 pin) ──┬──► P-FET source ──► P-FET drain ──► Sensors (BME280, LTR-390)
                                        │            │
                                    R (100kΩ)         │
                                        │             │
GPIO pin ───────────────────────────────┴─────────────┘ (controls the gate only)
```
- P-FET sits **between the shared 3.3V rail and the sensors** — not between the LDO and the ESP32 itself. The ESP32 must stay powered continuously (straight off the LDO) so it can still control the gate; only the downstream sensor branch gets switched.
- GPIO pulls the gate low (relative to source) → P-FET turns on → 3.3V reaches the sensors. GPIO drives the gate high → P-FET turns off → sensors fully de-powered. Use a spare GPIO not already claimed by GPIO32 (dock detect) or GPIO27 (slide switch). Rig prototype uses GPIO33.
- **Gate-to-source pull-up resistor required (100kΩ, from the Bag 17 resistor assortment) — found missing 2026-07-20, see Progress note below.** Without it, the gate has nothing holding it off except the ESP32 actively driving GPIO high; once deep sleep halts the CPU, the GPIO output isn't guaranteed to hold its driven state, the gate floats, and a floating BS250 gate can sit past its ~-2.1V to -3.5V Vgs(th) and keep the FET on through the whole sleep period. The pull-up guarantees gate defaults HIGH (FET off) whenever GPIO33 isn't actively pulling it low — covering both deep sleep and the brief pre-boot window before the pin is configured. 100kΩ keeps the added leakage while sensors are on (~33µA) negligible against the LDO's own current budget.
- Firmware: drive the gate on before an I2C read, allow a brief settle time for the sensors to power up and initialize, then read; drive the gate off again before entering deep sleep.

**Progress (2026-07-20):** LDO and BS250 gate wired on the CARD-0026 breadboard rig (bare ESP32 only — no sensors attached for this phase, per the "done when" full-stack I2C check being a later step, not this one). Firmware updated (`C:\esphome\hiking-monitor-test\hiking-monitor-test.yaml`): `sensor_power` GPIO switch on GPIO33, active-low to match the BS250 gate, turns on with a 50ms settle delay before each wake's sensor-read block and turns off immediately before all three `deep_sleep.enter` call sites (normal sleep, low-battery cutoff, slide-switch-off). Reflashed via OTA using a temporary trick — briefly moved the GPIO32 dock-detect jumper from GND to 3.3V to hold the rig awake (defeating the immediate-sleep branch) long enough for a reliable OTA push, avoiding the USB/LDO dual-power conflict — then moved the jumper back to GND to restore the CARD-0026 sleep-forcing condition and reset the board.

**Result:** gate turns on correctly, rail holds steady 3.3V, no brownout/reset-looping under the WiFi-connect spike — LDO risk flagged above did not materialize. **But the gate does not turn off during sleep** — confirmed the board actually entered deep sleep (mDNS/ping stopped resolving), yet the gated rail stayed at a steady 3.3V throughout. Root-caused to the missing gate pull-up documented above. Fix identified, not yet installed/retested as of this note.

**Progress (2026-07-20, continued) — pull-up installed, then a second unrelated firmware bug found and fixed:** After wiring the 100kΩ gate pull-up, the rail still didn't drop during sleep. Traced to an unrelated pre-existing bug in `hiking-monitor-test.yaml`'s `slide_switch` binary_sensor: its `on_state` handler fires on ESPHome's initial state publish at every boot (not just on real transitions), and since the slide switch always reads "off" on this rig (GPIO27 unconnected, floats via internal pull-up), that handler ran unconditionally on every boot — calling its own independent `switch.turn_off` + `deep_sleep.enter`, regardless of `dock_detect`, racing against the separate (correctly dock-aware) decision in the `on_boot priority: -200` block. Fixed by adding `binary_sensor.is_off: dock_detect` to that handler's condition, matching the guard already used elsewhere. Reflashed via OTA (added a temporary `api:` component to `hiking-monitor-test.yaml` to pull live logs over WiFi mid-session — still present in the file, harmless to leave, remove before this config is considered final). Also found and fixed during this session: the gate pull-up's non-Gate leg and the BS250's Source leg had been wired to the *raw battery/LDO-input* tap instead of the LDO's regulated *output* — corrected to both land on the LDO output rail, per the wiring plan above.

**Progress (2026-07-20, continued) — systematic diagnosis of a persistent partial-conduction leak:** Even with all of the above fixed, the gated rail still wouldn't drop below ~2.78-2.9V during the "off" condition (against a 100kΩ Drain pull-down added specifically to give Drain a defined reference — it had no load/sensors attached to define this state otherwise). Ruled out, in order, each with a direct test rather than assumption:
- **Ground rail continuity** — checked with battery disconnected, confirmed continuous, not a rail split.
- **FET orientation** — user identified and corrected a Source/Drain swap (had been reading the TO-92 package from the wrong face).
- **GPIO33/firmware involvement** — disconnected GPIO33 from Gate entirely; leak persisted identically, so not a firmware or GPIO drive issue.
- **The resistor/wiring network itself** — pulled the FET out of the breadboard completely (pull-up, pull-down, and all other wiring left in place); Drain cleanly read 0V with no FET installed, confirming the passive network has no bridge or short of its own.
- **A second, physically different BS250** (still Bag 34 stock) substituted in — identical ~2.78V leak reproduced.
- **Empirical lead identification** (diode-test mode, battery disconnected, all 3 leg-pairs both polarities) on the second unit: the pin reading OL against both others in every direction is Gate; the Source/Drain pair showed a real ~0.56V diode drop in one direction only. Anode (current-sourcing/positive-probe leg) = Drain, cathode = Source, per the P-channel body-diode rule. Result confirmed Left=Source, Mid=Gate, Right=Drain — the original standard TO-92 convention from earlier in this card — and confirmed as matching the actual current wiring.
- **Vgs directly measured** (not assumed) in the passive "should be off" state (GPIO33 disconnected, Gate floating via the pull-up only): Source and Gate both read 3.2V — Vgs = 0 exactly, which should put a healthy enhancement-mode P-channel MOSFET solidly into cutoff (off-state resistance normally megaohms+, leakage in the nanoamp-to-low-µA range).

**Conclusion:** with wiring, orientation, GPIO/firmware, the resistor network, and Vgs all directly verified correct, the remaining ~15-19kΩ effective Source-Drain conduction at Vgs=0 (reproduced identically across two physically different units from Bag 34) is far too conductive to be normal MOSFET subthreshold leakage. This points to a **parts/batch quality issue** with the Bag 34 BS250 stock — possibly mismarked or counterfeit units not behaving as genuine enhancement-mode P-channel devices — rather than any remaining circuit fault. (This project has hit exactly this class of problem before: see the counterfeit Podazz BMP280 sensors in `jctsh-parts-inventory.md`.) **Next step: source/verify BS250 units from a different supplier or batch before re-attempting the gate-off verification** — not more rewiring of the current stock.

**Replacement parts ordered (2026-07-20):** genuine BS250P (Diodes Incorporated) from Jameco — an authorized distributor, sourced directly from the manufacturer, unlike the suspect Bag 34 stock's original source. Same part, same datasheet, same pinout convention already confirmed empirically this session (Source-Gate-Drain, standard TO-92). Plan on arrival: run the same diode-test lead/health check used tonight (Gate = OL to both other legs in both directions; Source-Drain pair shows one clean ~0.5-0.7V diode reading, OL the reverse) as an incoming-inspection step before wiring any unit in, then re-attempt the gate-off verification this card is still blocked on.

**Known risk (LDO):** MCP1700's 250mA max is a tighter margin than AP2112K's 600mA against the ESP32's active-WiFi current bursts (109-154mA observed on this same rig during CARD-0026, USB-powered). If the LDO can't sustain those bursts, the same class of brownout-reset loop CARD-0026 diagnosed on the boost module could reappear on the new LDO path — this is exactly what the rig-first prototype step is meant to catch before committing to the real device.

**Standards cross-reference:** inherited from CARD-0027 — logged as a candidate pattern in `JCTsh-Build-Standards.md` §2.14 point 8 (v1.11), flagged `[CANDIDATE — not yet required, pending validation]`. Promote to a real required standard once this card is built and both fixes are measured working.

**Done when:** LDO and P-FET gate both installed and wired per this plan on both the test rig and the real hiking-monitor; each boots cleanly and reaches deep sleep normally on battery power alone (no brownout-reset loop); and the peripheral gate demonstrably cuts sensor power during sleep and restores clean I2C communication (BME280/LTR-390 both respond) on wake.

**Moved to Build (2026-07-20)** — starting the rig-first prototype (LDO + BS250 gate) per the Sequencing note above.

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

### CARD-0009 · [enhancement] [hiking-monitor] Enclosure design and build
**Status:** Build

**Notes:** Design and build the permanent enclosure. Field prototype (two-board sandwich) documented in `components/hiking-monitor/enclosure-prototype.md`. Standoffs arrive 2026-06-14; temp enclosure build before camping trip departure 2026-06-15. Device will be used in the field for ~2 weeks on that trip — hiking and van sensor simulation. Full 3D-printed permanent enclosure is a later step.

**LTR-390 rewiring (2026-07-12):** in progress. Replacing the LTR-390's soldered 0.1" male headers with a 150mm STEMMA QT / Qwiic cable (Adafruit #4209, `jctsh-parts-inventory.md` Bag 31) plugged into the sensor's STEMMA QT port, with the male-header end going into the perfboard's existing LTR-390 female header (unchanged). Gives slack to mount the sensor at the correct sky-facing orientation in the enclosure independent of the perfboard's own orientation — this is what the enclosure build actually needed the flexibility for. Only the sensor-side segment changes; perfboard-to-ESP32 traces (GPIO21/GPIO22) untouched. Docs updated: `wiring.md` (new wire-color table — STEMMA QT cable colors are SDA/SCL-swapped from the old breadboard colors, flagged explicitly), `perfboard-layout.md` (dated addendum on the LTR-390 header row, original build history kept intact).

**Reflection (required last Build step, per `JCTsh-Operating-System.md`):** once the enclosure is built and verified, two harvests before this card closes:

1. **3D-enclosure instruction template.** Generalize `hiking-monitor-enclosure-instructions.md` into a reusable template — e.g. `JCTsh-3D-Enclosure-Instructions-Template.md` at the repo root, following the same pattern `JCTsh-Component-Planning-Pattern.md` already establishes for component planning. Strip out hiking-monitor-specific content (exact dimensions, LTR-390/BME280/display specifics) and keep the reusable procedure: Tinkercad + OpenSCAD two-tool workflow, `-raw`/`-final` export naming convention, Xerocraft Bambu Studio/print-session steps, PLA-test-then-ASA-final print pattern, test-fit checklist structure. So the next component needing a printed enclosure (candidates already in the backlog: remote-temp-sensor-01, air-quality-monitor's clip-case) starts from a template instead of copying and hand-editing this component-specific doc from scratch.
2. **Any other pattern harvesting this card's work warrants** — not just the enclosure template. Sweep the full card history for anything worth capturing somewhere it'll be found again (per TOS's general Reflection rule, not limited to enclosures): the STEMMA QT/Dupont cable relocation fix for sensors that are rigid-socket-mounted facing the wrong way (a mounting-orientation pattern, not enclosure-specific — could recur on any future sensor with a fixed connector orientation); the `-raw`/`-final` STL naming convention and the `hiking-sensor` vs `hiking-monitor` (folder vs. ESPHome device name) confusion this card surfaced, in case anything beyond the enclosure-instructions doc references that ambiguity; and `hiking-monitor-enclosure-instructions.md` Step 56 already exists for build-standards-specific harvest (print orientation, insert types, ASA/PETG choice, etc.) — confirm it actually gets run, don't let this broader reflection substitute for it.

**Don't close until:** rewiring physically complete and I2C communication re-verified (LTR-390 still detected at 0x53, UV/light readings sane) after reassembly, AND both reflection items above are complete.

**Xerocraft trip prep (2026-07-13):** for the Session 1 PLA test print visit (`hiking-monitor-enclosure-instructions.md` Steps 30–33), bring:
- `components/hiking-monitor/enclosure/bottom-shell-final.stl`, `top-shell-final.stl`, `vent-insert-final.stl` — the current, ready-to-print exports.
- `hiking-monitor-enclosure-instructions.md` and `hiking-monitor-enclosure-plan.md` for on-site reference (Steps 30–36 cover this exact session; the plan doc's dimensions table is the fallback if a Step 34/35 test-fit check fails and you need the intended measurement to diagnose the offset).
- Physically: the main perfboard assembly (ESP32/BME280/LTR-390/switch) and the top-shell contents (display, TP4056+adapter, LiPo) — Steps 34–35 test-fit the freshly printed shells against the real hardware, not just visually.

**Doc fix (2026-07-13):** `hiking-monitor-enclosure-instructions.md` had stale STL filenames (`-cuts.stl` instead of the actual `-raw`/`-final` convention) and a wrong `components/hiking-monitor/enclosure/` path (should be `hiking-sensor`) throughout Steps 15, 16, 22, 23, 28, 29, 30, and 55. Corrected in the doc itself, including a naming-convention note near the top — see that file for the convention, not duplicated here.

**Xerocraft PLA test print session (2026-07-17):** Session 1 (Steps 30–33) complete — went very well. Test-fit against the actual soldered main perfboard and top-shell contents surfaced several changes, made live in Tinkercad during the session:
- USB-C charging port relocated — the main perfboard turned out to fit nicely stacked directly over the e-ink display board, changing the available wall space from what was planned.
- M3 screw holes and the solar panel wire hole enlarged (original clearance diameters too tight).
- M3 corner screw holes on the top shell corrected to actually pass all the way through.
- Lip on the bottom shell removed.
- A 1mm reference line added to the bottom shell floor, marking the perfboard's position and adjusted for the screw hole placement.

**Follow-up needed before `hiking-monitor-enclosure-plan.md` Section 0 can be updated to match:** these were live Tinkercad edits — exact new values weren't captured during the session. Section 0 exists specifically as the reproduction record (Tinkercad edits can't be replayed automatically), so it needs: the USB port's new wall/position, the new M3/solar hole diameters, what the removed "lip" was and why, and the floor reference line's exact position/dimensions relative to the perfboard. Get these from Joseph (re-opening the Tinkercad project or checking with calipers) before updating the plan doc.

**Next print planned: white ASA, Session 2** (`hiking-monitor-enclosure-instructions.md` Part 6, Steps 37+) — the final-material print per the doc's existing PLA-test-then-ASA-final pattern. Joseph's expectation going in: should be close given Session 1's fit corrections, with another print iteration available if needed. Section 0's dimension updates (above) should ideally be captured before Session 2 slices the files, so the ASA print reflects the corrected design rather than repeating any not-yet-documented fixes from memory.

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

**Raised 2026-07-28**, split out of CARD-0105's unscoped "answer voiced questions" and "provide history about the area" ideas after real design work and live experiments.

**Purpose, narrowed 2026-07-28 after testing:** three specific things, not "web search for general context":
1. Answer explicit questions Joseph voices during the hike and captures in Hiking Observations (e.g. today's real examples: *"what high school is it their mascot is the Bengals"*, *"wonder what that stands for"*).
2. Identify the specific named place (park, school, trail) at the hike's own coordinates.
3. Enrich with real formation-history, ownership, biology, or geology context once a place is confirmed.

**Explicitly out of scope, decided 2026-07-28:**
- General place-identification via blind web search against raw coordinates — tested directly (real Grand Rapids coordinates, Opus 4.8 + `web_search`): the tool hit a rate limit and returned zero working results across 5 attempts, still billed ~$0.35 for an *unconfirmed* guess, versus ~$0.015 for a plain no-search call that honestly said "I can't tell, here's how to check yourself." Reverse-geocoding (below) replaces this entirely, for free.
- Trail-condition / closure lookups — genuinely time-sensitive info, but by the time a hike is underway it's too late to act on; more relevant during hike *planning*, a separate concern outside this narrative-generation pipeline.

**Governing rules (carried forward from the existing `hike_start_forecast` "never fabricate absence" discipline in `SKILL.md`, and to be kept regardless of implementation):**
- Every augmented fact must come from an actual found source, not recalled from general training-data impression — omit rather than guess when it can't be confidently found.
- Every fact ties back to something that actually happened on the hike (a specific spot, a specific photo) — no disconnected trivia paragraphs. Otherwise this just trades "restates the tables" for "reads like a Wikipedia excerpt," a different flavor of the same original complaint.

**Real pipeline validated 2026-07-28, against today's actual hike coordinates:**
- **Base layer — deterministic, free, no hallucination risk.** Plain Nominatim reverse-geocoding (tested at zoom 14/16/17/18) only ever returns street/suburb-level address text — never a named park or school. **Overpass API** (a different free OSM query: "what named polygon features are near/contain this point," not "what's the nearest address") is the piece that actually works — a real query against today's coordinates correctly returned `Ottawa Hills High School` and `Ottawa Hills High School Athletic Fields` (operator: Grand Rapids Public Schools) and the separate `Ottawa Hills Park` nearby. This answers land ownership/type directly, no search or LLM guessing needed. The same mechanism (querying `route=hiking` relations) can surface named trail-network membership.
- **Enrichment layer — scoped search, only once a name is confirmed.** Targeted queries against a specific known name, not blind coordinate search — e.g. *"why is Ottawa Hills High School named that"*, *"what is Ottawa Hills High School known for (curriculum, sports records/championships)"* (both raised by Joseph 2026-07-28, using today's real sign photo as the concrete example), or *"what is [named program] Grand Rapids Parks & Rec"* once a specific public facility is identified — e.g. today's hike passed a public outdoor fitness course that appears to be a City of Grand Rapids Parks & Rec installation in 1-2 photos; once CARD-0107's vision step (or Overpass, if it's a named/tagged feature) identifies the specific program, a scoped search on that name is real value-add, distinct from guessing at unnamed equipment. This layer is the vision → search handoff described in CARD-0107.
- **Regional-scope layer — same search mechanism, keyed to the broad area, not the exact point.** Geology/topology and biology/ecology are inherently regional facts ("this area sits on glacial till from the Wisconsin glaciation," "you're in [ecoregion], where trumpet vine's presence means X") — treating them as regional rather than point-specific is both more accurate and reusable across hikes in the same area, rather than a fresh lookup every time.

**Architecture, resolved 2026-07-28 (Joseph):** no separate "Local Context" section after all — findings feed into `narrative.py`'s existing call and get woven into "The Hike" as one continuous story, same voice as the rest of the narrative. Reasoning: a separate section would need its own de-duplication pass against both the observations table and the narrative itself; folding everything into one generation call lets the same non-redundancy discipline (CARD-0109) dedupe against everything it can see in a single pass instead of needing a second reconciliation step. Also decided: the narrative should never report that a question was voiced (that's already visible in the Full Observations Log table) — it should just answer it, tied to the moment in the story.

**Built 2026-07-28:**
1. `components/hike-izer-orchestrator/place_context.py` (new) — `gather_place_context(hike_data, photos_manifest, api_key)`. Base layer: Nominatim (address) + Overpass (named park/school/trail + operator), both plain `urllib`, no new dependency. Enrichment layer: one Claude + `web_search` call, scoped only to confirmed names (from Overpass or a photo's `sign_text`, CARD-0107) and real Hiking Observations text — never a blind coordinate guess.
2. `narrative.py` — `generate_narrative()` takes a new `place_context` list, added to the JSON payload alongside `hiking_observations`/`stats`/etc.
3. `SKILL.md` part (a) — new guidance: weave `place_context` in, don't list it; answer a voiced question instead of reporting it was asked; apply the same non-redundancy discipline across `place_context`, the observations table, and the narrative's own sentences. Also fixed a stale doc reference found in passing — the weather-forecast section still described the pre-CARD-0106 "fires off the first Hiking Observation" trigger.
4. `generation.py` — calls `place_context.gather_place_context()` after photo captioning (so `sign_text` is available), passes the result into `narrative.generate_narrative()`.

**Two real bugs found and fixed via live testing against today's actual hike:**
- **Narration-leak bug.** Without a dedicated place to reason, the model's own research process ("I'll research...", "Search limit reached...") landed directly in the final text response — structurally indistinguishable from a real fact once split into lines. A live run actually discarded a **good** research pass because one narration line tripped the (correct) all-or-nothing guard. Root-fixed by adding `thinking: {"type": "adaptive"}` to the enrichment call, giving the model somewhere to reason that isn't the parsed output; the strict-format prompt instruction and the narration-keyword guard both stay as defense in depth, not the primary fix.
- **Overpass reliability, addressed 2026-07-28.** The same free public Overpass instance that worked cleanly in CARD-0107's earlier testing returned `504 Gateway Timeout` on two consecutive real runs. Added a second independent public mirror (Kumi Systems) as fallback — but a direct isolated test of that second mirror *also* timed out, on its own, nothing else running. Three timeouts across two independent providers this session reads as broadly unreliable public Overpass access during this window, not one instance having a bad day, so mirror-fallback alone wasn't enough confidence. **Fix:** up to 2 attempts per mirror (2 mirrors, 4 total attempts), raised timeouts (client 35s, Overpass's own internal `[timeout:25]`, both up from 30s/15s), 3s pause between same-mirror attempts. Re-tested afterward: succeeded in 2.3s on the very first attempt — confirms the retry/fallback code itself is correct, and that availability is genuinely intermittent (sometimes instant, sometimes down) rather than something to eliminate outright. This raises the odds of success; it isn't and can't be a guarantee against a free service with no SLA — `named_features()` returning `[]` (graceful degradation, unchanged) remains the real safety net, not this loop succeeding every time.

**Full pipeline verified against today's real hike** (base layer degraded by the Overpass timeout above, enrichment layer worked): real woven narrative produced, answering both voiced questions in-story ("The high school with the Bengals mascot is Ottawa Hills High School itself — and the 'OHHS' that prompted a puzzled aside is simply that school's abbreviation"), with genuinely surprising researched color (the school's prior "Indians" mascot and Native-American-motif building history, an NFL alumnus, the National Fitness Campaign's Dianne Feinstein-backed 1979 origin) woven into the story rather than listed. No forward-reference regression (the sensor-outage paragraph stayed clean).

**One residual issue, honestly not fully solved:** the generated narrative's opening line — "a loop of a little over two miles" — is a softer echo of the exact paraphrase-restatement problem CARD-0109 targeted (Distance: 2.0 mi is in the hero stat row). CARD-0109's rule caught 3 of the 4 original violations outright but doesn't 100%-reliably catch every instance of this shape of paraphrase. Not a new regression from this card's work, but surfaced by it -- worth a closer look at whether the rule needs another pass, or whether this is normal LLM-output variance to tolerate.

**Regional-scope layer built and verified 2026-07-28** — purpose #3 (geology/biology, keyed to the broad county/state area rather than the exact point). `gather_regional(region, cache_path, api_key)` shares the same Claude+`web_search` mechanism as the enrichment layer (extracted into a shared `_run_research_call()` helper) but keys off `_region_key()` (county/state/country from the same Nominatim response `gather_place_context()` already fetches, so no second geocoding call) and caches to a JSON file on disk — only non-empty results are cached, so a transient search failure is retried on the next hike in the region rather than permanently baked in as "nothing here."

**Two more real bugs found and fixed via this layer's live testing:**
- **Non-streaming request-length ceiling.** `_run_research_call` used a blocking `messages.create()` — a real run hit Anthropic's long-request limit at exactly 1801s and errored out (`docs.anthropic.com/en/api/errors#long-requests`): adaptive thinking plus several `web_search` round-trips can genuinely run past the ~10min a non-streaming call is allowed. Fixed: switched to `client.messages.stream()` + `get_final_message()`, which has no such ceiling.
- **Wrong text-block extraction discarded a real, good research pass.** A `web_search` response's `.content` interleaves narration-style text blocks ("I'll search for...") *before each individual search* with the real final answer at the end — joining every text block in the response (the original approach) pulled that pre-search narration in alongside good facts, correctly tripping the narration guard and discarding a real, useful pass. Fixed: only join text blocks after the *last* non-text block (i.e. after the last search result), which is the model's actual final answer.

**Real test result, 2026-07-28** (Kent County, MI, cold cache): 19 total facts — real Ottawa Hills HS history (previous "Indians" mascot, orange/black colors, 1923 land purchase, 1925 opening, Native-American-motif entrance) plus genuine regional geology (Mississippian-age Michigan Formation bedrock, Jurassic "red beds," the Plaster Creek gypsum-mining history, glacial drift landscape, county elevation range). Cache write confirmed; a second `gather_regional()` call against the same region returned instantly (0.000s) from cache, no new API call.

**Real cost measured, 2026-07-28 — higher than expected, then tuned down 70%.** The first real cold-cache run (enrichment + regional together) cost **$1.86** (300K input tokens, 9,922 output tokens, 11 web searches) — well above the ~$0.35 "expensive, rejected" blind-search figure cited above as the reason blind coordinate search was ruled out. Almost all of that ($1.50 of $1.86) was input tokens, not the web-search fee itself ($0.11) — each additional search's results compound into every later turn's input tokens within a call, so search count drives cost more than proportionally.

**Tuned 2026-07-28:** cut `max_uses` (enrichment 6→4, regional 5→3) and added explicit "budget your searches, prefer one strong source per topic" guidance to both prompts. Re-tested against the same real Kent County data, cold cache: **$0.56** (75K input tokens, 4,384 output tokens, 7 web searches — both calls used their full new budget) in **107s**, down from 21.4 minutes. Quality held up — the tuned run still produced genuinely specific, surprising facts (the Grand River as an "under-fit stream" carved by glacial meltwater, the Saginaw/Lake Michigan ice-lobe boundary, oak savanna's collapse from 2M acres to 8,000, prairie fens), not thinner or more generic than the untuned run. Regional is still a one-time-per-county cost (cached after — and for Joseph's home-turf counties, Pima/Maricopa are ~9,200 sq mi each vs. Kent County's ~870, so home-area hikes should amortize this to near-zero after the first). Enrichment's ~$0.4-0.5/hike (regional's cached share of the $0.56 subtracted) is the real recurring cost, worth watching across more real hikes.

**Cost tracking added, 2026-07-28** — `components/hike-izer-orchestrator/cost_tracking.py` (new): `CostTracker.record(response)` sums real `usage` (input/output tokens, `web_search_requests`) across every Claude call in a generation run and prices it (`$5/$25 per 1M tokens` for Opus 4.8, `$10/1,000 searches` for web search — both confirmed live against current docs). Threaded as an optional `cost_tracker=` param through `narrative.generate_narrative()`, `photo_captions.caption_photos()`, and every `place_context.py` research call; `generation.py` creates one tracker per run and appends its `.summary()` to the completion MQTT log line, so every real hike's actual API cost is now visible on the dashboard, not just discoverable via a one-off Console lookup. Verified against real API responses (`server_tool_use=None` case and a real web-search response both handled correctly) before wiring in.

**Closing note, 2026-07-29:** all three layers (base, enrichment, regional) are built, deployed, and verified against multiple real hikes, with cost tracking in place. The residual paraphrase issue above stays as documented color, not a blocker. One real accuracy gap surfaced since — `named_features()` anchors to the hike's first GPS point only, not the whole route, which can attribute a landmark from a *different* day's hike at the same starting point (found reviewing the July 29 narrative) — tracked forward as its own item in CARD-0112, not reopening this card.

**Related:** CARD-0105 (the unscoped idea this splits out of), CARD-0107 (the vision step this receives named subjects from), CARD-0109 (the non-redundancy rule this shares, and the residual issue noted above), CARD-0083/CARD-0097/CARD-0106 (the existing `hike_start_forecast` "never fabricate" pattern this design extends), CARD-0112 (the `named_features` first-point-anchor accuracy fix tracked forward there), CARD-0111 (the July 29 hike review that surfaced that gap).

---

### CARD-0106 · [bug] [hike-izer] Hike Start Forecast has captured zero rows since at least June 2026, despite CARD-0083/CARD-0097 shipping and being verified live — RESOLVED 2026-07-29 07:44 MST
**Status:** Done

**Raised 2026-07-28**, while investigating today's hike summary showing "not available" across the entire Weather Forecast at Hike Start section.

**Confirmed via direct investigation:**
- `Hike Start Forecast` sheet has 0 rows for the whole window 2026-06-01 through 2026-07-29 (checked via the live `action=export` endpoint) — not a one-day miss, the mechanism hasn't captured anything in at least ~2 months.
- Today's trigger condition was clearly met: all 7 real Hiking Observations logged today (11:52–11:56 AM UTC) carry resolved GPS coordinates via `_gpsLookup` — the "GPS hasn't resolved yet" skip path in `_maybeCaptureHikeStartForecast` doesn't explain this.
- Open-Meteo itself is healthy: replicated the exact forecast call the script makes, using one of today's real coordinates — HTTP 200, valid hourly data, correct `utc_offset_seconds: -14400` for Michigan.
- Live deployment reports version `2026-07-25.2-timeline-local-timezone-fix` — a version *after* CARD-0097's forecast-timezone fix, so the fix should be live, though there's no way to directly confirm the deployed source matches the repo copy of `environmental-data.gs` without OAuth access to the Apps Script API (these deploys are manual copy-paste, so repo/live drift is a real possibility given this project's history).
- **Executions log checked 2026-07-28 (Joseph):** all POSTs/GETs completed successfully, no errors logged.
- **Live source diffed 2026-07-28:** Joseph pasted the full live `_maybeCaptureHikeStartForecast` function body from the Apps Script editor; diffed byte-for-byte against the repo copy — identical. Drift/stale-deploy hypothesis ruled out. The version-string check that suggested this earlier is not proof of content match (it's a hand-typed label, not a checksum) — noting that distinction for future investigations on this file.
- **Duplicate/mismatched sheet name ruled out:** Joseph confirmed only one tab named "Hike Start Forecast" exists.
- **Synthetic test observation sent 2026-07-28** (timestamped inside today's real GPS-track window, so `_gpsLookup` resolved a real position) — **and it worked.** A real forecast row was captured (`temp_f: 67.3, precip_pct: 0, wind_mph: 5.9, humidity_pct: 93, uv_index: 0.5`). This proved the function itself is not broken, and reframed the question: why did an isolated test succeed where all 7 of today's real observations (and every real observation for ~2 months) did not?
- **Real bug #1 found via that test:** the captured row's `date_local` value came back as `2026-07-28T07:00:00.000Z` — a full Date object, not the plain `"2026-07-28"` string the dedup comparison needs. `forecastSheet.getRange('B:B').setNumberFormat('@')` does not reliably stop Sheets' `appendRow()` from auto-detecting a bare `"YYYY-MM-DD"` string as a real Date on write. This wouldn't explain zero rows on its own (a mismatched dedup key means *more* captures, not fewer) but is a real latent bug.
- **Leading theory for the actual zero-rows cause:** today's 7 real observations arrived in a tight burst (11:52:26–11:56:55, roughly one every 20–40s) — real concurrency risk, since Apps Script doesn't serialize concurrent `doPost` executions. It's also possible one of those executions hit an exception caught by the function's own internal `try/catch` (logged via `console.error`) without failing the overall request — the outer `doPost` always returns 200 regardless of inner forecast-capture outcome, so "no errors" at the Executions **list** level doesn't rule this out; it would require opening each individual execution's own log output, which wasn't done.

**Design flaw identified, 2026-07-28 (Joseph) — bigger than either bug above:** the whole trigger mechanism was unreliable by construction, independent of the bugs. Capture was keyed to the first *Hiking Observation* of the day — but a voice observation is optional (a hike with none never captures a forecast at all) and arbitrarily timed relative to when the hike actually started (could be a minute in, could be an hour in). **Proposed fix: trigger off the first *GPS point* of the day instead.** GPS logging is continuous and always present during a real hike, fires every ~30 seconds (not in a tight multi-request burst the way today's 7 observations did — incidentally also reduces the concurrency risk above), and each `action=gps` request already carries its own resolved `lat`/`lon`, so no `_gpsLookup` correlation step is even needed.

**Fixed 2026-07-28, in the repo** (`core/data-pipeline/environmental-data.gs`, not yet deployed):
1. Moved the `_maybeCaptureHikeStartForecast(...)` call from `doPost`'s hiking-observations branch to `doGet`'s `action === 'gps'` branch, right after the GPS point is appended to `GPS Track` — passes `{lat: lat, lon: lon}` directly from the request's own parsed coordinates.
2. Fixed the `date_local` Date-object bug: the appended value is now prefixed with a leading apostrophe (`"'" + dateLocal`) — the same mechanism Sheets' own UI uses to force literal text, and the reliable fix now that `setNumberFormat('@')` alone is confirmed insufficient.
3. Bumped `SCRIPT_VERSION` to `2026-07-28.1-hike-start-forecast-gps-trigger`.

**Deployed and synthetically verified 2026-07-28:** new script pasted into the Apps Script editor and redeployed — confirmed live via `action=version` (`2026-07-28.1-hike-start-forecast-gps-trigger`). A synthetic GPS point (`action=gps`, no observation involved at all) produced a real forecast row (`temp_f: 69.7, date_local: '2026-07-28'` — genuine plain string, not the old Date-object artifact). Both fixes confirmed working under a controlled test. Test rows (one in `GPS Track`, one in `Hike Start Forecast`) still need manual deletion — no delete endpoint on this API.

**Staying open — decided 2026-07-28 (Joseph):** the synthetic test proves the mechanism works, but not that it holds up under real conditions end-to-end (real GPSLogger → Apps Script path, including whatever timing/concurrency characteristics the original burst-of-observations failure may have depended on). Closing criterion is a real hike, not another synthetic test.

**Closing criterion met 2026-07-29.** The real July 29 Michigan hike — a genuine GPSLogger → Apps Script path, no synthetic data involved — captured a real Hike Start Forecast row (`temp_f: 59, precip_pct: 0, wind_mph: 5, humidity_pct: 81, uv_index: 0`), confirmed rendering correctly on the live page's Weather Forecast at Hike Start section. The GPS-point trigger (moved off the optional/arbitrarily-timed Hiking Observation trigger) held up under real end-to-end conditions, not just the earlier synthetic test.

**Related:** CARD-0083 (original feature), CARD-0097 (timezone fix, the behavior this card's symptom contradicts), CARD-0099 (Timeline sheet fix, deployed same day, matches the currently-live version string), CARD-0111 (the July 29 hike review that confirmed this closing criterion), `core/data-pipeline/environmental-data.gs`, `components/hike-izer/fetch_hike_data.py`.

---

### CARD-0104 · [idea] [hike-izer] Embed Gaia GPS's own track/map view instead of building a custom route+elevation renderer — option 1 verified live on 2 real hikes 2026-07-28 — RESOLVED 2026-07-29 07:44 MST
**Status:** Done

**Raised 2026-07-28**, exploring CARD-0082 (custom Gaia-GPS-style route+elevation graphic) — Joseph pointed out he already uses Gaia GPS on every hike, which raised the question of integrating with Gaia directly instead of re-rendering the same visual from scratch.

**Researched 2026-07-28:** Gaia GPS has no official public API (confirmed via their own help-center community posts — a public API has been a standing community request for years, not shipped). It does have an official **"Embed on your website"** feature: mark a specific track Public on gaiagps.com, then copy an iframe embed code from that track's page. The embed shows the Gaia Topo map with the track overlaid, plus stats and a link back to the source. An unofficial reverse-engineered Python client (`gaiagpsclient` on GitHub) also exists but isn't a real option for anything meant to run long-term — no support, can break on any internal API change, real ToS risk.

**Why this over CARD-0082:** dramatically less engineering — no basemap-provider decision, no tile-rendering/elevation-chart code to build, no new dependency. It's authentically "Gaia GPS style" because it *is* Gaia GPS. **Positioned as the lighter-weight path to try first** — CARD-0082 (full custom render, automatable, self-contained) stays available as the heavier fallback if this doesn't pan out or a fully-automatic/self-hosted version is wanted later.

**Trade-offs, both explicitly accepted by Joseph when this card was raised (not open questions):**
- **No API means a manual step every time** — Joseph marks the track Public and copies the embed code himself; this can't be scripted. Accepted: this is a nice-to-have visual, not core pipeline function.
- **That day's exact route becomes link-visible** (not searchable/indexed, but reachable by anyone with the URL) once marked Public. Accepted trade-off for the convenience.

**Real architectural point — the map has to be a follow-up patch, not part of the original generation.** CARD-0086's automatic pipeline publishes the summary the instant GPSLogger stops, often before Joseph has gotten around to the Gaia-side manual step at all — the two are decoupled in time. So this can't be step N of the existing generation flow; it needs its own **insert-into-an-already-published-page** mechanism. Three candidate shapes, sequenced deliberately (2026-07-28) rather than picked upfront:

1. **Conversational (try this first)** — Joseph pastes the embed code to Claude in any session whenever he gets around to it ("here's the Gaia embed for the June 15 hike"); Claude finds that day's already-published HTML on the M8, inserts a new "Route Map" section, re-publishes. Zero new tooling — proves out whether the whole idea (does the embed actually look good, does the insert-into-a-published-page workflow feel worth it) is worth investing in before building anything.
2. **Tasker phone widget + new webhook route** — once the manual version has proven the idea is worth keeping, this removes the human-in-the-loop-with-Claude step: a home-screen shortcut/Quick Settings tile runs a Tasker Task that prompts for the hike date, reads the embed code off the clipboard (still copied from Gaia's website by hand — no way around that part), and `POST`s both to a new `/webhook/gaia-embed` route on the existing orchestrator (`app.py`), same shared-secret `?key=` auth pattern as `/webhook/hike-end`. Server-side, it does the same find-file/insert-section/rewrite/rebuild-calendar-index work option 1 does by hand, just triggered by a phone tap instead of a conversation.
3. **Dedicated CLI script** — `add_gaia_embed.py --date <date> --embed-code <code>` run over SSH. Considered and effectively superseded by option 2 once a phone-side trigger exists; would only make sense if the Tasker route turns out not to fit for some reason.

**Deliberately building option 1 before option 2/3** — proving the concept manually first means not building phone-side tooling for something that might turn out not to be worth doing regularly once actually seen on a real page.

**Manual trial run 2026-07-28 (option 1) — real embeds patched into 2 already-published pages.** Joseph got real embed codes from gaiagps.com for both existing summaries (`2026-06-18`, `2026-07-23`) and pasted them in; patched a new "Route Map" `<section>` into each page's HTML (inserted right after the stat-row hero, before Weather Forecast — centered `.map-embed` wrapper, Gaia's own inline iframe styles left untouched, just given the same rounded/shadowed card framing as the rest of the page), re-published both to the M8, verified live via `curl` (embed markup present, pages return `200`). Same trial also caught and fixed a real data bug: `2026-07-23`'s calendar manifest (CARD-0092) had been backfilled `hike_confirmed: true` from a session-memory assumption, but that page's own content says GPS confirmation actually failed that day (CARD-0087) — corrected to `false`, calendar rebuilt, now shows correctly as `cal-day--not-confirmed`.

**Zoom-level scare, resolved as a one-off loading glitch, not a real limitation.** Joseph initially reported the `2026-06-18` embed opening at a continent-level zoom, needing many manual zoom-ins to see the route — matched a Gaia GPS help-center report (Feb 2021) describing the same behavior on their track/route detail pages, acknowledged by a Gaia rep as a bug at the time. `2026-07-23`'s embed looked correct from the start, which didn't fit a universal-bug explanation. **Resolved:** reloading the `2026-06-18` page fixed it — looked fine on the second load. So this was a transient first-load hiccup (on Gaia's end, nothing wrong with the embed code or how it's inserted), not a systemic platform limitation or anything track-size-correlated. Doesn't rule out an occasional bad first load in general, but isn't the dealbreaker it initially looked like — the "zero-engineering, looks native" case for this card over CARD-0082 stands.

**Also not yet confirmed:** whether the embed includes Gaia's real interactive elevation-hover-sync (their own app has it; unclear whether the public embed replicates it, versus just a static map + separate stats).

**Not yet done:** decide whether to move to option 2 (Tasker phone widget + webhook route) now that option 1 has proven the idea out on 2 real hikes, or keep using the manual/conversational path for now since it's working fine. **Done when:** that decision is made and, if option 2 is wanted, it's built and verified with a real phone-triggered embed insert.

**Resolved 2026-07-29, decided (Joseph):** option 2 (a bespoke Gaia-specific Tasker/webhook route) won't be built as its own thing — CARD-0112's two-step generation redesign (staging directory + conversational trigger) is the general mechanism this card was reinventing a narrower version of. Once CARD-0112 lands, "paste a Gaia embed and trigger a rich regeneration" is just one instance of the same staged-resources + step-2 pattern every enrichment source uses, not a special case needing its own webhook. Option 1 (conversational, proven on 2 real hikes) stays as the model going forward, formalized by CARD-0112 rather than superseded by it.

**Related:** CARD-0082 (the heavier custom-render alternative, still available as a fallback), CARD-0088 (HTML hosting this patches into), CARD-0086 (automatic triggering, the source of the timing/decoupling problem above), CARD-0092 (calendar home page, same `srv/` directory this patches files within, and the manifest bug this trial caught), CARD-0112 (the two-step redesign that generalizes this card's option 1 into the standard staging/trigger pattern for every enrichment source).

---

### CARD-0086 · [idea] [hike-izer] Automatic triggering — RESOLVED 2026-07-28
**Status:** Done

**Notes:** Raised 2026-07-23, split out of CARD-0074 (Hike-izer v2, superseded) as an individually-tracked feature. V1 is on-demand only (Joseph explicitly invokes a summary for a specific hike). This card is about detecting that a hike happened/finished and generating the summary automatically — needs a trigger mechanism decision (e.g. GPSLogger track completion, hiking-monitor's own wake/sleep pattern signaling a finished hike, a scheduled check) not yet made.

**Moved to Build 2026-07-24, now that CARD-0088 (Done) gives the M8 a real public HTTPS endpoint to receive the webhook.** Full implementation plan finalized this session — two-stage build: (1) Tasker trigger → webhook receiver on the M8, logging only, proves the field-verification risk (does GPSLogger's broadcast actually reach Tasker); (2) the generation pipeline itself (Python templating for all mechanical output + one narrow Claude API call for just narrative prose). New component: `components/hike-izer-orchestrator/`, joins `hike-izer-web`'s compose project, reachable at `https://photo-server.tailfe828a.ts.net/webhook/hike-end` via a new Caddy `reverse_proxy` route (no second Funnel port). Shared-secret query-param auth, same pattern as the existing Apps Script `key=`.

**Day/date handling — never assume Arizona.** A hike could happen anywhere Joseph is carrying his phone, not just at home, so (caught before build started) the webhook payload carries the phone's own local date/time and UTC offset (Tasker's local-clock variable) rather than the receiver inferring or hardcoding Arizona time. Every rendered timestamp in the output is presented in that local time and explicitly labeled as local.

**Requires Joseph:** create an Anthropic API key (Claude Console — account/billing action, can't be done on his behalf; confirmed 2026-07-24 none exists yet), build the Tasker profile on his phone, trigger a real GPSLogger stop to prove the trigger fires end-to-end.

**Stage 1 (trigger + connectivity) built and verified 2026-07-24.** New component `components/hike-izer-orchestrator/` (`app.py`, stdlib-only, matching `fetch_hike_data.py`'s convention) deployed as a second service in the `hike-izer-web` compose project on the M8 — shares that project's Docker network, reachable from Caddy by service name, no second Funnel port. Caddyfile got a `handle /webhook/*` route proxying to it. Shared-secret auth via `?key=` query param (`WEBHOOK_SECRET`, generated fresh, in `credentials.local.md` + the M8's `.env`). Verified live against the real public URL (`https://photo-server.tailfe828a.ts.net/webhook/hike-end`): correct secret + `stopped` event → 200, logged; wrong/missing secret → 401; `started`/`fileuploaded` → 200, logged-and-ignored. Existing static-file listing on the same domain confirmed still working after the Caddyfile change. `photo-server-heartbeat.py` extended to check `hike-izer-orchestrator`'s container health too (own `HEALTHCHECK`, `python3`/`urllib` against `/health` — no extra package); installed on the M8 and confirmed via a real run: `Heartbeat sent. status=online`.

**Payload contract simplified 2026-07-24, after checking Tasker's actual variables (not guessed).** `%TIMES` is Unix epoch seconds, not a local-time string — confirmed via `hiking-monitor-claude-code-instructions.md` Step 24 and Tasker's own docs. Rather than three separate local_date/local_time/utc_offset fields (error-prone to string-concatenate correctly in Tasker's UI), the webhook now takes one `local_datetime` field: a full ISO 8601 string with UTC offset (e.g. `2026-07-24T14:32:10-07:00`), built by Tasker's "Parse/Format Date and Time" action (`yyyy-MM-dd'T'HH:mm:ssZZ`, Joda-Time format) — one unambiguous field, parseable via Python's `datetime.fromisoformat`. Full Tasker profile build steps (Task + Event/Intent-Received Profile, mirroring CARD-0007's HTTP POST pattern) written into `components/hike-izer-orchestrator/README.md`.

**Stage 1 fully verified end-to-end 2026-07-24, real phone event confirmed.** After the adb decisive test (above) proved Tasker/Android broadcast reception works fine, a subsequent real Start/Stop in GPSLogger's own UI finally produced a real broadcast — received cleanly: `{"gpsloggerevent": "stopped", "filename": "20260724", "startedtimestamp": "1784939105391", "duration": "8", "distance": "0.0", "local_datetime": "2026-07-24T17:25:14-07:00"}`. Whatever was blocking GPSLogger's broadcast in the earlier attempts (root cause not conclusively identified — possibly transient app/service state, possibly related to enabling GPSLogger's own debug-to-file logging in between attempts) resolved itself; the full chain (GPSLogger → Tasker Task → webhook → orchestrator) is now proven working with a genuine phone-triggered event, not just synthetic curl/adb tests. Stage 1 is done-done. Stage 2 (generation: Python templating + the narrow Claude API call) not started.

**Stage 2 (generation) built and verified end-to-end 2026-07-24.** New modules in `components/hike-izer-orchestrator/`: `templating.py` (mechanical Markdown/HTML builder, direct port of `html-template.html`'s field mapping — unit-tested locally against both the `hike_confirmed: true` and `false` paths, plus a photos-manifest case), `narrative.py` (one Claude API call, `claude-opus-4-8`, `messages.parse()` + `output_format` for structured `{"narrative_paragraphs": [...]}`, system prompt built from the deployed `SKILL.md` copy read at call time), `generation.py` (orchestrates `fetch_hike_data.py`/`fetch_hike_photos.py` as subprocesses, then templating + narrative, writes straight into `srv/`), `mqtt_log.py` (`jctsh/hike-izer/publish/log`, same connect/publish pattern as `photo-server-heartbeat.py`). `app.py` now runs generation in a background thread so Tasker's HTTP timeout doesn't fire while the pipeline (which can run well past 10s) is still working. Orchestrator switched from a bind-mounted stock image to a real `Dockerfile` build (needs `anthropic`/`paho-mqtt`, unlike stage 1's stdlib-only design); `srv` volume changed to read-write for the orchestrator so generation writes directly into what `web` serves, no `scp` step.

**Real bug found and fixed during verification: query-window boundary.** Initial local-testing against a real day (2026-06-18, chosen because a reference doc already exists to compare against) surfaced a genuine discrepancy — a wrong first attempt (mis-diagnosed, then correctly fixed) around whether the fetch window should be bounded by the hike's own local UTC offset or a hardcoded `Z`. Resolved: **bounding by the hike's own local offset is correct** — it's what makes SKILL.md's manual "does this GPS session actually belong to the previous local day" judgment call unnecessary in the automated path, since a session that only *looks* cross-midnight in UTC-Z terms (e.g. an evening session in a DST-observing location) is naturally excluded by a correctly-local-bounded window, no reattachment logic needed. Confirmed live: New Mexico trip data (real coordinates near Elephant Butte/Truth or Consequences — Claude's narrative correctly named the real location from GPS coordinates, not a hallucination) using the correct `-06:00` MDT offset (New Mexico observes DST, unlike Arizona) correctly included only the true local-June-18 session and excluded the prior evening's, matching the interactively-authored reference doc's own manually-curated result — with the added benefit that the automated version required no manual curation to get there.

**Second bug found and fixed:** the coverage panel's "gaps over 6 minutes" note rendered raw UTC timestamps instead of local time — missed in the initial build despite the observations table already converting correctly. Fixed (`templating.py`'s `coverage_notes()` now takes `offset_delta`/`offset_str`), verified via a targeted test.

**Verified live on the M8, 2026-07-24:** real webhook-triggered generation for 2026-06-18 (correct offset) produced accurate Markdown/HTML matching the reference doc's actual content (improving on it — correctly excludes the misattributed evening session), with photos correctly fetched and embedded, published to the live public URL (curl confirms `200`). This intentionally overwrote the live `2026-06-18_hike-summary.html` (originally from CARD-0083/CARD-0088's interactive generation) — kept, by Joseph's call, since the new version is more accurate.

**MQTT publish-visibility logging confirmed live 2026-07-24.** `hike-izer-orchestrator` Mosquitto account created on the Pi (`sudo mosquitto_passwd`, credentials in `credentials.local.md`). Test publish confirmed landing on the log dashboard (`http://raspberrypi.local`) — `hike-izer-orchestrator` now appears as its own component filter, `System`-category test message received and timestamped correctly in MST. Both stages of CARD-0086 are now fully built and verified end-to-end — nothing left blocking except real-world usage over time.

**Real GPSLogger stop never reached Tasker — extensive live debugging 2026-07-24, root cause narrowed but not yet fixed.** Joseph built the Tasker Task (`Hike-izer Webhook`: Date/Time Format action → `local_datetime`, then HTTP Post) and Profile (`Intent Received`, action `com.mendhak.gpslogger.EVENT`) correctly — confirmed via screenshots. A real Start/Stop in GPSLogger's Simple View produced zero events in Tasker's Run Log (confirmed clean — Run Log logging was verified actively recording other activity at the time). Ruled out, in order: wrong stop control (Joseph used GPSLogger's own Start/Stop Logging button, the correct one), Tasker battery restriction ("Allow background usage" already on), outdated Tasker (6.6.20, confirmed current), wrong/outdated GPSLogger (version 135, Dec 2025, matches current source). **Decisive test:** installed `adb` (Android platform-tools, via winget) on Joseph's Windows machine, connected his phone via USB (debugging authorization required several retries — stale auth state, needed "Revoke USB debugging authorizations" + reconnect with screen already unlocked before plugging in), then ran `adb shell am broadcast -a com.mendhak.gpslogger.EVENT --es gpsloggerevent stopped ...` to send the exact broadcast GPSLogger would send, from a genuinely different process. **This worked end-to-end** — Tasker caught it, ran the Task, POSTed correctly, receiver logged a clean `stopped` event with correct `local_datetime`. This proves the entire chain (Tasker → webhook → orchestrator) is correct and that Android/Tasker can receive cross-app broadcasts fine on this phone — the remaining problem is narrowly that **GPSLogger itself isn't sending the broadcast** when Start/Stop Logging is tapped in its Simple View screen, despite `GpsLoggingService.java`'s `notifyByBroadcast()` being unconditional in the reviewed source. Next diagnostic step: check whether GPSLogger has its own debug/view log (would show whether it even attempted the broadcast) and whether Simple View's controls go through the same code path as the full app.

**Blocking dependency, corrected 2026-07-24 (same stale carry-over already fixed on CARD-0084):** CARD-0074's blanket "hiking-monitor device needs to be operational" note doesn't actually apply here either — triggering off GPSLogger or the Hiking Observations pipeline is phone-based, entirely independent of the ESP32 hiking-monitor device. No real blocker.

**Candidate trigger mechanisms considered 2026-07-24, while scoping CARD-0083's sibling need (hike-*start* detection):**
- **Explicit "end of hike" phrase match** (via the Hiking Observations pipeline, CARD-0007) — real precedent exists (today's actual hike literally ended with the observation "end of hike"), but depends on Joseph remembering to say it every time; if he doesn't, the trigger silently never fires.
- **GPS-session-based absence detection** (no new GPS point for N minutes) — doesn't depend on Joseph saying anything, but needs polling/a scheduled check rather than a clean event, has inherent lag (waiting out the N-minute window), and risks a false positive from a temporary GPS dead zone (canyon, dense tree cover) that isn't really the hike ending.

**Leading candidate, found 2026-07-24 — GPSLogger's own native start/stop broadcast, via Tasker.** GPSLogger (the Android app already used for the GPS Track pipeline, `com.mendhak.gpslogger`) broadcasts a native Android event whenever logging starts or stops (`com.mendhak.gpslogger.EVENT`), confirmed via its own documentation: *"GPSLogger sends a broadcast start/stop of logging... which you can receive as an event"* in Tasker. This beats both candidates above:
- Fully automatic — tied to something Joseph already reliably does (stopping GPSLogger when the hike ends), not a new verbal habit to remember.
- Immediate, no lag — fires the instant logging actually stops, not after an inferred timeout, and no false-positive risk from a temporary signal dead zone.
- Reuses proven infrastructure, not new territory — Tasker already fires an HTTP POST to the same Apps Script for the "Log Observation" task (CARD-0007, Steps 24-26 in `hiking-monitor-claude-code-instructions.md`). This would be a second, small Tasker profile copying that same pattern: trigger on "Intent Received" for GPSLogger's stop broadcast, action: HTTP POST to a hike-end endpoint.

**Confirmed 2026-07-24 (GPSLogger source + FAQ):** action `com.mendhak.gpslogger.EVENT`, extras `gpsloggerevent` (`"started"`/`"stopped"`/`"fileuploaded"` — one action string for both, distinguished by this field), `filename`, `startedtimestamp`, `duration`, `distance`. Tasker branches on `%gpsloggerevent` = `stopped`; `started`/`fileuploaded` logged and ignored.

**Invocation architecture — how the trigger actually produces a summary, researched 2026-07-24.** The trigger above only gets an HTTP POST to *some* endpoint when a hike ends. That endpoint has to actually run Hike-izer's narrative-writing step (currently `.claude/skills/hike-izer/SKILL.md`, only ever invoked by Joseph inside an interactive Claude Code session) with nobody watching. That's the real "does this need an agent?" question, and the answer is **no, not in the heavyweight sense** — reasoning below.

Note on "Cowork": not a current Anthropic product name I recognize — didn't want to fabricate an answer around it. The real menu of options for calling Claude programmatically:
- **Claude API — a single Messages API call** (or a short tool-use loop). You write the plumbing; Claude answers one well-scoped request.
- **Claude API + tool use (Tool Runner or manual loop)** — for when Claude itself needs to decide what to fetch/call across multiple steps.
- **Claude Agent SDK** (`claude-agent-sdk`) — Claude Code itself, packaged as a library: built-in Read/Write/Edit/Bash tools, the full agent loop, hooks, subagents. The closest thing to "run the Hike-izer Skill unattended, exactly like Joseph running Claude Code interactively."
- **Managed Agents (Claude's hosted agent platform)** — Anthropic runs the agent loop *and* hosts the sandbox container the agent's tools execute in; you create a persisted Agent config once, then fire Sessions (event-driven, or on a cron schedule via Deployments).

**Recommendation, refined 2026-07-24: skip the agent frameworks entirely and use one narrow Claude API call.** Hike-izer's actual pipeline (`fetch_hike_data.py` → `fetch_hike_photos.py` → write Markdown/HTML) is already a deterministic sequence of existing Python scripts. **New realization:** most of the *output* itself is also fully mechanical — the hero stat row, data tables, full observations log, coverage panel, and weather forecast cards are all direct field-to-template mappings with zero creative judgment. Only the narrative story (SKILL.md step 4a) genuinely needs an LLM. So the build splits cleanly: a Python templating module handles 100% of the mechanical output (a direct port of `html-template.html`'s existing mapping), and **one** Claude API call (`claude-opus-4-8`, structured output via `output_config.format`) returns just `{"narrative_paragraphs": [...]}`. Smaller, cheaper, more reliable than asking Claude to produce full HTML — still squarely the "classification/summarization/extraction" tier, not agent territory.

**Where this orchestrator lives — ties to CARD-0088 (Done).** Reuses CARD-0088's existing Tailscale Funnel URL via a new Caddy `reverse_proxy` route (`/webhook/*`) rather than exposing a second port — see the architecture note above.

**Logging/MQTT visibility becomes possible here, not before (noted 2026-07-24 during CARD-0088 build).** CARD-0088 explicitly skips a per-publish MQTT log line for its `scp`-based deploy step, because that step runs on Joseph's Windows machine, which has no MQTT-publish capability and adding one would mean a new pip dependency for a one-off script. Once this card's orchestrator exists and lives on the M8 (a Linux host with local broker access, same as every other JCTsh MQTT publisher), that constraint goes away — the orchestrator is the natural place to add real dashboard visibility (`jctsh/hike-izer/publish/log` on a successful auto-generated summary, `Alert`-category on a failure) using the same pattern already established for the backup script and scheduled-reboot notifications. Built in from the start here.

**Real-world usage confirmed repeatedly since 2026-07-24 — closing out.** The card's own 2026-07-24 status already said "nothing left blocking except real-world usage over time"; it just never got formally moved. Since then: CARD-0092 (calendar home page) was closed specifically on "automatic path confirmed on a real hike," and the entire 2026-07-28 Ottawa Hills hike (CARD-0107/CARD-0108/CARD-0109 testing) ran through this exact automatic GPSLogger → webhook → orchestrator pipeline with no manual invocation.

**Related:** CARD-0073 (Hike-izer v1, Done), CARD-0074 (superseded), CARD-0083 (sibling trigger-mechanism need, opposite end of the hike, Done), CARD-0007 (Hiking Observations pipeline — the phrase-match fallback and the Tasker HTTP-POST pattern the leading candidate copies), CARD-0088 (hosting, Done — this card's webhook route lives on that Funnel URL), `components/hiking-monitor/gps-pipeline.md` (GPSLogger app details), `components/hike-izer/fetch_hike_data.py`, `.claude/skills/hike-izer/SKILL.md` (the narrative-writing instructions this card's orchestrator calls Claude with).

---

### CARD-0098 · [enhancement] [traveling-lights] Randomized/staggered occupancy-simulation lighting while traveling — RESOLVED 2026-07-28
**Status:** Done

**Raised 2026-07-25**, prompted by Joseph asking how feasible an HA lights-while-traveling automation would be, then asking to build it now. New HA-only component, `components/traveling-lights/` (README.md + CLAUDE.md), following the `garage-presence` precedent for HA-only components with no hardware.

**Design went through five rounds before landing:**
1. First cut controlled all 5 entities (`light.overhead_light`, `switch.kitchen_overhead`, `light.nook`, `light.pendants`, `light.chandelier`) via a single `homeassistant.turn_on`/`turn_off` at one randomized time per night.
2. Joseph flagged the real flaw: all 5 are in the same room, so firing them simultaneously looks like a single master-switch flip regardless of how random the clock time is — not real occupancy behavior. **Fix:** each light gets its own random 1–5 min delay and the firing order is shuffled fresh every run (`| shuffle` + `repeat: for_each`).
3. Joseph asked how he'd know it actually ran while traveling, with no lights dashboard to check. **Fix:** both action automations end with a push notification (both Pixels) stating the fire time and which lights were turned on/off — same pattern as CARD-0036 (scheduled-reboot notifications) and front-porch-temp-sensor's threshold alerts.
4. Joseph noted the household normally turns lights on before full dark, not at a fixed clock time — and Tucson's real sunset swings ~5:25pm (Dec) to ~7:35pm (Jun), so a fixed window would look wrong most of the year. **Fix:** on-time is now `sun.sun`'s `next_setting` + a random 0–35 min offset, computed fresh each night. Off-time stays a fixed 10:00–11:30pm window (bedtime doesn't track the seasons).
5. After live-testing the two-automation design, Joseph asked why two switches were needed instead of one, and separately asked to drop `light.overhead_light`/`switch.kitchen_overhead` (down to 3 entities: nook, pendants, chandelier). **Fix:** merged "Evening On"/"Night Off" into a single **Traveling Lights** automation — two triggers tagged `id: 'on'`/`id: 'off'`, a `choose:` block runs the matching branch. One entity, one toggle, both directions.

**How it works:** "Traveling Lights - Randomize Daily Times" (always enabled) runs nightly at 3am, writing tonight's on-time (sunset-relative) and off-time (fixed window) into two `input_datetime` helpers. The single **Traveling Lights** automation (disabled by default) fires at whichever time comes due, staggers the 3 entities in a shuffled order with random per-light delays, then pushes a confirmation notification. Toggling that one automation (Settings → Automations → search "traveling") is the full "traveling mode" switch.

**Status: deployed 2026-07-25, partially live-verified.** Both `input_datetime` helpers created by Joseph via Settings → Devices & Services → Helpers → Date and/or time (Time-only). `automations.yaml` deployed to the Pi and reloaded four times as the design evolved — confirmed live each time via the HA API. Manually triggered the randomizer directly against real `sun.sun` data: actual sunset was `19:27` local, computed on-time landed at `19:33` (6 min after sunset, inside the intended window) — confirms the sunset-relative calc is correct against real data. Live-tested the pre-merge 5-entity/2-automation design end-to-end: enabled Evening On with a near-future test time, confirmed `light.overhead_light`, `light.pendants`, and `light.chandelier` actually turned on at staggered (non-simultaneous) times, exactly as designed.

**Real finding from the merge deploy:** the automation was still mid-run (`current: 1`) when the round-5 merge was reloaded — its manually-toggled `on` state reset to `off` afterward, unlike the three earlier reloads (which were minor content edits and preserved toggle state). Documented in `CLAUDE.md` as a practical rule: minor tweaks preserve the toggle across a reload, but a reload that restructures triggers/`choose:` logic under the same automation `id` may not — always re-check after any structural reload.

**Cosmetic-only leftovers from the merge (documented, not blocking):** the merged automation kept the old entity ID `automation.traveling_lights_evening_on` (HA doesn't re-slugify entity IDs to match a changed alias) even though it's now named "Traveling Lights" and covers both directions. `automation.traveling_lights_night_off` is now an orphaned `unavailable` entity — safe to delete via Settings → Entities, or ignore.

**Full on+off run confirmed live 2026-07-26/27 (pre-trim, 3 entities):** on-branch triggered 19:35:22 local, chandelier/pendants/nook fired at 19:38/19:41/19:42 (staggered ~1–3 min apart, matching the 1–5 min per-light delay design). Off-branch triggered 22:02:00 local (inside the 22:00–23:30 window), same 3 lights turned off at 22:06/22:10/22:12. Confirms the merged single-automation `choose:` structure works correctly for both directions — verified via HA `/api/logbook` rather than Joseph watching the house live.

**Round 6 — 2026-07-27, prompted by Joseph reviewing the verified run:**
1. Noticed the push notification's light list was raw entity IDs (`light.chandelier, light.pendants, light.nook`) instead of readable names. **Fix:** added a `lights_names` variable (`lights_order | map('state_attr', 'friendly_name') | join(', ')`) and pointed both notification templates at it — messages now read e.g. "Turned on: Nook, Pendants."
2. Asked to drop `light.chandelier` — down to 2 entities: `light.nook`, `light.pendants`.
3. Asked why the automation was found disabled despite having been manually enabled and live-tested the night before. **Root cause:** the Pi's pre-existing weekly `scheduled-reboot.timer` (CARD-0036) fired at 03:00 local on 2026-07-27, restarting Docker → the `homeassistant` container (confirmed via `docker inspect` StartedAt + HA's own "stopped"/"started" logbook entries 3 min apart). The automation's `initial_state: false` key forces that *specific* state on every HA startup — not just first-ever load with no registry entry, as CLAUDE.md previously (incorrectly) documented from the round-5 reload finding. **Fix:** removed `initial_state: false` entirely, so HA now restores whatever the toggle was last set to across any restart, including future scheduled reboots.

**Status: deployed and re-enabled 2026-07-27, 2-entity/friendly-name version armed for the night's live cycle** (on/off times randomized for that day: ~19:58/22:14 local).

**Closing criteria confirmed 2026-07-28.** The natural overnight cycle (2026-07-27 evening → 2026-07-28 early morning) ran on its own, verified via HA `/api/logbook`:
- On-branch triggered 19:58:41 local (exact match to the randomized on-time) — Pendants on at 20:01:47, Nook on at 20:03:47 (staggered, ~2 min apart).
- Off-branch triggered 22:14:00 local (exact match to the randomized off-time) — Pendants off at 22:15:06, Nook off at 22:17:06 (staggered, ~2 min apart).
- No `unavailable`/error states in this window. (a) staggering confirmed via logbook, (b) friendly names in the push notification confirmed by Joseph directly.

**Automation left enabled, not disabled — correcting an assumption caught by Joseph 2026-07-28.** The original closing note said "disable again until an actual trip," carried forward from stale text in an earlier scheduled check-in task rather than a live confirmation of travel status. Joseph is on an active trip as of this closing, so the automation stays on.

**Related:** `components/garage-presence/` (the HA-only-component precedent this follows), `components/traveling-lights/README.md`, `components/traveling-lights/CLAUDE.md`.

---

### CARD-0105 · [enhancement] [hike-izer] Continuous improvement — running list of small Hike-izer enhancements — RESOLVED 2026-07-29 05:35 MST
**Status:** Done

**Raised 2026-07-28**, reviewing the calendar and the first real automatic-pipeline hike. Ongoing catch-all for small Hike-izer polish items, not a one-shot scoped feature — expect this list to grow over time as more real hikes surface things worth improving.

**Built and verified live 2026-07-28:**
1. **Removed all card-number references from user-facing output.** Fixed in `components/hike-izer/html-template.html` (subtitle + footer), `components/hike-izer-orchestrator/templating.py`'s `render_html()` (subtitle + footer), `components/hike-izer/build_calendar_index.py` (footer). Also found and fixed several more embedded in the 2 interactively-authored pages' actual prose (not just subtitle/footer) — a UV-sensor caveat citing `CARD-0065`, an enclosure/power-redesign note citing `CARD-0070`, and a whole callout paragraph built around citing `CARD-0087` by number — reworded each to keep the substance while dropping the tracking-number jargon. Re-published all 3 live pages (`2026-06-18`, `2026-07-23` from local copies; `2026-07-28` edited directly on the M8 since it only ever existed there, auto-generated) and rebuilt the calendar. Verified live via `curl`: 0 `CARD-` matches on all 3 pages except one internal CSS comment (not user-visible, left alone).
2. **Calendar home page: month-by-month navigation.** Rebuilt `build_calendar_index.py` to generate one static page per month with an entry (`calendar-<year>-<month>.html`), zero-JS throughout: Prev/Next are plain links between months that actually have data (not strict calendar-adjacency, so there's never a dead link), and the year picker is a native `<details>`/`<summary>` disclosure list linking each year to its most recent month. `index.html` is a copy of the latest month's page. Verified live: root serves July 2026 (correct, most recent), June page reachable, nav correctly disables Prev on the oldest month and Next on the newest, year picker present and correct.
3. **Calendar color meaning, clarified 2026-07-28 (not a bug, but genuinely undecided until now).** Joseph noticed July 23 lost its green highlight after today's publish and flagged it as a regression. It technically wasn't one — that was an intentional correction made earlier this same session (July 23's page content says GPS confirmation actually failed that day, CARD-0087, since fixed, even though a real hike happened) — but surfaced that the green/outlined distinction itself (`hike_confirmed: true` vs. a published-but-unconfirmed report) was a design choice Claude made and reported after the fact, never actually confirmed with Joseph. **Decided now:** green means **any day with a published summary**, full stop — not gated on GPS confirmation status. Simplified `build_calendar_index.py` accordingly: dropped the `cal-day--not-confirmed` style entirely, renamed the surviving one `cal-day--logged` to reflect the new meaning. The manifest file itself and its `hike_confirmed` field stay as-is (still useful data, just no longer drives calendar styling). Verified live: July 23 now renders `cal-day--logged`, matching every other published day.
4. **Investigated why today's real automatic hike produced no visible completion log — and fixed a real durability gap, 2026-07-28.** Joseph asked why the dashboard showed no "published" line for today's real hike. Extensive SSH forensics (container creation time, image build time, Caddy routing, docker daemon journal, systemd timers) initially pointed at several wrong theories in turn (stale Tasker URL, manual invocation during CARD-0107/0108 testing, a same-morning redeploy) — each ruled out in turn by direct evidence or by Joseph's own account. The real, confirmed answer: the automatic pipeline **did** work — a real completion log (`Published hike summary for 2026-07-28...`, 05:10:36 MST, ~33min after the hike's actual 4:37am local end) was found once the dashboard was re-checked properly. It was published by an orchestrator container instance that existed *before* a later same-morning rebuild (cause not fully identified) replaced it — meaning that instance's own local container logs, which would have shown the webhook receipt, were gone by the time this was investigated. **Real durability gap this surfaced:** `app.py`'s webhook-receipt logging only ever went to the container's own stdout/stderr, which doesn't survive a container replacement — there was no *durable* record that a webhook had even arrived, independent of whether generation succeeded. **Fixed:** `app.py` now publishes to the same MQTT `jctsh/hike-izer/publish/log` pipeline `generation.py` already uses — on every valid webhook receipt (any event type, not just `stopped`), on a rejected/unauthorized POST (`Alert` category — the one signal a fully-silent failure can't produce), and on the orchestrator's own startup (so a future container rebuild is itself visible on the dashboard, not silent). All fire-and-forget in a background thread so a slow/down MQTT broker never adds latency to the webhook response or delays startup. **Deployed and verified live 2026-07-28:** rebuilt and redeployed the orchestrator on the M8, confirmed the new startup line landed on the dashboard, then sent a real diagnostic POST and confirmed its receipt line landed too.
5. **Found and fixed a real dashboard-visibility gap while investigating #4, 2026-07-28 — not hike-izer-specific, but logged here rather than a new card.** The same-day completion log from item #4 was genuinely on the dashboard but missed on first look: `core/logging/log_server.py`'s `_entries` deque is a fixed-size `MAX_ENTRIES = 200` ring buffer, **shared across every JCTsh component, not per-component** — with ~6 components heartbeating every 15–60 minutes around the clock, that 200-entry window rolls over well within a day, silently pushing older one-off events (like a hike-summary publish) out of the visible dashboard, even though the full history is still safe in the underlying rotating file log (`/mnt/jctsh-logs/jctsh.log`, 5MB × 5 backups). **Fixed:** bumped `MAX_ENTRIES` 200 → 1000. Deployed to the Pi (`scp` + `sudo systemctl restart jctsh-logging`), confirmed live via the running service's own source file.

**Local unit tests before deploying:** synthetic multi-month/multi-year manifest sets confirmed correct month-page generation, `index.html`-mirrors-latest-month behavior, Prev/Next disabled-state at both ends of the range, year-picker links, and the empty-state page (zero summaries published).

**Ideas below outgrew this catch-all and moved to their own cards, 2026-07-28** (real design work + live experiments made them each substantial enough to need their own thread):
- **Answer questions captured in voice observations** + **provide history about the area** → CARD-0108 (all three layers now built and verified against a real hike: base + enrichment + regional-scope, woven into the narrative, Overpass reliability mitigated with retry+mirror-fallback, per-hike cost tracking added) — grounded external context.
- **Identify things in photos** → CARD-0107 (Done) — vision-based photo identification, captions on the photo grid.
- Also newly split off, discovered while scoping the above: CARD-0109 (Done) — tighten the narrative's non-redundancy rule (today's real narrative mostly restates the data tables in prose).

**Moved to Done 2026-07-29 05:35 MST** — all 5 listed items built and verified live; no open items remained. Follow-on findings from the July 29 hike now tracked separately in CARD-0111.

**Related:** CARD-0073 (Hike-izer v1, Done), CARD-0081 (HTML rendering, Done — the template this strips card-refs from), CARD-0086 (automatic triggering, Done — the orchestrator this strips card-refs from), CARD-0091 (HTML-only output, Done), CARD-0092 (calendar home page, Done — the page this reworks), CARD-0087 (the GPS-confirmation pipeline bug behind the "not a bug" item above), CARD-0111 (successor running-list card, seeded from the July 29 hike).

---

### CARD-0111 · [enhancement] [hike-izer] Iterative refinement resulting from hike of July 29 — RESOLVED 2026-07-29 07:37 MST
**Status:** Done

**Raised 2026-07-29 05:35 MST**, reviewing the July 29 hike's automatically-generated page. Successor to CARD-0105 (Done) — same running-catch-all shape, re-seeded from this hike's findings rather than closed out.

**Scope — items found on first review:**
1. **Bug, root cause confirmed 2026-07-29 05:44 MST — Immich upload-timing race, not a code defect.** This hike happened in East Grand Rapids, MI (offset handling correctly used `-04:00`, confirming CARD-0086's non-Arizona-hardcoded logic held up on a real out-of-state trip). Checked directly via SSH into the M8 and the orchestrator's own logs plus a live Immich `search/metadata` query:
   - `hike-izer-orchestrator` received the GPSLogger `stopped` webhook at **11:37:43 UTC** and ran `fetch_hike_photos.py` immediately, querying Immich for assets between 11:07:57–11:37:39 UTC. It found **0 assets** and correctly wrote an empty manifest — `fetch_hike_photos.py` itself did exactly what it's supposed to.
   - A direct Immich API query confirms **7 real photos** were taken during that exact window (11:10:34–11:33:09 UTC, all with correct GPS EXIF) — but Immich's own `createdAt` (upload/ingestion time) for every one of them is **~12:37 UTC**, roughly an hour *after* the hike ended and the query already ran.
   - Joseph confirmed Immich's "use cellular data" is enabled, but the phone likely still didn't actually push the backup until reconnecting to WiFi after returning home — a real, observed upload delay, not a settings bug.
   - **Conclusion:** the automatic pipeline runs the instant GPSLogger stops, but Immich's mobile backup can lag by up to ~1 hour depending on connectivity. `fetch_hike_photos.py` queries too early by design (it has no retry), not incorrectly.
   - **Further diagnosed 2026-07-29 06:15 MST:** a live Immich query showed all 7 photos landed within the same ~12-second upload burst, regardless of when each was actually taken — confirming this is Immich's own Android background-sync unreliability (documented upstream: uploads only fire when the app is opened/foregrounded), not a fixed delay or WiFi-arrival trigger. Delay is tied to whenever Joseph next opens Immich — unpredictable, not something a fixed retry window could reliably catch.
   - **Spun off to CARD-0112 (Done)** — the real fix isn't a targeted retry but a broader two-step generation redesign (automatic data-only publish, then a manually-triggered enrichment + narrative pass once photos/Gaia/bird data are actually staged). Closing this item here as diagnosed; tracked forward in CARD-0112.
2. **Fixed and verified live 2026-07-29.** Title changed to "Hike Summary for [date]" (e.g. "Hike Summary for July 29, 2026") in both `<title>` and `<h1>`, via `format_date_display()`.
3. **Fixed and verified live 2026-07-29.** Hero stat-row's first box now shows start time, end time, and duration together (new `hero_time_display()`), replacing the old separate "Date" + "Duration" boxes — the date moved to the H1 instead, so nothing was lost. Stat-row CSS changed from a fixed 4-column grid to `auto-fit`/`minmax` to handle the new 3-card row (Time, Distance, Elevation Gain) cleanly at any width.
4. **Confirmed working, no action needed:** weather forecast and automatic generation both worked correctly on this hike.
5. **Fixed and verified live 2026-07-29.** The Expected vs. Actual Data Coverage note was reworded from a vague "the requested window extends into the future" (technically true but reads like an anomaly) to name the actual generation-time cutoff plainly, e.g. "Expected-reading counts reflect data through 7:38 AM UTC-04:00 (when this summary was generated) -- the rest of that calendar day hadn't happened yet." Revisit once CARD-0113 lands (session-scoped queries shrink this to near-negligible magnitude) and once CARD-0112's step 1/step 2 split makes "incomplete on purpose" a first-class idea rather than something to caveat inline.
6. **Fixed and verified live 2026-07-29.** GPS Trackpoints (sessions) row no longer hardcodes Expected/Coverage to "not available" — `coverage_table_rows()` now sums `expected_points` across every detected session (hike or rejected) to match `total_trackpoints`, same shape as the Environmental Data row above it (e.g. real July 29 output: 59 expected / 61 actual / 103.4%).
7. **Handled without touching the live page.** Reviewed the real narrative in detail (471 words) with Joseph: weather/sensor-empty/walking-pace restatement, over-length landmark trivia disproportionate to a 30-min walk, and a real accuracy bug (a *different* day's landmark got the spotlight — see CARD-0112 item 6) all came up. Folded into `SKILL.md`'s narrative rules: ~250-word target, tightened non-redundancy rule (weather table and empty-data cases explicitly covered, GPS-confirmation commentary cut), sun-position/route-shape downgraded to optional color, and a new "weight space by route-centrality, not research depth" rule. Deliberately did **not** regenerate the live July 29 narrative — a fresh `narrative.py` + `place_context.py` call there would cost real money for a page that'll likely be superseded once CARD-0112's two-step model lands anyway (narrative would move to step 2, with richer inputs than were available today).

**Deployed live 2026-07-29 07:37 MST, zero additional API cost:**
- The real `2026-07-29_hike-summary.html` was re-rendered locally from the already-fetched `hike_data.json` and the *existing* narrative text (reused verbatim, no new Claude call) through the fixed `templating.py`, then pushed into the M8's `srv/` directory — items 2/3/5/6 are live on the actual page, without spending anything on items 1 or 7.
- `templating.py` and `SKILL.md` were deployed into the orchestrator's own Docker image (rebuilt + recreated on the M8) so every future automatic hike picks up all of the above — this also caught a real gap along the way: the container's baked-in `SKILL.md` copy was stale (356 lines vs. the repo's 393), meaning tonight's narrative-rule refinements wouldn't have applied to any future hike without this redeploy.

**Related:** CARD-0105 (the predecessor running-list card this succeeds), CARD-0112 (item 1's photo-timing fix and the item-7-adjacent `named_features` accuracy bug both tracked forward here), CARD-0113 (session-scoped generation, sequenced ahead of CARD-0112), CARD-0086 (automatic triggering), CARD-0084 (photo fetch/gallery pipeline — confirmed working correctly; the bug is upstream timing, not this script), CARD-0104 (the Gaia-embed "patch a published page later" precedent CARD-0112's fix follows), CARD-0110 (richer route/speed stats the narrative now deliberately defers to).

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

**Raised 2026-07-28**, split out of CARD-0105's unscoped "identify things in photos" idea after real design work and a live experiment.

**Purpose:** identify wildlife, plants, landmarks, or named facilities/signage that are the clear focal point of a photo, as a short caption on the photo grid. Explicitly does NOT force an identification of incidental background elements (e.g. a tree species visible behind an unrelated sign) — if a photo is self-explanatory or nothing is confidently identifiable, the caption is empty, not a guess nobody asked for.

**Real experiment, 2026-07-28** (3 real photos from today's hike, Claude Opus 4.8, `messages.create` with base64 images): Immich's `?size=preview` thumbnail (1913×1440, ~3,676 input tokens, ~$0.018/photo) gave identical species-ID quality and confidence to the full-res original (4080×3072, downscaled to Opus 4.8's high-res cap, ~4,828 tokens, ~$0.024/photo) on all 3 photos. **Default to `thumb`** — ~24% cheaper, no observed quality loss. (Smaller saving than a naive "downsize aggressively" assumption would suggest — Immich's real preview resolution is already close to Opus 4.8's native cap, so there isn't much headroom left to trade away.)

**Prompt design correction (same experiment):** an unqualified "identify any notable plants/wildlife/landmarks" prompt forced an ID of a background pine species behind an Ottawa Hills HS sign photo — not useful, and exactly what the focal-point rule above exists to prevent. Any implementation needs that qualifier explicit in the prompt, not implied.

**Scope expansion, 2026-07-28 (Joseph):** vision's job here isn't only species ID — it should also read/recognize named facilities and institutional signage in-frame (e.g. a public outdoor fitness course installed by a city parks department, a school's own sign). Those identified names become the anchor for CARD-0108's scoped-search enrichment layer — a photo ID feeding a targeted lookup, not two disconnected features. See CARD-0108 for the specific fitness-course and Ottawa Hills examples this pairing was raised against.

**Architecture, resolved 2026-07-28 (Joseph):** photo IDs become **per-photo captions on the photo grid, not prose folded into the narrative.** Decouples this entirely from `narrative.py`'s call — no combined-call-vs-pre-pass tradeoff to make, since captioning doesn't feed `hike_data.json` or the narrative prompt at all. A per-photo step attaches its output to the photo manifest; `templating.py`'s photo-grid section renders it. Two direct wins from this shape: (1) a caption is inherently scoped to "what's in this picture," so it can't drift into the same restatement problem CARD-0109 targets in the narrative text; (2) every photo currently renders with `alt=""` (confirmed against today's real output) — captions double as real `alt` text, fixing actual accessibility as a free byproduct, not just adding a visible label.

**Built 2026-07-28:**
1. `components/hike-izer-orchestrator/photo_captions.py` (new) — `caption_photos(photos_manifest, photos_dir, api_key)`, one vision call per image asset against its `thumb` file, structured output so "nothing identifiable" comes back as a clean empty string rather than a forced guess. A captioning failure on one photo logs and continues rather than blocking the rest of the gallery (same principle as CARD-0084's photo-fetch and CARD-0083/CARD-0106's forecast capture).
2. `generation.py` — calls it right after photo fetch, before narrative generation.
3. `templating.py` — photo `<img>` tags now use the caption as real `alt` text (was `alt=""` on every photo, confirmed against real output).

**Caption/sign_text split, 2026-07-28 (Joseph):** a caption that just transcribes text already legible in the photo is redundant with what the photo itself shows — the same restatement problem CARD-0109 targets, in a new shape. Split the vision output into two fields: `caption` (shown to the reader, only for genuine non-textual identification — species, wildlife) and `sign_text` (not shown — raw transcription of any sign/plaque, captured as search-query material for CARD-0108). On the school-sign photo this took the caption from a lossy 12-word paraphrase down to correctly empty, while `sign_text` captured the full text: *"OTTAWA HILLS HIGH SCHOOL. GRAND RAPIDS PUBLIC SCHOOLS. GRPS my choice. Cherry Health Walk-ins welcome. GALAXY"* — real search material a caption could never hold. Same on the fitness-court sign: *"...NATIONAL FITNESS CAMPAIGN - EST. 1979 - FITNESS COURT... Parks and Recreation - CITY OF GRAND RAPIDS... Campaign Partner Since 2022. Priority Health for good..."*.

**Bug found and fixed by this same test:** `max_tokens=100` (tuned for caption alone) truncated mid-JSON-string on the two busiest signs once `sign_text` was added, failing to parse — caught by the existing failure handling (logged, degraded to empty, didn't crash the pipeline) but silently losing exactly the data this field exists to capture. Raised to `max_tokens=400`; re-verified clean on all 7 real photos, no truncation.

**Verified against all 7 of today's real photos** (two full passes — initial design, then the caption/sign_text split): focal-point rule held throughout, species IDs correct (`"Trumpet vine (Campsis radicans) in bloom"`, two distinct Rose of Sharon captions), one photo correctly returned empty on both fields (nothing identifiable), and both sign-bearing photos now yield rich `sign_text` instead of a lossy caption.

**Visible caption display, built and confirmed 2026-07-28:** Joseph's call — caption below the thumbnail, always reserving the space (even when empty) rather than a per-row-conditional treatment, which isn't practical on this responsive `auto-fill` grid without JS (row membership shifts with viewport width; this project avoids JS elsewhere, e.g. the zero-JS calendar pages from CARD-0092). `.photo-item` changed from a plain square `<a>` to a flex column (image + `.photo-caption` span with a fixed `min-height` so every tile stays equal height regardless of caption content); videos get an empty caption span too, for the same alignment reason. Rendered against real data (today's 7 real photos, real hike_data) and checked live in a browser via a local preview server — **Joseph confirmed the result directly ("Looks great to me")** after the in-session Chrome-automation screenshot attempts failed repeatedly and were abandoned in favor of a manual look.

**Related:** CARD-0105 (the unscoped idea this splits out of), CARD-0108 (the search-enrichment layer this hands named subjects to — now with a real example), CARD-0084 (the photo fetch/gallery pipeline this builds on, `fetch_hike_photos.py`'s `thumb`/`original` manifest fields).

---

### CARD-0092 · [idea] [hike-izer] Calendar view on a home page, clickable through to hike summaries — RESOLVED 2026-07-28
**Status:** Done

**Raised 2026-07-24.** A calendar showing which days had a confirmed hike — visually marked, clickable through to that day's `hike-summary.html` page.

**Interview before building, three open questions resolved with Joseph:**
1. **Data source:** a small sidecar `<date>_hike-summary.meta.json` (`{"hike_confirmed": true/false}`) written by both publish paths alongside their HTML, read by the calendar-builder — chosen over scanning/parsing HTML content. This turned out to matter for a real correctness reason found during planning: CARD-0100 made the *automatic* pipeline skip publishing entirely on unconfirmed days, but the *interactive* Skill still publishes a page saying "couldn't confirm a hike" when Joseph explicitly asks about a day — a naive "file exists = hike happened" scan would have wrongly marked those interactive-only unconfirmed days as hikes.
2. **Rebuild trigger:** after every publish, both paths — no manual step to remember, no drift.
3. **UI:** plain CSS grid, zero JS — matches `html-template.html`'s existing no-`<script>`-anywhere philosophy.

**Built:** new `components/hike-izer/build_calendar_index.py` (stdlib only) — scans a served directory for `*.meta.json` sidecars, groups by year/month, renders a reverse-chronological calendar grid (confirmed-hike days highlighted + linked, published-but-unconfirmed days outlined + linked, everything else plain) to `index.html`. Reuses the same CSS custom-property color system as `html-template.html` (copied variables, not a shared file, since this page has exactly one generator unlike the per-hike template's "consistency across independently-authored runs" concern). Grid uses `repeat(7, 1fr)` + `aspect-ratio: 1/1` so it reflows to any screen width without a breakpoint — deliberately kept at 7 columns on mobile too, unlike the stat-row's 4→2 breakpoint, since collapsing a calendar's day-of-week columns would break its meaning.

**Wired into both publish paths:**
- `generation.py` (automatic): writes the `.meta.json` (always `hike_confirmed: true` here, since CARD-0100's gate already returned early otherwise) and calls `build_calendar_index.py` via subprocess, same pattern as its existing `fetch_hike_data.py`/`fetch_hike_photos.py` calls.
- `SKILL.md` (interactive, step 5/7): writes the `.meta.json` locally alongside the HTML, `scp`s it up with the rest, then triggers `docker exec hike-izer-orchestrator python3 /app/build_calendar_index.py --srv-dir /srv/hike-izer` remotely — runs inside the container so the path matches regardless of trigger source.
- `Dockerfile` updated to include `build_calendar_index.py` in the deployed copy set.

**Verified 2026-07-28:** unit-style test against synthetic manifests confirmed correct month-grouping, reverse-chronological ordering, and day-of-week grid alignment. Deployed live to the M8, backfilled `.meta.json` for the 2 real summaries that predated this card (`2026-06-18`, `2026-07-23`), ran the builder for real — `https://hikes.jctnet.com/` now serves the calendar instead of Caddy's directory listing, both summary links resolve (`HTTP 200`). Browser screenshot verification was attempted but the tool kept timing out after several tries — stopped rather than loop on it; styling reuses already-visually-confirmed (CARD-0081) color variables, and markup structure was confirmed correct by direct inspection instead.

**Data bug found and fixed 2026-07-28, while working CARD-0104:** the `2026-07-23` backfill above was wrong — it was marked `hike_confirmed: true` from an assumption ("used in real verification tests earlier this session"), but that page's own content says the opposite: GPS confirmation actually *failed* that day (a since-resolved pipeline bug, CARD-0087) even though a real hike happened per Joseph's own confirmation. The calendar was showing it highlighted (confirmed) when it should have shown outlined (published, not GPS-confirmed). Corrected the `.meta.json` to `false` and rebuilt the index — verified live, July 23 now renders `cal-day--not-confirmed` not `cal-day--hike`. Worth remembering: backfilling manifest data from session-memory assumptions instead of checking the actual page content is exactly the kind of gap this session's other cards (CARD-0093's Cloudflare zone, CARD-0101's classification) kept finding — check the source of truth, don't infer it.

**Automatic path verified live 2026-07-28, real hike.** A genuine GPSLogger stop event (`2026-07-28`, a ~32 min/2.0mi walk) triggered the full pipeline for real: `docker logs` showed `hike_confirmed: true`, generation completed, and — the thing this card needed — `generation.py` wrote its own `.meta.json` (`{"hike_confirmed": true}`) and correctly triggered `build_calendar_index.py` (`"Wrote /srv/hike-izer/index.html: 3 summaries indexed."`). Confirmed via the live calendar (`cal-day--hike` for `2026-07-28`) and the MQTT publish log, which correctly referenced the new `hikes.jctnet.com` URL (not the retired `.ts.net` one) — incidentally also a real-world confirmation of CARD-0094's URL fix in production. Same run surfaced a zero-environmental-readings day, explained by Joseph not having the hiking-monitor device with him — not a pipeline bug, nothing further needed.

**Related:** CARD-0088 (HTML hosting, the home page this now lives at), CARD-0091 (HTML-only output, same session, the manifest/calendar work builds on top of it), CARD-0100 (the automatic-path confirmation gate this card's data-source design depends on, confirmed live in the same real run), CARD-0094 (the domain switch this run's MQTT log incidentally re-confirmed), CARD-0081 (HTML rendering template this reuses styling from), CARD-0073 (Hike-izer v1).

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

**Raised 2026-07-24**, during CARD-0088's build. CARD-0088 shipped on Tailscale Funnel instead of the originally-planned Cloudflare Tunnel + `hikes.jctnet.com` subdomain, after discovering Cloudflare's free-tier onboarding doesn't support adding a subdomain as its own independent zone — it requires the full `jctnet.com` apex, which would have meant migrating the domain's nameservers to Cloudflare while it still had live Zoho email (MX + SPF records) running through it. Too risky a change for what CARD-0088 needed at the time.

**Unblocked by CARD-0093** (Done, same day) — once `jctnet.com`'s DNS was cleaned up and email genuinely disabled, the nameserver-migration risk that ruled out Cloudflare was gone. Joseph confirmed picking this up anyway even though the card explicitly wasn't a commitment ("if the `*.ts.net` URL turns out to be perfectly fine in practice, there's no real reason to ever do this").

**Executed 2026-07-27, full switch:**
1. **Cloudflare zone:** `jctnet.com` added to Cloudflare (Free plan) — turned out a zone already existed, half-set-up from the aborted CARD-0088 attempt (status: "Invalid nameservers," never activated). Joseph found the two assigned nameservers (`damon.ns.cloudflare.com`, `sandra.ns.cloudflare.com`) via the Cloudflare dashboard and pointed `jctnet.com`'s registrar nameservers at them via GoDaddy — propagated fast (confirmed active within the same session).
2. **Tunnel setup, on the M8:** `cloudflared tunnel login` (real browser-auth flow, took 3 attempts — first two failed on a volume-mount path mismatch: the `cloudflare/cloudflared` image runs as a non-root `nonroot` user expecting `/home/nonroot/.cloudflared`, not `/root/.cloudflared`; then a permissions error on the mounted host dir until `chmod 777`'d). Once fixed: `tunnel create hike-izer` (ID `aa58cd9e-7535-404a-b144-9c4646143bdd`), `tunnel route dns hike-izer hikes.jctnet.com`.
3. **Compose wiring:** new `cloudflared` service added to `components/hike-izer-web/docker-compose.yml` (no published ports — outbound-only connection to Cloudflare's edge, routes `hikes.jctnet.com` → `http://web:80` over the compose project's Docker network per new `cloudflared-config.yml`). Credentials live in the now-populated, already-gitignored `~/hike-izer-web-app/cloudflared/` on the M8.
4. **Verified before cutover:** `https://hikes.jctnet.com/` returned identical Caddy directory-listing output to the existing `*.ts.net` URL (byte-identical structure, different only in a per-request nonce); the `/webhook/hike-end` proxy route also confirmed working through the new domain with a real `started` event.
5. **Cutover:** `generation.py`'s hardcoded publish-URL string updated to `hikes.jctnet.com`, orchestrator rebuilt/redeployed on the M8. `tailscale funnel --https=443 off` run on the M8 — confirmed the old `*.ts.net` URL is now genuinely unreachable (`HTTP 000`) while `hikes.jctnet.com` still returns 200.
6. **Docs updated to match the new live state** (not just the switch itself): `.claude/skills/hike-izer/SKILL.md`, `components/hike-izer-orchestrator/README.md`, `components/hike-izer-web/README.md` (substantial rewrite — exposure mechanism, setup steps, checking-it's-up commands), `credentials.local.md`, `jctsh-network.md` (both M8 rows). CARD-0096's touch-point note updated too — the Tailscale hostname is no longer a live public-URL dependency, just an admin/SSH access point, so a future host rename is now lower-stakes than that card originally scoped it.

**Real finding, 2026-07-27/28: the Cloudflare zone still had the full original 27-record scan.** Joseph reported `jctnet.com` redirecting to a blank `/lander` almost immediately after cutover — turned out the Cloudflare zone (added back on 2026-07-24 during the aborted CARD-0088 attempt) had never been touched since it was first scanned, so it still carried the *entire pre-CARD-0093* record set: the old GoDaddy-forwarding apex `A` record (proxied, still serving the exact `window.location.href="/lander"` redirect page that was the source of Joseph's separate `/lander` bug), plus all 3 Zoho `MX` records and all 4 `TXT` records (`google-site-verification`, SPF, MS `verifydomain`, `zoho-verification`) — live again, independent of and unaffected by anything done at GoDaddy, since Cloudflare's zone data doesn't sync with the registrar's DNS after the one-time import. This wasn't audited when the zone was activated for the tunnel — only the new `hikes` CNAME was checked. Fixed: Joseph deleted all 27 stale records directly in Cloudflare's DNS panel, confirmed via DNS-over-HTTPS lookups (MX/TXT/`autodiscover` CNAME all now NXDOMAIN/empty).

**Bonus, same fix: `jctnet.com`/`www.jctnet.com` now redirect to `hikes.jctnet.com`** rather than sitting fully dormant (Joseph's call, once the stray record needed deleting anyway) — 2 Cloudflare Page Rules (Free plan, 3 available): `jctnet.com/*` and `www.jctnet.com/*`, both `Forwarding URL` / 301 / `https://hikes.jctnet.com/$1`. Needed a placeholder proxied `A` record (`192.0.2.1`) for the apex and a proxied `CNAME www → jctnet.com`, since Page Rules only fire on traffic that actually reaches Cloudflare's edge — an unrecorded hostname never gets to the rule at all. First attempt used a single wildcard pattern (`*jctnet.com/*`) to cover both apex and `www` in one rule — Cloudflare correctly rejected it as a redirect loop, since the wildcard also matched `hikes.jctnet.com` itself. Two explicit non-wildcard rules avoid that. Verified live: both `jctnet.com` and `www.jctnet.com` cleanly 301 to `https://hikes.jctnet.com/`, `hikes.jctnet.com` itself unaffected (still 200 direct, no loop).

**Tasker update, done and verified 2026-07-28.** Joseph's Tasker uses the "HTTP Post" action (not "HTTP Request" as the README assumed), which splits the URL into separate **Server:Port** and **Path** fields rather than one combined URL. First update only changed Server:Port to `https://jctnet.com` (missing the `hikes.` subdomain, and now a 301-redirect target besides) while leaving **Path** as bare `key=G3sOgsf6Ly5N9XwYN2cb1r0qokkHkmug` — missing the `/webhook/hike-end` prefix entirely, so nothing reached the M8 across two attempts (confirmed via live `docker logs` tailing — the Task ran and its Flash action fired both times, so the failure was silent at the network layer, not a Tasker error). Fixed: **Server:Port** → `https://hikes.jctnet.com`, **Path** → `/webhook/hike-end?key=G3sOgsf6Ly5N9XwYN2cb1r0qokkHkmug`. Manual play-button test confirmed live afterward: request received correctly, `%variable` placeholders present as expected outside a real GPSLogger broadcast, correctly ignored since `gpsloggerevent` wasn't literally `stopped`. `components/hike-izer-orchestrator/README.md`'s Tasker build steps updated with the Server:Port/Path split for this action type, plus the silent-failure warning, so a future rebuild doesn't hit the same gap.

**Related:** CARD-0088 (original hosting card, the Tailscale Funnel-era design this replaces), CARD-0093 (the DNS cleanup that unblocked this), CARD-0086 (the webhook path this also affects), CARD-0096 (host-naming convention, touch-point note updated to reflect this card landing).

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

**Both originally-open decisions resolved 2026-07-27:** `jctnet.com`'s root `A`/parking records — full removal, domain goes fully dormant (Joseph opted for the simplest teardown, splitting the 3 still-wanted Google Sites pages out into **CARD-0103** instead of keeping any DNS around for them). `jctnet.net`'s dangling `google-site-verification` TXT — confirmed safe to remove; both `jctnet.com` and `jctnet.net` showed zero indexed pages in Search Console, so there was nothing live to lose, and `jctnet.com` isn't being re-verified in Search Console at all going forward (nothing left to index once it's parked).

**Notes:** Raised 2026-07-24, during CARD-0088's Cloudflare Tunnel setup — reviewing `jctnet.com`'s DNS in Cloudflare's onboarding scan surfaced 27 records, most of them dead cruft. Not part of CARD-0088 itself (that card doesn't touch the root domain at all) — a separate, standalone cleanup. **Broadened 2026-07-24** after Joseph flagged a second, separate domain also in play — `jctnet.net` — with its own live DNS and its own history; checked directly via public DNS lookup (Cloudflare's DoH API), not assumed. Folded into this same card rather than a sibling one, since it's the same underlying pattern (per-record keep/remove decision).

**Context on the two domains, from Joseph directly (2026-07-24):** `jctnet.net` was his long-time personal email domain (`jcthomas@jctnet.net`), managed across a GoDaddy-hosted-email/Microsoft 365 history. He's since migrated nearly everything important to `joscthomas@gmail.com` and set up Zoho on `jctnet.net` purely to catch remaining mail and forward it to Gmail during that transition — **this forwarding stays live indefinitely** (not an email-disable case like `jctnet.com`). While setting up Zoho he also incidentally created `jcthomas@jctnet.com`, but never gave that address to anyone, so `jctnet.com`'s email was fully safe to drop. `jctnet.com`'s Google Sites content was also mostly unwanted (3 specific pages carved out into CARD-0103), which **broadened the original cleanup scope** (the `www` CNAME/Google verification TXT were originally marked "Keep," superseded by full removal). `jctnet.net` separately turned out to have its own live Canva-connected site (found via DNS scan, not something Joseph had mentioned) — confirmed removable too.

**Both domains registered/managed at GoDaddy** — one registrar login covered the DNS editing for both.

---

**`jctnet.com` — full teardown to zero active records. DONE, confirmed live 2026-07-27.**
- **Removed — email disabled entirely** (never gave this address to anyone): `MX` ×3 (Zoho), `TXT "v=spf1 include:zohomail.com ~all"`, `TXT "zoho-verification=..."`.
- **Removed — Google Sites, now unwanted:** `CNAME www → ghs.googlehosted.com`, `TXT google-site-verification=...`. The 3 pages Joseph still wants (Cochie Springs hike, Mustang, Karli's Summer) are being re-homed on the M8 separately via **CARD-0103** — the content stays live at its native `sites.google.com` URL regardless of this DNS removal.
- **Removed — dead legacy cruft** from a Microsoft 365/Skype-for-Business + GoDaddy-hosted-email history predating Zoho: `CNAME autodiscover, lyncdiscover, sip, msoid` + both `SRV` records (`_sipfederationtls._tcp`, `_sip._tls`) — Microsoft federation; `CNAME e, email, mail, imap, pop, smtp, webmail, mobilemail, pda` → `secureserver.net`; `CNAME ftp → jctnet.com`; `CNAME _domainconnect → ...gd.domaincontrol.com`; `TXT "v=verifydomain MS=..."`.
- **Root `A` records removed too** (`15.197.148.33`, `3.33.130.190` — GoDaddy's forwarding/parking infra, likely root cause of the separate `/lander`-resolves-blank bug Joseph is investigating independently). Joseph opted for the simplest end state — fully parked, nothing forwarding — over fixing the forwarding target. Showed in GoDaddy's UI as `A @ → "Parked"` rather than raw IPs, and (same as `jctnet.net`'s `jct1` below) couldn't be deleted from the plain DNS table — removed via GoDaddy → **Forwarding** tab instead.
- **Live GoDaddy re-check 2026-07-27 confirmed no surprises** — no DKIM/DMARC records existed for `jctnet.com` (unlike `jctnet.net`; Joseph never actually used `jcthomas@jctnet.com`, so Zoho's optional DKIM/DMARC setup was never done here). All 24 non-infrastructure records matched the plan exactly.
- **Final state:** just `NS` ×2 (`ns23`/`ns24.domaincontrol.com`) and `SOA` — registrar infrastructure only. Zero active records, fully dormant, parked domain.

**`jctnet.net` — keep the email bridge, drop everything else. DONE, confirmed live 2026-07-27.**
- **Kept — the active forwarding bridge:** `MX` ×3 (`mx.zoho.com`, `mx2`, `mx3`), `TXT "v=spf1 include:zohomail.com ~all"`, `TXT "zoho-verification=..."` ×2 (`zb46987192...`, `zb84210231...`).
- **Kept — missed by the original 2026-07-24 research, found live 2026-07-27:** `TXT jctnet._domainkey` (Zoho's DKIM signing key) and `TXT _dmarc` (DMARC policy, `rua`/`ruf` → `jcthomas@jctnet.net`) — active email-authentication records supporting the same Zoho mail flow. Removing either wouldn't have stopped forwarding outright but would have risked deliverability/reputation for anything sent as `jctnet.net` — the opposite of what this card was protecting. Worth remembering for any future domain-cleanup card: a scan done for one purpose (Cloudflare onboarding, a DoH lookup) can miss records like DKIM/DMARC that don't show up unless you check the live registrar panel directly.
- **Removed:** the Canva site (`TXT "canva-domain-verify=..."`, root + `www` `A` records → Canva's hosting, `103.169.142.0`), `TXT "v=verifydomain MS=..."`, `TXT "google-site-verification=..."` (confirmed via Search Console — zero indexed pages), the full Microsoft/GoDaddy legacy-email bucket (`CNAME autodiscover, e, email, ftp, imap, lyncdiscover, mail, mobilemail, msoid, pda, pop, sip, smtp, webmail, _domainconnect` + `SRV _autodiscover._tcp, _sip._tls, _sipfederationtls._tcp` — 21 records, same pattern as `jctnet.com` but not individually enumerated in the original write-up), and `CNAME litesrv._domainkey → litesrv._domainkey.mlsend.com` (MailerSend, not Zoho — also missed by the original research).
- **`A jct1` ×2 (`15.197.142.173`, `3.33.152.147`)** — same GoDaddy forwarding-IP pattern as `jctnet.com`'s parked root, also missed by the original research. Joseph didn't recognize it, called it legacy cruft. Couldn't be deleted from the DNS table ("delete not allowed" — GoDaddy blocks direct deletion of records auto-generated by its **Domain Forwarding** feature); removed via GoDaddy → `jctnet.net` → **Forwarding** tab → deleting the `jct1` subdomain-forwarding entry, which cleared the underlying A records.
- **Final state:** exactly the target 8 records (`MX` ×3, SPF `TXT`, `zoho-verification` `TXT` ×2, `jctnet._domainkey` `TXT`, `_dmarc` `TXT`) plus `NS` ×2/`SOA` (untouched, registrar infrastructure).

**Side effect worth knowing about, not a driver of this card:** now that `jctnet.com` genuinely has no live email, the single biggest risk factor against a full-domain Cloudflare nameserver migration (which CARD-0088 explicitly avoided, falling back to Tailscale Funnel instead, specifically because live Zoho mail made that migration too risky) is gone. Doesn't mean CARD-0088 should be redone — just reopens that path as a future option if a real reason to revisit it ever comes up (see CARD-0094). `jctnet.net` keeping live email doesn't reopen anything, since CARD-0088 never considered that domain.

**Related:** CARD-0088 (the card whose Cloudflare setup surfaced `jctnet.com`'s cleanup), CARD-0094 (deferred Cloudflare switch, now lower-risk), CARD-0103 (migrating the 3 still-wanted Google Sites pages to the M8, split out 2026-07-27), the separate (not yet carded) `/lander` blank-page bug Joseph is fixing independently on `jctnet.com`.

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

### CARD-0099 · [bug] [core] Timeline sheet's `timestamp_az` column hardcodes Arizona local time for every row, regardless of where it happened — RESOLVED 2026-07-25
**Status:** Done

**Raised 2026-07-25**, discovered while confirming CARD-0097's fix — Joseph asked "are there any other columns in any sheet so named," which surfaced this second, more serious instance of the same standing principle ([[feedback_no_location_assumptions]]).

**Real gap, not just a stale label (unlike `date_az` in Hike Start Forecast, which CARD-0097 already made cosmetic-only):** `refreshTimeline()` (JCTsh menu → Refresh Timeline) merges Environmental Data + Hiking Observations into the "Timeline" sheet, and unconditionally formatted every row's display time via `_azString()` — hardcoded Arizona (UTC-7, no DST) — regardless of where that reading/observation actually happened. A Michigan or Egypt hike's rows would have silently shown the wrong wall-clock time, mislabeled as if it were correct.

**Fix:** replaced `_azString()` with `_localString(utcDate, lat, lon, offsetCache)`, resolving each row's real UTC offset *and* IANA zone name via Open-Meteo's `timezone=auto` (same provider/mechanism as CARD-0097), cached per rounded `(lat,lon)` for the life of one `refreshTimeline()` run so repeated locations (a fixed home sensor, or many readings from one hike) cost one real HTTP call, not one per row. Column renamed `timestamp_az` → `timestamp_local` — and since this sheet is fully rewritten (`clearContents()` + header) on every refresh, the rename actually takes effect immediately, unlike the Hike Start Forecast header which only sets its header once at sheet creation.

**Format iterated twice at Joseph's request:** first cut appended just the raw UTC offset (e.g. `+03:00`) — Joseph pointed out a bare offset means nothing without already knowing which place maps to it. Switched to leading with the IANA zone name (e.g. `Africa/Cairo`), which Open-Meteo already resolves as part of the same lookup at no extra cost — then added the raw offset back in parentheses alongside it, since that's still useful for quick arithmetic between rows. Final format: `YYYY-MM-DD HH:MM:SS Zone/Name (±HH:MM)`, e.g. `2026-07-25 17:24:37 Africa/Cairo (+03:00)`. Rows with no GPS correlation yet, or where the Open-Meteo lookup itself fails, fall back to an explicit `... UTC` label rather than a wrong guess.

**Live-verified 2026-07-25** against real production data (14,545 rows, spanning 2019–2026): after redeploying and running Refresh Timeline, Joseph confirmed directly from the Sheet that the real Giza test coordinate (29.9792, 31.1342, left over from CARD-0097's verification) now shows `2026-07-25 17:26:45 Africa/Cairo (+03:00)`, while a real fixed Arizona sensor (lat 32.4612997, lon -111.1184154) correctly shows `America/Phoenix (-07:00)` — different locations resolving to their own correct zone, not one hardcoded assumption for everything. Sort order also confirmed correct: the Giza row's true UTC instant (14:26:45 UTC) sorts just before the Arizona rows (14:31:44 UTC onward), confirming the sort key is still the real timestamp, not the display string.

**Troubleshooting note during verification:** the first "Refresh Timeline" click produced no corresponding entry in the Apps Script Executions log at all — the menu click hadn't actually invoked the function (likely a stale menu binding in an already-open browser tab from before the redeploy). Fully reloading the Sheet tab and re-clicking fixed it; the resulting execution (`Head`/`Menu`/`refreshTimeline`, 38.9s, Completed) is what actually produced the correct data. Worth remembering for any future Apps Script custom-menu debugging in this repo: check the Executions log for a *matching* entry before assuming a run happened at all.

**Related discovery, not yet acted on:** verifying this fix via the `action=export` HTTP endpoint turned out to be unreliable in a way that goes beyond the endpoint's already-documented Timeline caveat — `_exportSheet` silently drops (not just mis-filters) any row whose column A doesn't parse as a valid JS `Date`, and this happens *unconditionally*, even when no `start`/`end` filter is requested. The old Arizona-only format happened to still parse via V8's lenient date parsing; the new zone-name format (e.g. `... Africa/Cairo (+03:00)`) does not, so the export endpoint was quietly hiding exactly the rows needed to verify this fix. Verification was completed instead by having Joseph read the Sheet directly. Not fixed as part of this card — flagged for a possible follow-up if `action=export` needs to reliably return Timeline rows in the future.

**Related:** CARD-0097 (same standing principle, same Open-Meteo `timezone=auto` mechanism, found first), [[feedback_no_location_assumptions]] (the standing principle both cards are instances of), `core/data-pipeline/environmental-data.gs`, `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`, `components/hiking-monitor/data-pipeline.md`.

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

**Notes:** Filed 2026-07-23, narrowed 2026-07-24, moved to Build 2026-07-24, resolved 2026-07-24. Originally scoped as "HTML rendering, Levels 3-5" (embedded visuals, interactive, hosting) split out of CARD-0081. Narrowed further after realizing the embedded-visuals and interactive/photos items were pure duplicates of scope already owned elsewhere — CARD-0082 (Visual track + elevation graphic) already covers embedded maps/charts, CARD-0084 already covers photo integration. This card covers only the one genuinely unowned piece: **publishing** the HTML Hike-izer already generates (CARD-0081, Done) somewhere with a real URL, instead of emailing a file as an attachment.

**Decided 2026-07-24: self-host on the M8** (`photo-server`), not Google Sites — Google Sites' manual-publish friction (no programmatic API) was the deciding factor against it.

**Cloudflare Tunnel + `hikes.jctnet.com` was the original plan — attempted, then abandoned mid-build 2026-07-24.** The intent was a subdomain of `jctnet.com`, delegated via an NS record at the registrar, leaving the root domain's Google Sites DNS completely untouched. In practice, Cloudflare's free-tier onboarding **does not support adding a subdomain as its own independent zone** — typing `hikes.jctnet.com` into "Add a Site" was rejected and Cloudflare required the full `jctnet.com` apex instead. Reviewing the resulting DNS scan (27 records) surfaced that `jctnet.com` runs **live email via Zoho Mail** (3 MX + SPF) — a full nameserver migration to Cloudflare would have put that at real risk for a card that only needed to host a hiking-summary page. Backed out before activating the Cloudflare zone or touching GoDaddy; no changes made to `jctnet.com` at all. Two useful things came out of the attempt anyway: **CARD-0093** (DNS cleanup + disabling the unused Zoho email, which removes this exact risk and reopens the Cloudflare path later) and **CARD-0094** (the deferred, optional switch back to Cloudflare once CARD-0093 lands) — plus a likely root-cause finding for Joseph's separate `/lander`-resolves-blank bug: the root `jctnet.com` `A` records point to GoDaddy's own domain-forwarding IPs, not Google's, meaning the bare domain is being HTTP-redirected by GoDaddy to a misconfigured target rather than serving Google Sites directly (the real Sites mapping is on `www.jctnet.com` via CNAME).

**Shipped on: Tailscale Funnel.** `https://photo-server.tailfe828a.ts.net` — the M8 already runs Tailscale (same infra HA's own Tailscale HTTPS URL uses), zero risk to `jctnet.com`, zero DNS changes, works today. Trade-off knowingly accepted: an opaque `*.ts.net` address instead of a legible custom domain — see CARD-0094 if that's ever worth revisiting.

**Architecture, as built 2026-07-24:**
- **One Docker container, loopback-only host port** — `components/hike-izer-web/`: a Caddy container serving `~/hike-izer-web-app/srv/` as static files, published only to `127.0.0.1:8090` on the M8 host (not the LAN/WAN). `tailscale funnel --bg 8090` (run on the host, not in a container) exposes that port publicly, with TLS terminated by Tailscale. `jct` was set as the Tailscale operator (`sudo tailscale set --operator=jct`, one-time) so Funnel commands don't need `sudo`. The container defines its own `HEALTHCHECK` so the M8's heartbeat script (see below) has a real status to read, not an empty one.
- **Disk placement, checked 2026-07-24:** the M8's boot disk (`nvme0n1`, 477GB, 421GB free) is the *only SSD in the system*. Served content lives at `~/hike-izer-web-app/srv/` (under `/home`, still the boot disk) rather than the FHS-conventional `/srv/` — `/srv` is root-owned and `jct` has no passwordless sudo, so it matches the existing `netalertx-app/data`, `immich-app` convention instead of fighting that for no real gain. Estimated footprint at 3 hikes/week (CARD-0084's real photo sizes): ~7.3GB/year photos-only, ~12.5GB/year with occasional video — trivial against 421GB free.
- **Deliberately not backed up** — the M8's existing backup job (`photo-library-backup.sh`) is Immich-only; `~/hike-izer-web-app/srv/` isn't swept in, and that's fine — everything there is regenerable from the real sources of truth (Google Sheets pipeline + Immich), same reasoning already accepted for the photo cache (CARD-0084).
- **Heartbeat extended, not duplicated** — `hike-izer-web` added to the M8's existing 30-minute Docker health check (`photo-server-heartbeat.py`) alongside the four Immich containers. Note: this covers container health, not Funnel/tailnet connectivity itself — a known gap, not yet addressed.
- **No per-publish MQTT log line, deliberately** — the deploy step runs on Joseph's Windows machine (where Hike-izer's Skill executes today), which has no MQTT-publish capability; adding one would mean a new pip dependency for a one-off script, breaking `fetch_hike_data.py`'s "standard library only" convention. Revisit once CARD-0086's orchestrator exists on the M8 itself — the natural place for real publish-visibility logging.
- **Deploy folded into the existing Skill, not deferred to CARD-0086** — an `scp` step added to `.claude/skills/hike-izer/SKILL.md`'s generation flow. CARD-0086 (automatic *triggering*) is separate scope; this just means every summary generated from here on ends up published with no separate manual copy step.
- **New component** — `components/hike-izer-web/`, matching the convention where each M8-deployed app gets its own top-level `components/<name>/` directory (NetAlertX and Immich are separate components despite sharing a host).

**Verified 2026-07-24:** container deployed and healthy; real content (`2026-06-18_hike-summary.html` + its `_photos/` dir) served correctly over loopback; loopback-only binding confirmed genuinely unreachable from the LAN directly (`curl` to the M8's LAN IP on the published port times out); Funnel enabled and confirmed reachable from the public internet (`curl https://photo-server.tailfe828a.ts.net/2026-06-18_hike-summary.html` → HTTP 200, correct title); updated `photo-server-heartbeat.py` deployed and triggered for a real run — completed cleanly with `status=online`, no errors or `Alert`-category messages, confirming `hike-izer-web` reports healthy alongside the four Immich containers.

**Related:** CARD-0081 (HTML rendering, Levels 1-2, Done — produces the file this card publishes), CARD-0082 (embedded visuals/interactivity — separate card), CARD-0084 (photo integration — separate card), CARD-0086 (automatic triggering — future orchestrator home, and future MQTT publish-visibility logging), CARD-0092 (calendar home page — eventual replacement for this card's interim directory-listing index), CARD-0093 (DNS cleanup — unblocks CARD-0094), CARD-0094 (deferred switch to Cloudflare Tunnel + custom domain), CARD-0095 (M8 OS/firmware maintenance, surfaced while building this), CARD-0073 (Hike-izer v1, Done).

---

### CARD-0083 · [idea] [hike-izer] Show the weather forecast as it stood at hike start — RESOLVED 2026-07-24
**Status:** Done

**Notes:** Raised 2026-07-23, moved to Build 2026-07-24, resolved 2026-07-24. Show what the weather forecast *was* at the beginning of the hike — not a live/current forecast checked whenever the summary gets generated, and not actual observed conditions (that's already CARD-0074's separate "historical weather" item, explicitly scoped as actual-conditions lookup, not forecast).

**Feasibility issue found and resolved by scoping decision:** historical forecasts generally aren't retrievable after the fact — weather services archive what actually happened, not what was predicted at some past moment, unless something captured that specific forecast snapshot at the time. Scoped for **future hikes only**, captured live at hike start — not retroactive for hikes already recorded. No existing weather-fetch integration to build on: JCTsh's Weather Underground integration only *posts* the household's own sensor data outward, it doesn't pull forecast data in — this is a new integration either way.

**Content scope:** full detail — temperature, precipitation chance, wind, humidity, and UV index. Not just a one-line summary.

**Provider — decided 2026-07-24: Open-Meteo (`api.open-meteo.com`).** Neither of the two candidates originally considered (NWS: free, no key, but no UV index; OpenWeatherMap: has everything but needs an account/possible billing setup) was the best fit. Open-Meteo is free, needs **no API key or account at all**, and its hourly forecast endpoint returns temperature, humidity, precipitation probability, wind speed, and UV index in a single call — covers the full content scope with zero credential-management overhead, no `credentials.local.md` entry needed. **Origin point (raised by Joseph 2026-07-24):** unlike NWS/METAR (which snaps to a named station, e.g. an airport), Open-Meteo has no station concept — it's a gridded model interpolated to the exact coordinate requested. The response's own `latitude`/`longitude` (the actual grid point used, which can differ slightly from the input) is stored alongside the reading, so the record shows precisely what point the forecast was for.

**Capture mechanism — decided 2026-07-24: reuse the existing Hiking Observations pipeline (CARD-0007), no new mobile automation.** `environmental-data.gs` fires the forecast fetch server-side the moment it receives the **first Hiking Observation of a new calendar day (Arizona local)** — a positional/temporal heuristic, not a keyword match (real observation text is messy, e.g. an actual captured first-observation was *"hiking trail tortellita preserve perimeter Trail"*). Real-time (fires the instant the observation POSTs), zero new Tasker/Node-RED build. **Location correctness (caught 2026-07-24):** uses the observation's own GPS correlation (`_gpsLookup`, already computed for the observation row) — if that lookup hasn't resolved yet (no GPS trackpoint within its ±5 min window, common right at a trailhead, or a hike somewhere far from home), the capture is **skipped for that observation rather than falling back to a hardcoded home-area location**. An earlier draft of this design had that fallback; it was caught and removed before build, since it would have silently reported Tucson weather for a hike that isn't near Tucson. A later observation the same day with a resolved GPS position retries capture, so this is a deferral, not a permanent miss.

**Relationship to CARD-0086:** this card's trigger (Apps Script, hike-*start*) is a deliberate v1 choice made to avoid depending on CARD-0086 (hike-*finish* auto-triggering), which isn't built yet. CARD-0086's own notes already flag its GPSLogger native-broadcast mechanism as a candidate replacement for this same start-trigger once CARD-0086 is built — worth revisiting then, not a blocker now.

**Storage:** new `Hike Start Forecast` sheet in the "JCTsh Environmental Data" workbook, self-provisioning (Apps Script creates it with headers on first use — no manual Sheets setup), one row per Arizona-calendar-day, written once and never re-fetched. `fetch_hike_data.py` reads it via the existing generic `action=export` endpoint alongside the other three sheets.

**Display:** both Markdown and HTML, per existing Hike-izer convention (plain numeric/text data, unlike CARD-0084's photos which needed real files and are HTML-only) — see CARD-0091 for the separate, deliberately-deferred question of whether Markdown output continues to exist at all going forward. Its own labeled section, shown before the narrative story (context before "here's how the hike went"). In HTML the section is **always rendered, never omitted** — with five named values (not a variable-length gallery like Photos), the established "not available" stat-row convention applies instead of Photos' omit-when-empty pattern; each card shows "not available" rather than a blank or fabricated value when no forecast was captured for that day.

**Live deployment and verification (2026-07-24):** the redeployed Apps Script was confirmed live via `action=version`, then exercised end-to-end with real synthetic test data (a tomorrow-dated GPS point + Hiking Observation, cleaned up afterward — never touching today's real data). Two real bugs found and fixed during this process, both worth remembering:
- **`UrlFetchApp` needed a fresh authorization grant.** The original script never called an external URL; adding the Open-Meteo fetch required a new OAuth scope that a web app redeploy alone doesn't grant — the first 3 live-test observations (with valid GPS) silently produced zero forecast rows because the exception was swallowed by the function's own try/catch. Fixed by manually running a throwaway function directly in the Apps Script editor once, which triggered the authorization prompt; the grant applies per-account (not per-deployment-version), so no further redeploys were needed for this specifically.
- **Google Sheets auto-converts a bare `"YYYY-MM-DD"` string to a real Date value on write**, silently breaking the dedup comparison (a stored Date object never string-equals a freshly computed date string) — full ISO datetime strings like `timestamp` weren't affected, only the bare-date `date_az` column was. Fixed by forcing that column to plain-text format (`setNumberFormat('@')`) on every write, not just at sheet creation, so it's safe even against a sheet that already existed from before the fix.

After both fixes and a redeploy, a full clean test confirmed: sheet auto-creation, GPS-correlation skip-and-retry (an out-of-window observation correctly produced no capture), successful capture with real Open-Meteo data (including the origin-point snapping — requested `32.4614,-111.1184` came back as the real grid point `32.450283,-111.10121`), correct plain-text `date_az`, and dedup holding at exactly one row despite a second GPS-correlated observation the same day. `fetch_hike_data.py` run against the live deployment confirmed the real captured data flows correctly into `hike_start_forecast` in the output JSON, ready for the narrative-writing step. Test data (GPS Track, Hiking Observations, Hike Start Forecast — all dated 2026-07-25, clearly marked as test rows) was manually cleaned up afterward since the Apps Script has no delete endpoint.

**Related:** CARD-0074 (Hike-izer v2 — sibling "historical weather" i.e. actual-conditions item lives there, not here), CARD-0086 (hike-finish auto-triggering — candidate future replacement for this card's start-trigger), CARD-0091 (Markdown-format future — this card's forecast section ships to both formats until/unless CARD-0091 changes that), CARD-0007 (hiking observations pipeline, Tasker → Sheets precedent), `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`, `components/hike-izer/fetch_hike_data.py`.

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

**Not yet done:** report the confirmation back on the GitHub issue — that's a public action (commenting on someone else's issue) needing Joseph's explicit go-ahead, not something to post unprompted.

**Related:** CARD-0078 (where the bug was found and worked around), `netalertx/NetAlertX#1720` (upstream issue), `components/netalertx/docker-compose.yml`.

---

### CARD-0084 · [idea] [hike-izer] Photo integration (Immich) — RESOLVED 2026-07-24
**Status:** Done

**Notes:** Raised 2026-07-23, split out of CARD-0074 (Hike-izer v2, superseded) as an individually-tracked feature rather than a batched release item. Pull in photos taken during a hike, matched via `photo-server`'s Immich API to a confirmed hike's date/time range.

**Actual data dependency (corrected 2026-07-24 — not what CARD-0074 originally said):** CARD-0074's blanket blocker note ("hiking-monitor device needs to be operational") was carried into this card mechanically without checking whether it actually applies. It doesn't: this feature needs (1) a confirmed hike time window — which comes from GPS Track/GPSLogger (phone-based), entirely independent of the hiking-monitor ESP32 device, confirmed working independently by CARD-0087 — and (2) real photos in Immich falling within that window. The hiking-monitor device only produces Environmental Data (temp/humidity/pressure/UV/battery/altitude), which this feature doesn't touch at all.

**Test dataset confirmed available (2026-07-24):** queried Immich's `search/metadata` API (Joseph's account) directly against both confirmed-hike windows from June's trip — **9 real photos** land within the 2026-06-18 hike (14:46–15:55 UTC), **2 more** near the tail of the 2026-06-17 evening hike (23:51–02:59 UTC). All have correct `dateTimeOriginal` and real GPS EXIF, confirmed via a direct asset fetch. No blocker remains — this is buildable and verifiable right now.

**Scope, decided 2026-07-24 (interview before build):**
- **Matching:** time range only (each `is_hike` session's own start/end, queried separately per session — not merged into one enclosing span) — **not** GPS bounding box, changed during implementation planning. Reasoning: the time window already comes from the real GPS-confirmed session; if Joseph is out hiking and takes a photo inside that exact window, it was taken during the hike by definition. A bounding-box check only guards against a mismatch that mostly can't happen here, and has a real downside — it would silently drop legitimate hike photos lacking GPS EXIF (location services off, etc.).
- **Account:** Joseph's Immich account only (`joscthomas@gmail.com`), not Robin's.
- **Media types:** images and videos both included.
- **Curation:** fully automatic — every asset matching time criteria gets included, no manual review/approval step (consistent with how every other Hike-izer data source already works).
- **Output surface:** HTML only (CARD-0081's output) — the Markdown stays text-only as today; no photo references added there.
- **Display:** a thumbnail gallery in the HTML, each thumbnail clickable/linking to the full-resolution original.
- **Image storage/hosting:** extracted and downloaded locally at generation time (thumbnail + full-res per asset) into a directory alongside the HTML output — not linked directly to Immich's API (which requires an auth header no plain `<img>` tag can send) and not using Immich Shared Links (would make the page depend on photo-server staying reachable from wherever it's viewed, relevant given CARD-0088's future hosting plans). Self-contained output was preferred over avoiding duplication.
- **Git tracking:** the extracted media files themselves are gitignored (like `secrets.yaml`) — only the HTML/Markdown summaries stay tracked in git, to avoid unbounded repo growth from binary media; Immich remains the real source of truth/backup for the photos.

**Implementation (2026-07-24):**
- `components/hike-izer/fetch_hike_photos.py` (new) — mirrors `fetch_hike_data.py`'s conventions (argparse, stdlib `urllib`, stderr progress, one JSON output). Reads a day's `hike_data.json`, queries Immich `POST /api/search/metadata` (`takenAfter`/`takenBefore`, `withExif: true`, paginated) **separately per `is_hike` session** (not merged into one span — see bug fixed below), downloads `thumbnail?size=preview` + `original` per non-trashed match into an output dir, writes `manifest.json` for the HTML-authoring step to consume.
- `components/hike-izer/html-template.html` — new Photos gallery section (CSS grid, `auto-fill`/`minmax` so it reflows responsively with no extra breakpoint needed, plain link-to-original click-through, no JS lightbox), placed after Full Observations Log, before the Coverage section. Omitted entirely when the manifest is empty.
- `.claude/skills/hike-izer/SKILL.md` — new step wiring the script into the existing HTML-generation flow, including the cross-midnight curation caveat below.
- `.gitignore` — `hike-izer/summaries/*_photos/` (media stays local-only, HTML/Markdown stay tracked).
- `components/hike-izer/README.md` — file listing update.

**Real bug caught and fixed during verification (2026-07-24):** first implementation collapsed every `is_hike` session's window into one enclosing start-to-end span before querying Immich. On 2026-06-18 this pulled in 2 unrelated photos from ~12 hours before the real hike (from the query day's own leftover cross-midnight session fragment) alongside the 9 real ones — a real correctness bug, not the intended cross-midnight caveat. Fixed by querying each session's own window separately and merging results (deduped by asset ID). Re-verified: 2026-06-18 now correctly returns exactly the 9 real daytime-hike photos.

**Cross-midnight caveat (real, inherent, not a bug — same edge case as this doc's day-scoping rule):** confirmed via a proper wide-window fetch (spanning 2026-06-17 into 2026-06-18) that the two 02:50-02:51 UTC photos are the tail of the *real* June 17 evening hike (23:51 UTC start — 4:51 PM MST local, an ordinary evening hike, not a night hike; "midnight" here is the UTC/MST offset, not local midnight), correctly split from the 9 June-18-daytime photos once sessions are queried by their true (non-truncated) start/end. `fetch_hike_photos.py` can't resolve this on its own from a single day's data (documented in its own docstring); SKILL.md instructs the same manual per-day curation already applied to CARD-0081's `distance_mi` on such days.

**Verified end-to-end (2026-07-24):**
- Real run against 2026-06-18: 9 real photos downloaded, added to a real gallery in `2026-06-18_hike-summary.html`, opened in Chrome — all 9 load correctly (confirmed real image bytes, not broken links), light-mode and dark-mode CSS-variable cascade both correct on the new `.photo-item`/`.photo-grid` rules, click-through to full-res confirmed reachable (200), correct section placement.
- Real run against the wide 2026-06-17→18 window: confirmed the two sessions' assets split correctly (2 vs. 9, zero cross-contamination) at the manifest level.
- `hike_confirmed: false` path: confirmed the script exits early with an empty manifest **without calling Immich at all**, and confirmed the real `2026-07-23_hike-summary.html` has zero "Photos" section, as intended.
- `.gitignore`: confirmed via `git status` that neither `2026-06-18_photos/` nor `2026-06-17_photos/` shows as untracked/stageable — the pattern is working.

**Related:** CARD-0073 (Hike-izer v1, Done), CARD-0074 (superseded — see that card for the original v2 batch this was split from), CARD-0081 (HTML output this embeds into), CARD-0088 (hosting — relevant to the self-contained-storage decision above), `components/hike-izer/fetch_hike_data.py`.

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

**Notes:** Raised 2026-07-18. JCTsh's hiking-monitor pipeline already covers data collection (ESP32 sensors — BME280, LTR-390 UV; GPS track via Pixel GPSLogger) and data storage (GPS Track and Environmental Data Google Sheets, per CARD-0020). Hike-izer adds the missing layers on top: a controller layer (rules/analysis) and a rudimentary presentation layer, turning raw hike data into a narrative story of the hiking event rather than just charts.

**Relationship to CARD-0020:** complementary, not competing (Joseph's call). CARD-0020's Looker Studio dashboard stays scoped to raw charts/maps; Hike-izer's output is the narrative layer, generated from the same underlying Sheets data. Neither supersedes the other.

**Data source inventory (2026-07-18):** confirmed against the real pipeline code/docs, not assumption —
- **Environmental Data sheet** — full column set is A–Z, not A–X as `data-pipeline.md` previously (incorrectly) documented; `illuminance_lx`/`solar_v` were missing from that doc, now fixed.
- **Hiking Observations sheet — exists and works.** There IS a capture mechanism (Tasker voice-widget → Apps Script → auto-categorized row), built and field-confirmed in Steps 23–26.
- **GPS Track sheet** (via GPSLogger, not GaiaGPS — GaiaGPS was the superseded original plan and several docs still stale-reference it) — includes `alt` (altitude), which covers "height" without new hardware.
- **Timeline sheet** — existing manual-menu action already merges Environmental Data + Hiking Observations into one time-sorted sheet.
- **Compass/heading** — still a real gap, no sensor and not derivable cleanly from GPS Track alone (direction of travel ≠ which way the hiker was facing). Deferred, see scope below.
- Confirmed target trip for prototyping: the **2026-06-15 two-week trip**. GPS pipeline was redeployed 2026-06-12 (before the trip) so GPS Track data is very likely present; observations pipeline's exact completion date relative to June 15 isn't pinned down in the docs — check the real sheet before assuming observation rows exist for this window.

**Build step taken (2026-07-18):** extended `core/data-pipeline/environmental-data.gs` with a new read-only `action=export` on `doGet` — returns any sheet (Environmental Data / Hiking Observations / GPS Track) as JSON, optionally filtered by an ISO 8601 timestamp range, reusing the existing API_KEY auth. Documented in `data-pipeline.md`.

**Deployment saga (2026-07-18) — resolved.** The normal "Manage deployments → pencil → New version → Deploy" flow silently failed three times in a row: the Active deployment kept serving old code with zero errors, no indication anything was wrong. Root-caused by adding a `SCRIPT_VERSION` constant returned in every `doGet` response (including the "unknown action" fallback) — confirmed via `Deploy → Test deployments` (`/dev` URL, always runs Head/latest-saved code) that the *saved code* was correct the whole time; the problem was isolated specifically to the versioning step not promoting to the Active deployment. Fix: created an entirely new deployment (`Deploy → New deployment`) rather than continuing to fight the existing one — worked immediately, confirmed via `action=version` and a real `action=export` call that pulled all 6,202 real Environmental Data rows for the June 15 trip window.

**New deployment URL migrated everywhere the old one was referenced:** `credentials.local.md`, `data-pipeline.md`, Node-RED's `APPS_SCRIPT_URL` (found to live in `/home/pi/.node-red/environment`, a systemd `EnvironmentFile` — **not** the Node-RED editor's Settings → Environment Variables panel, which only covers flow/global-scoped vars, not OS-level ones; updated via SSH over Tailscale, `nodered` service restarted, verified via the live process's own `/proc/<pid>/environ` that the new URL is actually loaded, not just written to disk), and GPSLogger's custom URL setting on the Pixel (Joseph updated manually). Old deployment now fully unreferenced — left in place, harmless if idle.

**v1 scope — locked 2026-07-18 (Joseph's call, no separate Phase 1 planning doc; this card is the plan, given the scope's size — revisit if Hike-izer grows past v1 into photos/weather/automation):**
- **Mechanism:** a Claude Skill.
- **Trigger:** on-demand, with the **date/date-range as a prompt parameter** — not hardcoded to June 15. June 15 is the first test case, not the only one; Joseph may want to run this against other hikes later.
- **Inputs:** Environmental Data + Hiking Observations + GPS Track (lat/lon/alt), pulled for the requested date range via `action=export`.
- **Computed:** sun position (from lat/lon + timestamp), using GPS `alt` for height.
- **Output:** one Markdown document per run, including:
  1. A narrative story of the hike.
  2. Data tables/summaries as appropriate.
  3. **An explicit "expected vs. actual" data-coverage section** — not just an aside, a first-class part of the output. What was expected (sensor readings at ~2-min cadence, one observation stream, GPS trackpoints every ~30s, over the requested date range) versus what's actually present. This is meant to double as a health check on the whole hiking-monitor pipeline every time a summary is generated.
- **Explicitly deferred, not forgotten:** photos (Immich integration unbuilt), historical weather (no source picked), compass/heading (no data source), automatic triggering, rendered web page output.

**v1 built and verified end-to-end (2026-07-18).** Built as a real Claude Skill: `.claude/skills/hike-izer/SKILL.md` (instructions: determine date range, read credentials from `credentials.local.md`, run the fetch script, write the narrative in three parts, save to `hike-izer/summaries/`) plus `components/hike-izer/fetch_hike_data.py` (stdlib-only Python: fetches all three sheets via `action=export`, computes coverage stats, computes sun position via the NOAA/Meeus solar algorithm sampled along the GPS track). Code and generated output deliberately kept apart: code under `components/hike-izer/`, results under the top-level `hike-izer/summaries/` — so a future HTML presentation layer doesn't end up mixed in with source.

**Two real bugs found and fixed by testing against the real June 15 trip data, not left on paper:**
1. GPS Track's actual columns are `accuracy_m`/`altitude_m` (confirmed in `gps-pipeline.md`) — the script initially used `acc`/`alt`, silently returning `None` for every altitude. Fixed.
2. The GPS Track coverage calc originally compared point count against a full-date-range 30-second-cadence expectation, which produced a misleading "~1% coverage" — GPSLogger only runs during actual hikes, not continuously across a multi-day camping trip. Replaced with session detection (splits on >10min gaps, reports per-session coverage) — correctly showed 2 real sessions at 85.9% and 95.6% coverage instead of one alarming, wrong number.

**First real output generated:** `hike-izer/summaries/2026-06-15_hike-summary.md`. Genuine findings surfaced by the coverage section (not fabricated for demonstration) — UV index never exceeded 0.1 across the whole trip despite 110°F+ heat, consistent with the LTR-390 validation concern already tracked in CARD-0065; battery voltage dropped to 2.85V, lining up with the documented field LiPo failure (`README.md`, 2026-07-03); zero Hiking Observations rows despite the pipeline being confirmed working, worth a conscious check on whether the voice widget just wasn't used; only 2 GPS sessions (~4.3 hours total) detected across the full 2-week window. This is exactly the "awareness of how components are operating" goal from the original ask — not hypothetical, it found real things on the very first run.

**Second test round (2026-07-18), deliberately an edge case: today's date, still in progress.** Found and fixed two more real bugs:
3. **Future-window truncation.** Requesting a window extending into the future (e.g. today, before the day is over) computed "expected readings" against the full nominal window, producing a misleadingly low coverage % that wasn't a real problem. Fixed: `analyze_coverage` now caps the expected-calculation window at the actual current time when the requested end is in the future, and the output JSON carries `window_truncated_to_now` so the narrative can say so explicitly. `SKILL.md` updated to call this out when true.
4. **Cross-sensor contamination — more serious, and retroactive.** The Environmental Data sheet is shared across every JCTsh environmental sensor (`source` column distinguishes them), and the fetch script wasn't filtering by it. Testing today's date turned up 270 rows that were **entirely** `front-porch-temp-sensor`, not hiking-monitor — which would have been reported as hiking-monitor activity. Re-checked the already-published June 15 summary against this: **4,270 of its original 6,202 "hiking-monitor" rows were actually front-porch-temp-sensor.** Added a `--source` filter (default `hiking-monitor`) to `fetch_hike_data.py`, defaulting out any other source and reporting what else was seen but excluded. **`hike-izer/summaries/2026-06-15_hike-summary.md` regenerated with corrected numbers** (coverage 57.4%→17.9%, temp/humidity ranges narrowed, and a real ~10-hour Environmental Data gap on June 17 surfaced that had been masked by the other sensor's readings filling the same time slots) — the file carries its own correction note.

**Second real output, and a genuinely different kind of finding:** `hike-izer/summaries/2026-07-18_hike-summary.md`. Zero hiking-monitor Environmental Data readings all day, despite 7 Hiking Observations and 1 GPS point clearly showing a real walk happened (phone-based logging, no device). Since the same shared sheet has 270 `front-porch-temp-sensor` readings for the same day, this points at the hiking-monitor device itself (not deployed/charged/powered on?), not the pipeline — a different, useful class of signal than the coverage-percentage findings from the June 15 run.

**Model + presentation refinement (2026-07-18, Joseph's direction):**
1. **Feet is now the primary (only) unit for elevation** — `fetch_hike_data.py` converts `altitude_m` to `alt_ft`/`stats.altitude_ft` internally; the raw meters value from the sheet is never surfaced in output. Added a `compute_stats()` function to the script so temp/humidity/pressure/UV/battery/altitude ranges are computed once, consistently, rather than re-derived ad hoc each time.
2. **A hiking event is now defined as a single calendar day**, even a multi-day trip is a *series* of single-day events, not one combined report. `SKILL.md` rewritten around this: fetch the full requested range once, identify which individual days have real activity (a GPS session in practice), generate one `<date>_hike-summary.md` per active day. **Edge case handled:** a GPS session crossing UTC midnight (June 17 23:51 → June 18 02:59, confirmed real) is attributed to the day it *started*, not split into two partial, confusing day-summaries — verified by testing that querying June 17 alone only caught the first 8 minutes of that session.
3. **Non-redundant narrative rule added to `SKILL.md`:** the data table carries the numbers; the narrative synthesizes/interprets/draws conclusions rather than restating figures already sitting in a table two sections down.

**Summaries restructured to match:** the old combined `2026-06-15_hike-summary.md` (spanning the whole ~2-week query range) removed, replaced with `2026-06-17_hike-summary.md` and `2026-06-18_hike-summary.md` — the two actual hiking days, computed by partitioning the already-fetched dataset (Environmental Data bucketed by calendar day, GPS sessions attributed by start day) rather than re-querying per day, exactly as `SKILL.md` now prescribes. New finding from the properly-split data: **battery voltage declined day-over-day (3.97–4.36V on June 17 → 3.00–4.00V on June 18)** — a real trend, not noise, and an earlier data point in the same LiPo failure this trip is already known for.

**Hike-vs-not-a-hike classification added (2026-07-18, Joseph's direction).** Raised directly by the June 17 session: Joseph doesn't hike at night, so a gap-based GPS cluster alone isn't good enough evidence that a hike happened — it could be a drive, camp-site GPS drift, or (worth naming, since it's the actual constraint) genuinely happening in the dark. Added `_classify_hike()` to `fetch_hike_data.py`: every candidate GPS session must pass **both** a daylight check (≥80% of points at civil twilight or brighter, sun elevation > -6°) and a walking-pace check (median point-to-point speed 0.15–3.0 m/s / ~0.3–6.7 mph, computed via haversine distance) to count as `is_hike: true`. Sessions that fail carry `rejection_reasons` rather than being silently dropped — including a distinct "insufficient data" reason for single-point sessions (a session with 1 point has no speed pairs to compute; defaulting that to "0 m/s = stationary" would overstate what's actually known, so it gets its own honest reason instead). `coverage.gps_track.hike_confirmed` is `true` if any session that day passes both checks.

**Verified against real data both directions:** the two known-real hikes (June 17 evening, June 18 morning) both correctly classify `is_hike: true` (June 17's median speed came out to a low-but-passing 0.15 m/s — right at the threshold, consistent with a stop-and-start evening hike, not a red flag). July 18's lone GPS point correctly classifies `is_hike: false` with the new "insufficient data" reason rather than a misleading "stationary" one.

**`SKILL.md` updated with a new "What counts as a hike" section and an explicit "unable to confirm" output path** — when `hike_confirmed` is `false` for a requested day, the Skill must say so plainly and explain why (using the real `rejection_reasons`), rather than writing a normal hike narrative or silently producing nothing. `hike-izer/summaries/2026-07-18_hike-summary.md` rewritten to follow this path properly, now citing the actual classification output instead of the ad hoc framing used before this logic existed.

**Related:** `components/hiking-monitor/gps-pipeline.md`, `components/hiking-monitor/data-pipeline.md`, `components/hiking-monitor/hiking-logger.md`, CARD-0020 (Looker Studio dashboard, complementary).

**Resolution (2026-07-18):** closing as **version 1 done**. Core loop fully built and verified against real data, not left on paper: fetch → source-filter (`hiking-monitor` only) → hike classification (daylight + walking-pace checks, honest "unable to confirm" path when nothing passes) → single-day narrative with non-redundant tables and an explicit expected-vs-actual coverage/health section, elevation in feet throughout. Along the way, found and fixed real bugs — wrong GPS column names, misleading multi-day coverage math, future-window truncation, and cross-sensor contamination that had silently corrupted the first published summary — exactly the "awareness of how components are operating" goal from the original ask, working in practice, not hypothetically. Remaining ideas (photos, historical weather, hiker's compass/heading, automatic triggering, rendered HTML output) are real but represent v2, not blockers on calling v1 done — split out to **CARD-0074**, which also needs the hiking-monitor device itself operational again (it produced zero readings on 2026-07-18) before it can be built against fresh real data.

**Closed 2026-07-18 — Joseph directed the close.**

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

**Notes:** The hiking-monitor's actual standby battery life is unknown. The ESP32's own deep-sleep draw is negligible (~10µA), but `VOUT+` runs directly to the ESP32's `VIN` with the switch NOT in the power path, so the TP4056+boost module stays active even while the ESP32 sleeps — its quiescent current (undocumented by the manufacturer, plausibly 1-5mA for a cheap module) is almost certainly the real bottleneck. This measurement gives an actual number instead of a guess.

**Reuses the CARD-0025 tester rig** (spare ESP32 from Bag 1 + spare TP4056 from Bag 8) — build both cards in the same bench session.

**Setup:**
1. Flash the spare ESP32 with `hiking-monitor.yaml`, but change `esphome: name:` first (e.g. `hiking-monitor-test`) so it doesn't collide with the real device's hostname/MQTT identity. First flash must be via USB.
2. Tie **GPIO32 (dock detect) directly to GND** with a plain jumper — no divider needed for this test. This deterministically signals "no USB present" so the boot logic reliably proceeds into sleep instead of possibly floating and staying awake.
3. Leave **GPIO27 (slide switch) unconnected** — its internal pull-up reads HIGH by default, which the inverted logic treats as "switch OFF," also matching the sleep condition.
4. Sensors (BME280, LTR-390, display) don't need to be attached — I2C read errors will log but won't block the boot sequence from reaching the sleep-entry check.
5. Wire power as in CARD-0025: battery → TP4056 BAT input, TP4056 boost output → spare ESP32 VIN/GND.

**Measurement:**
1. Break the battery's positive lead and insert a multimeter in series (DC current mode, mA/µA jack — not the unfused high-current jack).
2. Power on. The `on_boot` priority -200 block should take it into deep sleep within a few seconds.
3. Wait a few seconds past that point, then read the steady-state current — that's the real standby draw.
4. Runtime estimate = 1100mAh ÷ measured current (mA), in hours.

**Outcome:** If the reading confirms the boost module's quiescent current dominates (likely 1-5mA range), consider this as supporting evidence for JCTsh-Build-Standards.md §2.14 point 7 (prefer direct LiPo-to-LDO over boost-then-buck for future builds) — the always-on boost stage is exactly what that recommendation exists to eliminate.

**Progress (2026-07-14):** Bench session started.

- **Test build:** created `C:\esphome\hiking-monitor-test\hiking-monitor-test.yaml` (renamed copy of `hiking-monitor.yaml` — `esphome:name: hiking-monitor-test`, own MQTT topic prefix `jctsh/components/hiking-monitor-test`, no collision with the real device). Config validated clean.
- **First spare ESP32 (Bag 1) — confirmed defective, discarded.** USB flash consistently failed with `esptool`: "Failed to communicate with the flash chip" — same failure across two cables, two ports, and manual BOOT-button bootloader entry, ruling out cable/port/timing as the cause. Confirmed hardware fault by successfully flashing a second spare board with an identical setup. Logged in `jctsh-parts-inventory.md` (v2.17, qty 8→7, discarded not returned to stock).
- **Second spare ESP32 — flashed successfully.**
- **Setup Steps 2-5 complete:** GPIO32→GND jumper, GPIO27 left unconnected, sensors not attached, battery→TP4056 BAT→boost output→ESP32 VIN/GND wired.
- **First reading: 0.03mA (30µA), steady.** All 4 wiring checkpoints re-verified (battery→TP4056 connection solid, meter correctly in series on battery+ lead, TP4056 VOUT — not BAT input — wired to ESP32 VIN/GND, meter dial+jack correctly on DC mA/µA) — wiring confirmed correct.
- **Reading is suspiciously good, not yet trusted.** ESP32's own deep-sleep draw (with both ext0/ext1 wakeup active) is plausibly 10-150µA alone, which could account for most of 30µA — but generic boost-converter ICs in these cheap TP4056+boost modules typically draw >1mA just keeping their regulation loop alive when actively switching. 30µA total suggests the boost stage likely **isn't actually engaging** under this near-zero sleep load (may be passing raw battery voltage through rather than truly boosting), rather than the module being unusually efficient.
- **Also unexplained:** no board LED lit at any point, including during boot — inconsistent with the real hiking-monitor's own documented behavior (onboard power LED is hardwired to 3.3V rail, stays lit through deep sleep per the CARD-0027 observation that motivated this whole investigation).

**Don't trust the 0.03mA reading until verified.** Decided against troubleshooting the existing rig in place — going to rebuild clean instead, ruling out a marginal/bad TP4056 module or a bad connection entirely rather than just checking voltages on a possibly-faulty setup.

**Next steps (resume here):**
1. Rebuild with a **fresh spare TP4056** (Bag 8) and **all-new connections** — battery→TP4056 BAT, TP4056 boost output→ESP32 VIN/GND, meter in series on the battery+ lead. Same working ESP32 (already flashed, no need to reflash).
2. Re-run the measurement (Measurement Steps 1-4 above) on the rebuilt rig.
3. If the new build still reads implausibly low (~30µA) and still shows no board LED: measure TP4056 VOUT+/VOUT− voltage (expect ~5V boosted, not raw ~3.7-4.2V battery voltage) and ESP32's 3V3 pin voltage to pin down whether the boost stage is actually engaging.
4. If the new build reads meaningfully higher (closer to the originally-feared 1-5mA range): that's likely the real number — the first rig probably had a bad TP4056 or a marginal connection. Proceed to the runtime calculation (Measurement Step 4) and CARD-0027's sequencing decision.

**Progress (2026-07-16) — root cause of the suspicious 30µA reading found: a blown fuse in the ammeter itself, not the TP4056 or wiring.**

Rebuilt clean with a fresh TP4056 and all-new connections per Next Step 1 — got the *identical* 0.03mA reading again, and VOUT+/VOUT− measured only 0.02V (not ~5V boosted, not even raw ~3.7-4.2V battery voltage — essentially zero). Forcing an active boot (disconnecting the GPIO32→GND jumper) didn't change either reading, which ruled out "boost auto-shuts-off under near-zero load" as the explanation — a module that dynamically responds to load should have reacted to a forced active-boot current spike, and it didn't.

Traced it properly instead of re-guessing: measured raw battery voltage directly (3.8V, healthy) vs. voltage at the TP4056's BAT+ input terminal (0.02V) — a ~3.8V drop at only 30µA implies roughly 126kΩ of resistance somewhere in between. Confirmed by measuring directly across the ammeter's own two terminals: 3.86V, meaning nearly the entire battery voltage was dropping *inside the meter itself*. **The ammeter's mA/µA fuse was blown.** Every "suspiciously good" reading across two separate, freshly-wired TP4056 rebuilds was never real hiking-monitor current at all — the TP4056 and ESP32 had been starved of real power the whole session, which is exactly why nothing else lined up (no LED, ~0V at VOUT, current not responding to a forced active boot).

**Switched to a second multimeter for current measurement (same rig, no rewiring needed).** First real result: ESP32's onboard LED lit for the first time all session (real power finally reaching the board) — but current bounced 109-154mA continuously and never settled, even after a full minute-plus and even after power-cycling with GPIO32 freshly reconnected to GND.

**Diagnosed via USB serial log** (`esphome logs hiking-monitor-test.yaml`, one diagnostic power cycle — current reading invalid during this cycle since USB power dominates, that's expected and fine): boot proceeded cleanly on USB power — BME280/LTR-390 failed to respond (expected, sensors not attached for this test), MQTT failed to resolve the broker address (`Error resolving broker IP address: -6`, non-fatal, noted but not investigated further), and the device reached `[I][deep_sleep:057]: Beginning sleep` in about 1 second. Firmware sleep-entry logic is confirmed correct and fast.

Re-tested on battery power alone (USB disconnected, fresh reset): still bouncing 100+mA, never settling — same as before USB confirmed the firmware works. Since USB (stable 5V) sleeps cleanly every time and battery/boost power never does, root cause is almost certainly a **brownout-reset loop**: the boost module's output sags under the ESP32's active-boot/WiFi current spike (~100-250mA bursts), dips below the brownout threshold, forces a reset, and the cycle repeats indefinitely — the device never completes one full boot-to-sleep cycle on battery power alone.

**Worked around it with a hot-swap methodology** rather than trying to fix the module: booted on USB, let it reach `Beginning sleep` and settle for a couple seconds, then disconnected USB *without resetting the board* while the battery/TP4056/meter circuit stayed connected throughout (already powering the board in parallel). This sidesteps the problem entirely — the boost module only had to sustain deep sleep's tiny steady current, never the active-boot spike it can't handle.

**Result: 22.6mA steady, on the 200mA range (nowhere near overload), LED lit.** Confirmed LED-lit is *expected* for genuine sleep, not a red flag — deep sleep only stops the CPU, it doesn't cut power to the 3.3V rail the LED is hardwired to, exactly matching CARD-0027's original observation on the real device. Runtime estimate: 1100mAh ÷ 22.6mA ≈ **48.7 hours, roughly 2 days** — worse than the original 1-5mA estimate that motivated this measurement (which would have implied 9-46 days).

**Important caveat — this brownout-reset-loop behavior has never been observed on the real, field-deployed hiking-monitor** (carried on a two-week camping trip, field-proven per CARD-0008). That strongly suggests this specific failure mode belongs to *this test rig's spare TP4056 module* (Bag 8), not the real device's own installed module — plausibly the same kind of unit-quality issue as the spare ESP32 that had to be discarded earlier in this same bench session. Since this module also can't handle load the way the real device's module apparently does, its idle/quiescent characteristics may not be identical either — poor load regulation and higher quiescent draw often correlate in cheap parts, but it's not guaranteed. **22.6mA should be treated as a real, valid measurement of this test rig's specific module, not a confirmed number for the real hiking-monitor's own module.**

**Also not accounted for:** BME280 and LTR-390 aren't attached to this test rig. Per typical datasheet specs each would add roughly tens to a few hundred µA of additional idle draw on the real device — small relative to the 22.6mA boost-module-dominated total, but real. Net effect: the real device's actual sleep current is probably somewhat *higher* than 22.6mA, not lower, meaning real standby life is probably somewhat *less* than the 48.7-hour estimate.

**Worth flagging separately:** if Bag 8's spare TP4056 stock has a batch-quality issue, it's relevant to any other component build that reuses it (remote-temp-sensor-01, air-quality-monitor's clip-case).

**Outcome:** boost module's quiescent current confirmed as the dominant factor in standby drain, strong evidence for CARD-0027's proposed peripheral power-gating fix — though since the boost stage itself (not just the peripherals) is the measured bottleneck here, a fix that only gates BME280/LTR-390/display power wouldn't address the biggest contributor unless it also cuts the boost stage. Worth revisiting CARD-0027's scope with this in mind.

**Closed 2026-07-16:** measurement scope is complete — real number obtained (22.6mA), method verified, caveats documented. The open question of whether this number holds for the real device's own TP4056 module is no longer blocking closure: CARD-0070 (LDO swap) now owns that verification as part of its own "done when" criteria (real hiking-monitor must boot and reach sleep normally on the new power path), so it doesn't need a separate open card here.

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

### CARD-0069 · [bug] [infrastructure] log_server.py silently drops heartbeat-only components' messages — RESOLVED 2026-07-15
**Status:** Done

**Notes:** Raised 2026-07-15, found while checking on CARD-0068's netalertx changes at Xerocraft (accessed remotely via Tailscale). `netalertx` appeared completely silent on the log dashboard since 20:36 the prior evening — 14+ hours, no heartbeat displayed anywhere — despite `/status` showing it "Online, 4m ago." Root-caused directly on the Pi (SSH via Tailscale), not guessed:

1. Confirmed Node-RED's flow is healthy and correct — `netalertx.flow.json`'s wiring matches the source exactly (pulled the live `flows.json` and diffed against the repo copy), the watchdog's own timer-reset log entries prove the machine-readable heartbeat (`jctsh/components/netalertx/heartbeat`) fires every 5 minutes as designed.
2. Live-captured MQTT traffic with `mosquitto_sub` and directly observed a real `Heartbeat - 35 online, 0 down, 49 total, 1 new` message hit `jctsh/components/netalertx/log` — the publish is genuinely happening.
3. Confirmed via `state.json`'s mtime that `log_server.py` *does* receive and process the message (`_store_entry` runs to completion, updates `_last_seen` — which is why `/status` looked fresh) — but it never reaches `_entries` or the log file.

**Root cause:** `_store_entry()`'s heartbeat-collapsing logic (`core/logging/log_server.py`) only flushes a component's pending heartbeat group to the visible log when either (a) `_heartbeat_state_key()` detects a state change — only fires for ON/OFF-style or `Watchdog: `-prefixed messages, not netalertx's "N online, N down" text, which always collapses to the same key — or (b) a *different, non-heartbeat* message arrives from that component, which flushes the pending group as a side effect before processing the new one. There is no periodic/timeout-based flush anywhere — `_flush_all_hb_groups()` is only ever called from the server's shutdown path.

Before CARD-0068, netalertx's frequent online/offline presence messages incidentally served as that flush trigger, which is why heartbeats always eventually appeared. CARD-0068 removed those (correctly, per that card's own reasoning), leaving netalertx with *only* same-shape heartbeats and a rare new-device alert — nothing left to ever trigger a flush. The heartbeat group now accumulates silently in memory indefinitely. This is a latent gap in `log_server.py` that CARD-0068 exposed, not a defect introduced by CARD-0068's own change — any future component that only ever sends constant-text heartbeats (no periodic non-heartbeat traffic) would hit the same silent-drop behavior.

**Fix direction:** add a periodic background flush — a lightweight thread (similar to the existing `_heartbeat_thread`) that walks `_hb_groups` and flushes any group whose last update is older than a threshold, regardless of whether new traffic arrives. General fix, not netalertx-specific — protects any current or future heartbeat-only component.

**Correction while checking the live dashboard (2026-07-15):** the main `/` dashboard was actually **not** silent — `_snapshot()` already renders unflushed `_hb_groups` entries live, so netalertx's heartbeat was visible there the whole time, just as one never-rotating accumulating line (confirmed: `Heartbeat ×180 [20:41–11:31] — 35 online, 0 down, 49 total, 1 new` before the fix). The actual gap is narrower than first framed: the `/log` raw-text history, the persisted `state.json` (lost on restart), and `/status`'s "last message" column never update, because none of those read from the live in-memory group — only from `_entries`, which the group never reaches without a flush trigger. Root cause and fix direction are unchanged; only the "completely silent" framing needed correcting.

**Implemented and deployed (2026-07-15):** added `HB_GROUP_STALE_SEC` (900s) and a new `_hb_flush_thread` (checks every 60s via `HB_FLUSH_CHECK_INTERVAL`) that calls `_flush_stale_hb_groups()` — walks `_hb_groups`, flushes any group whose `_last_update` (new field, stamped on every heartbeat update) is 15+ minutes stale, regardless of whether new traffic arrives. Also generalized the internal-field filtering in `_flush_hb_group`, `_save_state`, and `_snapshot` from the narrow `k != "_state_key"` check to `not k.startswith("_")`, so the new `_last_update` field (and any future internal field) doesn't leak into persisted state or rendered output automatically.

Deployed via `scp` to the Pi, syntax-verified (`py_compile`), `sudo systemctl restart jctsh-logging`. The restart itself exercised the existing shutdown-flush path and correctly wrote the accumulated `Heartbeat ×180 [20:41–11:31]` group to `jctsh.log` for the first time — direct proof the flush mechanism works end-to-end, not just unit-level reasoning. Going forward, new heartbeat groups will self-flush every ~15 minutes instead of accumulating indefinitely.

**Regression check across other components (2026-07-15) — bug turned out to be system-wide, not netalertx-specific.** The same restart-triggered flush surfaced multi-hour stuck heartbeat groups for *every* other component, not just netalertx:
- `garage-radar`: `Heartbeat ×11 [06:18–11:18]` — 5 hours stuck (its heartbeat only flushes on an actual presence ON/OFF flip in the message text; Sensor-category presence-detected/cleared messages are explicitly excluded from triggering a flush, by design, so a long stretch of steady presence never flushed)
- `salt-sensor`: `Heartbeat ×41 [15:28–11:28]` — 20 hours stuck
- `front-porch-temp-sensor`: `Heartbeat ×29 [21:04–11:04]` — 14 hours stuck
- `photo-server`: `Heartbeat ×41 [15:07–11:09]` — 20 hours stuck

All five flushed cleanly with formatting identical to the pre-fix collapse pattern (`Heartbeat ×N [start–end] — ...`) — no corruption, no stray internal fields leaking, no double-counting. This confirms the fix is a genuine systemic correction (every component's history was going stale for arbitrarily long stretches whenever nothing flush-triggering happened to occur), not a netalertx-only patch, and validates itself against real production data across five components at once rather than just netalertx's case. No regressions found.

**Real bug found in the first fix itself (2026-07-15, checked ~4 hours later per Joseph's request).** No new flush had happened in almost 4 hours — the first implementation was broken. Root cause: it compared elapsed time against `_last_update`, a field stamped on **every** incoming heartbeat, including the "same state, update in place" branch. Since netalertx heartbeats arrive every 5 minutes without fail, `_last_update` never got more than ~5 minutes old — the staleness clock kept getting reset by the very heartbeats it was supposed to eventually flush, so the group could never reach the 15-minute threshold. Functionally identical to the original bug this card exists to fix, just with a much longer (but still infinite) timeout.

**Corrected (2026-07-15):** switched from an idle-time check (`_last_update`, refreshed every message) to an age-based check (`_started_at`, stamped only once when a group is first created, never touched again). `_flush_aged_hb_groups()` (renamed from `_flush_stale_hb_groups`) now flushes a group once it's been open `HB_GROUP_MAX_AGE_SEC` (900s), regardless of how recently it was last updated — forcing periodic rotation even for a component that heartbeats forever without ever going quiet.

**Live-verified with a fast, deterministic test rather than another blind multi-hour wait** — temporarily dropped `HB_GROUP_MAX_AGE_SEC` to 90s (same "shorten the timeout, verify, restore" pattern the watchdog flow's own README already documents for testing its 35-minute timeout), redeployed, and within ~5 minutes observed a brand-new group (a single fresh heartbeat, `count=1`, no `×N [range]` collapse — proof it hadn't been accumulating) get flushed immediately once it crossed the 90-second age mark: `2026-07-15 15:16:20 MST | netalertx | System | Heartbeat - 39 online, 0 down, 49 total, 1 new`. This is unambiguous proof the age-based flush fires independent of continued traffic, not just reasoning about the code. Restored `HB_GROUP_MAX_AGE_SEC` to 900, redeployed, confirmed service running cleanly.

**Confirmed at real production cadence (2026-07-15).** A fresh group formed right after the 15:21:11 restart and self-flushed exactly 15 minutes later with no manual trigger, no shortened threshold, no other message arriving to force it: `2026-07-15 15:36:20 MST | netalertx | System | Heartbeat ×4 [15:21–15:36] — 39 online, 0 down, 49 total, 1 new`. This is the real-world confirmation the card was waiting on — mechanism verified at both the fast test threshold and the actual production threshold. All closing criteria met: fix implemented, deployed, a genuine bug in the first attempt found and corrected, verified live twice (fast deterministic test + real cadence), and regression-checked clean across every other component (garage-radar, salt-sensor, front-porch-temp-sensor, photo-server).

**Resolution:** `log_server.py`'s heartbeat-collapse logic now rotates any pending group after 15 minutes regardless of continued traffic, closing a systemic gap that was silently truncating history for every component, not just netalertx. Verified live at both a fast test threshold and the real 15-minute production cadence, with a genuine bug in the first fix attempt found and corrected along the way rather than assumed working.

**Closed 2026-07-15 — Joseph confirmed and directed the close.**

---

### CARD-0060 · [bug] [infrastructure] Pi running in active soft thermal throttling &mdash; no cooling &mdash; RESOLVED 2026-07-15
**Status:** Done

**Notes:** Found 2026-07-12 during a Pi health evaluation. `vcgencmd get_throttled` returns `0x80008` (bit 3: soft temperature limit *currently active*; bit 19: has occurred) at a measured 63&ndash;64&deg;C, confirmed on two separate checks. No under-voltage bits set &mdash; power supply is fine, this is purely thermal. No heatsink/fan apparent on this Pi 3B+. Likely compounded by an enclosed/warm install location, matching the pattern of other JCTsh closet-installed devices (photo-server M8, KeepConnect).

**Impact:** the Pi is right now running with reduced ARM clock speed to manage heat. Not causing instability (uptime is solid, no OOM/crash pattern), but is a real, currently-active performance ceiling on the device that hosts Home Assistant, Node-RED, Mosquitto, and the JCTsh log/watchdog server for the whole fleet.

**Location context (2026-07-12):** the Pi sits on a shelf near a 9-foot ceiling in the laundry room, in a plastic case of unknown internal heatsink status &mdash; Joseph doesn't want to open the case to check/add an internal heatsink. Chose an external-airflow approach instead of a case teardown: some of the heat load is plausibly ambient hot air pooling at ceiling height (heat rises) rather than purely the case trapping the Pi's own heat, so moving air across the whole shelf addresses both causes at once and benefits every device up there, not just the Pi.

**Resolution path (revised, no disassembly):** install a continuous-duty USB-powered fan on the shelf, aimed to move air across the shelf and out toward open room space (not just recirculate warm air in place against the ceiling). Recommended: **AC Infinity MULTIFAN S5** (single 80mm, ~52 CFM, dual ball bearings rated ~67,000 hours/~7.6 years continuous duty, USB powered, includes speed controller) &mdash; purpose-built for quiet electronics-cabinet cooling, enough real airflow to matter across an open shelf, unlike gentler terrarium-style USB fans. Step up to the **MULTIFAN S7** (multi-fan set) if one fan's throw doesn't cover the full shelf width. Power the fan from its own USB wall adapter or hub, not from the Pi's own USB ports, to avoid adding current draw to the Pi's own power rail (it currently shows no under-voltage flags &mdash; keep it that way). One ongoing maintenance item: it's a laundry room, so dryer lint will accumulate on the fan grille/blades over months of continuous running &mdash; an occasional wipe-down keeps airflow effective.

**Don't close until:** fan is physically installed and `vcgencmd get_throttled` is re-checked under normal and sustained-load conditions, confirming bit 3 ("soft temperature limit currently active") clears. **Holding verification until Joseph has the fan in place** &mdash; not yet done.

**Pre-install baseline (2026-07-14):** checked temps across the equipment shelf before the fan goes in, both to confirm the Pi's condition is unchanged and as a data point on the shelf-wide-heat-pooling theory.

- **Pi:** 64.5&deg;C, `throttled=0x80008` &mdash; unchanged from the 2026-07-12 finding, still actively soft-throttling.
- **M8 (photo-server), also on this shelf:** running well within normal range &mdash; CPU (real `k10temp` sensor, not the unreliable `acpitz` dummy) 39.3&deg;C, NVMe 40.9/41.9/33.9&deg;C, GPU 38.0&deg;C, 2.5GbE controllers 39.5/43.5&deg;C, WiFi 6E 38.0&deg;C. Worth noting against the shelf-wide-heat-pooling theory: if ambient heat pooling at ceiling height were the dominant factor, expected the M8 to be running warmer too. Doesn't rule the theory out &mdash; the Pi's plastic case with no heatsink at all is far more heat-sensitive than the M8's own active cooling &mdash; but the M8 isn't showing any distress from the shared shelf environment.
- **External USB HDDs (Backup Plus, Momentus, spare Seagate) &mdash; could not check:** needs `smartctl`, not installed; `sudo` on the M8's `jct` account requires an interactive password not available here.
- **Router (TP-Link Archer AXE75) &mdash; could not check:** no SSH/API access on this consumer router; admin web UI already confirmed undrivable via browser automation during CARD-0003.

**Post-install check (2026-07-14, a few hours after fan install):** significant improvement.

- **Pi:** 64.5&deg;C &rarr; **48.9&deg;C** (15.6&deg;C drop). `throttled`: `0x80008` &rarr; **`0x80000`** &mdash; bit 3 ("soft temperature limit *currently active*") is now clear, meeting the card's closing criteria. Remaining bit 19 is just the sticky "has occurred since boot" historical flag; it stays set until next reboot regardless of current temp and doesn't indicate ongoing throttling.
- **M8:** unchanged, still healthy (CPU 39.1&deg;C, NVMe 41.9&deg;C, GPU 37.0&deg;C) &mdash; as expected, confirms it was never the concern.

**Still open before closing:** this check was under normal conditions a few hours post-install, not explicitly a sustained-load test as the closing criteria also calls for. Pi's steady 24/7 workload (HA, Node-RED, Mosquitto, log/watchdog server) arguably already constitutes real sustained load rather than a synthetic spike, but worth a check-in after a longer period (a day or more) to confirm bit 3 stays clear rather than closing on a single few-hours-later reading.

Joseph is installing the fan next; re-check `vcgencmd get_throttled` afterward per the closing criteria above.

**Progress (2026-07-12):** Joseph ordered the **AC Infinity MULTIFAN S7** &mdash; dual 120mm (larger than the single-80mm S5 suggested above), UL-certified, marketed for receiver/DVR/console/computer cabinet cooling. Larger fans, more shelf coverage &mdash; a reasonable upgrade over the original suggestion. Not yet installed; verification still pending arrival/install.

**Sustained-load re-check (2026-07-15), checked remotely via Tailscale (Joseph at Xerocraft):** roughly a day after the 2026-07-14 post-install check, under the Pi's normal steady 24/7 workload &mdash; the sustained-load condition the earlier check was missing.

- **Pi:** `throttled=0x80000` &mdash; bit 3 ("soft temperature limit *currently active*") still clear, confirming the 2026-07-14 result wasn't a fluke. Temp **47.2&deg;C**, consistent with the post-install reading (48.9&deg;C), not drifting back up. Bit 19 remains set (sticky "has occurred since boot" flag) &mdash; expected, clears only on next reboot, not a sign of ongoing throttling.
- **M8 (photo-server):** still healthy &mdash; CPU (`k10temp` Tctl) 40.8&deg;C, GPU 36.0&deg;C, NVMe 40.9/31.9&deg;C, 2.5GbE 41.5/37.0&deg;C, WiFi 6E 34.0&deg;C. `lm-sensors` was reinstalled on photo-server for this check (it wasn't present in this session; installed via `apt-get install lm-sensors`, same real `k10temp` source as the 2026-07-14 baseline, not the unreliable `acpitz` dummy).

**Resolution:** fan install (AC Infinity MULTIFAN S7) confirmed effective across two separate checks a day apart &mdash; both under real sustained load, not just a synthetic spike. Soft thermal throttling is no longer active. Closing criteria fully met.

**Closed 2026-07-15 &mdash; Joseph confirmed and directed the close.**

---

### CARD-0063 · [idea] [infrastructure] NetAlertX MQTT event richness experiment + log dashboard wiring — RESOLVED 2026-07-14
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

### CARD-0049 · [enhancement] [salt-sensor] Move from breadboard to perfboard — RESOLVED 2026-07-13
**Status:** Done

**Progress (2026-07-10):** Follow-on to CARD-0004 (ESPHome migration). Moved all three LEDs off their original breadboard pins onto a perfboard-friendly layout: Red GPIO2→GPIO32, Yellow GPIO15→GPIO33, Green GPIO4→GPIO27 — gets Red/Yellow off strapping pins entirely and lines all three LEDs up on the same header row (left pins 7/8/11) for easier soldering. GPIO25/26 (DAC1/DAC2) were considered since they sit physically between GPIO32/33 and GPIO27, but ruled out — GPIO25 is confirmed broken for digital output in ESPHome/Arduino, GPIO26 avoided as a precaution for the same DAC-reinit reason. Trig (GPIO5) and Echo (GPIO18) unchanged.

Updated `salt-sensor.yaml` (wiring comment + `output:` block), `components/salt-sensor/CLAUDE.md`, and `components/salt-sensor/ESP32-project-pins.md` to match. Physical rewiring done; reflashed over OTA and field-verified — LEDs confirmed matching the `ok` status (green solid, red/yellow off) on the new pins, MQTT `/data` and `/status` reporting normally post-flash.

**Planning (2026-07-13):** wrote `components/salt-sensor/perfboard-layout.md` — modeled on hiking-monitor's perfboard-layout.md (Assembly Sequence → Pre-Power Checks → power-on/reboot verification), scaled down for salt-sensor's much simpler circuit (no I2C, no battery chain, no display). Worked through bus planning explicitly before the soldering steps: a ground bus is warranted (5 consumers: 3 LEDs, JSN-SR04T GND, Echo divider) and gets built with 2 spare tap points for future additions; a 5V/VIN bus is *not* warranted (only one consumer beyond the source — a direct point-to-point wire is equivalent and simpler); confirmed no other net (each LED drive line, Trig, Echo) has 3+ consumers, so no other bus is warranted either. 12-step assembly sequence, 18-check pre-power continuity/resistance table, and an explicit power-cycle verification section (cold USB unplug/replug, not just an OTA soft reboot — twice clean, minimum) all written into the doc.

**Build (2026-07-13):** Soldered per `perfboard-layout.md`'s Assembly Sequence — walked step by step interactively (each solder joint confirmed before proceeding to the next).

**Real issue found and fixed:** the physical ESP32 board in hand is a **SparkleIoT XH-32S** module, whose silkscreen pin *order* doesn't match `ESP32-project-pins.md`'s documented position numbering — same GPIO count, different physical layout, despite both nominally being "38-pin ESP32 DevKitC-32" boards. This wasn't caught until mid-build: the Trig wire had been soldered to the pad labeled `RX2` instead of `D5` (the two sit adjacent in a crowded cluster — `D18, D5, TX2, RX2, D4`), found only because Pre-Power Checks were done by reading the actual printed labels rather than trusting the documented table. Fixed by re-soldering Trig to the correct `D5` pad. `D18` (Echo) was double-checked at the same time and confirmed correct. Reference photo of the actual board saved to `components/salt-sensor/sparkleiot-xh-32s-pinout-photo.jpg`.

**Pre-Power Checks:** 19 checks run (not the originally-planned 18) — 2 checks from the hiking-monitor-derived template were dropped as not applicable (this board has no separate USB power-in header; power enters through the ESP32's own onboard USB port), and 3 new isolation checks were added on the spot (`D32`↔`D33`, `D5`↔`D18`, `D5`↔`RX2`, each expected open/no-beep) prompted directly by the `RX2`/`D5` mistake — confirming no solder bridge existed between visually-adjacent pins. **All 19 passed.**

**Power-on test:** LED self-test observed, `Online — ESPHome 2026.4.5, IP: 192.168.1.181, MQTT connected`, `/data` publishing `Salt: 95% (21.5 cm)` — same value as CARD-0049's original 2026-07-10 breadboard field verification, confirming the Echo divider (part of what got fixed) is producing sane readings. LED status confirmed matching (`ok` → solid green, red/yellow off).

**Resolution — reboot/power-cycle verification:** two clean cold power-cycles (physical USB unplug/replug, not just an OTA soft reboot, since this board is USB-powered not battery — a cold cycle exercises WiFi/MQTT reconnect and the LED self-test's boot path a warm reboot wouldn't). Cycle 1 (15:06 MST) and Cycle 2 (15:08 MST) both clean: LED self-test, MQTT reconnect, `Salt: 95% (21.5 cm)` both times. Both closing criteria (perfboard soldered + verified, survives power-cycle on new pins) now met.

**Reflection:** `components/salt-sensor/perfboard-layout.md` rewritten to reference pins by printed label instead of the wrong position numbers, with a prominent Board Note explaining the mismatch, all check results recorded, and the 3 new isolation checks made permanent. Harvested the generalizable lesson into `JCTsh-Build-Standards.md` §1.2 (v1.15): verify against a board's actual silkscreen labels rather than trusting a documented reference table, and add isolation checks between visually-adjacent pin labels to Pre-Power Checks as standard practice.

**Follow-up (2026-07-13):** `ESP32-project-pins.md` rewritten to match the actual SparkleIoT XH-32S board, organized by printed label with GPIO cross-reference (photo saved alongside it). `JCTsh-Perfboard-Build-Template.md` (new, repo root, Build Standards v1.16) generalizes the proven Assembly Sequence → Bus Planning → Pre-Power Checks → Reboot/Power-Cycle structure into a reusable skeleton for future perfboard builds, now that there are two real examples (hiking-monitor, salt-sensor) to draw from.

**Closed 2026-07-13 — Joseph confirmed and directed the close.**

---

### CARD-0066 · [enhancement] [photo-server] Verify legacy USB photo archive against Joseph's Immich library — RESOLVED 2026-07-13
**Status:** Done

**Notes:** Raised 2026-07-13. Joseph has a USB stick drive (E:) with a legacy photo archive — 941 `.jpg` files at the drive root (camera-original filenames like `CIMG0002.jpg`, dated 2002-2009), plus one unrelated `.exe` and several empty placeholder folders (`Documents/Pictures`, `Documents/Videos`, `Documents/Downloads`, `Documents/Music`, `System/Apps`, `System Volume Information`) — confirmed via direct inspection, no duplicate filenames within the 941. Wants to verify these are already in Immich (or upload whatever's missing) before wiping the drive, using the same checksum-based matching approach already established for the original Takeout migration (`components/photo-server/migration.md`) — matches skip, gaps upload, no separate dry-run needed.

**Plan:**
1. Copy the 941 `.jpg` files from `E:\` to `/home/jct/verify-batch-2026-07-13/` on the M8 (422G free, well clear of the ~164MB archive size).
2. Verify the copy (file count + total size match source) and notify Joseph once confirmed — he's wiping the USB drive himself right after, independent of the immich-go run finishing.
3. Run `immich-go upload from-folder` against Joseph's Immich library (API key in `credentials.local.md`) with `--session-tag` (tags newly-uploaded assets with a timestamped `{immich-go}/...` tag for review — chosen over `--into-album` since its semantics are unclear on whether skipped duplicates would also get swept into the album) and `--log-file /home/jct/verify-batch-2026-07-13/immich-go-verify.log`.
4. Report matched/uploaded/error counts back to Joseph.
5. Leave the staged copy and log **intact** on the M8 afterward — no cleanup step. This is a one-off ad hoc batch job, not a recurring/scheduled task.

**Other considerations flagged:**
- Matching is exact-checksum only (per the earlier discussion in this session) — if any of these camera-original files were also captured by the 2026 Google Takeout import in a re-compressed/re-processed form, they won't match here despite being the same photo content, and will upload as new assets. Not a bug, just a known limitation of checksum matching worth being aware of when reviewing the tagged results.
- These are old camera JPGs (2002-2009) — likely have usable EXIF dates for correct chronological placement; `immich-go`'s `--date-from-name` fallback (default on) wouldn't help here since these filenames don't encode dates, so any file missing EXIF may land with an inaccurate date. Worth a spot-check on a few results.

**Copy gotcha found and fixed (2026-07-13):** first `scp` pass used a case-sensitive `*.jpg` glob and silently copied only 787 of 941 files — the drive has a mix of `.jpg` and `.JPG` extensions, and Git Bash's default glob is case-sensitive, so all uppercase-extension files were skipped with no error. A first size-check also gave false confidence (`du -cb *.jpg | tail -1` on both sides was comparing the same case-filtered 787-file subset to itself, matching perfectly while still being wrong). Caught by cross-checking file *count* (941 via `find -iname`, case-insensitive) against the glob-based copy, which didn't match. Fixed: copied the missing 154 files with `shopt -s nocaseglob`, then re-verified with a case-insensitive, per-file byte sum (`find -iname '*.jpg' -printf '%s\n' | awk '{s+=$1} END{print s}'`) on both sides — confirmed exact match: 941 files, 154,096,152 bytes identical source and destination. General lesson: when verifying a copy, use case-insensitive matching consistently on both sides, and prefer a per-file byte sum over `du -cb | tail -1` (batching can silently truncate to the last chunk's total). Joseph confirmed the copy and wiped the USB drive.

**Resolution:** `immich-go upload from-folder` ran detached on the M8 (verified via `ps aux` after launch, not just the launcher's own exit code — same discipline as `migration.md`'s "killed background processes didn't actually die" lesson), completed in ~1 minute, zero errors. Reconciles exactly: **902 uploaded + 37 server-duplicates + 2 local-duplicates (two files in the batch were byte-identical to each other under different filenames) = 941.** All 902 new uploads tagged `{immich-go}/2026-07-13 10-...` for review in the Immich UI. Full log reviewed directly (not just the console summary) via `grep -iE 'error|warn|fail'` — no real errors; the only two "unknown file" warnings were the job's own `immich-go-console.out`/`immich-go-verify.log` files sitting in the scan directory, correctly recognized and skipped as non-photo files. Checked for the EXIF-date-fallback concern flagged above — zero matches for any date-fallback/no-EXIF warning pattern in the log, so no evidence any of the 902 uploads landed with an inaccurate date. Staged copy and log left intact at `/home/jct/verify-batch-2026-07-13/` on the M8 per the plan.

**Reflection:** generalized this into a reusable procedure — `components/photo-server/verify-and-retire-source.md` — covering the copy/verify/upload/review steps and both gotchas found here (case-sensitive glob dropping mixed-case extensions, `du -cb | tail -1` giving false confidence on a total). Indexed in `components/photo-server/README.md`'s doc table.

**Note for later:** Joseph spotted some visual duplicates by eye among the photos; not addressed by this card (out of scope — checksum matching only catches exact-byte duplicates, not near-duplicates/re-saves). Pointed to Immich's own built-in Duplicates view (CLIP-embedding based, already running, no new tooling) as the first thing to check whenever he's ready, with CARD-0028 already in Backlog for a more thorough standalone-tool pass if needed beyond that.

**Closed 2026-07-13 — Joseph confirmed and directed the close.**

---

### CARD-0065 · [bug] [hiking-monitor] Validate LTR-390 UV Index readings in real sunlight — RESOLVED 2026-07-13
**Status:** Done

**Notes:** Raised 2026-07-13. During post-CARD-0009-rework field testing, UVI read 0 (then 0.01) when the device was taken off dock power into "direct sunshine," raising concern about a wiring fault introduced by CARD-0009's STEMMA QT rework on the LTR-390. Split out as its own card rather than folded into CARD-0009, since that card scopes the enclosure/build work specifically and this is a sensor-correctness question that outlived it.

**Investigation:** ruled out, in order — enclosure/case blocking the sensor (device wasn't in the box), SDA/SCL swap from the STEMMA QT rework (wiring confirmed correct by direct inspection), and a loose STEMMA QT connector. BME280 (shared I2C bus) read normally throughout, narrowing any real fault to the LTR-390 itself. Sensor pointed straight at the sun and left to complete a full `update_interval: 2min` cycle — UVI climbed to **6.90**, a plausible value for clear midday sun. No hardware fault; the earlier near-zero readings were just pre-settle values from before the sensor had a clean, unobstructed, correctly-oriented exposure.

**Side finding:** the 5-minute heartbeat log message (`jctsh/components/hiking-monitor/log`) only reported uptime/RSSI/temp/battery — humidity, pressure, and UV index were invisible on the dashboard, which is why this diagnosis required reading the physical OLED instead of checking remotely. Expanded the heartbeat lambda in `hiking-monitor.yaml` to include all five BME280/LTR-390 readings (temp, humidity, pressure, UVI) plus battery, each NaN-safe.

**Resolution:** config validated clean (`esphome config`), OTA-reflashed successfully — device back online at 09:32:41 (`Online — ESPHome 2026.4.5, IP: 192.168.1.161, MQTT connected`). First post-reflash heartbeat (09:37:18) confirmed live on the dashboard: `Heartbeat - uptime: 0h 5m, RSSI: -59dBm, temp: 99.9°F, humidity: 32.7%, pressure: 931.7hPa, UVI: 6.92, batt: 4.00V` — all readings present, UVI holding steady near the earlier 6.90 reading.

**Closed 2026-07-13 — Joseph confirmed the new heartbeat message showed up on the log.**

---

### CARD-0003 · [enhancement] [infrastructure] TLS for Mosquitto (port 8883) — RESOLVED 2026-07-13
**Status:** Done

**Notes:** Port 1883 is internet-exposed via DuckDNS/port-forward with fail2ban, but credentials and sensor data are cleartext for any device using that path. TLS on 8883 eliminates this — scoped as a **split-port design**, not a fleet-wide switch: 1883 stays plaintext and LAN-only (not forwarded through the router), continuing to serve stationary home devices (garage-radar, salt-sensor, front-porch-temp-sensor, remote-temp-sensor-01, etc.) with no `secrets.yaml`/firmware changes needed. 8883 (TLS) becomes the *only* port forwarded via DuckDNS, used exclusively by devices that actually leave the home network — hiking-monitor today, air-quality-monitor once built (CARD-0012, "carried on hikes alongside the hiking monitor"). Steps: get Let's Encrypt cert for the DuckDNS hostname (certbot with duckdns plugin), add a TLS listener on port 8883 in mosquitto.conf, change the router port-forward from 1883→8883, add CA-cert trust config + updated broker port to the remote-capable devices' `secrets.yaml`/`mqtt:` block, reflash those devices only, update Node-RED broker node / HA MQTT integration if either connects over the forwarded path. CARD-0002 prerequisite complete.

**Decision rationale (2026-07-10):** considered reflashing the whole fleet uniformly vs. this split; chose the split because most devices are stationary and never traverse the internet-facing path, so fleet-wide TLS would add CA-cert config/maintenance to every device for no real exposure reduction on the stationary ones. This card protects only the internet-exposed path (roaming devices via DuckDNS/port-forward); it does not encrypt LAN-local port 1883 traffic for stationary devices — that residual, accepted risk is documented under CARD-0050, which was deprioritized 2026-07-10 on its own risk-analysis merits (see that card — CARD-0003 was mistakenly framed there at first as a substitute for it and later corrected).

**Unblocked (2026-07-10):** CARD-0004 (salt-sensor Arduino → ESPHome migration) is complete except one open verification item (12h reading cycle hasn't fired naturally yet) — doesn't block this card either way, since salt-sensor is a stationary device staying on plaintext LAN-only 1883 under the split-port design.

**Execution plan:** `C:\Users\jcthomas\.claude\plans\misty-fluttering-porcupine.md` (Claude Code plan file, not in this repo) — five phases: A) Pi/certbot cert issuance, B) Mosquitto TLS listener, C) router port-forward, D) hiking-monitor CA-trust config + OTA reflash, E) cutover + doc updates. Approved 2026-07-10.

**Progress (2026-07-10):** Phases A–C complete, Phase D in progress. Moved Planning → Build to reflect that this card skipped straight from an approved execution plan into live implementation, rather than following the Design (ESPHome Claude Code instructions) step that column normally implies.

**Progress (2026-07-13):** Phases A–D complete. Only Phase E (cutover + docs) remains.
- **Phase A (cert):** done. Retried past the earlier DuckDNS DNS flakiness (see prior note, now resolved) — cert issued for `jctsh.duckdns.org`, expires 2026-10-08. Deploy-hook (`core/mqtt/mosquitto-cert-deploy-hook.sh`, deployed to `/etc/letsencrypt/renewal-hooks/deploy/mosquitto-reload.sh`) copies renewed certs into `/etc/mosquitto/certs/` and restarts Mosquitto; `certbot renew --dry-run` and `certbot.timer` both confirmed working.
- **Phase B (Mosquitto TLS listener):** done. `core/mqtt/mqtt-tls.conf` deployed to `/etc/mosquitto/conf.d/`. Hit and fixed a real gotcha: `password_file`/`allow_anonymous` can't be redeclared per-listener when `per_listener_settings` is false (the default, and true here) — they're global once set in `local.conf`; redeclaring caused a "Duplicate password_file value" error. Fixed by dropping those lines from the new file. Verified: both 1883 and 8883 listening, TLS handshake against `localhost:8883` and against the public `jctsh.duckdns.org:8883` (from the Pi, exercising the real router path) both return a valid cert chain (`Verify return code: 0`).
- **Phase C (router forward):** done. New `8883 → 192.168.1.117:8883` rule added (Joseph, manually, via the router admin UI — browser automation couldn't drive this router's admin SPA, it never reached an "idle" state for the extension's tooling). Existing 1883 rule deliberately left in place until Phase E cutover.
- **Phase D (hiking-monitor):** done. `secrets.yaml` (`mqtt_ca_cert`, ISRG Root X1, expires 2030-06-04) and `hiking-monitor.yaml`'s `mqtt:` block (`port: 8883`, `certificate_authority`, `idf_send_async: false`) updated and compile clean. Device came back online 2026-07-13, unblocking the reflash. Hit two real snags getting the OTA to actually run: (1) `esphome run` from the repo path failed with `Detected a whitespace character in project paths` — same class of issue as the garage-radar build (`DEVLOG.md` 2026-05-20) — worked around via the existing whitespace-free mirror at `C:\esphome\hiking-monitor\`, but that mirror was stale (missing the TLS config/CA-cert changes entirely) and had to be re-synced from the repo copies of `hiking-monitor.yaml`/`secrets.yaml` before flashing, or it would have silently pushed the old plaintext-1883 config; (2) a leftover locked file in `.esphome/build/hiking-monitor/.pioenvs` from an earlier interrupted build blocked the clean step until manually removed. OTA upload succeeded, device rebooted. **Verified via Mosquitto log on the Pi:** old plaintext-1883 session (`hiking-monitor-04b24797df2c`) timed out at 08:59:25, new TLS session on port 8883 connected at 08:59:26 and has stayed up with no disconnects since (15s keepalive, so a real problem would already show).
- **Phase E (cutover + docs):** done. Docs updated 2026-07-13 to reflect 8883/TLS as the roaming-device path: `jctsh-network.md`, `components/hiking-monitor/wifi-config.md`, `credentials.local.md`, `jctsh-security-hardening.md` (dated superseded-note on the original port-inventory finding, history kept intact). Confirmed via `p-w-firefly/heartbeat.md` that coachproxyos reaches MQTT via Tailscale (`100.70.162.24:1883`), not the DuckDNS/port-forward path, so retiring the 1883 forward has no impact there. Old 1883 → 192.168.1.117 router-forward rule removed by Joseph (manual, router admin UI — same as Phase C, browser automation can't drive this router's admin SPA).

**Resolution:** all five phases complete. **Verified live 2026-07-13** from the LAN against the public `jctsh.duckdns.org` hostname (this router does hairpin NAT, confirmed in `wifi-config.md`, so a LAN-sourced test against the public hostname reflects the real forwarding table): port 1883 now returns connection refused (forward removed), port 8883 accepts a TCP connection (TLS listener still reachable). Cross-checked against the live Mosquitto log on the Pi: `hiking-monitor-04b24797df2c` has held a stable TLS session on 8883 since 08:59:26 with no disconnects (15s keepalive). The one 09:10 SSL "unexpected eof" log entry is this verification probe itself (a raw TCP connect with no TLS handshake), not a device problem.

Execution detail/history: `C:\Users\jcthomas\.claude\plans\misty-fluttering-porcupine.md`.

**Closed 2026-07-13 — Joseph confirmed and directed the close.**

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

### CARD-0057 · [enhancement] [kanban-board] Serve the kanban board as a live-parsing Pi page — RESOLVED 2026-07-11
**Status:** Done

**Notes:** Raised 2026-07-11. The manual regenerate-after-edit discipline agreed to when closing CARD-0056 is already slipping — updates to `kanban-board.md` aren't reliably followed by a republish. That's exactly the condition CARD-0056 named as the trigger to revisit this alternative, and it's now been hit. There's a second, measured cost beyond just forgetting: a regenerate cycle means re-reading the full ~600-line file (multiple large reads once the board grows) plus manually cross-checking it against the embedded JSON, which alone runs over 20k tokens — expensive as well as easy to skip.

**Skipped Planning/Design (2026-07-11):** the card's own architecture sketch below already functioned as the plan, and the one open question (getting `kanban-board.md` onto the Pi) already had a settled answer — same situation the TOS doc calls out for CARD-0003/CARD-0034, so this went straight from Backlog to Build.

**Approach:**
- New route on the Pi's existing `log_server.py` (e.g. `/kanban`), alongside the existing `/status` endpoint — reuses the running process/port rather than standing up anything new.
- A small regex-based parser matching `kanban-board.md`'s consistent card format (`### CARD-XXXX · [type] [tag] Title`, `**Notes:**`/`**Resolution:**`/`**Blocked:**` blocks, `## ColumnName` section headers) into the same card-object structure the artifact's JSON currently holds.
- Serve either full server-rendered HTML (reusing the existing blueprint-styled CSS) or a JSON endpoint the current client-side JS/CSS fetches instead of reading a baked-in `<script type="application/json">` block — the JSON route is less rework since the front end barely changes.
- Reachable on the LAN and via Tailscale, matching how `/status` is already scoped — no internet exposure needed.

**Resolved gap, superseded (2026-07-11):** originally planned as `scp`ing `kanban-board.md` to the Pi alongside `log_server.py` on deploy, repeated on every future edit. Built and briefly live-tested that way, then reconsidered — see "Architecture changed" below for what replaced it.

**Relationship to CARD-0056:** CARD-0056 built and closed the claude.ai Artifact version, explicitly deferring this Pi-hosted alternative and naming "manual regeneration turns out to be too easy to forget" as the specific revisit trigger. That trigger has now occurred.

**Built (2026-07-11):** added `_parse_kanban_board()`, `_KANBAN_TEMPLATE`, and `/kanban` + `/kanban/data` routes to `core/logging/log_server.py`, reusing the artifact's existing blueprint-styled front end (client-side search/filter/collapse unchanged) but swapping its data source from a baked-in JSON blob to a `fetch('/kanban/data')` call, auto-refreshed every 30s. Added cross-links from the `/` and `/status` pages' nav lines, matching the existing pattern.

**Sync automated, then superseded (2026-07-11):** first automated the remaining manual step (`scp`ing `kanban-board.md` to the Pi after every edit) as a project-level `PostToolUse` hook (`Write|Edit` matcher) that fired on file edits and `scp`'d the file if it matched. Built, pipe-tested, and schema-validated correctly, but the live proof-test failed: the settings watcher doesn't hot-reload a `hooks` section added mid-session to a file that already existed at session start, so it never actually fired this session.

**Architecture changed (2026-07-11):** while debugging the hook, Joseph asked why push at all rather than having the Pi pull the file itself. Real answer: this Windows machine isn't a server (not always on/reachable), but the repo's GitHub remote is, and it's public — so `_load_kanban_cards()` now fetches `https://raw.githubusercontent.com/joscthomas/jctsh/main/kanban-board.md` directly over HTTPS on every request via `urllib.request`, instead of reading a local file. Removed `KANBAN_FILE`, the local copy on the Pi, and the now-unneeded hook entirely — no push mechanism of any kind. Freshness is now tied to `git push`, not to individual edits or Claude Code sessions; the header label changed from "Updated" (file mtime) to "Fetched" (request time) since GitHub's raw-content endpoint doesn't expose a real last-modified time and the GitHub API's per-file-commit endpoint risks its 60-req/hour unauthenticated rate limit under the page's 30s auto-refresh.

Two real parser bugs found and fixed during local testing, both edge cases exposed by CARD-0057's own text describing its own conventions: a naive `"### CARD-"` substring sanity-check falsely flagged a mismatch because the card's own body quotes the format (`` `### CARD-XXXX · ...` ``) as documentation — the real line-anchored regex was correct all along, the *test* was wrong. Separately, a naive `"**Blocked" in body` heuristic false-flagged this same card as blocked because its body quotes `` `**Blocked:**` `` as an example of a recognized label; fixed by requiring the pattern at the start of a line (`^\*\*Blocked`), which also means CARD-0003's `**Blocked:**` — buried mid-bullet inside its Phase D progress narrative, not its own paragraph — doesn't get auto-flagged either. Accepted as a known limitation: the flag is a best-effort scanning aid, not authoritative; full text is always visible in the expanded card regardless.

**Verified — local-file version (2026-07-11, superseded):** local end-to-end HTTP test (real handler, real auth, a throwaway port) confirmed all 57 cards parse correctly, 401 without credentials, 200 with them, existing `/` and `/status` routes unaffected, and a missing-file case returns 503 instead of crashing. Deployed via the documented pattern (`scp log_server.py` + `kanban-board.md` to the Pi, `ssh ... sudo systemctl restart jctsh-logging`) — service came back up clean. Live-fetched `/kanban` and `/kanban/data` over the real network afterward: byte-identical sizes to the local test, 57 cards, timestamp matching the actual deploy moment.

**Re-verified — pull-from-GitHub version (2026-07-11):** same local end-to-end HTTP test re-run against the new `_load_kanban_cards()` (fetches the public repo's raw content instead of a local file) — 56 cards parsed correctly (one short of the local 57, since CARD-0057's own latest edits weren't pushed yet at test time, exactly the new expected behavior), `/kanban` and existing `/`/`/status` routes all unaffected. Deployed the updated `log_server.py` alone (no `kanban-board.md` to push anymore) and confirmed live: `/kanban/data` over the real network returned byte-identical output to the local test. Removed the now-obsolete local `kanban-board.md` copy from the Pi's disk.

**Reflection:** the "small regex-based parser" scope held up — no need for anything heavier. The two parser bugs found were both self-referential (the card describing the parser's own conventions tripped naive substring checks), a class of edge case worth remembering for any future text-based parser tested against a corpus that documents its own format. The bigger lesson was architectural: the first instinct (push on edit, via a Claude Code hook) solved the wrong layer — it made *editing* trigger sync, when the real question was *which side is reliably reachable*. The Pi is always-on; this laptop isn't. Once reframed as "have the always-on side pull from something else that's always-on" (GitHub, already in place as the git remote), the whole push/hook/scp mechanism became unnecessary rather than needing to be fixed. Worth asking "which side should own the pull" before reaching for a push mechanism next time. Separately: `sudo` commands over SSH to the Pi still prompted for approval despite the `ssh pi@raspberrypi.local *` allowlist rule, likely a safety layer above simple pattern-matching for privileged commands against shared physical infrastructure — reasonable to leave as-is.

**Autonomous build (2026-07-11):** Joseph configured project permissions (`.claude/settings.local.json`) so this build/deploy could run without per-operation confirmation — see progress notes below.

**Closed 2026-07-11 — live on GitHub push, re-verified working, no known open items.**

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

**Raised 2026-07-29 17:24 MST** — CARD-0112 designed the `<file_stem>_staging/` mechanism and specifically the SSHFS-Win mount as the no-friction way to get files into it (drag-and-drop from Explorer), but nothing ever tracked Joseph actually setting it up. Confirmed tonight it's genuinely unused: CARD-0080's real BirdNET exports came in through Downloads and got `scp`'d in manually instead.

**Scope:**
1. Install WinFsp + SSHFS-Win and mount the M8's staging path as a Windows drive, per CARD-0112's already-decided target: `\\sshfs\jct@100.111.16.14\home\jct\hike-izer-web-app\srv`, addressed by the Tailscale IP (not `photo-server.local`) so it resolves identically at home and remote. Verify it actually works — list real files through it, drop a test file in and confirm it lands on the M8.
2. **Write a new doc**, `components/hike-izer-orchestrator/staging.md`, covering the operational steps for managing this data day to day: how to find/confirm today's hike's correct `file_stem` (matters once a second same-day hike exists, per CARD-0113), the exact expected filenames/formats per staged resource (`gaia_embed.html` for CARD-0104's iframe snippet; any `.zip`/`.json` for a CARD-0080 BirdNET export — `birdnet.py` scans for either), and the fact that staged files are left in place after consumption (not deleted), so nothing needs re-staging for a later re-render.
3. Link the new doc from `components/hike-izer-orchestrator/README.md` (or create one if it doesn't exist) so it's discoverable outside this card.

**Item 1 done, 2026-07-30 13:03 MST.** WinFsp was already present; `winget install --id SSHFS-Win.SSHFS-Win -e` installed the rest. The mount actually landed as drive `Z:` (rooted at `jct`'s whole home directory, not just the `srv` subpath — `Z:\hike-izer-web-app\srv` reaches the same place the original `\\sshfs\...\srv` UNC path was meant to) rather than the UNC path resolving directly; a bare attempt at the raw UNC path in Explorer failed once the share was already connected via the drive letter, which turned out to be a red herring, not a real problem — confirmed via `Z:`. Verified with a real round-trip: wrote a test file through `Z:\hike-izer-web-app\srv\`, confirmed it landed correctly via direct SSH `cat` on the M8, then removed it.

**Note:** "Done when" below originally said "all three staged-resource types" but only two are actually named anywhere in this card or `_read_staging()` (Gaia embed, BirdNET export) — corrected to two; no third type exists to document.

**Items 2 and 3 done, 2026-07-30 13:10 MST.** Wrote `components/hike-izer-orchestrator/staging.md` — covers finding the right hike's staging directory, the Gaia embed (manual, laptop-only, exact filename `gaia_embed.html`), the BirdNET export (automatic per CARD-0122, with the mount as fallback, any `.zip`/`.json` filename), the mount setup itself, and that staged files persist after use. Linked from a new "Staging data for step 2" section in `components/hike-izer-orchestrator/README.md`.

**Follow-on fixes, 2026-07-30 13:15 MST:**
1. **Permissions bug found live** — every `<file_stem>_staging/` directory is created by the orchestrator container running as **root**, defaulting to owner-only write (`0755`). The `Z:` mount connects as the non-root `jct` Linux user, which could read/traverse those directories but never actually write a file into one — directly defeating this card's whole "drag-and-drop from Windows" point. Confirmed live (a real "permission denied" trying to save into `2026-07-30_staging/`), fixed today's directory via `docker exec ... chmod 777`, and fixed the root cause: both creation sites (`generation.py`'s `run()`, `app.py`'s `_handle_stage_file`) now `os.chmod(..., 0o777)` explicitly after `os.makedirs()` (not via `makedirs`'s own `mode=`, which the container's umask masks down anyway), so every future staging directory is writable from the mount from the moment it's created.
2. **`gaia_embed.html` renamed to `gaia_embed.txt`** — plain text is easier to create/paste the iframe snippet into from Windows than a `.html` file; the content staged there is still the same iframe markup either way. Updated `_read_staging()`'s expected filename, `_handle_stage_file`'s `kind=gaia` write path, and `staging.md`.

**Done when:** the mount is live and verified with a real file round-trip ✓, `staging.md` exists and covers both staged-resource types this component currently supports ✓, and it's linked from somewhere discoverable outside kanban-board.md ✓.

**Not done by Claude alone:** installing WinFsp/SSHFS-Win needed an elevated, interactive Windows installer — Joseph ran that step himself; Claude verified the mount and wrote the documentation once it was in.

**Related:** CARD-0112 (designed this mechanism, Done), CARD-0104 (Gaia embed, the first staged-resource type), CARD-0080 (BirdNET export, the second staged-resource type, Done), `components/hike-izer-orchestrator/generation.py` (`_read_staging()`).

---

### CARD-0120 · [bug] [hike-izer] Automatic session query window trusts GPSLogger's self-reported start time -- undercounted today's hike by ~85% — RESOLVED 2026-07-30 06:15 MST
**Status:** Done

**Raised 2026-07-30 05:18 MST** — Joseph asked why today's hike registered only 0.2 mi. Investigation found the published page (`2026-07-30_hike-summary.html`) reported 0.2 mi over 10 minutes, but the real hike was 1.33 mi over 35 minutes (71 GPS trackpoints, one continuous session, no internal gap >10 min).

**Root cause:** `generation.py`'s `_session_query_window()` bounds its Apps Script query to `startedtimestamp` (from the webhook's `stopped` payload) ± `SESSION_QUERY_PADDING` (10 min). GPSLogger sent an unexplained second `started` broadcast for the same file (`filename="20260730"`) at 12:12:09 UTC — 36 minutes after the real 11:36:28 start, and one second before `stopped` fired — which reset the `startedtimestamp` value carried in the `stopped` payload. Generation trusted that reset value and queried only ~12:02–12:22, capturing 21 of the hike's 71 real trackpoints. Confirmed directly from the orchestrator's container logs (`docker logs hike-izer-orchestrator`), which show both raw webhook payloads.

**Two theories investigated and ruled out before landing on the real cause:**
1. **Race condition / GPS points not yet uploaded to the Sheet.** Disproven — the query window itself was narrow (~20 min), not a correctly-wide window returning stale/incomplete data. The shortfall is fully explained by which time range was queried, independent of any upload timing.
2. **Option A — persist the earliest `started` timestamp, keyed by GPSLogger's `filename` field.** Rejected: `filename` is not unique per hike (today's own evidence — the same `"20260730"` value was reused across the spurious mid-hike restart), so a second same-day hike reusing the same filename risks its session window getting merged with an unrelated earlier hike's. A refined version (single state file, first-`started`-wins, deleted on `stopped`) avoids the filename-reuse problem, but introduces its own failure mode: if `stopped` never arrives for a hike (crash, force-kill), the state file is never cleared and corrupts the *next* hike's window with the dead hike's stale start time. Spun off as CARD-0121 rather than folded into this fix.

**Decision — Option B:** stop trusting any GPSLogger self-reported timestamp for session bounds. Reuse `fetch_hike_data.py`'s existing gap-based session-splitting (`_gps_sessions`, 10-minute gap threshold, already proven via CARD-0101/CARD-0113) directly in the automatic path: query the whole local day, let session detection run as it already does, then select whichever detected session's end is closest to the webhook's own `local_datetime` (the one genuinely trustworthy signal — "a hike just ended, right now") as "this" hike. Scope every data source (env/observations/GPS) to that session's `[start, end]` using the `_rows_in_hike_sessions` helper that already exists for CARD-0113's altitude scoping, rather than trusting the query window's bounds to already be correctly scoped. This handles today's corrupted-restart case and a genuine multi-hike day with one mechanism, with no new state to persist or expire.

**Scope:**
1. Modify `generation.py`'s session-window logic per the Option B design above.
2. Verify against today's real trace (should recover 71 points / 1.33 mi / ~35 min) and against 2026-07-29's real two-hike day (both hikes must stay correctly separated, not merged).
3. Regenerate `2026-07-30_hike-summary.html` with the corrected data once the fix is verified.

**Fixed 2026-07-30** in `components/hike-izer-orchestrator/generation.py`: added `_detect_session_window()`, which probes the whole local day (reusing `fetch_hike_data.py`'s existing gap-based `_gps_sessions` detection unchanged), picks whichever detected `is_hike` session's own end is within `SESSION_MATCH_TOLERANCE` (15 min) of the webhook's `local_datetime`, and uses *that* session's real start/end ± `SESSION_QUERY_PADDING` as the query window — instead of trusting `startedtimestamp` from the `stopped` payload. The old payload-trusting logic survives as `_session_query_window_from_payload()`, now only a defensive fallback for the case where no matching session is found at all.

**Verified locally before deploy**, using the real Apps Script data (not synthetic):
- Today's corrupted-restart trace: detected window `11:26:28Z`–`12:22:02Z` (real session `11:36:28`–`12:12:02` ± padding) — recovers the full hike, ignoring the bogus 12:12:09 `started` reset.
- 2026-07-29's real two-hike day: hike 1 → `10:57:57Z`–`11:47:39Z` (real `11:07:57`–`11:37:39` ± padding); hike 2 → `16:21:21Z`–`18:50:41Z` (real `16:31:21`–`18:40:41` ± padding, correctly excluding the trailing truncated drive segment). Each correctly isolated to its own session, no merging either direction.

**Deployed and confirmed live 2026-07-30 06:15 MST:** rebuilt and recreated the `orchestrator` container on the M8 with the fixed `generation.py` (healthy post-rebuild). Backed up the pre-fix `2026-07-30_hike-summary.html`/`.meta.json`/`hike_data.json` to `_backup_2026-07-30_pre-CARD-0120-fix/` on the M8 (not deleted), then re-fired the real `stopped` webhook payload against the live container to regenerate in place. Confirmed on the regenerated live page: **Distance 1.3 mi, Time 7:36 AM – 8:12 AM (36m)** — matches the real GPS trace, not the old 0.2 mi / 10 min. Bonus: the Immich photo search window widened along with the fix, from 1 matched photo to 7.

**Related:** CARD-0101/CARD-0113 (the session-splitting logic this reuses), CARD-0086 (automatic triggering, the pipeline this modifies), CARD-0121 (the separate "`stopped` never arrives at all" gap spun off from this investigation), `components/hike-izer-orchestrator/generation.py`, `components/hike-izer/fetch_hike_data.py`.

---

### CARD-0121 · [bug] [hike-izer] Automatic generation never runs if GPSLogger's "stopped" broadcast never fires
**Status:** Backlog

**Raised 2026-07-30 05:18 MST**, spun off from CARD-0120's investigation. `app.py`'s webhook handler only ever calls `generation.run_and_log()` in response to a `gpsloggerevent=stopped` POST — nothing else triggers automatic report generation. If GPSLogger crashes, gets force-killed by Android, or its Tasker exit condition never fires, no webhook arrives and no page is ever generated for that hike — silently, with no error or alert surfaced anywhere.

**Not solved by CARD-0120.** That card only changes how session bounds are computed once a `stopped` event is actually received; it does nothing for the case where one never arrives at all. Both the old (Option A) and new (Option B) designs for CARD-0120 are equally exposed to this — it's a gap in the trigger itself, not in session-bounds calculation.

**Scope not yet defined** — needs interview/design before moving to Planning. Rough shape: some periodic or backstop check that notices "real GPS trace data exists in the Sheet consistent with a hike, but no corresponding page was ever generated for it," and either generates it late or at minimum surfaces a visible alert (dashboard log line) rather than the gap staying invisible.

**Related:** CARD-0086 (automatic triggering, the system this gap is in), CARD-0120 (the investigation that surfaced this), `components/hike-izer-orchestrator/app.py`.

---

### CARD-0122 · [enhancement] [hike-izer] Automated staging: BirdNET Live phone Share → webhook → M8 staging directory — RESOLVED 2026-07-30 12:45 MST
**Status:** Done

**Raised 2026-07-30 06:40 MST** — Joseph asked how to get two files captured at the end of today's hike (Gaia GPS's iframe embed snippet, a BirdNET Live session export) into the correct `<file_stem>_staging/` directory (CARD-0112's mechanism) without a manual step. Considered and rejected email-to-self and Google Drive upload as the transport: both are zero-code but not actually automated (something still has to notice the file arrived and move it, taking on a new external-API credential surface — Gmail/Drive auth — to do it), and both add a third-party store-and-forward hop this project doesn't otherwise have. Decision: reuse the pattern already proven for GPSLogger (CARD-0086) — Tasker intercepts an Android Share and POSTs directly to a new orchestrator endpoint, over the same authenticated webhook channel everything else here already uses.

**Scope narrowed during Build, 2026-07-30 09:05 MST — Gaia dropped from this card.** Live testing found the "Share" action Gaia's *website* offers on a phone (even in desktop-site mode) only produces a plain map URL (`%astext` resolved to `https://gaiagps.com/map/?lo..`), not the `<iframe>` embed snippet `gaia_embed.html` actually needs. Joseph confirmed the real **Embed** feature — the one that generates that iframe code — only exists on the *laptop* browser's UI; it's simply not reachable from the phone at all, desktop-site spoofing or not. No phone-side automation (AutoShare, Tasker, clipboard-watching) can intercept something the phone never has access to in the first place. Since the embed code only ever exists on the laptop, and CARD-0119 already built exactly the tool for getting a file from Windows into `<file_stem>_staging/` (the SSHFS-Win mount), Gaia's embed snippet goes through that existing, no-new-code path instead — copy it on the laptop, drop it in as `gaia_embed.html` through the mount, done. This card's remaining scope is BirdNET's export only, the half that's genuinely phone-based.

**Design, as built/being built:**

1. **Orchestrator endpoint** (built and deployed 2026-07-30) — `POST /webhook/stage-file?key=<secret>&kind=gaia|birdnet[&ext=zip|json]` in `app.py`. Kept `kind=gaia` support in the deployed code even though the Gaia path above now bypasses it entirely — it's a few already-tested lines, not worth ripping out for a mechanism that might still find a use later. `kind=birdnet` writes the POST body to `<file_stem>_staging/birdnet_<timestamp>.<ext>`; `birdnet.parse_detections()` already globs `*.zip`/`*.json` regardless of filename, so no read-side change needed. Responds synchronously (just a file write, no background thread). Every receipt/failure gets a durable MQTT dashboard log line.
2. **Resolving *which* hike's staging directory** — `generation.latest_file_stem()`, whichever `*_hike-summary.html` has the most recent mtime. Deliberately not "today's date": a hike's real local date (from GPSLogger's `local_datetime`) can differ from the M8's fixed server TZ (`America/Phoenix`) whenever Joseph is traveling (this week's case — Michigan/Eastern). mtime sidesteps that date-boundary ambiguity and matches the real usage pattern (files get shared within minutes of the hike ending).
3. **Phone side, AutoShare (in progress)** — confirmed live 2026-07-30: enabling the plain "AutoShare" Share Target (not Command, not Intercept) adds one generic entry to Android's Share sheet. A Tasker profile with Event → Plugin → AutoShare (not the Action-side "Plugin → AutoShare," which is for Tasker *sending* a share out, confirmed via its "Share Options"/"App"/"Find Compatible apps" fields — the wrong direction) catches it, with "Receive Share Options" left blank (no filtering — match any share). Confirmed real variables: `%astext` (shared text), `%asfile()` (shared files, array — index with `%asfile(1)`), `%assubject`, `%ascommand`. Tested live from BirdNET Live: `%asfile(1)` resolved to a real `content://com.joaomgcd.autoshare...` URI (AutoShare's own FileProvider wrapping the file) — confirms BirdNET's export arrives as a file reference, not text. Confirmed separately (real files seen in Downloads, 2026-07-29): BirdNET's actual export extension is `.zip` (`BirdNET_Live_<date>_<time>_#N.zip`), settling one of the open questions below.

**Resolved — both open questions answered by real testing, not left open:**
- **Tasker's HTTP Request action cannot POST a `content://` URI directly** as its "File To Send" body — confirmed live via a real `FileNotFoundException` from Tasker's own run log. Fix: an intermediate File-category copy action resolves `%asfile(1)` to a real local path first; the HTTP Request's "File To Send" points at that resolved path instead of the raw content URI.
- **`WEBHOOK_SECRET` reused**, not a second secret minted — no issue in practice.

Also hit and fixed along the way (real bugs, not just config): the Tasker task's `If %asfile Set` guard was checking the wrong variable (`%asfile`, a bare scalar that's never set) instead of `%asfile()` (the actual array AutoShare populates) — caused every attempt to silently skip the HTTP Request entirely (`IfFail` in Tasker's run log) until corrected to check `%asfile()`. Separately, `app.py`'s `_handle_stage_file` had two rejection paths (invalid/missing `kind`, empty body) that responded with an HTTP error but never logged anything server-side — meaning an early failed attempt left zero trace anywhere, which is exactly what made diagnosing "nothing arrived" ambiguous for a while. Fixed by adding `log()`/`_log_mqtt_async("Alert", ...)` to both paths, matching every other rejection case's convention.

**Done when:** BirdNET Live's Share sheet lands its export in the correct hike's `_staging/` directory on the M8 with no manual step (no email, no Drive, no SCP), verified with a real share from a real hike. (Gaia's embed snippet is out of scope here — see the SSHFS-Win path above, unchanged from CARD-0119.) **Met 2026-07-30 12:39 MST.**

**Server side built and deployed 2026-07-30:** `POST /webhook/stage-file` added to `app.py`; `generation.py` gained `latest_file_stem()`. Rebuilt and recreated the `orchestrator` container on the M8 twice (once for the endpoint itself, once for the rejection-logging fix); confirmed healthy both times.

**Verified live with a real share from a real hike, 2026-07-30 12:39 MST:** BirdNET Live's actual export from today's hike (`BirdNET_Live_2026-07-30_07-36-35_#4.zip`) shared via AutoShare → Tasker → the deployed endpoint, landed at `2026-07-30_staging/birdnet_20260730T193925Z.zip` (18,614 bytes). Confirmed on the M8 via `docker exec`: the zip opens cleanly (`zipfile.testzip()` reports no corrupt members) and `birdnet.py`'s own `parse_detections()` correctly extracts 8 real species detections with plausible timestamps/confidences matching this morning's actual hike window — the genuine production code path, not just a zip-integrity check.

**Not done by Claude alone, done by Joseph:** the AutoShare install, both Share Target/Tasker profile setup, and all live-device troubleshooting (variable inspection, the `If`-condition bug, the file-copy fix) — same division of labor as CARD-0086's original GPSLogger Tasker setup.

**Related:** CARD-0112 (designed the `_staging/` mechanism this feeds), CARD-0119 (the SSHFS-Win mount — now the sole mechanism for staging the Gaia embed; this card no longer replaces it, just narrows to the half it doesn't cover), CARD-0104 (Gaia embed), CARD-0080 (BirdNET export), CARD-0086 (the original Tasker-webhook pattern this reuses), `components/hike-izer-orchestrator/app.py`, `components/hike-izer-orchestrator/generation.py` (`_read_staging()`, `_next_file_stem()`, `latest_file_stem()`), `components/hike-izer-orchestrator/birdnet.py` (`parse_detections()`).

---

### CARD-0123 · [enhancement] [hike-izer] Make narrative generation opt-in; move place-context/sun-position data into tables instead of prose — RESOLVED 2026-07-30 14:50 MST
**Status:** Done

**Raised 2026-07-30 14:20 MST** — Joseph asked for a cost breakdown of recent generations, which surfaced that `narrative.py`'s Claude call and `place_context.py`'s two research layers (`gather_enrichment()`, `gather_regional()`) are the only real cost beyond photo captioning — today's step 2 for the morning hike was $0.5838 across 9 calls (7 photo captions + 1 place-context research call w/ 4 web searches + 1 narrative call). Decision: make photo captioning the only *default* cost, with narrative fully preserved in code and available as an explicit opt-in per hike, not deleted.

**Scope:**
1. **`place_context.gather_place_context()`** gains an `include_research` parameter (default `False`). When false, skips `gather_enrichment()`/`gather_regional()` entirely (no calls, no cost) but still runs the deterministic, free layers — Nominatim reverse-geocode (address) and Overpass named-features lookup — since those now feed their own page sections regardless of the narrative flag (see below).
2. **`generation.run_step2()`** gains a `with_narrative` parameter (default `False`). When false, skips `narrative.generate_narrative()` entirely and passes `[]` for narrative paragraphs to `templating.render_html()` — reusing the *existing* omit-when-empty convention step 1's data-only pages already exercise, not new rendering logic.
3. **CLI**: `generation.py`'s `--step2 FILE_STEM` gains a sibling `--narrative` flag (opt-in, off by default) threaded through to both of the above. Turning narrative back on for a specific hike later is `--step2 <stem> --narrative`, no redeploy, no config file, nothing to restore — every existing function (`narrative.py`, `gather_enrichment`, `gather_regional`) stays exactly as it is, just not called by default.
4. **New deterministic page sections** (`templating.py`), replacing what previously only ever appeared woven into narrative prose:
   - **Location** — one line, from Nominatim's address.
   - **Nearby Named Features** table — Name / Type / Operator, from Overpass; omitted if none found.
   - **Observations** table — Time / Category / Text, straight from Hiking Observations (if not already rendered somewhere).
   - **Rejected-session note** — a GPS session detected but not classified as a hike shows its already-computed `rejection_reasons`, never surfaced on the page before now.
5. **Sun Position table extended** with the additional derivable-for-free fields discussed: peak-elevation time, a golden-hour flag, precise azimuth range, % of the hike in daylight — all already computable from `sun_position_samples`, no new data collection.
6. Cost logging needs no code change — `run_step2_and_log()`'s existing `(API cost: ...)` line already reports whatever `CostTracker.record()` calls actually happened; with narrative off, that's naturally just the photo-caption total.

**Done when:** a real step-2 run with no `--narrative` flag costs only what photo captioning costs (verified against a real hike), the new Location/Named Features/Observations sections render correctly from real data, the Sun Position table shows the extended fields, and `--step2 <stem> --narrative` still produces the full old-style enriched page with narrative prose, proving nothing was lost.

**Built and verified live, 2026-07-30 14:50 MST**, against the real second hike from today (`2026-07-30-2`):
- Found during Build: "Observations" was already its own table (`observations_table_rows`/`obs_section`, pre-existing, always rendered regardless of narrative) — nothing new needed there; scope item 4's Observations bullet turned out to already be done.
- `place_context.gather_place_context()` restructured to return `{address, named_features, research_facts}` (structured, not pre-flattened) instead of a flat fact-string list; `flatten_for_narrative()` added to reconstruct the old flat shape only when `narrative.py` actually needs it. Verified locally against real fetched hike data before deploying: `include_research=False` produces real `address`/`named_features` with zero Claude calls, and `flatten_for_narrative()` reproduces the exact old fact-string format.
- **Narrative off (default):** `$0.0664, 3 API calls` for a 3-photo hike — matches the $0.0663 photo-caption-only baseline from before this change, confirming zero added cost. Page correctly has no "The Hike" section, a real Location section (address + named features table, from Overpass despite it hitting rate limits mid-run — per-point retry meant later query points still succeeded), and the extended Sun Position table (elevation/azimuth range, % daylight, peak-elevation time, golden-hour flag — all real, all free).
- **`--narrative` (opt-in):** same hike, re-run with the flag — `$0.4854, 5 API calls, 4 web searches` (3 photo + 1 place-context research + 1 narrative, same structural pattern as a normal enriched run, just scaled to fewer photos). Confirmed a full, real narrative paragraph set rendered under "The Hike," proving the opt-in restore path genuinely works, not just compiles.
- Live page for `2026-07-30-2` currently reflects the `--narrative` test run (the richer version) since that ran last — Joseph's call whether to leave it or regenerate without `--narrative` to match the new default.

**Related:** CARD-0108 (place-context gathering, the module this extends), CARD-0086 (stage 2 / narrative generation, CARD-0112's split), CARD-0109 (the non-redundancy rule between tables and narrative this build has to keep respecting for whichever path is active), CARD-0110 (the sun-position/stats card this folds the elevation-range extension into), `components/hike-izer-orchestrator/narrative.py`, `components/hike-izer-orchestrator/place_context.py`, `components/hike-izer-orchestrator/generation.py`, `components/hike-izer-orchestrator/templating.py`, `components/hike-izer-orchestrator/cost_tracking.py`.
