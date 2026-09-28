# 资源包创建工具
import zipfile
import os
import json
import hashlib
from datetime import datetime


class ResourcePackager:
    """资源打包工具"""
    
    def __init__(self, version: str):
        self.version = version
        self.output_dir = f"release_{version}"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def create_resource_pack(self, source_folder: str, pack_name: str) -> dict:
        """
        创建资源包
        返回: 资源包信息字典
        """
        if not os.path.exists(source_folder):
            print(f"源文件夹不存在: {source_folder}")
            return None
        
        zip_filename = f"{pack_name}_v{self.version}.zip"
        zip_path = os.path.join(self.output_dir, zip_filename)
        
        print(f"正在打包: {source_folder} -> {zip_filename}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 首先添加ftp_config.json文件（如果存在）
            ftp_config_path = "ftp_config.json"
            if os.path.exists(ftp_config_path):
                zipf.write(ftp_config_path, "ftp_config.json")
                print(f"  添加: ftp_config.json")
            
            # 然后添加资源文件夹内容
            for root, dirs, files in os.walk(source_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 保持文件夹结构
                    arcname = os.path.join(
                        os.path.basename(source_folder),
                        os.path.relpath(file_path, source_folder)
                    )
                    zipf.write(file_path, arcname)
                    print(f"  添加: {arcname}")
        
        # 计算文件信息
        file_size = os.path.getsize(zip_path)
        checksum = self.calculate_sha256(zip_path)
        
        resource_info = {
            "name": zip_filename,
            "url": f"http://123.162.188.146:3000/resources/{zip_filename}",
            "size": file_size,
            "checksum": checksum,
            "type": pack_name
        }
        
        print(f"✓ 打包完成: {zip_filename}")
        print(f"  大小: {self._format_size(file_size)}")
        print(f"  SHA256: {checksum}")
        
        return resource_info
    
    @staticmethod
    def calculate_sha256(file_path: str) -> str:
        """计算文件SHA256校验和"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def create_manifest(
        self,
        exe_path: str,
        resources: list,
        changelog: list,
        description: str = ""
    ) -> str:
        """创建更新清单"""
        if not os.path.exists(exe_path):
            print(f"主程序不存在: {exe_path}")
            return None
        
        # 计算主程序信息
        file_size = os.path.getsize(exe_path)
        checksum = self.calculate_sha256(exe_path)
        
        # 添加ftp_config.json到资源列表（如果存在）
        ftp_config_path = "ftp_config.json"
        if os.path.exists(ftp_config_path):
            # 复制ftp_config.json到输出目录
            import shutil
            dest_ftp_config = os.path.join(self.output_dir, "ftp_config.json")
            shutil.copy2(ftp_config_path, dest_ftp_config)
            print(f"✓ 已复制: ftp_config.json -> {dest_ftp_config}")
            
            # 计算ftp_config.json的信息
            ftp_file_size = os.path.getsize(ftp_config_path)
            ftp_checksum = self.calculate_sha256(ftp_config_path)
            
            ftp_config_info = {
                "name": "ftp_config.json",
                "url": f"http://123.162.188.146:3000/downloads/ftp_config.json",
                "size": ftp_file_size,
                "checksum": ftp_checksum,
                "type": "config"
            }
            
            # 添加到资源列表
            resources.append(ftp_config_info)
        
        manifest = {
            "version": self.version,
            "build_date": datetime.now().isoformat(),
            "description": description or f"版本 {self.version}",
            "changelog": changelog,
            "download_url": f"http://123.162.188.146:3000/downloads/main_v{self.version}.exe",
            "file_size": file_size,
            "checksum": checksum,
            "min_version": "1.0.0",
            "force_update": False,
            "resources": resources
        }
        
        manifest_path = os.path.join(self.output_dir, "manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=4, ensure_ascii=False)
        
        print(f"\n✓ 清单文件已创建: {manifest_path}")
        print(f"  主程序大小: {self._format_size(file_size)}")
        print(f"  主程序SHA256: {checksum}")
        
        return manifest_path


def main():
    """主函数"""
    print("=" * 60)
    print(" 资源包创建工具 ".center(60, "="))
    print("=" * 60)
    
    # 版本号
    version = input("\n请输入版本号 (例如: 1.1.0): ").strip()
    if not version:
        print("版本号不能为空")
        return
    
    packager = ResourcePackager(version)
    
    # 需要打包的资源文件夹
    resource_folders = {
        "music": "cacheMusic",
        "music1": "cacheMusic1",
        "music2": "cacheMusic2",
        "material": "material",
        "gif_material": "gifMaterial",
        "tourist_pictures": "touristPictures",
        "end_credits": "endCredits"
    }
    
    print("\n可打包的资源文件夹:")
    for idx, (name, folder) in enumerate(resource_folders.items(), 1):
        exists = "✓" if os.path.exists(folder) else "✗"
        print(f"  {idx}. [{exists}] {name} ({folder})")
    
    # 选择要打包的资源
    selected = input("\n请选择要打包的资源 (多个用逗号分隔, 0=全部): ").strip()
    
    resources_info = []
    
    if selected == "0":
        # 打包所有资源
        for name, folder in resource_folders.items():
            info = packager.create_resource_pack(folder, name)
            if info:
                resources_info.append(info)
    else:
        # 打包选中的资源
        indices = [int(x.strip()) for x in selected.split(",") if x.strip().isdigit()]
        items = list(resource_folders.items())
        for idx in indices:
            if 1 <= idx <= len(items):
                name, folder = items[idx - 1]
                info = packager.create_resource_pack(folder, name)
                if info:
                    resources_info.append(info)
    
    # 创建清单文件
    print("\n" + "=" * 60)
    print(" 创建更新清单 ".center(60, "="))
    print("=" * 60)
    
    exe_path = input("\n主程序路径 (默认: main.exe): ").strip() or "main.exe"
    
    print("\n请输入更新内容 (每行一条, 空行结束):")
    changelog = []
    while True:
        line = input("  > ").strip()
        if not line:
            break
        changelog.append(line)
    
    description = input("\n版本描述 (可选): ").strip()
    
    manifest_path = packager.create_manifest(
        exe_path,
        resources_info,
        changelog,
        description
    )
    
    if manifest_path:
        print("\n" + "=" * 60)
        print(" 打包完成 ".center(60, "="))
        print("=" * 60)
        print(f"\n输出目录: {packager.output_dir}")
        print(f"资源包数量: {len(resources_info)}")
        print("\n请执行以下步骤:")
        print("1. 将主程序复制到输出目录")
        print("2. 上传所有文件到服务器")
        print("3. 更新服务器上的 manifest.json")
        print("4. 或创建 GitHub Release 并上传文件")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
