# Session Card Selection

**Author:** Joseph C Thomas (JCT), via Claude
**Purpose:** Defines how a session chooses which card to pick up next, when several are candidates.
**Version:** 1.0

---

Distinct from `JCTsh-Operating-System.md`'s Priority section — Priority tags how urgent a
card is; this is how a session actually chooses which card to pick up when several are
candidates. Applied by default when deciding what to work on next, not only when
prioritization is explicitly asked for.

Four factors, checked in order — move to the next only when the previous one doesn't
settle it:

1. **Actionable now vs. blocked on something else.** Skip a card — even one sitting in
   Build — if there's nothing left to do on it right now: it's waiting on a real-world
   recurrence, a manual deploy step, or some other external event, not on more work from
   this session.
2. **Whose job it is.** Skip a card whose next step belongs to Joseph by this project's
   established division of labor (e.g. building/confirming a Tasker profile is always
   his) — Claude's part there is already done at the scoping stage.
3. **Already scoped beats not yet scoped.** Prefer a card with a full interview and
   concrete acceptance criteria already sitting in Backlog/Planning over one that's still
   essence-only and needs a Planning pass before any code gets written — cheaper to pick
   up.
4. **Bugs before enhancements — a tiebreaker only.** When two or more candidates tie on
   all three factors above, prefer `[bug]`-tagged cards over `[enhancement]`/`[idea]`-tagged
   ones. Does not override factor 1 — a blocked bug still loses to an actionable
   enhancement.

Explicitly not weighed: raw severity beyond the bug/enhancement tiebreaker, card age, or
business impact — these can be added later if they prove genuinely load-bearing, same
discipline as the rest of this system.

**Related:** `JCTsh-Operating-System.md` (Priority section, the adjacent-but-distinct
existing concept), `kanban-board.md` CARD-0288 (origin of this document).
