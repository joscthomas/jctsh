# JCT Smart Home (JCTsh) Team Operating System (TOS)
**Author:** Joseph C Thomas (JCT)
**Purpose:** Defines how the JCTsh team works — the conceptual process governing all work.
**Version:** 1.5
**Version description:** Moved two process rules out of `JCTsh-Build-Standards.md` (CARD-0289 follow-on): §6.1/§6.3 (Additive First, Existing Pattern Investigation) generalized into a new Engineering Discipline section — they were framed around integration code but apply to any change in this repo; §7.5 (Documentation Captures Reality) folded into the Note on Build, since it was pure process with no technology content and overlapped the existing Reflection requirement. Also added a reconciliation note cross-referencing `JCTsh-Build-Standards.md` — this document covers process/policy/workflow (how the team works), that one covers technology/build conventions (how things get built); the boundary case (documentation structure) generalizes in whichever doc is broader and cross-references the narrower one, rather than duplicating. Also added a Documentation Structure section (CARD-0289) — split docs by topic/read-frequency, not file count, and keep cross-references current; generalizes `JCTsh-Build-Standards.md` §7.1a's README/CLAUDE.md split into a repo-wide rule. Also added a Session Card Selection pointer (CARD-0288) to the new standalone `JCTsh-Session-Card-Selection.md` — four ordered factors governing which card a session actually picks up next, distinct from the Priority section's urgency tag. Applied by default each session, not only when prioritization is explicitly asked for.
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
- **Investigate existing patterns first, never assume.** Before writing anything new that touches an existing process, locate and read the relevant existing implementation first — verify, don't guess at how something already works.

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

## Documentation Structure

**Split documentation by topic and read-frequency, not by minimizing file count.** What gets read every session stays small and central (`CLAUDE.md`, this document); detail that's only needed on demand goes into its own focused file that gets pointed to explicitly, rather than growing in place. A file sized to one topic — small enough to read whole in one pass — beats a large one that has to be sampled or reconstructed piecemeal once it outgrows that (`kanban-board.md` hit this for real, CARD-0193, forcing grep-only access and losing the "read straight through" comprehension a single pass gives).

The cost of splitting is reference-chasing and drift, not file count — so cross-references (`**Related:**` or equivalent) must stay explicit and current, or many small files just become a maze instead of a coherent system. `JCTsh-Build-Standards.md` §7.1a already applies this same read-frequency split at the component-doc level (README vs. CLAUDE.md); this section generalizes it as a repo-wide rule rather than a component-specific one (CARD-0289).

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

**Required last step of Build — Reflection:** Before a card moves to Done, reflect on what was learned while doing the work and capture it somewhere it will actually be found again — the relevant standards or pattern document (e.g. `JCTsh-Build-Standards.md` for hardware/firmware builds), a component doc, or a note on the card itself if no broader pattern doc applies. The goal is to leverage what was just learned in future work, not relearn the same thing by trial and error later. This mirrors `JCTsh-Component-Planning-Pattern.md`'s "Harvest new patterns into Build Standards" final step, generalized to all Build work, not just hardware components.

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
