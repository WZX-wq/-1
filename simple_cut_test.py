#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的视频截取测试
"""

import os
import sys
import subprocess

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def simple_test():
    """简单测试视频截取功能"""
    print("🔍 查找测试视频...")
    
    # 查找测试视频
    cache_dir = "cacheVideo"
    if not os.path.exists(cache_dir):
        print("❌ cacheVideo 目录不存在")
        return False
    
    video_files = [f for f in os.listdir(cache_dir) if f.endswith('.mp4')]
    if not video_files:
        print("❌ 没有找到测试视频")
        return False
    
    test_video = os.path.join(cache_dir, video_files[0])
    print(f"🎬 使用视频: {test_video}")
    
    # 测试截取5秒
    print("🔄 测试截取5秒...")
    
    # 导入函数
    try:
        from database_tool.video_load_tool import cut_video_by_audio_length, get_video_duration
    except Exception as e:
        print(f"❌ 导入函数失败: {e}")
        return False
    
    # 获取原视频时长
    try:
        duration = get_video_duration(test_video)
        if not duration:
            print("❌ 无法获取视频时长")
            return False
        print(f"📊 原视频时长: {duration:.2f}秒")
    except Exception as e:
        print(f"❌ 获取时长失败: {e}")
        return False
    
    # 截取视频
    try:
        cut_path = cut_video_by_audio_length(test_video, "test_123", 5.0)
        if not cut_path:
            print("❌ 截取失败")
            return False
        
        if not os.path.exists(cut_path):
            print(f"❌ 截取文件不存在: {cut_path}")
            return False
        
        print(f"✅ 截取成功: {cut_path}")
        
        # 验证时长
        cut_duration = get_video_duration(cut_path)
        if cut_duration:
            print(f"📊 截取后时长: {cut_duration:.2f}秒")
            
            error = abs(cut_duration - 5.0)
            if error <= 0.5:
                print(f"✅ 时长精度良好 (误差: {error:.2f}秒)")
            else:
                print(f"⚠️ 时长误差较大: {error:.2f}秒")
        else:
            print("⚠️ 无法获取截取后时长")
        
        # 清理测试文件
        try:
            os.remove(cut_path)
            print("🧹 清理完成")
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"❌ 截取过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始简单测试...")
    success = simple_test()
    if success:
        print("✅ 测试通过！")
    else:
        print("❌ 测试失败！")