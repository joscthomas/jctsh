// CARD-0028 review app frontend. Vanilla JS, no build step -- matches this
// project's general preference for the simplest thing that works. Every
// decision click saves immediately via fetch (no explicit "save" action);
// the year picker is a browsing aid only, never a gate on when Preview/
// Confirm can run (Joseph's session-oriented correction).

let reportData = null;
let currentYear = null;

// Delete scope (CARD-0028, Joseph's call) -- the pagination window
// currently loaded for the year being viewed, in groupKey/assetId terms.
// Empty on the year picker (nothing in view). Drives the tally bar, Preview
// Deletions, and Confirm & Delete, so none of them can act on a decision
// from a page you haven't scrolled to. See renderYear() for how it's built.
let currentScope = { groupKeys: [], singleAssetIds: [] };

// In-page toast, replacing native alert() (CARD-0028, Joseph's call) --
// browser alert()/confirm() dialogs are chrome-rendered and always prefixed
// with the page's own origin ("100.111.16.14 says"), which no page-level JS
// can suppress. This shows just the message, auto-dismissing after a few
// seconds (errors stay up longer -- more worth reading closely).
let toastTimeout = null;
function showToast(message, { isError = false } = {}) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.toggle('error', isError);
  toast.classList.add('open');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove('open'), isError ? 6000 : 3500);
}

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

// Pure data refresh -- deliberately does NOT render anything itself.
// Previously called renderYearPicker() internally, which as a side effect
// reset the global currentYear to null; every decision handler below
// follows this with `renderYear(currentYear)`, so that reset silently
// broke every single one (not just the new "Delete all" button) -- found
// live when Joseph hit "Delete all" and landed on a "Reviewing null" page
// showing 0 items in every section. The decision itself was saved
// correctly (the tally bar still showed "2 marked for deletion", read from
// the server) -- this was purely a client-side render bug, nothing lost.
async function loadReport() {
  reportData = await api('/api/report');
  await refreshTally();
}

