# 更新配置模块
import json
import os
from typing import Dict, List, Optional


class UpdateConfig:
    """更新系统配置管理"""
    
    # 当前版本号（语义化版本）
    CURRENT_VERSION = "1.6.0"
    
    # 更新服务器地址
    UPDATE_SERVER_URL = "https://llpjcwl0628.github.io/batchAiCutter"
    
    # GitHub Release 地址（可选）
    GITHUB_REPO = "llpjcwl0628/batchAiCutter"
    GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    
    # 本地配置文件路径
    CONFIG_FILE = "update_config.json"
    VERSION_FILE = "version.json"
    
    # 需要更新的资源文件夹列表
    RESOURCE_FOLDERS = [
        "cacheMusic",
        "cacheMusic1", 
        "cacheMusic2",
        "material",
        "gifMaterial",
        "soft_pic",
        "touristPictures",
        "endCredits",
        "coverPicMaterial"
    ]
    
    # 需要更新的配置文件
    CONFIG_FILES = [
        "setting.txt",
        "blank.ass",
        "white.png",
        "ftp_config.json"
    ]
    
    # 临时更新目录
    TEMP_UPDATE_DIR = "temp_update"
    BACKUP_DIR = "backup"
    
    def __init__(self):
        self.config_path = os.path.join(os.getcwd(), self.CONFIG_FILE)
        self.version_path = os.path.join(os.getcwd(), self.VERSION_FILE)
        self.load_config()
    
    def load_config(self) -> Dict:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self.get_default_config()
        return self.get_default_config()
    
    def save_config(self, config: Dict):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "auto_check_update": True,
            "auto_download_update": False,
            "update_channel": "stable",  # stable, beta, dev
            "check_interval_hours": 24,
            "download_threads": 4,
            "enable_incremental_update": True,
            "backup_before_update": True
        }
    
    def get_version_info(self) -> Dict:
        """获取版本信息"""
        version_info = {
            "version": self.CURRENT_VERSION,
            "build_date": "",
            "description": "批量AI视频剪辑工具"
        }
        
        if os.path.exists(self.version_path):
            try:
                with open(self.version_path, 'r', encoding='utf-8') as f:
                    saved_info = json.load(f)
                    version_info.update(saved_info)
            except Exception as e:
                print(f"读取版本信息失败: {e}")
        
        return version_info
    
    def save_version_info(self, version_info: Dict):
        """保存版本信息"""
        try:
            with open(self.version_path, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存版本信息失败: {e}")
    
    @staticmethod
    def compare_versions(v1: str, v2: str) -> int:
        """
        比较版本号
        返回: 1 if v1 > v2, -1 if v1 < v2, 0 if equal
        """
        def normalize(v):
            return [int(x) for x in v.split('.')]
        
        try:
            v1_parts = normalize(v1)
            v2_parts = normalize(v2)
            
            # 补齐长度
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts += [0] * (max_len - len(v1_parts))
            v2_parts += [0] * (max_len - len(v2_parts))
            
            for i in range(max_len):
                if v1_parts[i] > v2_parts[i]:
                    return 1
                elif v1_parts[i] < v2_parts[i]:
                    return -1
            return 0
        except Exception as e:
            print(f"版本比较失败: {e}")
            return 0
    
    def get_update_manifest_url(self) -> str:
        """获取更新清单URL"""
        return f"{self.UPDATE_SERVER_URL}/manifest.json"
    
    def get_resource_update_url(self, resource_name: str) -> str:
        """获取资源更新URL"""
        return f"{self.UPDATE_SERVER_URL}/resources/{resource_name}"
