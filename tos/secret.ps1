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
#                                                  value. No auto-clear (removed 2026-10-02,
#                                                  Joseph: he copies it onward into RoboForm
#                                                  anyway, which doesn't expire) -- clear the
#                                                  clipboard yourself if you want it gone sooner.
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
#   secret.ps1 writefile <name> -Path <file> -Key <yaml-key>
#                                                -- edits an EXISTING "key: value" line in a
#                                                   LOCAL file on this workstation (e.g. an
#                                                   ESPHome components/<name>/secrets.yaml,
#                                                   never committed) to <name>'s current vault
#                                                   value. Same never-print relay as `copy`
#                                                   (SSH -> a PowerShell variable -> the file,
#                                                   nulled right after) -- the value is never
#                                                   written to this script's own output, so a
#                                                   Claude Code session can run this directly
#                                                   instead of asking Joseph to paste it by
#                                                   hand (CARD-0372, 2026-10-02: "build it so I
#                                                   don't have to"). Refuses if the key is
#                                                   missing or appears more than once -- it
#                                                   edits an existing line, never adds one.
#                                                   Verifies by SHA-256 fingerprint match
#                                                   against the vault (re-read from disk after
#                                                   writing), never by comparing raw values.
#                                                   Only understands a simple "key: value" (or
#                                                   "key: \"value\"") line shape -- not general
#                                                   YAML, nested keys, or multi-line values.
#
#   secret.ps1 mosquitto-passwd <name> -MqttUser <broker-user>
#                                                [-MosquittoHost pi@pi1.local] [-PasswdFile /etc/mosquitto/passwd]
#                                                -- sets a Mosquitto broker account's password on a
#                                                   remote host (the Pi by default) to <name>'s current
#                                                   vault value, via mosquitto_passwd's INTERACTIVE
#                                                   (non -b) form -- the value is piped to its stdin
#                                                   prompts from a PowerShell variable, never passed as
#                                                   a command-line argument (which `-b` would do, and
#                                                   which is exactly the key=/password= literal CARD-0334's
#                                                   guard exists to block -- confirmed live 2026-10-02 that
#                                                   mosquitto_passwd 2.0.21 accepts piped, non-tty stdin
#                                                   fine). Then fixes ownership (`chown root:mosquitto`,
#                                                   the documented gotcha) and restarts mosquitto, checking
#                                                   it comes back active. Cannot verify by fingerprint like
#                                                   `writefile` (the passwd file holds a salted hash, not a
#                                                   comparable digest of the plaintext) -- verification is
#                                                   mosquitto_passwd's own exit code plus the post-restart
#                                                   active check.
#
# Rotation itself is tos/rotate.py (CARD-0372), which drives secret.py's rotation
# commands (stage/promote/envfile/drop-previous...) over the same SSH path; secret.py
# locks the vault for every write, and rotate.py keeps its own run lock. `writefile` and
# `mosquitto-passwd` above are not yet wired into rotate.py's own `apply:` holder mechanism
# (that only knows how to drive secret.py envfile on an SSH-reachable host) -- today
# they're invoked directly by whoever is driving a rotation (the rotate-credentials skill,
# or Joseph by hand) for a holder whose registry entry names a local file or a remote
# passwd-style account of the shape these two commands handle.

param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet('init', 'has', 'fingerprint', 'new', 'copy', 'set', 'run', 'due', 'writefile', 'mosquitto-passwd', 'envcopy', 'remoteenvwrite', 'syncfile')]
    [string]$Action,

    [Parameter(Position = 1)]
    [string]$Name,

    [int]$Length = 32,
    [int]$Timeout = 60,   # accepted, no longer used -- clipboard auto-clear removed 2026-10-02
    [string]$EnvVar,
    [string]$Path,
    [string]$Key,
    [string]$MqttUser,
    [string]$MosquittoHost,
    [string]$PasswdFile,
    [string]$RemoteHost,
    [string]$Restart,
    [string]$Dest,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = 'Stop'

$M8Host = 'jct@m8.local'
$M8Script = '/usr/local/bin/secret.py'
# Next to this script (C:\Shared\jctsh\tos on the workstation); JCTSH_REGISTRY overrides it (tests).
$RegistryPath = if ($env:JCTSH_REGISTRY) { $env:JCTSH_REGISTRY } else { Join-Path $PSScriptRoot 'credential-registry.yaml' }
# rotate.py's values-free run state (CARD-0372), shown by `due`.
$RotationStateDir = if ($env:JCTSH_ROTATION_STATE) { $env:JCTSH_ROTATION_STATE } else { Join-Path $PSScriptRoot '.rotation-state' }

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

