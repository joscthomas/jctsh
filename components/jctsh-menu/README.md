# jctsh-menu

Not a running service — this "component" is a single Tasker task
(`JCTsh Menu`) plus this doc. Given a real, discoverable home of its own
(CARD-0241) rather than filed under whichever backend happens to host its
first entry's webhook, because the whole point of this pattern is to be
domain-agnostic: a shared, growable home-screen menu for simple,
no-input, fire-and-forget phone actions, as an alternative to building a
brand-new dedicated Task + home-screen icon (the `Log Idea` pattern,
CARD-0173) for every future action of this shape.

**When to add an entry here vs. a dedicated icon:** if the action needs
no input from Joseph beyond "do it now" (like `Run Step 2`), it belongs
here — one more menu line + branch, no new Task/icon. If it needs input
first (speech-to-text, a typed value), a dedicated single-tap icon like
`Log Idea`/`Log Observation` stays the better shape — Joseph's explicit
call (2026-09-05) that the extra tap to open a menu isn't worth it for
those.

## Current entries

| Menu label | Sets | Calls | Owned by |
|---|---|---|---|
| `Hike-izer Step 2` | `%menu_selection` = `step-2` | `POST https://hikes.jctnet.com/webhook/step2?key=<WEBHOOK_SECRET>` | `components/hike-izer-orchestrator` (CARD-0239) — see that component's `README.md` for the webhook contract |

Add a row here (and a matching `If`/`HTTP Request` branch in the Task
below) whenever a new no-input action is built, regardless of which
container its webhook actually lives in.

## Status

Built and verified live, 2026-09-05/06 — real home-screen-icon test
confirmed a webhook receipt and full `Step 2 complete for 2026-09-03`
pipeline run. See `tasker-setup.md` for the build procedure.
`JCTsh-Menu.tsk.xml` (this directory) is the real exported Task (per
CARD-0231's research into committing Tasker objects to this repo the
same way Node-RED flows already are) — the source of truth for
re-importing this task.

## Related

- `tasker-setup.md` (the build procedure for this Task)
- CARD-0239 (`Hike-izer Step 2`'s own build, and the design decision to create this pattern instead of another dedicated icon)
- CARD-0241 (the doc reorg this component directory is a result of)
- CARD-0231 (Tasker export/import research — `JCTsh-Menu.tsk.xml` is its first real applied example)
- `components/hike-izer-orchestrator/README.md` (the `/webhook/step2` contract this entry calls)
- `tos/tasker-setup.md` / `components/hiking-monitor/hiking-monitor-claude-code-instructions.md` (the dedicated-icon pattern this menu is the alternative to)
