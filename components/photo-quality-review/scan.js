#!/usr/bin/env node
// CARD-0028: batch scan job -- run manually (or via a periodic timer) on the
// M8, not on every page load. Produces data/report.json for server.js to
// serve. Three passes over /mnt/photo-library/upload/ (both accounts' files
// in one tree, per routes/immich.js's own header comment on why that makes
// cross-library dedup free):
//   1. czkawka `image` -- near-duplicate groups (perceptual hash). Has its
//      own built-in cache (confirmed live: a second run against the same
//      files loads/re-saves cache entries instead of re-hashing), so
//      re-scans are naturally incremental for this pass.
//   2. czkawka `broken -c IMAGE` -- corrupted/unreadable image files.
//   3. A hand-rolled Laplacian-variance blur pass via `sharp` -- czkawka has
//      no blur detector at all (checked its real --help output; only `image`
//      and `broken` exist), so this fills that gap the same way the card's
//      original research flagged as a fallback. No built-in cache like
//      czkawka's, so this pass keeps its own mtime-keyed cache
//      (data/blur-cache.json) to make re-scans incremental too.
//
// Every flagged file's host path is then resolved to its Immich asset (via
// routes/immich.js's buildPathIndex()) before being written to report.json
// -- server.js should never need to touch the filesystem or recompute this.

require('dotenv').config();

const { execFile } = require('child_process');
const fs = require('fs/promises');
const path = require('path');
const sharp = require('sharp');

const immich = require('./routes/immich');
const notify = require('./routes/notify');

const UPLOAD_ROOT = process.env.PHOTO_LIBRARY_UPLOAD_ROOT || '/mnt/photo-library/upload';
const CZKAWKA_CLI_PATH = process.env.CZKAWKA_CLI_PATH;
const DATA_DIR = process.env.PHOTO_QUALITY_REVIEW_DATA_DIR || path.join(__dirname, 'data');

const REPORT_PATH = path.join(DATA_DIR, 'report.json');
const REPORT_HISTORY_DIR = path.join(DATA_DIR, 'report-history');
const BLUR_CACHE_PATH = path.join(DATA_DIR, 'blur-cache.json');

// CARD-0149: report.json used to just get overwritten on every rescan --
// no way to tell "did this scan find more than last time" without keeping
// something to compare against (Joseph asked exactly that after a real
// rescan notification). Archives the *previous* report before the new one
// lands, named from that report's own generatedAt (when it was actually
// produced, not "now" -- "now" is just when it's being retired). A plain
// fs.rename, not a copy: report.json and report-history/ are both under
// DATA_DIR, so this is a same-filesystem move, no need to duplicate a
// ~36MB file on disk just to relocate it. Deliberately no pruning here --
// see this card's own kanban entry for why that's left for later rather
// than guessed at now. Comparison/diffing what changed between snapshots
// is also explicitly out of scope for this card -- this only makes sure
// the data to compare exists.
async function archivePreviousReport() {
  let raw;
  try {
    raw = await fs.readFile(REPORT_PATH, 'utf-8');
  } catch {
    return; // first-ever scan -- nothing to archive yet
  }
  let generatedAt;
  try {
    generatedAt = JSON.parse(raw).generatedAt;
  } catch {
    generatedAt = null; // malformed/older report -- still worth keeping a copy
  }
  const stamp = (generatedAt || new Date().toISOString()).replace(/:/g, '-');
  await fs.mkdir(REPORT_HISTORY_DIR, { recursive: true });
  await fs.rename(REPORT_PATH, path.join(REPORT_HISTORY_DIR, `report-${stamp}.json`));
}

// CARD-0028: initial estimate from one synthetic test (a real in-focus
// photo scored ~720, the same photo with a heavy 15px gaussian blur applied
// scored ~8.2) -- not calibrated against a real spread of genuine sharp vs.
// blurry photos yet. Expect to revisit after the first real review session
// shows how well this threshold actually separates the two in practice.
const BLUR_VARIANCE_THRESHOLD = 50;

