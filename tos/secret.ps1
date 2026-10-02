# secret.ps1 -- CARD-0372's planned credential helper (originally named `sec`, renamed
# 2026-10-02). Wraps keepassxc-cli against the shared tos vault so a Claude Code
# session can use a credential without ever seeing its value.
#
# Vault: C:\Shared\.jctsh-vault\jctsh-vault.kdbx, unlocked by a key file -- never a
# memorized password. The key file is NOT read from the loose file on disk; it is
# read from THIS Windows profile's Credential Manager (target jctsh-vault-keyfile,
# written once per profile -- see CARD-0372's "Key file custody" notes), copied to a
# short-lived temp file only for the duration of a single keepassxc-cli call, then
# deleted. This mirrors exactly the open-test both Windows profiles already ran by
# hand before this script existed.
#
# Commands implemented (CARD-0334/CARD-0372's planned surface):
#   secret.ps1 init                          -- doctor check, no values
#   secret.ps1 has <name>                     -- does an entry exist (title only)
#   secret.ps1 fingerprint <name>             -- SHA-256 of the value, never the value
#   secret.ps1 new <name> [-Length 32]         -- generate + store, result on clipboard
#   secret.ps1 copy <name> [-Timeout 60]       -- re-place an existing value on clipboard
#   secret.ps1 set <name>                      -- interactive only (keepassxc-cli's own
#                                                  masked prompt); run this by hand, in
#                                                  your own terminal, never from a session
#   secret.ps1 run -Name <name> -EnvVar <VAR> -- <command...>
#                                               -- inject one secret into a child
#                                                  process's environment only, mask its
#                                                  exact value in that command's output
#
# Not built: `init` per-profile bootstrap beyond the doctor check (placing a Credential
# Manager entry on a brand-new profile is still a deliberate, by-hand act -- see
# CARD-0372); the cross-profile lock file; `rotate` (the registry-aware orchestrator
# that calls this helper).

param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet('init', 'has', 'fingerprint', 'new', 'copy', 'set', 'run')]
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

$VaultPath = 'C:\Shared\.jctsh-vault\jctsh-vault.kdbx'
$CredTarget = 'jctsh-vault-keyfile'
$KeepassCli = 'C:\Program Files\KeePassXC\keepassxc-cli.exe'

# --- Credential Manager access (same P/Invoke pattern used by hand for both profiles) ---

$credSrc = @'
using System;
using System.Runtime.InteropServices;

public class JctshSecretCred
{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct CREDENTIAL
    {
        public uint Flags;
        public uint Type;
        public string TargetName;
        public string Comment;
        public long LastWritten;
        public uint CredentialBlobSize;
        public IntPtr CredentialBlob;
        public uint Persist;
        public uint AttributeCount;
        public IntPtr Attributes;
        public string TargetAlias;
        public string UserName;
    }

    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool CredRead(string target, uint type, uint flags, out IntPtr credentialPtr);

    [DllImport("advapi32.dll")]
    public static extern void CredFree(IntPtr buffer);

    public static byte[] ReadBlob(string target)
    {
        IntPtr credPtr;
        if (!CredRead(target, 1, 0, out credPtr))
            throw new Exception("No Credential Manager entry '" + target + "' in this Windows profile (error " + Marshal.GetLastWin32Error() + ")");
        try
        {
            CREDENTIAL cred = (CREDENTIAL)Marshal.PtrToStructure(credPtr, typeof(CREDENTIAL));
            byte[] blob = new byte[cred.CredentialBlobSize];
            Marshal.Copy(cred.CredentialBlob, blob, 0, (int)cred.CredentialBlobSize);
            return blob;
        }
        finally
        {
            CredFree(credPtr);
        }
    }
}
'@
if (-not ([System.Management.Automation.PSTypeName]'JctshSecretCred').Type) {
    Add-Type -TypeDefinition $credSrc
}

function Get-VaultKeyFilePath {
    # Writes this profile's Credential Manager copy of the key file to a fresh temp
    # file. Caller MUST delete it (use try/finally) -- never leave a second loose copy.
    $bytes = [JctshSecretCred]::ReadBlob($CredTarget)
    $tmp = Join-Path $env:TEMP ("jctsh-vault-" + [Guid]::NewGuid().ToString('N') + '.keyx')
    [System.IO.File]::WriteAllBytes($tmp, $bytes)
    [Array]::Clear($bytes, 0, $bytes.Length)
    return $tmp
}

function Invoke-Keepass {
    param([string[]]$CliArgs, [switch]$CaptureOutput)
    $keyFile = Get-VaultKeyFilePath
    try {
        $fullArgs = $CliArgs + @('-k', $keyFile, '--no-password')
        if ($CaptureOutput) {
            return & $KeepassCli @fullArgs 2>&1
        } else {
            & $KeepassCli @fullArgs
            return $LASTEXITCODE
        }
    }
    finally {
        Remove-Item $keyFile -Force -ErrorAction SilentlyContinue
    }
}

# --- Commands ---

