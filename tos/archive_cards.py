"""CARD-0193: archive Done/Defer kanban cards that are big enough (or old
enough) to be worth moving out of the live tos/kanban-board.md.

Interactive-only, run manually by Claude and reviewed before --apply --
not yet wired to a periodic timer, same "prove it before automating"
discipline CARD-0173's Tasker rollout used (manual first, automate only
once proven). Dry run by default; pass --apply to actually write changes.

Archive-eligible: **Status:** is Done or Defer, AND (the card's full block
exceeds SIZE_THRESHOLD_BYTES OR its latest-mentioned date is older than
AGE_BACKUP_DAYS). Size is the primary trigger -- real data showed a
strongly skewed distribution where a handful of very verbose cards
dominate the file's size, while age-based archiving alone would sit idle
for months on a young project. Age is a slow secondary backup, not the
primary lever.

Destination: if exactly one of a card's bracketed tags (after the first,
which is always the type -- idea/enhancement/bug) matches a real
components/<name>/, core/<name>/, or hosts/<name>/ directory, or the
literal tag `tos`, the card's full text is appended verbatim under a
"## Card History" heading in that destination's card-archive.md (created
if missing -- tos/card-archive.md is a new file the first time a
tos-tagged card archives). components/ was the only place originally
checked; core/, hosts/, and tos itself were added after the first real
dry run showed genuine cards (e.g. CARD-0128, about the auto-PR pipeline
tos/ now contains) falling to the dated archive purely because their
real home wasn't a components/ directory, not because they lacked a real
home at all. Zero tag matches fall back to a dated archive file
(tos/kanban-archive.md) rather than guessing which destination was
meant. **2+ tag matches: see the CARD-0193 reopen note below -- this
paragraph's original "skip for manual review" behavior for that case was
superseded 2026-09-27.**

CARD-0290: destination changed from CLAUDE.md to a dedicated card-archive.md
sibling, 2026-09-17 -- appending archived cards directly into CLAUDE.md let
it grow unboundedly (hike-izer's reached 485KB) and conflated two different
purposes: CLAUDE.md is supposed to be curated "constraints and gotchas"
context (read every component/cluster-session startup, JCTsh-Component-
Session-Start.md), while archived card history is an on-demand-only
historical record -- exactly the same working-file-vs-archive split
kanban-board.md/kanban-archive.md already went through. Every existing
component's CLAUDE.md was migrated to this split in the same pass that
changed this destination logic; going forward, new archiving only ever
writes to card-archive.md, never CLAUDE.md.

A short pointer stub replaces the card in kanban-board.md, keeping the
**Status:** line so it still renders in /kanban's own column view (see
log_server.py's _KANBAN_STATUS_RE, which anchors on that line) instead of
silently vanishing -- consistent with this repo's "never let resolved
work disappear with no trace" convention.

Un-archiving (an already-archived card needing a real update later) is
not automated here -- move it back into kanban-board.md by hand if that
ever comes up, same interactive-judgment treatment as everything else
this script doesn't try to make mechanical.

CARD-0193 (reopened 2026-09-27): a 2+-tag-match card is no longer skipped
for manual review. The **primary destination is the first of the card's
own bracketed tags, in the order written, that matches a real directory**
-- arbitrary where there's no clearly-better owner, but deterministic and
reproducible (Joseph's explicit call, rather than letting these accumulate
in permanent manual-review limbo -- 4 cards were stuck this way on one
ordinary archiving pass). The full card archives there exactly as a
single-match card would. **Every other matching tag gets a short pointer
stub instead of a full duplicate** -- one line under that directory's own
`## Card History` heading naming the card and where its full text actually
lives, so it stays discoverable from any of its tagged directories without
a second copy that could drift from the first. Zero-match cards are
unaffected -- still fall to the dated `tos/kanban-archive.md`.

Usage:
    python archive_cards.py                 # dry run, prints the plan
    python archive_cards.py --apply         # actually writes the changes
"""
import argparse
import re
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KANBAN_PATH = REPO_ROOT / "tos" / "kanban-board.md"
COMPONENTS_DIR = REPO_ROOT / "components"
TOS_DIR = REPO_ROOT / "tos"

SIZE_THRESHOLD_BYTES = 5_000
AGE_BACKUP_DAYS = 90
CARD_HISTORY_HEADING = "## Card History"

