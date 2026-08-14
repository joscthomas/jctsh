#!/usr/bin/env python3
"""JCTsh Pi post-reboot health check (CARD-0158).

Runs once at boot (systemd oneshot, reboot-health-check.service) and
publishes a retained MQTT fact -- jctsh/core/jctsh-core/reboot-health --
confirming whether the Pi's own core services actually came back healthy
after a reboot, not just "the service unit exists." Mirrors CARD-0127's
retained-state pattern exactly (immich-update-check.py is the reference
implementation): this is *current true state*, republished every run
regardless of the outcome, so it can never silently fall out of view the
way a plain log message would the moment anything else logs for this same
component.

Raised by CARD-0129: a real scheduled reboot (2026-08-10) went unnoticed
for three days -- it happened to succeed, but nothing would have surfaced
it if it hadn't. The existing watchdog/heartbeat system already covers
MQTT/Node-RED/log-server going silent; this covers the one thing that
doesn't heartbeat -- Docker/container health -- specifically at the moment
it matters most, right after a reboot.

Uses mosquitto_pub (not paho-mqtt) and /etc/jctsh/log-server.env, matching
this Pi's own established script pattern (pi-maintenance-check.py), not
the M8 scripts' paho-mqtt convention.
"""
import json
import os
import subprocess
import time
from datetime import datetime, timezone

BROKER    = "127.0.0.1"
PORT      = 1883
COMPONENT = "jctsh-core"  # same dashboard row as the existing watchdog heartbeat
HEALTH_TOPIC = f"jctsh/core/{COMPONENT}/reboot-health"
LOG_TOPIC    = "jctsh/core/log-server/log"

# Docker itself and the containers it manages take real time to come up
# after a cold boot -- a single immediate check would routinely (and
# wrongly) report "unhealthy" while HA is still mid-startup. Polls up to
# this long before recording whatever the final observed state is.
HEALTH_POLL_TIMEOUT_S = 180
HEALTH_POLL_INTERVAL_S = 5

env = {}
with open("/etc/jctsh/log-server.env") as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v


def _boot_time_iso():
    """Actual boot time (local), not 'now' -- this script can run a little
    after boot itself, and the fact being reported is about the reboot, not
    about whenever this check happened to execute."""
    out = subprocess.run(["uptime", "-s"], capture_output=True, text=True, timeout=10).stdout.strip()
    return out  # e.g. "2026-08-17 03:00:19" -- already local (Pi's own tz)


def _docker_health(container):
    """Poll up to HEALTH_POLL_TIMEOUT_S for the container's own Docker
    healthcheck to resolve. Returns the final observed status string
    ('healthy', 'unhealthy', 'starting', or 'absent' if the container
    doesn't exist / has no healthcheck at all)."""
    deadline = time.monotonic() + HEALTH_POLL_TIMEOUT_S
    status = "absent"
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["docker", "inspect", "--format={{.State.Health.Status}}", container],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            status = "absent"
        else:
            status = result.stdout.strip() or "absent"
            if status == "healthy":
                return status
        time.sleep(HEALTH_POLL_INTERVAL_S)
    return status


def _service_active(name):
    result = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=10)
    return result.stdout.strip() == "active"


ha_status = _docker_health("homeassistant")
nodered_active = _service_active("nodered")
mosquitto_active = _service_active("mosquitto")

checks = {
    "homeassistant": ha_status,
    "nodered": "active" if nodered_active else "inactive",
    "mosquitto": "active" if mosquitto_active else "inactive",
}
healthy = ha_status == "healthy" and nodered_active and mosquitto_active

payload = json.dumps({
    "component": COMPONENT,
    "last_reboot": _boot_time_iso(),
    "healthy": healthy,
    "checks": checks,
})

subprocess.run(
    ["mosquitto_pub", "-h", BROKER, "-p", str(PORT),
     "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"],
     "-t", HEALTH_TOPIC, "-m", payload, "-r", "-q", "1"],
    check=True, timeout=10,
)

if healthy:
    print(f"Reboot health OK: {checks}")
else:
    # Same "Alert" category + log-topic path pi-maintenance-check.py and
    # immich-update-check.py already use to get a human's attention --
    # not a new, unverified notification mechanism.
    message = f"Reboot health check FAILED: {checks}"
    alert_payload = json.dumps({"component": COMPONENT, "category": "Alert", "message": message})
    subprocess.run(
        ["mosquitto_pub", "-h", BROKER, "-p", str(PORT),
         "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"],
         "-t", LOG_TOPIC, "-m", alert_payload],
        check=True, timeout=10,
    )
    print(message)
