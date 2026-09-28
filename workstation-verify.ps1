<#
CARD-0360: verify the workstation's actual state against what WORKSTATION-SETUP.md
documents, instead of trusting memory or the doc alone. Verify-only, deliberately --
matches the "revisit the pin per device, at that device's next real flash" call already
made on CARD-0357: this script reports drift, it never installs or changes anything.

Scope is the state CARD-0357 found could actually drift unnoticed: the Python versions
available via the `py` launcher, and which ESPHome pip version the live `esphome` command
actually resolves to versus the pin WORKSTATION-SETUP.md documents (parsed from that file
directly, so the pin has exactly one source of truth -- this script never hardcodes its
own copy). The SSH-client and C:\Shared gotchas in WORKSTATION-SETUP.md are situational
usage rules, not machine-checkable state, so they're intentionally out of scope here --
same "not covered" discipline WORKSTATION-SETUP.md itself uses for Git/gh/Claude Code/ESP-IDF.

Run from native PowerShell (never Git Bash -- a .ps1 can't run there anyway, which
incidentally double-checks that gotcha too).
#>

$ErrorActionPreference = 'Continue'
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$setupDoc = Join-Path $repoRoot 'WORKSTATION-SETUP.md'
$problems = @()

Write-Host "=== JCTsh workstation verify (CARD-0360) ===" -ForegroundColor Cyan

# --- Python versions available via the py launcher -----------------------
Write-Host "`n-- Python (py launcher) --"
$pyList = & py -0p 2>&1
if ($LASTEXITCODE -ne 0 -or -not $pyList) {
    $problems += "`py` launcher not found or returned nothing -- can't confirm any Python version."
    Write-Host "  FAIL: py launcher not available" -ForegroundColor Red
} else {
    $has311 = $pyList -match '-V:3\.11'
    $has312plus = $pyList | Where-Object { $_ -match '-V:3\.(1[2-9]|[2-9][0-9])' }
    if ($has311) { Write-Host "  OK: Python 3.11.x present" -ForegroundColor Green }
    else { $problems += "Python 3.11.x not found via `py -0p` (WORKSTATION-SETUP.md's long-standing base install)."; Write-Host "  WARN: Python 3.11.x not found" -ForegroundColor Yellow }
    if ($has312plus) { Write-Host "  OK: Python 3.12+ present (required by ESPHome 2026.7.0+)" -ForegroundColor Green }
    else { $problems += "No Python 3.12+ found via `py -0p` -- ESPHome 2026.7.0+ cannot be installed until this exists (CARD-0357)."; Write-Host "  FAIL: no Python 3.12+ found" -ForegroundColor Red }
}

# --- ESPHome: which interpreter backs it, and its version ----------------
Write-Host "`n-- ESPHome --"
$esphomeCmd = Get-Command esphome -ErrorAction SilentlyContinue
if (-not $esphomeCmd) {
    $problems += "No `esphome` command found on PATH."
    Write-Host "  FAIL: esphome not found on PATH" -ForegroundColor Red
} else {
    Write-Host "  esphome resolves to: $($esphomeCmd.Source)"
    $verOutput = & esphome version 2>&1
    $installedVersion = ($verOutput -join ' ') -replace '.*?(\d{4}\.\d+\.\d+).*', '$1'

    # Parse the documented pin straight from WORKSTATION-SETUP.md -- single source of
    # truth; this script never carries its own hardcoded copy of the pin.
    $pinnedVersion = $null
    if (Test-Path $setupDoc) {
        $docText = Get-Content $setupDoc -Raw
        if ($docText -match 'pinned at `(\d{4}\.\d+\.\d+)`') {
            $pinnedVersion = $Matches[1]
        }
    }

    if (-not $pinnedVersion) {
        $problems += "Could not parse a pinned version out of WORKSTATION-SETUP.md -- doc format may have changed."
        Write-Host "  WARN: could not parse documented pin from WORKSTATION-SETUP.md" -ForegroundColor Yellow
    } elseif ($installedVersion -eq $pinnedVersion) {
        Write-Host "  OK: installed esphome ($installedVersion) matches documented pin ($pinnedVersion)" -ForegroundColor Green
    } else {
        $problems += "esphome version mismatch: installed=$installedVersion, documented pin=$pinnedVersion. Either the workstation drifted or WORKSTATION-SETUP.md is stale -- reconcile deliberately, don't just silence this."
        Write-Host "  FAIL: installed=$installedVersion vs documented pin=$pinnedVersion" -ForegroundColor Red
    }
}

# --- Path length (proxy for the MAX_PATH / aioesphomeapi DLL gotcha) -----
Write-Host "`n-- Working directory path length --"
$cwd = (Get-Location).Path
$len = $cwd.Length
Write-Host "  $cwd ($len chars)"
if ($len -gt 180) {
    $problems += "Current directory is $len characters -- ESPHome's .esphome build cache nests well past this and can hit Windows's 260-char MAX_PATH (CARD-0357 hit this at exactly 255). Compile/flash from a short path (the existing C:\esphome\<name>\ convention), not here."
    Write-Host "  WARN: path is long enough to risk MAX_PATH during a compile" -ForegroundColor Yellow
} else {
    Write-Host "  OK: comfortably under MAX_PATH risk" -ForegroundColor Green
}

# --- Summary ---------------------------------------------------------------
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
if ($problems.Count -eq 0) {
    Write-Host "All checks passed -- workstation matches WORKSTATION-SETUP.md." -ForegroundColor Green
    exit 0
} else {
    Write-Host "$($problems.Count) issue(s) found:" -ForegroundColor Yellow
    foreach ($p in $problems) { Write-Host "  - $p" -ForegroundColor Yellow }
    Write-Host "`nSee WORKSTATION-SETUP.md for context on each of these." -ForegroundColor Yellow
    exit 1
}
