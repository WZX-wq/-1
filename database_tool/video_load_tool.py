# 视频上传下载工具
import datetime
import json
import random
import shutil
import subprocess
import threading
import time
from pathlib import Path

import cv2
import mysql.connector
from mysql.connector import Error
import requests

from ftplib import FTP, error_perm
import os

from ai_tool.ai_text_production import deepseek_ai_history_person
from ffmpeg_tool.video_concat_tool import get_video_duration
from database_tool.mysql_read_tool import fetch_with_retry
from database_tool.material_download_tool import download_to_cache, set_material_download_error

poorTime = 20

# 需要禁用的远程 FTP 服务器（该服务器不可访问，会长时间卡在连接上）
BANNED_FTP_HOSTS = ('123.162.188.146',)

host = '82.157.237.217'  # 数据库主机地址
database = 'sucai'  # 数据库名称
user = 'sucai_admin'  # 数据库用户名
password = 'HMFLrCYsiZwbYdtSDE7980@!_+#e6e998'  # 数据库密码
port = '35007'
CONNECT_TIMEOUT = 60  # 建立连接最长 60 秒
QUERY_TIMEOUT = 30  # 单条 SQL 最长 30 秒

# 首标签查询已经返回完整素材记录。后续次标签筛选直接复用这些候选，
# 避免为同一小批素材反复建立远程 MySQL/SSL 连接。
_material_candidate_cache = {}
_material_index_loaded = False
_material_index_lock = threading.RLock()
_material_index_write_lock = threading.Lock()
_material_index_sync_lock = threading.Lock()
_material_index_sync_started = False
_material_db_retry_after = 0.0
_MATERIAL_INDEX_FIELDS = (
    'id', 'tags', 'city', 'screen', 'duration', 'material_category',
    'material_application', 'is_quality_issue', 'video_down_status',
    'video_resolution_status',
)


def _material_index_path():
    return Path(os.getcwd()) / 'material_index.json'


def _material_index_record(video):
    return {key: video.get(key) for key in _MATERIAL_INDEX_FIELDS if key in video}


def _load_material_index():
    global _material_index_loaded
    with _material_index_lock:
        if _material_index_loaded:
            return
        _material_index_loaded = True
        try:
            with _material_index_path().open('r', encoding='utf-8') as index_file:
                records = json.load(index_file)
            if not isinstance(records, list):
                return
            for video in records:
                if isinstance(video, dict) and video.get('id') is not None:
                    _material_candidate_cache.setdefault(str(video['id']), video)
        except (OSError, ValueError, TypeError):
            return


def _save_material_index():
    index_path = _material_index_path()
    temporary_path = index_path.with_suffix('.json.tmp')
    try:
        with _material_index_write_lock:
            with _material_index_lock:
                records = list(_material_candidate_cache.values())
            temporary_path.write_text(
                json.dumps(records, ensure_ascii=False, default=str),
                encoding='utf-8',
            )
            os.replace(temporary_path, index_path)
    except OSError as error:
        print(f'保存本地素材索引失败：{error}')
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass


def _cache_material_candidates(videos):
    _load_material_index()
    changed = False
    with _material_index_lock:
        for video in videos or []:
            video_id = video.get('id')
            if video_id is not None:
                _material_candidate_cache[str(video_id)] = _material_index_record(video)
                changed = True
    if changed:
        _save_material_index()


def _local_material_path(video_id):
    cache_dir = Path(os.getcwd()) / 'cacheVideo'
    for name in (f'{video_id}.mp4', f'{video_id}.MP4'):
        path = cache_dir / name
        if path.is_file():
            return path
    return None


def _offline_material_candidates(keyword, screen, location, audio_length,
                                 poor_time=3, cate=None, allowed_ids=None):
    _load_material_index()
    allowed = {str(value) for value in allowed_ids} if allowed_ids is not None else None
    candidates = []
    unknown_local = []
    cache_dir = Path(os.getcwd()) / 'cacheVideo'
    with _material_index_lock:
        records = list(_material_candidate_cache.items())
    indexed_ids = {video_id for video_id, _video in records}
    for video_id, video in records:
        if allowed is not None and video_id not in allowed:
            continue
        path = _local_material_path(video_id)
        if path is None:
            continue
        tags = str(video.get('tags') or '')
        if keyword and keyword not in tags:
            continue
        city = str(video.get('city') or '')
        if location and location not in city:
            continue
        try:
            if int(video.get('screen')) != int(screen):
                continue
            duration = float(video.get('duration'))
            if not float(audio_length) - poor_time <= duration <= float(audio_length) + poor_time:
                continue
        except (TypeError, ValueError):
            continue
        if cate is not None and str(video.get('material_category')) != str(cate):
            continue
        candidates.append(video)
    if not candidates and cache_dir.is_dir():
        for path in cache_dir.iterdir():
            if not path.is_file() or path.suffix.lower() != '.mp4' or not path.stem.isdigit():
                continue
            if path.stem in indexed_ids:
                continue
            if allowed is not None and path.stem not in allowed:
                continue
            unknown_local.append({
                'id': int(path.stem),
                'tags': '',
                'city': '',
                'screen': screen,
                'duration': audio_length,
                'material_category': cate,
                'local_only': True,
            })
    if not candidates:
        candidates = unknown_local
        if candidates:
            print('本地素材标签索引没有匹配项，以下素材按编号随机兜底，无法保证与文案标签一致')
    random.shuffle(candidates)
    return candidates[:20]


def sync_local_material_index():
    """Load database metadata for existing cacheVideo IDs without downloading videos."""
    cache_dir = Path(os.getcwd()) / 'cacheVideo'
    if not cache_dir.is_dir():
        return 0
    video_ids = sorted({
        path.stem for path in cache_dir.iterdir()
        if path.is_file() and path.suffix.lower() == '.mp4' and path.stem.isdigit()
    }, key=int)
    if not video_ids:
        return 0

    connection = None
    cursor = None
    found = 0
    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
            connection_timeout=15,
            read_timeout=QUERY_TIMEOUT,
            write_timeout=QUERY_TIMEOUT,
        )
        cursor = connection.cursor(dictionary=True)
        columns = ', '.join(f'`{field}`' for field in _MATERIAL_INDEX_FIELDS)
        for offset in range(0, len(video_ids), 400):
            batch = video_ids[offset:offset + 400]
            placeholders = ', '.join(['%s'] * len(batch))
            cursor.execute(
                f'SELECT {columns} FROM materials WHERE id IN ({placeholders})',
                tuple(batch),
            )
            records = cursor.fetchall() or []
            _cache_material_candidates(records)
            found += len(records)
        print(f'本地素材标签索引已更新：{found}/{len(video_ids)}')
        return found
    except Exception as error:
        global _material_index_sync_started
        _material_index_sync_started = False
        print(f'更新本地素材标签索引失败：{error}')
        return found
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if connection:
            try:
                connection.close()
            except Exception:
                pass


def _start_local_material_index_sync():
    global _material_index_sync_started
    cache_dir = Path(os.getcwd()) / 'cacheVideo'
    if not cache_dir.is_dir():
        return
    with _material_index_sync_lock:
        if _material_index_sync_started:
            return
        _material_index_sync_started = True
    threading.Thread(
        target=sync_local_material_index,
        name='local-material-index-sync',
        daemon=True,
    ).start()


def _database_in_cooldown():
    return time.time() < _material_db_retry_after


def _mark_database_available():
    global _material_db_retry_after
    _material_db_retry_after = 0.0


def _mark_database_unavailable():
    global _material_db_retry_after
    _material_db_retry_after = time.time() + 60


def _filter_cached_materials(keyword, material_ids):
    _load_material_index()
    if not keyword or not material_ids:
        return None
    cache_keys = [str(video_id) for video_id in material_ids]
    if not all(key in _material_candidate_cache for key in cache_keys):
        return None
    candidates = [
        _material_candidate_cache[key]
        for key in cache_keys
        if keyword in (_material_candidate_cache[key].get('tags') or '')
    ]
    if _database_in_cooldown():
        candidates = [
            video for video in candidates
            if _local_material_path(video.get('id')) is not None
        ]
    return candidates


# 根据视频标签获取视频素材 id范围内
def _get_videos_by_keyword_once(first_keyword, screen, location, location_id_list, audio_length, poorTime=3, cate=None):
    """
    根据关键词获取标签中包含该关键词的视频信息

    参数：
        keyword: 要查询的关键词

    返回：
        包含该关键词的视频信息列表
    """
    if location == '中国':
        location = ''
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=15,
            read_timeout=QUERY_TIMEOUT,
            write_timeout=QUERY_TIMEOUT
        )
        location_id_str = ', '.join(f"'{location}'" for location in location_id_list)
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # 使用 LIKE 操作符进行模糊查询，确保匹配包含关键词的标签
            if cate is not None:
                cate_str = "and material_category = %s"
            else:
                cate_str = ""
            if location:
                query = f"""
                    SELECT * FROM materials
                    WHERE tags LIKE %s
                      AND screen = %s
                      AND city LIKE %s
                      AND id IN ({location_id_str})
                      AND CAST(duration AS UNSIGNED) BETWEEN %s - {poorTime} AND %s + {poorTime}
                      {cate_str}
                    ORDER BY RAND()
                    LIMIT 20
                """
                # 在关键词前后添加 % 以实现模糊匹配
                search_pattern = f"%{first_keyword}%"
                location_pattern = f"%{location}%"
                if cate is not None:
                    cursor.execute(query, (
                        search_pattern, screen, location_pattern, audio_length, audio_length, cate))  # 确保参数是元组
                else:
                    cursor.execute(query,
                                   (search_pattern, screen, location_pattern, audio_length, audio_length))  # 确保参数是元组
            else:
                query = f"""
                    SELECT * FROM materials
                    WHERE tags LIKE %s
                    and screen = %s
                     AND id IN ({location_id_str})
                    and CAST(duration AS UNSIGNED) BETWEEN %s - {poorTime} AND %s + {poorTime} 
                    {cate_str}
                    ORDER BY RAND()
                    LIMIT 20
                """
                # 在关键词前后添加 % 以实现模糊匹配
                search_pattern = f"%{first_keyword}%"
                if cate is not None:
                    cursor.execute(query, (search_pattern, screen, audio_length, audio_length, cate))  # 确保参数是元组
                else:
                    cursor.execute(query, (search_pattern, screen, audio_length, audio_length))  # 确保参数是元组

            # 获取所有匹配的视频信息
            videos = cursor.fetchall()
            return videos

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None
    finally:
        # 确保资源被正确释放
        if cursor:
            try:
                cursor.close()
            except Error:
                pass
        if connection:
            try:
                if connection.is_connected():
                    connection.close()
            except Error:
                pass


def get_videos_by_keyword(first_keyword, screen, location, location_id_list, audio_length, poorTime=3, cate=None):
    cached_videos = _filter_cached_materials(first_keyword, location_id_list)
    if cached_videos is not None:
        return cached_videos

    if _database_in_cooldown():
        return _offline_material_candidates(
            first_keyword, screen, location, audio_length, poorTime, cate,
            allowed_ids=location_id_list,
        )
    for attempt in range(1, 4):
        videos = _get_videos_by_keyword_once(
            first_keyword, screen, location, location_id_list, audio_length, poorTime, cate
        )
        if videos:
            _mark_database_available()
            return videos
        if videos == []:
            _mark_database_available()
            break
        _mark_database_unavailable()
        offline = _offline_material_candidates(
            first_keyword, screen, location, audio_length, poorTime, cate,
            allowed_ids=location_id_list,
        )
        if offline:
            return offline
        print(f"按标签筛选素材失败，准备重试（{attempt}/3）")
        if attempt < 3:
            time.sleep(1)
    return _offline_material_candidates(
        first_keyword, screen, location, audio_length, poorTime, cate,
        allowed_ids=location_id_list,
    )


