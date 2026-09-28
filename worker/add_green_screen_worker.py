from PyQt6.QtCore import QRunnable, pyqtSignal
from worker.worker_signals import WorkerSignals
from ffmpeg_tool.add_green_screen_tool import add_green_screen_overlay_to_video
import os

class AddGreenScreenWorker(QRunnable):
    def __init__(self, input_video_path, output_video_path, overlay_duration=3.0, 
                 position="bottom-right", scale=1.0, opacity=1.0):
        super().__init__()
        self.input_video_path = input_video_path
        self.output_video_path = output_video_path
        self.overlay_duration = overlay_duration
        self.position = position
        self.scale = scale
        self.opacity = opacity
        self.signals = WorkerSignals()

    def run(self):
        try:
            success = add_green_screen_overlay_to_video(
                self.input_video_path, 
                self.output_video_path, 
                self.overlay_duration,
                self.position,
                self.scale,
                self.opacity
            )
            
            if success and os.path.exists(self.output_video_path):
                # 成功，删除原文件
                if os.path.exists(self.input_video_path):
                    os.remove(self.input_video_path)
                    print(f"🧹 删除原视频文件: {self.input_video_path}")
                
                # 重命名处理后的文件
                import shutil
                shutil.move(self.output_video_path, self.input_video_path)
                print(f"📝 绿幕叠加处理文件重命名为: {self.input_video_path}")
                
                self.signals.finished.emit('绿幕叠加添加完成')
            else:
                self.signals.errorOccurred.emit('绿幕叠加添加失败')
                
        except Exception as e:
            print(f"❌ 绿幕叠加添加异常: {str(e)}")
            import traceback
            traceback.print_exc()
            self.signals.errorOccurred.emit(f'绿幕叠加添加异常: {str(e)}')