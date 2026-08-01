#!/usr/bin/env python3
"""CARD-0126: Pi-side container-image update check -- Home Assistant.
Shared logic in core/maintenance/container_update_check.py (deployed
alongside this script, same directory, on the actual host). Matches
pi-heartbeat.py's own conventions: mosquitto_pub, jctsh-core component,
log-server.env credentials, runs as root (no User= in its .service)."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from container_update_check import check_services
from open_kanban_pr import open_finding_pr  # CARD-0128

COMPONENT  = "jctsh-core"
LOG_TOPIC  = "jctsh/core/log-server/log"
STATE_FILE = "/root/.jctsh/container-update-check.state"
GITHUB_ENV = "/etc/jctsh/github.env"  # CARD-0128, same credential every other maintenance check uses

SERVICES = [
    {"name": "home-assistant", "container": "homeassistant",
     "source": "home-assistant/core", "version_method": "label"},
]

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

findings, new_state, pending_updates, resolved = check_services(SERVICES, state)

# CARD-0132: retained pending-update state, same pattern CARD-0127 used for
# Immich -- published every run for every successfully-checked service,
# independent of the throttled notification below, so /status's Pending
# Update column reflects current true state instead of "last thing logged."
for name, info in pending_updates.items():
    pending_payload = json.dumps({
        "pending": info["pending"], "current": info["current"], "latest": info["latest"],
    })
    try:
        subprocess.run(
            ["mosquitto_pub", "-h", "127.0.0.1", "-p", "1883",
             "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"],
             "-t", f"jctsh/core/{COMPONENT}/pending-update/{name}",
             "-r", "-q", "1", "-m", pending_payload],
            check=True, timeout=10,
        )
    except Exception as e:
        print(f"Failed to publish pending-update state for {name}: {e}")

# A resolved update leaves a stale "X available" notice as this component's
# Last Reading otherwise -- nothing else would tell the log dashboard the
# finding is out of date, since Last Reading shows whichever message was
# logged last, not current state. Post a one-time "now running" notice so
# it clears naturally instead of sitting there wrong indefinitely.
if resolved:
    resolved_message = f"Container image updated: {'; '.join(resolved)}"
    resolved_payload = json.dumps({"component": COMPONENT, "category": "System", "message": resolved_message})
    try:
        subprocess.run(
            ["mosquitto_pub", "-h", "127.0.0.1", "-p", "1883",
             "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"],
             "-t", LOG_TOPIC, "-m", resolved_payload],
            check=True, timeout=10,
        )
        print(f"Notified: {resolved_message}")
    except Exception as e:
        print(f"Failed to publish resolved notice: {e}")

if not findings:
    print("Nothing pending.")
else:
    message = f"Container image updates: {'; '.join(findings)}"
    payload = json.dumps({"component": COMPONENT, "category": "System", "message": message})
    try:
        subprocess.run(
            ["mosquitto_pub", "-h", "127.0.0.1", "-p", "1883",
             "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"],
             "-t", LOG_TOPIC, "-m", payload],
            check=True, timeout=10,
        )
        print(f"Notified: {message}")
    except Exception as e:
        print(f"Failed to publish: {e}")

    # CARD-0128: queue a kanban PR too, same as the OS-level maintenance
    # checks. Deliberately optional -- a missing/broken PR step must never
    # take down the notification above, which already succeeded.
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