_CARD_RE = re.compile(
    r"^### CARD-(\d{4}) · ((?:\[[^\]]+\]\s*)+)(.*?)\s*$",
    re.MULTILINE,
)
_TAG_RE = re.compile(r"\[([^\]]+)\]")
_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(\w+)", re.MULTILINE)
_DATE_RE = re.compile(r"\b(20[2-9]\d-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))\b")


def parse_cards(text):
    """Split kanban-board.md into card dicts. Mirrors log_server.py's own
    card-boundary logic (next '### CARD-' or EOF) but extracts *all*
    bracketed tags, not just the first, since destination routing needs
    every tag a card carries, not just log_server.py's display-only one."""
    matches = list(_CARD_RE.finditer(text))
    today = date.today()
    cards = []
    for i, m in enumerate(matches):
        card_id = f"CARD-{m.group(1)}"
        tags = _TAG_RE.findall(m.group(2))
        component_tags = tags[1:]  # tags[0] is always the type
        header_start = m.start()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[header_start:body_end]
        body = text[body_start:body_end]

        status_m = _STATUS_RE.search(body)
        status = status_m.group(1) if status_m else None

        latest_date = None
        for d in _DATE_RE.finditer(body):
            try:
                dt = datetime.strptime(d.group(1), "%Y-%m-%d").date()
            except ValueError:
                continue
            if dt <= today and (latest_date is None or dt > latest_date):
                latest_date = dt

        cards.append({
            "id": card_id, "component_tags": component_tags, "status": status,
            "start": header_start, "end": body_end, "block": block,
            "size": len(block.encode("utf-8")), "latest_date": latest_date,
        })
    return cards


def is_archive_eligible(card, today, forced_ids=frozenset(), excluded_ids=frozenset()):
    if card["id"] in excluded_ids:
        return False  # --exclude wins over both the automatic threshold and --force
    if card["status"] not in ("Done", "Defer"):
        return False  # --force never bypasses the status gate, only the size/age threshold
    if card["id"] in forced_ids:
        return True
    if card["size"] > SIZE_THRESHOLD_BYTES:
        return True
    if card["latest_date"] is not None and (today - card["latest_date"]).days > AGE_BACKUP_DAYS:
        return True
    return False


def archive_reason(card, today, forced_ids):
    """Human-readable why-was-this-archived text, shared by the annotation
    left on the moved card (see build_archive_note) and the stub's own note
    -- computed once from the same fields the eligibility check itself used,
    so the recorded reason can never drift from the actual trigger."""
    parts = []
    if card["size"] > SIZE_THRESHOLD_BYTES:
        parts.append(f"{card['size']}B, over the {SIZE_THRESHOLD_BYTES}B size threshold")
    if card["latest_date"] is not None and (today - card["latest_date"]).days > AGE_BACKUP_DAYS:
        days = (today - card["latest_date"]).days
        parts.append(f"{days} days since last touched, over the {AGE_BACKUP_DAYS}-day backup threshold")
    if card["id"] in forced_ids:
        parts.append("manually forced (--force)")
    return "; ".join(parts) if parts else "reason not recorded"


def discover_destinations():
    """Every tag that maps to a real card-archive.md-style destination: each
    components/<name>/ and core/<name>/ directory, plus `tos` itself
    (CARD-0193 found real cards -- e.g. CARD-0128, about the auto-PR
    pipeline tos/ now contains -- that belonged under `core/` or `tos/`
    rather than any components/ directory, and were only falling to the
    generic dated archive because the original design only checked
    components/). Returns {tag: (label, card_archive_path)}.

    CARD-0290: destination file is card-archive.md, not CLAUDE.md -- see
    this module's own docstring for why.

    CARD-0294: `architecture` (the new residual home for genuinely
    cross-cutting cards, a repo-root peer of components/core/hosts/tos, not
    a subdirectory of any of them) needs the same explicit entry `tos`
    already gets -- this function never walked the repo root generically,
    so a new top-level directory is invisible to it until added here.

    CARD-0316: `network` (DNS/domain-level concerns, another repo-root
    peer) needs the same explicit entry, for the same reason."""
    dests = {}
    for p in COMPONENTS_DIR.iterdir():
        if p.is_dir():
            dests[p.name] = (p.name, p / "card-archive.md")
    for base in ("core", "hosts"):
        base_dir = REPO_ROOT / base
        if not base_dir.is_dir():
            continue
        for p in base_dir.iterdir():
            if p.is_dir():
                dests[p.name] = (f"{base}/{p.name}", p / "card-archive.md")
    dests["tos"] = ("tos", TOS_DIR / "card-archive.md")
    dests["architecture"] = ("architecture", REPO_ROOT / "architecture" / "card-archive.md")
    dests["network"] = ("network", REPO_ROOT / "network" / "card-archive.md")
    return dests


