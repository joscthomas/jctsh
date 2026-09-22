# JCT Smart Home (JCTsh) Team Operating System (TOS)
**Author:** Joseph C Thomas (JCT)
**Purpose:** Defines how the JCTsh team works — the conceptual process governing all work.
**Version:** 1.21
**Version description:** CARD-0325 — the Board Commit Rule: a session commits `tos/kanban-board.md` on completion of its own work, never asking Joseph and never waiting on another session, including whatever in-flight text other sessions have in the file. Rejects the session-scoped lock file this document previously named as "the next lever" (struck in place), rules hunk-level board staging out as mechanically unavailable, and accepts commit-attribution drift as a documented limitation rather than a thing to measure or re-decide per occurrence. Adds the Card ID allocation rule alongside it (allocate late from the file, push serializes, later pusher renumbers, collisions are detectable by one grep) so the one variant that could lose real work is closed mechanically rather than watched for.
**Version history:** `JCTsh-Operating-System-History.md`
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

**Interview first — don't write a card from assumption (CARD-0304).** Ask enough to get real clarity on what the work is, why it's being done, and what "done" concretely looks like before writing anything. That acceptance criteria, once on the card, is the objective definition of "done-done" — it both guides the work and later confirms whether it actually got there. Include explicit non-goals, not just scope: naming what's deliberately excluded (e.g. CARD-0286 ruling out Immich's global Storage Template, CARD-0227's known-gap note) prevents scope drifting back in unnoticed later, and is as much a product of a real interview as the in-scope items are.

**Explicit decisions, never silent defaults (CARD-0304) — the thread connecting several rules elsewhere in this document.** A card doesn't drift into Defer, Retracted, an Accepted-limitation Done, or a Priority tag by default; a person makes that call, and it's recorded on the card. Stated once here rather than only implicitly, four separate times, in the Priority, State Transitions, and Retracting-a-card sections below.

---

## Engineering Discipline

Generalized from `JCTsh-Build-Standards.md` §6.1/§6.3 (CARD-0289 follow-on) — those were framed narrowly around integration code, but the underlying rules apply to any change in this repo, hardware or not:

- **Additive first.** New work is additive by default. Existing behavior, integrations, or automations are never removed or modified without an explicit decision documented in the card or instruction set — wire something new in parallel, don't replace, unless that decision was actually made.
- **Investigate existing patterns first, never assume.** Before writing anything new that touches an existing process, locate and read the relevant existing implementation first — verify, don't guess at how something already works. This explicitly includes a component's own **hardware/physical capability** — before relying on or asserting that a specific component can do something (a pin, a sensor, a debug interface), check that component's own `README.md` and the detail docs its Files table indexes (`wiring.md`, `power-system.md`, `ESP32-project-pins.md`, `perfboard-layout.md`, etc.), per `CLAUDE.md`'s pointer — not a sibling component's build, and not memory. Found live, 2026-09-17 (CARD-0226/CARD-0222/CARD-0258): five separate dated notes assumed a debug-UART setup built for air-quality-monitor could simply be run on hiking-monitor, without ever checking that device's own `wiring.md` — it was never wired for one.
- **Verify a claimed completion directly — don't trust a card's own "Done"/"verified" text at face value (CARD-0304).** Distinct from the rule above: that one is about *new* work not reinventing what already exists; this one is about *existing* claims of already-finished work not actually being checked. Caught twice in one session: CARD-0290 stated "zero Card History headings remain in any `CLAUDE.md`" when two actually did (`hosts/pi1`, `tos` itself); CARD-0258 found a resolved Watch-for marker whose own line was never edited, so the parser kept treating it as still-open indefinitely. A "Done" or "verified" claim is a claim, not a fact, until it's actually re-checked.
- **Measured thresholds over vague judgment.** When a rule needs a cutoff, pull real data before picking the number, rather than guessing at what "too big" or "too old" means. CARD-0193 measured the actual per-card size distribution before setting the 10KB archive threshold; CARD-0292's "concrete trigger, not a vague sense of 'too long'" is the same discipline applied to a document's own version-history.
- **Iterative and incremental — build for the need in front of you, not a hypothetical future one.** Solve today's real case; generalize or add a second lever only once an actual second case shows up, not preemptively. CARD-0193's archive design only added a secondary age-based threshold after the size-primary one proved insufficient on its own; CARD-0256's Backlog cards stay essence-only until Planning actually needs the detail; CARD-0284's cluster-session pilot started with one cluster and no upfront framework, deliberately deferring a naming convention or formal checklist until a second instance actually needed one.
- **Discover implied rules or conventions inherent in how work is actually being done, and explicitly define them in the appropriate place (CARD-0304) — this is a discipline about this document itself, not just about code.** A convention followed consistently but never written down (interviewing before writing a card, verifying a completion claim, requiring an explicit decision instead of a default) is real and binding, but stays vulnerable to being silently dropped or reinvented differently next time until it's actually stated somewhere. The activity that produced most of this section, and CARD-0302's retraction protocol before it, was exactly this — noticing an existing pattern and giving it a real, discoverable home rather than leaving it implicit. Mirrors `JCTsh-Component-Session-Start.md`'s own "promote once proven out" precedent for Auto Verify/Watch For markers and cluster sessions — but that precedent had only ever been *applied*, never stated as its own standing principle that this is how this document is supposed to grow.

