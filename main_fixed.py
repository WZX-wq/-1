#!/usr/bin/env python3
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

# 现在直接运行主程序
if __name__ == "__main__":
    # 导入并运行main.py
    from main import setup_ffmpeg_path, BatchAICutter
    from PyQt6.QtWidgets import QApplication
    
    # ffmpeg设置到系统环境
    setup_ffmpeg_path()
    app = QApplication(sys.argv)
    window = BatchAICutter()
    window.show()
    sys.exit(app.exec())