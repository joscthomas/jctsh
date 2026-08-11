require('dotenv').config();

const express = require('express');
const fs = require('fs/promises');
const path = require('path');

const immich = require('./routes/immich');
const deletionLog = require('./routes/deletion-log');

const PORT = Number(process.env.PORT) || 3001;
const DATA_DIR = process.env.PHOTO_QUALITY_REVIEW_DATA_DIR || path.join(__dirname, 'data');
const REPORT_PATH = path.join(DATA_DIR, 'report.json');
const DECISIONS_PATH = path.join(DATA_DIR, 'decisions.json');

// ---------------------------------------------------------------------------
// Persisted decision state -- every mark/skip click saves here immediately
// (CARD-0028's "closing the browser mid-review never loses progress"
// requirement). Not a commit boundary by itself -- see /api/preview and
// /api/confirm below for the actual delete step.
//
//   duplicates: { [groupKey]: { keepAssetId } | { skip: true } | { keepAll: true } | { deleteAll: true } }
//     groupKey is the sorted, joined assetIds of the group -- stable across
//     re-scans even if czkawka returns groups in a different order.
//   singles: { [assetId]: 'delete' }
//   dismissedSingles: string[] -- assetIds bulk-marked "reviewed, keeping
//     it" via the singles section's own dismiss action (Joseph's call,
//     2026-08-06: he doesn't want to click 'keep' per item, but does want a
//     way to say "I've looked at everything left in this list, hide it
//     going forward" -- separate from an individual decision, and unlike
//     decisions.singles, entries here are permanent even across a re-scan
//     that regenerates report.json, since the point is specifically "don't
//     make me re-review the same photo just because the batch job ran
//     again."
// ---------------------------------------------------------------------------
async function loadJson(filePath, fallback) {
  try {
    return JSON.parse(await fs.readFile(filePath, 'utf-8'));
  } catch {
    return fallback;
  }
}

async function loadDecisions() {
  const decisions = await loadJson(DECISIONS_PATH, { duplicates: {}, singles: {}, dismissedSingles: [] });
  if (!decisions.dismissedSingles) decisions.dismissedSingles = []; // pre-existing files predate this field
  return decisions;
}

async function saveDecisions(decisions) {
  await fs.mkdir(DATA_DIR, { recursive: true });
  await fs.writeFile(DECISIONS_PATH, JSON.stringify(decisions, null, 2));
}

// Found live (Joseph, 2026-08-06): after a review session heavy on
// auto-select, decisions he'd made no longer showed up after a reload.
// Root cause: every decisions.json writer (both /api/decide/* routes, plus
// /api/confirm's own load-mutate-save of the same file) did
// loadDecisions() -> mutate -> saveDecisions() with no locking at all --
// a classic read-modify-write race. Auto-select fires its own
// /api/decide/duplicate call the moment each group's album+motion badges
// resolve, and on a whole year's worth of groups loading at once, many of
// those land within milliseconds of each other: request B's loadDecisions()
// reads a snapshot from *before* request A's saveDecisions() lands, so B's
// later save silently overwrites A's change with a stale copy that never
// had it. Confirmed directly -- a decision genuinely existed in
// decisions.json, groupKey computation matched exactly, and /api/report
// still returned decision: null for it, which only makes sense if the
// write itself had been clobbered by a later, stale save.
//
// Fix: every read-modify-write of decisions.json now goes through this
// single in-process lock (a promise chain -- correct without a real mutex
// library since Node is single-threaded, this only needs to serialize
// *ordering* of async operations, not guard against real parallelism).
let decisionsLock = Promise.resolve();
function withDecisionsLock(fn) {
  const result = decisionsLock.then(fn, fn);
  decisionsLock = result.then(() => {}, () => {}); // never let one failure wedge the chain for later callers
  return result;
}

function groupKey(group) {
  return group.map((m) => m.assetId).sort().join(',');
}

function yearOf(isoDate) {
  return isoDate ? new Date(isoDate).getFullYear() : null;
}

