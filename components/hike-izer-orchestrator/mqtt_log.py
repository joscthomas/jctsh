#!/usr/bin/env python
"""
MQTT publish-visibility logging for hike-izer-orchestrator (CARD-0086).

Same connect/publish/disconnect pattern as
components/photo-server/photo-server-heartbeat.py -- loop_start() before
publish, wait_for_publish() before loop_stop()/disconnect(), since a bare
publish()-then-disconnect() was found to drop QoS-1 messages in production
(see components/photo-server/heartbeat.md).
"""

import json
import os

import paho.mqtt.client as mqtt

BROKER = "192.168.1.117"
PORT = 1883
COMPONENT = "hike-izer-orchestrator"
TOPIC = "jctsh/hike-izer/publish/log"


def publish_log(category, message, component=None):
    """CARD-0225: component defaults to this container's own identity
    (every existing call site) but can be overridden -- the new
    /webhook/pipeline-log relay forwards GPS Track/Hiking Observations/
    Hike Start Forecast log lines through this same MQTT connection, and
    those should show up on the dashboard tagged as their own pipeline,
    not lumped under "hike-izer-orchestrator"."""
    username = os.environ.get("MQTT_USERNAME")
    password = os.environ.get("MQTT_PASSWORD")
    if not username or not password:
        print(f"[mqtt_log] MQTT_USERNAME/MQTT_PASSWORD not set -- skipping publish: {message}", flush=True)
        return

    payload = json.dumps({"component": component or COMPONENT, "category": category, "message": message})

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(username, password)
    client.connect(BROKER, PORT, 10)
    client.loop_start()
    info = client.publish(TOPIC, payload, qos=1)
    info.wait_for_publish(timeout=5)
    client.loop_stop()
    client.disconnect()
