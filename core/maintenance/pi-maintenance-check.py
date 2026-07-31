#!/usr/bin/env python3
"""JCTsh Pi OS/firmware maintenance check (CARD-0125, CARD-0095's Pi sibling).

Checks apt-upgradable packages and the /var/run/reboot-required flag.
Notify-only, never applies anything itself -- same policy as the M8's
components/photo-server/maintenance-check.py.

No firmware-check step here, unlike the M8 version: confirmed live
2026-07-31 that this Pi (a 3B+) has no EEPROM bootloader
(`rpi-eeprom-update` reports "Device does not a have a Raspberry Pi
bootloader EEPROM ... Skipping"). Its boot firmware updates through
the ordinary `raspi-firmware` apt package instead, already covered by
the plain apt-upgradable check below -- nothing extra to check.

Uses mosquitto_pub (not paho-mqtt) and jctsh-core/log-server.env,
matching this Pi's own established pattern (core/homeassistant/
pi-heartbeat.py) rather than the M8 scripts' paho-mqtt + dedicated
per-host account pattern.
"""
import json, os, subprocess
from datetime import datetime, timezone, timedelta

BROKER    = "127.0.0.1"
PORT      = 1883
COMPONENT = "jctsh-core"
LOG_TOPIC = "jctsh/core/log-server/log"

STATE_FILE   = "/root/.jctsh/maintenance-check.state"
REMIND_EVERY = timedelta(days=7)

# CARD-0095's risk-tiering, unchanged: packages matching these get pulled out
# of the routine low-risk count and flagged for deliberate review. Confirmed
# live 2026-07-31 that all these patterns still appear in this Pi's own
# upgradable list (e.g. linux-image-rpi-2712, linux-image-rpi-v8, libc6).
REVIEW_PATTERNS = ("docker", "containerd", "linux-image", "linux-generic", "libc6")

env = {}
with open("/etc/jctsh/log-server.env") as f:
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


routine_count, review_pkgs = _apt_upgradable()
reboot_needed = _reboot_required()

findings = []
if review_pkgs:
    findings.append(f"{len(review_pkgs)} package(s) need review: {', '.join(review_pkgs)}")
if reboot_needed:
    findings.append("reboot required")

if not findings and routine_count == 0:
    print("Nothing pending.")
    raise SystemExit(0)

fingerprint = json.dumps(
    {"routine": routine_count, "review": review_pkgs, "reboot": reboot_needed}, sort_keys=True
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
    message = f"Pi maintenance: {routine_note}{'; '.join(findings)}"
    category = "Alert"
else:
    message = f"Pi maintenance: {routine_note}nothing needing review."
    category = "System"

payload = json.dumps({"component": COMPONENT, "category": category, "message": message})

try:
    subprocess.run(
        ["mosquitto_pub", "-h", BROKER, "-p", str(PORT),
         "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"],
         "-t", LOG_TOPIC, "-m", payload],
        check=True, timeout=10,
    )
except Exception as e:
    print(f"Failed to publish: {e}")
    raise SystemExit(1)

os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
with open(STATE_FILE, "w") as f:
    json.dump({"fingerprint": fingerprint, "notified_at": now.isoformat()}, f)

print(f"Notified: {message}")