// report.json is a static scan snapshot -- it has no idea an asset was
// later actually deleted (via a completed Confirm & Delete). Without this,
// a duplicate group whose surviving member is already the real outcome of
// a past decision would keep reappearing as if undecided on every reload,
// and a group with a stale reference to an already-gone sibling could get
// re-queued for deletion (re-logging an already-logged file -- the same
// class of problem the deletion-log duplicate-row bug was). Joseph:
// "I don't want to review again those items that are already logged as
// deleted." Filters both duplicate groups (any member already deleted ->
// the whole group's decision already happened, drop it) and singles
// (broken/blurry) against the one real source of truth for "is this
// actually gone" -- the deletion log itself (`getDeletedAssetIds()`), not
// decisions.json, which only tracks *pending* choices.
// Returns both the filtered report (what pendingDeletions() and /api/report
// actually operate on) and the removed items themselves -- Joseph wanted
// visible confirmation of what's already been handled ("I've already
// reviewed and deleted the ones I wanted to delete") rather than those
// items just silently vanishing with no trace. /api/report uses the removed
// lists to surface a per-year "N already deleted" count; pendingDeletions()
// ignores them, it only needs the filtered report.
function filterDeletedFromReport(report, deletedIds) {
  if (deletedIds.size === 0) {
    return { report, removedGroups: [], removedBroken: [], removedBlurry: [] };
  }
  const removedGroups = [];
  const duplicateGroups = report.duplicateGroups.filter((group) => {
    const hit = group.some((m) => deletedIds.has(m.assetId));
    if (hit) removedGroups.push(group);
    return !hit;
  });
  const removedBroken = [];
  const broken = report.broken.filter((item) => {
    const hit = deletedIds.has(item.assetId);
    if (hit) removedBroken.push(item);
    return !hit;
  });
  const removedBlurry = [];
  const blurry = report.blurry.filter((item) => {
    const hit = deletedIds.has(item.assetId);
    if (hit) removedBlurry.push(item);
    return !hit;
  });
  return { report: { ...report, duplicateGroups, broken, blurry }, removedGroups, removedBroken, removedBlurry };
}

// Display-only filtering, separate from filterDeletedFromReport above
// (CARD-0028, Joseph's call, 2026-08-06): a "Keep all" duplicate group has
// no pending action at all -- nothing to delete, nothing to Confirm --
// functionally as resolved as an already-deleted group, so it's hidden the
// same permanent way rather than gated behind the hide-decided toggle
// ("I don't want to see the Keep All decisions"). Singles bulk-dismissed
// via the singles section's own "Mark remaining as reviewed" action are
// hidden the same way -- and permanently, specifically so a later re-scan
// of the same photo doesn't force reviewing it again ("if the batch process
// is rerun, I don't want the ones I've reviewed to show up again"). Only
// used by /api/report (the display layer) -- pendingDeletions() doesn't
// need this: a keepAll group and a dismissed single both already produce
// zero pending deletions on their own (see the existing decision-branch
// logic below), so filtering them out of its input changes nothing there.
function filterResolvedFromReport(report, decisions, dismissedSingleIds) {
  const removedKeepAllGroups = [];
  const duplicateGroups = report.duplicateGroups.filter((group) => {
    const decision = decisions.duplicates[groupKey(group)];
    if (decision && decision.keepAll) {
      removedKeepAllGroups.push(group);
      return false;
    }
    return true;
  });

  const removedDismissedSingles = [];
  function dropDismissed(items) {
    return items.filter((item) => {
      if (dismissedSingleIds.has(item.assetId)) {
        removedDismissedSingles.push(item);
        return false;
      }
      return true;
    });
  }
  const broken = dropDismissed(report.broken);
  const blurry = dropDismissed(report.blurry);

  return { report: { ...report, duplicateGroups, broken, blurry }, removedKeepAllGroups, removedDismissedSingles };
}

