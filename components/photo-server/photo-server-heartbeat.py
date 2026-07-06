#!/usr/bin/env python3
import json, subprocess, sys
import paho.mqtt.client as mqtt

BROKER    = "192.168.1.117"
PORT      = 1883
COMPONENT = "photo-server"
LOG_TOPIC = f"jctsh/server/{COMPONENT}/log"
HB_TOPIC  = f"jctsh/server/{COMPONENT}/heartbeat"
USERNAME  = "photo-server"

CONTAINERS = ["immich_server", "immich_postgres", "immich_machine_learning", "immich_redis"]

env = {}
with open("/etc/jctsh/heartbeat.env") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v

with open("/proc/uptime") as f:
    secs = int(float(f.read().split()[0]))
uptime = f"{secs // 3600}h {(secs % 3600) // 60}m"

unhealthy = []
for name in CONTAINERS:
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", name],
            capture_output=True, text=True, timeout=10,
        )
        status = result.stdout.strip()
        if result.returncode != 0:
            unhealthy.append(f"{name}:not found")
        elif status != "healthy":
            unhealthy.append(f"{name}:{status}")
    except Exception as e:
        unhealthy.append(f"{name}:error({e})")

if unhealthy:
    status = "degraded"
    category = "Alert"
    log_message = f"Immich degraded - {', '.join(unhealthy)}"
else:
    status = "online"
    category = "System"
    log_message = "Heartbeat - online."

log_payload = json.dumps({"component": COMPONENT, "category": category, "message": log_message})
hb_payload  = json.dumps({"component": COMPONENT, "uptime": uptime, "status": status})

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, env["MQTT_PASSWORD"])
try:
    client.connect(BROKER, PORT, 10)
    client.loop_start()
    info_log = client.publish(LOG_TOPIC, log_payload, qos=1)
    info_hb  = client.publish(HB_TOPIC,  hb_payload,  qos=1)
    info_log.wait_for_publish(timeout=5)
    info_hb.wait_for_publish(timeout=5)
    client.loop_stop()
    client.disconnect()
    print(f"Heartbeat sent. status={status}")
except Exception as e:
    print(f"Failed: {e}", file=sys.stderr)
    sys.exit(1)
