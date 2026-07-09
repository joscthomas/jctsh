# JCTsh Security Hardening Plan
**Author:** Joseph C Thomas (JCT)
**Purpose:** Step-by-step Claude Code instructions to harden the JCTsh smart home ecosystem against the attack techniques used in nation-state residential proxy and credential-based campaigns (e.g., Midnight Blizzard).
**Version:** 1.1
**Version description:** Added Steps 9–14 covering Ring/Amazon, SmartThings/Samsung, Ecobee, Google accounts, router firmware, and router admin credentials. Expanded Summary Table. Step 5 Google MFA cross-reference updated to point to new Step 11.
**Project:** JCTsh
**Status:** All steps (1–14 + Final) complete as of 2026-07-09 (CARD-022, CARD-023). See findings below each step.

---

## Context

This plan addresses the threat class illustrated by the Midnight Blizzard / Microsoft breach: residential devices recruited as proxy hop points, credential theft, OAuth abuse, and lateral movement from weak or unprotected accounts. The JCTsh system is not a high-value nation-state target, but the same techniques are used at scale against residential networks by lower-level threat actors.

Steps are ordered by priority: highest-risk items with the lowest remediation effort first. Steps 1–8 cover local infrastructure. Steps 9–14 cover cloud-dependent devices and accounts; these are manual steps that Claude Code can guide but cannot execute directly.

---

## Before You Begin

Read `JCTsh-Build-Standards.md` before executing any step. All findings and new patterns discovered during execution must be harvested back to that document as the final step.

---

## Step 1 — Audit `secrets.yaml` git exclusion (ESP32 / ESPHome)

**Risk:** API keys, Wi-Fi passwords, and MQTT credentials committed to GitHub are permanently exposed in history even after deletion.

**Actions:**
1. Open a PowerShell terminal in the JCTsh monorepo root.
2. Verify `.gitignore` contains an entry for `secrets.yaml` and any file matching `*secrets*` or `*.key`.
3. Run the following to confirm no secrets files have ever been committed:
   ```powershell
   git log --all --full-history -- "**/secrets.yaml"
   git log --all --full-history -- "**/*.key"
   ```
4. If any results are returned, report the commit hashes and filenames — do not attempt remediation automatically; pause and report to Joseph.
5. Confirm `secrets.yaml` exists in each ESPHome component directory and is present on disk but absent from `git status` tracked files.
6. Document findings in a summary comment at the top of this step.

**Done when:** `git log` returns no results for secrets files and `.gitignore` is confirmed correct.

**Findings (2026-06-20):** PASS. `.gitignore` excludes `secrets.yaml`, `secrets.h`, and `credentials.local.md`. `git log` returned no results for `**/secrets.yaml` or `**/*.key` — nothing ever committed. Secrets files confirmed on disk and untracked: `components/front-porch-temp-sensor/secrets.yaml`, `components/garage-radar/secrets.yaml`, `components/hiking-sensor/secrets.yaml`, `components/salt-sensor/secrets.h` (×2, one in subdirectory). No action needed.

---

## Step 2 — Audit Raspberry Pi SSH configuration

**Risk:** Password-based SSH on the Pi exposes it to the same password-spray attacks used against Microsoft. The Pi hosts Mosquitto, Node-RED, and Home Assistant — the highest-value target in JCTsh.

**Actions:**
1. SSH into the Pi (via Tailscale).
2. Check `/etc/ssh/sshd_config` for the following settings and confirm all are set as shown:
   ```
   PasswordAuthentication no
   PermitRootLogin no
   PubkeyAuthentication yes
   ```
3. If any setting is incorrect, update `/etc/ssh/sshd_config` and reload SSH:
   ```bash
   sudo systemctl reload sshd
   ```
4. Confirm at least one authorized public key exists in `~/.ssh/authorized_keys`.
5. Attempt a password-based SSH login from a separate terminal to confirm it is rejected.
6. Document the current and corrected state.

**Done when:** Password auth is confirmed disabled and a key-based login test succeeds.

**Findings (2026-06-20):** FIXED. `/etc/ssh/sshd_config.d/50-cloud-init.conf` contained `PasswordAuthentication yes`, explicitly overriding the default. Changed to `PasswordAuthentication no` and reloaded sshd. Password auth now rejected (`Permission denied (publickey)` only — password no longer offered). `PermitRootLogin` is default `prohibit-password` (acceptable). `PubkeyAuthentication` is default `yes`. Key-based login confirmed working via Tailscale.

