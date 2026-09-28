#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试人物图片添加动画效果
"""

import os
import sys
import subprocess

def test_person_pic_animation():
    """测试人物图片添加动画"""
    input_video = "test_preview_video0.mp4"
    person_pic = "person_images/175.webp"
    output_video = "test_person_animation.mp4"

    # 检查文件是否存在
    if not os.path.exists(input_video):
        print(f"[X] 输入视频不存在: {input_video}")
        return

    if not os.path.exists(person_pic):
        print(f"[X] 人物图片不存在: {person_pic}")
        return

    # 获取视频分辨率
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'default', '-show_entries', 'stream=width,height', input_video],
            capture_output=True,
            text=True
        )
        width, height = None, None
        for line in result.stdout.split('\n'):
            if 'width=' in line:
                width = int(line.split('=')[1].strip())
            elif 'height=' in line:
                height = int(line.split('=')[1].strip())

        if not width or not height:
            print("[X] 无法获取视频分辨率")
            return

        print(f"[OK] 视频分辨率: {width}x{height}")
    except Exception as e:
        print(f"[X] 获取视频分辨率失败: {e}")
        return

    # 获取图片分辨率
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'default', '-show_entries', 'stream=width,height', person_pic],
            capture_output=True,
            text=True
        )
        pic_width, pic_height = None, None
        for line in result.stdout.split('\n'):
            if 'width=' in line:
                pic_width = int(line.split('=')[1].strip())
            elif 'height=' in line:
                pic_height = int(line.split('=')[1].strip())

        if not pic_width or not pic_height:
            print("[X] 无法获取图片分辨率")
            return

        print(f"[OK] 人物图片尺寸: {pic_width}x{pic_height}")
    except Exception as e:
        print(f"[X] 获取图片分辨率失败: {e}")
        return

    # 计算原大小的居中位置
    orig_x = (width - pic_width) // 2
    orig_y = (height - pic_height) // 2

    print(f"[OK] 居中位置: ({orig_x}, {orig_y})")

    # 构建FFmpeg命令
    filter_complex = (
        f'[1:v]scale={pic_width}:{pic_height}:flags=lanczos,format=argb,colorchannelmixer=aa=1.0[person];'
        f'[0:v][person]overlay='
        f"'if(lt(t,3),{orig_x},if(lt(t,5),{orig_x}+(20-{orig_x})*(t-3)/2,20))':"
        f"'if(lt(t,3),{orig_y},if(lt(t,5),{orig_y}+(20-{orig_y})*(t-3)/2,20))',"
        f'format=yuv420p'
    )

    command = [
        'ffmpeg', '-y',
        '-i', input_video,
        '-i', person_pic,
        '-threads', '4',
        '-preset', 'faster',
        '-tune', 'fastdecode',
        '-filter_complex', filter_complex,
        '-c:v', 'libx264',
        '-crf', '23',
        '-c:a', 'copy',
        '-movflags', '+faststart',
        output_video
    ]

    print(f"[CMD] FFmpeg命令: {' '.join(command)}")
    print(f"[RUN] 开始处理...")

    # 执行命令
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding='utf-8',
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )

    if result.returncode != 0:
        print(f"[X] FFmpeg返回码: {result.returncode}")
        print(f"[X] 标准错误: {result.stderr}")
        return

    # 检查输出文件
    if not os.path.exists(output_video):
        print("[X] 输出文件未生成")
        return

    output_size = os.path.getsize(output_video)
    print(f"[OK] 处理成功!")
    print(f"[OUT] 输出文件: {output_video}")
    print(f"[OUT] 文件大小: {output_size:,} 字节")
    print(f"\n[INFO] 动画说明:")
    print(f"   0-3秒: 人物图片居中显示 ({orig_x}, {orig_y})")
    print(f"   3-5秒: 平滑移动到左上角 (20, 20)")
    print(f"   5秒后: 固定在左上角 (20, 20)")

if __name__ == "__main__":
    test_person_pic_animation()
