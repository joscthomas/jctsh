#!/usr/bin/env python3
import json, os, shutil, subprocess, sys, time
import paho.mqtt.client as mqtt

BROKER    = "192.168.1.117"
PORT      = 1883
COMPONENT = "photo-server"
LOG_TOPIC = f"jctsh/server/{COMPONENT}/log"
HB_TOPIC  = f"jctsh/server/{COMPONENT}/heartbeat"
USERNAME  = "photo-server"

CONTAINERS = [
    "immich_server", "immich_postgres", "immich_machine_learning", "immich_redis",
    # CARD-0088: hike-izer-web serves Hike-izer's HTML (exposed via Tailscale
    # Funnel, not a container -- so only one container to check here). It
    # defines its own HEALTHCHECK (docker-compose.yml) -- without one,
    # docker inspect's health status comes back empty, which this script's
    # `elif status != "healthy"` check would treat as unhealthy every cycle.
    "hike-izer-web",
    # CARD-0086: webhook receiver for automatic hike-end triggering, second
    # service in the same hike-izer-web compose project. Also defines its
    # own HEALTHCHECK (python3 hitting its /health endpoint) for the same
    # reason as hike-izer-web above.
    "hike-izer-orchestrator",
]

# Backup drives (CARD-0030) — Immich itself never touches these, only the standalone
# photo-library-backup.sh script does, so the container-level storage check above has no
# visibility into them at all. CARD-0046: this went undetected during the 2026-07-10
# drive-swap incident, when Momentus suffered a real hardware I/O failure with zero
# dashboard visibility until it was found by chance while troubleshooting something else.
BACKUP_MOUNTS = {
    "backup-robin":  "/mnt/photo-library-backup",
    "backup-joseph": "/mnt/photo-library-backup-joseph",
}

# CARD-0051: all three mounts, checked for capacity in addition to the read/write
# checks above — read/write only confirms a mount is *working*, not how full it is.
CAPACITY_MOUNTS = {"primary": "/mnt/photo-library", **BACKUP_MOUNTS}
CAPACITY_THRESHOLD_PCT = 90

# CARD-0051: photo-library-backup.sh touches this only on a fully-successful run
# (both rsync jobs exit 0) — its per-run success/failure report (CARD-0040) doesn't
# cover the run simply never happening (cron broken, script missing, host down over
# the scheduled window). 9 days = one missed weekly Sunday 2am run + 2-day grace.
BACKUP_STAMP = "/home/jct/photo-library-backup-success.stamp"
BACKUP_STALE_DAYS = 9

env = {}
with open("/etc/jctsh/heartbeat.env") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v

with open("/proc/uptime") as f:
    secs = int(float(f.read().split()[0]))
uptime = f"{secs // 3600}h {(secs % 3600) // 60}m"

unhealthy = []
# CARD-0124: self-healed-this-cycle events, tracked separately from unhealthy
# so a fully-recovered cycle doesn't render identically to a still-broken one
# (both used to just be "Immich degraded - ..." either way, with no visual
# distinction on the dashboard between "still wrong, look now" and "this
# happened and already fixed itself"). See the status/category decision below.
recovered = []

