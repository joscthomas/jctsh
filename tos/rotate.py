#!/usr/bin/env python3
"""rotate.py -- CARD-0372's credential rotation runner.

Runs on the workstation, where tos/credential-registry.yaml lives. Never sees a
value: every vault operation is a `secret.py` call on the M8 over SSH (values stay
there), and a value a person must paste goes straight from the M8 to the Windows
clipboard through `secret.ps1 copy` (auto-cleared). Output is holder names,
pass/fail and short fingerprints only.

    rotate.py plan     <target>      the plan, offline -- no M8, nothing changes
    rotate.py verify   <target>      run each holder's check against the CURRENT value
    rotate.py start    <target> [--prompt] [--window-days N] [--no-current] [--restage]
    rotate.py continue <target>      resume after a manual step or an interruption
    rotate.py status   [<target>]    rotations in progress
    rotate.py confirm-synced <target>  you pasted the new value into RoboForm
    rotate.py finish   <target> [--force]   revoke the old value, record last_rotated
    rotate.py abort    <target>      before cutover: put the old value back, drop the new

<target> is a registry id, or <id>--<account> for an entry with an `accounts:` map
(one account at a time). The vault entry and the RoboForm entry use the same name.

The lifecycle (CARD-0372's "one fixed lifecycle"):
  start     preflight; stage <name>.next in the vault (generated, or typed with
            --prompt for a value a service mints); the rotation's window closes
            `--window-days` from now (default 14)
  holders   in registry order. A holder with an `apply:` map is updated by the
            runner (secret.py envfile + restart) and checked (`check_cmd`, else you
            confirm its `verify`); any other holder is guided: the new value goes on
            your clipboard and the runner waits for you to say it's done.
            A dual-accept holder (apply.previous_var) gets the new value AND keeps
            the old one valid until the window closes -- the server enforces that
            itself, so a phone or device can move later without an outage.
  cutover   every holder done: <name>.next becomes <name>, the old value is kept as
            <name>.previous; the registry gets roboform_synced: false
  RoboForm  paste the new value into RoboForm, then `confirm-synced`
  finish    once RoboForm is confirmed (or the window has closed, or --force):
            dual-accept holders drop the old value, the vault purges
            <name>.previous, the registry gets last_rotated: <today> and
            rotation_requested: null. Commit the registry afterwards.

State: one values-free JSON file per rotation in tos/.rotation-state/ (gitignored,
shared by both Windows profiles since they use the same checkout), plus a lock file
there so two runs can't overlap. A run can stop anywhere and `continue` picks up.

Environment (for tests and odd setups): JCTSH_REGISTRY, JCTSH_ROTATION_STATE,
JCTSH_M8_HOST (default jct@m8.local), JCTSH_M8=local (run tos/secret.py on this
host instead of over SSH), JCTSH_ANSWERS (comma-separated answers for the prompts),
JCTSH_CLIP=none (never touch the clipboard), JCTSH_TODAY (YYYY-MM-DD).
"""
import argparse
import datetime as dt
import json
import os
import re
import shlex
import socket
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.environ.get("JCTSH_REGISTRY", os.path.join(HERE, "credential-registry.yaml"))
STATE_DIR = os.environ.get("JCTSH_ROTATION_STATE", os.path.join(HERE, ".rotation-state"))
M8_HOST = os.environ.get("JCTSH_M8_HOST", "jct@m8.local")
M8_SECRET = "/usr/local/bin/secret.py"
DEFAULT_WINDOW_DAYS = 14   # CARD-0372 decision 6 (draft)

# Exit codes: 0 ok, 1 failed/refused, 3 stopped and waiting on a person (resume with `continue`).
WAITING = 3


class Stop(Exception):
    def __init__(self, msg, code=1):
        super().__init__(msg)
        self.code = code


# --- registry parsing ------------------------------------------------------------
# The registry is YAML, but it is also read line by line by secret.ps1's `due` and
# edited in place by this runner (so comments survive), so it keeps a strict shape:
# `  - id:` starts an entry, `    key: value` is a field, and `holders:`/`accounts:`
# items are one-line flow maps. This parser reads exactly that shape, stdlib only.

