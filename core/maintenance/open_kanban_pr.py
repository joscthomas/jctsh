"""CARD-0128: open a PR against kanban-board.md for a maintenance finding.

Pure GitHub REST API -- no local git clone or `gh` CLI needed on the M8/Pi
(neither host has one, and this session's own git access from the dev
machine turned out to be plain `git push`, not the `gh` CLI, so there was
nothing to reuse). Creates a branch ref, updates kanban-board.md via the
Contents API (which creates a commit on that branch), opens a PR. Imported
by maintenance-check.py / pi-maintenance-check.py, not run standalone.

Dedup: the caller passes its own fingerprint (the same one already used
for the Alert-notification throttle) and its own persisted state dict.
Before doing anything, checks whether that state already holds a PR
number for this exact fingerprint AND that PR is still open on GitHub --
if so, does nothing. This directly extends the existing throttle-state
mechanism (CARD-0095/CARD-0125) rather than needing CARD-0127's
retained-MQTT state, which solves a different problem (a different
process, the dashboard, learning current state) -- see CARD-0128's own
Planning notes for why that dependency doesn't actually hold up.

main gets a branch-protection rule requiring PR review before merge (set
up separately, via GitHub's web UI -- not something this module or its
PAT can do, and deliberately so: the PAT is scoped to Contents+PRs only,
not Administration). That rule is what makes this structurally incapable
of touching main directly, not just "trusted" not to.

Card numbering (fixed 2026-07-31 15:36 MST, from a real race condition
caught during review): open_finding_pr() no longer reads or bumps main's
next-card-id marker at all -- the stub goes in with a literal CARD-XXX
placeholder, and the PR's diff never touches the marker line. Real
number assignment happens at merge time instead (resolve_and_merge()),
by reading main's marker *then*, not when the PR was opened. Reasoning:
main's marker doesn't move until merge regardless of what a PR's diff
claims, so two concurrent PRs (M8 and Pi both finding something around
the same time) could previously both compute and claim the same number
before either merged -- a real collision, not hypothetical, since
nothing reserves a number just by opening a PR. Deferring assignment to
merge time removes the race entirely, and mirrors the exact discipline
already used for every manual card edit in this repo: read the marker
fresh immediately before writing, never trust an earlier read.
resolve_and_merge() is meant to be run interactively (by Claude, when
asked to merge one of these PRs) -- it is not imported or called by
the deployed maintenance-check scripts, unlike open_finding_pr().
"""
import base64
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

REPO   = "joscthomas/jctsh"
API    = "https://api.github.com"
BRANCH_BASE = "main"


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
        return json.loads(resp.read())


def _pr_still_open(pr_number, token):
    try:
        data = _api("GET", f"/repos/{REPO}/pulls/{pr_number}", token)
        return data.get("state") == "open"
    except urllib.error.HTTPError:
        return False


def _render_stub(card_id, component, message, now):
    ts = now.strftime("%Y-%m-%d %H:%M %Z") or now.strftime("%Y-%m-%d %H:%M UTC")
    title = message if len(message) <= 80 else message[:77] + "…"
    return (
        f"### {card_id} · [enhancement] [infrastructure] {title} — auto-opened from {component}\n"
        f"**Status:** Backlog\n\n"
        f"**Auto-generated {ts} from {component}'s maintenance check.** "
        f"Raw finding: {message}. Needs a human/Claude interview pass to scope "
        f"real acceptance criteria — this stub only captures that something "
        f"was found, not what \"done\" looks like.\n\n"
        f"**Related:** live dashboard entry at time of generation.\n\n---\n\n"
    )


