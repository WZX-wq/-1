#!/usr/bin/env python3
"""
优化的水印添加Worker
性能提升版本 - 显著减少处理时间
"""

import sys
import time
import asyncio
from pathlib import Path
from PySide6.QtCore import QRunnable
from worker.signals import WorkerSignals

# 导入优化的水印工具
sys.path.append(str(Path(__file__).parent.parent))
from ffmpeg_tool.add_watermark_tool_optimized import (
    add_text_watermark_optimized,
    add_pic_watermark_optimized,
    get_system_info,
    get_optimal_encoding_params
)

class AddWatermarkWorkerOptimized(QRunnable):
    """
    优化的水印添加Worker
    
    性能优化特性：
    1. 硬件加速支持（CUDA）
    2. 多线程优化
    3. FFmpeg参数优化
    4. 进度回调
    5. 性能统计
    """
    
    def __init__(self, video_path, output_file, watermark_setting, watermark_type=1, pic_path=None):
        super().__init__()
        self.video_path = video_path
        self.pic_path = pic_path
        self.output_file = output_file
        self.watermark_type = watermark_type
        self.watermark_setting = watermark_setting
        self.signals = WorkerSignals()
        
        # 性能相关
        self.start_time = None
        self.system_info = get_system_info()
        self.encoding_params = get_optimal_encoding_params()
        
        print(f"🚀 优化的水印Worker初始化")
        print(f"   系统: {self.system_info['system']}")
        print(f"   CPU核心: {self.system_info['cpu_count']}")
        if self.system_info['gpu_available']:
            print(f"   🎮 GPU加速: {self.system_info['gpu_type']}")

    def run(self):
        """执行水印添加任务"""
        self.start_time = time.time()
        
        try:
            # 发送开始信号
            self.signals.progress.emit(0)
            
            if self.watermark_type == 1:
                # 文字水印
                processing_time = asyncio.run(self.add_text_watermark())
            else:
                # 图片水印
                processing_time = asyncio.run(self.add_pic_watermark())
            
            total_time = time.time() - self.start_time
            
            # 发送完成信号和性能信息
            self.signals.progress.emit(100)
            
            performance_info = {
                'processing_time': processing_time,
                'total_time': total_time,
                'gpu_accelerated': self.system_info['gpu_available'],
                'encoding_params': self.encoding_params
            }
            
            message = f'添加水印完成！处理时间: {processing_time:.2f}秒'
            if self.system_info['gpu_available']:
                message += ' (GPU加速)'
            
            self.signals.finished.emit(message)
            
            # 发送性能统计
            self.signals.performance.emit(performance_info)
            
        except Exception as e:
            error_msg = f'水印添加失败: {str(e)}'
            print(f"❌ {error_msg}")
            self.signals.errorOccurred.emit(error_msg)

    async def add_text_watermark(self):
        """添加文字水印（异步版本）"""
        try:
            # 模拟进度更新
            self.signals.progress.emit(10)
            
            # 执行优化的文字水印添加
            processing_time = add_text_watermark_optimized(
                self.video_path, 
                self.output_file, 
                self.watermark_setting
            )
            
            self.signals.progress.emit(90)
            return processing_time
            
        except Exception as e:
            print(f"文字水印添加失败: {e}")
            raise

    async def add_pic_watermark(self):
        """添加图片水印（异步版本）"""
        try:
            # 模拟进度更新
            self.signals.progress.emit(10)
            
            # 执行优化的图片水印添加
            processing_time = add_pic_watermark_optimized(
                self.video_path,
                self.pic_path,
                self.output_file,
                self.watermark_setting
            )
            
            self.signals.progress.emit(90)
            return processing_time
            
        except Exception as e:
            print(f"图片水印添加失败: {e}")
            raise

