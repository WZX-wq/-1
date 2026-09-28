#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复OpenCV导入错误的临时解决方案
"""

import sys
import os

def fix_opencv_import():
    """修复OpenCV导入错误"""
    
    # 检查并移除有问题的OpenCV路径
    problematic_paths = []
    for path in sys.path:
        if 'cv2' in path and 'Roaming' in path:
            problematic_paths.append(path)
    
    for path in problematic_paths:
        if path in sys.path:
            sys.path.remove(path)
            print(f"已移除有问题的OpenCV路径: {path}")
    
    # 尝试导入OpenCV
    try:
        import cv2
        print("✅ OpenCV导入成功！")
        print(f"OpenCV版本: {cv2.__version__}")
        return True
    except ImportError as e:
        print(f"❌ OpenCV导入失败: {e}")
        return False

def check_opencv_installation():
    """检查OpenCV安装情况"""
    
    # 检查系统路径中的OpenCV
    print("=== 检查OpenCV安装情况 ===")
    
    # 检查site-packages中的OpenCV
    for path in sys.path:
        if 'site-packages' in path:
            cv2_path = os.path.join(path, 'cv2')
            if os.path.exists(cv2_path):
                print(f"✅ 找到OpenCV安装: {cv2_path}")
                
                # 检查cv2目录内容
                try:
                    files = os.listdir(cv2_path)
                    print(f"   OpenCV目录包含: {files[:5]}...")  # 只显示前5个文件
                except:
                    print(f"   ⚠️ 无法读取OpenCV目录内容")
    
    # 检查是否有重复安装
    cv2_paths = [p for p in sys.path if 'cv2' in p]
    if len(cv2_paths) > 1:
        print(f"⚠️ 发现多个OpenCV路径: {cv2_paths}")
    
    return len(cv2_paths) > 0

def main():
    """主函数"""
    
    print("开始修复OpenCV导入问题...")
    
    # 检查安装情况
    if not check_opencv_installation():
        print("❌ 未找到OpenCV安装，请先安装OpenCV")
        return
    
    # 尝试修复导入
    if fix_opencv_import():
        print("\n✅ OpenCV导入问题已修复！")
        print("现在可以正常运行main.py了")
    else:
        print("\n❌ 修复失败，可能需要重新安装OpenCV")
        print("建议执行: pip uninstall opencv-python")
        print("然后执行: pip install opencv-python")

if __name__ == "__main__":
    main()