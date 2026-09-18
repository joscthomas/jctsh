# JCT Smart Home (JCTsh) Team Operating System (TOS)
**Author:** Joseph C Thomas (JCT)
**Purpose:** Defines how the JCTsh team works — the conceptual process governing all work.
**Version:** 1.11
**Version description:** Added two Documentation Structure notes (CARD-0290, Joseph) — (1) archived card history now gets its own `card-archive.md` per component, never appended into `CLAUDE.md` directly (the same working-file/archive split `kanban-board.md`/`kanban-archive.md` already has, applied at the component-doc layer after `components/hike-izer/CLAUDE.md` reached 485KB); (2) a component-doc filename standard — unprefixed by default (matches `README.md`/`CLAUDE.md`'s own locked, unprefixed names), prefixed only when a file is commonly referenced by name outside its own directory context. Explicitly a process/documentation rule, not a technology one — corrected after initially proposing it for `JCTsh-Build-Standards.md`, which doesn't fit a rule that applies the same regardless of a component's hardware. Prior version description: Added a Component/Cluster Sessions section pointing to the new `JCTsh-Component-Session-Start.md` (CARD-0284, Joseph) — a session with a standing, resumed identity for a specific component or cluster (distinct from a general session with no such persistent focus) runs extended startup steps beyond `CLAUDE.md`'s general Session Start: read each covered component's `README.md` and `CLAUDE.md` fully, and scope the kanban/marker checks to its own component tags specifically, not just rely on the whole-board general sweep. Same session-behavior-document pattern as `JCTsh-Session-Card-Selection.md`. Prior version description: Extended Engineering Discipline's "Investigate existing patterns first" rule to explicitly cover hardware/physical capability claims (CARD-0226/CARD-0222/CARD-0258, Joseph) — check a component's own `README.md`/detail docs before relying on or asserting what it can physically do, never infer from a sibling component's build. Raised directly by a real miss: five dated notes on CARD-0226 assumed hiking-monitor could run air-quality-monitor's debug-UART setup, never checked hiking-monitor's own `wiring.md`, which shows it was never wired for one. Root `CLAUDE.md`'s own pointer corrected to match — `README.md` is the permanent hardware/capability reference per `JCTsh-Build-Standards.md` §7.1, `CLAUDE.md` is history/rationale, and the two were being conflated. Prior version description: Added an Accepted-limitation closure note under Note on Build (CARD-0258, Joseph: "i like it") — a card can reach Done with its root-cause criterion unmet, but only when a built mitigation is confirmed working live, the unmet piece is specifically causal (not functional) understanding, no practical investigative path remains, and a person makes that call explicitly. Distinguished from Defer (no working mitigation at all) and from a card with a still-active lead (doesn't qualify yet, e.g. CARD-0222 pending CARD-0226/CARD-0221's UART-capture path). Prior version description: Added a Listing open cards subsection to Auto Verify / Watch For Markers (CARD-0258, Joseph) — when a session lists open cards for Joseph directly (not the `/kanban` dashboard), cards carrying an active marker are omitted from the visible list entirely (not just sorted last) and rolled up into a single count at the end, mirroring `/kanban`'s existing sort-to-end reasoning that a marker-carrying card doesn't need attention right now. Prior version description: Added an Auto Verify / Watch For Markers section (CARD-0251/CARD-0258) — promotes the ad hoc marker practice CARD-0251 built into a real documented home, per that card's own "promote once proven out" plan. Formalizes a resolution protocol that didn't exist before: found live via CARD-0258, where a Watch for marker was actually resolved but its original marker line was never edited to stop matching the parser's literal-text regex, leaving both the `/kanban` badge and every future Session Start's grep treating an already-answered check as still open indefinitely. Prior version description: Moved two process rules out of `JCTsh-Build-Standards.md` (CARD-0289 follow-on): §6.1/§6.3 (Additive First, Existing Pattern Investigation) generalized into a new Engineering Discipline section — they were framed around integration code but apply to any change in this repo; §7.5 (Documentation Captures Reality) folded into the Note on Build, since it was pure process with no technology content and overlapped the existing Reflection requirement. Also added a reconciliation note cross-referencing `JCTsh-Build-Standards.md` — this document covers process/policy/workflow (how the team works), that one covers technology/build conventions (how things get built); the boundary case (documentation structure) generalizes in whichever doc is broader and cross-references the narrower one, rather than duplicating. Also added a Documentation Structure section (CARD-0289) — split docs by topic/read-frequency, not file count, and keep cross-references current; generalizes `JCTsh-Build-Standards.md` §7.1a's README/CLAUDE.md split into a repo-wide rule. Also added a Session Card Selection pointer (CARD-0288) to the new standalone `JCTsh-Session-Card-Selection.md` — four ordered factors governing which card a session actually picks up next, distinct from the Priority section's urgency tag. Applied by default each session, not only when prioritization is explicitly asked for.
**Related files:** `JCTsh-Build-Standards.md` (technology/build conventions — see the reconciliation note below for how the two relate)

---

## Team Members

- **Joseph (JCT)**
- **Claude**

---

**Scope boundary, reconciled with `JCTsh-Build-Standards.md`:** this document is process, policy, and workflow — how the team works, how work moves through the board, how a session decides what to pick up. Technology and build conventions — how to wire, name, or configure things — live in `JCTsh-Build-Standards.md` instead. A rule that would still make sense in a repo with no hardware or code at all belongs here, not there.

---

## Core Principle

All work has a card on the kanban board (`kanban-board.md`). The board is the durable, scannable record of what the team is doing, has done, and has decided not to do — not DEVLOG entries or component docs alone, which capture detail but aren't structured for at-a-glance status.

If files start changing for something not already covered by an open card, a card should exist before or while that work proceeds — or a deliberate decision gets made not to open one. Work doesn't happen off the board silently.

---

## Engineering Discipline

Generalized from `JCTsh-Build-Standards.md` §6.1/§6.3 (CARD-0289 follow-on) — those were framed narrowly around integration code, but the underlying rules apply to any change in this repo, hardware or not:

- **Additive first.** New work is additive by default. Existing behavior, integrations, or automations are never removed or modified without an explicit decision documented in the card or instruction set — wire something new in parallel, don't replace, unless that decision was actually made.
- **Investigate existing patterns first, never assume.** Before writing anything new that touches an existing process, locate and read the relevant existing implementation first — verify, don't guess at how something already works. This explicitly includes a component's own **hardware/physical capability** — before relying on or asserting that a specific component can do something (a pin, a sensor, a debug interface), check that component's own `README.md` and the detail docs its Files table indexes (`wiring.md`, `power-system.md`, `ESP32-project-pins.md`, `perfboard-layout.md`, etc.), per `CLAUDE.md`'s pointer — not a sibling component's build, and not memory. Found live, 2026-09-17 (CARD-0226/CARD-0222/CARD-0258): five separate dated notes assumed a debug-UART setup built for air-quality-monitor could simply be run on hiking-monitor, without ever checking that device's own `wiring.md` — it was never wired for one.

`JCTsh-Build-Standards.md` §6.1/§6.3 keep their section numbers as short pointers here, with any hardware/integration-specific specifics that don't generalize.

---

## Where Work Happens: Chat vs. Claude Code

**Preliminary thinking and research happens in Claude chat, informally.** Feasibility questions, initial ideas, "should we build this at all" — this stage does **not** produce planning documents and doesn't correspond to any board column. It's pre-Backlog raw material, not tracked work, and no card exists yet.

**The transition point is a decision to build something.** Once preliminary thinking and initial research are done and that decision is made, move to Claude Code and create a card capturing that thinking and research, placed in **Backlog**. From Backlog onward, Claude Code handles everything — Planning (including whatever phases or documents the work needs, see Note on Planning below), Design, Build, and Done. Chat's role ends once the card exists; it doesn't re-enter the process to produce planning or design documents later.

---

## Board Columns (States)

**"Column" and "state" are synonyms.** Each column on the kanban board is a state a card can be in. Taken together, the columns represent a process of state transitions — a card moves through them (not necessarily every one, see Observed Exception below) as work progresses from idea to completion, or out sideways into Defer.

| Column (State) | Definition |
|---|---|
| **Backlog** | Captured, not yet being worked on |
| **Planning** | Plan is being laid out |
| **Design** | Claude Code instructions being written |
| **Build** | Going through Claude Code instructions, including testing |
| **Done** | Complete |
| **Defer** | A deliberate decision not to pursue for now (not abandoned, not forgotten — just consciously parked); reachable from any other state |

---

## Priority

Independent of column/state — priority describes how urgently a card needs attention, not how far along it is. A card can be Critical and still sit in Backlog (just captured, not yet started) or Low and sit in Build (in progress, but nobody's in a hurry). Four levels:

| Priority | Definition |
|---|---|
| **Critical** | Must be done as soon as possible — something is actively broken, actively at risk, or a real deadline is bearing down. |
| **High** | Must be done, but there's time to schedule the work — not urgent today, not optional either. |
| **Medium** | Cool to do — worth it if the opportunity or energy is there, not load-bearing. |
| **Low** | Probably will never get to — captured so the idea isn't lost, not a real commitment. |

Use this scale whenever asked to prioritize — cards, backlog review, or otherwise. Not every card needs an explicit priority tag; assign one when it's actually asked for or genuinely load-bearing to the work (e.g. a real deadline like CARD-0164's), not retroactively swept across the whole board.

---

## Session Card Selection

Distinct from Priority above — Priority tags how urgent a card is; **which card a session actually picks up when several are candidates** is a separate question, defined in its own document: `JCTsh-Session-Card-Selection.md`. Applied by default when deciding what to work on next, not only when prioritization is explicitly asked for.

---

## Component/Cluster Sessions

A session with a standing, resumed identity dedicated to a specific component or group of components (a **cluster session**, CARD-0284 — e.g. "the hike-izer session") runs extended startup steps beyond `CLAUDE.md`'s general Session Start, defined in its own document: `JCTsh-Component-Session-Start.md`. Distinct from a general session with no such persistent focus, which only ever runs the general steps.

---

## Documentation Structure

**Split documentation by topic and read-frequency, not by minimizing file count.** What gets read every session stays small and central (`CLAUDE.md`, this document); detail that's only needed on demand goes into its own focused file that gets pointed to explicitly, rather than growing in place. A file sized to one topic — small enough to read whole in one pass — beats a large one that has to be sampled or reconstructed piecemeal once it outgrows that (`kanban-board.md` hit this for real, CARD-0193, forcing grep-only access and losing the "read straight through" comprehension a single pass gives).

The cost of splitting is reference-chasing and drift, not file count — so cross-references (`**Related:**` or equivalent) must stay explicit and current, or many small files just become a maze instead of a coherent system. `JCTsh-Build-Standards.md` §7.1a already applies this same read-frequency split at the component-doc level (README vs. CLAUDE.md); this section generalizes it as a repo-wide rule rather than a component-specific one (CARD-0289).

**Archived card history gets its own file, never appended into `CLAUDE.md` directly (CARD-0290).** `CLAUDE.md` is supposed to be curated, actively-useful context (constraints, gotchas, design rationale) — but `archive_cards.py` (CARD-0193) was appending full archived-card text straight into it, unbounded, conflating "current curated context" with "growing historical record" in one file. Same read-frequency-split principle as this section's own rule, just not yet applied at this specific layer until it was actually hit (`components/hike-izer/CLAUDE.md` reached 485KB). Fixed: every component's archived card history now lives in a sibling `card-archive.md` — read on-demand only, never as part of routine Session Start or component/cluster-session startup (`JCTsh-Component-Session-Start.md`) — same relationship `CLAUDE.md` already has to `kanban-archive.md`/`kanban-board.md`.

**Component-doc filename standard, decided 2026-09-17 (CARD-0290, Joseph) — applies regardless of a component's technology** (hardware or pure software, ESP32 firmware or an HA-only automation): **unprefixed by default** — `wiring.md`, `power-system.md`, `card-archive.md`, etc., not `<component>-wiring.md`. A file that's only ever opened from within its own component's directory context gains nothing from repeating the component's name — the path already disambiguates, and it matches the two filenames this convention can't deviate from anyway (`README.md`/`CLAUDE.md`, locked by GitHub/Claude Code convention). **Prefix only when a file is commonly referenced or searched by name outside its own directory context** — e.g. `hiking-monitor-enclosure-plan.md`, `*-claude-code-instructions.md` — generic-enough names that a bare version would be ambiguous the moment it's typed or searched without already being scoped to one component's folder. This existing split was never articulated before now; going forward, apply it deliberately rather than by feel.

---

## State Transitions

Each transition has a **trigger** — the concrete thing (an artifact existing, a decision being made, or both) that causes a card to move to the next state. A trigger is not a vague sense that it's "probably time" — it's a specific, checkable condition.

| From | To | Trigger |
|---|---|---|
| *(new)* | **Backlog** | Entry criteria: any idea or thought the team might want to work on. This is the lowest bar on the board — capture, don't filter. |
| **Backlog** | **Planning** | A decision to spend time exploring and researching the idea. |
| **Planning** | **Design** | A planning document exists **and** a decision to spend time designing a solution. |
| **Design** | **Build** | A design document or Claude Code instructions exist **and** a decision to build the thing. |
| **Build** | **Done** | All criteria for the Build are satisfied, **including verification that everything works correctly** — not just that the code/files changed. |
| *(any state)* | **Defer** | A decision to not pursue the work. |

**Note on Planning:** Planning is not always a single step, and it happens in Claude Code, not chat (see Where Work Happens above) — chat's contribution is the informal, pre-card thinking that led to the card's creation, not the planning documents themselves. For a hardware or software build, Planning may consist of multiple sequential phases — e.g. discovery/feasibility, hardware selection, architecture/integration design, per `JCTsh-Component-Planning-Pattern.md`'s Phases 1–3 — each potentially producing its own planning document depending on the sequence and depth of work the card actually needs. For simpler work, Planning may produce just a single planning document. Either way, the Planning → Design trigger's "a planning document exists" is satisfied by whatever set of documents Planning actually produced — the structure adapts to the work, not the other way around.

**Note on Build:** Build is not Claude Code executing alone. It includes per-step manual work and confirmation by Joseph wherever the work requires it — physical assembly, wiring, flashing, real-world verification — the same Claude Code does / Joseph does / Joseph confirms pattern `JCTsh-Component-Planning-Pattern.md` Phase 5 uses for hardware builds, generalized to any card where a human step is required. "Verification that everything works correctly" means the change is live and confirmed working — deployed, tested, observed — not merely edited locally. A card with outstanding deployment, manual, or verification steps stays in Build with those steps noted, rather than moving to Done prematurely. **Documentation captures reality as it goes** (generalized from `JCTsh-Build-Standards.md` §7.5, CARD-0289 follow-on): instructions get updated with actual findings during the work itself, not just original intentions, and a deviation from the plan is documented immediately when discovered — not deferred to the Reflection step below.

**Accepted-limitation closure (added 2026-09-17, CARD-0258, Joseph: "i like it").** A card can still reach Done even when a stated Done-when criterion — specifically, *identifying a root cause* — is never met, provided all of the following hold, and the decision is explicit, never a default:
1. **Any mitigation the card built is itself confirmed working live**, per the Note on Build above — not just deployed. The card closes on "handled, cause unknown," never on "hopefully handled, unverified." A card with no working mitigation at all doesn't qualify for this — that's a **Defer** candidate instead (State Transitions table above), not a Done, since nothing was actually accomplished to close on.
2. **The unmet criterion is root-cause identification, not a functional/behavioral requirement.** A "does it actually work" criterion never gets this treatment — only "do we know why" can.
3. **No further practical investigative path remains** — the evidence that could have settled it is gone, exhausted, or blocked, not just "hasn't been gotten to yet." A card with an active, real lead still open doesn't qualify until that lead is actually exhausted, even if it's been sitting for a while.
4. **A person makes the call explicitly and it's recorded on the card** — this is never a default a card drifts into by simply sitting untouched in Build.

Closing a card this way doesn't make it un-reopenable: a genuine new lead or recurrence later is a fresh finding, not a violation of the closure.

**Required last step of Build — Reflection:** Before a card moves to Done, reflect on what was learned while doing the work and capture it somewhere it will actually be found again — the relevant standards or pattern document (e.g. `JCTsh-Build-Standards.md` for hardware/firmware builds), a component doc, or a note on the card itself if no broader pattern doc applies. The goal is to leverage what was just learned in future work, not relearn the same thing by trial and error later. This mirrors `JCTsh-Component-Planning-Pattern.md`'s "Harvest new patterns into Build Standards" final step, generalized to all Build work, not just hardware components.

---

## Auto Verify / Watch For Markers

A card can carry a **follow-up marker** in its body when Build's "verification that everything works correctly" (Note on Build, above) can't be done live at write time. Two flavors, named and built via CARD-0251 (2026-09-07/08):

- **Date-based — `**Auto verify: <date>**`.** For a verification that depends on a known future date/event (a scheduled reboot, a timer firing). Checked at CLAUDE.md's Session Start, every session, once the date has passed.
- **Event-based — `**Watch for:** <description>`.** For a verification tied to a real-world condition of unknown future timing — no date to wait on, typically a specific log line that only appears if/when a field condition occurs. Checked at CLAUDE.md's Session Start, every session, unconditionally.

Both markers are parsed by `core/logging/log_server.py` (`_parse_kanban_board()`) and rendered as a badge on the card's `/kanban` header, so an open marker is visible without reading the card body.

**Status-vs-marker rule (corrected 2026-09-17, CARD-0251/CARD-0276/CARD-0224):** an open marker means real-world verification is still outstanding — the card stays in Build (or whatever non-Done state it's actually in) until the marker resolves, full stop. Being "verified some other way" (code review, a synthetic test, a live check of a different kind) is never a substitute and never grounds an exception.

**Resolution protocol (added 2026-09-17, CARD-0258 — a real gap found live, not designed in advance):** both the parser and CLAUDE.md's Session Start grep match a marker by its exact literal text (`^\*\*Auto verify: <date>\*\*` / `^\*\*Watch for:\*\*`) — neither has any independent notion of "already resolved." When a marker's condition is actually observed:
1. Write a dated resolution note documenting what was observed (same discipline as any other Build finding).
2. **Also edit the original marker line itself** so it stops matching the literal pattern — e.g. `**Watch for (RESOLVED 2026-09-17, see below):**` — never just leave it as-is and rely on a later paragraph to explain it resolved. A resolution note alone, with the original marker text still intact, is a real bug, not a cosmetic one: the `/kanban` badge keeps showing the card as still-watching, and Session Start's grep keeps re-running the same already-answered check every future session, indefinitely. This exact failure mode is what CARD-0258 was caught doing before this protocol existed.
3. Only once the marker is neutralized this way (and Build's other criteria are met) does the card actually clear the Build → Done trigger.

**Listing open cards (added 2026-09-17, Joseph).** Same "doesn't need eyes on it right now" reasoning as `/kanban`'s own sort-to-end-of-column behavior (CARD-0251), applied to how a session lists open cards for Joseph directly (verbally, in chat) rather than via the dashboard: a card carrying an active Auto verify or Watch for marker is passively waiting on something outside the session's control, so it's omitted from the visible list entirely — not just sorted last. State the total count of omitted marker-carrying cards at the end of the list instead (e.g. "4 more waiting on a marker"), so nothing is silently hidden, just decluttered. A card whose marker has resolved (per the resolution protocol above) is no longer "carrying an active marker" and belongs back in the visible list like any other open card.

**Related:** CARD-0251 (origin, both marker flavors), CARD-0258 (found and fixed the resolution gap this protocol formalizes, and raised the listing convention above), CARD-0224/CARD-0276 (the status-vs-marker correction), `core/logging/log_server.py` (`_parse_kanban_board()`, the badge-rendering parser both flavors share).

---

## Observed Exception: Skipping Design

In practice, several cards move directly from Planning to Build, skipping Design as a distinct column. This happens when Planning (in Claude Code, per `JCTsh-Component-Planning-Pattern.md`) already produces an approved execution plan or Claude Code instructions as part of Planning itself — at that point the Design → Build trigger's criteria are already satisfied, so the card just starts in Build rather than sitting in an empty Design column for form's sake. `kanban-board.md` notes this explicitly on cards where it happened (e.g. CARD-0003, CARD-0034) rather than silently skipping the column.

---

## Applying TOS to Pre-Existing Work

TOS did not exist when most of the cards currently in `kanban-board.md` were worked. Older cards that don't cleanly match a single column — e.g. a card whose Design deliverable (Claude Code instructions) is already complete while it still sits in Planning — aren't inconsistencies to fix. They're history that predates the process which would have produced a cleaner state. This is process improvement, not a correction owed to past work.

Reconciling any specific older or in-flight card against TOS — moving it to the column it actually belongs in, retroactively producing a missing artifact — is a **per-card judgment call** based on whether doing so adds real value, not a blanket retroactive mandate to sweep the whole board into compliance.

---

## Relationship to Commit / Push

Separate from board state, but adjacent to it. The **card**, not any git mechanic, is the organizing concept — a file getting staged (`git add`) isn't a meaningful state of its own, just the mechanical step that tells git which files belong to the next commit.

| Concept | What it is |
|---|---|
| **File creation/modification** | The result of working a card — a card's work produces some set of created or modified files on disk |
| **Commit** | Taking that file set (the card's work product) and recording it into local `.git` history. Not strictly before or after Done — the commit is the action that *enacts* the Build → Done transition. It requires Build's criteria (implementation, verification, reflection) to be satisfied first, and typically includes the `kanban-board.md` edit moving the card to Done with its Resolution note in the same atomic commit |
| **Commit note** | Ties back to the card that defines the work, so history reads as "which card produced this snapshot," not just a list of file diffs |
| **Push** | A backup checkpoint, not a release — nothing deploys from `origin/main` itself (devices/servers are updated via their own explicit step: scp, OTA, a deploy script, verified live before the commit that represents it), so a push just copies already-verified history to the remote. Default to pushing readily rather than batching for release-shaped reasons |

See the user's global Claude Code preferences for the full card/commit/push workflow this operating system runs inside of.