// ---------------------------------------------------------------------------
// Build the list of everything currently marked for deletion, shared by both
// /api/preview (read-only) and /api/confirm (actually deletes) so the two
// can never drift apart.
//
// scope (CARD-0028, Joseph's call) narrows this to a specific set of
// groupKeys/assetIds -- the client's current pagination window -- instead
// of every pending decision across the whole library. Found live: paging
// only ever controlled what got *rendered*, not what auto-select could act
// on, so a year with a large backlog could accumulate hundreds of
// auto-selected duplicate picks on pages the reviewer had scrolled past and
// never actually looked at again -- Confirm & Delete would still process
// all of them. Duplicate groups are never split across pages (a group
// renders as one atomic unit client-side), so filtering by groupKey here
// can never produce a partial-group result.
// ---------------------------------------------------------------------------
async function pendingDeletions(scope = null) {
  const rawReport = await loadJson(REPORT_PATH, { duplicateGroups: [], broken: [], blurry: [] });
  const deletedIds = await deletionLog.getDeletedAssetIds();
  const { report } = filterDeletedFromReport(rawReport, deletedIds);
  const decisions = await loadDecisions();
  const pending = [];

  const scopeGroupKeys = scope && Array.isArray(scope.groupKeys) ? new Set(scope.groupKeys) : null;
  const scopeSingleIds = scope && Array.isArray(scope.singleAssetIds) ? new Set(scope.singleAssetIds) : null;

  for (const group of report.duplicateGroups) {
    const key = groupKey(group);
    if (scopeGroupKeys && !scopeGroupKeys.has(key)) continue;
    const decision = decisions.duplicates[key];
    if (!decision || decision.skip) continue;

    // Whole group is bad (e.g. a duplicate pair where neither shot is worth
    // keeping) -- every member goes, no "keep" survivor.
    if (decision.deleteAll) {
      for (const member of group) {
        pending.push({ ...member, reason: 'duplicate group, all marked for deletion', groupKey: key });
      }
      continue;
    }

    if (!decision.keepAssetId) continue;
    const kept = group.find((m) => m.assetId === decision.keepAssetId);
    if (!kept) continue; // stale decision referencing an asset no longer in this group
    // Auto-selected decisions (CARD-0028, Joseph's call) carry their own
    // reason -- surfaced here so Preview Deletions, the actual review/
    // confirm checkpoint for these, explains *why* a copy was picked
    // automatically instead of just stating what happened.
    const reason = decision.auto
      ? `duplicate, kept ${kept.originalFileName} (auto-selected -- ${decision.autoReason})`
      : `duplicate, kept ${kept.originalFileName}`;
    for (const member of group) {
      if (member.assetId === decision.keepAssetId) continue;
      pending.push({ ...member, reason, groupKey: key });
    }
  }

  for (const item of [...report.broken, ...report.blurry]) {
    if (scopeSingleIds && !scopeSingleIds.has(item.assetId)) continue;
    if (decisions.singles[item.assetId] !== 'delete') continue;
    const reason = item.errors
      ? `broken (${Object.keys(item.errors).join(', ')})`
      : `blurry (variance ${item.variance.toFixed(1)})`;
    pending.push({ ...item, reason });
  }

  return pending;
}

// ---------------------------------------------------------------------------
// Express app
// ---------------------------------------------------------------------------
const app = express();
app.use(express.json());
app.use('/public', express.static(path.join(__dirname, 'public')));

app.get('/review', (req, res) => res.sendFile(path.join(__dirname, 'public', 'review.html')));

app.get('/photo/:ownerLabel/:assetId/thumbnail', async (req, res) => {
  try {
    const upstream = await immich.getThumbnailResponse(req.params.assetId, req.params.ownerLabel);
    res.set('Content-Type', upstream.headers.get('content-type') || 'image/jpeg');
    res.send(Buffer.from(await upstream.arrayBuffer()));
  } catch (err) {
    res.status(502).json({ status: 'error', message: err.message });
  }
});

