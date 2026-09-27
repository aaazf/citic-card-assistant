@echo off
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo Creating backend environment...
  python -m venv .venv
  if errorlevel 1 goto error
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto error
)
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
goto end
:error
echo.
echo Backend setup failed. Check that Python and network access are available.
pause
:end
