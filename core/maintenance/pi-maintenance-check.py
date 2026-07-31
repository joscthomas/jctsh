#!/usr/bin/env python3
"""JCTsh Pi OS/firmware maintenance check (CARD-0125, CARD-0095's Pi sibling).

Checks apt-upgradable packages and whether the running kernel is stale.
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

Bug found and fixed same day (2026-07-31), from a real incident: the
review-pattern filter used exact substrings ("linux-image",
"linux-generic") that missed linux-headers-* and linux-libc-dev --
installing those (miscategorized as "routine") pulled in the full
kernel image and libc6 as automatic apt dependencies, exactly the
packages meant to be held back for deliberate review. Broadened to a
"linux-" prefix match, which catches headers/image/libc-dev/base/
kbuild uniformly -- every kernel-adjacent package on this system
happens to share that prefix, confirmed against the real package list.
Separately, /var/run/reboot-required turned out to never exist on
Raspberry Pi OS at all (no update-notifier-common package, unlike
Ubuntu) -- reboot detection is now a direct comparison of the running
kernel (`uname -r`) against installed linux-image-* packages instead.
"""
import json, os, subprocess, sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from open_kanban_pr import open_finding_pr  # CARD-0128

BROKER    = "127.0.0.1"
PORT      = 1883
COMPONENT = "jctsh-core"
LOG_TOPIC = "jctsh/core/log-server/log"

STATE_FILE  = "/root/.jctsh/maintenance-check.state"
GITHUB_ENV  = "/etc/jctsh/github.env"  # CARD-0128: GITHUB_PAT=... -- absent until the token exists, deliberately optional
REMIND_EVERY = timedelta(days=7)

# CARD-0095's risk-tiering, revised 2026-07-31: "linux-" (not the narrower
# "linux-image"/"linux-generic") catches every kernel-adjacent package on
# this system -- linux-image-*, linux-headers-*, linux-libc-dev, linux-base-*,
# linux-kbuild-* all share the prefix, confirmed against the real installed
# package list. The narrower version is what let linux-headers/linux-libc-dev
# through as "routine" and pull the kernel + libc6 in as automatic
# dependencies -- see the module docstring.
REVIEW_PATTERNS = ("docker", "containerd", "linux-", "libc6")

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
    """No update-notifier-common on Raspberry Pi OS, so /var/run/reboot-required
    never exists here (confirmed live 2026-07-31) -- compare the running
    kernel against installed linux-image-* packages instead. True if any
    installed versioned kernel package (e.g. linux-image-6.18.34+rpt-rpi-v8)
    is newer than the one actually running."""
    running = subprocess.run(
        ["uname", "-r"], capture_output=True, text=True, timeout=10
    ).stdout.strip()
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${Package}\n"], capture_output=True, text=True, timeout=10,
    )
    for pkg in result.stdout.splitlines():
        if not pkg.startswith("linux-image-"):
            continue
        candidate = pkg[len("linux-image-"):]
        if not candidate[:1].isdigit() or candidate == running:
            continue  # meta-package (e.g. linux-image-rpi-v8) or already running
        newer = subprocess.run(
            ["dpkg", "--compare-versions", candidate, "gt", running], timeout=5,
        )
        if newer.returncode == 0:
            return True
    return False


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

new_state = {"fingerprint": fingerprint, "notified_at": now.isoformat()}

# CARD-0128: open/refresh a queued kanban PR for real findings (not the
# routine-only "nothing needing review" case) -- deliberately optional,
# not a hard failure, since GITHUB_ENV won't exist until the PAT is
# created; a missing/broken PR step must never take down the Alert
# notification above, which already succeeded by this point.
if findings:
    try:
        gh_env = {}
        with open(GITHUB_ENV) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    gh_env[k] = v
        prior_pr_state = {k: state[k] for k in ("pr_fingerprint", "pr_number") if k in state}
        pr_state, pr_url = open_finding_pr(
            COMPONENT, message, fingerprint, gh_env["GITHUB_PAT"], prior_pr_state,
        )
        new_state.update(pr_state)
        if pr_url:
            print(f"Opened kanban PR: {pr_url}")
    except FileNotFoundError:
        pass  # GITHUB_ENV not set up yet -- CARD-0128 not yet activated
    except Exception as e:
        print(f"CARD-0128 PR step failed (Alert notification above still succeeded): {e}")

os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
with open(STATE_FILE, "w") as f:
    json.dump(new_state, f)

print(f"Notified: {message}")
