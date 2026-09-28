# -*- coding: utf-8 -*-
# 测试封面视频下载
import sys
import os
os.chdir('d:/batchAiCutter/batchAiCutter_1')
sys.path.insert(0, 'd:/batchAiCutter/batchAiCutter_1')

from database_tool.video_load_tool import get_cover_video_collect_all, download_cover_video, get_3s_video_url

print("=" * 50)
print("Test cover video download")
print("=" * 50)

# 1. 测试获取封面视频ID
print("\n[1] Get cover video ID...")
test_keywords = ["风景", "自然"]
test_category = "普通素材"

cover_id = get_cover_video_collect_all(test_keywords, test_category)
if cover_id:
    print(f"[OK] Cover video ID: {cover_id}")
else:
    print("[FAIL] Cannot get video ID")
    sys.exit(1)

# 2. 获取视频URL
print("\n[2] Get video URL...")
video_url = get_3s_video_url(cover_id)
if video_url:
    print(f"[OK] Video URL: {video_url}")
else:
    print("[FAIL] Cannot get video URL")
    sys.exit(1)

# 3. 测试下载视频
print("\n[3] Download video...")
result = download_cover_video(cover_id)
if result:
    if isinstance(result, str) and ('fail' in result.lower() or 'error' in result.lower()):
        print(f"[FAIL] Download failed: {result}")
    elif os.path.exists(result):
        file_size = os.path.getsize(result) / (1024 * 1024)
        print(f"[OK] Download success!")
        print(f"     File path: {result}")
        print(f"     File size: {file_size:.2f} MB")
    else:
        print(f"[FAIL] Download result abnormal: {result}")
else:
    print("[FAIL] Download returned empty result")

print("\n" + "=" * 50)
print("Test completed")
print("=" * 50)