def _get_videos_by_keyword_1_once(first_keyword, screen, location, audio_length, poorTime=3, cate=None):
    """
    根据关键词获取标签中包含该关键词的视频信息

    参数：
        keyword: 要查询的关键词

    返回：
        包含该关键词的视频信息列表
    """
    if location == '中国':
        location = ''
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=15,
            read_timeout=QUERY_TIMEOUT,
            write_timeout=QUERY_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # 使用 LIKE 操作符进行模糊查询，确保匹配包含关键词的标签
            if cate is not None:
                cate_str = "and material_category = %s"
            else:
                cate_str = ""
            if location:
                query = f"""
                                SELECT * FROM materials
                                WHERE (tags LIKE %s OR tags LIKE %s ESCAPE '\\\\')
                                and material_application = '视频素材'
                                and is_quality_issue= 0 
                                and video_down_status= 1 
                                and video_resolution_status= 1
                                and screen = %s
                                and city LIKE %s
                                and CAST(duration AS UNSIGNED) BETWEEN %s - {poorTime} AND %s + {poorTime} 
                                {cate_str}
                                ORDER BY RAND()
                                LIMIT 20
                            """
                # 在关键词前后添加 % 以实现模糊匹配
                search_pattern_1 = f"%{first_keyword}"
                search_pattern_2 = f"%{first_keyword}\\_%"
                location_pattern = f"%{location}%"
                if cate is not None:
                    cursor.execute(query, (
                        search_pattern_1, search_pattern_2, screen, location_pattern, audio_length, audio_length,
                        cate))  # 确保参数是元组
                else:
                    cursor.execute(query,
                                   (search_pattern_1, search_pattern_2, screen, location_pattern, audio_length,
                                    audio_length))  # 确保参数是元组
            else:
                query = f"""
                    SELECT * FROM materials
                    WHERE  (tags LIKE %s OR tags LIKE %s ESCAPE '\\\\')
                    and material_application = '视频素材'
                    and is_quality_issue= 0
                    and video_down_status = 1 
                    and video_resolution_status = 1
                    and screen = %s
                    and CAST(duration AS UNSIGNED) BETWEEN %s - {poorTime} AND %s + {poorTime}
                    {cate_str}
                    ORDER BY RAND()
                    LIMIT 20
                """
                # 在关键词前后添加 % 以实现模糊匹配
                search_pattern_1 = f"%{first_keyword}"
                search_pattern_2 = f"%{first_keyword}\\_%"
                if cate is not None:
                    cursor.execute(query, (
                        search_pattern_1, search_pattern_2, screen, audio_length, audio_length, cate))  # 确保参数是元组
                else:
                    cursor.execute(query,
                                   (search_pattern_1, search_pattern_2, screen, audio_length, audio_length))  # 确保参数是元组

            # 获取所有匹配的视频信息
            videos = cursor.fetchall()
            return videos if videos else []
        else:
            return None

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in get_videos_by_keyword_1: {e}")
        return None
    finally:
        # 确保资源被正确释放
        if cursor:
            try:
                cursor.close()
            except Error:
                pass
        if connection:
            try:
                if connection.is_connected():
                    connection.close()
            except Error:
                pass


def get_videos_by_keyword_1(first_keyword, screen, location, audio_length, poorTime=3, cate=None):
    if _database_in_cooldown():
        return _offline_material_candidates(
            first_keyword, screen, location, audio_length, poorTime, cate,
        )
    for attempt in range(1, 4):
        videos = _get_videos_by_keyword_1_once(
            first_keyword, screen, location, audio_length, poorTime, cate
        )
        if videos:
            _mark_database_available()
            _cache_material_candidates(videos)
            _start_local_material_index_sync()
            return videos
        if videos == []:
            _mark_database_available()
            _start_local_material_index_sync()
            break
        _mark_database_unavailable()
        offline = _offline_material_candidates(
            first_keyword, screen, location, audio_length, poorTime, cate,
        )
        if offline:
            return offline
        print(f"按首标签查询素材失败，准备重试（{attempt}/3）")
        if attempt < 3:
            time.sleep(1)
    return _offline_material_candidates(
        first_keyword, screen, location, audio_length, poorTime, cate,
    )


# 根据cn视频标签获取视频素材 id范围内
def get_cn_videos_by_keyword(first_keyword, screen, location, location_id_list, audio_length, poorTime=3, cate=None):
    """
    根据关键词获取标签中包含该关键词的视频信息

    参数：
        keyword: 要查询的关键词

    返回：
        包含该关键词的视频信息列表
    """
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=CONNECT_TIMEOUT
        )
        location_id_str = ', '.join(f"'{location}'" for location in location_id_list)
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # 使用 LIKE 操作符进行模糊查询，确保匹配包含关键词的标签
            if cate is not None:
                cate_str = "and cate = %s"
            else:
                cate_str = ""
            if location:
                query = f"""
                    SELECT * FROM cn_video_info
                    WHERE first_tag LIKE %s
                      AND screen = %s
                      AND second_tag LIKE %s
                      AND id IN ({location_id_str})
                      AND CAST(duration AS FLOAT) BETWEEN %s - {poorTime} AND %s + {poorTime}
                      {cate_str}
                    ORDER BY RAND()
                    LIMIT 20
                """
                # 在关键词前后添加 % 以实现模糊匹配
                search_pattern = f"%{first_keyword}%"
                location_pattern = f"%{location}%"
                if cate is not None:
                    cursor.execute(query, (
                        search_pattern, screen, location_pattern, audio_length, audio_length, cate))  # 确保参数是元组
                else:
                    cursor.execute(query,
                                   (search_pattern, screen, location_pattern, audio_length, audio_length))  # 确保参数是元组
            else:
                query = f"""
                    SELECT * FROM cn_video_info
                    WHERE first_tag LIKE %s
                    and screen = %s
                     AND id IN ({location_id_str})
                    and CAST(duration AS FLOAT) BETWEEN %s - {poorTime} AND %s + {poorTime} 
                    {cate_str}
                    ORDER BY RAND()
                    LIMIT 20
                """
                # 在关键词前后添加 % 以实现模糊匹配
                search_pattern = f"%{first_keyword}%"
                if cate is not None:
                    cursor.execute(query, (search_pattern, screen, audio_length, audio_length, cate))  # 确保参数是元组
                else:
                    cursor.execute(query, (search_pattern, screen, audio_length, audio_length))  # 确保参数是元组

            # 获取所有匹配的视频信息
            videos = cursor.fetchall()
            return videos

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return []
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def get_cn_videos_by_keyword_1(first_keyword, screen, location, audio_length, poorTime=3, cate=None):
    """
    根据关键词获取标签中包含该关键词的视频信息

    参数：
        keyword: 要查询的关键词

    返回：
        包含该关键词的视频信息列表
    """
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=CONNECT_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # 使用 LIKE 操作符进行模糊查询，确保匹配包含关键词的标签
            if cate is not None:
                cate_str = "and cate = %s"
            else:
                cate_str = ""
            if location:
                query = f"""
                                SELECT * FROM cn_video_info
                                WHERE (first_tag LIKE %s OR first_tag LIKE %s)
                                and screen = %s
                                and second_tag LIKE %s
                                and CAST(duration AS FLOAT) BETWEEN %s - {poorTime} AND %s + {poorTime} 
                                {cate_str}
                                ORDER BY RAND()
                                LIMIT 20
                            """
                # 在关键词前后添加 % 以实现模糊匹配
                search_pattern_1 = f"%{first_keyword}"
                search_pattern_2 = f"%{first_keyword}_%"
                location_pattern = f"%{location}%"
                if cate is not None:
                    cursor.execute(query, (
                        search_pattern_1, search_pattern_2, screen, location_pattern, audio_length, audio_length,
                        cate))  # 确保参数是元组
                else:
                    cursor.execute(query,
                                   (search_pattern_1, search_pattern_2, screen, location_pattern, audio_length,
                                    audio_length))  # 确保参数是元组
            else:
                query = f"""
                    SELECT * FROM cn_video_info
                    WHERE (first_tag LIKE %s OR first_tag LIKE %s)
                    and screen = %s
                    and CAST(duration AS FLOAT) BETWEEN %s - {poorTime} AND %s + {poorTime} 
                    {cate_str}
                    ORDER BY RAND()
                    LIMIT 20
                """
                # 在关键词前后添加 % 以实现模糊匹配
                search_pattern_1 = f"%{first_keyword}"
                search_pattern_2 = f"%{first_keyword}_%"
                if cate is not None:
                    cursor.execute(query, (
                        search_pattern_1, search_pattern_2, screen, audio_length, audio_length, cate))  # 确保参数是元组
                else:
                    cursor.execute(query,
                                   (search_pattern_1, search_pattern_2, screen, audio_length, audio_length))  # 确保参数是元组

            # 获取所有匹配的视频信息
            videos = cursor.fetchall()
            return videos

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return []
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def get_music_by_keyword(keyword):
    """
    根据关键词获取标签中包含该关键词的音乐信息

    参数：
        keyword: 要查询的关键词

    返回：
        包含该关键词的音乐信息列表
    """
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=CONNECT_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # 使用 LIKE 操作符进行模糊查询，确保匹配包含关键词的标签
            query = """
                SELECT * FROM music_info 
                WHERE first_tag LIKE %s
                ORDER BY RAND()
                LIMIT 5
            """
            # 在关键词前后添加 % 以实现模糊匹配
            search_pattern = f"%{keyword}%"
            cursor.execute(query, (search_pattern,))  # 确保参数是元组

            # 获取所有匹配的视频信息
            videos = cursor.fetchall()

            return videos

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return []
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 记录上传视频素材的信息
def add_video_record(param):
    """
    添加新的视频记录到数据库

    参数：
        title: 视频标题
        first_tag: 一级标签
        second_tag: 二级标签
        video_location: 视频位置
        duration: 视频时长

    返回：
        如果插入成功返回 True，否则返回 False
    """
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=CONNECT_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor()
            query = f"""
                INSERT INTO video_info 
                (title, first_tag, second_tag, duration, created_date, screen, cate)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                param['title'], param['firstTags'], param['secondTags'], param['videoLength'], param['createdDate'],
                param['screen'], param['cate'])
            cursor.execute(query, values)
            connection.commit()

            # 获取刚插入记录的 id
            last_insert_id = cursor.lastrowid
            # 根据 id 更新 video_url
            new_video_url = f"{last_insert_id}.MP4"
            update_query = "UPDATE video_info SET video_url = %s WHERE id = %s"
            cursor.execute(update_query, (new_video_url, last_insert_id))
            connection.commit()

            return last_insert_id

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return False
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 记录上传视频素材的信息
def add_music_record(param):
    """
    添加新的视频记录到数据库

    参数：
        title: 视频标题
        first_tag: 一级标签
        second_tag: 二级标签
        video_location: 视频位置
        duration: 视频时长

    返回：
        如果插入成功返回 True，否则返回 False
    """
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=CONNECT_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor()
            query = """
                INSERT INTO music_info 
                (title, first_tag, second_tag, duration, created_date)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (
                param['title'], param['firstTags'], param['secondTags'], param['videoLength'], param['createdDate'])
            cursor.execute(query, values)
            connection.commit()

            # 获取刚插入记录的 id
            last_insert_id = cursor.lastrowid
            # 根据 id 更新 video_url
            new_video_url = f"{last_insert_id}.MP3"
            update_query = "UPDATE music_info SET music_url = %s WHERE id = %s"
            cursor.execute(update_query, (new_video_url, last_insert_id))
            connection.commit()

            return last_insert_id

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return False
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def delete_video_record(video_id):
    """
    按 id 删除视频记录

    参数：
        video_id: 视频记录的 id

    返回：
        如果删除成功返回 True，否则返回 False
    """
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=CONNECT_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor()
            query = """
                DELETE FROM video_info 
                WHERE id = %s
            """
            cursor.execute(query, (video_id,))
            connection.commit()

            if cursor.rowcount > 0:
                return True
            else:
                return False
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return False
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def delete_music_record(music_id):
    """
    按 id 删除视频记录

    参数：
        music_id: 音乐记录的 id

    返回：
        如果删除成功返回 True，否则返回 False
    """
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=CONNECT_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor()
            query = """
                DELETE FROM music_info 
                WHERE id = %s
            """
            cursor.execute(query, (music_id,))
            connection.commit()

            if cursor.rowcount > 0:
                return True
            else:
                return False
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return False
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def get_random_id(screen):
    """
    从数据库随机获取一个存在的 id

    返回：
        随机的 id 值，若查询失败则返回 None
    """
    connection = None
    cursor = None
    try:
        # 连接数据库，此处需要填入你的数据库连接相关信息
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=CONNECT_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # 随机获取一个 id
            query = """
                SELECT id FROM video_info 
                where screen = %s
                ORDER BY RAND() LIMIT 1
            """
            cursor.execute(query, (screen,))

            # 获取随机的 id
            result = cursor.fetchone()
            if result:
                return result['id']
            else:
                return None

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def get_video_url(video_id):
    """
    按 id 获取视频记录的 video_url。

    参数：
        video_id: 视频记录的 id

    返回：
        如果找到对应的记录，返回 video_url，否则返回 None
    """
    if video_id is None:
        return None
    result = fetch_with_retry(
        dict(host=host, database=database, user=user, password=password, port=port),
        "SELECT local_video_domain, local_video_url FROM materials WHERE id = %s",
        (video_id,), operation_name='查询素材下载地址')
    if not result or not result[1]:
        return None
    return 'http://100.122.91.10:8991/' + result[1]


