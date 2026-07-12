#!/usr/bin/env python3
"""
JCTsh Log Server
Subscribes to jctsh/+/+/log, serves a live dashboard at http://JCTsh.local/
"""

import base64
import json
import os
import logging
import logging.handlers
import re
import signal
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer

import paho.mqtt.client as mqtt

# ── Config ────────────────────────────────────────────────────────────────────
MQTT_BROKER = "localhost"
MQTT_PORT   = 1883
MQTT_USER          = os.environ["MQTT_USER"]
MQTT_PASS          = os.environ["MQTT_PASS"]
DASHBOARD_USER     = os.environ["DASHBOARD_USER"]
DASHBOARD_PASS     = os.environ["DASHBOARD_PASS"]
MQTT_TOPIC         = "jctsh/+/+/log"
_TZ                = ZoneInfo("America/Phoenix")
HEARTBEAT_TOPIC    = "jctsh/core/log-server/log"
HEARTBEAT_INTERVAL = 3600
HTTP_PORT   = 80
_REMOTE_COMPONENTS     = {"coachproxyos"}
_HOME_HB_THRESHOLD_MIN = 70   # hourly beat + 10 min grace
LOG_DIR     = "/home/pi/jctsh/logs"
LOG_FILE    = os.path.join(LOG_DIR, "jctsh.log")
STATE_FILE  = os.path.join(LOG_DIR, "state.json")
MAX_ENTRIES = 200
KANBAN_RAW_URL = "https://raw.githubusercontent.com/joscthomas/jctsh/main/kanban-board.md"

# ── Shared state ─────────────────────────────────────────────────────────────
_lock        = threading.Lock()
_entries     = deque(maxlen=MAX_ENTRIES)   # flushed, displayable entries
_pending     = None                         # current non-heartbeat repeat group (not yet flushed)
_hb_groups   = {}                           # component -> active heartbeat collapse group
_last_seen   = {}                           # component -> most recent entry, regardless of eviction
_mqtt_client = None

# ── File logging ─────────────────────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)
_file_logger = logging.getLogger("jctsh")
_file_logger.setLevel(logging.INFO)
_fh = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=1_000_000, backupCount=5
)
_fh.setFormatter(logging.Formatter("%(message)s"))
_file_logger.addHandler(_fh)


# ── State persistence (survive service restarts) ────────────────────────────
def _save_state():
    """Persist _entries and _last_seen so the dashboard doesn't start empty
    after a restart. Caller must hold _lock. Best-effort — a failed save
    just means the next restart starts fresh, same as before this existed."""
    try:
        data = {
            "entries": list(_entries),
            "last_seen": {
                comp: {k: v for k, v in e.items() if k != "_state_key"}
                for comp, e in _last_seen.items()
            },
        }
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, STATE_FILE)
    except OSError:
        pass


def _load_state():
    """Restore _entries and _last_seen from disk on startup, if present.
    Does not re-write anything to the log file — this only rehydrates the
    in-memory view. _pending/_hb_groups intentionally start fresh."""
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
        for e in data.get("entries", []):
            _entries.append(e)
        _last_seen.update(data.get("last_seen", {}))
    except (OSError, json.JSONDecodeError):
        pass


def _heartbeat_state_key(message):
    """Return the collapse key for a collapsible message.

    Watchdog messages: key is the full message so a changing active list
    starts a new group.  Device heartbeats with discrete ON/OFF state break
    on state change.  Continuous values (e.g. temp) always return the same
    key so all heartbeats from that component collapse into one group.
    """
    if message.startswith("Watchdog: "):
        return message
    parts = message.rsplit(", ", 1)
    if len(parts) > 1:
        last = parts[-1]
        if last.endswith(": ON") or last.endswith(": OFF"):
            return last
    return "heartbeat"


def _format_line(e):
    count = e["count"]
    msg   = e["message"]
    if count > 1 and "first_ts" in e:
        first_hm = e["first_ts"][11:16]
        last_hm  = e["ts"][11:16]
        if msg.startswith("Heartbeat - "):
            details = msg[len("Heartbeat - "):]
            display = f"Heartbeat ×{count} [{first_hm}–{last_hm}] — {details}"
        else:
            display = f"{msg}  ×{count} [{first_hm}–{last_hm}]"
    else:
        display = msg
        if count > 1:
            display += f"  (×{count})"
    return f"{e['ts']} | {e['component']:<15} | {e['category']:<8} | {display}"


def _flush_pending():
    """Move pending entry into the display deque and write to file. Caller must hold _lock."""
    global _pending
    if _pending:
        _entries.append(dict(_pending))
        _file_logger.info(_format_line(_pending))
        _pending = None


def _flush_hb_group(component):
    """Flush heartbeat group for a component into _entries and file. Caller must hold _lock."""
    group = _hb_groups.pop(component, None)
    if group:
        entry = {k: v for k, v in group.items() if k != "_state_key"}
        _entries.append(entry)
        _file_logger.info(_format_line(entry))


def _flush_all_hb_groups():
    """Flush all active heartbeat groups. Caller must hold _lock."""
    for comp in list(_hb_groups.keys()):
        _flush_hb_group(comp)


# ── MQTT callbacks ────────────────────────────────────────────────────────────
_STATUS_TOPIC = "jctsh/components/+/status"


def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe([(MQTT_TOPIC, 0), (_STATUS_TOPIC, 0)])
        print(f"[MQTT] Connected to {MQTT_BROKER}. Subscribed to {MQTT_TOPIC}, {_STATUS_TOPIC}")
        client.publish(HEARTBEAT_TOPIC, json.dumps({
            "component": "jctsh-core",
            "category":  "System",
            "message":   "Log server connected.",
        }))
    else:
        print(f"[MQTT] Connection failed rc={rc}")


def _store_entry(component, category, message, ts):
    """Store a log entry — heartbeat vs regular. Caller must hold _lock."""
    global _pending
    if message.startswith("Heartbeat - ") or message.startswith("Watchdog: "):
        state_key = _heartbeat_state_key(message)
        existing  = _hb_groups.get(component)
        if existing and existing["_state_key"] == state_key:
            existing["ts"]      = ts
            existing["message"] = message
            existing["count"]  += 1
        else:
            if existing:
                _flush_hb_group(component)
            _hb_groups[component] = {
                "ts": ts, "first_ts": ts,
                "component": component, "category": category,
                "message": message, "count": 1,
                "_state_key": state_key,
            }
        _last_seen[component] = _hb_groups[component]
    else:
        # Non-heartbeat: flush any open heartbeat group for this component first.
        # Sensor-category messages are co-scheduled with the heartbeat interval —
        # don't let them break up heartbeat collapsing.
        if component in _hb_groups and category != "Sensor":
            _flush_hb_group(component)
        key = (component, category, message)
        if (_pending and
                (_pending["component"], _pending["category"], _pending["message"]) == key):
            _pending["count"] += 1
        else:
            _flush_pending()
            _pending = {
                "ts": ts, "component": component,
                "category": category, "message": message, "count": 1,
            }
        _last_seen[component] = _pending
    _save_state()


