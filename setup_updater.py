# 更新系统配置向导
import json
import os


def setup_update_system():
    """更新系统配置向导"""
    print("=" * 70)
    print(" 更新系统配置向导 ".center(70, "="))
    print("=" * 70)
    
    print("\n此向导将帮助您配置自动更新系统\n")
    
    # 1. 基本配置
    print("【步骤 1/4】基本配置")
    print("-" * 70)
    
    version = input("当前版本号 [1.0.0]: ").strip() or "1.0.0"
    description = input("项目描述 [批量AI视频剪辑工具]: ").strip() or "批量AI视频剪辑工具"
    
    # 2. 更新服务器配置
    print("\n【步骤 2/4】更新服务器配置")
    print("-" * 70)
    print("1. 自定义服务器")
    print("2. GitHub Releases")
    
    choice = input("选择更新方式 [1]: ").strip() or "1"
    
    if choice == "1":
        server_url = input("更新服务器地址 (例如: https://your-server.com/api): ").strip()
        github_repo = ""
    else:
        server_url = ""
        github_repo = input("GitHub 仓库 (例如: username/repo): ").strip()
    
    # 3. 更新策略
    print("\n【步骤 3/4】更新策略")
    print("-" * 70)
    
    auto_check = input("启用自动检查更新? [Y/n]: ").strip().lower() != 'n'
    auto_download = input("启用自动下载更新? [y/N]: ").strip().lower() == 'y'
    
    print("\n更新通道:")
    print("1. stable - 稳定版")
    print("2. beta - 测试版")
    print("3. dev - 开发版")
    channel_choice = input("选择更新通道 [1]: ").strip() or "1"
    channel_map = {"1": "stable", "2": "beta", "3": "dev"}
    update_channel = channel_map.get(channel_choice, "stable")
    
    check_interval = input("检查更新间隔（小时） [24]: ").strip() or "24"
    
    # 4. 高级选项
    print("\n【步骤 4/4】高级选项")
    print("-" * 70)
    
    download_threads = input("下载线程数 [4]: ").strip() or "4"
    backup_before_update = input("更新前创建备份? [Y/n]: ").strip().lower() != 'n'
    
    # 生成配置文件
    print("\n" + "=" * 70)
    print(" 生成配置文件 ".center(70, "="))
    print("=" * 70)
    
    # update_config.json
    config = {
        "auto_check_update": auto_check,
        "auto_download_update": auto_download,
        "update_channel": update_channel,
        "check_interval_hours": int(check_interval),
        "download_threads": int(download_threads),
        "enable_incremental_update": True,
        "backup_before_update": backup_before_update
    }
    
    config_path = "update_config.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(f"✓ 已创建: {config_path}")
    
    # version.json
    version_info = {
        "version": version,
        "build_date": "",
        "description": description
    }
    
    version_path = "version.json"
    with open(version_path, 'w', encoding='utf-8') as f:
        json.dump(version_info, f, indent=4, ensure_ascii=False)
    print(f"✓ 已创建: {version_path}")
    
    # 更新 update_config.py
    if server_url or github_repo:
        update_config_py = "update_system/update_config.py"
        if os.path.exists(update_config_py):
            with open(update_config_py, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if server_url:
                content = content.replace(
                    'UPDATE_SERVER_URL = "https://your-update-server.com/api"',
                    f'UPDATE_SERVER_URL = "{server_url}"'
                )
            
            if github_repo:
                content = content.replace(
                    'GITHUB_REPO = "your-username/batchAiCutter"',
                    f'GITHUB_REPO = "{github_repo}"'
                )
                content = content.replace(
                    'CURRENT_VERSION = "1.0.0"',
                    f'CURRENT_VERSION = "{version}"'
                )
            
            with open(update_config_py, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 已更新: {update_config_py}")
    
    # 显示摘要
    print("\n" + "=" * 70)
    print(" 配置完成 ".center(70, "="))
    print("=" * 70)
    
    print("\n配置摘要:")
    print(f"  版本: {version}")
    print(f"  更新方式: {'自定义服务器' if server_url else 'GitHub Releases'}")
    print(f"  自动检查: {'是' if auto_check else '否'}")
    print(f"  自动下载: {'是' if auto_download else '否'}")
    print(f"  更新通道: {update_channel}")
    print(f"  检查间隔: {check_interval} 小时")
    
    print("\n后续步骤:")
    print("1. 根据 README.md 配置服务器或 GitHub Releases")
    print("2. 在 main.py 中集成更新系统（参考 example_integration.py）")
    print("3. 使用 create_update_package.py 创建更新包")
    print("4. 打包程序: pyinstaller main.spec")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        setup_update_system()
    except KeyboardInterrupt:
        print("\n\n配置已取消")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
