# Pi1 — Host Docs

**Mostly a placeholder, created 2026-08-19 alongside `hosts/m8/` (CARD-0096 addendum) — not yet populated, with one exception below.**

## Files

| File | Purpose |
|---|---|
| `daemon.json` | CARD-0326 — this host's `/etc/docker/daemon.json` (DNS pinning + `data-root` on the USB drive, CARD-0159). Tracked per host because the M8's differs legitimately; see `core/docker/README.md` for the comparison and deploy steps. Also the first real content in this directory — the migration described below is still outstanding. |


The Pi's host-level operational info currently lives scattered across the repo rather than consolidated here: general software inventory in the root-level `SOFTWARE-ENVIRONMENT.md`, and individual infrastructure services organized by function under `core/` (`core/logging/`, `core/node-red/`, `core/mqtt/`, `core/homeassistant/`, etc.) rather than by host. Migrating that scattered info into this directory — matching the `hosts/m8/` pattern (base setup, network reference, scheduled jobs, host-wide maintenance) — is deliberate future follow-on work, not done as part of the M8 reorg that created this placeholder. See `kanban-board.md` CARD-0096's addendum.
