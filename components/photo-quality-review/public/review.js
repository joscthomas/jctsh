// CARD-0028 review app frontend. Vanilla JS, no build step -- matches this
// project's general preference for the simplest thing that works. Every
// decision click saves immediately via fetch (no explicit "save" action);
// the year picker is a browsing aid only, never a gate on when Preview/
// Confirm can run (Joseph's session-oriented correction).

let reportData = null;
let currentYear = null;

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

function thumbUrl(item) {
  return `/photo/${item.ownerLabel}/${item.assetId}/thumbnail`;
}

function viewUrl(item) {
  return `/view/${item.assetId}`;
}

async function loadReport() {
  reportData = await api('/api/report');
  renderYearPicker();
  await refreshTally();
}

function renderYearPicker() {
  const subtitle = document.getElementById('subtitle');
  const content = document.getElementById('content');
  currentYear = null;

  if (!reportData.generatedAt) {
    subtitle.textContent = 'No scan has been run yet.';
    content.innerHTML = '<p class="empty">Run scan.js on the M8 first, then reload this page.</p>';
    return;
  }

  subtitle.textContent = `Last scanned ${new Date(reportData.generatedAt).toLocaleString()}`;

  if (reportData.years.length === 0) {
    content.innerHTML = '<p class="empty">Nothing flagged -- library looks clean.</p>';
    return;
  }

  const cards = reportData.years.map((year) => {
    const count = countForYear(year);
    return `<div class="year-card" data-year="${year}">
      <div class="year">${year}</div>
      <div class="count">${count.total} flagged, ${count.reviewed} reviewed</div>
    </div>`;
  }).join('');

  content.innerHTML = `<div class="year-list">${cards}</div>`;
  content.querySelectorAll('.year-card').forEach((card) => {
    card.addEventListener('click', () => renderYear(Number(card.dataset.year)));
  });
}

function countForYear(year) {
  let total = 0;
  let reviewed = 0;
  for (const g of reportData.duplicateGroups) {
    if (g.year !== year) continue;
    total++;
    if (g.decision) reviewed++;
  }
  for (const item of [...reportData.broken, ...reportData.blurry]) {
    if (item.year !== year) continue;
    total++;
    if (item.decision) reviewed++;
  }
  return { total, reviewed };
}

function renderYear(year) {
  currentYear = year;
  const content = document.getElementById('content');
  document.getElementById('subtitle').textContent = `Reviewing ${year}`;

  const groups = reportData.duplicateGroups.filter((g) => g.year === year);
  const broken = reportData.broken.filter((i) => i.year === year);
  const blurry = reportData.blurry.filter((i) => i.year === year);

  let html = `<a class="back-link" href="#" id="backLink">&larr; All years</a>`;

  html += `<h2>Duplicates (${groups.length})</h2>`;
  html += groups.length
    ? groups.map(renderDuplicateGroup).join('')
    : '<p class="empty">None this year.</p>';

  html += `<h2>Blurry &amp; Broken (${broken.length + blurry.length})</h2>`;
  const singles = [...broken, ...blurry];
  html += singles.length
    ? `<div class="grid">${singles.map(renderSingle).join('')}</div>`
    : '<p class="empty">None this year.</p>';

  content.innerHTML = html;

  document.getElementById('backLink').addEventListener('click', (e) => {
    e.preventDefault();
    renderYearPicker();
  });
  wireDuplicateHandlers();
  wireSingleHandlers();
}

function renderDuplicateGroup(group) {
  const decision = group.decision;
  const items = group.members.map((m) => `
    <div class="item" data-asset-id="${m.assetId}">
      <img src="${thumbUrl(m)}" alt="${m.originalFileName}" loading="lazy">
      <div class="fname">${m.originalFileName}</div>
      <a class="view-link" href="${viewUrl(m)}" target="_blank" rel="noopener">View original</a>
      <label>
        <input type="radio" name="keep-${group.groupKey}" value="${m.assetId}"
          ${decision && decision.keepAssetId === m.assetId ? 'checked' : ''}>
        Keep this one
      </label>
    </div>
  `).join('');

  return `<div class="group" data-group-key="${group.groupKey}">
    <div class="group-row">
      ${items}
      <button class="skip-btn ${decision && decision.skip ? 'active' : ''}" data-group-key="${group.groupKey}">
        Skip for now
      </button>
    </div>
  </div>`;
}