// CARD-0028 build finding: lowered from an initial 8 after a real run showed
// concurrent reads against /mnt/photo-library's spinning HDD self-thrash
// (each of the 8 workers seeking to a different, unrelated file at once) --
// a lower value trades some of the convolution step's own parallelizability
// for less randomized disk access, which dominates on this hardware.
const BLUR_CONCURRENCY = 2;
const IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp', '.tiff', '.gif']);

function log(msg) {
  console.error(`[scan] ${msg}`);
}

// CARD-0028 build fix: the first real full-library run showed this needs to
// be genuinely non-blocking, not just async-flavored -- execFileSync (the
// original implementation) freezes Node's single-threaded event loop for
// the entire subprocess lifetime, which also blocks Node's own signal
// handling until the subprocess exits (a killed parent can't clean up its
// child while frozen inside a sync call). The three passes below now run
// sequentially anyway (see main()'s own comment -- concurrent passes
// thrash a spinning disk rather than genuinely parallelizing), so the
// original motivation for switching off execFileSync (letting them
// interleave) no longer applies -- but the non-blocking property is still
// what makes clean shutdown possible. Using execFile's raw callback form
// (not the promisified wrapper) so the ChildProcess handle itself can be
// tracked in activeChildren -- confirmed live the hard way: killing the
// parent `node scan.js` process (e.g. `pkill -f 'node scan.js'`) does NOT
// kill an already-spawned execFileSync/execFile child on its own, and a
// real orphaned czkawka_cli process was found still running a full-tree
// scan minutes after its parent had been killed, silently competing for
// disk/CPU with a later, unrelated run. SIGINT/SIGTERM handlers below kill
// every tracked child before the process exits -- but this only helps
// against a *graceful* kill; `kill -9`/SIGKILL can't be caught by anything,
// so a forceful stop should still use plain `kill`/`pkill`, not `-9`, to
// let this cleanup actually run.
//
// -M (suppress info/warning messages, on top of -N which already suppresses
// result printing) matters for the same reason maxBuffer is raised well
// past its 1MB default -- without it, czkawka's own progress chatter over a
// 200k+-file scan risks exceeding execFile's buffered-output limit and
// failing the whole call; -N alone wasn't enough, confirmed only after
// switching off execFileSync exposed how much output czkawka actually still
// emits.
const activeChildren = new Set();

function runCzkawka(args) {
  return new Promise((resolve) => {
    const child = execFile(CZKAWKA_CLI_PATH, args, { maxBuffer: 100 * 1024 * 1024 }, () => {
      // czkawka exits non-zero when it *finds* results (confirmed live --
      // exit code 11 on a real duplicate match) -- not a failure. A genuine
      // crash (bad binary, bad args) would still have failed to write the
      // output file at all, which the caller catches separately when
      // reading it back, so any exec error here is deliberately swallowed.
      activeChildren.delete(child);
      resolve();
    });
    activeChildren.add(child);
  });
}

function killActiveChildren(signal) {
  for (const child of activeChildren) {
    try {
      child.kill(signal);
    } catch {
      // already exited -- nothing to do
    }
  }
}

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    log(`Received ${signal} -- killing ${activeChildren.size} active czkawka subprocess(es)...`);
    killActiveChildren('SIGKILL');
    process.exit(signal === 'SIGINT' ? 130 : 143);
  });
}

async function scanDuplicates() {
  const outPath = path.join(DATA_DIR, '_czkawka_image.json');
  log('Running czkawka image (near-duplicate) scan...');
  await runCzkawka(['image', '-d', UPLOAD_ROOT, '-p', outPath, '-N', '-M']);
  const raw = await fs.readFile(outPath, 'utf-8');
  const groups = JSON.parse(raw); // [[{path, size, width, height, modified_date, difference}, ...], ...]
  log(`  found ${groups.length} duplicate group(s)`);
  // Keep every field czkawka gives us, not just path -- these files are
  // frequently the *same original filename* re-saved/re-exported (burst
  // shots, edits), so size/dimensions/difference are what actually let a
  // reviewer tell two identically-named thumbnails apart (Joseph found this
  // gap live: "the filenames shown for duplicates are the same, what's the
  // difference?" -- there was no answer in the UI because this function was
  // discarding everything but the path before it ever reached the report).
  return groups;
}

