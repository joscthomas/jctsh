# secret.ps1 -- Windows-side client for CARD-0372's credential helper (originally
# named `sec`, renamed 2026-10-02, MOVED OFF WINDOWS 2026-10-02 -- Joseph: "building a
# dependency on windows... manage it not on windows").
#
# The vault and the real `secret` logic now live on the M8 (tos/secret.py,
# /usr/local/bin/secret.py there) -- a single root-owned, 0600 key file, no DPAPI, no
# per-Windows-profile duplication, no cross-profile lock file. This script is now a
# thin SSH wrapper: every vault-touching command (init/has/fingerprint/new/copy/set/run)
# just relays to the M8 over `ssh jct@m8.local`. `due` is the one exception -- it only
# reads tos/credential-registry.yaml (values-free), so it stays fully local, no network
# dependency, same as before.
#
# Commands:
#   secret.ps1 init                            -- doctor check on the M8, no values
#   secret.ps1 has <name>                      -- does an entry exist (title only)
#   secret.ps1 fingerprint <name>               -- SHA-256 of the value, never the value
#   secret.ps1 new <name> [-Length 32]          -- generate on the M8, value relayed once
#                                                  over SSH (encrypted in transit) straight
#                                                  onto this machine's clipboard, never
#                                                  printed or written to disk here
#   secret.ps1 copy <name>                      -- same relay-to-clipboard, for an existing
#                                                  value. KNOWN REGRESSION (for review):
#                                                  the old local keepassxc-cli `clip` had a
#                                                  built-in auto-clear timeout; this path
#                                                  doesn't clear the Windows clipboard for
#                                                  you -- clear it yourself after pasting.
#   secret.ps1 set <name>                       -- interactive; opens `ssh -t` so the M8's
#                                                  own masked prompt works over the session;
#                                                  run this by hand, never from inside a
#                                                  Claude Code session
#   secret.ps1 run -Name <name> -EnvVar <VAR> -- <command...>
#                                                -- runs <command> ON THE M8 (not locally)
#                                                   with the value injected into its
#                                                   environment only; M8 masks its exact
#                                                   value before this script ever sees the
#                                                   output
#   secret.ps1 due                              -- local-only registry scan (see above),
#                                                   unchanged by the M8 move
#
# Not built: the registry-aware `rotate` orchestrator; a lock file for two SSH sessions
# racing the same credential (not yet a real problem -- M8 having one owner already
# removed the Windows two-profile version of this problem).

param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet('init', 'has', 'fingerprint', 'new', 'copy', 'set', 'run', 'due')]
    [string]$Action,

    [Parameter(Position = 1)]
    [string]$Name,

    [int]$Length = 32,
    [int]$Timeout = 60,
    [string]$EnvVar,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = 'Stop'

$M8Host = 'jct@m8.local'
$M8Script = '/usr/local/bin/secret.py'
$RegistryPath = 'C:\Shared\jctsh\tos\credential-registry.yaml'

# --- SSH relay to the M8 (replaces the old local Credential-Manager/keepassxc-cli calls) ---

function ConvertTo-RemoteQuoted {
    param([string]$Value)
    "'" + ($Value -replace "'", "'\''") + "'"
}

function Invoke-RemoteSecret {
    param([string[]]$RemoteArgs, [switch]$Tty, [switch]$CaptureOutput)
    $quoted = $RemoteArgs | ForEach-Object { ConvertTo-RemoteQuoted $_ }
    $remoteCmd = "python3 $M8Script " + ($quoted -join ' ')
    $sshArgs = @()
    if ($Tty) { $sshArgs += '-t' }
    $sshArgs += $M8Host, $remoteCmd
    if ($CaptureOutput) {
        $out = & ssh @sshArgs 2>&1
        return [pscustomobject]@{ Output = $out; ExitCode = $LASTEXITCODE }
    } else {
        & ssh @sshArgs
        return [pscustomobject]@{ Output = $null; ExitCode = $LASTEXITCODE }
    }
}

function Set-ClipboardWithAutoClear {
    # Fixes the regression from the M8 move: the old local `keepassxc-cli clip` had a
    # built-in auto-clear timeout; relaying a value over SSH to this clipboard didn't.
    # Spawns a fully detached background process (survives this script exiting) that
    # waits, then clears the clipboard ONLY if it still holds this exact value -- so it
    # never clobbers something else you copied in the meantime. Compares by SHA-256
    # fingerprint; the clearer process never carries the real value, only the hash.
    param([string]$Value, [int]$TimeoutSeconds)
    Set-Clipboard -Value $Value
    $hash = [BitConverter]::ToString(
        [System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Value))
    ).Replace('-', '')

    $clearScript = @"
