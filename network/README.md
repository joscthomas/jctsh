# network/ — DNS, Domains, and Network-Level Concerns

Doc-only directory (no executable code) for cards about external network/DNS concerns —
`jctnet.com`/`jctnet.net` DNS records, domain configuration — that don't belong to any
single component, core service, or host. Created 2026-09-19, alongside deprecating the
generic `[personal]` tag (`kanban-board.md` CARD-0316) — DNS cleanup work had been tagged
`[personal]` even though it's genuinely operational/network work, not personal-life
content, once actually looked at.

**What belongs here:** DNS record management, domain-level configuration, and similar
network-layer decisions that span or predate any specific host/component.

**What doesn't:** local/LAN device networking that's actually a specific host or
component's own concern (e.g. a device's own WiFi config) — that stays tagged to the
owning component/host, same as always.

## Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | Curated context — currently a stub |
| `card-archive.md` | Archived `[network]`-tagged card history (created on first use by `archive_cards.py`) |

## Related

- `kanban-board.md` CARD-0316 — deprecating `[personal]`, the reason this directory exists.
- `architecture/README.md` — the same doc-only, no-component-home pattern, for the
  cross-cutting-decisions case instead of the network-specific one.
