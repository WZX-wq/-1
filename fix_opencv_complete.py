#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完全修复OpenCV导入错误的解决方案
"""

import sys
import os
import shutil

def backup_and_fix_opencv():
    """备份并修复有问题的OpenCV安装"""
    
    print("=== 备份并修复OpenCV安装 ===")
    
    # 有问题的OpenCV路径
    problematic_path = 'C:\\Users\\Administrator\\AppData\\Roaming\\Python\\Python38\\site-packages\\cv2'
    
    # 备份路径
    backup_path = 'C:\\Users\\Administrator\\AppData\\Roaming\\Python\\Python38\\site-packages\\cv2_backup'
    
    if os.path.exists(problematic_path):
        # 备份有问题的OpenCV
        if os.path.exists(backup_path):
            shutil.rmtree(backup_path)
        shutil.move(problematic_path, backup_path)
        print(f"✅ 已备份有问题的OpenCV到: {backup_path}")
    
    # 从系统路径中移除有问题的路径
    if problematic_path in sys.path:
        sys.path.remove(problematic_path)
        print(f"✅ 已从系统路径中移除: {problematic_path}")

def check_opencv_installation():
    """检查OpenCV安装情况"""
    
    print("=== 检查OpenCV安装情况 ===")
    
    # 检查正确的OpenCV路径
    correct_path = 'C:\\Program Files\\python\\lib\\site-packages\\cv2'
    if os.path.exists(correct_path):
        print(f"✅ 找到正确的OpenCV安装: {correct_path}")
        
        # 检查cv2目录内容
        try:
            files = os.listdir(correct_path)
            print(f"   OpenCV目录包含: {files[:5]}...")  # 只显示前5个文件
            return True
        except:
            print(f"   ⚠️ 无法读取OpenCV目录内容")
            return False
    else:
        print(f"❌ 未找到正确的OpenCV安装")
        return False

def test_opencv_import():
    """测试OpenCV导入"""
    
    print("\n=== 测试OpenCV导入 ===")
    
    try:
        import cv2
        print("✅ OpenCV导入成功！")
        print(f"OpenCV版本: {cv2.__version__}")
        return True
    except ImportError as e:
        print(f"❌ OpenCV导入失败: {e}")
        return False

def test_database_tool_import():
    """测试database_tool导入"""
    
    print("\n=== 测试database_tool导入 ===")
    
    try:
        from database_tool.video_load_tool import get_videos_by_keyword
        print("✅ database_tool.video_load_tool导入成功！")
        return True
    except Exception as e:
        print(f"❌ database_tool导入失败: {e}")
        return False

def create_fixed_main():
    """创建修复后的main.py入口文件"""
    
    fixed_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复OpenCV导入问题后的主程序入口
"""

import sys
import os

# 修复OpenCV导入问题
# 移除有问题的OpenCV路径
problematic_path = 'C:\\\\Users\\\\Administrator\\\\AppData\\\\Roaming\\\\Python\\\\Python38\\\\site-packages\\\\cv2'
if problematic_path in sys.path:
    sys.path.remove(problematic_path)

# 确保使用正确的OpenCV路径
correct_path = 'C:\\\\Program Files\\\\python\\\\lib\\\\site-packages'
if correct_path not in sys.path:
    sys.path.insert(0, correct_path)

# 现在导入主程序
from main import main

if __name__ == "__main__":
    main()
'''
    
    with open('main_fixed.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("✅ 已创建修复后的入口文件: main_fixed.py")

def reinstall_opencv():
    """重新安装OpenCV"""
    
    print("\n=== 重新安装OpenCV ===")
    
    try:
        # 卸载OpenCV
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "opencv-python", "-y"], check=True)
        print("✅ 已卸载OpenCV")
        
        # 安装OpenCV
        subprocess.run([sys.executable, "-m", "pip", "install", "opencv-python"], check=True)
        print("✅ 已重新安装OpenCV")
        
        return True
    except Exception as e:
        print(f"❌ 重新安装OpenCV失败: {e}")
        return False

def main():
    """主函数"""
    
    print("开始完全修复OpenCV导入问题...")
    
    # 检查OpenCV安装
    if not check_opencv_installation():
        print("❌ 未找到正确的OpenCV安装")
        return
    
    # 备份并修复OpenCV
    backup_and_fix_opencv()
    
    # 测试OpenCV导入
    if test_opencv_import():
        print("\n✅ OpenCV导入修复成功！")
        
        # 测试database_tool导入
        if test_database_tool_import():
            print("\n🎉 所有导入测试通过！")
            print("现在可以正常运行程序了")
            
            # 创建修复后的入口文件
            create_fixed_main()
            
            print("\n📋 使用说明:")
            print("1. 使用 'python main_fixed.py' 来运行程序")
            print("2. 或者直接在PyCharm中运行 main_fixed.py")
        else:
            print("\n⚠️ database_tool导入失败，可能需要进一步修复")
    else:
        print("\n❌ OpenCV导入修复失败")
        print("\n🔄 尝试重新安装OpenCV...")
        
        if reinstall_opencv():
            print("\n✅ OpenCV重新安装成功！")
            print("请重新运行此脚本来测试导入")
        else:
            print("\n❌ 重新安装失败，请手动执行:")
            print("1. pip uninstall opencv-python -y")
            print("2. pip install opencv-python")

if __name__ == "__main__":
    main()