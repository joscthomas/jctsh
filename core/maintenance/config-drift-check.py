#!/usr/bin/env python3
"""CARD-0328: drift check for version-controlled copies of live Pi config.

`core/mqtt/`, `core/node-red/` and `core/homeassistant/` are each a
version-controlled copy of files that actually run from somewhere else on the
Pi, and root CLAUDE.md's rule ("the repo is the source of truth... do not edit
on the Pi directly or the repo will fall out of sync") had nothing checking it.
This compares each live file against the same file on GitHub `main` (fetched
with the token every other maintenance check here already uses -- no
checkout needed on the Pi) and, on drift, posts an Alert and opens a kanban PR
via open_kanban_pr.py.

Detect-and-report only, same notify-only policy as every other check in this
directory: never writes to the repo or to the live file, and never decides
which side is right (a live hotfix may be the correct one) -- that's the PR
reviewer's call.

Three details worth knowing:
- Node-RED doesn't map file-to-file. The repo keeps one *.flow.json per flow;
  the live instance keeps everything merged in one flows.json. Flow files are
  compared node-by-node by id, ignoring cosmetic editor positions, and live
  tabs/nodes with no counterpart in *any* repo flow file are reported too (a
  flow built live and never brought back is the exact failure being guarded).
- Secrets never reach a PR body. Diffs are rendered from a masked copy of both
  sides (bcrypt hashes, credentialSecret/password/token-style values). If the
  files differ *only* in a masked value that's still reported, just with the
  content withheld.
- A closed-but-unfixed PR must not re-open daily: same fingerprint is
  re-notified at most every REMIND_EVERY, same throttle as the other checks.

Runs as root on the Pi (no User= in its .service), matching
pi-maintenance-check.py's conventions: mosquitto_pub, jctsh-core component,
log-server.env / github.env credentials. `--dry-run` prints findings and does
nothing else (no log line, no PR, no state write).
"""
import difflib, hashlib, json, os, re, subprocess, sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from open_kanban_pr import open_finding_pr, _get_file_text, _api, REPO, BRANCH_BASE  # CARD-0128

BROKER     = "127.0.0.1"
PORT       = 1883
COMPONENT  = "jctsh-core"
LOG_TOPIC  = "jctsh/core/log-server/log"
STATE_FILE = "/root/.jctsh/config-drift-check.state"
GITHUB_ENV = "/etc/jctsh/github.env"
REMIND_EVERY = timedelta(days=7)

MAX_DIFF_LINES_PER_FILE = 30   # keeps the PR body readable; the full diff is one manual command away
MAX_MESSAGE_CHARS       = 6000

NODERED_FLOWS = "/home/pi/.node-red/flows.json"
HA_DIR        = "/mnt/jctsh-logs/homeassistant"

# (repo path, live path or candidates in preference order, mode). A live path
# given as a tuple is tried in order; none existing is itself a finding rather
# than a crash, so a wrong guess here surfaces on the first run instead of
# silently skipping the file.
MANIFEST = [
    # -- core/mqtt (maps 1:1 onto /etc/mosquitto/) --
    ("core/mqtt/mosquitto.conf", "/etc/mosquitto/mosquitto.conf", "file"),
    ("core/mqtt/jctsh.conf", "/etc/mosquitto/conf.d/jctsh.conf", "file"),
    ("core/mqtt/local.conf", "/etc/mosquitto/conf.d/local.conf", "file"),
    ("core/mqtt/mqtt-tls.conf", "/etc/mosquitto/conf.d/mqtt-tls.conf", "file"),
    # Installed under a different name than the repo's (verified live 2026-09-23).
    ("core/mqtt/mosquitto-cert-deploy-hook.sh",
     ("/etc/letsencrypt/renewal-hooks/deploy/mosquitto-reload.sh",
      "/etc/letsencrypt/renewal-hooks/deploy/mosquitto-cert-deploy-hook.sh"), "file"),
    # -- core/node-red --
    ("core/node-red/settings.js", "/home/pi/.node-red/settings.js", "file"),
    ("core/node-red/core.flow.json", NODERED_FLOWS, "flows"),
    ("core/node-red/watchdog.flow.json", NODERED_FLOWS, "flows"),
    # -- core/homeassistant --
    ("core/homeassistant/automations.yaml", f"{HA_DIR}/automations.yaml", "file"),
    ("core/homeassistant/configuration.yaml", f"{HA_DIR}/configuration.yaml", "file"),
    # Not under HA_DIR: the running container's own compose label points at /home/pi (verified live 2026-09-23).
    ("core/homeassistant/docker-compose.yml", "/home/pi/docker-compose.yml", "file"),
    ("core/homeassistant/container-update-check.py", "/usr/local/bin/container-update-check.py", "file"),
    ("core/homeassistant/pi-heartbeat.py", "/usr/local/bin/pi-heartbeat.py", "file"),
]

