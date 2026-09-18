# JCTsh-Component-Session-Start.md — Version History

Full changelog for `JCTsh-Component-Session-Start.md`, split out (CARD-0292) alongside
the analogous split for `JCTsh-Operating-System.md` — same growing "Prior version
description" chain pattern, applied proactively here before it grew as large. Read on
demand only, not part of routine reading. The live document's header now states only
the current version and its own description.

---

| Version | Description |
|---|---|
| 1.7 | Split this changelog out to this file (CARD-0292) — proactive, alongside the analogous `JCTsh-Operating-System.md` split, before this document's own chain grew as large. From this version on, the live document's header holds only the current version's description; this file is the complete record. |
| 1.6 | Corrected the document's own framing (CARD-0284 follow-on, Joseph) — a component session does not run every general Session Start step unmodified and then add more on top, as previously stated. Replaced that framing with a per-step table covering all 9 general steps (scoped / skipped / unscoped, decided individually), so the two step-lists below are now genuinely "instead of," not "in addition to." |
| 1.5 | Added step 5 (CARD-0282) — scope `CLAUDE.md`'s `/status` device-health check to this session's own covered component(s) only, the same scoping principle step 3 already applies to kanban checks, applied here to device/dashboard health instead. |
| 1.4 | Step 4 revised (CARD-0284 follow-on) — softened "resume it, never restart it" to "default to resuming," with a real case for a periodic deliberate restart (context/cost bloat, self-testing that the `.md` files are actually sufficient on their own, shedding stale intermediate reasoning) — not just a fallback for a lost session. Also noted the mechanical point that resuming works just as well from a clean shell (`claude --resume`/`--continue`) as from `/resume` inside another session, which is the practical way to run two component sessions side by side. |
| 1.3 | Added "Initiating or Rebuilding a Component Session" (CARD-0284, moved to Build) — generalizes the two real instances (hike-izer, `tos`) into a repeatable 4-step procedure for starting a new component/cluster session or reconstructing an existing one, using nothing beyond this document's own existing startup steps. |
| 1.2 | Step 3 extended (CARD-0284 follow-on) — the component-tag scoping isn't just for the automated startup kanban checks, it's the default for any card-related request made during the session (e.g. "list the open cards" defaults to this session's own component tag(s), not the whole board, unless Joseph asks otherwise). Found live: a `tos`-component-session "list the open cards" request was answered whole-board instead, because the prior wording only covered the automatic sweep. |
| 1.1 | Step 2 updated (CARD-0290) — `CLAUDE.md` is genuinely readable in full now that archived card history lives in a dedicated `card-archive.md` sibling instead of being appended directly into `CLAUDE.md` (which had grown as large as 485KB before the split). `card-archive.md` explicitly stays out of this list — on-demand only, never routine reading. |
| 1.0 | Initial release (CARD-0284) — original 4-step startup list, description not separately recorded before the chaining convention began. |

**Related:** `tos/kanban-board.md` CARD-0292 (this split), `JCTsh-Operating-System-History.md` (the analogous split for that document).
