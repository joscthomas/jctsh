# m8 — Network Reference

Cross-reference with `network/jctsh-network.md`, which is the canonical device table.

| Property | Value |
|---|---|
| Hostname | `m8` (renamed from `photo-server`, CARD-0096, 2026-08-14) |
| LAN IP | `192.168.1.165` (DHCP-reserved) |
| mDNS | `m8.local` — confirmed working from Windows via `ping` (`photo-server.local` still resolves via a transition-window mDNS alias, CARD-0096) |
| MAC | `70:70:fc:09:ad:a5` (`eno1`, wired) |
| Tailscale IP | `100.111.16.14` |
| Web UI | `http://m8.local:2283` / `http://192.168.1.165:2283` |

M8 has two identical-looking ethernet ports — only `eno1` has the DHCP lease and active link. Moving the cable to the other port silently drops network (see `photo-server-phase2-planning.md` hardware gotchas).