// "Click a thumbnail to see the original" (CARD-0028) -- redirects straight
// to that asset's own page in Immich's existing web UI rather than the
// review app building its own full-resolution viewer. A server-side
// redirect keeps Immich's URL out of client JS, same reasoning as the
// thumbnail proxy above.
//
// Deliberately a *different* env var than IMMICH_SERVER_URL: that one is
// `http://localhost:2283`, correct for this server's own API calls (it runs
// on the M8 itself) but wrong here -- this URL goes into a redirect the
// *browser* follows, and "localhost" in the browser means the reviewer's
// own machine, not the M8. Found live: clicking "View original" tried to
// load Immich from Joseph's own laptop. IMMICH_PUBLIC_URL must be reachable
// from wherever the reviewer's browser actually is (the M8's Tailscale IP,
// since that's how this review app itself is being reached remotely) --
// falls back to IMMICH_SERVER_URL only so this doesn't hard-crash if unset.
app.get('/view/:assetId', (req, res) => {
  const base = process.env.IMMICH_PUBLIC_URL || process.env.IMMICH_SERVER_URL;
  res.redirect(`${base}/photos/${req.params.assetId}`);
});

// Full report, decisions merged in, grouped by year for the landing page.
app.get('/api/report', async (req, res) => {
  const rawReport = await loadJson(REPORT_PATH, { generatedAt: null, duplicateGroups: [], broken: [], blurry: [] });
  const deletedIds = await deletionLog.getDeletedAssetIds();
  const decisions = await loadDecisions();
  const dismissedSingleIds = new Set(decisions.dismissedSingles);

  const stage1 = filterDeletedFromReport(rawReport, deletedIds);
  const stage2 = filterResolvedFromReport(stage1.report, decisions, dismissedSingleIds);
  const report = stage2.report;

  const duplicateGroups = report.duplicateGroups.map((group) => {
    const key = groupKey(group);
    return { groupKey: key, members: group, year: yearOf(group[0]?.fileCreatedAt), decision: decisions.duplicates[key] || null };
  });
  const broken = report.broken.map((item) => ({
    ...item, year: yearOf(item.fileCreatedAt), decision: decisions.singles[item.assetId] || null,
  }));
  const blurry = report.blurry.map((item) => ({
    ...item, year: yearOf(item.fileCreatedAt), decision: decisions.singles[item.assetId] || null,
  }));

  const years = new Set();
  for (const g of duplicateGroups) if (g.year) years.add(g.year);
  for (const b of [...broken, ...blurry]) if (b.year) years.add(b.year);

  // Per-year "already resolved, hidden" counts (CARD-0028, Joseph's call) --
  // deleted/keepAll/dismissed items no longer appear in
  // duplicateGroups/broken/blurry at all, which on its own reads as
  // "nothing left to review" rather than "already handled." Surfaced here
  // so the client can show e.g. "Blurry & Broken (3 -- 12 already deleted,
  // 40 reviewed & dismissed)" instead of already-done work just silently
  // vanishing with no trace.
  const resolvedCounts = {};
  function bump(year, key) {
    if (!year) return;
    if (!resolvedCounts[year]) {
      resolvedCounts[year] = { deletedGroups: 0, deletedSingles: 0, keepAllGroups: 0, dismissedSingles: 0 };
    }
    resolvedCounts[year][key]++;
    years.add(year);
  }
  for (const group of stage1.removedGroups) bump(yearOf(group[0]?.fileCreatedAt), 'deletedGroups');
  for (const item of [...stage1.removedBroken, ...stage1.removedBlurry]) bump(yearOf(item.fileCreatedAt), 'deletedSingles');
  for (const group of stage2.removedKeepAllGroups) bump(yearOf(group[0]?.fileCreatedAt), 'keepAllGroups');
  for (const item of stage2.removedDismissedSingles) bump(yearOf(item.fileCreatedAt), 'dismissedSingles');

  // Per-year count of items that still genuinely need a decision (CARD-0028,
  // Joseph's call: "2026 review for now is done so it seems like the 2026
  // button should be disabled... if we rerun the batch process and more are
  // identified then enable 2026"). A group counts as actionable if it has
  // no decision yet, or was explicitly skipped (skip means "revisit later,"
  // not "done") -- keepAssetId/deleteAll/keepAll are all real decisions,
  // done regardless of whether Confirm & Delete has actually run yet. A
  // single counts as actionable only if untouched (decision is only ever
  // 'delete' or null now -- see /api/decide/single).
  const actionableByYear = {};
  function bumpActionable(year) {
    if (!year) return;
    actionableByYear[year] = (actionableByYear[year] || 0) + 1;
  }
  for (const g of duplicateGroups) {
    if (!g.decision || g.decision.skip) bumpActionable(g.year);
  }
  for (const item of [...broken, ...blurry]) {
    if (!item.decision) bumpActionable(item.year);
  }

  res.json({
    generatedAt: report.generatedAt,
    years: [...years].sort((a, b) => b - a),
    duplicateGroups,
    broken,
    blurry,
    resolvedCounts,
    actionableByYear,
  });
});

