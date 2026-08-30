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
import open_kanban_pr  # CARD-0173: /webhook/idea
import templating  # CARD-0194: reuses _esc() for the live-HTML patch

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
PORT = int(os.environ.get("PORT", "8080"))
# CARD-0194: deliberately separate from WEBHOOK_SECRET -- that's a long
# random string, fine for a machine-to-machine webhook but not something
# Joseph wants to type on his phone. A short, memorable PIN, checked
# server-side on every save (the client never verifies it itself, just
# remembers a working one in localStorage after a first successful save).
EDIT_PIN = os.environ.get("EDIT_PIN", "")
# CARD-0173: same GitHub PAT already used by this M8's own host-level
# maintenance-check.py (that's how PR #5, the KEK CA firmware finding,
# got opened) -- reused here, not a new token, since this container is a
# separate process from that host script and needs its own copy via env
# var, same "one credential, read from wherever it's needed" pattern
# already used for HA_TOKEN across this repo.
GITHUB_PAT = os.environ.get("GITHUB_PAT", "")
# CARD-0227: base URL for images written to generation.SRV_DIR/idea-images/,
# which Caddy's catch-all file_server block already serves publicly --
# components/hike-izer-web/Caddyfile's `handle {}` block roots at
# /srv/hike-izer, the same directory generation.SRV_DIR points at inside
# this container (shared volume with the `web` service).
PUBLIC_SRV_BASE_URL = "https://hikes.jctnet.com"


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
        if parts.path == "/webhook/idea-image":
            self._handle_idea_image(parts)
            return
        if parts.path == "/webhook/idea":
            self._handle_idea(parts)
            return
        if parts.path == "/webhook/edit-observation":
            self._handle_edit_observation(parts)
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
        no background thread needed.

        CARD-0136: a BirdNET share can reach here *before* the hike-end
        webhook does (confirmed live 2026-08-03 -- a share landed 27s ahead
        of the "stopped" event for the same hike), at which point
        current_or_latest_file_stem() can only resolve to some other,
        already-published hike -- silently wrong, not just unavailable. For
        kind=birdnet specifically, an optional local_datetime query param
        (same Tasker "Parse/Format Date and Time" pattern the hike-end
        webhook already uses) lets this handler check whether the
        already-known hike's own date actually matches the file's -- if not,
        it parks the file in a dated pending directory for run() to claim
        once that hike's own file_stem actually exists, instead of guessing.
        Gaia embeds don't get this treatment -- staged well after hike-end
        during step 2's conversational flow, no comparable race exists."""
        if not self._authorized(parts):
            log("Rejected stage-file POST: missing or incorrect key")
            _log_mqtt_async("Alert", "Stage-file webhook POST rejected: missing or incorrect key.")
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        qs = parse_qs(parts.query)
        kind = qs.get("kind", [""])[0]
        if kind not in ("gaia", "birdnet"):
            log(f"Rejected stage-file POST: invalid or missing kind (got {kind!r})")
            _log_mqtt_async("Alert", f"Stage-file webhook POST rejected: invalid or missing kind (got {kind!r}).")
            self._respond(400, {"status": "error", "message": f"invalid or missing kind (got {kind!r})"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        if not body:
            log(f"Rejected stage-file POST ({kind}): empty body")
            _log_mqtt_async("Alert", f"Stage-file webhook POST ({kind}) rejected: empty body.")
            self._respond(400, {"status": "error", "message": "empty body"})
            return

        file_stem = generation.current_or_latest_file_stem()

        pending_date_str = None
        if kind == "birdnet":
            local_datetime = qs.get("local_datetime", [None])[0]
            if local_datetime:
                try:
                    date_str, _offset_str = generation._local_date_and_offset(local_datetime)
                except ValueError as e:
                    log(f"Stage-file POST (birdnet): unparseable local_datetime ({e}) -- falling back to UTC date")
                    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            else:
                # No local_datetime at all (older Tasker config, or some
                # future non-Tasker sender) -- UTC date is a reasonable
                # guess rather than rejecting a real file over a missing
                # param, same "don't lose data over an optional field"
                # judgment call as the fallback above.
                date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            if file_stem is None or generation._date_str_from_stem(file_stem) != date_str:
                pending_date_str = date_str

        if pending_date_str is not None:
            staging_dir = generation.pending_birdnet_dir(pending_date_str)
        elif file_stem is not None:
            staging_dir = os.path.join(generation.SRV_DIR, f"{file_stem}_staging")
        else:
            log(f"Rejected stage-file POST ({kind}): no published hike found to stage against")
            _log_mqtt_async("Alert", f"Stage-file webhook POST ({kind}) rejected: no published hike found.")
            self._respond(409, {"status": "error", "message": "no published hike found"})
            return

        # CARD-0119: chmod explicitly (not via makedirs' mode=, which the
        # container's umask would mask down anyway) so the SSHFS-Win mount
        # -- connected as the non-root `jct` Linux user -- can actually
        # write into a directory this root-running process creates.
        os.makedirs(staging_dir, exist_ok=True)
        os.chmod(staging_dir, 0o777)

        if kind == "gaia":
            dest = os.path.join(staging_dir, "gaia_embed.txt")
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

        if pending_date_str is not None:
            log(f"Staged {kind} file as pending for {pending_date_str} (no matching hike yet): {dest}")
            _log_mqtt_async("System", f"Staged {kind} file as pending for {pending_date_str} (no matching hike yet).")
            self._respond(200, {"status": "ok", "file_stem": None, "pending_date": pending_date_str})
        else:
            log(f"Staged {kind} file for {file_stem}: {dest}")
            _log_mqtt_async("System", f"Staged {kind} file for {file_stem}.")
            self._respond(200, {"status": "ok", "file_stem": file_stem})

    def _handle_idea_image(self, parts):
        """CARD-0227: receives an image attached to a jctsh-idea email,
        relayed here by email-idea-check.py (running on the Pi -- Google
        Apps Script can't hold a raw socket/MQTT connection, and this
        pipeline doesn't use MQTT anyway, it's a plain HTTP relay to
        wherever the image can actually be hosted). Writes it into
        generation.SRV_DIR/idea-images/, the same directory Caddy's
        catch-all file_server block already serves publicly at
        hikes.jctnet.com (components/hike-izer-web/Caddyfile) -- no new
        Caddy route, no new Cloudflare config, this just reuses the
        existing /webhook/* proxy rule. Returns the resulting public URL
        so the caller can embed it in the PR body (open_kanban_pr.py's
        image_url param)."""
        if not self._authorized(parts):
            log("Rejected idea-image POST: missing or incorrect key")
            _log_mqtt_async("Alert", "Idea-image webhook POST rejected: missing or incorrect key.")
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        qs = parse_qs(parts.query)
        ext = qs.get("ext", ["jpg"])[0].lower()
        if ext not in ("jpg", "jpeg", "png", "gif", "webp"):
            log(f"Rejected idea-image POST: invalid ext (got {ext!r})")
            _log_mqtt_async("Alert", f"Idea-image webhook POST rejected: invalid ext (got {ext!r}).")
            self._respond(400, {"status": "error", "message": f"invalid ext (got {ext!r})"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        if not body:
            log("Rejected idea-image POST: empty body")
            _log_mqtt_async("Alert", "Idea-image webhook POST rejected: empty body.")
            self._respond(400, {"status": "error", "message": "empty body"})
            return

        images_dir = os.path.join(generation.SRV_DIR, "idea-images")
        # CARD-0119's own reasoning applies here too: chmod explicitly so
        # anything else that later needs to touch this directory (not
        # just this root-running container) isn't blocked by a masked-down
        # umask default.
        os.makedirs(images_dir, exist_ok=True)
        os.chmod(images_dir, 0o777)

        filename = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}.{ext}"
        dest = os.path.join(images_dir, filename)

        try:
            with open(dest, "wb") as f:
                f.write(body)
        except OSError as e:
            log(f"Failed to write idea image {filename}: {e}")
            _log_mqtt_async("Alert", f"Idea-image webhook failed to write {filename}: {e}")
            self._respond(500, {"status": "error", "message": "write failed"})
            return

        url = f"{PUBLIC_SRV_BASE_URL}/idea-images/{filename}"
        log(f"Staged idea image: {dest} -> {url}")
        _log_mqtt_async("System", f"Staged idea image {filename}.")
        self._respond(200, {"status": "ok", "url": url})

    def _handle_idea(self, parts):
        """CARD-0173: Tasker voice-capture -> straight to a placeholder
        kanban PR, no email in between. Same open_finding_pr() every
        other maintenance-check script in this repo already uses
        (CARD-0128) -- component "jctsh-core", matching email-idea-
        check.py's own choice, so a voice-captured idea reads identically
        to an emailed one on the kanban board, no third "auto-opened
        from X" variant to special-case anywhere.

        Runs synchronously, not backgrounded like hike-end -- opening a
        PR is a handful of fast GitHub API calls, not a multi-step
        generation pipeline, same reasoning _handle_stage_file already
        uses for its own synchronous response ("writing a file is fast,
        no background thread needed"). A real, immediate success/failure
        response is also what makes Tasker's own confirmation Flash
        ("Idea logged." vs "Idea failed.") mean anything.

        fingerprint is a fresh timestamp each call, not reused across
        requests -- state is always {} too, same as email-idea-check.py's
        own per-message calls. There's no repeat-finding concept here the
        way maintenance-check scripts have (the same underlying condition
        showing up on every poll); every voice capture is a genuinely new,
        distinct utterance, so open_finding_pr()'s dedup logic is simply
        never exercised via this path."""
        if not self._authorized(parts):
            log("Rejected idea webhook POST: missing or incorrect key")
            _log_mqtt_async("Alert", "Idea webhook POST rejected: missing or incorrect key.")
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        if not GITHUB_PAT:
            log("Rejected idea webhook POST: GITHUB_PAT not configured")
            _log_mqtt_async("Alert", "Idea webhook POST rejected: GITHUB_PAT not configured on this host.")
            self._respond(500, {"status": "error", "message": "not configured"})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            log(f"Rejected idea webhook POST: invalid JSON body ({raw!r})")
            self._respond(400, {"status": "error", "message": "invalid JSON"})
            return

        text = (payload.get("text") or "").strip()
        if not text:
            log("Rejected idea webhook POST: empty or missing 'text'")
            self._respond(400, {"status": "error", "message": "empty or missing 'text'"})
            return

        fingerprint = f"voice-{datetime.now(timezone.utc).isoformat()}"
        try:
            _, pr_url = open_kanban_pr.open_finding_pr(
                "jctsh-core", text, fingerprint, GITHUB_PAT, {},
            )
        except Exception as e:
            log(f"Idea webhook: open_finding_pr failed: {e}")
            _log_mqtt_async("Alert", f"Idea webhook failed to open PR: {e}")
            self._respond(502, {"status": "error", "message": "failed to open PR"})
            return

        log(f"Idea webhook: opened {pr_url} for {text!r}")
        _log_mqtt_async("System", f'Voice idea -> kanban PR: "{text}" -- {pr_url}')
        self._respond(200, {"status": "ok", "pr_url": pr_url})

    def _handle_edit_observation(self, parts):
        """CARD-0194: manual observation-text correction from a hike page's
        hidden edit UI. Auth is a short PIN (EDIT_PIN), not WEBHOOK_SECRET --
        see that constant's own comment. Writes the correction to a small
        per-hike overrides file (durable, survives regeneration -- applied
        by generation._apply_observation_overrides()) and, for immediate
        effect, patches the already-published static HTML directly rather
        than waiting for a future regeneration."""
        if not EDIT_PIN:
            log("Rejected edit-observation POST: EDIT_PIN not configured")
            _log_mqtt_async("Alert", "Edit-observation webhook POST rejected: EDIT_PIN not configured on this host.")
            self._respond(500, {"status": "error", "message": "not configured"})
            return

        provided_key = parse_qs(parts.query).get("key", [""])[0]
        if not hmac.compare_digest(provided_key, EDIT_PIN):
            log("Rejected edit-observation POST: incorrect PIN")
            _log_mqtt_async("Alert", "Edit-observation webhook POST rejected: incorrect PIN.")
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            log(f"Rejected edit-observation POST: invalid JSON body ({raw!r})")
            self._respond(400, {"status": "error", "message": "invalid JSON"})
            return

        file_stem = (payload.get("file_stem") or "").strip()
        timestamp = (payload.get("timestamp") or "").strip()
        text = payload.get("text")
        # Path-safety: file_stem is embedded directly into a filesystem path
        # below -- reject anything that could escape SRV_DIR.
        if not file_stem or not timestamp or text is None or "/" in file_stem or "\\" in file_stem or ".." in file_stem:
            log(f"Rejected edit-observation POST: missing/invalid field (file_stem={file_stem!r}, timestamp={timestamp!r})")
            self._respond(400, {"status": "error", "message": "missing or invalid file_stem, timestamp, or text"})
            return

        overrides_path = os.path.join(generation.SRV_DIR, f"{file_stem}_hike-summary.overrides.json")
        try:
            with open(overrides_path, "r", encoding="utf-8") as f:
                overrides = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            overrides = {}
        overrides[timestamp] = text
        try:
            with open(overrides_path, "w", encoding="utf-8") as f:
                json.dump(overrides, f, indent=2)
        except OSError as e:
            log(f"Edit-observation: failed to write overrides file for {file_stem}: {e}")
            _log_mqtt_async("Alert", f"Edit-observation failed to write overrides for {file_stem}: {e}")
            self._respond(500, {"status": "error", "message": "write failed"})
            return

        # Immediate effect: patch the already-published static HTML too,
        # not just the durable overrides file -- otherwise the correction
        # wouldn't show up until the next full regeneration, which may be
        # days away or may never happen again for an already-finished hike.
        html_path = os.path.join(generation.SRV_DIR, f"{file_stem}_hike-summary.html")
        patched = False
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()
            marker = f'data-obs-ts="{templating._esc(timestamp)}">'
            start = html.find(marker)
            if start != -1:
                start += len(marker)
                end = html.find("</span>", start)
                if end != -1:
                    html = html[:start] + templating._esc(text) + html[end:]
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html)
                    patched = True
        except FileNotFoundError:
            pass

        log(f"Edit-observation: {file_stem} @ {timestamp} -> {text!r} (live page patched: {patched})")
        _log_mqtt_async(
            "System",
            f'Observation edited on {file_stem}: "{text}"' + ("" if patched else " (overrides saved, but the live page's matching row wasn't found to patch)"),
        )
        self._respond(200, {"status": "ok", "patched_live_page": patched})

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
