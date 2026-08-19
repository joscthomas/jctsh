#!/usr/bin/env python3
"""CARD-0126: M8-side container-image update check -- NetAlertX, Caddy
(hike-izer-web), cloudflared. Shared logic in
core/maintenance/container_update_check.py (deployed alongside this
script, same directory, on the actual host)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from container_update_check import check_services
from open_kanban_pr import open_finding_pr  # CARD-0128
import paho.mqtt.client as mqtt

BROKER    = "192.168.1.117"
PORT      = 1883
COMPONENT = "photo-server"
LOG_TOPIC = f"jctsh/server/{COMPONENT}/log"
USERNAME  = "photo-server"

STATE_FILE = "/home/jct/.jctsh/container-update-check.state"
GITHUB_ENV = "/etc/jctsh/github.env"  # CARD-0128, same credential every other maintenance check uses

SERVICES = [
    {"name": "netalertx", "container": "netalertx",
     "source": "netalertx/NetAlertX", "version_method": "label"},
    {"name": "caddy", "container": "hike-izer-web",
     # Not caddyserver/caddy-docker -- confirmed live 2026-07-31 that repo
     # has no GitHub releases at all (404), it's just the Dockerfile
     # packaging repo. The OCI source label on the running container points
     # there, but the real releases (and the tag that actually matches the
     # image's own .image.version label) live at the core software repo.
     "source": "caddyserver/caddy", "version_method": "label"},
    {"name": "cloudflared", "container": "hike-izer-cloudflared",
     "source": "cloudflare/cloudflared", "version_method": "exec",
     "exec_cmd": ["cloudflared", "--version"], "version_regex": r"version (\S+)"},
]

env = {}
with open("/etc/jctsh/heartbeat.env") as f:
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

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, env["MQTT_PASSWORD"])
client.connect(BROKER, PORT, 10)
client.loop_start()

# CARD-0132: retained pending-update state per service, same pattern CARD-0127
# used for Immich -- published every run regardless of whether `findings` is
# empty, so /status's Pending Update column reflects current true state
# instead of "last thing logged."
for name, info in pending_updates.items():
    pending_topic = f"jctsh/server/{COMPONENT}/pending-update/{name}"
    pending_payload = json.dumps({
        "pending": info["pending"], "current": info["current"], "latest": info["latest"],
    })
    pub = client.publish(pending_topic, pending_payload, qos=1, retain=True)
    pub.wait_for_publish(timeout=5)

# A resolved update leaves a stale "X available" notice as this component's
# Last Reading otherwise -- nothing else would tell the log dashboard the
# finding is out of date, since Last Reading shows whichever message was
# logged last, not current state. Post a one-time "now running" notice so
# it clears naturally instead of sitting there wrong indefinitely.
if resolved:
    resolved_message = f"Container image updated: {'; '.join(resolved)}"
    resolved_payload = json.dumps({"component": COMPONENT, "category": "System", "message": resolved_message})
    pub = client.publish(LOG_TOPIC, resolved_payload, qos=1)
    pub.wait_for_publish(timeout=5)
    print(f"Notified: {resolved_message}")

if not findings:
    print("Nothing pending.")
else:
    message = f"Container image updates: {'; '.join(findings)}"
    payload = json.dumps({"component": COMPONENT, "category": "System", "message": message})
    info = client.publish(LOG_TOPIC, payload, qos=1)
    info.wait_for_publish(timeout=5)
    print(f"Notified: {message}")

    # CARD-0128: queue a kanban PR too, same as the OS-level maintenance
    # checks -- an available image update is exactly the kind of finding
    # that belongs in the work queue, not just the log. Deliberately
    # optional, same as the other scripts: a missing/broken PR step must
    # never take down the notification above, which already succeeded.
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

client.loop_stop()
client.disconnect()

os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
with open(STATE_FILE, "w") as f:
    json.dump(new_state, f)
