# core/docker — Docker/containerd Daemon Configuration

Version-controlled copy of the Docker and containerd daemon-level config applied to
JCTsh hosts running containers (the Pi and the M8). Not a running service itself —
these files configure the container runtime every other `core/`/`components/` Docker
service depends on.

**Status:** Production — every containerized JCTsh service runs under this config.

---

## Files

| File | Deploys to | Purpose |
|---|---|---|
| `daemon.json` | `/etc/docker/daemon.json` | Pins DNS to `8.8.8.8`/`8.8.4.4` (prevents a stale DHCP-assigned DNS server baking into a container's network config at creation time — caused a real HA cloud-connectivity outage in June 2026) and sets `data-root` onto the USB drive rather than the SD card/root filesystem (`JCTsh-Build-Standards.md` §9.10) |
| `containerd-config.toml` | `/etc/containerd/config.toml` | Sets containerd's own `root` onto the same USB drive — on a containerd-backed Docker install, this is where the actual bulk of image/container-layer data lives, not `/var/lib/docker` |

## Deploy

```bash
scp core/docker/daemon.json <host>:/etc/docker/daemon.json
scp core/docker/containerd-config.toml <host>:/etc/containerd/config.toml
ssh <host> "sudo systemctl restart containerd docker"
```

A `data-root`/`root` path change only takes effect for containers created after the
restart — see `JCTsh-Build-Standards.md` §9.10 for the mount-ordering race this must be
paired with (`RequiresMountsFor` on the target USB mount) and the reboot-test
verification standard.

**Not yet reflected here:** CARD-0272's M8-wide switch to the `journald` logging driver
was applied directly on the M8's `/etc/docker/daemon.json` — this repo's copy of
`daemon.json` doesn't yet include that setting. Worth confirming whether the two hosts'
real configs have actually diverged, or whether this file simply needs updating to match.
