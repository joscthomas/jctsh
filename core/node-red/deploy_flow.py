#!/usr/bin/env python3
"""Deploy one flow tab from a repo *.flow.json to the live Node-RED via its Admin API.

Why this exists (CARD-0324): flows were being pushed by hand-rolled one-off calls
(CARD-0331). The Admin API needs the admin login, which a Claude Code session
must not read out of credentials.local.md -- so this asks for it interactively,
in *your* terminal, and never writes it anywhere.

    python core/node-red/deploy_flow.py core/node-red/watchdog.flow.json tab_watchdog
    python core/node-red/deploy_flow.py core/node-red/watchdog.flow.json tab_watchdog --trigger inject_daily_check

Steps: authenticate -> fetch the live tab -> show which node ids would be
added/changed/removed -> ask to confirm -> PUT /flow/<tab> -> re-fetch and verify
every function node's code is what is now running. Only the named tab is
replaced; Node-RED restarts just that flow (its in-memory timers reset -- for the
watchdog that means each component's silence timer re-arms on its next heartbeat).

Stdlib only. Default host is the Pi's Tailscale IP; --host to override.
"""
import argparse, getpass, json, sys, urllib.error, urllib.parse, urllib.request

# Load-time defaults Node-RED adds to a node; not a difference worth reporting.
_DEFAULTS = (0, "", False, None, [], {})


def call(host, method, path, token=None, body=None, form=None):
    data, headers = None, {}
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"http://{host}:1880{path}", data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        try:
            return resp.status, (json.loads(raw) if raw else None)
        except ValueError:   # e.g. POST /inject answers with plain text, not JSON
            return resp.status, raw.decode(errors="replace")


def _differs(repo_node, live_node):
    a = {k: v for k, v in repo_node.items() if k not in ("x", "y")}
    b = {k: v for k, v in live_node.items()
         if k not in ("x", "y") and not (k not in repo_node and v in _DEFAULTS)}
    return a != b


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("flow_file")
    ap.add_argument("tab_id")
    ap.add_argument("--host", default="100.70.162.24")
    ap.add_argument("--user", default="admin")
    ap.add_argument("--trigger", metavar="INJECT_ID", help="fire this inject node once after deploying")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    a = ap.parse_args()

    with open(a.flow_file, encoding="utf-8") as f:
        repo = json.load(f)
    repo_nodes = [n for n in repo if n.get("z") == a.tab_id]
    tab_nodes = [n for n in repo if n.get("id") == a.tab_id and n.get("type") == "tab"]
    if not repo_nodes or not tab_nodes:
        sys.exit(f"{a.flow_file} has no tab '{a.tab_id}' with nodes in it.")

    pw = getpass.getpass(f"Node-RED password for {a.user}@{a.host}: ")
    try:
        _, tok = call(a.host, "POST", "/auth/token", form={
            "client_id": "node-red-admin", "grant_type": "password", "scope": "*",
            "username": a.user, "password": pw})
    except urllib.error.HTTPError as e:
        sys.exit(f"Login failed: HTTP {e.code}")
    token = tok["access_token"]
    del pw

    _, live = call(a.host, "GET", f"/flow/{a.tab_id}", token)
    live_by_id = {n["id"]: n for n in live.get("nodes", [])}
    repo_by_id = {n["id"]: n for n in repo_nodes}
    added = sorted(set(repo_by_id) - set(live_by_id))
    removed = sorted(set(live_by_id) - set(repo_by_id))
    changed = sorted(i for i in set(repo_by_id) & set(live_by_id) if _differs(repo_by_id[i], live_by_id[i]))
    print(f"\nTab '{live.get('label')}' on {a.host}:")
    print(f"  add    : {added or '-'}")
    print(f"  change : {changed or '-'}")
    print(f"  remove : {removed or '-'}")

    if not (added or changed or removed):
        print("Live already matches the repo -- nothing to deploy.")
    else:
        if not a.yes and input("\nDeploy this tab now? [y/N] ").strip().lower() != "y":
            sys.exit("Aborted, nothing changed.")
        body = dict(live)
        body["nodes"] = repo_nodes
        status, _ = call(a.host, "PUT", f"/flow/{a.tab_id}", token, body=body)
        print(f"PUT /flow/{a.tab_id} -> HTTP {status}")

        _, after = call(a.host, "GET", f"/flow/{a.tab_id}", token)
        after_by_id = {n["id"]: n for n in after.get("nodes", [])}
        bad = [i for i, n in repo_by_id.items()
               if n["type"] == "function" and after_by_id.get(i, {}).get("func") != n["func"]]
        missing = sorted(set(repo_by_id) - set(after_by_id))
        if bad or missing:
            sys.exit(f"VERIFY FAILED -- function code differs: {bad}, missing nodes: {missing}")
        print(f"Verified: all {len(repo_by_id)} nodes present, every function node's code matches the repo.")

    if a.trigger:
        status, _ = call(a.host, "POST", f"/inject/{a.trigger}", token)
        print(f"Triggered inject '{a.trigger}' -> HTTP {status}")


if __name__ == "__main__":
    main()
