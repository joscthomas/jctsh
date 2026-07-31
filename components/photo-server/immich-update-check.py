#!/usr/bin/env python3
import json, os, urllib.request
from datetime import datetime, timezone, timedelta
import paho.mqtt.client as mqtt

BROKER    = "192.168.1.117"
PORT      = 1883
COMPONENT = "photo-server"
LOG_TOPIC = f"jctsh/server/{COMPONENT}/log"
USERNAME  = "photo-server"

IMMICH_BASE   = "http://localhost:2283"
ADMIN_API_KEY = "VibjMm5LXk2LU4xpsJ04F2ggbZsjX3uEim1CjXf0A"
STATE_FILE    = "/home/jct/.jctsh/immich-update-check.state"
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


current = api_get("/api/server/version")
current_str = f"v{current['major']}.{current['minor']}.{current['patch']}"

check = api_get("/api/server/version-check")
latest_str = check["releaseVersion"]
pending = latest_str != current_str

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
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

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
if send_notification:
    notify_payload = json.dumps({"component": COMPONENT, "category": "System", "message": notify_message})
    info_log = client.publish(LOG_TOPIC, notify_payload, qos=1)
    info_log.wait_for_publish(timeout=5)
client.loop_stop()
client.disconnect()

if send_notification:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump({"version": latest_str, "notified_at": datetime.now(timezone.utc).isoformat()}, f)
    print(f"Notified: {notify_message}")
else:
    print(f"Pending-update state published: pending={pending}")
