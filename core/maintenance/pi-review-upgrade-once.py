#!/usr/bin/env python3
"""JCTsh Pi review-category package upgrade -- CARD-0351.

One-shot: unholds the review-category packages (Docker/containerd/kernel/
libc6 -- everything CARD-0351's own maintenance check flagged as needing a
deliberate look rather than the routine batch), upgrades exactly those, waits
for `homeassistant` to report healthy, then reboots regardless (logging an
Alert first if health wasn't confirmed in time) so the new kernel actually
takes effect.

Written up only in `kanban-board.md` prose the first time this ran
(2026-09-27), with the actual logic living entirely inside an ad hoc
`systemd-run` transient-unit command -- never a real file on disk. That
transient unit was lost when the Pi's regular Monday 03:00 scheduled reboot
wiped `/run` before the job's own Tuesday 02:00 fire time, silently dropping
the whole job. This script exists so the *logic* survives on disk from now
on, independent of whatever transient timer wrapper schedules it -- the
lesson CARD-0344/CARD-0351 already learned for image pulls (`pi-image-pull.py`)
applied to this one-off job too.

Usage:
    sudo pi-review-upgrade-once.py
    sudo pi-review-upgrade-once.py --schedule "2026-09-29 02:00:00"

Deliberately narrow: only the exact package list below, `apt-get install
--only-upgrade`, never a blanket `apt upgrade`/`apt full-upgrade` -- so
nothing that becomes newly-upgradable between scheduling and firing gets
swept in unintentionally. Re-run with a fresh `--schedule` each time this
maintenance window comes up again; nothing here re-triggers itself.
"""
import argparse
import json
import os
import subprocess
import sys
import time

BROKER = "127.0.0.1"
PORT = 1883
COMPONENT = "jctsh-core"
LOG_TOPIC = "jctsh/core/log-server/log"
ENV_FILE = "/etc/jctsh/log-server.env"

REVIEW_PACKAGES = [
    "containerd.io", "docker-buildx-plugin", "docker-ce", "docker-ce-cli",
    "docker-ce-rootless-extras", "docker-compose-plugin", "libc6", "libc6-dev",
    "linux-base-rpi-2712", "linux-base-rpi-v8", "linux-headers-rpi-2712",
    "linux-headers-rpi-v8", "linux-image-rpi-2712", "linux-image-rpi-v8",
    "linux-libc-dev",
]

HEALTH_WAIT_TIMEOUT_S = 600  # 10 min, per CARD-0351's own design
HEALTH_POLL_INTERVAL_S = 10


def _load_env():
    env = {}
    with open(ENV_FILE) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env


def _log(message, category="System"):
    """Publish to the log dashboard -- best-effort, never fatal to the
    actual upgrade/reboot work (same pattern as pi-image-pull.py's _log)."""
    print(f"[{category}] {message}")
    try:
        env = _load_env()
        payload = json.dumps({"component": COMPONENT, "category": category, "message": message})
        subprocess.run(
            ["mosquitto_pub", "-h", BROKER, "-p", str(PORT),
             "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"],
             "-t", LOG_TOPIC, "-m", payload],
            check=True, timeout=10,
        )
    except Exception as e:
        print(f"[warn] MQTT log failed: {e}", file=sys.stderr)


def schedule(when):
    cmd = [
        "systemd-run",
        "--unit=jctsh-review-upgrade-once",
        f"--on-calendar={when}",
        "--description=JCTsh one-shot review-category package upgrade (CARD-0351)",
        sys.executable, os.path.abspath(__file__),
    ]
    print("Scheduling transient unit:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"Scheduled as 'jctsh-review-upgrade-once' for {when}. No timer file installed -- "
          f"a one-shot transient unit that removes itself after running. "
          f"Only safe if no reboot lands between now and {when} (transient units live in "
          f"/run, wiped on reboot -- exactly what silently dropped this job's first run). "
          f"Check on it later with: systemctl status jctsh-review-upgrade-once  /  "
          f"journalctl -u jctsh-review-upgrade-once")


def run():
    held = subprocess.run(["apt-mark", "showhold"], capture_output=True, text=True).stdout.split()
    missing_hold = [p for p in REVIEW_PACKAGES if p not in held]
    if missing_hold:
        _log(f"Review-upgrade: expected packages not currently held, proceeding anyway: {missing_hold}",
             category="Alert")

    _log(f"Review-upgrade starting: unholding and upgrading {len(REVIEW_PACKAGES)} packages "
         f"({', '.join(REVIEW_PACKAGES)})")
    subprocess.run(["apt-mark", "unhold"] + REVIEW_PACKAGES, check=True)

    t0 = time.time()
    result = subprocess.run(["apt-get", "install", "--only-upgrade", "-y"] + REVIEW_PACKAGES)
    elapsed = time.time() - t0
    if result.returncode != 0:
        _log(f"Review-upgrade: apt-get install --only-upgrade FAILED (exit {result.returncode}, "
             f"{elapsed:.0f}s) -- not rebooting, needs a look", category="Alert")
        return
    _log(f"Review-upgrade: package upgrade complete ({elapsed:.0f}s)")

    _log(f"Review-upgrade: waiting up to {HEALTH_WAIT_TIMEOUT_S // 60} min for homeassistant "
         f"to report healthy before rebooting")
    healthy = False
    waited = 0
    while waited < HEALTH_WAIT_TIMEOUT_S:
        status = subprocess.run(
            ["docker", "inspect", "homeassistant", "--format", "{{.State.Health.Status}}"],
            capture_output=True, text=True,
        ).stdout.strip()
        if status == "healthy":
            healthy = True
            break
        time.sleep(HEALTH_POLL_INTERVAL_S)
        waited += HEALTH_POLL_INTERVAL_S

    if healthy:
        _log(f"Review-upgrade: homeassistant confirmed healthy after {waited}s, rebooting now")
    else:
        _log(f"Review-upgrade: homeassistant did NOT confirm healthy within "
             f"{HEALTH_WAIT_TIMEOUT_S // 60} min -- rebooting anyway, check HA manually", category="Alert")

    subprocess.run(["systemctl", "reboot"], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--schedule", metavar="WHEN",
                         help='Schedule for a later time instead of running now '
                              '(e.g. "2026-09-29 02:00:00") -- schedules a one-shot transient '
                              'systemd unit. No timer file is left installed.')
    args = parser.parse_args()

    if args.schedule:
        schedule(args.schedule)
    else:
        run()


if __name__ == "__main__":
    main()
