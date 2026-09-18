# Portable Kanban Template

**Purpose:** A minimal card-based backlog, distilled from `jctsh`'s own `kanban-board.md`
discipline (card format, Status columns, done-when criteria, `Related:` cross-refs) for
reuse in a small, separate repo — first users are the LogSeq and Pastor Ben blog repos
(CARD-0297/CARD-0298), bootstrapped from this file rather than reinventing the format.

**Deliberately excludes jctsh's automation scaffolding** — `archive_cards.py`, the
auto-PR maintenance-check intake pipeline, the multi-host Session Start ritual. None of
that solves a problem a small, low-card-volume repo actually has; it exists in `jctsh`
because that repo's real card volume and multi-host operational surface earned it over
time (CARD-0193, CARD-0128). A repo that starts from this template should only add that
kind of scaffolding later, if its own real volume/need justifies it — not preemptively,
per the same iterative/incremental discipline `JCTsh-Operating-System.md` applies
everywhere else.

**To use this template:** copy this file into the new repo as its own `kanban-board.md`
(or equivalent name), delete this purpose/exclusion preamble, and start adding cards
under the `next-card-id` marker below.

---

Lightweight kanban. Each card has a **type** (idea | enhancement | bug) and a unique ID.

**Columns:** Backlog → Planning → Build → Done, plus **Defer** (a deliberate decision not
to pursue for now — not abandoned, not forgotten — reachable from any other column).
- **Backlog** — captured, not yet being worked on
- **Planning** — being scoped/interviewed, and (if non-trivial) an implementation plan written
- **Build** — going through the plan/implementation, including testing
- **Done** — complete
- **Defer** — consciously parked, can move here from any other column

**Priority** (optional, independent of column) — how urgently a card needs attention, not
how far along it is:

| Priority | Definition |
|---|---|
| **Critical** | Must be done as soon as possible. |
| **High** | Must be done, time to schedule it. |
| **Medium** | Worth it if the opportunity/energy is there, not load-bearing. |
| **Low** | Probably will never get to — captured so the idea isn't lost. |

<!-- next-card-id: CARD-0001 -->

---

### CARD-0001 · [idea] Example card — delete once real cards exist

**Status:** Backlog

**Priority:** *(optional — omit if not yet judged)*

Free-text body: why this was raised, what's been decided so far, open questions still to
resolve. Update in place as understanding develops — don't rewrite history, add to it.

**Done when:** the concrete, objective condition that makes this card closeable — written
once real scoping happens, not guessed at card-creation time.

**Related:** other CARD-IDs this connects to, if any.

---
