# JCTsh Backlog

Lightweight kanban. Each card has a **type** (idea | enhancement | bug) and a unique ID.

**Columns:** Backlog → Planning → Build → Done, plus **Defer** (off to the side — reachable from any stage)
- **Backlog** — captured, not yet being worked on
- **Planning** — being scoped/interviewed, and (if non-trivial) an implementation plan written — no separate Design checkpoint; the plan itself is the design artifact
- **Build** — going through the plan/implementation, including testing
- **Done** — complete
- **Defer** — a deliberate decision not to pursue for now (not abandoned, not forgotten — just consciously parked); can move here from any other column

<!-- next-card-id: CARD-0194 -->

---

### CARD-0193 · [idea] [infrastructure] Kanban board scaling strategy — RESOLVED 2026-08-22 20:17 MST
**Status:** Done

**Closed 2026-08-22 20:17 MST.** Every design point built, deployed, and live-tested: the `log_server.py` caching fix (7x faster repeat polls); `archive_cards.py` (size-primary trigger, `--force`, `--apply`, provenance annotations); a real archiving run (27 cards, `kanban-board.md` 1.18MB → 731KB, all six retagging fixes applied); the on-demand archived-detail lookup in `/kanban`; and a green/yellow/red size indicator on the board header tied to the two real thresholds (256KB Read-tool cap, 1MB GitHub API cap) that this whole card was about in the first place. All previously-open decisions confirmed: 90-day secondary age backup, un-archiving moves a card back to the live file, the dated archive stays one file (`tos/kanban-archive.md`), and the tool stays manual with a periodic Session Start reminder rather than a timer. **Reflection (per `JCTsh-Operating-System.md`'s Build → Done requirement):** the durable knowledge from this card lives in three places that will actually be read again — `tos/README.md` (the system overview), `CLAUDE.md`'s Session Start (the "don't forget" mechanism), and `archive_cards.py`'s own docstring (every design decision and why, next to the code it governs) — not just in this card's own history.

**Moved to Build 2026-08-22 19:28 MST (Joseph).** Design is settled enough to start implementation; the remaining "Still open" items below (secondary age threshold, un-archive rule, single-vs-per-year archive file) aren't full blockers — resolve them as part of doing the work, not before starting it.

**Step 1 (point 4, the caching fix) done and live-tested, 2026-08-22 19:32 MST.** Added a 20s TTL cache to `log_server.py`'s `_load_kanban_cards()` (module-level dict, thread-lock guarded for `ThreadingHTTPServer`) — it was re-fetching and re-parsing the entire raw file unconditionally on every call, including the `/kanban` page's own client JS polling `/kanban/data` every 30s for as long as a tab stays open, a cost that was previously undocumented until this investigation found it. Deployed to the Pi, restarted `jctsh-logging`. Live-tested directly against the real endpoint: cold fetch 0.53s, immediate repeat 0.07s (~7x faster, byte-identical content) confirming the cache hit; a third request after waiting 22s (past the 20s TTL) took 0.665s again and returned a genuinely different byte count, confirming the cache correctly expires and re-fetches real fresh content rather than ever serving indefinitely stale data. Archiving mechanism itself (points 1-3, 6-7) not yet started.

**Raised 2026-08-22 18:24 MST (Joseph), during a strategy discussion following CARD-0190.** `kanban-board.md` just crossed GitHub's 1MB Contents API limit (CARD-0190) and is still growing unboundedly — that fix patches the automated PR pipeline's read path, but doesn't address the underlying growth, or two other size-sensitive consumers this discussion surfaced: Claude's own Read tool (256KB cap, already forcing grep-only access on this file this session) and `core/logging/log_server.py`'s `/kanban` viewer, which has **no caching at all** — every single page load re-downloads and re-parses the entire raw file from GitHub, with a 10s timeout. Since Joseph's own habit is always viewing the rendered board (never the raw file), that third one is the cost he'd actually feel most directly as the file keeps growing.

**Design decided via interview 2026-08-22:**
1. **Archive trigger: size-primary, revised 2026-08-22 — the original age-based design was wrong about what actually drives the file's size.** Real per-card size data pulled from the live file: card size is a strongly skewed long-tail distribution, median ~4KB, but the top 15 cards alone (8% of all 193) account for 28% of the file's total 1.15MB. Threshold sensitivity checked directly: >15KB catches 16 cards / 29% of the file; **>10KB catches 28 cards (14.5%) / 42% of the file — the chosen threshold.** A card becomes archive-eligible once it's **Done or Defer AND exceeds 10KB** — this targets where the size actually lives (a handful of very verbose resolved cards: CARD-0096 at 40KB, CARD-0147 at 29KB, CARD-0028 at 28KB, etc.), not an arbitrary age window that — per the age-profile data below — wouldn't touch a single one of these for weeks regardless, even though they're already resolved and already the dominant cost today. **Age kept as a secondary, slower backup rule** (e.g. Done/Defer AND older than 180 days, independent of size) to eventually sweep up the long tail of small-but-accumulating cards over a longer horizon — but size, not age, is the primary lever, since that's what's actually causing today's pain. Automatic and periodic either way — no manual per-card judgment needed for the mechanical trigger itself (component-doc-vs-archive-file *destination* still needs the tag-matching logic in point 2).
2. **Archive destination: `components/<name>/CLAUDE.md` when one fits, dated archive file otherwise — corrected 2026-08-22, was wrongly stated as README.md earlier.** Extends CARD-0187's existing precedent exactly (that card's full history was migrated "verbatim" into `components/outdoor-presence-detection/CLAUDE.md`, **not** its README). This isn't just convention-matching — `JCTsh-Build-Standards.md` §7.1a already draws this line on purpose: README stays the short, scannable "what this does, how to run it" doc; CLAUDE.md is explicitly the "full YAML/history" home. Dumping a multi-thousand-word archived card into a README would recreate the exact bloat problem this card exists to fix, one directory down. **Second, independent reason CLAUDE.md is the right target, not just the correct one:** component `CLAUDE.md` files are read *on demand* ("see `components/<name>/CLAUDE.md` for component-specific context," only when someone's actually working on that component) — not unconditionally every session the way `kanban-board.md`'s Build column is. Letting a component's `CLAUDE.md` grow **partitions** growth by component instead of recreating one more monolithic ever-growing file — the same principle that justified splitting `tos/` out of `core/maintenance/`'s grab-bag in CARD-0191, one level down. Mechanics: cut the card's full `### CARD-NNNN ... ---` block out of `kanban-board.md`, append it verbatim under a `## Card History` section in the component's `CLAUDE.md` (creating the file if the component doesn't have one yet, per §7.1a). Cards with no matching `components/<name>/` directory (mostly `[infrastructure]`/`[core]`-tagged process cards, a minority of the total) fall to a dated archive file (e.g. `tos/kanban-archive-2026.md`) instead — its growth should be naturally slower than `kanban-board.md`'s own historical rate, since most cards *do* carry a real component tag.
3. **Archive trace: a short pointer stub stays in `kanban-board.md`.** Not deleted outright — e.g. `### CARD-0155 · ... — Done, archived to components/photo-quality-review/CLAUDE.md`. Keeps the live file a complete, scannable index of every card that ever existed, consistent with this repo's existing "never let resolved work silently vanish with no trace" convention (already applied elsewhere, e.g. `photo-quality-review`'s `resolvedCounts`). **Reference scheme, clarified 2026-08-22:** the stub's archived-to path is a plain-text pointer, not a real hyperlink — matching how every other cross-reference in this file already works ("see `kanban-board.md` CARD-0028," never a markdown `[link](...)`). Confirmed live: zero `[CARD-...](...)`-style links exist anywhere in the file today, and `log_server.py`'s `/kanban` viewer has no link-generation logic either — so archiving doesn't introduce a new "chasing a reference" cost, it's the exact same manual lookup the board already requires today, just against a smaller, better-scoped document instead of the same 1.1MB file. A follow-on idea (not part of this card): teaching the `/kanban` viewer to turn every `CARD-NNNN` mention into a real link via a small ID→current-location index would fix reference-chasing board-wide, independent of whether archiving ships.
4. **Quick, independent win identified alongside this:** add caching to `log_server.py`'s `_load_kanban_cards()` (short TTL, or a conditional GET against GitHub's ETag) regardless of the archival timeline — fixes the "re-fetch and re-parse megabytes on every page view" cost on its own, worth doing even before archival ships.
5. **`/kanban`'s baseline needs zero code changes for archiving — confirmed by design, 2026-08-22.** It only ever fetches/parses `tos/kanban-board.md`; after archiving, all that's left there for an archived card is its stub, so that's exactly what renders by default — no special-casing, no automatically fetching the target file to inline its content on every page load. This is deliberate, not an oversight: `JCTsh-Operating-System.md`'s own Core Principle defines the board as "the durable, **scannable** record... not DEVLOG entries or component docs alone, which capture detail but aren't structured for at-a-glance status." For a long-Done card, "Done, archived to `components/X/CLAUDE.md`" *is* the correct at-a-glance status. **Automatically** inlining every archived card's target doc on every view was considered and rejected — it would multiply this card's whole size/fragility concern across every component doc on every page load, instead of reducing it in one file.
6. **On-demand archived-detail lookup, decided as a real (but not urgent) design, 2026-08-22 — different from #5's rejected idea because it's lazy and single-target, not automatic and page-wide.** The stub already carries the exact `archived to <path>` pointer. Add a small expand affordance on stubbed cards that, on click only, hits a new lightweight `log_server.py` endpoint: fetch *that one file* fresh from GitHub (same pattern as the existing `KANBAN_RAW_URL` fetch, just parameterized by path), then either render it whole (if it's a dedicated per-card file, see #7) or extract just the matching `### CARD-NNNN ...` section by heading boundary (if it's living inside a shared `CLAUDE.md`) — reusing the same heading-boundary parsing `_parse_kanban_board` already does for the main file, not new parsing logic. One small fetch, triggered once, only when actually asked for — doesn't touch the main page-load cost this card exists to fix. Worth building, but no more urgent than the rest of the archival mechanism itself, given the age-profile finding above (nothing to archive yet).
7. **Archive destination granularity, decided 2026-08-22 (raised by Joseph): default to the shared `CLAUDE.md` model above, with per-card files as the escape valve for a specific component if/when its `CLAUDE.md` itself gets big enough to hurt — not the default from day one.** Considered giving every archived card its own file now (e.g. `components/<name>/cards/CARD-0155.md`, with `CLAUDE.md` just indexing them). Real pros: `CLAUDE.md` stays small forever regardless of accumulated archive volume; cheaper/more precise reads (open exactly one card, not search a shared doc); no shared-file merge-conflict risk when two cards archive around the same time; cleaner un-archiving (delete one file vs. surgically extract a section). Real cons, decisive for now: loses the narrative cohesion CARD-0187's own `CLAUDE.md` deliberately relies on (several related cards folded into one continuous story, e.g. the Ring integration's evolution across CARD-0145/0146/0184/0185/0187 — splitting each into an isolated file loses the "read straight through and watch the design change" quality); it's a genuinely new, unprecedented convention (no `components/<name>/cards/` pattern exists anywhere in this repo today) versus extending the already-proven README/CLAUDE.md split; and it adds a third moving part to the archiving mechanics (create the file, update `CLAUDE.md`'s index, *and* leave the `kanban-board.md` stub) versus two. **Decision:** don't solve a size problem that doesn't exist yet on any specific component — same discipline as the age-threshold finding above. Revisit per-component if and when one specific `CLAUDE.md` actually grows large enough to warrant it.

**Real age-profile data pulled 2026-08-22 — the finding that triggered reconsidering the trigger entirely.** `kanban-board.md` was created 2026-06-13; the whole project is ~70 days old. Of 162 Done/Defer cards (of 193 total), age-by-latest-mentioned-date breaks down as: <30 days: 108 (69%), 30-45 days: 36 (23%), 45-60 days: 8 (5%), 60-70 days: 5 (3%) — **zero cards older than 70 days, because nothing can be.** Any age threshold in the range originally considered (90+ days) would archive nothing for weeks. Cross-checking against the size data above confirms this isn't a coincidence: the file's actual size problem is **verbosity per card**, not accumulated age — CARD-0012, CARD-0187, and CARD-0028 are each thousands of words, all resolved recently (well under 45 days), and every one of them is already in the top-15-by-size list. This is why the trigger was revised to size-primary (point 1) rather than just picking a smaller age number. The `log_server.py` caching fix (point 4) remains the only lever that helps immediately, before any archiving runs at all.