def _parse_flow(s, i=0):
    """Parse one YAML flow value starting at s[i]. Returns (value, next_index)."""
    def ws(i):
        while i < len(s) and s[i] in " \t":
            i += 1
        return i
    i = ws(i)
    c = s[i] if i < len(s) else ""
    if c == "{":
        out, i = {}, ws(i + 1)
        while i < len(s) and s[i] != "}":
            j = s.index(":", i)
            key = s[i:j].strip()
            val, i = _parse_flow(s, j + 1)
            out[key] = val
            i = ws(i)
            if i < len(s) and s[i] == ",":
                i = ws(i + 1)
        return out, i + 1
    if c == "[":
        out, i = [], ws(i + 1)
        while i < len(s) and s[i] != "]":
            val, i = _parse_flow(s, i)
            out.append(val)
            i = ws(i)
            if i < len(s) and s[i] == ",":
                i = ws(i + 1)
        return out, i + 1
    if c == '"':
        buf, i = [], i + 1
        while s[i] != '"':
            if s[i] == "\\":
                i += 1
                buf.append({"n": "\n", "t": "\t"}.get(s[i], s[i]))
            else:
                buf.append(s[i])
            i += 1
        return "".join(buf), i + 1
    if c == "'":
        j = i + 1
        while True:
            j = s.index("'", j)
            if j + 1 < len(s) and s[j + 1] == "'":
                j += 2
                continue
            break
        return s[i + 1:j].replace("''", "'"), j + 1
    j = i
    while j < len(s) and s[j] not in ",]}":
        j += 1
    return _plain(s[i:j].strip()), j


def _plain(t):
    # yes/no too: YAML 1.1 (what PyYAML reads this file as) treats them as booleans.
    return {"null": None, "~": None, "": None, "true": True, "false": False,
            "yes": True, "no": False}.get(t, t)


def _field_value(rest):
    """The value part of a `    key: value   # comment` line."""
    rest = rest.strip()
    if rest[:1] in ('"', "'", "[", "{"):
        return _parse_flow(rest)[0]
    return _plain(re.split(r"\s+#", rest, maxsplit=1)[0].strip())


def load_registry(path=REGISTRY):
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    # A Windows checkout may have CRLF (git autocrlf): parse without the \r, and
    # save_lines() puts it back so a write-back never mixes line endings.
    crlf = "\r\n" in text
    lines = text.replace("\r\n", "\n").split("\n")
    entries, cur, section = {"__crlf__": crlf}, None, None
    for n, line in enumerate(lines):
        m = re.match(r"^  - id:\s*(\S+)\s*$", line)
        if m:
            cur = {"id": m.group(1), "fields": {}, "field_line": {}, "holders": [], "accounts": {},
                   "account_line": {}, "shared": [], "start": n, "end": n}
            entries[cur["id"]] = cur
            section = None
            continue
        if cur is None:
            continue
        if not line.strip():
            cur = None
            continue
        cur["end"] = n
        m = re.match(r"^    (\w+):\s*$", line)
        if m:
            section = m.group(1)
            continue
        m = re.match(r"^      - (\{.*\})\s*$", line)
        if m and section == "holders":
            cur["holders"].append(_parse_flow(m.group(1))[0])
            continue
        m = re.match(r"^      ([\w.-]+):\s*(\{.*\})\s*$", line)
        if m and section == "accounts":
            cur["accounts"][m.group(1)] = _parse_flow(m.group(2))[0]
            cur["account_line"][m.group(1)] = n
            continue
        m = re.match(r"^    (\w+):\s*(.*)$", line)
        if m:
            section = None
            key, val = m.group(1), _field_value(m.group(2))
            cur["fields"][key] = val
            cur["field_line"][key] = n
            if key.endswith("_holder") and isinstance(val, dict):
                cur["shared"].append((key, val))
    return entries, lines


def save_lines(lines, crlf, path=REGISTRY):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(("\r\n" if crlf else "\n").join(lines))
    os.replace(tmp, path)


def resolve(entries, target):
    eid, _, acct = target.partition("--")
    e = entries.get(eid) if eid != "__crlf__" else None
    if not e:
        raise Stop(f"no registry entry '{eid}' in {REGISTRY}")
    if e["fields"].get("retired"):
        raise Stop(f"'{eid}' is retired ({e['fields']['retired']}) -- nothing to rotate")
    if acct:
        if acct not in e["accounts"]:
            raise Stop(f"'{eid}' has no account '{acct}'. Accounts: {', '.join(e['accounts']) or 'none'}")
        if e["accounts"][acct].get("retired"):
            raise Stop(f"'{target}' is retired ({e['accounts'][acct]['retired']}) -- nothing to rotate")
    elif e["accounts"]:
        live = [a for a, v in e["accounts"].items() if not v.get("retired")]
        raise Stop(f"'{eid}' is a grouped entry -- rotate one account at a time: "
                   + ", ".join(f"{eid}--{a}" for a in live))
    return e, acct or None


