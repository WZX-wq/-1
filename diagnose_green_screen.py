#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绿幕叠加问题诊断工具
"""
import os
import subprocess
import sys

def diagnose_ffmpeg():
    """诊断FFmpeg环境"""
    print("🔍 诊断FFmpeg环境...")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        print("✅ FFmpeg可正常执行")
        print(f"📊 版本信息: {result.stdout.split()[2]}")
        return True
    except Exception as e:
        print(f"❌ FFmpeg执行失败: {e}")
        return False

def diagnose_videos():
    """诊断视频文件"""
    print("\n🔍 诊断视频文件...")
    
    current_dir = os.getcwd()
    video_folder = os.path.join(current_dir, 'DigitalHumans')
    
    if not os.path.exists(video_folder):
        print(f"❌ 绿幕文件夹不存在: {video_folder}")
        return False
    
    green_screens = []
    for file in os.listdir(video_folder):
        if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
            green_screens.append(os.path.join(video_folder, file))
    
    if not green_screens:
        print(f"❌ 绿幕文件夹中没有视频文件")
        return False
    
    print(f"✅ 找到 {len(green_screens)} 个绿幕文件:")
    for gs in green_screens[:3]:  # 只显示前3个
        print(f"   📁 {os.path.basename(gs)}")
        
        # 检查视频属性
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', gs]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ {os.path.basename(gs)} 可正常读取")
            else:
                print(f"   ❌ {os.path.basename(gs)} 读取失败: {result.stderr}")
        except Exception as e:
            print(f"   ❌ {os.path.basename(gs)} 诊断异常: {e}")
    
    return True

def test_simple_green_screen():
    """测试简单的绿幕叠加"""
    print("\n🔍 测试简单绿幕叠加...")
    
    # 查找一个测试视频
    test_video = None
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.lower().endswith('.mp4') and 'test' in file.lower():
                test_video = os.path.join(root, file)
                break
        if test_video:
            break
    
    if not test_video:
        # 尝试创建一个测试视频
        test_video = 'test_input.mp4'
        try:
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=320x240:rate=1',
                '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=5',
                '-y', test_video
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ 创建测试视频失败: {result.stderr}")
                return False
            print(f"✅ 创建测试视频: {test_video}")
        except Exception as e:
            print(f"❌ 创建测试视频异常: {e}")
            return False
    
    # 获取一个绿幕文件
    green_screen = None
    green_screen_folder = os.path.join(os.getcwd(), 'DigitalHumans')
    if os.path.exists(green_screen_folder):
        for file in os.listdir(green_screen_folder):
            if file.lower().endswith('.mp4'):
                green_screen = os.path.join(green_screen_folder, file)
                break
    
    if not green_screen:
        print("❌ 没有找到绿幕文件")
        return False
    
    output_video = 'test_green_screen_output.mp4'
    
    # 简化的绿幕叠加命令
    filter_complex = (
        f'[1:v]scale=640:480[gs];'
        f'[gs]colorkey=0x00FF01:0.1:0.2[gs_ck];'
        f'[0:v][gs_ck]overlay=shortest=1[outv]'
    )
    
    cmd = [
        'ffmpeg', '-i', test_video, '-i', green_screen,
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '0:a',
        '-c:v', 'libx264', '-c:a', 'aac',
        '-y', output_video
    ]
    
    print(f"🔄 执行测试命令...")
    print(f"📝 命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"📊 返回码: {result.returncode}")
        if result.stdout:
            print(f"📊 标准输出: {result.stdout}")
        if result.stderr:
            print(f"📊 错误输出: {result.stderr}")
        
        if result.returncode == 0 and os.path.exists(output_video):
            print(f"✅ 测试成功: {output_video}")
            return True
        else:
            print(f"❌ 测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def main():
    print("🚀 绿幕叠加问题诊断工具")
    print("=" * 50)
    
    # 1. 诊断FFmpeg环境
    if not diagnose_ffmpeg():
        return False
    
    # 2. 诊断视频文件
    if not diagnose_videos():
        return False
    
    # 3. 测试简单绿幕叠加
    if not test_simple_green_screen():
        return False
    
    print("\n✅ 所有测试通过")
    return True

if __name__ == '__main__':
    success = main()
    input("\n按回车键退出...")
    sys.exit(0 if success else 1)