function renderYearPicker() {
  const subtitle = document.getElementById('subtitle');
  const content = document.getElementById('content');
  currentYear = null;
  currentScope = { groupKeys: [], singleAssetIds: [] }; // nothing in view here

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

  // A year with nothing actionable left (CARD-0028, Joseph's call: "2026
  // review for now is done so it seems like the 2026 button should be
  // disabled... if we rerun the batch process and more are identified then
  // enable 2026") gets disabled -- no click handler at all, not just a
  // visual dimming -- and re-enables itself automatically the moment
  // actionableByYear[year] goes back above zero, e.g. after a re-scan
  // surfaces something genuinely new.
  const cards = reportData.years.map((year) => {
    const count = countForYear(year);
    const actionable = (reportData.actionableByYear && reportData.actionableByYear[year]) || 0;
    const isDone = actionable === 0;
    return `<div class="year-card${isDone ? ' is-done' : ''}" data-year="${year}">
      <div class="year">${year}</div>
      <div class="count">${count.total} flagged, ${count.reviewed} reviewed${isDone ? ' &mdash; done' : ''}</div>
    </div>`;
  }).join('');

  content.innerHTML = `<div class="year-list">${cards}</div>`;
  content.querySelectorAll('.year-card:not(.is-done)').forEach((card) => {
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
  // Already-resolved items (deleted / Keep-all / dismissed) don't appear in
  // duplicateGroups/broken/blurry at all -- without this they'd silently
  // drop out of this year's own flagged/reviewed tally instead of counting
  // as the reviewed work they represent.
  const r = (reportData.resolvedCounts && reportData.resolvedCounts[year]) || {
    deletedGroups: 0, deletedSingles: 0, keepAllGroups: 0, dismissedSingles: 0,
  };
  const resolvedTotal = r.deletedGroups + r.deletedSingles + r.keepAllGroups + r.dismissedSingles;
  total += resolvedTotal;
  reviewed += resolvedTotal;
  return { total, reviewed };
}

// Hide-already-decided toggle (CARD-0028, Joseph's call): reloading a year
// re-shows every group/item, including ones already decided (checked radio,
// active Skip/Keep-all/Delete-all button) but not yet run through Confirm &
// Delete -- correct (Preview is the real audit step, decided items must
// stay visible/editable until then), but easy to mistake for "my decisions
// didn't stick" when the page is dense with badges. This toggle only
// affects what's rendered for the currently-open year -- it's a display
// filter, not a data change, and doesn't touch decisions.json or auto-select
// (a hidden group can still get auto-selected in the background; it just
// won't visibly disappear until the next render).
let hideDecided = false;

// Paging within a year (CARD-0028, Joseph's call): a year like 2015 has
// 5,128 duplicate groups (11,043 photos) and 629 blurry items -- rendering
// all of it at once was the real cause of the review page going
// unresponsive, both from raw DOM size and from loadAlbumBadges()/
// loadMotionBadges() firing one fetch per visible thumbnail with no cap
// (see the concurrency limiter below). GROUPS_PAGE_SIZE is counted in
// *groups*, not photos -- at ~2 members/group average that's roughly the
// same ~200-photo budget as SINGLES_PAGE_SIZE, which counts photos
// directly. Reset to the first page whenever a year is entered fresh
// (from the picker, a hide-decided toggle, or after a decision reload) --
// only the "Show more" buttons themselves pass resetPaging: false.
const GROUPS_PAGE_SIZE = 100;
const SINGLES_PAGE_SIZE = 200;
let visibleGroupLimit = GROUPS_PAGE_SIZE;
let visibleSingleLimit = SINGLES_PAGE_SIZE;

function renderYear(year, { resetPaging = true } = {}) {
  currentYear = year;
  if (resetPaging) {
    visibleGroupLimit = GROUPS_PAGE_SIZE;
    visibleSingleLimit = SINGLES_PAGE_SIZE;
  }
  const content = document.getElementById('content');
  document.getElementById('subtitle').textContent = `Reviewing ${year}`;

  const allGroups = reportData.duplicateGroups.filter((g) => g.year === year);
  const allBroken = reportData.broken.filter((i) => i.year === year);
  const allBlurry = reportData.blurry.filter((i) => i.year === year);

  const groups = hideDecided ? allGroups.filter((g) => !g.decision) : allGroups;
  const broken = hideDecided ? allBroken.filter((i) => !i.decision) : allBroken;
  const blurry = hideDecided ? allBlurry.filter((i) => !i.decision) : allBlurry;

  // Delete scope (CARD-0028, Joseph's call): the tally/Preview/Confirm used
  // to total every pending decision across the *entire* library session,
  // which meant Confirm & Delete could act on auto-selected duplicate
  // groups from pages you'd never actually scrolled to (paging only
  // controls what's *rendered*, decisions persist regardless). Now the
  // pagination window itself IS the scope: only groups/items within the
  // currently-loaded page count toward the tally and get processed by
  // Confirm & Delete. Deliberately computed from allGroups/allBroken+
  // allBlurry (unfiltered by hideDecided), not from `groups`/`broken`/
  // `blurry` above -- hideDecided is a display-only declutter toggle, and a
  // decided-but-hidden row is still meaningfully "on this page." Duplicate
  // groups are never split across pages (a group is one atomic render
  // unit), so there's no partial-group edge case to handle here.

  let html = `<a class="back-link" href="#" id="backLink">&larr; All years</a>`;
  html += `<label class="hide-decided-toggle">
    <input type="checkbox" id="hideDecidedToggle" ${hideDecided ? 'checked' : ''}>
    Hide already-decided items
  </label>`;

  // Already-resolved items (real Confirm & Delete already ran, a "Keep all"
  // decision, or a bulk-dismissed single) don't appear in
  // reportData.duplicateGroups/broken/blurry at all -- the server filters
  // them out entirely (see server.js's filterDeletedFromReport /
  // filterResolvedFromReport). On its own that reads as "there's nothing
  // here," easy to mistake for "my decision didn't take." resolvedCounts is
  // the server's separate tally of exactly what got filtered and why, so
  // the header can say so explicitly instead of the work just vanishing.
  const yearResolved = (reportData.resolvedCounts && reportData.resolvedCounts[year]) || {
    deletedGroups: 0, deletedSingles: 0, keepAllGroups: 0, dismissedSingles: 0,
  };

  const dupHidden = allGroups.length - groups.length;
  const dupNotes = [];
  if (dupHidden) dupNotes.push(`${dupHidden} already decided, hidden`);
  if (yearResolved.deletedGroups) dupNotes.push(`${yearResolved.deletedGroups} already deleted`);
  if (yearResolved.keepAllGroups) dupNotes.push(`${yearResolved.keepAllGroups} kept via "Keep all"`);
  html += `<h2>Duplicates (${groups.length}${dupNotes.length ? ` &mdash; ${dupNotes.join(', ')}` : ''})</h2>`;
  const groupsPage = allGroups.slice(0, visibleGroupLimit);
  const groupsRemaining = allGroups.length - groupsPage.length;
  const groupsToShow = hideDecided ? groupsPage.filter((g) => !g.decision) : groupsPage;
  html += groupsToShow.length
    ? groupsToShow.map(renderDuplicateGroup).join('')
    : allGroups.length
    ? '<p class="empty">All duplicates here are already decided.</p>'
    : '<p class="empty">None this year.</p>';
  if (groupsRemaining > 0) {
    html += `<button class="load-more-btn" id="loadMoreGroupsBtn">
      Show ${Math.min(GROUPS_PAGE_SIZE, groupsRemaining)} more duplicate group(s) (${groupsRemaining} not yet shown)
    </button>`;
  }

  const singlesAllCount = allBroken.length + allBlurry.length;
  const singles = [...broken, ...blurry];
  const singlesHidden = singlesAllCount - singles.length;
  const singlesNotes = [];
  if (singlesHidden) singlesNotes.push(`${singlesHidden} already decided, hidden`);
  if (yearResolved.deletedSingles) singlesNotes.push(`${yearResolved.deletedSingles} already deleted`);
  if (yearResolved.dismissedSingles) singlesNotes.push(`${yearResolved.dismissedSingles} reviewed & dismissed`);
  html += `<h2>Blurry &amp; Broken (${singles.length}${singlesNotes.length ? ` &mdash; ${singlesNotes.join(', ')}` : ''})</h2>`;
  // Bulk "I've looked at everything left here" (CARD-0028, Joseph's call):
  // only offered when there's at least one *undecided* single actually
  // showing -- no point dismissing a list that's empty or that's only
  // showing already-marked-for-deletion items.
  const undecidedSingles = singles.filter((i) => !i.decision);
  if (undecidedSingles.length > 0) {
    html += `<button class="dismiss-singles-btn" id="dismissSinglesBtn">
      Mark remaining ${undecidedSingles.length} as reviewed (keep them, hide from this list)
    </button>`;
  }
  // Paged for rendering only -- the dismiss button above intentionally
  // still operates on the *full* undecidedSingles (every page), since "mark
  // everything remaining as reviewed" should cover the whole section, not
  // just whatever page happens to be currently visible. Delete scope (see
  // groupsPage above) is different: it's meant to track "what I'm actually
  // looking at," so it's built from the unfiltered year-wide singles list,
  // same as groupsPage.
  const allSingles = [...allBroken, ...allBlurry];
  const singlesPage = allSingles.slice(0, visibleSingleLimit);
  const singlesRemaining = allSingles.length - singlesPage.length;
  const singlesToShow = hideDecided ? singlesPage.filter((i) => !i.decision) : singlesPage;
  html += singlesToShow.length
    ? `<div class="grid">${singlesToShow.map(renderSingle).join('')}</div>`
    : singlesAllCount
    ? '<p class="empty">All blurry/broken items here are already decided.</p>'
    : '<p class="empty">None this year.</p>';
  if (singlesRemaining > 0) {
    html += `<button class="load-more-btn" id="loadMoreSinglesBtn">
      Show ${Math.min(SINGLES_PAGE_SIZE, singlesRemaining)} more (${singlesRemaining} not yet shown)
    </button>`;
  }

  currentScope = {
    groupKeys: groupsPage.map((g) => g.groupKey),
    singleAssetIds: singlesPage.map((i) => i.assetId),
  };

  content.innerHTML = html;

  document.getElementById('backLink').addEventListener('click', (e) => {
    e.preventDefault();
    renderYearPicker();
  });
  document.getElementById('hideDecidedToggle').addEventListener('change', (e) => {
    hideDecided = e.target.checked;
    renderYear(year);
  });
  const loadMoreGroupsBtn = document.getElementById('loadMoreGroupsBtn');
  if (loadMoreGroupsBtn) {
    loadMoreGroupsBtn.addEventListener('click', () => {
      visibleGroupLimit += GROUPS_PAGE_SIZE;
      renderYear(year, { resetPaging: false });
    });
  }
  const loadMoreSinglesBtn = document.getElementById('loadMoreSinglesBtn');
  if (loadMoreSinglesBtn) {
    loadMoreSinglesBtn.addEventListener('click', () => {
      visibleSingleLimit += SINGLES_PAGE_SIZE;
      renderYear(year, { resetPaging: false });
    });
  }
  const dismissBtn = document.getElementById('dismissSinglesBtn');
  if (dismissBtn) {
    dismissBtn.addEventListener('click', async () => {
      const assetIds = undecidedSingles.map((i) => i.assetId);
      dismissBtn.disabled = true;
      dismissBtn.textContent = 'Marking as reviewed...';

      // Progress dialog (CARD-0028, Joseph's call) -- this bulk-dismisses
      // whatever's currently undecided in the section, which on a year with
      // a large backlog can be hundreds/thousands of items; same reasoning
      // as Confirm & Delete's own countdown, so it gets the same treatment
      // rather than a single button-text change that reads like a hang.
      const backdrop = document.getElementById('dismissModalBackdrop');
      const textEl = document.getElementById('dismissProgressText');
      const barEl = document.getElementById('dismissProgressBar');
      const barFillEl = document.getElementById('dismissProgressBarFill');
      barFillEl.style.width = '0%';
      textEl.innerHTML = '<span class="spinner"></span> Starting&hellip;';
      backdrop.classList.add('open');
      const pollHandle = pollProgress('/api/dismiss-singles/progress', 'Marking', textEl, barEl, barFillEl);

      // Found live (Joseph): the dialog closed the instant the /api/dismiss-
      // singles POST itself resolved (correct -- that write really is
      // fast), but the dismiss handler used to close it *before*
      // loadReport()+renderYear() below, which re-fetches and re-parses
      // report.json (confirmed ~0.9s server-side alone on this library's
      // size, on top of the client's own re-parse and DOM re-render) --
      // several more seconds of real, visible work with the dialog already
      // gone. Keeping it open (with a distinct "Refreshing..." state, since
      // the /api/dismiss-singles/progress counter itself has already
      // reached 100% by this point) through the full round trip means it
      // only closes once the list has actually finished updating.
      try {
        await api('/api/dismiss-singles', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ assetIds }),
        });
        clearInterval(pollHandle);
        barFillEl.style.width = '100%';
        textEl.innerHTML = '<span class="spinner"></span> Refreshing the list&hellip;';
        await loadReport();
        renderYear(year);
      } finally {
        clearInterval(pollHandle);
        barEl.classList.remove('active');
        backdrop.classList.remove('open');
      }
    });
  }
  wireDuplicateHandlers();
  wireSingleHandlers();
  loadAlbumBadges();
  loadMotionBadges();
}

