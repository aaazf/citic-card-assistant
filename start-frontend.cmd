@echo off
cd /d "%~dp0frontend"
if not exist "node_modules\.bin\vite.CMD" (
  echo Installing frontend dependencies...
  call corepack pnpm install
  if errorlevel 1 goto error
)
call "node_modules\.bin\vite.CMD" --host 127.0.0.1
goto end
:error
echo.
echo Frontend setup failed. Check that Node.js and network access are available.
pause
:end
