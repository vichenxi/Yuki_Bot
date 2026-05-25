@echo off
chcp 65001 >nul
pushd "%~dp0"
set "ROOT=%CD%"
popd

echo ============================================
echo  yukibot 启动
echo ============================================
echo 目录: %ROOT%
echo.

REM 检查 config.json
if not exist "%ROOT%\config.json" (
  echo [错误] 未找到 config.json
  echo 请先运行 setup.bat 完成初始化。
  pause
  exit /b 1
)

REM 启动 lt_daemon（Life Tick 计时器）
echo 启动 lt_daemon...
start "" /b pythonw "%ROOT%\core\lt_daemon.py"

REM 启动 tg_daemon（Telegram 消息监听）
echo 启动 tg_daemon...
start "" /b pythonw "%ROOT%\core\tg_daemon.py"

REM 启动 claude_monitor（自动调用 claude 处理 pending 文件）
echo 启动 claude_monitor...
start "" /b pythonw "%ROOT%\core\claude_monitor.py"

echo.
echo 所有守护进程已在后台启动。
echo 日志文件位于: %ROOT%\*.log
echo 关闭 bot: 结束 pythonw 进程，或运行 stop.bat
echo.
pause