`JCTsh-Build-Standards.md` §6.1/§6.3 keep their section numbers as short pointers here, with any hardware/integration-specific specifics that don't generalize.

---

## Where Work Happens: Pre-Card Thinking vs. Tracked Work

**The real distinction is never which tool — chat, a Claude Code session, anywhere — it's whether a card exists yet (corrected 2026-09-18, CARD-0304).** Preliminary thinking and research is informal wherever it happens: feasibility questions, initial ideas, "should we build this at all." This stage does **not** produce planning documents and doesn't correspond to any board column — it's pre-Backlog raw material, not tracked work, no card exists yet, regardless of which surface the thinking happened on.

**The transition point is a decision to build something.** Once preliminary thinking and initial research are done and that decision is made, create a card capturing that thinking and research, placed in **Backlog**. From Backlog onward, everything is tracked work on the card — Planning (including whatever phases or documents the work needs, see Note on Planning below), Design, Build, and Done. Once the card exists, informal pre-card thinking doesn't re-enter the process to produce planning or design documents later — those belong on the card from that point on, wherever the session doing the work happens to be running.

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

A session with a standing, resumed identity dedicated to a specific component or group of components (a **cluster session**, CARD-0284 — e.g. "the hike-izer session") runs a modified version of `CLAUDE.md`'s general Session Start — some steps scoped to the component(s), some skipped, some unscoped, plus component-only steps with no general equivalent — defined in its own document: `JCTsh-Component-Session-Start.md`. Distinct from a general session with no such persistent focus, which only ever runs the general steps unmodified.

---

## Documentation Structure

**Single source of truth — eliminate redundancy on discovery (CARD-0304, found missed from this document despite being confirmed correct in the same conversation that produced the other nine items — see Engineering Discipline's own "verify a claimed completion" principle above, applied here to this document's own claimed completeness).** The inverse of "split by topic" below: when the same fact ends up documented in two places, collapse to one authoritative location and point the other at it — never maintain two copies that can silently drift apart. Found live, CARD-0303: root `CLAUDE.md`'s ESP32 GPIO exclusion list and `JCTsh-Build-Standards.md` §2.6's had already diverged (each missing pins the other correctly excluded) before anyone checked whether the "duplication" was actually a full restatement or had quietly drifted into disagreement. **Merge, don't just delete, when reconciling (added same pass, CARD-0303):** when one copy has more or better detail than the other, fold the richer content into the canonical location before trimming the redundant copy to a pointer — don't delete the sparser fact and lose the richer one just because it happened to live in the wrong file. CARD-0303 merged root `CLAUDE.md`'s fuller MQTT log-category table and its event-time convention (missing from Build Standards entirely) into `JCTsh-Build-Standards.md` §4.2 before trimming `CLAUDE.md`'s copy to a pointer.

