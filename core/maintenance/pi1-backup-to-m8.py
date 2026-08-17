#!/usr/bin/env python3
"""CARD-0177: weekly backup of Pi1's HA + Mosquitto state to the M8.

Real gap found by CARD-0172's disaster-recovery audit: `/mnt/jctsh-logs/
homeassistant` (full HA `/config` -- `.storage/` registries, every
integration's OAuth/pairing state, recorder history) and `/mnt/jctsh-logs/
mosquitto` (broker persistence) had zero backup. Both are small (well under
100MB combined at the time this was built), so a weekly mirror is cheap
against a real, painful-if-triggered consequence.

Pushes from the Pi to the M8 over a dedicated, narrowly-scoped SSH key
(`/home/pi/.ssh/pi1_backup_ed25519`), authorized on the M8 side via `rrsync`
(`command="rrsync /home/jct/pi1-backup/",restrict` in `~/.ssh/authorized_keys`)
-- confirmed live that this key cannot get a shell (`SSH_ORIGINAL_COMMAND
does not run rsync`) and cannot write outside that one directory tree (a
destination path outside it gets silently re-rooted inside the sandbox by
rrsync itself, not actually escaping -- confirmed with a real dry-run test,
not just read from rrsync's docs).

Same MQTT log pattern as this Pi's other maintenance scripts
(pi-maintenance-check.py): mosquitto_pub via /etc/jctsh/log-server.env,
component jctsh-core, same log topic every core-level check already uses.
"""
import json
import subprocess
import sys

BROKER = "127.0.0.1"
PORT = 1883
COMPONENT = "jctsh-core"
LOG_TOPIC = "jctsh/core/log-server/log"

SSH_KEY = "/home/pi/.ssh/pi1_backup_ed25519"
# CARD-0177: the M8 side authorizes this key via `rrsync /home/jct/pi1-backup/`
# (see the module docstring), which re-roots *any* path the client sends at
# that directory -- confirmed live the hard way: an absolute-looking
# destination path here doubled up into .../pi1-backup/home/jct/pi1-backup/...
# and failed outright (no such directory). Destination paths below are bare
# and relative for exactly that reason -- they already resolve inside the
# sandbox without repeating its root.
M8_DEST = "jct@192.168.1.165:"

# (source, destination subdir under M8_DEST) -- trailing slashes matter for
# rsync's "copy contents of" semantics, not the directory itself.
JOBS = [
    ("/mnt/jctsh-logs/homeassistant/", f"{M8_DEST}homeassistant/"),
    ("/mnt/jctsh-logs/mosquitto/", f"{M8_DEST}mosquitto/"),
]

env = {}
with open("/etc/jctsh/log-server.env") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v


def _publish(category, message):
    payload = json.dumps({"component": COMPONENT, "category": category, "message": message})
    subprocess.run(
        ["mosquitto_pub", "-h", BROKER, "-p", str(PORT),
         "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"],
         "-t", LOG_TOPIC, "-m", payload],
        check=True, timeout=10,
    )


# BatchMode -- never prompt (this runs unattended via systemd); StrictHostKeyChecking
# accept-new -- trust the M8's host key on first contact (already trusted as of this
# script's own deployment) but reject outright if it ever changes, rather than either
# blindly trusting every connection or blocking on a prompt nothing will answer.
ssh_cmd = f"ssh -i {SSH_KEY} -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"

errors = []
for src, dst in JOBS:
    result = subprocess.run(
        ["rsync", "-a", "--delete", "-e", ssh_cmd, src, dst],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        errors.append(f"{src}: exit {result.returncode}: {result.stderr.strip()[-300:]}")

if errors:
    message = "Pi1 backup to M8 failed: " + "; ".join(errors)
    print(message, file=sys.stderr)
    try:
        _publish("Alert", message)
    except Exception as e:
        print(f"Also failed to publish alert: {e}", file=sys.stderr)
    raise SystemExit(1)

message = "Pi1 backup to M8: complete. homeassistant + mosquitto synced."
print(message)
_publish("System", message)