// Concurrency-limited iteration -- mirrors scan.js's own mapWithConcurrency.
// loadAlbumBadges/loadMotionBadges below used to fire one fetch per visible
// thumbnail via a bare forEach(async ...), with no cap at all. Fine for a
// handful of duplicate groups, genuinely pathological for a heavy year --
// even with per-year paging now capping what's in the DOM to ~100 groups,
// that's still ~200 photos x 2 badge types = ~400 simultaneous requests
// hitting this single-threaded Node server (each of which itself calls out
// to Immich) at once. Capped concurrency spreads that load out instead of
// firing it all in one burst.
async function forEachWithConcurrency(items, limit, fn) {
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const item = items[next++];
      await fn(item);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
}

const BADGE_FETCH_CONCURRENCY = 6;

// Album membership per duplicate-group member (CARD-0028) -- fetched lazily,
// only for the year currently being reviewed (not the whole library up
// front -- see server.js's own comment on /api/albums/:assetId for why).
// This turned out to matter: which copy is actually linked to an album is a
// real, independent signal for which one to keep, separate from filename/
// size/dimensions -- a duplicate can have the "cleanest" name and still be
// the one with no album at all.
function loadAlbumBadges() {
  const els = [...document.querySelectorAll('.album-badge[data-asset-id]')];
  forEachWithConcurrency(els, BADGE_FETCH_CONCURRENCY, async (el) => {
    const { assetId, owner } = el.dataset;
    const groupKey = el.closest('.group')?.dataset.groupKey;
    let albums = [];
    try {
      ({ albums } = await api(`/api/albums/${assetId}?ownerLabel=${owner}`));
      if (albums.length) {
        el.textContent = `In album: ${albums.join(', ')}`;
        el.classList.add('has-album');
      } else {
        el.textContent = 'Not in any album';
        el.classList.add('no-album');
      }
    } catch {
      el.textContent = '';
    }
    if (groupKey) recordAlbumStatus(groupKey, assetId, albums);
  });
}

