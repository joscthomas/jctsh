# Back Patio Temp Sensor — MQTT Account Setup

Create a dedicated Mosquitto account for this component before flashing.
A missing account causes silent MQTT connection failure — the ESP32 will boot and
connect to WiFi but never publish sensor data or log messages.

---

## Commands (run on the Pi)

Choose a strong password, then run these three commands in order:

```bash
sudo mosquitto_passwd -b /etc/mosquitto/passwd back-patio-temp-sensor <password>
sudo chown root:mosquitto /etc/mosquitto/passwd
sudo systemctl restart mosquitto
```

Replace `<password>` with your chosen password.

**The `chown` command is mandatory, not optional.** See the gotcha section below.

---

## Ownership Gotcha

`sudo mosquitto_passwd` resets the group owner of `/etc/mosquitto/passwd` to `root`.
Mosquitto runs as the `mosquitto` user and requires group read access to the passwd file.
If the group is `root` instead of `mosquitto`, Mosquitto cannot read credentials and will
fail to authenticate any client — including Node-RED and Home Assistant, not just this device.

Always run `sudo chown root:mosquitto /etc/mosquitto/passwd` immediately after any
`mosquitto_passwd` command, then restart Mosquitto to pick up the change.

Confirm Mosquitto restarted cleanly:
```bash
sudo systemctl status mosquitto
```

Look for `Active: active (running)`. If it shows `failed`, check `journalctl -u mosquitto -n 20`
for the error.

---

## Store the Password

Save the password in `components/back-patio-temp-sensor/secrets.yaml`. This file is
gitignored — never commit it.

```yaml
mqtt_username: "back-patio-temp-sensor"
mqtt_password: "<your chosen password>"
```

---

## CLAUDE.md Update Required

After creating the account, add a row to the credentials table in the root `CLAUDE.md`:

| Account | Used by |
|---|---|
| `back-patio-temp-sensor` | back-patio-temp-sensor ESPHome device |

Add the new row at the end of the existing table.

---

## Checklist — completed 2026-09-21 16:08 MST (CARD-0219)

- [x] Password generated (24-char alphanumeric)
- [x] `mosquitto_passwd` command run on Pi
- [x] `chown root:mosquitto` run immediately after — confirmed `-rw-r----- root mosquitto`
- [x] `systemctl restart mosquitto` run
- [x] `systemctl is-active mosquitto` returns `active`; journal shows a clean config load
- [x] Password stored in `secrets.yaml` (gitignored) and in `credentials.local.md`
- [x] `back-patio-temp-sensor` row added to credentials table in root `CLAUDE.md`
- [x] **Authentication verified live** — `mosquitto_pub` as `back-patio-temp-sensor` to
      `jctsh/components/back-patio-temp-sensor/log` accepted by the broker. Not inferred
      from the account existing; the credential was actually exercised.

**Expected warning, not a failure.** `mosquitto_passwd` prints
`Warning: File /etc/mosquitto/passwd group is not root. Future versions will refuse to load this file.`
That is the inverse of this project's deliberate `chown root:mosquitto` — the file's group
*must* be `mosquitto` for the broker to read it. Ignore the warning; do not "fix" it by
setting the group back to root, which is exactly the failure the Ownership Gotcha above
describes. Worth watching if Mosquitto ever does start refusing the file.
