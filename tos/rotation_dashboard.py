#!/usr/bin/env python3
"""rotation_dashboard.py -- CARD-0372: a live, local view of rotate.py's state.

Joseph, 2026-10-02: the CLI's output scrolls off and he can't keep track of what's
going on mid-rotation. This serves one page, localhost-only, that polls rotate.py's
own values-free state files (tos/.rotation-state/*.json) and secret.ps1's `due`
report every few seconds and redraws -- no action, no vault touch, nothing leaves
this machine. Stdlib only, same as rotate.py.

Run: python tos\\rotation_dashboard.py   (opens the browser; Ctrl+C to stop)
"""
import datetime as dt
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.environ.get("JCTSH_ROTATION_STATE", os.path.join(HERE, ".rotation-state"))
SECRET_PS1 = os.path.join(HERE, "secret.ps1")
PORT = int(os.environ.get("JCTSH_DASHBOARD_PORT", "8765"))
# A guided holder's "done/doesn't apply/later?" question is answered by Joseph in the
# Claude Code chat, not on this page -- rotate.py's process then sits waiting and the
# state file simply stops being touched. There's no direct "a process is blocked" signal
# available to a page reading files from disk, so staleness while still 'applying' is the
# proxy: if nothing's moved in a while, it's not running, it's waiting on a person.
STALE_SECONDS = 20

sys.path.insert(0, HERE)
import rotate as rz  # noqa: E402  -- reuse its registry parsing, never its network/vault calls


def plan_for(target):
    """The full plan for one target, keyed by holder key -- mode, what it does, how it's
    verified -- straight from rotate.py's own holders_for(), so the dashboard shows the
    real plan, not just whatever labels happen to be in the state file."""
    try:
        entries, _ = rz.load_registry()
        e, acct = rz.resolve(entries, target)
    except Exception:
        return {}
    out = {}
    for h in rz.holders_for(e, acct):
        if h["apply"]:
            desc = rz.describe_apply(h["apply"])
        elif h["verify"]:
            desc = f"verify: {h['verify']}"
        else:
            desc = h.get("note") or ""
        out[h["key"]] = {"mode": "auto" if h["apply"] else "guided", "desc": desc,
                          "check_cmd": h.get("check_cmd")}
    return out


def read_in_progress():
    out = []
    if not os.path.isdir(STATE_DIR):
        return out
    for fn in sorted(os.listdir(STATE_DIR)):
        p = os.path.join(STATE_DIR, fn)
        if not fn.endswith(".json") or fn == "planned.json" or not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                st = json.load(f)
        except Exception:
            continue
        holders = st.get("holders", [])
        plan = plan_for(st.get("target"))
        enriched = []
        for h in holders:
            info = plan.get(h.get("key"), {})
            enriched.append({**h, "mode": info.get("mode", "guided"), "desc": info.get("desc", "")})
        done = sum(h.get("status") in ("done", "not-applicable") for h in holders)
        phase = st.get("phase")
        next_cmd = {"applying": "continue",
                    "cutover": "confirm-synced" if not st.get("roboform_synced") else "finish"}.get(phase)
        needs_attention, why = False, None
        if phase == "cutover" and not st.get("roboform_synced"):
            needs_attention, why = True, "paste the new value into RoboForm, then confirm-synced"
        elif phase == "applying":
            try:
                updated = dt.datetime.fromisoformat(st.get("updated", ""))
                stale = (dt.datetime.now(updated.tzinfo) - updated).total_seconds() > STALE_SECONDS
            except Exception:
                stale = False
            if stale and done < len(holders):
                needs_attention, why = True, "a guided step is waiting on your answer in the Claude Code session"
        out.append({
            "target": st.get("target"), "phase": phase,
            "done": done, "total": len(holders), "holders": enriched,
            "roboform_synced": bool(st.get("roboform_synced")),
            "expires": st.get("expires"), "updated": st.get("updated"), "started": st.get("started"),
            "next": f"rotate.py {next_cmd} {st.get('target')}" if next_cmd else None,
            "needs_attention": needs_attention, "needs_attention_why": why,
        })
    return out