def holders_for(e, acct):
    """Every place the target's value must change, in the order to change them."""
    raw = []
    if acct:
        a = dict(e["accounts"][acct])
        a.setdefault("where", a.get("holder"))
        raw.append((f"[{acct}] ", a))
    raw += [("[shared] ", h) for _, h in e["shared"]]
    raw += [("", h) for h in e["holders"]]
    out = []
    for i, (prefix, h) in enumerate(raw):
        where = h.get("where") or h.get("holder") or "?"
        apply = h.get("apply") if isinstance(h.get("apply"), dict) else None
        if apply is not None:
            apply = dict(apply)
            apply.setdefault("var", h.get("var"))
        out.append({
            "key": f"{i}:{where}",
            "label": prefix + where,
            "kind": h.get("kind") or "manual",
            "var": h.get("var"),
            "verify": h.get("verify"),
            "note": h.get("note"),
            "apply": apply if apply and apply.get("envfile") and apply.get("var") else None,
            "check_cmd": h.get("check_cmd"),
        })
    return out


# --- registry write-back -----------------------------------------------------------

def _account_set(line, field, value):
    pat = re.compile(rf'(\b{field}:\s*)("(?:[^"\\]|\\.)*"|[^,}}]+)')
    if pat.search(line):
        return pat.sub(lambda m: m.group(1) + value, line, count=1)
    return re.sub(r"\}\s*$", f", {field}: {value}}}", line)


def registry_set(target, field, value, comment=None):
    """Set one field on the target (an entry, or one account of a grouped entry),
    keeping every other line -- comments included -- exactly as it was."""
    entries, lines = load_registry()
    eid, _, acct = target.partition("--")
    e = entries[eid]
    if acct:
        n = e["account_line"][acct]
        lines[n] = _account_set(lines[n], field, value)
    elif field in e["field_line"]:
        n = e["field_line"][field]
        lines[n] = f"    {field}: {value}" + (f"   # {comment}" if comment else "")
    else:
        after = next((e["field_line"][k] for k in ("roboform", "last_rotated") if k in e["field_line"]), e["start"])
        lines.insert(after + 1, f"    {field}: {value}" + (f"   # {comment}" if comment else ""))
    save_lines(lines, entries["__crlf__"])


# --- M8 / clipboard / prompts --------------------------------------------------------

def secret(args, tty=False, check=True):
    """Run secret.py on the M8. Its output never carries a value for the commands used here."""
    if os.environ.get("JCTSH_M8") == "local":
        cmd = [sys.executable, os.path.join(HERE, "secret.py")] + args
    else:
        cmd = ["ssh"] + (["-t"] if tty else []) + [M8_HOST, "python3 " + M8_SECRET + " "
                                                    + " ".join(shlex.quote(a) for a in args)]
    if tty:
        r = subprocess.run(cmd)
        out = ""
    else:
        r = subprocess.run(cmd, capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
    if check and r.returncode != 0:
        raise Stop(f"secret.py {args[0]} failed on the M8: {out or 'exit ' + str(r.returncode)}")
    return r.returncode, out


def clip(name):
    """Put a vault value on the Windows clipboard via secret.ps1 -- the value goes
    M8 -> clipboard and never through this process's output. No auto-clear (removed
    2026-10-02, Joseph: he copies it onward into RoboForm anyway, which doesn't
    expire) -- it sits on the clipboard until something else overwrites it."""
    if os.environ.get("JCTSH_CLIP") == "none" or os.name != "nt":
        say(f"    (get the value with: secret.ps1 copy {name})")
        return
    ps1 = os.path.join(HERE, "secret.ps1")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1,
                        "copy", name], capture_output=True, text=True)
    if r.returncode == 0:
        say(f"    value of {name} is on the clipboard")
    else:
        say(f"    could not put {name} on the clipboard -- run: secret.ps1 copy {name}")


_answers = [a.strip() for a in os.environ["JCTSH_ANSWERS"].split(",")] if os.environ.get("JCTSH_ANSWERS") else None


