@echo off
TITLE RAGOps Full-Stack Dev Launcher
echo ===================================================
echo   Starting RAGOps Backend and React Web Dashboard
echo ===================================================
echo.

set ROOT_DIR=%~dp0..
cd /d "%ROOT_DIR%"

echo [1/2] Starting React Vite Dashboard in new window...
start "RAGOps React Dashboard" cmd /k "cd /d "%ROOT_DIR%\react" && npm run dev"

echo [2/2] Starting RAGOps FastAPI Backend on port 8000...
echo FastAPI Docs: http://127.0.0.1:8000/docs
echo React UI:     http://localhost:5173
echo.
python -m ragops.cli.main serve --host 0.0.0.0 --port 8000 --reload
pause

