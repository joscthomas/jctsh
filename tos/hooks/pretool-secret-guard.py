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

# A command that IS a sanctioned tool invocation (secret.ps1/secret.py/rotate.py) is
# allowed to name a secret-bearing path -- that's the whole point of those tools
# (CARD-0372's `secret.ps1 writefile`, 2026-10-02: "build it so I don't have to" paste
# a value by hand). Only the PATH-based block below is exempted, and only when the
# entire command is one such invocation with no shell chaining that could smuggle in
# a second, unsanctioned command after it -- `cat secrets.yaml` must still be blocked
# even if it runs right after a legitimate secret.ps1 call. Read/Grep get no exemption:
# there is no sanctioned way to directly Read a secret-bearing file.
CD_PREFIX = re.compile(r"^\s*cd\s+\S+\s*(?:&&|;)\s*", re.I)
CD_ONLY = re.compile(r"^\s*cd\s+\S+\s*$", re.I)
SCRIPT_INVOCATION = re.compile(
    r"^(?:\.[\\/]|\.\\|python3?\s+|py\s+)?tos[\\/](?:secret\.ps1|secret\.py|rotate\.py)\b", re.I
)
SHELL_CHAIN_CHARS = re.compile(r"[;&|`]|\$\(")


def _is_sanctioned_line(line):
    if CD_ONLY.match(line):
        return True
    rest = CD_PREFIX.sub("", line, count=1)
    if not SCRIPT_INVOCATION.match(rest):
        return False
    after_match = SCRIPT_INVOCATION.sub("", rest, count=1)
    return not SHELL_CHAIN_CHARS.search(after_match)


def is_sanctioned_command(command):
    """True only if EVERY line of the command is a bare 'cd <dir>' or a single
    secret.ps1/secret.py/rotate.py invocation (optionally cd-prefixed on that same
    line) with no further shell chaining -- a batch of several sanctioned calls on
    separate lines is fine (CARD-0372, 2026-10-02: writing several device-secret
    values in one multi-line PowerShell block), but a smuggled-in `cat secrets.yaml`,
    whether joined with ;/&& or just sitting on its own line, still blocks the whole
    command. Checked per-line, not just once at the start, specifically so a newline
    can't be used to evade the single-command check the original version only did."""
    lines = [l for l in command.splitlines() if l.strip()]
    return bool(lines) and all(_is_sanctioned_line(l) for l in lines)


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
            haystacks.append((key, value))

    for key, text in haystacks:
        path_exempt = (
            key == "command"
            and tool_name in ("Bash", "PowerShell")
            and is_sanctioned_command(text)
        )
        for pat in SECRET_PATH_PATTERNS:
            if path_exempt:
                break
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