switch ($Action) {

    'init' {
        $checks = @()

        $cliFound = Test-Path $KeepassCli
        $checks += [pscustomobject]@{ Check = 'keepassxc-cli.exe present'; Pass = $cliFound }

        $vaultFound = Test-Path $VaultPath
        $checks += [pscustomobject]@{ Check = 'vault file present'; Pass = $vaultFound }

        $credFound = $true
        try { [void][JctshSecretCred]::ReadBlob($CredTarget) } catch { $credFound = $false }
        $checks += [pscustomobject]@{ Check = "Credential Manager entry '$CredTarget' present (this profile)"; Pass = $credFound }

        $unlockOk = $false
        if ($cliFound -and $vaultFound -and $credFound) {
            try {
                $out = Invoke-Keepass -CliArgs @('db-info', $VaultPath) -CaptureOutput
                $unlockOk = ($out -join "`n") -match 'Number of entries'
            } catch { $unlockOk = $false }
        }
        $checks += [pscustomobject]@{ Check = 'vault unlocks with this profile''s key file'; Pass = $unlockOk }

        $checks | ForEach-Object {
            $mark = if ($_.Pass) { 'OK  ' } else { 'FAIL' }
            Write-Output "[$mark] $($_.Check)"
        }
        if ($checks | Where-Object { -not $_.Pass }) { exit 1 }
        exit 0
    }

    'has' {
        if (-not $Name) { throw 'Usage: secret.ps1 has <name>' }
        $out = Invoke-Keepass -CliArgs @('ls', $VaultPath, '-f') -CaptureOutput
        $found = ($out -split "`n") | Where-Object { $_.Trim() -eq $Name }
        if ($found) {
            Write-Output "yes -- '$Name' exists in the vault"
            exit 0
        } else {
            Write-Output "no -- '$Name' not found in the vault"
            exit 1
        }
    }

    'fingerprint' {
        if (-not $Name) { throw 'Usage: secret.ps1 fingerprint <name>' }
        $out = Invoke-Keepass -CliArgs @('show', $VaultPath, $Name, '-s', '-a', 'Password', '-q') -CaptureOutput
        $value = ($out -join "`n")
        if (-not $value) { throw "No value read back for '$Name' -- does the entry exist? (secret.ps1 has $Name)" }
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($value)
        $hash = [BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)).Replace('-', '').ToLower()
        [Array]::Clear($bytes, 0, $bytes.Length)
        $value = $null
        Write-Output "sha256:$hash"
    }

    'new' {
        if (-not $Name) { throw 'Usage: secret.ps1 new <name> [-Length 32]' }
        $exitCode = Invoke-Keepass -CliArgs @('add', $VaultPath, $Name, '-q', '-g', '-L', $Length, '-l', '-U', '-n', '-s')
        if ($exitCode -ne 0) { throw "keepassxc-cli add failed for '$Name' (exit $exitCode) -- does it already exist? (secret.ps1 has $Name)" }
        Invoke-Keepass -CliArgs @('clip', $VaultPath, $Name, $Timeout, '-q')
        Write-Output "Created '$Name' (length $Length) and placed its value on the clipboard for $Timeout s. Paste it into RoboForm now, then add a registry entry (see CARD-0372's 'New-credential workflow')."
    }

    'copy' {
        if (-not $Name) { throw 'Usage: secret.ps1 copy <name> [-Timeout 60]' }
        $exitCode = Invoke-Keepass -CliArgs @('clip', $VaultPath, $Name, $Timeout, '-q')
        if ($exitCode -ne 0) { throw "Could not clip '$Name' (exit $exitCode) -- does it exist? (secret.ps1 has $Name)" }
        Write-Output "'$Name' placed on the clipboard for $Timeout s."
    }

    'set' {
        if (-not $Name) { throw 'Usage: secret.ps1 set <name>  (interactive -- run this yourself, not from a session)' }
        $keyFile = Get-VaultKeyFilePath
        try {
            $exists = (Invoke-Keepass -CliArgs @('ls', $VaultPath, '-f') -CaptureOutput) -split "`n" | Where-Object { $_.Trim() -eq $Name }
            $verb = if ($exists) { 'edit' } else { 'add' }
            Write-Output "Prompting for '$Name''s new value -- this reads from YOUR terminal's own masked prompt, never from this script or a session."
            & $KeepassCli $verb $VaultPath $Name -k $keyFile --no-password -p
        }
        finally {
            Remove-Item $keyFile -Force -ErrorAction SilentlyContinue
        }
    }

    'run' {
        if (-not $Name -or -not $EnvVar -or -not $Rest) {
            throw 'Usage: secret.ps1 run -Name <entry> -EnvVar <VARNAME> -- <command> [args...]'
        }
        $out = Invoke-Keepass -CliArgs @('show', $VaultPath, $Name, '-s', '-a', 'Password', '-q') -CaptureOutput
        $value = ($out -join "`n")
        if (-not $value) { throw "No value read back for '$Name'." }

        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $Rest[0]
        if ($Rest.Length -gt 1) { $psi.Arguments = ($Rest[1..($Rest.Length - 1)] | ForEach-Object { '"' + $_ + '"' }) -join ' ' }
        $psi.EnvironmentVariables[$EnvVar] = $value
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.UseShellExecute = $false

        $proc = [System.Diagnostics.Process]::Start($psi)
        $stdout = $proc.StandardOutput.ReadToEnd()
        $stderr = $proc.StandardError.ReadToEnd()
        $proc.WaitForExit()
        $code = $proc.ExitCode

        $masked = $value
        $stdoutMasked = $stdout.Replace($masked, '[REDACTED]')
        $stderrMasked = $stderr.Replace($masked, '[REDACTED]')
        $value = $null; $masked = $null

        if ($stdoutMasked) { Write-Output $stdoutMasked }
        if ($stderrMasked) { Write-Output "STDERR: $stderrMasked" }
        exit $code
    }
}