def get_3s_video_url(video_id):
    """
    按 id 获取视频记录的 video_url。

    参数：
        video_id: 视频记录的 id

    返回：
        如果找到对应的记录，返回 video_url，否则返回 None
    """
    if video_id is None:
        return None
    result = fetch_with_retry(
        dict(host=host, database=database, user=user, password=password, port=port),
        "SELECT local_video_domain, local_video_url FROM materials_3s WHERE id = %s",
        (video_id,), operation_name='查询封面素材下载地址')
    if not result or not result[1]:
        return None
    return 'http://100.122.91.10:8991/' + result[1]


def get_cn_video_url(video_id):
    """
    按 id 获取视频记录的 video_url。

    参数：
        video_id: 视频记录的 id

    返回：
        如果找到对应的记录，返回 video_url，否则返回 None
    """
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=CONNECT_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor()
            query = """
                SELECT video_url,domain FROM cn_video_info 
                WHERE id = %s
            """
            cursor.execute(query, (video_id,))
            result = cursor.fetchone()

            if result:
                video_url, domain = result
                if domain:
                    return 'http://100.122.91.10:8991/' + video_url
                else:
                    return video_url
            else:
                return None

    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return None
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def get_arf_video_url(video_id):
    """
    按 id 获取视频记录的 video_url。

    参数：
        video_id: 视频记录的 id

    返回：
        如果找到对应的记录，返回 video_url，否则返回 None
    """
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=CONNECT_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor()
            query = """
                SELECT video_url FROM afr_video_info 
                WHERE id = %s
            """
            cursor.execute(query, (video_id,))
            result = cursor.fetchone()

            if result:
                return result[0]
            else:
                return None

    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return None
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def get_cover_video_url(video_id):
    """
    按 id 获取视频记录的 video_url。

    参数：
        video_id: 视频记录的 id

    返回：
        如果找到对应的记录，返回 video_url，否则返回 None
    """
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=CONNECT_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor()
            query = """
                SELECT video_url FROM video_cover_info 
                WHERE id = %s
            """
            cursor.execute(query, (video_id,))
            result = cursor.fetchone()

            if result:
                return result[0]
            else:
                return None

    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return None
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def get_pic_url(pic_id):
    """
    按 id 获取图片的 pic_url。

    参数：
        pic_id: 图片记录的 id

    返回：
        如果找到对应的记录，返回 video_url，否则返回 None
    """
    if pic_id is None:
        return None
    result = fetch_with_retry(
        dict(host=host, database=database, user=user, password=password, port=port),
        "SELECT image_path FROM image_frames WHERE id = %s", (pic_id,),
        operation_name='查询图片下载地址')
    return result[0] if result else None


def update_video_screen_by_id(video_id: int, new_screen: str) -> bool:
    """
    根据 id 更新 video_info 表里的 screen 字段
    :param video_id: 主键 id
    :param new_screen: 新的 screen 值
    :return: True/False 表示更新是否成功
    """
    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=CONNECT_TIMEOUT
        )
        if connection.is_connected():
            cursor = connection.cursor()
            sql = "UPDATE video_info SET screen = %s WHERE id = %s"
            cursor.execute(sql, (new_screen, video_id))
            connection.commit()
            return True
    except Error as e:
        print(f"MySQL error: {e}")
        return False
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 随机获取封面素材
def get_random_cover_video(title_keyword_list, cate):
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host=host,  # 数据库主机地址
            database=database,  # 数据库名称
            user=user,  # 数据库用户名
            password=password,  # 数据库密码
            port=port,
            connection_timeout=CONNECT_TIMEOUT
        )
        for title_keyword in title_keyword_list:
            title_keyword_pattern = f"%{title_keyword}%"
            if connection.is_connected():
                cursor = connection.cursor()
                query = """
                      SELECT id
                      FROM materials_3s
                      WHERE tags LIKE %s
                      and is_quality_issue= 0 
                      and video_down_status= 1 
                      and video_resolution_status= 1
                      and material_application = '前三秒素材'
                      and material_category = %s
                      ORDER BY RAND()
                      LIMIT 1
                   """
                cursor.execute(query, (title_keyword_pattern, cate,))
                result = cursor.fetchone()
                if result:
                    return result[0]

        if connection.is_connected():
            cursor = connection.cursor()
            query = """
                             SELECT id
                             FROM materials_3s
                             where material_category = %s
                             and material_application = '前三秒素材'
                             and is_quality_issue= 0 
                             and video_down_status= 1 
                             and video_resolution_status= 1
                             ORDER BY RAND()
                             LIMIT 1
                          """
            cursor.execute(query, (cate,))
            result = cursor.fetchone()
            if result:
                return result[0]

    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return None
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 随机获取封面素材
def get_random_cover_video_by_cate(cate):
    result = fetch_with_retry(
        dict(host=host, database=database, user=user, password=password, port=port),
        """SELECT id FROM materials_3s WHERE material_category = %s
           AND material_application = '前三秒素材'
           AND is_quality_issue = 0 AND video_down_status = 1
           AND video_resolution_status = 1 ORDER BY RAND() LIMIT 1""",
        (cate,), operation_name='随机查询通用素材')
    return result[0] if result else None


# 智能封面选择：收集所有关键词匹配的视频（合并去重），再随机选择
def get_cover_video_collect_all(title_keyword_list, cate):
    """
    智能封面选择算法：
    1. 收集所有关键词匹配的候选视频（合并去重）
    2. 从合并后的候选池中随机选择
    3. 如果没有候选，回退到类别随机选择

    Args:
        title_keyword_list: 关键词列表
        cate: 素材类别

    Returns:
        视频ID或None
    """
    connect_kwargs = {
        'host': host, 'database': database, 'user': user,
        'password': password, 'port': port
    }

    # 收集所有关键词匹配的候选视频（单次 SQL，避免多次全表扫描）
    all_candidates = set()
    if title_keyword_list:
        keyword_patterns = [f"%{keyword}%" for keyword in title_keyword_list]
        placeholders = ' OR '.join(['tags LIKE %s'] * len(title_keyword_list))
        query = f"""
            SELECT DISTINCT id
            FROM materials_3s
            WHERE ({placeholders})
            AND is_quality_issue = 0
            AND video_down_status = 1
            AND video_resolution_status = 1
            AND material_application = '前三秒素材'
            AND material_category = %s
        """
        results = fetch_with_retry(
            connect_kwargs,
            query,
            tuple(keyword_patterns) + (cate,),
            fetch_all=True,
            operation_name='查询封面素材',
        )
        if results is None:
            return None
        all_candidates.update(row[0] for row in results)

    # 从候选池中随机选择
    if all_candidates:
        selected_id = random.choice(list(all_candidates))
        print(f"[封面选择] 关键词匹配候选池: {len(all_candidates)}个视频，选中ID: {selected_id}")
        return selected_id

    # 没有候选，回退到类别随机选择
    print(f"[封面选择] 关键词无匹配，回退到类别随机选择")
    fallback_query = """
        SELECT id
        FROM materials_3s
        WHERE material_category = %s
        AND material_application = '前三秒素材'
        AND is_quality_issue = 0
        AND video_down_status = 1
        AND video_resolution_status = 1
        ORDER BY RAND()
        LIMIT 1
    """
    result = fetch_with_retry(
        connect_kwargs,
        fallback_query,
        (cate,),
        operation_name='随机查询封面素材',
    )
    return result[0] if result else None


# 随机获取图像
def get_random_cover_pic(title_keyword_list, account_name):
    connect_kwargs = dict(host=host, database=database, user=user, password=password, port=port)
    # 旧 FTP 不可用时只选本地已同步的图片，避免选中后必然下载失败。
    cache_dir = os.path.join(os.getcwd(), 'touristPictures')
    cached_ids = sorted({Path(name).stem for name in os.listdir(cache_dir)}) if os.path.isdir(cache_dir) else []
    restrict_sql = ''
    restrict_params = ()
    if read_ftp_config().get('ftp_host') in BANNED_FTP_HOSTS:
        if not cached_ids:
            return None
        restrict_sql = f" AND id IN ({','.join(['%s'] * len(cached_ids))})"
        restrict_params = tuple(cached_ids)

    for title_keyword in title_keyword_list:
        result = fetch_with_retry(
            connect_kwargs,
            f"""SELECT id FROM image_frames
                WHERE image_tags LIKE %s AND (user = %s OR user IS NULL)
                {restrict_sql} ORDER BY RAND() LIMIT 1""",
            (f"%{title_keyword}%", account_name) + restrict_params,
            operation_name='按关键词查询图片素材')
        if result:
            return result[0]

    result = fetch_with_retry(
        connect_kwargs,
        f"""SELECT id FROM image_frames WHERE (user = %s OR user IS NULL)
            {restrict_sql} ORDER BY RAND() LIMIT 1""",
        (account_name,) + restrict_params, operation_name='随机查询图片素材')
    return result[0] if result else None


def get_afr_random_id(screen):
    """
    从数据库随机获取一个存在的 id

    返回：
        随机的 id 值，若查询失败则返回 None
    """
    result = fetch_with_retry(
        dict(host=host, database=database, user=user, password=password, port=port),
        """SELECT id FROM materials WHERE screen = %s
           AND material_application = '三农素材'
           AND is_quality_issue = 0 AND video_down_status = 1
           AND video_resolution_status = 1 ORDER BY RAND() LIMIT 1""",
        (screen,), dictionary=True, operation_name='随机查询三农素材')
    return result['id'] if result else None


