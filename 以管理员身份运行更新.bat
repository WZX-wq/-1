@echo off
chcp 65001 >nul
echo ============================================================
echo 🔐 以管理员身份运行更新程序
echo ============================================================
echo.

:: 检查是否已经是管理员
net session >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ 已具有管理员权限
    echo.
    goto :run_update
) else (
    echo ⚠️  需要管理员权限
    echo 正在请求管理员权限...
    echo.
    
    :: 请求管理员权限并重新运行
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:run_update
echo 📦 启动更新程序...
echo.

:: 启动主程序
if exist "main.exe" (
    start "" "main.exe"
    echo ✅ 更新程序已启动
) else (
    echo ❌ 找不到 main.exe
    echo 请确保此脚本与 main.exe 在同一目录
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✅ 完成
echo ============================================================
pause
