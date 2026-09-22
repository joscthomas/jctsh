# core/docker — Docker/containerd Daemon Configuration

Docker and containerd daemon-level config for the JCTsh hosts that run containers (the
Pi and the M8). Not a running service itself — this config governs the container runtime
every other `core/`/`components/` Docker service depends on.

**Status:** Production — every containerized JCTsh service runs under this config.

---

## Where each host's `daemon.json` lives

**Each host's `daemon.json` is tracked under `hosts/<host>/`, not here (CARD-0326).** The
two hosts' configs genuinely differ, and correctly so — a single shared file cannot
represent both without one host's real config going untracked:

| Host | Repo copy | `dns` | `data-root` | `log-driver` |
|---|---|---|---|---|
| Pi | `hosts/pi1/daemon.json` | ✓ | `/mnt/jctsh-logs/docker` | *(default `json-file`)* |
| M8 | `hosts/m8/daemon.json` | ✓ | *(absent)* | `journald` |

- **`dns` (both hosts)** pins `8.8.8.8`/`8.8.4.4`, preventing a stale DHCP-assigned DNS
  server from baking into a container's network config at creation time — the cause of a
  real HA cloud-connectivity outage in June 2026.
- **`data-root` is Pi-only** (CARD-0159) — it exists to keep Docker's bulk off the Pi's
  microSD card (`JCTsh-Build-Standards.md` §9.10). The M8 has no SD card and no such
  constraint, so it has no reason to set it.
- **`log-driver: journald` is M8-only** (CARD-0272) — reuses the M8's already-persistent
  journal so container output survives a reboot. Whether the Pi should do the same is
  deliberately still open: **CARD-0327**.

## Files in this directory

| File | Deploys to | Purpose |
|---|---|---|
| `containerd-config.toml` | `/etc/containerd/config.toml` | **Pi only** — sets containerd's own `root` onto the USB drive. On a containerd-backed Docker install this is where the bulk of image/container-layer data actually lives, not under `/var/lib/docker`. The M8 has no counterpart. |

## Deploy

```bash
# Docker daemon config -- per host, from that host's own directory
scp hosts/pi1/daemon.json pi@pi1.local:/tmp/daemon.json      # Pi
ssh pi@pi1.local "sudo install -m 644 /tmp/daemon.json /etc/docker/daemon.json"

scp hosts/m8/daemon.json jct@m8.local:/tmp/daemon.json       # M8
ssh jct@m8.local "sudo install -m 644 /tmp/daemon.json /etc/docker/daemon.json"

# containerd (Pi only)
scp core/docker/containerd-config.toml pi@pi1.local:/tmp/config.toml
ssh pi@pi1.local "sudo install -m 644 /tmp/config.toml /etc/containerd/config.toml"

ssh <host> "sudo systemctl restart containerd docker"
```

Staged through `/tmp` + `sudo install` because `/etc` is root-owned on both hosts — a
direct `scp` to `/etc/...` fails.

**Two things a daemon restart does *not* do, both found the hard way:**

- A **`data-root`/`root` path change** only takes effect for containers created after the
  restart — see `JCTsh-Build-Standards.md` §9.10 for the mount-ordering race it must be
  paired with (`RequiresMountsFor` on the target USB mount) and the reboot-test standard.
- A **`log-driver` change** likewise only applies to **newly created** containers.
  `systemctl restart docker` restarts existing containers per their restart policy
  without recreating them, so they silently stay on their original driver — every
  container needs `docker compose up -d --force-recreate`, once per compose project
  (`JCTsh-Build-Standards.md` §9.9, learned live during CARD-0272).

To confirm a host's repo copy still matches reality:

```bash
ssh pi@pi1.local "sudo cat /etc/docker/daemon.json" | diff - hosts/pi1/daemon.json
ssh jct@m8.local "sudo cat /etc/docker/daemon.json" | diff - hosts/m8/daemon.json
```
