#!/usr/bin/env python3
"""JCTsh Pi Docker/containerd image pull -- CARD-0269, formalizing CARD-0268.

Generic, reusable pull mechanism for any Docker-based service running on
the Pi (a 3B+ whose 4 USB ports and onboard Ethernet all share one
internal USB 2.0 hub -- CARD-0264/CARD-0268). Pulling a new image on this
host is genuinely risky in two independent, confirmed ways:

1. I/O contention: a bulk pull competes with a live container's own reads
   on the same physical bus. Confirmed live during CARD-0266's HA update --
   HA's own healthcheck started timing out mid-pull.
2. A real dockerd bug (Docker 29.6.1, confirmed reproducible, survives a
   full host reboot): after a clean manifest fetch, an OCI "referrers"
   404 followed by a manifest-digest 404 makes dockerd's own pull
   orchestration hang silently for 5+ minutes. `docker pull`/
   `docker compose pull` are NOT safe to use on this host as a result.

Both are addressed here, not worked around ad hoc each time:
- Uses `ctr -n moby images pull` (containerd's own lower-level pull),
  which bypasses dockerd's stuck orchestration entirely -- the confirmed
  working fix for problem 2.
- Wraps it in `ionice -c3` (idle I/O class) so it can't starve a live
  container's own reads even if run while something's up -- the cheapest
  targeted fix for problem 1 (CARD-0268 fix option 1).

Usage:
    sudo pi-image-pull.py <image:tag> [--recreate SERVICE] [--compose-dir DIR]
    sudo pi-image-pull.py <image:tag> --schedule "2026-09-21 03:30:00" [--recreate SERVICE]

Examples:
    # Pull now, don't touch any running container.
    sudo pi-image-pull.py ghcr.io/home-assistant/home-assistant:stable

    # Pull now and recreate the homeassistant service from /home/pi/docker-compose.yml.
    sudo pi-image-pull.py ghcr.io/home-assistant/home-assistant:stable --recreate homeassistant

    # Schedule for the next maintenance window (ahead of the Pi's own
    # Mon 3 AM scheduled reboot, per CARD-0268's fix option 2) instead of
    # running immediately -- a one-shot transient systemd unit, nothing
    # left installed afterward.
    sudo pi-image-pull.py ghcr.io/home-assistant/home-assistant:stable \
        --recreate homeassistant --schedule "2026-09-21 03:30:00"

This script never decides *whether* to apply an update -- that stays a
deliberate, evaluated call made in a normal session (CARD-0268's standing
constraint: "stays a deliberate step that gets triggered after
evaluation"). It only makes the *mechanics* of an already-decided pull
safe and consistent. --schedule still requires this script to be invoked
explicitly when the decision is made; nothing here runs on a recurring
timer.
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


def _load_env():
    env = {}
    with open(ENV_FILE) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env


def _log(message, category="System"):
    """Publish to the log dashboard (mosquitto_pub, matching
    pi-maintenance-check.py's established pattern for this host) --
    best-effort, never fatal to the actual pull/recreate work."""
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


def _unit_name(image):
    return "pi-image-pull-" + image.split("/")[-1].replace(":", "-").replace(".", "-")


def schedule(image, when, recreate, compose_dir):
    unit = _unit_name(image)
    cmd = [
        "systemd-run",
        f"--unit={unit}",
        f"--on-calendar={when}",
        f"--description=JCTsh scheduled image pull: {image}",
        sys.executable, os.path.abspath(__file__), image,
    ]
    if recreate:
        cmd += ["--recreate", recreate, "--compose-dir", compose_dir]
    print("Scheduling transient unit:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"Scheduled as '{unit}' for {when}. No timer file installed -- "
          f"it's a one-shot transient unit that removes itself after running. "
          f"Check on it later with: systemctl status {unit}  /  journalctl -u {unit}")


def pull(image):
    _log(f"Image pull starting: {image} (ionice-wrapped ctr, per CARD-0268/CARD-0269)")
    t0 = time.time()
    result = subprocess.run(["ionice", "-c3", "ctr", "-n", "moby", "images", "pull", image])
    elapsed = time.time() - t0
    if result.returncode != 0:
        _log(f"Image pull FAILED: {image} (exit {result.returncode}, {elapsed:.0f}s)", category="Alert")
        return False
    _log(f"Image pull complete: {image} ({elapsed:.0f}s)")
    return True


def _container_status(name):
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name=^{name}$", "--format", "{{.Names}}"],
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def _fix_stale_temp_name(service):
    """CARD-0268's real finding: docker compose up -d can leave a
    container under a temporary auto-generated name (`<short-id>_service`)
    instead of the compose file's real container_name, if the target name
    was transiently still held by the outgoing container during a
    stop/recreate race. Detect and correct it rather than leaving the
    service running under the wrong name."""
    if _container_status(service):
        return  # already correctly named
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name=_{service}$",
         "--format", "{{.Names}}\t{{.CreatedAt}}"],
        capture_output=True, text=True,
    )
    candidates = [line.split("\t")[0] for line in result.stdout.strip().splitlines() if line]
    if not candidates:
        return
    temp_name = candidates[0]
    print(f"Container found under temporary name '{temp_name}' -- renaming to '{service}' (CARD-0268 known rough edge)")
    subprocess.run(["docker", "stop", temp_name], check=False)
    subprocess.run(["docker", "rename", temp_name, service], check=True)
    subprocess.run(["docker", "start", service], check=True)


def _wait_for_health(service, timeout=300, interval=10):
    has_health = subprocess.run(
        ["docker", "inspect", service, "--format", "{{if .State.Health}}yes{{end}}"],
        capture_output=True, text=True,
    ).stdout.strip()
    if has_health != "yes":
        status = subprocess.run(
            ["docker", "inspect", service, "--format", "{{.State.Status}}"],
            capture_output=True, text=True,
        ).stdout.strip()
        return status == "running"

    deadline = time.time() + timeout
    while time.time() < deadline:
        status = subprocess.run(
            ["docker", "inspect", service, "--format", "{{.State.Health.Status}}"],
            capture_output=True, text=True,
        ).stdout.strip()
        if status == "healthy":
            return True
        if status == "unhealthy":
            return False
        time.sleep(interval)
    return False


def recreate(service, compose_dir):
    _log(f"Recreating container: {service}")
    ok = False
    for attempt in (1, 2):
        result = subprocess.run(["docker", "compose", "up", "-d", service], cwd=compose_dir)
        if result.returncode == 0:
            ok = True
            break
        if attempt == 1:
            print("Recreate failed once (often a transient stop-event race, per CARD-0268) -- retrying in 5s...")
            time.sleep(5)
    if not ok:
        _log(f"Container recreate FAILED after retry: {service}", category="Alert")
        return False

    _fix_stale_temp_name(service)

    if not _wait_for_health(service):
        _log(f"Container '{service}' did not reach a healthy/running state within timeout", category="Alert")
        return False

    _log(f"Container '{service}' recreated and healthy")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", help="Full image ref, e.g. ghcr.io/home-assistant/home-assistant:stable")
    parser.add_argument("--recreate", metavar="SERVICE",
                         help="docker compose service name to recreate after a successful pull")
    parser.add_argument("--compose-dir", default="/home/pi",
                         help="directory containing docker-compose.yml for --recreate (default: /home/pi)")
    parser.add_argument("--schedule", metavar="WHEN",
                         help='systemd OnCalendar spec to run this later instead of now '
                              '(e.g. "2026-09-21 03:30:00") -- schedules a one-shot transient '
                              'unit and exits immediately; nothing runs until then')
    args = parser.parse_args()

    if os.geteuid() != 0:
        print("This script touches containerd/Docker state directly -- run with sudo.", file=sys.stderr)
        sys.exit(1)

    if args.schedule:
        schedule(args.image, args.schedule, args.recreate, args.compose_dir)
        return

    if not pull(args.image):
        sys.exit(1)

    if args.recreate:
        if not recreate(args.recreate, args.compose_dir):
            sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
