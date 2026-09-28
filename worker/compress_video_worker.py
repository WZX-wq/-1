import asyncio
import os

from ffmpeg_tool.video_compress_tool import compress_video_fast
from worker.worker_signals import WorkerSignals
from PyQt6.QtCore import QRunnable


class CompressVideoWorker(QRunnable):
    def __init__(self, input_video_path, output_path):
        super().__init__()
        self.input_video_path = input_video_path
        self.output_path = output_path
        self.signals = WorkerSignals()

    def run(self):
        try:
            success = compress_video_fast(self.input_video_path, self.output_path)
            
            if success and os.path.exists(self.output_path):
                # 压缩成功，删除原文件并重命名压缩文件
                try:
                    if os.path.exists(self.input_video_path):
                        os.remove(self.input_video_path)
                        print(f"🧹 删除未压缩文件: {self.input_video_path}")
                    
                    # 重命名压缩文件为原文件名
                    import shutil
                    shutil.move(self.output_path, self.input_video_path)
                    print(f"📝 压缩文件重命名为: {self.input_video_path}")
                    
                    self.signals.finished.emit('视频压缩完成')
                except Exception as rename_error:
                    print(f"⚠️ 文件重命名失败，保留临时文件: {str(rename_error)}")
                    self.signals.finished.emit('视频压缩完成（使用临时文件）')
            else:
                self.signals.errorOccurred.emit('视频压缩失败')
                
        except Exception as e:
            print(f"❌ 视频压缩异常: {str(e)}")
            import traceback
            traceback.print_exc()
            self.signals.errorOccurred.emit(f'视频压缩异常: {str(e)}')
