#!/usr/bin/env python
"""
CARD-0141: push a notification to Joseph's Pixel via Home Assistant's
companion-app notify service, so a hike-summary publish (or failure)
surfaces immediately instead of only appearing on the MQTT log dashboard
(mqtt_log.py). Same best-effort, log-and-continue convention as that
module -- a notification failure must never break generation itself.

HA runs on the Pi, this container runs on the M8 -- HA_URL points at the
Pi's LAN IP, same address mqtt_log.py's own BROKER constant already uses
successfully from this same container, not a new cross-host path.
"""

import json
import os
import urllib.request

NOTIFY_SERVICE = "mobile_app_pixel_10_pro_xl"


def send_push(title, message):
    ha_url = os.environ.get("HA_URL")
    ha_token = os.environ.get("HA_TOKEN")
    if not ha_url or not ha_token:
        print(f"[ha_notify] HA_URL/HA_TOKEN not set -- skipping push: {message}", flush=True)
        return

    req = urllib.request.Request(
        f"{ha_url}/api/services/notify/{NOTIFY_SERVICE}",
        data=json.dumps({"title": title, "message": message}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[ha_notify] push notification failed: {e}", flush=True)
