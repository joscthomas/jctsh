# Tasker setup — TOS

CARD-0241: build procedure for TOS-domain Tasker tasks, split out of
`components/hike-izer-orchestrator/README.md`. `/webhook/idea` is hosted
in that container purely for infrastructure convenience (a free public
HTTPS endpoint, per CARD-0191's own inventory) — it's not a hiking
feature, it feeds kanban card creation (`open_kanban_pr.open_finding_pr()`,
see `tos/README.md`), so its build guide belongs here instead.

## Log Idea (voice-capture idea intake)

CARD-0173. Mirrors "Log Observation"'s original design exactly
(`components/hiking-monitor/hiking-monitor-claude-code-instructions.md`,
Step 24) — a manually-tapped home-screen widget, not an event-triggered
Profile (there's no external event to fire on here, this only ever
starts because you tapped it). Calls
`hike-izer-orchestrator`'s `/webhook/idea` route — see that component's
`README.md` for the payload/response contract.

**1. Create the Task** — Tasker → Tasks tab → **+** → name it `Log Idea`:

1. **Action 1 — Get Voice:**
   - Title: `Speak your idea`
   - Output Variable: `idea_text` (Get Voice actually stores its result in
     `%VOICE` regardless of this field — same quirk Step 24 already
     documented for "Log Observation")

2. **Action 2 — Stop if no input (user cancelled):**
   - Search for **Stop**
   - Condition: `%VOICE` **Is Not Set**
   - Error checkbox: **unchecked**

3. **Action 3 — HTTP Post:**
   - Method: `POST`
   - Server:Port: `https://hikes.jctnet.com`
   - Path: `/webhook/idea?key=G3sOgsf6Ly5N9XwYN2cb1r0qokkHkmug`
     (`WEBHOOK_SECRET` from `credentials.local.md` — same key `hike-end`
     already uses, one shared secret across every route on this webhook
     receiver, not a separate one per endpoint)
   - Headers: `Content-Type: application/json`
   - Body: `{"text":"%VOICE"}`

4. **Action 4 — Flash:**
   - Text: `Idea logged`
   - The HTTP Post action's own response code is available as
     `%HTTP_RESPONSE_CODE` if you want a real success/failure distinction
     here instead of an unconditional Flash — optional, confirm what's
     actually available in your Tasker version when building this live.

**Test the task manually before adding the widget:** tap the play button
next to `Log Idea` in the Tasks list, speak a test idea, then check
`docker logs hike-izer-orchestrator` on the M8 for a matching `Idea
webhook: opened ... for '...'` line, and confirm a new `CARD-XXX:` PR
actually appeared (`gh pr list` or the GitHub web UI).

**2. Add the home screen icon.** **Correction, found live 2026-08-16:** the
Widgets → Task Shortcut route documented for "Log Observation" Step 25
led to a widget-configuration preview screen with no visible way to
confirm/save it on this Tasker version (no checkmark, and the back arrow
didn't place it either) — a real UI difference from whatever Tasker
version Step 25 was originally built against, not a mistake in following
those steps. **What actually works:** in Tasker's **Tasks** tab, tap
**Log Idea** to select it, open its **3-dot overflow menu**, and choose
**Add to Launcher** — this places a launcher icon directly on the home
screen without going through the Android widget-placement flow at all.

**Real end-to-end test:** tap the icon from the home screen (not the
Tasks list), speak a real idea, confirm the PR appears. This is the one
verification step that can't be done from a desk.

**`Log-Idea.tsk.xml`** (this directory) is the real exported Task, per
CARD-0231. Matches this walkthrough with no discrepancies found —
unlike several of its siblings (`Hike-izer Done`, CARD-0242), this one's
on-device build exactly matches its documentation.

## Related

- `tos/README.md` (the TOS index — auto-PR intake pipeline this feeds)
- `components/hike-izer-orchestrator/README.md` (the `/webhook/idea` contract this Task calls)
- CARD-0173 (this task's own tracking card)
- CARD-0241 (the doc split this file is a result of)
