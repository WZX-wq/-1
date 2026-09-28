"""
通过账号 + 标题删除单条记录
表名：fabu_task_info
"""
import time

import mysql.connector
from mysql.connector import Error

# ========= 连接配置（改成你的） =========
DB_CONFIG = dict(
    host="82.157.237.217",
    user="ljx_lepin123",
    password="ea.367GZX!#EmwfpEYW$f",
    database="zdcat",
    port=35008,
)
TABLE = "fabu_task_info"


# =======================================

def delete_record(account: str, title: str) -> int:
    """
    删除账号+标题匹配的记录，返回影响行数
    """
    sql = f"DELETE FROM {TABLE} WHERE account=%s AND title=%s"
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (account, title))
                conn.commit()
                return cur.rowcount
    except Error as e:
        print("数据库错误：", e)
        return 0


def main():
    account = input("请输入账号：").strip()
    title = input("请输入标题：").strip()
    if not account or not title:
        print("账号和标题不能为空！")
        return
    rows = delete_record(account, title)
    print(f"已删除 {rows} 条记录。")


if __name__ == "__main__":
    main()
    time.sleep(3)
