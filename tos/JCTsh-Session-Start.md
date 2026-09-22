# JCTsh Session Start

Read this at the start of every Claude Code session in this repo, before doing anything
else — every session, not just the first time, same as `JCTsh-Operating-System.md`.

**This list is for a general session.** A component/cluster session (CARD-0284 — a session
with a standing identity dedicated to specific component(s)) runs a modified version instead,
not this list unmodified plus extras — see `JCTsh-Component-Session-Start.md`'s per-step
table for exactly which steps below get scoped, skipped, or run as-is.

1. **`git status --short` for uncommitted changes to tracked files, especially
   `tos/kanban-board.md`.** A prior session can leave real edits sitting in the working tree
   without ever running `git commit`/`git push` — invisible to git history, but still capable
   of silently going stale, getting lost, or (as happened live, 2026-09-17) causing a later
   `git pull` to abort once some other change lands on `origin/main` first. If anything shows
   up, summarize it to Joseph and ask how to handle it (commit now, stash and reconcile, or
   discard) before doing anything else that touches git — don't assume it's safe to ignore or
   work around silently.
   **Also `git fetch` then `git branch -r --no-merged origin/main`, checking for remote
   branches with real, complete work sitting unmerged (CARD-0310).** A mobile/cloud session
   can commit and push finished, even Done-marked work to its own branch without ever merging
   it back to `main` — found live 2026-09-19: CARD-0309 was built, verified, and marked Done
   entirely on a branch (`claude/pr-review-handling-t5b3ck`) that nothing merged, undiscovered
   until a routine `git fetch` happened to reveal it. **Exclude the auto-generated
   `maintenance-alert/*` branches** (CARD-0128's intake pipeline) — those are expected to sit
   unmerged until reviewed via `tos/pr-review-checklist.md`, not a sign of anything missed.
   Anything else found is exactly this check's target: summarize it to Joseph, and if it looks
   complete and Done, merge it in (checking for conflicts against any local work first, same
   care as reconciling uncommitted local changes above) rather than leaving it stranded.
2. The Build column of `tos/kanban-board.md` — what's actively in progress.
3. Any card in `tos/kanban-board.md`, in any column, that's been updated in the last 7 days —
   catches recently-Done or recently-touched Backlog/Planning cards that Build alone would
   miss. Cards in this project consistently carry an explicit date in their title or body
   (`Raised`, `RESOLVED`, `verified`, `Built`, etc.) — scan for those rather than relying on
   file mtime or git blame, since a single edit to `tos/kanban-board.md` often touches many
   cards' surrounding text at once and would make every card look recently modified.
4. Check for open GitHub PRs on the `jctsh` repo (`gh pr list` if available, otherwise the
   GitHub REST API — see `tos/open_kanban_pr.py`, CARD-0128). These are
   auto-opened maintenance findings (container-image updates, firmware, etc.) with a
   `CARD-XXX` placeholder title, not yet merged into `tos/kanban-board.md`. Summarize what's
   open and ask Joseph what he wants to do with them — don't merge or close any without
   his go-ahead. **Exception: never surface the `jctsh-pr-selftest` PR** (CARD-0192's daily
   self-test of this same intake pipeline) — a PR from that component existing at all is a
   successful test result, not a finding needing a decision, and it closes itself
   automatically on the next day's run. Skip it from the summary entirely. See
   `tos/pr-review-checklist.md` for the step-by-step review/handling procedure once Joseph
   says how he wants a given PR handled.
5. **Auto verify markers (date-based) — check for any card carrying an `Auto verify: <date>`
   marker whose date has already passed (CARD-0249, CARD-0251).** These mark a verification
   step that couldn't be done live at write time — usually because it depends on a future
   external event (a scheduled reboot, a timer firing, etc.) — and exist specifically because
   step 3's 7-day recently-updated window isn't enough: a card can sit untouched for longer
   than 7 days while still waiting on its marked date, and would otherwise never resurface.
   `grep -n "Auto verify:" tos/kanban-board.md`; for any hit whose date has passed, follow
   through on that card's own stated check (SSH/API/dashboard, etc.) and update the card with
   the result before moving on to other work. This check runs every session regardless of the
   7-day window above — a card can sit for months past its date and must still be caught.
6. **Auto verify markers (event-based) — check for any card carrying a `Watch for:` marker
   (CARD-0224, CARD-0251).** Same family as step 5, but for a verification that depends on a
   real-world event of *unknown* future timing — no date to wait for. `grep -n "Watch for:"
   tos/kanban-board.md`; for any hit, grep the Pi's durable log for the stated pattern —
   `ssh pi@pi1.local "grep -l '<pattern>' /mnt/jctsh-logs/jctsh.log*"` (check every
   rotated backup, not just the live file — `jctsh.log` rotates at 1MB/5 backups, so an
   old occurrence can already have rolled into `.1`/`.2`/etc.). If found, follow through
   on that card's own stated resolution and update it before moving on. This runs every
   session, unconditionally — there's no date to gate it on, so skipping it is the only
   way it'd ever be missed.
7. `tos/JCTsh-Operating-System.md` — the process definition governing how work moves through
   the board (columns, state-transition triggers, the Build → Done Reflection requirement).
   Read this once per session alongside the board itself, not just the first time. It points
   to `tos/JCTsh-Session-Card-Selection.md` — the four ordered factors for choosing which card
   to pick up next (CARD-0288) — apply that by default when deciding what to work on. **If
   this session has a standing, resumed identity dedicated to a specific component or cluster
   of components** (a cluster session, CARD-0284 — e.g. "the hike-izer session"), it also
   points to `tos/JCTsh-Component-Session-Start.md` — extended startup steps beyond this list,
   scoped to that component/cluster (read its `README.md`/`CLAUDE.md`, check its own
   component-tagged cards specifically). A general session with no such persistent focus
   doesn't need this extra step.
8. **Check whether `tos/kanban-board.md` needs archiving (CARD-0193).** `archive_cards.py` is
   deliberately manual, not on a timer — so nothing else will notice if the file has grown
   large again. If it's been a few weeks since the last archiving pass, or the file feels
   noticeably large/slow to work with, run `python tos/archive_cards.py` (dry run) and offer
   to `--apply` if it finds a meaningful number of eligible cards. Don't run this every single
   session reflexively — it's a periodic check, not a per-session action.
9. **Examine the JCTsh Log Dashboard (`http://pi1.local/`, Basic Auth user `jctsh`) for system
   problems or data issues.** Scan recent entries across components for `Alert`-category
   messages, error-shaped `System`/`MQTT` messages, or anything that otherwise looks wrong
   (missing/gappy data, an unexpected reboot, a component gone silent) that isn't already
   covered by steps 5/6's targeted marker checks above. Summarize anything notable to Joseph
   rather than acting on it unprompted — this step is a general health scan, not a substitute
   for the specific Auto verify/Watch for lookups. **For "is component X actually alive right
   now," check the live `/status` page, not a raw-log grep (CARD-0282).** `jctsh.log*` only
   gets a line written after a flush trigger (a state change, 15 minutes, or another message)
   — it can look silent for months while the device is actually fine, the exact false alarm
   CARD-0281 hit. `/status` reflects real, current per-component connection/freshness state
   directly; use the raw log for "what did component X say recently," not "is it alive now."
   **The freshness/connection check itself needs no credential (CARD-0330) — `/status.json`
   is a separate, unauthenticated endpoint returning just per-component `freshness`/
   `connection`/`last_seen`, no log content.** The rest of this step (scanning for `Alert`
   messages and anything else that looks wrong) still needs the authenticated `/status`/`/log`
   dashboard — `DASHBOARD_PASS` isn't something a session can pull non-interactively (Claude
   Code's own credential-materialization guard blocks reading it from the Pi's env file or
   curling the authenticated endpoints), so ask Joseph for it when that fuller scan is
   actually needed, rather than treating a blocked attempt as something to work around.
   A general session scans `/status` across every device; a component session (per
   `JCTsh-Component-Session-Start.md`) scans it for its own covered component(s) only.

