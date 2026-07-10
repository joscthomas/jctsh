# photo-server — Operations Guide

Day-to-day maintenance for the GMKtec M8 (`photo-server`, `192.168.1.165`). For build steps see `photo-server-claude-code-instructions.md`; for monitoring see `heartbeat.md`.

## Scheduled Reboot

| Property | Value |
|---|---|
| Managed by | systemd timer (`scheduled-reboot.timer` → `scheduled-reboot.service`) |
| Schedule | Weekly, Monday 4:00 AM (`America/Phoenix`) |
| Action | Publish MQTT notice, then `/sbin/reboot` |

Version-controlled unit files: `core/maintenance/scheduled-reboot-m8.service` (deployed as
`scheduled-reboot.service`), `core/maintenance/scheduled-reboot-m8.timer` (deployed as
`scheduled-reboot.timer`). `Persistent=true` — if the M8 is powered off at the scheduled
time, it reboots on next boot instead of skipping the week.

**Value:** clears memory creep in long-running Docker containers (Immich server/ML), applies pending kernel/package updates from `unattended-upgrades` that need a reboot to take effect, and exercises the boot path regularly so a startup regression (bad mount, container not set to auto-restart) surfaces on a Monday morning instead of during an actual outage.

Staggered one hour behind the Pi's own weekly reboot (Monday 3:00 AM) — the M8's heartbeat script publishes to the Mosquitto broker on the Pi, so overlapping the two would produce a false "M8 down" reading while it's really just the Pi that's mid-reboot.

To check: `systemctl list-timers scheduled-reboot.timer`

All four Immich containers (`immich_server`, `immich_postgres`, `immich_machine_learning`, `immich_redis`) are on Docker's `restart: unless-stopped` policy and come back automatically after reboot — confirmed working 2026-07-08 after a manual power-cycle for outlet reconfiguration (see `keepconnect.md`).

**Dashboard visibility (added 2026-07-08):** `scheduled-reboot.service` publishes
`"Scheduled reboot about to occur."` (component `photo-server`, category `System`) to
`jctsh/server/photo-server/log` immediately before rebooting. A second unit,
`reboot-complete.service` (`core/maintenance/reboot-complete-m8.service`, runs on every
boot via `WantedBy=multi-user.target`, `After=network-online.target`), publishes
`"Boot complete."` to the same topic/component once the M8 has network access to reach
the Pi's broker. Both use the `photo-server` MQTT account already set up for the
heartbeat script (`/etc/jctsh/heartbeat.env`) and the `mosquitto_pub` CLI — required
installing the `mosquitto-clients` apt package (not previously present on the M8; the
heartbeat script uses the Python `paho-mqtt` library instead). Verified live 2026-07-08
via manual `systemctl start reboot-complete.service`.

## Immich Update Check (added 2026-07-10)

| Property | Value |
|---|---|
| Managed by | systemd timer (`immich-update-check.timer` → `immich-update-check.service`) |
| Schedule | Daily, 6:00 AM (`America/Phoenix`) |
| Action | Compare `/api/server/version` against `/api/server/version-check`; publish an MQTT notice if a newer release is available |

Version-controlled files: `components/photo-server/immich-update-check.py` (deployed to
`/usr/local/bin/`), `core/maintenance/immich-update-check.service`,
`core/maintenance/immich-update-check.timer`.

**Deliberately notify-only, not auto-update.** Immich is actively developed and this
instance has already surfaced real bugs in a single patch version (the CARD-0037/0042/0043
gaps, the HEIC distortion issue) — auto-applying updates unattended on a library holding
irreplaceable family photos isn't worth the risk. The actual update (`docker compose pull
&& docker compose up -d` in `~/immich-app`) stays a deliberate, manual step.

**De-duplicated by design** — a state file (`/home/jct/.jctsh/immich-update-check.state`,
not `/etc/jctsh/` since that directory isn't writable by the `jct` user and caused the
first deploy attempt to crash) stores the last-notified version, so the same pending
update doesn't re-fire every day. It only notifies again if an even newer version becomes
available after the first notice.

Message published as component `photo-server`, category `System`, e.g. `"Immich update
available: v3.0.2 (currently running v3.0.1)"`. Verified live 2026-07-10: first run
notified correctly, second run correctly skipped re-notifying for the same version.

## Immich Tags Feature (People Tags from Google Photos)

The Tags feature is **disabled by default** in Immich — nothing shows in the sidebar, the
asset info panel has no Tags section, and `tag` doesn't appear as a search filter option
until it's turned on. Enable via: profile avatar menu → **Account Settings** → **Features**
section → enable **Tags**.

Once enabled, two top-level tags exist: `People` (332 children, one per name Google Photos
had already identified/tagged in the original account, carried over via `immich-go`'s
`--people-tag` flag reading each photo's Takeout JSON `people` field) and
`takeout-20260703T160953Z-3` (the import-batch tag `immich-go` applies automatically,
single label, no children).

**Important: these tags are a separate system from Immich's own ML face-recognition Person
clusters** (`faceDetection`/`facialRecognition`, see CARD-0037 in `backlog.md`). Tagging
`People/<name>` here does not automatically name or link to the corresponding ML cluster —
they don't talk to each other. Tags are static labels carried over from Google's own
historical face-tagging (instant, already complete, searchable by tag once the feature is
on); ML clusters are Immich's own ongoing face-detection/recognition pipeline (needs manual
naming per cluster, catches people Google never had tagged). Use both — tags for what's
already labeled, cluster-naming for the rest.

Also note: Immich's main search bar does **CLIP semantic search** on free text, not a
literal tag/name lookup — typing a person's name there returns whatever the model judges
loosely similar, which is close to random for a name it has no way to recognize. To find
photos by tag, browse the Tags view directly (once enabled) rather than typing the name
into search.

## Router Reboot Coordination

KeepConnect (the router rebooter — see `keepconnect.md`) resets the router on its own weekly schedule, currently landing on a day that has drifted from its original Wednesday setting. This is expected: KeepConnect's "every 7 days" timer appears to restart from *any* reset, scheduled or outage-triggered, so the weekday it lands on shifts over time and can't be relied on as fixed. The Pi and M8 reboot schedule above is intentionally not synchronized to it — a router reboot is a brief (~30 sec cut, ~4 min reconnect) network blip that both machines tolerate regardless of whether they happen to be mid-boot at the same time.
