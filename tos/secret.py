#!/usr/bin/env python3
"""secret.py -- CARD-0372's credential helper, M8-hosted (moved off Windows 2026-10-02,
Joseph: "building a dependency on windows... manage it not on windows"). Wraps
keepassxc-cli against this host's vault so nothing needs to see a credential's value
to use it. Deployed to /usr/local/bin/secret.py (root:root, 0755) -- same convention
as maintenance-check.py.

Why M8, not the Windows workstation: the vault's key file is a single root-owned,
0600 file here -- no DPAPI, no per-profile duplication, no cross-profile lock file.
That whole class of problem only existed because of being on a two-user Windows
desktop; one Linux host with one owner doesn't have it. `secret.ps1` on Windows
(tos/secret.ps1) is now a thin SSH wrapper around this script for Joseph's
interactive use (new/copy/set/fingerprint/has) -- `due` (the registry scan) stays
local to Windows, since it only reads credential-registry.yaml and never touches
this vault.

Vault: /home/jct/.jctsh-vault/jctsh-vault.kdbx, key-file-only (no master password).
Key file: /home/jct/.jctsh-vault/jctsh-vault.keyx, mode 0600, owned by jct (the
same account `jct` always had passwordless sudo on this host anyway, so -- same
caveat CARD-0334 already recorded about the Windows Credential Manager -- this is
an at-rest permission boundary, not a barrier against anyone who can already run
code as `jct`/root on this box).

Commands: init, has <name>, fingerprint <name>, new <name> [--length N],
copy <name>, set <name> (interactive, run with `ssh -t` for the masked prompt),
run <name> --env VAR -- <command...> (injects into a child process on THIS host).
"""
import argparse
import hashlib
import subprocess
import sys

VAULT_PATH = "/home/jct/.jctsh-vault/jctsh-vault.kdbx"
KEY_PATH = "/home/jct/.jctsh-vault/jctsh-vault.keyx"
CLI = "keepassxc-cli"


def kp(args, capture=False):
    full = [CLI] + args + ["-k", KEY_PATH, "--no-password"]
    if capture:
        return subprocess.run(full, capture_output=True, text=True)
    return subprocess.run(full)


def cmd_init(_args):
    import os
    checks = [
        ("keepassxc-cli present", subprocess.run(["which", CLI], capture_output=True).returncode == 0),
        ("vault file present", os.path.exists(VAULT_PATH)),
        ("key file present, mode 0600", os.path.exists(KEY_PATH) and oct(os.stat(KEY_PATH).st_mode)[-3:] == "600"),
    ]
    unlock_ok = False
    if all(c[1] for c in checks):
        r = kp(["db-info", VAULT_PATH], capture=True)
        unlock_ok = "Number of entries" in r.stdout
    checks.append(("vault unlocks", unlock_ok))
    for name, ok in checks:
        print(f"[{'OK  ' if ok else 'FAIL'}] {name}")
    sys.exit(0 if all(c[1] for c in checks) else 1)


def cmd_has(args):
    r = kp(["ls", VAULT_PATH, "-f"], capture=True)
    names = [l.strip() for l in r.stdout.splitlines()]
    if args.name in names:
        print(f"yes -- '{args.name}' exists in the vault")
        sys.exit(0)
    print(f"no -- '{args.name}' not found in the vault")
    sys.exit(1)


def cmd_fingerprint(args):
    r = kp(["show", VAULT_PATH, args.name, "-s", "-a", "Password", "-q"], capture=True)
    value = r.stdout.strip()
    if not value:
        print(f"No value read back for '{args.name}' -- does it exist? (secret.py has {args.name})", file=sys.stderr)
        sys.exit(1)
    digest = hashlib.sha256(value.encode()).hexdigest()
    value = None
    print(f"sha256:{digest}")


