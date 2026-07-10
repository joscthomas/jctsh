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

if latest_str == current_str:
    print(f"Up to date: {current_str}")
    raise SystemExit(0)

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
    raise SystemExit(0)

message = f"Immich update available: {latest_str} (currently running {current_str})"
payload = json.dumps({"component": COMPONENT, "category": "System", "message": message})

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
    json.dump({"version": latest_str, "notified_at": now.isoformat()}, f)

print(f"Notified: {message}")