def _get_afr_videos_by_keyword_once(first_keyword, screen, audio_length, poorTime=20):
    """按首标签查询可用的三农素材候选。"""
    if not first_keyword:
        return []

    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
            connection_timeout=15,
            read_timeout=QUERY_TIMEOUT,
            write_timeout=QUERY_TIMEOUT,
        )
        if not connection.is_connected():
            return None

        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT * FROM materials
            WHERE tags LIKE %s
              AND material_application = '三农素材'
              AND is_quality_issue = 0
              AND video_down_status = 1
              AND video_resolution_status = 1
              AND screen = %s
              AND CAST(duration AS UNSIGNED) BETWEEN %s - %s AND %s + %s
            ORDER BY RAND()
            LIMIT 20
            """,
            (f"%{first_keyword}%", screen, audio_length, poorTime, audio_length, poorTime),
        )
        return cursor.fetchall()
    except Error as e:
        print(f"按标签查询三农素材失败: {e}")
        return None
    except Exception as e:
        print(f"按标签查询三农素材出现异常: {e}")
        return None
    finally:
        if cursor:
            try:
                cursor.close()
            except Error:
                pass
        if connection:
            try:
                if connection.is_connected():
                    connection.close()
            except Error:
                pass


def get_afr_videos_by_keyword(first_keyword, screen, audio_length, poorTime=20):
    """按标签获取三农素材，返回候选记录列表。"""
    for attempt in range(1, 4):
        videos = _get_afr_videos_by_keyword_once(first_keyword, screen, audio_length, poorTime)
        if videos is not None:
            return videos
        print(f"按标签查询三农素材失败，准备重试（{attempt}/3）")
        if attempt < 3:
            time.sleep(1)
    return []


# 下载封面视频
def download_cover_video(cover_video_id):
    parent_dir = os.getcwd()
    # 构造同级的缓存文件夹路径
    cache_dir = os.path.join(parent_dir, 'cacheCoverVideo')
    # 确保缓存文件夹存在
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # 保存视频文件
    file_path = os.path.join(cache_dir, f'{cover_video_id}.mp4')

    # 获取封面视频下载地址
    FTP_file_path = get_3s_video_url(cover_video_id)
    if not FTP_file_path:
        set_material_download_error(f'封面素材 {cover_video_id}没有可用的下载地址')
        return ''

    try:
        url = FTP_file_path if 'http' in FTP_file_path else f'http://100.122.91.10:8991/{FTP_file_path}'
        auth = ('xiaoling', 'XL#!_+Dj@!DYN7MzicAkXw') if '100.122.91.10' in url else None
        if not download_to_cache(url, file_path, f'封面素材 {cover_video_id}', auth=auth):
            return ''

        try:
            # 目标分辨率（1080p）
            target_width = 1920
            target_height = 1080

            # 获取原始视频的分辨率
            original_resolution = get_video_resolution(file_path)
            if not original_resolution:
                os.remove(file_path)
                if not download_to_cache(url, file_path, f'封面素材 {cover_video_id}', auth=auth):
                    return ''
                original_resolution = get_video_resolution(file_path)
            if not original_resolution:
                set_material_download_error(f'封面素材 {cover_video_id}不是可读取的视频文件')
                return ''
            if original_resolution and original_resolution[0] == target_width and original_resolution[
                1] == target_height:
                print(f"视频已经是1080p，跳过处理: {file_path}")
                return file_path
            if original_resolution and original_resolution[0] == target_height and original_resolution[
                1] == target_width:
                print(f"视频已经是1080p，跳过处理: {file_path}")
                return file_path

            # 构建输出路径（与原视频同名，但放在输出文件夹中）
            output_path = os.path.splitext(file_path)[0] + "_processed.mp4"

            # 处理视频
            if original_resolution[0] < original_resolution[1]:
                result = process_vertical_video(file_path, output_path)
            else:
                result = process_across_video(file_path, output_path)
            if result:
                # 删除原始视频
                os.remove(file_path)
                # 将处理后的视频重命名为原始名称
                os.rename(output_path, file_path)
                print(f"处理完成并替换原始文件: {file_path}")
            else:
                set_material_download_error(f'封面素材 {cover_video_id}转码失败')
                return ''
        except Exception as e:
            print(f"处理分辨率视频出错: {file_path} -> {e}")
            set_material_download_error(f'封面素材 {cover_video_id}处理异常：{e}')
            return ''
        return file_path
    except Exception as e:
        print(f'视频下载失败{e}')
        set_material_download_error(f'封面素材 {cover_video_id}下载/处理异常：{e}')
        return ''


# 下载视频
def download_video(video_id, screen):
    parent_dir = os.getcwd()
    # 构造同级的缓存文件夹路径
    cache_dir = os.path.join(parent_dir, 'cacheVideo')
    # 确保缓存文件夹存在
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # 保存视频文件
    file_path = os.path.join(cache_dir, f'{video_id}.mp4')

    # 已存在且可读取的本地素材直接复用，断网时不再查询下载地址。
    if get_video_resolution(file_path):
        return file_path

    video_url = get_video_url(video_id)
    auth = ('xiaoling', 'XL#!_+Dj@!DYN7MzicAkXw') if video_url and '100.122.91.10' in video_url else None
    if not download_to_cache(video_url, file_path, f'素材 {video_id}', auth=auth):
        return ''

    # 普通素材无需在下载阶段强制转码；只要视频可读，就交给后续裁剪/合成。
    original_resolution = get_video_resolution(file_path)
    if not original_resolution:
        try:
            os.remove(file_path)
        except OSError:
            pass
        if not download_to_cache(video_url, file_path, f'素材 {video_id}', auth=auth):
            return ''
        original_resolution = get_video_resolution(file_path)
    if not original_resolution:
        set_material_download_error(f'素材 {video_id}不是可读取的视频文件')
        return ''
    return file_path


# 下载视频
def download_cn_video(video_id, screen):
    parent_dir = os.getcwd()
    # 构造同级的缓存文件夹路径
    cache_dir = os.path.join(parent_dir, 'cacheCNVideo')
    # 确保缓存文件夹存在
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # 保存视频文件
    file_path = os.path.join(cache_dir, f'{video_id}.mp4')

    if get_video_resolution(file_path):
        return file_path

    video_url = get_video_url(video_id)
    auth = ('xiaoling', 'XL#!_+Dj@!DYN7MzicAkXw') if video_url and '100.122.91.10' in video_url else None
    if not download_to_cache(video_url, file_path, f'国内素材 {video_id}', auth=auth):
        return ''

    original_resolution = get_video_resolution(file_path)
    if not original_resolution:
        try:
            os.remove(file_path)
        except OSError:
            pass
        if not download_to_cache(video_url, file_path, f'国内素材 {video_id}', auth=auth):
            return ''
        original_resolution = get_video_resolution(file_path)
    if not original_resolution:
        set_material_download_error(f'国内素材 {video_id}不是可读取的视频文件')
        return ''

    target_resolution = (1920, 1080) if screen == 1 else (1080, 1920)
    if original_resolution == target_resolution:
        return file_path

    output_path = os.path.splitext(file_path)[0] + "_processed.mp4"
    result = process_vertical_video(file_path, output_path) if screen == 0 else process_across_video(file_path, output_path)
    if not result:
        set_material_download_error(f'国内素材 {video_id}转码失败')
        return ''
    os.replace(output_path, file_path)
    return file_path


# 下载三农视频
def download_afr_video(video_id):
    parent_dir = os.getcwd()
    # 构造同级的缓存文件夹路径
    cache_dir = os.path.join(parent_dir, 'cacheAFRVideo')
    # 确保缓存文件夹存在
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # 保存视频文件
    file_path = os.path.join(cache_dir, f'{video_id}.mp4')

    if get_video_resolution(file_path):
        return file_path

    video_url = get_video_url(video_id)
    if not video_url:
        set_material_download_error(f'三农素材 {video_id}没有可用的下载地址')
        return ''

    auth = ('xiaoling', 'XL#!_+Dj@!DYN7MzicAkXw') if '100.122.91.10' in video_url else None
    if not download_to_cache(video_url, file_path, f'三农素材 {video_id}', auth=auth):
        return ''

    try:
        # if not os.path.exists(file_path):
        #     if 'http' in FTP_file_path:
        #         url = FTP_file_path
        #     else:
        #         # url = f'http://182.110.69.75:8991/' + FTP_file_path  # 将 <filename> 替换为实际的视频文件名
        #         url = f'http://100.122.91.10:8991/' + FTP_file_path  # 将 <filename> 替换为实际的视频文件名
        #
        #     # 🚀 优化：使用流式下载和连接复用
        #     session = requests.Session()
        #
        #     # 设置连接池
        #     adapter = requests.adapters.HTTPAdapter(
        #         pool_connections=10,
        #         pool_maxsize=10,
        #         max_retries=3
        #     )
        #     session.mount('http://', adapter)
        #     session.mount('https://', adapter)
        #
        #     if '100.122.91.10' in url:
        #         response = session.get(url, auth=('xiaoling', 'XL#!_+Dj@!DYN7MzicAkXw'), timeout=(30, 300), stream=True)
        #     else:
        #         # 跳过SSL验证（处理证书过期问题）
        #         response = session.get(url, timeout=(30, 300), stream=True, verify=False)
        #
        #     if response.status_code == 200:
        #         # 🚀 优化：流式下载，减少内存占用
        #         with open(file_path, 'wb') as f:
        #             for chunk in response.iter_content(chunk_size=8192):
        #                 if chunk:
        #                     f.write(chunk)
        #         print('视频下载成功')

        try:
            # 目标分辨率（1080p）
            target_width = 1920
            target_height = 1080

            # 获取原始视频的分辨率
            original_resolution = get_video_resolution(file_path)
            if not original_resolution:
                os.remove(file_path)
                if not download_to_cache(video_url, file_path, f'三农素材 {video_id}', auth=auth):
                    return ''
                original_resolution = get_video_resolution(file_path)
            if not original_resolution:
                set_material_download_error(f'三农素材 {video_id}不是可读取的视频文件')
                return ''
            if original_resolution and original_resolution[0] == target_width and original_resolution[
                1] == target_height:
                print(f"视频已经是1080p，跳过处理: {file_path}")
                return file_path
            if original_resolution and original_resolution[0] == target_height and original_resolution[
                1] == target_width:
                print(f"视频已经是1080p，跳过处理: {file_path}")
                return file_path

            # 构建输出路径（与原视频同名，但放在输出文件夹中）
            output_path = os.path.splitext(file_path)[0] + "_processed.mp4"

            # 处理视频
            if original_resolution[0] < original_resolution[1]:
                result = process_vertical_video(file_path, output_path)
            else:
                result = process_across_video(file_path, output_path)
            if result:
                # 删除原始视频
                os.remove(file_path)
                # 将处理后的视频重命名为原始名称
                os.rename(output_path, file_path)
                print(f"处理完成并替换原始文件: {file_path}")
            else:
                set_material_download_error(f'三农素材 {video_id}转码失败')
                return ''
        except Exception as e:
            print(f"处理分辨率视频出错: {file_path} -> {e}")
            set_material_download_error(f'三农素材 {video_id}处理异常：{e}')
            return ''
        return file_path
    except Exception as e:
        print(f'视频下载失败{e}')
        set_material_download_error(f'三农素材 {video_id}下载/处理异常：{e}')
        return ''


# 下载图片
def download_word_pic(pic_id):
    cfg = read_ftp_config()
    ftp_host = cfg['ftp_host']
    ftp_user = cfg['ftp_user']
    ftp_pass = cfg['ftp_pass']
    ftp_port = cfg.get('ftp_port', 21)

    cache_dir = os.path.join(os.getcwd(), 'touristPictures')
    os.makedirs(cache_dir, exist_ok=True)
    for suffix in ('.jpg', '.jpeg', '.png', '.webp'):
        cached_path = os.path.join(cache_dir, f'{pic_id}{suffix}')
        if os.path.exists(cached_path):
            return cached_path

    if ftp_host in BANNED_FTP_HOSTS:
        print(f'已禁用远程 FTP 下载（{ftp_host}），本地无图片 {pic_id}')
        return None

    try:
        ftp = FTP()
        ftp.connect(host=ftp_host, port=ftp_port)
        ftp.login(user=ftp_user, passwd=ftp_pass)

        remote_dir = "/generated_pic"
        ftp.cwd(remote_dir)

        # 本地保存路径
        cache_dir = os.path.join(os.getcwd(), 'touristPictures')
        os.makedirs(cache_dir, exist_ok=True)

        # FTP 端文件名
        file_name = os.path.basename(get_pic_url(pic_id))   # 去掉 /generated_pic/
        local_path = os.path.join(cache_dir, f'{pic_id}.jpg')

        # 下载
        with open(local_path, 'wb') as f:
            ftp.retrbinary(f'RETR {file_name}', f.write)
        ftp.quit()

        print(f'图片 {file_name} 下载成功 → {local_path}')

        # ====== 分辨率检查（文件已存在） ======
        try:
            target_w, target_h = 1080, 1920          # 竖屏 1080p
            orig_w, orig_h = get_image_resolution(local_path)
            if orig_w == target_w and orig_h == target_h:
                print(f'图片已是竖屏1080p，跳过处理: {local_path}')
        except Exception as e:
            print(f'分辨率检查出错: {e}')

        return local_path

    except Exception as e:
        print(f'下载失败: {e}')
        return str(e)


# 下载人物图片
def download_person_pic(pic_id):
    cfg = read_ftp_config()
    ftp_host = cfg['ftp_host']
    ftp_user = cfg['ftp_user']
    ftp_pass = cfg['ftp_pass']
    ftp_port = cfg.get('ftp_port', 21)

    if ftp_host in BANNED_FTP_HOSTS:
        print(f'已禁用远程 FTP 下载（{ftp_host}），跳过人物图片 {pic_id}')
        return None

    try:
        ftp = FTP()
        ftp.connect(host=ftp_host, port=ftp_port)
        ftp.login(user=ftp_user, passwd=ftp_pass)

        remote_dir = "/person_images"
        ftp.cwd(remote_dir)

        # 本地保存路径
        cache_dir = os.path.join(os.getcwd(), 'touristPictures')
        os.makedirs(cache_dir, exist_ok=True)

        # 获取远程目录中的文件列表
        file_list = ftp.nlst()
        
        # 尝试匹配文件名：支持 {pic_id}.{ext} 或 person_{pic_id}.{ext}
        file_found = None
        for file_name in file_list:
            base_name, ext = os.path.splitext(file_name)
            if base_name == str(pic_id) or base_name == f"person_{pic_id}":
                file_found = file_name
                break
        
        if not file_found:
            print(f"在 /person_images 目录中未找到ID为 {pic_id} 的人物图片")
            ftp.quit()
            return None
        
        local_path = os.path.join(cache_dir, file_found)

        # 下载
        with open(local_path, 'wb') as f:
            ftp.retrbinary(f'RETR {file_found}', f.write)
        ftp.quit()

        print(f'人物图片 {file_found} 下载成功 -> {local_path}')

        return local_path

    except Exception as e:
        print(f'下载人物图片失败: {e}')
        return None


# 按音频时长随机截取视频长度
def cut_video_by_audio_length(video_path, video_id, audio_length):
    """
    按音频时长截取视频，精确截取并修复结尾卡顿问题。

    优化方案：
    1. 使用 accurate_seek 精确定位到起始时间
    2. 直接重新编码，避免流复制的不精确性
    3. 强制关键帧对齐，确保开头和结尾都是关键帧
    4. 精确控制时长，避免累积误差

    :param video_path: 原视频路径
    :param video_id: 视频ID
    :param audio_length: 目标时长（秒）
    :return: 截取后的视频路径
    """
    if not os.path.exists(video_path):
        print(f'视频文件不存在: {video_path}')
        return ''

    # 获取当前工作目录
    parent_dir = os.getcwd()
    # 构造同级的缓存文件夹路径
    cache_dir = os.path.join(parent_dir, 'cacheCutVideo')
    # 确保缓存文件夹存在
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # 时间戳
    timestamp = str(int(time.time()))

    # 保存视频文件
    cut_file_path = os.path.join(cache_dir, f'cut_{timestamp}_{video_id}.mp4')
    # 视频时长
    original_video_length = get_video_duration(video_path)

    # 音频时长大于视频时长，直接复制返回
    if audio_length >= original_video_length:
        shutil.copy(video_path, cut_file_path)
        return cut_file_path

    # 随机选择一个起始时间点（预留0.5秒缓冲，确保能完整截取）
    max_start_time = max(0, original_video_length - audio_length - 0.5)
    start_time = random.uniform(0, max_start_time)

    try:
        # 🔥 优化方案：直接使用 accurate_seek + 重新编码，一步到位
        # 避免两步处理导致的时长累积误差
        encode_command = [
            "ffmpeg", "-y",
            # 🔥 精确定位：在输入前使用 -ss 更精确
            "-ss", f"{start_time:.3f}",
            "-accurate_seek",
            "-i", video_path,
            # 🔥 精确截取时长
            "-t", f"{audio_length:.3f}",
            # 🔥 视频编码：强制关键帧对齐
            "-c:v", "libx264",
            "-preset", "fast",           # 快速编码
            "-crf", "23",               # 良好质量
            # 🔥 关键帧控制：确保开头和结尾都是关键帧
            "-force_key_frames", "expr:gte(t,n_forced*1)",  # 每秒强制关键帧
            "-keyint_min", "30",          # 最小关键帧间隔30帧
            "-g", "30",                   # GOP大小30帧(约1秒)
            "-sc_threshold", "0",          # 禁用场景切换检测，强制固定GOP
            # 🔥 音频编码：统一参数
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",               # 统一采样率
            # 🔥 时间戳处理：确保时序连续
            "-fflags", "+genpts",         # 生成准确时间戳
            "-avoid_negative_ts", "make_zero",  # 处理负时间戳
            "-movflags", "+faststart",     # 优化播放性能
            cut_file_path
        ]

        print(f'开始截取视频: 起始={start_time:.3f}s, 目标时长={audio_length:.3f}s')

        result = subprocess.run(
            encode_command,
            check=False,
            encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )

        if result.returncode != 0:
            print(f'视频截取失败: {result.stderr}')
            return ''

        # 验证输出视频时长是否接近目标时长
        output_duration = get_video_duration(cut_file_path)
        duration_diff = abs(output_duration - audio_length)

        if duration_diff > 0.2:  # 🔥 严格检查：允许0.2秒误差
            print(f'视频时长偏差较大:')
            print(f'   目标={audio_length:.3f}s, 实际={output_duration:.3f}s, 差值={duration_diff:.3f}s')

            # 如果偏差太大，重新调整截取
            if duration_diff > 1.0:
                print(f'偏差过大，尝试修正...')
                # 计算调整后的时长
                adjusted_duration = audio_length + (audio_length - output_duration)
                return cut_video_by_audio_length(video_path, f"{video_id}_retry", adjusted_duration)
        else:
            print(f'视频截取成功（精确时长+关键帧对齐）: {cut_file_path}')
            print(f'   起始={start_time:.3f}s, 时长={output_duration:.3f}s, 差值={duration_diff:.3f}s')

        return cut_file_path

    except subprocess.TimeoutExpired:
        print(f'视频截取超时（>300秒）')
        return ''
    except Exception as e:
        print(f'按音频时长截取视频失败: {e}')
        return ''


def reencode_video(input_path, output_path):
    """
    将视频重新编码为 H.264 视频流和 AAC 音频流。
    :param input_path: 输入视频文件路径
    :param output_path: 输出视频文件路径
    """
    command = [
        "ffmpeg",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-y",
        output_path
    ]
    subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=600)


def reencode_video_with_keyframe(input_path, output_path):
    """
    将视频画面重新编码为 H.264，并强制从零时间戳和关键帧开始。
    用于 concat demuxer 合并前的预处理，确保每段都是关键帧开头。

    :param input_path: 输入视频文件路径
    :param output_path: 输出视频文件路径
    """
    command = [
        "ffmpeg",
        "-i", input_path,
        "-map", "0:v:0",
        "-vf", "fps=30,setsar=1,format=yuv420p,settb=1/30,setpts=N",
        "-c:v", "libx264",
        "-preset", "fast",        # 快速编码
        "-crf", "23",
        "-fps_mode", "cfr",
        "-force_key_frames", "expr:gte(t,n_forced*1)",  # 每秒强制关键帧
        "-keyint_min", "30",      # 最小关键帧间隔30帧
        "-g", "30",               # GOP大小30帧(约1秒)
        "-sc_threshold", "0",    # 禁用场景切换检测，强制固定GOP
        "-an",
        "-fflags", "+genpts",     # 生成准确时间戳
        "-avoid_negative_ts", "make_zero",
        "-movflags", "+faststart",
        "-y",
        output_path
    ]
    subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=600)


def merge_videos(video_paths, id_str):
    """
    将多个视频地址合并成一个视频并返回合并后的视频地址。
    修复了第二段视频画面卡住的问题。

    优化方案：
    1. 每个视频片段重新编码时强制关键帧对齐
    2. 移除 vsync/async 参数，避免帧率调整
    3. 固定 GOP 结构，确保每个片段开头结尾都是关键帧
    4. 增加详细的日志输出，便于排查问题

    :param id_str: 用于标识输出文件的字符串
    :param video_paths: 视频文件路径列表
    :return: 合并后的视频文件路径
    """
    try:
        # 创建输出文件夹
        parent_dir = Path.cwd()
        out_dir = parent_dir / 'cacheCutVideo'
        out_dir.mkdir(exist_ok=True)

        # 时间戳
        timestamp = str(int(time.time()))

        # 构造输出文件名
        output_file_name = f"merged_{timestamp}_{id_str}.mp4"
        output_file_path = out_dir / output_file_name

        print(f'开始合并视频: {len(video_paths)} 个片段')
        print(f'   输出文件: {output_file_name}')

        # 重新编码视频，确保每段都从关键帧开始
        reencoded_video_paths = []
        expected_duration = 0.0
        for i, video_path in enumerate(video_paths):
            reencoded_path = out_dir / f"reencoded_{i}_{os.path.basename(video_path)}"

            # 验证输入文件存在
            if not os.path.exists(video_path):
                print(f'输入视频不存在: {video_path}')
                return ''

            # 获取输入视频时长
            input_duration = get_video_duration(video_path)
            print(f'   片段{i+1}: {os.path.basename(video_path)}, 时长={input_duration:.2f}s')

            # 使用关键帧强制编码，确保每段都是关键帧开头
            try:
                reencode_video_with_keyframe(video_path, reencoded_path)
            except Exception as e:
                print(f'重新编码片段{i+1}失败: {e}')
                return ''

            # 验证输出视频时长
            output_duration = get_video_duration(str(reencoded_path))
            duration_diff = abs(output_duration - input_duration)
            if duration_diff > 0.5:
                print(f'   片段{i+1}时长偏差: {duration_diff:.3f}s')
            else:
                print(f'   片段{i+1}重新编码成功: 时长={output_duration:.2f}s')

            reencoded_video_paths.append(reencoded_path)
            expected_duration += output_duration

        # 创建一个临时文件，用于存储视频文件的路径
        temp_file_path = out_dir / f"temp_{timestamp}_{id_str}.txt"
        with open(temp_file_path, "w", encoding='utf-8') as temp_file:
            for video_path in reencoded_video_paths:
                temp_file.write(f"file '{video_path}'\n")

        print(f'合并列表文件: {temp_file_path}')

        # 使用 FFmpeg 合并视频并重新编码
        # 修复：移除 vsync/async 参数，使用更精确的时序控制
        command = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(temp_file_path),
            "-map", "0:v:0",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            # 🔥 关键帧控制：确保每个片段开头都是关键帧
            "-keyint_min", "30",  # 最小关键帧间隔
            "-g", "30",           # 关键帧间隔30帧(约1秒)
            "-sc_threshold", "0", # 禁用场景切换检测，强制固定关键帧
            # 这里只合并画面，旁白和音乐会在后续阶段统一加入。
            # 不让缺失或过短的素材音轨通过 -shortest 截断后续画面。
            "-an",
            # 🔥 时间戳处理：确保时序连续
            "-fflags", "+genpts", # 生成准确时间戳
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            "-y",
            str(output_file_path)
        ]

        print(f'开始合并视频...')
        result = subprocess.run(
            command,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )

        if result.returncode != 0:
            print(f'合并视频失败: {result.stderr}')
            # 清理临时文件
            for reencoded_path in reencoded_video_paths:
                if os.path.exists(reencoded_path):
                    try:
                        os.remove(reencoded_path)
                    except:
                        pass
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            return ''

        # 验证合并结果
        if not os.path.exists(output_file_path):
            print(f'合并输出文件不存在: {output_file_path}')
            return ''

        merged_duration = get_video_duration(str(output_file_path))
        print(f'合并视频成功: {output_file_name}, 总时长={merged_duration:.2f}s')

        if abs(merged_duration - expected_duration) > 0.5:
            print(f'合并视频时长校验失败: 期望={expected_duration:.2f}s, 实际={merged_duration:.2f}s')
            try:
                os.remove(output_file_path)
            except OSError:
                pass
            try:
                os.remove(temp_file_path)
                for reencoded_path in reencoded_video_paths:
                    os.remove(reencoded_path)
            except OSError:
                pass
            return ''

        # 删除临时文件和重新编码的视频文件
        try:
            os.remove(temp_file_path)
            for reencoded_path in reencoded_video_paths:
                os.remove(reencoded_path)
            print(f'清理临时文件完成')
        except Exception as e:
            print(f'清理临时文件时出错: {e}')

        return str(output_file_path)

    except subprocess.TimeoutExpired:
        print(f'合并视频超时（>600秒）')
        return ''
    except Exception as e:
        print(f'合并封面视频失败: {e}')
        return ''


def merge_videos_with_duration(video_paths, id_str, audio_length):
    """
    将多个视频地址合并成一个指定时长的视频。
    每个视频按比例截取时长，使总时长等于 audio_length。

    :param video_paths: 视频文件路径列表
    :param id_str: 用于标识输出文件的字符串
    :param audio_length: 目标音频时长（秒）
    :return: 合并后的视频文件路径，失败返回空字符串
    """
    try:
        # 创建输出文件夹
        parent_dir = Path.cwd()
        out_dir = parent_dir / 'cacheCutVideo'
        out_dir.mkdir(exist_ok=True)

        # 时间戳
        timestamp = str(int(time.time()))

        # 构造输出文件名
        output_file_name = f"merged_{timestamp}_{id_str}_{audio_length}s.mp4"
        output_file_path = out_dir / output_file_name

        # 计算每个视频应该截取的时长
        video_count = len(video_paths)
        if video_count == 0:
            print(f'视频列表为空')
            return ''

        # 每个视频的平均时长
        avg_duration = audio_length / video_count
        min_clip_duration = 0.5  # 每个片段最小0.5秒

        # 计算实际每个视频的截取时长
        clip_durations = []
        for i in range(video_count):
            if i < video_count - 1:
                # 前面的视频按平均时长分配，至少0.5秒
                clip_duration = max(avg_duration, min_clip_duration)
                clip_durations.append(clip_duration)
            else:
                # 最后一个视频：目标时长减去前面的总时长
                used_duration = sum(clip_durations)
                clip_duration = audio_length - used_duration
                if clip_duration < min_clip_duration:
                    clip_duration = min_clip_duration
                clip_durations.append(clip_duration)

        # 截取每个视频片段
        clip_video_paths = []
        for video_path, clip_duration in zip(video_paths, clip_durations):
            if not os.path.exists(video_path):
                print(f'视频文件不存在: {video_path}')
                continue

            # 获取原始视频时长
            original_duration = get_video_duration(video_path)

            # 计算截取时长（如果原视频比目标短，使用原视频时长）
            actual_clip_duration = min(clip_duration, original_duration)

            # 随机选择起始时间点
            if original_duration > actual_clip_duration:
                start_time = random.uniform(0, original_duration - actual_clip_duration)
            else:
                start_time = 0

            # 构造输出文件名
            clip_file_name = f"clip_{timestamp}_{os.path.basename(video_path)}_{clip_duration:.1f}s.mp4"
            clip_file_path = out_dir / clip_file_name

            # 使用 FFmpeg 截取视频
            command = [
                "ffmpeg", "-y",
                "-ss", f"{start_time:.3f}",
                "-accurate_seek",
                "-i", video_path,
                "-t", f"{actual_clip_duration:.3f}",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "48000",
                "-avoid_negative_ts", "make_zero",
                "-fflags", "+genpts",
                "-movflags", "+faststart",
                str(clip_file_path)
            ]

            result = subprocess.run(command, check=False, encoding='utf-8',
                                    creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True, text=True, timeout=300)

            if result.returncode == 0 and os.path.exists(clip_file_path):
                clip_video_paths.append(str(clip_file_path))
                print(f'视频片段截取成功: {clip_duration:.1f}s')
            else:
                print(f'视频片段截取失败: {result.stderr}')

        # 检查是否有成功截取的片段
        if len(clip_video_paths) == 0:
            print(f'所有视频片段截取失败')
            return ''

        # 创建一个临时文件，用于存储视频文件的路径
        temp_file_path = out_dir / f"temp_{timestamp}_{id_str}.txt"
        with open(temp_file_path, "w") as temp_file:
            for clip_path in clip_video_paths:
                temp_file.write(f"file '{clip_path}'\n")

        # 使用 FFmpeg 合并视频并重新编码
        command = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(temp_file_path),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-vsync", "1",
            "-async", "1",
            "-movflags", "+faststart",
            # 不强制映射流，让ffmpeg自动处理缺失音频的视频
            "-shortest",
            "-y",
            str(output_file_path)
        ]
        result = subprocess.run(command, check=False, encoding='utf-8',
                                creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True, text=True, timeout=600)

        # 删除临时文件和截取的视频片段
        os.remove(temp_file_path)
        for clip_path in clip_video_paths:
            try:
                os.remove(clip_path)
            except Exception as e:
                print(f'删除临时文件失败: {e}')

        if result.returncode == 0 and os.path.exists(output_file_path):
            print(f'视频合并成功: {output_file_path}')
            return str(output_file_path)
        else:
            print(f'视频合并失败: {result.stderr}')
            return ''

    except Exception as e:
        print(f'合并视频失败（按时长）: {e}')
        return ''


# def download_music(music_id):
#     parent_dir = os.getcwd()  #
#     # 构造同级的缓存文件夹路径
#     cache_dir = os.path.join(parent_dir, 'cacheMusic3')
#     # 确保缓存文件夹存在
#     if not os.path.exists(cache_dir):
#         os.makedirs(cache_dir)
#
#     # 保存视频文件
#     file_path = os.path.join(cache_dir, f'{music_id}.mp4')
#
#     # FTP_file_path = get_video_url(video_id)
#
#     try:
#         if not os.path.exists(file_path):
#             # url = f'http://182.110.69.75:8991/music/{music_id}.mp3'  # 将 <filename> 替换为实际的视频文件名
#             url = f'http://100.122.91.10:8991/' + FTP_file_path  # 将 <filename> 替换为实际的视频文件名
#             response = requests.get(url, auth=('xiaoling', 'XL#!_+Dj@!DYN7MzicAkXw'), timeout=(120, 120))
#
#             if response.status_code == 200:
#                 with open(file_path, 'wb') as f:  # 获取服务器上的视频 检索
#                     f.write(response.content)
#                 print('音乐下载成功')
#
#         return file_path
#     except Exception as e:
#         print(f'音乐下载失败{e}')
#         return False


def ftp_upload(video_id, local_file_path):
    # FTP服务器信息
    ftp_host = '100.122.91.10'
    ftp_user = 'sp_sucai_admin'
    ftp_pass = '735@eaee72b6c634500!dd'
    ftp_port = 9901
    # 连接到FTP服务器
    ftp = FTP()
    ftp.connect(host=ftp_host, port=ftp_port)
    ftp.login(user=ftp_user, passwd=ftp_pass)

    # 提取文件的后缀（例如 .mp4）
    file_extension = os.path.splitext(local_file_path)[1]

    # 上传文件
    remote_file_path = f'{video_id}{file_extension}'  # 远程文件路径

    with open(local_file_path, 'rb') as file:
        ftp.storbinary(f'STOR {remote_file_path}', file)

    print(f'File {local_file_path} uploaded to {remote_file_path} successfully.')

    # 断开连接
    ftp.quit()


# 上传视频 图片
def ftp_ai_upload(video_id, local_file_path):
    try:
        # FTP服务器信息
        ftp_host = '100.122.91.10'
        ftp_user = 'video_site_admin'
        ftp_pass = '735@eaee72b6c634500!dd'
        ftp_port = 9903
        # 连接到FTP服务器
        ftp = FTP()
        ftp.connect(host=ftp_host, port=ftp_port)
        ftp.login(user=ftp_user, passwd=ftp_pass)

        # 提取文件的后缀（例如 .mp4）
        video_file_extension = os.path.splitext(local_file_path)[1]

        # 上传文件
        # 当天日期文件夹，如 20240731
        date_folder = datetime.datetime.now().strftime("%Y%m%d")  # 或 "%Y/%m/%d"
        remote_dir = f"/{date_folder}"
        _make_ftp_dirs(ftp, remote_dir)

        # 视频存储位置
        video_remote_file_path = f"{remote_dir}/{video_id}{video_file_extension}"  # 远程文件路径

        with open(local_file_path, 'rb') as file:
            ftp.storbinary(f'STOR {video_remote_file_path}', file)

        # 截取两张视频图片
        pic_saved_paths = random_snapshots(local_file_path)
        pic_file_extension = os.path.splitext(pic_saved_paths[0])[1]

        # 图片存储位置
        pic_0_remote_file_path = f"{remote_dir}/{video_id}_0{pic_file_extension}"  # 远程文件路径 图片1
        pic_1_remote_file_path = f"{remote_dir}/{video_id}_1{pic_file_extension}"  # 远程文件路径 图片2

        if os.path.exists(pic_saved_paths[0]) and os.path.exists(pic_saved_paths[1]):
            with open(pic_saved_paths[0], 'rb') as file:
                ftp.storbinary(f'STOR {pic_0_remote_file_path}', file)

            with open(pic_saved_paths[1], 'rb') as file:
                ftp.storbinary(f'STOR {pic_1_remote_file_path}', file)

        time.sleep(3)

        if os.path.exists(pic_saved_paths[0]):
            os.remove(pic_saved_paths[0])

        if os.path.exists(pic_saved_paths[1]):
            os.remove(pic_saved_paths[1])

        pic_remote_file_path_str = pic_0_remote_file_path + ',' + pic_1_remote_file_path

        print(f'File {local_file_path} uploaded to {video_remote_file_path} successfully.')

        # 断开连接
        ftp.quit()
        return video_remote_file_path, pic_remote_file_path_str
    except Exception as e:
        print(f'上传视频失败{str(e)}')
        return '', ''


#
#
# def random_snapshots(video_path: str, output_dir: str = "snapshots") -> list:
#     """
#     从视频中随机截取两张图片，间隔至少10秒，保存到指定文件夹中。
#     :param video_path: 视频文件路径
#     :param output_dir: 输出文件夹名称
#     :return: 两张图片的完整路径列表
#     """
#     # 创建输出文件夹
#     out_dir = Path.cwd() / output_dir
#     out_dir.mkdir(exist_ok=True)
#
#     # 打开视频
#     cap = cv2.VideoCapture(video_path)
#     if not cap.isOpened():
#         raise IOError("无法打开视频文件")
#
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#     min_interval_frames = int(fps * 10)  # 10秒对应的帧数
#
#     if total_frames < min_interval_frames * 2:
#         raise ValueError("视频太短，无法截取两张间隔至少10秒的图片")
#
#     # 随机选择两个帧，确保间隔至少10秒
#     frame_ids = random.sample(range(total_frames), 2)
#     frame_ids.sort()
#
#     saved_paths = []
#     for idx, fid in enumerate(frame_ids, 1):
#         cap.set(cv2.CAP_PROP_POS_FRAMES, fid)
#         ret, frame = cap.read()
#         if not ret:
#             continue
#
#         # 构造文件名：时间戳_序号.png
#         timestamp = int(time.time() * 1000)  # 当前时间戳，毫秒级
#         filename = f"{timestamp}_{idx}.png"
#         file_path = out_dir / filename
#
#         # 保存图片
#         cv2.imwrite(str(file_path), frame)
#         saved_paths.append(str(file_path))
#
#     cap.release()
#
#     if len(saved_paths) != 2:
#         raise RuntimeError("截图失败")
#
#     return saved_paths
#

