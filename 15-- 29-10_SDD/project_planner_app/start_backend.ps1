$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\backend"
if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created backend\.env. Edit it and set your PostgreSQL password, then run this script again." -ForegroundColor Yellow
    exit 1
}
if (!(Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "Virtual environment not found. Create it with: py -3.14 -m venv .venv" -ForegroundColor Yellow
    exit 1
}
. .\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
