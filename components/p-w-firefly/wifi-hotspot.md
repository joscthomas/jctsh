# WiFi Hotspot — Pleasure-Way Firefly Interface

Broadcast a permanent JCT-RV WiFi hotspot so the eRVin dashboard is reachable from any device in the coach, with or without a home network connection.

---

## How It Works

The Pi 3B+ BCM43438 chip supports concurrent STA+AP mode — it connects to JCTnet1 at home AND broadcasts JCT-RV simultaneously. A virtual AP interface (`uap0`) is created alongside `wlan0` at boot. `hostapd` runs on `uap0`; `wlan0` continues to handle home network connection as before.

- **At home:** wlan0 connected to JCTnet1, uap0 broadcasting JCT-RV on the same channel
- **In the RV:** wlan0 idle (no home network), uap0 broadcasting JCT-RV on channel 6

Dashboard access via JCT-RV: `http://192.168.5.1`

---

## Credentials

SSID: `JCT-RV` — password in `secrets.md`

---

## Files on Pi

### `/etc/systemd/system/uap0-setup.service`

Creates the virtual AP interface from wlan0 at boot, before hostapd starts.

```
[Unit]
Description=Create uap0 AP interface
Before=hostapd.service
After=sys-subsystem-net-devices-wlan0.device

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/sbin/iw dev wlan0 interface add uap0 type __ap
ExecStop=/sbin/iw dev uap0 del

[Install]
WantedBy=multi-user.target
```

### `/etc/hostapd/hostapd.conf`

```
interface=uap0
driver=nl80211
ssid=JCT-RV
hw_mode=g
channel=6
ieee80211n=1
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=<see secrets.md>
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
```

Channel 6 is the default for RV use (no home network). When wlan0 is connected at home, the brcmfmac driver forces uap0 to the same channel as wlan0 automatically.

### `/etc/default/hostapd`

`DAEMON_CONF="/etc/hostapd/hostapd.conf"`

### `/etc/systemd/network/05-uap0.network`

```
[Match]
Name=uap0

[Network]
LinkLocalAddressing=no
Address=192.168.5.1/24
```

### `/etc/dnsmasq.d/jct-rv.conf`

```
interface=uap0
bind-interfaces
port=0
dhcp-range=192.168.5.100,192.168.5.200,255.255.255.0,24h
dhcp-option=3,192.168.5.1
```

`port=0` disables DNS (systemd-resolved already holds port 53). Dashboard is accessed by IP so DNS is not needed on the hotspot.

---

## Package Installation Notes

The eRVin image is based on Raspbian Buster (EOL). The main Raspbian mirror (`raspbian.raspberrypi.org`) returns 404 for most packages. Workaround applied during setup:

1. Added Debian Buster archive as apt source: `deb [trusted=yes] http://archive.debian.org/debian buster main`
2. Downloaded hostapd directly: `wget http://archive.debian.org/debian/pool/main/w/wpa/hostapd_2.7+git20190128+0c1e29f-6+deb10u3_armhf.deb && sudo dpkg -i hostapd.deb`
3. dnsmasq installed from `archive.raspberrypi.org/debian` (raspi.list source, still active)

Source file: `/etc/apt/sources.list.d/debian-buster-archive.list`

---

## Confirmed Details

*(Step 8 confirmed complete — May 2026)*

| Item | Value |
|---|---|
| JCT-RV hotspot broadcasting | Yes — confirmed after reboot |
| uap0 IP address | 192.168.5.1/24 |
| DHCP range | 192.168.5.100–200 |
| DNS advertised to clients | 8.8.8.8 (Google) |
| IP masquerading | Enabled — clients share Pi's internet via wlan0 |
| Channel | Follows JCTnet1 (channel 10 at home); channel 6 in RV |
| Services enabled at boot | uap0-setup, hostapd, dnsmasq |
| IP forwarding | /etc/sysctl.d/99-jct-rv.conf — net.ipv4.ip_forward=1 |
| Dashboard reachable at 192.168.5.1 | Yes — http://192.168.5.1/ui/ confirmed from phone on JCT-RV |

---

## Troubleshooting

**uap0 not created at boot:** Check `sudo systemctl status uap0-setup`. The `iw dev wlan0 interface add uap0 type __ap` command requires wlan0 to exist first. If wlan0 isn't ready, the service fails silently — verify `wpa_supplicant@wlan0.service` started before uap0-setup.

**hostapd fails to start:** Run `sudo journalctl -u hostapd -n 30`. Confirm hostapd is not masked (`sudo systemctl unmask hostapd`). Confirm `DAEMON_CONF` is set in `/etc/default/hostapd`.

**uap0 gets 169.254.x.x instead of 192.168.5.1:** systemd-networkd hasn't applied 05-uap0.network yet. Run `sudo systemctl restart systemd-networkd`. Then restart dnsmasq. The `LinkLocalAddressing=no` setting in 05-uap0.network prevents the spurious link-local address on subsequent boots.

**dnsmasq "unknown interface uap0":** uap0 didn't have a real IP address when dnsmasq started. Ensure uap0-setup and systemd-networkd have assigned 192.168.5.1 before starting dnsmasq. Service ordering handles this on normal boots.

**dnsmasq "port 53: Address already in use":** Confirm `port=0` is present in `/etc/dnsmasq.d/jct-rv.conf`. This disables dnsmasq's DNS listener so it doesn't conflict with systemd-resolved.

**Android phone can't reach 192.168.5.1:** Android detects JCT-RV has no internet and silently routes traffic through cellular. Fix: go to WiFi settings → tap JCT-RV → enable "Use this network anyway" (or "Always use this network"). Set this once and Android remembers it.