def ask(prompt, choices):
    """One-letter answer from `choices`; stops the run (resumable) without a terminal."""
    if _answers is not None:
        if not _answers:
            raise Stop("waiting on a person (no scripted answers left) -- resume with: rotate.py continue", WAITING)
        a = _answers.pop(0)
        say(f"{prompt} [{'/'.join(choices)}] {a}")
        return a
    if not sys.stdin.isatty():
        raise Stop("waiting on a person -- run rotate.py continue <target> from a terminal", WAITING)
    while True:
        try:
            a = input(f"{prompt} [{'/'.join(choices)}] ").strip().lower()[:1]
        except EOFError:
            # isatty() can misreport in some non-interactive environments (confirmed
            # live 2026-10-02: Claude Code's Bash tool on this Windows/git-bash setup) --
            # input() then hits EOF instead of ever getting a real answer. Treat that
            # exactly like "no real terminal" rather than crashing: stop cleanly,
            # resumable the normal way.
            raise Stop("waiting on a person -- run rotate.py continue <target> from a terminal", WAITING)
        if a in choices:
            return a


def say(msg=""):
    print(msg, flush=True)


# --- state + lock ---------------------------------------------------------------------

def now_utc():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def today():
    return os.environ.get("JCTSH_TODAY") or dt.date.today().isoformat()


def state_path(target):
    return os.path.join(STATE_DIR, f"{target}.json")


def load_state(target, required=True):
    p = state_path(target)
    if not os.path.exists(p):
        if required:
            raise Stop(f"no rotation in progress for '{target}' (rotate.py status lists them)")
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_state(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    st["updated"] = now_utc().isoformat()
    tmp = state_path(st["target"]) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2)
    os.replace(tmp, state_path(st["target"]))


class RunLock:
    """One rotate.py at a time across both Windows profiles (same checkout)."""

    def __init__(self, command, break_lock=False):
        self.path = os.path.join(STATE_DIR, "rotate.lock")
        self.command, self.break_lock = command, break_lock

    def __enter__(self):
        os.makedirs(STATE_DIR, exist_ok=True)
        info = {"pid": os.getpid(), "host": socket.gethostname(), "user": os.environ.get("USERNAME") or os.environ.get("USER"),
                "command": self.command, "started": now_utc().isoformat()}
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if not self.break_lock:
                try:
                    with open(self.path, encoding="utf-8") as f:
                        held = f.read().strip()
                except OSError:
                    held = "?"
                raise Stop(f"another rotate.py run holds the lock: {held}\n"
                           f"If that run is dead, re-run with --break-lock.")
            os.remove(self.path)
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(info, f)
        return self

    def __exit__(self, *exc):
        try:
            os.remove(self.path)
        except OSError:
            pass


# --- holder actions -------------------------------------------------------------------

def describe_apply(a):
    where = f"{a['host']}:" if a.get("host") else "M8:"
    parts = [f"envfile {where}{a['envfile']} {a['var']}=<new>"]
    if a.get("previous_var"):
        parts.append(f"{a['previous_var']}=<old> until {a.get('expires_var') or '?'}")
    if a.get("restart"):
        parts.append(f"restart: {a['restart']}")
    return "; ".join(parts)


def envfile_args(a):
    args = ["envfile", "--file", a["envfile"]]
    if a.get("host"):
        args += ["--host", a["host"]]
    if a.get("sudo"):
        args.append("--sudo")
    return args


def run_check(name, holder, env_new, env_old=None):
    """A holder's check_cmd, on the M8, with the value(s) in its environment only."""
    binds = ["--env", f"NEW={env_new}"] + (["--env", f"OLD={env_old}"] if env_old else [])
    rc, out = secret(["run", name] + binds + ["--", "sh", "-c", holder["check_cmd"]], check=False)
    tail = " | ".join(out.splitlines()[-3:])
    return rc == 0, tail


def has_entries(names, *wanted):
    return [w for w in wanted if w in names]


def vault_names():
    _, out = secret(["ls"])
    return set(out.splitlines())


# --- commands ---------------------------------------------------------------------------

