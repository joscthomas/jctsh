// Home Assistant integration layer for photo-tv-display.
//
// Confirmed live against the real HA instance before this file was written:
// `media_player.groom_tv` ("GRoom TV") exists via the Cast integration and
// currently reports state "off" (no photo currently casting). See
// photo-tv-display-claude-code-instructions.md Step 4.2 -- the *idle*-vs-
// *playing*-vs-*off* state vocabulary this TV actually reports once
// something is cast to it is still unconfirmed; IDLE_STATES below is a
// documented starting guess (the doc's own suggestion), not an observed
// fact. Correct it once Joseph reports real values from Step 11 live
// testing -- do not treat this as finished.

const HA_URL = process.env.HA_SERVER_URL;
const HA_TOKEN = process.env.HA_LONG_LIVED_TOKEN;
const TV_ENTITY_ID = process.env.HA_TV_ENTITY_ID;

async function haFetch(path, { method = 'GET', body } = {}) {
  const res = await fetch(`${HA_URL}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${HA_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HA ${method} ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

async function startSlideshow(port) {
  return haFetch('/api/services/media_player/play_media', {
    method: 'POST',
    body: {
      entity_id: TV_ENTITY_ID,
      media_content_id: `http://photo-server.local:${port}/tv`,
      media_content_type: 'url',
    },
  });
}

async function getTvState() {
  return haFetch(`/api/states/${TV_ENTITY_ID}`);
}

// UNCONFIRMED -- placeholder pending Step 11 live observation (see file header).
const IDLE_STATES = ['idle', 'off', 'paused'];

// Polls HA every POLL_INTERVAL_MS, tracks how long the TV has continuously
// reported an idle-equivalent state, and calls onIdleThresholdReached() once
// idleTimeoutSec (runtime-configurable from the phone controller, per Phase 1
// spec) is exceeded. Node.js owns this timing (rather than an HA-native
// automation) specifically because the phone controller can change the idle
// timeout at runtime without editing an HA automation -- the instructions
// doc's own reasoning for preferring this path.
function startIdlePoller({ port, getIdleTimeoutSec, onIdleThresholdReached, pollIntervalMs = 60_000 }) {
  let idleSinceMs = null;
  let firedForThisIdlePeriod = false;

  const tick = async () => {
    try {
      const state = await getTvState();
      const isIdle = IDLE_STATES.includes(state.state);

      if (!isIdle) {
        idleSinceMs = null;
        firedForThisIdlePeriod = false;
        return;
      }

      if (idleSinceMs === null) idleSinceMs = Date.now();

      const idleTimeoutSec = getIdleTimeoutSec();
      if (idleTimeoutSec === null) return; // auto-start disabled

      const idleForSec = (Date.now() - idleSinceMs) / 1000;
      if (idleForSec >= idleTimeoutSec && !firedForThisIdlePeriod) {
        firedForThisIdlePeriod = true;
        await startSlideshow(port);
        onIdleThresholdReached();
      }
    } catch (err) {
      console.error('Idle poll failed:', err.message);
    }
  };

  const timer = setInterval(tick, pollIntervalMs);
  return () => clearInterval(timer);
}

module.exports = { startSlideshow, getTvState, startIdlePoller, IDLE_STATES };