# Live directories where a file that exists on the Pi but not in the repo is itself drift
# (a config dropped in and never brought back -- the same failure, from the other side).
# (live dir, glob, repo dir the files should be tracked in)
LIVE_ONLY_DIRS = [
    ("/etc/mosquitto/conf.d", "*.conf", "core/mqtt"),
]

# Editor layout only -- dragging a node in the Node-RED editor changes these
# and nothing else, and reporting that as drift would be pure noise.
FLOW_IGNORE_KEYS = {"x", "y", "w", "h"}

_BCRYPT_RE = re.compile(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}")
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")   # HA long-lived tokens etc.

# Node-RED's own auto-created settings node. Its `env` list holds real secrets in
# plaintext (HA_TOKEN, verified live 2026-09-23), so it is never compared or shown.
FLOW_IGNORE_TYPES = {"global-config"}
# Properties Node-RED adds with a default value when it loads a node (e.g. `inputs: 0`
# on an mqtt in node). Present-only-live with one of these values is not drift.
_FLOW_DEFAULT_VALUES = (0, "", False, None, [], {})
_SECRET_LINE_RE = re.compile(
    r"(?im)^(?P<head>[^\n]*?(?:credentialSecret|password|passwd|secret|token|api[_-]?key)"
    r"[^\n:=]*[:=]\s*).*$"
)


def _norm(text):
    return text.replace("\r\n", "\n")


def mask_secrets(text):
    """Both sides get masked before diffing for display. Never for the drift
    decision itself -- see compare_file()."""
    text = _BCRYPT_RE.sub("<bcrypt-hash>", text)
    text = _JWT_RE.sub("<token>", text)
    return _SECRET_LINE_RE.sub(lambda m: m.group("head") + "<redacted>", text)


def _clip(lines, n):
    if len(lines) <= n:
        return lines
    return lines[:n] + [f"... ({len(lines) - n} more diff line(s) not shown)"]


def compare_file(repo_text, live_text):
    """Returns None if identical, else a list of display lines. Drift is
    decided on the raw (newline-normalized) text, but the displayed diff comes
    from the masked copies -- so a change confined to a secret value is still
    caught, just shown as withheld rather than leaked."""
    repo_text, live_text = _norm(repo_text), _norm(live_text)
    if repo_text == live_text:
        return None
    diff = [
        l for l in difflib.unified_diff(
            mask_secrets(repo_text).splitlines(), mask_secrets(live_text).splitlines(),
            fromfile="repo (main)", tofile="live (Pi)", lineterm="", n=1,
        )
    ]
    if not diff:
        return ["differs only in a secret-bearing value (content withheld)"]
    return diff


def _node_summary(node):
    return f"{node.get('type', '?')} '{node.get('label') or node.get('name') or node.get('id')}'"


def _short(v):
    s = mask_secrets(json.dumps(v, sort_keys=True))
    return s if len(s) <= 100 else s[:97] + "..."


def compare_flows(repo_nodes, live_nodes):
    """Compare one repo flow file's nodes against the merged live flows.json.
    Returns a list of display lines ([] if no drift). Matching is by node id,
    and credentials never appear in flows.json (Node-RED keeps them in the
    separate flows_cred.json), so nothing secret can surface here."""
    live_by_id = {n["id"]: n for n in live_nodes if "id" in n}
    lines = []
    for n in repo_nodes:
        live = live_by_id.get(n["id"])
        if live is None:
            lines.append(f"missing on Pi: {_node_summary(n)} ({n['id']})")
            continue
        if n.get("type") in FLOW_IGNORE_TYPES:
            continue
        a = {k: v for k, v in n.items() if k not in FLOW_IGNORE_KEYS}
        b = {k: v for k, v in live.items() if k not in FLOW_IGNORE_KEYS
             and not (k not in a and v in _FLOW_DEFAULT_VALUES)}
        if a == b:
            continue
        keys = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        lines.append(f"changed on Pi: {_node_summary(n)} ({n['id']}) -- keys: {', '.join(keys)}")
        for k in keys[:4]:
            lines.append(f"    {k}: repo={_short(a.get(k))}  live={_short(b.get(k))}")
    return lines


