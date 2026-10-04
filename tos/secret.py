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
(tos/secret.ps1) is a thin SSH wrapper around this script for Joseph's interactive
use, and `rotate.py` (tos/rotate.py, the rotation runner) drives the rotation
commands below over the same SSH path -- `due` (the registry scan) stays local to
Windows, since it only reads credential-registry.yaml and never touches this vault.

Vault: /home/jct/.jctsh-vault/jctsh-vault.kdbx, key-file-only (no master password).
Key file: /home/jct/.jctsh-vault/jctsh-vault.keyx, mode 0600, owned by jct (the
same account `jct` always had passwordless sudo on this host anyway, so -- same
caveat CARD-0334 already recorded about the Windows Credential Manager -- this is
an at-rest permission boundary, not a barrier against anyone who can already run
code as `jct`/root on this box). JCTSH_VAULT_DIR overrides the directory (tests).

Entry names follow the registry: `<id>`, or `<id>--<account>` for a grouped entry.
A rotation keeps up to three entries per credential:
    <name>.next      the staged new value (before cutover)
    <name>           the current value
    <name>.previous  the old value, kept after cutover until `drop-previous`

Commands -- the only ones that ever print a value are `new` and `copy`, whose stdout
is meant for secret.ps1's clipboard relay, never a terminal or a session:
  init                         doctor check, no values
  has <name>                   does an entry exist (title only)
  ls                           entry titles, no values
  fingerprint <name>           SHA-256 of the value, never the value
  new <name> [--length N] [--no-special]
                               generate a brand-new entry; value relayed once on stdout
  copy <name>                  value on stdout, for the clipboard relay
  set <name>                   interactive masked prompt (run with `ssh -t`)
  run <name> --env VAR [--env VAR=<entry>]... [--stdin <entry>] -- <command...>
                               run a command on THIS host with values injected; every
                               injected value is masked out of its output
  reach <user@host>            can this host SSH there non-interactively (BatchMode)
  -- rotation (rotate.py drives these; usable by hand too) --
  stage <name> [--length N] [--special] [--prompt] [--replace]
                               create <name>.next: generated (default 40, alphanumeric --
                               safe in .env/YAML/headers) or typed at a masked prompt
                               (--prompt, for values a service mints, e.g. an HA token)
  promote <name>               cutover: <name> -> <name>.previous, <name>.next -> <name>
  unpromote <name>             undo a promote: <name> discarded, <name>.previous -> <name>
  discard-next <name>          purge a staged <name>.next (abort before cutover)
  drop-previous <name>         purge <name>.previous (the vault half of "revoke")
  envfile --file PATH [--host user@host] [--sudo] [--set VAR=<entry>]...
          [--set-text VAR=TEXT]... [--unset VAR]... [--restart CMD]
                               edit KEY=VALUE lines in an env file, locally or over SSH,
                               then optionally run a restart command on that same host.
                               Values travel on stdin only (never argv, never a temp
                               file); the file is replaced atomically with its mode and
                               owner kept; prints variable names only.

Every command that changes the vault takes an exclusive lock first, so two runs (a
rotation and a hand-run `set`, or two SSH sessions) can't interleave writes.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time

VAULT_DIR = os.environ.get("JCTSH_VAULT_DIR", "/home/jct/.jctsh-vault")
VAULT_PATH = os.path.join(VAULT_DIR, "jctsh-vault.kdbx")
KEY_PATH = os.path.join(VAULT_DIR, "jctsh-vault.keyx")
LOCK_PATH = os.path.join(VAULT_DIR, ".secret.lock")
CLI = "keepassxc-cli"
RECYCLE = "Recycle Bin"

# Generated rotation values are alphanumeric by default: every holder format this
# project uses (.env files that docker compose interpolates, YAML, HTTP headers,
# ESPHome secrets) takes them without quoting. 40 chars of [A-Za-z0-9] is ~238 bits.
STAGE_DEFAULT_LENGTH = 40


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def kp(args, capture=False, input_text=None):
    full = [CLI] + args + ["-k", KEY_PATH, "--no-password"]
    if capture or input_text is not None:
        return subprocess.run(full, capture_output=True, text=True, input=input_text)
    return subprocess.run(full)


@contextlib.contextmanager
def vault_lock(timeout=60):
    """Exclusive lock for anything that writes the vault."""
    fd = os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o600)
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > deadline:
                    die(f"vault is locked by another secret.py run (waited {timeout}s): {LOCK_PATH}")
                time.sleep(0.5)
        yield
    finally:
        os.close(fd)  # closing the descriptor releases the flock


