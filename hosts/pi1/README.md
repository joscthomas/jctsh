# Pi1 — Host Docs

**Mostly a placeholder, created 2026-08-19 alongside `hosts/m8/` (CARD-0096 addendum) — not yet populated, with one exception below.**

## Files

| File | Purpose |
|---|---|
| `daemon.json` | CARD-0326 — this host's `/etc/docker/daemon.json` (DNS pinning + `data-root` on the USB drive, CARD-0159). Tracked per host because the M8's differs legitimately; see `core/docker/README.md` for the comparison and deploy steps. Also the first real content in this directory — the migration described below is still outstanding. |
| `20auto-upgrades` | CARD-0350 — deployed to `/etc/apt/apt.conf.d/20auto-upgrades`. Enables this host's already-enabled-but-inert `apt-daily.timer` to actually refresh the apt package index daily; explicitly does not enable unattended upgrades (notify-only policy, root `CLAUDE.md`). Not in the drift check yet (CARD-0328's `MANIFEST` covers `core/mqtt`/`core/node-red`/`core/homeassistant` only) -- worth adding since it's the exact same version-controlled-copy risk. |
| `journald-persistent-storage.conf` | CARD-0353 — deployed to `/etc/systemd/journald.conf.d/50-persistent-storage.conf`. Re-asserts `Storage=persistent` at a precedence tier that wins over Raspberry Pi OS's own vendor drop-in (`/usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf`, `Storage=volatile`) -- CARD-0246's original fix set `Storage=persistent` only in `/etc/systemd/journald.conf` itself, which that vendor drop-in silently outranked the whole time. Same not-in-drift-check gap as `20auto-upgrades` above. |


The Pi's host-level operational info currently lives scattered across the repo rather than consolidated here: general software inventory in the root-level `SOFTWARE-ENVIRONMENT.md`, and individual infrastructure services organized by function under `core/` (`core/logging/`, `core/node-red/`, `core/mqtt/`, `core/homeassistant/`, etc.) rather than by host. Migrating that scattered info into this directory — matching the `hosts/m8/` pattern (base setup, network reference, scheduled jobs, host-wide maintenance) — is deliberate future follow-on work, not done as part of the M8 reorg that created this placeholder. See `kanban-board.md` CARD-0096's addendum.
