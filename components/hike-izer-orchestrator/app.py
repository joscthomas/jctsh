#!/usr/bin/env python
"""
Hike-izer orchestrator -- webhook receiver for automatic hike-end triggering
(CARD-0086).

Stage 1 (this file, initial build): receives the Tasker HTTP POST fired when
GPSLogger's native stop broadcast fires, validates the shared secret, and
logs what it received. No generation yet -- proves the trigger chain works
end-to-end (GPSLogger -> Tasker -> this receiver) before generation logic is
added in stage 2.

Standard library only -- no pip install required, matching
components/hike-izer/fetch_hike_data.py's convention.

Expected POST body (JSON), matching GPSLogger's own broadcast extras plus
the phone's local date/time as a single ISO 8601 string with UTC offset
(added here because a hike can happen anywhere Joseph is carrying his
phone -- never assume Arizona). Tasker builds this via its "Parse/Format
Date and Time" action (Joda-Time format string `yyyy-MM-dd'T'HH:mm:ssZZ`,
input "Now") rather than string-concatenating separate date/time/offset
variables -- one field, unambiguous:
    {
        "gpsloggerevent": "stopped",              # "started" | "stopped" | "fileuploaded"
        "filename": "...",
        "startedtimestamp": "...",
        "duration": "...",
        "distance": "...",
        "local_datetime": "2026-07-24T14:32:10-07:00"  # phone's local time, ISO 8601 w/ offset
    }

Auth: shared secret via `?key=` query param, same pattern as the existing
Apps Script webhook (core/data-pipeline/environmental-data.gs).
"""

import hmac
import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
PORT = int(os.environ.get("PORT", "8080"))


def log(message):
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{ts}] {message}", flush=True)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default per-request stderr logging; we log explicitly below

    def do_GET(self):
        if urlsplit(self.path).path == "/health":
            self._respond(200, {"status": "ok"})
            return
        self._respond(404, {"status": "error", "message": "not found"})

    def do_POST(self):
        parts = urlsplit(self.path)
        if parts.path != "/webhook/hike-end":
            self._respond(404, {"status": "error", "message": "not found"})
            return

        provided_key = parse_qs(parts.query).get("key", [""])[0]
        if not WEBHOOK_SECRET or not hmac.compare_digest(provided_key, WEBHOOK_SECRET):
            log("Rejected webhook POST: missing or incorrect key")
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            log(f"Rejected webhook POST: invalid JSON body ({raw!r})")
            self._respond(400, {"status": "error", "message": "invalid JSON"})
            return

        event = payload.get("gpsloggerevent", "<missing>")
        log(f"Received gpsloggerevent={event} payload={json.dumps(payload)}")

        if event != "stopped":
            log(f"Ignoring event '{event}' (only 'stopped' triggers generation)")
            self._respond(200, {"status": "ok", "message": f"logged, ignored ({event})"})
            return

        # Stage 2 (not yet built): kick off fetch_hike_data.py / fetch_hike_photos.py
        # and generation here, using payload['local_datetime'] (parseable via
        # datetime.fromisoformat) as "today" for the hike -- never
        # inferred/hardcoded as Arizona.
        log("Stop event received -- generation not yet implemented (stage 2)")
        self._respond(200, {"status": "ok", "message": "stop event logged"})

    def _respond(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    if not WEBHOOK_SECRET:
        log("FATAL: WEBHOOK_SECRET not set -- refusing to start")
        sys.exit(1)
    log(f"Starting hike-izer-orchestrator webhook receiver on :{PORT}")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
