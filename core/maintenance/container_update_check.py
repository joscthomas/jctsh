"""CARD-0126: container-image update visibility via each service's GitHub
Releases API.

Generic across any Docker container whose image is a real open-source
project with GitHub releases -- NetAlertX, Caddy, cloudflared, and Home
Assistant all qualify. Confirmed live 2026-07-31: each of those four
containers carries an org.opencontainers.image.source label pointing at
its real repo, and current version is determinable either from the
matching .image.version label, or (cloudflared, which sets source but
not version) by exec-ing the binary's own --version flag.

Notify-only, same policy as every other maintenance check in this repo
(CARD-0095, CARD-0125, immich-update-check.py) -- never pulls or
updates anything itself. Imported by a thin per-host wrapper script
that defines its own SERVICES list; not run standalone.
"""
import json
import re
import subprocess
import urllib.request
from datetime import datetime, timezone, timedelta

REMIND_EVERY = timedelta(days=7)


def _current_version(service):
    if service["version_method"] == "label":
        result = subprocess.run(
            ["docker", "inspect", service["container"], "--format",
             '{{index .Config.Labels "org.opencontainers.image.version"}}'],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() or None
    if service["version_method"] == "exec":
        result = subprocess.run(
            ["docker", "exec", service["container"], *service["exec_cmd"]],
            capture_output=True, text=True, timeout=10,
        )
        m = re.search(service["version_regex"], result.stdout)
        return m.group(1) if m else None
    return None


def _latest_release(source_repo):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{source_repo}/releases/latest",
        headers={"Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return data.get("tag_name")


def _normalize(v):
    """Strip a leading 'v' so 'v2.11.4' and '2.11.4' compare equal --
    different projects format release tags differently (Caddy: v-prefixed;
    NetAlertX, Home Assistant, cloudflared: bare)."""
    return v.lstrip("v") if v else v


def check_services(services, state):
    """Returns (findings, new_state, pending_updates, resolved). findings is
    a list of human-readable strings, one per service with a genuinely new,
    not-yet-throttled update available. new_state is the caller's state dict
    to persist, keyed per service name with {"version", "notified_at"} for
    the same 7-day reminder throttle every other check in this repo uses.

    pending_updates (CARD-0132) is {service_name: {"pending", "current",
    "latest"}}, populated for every service whose current/latest version was
    actually determined this run -- unconditionally, independent of the
    notification throttle above. Mirrors immich-update-check.py's CARD-0127
    pattern: callers publish this as retained MQTT state every run so a
    dashboard's Pending Update column reflects current true state rather
    than "last thing logged," instead of only firing when a new, unthrottled
    finding happens to exist.

    resolved is a list of human-readable strings, one per service whose
    *running* version actually changed since the last check (persisted under
    new_state["_last_current"]) -- fires once, right after a real update was
    applied, regardless of whether the new version still shows pending. Exists
    so callers can post a one-time "now running X" log message: without it, a
    component's last-logged message stays frozen on its old "update available"
    notice indefinitely once the update is actually applied, since nothing
    else would otherwise tell the log-history-based dashboard column that
    the finding is stale. Not throttled -- a real version change is rare and
    always worth a fresh log line, unlike the routine "still pending" case
    findings/the 7-day throttle already cover."""
    findings = []
    new_state = dict(state)
    pending_updates = {}
    resolved = []
    last_current = dict(state.get("_last_current", {}))
    now = datetime.now(timezone.utc)
    for svc in services:
        name = svc["name"]
        try:
            current = _current_version(svc)
            latest = _latest_release(svc["source"])
        except Exception as e:
            findings.append(f"{name}: check failed ({e})")
            continue
        if not current or not latest:
            continue
        pending = _normalize(current) != _normalize(latest)
        pending_updates[name] = {"pending": pending, "current": current, "latest": latest}

        prior_current = last_current.get(name)
        if prior_current is not None and prior_current != current:
            resolved.append(f"{name}: now running {current}")
        last_current[name] = current

        if not pending:
            new_state.pop(name, None)
            continue
        prior = state.get(name, {})
        same_version = prior.get("version") == latest
        if same_version:
            last = datetime.fromisoformat(prior["notified_at"])
            due = now - last >= REMIND_EVERY
        else:
            due = True
        if same_version and not due:
            continue
        findings.append(f"{name}: {latest} available (running {current})")
        new_state[name] = {"version": latest, "notified_at": now.isoformat()}
    new_state["_last_current"] = last_current
    return findings, new_state, pending_updates, resolved