def entry_names():
    """Top-level entry titles (the recycle bin's contents are excluded)."""
    r = kp(["ls", VAULT_PATH, "-f"], capture=True)
    if r.returncode != 0:
        die(f"could not list the vault: {r.stderr.strip()}")
    return {l.strip() for l in r.stdout.splitlines() if l.strip() and "/" not in l.strip()}


def read_value(name):
    r = kp(["show", VAULT_PATH, name, "-s", "-a", "Password", "-q"], capture=True)
    value = r.stdout.rstrip("\r\n")
    return value if r.returncode == 0 and value else None


def short_fp(value):
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()[:12]


# A paste into keepassxc-cli's masked prompt, over `ssh -t` from Windows Terminal, can arrive
# wrapped in bracketed-paste markers (ESC[200~ ... ESC[201~) -- the prompt reads the terminal
# raw, so they end up IN the stored value (found live 2026-10-03: a 93-char GitHub token
# stored as 105). Stop the terminal sending them, then strip any that still got in.
PASTE_MARKERS = re.compile(r"\x1b\[20[01]~")


def disable_bracketed_paste():
    if sys.stderr.isatty():
        sys.stderr.write("\x1b[?2004l")
        sys.stderr.flush()


def clean_pasted(name):
    """Strip paste markers and stray surrounding whitespace from a stored value, in place.
    Returns how many characters were removed (0 = it was already clean). Never prints a value."""
    value = read_value(name)
    if not value:
        return 0
    cleaned = PASTE_MARKERS.sub("", value).strip()
    if cleaned == value:
        return 0
    if not cleaned:
        die(f"'{name}' is empty once the paste markers are removed -- nothing to keep.")
    r = kp(["edit", VAULT_PATH, name, "-p", "-q"], capture=True, input_text=cleaned + "\n")
    if r.returncode != 0 or read_value(name) != cleaned:
        die(f"could not rewrite '{name}' with the cleaned value -- left unchanged.")
    return len(value) - len(cleaned)


def rename(old, new):
    r = kp(["edit", VAULT_PATH, old, "-t", new, "-q"], capture=True)
    if r.returncode != 0:
        die(f"could not rename '{old}' to '{new}': {r.stderr.strip()}")


def purge(name):
    """Delete an entry for good -- a plain `rm` only moves it to the recycle bin,
    which would leave the old value sitting in the vault."""
    r = kp(["rm", VAULT_PATH, name, "-q"], capture=True)
    if r.returncode != 0:
        die(f"could not delete '{name}': {r.stderr.strip()}")
    for _ in range(20):  # the bin can hold several same-titled copies
        r = kp(["rm", VAULT_PATH, f"{RECYCLE}/{name}", "-q"], capture=True)
        if r.returncode != 0:
            break


# --- original commands ---------------------------------------------------------

def cmd_init(_args):
    checks = [
        ("keepassxc-cli present", subprocess.run(["which", CLI], capture_output=True).returncode == 0),
        ("vault file present", os.path.exists(VAULT_PATH)),
        ("key file present, mode 0600", os.path.exists(KEY_PATH) and oct(os.stat(KEY_PATH).st_mode)[-3:] == "600"),
    ]
    unlock_ok = False
    if all(c[1] for c in checks):
        r = kp(["db-info", VAULT_PATH], capture=True)
        unlock_ok = "Number of entries" in r.stdout or r.returncode == 0
    checks.append(("vault unlocks", unlock_ok))
    for name, ok in checks:
        print(f"[{'OK  ' if ok else 'FAIL'}] {name}")
    sys.exit(0 if all(c[1] for c in checks) else 1)


def cmd_has(args):
    if args.name in entry_names():
        print(f"yes -- '{args.name}' exists in the vault")
        sys.exit(0)
    print(f"no -- '{args.name}' not found in the vault")
    sys.exit(1)


def cmd_ls(_args):
    for name in sorted(entry_names()):
        print(name)


def cmd_fingerprint(args):
    value = read_value(args.name)
    if not value:
        die(f"No value read back for '{args.name}' -- does it exist? (secret.py has {args.name})")
    digest = hashlib.sha256(value.encode()).hexdigest()
    value = None
    print(f"sha256:{digest}")


def cmd_new(args):
    with vault_lock():
        gen = ["-g", "-L", str(args.length), "-l", "-U", "-n"] + ([] if args.no_special else ["-s"])
        r = kp(["add", VAULT_PATH, args.name, "-q"] + gen, capture=True)
        if r.returncode != 0:
            die(f"keepassxc-cli add failed for '{args.name}' -- does it already exist? (secret.py has {args.name})")
    # Relay the value once, on stdout, for the caller (secret.ps1's SSH wrapper) to
    # clip and discard -- never written to a file, never logged, this process exits
    # right after.
    print(read_value(args.name) or "")


