# eRVin Lexor FL Configuration File — Pleasure-Way Firefly Interface

Install the Pleasure-Way Lexor FL configuration file so eRVin maps Firefly RV-C device IDs to named coach entities.

---

## What the Configuration File Does

The configuration file maps Firefly RV-C device IDs to named entities specific to the Lexor FL layout — tank sensors, light circuits, awning, generator, water pump, inverter, and other coach systems. Without it, eRVin can receive RV-C data but cannot label it meaningfully.

---

## Step 1 — Access the eRVin Dashboard

Open Chrome on a Pixel or browser on a PC connected to the home network. Navigate to:

```
http://192.168.1.219
```

If the dashboard does not load on port 80, try:

```
http://192.168.1.219:1880
```

The Node-RED admin UI is at port 1880 (credentials: admin / see secrets.md).

---

## Step 2 — Locate the Pleasure-Way Lexor FL Configuration File

**Check the myervin.com community first** — a fellow Pleasure-Way owner (2017 Lexor TS, same coach architecture) posted a Pleasure-Way configuration file to the myervin.com community. See [bclass.org/automating-lexi/](https://bclass.org/automating-lexi/) for context. This file may work directly or require minor adjustments for the 2018 Lexor FL.

1. Go to **myervin.com** and check the community/downloads section for a Pleasure-Way Lexor configuration file
2. If a community-contributed Pleasure-Way file is available, download it
3. If not, download the generic eRVin configuration file and note that entity names may need manual adjustment after RV-C connectivity is established in Step 11

---

## Step 3 — Install the Configuration File

1. In the eRVin dashboard, navigate to the configuration or setup section
2. Locate the option to upload or install a configuration file
3. Select the downloaded Pleasure-Way Lexor FL configuration file
4. Confirm the installation

---

## Step 4 — Verify

After installation, named entities should appear in the dashboard — tank levels, battery, light circuits, etc. Confirm at least some entities are labeled. Note that live data will not appear until CAN bus connectivity is established in Step 11.

---

## Troubleshooting — Missing Node Types

After installing the configuration file, the dashboard at port 80 may show "Welcome to Node-RED Dashboard — Please add some UI nodes to your flow and redeploy." This happens because the Pleasure-Way config flows depend on two Node-RED packages that are not bundled with eRVin:

- `node-red-contrib-owntracks`
- `node-red-contrib-webhookrelay`

Install them via SSH:

```
cd ~/.node-red && npm install node-red-contrib-owntracks node-red-contrib-webhookrelay
```

Then restart Node-RED (service name on eRVin is `nodered`, not `node-red`):

```
sudo systemctl restart nodered
```

Reload the editor at port 1880 — missing node warnings should be gone and flows should show as running.

---

## Confirmed Details

*(Step 7 confirmed complete — May 2026)*

| Item | Value |
|---|---|
| Configuration file source | myervin.com community (Pleasure-Way Lexor) |
| Configuration file version/date | TBD |
| Named entities visible in dashboard | Yes — dashboard shows coach systems after missing node fix |
| Missing nodes installed | node-red-contrib-owntracks, node-red-contrib-webhookrelay |
| Node-RED service name on eRVin | `nodered` (not `node-red`) |
