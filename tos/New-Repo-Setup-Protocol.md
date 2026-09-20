# New Repo Setup Protocol

**Author:** Joseph C Thomas (JCT), via Claude
**Purpose:** The repeatable procedure for moving a distinct personal content domain
(currently living as a plain, unversioned folder) into its own dedicated git repo under
`Projects/` — extracted from CARD-0297 (LogSeq) and CARD-0298 (Pastor Ben blog), the two
real instances that established this pattern, so the next one (e.g. CARD-0317, Bible study
content) doesn't rediscover the same lessons from scratch.
**Version:** 1.1
**Version description:** Added a top-level "Confirmation gates" section and strengthened the
`.gitignore` step (CARD-0317, 2026-09-20) — executing this protocol on a real third instance
still skipped two things it already documented (visibility, card-migration confirmation) and
one it hadn't (`.gitignore` as an explicit decision, not a silently-droppable step), because
they were folded into the same general "yes, build this" that authorized the whole card.
Writing a rule down once wasn't enough to survive contact with a real "just do it" instruction
this same session already gave for the mechanical work.
**Related:** `Protocol-Placement.md` (this doc's own placement — "shared by some projects,"
interim home in jctsh's `tos/`), `Portable-Kanban-Template.md` (used in step 8), CARD-0297,
CARD-0298 (the precedent), CARD-0301 (created `Projects/` itself and the portable template).

---

**Scope:** a distinct content domain — one person's blog, notes system, or similar — that
belongs in its own repo rather than folded into jctsh or another existing one. Not for a new
jctsh component (that's `JCTsh-Component-Session-Start.md`'s territory instead).

**Confirmation gates — these need their own explicit yes, never inferred from a general
"create the repo" go-ahead (added 2026-09-20, CARD-0317's real miss — both of these were
already written into steps 1 and 8 below, and still got skipped in practice: visibility was
assumed private from precedent instead of asked, and CARD-0317's content got moved into the
new repo's board before Joseph confirmed that specific move, not just the repo's creation).
A general "yes, build this" authorizes the mechanical steps; it does not answer these two on
its own:**
1. **Visibility** (step 1) — ask every time, even when every prior instance came back
   "private." A strong pattern is not a decision already made for the next one.
2. **Migrating an originating card's content into the new repo's board** (step 8) — a
   separate ask from "create the repo," not bundled into it.

## 1. Interview before touching anything

Don't assume the folder everyone's been calling "the LogSeq folder" (or equivalent) is
actually the live one — **CARD-0297's original scope named the wrong folder**, a stale
10-month-old copy, discovered only by checking file-modification recency directly rather
than trusting the obvious path. Ask:
- What does this content actually consist of, in enough detail to know what "done" means?
- **Is it actively synced or written to by something already** (a sync service, another
  device, an app with its own file-watcher)? If yes, that service's own safe-relocation
  procedure has to be handled before any move (see step 4) — this is the single highest-risk
  question in the whole protocol.
- Privacy/visibility — private by default for personal content; ask directly rather than
  assume, but expect "private" for anything with names/photos/journal content in it.

## 2. Secrets sweep, before any `git init`

Two passes, not one:
1. **Targeted** — `grep -rlIi "api[_-]?key|password|secret|token|bearer|AKIA[0-9A-Z]|-----BEGIN.*PRIVATE KEY"` restricted to code/config extensions first (`.md .txt .php .json .yaml .yml`).
2. **Broad** — the same pattern with no extension filter, across every file type, right before
   the actual `git add -A`/commit. CARD-0298's real find (two old `wp-config.php` backups with
   a live DB password and all 8 WordPress auth/nonce salts, sitting inside ordinary-looking
   date folders) would NOT have been caught by a scan that assumed only "config-looking" files
   could hold secrets.

**Every hit gets its actual matched line read before being called real or a false positive**
— don't conclude from the keyword match alone. Both repos had real false positives (a
Skill doc's prose mentioning "Application Password," "bearer" matching inside "image
bearers of God") that a keyword-only tool would have wrongly flagged forever.

If something real turns up, that's Joseph's call, not an assumed default — ask whether to
delete outright, exclude via `.gitignore`, or (if it's a live credential) rotate it
independent of anything git-related.

## 3. Cruft cleanup — enumerate and confirm before deleting, never silently

Real categories found across both repos: OS thumbnail/metadata cache (`Thumbs.db`,
`.picasa.ini`, `desktop.ini`), office-app lock/temp files (`~$*`, `*.tmp`), and whole
autosave folders (Corel `Auto-Preserve`). For each category: **find every instance, total
their size, and get an explicit yes before deleting** — this surfaced real numbers worth
seeing before commit (149 files/5.2MB in one pass, another 149 files/11.6MB in a second pass
that only turned up once actual `git add` staging surfaced them). Don't assume one cleanup
pass caught everything; a second check right before the initial commit is normal, not a sign
something went wrong the first time.

## 4. If a sync service is involved, research its procedure — don't guess

LogSeq Sync's safe relocation ([discuss.logseq.com](https://discuss.logseq.com/t/how-to-move-local-directory-of-a-sync-ed-logseq-graph/29533))
turned out to be: unlink the graph in-app, move the folder, then re-link from the new
location — a real, documented, three-step procedure, not something to improvise. If this
domain's content is synced by anything (a note-taking app's own cloud sync, a photo
service, etc.), find that service's own documented safe-move procedure via web search
before moving a single file. Verify afterward with a real round-trip test (LogSeq's case:
write a test file, confirm it actually synced) — don't just trust that it probably worked.

