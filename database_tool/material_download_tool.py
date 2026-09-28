import os
import threading
import time
from urllib.parse import urlparse

import requests
from urllib3.util.retry import Retry


_download_state = threading.local()


def set_material_download_error(message):
    _download_state.last_error = str(message or '')


def get_last_material_download_error():
    return getattr(_download_state, 'last_error', '')


def download_to_cache(url, file_path, material_name, auth=None):
    """完整下载到临时文件，成功后再替换缓存，避免留下半截视频。"""
    set_material_download_error('')
    if not url:
        set_material_download_error(f'{material_name}没有可用的下载地址')
        return False

    if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
        return True

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    part_path = f'{file_path}.{os.getpid()}.{threading.get_ident()}.part'
    try:
        retryable_statuses = {500, 502, 503, 504}
        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            try:
                # 每次尝试都创建全新会话。IIS/上游节点异常时，复用原连接会连续命中同一 502。
                connection_retry = Retry(
                    total=1,
                    connect=1,
                    read=1,
                    status=0,
                    allowed_methods=frozenset({'GET'}),
                    raise_on_status=False,
                )
                adapter = requests.adapters.HTTPAdapter(max_retries=connection_retry)
                with requests.Session() as session:
                    # 系统代理无法访问内网素材服务，会把所有请求统一返回为 502。
                    # 仅该内网主机直连；公网下载仍沿用用户的代理设置。
                    if urlparse(url).hostname == '100.122.91.10':
                        session.trust_env = False
                    session.mount('http://', adapter)
                    session.mount('https://', adapter)
                    response = session.get(
                        url,
                        auth=auth,
                        timeout=(30, 300),
                        stream=True,
                        verify=False if url.lower().startswith('https://') else True,
                    )
                    if response.status_code != 200:
                        status_code = response.status_code
                        if status_code in retryable_statuses and attempt < max_attempts:
                            time.sleep(0.8 * (2 ** (attempt - 1)))
                            continue
                        set_material_download_error(
                            f'{material_name}服务器返回 HTTP {status_code}（已尝试{attempt}次）'
                        )
                        return False

                    with open(part_path, 'wb') as file_obj:
                        for chunk in response.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                file_obj.write(chunk)
                break
            except (requests.RequestException, OSError) as error:
                if attempt >= max_attempts:
                    set_material_download_error(f'{material_name}下载异常（已尝试{attempt}次）：{error}')
                    return False
                time.sleep(0.8 * (2 ** (attempt - 1)))

        if not os.path.isfile(part_path) or os.path.getsize(part_path) == 0:
            set_material_download_error(f'{material_name}下载结果为空')
            return False
        os.replace(part_path, file_path)
        return True
    except OSError as error:
        set_material_download_error(f'{material_name}下载异常：{error}')
        return False
    finally:
        if os.path.exists(part_path):
            try:
                os.remove(part_path)
            except OSError:
                pass
