# -*- coding: utf-8 -*-
import mysql.connector

host = '82.157.237.217'
database = 'xcx'
user = 'root'
password = 'HMFLrCYsiZwbYdtSDE7980@!_+#e6e998'
port = 6306

try:
    print("正在连接数据库...")
    conn = mysql.connector.connect(
        host=host,
        database=database,
        user=user,
        password=password,
        port=port
    )
    print("数据库连接成功!")
    
    cursor = conn.cursor()
    
    # 检查符合条件的视频数量
    query = """
        SELECT COUNT(*) 
        FROM materials_3s 
        WHERE video_down_status = 1 
        AND video_resolution_status = 1 
        AND is_quality_issue = 0 
        AND material_application = '前三秒素材'
        AND material_category = '普通素材'
    """
    cursor.execute(query)
    count = cursor.fetchone()[0]
    print(f"符合条件的视频数量: {count}")
    
    if count > 0:
        # 获取一个样本
        sample_query = """
            SELECT id, local_video_domain, local_video_url
            FROM materials_3s 
            WHERE video_down_status = 1 
            AND video_resolution_status = 1 
            AND is_quality_issue = 0 
            AND material_application = '前三秒素材'
            AND material_category = '普通素材'
            LIMIT 1
        """
        cursor.execute(sample_query)
        result = cursor.fetchone()
        print(f"\n样本视频信息:")
        print(f"  ID: {result[0]}")
        print(f"  Domain: {result[1]}")
        print(f"  URL: {result[2]}")
        print(f"  完整路径: {result[1]}/{result[2]}")
    
    conn.close()
    print("\n测试完成!")
    
except Exception as e:
    print(f"错误: {e}")
