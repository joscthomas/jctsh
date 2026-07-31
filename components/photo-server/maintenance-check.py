#!/usr/bin/env python3
"""JCTsh M8 OS/firmware maintenance check (CARD-0095).

Checks apt-upgradable packages, the /var/run/reboot-required flag, and
pending fwupd firmware updates. Notify-only, same shape as
immich-update-check.py -- never applies anything itself. Applying is a
deliberate human step (see CARD-0095's policy note on why: Docker,
kernel, and firmware updates specifically want judgment, not a script
guessing which of the household's live services could be affected).

A state file throttles repeat notifications for an *unchanged* finding
set (REMIND_EVERY), but any genuinely new finding -- a new package
entering the review list, the reboot-required flag flipping on, a new
firmware update appearing -- always notifies immediately regardless of
the throttle, since the fingerprint changes.
"""
import json, os, subprocess
from datetime import datetime, timezone, timedelta
import paho.mqtt.client as mqtt

BROKER    = "192.168.1.117"
PORT      = 1883
COMPONENT = "photo-server"
LOG_TOPIC = f"jctsh/server/{COMPONENT}/log"
USERNAME  = "photo-server"

STATE_FILE   = "/home/jct/.jctsh/maintenance-check.state"
REMIND_EVERY = timedelta(days=7)

# CARD-0095's risk-tiering: packages matching these get pulled out of the
# routine low-risk count and flagged for deliberate review -- a Docker
# daemon restart touches every running container, a kernel/libc6 update is
# why a reboot becomes required, matching the card's own reasoning.
#
# "linux-" (not the narrower "linux-image"/"linux-generic"), fixed 2026-07-31
# after a real incident on the Pi sibling script: the narrower patterns
# missed linux-headers-*/linux-libc-dev, which pulled the actual kernel image
# and libc6 in as automatic apt dependencies while miscategorized as
# "routine". Never actually triggered here (no linux-headers packages were
# pending on the M8 tonight), but it's the same latent bug in the same
# pattern -- fixed for consistency, not because it's bitten this host yet.
REVIEW_PATTERNS = ("docker", "containerd", "linux-", "libc6")

env = {}
with open("/etc/jctsh/heartbeat.env") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v


def _apt_upgradable():
    result = subprocess.run(
        ["apt", "list", "--upgradable"], capture_output=True, text=True, timeout=30,
    )
    lines = [l for l in result.stdout.splitlines() if l and not l.startswith("Listing")]
    review = sorted({l.split("/")[0] for l in lines if any(p in l for p in REVIEW_PATTERNS)})
    routine = len(lines) - len(review)
    return routine, review


def _reboot_required():
    return os.path.exists("/var/run/reboot-required")


def _firmware_updates():
    result = subprocess.run(
        ["fwupdmgr", "get-upgrades", "--json"], capture_output=True, text=True, timeout=30,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    names = []
    for device in data.get("Devices", []):
        for release in device.get("Releases", []):
            names.append(f"{device.get('Name', 'device')}: {release.get('Summary', 'update available')}")
    return sorted(names)


routine_count, review_pkgs = _apt_upgradable()
reboot_needed = _reboot_required()
firmware = _firmware_updates()

findings = []
if review_pkgs:
    findings.append(f"{len(review_pkgs)} package(s) need review: {', '.join(review_pkgs)}")
if reboot_needed:
    findings.append("reboot required")
if firmware:
    findings.append(f"{len(firmware)} firmware update(s) available: {'; '.join(firmware)}")

if not findings and routine_count == 0:
    print("Nothing pending.")
    raise SystemExit(0)

fingerprint = json.dumps(
    {"routine": routine_count, "review": review_pkgs, "reboot": reboot_needed, "fw": firmware},
    sort_keys=True,
)

try:
    with open(STATE_FILE) as f:
        state = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    state = {}

now = datetime.now(timezone.utc)
same_finding = state.get("fingerprint") == fingerprint
if same_finding:
    last_notified = datetime.fromisoformat(state["notified_at"])
    due_for_reminder = now - last_notified >= REMIND_EVERY
else:
    due_for_reminder = True

if same_finding and not due_for_reminder:
    days_left = REMIND_EVERY - (now - last_notified)
    print(f"Already notified about this exact finding set -- next reminder in {days_left.days}d.")
    raise SystemExit(0)

routine_note = f"{routine_count} routine update(s) pending. " if routine_count else ""
if findings:
    message = f"M8 maintenance: {routine_note}{'; '.join(findings)}"
    category = "Alert"
else:
    message = f"M8 maintenance: {routine_note}nothing needing review."
    category = "System"

payload = json.dumps({"component": COMPONENT, "category": category, "message": message})

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, env["MQTT_PASSWORD"])
client.connect(BROKER, PORT, 10)
client.loop_start()
info = client.publish(LOG_TOPIC, payload, qos=1)
info.wait_for_publish(timeout=5)
client.loop_stop()
client.disconnect()

os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
with open(STATE_FILE, "w") as f:
    json.dump({"fingerprint": fingerprint, "notified_at": now.isoformat()}, f)

print(f"Notified: {message}")
