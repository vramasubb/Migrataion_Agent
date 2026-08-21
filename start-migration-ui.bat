@echo off
echo.
echo ========================================
echo   Test Migration Agent UI — Launcher
echo ========================================
echo.

echo [1/2] Starting backend server (port 3001)...
start "Migration Backend" cmd /k "cd /d "%~dp0migration-backend" && node server.js"

echo Waiting for backend to start...
timeout /t 2 /nobreak >nul

echo [2/2] Starting React UI (port 5173)...
start "Migration UI" cmd /k "cd /d "%~dp0migration-ui" && npm run dev"

echo.
echo ✅ Both services starting...
echo.
echo    UI:      http://localhost:5173
echo    Backend: http://localhost:3001
echo.
echo Open http://localhost:5173 in your browser.
pause