**Superseding stale content: mark and strike through, don't silently delete (CARD-0303).** Distinct from single-source-of-truth's "collapse two copies into one" — this is for a document found to contradict *itself* or a policy decided later, not a duplicate-elsewhere case. Correct it visibly: strike through the superseded text and explain why, rather than deleting it outright. A silent deletion erases the evidence the contradiction ever existed — exactly what makes drift like this hard to find the next time. Found live, CARD-0303: `JCTsh-Build-Standards.md` §5's own opening line ("every component... exposed in SmartThings... not deferred") predated and directly contradicted §6.4's later SmartThings-Free policy (CARD-0164) — struck through in place with a note, not removed.

**`README.md` vs. `CLAUDE.md` — what goes in which (stated explicitly for the first time, CARD-0304).** A real, load-bearing distinction applied consistently across this whole session's CARD-0290/CARD-0291 work, but until now only ever stated in root `CLAUDE.md`'s own opening paragraph, never here:
- **`README.md` is the permanent reference** — what a component actually is, right now: hardware, wiring, MQTT topics, integration, known behaviors, current capabilities and limitations (`JCTsh-Build-Standards.md` §7.1/§7.1a).
- **`CLAUDE.md` is curated context** — design rationale, constraints, gotchas, open threads. Kept genuinely small (archived card history lives separately, on-demand only — see the archived-card-history rule below).
Before relying on or asserting a hardware/physical capability, check the component's own `README.md` first, not a sibling's build or memory — see Engineering Discipline above.

**Split documentation by topic and read-frequency, not by minimizing file count.** What gets read every session stays small and central (`CLAUDE.md`, this document); detail that's only needed on demand goes into its own focused file that gets pointed to explicitly, rather than growing in place. A file sized to one topic — small enough to read whole in one pass — beats a large one that has to be sampled or reconstructed piecemeal once it outgrows that (`kanban-board.md` hit this for real, CARD-0193, forcing grep-only access and losing the "read straight through" comprehension a single pass gives).

The cost of splitting is reference-chasing and drift, not file count — so cross-references (`**Related:**` or equivalent) must stay explicit and current, or many small files just become a maze instead of a coherent system. `JCTsh-Build-Standards.md` §7.1a already applies this same read-frequency split at the component-doc level (README vs. CLAUDE.md); this section generalizes it as a repo-wide rule rather than a component-specific one (CARD-0289).

**Archived card history gets its own file, never appended into `CLAUDE.md` directly (CARD-0290).** `CLAUDE.md` is supposed to be curated, actively-useful context (constraints, gotchas, design rationale) — but `archive_cards.py` (CARD-0193) was appending full archived-card text straight into it, unbounded, conflating "current curated context" with "growing historical record" in one file. Same read-frequency-split principle as this section's own rule, just not yet applied at this specific layer until it was actually hit (`components/hike-izer/CLAUDE.md` reached 485KB). Fixed: every component's archived card history now lives in a sibling `card-archive.md` — read on-demand only, never as part of routine Session Start or component/cluster-session startup (`JCTsh-Component-Session-Start.md`) — same relationship `CLAUDE.md` already has to `kanban-archive.md`/`kanban-board.md`.

**Component-doc filename standard, decided 2026-09-17 (CARD-0290, Joseph) — applies regardless of a component's technology** (hardware or pure software, ESP32 firmware or an HA-only automation): **unprefixed by default** — `wiring.md`, `power-system.md`, `card-archive.md`, etc., not `<component>-wiring.md`. A file that's only ever opened from within its own component's directory context gains nothing from repeating the component's name — the path already disambiguates, and it matches the two filenames this convention can't deviate from anyway (`README.md`/`CLAUDE.md`, locked by GitHub/Claude Code convention). **Prefix only when a file is commonly referenced or searched by name outside its own directory context** — e.g. `hiking-monitor-enclosure-plan.md`, `*-claude-code-instructions.md` — generic-enough names that a bare version would be ambiguous the moment it's typed or searched without already being scoped to one component's folder. This existing split was never articulated before now; going forward, apply it deliberately rather than by feel.

