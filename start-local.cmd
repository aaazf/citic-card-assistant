@echo off
cd /d "%~dp0"
start "Knowledge Backend" cmd /k ""%~dp0start-backend.cmd""
start "Knowledge Frontend" cmd /k ""%~dp0start-frontend.cmd""
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5173"
