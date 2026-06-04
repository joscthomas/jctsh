# Hiking Monitor — MQTT Account Setup
**Component:** hiking-monitor
**Purpose:** Commands to create the dedicated Mosquitto account for this component.

---

## Account Details

| Field | Value |
|---|---|
| Account name | `hiking-monitor` |
| Password | See `credentials.local.md` → Mosquitto table |

---

## Commands — Run on Pi

```bash
ssh pi@raspberrypi.local "sudo mosquitto_passwd -b /etc/mosquitto/passwd hiking-monitor 41eTiwh0XzMlmoDnPOYc && sudo chown root:mosquitto /etc/mosquitto/passwd && sudo systemctl restart mosquitto && sudo systemctl status mosquitto --no-pager | grep Active"
```

Expected output: `Active: active (running)`

**Why the chown is required:** `sudo mosquitto_passwd` resets `/etc/mosquitto/passwd` group ownership to `root`. Mosquitto runs as the `mosquitto` user and cannot read the file without group access. Always run `chown` immediately after any `mosquitto_passwd` operation.

---

## CLAUDE.md Update Required

After running the command above, add a row to the MQTT credentials table in root `CLAUDE.md`:

| Account | Used by |
|---|---|
| `hiking-monitor` | hiking-sensor ESPHome device |

---

## Credential Storage

Password is stored in `components/hiking-sensor/secrets.yaml` (gitignored) as `mqtt_password`.
