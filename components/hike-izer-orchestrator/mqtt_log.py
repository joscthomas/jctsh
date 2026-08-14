#!/usr/bin/env python
"""
MQTT publish-visibility logging for hike-izer-orchestrator (CARD-0086).

Same connect/publish/disconnect pattern as
components/m8/photo-server-heartbeat.py -- loop_start() before
publish, wait_for_publish() before loop_stop()/disconnect(), since a bare
publish()-then-disconnect() was found to drop QoS-1 messages in production
(see components/m8/heartbeat.md).
"""

import json
import os

import paho.mqtt.client as mqtt

BROKER = "192.168.1.117"
PORT = 1883
COMPONENT = "hike-izer-orchestrator"
TOPIC = "jctsh/hike-izer/publish/log"


def publish_log(category, message):
    username = os.environ.get("MQTT_USERNAME")
    password = os.environ.get("MQTT_PASSWORD")
    if not username or not password:
        print(f"[mqtt_log] MQTT_USERNAME/MQTT_PASSWORD not set -- skipping publish: {message}", flush=True)
        return

    payload = json.dumps({"component": COMPONENT, "category": category, "message": message})

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(username, password)
    client.connect(BROKER, PORT, 10)
    client.loop_start()
    info = client.publish(TOPIC, payload, qos=1)
    info.wait_for_publish(timeout=5)
    client.loop_stop()
    client.disconnect()
