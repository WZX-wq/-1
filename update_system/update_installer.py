# 更新安装模块
import os
import sys
import shutil
import subprocess
import time
import stat
import ctypes
from typing import Optional, Callable
from datetime import datetime
from .update_config import UpdateConfig


class UpdateInstaller:
    """更新安装器"""
    
    def __init__(self, config: UpdateConfig):
        self.config = config
        self.backup_created = False
        self.backup_path = None
    
    def install_update(self, progress_callback: Optional[Callable] = None) -> tuple:
        """
        安装更新
        返回: (是否成功, 错误消息)
        """
        try:
            temp_dir = os.path.join(os.getcwd(), self.config.TEMP_UPDATE_DIR)
            if not os.path.exists(temp_dir):
                error_msg = "更新文件不存在，请先下载更新包"
                print(error_msg)
                return False, error_msg
            
            # 1. 备份当前版本
            if progress_callback:
                progress_callback(10, "创建备份...")
            
            config_data = self.config.load_config()
            if config_data.get('backup_before_update', True):
                success, error = self._create_backup()
                if not success:
                    error_msg = f"创建备份失败：{error}"
                    print(error_msg)
                    return False, error_msg
            
            # 2. 替换主程序
            if progress_callback:
                progress_callback(30, "准备替换主程序...")
            
            success, error = self._prepare_exe_update(temp_dir)
            if not success:
                self._restore_from_backup()
                error_msg = f"准备更新失败：{error}"
                print(error_msg)
                return False, error_msg
            
            # 3. 更新资源文件
            if progress_callback:
                progress_callback(50, "更新资源文件...")
            
            success, error = self._update_resources(temp_dir)
            if not success:
                self._restore_from_backup()
                error_msg = f"更新资源失败：{error}"
                print(error_msg)
                return False, error_msg
            
            # 4. 更新配置文件
            if progress_callback:
                progress_callback(70, "更新配置文件...")
            
            self._update_config_files(temp_dir)
            
            # 5. 更新版本信息
            if progress_callback:
                progress_callback(80, "更新版本信息...")
            
            # 获取manifest.json中的新版本信息
            manifest_path = os.path.join(temp_dir, 'manifest.json')
            if os.path.exists(manifest_path):
                try:
                    import json
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    
                    # 更新版本信息
                    new_version_info = {
                        'version': manifest.get('version', self.config.CURRENT_VERSION),
                        'build_date': manifest.get('build_date', ''),
                        'description': manifest.get('description', '')
                    }
                    self._update_version_info(new_version_info)
                    print(f"✅ 版本信息已更新为: {new_version_info['version']}")
                    
                except Exception as e:
                    print(f"⚠️  更新版本信息失败: {e}")
            
            # 6. 创建更新脚本
            if progress_callback:
                progress_callback(90, "准备重启...")
            
            self._create_update_script(temp_dir)
            
            if progress_callback:
                progress_callback(100, "更新准备完成")
            
            return True, "更新安装成功，准备重启"
            
        except Exception as e:
            error_msg = f"安装更新异常：{str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            self._restore_from_backup()
            return False, error_msg
    
    def _get_main_executable(self) -> str:
        """获取主程序路径"""
        # 如果是打包后的 exe，sys.executable 就是主程序
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            return sys.executable
        else:
            # 开发环境，使用 main.exe 或 main.py 所在目录
            return os.path.join(os.getcwd(), 'main.exe')
    
    def _create_backup(self) -> tuple:
        """创建备份
        返回: (是否成功, 错误消息)
        """
        try:
            backup_dir = os.path.join(os.getcwd(), self.config.BACKUP_DIR)
            os.makedirs(backup_dir, exist_ok=True)
            
            # 使用时间戳创建备份文件夹
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_path = os.path.join(backup_dir, f"backup_{timestamp}")
            os.makedirs(self.backup_path, exist_ok=True)
            
            # 备份主程序
            current_exe = self._get_main_executable()
            if os.path.exists(current_exe):
                shutil.copy2(current_exe, os.path.join(self.backup_path, 'main.exe'))
                print(f"✅ 已备份主程序: {os.path.basename(current_exe)}")
            
            # 备份资源文件夹
            for folder in self.config.RESOURCE_FOLDERS:
                src_folder = os.path.join(os.getcwd(), folder)
                if os.path.exists(src_folder):
                    dst_folder = os.path.join(self.backup_path, folder)
                    shutil.copytree(src_folder, dst_folder, dirs_exist_ok=True)
            
            # 备份配置文件
            for config_file in self.config.CONFIG_FILES:
                src_file = os.path.join(os.getcwd(), config_file)
                if os.path.exists(src_file):
                    shutil.copy2(src_file, os.path.join(self.backup_path, config_file))
            
            self.backup_created = True
            print(f"备份创建成功: {self.backup_path}")
            return True, "备份成功"
            
        except PermissionError as e:
            error_msg = f"权限不足，请以管理员身份运行程序 ({str(e)})"
            print(f"创建备份失败: {error_msg}")
            return False, error_msg
        except OSError as e:
            error_msg = f"磁盘空间不足或IO错误 ({str(e)})"
            print(f"创建备份失败: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = str(e)
            print(f"创建备份失败: {error_msg}")
            return False, error_msg
    
    def _prepare_exe_update(self, temp_dir: str) -> tuple:
        """准备更新主程序
        返回: (是否成功, 错误消息)
        """
        try:
            new_exe = os.path.join(temp_dir, 'main.exe')
            if not os.path.exists(new_exe):
                error_msg = "新版本程序文件不存在，下载可能未完成"
                print(error_msg)
                return False, error_msg
            
            # 验证文件大小
            file_size = os.path.getsize(new_exe)
            if file_size < 1024:  # 小于1KB，可能损坏
                error_msg = f"新程序文件大小异常：{file_size} 字节，文件可能已损坏，请重新下载"
                print(error_msg)
                return False, error_msg
            
            print(f"✅ 新程序验证通过，大小: {self._format_size(file_size)}")
            return True, "验证成功"
            
        except Exception as e:
            error_msg = str(e)
            print(f"准备更新主程序失败: {error_msg}")
            return False, error_msg
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def _remove_readonly(self, func, path, exc_info):
        """删除只读文件的错误处理函数"""
        if not os.access(path, os.W_OK):
            # 尝试修改文件权限
            os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
            func(path)
        else:
            raise
    
    def _force_remove_file(self, file_path: str) -> bool:
        """强制删除文件（处理只读、占用等问题）"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                if not os.path.exists(file_path):
                    return True
                
                # 尝试删除文件
                os.remove(file_path)
                return True
                
            except PermissionError:
                # 修改文件权限后重试
                try:
                    os.chmod(file_path, stat.S_IWUSR | stat.S_IRUSR)
                    os.remove(file_path)
                    return True
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"删除文件失败（尝试 {attempt + 1}/{max_retries}）: {file_path}")
                        time.sleep(0.5)  # 等待文件释放
                    else:
                        print(f"无法删除文件: {file_path} - {e}")
                        return False
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                else:
                    print(f"删除文件失败: {file_path} - {e}")
                    return False
        
        return False
    
    def _force_remove_dir(self, dir_path: str) -> bool:
        """强制删除目录（处理只读、占用等问题）"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if not os.path.exists(dir_path):
                    return True
                
                # 使用自定义错误处理函数删除目录
                shutil.rmtree(dir_path, onerror=self._remove_readonly)
                return True
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"删除目录失败（尝试 {attempt + 1}/{max_retries}）: {dir_path}")
                    time.sleep(1)
                else:
                    print(f"无法删除目录: {dir_path} - {e}")
                    print("提示: 请手动删除此目录或以管理员身份运行程序")
                    return False
        
        return False
    
    def _update_resources(self, temp_dir: str) -> tuple:
        """更新资源文件
        返回: (是否成功, 错误消息)
        """
        try:
            resources_dir = os.path.join(temp_dir, 'resources')
            if not os.path.exists(resources_dir):
                # 没有资源更新
                print("✅ 无需更新资源文件")
                return True, "无需更新资源"
            
            failed_items = []  # 记录失败的项
            success_items = []  # 记录成功的项
            
            # 更新资源文件夹
            for item in os.listdir(resources_dir):
                src_path = os.path.join(resources_dir, item)
                dst_path = os.path.join(os.getcwd(), item)
                
                try:
                    if os.path.isdir(src_path):
                        # 如果是文件夹，先删除旧的再复制新的
                        if os.path.exists(dst_path):
                            print(f"正在删除旧资源文件夹: {item}...")
                            if not self._force_remove_dir(dst_path):
                                error = f"无法删除旧文件夹（文件可能被占用）"
                                print(f"⚠️  跳过资源文件夹: {item} ({error})")
                                failed_items.append(f"{item}: {error}")
                                continue
                        
                        # 复制新文件夹
                        print(f"正在复制新资源文件夹: {item}...")
                        shutil.copytree(src_path, dst_path)
                        print(f"✅ 已更新资源文件夹: {item}")
                        success_items.append(item)
                        
                    elif os.path.isfile(src_path):
                        # 如果是文件，先删除旧的再复制
                        if os.path.exists(dst_path):
                            if not self._force_remove_file(dst_path):
                                error = f"无法删除旧文件（文件可能被占用）"
                                print(f"⚠️  跳过资源文件: {item} ({error})")
                                failed_items.append(f"{item}: {error}")
                                continue
                        
                        shutil.copy2(src_path, dst_path)
                        print(f"✅ 已更新资源文件: {item}")
                        success_items.append(item)
                        
                except Exception as e:
                    error = str(e)
                    print(f"⚠️  更新资源失败: {item} - {error}")
                    failed_items.append(f"{item}: {error}")
                    # 继续处理其他资源，不中断整个更新过程
                    continue
            
            # 判断更新结果
            if failed_items:
                # 有失败项，但采用部分成功策略
                error_msg = f"部分资源更新失败（{len(failed_items)}个失败，{len(success_items)}个成功）：" + "; ".join(failed_items[:3])  # 只显示前3个错误
                if len(failed_items) > 3:
                    error_msg += f" ...还有{len(failed_items)-3}个失败"
                print(f"⚠️  {error_msg}")
                # 如果超过一半失败，返回失败
                if len(failed_items) > len(success_items):
                    return False, error_msg
                else:
                    # 部分成功，继续
                    return True, f"部分资源更新成功（{len(success_items)}个成功，{len(failed_items)}个失败）"
            
            print(f"✅ 所有资源更新成功（共{len(success_items)}个）")
            return True, "资源更新成功"
            
        except Exception as e:
            error_msg = str(e)
            print(f"更新资源文件失败: {error_msg}")
            return False, error_msg
    
    def _update_version_info(self, new_version_info: dict):
        """更新版本信息"""
        try:
            # 更新 version.json
            self.config.save_version_info(new_version_info)
            
            # 更新 update_config.py 中的 CURRENT_VERSION
            config_py_path = os.path.join(
                os.path.dirname(__file__),
                'update_config.py'
            )
            
            if os.path.exists(config_py_path):
                with open(config_py_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 替换 CURRENT_VERSION
                import re
                new_content = re.sub(
                    r'CURRENT_VERSION\s*=\s*["\'].*?["\']',
                    f'CURRENT_VERSION = "{new_version_info["version"]}"',
                    content
                )
                
                with open(config_py_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"✅ update_config.py 中的版本号已更新")
                    
        except Exception as e:
            print(f"⚠️  更新版本信息失败: {e}")
    
    def _update_config_files(self, temp_dir: str):
        """更新配置文件"""
        try:
            # 检查临时目录中是否有配置文件
            config_files_dir = temp_dir
            
            # 更新配置文件列表中的文件
            updated_files = []
            skipped_files = []
            
            for config_file in self.config.CONFIG_FILES:
                src_path = os.path.join(config_files_dir, config_file)
                dst_path = os.path.join(os.getcwd(), config_file)
                
                # 检查源文件是否存在
                if not os.path.exists(src_path):
                    skipped_files.append(f"{config_file} (源文件不存在)")
                    continue
                
                # 检查目标文件是否存在
                if not os.path.exists(dst_path):
                    # 目标文件不存在，直接复制
                    shutil.copy2(src_path, dst_path)
                    updated_files.append(f"{config_file} (新增)")
                    print(f"✅ 已添加配置文件: {config_file}")
                else:
                    # 目标文件存在，比较内容决定是否更新
                    # 对于ftp_config.json等重要配置文件，总是更新
                    if config_file == "ftp_config.json":
                        # 备份原文件
                        backup_path = dst_path + ".backup"
                        if os.path.exists(dst_path):
                            shutil.copy2(dst_path, backup_path)
                        
                        # 更新文件
                        shutil.copy2(src_path, dst_path)
                        updated_files.append(f"{config_file} (强制更新)")
                        print(f"✅ 已更新配置文件: {config_file}")
                    else:
                        # 其他配置文件，如果内容不同则更新
                        with open(src_path, 'r', encoding='utf-8') as f1, open(dst_path, 'r', encoding='utf-8') as f2:
                            src_content = f1.read()
                            dst_content = f2.read()
                        
                        if src_content != dst_content:
                            # 备份原文件
                            backup_path = dst_path + ".backup"
                            if os.path.exists(dst_path):
                                shutil.copy2(dst_path, backup_path)
                            
                            # 更新文件
                            shutil.copy2(src_path, dst_path)
                            updated_files.append(f"{config_file} (内容更新)")
                            print(f"✅ 已更新配置文件: {config_file}")
                        else:
                            skipped_files.append(f"{config_file} (内容相同)")
            
            # 输出更新结果
            if updated_files:
                print(f"✅ 配置文件更新完成: {len(updated_files)}个文件已更新")
                for file_info in updated_files:
                    print(f"   - {file_info}")
            
            if skipped_files:
                print(f"ℹ️  跳过配置文件: {len(skipped_files)}个文件未更新")
                for file_info in skipped_files:
                    print(f"   - {file_info}")
                    
        except Exception as e:
            print(f"⚠️  更新配置文件失败: {e}")
    
    def _create_update_script(self, temp_dir: str):
        """创建更新脚本"""
        try:
            new_exe = os.path.join(temp_dir, 'main.exe')
            current_exe = self._get_main_executable()  # 使用新方法获取主程序路径
            current_dir = os.getcwd()
            
            print(f"📝 更新脚本信息:")
            print(f"   新程序: {new_exe}")
            print(f"   当前程序: {current_exe}")
            print(f"   工作目录: {current_dir}")
            
            # 获取manifest.json中的版本信息
            manifest_path = os.path.join(temp_dir, 'manifest.json')
            version_info = {
                'version': '1.0.0',
                'build_date': '',
                'description': ''
            }
            
            if os.path.exists(manifest_path):
                try:
                    import json
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    version_info = {
                        'version': manifest.get('version', '1.0.0'),
                        'build_date': manifest.get('build_date', ''),
                        'description': manifest.get('description', '')
                    }
                except Exception as e:
                    print(f"读取manifest.json失败: {e}")
            
            # 创建批处理脚本来替换程序
            script_content = f"""@echo off
chcp 65001 >nul
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 🔄 正在应用更新...
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

timeout /t 3 /nobreak > nul

echo 🗑️  删除旧程序...
set "RETRY_COUNT=0"
:retry
del /F /Q "{current_exe}" 2>nul
if exist "{current_exe}" (
    set /a RETRY_COUNT+=1
    echo 重试次数: %RETRY_COUNT%
    if %RETRY_COUNT% GTR 10 (
        echo ❌ 删除旧程序超时，可能需要手动删除
        echo 请手动删除: "{current_exe}"
        echo 然后运行: "{current_exe}"
        pause
        exit /b 1
    )
    timeout /t 1 /nobreak > nul
    goto retry
)

echo ✅ 旧程序已删除
echo.

echo 📦 复制新程序...
move /Y "{new_exe}" "{current_exe}"
if %errorlevel% equ 0 (
    echo ✅ 新程序已安装
) else (
    echo ❌ 程序更新失败
    echo 可能需要管理员权限或文件被占用
    echo 请以管理员身份运行程序或重启电脑后手动运行
    pause
    exit /b 1
)

echo.
echo 📝 更新版本信息...
(
echo {{
echo     "version": "{version_info['version']}",
echo     "build_date": "{version_info['build_date']}",
echo     "description": "{version_info['description']}"
echo }}
) > "{current_dir}\{self.config.VERSION_FILE}"
echo ✅ 版本信息已更新
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ✅ 更新完成！
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 🚀 正在启动程序...
timeout /t 2 /nobreak > nul

cd /d "{current_dir}"
"{current_exe}"

echo.
echo 🧹 清理临时文件...
timeout /t 3 /nobreak > nul
rmdir /S /Q "{temp_dir}" 2>nul

echo ✅ 清理完成
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 🎉 更新成功！程序已重启
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

del "%~f0"
"""
            
            script_path = os.path.join(temp_dir, 'update.bat')
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            print(f"✅ 更新脚本已创建: {script_path}")
            
        except Exception as e:
            print(f"创建更新脚本失败: {e}")
    
    def _is_admin(self) -> bool:
        """检查是否有管理员权限"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def _restore_from_backup(self) -> bool:
        """从备份恢复"""
        if not self.backup_created or not self.backup_path:
            print("⚠️  没有可用的备份")
            return False
        
        try:
            print("正在从备份恢复...")
            
            # 恢复主程序
            backup_exe = os.path.join(self.backup_path, 'main.exe')
            current_exe = self._get_main_executable()  # 使用新方法
            
            # 检查是否需要管理员权限
            if os.path.exists(backup_exe):
                try:
                    if os.path.exists(current_exe):
                        self._force_remove_file(current_exe)
                    shutil.copy2(backup_exe, current_exe)
                    print(f"✅ 主程序已恢复: {os.path.basename(current_exe)}")
                except PermissionError:
                    if not self._is_admin():
                        print("⚠️  需要管理员权限才能恢复主程序")
                        print("提示: 请以管理员身份运行程序")
                    raise
            
            # 恢复资源文件夹
            for folder in self.config.RESOURCE_FOLDERS:
                backup_folder = os.path.join(self.backup_path, folder)
                if os.path.exists(backup_folder):
                    dst_folder = os.path.join(os.getcwd(), folder)
                    try:
                        if os.path.exists(dst_folder):
                            self._force_remove_dir(dst_folder)
                        shutil.copytree(backup_folder, dst_folder)
                        print(f"✅ 资源文件夹已恢复: {folder}")
                    except Exception as e:
                        print(f"⚠️  恢复资源文件夹失败: {folder} - {e}")
                        continue
            
            # 恢复配置文件
            for config_file in self.config.CONFIG_FILES:
                backup_file = os.path.join(self.backup_path, config_file)
                if os.path.exists(backup_file):
                    try:
                        dst_file = os.path.join(os.getcwd(), config_file)
                        if os.path.exists(dst_file):
                            self._force_remove_file(dst_file)
                        shutil.copy2(backup_file, dst_file)
                        print(f"✅ 配置文件已恢复: {config_file}")
                    except Exception as e:
                        print(f"⚠️  恢复配置文件失败: {config_file} - {e}")
                        continue
            
            print("✅ 从备份恢复成功")
            return True
            
        except Exception as e:
            print(f"❌ 从备份恢复失败: {e}")
            if not self._is_admin():
                print("\n💡 建议: 以管理员身份运行程序以避免权限问题")
            return False
    
    def execute_update(self):
        """执行更新（重启程序）"""
        try:
            temp_dir = os.path.join(os.getcwd(), self.config.TEMP_UPDATE_DIR)
            script_path = os.path.join(temp_dir, 'update.bat')
            
            if os.path.exists(script_path):
                print(f"🚀 正在启动更新脚本: {script_path}")
                
                # 启动更新脚本
                subprocess.Popen(
                    script_path,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # 等待一小段时间确保脚本启动
                time.sleep(0.5)
                
                print("✅ 更新脚本已启动，程序即将退出...")
                
                # 退出当前程序
                sys.exit(0)
            else:
                print(f"❌ 更新脚本不存在: {script_path}")
                
        except Exception as e:
            print(f"执行更新失败: {e}")
    
    def cleanup_old_backups(self, keep_count: int = 3):
        """清理旧备份，保留最新的几个"""
        try:
            backup_dir = os.path.join(os.getcwd(), self.config.BACKUP_DIR)
            if not os.path.exists(backup_dir):
                return
            
            # 获取所有备份文件夹
            backups = []
            for item in os.listdir(backup_dir):
                item_path = os.path.join(backup_dir, item)
                if os.path.isdir(item_path) and item.startswith('backup_'):
                    backups.append((item_path, os.path.getctime(item_path)))
            
            # 按时间排序
            backups.sort(key=lambda x: x[1], reverse=True)
            
            # 删除旧备份
            for backup_path, _ in backups[keep_count:]:
                shutil.rmtree(backup_path)
                print(f"已删除旧备份: {backup_path}")
                
        except Exception as e:
            print(f"清理旧备份失败: {e}")