def find_orphan_flows(live_nodes, all_repo_ids, repo_tab_labels=frozenset()):
    """Live tabs (and their nodes) that exist in *no* repo flow file. Reported
    once per tab rather than per node. Config nodes with no tab (no `z`) that
    the repo doesn't know are reported individually."""
    def known_tab(tab):
        if tab["id"] in all_repo_ids or (tab.get("label") or "").strip() in repo_tab_labels:
            return True
        return any(n.get("z") == tab["id"] and n.get("id") in all_repo_ids for n in live_nodes)

    orphan_tabs = {n["id"]: n for n in live_nodes if n.get("type") == "tab" and not known_tab(n)}
    lines = []
    for tab_id, tab in orphan_tabs.items():
        count = sum(1 for n in live_nodes if n.get("z") == tab_id)
        lines.append(f"live-only flow tab (not in any repo flow file): '{tab.get('label') or tab_id}' "
                     f"({tab_id}, {count} node(s))")
    for n in live_nodes:
        if n.get("type") == "tab" or n.get("type") in FLOW_IGNORE_TYPES or n.get("id") in all_repo_ids:
            continue
        if n.get("z") in orphan_tabs:
            continue
        if n.get("z") is None:
            lines.append(f"live-only config node (not in any repo flow file): {_node_summary(n)} ({n.get('id')})")
    return lines


def _read_live(spec):
    """(path_used, text) for the first existing candidate, else (None, None)."""
    candidates = (spec,) if isinstance(spec, str) else spec
    for p in candidates:
        try:
            with open(p, encoding="utf-8") as f:
                return p, f.read()
        except FileNotFoundError:
            continue
    return None, None


def _list_live_dir(path, pattern):
    import fnmatch
    try:
        return [n for n in os.listdir(path) if fnmatch.fnmatch(n, pattern)]
    except FileNotFoundError:
        return []


def collect_findings(fetch_repo_text, list_repo_flow_files, read_live=_read_live, list_live_dir=_list_live_dir):
    """Pure orchestration, with the I/O edges injected so it can be tested
    without GitHub or a Pi. Returns a list of {"scope", "file", "lines"}."""
    findings = []
    flow_cache = {}   # live path -> parsed nodes (the merged flows.json is read once)

    for repo_path, live_spec, mode in MANIFEST:
        scope = repo_path.split("/")[1]
        used, live_text = read_live(live_spec)
        if used is None:
            looked = live_spec if isinstance(live_spec, str) else ", ".join(live_spec)
            findings.append({"scope": scope, "file": repo_path,
                             "lines": [f"live file not found (looked in: {looked})"]})
            continue
        try:
            repo_text = fetch_repo_text(repo_path)
        except Exception as e:
            findings.append({"scope": scope, "file": repo_path,
                             "lines": [f"could not fetch repo copy from {BRANCH_BASE}: {e}"]})
            continue

        if mode == "file":
            lines = compare_file(repo_text, live_text)
        else:
            if used not in flow_cache:
                flow_cache[used] = json.loads(live_text)
            lines = compare_flows(json.loads(repo_text), flow_cache[used]) or None
        if lines:
            findings.append({"scope": scope, "file": repo_path, "lines": lines})

    for live_dir, pattern, repo_dir in LIVE_ONLY_DIRS:
        tracked = {os.path.basename(live) for _, spec, _ in MANIFEST
                   for live in ((spec,) if isinstance(spec, str) else spec)
                   if os.path.dirname(live) == live_dir}
        for name in sorted(list_live_dir(live_dir, pattern)):
            if name not in tracked:
                findings.append({"scope": repo_dir.split("/")[1], "file": f"{live_dir}/{name} (live only)",
                                 "lines": [f"exists on the Pi but is not tracked in {repo_dir}/"]})

    # Live-only flows need *every* repo flow file as the reference set, not just
    # the two under core/node-red, or another component's flow would look orphaned.
    if NODERED_FLOWS in flow_cache:
        all_ids, tab_labels = set(), set()
        for path in list_repo_flow_files():
            try:
                nodes = json.loads(fetch_repo_text(path))
                all_ids.update(n["id"] for n in nodes if "id" in n)
                tab_labels.update((n.get("label") or "").strip() for n in nodes if n.get("type") == "tab")
            except Exception as e:
                findings.append({"scope": "node-red", "file": path,
                                 "lines": [f"could not read repo flow file for the orphan check: {e}"]})
                return findings   # an incomplete reference set would make orphans meaningless
        orphans = find_orphan_flows(flow_cache[NODERED_FLOWS], all_ids, tab_labels)
        if orphans:
            findings.append({"scope": "node-red", "file": "live flows.json (no repo counterpart)",
                             "lines": orphans})
    return findings


