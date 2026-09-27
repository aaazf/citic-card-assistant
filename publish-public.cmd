@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================
echo    中信银行信用卡智能咨询助手 - 公网测试发布
echo ============================================
echo.

if not exist "frontend\dist\index.html" (
  echo [1/4] 构建前端产物...
  pushd frontend
  call corepack pnpm install
  if errorlevel 1 goto error
  call corepack pnpm build
  if errorlevel 1 goto error
  popd
) else (
  echo [1/4] 已存在前端构建产物，跳过构建。
)

if not exist "backend\.venv\Scripts\python.exe" (
  echo [2/4] 创建后端环境...
  pushd backend
  python -m venv .venv
  if errorlevel 1 goto error
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto error
  popd
) else (
  echo [2/4] 后端环境已存在。
)

if not exist "tools\cloudflared.exe" (
  echo [!] 缺少 tools\cloudflared.exe，无法建立公网隧道。
  goto error
)

echo [3/4] 检查后端...
curl.exe -s -o NUL -m 5 http://127.0.0.1:8000/api/v1/health
if errorlevel 1 (
  echo       后端未运行，正在启动...
  start "Knowledge Backend" cmd /k ""%~dp0start-backend.cmd""
  timeout /t 8 /nobreak >nul
) else (
  echo       后端已在 8000 端口运行，直接复用。
)

echo [4/4] 建立公网隧道...
echo.
echo     稍等片刻，在下面的输出里找到这一行：
echo         https://xxxx-xxxx-xxxx.trycloudflare.com
echo     把这个网址发给测试人员即可。
echo.
echo     关闭本窗口 = 停止对外服务。
echo.
"%~dp0tools\cloudflared.exe" tunnel --url http://127.0.0.1:8000 --no-autoupdate
goto end

:error
echo.
echo 发布失败，请检查上面的错误信息。
pause
:end
endlocal
