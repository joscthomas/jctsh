#!/usr/bin/env python3
"""JCTsh email-to-kanban-card watcher (CARD-0151).

Polls Joseph's Gmail inbox via the Gmail API (OAuth2, not IMAP -- Gmail
App Passwords weren't available on this account even with 2FA on) for
new emails to his plus-addressed alias (joscthomas+kbc@gmail.com) and
opens a placeholder kanban PR for each one via CARD-0128's
open_finding_pr(), reusing the same GitHub PAT already set up for the
Pi/M8 maintenance-check scripts (/etc/jctsh/github.env) -- no new
GitHub credential needed.

OAuth setup: a Google Cloud project + OAuth client (Desktop app type)
was created and PUBLISHED (not left in Testing), specifically because
Testing-mode refresh tokens for sensitive scopes like gmail.modify
expire after 7 days -- confirmed live during setup (a token minted
while in Testing carried a refresh_token_expires_in of ~7 days; an
identical token minted immediately after publishing had no expiry
field at all). Publishing still shows Google's "unverified app"
warning to anyone going through consent (expected/normal for a
personal single-user app that hasn't gone through Google's formal
verification process) -- bypassed once via the developer-only
"Advanced -> Go to ... (unsafe)" link during the one-time
authorization step that produced the refresh token stored in
EMAIL_ENV below.

Subject becomes the card's title/one-liner, body (if any) becomes
additional detail -- both are just concatenated into
open_finding_pr()'s single `message` argument, since CARD-0128's
_render_stub() already puts the full message into the stub's "Raw
finding" line regardless of length. Deliberately just a placeholder --
the real interview pass that scopes actual acceptance criteria happens
later, in a normal Claude Code session, not here.

Dedup is Gmail-native, not the fingerprint/state-file pattern the
other maintenance-check scripts use: each matching email is only ever
processed once, since the UNREAD label is removed immediately after a
PR opens successfully -- the next poll's query naturally excludes it,
no separate state file needed. If the PR-open call itself fails, the
label is deliberately left alone so the next poll retries it rather
than silently losing the idea.
"""
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from open_kanban_pr import open_finding_pr  # CARD-0128

BROKER    = "127.0.0.1"
PORT      = 1883
COMPONENT = "jctsh-core"
LOG_TOPIC = "jctsh/core/log-server/log"

GITHUB_ENV = "/etc/jctsh/github.env"            # GITHUB_PAT=...
EMAIL_ENV  = "/etc/jctsh/email-idea-check.env"  # GOOGLE_CLIENT_ID=..., GOOGLE_CLIENT_SECRET=..., GOOGLE_REFRESH_TOKEN=...
LOG_ENV    = "/etc/jctsh/log-server.env"        # MQTT_USER=..., MQTT_PASS=...

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PLUS_TAG  = "kbc"


def _load_env(path):
    env = {}
    with open(path) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env


def _api(method, url, access_token, body=None):
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def _get_access_token(email_env):
    data = urllib.parse.urlencode({
        "client_id": email_env["GOOGLE_CLIENT_ID"],
        "client_secret": email_env["GOOGLE_CLIENT_SECRET"],
        "refresh_token": email_env["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())["access_token"]


def _decode_part(data_b64url):
    padded = data_b64url + "=" * (-len(data_b64url) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _plain_body(payload):
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return _decode_part(payload["body"]["data"])
    for part in payload.get("parts", []) or []:
        text = _plain_body(part)
        if text:
            return text
    return ""


def _header(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _publish_log(category, message):
    log_env = _load_env(LOG_ENV)
    payload = json.dumps({"component": COMPONENT, "category": category, "message": message})
    subprocess.run(
        ["mosquitto_pub", "-h", BROKER, "-p", str(PORT),
         "-u", log_env["MQTT_USER"], "-P", log_env["MQTT_PASS"],
         "-t", LOG_TOPIC, "-m", payload],
        check=True, timeout=10,
    )


email_env = _load_env(EMAIL_ENV)
gh_env = _load_env(GITHUB_ENV)
access_token = _get_access_token(email_env)

query = f"to:{PLUS_TAG} is:unread"
listing = _api("GET", f"{GMAIL_API}/messages?" + urllib.parse.urlencode({"q": query}), access_token)
messages = listing.get("messages", [])

if not messages:
    print("No new idea emails.")
    raise SystemExit(0)

opened = []
for m in messages:
    msg = _api("GET", f"{GMAIL_API}/messages/{m['id']}?format=full", access_token)
    headers = msg["payload"]["headers"]
    subject = _header(headers, "Subject").strip() or "(no subject)"
    body = _plain_body(msg["payload"]).strip()
    message_id = _header(headers, "Message-ID") or f"<no-id-{m['id']}>"

    full_message = subject if not body else f"{subject}\n\n{body}"

    try:
        # Fresh state={} every call -- dedup is the Gmail UNREAD label,
        # not open_finding_pr()'s own single-fingerprint memory, which
        # is built for "same finding repeated across polls", not "many
        # distinct one-off emails". See module docstring.
        _, pr_url = open_finding_pr(COMPONENT, full_message, message_id, gh_env["GITHUB_PAT"], {})
        _api("POST", f"{GMAIL_API}/messages/{m['id']}/modify", access_token, {"removeLabelIds": ["UNREAD"]})
        opened.append((subject, pr_url))
    except Exception as e:
        print(f"Failed to open PR for '{subject}': {e} -- leaving unread for retry")

for subject, pr_url in opened:
    _publish_log("System", f'Email idea -> kanban PR: "{subject}" -- {pr_url}')
    print(f"Opened: {subject} -> {pr_url}")

if not opened and messages:
    raise SystemExit(1)