**A document's own version-tracking gets split into a sibling `<Doc>-History.md` once it stops being a short header field, decided 2026-09-17 (CARD-0292, Joseph — "put doc version tracking in a separate file and point at it... make this a pattern").** Same read-frequency-split principle as this section's other rules, applied one layer up — to a doc's own changelog, not just its subject matter. `JCTsh-Operating-System.md`'s own "Version description" field had grown into a chain of "Prior version description" entries reaching ~6KB, over 20% of the file, entirely because each version bump prepended new text and kept every prior entry inline rather than ever splitting them out — the exact same unbounded-growth shape as `kanban-board.md` (CARD-0193) and component `CLAUDE.md` files (CARD-0290), one layer up. **Concrete trigger, not a vague sense of "too long":** once a document's version-history content stops being a single-paragraph field and starts reading as a changelog — a real chain of "Prior version description" entries, or (as `JCTsh-Build-Standards.md` already had, structured better from the start) a dedicated version-history table — split it into `<Doc>-History.md`. From that point on, the live document's header holds **only the current version's own description**, never chained prior ones; the history file is the complete record, read on demand only, never part of routine reading. Applied immediately to the three documents that already qualified: `JCTsh-Operating-System.md` (this document, → `JCTsh-Operating-System-History.md`), `JCTsh-Component-Session-Start.md` (→ `JCTsh-Component-Session-Start-History.md`, split proactively before its own chain grew as large), and `JCTsh-Build-Standards.md` (→ `JCTsh-Build-Standards-History.md`, its existing table had reached 14.6KB inside an already-121KB file). `JCTsh-Session-Card-Selection.md` was checked and left alone — its version description is still a single short paragraph, not yet a real problem to solve preemptively.

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

