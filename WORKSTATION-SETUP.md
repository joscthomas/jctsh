# JCTsh Workstation Setup

Reference for what this repo's development/flashing workstation (Joseph's Windows machine)
needs installed and configured, and the tool-specific gotchas that aren't obvious from error
messages alone. Single-operator machine, not a fleet of contributor machines — this is the
canonical, actively-read home for these facts (CARD-0354); several were previously recorded
only in archived card history (`card-archive.md`, on-demand-only reading) or scattered across
individual component `flashing.md` files, which is how the Python-version gap below went
unnoticed for ~5 months. For the Pi/M8's own software, see `SOFTWARE-ENVIRONMENT.md`; for the
physical smart-home devices, see `ENVIRONMENT.md`.

## Python

| Version | Purpose |
|---|---|
| 3.11.x (`C:\Users\jcthomas\AppData\Local\Programs\Python\Python311\`) | Long-standing base install — general scripting, most tooling |
| 3.12.10 (installed 2026-09-27, CARD-0354, via `winget install Python.Python.3.12`) | Required by ESPHome 2026.7.0+ (see below) — installed alongside 3.11, not replacing it |

Both are reachable via the `py` launcher: `py -3.11`, `py -3.12` (bare `py`/`python` defaults
to whichever was installed/registered first — check with `py -0` before assuming).

## ESPHome (firmware build/flash tooling)

**Currently pinned at `2026.4.5`** (`pip install esphome==2026.4.5`) — every component's
`flashing.md`/build-instructions doc should say this. The pin exists because `2026.9.0`
(current latest as of 2026-09-27) was believed to "break the compile" when first tried
around CARD-0333/CARD-0335 (2026-09-24/25) — **root-caused 2026-09-27/28, CARD-0354, and it
was never actually a YAML/config incompatibility:**

1. **ESPHome 2026.7.0 and later require Python ≥3.12** (`Requires-Python >=3.12.0,<3.15` on
   PyPI) — this workstation only had 3.11 at the time, so `pip install esphome==2026.9.0`
   couldn't even resolve a matching distribution. Fixed by installing 3.12 above.
2. **ESP-IDF's own toolchain installer refuses to run under Git Bash/MSYS** — `ERROR:
   MSys/Mingw is not supported`. This is real and applies to *any* ESPHome version doing a
   fresh ESP-IDF framework install, not just 2026.9.0 — **always compile/flash from native
   PowerShell or cmd, never Git Bash**, even though Git Bash is this repo's normal shell for
   everything else (SSH to the Pi/M8, git, etc. — see below).
3. **Windows `MAX_PATH` (260 chars) can break a DLL import inside `aioesphomeapi`** (a
   dependency ESPHome's `time:` component pulls in) with `ImportError: DLL load failed ...
   The filename or extension is too long` if the venv/install path is too deeply nested —
   confirmed live at exactly 255 characters. **This is the actual reason for the
   `C:\esphome\<name>\` flash-directory convention** (short, root-level, no spaces) already
   used for real device flashes — previously followed without the underlying reason being
   written down anywhere live.

**Confirmed 2026-09-27/28 (CARD-0354):** with Python 3.12 + native PowerShell + a
short working path, `garage-radar.yaml` compiles clean on ESPHome 2026.9.0 (exit 0, real
firmware binaries generated) — strong evidence the 5-month-old pin was never a real ESPHome
regression. **Not yet re-verified for the other 5 devices**, and the live fleet's actual pin
has deliberately **not** been bumped yet (CARD-0354's own scope decision: fix + prove the
compile, don't force a fleet-wide reflash in the same pass). Per Joseph's direction
(2026-09-28): the pin gets revisited **per device, at that device's next real flash** —
whoever next runs `esphome run <device>.yaml` should try the current latest ESPHome first
now that the workstation is actually capable of running it, rather than reflexively reusing
`2026.4.5`.

**Other real gotchas, carried forward from archived card history:**
- **Stale `.esphome` build-cache directories can cause `Access is denied` / permission
  errors** when ESPHome tries to clean them after a version or environment change (e.g. a
  Windows user-profile rename left one such cache pointing at a dead path). `.esphome/` is
  always gitignored and fully regenerable — if a compile fails while trying to *clean* the
  build directory (not while actually building), delete `.esphome/` under that component and
  retry before assuming anything else is wrong.
- **After flashing, wait past ~60s before touching the device** — ESP32 OTA has automatic
  rollback: if the new image reboots before it's marked valid, the bootloader silently
  reverts to the previous firmware, and every observation in that window is actually the
  *old* firmware running.

## SSH (Pi / M8 access)

**Use Git Bash's `ssh`, not PowerShell's native OpenSSH** — PowerShell's OpenSSH client
rejects `~/.ssh/id_ed25519` on ACL grounds where Git Bash's `ssh` (and the `Bash` tool) work
fine (found live during CARD-0328). If a `ssh`/`scp` command needs a fresh host-key prompt
answered non-interactively, use `-o StrictHostKeyChecking=accept-new` after comparing the
fingerprint against the already-trusted key — a plain shell command can't answer an
interactive host-key prompt.

## Filesystem

**`C:\Shared` is a junction, not a real directory** — the `Read`/`Write`/`Glob` tools refuse
to operate on it; PowerShell reads/writes it fine. Relevant any time a task touches something
under that path (e.g. RoboForm exports, per `digital-identity-protection-checklist.md`).

## Not covered here (CARD-0344's explicit scope boundary, unchanged)

Git, `gh`, Claude Code, and ESP-IDF's own toolchain versioning are deliberately not tracked
by any maintenance check or this doc's own currency — only ESPHome, because it's the one tool
that has actually broken a build. Revisit that boundary if a second real gap in one of those
shows up, not preemptively.

**Related:** CARD-0354 (root-caused the ESPHome pin, wrote this doc), CARD-0333/CARD-0335
(where the pin was first established), CARD-0344 (the update-check scope boundary this doc's
last section restates), CARD-0328 (found the SSH ACL gotcha).
