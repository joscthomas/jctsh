#!/usr/bin/env python3
import os, json, sys
import paho.mqtt.client as mqtt

BROKER    = "100.70.162.24"
PORT      = 1883
COMPONENT = "coachproxyos"
LOG_TOPIC = f"jctsh/rv/{COMPONENT}/log"
HB_TOPIC  = f"jctsh/rv/{COMPONENT}/heartbeat"
USERNAME  = "coachproxyos"

env = {}
with open("/etc/jctsh/heartbeat.env") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v

with open("/proc/uptime") as f:
    secs = int(float(f.read().split()[0]))
uptime = f"{secs // 3600}h {(secs % 3600) // 60}m"

log_payload = json.dumps({"component": COMPONENT, "category": "System", "message": "Heartbeat - online."})
hb_payload  = json.dumps({"component": COMPONENT, "uptime": uptime, "status": "online"})

client = mqtt.Client()
client.username_pw_set(USERNAME, env["MQTT_PASSWORD"])
try:
    client.connect(BROKER, PORT, 10)
    client.publish(LOG_TOPIC, log_payload, qos=1)
    client.publish(HB_TOPIC,  hb_payload,  qos=1)
    client.disconnect()
    print("Heartbeat sent.")
except Exception as e:
    print(f"Failed: {e}", file=sys.stderr)
    sys.exit(1)