def cmd_plan(args):
    entries, _ = load_registry()
    e, acct = resolve(entries, args.target)
    f = e["fields"]
    a = e["accounts"].get(acct, {}) if acct else {}
    hs = holders_for(e, acct)
    say(f"=== ROTATION PLAN: {args.target} (offline -- nothing executed, no value touched) ===")
    say(f"What:          {f.get('what')}")
    say(f"Tier:          {f.get('tier')}")
    say(f"Last rotated:  {a.get('last_rotated') or f.get('last_rotated')}")
    exp = (f.get("exposed") or []) + (a.get("exposed") or [])
    say(f"Exposed:       {', '.join(map(str, exp)) if exp else 'no'}")
    rr = a.get("rotation_requested") or f.get("rotation_requested")
    if rr:
        say(f"Requested:     {rr}")
    say(f"Vault entry:   {args.target}  (RoboForm entry: the same name)")
    st = load_state(args.target, required=False)
    if st:
        say(f"IN PROGRESS:   phase {st['phase']} since {st['started']} -- rotate.py status {args.target}")
    say("")
    say(f"Holders ({len(hs)}), in order:")
    for i, h in enumerate(hs, 1):
        mode = "auto" if h["apply"] else "guided"
        say(f"  {i}. [{mode}] {h['label']}" + (f"  ({h['var']})" if h["var"] else ""))
        if h["apply"]:
            say(f"       does:   {describe_apply(h['apply'])}")
        if h["check_cmd"]:
            say(f"       check:  {h['check_cmd']}")
        elif h["verify"]:
            say(f"       verify: {h['verify']} (you confirm)")
    dual = [h for h in hs if h["apply"] and h["apply"].get("previous_var")]
    say("")
    if dual:
        say(f"Dual-accept: yes -- the old value stays valid until the window closes ({DEFAULT_WINDOW_DAYS}d default), "
            f"so guided holders can move later without an outage.")
    else:
        say("Dual-accept: no -- each holder switches when it's updated; do the guided ones promptly.")
    say(f"Start with:  rotate.py start {args.target}" + ("  --prompt (value minted by the service)" if f.get("class") == "token" else ""))
    if args.preview:
        os.makedirs(STATE_DIR, exist_ok=True)
        preview = {
            "target": args.target, "planned_at": now_utc().isoformat(),
            "holders": [{"key": h["key"], "label": h["label"], "mode": "auto" if h["apply"] else "guided",
                         "desc": describe_apply(h["apply"]) if h["apply"] else (h["verify"] or "")}
                        for h in hs],
        }
        with open(os.path.join(STATE_DIR, "planned.json"), "w", encoding="utf-8") as pf:
            json.dump(preview, pf, indent=2)


def cmd_start(args):
    entries, _ = load_registry()
    e, acct = resolve(entries, args.target)
    name = args.target
    with RunLock(f"start {name}", args.break_lock):
        if load_state(name, required=False):
            raise Stop(f"a rotation of '{name}' is already in progress -- rotate.py continue {name}")
        hs = holders_for(e, acct)
        say(f"=== START {name} ===")
        secret(["init"])
        names = vault_names()
        present = has_entries(names, name, name + ".next", name + ".previous")
        if name + ".previous" in present:
            raise Stop(f"'{name}.previous' is still in the vault from an earlier rotation -- finish that first "
                       f"(or, if it's truly done, secret.py drop-previous {name}).")
        if name + ".next" in present and not args.restage:
            raise Stop(f"'{name}.next' is already staged but no rotation state exists (an interrupted start?). "
                       f"Re-run with --restage to replace it.")
        has_current = name in present
        if not has_current and not args.no_current:
            raise Stop(f"the vault has no current value for '{name}', so nothing could be rolled back and a "
                       f"dual-accept server couldn't keep the old value. Store it first: secret.ps1 set {name}\n"
                       f"(or pass --no-current if the old value is lost and being replaced outright).")
        if not has_current:
            dual = [h["label"] for h in hs if h["apply"] and h["apply"].get("previous_var")]
            if dual:
                say(f"  note: no current value -- dual-accept holders get the new value only: {', '.join(dual)}")
        for host in sorted({h["apply"]["host"] for h in hs if h["apply"] and h["apply"].get("host")}):
            rc, out = secret(["reach", host], check=False)
            if rc != 0:
                raise Stop(f"preflight: the M8 can't reach {host} non-interactively -- {out}\n"
                           f"Set up a key from the M8 to {host} first, or handle that holder by hand.")
            say(f"  preflight: M8 -> {host} ok")
        stage = ["stage", name] + (["--replace"] if args.restage else [])
        if args.prompt:
            stage.append("--prompt")
            secret(stage, tty=True)
            _, out = secret(["fingerprint", name + ".next"])
            out = "staged " + name + ".next (" + out[:19] + ")"
        else:
            _, out = secret(stage)
        say(f"  {out}")
        expires = now_utc() + dt.timedelta(days=args.window_days)
        st = {
            "target": name, "phase": "applying", "started": now_utc().isoformat(),
            "expires": expires.isoformat().replace("+00:00", "Z"), "window_days": args.window_days,
            "has_current": has_current, "roboform_synced": False,
            "holders": [{"key": h["key"], "label": h["label"], "status": "pending"} for h in hs],
        }
        save_state(st)
        say(f"  window closes {st['expires']} (old value stops working there at the latest)")
        preview_path = os.path.join(STATE_DIR, "planned.json")
        if os.path.exists(preview_path):
            try:
                with open(preview_path, encoding="utf-8") as pf:
                    if json.load(pf).get("target") == name:
                        os.remove(preview_path)
            except Exception:
                pass
        _continue(st, e, acct)