def cmd_new(args):
    r = kp(["add", VAULT_PATH, args.name, "-q", "-g", "-L", str(args.length), "-l", "-U", "-n", "-s"])
    if r.returncode != 0:
        print(f"keepassxc-cli add failed for '{args.name}' -- does it already exist? (secret.py has {args.name})", file=sys.stderr)
        sys.exit(1)
    # Relay the value once, on stdout, for the caller (secret.ps1's SSH wrapper) to
    # clip and discard -- never written to a file, never logged, this process exits
    # right after.
    r2 = kp(["show", VAULT_PATH, args.name, "-s", "-a", "Password", "-q"], capture=True)
    print(r2.stdout.strip())


def cmd_copy(args):
    r = kp(["show", VAULT_PATH, args.name, "-s", "-a", "Password", "-q"], capture=True)
    value = r.stdout.strip()
    if not value:
        print(f"Could not read '{args.name}' -- does it exist? (secret.py has {args.name})", file=sys.stderr)
        sys.exit(1)
    print(value)


def cmd_set(args):
    r = kp(["ls", VAULT_PATH, "-f"], capture=True)
    names = [l.strip() for l in r.stdout.splitlines()]
    verb = "edit" if args.name in names else "add"
    print(f"Prompting for '{args.name}'s new value -- masked, read from this terminal only "
          f"(run with `ssh -t` so the prompt actually works).", file=sys.stderr)
    subprocess.run([CLI, verb, VAULT_PATH, args.name, "-k", KEY_PATH, "--no-password", "-p"])


def cmd_run(args):
    r = kp(["show", VAULT_PATH, args.name, "-s", "-a", "Password", "-q"], capture=True)
    value = r.stdout.strip()
    if not value:
        print(f"No value read back for '{args.name}'.", file=sys.stderr)
        sys.exit(1)
    import os
    env = os.environ.copy()
    env[args.env] = value
    proc = subprocess.run(args.command, env=env, capture_output=True, text=True)
    masked = args.command  # noqa: F841 -- not used, kept for clarity the command itself never carries the value
    stdout_masked = proc.stdout.replace(value, "[REDACTED]")
    stderr_masked = proc.stderr.replace(value, "[REDACTED]")
    value = None
    if stdout_masked:
        print(stdout_masked, end="")
    if stderr_masked:
        print(f"STDERR: {stderr_masked}", end="", file=sys.stderr)
    sys.exit(proc.returncode)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)

    sub.add_parser("init")

    p_has = sub.add_parser("has")
    p_has.add_argument("name")

    p_fp = sub.add_parser("fingerprint")
    p_fp.add_argument("name")

    p_new = sub.add_parser("new")
    p_new.add_argument("name")
    p_new.add_argument("--length", type=int, default=32)

    p_copy = sub.add_parser("copy")
    p_copy.add_argument("name")

    p_set = sub.add_parser("set")
    p_set.add_argument("name")

    p_run = sub.add_parser("run")
    p_run.add_argument("name")
    p_run.add_argument("--env", required=True)
    # Not argparse.REMAINDER here: it's documented-unreliable when mixed with a
    # required optional in the same subparser (bpo-9540/17050) -- split on a literal
    # `--` ourselves instead, before argparse ever sees the child command's own args.
    p_run.add_argument("command", nargs="*", help=argparse.SUPPRESS)

    argv = sys.argv[1:]
    command = None
    if argv and argv[0] == "run" and "--" in argv:
        dash = argv.index("--")
        argv, command = argv[:dash], argv[dash + 1:]

    args = p.parse_args(argv)
    if args.action == "run":
        if not command:
            p_run.error("missing child command after '--' (e.g. secret.py run <name> --env VAR -- <command> [args...])")
        args.command = command

    {
        "init": cmd_init,
        "has": cmd_has,
        "fingerprint": cmd_fingerprint,
        "new": cmd_new,
        "copy": cmd_copy,
        "set": cmd_set,
        "run": cmd_run,
    }[args.action](args)


if __name__ == "__main__":
    main()
