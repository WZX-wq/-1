import subprocess


def add_bgm_to_video(input_video_path, bgm_path, video_volume, music_volume, output_path):
    """
    为已生成的视频添加背景音乐（最后一步处理）

    参数：
        input_video_path: 已生成的视频路径（包含原配音）
        bgm_path: 背景音乐路径
        output_path: 输出路径
    """
    try:
        bg_audio_volume = int(music_volume)/100   # 转换为0到1之间的浮点数
        tts_volume = int(video_volume)/100  # 转换为0到1之间的浮点数
        # bg_audio_volume: float = 0.5  # 将背景音音量设置为原来的 50%
        # tts_volume: float = 0.8       # 将原配音音量设置为原来的 80%
        command = [
            "ffmpeg",
            "-i", input_video_path,
            "-i", bgm_path,
            "-filter_complex",
            f"[0:a]volume={tts_volume}[tts];"  # 调整原配音音量
            f"[1:a]volume={bg_audio_volume},aloop=loop=-1:size=2147483647[bg];"  # 循环播放背景音乐
            "[tts][bg]amix=inputs=2:duration=first:dropout_transition=0[outa]",  # 混合音频并命名输出为outa
            "-c:v", "copy",  # 视频流直接复制，不重新编码
            "-map", "0:v",  # 映射视频流
            "-map", "[outa]",  # 映射混合后的音频流
            "-shortest",  # 使输出与视频长度一致
            "-y",  # 覆盖已存在的输出文件
            output_path
        ]
        # subprocess.run(command, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run(command, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(e)