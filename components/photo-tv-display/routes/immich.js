// Immich API integration layer for photo-tv-display.
//
// Verified against the real M8 Immich instance (v3.1.0) and its published
// OpenAPI spec at build time (immich-app/immich, open-api/immich-openapi-specs.json)
// rather than assumed from older docs — the API has moved since this component
// was planned:
//   - Asset filtering DTOs have no `ownerId` field. There is no way to ask a
//     single account's API key for "both users' photos" in one call. Joseph
//     and Robin's Immich accounts are queried separately (their own API keys)
//     and merged client-side — this is *why* the Phase 2 "multi-account merge"
//     design exists, not just an implementation detail.
//   - `isArchived` (boolean) has been replaced by `visibility` (enum:
//     archive/timeline/hidden/locked). "Exclude archived by default" now means
//     requesting `visibility: 'timeline'` explicitly.
//   - The single-asset `PUT /assets/{id}` update endpoint is flagged
//     "deprecated" in the spec, but its own x-immich-history entry lists itself
//     as its own replacement (a spec-generation quirk, not a real successor) --
//     it's still the only endpoint that updates one asset's isFavorite, and it
//     works against the real instance. Used deliberately despite the flag.
//   - Immich `personId`s and album ownership are scoped to the account that
//     recognized/created them -- Joseph's and Robin's face-recognition results
//     are separate Person records even for the same physical person, and one
//     account's API key cannot reliably assume write access to the other's
//     assets. Every per-asset write (favorite/delete/album) therefore takes an
//     explicit `ownerLabel` and uses that account's own key, resolved once at
//     startup via GET /users/me rather than guessed.

// Immich mounts its REST API under /api (confirmed live against the M8
// instance -- bare paths like /search/random 404). IMMICH_SERVER_URL itself
// stays the bare host:port in .env, matching the existing convention in
// components/hike-izer/fetch_hike_photos.py, which prepends /api the same way.
const BASE_URL = `${process.env.IMMICH_SERVER_URL}/api`;

const ACCOUNTS = {
  joseph: process.env.IMMICH_API_KEY_JOSEPH,
  robin: process.env.IMMICH_API_KEY_ROBIN,
};

// Populated by resolveOwners() at startup: { [immichUserId]: 'joseph' | 'robin' }
let OWNER_ID_TO_LABEL = {};

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

// Must be called once at server startup before any other function here is used.
async function resolveOwners() {
  const map = {};
  for (const [label, key] of Object.entries(ACCOUNTS)) {
    const me = await immichFetch(key, '/users/me');
    map[me.id] = label;
  }
  OWNER_ID_TO_LABEL = map;
}

function tagOwner(asset) {
  return { ...asset, ownerLabel: OWNER_ID_TO_LABEL[asset.ownerId] || 'unknown' };
}

// Runs queryFn(apiKey) against one or both accounts (per `accounts`, default
// both), merges results, tags each asset with its real owner (from
// OWNER_ID_TO_LABEL, not "which key fetched it" -- shared albums mean the
// same asset can come back from either key), and dedupes by asset id.
async function mergeAccounts(queryFn, accounts = ['joseph', 'robin']) {
  const lists = await Promise.all(
    accounts.map((label) => queryFn(ACCOUNTS[label]))
  );
  const seen = new Map();
  for (const list of lists) {
    for (const asset of list) {
      if (!seen.has(asset.id)) seen.set(asset.id, tagOwner(asset));
    }
  }
  // Without this, querying both accounts leaves the merged pool as
  // "everything from account A, then everything from account B" -- shuffle
  // so a two-account slideshow actually interleaves rather than running
  // through one person's photos before ever showing the other's.
  return shuffle([...seen.values()]);
}

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const BASE_RANDOM_FILTERS = { visibility: 'timeline', size: 100 };

