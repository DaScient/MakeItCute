Param()
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\..")

if (-Not (Test-Path ".venv")) {
    python -m venv .venv
}

$activate = ".\.venv\Scripts\Activate.ps1"
& $activate

python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "✅ Virtual env ready. Activate later with: .\.venv\Scripts\Activate.ps1"
