# PR Review Checklist

**Author:** Joseph C Thomas (JCT), via Claude
**Purpose:** Step-by-step checklist for reviewing and handling a PR opened against this repo by the auto-PR intake pipeline (`tos/README.md`).
**Version:** 1.0
**Version description:** Initial release — consolidates steps previously scattered across `tos/README.md`, `tos/open_kanban_pr.py`, `tos/land_pr_card.py`, and `JCTsh-Operating-System.md`'s "interview first" rule into one procedural checklist.

---

**Scope:** this covers PRs from the auto-PR intake pipeline — the zero-file-diff, `CARD-XXX`-placeholder-title PRs opened by `open_finding_pr()` for a voice-captured idea, an emailed idea, or an automated maintenance finding (see `tos/README.md`'s pipeline diagram). It does not cover an ordinary code PR (a feature branch with a real file diff) — that follows standard git/GitHub review practice, not this checklist.

## Steps

1. **Skip the self-test PR entirely.** If the PR is from `jctsh-pr-selftest` (CARD-0192's daily self-test of this same intake pipeline), it needs no review — its existence is a successful test result, not a finding needing a decision, and it closes itself on the next day's run. Don't merge, close, or otherwise act on it.

2. **Read the raw finding.** The PR carries zero file diff — the finding's component and message live only in the PR's own title/body (CARD-0190). Read that, not `kanban-board.md`, which nothing touches until merge time.

3. **Decide which merge-time path it needs — never a default:**
   - **Trivial / genuinely self-explanatory** (e.g. a routine container-image-update notice) → the auto-generated stub is fine. Run `resolve_and_merge()` (`tos/open_kanban_pr.py`), which renumbers the PR body straight into a card.
   - **Anything real** → do not just renumber the stub. Per `JCTsh-Operating-System.md`'s "interview first, don't write a card from assumption" rule (CARD-0304), a bare auto-opened title is exactly the one-line card that rule warns against. Instead:
     1. Get Joseph's explicit go-ahead to proceed with this finding.
     2. Interview to fill in a real acceptance-criteria / "done" definition — not just the auto-opened title.
     3. Confirm the finished card text with Joseph.
     4. Run `python tos/land_pr_card.py --pr <N> --body path/to/card_body.md` with that confirmed text.

4. **Never merge or close a PR from this pipeline without Joseph's go-ahead** — summarize what's open and let him decide, per `JCTsh-Session-Start.md` step 4.

5. **Confirm the landed result.** Neither script asks Joseph anything itself — `land_pr_card.py`'s own docstring is explicit that confirming the rendered card against Joseph is a separate step it doesn't perform. Don't treat a PR as landed until that confirmation happens.

## Where the mechanics live (not repeated here)

- **`tos/README.md`** — the pipeline's shape: the three intake sources, why the PR carries no diff, and how the two merge-time functions relate.
- **`tos/open_kanban_pr.py`** module docstring — `open_finding_pr()`/`resolve_and_merge()` mechanics: branch-per-finding, dedup-by-fingerprint, why card numbering is deferred to merge time.
- **`tos/land_pr_card.py`** module docstring — the mechanical tail end of the interview path: reading the number marker fresh, substituting `{id}`, committing, merging, deleting the branch.
- **`JCTsh-Operating-System.md`** — the policy this checklist enforces: "Interview first" (CARD-0304), and the State Transition / Board Column rules a landed card then has to conform to.

**Related:** `kanban-board.md` CARD-0128 (pipeline origin), CARD-0190 (zero-diff PR redesign), CARD-0192 (self-test PR), CARD-0304 (interview-first rule).
