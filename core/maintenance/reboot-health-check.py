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

CARD-0247 extension: a Docker healthcheck passing for the `homeassistant`
container doesn't mean every integration actually resynced after the
restart -- CARD-0240 found a config entry can report `state: loaded` while
its entities are still stuck `unavailable`. Once the container itself is
healthy, this also hits the HA REST API: counts unavailable entities, and
parses the container's own "Waiting for integrations to complete setup"
boot log line (the same detection technique CARD-0240 used by hand) for
which domains HA itself flagged as slow to start this boot.

Real format check against the Pi's own logs (not assumed): the line is a
dict-of-tuples, e.g. `{('samsungtv', '01KZ...'): 233.7, ('mqtt', '01KS...'):
442198.3, ...}` -- and on a normal boot it routinely names several
perfectly healthy integrations (met, google_translate, cast, mqtt,
denonavr, dlna_dmr) that just took a little longer to finish setup, not
integrations with this bug. So the raw list is NOT used as "anything named
here is suspect" -- only AUTO_RELOAD_DOMAINS and WATCH_ONLY_DOMAINS below
(integrations independently known, via CARD-0240, to carry external/cloud
pairing state that a plain reload doesn't always resync) are checked
against it. AUTO_RELOAD_DOMAINS get reloaded automatically; WATCH_ONLY
domains (e.g. samsungtv, whose fix is a physical accept-on-the-TV action no
unattended job can complete) are only ever flagged via an Alert.
"""
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

BROKER    = "127.0.0.1"
PORT      = 1883
COMPONENT = "jctsh-core"  # same dashboard row as the existing watchdog heartbeat
HEALTH_TOPIC = f"jctsh/core/{COMPONENT}/reboot-health"
LOG_TOPIC    = "jctsh/core/log-server/log"

# Integrations confirmed (CARD-0240) safe to blind-reload unattended --
# a stale-but-loaded config entry, no physical/human step involved.
AUTO_RELOAD_DOMAINS = ("smartthings", "ring")

# Integrations known to carry the same "loaded but not actually resynced"
# risk but NOT safe to blind-reload (e.g. samsungtv's fix is a physical
# accept-on-the-TV action) -- flagged via Alert only. Deliberately a short,
# curated list, not "anything HA names as slow to start" -- most domains
# that transiently appear there on a normal boot (met, google_translate,
# cast, mqtt, etc.) are not this class of bug at all.
WATCH_ONLY_DOMAINS = ("samsungtv",)

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


def _ha_request(path, method="GET"):
    req = urllib.request.Request(
        f"{env['HA_URL']}{path}",
        headers={"Authorization": f"Bearer {env['HA_TOKEN']}"},
        method=method,
        data=b"{}" if method == "POST" else None,
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read()
        return json.loads(body) if body else None


def _unavailable_count():
    states = _ha_request("/api/states")
    return sum(1 for s in states if s.get("state") == "unavailable")


def _slow_loading_domains():
    """Parse `homeassistant`'s own boot log for every "Waiting for
    integrations to complete setup" line in the last 10 minutes -- the same
    technique CARD-0240 used by hand to find samsungtv on the same
    slow-loading list as smartthings/ring. The line is a dict-of-tuples
    (`{('samsungtv', '01KZ...'): 233.7, ...}`), confirmed against the Pi's
    own real logs -- union the domain (first tuple element) across every
    matching line in the window, since a given domain can drop off the list
    between successive log lines as it finishes. Returns the raw set;
    callers intersect against AUTO_RELOAD_DOMAINS/WATCH_ONLY_DOMAINS rather
    than treating membership here alone as suspect (see module docstring)."""
    result = subprocess.run(
        ["docker", "logs", "--since", "10m", "homeassistant"],
        capture_output=True, text=True, timeout=15,
    )
    domains = set()
    for line in (result.stdout + result.stderr).splitlines():
        if "Waiting for integrations to complete setup" in line:
            domains.update(re.findall(r"\('([a-zA-Z0-9_]+)',", line))
    return domains


def _reload_domain(domain):
    entries = _ha_request("/api/config/config_entries/entry")
    reloaded = []
    for e in entries:
        if e.get("domain") == domain:
            _ha_request(f"/api/config/config_entries/entry/{e['entry_id']}/reload", method="POST")
            reloaded.append(e.get("title", domain))
    return reloaded


ha_status = _docker_health("homeassistant")
nodered_active = _service_active("nodered")
mosquitto_active = _service_active("mosquitto")

checks = {
    "homeassistant": ha_status,
    "nodered": "active" if nodered_active else "inactive",
    "mosquitto": "active" if mosquitto_active else "inactive",
}
healthy = ha_status == "healthy" and nodered_active and mosquitto_active

entity_check = None
watch_domains = []
if ha_status == "healthy" and env.get("HA_TOKEN") and env.get("HA_URL"):
    try:
        before = _unavailable_count()
        slow_domains = _slow_loading_domains()
        auto_reloaded = {}
        for domain in AUTO_RELOAD_DOMAINS:
            if domain in slow_domains:
                auto_reloaded[domain] = _reload_domain(domain)
        if auto_reloaded:
            time.sleep(15)  # let the reload actually resync before recounting
        after = _unavailable_count() if auto_reloaded else before
        watch_domains = [d for d in WATCH_ONLY_DOMAINS if d in slow_domains]
        entity_check = {
            "unavailable_before": before,
            "unavailable_after": after,
            "auto_reloaded": auto_reloaded,
            "watch_domains": watch_domains,
        }
    except (urllib.error.URLError, KeyError, ValueError) as exc:
        entity_check = {"error": str(exc)}

payload = json.dumps({
    "component": COMPONENT,
    "last_reboot": _boot_time_iso(),
    "healthy": healthy,
    "checks": checks,
    "entity_check": entity_check,
})

subprocess.run(
    ["mosquitto_pub", "-h", BROKER, "-p", str(PORT),
     "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"],
     "-t", HEALTH_TOPIC, "-m", payload, "-r", "-q", "1"],
    check=True, timeout=10,
)

def _alert(message):
    # Same "Alert" category + log-topic path pi-maintenance-check.py and
    # immich-update-check.py already use to get a human's attention --
    # not a new, unverified notification mechanism.
    alert_payload = json.dumps({"component": COMPONENT, "category": "Alert", "message": message})
    subprocess.run(
        ["mosquitto_pub", "-h", BROKER, "-p", str(PORT),
         "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"],
         "-t", LOG_TOPIC, "-m", alert_payload],
        check=True, timeout=10,
    )
    print(message)


if healthy:
    print(f"Reboot health OK: {checks}")
else:
    _alert(f"Reboot health check FAILED: {checks}")

if watch_domains:
    # A domain HA itself flagged as slow to start this boot, but not one
    # we auto-reload (e.g. samsungtv -- its fix is a physical accept-on-
    # the-TV action no unattended job can complete) -- flag it, don't
    # silently reload or silently ignore it.
    _alert(
        f"Reboot health check: {', '.join(watch_domains)} slow to start "
        f"and not auto-reloaded -- may need a manual check "
        f"({entity_check['unavailable_before']} unavailable entities at boot)."
    )
elif entity_check and entity_check.get("error"):
    _alert(f"Reboot health check: entity-availability check failed ({entity_check['error']}).")
