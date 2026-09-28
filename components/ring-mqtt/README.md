# ring-mqtt — Ring Doorbell/Camera MQTT + RTSP Gateway

Runs on the M8 (`hosts/m8/`). Bridges Ring devices to Home Assistant via MQTT discovery
and provides an RTSP gateway for live view (`camera.play_stream` / Generic Camera in HA,
CARD-0146).

**Status:** Production.

Pinned to an explicit version (`5.9.3`, CARD-0344) rather than `:latest`, matching this
repo's standing pin-don't-float convention (CARD-0352 did the same for cloudflared) —
now covered by `hosts/m8/container-update-check.py`'s `SERVICES` list like every other
pinned M8 container.

## Deploy

```bash
scp components/ring-mqtt/docker-compose.yml jct@m8.local:/home/jct/ring-mqtt/docker-compose.yml
ssh jct@m8.local "cd /home/jct/ring-mqtt && docker compose up -d"
```

`./config` (device pairing state, tokens) and MQTT credentials are host-local, not
repo-tracked.