async function scanBroken() {
  const outPath = path.join(DATA_DIR, '_czkawka_broken.json');
  log('Running czkawka broken (corrupted image) scan...');
  await runCzkawka(['broken', '-d', UPLOAD_ROOT, '-c', 'IMAGE', '-p', outPath, '-N', '-M']);
  const raw = await fs.readFile(outPath, 'utf-8');
  const items = JSON.parse(raw); // [{path, modified_date, size, errors}, ...]
  log(`  found ${items.length} broken file(s)`);
  return items.map((entry) => ({ path: entry.path, errors: entry.errors }));
}

async function walkImageFiles(dir) {
  const results = [];
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...(await walkImageFiles(full)));
    } else if (IMAGE_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) {
      results.push(full);
    }
  }
  return results;
}

async function blurVariance(filePath) {
  const { data, info } = await sharp(filePath)
    .resize(512, 512, { fit: 'inside', withoutEnlargement: true })
    .greyscale()
    .convolve({ width: 3, height: 3, kernel: [0, 1, 0, 1, -4, 1, 0, 1, 0] })
    .raw()
    .toBuffer({ resolveWithObject: true });
  const n = data.length;
  let sum = 0;
  for (let i = 0; i < n; i++) sum += data[i];
  const mean = sum / n;
  let variance = 0;
  for (let i = 0; i < n; i++) variance += (data[i] - mean) ** 2;
  return variance / n;
}

// Simple concurrency-limited map -- no new dependency for something this small.
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

async function scanBlurry() {
  log('Enumerating image files for blur pass...');
  const files = await walkImageFiles(UPLOAD_ROOT);
  log(`  ${files.length} image file(s) found`);

  let cache = {};
  try {
    cache = JSON.parse(await fs.readFile(BLUR_CACHE_PATH, 'utf-8'));
  } catch {
    // no cache yet -- first run
  }

  let reused = 0;
  let computed = 0;
  let processed = 0;
  const blurry = [];
  const startedAt = Date.now();

  // Progress logging + a periodic cache save -- this is the one pass with no
  // built-in progress signal (czkawka suppresses its own console output) and
  // the longest-running one on a first full-library scan, so an interrupted
  // run (or one that's just taking a while) shouldn't look silent, and
  // shouldn't lose all its cached work if it's killed before finishing.
  const PROGRESS_EVERY = 2000;

  await mapWithConcurrency(files, BLUR_CONCURRENCY, async (filePath) => {
    const stat = await fs.stat(filePath);
    const mtimeMs = stat.mtimeMs;
    const cached = cache[filePath];
    let variance;
    if (cached && cached.mtimeMs === mtimeMs) {
      variance = cached.variance;
      reused++;
    } else {
      try {
        variance = await blurVariance(filePath);
      } catch (err) {
        // Unreadable/corrupted -- czkawka's broken pass already covers this
        // case; don't let a decode failure here crash the whole blur pass.
        processed++;
        return;
      }
      cache[filePath] = { mtimeMs, variance };
      computed++;
    }
    if (variance < BLUR_VARIANCE_THRESHOLD) {
      blurry.push({ path: filePath, variance });
    }
    processed++;
    if (processed % PROGRESS_EVERY === 0) {
      const elapsedSec = (Date.now() - startedAt) / 1000;
      const rate = processed / elapsedSec;
      const etaSec = (files.length - processed) / rate;
      log(
        `  blur progress: ${processed}/${files.length} ` +
        `(${elapsedSec.toFixed(0)}s elapsed, ~${etaSec.toFixed(0)}s remaining)`
      );
      await fs.writeFile(BLUR_CACHE_PATH, JSON.stringify(cache));
    }
  });

  log(`  blur pass: ${computed} newly computed, ${reused} reused from cache, ${blurry.length} below threshold`);
  await fs.mkdir(DATA_DIR, { recursive: true });
  await fs.writeFile(BLUR_CACHE_PATH, JSON.stringify(cache));
  return blurry;
}

// Tracks how many flagged files couldn't be matched to any Immich asset --
// surfaced as a visible summary line, not just scroll-by warnings, since a
// real run found 74 such files that turned out to be genuine 0-byte files
// on disk with no Immich record under any visibility state (timeline,
// archive, or hidden) -- worth Joseph's attention as a possible separate
// data-integrity issue, not something to silently drop.
let unresolvedCount = 0;

