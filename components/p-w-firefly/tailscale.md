# Tailscale — Pleasure-Way Firefly Interface

Install Tailscale on the RV Pi so the eRVin dashboard is reachable remotely from any device on the same Tailscale account, without port forwarding or a public IP.

---

## Confirmed Details

*(Step 9 confirmed complete — May 2026)*

| Item | Value |
|---|---|
| Tailscale IP | 100.90.246.43 |
| Device name | coachproxyos |
| Account | joscthomas@gmail.com |
| Tailscale version | 1.98.3 |
| tailscaled enabled at boot | Yes |
| Dashboard remote access | http://100.90.246.43 |

---

## Installation Notes

The eRVin image is based on Raspbian Buster (EOL). The main Raspbian mirror (`raspbian.raspberrypi.org`) no longer serves packages and caused `apt-get` to fail hard. Workaround applied:

- Renamed `/etc/apt/sources.list` to `/etc/apt/sources.list.disabled` to prevent apt from failing on the dead mirror
- Tailscale installed from its own repo (`pkgs.tailscale.com/stable/raspbian/buster`) which remains active
- `tailscaled` was auto-enabled at boot by the package installer

---

## Re-authenticating

Tailscale auth keys expire. If the Pi loses its Tailscale connection:

```
sudo tailscale up
```

Visit the printed URL to re-authenticate, then confirm with `tailscale status`.

---

## Access

From any device on the same Tailscale account:

| Service | URL |
|---|---|
| eRVin dashboard | http://100.90.246.43 |
| Node-RED editor | http://100.90.246.43:1880 |
| SSH | ssh pi@100.90.246.43 |
