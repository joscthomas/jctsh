# Staging data for Hike-izer's enriched (step 2) pass

Operational runbook for getting Gaia GPS's embed snippet and a BirdNET Live
export into the right hike's staging directory, so step 2 (`run_step2` —
the enriched narrative/photos/bird-table pass, CARD-0112) can pick them up.
For the mechanics of *why* this exists, see CARD-0112 (designed the
`<file_stem>_staging/` directory), CARD-0119 (this doc, plus the SSHFS-Win
mount), and CARD-0122 (BirdNET's automatic phone-to-server path).

Only two staged-resource types exist today — nothing else is read from a
staging directory.

---

## 1. Find the right hike's staging directory

From Windows (via the `Z:` mount, see Section 4), the `srv` directory is:

```
Z:\hike-izer-web-app\srv
```

Every hike gets its own `<file_stem>_staging/` directory under there —
`2026-07-30_staging/` for the first (or only) hike that day, `2026-07-30-2_staging/`
for a second same-day hike (CARD-0113), and so on.

Fastest way to confirm the right one: check that `srv` directory for
whichever `*_hike-summary.html` is newest, or just look at the live
calendar page (`https://hikes.jctnet.com/`) for today's date. The
directory of the same name (swap `_hike-summary.html` for `_staging`) is
the one to use. If you're staging files right after a hike just ended,
it's almost always the most recently published one.

## 2. Gaia GPS embed snippet — manual, laptop only

Gaia's real **Embed** feature (the one that generates an `<iframe>`
snippet, not just a shareable map link) only exists in the **laptop**
browser's UI — confirmed 2026-07-30 it's not reachable from the phone at
all, even with "Request desktop site" on. So this one stays a manual,
laptop-side step:

1. On the laptop, use Gaia's Embed feature to generate the `<iframe>`
   snippet and copy it.
2. Through the `Z:` SSHFS-Win mount (see Section 4), save it as exactly
   **`gaia_embed.html`** inside that hike's `_staging/` directory —
   `generation.py`'s `_read_staging()` looks for that exact filename, no
   variations.

## 3. BirdNET Live export — automatic, with the mount as fallback

Normally fully automatic (CARD-0122): sharing a BirdNET Live session
export from the phone (via the AutoShare app → Tasker → the
`/webhook/stage-file` endpoint) lands it in the correct staging directory
with no manual step at all.

If that pipeline is ever down or being bypassed, the manual fallback is
the same mount: drop the export (any filename ending `.zip` or `.json` —
`birdnet.py`'s `parse_detections()` globs for both and doesn't care about
the exact name) into that hike's `_staging/` directory. More than one
export can be staged for the same hike (e.g. multiple survey sessions);
all of them get parsed.

## 4. The SSHFS-Win mount itself

Installed and verified 2026-07-30 (CARD-0119). Mounted as drive **`Z:`**,
rooted at the `jct` account's whole home directory on the M8 — the
staging directories themselves are one level deeper, at
`Z:\hike-izer-web-app\srv\<file_stem>_staging\`.

If the mount is ever missing (new machine, after a reboot that didn't
reconnect it, etc.):

```powershell
winget install --id WinFsp.WinFsp -e
winget install --id SSHFS-Win.SSHFS-Win -e
```

Then in File Explorer, connect to:

```
\\sshfs\jct@100.111.16.14\home\jct
```

using the Tailscale IP (not `photo-server.local`) so it resolves
identically at home and remote — same convention as everywhere else in
this repo. Credentials (`jct` account) are in `credentials.local.md`. It
should reconnect as `Z:`; if a *raw* UNC path attempt fails once the share
is already connected via a drive letter, that's a red herring, not a real
problem — check `Z:` directly instead.

## 5. Staged files aren't deleted after use

Step 2 reads whatever's staged but never removes it. That means a later
re-render of the same hike (e.g. after an unrelated bug fix) doesn't need
anything re-staged — it's already there from last time.

---

## Related

- CARD-0112 (designed the `<file_stem>_staging/` mechanism)
- CARD-0119 (this doc + the SSHFS-Win mount)
- CARD-0122 (BirdNET's automatic phone → `/webhook/stage-file` path)
- CARD-0104 (Gaia embed, the first staged-resource type)
- CARD-0080 (BirdNET export, the second staged-resource type)
- `components/hike-izer-orchestrator/generation.py` (`_read_staging()`, `run_step2()`)
- `components/hike-izer-orchestrator/birdnet.py` (`parse_detections()`)
- `components/hike-izer-orchestrator/app.py` (`_handle_stage_file`)
