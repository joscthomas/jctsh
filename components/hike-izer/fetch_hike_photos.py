#!/usr/bin/env python
"""
Hike-izer photo/video fetcher (CARD-0084).

Reads a hike_data.json already produced by fetch_hike_data.py and queries
Immich (photo-server) separately for each GPS-confirmed hike session's own
[start, end] window that day -- time range only, no GPS bounding-box filter
(the time window already comes from the real GPS-confirmed session, so any
photo taken inside it was taken during the hike by definition; a location
filter would only risk dropping legitimate photos that lack GPS EXIF).
Sessions are queried individually, NOT collapsed into one start-to-end span
-- a query day can contain two unrelated sessions hours apart (e.g. an early-
morning tail end plus an afternoon hike), and merging them into one span
would pull in photos from the gap between them that belong to neither.
Downloads a thumbnail and the original file for each match, and writes a
manifest.json describing what landed on disk, for the hike-izer Skill's
HTML-authoring step to build a gallery from.

KNOWN LIMITATION (cross-midnight sessions, same edge case as Hike-izer's day-
scoping rule in SKILL.md): a query day's *own* window can still surface a
session that only *looks* like it starts that day (e.g. "00:00:03") because
the query itself is capped at that day's midnight -- the session may really
be the tail of a hike that started the evening before, which this script
can't know without also querying the prior day. This script does not attempt
that lookback. When curating the gallery for HTML, cross-reference session
start times against known adjacent-day context (the same judgment call
already applied to CARD-0081's distance_mi stat on such days) and manually
exclude manifest entries that belong to a different day's hike.

Usage:
    python fetch_hike_photos.py --data hike_data.json \
        --immich-url http://photo-server.local:2283 --immich-key <API_KEY> \
        --out-dir hike-izer/summaries/2026-06-18_photos

Standard library only -- no pip install required.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def _api_get(base_url, api_key, path):
    req = urllib.request.Request(base_url.rstrip('/') + path, headers={'x-api-key': api_key})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _api_post_json(base_url, api_key, path, payload):
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        base_url.rstrip('/') + path,
        data=body,
        headers={'x-api-key': api_key, 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))


def hike_time_windows(hike_data):
    """Every is_hike-confirmed session's own [start, end] that day, as a list
    of (start_iso, end_iso) pairs -- NOT collapsed into one enclosing span.
    Sessions can be hours apart (e.g. a query window that also picks up the
    tail of the *previous* day's midnight-crossing hike); querying Immich
    with one merged span would pull in photos from the gap between sessions
    that have nothing to do with either hike. Returns [] if hike_confirmed is
    false or there are no is_hike sessions."""
    gps_track = hike_data.get('coverage', {}).get('gps_track', {})
    if not gps_track.get('hike_confirmed'):
        return []
    return [(s['start'], s['end']) for s in gps_track.get('sessions', []) if s.get('is_hike')]


def search_assets(base_url, api_key, taken_after, taken_before):
    """Page through /api/search/metadata for every asset in the window."""
    assets = []
    page = 1
    while True:
        result = _api_post_json(base_url, api_key, '/api/search/metadata', {
            'takenAfter': taken_after,
            'takenBefore': taken_before,
            'withExif': True,
            'page': page,
        })
        items = result['assets']['items']
        assets.extend(items)
        if len(assets) >= result['assets']['total'] or not items:
            break
        page += 1
    return [a for a in assets if not a.get('isTrashed')]


def _ext_for_mime(mime_type):
    return {
        'image/jpeg': 'jpg', 'image/png': 'png', 'image/heic': 'heic',
        'video/mp4': 'mp4', 'video/quicktime': 'mov',
    }.get(mime_type, 'bin')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data', required=True, help='Path to hike_data.json from fetch_hike_data.py')
    ap.add_argument('--immich-url', required=True, help='Immich base URL, e.g. http://photo-server.local:2283')
    ap.add_argument('--immich-key', required=True, help='Immich API key')
    ap.add_argument('--out-dir', required=True, help='Directory to write downloaded media + manifest.json into')
    args = ap.parse_args()

    with open(args.data, 'r', encoding='utf-8') as f:
        hike_data = json.load(f)

    os.makedirs(args.out_dir, exist_ok=True)
    manifest_path = os.path.join(args.out_dir, 'manifest.json')

    windows = hike_time_windows(hike_data)
    if not windows:
        print('No confirmed hike session -- writing empty manifest.', file=sys.stderr)
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump({'assets': []}, f, indent=2)
        return

    assets_by_id = {}
    try:
        for taken_after, taken_before in windows:
            print(f'Searching Immich for assets {taken_after} .. {taken_before}...', file=sys.stderr)
            for a in search_assets(args.immich_url, args.immich_key, taken_after, taken_before):
                assets_by_id[a['id']] = a  # dedupe -- a photo can't belong to two sessions, but be safe
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f'ERROR: Immich unreachable or request failed ({e}) -- writing empty manifest.', file=sys.stderr)
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump({'assets': []}, f, indent=2)
        sys.exit(1)

    assets = list(assets_by_id.values())
    print(f'  {len(assets)} matching asset(s) across {len(windows)} session(s)', file=sys.stderr)

    manifest_assets = []
    for a in assets:
        asset_id = a['id']
        ext = _ext_for_mime(a.get('originalMimeType', ''))
        thumb_name = f'{asset_id}_thumb.jpg'
        original_name = f'{asset_id}_original.{ext}'

        thumb_bytes = _api_get(args.immich_url, args.immich_key, f'/api/assets/{asset_id}/thumbnail?size=preview')
        with open(os.path.join(args.out_dir, thumb_name), 'wb') as f:
            f.write(thumb_bytes)

        original_bytes = _api_get(args.immich_url, args.immich_key, f'/api/assets/{asset_id}/original')
        with open(os.path.join(args.out_dir, original_name), 'wb') as f:
            f.write(original_bytes)

        exif = a.get('exifInfo') or {}
        manifest_assets.append({
            'id': asset_id,
            'type': a.get('type'),
            'takenAt': a.get('fileCreatedAt'),
            'lat': exif.get('latitude'),
            'lon': exif.get('longitude'),
            'thumb': thumb_name,
            'original': original_name,
        })

    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump({'assets': manifest_assets}, f, indent=2)

    print(f'Wrote {manifest_path}: {len(manifest_assets)} asset(s) downloaded to {args.out_dir}', file=sys.stderr)


if __name__ == '__main__':
    main()
