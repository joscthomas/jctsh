#!/usr/bin/env python3
"""CARD-0344: Node-RED update check -- covers Node-RED itself (installed
via `npm install -g`, so the Pi's apt-based OS check never sees it) and its
palette nodes (`node-red-node-*`/`node-red-contrib-*`, installed locally
into /home/pi/.node-red's own package.json). Same notify-only policy and
7-day reminder throttle as every other maintenance check in this repo
(container_update_check.py, pi-maintenance-check.py).

`npm outdated --json` already does the current/wanted/latest resolution for
both scopes -- no GitHub Releases API needed here, unlike the Docker-image
checks."""
import json, os, subprocess, sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from open_kanban_pr import open_finding_pr  # CARD-0128

COMPONENT   = "jctsh-core"
LOG_TOPIC   = "jctsh/core/log-server/log"
STATE_FILE  = "/root/.jctsh/node-red-update-check.state"
GITHUB_ENV  = "/etc/jctsh/github.env"  # CARD-0128, same credential every other maintenance check uses
NODE_RED_DIR = "/home/pi/.node-red"
REMIND_EVERY = timedelta(days=7)


def _npm_outdated(cwd, global_flag):
    cmd = ["npm", "outdated"] + (["-g"] if global_flag else []) + ["--json"]
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
    # npm outdated exits 1 when it finds anything outdated -- not a real error.
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {}


def _check():
    findings = []
    packages = {}
    for pkg, info in _npm_outdated("/", global_flag=True).items():
        packages[pkg] = info
    for pkg, info in _npm_outdated(NODE_RED_DIR, global_flag=False).items():
        packages[pkg] = info
    return packages


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

packages = _check()
new_state = dict(state)
findings = []
pending_updates = {}
resolved = []
last_current = dict(state.get("_last_current", {}))
now = datetime.now(timezone.utc)

for name, info in packages.items():
    current, latest = info.get("current"), info.get("latest")
    if not current or not latest:
        continue
    pending_updates[name] = {"pending": current != latest, "current": current, "latest": latest}

    prior_current = last_current.get(name)
    if prior_current is not None and prior_current != current:
        resolved.append(f"{name}: now running {current}")
    last_current[name] = current

    if current == latest:
        new_state.pop(name, None)
        continue
    prior = state.get(name, {})
    same_version = prior.get("version") == latest
    due = True
    if same_version:
        last = datetime.fromisoformat(prior["notified_at"])
        due = now - last >= REMIND_EVERY
    if same_version and not due:
        continue
    findings.append(f"{name}: {latest} available (running {current})")
    new_state[name] = {"version": latest, "notified_at": now.isoformat()}

new_state["_last_current"] = last_current

# Packages that dropped out of npm's outdated list entirely (not just
# resolved to a new current version) also need their stale pending-update
# fact cleared -- otherwise /status's Pending Update column keeps showing
# an update that npm no longer reports at all.
for stale_name in set(state) - set(packages) - {"_last_current", "_pr"}:
    pending_updates.setdefault(stale_name, {"pending": False, "current": None, "latest": None})
    new_state.pop(stale_name, None)


def _publish(topic, payload, retain=False):
    cmd = ["mosquitto_pub", "-h", "127.0.0.1", "-p", "1883",
           "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"], "-t", topic, "-m", payload]
    if retain:
        cmd[1:1] = ["-r", "-q", "1"]
    subprocess.run(cmd, check=True, timeout=10)


for name, info in pending_updates.items():
    try:
        _publish(f"jctsh/core/{COMPONENT}/pending-update/{name}", json.dumps(info), retain=True)
    except Exception as e:
        print(f"Failed to publish pending-update state for {name}: {e}")

if resolved:
    resolved_message = f"Node-RED update: {'; '.join(resolved)}"
    try:
        _publish(LOG_TOPIC, json.dumps({"component": COMPONENT, "category": "System", "message": resolved_message}))
        print(f"Notified: {resolved_message}")
    except Exception as e:
        print(f"Failed to publish resolved notice: {e}")

if not findings:
    print("Nothing pending.")
else:
    message = f"Node-RED update(s) pending: {'; '.join(findings)}"
    try:
        _publish(LOG_TOPIC, json.dumps({"component": COMPONENT, "category": "System", "message": message}))
        print(f"Notified: {message}")
    except Exception as e:
        print(f"Failed to publish: {e}")

    try:
        gh_env = {}
        with open(GITHUB_ENV) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    gh_env[k] = v
        fingerprint = json.dumps(sorted(findings))
        prior_pr_state = new_state.get("_pr", {})
        pr_state, pr_url = open_finding_pr(
            COMPONENT, message, fingerprint, gh_env["GITHUB_PAT"], prior_pr_state,
        )
        new_state["_pr"] = pr_state
        if pr_url:
            print(f"Opened kanban PR: {pr_url}")
    except FileNotFoundError:
        pass  # GITHUB_ENV not set up yet
    except Exception as e:
        print(f"CARD-0128 PR step failed (notification above still succeeded): {e}")

os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
with open(STATE_FILE, "w") as f:
    json.dump(new_state, f)
