import os
import sys
sys.path.append('.')

from ffmpeg_tool.video_concat_tool import create_video_with_image_start

# 简单测试
test_video = "test_preview_video0.mp4"
test_image = "cover.jpg"
output_video = "simple_audio_test_output.mp4"

print(f"测试视频: {test_video}")
print(f"测试图片: {test_image}")
print(f"输出视频: {output_video}")

if os.path.exists(test_video) and os.path.exists(test_image):
    try:
        create_video_with_image_start(test_video, test_image, output_video, image_duration=2.0)
        print(f"✅ 成功创建: {output_video}")
        print("请播放视频验证:")
        print("- 前2秒: 静音图片")
        print("- 2秒后: 原视频+音频")
    except Exception as e:
        print(f"❌ 错误: {e}")
else:
    print("❌ 缺少测试文件")