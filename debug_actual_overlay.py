#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
实际绿幕叠加调试脚本
详细查看FFmpeg命令和实际参数
"""

import os
import subprocess
from ffmpeg_tool.add_green_screen_tool import add_green_screen_overlay_to_video, get_video_resolution

def create_debug_videos():
    """创建用于调试的视频和绿幕"""
    print("🎬 创建调试视频和绿幕...")
    
    # 创建主视频（1920x1080，带边框便于观察）
    main_video = "debug_main_1920x1080.mp4"
    cmd1 = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', 'color=lightblue:size=1920x1080:duration=3',
        '-f', 'lavfi',
        '-i', 'drawbox=w=1920:h=1080:x=0:y=0:color=red:t=2',
        '-filter_complex', '[0:v][1:v]overlay=format=auto',
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
    
    # 创建绿幕素材（320x240，绿色）
    green_video = "debug_green_320x240.mp4"
    cmd2 = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', 'color=green:size=320x240:duration=2',
        '-f', 'lavfi',
        '-i', 'drawtext=text=GREEN:fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2',
        '-filter_complex', '[0:v][1:v]overlay=format=auto',
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

def debug_overlay_position():
    """详细调试叠加位置"""
    print("\n🔍 详细调试绿幕叠加位置...")
    
    # 创建调试文件
    main_video, green_video = create_debug_videos()
    if not main_video or not green_video:
        print("❌ 创建调试文件失败")
        return False
    
    # 验证视频信息
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
    
    # 测试不同位置
    test_positions = ["bottom-right", "bottom-center", "top-right", "center"]
    
    print(f"\n🎬 测试不同位置:")
    
    for pos in test_positions:
        output_video = f"debug_output_{pos}.mp4"
        
        print(f"\n--- 测试位置: {pos} ---")
        
        try:
            success = add_green_screen_overlay_to_video(
                main_video,
                output_video,
                overlay_duration=2.0,
                position=pos,
                scale=1.0,
                opacity=1.0
            )
            
            if success and os.path.exists(output_video):
                print(f"✅ {pos}: 生成成功")
                
                # 获取输出视频信息
                out_w, out_h = get_video_resolution(output_video)
                print(f"   输出视频: {out_w}x{out_h}")
                
                # 手动计算位置进行验证
                from ffmpeg_tool.add_green_screen_tool import calculate_overlay_position
                expected_x, expected_y = calculate_overlay_position(pos, main_w, main_h, green_w, green_h)
                print(f"   期望位置: ({expected_x}, {expected_y})")
                
                # 分析位置含义
                if pos == "bottom-right":
                    print(f"   右下角说明: 距离右边缘{green_w+10}px，底边缘{green_h+10}px")
                elif pos == "bottom-center":
                    print(f"   底部居中说明: 距离底边缘{green_h+10}px，水平居中")
                elif pos == "top-right":
                    print(f"   右上角说明: 距离右边缘{green_w+10}px，顶边缘{green_h+10}px")
                elif pos == "center":
                    print(f"   中央说明: 水平和垂直都居中")
                    
            else:
                print(f"❌ {pos}: 生成失败")
                
        except Exception as e:
            print(f"❌ {pos}: 异常 - {e}")
    
    # 清理文件
    print(f"\n🧹 清理文件...")
    cleanup_files = [main_video, green_video, green_in_folder]
    for file in cleanup_files:
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
    
    print(f"\n💡 请检查生成的视频文件:")
    print(f"  debug_output_bottom-right.mp4 - 应该在右下角")
    print(f"  debug_output_bottom-center.mp4 - 应该在底部居中")
    print(f"  debug_output_top-right.mp4 - 应该在右上角")
    print(f"  debug_output_center.mp4 - 应该在正中央")
    print(f"\n如果bottom-right视频中的绿幕在底部居中，说明：")
    print(f"1. FFmpeg overlay参数有问题")
    print(f"2. 位置计算逻辑有误")
    print(f"3. 视频坐标系理解错误")
    
    return True

if __name__ == "__main__":
    print("=" * 70)
    print("绿幕叠加实际位置调试")
    print("=" * 70)
    
    debug_overlay_position()
    
    print("\n" + "=" * 70)
    print("调试完成！请查看生成的视频文件。")
    print("=" * 70)