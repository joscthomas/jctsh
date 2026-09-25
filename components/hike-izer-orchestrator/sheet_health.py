#!/usr/bin/env python
"""
CARD-0338: is the environmental Google Sheet responsive right now?

Calls the Apps Script's `action=health` (opens the spreadsheet and reads a
real cell -- unlike `action=version`, which never touches it and so stayed fast
through the 2026-09-25 outage). Used by the *automated* jobs that make heavy
full-range reads -- the daily refresh and the backstop check -- so they skip
(and say why) instead of piling more long-running executions onto a struggling
document. Deliberately NOT used by a manually-requested `--step2`.

Fails open in exactly one case: a script that predates `action=health`
answers "unknown action", which says nothing about the Sheet, so that is
treated as healthy rather than blocking every refresh until it is redeployed.
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
        req = urllib.request.Request(url + "?" + urllib.parse.urlencode({"key": key, "action": "health"}))
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