## 5. Decide the final location — check for a backup-service conflict *before* moving

A folder that's about to be both git-tracked and (possibly) sync-service-tracked can also
collide with a third layer: whole-machine backup software (Google Drive for Desktop, in
this case) watching the same parent folder. If the destination sits inside something already
being backed up wholesale, that's three independent write-agents on the same files — real
risk of write contention, not theoretical. Check what's currently backed up before deciding
the final path, not after — CARD-0297 had to redo an entire move because this wasn't checked
first. If a proven-excluded sibling location already exists (e.g. a folder literally named
"not synced"), prefer reusing it over fighting a backup tool's UI to carve out an exception.

## 6. Physical move — Joseph does it

A move at this scale reliably gets blocked by Claude Code's own auto-mode safety classifier
("Irreversible Local Destruction") — don't spend time working around that; it's a real
guardrail, not a bug. Joseph does the actual move (and any step-4 unlink/relink), Claude
verifies immediately after from the new location: content present, old location empty (or at
least this specific subfolder gone, siblings untouched), correct size, and — if it was
already a git repo somehow — `git status`/`git remote -v` unaffected.

## 7. `git init`, `.gitignore`, initial commit

`.gitignore` categories, in order of how often they've actually mattered:
1. Whatever step 3 just cleaned out (so it doesn't silently reaccumulate).
2. **The source app's own internal backup/versioning state**, if it has one (LogSeq's
   `logseq/.recycle/`, `logseq/bak/`, `logseq/version-files/`) — redundant once real git
   history exists.
3. **Pure sync-transaction/counter files that carry no real content** but get rewritten on
   every sync write (LogSeq's `graphs-txid.edn` — just a graph ID + client ID + an
   ever-incrementing number). Tracking these means `git status` shows something "changed"
   almost anytime you check, with zero actual information in the diff. This is easy to miss
   at initial-commit time and only becomes obvious once the repo is live — check for it
   deliberately, don't wait to notice the annoyance.

If the source folder already has its own stray `.git` (an app's internal versioning
pointer, unrelated to the new repo), confirm with Joseph it's safe to replace (check it has
no remote / no real commits first) before running `git init`.

**Decide `.gitignore` explicitly even when nothing obvious applies — don't just skip the
step (CARD-0317's real miss: a repo with no migrated folder and no sync tool had no obvious
candidate, and the step got silently dropped rather than consciously ruled out).** "No
`.gitignore` needed yet" is a legitimate outcome of this step; arriving there without
noticing the step existed is not.

## 8. Bootstrap `kanban-board.md`

Copy `tos/Portable-Kanban-Template.md` in, delete its own purpose/exclusion preamble, and
title the board after the new repo. If any jctsh cards already exist that are genuinely
about this new domain (tagged `[tos]` "until the repo exists," per the established
convention) rather than about jctsh itself — move them here, retaining full content, not
paraphrased, and **retract them in jctsh with a stub** pointing to their new home (`[retracted]
Moved to <repo>'s own kanban-board.md as CARD-XXXX — was: <original title>`). Ask Joseph
before doing this move, don't assume it — it's easy to get ahead of an explicit go-ahead here.

**No `/kanban` board adjustment needed for the retraction itself** — `log_server.py`'s
`_KANBAN_STATUS_RE` only recognizes `Backlog`/`Planning`/`Build`/`Done`/`Defer`; a card
with `**Status:** Retracted` is silently skipped from every column by existing, documented
design (not an error), so it correctly disappears from the live board with zero code
changes. Worth a quick actual check of the live `/kanban` page after the move anyway — this
is what's *supposed* to happen, not a substitute for confirming it.

## 9. Write `README.md`

Cover: what this content actually is (in Joseph's own words where he's given them, not a
guessed paraphrase), this repo's role relative to any existing sync/workflow it's not
replacing, why it lives at its specific path if that's non-obvious (step 5's conflict, if
any), a structure table, and the session note from step 11.

## 10. Private GitHub repo, push

`gh repo create <name> --private --source=. --remote=origin`, then push. Confirm visibility
afterward with `gh repo view <owner>/<name> --json visibility` — don't assume the flag took
effect silently.

## 11. Session-separation note

Add a line to `README.md`: this repo's work happens in its own dedicated Claude Code
session, not scoped under any jctsh component/cluster session (`JCTsh-Component-Session-Start.md`'s
registry is explicitly jctsh-only — a separate personal repo doesn't get a row there).

## 12. Close out the originating jctsh card

Full summary on the jctsh card that tracked this move: what was found (the interview
answers, any wrong-assumption corrections), what was cleaned up (with real counts), what got
built, verification results, and a pointer to the new repo. This is the historical record —
the new repo's own `README.md`/`kanban-board.md` don't need to repeat it.

## Done-when checklist

- [ ] Interview questions (step 1) answered, not assumed
- [ ] Both secrets-sweep passes run, every hit's actual content read
- [ ] Cruft enumerated, sized, and confirmed before deletion (checked again at final staging)
- [ ] Sync-service relocation researched and verified with a real test, if applicable
- [ ] Backup-conflict check done before finalizing the destination path
- [ ] Repo moved, `git init`, `.gitignore` covers all three categories in step 7
- [ ] `kanban-board.md` bootstrapped; any migrated jctsh cards retracted there with stubs
- [ ] `README.md` written, including the session-separation note
- [ ] Private GitHub repo created and confirmed private, pushed
- [ ] Originating jctsh card closed with a full summary