// filterParams: { mode, ...mode-specific params }
// Supported modes: random, owner, favorites, person, concept, location, album,
// dateRange, onThisDay
async function getPhotosByFilter(filterParams) {
  const { mode } = filterParams;

  switch (mode) {
    case 'random': {
      return mergeAccounts((key) =>
        immichFetch(key, '/search/random', { method: 'POST', body: BASE_RANDOM_FILTERS })
      );
    }

    case 'owner': {
      // accounts: ['joseph'] | ['robin'] | ['joseph','robin']
      const accounts = filterParams.accounts || ['joseph', 'robin'];
      return mergeAccounts(
        (key) => immichFetch(key, '/search/random', { method: 'POST', body: BASE_RANDOM_FILTERS }),
        accounts
      );
    }

    case 'favorites': {
      return mergeAccounts((key) =>
        immichFetch(key, '/search/random', {
          method: 'POST',
          body: { ...BASE_RANDOM_FILTERS, isFavorite: true },
        })
      );
    }

    case 'person': {
      // personId is scoped to one account -- caller must supply which one.
      const { personId, ownerLabel } = filterParams;
      const key = ACCOUNTS[ownerLabel];
      const res = await immichFetch(key, '/search/metadata', {
        method: 'POST',
        body: { visibility: 'timeline', personIds: [personId], size: 200 },
      });
      return res.assets.items.map(tagOwner);
    }

    case 'concept': {
      const accounts = filterParams.accounts || ['joseph', 'robin'];
      return mergeAccounts(async (key) => {
        const res = await immichFetch(key, '/search/smart', {
          method: 'POST',
          body: { visibility: 'timeline', query: filterParams.query, size: 100 },
        });
        return res.assets.items;
      }, accounts);
    }

    case 'location': {
      const { city, state, country } = filterParams;
      return mergeAccounts(async (key) => {
        const res = await immichFetch(key, '/search/metadata', {
          method: 'POST',
          body: {
            visibility: 'timeline',
            ...(city ? { city } : {}),
            ...(state ? { state } : {}),
            ...(country ? { country } : {}),
            size: 200,
          },
        });
        return res.assets.items;
      });
    }

    case 'album': {
      // Albums are scoped to the account that created them; shared albums are
      // still fetched via their owner's key.
      const { albumId, ownerLabel } = filterParams;
      const key = ACCOUNTS[ownerLabel];
      const res = await immichFetch(key, '/search/metadata', {
        method: 'POST',
        body: { visibility: 'timeline', albumIds: [albumId], size: 500 },
      });
      return res.assets.items.map(tagOwner);
    }

    case 'dateRange': {
      const { start, end } = filterParams;
      return mergeAccounts(async (key) => {
        const res = await immichFetch(key, '/search/metadata', {
          method: 'POST',
          body: { visibility: 'timeline', takenAfter: start, takenBefore: end, size: 500 },
        });
        return res.assets.items;
      });
    }

    case 'onThisDay': {
      // Immich has no native "same calendar day across all years" filter --
      // query one takenAfter/takenBefore range per year, going back
      // ON_THIS_DAY_LOOKBACK_YEARS years, and merge. A fixed lookback window
      // (not "every year with data") keeps this to a bounded number of calls;
      // 20 years covers this household's actual photo history with room to
      // spare.
      const ON_THIS_DAY_LOOKBACK_YEARS = 20;
      const now = new Date();
      const mm = String(now.getMonth() + 1).padStart(2, '0');
      const dd = String(now.getDate()).padStart(2, '0');
      const years = Array.from({ length: ON_THIS_DAY_LOOKBACK_YEARS }, (_, i) => now.getFullYear() - i);

      return mergeAccounts(async (key) => {
        const perYear = await Promise.all(
          years.map((year) =>
            immichFetch(key, '/search/metadata', {
              method: 'POST',
              body: {
                visibility: 'timeline',
                takenAfter: `${year}-${mm}-${dd}T00:00:00.000Z`,
                takenBefore: `${year}-${mm}-${dd}T23:59:59.999Z`,
                size: 100,
              },
            }).then((res) => res.assets.items)
          )
        );
        return perYear.flat();
      });
    }

    default:
      throw new Error(`Unknown filter mode: ${mode}`);
  }
}

