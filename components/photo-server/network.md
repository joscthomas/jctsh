# photo-server — Network Reference

Cross-reference with `jctsh-network.md` (repo root), which is the canonical device table.

| Property | Value |
|---|---|
| Hostname | `photo-server` |
| LAN IP | `192.168.1.165` (DHCP-reserved) |
| mDNS | `photo-server.local` — confirmed working from Windows via `ping` |
| MAC | `70:70:fc:09:ad:a5` (`eno1`, wired) |
| Tailscale IP | `100.111.16.14` |
| Web UI | `http://photo-server.local:2283` / `http://192.168.1.165:2283` |

M8 has two identical-looking ethernet ports — only `eno1` has the DHCP lease and active link. Moving the cable to the other port silently drops network (see `photo-server-phase2-planning.md` hardware gotchas).
