#!/usr/bin/env python3
"""
并行视频素材下载Worker
性能优化版本 - 支持并行下载多个视频素材
"""

import sys
import time
import threading
from pathlib import Path
from PySide6.QtCore import QRunnable, QObject, Signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from database_tool.video_load_tool_optimized import (
    VideoDownloadOptimizer,
    VideoMaterialMatcher,
    DownloadPerformanceMonitor
)

# 导入原有函数
from database_tool.video_load_tool import (
    get_videos_by_keyword_1,
    cut_video_by_audio_length
)

class ParallelDownloadSignals(QObject):
    """并行下载信号"""
    progress = Signal(str, int, int, int)  # video_id, progress, current, total
    overall_progress = Signal(str, int, int, int)  # type, progress, current, total
    file_completed = Signal(str, str)  # video_id, file_path
    file_failed = Signal(str, str)  # video_id, error
    batch_completed = Signal(str)  # message
    performance_stats = Signal(dict)  # performance statistics

class ParallelDownloadWorker(QRunnable):
    """并行下载Worker"""
    
    def __init__(
        self,
        download_requests: List[Dict],
        max_workers: int = 4,
        enable_progress: bool = True
    ):
        super().__init__()
        self.download_requests = download_requests
        self.max_workers = max_workers
        self.enable_progress = enable_progress
        self.signals = ParallelDownloadSignals()
        
        # 性能监控
        self.monitor = DownloadPerformanceMonitor()
        
        # 下载优化器
        self.optimizer = VideoDownloadOptimizer(
            max_workers=max_workers,
            chunk_size=8192
        )
        
        # 统计信息
        self.stats = {
            'total': len(download_requests),
            'completed': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        print(f"🚀 初始化并行下载Worker: {len(download_requests)}个任务, {max_workers}个线程")

    def run(self):
        """执行并行下载"""
        self.stats['start_time'] = time.time()
        self.monitor.start_monitoring()
        
        try:
            print(f"🎬 开始并行下载 {len(self.download_requests)} 个视频素材...")
            
            # 执行批量下载
            results = self.optimizer.batch_download_videos(
                self.download_requests,
                self._create_progress_callback()
            )
            
            # 处理结果
            successful_downloads = []
            failed_downloads = []
            
            for video_id, file_path in results:
                if file_path:
                    successful_downloads.append((video_id, file_path))
                    self.signals.file_completed.emit(video_id, file_path)
                    
                    # 记录文件大小
                    self.monitor.record_file_size(file_path)
                else:
                    failed_downloads.append(video_id)
                    self.signals.file_failed.emit(video_id, "下载失败")
            
            self.stats['completed'] = len(successful_downloads)
            self.stats['failed'] = len(failed_downloads)
            
            # 发送完成信号
            self.stats['end_time'] = time.time()
            duration = self.stats['end_time'] - self.stats['start_time']
            
            message = (
                f"并行下载完成！"
                f"成功: {self.stats['completed']}/{self.stats['total']}, "
                f"耗时: {duration:.2f}秒"
            )
            self.signals.batch_completed.emit(message)
            
            # 发送性能统计
            performance_stats = self.monitor.end_monitoring()
            if performance_stats:
                performance_stats.update(self.stats)
                self.signals.performance_stats.emit(performance_stats)
            
        except Exception as e:
            error_msg = f"并行下载失败: {str(e)}"
            print(f"❌ {error_msg}")
            self.signals.file_failed.emit("batch", error_msg)

    def _create_progress_callback(self):
        """创建进度回调函数"""
        def callback(video_id, progress, current, total):
            if video_id == 'overall':
                # 总体进度
                self.signals.overall_progress.emit(
                    video_id, progress, current, total
                )
            else:
                # 单个文件进度
                self.signals.file_completed.emit(
                    video_id, f"进度: {progress}%"
                )
                self.signals.progress.emit(
                    video_id, progress, current, total
                )
        return callback

class MaterialMatchingWorker(QRunnable):
    """素材匹配和下载Worker"""
    
    def __init__(
        self,
        text_parts: List[str],
        screen: int,
        location: str,
        audio_lengths: List[int],
        location_ids: List[str],
        max_workers: int = 4
    ):
        super().__init__()
        self.text_parts = text_parts
        self.screen = screen
        self.location = location
        self.audio_lengths = audio_lengths
        self.location_ids = location_ids
        self.max_workers = max_workers
        self.signals = ParallelDownloadSignals()
        
        # 初始化优化器
        download_optimizer = VideoDownloadOptimizer(max_workers=max_workers)
        self.matcher = VideoMaterialMatcher(download_optimizer)
        
        # 性能监控
        self.monitor = DownloadPerformanceMonitor()

    def run(self):
        """执行素材匹配和下载"""
        self.monitor.start_monitoring()
        
        try:
            print(f"🎬 开始匹配和下载 {len(self.text_parts)} 个素材...")
            
            # 执行并行匹配和下载
            processed_videos = self.matcher.match_and_download_materials_parallel(
                self.text_parts,
                self.screen,
                self.location,
                self.audio_lengths,
                self.location_ids,
                self._create_progress_callback()
            )
            
            # 发送完成信号
            message = f"素材匹配完成！成功处理: {len(processed_videos)} 个视频"
            self.signals.batch_completed.emit(message)
            
            # 发送性能统计
            performance_stats = self.monitor.end_monitoring()
            if performance_stats:
                self.signals.performance_stats.emit(performance_stats)
            
            # 发送处理完成的视频列表
            for video_path in processed_videos:
                self.signals.file_completed.emit("processed", video_path)
            
        except Exception as e:
            error_msg = f"素材匹配失败: {str(e)}"
            print(f"❌ {error_msg}")
            self.signals.file_failed.emit("batch", error_msg)

    def _create_progress_callback(self):
        """创建进度回调函数"""
        def callback(type_str, progress, current, total):
            if type_str == 'overall':
                self.signals.overall_progress.emit(
                    type_str, progress, current, total
                )
            elif type_str == 'processing':
                self.signals.progress.emit(
                    "processing", progress, current, total
                )
            else:
                # 单个下载进度
                self.signals.progress.emit(
                    type_str, progress, current, total
                )
        return callback

class SmartDownloadScheduler:
    """智能下载调度器"""
    
    def __init__(self, max_concurrent_downloads: int = 6):
        self.max_concurrent = max_concurrent_downloads
        self.active_downloads = {}
        self.download_queue = []
        self.lock = threading.Lock()
        
    def schedule_download(
        self,
        download_requests: List[Dict],
        priority_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """智能调度下载任务"""
        # 按优先级排序
        if priority_callback:
            download_requests.sort(key=priority_callback, reverse=True)
        
        # 分批处理
        batches = []
        for i in range(0, len(download_requests), self.max_concurrent):
            batch = download_requests[i:i + self.max_concurrent]
            batches.append(batch)
        
        return batches
    
    def estimate_download_time(self, requests: List[Dict]) -> float:
        """估算下载时间"""
        # 简单估算：假设平均下载速度为 2MB/s
        avg_file_size_mb = 10  # 假设平均文件大小
        total_size_mb = len(requests) * avg_file_size_mb
        avg_speed_mbps = 2  # 假设下载速度
        
        return total_size_mb / avg_speed_mbps

# 便捷函数
def create_parallel_download_worker(
    video_requests: List[Dict],
    max_workers: int = 4
) -> ParallelDownloadWorker:
    """创建并行下载Worker的便捷函数"""
    return ParallelDownloadWorker(video_requests, max_workers)

def create_material_matching_worker(
    text_parts: List[str],
    screen: int,
    location: str,
    audio_lengths: List[int],
    location_ids: List[str],
    max_workers: int = 4
) -> MaterialMatchingWorker:
    """创建素材匹配Worker的便捷函数"""
    return MaterialMatchingWorker(
        text_parts, screen, location, audio_lengths, location_ids, max_workers
    )

# 使用示例
if __name__ == "__main__":
    # 示例：并行下载
    download_requests = [
        {'video_id': '123', 'screen': 1},
        {'video_id': '456', 'screen': 1},
        {'video_id': '789', 'screen': 1},
    ]
    
    worker = create_parallel_download_worker(download_requests, max_workers=3)
    
    # 连接信号（在Qt应用中使用）
    # worker.signals.progress.connect(on_progress)
    # worker.signals.batch_completed.connect(on_completed)
    
    print("并行下载Worker创建完成！")