// Full metadata for the currently displayed asset -- always fetched with the
// owning account's own key (see file header on why).
async function getAssetMetadata(assetId, ownerLabel) {
  const key = ACCOUNTS[ownerLabel];
  const asset = await immichFetch(key, `/assets/${assetId}`);
  return tagOwner(asset);
}

// List of albums for one account (used for the "add to existing album"
// controller action, scoped to whichever account owns the current photo).
// assetId, if given, filters to just the albums containing that asset --
// used to resolve a "folder" label for the deletion log.
async function getAlbums(ownerLabel, assetId) {
  const key = ACCOUNTS[ownerLabel];
  const qs = assetId ? `?assetId=${assetId}` : '';
  return immichFetch(key, `/albums${qs}`);
}

// List of recognized people for one account (used for the "by person" filter
// panel). Names are prefixed with the owning account so Joseph's and Robin's
// separately-trained face records for the same physical person are never
// confused for one entry in the UI.
async function getPeople(ownerLabel) {
  const key = ACCOUNTS[ownerLabel];
  const res = await immichFetch(key, '/people?size=1000');
  return res.people.map((p) => ({ ...p, ownerLabel }));
}

async function toggleFavorite(assetId, favoriteState, ownerLabel) {
  const key = ACCOUNTS[ownerLabel];
  const asset = await immichFetch(key, `/assets/${assetId}`, {
    method: 'PUT',
    body: { isFavorite: favoriteState },
  });
  return tagOwner(asset);
}

// force: false -> moves to Immich's own trash (recoverable within its
// retention window) rather than an immediate permanent delete. Matches the
// planning doc's framing of delete as "removes it from our home library" --
// Immich's trash is a free extra safety net on top of that, not a deviation
// from it. Revisit to force:true if Joseph wants immediate permanent deletes.
async function deleteAsset(assetId, ownerLabel) {
  const key = ACCOUNTS[ownerLabel];
  await immichFetch(key, '/assets', {
    method: 'DELETE',
    body: { ids: [assetId], force: false },
  });
}

async function addToAlbum(assetId, albumId, ownerLabel) {
  const key = ACCOUNTS[ownerLabel];
  return immichFetch(key, `/albums/${albumId}/assets`, {
    method: 'PUT',
    body: { ids: [assetId] },
  });
}

async function createAlbum(albumName, assetId, ownerLabel) {
  const key = ACCOUNTS[ownerLabel];
  return immichFetch(key, '/albums', {
    method: 'POST',
    body: { albumName, assetIds: [assetId] },
  });
}

// Raw image bytes proxy -- browsers can't attach the x-api-key header to a
// plain <img src>, so the Node server fetches with the owning account's key
// and streams the response straight through (see server.js's /photo route).
// variant: 'thumbnail' | 'original'. Path shape matches the existing
// precedent in components/hike-izer/fetch_hike_photos.py.
async function getAssetImageResponse(assetId, ownerLabel, variant) {
  const key = ACCOUNTS[ownerLabel];
  const path = variant === 'original'
    ? `/assets/${assetId}/original`
    : `/assets/${assetId}/thumbnail?size=preview`;
  const res = await fetch(`${BASE_URL}${path}`, { headers: { 'x-api-key': key } });
  if (!res.ok) throw new Error(`Immich image fetch failed: ${res.status}`);
  return res;
}

// Real Immich reverse-geocoding data (confirmed live against the M8 library)
// returns "United States of America", not "United States"/"USA" as the
// original planning doc assumed -- matched with startsWith so any of that
// family of spellings is treated as domestic.
function formatLocation(city, state, country) {
  if (!city) return null;
  if (country && country.startsWith('United States')) {
    return state ? `${city}, ${state}` : city;
  }
  return country ? `${city}, ${country}` : city;
}

module.exports = {
  resolveOwners,
  getPhotosByFilter,
  getAssetMetadata,
  getAssetImageResponse,
  getAlbums,
  getPeople,
  toggleFavorite,
  deleteAsset,
  addToAlbum,
  createAlbum,
  formatLocation,
};
