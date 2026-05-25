@echo off
chcp 65001 >nul
pushd "%~dp0"
set "ROOT=%CD%"
popd

echo ============================================
echo  yukibot 初始化配置
echo ============================================
echo 安装目录: %ROOT%
echo.

REM 将 prompts 中的占位路径替换为实际安装路径
REM 占位符: YUKIBOT_ROOT_PLACEHOLDER
powershell -Command ^
  "$root = '%ROOT%'.Replace('\', '/'); " ^
  "$files = Get-ChildItem '%ROOT%\prompts\*.txt'; " ^
  "foreach ($f in $files) { " ^
    "$c = [IO.File]::ReadAllText($f.FullName, [Text.Encoding]::UTF8); " ^
    "$c2 = $c.Replace('YUKIBOT_ROOT_PLACEHOLDER', $root); " ^
    "if ($c2 -ne $c) { [IO.File]::WriteAllText($f.FullName, $c2, [Text.Encoding]::UTF8); Write-Host ('已更新: ' + $f.Name) } " ^
  "}"

REM 检查 config.json 是否存在，若不存在则从 example 复制
if not exist "%ROOT%\config.json" (
  if exist "%ROOT%\config.example.json" (
    copy "%ROOT%\config.example.json" "%ROOT%\config.json" >nul
    echo 已创建 config.json（从 config.example.json 复制）
    echo 请编辑 config.json 填入您的 bot_token 和 API key。
  )
) else (
  echo config.json 已存在，跳过。
)

REM 创建必要目录
if not exist "%ROOT%\data\logs" mkdir "%ROOT%\data\logs"
if not exist "%ROOT%\assets\voice_models" mkdir "%ROOT%\assets\voice_models"
if not exist "%ROOT%\assets\voice_ref" mkdir "%ROOT%\assets\voice_ref"

echo.
echo 初始化完成！
echo 下一步：编辑 config.json，然后双击 scripts\start.bat 启动 bot。
echo.
pause