def random_snapshots(video_path: str, output_dir: str = "snapshots") -> list:
    """
    从视频中随机截取两张图片，间隔至少10秒，且不截取最后三秒的内容，保存到指定文件夹中。
    :param video_path: 视频文件路径
    :param output_dir: 输出文件夹名称
    :return: 两张图片的完整路径列表
    """
    # 创建输出文件夹
    out_dir = Path.cwd() / output_dir
    out_dir.mkdir(exist_ok=True)

    # 打开视频
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError("无法打开视频文件")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    min_interval_frames = int(fps * 10)  # 10秒对应的帧数
    last_three_seconds_frames = int(fps * 3)  # 最后三秒对应的帧数

    if total_frames < min_interval_frames * 2 + last_three_seconds_frames:
        raise ValueError("视频太短，无法截取两张间隔至少10秒且不包括最后三秒的图片")

    # 随机选择两个帧，确保间隔至少10秒且不包括最后三秒
    frame_ids = random.sample(range(total_frames - last_three_seconds_frames), 2)
    frame_ids.sort()

    saved_paths = []
    for idx, fid in enumerate(frame_ids, 1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fid)
        ret, frame = cap.read()
        if not ret:
            continue

        # 构造文件名：时间戳_序号.png
        timestamp = int(time.time() * 1000)  # 当前时间戳，毫秒级
        filename = f"{timestamp}_{idx}.png"
        file_path = out_dir / filename

        # 保存图片
        cv2.imwrite(str(file_path), frame)
        saved_paths.append(str(file_path))

    cap.release()

    if len(saved_paths) != 2:
        raise RuntimeError("截图失败")

    return saved_paths