function resolveAsset(pathIndex, hostPath) {
  const info = pathIndex[hostPath];
  if (!info) {
    unresolvedCount++;
    return null;
  }
  return info;
}

async function main() {
  const startedAt = Date.now();
  await fs.mkdir(DATA_DIR, { recursive: true });

  // CARD-0028 build finding: /mnt/photo-library is a spinning HDD (confirmed
  // via `lsblk -d -o rota` -- ROTA=1 on /dev/sda, a Seagate Backup Plus),
  // not an SSD. A real full-account run showed running these three passes
  // concurrently (the original design, and the whole point of the earlier
  // execFileSync -> execFile fix) actually made things *worse* on this
  // hardware -- three independent processes doing their own random file
  // reads against the same physical disk head at once cause seek-time
  // thrashing, not real parallelism. Measured live: ~0.8 files/sec on the
  // blur pass alone while both czkawka passes ran alongside it -- at that
  // rate a 150k-file library would take days. Running them sequentially
  // instead gives each pass uncontested, closer-to-sequential disk access.
  // The execFile (non-blocking) + child-tracking fix from that same episode
  // is still worth keeping regardless -- it's what makes SIGINT/SIGTERM
  // cleanup possible -- this only changes *when* each pass starts, not how
  // its own subprocess is managed.
  const duplicateGroups = await scanDuplicates();
  const broken = await scanBroken();
  const blurry = await scanBlurry();

  log('Building Immich path index (both accounts)...');
  const pathIndex = await immich.buildPathIndex();
  log(`  indexed ${Object.keys(pathIndex).length} asset(s)`);

  const resolvedDuplicateGroups = duplicateGroups
    .map((group) =>
      group
        .map((entry) => {
          const asset = resolveAsset(pathIndex, entry.path);
          return asset && {
            ...asset,
            path: entry.path,
            size: entry.size,
            width: entry.width,
            height: entry.height,
            difference: entry.difference,
          };
        })
        .filter(Boolean)
    )
    // A group only makes sense with 2+ resolved members -- one member left
    // (the rest unresolved) has nothing to compare against.
    .filter((group) => group.length >= 2);

  const resolvedBroken = broken
    .map(({ path: p, errors }) => {
      const asset = resolveAsset(pathIndex, p);
      return asset && { ...asset, path: p, errors };
    })
    .filter(Boolean);

  const resolvedBlurry = blurry
    .map(({ path: p, variance }) => {
      const asset = resolveAsset(pathIndex, p);
      return asset && { ...asset, path: p, variance };
    })
    .filter(Boolean);

  const report = {
    generatedAt: new Date().toISOString(),
    duplicateGroups: resolvedDuplicateGroups,
    broken: resolvedBroken,
    blurry: resolvedBlurry,
  };

  await archivePreviousReport();
  await fs.writeFile(REPORT_PATH, JSON.stringify(report, null, 2));

  const elapsedMin = ((Date.now() - startedAt) / 60000).toFixed(1);
  const summary =
    `${resolvedDuplicateGroups.length} duplicate group(s), ${resolvedBroken.length} broken, ` +
    `${resolvedBlurry.length} blurry (${elapsedMin} min)`;
  log(`Wrote ${REPORT_PATH}: ${summary}`);
  if (unresolvedCount > 0) {
    log(
      `NOTE: ${unresolvedCount} flagged file(s) had no matching Immich asset in any ` +
      `visibility state -- excluded from the report. Worth checking separately ` +
      `(e.g. the 0-byte-file case found during CARD-0028's own build) rather than assuming it's benign.`
    );
  }

  await notify.sendPush(
    'Photo Quality Scan',
    `Scan complete: ${summary}.` +
    (unresolvedCount > 0 ? ` ${unresolvedCount} flagged file(s) had no matching Immich asset.` : '')
  );
}

main().catch(async (err) => {
  console.error('[scan] FATAL:', err);
  await notify.sendPush('Photo Quality Scan', `Scan failed: ${err.message}`);
  process.exit(1);
});
