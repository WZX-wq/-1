# -*- coding: utf-8 -*-
"""Diagnose AFR Video Generation"""
import sys, os
os.chdir('d:/batchAiCutter/batchAiCutter_1')
sys.path.insert(0, 'd:/batchAiCutter/batchAiCutter_1')

from database_tool.video_load_tool import get_afr_random_id, download_afr_video, get_video_url
import mysql.connector

host = '82.157.237.217'
database = 'sucai'
user = 'sucai_admin'
password = 'HMFLrCYsiZwbYdtSDE7980@!_+#e6e998'
port = '35007'

print("=" * 60)
print("AFR Video Diagnosis")
print("=" * 60)

# Step 1: Check database connection
print("\n[1] Database connection...")
try:
    conn = mysql.connector.connect(host=host, database=database, user=user, password=password, port=port, connection_timeout=30)
    print("  [OK] Connected")
    
    cur = conn.cursor()
    
    # Check total AFR records
    cur.execute("SELECT COUNT(*) FROM materials WHERE material_application = '三农素材'")
    total = cur.fetchone()[0]
    print(f"  Total AFR records: {total}")
    
    # Check with filters
    cur.execute("SELECT COUNT(*) FROM materials WHERE material_application = '三农素材' AND is_quality_issue = 0 AND video_down_status = 1 AND video_resolution_status = 1")
    valid = cur.fetchone()[0]
    print(f"  Valid (quality_issue=0, down_status=1, resolution=1): {valid}")
    
    # Check by screen
    for s in [0, 1]:
        cur.execute("SELECT COUNT(*) FROM materials WHERE material_application = '三农素材' AND is_quality_issue = 0 AND video_down_status = 1 AND video_resolution_status = 1 AND screen = %s", (s,))
        c = cur.fetchone()[0]
        print(f"  screen={s}: {c}")
    
    # Sample video
    cur.execute("SELECT id, local_video_domain, local_video_url FROM materials WHERE material_application = '三农素材' AND is_quality_issue = 0 AND video_down_status = 1 AND video_resolution_status = 1 LIMIT 1")
    row = cur.fetchone()
    if row:
        print(f"\n[2] Sample video:")
        print(f"  ID: {row[0]}")
        print(f"  URL: {row[1]}/{row[2]}")
    else:
        print("\n[2] No valid AFR video found!")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"  [FAIL] {e}")

# Step 3: Test get_afr_random_id
print("\n[3] Test get_afr_random_id...")
for s in [0, 1]:
    vid = get_afr_random_id(s)
    print(f"  screen={s}: {vid}")

# Step 4: Test download
print("\n[4] Test download...")
vid = get_afr_random_id(0)
if vid:
    url = get_video_url(vid)
    print(f"  URL: {url}")
    result = download_afr_video(vid)
    print(f"  Result: {result}")
    if result and os.path.exists(str(result)):
        sz = os.path.getsize(str(result)) / 1024 / 1024
        print(f"  File size: {sz:.2f} MB")

print("\nDone")
