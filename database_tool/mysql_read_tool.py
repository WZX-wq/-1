import time

import mysql.connector


DEFAULT_CONNECT_TIMEOUT = 15
DEFAULT_READ_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 1


class DatabaseReadError(RuntimeError):
    """A database read exhausted its retry budget."""


def fetch_with_retry(connect_kwargs, query, params=(), *, dictionary=False,
                     fetch_all=False, operation_name="数据库查询",
                     raise_on_failure=False):
    """执行只读查询；连接或读取瞬时失败时有限重试，耗尽后返回 None。"""
    config = dict(connect_kwargs)
    config.setdefault("connection_timeout", DEFAULT_CONNECT_TIMEOUT)
    config.setdefault("read_timeout", DEFAULT_READ_TIMEOUT)
    config.setdefault("write_timeout", DEFAULT_READ_TIMEOUT)

    last_error = None
    for attempt in range(1, DEFAULT_RETRY_ATTEMPTS + 1):
        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(**config)
            cursor = connection.cursor(dictionary=dictionary)
            cursor.execute(query, params)
            return cursor.fetchall() if fetch_all else cursor.fetchone()
        except mysql.connector.Error as error:
            last_error = error
            print(f"{operation_name}失败（{attempt}/{DEFAULT_RETRY_ATTEMPTS}）: {error}")
            if attempt < DEFAULT_RETRY_ATTEMPTS:
                time.sleep(DEFAULT_RETRY_DELAY)
        finally:
            if cursor:
                try:
                    cursor.close()
                except mysql.connector.Error:
                    pass
            if connection:
                try:
                    if connection.is_connected():
                        connection.close()
                except mysql.connector.Error:
                    pass
    if raise_on_failure:
        raise DatabaseReadError(f"{operation_name}失败: {last_error}") from last_error
    return None