app.post('/api/decide/duplicate', async (req, res) => {
  const { groupKey: key, keepAssetId, skip, deleteAll, keepAll, auto, autoReason } = req.body;
  if (!key) return res.status(400).json({ status: 'error', message: 'groupKey required' });
  await withDecisionsLock(async () => {
    const decisions = await loadDecisions();
    decisions.duplicates[key] = skip
      ? { skip: true }
      : deleteAll
      ? { deleteAll: true }
      // keepAll is a real, deliberate decision (both/all copies are worth
      // keeping) -- distinct from skip, which means "haven't decided yet,
      // revisit later." Joseph hit a real case where neither picking one
      // member nor deferring the whole group fit: he'd looked and genuinely
      // wanted both kept. pendingDeletions() needs no new branch for this --
      // it already falls through to "nothing pending" for any decision with
      // no keepAssetId and no deleteAll, same as it always has.
      : keepAll
      ? { keepAll: true }
      : auto
      ? { keepAssetId, auto: true, autoReason }
      : { keepAssetId };
    await saveDecisions(decisions);
  });
  res.json({ status: 'ok' });
});

// Simplified (Joseph's call, 2026-08-06): singles used to support 'keep' as
// a distinct saved decision, but that forced clicking "keep" on every item
// you *didn't* want to delete -- unnecessary, since pendingDeletions() only
// ever queues assets explicitly marked 'delete'; anything untouched was
// already effectively "kept." decision is now just 'delete' or null
// (clears back to unmarked/undecided) -- 'keep' is still accepted so any
// pre-existing 'keep' entries from before this change don't 400 if the
// client ever re-sends one, but the UI itself no longer generates it.
app.post('/api/decide/single', async (req, res) => {
  const { assetId, decision } = req.body;
  if (!assetId || ![null, 'keep', 'delete'].includes(decision)) {
    return res.status(400).json({ status: 'error', message: 'assetId and decision (delete|null) required' });
  }
  await withDecisionsLock(async () => {
    const decisions = await loadDecisions();
    if (decision === null) delete decisions.singles[assetId];
    else decisions.singles[assetId] = decision;
    await saveDecisions(decisions);
  });
  res.json({ status: 'ok' });
});

// Bulk-dismiss (CARD-0028, Joseph's call, 2026-08-06): "I don't want to
// mark the ones to keep, only the ones to delete... if the batch process is
// rerun, I don't want the ones I've reviewed to show up again." Takes
// whatever assetIds the client says are currently visible-and-undecided in
// a section and adds them to decisions.dismissedSingles, filtered out of
// /api/report from here on (see filterResolvedFromReport) -- permanently,
// including across a future re-scan, since the whole point is not
// re-reviewing the same photo just because report.json regenerated.
//
// Progress-tracked the same way /api/confirm is (Joseph's call): a "mark all
// remaining as reviewed" click on a year with a large backlog can cover
// hundreds/thousands of assetIds at once, and with no feedback that reads
// exactly like the pre-fix Confirm & Delete hang. The actual decisions.json
// write still happens once, atomically, at the end (same lock discipline as
// every other decisions.json writer) -- only the in-memory Set-building loop
// yields periodically so a client polling /api/dismiss-singles/progress can
// observe real intermediate counts on a large batch.
let dismissInProgress = false;
let dismissProgress = { total: 0, completed: 0 };
const DISMISS_YIELD_EVERY = 200;