def cmd_continue(args):
    entries, _ = load_registry()
    e, acct = resolve(entries, args.target)
    with RunLock(f"continue {args.target}", args.break_lock):
        st = load_state(args.target)
        if st["phase"] != "applying":
            say(f"'{args.target}' is past the holder steps (phase {st['phase']}). Next: "
                + ("rotate.py confirm-synced / finish" if st["phase"] == "cutover" else "nothing"))
            return
        _continue(st, e, acct)


def _continue(st, e, acct):
    name = st["target"]
    hs = {h["key"]: h for h in holders_for(e, acct)}
    for hstate in st["holders"]:
        if hstate["status"] in ("done", "not-applicable"):
            continue
        h = hs.get(hstate["key"])
        if h is None:
            raise Stop(f"holder '{hstate['label']}' is in the rotation state but no longer in the registry -- "
                       f"put it back, or abort the rotation.")
        say("")
        say(f"--- holder: {h['label']}" + (f" ({h['var']})" if h["var"] else ""))
        if h["note"]:
            say(f"    note: {h['note']}")
        if h["apply"] and hstate["status"] not in ("applied", "failed-check"):
            a = h["apply"]
            args = envfile_args(a) + ["--set", f"{a['var']}={name}.next"]
            if a.get("previous_var") and st["has_current"]:
                args += ["--set", f"{a['previous_var']}={name}"]
                if a.get("expires_var"):
                    args += ["--set-text", f"{a['expires_var']}={st['expires']}"]
            if a.get("restart"):
                args += ["--restart", a["restart"]]
            rc, out = secret(args, check=False)
            for line in out.splitlines():
                say(f"    {line}")
            if rc != 0:
                hstate["status"] = "failed"
                save_state(st)
                raise Stop(f"applying to {h['label']} failed. The old value is still current everywhere else.\n"
                           f"Fix the cause and run rotate.py continue {name}, or rotate.py abort {name}.")
            hstate["status"] = "applied"
            save_state(st)
        if h["apply"] and h["check_cmd"]:
            ok, tail = run_check(name, h, f"{name}.next", name if st["has_current"] else None)
            say(f"    check {'passed' if ok else 'FAILED'}" + (f": {tail}" if tail else ""))
            if not ok:
                hstate["status"] = "failed-check"
                save_state(st)
                raise Stop(f"{h['label']} took the new value but its check failed. "
                           f"Investigate, then rotate.py continue {name} (re-checks) or rotate.py abort {name}.")
            hstate["status"] = "done"
        else:
            if not h["apply"]:
                say(f"    guided: put the new value into this holder" + (f" as {h['var']}" if h["var"] else ""))
                clip(f"{name}.next")
            if h["verify"]:
                say(f"    verify: {h['verify']}")
            a = ask("    done and verified (d), doesn't hold this value (n), later (l), abort (a)?", ["d", "n", "l", "a"])
            if a == "l":
                hstate["status"] = "later"
                save_state(st)
                raise Stop(f"stopped at {h['label']} -- resume with rotate.py continue {name}", WAITING)
            if a == "a":
                save_state(st)
                raise Stop(f"stopped -- to undo what's done so far: rotate.py abort {name}", WAITING)
            hstate["status"] = "done" if a == "d" else "not-applicable"
            hstate["at"] = now_utc().isoformat()
        save_state(st)

    say("")
    say("--- cutover: every holder has the new value")
    _, out = secret(["promote", name])
    say(f"    {out}")
    st["phase"] = "cutover"
    st["cutover"] = now_utc().isoformat()
    save_state(st)
    registry_set(name, "roboform_synced", "false")
    say("    registry: roboform_synced: false")
    say("")
    say(f"--- RoboForm: paste the new value into the RoboForm entry '{name}'")
    clip(name)
    say(f"    then: rotate.py confirm-synced {name}")
    say(f"    then: rotate.py finish {name}  (drops the old value; possible without the RoboForm "
        f"confirmation only after {st['expires']} or with --force)")


