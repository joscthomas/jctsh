#!/usr/bin/env python3
"""CARD-0334 Phase 1c, step 1 of 2 -- DO NOT RUN THIS FROM A CLAUDE CODE SESSION.

Run by Joseph himself, in his own terminal, outside any session (same bypass
CARD-0334 decision 3 already established for reading credentials.local.md
directly). Reads every backtick-quoted token in credentials.local.md as a
candidate secret value, salts and SHA-256-hashes each one, and writes out ONLY
the hashes + lengths -- never a value, never a hint beyond "something this
length exists". This is what lets the PostToolUse tripwire (1c, step 2)
recognize a known secret appearing in some command's output without the
tripwire itself ever holding the real values either.

Output: tos/hooks/secret-fingerprints.json and tos/hooks/.secret-salt (a fresh
random salt, generated once). BOTH MUST STAY OUT OF GIT -- add them to
.gitignore before the first run. A salted hash of a weak/guessable secret
(several of the Mosquitto/device passwords are short and non-random) is not
meaningfully protected by the salt alone the way a long random token's hash
is; keeping this workstation-local, never committed, is the actual protection,
same class of caution as credentials.local.md itself.

Usage: python tos/hooks/generate-fingerprints.py
"""
import json
import hashlib
import os
import re
import secrets as _secrets
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDS_FILE = os.path.join(REPO_ROOT, "credentials.local.md")
SALT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".secret-salt")
OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secret-fingerprints.json")

TOKEN_PATTERN = re.compile(r"`([^`]{6,})`")


def main():
    if not os.path.exists(CREDS_FILE):
        print(f"Not found: {CREDS_FILE}", file=sys.stderr)
        sys.exit(1)

    if os.path.exists(SALT_FILE):
        with open(SALT_FILE, "r") as f:
            salt = f.read().strip()
    else:
        salt = _secrets.token_hex(32)
        with open(SALT_FILE, "w") as f:
            f.write(salt)
        print(f"Generated a new salt at {SALT_FILE} -- back this up (e.g. a RoboForm "
              f"Safenote) the same way the vault key file was, or a workstation loss "
              f"means regenerating fingerprints from scratch is the only recovery.")

    with open(CREDS_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    seen = set()
    fingerprints = []
    for match in TOKEN_PATTERN.finditer(content):
        value = match.group(1)
        if value in seen:
            continue
        seen.add(value)
        digest = hashlib.sha256((salt + value).encode("utf-8")).hexdigest()
        fingerprints.append({"length": len(value), "hash": digest})
        value = None  # never held longer than this iteration

    with open(OUT_FILE, "w") as f:
        json.dump(fingerprints, f, indent=2)

    print(f"Wrote {len(fingerprints)} fingerprints to {OUT_FILE} (values-free -- "
          f"safe to inspect, but keep both this file and {SALT_FILE} out of git).")


if __name__ == "__main__":
    main()
