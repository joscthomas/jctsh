# Where Protocols, Steps, and Rules Live

**Author:** Joseph C Thomas (JCT), via Claude
**Purpose:** Where a step-by-step procedure, rule, or protocol should be documented —
across jctsh, and (interim, pending CARD-0315) anywhere else Joseph works with Claude.
**Version:** 1.0
**Version description:** Initial version, decided 2026-09-19 out of a live discussion
about LogSeq's own editing conventions.

---

**A step-by-step procedure, rule, or protocol belongs in its own dedicated `.md` file,
never inlined directly into a `CLAUDE.md`** (global or project-local). A `CLAUDE.md`
stays a short, curated pointer to where the real content lives, not the content itself —
same discipline `JCTsh-Operating-System.md`'s Documentation Structure section already
applies to `README.md` vs. `CLAUDE.md` within a component, generalized here to `CLAUDE.md`
files themselves at any level (global, repo-root, or component).

**Where the protocol itself lives depends on its actual scope:**

- **Specific to one project** — lives inside that project, in a discoverable, versioned
  location analogous to jctsh's own `tos/` directory (e.g. `tos/JCTsh-Session-Start.md`,
  `tos/pr-review-checklist.md`). LogSeq's own editing conventions are the first example
  of this pattern applied outside jctsh — see `LogSeq/tos/` once created.
- **Genuinely universal, true regardless of the project** — belongs in Joseph's global
  `~/.claude/CLAUDE.md`, which already documents the general card/commit/push workflow
  this same rule generalizes from.
- **Shared by *some* projects but not universal to all of them** (e.g. a family of
  related personal repos under `Projects/`) — **no settled home yet.** Interim call,
  2026-09-19: reuse `jctsh/tos/` for this middle tier too, since it's already the most
  mature process home that exists, rather than inventing a new shared location
  preemptively. Revisit if `tos/kanban-board.md` CARD-0315's own open question (whether a
  dedicated shared/"TOS" location is eventually worth creating) ever gets a real answer.

**Related:** `tos/kanban-board.md` CARD-0315 (the open cross-repo protocol-management
question this document's own placement is an interim answer to), `JCTsh-Operating-System.md`
(Documentation Structure section — the README-vs-CLAUDE.md split this generalizes).
