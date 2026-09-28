Server 2016 兼容版使用说明

1. 将压缩包完整解压到一个新文件夹，不能只复制或覆盖 main.exe。
2. 保持 main.exe 与 _internal 文件夹在同一级目录，双击根目录中的 main.exe。
3. 不要把旧版本的 _internal 文件夹、Qt6Core.dll 或其他 DLL 混入新目录。
4. 本包使用 Qt 6.7 运行库，已避开 Windows Server 2016 缺少的 SetThreadDescription API；程序不需要目标电脑安装 Python、PyQt6、FFmpeg 或 VC++。
5. 目标电脑需为 64 位 Windows。首次运行会在 main.exe 同目录生成 setting.txt。

如果仍然无法启动，请把 main.exe 同目录下生成的 qt_load_diagnostics.txt 完整发回，不要只截错误窗口。
