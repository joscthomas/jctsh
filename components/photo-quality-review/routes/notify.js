// CARD-0028: push a notification to Joseph's Pixel via Home Assistant's
// companion-app notify service, so a long-running scan.js run doesn't need
// an attended SSH session to know when it's done. Same pattern already
// built this session for hike-izer-orchestrator's ha_notify.py -- best-
// effort, log-and-continue, never lets a notification failure break the
// caller.

async function sendPush(title, message) {
  const haUrl = process.env.HA_URL;
  const haToken = process.env.HA_TOKEN;
  if (!haUrl || !haToken) {
    console.error(`[notify] HA_URL/HA_TOKEN not set -- skipping push: ${message}`);
    return;
  }
  try {
    const res = await fetch(`${haUrl}/api/services/notify/mobile_app_pixel_10_pro_xl`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${haToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title, message }),
    });
    if (!res.ok) console.error(`[notify] push failed: ${res.status}`);
  } catch (err) {
    console.error(`[notify] push failed: ${err.message}`);
  }
}

module.exports = { sendPush };