def cmd_confirm_synced(args):
    with RunLock(f"confirm-synced {args.target}", args.break_lock):
        st = load_state(args.target, required=False)
        if st is None:
            # Already finished (e.g. `finish --force` before the paste): only the registry flag is left.
            entries, _ = load_registry()
            e, acct = resolve(entries, args.target)
            cur = (e["accounts"][acct] if acct else e["fields"]).get("roboform_synced")
            if cur is not False:
                raise Stop(f"no rotation of '{args.target}' is waiting on RoboForm (roboform_synced: {cur}).")
            registry_set(args.target, "roboform_synced", "true")
            say(f"RoboForm confirmed for {args.target}; registry roboform_synced: true.")
            return
        if st["phase"] != "cutover":
            raise Stop(f"'{args.target}' is in phase {st['phase']} -- RoboForm gets the value after cutover.")
        st["roboform_synced"] = True
        st["roboform_confirmed"] = now_utc().isoformat()
        save_state(st)
        registry_set(args.target, "roboform_synced", "true")
        say(f"RoboForm confirmed for {args.target}; registry roboform_synced: true. Next: rotate.py finish {args.target}")


def cmd_finish(args):
    entries, _ = load_registry()
    e, acct = resolve(entries, args.target)
    name = args.target
    with RunLock(f"finish {name}", args.break_lock):
        st = load_state(name)
        if st["phase"] != "cutover":
            raise Stop(f"'{name}' is in phase {st['phase']} -- finish comes after cutover (rotate.py continue {name}).")
        expires = dt.datetime.fromisoformat(st["expires"].replace("Z", "+00:00"))
        if not st["roboform_synced"] and now_utc() < expires and not args.force:
            raise Stop(f"RoboForm isn't confirmed yet. Paste the value (secret.ps1 copy {name}), run "
                       f"rotate.py confirm-synced {name}, then finish. Revoking now could leave no usable "
                       f"human copy; the old value stays valid until {st['expires']} at the latest. "
                       f"(--force to revoke anyway.)")
        say(f"=== FINISH {name} ===")
        for h in holders_for(e, acct):
            a = h["apply"]
            if not (a and a.get("previous_var")) or not st["has_current"]:
                continue
            args_ = envfile_args(a) + ["--unset", a["previous_var"]]
            if a.get("expires_var"):
                args_ += ["--unset", a["expires_var"]]
            if a.get("restart"):
                args_ += ["--restart", a["restart"]]
            rc, out = secret(args_, check=False)
            for line in out.splitlines():
                say(f"    {line}")
            if rc != 0:
                raise Stop(f"removing the old value from {h['label']} failed -- fix and re-run finish. "
                           f"(It also stops being accepted at {st['expires']} on its own.)")
            if h["check_cmd"]:
                ok, tail = run_check(name, h, name)
                say(f"    check {'passed' if ok else 'FAILED'}" + (f": {tail}" if tail else ""))
                if not ok:
                    raise Stop(f"{h['label']} fails its check after dropping the old value -- investigate before "
                               f"re-running finish.")
        revoke = e["fields"].get("revoke")
        if revoke:
            say(f"--- revoke step for this credential: {revoke}")
            if ask("    done (d) or stop here (l)?", ["d", "l"]) != "d":
                raise Stop(f"stopped before the revoke step -- re-run rotate.py finish {name}", WAITING)
        _, out = secret(["drop-previous", name])
        say(f"    {out}")
        registry_set(name, "last_rotated", today(), comment="rotate.py (CARD-0372)")
        if (e["accounts"].get(acct, {}) if acct else e["fields"]).get("rotation_requested"):
            registry_set(name, "rotation_requested", "null")
        st["phase"] = "done"
        st["finished"] = now_utc().isoformat()
        done_dir = os.path.join(STATE_DIR, "done")
        os.makedirs(done_dir, exist_ok=True)
        with open(os.path.join(done_dir, f"{name}-{st['finished'][:10]}.json"), "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2)
        os.remove(state_path(name))
        say(f"    registry: last_rotated: {today()}" + (" (roboform_synced stays false -- paste it!)" if not st["roboform_synced"] else ""))
        say(f"Done. Commit tos/credential-registry.yaml; secret.ps1 due should no longer list {name}.")


def cmd_abort(args):
    entries, _ = load_registry()
    e, acct = resolve(entries, args.target)
    name = args.target
    with RunLock(f"abort {name}", args.break_lock):
        st = load_state(name)
        if st["phase"] != "applying":
            raise Stop(f"'{name}' is past cutover -- going back isn't automatic. If the new value is broken: "
                       f"secret.py unpromote {name}, then put the old value back into each holder.")
        hs = {h["key"]: h for h in holders_for(e, acct)}
        say(f"=== ABORT {name} ===")
        for hstate in reversed(st["holders"]):
            if hstate["status"] in ("pending", "not-applicable"):
                continue
            h = hs.get(hstate["key"])
            label = hstate["label"]
            if h and h["apply"]:
                if not st["has_current"]:
                    say(f"    {label}: has the new value; there's no old value to put back (--no-current)")
                    continue
                a = h["apply"]
                args_ = envfile_args(a) + ["--set", f"{a['var']}={name}"]
                if a.get("previous_var"):
                    args_ += ["--unset", a["previous_var"]] + (["--unset", a["expires_var"]] if a.get("expires_var") else [])
                if a.get("restart"):
                    args_ += ["--restart", a["restart"]]
                rc, out = secret(args_, check=False)
                for line in out.splitlines():
                    say(f"    {line}")
                if rc != 0:
                    raise Stop(f"restoring {label} failed -- fix and re-run abort (nothing else was undone yet).")
                hstate["status"] = "pending"
                save_state(st)
            elif hstate["status"] in ("done", "later"):
                say(f"--- {label}: put the OLD value back by hand")
                if st["has_current"]:
                    clip(name)
                if ask("    restored (d), or stop here (l)?", ["d", "l"]) != "d":
                    raise Stop(f"stopped -- re-run rotate.py abort {name} to continue undoing", WAITING)
                hstate["status"] = "pending"
                save_state(st)
        _, out = secret(["discard-next", name])
        say(f"    {out}")
        os.remove(state_path(name))
        say(f"Aborted: {name} is back on its old value; nothing was recorded in the registry.")


def cmd_verify(args):
    entries, _ = load_registry()
    e, acct = resolve(entries, args.target)
    name = args.target
    say(f"=== VERIFY {name} (current value, nothing changes) ===")
    bad = 0
    for h in holders_for(e, acct):
        if h["check_cmd"]:
            ok, tail = run_check(name, h, name)
            bad += not ok
            say(f"  [{'PASS' if ok else 'FAIL'}] {h['label']}: {tail}")
        else:
            say(f"  [manual] {h['label']}: {h['verify'] or 'no check recorded'}")
    sys.exit(1 if bad else 0)


def cmd_status(args):
    if not os.path.isdir(STATE_DIR):
        say("no rotations in progress")
        return
    files = sorted(f for f in os.listdir(STATE_DIR) if f.endswith(".json"))
    if args.target:
        files = [f for f in files if f == f"{args.target}.json"]
    if not files:
        say("no rotations in progress")
        return
    for fn in files:
        with open(os.path.join(STATE_DIR, fn), encoding="utf-8") as f:
            st = json.load(f)
        done = sum(h["status"] in ("done", "not-applicable") for h in st["holders"])
        say(f"{st['target']}: phase {st['phase']}, holders {done}/{len(st['holders'])}, "
            f"RoboForm {'confirmed' if st['roboform_synced'] else 'not confirmed'}, window closes {st['expires']}")
        for h in st["holders"]:
            if h["status"] not in ("done", "not-applicable"):
                say(f"    {h['status']:<12} {h['label']}")
        nxt = {"applying": "continue", "cutover": "confirm-synced" if not st["roboform_synced"] else "finish"}[st["phase"]]
        say(f"    next: rotate.py {nxt} {st['target']}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for c in ("plan", "verify", "continue", "confirm-synced", "finish", "abort", "start"):
        sp = sub.add_parser(c)
        sp.add_argument("target")
        sp.add_argument("--break-lock", action="store_true")
    sub.choices["plan"].add_argument("--preview", action="store_true",
                                      help="write a values-free preview to .rotation-state/planned.json for the dashboard")
    sub.choices["start"].add_argument("--prompt", action="store_true", help="type a value the service minted")
    sub.choices["start"].add_argument("--window-days", type=int, default=DEFAULT_WINDOW_DAYS)
    sub.choices["start"].add_argument("--no-current", action="store_true")
    sub.choices["start"].add_argument("--restage", action="store_true")
    sub.choices["finish"].add_argument("--force", action="store_true")
    sp = sub.add_parser("status")
    sp.add_argument("target", nargs="?")
    args = p.parse_args()
    fn = {"plan": cmd_plan, "verify": cmd_verify, "start": cmd_start, "continue": cmd_continue,
          "status": cmd_status, "confirm-synced": cmd_confirm_synced, "finish": cmd_finish,
          "abort": cmd_abort}[args.cmd]
    try:
        fn(args)
    except Stop as s:
        print(str(s), file=sys.stderr)
        sys.exit(s.code)


if __name__ == "__main__":
    main()
