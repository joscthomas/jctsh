# architecture/ — Cross-Cutting Architecture and Operational Decisions

Doc-only directory (no executable code) for cards that are genuinely cross-cutting —
not owned by any single component, core service, or host. Created 2026-09-18 (CARD-0294)
specifically to give the residual bucket of `[infrastructure]`-tagged cards a real home,
once host-specific and component-specific ones were retagged to `[m8]`/`[pi1]`/their
actual component.

**What belongs here:** strategy decisions spanning multiple systems (SmartThings API
strategy, MQTT security posture), standards that apply to a whole class of future
components rather than one existing directory (backyard-device power patterns, battery
build standards before they were harvested into `JCTsh-Build-Standards.md`), and
whole-repo audits (security hardening, disaster recovery, cross-host reboot behavior).

**What doesn't:** anything that fits a real `components/<name>/`, `core/<name>/`, or
`hosts/<name>/` directory once actually checked — see `JCTsh-Operating-System.md`'s
Engineering Discipline section on investigating before assuming a card can't be
reconciled.

## Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | Curated context — currently a stub |
| `card-archive.md` | Archived `[architecture]`-tagged card history (created on first use by `archive_cards.py`) |

## Related

- `kanban-board.md` CARD-0294 — the tag reconciliation that created this directory.
- `JCTsh-Operating-System.md`'s Documentation Structure section — the README-vs-CLAUDE.md
  split this directory follows like any other.
