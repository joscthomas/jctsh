# Component/Cluster Session Start

**Author:** Joseph C Thomas (JCT), via Claude
**Purpose:** The startup steps a persistent component or cluster session (CARD-0284) actually runs instead of `CLAUDE.md`'s general Session Start — some general steps scoped down, some skipped, some run unscoped, plus component-only steps with no general-session equivalent.
**Version:** 1.7
**Version description:** Split the "Version description" chain out to `JCTsh-Component-Session-Start-History.md` (CARD-0292), proactively alongside the analogous `JCTsh-Operating-System.md` split — this document's own chain would have hit the same growth pattern soon. From this version on, this header holds only the current version's description; older ones live exclusively in the history file, never chained here.
**Version history:** `JCTsh-Component-Session-Start-History.md`

---

A **component session** — which includes a **cluster session** (CARD-0284: a group of related components with one shared session, e.g. "the hike-izer session" covering `hike-izer`/`hike-izer-orchestrator`/`hike-izer-web`/`core/data-pipeline`) — is a session with a standing, resumed identity dedicated to one or more specific components. This is distinct from a general session with no such persistent focus (yet) established.

## Initiating or Rebuilding a Component Session

Two real instances exist as of 2026-09-17 — the hike-izer cluster session (CARD-0284's original pilot) and the `tos` component session (this document's own subject, confirmed as a second instance the same day) — generalized here into a repeatable procedure for starting a new one, or reconstructing an existing one that's been lost or never formally initiated:

