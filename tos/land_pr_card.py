"""Land a maintenance-finding PR (CARD-0128) as a finished kanban card on main.

Interactive-only -- run by Claude, one PR at a time, when Joseph has
explicitly said to proceed. Not imported by any deployed maintenance-check
script and not something to loop over multiple PRs unattended.

This deliberately does NOT just renumber open_kanban_pr.py's
auto-generated CARD-XXX stub the way resolve_and_merge() does. A bare
stub ("Container image updates: X available") is exactly the "one-line
card from assumption" that this repo's global card-creation rule warns
against (~/.claude/CLAUDE.md: "When creating a card, interview first").
So the mechanical work this script does is only the tail end, after a
human has already:
  1. Seen the PR's raw finding and said explicitly to proceed with it.
  2. Answered clarifying questions so the card has a real "done"
     definition, not just the auto-opened title.
  3. Confirmed the finished card text.

Given that finished text, this script:
  1. Reads main's next-card-id marker fresh (not cached from an earlier
     read -- same discipline CARD-0128 already established, to survive
     concurrent findings from different hosts).
  2. Substitutes the assigned number into the card body wherever `{id}`
     appears.
  3. Builds main's content with the marker bumped and the finished card
     inserted at the standard anchor point, and pushes that as a commit
     on the PR's own branch (not stub-editing the branch's existing
     content) -- mirrors resolve_and_merge()'s own fix for a real bug
     where trusting a branch's stale full-file copy could silently
     revert a different card merged after the branch was created.
  4. Merges into main, polling briefly if GitHub hasn't finished
     computing mergeability yet.
  5. Deletes the merged branch.

Usage:
    python land_pr_card.py --pr 10 --body path/to/card_body.md

card_body.md must be the complete card block:
    starts with `### {id} \xb7 [type] [tags] Title` -- note: no "CARD-"
    prefix before `{id}`, since the assigned card_id already includes it
    ends with the closing `---\n\n` separator (added automatically if
    missing)
    `{id}` used as the placeholder anywhere the real card number belongs

Confirm the rendered result against Joseph before treating a PR as
landed -- this script does not ask him anything itself.
"""
import argparse
import base64
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = "joscthomas/jctsh"
API = "https://api.github.com"
BRANCH_BASE = "main"
CREDS_FILE = Path(__file__).resolve().parents[1] / "credentials.local.md"


def _load_token():
    text = CREDS_FILE.read_text(encoding="utf-8")
    m = re.search(r"GitHub PAT.*?\| Token \| `([^`]+)` \|", text, re.DOTALL)
    if not m:
        raise SystemExit(f"Couldn't find the GitHub PAT in {CREDS_FILE}")
    return m.group(1)