**Retracting a card (formalized 2026-09-18, CARD-0302 — observed convention, never previously written down).** Distinct from **Defer**: Defer means the work is real but consciously parked; retraction means the card itself shouldn't have been opened as its own card — almost always because it duplicates work already tracked elsewhere, found only after the fact (e.g. CARD-0302 duplicating the already-open CARD-0294; CARD-0252/0253 duplicating open threads on CARD-0012). Not a new column — a retracted card's `**Status:**` is **Done**, with the retraction itself named in the title:
1. **Title becomes `[retracted] Folded into CARD-XXXX — was: <original title>`** — replacing the type bracket (`[idea]`/`[bug]`/`[enhancement]`), not adding to it.
2. **Body explains when/why it was opened, then found to duplicate**, and names the real card its findings moved to.
3. **Any genuinely new finding the retracted card surfaced gets folded into the target card as its own note** — not lost just because the card housing it was a mistake.
4. **Kept as a stub, never deleted** — the card number may already be referenced elsewhere (a commit message, a code comment, another card's `Related:` line), and a dangling reference is worse than a short stub explaining where the content actually lives.
5. **A `Related:` line points at the target card.**

**Note on Build:** Build is not Claude Code executing alone. It includes per-step manual work and confirmation by Joseph wherever the work requires it — physical assembly, wiring, flashing, real-world verification — the same Claude Code does / Joseph does / Joseph confirms pattern `JCTsh-Component-Planning-Pattern.md` Phase 5 uses for hardware builds, generalized to any card where a human step is required. "Verification that everything works correctly" means the change is live and confirmed working — deployed, tested, observed — not merely edited locally. A card with outstanding deployment, manual, or verification steps stays in Build with those steps noted, rather than moving to Done prematurely. **Live/real verification beats synthetic or inferred confidence (CARD-0304).** A synthetic test, a code review, or "it should work" is a useful intermediate step, never a substitute for the real thing — this is the entire reason Auto Verify/Watch For markers exist (below): to hold a card open until the actual real-world condition is observed, not close it on inferred confidence instead. **Documentation captures reality as it goes** (generalized from `JCTsh-Build-Standards.md` §7.5, CARD-0289 follow-on): instructions get updated with actual findings during the work itself, not just original intentions, and a deviation from the plan is documented immediately when discovered — not deferred to the Reflection step below.

**Plan, as-built docs, and the card are three different things — keep journey-noise out of as-built docs (clarified 2026-09-18, CARD-0304).**
- **The plan** — original intention, what Planning/Design produced before Build started. Stays as-is once Build finishes; it is what it was, never cleaned up or rewritten retroactively to match how things actually turned out.
- **As-built docs** (`README.md`, wiring/current-state references) — describe what *is*, right now, cleanly. Once built, these should read as if it were always this way, not carry "originally we tried X, then Y" narrative.
- **The card** — the journey from plan to as-built: what was tried, what changed, why, the messy part. This is where that history belongs, and the only place it belongs. The "Documentation captures reality as it goes" note above is about keeping the *plan/instruction-set* from going stale during Build — a different, still-correct point from this one, which is about not letting that same journey narrative leak into the *as-built* reference doc once the work is done.

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

**Format and ordering (added 2026-09-17, Joseph, CARD-0288 follow-on) — always applied, not just when prioritization is explicitly asked for.** Present the visible list (marker-hidden cards already excluded per above) as a table — columns ID, Status/column, Title — never a flat bulleted list. Row order combines both of this project's ordering concepts, which govern different axes and previously had no stated interaction:
1. **Priority tier first** (`JCTsh-Operating-System.md`'s Priority section: Critical → High → Medium → Low → unset/no tag) — the coarse grouping.
2. **`JCTsh-Session-Card-Selection.md`'s four ordered factors, within each tier** (actionable-now vs. blocked, whose-job, already-scoped, bugs-before-enhancements tiebreaker) — the fine-grained order inside a given priority tier.

This doesn't reopen CARD-0288's original "severity/bug-vs-enhancement wasn't weighed" scoping — that was about which card a session picks up *next*, a different question from how a requested listing gets *displayed*. Priority becomes load-bearing only for this display ordering, not for selection itself.

**Related:** CARD-0251 (origin, both marker flavors), CARD-0258 (found and fixed the resolution gap this protocol formalizes, and raised the listing convention above), CARD-0224/CARD-0276 (the status-vs-marker correction), CARD-0288 (Session Card Selection, combined with Priority for this table/ordering rule), `core/logging/log_server.py` (`_parse_kanban_board()`, the badge-rendering parser both flavors share).

---

## Observed Exception: Skipping Design

In practice, several cards move directly from Planning to Build, skipping Design as a distinct column. This happens when Planning (in Claude Code, per `JCTsh-Component-Planning-Pattern.md`) already produces an approved execution plan or Claude Code instructions as part of Planning itself — at that point the Design → Build trigger's criteria are already satisfied, so the card just starts in Build rather than sitting in an empty Design column for form's sake. `kanban-board.md` notes this explicitly on cards where it happened (e.g. CARD-0003, CARD-0034) rather than silently skipping the column.

---

## Applying TOS to Pre-Existing Work

TOS did not exist when most of the cards currently in `kanban-board.md` were worked. Older cards that don't cleanly match a single column — e.g. a card whose Design deliverable (Claude Code instructions) is already complete while it still sits in Planning — aren't inconsistencies to fix. They're history that predates the process which would have produced a cleaner state. This is process improvement, not a correction owed to past work.

Reconciling any specific older or in-flight card against TOS — moving it to the column it actually belongs in, retroactively producing a missing artifact — is a **per-card judgment call** based on whether doing so adds real value, not a blanket retroactive mandate to sweep the whole board into compliance.

---

## Concurrent Sessions

Moved here from root `CLAUDE.md`, CARD-0303 — pure team-workflow policy (would still make sense in a repo with no hardware or code), previously homeless in the document meant to own this category. Multiple Claude Code sessions (or the user directly) may edit files in this repo at the same time. Git has no file-locking or checkout-exclusivity model (unlike SVN/Perforce) — two sessions sharing this working directory get no automatic protection against clobbering each other.

The real risk is **staleness between reading a file and writing it back**, not how long a file stays "open" (tool calls never hold a file open across turns). Practices:

- **Reread reactively, not preemptively (CARD-0283, 2026-09-17).** Don't reread a shared file fresh before every single edit as a blanket precaution — that's a real, continual cost paid regardless of whether any other session actually touched it. Instead, attempt the edit against the content already in hand; `Edit`'s own exact-string match already fails safely if another session changed that text in the meantime. Only reread (the affected section, then retry) when an `Edit` call actually fails due to a stale match. Same safety guarantee as a preemptive reread — a stale write still can't silently clobber another session's change — without the wasted round-trip when there was never any real contention. ~~If this stops being enough (e.g., genuinely frequent concurrent multi-session activity on `tos/kanban-board.md`), the next lever is a session-scoped lock file claimed once per multi-edit pass rather than per edit — not adopted yet.~~ **Superseded 2026-09-22 (CARD-0325): the triggering condition was met — four sweeps, three of them in one morning with four cluster sessions live — and the lock file was examined and rejected.** Nothing was ever clobbered in any of the four; `Edit`'s exact-string match held every time. The problem is commit *timing*, not concurrent writing, so a lock would serialize four sessions to solve a problem that has never once cost content. Board Commit Rule below instead.
- **Never `git add -A` or `git add .`** — always stage specific files/paths. A blanket add is what sweeps up another session's unrelated, held-back edits and creates real collisions. Confirmed as a live risk, not just theoretical, CARD-0303: a `tos`-scoped rename got swept into a concurrent hike-izer session's own commit this way.
- **Prefer Edit over Write for shared files.** Edit's exact-string match fails safely if the content changed underneath you; Write blindly overwrites whatever is on disk.
- **Board Commit Rule — commit on completion, never ask, never wait (CARD-0325, 2026-09-22).** Commit `tos/kanban-board.md` as a whole — a card closing, a card added, meaningful progress — never surgically split per card. When a session finishes a bounded piece of work it stages its own files by name plus the board, commits, and pushes **immediately: without asking Joseph, and without waiting on any other session.** Four consequences, all deliberate:
  1. **Never attempt hunk-level staging of the board.** Unavailable, not merely discouraged — cards are appended at the same top edge, so one session's new card and another session's edit to the card just below it land in a single indivisible diff hunk (CARD-0325, instance 4, tried and failed twice).
  2. **If the board carries another session's in-flight card text, commit it too** and add the trailer `Board also carries in-flight edits from another session.` No session holds its own finished work hostage to another session's timing.
  3. **Attribution drift is an accepted limitation, decided once so it stops being re-litigated.** A card's work landing under another card's commit message costs nothing real here: the card itself is the record of what happened, `git log` is a secondary index, and nothing deploys from `origin/main`.
  4. **No instance log and no instrumentation.** The four sweeps behind this rule are recorded on CARD-0325 as its evidence; from here the cost is simply accepted, and an accepted cost doesn't get measured (Joseph, 2026-09-22: "why do we need to keep a log file?").
- **Card ID allocation — allocate late, let the push serialize it (CARD-0325, 2026-09-22).** The `<!-- next-card-id -->` marker is a convenience, not a lock: three sessions claimed CARD-0322 through CARD-0328 within ~45 minutes on 2026-09-22. Four mechanical steps make that safe without any coordination:
  1. **Take the number immediately before writing the card**, from the file itself — `max(CARD-nnnn)` in `tos/kanban-board.md`, with the marker as a cross-check — never from a number read earlier in the session.
  2. **Write the card and bump the marker in the same edit**, then commit and push right away per the Board Commit Rule above. The push is the serialization point.
  3. **If that push is rejected as non-fast-forward**, pull, then re-check your own number. If another card now holds it, **renumber your own card** — later pusher yields — and fix its cross-references before pushing again.
  4. **A collision is trivially detectable**, so it never needs watching for: `grep -oE "^### CARD-[0-9]{4}" tos/kanban-board.md | sort | uniq -d` prints nothing when healthy. Verified empty 2026-09-22 across the board and every archive; the repeats that check finds *between* files are archived copies of one card, not two cards sharing a number.

- **Reserve `git worktree` / branch isolation for the narrow case of two sessions actively rewriting the *same* file at the same time** — it's not a default. Isolating a session onto its own branch means its work is invisible to anything reading `main` directly (e.g. the live kanban page pulled from `main` on GitHub) until an explicit merge, which is unnecessary overhead when sessions are touching disjoint files.

---

## Relationship to Commit / Push

Separate from board state, but adjacent to it. The **card**, not any git mechanic, is the organizing concept — a file getting staged (`git add`) isn't a meaningful state of its own, just the mechanical step that tells git which files belong to the next commit.

| Concept | What it is |
|---|---|
| **File creation/modification** | The result of working a card — a card's work produces some set of created or modified files on disk |
| **Commit** | Taking that file set (the card's work product) and recording it into local `.git` history. Not strictly before or after Done — the commit is the action that *enacts* the Build → Done transition. It requires Build's criteria (implementation, verification, reflection) to be satisfied first, and typically includes the `kanban-board.md` edit moving the card to Done with its Resolution note in the same atomic commit |
| **Commit note** | Ties back to the card that defines the work, so history reads as "which card produced this snapshot," not just a list of file diffs |
| **Push** | A backup checkpoint, not a release — nothing deploys from `origin/main` itself (devices/servers are updated via their own explicit step: scp, OTA, a deploy script, verified live before the commit that represents it), so a push just copies already-verified history to the remote. There is no release management here at all. |

**`tos/kanban-board.md` is never a judgment call (CARD-0325, 2026-09-22).** A session that stops to ask Joseph whether or when to commit the board is violating this document, not being careful — deciding commit timing is not his job, and four sessions each raising it separately is the failure mode this rule exists to end. Condition 1 below is satisfied by definition for a board edit the session was already authorized to make; see the Board Commit Rule in Concurrent Sessions above for the mechanics.

**When commit/push happen without a separate ask (established 2026-09-18).** The general principle lives in the user's global Claude Code preferences (a cross-project practice, not specific to this repo); this is that principle's concrete shape in this repo. Both conditions must hold:
1. **The commit represents no judgment call Joseph hasn't already seen** — either he gave an explicit go-ahead on the finished work, or a card's own interview made the approach unambiguous and he separately authorized *doing* the work. Scoping a card and authorizing its execution are two different gates (see the Retracting-a-card note above's own CARD-0302 history for why this matters) — collapsing them isn't what this rule permits.
2. **It's not runtime/production code** — firmware, deployed scripts, anything where a bad commit changes real device/service behavior. That still gets a real offer-and-wait; only documentation, `tos/kanban-board.md`, and similar non-executing changes qualify.

Push follows automatically once a commit is made this way — it carries no risk beyond the commit itself (this repo has no CI/CD triggered by `push`). Still always ask before force-push, history rewrites, or `git add -A`/`.` on a repo with another session's uncommitted work — none of those are covered by this rule regardless of how well-authorized the underlying task is.

**Real incident this rule already had to account for:** a CARD-0291 fix (renaming `netalertx-README.md`) was staged but landed inside a concurrent hike-izer session's own commit instead of this one, because that session's own `git add` swept it up — the risk a blanket add poses to another session's held-back work, not something this commit/push rule changes.

See the user's global Claude Code preferences for the general cross-project version of this practice.
