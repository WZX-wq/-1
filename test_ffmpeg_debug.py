#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试FFmpeg人物图片添加命令
"""

import os
import subprocess
import sys

def test_ffmpeg_command():
    """测试不同的FFmpeg命令格式"""
    print("=" * 60)
    print("FFmpeg 命令调试测试")
    print("=" * 60)
    
    # 测试文件路径
    test_video = "test_preview_video0.mp4"
    person_images_dir = "person_images"
    
    # 查找测试视频
    if not os.path.exists(test_video):
        print(f"❌ 测试视频不存在: {test_video}")
        print("请先创建一个测试视频")
        return
    
    # 查找测试图片
    person_pic = None
    if os.path.exists(person_images_dir):
        for file in os.listdir(person_images_dir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                person_pic = os.path.join(person_images_dir, file)
                print(f"✅ 找到图片: {person_pic}")
                break
    
    if not person_pic:
        print(f"❌ 未找到人物图片，在 {person_images_dir} 文件夹")
        return
    
    output_video = "test_person_overlay.mp4"
    
    # 测试不同的FFmpeg命令
    test_commands = [
        {
            "name": "简化版（推荐）",
            "cmd": [
                'ffmpeg', '-y',
                '-i', test_video,
                '-loop', '1',
                '-i', person_pic,
                '-filter_complex', '[0:v][1:v]overlay=(W-w)/2:(H-h)/2',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-t', '3',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-map', '0:a',
                output_video
            ]
        },
        {
            "name": "使用自定义位置",
            "cmd": [
                'ffmpeg', '-y',
                '-i', test_video,
                '-loop', '1',
                '-i', person_pic,
                '-filter_complex', '[0:v][1:v]overlay=100:100',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-t', '3',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-map', '0:a',
                output_video
            ]
        },
        {
            "name": "使用 enable 时间控制",
            "cmd": [
                'ffmpeg', '-y',
                '-i', test_video,
                '-loop', '1',
                '-i', person_pic,
                '-filter_complex', '[0:v][1:v]overlay=(W-w)/2:(H-h)/2:enable=between(t,0,3)',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-t', '3',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-map', '0:a',
                output_video
            ]
        },
        {
            "name": "最简单的版本",
            "cmd": [
                'ffmpeg', '-y',
                '-i', test_video,
                '-i', person_pic,
                '-filter_complex', '[0:v][1:v]overlay=0:0',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-t', '3',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-map', '0:a',
                output_video
            ]
        }
    ]
    
    # 测试每个命令
    for i, test_config in enumerate(test_commands, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}: {test_config['name']}")
        print(f"{'='*60}")
        
        # 清理之前的输出文件
        if os.path.exists(output_video):
            os.remove(output_video)
        
        print(f"🔧 命令: {' '.join(test_config['cmd'])}")
        
        try:
            result = subprocess.run(
                test_config['cmd'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                timeout=30
            )
            
            print(f"📊 返回码: {result.returncode}")
            
            if result.returncode == 0:
                if os.path.exists(output_video):
                    file_size = os.path.getsize(output_video)
                    print(f"✅ 成功！")
                    print(f"📦 输出文件: {output_video}")
                    print(f"📏 文件大小: {file_size:,} 字节")
                    
                    # 获取视频信息
                    cmd_info = [
                        'ffprobe',
                        '-v', 'quiet',
                        '-print_format', 'default',
                        '-show_entries', 'stream=width,height,duration',
                        output_video
                    ]
                    info_result = subprocess.run(
                        cmd_info,
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    
                    print(f"📐 视频信息:")
                    for line in info_result.stdout.split('\n'):
                        if line.strip():
                            print(f"   {line}")
                    
                    # 如果成功，退出
                    print(f"\n{'='*60}")
                    print(f"✅ 找到可用的FFmpeg命令格式!")
                    print(f"推荐使用: {test_config['name']}")
                    return
            else:
                print(f"❌ 输出文件未生成")
        except subprocess.TimeoutExpired:
            print(f"⏱️ 超时 (30秒)")
        except Exception as e:
            print(f"❌ 异常: {type(e).__name__}")
            print(f"   错误信息: {str(e)}")
        
        if result.stderr:
            print(f"❌ 错误输出: {result.stderr[:500]}")
        if result.stdout:
            print(f"📋 标准输出: {result.stdout[:500]}")
    
    print(f"\n{'='*60}")
    print("❌ 所有测试命令都失败了")
    print(f"{'='*60}")
    print("\n可能的原因:")
    print("1. FFmpeg 未安装或不在 PATH 中")
    print("2. 输入文件或图片不存在")
    print("3. 文件路径包含特殊字符或空格")
    print("4. FFmpeg 版本太旧，不支持某些滤镜")
    print("5. 磁盘空间不足")
    print("6. 视频或图片文件损坏")


if __name__ == "__main__":
    try:
        test_ffmpeg_command()
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被中断")
    except Exception as e:
        print(f"\n\n❌ 测试程序异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n按任意键退出...")
    input()