---

## Step 3 — Audit Raspberry Pi open ports and services

**Risk:** Unintended open ports (Mosquitto, Node-RED, HA) reachable from the internet rather than only from the local network and Tailscale.

**Actions:**
1. On the Pi, run:
   ```bash
   sudo ss -tlnp
   ```
2. For each port listed, identify the service and its intended audience:
   - Port 1883 (Mosquitto MQTT) — should be LAN-only or Tailscale-only; must NOT be internet-facing.
   - Port 1880 (Node-RED) — should be LAN-only or Tailscale-only.
   - Port 8123 (Home Assistant) — should be LAN-only or Tailscale-only.
   - Port 22 (SSH) — acceptable only via Tailscale.
3. On the router admin page, confirm no port forwarding rules exist for ports 1883, 1880, or 8123.
4. If any of those ports are forwarded, remove the forwarding rules and document what was removed.
5. Document the full port list and the disposition of each.

**Done when:** No JCTsh service ports are exposed directly to the internet; all remote access is via Tailscale only.

**Findings (2026-06-20):** PASS with one intentional exception and one fix.

Port inventory (post-remediation):

| Port | Service | Disposition |
|------|---------|-------------|
| 22 | sshd | LAN + Tailscale — key auth only (fixed in Step 2) |
| 80 | log server (python3) | LAN + Tailscale — not internet-forwarded |
| 443 | nginx (Tailscale HTTPS proxy for HA) | Tailscale-only in practice — cert is for `raspberrypi.tailfe828a.ts.net`, LAN access yields cert error; not internet-forwarded |
| 1880 | Node-RED | LAN + Tailscale — not internet-forwarded |
| 1883 | Mosquitto | LAN + **internet via DuckDNS/port-forward** — INTENTIONAL; required for ESP32 hotspot connectivity (hiking-monitor, CARD-008); mitigated by fail2ban + strong credentials; TLS pending (CARD-003) |
| 8123 | Home Assistant | LAN + Tailscale — not internet-forwarded; external access via Nabu Casa |
| 18554 | go2rtc | localhost only — OK |
| 18555 | go2rtc (WebRTC API) | LAN — HA camera component; not internet-forwarded |
| 37995 | python3 | localhost only — internal HA component |
| 111 | rpcbind | **FIXED** — disabled and stopped; NFS portmapper not needed |

Router port forwarding confirmation (1880, 8123) requires home WiFi access to `192.168.1.1` — deferred to next home session. Based on CLAUDE.md and MQTT-only configuration, only port 1883 is expected to be forwarded.

---

## Step 4 — Audit MQTT broker authentication

**Risk:** An open Mosquitto instance (no username/password) on the LAN allows any device that joins the network to publish or subscribe to all JCTsh topics.

**Actions:**
1. Check `/etc/mosquitto/mosquitto.conf` (or the active config file) for:
   ```
   allow_anonymous false
   password_file /etc/mosquitto/passwd
   ```
2. If `allow_anonymous true` is set or the password_file line is absent, Mosquitto is open. Report this finding and pause — do not change the config without Joseph's confirmation, as all ESPHome devices will need credential updates simultaneously.
3. If authentication is already enabled, verify the password file exists and is non-empty:
   ```bash
   sudo cat /etc/mosquitto/passwd
   ```
4. Confirm the credentials in `secrets.yaml` for at least one ESPHome component match a valid entry in the password file.
5. Document the current state.

**Done when:** Mosquitto is confirmed to require authentication, or the finding is clearly documented for a follow-up remediation session.

**Findings (2026-06-20):** PASS. Auth config is in `/etc/mosquitto/conf.d/jctsh.conf` (included via `include_dir`): `allow_anonymous false`, `password_file /etc/mosquitto/passwd`. Passwd file has 8 entries (matches known accounts: jctsh-log-server, nodered, homeassistant, garage-radar, salt-sensor, front-porch-temp-sensor, hiking-monitor, plus one). No anonymous access possible.

---

## Step 5 — Audit Tailscale MFA and ACL

**Risk:** Tailscale is the sole remote access path to the Pi. A compromised Tailscale account removes all network isolation.

**Actions:**
1. Open https://login.tailscale.com/admin in a browser.
2. Confirm the account uses a login method with MFA enabled:
   - If logged in via Google: MFA status is audited in Step 11. Cross-reference that step's findings here.
   - If logged in via a Tailscale account directly: confirm a TOTP or hardware key is enrolled under Settings > Keys.
