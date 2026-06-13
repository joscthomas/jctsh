# MQTT Infrastructure — Monitoring Layers

How to see what's happening at each layer of the DuckDNS → port forward → Mosquitto → fail2ban stack.

---

## Layer 1: ESPHome flash output

During `esphome run`, after OTA upload completes, the tool streams device log output via MQTT. Key lines to look for:

```
[I][mqtt:348]: Connected          ← firmware MQTT component connected successfully
[I][HikeLog:096]: Log file cleared ← SPIFFS had data, was replayed and cleared
[I][safe_mode:091]: Boot seems successful; resetting boot loop counter
```

If MQTT never connects, `[I][mqtt:348]: Connected` never appears and the tool will eventually time out.

---

## Layer 2: Log dashboard

`http://raspberrypi.local` (or `http://192.168.1.117`)

Every time the hiking-monitor boots and connects, two messages appear under the `hiking-monitor` component:

- `Hiking monitor online - ESPHome X.X.X, IP: 192.168.1.161`
- `MQTT connected`

If these appear, the full chain worked.

---

## Layer 3: Mosquitto log

```
ssh pi@raspberrypi.local "sudo tail -50 /var/log/mosquitto/mosquitto.log"
```

Or follow live:
```
ssh pi@raspberrypi.local "sudo tail -f /var/log/mosquitto/mosquitto.log"
```

**What the source IP tells you:**

| Source IP | Meaning |
|---|---|
| `192.168.1.161` | Direct LAN connection — old `raspberrypi.local` broker address |
| `174.18.46.157` | Through DuckDNS + port forward — NAT hairpinning from home network |
| Any cellular IP | Hotspot connection — device is on Pixel cellular, routing through port forward |

A successful connection looks like:
```
2026-06-12T18:46:56: New connection from 174.18.46.157:50922 on port 1883.
2026-06-12T18:46:56: New client connected from 174.18.46.157:50922 as hiking-monitor-04b24797df2c (p2, c0, k15, u'hiking-monitor').
```

A failed auth attempt looks like:
```
2026-06-12T18:46:56: New connection from 203.0.113.5:12345 on port 1883.
2026-06-12T18:46:56: Client <unknown> disconnected, not authorised.
```

---

## Layer 4: fail2ban log

```
ssh pi@raspberrypi.local "sudo tail -50 /var/log/fail2ban.log"
```

Or follow live:
```
ssh pi@raspberrypi.local "sudo tail -f /var/log/fail2ban.log"
```

A ban event looks like:
```
2026-06-12 18:50:00,000 fail2ban.actions [1234]: NOTICE  [mosquitto] Ban 203.0.113.5
```

Check current jail status (active bans, total failed attempts):
```
ssh pi@raspberrypi.local "sudo fail2ban-client status mosquitto"
```

Manually unban an IP if needed:
```
ssh pi@raspberrypi.local "sudo fail2ban-client set mosquitto unbanip 203.0.113.5"
```

---

## Layer 5: DuckDNS

Verify DuckDNS has the current public IP:
```
ssh pi@raspberrypi.local "cat /home/pi/duckdns/duck.log"
```

Output should be `OK`. Run the update manually if needed:
```
ssh pi@raspberrypi.local "/home/pi/duckdns/duck.sh && cat /home/pi/duckdns/duck.log"
```

Verify the hostname resolves to your current public IP:
```
ssh pi@raspberrypi.local "curl -s https://api.duckdns.org/update?domains=jctsh&token=&verbose=true"
```

---

## Configuration reference

| File | Location | Purpose |
|---|---|---|
| DuckDNS client | `/home/pi/duckdns/duck.sh` | Updates DuckDNS with current public IP |
| DuckDNS cron | `crontab -l` (pi user) | Runs duck.sh every 5 minutes |
| Mosquitto timestamp config | `/etc/mosquitto/conf.d/jctsh.conf` | ISO 8601 log timestamps for fail2ban |
| fail2ban filter | `/etc/fail2ban/filter.d/mosquitto.conf` | Matches connection attempts |
| fail2ban jail | `/etc/fail2ban/jail.d/mosquitto.conf` | Ban rules: 10 attempts/60s → 1h ban |
| Mosquitto log | `/var/log/mosquitto/mosquitto.log` | All connection and auth events |
| fail2ban log | `/var/log/fail2ban.log` | Ban/unban events |
