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
//   duplicates: { [groupKey]: { keepAssetId } | { skip: true } }
//     groupKey is the sorted, joined assetIds of the group -- stable across
//     re-scans even if czkawka returns groups in a different order.
//   singles: { [assetId]: 'keep' | 'delete' }
// ---------------------------------------------------------------------------
async function loadJson(filePath, fallback) {
  try {
    return JSON.parse(await fs.readFile(filePath, 'utf-8'));
  } catch {
    return fallback;
  }
}

async function loadDecisions() {
  return loadJson(DECISIONS_PATH, { duplicates: {}, singles: {} });
}

async function saveDecisions(decisions) {
  await fs.mkdir(DATA_DIR, { recursive: true });
  await fs.writeFile(DECISIONS_PATH, JSON.stringify(decisions, null, 2));
}

function groupKey(group) {
  return group.map((m) => m.assetId).sort().join(',');
}

function yearOf(isoDate) {
  return isoDate ? new Date(isoDate).getFullYear() : null;
}

// ---------------------------------------------------------------------------
// Build the list of everything currently marked for deletion, shared by both
// /api/preview (read-only) and /api/confirm (actually deletes) so the two
// can never drift apart.
// ---------------------------------------------------------------------------
async function pendingDeletions() {
  const report = await loadJson(REPORT_PATH, { duplicateGroups: [], broken: [], blurry: [] });
  const decisions = await loadDecisions();
  const pending = [];

  for (const group of report.duplicateGroups) {
    const key = groupKey(group);
    const decision = decisions.duplicates[key];
    if (!decision || decision.skip || !decision.keepAssetId) continue;
    const kept = group.find((m) => m.assetId === decision.keepAssetId);
    if (!kept) continue; // stale decision referencing an asset no longer in this group
    for (const member of group) {
      if (member.assetId === decision.keepAssetId) continue;
      pending.push({ ...member, reason: `duplicate, kept ${kept.originalFileName}`, groupKey: key });
    }
  }

  for (const item of [...report.broken, ...report.blurry]) {
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
// redirect keeps IMMICH_SERVER_URL out of client JS, same reasoning as the
// thumbnail proxy above.
app.get('/view/:assetId', (req, res) => {
  res.redirect(`${process.env.IMMICH_SERVER_URL}/photos/${req.params.assetId}`);
});

// Full report, decisions merged in, grouped by year for the landing page.
app.get('/api/report', async (req, res) => {
  const report = await loadJson(REPORT_PATH, { generatedAt: null, duplicateGroups: [], broken: [], blurry: [] });
  const decisions = await loadDecisions();

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

  res.json({
    generatedAt: report.generatedAt,
    years: [...years].sort((a, b) => b - a),
    duplicateGroups,
    broken,
    blurry,
  });
});

app.post('/api/decide/duplicate', async (req, res) => {
  const { groupKey: key, keepAssetId, skip } = req.body;
  if (!key) return res.status(400).json({ status: 'error', message: 'groupKey required' });
  const decisions = await loadDecisions();
  decisions.duplicates[key] = skip ? { skip: true } : { keepAssetId };
  await saveDecisions(decisions);
  res.json({ status: 'ok' });
});

app.post('/api/decide/single', async (req, res) => {
  const { assetId, decision } = req.body;
  if (!assetId || !['keep', 'delete'].includes(decision)) {
    return res.status(400).json({ status: 'error', message: 'assetId and decision (keep|delete) required' });
  }
  const decisions = await loadDecisions();
  decisions.singles[assetId] = decision;
  await saveDecisions(decisions);
  res.json({ status: 'ok' });
});

// Dry-run: exact list of what /api/confirm would delete right now, without
// deleting anything -- the "last sanity check" step from CARD-0028's plan.
app.get('/api/preview', async (req, res) => {
  res.json({ items: await pendingDeletions() });
});

// Session-oriented commit (CARD-0028, Joseph's correction): deletes and logs
// whatever is currently marked, regardless of which year(s) it spans or
// whether a full year was finished -- the year picker is a browsing aid
// only, never a gate on this step.
app.post('/api/confirm', async (req, res) => {
  const items = await pendingDeletions();
  const decisions = await loadDecisions();
  const deleted = [];
  const failed = [];

  for (const item of items) {
    try {
      await immich.deleteAsset(item.assetId, item.ownerLabel);
      await deletionLog.logDeletion({
        originalFileName: item.originalFileName,
        fileCreatedAt: item.fileCreatedAt,
        assetId: item.assetId,
        ownerLabel: item.ownerLabel,
        reason: item.reason,
      });
      deleted.push(item.assetId);

      // Retire this asset from decisions.json now that it's actually gone --
      // the deletion-log CSV/Sheet is the permanent record from here on.
      if (item.groupKey) {
        const group = decisions.duplicates[item.groupKey];
        if (group) delete decisions.duplicates[item.groupKey]; // whole group is resolved once its non-kept members are deleted
      } else {
        delete decisions.singles[item.assetId];
      }
    } catch (err) {
      failed.push({ assetId: item.assetId, error: err.message });
    }
  }

  await saveDecisions(decisions);
  res.json({ status: 'ok', deletedCount: deleted.length, failed });
});

app.listen(PORT, () => {
  console.log(`photo-quality-review listening on :${PORT}`);
});