# random_snapshots('123.mp4')

def _make_ftp_dirs(ftp, remote_dir):
    """逐级创建 FTP 目录"""
    parts = remote_dir.strip("/").split("/")
    path = ""
    for part in parts:
        path += f"/{part}"
        try:
            ftp.cwd(path)
        except error_perm:
            ftp.mkd(path)
            ftp.cwd(path)


def ftp_upload_music(video_id, local_file_path):
    # FTP服务器信息
    ftp_host = '100.122.91.10'
    ftp_user = 'sp_sucai_admin'
    ftp_pass = '735@eaee72b6c634500!dd'
    ftp_port = 9901
    # 连接到FTP服务器
    ftp = FTP()
    ftp.connect(host=ftp_host, port=ftp_port)
    ftp.login(user=ftp_user, passwd=ftp_pass)

    # 提取文件的后缀（例如 .mp4）
    file_extension = os.path.splitext(local_file_path)[1]

    # 切换到远程音乐文件夹，如果不存在则创建
    # if '/music/' not in ftp.nlst():
    #     ftp.mkd(f'/music/')

    # 上传文件
    remote_file_path = f'/music/{video_id}{file_extension}'  # 远程文件路径

    with open(local_file_path, 'rb') as file:
        ftp.storbinary(f'STOR {remote_file_path}', file)

    print(f'File {local_file_path} uploaded to {remote_file_path} successfully.')

    # 断开连接
    ftp.quit()


