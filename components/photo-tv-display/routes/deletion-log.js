// Deletion logging for photo-tv-display.
//
// Local CSV file is the primary, persistent record (per Phase 1/2 planning --
// survives regardless of network state). The Google Sheet is a secondary,
// best-effort copy for browsing/manual Google Photos cleanup from any device;
// its failure must never block or roll back an already-confirmed Immich delete.

const fs = require('fs/promises');
const path = require('path');

const CSV_PATH = process.env.DELETION_LOG_LOCAL_PATH;
const APPS_SCRIPT_URL = process.env.DELETION_LOG_SHEET_APPS_SCRIPT_URL;
const APPS_SCRIPT_KEY = process.env.DELETION_LOG_SHEET_APPS_SCRIPT_KEY;

const CSV_HEADER = 'timestamp,filename,date_taken,album_folder,immich_asset_id,deleted_by\n';

function csvField(value) {
  const s = value === null || value === undefined ? '' : String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
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

// assetMetadata: the AssetResponseDto-shaped object for the deleted asset
// (needs originalFileName, fileCreatedAt, ownerLabel at minimum).
// albumFolder: best-known album/folder name at time of delete, or '' if none.
// deletedBy: 'joseph' | 'robin'.
async function logDeletion(assetMetadata, albumFolder, deletedBy) {
  const record = {
    timestamp: new Date().toISOString(),
    filename: assetMetadata.originalFileName,
    date_taken: assetMetadata.fileCreatedAt,
    album_folder: albumFolder || '',
    immich_asset_id: assetMetadata.id,
    deleted_by: deletedBy,
  };

  await appendLocalCsv(record);

  try {
    await postToSheet(record);
  } catch (err) {
    console.warn('Deletion log: Google Sheet POST failed (local CSV row already written):', err.message);
  }
}

module.exports = { logDeletion };