def resolve_destination(card, destinations):
    """Every card tag that matches a real destination, in the order the
    card itself lists them. Zero matches: dated archive. One or more:
    the first is the primary (full text archives there); any rest are
    secondaries (CARD-0193 -- get a pointer stub instead of a duplicate)."""
    matches = [t for t in card["component_tags"] if t in destinations]
    if len(matches) == 0:
        return "dated", None, []
    return "matched", matches[0], matches[1:]


def build_stub(card, archive_path, today, reason):
    header_line = card["block"].splitlines()[0]
    return (
        f"{header_line}\n"
        f"**Status:** {card['status']}\n\n"
        f"Archived to `{archive_path}` on {today.isoformat()} (CARD-0193) — {reason}.\n\n"
        f"---\n\n"
    )


def build_archived_block(card, today, reason):
    """The card's own verbatim text, prefixed with a short note recording
    when and why it was moved -- the note sits *before* the original
    heading, outside the card's own text, so the archived copy still reads
    as "the card, plus a small provenance marker," not a rewritten card."""
    return (
        f"**Archived from `tos/kanban-board.md` on {today.isoformat()} (CARD-0193)** — {reason}.\n\n"
        f"{card['block'].strip()}"
    )


def build_pointer_stub(card, primary_path, today, reason):
    """CARD-0193: a one-line pointer for a secondary tag match -- the card's
    full text lives at `primary_path` instead; this just makes it
    discoverable from every directory it's also tagged with, without a
    second copy of the text that could drift from the first."""
    header_line = card["block"].splitlines()[0]
    primary_rel = display_path(primary_path, today)
    return (
        f"{header_line}\n\n"
        f"Archived in full to `{primary_rel}` on {today.isoformat()} (CARD-0193) — {reason}. "
        f"Also tagged here; this is a pointer only, not a duplicate."
    )


def append_under_heading(existing_text, heading, addition, fresh_preamble):
    """Insert `addition` right after `heading` -- before the next top-level
    '## ' heading if one follows, else at EOF. Creates `heading` at the end
    of the file (after `fresh_preamble` if the file doesn't exist yet) if
    it isn't already present. Keeps repeated runs appending in the same
    place instead of scattering entries across the file."""
    if existing_text is None:
        return fresh_preamble.rstrip("\n") + "\n\n" + heading + "\n\n" + addition.strip() + "\n"
    if heading in existing_text:
        start = existing_text.index(heading) + len(heading)
        rest = existing_text[start:]
        next_m = re.search(r"\n## ", rest)
        insert_at = start + (next_m.start() if next_m else len(rest))
        before = existing_text[:insert_at].rstrip("\n")
        after = existing_text[insert_at:].lstrip("\n")
        joined = before + "\n\n" + addition.strip() + "\n\n"
        return joined + after if after else joined
    return existing_text.rstrip("\n") + "\n\n" + heading + "\n\n" + addition.strip() + "\n"


