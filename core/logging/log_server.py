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
  <p class="sub">Updates every 5s &nbsp;|&nbsp; Last %%MAX%% entries &nbsp;|&nbsp; <a href="/log" style="color:#555">%%LOG%%</a></p>
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
        r.classList.toggle('hidden',
          (comp && r.dataset.c !== comp) || (cat && r.dataset.k !== cat));
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


def _snapshot():
    with _lock:
        entries = list(_entries)
        if _pending:
            entries.append(dict(_pending))
        for group in _hb_groups.values():
            entries.append({k: v for k, v in group.items() if k != "_state_key"})
    entries.sort(key=lambda e: e["ts"])
    return entries


def _entry_color(e):
    cat = e["category"]
    if cat == "Alert":
        return "#ff4444" if "CRITICAL" in e["message"] else "#ffaa00"
    return _CATEGORY_COLORS.get(cat, "#e0e0e0")


def _build_html(snapshot):
    rows = []
    components = set()
    for e in snapshot:
        components.add(e["component"])
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
            body = json.dumps({
                "entries":    snap,
                "components": sorted({e["component"] for e in snap}),
            }).encode("utf-8")
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