// Motion Photo (.MP.jpg) video-integrity badge (CARD-0028) -- czkawka only
// ever compares the still frame, so two duplicate copies can look identical
// while one's embedded motion clip is corrupted. Left blank for ordinary
// (non-Motion-Photo) items -- no point flagging "not a motion photo" on
// every single thumbnail that isn't one.
function loadMotionBadges() {
  const els = [...document.querySelectorAll('.motion-badge[data-asset-id]')];
  forEachWithConcurrency(els, BADGE_FETCH_CONCURRENCY, async (el) => {
    const { assetId, owner } = el.dataset;
    const groupKey = el.closest('.group')?.dataset.groupKey;
    let info = { isMotionPhoto: false };
    try {
      info = await api(`/api/motion-check/${assetId}?ownerLabel=${owner}`);
      if (info.isMotionPhoto) {
        if (info.valid) {
          el.textContent = 'Motion video: OK';
          el.classList.add('motion-ok');
        } else {
          el.textContent = 'Motion video: BROKEN';
          el.classList.add('motion-broken');
        }
      }
    } catch {
      // leave blank, fall through to recordMotionStatus with the neutral default
    }
    if (groupKey) recordMotionStatus(groupKey, assetId, info);
  });
}

// Auto-select (Joseph's call, 2026-08-06): for a 2-member duplicate group,
// once BOTH members' album membership and Motion Photo status are known,
// automatically pick "Keep this one" when the evidence is unambiguous --
// removes the repetitive manual click for clear-cut pairs, without skipping
// review: it's still just a normal decision saved through the same
// /api/decide/duplicate call a manual click makes, and Preview Deletions
// (which now explains *why* an auto-pick was made) remains the actual
// review/confirm checkpoint before anything is deleted. Never overrides an
// existing decision, manual or previously auto-applied.
//
// Two independent signals, each individually confirmed live against real
// data this session:
//   - motion: one copy's embedded Motion Photo video is corrupted, the
//     other's plays fine.
//   - album: one copy is linked to an album, the other isn't -- losing that
//     link (once Immich's 30-day trash retention expires) is a real cost
//     Joseph flagged directly, not a hypothetical.
// If both signals are decisive but point at *different* members, that's a
// genuine judgment call -- deliberately left for manual review rather than
// picking one arbitrarily.
const motionStatusByGroup = new Map(); // groupKey -> Map(assetId -> {isMotionPhoto, valid})
const albumStatusByGroup = new Map(); // groupKey -> Map(assetId -> string[] albums)

