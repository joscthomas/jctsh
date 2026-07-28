# Phone Workflow — What Joseph Actually Does on a Hike

Quick reference for the phone-side steps during a hike. For the hiking-monitor
*device's* switch/mode behavior specifically (separate from the phone), see
`operations.md`'s "Hiking" workflow section.

This spans three otherwise-separate pieces: GPSLogger (triggers the automatic
Hike-izer pipeline, CARD-0086), the "Log Observation" Tasker widget (Hiking
Observations pipeline), and Gaia GPS (personal navigation, and — as of
CARD-0104 — the source of the Route Map embed added to summaries afterward).

## Start of hike
1. **Start GPSLogger** — normal app start, tapped directly in the app.
2. **Start Gaia GPS** — same, tapped directly in the app. Independent of
   GPSLogger; used for personal navigation and later for CARD-0104's map
   embed, not part of the automatic pipeline at all.
3. **Turn the hiking-monitor device's switch ON** — see `operations.md`.

**No Tasker action needed here.** The Hike-izer Tasker *Profile* is a passive
listener, always armed in the background (an "Intent Received" trigger
watching for GPSLogger's own broadcasts). It does nothing on GPSLogger's
`started` event — only `stopped` triggers anything (see
`components/hike-izer-orchestrator/README.md`). There's nothing to manually
run at the start.

## During the hike
- **Log an observation** any time: tap the **"Log Observation"** home-screen
  widget (Tasker Task Shortcut) → speak the observation → it's transcribed
  and posted straight to the Hiking Observations sheet. Repeat as many times
  as wanted.
- No other action needed — the hiking-monitor device reads/logs on its own
  every 2 minutes; GPSLogger posts trackpoints every 30 seconds.

## End of hike
1. **Stop GPSLogger.**
2. **Stop Gaia GPS.**
3. **Turn the hiking-monitor device's switch OFF.**

**No Tasker action needed here either.** The moment GPSLogger is stopped, it
broadcasts the `stopped` event itself — the already-armed Tasker Profile
fires automatically, which triggers the whole automatic Hike-izer pipeline
(webhook → M8 orchestrator → generation → publish) with zero further input.
Stopping Gaia GPS is unrelated to that pipeline; it just saves the track in
Gaia for later (CARD-0104's manual map-embed step, whenever Joseph gets
around to it).

## After the hike (whenever convenient, not urgent)
- The automatic summary is already published by the time GPSLogger finishes
  stopping — check `https://hikes.jctnet.com/`.
- To add the Gaia route map (CARD-0104, currently manual): visit
  gaiagps.com, mark the relevant track Public, copy its embed code, and
  paste it to Claude along with the hike's date.

## Related
- `operations.md` — hiking-monitor device switch/mode behavior, battery,
  charging.
- `components/hike-izer-orchestrator/README.md` — Tasker Profile/Task setup,
  webhook contract, CARD-0086.
- `hiking-monitor-claude-code-instructions.md` Step 24 — how the "Log
  Observation" widget was originally built.
- `kanban-board.md` CARD-0104 — the Gaia GPS route-map embed trial.