def cmd_copy(args):
    value = read_value(args.name)
    if not value:
        die(f"Could not read '{args.name}' -- does it exist? (secret.py has {args.name})")
    print(value)


def cmd_set(args):
    with vault_lock(timeout=5):
        verb = "edit" if args.name in entry_names() else "add"
        print(f"Prompting for '{args.name}'s new value -- masked, read from this terminal only "
              f"(run with `ssh -t` so the prompt actually works).", file=sys.stderr)
        disable_bracketed_paste()
        subprocess.run([CLI, verb, VAULT_PATH, args.name, "-k", KEY_PATH, "--no-password", "-p"])
        removed = clean_pasted(args.name)
        if removed:
            print(f"(removed {removed} stray paste/whitespace characters from the pasted value)", file=sys.stderr)


def cmd_clean(args):
    with vault_lock():
        removed = clean_pasted(args.name)
        value = read_value(args.name)
    if value is None:
        die(f"No value read back for '{args.name}'.")
    print(f"'{args.name}': " + (f"removed {removed} stray characters" if removed else "already clean")
          + f" -- now {len(value)} characters, {short_fp(value)}")


def parse_bindings(name, env_specs):
    """`--env VAR` binds <name>; `--env VAR=<entry>` binds that entry."""
    out = []
    for spec in env_specs:
        var, _, entry = spec.partition("=")
        if not var.isidentifier():
            die(f"--env '{spec}': '{var}' is not a valid environment variable name")
        out.append((var, entry or name))
    return out


def cmd_run(args):
    values = {}
    env = os.environ.copy()
    for var, entry in parse_bindings(args.name, args.env):
        if entry not in values:
            values[entry] = read_value(entry)
            if not values[entry]:
                die(f"No value read back for '{entry}'.")
        env[var] = values[entry]
    stdin_text = None
    if args.stdin:
        stdin_text = values.get(args.stdin) or read_value(args.stdin)
        if not stdin_text:
            die(f"No value read back for '{args.stdin}'.")
        values[args.stdin] = stdin_text
        stdin_text += "\n"
    proc = subprocess.run(args.command, env=env, capture_output=True, text=True, input=stdin_text)
    out, err = proc.stdout, proc.stderr
    # Longest first, so a value that contains another can't leave a fragment behind.
    for v in sorted(set(values.values()), key=len, reverse=True):
        out = out.replace(v, "[REDACTED]")
        err = err.replace(v, "[REDACTED]")
    values = env = stdin_text = None
    if out:
        print(out, end="")
    if err:
        print(f"STDERR: {err}", end="", file=sys.stderr)
    sys.exit(proc.returncode)


def ssh_base(host):
    return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host]


def cmd_reach(args):
    r = subprocess.run(ssh_base(args.host) + ["true"], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"yes -- this host can SSH to {args.host} non-interactively")
        sys.exit(0)
    print(f"no -- this host cannot SSH to {args.host} non-interactively ({r.stderr.strip() or 'exit ' + str(r.returncode)})")
    sys.exit(1)


# --- rotation commands ---------------------------------------------------------

def cmd_stage(args):
    nxt = f"{args.name}.next"
    with vault_lock():
        if nxt in entry_names():
            if not args.replace:
                die(f"'{nxt}' already exists -- a rotation is already staged. Finish or abort it, "
                    f"or pass --replace to throw that staged value away.")
            purge(nxt)
        if args.prompt:
            if not sys.stdin.isatty():
                die("--prompt needs a terminal (run through `ssh -t`).")
            print(f"Paste the new value for '{args.name}' (masked):", file=sys.stderr)
            disable_bracketed_paste()
            r = subprocess.run([CLI, "add", VAULT_PATH, nxt, "-k", KEY_PATH, "--no-password", "-p"])
            if r.returncode != 0:
                die(f"could not create '{nxt}'")
            removed = clean_pasted(nxt)
            if removed:
                print(f"(removed {removed} stray paste/whitespace characters from the pasted value)", file=sys.stderr)
        else:
            gen = ["-g", "-L", str(args.length), "-l", "-U", "-n"] + (["-s"] if args.special else [])
            r = kp(["add", VAULT_PATH, nxt, "-q"] + gen, capture=True)
            if r.returncode != 0:
                die(f"could not create '{nxt}': {r.stderr.strip()}")
        value = read_value(nxt)
        if not value:
            purge(nxt)
            die(f"'{nxt}' came back empty -- nothing staged.")
        print(f"staged {nxt} ({short_fp(value)})")


