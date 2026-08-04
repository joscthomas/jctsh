require('dotenv').config();

const express = require('express');
const http = require('http');
const { WebSocketServer } = require('ws');

const immich = require('./routes/immich');
const ha = require('./routes/homeassistant');
const deletionLog = require('./routes/deletion-log');

const PORT = Number(process.env.PORT) || 3000;

// ---------------------------------------------------------------------------
// Authoritative server-side state. Pool entries are deliberately lightweight
// ({id, ownerLabel} only, not full asset objects) -- keeps WebSocket state
// broadcasts small regardless of pool size. Clients fetch full metadata for
// the *current* asset only, via REST, as they display it.
// ---------------------------------------------------------------------------
const state = {
  filter: { mode: 'random' },
  settings: {
    displayDurationSec: 10,
    transition: 'crossfade', // crossfade | kenburns | cut | fadeblack
    metadataFields: { date: true, location: true, people: true, folder: false, owner: true, description: false },
    metadataBehavior: 'fadeInOut', // always | fadeInOut | onDemand
    deleteConfirm: true,
    idleTimeoutSec: 300, // null = auto-start disabled
  },
  pool: [], // [{ id, ownerLabel }]
  index: 0,
};

async function reloadPool(filter) {
  const assets = await immich.getPhotosByFilter(filter);
  state.filter = filter;
  state.pool = assets.map((a) => ({ id: a.id, ownerLabel: a.ownerLabel }));
  state.index = 0;
}

function currentAsset() {
  return state.pool[state.index] || null;
}

// ---------------------------------------------------------------------------
// Express app
// ---------------------------------------------------------------------------
const app = express();
app.use(express.json());
app.use('/public', express.static(__dirname + '/public'));

app.get('/tv', (req, res) => res.sendFile(__dirname + '/public/tv.html'));
app.get('/controller', (req, res) => res.sendFile(__dirname + '/public/controller.html'));

// Image proxy -- browsers can't attach x-api-key to <img src>, so the server
// fetches with the owning account's key and streams the response through.
app.get('/photo/:ownerLabel/:id/:variant', async (req, res) => {
  try {
    const upstream = await immich.getAssetImageResponse(req.params.id, req.params.ownerLabel, req.params.variant);
    res.set('Content-Type', upstream.headers.get('content-type') || 'image/jpeg');
    const buf = Buffer.from(await upstream.arrayBuffer());
    res.send(buf);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

app.get('/api/albums', async (req, res) => {
  try {
    res.json(await immich.getAlbums(req.query.owner, req.query.assetId));
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

app.get('/api/people', async (req, res) => {
  try {
    res.json(await immich.getPeople(req.query.owner));
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

app.get('/api/asset/:ownerLabel/:id', async (req, res) => {
  try {
    const asset = await immich.getAssetMetadata(req.params.id, req.params.ownerLabel);
    const exif = asset.exifInfo || {};
    // Album membership doubles as the "folder / album name" metadata field --
    // Immich has no separate filesystem-folder concept to surface instead.
    const albums = await immich.getAlbums(req.params.ownerLabel, req.params.id).catch(() => []);
    res.json({
      ...asset,
      locationLabel: immich.formatLocation(exif.city, exif.state, exif.country),
      albumNames: albums.map((a) => a.albumName),
    });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

app.post('/api/start-slideshow', async (req, res) => {
  try {
    await ha.startSlideshow(PORT);
    res.json({ status: 'ok' });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

const server = http.createServer(app);

// ---------------------------------------------------------------------------
// WebSocket -- state sync between TV view and any connected phone controller(s).
// Last-write-wins: every handled message ends by broadcasting the new
// authoritative state to all clients, including the sender.
// ---------------------------------------------------------------------------
const wss = new WebSocketServer({ server });

function publicState() {
  return { type: 'state', filter: state.filter, settings: state.settings, pool: state.pool, index: state.index };
}

function broadcast(msg) {
  const data = JSON.stringify(msg);
  for (const client of wss.clients) {
    if (client.readyState === client.OPEN) client.send(data);
  }
}

wss.on('connection', (ws) => {
  ws.send(JSON.stringify(publicState()));

  ws.on('message', async (raw) => {
    let msg;
    try {
      msg = JSON.parse(raw);
    } catch {
      return;
    }

    try {
      // Ephemeral, not part of persisted state -- e.g. "on demand" metadata
      // reveal from the phone controller. Relayed as-is, no state broadcast.
      if (msg.type === 'flashMetadata') {
        broadcast({ type: 'flashMetadata' });
        return;
      }

      switch (msg.type) {
        case 'nav': {
          if (state.pool.length === 0) break;
          const delta = msg.direction === 'prev' ? -1 : 1;
          state.index = (state.index + delta + state.pool.length) % state.pool.length;
          break;
        }

        case 'setFilter': {
          await reloadPool(msg.filter);
          break;
        }

        case 'setSettings': {
          state.settings = { ...state.settings, ...msg.settings };
          break;
        }

        case 'favorite': {
          const asset = currentAsset();
          if (!asset) break;
          await immich.toggleFavorite(asset.id, msg.value, asset.ownerLabel);
          break;
        }

        case 'delete': {
          const asset = currentAsset();
          if (!asset) break;
          const meta = await immich.getAssetMetadata(asset.id, asset.ownerLabel);
          await immich.deleteAsset(asset.id, asset.ownerLabel);
          await deletionLog.logDeletion(meta, msg.albumFolder, msg.actingUser);
          // Remove from the live pool so the slideshow doesn't try to show it again.
          state.pool.splice(state.index, 1);
          if (state.index >= state.pool.length) state.index = 0;
          break;
        }

        case 'addToAlbum': {
          const asset = currentAsset();
          if (!asset) break;
          await immich.addToAlbum(asset.id, msg.albumId, asset.ownerLabel);
          break;
        }

        case 'createAlbum': {
          const asset = currentAsset();
          if (!asset) break;
          await immich.createAlbum(msg.albumName, asset.id, asset.ownerLabel);
          break;
        }

        case 'startSlideshow': {
          await ha.startSlideshow(PORT);
          break;
        }

        default:
          return; // unknown message type -- no state change, no broadcast
      }

      broadcast(publicState());
    } catch (err) {
      ws.send(JSON.stringify({ type: 'error', message: err.message }));
    }
  });
});

// Idle auto-start polling (see routes/homeassistant.js for the IDLE_STATES caveat).
ha.startIdlePoller({
  port: PORT,
  getIdleTimeoutSec: () => state.settings.idleTimeoutSec,
  onIdleThresholdReached: () => console.log('Idle threshold reached -- slideshow auto-started.'),
});

async function start() {
  await immich.resolveOwners();
  await reloadPool(state.filter);
  server.listen(PORT, () => console.log(`photo-tv-display listening on :${PORT}`));
}

start().catch((err) => {
  console.error('Fatal startup error:', err);
  process.exit(1);
});
