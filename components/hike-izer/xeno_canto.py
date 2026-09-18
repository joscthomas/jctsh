#!/usr/bin/env python
"""
CARD-0174: reference bird-call lookup via the Xeno-canto API. Deployed copy
from components/hike-izer/ into components/hike-izer-orchestrator/ at build
time (Dockerfile), same pattern as build_hike_map.py/build_hike_chart.py --
both templating.py (in-process import) and build_wildlife_index.py (its own
subprocess, see generation.py's BUILD_WILDLIFE_SCRIPT call) import this
directly.

Looks up one representative recording per species, keyed by scientific name
(more precise/stable than English name, which can mismatch BirdNET's own
common-name spelling), and caches results to a shared JSON file so the same
species looked up on one page (a per-hike page via templating.py) is already
cached for the other (wildlife.html via build_wildlife_index.py) -- these
run as separate OS processes within the same generation.py run, so the
cache is what makes that sharing work, not shared Python state. Cache is
re-read and re-written on every call rather than held open across calls --
call volume is a handful of species per page, not a hot path, so the extra
I/O is cheap and this stays correct across processes without needing any
locking.

Server-side only: the API key never reaches the browser. The rendered page
embeds Xeno-canto's own public audio-file URL directly (safe to be public,
same as any other CDN link) -- never the key itself, which stays in this
process's environment (XENO_CANTO_API_KEY, see generation.py's _env()-style
handling) and is never written into generated HTML.

Standard library only -- matches every other component in this pipeline.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://xeno-canto.org/api/3/recordings"
CACHE_PATH = "/srv/hike-izer-private/xeno_canto_cache.json"

# Prefer an actual song/call over incidental noise (alarm calls, flight
# calls, begging calls, etc. are real recordings but less useful as a
# "what does this species normally sound like" reference); prefer
# better-quality recordings when more than one type match exists. This is
# a best-effort ranking over whatever a 10-recording sample returns, not a
# hard filter -- any identified recording is better than none.
_TYPE_PREFERENCE = ("song", "call")
_QUALITY_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}


def _pick_best(recordings):
    def rank(r):
        rtype = (r.get("type") or "").lower()
        type_rank = next(
            (i for i, pref in enumerate(_TYPE_PREFERENCE) if pref in rtype),
            len(_TYPE_PREFERENCE),
        )
        return (type_rank, _QUALITY_RANK.get(r.get("q"), 5))
    return min(recordings, key=rank)


def _query(scientific_name, api_key):
    genus, _, species = scientific_name.partition(" ")
    query = urllib.parse.quote(f"gen:{genus} sp:{species}")
    url = f"{API_URL}?query={query}&key={urllib.parse.quote(api_key)}&per_page=10"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None

    recordings = data.get("recordings") or []
    if not recordings:
        return None

    best = _pick_best(recordings)
    if not best.get("file"):
        return None
    return {
        "audio_url": best["file"],
        "recordist": best.get("rec") or "unknown",
        "license_url": best.get("lic") or "",
        "xc_url": best.get("url") or "",
    }


def load_cache(path=CACHE_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache, path=CACHE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def lookup(scientific_name, api_key, cache_path=CACHE_PATH):
    """Returns a dict {audio_url, recordist, license_url, xc_url}, or None
    if there's no key configured yet, no recording was found, or the API
    call failed -- caller omits the speaker icon entirely in every None
    case, same "don't fabricate" convention as the rest of this pipeline.
    A failed lookup is cached as None too (not retried every call) --
    genuinely rare species with no Xeno-canto coverage shouldn't cost a
    fresh API round-trip on every single page that mentions them."""
    if not api_key:
        return None

    cache = load_cache(cache_path)
    if scientific_name in cache:
        return cache[scientific_name]

    result = _query(scientific_name, api_key)
    cache[scientific_name] = result
    save_cache(cache, cache_path)
    return result


def render_button_html(audio, esc, species_name=""):
    """Speaker-icon button for one species, or '' if no reference call was
    found. `esc` is the caller's own HTML-escaping function -- both
    templating.py and build_wildlife_index.py already have one, no need for
    this module to take on that dependency itself. Shared here (not
    duplicated in each template) so both pages render byte-identical markup
    -- CARD-0176 hit real drift from exactly this kind of duplication
    between the two templates.

    CARD-0278: no longer emits an inline <audio> sibling -- the audio URL
    and species name are carried as data-audio-url/data-species attributes
    instead, read by the shared player-widget script below (also CARD-0278:
    both pages now route into the same persistent widget, not one shared
    button feeding two different playback behaviors as originally split --
    Joseph's call, once he saw wildlife.html's simpler per-click toggle next
    to the hike-summary page's real widget and wanted the two consistent)."""
    if not audio:
        return ""
    title = (
        f"Reference call — recording by {audio['recordist']}, Xeno-canto "
        f"(CC BY-NC-SA) — {audio['xc_url']}"
    )
    return (
        f' <button class="audio-btn" type="button" title="{esc(title)}" '
        f'data-audio-url="{esc(audio["audio_url"])}" data-species="{esc(species_name)}"'
        f'>&#128266;</button>'
    )


# CARD-0278: persistent species-audio player widget -- shared markup/CSS/JS
# so wildlife.html and the hike-summary page render and behave identically,
# same drift-avoidance reasoning as render_button_html() above. Each page
# still owns its own design-token values (--surface/--accent/etc. differ
# slightly in hex between the two <style> blocks); only the rule *shapes*
# and the widget's HTML/JS are shared here.

PLAYER_WIDGET_CSS = """
  .species-player {
    display: flex; align-items: center; gap: 0.6rem; margin-top: 0.75rem;
    padding: 0.6rem 0.9rem; background: var(--surface); border: 1px solid var(--line);
    border-radius: var(--radius); box-shadow: var(--shadow);
  }
  /* Real bug found live (CARD-0278): an unqualified `.species-player {
     display: flex }` rule beats the browser's own `[hidden] { display:
     none }` UA-stylesheet rule (author styles win over user-agent styles
     at equal specificity), so the widget rendered visible from page load
     regardless of the `hidden` attribute. This higher-specificity rule
     re-asserts hidden explicitly rather than relying on the attribute
     alone. */
  .species-player[hidden] { display: none; }
  .species-player-toggle {
    background: var(--accent); color: var(--accent-ink); border: none; border-radius: 50%;
    width: 2rem; height: 2rem; flex: none; cursor: pointer; font-size: 0.8em;
    display: flex; align-items: center; justify-content: center;
  }
  .species-player-toggle:hover { opacity: 0.85; }
  .species-player-label { font-weight: 600; }
"""


def render_player_widget_html():
    """The widget's own markup -- append once per page, right after
    whichever table's audio-btn clicks should feed it. Starts hidden;
    render_player_widget_script()'s click-delegation reveals it on first
    use."""
    return (
        '<div class="species-player" id="species-player" hidden>'
        '<button type="button" class="species-player-toggle" id="species-player-toggle" aria-label="Play/pause">&#9654;</button>'
        '<span class="species-player-label" id="species-player-label"></span>'
        '<audio id="species-player-audio" preload="none"></audio>'
        '</div>'
    )


def render_player_widget_script(table_id):
    """Click-delegation on `table_id` (the page's own species table) plus
    the widget's play/pause/scroll-into-view wiring. `table_id` is the only
    thing that ever differs between the two pages ("birdnet-table" vs
    "wildlife-table"), so it's the one parameter -- everything else about
    how the widget behaves is identical on both pages by construction, not
    just by convention."""
    return f"""<script>
(function () {{
  var audioTable = document.getElementById("{table_id}");
  var player = document.getElementById("species-player");
  if (!audioTable || !player) return;
  var playerAudio = document.getElementById("species-player-audio");
  var playerLabel = document.getElementById("species-player-label");
  var playerToggle = document.getElementById("species-player-toggle");
  // Compared against the raw data-audio-url on each click instead of
  // reading playerAudio.src back -- the browser normalizes .src to an
  // absolute URL once set, which can legitimately differ in formatting
  // from the original attribute string even for the same resource,
  // causing a spurious reload/restart on re-clicking the same species.
  var currentUrl = null;

  function setToggleIcon() {{
    playerToggle.innerHTML = playerAudio.paused ? "&#9654;" : "&#10074;&#10074;";
  }}
  playerAudio.addEventListener("play", setToggleIcon);
  playerAudio.addEventListener("pause", setToggleIcon);
  playerAudio.addEventListener("ended", setToggleIcon);

  playerToggle.addEventListener("click", function () {{
    if (playerAudio.paused) {{ playerAudio.play().catch(function () {{}}); }} else {{ playerAudio.pause(); }}
  }});

  audioTable.addEventListener("click", function (e) {{
    if (!e.target.classList || !e.target.classList.contains("audio-btn")) return;
    var url = e.target.dataset.audioUrl;
    if (!url) return;
    playerLabel.textContent = e.target.dataset.species || "";
    player.hidden = false;
    player.scrollIntoView({{behavior: "smooth", block: "center"}});
    if (currentUrl !== url) {{
      currentUrl = url;
      playerAudio.src = url;
    }}
    // play() is a Promise -- a network/decode failure (bad URL, blocked
    // request) rejects it silently otherwise, leaving the toggle icon
    // stuck on play with no feedback. Caught here, not left unhandled.
    playerAudio.play().catch(function (err) {{
      console.error("species-player: playback failed", err);
    }});
  }});
}})();
</script>"""
