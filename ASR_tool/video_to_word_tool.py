# 提取视频中的文案
import os
import time

import zhconv
import whisper
from PyQt6.QtCore import QThreadPool, QEventLoop

from ai_tool.ai_text_production import ai_fix_errors
from worker.ai_worker import AiDisposeIntro


# 提取视频中的文案
def get_copy_from_video(account_name, video_dir_path, video_type):
    # model_type = input('请选择语音识别模型类型 tiny、base、small、medium、large:\n')
    model_type = 'small'
    print(f'正在加载语音识别模型openai-whisper---{model_type}，首次打开需要下载')
    # 加载模型（首次运行会自动下载模型）
    model = whisper.load_model(model_type)  # 中文建议用 medium 或 large
    VIDEO_SUFFIX = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.rmvb', '.m4v'}
    # excel文案文件
    timestamp = int(time.time() * 1000)  # 当前时间戳，毫秒级
    task_copy_file_name = f"{timestamp}_copy.xlsx"
    task_label_file_name = f"{timestamp}_label.xlsx"
    task_copy_file_path = os.path.join(video_dir_path, task_copy_file_name)
    task_label_file_path = os.path.join(video_dir_path, task_label_file_name)

    # 遍历文件夹中的所有文件
    for filename in os.listdir(video_dir_path):
        if os.path.isfile(os.path.join(video_dir_path, filename)):
            if os.path.splitext(filename)[1].lower() in VIDEO_SUFFIX:
                # 构造文件的完整路径
                file_path = os.path.join(video_dir_path, filename)
                # 检查是否是视频文件
                if os.path.isfile(file_path):
                    # 使用 initial_prompt 参数，确保输出简体中文
                    result = model.transcribe(file_path, language="zh", initial_prompt="以下是普通话的句子。")
                    # 如果仍然输出繁体字，使用 zhconv 转换为简体
                    result["text"] = zhconv.convert(result["text"], "zh-cn")
                    print(result["text"])
                    ai_worker = AiDisposeIntro(task_copy_file_path, task_label_file_path, account_name,
                                               result["text"])
                    # Ai处理识别到的文案
                    if video_type == 1:
                        ai_worker = AiDisposeIntro(task_copy_file_path, task_label_file_path, account_name,
                                                   result["text"])

                    loop = QEventLoop()
                    ai_worker.signals.finished.connect(loop.quit)
                    ai_worker.signals.errorOccurred.connect(loop.quit)
                    QThreadPool.globalInstance().start(ai_worker)
                    loop.exec()


# get_copy_from_video('有品位', r'D:\生成视频', 1)

# get_copy_from_video(r'D:\生成视频')
