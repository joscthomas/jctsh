# rotate.ps1 -- shim: the rotation runner is tos/rotate.py (CARD-0372), which replaced
# this file's old dry-run-only skeleton (that's `rotate.py plan <target>` now).
#
#   powershell tos/rotate.ps1 plan data-pipeline-api-key
#   powershell tos/rotate.ps1 start data-pipeline-api-key
#
# Every argument is passed through unchanged; `python tos/rotate.py --help` lists the
# commands. Uses the `py` launcher when present (the usual Windows install), else python.
$py = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
& $py (Join-Path $PSScriptRoot 'rotate.py') @args
exit $LASTEXITCODE
