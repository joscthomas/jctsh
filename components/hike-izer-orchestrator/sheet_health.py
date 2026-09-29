#!/usr/bin/env python
"""
CARD-0338: is the environmental data store responsive right now?

CARD-0349 Phase 1 (Step 7): both callers now point this at
`data-pipeline-api`'s own `/health` route (a real `SELECT 1`) instead of
`environmental-data.gs`'s `action=health` -- Environmental Data/GPS Track,
the tables whose slow full-range reads originally motivated this check
(CARD-0338, the 2026-09-25 outage), now live in TimescaleDB, not the
Sheet. `check()` itself is unchanged: `url` is just the full health-check
endpoint (append `?key=&action=health` regardless of target -- the new
gateway ignores the unused `action` param, same call shape either way).
Used by the *automated* jobs that make heavy full-range reads -- the daily
refresh and the backstop check -- so they skip (and say why) instead of
piling more long-running executions onto a struggling store. Deliberately
NOT used by a manually-requested `--step2`.

Fails open in exactly one case: a target that predates `action=health`
answers "unknown action", which says nothing about the store's real
health, so that is treated as healthy rather than blocking every refresh.
`data-pipeline-api`'s own `/health` never returns that message, so this
branch is dead code against the new target -- harmless, left in place
rather than special-cased away (it was only ever right for the retired
Apps Script target -- every table now comes from the gateway).
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

SLOW_SECONDS = 10
CALL_TIMEOUT_SECONDS = 30


def check(url, key):
    """Returns (ok, detail). Never raises, and detail never contains the URL
    or key (an exception's own text can, so only the exception's type is used)."""
    start = time.time()
    try:
        # CARD-0349: Cloudflare's Bot Fight Mode (fronting hikes.jctnet.com,
        # the new gateway target) silently 403s urllib's default
        # 'Python-urllib/3.x' User-Agent before the request even reaches
        # data-pipeline-api -- found live via fetch_hike_data.py's own Step
        # 6 cutover, same fix applied here before this was ever deployed.
        req = urllib.request.Request(
            url + "?" + urllib.parse.urlencode({"key": key, "action": "health"}),
            headers={"User-Agent": "jctsh-hike-izer/1.0"},
        )
        with urllib.request.urlopen(req, timeout=CALL_TIMEOUT_SECONDS) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return False, f"health call failed after {time.time() - start:.0f}s ({type(e).__name__})"

    elapsed = time.time() - start
    if body.get("status") != "ok":
        if body.get("message") == "unknown action":
            return True, "script predates action=health -- Sheet not checked"
        return False, f"health call returned status={body.get('status')!r}"
    if elapsed > SLOW_SECONDS:
        return False, f"health call slow ({elapsed:.0f}s)"
    return True, f"ok in {elapsed:.1f}s"
