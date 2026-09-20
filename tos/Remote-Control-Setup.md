# Claude Code Remote Control Setup

**Author:** Joseph C Thomas (JCT), via Claude
**Purpose:** How to actually connect the Claude Android app to a Claude Code session running
on this desktop — CARD-0296 raised this after an initial attempt (2026-09-19) opened the
Android app cold and got a brand-new, disconnected cloud session instead of the desktop one.
**Version:** 1.0
**Version description:** Initial version, written 2026-09-20 from `claude-code-guide` agent
research against Claude Code's own docs (code.claude.com/docs/en/remote-control.md).
**Related:** `tos/kanban-board.md` CARD-0296 (the card this resolves), `tos/Protocol-Placement.md`
(this doc's own placement — "shared by some projects," genuinely universal in this case since
it applies to any project, not just jctsh).

---

## The mechanism: Remote Control

The session runs **locally on this Windows desktop** the entire time — filesystem, tools, MCP
servers, and code execution all stay here. The phone (or a browser at `claude.ai/code`) is
only a remote screen into it, not a separate execution environment.

**Why the Android app created a new session instead of connecting, 2026-09-19:** opening the
app cold, with no Remote Control session active on the desktop, always creates a new
cloud-hosted session. Remote Control has to be explicitly started on the desktop *first* for
the phone to see and connect to that specific session.

## Desktop-side requirements

- Signed into claude.ai with the same account the phone will use (not API-key auth).
- An eligible subscription (Pro, Max, Team, or Enterprise).
- Team/Enterprise only: an organization Owner has to enable Remote Control at
  `claude.ai/admin-settings/claude-code`.
- No custom `ANTHROPIC_BASE_URL` pointed anywhere but `api.anthropic.com`.
- Feature-flag evaluation left enabled — don't set `DISABLE_TELEMETRY`, `DO_NOT_TRACK`,
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, or `DISABLE_GROWTHBOOK`.
- Workspace trust already accepted for the project directory (run `claude` there once first
  if it's genuinely new).

## Starting it on the desktop — three ways

1. **`/remote-control`** typed into an already-running session — carries over that session's
   existing conversation history. This is the one that reaches a session you're *already in
   the middle of*, which is what CARD-0296 actually wanted.
2. **`claude --remote-control`** — starts a fresh interactive session that's remote-reachable
   from the moment it opens.
3. **`claude remote-control`** (server mode) — a standalone, longer-lived server process; see
   "Multiple sessions" below.

## Connecting from the phone

1. Open the Claude app for Android, signed into the same account.
2. Go to the **Code** section.
3. Find the session — a green status dot marks it online.
4. Tap it to connect.

Alternatively, scan the QR code the desktop terminal shows (press spacebar while
`claude remote-control` is running), or open the session URL the terminal prints.

## Multiple sessions

**Yes, more than one session can be remote-controllable at once.** The limit is "one remote
session per interactive Claude Code process," not one per account or device — so running
`/remote-control` independently inside several separate sessions (e.g. this jctsh session in
one terminal window, a separate LogSeq session in another) makes all of them simultaneously
reachable. The phone app's Code section lists every online session at once, by name, and
switching between them is just tapping a different one.

**Server mode** (`claude remote-control`) is a different, heavier option: one server process
manages a *pool* of sessions (default capacity 32, `--capacity` to change it), with a
`--spawn` mode controlling how new ones get created (`same-dir`: share one working directory;
`worktree`: each gets its own git worktree; `session`: single-session, rejects more
connections). Sessions the server created keep running even after the server itself stops,
resumable via `--continue`/`--session-id`.

**For this project's actual scale (a handful of repos — jctsh, LogSeq, PB-Blog, and whatever
comes next), running `/remote-control` independently in each session you want reachable is
simpler than standing up server mode, and already covers "multiple concurrent sessions."**
Server mode is worth revisiting only if that stops being enough (many more concurrent
sessions than a few terminal windows can reasonably hold) — not adopted preemptively, per
this project's usual iterative/incremental discipline.

## Real limitations

- **The desktop process has to keep running.** Close the terminal (or quit the app hosting
  it), and the session goes offline until it's restarted.
- **Can't retroactively enable Remote Control on an already-running session from outside
  it** — either start a session with `--remote-control` from the beginning, or run
  `/remote-control` inside a session that's already open (the path this project actually uses).
- Reconnects automatically after the desktop sleeps or the network drops.
