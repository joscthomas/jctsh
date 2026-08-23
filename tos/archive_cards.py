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
"## Card History" heading in that destination's CLAUDE.md (created if
missing -- tos/CLAUDE.md is a new file the first time a tos-tagged card
archives). components/ was the only place originally checked; core/,
hosts/, and tos itself were added after the first real dry run showed
genuine cards (e.g. CARD-0128, about the auto-PR pipeline tos/ now
contains) falling to the dated archive purely because their real home
wasn't a components/ directory, not because they lacked a real home at
all. Zero or 2+ tag matches fall back to a dated archive file
(tos/kanban-archive.md) rather than guessing which destination was
meant -- an ambiguous or genuinely absent match is a tagging-precision
problem to flag and fix, not something this script should silently paper
over.

A short pointer stub replaces the card in kanban-board.md, keeping the
**Status:** line so it still renders in /kanban's own column view (see
log_server.py's _KANBAN_STATUS_RE, which anchors on that line) instead of
silently vanishing -- consistent with this repo's "never let resolved
work disappear with no trace" convention.

Un-archiving (an already-archived card needing a real update later) is
not automated here -- move it back into kanban-board.md by hand if that
ever comes up, same interactive-judgment treatment as everything else
this script doesn't try to make mechanical.

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

SIZE_THRESHOLD_BYTES = 10_000
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


def is_archive_eligible(card, today, forced_ids=frozenset()):
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
    """Every tag that maps to a real CLAUDE.md-style destination: each
    components/<name>/ and core/<name>/ directory, plus `tos` itself
    (CARD-0193 found real cards -- e.g. CARD-0128, about the auto-PR
    pipeline tos/ now contains -- that belonged under `core/` or `tos/`
    rather than any components/ directory, and were only falling to the
    generic dated archive because the original design only checked
    components/). Returns {tag: (label, claude_md_path)}."""
    dests = {}
    for p in COMPONENTS_DIR.iterdir():
        if p.is_dir():
            dests[p.name] = (p.name, p / "CLAUDE.md")
    for base in ("core", "hosts"):
        base_dir = REPO_ROOT / base
        if not base_dir.is_dir():
            continue
        for p in base_dir.iterdir():
            if p.is_dir():
                dests[p.name] = (f"{base}/{p.name}", p / "CLAUDE.md")
    dests["tos"] = ("tos", TOS_DIR / "CLAUDE.md")
    return dests


def resolve_destination(card, destinations):
    matches = [t for t in card["component_tags"] if t in destinations]
    if len(matches) == 1:
        return "matched", matches[0]
    if len(matches) == 0:
        return "dated", None
    return "ambiguous", matches


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


def apply_plan(plan, today):
    by_path = {}
    dated_entries = []
    for card, kind, dest_path, label, reason in plan:
        block = build_archived_block(card, today, reason)
        if kind == "matched":
            by_path.setdefault(dest_path, (label, []))[1].append(block)
        else:
            dated_entries.append(block)

    written = []
    for path, (label, blocks) in by_path.items():
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        preamble = f"# {label} — Context\n"
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
    for card, kind, dest_path, label, reason in sorted(plan, key=lambda p: p[0]["start"], reverse=True):
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
    args = ap.parse_args()
    forced_ids = set(args.force)

    destinations = discover_destinations()
    text = KANBAN_PATH.read_text(encoding="utf-8")
    cards = parse_cards(text)
    today = date.today()

    eligible = [c for c in cards if is_archive_eligible(c, today, forced_ids)]
    plan = []
    skipped_ambiguous = []
    for card in eligible:
        kind, detail = resolve_destination(card, destinations)
        if kind == "ambiguous":
            skipped_ambiguous.append((card, detail))
            continue
        reason = archive_reason(card, today, forced_ids)
        if kind == "matched":
            label, dest_path = destinations[detail]
            plan.append((card, kind, dest_path, label, reason))
        else:
            plan.append((card, kind, None, None, reason))

    print(f"{len(cards)} total cards, {len(eligible)} archive-eligible, {len(plan)} will be archived.\n")
    for card, kind, dest_path, label, reason in plan:
        tag_note = "no matching tag" if kind == "dated" else f"tag: {label}"
        print(f"  {card['id']} [{card['status']}] {reason} ({tag_note}) -> {display_path(dest_path, today)}")

    if skipped_ambiguous:
        print(f"\n{len(skipped_ambiguous)} SKIPPED (ambiguous tag match, needs manual review):")
        for card, tags in skipped_ambiguous:
            print(f"  {card['id']}: tags {tags} match multiple known directories")

    if not plan:
        print("\nNothing to do.")
        return

    if not args.apply:
        print("\nDry run only -- pass --apply to write these changes.")
        return

    written = apply_plan(plan, today)
    print(f"\nApplied. Files written:")
    for p in written:
        print(f"  {p.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