def parse_due(text):
    sections, current = {}, None
    for line in text.splitlines():
        m = re.match(r"^=== (.+?) ===$", line.strip())
        if m:
            current = m.group(1)
            sections[current] = []
            continue
        if current is None:
            continue
        s = line.strip()
        if not s or s == "none":
            continue
        name, _, detail = s.partition(" -- ")
        sections[current].append({"name": name, "detail": detail})
    return sections


def pick(sections, keyword):
    for title, rows in sections.items():
        if keyword in title:
            return rows
    return []


def read_due():
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", SECRET_PS1, "due"],
            capture_output=True, text=True, timeout=30,
        )
        return parse_due(r.stdout), None
    except Exception as e:
        return {}, str(e)


def all_targets_and_last_rotated():
    """Every live (non-retired) credential/account name the registry knows about, with
    its last_rotated -- used only to compute the 'good' bucket (everything not flagged
    by any other bucket), never to decide anything."""
    entries, _ = rz.load_registry()
    out = {}
    for eid, e in entries.items():
        if eid == "__crlf__":
            continue
        if e["fields"].get("retired"):
            continue
        if e["accounts"]:
            for acct, a in e["accounts"].items():
                if a.get("retired"):
                    continue
                out[f"{eid}--{acct}"] = a.get("last_rotated") or e["fields"].get("last_rotated")
        else:
            out[eid] = e["fields"].get("last_rotated")
    return out


def read_planned(in_progress_targets):
    """rotate.py plan --preview writes this -- a values-free snapshot of what's
    about to be staged, so the dashboard shows something between 'plan' and
    'start' instead of a blank panel. Suppressed once the real rotation starts
    (cmd_start deletes it, but also check here defensively -- a stale file
    from an interrupted run should never shadow the real in-progress entry)."""
    p = os.path.join(STATE_DIR, "planned.json")
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    if data.get("target") in in_progress_targets:
        return None
    return data


def build_status():
    due, err = read_due()
    in_progress = read_in_progress()
    planned = read_planned({r["target"] for r in in_progress})
    exposed = pick(due, "EXPOSED")
    requested = pick(due, "REQUESTED")
    roboform_pending = pick(due, "ROBOFORM")
    overdue = pick(due, "OVERDUE")
    declined = pick(due, "DECLINED")

    flagged = {row["name"] for row in (exposed + requested + roboform_pending + overdue + declined)}
    flagged |= {r["target"] for r in in_progress}
    good = [{"name": name, "last_rotated": lr} for name, lr in sorted(all_targets_and_last_rotated().items())
            if name not in flagged]

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "needs_attention": any(r.get("needs_attention") for r in in_progress),
        "in_progress": in_progress,
        "planned": planned,
        "exposed": exposed,
        "requested": requested,
        "roboform_pending": roboform_pending,
        "overdue": overdue,
        "declined": declined,
        "good": good,
        "due_error": err,
    }


def set_declined(target, reason):
    """registry_set is a precise single-field line edit (rotate.py's own write-back
    mechanism) -- values-free, reversible, no vault/network touch. Does not commit;
    that stays a deliberate, visible git step like every other registry change."""
    value = "null" if reason is None else json.dumps(f"{dt.date.today().isoformat()}: {reason}")
    rz.registry_set(target, "rotation_declined", value)


PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>JCTsh Credential Rotation</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #f5f6f8; --panel: #ffffff; --text: #1a1d23; --muted: #6b7280;
    --border: #e2e5ea; --accent: #2563eb; --ok: #16a34a; --warn: #d97706; --bad: #dc2626;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #15171c; --panel: #1e2128; --text: #e7e9ec; --muted: #9aa1ad; --border: #2c303a; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 20px 16px 48px; background: var(--bg); color: var(--text);
         font: 14px/1.5 -apple-system, Segoe UI, Roboto, sans-serif; }
  h1 { font-size: 18px; margin: 0 0 4px; }
  .sub { color: var(--muted); font-size: 12px; margin-bottom: 20px; display: flex; gap: 8px; align-items: center; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ok); animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .35; } }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
           padding: 16px; margin-bottom: 16px; max-width: 760px; }
  .panel h2 { font-size: 14px; margin: 0 0 12px; }
  .empty { color: var(--muted); font-style: italic; }
  .rotation { border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 12px; }
  .rotation:last-child { margin-bottom: 0; }
  .rotation-head { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 6px; }
  .target { font-weight: 600; font-size: 15px; }
  .phase { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .03em; }
  .bar { height: 6px; border-radius: 3px; background: var(--border); margin: 10px 0; overflow: hidden; }
  .bar-fill { height: 100%; background: var(--accent); transition: width .3s ease; }
  .holders { margin-top: 8px; }
  .holder { padding: 6px 0; font-size: 13px; border-top: 1px solid var(--border); }
  .holder:first-child { border-top: none; }
  .holder-row { display: flex; align-items: center; gap: 8px; }
  .holder-row .label { flex: 1; }
  .check { width: 15px; height: 15px; border-radius: 4px; border: 1.5px solid var(--muted);
           display: inline-flex; align-items: center; justify-content: center; font-size: 11px;
           flex: none; }
  .check.checked { background: var(--ok); border-color: var(--ok); color: #fff; }
  .mode-tag { font-size: 10px; color: var(--muted); border: 1px solid var(--border); border-radius: 4px;
              padding: 0 5px; text-transform: uppercase; letter-spacing: .03em; }
  .desc { font-size: 12px; color: var(--muted); margin: 2px 0 0 23px; }
  .badge { font-size: 11px; padding: 1px 7px; border-radius: 99px; white-space: nowrap; }
  .b-done, .b-not-applicable { background: color-mix(in srgb, var(--ok) 18%, transparent); color: var(--ok); }
  .b-pending { background: color-mix(in srgb, var(--muted) 18%, transparent); color: var(--muted); }
  .b-applied { background: color-mix(in srgb, var(--accent) 18%, transparent); color: var(--accent); }
  .b-later { background: color-mix(in srgb, var(--warn) 18%, transparent); color: var(--warn); }
  .b-failed, .b-failed-check { background: color-mix(in srgb, var(--bad) 18%, transparent); color: var(--bad); }
  .meta { font-size: 12px; color: var(--muted); margin-top: 8px; }
  .next { margin-top: 10px; font-family: ui-monospace, Consolas, monospace; font-size: 12px;
          background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; }
  .list-row { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 4px 0;
              font-size: 13px; border-top: 1px solid var(--border); }
  .list-row:first-child { border-top: none; }
  .list-row .detail { color: var(--muted); text-align: right; flex: none; }
  .list-row .name { flex: 1; }
  .note { font-size: 11px; color: var(--muted); margin-top: 10px; }
  button.mini { font-size: 11px; padding: 3px 9px; border-radius: 6px; border: 1px solid var(--border);
                background: var(--bg); color: var(--text); cursor: pointer; flex: none; }
  button.mini:hover { border-color: var(--accent); color: var(--accent); }
  .attn-banner { display: none; background: var(--warn); color: #1a1d23; border-radius: 10px;
                 padding: 12px 16px; margin-bottom: 16px; max-width: 760px; font-weight: 600;
                 animation: attn-pulse 1.4s infinite; }
  .attn-banner.show { display: block; }
  @keyframes attn-pulse { 0%,100% { opacity: 1; } 50% { opacity: .75; } }
</style>
</head>
<body>
  <h1>Credential Rotation</h1>
  <div class="sub"><span class="dot" id="dot"></span><span id="updated">connecting...</span></div>

  <div class="attn-banner" id="attn-banner">&#9888; Switch to the Claude Code session &mdash; <span id="attn-why"></span></div>

  <div class="panel" id="planned-panel" style="display:none">
    <h2>Planned (not started yet)</h2>
    <div id="planned"></div>
    <div class="note">Staged by `rotate.py plan --preview`. Nothing has changed yet -- waiting for the go-ahead to run `start`.</div>
  </div>

  <div class="panel">
    <h2>In progress</h2>
    <div id="in-progress"><div class="empty">loading...</div></div>
  </div>

  <div class="panel" id="due-panel">
    <h2>Needs attention (information only -- not a to-do list)</h2>
    <div id="due"><div class="empty">loading...</div></div>
    <div class="note">CARD-0372: no rotation deadlines for this bucket. This is what's exposed, requested,
      overdue by cadence, or rotated-but-not-yet-in-RoboForm -- not permission to act.</div>
  </div>

  <div class="panel">
    <h2>Declined (explicit decision not to rotate)</h2>
    <div id="declined"><div class="empty">loading...</div></div>
  </div>

  <div class="panel">
    <h2>Good / up to date</h2>
    <div id="good"><div class="empty">loading...</div></div>
    <div class="note">Nothing flagged. "Decline" records that you've chosen not to rotate this one --
      it's reversible and stays visible here, it's never silently dropped.</div>
  </div>

<script>
function badge(status) {
  return `<span class="badge b-${status}">${status}</span>`;
}
function fmtTime(iso) {
  if (!iso) return '';
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}
function renderInProgress(list) {
  const el = document.getElementById('in-progress');
  if (!list.length) { el.innerHTML = '<div class="empty">nothing in progress</div>'; return; }
  el.innerHTML = list.map(r => {
    const pct = r.total ? Math.round(100 * r.done / r.total) : 0;
    const holders = r.holders.map(h => {
      const checked = h.status === 'done' || h.status === 'not-applicable';
      return `<div class="holder">
        <div class="holder-row">
          <span class="check ${checked ? 'checked' : ''}">${checked ? '✓' : ''}</span>
          <span class="label">${h.label}</span>
          <span class="mode-tag">${h.mode || 'guided'}</span>
          ${checked ? '' : badge(h.status)}
        </div>
        ${h.desc ? `<div class="desc">${h.desc}</div>` : ''}
      </div>`;
    }).join('');
    const next = r.next ? `<div class="next">${r.next}</div>` : '';
    return `<div class="rotation">
      <div class="rotation-head"><span class="target">${r.target}</span><span class="phase">${r.phase}</span></div>
      <div class="bar"><div class="bar-fill" style="width:${pct}%"></div></div>
      <div class="meta">${r.done}/${r.total} holders done &middot; RoboForm ${r.roboform_synced ? 'confirmed' : 'not yet'}
        &middot; window closes ${fmtTime(r.expires)}</div>
      <div class="holders">${holders}</div>
      ${next}
    </div>`;
  }).join('');
}
function renderDue(data) {
  const el = document.getElementById('due');
  const sections = [
    ['Exposed, not yet rotated', data.exposed],
    ['Rotation requested', data.requested],
    ['Rotated, not yet in RoboForm', data.roboform_pending],
    ['Overdue by cadence', data.overdue],
  ];
  const any = sections.some(([, rows]) => rows.length);
  if (!any) { el.innerHTML = '<div class="empty">nothing outstanding</div>'; return; }
  el.innerHTML = sections.filter(([, rows]) => rows.length).map(([title, rows]) => `
    <div style="margin-bottom:10px">
      <div style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.03em;margin-bottom:4px">${title}</div>
      ${rows.map(r => `<div class="list-row"><span>${r.name}</span><span class="detail">${r.detail}</span></div>`).join('')}
    </div>`).join('');
}
function renderPlanned(planned) {
  const panel = document.getElementById('planned-panel');
  if (!planned) { panel.style.display = 'none'; return; }
  panel.style.display = 'block';
  const holders = planned.holders.map(h => `<div class="holder">
      <div class="holder-row">
        <span class="check"></span>
        <span class="label">${h.label}</span>
        <span class="mode-tag">${h.mode}</span>
      </div>
      ${h.desc ? `<div class="desc">${h.desc}</div>` : ''}
    </div>`).join('');
  document.getElementById('planned').innerHTML = `<div class="rotation">
      <div class="rotation-head"><span class="target">${planned.target}</span><span class="phase">planned</span></div>
      <div class="holders">${holders}</div>
    </div>`;
}
function renderDeclined(rows) {
  const el = document.getElementById('declined');
  if (!rows.length) { el.innerHTML = '<div class="empty">none</div>'; return; }
  el.innerHTML = rows.map(r => `<div class="list-row">
      <span class="name">${r.name}</span>
      <span class="detail">${r.detail}</span>
      <button class="mini" onclick="undecline('${r.name}')">Un-decline</button>
    </div>`).join('');
}
function renderGood(rows) {
  const el = document.getElementById('good');
  if (!rows.length) { el.innerHTML = '<div class="empty">nothing else tracked</div>'; return; }
  el.innerHTML = rows.map(r => `<div class="list-row">
      <span class="name">${r.name}</span>
      <span class="detail">last rotated ${r.last_rotated || 'unknown'}</span>
      <button class="mini" onclick="decline('${r.name}')">Decline</button>
    </div>`).join('');
}
async function decline(name) {
  const reason = prompt(`Why decline rotating "${name}"? (recorded in the registry, reversible)`);
  if (reason === null || reason.trim() === '') return;
  await fetch('/api/decline', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target: name, reason: reason.trim() }) });
  tick();
}
async function undecline(name) {
  if (!confirm(`Un-decline "${name}" -- it goes back to being evaluated normally?`)) return;
  await fetch('/api/undecline', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target: name }) });
  tick();
}
const BASE_TITLE = document.title;
let lastNeedsAttention = false;
if ('Notification' in window && Notification.permission === 'default') {
  Notification.requestPermission();
}
function renderAttention(data) {
  const banner = document.getElementById('attn-banner');
  const hit = (data.in_progress || []).find(r => r.needs_attention);
  banner.classList.toggle('show', !!hit);
  if (hit) {
    document.getElementById('attn-why').textContent = `${hit.target}: ${hit.needs_attention_why}`;
    document.title = '⚠ ' + BASE_TITLE;
  } else {
    document.title = BASE_TITLE;
  }
  if (data.needs_attention && !lastNeedsAttention && 'Notification' in window && Notification.permission === 'granted') {
    new Notification('Credential rotation needs you', {
      body: hit ? `${hit.target}: ${hit.needs_attention_why}` : 'Switch to the Claude Code session.',
    });
  }
  lastNeedsAttention = !!data.needs_attention;
}
async function tick() {
  try {
    const r = await fetch('/api/status');
    const data = await r.json();
    renderPlanned(data.planned);
    renderInProgress(data.in_progress);
    renderDue(data);
    renderDeclined(data.declined);
    renderGood(data.good);
    renderAttention(data);
    document.getElementById('dot').style.background = 'var(--ok)';
    document.getElementById('updated').textContent = 'live -- updated ' + new Date(data.generated_at).toLocaleTimeString();
  } catch (e) {
    document.getElementById('dot').style.background = 'var(--bad)';
    document.getElementById('updated').textContent = 'lost connection to dashboard server';
  }
}
tick();
setInterval(tick, 3000);
</script>
</body>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", PAGE_HTML.encode("utf-8"))
        elif self.path == "/api/status":
            self._send(200, "application/json", json.dumps(build_status()).encode("utf-8"))
        else:
            self._send(404, "text/plain", b"not found")

    def do_POST(self):
        if self.path not in ("/api/decline", "/api/undecline"):
            self._send(404, "text/plain", b"not found")
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            target = body["target"]
            if self.path == "/api/decline":
                set_declined(target, body.get("reason") or "declined")
            else:
                set_declined(target, None)
            self._send(200, "application/json", b'{"ok": true}')
        except Exception as e:
            self._send(400, "application/json", json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))


def main():
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Rotation dashboard: {url}  (Ctrl+C to stop)", flush=True)
    if "--no-browser" not in sys.argv:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
