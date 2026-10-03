---
name: rotate-credentials
description: Step Joseph through rotating one JCTsh credential at a time using tos/rotate.py and tos/secret.ps1 -- triages what's due from the registry in priority order, drives the live rotation with his go-ahead at each stage, closes it out, then offers the next one. Use when Joseph asks to rotate a credential/secret/key/password, check what rotation is outstanding, continue/resume an in-progress rotation, or wants to "go through the rotation workflow."
---

# Rotate Credentials

Drives `tos/rotate.py` + `tos/secret.ps1` to rotate one JCTsh credential at a
time, live, with Joseph at the keyboard for every guided step. CARD-0372 is
the tracking card (its "FOR JOSEPH'S REVIEW" proposal, 2026-10-02, is this
skill's design source). This skill is the operator; `rotate.py`/`secret.py`
do the actual work and are the only things that ever touch a value.

## Run this procedurally, not conversationally

**Joseph, 2026-10-02, after the first live runs felt like ordinary free-form
chat instead of a defined workflow: "i want it to be step by step very
procedural."** Label every step by its number/name from this doc (e.g. "Step
2: Prepare" before running `plan`) instead of narrating decisions in prose.
Don't explain *why* a command is safe or editorialize on what just happened
-- state the result and move to the next labeled step. Only stop for input
at the points this doc actually designates (the go-ahead before
`start`/`continue`/`finish`/`abort`, and the RoboForm paste) -- not for
asides, caveats, or restating context Joseph already has. If something
genuinely goes wrong (a crash, an unexpected value, a failed check), say so
plainly and ask what to do -- that's a real decision point, not a tangent.

## The standing rule

**Never print, echo, or log a credential's value** -- not in a Bash command's
text, not in its output, not in a card, commit message, or chat reply
(CARD-0334). Every command below is values-free by design: `rotate.py`'s own
output names holders and pass/fail only; `secret.ps1 copy`/`set` relay a
value straight to the Windows clipboard or a masked, interactive SSH prompt,
never through this session. If anything ever surfaces a value anyway, stop
immediately, say so by credential name (never the value), and treat it as an
incident (CARD-0334) rather than continuing.

## Workstation gotcha: always invoke via `python`, never bare `.\rotate.py`

Found live 2026-10-02: a bare `.\tos\rotate.py <cmd> <target>` can open the
file in Sublime Text instead of running it, if Sublime has claimed this
workstation's `.py` file association (the same class of problem as
`secret.ps1` opening in Notepad when typed into `cmd.exe` instead of real
PowerShell -- here it bites even inside a real PowerShell session, because
`.\file.py` falls back to Windows' file-association "open" verb unless `.py`
is actually associated with `python.exe`). **Always invoke explicitly:**
`python tos\rotate.py <cmd> <target>` (confirmed present on this workstation,
`python --version` -> 3.12.10) -- never relies on file association, so it
can't be hijacked by whatever editor is currently registered for `.py`.
`secret.ps1` itself is unaffected (it's genuinely a PowerShell script, and
`.ps1`'s association issue is the separate cmd-vs-PowerShell one covered
elsewhere) -- keep invoking it as `.\tos\secret.ps1 <cmd>`.

## 1. Triage -- what to rotate next

Run `.\tos\secret.ps1 due` (local, read-only, no vault touch -- safe to run
freely). It reports: exposed-and-unrotated (surfaces every session,
unconditionally, per `JCTsh-Session-Start.md` step 9), explicit
`rotation_requested` entries, overdue-by-cadence, anything `rotate.py` has
started but not finished, and anything stuck at `roboform_synced: false`.

**Recommend one credential at a time, not the whole list dumped.** Priority:
1. Anything already in progress (`rotate.py status`) or stuck on
   `roboform_synced: false` -- finish that before starting a new one.
2. Exposed-and-unrotated, ordered by real-world reachability. CARD-0375's own
   ordering is the model: internet-reachable (e.g. `webhook-secret`) before
   LAN-reachable (e.g. a Mosquitto/OTA pair) before local-only (e.g. an API
   key) before an already-retired endpoint.
3. Explicit `rotation_requested` entries.
4. Overdue-by-cadence, oldest first.

