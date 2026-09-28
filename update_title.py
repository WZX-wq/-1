"""
输入账号和标题，将对应记录的 status 字段改为 1
"""
import hashlib
import uuid

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


# =========================================

def set_status_1(account: str, title: str) -> int:
    """
    将 account+title 对应记录的 status 改为 1
    返回受影响行数
    """
    sql = f"UPDATE {TABLE} SET status=1 WHERE account=%s AND title=%s"
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
    rows = set_status_1(account, title)
    print(f"已将 {rows} 条记录的状态置为 1。")


def get_pc_mac_address_upper():
    """
    获取PC的Mac地址，返回大写地址，如：F8-A2-D6-CC-BB-AA
    :return:
    """
    # print('\n=========    获取电脑mac地址   =========')
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    # 转大写
    mac_1 = "-".join([mac[e:e + 2] for e in range(0, 11, 2)]).upper()
    return md5_encrypt(mac_1)


def md5_encrypt(text):
    md5 = hashlib.md5()
    md5.update(text.encode('utf-8'))
    return md5.hexdigest()


if __name__ == "__main__":
    main()
