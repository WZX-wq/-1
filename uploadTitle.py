# 标题上传
import os
import mysql.connector
from mysql.connector import Error
from openpyxl import load_workbook

# 数据库连接配置
DB_CONFIG = {
    "host": '82.157.237.217',
    "user": 'ljx_lepin123',
    "password": 'ea.367GZX!#EmwfpEYW$f',
    "database": 'ai_video',
    "port": '35008'
}

# 文件夹路径
folder_path = r'D:\三农\三农知识'

def connect_to_db():
    """连接到数据库"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("Connected to the database")
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# 标题类型
# 1 景点介绍
# 2 全国景点介绍
# 3 科普通用
# 4 美食介绍
# 5 文字介绍
# 6 三农素材通用

def insert_titles(conn, account_name, titles):
    """批量写入：一次性 executemany"""
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT IGNORE INTO video_title_info (title, account_name, title_type)
                VALUES (%s, %s, 6)
            """
            # 构造参数列表
            data = [(t, account_name) for t in titles if t]   # 去掉空值
            cur.executemany(sql, data)                      # 一次发完
            conn.commit()
            print(f'成功写入 {cur.rowcount} 条，跳过 {len(data)-cur.rowcount} 条重复')
    except Error as e:
        print(f"❌ 批量写入失败: {e}")
        conn.rollback()


def process_excel_files():
    """处理文件夹中的所有 Excel 文件"""
    conn = connect_to_db()
    if conn:
        for file_name in os.listdir(folder_path):
            if file_name.endswith('.xlsx'):
                account_name = os.path.splitext(file_name)[0]
                file_path = os.path.join(folder_path, file_name)
                print(f"Processing {file_name}...")
                workbook = load_workbook(file_path)
                sheet = workbook.active
                titles = [cell.value for cell in sheet['A'][1:]]  # 从第二行开始读取第一列
                insert_titles(conn, account_name, titles)
        conn.close()


if __name__ == "__main__":
    process_excel_files()
