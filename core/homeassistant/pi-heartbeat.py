#!/usr/bin/env python3
import json, os, subprocess, sys

BROKER    = "127.0.0.1"
PORT      = 1883
COMPONENT = "jctsh-core"
LOG_TOPIC = "jctsh/core/log-server/log"

# Docker containers on the Pi that have a HEALTHCHECK configured. Extend this
# list if more containers on the Pi get one later.
CONTAINERS = ["homeassistant"]

env = {}
with open("/etc/jctsh/log-server.env") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v

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
            unhealthy.append(f"{name}:{status or 'no healthcheck configured'}")
    except Exception as e:
        unhealthy.append(f"{name}:error({e})")

if unhealthy:
    category = "Alert"
    message = f"Docker degraded - {', '.join(unhealthy)}"
else:
    category = "System"
    message = "Heartbeat - Docker containers healthy."

payload = json.dumps({"component": COMPONENT, "category": category, "message": message})

try:
    subprocess.run(
        ["mosquitto_pub", "-h", BROKER, "-p", str(PORT),
         "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"],
         "-t", LOG_TOPIC, "-m", payload],
        check=True, timeout=10,
    )
    print(f"Heartbeat sent. category={category}")
except Exception as e:
    print(f"Failed: {e}", file=sys.stderr)
    sys.exit(1)