**How to get that time of day — verified 2026-09-22 09:56 MST, because the obvious method is broken on this workstation.**

| Source | Verdict |
|---|---|
| `date` (bare, in the Bash tool) | **Correct — use this.** Verified against the Pi to the second: both read `10:08:13` MST. The `USMST` label is a POSIX `TZ` string, not a malfunction. |
| `TZ=America/Phoenix date` | **Broken — never use.** Returns **UTC**, because `/usr/share/zoneinfo/` does not exist in this environment, so glibc silently falls back to UTC while `%Z` still prints the zone name you asked for. That combination — right label, wrong time, no error — is what makes it dangerous. Confirmed live: `17:08:13` returned when the true local time was `10:08:13`. |
| `date -u` | Correct, but it's UTC — subtract 7 for MST, or just use bare `date`. |
| `git log --date=format-local`, PowerShell `Get-Date`, `ls` mtimes, the Pi's own `date` over ssh | All correct, all agree with bare `date`. |

**Real damage, both directions, on 2026-09-22.** CARD-0219 carried a `18:46 MST` Build-progress stamp that was actually `11:46 MST` — written via the broken `TZ=` path, exactly 7 hours ahead (found and fixed by the porch/patio session, `1c5fef2`). Separately, three stamps on CARD-0291/CARD-0325/CARD-0328 were **estimated forward instead of read at all**, landing 10–25 minutes ahead of the commits carrying them (found and fixed by the `tos` session). **So both failure modes are real here: a tool that lies, and not consulting the tool.** The diagnosis also went wrong on its first pass — the skew was initially reported as "bare `date` returns UTC labelled MST," which is the opposite of the truth and would have had sessions subtracting 7 hours from correct stamps. Verify against the Pi before acting on any claim that the clock is wrong.

**When a stamp is already written and its accuracy is in doubt, the commit that carried it is the ground truth** — `git log --date=format-local:'%Y-%m-%d %H:%M' <sha>`. A card's own prose can drift; a commit timestamp can't.

**Every timestamp written into `tos/kanban-board.md` (`Raised`, `RESOLVED`, `verified`, `Built`,
`Decided`, status-line dates, anywhere else a date gets stamped) MUST include a time of day,
local Phoenix time (`America/Phoenix`, MST, UTC-7, no DST) — e.g. `2026-08-03 14:32 MST`, never
just `2026-08-03`. This has had to be corrected multiple times because a bare date is easy to
default to mid-sentence — treat a date with no time as a formatting error to fix before writing
it, not a style choice.
