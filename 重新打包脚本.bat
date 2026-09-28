@echo off
chcp 65001 >nul
echo ========================================
echo    清理并重新打包 Server 2016 兼容版 main.exe
echo ========================================
echo.

:: 步骤 1: 清理旧的打包文件
echo [1/3] 清理旧的打包文件...
if exist "build" (
    echo    删除 build 目录...
    rmdir /s /q build
)
if exist "dist" (
    echo    删除 dist 目录...
    rmdir /s /q dist
)
echo    ✓ 清理完成
echo.

:: 步骤 2: 检查兼容 spec
echo [2/3] 检查 main_legacy_compat.spec 配置...
if not exist "main_legacy_compat.spec" (
    echo    ✗ 错误: main_legacy_compat.spec 文件不存在！
    pause
    exit /b 1
)

:: 检查是否已禁用 UPX
findstr /C:"upx=False" main_legacy_compat.spec >nul
if %errorlevel% equ 0 (
    echo    ✓ UPX 已禁用（推荐配置）
) else (
    echo    ⚠ 警告: UPX 未禁用，可能导致 ucrtbase.dll 错误
    echo    建议修改 main_legacy_compat.spec 中的 upx=False
    echo.
    choice /C YN /M "是否继续打包"
    if errorlevel 2 exit /b 0
)
echo.

:: 步骤 3: 开始打包
echo [3/3] 开始打包...
echo    执行命令: pyinstaller main_legacy_compat.spec
echo.
pyinstaller main_legacy_compat.spec

:: 检查打包结果
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo    ✓ 打包成功！
    echo ========================================
    echo.
    echo 生成的文件位置:
    if exist "dist\main.exe" (
        echo    - 单文件模式: dist\main.exe
        for %%A in ("dist\main.exe") do echo    - 文件大小: %%~zA 字节
    ) else if exist "dist\main" (
        echo    - 目录模式: dist\main\
        dir /s "dist\main"
    )
    echo.
    echo 下一步操作:
    echo    1. 测试运行 dist\main.exe
    echo    2. 如果出现 ucrtbase.dll 错误，请查看 ucrtbase.dll错误修复指南.md
    echo    3. 准备分发包（建议包含 VC++ 运行库）
    echo.
) else (
    echo.
    echo ========================================
    echo    ✗ 打包失败！
    echo ========================================
    echo.
    echo 可能的原因:
    echo    1. 缺少依赖库
    echo    2. main_legacy_compat.spec 配置错误
    echo    3. PyInstaller 版本过低
    echo.
    echo 建议操作:
    echo    1. 检查上面的错误信息
    echo    2. 运行: pip install --upgrade pyinstaller
    echo    3. 检查 main_legacy_compat.spec 语法
    echo.
)

pause