def apply_plan(plan, today, destinations):
    by_path = {}
    dated_entries = []
    for card, kind, dest_path, label, reason, secondary_tags in plan:
        block = build_archived_block(card, today, reason)
        if kind == "matched":
            by_path.setdefault(dest_path, (label, []))[1].append(block)
            for sec_tag in secondary_tags:
                sec_label, sec_path = destinations[sec_tag]
                stub = build_pointer_stub(card, dest_path, today, reason)
                by_path.setdefault(sec_path, (sec_label, []))[1].append(stub)
        else:
            dated_entries.append(block)

    written = []
    for path, (label, blocks) in by_path.items():
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        preamble = (
            f"# {label} — Card Archive\n\n"
            f"Historical record of archived Done/Defer kanban cards for this component "
            f"(CARD-0193). Not read as part of routine Session Start or component/cluster-"
            f"session startup (JCTsh-Component-Session-Start.md) -- on-demand lookup only. "
            f"See this component's own CLAUDE.md for current, curated context.\n"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        new_text = append_under_heading(existing, CARD_HISTORY_HEADING, "\n\n".join(blocks), preamble)
        path.write_text(new_text, encoding="utf-8")
        written.append(path)

    if dated_entries:
        path = TOS_DIR / "kanban-archive.md"
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        preamble = (
            f"# JCTsh Kanban Archive\n\n"
            f"Cards archived from `tos/kanban-board.md` (CARD-0193) because they were "
            f"Done/Defer and either large ({SIZE_THRESHOLD_BYTES}B+) or old "
            f"({AGE_BACKUP_DAYS}+ days) enough to move out of the live working file, "
            f"with no single matching `components/<name>/`, `core/<name>/`, `hosts/<name>/`, "
            f"or `tos` tag to migrate into instead. Not read by the auto-PR intake "
            f"pipeline or Session Start -- "
            f"purely a historical record. See the stub left in `tos/kanban-board.md` "
            f"for the pointer back."
        )
        new_text = append_under_heading(existing, "## Archived Cards", "\n\n".join(dated_entries), preamble)
        path.write_text(new_text, encoding="utf-8")
        written.append(path)

    # Splice stubs into kanban-board.md, highest offset first so earlier
    # offsets in the same pass stay valid.
    text = KANBAN_PATH.read_text(encoding="utf-8")
    for card, kind, dest_path, label, reason, secondary_tags in sorted(plan, key=lambda p: p[0]["start"], reverse=True):
        stub = build_stub(card, display_path(dest_path, today), today, reason)
        text = text[:card["start"]] + stub + text[card["end"]:]
    KANBAN_PATH.write_text(text, encoding="utf-8")
    written.append(KANBAN_PATH)
    return written


def display_path(dest_path, today):
    if dest_path is None:
        return "tos/kanban-archive.md"
    return str(dest_path.relative_to(REPO_ROOT)).replace("\\", "/")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry run, plan only)")
    ap.add_argument(
        "--force", action="append", default=[], metavar="CARD-NNNN",
        help="Include a specific card even if it doesn't meet the automatic "
             "size/age threshold -- for edge cases just under the line "
             "(e.g. a card that was legitimately eligible before an "
             "incidental edit shifted its byte count). Repeatable.",
    )
    ap.add_argument(
        "--exclude", action="append", default=[], metavar="CARD-NNNN",
        help="Skip a specific card even if it meets the automatic size/age "
             "threshold -- for a Done/Defer card that still carries an active "
             "Watch-for/Auto-verify marker Session Start's grep depends on "
             "finding in the live file (see CARD-0251). Repeatable, and wins "
             "over --force if the same id is passed to both.",
    )
    args = ap.parse_args()
    forced_ids = set(args.force)
    excluded_ids = set(args.exclude)

    destinations = discover_destinations()
    text = KANBAN_PATH.read_text(encoding="utf-8")
    cards = parse_cards(text)
    today = date.today()

    eligible = [c for c in cards if is_archive_eligible(c, today, forced_ids, excluded_ids)]
    plan = []
    for card in eligible:
        kind, detail, secondary_tags = resolve_destination(card, destinations)
        reason = archive_reason(card, today, forced_ids)
        if kind == "matched":
            label, dest_path = destinations[detail]
            plan.append((card, kind, dest_path, label, reason, secondary_tags))
        else:
            plan.append((card, kind, None, None, reason, []))

    print(f"{len(cards)} total cards, {len(eligible)} archive-eligible, {len(plan)} will be archived.\n")
    for card, kind, dest_path, label, reason, secondary_tags in plan:
        tag_note = "no matching tag" if kind == "dated" else f"tag: {label}"
        if secondary_tags:
            sec_labels = [destinations[t][0] for t in secondary_tags]
            tag_note += f", pointer stub(s) in: {', '.join(sec_labels)}"
        print(f"  {card['id']} [{card['status']}] {reason} ({tag_note}) -> {display_path(dest_path, today)}")

    if not plan:
        print("\nNothing to do.")
        return

    if not args.apply:
        print("\nDry run only -- pass --apply to write these changes.")
        return

    written = apply_plan(plan, today, destinations)
    print(f"\nApplied. Files written:")
    for p in written:
        print(f"  {p.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
