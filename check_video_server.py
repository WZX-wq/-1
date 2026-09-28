# -*- coding: utf-8 -*-
"""检查视频服务器配置"""
import sys
sys.path.insert(0, 'd:/batchAiCutter/batchAiCutter_1')

from database_tool.video_load_tool import get_3s_video_url, get_cover_video_collect_all

print("=" * 60)
print("检查视频服务器配置")
print("=" * 60)

# 1. 获取一个封面视频ID
print("\n[1] 获取封面视频ID...")
cover_id = get_cover_video_collect_all(["风景"], "普通素材")
if cover_id:
    print(f"  封面视频ID: {cover_id}")
else:
    print("  无法获取视频ID")
    sys.exit(1)

# 2. 获取该视频的URL配置
print("\n[2] 获取视频URL...")
video_url = get_3s_video_url(cover_id)
print(f"  数据库返回的URL: {video_url}")

# 3. 分析URL结构
print("\n[3] URL分析:")
if video_url:
    if '100.122.91.10' in video_url:
        print("  - 使用服务器: 100.122.91.10:8991")
    elif '182.110.69.75' in video_url:
        print("  - 使用服务器: 182.110.69.75:8991")
    elif video_url.startswith('http'):
        print(f"  - 直接使用完整URL")
    else:
        print(f"  - 需要拼接URL")

print("\n" + "=" * 60)
