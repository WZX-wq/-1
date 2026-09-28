#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复OpenCV导入错误的解决方案 - 版本2
"""

import sys
import os

def fix_opencv_recursive_import():
    """修复OpenCV递归导入错误"""
    
    print("=== 修复OpenCV递归导入错误 ===")
    
    # 移除有问题的OpenCV路径（Roaming目录中的）
    problematic_path = 'C:\\Users\\Administrator\\AppData\\Roaming\\Python\\Python38\\site-packages\\cv2'
    
    if problematic_path in sys.path:
        sys.path.remove(problematic_path)
        print(f"✅ 已移除有问题的OpenCV路径: {problematic_path}")
    
    # 确保使用正确的OpenCV路径
    correct_path = 'C:\\Program Files\\python\\lib\\site-packages'
    if correct_path not in sys.path:
        sys.path.insert(0, correct_path)
        print(f"✅ 已添加正确的OpenCV路径: {correct_path}")
    
    # 尝试导入OpenCV
    try:
        import cv2
        print("✅ OpenCV导入成功！")
        print(f"OpenCV版本: {cv2.__version__}")
        return True
    except ImportError as e:
        print(f"❌ OpenCV导入失败: {e}")
        return False

def test_main_import():
    """测试main.py的导入"""
    
    print("\n=== 测试main.py导入 ===")
    
    try:
        # 模拟main.py的导入过程
        import sys
        import os
        
        # 先修复OpenCV导入
        fix_opencv_recursive_import()
        
        # 尝试导入database_tool.video_load_tool
        from database_tool.video_load_tool import get_videos_by_keyword
        print("✅ database_tool.video_load_tool导入成功！")
        
        # 尝试导入其他关键模块
        import cv2
        import numpy as np
        print("✅ 所有关键模块导入成功！")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入测试失败: {e}")
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
import sys
import os

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
    print("请使用 'python main_fixed.py' 来运行程序")

def main():
    """主函数"""
    
    print("开始修复OpenCV导入问题...")
    
    # 修复OpenCV导入
    if fix_opencv_recursive_import():
        print("\n✅ OpenCV导入修复成功！")
        
        # 测试main.py导入
        if test_main_import():
            print("\n🎉 所有导入测试通过！")
            print("现在可以正常运行程序了")
            
            # 创建修复后的入口文件
            create_fixed_main()
        else:
            print("\n⚠️ 导入测试失败，可能需要进一步修复")
    else:
        print("\n❌ OpenCV导入修复失败")
        print("建议重新安装OpenCV:")
        print("1. pip uninstall opencv-python")
        print("2. pip install opencv-python")

if __name__ == "__main__":
    main()