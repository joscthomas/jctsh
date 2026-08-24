#!/usr/bin/env python3
"""JCTsh kanban-PR intake pipeline watchdog self-test (CARD-0192).

Runs daily. Calls open_finding_pr() with a recognizable, obviously-synthetic
finding, confirms a real PR actually opened, closes the *previous* run's test
PR (found in this script's own persisted state), and persists the new one for
next time. If open_finding_pr() (or the confirmation re-fetch) fails, the
pipeline that CARD-0190's real incident depends on is broken -- publish an
Alert that explicitly names the risk window (any real idea/finding logged
since the last confirmed-good run may have been silently lost), not just
"self-test failed."

Deliberately does NOT reuse open_finding_pr()'s own fingerprint-based dedup
across runs (that's built for "same finding seen again," not "prove the
pipeline works right now") -- the fingerprint here is date-suffixed so every
day's run always attempts a genuinely fresh open, and this script's own state
file (not open_finding_pr()'s state parameter) is what remembers the PR
number to close next time.

State file: STATE_PATH below (create the containing directory before first
deploy: sudo mkdir -p /var/lib/jctsh && sudo chown jct:jct /var/lib/jctsh,
or root:pi on the Pi -- matches this repo's other mutable-state files, not
/etc which is config-only).
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from open_kanban_pr import open_finding_pr, close_pr, _pr_still_open  # CARD-0128/CARD-0192

BROKER    = "127.0.0.1"
PORT      = 1883
COMPONENT = "jctsh-pr-selftest"
LOG_TOPIC = "jctsh/core/log-server/log"

GITHUB_ENV = "/etc/jctsh/github.env"   # GITHUB_PAT=...
LOG_ENV    = "/etc/jctsh/log-server.env"  # MQTT_USER=..., MQTT_PASS=...
STATE_PATH = "/var/lib/jctsh/kanban-pr-selftest-state.json"

TEST_MESSAGE = (
    "Automated daily self-test of the kanban-PR intake pipeline (CARD-0192). "
    "Confirms open_finding_pr() can still open a real PR. Safe to ignore -- "
    "this closes itself automatically on tomorrow's run."
)


def _load_env(path):
    env = {}
    with open(path) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env


def _load_state():
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH) as f:
        return json.load(f)


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f)


def _publish_log(category, message):
    log_env = _load_env(LOG_ENV)
    payload = json.dumps({"component": COMPONENT, "category": category, "message": message})
    subprocess.run(
        ["mosquitto_pub", "-h", BROKER, "-p", str(PORT),
         "-u", log_env["MQTT_USER"], "-P", log_env["MQTT_PASS"],
         "-t", LOG_TOPIC, "-m", payload],
        check=True, timeout=10,
    )


state = _load_state()
gh_env = _load_env(GITHUB_ENV)
token = gh_env["GITHUB_PAT"]
now = datetime.now(timezone.utc)

# Close the previous run's test PR before opening today's -- keeps the PR
# list clean without manual upkeep (Joseph's interview decision, CARD-0192).
prev_pr_number = state.get("pr_number")
if prev_pr_number:
    try:
        close_pr(prev_pr_number, token)
    except Exception as e:
        print(f"Warning: couldn't close previous test PR #{prev_pr_number}: {e} -- continuing anyway")

try:
    fingerprint = f"kanban-pr-selftest-{now.strftime('%Y-%m-%d')}"
    new_state, pr_url = open_finding_pr(COMPONENT, TEST_MESSAGE, fingerprint, token, {})
    pr_number = new_state["pr_number"]

    # Explicit confirmation re-fetch, matching CARD-0192's own stated design
    # ("confirms a PR actually opened") rather than just trusting that
    # open_finding_pr() didn't raise.
    if not _pr_still_open(pr_number, token):
        raise RuntimeError(f"PR #{pr_number} reported opened but a fresh GET doesn't show it as open")

    _save_state({
        "pr_number": pr_number,
        "pr_fingerprint": fingerprint,
        "last_success_at": now.isoformat(),
    })
    print(f"Self-test OK: {pr_url}")

except Exception as e:
    last_success = state.get("last_success_at", "unknown -- no prior successful run recorded")
    alert = (
        f"Kanban-PR intake pipeline self-test FAILED at {now.isoformat()}: {e}. "
        f"Last confirmed-good run: {last_success}. Any real idea/finding logged "
        f"since then may have been silently lost (see CARD-0190) -- check the "
        f"pipeline (open_kanban_pr.py, GITHUB_PAT validity, GitHub API status) "
        f"and re-check for any real ideas from that window."
    )
    print(alert, file=sys.stderr)
    try:
        _publish_log("Alert", alert)
    except Exception as mqtt_err:
        print(f"Also failed to publish the alert itself: {mqtt_err}", file=sys.stderr)
    raise SystemExit(1)
