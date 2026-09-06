# Tasker setup — jctsh-menu

Build procedure for the `JCTsh Menu` task. See `README.md` for what this
component is and its current entries table.

**`JCTsh-Menu.tsk.xml`** (this directory) is the real exported Task —
Tasker's own long-press → Export on the Task, `.tsk.xml` per CARD-0231's
research into committing Tasker objects to this repo the same way
Node-RED flows already are. Treat it as the source of truth for
re-importing this task; the walkthrough below documents the same
structure by hand, for anyone building it fresh or checking what it
does without opening Tasker.

**Real Tasker UI shape differed from the original plan** (kept for its
still-correct order of operations, corrected in place): this version's
Menu action has no single "Output Variable" field — instead, each menu
item carries its own **Action** (here, **Variable Set**), and the HTTP
call uses Tasker's **HTTP Request** action with a single combined **URL**
field, not a split Server:Port/Path pair.

## Building the Tasker task (Joseph)

**1. Create the Task** — Tasker → Tasks tab → **+** → name it `JCTsh Menu`:

1. **Action 1 — Variable Clear** `%menu_selection`. Runs before the menu
   every time, so a dismissed/cancelled menu reliably leaves the variable
   unset rather than stale from a previous run — without this, cancelling
   the menu could silently re-fire whatever was picked last time.

2. **Action 2 — Menu** (search **Menu** in the Task category, style
   `IconAndTextMenu`, timeout 30s):
   - Add an item labeled `Hike-izer Step 2`. Its own **Action** field →
     **Variable Set** → `%menu_selection` to the text `step-2`.
     (One more blank placeholder item is fine — Tasker adds it by
     default.)

3. **Action 3 — If** `%menu_selection` **Eq** `step-2` *(exact match —
   a hyphen/underscore mismatch here is exactly the bug found and fixed
   live 2026-09-06; whatever value the item's Variable Set uses must
   match this comparison character-for-character)*:
   - **HTTP Request**, Method `POST`, URL:
     `https://hikes.jctnet.com/webhook/step2?key=G3sOgsf6Ly5N9XwYN2cb1r0qokkHkmug`
     (same shared `WEBHOOK_SECRET` every other route on this receiver
     uses) — no headers/body needed.
   - **Flash:** `Hike-izer Step 2 started`.
   - **End If**

   *(Future entries: add another menu item + its own `If %menu_selection
   Eq "<value>"` block, same shape, pointed at that action's own
   webhook.)*

**Test manually before adding the icon:** tap the play button next to
`JCTsh Menu` in the Tasks list, pick `Hike-izer Step 2`, then check
`docker logs hike-izer-orchestrator` on the M8 for a `Step2 webhook
received -- starting gap-fill pass for ...` line, and confirm the
hike-summary page's data sections actually refresh.

**Add the home screen icon** — same route as `Log Idea` (the Widgets →
Task Shortcut flow doesn't save cleanly on this Tasker version): Tasks
tab → select `JCTsh Menu` → 3-dot overflow menu → **Add to Launcher**.

**Real end-to-end test, confirmed 2026-09-06:** tapped the icon from the
home screen (not the Tasks list), picked `Hike-izer Step 2`, confirmed
via `docker logs` a real webhook receipt and a full `Step 2 complete for
2026-09-03` pipeline run.

## Related

- `README.md` (this component's reference doc — what it is, current entries table)
- CARD-0239 (`Hike-izer Step 2`'s own build)
- CARD-0241 (the doc reorg this file is a result of)
- CARD-0231 (Tasker export/import research — `JCTsh-Menu.tsk.xml` is its first real applied example)