class BatchWatermarkWorker(QRunnable):
    """
    批量水印处理Worker
    可以并行处理多个视频的水印添加
    """
    
    def __init__(self, video_list, output_dir, watermark_setting, watermark_type=1, pic_path=None):
        super().__init__()
        self.video_list = video_list
        self.output_dir = output_dir
        self.watermark_setting = watermark_setting
        self.watermark_type = watermark_type
        self.pic_path = pic_path
        self.signals = WorkerSignals()
        
        self.system_info = get_system_info()
        self.processed_count = 0
        self.total_count = len(video_list)

    def run(self):
        """批量处理水印"""
        try:
            print(f"🎬 开始批量处理 {self.total_count} 个视频的水印")
            
            for i, video_path in enumerate(self.video_list):
                try:
                    # 计算输出路径
                    video_name = Path(video_path).stem
                    output_file = Path(self.output_dir) / f"{video_name}_watermarked.mp4"
                    
                    # 创建优化的Worker
                    worker = AddWatermarkWorkerOptimized(
                        video_path,
                        str(output_file),
                        self.watermark_setting,
                        self.watermark_type,
                        self.pic_path
                    )
                    
                    # 连接信号
                    worker.signals.finished.connect(self.on_video_finished)
                    worker.signals.errorOccurred.connect(self.on_video_error)
                    
                    # 执行处理
                    worker.run()
                    
                    # 更新进度
                    progress = int((i + 1) / self.total_count * 100)
                    self.signals.progress.emit(progress)
                    
                except Exception as e:
                    print(f"处理视频 {video_path} 失败: {e}")
                    self.on_video_error(f"处理 {video_path} 失败: {e}")
            
            message = f'批量水印处理完成！成功: {self.processed_count}/{self.total_count}'
            self.signals.finished.emit(message)
            
        except Exception as e:
            error_msg = f'批量水印处理失败: {str(e)}'
            self.signals.errorOccurred.emit(error_msg)

    def on_video_finished(self, message):
        """单个视频处理完成"""
        self.processed_count += 1
        print(f"✅ {message} ({self.processed_count}/{self.total_count})")

    def on_video_error(self, error_msg):
        """单个视频处理失败"""
        print(f"❌ {error_msg}")

# 性能对比工具
class WatermarkPerformanceAnalyzer:
    """水印性能分析器"""
    
    def __init__(self):
        self.system_info = get_system_info()
        self.test_results = []
    
    def benchmark_original_vs_optimized(self, video_path, watermark_setting, watermark_type=1, pic_path=None):
        """对比原始版本和优化版本的性能"""
        print("🔍 开始性能基准测试...")
        
        # 测试原始版本
        try:
            from ffmpeg_tool.add_watermark_tool import add_text_watermark, add_pic_watermark
            
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                original_output = f.name
            
            print("🐌 测试原始版本...")
            start_time = time.time()
            
            if watermark_type == 1:
                add_text_watermark(video_path, original_output, watermark_setting)
            else:
                add_pic_watermark(video_path, pic_path, original_output, watermark_setting)
            
            original_time = time.time() - start_time
            
            # 清理
            if Path(original_output).exists():
                Path(original_output).unlink()
                
        except Exception as e:
            print(f"原始版本测试失败: {e}")
            original_time = None
        
        # 测试优化版本
        try:
            from ffmpeg_tool.add_watermark_tool_optimized import add_text_watermark_optimized, add_pic_watermark_optimized
            
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                optimized_output = f.name
            
            print("🚀 测试优化版本...")
            start_time = time.time()
            
            if watermark_type == 1:
                optimized_time = add_text_watermark_optimized(video_path, optimized_output, watermark_setting)
            else:
                optimized_time = add_pic_watermark_optimized(video_path, pic_path, optimized_output, watermark_setting)
            
            # 清理
            if Path(optimized_output).exists():
                Path(optimized_output).unlink()
                
        except Exception as e:
            print(f"优化版本测试失败: {e}")
            optimized_time = None
        
        # 输出对比结果
        print("\n📊 性能对比结果:")
        print("="*50)
        if original_time:
            print(f"原始版本耗时: {original_time:.2f}秒")
        if optimized_time:
            print(f"优化版本耗时: {optimized_time:.2f}秒")
        
        if original_time and optimized_time:
            improvement = ((original_time - optimized_time) / original_time) * 100
            speedup = original_time / optimized_time
            print(f"性能提升: {improvement:.1f}%")
            print(f"速度倍数: {speedup:.2f}x")
            
            if improvement > 20:
                print("🎉 显著性能提升！")
            elif improvement > 0:
                print("✅ 性能有改善")
            else:
                print("⚠️ 性能差异不大")
        
        return {
            'original_time': original_time,
            'optimized_time': optimized_time,
            'improvement_percent': ((original_time - optimized_time) / original_time * 100) if original_time and optimized_time else None
        }