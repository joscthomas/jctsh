# core/docker — Context

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 8334B, over the 5000B size threshold.

### CARD-0159 · [enhancement] [docker] Move Docker's data-root from the Pi's SD card to the existing USB drive — RESOLVED 2026-08-14 14:36 MST
**Status:** Done

**Raised 2026-08-13 21:30 MST**, during CARD-0130's HA image update — a pull failed mid-download (`short read: ... unexpected EOF`, a transient registry hiccup, unrelated to this card) and Joseph asked what a USB drive on the Pi would actually buy, prompted by seeing Docker's data-root (`/var/lib/docker`) sitting on the SD card mid-pull.

**Same motivation as CARD-0006 (Done), same underlying fix, different directory.** That card moved the log directory to a USB stick — its own investigation found capacity was never the real constraint (log volume was under 1MB after 1.5 months); the actual problem was **SD card write endurance**, which degrades under frequent writes in a way USB flash/SSD tolerates far better. Docker's data-root sees exactly that write pattern (image layer pulls, container filesystem churn) and currently sits on the same SD card (`/dev/mmcblk0p2`, root filesystem) as the OS itself.

**Target drive decided (interviewed live):** share the existing USB drive from CARD-0006 (`/dev/sda1`, mounted `/mnt/jctsh-logs`, labeled `jctsh-logs`) rather than sourcing a second drive — checked live, it has 30GB total with only 4.7MB used (log volume is negligible), plenty of room for Docker's data too without competing for space or meaningfully changing its own wear profile.

**Design, mirroring CARD-0006's own careful approach (not yet built):**
1. Stop Docker (`sudo systemctl stop docker`) before moving anything — never rsync a live, in-use data directory.
2. Move `/var/lib/docker`'s actual contents onto the USB drive (e.g. a `docker` subdirectory alongside the existing log directory, or reconsider whether this warrants a second partition on the same physical drive — decide at Build time).
3. Set Docker's `data-root` explicitly in `/etc/docker/daemon.json` (already tracked in this repo, currently only pins DNS — `{"dns": [...]}`) to the new USB path, alongside the existing DNS config, not replacing it.
4. **The exact gap CARD-0006 found and fixed for `jctsh-logging.service` almost certainly applies here too** — Docker's own systemd unit needs a mount-ordering dependency (`RequiresMountsFor=/mnt/jctsh-logs` or equivalent) so a reboot can't race Docker's startup ahead of the USB mount and silently recreate `/var/lib/docker` back on the SD card underneath it. Check whether `docker.service` already has this (likely not, same blind spot CARD-0032/0048/0006 each independently hit) and add it if missing.
5. Verify via a real reboot test, same as CARD-0006 did — mount comes back automatically, Docker waits for it correctly, all containers (`homeassistant`, and anything else running) come back up using data from the USB path, not fresh/empty. `reboot-health-check.py` (CARD-0158) conveniently already checks `homeassistant`'s health post-reboot — real, incidental extra coverage for this card's own verification once both are live.
6. Clean up the stale SD-card copy of the old data-root only once the USB path is confirmed live and correct — same sequencing CARD-0006 used.

**Real, higher blast radius than CARD-0006, worth stating plainly:** the log directory was an appendable file with a trivial rollback (stale SD copy sitting untouched until deletion). Docker's data-root holds every container's actual data (`homeassistant` included, which Robin depends on directly) — a mistake here risks breaking Docker/HA entirely, not just losing some log history. Do this deliberately, with a real backup of the SD-card copy kept until the USB path is fully verified, not as a quick add-on to some other night's session.

**Done when:** Docker's data-root genuinely lives on the USB drive (confirmed via `docker info`'s `DockerRootDir`), a real reboot correctly brings every container back up from the USB-resident data with no gap, the systemd mount-ordering dependency is in place and verified (not just assumed), and the old SD-card copy is removed only after all of that's confirmed.

**Built and verified live, 2026-08-14 — scope expanded well beyond the original design, each expansion found live rather than planned upfront:**

