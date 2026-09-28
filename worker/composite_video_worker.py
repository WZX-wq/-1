import asyncio
import os
import sys
from threading import Lock
from typing import List, Tuple, Optional

from ffmpeg_tool.subtitles_audio_tool import add_audio_and_subtitles_to_part
from ffmpeg_tool.video_concat_tool import addCover, concatenate_videos_in_segments
from sanong_generation.media_core import compose_video_segments
from worker.worker_signals import WorkerSignals
from PyQt6.QtCore import QRunnable


def _safe_print(message):
    """兼容 Windows GBK 控制台，日志字符不能中断视频任务。"""
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(str(message).encode(encoding, errors="replace").decode(encoding))


# 添加音频字幕合成视频
class CompositeVideo(QRunnable):
    def __init__(self, video_list, audio_list, ass_list, ass_title_list, output_final_path, transition_setting,
                 pic_time=3, max_workers=4):
        super().__init__()
        self.video_list = video_list
        self.audio_list = audio_list
        self.ass_list = ass_list
        self.ass_title_list = ass_title_list
        self.output_final_path = output_final_path
        self.transition_setting = transition_setting
        self.pic_time = pic_time
        self.max_workers = max_workers  # 最大并发线程数
        self.signals = WorkerSignals()
        self._progress_lock = Lock()  # 进度锁，防止线程竞争
        self._processed_count = 0  # 已处理计数

    def _process_single_video(self, args: Tuple[int, str, str, str, Optional[str]]) -> Tuple[int, str, bool, str]:
        """处理单个视频片段的线程函数"""
        i, video_path, audio_path, ass_path, ass_title_path = args
        
        try:
            # 在线程中创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                final_output_video_path = loop.run_until_complete(
                    asyncio.wait_for(
                        self.add_process(video_path, audio_path, ass_path, ass_title_path),
                        timeout=180  # 3分钟超时
                    )
                )
                
                success = final_output_video_path and os.path.exists(final_output_video_path)
                
                # 线程安全地更新进度
                with self._progress_lock:
                    self._processed_count += 1
                    progress_text = f"🔄 处理进度: {self._processed_count}/{len(self.video_list)}"
                    if success:
                        _safe_print(f"✅ 成功处理视频片段 {i+1}/{len(self.video_list)}")
                    else:
                        _safe_print(f"❌ 视频片段 {i+1} 处理失败")
                    
                    # 发送进度信号
                    self.signals.progress.emit(self._processed_count, len(self.video_list), progress_text)
                
                error_msg = ""
                if not success:
                    error_msg = f"片段 {i+1}: 处理失败"
                
                return i, final_output_video_path, success, error_msg
                
            finally:
                loop.close()
                
        except asyncio.TimeoutError:
            error_msg = f"片段 {i+1}: 处理超时"
            _safe_print(f"❌ 视频片段 {i+1} 处理超时")
            with self._progress_lock:
                self._processed_count += 1
                self.signals.progress.emit(self._processed_count, len(self.video_list), 
                                         f"🔄 处理进度: {self._processed_count}/{len(self.video_list)}")
            return i, "", False, error_msg
            
        except Exception as e:
            error_msg = f"片段 {i+1}: {str(e)}"
            _safe_print(f"❌ 视频片段 {i+1} 处理异常: {e}")
            with self._progress_lock:
                self._processed_count += 1
                self.signals.progress.emit(self._processed_count, len(self.video_list), 
                                         f"🔄 处理进度: {self._processed_count}/{len(self.video_list)}")
            return i, "", False, error_msg

    def run(self):
        try:
            compose_video_segments(
                self.video_list,
                self.audio_list,
                self.ass_list,
                self.ass_title_list,
                self.output_final_path,
                self.transition_setting,
                self.pic_time,
                self.max_workers,
                segment_processor=self._process_single_video,
                merge_callback=self.composite_process,
                cover_callback=self.addCover,
            )
            self.signals.finished.emit('完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))

    async def add_process(self, video_path, audio_path, ass_path, ass_title_path):
        # 调用添加
        final_output_video_path = await add_audio_and_subtitles_to_part(video_path, audio_path, ass_path,
                                                                        ass_title_path)
        return final_output_video_path

    async def composite_process(self, final_part_video_list, out_path):
        # 调用合并
        concatenate_videos_in_segments(final_part_video_list, out_path,
                                       str(self.transition_setting['transitionNum']),
                                       self.transition_setting['transitionTime'])

    # 添加封面
    async def addCover(self, video_path, pic_time):
        # 截取图片作为封面
        addCover(video_path, self.output_final_path, pic_time)