def render_message(findings):
    files = ", ".join(f["file"] for f in findings)
    out = [f"Config drift: {len(findings)} item(s) differ between the Pi and the repo's {BRANCH_BASE} -- {files}", ""]
    for f in findings:
        out.append(f"[{f['scope']}] {f['file']}")
        out.extend("  " + l for l in _clip(f["lines"], MAX_DIFF_LINES_PER_FILE))
        out.append("")
    out.append("Repo is the source of truth by rule, but a live hotfix may be the correct side -- "
               "decide per item whether to bring it back to the repo or redeploy from it.")
    msg = mask_secrets("\n".join(out)).replace("```", "'''")   # open_finding_pr puts this inside a code fence
    if len(msg) > MAX_MESSAGE_CHARS:
        msg = msg[:MAX_MESSAGE_CHARS - 40] + "\n... (message truncated)"
    return msg


def fingerprint_of(findings):
    return hashlib.sha256(json.dumps(findings, sort_keys=True).encode()).hexdigest()[:16]


def _load_env(path):
    out = {}
    with open(path) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                out[k] = v
    return out


def main(argv):
    dry_run = "--dry-run" in argv

    try:
        token = _load_env(GITHUB_ENV)["GITHUB_PAT"]
    except (FileNotFoundError, KeyError):
        print(f"{GITHUB_ENV} missing or has no GITHUB_PAT -- can't fetch the repo copies to compare against.")
        return 1

    def fetch_repo_text(path):
        return _get_file_text(path, BRANCH_BASE, token)

    def list_repo_flow_files():
        tree = _api("GET", f"/repos/{REPO}/git/trees/{BRANCH_BASE}?recursive=1", token)
        if tree.get("truncated"):
            raise RuntimeError("repo tree listing truncated -- orphan-flow check would use an incomplete reference set")
        return sorted(e["path"] for e in tree["tree"] if e["path"].endswith(".flow.json"))

    try:
        findings = collect_findings(fetch_repo_text, list_repo_flow_files)
    except Exception as e:
        # GitHub unreachable etc. is not drift -- fail loudly (systemd shows it), open nothing.
        print(f"Drift check could not complete: {e}")
        return 1

    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    if not findings:
        print("No drift.")
        if not dry_run and state:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "w") as f:
                json.dump({}, f)   # clean run resets the throttle so a later recurrence notifies at once
        return 0

    message = render_message(findings)
    if dry_run:
        print(message)
        return 0

    fingerprint = fingerprint_of(findings)
    now = datetime.now(timezone.utc)
    if state.get("fingerprint") == fingerprint:
        last = datetime.fromisoformat(state["notified_at"])
        if now - last < REMIND_EVERY:
            print(f"Same drift already notified -- next reminder in {(REMIND_EVERY - (now - last)).days}d.")
            return 0

    env = _load_env("/etc/jctsh/log-server.env")
    log_line = message.split("\n", 1)[0]
    payload = json.dumps({"component": COMPONENT, "category": "Alert", "message": log_line})
    try:
        subprocess.run(
            ["mosquitto_pub", "-h", BROKER, "-p", str(PORT),
             "-u", env["MQTT_USER"], "-P", env["MQTT_PASS"], "-t", LOG_TOPIC, "-m", payload],
            check=True, timeout=10,
        )
    except Exception as e:
        print(f"Failed to publish: {e}")
        return 1

    new_state = {"fingerprint": fingerprint, "notified_at": now.isoformat()}
    # Deliberately non-fatal, like every other check: the Alert above already
    # succeeded, and a broken PR step must never undo it.
    try:
        prior_pr_state = {k: state[k] for k in ("pr_fingerprint", "pr_number") if k in state}
        pr_state, pr_url = open_finding_pr(COMPONENT, message, fingerprint, token, prior_pr_state)
        new_state.update(pr_state)
        if pr_url:
            print(f"Opened kanban PR: {pr_url}")
    except Exception as e:
        print(f"CARD-0128 PR step failed (Alert above still succeeded): {e}")

    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(new_state, f)
    print(f"Notified: {log_line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))