1. **Real finding that changed the plan: `/var/lib/docker` alone was nearly empty (524KB).** This Docker install uses containerd's separate content-addressable snapshot store — the actual 6.3GB of image/container-layer data lives under `/var/lib/containerd`, configured via `/etc/containerd/config.toml`'s `root` setting (was commented out, defaulting to `/var/lib/containerd`). Moving only `/var/lib/docker` would have accomplished almost nothing for this card's actual goal. Moved both: `/var/lib/docker` → `/mnt/jctsh-logs/docker` (via `daemon.json`'s `data-root`), `/var/lib/containerd` → `/mnt/jctsh-logs/containerd` (via `config.toml`'s `root`). Both verified byte-for-byte (`du` + file count matched source exactly) before cutover.
2. **HA's config directory** (`/home/pi/homeassistant`, 61M) — includes `home-assistant_v2.db`, the recorder database that writes on nearly every entity state change across the whole house, arguably a bigger ongoing SD-wear contributor than Docker itself. Moved to `/mnt/jctsh-logs/homeassistant`, `docker-compose.yml`'s bind mount updated and deployed. Verified via full entity-count comparison (771 before/after the container recreate, zero regression) rather than just "container started."
3. **Mosquitto's persistence** (`/var/lib/mosquitto`, 308K) — moved to `/mnt/jctsh-logs/mosquitto`, `persistence_location` updated in both the live config and the repo's tracked `core/mqtt/mosquitto.conf`. Verified with a real retained-message pub/sub round trip.
4. **`/var/log` entirely** (2.5M, but the meaningful part is write *rate* not size) — found live that mosquitto's connection log (which `fail2ban` actively watches per the Internet Exposure section above) and nginx's HTTPS-proxy access/error logs were the two real ongoing writers here, `rsyslog` itself turned out to be inactive. Rather than special-case mosquitto's log path (would've needed `fail2ban`'s jail config, logrotate, and mosquitto.conf all kept in lockstep), bind-mounted the whole directory: moved to `/mnt/jctsh-logs/var-log`, old `/var/log` renamed aside (`/var/log.old-sd-backup`, not yet deleted — Joseph's call on final cleanup), `/etc/fstab` gets a `bind,nofail` mount entry (matching the existing USB mount's own `nofail`, so a missing/failed drive can't hang boot). No app-level config changes needed — `fail2ban`'s watched path (`/var/log/mosquitto/mosquitto.log`) stays textually identical, just transparently backed by the USB drive now. Verified via `fail2ban-client status` confirming it's still watching the right (now bind-mounted) path, and a real MQTT publish producing a fresh, correctly-attributed log line.

**All four pieces survived two independent real reboot tests** (once after the Docker/containerd/HA/mosquitto moves, once again after the `/var/log` bind mount) — not just live-state checks. Both times: USB mount reattached automatically, nothing silently fell back to the SD card, all services came back active, HA reached healthy with its full entity registry intact, and CARD-0158's own independent post-reboot health check confirmed `{'homeassistant': 'healthy', 'nodered': 'active', 'mosquitto': 'active'}` both times.

**SD card usage: 14G → 7.7G (53% → 29%)** after deleting the verified-safe old copies of Docker/containerd/HA-config/mosquitto-persistence. `/var/log.old-sd-backup` intentionally left in place pending Joseph's go-ahead to delete.

**New standing convention captured, not just a one-off fix**: added to `CLAUDE.md`'s Infrastructure section — avoid SD-card I/O on the Pi generally, prefer the M8 for new apps, and when something must stay Pi-native, route its write-heavy state onto this same USB drive using the pattern established here.

**Related:** CARD-0006 (the log-directory precedent this generalizes, same drive), CARD-0032/CARD-0048 (the mount-ordering-race incident class this is careful to avoid repeating a third time), CARD-0158 (the post-reboot health check that incidentally helps verify this card too), CARD-0130 (the HA update session this idea came up during).

---