def clean_cache_video():
    parent_dir = os.getcwd()
    # 构造同级的缓存文件夹路径
    cache_dir = os.path.join(parent_dir, 'cacheVideo')
    # 确保缓存文件夹存在
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)


# def get_video_resolution(video_path):
#     """获取视频分辨率"""
#     try:
#         probe = ffmpeg.probe(video_path)
#         video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
#         width = int(video_stream['width'])
#         height = int(video_stream['height'])
#         return width, height
#     except Exception as e:
#         print(f"获取视频分辨率出错: {e}")
#         return None


def get_video_resolution(video_path: str):
    """
    使用 ffprobe + subprocess 获取视频分辨率 (width, height)
    失败返回 None
    """
    if not os.path.isfile(video_path):
        return None

    # OpenCV 已随程序打包，优先用它校验缓存，避免仅因系统找不到 ffprobe
    # 就把已经下载成功的视频误报为“下载失败”。
    capture = cv2.VideoCapture(video_path)
    try:
        if capture.isOpened():
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if width > 0 and height > 0:
                return width, height
    finally:
        capture.release()

    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        video_path
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        data = json.loads(result.stdout)
        stream = data.get("streams", [{}])[0]
        width = int(stream.get("width"))
        height = int(stream.get("height"))
        if width and height:
            return width, height
    except Exception as e:
        print(f"获取视频分辨率出错: {e}")
    return None


# 获取图片的分辨率
def get_image_resolution(image_path: str):
    """
    使用 Pillow 获取图片分辨率 (width, height)
    失败返回 None
    """
    if not os.path.isfile(image_path):
        return None

    try:
        from PIL import Image

        with Image.open(image_path) as img:
            width, height = img.size
            return width, height
    except Exception as e:
        print(f"获取图片分辨率出错: {e}")
    return None


def process_vertical_video(input_path, output_path):
    """处理单个视频，将其转换为1080p"""
    try:
        # 目标分辨率（1080p）
        target_width = 1080
        target_height = 1920

        # 构建FFmpeg命令
        command = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-vf", (
                f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2"
            ),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]

        # 执行命令
        subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=600)
        print(f"成功处理: {input_path} -> {output_path}")
        return output_path

    except Exception as e:
        print(f"处理视频出错: {input_path} -> {e}")
        return None


def process_across_video(input_path, output_path):
    """处理单个视频，将其转换为1080p"""
    try:
        # 目标分辨率（1080p）
        target_width = 1920
        target_height = 1080

        # 构建FFmpeg命令
        command = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-vf", (
                f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2"
            ),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]

        # 执行命令
        subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=600)
        print(f"成功处理: {input_path} -> {output_path}")
        return output_path

    except Exception as e:
        print(f"处理视频出错: {input_path} -> {e}")
        return None


def get_screen_orientation(video_path):
    """
    判断视频是竖屏还是横屏。

    参数:
    video_path -- 视频文件路径

    返回:
    'horizontal' -- 横屏
    'vertical' -- 竖屏
    """
    from moviepy.video.io.VideoFileClip import VideoFileClip

    # 打开视频文件
    with VideoFileClip(video_path) as clip:
        width = clip.w
        height = clip.h
        # 判断屏幕方向
        if width > height:
            return 1  # 横屏
        else:
            return 0  # 竖屏


# 记录上传视频素材的信息
def add_lost_video_record(param):
    """
    添加新的视频记录到数据库

    参数：
        title: 视频标题
        first_tag: 一级标签
        second_tag: 二级标签
        video_location: 视频位置
        duration: 视频时长

    返回：
        如果插入成功返回 True，否则返回 False
    """
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='ai_video',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008',
            connection_timeout=15,
            read_timeout=QUERY_TIMEOUT,
            write_timeout=QUERY_TIMEOUT
        )

        if connection.is_connected():
            cursor = connection.cursor()
            query = f"""
                INSERT INTO lost_video_info 
                (title, first_tag, second_tag, duration, screen, account_name)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                param['title'], param['firstTags'], param['secondTags'], param['videoLength'],
                param['screen'], param['accountName'])
            cursor.execute(query, values)
            connection.commit()
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return False


# 记录上传视频素材的信息
def add_lost_cn_video_record(param):
    """
    添加新的视频记录到数据库

    参数：
        title: 视频标题
        first_tag: 一级标签
        second_tag: 二级标签
        video_location: 视频位置
        duration: 视频时长

    返回：
        如果插入成功返回 True，否则返回 False
    """
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='ai_video',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008'
        )

        if connection.is_connected():
            cursor = connection.cursor()
            query = f"""
                INSERT INTO lost_cn_video_info 
                (title, first_tag, second_tag, duration, screen, account_name, title_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                param['title'], param['firstTags'], param['secondTags'], param['videoLength'],
                param['screen'], param['accountName'], param['titleType'])
            cursor.execute(query, values)
            connection.commit()
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return False
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 获取所有的模板信息
def get_video_model_list():
    query = "SELECT * FROM video_model_set"
    result = fetch_with_retry(
        {
            'host': '82.157.237.217', 'database': 'ai_video',
            'user': 'ljx_lepin123', 'password': 'ea.367GZX!#EmwfpEYW$f', 'port': '35008'
        },
        query,
        fetch_all=True,
        dictionary=True,
        operation_name='获取视频模板列表',
    )
    if not result:
        return None, None, None, None
    columns = [(key,) for key in result[0].keys()]
    rows = [tuple(item.values()) for item in result]
    return columns, len(rows), len(rows[0]), rows


def delete_video_model(video_model_id):
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='ai_video',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008'
        )

        if connection.is_connected():
            cursor = connection.cursor()
            query = """
                DELETE FROM video_model_set 
                WHERE id = %s
            """
            cursor.execute(query, (video_model_id,))
            connection.commit()
            if cursor.rowcount > 0:
                return True
            else:
                return False
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return False
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def update_video_model(video_id, video_model_param):
    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='ai_video',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008'
        )
        if connection.is_connected():
            cursor = connection.cursor()
            sql = "UPDATE video_model_set SET model_name = %s, model_set = %s WHERE id = %s"
            cursor.execute(sql, (video_model_param['model_name'], video_model_param['model_set'], video_id))
            connection.commit()
            return True
    except Error as e:
        print(f"MySQL error: {e}")
        return False
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 记录上传视频素材的信息
def add_video_model(param):
    connection = None
    cursor = None
    try:
        # 连接数据库
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='ai_video',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008'
        )

        if connection.is_connected():
            cursor = connection.cursor()
            query = f"""
                INSERT INTO video_model_set 
                (model_name, model_set)
                VALUES (%s, %s)
            """
            values = (
                param['model_name'], param['model_set'])
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


def get_random_video_model():
    return fetch_with_retry(
        {
            'host': '82.157.237.217', 'database': 'ai_video',
            'user': 'ljx_lepin123', 'password': 'ea.367GZX!#EmwfpEYW$f', 'port': '35008'
        },
        "SELECT * FROM video_model_set ORDER BY RAND() LIMIT 1",
        dictionary=True,
        operation_name='随机获取视频模板',
    )


