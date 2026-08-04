(() => {
  const layerA = document.getElementById('layerA');
  const layerB = document.getElementById('layerB');
  const overlay = document.getElementById('overlay');
  const stage = document.getElementById('stage');

  let activeLayer = layerA;
  let inactiveLayer = layerB;

  let state = null; // last known server state: { filter, settings, pool, index }
  let shownAssetKey = null; // `${ownerLabel}:${id}` of what's currently on screen
  let advanceTimer = null;
  let overlayHideTimer = null;

  // ---- WebSocket, with basic manual reconnect ------------------------------
  // ws itself does not reconnect automatically (documented risk in the Phase 2
  // planning doc) -- this is a minimal retry loop, not the Socket.IO fallback
  // that doc names as the real fix if this proves unreliable on real WiFi.
  let ws;
  function connect() {
    ws = new WebSocket(location.origin.replace(/^http/, 'ws'));
    ws.onmessage = onMessage;
    ws.onclose = () => setTimeout(connect, 3000);
    ws.onerror = () => ws.close();
  }
  connect();

  function onMessage(evt) {
    const msg = JSON.parse(evt.data);
    if (msg.type === 'state') {
      state = msg;
      maybeShowCurrentAsset();
    } else if (msg.type === 'flashMetadata') {
      revealOverlay(true);
    }
  }

  function currentPoolEntry() {
    if (!state || state.pool.length === 0) return null;
    return state.pool[state.index];
  }

  async function maybeShowCurrentAsset() {
    const entry = currentPoolEntry();
    if (!entry) return;
    const key = `${entry.ownerLabel}:${entry.id}`;
    if (key === shownAssetKey) return; // nothing to do, already showing this one
    shownAssetKey = key;
    await showAsset(entry);
  }

  async function showAsset(entry) {
    const [meta] = await Promise.all([
      fetch(`/api/asset/${entry.ownerLabel}/${entry.id}`).then((r) => r.json()),
    ]);

    const imgUrl = `/photo/${entry.ownerLabel}/${entry.id}/thumbnail`;
    await preload(imgUrl);

    const transition = state.settings.transition;
    if (transition === 'fadeblack') {
      await fadeOut(activeLayer);
    }

    const nextLayer = transition === 'fadeblack' ? activeLayer : inactiveLayer;
    nextLayer.src = imgUrl;
    nextLayer.classList.remove('kenburns');
    void nextLayer.offsetWidth; // restart animation if reapplied
    if (transition === 'kenburns') {
      nextLayer.style.animationDuration = `${state.settings.displayDurationSec + 1}s`;
      nextLayer.classList.add('kenburns');
    }

    stage.classList.toggle('cut', transition === 'cut');

    if (transition !== 'fadeblack') {
      activeLayer.classList.remove('visible');
      nextLayer.classList.add('visible');
      activeLayer = nextLayer;
      inactiveLayer = activeLayer === layerA ? layerB : layerA;
    } else {
      activeLayer.classList.add('visible');
    }

    updateOverlay(meta);
    restartAdvanceTimer();
  }

  function preload(url) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = resolve;
      img.onerror = reject;
      img.src = url;
    });
  }

  function fadeOut(layer) {
    return new Promise((resolve) => {
      layer.classList.remove('visible');
      setTimeout(resolve, 1200); // matches .photo-layer transition duration
    });
  }

  function restartAdvanceTimer() {
    clearTimeout(advanceTimer);
    const sec = state.settings.displayDurationSec || 10;
    advanceTimer = setTimeout(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'nav', direction: 'next' }));
    }, sec * 1000);
  }

  // ---- Metadata overlay ------------------------------------------------
  function buildOverlayText(meta) {
    const f = state.settings.metadataFields;
    const lines = [];
    if (f.date && meta.fileCreatedAt) {
      lines.push(new Date(meta.fileCreatedAt).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }));
    }
    if (f.location && meta.locationLabel) lines.push(meta.locationLabel);
    if (f.people && meta.people && meta.people.length) lines.push(meta.people.map((p) => p.name).filter(Boolean).join(', '));
    if (f.folder && meta.albumNames && meta.albumNames.length) lines.push(meta.albumNames.join(', '));
    if (f.owner && meta.ownerLabel) lines.push(meta.ownerLabel === 'joseph' ? "Joseph's photo" : meta.ownerLabel === 'robin' ? "Robin's photo" : '');
    if (f.description && meta.exifInfo && meta.exifInfo.description) lines.push(meta.exifInfo.description);
    return lines.filter(Boolean);
  }

  function updateOverlay(meta) {
    const lines = buildOverlayText(meta);
    overlay.innerHTML = lines.map((l) => `<div class="row">${escapeHtml(l)}</div>`).join('');

    clearTimeout(overlayHideTimer);
    const behavior = state.settings.metadataBehavior;
    if (behavior === 'always') {
      revealOverlay(false);
    } else if (behavior === 'fadeInOut') {
      revealOverlay(false);
      overlayHideTimer = setTimeout(() => overlay.classList.remove('visible'), 4000);
    } else {
      overlay.classList.remove('visible'); // onDemand -- hidden until flashMetadata
    }
  }

  function revealOverlay(autoHide) {
    overlay.classList.add('visible');
    if (autoHide) {
      clearTimeout(overlayHideTimer);
      overlayHideTimer = setTimeout(() => overlay.classList.remove('visible'), 4000);
    }
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
})();
