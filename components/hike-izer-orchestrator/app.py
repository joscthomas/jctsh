#!/usr/bin/env python
"""
Hike-izer orchestrator -- webhook receiver for automatic hike-end triggering
(CARD-0086).

Receives the Tasker HTTP POST fired when GPSLogger's native stop broadcast
fires, validates the shared secret, and (stage 2) kicks off the generation
pipeline in a background thread -- the HTTP response returns immediately so
Tasker's own request timeout doesn't fire while fetch/Immich/Claude calls
that can take well over 10 seconds are still running.

Unlike fetch_hike_data.py, this file (and generation.py/narrative.py/
mqtt_log.py) needs pip packages (anthropic, paho-mqtt) -- see Dockerfile.

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
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

import generation
import mqtt_log

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
PORT = int(os.environ.get("PORT", "8080"))


def log(message):
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{ts}] {message}", flush=True)


def _log_mqtt_async(category, message):
    # Fire-and-forget, off the request-handling thread -- an MQTT publish
    # takes up to 5s (mqtt_log.py's own wait_for_publish timeout) and must
    # never add latency to a webhook response or delay server startup.
    # Also the durable half of every log() call site below: a container's
    # own stdout/stderr dies with it on any rebuild (confirmed live
    # 2026-07-28 -- a real webhook's receipt was provably lost this way,
    # untraceable after the container that received it got replaced),
    # while this MQTT line lands on the dashboard independent of container
    # lifecycle.
    def _send():
        try:
            mqtt_log.publish_log(category, message)
        except Exception as e:
            log(f"mqtt_log publish failed: {e}")

    threading.Thread(target=_send, daemon=True).start()


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
        if parts.path == "/webhook/hike-end":
            self._handle_hike_end(parts)
            return
        if parts.path == "/webhook/stage-file":
            self._handle_stage_file(parts)
            return
        self._respond(404, {"status": "error", "message": "not found"})

    def _authorized(self, parts):
        provided_key = parse_qs(parts.query).get("key", [""])[0]
        return bool(WEBHOOK_SECRET) and hmac.compare_digest(provided_key, WEBHOOK_SECRET)

    def _handle_hike_end(self, parts):
        if not self._authorized(parts):
            log("Rejected webhook POST: missing or incorrect key")
            # Alert, not System -- a rejected auth attempt reaching us at
            # all is the one signal a totally-silent failure (nothing ever
            # arriving) can't produce, so it's worth flagging distinctly.
            _log_mqtt_async("Alert", "Webhook POST rejected: missing or incorrect key.")
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
        # The durable half of the line above -- generation.py already
        # publishes its own completion/failure line once a 'stopped' run
        # finishes, but there was previously no durable record that the
        # webhook itself was ever received in the first place.
        _log_mqtt_async("System", f"Webhook received: gpsloggerevent={event}.")

        if event != "stopped":
            log(f"Ignoring event '{event}' (only 'stopped' triggers generation)")
            self._respond(200, {"status": "ok", "message": f"logged, ignored ({event})"})
            return

        log("Stop event received -- starting generation in the background")
        threading.Thread(target=generation.run_and_log, args=(payload,), daemon=True).start()
        self._respond(200, {"status": "ok", "message": "stop event received, generating"})

    def _handle_stage_file(self, parts):
        """CARD-0122: receives a file shared directly from the phone (via
        AutoShare + Tasker) for the currently-in-progress staging workflow --
        a Gaia GPS embed snippet or a BirdNET Live export -- and writes it
        into the most-recently-published hike's own _staging directory (see
        generation.latest_file_stem for why mtime, not "today"). Unlike
        hike-end, this responds synchronously -- writing a file is fast,
        no background thread needed."""
        if not self._authorized(parts):
            log("Rejected stage-file POST: missing or incorrect key")
            _log_mqtt_async("Alert", "Stage-file webhook POST rejected: missing or incorrect key.")
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        qs = parse_qs(parts.query)
        kind = qs.get("kind", [""])[0]
        if kind not in ("gaia", "birdnet"):
            self._respond(400, {"status": "error", "message": f"invalid or missing kind (got {kind!r})"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        if not body:
            self._respond(400, {"status": "error", "message": "empty body"})
            return

        file_stem = generation.latest_file_stem()
        if file_stem is None:
            log(f"Rejected stage-file POST ({kind}): no published hike found to stage against")
            _log_mqtt_async("Alert", f"Stage-file webhook POST ({kind}) rejected: no published hike found.")
            self._respond(409, {"status": "error", "message": "no published hike found"})
            return

        staging_dir = os.path.join(generation.SRV_DIR, f"{file_stem}_staging")
        os.makedirs(staging_dir, exist_ok=True)

        if kind == "gaia":
            dest = os.path.join(staging_dir, "gaia_embed.html")
        else:
            ext = qs.get("ext", ["zip"])[0]
            if ext not in ("zip", "json"):
                ext = "zip"
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            dest = os.path.join(staging_dir, f"birdnet_{ts}.{ext}")

        try:
            with open(dest, "wb") as f:
                f.write(body)
        except OSError as e:
            log(f"Failed to write staged file for {file_stem} ({kind}): {e}")
            _log_mqtt_async("Alert", f"Stage-file webhook failed to write {kind} for {file_stem}: {e}")
            self._respond(500, {"status": "error", "message": "write failed"})
            return

        log(f"Staged {kind} file for {file_stem}: {dest}")
        _log_mqtt_async("System", f"Staged {kind} file for {file_stem}.")
        self._respond(200, {"status": "ok", "file_stem": file_stem})

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
    # Makes a container rebuild/restart itself visible on the dashboard --
    # today's investigation (2026-07-28) spent a long time on SSH forensics
    # specifically because a container churn was invisible from here.
    _log_mqtt_async("System", "Orchestrator webhook receiver started.")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
