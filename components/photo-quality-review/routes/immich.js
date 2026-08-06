// Immich API integration for photo-quality-review (CARD-0028).
//
// Verified against the real M8 Immich instance (v3.1.0) directly, same
// discipline photo-tv-display's own routes/immich.js used -- confirmed live
// rather than assumed:
//   - Every asset object exposes both `originalPath` (e.g.
//     "/data/upload/<ownerId>/b1/06/<uuid>.jpg") and `checksum`.
//     `/data` is the Immich container's mount point for `UPLOAD_LOCATION`
//     (confirmed directly from ~/immich-app/.env and docker-compose.yml on
//     the M8: `UPLOAD_LOCATION=/mnt/photo-library`), so a flagged file's
//     real host path maps to its Immich asset purely by string substitution
//     -- no checksum computation or per-file API call needed.
//   - `/search/metadata` paginates via `page`/`assets.nextPage`, max `size`
//     1000 per page (confirmed live -- requesting size:1000 still returned
//     nextPage: 2 immediately).
//   - Two accounts (Joseph's, Robin's) are queried separately with their own
//     API keys and merged client-side -- same reasoning as photo-tv-display:
//     there is no single-key "both users" filter.
//   - Delete uses Immich's own trash (force: false), same free safety net
//     photo-tv-display's deleteAsset() already established.

const { execFile } = require('child_process');
const { promisify } = require('util');
const execFileAsync = promisify(execFile);

const UPLOAD_CONTAINER_PREFIX = '/data';
const UPLOAD_HOST_PREFIX = '/mnt/photo-library';
const PAGE_SIZE = 1000;

const BASE_URL = `${process.env.IMMICH_SERVER_URL}/api`;

const ACCOUNTS = {
  joseph: process.env.IMMICH_API_KEY_JOSEPH,
  robin: process.env.IMMICH_API_KEY_ROBIN,
};

