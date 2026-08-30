"""CARD-0128: open a PR against kanban-board.md for a maintenance finding.

Pure GitHub REST API -- no local git clone or `gh` CLI needed on the M8/Pi
(neither host has one, and this session's own git access from the dev
machine turned out to be plain `git push`, not the `gh` CLI, so there was
nothing to reuse). Imported by maintenance-check.py / pi-maintenance-check.py,
not run standalone.

CARD-0190: open_finding_pr() creates a branch ref pointing at an *empty*
commit (same tree as main, just a new commit object -- the minimal thing
that satisfies GitHub's "head and base must differ" requirement for opening
a PR) and never touches kanban-board.md at all; the finding's component and
message live only in the PR's own title/body. The real kanban-board.md
insertion happens once, at merge time, in resolve_and_merge(), which parses
the finding back out of the PR body. This replaced an earlier design where
open_finding_pr() itself wrote a CARD-XXX stub into kanban-board.md on the
branch -- broke once that file crossed GitHub's Contents API's 1MB
content-size limit (confirmed live, 2026-08-22: every call started failing
with "substring not found", since the API's `content` field silently comes
back empty over that threshold, with no error). Deferring to merge time also
means only the much-less-frequent, interactive merge path needs the
size-safe read (_get_file_text(), the `application/vnd.github.raw` media
type) rather than every single automated open.

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
caught during review): open_finding_pr() never reads or bumps main's
next-card-id marker -- every PR title/number stays CARD-XXX until merge.
Real number assignment happens at merge time instead (resolve_and_merge()),
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
        # CARD-0192, found live: DELETE (e.g. deleting a branch ref) returns
        # 204 No Content -- an empty body. json.loads(b'') raises
        # JSONDecodeError, not caught by callers that only expect
        # urllib.error.HTTPError. Every existing caller before CARD-0192
        # only ever hit GET/POST/PUT/PATCH against endpoints that always
        # return a body, so this was latent until the first DELETE caller.
        raw = resp.read()
        return json.loads(raw) if raw else None


def _pr_still_open(pr_number, token):
    try:
        data = _api("GET", f"/repos/{REPO}/pulls/{pr_number}", token)
        return data.get("state") == "open"
    except urllib.error.HTTPError:
        return False


def close_pr(pr_number, token):
    """Close a PR without merging, and delete its branch (CARD-0192's
    daily self-test cleanup -- each run closes the previous run's test PR
    before opening a fresh one). Tolerant of the PR already being closed/
    merged/gone -- cleanup failing shouldn't block opening today's test.
    Catches Exception broadly, not just HTTPError -- this is best-effort
    cleanup, not something that should ever block opening today's real
    test PR, whatever the failure mode turns out to be."""
    try:
        _api("PATCH", f"/repos/{REPO}/pulls/{pr_number}", token, {"state": "closed"})
    except Exception:
        pass
    try:
        pr = _api("GET", f"/repos/{REPO}/pulls/{pr_number}", token)
        _api("DELETE", f"/repos/{REPO}/git/refs/heads/{pr['head']['ref']}", token)
    except Exception:
        pass


def _get_file_text(path, ref, token):
    """Raw text content of `path` at `ref` (CARD-0190). GitHub's Contents API
    only populates the JSON `content` field for files under 1MB -- over that
    (kanban-board.md crossed this in August 2026: confirmed live via a real
    "substring not found" failure, since the empty `content` decoded to an
    empty string), it comes back empty with no error. The `application/
    vnd.github.raw` media type bypasses the JSON+base64 envelope entirely and
    returns the file's actual bytes, which works up to 100MB."""
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
    tree lookup rather than the Contents API's metadata `sha` field -- needed
    for the Contents API PUT's optimistic-concurrency check, without any
    dependence on how that same endpoint behaves for files over its 1MB
    content-size limit (only the JSON metadata is being read here, no file
    content download at all -- trees report blob sha regardless of size)."""
    ref_data = _api("GET", f"/repos/{REPO}/git/refs/heads/{ref}", token)
    commit = _api("GET", f"/repos/{REPO}/git/commits/{ref_data['object']['sha']}", token)
    tree = _api("GET", f"/repos/{REPO}/git/trees/{commit['tree']['sha']}?recursive=1", token)
    for entry in tree["tree"]:
        if entry["path"] == path:
            return entry["sha"]
    raise FileNotFoundError(f"{path} not found in {ref}'s tree")


def _title_line(message, limit):
    """First line of `message` only, truncated to `limit` chars -- CARD-0151
    found live that a blind message[:limit] slice (the original behavior)
    can cut straight through a message's own "\\n\\n" into unrelated
    content that happens to follow it (e.g. a forwarded email's header
    block), producing a garbled multi-line title. Every existing caller
    passes single-line messages, so splitting on the first line first is
    a no-op for them -- this only changes behavior for messages that
    actually contain a newline."""
    first_line = message.split("\n", 1)[0]
    return first_line if len(first_line) <= limit else first_line[:limit - 3] + "…"


def _render_stub(card_id, component, message, now, image_url=None):
    """CARD-0227: `image_url`, when given, is rendered right after the raw
    finding -- unlike open_finding_pr()'s PR body, this stub has no code
    fence to dodge, so the markdown image line can just be appended
    directly."""
    ts = now.strftime("%Y-%m-%d %H:%M %Z") or now.strftime("%Y-%m-%d %H:%M UTC")
    title = _title_line(message, 80)
    image_line = f"\n\n![idea image]({image_url})" if image_url else ""
    return (
        f"### {card_id} · [enhancement] [infrastructure] {title} — auto-opened from {component}\n"
        f"**Status:** Backlog\n\n"
        f"**Auto-generated {ts} from {component}'s maintenance check.** "
        f"Raw finding: {message}. Needs a human/Claude interview pass to scope "
        f"real acceptance criteria — this stub only captures that something "
        f"was found, not what \"done\" looks like.{image_line}\n\n"
        f"**Related:** live dashboard entry at time of generation.\n\n---\n\n"
    )


def open_finding_pr(component, message, fingerprint, token, state, image_url=None):
    """Idempotent per fingerprint. `state` is the caller's own persisted
    throttle-state dict (already fingerprint-keyed for the Alert
    notification) -- this reads/extends it with pr_fingerprint/pr_number,
    caller is responsible for persisting the returned dict same as it
    already persists its own state. Returns (state, pr_url_or_None) --
    pr_url is None when an existing open PR already covers this finding,
    so the caller can tell "nothing new happened" from "opened one".

    CARD-0227: `image_url`, when given, is rendered as a markdown image
    line in the PR body -- deliberately placed *outside* the "Finding:"
    fenced code block below, since a markdown image reference inside a
    fence renders as literal text, not an image."""
    if (state.get("pr_fingerprint") == fingerprint
            and state.get("pr_number")
            and _pr_still_open(state["pr_number"], token)):
        return state, None

    main_ref = _api("GET", f"/repos/{REPO}/git/refs/heads/{BRANCH_BASE}", token)
    main_sha = main_ref["object"]["sha"]

    now = datetime.now(timezone.utc)
    branch = f"maintenance-alert/{component}-{now.strftime('%Y-%m-%d-%H%M%S')}"

    # CARD-0190: no longer reads or writes kanban-board.md here at all --
    # that file crossed GitHub's 1MB Contents API content-size limit and
    # every call started failing with "substring not found" (content comes
    # back empty over that threshold, with no error). The real insertion
    # happens once, at merge time, in resolve_and_merge(), which needs the
    # size-safe fix regardless since it's the one place still touching the
    # real file. This branch only needs a commit that differs from main so
    # GitHub will accept the PR (a zero-commit-diff branch 422s) -- an empty
    # commit (identical tree to main, new message) satisfies that with no
    # file touched at all. Component + message travel in the PR's own
    # title/body (already-existing format), parsed back out by
    # resolve_and_merge() at merge time.
    main_commit = _api("GET", f"/repos/{REPO}/git/commits/{main_sha}", token)
    empty_commit = _api("POST", f"/repos/{REPO}/git/commits", token, {
        "message": f"CARD-XXX: {_title_line(message, 60)}",
        "tree": main_commit["tree"]["sha"],
        "parents": [main_sha],
    })
    _api("POST", f"/repos/{REPO}/git/refs", token, {
        "ref": f"refs/heads/{branch}", "sha": empty_commit["sha"],
    })

    body = (
        f"Auto-opened by {component}'s maintenance check (CARD-0128).\n\n"
        f"Finding:\n```\n{message}\n```\n\n"
    )
    if image_url:
        body += f"![idea image]({image_url})\n\n"
    body += (
        f"Card number is a placeholder (`CARD-XXX`) -- real numbering, and the "
        f"actual kanban-board.md insertion, both happen at merge time (CARD-0190), "
        f"not here, to avoid a race between concurrent findings from different "
        f"hosts and to sidestep kanban-board.md's size on every single open. "
        f"See resolve_and_merge(). This PR intentionally shows no file changes "
        f"until then."
    )

    pr = _api("POST", f"/repos/{REPO}/pulls", token, {
        "title": f"CARD-XXX: {_title_line(message, 72)}",
        "head": branch,
        "base": BRANCH_BASE,
        "body": body,
    })

    new_state = dict(state)
    new_state["pr_fingerprint"] = fingerprint
    new_state["pr_number"] = pr["number"]
    return new_state, pr["html_url"]


_FINDING_BODY_RE = re.compile(
    r"Auto-opened by (?P<component>.+?)'s maintenance check.*?"
    r"Finding:\n```\n(?P<message>.*?)\n```\n\n"
    # CARD-0227: optional -- present only when open_finding_pr() was called
    # with image_url, matching the exact line it appends right after the
    # fence closes.
    r"(?:!\[idea image\]\((?P<image_url>[^)]+)\)\n\n)?",
    re.DOTALL,
)
_BRANCH_TS_RE = re.compile(r"-(\d{4}-\d{2}-\d{2}-\d{6})$")


def resolve_and_merge(pr_number, token, merge_method="squash"):
    """Interactive-use only (Claude, when asked to merge a CARD-0128 PR) --
    not called by the deployed scripts. Reads main's next-card-id marker
    *now* (not whenever the PR happened to be opened), renders the real
    stub, pushes a fixup commit on the PR's own branch, then merges -- so
    the commit that actually lands on main is already fully correct, never
    a moment where main shows a literal CARD-XXX. Returns the assigned
    card_id.

    CARD-0190: open_finding_pr() no longer writes a stub into the branch at
    all (that required reading/writing kanban-board.md at open time, which
    broke once the file crossed GitHub's 1MB Contents API content-size
    limit) -- the branch is just an empty commit, and the finding's
    component/message live only in the PR's own title/body. This function
    now parses those back out of the PR body and renders the stub fresh via
    _render_stub(), against a freshly-read `main` (same "never trust a
    stale copy" discipline the original 2026-07-31 fix established, now
    simpler since there's no branch-side stub content to reconcile against
    at all -- only main's kanban-board.md is ever read for content)."""
    pr = _api("GET", f"/repos/{REPO}/pulls/{pr_number}", token)
    branch = pr["head"]["ref"]

    body_match = _FINDING_BODY_RE.search(pr.get("body") or "")
    if not body_match:
        raise ValueError(f"PR #{pr_number}: could not parse component/finding from its body")
    component = body_match.group("component")
    message = body_match.group("message")
    image_url = body_match.group("image_url")

    # Recover the original raised-at time from the branch name's own
    # "-YYYY-MM-DD-HHMMSS" suffix (already embedded there since
    # open_finding_pr() builds the branch name from it) so the rendered
    # stub's "Auto-generated {ts}" line reflects when the finding actually
    # happened, not when it happened to get merged.
    ts_match = _BRANCH_TS_RE.search(branch)
    now = (
        datetime.strptime(ts_match.group(1), "%Y-%m-%d-%H%M%S").replace(tzinfo=timezone.utc)
        if ts_match else datetime.now(timezone.utc)
    )

    main_text = _get_file_text("tos/kanban-board.md", BRANCH_BASE, token)
    m = re.search(r"<!-- next-card-id: (CARD-\d{4}) -->", main_text)
    card_id = m.group(1)
    next_marker = f"CARD-{int(card_id[5:]) + 1:04d}"

    stub = _render_stub(card_id, component, message, now, image_url=image_url)

    new_main_text = main_text.replace(
        f"<!-- next-card-id: {card_id} -->", f"<!-- next-card-id: {next_marker} -->", 1,
    )
    insert_at = new_main_text.index("---\n\n") + len("---\n\n")
    new_main_text = new_main_text[:insert_at] + stub + new_main_text[insert_at:]

    branch_file_sha = _blob_sha_at("tos/kanban-board.md", branch, token)
    _api("PUT", f"/repos/{REPO}/contents/tos/kanban-board.md", token, {
        "message": f"{card_id}: assign real card number at merge",
        "content": base64.b64encode(new_main_text.encode("utf-8")).decode("ascii"),
        "sha": branch_file_sha,
        "branch": branch,
    })

    commit_title = f"{card_id}: {pr['title'].split(': ', 1)[-1]}"
    try:
        _api("PUT", f"/repos/{REPO}/pulls/{pr_number}/merge", token, {
            "commit_title": commit_title, "merge_method": merge_method,
        })
    except urllib.error.HTTPError as e:
        # CARD-0128, hit live 2026-07-31 merging two same-session PRs back
        # to back: every stub inserts at the *same* fixed anchor point (the
        # intro's first "---\n\n"), so any two PRs open at once will have
        # identical surrounding context there -- git's 3-way merge can't
        # tell "two independent additions" from "a real conflict" and
        # rejects it, even though the fixup above already produced fully
        # correct final content. Not a rare edge case: it's the ordinary
        # case whenever more than one PR is open simultaneously. Recover by
        # constructing the merge commit directly via the Git Data API
        # (explicit two-parent commit: main's current tip + this branch's
        # tip, tree = the already-correct content above) instead of asking
        # GitHub to reconcile two diffs that touch the same lines.
        if e.code not in (405, 422):
            raise
        main_ref2 = _api("GET", f"/repos/{REPO}/git/refs/heads/{BRANCH_BASE}", token)
        main_sha2 = main_ref2["object"]["sha"]
        branch_ref2 = _api("GET", f"/repos/{REPO}/git/refs/heads/{branch}", token)
        branch_sha2 = branch_ref2["object"]["sha"]
        branch_file_sha2 = _blob_sha_at("tos/kanban-board.md", branch, token)
        main_commit2 = _api("GET", f"/repos/{REPO}/git/commits/{main_sha2}", token)
        new_tree = _api("POST", f"/repos/{REPO}/git/trees", token, {
            "base_tree": main_commit2["tree"]["sha"],
            "tree": [{"path": "tos/kanban-board.md", "mode": "100644", "type": "blob",
                      "sha": branch_file_sha2}],
        })
        merge_commit = _api("POST", f"/repos/{REPO}/git/commits", token, {
            "message": f"Merge {BRANCH_BASE} into {branch} ({card_id} conflict workaround)",
            "tree": new_tree["sha"], "parents": [main_sha2, branch_sha2],
        })
        _api("PATCH", f"/repos/{REPO}/git/refs/heads/{branch}", token, {"sha": merge_commit["sha"]})
        _api("PUT", f"/repos/{REPO}/pulls/{pr_number}/merge", token, {
            "commit_title": commit_title, "merge_method": "merge",  # not squash -- would re-diff and re-conflict
        })

    return card_id