def _api(method, path, token, body=None):
    req = urllib.request.Request(
        f"{API}{path}", method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def _get_file_text(path, ref, token):
    """Raw text content of `path` at `ref` (CARD-0190). GitHub's Contents API
    only populates the JSON `content` field for files under 1MB --
    kanban-board.md crossed that in August 2026, and this script duplicated
    the same broken base64.b64decode(current["content"]) pattern
    open_kanban_pr.py's resolve_and_merge() had (confirmed live via that
    identical failure mode). The `application/vnd.github.raw` media type
    bypasses the JSON+base64 envelope entirely and works up to 100MB."""
    req = urllib.request.Request(
        f"{API}/repos/{REPO}/contents/{path}?ref={ref}", method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.raw",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def _blob_sha_at(path, ref, token):
    """Current blob sha for `path` at `ref` (CARD-0190), via the Git Data API
    tree lookup rather than the Contents API's metadata `sha` field -- same
    fix as open_kanban_pr.py's helper of the same name, kept as a local
    duplicate here since this script is deliberately standalone (see module
    docstring)."""
    ref_data = _api("GET", f"/repos/{REPO}/git/refs/heads/{ref}", token)
    commit = _api("GET", f"/repos/{REPO}/git/commits/{ref_data['object']['sha']}", token)
    tree = _api("GET", f"/repos/{REPO}/git/trees/{commit['tree']['sha']}", token)
    for entry in tree["tree"]:
        if entry["path"] == path:
            return entry["sha"]
    raise FileNotFoundError(f"{path} not found in {ref}'s tree")


def _put_merge(pr_number, token, commit_title, merge_method, attempts, delay):
    """One merge attempt, retried -- GitHub computes PR mergeability
    asynchronously. Confirmed live landing CARD-0160 (PR #11): an
    identical merge call 405'd twice, then succeeded seconds later with
    zero reviews once GitHub's mergeable_state flipped from "unknown" to
    "clean" -- not a branch-protection rejection.

    Returns the merge commit sha, or None specifically when a squash
    attempt hits a real conflict signal (caller should fall back to the
    git-data-api approach in _merge_with_retry). Any other transient
    error (405 or 409, "unknown" state not yet resolved) is retried up to
    `attempts` times before giving up for real.

    Confirmed live 2026-08-16 landing 6 PRs in one session: this needs to
    wrap *every* call to the merge endpoint, not just the first one. The
    previous version only retried the initial squash attempt -- the
    git-data-api fallback below ends with its own call to this same
    endpoint (patching the branch ref onto a fresh merge commit resets
    GitHub's mergeable_state cache right back to "unknown"), and that
    second call had no retry or error handling at all. A transient error
    there crashed the whole script uncaught, which is what actually
    happened on most of that session's failures -- not a real conflict."""
    last_err = None
    for _ in range(attempts):
        try:
            result = _api("PUT", f"/repos/{REPO}/pulls/{pr_number}/merge", token, {
                "commit_title": commit_title, "merge_method": merge_method,
            })
            return result["sha"]
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 405 and merge_method == "squash":
                try:
                    body = json.loads(e.read())
                except Exception:
                    body = {}
                if body.get("message") == "Pull Request has merge conflicts":
                    return None  # real conflict signal -- caller falls back
            time.sleep(delay)
    raise SystemExit(
        f"PR #{pr_number} still not mergeable after {attempts} attempts "
        f"(~{attempts * delay:.0f}s), merge_method={merge_method!r}. "
        f"Last error: {last_err}. Check the PR on GitHub directly."
    )


def _merge_with_retry(pr_number, branch, commit_title, token, attempts=8, delay=4.0):
    """Squash-merge if GitHub can compute it cleanly. If not -- confirmed
    live landing CARD-0161 (PR #10): GitHub's 3-way merge compares against
    the PR's *original* branch point, not current main, so it can't tell
    "two independent additions near the same fixed anchor line" (every
    card inserts at the same spot) from a genuine conflict, even though
    this function already rebuilt the branch's content from a fresh read
    of main -- construct the merge commit directly via the Git Data API
    instead (two parents: main's current tip + this branch's tip, tree =
    the branch's already-correct content), same fix open_kanban_pr.py's
    resolve_and_merge() already uses for the identical failure mode."""
    sha = _put_merge(pr_number, token, commit_title, "squash", attempts, delay)
    if sha is not None:
        return sha

    main_ref = _api("GET", f"/repos/{REPO}/git/refs/heads/{BRANCH_BASE}", token)
    main_sha = main_ref["object"]["sha"]
    branch_ref = _api("GET", f"/repos/{REPO}/git/refs/heads/{branch}", token)
    branch_sha = branch_ref["object"]["sha"]
    branch_file_sha = _blob_sha_at("tos/kanban-board.md", branch, token)
    main_commit = _api("GET", f"/repos/{REPO}/git/commits/{main_sha}", token)
    new_tree = _api("POST", f"/repos/{REPO}/git/trees", token, {
        "base_tree": main_commit["tree"]["sha"],
        "tree": [{"path": "tos/kanban-board.md", "mode": "100644", "type": "blob",
                  "sha": branch_file_sha}],
    })
    merge_commit = _api("POST", f"/repos/{REPO}/git/commits", token, {
        "message": f"Merge {BRANCH_BASE} into {branch} ({commit_title} conflict workaround)",
        "tree": new_tree["sha"], "parents": [main_sha, branch_sha],
    })
    _api("PATCH", f"/repos/{REPO}/git/refs/heads/{branch}", token, {"sha": merge_commit["sha"]})
    return _put_merge(pr_number, token, commit_title, "merge", attempts, delay)  # not squash -- would re-diff and re-conflict


def land_pr_card(pr_number, card_body_template, token):
    """Returns (card_id, merge_commit_sha)."""
    pr = _api("GET", f"/repos/{REPO}/pulls/{pr_number}", token)
    if pr["state"] != "open":
        raise SystemExit(f"PR #{pr_number} is not open (state={pr['state']!r}) -- nothing to land.")
    branch = pr["head"]["ref"]

    main_text = _get_file_text("tos/kanban-board.md", BRANCH_BASE, token)
    m = re.search(r"<!-- next-card-id: (CARD-\d{4}) -->", main_text)
    if not m:
        raise SystemExit("Couldn't find the next-card-id marker in main's kanban-board.md.")
    card_id = m.group(1)
    next_marker = f"CARD-{int(card_id[5:]) + 1:04d}"

    finished_card = card_body_template.replace("{id}", card_id)
    if not finished_card.startswith(f"### {card_id} "):
        raise SystemExit(f"Card body doesn't start with '### {card_id} \xb7 ...' after substitution.")
    if not finished_card.rstrip("\n").endswith("---"):
        finished_card = finished_card.rstrip("\n") + "\n\n---\n\n"
    elif not finished_card.endswith("\n\n"):
        finished_card = finished_card.rstrip("\n") + "\n\n"

    new_main_text = main_text.replace(
        f"<!-- next-card-id: {card_id} -->", f"<!-- next-card-id: {next_marker} -->", 1,
    )
    insert_at = new_main_text.index("---\n\n") + len("---\n\n")
    new_main_text = new_main_text[:insert_at] + finished_card + new_main_text[insert_at:]

    branch_file_sha = _blob_sha_at("tos/kanban-board.md", branch, token)
    title_line = re.sub(r"^### CARD-\d{4} \xb7 ", "", finished_card.splitlines()[0])
    commit_title = f"{card_id}: {title_line}"

    _api("PUT", f"/repos/{REPO}/contents/tos/kanban-board.md", token, {
        "message": commit_title,
        "content": base64.b64encode(new_main_text.encode("utf-8")).decode("ascii"),
        "sha": branch_file_sha,
        "branch": branch,
    })

    merge_commit_sha = _merge_with_retry(pr_number, branch, commit_title, token)

    try:
        _api("DELETE", f"/repos/{REPO}/git/refs/heads/{branch}", token)
    except urllib.error.HTTPError:
        pass  # GitHub auto-deletes on merge in some repo settings -- fine either way

    return card_id, merge_commit_sha


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pr", type=int, required=True, help="PR number to land")
    ap.add_argument("--body", required=True, help="Path to the finished card body markdown ('{id}' as the card-number placeholder)")
    ap.add_argument("--token", help="GitHub PAT; defaults to reading credentials.local.md")
    args = ap.parse_args()

    token = args.token or _load_token()
    card_body = Path(args.body).read_text(encoding="utf-8")

    card_id, merge_sha = land_pr_card(args.pr, card_body, token)
    print(f"Landed PR #{args.pr} as {card_id} (merge commit {merge_sha[:10]})")


if __name__ == "__main__":
    main()
