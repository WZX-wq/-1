#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查真实账号的标题类型情况
"""
import os
import sys
import mysql.connector
import datetime

# 添加当前目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_account_types(account_name):
    """检查账号的标题类型详情"""
    print(f"\n=== 检查账号: {account_name} ===")
    
    connection = None
    cursor = None
    
    try:
        connection = mysql.connector.connect(
            host='82.157.237.217',
            database='ai_video',
            user='ljx_lepin123',
            password='ea.367GZX!#EmwfpEYW$f',
            port='35008'
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            today_pattern = f"%{today}%"
            
            # 查看所有标题类型及其可用数量
            query = """
                SELECT title_type, COUNT(*) as count
                FROM video_title_info 
                WHERE account_name = %s 
                AND is_generate = 0
                AND (last_time IS NULL OR last_time NOT LIKE %s)
                GROUP BY title_type
                ORDER BY title_type
            """
            cursor.execute(query, (account_name, today_pattern))
            results = cursor.fetchall()
            
            if results:
                print("可用标题类型及数量:")
                for title_type, count in results:
                    print(f"  类型 {title_type}: {count} 个可用标题")
                
                available_types = [row[0] for row in results]
                return available_types
            else:
                print("  ❌ 没有可用的标题")
                return []
                
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return []
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

def check_all_accounts():
    """检查所有账号"""
    # 获取video_model_set中的账号
    video_model_folder_path = os.path.join(os.getcwd(), 'video_model_set')
    if os.path.exists(video_model_folder_path):
        account_files = [f for f in os.listdir(video_model_folder_path) if f.endswith('.txt')]
        account_list = [f.replace('.txt', '') for f in account_files]
        
        print(f"发现 {len(account_list)} 个账号:")
        for account in account_list:
            check_account_types(account)
    else:
        print("❌ video_model_set 文件夹不存在")

if __name__ == "__main__":
    check_all_accounts()