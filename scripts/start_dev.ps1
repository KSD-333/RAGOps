# RAGOps Full-Stack Dev Launcher (PowerShell)
$rootDir = Split-Path -Parent $PSScriptRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Starting RAGOps Backend and React Web Dashboard  " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Backend API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "React UI URL:     http://localhost:5173" -ForegroundColor Green
Write-Host ""

# Launch React in a separate terminal process
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$rootDir\react'; npm run dev"

# Launch Backend in current terminal
Set-Location "$rootDir"
python -m ragops.cli.main serve --host 0.0.0.0 --port 8000 --reload