def _on_message(client, userdata, msg):
    ts = datetime.now(_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")

    # ESPHome device availability: jctsh/components/<name>/status → "online"/"offline"
    if msg.topic.endswith("/status"):
        try:
            payload = msg.payload.decode("utf-8").strip()
        except Exception:
            return
        parts = msg.topic.split("/")
        if len(parts) == 4:
            component = parts[2]
            if payload == "online":
                category, message = "MQTT", "Connected."
            elif payload == "offline":
                category, message = "MQTT", "Disconnected (LWT)."
            else:
                return
            with _lock:
                _store_entry(component, category, message, ts)
        return

    # Standard JSON log message on jctsh/+/+/log
    try:
        data      = json.loads(msg.payload.decode("utf-8"))
        component = str(data.get("component", "unknown"))
        category  = str(data.get("category",  "System"))
        message   = str(data.get("message",   ""))
        with _lock:
            _store_entry(component, category, message, ts)
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
        pass


# ── HTML dashboard ────────────────────────────────────────────────────────────
_CATEGORY_COLORS = {
    "MQTT":   "#00ccff",
    "System": "#00cc99",
    "Sensor": "#e0e0e0",
    "Test":   "#ffaa00",
}

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>JCTsh Log Dashboard</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMiAzMiI+PHJlY3Qgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiBmaWxsPSIjMWExYTFhIi8+PHRleHQgeD0iMTYiIHk9IjI0IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjMDBjYzk5IiBmb250LWZhbWlseT0ibW9ub3NwYWNlIiBmb250LXNpemU9IjIyIiBmb250LXdlaWdodD0iYm9sZCI+SjwvdGV4dD48L3N2Zz4=">
  <style>
    html, body { height:100%; }
    body { background:#1a1a1a; color:#e0e0e0; font-family:monospace;
           font-size:13px; margin:0; display:flex; flex-direction:column; overflow:hidden; }
    h2   { color:#00cc99; margin-bottom:4px; }
    .sub { color:#b0b0b0; font-size:11px; margin-bottom:16px; }
    .headerblock { flex:none; padding:20px 20px 0; }
    .controls { margin-bottom:12px; }
    .controls label  { color:#c0c0c0; margin-right:4px; }
    .controls select { background:#111; color:#e0e0e0; border:1px solid #333;
                       padding:3px 8px; font-family:monospace; margin-right:16px;
                       cursor:pointer; }
    .tablewrap { flex:1; overflow-y:auto; padding:0 20px 20px; }
    table { border-collapse:collapse; width:100%; }
    th    { color:#aaa; font-size:11px; text-align:left; padding:4px 8px;
            border-bottom:1px solid #2a2a2a; background:#1a1a1a;
            position:sticky; top:0; z-index:1; }
    td    { padding:3px 8px; vertical-align:top; cursor:text; }
    tr:hover td { background:#1f1f1f; }
    .hidden { display:none; }
  </style>
</head>
<body>
  <div class="headerblock">
    <h2>JCTsh Log Dashboard</h2>
    <p class="sub">Updates every 5s &nbsp;|&nbsp; Last %%MAX%% entries &nbsp;|&nbsp; <a href="/log" target="_blank" style="color:#b0b0b0">%%LOG%%</a> &nbsp;|&nbsp; <a href="/status" style="color:#b0b0b0">Device status</a> &nbsp;|&nbsp; <a href="/kanban" style="color:#b0b0b0">Kanban board</a></p>
    <div class="controls">
      <label>Component:</label>
      <select id="fc" onchange="f()"><option value="">All</option>%%COMP%%</select>
      <label>Category:</label>
      <select id="fk" onchange="f()">
        <option value="">All</option>
        <option>MQTT</option><option>System</option>
        <option>Sensor</option><option>Alert</option><option>Test</option>
      </select>
    </div>
  </div>
  <div class="tablewrap">
    <table id="log">
      <thead>
        <tr><th>Timestamp</th><th>Component</th><th>Category</th><th>Message</th></tr>
      </thead>
      <tbody>
%%ROWS%%
      </tbody>
    </table>
  </div>
  <script>
    var _COLORS = {MQTT:'#00ccff',System:'#00cc99',Sensor:'#e0e0e0',Test:'#ffaa00'};
    function _color(e) {
      if (e.category === 'Alert') return e.message.indexOf('CRITICAL') !== -1 ? '#ff4444' : '#ffaa00';
      return _COLORS[e.category] || '#e0e0e0';
    }
    function _esc(s) {
      return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }
    function _row(e) {
      var c = _color(e);
      var msg, x = '';
      if (e.count > 1 && e.first_ts) {
        var ft = e.first_ts.slice(11,16), lt = e.ts.slice(11,16);
        if (e.message.indexOf('Heartbeat - ') === 0) {
          var details = e.message.slice(12);
          msg = 'Heartbeat \xd7' + e.count + ' [' + ft + '–' + lt + '] — ' + details;
        } else {
          msg = e.message + '  \xd7' + e.count + ' [' + ft + '–' + lt + ']';
        }
      } else {
        msg = e.message;
        if (e.count > 1) x = ' <span style="color:'+c+'">\xd7'+e.count+'</span>';
      }
      return '<tr data-c="'+_esc(e.component)+'" data-k="'+_esc(e.category)+'">'
        +'<td style="color:#b0b0b0;white-space:nowrap">'+_esc(e.ts)+'</td>'
        +'<td style="color:#b0b0b0">'+_esc(e.component)+'</td>'
        +'<td style="color:'+c+'">'+_esc(e.category)+'</td>'
        +'<td style="color:'+c+'">'+_esc(msg)+x+'</td>'
        +'</tr>';
    }
    function f() {
      var comp = document.getElementById('fc').value;
      var cat  = document.getElementById('fk').value;
      localStorage.setItem('jctsh_fc', comp);
      localStorage.setItem('jctsh_fk', cat);
      document.querySelectorAll('#log tbody tr').forEach(function(r) {
        var comps = r.dataset.c.split(',').map(function(s){return s.trim();});
        r.classList.toggle('hidden',
          (comp && comps.indexOf(comp) === -1) || (cat && r.dataset.k !== cat));
      });
    }
    function _render(data) {
      document.querySelector('#log tbody').innerHTML = data.entries.map(_row).join('');
      var fc  = document.getElementById('fc');
      var sel = fc.value;
      fc.innerHTML = '<option value="">All</option>'
        + data.components.map(function(c){return '<option>'+_esc(c)+'</option>';}).join('');
      fc.value = sel;
      f();
    }
    var _latestData     = null;
    var _lastSelActivity = 0;
    var _SEL_GRACE_MS    = 3000;
    function _hasSelection() {
      var sel = window.getSelection();
      return !!(sel && sel.toString().length > 0);
    }
    function _touchSelection() { _lastSelActivity = Date.now(); }
    function _maybeRender() {
      if (!_latestData) return;
      if (_hasSelection()) return;
      if (Date.now() - _lastSelActivity < _SEL_GRACE_MS) return;
      _render(_latestData);
    }
    function _poll() {
      fetch('/data').then(function(r){return r.json();}).then(function(data) {
        _latestData = data;
        _maybeRender();
      }).catch(function(){});
    }
    window.addEventListener('DOMContentLoaded', function() {
      var fc = localStorage.getItem('jctsh_fc') || '';
      var fk = localStorage.getItem('jctsh_fk') || '';
      if (fc) document.getElementById('fc').value = fc;
      if (fk) document.getElementById('fk').value = fk;
      f();
      setInterval(_poll, 5000);
      setInterval(_maybeRender, 1000);
      document.addEventListener('selectionchange', function() {
        _touchSelection();
      });
      var logTable = document.getElementById('log');
      logTable.addEventListener('mousedown', _touchSelection);
      logTable.addEventListener('mouseup', _touchSelection);
    });
  </script>
</body>
</html>"""


_STATUS_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>JCTsh Device Status</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMiAzMiI+PHJlY3Qgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiBmaWxsPSIjMWExYTFhIi8+PHRleHQgeD0iMTYiIHk9IjI0IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjMDBjYzk5IiBmb250LWZhbWlseT0ibW9ub3NwYWNlIiBmb250LXNpemU9IjIyIiBmb250LXdlaWdodD0iYm9sZCI+SjwvdGV4dD48L3N2Zz4=">
  <style>
    body    { background:#1a1a1a; color:#e0e0e0; font-family:monospace;
              font-size:13px; margin:20px; }
    h2      { color:#00cc99; margin-bottom:4px; }
    h3      { color:#aaa; font-size:11px; margin-top:24px; margin-bottom:8px;
              text-transform:uppercase; letter-spacing:2px; }
    .sub    { color:#b0b0b0; font-size:11px; margin-bottom:16px; }
    table   { border-collapse:collapse; width:100%; margin-bottom:8px; }
    th      { color:#aaa; font-size:11px; text-align:left; padding:4px 8px;
              border-bottom:1px solid #2a2a2a; }
    td      { padding:3px 8px; vertical-align:top; }
    tr:hover td { background:#1f1f1f; }
    .online  { color:#00cc99; }
    .offline { color:#ff4444; }
    .unknown { color:#aaa; }
    .dim     { color:#666; }
    .ts      { color:#b0b0b0; white-space:nowrap; }
    .msg     { color:#d0d0d0; }
  </style>
</head>
<body>
  <h2>JCTsh Device Status</h2>
  <p class="sub">Auto-refreshes every 60s &nbsp;|&nbsp; Based on last %%MAX%% log entries
    &nbsp;|&nbsp; <a href="/" style="color:#b0b0b0">Log dashboard</a>
    &nbsp;|&nbsp; <a href="/kanban" style="color:#b0b0b0">Kanban board</a></p>
  <h3>Always-on</h3>
  <table>
    <thead><tr>
      <th>Component</th><th>Status</th><th>Last Heartbeat</th><th>Last Reading</th>
    </tr></thead>
    <tbody>
%%HOME_ROWS%%
    </tbody>
  </table>
  <h3>Mobile</h3>
  <table>
    <thead><tr>
      <th>Component</th><th>Last Seen</th><th>Last Message</th>
    </tr></thead>
    <tbody>
%%REMOTE_ROWS%%
    </tbody>
  </table>
  <script>setTimeout(function(){location.reload();},60000);</script>
</body>
</html>"""


def _ago(ts_str):
    """Return a human-readable 'X ago' string from a log timestamp."""
    if not ts_str:
        return "—"
    try:
        dt   = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=_TZ)
        secs = int((datetime.now(_TZ) - dt).total_seconds())
        if secs < 120:
            return f"{secs}s ago"
        if secs < 3600:
            return f"{secs // 60}m ago"
        if secs < 86400:
            h, m = divmod(secs // 60, 60)
            return (f"{h}h {m}m ago" if m else f"{h}h ago")
        return f"{secs // 86400}d ago"
    except (ValueError, TypeError):
        return "—"


def _compute_status(entries):
    """Derive per-component status summary from a snapshot of log entries."""
    now  = datetime.now(_TZ)
    info = {}
    for e in entries:
        for comp in e["component"].split(","):
            comp = comp.strip()
            rec  = info.setdefault(comp, {
                "last_ts": None, "last_msg": None,
                "last_hb_ts": None, "has_hb": False,
                "last_reading_ts": None, "last_reading_msg": None,
            })
            ts, msg = e["ts"], e["message"]
            if rec["last_ts"] is None or ts > rec["last_ts"]:
                rec["last_ts"]  = ts
                rec["last_msg"] = msg
            is_hb = msg.startswith("Heartbeat - ") or msg.startswith("Watchdog: ")
            if is_hb:
                rec["has_hb"] = True
                if rec["last_hb_ts"] is None or ts > rec["last_hb_ts"]:
                    rec["last_hb_ts"] = ts
            else:
                if rec["last_reading_ts"] is None or ts > rec["last_reading_ts"]:
                    rec["last_reading_ts"]  = ts
                    rec["last_reading_msg"] = msg

    result = {}
    for comp, rec in info.items():
        is_remote = comp in _REMOTE_COMPONENTS
        if is_remote:
            status = "?"
        elif not rec["has_hb"]:
            status = "?"
        else:
            try:
                dt  = datetime.strptime(rec["last_hb_ts"][:19], "%Y-%m-%d %H:%M:%S")
                dt  = dt.replace(tzinfo=_TZ)
                age = (now - dt).total_seconds() / 60
                status = "Online" if age < _HOME_HB_THRESHOLD_MIN else "Offline"
            except (ValueError, TypeError):
                status = "?"
        result[comp] = {**rec, "status": status, "is_remote": is_remote}
    return result


def _build_status_html():
    snap   = _snapshot()
    comps  = _compute_status(snap)
    home   = sorted((c, r) for c, r in comps.items() if not r["is_remote"])
    remote = sorted((c, r) for c, r in comps.items() if r["is_remote"])

    home_rows = []
    for comp, rec in home:
        s = rec["status"]
        if s == "Online":
            scls, slabel = "online",  "Online"
        elif s == "Offline":
            scls, slabel = "offline", "Offline"
        else:
            scls, slabel = "unknown", "?"
        hb_cell = (f'<span class="ts">{escape(_ago(rec["last_hb_ts"]))}</span>'
                   if rec["last_hb_ts"] else '<span class="dim">—</span>')
        if rec["last_reading_msg"]:
            rd_msg  = rec["last_reading_msg"]
            rd_disp = escape(rd_msg if len(rd_msg) <= 80 else rd_msg[:77] + "…")
            rd_cell = f'{rd_disp} <span class="ts">{escape(_ago(rec["last_reading_ts"]))}</span>'
        else:
            rd_cell = '<span class="dim">—</span>'
        home_rows.append(
            f'      <tr>'
            f'<td>{escape(comp)}</td>'
            f'<td class="{scls}">{slabel}</td>'
            f'<td>{hb_cell}</td>'
            f'<td class="msg">{rd_cell}</td>'
            f'</tr>'
        )

    remote_rows = []
    for comp, rec in remote:
        if rec["last_ts"]:
            ls_cell = (f'<span class="ts">{escape(rec["last_ts"][:16])}</span>'
                       f' <span class="dim">({escape(_ago(rec["last_ts"]))})</span>')
        else:
            ls_cell = '<span class="dim">—</span>'
        lm = rec["last_msg"] or ""
        lm_disp = escape(lm if len(lm) <= 80 else lm[:77] + "…")
        remote_rows.append(
            f'      <tr>'
            f'<td>{escape(comp)}</td>'
            f'<td>{ls_cell}</td>'
            f'<td class="msg">{lm_disp}</td>'
            f'</tr>'
        )

    no_home   = "      <tr><td colspan='4' class='dim'>No always-on devices in recent log.</td></tr>"
    no_remote = "      <tr><td colspan='3' class='dim'>No mobile devices in recent log.</td></tr>"
    html = _STATUS_TEMPLATE
    html = html.replace("%%HOME_ROWS%%",   "\n".join(home_rows)   or no_home)
    html = html.replace("%%REMOTE_ROWS%%", "\n".join(remote_rows) or no_remote)
    html = html.replace("%%MAX%%", str(MAX_ENTRIES))
    return html


# ── Kanban board (live-parsed from kanban-board.md, CARD-0057) ──────────────
_KANBAN_COLUMNS = ["Backlog", "Planning", "Design", "Build", "Done", "Defer"]
_KANBAN_COLUMN_RE = re.compile(
    r"^## (" + "|".join(_KANBAN_COLUMNS) + r")\s*$", re.MULTILINE
)
_KANBAN_CARD_RE = re.compile(
    r"^### CARD-(\d{4}) · \[(\w+)\] \[([\w-]+)\] (.+?)\s*$", re.MULTILINE
)


def _parse_kanban_board(text):
    """Parse kanban-board.md into a list of card dicts (id/type/tag/column/
    title/notes/flag). Best-effort: only recognizes the file's established
    '### CARD-XXXX · [type] [tag] Title' / '## ColumnName' conventions —
    a card that doesn't match those is silently skipped, not an error."""
    col_matches = list(_KANBAN_COLUMN_RE.finditer(text))
    cards = []
    for i, cm in enumerate(col_matches):
        col_name = cm.group(1)
        start = cm.end()
        end = col_matches[i + 1].start() if i + 1 < len(col_matches) else len(text)
        section = text[start:end]
        card_matches = list(_KANBAN_CARD_RE.finditer(section))
        for j, m in enumerate(card_matches):
            cid, ctype, ctag, title = m.group(1), m.group(2), m.group(3), m.group(4)
            body_start = m.end()
            body_end = (card_matches[j + 1].start() if j + 1 < len(card_matches)
                        else len(section))
            body = section[body_start:body_end]
            body = re.sub(r"(?m)^---\s*$", "", body).strip()
            body = re.sub(r"^\*\*Notes:\*\*\s*", "", body)
            card = {
                "id": cid, "type": ctype, "tag": ctag,
                "column": col_name, "title": title.strip(), "notes": body,
            }
            if re.search(r"(?m)^\*\*Blocked", body):
                card["flag"] = "blocked"
            cards.append(card)
    return cards


def _load_kanban_cards():
    """Pull kanban-board.md straight from GitHub (public repo) on every
    request — no local copy on the Pi, no push/scp/hook needed. Freshness
    is tied to `git push`, not to individual edits. Returns None on any
    network failure (offline, GitHub down, rate-limited, etc.)."""
    try:
        req = urllib.request.Request(
            KANBAN_RAW_URL, headers={"Cache-Control": "no-cache"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError, UnicodeDecodeError):
        return None
    return _parse_kanban_board(text)


_KANBAN_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>JCTsh Kanban Board</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMiAzMiI+PHJlY3Qgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiBmaWxsPSIjMWExYTFhIi8+PHRleHQgeD0iMTYiIHk9IjI0IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjMDBjYzk5IiBmb250LWZhbWlseT0ibW9ub3NwYWNlIiBmb250LXNpemU9IjIyIiBmb250LXdlaWdodD0iYm9sZCI+SjwvdGV4dD48L3N2Zz4=">
<style>
  :root {
    --bg: #eef3f8;
    --bg-grid: #dfe9f2;
    --surface: #ffffff;
    --surface-2: #e3ecf4;
    --ink: #16324f;
    --ink-muted: #4d6b87;
    --ink-faint: #8098b0;
    --line: #c7d8e6;
    --line-strong: #a9c2d8;
    --accent: #a8611f;
    --accent-ink: #fffaf3;
    --good: #3f7248;
    --warning: #93701a;
    --danger: #a8503f;
    --idea: #35648f;
    --shadow: 0 1px 2px rgba(22,50,79,0.06), 0 6px 16px -8px rgba(22,50,79,0.18);
    --radius: 3px;
    --mono: ui-monospace, "Cascadia Code", "JetBrains Mono", "SF Mono", Consolas, "Liberation Mono", monospace;
    --sans: ui-sans-serif, -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0d1c2e;
      --bg-grid: #112741;
      --surface: #163657;
      --surface-2: #1c4267;
      --ink: #eaf2fa;
      --ink-muted: #a3bcd2;
      --ink-faint: #6f8caa;
      --line: #2c4d6f;
      --line-strong: #3c6187;
      --accent: #e39a52;
      --accent-ink: #24160a;
      --good: #7ab982;
      --warning: #e0bd57;
      --danger: #e0897a;
      --idea: #79aede;
      --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 20px -10px rgba(0,0,0,0.5);
    }
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body {
    margin: 0;
    background:
      repeating-linear-gradient(0deg, transparent, transparent 27px, var(--bg-grid) 27px, var(--bg-grid) 28px),
      repeating-linear-gradient(90deg, transparent, transparent 27px, var(--bg-grid) 27px, var(--bg-grid) 28px),
      var(--bg);
    color: var(--ink);
    font-family: var(--sans);
    -webkit-font-smoothing: antialiased;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  @media (prefers-reduced-motion: reduce) {
    * { animation-duration: 0.001ms !important; transition-duration: 0.001ms !important; }
  }
  a { color: var(--accent); }
  code {
    font-family: var(--mono);
    font-size: 0.92em;
    background: var(--surface-2);
    border: 1px solid var(--line);
    border-radius: 2px;
    padding: 0.05em 0.35em;
  }
  .titleblock {
    flex: none;
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 1.25rem 2rem;
    align-items: end;
    padding: 1rem 1.5rem 0.85rem;
    border-bottom: 2px solid var(--ink);
    background: var(--surface);
  }
  .titleblock__id { font-family: var(--mono); line-height: 1.15; }
  .titleblock__id .proj { font-size: 1.3rem; font-weight: 700; letter-spacing: 0.01em; text-wrap: balance; }
  .titleblock__id .sheet { margin-top: 0.2rem; font-size: 0.72rem; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.08em; }
  .titleblock__meta {
    display: flex; gap: 1.75rem; font-family: var(--mono); font-size: 0.72rem;
    color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.07em;
    align-self: end; padding-bottom: 0.15rem;
  }
  .titleblock__meta b {
    display: block; color: var(--ink); font-weight: 600; text-transform: none;
    letter-spacing: normal; font-size: 0.92rem; margin-top: 0.15rem;
  }
  .titleblock__controls { display: flex; flex-direction: column; gap: 0.5rem; align-items: flex-end; }
  .search {
    display: flex; align-items: center; gap: 0.4rem; background: var(--surface-2);
    border: 1px solid var(--line-strong); border-radius: var(--radius); padding: 0.32rem 0.6rem; width: 15.5rem;
  }
  .search svg { flex: none; opacity: 0.55; }
  .search input { border: 0; background: transparent; color: var(--ink); font-family: var(--sans); font-size: 0.85rem; width: 100%; outline: none; }
  .search input::placeholder { color: var(--ink-faint); }
  .chips { display: flex; gap: 0.4rem; }
  .chip {
    font-family: var(--mono); font-size: 0.68rem; letter-spacing: 0.04em; text-transform: uppercase;
    border: 1px solid var(--line-strong); background: var(--surface-2); color: var(--ink-muted);
    border-radius: 999px; padding: 0.28rem 0.65rem; cursor: pointer; display: flex; align-items: center; gap: 0.35rem; user-select: none;
  }
  .chip:hover { border-color: var(--ink-faint); }
  .chip[aria-pressed="true"] { color: var(--ink); border-color: currentColor; }
  .chip[aria-pressed="true"] .dot { opacity: 1; }
  .chip[aria-pressed="false"] { opacity: 0.55; }
  .chip .dot { width: 0.5rem; height: 0.5rem; border-radius: 50%; background: var(--dot); opacity: 0.35; flex: none; }
  .chip:focus-visible, button:focus-visible, summary:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .board { flex: 1; display: flex; gap: 1rem; padding: 1rem 1.5rem 1.25rem; overflow-x: auto; overflow-y: hidden; align-items: flex-start; }
  .column {
    flex: none; width: 21rem; display: flex; flex-direction: column; max-height: 100%;
    background: color-mix(in srgb, var(--surface) 55%, transparent);
    border: 1px solid var(--line); border-radius: var(--radius); transition: width 0.15s ease;
  }
  .column[data-collapsed="true"] { width: 2.6rem; }
  .column[data-collapsed="true"] .column__body, .column[data-collapsed="true"] .column__desc { display: none; }
  .column[data-collapsed="true"] .column__head {
    writing-mode: vertical-rl; text-orientation: mixed; height: 100%; padding: 0.75rem 0; border-bottom: 0; border-right: 1px solid var(--line);
  }
  .column[data-collapsed="true"] .column__head .colcount { writing-mode: horizontal-tb; }
  .column__head {
    flex: none; display: flex; align-items: center; gap: 0.55rem; padding: 0.65rem 0.75rem;
    border-bottom: 1px solid var(--line); cursor: pointer; background: none; border-top: none;
    border-left: none; border-right: none; width: 100%; text-align: left; color: inherit; font: inherit;
  }
  .column__head .name { font-family: var(--mono); font-weight: 600; font-size: 0.86rem; letter-spacing: 0.02em; flex: 1; }
  .colcount {
    font-family: var(--mono); font-size: 0.72rem; color: var(--ink-muted); background: var(--surface-2);
    border: 1px solid var(--line); border-radius: 999px; padding: 0.05rem 0.5rem;
  }
  .column__desc { flex: none; font-size: 0.74rem; color: var(--ink-muted); padding: 0.55rem 0.75rem 0; line-height: 1.4; }
  .column__body { flex: 1; overflow-y: auto; padding: 0.65rem; display: flex; flex-direction: column; gap: 0.6rem; }
  .column__empty { font-size: 0.8rem; color: var(--ink-faint); font-style: italic; padding: 0.5rem 0.15rem; }
  .column[data-col="Backlog"]  .column__head { border-top: 3px solid var(--ink-faint); }
  .column[data-col="Planning"] .column__head { border-top: 3px solid var(--idea); }
  .column[data-col="Design"]   .column__head { border-top: 3px solid var(--accent); }
  .column[data-col="Build"]    .column__head { border-top: 3px solid var(--warning); }
  .column[data-col="Done"]     .column__head { border-top: 3px solid var(--good); }
  .column[data-col="Defer"]    .column__head { border-top: 3px dashed var(--ink-faint); }
  .card { background: var(--surface); border: 1px solid var(--line); border-left: 3px solid var(--stripe, var(--ink-faint)); border-radius: var(--radius); box-shadow: var(--shadow); }
  .card[data-type="bug"]         { --stripe: var(--danger); }
  .card[data-type="enhancement"] { --stripe: var(--accent); }
  .card[data-type="idea"]        { --stripe: var(--idea); }
  .card > summary { list-style: none; cursor: pointer; padding: 0.6rem 0.7rem; display: grid; grid-template-columns: auto auto 1fr auto; align-items: center; gap: 0.4rem 0.5rem; }
  .card > summary::-webkit-details-marker { display: none; }
  .card .cid { font-family: var(--mono); font-size: 0.7rem; font-weight: 700; color: var(--stripe, var(--ink-muted)); }
  .card .ctype {
    font-family: var(--mono); font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--stripe, var(--ink-muted)); border: 1px solid var(--stripe, var(--line)); border-radius: 2px; padding: 0.02rem 0.32rem;
  }
  .card .ctag { grid-column: 1 / -1; font-family: var(--mono); font-size: 0.68rem; color: var(--ink-faint); }
  .card .ctitle { grid-column: 1 / -1; font-size: 0.9rem; font-weight: 600; line-height: 1.35; text-wrap: balance; }
  .card .cmeta { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.1rem; }
  .flag { font-family: var(--mono); font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.05em; border-radius: 2px; padding: 0.08rem 0.4rem; border: 1px solid transparent; }
  .flag[data-flag="blocked"] { color: var(--danger); border-color: var(--danger); background: color-mix(in srgb, var(--danger) 12%, transparent); }
  .chevron { color: var(--ink-faint); transition: transform 0.15s ease; flex: none; }
  .card[open] > summary .chevron { transform: rotate(90deg); }
  .card__detail { padding: 0 0.75rem 0.8rem 0.95rem; border-top: 1px dashed var(--line); margin-top: 0.1rem; padding-top: 0.6rem; }
  .card__detail p { margin: 0 0 0.6rem; font-size: 0.83rem; line-height: 1.55; color: var(--ink); }
  .card__detail p:last-child { margin-bottom: 0; }
  .card__detail ul { margin: 0 0 0.6rem; padding-left: 1.1rem; font-size: 0.83rem; line-height: 1.5; }
  .card__detail li { margin-bottom: 0.25rem; }
  .card__detail strong { color: var(--ink); }
  .noresults { color: var(--ink-faint); font-family: var(--mono); font-size: 0.85rem; padding: 2rem; }
  ::-webkit-scrollbar { width: 10px; height: 10px; }
  ::-webkit-scrollbar-thumb { background: var(--line-strong); border-radius: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
</style>
</head>
<body>
<div class="titleblock">
  <div class="titleblock__id">
    <div class="proj">JCTsh Kanban Board</div>
    <div class="sheet">kanban-board.md — Live from GitHub</div>
  </div>
  <div class="titleblock__meta">
    <div>Cards<b id="metaCount">–</b></div>
    <div>Fetched<b id="metaUpdated">–</b></div>
  </div>
  <div class="titleblock__controls">
    <div class="search">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input id="q" type="search" placeholder="Search cards, tags, notes…" autocomplete="off" />
    </div>
    <div class="chips" id="typeChips"></div>
  </div>
</div>
<div class="board" id="board"><div class="noresults">Loading…</div></div>
<script>
(function () {
  var COLUMNS = [
    { key: 'Backlog',  desc: 'Captured, not yet being worked on.' },
    { key: 'Planning', desc: 'Plan is being laid out.' },
    { key: 'Design',   desc: 'Claude Code instructions being written.' },
    { key: 'Build',    desc: 'Going through instructions, including testing.' },
    { key: 'Done',     desc: 'Complete.' },
    { key: 'Defer',    desc: 'A deliberate decision not to pursue for now.' }
  ];
  var TYPES = [
    { key: 'bug', label: 'Bug', varName: '--danger' },
    { key: 'enhancement', label: 'Enhancement', varName: '--accent' },
    { key: 'idea', label: 'Idea', varName: '--idea' }
  ];
  var CARDS = [];
  var state = {
    q: '',
    types: { bug: true, enhancement: true, idea: true },
    collapsed: { Done: true, Defer: true }
  };
  try {
    var savedCollapsed = localStorage.getItem('jctsh-kanban-collapsed-v2');
    if (savedCollapsed) {
      var parsed = JSON.parse(savedCollapsed);
      for (var k in parsed) state.collapsed[k] = parsed[k];
    }
    var savedTypes = localStorage.getItem('jctsh-kanban-types');
    if (savedTypes) state.types = JSON.parse(savedTypes);
  } catch (e) {}
  function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function inline(s) {
    return escapeHtml(s)
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`(.+?)`/g, '<code>$1</code>');
  }
  function mdToHtml(md) {
    var paras = md.split(/\n\n+/);
    return paras.map(function (p) {
      if (/^- /m.test(p)) {
        var items = p.split(/\n/).filter(Boolean).map(function (li) {
          return '<li>' + inline(li.replace(/^- /, '')) + '</li>';
        }).join('');
        return '<ul>' + items + '</ul>';
      }
      return '<p>' + inline(p) + '</p>';
    }).join('');
  }
  var flagLabels = { blocked: 'Blocked' };
  function cardMatches(card) {
    if (!state.types[card.type]) return false;
    if (!state.q) return true;
    var hay = (card.id + ' ' + card.title + ' ' + card.tag + ' ' + card.notes).toLowerCase();
    return hay.indexOf(state.q) !== -1;
  }
  function renderChips() {
    var el = document.getElementById('typeChips');
    el.innerHTML = TYPES.map(function (t) {
      var pressed = state.types[t.key];
      return '<button class="chip" data-type="' + t.key + '" aria-pressed="' + pressed + '" style="--dot:var(' + t.varName + ')">' +
        '<span class="dot"></span>' + t.label + '</button>';
    }).join('');
    el.querySelectorAll('.chip').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var k = btn.getAttribute('data-type');
        state.types[k] = !state.types[k];
        try { localStorage.setItem('jctsh-kanban-types', JSON.stringify(state.types)); } catch (e) {}
        render();
      });
    });
  }
  function cardHtml(card) {
    var flags = '';
    if (card.flag && flagLabels[card.flag]) {
      flags += '<span class="flag" data-flag="' + card.flag + '">' + flagLabels[card.flag] + '</span>';
    }
    return (
      '<details class="card" data-type="' + card.type + '">' +
        '<summary>' +
          '<span class="cid">CARD-' + card.id + '</span>' +
          '<span class="ctype">' + card.type + '</span>' +
          '<svg class="chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 6 15 12 9 18"/></svg>' +
          '<span class="ctag">[' + escapeHtml(card.tag) + ']</span>' +
          '<span class="ctitle">' + escapeHtml(card.title) + '</span>' +
          (flags ? '<span class="cmeta">' + flags + '</span>' : '') +
        '</summary>' +
        '<div class="card__detail">' + mdToHtml(card.notes) + '</div>' +
      '</details>'
    );
  }
  function allTypesOn() {
    return state.types.bug && state.types.enhancement && state.types.idea;
  }
  function render() {
    var visible = CARDS.filter(cardMatches);
    var board = document.getElementById('board');
    board.innerHTML = COLUMNS.map(function (col) {
      var cards = visible.filter(function (c) { return c.column === col.key; });
      var total = CARDS.filter(function (c) { return c.column === col.key; }).length;
      var collapsed = !!state.collapsed[col.key];
      var body = cards.length
        ? cards.map(cardHtml).join('')
        : '<div class="column__empty">' + (total === 0 ? 'No cards here right now.' : 'No matches in this view.') + '</div>';
      return (
        '<section class="column" data-col="' + col.key + '" data-collapsed="' + collapsed + '">' +
          '<button class="column__head" data-toggle="' + col.key + '">' +
            '<span class="name">' + col.key + '</span>' +
            '<span class="colcount">' + (state.q || !allTypesOn() ? cards.length + '/' + total : total) + '</span>' +
          '</button>' +
          '<div class="column__desc">' + col.desc + '</div>' +
          '<div class="column__body">' + body + '</div>' +
        '</section>'
      );
    }).join('');
    board.querySelectorAll('[data-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var k = btn.getAttribute('data-toggle');
        state.collapsed[k] = !state.collapsed[k];
        try { localStorage.setItem('jctsh-kanban-collapsed-v2', JSON.stringify(state.collapsed)); } catch (e) {}
        render();
      });
    });
    document.getElementById('metaCount').textContent = CARDS.length;
  }
  function load() {
    fetch('/kanban/data').then(function (r) { return r.json(); }).then(function (data) {
      CARDS = data.cards;
      document.getElementById('metaUpdated').textContent = data.updated;
      renderChips();
      render();
    }).catch(function (err) {
      document.getElementById('board').innerHTML = '<div class="noresults">Failed to load kanban-board.md: ' + err + '</div>';
    });
  }
  var qInput = document.getElementById('q');
  qInput.addEventListener('input', function () {
    state.q = qInput.value.trim().toLowerCase();
    render();
  });
  load();
  setInterval(load, 30000);
})();
</script>
</body>
</html>"""

_KANBAN_HTML_BYTES = _KANBAN_TEMPLATE.encode("utf-8")


_PRESENCE_DETECTED_RE = re.compile(
    r"Presence detected \(distance: (.+?), still: (ON|OFF), moving: (ON|OFF)\)"
)


def _collapse_for_display(entries):
    """Apply display-time collapsing rules. Raw _entries are never modified."""
    result = []
    i = 0
    while i < len(entries):
        e = entries[i]
        has_next = i + 1 < len(entries)

        # Rule 1: System "...online..." + MQTT "MQTT connected" from same component
        if (e["category"] == "System" and " online" in e["message"] and has_next):
            nxt = entries[i + 1]
            if (nxt["component"] == e["component"] and
                    nxt["category"] == "MQTT" and
                    nxt["message"] == "MQTT connected"):
                details = e["message"].split(" - ", 1)[1] if " - " in e["message"] else e["message"]
                merged = dict(e)
                merged["message"] = f"Online — {details}, MQTT connected"
                result.append(merged)
                i += 2
                continue

        # Rule 2: Presence detected + Presence cleared from same component
        pm = _PRESENCE_DETECTED_RE.match(e["message"]) if e["category"] == "Sensor" else None
        if pm and has_next:
            nxt = entries[i + 1]
            if (nxt["component"] == e["component"] and
                    nxt["category"] == "Sensor" and
                    nxt["message"] == "Presence cleared - timeout elapsed"):
                dist     = pm.group(1)
                still_on = pm.group(2) == "ON"
                moving_on = pm.group(3) == "ON"
                start_hms = e["ts"][11:19]
                end_hms   = nxt["ts"][11:19]
                try:
                    t0  = datetime.strptime(e["ts"][:19],   "%Y-%m-%d %H:%M:%S")
                    t1  = datetime.strptime(nxt["ts"][:19], "%Y-%m-%d %H:%M:%S")
                    dur = f"({int((t1 - t0).total_seconds())}s)"
                except ValueError:
                    dur = ""
                state_parts = (["still"] if still_on else []) + (["moving"] if moving_on else [])
                detail = ", ".join([f"at {dist}"] + state_parts)
                merged = dict(e)
                merged["message"] = f"Presence {start_hms}–{end_hms} {dur} — {detail}"
                result.append(merged)
                i += 2
                continue

        # Rule 3: Salt daily doubles — same day, same %, collapse to one line
        sm = (re.match(r"Salt: (\d+)% \((\d+\.\d+) cm\)", e["message"])
              if e["component"] == "salt-sensor" and e["category"] == "Sensor" else None)
        if sm and has_next:
            nxt  = entries[i + 1]
            nxt_m = re.match(r"Salt: (\d+)% \((\d+\.\d+) cm\)", nxt.get("message", ""))
            if (nxt_m and
                    nxt["component"] == "salt-sensor" and
                    nxt["category"] == "Sensor" and
                    e["ts"][:10] == nxt["ts"][:10] and
                    sm.group(1) == nxt_m.group(1)):
                merged = dict(e)
                merged["message"] = f"Salt: {sm.group(1)}% full ({sm.group(2)}→{nxt_m.group(2)} cm)"
                result.append(merged)
                i += 2
                continue

        # Rule 4: Simultaneous MQTT disconnects (within 2 s) — group into one row
        if e["category"] == "MQTT" and e["message"] == "MQTT disconnected":
            group_end = i + 1
            try:
                t0 = datetime.strptime(e["ts"][:19], "%Y-%m-%d %H:%M:%S")
                while group_end < len(entries):
                    nxt = entries[group_end]
                    if nxt["category"] != "MQTT" or nxt["message"] != "MQTT disconnected":
                        break
                    t1 = datetime.strptime(nxt["ts"][:19], "%Y-%m-%d %H:%M:%S")
                    if abs((t1 - t0).total_seconds()) > 2:
                        break
                    group_end += 1
            except ValueError:
                pass
            if group_end > i + 1:
                merged = dict(e)
                merged["component"] = ", ".join(entries[j]["component"] for j in range(i, group_end))
                result.append(merged)
                i = group_end
                continue

        result.append(e)
        i += 1
    return result


def _snapshot():
    with _lock:
        entries = list(_entries)
        if _pending:
            entries.append(dict(_pending))
        for group in _hb_groups.values():
            entries.append({k: v for k, v in group.items() if k != "_state_key"})
        shown = {c.strip() for e in entries for c in e["component"].split(",")}
        for comp, last in _last_seen.items():
            if comp not in shown:
                entries.append({k: v for k, v in last.items() if k != "_state_key"})
    entries.sort(key=lambda e: e["ts"])
    return _collapse_for_display(entries)


def _entry_color(e):
    cat = e["category"]
    if cat == "Alert":
        return "#ff4444" if "CRITICAL" in e["message"] else "#ffaa00"
    return _CATEGORY_COLORS.get(cat, "#e0e0e0")


def _build_html(snapshot):
    rows = []
    components = set()
    for e in snapshot:
        for c_part in e["component"].split(","):
            components.add(c_part.strip())
        color = _entry_color(e)
        count = e["count"]
        if count > 1 and "first_ts" in e:
            first_hm  = e["first_ts"][11:16]
            last_hm   = e["ts"][11:16]
            if e["message"].startswith("Heartbeat - "):
                details  = e["message"][len("Heartbeat - "):]
                msg_html = escape(f"Heartbeat ×{count} [{first_hm}–{last_hm}] — {details}")
            else:
                msg_html = escape(f"{e['message']}  ×{count} [{first_hm}–{last_hm}]")
            count_tag = ""
        else:
            msg_html  = escape(e["message"])
            count_tag = (f' <span style="color:{color}">×{count}</span>'
                         if count > 1 else "")
        rows.append(
            f'      <tr data-c="{escape(e["component"])}" data-k="{escape(e["category"])}">'
            f'<td style="color:#b0b0b0;white-space:nowrap">{escape(e["ts"])}</td>'
            f'<td style="color:#b0b0b0">{escape(e["component"])}</td>'
            f'<td style="color:{color}">{escape(e["category"])}</td>'
            f'<td style="color:{color}">{msg_html}{count_tag}</td>'
            f'</tr>'
        )
    comp_opts = "".join(f'<option>{escape(c)}</option>' for c in sorted(components))
    html = _HTML_TEMPLATE
    html = html.replace("%%ROWS%%",  "\n".join(rows))
    html = html.replace("%%COMP%%",  comp_opts)
    html = html.replace("%%MAX%%",   str(MAX_ENTRIES))
    html = html.replace("%%LOG%%",   escape(LOG_FILE))
    return html


class _Handler(BaseHTTPRequestHandler):
    def _check_auth(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            return False
        try:
            user, _, pw = base64.b64decode(auth[6:]).decode("utf-8").partition(":")
        except Exception:
            return False
        return user == DASHBOARD_USER and pw == DASHBOARD_PASS

    def _send_auth_challenge(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="JCTsh"')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if not self._check_auth():
            self._send_auth_challenge()
            return
        if self.path == "/log":
            try:
                with open(LOG_FILE, "rb") as f:
                    body = f.read()
            except OSError:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/data":
            snap = _snapshot()
            comps = set()
            for _e in snap:
                for _c in _e["component"].split(","):
                    comps.add(_c.strip())
            body = json.dumps({
                "entries":    snap,
                "components": sorted(comps),
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/status":
            body = _build_status_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/kanban":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(_KANBAN_HTML_BYTES)))
            self.end_headers()
            self.wfile.write(_KANBAN_HTML_BYTES)
            return
        if self.path == "/kanban/data":
            cards = _load_kanban_cards()
            if cards is None:
                self.send_response(503)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"Could not fetch {KANBAN_RAW_URL}".encode("utf-8"))
                return
            fetched = datetime.now(_TZ).strftime("%Y-%m-%d %H:%M %Z")
            body = json.dumps({"cards": cards, "updated": fetched}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path != "/":
            self.send_response(404)
            self.end_headers()
            return
        body = _build_html(_snapshot()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # suppress HTTP access log noise


# ── Heartbeat thread ──────────────────────────────────────────────────────────
def _heartbeat_thread():
    time.sleep(HEARTBEAT_INTERVAL)
    while True:
        if _mqtt_client and _mqtt_client.is_connected():
            with _lock:
                active = sorted({e["component"] for e in _entries
                                 if e["component"] != "jctsh-core"})
            if active:
                msg = "Watchdog: alive. Active: " + ", ".join(active) + "."
            else:
                msg = "Watchdog: alive. No component activity."
            payload = json.dumps({
                "component": "jctsh-core",
                "category":  "System",
                "message":   msg,
            })
            _mqtt_client.publish(HEARTBEAT_TOPIC, payload)
        time.sleep(HEARTBEAT_INTERVAL)


# ── MQTT thread ───────────────────────────────────────────────────────────────
def _mqtt_thread():
    global _mqtt_client
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        client = mqtt.Client()  # paho-mqtt < 2.0
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    _mqtt_client = client
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            client.loop_forever()
        except Exception as exc:
            print(f"[MQTT] Error: {exc} — retrying in 10s")
            time.sleep(10)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[JCTsh] Log server starting — MQTT {MQTT_BROKER}:{MQTT_PORT}, HTTP :{HTTP_PORT}")
    with _lock:
        _load_state()
    print(f"[JCTsh] Restored {len(_entries)} entries, {len(_last_seen)} known components from {STATE_FILE}")
    t = threading.Thread(target=_mqtt_thread, daemon=True)
    t.start()
    threading.Thread(target=_heartbeat_thread, daemon=True).start()
    httpd = ThreadingHTTPServer(("", HTTP_PORT), _Handler)
    print("[JCTsh] Dashboard at http://JCTsh.local/")
    signal.signal(signal.SIGTERM,
                  lambda *_: threading.Thread(target=httpd.shutdown, daemon=True).start())
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        with _lock:
            _flush_pending()
            _flush_all_hb_groups()
            _save_state()
        print("\n[JCTsh] Stopped.")
