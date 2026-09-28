# 用户的账号信息
import hashlib
import uuid

import mysql.connector

from mysql.connector import Error

CONNECT_TIMEOUT = 15
QUERY_TIMEOUT = 30


# 根据mac地址以及账号的名称 获取账号的id
def get_account_by_name(account_name):
    mac = get_pc_mac_address_upper()
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='zdcat',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008',
            connection_timeout=CONNECT_TIMEOUT,
            read_timeout=QUERY_TIMEOUT,
            write_timeout=QUERY_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor()
            query = """
                   SELECT account, mac FROM fabu_users 
                   WHERE name LIKE %s
               """
            account_name = f"%{account_name}%"
            cursor.execute(query, (account_name,))
            result = cursor.fetchall()
            if result:
                return result
            else:
                return []

    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return []
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 上传视频任务信息
def add_user_task(param):
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='zdcat',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008',
            connection_timeout=CONNECT_TIMEOUT,
            read_timeout=QUERY_TIMEOUT,
            write_timeout=QUERY_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor()
            query = """
                   INSERT INTO fabu_task_info
                   (`name`, `account`, `create_time`, `title`, `mac`, `tag`, `path`, `describe`, `classify`, `task_type`)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               """
            values = (
                param['name'], param['account'], param['create_time'], param['title'], param['mac'],
                param['tag'], param['path'], param['describe'], param['classify'], param['task_type'])
            cursor.execute(query, values)
            connection.commit()
            return True

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return False
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def update_image_user_by_id(pic_id: int, new_user: str):
    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host='82.157.237.217',
            database='sucai',
            user='sucai_admin',
            password='HMFLrCYsiZwbYdtSDE7980@!_+#e6e998',
            port='35007',
            connection_timeout=CONNECT_TIMEOUT,
            read_timeout=QUERY_TIMEOUT,
            write_timeout=QUERY_TIMEOUT
        )
        if not connection.is_connected():
            return None

        cursor = connection.cursor()
        sql = "UPDATE image_frames SET user = %s WHERE id = %s"
        cursor.execute(sql, (new_user, pic_id))
        connection.commit()          # 手动提交
        return cursor.rowcount    # 0 表示 id 不存在；1 表示更新成功
    except mysql.connector.Error as e:
        print(f"更新失败: {e}")
        return None
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


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
