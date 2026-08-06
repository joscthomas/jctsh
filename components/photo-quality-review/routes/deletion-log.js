// Deletion logging for photo-quality-review (CARD-0028).
//
// Deliberately points at the *same* CSV file and Apps Script deployment
// photo-tv-display's routes/deletion-log.js already writes to (same env var
// names, same .env values) -- this is what makes the CARD-0028 interview's
// "standing Google Photos manual-groom list" a single converged record
// rather than a second, separate list. Local CSV is the primary, persistent
// record; the Google Sheet is a secondary best-effort copy for browsing from
// any device. A Sheet POST failure must never block or roll back an
// already-confirmed Immich delete.
//
// `album_folder` is repurposed here as a short human-readable reason
// ("duplicate, kept <filename>" / "blurry" / "broken") -- confirmed safe by
// reading the deployed Apps Script (components/photo-tv-display/apps-script.gs):
// it's a plain pass-through column with no schema validation on content.

const fs = require('fs/promises');

const CSV_PATH = process.env.DELETION_LOG_LOCAL_PATH;
const APPS_SCRIPT_URL = process.env.DELETION_LOG_SHEET_APPS_SCRIPT_URL;
const APPS_SCRIPT_KEY = process.env.DELETION_LOG_SHEET_APPS_SCRIPT_KEY;

const CSV_HEADER = 'timestamp,filename,date_taken,album_folder,immich_asset_id,deleted_by\n';

function csvField(value) {
  const s = value === null || value === undefined ? '' : String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

// Minimal quoted-field-aware CSV line parser -- `album_folder`/reason values
// can contain commas (e.g. "duplicate, kept X.jpg"), which csvField() above
// already quotes on write; this is the matching read-side parse, not a
// general CSV library.
function parseCsvLine(line) {
  const row = [];
  let cur = '';
  let inQuotes = false;
  for (const ch of line) {
    if (ch === '"') inQuotes = !inQuotes;
    else if (ch === ',' && !inQuotes) {
      row.push(cur);
      cur = '';
    } else {
      cur += ch;
    }
  }
  row.push(cur);
  return row;
}

// Every asset ID that's already been deleted and logged (CARD-0028) --
// lets the review UI filter out groups/items that reference an already-gone
// asset, rather than presenting them for review again. Found the need for
// this live: after the decisions.json race-condition fix + cleanup, Joseph
// didn't want to see groups whose members are already logged as deleted
// re-appear as if undecided. report.json is a static scan snapshot that has
// no idea an asset was later deleted, so this check has to happen at
// request time against the one source of truth for "is this actually
// gone" -- the deletion log itself, not decisions.json (which only tracks
// pending choices, and gets an entry *removed*, not added, once deleted).
async function getDeletedAssetIds() {
  let raw;
  try {
    raw = await fs.readFile(CSV_PATH, 'utf-8');
  } catch {
    return new Set(); // no log yet -- nothing has been deleted
  }
  const lines = raw.trim().split('\n');
  if (lines.length < 2) return new Set();
  const header = parseCsvLine(lines[0]);
  const idCol = header.indexOf('immich_asset_id');
  if (idCol === -1) return new Set();
  const ids = new Set();
  for (let i = 1; i < lines.length; i++) {
    const row = parseCsvLine(lines[i]);
    if (row[idCol]) ids.add(row[idCol]);
  }
  return ids;
}

async function appendLocalCsv(record) {
  try {
    await fs.access(CSV_PATH);
  } catch {
    await fs.writeFile(CSV_PATH, CSV_HEADER);
  }
  const row = [
    record.timestamp,
    record.filename,
    record.date_taken,
    record.album_folder,
    record.immich_asset_id,
    record.deleted_by,
  ]
    .map(csvField)
    .join(',');
  await fs.appendFile(CSV_PATH, row + '\n');
}

async function postToSheet(record) {
  const url = new URL(APPS_SCRIPT_URL);
  url.searchParams.set('key', APPS_SCRIPT_KEY);
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(record),
  });
  if (!res.ok) {
    throw new Error(`Apps Script POST failed: ${res.status}`);
  }
}

// originalFileName/fileCreatedAt/assetId/ownerLabel come from the same
// per-asset info already carried through the path index (routes/immich.js).
async function logDeletion({ originalFileName, fileCreatedAt, assetId, ownerLabel, reason }) {
  const record = {
    timestamp: new Date().toISOString(),
    filename: originalFileName,
    date_taken: fileCreatedAt,
    album_folder: reason,
    immich_asset_id: assetId,
    deleted_by: ownerLabel,
  };

  await appendLocalCsv(record);

  try {
    await postToSheet(record);
  } catch (err) {
    console.warn('Deletion log: Google Sheet POST failed (local CSV row already written):', err.message);
  }
}

module.exports = { logDeletion, getDeletedAssetIds };