# 获取未使用的标题信息
def get_unused_title_info(account_name, title_type):
    connection = None
    cursor = None
    try:
        # 连接数据库，此处需要填入你的数据库连接相关信息
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='ai_video',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008'
        )
        # 如果title_type 不为空字符串,就加上类型筛选,不再选择这个类型的标题
        title_type_condition = "and title_type != %s"
        title_type_value = (title_type,)
        if connection.is_connected():
            cursor = connection.cursor()
            today = datetime.datetime.now().strftime('%Y-%m-%d')  # 获取今天的日期
            today_pattern = f"%{today}%"
            # 随机获取一个 模板设置
            query = f"""
                SELECT * FROM video_title_info
                where is_generate = 0
                and account_name = %s
                and (last_time IS NULL OR last_time NOT LIKE %s)
                {title_type_condition}
                ORDER BY RAND() LIMIT 1
            """
            cursor.execute(query, (account_name, today_pattern) + title_type_value)
            result = cursor.fetchone()
            if result:
                return result
            else:
                if connection.is_connected():
                    cursor = connection.cursor()
                    today = datetime.datetime.now().strftime('%Y-%m-%d')  # 获取今天的日期
                    today_pattern = f"%{today}%"
                    # 随机获取一个 模板设置
                    query = """
                        SELECT * FROM video_title_info
                        where is_generate = 0
                        and account_name = %s
                        and (last_time IS NULL OR last_time NOT LIKE %s)
                        ORDER BY RAND() LIMIT 1
                    """
                    cursor.execute(query, (account_name, today_pattern,))
                    result = cursor.fetchone()
                    return result

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 标题id获取数据库文案
def get_content_label(title_id):
    connection = None
    cursor = None
    try:
        # 连接数据库，此处需要填入你的数据库连接相关信息
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='ai_video',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008'
        )
        if connection.is_connected():
            cursor = connection.cursor()
            # 随机获取一个 模板设置
            query = """
                   SELECT * FROM video_title_info
                   where id = %s
               """
            cursor.execute(query, (title_id,))
            result = cursor.fetchone()
            return result
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def mark_title_generated(title_id: int) -> int:
    """
    根据主键 id 把 is_generate 置为 1
    :param title_id: 主键 id
    :return: 影响行数
    """
    connection = None
    cursor = None
    try:
        # 连接数据库，此处需要填入你的数据库连接相关信息
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='ai_video',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008',
            connection_timeout=15,
            read_timeout=QUERY_TIMEOUT,
            write_timeout=QUERY_TIMEOUT
        )
        if connection.is_connected():
            cursor = connection.cursor()
            # 随机获取一个 模板设置
            sql = "UPDATE video_title_info SET is_generate = 1 WHERE id = %s"
            cursor.execute(sql, (title_id,))
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


def update_video_title_info(title_id, new_content, new_label):
    """
    根据给定的 id 更新 video_title_info 表中的 content 和 label 字段
    :param connection: 已经建立的数据库连接对象
    :param title_id: 要更新的记录的 id
    :param new_content: 新的 content 值
    :param new_label: 新的 label 值
    :return: 更新的行数
    """
    connection = None
    cursor = None
    try:
        # 连接数据库，此处需要填入你的数据库连接相关信息
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='ai_video',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008'
        )
        if connection.is_connected():
            cursor = connection.cursor()
            sql = """
                UPDATE video_title_info
                SET content = %s, label = %s
                WHERE id = %s
            """
            cursor.execute(sql, (new_content, new_label, title_id))
            connection.commit()
            return True
    except Error as e:
        print(f"Error while updating record: {e}")
        return False
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 更新标题为已上传FTP
def mark_title_ftp_uploaded(account_name, video_tite_id, video_tite):
    connection = None
    cursor = None
    try:
        # 连接数据库，此处需要填入你的数据库连接相关信息
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='zdcat',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008'
        )
        if connection.is_connected():
            cursor = connection.cursor()
            # 从本地配置文件中读取 ftp 上传路径信息
            # ftp_path_info = read_ftp_config().get('ftp_download_ip', '') + '/' + str(video_tite_id) + '.mp4'
            ftp_path_info = str(video_tite_id) + '.mp4'
            sql = "UPDATE fabu_task_info SET ftp_ip = %s WHERE name = %s and title = %s"
            cursor.execute(sql, (ftp_path_info, account_name, video_tite))
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


# 上传视频到ftp目录下
def ftp_upload_video_to_site(video_file_path, title_id):
    try:
        # FTP服务器信息 通过读取ftp_config.json文件获取
        ftp_host = read_ftp_config()['ftp_host']
        ftp_user = read_ftp_config()['ftp_user']
        ftp_pass = read_ftp_config()['ftp_pass']
        ftp_port = read_ftp_config()['ftp_port']
        # 连接到FTP服务器
        ftp = FTP()
        ftp.connect(host=ftp_host, port=ftp_port)
        ftp.login(user=ftp_user, passwd=ftp_pass)

        remote_dir_path = f"/generated_video"
        _make_ftp_dirs(ftp, remote_dir_path)
        ftp.cwd(remote_dir_path)

        # 上传文件 保存为 ftp_filename
        remote_file_path = f'{title_id}' + '.mp4'
        with open(video_file_path, 'rb') as file:
            ftp.storbinary(f'STOR {remote_file_path}', file)
        print(f'File {video_file_path} uploaded to {remote_file_path} successfully.')
        # 断开连接
        ftp.quit()
        return True
    except Exception as e:
        print(f'上传视频失败{str(e)}')
        return False


# 读取 ftp_config.json文件获取 ftp 配置
def read_ftp_config():
    try:
        with open('ftp_config.json', 'r') as f:
            config = json.load(f)
            return config
    except Exception as e:
        print(f'读取 ftp_config.json 文件失败: {str(e)}')
        return {}


# 记录标题信息上传不成功
def record_unsuccess_title_info(result):
    connection = None
    cursor = None
    try:
        # 连接数据库，此处需要填入你的数据库连接相关信息
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='ai_video',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008'
        )
        if connection.is_connected():
            cursor = connection.cursor()
            # 获取当前时间
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            sql = """
                UPDATE video_title_info
                SET last_time = %s, try_num = %s
                WHERE id = %s
            """
            try_num = result[8] + 1

            # 如果次数大于3次  重置文案
            if try_num >= 3:
                try_num = 0
                update_video_title_info(result[0], '', '')

            cursor.execute(sql, (current_time, try_num, result[0]))
            connection.commit()
            return True
    except Error as e:
        print(f"Error while updating record: {e}")
        return False
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 上传视频的文案、标题、信息
def upload_video_info_to_site(result, account_location):
    content_str_list = result[2].split('&&')
    content = ''
    for index, content_str in enumerate(content_str_list):
        if index == 0:
            content_str = content_str.replace('|', '')
        if index == 1:
            content_str = ''
        if content_str is not None and content_str != '':
            content = content + '<p>' + content_str + '</p>'

    video_data = {"title": result[1], "content": content, "region": account_location, 'sp_account_name': result[5]}

    url1 = 'http://123.207.187.252:8001/index/videoto_site/info'
    try:
        resp = requests.post(url1, data=video_data, timeout=30)
        resp.raise_for_status()
        video_id = resp.json()['data']['id']  # 或 resp.text
        return video_id
    except Exception as e:
        print('上传视频信息出错了%s' % e)
        return 0


# 上传视频以及视频截图
def upload_video_pic_to_site(video_id, video_file_path):
    url2 = 'http://123.207.187.252:8001/index/videoto_site/video_url'
    if video_id == 0:
        return False
    video_url, video_pic_str = ftp_ai_upload(video_id, video_file_path)
    if video_url != '':
        video_url_data = {"id": video_id, "video_url": video_url, "imgs": video_pic_str}
        try:
            resp = requests.post(url2, data=video_url_data, timeout=30)
            resp.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            print(f"请求失败：{e}")
            return False


# 获取人物图片id
def get_person_id(title):
    connection = None
    cursor = None
    try:
        # 连接数据库，此处需要填入你的数据库连接相关信息
        connection = mysql.connector.connect(
            host='82.157.237.217',  # 数据库主机地址
            database='ai_video',  # 数据库名称
            user='ljx_lepin123',  # 数据库用户名
            password='ea.367GZX!#EmwfpEYW$f',  # 数据库密码
            port='35008'
        )
        person_name = deepseek_ai_history_person(title)
        if connection.is_connected():
            cursor = connection.cursor()
            # 随机获取一个 模板设置
            query = """
                   SELECT * FROM lishimingren
                   where keywords LIKE %s
               """
            person_name_like = f"%{person_name}%"
            cursor.execute(query, (person_name_like,))
            result = cursor.fetchone()
            return result
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None
    finally:
        # 确保资源被正确释放
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# get_unused_title_info('Ai游中国')


# def process_folder(input_folder, output_folder):
#     """处理文件夹中的所有视频，跳过已经为1080p的视频"""
#     # 确保输出文件夹存在
#     os.makedirs(output_folder, exist_ok=True)
#
#     # 目标分辨率（1080p）
#     target_width = 1920
#     target_height = 1080
#
#     # 遍历输入文件夹中的所有文件
#     for file_path in Path(input_folder).glob('*'):
#         if file_path.is_file():
#             # 检查是否为视频文件（可以根据需要扩展支持更多格式）
#             if file_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv']:
#                 # 获取视频分辨率
#                 resolution = get_video_resolution(str(file_path))
#                 if resolution and resolution[0] == target_width and resolution[1] == target_height:
#                     print(f"跳过已为1080p的视频: {file_path}")
#                     continue
#
#                 # 构建输出路径
#                 output_path = Path(output_folder) / file_path.name
#                 # 处理视频
#                 process_video(str(file_path), str(output_path))
#
#     print(f"所有视频处理完成，输出文件夹: {output_folder}")

# download_video(1)
# # ftp_upload(1, r'D:\素材\1.mp4')
# get_videos_by_keyword('3', '4')


def get_person_pic_path(person_id):
    """
    根据人物ID获取人物图片路径
    
    Args:
        person_id: 人物ID（数字）
    
    Returns:
        str: 人物图片的完整路径，如果不存在则返回 None
    """
    try:
        # 构造person_images文件夹路径
        current_dir = os.getcwd()
        person_images_dir = os.path.join(current_dir, 'person_images')
        
        # 确保文件夹存在
        if not os.path.exists(person_images_dir):
            print(f"人物图片文件夹不存在: {person_images_dir}")
            return None
        
        # 构造图片文件名（以ID命名）
        # 支持多种图片格式
        image_extensions = ['.png', '.jpg', '.jpeg', '.webp']
        
        for ext in image_extensions:
            person_pic_path = os.path.join(person_images_dir, f"{person_id}{ext}")
            if os.path.exists(person_pic_path):
                print(f"找到人物图片: {person_pic_path}")
                return person_pic_path
        
        # 如果没找到，尝试其他命名方式
        for ext in image_extensions:
            person_pic_path = os.path.join(person_images_dir, f"person_{person_id}{ext}")
            if os.path.exists(person_pic_path):
                print(f"找到人物图片（带前缀）: {person_pic_path}")
                return person_pic_path
        
        print(f"未找到ID为 {person_id} 的人物图片")
        print(f"搜索路径: {person_images_dir}")
        
        # 列出person_images文件夹中的所有文件供调试
        if os.path.exists(person_images_dir):
            existing_files = os.listdir(person_images_dir)
            print(f"现有文件: {existing_files}")
        
        return None
        
    except Exception as e:
        print(f"获取人物图片路径失败: {e}")
        return None


# cut_video_by_audio_length('1.mp4', '1', 5.0)
