#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试绿幕动画播放问题
"""
import os
import subprocess
import sys

def test_green_screen_only():
    """测试绿幕素材单独播放"""
    print("🧪 测试绿幕素材单独播放...")
    
    # 提取绿幕素材的前15秒来查看动画
    output_file = "green_screen_debug_15s.mp4"
    
    cmd = [
        'ffmpeg',
        '-i', 'DigitalHumans/1.mp4',
        '-t', '15',  # 提取前15秒
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-y', output_file
    ]
    
    print(f"📝 命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode == 0:
            print(f"✅ 绿幕素材提取成功: {output_file}")
            print(f"📊 文件大小: {os.path.getsize(output_file)} bytes")
            return True
        else:
            print(f"❌ 绿幕素材提取失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 提取异常: {e}")
        return False

def test_simple_overlay():
    """测试简单的叠加，不使用循环"""
    print("\n🧪 测试简单叠加（不循环）...")
    
    # 找一个测试视频
    test_video = None
    for root, dirs, files in os.walk('cacheCutVideo'):
        for file in files:
            if file.endswith('.mp4') and not file.startswith('1764747778_'):
                test_video = os.path.join(root, file)
                break
        if test_video:
            break
    
    if not test_video:
        print("❌ 没有找到测试视频")
        return False
    
    output_file = "simple_overlay_debug.mp4"
    
    # 简单叠加绿幕素材的前5秒
    cmd = [
        'ffmpeg',
        '-i', test_video,
        '-i', 'DigitalHumans/1.mp4',
        '-filter_complex',
        '[1:v]scale=640:480[colorkey_in];[colorkey_in]colorkey=0x00FF00:0.1:0.2[gs_ck];[gs_ck]trim=duration=5[gs_trim];[0:v][gs_trim]overlay=10:10',
        '-t', '5',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-y', output_file
    ]
    
    print(f"📝 命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode == 0:
            print(f"✅ 简单叠加成功: {output_file}")
            print(f"📊 文件大小: {os.path.getsize(output_file)} bytes")
            return True
        else:
            print(f"❌ 简单叠加失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 叠加异常: {e}")
        return False

def test_loop_issue():
    """测试循环问题"""
    print("\n🧪 测试循环问题...")
    
    # 找一个测试视频
    test_video = None
    for root, dirs, files in os.walk('cacheCutVideo'):
        for file in files:
            if file.endswith('.mp4') and not file.startswith('1764747778_'):
                test_video = os.path.join(root, file)
                break
        if test_video:
            break
    
    if not test_video:
        print("❌ 没有找到测试视频")
        return False
    
    output_file = "loop_overlay_debug.mp4"
    
    # 使用循环叠加15秒
    cmd = [
        'ffmpeg',
        '-i', test_video,
        '-i', 'DigitalHumans/1.mp4',
        '-filter_complex',
        '[1:v]scale=640:480[colorkey_in];[colorkey_in]colorkey=0x00FF00:0.1:0.2[gs_ck];[gs_ck]loop=loop=3:start=0[gs_loop];[gs_loop]trim=duration=15[gs_trim];[0:v][gs_trim]overlay=10:10',
        '-t', '15',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-y', output_file
    ]
    
    print(f"📝 命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode == 0:
            print(f"✅ 循环叠加成功: {output_file}")
            print(f"📊 文件大小: {os.path.getsize(output_file)} bytes")
            return True
        else:
            print(f"❌ 循环叠加失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 循环叠加异常: {e}")
        return False

def main():
    print("🚀 绿幕动画播放问题诊断工具")
    print("=" * 50)
    
    # 1. 测试绿幕素材单独播放
    if not test_green_screen_only():
        return False
    
    # 2. 测试简单叠加
    if not test_simple_overlay():
        return False
    
    # 3. 测试循环问题
    if not test_loop_issue():
        return False
    
    print("\n✅ 所有测试完成")
    print("💡 建议：请查看生成的视频文件，确认绿幕动画是否正常播放")
    return True

if __name__ == '__main__':
    main()
    input("\n按回车键退出...")