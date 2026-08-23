# hike-izer/ — Generated Output Staging

This directory holds **generated output only** — not source code. The
`hike-izer` skill (`.claude/skills/hike-izer/SKILL.md`) writes here when
building a hike summary; the actual pipeline code lives separately in
`components/hike-izer/`. Kept apart deliberately: code stays under
`components/hike-izer/`, results land here.

## What's in `summaries/`

For each hike, keyed by start date:
- `<start-date>_hike-summary.html` — the rendered summary page. Tracked in git as a historical record.
- `<start-date>_hike-summary.meta.json` — metadata alongside it. Also tracked.
- `<start-date>_photos/` — processed photos for that hike. **Gitignored** (`hike-izer/summaries/*_photos/`) — bulky and regenerable, not worth tracking.

## How it's used

Per the skill's own documented flow:
1. Fetch and analyze hike data (helper scripts in `components/hike-izer/`).
2. Build the HTML summary, meta.json, and photos here, under `summaries/`.
3. Publish by `scp`-ing the HTML, meta.json, and photos folder up to the M8 (`~/hike-izer-web-app/srv/`) — that's what actually serves the public hike pages, not this directory.

This directory is a local staging area, not a deployed artifact — nothing reads from it directly except the publish step.

## Related

- `components/hike-izer/` — the actual pipeline source and its own README/CLAUDE.md.
- `.claude/skills/hike-izer/SKILL.md` — the full generation/publish workflow this directory is a byproduct of.
- `components/hike-izer-web/`, `components/hike-izer-orchestrator/` — the M8-hosted app this staging output gets published to.