**All remaining decisions confirmed 2026-08-22 20:20 MST (Joseph):**
- ~~The secondary age backup threshold~~ — **90 days**, not 180. `archive_cards.py`'s `AGE_BACKUP_DAYS` updated to match.
- ~~Whether this waits for CARD-0191's directory consolidation~~ — resolved: CARD-0191 is Done, `tos/` exists, the dated archive file targets `tos/kanban-archive.md` directly.
- ~~A rule for un-archiving~~ — **move back to the live file.** If an already-archived card needs a real update later (this session's own CARD-0146 correction, months after its original close, is exactly this shape), it moves back into `kanban-board.md` rather than being edited in place in the archive/component doc — keeps the invariant that the live file only holds active-or-recently-touched cards. Not automated (same as archiving itself) — a manual/Claude-driven move when it comes up.
- ~~Whether one growing dated archive file reproduces the same size problem~~ — **one file, not split by year.** `archive_cards.py` and the already-created archive file both renamed from `tos/kanban-archive-2026.md` to `tos/kanban-archive.md` to match. Revisit splitting only if this file itself ever grows large enough to matter — same "don't solve it before it's a real problem" discipline as everything else on this card.
- **Tool stays manual, not wired to a timer.** To make sure it doesn't get forgotten, added a periodic (not every-session) check to `CLAUDE.md`'s Session Start: if it's been a few weeks or the file feels large again, dry-run `archive_cards.py` and offer to apply.

**"Should this just be a real database instead?" — considered and ruled out, 2026-08-22, Claude's analysis.** Raised as a genuine question, not rhetorical, given how many of these problems (size limits, ad-hoc concurrency handling) a database would erase outright. Weighed both ways:

*What a database would fix:* all three size-based failure modes permanently (no 1MB API cap, no 256KB Read-tool cap, no re-fetch-and-reparse-everything-per-view); real structured queries instead of grep; and it would eliminate the concurrency machinery CARD-0128 had to hand-build (deferred numbering, empty commits, blob-sha tree lookups, manual merge-conflict recovery via the Git Data API) — a database's transactions give that for free.

*What it would cost — the three biggest strengths already identified this session:* (1) **git-native sync** — code and project-state currently share one commit history; a database is either a separate service outside git (state/code can drift again) or a SQLite file checked into git (unreadable diffs, unmergeable binary conflicts on concurrent writes — worse than today's text conflicts, not better). (2) **AI-cold-readability** — reading a markdown file with full narrative reasoning in one pass is free today; a database needs a query layer built and maintained just to preserve that. (3) **The PR-based review gate** — "open a PR, get reviewed, then merge" reuses GitHub's existing trust infrastructure as the approval workflow; a database write is just a write, and staging/approval would have to be reinvented as custom app logic.

*The size math doesn't support it either.* 1.14MB / ~190 cards is trivially small for any database — the problem was never "this data needs a database," it's "the tooling around a plain file assumed it would stay small forever." Every concrete failure so far is narrow and already fixed or already planned here (CARD-0190's API fix, this card's caching + archival plan). A database also assumes multi-writer contention this solo-operator-plus-AI setup rarely produces — the one real concurrency bug seen (CARD-0128's numbering race) came from two *automated scripts*, not human contention, and was already solved cheaply without one.

**Decision: not now, likely not ever at this scale.** Middle-ground option kept in reserve if search/filtering ever genuinely hurts: a SQLite index built *from* the parsed markdown (`log_server.py` already parses every card into a dict; caching that into a queryable local index gives fast filtering without making SQLite the source of truth) — not needed today, worth remembering if the calculus changes.

**Related:** CARD-0190 (the size limit that surfaced this), CARD-0191 (TOS directory consolidation — affects where an archive file would live), CARD-0187 (existing precedent for migrating a card's history into a component doc), `JCTsh-Operating-System.md` (found during CARD-0191's own research — the process side of the TOS this all belongs under).

---

### CARD-0192 · [idea] [infrastructure] Watchdog self-test for the kanban-PR intake pipeline
**Status:** Backlog

**Raised 2026-08-22 18:24 MST (Joseph), during a strategy discussion following CARD-0190.** CARD-0190's root bug (the Tasker "Log Idea" widget silently failing while hiking) was only discovered because Joseph happened to check the PR list afterward — nothing surfaced the failure on its own. Addresses the top-priority weakness identified in that discussion: the auto-PR intake pipeline (`open_finding_pr()`/CARD-0128/CARD-0173) runs unattended (a webhook always listening, `email-idea-check.py` polling on a timer) but has no monitoring of its own, unlike this project's other unattended services.

**Proposed approach, not yet interviewed/scoped:** mirror the existing Node-RED watchdog pattern (`core/node-red/watchdog.flow.json` — alerts via HA companion-app push notification if a component goes silent for 10 minutes) rather than inventing a new alerting mechanism. A periodic synthetic self-test — e.g. a scheduled job that calls `open_finding_pr()` with a recognizable test fingerprint, confirms a PR actually opened, then either auto-closes it or leaves it for `resolve_and_merge()`'s own idempotent handling — with a failure routed into the same MQTT log / HA-notification path every other component's health check already uses, so a broken pipeline pages Joseph instead of waiting to be noticed by chance.

**Open questions for interview before Build:** test cadence (hourly? daily?); where the self-test job runs (a new systemd timer alongside `email-idea-check.py` on the M8, or folded into an existing maintenance-check script); whether a failed self-test should also be evidence that a *real* idea/finding might have been silently dropped during the same window (CARD-0190's actual incident) and whether that's worth surfacing distinctly; whether the test PR needs cleanup automation or can just accumulate and get closed manually/occasionally.

**Related:** CARD-0190 (the incident this directly addresses), CARD-0128 (`open_finding_pr()`, what's being tested), CARD-0173 (Tasker "Log Idea" widget, the path that failed silently), `core/node-red/watchdog.flow.json` (the existing pattern this mirrors).

---

### CARD-0191 · [idea] [infrastructure] Consolidate TOS (Team Operating System) tooling into its own directory — RESOLVED 2026-08-22 18:54 MST
**Status:** Done

**Confirmed 2026-08-22 18:40 MST (Joseph):** move `kanban-board.md` into `tos/` along with everything else — the recommendation below proceeds as written, not the "leave it at root" alternative.

**Raised 2026-08-22 18:02 MST (Joseph), while discussing CARD-0190's fix.** Joseph named the collection of kanban-board.md + its surrounding tooling/process the "Team Operating System" (TOS) and wants it consolidated into a dedicated directory rather than scattered across the repo by infrastructure convenience.

**Current state, inventoried 2026-08-22 — TOS code exists but has no dedicated home:**

| Piece | Currently lives in | Why it's there |
|---|---|---|
| `kanban-board.md` (the data) | repo root | Historical — predates everything else |
| Process rules (interview-first, commit=done-done, card/commit/push workflow) | `CLAUDE.md` (repo root, project-level) + `~/.claude/CLAUDE.md` (machine-level, outside this repo entirely) | Repo-root convention for Claude session-start reading |
| `open_kanban_pr.py` (`open_finding_pr`/`resolve_and_merge`) | `core/maintenance/` | Mixed with ~20 unrelated infra scripts (container updates, heartbeats, reboots, backups) |
| `land_pr_card.py` (interactive card-landing script) | `core/maintenance/` | Same reason |
| `email-idea-check.py` + `.service`/`.timer` | `core/maintenance/` | Same reason |
| `/webhook/idea` route (Tasker voice-idea entry point) | Embedded in `components/hike-izer-orchestrator/app.py` | That container already has a public HTTPS endpoint (Caddy + Tailscale Funnel) — hosted there for the free endpoint, not because it's a hiking feature |
| `/kanban` viewer route + `_parse_kanban_board`/`_load_kanban_cards` | Embedded in `core/logging/log_server.py` | That's the one web server already running on the Pi |

**Claude's recommendation, given for Joseph to confirm/adjust:**

1. **New top-level directory `tos/`** (peer to `components/` and `core/`, not nested under `core/`) — it's not home-automation infrastructure and it's not a device/app component, it's the project's own self-management tooling, conceptually a third category.
2. **Move into it:** `kanban-board.md`, `open_kanban_pr.py`, `land_pr_card.py`, `email-idea-check.py` + its `.service`/`.timer` (all via `git mv`, preserving history).
3. **Leave in place, update their deploy-copy source path:** the `/webhook/idea` route stays in `hike-izer-orchestrator/app.py` (still needs that container's public endpoint) and the `/kanban` viewer stays in `log_server.py` (still needs that running web server) — but both already treat `open_kanban_pr.py`/`kanban-board.md` as "deployed copies from elsewhere," matching this repo's existing convention (e.g. `fetch_hike_data.py` deployed from `components/hike-izer/`) — just repoint the source path to `tos/`.
4. **Leave `CLAUDE.md` at repo root** — Claude Code specifically looks for it there; moving it breaks auto-loading. Update its internal references (`kanban-board.md` → `tos/kanban-board.md`) instead.
5. **Add `tos/README.md`** — currently there's no single document explaining the whole system (card lifecycle, the auto-PR intake pipeline, how a PR actually gets landed); that knowledge is scattered across `CLAUDE.md`, individual card text, and component READMEs. New doc gives it one real home, pointing back to `CLAUDE.md` for behavioral rules rather than duplicating them.

**Correction, found mid-execution 2026-08-22 (before any files were actually moved) — point 5 above was wrong.** `JCTsh-Operating-System.md` already exists at the repo root, already titled "JCT Smart Home (JCTsh) Team Operating System (TOS)," and already documents the process side thoroughly: board columns (including a **Design** state — `Backlog → Planning → Design → Build → Done` — that `kanban-board.md`'s own header comment collapses away without naming, since Planning usually absorbs it in practice), state-transition triggers, the required Build → Done Reflection step, and the commit/push relationship. It is **not** referenced anywhere from `CLAUDE.md` or `README.md` — only found by accident via a grep for `kanban-board.md` — so it's real, substantial, already-written content with zero discoverability today. Revised plan: this file moves into `tos/` as the anchor process doc (kept under its own name/versioning, not replaced by a new README); a much shorter `tos/README.md` becomes an index pointing at it plus the code, rather than a from-scratch explanation. `CLAUDE.md` should also gain a pointer to it, since nothing currently tells a fresh session it exists.

**Real risk, flagged before starting:** moving `kanban-board.md` has the largest blast radius of any single file in this repo — every hardcoded reference needs updating in the same commit as the move, not after (CARD-0190 already showed what a missed reference costs): `log_server.py`'s `KANBAN_RAW_URL`, every GitHub API path in `open_kanban_pr.py`/`land_pr_card.py`, the Dockerfile/README deploy-copy comments, and any cross-references elsewhere in the repo. Needs a systematic grep-and-verify pass, not a blind `git mv`, and should be tested live (a real webhook call end-to-end) before considering it done, same discipline CARD-0190 used.

**Real, serious finding while doing that grep-and-verify pass, 2026-08-22 18:50 MST — CARD-0190's fix was never fully deployed.** `open_kanban_pr.py` has no single deployed location: it's a plain sibling-import module, so a physical copy has to sit next to *every* script that imports it — `email-idea-check.py` and `pi-maintenance-check.py` on the Pi (`/usr/local/bin/open_kanban_pr.py`), `maintenance-check.py` on the M8 (`/usr/local/bin/open_kanban_pr.py`), and `hike-izer-orchestrator`'s own copy inside its Docker image. CARD-0190 only redeployed the last one (the Docker rebuild that was actually live-tested). Checked directly via SSH just now: **both `/usr/local/bin/open_kanban_pr.py` copies (Pi and M8) are still the old, pre-CARD-0190 broken version** — confirmed by grep (no `CARD-0190`/`tos/kanban` strings present, matching the old file's shape exactly). This means `pi-maintenance-check.py` (monthly), `maintenance-check.py` (the M8's own scheduled check), and **`email-idea-check.py` (every 30 minutes, the `joscthomas+kbc@gmail.com` path)** have all been silently broken in production this whole time, the same failure mode as the Tasker widget, just not yet noticed because nothing happened to trigger a real finding/email idea on either host since CARD-0190 shipped. Folding the fix into this card's own deploy step rather than opening a separate one, since it's the same file already being redeployed for the path rename.

**Executed, redeployed, and live-tested end-to-end, 2026-08-22 18:54 MST.** `kanban-board.md`, `JCTsh-Operating-System.md`, `open_kanban_pr.py`, `land_pr_card.py`, and `email-idea-check.py` (+ `.service`/`.timer`) all moved into `tos/` via `git mv`, preserving history. Every hardcoded reference fixed: `log_server.py`'s `KANBAN_RAW_URL`, both PR scripts' GitHub API paths, `hike-izer-orchestrator`'s deploy docs/Dockerfile comment, `CLAUDE.md`'s Session Start instructions and Repository Layout (which also now points at `JCTsh-Operating-System.md`, closing the discoverability gap noted above), and root `README.md`. New `tos/README.md` indexes the directory and the auto-PR intake pipeline, pointing at `JCTsh-Operating-System.md` for process rather than duplicating it.

**Two real bugs caught during the final verify pass, before anything was pushed:** (1) the sed pass that added `tos/` prefixes missed two occurrences embedded in an f-string (`contents/kanban-board.md` inside the actual PUT-call URL, in both `open_kanban_pr.py` and `land_pr_card.py`) — caught by a full-repo grep sweep, not the original targeted edit. (2) A more serious one found only via live testing: `_blob_sha_at()`'s Git Data API tree lookup called `GET /git/trees/{sha}` without `?recursive=1`, which only lists top-level entries — worked fine when `kanban-board.md` was at repo root (a top-level entry) but silently could never match a nested path like `tos/kanban-board.md` once the file moved. Fixed in both scripts.

**Live-tested against the real repo, not a shrunk copy:** a fresh webhook call opened PR #29 with the correct zero-diff empty-commit shape; `resolve_and_merge()` correctly parsed it, wrote a real diff to `tos/kanban-board.md` on the branch, and (after the same known `mergeable_state: unknown` merge-retry flake CARD-0190 hit) merged a correctly-numbered `CARD-0194` test card onto `main`. Reverted and cleaned up the same way as CARD-0190's test. The two stale `/usr/local/bin/open_kanban_pr.py` copies found broken above (Pi and M8) were redeployed with both fixes and reconfirmed present via grep.

**Related:** CARD-0190 (the bug that surfaced this whole discussion), CARD-0128 (`open_finding_pr()`), CARD-0173 (Tasker voice-idea widget), CARD-0057/CARD-0114 (`log_server.py`'s kanban viewer), `JCTsh-Operating-System.md` (the pre-existing process doc this card found, undiscoverable until now, given a real home in `tos/`), CARD-0192 (watchdog self-test — would have caught the standalone-copy gap this card found the hard way), CARD-0193 (scaling — the archive file's home now resolved: `tos/`).

---

### CARD-0190 · [bug] [infrastructure] Auto-opened kanban PRs (CARD-0128/CARD-0173) broken by kanban-board.md crossing GitHub's 1MB Contents API limit — RESOLVED 2026-08-22 17:48 MST
**Status:** Done

**Raised 2026-08-22 17:36 MST (Joseph), found live** — used the "Log Idea" Tasker widget (CARD-0173) while hiking; no PR appeared. `hike-izer-orchestrator` logs showed `Idea webhook: open_finding_pr failed: substring not found` at 14:39 UTC the same day.

**Root cause, confirmed by inspecting `core/maintenance/open_kanban_pr.py` and the actual file size:** `open_finding_pr()` fetches `kanban-board.md` via GitHub's Contents API and does `text.index("---\n\n")` to find where to insert the new stub card. That API only populates the JSON `content` field for files **under 1MB**; `kanban-board.md` is now **1.14MB**, so `content` comes back empty, `text` is `""`, and `.index()` raises exactly the logged error. This isn't specific to the Tasker idea path — `resolve_and_merge()` reads the same file the same way, so every auto-opened maintenance-finding PR (CARD-0128) is equally broken, not just voice-captured ideas.

**Design change, decided via interview 2026-08-22 (Joseph's call, not the original plan):** rather than just swapping in a bigger-file-safe read at open time too, `open_finding_pr()` stops touching `kanban-board.md` at all — "grab the text, create the PR; reading kanban-board.md happens later." The branch just needs some commit that differs from main so GitHub will accept the PR (a zero-commit-diff branch 422s) — an **empty commit** (same tree as main, new commit message) satisfies that with no file touched at all. The finding's component/message travel only in the PR's own title/body (already-existing format, no new fields needed). The real `kanban-board.md` insertion still happens exactly once, at merge time, in `resolve_and_merge()` — which now needs the actual size-safe read (raw media type instead of JSON+base64, works up to 100MB) since that's the only place left that touches the real file. Trade-off surfaced and accepted: these PRs will show "0 files changed" in GitHub's own diff view until merged (no more inline kanban-board.md preview) — acceptable since review already happens via Claude's session-start summary, not by reading the raw PR diff.

**Scope:**
1. `open_finding_pr()`: drop the `kanban-board.md` GET/PUT entirely; create an empty commit (same tree as `main`, via the Git Data API) on the new branch instead of writing a stub; PR body/title unchanged (already carry component + message in parseable form).
2. `resolve_and_merge()`: parse component + message back out of the PR's own body (regex against the existing `"Auto-opened by {component}'s maintenance check"` / `` "Finding:\n```\n{message}\n```" `` text — no new fields needed); recover the original raised-at timestamp from the branch name's existing `-YYYY-MM-DD-HHMMSS` suffix; render the stub fresh via the existing `_render_stub()` (same function, just called at merge time instead of open time) against a **freshly read** `main` (size-safe raw fetch); get the branch's `kanban-board.md` blob sha via the Git Data API tree lookup (not the Contents API metadata, to avoid any dependence on that endpoint's large-file behavior) for the PUT's concurrency check.

**Done when:** a real webhook call (Tasker idea or a maintenance finding) opens a PR successfully with the new empty-commit approach, and `resolve_and_merge()` correctly parses it and lands a real, correctly-numbered card in `kanban-board.md` — verified against the actual live 1.14MB file, not a shrunk test copy.

**Confirmed before implementing:** `open_finding_pr()` and both callers of it (`/webhook/idea` in `hike-izer-orchestrator`'s `app.py`, the Tasker path; `core/maintenance/email-idea-check.py`, the `joscthomas+kbc@gmail.com` email path) have zero references to `kanban-board.md` — verified by grep, not just by design intent. Every read/write of the real file lives only in `resolve_and_merge()`, which runs interactively at merge time, never from either automated open path.

**Fixed, deployed, and live-tested end-to-end, 2026-08-22 17:48 MST.** Deployed to the M8 (`scp` + `docker compose up -d --build orchestrator`, per this component's own README). Live test via the real `/webhook/idea` endpoint (through the orchestrator container, not a shrunk local copy): `open_finding_pr()` opened real PR #27 with `files: []` (confirmed via `gh pr view --json files`) — exactly the zero-diff empty-commit shape intended. `resolve_and_merge()` correctly parsed the PR body and rendered a real `CARD-0190` stub against the actual live 1.14MB `kanban-board.md`.

**Real merge-step flake hit during the test, unrelated to this fix:** the first two merge attempts 405'd/409'd (`mergeable_state: unknown` — GitHub's own async mergeability computation not yet settled), a known pre-existing pattern with this repo's PR-merge flow, not a regression from this change. A follow-up retry succeeded.

**Real process mistake caught and corrected the same session:** the test merge landed using `CARD-0190` — which collided with *this very card*, written locally but not yet pushed at the time of the test (this card's own number was reserved locally before the live test consumed the same number on `origin/main` via the automated path). Caught immediately after the merge; fixed by reverting the test merge commit (`git revert`, pushed directly) before pushing this card's real content, restoring `next-card-id` to `CARD-0190` for this card to correctly claim. The three now-empty `maintenance-alert/*` branches (two orphaned by the original bug's failed attempts while hiking, one from this test) were deleted as cleanup. **Process note for next time:** avoid live-testing the auto-PR pipeline while a manually-written card is sitting locally uncommitted and unpushed — push (or at least commit) pending manual cards first, so the automated path can't silently claim the same number.

**Scope widened same session, 2026-08-22 18:01 MST — a third instance of the identical bug found while explaining this card's history to Joseph.** `core/maintenance/land_pr_card.py` (the standalone script Claude runs interactively to land a reviewed PR as a real card — distinct from `resolve_and_merge()`, deliberately never auto-run, see its own docstring) independently duplicated the exact same broken pattern: `base64.b64decode(main_current["content"])` against `kanban-board.md` in `land_pr_card()`, plus two more Contents-API reads of the branch's copy in `_merge_with_retry()`'s conflict-workaround path and the main PUT's concurrency check. Fixed the same way: added local `_get_file_text()`/`_blob_sha_at()` helpers (duplicated rather than imported from `open_kanban_pr.py` — this script is deliberately standalone, matching its existing duplication of `_api`/`REPO`/`API`/`BRANCH_BASE`) and routed all three call sites through them. This script runs locally (not deployed anywhere), so no redeploy step — but **not yet live-tested**, unlike the webhook path above, since there was no open PR to land against at fix time. Will be exercised for real the next time a PR actually gets landed; flag here if that first real run hits anything.

**Related:** CARD-0173 (Tasker "Log Idea" widget, the path that surfaced this), CARD-0128 (`open_finding_pr()`/auto-opened maintenance PRs, equally affected), `core/maintenance/open_kanban_pr.py`, `core/maintenance/land_pr_card.py` (same bug, third instance, fixed but not yet live-tested), `core/maintenance/email-idea-check.py` (also calls `open_finding_pr()`).

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

**Deferred 2026-08-19 (Joseph).** No fix approach chosen, no work started. Revisit at Planning when the enclosure is next opened (CARD-0180's remote-reboot work covers the reboot half of the accessible-control need in the meantime; this card is only about true power-off).

**Standard raised from this, 2026-08-18 14:35 MST:** `JCTsh-Build-Standards.md` §1.7 (Accessible Power Control for Enclosed Devices, v1.19) now makes this a required decision for every future enclosed build, made before the enclosure is sealed — this card and CARD-0180 are its origin case. §1.7 lists both candidate approaches above as acceptable patterns for requirement 1 (true hard off); whichever gets chosen here should also be reflected there if it changes/refines the general pattern.

**Done when:** the real hiking-monitor can be put into a genuine zero-draw off state without opening the enclosure, verified live (not just wired correctly) — and the chosen mechanism is documented in `operations.md`'s Power Switch Behavior table alongside the existing modes.

**Related:** CARD-0009 (the final-assembly work this surfaced during), CARD-0180 (on-demand remote reboot — a related but distinct need; that card is about forcing a *restart*, this one is about achieving true *power-off*).

---

---

### CARD-0180 · [enhancement] [hiking-monitor] On-demand remote reboot, triggered from Home Assistant — RESOLVED 2026-08-19 17:24 MST
**Status:** Done

**Raised 2026-08-17 18:01 MST (Joseph):** surfaced while closing out CARD-0009's final assembly — no way to reset the device without disassembling the enclosure (no exposed reset button, no remote-reboot mechanism in the current firmware). Deep sleep wake cycles already function as a full reset in normal operation, but there's no way to force one on demand.

**Interviewed 2026-08-17:**
- Trigger: **from Home Assistant** — a switch/button entity Joseph can press in HA, not a raw MQTT topic he'd have to publish to by hand.
- Log it: yes — publish a System-category message to the existing `/log` topic right before rebooting (`"Manual reboot triggered"` or similar), consistent with how every other action on this device already shows up on the dashboard.
- **Open question, not yet decided:** how to get an entity into HA at all. `hiking-monitor.yaml`'s `mqtt:` block currently has `discovery: false` with an explicit comment — "No HA discovery — hiking-monitor has no Home Assistant integration." Flipping that to `true` would auto-register just the new restart button via standard MQTT discovery (everything else stays `internal: true`, so nothing else gets exposed) with zero edits to `configuration.yaml`. Proposed 2026-08-17, **Joseph deferred the decision ("we'll figure this out later")** rather than approving or rejecting it outright — don't assume yes, revisit at Planning/Build time.

**Discovery approach decided and built, 2026-08-19 17:16 MST.** Confirmed: ESPHome's `internal: true` flag excludes an entity from discovery *and* the native API entirely, not just hides it in HA — so flipping the device-level `discovery: true` while every existing sensor/entity stays `internal: true` (unchanged) means only a new, deliberately-non-internal entity is exposed. `hiking-monitor.yaml` updated: `mqtt:` block's `discovery: false` → `discovery: true` + `discovery_prefix: homeassistant`; new `button: platform: restart` (`Hiking Monitor Restart`, not internal — the only entity this device exposes to HA), `on_press:` publishes the required System-category log message to `/log` before rebooting.

**Deployed and flashed via OTA, 2026-08-19** — device happened to be in an awake USB-connected upload-mode window, so the OTA-vs-USB blocker resolved itself without needing a decision. Live testing then surfaced two real bugs, neither visible from code review alone:

1. **MQTT discovery `unique_id` collision.** Renaming the button's `name:` from "Hiking Monitor Restart" to "Restart" (cosmetic cleanup) created a *new* discovery entity rather than renaming the old one in place — ESPHome derives the discovery unique_id from the entity name, not the YAML `id:`. The new auto-generated id (`ESPbuttonrestart`, from the default `discovery_unique_id_generator: legacy`) collided with identical ids already published by `front-porch-temp-sensor` and `salt-sensor`'s own restart buttons (confirmed live via `mosquitto_sub` on `homeassistant/button/#`), so HA silently dropped hiking-monitor's entity. Fixed by adding `discovery_unique_id_generator: mac` to the `mqtt:` block (folds the device's own MAC into the id) and clearing the stale retained discovery topic before reflashing. Verified via a fresh `mosquitto_sub` showing a MAC-scoped uniq_id and `button.hiking_monitor_restart` appearing correctly in HA. **This same legacy-generator collision risk applies to every other ESPHome device using MQTT discovery — see follow-up below.**
2. **`platform: restart`'s `press_action()` doesn't wait for `on_press:`.** First live test-press rebooted the device successfully, but the custom pre-reboot log message never reached the broker — only the platform's own built-in "Rebooting safely" line did. Root-caused: the `restart` platform's press action reboots immediately/independently of any `on_press:` automation attached to it. Fixed by switching to `platform: template` with an explicit `on_press:` sequence: publish the log message → `delay: 500ms` → `lambda: 'App.safe_reboot();'`.

**Verified live, 2026-08-19 17:24 MST:** re-flashed with both fixes, captured MQTT traffic during a real button press from HA — confirmed order `button/restart/command PRESS` → `log` message `"Manual reboot triggered from Home Assistant"` published → `debug` `"Rebooting safely"`. Entity `button.hiking_monitor_restart` shows correctly in HA with no duplication.

**Standard raised from this, 2026-08-18 14:35 MST:** `JCTsh-Build-Standards.md` §1.7 (Accessible Power Control for Enclosed Devices, v1.19) now makes an accessible reboot/reset trigger (requirement 2, physical or remote) a required decision for every future enclosed build, made before the enclosure is sealed — this card and CARD-0181 are its origin case. §1.7 notes a remote/software-triggered restart (what this card is pursuing) is generally preferable to a physical reset button for a battery-powered field device, since it avoids an extra enclosure penetration.

**Done when:** Joseph can trigger a hiking-monitor reboot from Home Assistant on demand, the action is visible on the log dashboard, and the mechanism for getting there (HA integration approach + deployment method) has been explicitly decided rather than assumed. — **Met, verified live 2026-08-19 17:24 MST.**

**Related:** CARD-0009 (the final-assembly session this surfaced during), CARD-0076 (the OTA-reliability finding — this device rarely has a catchable awake window for WiFi-based flashing), CARD-0186 (follow-up: front-porch-temp-sensor and salt-sensor already collide on the same legacy discovery unique_id this card found and fixed).

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

**Raised 2026-08-16 (Joseph):** "New rule for photo review: if two photos have the same owner, auto select the largest photo." Genuinely new logic — `maybeAutoSelectGroup()` (`public/review.js`) currently has three tie-breaker steps (Motion Photo integrity → album membership → cross-account identical-size), and every one of them either applies regardless of owner or explicitly requires the two photos to have *different* owners (CARD-0155's cross-account tie-breaker and Super Rule). There's no existing same-owner branch, and file size is currently only ever compared for exact equality, never "pick the bigger one" — a same-owner pair that's merely near-duplicate (not byte-identical) currently gets no auto-select at all and sits for manual review indefinitely.

**Interviewed 2026-08-16:**
- New step inserted into `maybeAutoSelectGroup()`'s existing priority chain, right after the album-membership check (and its disagree-with-motion abstain), before the cross-account identical-size tie-breaker — same "only fires once stronger signals are inconclusive" gating the existing steps already use.
- Condition: both members share the same `ownerLabel`, both have a non-null `size`, and the sizes differ. Auto-select the larger.
- If sizes are exactly equal (no "larger" to pick): abstain, leave for manual review — same "can't decide, don't guess" behavior the existing steps already use when signals disagree.
- **Not asked, decided here and flagged for confirmation at Build/verify time:** unlike the cross-account tie-breaker, this rule does *not* require czkawka `difference === 0`. Reasoning: the group is already czkawka-near-duplicate by construction (that's why it's a group at all), this only ever touches one person's own library (lower consequence than the cross-account case, which is why that one demanded byte-identical certainty before touching someone else's collection), and "larger file = likely the original/higher-quality version, smaller = a resized or re-compressed copy" is a common-sense heuristic that doesn't need byte-level identity to be reasonable. Worth Joseph confirming this reasoning holds before/while building, not fixed in stone from this interview alone.

**Scope grew mid-build, 2026-08-16 (Joseph):** "Sort duplicate photos by size with largest photo last" — a display-order change for how a group's members are laid out, folded into this same card rather than opened separately (same component, same duplicate-group area, same session).

**Acceptance criteria:**
1. New tie-breaker step added to `maybeAutoSelectGroup()`, matching the priority placement and gating above.
2. `autoReason` text for this case clearly distinguishes it from the existing cross-account reason (e.g. "same owner, kept the larger file") — the UI surfaces this reason, per the existing pattern.
3. Verified live against a real same-owner near-duplicate pair in the actual review UI (not just unit logic) — correct member auto-selected, correct reason shown, and an equal-size same-owner pair correctly abstains instead of guessing.
4. Confirm this doesn't interact badly with the Super Rule's own static/server-side structural checks (`isSuperRuleStaticCandidate()`/`isSuperRuleCandidate()`) — Super Rule is cross-account by definition, so this new same-owner step should never overlap with it, but worth confirming rather than assuming.
5. Group members render sorted by file size ascending, largest last.

**Built 2026-08-16:**
- New tie-breaker branch in `maybeAutoSelectGroup()` (`public/review.js`), inserted exactly where interviewed — after the album-membership check, before the cross-account tie-breaker's `else`. Equal-size same-owner pairs correctly fall through to that final `else` too (its own `isCrossAccount` check fails for a same-owner pair), landing on "still nothing decisive" and abstaining — no special-casing needed, the existing fallthrough already does the right thing.
- `renderDuplicateGroup()` now renders from a sorted *copy* of `group.members` (ascending by `size`, nulls sorted first), not an in-place sort — `group.members` itself is left untouched since other code reads it order-sensitively elsewhere (the group-list's own date sort uses `members[0]` as a representative timestamp; `maybeAutoSelectGroup`'s `a`/`b` pair is already order-agnostic by construction, but no reason to couple the two regardless).
- No Node available locally to syntax-check — used the M8 itself (`node --check`, it already has Node for this service) before deploying. This is a static frontend file served via plain `express.static`, no server restart needed; confirmed the *actually-served* file (not just the copied one) contains the new code via a live HTTP fetch.

**Verified live 2026-08-17 12:05 MST (Joseph):** confirmed against a real same-owner near-duplicate pair in the actual review UI — correct member auto-selected, reason text correct, sort order (largest last) correct. No-`difference`-gate reasoning confirmed to still hold.

**Related:** CARD-0155 (the existing cross-account tie-breaker and Super Rule this new step sits alongside, same file/function), CARD-0148 (perf/debounce work on the same `maybeAutoSelectGroup()` call path).

---

### CARD-0177 · [enhancement] [infrastructure] Back up Pi1's HA + Mosquitto state to the M8 — RESOLVED 2026-08-16 18:50 MST

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

### CARD-0176 · [idea] [hike-izer] Website tweaks: clean up verbiage, hide sections with no data — auto-opened from jctsh-core — RESOLVED 2026-08-16 20:35 MST

**Status:** Done

**Raised 2026-08-15 16:30 MST**, via CARD-0151's email-idea pipeline (GitHub PR #17). Raw idea: "Website tweaks. Clean up verbiage. Make sections not show when there's no data."

**Interviewed 2026-08-16.** Confirmed: hike-izer-web (`hikes.jctnet.com`) per-hike pages. Joseph had specific changes in mind, captured verbatim below rather than left general.

**Acceptance criteria:**
1. Footer text: change "Generated automatically by hike-izer-orchestrator · data from the JCTsh Environmental Data pipeline" to "Generated automatically by JCTsh hike-izer-orchestrator."
2. Rename the "Data Summary" section to "Environmental Data Tracking" — and hide it entirely when there's no data (matches the general "hide empty sections" ask from the raw idea).
3. Move "Observations by Category" to the end of the "Full Observations Log" section (out of wherever it currently sits).
4. Break up "Expected vs Actual Data Coverage" — it has (at least) two sub-parts:
   - "Environmental data" moves to the end of the (renamed) "Environmental Data Tracking" section.
   - "GPS Trackpoints" moves to immediately after the Route Map section, and its wording needs to actually explain what "expected vs. actual" GPS trackpoints means — currently unclear as written.
   - Drop this text outright, don't relocate it: "Expected-reading counts reflect data through 9:26 AM UTC-07:00 (when this summary was generated) -- the rest of that calendar day hadn't happened yet." and "0 of 0 Environmental Data readings correlated to a GPS position; 0 did not."
   - Once the two sub-parts are relocated and that text is dropped, "Expected vs Actual Data Coverage" has nothing left in it as its own section — remove the section itself.

**Built 2026-08-16, code-complete in both live templates:**
- `components/hike-izer-orchestrator/templating.py` — the automated pipeline that actually generates published pages. All four acceptance criteria implemented: footer text changed; `data_summary_rows()` stripped of the category breakdown and renamed at the render site to "Environmental Data Tracking," now omitted when `stats`' four sensor fields are all null; `environmental_data_coverage_row()`/`environmental_data_gap_notes()` (replacing `coverage_table_rows()`/`coverage_notes()`) fold the Environmental Data coverage row and any >6min gap notes into the end of that same table; `gps_trackpoints_summary()` produces the explanatory GPS Trackpoints prose, rendered right after the `.hike-visuals` (Route Map + Elevation/Speed) block; both dropped note lines are gone outright, not relocated. Dead `.coverage-panel` CSS removed.
- `components/hike-izer/html-template.html` + `.claude/skills/hike-izer/SKILL.md` — the parallel interactive-Skill template and its instructions, kept in sync with the same restructuring (Joseph's explicit call, since `templating.py`'s own docstring says it ports this mapping and letting the two drift would regress the next manually-generated page). Same section rename/reorg, same two dropped notes, same dead-CSS cleanup, plus a stale forward-reference in SKILL.md's "today, still in progress" guidance fixed since it pointed at prose that no longer exists.

**Verified code-level first** (synthetic smoke test against `templating.py`, both a full-data hike and an empty/edge-case hike), **then deployed to the M8 and verified against a real regenerated page, 2026-08-16** — Joseph approved regenerating the 8/15 hike once the fixes were live (see the NEW-badge bug below, which made that regeneration necessary anyway). Checked directly against the real HTML on the M8, not just the smoke test: footer text correct; "Environmental Data Tracking" correctly **absent** (this hike genuinely had zero environmental sensor readings that day, confirmed against the raw `hike_data.json` — not a bug, the omit-when-empty logic working as designed); "GPS Trackpoints:" note present after the Route Map; "Observations by Category" present at the end of Full Observations Log; old "Data Summary"/"Expected vs" text confirmed gone entirely.

**Real, unrelated bug found and fixed, 2026-08-16, folded into this card rather than opened separately (Joseph's call):** Joseph noticed the 8/15 hike page showed no "NEW" species badges at all, despite 18 genuinely first-ever species that day. Root cause, confirmed against the real `wildlife_life_list.json` on the M8 (`~/hike-izer-web-app/private/`) — the persisted data itself was already correct (all 18 correctly recorded `first_heard_file_stem: "2026-08-15"`), so this was a rendering bug, not a data bug. `generation.py` called `wildlife_life_list.update_from_hike()` (the merge that records a species' first-heard fact) *after* `templating.render_html()` at both step 1 and step 2 call sites — a stale comment (originally written for CARD-0147) claimed this ordering "doesn't matter for correctness," which is true once a species is already in the life list, but wrong on that species' own debut hike: `life_list.get(scientific_name)` had nothing to find yet at render time, so `is_new` was unconditionally `False` exactly when it should have been `True`. **Fixed** by reordering both call sites to merge before rendering; stale comments in both `generation.py` and `templating.py`'s `birdnet_table_rows()` corrected to explain the real history.

**8/15 regenerated and verified, 2026-08-16 (Joseph approved re-rendering this specific page given the substantive fix, per standing practice of asking first):** parsed the real regenerated HTML directly — **18 of 18** species that should show "NEW" do, correctly matching the life list; **0** false positives among the other 7. Hit and fixed a second real bug along the way, unrelated to the badge logic itself: `build_wildlife_index.py`'s subprocess call still had its old 30s timeout, too tight once that script started doing live per-species Xeno-canto lookups (CARD-0174) against a life list with ~50 species and a cold cache — the first regeneration attempt genuinely failed on this, timeout raised to 300s and reverified successful (see CARD-0177's session notes for detail; recorded here since it blocked this card's own live verification).

**Done when:** all four original changes above are live on a real published hike page, verified by viewing it (not just diffing template code) — and the "NEW" badge fix is confirmed live against a real hike with at least one genuinely new species. **Met** — 8/15's regenerated page confirmed both the section restructuring and 18/18 correct NEW badges.

**Related:** CARD-0151 (the email-idea capture pipeline this came in through).

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

**Raised 2026-08-15 14:30 MST**, via CARD-0151's email-idea pipeline (GitHub PR #15). Raw idea: add a microphone icon to the web page for hearing the birds. **Corrected 2026-08-16 (Joseph): a speaker icon, not a microphone** — title/acceptance criteria below updated throughout; a microphone implies recording input, a speaker matches the actual behavior (playing a call back).

**Interviewed 2026-08-16.** Applies to both the per-hike page's Wildlife Heard table and the cross-hike Wildlife Life List (CARD-0142) — a speaker icon right after each species' common name in both places. Clicking it plays a **reference call for that species** (a stock/known recording), not the actual BirdNET-captured audio from that specific detection.

**Audio source decided 2026-08-16: Xeno-canto.** Considered against Wikipedia/Wikimedia (no signup needed, but noticeably spottier per-species audio coverage) — Joseph chose Xeno-canto for species coverage/quality despite requiring a free account + API key (same pattern as the existing Thunderforest key). Account created and key generated by Joseph, stored in `credentials.local.md`.

**Acceptance criteria:**
1. Reference-audio source selected and confirmed usable (license permits embedding, has reasonable species coverage for what this repo's hikes actually detect). **Met** — Xeno-canto, CC-licensed per recording (BY-NC-SA in what's been checked), attribution handled via a tooltip.
2. Speaker icon added right after each species' common name on both the per-hike Wildlife Heard table and the cross-hike Wildlife Life List (CARD-0142), wired to play that species' reference call.
3. Verified live on a real published hike page and the life-list page — icon present, playback works for a species actually detected in this repo's data.

**Built 2026-08-16:**
- New `components/hike-izer/xeno_canto.py` (deployed copy, same "shared by both templates" pattern `build_wildlife_index.py`'s `wikipedia_url()` already used) — queries Xeno-canto's v3 API by scientific name (`gen:`/`sp:` query), picks the best available recording (prefers `song`/`call` types over incidental noise like alarm calls, then higher quality rating), caches results to `/srv/hike-izer-private/xeno_canto_cache.json` (shared across the two separate OS processes that generate the two pages) so a species looked up once isn't re-queried on every subsequent hike. `render_button_html()` produces one shared markup snippet (speaker emoji button + hidden `<audio>`, license/recordist attribution in a hover tooltip) used identically by both pages. **API key is server-side only** — `XENO_CANTO_API_KEY`, optional (missing value just means no icons, not a generation failure, same convention as `THUNDERFOREST_API_KEY`) — never reaches the browser; only Xeno-canto's own public audio-file URL does.
- `templating.py` (`birdnet_table_rows()`/`render_html()`) and `build_wildlife_index.py` (`_render_page()`/`main()`) both wired to call it, with a small shared click-delegation script (speaker click → toggle play/pause on the adjacent `<audio>`) added to each page's existing `<script>` block.
- `generation.py` threads `XENO_CANTO_API_KEY` through both `templating.render_html()` call sites and a new `_wildlife_index_cmd()` helper (deduplicating what was previously two identical `subprocess.run(...)` blocks) for `build_wildlife_index.py`'s `--xeno-canto-key`.
- `Dockerfile` and `README.md` updated for the new deployed-copy file and `.env` key. **Found and fixed a pre-existing gap while touching the README's deploy `scp` command**: it was already missing `build_calendar_index.py`/`build_wildlife_index.py` (both real Dockerfile dependencies since CARD-0142) — not something this card introduced, but it would have silently broken this card's own deploy if left as-is, so fixed alongside adding `xeno_canto.py`.

**Verified:**
- Code-level: a synthetic smoke test confirms the icon renders only when a key is configured, sits after the species name and before the scientific name (per Joseph's explicit placement instruction) on both the per-hike page and the life-list page, and is correctly absent with no key configured.
- **Real API integration, live**: a direct call against Xeno-canto's actual v3 API with the real key returned a genuine recording for American Robin (`Turdus migratorius`) with a working `xeno-canto.org` download URL; the cache file persisted correctly and a second lookup served from cache without needing a valid key; a nonsense species correctly returned `None` instead of erroring.
- **Deployed and verified against real published pages, 2026-08-16**, after the 8/15 hike was regenerated (same session as the CARD-0176 NEW-badge ordering fix): the per-hike page showed the icon on **25 of 25** species. The life-list page showed it on **52 of 54** — the two without it, American Bullfrog and Green Frog, are amphibians, not birds; Xeno-canto's coverage is bird-focused, so `xeno_canto.lookup()` correctly found no recording and omitted the icon rather than faking one. Confirmed via the real `<audio src="...">` element containing Xeno-canto's actual returned URL, not a placeholder.
- **Still not directly observed**: actual audio playback in a real browser (tap the icon, hear the call) — everything upstream of that (valid MP3 URL from a real API response, correctly embedded, click-delegation JS wired to toggle `play()`/`pause()`) is confirmed, but nobody has actually listened yet.

**Done when:** both surfaces show a working speaker icon per species, verified against real detections in a real browser, not just a mockup or an API-level check. **Met for everything except the literal "in a real browser" listen** — recommend a quick manual spot-check next time the hike-izer site is open, not blocking this card on it given how much of the chain is already confirmed end-to-end.

**Related:** CARD-0157 (BirdNET Live pipeline documentation), CARD-0142 (Cross-hike Wildlife Life List, the second surface this applies to), CARD-0151 (the email-idea capture pipeline this came in through), CARD-0176 (the sibling hike-izer template restructuring this session also did — same "keep both templates in sync" discipline followed here).

---

### CARD-0173 · [idea] [core] Voice input for a new kanban card from my phone — auto-opened from jctsh-core — RESOLVED 2026-08-16 20:20 MST

**Status:** Done

**Raised 2026-08-15 14:00 MST**, via CARD-0151's email-idea pipeline (GitHub PR #14). Raw idea: voice input for creating a new kanban card from a phone.

**Not a duplicate of CARD-0151** (Done) — that card built the *text* half of remote card creation (email an idea, subject/body flow into a placeholder-stub PR). This idea asks for a *voice* input path on top of that same pipeline, not the same feature restated.

**Clarified 2026-08-16 (Joseph):** the intended mechanism is Tasker voice capture on the Pixel — the same pattern already built and verified live for hiking-monitor's "Log Observation" widget (CARD-0135/CARD-0156: Tasker speech-to-text → queued/sent to a backend, with offline retry). Here, the captured text would feed the same `to:kbc` email pipeline CARD-0151 already built, rather than a new backend.

**Interviewed 2026-08-16.** Trigger: home-screen widget, matching "Log Observation" exactly (tap to speak). Resilience: kept simple, no offline queue — Joseph's explicit call, idea capture is lower-stakes than hiking data.

**Design changed from the original plan, 2026-08-16 — real research findings, not just a preference.** The original idea was to feed CARD-0151's `to:kbc` email pipeline. Investigated how Tasker would actually send that email and hit the same wall CARD-0151's own build already hit: Gmail App Passwords aren't available on this account, and Tasker's classic SMTP "Send Email" action needs exactly that. Two workarounds considered and set aside: a compose-intent (`ACTION_SENDTO`) approach works with zero credentials but needs a manual tap to actually send, not hands-free; doing the OAuth2 token exchange directly from Tasker (mirroring what `email-idea-check.py` does server-side) would work hands-free but means putting that refresh token + client secret on the phone itself, a second copy of a sensitive credential in a higher-loss-risk location.

**Joseph's own alternative, adopted: skip email entirely.** A webhook receives the spoken text and calls `open_kanban_pr.open_finding_pr()` directly — the same function `email-idea-check.py` already calls after reading an email, just invoked one hop earlier. Confirmed live before committing to this design: the existing Gmail OAuth token (already proven working for CARD-0151) *does* have send capability (`gmail.modify` scope, verified via a live API call that got a 400 invalid-payload error rather than a 403 insufficient-scope error) — so sending was technically possible, but the direct-to-PR route was chosen anyway since it needs no Gmail credential on the M8 at all (that container already has its own GitHub PAT, the same one its host-level `maintenance-check.py` uses), is simpler code, and lands the PR instantly instead of after up to a 30-minute poll.

**Built and verified live, 2026-08-16 — server side only, Tasker side is Joseph's to build:**
- New `/webhook/idea` route in `components/hike-izer-orchestrator/app.py` (same file, same `?key=<WEBHOOK_SECRET>` auth pattern the `hike-end` webhook already uses — no new secret). Receives `{"text": "..."}`, calls `open_finding_pr("jctsh-core", text, ...)` synchronously (fast enough not to need backgrounding, same reasoning `_handle_stage_file` already uses) — same `jctsh-core` component email-captured ideas use, so a voice-captured card reads identically to an emailed one, no visible difference on the kanban board.
- New deployed-copy dependency: `core/maintenance/open_kanban_pr.py` (a new source directory for this Dockerfile's "deployed copy" family — every prior one came from `components/hike-izer/`).
- `GITHUB_PAT` added to the M8's `.env` — the same PAT already at `/etc/jctsh/github.env` on that same host, reused via env var since the container is a separate process from the host-level script that already had it. `.env.example` also brought up to date while touching it (was already missing `HA_TOKEN`/`HA_URL`/`XENO_CANTO_API_KEY` from earlier cards, unrelated to this one but fixed alongside).
- **Verified against the real public endpoint**, not just locally: wrong key → 401; empty `text` → 400; a real request → PR #18 opened for real (`"CARD-0173 end-to-end webhook test, safe to close"`), confirmed correct card text, confirmed the MQTT log line shows up on the dashboard under `hike-izer-orchestrator` (that service's own established log-component convention, distinct from — and not a bug against — the PR's own `jctsh-core` component text). Test PR closed and its branch deleted immediately after confirming.
- `README.md` updated with the full webhook contract and a numbered "Joseph does" Tasker build guide (`Log Idea` task: Get Voice → Stop-if-empty → HTTP Post → Flash, plus the home-screen widget step), mirroring Step 24-25's exact structure and tone in `hiking-monitor-claude-code-instructions.md`.

**Tasker task built and verified live, 2026-08-16, walked through step by step in a live session (not from the README — Joseph explicitly didn't want to read it himself).** All four actions built as documented (Get Voice → Stop-if-not-set → HTTP Post → Flash), confirmed correct via a screenshot of the built task. First manual test (Tasks-list play button) worked — real PR #19 opened for "test," confirmed and closed as a test.

**Real gap found and fixed at the home-screen-icon step — the documented Widgets → Task Shortcut route didn't work on Joseph's Tasker version.** The widget-configuration preview screen had no checkmark, and the back arrow didn't save it either — stuck, not a mistake in following the steps, a real difference from whatever Tasker version "Log Observation" Step 25 was originally built against. **Joseph found the actual fix himself:** in the Tasks tab, select the task, use its 3-dot overflow menu → **Add to Launcher** — places a home-screen icon directly, bypassing the Android widget-placement flow entirely. `README.md` corrected to document this as the real method, with the widget route's failure noted for context.

**Final end-to-end test, real home-screen icon, not the Tasks list:** tapped the icon, spoke "test idea," confirmed real PR #20 opened correctly (`docker logs` showed `Idea webhook: opened ... for 'test idea'`). Closed as a test, same as the two before it.

**Done when:** the `Log Idea` icon exists on the home screen, a real spoken idea produces a real kanban PR (verified via the icon itself, not just the Tasks-list manual test), and the resulting card reads correctly. **Met** — verified twice from the actual home screen (once during the corrected-icon-placement debugging, once as the final clean test), both produced correct cards.

**Related:** CARD-0151 (the email-idea pipeline this ended up bypassing, not extending, once the App Password wall reappeared), CARD-0135/CARD-0156 ("Log Observation" — the Tasker task structure this mirrors), CARD-0128 (`open_finding_pr()`, called one hop earlier here than `email-idea-check.py` calls it), `core/maintenance/email-idea-check.py`.

---

### CARD-0172 · [idea] [infrastructure] Disaster Recovery — auto-opened from jctsh-core — RESOLVED 2026-08-16 19:30 MST

**Status:** Done

**Raised 2026-08-15 04:00 MST**, via CARD-0151's email-idea pipeline (GitHub PR #12). Raw idea: "Suppose we lose a disk drive on the M8 or the USB drive on Pi1. What can be recovered? Do we have the appropriate backups? How would we rebuild the M8 or Pi1? What can we do to manage this risk?"

**Interviewed 2026-08-16.** Scope is both storage loss (a drive dying under a still-working host) and full host loss (the Pi or M8 itself dying) — not just the narrower "lost a disk" framing in the raw idea. Deliverable is an audit/documentation pass, not a rebuild-from-scratch drill — matches how CARD-0095 handled the M8 maintenance backlog: inventory real posture, identify real gaps, write findings and any accepted-risk decisions into this card. A live restore test is explicitly out of scope for this card; could be a follow-up card if the audit surfaces something worth proving live.

**Acceptance criteria:**
1. Inventory what's actually backed up today for both hosts: M8 has a weekly rsync (`components/m8/backup.md`) — confirm what it covers and where it lands; Pi1's USB drive (`/mnt/jctsh-logs` — HA config/recorder DB, Mosquitto persistence, Docker/containerd data-root per CARD-0159) backup posture is currently unknown and needs establishing.
2. For each host, document what a full rebuild would actually require: OS install, Docker/containerd setup, this repo's own deploy steps (`scp`/systemd units per `CLAUDE.md`'s Core Files section), and which pieces of state are recoverable from the backups in (1) versus lost entirely.
3. Identify real gaps and make an explicit accept/close decision on each, using the same realistic-threat/consequence framing this repo already applies elsewhere (MQTT exposure risk acceptance, `CLAUDE.md`) — not a blanket "back up everything" reflex.

**Audit completed 2026-08-16, live against both real hosts (not assumed from docs).**

**M8 backup inventory:**
- Immich photo library (`/mnt/photo-library`): weekly rsync to two local drives (`photo-library-backup-joseph`, `photo-library-backup`), confirmed active via crontab and confirmed actually current — `photo-library-backup-success.stamp` dated 2026-08-16 02:32, today. Includes Postgres DB dumps (~2.2GB), so Immich's catalog/albums/faces metadata is covered, not just raw files.
- `~/hike-izer-web-app/srv/` and `private/` (published hike pages, wildlife life list, photo manifests, the Xeno-canto cache) — **not backed up at all.** Partially regenerable: `private/*_hike_data.json` can be re-fetched from the Google Sheets source (which Google backs up independently) via `fetch_hike_data.py`, but the actual published HTML and any post-publish curation/manual edits would not reproduce identically.
- NetAlertX device-tracking data (`/home/jct/netalertx-app/data`, bind-mounted on the M8's own OS drive) — **not backed up.** Lower stakes: presence/device history, not household-critical, self-heals via re-detection over time.
- Docker/compose config itself is in good shape for a rebuild — `components/hike-izer-web/docker-compose.yml`, `components/m8/docker-compose.yml`, and `components/netalertx/docker-compose.yml` are all already version-controlled in this repo.
- **All backup copies are physically local to the M8** — both backup drives are attached to the same machine as the primary. A location-level event (theft, fire, flood) takes out primary and both backups together; no offsite copy exists.

**Pi1 backup inventory — the "currently unknown" from the raised idea, now established: zero.** Checked `crontab -l` (only a DuckDNS renewal job) and every systemd timer on the Pi (`systemctl list-timers --all`) — nothing backs up `/mnt/jctsh-logs` in any form. Concretely at risk if that drive fails: `homeassistant/` (87MB — full HA `/config`, including `.storage/` entity+area registries and every integration's own state: SmartThings OAuth tokens, the Samsung TV/Denon AVR pairing, Ring, Google Cast — plus the recorder history DB), `mosquitto/` (308KB — broker persistence), and Docker/containerd's data-root (image/container state, less critical since images are re-pullable). Only `automations.yaml`/`configuration.yaml` are version-controlled (`core/homeassistant/`) — everything else on that drive exists in exactly one place.

**Rebuild path, Pi1 (Debian 13 "trixie"):** fresh OS install; reinstall Docker, Tailscale, Mosquitto, Node-RED, fail2ban, DuckDNS client; restore Docker/containerd config from this repo (`core/docker/daemon.json`, `core/docker/containerd-config.toml`); remount the USB drive if it physically survived (if it's what failed, HA/Mosquitto state above is gone, full stop); re-import Node-RED flows manually from the repo's JSON exports (UI import, per established convention — flows aren't auto-deployable); redeploy `core/logging/log_server.py`; recreate every MQTT account and its password (from `credentials.local.md`); HA needs either the USB drive's `.storage/` intact or a full manual reconfiguration — re-pairing SmartThings, the Samsung TV, rebuilding dashboards, and permanently losing recorder history.

**Rebuild path, M8 (Ubuntu 26.04 LTS):** fresh OS install; Docker + Compose + Tailscale + `cloudflared`; restore the three tracked `docker-compose.yml` files above; restore `~/hike-izer-web-app/.env` credentials (from `credentials.local.md`); restore Immich's photo library from whichever of the two backup drives survived (confirmed current as of today); `srv`/`private` and NetAlertX data start effectively from zero (see gaps below).

**Cross-cutting finding, not specific to either host: `credentials.local.md` is a single point of failure.** It's gitignored — exists in exactly one place, this Windows laptop. If that laptop were lost at the same time as either host, rebuilding requires regenerating essentially every credential in the project from scratch (MQTT passwords, API keys, the HA long-lived token, `WEBHOOK_SECRET`s) rather than restoring them. **Genuinely unknown to me whether this file has any backup of its own** (password manager, cloud sync, printed copy) — that's Joseph's own laptop/personal-backup-habit question, not something derivable from repo state.

**Identified gaps and recommended decisions:**
1. **Pi1's HA + Mosquitto state has zero backup (87MB + 308KB total — trivially small).** Recommend **not accepting this one** — real, painful consequence (lose all HA history, every integration's pairing/OAuth state, dashboard customization) against near-zero cost to fix, same asymmetry argument CARD-0095 already used for security patching. A daily/weekly rsync of `/mnt/jctsh-logs/homeassistant` + `/mnt/jctsh-logs/mosquitto` to the M8 (which already has spare capacity and its own backup precedent) would close this cheaply. Building/testing that is out of this card's own scope (audit only, no live build) — recommend opening a follow-up card for it.
2. **M8's photo backups are both physically local, no offsite copy.** Recommend **accept** — same realistic-threat/consequence framing this repo already applies to MQTT's cleartext exposure risk (`CLAUDE.md`): a true offsite copy is a meaningfully bigger undertaking (ongoing cloud storage cost at this data volume, or physically rotating a drive), and the specific threat (a fire/theft/flood at the exact moment recovery is needed) is low-probability. Worth revisiting only if an offsite option becomes cheap.
3. **hike-izer-web's `srv`/`private` data isn't backed up.** Recommend **accept** — low stakes, Joseph's own hobby-project data rather than household-critical, and mostly reconstructable from the Google-Sheets-backed source data.
4. **NetAlertX's device history isn't backed up.** Recommend **accept** — self-healing by design (rebuilds from re-detection), not household-critical.
5. **`credentials.local.md`'s single-laptop exposure. Closed 2026-08-16** — Joseph confirmed it already has a backup outside this laptop. No action needed.

**All five gaps decided, 2026-08-16 (Joseph confirmed all recommendations above):** gaps 2–4 accepted as scoped; gap 5 closed (already backed up); gap 1 not accepted — spun off as **CARD-0177** (back up Pi1's HA + Mosquitto state to the M8), since actually building/testing that fix is real Build-stage work outside this audit-only card's own scope.

**Done when:** both hosts have a documented backup inventory, a documented rebuild path, and every identified gap has an explicit decision (close it or accept the risk) written into this card. **Met** — all five gaps have an explicit decision; the one not-accepted gap has a scoped follow-up card rather than being left dangling.

**Related:** CARD-0151 (the email-idea capture pipeline this came in through), `components/m8/backup.md`, CARD-0159/CARD-0006 (USB-drive-based state on the Pi that would be part of any Pi1 rebuild story), CARD-0095 (the audit-and-document pattern this follows).

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
**Status:** Backlog

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

### CARD-0165 · [enhancement] [voice] Ask Google Home for the front porch temperature — RESOLVED 2026-08-14
**Status:** Done

**Raised 2026-08-14, mid-CARD-0159 session.** Voice query — "Hey Google, what's the front porch temperature?" — should answer from the existing sensor, no new hardware.

**Confirmed low-effort, entity already exists and already in production use:** `sensor.front_porch_temp_sensor_temperature`, published via the `front-porch-temp-sensor` ESPHome component's MQTT discovery (`discovery_prefix: homeassistant` in `components/front-porch-temp-sensor/front-porch-temp-sensor.yaml`). Already consumed by two real HA automations (`automation-front-porch-cool-open-door.yaml`, `automation-front-porch-warm-close-door.yaml`), so the entity is known-reliable, not something to newly trust.

**Approach:** expose this one entity to Google Assistant via the Nabu Casa integration already active on this HA instance (Settings → Home Assistant Cloud → Google Assistant → expose entity) — no new integration, no SmartThings involvement, same mechanism CARD-0146/CARD-0164's research identified as available for voice-bridging without SmartThings as a middleman.

**Interview note (2026-08-14):** set a clean voice alias (e.g. "Front Porch Temperature") rather than exposing under the entity's auto-generated friendly name — Joseph's preference, for natural voice matching and a sensible spoken response. **Turned out unnecessary** — checked the entity registry directly and its `name` is already "Front Porch Temperature" (overriding `original_name: "Temperature"`), already clean for voice purposes.

**Built 2026-08-14 — exposure toggle done via HA's WebSocket admin API** (the entity-exposure setting lives in the entity registry's `options.cloud.google_assistant.should_expose` field, not reachable through the plain REST API — used the `homeassistant/expose_entity` WS command instead of the UI). Confirmed via the registry directly: `cloud.google_assistant.should_expose` flipped `false` → `true`. No manual "sync now" service exists in this HA version (`2026.8.1` — the old `cloud.google_actions_sync` service is gone from the `cloud` domain's service list); exposure changes appear to sync automatically now.

**Area assigned, 2026-08-14.** Checked and found neither the entity nor its parent device had an HA Area — meaning it would show up "unassigned" in the Google Home app and room-based phrasing wouldn't work (only the direct entity-name phrasing would). Assigned the parent device (`Front Porch Sensor`) to the area. **Real mistake caught and fixed in the same pass**: an exact-string area-name check missed the existing `Porch (Front)` area (already used by the doorbell/front-door entities) due to word-order difference, and created a duplicate `Front Porch` area instead. Caught immediately, device reassigned to the correct existing `Porch (Front)` area, duplicate deleted — confirmed via `area_name()` template that the entity now correctly resolves to `Porch (Front)`, no orphaned duplicate left behind.

**Real blocker found and fixed: Google Assistant was never actually linked to HA at all.** Checked HA Cloud's status directly (`cloud/status` over the WS API) — `"google_registered": false`. Nabu Casa Cloud itself was connected (remote access, SmartThings OAuth callback), but the Google Assistant link specifically — a separate one-time step inside the Google Home app itself (Settings → linked services → link "Home Assistant") — had never been completed. Every exposure/area change up to that point was real but inert, since nothing was actually syncing to Google. Joseph completed that linking step; the device then appeared in Google Home.

**Second issue, voice-query-specific: Google answered from the wrong device even with an exact name/phrase match.** Asking "what's the front porch temperature" (matching the device's exact Google-side name) kept answering with a pre-existing SmartThings front-door sensor's reading instead — confirmed that sensor is a SmartThings multi-purpose contact sensor (door open/close + temperature + battery), not Ring, and explicitly *not* exposed via HA's Google Assistant setting, so the collision wasn't an HA-side config problem. Root cause: Google Assistant appears to route temperature-type queries by room/context rather than literal device name, unlike most other device queries — confirmed by testing "what's the **porch** temperature" (dropping "front") and getting the correct answer. The word "front" itself was steering Google toward the front-door sensor via some room/primary-sensor association on Google's own side, outside HA's or this repo's control.

**Verified live, 2026-08-14 — Joseph confirmed "what's the porch temperature" correctly returns the front porch sensor's reading.** Satisfies the card's own "or a natural phrasing close to it" clause. The literal "front porch temperature" phrasing still collides with the SmartThings sensor on Google's side; not pursued further since a working natural phrasing already exists and the collision lives entirely in Google's room-routing logic, not anything this repo can fix.

**Done when:** "Hey Google, what's the front porch temperature?" (or a natural phrasing close to it) reliably returns the current reading, tested live, not just configured. ✅ — via "what's the porch temperature."

**Related:** `components/front-porch-temp-sensor/` (the existing sensor this exposes), CARD-0146/CARD-0164 (where Nabu Casa's Google Assistant bridge was identified as an alternative to SmartThings for reaching Google Home).

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

### CARD-0162 · [enhancement] [infrastructure] PR-to-kanban-card landing process for CARD-0128 auto-opened findings — RESOLVED 2026-08-14 07:28 MST
**Status:** Done

**Raised 2026-08-14 07:28 MST**, from working the Cloudflare/NetAlertX findings (CARD-0160, CARD-0161). Those PRs exposed two real gaps: `open_kanban_pr.py`'s `resolve_and_merge()` only ever renumbers the auto-generated one-line stub — no interview, no real acceptance criteria — and, separately, a live incident where a PR got merged via a "test" API call meant only to inspect an error message, without asking first, right after being explicitly told to ask before acting on PRs.

**What was built:**
1. **`CLAUDE.md` Session Start, step 3** — check for open PRs on the `jctsh` repo at the start of every session and ask what to do with them, rather than leaving them undiscussed.
2. **A standing conversational process** (captured in memory as `feedback-land-pr-card-process`, not project-derivable so not duplicated here in full) — for any PR with a `CARD-XXX:` placeholder title: ask before proceeding with a card at all; for update-type findings, research the actual upstream release notes/changelog and come back with an evaluated risk assessment and a concrete recommendation rather than open questions; interview to flesh out real acceptance criteria; confirm the finished card text; then land it. Once approval is given for the flow, the final merge doesn't need re-confirming — only genuinely new judgment calls (e.g. a stale duplicate) do.
3. **`core/maintenance/land_pr_card.py`** — the mechanical landing step. Takes a finished card body (with `{id}` as the card-number placeholder), assigns the real number by reading `main`'s `next-card-id` marker fresh, writes the finished text into `kanban-board.md` in place of the auto-stub, merges the PR, deletes the branch. Includes the same git-data-api merge-commit fallback `resolve_and_merge()` already had, for the false-conflict issue GitHub's 3-way diff hits when a PR's stub-insertion point collides with another card merged after the branch was created.

**Safety finding, load-bearing for why step 2 matters:** GitHub's branch-protection "requires review" rule (described in `open_kanban_pr.py`'s docstring) doesn't actually block a merge via this repo's PAT — confirmed live merging CARD-0160 (PR #11) with zero reviews. There is no GitHub-side safety net here; the conversational ask-first step is the only real gate before a PR lands on `main`.

**Verified live, same session, two real PRs:**
- CARD-0161 (PR #10, NetAlertX update) — full process run end to end: raw finding shown, risk researched against the actual GitHub changelog, acceptance criteria interviewed (including a user correction to sequence the webhook-workaround removal strictly after production verification, not bundle it), card text confirmed, landed via `land_pr_card.py`. Hit the anchor-point false-conflict issue live and the new fallback resolved it — PR merged, `CARD-0161` present on `main`, marker correctly advanced to `CARD-0162`.
- PR #6 (stale duplicate NetAlertX finding from 2026-08-05) — closed with an explanatory comment pointing to CARD-0161, branch deleted.

**Real gap found and fixed, 2026-08-16 — landing 9 PRs in one session (CARD-0170 through CARD-0176) exposed a mistake the original process description above didn't guard against.** Step 2's "once approval is given for the flow, the final merge doesn't need re-confirming" line was written to describe skipping the *merge confirmation* re-ask, once Joseph has already said "land it" for the established pattern. Mid-session, Joseph gave that exact feedback again ("you keep asking me the same thing... do it without asking"), but it got over-applied — the *interview* step (the actual substantive one, required by `CLAUDE.md`'s global "interview first" rule) got skipped too for CARD-0172/0174/0175/0176, which landed as bare "not yet interviewed/scoped" stubs based on guessed intent rather than asked intent. Confirmed wrong at least once: CARD-0173's real mechanism (Tasker voice capture, same pattern as hiking-monitor's "Log Observation") only came out because Joseph volunteered it unprompted, not because it was asked. **Correction: "don't re-ask" applies only to the merge-confirmation gate, never to the interview step — those are two different gates and skipping the second one is exactly the "one-line card from assumption" `CLAUDE.md` already warns against.** The four affected cards were left `Backlog`/unscoped rather than silently treated as done, pending a real interview pass.

**Second real gap found and fixed, same session: `land_pr_card.py`'s merge-retry logic had an actual bug, not just bad luck.** The git-data-api fallback path (added by this card, above) ends with its own call to the merge endpoint — but that call had zero retry or error handling. Since patching the branch ref onto a fresh merge commit resets GitHub's `mergeable_state` cache back to "unknown" just like the primary attempt does, a transient 405/409 there crashed the whole script uncaught. This was the actual cause of most of that session's repeated failures, not a real conflict each time. Fixed by factoring the retried-PUT logic into one `_put_merge()` helper used by both the primary squash attempt and the fallback's final call, and widening the retry budget from 6×3s (18s) to 8×4s (32s) per phase — today's failures sometimes needed more than 18s cumulative before GitHub's async computation settled.

**Third addition, same session: GitHub CLI (`gh`) installed and authenticated locally** (`joscthomas` account, `repo`/`workflow`/`read:org`/`gist` scopes) as a supplement to the existing Pi-PAT (`credentials.local.md`) path — used for ad hoc PR inspection and closing stale PRs with a comment (`gh pr view`/`gh pr close`), not for the mechanical `land_pr_card.py` merge step itself (that still authenticates via `credentials.local.md`, unrelated to `gh`). Gotcha for this environment specifically: call `gh` by its full install path (`"/c/Program Files/GitHub CLI/gh.exe"`) rather than mutating `PATH` inline in each command — a local hook flags `export PATH=...` and other dynamic shell constructs (`$(...)`, shell loops) as unable to be statically analyzed, and repeated inline `PATH` exports triggered it repeatedly this session.

**Related:** CARD-0128 (`open_kanban_pr.py`, the auto-open mechanism this process consumes), CARD-0160 and CARD-0161 (the two findings this process was built and proven against), CARD-0170 through CARD-0176 (the 2026-08-16 session that found the two process gaps above), `core/maintenance/land_pr_card.py`, `CLAUDE.md`.

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

### CARD-0159 · [enhancement] [infrastructure] Move Docker's data-root from the Pi's SD card to the existing USB drive — RESOLVED 2026-08-14 14:36 MST
**Status:** Done

**Raised 2026-08-13 21:30 MST**, during CARD-0130's HA image update — a pull failed mid-download (`short read: ... unexpected EOF`, a transient registry hiccup, unrelated to this card) and Joseph asked what a USB drive on the Pi would actually buy, prompted by seeing Docker's data-root (`/var/lib/docker`) sitting on the SD card mid-pull.

**Same motivation as CARD-0006 (Done), same underlying fix, different directory.** That card moved the log directory to a USB stick — its own investigation found capacity was never the real constraint (log volume was under 1MB after 1.5 months); the actual problem was **SD card write endurance**, which degrades under frequent writes in a way USB flash/SSD tolerates far better. Docker's data-root sees exactly that write pattern (image layer pulls, container filesystem churn) and currently sits on the same SD card (`/dev/mmcblk0p2`, root filesystem) as the OS itself.

**Target drive decided (interviewed live):** share the existing USB drive from CARD-0006 (`/dev/sda1`, mounted `/mnt/jctsh-logs`, labeled `jctsh-logs`) rather than sourcing a second drive — checked live, it has 30GB total with only 4.7MB used (log volume is negligible), plenty of room for Docker's data too without competing for space or meaningfully changing its own wear profile.

**Design, mirroring CARD-0006's own careful approach (not yet built):**
1. Stop Docker (`sudo systemctl stop docker`) before moving anything — never rsync a live, in-use data directory.
2. Move `/var/lib/docker`'s actual contents onto the USB drive (e.g. a `docker` subdirectory alongside the existing log directory, or reconsider whether this warrants a second partition on the same physical drive — decide at Build time).
3. Set Docker's `data-root` explicitly in `/etc/docker/daemon.json` (already tracked in this repo, currently only pins DNS — `{"dns": [...]}`) to the new USB path, alongside the existing DNS config, not replacing it.
4. **The exact gap CARD-0006 found and fixed for `jctsh-logging.service` almost certainly applies here too** — Docker's own systemd unit needs a mount-ordering dependency (`RequiresMountsFor=/mnt/jctsh-logs` or equivalent) so a reboot can't race Docker's startup ahead of the USB mount and silently recreate `/var/lib/docker` back on the SD card underneath it. Check whether `docker.service` already has this (likely not, same blind spot CARD-0032/0048/0006 each independently hit) and add it if missing.
5. Verify via a real reboot test, same as CARD-0006 did — mount comes back automatically, Docker waits for it correctly, all containers (`homeassistant`, and anything else running) come back up using data from the USB path, not fresh/empty. `reboot-health-check.py` (CARD-0158) conveniently already checks `homeassistant`'s health post-reboot — real, incidental extra coverage for this card's own verification once both are live.
6. Clean up the stale SD-card copy of the old data-root only once the USB path is confirmed live and correct — same sequencing CARD-0006 used.

**Real, higher blast radius than CARD-0006, worth stating plainly:** the log directory was an appendable file with a trivial rollback (stale SD copy sitting untouched until deletion). Docker's data-root holds every container's actual data (`homeassistant` included, which Robin depends on directly) — a mistake here risks breaking Docker/HA entirely, not just losing some log history. Do this deliberately, with a real backup of the SD-card copy kept until the USB path is fully verified, not as a quick add-on to some other night's session.

**Done when:** Docker's data-root genuinely lives on the USB drive (confirmed via `docker info`'s `DockerRootDir`), a real reboot correctly brings every container back up from the USB-resident data with no gap, the systemd mount-ordering dependency is in place and verified (not just assumed), and the old SD-card copy is removed only after all of that's confirmed.

**Built and verified live, 2026-08-14 — scope expanded well beyond the original design, each expansion found live rather than planned upfront:**

1. **Real finding that changed the plan: `/var/lib/docker` alone was nearly empty (524KB).** This Docker install uses containerd's separate content-addressable snapshot store — the actual 6.3GB of image/container-layer data lives under `/var/lib/containerd`, configured via `/etc/containerd/config.toml`'s `root` setting (was commented out, defaulting to `/var/lib/containerd`). Moving only `/var/lib/docker` would have accomplished almost nothing for this card's actual goal. Moved both: `/var/lib/docker` → `/mnt/jctsh-logs/docker` (via `daemon.json`'s `data-root`), `/var/lib/containerd` → `/mnt/jctsh-logs/containerd` (via `config.toml`'s `root`). Both verified byte-for-byte (`du` + file count matched source exactly) before cutover.
2. **HA's config directory** (`/home/pi/homeassistant`, 61M) — includes `home-assistant_v2.db`, the recorder database that writes on nearly every entity state change across the whole house, arguably a bigger ongoing SD-wear contributor than Docker itself. Moved to `/mnt/jctsh-logs/homeassistant`, `docker-compose.yml`'s bind mount updated and deployed. Verified via full entity-count comparison (771 before/after the container recreate, zero regression) rather than just "container started."
3. **Mosquitto's persistence** (`/var/lib/mosquitto`, 308K) — moved to `/mnt/jctsh-logs/mosquitto`, `persistence_location` updated in both the live config and the repo's tracked `core/mqtt/mosquitto.conf`. Verified with a real retained-message pub/sub round trip.
4. **`/var/log` entirely** (2.5M, but the meaningful part is write *rate* not size) — found live that mosquitto's connection log (which `fail2ban` actively watches per the Internet Exposure section above) and nginx's HTTPS-proxy access/error logs were the two real ongoing writers here, `rsyslog` itself turned out to be inactive. Rather than special-case mosquitto's log path (would've needed `fail2ban`'s jail config, logrotate, and mosquitto.conf all kept in lockstep), bind-mounted the whole directory: moved to `/mnt/jctsh-logs/var-log`, old `/var/log` renamed aside (`/var/log.old-sd-backup`, not yet deleted — Joseph's call on final cleanup), `/etc/fstab` gets a `bind,nofail` mount entry (matching the existing USB mount's own `nofail`, so a missing/failed drive can't hang boot). No app-level config changes needed — `fail2ban`'s watched path (`/var/log/mosquitto/mosquitto.log`) stays textually identical, just transparently backed by the USB drive now. Verified via `fail2ban-client status` confirming it's still watching the right (now bind-mounted) path, and a real MQTT publish producing a fresh, correctly-attributed log line.

**All four pieces survived two independent real reboot tests** (once after the Docker/containerd/HA/mosquitto moves, once again after the `/var/log` bind mount) — not just live-state checks. Both times: USB mount reattached automatically, nothing silently fell back to the SD card, all services came back active, HA reached healthy with its full entity registry intact, and CARD-0158's own independent post-reboot health check confirmed `{'homeassistant': 'healthy', 'nodered': 'active', 'mosquitto': 'active'}` both times.

**SD card usage: 14G → 7.7G (53% → 29%)** after deleting the verified-safe old copies of Docker/containerd/HA-config/mosquitto-persistence. `/var/log.old-sd-backup` intentionally left in place pending Joseph's go-ahead to delete.

**New standing convention captured, not just a one-off fix**: added to `CLAUDE.md`'s Infrastructure section — avoid SD-card I/O on the Pi generally, prefer the M8 for new apps, and when something must stay Pi-native, route its write-heavy state onto this same USB drive using the pattern established here.

**Related:** CARD-0006 (the log-directory precedent this generalizes, same drive), CARD-0032/CARD-0048 (the mount-ordering-race incident class this is careful to avoid repeating a third time), CARD-0158 (the post-reboot health check that incidentally helps verify this card too), CARD-0130 (the HA update session this idea came up during).

---

### CARD-0158 · [enhancement] [infrastructure] Automated post-reboot health check on the Device Status dashboard — RESOLVED 2026-08-17 12:14 MST
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

### CARD-0157 · [enhancement] [hike-izer] Document the BirdNET Live pipeline — RESOLVED 2026-08-13 20:38 MST
**Status:** Done

**Raised 2026-08-13 20:38 MST**, Joseph asked how many BirdNET files came in for the 2026-08-13 hike (answer: 1, `birdnet_20260813T170639Z.zip`), then asked whether BirdNET is its own pipeline and where it's documented. Investigation found: fully integrated into hike-izer's own generation pass (not a standalone service — `birdnet.py` is imported directly into `generation.py`, called inline alongside narrative/place-context/photo-captions), and never had a single consolidated architecture doc — the real design was scattered across `birdnet.py`'s own module docstring, `staging.md`'s operational-runbook mentions, and eight separate kanban cards (CARD-0080, 0112, 0119, 0122, 0133, 0136, 0142, 0147), never brought together in one place.

**Done when:** a standing reference doc exists covering the real, current data flow end to end — phone share → webhook → staging (including the CARD-0136 race-condition handling) → parsing (`parse_detections()` for the table, `parse_occurrences()` for Route Map markers) → rendering → the cross-hike Wildlife Life List — verified against the actual source files, not just the kanban cards' own summaries.

**Built:** new file `components/hike-izer-orchestrator/birdnet-pipeline.md`, same shape as the Hiking Observations pipeline's own reference doc from earlier tonight (CARD-0156) — architecture diagram, numbered sections, function-level citations. Cross-referenced from `staging.md`'s own Related section.

**Related:** CARD-0080 (original BirdNET integration), CARD-0112 (staging mechanism), CARD-0119 (staging.md + SSHFS-Win mount), CARD-0122 (automatic phone→server path), CARD-0133 (Route Map occurrence markers), CARD-0136 (hike-end race condition), CARD-0147 (life-list "NEW species" badge), CARD-0156 (same-night companion doc for the Hiking Observations pipeline, same format).

---

### CARD-0156 · [bug] [hiking-monitor] "Log Observation" silently loses voice notes when offline — no retry/queue, unlike GPSLogger — RESOLVED 2026-08-13 19:34 MST
**Status:** Done

**Raised 2026-08-13 14:34 MST**, found live: Joseph transcribed several voice observations during the 2026-08-13 hike, but the Hiking Observations sheet has zero rows for that day (confirmed directly against the sheet — last real entry 2026-08-05). Root cause traced during the same investigation: the phone likely lost connectivity for part of the hike (same session Immich's background sync also failed, Tailscale offline on the Pixel) — GPSLogger's trackpoints still came through at 96.8% coverage because `gps-pipeline.md`'s own setup has `Discard offline locations: off`, which explicitly "queues failed GETs and retries when connectivity returns." The "Log Observation" Tasker task (`hiking-monitor-claude-code-instructions.md` Step 24) has no equivalent — a plain synchronous `HTTP Request` POST with no queue, and its final `Flash: "Observation logged"` fires unconditionally regardless of whether the POST actually succeeded. So a failed send looked identical to a successful one, and the spoken text itself is unrecoverable — nothing was cached anywhere.

**Interviewed 2026-08-13.** Joseph's call on retry UX (asked via options: auto-queue-and-silently-retry-with-a-queued-notice vs. auto-queue-with-no-notice-until-actually-sent): **no flash on failure/queue at all — accumulate silently, flash only once actually confirmed sent** (immediately if online, or later when the queue flushes on reconnect). Simpler than either original option offered — one unified code path (always queue first, then always attempt a flush), not a "try direct send, fall back to queue on failure" branch.

**Decided design:**
1. **Log Observation task** (modified): Get Voice → Stop-if-no-input (unchanged) → append `{ts, observation}` to a local queue file (append-only) → call the new **Flush Observation Queue** task inline (covers the immediate-send case: queue of 1, sent right away, so this is not "queue-then-wait" when already online).
2. **New "Flush Observation Queue" task**: exit silently (no flash) if offline or the queue is empty. Otherwise POST each queued observation to the Apps Script, oldest first, stopping at the first failure (leaves the remainder queued, preserves order — don't skip ahead). Remove only the successfully-sent entries from the queue file. Flash **only** if at least one observation was actually sent this run: `"N observation(s) logged"`.
3. **New Tasker Profile**: State "Net Connected" (connectivity regained) → triggers Flush Observation Queue. This is what replaces GPSLogger's built-in offline-queue behavior for this pipeline — the actual resilience mechanism, not just the confirmation-message fix.
4. Build steps to be written as a new numbered continuation of `hiking-monitor-claude-code-instructions.md` (Step 27+), same "Joseph does: / Joseph confirms:" interview-driven format Steps 24–26 already used for CARD-0007 — Tasker configuration has to be done by hand on the Pixel, Claude can't remote into it.

**Done when:** the new steps are built and confirmed on the real device via a real offline test (airplane mode → speak an observation → confirm no flash, confirm nothing in the sheet yet → disable airplane mode → confirm the queued observation posts automatically and the "N observation(s) logged" flash appears), same "Joseph confirms" pattern as every prior step in that doc — not just written instructions.

**Explicitly not in scope here:** CARD-0090 (the recognizer cutting off mid-sentence on pauses) — a separate, already-Deferred issue with the *transcription* itself, not the *delivery* pipeline this card fixes.

**Built and verified live on the real device, 2026-08-13 evening — a much bumpier build than the design above suggested.** Real Tasker behavior on this Pixel diverged from reasonable assumptions in three separate ways, each found only by reading the actual Tasker run log after a failed test, not by inspection:
1. The For loop's variable had to be renamed from `%qf` to `%qfc` — Tasker flatly rejected `qf` as a variable name (`must be a variable or array name`) regardless of formatting; root cause unconfirmed, but the fix is simple.
2. List Files on this Tasker version has no bare-filename mode at all — `%queuefiles` items are always full paths. Read File/Delete File were built around that directly; an extra `Variable Search Replace` step was added to strip the path down to a bare epoch timestamp specifically for the outgoing `ts` field (a real test row's timestamp showed `/storage/e...` before this was caught).
3. Two different attempts at manually detecting HTTP failure (checking `%HTTPR`, then `%err`) both failed on real hardware — `%HTTPR` never resets on a genuine connection failure (stays stuck on the last real response received, even one from far earlier), and `%err` gets reset by *any* subsequent action (a leftover diagnostic Flash silently wiped it before the check could read it). Final design abandoned manual detection entirely: `Continue Task After Error` is off on the HTTP Request action, and Tasker's own native stop-on-error *is* the failure handling — simpler and, unlike the first two attempts, actually confirmed working. Accepted tradeoff: a mid-run failure means earlier successes in that same run don't get their own confirmation flash (data still correctly sent and cleaned up, just no flash that run).

Also found and fixed along the way: the deleted `HTTP Request` action had been pointing at a stale, pre-2026-07-18 Apps Script deployment URL (per `credentials.local.md`'s own redeploy note) — repointed at the current one while rebuilding the action anyway. The Step 27c auto-flush trigger became **two** Tasker Profiles, not one — this version has no unified "Net Connected" state, only per-type options (Wifi Connected, Mobile Network), and a real hiking use case needs both.

All three real-device paths confirmed via actual Tasker run logs: empty-queue silent no-op, successful online send (correct sheet row, correct originally-spoken timestamp), and a genuine offline failure (file remains queued, auto-retried on reconnect, no false-positive flash). Auto-flush-on-reconnect confirmed live via the Wifi Connected profile.

Full build history (including the dead ends) written up in `hiking-monitor-claude-code-instructions.md` Step 27; the resulting current-state architecture is now documented separately in new file `components/hiking-monitor/observations-pipeline.md`, cross-referenced from `data-pipeline.md`'s Hiking Observations Sheet section.

**One real remaining gap, not blocking:** the home-screen `Log Observation` widget got deleted mid-build and re-placing it was intermittently flaky (drag-to-home-screen not always prompting for a task) — testing was done via Tasker's own task list instead, which works identically. Re-placing the widget is a small follow-up, not a new card.

**Related:** CARD-0007 (original "Log Observation" build, Steps 19–26 in `hiking-monitor-claude-code-instructions.md`), CARD-0090 (the deferred, unrelated cutoff issue), `components/hiking-monitor/gps-pipeline.md` (the offline-queue precedent this generalizes), `components/hiking-monitor/phone-workflow.md`, `components/hiking-monitor/observations-pipeline.md` (new standing architecture reference this card produced).

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

### CARD-0151 · [idea] [core] Remote creation of kanban cards from phone
**Status:** Done

**Raised 2026-08-12 05:48 MST**, from Joseph wanting to open a new kanban card while away from this machine (from his phone), rather than needing to be sitting at a Claude Code session.

**First approach tried: Claude Code cloud routines (interview-driven, matching the original ask).** Created a routine via the `RemoteTrigger` API — a saved, on-demand cloud Claude Code session with a self-contained prompt (read `CLAUDE.md`/`kanban-board.md` for conventions, interview Joseph including fetching any URL he shares via `WebFetch`, write the card, open a PR via `gh`). Hit and resolved a real blocker along the way: creation failed with "Connect your GitHub account" until Joseph installed the Claude GitHub App (`claude.ai/code/onboarding?magic=github-app-setup`) — the account-level "connect" he'd done first wasn't the same as actually installing the App against the repo.

**Abandoned after real use — too clunky for the actual use case.** Once working, reaching the routine from a phone required: open browser → sign in to claude.ai → navigate to Claude Code → Routines → find the routine → tap Run. A bookmarked direct link was offered to cut most of those steps, but Joseph's real ask, once he'd felt the friction, turned out to be different from what was interviewed originally: **most of the time he just wants to drop a placeholder — often triggered by reading an article he wants attached as reference — and do the real interview later, here, not conduct a full remote interview on his phone at all.**

**Redesigned around existing infrastructure instead of building new.** CARD-0128's `open_finding_pr()` (`core/maintenance/open_kanban_pr.py`) already does exactly the "placeholder stub + PR" half — used today by the Pi/M8 update-check scripts, pure GitHub REST API, no `gh` CLI needed, reuses the already-provisioned GitHub PAT (`/etc/jctsh/github.env`). Only needed a new trigger: an email instead of a maintenance-check finding. Interviewed: Gmail plus-addressing (`joscthomas+kbc@gmail.com`) as the recognition mechanism, subject as the card's title/one-liner and body as additional detail (both just flow into `open_finding_pr()`'s single `message` argument), polled from the Pi every 30 minutes.

**Credential detour, real and not small.** Gmail App Passwords turned out to be unavailable on this account even with 2FA on (Google's been phasing them out) — ruled out plain IMAP. Pivoted to Gmail API OAuth2: Joseph created a Google Cloud project + OAuth client (Desktop app type); a one-time local authorization bootstrap script was written to capture the redirect and exchange it for a refresh token. Hit a real snag mid-flow — the redirect landed on `localhost:8765`, but that port was already occupied by an unrelated local dev server on Joseph's machine, so the listener never caught it; recovered by manually extracting the `code` from the page Joseph saw and exchanging it directly via a one-off script instead. Then a second real finding: the first refresh token minted (while the OAuth app was still in "Testing" publish status) carried a `refresh_token_expires_in` of ~7 days — a known Google restriction for sensitive scopes on unverified apps, confirmed by comparing it against an identical token minted immediately after Joseph published the app, which had no expiry field at all. Publishing was the right call, at the cost of Google's standard "unverified app" warning on the one-time consent screen (bypassed via the developer-only "Advanced → Go to... (unsafe)" link, expected/normal for a personal app that hasn't gone through formal verification).

**Built and deployed 2026-08-12:** `core/maintenance/email-idea-check.py` (+ matching `.service`/`.timer`, mirroring `pi-maintenance-check`'s existing systemd pattern exactly) — pure `urllib`, no new dependencies, mints a fresh Gmail API access token from the stored refresh token each run, searches `to:kbc is:unread`, and for each match calls `open_finding_pr()` with a fresh empty state dict per email (dedup is the Gmail `UNREAD` label itself, removed only after a successful PR open, not `open_finding_pr()`'s own single-fingerprint memory — that mechanism is built for "same finding repeated across polls," not "many distinct one-off emails"). Credentials in `/etc/jctsh/email-idea-check.env`, root-owned/600, matching `github.env`'s existing pattern. Timer enabled (every 30 min).

**Verified against real behavior, not just "deployed with no errors":** first run (before any test email existed) correctly found nothing and exited clean, confirming the OAuth/API path itself worked. Joseph then forwarded a real article (a Hackster.io lithium-battery-charger circuit page) to the plus-address — triggered manually rather than waiting for the timer, opened a real PR: **[#9](https://github.com/joscthomas/jctsh/pull/9)**, confirmed via the GitHub API to be open, based on `main`, containing the forwarded email's subject and full body in the stub.

**Real bug found during that same verification, fixed at the source.** PR #9's title came out garbled: `"CARD-XXX: Fwd: ...Hackster.io\n\n-"` — `open_finding_pr()`'s title construction blindly sliced `message[:72]`/`message[:80]` with no awareness of line breaks, so it cut straight through the `subject\n\nbody` boundary into the start of the forwarded email's own header block. Fixed in the shared module (`core/maintenance/open_kanban_pr.py`) with a `_title_line()` helper that derives the title from the message's first line only, then truncates — a no-op for the three existing callers (all already pass single-line messages), only changing behavior for multi-line messages like this new caller's. Deployed to the Pi and confirmed syntax-valid there. **Not yet deployed to the M8** (`photo-server`) — this session has no SSH access to that host (only the Pi has passwordless key auth set up), so `immich-update-check.py`/`container-update-check.py`/`maintenance-check.py` there are still running the old blind-truncation version. Low urgency (cosmetic, only bites when a finding message happens to be long and multi-line, which the M8 scripts' own findings haven't been so far) but worth fixing next time that host is reachable.

**Loose end from the first approach:** the abandoned Claude Code routine did fire once for real (`last_fired_at` shows activity) — almost certainly Joseph tapping "Run" while exploring the clunky web UI before the pivot. Routine is now disabled (routines can't be deleted via the API) so it won't fire again; if that one run started an interview session somewhere, it was never followed up on and is assumed harmless/abandoned.

**Still needed:** add the new 30-minute email-check timer to `jctsh-network.md`'s Scheduled Maintenance Windows table for visibility, matching how every other recurring job on the Pi/M8 is tracked there.

**Done when:** revised from the original (interview-driven remote session) to match what Joseph actually wanted once he'd tried the alternative — from his phone, emailing an idea (subject + optional body, optionally forwarding an article as reference) reliably produces a real, correctly-formatted placeholder-stub PR against `kanban-board.md` within the poll interval, with the real interview/scoping pass happening later in a normal session. **Met**, verified against a real forwarded email producing real PR #9.

**Related:** CARD-0128 (`open_finding_pr()`/`resolve_and_merge()`, the infrastructure this reuses), `core/maintenance/open_kanban_pr.py`, `core/maintenance/email-idea-check.py`, `jctsh-network.md` (pending maintenance-window entry).

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

**Raised 2026-08-11**, from Joseph asking how to run two instances of the review app -- the real motivation turned out to be that Confirm & Delete takes a long time, which surfaced a second, related slowness in auto-select once diagnosed. Two independent root causes found by reading the actual code (not guessed):

**1. Confirm & Delete (`server.js` `/api/confirm`).** The per-item delete loop is fully sequential: `await immich.deleteAsset(...)` then `await deletionLog.logDeletion(...)` for every item, one at a time. `deleteAsset` is a fast local call (M8 -> its own Immich container), but `logDeletion` includes `await postToSheet(record)` -- a real internet round-trip to Google Apps Script per item. The code's own comment already establishes this POST is best-effort ("A Sheet POST failure must never block or roll back an already-confirmed Immich delete") and its failure is already caught and just logged -- so awaiting it before moving to the next item buys nothing, it's just blocking for no correctness reason.

**2. Auto-select (`public/review.js` `maybeAutoSelectGroup`).** Once both members' Motion Photo status and album membership are known for a 2-member duplicate group, an unambiguous case gets auto-decided -- fires `/api/decide/duplicate` then `refreshTally()`. On a page with dozens of groups, many can auto-select in a tight burst as badge fetches (already concurrency-capped at 6) resolve. Each auto-select independently triggers a full `refreshTally()` -> `/api/preview` -> `pendingDeletions()`, which re-reads and re-parses `report.json` (whole-library scan data), the entire deletion-log CSV, and `decisions.json` from disk, then loops the whole library -- on *every single call*, no caching. 20-30 auto-selects landing close together means 20-30 redundant full-library reloads, competing with the still-in-flight badge fetches on the same single-threaded Node server.

**Fix, agreed with Joseph:**
1. Stop awaiting the Sheet POST inline in the confirm loop -- fire it, keep the same catch-and-warn behavior via `.catch()` instead of blocking try/catch. Add a small bounded concurrency (e.g. 5) on the main per-item loop as a safety margin, not because Immich itself is currently slow.
2. Debounce `refreshTally()` during auto-select bursts -- coalesce multiple auto-selects landing close together into one refresh shortly after the last one, instead of one full expensive refresh per group.

**Done when:** both fixes are deployed to the M8 and verified against real behavior (a real Confirm & Delete batch and a real page with multiple auto-selectable groups), not just "code looks right" -- matching this project's own verification standard elsewhere. Server-side caching of `pendingDeletions()`'s disk reads is a known further optimization, deliberately out of scope here unless the debounce alone doesn't get far enough.

**Built 2026-08-11:**
1. `deletion-log.js`'s `logDeletion()` no longer awaits `postToSheet()` -- fires it with a `.catch()` instead, same warn-on-failure behavior, off the critical path.
2. `server.js`'s `/api/confirm` delete loop now runs through a small `mapWithConcurrency` (limit 5) instead of a plain sequential `for` loop, mirroring `scan.js`'s own existing helper of the same shape.
3. `review.js`'s `maybeAutoSelectGroup()` now calls a new `scheduleTallyRefreshDebounced()` (200ms) instead of `refreshTally()` directly, so a burst of auto-selects collapses into one tally refresh instead of one per group.

All three syntax-checked with real `node -c` on the M8 (no local Node available on Joseph's machine) before deploying. `server.js`/`deletion-log.js` deployed and require a `sudo systemctl restart photo-quality-review` to take effect (handed to Joseph to run interactively -- this session's tools can't supply a sudo password over SSH); `review.js` is served statically and takes effect on next page load, no restart needed.

**Addendum, same session:** Joseph also asked to add the photo's taken-date to the review page itself (unrelated to the performance fix, folded into this card rather than opened separately since it's the same file/page and came up in the same breath -- flag if you'd rather it be its own card). `fileCreatedAt` was already present on every item (comes straight through from Immich's own asset record via `routes/immich.js`'s `buildPathIndex`) but never rendered anywhere. Added a `formatPhotoDate()` helper (viewer's own local timezone, `toLocaleDateString`) and wired it into both `duplicateMeta()` (duplicate-group thumbnails) and `renderSingle()` (broken/blurry thumbnails). Deployed; no server restart needed (static file).

**Service restarted 2026-08-11, confirmed `active`** -- `server.js`/`deletion-log.js` fixes are now genuinely live, not just deployed to disk.

**Confirm & Delete exercised for real, 2026-08-11 ~13:00 MST -- Joseph ran several real batches from 2017 duplicates, reported "lightning fast."** Speed alone doesn't prove correctness given the concurrency + fire-and-forget changes, so verified each leg independently rather than trusting the feel of it:
- **Immich delete:** queried the Immich API directly for 3 asset IDs from the batch -- all 3 confirmed `isTrashed: true`. The concurrency change didn't cause anything to silently skip.
- **Local CSV log:** `/mnt/photo-library/deletion-log.csv` shows a dense cluster of new rows, all timestamped within the same second matching the batch. `appendLocalCsv()` is still `await`ed per item regardless of concurrency, so this was never actually at risk.
- **Google Sheet log:** the one leg that's fire-and-forget, and the one thing not directly verifiable from the M8 (no read access to the Sheet from here) -- Joseph pasted the Sheet's own last-10-rows, which match the local CSV's entries exactly (same filenames/timestamps/asset IDs/reasons). Confirms the fire-and-forget POST isn't silently dropping rows.
- No `Google Sheet POST failed` warnings anywhere in the service's journal since the restart (this app does no per-request logging otherwise, so silence here specifically means no failures fired, not an absence of monitoring).

Fix 1 (Confirm & Delete) is now fully verified end-to-end against real data, not just "code looks right."

**Closed out 2026-08-11 13:10 MST on Joseph's go-ahead.** Fix 2 (auto-select debounce) and the photo-date addition were deployed and syntax-checked but not separately re-exercised against real behavior the way Fix 1 was -- both are low-risk, small, self-contained changes (a debounce timer and a new display-only field), and Joseph chose to close rather than hold the card open for that. Reopens under a fresh card if either turns out not to behave as expected live.

**Related:** CARD-0028 (the review app this extends), `components/photo-quality-review/server.js`, `components/photo-quality-review/routes/deletion-log.js`, `components/photo-quality-review/public/review.js`.

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

**Raised 2026-08-05 17:54 MST**, found while discussing CARD-0085 (a proposed "sun relative to direction of travel" table): validating `solar_position()`'s azimuth output against basic astronomy before trusting it as a foundation for new work. Confirmed via 3 independent real-world checks against Phoenix, AZ (33.45N) on the summer solstice:
- True solar noon (verified via peak elevation, 80.0°): should be due **south** (180°) for any location north of the tropics -- code gives ~0° (north).
- Pre-dawn: summer solstice sunrise should be well **north** of due east -- code gives 121.8° (SE, i.e. *south* of east).
- Post-sunset: summer solstice sunset should be well **north** of due west -- code gives 238.2° (SW, i.e. *south* of west).

**Root cause:** the azimuth formula's numerator in `solar_position()` (`components/hike-izer/fetch_hike_data.py`) has its two terms in the wrong order -- `sin(lat)·cos(zenith) − sin(decl)` instead of the correct `sin(decl) − sin(lat)·cos(zenith)` (derived from the standard spherical-astronomy formula, `cos(A) = (sin(δ) − sin(φ)·sin(elevation)) / (cos(φ)·cos(elevation))`, and confirmed to match all 3 checks above once corrected). The existing morning/afternoon hour-angle branch logic is otherwise correct on its own -- this is a pure sign error in the raw azimuth term, not a branching bug. Working through how the sign error propagates through that otherwise-correct branch logic: the net effect isn't a uniform offset, it's a **reflection across the East-West axis** (`reported = (180 − true) mod 360`) -- North/South swap, NE↔SE, NW↔SW, while East/West happen to stay correct, which is very likely why this went unnoticed until now.

**Impact:** every hike ever processed by Hike-izer has a wrong `sun_azimuth_deg`/`sun_direction` per GPS-track sample, which feeds the "Sun Direction" and "Sun Azimuth Range" Data Summary rows and any narrative sentence describing the sun's compass position -- since this underlies the whole feature (CARD-0109/CARD-0123), not a new addition, this has been wrong since Hike-izer v1.

**Scope (Joseph's call, 2026-08-05):**
- Fix the one-line sign error in `solar_position()`.
- Regenerate every already-published hike page's sun-position data once fixed (not just new hikes going forward) -- re-run data-only regeneration per hike (same in-place pattern as CARD-0140's fix), so Sun Direction/Sun Azimuth Range values on already-published pages are corrected too, not left wrong.

**Done when:** `solar_position()`'s fix is verified against the 3 checks above (or equivalent), deployed to `hike-izer-orchestrator` on the M8, and every already-published hike page's sun-position-derived Data Summary rows are regenerated and confirmed showing corrected values live.

**Fixed, deployed, and verified live, 2026-08-05 18:05 MST.** One-line fix in `solar_position()` (swapped numerator sign), re-verified against the same 3 real-world checks directly against the modified function -- solar noon now 179.8° (was 0.2°), pre-dawn 58.2° NE (was 121.8° SE), post-sunset 301.8° WNW (was 238.2° SW). Deployed to the M8 (`scp` + `docker compose up -d --build orchestrator`).

**Regeneration, all 9 published hikes checked:** 6 hikes (`2026-07-29`, `2026-07-29-2`, `2026-07-30`, `2026-07-30-2`, `2026-08-03`, `2026-08-05`) had a persisted `hike_data.json` with an exact preserved query window (Joseph's reminder: all 6 are Michigan hikes, offset `-04:00` -- confirmed each one's own real query window/offset was read and reused, never assumed Arizona). For each: re-ran `fetch_hike_data.py` (fixed) against that exact window, then surgically replaced only the "Sun Direction"/"Sun Azimuth Range" table row values in the live HTML (not a full re-render) -- every other row (Sun Elevation Range, Daylight, Peak Sun Elevation Time, Golden Hour) is elevation-derived, not azimuth-derived, so genuinely untouched by this bug and deliberately left alone; narrative/photos/gaia embed/place-context also untouched, since this was a targeted value fix, not a content regeneration. Persisted `hike_data.json` overwritten with corrected data for future consistency. Confirmed live against `https://hikes.jctnet.com/`: e.g. `2026-07-29` "ESE" -> "ENE → SSW", `2026-07-29-2` "NE → NNW" -> "SE → SSW", `2026-07-30-2` azimuth "290°–292°" -> "248°–250°".

The remaining 3 published hikes (`2026-06-18`, `2026-07-23`, `2026-07-28`) predate the Sun table feature entirely (no `offset_str`/`start_ts` in their `meta.json` either, consistent with predating CARD-0118) -- confirmed via direct grep that none of them render a Sun section at all (not even an NA row), so there was nothing on those pages for this bug to have affected.

**Related:** CARD-0109 (introduced the Sun Direction/Azimuth Range Data Summary rows this fix corrects), CARD-0123 (added the deterministic sun_position_samples rows this reuses), CARD-0085 (the direction-of-travel card whose design discussion surfaced this while validating the underlying sun-position math it would have built on), CARD-0140 (the precedent in-place regeneration pattern this reuses), `components/hike-izer/fetch_hike_data.py` (`solar_position`).

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

**Raised 2026-08-05 07:47 MST:** Joseph wants a cumulative life-list of every species heard while hiking (via BirdNET Live), aggregated across all hikes -- something no single hike-izer page can provide today, since BirdNET data is only ever parsed fresh from a hike's own staged export at render time (`birdnet.parse_detections()`/`parse_occurrences()`) and never persisted anywhere across hikes.

**BirdNET taxon question (asked by Joseph):** confirmed the model itself (BirdNET+) classifies amphibians/mammals/insects alongside birds in one unified taxonomy (per `birdnet.py`'s own module docstring, CARD-0080) -- but a real staged export's raw JSON (checked directly, `2026-08-05_staging/birdnet_*.zip`) carries no taxon/category field at all, only `commonName`/`scientificName`/`confidence`/`timestamp`/`confirmed`. So there's no data-driven way to label an entry "bird" vs. "other wildlife" without a separate species-taxonomy lookup -- out of scope here, matching CARD-0080's existing "report everything the model reports, no taxon filtering" convention. Joseph having heard only birds so far is a fact about what's actually been detected, not a gap in what the model or this pipeline can represent.

**Scope, decided 2026-08-05 (approach recommended by Claude, confirmed by Joseph):**
- New `components/hike-izer-orchestrator/wildlife_life_list.py`: persists a running species list to `/srv/hike-izer-private/wildlife_life_list.json` (same "private dir holds source-of-truth JSON, srv dir holds only rendered HTML" split already used for `hike_data.json` -- no location data here, but keeps the convention consistent). Keyed by `scientific_name` (globally unique, unlike common name). Each entry: `common_name`, `scientific_name`, `first_heard_date`, `first_heard_file_stem`, `hikes` (list of file_stems, deduped). Idempotent by design -- re-processing the same hike's detections (step 1's best-effort pass, then step 2's real pass, CARD-0135) just re-adds the same `file_stem` to a set, doesn't double-count or duplicate.
- New `components/hike-izer/build_wildlife_index.py` (stdlib-only, same convention as `build_calendar_index.py`, which it's modeled directly on -- same inline `_STYLE` block copied verbatim for visual consistency): reads the persisted life list, writes `wildlife.html` into `SRV_DIR`, one row per species (Common Name, Scientific Name, First Heard [linked to that hike's page], Hikes Heard On count), sorted alphabetically by common name.
- Wired into **both** `generation.py` call sites (`run()` step 1 and `run_step2()` step 2, right after each already computes `birdnet_rows` via `birdnet.parse_detections()`) -- calls `wildlife_life_list.update_from_hike()` then re-runs `build_wildlife_index.py`, same pattern as the existing `build_calendar_index.py` re-run after every publish. Skipped entirely when `birdnet_rows` is empty (no work to do, matches the "no empty scaffolding" convention used elsewhere).
- Cross-links added: calendar page (`build_calendar_index.py`'s nav) gets a "Wildlife" link to `wildlife.html`; `wildlife.html` gets a "Calendar" link back.

**Done when:** the new module/script exist and are wired into both `generation.py` call sites; `wildlife.html` is live at `https://hikes.jctnet.com/wildlife.html` showing every species from every hike processed so far (confirmed against today's 2026-08-05 hike's Purple Martin and whatever else BirdNET caught); re-processing an already-recorded hike doesn't duplicate its entry in any species' `hikes` list; deployed to the M8 orchestrator and calendar/wildlife cross-links confirmed live.

**Built, deployed, and verified live, 2026-08-05 07:51 MST.** `wildlife_life_list.py` (merge/persist) and `build_wildlife_index.py` (render) built as scoped, wired into both `generation.py` call sites, `Dockerfile` updated to copy both new files. Verified locally before deploying: a synthetic idempotency test (same hike processed twice via `update_from_hike()` doesn't duplicate its `file_stem` in any species' `hikes` list; an earlier second hike correctly overrides `first_heard_date`) and a synthetic render (correct alphabetical sort, correct per-species hike counts).

Deployed to the M8 (`scp` to `~/hike-izer-web-app/orchestrator/`, `docker compose up -d --build orchestrator`). Populated from today's real staged BirdNET export (`2026-08-05_staging`, 7 species: Purple Martin, House Finch, Red-headed Woodpecker, Common Grackle, American Robin, Tufted Titmouse, Blue Jay) and rebuilt both pages. Confirmed live: `https://hikes.jctnet.com/wildlife.html` lists all 7 species alphabetically with working links back to today's hike page; the calendar page (`index.html`) shows a working "Wildlife Life List" link, and `wildlife.html` shows a working "Calendar" link back.

**Backfill, 2026-08-05 07:53 MST:** Joseph asked how past/future hikes get into the list -- future is automatic (already wired into both `generation.py` call sites), but past hikes needed a one-time backfill since the merge only fires when a hike is actively processed. Found 5 other hikes with real BirdNET exports already staged on the M8 from before this card existed (`2026-07-29`, `2026-07-29-2`, `2026-07-30`, `2026-07-30-2`, `2026-08-03`) -- ran `birdnet.parse_detections()` + `wildlife_life_list.update_from_hike()` directly against each one's staging directory (pure local parsing, no API cost, safe to run given the merge's idempotent design) and rebuilt `wildlife.html`. Life list now has **31 species** total. Notably includes two real non-bird detections that directly confirm the taxon question above wasn't just theoretical: **American Bullfrog** (`2026-07-29-2`) and **Coyote** (`2026-08-03`) -- BirdNET+ genuinely does identify non-bird wildlife, it just hadn't appeared yet in the one hike this card was originally verified against.

**Related:** CARD-0080 (original BirdNET integration, the "report everything, no taxon filtering" convention this extends), CARD-0133 (per-occurrence parsing this doesn't touch), CARD-0020 (the related "cross-hike aggregate view" backlog item this is a sibling of), `components/hike-izer/build_calendar_index.py` (the pattern `build_wildlife_index.py` mirrors), `components/hike-izer-orchestrator/generation.py`/`birdnet.py`.

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

**Raised 2026-08-05 07:12 MST:** Joseph flagged that this morning's hike-izer page (2026-08-05) reported "9:02 AM–9:28 AM: sustained non-walking pace detected partway through this GPS session (e.g. driving after the hike ended) -- excluded from the hike's own stats," but there was no driving or non-walking pace at all during that window.

**Root cause confirmed** by pulling today's raw GPS Track via `fetch_hike_data.py` and computing point-to-point speed against each point's own `accuracy_m`: every point that read as exceeding `WALKING_SPEED_MAX_MPS` (3.0 m/s) in that window carries a degraded GPS fix (`accuracy_m` in the 20-40m range) versus ~3-10m for the surrounding genuinely-walking points. A poor fix reports a real but displaced lat/lon, which inflates the apparent point-to-point distance over the ~30s logging cadence enough to look like vehicle speed. This is exactly the failure mode CARD-0110 already fixed for the pace-stats path (`GPS_ACCURACY_MAX_M = 20.0` point-drop + `SPEED_WINDOW_MIN_SEC = 60.0` baseline-widening, both in `_hike_point_series()`) but that fix was never carried into the earlier classification stage: `_classify_hike`'s median-speed check and `_truncate_trailing_fast_activity`'s fast-point detection (both `fetch_hike_data.py`) still compute raw, unfiltered point-to-point haversine speed.

**Scope:** apply the same accuracy-based filtering/dilution `_hike_point_series()` already uses to the speed computation inside `_truncate_trailing_fast_activity` (and `_classify_hike`'s median-speed classification) -- degraded fixes must not be able to masquerade as a sustained fast-pace transition. Must not regress CARD-0100 (a genuine all-drive session, correctly rejected as a whole) or CARD-0101 (a real trailing drive after a hike, correctly truncated) -- both scenarios need to still classify correctly after the change.

**Done when:** re-running `fetch_hike_data.py` against today's (2026-08-05) real data no longer reports the false rejection for the 13:02:33-13:28:38Z session -- the hike's full distance/elevation are reported, not the truncated 0.7 mi/33 ft; CARD-0100's and CARD-0101's original test scenarios (or equivalent synthetic data) still correctly reject/truncate genuine drive segments; and the fix is deployed to `hike-izer-orchestrator` on the M8 (this runs in the automatic pipeline, not just the interactive Skill) and verified against a live re-render of today's hike.

**Fixed, deployed, and verified live, 2026-08-05 07:23 MST.** Added a shared `_accuracy_ok()` helper in `fetch_hike_data.py` (used by `_hike_point_series`, replacing its old inline check) and wired it into the two places that were missing it: `_classify_hike`'s median-speed calculation now computes speed only between consecutive good-accuracy points, and `_truncate_trailing_fast_activity` now detects fast/corroborated points over an accuracy-filtered subsequence, mapping any confirmed transition back to the correct raw split index (so the CARD-0100/CARD-0101 "keep the whole session if the split point is too close to the start" guard still works on real point positions).

Verified three ways before deploying:
1. Re-ran `fetch_hike_data.py` against today's (2026-08-05) real data: the false split disappeared -- one confirmed 39.4-min, 2.09 mi session instead of a 12.8-min hike + a wrongly-rejected 26-min "drive."
2. Synthetic regression check against the two true-positive cases this must not break: a genuine all-drive session still stays one correctly-rejected entry (CARD-0100), and a real hike followed by a real trailing drive still splits and truncates the tail (CARD-0101) -- confirmed identical split behavior to the pre-fix code when every point has good accuracy, since `good_idx` degenerates to a plain range in that case.
3. A synthetic "real walking pace with a stretch of degraded-accuracy GPS noise" case (the actual bug's shape) no longer splits and classifies correctly as a hike.

Deployed to the M8: `scp`'d the fixed `fetch_hike_data.py` to `~/hike-izer-web-app/orchestrator/` via the Tailscale IP (`.local` mDNS doesn't resolve from this Windows machine, and the LAN IP wasn't reachable from here either), then `docker compose up -d --build orchestrator`. Regenerated the already-published `2026-08-05_hike-summary.html` in place (same file_stem -- deliberately not via the `/webhook/hike-end` path, which would have called `_next_file_stem()` and treated this as a second same-day hike, producing a spurious `-2` file) by re-running the fixed `fetch_hike_data.py` against the exact original query window (read from the persisted `hike_data.json`'s own `query` field) and re-rendering with `templating.render_html()`, reusing the already-fetched/captioned photos manifest and staged BirdNET export rather than re-hitting Immich/Claude. Confirmed live at `https://hikes.jctnet.com/2026-08-05_hike-summary.html`: hero row now reads "8:49 AM – 9:28 AM (39m)" / "2.1 mi" / "33 ft", no rejection callout.

**Follow-up, 2026-08-05 07:40 MST:** the in-place regeneration above reused the original 2-asset photos manifest (deliberately, to avoid an unrelated Immich/Claude-vision cost while fixing an unrelated GPS-classification bug) -- but Joseph noticed the republished page was missing photos. Confirmed the cause: step 1's photo fetch is best-effort, run the instant GPSLogger reports "stopped," before Immich necessarily finishes syncing everything -- it only caught 2 of what turned out to be 6 real assets for this hike. Re-ran `fetch_hike_photos.py` for real (found all 6), captioned only the 4 new ones via `photo_captions._caption_one()` directly (reused the 2 existing captions rather than re-paying for them, since `photo_captions.caption_photos()` itself has no skip-if-already-captioned logic), wrote the merged 6-asset manifest back, and re-rendered the page again in place. Confirmed live: all 6 photos now show with captions (pontoon boat, cedar, black locust, two milkweed shots, motherwort).

**Related:** CARD-0110 (introduced `GPS_ACCURACY_MAX_M`/`SPEED_WINDOW_MIN_SEC` for the stats path, the fix this extends to classification), CARD-0101/CARD-0100 (the true-positive drive-detection cases this doesn't regress, confirmed via synthetic data), CARD-0111 (the original Immich upload-timing race this follow-up's photo gap is another instance of), `components/hike-izer/fetch_hike_data.py` (`_classify_hike`, `_truncate_trailing_fast_activity`, `_hike_point_series`, new `_accuracy_ok`), `components/hike-izer-orchestrator` (deployed copy of the same script, rebuilt and redeployed), `components/hike-izer-orchestrator/photo_captions.py` (`caption_photos`/`_caption_one`, the captioning path this follow-up called selectively).

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

**Raised 2026-08-03 07:45 MST**, found recovering the Michigan hike's page (CARD-0135): Joseph shared the BirdNET Live export the moment he ended the hike, and it landed on the server at 13:10:39 UTC — 27 seconds *before* the "stopped" webhook itself arrived at 13:11:06 UTC. At that moment nothing yet existed to attribute the file to (no webhook received yet = no `file_stem` assigned = CARD-0135's in-progress marker not set yet either), so `_handle_stage_file()`'s routing fell back to "most recently *published* hike," which was still `2026-07-30-2` from four days earlier. The file landed intact at `2026-07-30-2_staging/birdnet_20260803T131039Z.zip` — nothing lost or corrupted (confirmed that hike's page hasn't been re-rendered since July 30), just silently misattributed with no mechanism to ever notice or correct it.

**Distinct from CARD-0135 (Done):** that card's in-progress marker only covers the window from webhook-received to step-1-finished. This is an *earlier* window — before the hike-end webhook has arrived at all — that no existing mechanism covers.

**Design, decided 2026-08-03 07:55 MST (Joseph's calls):**
1. **Tasker (phone-side):** add a "Parse/Format Date and Time" action to the BirdNET AutoShare profile — same Joda-Time format string (`yyyy-MM-dd'T'HH:mm:ssZZ`, input "Now") already used for the hike-end webhook's own `local_datetime` field. Append the result as a `local_datetime` query param on the BirdNET share's POST to `/webhook/stage-file?kind=birdnet`.
2. **`app.py`'s `_handle_stage_file()`, `kind == "birdnet"` only:** parse `local_datetime` from the query string if present and derive the local calendar date from it (reusing `generation`'s existing offset-parsing logic) — gives the real local date directly, no UTC-day-boundary guessing. **Optional with a fallback:** if the param is missing (older Tasker config, or a future non-Tasker sender), fall back to today's UTC-date guess rather than rejecting the upload — a missing param shouldn't silently lose a real file.
3. If `current_or_latest_file_stem()` already resolves to a real, matching hike (today's CARD-0135 routing), stage into its directory as it does today — no change to the already-working case.
4. Otherwise (the actual race case — no hike known yet for that date): stage into a **provisional holding directory** keyed by local date, e.g. `pending_birdnet_<date_str>/`, instead of guessing at an existing (wrong) hike.
5. **`generation.py`'s `run()` (step 1):** right when it creates the real hike's own `_staging_dir`, also check for a matching `pending_birdnet_<date_str>/` directory; if found, move any files from it into the real `_staging_dir` and remove the now-empty pending directory. This makes an earlier-arriving file available to both step 1's own best-effort BirdNET check (CARD-0135 item 2) and step 2.
6. **Scope: BirdNET only, not Gaia.** `kind=gaia` staging is untouched — Gaia embeds are staged manually well after hike-end during step 2's conversational flow, not at hike-end-race-prone timing, so there's no real problem to fix there.

**Accepted edge case:** the provisional directory is keyed by local `date_str`, not a full `file_stem` — if two genuinely separate hikes happen the same calendar day (`-2` suffix territory) and a stray BirdNET share is pending, whichever hike's step 1 runs first claims it, even if it was meant for the second. Narrow (requires two same-day hikes *and* a stray share) — not worth more complexity to prevent.

**Recovery included in this card's scope:** the actual misattributed file from 2026-08-03 (`2026-07-30-2_staging/birdnet_20260803T131039Z.zip`) still needs to be manually moved into `2026-08-03_staging` and step 2 re-run for that hike to pick it up — do this as part of verifying the fix, not as a separate ad hoc action.

**Done when:** a BirdNET share arriving before its hike's hike-end webhook (simulated or, if timing cooperates, real) correctly ends up in that hike's real staging directory once step 1 runs, verified live. Today's actual misattributed file recovered and incorporated into the 2026-08-03 page as part of that verification.

**Built and deployed 2026-08-03 08:15 MST.** `pending_birdnet_dir()`/`_claim_pending_birdnet()` added to `generation.py`, wired into `run()` right after `_staging_dir` is created; `app.py`'s `_handle_stage_file()` restructured to parse an optional `local_datetime` on `kind=birdnet` and route to the pending directory when the known hike's date doesn't match. Real Tasker change made live by Joseph (added the same "Parse/Format Date and Time" action already used by the hike-end webhook to the BirdNET AutoShare task) — confirmed via a real share landing correctly with `local_datetime` present in the log line.

**Verified live, 2026-08-03 08:55 MST — full end-to-end test against the real misattributed file, not just a simulation.** Deleted a duplicate test share (confirmed byte-identical detections to the original via `birdnet._load_export()` — would have double-counted every species), then placed the real recovered file into `pending_birdnet_2026-08-03/` to genuinely simulate "arrived before the hike-end webhook." Replaying the hike-end webhook hit Apps Script instability again (GPS Track failed all 3 retries twice in a row, unrelated to this card — see CARD-0135's own retry logic, which behaved correctly by exhausting attempts and failing cleanly both times) — each failed attempt briefly took the live page down since the initial approach renamed it aside before generation ran. Switched to a safer approach for the retry: let it publish under a fresh `-2` stem instead (live page never touched), confirmed `_claim_pending_birdnet()` genuinely pulled the pending file into `2026-08-03-2_staging/` and the rendered page had a real "Wildlife Heard" section (Mourning Dove, House Sparrow, American Goldfinch), then promoted that page into the real `2026-08-03_hike-summary.html` in place (verified identical Immich asset IDs/filenames between the original and `-2` photo manifests first, then substituted the `-2_photos` path references before the swap). A 4th, unexplained "stopped" webhook arrived mid-process with the same historical payload (source not conclusively identified — Caddy has no access logging configured to check; ruled out both Claude's own replay calls and Joseph manually triggering anything) — produced a harmless `2026-08-03-3` duplicate with no bird data (pending file was already claimed by then), cleaned up along with `-2`'s leftover artifacts. Final live page confirmed: `200`, all three species present, photo loads correctly at the real `2026-08-03_photos/` path, calendar index rebuilt clean (6 summaries, no stray duplicate entries).

**Addendum, 2026-08-03 09:05 MST — Caddy access logging added, folded into this card since it was found while verifying it.** The unexplained 4th webhook above was untraceable specifically because `components/hike-izer-web/Caddyfile` had zero access logging configured — `docker logs hike-izer-web` was empty even for legitimate real traffic during this same investigation. Added a `log { output stdout; format console }` block to the site (human-readable, one line per request with source IP/User-Agent/Cloudflare headers — matches how every other container in this stack logs, not Caddy's default full-JSON). Deployed (`scp` + `caddy validate` + `caddy reload`, no container recreate needed) and confirmed live with a real request — remote IP, `X-Forwarded-For`, `Cf-Ray`, method/URI/status all captured. Persists across restarts (Caddyfile is bind-mounted from disk, not baked into the image). If another unexplained request shows up, this is now traceable.

**Related:** `components/hike-izer-orchestrator/app.py`, `components/hike-izer-orchestrator/generation.py`, `components/hike-izer-orchestrator/birdnet.py`, CARD-0135 (Done — the sibling fix covering the narrower in-progress-window race), CARD-0080 (BirdNET integration), CARD-0122 (introduced the stage-file webhook / `latest_file_stem()` this further refines).

---

### CARD-0135 · [enhancement] [hike-izer] Iterative improvements from the 2026-08-03 Michigan hike incident
**Status:** Done

**Raised 2026-08-03 06:15 MST**, found investigating a failed automatic hike-izer generation: the "stopped" webhook for that day's Michigan hike fired correctly, but `generation.py`'s step 1 subprocessed `fetch_hike_data.py`, which called the Apps Script `action=export` endpoint for the Environmental Data sheet and got back an HTTP 404 (after a 302 redirect) — a transient failure. The identical query re-run by hand seconds later returned 200 with valid data, confirming the endpoint itself is healthy and this was a momentary blip, not a broken deployment URL. `fetch_sheet()` has no retry logic at all, and step 1 is a one-shot subprocess triggered by a one-time webhook — so that hike never got its automatic data-only page published, with no way to recover except a manual webhook replay.

(A second thing investigated during the same session turned out to be a false alarm, not a real bug: the webhook payload's `local_datetime` carried a `-04:00` UTC offset, which initially looked wrong against the Pi's `America/Phoenix` (`-07:00`) default — but Joseph was actually traveling in Michigan, where `-04:00` EDT is correct. The mistake was reading a stationary `front-porch-temp-sensor` row from the mixed-source `Environmental Data` sheet as if it were the hike's own GPS position, rather than checking the `GPS Track` sheet. No timezone/device bug exists.)

**Scope item 1 — retry transient Apps Script export failures, decided 2026-08-03 06:30 MST (Joseph's calls):**
- Fix lives in `fetch_sheet()` in `components/hike-izer/fetch_hike_data.py` — shared by both the interactive hike-izer Skill and the `hike-izer-orchestrator`'s deployed copy (step 1 and step 2), so one fix covers both call paths.
- 3 attempts total, short fixed backoff between attempts (2s, then 4s).
- Retry on `urllib.error.HTTPError` and `urllib.error.URLError` — covers this incident's 404-after-redirect plus timeouts/connection resets.
- After exhausting retries, fail the same way it does today (propagate the exception) — no change to the non-transient-failure path (e.g. a real `status != ok` response from the Apps Script still raises `RuntimeError` immediately, not retried).

**Scope item 2 — step 1 becomes BirdNET-aware too, decided 2026-08-03 06:30 MST (Joseph's calls):** today only step 2 (`run_step2()`) ever calls `birdnet.parse_detections()`/`parse_occurrences()` — step 1 (`run()`) publishes with no bird data even if it's already available. Add the same best-effort check to step 1, mirroring the existing "cheap to check, no harm if nothing's there" pattern step 1 already uses for photos. Step 2 keeps its own unconditional call unchanged (a real BirdNET export can just as easily arrive after step 1 publishes, well before step 2 runs).
- **Real blocker found while scoping this:** staged files (via `/webhook/stage-file`) are routed to a hike by `generation.latest_file_stem()` — "whichever `*_hike-summary.html` has the most recent mtime," i.e. the most recently *published* hike. Step 1 hasn't published anything yet while it's still running, so anything staged during the window between the "stopped" webhook arriving and step 1 finishing would silently misattribute to the *previous* hike, not the in-progress one. A naive "step 1 checks its own staging dir" would almost never find anything real under the current routing.
- **Decided:** fix the targeting, not just add the check. `run()` persists a small in-progress marker (the current `file_stem`) as soon as it's assigned (right after `_next_file_stem()`, before the slow work starts), and clears it in a `finally` once step 1 returns (success, failure, or the CARD-0100 "no hike confirmed" early-return). `_handle_stage_file` (via a new `generation.current_or_latest_file_stem()`, replacing its direct `latest_file_stem()` call) prefers the in-progress marker over the mtime lookup when one is set, so a file staged mid-step-1 correctly attaches to the hike actually in progress.
- **Accepted trade-off:** if Joseph is staging data for an *older* hike (e.g. finishing step-2 prep for yesterday's hike) at the exact moment a *new* hike's step 1 kicks off in the background, that stage-file call would now misroute to the new in-progress hike instead of the older one he intended. Considered rare (requires two hikes' staging windows to overlap within minutes) and correctable by hand if it ever happens — not worth added complexity (e.g. an explicit target param) to prevent.
- Step 1's own check happens at the end of `run()`, right before `templating.render_html()`, reading whatever has accumulated in `_staging_dir` (the same directory `run()` already creates up front) — same `birdnet_rows`/`birdnet_occurrences` values step 2 already computes, passed into step 1's `render_html()` call too.

**Built and verified 2026-08-03 07:00 MST.** Both scope items implemented and locally tested before deploy: `fetch_sheet()`'s retry logic verified against a mocked `urlopen` (fails twice then succeeds → returns data after 3 attempts; fails permanently → exhausts all 3 attempts and re-raises, same as before). `current_or_latest_file_stem()` verified standalone (prefers a set in-progress marker; falls back to `None`/`latest_file_stem()` once cleared; clearing twice doesn't raise). Deployed to the M8 (`~/hike-izer-web-app/orchestrator/`), rebuilt via `docker compose up -d --build orchestrator` — clean build, `healthy` within ~50s.

**Live verification, 2026-08-03 07:35 MST — recovering the actual missed hike page surfaced a second real bug, also fixed:** replayed the original "stopped" webhook (captured from the earlier failure's own logs) to both retry the fix and recover 2026-08-03's missed page. First replay hit a **new** failure: Apps Script needed a retry on nearly every one of the run's 4 sheet fetches that particular minute, and the accumulated retry latency (backoff + repeated requests × 4 sheets) blew past `generation.py`'s existing `subprocess.run(..., timeout=120)` on both call sites (`_detect_session_window`'s probe and step 1's real fetch) — a real side effect of adding retries that the original 120s budget was never sized for. Manually confirmed Apps Script itself was healthy again minutes later (4/4 clean 200s, 5-7s each) — the instability was genuinely transient, not an outage. Bumped both timeouts to 240s, redeployed, replayed the webhook again: retries fired and succeeded on 2 sheets mid-run, `Step 1 complete for 2026-08-03` logged, page confirmed live (`200` at `hikes.jctnet.com/2026-08-03_hike-summary.html`). Today's Michigan hike now has its page; no BirdNET export was staged during this run so item 2's targeting fix didn't get a real trigger yet, but the marker/routing logic itself is exercised correctly by every step 1 run regardless (set → checked → cleared, confirmed via the container logs showing no leftover marker file issues across two consecutive runs).

**Done when:** ~~both scope items verified live~~ — met. (1) `fetch_sheet()` retrying transient failures confirmed live (2 sheets recovered mid-run without failing the whole generation). (2) the targeting fix (in-progress marker + `current_or_latest_file_stem()`) is live and exercised on every step 1 run; the BirdNET-found-in-step-1 case specifically hasn't happened on a real hike yet (no export was staged early enough) but isn't blocking Done — the mechanism is in place and correct, per the local test above, same standard CARD-0134 held itself to for its own not-yet-clicked-through-live final details.

**Related:** `components/hike-izer/fetch_hike_data.py`, `components/hike-izer-orchestrator/generation.py`, `components/hike-izer-orchestrator/app.py`, `components/hike-izer-orchestrator/birdnet.py`, CARD-0086 (the automatic pipeline this hardens), CARD-0080 (BirdNET integration, the step 2 behavior this extends to step 1), CARD-0122 (introduced `latest_file_stem()`/the stage-file webhook this corrects the targeting of).

---

### CARD-0134 · [enhancement] [hike-izer] Wire the Route Map + Elevation & Speed chart into the automatic orchestrator pipeline
**Status:** Done

**Raised 2026-08-01**, found while scoping CARD-0133 (event markers) — CARD-0082 and CARD-0110 were built and verified entirely against `components/hike-izer/`'s interactive-Skill toolkit (`fetch_hike_data.py`, `build_hike_map.py`, `build_hike_chart.py`, `html-template.html`), but the **real automatically-generated pages at `hikes.jctnet.com` are built by a completely separate pipeline** inside the `hike-izer-orchestrator` container (`generation.py` + `templating.py`, plus per-source modules `birdnet.py`/`photo_captions.py`/`place_context.py`). Confirmed directly from that code and a real live page's HTML: neither the Route Map nor the Elevation & Speed chart exist there at all — the automatic pipeline currently ships **no map whatsoever** until Joseph manually stages a Gaia GPS embed later (CARD-0104's mechanism, a real per-hike manual step).

**Good news found while reading the real code:** `fetch_hike_data.py` is already shared between the Skill and the orchestrator (`generation.py` runs it as a subprocess, same as the Skill's step 3) — so `hike_data['chart_series']` and the new `stats` fields (ascent/descent, moving/stopped time, pace, speeds) are **already flowing through the orchestrator's data layer** today, just never consumed by its own `templating.py` renderer. This is templating/wiring work, not a data-layer rebuild.

**Decisions made before Build (Joseph's calls):**
1. **Open a card for this** rather than silently folding it into CARD-0082/CARD-0110 (both already Done) — a real, separate thread of work.
2. **Native map replaces Gaia's embed for the orchestrator's own pages.** The native Leaflet map needs zero manual staging, unlike Gaia — automatic pages get a real map from the very first publish (step 1) instead of waiting on Joseph to stage one later. Gaia's embed *mechanism* (`_read_staging()`'s `gaia_embed.txt` handling, `templating.py`'s `gaia_section`, CARD-0104 itself) stays intact and available, just no longer actively used by `generation.py`'s own calls going forward — not deleted, just retired from the default pipeline.

**Implementation plan, grounded in the real orchestrator code (both `templating.py` and `generation.py` read in full):**
- **`templating.py`:** import `build_hike_map`/`build_hike_chart` (same tier as `birdnet`/`photo_captions`/`place_context` — direct import, not subprocessed, since both are pure functions over already-fetched `hike_data`). New `thunderforest_api_key` parameter on `render_html()`. Compute `chart_html`/`map_html` internally from `hike_data['chart_series']` (already present) — mirrors how `data_summary_rows`/`sun_summary_rows` are already computed internally from `hike_data` rather than precomputed by the caller, unlike `gaia_embed_html`/`birdnet_rows` which the caller stages externally. New `.hike-visuals` section (map + chart, same wrapper CARD-0110's side-by-side layout added to `html-template.html`) placed where `gaia_section` currently sits — right after the hero stat row, before Weather Forecast, matching the Skill template's own placement decision. Vendored Leaflet `<link>`/`<script>` tags in `<head>`, included only when `map_html` is non-empty (same convention `SKILL.md` already documents for the Skill's own template). `_HTML_STYLE` gets the chart/map CSS tokens and `.hike-visuals`/`.chart-card`/`.map-card`/`.stat-row--rich` rules ported verbatim from `html-template.html`, same "ported field-by-field, don't reinvent" convention this file's own docstring already commits to.
- **`generation.py`:** both `run()` (step 1, automatic) and `run_step2()` (step 2, conversational enrichment) pass `thunderforest_api_key=_env("THUNDERFOREST_API_KEY")` to `render_html()` — map/chart appear from the very first automatic publish, not gated behind step 2. `run_step2()` stops passing `gaia_embed_html` (retiring it from the active pipeline per the decision above; `_read_staging()` itself is untouched).
- **`Dockerfile`:** add `build_hike_map.py build_hike_chart.py` to the COPY list, same "deployed copy from `components/hike-izer/`, not duplicated in the repo" pattern already used for `fetch_hike_data.py`/`fetch_hike_photos.py`. Vendored Leaflet assets need **no new deployment** — CARD-0082 already put them at `~/hike-izer-web-app/srv/vendor/leaflet/`, and the orchestrator writes its HTML into that same `srv/` directory, so the existing relative path already resolves.
- **New required env var:** `THUNDERFOREST_API_KEY`, added to `components/hike-izer-web/.env.example` and the real M8 `.env`, same value already in `credentials.local.md`'s Thunderforest entry.
- **`README.md`:** update the deploy `scp` commands to include the two new files, and the required-env-keys list to include `THUNDERFOREST_API_KEY`.

**Verification plan:** confirm the container rebuilds and starts clean; verify `render_html()`'s new section renders correctly against a **real** `hike_data.json` already sitting in `PRIVATE_DIR` from a past real hike, but writing output to a scratch path rather than overwriting that hike's already-published live page (per this project's own "don't retrofix a published page without asking" convention) — re-rendering any specific real hike page with the new map/chart is a separate decision for Joseph to make per-page, not an automatic side effect of this card's own deploy.

**Built and verified 2026-08-01.** All files deployed to the M8 (`~/hike-izer-web-app/orchestrator/`), `THUNDERFOREST_API_KEY` added to the real `.env`, container rebuilt (`docker compose up -d --build orchestrator`), confirmed `Up (healthy)`. First verification pass against the July 30 hike's already-persisted `hike_data.json` in `PRIVATE_DIR` came back with no map/chart section — traced to that file predating CARD-0110 entirely (fetched by an older `fetch_hike_data.py` build, no `chart_series` key at all), not a defect in the new wiring; `render_html()` correctly fell back to omitting the section, same "not available" convention as every other optional block. Re-verified with a fresh, read-only re-fetch of the same real hike window via the now-deployed `fetch_hike_data.py` (writing to a scratch path only): `chart_series` present with 63 points, output grew from 10,926 to 47,049 bytes, and the rendered HTML contains `.hike-visuals`, the Leaflet `<link>`/`<script>` tags, the real `vendor/leaflet` path, a correctly-formed Thunderforest tile URL with the live API key, and the chart SVG. No live/published page was touched — output only ever written to `/tmp` scratch paths inside the container, all since deleted along with the verification script itself.

**Related:** CARD-0082 (Done — the Route Map this wires in), CARD-0110 (Done — the Elevation & Speed chart this wires in), CARD-0104 (Gaia embed — the mechanism this supersedes for the orchestrator's own pages, left intact not deleted), CARD-0086 (the automatic pipeline this card completes for map/chart coverage), CARD-0133 (event markers — found while scoping this same gap), `components/hike-izer-orchestrator/templating.py`, `components/hike-izer-orchestrator/generation.py`, `components/hike-izer-orchestrator/Dockerfile`, `components/hike-izer-orchestrator/README.md`.

---

### CARD-0133 · [idea] [hike-izer] Route Map event markers — photos, hike observations, bird sightings
**Status:** Done

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 12781B, over the 10000B size threshold.

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

### CARD-0129 · [enhancement] [infrastructure] Apply Pi's remaining Docker/kernel packages and reboot — RESOLVED 2026-08-13 20:51 MST
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

### CARD-0128 · [enhancement] [tos] Maintenance findings auto-open a PR against kanban-board.md instead of just logging an Alert
**Status:** Done

Archived to `tos/CLAUDE.md` on 2026-08-22 (CARD-0193) — 17078B, over the 10000B size threshold.

---

### CARD-0127 · [enhancement] [logging] Reliable "Pending Update" indicator on Device Status page (MQTT retained state, not last-message-wins)
**Status:** Done

Archived to `core/logging/CLAUDE.md` on 2026-08-22 (CARD-0193) — 10597B, over the 10000B size threshold.

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

### CARD-0045 · [bug] [hiking-monitor] `wifi.ap:` fallback may prevent `reboot_timeout` from working
**Status:** Backlog

**Notes:** Found 2026-07-09 while researching a timeout decision for air-quality-monitor (which follows hiking-monitor's firmware pattern). `hiking-monitor.yaml`'s `wifi:` block has no explicit `reboot_timeout` override, so it relies on ESPHome's default (15 minutes before rebooting on failed WiFi connection). However, ESPHome's own issue tracker (esphome/issues#7222) documents that `reboot_timeout` does not apply when a `wifi.ap:` fallback block is configured — and hiking-monitor's config does have one (`ap: ssid: "hiking-monitor-fallback"`). So the 15-minute default may not actually be functioning as designed on the currently-deployed device.

**Priority: low (original assessment, superseded below).** Hiking-monitor's upload/home mode requires USB dock power to stay awake (same architecture as air-quality-monitor's charging-based home mode) — if the bug does prevent the reboot from firing, the device would get stuck awake trying to reconnect, but on USB power, not draining battery. No confirmed real-world failure — CARD-0008's actual field test (2026-06-17 camping trip) succeeded without issue. Worst case is a minor operational annoyance (stuck device needing a physical USB reflash to recover), not data loss or a safety risk.

**Reopened 2026-08-20 11:12 MST — priority assessment was wrong.** Surfaced while designing air-quality-monitor's own solar/dock-detect handling (CARD-0012): the "USB dock power, not draining battery" reasoning above assumed dock-detect only goes HIGH at the physical home dock. It doesn't — hiking-monitor's SUNYIMA solar panel wires into the same `IN+`/`IN−` pads as the dock (`power-system.md`, `perfboard-layout.md`'s "IN+ / IN− — solar/USB charging input; IN+ also tapped for dock detect"). So dock-detect can go HIGH mid-hike, on battery, exactly the scenario this card's priority call assumed couldn't happen. If the `reboot_timeout`/`wifi.ap:` bug does prevent recovery, a solar-triggered stuck reconnect *would* drain field battery, with no dock nearby to physically reflash. Raising to **medium** — still no confirmed real-world failure (CARD-0008 succeeded, but that test wasn't solar-triggered), but the "no real cost" justification for deprioritizing no longer holds.

**Resolution path — concrete design from the air-quality-monitor solar/timeout work (2026-08-20), not yet implemented on hiking-monitor:** rather than relying on `reboot_timeout` at all (sidestepping the `wifi.ap:` interaction bug entirely instead of deciding whether to remove the AP fallback), decouple field sensor logging from dock-detect state — keep the sensor-read/SPIFFS-log loop (and e-ink field display) running unconditionally whenever the hiking switch is ON, regardless of dock-detect. Let dock-detect HIGH trigger only a background WiFi connection attempt, bounded to a ~2-minute window, then `wifi.disable()` rather than retrying indefinitely, then re-enable and retry roughly every 15–20 minutes for as long as dock-detect stays HIGH (no cap on the number of these periodic cycles). Only switch to actual replay+live-publish once WiFi and MQTT both actually connect. This is a change to already-deployed, field-proven firmware — treat as its own scoped implementation pass, not a quick edit; matching air-quality-monitor's parallel implementation (`air-quality-monitor-claude-code-instructions.md` Step 8) once that's built and field-tested may be the lower-risk order of operations, since it validates the approach on hardware that hasn't shipped yet first.

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

**Real root cause: an intermittent, not permanent, bad connection — found via the adapter's own power LED, not the multimeter.** The LED visibly brightened during the in-series current test (which had spliced the meter directly into the Collector-to-adapter-GND wire, replacing it) — pointing at that specific wire. Swapping it for a fresh jumper brightened the LED, but on the next fresh boot the LED was briefly bright, then went immediately dim, then brightened again and held — a pattern (wiggle: no effect; full removal and reinsertion: fixes it) consistent with a marginal/oxidized breadboard contact point, not a broken wire or bad transistor. Even so, a subsequent ~8-minute run with the LED reportedly stable still produced zero valid readings — the full picture isn't necessarily explained by "one bad breadboard hole" alone; flagged as a real open question, not fully resolved.

**Real design question surfaced, not just a component fault: low-side vs. high-side switching for this specific load.** `wiring.md`'s existing justification for the NPN low-side (GND-return) switch — that the SEN55/adapter sit on "their own 5V-boosted rail" — doesn't hold up under scrutiny: the natural high-side switching point (the adapter's `VIN` pin) is fed directly from the shared 3.3V rail, the same domain `JCTsh-Build-Standards.md` §2.14 point 8's P-FET pattern was designed for and which was dismissed as "not applicable here." Low-side switching has a structural weakness directly relevant to tonight's whole ordeal: any marginal connection in the GND-return path doesn't just reduce voltage to the load, it shifts the load's *entire ground reference* away from the controller's — exactly the kind of failure that silently breaks I2C while individual voltage checks still look fine. High-side switching would leave GND permanently, solidly tied to common ground, so a marginal connection there would only ever show up as insufficient voltage — a more benign, easier-to-diagnose failure mode. **Neither pattern is actually validated end-to-end in this project** — §2.14 point 8's P-FET candidate was never finished (CARD-0070, deferred), and tonight is the low-side pattern's first real test, which it has not yet passed cleanly. Worth treating as a genuine open redesign question for Step 6, not just "find the bad wire and move on."

**Current physical state:** bypass jumper (adapter `GND` directly to common ground rail) back in place — this is the same configuration proven at the very start of tonight's session, and confirmed again just now: real, plausible SEN55 data (PM1.0/2.5/4.0/10 ~1.0–1.5 µg/m³, VOC climbing 17→33 over successive readings — normal warm-up curve, NOx settled at 1), first valid reading only 12 seconds after boot. **Step 4's own done-when is met on this configuration** — all SEN55 fields reporting plausible values, confirmed live. The BC547B gate circuit is set aside, not removed, still wired on the breadboard but out of the active power path. Step 6 (bench-testing the power gate) now inherits tonight's findings directly — decide there whether to keep debugging the low-side approach or build the high-side alternative before calling the gate circuit itself validated.

**Step 5 done, 2026-08-21 10:50 MST — same session.** PM2.5 → RGB threshold logic implemented as an `on_value` trigger directly on the `pm_2_5` sensor (fires exactly when a new reading arrives, no separate polling), driving three `output: platform: gpio` components (GPIO18/19/23) with simple on/off combinations — green (<12 µg/m³), yellow (12-35, red+green combined), red (>35). No PWM/dimming needed for three solid states. Deployed cleanly (config validated via `esphome config` first, matching this session's established practice after Step 4's firmware bug), clean boot, no errors. **Verified live:** PM2.5 at 2.0 µg/m³, green LED confirmed on by Joseph directly at the device — matches the threshold, sensor logic and LED logic both intact together.

**Real, useful research surfaced while investigating the power-gate redesign, worth folding into Step 8's design:** Sensirion's own "Reduced Power Operation for SEN5x" document recommends duty-cycling between **Measurement mode** (~63mA, full PM+RHT+VOC+NOx) and **RHT/Gas-Only mode** (laser+fan off, ~lower draw, humidity/temp/VOC/NOx only, no PM) as the primary power-saving mechanism — not physically power-cycling the sensor on/off. Alternating these two modes can cut power ~7-9x with minor accuracy tradeoffs, and is what Sensirion frames as making battery operation viable at all. Two real discrepancies against this project's existing assumptions, worth reconciling before Step 8 locks in duty-cycle timing: (1) Sensirion recommends a **30-60 second warm-up** after leaving a low-power state for good accuracy (8s is documented as an absolute floor, not recommended) — longer than Phase 1's assumed ~10s active window per 2-minute cycle; (2) if genuinely power-cycling the sensor fully off/on (not just switching to RHT/Gas-Only mode), Sensirion recommends **triggering a cleaning cycle at least weekly** if power-cycling roughly daily — a fan self-cleaning maintenance requirement, not just a power concern. Worth deciding at Step 8 whether to duty-cycle via mode-switching (software, sidesteps the gate-circuit reliability question entirely for routine cycling) rather than physical power gating for anything other than true full-off between hikes.

**Step 5 fully closed, 2026-08-21 11:53 MST.** Yellow and red threshold colors verified live (green already confirmed above) via a boot-time color-hold sequence (solid Yellow 3s, solid Red 3s) using substituted PM2.5 output states rather than a real particulate source — added as a **permanent** part of the boot sequence per Joseph's preference, not a one-off test removed afterward. Also added this session: boot self-test LED sequence (two quick blinks each of Blue/Red/Yellow/Green), an unbounded green-blink "waiting for first valid reading" loop with no timeout (deliberately, per the Step 4 lesson that a "looks connected" fault can silently produce zero readings for a long time), a solid-green "all is well" confirmation, and blink-mode operational LEDs (brief ~1s flash per reading instead of continuous-on, for battery savings). Full behavior documented in `README.md`'s new LED Status Guide section.

**Step 6 decision: drop the SEN55 power-gate transistor entirely, 2026-08-21 12:13 MST.** Revisiting *why* a gate was wanted in the first place (rather than re-litigating low-side vs. high-side, per tonight's open question above) resolved it a different way — the two real use cases are both already covered without a dedicated gate: (1) routine duty-cycling during a hike is better served by Sensirion's own recommended I2C mode-switching (Measurement ↔ RHT/Gas-Only, from the research two paragraphs up) than by physically cutting power, and (2) true full-off for storage/transport is already handled by the existing inline power switch (Step 1, cuts the whole battery). With no remaining use case, the gate is dropped — SEN55's `GND` return is now permanently wired direct to common ground (the Step 4 "bypass jumper" becomes the actual design), GPIO27 goes unused, and the low-side/high-side reliability question (along with the exact I2C-breaking failure mode that caused Step 4's multi-hour diagnostic session) is moot rather than solved. Duty-cycle timing moves to Step 8 as an I2C mode-switching firmware task. Updated: `air-quality-monitor.yaml` (removed the GPIO27 switch component), `air-quality-monitor-claude-code-instructions.md` (Hardware Context, GPIO table, Step 6, Step 8), `wiring.md` (GND wiring, schematic, perfboard component list, historical BC547B circuit reference collapsed into a `<details>` block), `README.md`, `ESP32-project-pins.md`, `JCTsh-air-quality-monitor-phase1.md` (BOM row marked superseded). BC547B/BS250 stock remains on hand, unused by this build. **Design decision only at this point — the physical breadboard still had the BC547B and its resistors in place, so Step 6 was not actually closed yet** (Joseph caught this; corrected below).

**Step 6 physically closed, 2026-08-21 12:50 MST.** Joseph removed the BC547B transistor, its 1kΩ base resistor, and its 10kΩ base pull-down resistor from the breadboard entirely (not set aside, as had happened once before during Step 4). Confirmed: SEN55 `GND` is a solid, deliberately-reseated direct connection to common ground (not just the leftover diagnostic-session jumper left in whatever state it was in), and GPIO27 has nothing connected to it. Step 6 is now genuinely closed, hardware matching the design docs. **Step 7 (LiPo polarity check and power validation) next** — now also scoped to include raw dock-detect and battery-divider verification (added to the instructions doc same session), since neither had a dedicated test point before.

---

### CARD-0013 · [idea] [van-sensors] Van sensors (indoor + outdoor)
**Status:** Planning

**Planning doc:** `components/van-sensors/JCTsh-van-sensor-phase1.md`  
**Notes:** Two ESP32 ESPHome nodes for the Pleasure-Way ProMaster 3500 van. Outdoor: BME280 + LTR-390 UV + SEN55 air quality, LiPo powered. Indoor: BME280 + SCD40 CO2 + MQ-6 propane, 12V coach power. Both log to onboard flash during travel, sync to home MQTT on WiFi reconnect (home or Pixel hotspot). DS3231 RTC for accurate timestamps during extended trips. GPS correlation via GPSLogger on Pixel. Phase 1 complete — ready for Phase 2 (hardware selection, inventory scan, open questions resolved).

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

Archived to `components/hike-izer/CLAUDE.md` on 2026-08-22 (CARD-0193) — 18619B, over the 10000B size threshold.

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

**Confirmation reported back to the GitHub issue same day (2026-07-24)** — maintainer acknowledged and kept it open until the production release, closing it 2026-08-04 when v26.8.5 shipped with the fix. See CARD-0161 for the production landing of that release.

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

### CARD-0063 · [idea] [netalertx] NetAlertX MQTT event richness experiment + log dashboard wiring — RESOLVED 2026-07-14
**Status:** Done

Archived to `components/netalertx/CLAUDE.md` on 2026-08-22 (CARD-0193) — 11177B, over the 10000B size threshold.

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
