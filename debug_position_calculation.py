#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试绿幕位置计算
验证为什么实际生成的是底部居中而不是右下角
"""

import os
import subprocess
from ffmpeg_tool.add_green_screen_tool import calculate_overlay_position, get_video_resolution

def test_position_calculation():
    """测试位置计算函数"""
    print("🔍 测试位置计算函数...")
    
    # 测试不同分辨率和绿幕尺寸
    test_cases = [
        (1920, 1080, 640, 480, "bottom-right", "横屏+标准绿幕"),
        (1080, 1920, 320, 240, "bottom-right", "竖屏+小绿幕"),
        (1920, 1080, 1280, 720, "bottom-right", "横屏+16:9绿幕"),
        (1080, 1920, 360, 640, "bottom-right", "竖屏+9:16绿幕"),
    ]
    
    print(f"\n📊 位置计算测试结果:")
    print(f"{'分辨率':<12} {'绿幕尺寸':<12} {'位置':<15} {'计算坐标':<15} {'说明'}")
    print("-" * 70)
    
    for video_w, video_h, overlay_w, overlay_h, pos, desc in test_cases:
        x, y = calculate_overlay_position(pos, video_w, video_h, overlay_w, overlay_h)
        print(f"{video_w}x{video_h:<9} {overlay_w}x{overlay_h:<10} {pos:<15} ({x}, {y:<12}) {desc}")

def create_debug_test():
    """创建调试测试"""
    print("\n🎬 创建调试测试视频...")
    
    # 创建一个带有边框的测试视频，便于观察位置
    test_video = "debug_position_test.mp4"
    
    # 创建带网格边框的测试视频，方便观察绿幕位置
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', f'color=lightblue:size=1920x1080:duration=3',
        '-f', 'lavfi',
        '-i', f'drawbox=w=1920:h=1080:x=0:y=0:color=red:t=2',  # 红色边框
        '-filter_complex', '[0:v][1:v]overlay=format=auto',
        '-f', 'lavfi',
        '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-t', '3',
        '-y',
        test_video
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(test_video):
            print(f"✅ 创建调试测试视频: {test_video}")
            return test_video
        else:
            print(f"❌ 创建调试测试视频失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ 创建调试测试视频异常: {e}")
        return None

def test_actual_position():
    """测试实际生成视频的位置"""
    print("\n🧪 测试实际绿幕位置...")
    
    # 创建测试视频
    test_video = create_debug_test()
    if not test_video:
        return False
    
    # 创建绿幕素材
    green_screen = "debug_green.mp4"
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', 'color=green:size=320x240:duration=2',
        '-f', 'lavfi', 
        '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-t', '2',
        '-y',
        green_screen
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ 创建绿幕失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 创建绿幕异常: {e}")
        return False
    
    # 准备绿幕素材文件夹
    os.makedirs('DigitalHumans', exist_ok=True)
    import shutil
    green_in_folder = os.path.join('DigitalHumans', os.path.basename(green_screen))
    shutil.copy2(green_screen, green_in_folder)
    
    # 测试不同位置
    positions = ["bottom-right", "bottom-center", "bottom-left", "top-right", "center"]
    
    for i, pos in enumerate(positions):
        output_video = f"debug_output_{pos}.mp4"
        
        try:
            from ffmpeg_tool.add_green_screen_tool import add_green_screen_overlay_to_video
            
            success = add_green_screen_overlay_to_video(
                test_video,
                output_video,
                overlay_duration=2.0,
                position=pos,
                scale=1.0,
                opacity=1.0
            )
            
            if success and os.path.exists(output_video):
                print(f"✅ {pos}: 生成成功 - {output_video}")
                
                # 分析实际叠加位置
                video_width, video_height = get_video_resolution(output_video)
                green_width, green_height = get_video_resolution(green_screen)
                
                expected_x, expected_y = calculate_overlay_position(
                    pos, 1920, 1080, green_width, green_height
                )
                
                print(f"   期望位置: ({expected_x}, {expected_y}) - {pos}")
                print(f"   视频尺寸: {video_width}x{video_height}")
                print(f"   绿幕尺寸: {green_width}x{green_height}")
            else:
                print(f"❌ {pos}: 生成失败")
                
        except Exception as e:
            print(f"❌ {pos}: 异常 - {e}")
    
    # 清理文件
    print(f"\n🧹 清理测试文件...")
    for file in [test_video, green_screen, green_in_folder]:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"   🗑️ 删除: {file}")
            except:
                pass
    
    try:
        if os.path.exists('DigitalHumans') and not os.listdir('DigitalHumans'):
            os.rmdir('DigitalHumans')
    except:
        pass
    
    return True

def check_ffmpeg_overlay_command():
    """检查FFmpeg overlay命令的具体执行"""
    print("\n🔍 分析FFmpeg overlay命令...")
    
    print("bottom-right位置的计算逻辑:")
    print("  x = video_width - overlay_width - 10")
    print("  y = video_height - overlay_height - 10")
    print()
    
    # 示例计算
    video_width, video_height = 1920, 1080
    overlay_width, overlay_height = 320, 240
    
    x = video_width - overlay_width - 10  # 1920 - 320 - 10 = 1590
    y = video_height - overlay_height - 10  # 1080 - 240 - 10 = 830
    
    print(f"示例计算 ({video_width}x{video_height} 视频, {overlay_width}x{overlay_height} 绿幕):")
    print(f"  x = {video_width} - {overlay_width} - 10 = {x}")
    print(f"  y = {video_height} - {overlay_height} - 10 = {y}")
    print(f"  理论位置: ({x}, {y}) - 应该是右下角")
    print()
    
    print("bottom-center位置的计算逻辑:")
    print("  x = (video_width - overlay_width) // 2")
    print("  y = video_height - overlay_height - 10")
    print()
    
    x_center = (video_width - overlay_width) // 2  # (1920 - 320) // 2 = 800
    y_bottom = video_height - overlay_height - 10  # 1080 - 240 - 10 = 830
    
    print(f"示例计算 ({video_width}x{video_height} 视频, {overlay_width}x{overlay_height} 绿幕):")
    print(f"  x = ({video_width} - {overlay_width}) // 2 = {x_center}")
    print(f"  y = {video_height} - {overlay_height} - 10 = {y_bottom}")
    print(f"  理论位置: ({x_center}, {y_bottom}) - 应该是底部居中")
    print()
    
    print("如果您观察到的是底部居中，可能的原因:")
    print("1. 位置参数实际传入的是 'bottom-center' 而不是 'bottom-right'")
    print("2. 视频分辨率检测错误")
    print("3. 绿幕尺寸检测错误")
    print("4. FFmpeg overlay参数有误")

if __name__ == "__main__":
    print("=" * 70)
    print("绿幕位置计算调试")
    print("=" * 70)
    
    # 测试位置计算
    test_position_calculation()
    
    # 分析FFmpeg命令
    check_ffmpeg_overlay_command()
    
    # 测试实际生成
    print(f"\n" + "=" * 70)
    print("如果要测试实际生成的视频位置，请运行:")
    print("python test_actual_position()")
    print("=" * 70)