app.get('/api/dismiss-singles/progress', (req, res) => {
  res.json({ inProgress: dismissInProgress, total: dismissProgress.total, completed: dismissProgress.completed });
});

app.post('/api/dismiss-singles', async (req, res) => {
  const { assetIds } = req.body;
  if (!Array.isArray(assetIds) || assetIds.length === 0) {
    return res.status(400).json({ status: 'error', message: 'assetIds (non-empty array) required' });
  }
  if (dismissInProgress) {
    return res.status(409).json({
      status: 'error',
      message: 'A dismiss operation is already in progress -- please wait for it to finish.',
    });
  }
  dismissInProgress = true;
  dismissProgress = { total: assetIds.length, completed: 0 };
  try {
    await withDecisionsLock(async () => {
      const decisions = await loadDecisions();
      const existing = new Set(decisions.dismissedSingles);
      for (let i = 0; i < assetIds.length; i++) {
        existing.add(assetIds[i]);
        dismissProgress.completed = i + 1;
        if (i % DISMISS_YIELD_EVERY === 0) await new Promise((resolve) => setImmediate(resolve));
      }
      decisions.dismissedSingles = [...existing];
      await saveDecisions(decisions);
    });
    res.json({ status: 'ok', dismissedCount: assetIds.length });
  } finally {
    dismissInProgress = false;
  }
});

// Album membership for one asset (CARD-0028) -- fetched on demand as
// duplicate groups are rendered, not baked into report.json (see immich.js's
// getAlbumsForAsset for why). ownerLabel comes from the report data the
// client already has for this asset, same as the thumbnail proxy above.
app.get('/api/albums/:assetId', async (req, res) => {
  const { ownerLabel } = req.query;
  if (!ownerLabel) return res.status(400).json({ status: 'error', message: 'ownerLabel required' });
  try {
    const albums = await immich.getAlbumsForAsset(req.params.assetId, ownerLabel);
    res.json({ albums });
  } catch (err) {
    res.status(502).json({ status: 'error', message: err.message });
  }
});

// Motion Photo video-integrity check for one asset (CARD-0028) -- fetched
// on demand alongside album membership, same reasoning: too many assets to
// check every duplicate group's every member up front, most groups never
// get reviewed. Non-Motion-Photo assets resolve fast (isMotionPhoto: false,
// no ffprobe call at all).
app.get('/api/motion-check/:assetId', async (req, res) => {
  const { ownerLabel } = req.query;
  if (!ownerLabel) return res.status(400).json({ status: 'error', message: 'ownerLabel required' });
  try {
    const result = await immich.checkMotionPhotoValidity(req.params.assetId, ownerLabel);
    res.json(result);
  } catch (err) {
    res.status(502).json({ status: 'error', message: err.message });
  }
});

// Dry-run: exact list of what /api/confirm would delete right now, without
// deleting anything -- the "last sanity check" step from CARD-0028's plan.
// POST (not GET) so the client can carry a scope in the body -- see
// pendingDeletions()'s own comment for why this is scoped at all.
app.post('/api/preview', async (req, res) => {
  res.json({ items: await pendingDeletions(req.body && req.body.scope) });
});

// Page-scoped commit (CARD-0028, revised from the original session-wide
// design after Joseph found that design let Confirm & Delete act on
// auto-selected decisions from pages he hadn't actually looked at during
// this visit -- see pendingDeletions()'s own comment). Still not gated by
// the year picker itself; the *pagination window* is the boundary now, not
// the year.
// In-flight guard (CARD-0028) -- found live: with no feedback while a real
// delete pass was running, Joseph clicked Confirm & Delete repeatedly, and
// each click ran its own full pendingDeletions()-then-delete-then-log pass.
// Immich's own delete API doesn't error on an asset that's already trashed,
// so nothing broke there -- but deletionLog.logDeletion() has no dedup logic
// at all, so every repeat pass re-logged the same files: 275 real log rows
// covering only 55 actual deletions (5x each), confirmed directly against
// the CSV. The client now disables the button while a request is in
// flight, but this guard is the real backstop -- it also covers a second
// browser tab or any other path that could fire a concurrent request.
// CARD-0148: simple concurrency-limited map, same small self-contained
// pattern scan.js's own mapWithConcurrency already uses (no shared module,
// no build step) -- a safety margin for the delete loop below now that
// deletionLog.logDeletion() no longer blocks on the slow leg per item (see
// that module's own comment), not because Immich itself is slow.
async function mapWithConcurrency(items, limit, fn) {
  const results = new Array(items.length);
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const i = next++;
      results[i] = await fn(items[i], i);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}
