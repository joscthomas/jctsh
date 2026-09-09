# tos/ — Team Operating System

CARD-0191: this directory consolidates JCTsh's "Team Operating System" (TOS) —
the kanban board itself, the process governing how work moves through it, and
the tooling that lets ideas/findings get onto the board from outside a
Claude Code session (voice, email, automated maintenance checks). Before
this, these pieces were scattered across the repo by whichever
infrastructure happened to be convenient to host them on, not by any
conceptual grouping — see CARD-0191 on `kanban-board.md` for the full
before/after inventory.

**Start with `JCTsh-Operating-System.md` for the actual process definition**
(board columns, state-transition triggers, the Build → Done Reflection
requirement, the commit/push relationship). This file is the index of what's
here and how the pieces fit together — it doesn't repeat that content.

## What's here

| File | Role |
|---|---|
| `kanban-board.md` | The board itself — every card, its status, and its full history. |
| `JCTsh-Operating-System.md` | The process definition — columns, triggers, Reflection requirement. Read once per session (see `CLAUDE.md`'s Session Start). |
| `open_kanban_pr.py` | `open_finding_pr()` / `resolve_and_merge()` — opens a placeholder-stub PR against `kanban-board.md` for any finding/idea, and lands a reviewed PR as a real numbered card at merge time. Imported (as a sibling module) by `email-idea-check.py`, `pi-maintenance-check.py`, `maintenance-check.py`, and `hike-izer-orchestrator`'s `/webhook/idea` route. |
| `land_pr_card.py` | Interactive-only script Claude runs (never automated) to land a PR as a fully-interviewed, real card — not just a renumbered stub. See its own docstring for the distinction from `resolve_and_merge()`. |
| `email-idea-check.py` + `.service`/`.timer` | Polls `joscthomas+kbc@gmail.com` every 30 min for `jctsh-idea` emails (CARD-0151), calls `open_finding_pr()` for each. Deployed to the Pi. |

## The auto-PR intake pipeline

Three independent entry points all funnel into the same `open_finding_pr()`,
so a voice-captured idea, an emailed idea, and an automated maintenance
finding all produce identically-shaped placeholder PRs:

```
Tasker "Log Idea" widget ──► /webhook/idea (hike-izer-orchestrator) ──┐
joscthomas+kbc@gmail.com ──► email-idea-check.py ─────────────────────┼──► open_finding_pr()
maintenance-check.py / pi-maintenance-check.py (scheduled findings) ──┘         │
                                                                                  ▼
                                                          Real PR opened against `main`,
                                                          zero file diff (CARD-0190) —
                                                          finding text lives in the PR's
                                                          own title/body only
                                                                                  │
                                                                                  ▼
                                            Claude reviews, then runs resolve_and_merge()
                                            (auto-generated stub) or land_pr_card.py
                                            (real interviewed card) — this is the only
                                            point that actually reads/writes kanban-board.md
```

Nothing writes to `kanban-board.md` except at merge time, and only through
one of the two merge-time functions above — see CARD-0190's card text for
why (`kanban-board.md` crossed GitHub's 1MB Contents API content-size limit
in August 2026; every read of it now uses the `application/vnd.github.raw`
media type instead of the size-limited JSON `content` field).

## Auto verify markers

A separate mechanism from the intake pipeline above — this one's about not
forgetting a follow-up on a card that's already on the board, when the thing
being waited on won't happen until later. Two flavors, one literal keyword
kept deliberately distinct per flavor so each reads naturally in its own
card's prose (CARD-0251):

| Flavor | Marker syntax | For a check that depends on... | Checked how |
|---|---|---|---|
| Date-based | `**Auto verify: <date>**` | a known future date/event (a scheduled reboot, a timer firing) | `CLAUDE.md` Session Start step 4 greps `kanban-board.md`, follows through once the date has passed |
| Event-based | `**Watch for:** <description>` | a real-world condition of unknown future timing (typically a specific log message) | `CLAUDE.md` Session Start step 5 greps `kanban-board.md`, then greps the Pi's durable log (`/mnt/jctsh-logs/jctsh.log*`, including rotated backups) for the stated pattern |

Both flavors exist because the board's own 7-day recently-updated Session
Start check (see `CLAUDE.md`) isn't enough — a card can sit untouched far
longer than that while still genuinely waiting on its marker, and would
otherwise never resurface on its own.

Implemented entirely in `core/logging/log_server.py` (not this directory) —
`_parse_kanban_board()` extracts either marker into the card dict
(`auto_verify`/`watch_for`), `cardHtml()` renders it as a badge on the
card's `/kanban` header, and `render()`'s per-column sort pushes any
marker-carrying card to the end of its column, since it's passively waiting
and doesn't need attention right now. See `kanban-board.md` CARD-0251 for
the full build history, and CARD-0249/CARD-0224 for each flavor's origin
case.

## Deploy

`open_kanban_pr.py` has **no single canonical deployed location** — it's a
plain sibling-import module, so a copy has to sit next to every script that
imports it:

| Deployed copy | Host | Alongside | Redeploy command |
|---|---|---|---|
| `/usr/local/bin/open_kanban_pr.py` | Pi | `pi-maintenance-check.py`, `email-idea-check.py` | `scp tos/open_kanban_pr.py pi@pi1.local:/usr/local/bin/` |
| `/usr/local/bin/open_kanban_pr.py` | M8 | `maintenance-check.py` | `scp tos/open_kanban_pr.py jct@m8.local:/usr/local/bin/` |
| `~/hike-izer-web-app/orchestrator/open_kanban_pr.py` | M8 (Docker) | `hike-izer-orchestrator`'s `app.py` | See `components/hike-izer-orchestrator/README.md`'s deploy section — requires a `docker compose up -d --build orchestrator`, not just an `scp`. |

**Any change to `open_kanban_pr.py` needs all three redeployed**, not just
one — CARD-0190's original fix only redeployed the Docker copy and missed
both `/usr/local/bin/` copies, which stayed broken until CARD-0191 caught it.

`land_pr_card.py` is never deployed — it's run locally from this repo
checkout by Claude, using `credentials.local.md` (gitignored, repo root) for
the GitHub PAT.

`email-idea-check.py` deploys to the Pi as `/usr/local/bin/email-idea-check.py`,
managed by `email-idea-check.service`/`.timer` (`systemctl daemon-reload` after
changing the unit files themselves; a plain code change only needs the script
re-copied and, if `Type=oneshot`, no restart is needed — it just runs fresh on
the timer's next tick).

## Related

- `kanban-board.md` CARD-0191 — the consolidation this directory is the result of, full inventory and reasoning.
- `kanban-board.md` CARD-0190 — the 1MB Contents API bug this whole pipeline had to be redesigned around.
- `kanban-board.md` CARD-0192 — proposed watchdog self-test for this pipeline (not yet built).
- `kanban-board.md` CARD-0193 — kanban board scaling/archival strategy, including why a database was considered and ruled out.
- `kanban-board.md` CARD-0251 — Auto verify markers (date-based + event-based), the follow-up-reminder mechanism described above.
