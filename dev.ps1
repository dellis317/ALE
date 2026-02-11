# Start both ALE backend and frontend dev servers.
# Usage: .\dev.ps1

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Start backend in a new PowerShell window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$projectRoot'; uvicorn web.backend.app.main:app --reload --port 8000"

# Start frontend in the current window
Set-Location "$projectRoot\web\frontend"
npm run dev
