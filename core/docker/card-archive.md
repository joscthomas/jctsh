# core/docker — Card Archive

Historical record of archived Done/Defer kanban cards for this component (CARD-0193's archiving process, migrated to this dedicated file by CARD-0290 — previously these were appended directly into `CLAUDE.md`, which grew unboundedly and stopped being practical to read in full). **Not read as part of routine Session Start or component-session startup** (`JCTsh-Component-Session-Start.md`) — on-demand lookup only. See this component's own `CLAUDE.md` for current, curated context.

---

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

**Archived from `tos/kanban-board.md` on 2026-09-22 (CARD-0193)** — 6824B, over the 5000B size threshold.

### CARD-0326 · [enhancement] [docker] Per-host Docker daemon config — the repo tracks only the Pi's, and the two hosts have genuinely diverged — RESOLVED ~~2026-09-22 09:50 MST~~ 2026-09-22 09:49 MST
**Status:** Done

**Raised 2026-09-22 09:40 MST (ops cluster session startup), answering a question `core/docker/README.md` had already written down but never resolved:** its closing note asked "worth confirming whether the two hosts' real configs have actually diverged, or whether this file simply needs updating to match." Checked live this session — **they have genuinely diverged, and correctly so:**

| | Pi (`/etc/docker/daemon.json`) | M8 (`/etc/docker/daemon.json`) |
|---|---|---|
| `dns` | `8.8.8.8`, `8.8.4.4` | `8.8.8.8`, `8.8.4.4` |
| `data-root` | `/mnt/jctsh-logs/docker` | *(absent)* |
| `log-driver` | *(absent — Docker's default `json-file`)* | `journald` |

Neither difference is drift to correct. `data-root` is Pi-only because it exists to keep Docker's bulk off the SD card (CARD-0159) — the M8 has no SD card and no such constraint. `log-driver: journald` is M8-only because CARD-0272 applied it M8-wide and never scoped the Pi (now CARD-0327). So **one file cannot represent both hosts** — and the live consequence is that the M8's real Docker daemon config is **not version-controlled at all**: no recovery copy if the M8's `/etc` is lost, and no diffable record of what CARD-0272 actually changed on disk.

**Design decided 2026-09-22 09:40 MST (Joseph, via AskUserQuestion — per-host files under `hosts/`, chosen over suffixed files in `core/docker/` and over documenting the divergence in place):** each host's real config lives in its own `hosts/<host>/daemon.json`, matching the existing `hosts/<name>/` pattern and the unprefixed-filename convention (`JCTsh-Operating-System.md`'s Documentation Structure section — the path already disambiguates, so `daemon.pi1.json` would just repeat it). `core/docker/` keeps `containerd-config.toml` (genuinely Pi-only, no M8 counterpart) and its `README.md` becomes the shared explainer and deploy reference pointing at both. The "keep one file, document the divergence" option was rejected for the specific reason that it leaves the M8's config untracked — which is the actual defect here, not the documentation gap.

**Explicitly not in scope:** changing either host's *running* config. This card moves and accurately records what is already live on each machine — it applies nothing and restarts nothing. Whether the Pi should also get `journald` is CARD-0327; whether the M8 should also pin `data-root` is a non-question (no SD card, no reason).

**Done when:** `hosts/pi1/daemon.json` and `hosts/m8/daemon.json` each match that host's live `/etc/docker/daemon.json` (verified by a real `diff` against each host, not by assuming the copy is right), `core/docker/README.md`'s Files table and Deploy section name the correct per-host file and no longer carry the now-answered "not yet reflected here" open question, and the old single `core/docker/daemon.json` is gone with nothing still pointing at it — root `CLAUDE.md`'s Core Files list names it explicitly and must be updated in the same pass.

**Built and verified live, ~~2026-09-22 09:50 MST~~ 2026-09-22 09:49 MST (corrected 2026-09-22 10:35 MST, this session's own timestamp-hazard check, per the TZ= sweep raised on CARD-0329) — all four "Done when" criteria met, each checked rather than assumed:**
1. `hosts/pi1/daemon.json` and `hosts/m8/daemon.json` created by reading each host's live `/etc/docker/daemon.json` directly over SSH and writing the output verbatim — not hand-transcribed. Verified by piping each host's live file back through `diff` against its repo copy: **both `IDENTICAL`.** Both also confirmed to parse as valid JSON (the same pre-install validation CARD-0272 used, since a malformed `daemon.json` prevents dockerd from starting at all).
2. `core/docker/README.md` rewritten: a per-host comparison table (which setting each host has and *why* the difference is correct, not drift), per-host deploy commands, and a `diff`-based "is the repo copy still accurate" check. The stale "Not yet reflected here" open question is gone — answered, not just deleted.
3. Old `core/docker/daemon.json` removed via `git rm`. `core/docker/` now holds only `containerd-config.toml`, which is genuinely Pi-only and has no M8 counterpart.
4. Every reference chased, not just the ones in this directory: root `CLAUDE.md`'s Core Files list (two separate mentions — the Files entry *and* the DNS-pinning paragraph) updated, plus new `Files` rows in `hosts/m8/README.md` and `hosts/pi1/README.md`. A repo-wide grep for `core/docker/daemon.json` across `*.md`/`*.py`/`*.yml` now returns **nothing** outside the card archives and this board (correctly — those are historical records, not live pointers).

**Nothing on either host was touched** — no config written, no daemon restarted, no container recreated. This card only changed how the repo *records* what was already running, exactly as scoped.

**Reflection — two things worth carrying forward, one of which is really the general lesson here.** The narrow one: the deploy steps now stage through `/tmp` + `sudo install` rather than `scp`ing straight to `/etc/...`, which simply doesn't work on either host (root-owned `/etc`, and neither host permits root SSH) — the old README's one-line `scp core/docker/daemon.json <host>:/etc/docker/daemon.json` could never have run as written. The general one, and the reason this card existed at all: **a "version-controlled copy" of a host config is only true as long as someone re-checks it against the host.** CARD-0272 changed the M8's real `daemon.json` and correctly documented *on its own card* that it had, while the repo copy silently stopped matching any host — and it stayed that way for 8 days, discovered only because a session happened to `cat` both files side by side. The durable fix isn't vigilance, it's the `diff` one-liner now in `core/docker/README.md`: a cheap, explicit way to ask "is this still true?" that didn't previously exist for these files. Worth considering the same treatment for the repo's other version-controlled-copy-of-a-live-file directories (`core/mqtt/`, `core/node-red/`, `core/homeassistant/`), which have exactly the same drift exposure and, as far as this card checked, no equivalent verification step either — not opened as a card yet, noted here rather than lost.

**Related:** CARD-0272 (put `log-driver: journald` on the M8 without updating the repo copy — the immediate cause), CARD-0159 (put `data-root` on the Pi — the other half of the divergence), CARD-0327 (the Pi-journald question this deliberately split off), CARD-0096 (created `hosts/m8/` and `hosts/pi1/`, the pattern this follows).

---