async function immichFetch(apiKey, path, { method = 'GET', body } = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      'x-api-key': apiKey,
      'Content-Type': 'application/json',
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Immich ${method} ${path} failed: ${res.status} ${text}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

function containerPathToHostPath(originalPath) {
  if (!originalPath.startsWith(UPLOAD_CONTAINER_PREFIX)) return null;
  return UPLOAD_HOST_PREFIX + originalPath.slice(UPLOAD_CONTAINER_PREFIX.length);
}

// Pages through every asset for one account and returns
// { [hostPath]: { assetId, ownerLabel, fileCreatedAt, originalFileName } }.
// Scoped to visibility:'timeline' -- matches photo-tv-display's own default
// (excludes archived/hidden/locked), which is also the set of photos
// actually worth reviewing for quality issues.
async function buildPathIndexForAccount(ownerLabel) {
  const apiKey = ACCOUNTS[ownerLabel];
  const index = {};
  let page = 1;
  for (;;) {
    const res = await immichFetch(apiKey, '/search/metadata', {
      method: 'POST',
      body: { visibility: 'timeline', size: PAGE_SIZE, page },
    });
    for (const asset of res.assets.items) {
      const hostPath = containerPathToHostPath(asset.originalPath);
      if (!hostPath) continue; // defensive -- unexpected path shape, skip rather than crash
      index[hostPath] = {
        assetId: asset.id,
        ownerLabel,
        fileCreatedAt: asset.fileCreatedAt,
        originalFileName: asset.originalFileName,
      };
    }
    if (!res.assets.nextPage) break;
    page = Number(res.assets.nextPage);
  }
  return index;
}

// Full cross-account index: { [hostPath]: { assetId, ownerLabel,
// fileCreatedAt, originalFileName } }. This is what makes cross-library
// dedup free -- czkawka already scanned both accounts' files in one pass
// (it doesn't know or care about the ownerId split), so resolving each
// flagged path just needs one merged lookup table.
async function buildPathIndex() {
  const [josephIndex, robinIndex] = await Promise.all([
    buildPathIndexForAccount('joseph'),
    buildPathIndexForAccount('robin'),
  ]);
  return { ...josephIndex, ...robinIndex };
}

// Which album(s), if any, an asset belongs to (CARD-0028). Fetched lazily
// per-asset when a duplicate group is actually viewed, not baked into
// report.json at scan time -- doing this for all ~95k duplicate-group
// members up front would mean that many extra Immich API calls on every
// report rebuild, for data most groups will never be reviewed. This turned
// out to be a real, independent signal for which copy to keep, not just a
// nice-to-have: a real 4-copy duplicate had 2 members in an album and 2
// with no album at all, and the "cleanest" filename was one of the
// album-less ones -- picking by filename/size alone would have kept the
// wrong copy and silently dropped the photo from its trip album once
// Immich's trash retention (30 days, confirmed via /api/system-config)
// expired.
async function getAlbumsForAsset(assetId, ownerLabel) {
  const key = ACCOUNTS[ownerLabel];
  const albums = await immichFetch(key, `/albums?assetId=${assetId}`);
  return albums.map((a) => a.albumName);
}

// Motion Photo video-integrity check (CARD-0028). czkawka's duplicate
// detection only ever compares the still frame's visual hash -- it has no
// idea a Motion Photo (.MP.jpg) even has an embedded video clip, let alone
// whether that clip still plays. Found live: two duplicate copies of the
// same still had identical-looking frames, but one's linked video was
// corrupted (`moov atom not found`, unplayable) -- picking "keep the
// smaller one" or eyeballing the still alone would have kept the broken
// copy and lost the working motion clip.
//
// No ffprobe/ffmpeg installed on the bare M8 host -- reuses the copy
// already inside the immich_server container via `docker exec` rather than
// adding a new host dependency for one narrow check. Safe against injection
// even though `video.originalPath` flows into a shelled-out command:
// execFile (not exec) never invokes a shell, and the path itself comes from
// Immich's own API response, not from user input.
async function checkMotionPhotoValidity(assetId, ownerLabel) {
  const key = ACCOUNTS[ownerLabel];
  const asset = await immichFetch(key, `/assets/${assetId}`);
  if (!asset.livePhotoVideoId) return { isMotionPhoto: false };

  const video = await immichFetch(key, `/assets/${asset.livePhotoVideoId}`);
  try {
    await execFileAsync('docker', [
      'exec', 'immich_server', 'ffprobe', '-v', 'error',
      '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1',
      video.originalPath,
    ]);
    return { isMotionPhoto: true, valid: true };
  } catch {
    return { isMotionPhoto: true, valid: false };
  }
}

// force: false -> moves to Immich's own trash (recoverable within its
// retention window), same convention as photo-tv-display's deleteAsset().
async function deleteAsset(assetId, ownerLabel) {
  const key = ACCOUNTS[ownerLabel];
  await immichFetch(key, '/assets', {
    method: 'DELETE',
    body: { ids: [assetId], force: false },
  });
}

// Raw thumbnail bytes proxy -- browsers can't attach x-api-key to a plain
// <img src>, so the server fetches with the owning account's key and
// streams the response through. Only 'thumbnail' is needed here -- viewing
// the full original happens by deep-linking to Immich's own web UI instead
// of proxying it ourselves (Joseph's/Claude's design call, CARD-0028).
async function getThumbnailResponse(assetId, ownerLabel) {
  const key = ACCOUNTS[ownerLabel];
  const res = await fetch(`${BASE_URL}/assets/${assetId}/thumbnail?size=preview`, {
    headers: { 'x-api-key': key },
  });
  if (!res.ok) throw new Error(`Immich thumbnail fetch failed: ${res.status}`);
  return res;
}

module.exports = {
  ACCOUNTS,
  buildPathIndex,
  deleteAsset,
  getThumbnailResponse,
  getAlbumsForAsset,
  checkMotionPhotoValidity,
};