3. In the Tailscale admin console, review the ACL (Access Controls tab):
   - Confirm only trusted devices (the Pi, Joseph's Windows machine, Pixel 10 Pro XL) are in the tailnet.
   - Look for any unfamiliar devices and report them.
4. Document device list and ACL settings.

**Done when:** MFA status is confirmed and tailnet device list is reviewed and clean.

**Findings (2026-06-20):** PARTIAL. Device list via `tailscale status` — 4 devices, all under `joscthomas@`, all recognized:
- `100.70.162.24` raspberrypi (linux) — home Pi
- `100.90.246.43` coachproxyos (linux) — RV Pi, offline
- `100.112.116.79` desktop-fqbdl5b (windows) — Joseph's Windows machine
- `100.126.154.88` jct-pixel-10-pro-xl (android) — Pixel phone

No unfamiliar devices. ACL: default (all devices in tailnet can reach each other). MFA: Tailscale uses Google account (`joscthomas@`) — MFA status deferred to CARD-023 Step 11 (Google account audit).

---

## Step 6 — Audit router UPnP setting

**Risk:** UPnP allows IoT devices (Ring cameras, Google Home, smart plugs, ESP32s) to automatically open inbound ports on the router without Joseph's knowledge. This is a primary recruitment mechanism for residential proxy networks.

**Actions:**
1. Log into the router admin interface.
2. Locate the UPnP setting (typically under Advanced > NAT or Advanced > UPnP).
3. If UPnP is enabled:
   - Note which devices have registered UPnP port mappings (usually visible in the same section).
   - Document the current mappings.
   - Report to Joseph before disabling — disabling UPnP can break some devices (e.g., some Ring features, gaming consoles). Joseph will decide whether to disable.
4. If UPnP is already disabled, confirm and document.

**Done when:** UPnP state is documented and Joseph has been given the current mapping list to make an informed decision.

**Findings (2026-06-20):** DEFERRED — requires access to router admin at `192.168.1.1`, which is only reachable on home WiFi. Joseph was not on home WiFi during this session. Complete when next on home network: log into router admin → Advanced → NAT/UPnP → document state and any active UPnP mappings.

**Update (2026-07-09):** DONE. UPnP was enabled with zero registered clients — no device depended on it. Disabled via Advanced → NAT Forwarding → UPnP on the TP-Link Archer AXE75 admin page. Step 6 complete.

---

## Step 7 — Audit Home Assistant external access configuration

**Risk:** If HA is configured with an externally-accessible URL or the HA Cloud (Nabu Casa) integration is enabled without MFA, it creates a cloud-exposed entry point.

**Actions:**
1. In Home Assistant, navigate to Settings > System > Network.
2. Check whether an external URL is configured. If so, document the URL and confirm it is only reachable via Tailscale (not a public DNS entry pointing to the home IP).
3. Check Settings > Home Assistant Cloud — if Nabu Casa is enabled and active, note it. It is a legitimate service but adds a cloud dependency surface.
4. Confirm the HA admin account (owner account) has a strong password. HA does not natively support MFA via TOTP for local accounts by default — check if the TOTP multi-factor auth module is enabled under your profile.
5. If TOTP MFA is not enabled on the HA admin account, enable it:
   - Profile > Multi-factor Authentication Modules > Enable TOTP.
6. Document final state.

**Done when:** HA admin account has MFA enabled and no unintended external URL is configured.

**Findings (2026-06-20):** PARTIAL. External URL: not configured (correct — Nabu Casa provides the external URL). Nabu Casa active (account `joscthomas@gmail.com`). HA MFA: NOT ENABLED — checked `.storage/auth`; `Joseph Thomas` and `robin` both have `mfa_modules: none`. Action required: Joseph must enable TOTP manually — HA profile → Multi-Factor Authentication Modules → Enable TOTP → scan QR code with authenticator app. Do for both the owner account and Robin's account.

**Update (2026-07-09):** DONE. TOTP MFA enabled for both accounts (Joseph and Robin) via HA profile → Multi-Factor Authentication Modules. Step 7 complete.

---

## Step 8 — Audit Node-RED authentication

**Risk:** Node-RED by default runs with no authentication. Anyone on the LAN (or Tailscale network) can access the flow editor and modify automation logic or read MQTT payloads.

**Actions:**
1. Check the Node-RED settings file (typically `~/.node-red/settings.js` on the Pi).
2. Look for the `adminAuth` block. If it is commented out or absent, Node-RED has no login.
3. If `adminAuth` is absent, add a bcrypt-hashed admin credential:
   ```bash
   node-red-admin hash-pw
   ```
   Then add the `adminAuth` block to `settings.js` with the generated hash. Restart Node-RED:
   ```bash
   sudo systemctl restart nodered
   ```
4. Confirm the Node-RED editor requires login after the restart.
5. Document the change.

**Done when:** Node-RED requires a username and password to access the editor.

**Findings (2026-06-20):** PASS. `adminAuth` block present in `/home/pi/.node-red/settings.js` with bcrypt-hashed password for `admin` user. No action needed.

---

## Step 9 — Audit Ring / Amazon account security

**Risk:** Ring cameras cover the full perimeter of the property. A compromised Ring or Amazon account exposes live and recorded video and enables motion detection manipulation. Amazon accounts are also a high-value credential-theft target due to payment data.

**Note:** This step is manual. Claude Code will display instructions; Joseph executes in a browser or the Ring/Amazon app.

**Actions:**
1. **Amazon account MFA:**
   - Go to https://www.amazon.com/account and navigate to Login & Security.
   - Confirm Two-Step Verification (2SV) is enabled. If not, enable it using an authenticator app (preferred over SMS).
2. **Ring account MFA:**
   - Ring accounts are Amazon accounts — MFA set in Step 9.1 covers Ring login.
   - Open the Ring app > Account > Two-Factor Authentication and confirm it is enabled.
3. **Authorized users audit:**
   - In the Ring app, go to Account > Shared Users.
   - Review all shared users. Remove any that are no longer needed.
4. **OAuth / third-party app audit:**
   - Go to https://www.amazon.com/ap/adam and review all apps with access to your Amazon account.
   - Revoke access for any app you do not recognize or no longer use.
5. **Ring devices firmware:**
   - In the Ring app, check each device for firmware update status (Device Health > Firmware). Ring updates automatically, but confirm no device is stuck on an old version.
6. Document findings.

**Done when:** Amazon/Ring MFA confirmed enabled, shared users reviewed, OAuth apps audited.

**Findings (2026-06-20):** PASS. Amazon 2SV enabled. Ring MFA enabled with authenticator app. Shared users reviewed at device level — all expected. Amazon OAuth apps reviewed — clean. Ring firmware: option not present in current app version; Ring manages firmware automatically, no manual action available or needed.

---

## Step 10 — Audit SmartThings / Samsung account security

**Risk:** SmartThings is the central integration hub for Zigbee/Z-Wave switches, plug adapters, door sensors, garage door opener, and Google Home. A compromised Samsung account gives an attacker control of locks, lights, and sensors across the home.

**Note:** This step is manual. Claude Code will display instructions; Joseph executes in a browser or the SmartThings app.

**Actions:**
1. **Samsung account MFA:**
   - Go to https://account.samsung.com and navigate to Security > Two-Step Verification.
   - Confirm 2SV is enabled. Enable it with an authenticator app if not already active.
2. **SmartThings connected apps audit:**
   - Open the SmartThings app > Menu > Connected Services.
   - Review all connected services and OAuth integrations. Remove any not actively in use.
3. **Personal Access Token (PAT) audit:**
   - PATs are used by Node-RED for SmartThings integration. Per JCTsh architecture, PATs expire in 24 hours and are not used for persistent connections — confirm no long-lived PATs have been created.
   - Go to https://account.smartthings.com/tokens and review the token list. Revoke any unexpected or stale tokens.
4. **SmartThings app authorized users:**
   - In the SmartThings app, check for any guest or shared users under Settings > Manage Members. Remove any that are no longer needed.
5. Document findings.

**Done when:** Samsung MFA confirmed, connected apps reviewed, PAT list audited.

**Findings (2026-06-20):** PASS with one remediation. Samsung account 2SV enabled. Connected services: Google, Home Assistant, Ring, Ecobee — all expected. SharpTools was present but unrecognized — revoked. No Personal Access Tokens present. Members: only expected users.

---

## Step 11 — Audit Google account security (Google Home, Nest, Chromecast, Pixel)

**Risk:** The Google account underpins Google Home devices (garage, master bedroom, gathering room, back porch), Nest display (master bath), Chromecast, Google TV, and both Pixel phones. A single compromised Google account grants access to all of these, plus location history, photos, and Gmail.

**Note:** This step is manual. Claude Code will display instructions; Joseph executes on a Pixel or at myaccount.google.com. Covers both Joseph's account (Pixel 10 Pro XL) and Robin's account (Pixel 7).

**Actions — for each Google account (Joseph and Robin):**
1. **MFA status:**
   - Go to https://myaccount.google.com/security.
   - Confirm 2-Step Verification is enabled. Preferred method: Google Prompt or a hardware security key. SMS is acceptable but weaker.
2. **Passkeys audit:**
   - Under Security > How you sign in to Google, review enrolled passkeys and security keys. Remove any device you no longer own.
3. **Third-party app access (OAuth audit):**
   - Go to https://myaccount.google.com/permissions.
   - Review all apps with access to the Google account. This is the primary OAuth abuse vector used in attacks like Midnight Blizzard.
   - Revoke access for any app not actively in use, especially any with broad scopes (e.g., "See and edit all your files").
4. **Recent security activity:**
   - Under Security > Recent security activity, check for any unfamiliar sign-ins or events. Report any anomalies.
5. **Google Home device audit:**
   - In the Google Home app, go to Settings > Home Members. Review who has access to the home and remove any accounts no longer needed.
6. Document findings for both accounts.

**Done when:** MFA confirmed on both Google accounts, OAuth apps audited, Home Members reviewed.

**Findings (2026-06-20):** PASS — both accounts. Joseph: 2-Step Verification enabled with authenticator app, passkeys/devices clean, OAuth apps clean, no unfamiliar security activity, Home Members clean. Robin: all checks clean.

---

## Step 12 — Audit Ecobee account security

**Risk:** The Ecobee thermostat controls HVAC. A compromised Ecobee account enables physical discomfort (temperature manipulation) and reveals occupancy patterns (home/away detection data).

**Note:** This step is manual. Claude Code will display instructions; Joseph executes at ecobee.com or in the Ecobee app.

**Actions:**
1. **Ecobee account MFA:**
   - Go to https://www.ecobee.com and sign in.
   - Navigate to Account > Security.
   - Confirm Two-Factor Authentication is enabled. Enable it with an authenticator app if not active.
2. **Connected apps audit:**
   - Under Account > Apps, review any third-party integrations (e.g., SmartThings, Google Home, Amazon Alexa).
   - Revoke access for any integration not actively in use.
3. **Access list:**
   - If any additional users have been granted access to the thermostat, review and remove any that are no longer needed.
4. Document findings.

**Done when:** Ecobee MFA confirmed and connected apps reviewed.

**Findings (2026-06-20):** PASS. Ecobee MFA enabled. Connected apps: Google and SmartThings — both expected. No unexpected users.

---

## Step 13 — Audit router firmware and admin credentials

**Risk:** An outdated router firmware may contain known vulnerabilities. A default or weak router admin password is the single most common way home routers are recruited into residential proxy networks. The router is the gateway for every JCTsh device.

**Note:** Router admin access is required. Claude Code will display instructions; Joseph executes in the router admin interface.

**Actions:**
1. **Admin password:**
   - Log into the router admin interface.
   - Navigate to Administration > Admin Password (location varies by router brand).
   - If the admin password is the factory default or a simple password, change it to a strong unique password (16+ characters). Store it in a password manager.
2. **Firmware version:**
   - Navigate to Administration > Firmware Update (or equivalent).
   - Note the current firmware version and check for available updates.
   - If an update is available, apply it. Most home routers require a manual trigger.
   - After update, confirm the router reboots cleanly and all JCTsh devices reconnect.
3. **Remote management:**
   - Confirm remote management / WAN-side admin access is disabled. This setting (sometimes called "Remote Access" or "Web Access from WAN") should always be OFF for a home router.
4. **DNS settings:**
   - Note the configured DNS servers. If they are the ISP defaults, that is acceptable. Flag any unknown third-party DNS entries — they can indicate router compromise (DNS hijacking).
5. Document firmware version, admin password change (confirm only, not the password itself), and remote management state.

**Done when:** Firmware is current, admin password is strong and unique, remote management is disabled.

**Findings (2026-06-20):** DEFERRED — requires home WiFi access to router admin at `192.168.1.1`. Complete when next on home network alongside Step 6 (UPnP).

**Update (2026-07-09):** DONE. Admin password rotated to a new strong unique password (stored in `credentials.local.md`, not reproduced here). Remote management/WAN-side admin access confirmed disabled. DNS confirmed configured for CenturyLink/Quantum Fiber bypass-modem setup — no unexpected third-party entries. Firmware: hardware Archer AXE75 v1.0, running 1.5.2 Build 20260113 rel.53105(5553), latest available is 1.5.3 Build 20260209 rel.71108 — one version behind. Auto-update enabled, scheduled nightly 3–5 AM, which will pick up 1.5.3 tonight; ongoing firmware currency now handled automatically rather than requiring a manual periodic check. Step 13 complete.

---

## Step 14 — Audit Windows development machine security

**Risk:** Joseph's Windows machine (VS Code, PowerShell, Git, Claude Code) holds the JCTsh monorepo, ESPHome secrets, and SSH keys. A compromised Windows machine is equivalent to compromising the Pi.

**Note:** This step is partially automatable via PowerShell. Claude Code will execute the audit commands and display results for Joseph's review.

**Actions:**
1. **Windows Update status:**
   ```powershell
   Get-WindowsUpdateLog
   (New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher().Search("IsInstalled=0").Updates | Select-Object Title
   ```
   Report any pending updates. Critical and security updates should be applied promptly.
2. **SSH key file permissions:**
   - Locate the private key used for Pi access (typically `~/.ssh/id_rsa` or `~/.ssh/id_ed25519`).
   - Confirm permissions restrict access to Joseph's user account only:
     ```powershell
     icacls "$env:USERPROFILE\.ssh\id_ed25519"
     ```
   - If any group other than the owner has access, tighten permissions:
     ```powershell
     icacls "$env:USERPROFILE\.ssh\id_ed25519" /inheritance:r /grant:r "$env:USERNAME:(R)"
     ```
3. **Microsoft account MFA (Windows login):**
   - If the Windows machine uses a Microsoft account login, confirm MFA is enabled at https://account.microsoft.com/security.
   - Report status — cannot automate this check.
4. **Installed browser extensions:**
   - Malicious browser extensions are a common credential-theft vector.
   - In Chrome/Edge, navigate to the Extensions page and review installed extensions. Report any unfamiliar entries for Joseph's review.
5. Document findings.

**Done when:** Windows is fully patched, SSH key permissions are correct, and Microsoft account MFA is confirmed.

**Findings (2026-06-20):** PASS with one fix. Windows Update: no pending updates. SSH key (`id_ed25519`): FIXED — `BUILTIN\Administrators` and `NT AUTHORITY\SYSTEM` had full access; removed; now `DESKTOP-FQBDL5B\jcthomas:(R)` only. SSH confirmed still working after permission change. Microsoft account MFA: enabled. Browser extensions: clean.

---

## Final Step — Harvest to JCTsh-Build-Standards.md

After all steps are complete:
1. Review all findings and any new patterns discovered.
2. Add a **Security** section to `JCTsh-Build-Standards.md` if one does not exist, capturing:
   - SSH key-only requirement for the Pi
   - MQTT authentication requirement
   - `secrets.yaml` must always be in `.gitignore`
   - Node-RED `adminAuth` requirement
   - UPnP policy decision (enabled/disabled and rationale)
   - Tailscale as the sole remote access path (no direct port forwarding)
   - MFA required on all cloud accounts: Google, Amazon/Ring, Samsung, Ecobee, Microsoft
   - Router firmware currency and admin credential policy
   - SSH private key Windows permission requirement
3. Commit all changes to the repo with the message: `security: hardening audit and remediation`.

---

## Summary Table

| Step | Area | Risk Level | Effort | Automated? |
|------|------|-----------|--------|------------|
| 1 | secrets.yaml git exclusion | Critical | Low | Yes |
| 2 | Pi SSH password auth | Critical | Low | Yes |
| 3 | Pi open ports / port forwarding | High | Low | Yes |
| 4 | MQTT broker authentication | High | Medium | Yes |
| 5 | Tailscale MFA and ACL | High | Low | Partial |
| 6 | Router UPnP | Medium | Low | Manual |
| 7 | Home Assistant MFA | Medium | Low | Partial |
| 8 | Node-RED authentication | Medium | Low | Yes |
| 9 | Ring / Amazon account | High | Low | Manual |
| 10 | SmartThings / Samsung account | High | Low | Manual |
| 11 | Google accounts (Joseph + Robin) | High | Low | Manual |
| 12 | Ecobee account | Medium | Low | Manual |
| 13 | Router firmware and admin credentials | High | Low | Manual |
| 14 | Windows machine security | High | Medium | Partial |
| Final | Build Standards harvest | — | Low | Yes |
