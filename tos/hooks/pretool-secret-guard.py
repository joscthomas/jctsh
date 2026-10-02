#!/usr/bin/env python3
"""PreToolUse hook -- CARD-0334 Phase 1b.

Blocks a Bash/PowerShell/Read/Grep call before it runs if it either (a) touches a
known secret-bearing path, or (b) its own command text contains something that
looks like a secret literal (a JWT, a Bearer token, a password=/key=/token=
assignment, a known provider-key prefix). (b) is what Phase 1a's static deny
rules can't catch -- a path-based rule only stops touching the FILE, not pasting
a value that's already in hand into some other command.

NOT YET LIVE-VERIFIED. CARD-0372 has an open item that the simpler Phase 1a deny
rules didn't visibly block anything in the session that drafted them -- until
that's confirmed fixed (fresh-session retest), don't trust this one either.
Claude Code's exact PreToolUse stdin/exit-code contract is implemented here to
the best of this session's knowledge, not verified against the live tool.

Fails OPEN on anything it can't parse or doesn't recognize -- a broken hook
should never be the reason routine work stops; it should only ever narrow what
it blocks, not what it allows by accident.
"""
import json
import re
import sys

SECRET_PATH_PATTERNS = [
    re.compile(r"credentials\.local\.md", re.I),
    re.compile(r"secrets\.yaml", re.I),
    re.compile(r"secrets\.h\b", re.I),
    re.compile(r"(^|[\\/])\.env$", re.I),
    re.compile(r"\.esphome[\\/]", re.I),
]

SECRET_SHAPED_PATTERNS = [
    (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "a JWT"),
    (re.compile(r"Bearer\s+[A-Za-z0-9._-]{10,}", re.I), "a Bearer token"),
    (re.compile(r"(api[_-]?key|password|secret|token)\s*[:=]\s*[\"']?[A-Za-z0-9._-]{8,}", re.I),
     "a key=/password=/token= style assignment"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "a GitHub PAT"),
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), "an Anthropic API key"),
]

GUARDED_TOOLS = {"Bash", "PowerShell", "Read", "Grep"}


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    if tool_name not in GUARDED_TOOLS:
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    haystacks = []
    for key in ("command", "file_path", "path", "pattern"):
        value = tool_input.get(key)
        if isinstance(value, str):
            haystacks.append(value)

    for text in haystacks:
        for pat in SECRET_PATH_PATTERNS:
            if pat.search(text):
                print(
                    f"Blocked: {tool_name} touches a secret-bearing path "
                    f"(matched {pat.pattern!r}). Use tos/secret.ps1 instead, or run "
                    f"this by hand outside the session (CARD-0334's bypass).",
                    file=sys.stderr,
                )
                sys.exit(2)
        for pat, label in SECRET_SHAPED_PATTERNS:
            if pat.search(text):
                print(
                    f"Blocked: {tool_name}'s command text looks like it contains "
                    f"{label}. Never put a secret literal in a command -- read it "
                    f"inside the command instead, or via tos/secret.ps1.",
                    file=sys.stderr,
                )
                sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
