#!/usr/bin/env python3
"""
优化的视频素材下载工具
性能优化版本 - 显著减少下载时间
"""

import os
import time
import requests
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue
import hashlib

# 导入原始模块
import mysql.connector
from mysql.connector import Error

# 导入原有函数
from video_load_tool import (
    get_videos_by_keyword,
    get_videos_by_keyword_1,
    cut_video_by_audio_length,
    get_video_resolution,
    get_video_url
)

class VideoDownloadOptimizer:
    """视频下载优化器"""
    
    def __init__(self, max_workers: int = 4, chunk_size: int = 8192):
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.session = requests.Session()
        
        # 连接池优化
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # 线程安全的状态跟踪
        self.download_stats = {
            'total_files': 0,
            'completed': 0,
            'failed': 0,
            'total_bytes': 0,
            'downloaded_bytes': 0
        }
        self.stats_lock = threading.Lock()
        
    def download_video_optimized(
        self, 
        video_id: str, 
        screen: int,
        progress_callback: Optional[callable] = None
    ) -> Optional[str]:
        """优化的视频下载函数"""
        cache_dir = os.path.join(os.getcwd(), 'cacheVideo')
        os.makedirs(cache_dir, exist_ok=True)
        
        file_path = os.path.join(cache_dir, f'{video_id}.mp4')
        
        # 检查是否已存在且完整
        if self._is_video_complete(file_path):
            print(f"✅ 视频已存在且完整: {video_id}")
            return file_path
        
        # 获取下载URL
        ftp_file_path = get_video_url(video_id)
        if 'http' in ftp_file_path:
            url = ftp_file_path
        else:
            url = f'http://100.122.91.10:8991/' + ftp_file_path
        
        # 执行优化下载
        success = self._download_with_resume(url, file_path, video_id, progress_callback)
        
        if success:
            return file_path
        else:
            return None
    
    def _download_with_resume(
        self, 
        url: str, 
        file_path: str, 
        video_id: str,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """支持断点续传的下载"""
        try:
            # 检查已下载大小
            downloaded_bytes = 0
            if os.path.exists(file_path):
                downloaded_bytes = os.path.getsize(file_path)
            
            # 设置断点续传头
            headers = {}
            mode = 'wb'
            if downloaded_bytes > 0:
                headers['Range'] = f'bytes={downloaded_bytes}-'
                mode = 'ab'
            
            # 下载请求
            auth = ('xiaoling', 'XL#!_+Dj@!DYN7MzicAkXw') if '100.122.91.10' in url else None
            
            response = self.session.get(
                url,
                headers=headers,
                stream=True,
                timeout=(30, 300),
                auth=auth
            )
            response.raise_for_status()
            
            # 获取文件总大小
            content_range = response.headers.get('Content-Range', '')
            if content_range:
                total_size = int(content_range.split('/')[-1])
            else:
                total_size = int(response.headers.get('content-length', 0))
            
            # 流式下载
            with open(file_path, mode) as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
                        
                        # 更新进度
                        if progress_callback and total_size:
                            progress = min(100, int((downloaded_bytes / total_size) * 100))
                            progress_callback(video_id, progress, downloaded_bytes, total_size)
            
            print(f"✅ 下载完成: {video_id}")
            return True
            
        except Exception as e:
            print(f"❌ 下载失败 {video_id}: {e}")
            return False
    
    def _is_video_complete(self, file_path: str) -> bool:
        """检查视频文件是否完整"""
        if not os.path.exists(file_path):
            return False
        
        try:
            # 检查文件大小（简单验证）
            file_size = os.path.getsize(file_path)
            return file_size > 1024 * 1024  # 大于1MB认为是有效文件
        except:
            return False
    
    def batch_download_videos(
        self, 
        video_requests: List[Dict], 
        progress_callback: Optional[callable] = None
    ) -> List[Optional[str]]:
        """批量并行下载视频"""
        print(f"🚀 开始并行下载 {len(video_requests)} 个视频...")
        
        self.download_stats['total_files'] = len(video_requests)
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有下载任务
            future_to_request = {}
            
            for request in video_requests:
                video_id = request['video_id']
                screen = request.get('screen', 1)
                
                future = executor.submit(
                    self.download_video_optimized,
                    video_id,
                    screen,
                    self._create_progress_callback(progress_callback)
                )
                future_to_request[future] = request
            
            # 收集结果
            for future in as_completed(future_to_request):
                request = future_to_request[future]
                video_id = request['video_id']
                
                try:
                    result = future.result()
                    results.append((video_id, result))
                    
                    with self.stats_lock:
                        if result:
                            self.download_stats['completed'] += 1
                        else:
                            self.download_stats['failed'] += 1
                        
                        # 更新总体进度
                        if progress_callback:
                            completed = self.download_stats['completed']
                            total = self.download_stats['total_files']
                            overall_progress = int((completed / total) * 100) if total > 0 else 0
                            progress_callback('overall', overall_progress, completed, total)
                
                except Exception as e:
                    print(f"❌ 下载异常 {video_id}: {e}")
                    results.append((video_id, None))
                    
                    with self.stats_lock:
                        self.download_stats['failed'] += 1
        
        return results
    
    def _create_progress_callback(self, user_callback):
        """创建线程安全的进度回调"""
        def callback(video_id, progress, current, total):
            with self.stats_lock:
                if user_callback:
                    user_callback(video_id, progress, current, total)
        return callback
    
    def get_download_stats(self) -> Dict:
        """获取下载统计信息"""
        with self.stats_lock:
            return self.download_stats.copy()

class VideoMaterialMatcher:
    """视频素材匹配器优化版"""
    
    def __init__(self, download_optimizer: VideoDownloadOptimizer):
        self.optimizer = download_optimizer
        
    def match_and_download_materials_parallel(
        self,
        text_parts: List[str],
        screen: int,
        location: str,
        audio_lengths: List[int],
        location_ids: List[str],
        progress_callback: Optional[callable] = None
    ) -> List[str]:
        """并行匹配和下载视频素材"""
        print(f"🎬 开始并行匹配 {len(text_parts)} 个素材...")
        
        # 第一阶段：并行获取所有候选视频信息
        video_candidates = self._get_video_candidates_parallel(
            text_parts, screen, location, audio_lengths, location_ids
        )
        
        # 第二阶段：并行下载选择的视频
        download_requests = []
        for i, candidates in enumerate(video_candidates):
            if candidates:
                # 选择第一个候选（可根据需要优化选择策略）
                selected_video = candidates[0]
                download_requests.append({
                    'video_id': selected_video['id'],
                    'screen': screen,
                    'part_index': i,
                    'audio_length': audio_lengths[i]
                })
        
        # 第三阶段：并行下载
        download_results = self.optimizer.batch_download_videos(
            download_requests,
            progress_callback
        )
        
        # 第四阶段：并行视频处理
        processed_videos = self._process_downloaded_videos_parallel(
            download_results, audio_lengths, progress_callback
        )
        
        return processed_videos
    
    def _get_video_candidates_parallel(
        self,
        text_parts: List[str],
        screen: int,
        location: str,
        audio_lengths: List[int],
        location_ids: List[str]
    ) -> List[List[Dict]]:
        """并行获取视频候选"""
        print("🔍 并行获取视频候选...")
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            for i, text_part in enumerate(text_parts):
                future = executor.submit(
                    self._get_single_part_candidates,
                    text_part, screen, location, audio_lengths[i], location_ids
                )
                futures.append(future)
            
            candidates = []
            for future in as_completed(futures):
                try:
                    part_candidates = future.result()
                    candidates.append(part_candidates)
                except Exception as e:
                    print(f"获取候选视频失败: {e}")
                    candidates.append([])
        
        return candidates
    
    def _get_single_part_candidates(
        self,
        keyword: str,
        screen: int,
        location: str,
        audio_length: int,
        location_ids: List[str]
    ) -> List[Dict]:
        """获取单个部分的视频候选"""
        try:
            videos = get_videos_by_keyword_1(
                keyword, screen, location, location_ids, audio_length, "美食素材"
            )
            return videos[:5]  # 限制候选数量
        except Exception as e:
            print(f"获取候选失败 {keyword}: {e}")
            return []
    
    def _process_downloaded_videos_parallel(
        self,
        download_results: List[Tuple[str, Optional[str]]],
        audio_lengths: List[int],
        progress_callback: Optional[callable]
    ) -> List[str]:
        """并行处理下载的视频"""
        print("🎥 并行处理视频...")
        
        processed_videos = []
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            
            for video_id, video_path, audio_length in zip(
                [r[0] for r in download_results],
                [r[1] for r in download_results],
                audio_lengths
            ):
                if video_path and os.path.exists(video_path):
                    future = executor.submit(
                        self._process_single_video,
                        video_path, video_id, audio_length
                    )
                    futures.append(future)
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        processed_videos.append(result)
                        
                        if progress_callback:
                            progress_callback('processing', len(processed_videos), len(futures))
                except Exception as e:
                    print(f"视频处理失败: {e}")
        
        return processed_videos
    
    def _process_single_video(
        self, 
        video_path: str, 
        video_id: str, 
        audio_length: int
    ) -> Optional[str]:
        """处理单个视频"""
        try:
            cut_video_path = cut_video_by_audio_length(video_path, video_id, audio_length)
            if os.path.exists(cut_video_path):
                print(f"✅ 视频处理完成: {video_id}")
                return cut_video_path
            else:
                print(f"❌ 视频处理失败: {video_id}")
                return None
        except Exception as e:
            print(f"❌ 视频处理异常 {video_id}: {e}")
            return None

# 向后兼容的优化函数
def download_video_batch(
    video_requests: List[Dict],
    max_workers: int = 4,
    progress_callback: Optional[callable] = None
) -> List[Optional[str]]:
    """批量下载视频的便捷函数"""
    optimizer = VideoDownloadOptimizer(max_workers=max_workers)
    results = optimizer.batch_download_videos(video_requests, progress_callback)
    
    # 转换结果格式
    return [result[1] for result in results]

def download_video_optimized(video_id: str, screen: int = 1) -> Optional[str]:
    """优化版本的单视频下载（向后兼容）"""
    optimizer = VideoDownloadOptimizer()
    return optimizer.download_video_optimized(video_id, screen)

# 性能监控工具
class DownloadPerformanceMonitor:
    """下载性能监控器"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.file_sizes = []
        
    def start_monitoring(self):
        """开始监控"""
        self.start_time = time.time()
        self.file_sizes = []
        
    def record_file_size(self, file_path: str):
        """记录文件大小"""
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            self.file_sizes.append(size)
    
    def end_monitoring(self):
        """结束监控并返回统计"""
        self.end_time = time.time()
        
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            total_size = sum(self.file_sizes)
            avg_speed = total_size / duration if duration > 0 else 0
            
            return {
                'duration': duration,
                'total_size_mb': total_size / (1024 * 1024),
                'file_count': len(self.file_sizes),
                'avg_speed_mbps': avg_speed / (1024 * 1024),
                'avg_size_mb': total_size / len(self.file_sizes) / (1024 * 1024) if self.file_sizes else 0
            }
        return None