**Before recommending, check for a same-device companion rotation.** A
Mosquitto account and an `esp32-device-secrets` OTA entry for the same ESP32
device both end in a guided "flash the device" holder -- if both are in the
`due` output at once, recommend doing them together as one physical
reflash, not two. Missed live 2026-10-02 (hiking-monitor's MQTT and OTA
passwords were rotated as two separate sessions, forcing a second
unnecessary reflash -- Joseph: "why was I instructed to do the MQTT password
... without the OTA password? now I have to flash it again") -- grep the
`due` output for the same device name across both `mosquitto-accounts--*`
and `esp32-device-secrets--*-ota` before finishing either one in isolation.

State which one (or which pair) and why in one or two sentences, then ask
whether to proceed with it or let Joseph name a different one. **CARD-0372's
standing decision: no rotation deadlines for the exposed bucket** -- `due`
surfacing something is information, not itself permission to act. Don't
treat silence as a yes.

## 2. Prepare

`python tos\rotate.py plan <target>` -- offline, nothing touched, no value read.
Shows every holder in order, which are automatic (`apply`) vs guided, and
whether dual-accept covers the guided ones (meaning the old value keeps
working while Joseph gets to them, vs. switching immediately). Read it and
tell Joseph up front what he'll need at hand based on the guided holders --
his phone for GPSLogger/Tasker, a USB cable for an ESP32 reflash, etc. --
don't make him discover it mid-rotation.

Check the value is already in the vault: `.\tos\secret.ps1 has <target>`. If
not found, **stop here** and tell Joseph to run `.\tos\secret.ps1 set
<target>` himself, in his own terminal. Never attempt this from inside this
session -- the masked prompt only works from an interactive terminal Joseph
is typing into directly; `secret.ps1`'s own header says this explicitly.

## 3. Drive

`start`/`continue`/`finish`/`abort` each change real state and always need
Joseph's explicit go-ahead before you run them -- show the exact command,
say in one line what it's about to do, and wait for him to say go. Don't
chain them automatically back to back.

- `python tos\rotate.py start <target>` -- stages the new value, then runs every
  automatic (`apply`) holder and its check without asking per-holder (that's
  what "automatic" means -- the one go-ahead for `start` covers all of
  them), then stops at the first guided holder.
- **Each guided holder:** the command puts the new value on the clipboard and
  names where it goes. Relay that instruction verbatim, then wait for Joseph
  to say it's done (or that this holder doesn't actually hold the value, or
  that he wants to pause here). Then run:
  ```
  $env:JCTSH_ANSWERS = "d"; python tos\rotate.py continue <target>
  ```
  (`d` = done, `n` = doesn't hold this value, `l` = later/pause, `a` = abort
  from here -- use whichever Joseph actually said). **This consumes exactly
  one answer and stops again** at the next guided holder, or moves on to
  cutover if that was the last one. That one-answer-then-stop behavior is
  deliberate, not a bug: `rotate.py` refuses to block on a live prompt when
  it isn't run from a real interactive terminal, so it always hands control
  back to you after a single step -- never try to pre-supply multiple
  answers at once to rush through several holders unattended.
- After the last holder, it moves into cutover on its own and tells you to
  paste into RoboForm next.

**Rotating a same-device companion pair (a Mosquitto account + that device's
OTA password): one reflash, not two.** Joseph, 2026-10-02: "why not flash
them both at the same time?" -- `start` *both* targets first (each stages its
own `.next` value independently; staging one doesn't touch the other).
`writefile` *both* new values into the device's `secrets.yaml` (and its
`C:\esphome` copy) -- `mqtt_password` for the Mosquitto target, `ota_password`
for the ESP32 target -- before compiling anything. Then exactly one
`esphome compile` and one `esphome upload` for that device, covering both
changes at once. Only then confirm each target's file-write holder (`d`) via
its own `continue` call -- `rotate.py` still tracks the two rotations
separately, this just means the physical device action behind both of them
only happens once. The remaining holders (the Pi's Mosquitto account,
deleting the build-cache tree) are independent per target and still handled
one at a time as usual.

## 4. RoboForm + close out

Tell Joseph to paste the new value into the RoboForm entry of the same name
(`.\tos\secret.ps1 copy <target>` puts it on the clipboard again if he needs
it there a second time), then run `python tos\rotate.py confirm-synced <target>`.

Then `python tos\rotate.py finish <target>` -- drops the old value from any
dual-accept holders, purges `<target>.previous` from the vault, and writes
`last_rotated`/clears `rotation_requested` in the registry. If the
credential's registry entry carries a `revoke:` step, `finish` pauses once
more for that before completing.

**Commit `tos/credential-registry.yaml`** once `finish` completes (per
CARD-0325: commit kanban/registry changes on completion, no separate ask).
That's the one file this skill edits directly -- everything else above is a
CLI call that edits the registry itself. If the card this exposure or
rotation came from (CARD-0334, CARD-0375, or a future one) names this
credential as part of its own closing bar, note the completion there too.

## 5. Then repeat

Re-run `.\tos\secret.ps1 due` and offer the next one, same priority order as
step 1. Keep going until Joseph says to stop, or nothing meaningful is left
in any bucket.

## Diagnosing a failed check

`continue`/`finish` stop immediately (exit code 1, not the normal "waiting on
a person" 3) if an automatic holder's restart or `check_cmd` fails, printing
that command's own output. Read it before guessing: tell a bad restart apart
from a bad check apart from an SSH/network problem, and recommend either
`continue` (once the real cause is actually fixed) or `abort` -- but only
before cutover. After cutover, `abort` itself refuses; the only way back is
`secret.py unpromote <target>` plus manually restoring every holder by hand,
exactly as `rotate.py`'s own error message for that case says.

## What this skill never does on its own

- **Seed the vault** (`secret.ps1 set`) -- always Joseph, from his own
  terminal, never relayed through this session.
- **Run `start`/`continue`/`finish`/`abort` without saying the exact command
  first** and getting an explicit go-ahead.
- **Decide a credential is "due enough" to act on without being asked** --
  surfacing `due` output is not permission; CARD-0372 deliberately set no
  rotation deadlines.
- **Pre-supply more than one `JCTSH_ANSWERS` value per `continue` call** --
  one guided holder, one answer, one stop, every time.

Related: CARD-0372 (registry + runner, this skill's own design source),
CARD-0334 (the never-print rule), CARD-0375 (the public-repo exposure this
mechanism exists to close out), `tos/credential-registry.yaml`'s own header
comment (full schema), `tos/rotate.py`'s module docstring (full CLI surface
and environment variables).