def cmd_promote(args):
    name, nxt, prev = args.name, f"{args.name}.next", f"{args.name}.previous"
    with vault_lock():
        names = entry_names()
        if nxt not in names:
            if name in names and prev in names:
                print(f"already promoted: {name} is current, {prev} kept")
                return
            die(f"nothing staged: '{nxt}' does not exist")
        if name in names:
            if prev in names:
                die(f"'{prev}' still exists from an earlier rotation -- run drop-previous {name} first.")
            rename(name, prev)
        rename(nxt, name)
        print(f"promoted: {name} is now the new value" + (f"; old value kept as {prev}" if name in names else ""))


def cmd_unpromote(args):
    name, prev = args.name, f"{args.name}.previous"
    with vault_lock():
        names = entry_names()
        if prev not in names:
            die(f"'{prev}' does not exist -- nothing to restore")
        if name in names:
            purge(name)
        rename(prev, name)
        print(f"unpromoted: {name} is the old value again; the new value was deleted")


def cmd_discard_next(args):
    nxt = f"{args.name}.next"
    with vault_lock():
        if nxt not in entry_names():
            print(f"nothing to discard: '{nxt}' does not exist")
            return
        purge(nxt)
        print(f"discarded {nxt}")


def cmd_drop_previous(args):
    prev = f"{args.name}.previous"
    with vault_lock():
        if prev not in entry_names():
            print(f"nothing to drop: '{prev}' does not exist")
            return
        purge(prev)
        print(f"dropped {prev}")


# Runs on the target host (locally or through SSH) as `python3 -c`; reads a JSON
# payload with the values from stdin, so no value is ever in argv or a temp file.
ENVFILE_EDITOR = r'''
import json, os, sys, tempfile
p = json.loads(sys.stdin.read())
path = os.path.expanduser(p["path"])
with open(path, "rb") as f:
    raw = f.read().decode("utf-8")
nl = "\r\n" if "\r\n" in raw else "\n"
lines = raw.splitlines()
def key_of(line):
    s = line.strip()
    if s.startswith("export "):
        s = s[7:].lstrip()
    if not s or s.startswith("#") or "=" not in s:
        return None
    return s.split("=", 1)[0].strip()
sets, unset = p["set"], set(p["unset"])
changed, added, removed, out, seen = [], [], [], [], set()
for line in lines:
    k = key_of(line)
    if k in unset:
        removed.append(k)
        continue
    if k in sets:
        if k in seen:
            removed.append(k)  # a duplicate line would shadow or be shadowed by ours
            continue
        prefix = "export " if line.strip().startswith("export ") else ""
        out.append(prefix + k + "=" + sets[k])
        seen.add(k)
        changed.append(k)
        continue
    out.append(line)
for k, v in sets.items():
    if k not in seen:
        out.append(k + "=" + v)
        added.append(k)
st = os.stat(path)
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".envfile-")
try:
    with os.fdopen(fd, "w", newline="") as f:
        f.write(nl.join(out) + nl)
    os.chmod(tmp, st.st_mode & 0o7777)
    if os.geteuid() == 0:
        os.chown(tmp, st.st_uid, st.st_gid)
    os.replace(tmp, path)
except BaseException:
    os.unlink(tmp)
    raise
with open(path, encoding="utf-8") as f:
    check = {key_of(l): l.split("=", 1)[1] for l in f.read().splitlines() if key_of(l)}
bad = [k for k, v in sets.items() if check.get(k) != v] + [k for k in unset if k in check]
print(json.dumps({"changed": changed, "added": added, "removed": sorted(set(removed)), "mismatch": bad}))
sys.exit(1 if bad else 0)
'''

# A value written raw into KEY=VALUE must not need quoting -- docker compose, systemd
# EnvironmentFile and a shell `source` all read these characters the same way.
ENV_SAFE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:+/@%,=~")