function recordMotionStatus(groupKey, assetId, info) {
  if (!motionStatusByGroup.has(groupKey)) motionStatusByGroup.set(groupKey, new Map());
  motionStatusByGroup.get(groupKey).set(assetId, info);
  maybeAutoSelectGroup(groupKey);
}

function recordAlbumStatus(groupKey, assetId, albums) {
  if (!albumStatusByGroup.has(groupKey)) albumStatusByGroup.set(groupKey, new Map());
  albumStatusByGroup.get(groupKey).set(assetId, albums);
  maybeAutoSelectGroup(groupKey);
}

async function maybeAutoSelectGroup(groupKey) {
  const group = findDuplicateGroup(groupKey);
  if (!group || group.decision) return; // already decided -- never override
  if (group.members.length !== 2) return; // only the unambiguous 2-member case
  const [a, b] = group.members;

  const motion = motionStatusByGroup.get(groupKey);
  const albums = albumStatusByGroup.get(groupKey);
  if (!motion || motion.size !== 2 || !albums || albums.size !== 2) return; // still waiting

  const isBroken = (assetId) => {
    const info = motion.get(assetId);
    return !!(info && info.isMotionPhoto && info.valid === false);
  };
  const hasAlbum = (assetId) => (albums.get(assetId) || []).length > 0;

  let motionWinner = null;
  if (isBroken(a.assetId) !== isBroken(b.assetId)) {
    motionWinner = isBroken(a.assetId) ? b.assetId : a.assetId;
  }
  let albumWinner = null;
  if (hasAlbum(a.assetId) !== hasAlbum(b.assetId)) {
    albumWinner = hasAlbum(a.assetId) ? a.assetId : b.assetId;
  }

  let keepAssetId = null;
  let autoReason = null;
  if (motionWinner && albumWinner) {
    if (motionWinner !== albumWinner) return; // signals disagree -- leave for manual review
    keepAssetId = motionWinner;
    autoReason = 'sibling had a broken Motion Photo video, and this is the one in an album';
  } else if (motionWinner) {
    keepAssetId = motionWinner;
    autoReason = 'sibling had a broken Motion Photo video';
  } else if (albumWinner) {
    keepAssetId = albumWinner;
    autoReason = 'this copy is in an album, the other is not';
  } else {
    return; // neither signal is decisive
  }

  const decision = { keepAssetId, auto: true };
  const groupEl = document.querySelector(`.group[data-group-key="${CSS.escape(groupKey)}"]`);
  if (groupEl) applyDuplicateDecisionLocally(groupEl, groupKey, decision);
  else if (group) group.decision = decision;

  await api('/api/decide/duplicate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ groupKey, keepAssetId, auto: true, autoReason }),
  });
  await refreshTally();
}