1. **Decide the scope.** One component, or a cluster of related components that findings routinely travel across together (CARD-0284's cluster-level granularity guidance) — not one session per individual file or feature.
2. **Give it a plain name** matching the scope (e.g. "the hike-izer session," "the tos session") — this is purely so `/resume`'s own picker can find it later; no separate registry or naming file is needed.
3. **Run the startup steps below** (this document's per-step table plus its two component-only read steps, scoped to the chosen component(s)) — this is the entire initiation procedure. There is no separate "setup" step beyond actually running startup scoped to the new component(s) for the first time.
4. **From then on, default to resuming it** (CARD-0284's workflow) — the session's own history is a speed cache, not the source of truth, so nothing is lost if it's later abandoned and needs rebuilding: re-running the same startup steps against the same component(s) reconstructs full working context from the `.md` files alone, per CARD-0284's original "cache layer, not a second store" design. This is what makes "rebuilding" identical to "initiating" — there's no separate recovery procedure to maintain. Mechanically, resuming doesn't require staying inside an existing session: from a clean shell/terminal, `claude --resume` (pick it from the list) or `claude --continue` (if it's the most recent) reaches the same session just as well as `/resume` from within another one — the practical way to run two component sessions side by side is simply two terminal windows, each resumed independently.

**A periodic deliberate restart is a real, worthwhile exception to "always resume," not just a fallback for a lost session (added 2026-09-17).** Three genuine benefits, weighed against the ramp-up cost this whole design exists to avoid: (1) **context/cost bloat** — a long-lived session's transcript keeps growing every turn, so a fresh one costs less per turn even with auto-summarization; (2) **self-testing the "cache, not source of truth" claim** — a session that's never rebuilt never actually proves the `.md` files are sufficient on their own, and a rebuild is exactly the mechanism that surfaced two real documentation gaps in this same `tos` session (CARD-0290's incomplete migration, the whole-board-vs-scoped listing miss); (3) **sheds stale intermediate reasoning** — corrected mistakes and abandoned approaches linger in a long session's context even after the docs are fixed, while a rebuild starts from only what's currently true. Not scoped to a specific cadence yet — periodic, judgment-based, the same "don't over-engineer before a real need shows up" discipline as the rest of this practice.

**A component session does not run `CLAUDE.md`'s general Session Start steps unmodified (corrected 2026-09-17, Joseph — this document previously said it did).** Each of the 9 general steps is either scoped to this session's own component(s), run exactly as a general session would, or skipped outright — never blindly run whole-board on top of everything below. This table replaces the general list for a component session; it isn't additional to it:

| # | General Session Start step | Component session treatment |
|---|---|---|
| 1 | `git status --short` for uncommitted changes | **Scoped** — check status only for files under this session's own covered component director(y/ies), not the whole repo. |
| 2 | `kanban-board.md` Build column | **Scoped** to this session's own component tag(s), not the whole board. |
| 3 | `kanban-board.md` cards updated in the last 7 days | **Scoped** to this session's own component tag(s), not the whole board. |
| 4 | Open GitHub PRs (auto-intake pipeline) | **Skipped** — a raw finding's component often isn't identifiable until reviewed; triaging the whole intake queue isn't this session's job. |
| 5 | Auto verify markers (date-based) | **Scoped** to this session's own component tag(s). |
| 6 | Watch for markers (event-based) | **Scoped** to this session's own component tag(s). |
| 7 | Read `tos/JCTsh-Operating-System.md` | **Unscoped** — runs in full, exactly like a general session. Foundational process knowledge (columns, triggers, Engineering Discipline), not a per-component data scan. |
| 8 | Periodic `archive_cards.py` dry-run check | **Skipped** — whole-board file-size housekeeping, unrelated to any specific component. |
| 9 | `/status` device-health check (CARD-0282) | **Scoped** to this session's own covered component(s)/device(s), not the whole fleet. |

**Any card-related request made mid-session, not just the automated steps above, defaults to this session's own component tag(s)** unless Joseph asks for the whole board explicitly (Real miss, 2026-09-17: a "list the open cards" request during the `tos` component session was answered against the whole board instead, because the prior wording only covered the automatic startup sweep, not requests made later in the session). Same default applies to the `/status` check (row 9) for any ad hoc device-health question asked mid-session.

Then, additionally — steps with no general-session equivalent at all, specific to a component session:

1. **Read each covered component's `README.md` in full.** Per `JCTsh-Build-Standards.md` §7.1, `README.md` is the permanent reference — hardware, wiring, known behaviors, current capabilities/limitations — while `CLAUDE.md` is history and design rationale. Read once per resume, not just skimmed for whatever the immediate task is, so a hardware-capability question that comes up mid-session doesn't need rediscovery from scratch. (The real miss this step formalizes: CARD-0226/CARD-0222/CARD-0258, 2026-09-17 — five separate dated notes assumed hiking-monitor could run a debug-UART setup built for a different component, without ever checking hiking-monitor's own `README.md`/`wiring.md`, which would have shown it never had one.)
2. **Read each covered component's `CLAUDE.md` in full.** Current, curated context — design rationale, constraints, gotchas, open threads. As of CARD-0290 this stays genuinely small (archived card history now lives in a separate `card-archive.md` sibling, never appended directly into `CLAUDE.md`), so reading it in full at every resume is actually practical, not just aspirational.

**Not required — stays on-demand:** re-reading every detail doc a `README.md`'s Files table indexes (`wiring.md`, `power-system.md`, `ESP32-project-pins.md`, etc.) at every resume, and — explicitly, per CARD-0290 — each covered component's `card-archive.md`. Those stay read-when-actually-needed: detail docs per the Engineering Discipline rule (`JCTsh-Operating-System.md`) requiring a check before asserting a hardware-capability claim, `card-archive.md` only when a specific historical question actually needs it. Step 2 above is about `CLAUDE.md`'s own curated-context layer being fresh, not preloading every downstream/archival file every time.

**Related:** CARD-0284 (cluster-session origin and end-to-end workflow), CARD-0292 (this document's own version-history split), `JCTsh-Component-Session-Start-History.md` (this document's full changelog), `JCTsh-Session-Card-Selection.md` (the analogous session-behavior document this mirrors in structure), `CLAUDE.md` (general Session Start — always runs first), `JCTsh-Build-Standards.md` §7.1 (README.md's role as permanent reference), `JCTsh-Operating-System.md` (Engineering Discipline section, Auto Verify / Watch For Markers section, Documentation Structure section — the card-archive.md filename standard), CARD-0290 (the CLAUDE.md/card-archive.md split this document was updated for).
