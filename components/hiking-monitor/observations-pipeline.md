# Hiking Monitor — Hiking Observations Pipeline (Steps 24–27)

This document covers the "Log Observation" voice-note pipeline on the Pixel: the
Tasker task that captures a spoken observation (Step 24), and the offline
queue/retry mechanism that makes delivery resilient to connectivity gaps
(Step 27, CARD-0156). For the sheet's own column schema, see
`data-pipeline.md`'s "Hiking Observations Sheet" section. For the *build
history* — what was tried, what didn't work on this Tasker version, and why
each design decision landed where it did — see
`hiking-monitor-claude-code-instructions.md` Steps 24–27. This file is the
current-state reference; that one is the record of how it got here.

---

## Architecture Overview

```
Pixel 10 Pro XL (Tasker: "Log Observation")
    │  tap widget/task → Get Voice → transcribe
    ▼
Write File: Tasker/obs_queue/<epoch_ts>
    │  (one file per observation, filename = spoken-at epoch seconds)
    ▼
Perform Task: "Flush Observation Queue"  ──────────────┐
    │  attempted immediately, every time                │
    ▼                                                    │  also triggered by:
List Files (Tasker/obs_queue/) → For each queued file:   │  State: Wifi Connected
    Read File → strip path → HTTP POST                   │  State: Mobile Network
    │                                                     │  (either connectivity
    ├─ success → Delete File, count it, Flash on exit ────┤   type regained)
    │
    └─ failure → Tasker stops the whole task immediately
                 (Continue Task After Error: off on the
                 HTTP Request action) — file stays queued,
                 untouched, retried on the next flush
                 attempt. No flash, nothing sent, nothing
                 lost.
                         │
                         ▼
        Google Apps Script  action=doPost (component: "hiking-observations")
                         │
                         ▼
              "Hiking Observations" sheet in "JCTsh Environmental Data"
```

No local audio is ever saved — Tasker's **Get Voice** action transcribes
on-device and only ever produces the resulting text (`%VOICE`); if there's no
connectivity at the moment of speaking, the *text* is queued, not audio.

---

## Section 1 — "Log Observation" task

Home-screen Task Shortcut widget (or run directly from Tasker's Tasks tab —
functionally identical). Four actions:

1. **Get Voice** — Title: "Speak Your Observation", transcribes to `%VOICE`.
2. **Stop** — inline `If %VOICE !Set` (cancelled/no speech detected — quiet
   exit, nothing queued).
3. **Write File** — File: `Tasker/obs_queue/%TIMES` (no extension), Text:
   `%VOICE`, Append: off, Continue Task After Error: on.
4. **Perform Task** — `Flush Observation Queue`.

No Flash anywhere in this task — by design (Joseph's call, CARD-0156): no
confirmation at the moment of speaking, silent whether online or offline.
Confirmation only ever comes from the Flush task itself, once something is
*actually* sent.

---

## Section 2 — "Flush Observation Queue" task

Twelve actions, all detail (including the three real-device quirks that
shaped this design — a rejected variable name, no bare-filename mode on List
Files, and two failed attempts at manual HTTP-failure detection before
landing on Tasker's native stop-on-error) documented in
`hiking-monitor-claude-code-instructions.md` Step 27b. Summary of the
current, confirmed-working state:

1. **List Files** (`Tasker/obs_queue/`) → `%queuefiles` (always full paths on
   this device — no bare-filename option exists here), sorted by name
   ascending (epoch filenames sort chronologically).
2. **Stop** if `%queuefiles(#) Eq 0` — nothing queued, silent exit.
3. **Variable Set** `%sent_count` = `0`.
4. **For** `%qfc` in `%queuefiles()` — loop variable is `%qfc`, not the more
   obvious `%qf`; the latter is rejected outright by this Tasker version.
5. **Read File** `%qfc` → `%obs_text`.
6. **Variable Set** `%obs_ts` = `%qfc`.
7. **Variable Search Replace** on `%obs_ts`, pattern `^.*/` → empty (strips
   the full path down to the bare epoch timestamp for the outgoing `ts`
   field).
8. **HTTP Request** — POST to the Apps Script, JSON body carrying `%obs_ts`
   and `%obs_text`. **Continue Task After Error: off** — a real failure stops
   the whole task here, natively, before anything downstream runs.
9. **Delete File** `%qfc` (only reached on confirmed success).
10. **Variable Add** `%sent_count` +1.
11. **End For.**
12. **Flash** `%sent_count observation(s) logged`, inline `If %sent_count > 0`.

**Failure behavior:** the file is never deleted, `%sent_count` is never
incremented, and no flash fires unless the POST genuinely succeeds. A failed
attempt leaves the queue exactly as it was, ready for the next trigger.

---

## Section 3 — Auto-flush triggers

Two Tasker **Profiles** (State → Net), both pointing at `Flush Observation
Queue` — this Tasker version has no single unified "any connectivity"
option:

| Trigger | Covers |
|---|---|
| Wifi Connected | Returning to home WiFi |
| Mobile Network | Regaining cellular signal (the realistic mid-hike case) |

Plus the always-on opportunistic path: every `Log Observation` run also calls
Flush immediately (Section 1, Action 4), so if the phone is already online
when you speak, the observation sends right away with no queueing at all.

---

## Section 4 — Known gaps / not yet built

- **Home-screen widget placement** is currently flaky on this device (Tasker
  Task Shortcut widget intermittently fails to prompt for a task when
  dragged onto the home screen). Not blocking — running the task directly
  from Tasker works identically — but the widget itself may need
  re-creating; see `hiking-monitor-claude-code-instructions.md` Step 27d.
- **CARD-0090** (recognizer cutting off mid-sentence on pauses) is a separate,
  already-Deferred issue with the *transcription* step, unrelated to and not
  addressed by this delivery-resilience work.
- The Apps Script deployment URL used by this pipeline was found and
  corrected mid-build (was pointing at a pre-2026-07-18 stale deployment) —
  worth checking whether `gps-pipeline.md`'s GPSLogger custom-URL config has
  the same issue; not yet checked.

## Related
- `hiking-monitor-claude-code-instructions.md` Steps 24–27 — full build
  history, including every dead end tried before landing on this design.
- `data-pipeline.md` — "Hiking Observations Sheet" column schema, and the
  general Apps Script export API this pipeline's target endpoint is part of.
- `gps-pipeline.md` — the `Discard offline locations: off` precedent this
  generalizes, for the sibling GPS Track pipeline.
- `kanban-board.md` CARD-0156 — resolution summary and interview record.
