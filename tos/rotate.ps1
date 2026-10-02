# rotate.ps1 -- CARD-0372's registry-aware orchestrator, Step 5 skeleton only.
#
# Reads tos/credential-registry.yaml (values-free) for a single credential id and
# prints its rotation plan: holders, each one's kind (scripted/manual) and verify
# check, whether the server dual-accepts old+new. Read-only -- never touches the
# vault, never calls secret.ps1, never pushes anything to a holder. That's Step 6+
# (a real per-credential "recipe"), deliberately not built yet (Joseph, 2026-10-02:
# "build the process, do not do any live rotations").
#
# `secret.py`/`secret.ps1` is the primitive ("give me a value, safely"); this script
# is the thing that's supposed to read the registry and decide what to DO with that
# value -- see CARD-0372's "how does secret interact with the registry" note. Right
# now it only does the read/decide/print half; the "do" half per credential is
# intentionally still missing.
#
# Usage: rotate.ps1 <id> [-VerifyOnly]
#   <id>          -- dry-run is the only mode that does anything right now; this
#                    always behaves as --dry-run regardless of flags, until a real
#                    recipe exists to make -VerifyOnly mean something.

param(
    [Parameter(Position = 0, Mandatory = $true)]
    [string]$Id,

    [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$RegistryPath = 'C:\Shared\jctsh\tos\credential-registry.yaml'

function Get-EntryLines {
    param([string]$Id)
    $lines = Get-Content $RegistryPath
    $collecting = $false
    $out = @()
    $pattern = "^  - id:\s*$([regex]::Escape($Id))\s*$"
    foreach ($line in $lines) {
        if (-not $collecting -and $line -match $pattern) {
            $collecting = $true
            $out += $line
            continue
        }
        if ($collecting) {
            if ($line.Trim() -eq '') { break }
            $out += $line
        }
    }
    return $out
}

function Get-Field {
    param([string[]]$EntryLines, [string]$Field)
    foreach ($line in $EntryLines) {
        if ($line -match "^    $Field`:\s*(.+?)\s*(#.*)?$") { return $Matches[1].Trim() }
    }
    return $null
}

function Get-Holders {
    param([string[]]$EntryLines)
    $holders = @()
    $inHolders = $false
    foreach ($line in $EntryLines) {
        if ($line -match '^    holders:\s*$') { $inHolders = $true; continue }
        if ($inHolders) {
            if ($line -match '^      - \{(.*)\}\s*$') {
                $body = $Matches[1]
                $where = $null; $kind = $null; $verify = $null
                if ($body -match 'where:\s*"([^"]*)"') { $where = $Matches[1] }
                if ($body -match 'kind:\s*(\w+)') { $kind = $Matches[1] }
                if ($body -match 'verify:\s*"([^"]*)"') { $verify = $Matches[1] }
                $holders += [pscustomobject]@{ Where = $where; Kind = $kind; Verify = $verify }
            } elseif ($line -notmatch '^      ') {
                $inHolders = $false
            }
        }
    }
    return $holders
}

$entry = Get-EntryLines -Id $Id
if ($entry.Count -eq 0) {
    Write-Output "No registry entry found for '$Id'. (Grouped sub-accounts, e.g. mosquitto-accounts--nodered, aren't individually rotatable yet -- rotate the group id and handle the one sub-account by hand; see CARD-0372's open design question on this.)"
    exit 1
}

$what = Get-Field $entry 'what'
$tier = Get-Field $entry 'tier'
$lastRotated = Get-Field $entry 'last_rotated'
$dualAccept = Get-Field $entry 'dual_accept'
$automation = Get-Field $entry 'automation'
$note = Get-Field $entry 'note'
$holders = Get-Holders $entry

Write-Output "=== ROTATION PLAN: $Id (DRY RUN -- nothing executed, no value touched) ==="
Write-Output "What:         $what"
Write-Output "Tier:         $tier"
Write-Output "Last rotated: $lastRotated"
Write-Output "Dual-accept:  $dualAccept"
Write-Output "Automation:   $automation"
if ($note) { Write-Output "Note:         $note" }
Write-Output ""
Write-Output "Holders ($($holders.Count)):"
if ($holders.Count -eq 0) {
    Write-Output "  (none parsed -- this id may be a grouped entry with an 'accounts:' map instead of a flat 'holders:' list; rotate.ps1 doesn't handle that shape yet)"
} else {
    $i = 1
    foreach ($h in $holders) {
        Write-Output "  $i. [$($h.Kind)] $($h.Where)"
        if ($h.Verify) { Write-Output "       verify: $($h.Verify)" }
        $i++
    }
}
Write-Output ""
Write-Output "NOT IMPLEMENTED: generate/stage/distribute/verify/cutover/revoke. This is Step 5's"
Write-Output "skeleton only -- a real recipe (Step 6+) is what would actually execute this plan."
