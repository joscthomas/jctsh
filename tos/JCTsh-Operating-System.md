# JCT Smart Home (JCTsh) Team Operating System (TOS)
**Author:** Joseph C Thomas (JCT)
**Purpose:** Defines how the JCTsh team works — the conceptual process governing all work.
**Version:** 1.0
**Version description:** Initial version — defines the kanban board, its columns (states) and state-transition triggers; Team Members; where work happens (Claude chat for informal pre-card thinking, Claude Code for Planning through Done); Notes on Planning (single or multi-phase/multi-document) and Build (per-step manual work/confirmation by Joseph, plus a required closing Reflection step); applying TOS to pre-existing work; and the relationship between board state and the commit/push workflow.

---

## Team Members

- **Joseph (JCT)**
- **Claude**

---

## Core Principle

All work has a card on the kanban board (`kanban-board.md`). The board is the durable, scannable record of what the team is doing, has done, and has decided not to do — not DEVLOG entries or component docs alone, which capture detail but aren't structured for at-a-glance status.

If files start changing for something not already covered by an open card, a card should exist before or while that work proceeds — or a deliberate decision gets made not to open one. Work doesn't happen off the board silently.

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

**Note on Build:** Build is not Claude Code executing alone. It includes per-step manual work and confirmation by Joseph wherever the work requires it — physical assembly, wiring, flashing, real-world verification — the same Claude Code does / Joseph does / Joseph confirms pattern `JCTsh-Component-Planning-Pattern.md` Phase 5 uses for hardware builds, generalized to any card where a human step is required. "Verification that everything works correctly" means the change is live and confirmed working — deployed, tested, observed — not merely edited locally. A card with outstanding deployment, manual, or verification steps stays in Build with those steps noted, rather than moving to Done prematurely.

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
