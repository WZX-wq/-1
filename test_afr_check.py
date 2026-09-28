# -*- coding: utf-8 -*-
"""Check AFR video files"""
import sys, os
os.chdir('d:/batchAiCutter/batchAiCutter_1')
sys.path.insert(0, 'd:/batchAiCutter/batchAiCutter_1')

import mysql.connector

host = '82.157.237.217'
database = 'sucai'
user = 'sucai_admin'
password = 'HMFLrCYsiZwbYdtSDE7980@!_+#e6e998'
port = '35007'

print("Check AFR video files in database...")
conn = mysql.connector.connect(host=host, database=database, user=user, password=password, port=port)
cur = conn.cursor()

# Show 10 samples
cur.execute("""
    SELECT id, local_video_domain, local_video_url 
    FROM materials 
    WHERE material_application = '三农素材' 
    AND is_quality_issue = 0 
    AND video_down_status = 1 
    AND video_resolution_status = 1
    LIMIT 10
""")
rows = cur.fetchall()

print(f"\nSample AFR video URLs:")
for r in rows:
    full_url = f"{r[1]}/{r[2]}"
    print(f"  ID={r[0]} -> {full_url}")

# Check unique domains
cur.execute("""
    SELECT DISTINCT local_video_domain 
    FROM materials 
    WHERE material_application = '三农素材'
""")
domains = cur.fetchall()
print(f"\nUnique domains: {[d[0] for d in domains]}")

# Check file path patterns
cur.execute("""
    SELECT local_video_url 
    FROM materials 
    WHERE material_application = '三农素材'
    LIMIT 20
""")
paths = cur.fetchall()
print(f"\nFile paths:")
for p in paths:
    print(f"  {p[0]}")

cur.close()
conn.close()
