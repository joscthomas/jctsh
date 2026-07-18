# Hike-izer

Software-only application layer that turns raw hiking-sensor data (Environmental
Data, Hiking Observations, GPS Track) into a narrative Markdown summary of a hike
— temperature/humidity/UV trends, elevation, the hiker's own voice observations,
sun position along the route, and an explicit expected-vs-actual data-coverage
section that doubles as a health check on the whole hiking-sensor pipeline.

**Status:** v1 built and verified end-to-end (2026-07-18) against the real
2026-06-15 trip data. Tracking card: **CARD-0073** on `kanban-board.md`.

---

## Where things live

Hike-izer's files are deliberately split across three locations:

| What | Where | Why |
|---|---|---|
| The Skill itself (invokable instructions) | `.claude/skills/hike-izer/SKILL.md` | Claude Code only discovers/invokes skills from `.claude/skills/*/SKILL.md` — it can't live anywhere else. |
| Code (data fetch, coverage math, sun-position calc) | `components/hike-izer/fetch_hike_data.py` | Matches every other JCTsh component's convention — code and docs for a component live under `components/<name>/`. |
| Generated output (one Markdown file per hike) | `hike-izer/summaries/` (top-level, sibling to `components/`) | Kept separate from source code on purpose — if a future presentation layer generates HTML, it goes here too, not mixed in with the code that produced it. |

To actually run Hike-izer, invoke the Skill (`.claude/skills/hike-izer/SKILL.md`)
with a hike date or date range — it handles reading credentials, calling
`fetch_hike_data.py`, and writing the narrative itself. Don't run
`fetch_hike_data.py` standalone expecting a finished summary; it only produces
the structured JSON the Skill's narrative-writing step consumes.

---

## Related

- `components/hiking-sensor/data-pipeline.md` — Environmental Data / Hiking Observations schema and the `action=export` API this depends on.
- `components/hiking-sensor/gps-pipeline.md` — GPS Track schema (`accuracy_m`/`altitude_m`, not `acc`/`alt`).
- CARD-0020 on `kanban-board.md` — complementary Looker Studio dashboard (raw charts/maps), not superseded by Hike-izer.
- CARD-0073 on `kanban-board.md` — full build history, v1 scope, the deployment-migration saga, and known findings from the first real run.
