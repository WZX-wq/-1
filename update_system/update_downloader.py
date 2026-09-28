# 更新下载模块
import os
import requests
import hashlib
import zipfile
import shutil
import warnings
from typing import Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from .update_config import UpdateConfig

# 禁用 SSL 警告
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class UpdateDownloader:
    """更新下载器"""
    
    def __init__(self, config: UpdateConfig):
        self.config = config
        self.download_progress = 0
        self.total_size = 0
        self.downloaded_size = 0
        self.cancel_download = False
    
    def check_existing_update(self, update_info: Dict) -> bool:
        """
        检查是否存在已下载的更新文件
        返回: 是否存在完整有效的更新文件
        """
        try:
            temp_dir = os.path.join(os.getcwd(), self.config.TEMP_UPDATE_DIR)
            if not os.path.exists(temp_dir):
                return False
            
            # 检查 manifest.json 是否存在
            manifest_path = os.path.join(temp_dir, 'manifest.json')
            if not os.path.exists(manifest_path):
                return False
            
            # 检查主程序文件是否存在
            exe_path = os.path.join(temp_dir, 'main.exe')
            if not os.path.exists(exe_path):
                return False
            
            # 验证主程序文件大小（简单验证）
            expected_size = update_info.get('file_size', 0)
            if expected_size > 0:
                actual_size = os.path.getsize(exe_path)
                # 允许一定误差范围
                if actual_size < expected_size * 0.9:  # 小于期望大小的90%认为不完整
                    print(f"主程序文件不完整: 期望 {self._format_size(expected_size)}, 实际 {self._format_size(actual_size)}")
                    return False
            
            # 检查资源文件（如果有的话）
            resources = update_info.get('resources', [])
            resources_dir = os.path.join(temp_dir, 'resources')
            
            # 检查是否有任何缺失的资源文件
            missing_resources = []
            for resource in resources:
                resource_name = resource['name']
                resource_path = os.path.join(resources_dir, resource_name)
                
                if not os.path.exists(resource_path):
                    missing_resources.append(resource_name)
                    continue
                
                # 验证资源文件大小
                expected_resource_size = resource.get('size', 0)
                if expected_resource_size > 0:
                    actual_resource_size = os.path.getsize(resource_path)
                    if actual_resource_size < expected_resource_size * 0.9:
                        print(f"资源文件不完整: {resource_name}")
                        missing_resources.append(resource_name)
                        continue
            
            if missing_resources:
                print(f"检测到 {len(missing_resources)} 个缺失或不完整的资源文件: {', '.join(missing_resources)}")
                return False  # 有缺失资源文件，需要重新下载
            
            print("✅ 检测到已存在的完整更新文件，跳过下载")
            return True
            
        except Exception as e:
            print(f"检查已存在更新文件时出错: {e}")
            return False
    
    def download_update(
        self, 
        update_info: Dict,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> bool:
        """
        下载更新包
        返回: 是否成功（主程序下载成功即认为成功）
        """
        try:
            # 检查是否已存在完整的更新文件
            if self.check_existing_update(update_info):
                if progress_callback:
                    progress_callback(100, 100, "已存在完整更新文件，跳过下载")
                return True
            
            # 创建临时目录
            temp_dir = os.path.join(os.getcwd(), self.config.TEMP_UPDATE_DIR)
            os.makedirs(temp_dir, exist_ok=True)
            
            # 保存 manifest.json 到临时目录（用于后续更新版本信息）
            import json
            manifest_path = os.path.join(temp_dir, 'manifest.json')
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(update_info, f, indent=4, ensure_ascii=False)
            print(f"✅ manifest.json 已保存到临时目录")
            
            # 下载主程序
            exe_path = os.path.join(temp_dir, 'main.exe')
            
            # 检查是否已存在完整文件
            skip_exe_download = False
            if os.path.exists(exe_path):
                expected_size = update_info.get('file_size', 0)
                if expected_size > 0:
                    actual_size = os.path.getsize(exe_path)
                    if actual_size >= expected_size * 0.9:  # 大小合理
                        skip_exe_download = True
                        print(f"✅ 主程序文件已存在，跳过下载: {self._format_size(actual_size)}")
            
            if not skip_exe_download:
                success = self._download_file(
                    update_info['download_url'],
                    exe_path,
                    update_info.get('file_size', 0),
                    progress_callback,
                    "下载主程序"
                )
                
                if not success or self.cancel_download:
                    return False
            else:
                # 更新进度
                if progress_callback:
                    progress_callback(update_info.get('file_size', 0), update_info.get('file_size', 0), "主程序已存在")
            
            # 验证文件完整性
            if update_info.get('checksum'):
                if not self._verify_checksum(exe_path, update_info['checksum']):
                    actual_checksum = self._calculate_file_checksum(exe_path)
                    error_msg = f"主程序文件校验失败:\n  期望: {update_info['checksum'][:16]}...\n  实际: {actual_checksum[:16] if actual_checksum else '计算失败'}..."
                    print(error_msg)
                    if progress_callback:
                        progress_callback(0, 0, "主程序文件校验失败")
                    # 询问用户是否继续
                    print("⚠️  文件校验失败，可能是文件损坏或校验和不匹配")
                    # 为了用户体验，我们仍然允许继续安装
                    # return False
                else:
                    print("✅ 主程序文件校验成功")
            
            # 下载资源文件（即使失败也不影响主程序）
            resources = update_info.get('resources', [])
            if resources:
                print("开始下载资源文件...")
                success = self._download_resources(
                    resources,
                    temp_dir,
                    progress_callback
                )
                if not success:
                    print("⚠️  资源文件下载失败，但主程序下载成功")
                    # 不返回False，允许继续安装主程序
                    if progress_callback:
                        progress_callback(100, 100, "主程序下载完成，部分资源下载失败")
                else:
                    if progress_callback:
                        progress_callback(100, 100, "下载完成")
            else:
                if progress_callback:
                    progress_callback(100, 100, "下载完成")
            
            return True  # 主程序下载成功即可
            
        except Exception as e:
            if progress_callback:
                progress_callback(0, 0, f"下载失败: {e}")
            print(f"下载更新失败: {e}")
            return False
    
    def _download_file(
        self,
        url: str,
        save_path: str,
        expected_size: int = 0,
        progress_callback: Optional[Callable] = None,
        message: str = "下载中",
        max_retries: int = 3
    ) -> bool:
        """下载单个文件（带重试和断点续传）"""
        for attempt in range(max_retries):
            try:
                # 检查是否已有部分下载
                downloaded = 0
                if os.path.exists(save_path):
                    downloaded = os.path.getsize(save_path)
                    print(f"检测到已下载 {self._format_size(downloaded)}，继续下载...")
                
                print(f"开始下载: {url} (尝试 {attempt + 1}/{max_retries})")
                
                # 设置断点续传的headers
                headers = {}
                mode = 'wb'
                if downloaded > 0:
                    headers['Range'] = f'bytes={downloaded}-'
                    mode = 'ab'  # 追加模式
                
                # 增加超时时间
                session = requests.Session()
                
                response = session.get(
                    url,
                    headers=headers,
                    stream=True,
                    timeout=(30, 300),  # (连接超时, 读取超时)
                    verify=False
                )
                response.raise_for_status()
                
                # 获取总大小
                if 'Content-Range' in response.headers:
                    # 断点续传
                    total_size = int(response.headers['Content-Range'].split('/')[-1])
                else:
                    # 全新下载
                    total_size = int(response.headers.get('content-length', 0))
                
                if expected_size and total_size != expected_size:
                    print(f"警告: 文件大小不匹配 (期望: {expected_size}, 实际: {total_size})")
                
                # 使用更小的chunk size，更稳定
                chunk_size = 4096  # 4KB，更小更稳定
                
                with open(save_path, mode) as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if self.cancel_download:
                            print("下载已取消")
                            return False
                        
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if progress_callback and total_size:
                                progress = int((downloaded / total_size) * 100)
                                progress_callback(downloaded, total_size, message)
                
                print(f"下载成功: {save_path}")
                return True
                
            except requests.exceptions.ConnectionError as e:
                print(f"连接错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("等待10秒后重试...")
                    import time
                    time.sleep(10)  # 连接错误等待更久
                else:
                    print(f"下载失败: 已达到最大重试次数")
                    return False
                    
            except requests.exceptions.Timeout as e:
                print(f"下载超时 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("等待5秒后重试...")
                    import time
                    time.sleep(5)
                else:
                    print(f"下载失败: 已达到最大重试次数")
                    return False
                    
            except Exception as e:
                print(f"下载文件失败 {url}: {e}")
                if attempt < max_retries - 1:
                    print("等待5秒后重试...")
                    import time
                    time.sleep(5)
                else:
                    return False
        
        return False
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def _download_resources(
        self,
        resources: list,
        temp_dir: str,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """并行下载资源文件"""
        try:
            config_data = self.config.load_config()
            max_threads = config_data.get('download_threads', 4)
            
            resources_dir = os.path.join(temp_dir, 'resources')
            os.makedirs(resources_dir, exist_ok=True)
            
            # 筛选出需要下载的资源文件（缺失或不完整的）
            resources_to_download = []
            for resource in resources:
                resource_name = resource['name']
                save_path = os.path.join(resources_dir, resource_name)
                
                # 检查URL有效性
                url = resource.get('url', '')
                if not url or 'your-server.com' in url:
                    print(f"⚠️  跳过无效资源URL: {resource_name} - {url}")
                    continue
                
                # 检查文件是否已存在且完整
                skip_download = False
                if os.path.exists(save_path):
                    expected_size = resource.get('size', 0)
                    if expected_size > 0:
                        actual_size = os.path.getsize(save_path)
                        if actual_size >= expected_size * 0.9:  # 大小合理
                            skip_download = True
                            print(f"✅ 资源文件已存在，跳过下载: {resource_name} ({self._format_size(actual_size)})")
                
                if not skip_download:
                    resources_to_download.append(resource)
            
            if not resources_to_download:
                print("✅ 所有资源文件已存在或无需下载，无需下载")
                return True
            
            total_resources = len(resources_to_download)
            completed_resources = 0
            
            print(f"开始下载 {total_resources} 个资源文件...")
            print("资源列表:")
            for i, resource in enumerate(resources_to_download):
                print(f"  {i+1}. {resource['name']} ({self._format_size(resource.get('size', 0))})")
                print(f"     URL: {resource['url']}")
            
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                future_to_resource = {}
                
                for resource in resources_to_download:
                    save_path = os.path.join(resources_dir, resource['name'])
                    future = executor.submit(
                        self._download_file,
                        resource['url'],
                        save_path,
                    resource.get('size', 0),
                        None,
                        f"下载资源: {resource['name']}"
                    )
                    future_to_resource[future] = resource
                
                for future in as_completed(future_to_resource):
                    if self.cancel_download:
                        executor.shutdown(wait=False)
                        return False
                    
                    resource = future_to_resource[future]
                    try:
                        success = future.result()
                        if not success:
                            print(f"下载资源失败: {resource['name']}")
                            print(f"  URL: {resource.get('url', '未知')}")
                            return False
                        
                        completed_resources += 1
                        if progress_callback:
                            progress = int((completed_resources / total_resources) * 100)
                            progress_callback(
                                completed_resources,
                                total_resources,
                                f"下载资源 ({completed_resources}/{total_resources})"
                            )
                    except Exception as e:
                        print(f"处理资源下载失败: {e}")
                        import traceback
                        traceback.print_exc()
                        return False
            
            # 解压资源包
            extracted_count = 0
            for resource in resources_to_download:  # 只解压新下载的资源
                if resource['name'].endswith('.zip'):
                    zip_path = os.path.join(resources_dir, resource['name'])
                    if self._extract_resource(zip_path, resources_dir):
                        extracted_count += 1
            
            print(f"✅ 资源下载完成: {completed_resources}个下载, {extracted_count}个解压")
            return True
            
        except Exception as e:
            print(f"下载资源失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _extract_resource(self, zip_path: str, extract_to: str) -> bool:
        """解压资源包
        返回: 是否成功
        """
        try:
            if not os.path.exists(zip_path):
                print(f"⚠️  ZIP文件不存在，跳过解压: {os.path.basename(zip_path)}")
                return False
                
            print(f"正在解压资源: {os.path.basename(zip_path)}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            # 删除压缩包
            os.remove(zip_path)
            print(f"✅ 资源解压成功: {os.path.basename(zip_path)}")
            return True
        except zipfile.BadZipFile as e:
            print(f"❌ ZIP文件损坏: {e} - {os.path.basename(zip_path)}")
            return False
        except PermissionError as e:
            print(f"❌ 权限不足无法解压: {e} - {os.path.basename(zip_path)}")
            return False
        except Exception as e:
            print(f"❌ 解压资源失败: {e} - {os.path.basename(zip_path)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _calculate_file_checksum(self, file_path: str) -> str:
        """计算文件的SHA256校验和"""
        try:
            import hashlib
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"计算文件校验和失败: {e}")
            return ""
    
    def _verify_checksum(self, file_path: str, expected_checksum: str) -> bool:
        """验证文件校验和"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            actual_checksum = sha256_hash.hexdigest()
            return actual_checksum.lower() == expected_checksum.lower()
            
        except Exception as e:
            print(f"校验文件失败: {e}")
            return False
    
    def cancel(self):
        """取消下载"""
        self.cancel_download = True
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            temp_dir = os.path.join(os.getcwd(), self.config.TEMP_UPDATE_DIR)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"清理临时文件失败: {e}")
