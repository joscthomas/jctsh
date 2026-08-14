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
CREDS_FILE = Path(__file__).resolve().parents[2] / "credentials.local.md"


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


def _merge_with_retry(pr_number, branch, commit_title, token, attempts=6, delay=3.0):
    """GitHub computes PR mergeability asynchronously. Confirmed live
    landing CARD-0160 (PR #11): an identical merge call 405'd twice,
    then succeeded seconds later with zero reviews once GitHub's
    mergeable_state flipped from "unknown" to "clean" -- not a branch-
    protection rejection. Poll first instead of assuming a real conflict.

    But a real conflict does happen too -- confirmed live landing
    CARD-0161 (PR #10): GitHub's 3-way merge compares against the PR's
    *original* branch point, not current main, so it can't tell "two
    independent additions near the same fixed anchor line" (every card
    inserts at the same spot) from a genuine conflict, even though this
    function already rebuilt the branch's content from a fresh read of
    main. Exact same failure mode open_kanban_pr.py's resolve_and_merge()
    already hit and worked around -- same fix here: construct the merge
    commit directly via the Git Data API (two parents: main's current
    tip + this branch's tip, tree = the branch's already-correct
    content) instead of asking GitHub to reconcile two diffs that touch
    the same lines."""
    last_err = None
    for _ in range(attempts):
        try:
            result = _api("PUT", f"/repos/{REPO}/pulls/{pr_number}/merge", token, {
                "commit_title": commit_title, "merge_method": "squash",
            })
            return result["sha"]
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 405:
                try:
                    body = json.loads(e.read())
                except Exception:
                    body = {}
                if body.get("message") == "Pull Request has merge conflicts":
                    break  # not transient -- go straight to the git-data-api fallback
            time.sleep(delay)
    else:
        raise SystemExit(
            f"PR #{pr_number} still not mergeable after {attempts} attempts "
            f"(~{attempts * delay:.0f}s). Last error: {last_err}. Check the "
            f"PR on GitHub directly."
        )

    main_ref = _api("GET", f"/repos/{REPO}/git/refs/heads/{BRANCH_BASE}", token)
    main_sha = main_ref["object"]["sha"]
    branch_ref = _api("GET", f"/repos/{REPO}/git/refs/heads/{branch}", token)
    branch_sha = branch_ref["object"]["sha"]
    branch_content = _api("GET", f"/repos/{REPO}/contents/kanban-board.md?ref={branch}", token)
    main_commit = _api("GET", f"/repos/{REPO}/git/commits/{main_sha}", token)
    new_tree = _api("POST", f"/repos/{REPO}/git/trees", token, {
        "base_tree": main_commit["tree"]["sha"],
        "tree": [{"path": "kanban-board.md", "mode": "100644", "type": "blob",
                  "sha": branch_content["sha"]}],
    })
    merge_commit = _api("POST", f"/repos/{REPO}/git/commits", token, {
        "message": f"Merge {BRANCH_BASE} into {branch} ({commit_title} conflict workaround)",
        "tree": new_tree["sha"], "parents": [main_sha, branch_sha],
    })
    _api("PATCH", f"/repos/{REPO}/git/refs/heads/{branch}", token, {"sha": merge_commit["sha"]})
    result = _api("PUT", f"/repos/{REPO}/pulls/{pr_number}/merge", token, {
        "commit_title": commit_title, "merge_method": "merge",  # not squash -- would re-diff and re-conflict
    })
    return result["sha"]


def land_pr_card(pr_number, card_body_template, token):
    """Returns (card_id, merge_commit_sha)."""
    pr = _api("GET", f"/repos/{REPO}/pulls/{pr_number}", token)
    if pr["state"] != "open":
        raise SystemExit(f"PR #{pr_number} is not open (state={pr['state']!r}) -- nothing to land.")
    branch = pr["head"]["ref"]

    main_current = _api("GET", f"/repos/{REPO}/contents/kanban-board.md?ref={BRANCH_BASE}", token)
    main_text = base64.b64decode(main_current["content"]).decode("utf-8")
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

    branch_current = _api("GET", f"/repos/{REPO}/contents/kanban-board.md?ref={branch}", token)
    title_line = re.sub(r"^### CARD-\d{4} \xb7 ", "", finished_card.splitlines()[0])
    commit_title = f"{card_id}: {title_line}"

    _api("PUT", f"/repos/{REPO}/contents/kanban-board.md", token, {
        "message": commit_title,
        "content": base64.b64encode(new_main_text.encode("utf-8")).decode("ascii"),
        "sha": branch_current["sha"],
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
