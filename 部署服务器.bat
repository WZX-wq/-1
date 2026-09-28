@echo off
chcp 65001 >nul
echo ============================================================
echo 🚀 BatchAiCutter 更新服务器部署脚本
echo ============================================================
echo.

:: 设置变量
set SERVER_DIR=G:\batch-server
set SOURCE_DIR=%~dp0

echo 📁 服务器目录: %SERVER_DIR%
echo 📁 源文件目录: %SOURCE_DIR%
echo.

:: 检查服务器目录是否存在
if not exist "%SERVER_DIR%" (
    echo ❌ 服务器目录不存在: %SERVER_DIR%
    echo 正在创建目录...
    mkdir "%SERVER_DIR%"
    mkdir "%SERVER_DIR%\downloads"
    mkdir "%SERVER_DIR%\resources"
    echo ✅ 目录创建成功
    echo.
)

:: 备份原文件
echo 📦 备份原文件...
if exist "%SERVER_DIR%\server.js" (
    copy "%SERVER_DIR%\server.js" "%SERVER_DIR%\server.js.backup.%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%" >nul
    echo ✅ 已备份 server.js
)

if exist "%SERVER_DIR%\package.json" (
    copy "%SERVER_DIR%\package.json" "%SERVER_DIR%\package.json.backup" >nul
    echo ✅ 已备份 package.json
)
echo.

:: 复制新文件
echo 📋 复制新文件...
copy "%SOURCE_DIR%server.js" "%SERVER_DIR%\server.js" >nul
if %errorlevel% equ 0 (
    echo ✅ server.js 复制成功
) else (
    echo ❌ server.js 复制失败
    pause
    exit /b 1
)

copy "%SOURCE_DIR%package.json" "%SERVER_DIR%\package.json" >nul
if %errorlevel% equ 0 (
    echo ✅ package.json 复制成功
) else (
    echo ❌ package.json 复制失败
    pause
    exit /b 1
)
echo.

:: 检查 Node.js
echo 🔍 检查 Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未安装 Node.js
    echo 请先安装 Node.js: https://nodejs.org/
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
    echo ✅ Node.js 版本: %NODE_VERSION%
)
echo.

:: 安装依赖
echo 📦 安装依赖...
cd /d "%SERVER_DIR%"
call npm install
if %errorlevel% neq 0 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)
echo ✅ 依赖安装成功
echo.

:: 检查必要文件
echo 🔍 检查必要文件...
if not exist "%SERVER_DIR%\manifest.json" (
    echo ⚠️  警告: manifest.json 不存在
    echo 请手动创建或从 release_1.1.0 目录复制
)

if not exist "%SERVER_DIR%\downloads" (
    mkdir "%SERVER_DIR%\downloads"
    echo ✅ 创建 downloads 目录
)

if not exist "%SERVER_DIR%\resources" (
    mkdir "%SERVER_DIR%\resources"
    echo ✅ 创建 resources 目录
)
echo.

:: 显示下一步操作
echo ============================================================
echo ✅ 部署完成！
echo ============================================================
echo.
echo 📋 下一步操作:
echo.
echo 1. 将更新文件放入相应目录:
echo    - 主程序: %SERVER_DIR%\downloads\
echo    - 资源包: %SERVER_DIR%\resources\
echo.
echo 2. 创建/更新 manifest.json:
echo    - 位置: %SERVER_DIR%\manifest.json
echo    - 参考: %SOURCE_DIR%manifest.json编写指南.md
echo.
echo 3. 启动服务器:
echo    cd %SERVER_DIR%
echo    npm start
echo.
echo 4. 或使用 PM2 (推荐):
echo    npm install -g pm2
echo    pm2 start server.js --name batch-server
echo    pm2 save
echo.
echo ============================================================
echo.

pause
