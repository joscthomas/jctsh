#!/usr/bin/env python3
"""CARD-0344: ESPHome coverage -- two distinct, independently-throttled checks:

1. Per-device divergence (real Alert, 7-day throttle): parses each of the 6
   field devices' most recent "online - ESPHome X" boot line out of the Pi's
   own durable log, and alerts if any device is running something other than
   PINNED_VERSION. This is the CARD-0333/CARD-0335-class risk -- a device
   accidentally flashed off the deliberate pin.

2. Pin-vs-latest (informational only, no kanban PR, 30-day throttle):
   queries ESPHome's GitHub Releases API and logs when a release newer than
   PINNED_VERSION exists. The pin is deliberate (2026.9.0 broke the compile,
   CARD-0333/0335) so this deliberately does NOT escalate to a PR the way
   every other maintenance check here does -- it exists purely so the held
   version doesn't get silently forgotten forever, matching CARD-0257's
   held-update re-notify pattern.

PINNED_VERSION must be kept in sync by hand with the actual pinned pip
version on the Windows workstation (see network/jctsh-network.md-adjacent
component instructions.md files) -- there is no way to check the workstation
install itself from a Pi-side script.
"""
import glob, json, os, re, subprocess, sys, urllib.request
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from open_kanban_pr import open_finding_pr  # CARD-0128

PINNED_VERSION = "2026.4.5"
DEVICES = ["air-quality-monitor", "back-patio-temp-sensor", "front-porch-temp-sensor",
           "garage-radar", "hiking-monitor", "salt-sensor"]

COMPONENT    = "jctsh-core"
LOG_TOPIC    = "jctsh/core/log-server/log"
STATE_FILE   = "/root/.jctsh/esphome-check.state"
GITHUB_ENV   = "/etc/jctsh/github.env"
LOG_GLOB     = "/mnt/jctsh-logs/jctsh.log*"
DEVICE_REMIND_EVERY = timedelta(days=7)
PIN_REMIND_EVERY    = timedelta(days=30)

_LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) MST \| ([^|]+) \| ([^|]+) \| (.*)$"
)
_VERSION_RE = re.compile(r"ESPHome (\S+?)[,\s]")


def _latest_versions():
    """Returns {device: version} for whichever of DEVICES has an
    'online - ESPHome X' line anywhere in the log files, using each
    device's true latest (max timestamp) occurrence, not file order."""
    latest = {}  # device -> (timestamp, version)
    for path in glob.glob(LOG_GLOB):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = _LINE_RE.match(line)
                    if not m:
                        continue
                    ts, component, category, message = m.groups()
                    component = component.strip()
                    if component not in DEVICES or category.strip() != "System":
                        continue
                    vm = _VERSION_RE.search(message)
                    if not vm:
                        continue
                    if component not in latest or ts > latest[component][0]:
                        latest[component] = (ts, vm.group(1))
        except OSError:
            continue
    return {d: v[1] for d, v in latest.items()}


def _esphome_latest_release():
    req = urllib.request.Request(
        "https://api.github.com/repos/esphome/esphome/releases/latest",
        headers={"Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read()).get("tag_name")


env = {}
with open("/etc/jctsh/log-server.env") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v

try:
    with open(STATE_FILE) as f:
        state = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    state = {}

new_state = dict(state)
now = datetime.now(timezone.utc)


def _publish(topic, payload):
    subprocess.run(
        ["mosquitto_pub", "-h", "127.0.0.1", "-p", "1883",
         "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"], "-t", topic, "-m", payload],
        check=True, timeout=10,
    )


# --- Check 1: per-device divergence from the pin -----------------------
versions = _latest_versions()
divergent = {d: v for d, v in versions.items() if v != PINNED_VERSION}
missing = [d for d in DEVICES if d not in versions]

divergence_state = state.get("_divergence", {})
fingerprint = json.dumps(sorted(divergent.items()))
same_finding = divergence_state.get("fingerprint") == fingerprint
due = True
if same_finding and divergent:
    last = datetime.fromisoformat(divergence_state["notified_at"])
    due = now - last >= DEVICE_REMIND_EVERY

if divergent and (not same_finding or due):
    detail = "; ".join(f"{d}: {v}" for d, v in sorted(divergent.items()))
    message = f"ESPHome version drift from pin ({PINNED_VERSION}): {detail}"
    try:
        _publish(LOG_TOPIC, json.dumps({"component": COMPONENT, "category": "Alert", "message": message}))
        print(f"Notified: {message}")
    except Exception as e:
        print(f"Failed to publish: {e}")
    new_state["_divergence"] = {"fingerprint": fingerprint, "notified_at": now.isoformat()}
    try:
        gh_env = {}
        with open(GITHUB_ENV) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    gh_env[k] = v
        prior_pr_state = new_state.get("_pr", {})
        pr_state, pr_url = open_finding_pr(
            COMPONENT, message, fingerprint, gh_env["GITHUB_PAT"], prior_pr_state,
        )
        new_state["_pr"] = pr_state
        if pr_url:
            print(f"Opened kanban PR: {pr_url}")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"CARD-0128 PR step failed (notification above still succeeded): {e}")
elif not divergent:
    new_state.pop("_divergence", None)
    print(f"All {len(versions)}/{len(DEVICES)} reporting devices on pin ({PINNED_VERSION}).")
else:
    print("Divergence already notified, not yet due for a reminder.")

if missing:
    print(f"No ESPHome boot line found for: {', '.join(missing)} (not necessarily a problem -- may just not have rebooted within the log's retention window).")

# --- Check 2: pin vs. latest upstream release (informational only) -----
pin_state = state.get("_pin_check", {})
try:
    latest_release = _esphome_latest_release()
    pin_stale = latest_release and latest_release != PINNED_VERSION
    same_release = pin_state.get("latest") == latest_release
    pin_due = True
    if same_release:
        last = datetime.fromisoformat(pin_state["notified_at"])
        pin_due = now - last >= PIN_REMIND_EVERY
    if pin_stale and (not same_release or pin_due):
        message = (f"ESPHome {latest_release} is available upstream; still pinned at "
                   f"{PINNED_VERSION} (2026.9.0 broke the compile, CARD-0333/0335). "
                   f"Informational only -- revisit the pin deliberately, no action implied.")
        try:
            _publish(LOG_TOPIC, json.dumps({"component": COMPONENT, "category": "System", "message": message}))
            print(f"Notified (informational, no PR): {message}")
        except Exception as e:
            print(f"Failed to publish: {e}")
        new_state["_pin_check"] = {"latest": latest_release, "notified_at": now.isoformat()}
    elif not pin_stale:
        new_state.pop("_pin_check", None)
        print(f"Pin ({PINNED_VERSION}) matches latest upstream release.")
    else:
        print("Pin-vs-latest already notified, not yet due for a reminder.")
except Exception as e:
    print(f"Pin-vs-latest check failed (device-divergence check above is unaffected): {e}")

os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
with open(STATE_FILE, "w") as f:
    json.dump(new_state, f)
