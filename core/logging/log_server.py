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
MAX_ENTRIES = 200

# ── Shared state ─────────────────────────────────────────────────────────────
_lock        = threading.Lock()
_entries     = deque(maxlen=MAX_ENTRIES)   # flushed, displayable entries
_pending     = None                         # current non-heartbeat repeat group (not yet flushed)
_hb_groups   = {}                           # component -> active heartbeat collapse group
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
def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        print(f"[MQTT] Connected to {MQTT_BROKER}. Subscribed to {MQTT_TOPIC}")
    else:
        print(f"[MQTT] Connection failed rc={rc}")


def _on_message(client, userdata, msg):
    global _pending
    try:
        data      = json.loads(msg.payload.decode("utf-8"))
        component = str(data.get("component", "unknown"))
        category  = str(data.get("category",  "System"))
        message   = str(data.get("message",   ""))
        ts        = datetime.now(_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")

        with _lock:
            if message.startswith("Heartbeat - ") or message.startswith("Watchdog: "):
                state_key = _heartbeat_state_key(message)
                existing  = _hb_groups.get(component)
                if existing and existing["_state_key"] == state_key:
                    # Same state: extend the group with latest values
                    existing["ts"]      = ts
                    existing["message"] = message
                    existing["count"]  += 1
                else:
                    # State changed or new component: flush old group, start fresh
                    if existing:
                        _flush_hb_group(component)
                    _hb_groups[component] = {
                        "ts": ts, "first_ts": ts,
                        "component": component, "category": category,
                        "message": message, "count": 1,
                        "_state_key": state_key,
                    }
            else:
                # Non-heartbeat: flush any open heartbeat group for this component first.
                # Sensor-category messages are health checks co-scheduled with the heartbeat
                # interval — don't let them break up heartbeat collapsing.
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
                        "category": category, "message": message, "count": 1
                    }
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
    body { background:#1a1a1a; color:#e0e0e0; font-family:monospace;
           font-size:13px; margin:20px; }
    h2   { color:#00cc99; margin-bottom:4px; }
    .sub { color:#555; font-size:11px; margin-bottom:16px; }
    .controls { margin-bottom:12px; }
    .controls label  { color:#888; margin-right:4px; }
    .controls select { background:#111; color:#e0e0e0; border:1px solid #333;
                       padding:3px 8px; font-family:monospace; margin-right:16px;
                       cursor:pointer; }
    table { border-collapse:collapse; width:100%; }
    th    { color:#555; font-size:11px; text-align:left; padding:4px 8px;
            border-bottom:1px solid #2a2a2a; }
    td    { padding:3px 8px; vertical-align:top; cursor:text; }
    tr:hover td { background:#1f1f1f; }
    .hidden { display:none; }
  </style>
</head>
<body>
  <h2>JCTsh Log Dashboard</h2>
  <p class="sub">Updates every 5s &nbsp;|&nbsp; Last %%MAX%% entries &nbsp;|&nbsp; <a href="/log" target="_blank" style="color:#555">%%LOG%%</a> &nbsp;|&nbsp; <a href="/status" style="color:#555">Device status</a></p>
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
  <table id="log">
    <thead>
      <tr><th>Timestamp</th><th>Component</th><th>Category</th><th>Message</th></tr>
    </thead>
    <tbody>
%%ROWS%%
    </tbody>
  </table>
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
        +'<td style="color:#888;white-space:nowrap">'+_esc(e.ts)+'</td>'
        +'<td style="color:#888">'+_esc(e.component)+'</td>'
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
    function _poll() {
      fetch('/data').then(function(r){return r.json();}).then(_render).catch(function(){});
    }
    window.addEventListener('DOMContentLoaded', function() {
      var fc = localStorage.getItem('jctsh_fc') || '';
      var fk = localStorage.getItem('jctsh_fk') || '';
      if (fc) document.getElementById('fc').value = fc;
      if (fk) document.getElementById('fk').value = fk;
      f();
      setInterval(_poll, 5000);
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
    h3      { color:#555; font-size:11px; margin-top:24px; margin-bottom:8px;
              text-transform:uppercase; letter-spacing:2px; }
    .sub    { color:#555; font-size:11px; margin-bottom:16px; }
    table   { border-collapse:collapse; width:100%; margin-bottom:8px; }
    th      { color:#555; font-size:11px; text-align:left; padding:4px 8px;
              border-bottom:1px solid #2a2a2a; }
    td      { padding:3px 8px; vertical-align:top; }
    tr:hover td { background:#1f1f1f; }
    .online  { color:#00cc99; }
    .offline { color:#ff4444; }
    .unknown { color:#555; }
    .dim     { color:#555; }
    .ts      { color:#888; white-space:nowrap; }
    .msg     { color:#888; }
  </style>
</head>
<body>
  <h2>JCTsh Device Status</h2>
  <p class="sub">Auto-refreshes every 60s &nbsp;|&nbsp; Based on last %%MAX%% log entries
    &nbsp;|&nbsp; <a href="/" style="color:#555">Log dashboard</a></p>
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
            rd_cell = f'{rd_disp} <span class="dim">{escape(_ago(rec["last_reading_ts"]))}</span>'
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
            f'<td class="dim">{lm_disp}</td>'
            f'</tr>'
        )

    no_home   = "      <tr><td colspan='4' class='dim'>No always-on devices in recent log.</td></tr>"
    no_remote = "      <tr><td colspan='3' class='dim'>No mobile devices in recent log.</td></tr>"
    html = _STATUS_TEMPLATE
    html = html.replace("%%HOME_ROWS%%",   "\n".join(home_rows)   or no_home)
    html = html.replace("%%REMOTE_ROWS%%", "\n".join(remote_rows) or no_remote)
    html = html.replace("%%MAX%%", str(MAX_ENTRIES))
    return html


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
            f'<td style="color:#888;white-space:nowrap">{escape(e["ts"])}</td>'
            f'<td style="color:#888">{escape(e["component"])}</td>'
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
    t = threading.Thread(target=_mqtt_thread, daemon=True)
    t.start()
    threading.Thread(target=_heartbeat_thread, daemon=True).start()
    httpd = ThreadingHTTPServer(("", HTTP_PORT), _Handler)
    print("[JCTsh] Dashboard at http://JCTsh.local/")
    signal.signal(signal.SIGTERM, lambda *_: httpd.shutdown())
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        with _lock:
            _flush_pending()
            _flush_all_hb_groups()
        print("\n[JCTsh] Stopped.")
