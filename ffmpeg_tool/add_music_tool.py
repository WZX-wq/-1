import os
import subprocess


def add_bgm_to_video(input_video_path, bgm_path, video_volume, music_volume, output_path):
    """Mix narration and BGM, rejecting failed FFmpeg output instead of keeping a silent stage."""
    if os.path.abspath(input_video_path) == os.path.abspath(output_path):
        raise ValueError("背景音乐输出路径不能与输入视频相同")
    bg_audio_volume = int(music_volume) / 100
    tts_volume = int(video_volume) / 100
    command = [
        "ffmpeg",
        "-i", input_video_path,
        "-i", bgm_path,
        "-filter_complex",
        f"[0:a]volume={tts_volume}[tts];"
        f"[1:a]volume={bg_audio_volume},aloop=loop=-1:size=2147483647[bg];"
        "[tts][bg]amix=inputs=2:duration=first:dropout_transition=0[outa]",
        "-c:v", "copy",
        "-map", "0:v",
        "-map", "[outa]",
        "-shortest",
        "-y",
        output_path,
    ]
    try:
        if os.path.exists(output_path):
            os.remove(output_path)
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
    except OSError as error:
        raise RuntimeError(f"无法启动 FFmpeg 添加背景音乐：{error}") from error
    if result.returncode != 0:
        try:
            os.remove(output_path)
        except FileNotFoundError:
            pass
        details = (result.stderr or result.stdout or "FFmpeg 未返回错误详情").strip()
        raise RuntimeError(f"FFmpeg 添加背景音乐失败：{details[-1200:]}")
    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("FFmpeg 报告成功，但未生成有效的 BGM 视频文件")
