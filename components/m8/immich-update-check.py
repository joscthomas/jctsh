#!/usr/bin/env python3
import json, os, sys, urllib.request
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from open_kanban_pr import open_finding_pr  # CARD-0128
import paho.mqtt.client as mqtt

BROKER    = "192.168.1.117"
PORT      = 1883
COMPONENT = "photo-server"
LOG_TOPIC = f"jctsh/server/{COMPONENT}/log"
USERNAME  = "photo-server"

IMMICH_BASE   = "http://localhost:2283"
ADMIN_API_KEY = "VibjMm5LXk2LU4xpsJ04F2ggbZsjX3uEim1CjXf0A"
STATE_FILE    = "/home/jct/.jctsh/immich-update-check.state"
GITHUB_ENV    = "/etc/jctsh/github.env"  # CARD-0128, same credential every other maintenance check uses
REMIND_EVERY  = timedelta(days=7)

env = {}
with open("/etc/jctsh/heartbeat.env") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v


def api_get(path):
    req = urllib.request.Request(
        IMMICH_BASE + path, headers={"x-api-key": ADMIN_API_KEY}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


try:
    with open(STATE_FILE) as f:
        disk_state = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    disk_state = {}

current = api_get("/api/server/version")
current_str = f"v{current['major']}.{current['minor']}.{current['patch']}"

check = api_get("/api/server/version-check")
latest_str = check["releaseVersion"]
pending = latest_str != current_str

# A resolved update leaves a stale "X available" notice as this component's
# Last Reading otherwise -- nothing else would tell the log dashboard the
# finding is out of date, since Last Reading shows whichever message was
# logged last, not current state. Detected by comparing against the running
# version last seen on disk (persisted every run, unlike the throttle state
# below which is only written when actually notifying) -- fires once, right
# after a real upgrade, not on every routine "still running vX" check.
resolved_message = None
prior_current = disk_state.get("last_known_current")
if prior_current is not None and prior_current != current_str:
    resolved_message = f"Immich upgraded to {current_str}"

# CARD-0127: retained-state publish, independent of the throttled notification
# logic below. Always sent, every run, regardless of whether this run ends up
# notifying on the log dashboard -- this is what makes /status's Pending
# Update column a reliable "current true state" rather than "whatever the
# last message happened to be." Explicit pending:false when up to date,
# not just skipping the publish -- an absent retained topic is ambiguous
# with "never checked," an explicit false isn't.
pending_payload = json.dumps({
    "pending": pending, "current": current_str, "latest": latest_str,
})
# CARD-0127: namespaced by item ("immich"), not just by host component --
# MQTT retains one value per topic, so a bare .../pending-update topic would
# silently collide with any other pending-update state ever published for
# this same component (e.g. CARD-0095's OS-level maintenance check, if that
# gets extended to publish retained state too). Each distinct "thing that
# can be pending" gets its own topic; the dashboard aggregates per component.
PENDING_TOPIC = f"jctsh/server/{COMPONENT}/pending-update/immich"

send_notification = False
notify_message = None

if pending:
    state = disk_state

    now = datetime.now(timezone.utc)
    same_version = state.get("version") == latest_str
    if same_version:
        last_notified = datetime.fromisoformat(state["notified_at"])
        due_for_reminder = now - last_notified >= REMIND_EVERY
    else:
        due_for_reminder = True

    if same_version and not due_for_reminder:
        days_left = REMIND_EVERY - (now - last_notified)
        print(f"Already notified about {latest_str} (running {current_str}) "
              f"— next reminder in {days_left.days}d — not re-notifying")
    else:
        send_notification = True
        notify_message = f"Immich update available: {latest_str} (currently running {current_str})"
else:
    print(f"Up to date: {current_str}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, env["MQTT_PASSWORD"])
client.connect(BROKER, PORT, 10)
client.loop_start()
info_pending = client.publish(PENDING_TOPIC, pending_payload, qos=1, retain=True)
info_pending.wait_for_publish(timeout=5)
if resolved_message:
    resolved_payload = json.dumps({"component": COMPONENT, "category": "System", "message": resolved_message})
    info_resolved = client.publish(LOG_TOPIC, resolved_payload, qos=1)
    info_resolved.wait_for_publish(timeout=5)
    print(f"Notified: {resolved_message}")
if send_notification:
    notify_payload = json.dumps({"component": COMPONENT, "category": "System", "message": notify_message})
    info_log = client.publish(LOG_TOPIC, notify_payload, qos=1)
    info_log.wait_for_publish(timeout=5)
client.loop_stop()
client.disconnect()

# Base state carried forward every run now (previously only written when
# send_notification, which left last_known_current permanently stale/absent
# on every up-to-date or throttled run). Pending-throttle fields
# (version/notified_at/pr_*) only make sense while an update is genuinely
# pending, so they're dropped once resolved rather than carried forward.
new_state = dict(disk_state) if pending else {}
new_state["last_known_current"] = current_str

if send_notification:
    new_state["version"] = latest_str
    new_state["notified_at"] = now.isoformat()

    # CARD-0128: queue a kanban PR too, same as every other maintenance
    # check -- this was the one script that predated CARD-0128 and never
    # got wired in (found 2026-07-31 while explaining why an Immich update
    # wasn't showing up in the PR queue the way HA's did). Deliberately
    # optional, same pattern as the others: a missing/broken PR step must
    # never take down the notification above, which already succeeded.
    try:
        gh_env = {}
        with open(GITHUB_ENV) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    gh_env[k] = v
        prior_pr_state = {k: state[k] for k in ("pr_fingerprint", "pr_number") if k in state}
        pr_state, pr_url = open_finding_pr(
            COMPONENT, notify_message, latest_str, gh_env["GITHUB_PAT"], prior_pr_state,
        )
        new_state.update(pr_state)
        if pr_url:
            print(f"Opened kanban PR: {pr_url}")
    except FileNotFoundError:
        pass  # GITHUB_ENV not set up yet
    except Exception as e:
        print(f"CARD-0128 PR step failed (notification above still succeeded): {e}")

    print(f"Notified: {notify_message}")
else:
    print(f"Pending-update state published: pending={pending}")

os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
with open(STATE_FILE, "w") as f:
    json.dump(new_state, f)