// Duplicate-group members frequently share the exact same originalFileName
// (burst shots, re-exports of the same shot) -- czkawka's own size/
// dimensions/similarity-difference fields are what actually let a reviewer
// tell two identically-named thumbnails apart. Blank when absent (report
// generated before this field started being kept -- see scan.js's own note).
function formatBytes(n) {
  if (n == null) return null;
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function duplicateMeta(m) {
  const parts = [];
  if (m.width && m.height) parts.push(`${m.width}×${m.height}`);
  const bytes = formatBytes(m.size);
  if (bytes) parts.push(bytes);
  if (m.difference != null) parts.push(`diff ${m.difference} from group leader`);
  return parts.join(' · ');
}

// Which Immich account (Joseph's or Robin's) an item actually lives under
// (CARD-0028) -- both accounts' files get scanned and shown together (see
// routes/immich.js's buildPathIndex), so without this a reviewer has no way
// to tell whose library a given duplicate/blurry/broken photo is even in.
function ownerLabelText(ownerLabel) {
  if (!ownerLabel) return '';
  return ownerLabel.charAt(0).toUpperCase() + ownerLabel.slice(1);
}

function renderDuplicateGroup(group) {
  const decision = group.decision;
  const items = group.members.map((m) => {
    const meta = duplicateMeta(m);
    return `
    <div class="item" data-asset-id="${m.assetId}">
      <a class="thumb-link" href="${viewUrl(m)}" target="_blank" rel="noopener">
        <img src="${thumbUrl(m)}" alt="${m.originalFileName}" loading="lazy">
      </a>
      <div class="fname">${m.originalFileName}</div>
      <div class="owner-badge owner-${m.ownerLabel}">${ownerLabelText(m.ownerLabel)}</div>
      ${meta ? `<div class="fmeta">${meta}</div>` : ''}
      <div class="album-badge" data-asset-id="${m.assetId}" data-owner="${m.ownerLabel}">Checking albums&hellip;</div>
      <div class="motion-badge" data-asset-id="${m.assetId}" data-owner="${m.ownerLabel}"></div>
      <a class="view-link" href="${viewUrl(m)}" target="_blank" rel="noopener">View original</a>
      <label>
        <input type="radio" name="keep-${group.groupKey}" value="${m.assetId}"
          ${decision && decision.keepAssetId === m.assetId ? 'checked' : ''}>
        Keep this one
        <span class="auto-tag" style="display:${decision && decision.auto && decision.keepAssetId === m.assetId ? 'inline' : 'none'}">(auto-selected)</span>
      </label>
    </div>
  `;
  }).join('');

  return `<div class="group" data-group-key="${group.groupKey}">
    <div class="group-row">
      ${items}
      <button class="skip-btn ${decision && decision.skip ? 'active' : ''}" data-group-key="${group.groupKey}">
        Skip for now
      </button>
      <button class="keep-all-btn ${decision && decision.keepAll ? 'active' : ''}" data-group-key="${group.groupKey}">
        Keep all -- no deletion
      </button>
      <button class="delete-all-btn ${decision && decision.deleteAll ? 'active' : ''}" data-group-key="${group.groupKey}">
        Delete all -- keep none
      </button>
    </div>
  </div>`;
}

// Simplified (Joseph's call, 2026-08-06): "don't want to mark the ones to
// keep, only the ones to delete -- once I've decided the ones to delete, I
// want to keep the rest." A single toggle now: unmarked (implicitly kept,
// no click needed) <-> marked for deletion. This already matches how
// pendingDeletions() actually behaves -- only assets with decision ===
// 'delete' are ever queued -- the old three-way keep/delete/unset cycle was
// forcing an explicit "keep" click that was never functionally necessary.
function renderSingle(item) {
  const isBroken = !!item.errors;
  const label = isBroken
    ? `Broken (${Object.keys(item.errors).join(', ')})`
    : `Blur score ${item.variance.toFixed(1)}`;
  const marked = item.decision === 'delete' ? 'marked-delete' : '';
  const buttonLabel = item.decision === 'delete' ? '✖ Marked: Delete' : 'Delete';
  const itemClass = item.decision === 'delete' ? 'item is-decided' : 'item';

  return `<div class="${itemClass}" data-asset-id="${item.assetId}">
    <a class="thumb-link" href="${viewUrl(item)}" target="_blank" rel="noopener">
      <img src="${thumbUrl(item)}" alt="${item.originalFileName}" loading="lazy">
    </a>
    <div class="fname">${item.originalFileName}</div>
    <div class="owner-badge owner-${item.ownerLabel}">${ownerLabelText(item.ownerLabel)}</div>
    <div class="fname">${label}</div>
    <a class="view-link" href="${viewUrl(item)}" target="_blank" rel="noopener">View original</a>
    <button class="toggle-btn ${marked}" data-asset-id="${item.assetId}">${buttonLabel}</button>
  </div>`;
}

// Decision clicks used to `await loadReport(); renderYear(currentYear)` --
// a full re-render of every group in the year, including the album/motion
// badges, which reset to "Checking..." and re-fetched from scratch on
// *every single click anywhere in the list*, not just the item clicked.
// Joseph: "the page keeps reloading and its herky jerky... loses the motion
// video indicator then gets it back on reload." Fixed by updating only the
// specific group/item's own controls in place, and mutating the in-memory
// reportData to match (so a later full render, e.g. after Confirm & Delete,
// still reflects the current state without needing a re-fetch).
function findDuplicateGroup(key) {
  return reportData.duplicateGroups.find((g) => g.groupKey === key);
}

function applyDuplicateDecisionLocally(groupEl, key, decision) {
  const g = findDuplicateGroup(key);
  if (g) g.decision = decision;
  groupEl.querySelector('.skip-btn').classList.toggle('active', !!(decision && decision.skip));
  groupEl.querySelector('.keep-all-btn').classList.toggle('active', !!(decision && decision.keepAll));
  groupEl.querySelector('.delete-all-btn').classList.toggle('active', !!(decision && decision.deleteAll));
  groupEl.querySelectorAll('.item').forEach((itemEl) => {
    const assetId = itemEl.dataset.assetId;
    const isKept = !!(decision && decision.keepAssetId === assetId);
    const radio = itemEl.querySelector('input[type=radio]');
    if (radio) radio.checked = isKept;
    const autoTag = itemEl.querySelector('.auto-tag');
    if (autoTag) autoTag.style.display = isKept && decision.auto ? 'inline' : 'none';
  });
}

function wireDuplicateHandlers() {
  document.querySelectorAll('.group').forEach((groupEl) => {
    const key = groupEl.dataset.groupKey;
    groupEl.querySelectorAll('input[type=radio]').forEach((radio) => {
      radio.addEventListener('change', async () => {
        const decision = { keepAssetId: radio.value };
        applyDuplicateDecisionLocally(groupEl, key, decision);
        await api('/api/decide/duplicate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ groupKey: key, keepAssetId: radio.value }),
        });
        await refreshTally();
      });
    });
    const skipBtn = groupEl.querySelector('.skip-btn');
    skipBtn.addEventListener('click', async () => {
      const decision = { skip: true };
      applyDuplicateDecisionLocally(groupEl, key, decision);
      await api('/api/decide/duplicate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ groupKey: key, skip: true }),
      });
      await refreshTally();
    });
    const keepAllBtn = groupEl.querySelector('.keep-all-btn');
    keepAllBtn.addEventListener('click', async () => {
      const decision = { keepAll: true };
      applyDuplicateDecisionLocally(groupEl, key, decision);
      await api('/api/decide/duplicate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ groupKey: key, keepAll: true }),
      });
      await refreshTally();
    });
    const deleteAllBtn = groupEl.querySelector('.delete-all-btn');
    deleteAllBtn.addEventListener('click', async () => {
      const decision = { deleteAll: true };
      applyDuplicateDecisionLocally(groupEl, key, decision);
      await api('/api/decide/duplicate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ groupKey: key, deleteAll: true }),
      });
      await refreshTally();
    });
  });
}

