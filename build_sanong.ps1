[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$PythonExe = Join-Path $ProjectRoot '.build-python312-official\python.exe'
$DistRoot = if ($env:SANONG_DIST_ROOT) {
    [System.IO.Path]::GetFullPath($env:SANONG_DIST_ROOT)
} else {
    Join-Path $ProjectRoot 'dist_sanong'
}
$BuildRoot = if ($env:SANONG_BUILD_ROOT) {
    [System.IO.Path]::GetFullPath($env:SANONG_BUILD_ROOT)
} else {
    Join-Path $ProjectRoot 'build_sanong'
}
$ReleaseDir = Join-Path $DistRoot '三农视频生成'

foreach ($RequiredPath in @(
    $PythonExe,
    (Join-Path $ProjectRoot 'sanong_runner.spec'),
    (Join-Path $ProjectRoot 'sanong_runner.json'),
    (Join-Path $ProjectRoot 'setting.txt'),
    (Join-Path $ProjectRoot '三农视频生成使用说明.txt'),
    (Join-Path $ProjectRoot 'tb.ico'),
    (Join-Path $ProjectRoot 'soft_pic'),
    (Join-Path $ProjectRoot 'video_model_set'),
    (Join-Path $ProjectRoot 'cacheMusic1'),
    (Join-Path $ProjectRoot 'cacheAFRVideo'),
    (Join-Path $ProjectRoot '.legacy-pyqt67\PyQt6\Qt6\bin\Qt6Core.dll'),
    (Join-Path $ProjectRoot '.legacy-pyqt67\PyQt6\Qt6\bin\Qt6Gui.dll'),
    (Join-Path $ProjectRoot '.legacy-pyqt67\PyQt6\Qt6\bin\Qt6Widgets.dll'),
    (Join-Path $ProjectRoot '.legacy-server2016-runtime\icu.dll'),
    (Join-Path $ProjectRoot '.legacy-server2016-runtime\icuin.dll'),
    (Join-Path $ProjectRoot '.legacy-server2016-runtime\icuuc.dll'),
    (Join-Path $ProjectRoot 'ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe'),
    (Join-Path $ProjectRoot 'ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe')
)) {
    if (-not (Test-Path -LiteralPath $RequiredPath)) {
        throw "缺少构建输入: $RequiredPath"
    }
}

foreach ($Target in @($DistRoot, $BuildRoot)) {
    $FullTarget = [System.IO.Path]::GetFullPath($Target)
    if (-not $FullTarget.StartsWith($ProjectRoot + [System.IO.Path]::DirectorySeparatorChar)) {
        throw "拒绝清理项目目录外的路径: $FullTarget"
    }
    if (Test-Path -LiteralPath $FullTarget) {
        Remove-Item -LiteralPath $FullTarget -Recurse -Force
    }
}

Push-Location $ProjectRoot
try {
    & $PythonExe -m PyInstaller --noconfirm --clean `
        --distpath $DistRoot --workpath $BuildRoot `
        (Join-Path $ProjectRoot 'sanong_runner.spec')
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller 构建失败，退出码: $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Copy-Item -LiteralPath (Join-Path $ProjectRoot 'sanong_runner.json') -Destination $ReleaseDir -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'setting.txt') -Destination $ReleaseDir -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot '三农视频生成使用说明.txt') -Destination $ReleaseDir -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'tb.ico') -Destination $ReleaseDir -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'soft_pic') -Destination $ReleaseDir -Recurse -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'video_model_set') -Destination $ReleaseDir -Recurse -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'cacheMusic1') -Destination $ReleaseDir -Recurse -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'cacheAFRVideo') -Destination $ReleaseDir -Recurse -Force

Write-Host "构建完成: $ReleaseDir"
