# 更新检查模块
import requests
import json
import warnings
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from .update_config import UpdateConfig

# 禁用 SSL 警告
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class UpdateChecker:
    """更新检查器"""
    
    def __init__(self, config: UpdateConfig):
        self.config = config
        self.last_check_time = None
        self.latest_version_info = None
    
    def should_check_update(self) -> bool:
        """判断是否应该检查更新"""
        if not self.last_check_time:
            return True
        
        config_data = self.config.load_config()
        interval_hours = config_data.get('check_interval_hours', 24)
        
        time_diff = datetime.now() - self.last_check_time
        return time_diff > timedelta(hours=interval_hours)
    
    def check_for_updates(self, force: bool = False) -> Tuple[bool, Optional[Dict]]:
        """
        检查是否有更新
        返回: (是否有更新, 更新信息字典)
        """
        if not force and not self.should_check_update():
            return False, None
        
        try:
            # 方式1: 从自定义服务器检查
            update_info = self._check_from_server()
            
            # 方式2: 从 GitHub Releases 检查（备用）
            if not update_info:
                update_info = self._check_from_github()
            
            self.last_check_time = datetime.now()
            
            if update_info:
                # 使用从version.json读取的实际版本，而不是硬编码版本
                version_info = self.config.get_version_info()
                current_version = version_info['version']
                latest_version = update_info.get('version', '')
                
                if self.config.compare_versions(latest_version, current_version) > 0:
                    self.latest_version_info = update_info
                    return True, update_info
            
            return False, None
            
        except Exception as e:
            print(f"检查更新失败: {e}")
            return False, None
    
    def _check_from_server(self) -> Optional[Dict]:
        """从自定义服务器检查更新"""
        try:
            manifest_url = self.config.get_update_manifest_url()
            print(f"📡 正在从自定义服务器检查更新: {manifest_url}")
            response = requests.get(manifest_url, timeout=5, verify=False)
            response.raise_for_status()
            
            manifest = response.json()
            print(f"✅ 从自定义服务器获取更新信息成功: 版本 {manifest.get('version', '未知')}"),
            return self._parse_manifest(manifest)
            
        except Exception as e:
            print(f"❌ 从自定义服务器检查更新失败: {e}")
            return None
    
    def _check_from_github(self) -> Optional[Dict]:
        """从 GitHub Releases 检查更新"""
        try:
            print(f"📡 正在从GitHub检查更新: {self.config.GITHUB_API_URL}")
            response = requests.get(
                self.config.GITHUB_API_URL,
                headers={'Accept': 'application/vnd.github.v3+json'},
                timeout=5,
                verify=False  # 禁用SSL验证
            )
            response.raise_for_status()
            
            release_data = response.json()
            print(f"✅ 从GitHub获取更新信息成功: 版本 {release_data.get('tag_name', '未知')}")
            return self._parse_github_release(release_data)
            
        except Exception as e:
            print(f"❌ 从 GitHub 检查更新失败: {e}")
            return None
    
    def _parse_manifest(self, manifest: Dict) -> Dict:
        """解析更新清单"""
        return {
            'version': manifest.get('version', ''),
            'build_date': manifest.get('build_date', ''),
            'description': manifest.get('description', ''),
            'changelog': manifest.get('changelog', []),
            'download_url': manifest.get('download_url', ''),
            'file_size': manifest.get('file_size', 0),
            'checksum': manifest.get('checksum', ''),
            'min_version': manifest.get('min_version', ''),
            'force_update': manifest.get('force_update', False),
            'resources': manifest.get('resources', []),  # 需要更新的资源列表
        }
    
    def _parse_github_release(self, release: Dict) -> Optional[Dict]:
        """解析 GitHub Release 数据"""
        assets = release.get('assets', [])
        exe_asset = None
        resources_assets = []
        
        # 查找主程序和资源包
        for asset in assets:
            name = asset.get('name', '')
            if name.endswith('.exe'):
                exe_asset = asset
            elif name.startswith('resources_'):
                resources_assets.append(asset)
        
        if not exe_asset:
            return None
        
        return {
            'version': release.get('tag_name', '').lstrip('v'),
            'build_date': release.get('published_at', ''),
            'description': release.get('name', ''),
            'changelog': release.get('body', '').split('\n'),
            'download_url': exe_asset.get('browser_download_url', ''),
            'file_size': exe_asset.get('size', 0),
            'checksum': '',  # GitHub 不提供，需要额外获取
            'min_version': '',
            'force_update': False,
            'resources': [
                {
                    'name': asset.get('name', ''),
                    'url': asset.get('browser_download_url', ''),
                    'size': asset.get('size', 0)
                }
                for asset in resources_assets
            ]
        }
    
    def get_update_summary(self) -> str:
        """获取更新摘要信息"""
        if not self.latest_version_info:
            return "暂无更新信息"
        
        info = self.latest_version_info
        summary = f"""
版本: {info.get('version', 'Unknown')}
发布日期: {info.get('build_date', 'Unknown')}
大小: {self._format_size(info.get('file_size', 0))}

更新内容:
{chr(10).join('- ' + item for item in info.get('changelog', []))}
"""
        return summary
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