def cmd_envfile(args):
    if args.sudo and args.file.startswith("~"):
        die("--sudo with a '~' path would expand to root's home -- give the absolute path.")
    sets, values = {}, []
    for spec in args.set:
        var, _, entry = spec.partition("=")
        if not var.isidentifier() or not entry:
            die(f"--set '{spec}': expected VAR=<vault entry>")
        value = read_value(entry)
        if not value:
            die(f"No value read back for '{entry}'.")
        if not set(value) <= ENV_SAFE:
            die(f"'{entry}' contains characters an env file can misread (quotes, spaces, $, #, ...) -- "
                f"refusing to write it raw. Stage values with the default alphanumeric charset.")
        sets[var] = value
        values.append(value)
    for spec in args.set_text:
        var, _, text = spec.partition("=")
        if not var.isidentifier() or not set(text) <= ENV_SAFE:
            die(f"--set-text '{spec}': expected VAR=TEXT with no characters needing quotes")
        sets[var] = text
    unset = list(args.unset)
    if not sets and not unset:
        die("nothing to do: give --set, --set-text or --unset")
    payload = json.dumps({"path": args.file, "set": sets, "unset": unset})

    editor = ["python3", "-c", ENVFILE_EDITOR]
    if args.sudo:
        editor = ["sudo", "-n"] + editor
    if args.host:
        cmd = ssh_base(args.host) + [" ".join(shlex.quote(c) for c in editor)]
    else:
        cmd = editor
    r = subprocess.run(cmd, input=payload, capture_output=True, text=True)
    payload = sets = None
    out, err = r.stdout, r.stderr
    for v in values:
        out, err = out.replace(v, "[REDACTED]"), err.replace(v, "[REDACTED]")
    where = f"{args.host}:{args.file}" if args.host else args.file
    try:
        res = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        die(f"envfile edit failed on {where}: {err.strip() or out.strip() or 'exit ' + str(r.returncode)}")
    if r.returncode != 0 or res.get("mismatch"):
        die(f"envfile edit on {where} did not verify: mismatch={res.get('mismatch')} {err.strip()}")
    parts = [f"{k} {', '.join(res[k])}" for k in ("changed", "added", "removed") if res[k]]
    print(f"envfile {where}: " + ("; ".join(parts) or "no change") + " (verified)")

    if args.restart:
        rc = ssh_base(args.host) + [args.restart] if args.host else ["sh", "-c", args.restart]
        rr = subprocess.run(rc, capture_output=True, text=True)
        tail = (rr.stderr.strip() or rr.stdout.strip()).splitlines()[-3:]
        if rr.returncode != 0:
            die(f"restart failed on {args.host or 'this host'} (exit {rr.returncode}): {' | '.join(tail)}")
        print(f"restart ok on {args.host or 'this host'}: {args.restart}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="action", required=True)

    sub.add_parser("init")
    sub.add_parser("ls")
    for name in ("has", "fingerprint", "copy", "set", "promote", "unpromote", "discard-next", "drop-previous"):
        sub.add_parser(name).add_argument("name")

    p_new = sub.add_parser("new")
    p_new.add_argument("name")
    p_new.add_argument("--length", type=int, default=32)
    p_new.add_argument("--no-special", action="store_true")

    p_stage = sub.add_parser("stage")
    p_stage.add_argument("name")
    p_stage.add_argument("--length", type=int, default=STAGE_DEFAULT_LENGTH)
    p_stage.add_argument("--special", action="store_true")
    p_stage.add_argument("--prompt", action="store_true")
    p_stage.add_argument("--replace", action="store_true")

    p_clean = sub.add_parser("clean")
    p_clean.add_argument("name")

    p_reach = sub.add_parser("reach")
    p_reach.add_argument("host")

    p_env = sub.add_parser("envfile")
    p_env.add_argument("--file", required=True)
    p_env.add_argument("--host")
    p_env.add_argument("--sudo", action="store_true")
    p_env.add_argument("--set", action="append", default=[])
    p_env.add_argument("--set-text", action="append", default=[])
    p_env.add_argument("--unset", action="append", default=[])
    p_env.add_argument("--restart")

    p_run = sub.add_parser("run")
    p_run.add_argument("name")
    p_run.add_argument("--env", action="append", default=[])
    p_run.add_argument("--stdin")
    # Not argparse.REMAINDER here: it's documented-unreliable when mixed with
    # optionals in the same subparser (bpo-9540/17050) -- split on a literal `--`
    # ourselves instead, before argparse ever sees the child command's own args.
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
        if not args.env and not args.stdin:
            p_run.error("give at least one --env VAR[=<entry>] or --stdin <entry>")
        args.command = command

    {
        "init": cmd_init, "has": cmd_has, "ls": cmd_ls, "fingerprint": cmd_fingerprint,
        "new": cmd_new, "copy": cmd_copy, "set": cmd_set, "run": cmd_run, "reach": cmd_reach,
        "stage": cmd_stage, "promote": cmd_promote, "unpromote": cmd_unpromote,
        "discard-next": cmd_discard_next, "drop-previous": cmd_drop_previous,
        "envfile": cmd_envfile, "clean": cmd_clean,
    }[args.action](args)


if __name__ == "__main__":
    main()
