(() => {
  // ---- Who is using this phone? (for deletion-log attribution only --
  // Phase 1 spec is explicit both users have full, equal, unrestricted access) --
  let whoAmI = localStorage.getItem('ptd_whoami');
  if (whoAmI !== 'joseph' && whoAmI !== 'robin') {
    whoAmI = (prompt("Who's using this phone? Type 'joseph' or 'robin'.") || '').trim().toLowerCase();
    if (whoAmI !== 'joseph' && whoAmI !== 'robin') whoAmI = 'joseph';
    localStorage.setItem('ptd_whoami', whoAmI);
  }
  document.getElementById('whoami').textContent = `Signed in as ${whoAmI === 'joseph' ? 'Joseph' : 'Robin'}`;

  let state = null;
  let currentMeta = null; // full metadata for the currently displayed asset

  // ---- WebSocket, same manual-reconnect pattern as tv.js ----------------
  let ws;
  function connect() {
    ws = new WebSocket(location.origin.replace(/^http/, 'ws'));
    ws.onmessage = onMessage;
    ws.onclose = () => setTimeout(connect, 3000);
    ws.onerror = () => ws.close();
  }
  connect();

  function send(msg) {
    if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
  }

  async function onMessage(evt) {
    const msg = JSON.parse(evt.data);
    if (msg.type !== 'state') return;
    state = msg;
    reflectSettings();
    await reflectCurrentAsset();
  }

  async function reflectCurrentAsset() {
    const entry = state.pool[state.index];
    if (!entry) {
      document.getElementById('preview').removeAttribute('src');
      document.getElementById('caption').textContent = 'No photos match the current filter.';
      currentMeta = null;
      return;
    }
    currentMeta = await fetch(`/api/asset/${entry.ownerLabel}/${entry.id}`).then((r) => r.json());
    document.getElementById('preview').src = `/photo/${entry.ownerLabel}/${entry.id}/thumbnail`;
    document.getElementById('caption').textContent =
      [currentMeta.originalFileName, currentMeta.locationLabel].filter(Boolean).join(' — ');
    document.getElementById('btnFavorite').textContent = currentMeta.isFavorite ? '★ Favorited' : '☆ Favorite';
    document.getElementById('btnFavorite').classList.toggle('toggled', !!currentMeta.isFavorite);
  }

  function reflectSettings() {
    const s = state.settings;
    document.getElementById('setDuration').value = s.displayDurationSec;
    document.getElementById('setTransition').value = s.transition;
    document.getElementById('mfDate').checked = s.metadataFields.date;
    document.getElementById('mfLocation').checked = s.metadataFields.location;
    document.getElementById('mfPeople').checked = s.metadataFields.people;
    document.getElementById('mfFolder').checked = s.metadataFields.folder;
    document.getElementById('mfOwner').checked = s.metadataFields.owner;
    document.getElementById('mfDescription').checked = s.metadataFields.description;
    document.getElementById('setMetaBehavior').value = s.metadataBehavior;
    document.getElementById('onDemandRow').style.display = s.metadataBehavior === 'onDemand' ? 'flex' : 'none';
    document.getElementById('setDeleteConfirm').checked = s.deleteConfirm;
    document.getElementById('setIdleTimeout').value = s.idleTimeoutSec === null ? 0 : s.idleTimeoutSec;
  }

  // ---- Nav / start -------------------------------------------------------
  document.getElementById('btnPrev').onclick = () => send({ type: 'nav', direction: 'prev' });
  document.getElementById('btnNext').onclick = () => send({ type: 'nav', direction: 'next' });
  document.getElementById('btnStart').onclick = () => send({ type: 'startSlideshow' });

  // ---- Actions -------------------------------------------------------
  document.getElementById('btnFavorite').onclick = () => {
    if (!currentMeta) return;
    send({ type: 'favorite', value: !currentMeta.isFavorite });
  };

  document.getElementById('btnDelete').onclick = async () => {
    if (!currentMeta) return;
    if (state.settings.deleteConfirm && !confirm(`Delete "${currentMeta.originalFileName}"? This moves it to Immich's trash.`)) return;

    const entry = state.pool[state.index];
    const albums = await fetch(`/api/albums?owner=${entry.ownerLabel}&assetId=${entry.id}`).then((r) => r.json());
    const albumFolder = albums.map((a) => a.albumName).join(', ');

    send({ type: 'delete', albumFolder, actingUser: whoAmI });
  };

  document.getElementById('btnAddAlbum').onclick = async () => {
    if (!currentMeta) return;
    const entry = state.pool[state.index];
    const albums = await fetch(`/api/albums?owner=${entry.ownerLabel}`).then((r) => r.json());
    if (albums.length === 0) return alert('No existing albums for this photo\'s account yet.');
    const names = albums.map((a, i) => `${i + 1}. ${a.albumName}`).join('\n');
    const choice = prompt(`Add to which album?\n${names}\n\nEnter a number:`);
    const idx = Number(choice) - 1;
    if (!albums[idx]) return;
    send({ type: 'addToAlbum', albumId: albums[idx].id });
  };

  document.getElementById('btnNewAlbum').onclick = () => {
    if (!currentMeta) return;
    const name = prompt('New album name:');
    if (!name) return;
    send({ type: 'createAlbum', albumName: name });
  };

  document.getElementById('btnFlashMetadata').onclick = () => send({ type: 'flashMetadata' });

  // ---- Filter panel -------------------------------------------------------
  const filterModeEl = document.getElementById('filterMode');
  const filterExtraEl = document.getElementById('filterExtra');

  const FILTER_TEMPLATES = {
    random: () => '',
    favorites: () => '',
    onThisDay: () => '',
    owner: () => `
      <label><input type="radio" name="acct" value="joseph" checked> Joseph only</label><br>
      <label><input type="radio" name="acct" value="robin"> Robin only</label><br>
      <label><input type="radio" name="acct" value="both"> Both</label>`,
    concept: () => `<input type="text" id="fConcept" placeholder="e.g. hiking, birthday, sunset">`,
    location: () => `
      <input type="text" id="fCity" placeholder="City"><br><br>
      <input type="text" id="fState" placeholder="State"><br><br>
      <input type="text" id="fCountry" placeholder="Country (optional)">`,
    dateRange: () => `
      <input type="date" id="fStart"> to <input type="date" id="fEnd">`,
    person: () => `
      <label><input type="radio" name="pacct" value="joseph" checked> Joseph's library</label>
      <label><input type="radio" name="pacct" value="robin"> Robin's library</label><br><br>
      <select id="fPerson"></select>`,
    album: () => `
      <label><input type="radio" name="aacct" value="joseph" checked> Joseph's library</label>
      <label><input type="radio" name="aacct" value="robin"> Robin's library</label><br><br>
      <select id="fAlbum"></select>`,
  };

  async function renderFilterExtra() {
    const mode = filterModeEl.value;
    filterExtraEl.innerHTML = (FILTER_TEMPLATES[mode] || (() => ''))();

    if (mode === 'person') {
      const populate = async () => {
        const acct = document.querySelector('input[name="pacct"]:checked').value;
        const people = await fetch(`/api/people?owner=${acct}`).then((r) => r.json());
        document.getElementById('fPerson').innerHTML = people.map((p) => `<option value="${p.id}">${p.name || '(unnamed)'}</option>`).join('');
      };
      document.querySelectorAll('input[name="pacct"]').forEach((r) => (r.onchange = populate));
      await populate();
    }

    if (mode === 'album') {
      const populate = async () => {
        const acct = document.querySelector('input[name="aacct"]:checked').value;
        const albums = await fetch(`/api/albums?owner=${acct}`).then((r) => r.json());
        document.getElementById('fAlbum').innerHTML = albums.map((a) => `<option value="${a.id}">${a.albumName}</option>`).join('');
      };
      document.querySelectorAll('input[name="aacct"]').forEach((r) => (r.onchange = populate));
      await populate();
    }
  }
  filterModeEl.onchange = renderFilterExtra;
  renderFilterExtra();

  document.getElementById('btnApplyFilter').onclick = () => {
    const mode = filterModeEl.value;
    let filter = { mode };

    if (mode === 'owner') {
      const acct = document.querySelector('input[name="acct"]:checked').value;
      filter.accounts = acct === 'both' ? ['joseph', 'robin'] : [acct];
    } else if (mode === 'concept') {
      filter.query = document.getElementById('fConcept').value;
    } else if (mode === 'location') {
      filter.city = document.getElementById('fCity').value || undefined;
      filter.state = document.getElementById('fState').value || undefined;
      filter.country = document.getElementById('fCountry').value || undefined;
    } else if (mode === 'dateRange') {
      filter.start = document.getElementById('fStart').value ? new Date(document.getElementById('fStart').value).toISOString() : undefined;
      filter.end = document.getElementById('fEnd').value ? new Date(document.getElementById('fEnd').value + 'T23:59:59').toISOString() : undefined;
    } else if (mode === 'person') {
      filter.ownerLabel = document.querySelector('input[name="pacct"]:checked').value;
      filter.personId = document.getElementById('fPerson').value;
    } else if (mode === 'album') {
      filter.ownerLabel = document.querySelector('input[name="aacct"]:checked').value;
      filter.albumId = document.getElementById('fAlbum').value;
    }

    send({ type: 'setFilter', filter });
  };

  // ---- Settings panel -------------------------------------------------------
  document.getElementById('setMetaBehavior').onchange = (e) => {
    document.getElementById('onDemandRow').style.display = e.target.value === 'onDemand' ? 'flex' : 'none';
  };

  document.getElementById('btnApplySettings').onclick = () => {
    const idleVal = Number(document.getElementById('setIdleTimeout').value);
    send({
      type: 'setSettings',
      settings: {
        displayDurationSec: Number(document.getElementById('setDuration').value) || 10,
        transition: document.getElementById('setTransition').value,
        metadataFields: {
          date: document.getElementById('mfDate').checked,
          location: document.getElementById('mfLocation').checked,
          people: document.getElementById('mfPeople').checked,
          folder: document.getElementById('mfFolder').checked,
          owner: document.getElementById('mfOwner').checked,
          description: document.getElementById('mfDescription').checked,
        },
        metadataBehavior: document.getElementById('setMetaBehavior').value,
        deleteConfirm: document.getElementById('setDeleteConfirm').checked,
        idleTimeoutSec: idleVal > 0 ? idleVal : null,
      },
    });
  };
})();