function wireSingleHandlers() {
  document.querySelectorAll('.toggle-btn[data-asset-id]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const assetId = btn.dataset.assetId;
      // Toggle only: unmarked <-> marked for deletion. Anything left
      // unmarked is implicitly kept -- no separate "keep" click needed.
      const next = btn.classList.contains('marked-delete') ? null : 'delete';
      btn.classList.remove('marked-delete');
      if (next === 'delete') btn.classList.add('marked-delete');
      btn.textContent = next === 'delete' ? '✖ Marked: Delete' : 'Delete';
      btn.closest('.item').classList.toggle('is-decided', next === 'delete');
      const item = [...reportData.broken, ...reportData.blurry].find((i) => i.assetId === assetId);
      if (item) item.decision = next;
      await api('/api/decide/single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assetId, decision: next }),
      });
      await refreshTally();
    });
  });
}

async function refreshTally() {
  const preview = await api('/api/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scope: currentScope }),
  });
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
  // Clear any leftover progress state from a previous confirm attempt (e.g.
  // a failed one) -- this modal can be reopened without a page reload.
  document.getElementById('confirmProgressText').innerHTML = '';
  document.getElementById('progressBar').classList.remove('active');
  document.getElementById('progressBarFill').style.width = '0%';
  backdrop.classList.add('open');
});

document.getElementById('cancelBtn').addEventListener('click', () => {
  document.getElementById('modalBackdrop').classList.remove('open');
});

