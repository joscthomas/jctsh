# Front Porch Temp Sensor — MQTT Account Setup (Step 2)

Create a dedicated Mosquitto account for this component before flashing.
A missing account causes silent MQTT connection failure — the ESP32 will boot and
connect to WiFi but never publish sensor data or log messages.

---

## Commands (run on the Pi)

Choose a strong password, then run these three commands in order:

```bash
sudo mosquitto_passwd -b /etc/mosquitto/passwd front-porch-temp-sensor <password>
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

Save the password in `components/front-porch-temp-sensor/secrets.yaml` (created in Step 3).
This file is gitignored — never commit it.

```yaml
mqtt_username: "front-porch-temp-sensor"
mqtt_password: "<your chosen password>"
```

The full `secrets.yaml` will be created from the template in Step 3. For now, just keep
the password somewhere safe until Step 3.

---

## CLAUDE.md Update Required

After creating the account, add a row to the credentials table in the root `CLAUDE.md`:

| Account | Used by |
|---|---|
| `front-porch-temp-sensor` | front-porch-temp-sensor ESPHome device |

The table currently ends at `salt-sensor`. Add the new row immediately after it.

---

## Checklist

- [ ] Password chosen
- [ ] `mosquitto_passwd` command run on Pi
- [ ] `chown root:mosquitto` run immediately after
- [ ] `systemctl restart mosquitto` run
- [ ] `systemctl status mosquitto` confirms `active (running)`
- [ ] Password stored securely (will go into `secrets.yaml` in Step 3)
- [ ] `front-porch-temp-sensor` row added to credentials table in root `CLAUDE.md`
