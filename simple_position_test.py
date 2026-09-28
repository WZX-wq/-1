#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化位置测试
直接调用绿幕叠加函数并查看实际输出
"""

import os
import subprocess
from ffmpeg_tool.add_green_screen_tool import add_green_screen_overlay_to_video, calculate_overlay_position, get_video_resolution

def create_simple_videos():
    """创建简单的测试视频"""
    print("🎬 创建简单测试视频...")
    
    # 创建主视频
    main_video = "simple_main.mp4"
    cmd1 = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', 'testsrc2=size=1920x1080:duration=3',
        '-f', 'lavfi',
        '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-t', '3',
        '-y',
        main_video
    ]
    
    try:
        result = subprocess.run(cmd1, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ 创建主视频失败: {result.stderr}")
            return None, None
    except Exception as e:
        print(f"❌ 创建主视频异常: {e}")
        return None, None
    
    # 创建绿幕素材
    green_video = "simple_green.mp4"
    cmd2 = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', 'color=green:size=400x300:duration=2',
        '-f', 'lavfi',
        '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-t', '2',
        '-y',
        green_video
    ]
    
    try:
        result = subprocess.run(cmd2, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ 创建绿幕失败: {result.stderr}")
            return main_video, None
    except Exception as e:
        print(f"❌ 创建绿幕异常: {e}")
        return main_video, None
    
    print(f"✅ 创建主视频: {main_video}")
    print(f"✅ 创建绿幕: {green_video}")
    
    return main_video, green_video

def test_positions_simple():
    """测试位置"""
    print("\n🧪 测试绿幕位置...")
    
    # 创建测试文件
    main_video, green_video = create_simple_videos()
    if not main_video or not green_video:
        print("❌ 创建测试文件失败")
        return False
    
    # 获取视频信息
    main_w, main_h = get_video_resolution(main_video)
    green_w, green_h = get_video_resolution(green_video)
    
    print(f"\n📊 视频信息:")
    print(f"  主视频: {main_w}x{main_h}")
    print(f"  绿幕素材: {green_w}x{green_h}")
    
    # 准备绿幕文件夹
    os.makedirs('DigitalHumans', exist_ok=True)
    import shutil
    green_in_folder = os.path.join('DigitalHumans', os.path.basename(green_video))
    shutil.copy2(green_video, green_in_folder)
    
    # 测试 bottom-right 和 bottom-center 对比
    positions_to_test = ["bottom-right", "bottom-center"]
    
    for pos in positions_to_test:
        output_video = f"simple_test_{pos}.mp4"
        
        print(f"\n--- 测试位置: {pos} ---")
        
        # 手动计算期望位置
        expected_x, expected_y = calculate_overlay_position(pos, main_w, main_h, green_w, green_h)
        print(f"📍 计算位置: ({expected_x}, {expected_y})")
        
        try:
            success = add_green_screen_overlay_to_video(
                main_video,
                output_video,
                overlay_duration=2.0,
                position=pos,
                scale=1.0,
                opacity=0.8  # 半透明，便于观察
            )
            
            if success and os.path.exists(output_video):
                print(f"✅ {pos}: 生成成功 - {output_video}")
                print(f"   文件大小: {os.path.getsize(output_video)/1024/1024:.2f}MB")
            else:
                print(f"❌ {pos}: 生成失败")
                
        except Exception as e:
            print(f"❌ {pos}: 异常 - {e}")
    
    # 清理源文件
    print(f"\n🧹 清理源文件...")
    for file in [main_video, green_video, green_in_folder]:
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
    
    print(f"\n📁 生成的测试文件:")
    print(f"  simple_test_bottom-right.mp4 - 应该在右下角")
    print(f"  simple_test_bottom-center.mp4 - 应该在底部居中")
    print(f"\n🔍 观察要点:")
    print(f"  - bottom-right视频中的绿幕应该在右下角")
    print(f"  - bottom-center视频中的绿幕应该在底部居中")
    print(f"  - 如果bottom-right视频中的绿幕在底部居中，说明位置计算有问题")
    
    return True

if __name__ == "__main__":
    print("=" * 70)
    print("简化绿幕位置测试")
    print("=" * 70)
    
    test_positions_simple()
    
    print("\n" + "=" * 70)
    print("请查看生成的视频文件验证位置！")
    print("=" * 70)