// Found live (Joseph): clicking Confirm & Delete gave no feedback while the
// real delete was running, so he clicked it several more times -- each
// click fired its own full /api/confirm pass, and since Immich's delete API
// doesn't error on an already-trashed asset, every one of those extra
// passes re-logged the same files to the deletion log. 275 rows ended up
// covering only 55 real deletions (5x each). No data was actually
// double-deleted -- purely a duplicate-logging bug. Fixed two ways: this
// button-disable + "please wait" state (so a repeat click is simply
// ignored), and a matching server-side in-flight guard on /api/confirm
// itself (belt and suspenders -- covers a second browser tab or a stray
// retry, not just this one button).
// Found live (Joseph, second time): the button *did* correctly disable and
// the static "please wait" text *was* there, but on a real ~100-item batch
// (each item a real Immich API call, a CSV append, and a Sheet POST) that
// took several minutes, a message that never changes reads exactly like a
// hang -- there was no way to tell "still working" from "stuck." Replaced
// with a live "Deleting X of Y..." counter, polled from the server every
// second, plus a spinner -- something visibly moving is the only real proof
// a long-running background process hasn't died.
// Found live (Joseph, third time): even with the text-based spinner in
// place, a real 10+ item batch still read as "nothing happened" -- a single
// line of text updating in place inside a dialog that was already open (via
// Preview) is easy to not consciously register, especially right before a
// native alert() steals focus the moment it's done. A progress *bar* is a
// much harder-to-miss visual signal than text alone, and polling every
// 300ms (down from 1000ms) means the first update lands well before a
// several-second batch could finish, rather than possibly never getting a
// tick in edge cases.
// Found live (Joseph, fourth time): the progress text/bar still wasn't
// visible -- it sat at the *top* of the modal, right above modalList, which
// on a long pending-deletions list pushes it off the top of the visible
// scroll area (the modal itself scrolls, doesn't grow past 80vh). Moved to
// its own element below the list, right above the action buttons, which
// stays in view regardless of list length.
// Shared by Confirm & Delete and Mark-remaining-as-reviewed (CARD-0028) --
// both are single requests that can process a large batch server-side with
// no other feedback, so both get the same spinner+bar treatment via the same
// polled-progress endpoint shape ({ total, completed }).
function pollProgress(progressUrl, verb, textEl, barEl, barFillEl) {
  barEl.classList.add('active');
  const tick = async () => {
    try {
      const p = await api(progressUrl);
      if (p.total > 0) {
        textEl.innerHTML = `<span class="spinner"></span> ${verb} ${p.completed} of ${p.total}&hellip;`;
        barFillEl.style.width = `${Math.round((p.completed / p.total) * 100)}%`;
      }
    } catch {
      // transient poll failure -- leave the last-known text showing, the
      // main await below is still the source of truth for completion.
    }
  };
  tick();
  return setInterval(tick, 300);
}

document.getElementById('confirmBtn').addEventListener('click', async (e) => {
  const confirmBtn = e.currentTarget;
  const cancelBtn = document.getElementById('cancelBtn');
  if (confirmBtn.disabled) return; // a delete is already running -- ignore repeat clicks
  const progressTextEl = document.getElementById('confirmProgressText');
  const barEl = document.getElementById('progressBar');
  const barFillEl = document.getElementById('progressBarFill');
  confirmBtn.disabled = true;
  cancelBtn.disabled = true;
  barFillEl.style.width = '0%';
  progressTextEl.innerHTML = '<span class="spinner"></span> Starting delete&hellip;';
  const pollHandle = pollProgress('/api/confirm/progress', 'Deleting', progressTextEl, barEl, barFillEl);
  // Found live (Joseph) -- same gap as the dismiss-singles dialog had: the
  // modal used to close the instant /api/confirm itself resolved (correct,
  // that part really is done), but loadReport()+renderYear() below re-fetch
  // and re-parse the (large) report.json and rebuild the DOM, which is real,
  // visible work with the dialog already gone. Keeping it open through the
  // full round trip (with a distinct "Refreshing..." state, since the
  // /api/confirm/progress counter has already reached 100% by this point)
  // means it only closes once the list has actually finished updating.
  try {
    const result = await api('/api/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope: currentScope }),
    });
    clearInterval(pollHandle);
    barFillEl.style.width = '100%';
    progressTextEl.innerHTML = '<span class="spinner"></span> Refreshing the list&hellip;';
    showToast(`Deleted ${result.deletedCount} file(s).` + (result.failed.length ? ` ${result.failed.length} failed.` : ''), { isError: result.failed.length > 0 });
    await loadReport();
    if (currentYear) renderYear(currentYear); else renderYearPicker();
    barEl.classList.remove('active');
    document.getElementById('modalBackdrop').classList.remove('open');
  } catch (err) {
    clearInterval(pollHandle);
    barEl.classList.remove('active');
    progressTextEl.textContent = '';
    showToast(`Delete failed: ${err.message}`, { isError: true });
  } finally {
    confirmBtn.disabled = false;
    cancelBtn.disabled = false;
  }
});

loadReport().then(renderYearPicker);