const CONFIRM_CONCURRENCY = 5;

let confirmInProgress = false;

// Live progress (CARD-0028) -- a static "please wait" message wasn't
// convincing enough on a real ~100-item batch that took minutes: Joseph
// couldn't tell the button-disabled state apart from a genuine hang.
// Polled by the client every second while a confirm is running; this
// module-level object is intentionally simple (one delete pass runs at a
// time, guarded by confirmInProgress above, so there's no concurrent-writer
// risk the way decisions.json had).
let confirmProgress = { total: 0, completed: 0 };

app.get('/api/confirm/progress', (req, res) => {
  res.json({ inProgress: confirmInProgress, total: confirmProgress.total, completed: confirmProgress.completed });
});

app.post('/api/confirm', async (req, res) => {
  if (confirmInProgress) {
    return res.status(409).json({
      status: 'error',
      message: 'A delete is already in progress -- please wait for it to finish.',
    });
  }
  confirmInProgress = true;
  confirmProgress = { total: 0, completed: 0 };
  try {
    const items = await pendingDeletions(req.body && req.body.scope);
    confirmProgress.total = items.length;
    const deletedItems = [];
    const failed = [];

    // The delete loop itself (real Immich API calls, one per item -- can
    // legitimately take a while) runs outside the decisions lock. Earlier
    // version of this handler loaded decisions.json once up front, held
    // that in-memory copy across the whole loop, and only wrote it back at
    // the end -- which has the exact same lost-write shape as the bug just
    // fixed on /api/decide/*: any decide-call whose own load+mutate+save
    // completed *during* this loop would get silently erased when this
    // handler's final save overwrote decisions.json with its now-stale
    // snapshot. Fixed by never holding a long-lived copy across the loop --
    // only track which items actually got deleted here, then do one
    // fresh-load-and-targeted-removal at the very end, fully inside the
    // lock.
    // CARD-0148: bounded concurrency (was a plain sequential for-loop) --
    // deletedItems.push/failed.push/confirmProgress.completed++ are all
    // safe here despite running from multiple concurrent workers: Node has
    // no true parallelism, only interleaving at await points, so each of
    // these synchronous operations completes atomically between them.
    await mapWithConcurrency(items, CONFIRM_CONCURRENCY, async (item) => {
      try {
        await immich.deleteAsset(item.assetId, item.ownerLabel);
        await deletionLog.logDeletion({
          originalFileName: item.originalFileName,
          fileCreatedAt: item.fileCreatedAt,
          assetId: item.assetId,
          ownerLabel: item.ownerLabel,
          reason: item.reason,
        });
        deletedItems.push(item);
      } catch (err) {
        failed.push({ assetId: item.assetId, error: err.message });
      } finally {
        confirmProgress.completed++;
      }
    });

    await withDecisionsLock(async () => {
      const decisions = await loadDecisions();
      // Retire each actually-deleted asset from decisions.json now that
      // it's really gone -- the deletion-log CSV/Sheet is the permanent
      // record from here on. Loaded fresh right here, under the lock, so
      // this can't clobber a decision saved by any other request while the
      // delete loop above was running.
      for (const item of deletedItems) {
        if (item.groupKey) {
          delete decisions.duplicates[item.groupKey]; // whole group is resolved once its non-kept members are deleted
        } else {
          delete decisions.singles[item.assetId];
        }
      }
      await saveDecisions(decisions);
    });

    res.json({ status: 'ok', deletedCount: deletedItems.length, failed });
  } finally {
    confirmInProgress = false;
  }
});

app.listen(PORT, () => {
  console.log(`photo-quality-review listening on :${PORT}`);
});