function renderSingle(item) {
  const isBroken = !!item.errors;
  const label = isBroken
    ? `Broken (${Object.keys(item.errors).join(', ')})`
    : `Blur score ${item.variance.toFixed(1)}`;
  const marked = item.decision === 'delete' ? 'marked-delete' : item.decision === 'keep' ? 'marked-keep' : '';
  const buttonLabel = item.decision === 'delete' ? 'Marked: Delete' : item.decision === 'keep' ? 'Marked: Keep' : 'Delete?';

  return `<div class="item" data-asset-id="${item.assetId}">
    <img src="${thumbUrl(item)}" alt="${item.originalFileName}" loading="lazy">
    <div class="fname">${item.originalFileName}</div>
    <div class="fname">${label}</div>
    <a class="view-link" href="${viewUrl(item)}" target="_blank" rel="noopener">View original</a>
    <button class="toggle-btn ${marked}" data-asset-id="${item.assetId}">${buttonLabel}</button>
  </div>`;
}

function wireDuplicateHandlers() {
  document.querySelectorAll('.group').forEach((groupEl) => {
    const key = groupEl.dataset.groupKey;
    groupEl.querySelectorAll('input[type=radio]').forEach((radio) => {
      radio.addEventListener('change', async () => {
        await api('/api/decide/duplicate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ groupKey: key, keepAssetId: radio.value }),
        });
        await loadReport();
        renderYear(currentYear);
      });
    });
    const skipBtn = groupEl.querySelector('.skip-btn');
    skipBtn.addEventListener('click', async () => {
      await api('/api/decide/duplicate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ groupKey: key, skip: true }),
      });
      await loadReport();
      renderYear(currentYear);
    });
  });
}

function wireSingleHandlers() {
  document.querySelectorAll('.toggle-btn[data-asset-id]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const assetId = btn.dataset.assetId;
      // Cycle: unset -> delete -> keep -> delete -> ...
      const next = btn.classList.contains('marked-delete') ? 'keep' : 'delete';
      await api('/api/decide/single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assetId, decision: next }),
      });
      await loadReport();
      renderYear(currentYear);
    });
  });
}

async function refreshTally() {
  const preview = await api('/api/preview');
  const bar = document.getElementById('tallyBar');
  const count = document.getElementById('tallyCount');
  if (preview.items.length === 0) {
    bar.style.display = 'none';
  } else {
    bar.style.display = 'flex';
    count.textContent = `${preview.items.length} marked for deletion`;
  }
  return preview.items;
}

document.getElementById('previewBtn').addEventListener('click', async () => {
  const items = await refreshTally();
  const backdrop = document.getElementById('modalBackdrop');
  document.getElementById('modalSummary').textContent =
    `${items.length} file(s) will be moved to Immich's trash and logged for Google Photos cleanup:`;
  document.getElementById('modalList').innerHTML = items
    .map((i) => `<li>${i.originalFileName} &mdash; ${i.reason}</li>`)
    .join('');
  backdrop.classList.add('open');
});

document.getElementById('cancelBtn').addEventListener('click', () => {
  document.getElementById('modalBackdrop').classList.remove('open');
});

document.getElementById('confirmBtn').addEventListener('click', async () => {
  const result = await api('/api/confirm', { method: 'POST' });
  document.getElementById('modalBackdrop').classList.remove('open');
  alert(`Deleted ${result.deletedCount} file(s).` + (result.failed.length ? ` ${result.failed.length} failed.` : ''));
  await loadReport();
  if (currentYear) renderYear(currentYear);
});

loadReport();