def open_finding_pr(component, message, fingerprint, token, state):
    """Idempotent per fingerprint. `state` is the caller's own persisted
    throttle-state dict (already fingerprint-keyed for the Alert
    notification) -- this reads/extends it with pr_fingerprint/pr_number,
    caller is responsible for persisting the returned dict same as it
    already persists its own state. Returns (state, pr_url_or_None) --
    pr_url is None when an existing open PR already covers this finding,
    so the caller can tell "nothing new happened" from "opened one"."""
    if (state.get("pr_fingerprint") == fingerprint
            and state.get("pr_number")
            and _pr_still_open(state["pr_number"], token)):
        return state, None

    main_ref = _api("GET", f"/repos/{REPO}/git/refs/heads/{BRANCH_BASE}", token)
    main_sha = main_ref["object"]["sha"]

    now = datetime.now(timezone.utc)
    branch = f"maintenance-alert/{component}-{now.strftime('%Y-%m-%d-%H%M%S')}"
    _api("POST", f"/repos/{REPO}/git/refs", token, {
        "ref": f"refs/heads/{branch}", "sha": main_sha,
    })

    current = _api("GET", f"/repos/{REPO}/contents/kanban-board.md?ref={BRANCH_BASE}", token)
    text = base64.b64decode(current["content"]).decode("utf-8")

    # CARD-XXX placeholder -- never reads or touches the next-card-id marker
    # line, see the module docstring for why. Real number assigned at merge
    # time by resolve_and_merge().
    insert_at = text.index("---\n\n") + len("---\n\n")
    new_text = text[:insert_at] + _render_stub("CARD-XXX", component, message, now) + text[insert_at:]

    _api("PUT", f"/repos/{REPO}/contents/kanban-board.md", token, {
        "message": f"CARD-XXX: auto-open from {component} maintenance check",
        "content": base64.b64encode(new_text.encode("utf-8")).decode("ascii"),
        "sha": current["sha"],
        "branch": branch,
    })

    pr = _api("POST", f"/repos/{REPO}/pulls", token, {
        "title": f"CARD-XXX: {message[:72]}",
        "head": branch,
        "base": BRANCH_BASE,
        "body": f"Auto-opened by {component}'s maintenance check (CARD-0128).\n\n"
                f"Finding:\n```\n{message}\n```\n\n"
                f"Card number is a placeholder (`CARD-XXX`) -- real numbering is "
                f"assigned at merge time, not here, to avoid a race between "
                f"concurrent findings from different hosts. See resolve_and_merge().",
    })

    new_state = dict(state)
    new_state["pr_fingerprint"] = fingerprint
    new_state["pr_number"] = pr["number"]
    return new_state, pr["html_url"]


def resolve_and_merge(pr_number, token, merge_method="squash"):
    """Interactive-use only (Claude, when asked to merge a CARD-0128 PR) --
    not called by the deployed scripts. Reads main's next-card-id marker
    *now* (not whenever the PR happened to be opened), replaces the PR
    branch's CARD-XXX placeholder with the real ID, sets the marker
    correctly for the number actually assigned (not just incrementing
    whatever stale value the branch's own copy had), pushes that as a
    fixup commit on the PR's own branch, then merges -- so the commit
    that actually lands on main is already fully correct, never a moment
    where main shows a literal CARD-XXX. Returns the assigned card_id."""
    main_current = _api("GET", f"/repos/{REPO}/contents/kanban-board.md?ref={BRANCH_BASE}", token)
    main_text = base64.b64decode(main_current["content"]).decode("utf-8")
    m = re.search(r"<!-- next-card-id: (CARD-\d{4}) -->", main_text)
    card_id = m.group(1)
    next_marker = f"CARD-{int(card_id[5:]) + 1:04d}"

    pr = _api("GET", f"/repos/{REPO}/pulls/{pr_number}", token)
    branch = pr["head"]["ref"]

    branch_current = _api("GET", f"/repos/{REPO}/contents/kanban-board.md?ref={branch}", token)
    branch_text = base64.b64decode(branch_current["content"]).decode("utf-8")

    # Scoped replace, not a bare "CARD-XXX" substring match -- caught live
    # during review (2026-07-31): this repo's own documentation *about* this
    # placeholder mechanism contains the literal words "CARD-XXX" multiple
    # times in prose (CARD-0128's own card notes), and a blind global
    # replace would have corrupted that prose along with resolving the
    # actual stub. _render_stub() only ever places card_id in one exact
    # spot -- "### {card_id} \xb7 " -- so anchor on that full pattern instead.
    fixed_text = branch_text.replace("### CARD-XXX \xb7 ", f"### {card_id} \xb7 ", 1)
    fixed_text = re.sub(
        r"<!-- next-card-id: CARD-\d{4} -->", f"<!-- next-card-id: {next_marker} -->", fixed_text, count=1,
    )

    _api("PUT", f"/repos/{REPO}/contents/kanban-board.md", token, {
        "message": f"{card_id}: assign real card number at merge",
        "content": base64.b64encode(fixed_text.encode("utf-8")).decode("ascii"),
        "sha": branch_current["sha"],
        "branch": branch,
    })

    _api("PUT", f"/repos/{REPO}/pulls/{pr_number}/merge", token, {
        "commit_title": f"{card_id}: {pr['title'].split(': ', 1)[-1]}",
        "merge_method": merge_method,
    })

    return card_id