# No auto-clear (removed 2026-10-02, Joseph: "that's a PITA, when I get it into
# RoboForm I just copy it to the clipboard from there anyway and it does not expire").
# A plain Set-Clipboard -Value $Value is all `new`/`copy` do now -- the clipboard holds
# the value until something else overwrites it, same as any normal copy/paste. Clear it
# yourself if you want it gone sooner (or paste into RoboForm, which Joseph already does
# as the next step regardless).

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
                ExposedDates = @(); RotationRequested = $null; RotationDeclined = $null
                Retired = $null; RoboformPending = $false
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
        if ($line -match '^    rotation_declined:\s*(null|".*")') {
            $cur.RotationDeclined = if ($Matches[1] -eq 'null') { $null } else { $Matches[1] }
            continue
        }
        if ($line -match '^    roboform_synced:\s*false\b') { $cur.RoboformPending = $true; continue }
        if ($line -match '^    retired:\s*(null|".*")') {
            $cur.Retired = if ($Matches[1] -eq 'null') { $null } else { $Matches[1] }
            continue
        }
        # A nested sub-account, e.g. mosquitto-accounts.accounts.<name>: {holder: ..., exposed: [...],
        # last_rotated: ..., rotation_requested: "...", retired: "..."}. Every account is recorded, not
        # just flagged ones: an entry with an accounts: map is evaluated per account (CARD-0372, 2026-10-02).
        if ($line -match '^      (\S+):\s*\{(.*)\}\s*$') {
            $subName = $Matches[1]; $body = $Matches[2]
            $subRR = $null; $subRD = $null; $subRetired = $null; $subLast = $null; $subExposed = @()
            if ($body -match 'rotation_requested:\s*"([^"]*)"') { $subRR = $Matches[1] }
            if ($body -match 'rotation_declined:\s*"([^"]*)"') { $subRD = $Matches[1] }
            if ($body -match 'retired:\s*"([^"]*)"') { $subRetired = $Matches[1] }
            # Match the unquoted fields only outside quoted strings, so a holder/reason text can't fake one.
            $bare = $body -replace '"[^"]*"', '""'
            if ($bare -match 'last_rotated:\s*([^,\s}]+)') { $subLast = $Matches[1] }
            if ($bare -match 'exposed:\s*\[([^\]]*)\]') {
                $subExposed = @([regex]::Matches($Matches[1], '\d{4}-\d{2}-\d{2}') | ForEach-Object { $_.Value })
            }
            $subRecords += [pscustomobject]@{
                Id = $cur.Id; SubAccount = $subName; RotationRequested = $subRR; RotationDeclined = $subRD
                Retired = $subRetired; LastRotated = $subLast; ExposedDates = $subExposed
                RoboformPending = ($bare -match 'roboform_synced:\s*false\b')
            }
            continue
        }
    }
    if ($cur) { $idRecords += [pscustomobject]$cur }

    # Lists, not arrays: the nested function below appends to them through PowerShell's dynamic scope.
    $exposedBucket = [System.Collections.Generic.List[object]]::new()
    $requestedBucket = [System.Collections.Generic.List[object]]::new()
    $overdueBucket = [System.Collections.Generic.List[object]]::new()
    $roboformBucket = [System.Collections.Generic.List[object]]::new()
    $declinedBucket = [System.Collections.Generic.List[object]]::new()

    # One credential's status, highest-priority bucket only: exposed > requested > overdue.
    function Add-DueStatus($Name, $ExposedDates, $LastRotated, $RotationRequested, $IntervalDays, $Tier) {
        $mostRecentExposed = $null
        if ($ExposedDates.Count -gt 0) { $mostRecentExposed = ($ExposedDates | Sort-Object -Descending | Select-Object -First 1) }

        $rotatedAfterExposure = $false
        if ($mostRecentExposed -and $LastRotated -and $LastRotated -ne 'unknown') {
            try { $rotatedAfterExposure = ([datetime]$LastRotated) -ge ([datetime]$mostRecentExposed) } catch { }
        }

        if ($mostRecentExposed -and -not $rotatedAfterExposure) {
            $null = $exposedBucket.Add([pscustomobject]@{ Name = $Name; Detail = "exposed $mostRecentExposed, last_rotated $LastRotated" })
            return
        }
        if ($RotationRequested) {
            $null = $requestedBucket.Add([pscustomobject]@{ Name = $Name; Detail = $RotationRequested })
            return
        }
        if ($IntervalDays) {
            if (-not $LastRotated -or $LastRotated -eq 'unknown') {
                $null = $overdueBucket.Add([pscustomobject]@{ Name = $Name; Detail = "never recorded (tier $Tier, $($IntervalDays)d cadence)" })
            } else {
                try {
                    $days = ($today - [datetime]$LastRotated).Days
                    if ($days -gt $IntervalDays) {
                        $null = $overdueBucket.Add([pscustomobject]@{ Name = $Name; Detail = "$days days since last rotation (cadence $($IntervalDays)d)" })
                    }
                } catch { }
            }
        }
    }

    foreach ($r in $idRecords) {
        if ($r.Retired) { continue }  # retired = stops existing anywhere; no action to surface

        $subs = @($subRecords | Where-Object { $_.Id -eq $r.Id })
        if ($r.RoboformPending) { $null = $roboformBucket.Add([pscustomobject]@{ Name = $r.Id }) }
        foreach ($s in $subs) {
            if ($s.RoboformPending -and -not $s.Retired) { $null = $roboformBucket.Add([pscustomobject]@{ Name = "$($r.Id)--$($s.SubAccount)" }) }
        }
        if ($subs.Count -eq 0) {
            if ($r.RotationDeclined) {
                $null = $declinedBucket.Add([pscustomobject]@{ Name = $r.Id; Detail = $r.RotationDeclined })
                continue
            }
            Add-DueStatus $r.Id $r.ExposedDates $r.LastRotated $r.RotationRequested $r.IntervalDays $r.Tier
            continue
        }

        # Grouped entry: each account on its own. An entry-level exposure applies to every account; an
        # account's own last_rotated wins over the entry's fallback, so rotating one account clears only it.
        foreach ($s in $subs) {
            if ($s.Retired) { continue }  # e.g. mosquitto-accounts--air-quality-monitor, CARD-0377
            if ($s.RotationDeclined) {
                $null = $declinedBucket.Add([pscustomobject]@{ Name = "$($r.Id)--$($s.SubAccount)"; Detail = $s.RotationDeclined })
                continue
            }
            $exposed = @($r.ExposedDates) + @($s.ExposedDates)
            $last = if ($s.LastRotated) { $s.LastRotated } else { $r.LastRotated }
            $rr = if ($s.RotationRequested) { $s.RotationRequested } else { $r.RotationRequested }
            Add-DueStatus "$($r.Id)--$($s.SubAccount)" $exposed $last $rr $r.IntervalDays $r.Tier
        }
    }

    # Rotations rotate.py has started and not finished (values-free JSON state files).
    $inProgress = [System.Collections.Generic.List[object]]::new()
    if (Test-Path $RotationStateDir) {
        foreach ($f in Get-ChildItem -Path $RotationStateDir -Filter '*.json' -File) {
            try {
                $st = Get-Content $f.FullName -Raw | ConvertFrom-Json
                $next = if ($st.phase -eq 'applying') { 'continue' } elseif ($st.roboform_synced) { 'finish' } else { 'confirm-synced' }
                # PowerShell 7's ConvertFrom-Json turns the ISO timestamp into a DateTime; show it as ISO again.
                $exp = if ($st.expires -is [datetime]) { $st.expires.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") } else { $st.expires }
                $null = $inProgress.Add([pscustomobject]@{ Name = $st.target; Detail = "phase $($st.phase), window closes $exp -- next: rotate.py $next $($st.target)" })
            } catch { }
        }
    }

    [pscustomobject]@{ Exposed = $exposedBucket; Requested = $requestedBucket; Overdue = $overdueBucket
                       Roboform = $roboformBucket; InProgress = $inProgress; Declined = $declinedBucket }
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
        if ($value) { Set-Clipboard -Value $value }
        $value = $null
        Write-Output "Created '$Name' (length $Length) on the M8 vault; its value is on the clipboard (stays until you copy something else). Paste it into RoboForm, then add a registry entry (see CARD-0372's 'New-credential workflow')."
    }

    'copy' {
        if (-not $Name) { throw 'Usage: secret.ps1 copy <name>' }
        $r = Invoke-RemoteSecret -RemoteArgs @('copy', $Name) -CaptureOutput
        if ($r.ExitCode -ne 0) {
            $r.Output | ForEach-Object { Write-Output $_ }
            exit $r.ExitCode
        }
        $value = ($r.Output -join "`n").Trim()
        if ($value) { Set-Clipboard -Value $value }
        $value = $null
        Write-Output "'$Name' placed on the clipboard (stays until you copy something else)."
    }

    'set' {
        if (-not $Name) { throw 'Usage: secret.ps1 set <name>  (interactive -- masked prompt over SSH; run this yourself, not from a session)' }
        $r = Invoke-RemoteSecret -RemoteArgs @('set', $Name) -Tty
        exit $r.ExitCode
    }

    'writefile' {
        if (-not $Name -or -not $Path -or -not $Key) {
            throw 'Usage: secret.ps1 writefile <name> -Path <file> -Key <yaml-key>  (edits an EXISTING "key: value" line in place; the value is never printed)'
        }
        $resolved = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
        $pattern = '^(\s*)' + [regex]::Escape($Key) + '(\s*):(\s*)(.*?)\s*$'

        function Get-YamlEscaped([string]$v) {
            [regex]::Replace($v, '[\\"]', { param($m) if ($m.Value -eq '\') { '\\' } else { '\"' } })
        }
        function Get-YamlUnescaped([string]$v) {
            [regex]::Replace($v, '\\.', { param($m) if ($m.Value -eq '\\\\') { '\' } elseif ($m.Value -eq '\\"') { '"' } else { $m.Value } })
        }
        function Get-Sha256Hex([string]$v) {
            ([BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($v)))).Replace('-', '').ToLowerInvariant()
        }

        $lines = [System.IO.File]::ReadAllLines($resolved)
        $hits = @()
        for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match $pattern) { $hits += $i } }
        if ($hits.Count -eq 0) { throw "'$Key' not found in $resolved -- writefile only edits an existing key, it won't add one." }
        if ($hits.Count -gt 1) { throw "'$Key' appears $($hits.Count) times in $resolved -- ambiguous, edit it by hand." }

        $r = Invoke-RemoteSecret -RemoteArgs @('copy', $Name) -CaptureOutput
        if ($r.ExitCode -ne 0) {
            $r.Output | ForEach-Object { Write-Output $_ }
            exit $r.ExitCode
        }
        $value = ($r.Output -join "`n").Trim()
        if (-not $value) { throw "no value read back for '$Name'" }

        $i = $hits[0]
        $m = [regex]::Match($lines[$i], $pattern)
        $lines[$i] = $m.Groups[1].Value + $Key + $m.Groups[2].Value + ':' + $m.Groups[3].Value + '"' + (Get-YamlEscaped $value) + '"'
        $value = $null

        $tmp = Join-Path (Split-Path $resolved) (".writefile-$([Guid]::NewGuid().ToString('N')).tmp")
        [System.IO.File]::WriteAllLines($tmp, $lines, [System.Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $tmp -Destination $resolved -Force

        # Re-read from disk (not from the variable just written) and verify by fingerprint,
        # never by comparing raw values.
        $writtenLine = ([System.IO.File]::ReadAllLines($resolved))[$i]
        $wm = [regex]::Match($writtenLine, $pattern)
        $writtenValue = Get-YamlUnescaped ($wm.Groups[4].Value.Trim('"'))
        $localHash = Get-Sha256Hex $writtenValue
        $writtenValue = $null

        $fp = Invoke-RemoteSecret -RemoteArgs @('fingerprint', $Name) -CaptureOutput
        $remoteHash = (($fp.Output -join '').Trim()) -replace '^sha256:', ''
        if ($localHash -ne $remoteHash) {
            throw "wrote into $resolved but the on-disk value's fingerprint doesn't match the vault's current '$Name' -- investigate before trusting this file (never diff the values directly; compare 'secret.ps1 fingerprint $Name' against a fresh run of this command)."
        }
        Write-Output "wrote '$Key' in $resolved from '$Name' (fingerprint-verified; value never shown)."
    }

    'mosquitto-passwd' {
        if (-not $Name -or -not $MqttUser) {
            throw 'Usage: secret.ps1 mosquitto-passwd <name> -MqttUser <broker-user> [-MosquittoHost pi@pi1.local] [-PasswdFile /etc/mosquitto/passwd]'
        }
        $h = if ($MosquittoHost) { $MosquittoHost } else { 'pi@pi1.local' }
        $f = if ($PasswdFile) { $PasswdFile } else { '/etc/mosquitto/passwd' }

        $r = Invoke-RemoteSecret -RemoteArgs @('copy', $Name) -CaptureOutput
        if ($r.ExitCode -ne 0) {
            $r.Output | ForEach-Object { Write-Output $_ }
            exit $r.ExitCode
        }
        $value = ($r.Output -join "`n").Trim()
        if (-not $value) { throw "no value read back for '$Name'" }

        # Interactive (non -b) form: two lines on stdin, never a command-line argument.
        $stdinPayload = "$value`n$value`n"
        $value = $null
        $setOutput = $stdinPayload | & ssh $h "sudo mosquitto_passwd $f $MqttUser" 2>&1
        $setExit = $LASTEXITCODE
        $stdinPayload = $null
        if ($setExit -ne 0) {
            $setOutput | ForEach-Object { Write-Output $_ }
            throw "mosquitto_passwd on $h exited $setExit -- the old password is still in $f; nothing else was touched."
        }

        & ssh $h "sudo chown root:mosquitto $f" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "chown root:mosquitto $f failed on $h -- fix by hand before relying on this account." }
        & ssh $h "sudo systemctl restart mosquitto" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "systemctl restart mosquitto failed on $h -- check it by hand." }
        Start-Sleep -Seconds 2
        $active = (& ssh $h "systemctl is-active mosquitto" 2>&1 | Out-String).Trim()
        if ($active -ne 'active') {
            throw "mosquitto is not active on $h after restart (status: $active) -- investigate before trusting this rotation."
        }
        Write-Output "set '$MqttUser' on ${h}:${f} from '$Name' (mosquitto_passwd interactive form, value only ever on stdin; verified mosquitto active after restart; value never shown)."
    }

    'envcopy' {
        if (-not $Name -or -not $RemoteHost -or -not $Path -or -not $Key) {
            throw 'Usage: secret.ps1 envcopy <label> -RemoteHost <user@host> -Path <remote envfile> -Key <VAR_NAME>  (reads one KEY=VALUE line from a remote file over SSH, relays straight to the clipboard, never prints it -- for a credential not yet in the vault)'
        }
        # A targeted single-key read, not a dump -- deliberately the opposite shape of
        # the CARD-0334 sixth-occurrence incident (a broad `env | grep` that matched
        # more than intended). grep -E '^KEY=' can only ever match that one name.
        $remoteCmd = "grep -E '^" + $Key + "=' " + $Path + " | head -1 | cut -d= -f2-"
        $raw = & ssh $RemoteHost $remoteCmd 2>&1
        $exit = $LASTEXITCODE
        if ($exit -ne 0 -or -not $raw) {
            throw "could not read '$Key' from ${RemoteHost}:${Path} (exit $exit) -- confirm the key exists and is spelled exactly right."
        }
        $value = ($raw -join "`n").Trim()
        if ($value.Length -ge 2 -and (($value[0] -eq '"' -and $value[-1] -eq '"') -or ($value[0] -eq "'" -and $value[-1] -eq "'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        Set-Clipboard -Value $value
        $value = $null
        Write-Output "'$Name' ($Key from ${RemoteHost}:${Path}) placed on the clipboard (stays until you copy something else). Value never shown."
    }

    'syncfile' {
        if (-not $Path -or -not $Dest) {
            throw 'Usage: secret.ps1 syncfile -Path <source> -Dest <destination>  (plain local file copy -- no vault/value involved, just a sanctioned way to touch a device-secrets path, e.g. syncing a repo secrets.yaml over its stale C:\esphome working copy)'
        }
        $src = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
        Copy-Item -LiteralPath $src -Destination $Dest -Force
        Write-Output "copied $src -> $Dest"
    }

    'remoteenvwrite' {
        if (-not $Name -or -not $RemoteHost -or -not $Path -or -not $Key) {
            throw 'Usage: secret.ps1 remoteenvwrite <name> -RemoteHost <user@host> -Path <remote KEY=VALUE file> -Key <VAR_NAME> [-Restart "<remote restart command>"]  (edits one EXISTING line via piped stdin, never a command-line literal; the value is never shown)'
        }
        $r = Invoke-RemoteSecret -RemoteArgs @('copy', $Name) -CaptureOutput
        if ($r.ExitCode -ne 0) {
            $r.Output | ForEach-Object { Write-Output $_ }
            exit $r.ExitCode
        }
        $value = ($r.Output -join "`n").Trim()
        if (-not $value) { throw "no value read back for '$Name'" }

        # Push a small Python script (avoids multi-layer shell/awk quoting entirely --
        # a one-line awk version didn't survive PowerShell -> ssh.exe argv encoding
        # intact, found live testing this), then run it with the new value piped via
        # stdin only -- never interpolated into any command's own text.
        $pyScript = @"
import sys, os, tempfile
newval = sys.stdin.read().rstrip('\n')
path = r'$Path'
key = '$Key'
with open(path) as f:
    lines = f.readlines()
hits = [i for i, l in enumerate(lines) if l.startswith(key + '=')]
if len(hits) != 1:
    print(f'ERROR: key count {len(hits)}', file=sys.stderr)
    sys.exit(1)
lines[hits[0]] = key + '=' + newval + '\n'
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or '.')
with os.fdopen(fd, 'w') as f:
    f.writelines(lines)
os.replace(tmp, path)
print('updated')
"@
        $remoteTmp = "/tmp/.secret-remoteenvwrite-$([Guid]::NewGuid().ToString('N')).py"
        $pyScript | & ssh $RemoteHost "cat > $remoteTmp" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "could not stage the helper script on $RemoteHost" }
        $out = $value | & ssh $RemoteHost "python3 $remoteTmp" 2>&1
        $exit = $LASTEXITCODE
        $value = $null
        & ssh $RemoteHost "rm -f $remoteTmp" 2>&1 | Out-Null
        $outText = ($out -join "`n")
        if ($exit -ne 0 -or $outText -notmatch 'updated') {
            throw "remoteenvwrite on ${RemoteHost}:${Path} failed (exit $exit): $outText"
        }

        if ($Restart) {
            & ssh $RemoteHost $Restart 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "restart command '$Restart' failed on $RemoteHost" }
        }

        # Verify by fingerprint -- re-read from disk, never compare raw values.
        $readBack = & ssh $RemoteHost "grep -E '^$Key=' '$Path' | head -1 | cut -d= -f2-" 2>&1
        $readValue = ($readBack -join "`n").Trim()
        $localHash = ([BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($readValue)))).Replace('-', '').ToLowerInvariant()
        $readValue = $null
        $fp = Invoke-RemoteSecret -RemoteArgs @('fingerprint', $Name) -CaptureOutput
        $remoteHash = (($fp.Output -join '').Trim()) -replace '^sha256:', ''
        if ($localHash -ne $remoteHash) {
            throw "wrote into ${RemoteHost}:${Path} but the on-disk value's fingerprint doesn't match the vault's current '$Name' -- investigate before trusting this."
        }
        Write-Output "wrote '$Key' in ${RemoteHost}:${Path} from '$Name' (fingerprint-verified$(if ($Restart) { "; restarted via '$Restart'" }); value never shown)."
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
        Write-Output "=== ROTATIONS IN PROGRESS (rotate.py) ==="
        if ($report.InProgress.Count -gt 0) {
            $report.InProgress | ForEach-Object { Write-Output "  $($_.Name) -- $($_.Detail)" }
        } else { Write-Output "  none" }

        Write-Output ""
        Write-Output "=== ROTATED, NOT YET PASTED INTO ROBOFORM (roboform_synced: false) ==="
        if ($report.Roboform.Count -gt 0) {
            $report.Roboform | ForEach-Object { Write-Output "  $($_.Name) -- secret.ps1 copy $($_.Name), paste into RoboForm, then rotate.py confirm-synced (or set roboform_synced: true)" }
        } else { Write-Output "  none" }

        Write-Output ""
        Write-Output "=== OVERDUE BY CADENCE (periodic nudge -- offer, don't demand) ==="
        if ($report.Overdue.Count -gt 0) {
            $report.Overdue | ForEach-Object { Write-Output "  $($_.Name) -- $($_.Detail)" }
        } else { Write-Output "  none" }

        Write-Output ""
        Write-Output "=== DECLINED (explicit decision not to rotate) ==="
        if ($report.Declined.Count -gt 0) {
            $report.Declined | ForEach-Object { Write-Output "  $($_.Name) -- $($_.Detail)" }
        } else { Write-Output "  none" }

        if ($report.Exposed.Count -gt 0) { exit 2 }
        elseif ($report.Requested.Count -gt 0 -or $report.Overdue.Count -gt 0 -or $report.Roboform.Count -gt 0 -or $report.InProgress.Count -gt 0) { exit 1 }
        else { exit 0 }
    }
}