Start-Sleep -Seconds $TimeoutSeconds
try {
    `$cur = Get-Clipboard -Raw -ErrorAction SilentlyContinue
    if (`$cur) {
        `$h = [BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes(`$cur))).Replace('-','')
        if (`$h -eq '$hash') { Set-Clipboard -Value ' ' }
    }
} catch {}
"@
    $encoded = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($clearScript))
    Start-Process powershell -ArgumentList @('-NoProfile', '-WindowStyle', 'Hidden', '-EncodedCommand', $encoded) -WindowStyle Hidden | Out-Null
}

# --- Registry scan (values-free: only reads tos/credential-registry.yaml, never the
# vault or Credential Manager) ---

function Get-RegistryDueReport {
    $lines = Get-Content $RegistryPath
    $today = Get-Date

    $idRecords = @()
    $subRecords = @()
    $cur = $null

    foreach ($line in $lines) {
        if ($line -match '^  - id:\s*(\S+)\s*$') {
            if ($cur) { $idRecords += [pscustomobject]$cur }
            $cur = @{
                Id = $Matches[1]; Tier = $null; IntervalDays = $null; LastRotated = $null
                ExposedDates = @(); RotationRequested = $null; Retired = $null
            }
            continue
        }
        if (-not $cur) { continue }

        if ($line -match '^    tier:\s*(\d+)') { $cur.Tier = [int]$Matches[1]; continue }
        if ($line -match '^    interval_days:\s*(null|\d+)') {
            $cur.IntervalDays = if ($Matches[1] -eq 'null') { $null } else { [int]$Matches[1] }
            continue
        }
        if ($line -match '^    last_rotated:\s*(\S+)') { $cur.LastRotated = $Matches[1]; continue }
        if ($line -match '^    exposed:\s*\[(.*)\]') {
            $cur.ExposedDates = @([regex]::Matches($Matches[1], '\d{4}-\d{2}-\d{2}') | ForEach-Object { $_.Value })
            continue
        }
        if ($line -match '^    rotation_requested:\s*(null|".*")') {
            $cur.RotationRequested = if ($Matches[1] -eq 'null') { $null } else { $Matches[1] }
            continue
        }
        if ($line -match '^    retired:\s*(null|".*")') {
            $cur.Retired = if ($Matches[1] -eq 'null') { $null } else { $Matches[1] }
            continue
        }
        # A nested sub-account, e.g. mosquitto-accounts.accounts.<name>: {holder: ..., rotation_requested: "...", retired: "..."}
        if ($line -match '^      (\S+):\s*\{(.*)\}\s*$') {
            $subName = $Matches[1]; $body = $Matches[2]
            $subRR = $null; $subRetired = $null
            if ($body -match 'rotation_requested:\s*"([^"]*)"') { $subRR = $Matches[1] }
            if ($body -match 'retired:\s*"([^"]*)"') { $subRetired = $Matches[1] }
            if ($subRR -or $subRetired) {
                $subRecords += [pscustomobject]@{ Id = $cur.Id; SubAccount = $subName; RotationRequested = $subRR; Retired = $subRetired }
            }
            continue
        }
    }
    if ($cur) { $idRecords += [pscustomobject]$cur }

    $exposedBucket = @(); $requestedBucket = @(); $overdueBucket = @()

    foreach ($r in $idRecords) {
        if ($r.Retired) { continue }  # retired = stops existing anywhere; no action to surface

        $mostRecentExposed = $null
        if ($r.ExposedDates.Count -gt 0) { $mostRecentExposed = ($r.ExposedDates | Sort-Object -Descending | Select-Object -First 1) }

        $rotatedAfterExposure = $false
        if ($mostRecentExposed -and $r.LastRotated -and $r.LastRotated -ne 'unknown') {
            try { $rotatedAfterExposure = ([datetime]$r.LastRotated) -ge ([datetime]$mostRecentExposed) } catch { }
        }

        if ($mostRecentExposed -and -not $rotatedAfterExposure) {
            $exposedBucket += [pscustomobject]@{ Name = $r.Id; Detail = "exposed $mostRecentExposed, last_rotated $($r.LastRotated)" }
            continue
        }
        if ($r.RotationRequested) {
            $requestedBucket += [pscustomobject]@{ Name = $r.Id; Detail = $r.RotationRequested }
            continue
        }
        if ($r.IntervalDays) {
            if (-not $r.LastRotated -or $r.LastRotated -eq 'unknown') {
                $overdueBucket += [pscustomobject]@{ Name = $r.Id; Detail = "never recorded (tier $($r.Tier), $($r.IntervalDays)d cadence)" }
            } else {
                try {
                    $days = ($today - [datetime]$r.LastRotated).Days
                    if ($days -gt $r.IntervalDays) {
                        $overdueBucket += [pscustomobject]@{ Name = $r.Id; Detail = "$days days since last rotation (cadence $($r.IntervalDays)d)" }
                    }
                } catch { }
            }
        }
    }

    foreach ($s in $subRecords) {
        if ($s.Retired) { continue }  # e.g. mosquitto-accounts--air-quality-monitor, CARD-0377
        if ($s.RotationRequested) {
            $requestedBucket += [pscustomobject]@{ Name = "$($s.Id)--$($s.SubAccount)"; Detail = $s.RotationRequested }
        }
    }

    [pscustomobject]@{ Exposed = $exposedBucket; Requested = $requestedBucket; Overdue = $overdueBucket }
}

# --- Commands ---

switch ($Action) {

    'init' {
        $r = Invoke-RemoteSecret -RemoteArgs @('init') -CaptureOutput
        $r.Output | ForEach-Object { Write-Output $_ }
        exit $r.ExitCode
    }

    'has' {
        if (-not $Name) { throw 'Usage: secret.ps1 has <name>' }
        $r = Invoke-RemoteSecret -RemoteArgs @('has', $Name) -CaptureOutput
        $r.Output | ForEach-Object { Write-Output $_ }
        exit $r.ExitCode
    }

    'fingerprint' {
        if (-not $Name) { throw 'Usage: secret.ps1 fingerprint <name>' }
        $r = Invoke-RemoteSecret -RemoteArgs @('fingerprint', $Name) -CaptureOutput
        $r.Output | ForEach-Object { Write-Output $_ }
        exit $r.ExitCode
    }

    'new' {
        if (-not $Name) { throw 'Usage: secret.ps1 new <name> [-Length 32]' }
        $r = Invoke-RemoteSecret -RemoteArgs @('new', $Name, '--length', "$Length") -CaptureOutput
        if ($r.ExitCode -ne 0) {
            $r.Output | ForEach-Object { Write-Output $_ }
            exit $r.ExitCode
        }
        $value = ($r.Output -join "`n").Trim()
        if ($value) { Set-ClipboardWithAutoClear -Value $value -TimeoutSeconds $Timeout }
        $value = $null
        Write-Output "Created '$Name' (length $Length) on the M8 vault; its value is on the clipboard for $Timeout s (auto-clears, won't clobber anything else you copy first). Paste it into RoboForm, then add a registry entry (see CARD-0372's 'New-credential workflow')."
    }

    'copy' {
        if (-not $Name) { throw 'Usage: secret.ps1 copy <name>' }
        $r = Invoke-RemoteSecret -RemoteArgs @('copy', $Name) -CaptureOutput
        if ($r.ExitCode -ne 0) {
            $r.Output | ForEach-Object { Write-Output $_ }
            exit $r.ExitCode
        }
        $value = ($r.Output -join "`n").Trim()
        if ($value) { Set-ClipboardWithAutoClear -Value $value -TimeoutSeconds $Timeout }
        $value = $null
        Write-Output "'$Name' placed on the clipboard for $Timeout s (auto-clears)."
    }

    'set' {
        if (-not $Name) { throw 'Usage: secret.ps1 set <name>  (interactive -- masked prompt over SSH; run this yourself, not from a session)' }
        $r = Invoke-RemoteSecret -RemoteArgs @('set', $Name) -Tty
        exit $r.ExitCode
    }

    'run' {
        if (-not $Name -or -not $EnvVar -or -not $Rest) {
            throw 'Usage: secret.ps1 run -Name <entry> -EnvVar <VARNAME> -- <command> [args...]  (command executes ON THE M8, not locally)'
        }
        $remoteArgs = @('run', $Name, '--env', $EnvVar, '--') + $Rest
        $r = Invoke-RemoteSecret -RemoteArgs $remoteArgs -CaptureOutput
        $r.Output | ForEach-Object { Write-Output $_ }
        exit $r.ExitCode
    }

    'due' {
        $report = Get-RegistryDueReport

        Write-Output "=== EXPOSED, NOT YET ROTATED (surface every session, per JCTsh-Session-Start.md) ==="
        if ($report.Exposed.Count -gt 0) {
            $report.Exposed | ForEach-Object { Write-Output "  $($_.Name) -- $($_.Detail)" }
        } else { Write-Output "  none" }

        Write-Output ""
        Write-Output "=== ROTATION REQUESTED ==="
        if ($report.Requested.Count -gt 0) {
            $report.Requested | ForEach-Object { Write-Output "  $($_.Name) -- $($_.Detail)" }
        } else { Write-Output "  none" }

        Write-Output ""
        Write-Output "=== OVERDUE BY CADENCE (periodic nudge -- offer, don't demand) ==="
        if ($report.Overdue.Count -gt 0) {
            $report.Overdue | ForEach-Object { Write-Output "  $($_.Name) -- $($_.Detail)" }
        } else { Write-Output "  none" }

        if ($report.Exposed.Count -gt 0) { exit 2 }
        elseif ($report.Requested.Count -gt 0 -or $report.Overdue.Count -gt 0) { exit 1 }
        else { exit 0 }
    }
}