# CARD-0124: host-side mount-presence check, ahead of everything else below.
# The 2026-07-30 incident showed a real gap: the primary drive dropped off USB,
# reconnected 5s later at the bus level, but nothing remounted it at
# /mnt/photo-library — Docker's health check stayed "healthy" (API-only) and
# even the existing storage write-test (below) only ever reported a generic
# I/O error, never "the mount itself is gone". This runs first, synchronously,
# in the same invocation — no cross-run state needed, since a fresh process
# starts every 30 min via the systemd timer anyway. That's also the flap
# guard: worst case this fires once per scheduled tick, each occurrence
# separately logged, never a tight retry loop.
_primary_remounted = False
for _label, _mount in CAPACITY_MOUNTS.items():
    if os.path.ismount(_mount):
        continue
    try:
        # -n (non-interactive): fail fast with a clean nonzero exit if the
        # NOPASSWD sudoers entry isn't set up, instead of hanging forever
        # with no TTY to prompt (confirmed live 2026-07-31).
        result = subprocess.run(
            ["sudo", "-n", "/usr/bin/mount", _mount],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and os.path.ismount(_mount):
            recovered.append(f"{_label}-mount:auto-remounted")
            if _label == "primary":
                _primary_remounted = True
        else:
            err = (result.stderr or result.stdout or "unknown error").strip()[:200]
            unhealthy.append(f"{_label}-mount:missing, remount-failed({err})")
    except Exception as e:
        unhealthy.append(f"{_label}-mount:missing, remount-error({e})")

# Guarded restart, primary only: only the primary is bind-mounted into a
# container (immich_server) — the backup mounts are touched only by
# photo-library-backup.sh, never a running container, so a remount alone is
# enough for them. Docker bind mounts don't pick up a host remount that
# happens after the container started (same root-cause class as CARD-0046),
# so immich_server needs an explicit restart to actually see the fresh mount.
# Triggered only by this specific transition (was missing, just remounted) —
# never a blind retry-on-every-failed-check loop. No sudo needed for this
# one: jct is already in the docker group.
if _primary_remounted:
    try:
        result = subprocess.run(
            ["docker", "restart", "immich_server"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            recovered.append("immich_server:auto-restarted-after-remount")
            time.sleep(5)  # give it a moment before the health/storage checks below run
        else:
            err = (result.stderr or result.stdout or "unknown error").strip()[:200]
            unhealthy.append(f"immich_server:restart-failed({err})")
    except Exception as e:
        unhealthy.append(f"immich_server:restart-error({e})")

# CARD-0124: if we just restarted immich_server ourselves above, it's expected
# to briefly report "starting" rather than "healthy" — that's our own
# in-progress recovery, not a new/different problem, so it belongs in
# `recovered` (still visible) rather than `unhealthy` (which would otherwise
# keep this cycle flagged as still-degraded for a transient state CARD-0032's
# own live test already showed clears within about a minute).
_just_restarted_primary = "immich_server:auto-restarted-after-remount" in recovered
for name in CONTAINERS:
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", name],
            capture_output=True, text=True, timeout=10,
        )
        status = result.stdout.strip()
        if result.returncode != 0:
            unhealthy.append(f"{name}:not found")
        elif status != "healthy":
            if name == "immich_server" and _just_restarted_primary and status == "starting":
                recovered.append(f"immich_server:{status}-after-restart")
            else:
                unhealthy.append(f"{name}:{status}")
    except Exception as e:
        unhealthy.append(f"{name}:error({e})")

# Docker's health check only pings the Immich API — it doesn't touch /data, so a broken
# bind mount (e.g. the USB drive dropping out mid-session) still reports "healthy". Write,
# read, and remove a marker file through the container's own mount to catch that case
# directly. Only run if immich_server itself is confirmed up, since a missing container
# would make this fail for the same reason already captured above.
if not any(u.startswith("immich_server:") for u in unhealthy):
    try:
        result = subprocess.run(
            ["docker", "exec", "immich_server", "sh", "-c",
             "echo ok > /data/upload/.heartbeat_check "
             "&& cat /data/upload/.heartbeat_check > /dev/null "
             "&& rm -f /data/upload/.heartbeat_check"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "unknown error").strip()[:200]
            unhealthy.append(f"storage:{err}")
    except Exception as e:
        unhealthy.append(f"storage:error({e})")

# Backup drives are mounted directly on the host, not inside a container — Immich never
# touches them, so this is plain host-level file I/O, not docker exec like the primary
# check above. Same write/read/remove pattern.
for label, mount in BACKUP_MOUNTS.items():
    marker = os.path.join(mount, ".heartbeat_check")
    try:
        with open(marker, "w") as f:
            f.write("ok")
        with open(marker) as f:
            f.read()
        os.remove(marker)
    except Exception as e:
        unhealthy.append(f"{label}:{str(e)[:200]}")

# CARD-0051: capacity check, separate from the read/write checks above — a mount can
# be perfectly writable right up until the moment it's actually full.
for label, mount in CAPACITY_MOUNTS.items():
    try:
        usage = shutil.disk_usage(mount)
        pct_used = usage.used / usage.total * 100
        if pct_used >= CAPACITY_THRESHOLD_PCT:
            unhealthy.append(f"{label}-capacity:{pct_used:.0f}% used")
    except Exception as e:
        unhealthy.append(f"{label}-capacity:error({e})")

# CARD-0051: backup staleness — absence of a recent successful run, not covered by
# photo-library-backup.sh's own per-run success/failure report (CARD-0040).
try:
    age_days = (time.time() - os.path.getmtime(BACKUP_STAMP)) / 86400
    if age_days >= BACKUP_STALE_DAYS:
        unhealthy.append(f"backup:stale ({age_days:.1f}d since last success)")
except FileNotFoundError:
    unhealthy.append("backup:stale (no successful run recorded)")
except Exception as e:
    unhealthy.append(f"backup:error({e})")

if unhealthy:
    # Still genuinely wrong right now, regardless of any partial self-heal —
    # this is the one status that should actually draw the eye.
    status = "degraded"
    category = "Alert"
    log_message = f"Immich degraded - {', '.join(unhealthy)}"
    if recovered:
        log_message += f" (also auto-recovered this cycle: {', '.join(recovered)})"
elif recovered:
    # CARD-0124: everything that broke this cycle already fixed itself —
    # genuinely healthy right now, so System/"online" (not Alert/"degraded"),
    # but distinct wording from the plain heartbeat below so it doesn't
    # collapse and stays visible: an automatic recovery is worth seeing, not
    # silently folding into "nothing happened."
    status = "online"
    category = "System"
    log_message = f"Immich recovered - {', '.join(recovered)}"
else:
    status = "online"
    category = "System"
    log_message = "Heartbeat - online."

log_payload = json.dumps({"component": COMPONENT, "category": category, "message": log_message})
hb_payload  = json.dumps({"component": COMPONENT, "uptime": uptime, "status": status})

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, env["MQTT_PASSWORD"])
try:
    client.connect(BROKER, PORT, 10)
    client.loop_start()
    info_log = client.publish(LOG_TOPIC, log_payload, qos=1)
    info_hb  = client.publish(HB_TOPIC,  hb_payload,  qos=1)
    info_log.wait_for_publish(timeout=5)
    info_hb.wait_for_publish(timeout=5)
    client.loop_stop()
    client.disconnect()
    print(f"Heartbeat sent. status={status}")
except Exception as e:
    print(f"Failed: {e}", file=sys.stderr)
    sys.exit(1)
