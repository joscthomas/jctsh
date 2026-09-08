#!/usr/bin/env python3
import json, os, subprocess, sys

BROKER    = "127.0.0.1"
PORT      = 1883
COMPONENT = "jctsh-core"
LOG_TOPIC = "jctsh/core/log-server/log"

# Docker containers on the Pi that have a HEALTHCHECK configured. Extend this
# list if more containers on the Pi get one later.
CONTAINERS = ["homeassistant"]

# CARD-0249: a container reporting "starting" within this many seconds of boot is a
# scheduled-reboot.timer artifact, not a real problem -- see the card for the incident
# that prompted this (a normal weekly reboot logged as a plain Alert with no way to
# tell it apart from a real crash-loop without SSHing in and checking uptime by hand).
POST_REBOOT_GRACE_SECS = 600

with open("/proc/uptime") as f:
    uptime_secs = float(f.read().split()[0])

env = {}
with open("/etc/jctsh/log-server.env") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v

unhealthy = []
starting_post_reboot = []
for name in CONTAINERS:
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", name],
            capture_output=True, text=True, timeout=10,
        )
        status = result.stdout.strip()
        if result.returncode != 0:
            unhealthy.append(f"{name}:not found")
        elif status == "starting" and uptime_secs < POST_REBOOT_GRACE_SECS:
            starting_post_reboot.append(f"{name}:{status}")
        elif status != "healthy":
            unhealthy.append(f"{name}:{status or 'no healthcheck configured'}")
    except Exception as e:
        unhealthy.append(f"{name}:error({e})")

if unhealthy:
    category = "Alert"
    message = f"Docker degraded - {', '.join(unhealthy)}"
    if starting_post_reboot:
        message += f" (also starting after scheduled reboot: {', '.join(starting_post_reboot)})"
elif starting_post_reboot:
    category = "System"
    message = f"Docker containers starting after scheduled reboot - {', '.join(starting_post_reboot)}"
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
