# Script de arranque rápido para EPIA (Backend en :8010 + Frontend en :5173)
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  🏋️  Iniciando EPIA — Entrenador Personal de IA" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  • Backend API : http://127.0.0.1:8010 (Docs: /docs)" -ForegroundColor Gray
Write-Host "  • Frontend UI : http://localhost:5173" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\backend'; .\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8010"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\frontend'; npm run dev"

