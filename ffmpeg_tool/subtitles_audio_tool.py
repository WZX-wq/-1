# -*- coding: utf-8 -*-
# 字幕文件，配音文件
import asyncio
import re
import subprocess
import tempfile
import time

import requests
from edge_tts import Communicate
from pydub import AudioSegment
import os
import datetime
from tqdm import tqdm
from zhconv import convert  # 简繁体转换

# 百度api
API_KEY = "HCMW3AxwYcK7R2GsgSLGcie6"
SECRET_KEY = "QlIGAFCGeMMQewXPQp5hYzFJswrcuCqj"


def _get_temp_output_directory(audio_path):
    """临时视频跟随任务音频写入缓存目录，避免污染或写入只读素材目录。"""
    directory_path = os.path.dirname(os.path.abspath(audio_path))
    os.makedirs(directory_path, exist_ok=True)
    return directory_path


# 文本分割
def split_text_into_sentences(text):
    """
    将文本按句子分割
    """
    sentences = re.split(r'(?<=[，。！？])|\s+', text)  # 按中文标点或者空格分割句子
    sentences = [re.sub(r'[，。！？\s]', '', s) for s in sentences if s.strip()]  # 去除空句子
    return sentences

# 说话人补全切句
def split_and_restore_speakers(text: str):
    """
    1. 如果 text 里完全没有 'A:'/'B:'，则默认全部补 'B:'；
    2. 否则按已有标签正常切分；
    3. 按中文标点（，。！？）切句，保留标点；
    4. 返回 ['B:xxx', ...] 或 ['A:xxx', 'B:xxx', ...]
    """
    text = text.strip()
    # 1. 没有任何说话人标签 → 整体包一层 B:
    if not re.search(r'[AB]:', text):
        text = 'B:' + text

    # 2. 按标签把整段切开
    parts = re.split(r'([AB]:)', text)
    if not parts[0].strip():          # 去掉开头空串
        parts = parts[1:]
    speaker_content = [(parts[i], parts[i+1]) for i in range(0, len(parts), 2)]

    # 3. 切句并补回 speaker
    result = []
    for spk, cont in speaker_content:
        cont = cont.strip()
        # sentences = re.split(r'(?<=[，。！？])', cont)
        sentences = re.split(r'(?<=[，。！？])|\s+', cont)
        for sent in sentences:
            sent = sent.strip()
            if sent:
                result.append(spk + sent)
    return result

# def get_audio_length(audio_path):
#     """
#     获取音频文件的长度（秒）
#     """
#     audio = AudioSegment.from_file(audio_path)
#     return float(len(audio) / 1000.0)  # pydub 返回的是毫秒，转换为秒

def get_audio_length(audio_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=True  # 如果命令失败会抛出异常
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return 0.0

def get_video_length(video_path):
    """
    获取视频文件的长度（秒）
    """
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
         video_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return float(result.stdout)


# 转换成时长的格式
def format_time(seconds):
    """
    将秒转换为 HH:MM:SS 格式
    """
    # 计算小时、分钟和秒
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)

    # 格式化输出，确保每个部分都是两位数
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


async def generate_voice(one_text, output_path, increase_db=0, voice_name="zh-CN-YunxiNeural", speed="+0%"):
    """
    生成单段语音文件，并调整音量

    参数：
        text: 要生成的语音文本
        output_path: 最终保存的音频文件路径
        increase_db: 增加的音量分贝数，默认为 10
    """
    temp_output_path = "temp_voice.mp3"
    adjust_temp_output_path = "adjust_temp_voice.mp3"

    # 删除临时文件（可选）
    if os.path.exists(temp_output_path):
        os.remove(temp_output_path)

    if os.path.exists(adjust_temp_output_path):
        os.remove(adjust_temp_output_path)

    # zh-CN-YunxiNeural zh-CN-XiaoxiaoNeural

    # 使用正则表达式匹配数字和百分号
    def replace_percentage(match):
        number = match.group(1)
        return f"百分之{number}"

        # 替换百分号

    one_text = re.sub(r'(\d+)%', replace_percentage, one_text)

    one_text = one_text.replace("@", "艾特")

    max_retries = 6  # 最大重试次数
    retries = 0
    while retries < max_retries:
        try:
            voice = Communicate(text=one_text, voice=voice_name, rate=speed,  pitch="-10Hz")
            # await voice.save(temp_output_path)
            await asyncio.wait_for(voice.save(temp_output_path), timeout=30)
            # 获取原始音频时长
            duration_cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                temp_output_path
            ]
            duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            original_duration = float(duration_result.stdout.strip()) if duration_result.returncode == 0 else 0
            
            # 跳过前0.1秒和后0.1秒的静音
            start_time = 0.1
            end_time = original_duration - 0.1
            
            command = [
                "ffmpeg",
                "-i", temp_output_path,
                "-ss", str(start_time),  # 跳过前0.1秒的静音引子
                "-to", str(end_time),    # 去除后0.1秒的静音尾音
                "-acodec", "libmp3lame",  # 使用 AAC 编码器
                "-b:a", "128k",  # 音频比特率设置为 128k
                "-ar", "44100",  # 采样率设置为 44100 Hz
                "-ac", "2",  # 双声道
                adjust_temp_output_path
            ]
            # subprocess.run(command, check=True)
            run_ffmpeg(command)
            break  # 如果成功生成语音，退出循环
        except Exception as e:
            print(f"Service Unavailable: {e}. Retrying ({retries + 1}/{max_retries})...")
            retries += 1
            await asyncio.sleep(3)  # 等待1秒后重试

    if retries == max_retries:
        print('已结束尝试生成语言，未能生成')
        return ''

    # 加载临时语音文件并调整音量
    audio = AudioSegment.from_file(adjust_temp_output_path)
    audio = audio + increase_db

    # 保存最终的音频文件
    audio.export(output_path, format="mp3")

    # 删除临时文件（可选）
    os.remove(temp_output_path)
    os.remove(adjust_temp_output_path)
    return output_path


def merge_audios(audio_paths, output_path):
    """
    合并多个音频文件
    :param audio_paths: 音频文件路径列表
    :param output_path: 输出音频文件路径
    """

    if not audio_paths:
        raise ValueError("没有可合并的配音文件")

    invalid_audio_paths = [
        path for path in audio_paths
        if not os.path.isfile(path) or os.path.getsize(path) <= 0
    ]
    if invalid_audio_paths:
        raise FileNotFoundError(f"配音文件不存在或为空: {invalid_audio_paths[0]}")

    # 如果文件已存在，删除它
    if os.path.exists(output_path):
        os.remove(output_path)

    output_directory = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(output_directory, exist_ok=True)
    list_file = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix="_audio_concat.txt",
        dir=output_directory, delete=False
    )
    try:
        with list_file:
            for audio_path in audio_paths:
                normalized_path = os.path.abspath(audio_path).replace('\\', '/')
                escaped_path = normalized_path.replace("'", "'\\''")
                list_file.write(f"file '{escaped_path}'\n")

        # 每次合并使用独立列表文件，避免连续任务互相覆盖同一个临时文件。
        command = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file.name,
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            output_path
        ]
        run_ffmpeg(command)
        if not os.path.isfile(output_path) or os.path.getsize(output_path) <= 0:
            raise RuntimeError("FFmpeg 未生成有效的合并配音文件")
    finally:
        try:
            os.remove(list_file.name)
        except FileNotFoundError:
            pass


def produce_subtitle_srt(subtitles, timestamp_folder_path, clips_num=None):
    current_directory = timestamp_folder_path
    if clips_num is None:
        temp_subtitle_path = os.path.join(current_directory, "temp_subtitle.srt")
    else:
        temp_subtitle_path = os.path.join(current_directory, f"temp_subtitle{clips_num}.srt")

    if os.path.exists(temp_subtitle_path):
        os.remove(temp_subtitle_path)

    # 创建字幕文件
    with open(temp_subtitle_path, "w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(subtitles):
            start_time = f"{int(start // 3600):02d}:{int((start % 3600) // 60):02d}:{int(start % 60):02d},{int((start % 1) * 1000):03d}"
            end_time = f"{int(end // 3600):02d}:{int((end % 3600) // 60):02d}:{int(end % 60):02d},{int((end % 1) * 1000):03d}"
            f.write(f"{i + 1}\n{start_time} --> {end_time}\n{text}\n\n")

    # 确保SRT文件存在且为UTF-8编码
    if not os.path.exists(temp_subtitle_path):
        raise FileNotFoundError(f"字幕文件不存在: temp_subtitle.srt")
    else:
        print('已经生成字幕文件')


def adjust_video_speed_to_audio(timestamp_folder_path, video_path):
    """
    根据音频长度调整视频播放速度，并将输入音频添加到视频中
    """
    final_audio_path = "temp_final_audio.mp3"
    # 音频位置
    audio_path = os.path.join(timestamp_folder_path, final_audio_path)

    # 获取音频和视频的长度
    audio_length = get_audio_length(audio_path)
    video_length = get_video_length(video_path)

    # 计算目标播放速度
    speed_factor = audio_length / video_length

    # 调整后的视频
    output_video = 'adjust_speed_video.mp4'
    output_video_path = os.path.join(timestamp_folder_path, output_video)

    if os.path.exists(output_video_path):
        os.remove(output_video_path)

    # 构建 FFmpeg 命令
    command = [
        "ffmpeg",
        "-i", video_path,
        "-i", audio_path,
        "-filter_complex",
        f"[0:v]setpts={speed_factor:.4f}*PTS[v]",
        "-map", "[v]",  # 选择调整后的视频流
        "-map", "1:a",  # 选择输入音频流
        "-c:v", "libx264",  # 使用 H.264 编码器
        "-preset", "fast",  # 编码速度设置为快速
        "-crf", "23",  # 质量设置为默认值 23
        "-c:a", "aac",  # 使用 AAC 编码器
        "-b:a", "128k",  # 音频比特率设置为 128k
        output_video_path
    ]

    # 执行 FFmpeg 命令
    # subprocess.run(command, check=True)
    run_ffmpeg(command)
    return output_video_path


def adjust_video_speed_from_audio_path(audio_path, video_path):
    """
    根据音频长度调整视频播放速度，并将输入音频添加到视频中
    """

    # 获取音频和视频的长度
    audio_length = get_audio_length(audio_path)
    video_length = get_video_length(video_path)

    # 计算目标播放速度
    speed_factor = audio_length / video_length

    # 调整后的视频
    file_name = os.path.basename(video_path)
    directory_path = _get_temp_output_directory(audio_path)

    # 在文件名前面添加 "temp_adjust_" + 时间戳 + 线程ID，避免并发冲突
    timestamp = str(int(time.time() * 1000))  # 使用毫秒级时间戳
    thread_id = str(id(audio_path) % 10000)  # 使用输入音频对象ID作为标识
    new_file_name = f"temp_adjust_{timestamp}_{thread_id}_{file_name}"

    # 重新拼接完整的路径
    output_video_path = os.path.join(directory_path, new_file_name)

    if os.path.exists(output_video_path):
        os.remove(output_video_path)

    # 构建 FFmpeg 命令
    command = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-i", audio_path,
        "-filter_complex",
        f"[0:v]setpts={speed_factor:.4f}*PTS[v]",
        "-map", "[v]",  # 选择调整后的视频流
        "-map", "1:a",  # 选择输入音频流
        "-c:v", "libx264",  # 使用 H.264 编码器
        "-preset", "fast",  # 编码速度设置为快速
        "-crf", "23",  # 质量设置为默认值 23
        "-c:a", "aac",  # 使用 AAC 编码器
        "-b:a", "128k",  # 音频比特率设置为 128k
        output_video_path
    ]

    # 执行 FFmpeg 命令
    # subprocess.run(command, check=True)
    run_ffmpeg(command)
    return output_video_path


async def produce_audio_and_subtitles(timestamp, subtitles_text):
    # 创建一个缓存文件夹，用来存储中间文件
    # 获取当前程序的路径
    current_directory = os.getcwd()

    # 创建时间戳文件夹
    timestamp_folder_name = 'subtitles' + f"{timestamp}"
    timestamp_folder_path = os.path.join(current_directory, timestamp_folder_name)
    # 判断且创建
    if not os.path.exists(timestamp_folder_path):
        os.makedirs(timestamp_folder_path)

    sentences = split_text_into_sentences(subtitles_text)
    segments = [{"text": sentence} for sentence in sentences]

    temp_audio_paths = []  # 用于存储临时音频文件路径
    subtitles_list = []  # 用于记录字幕信息
    # 处理每个分段
    start_time = 0

    for i, seg in enumerate(segments):
        voice_path = f"temp_voice_{i}.mp3"
        full_voice_path = os.path.join(timestamp_folder_path, voice_path)
        await generate_voice(seg["text"], full_voice_path)

        # 获取语音文件的实际长度
        audio_length = get_audio_length(full_voice_path)

        # 记录字幕
        end_time = start_time + audio_length
        subtitles_list.append((start_time, end_time, seg["text"]))

        # 更新开始时间
        start_time = end_time

        # 将临时音频文件路径添加到列表
        temp_audio_paths.append(full_voice_path)

    # 合并所有临时音频文件
    final_audio_path = "temp_final_audio.mp3"
    full_final_audio_path = os.path.join(timestamp_folder_path, final_audio_path)

    merge_audios(temp_audio_paths, full_final_audio_path)

    # 删除临时音频文件
    for temp_audio_path in temp_audio_paths:
        os.remove(temp_audio_path)

    # 生成字幕文件
    produce_subtitle_srt(subtitles_list, timestamp_folder_path)


async def produce_audio_and_subtitles_to_path(api_type, video_tamp_path, subtitles_text, clips_num, audio_setting):
    sentences = split_text_into_sentences(subtitles_text)
    segments = [{"text": sentence} for sentence in sentences]

    temp_audio_paths = []  # 用于存储临时音频文件路径
    subtitles_list = []  # 用于记录字幕信息
    # 处理每个分段
    start_time = 0

    for i, seg in enumerate(segments):
        voice_path = f"temp_voice_{i}.mp3"
        full_voice_path = os.path.join(video_tamp_path, voice_path)
        if api_type == 0:
            await generate_voice(
                one_text=seg["text"],
                output_path=full_voice_path,
                increase_db=audio_setting['volume_value'],
                voice_name=audio_setting['audio_role'],
                speed=audio_setting['speed_value']
            )
        else:
            bd_generate_voice(
                text=seg["text"],
                out_path=full_voice_path,
                role=audio_setting['audio_role'],
                spd=audio_setting['speed_value'],
                pit=audio_setting['tone_value'],
                vol=audio_setting['volume_value']
            )

        # 获取语音文件的实际长度
        audio_length = get_audio_length(full_voice_path)

        # 记录字幕
        end_time = start_time + audio_length
        subtitles_list.append((start_time, end_time, seg["text"]))

        # 更新开始时间
        start_time = end_time

        # 将临时音频文件路径添加到列表
        temp_audio_paths.append(full_voice_path)

    # 合并所有临时音频文件
    final_audio_path = f"temp_final_audio{clips_num}.mp3"
    full_final_audio_path = os.path.join(video_tamp_path, final_audio_path)

    merge_audios(temp_audio_paths, full_final_audio_path)

    # 删除临时音频文件
    for temp_audio_path in temp_audio_paths:
        os.remove(temp_audio_path)

    # 生成字幕文件
    produce_subtitle_srt(subtitles_list, video_tamp_path, clips_num)


async def AB_produce_audio_and_subtitles_to_path(api_type, video_tamp_path, subtitles_text, clips_num, audio_setting):
    sentences = split_and_restore_speakers(subtitles_text)
    segments = [{"text": sentence} for sentence in sentences]

    temp_audio_paths = []  # 用于存储临时音频文件路径
    subtitles_list = []  # 用于记录字幕信息
    # 处理每个分段
    start_time = 0

    for i, seg in enumerate(segments):
        voice_path = f"temp_voice_{i}.mp3"
        full_voice_path = os.path.join(video_tamp_path, voice_path)
        if api_type == 0:
            if seg["text"].startswith('A:'):
                audio_setting['audio_role'] = 'zh-CN-XiaoxiaoNeural'
            elif seg["text"].startswith('B:'):
                audio_setting['audio_role'] = 'zh-CN-YunxiNeural'
            await generate_voice(
                one_text=seg["text"].replace('A:', '').replace('B:', ''),
                output_path=full_voice_path,
                increase_db=audio_setting['volume_value'],
                voice_name=audio_setting['audio_role'],
                speed=audio_setting['speed_value']
            )
        else:
            bd_generate_voice(
                text=seg["text"],
                out_path=full_voice_path,
                role=audio_setting['audio_role'],
                spd=audio_setting['speed_value'],
                pit=audio_setting['tone_value'],
                vol=audio_setting['volume_value']
            )

        # 获取语音文件的实际长度
        audio_length = get_audio_length(full_voice_path)

        # 记录字幕
        end_time = start_time + audio_length
        subtitles_list.append((start_time, end_time, seg["text"]))

        # 更新开始时间
        start_time = end_time

        # 将临时音频文件路径添加到列表
        temp_audio_paths.append(full_voice_path)

    # 合并所有临时音频文件
    final_audio_path = f"temp_final_audio{clips_num}.mp3"
    full_final_audio_path = os.path.join(video_tamp_path, final_audio_path)

    merge_audios(temp_audio_paths, full_final_audio_path)

    # 删除临时音频文件
    for temp_audio_path in temp_audio_paths:
        os.remove(temp_audio_path)

    # 生成字幕文件
    produce_subtitle_srt(subtitles_list, video_tamp_path, clips_num)


# 给视频添加字幕音频
async def add_audio_and_subtitles(timestamp, video_path, out_path):
    current_directory = os.getcwd()
    timestamp_folder_name = 'subtitles' + f"{timestamp}"
    timestamp_folder_path = os.path.join(current_directory, timestamp_folder_name)

    # 根据音频调整视频播放速度
    adjust_video_speed_to_audio(timestamp_folder_path, video_path)

    temp__video_path = os.path.join(timestamp_folder_path, 'adjust_speed_video.mp4')

    temp_subtitle_path = os.path.join(timestamp_folder_path, "temp_subtitle.srt")

    # 转换路径为Windows原生格式
    win_video_path = temp__video_path.replace('/', '\\')
    win_srt_path = temp_subtitle_path.replace('\\', '//').replace(':', '\\:')
    command = [
        'ffmpeg',
        '-y',  # 覆盖输出文件
        '-i', str(win_video_path),
        '-vf', f"subtitles='{win_srt_path}'",
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'copy',  # 保持原音频编码
        str(out_path)
    ]
    try:
        # subprocess.run(command, check=True, encoding='utf-8', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run(command, check=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
        if os.path.exists(temp__video_path):
            os.remove(temp__video_path)
        return True
    except subprocess.CalledProcessError as e:
        print(f"字幕音频添加失败，错误详情:\n{e.stderr}")
        return False


async def _add_audio_subtitles_with_loop(video_path, audio_path, ass_path, ass_title_path, video_length, audio_length):
    """视频循环策略：当音频时长远大于视频时长时，循环播放视频直到音频结束"""
    # 调整后的视频
    file_name = os.path.basename(video_path)
    directory_path = _get_temp_output_directory(audio_path)

    # 在文件名前面添加 "temp_final_"，使用毫秒级时间戳避免并发冲突
    timestamp = str(int(time.time() * 1000))
    thread_id = str(id(audio_path) % 10000)

    new_file_name_1 = f"{timestamp}_{thread_id}_temp_final_{file_name}"
    new_file_name_2 = f"{timestamp}_{thread_id}_temp_final_title{file_name}"

    # 重新拼接完整的路径
    final_output_video_path_1 = os.path.join(directory_path, new_file_name_1)
    final_output_video_path_2 = os.path.join(directory_path, new_file_name_2)

    # 计算需要循环的次数
    loop_times = int(audio_length / video_length) + 1
    print(f"🔄 视频需要循环 {loop_times} 次以匹配音频时长")

    # 创建循环视频的临时文件
    temp_loop_video_path = os.path.join(directory_path, f"{timestamp}_temp_loop_video.mp4")
    
    # 使用FFmpeg创建循环视频
    loop_cmd = [
        'ffmpeg',
        '-stream_loop', str(loop_times),
        '-i', video_path,
        '-t', str(audio_length),  # 确保循环视频时长等于音频时长
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-y',
        temp_loop_video_path
    ]
    
    try:
        subprocess.run(loop_cmd, check=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW, timeout=600)
        print(f"✅ 循环视频创建完成，时长: {audio_length:.2f}秒")
        
        # 添加音频和字幕到循环视频
        return await _add_audio_subtitles_to_video_file(temp_loop_video_path, audio_path, ass_path, ass_title_path, 
                                                       final_output_video_path_1, final_output_video_path_2)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 创建循环视频失败: {e.stderr}")
        # 降级到速度调整策略
        print("🔄 降级到速度调整策略")
        return await _add_audio_subtitles_with_speed_adjust(video_path, audio_path, ass_path, ass_title_path)
    finally:
        # 清理临时循环视频文件
        if os.path.exists(temp_loop_video_path):
            try:
                os.remove(temp_loop_video_path)
            except Exception as e:
                print(f"⚠️ 清理临时循环视频文件失败: {e}")


async def _add_audio_subtitles_with_speed_adjust(video_path, audio_path, ass_path, ass_title_path):
    """速度调整策略：调整视频播放速度以匹配音频"""
    # 调整后的视频
    file_name = os.path.basename(video_path)
    directory_path = _get_temp_output_directory(audio_path)

    # 在文件名前面添加 "temp_final_"，使用毫秒级时间戳避免并发冲突
    timestamp = str(int(time.time() * 1000))
    thread_id = str(id(audio_path) % 10000)

    new_file_name_1 = f"{timestamp}_{thread_id}_temp_final_{file_name}"
    new_file_name_2 = f"{timestamp}_{thread_id}_temp_final_title{file_name}"

    # 重新拼接完整的路径
    final_output_video_path_1 = os.path.join(directory_path, new_file_name_1)
    final_output_video_path_2 = os.path.join(directory_path, new_file_name_2)

    # 根据音频调整视频播放速度
    adjust_video_path = adjust_video_speed_from_audio_path(audio_path, video_path)
    
    # 添加音频和字幕到调整后的视频
    return await _add_audio_subtitles_to_video_file(adjust_video_path, audio_path, ass_path, ass_title_path, 
                                                   final_output_video_path_1, final_output_video_path_2)


async def _add_audio_subtitles_normal(video_path, audio_path, ass_path, ass_title_path):
    """正常处理策略：直接添加音频和字幕"""
    # 调整后的视频
    file_name = os.path.basename(video_path)
    directory_path = _get_temp_output_directory(audio_path)

    # 在文件名前面添加 "temp_final_"，使用毫秒级时间戳避免并发冲突
    timestamp = str(int(time.time() * 1000))
    thread_id = str(id(audio_path) % 10000)

    new_file_name_1 = f"{timestamp}_{thread_id}_temp_final_{file_name}"
    new_file_name_2 = f"{timestamp}_{thread_id}_temp_final_title{file_name}"

    # 重新拼接完整的路径
    final_output_video_path_1 = os.path.join(directory_path, new_file_name_1)
    final_output_video_path_2 = os.path.join(directory_path, new_file_name_2)
    
    # 添加音频和字幕到原始视频
    return await _add_audio_subtitles_to_video_file(video_path, audio_path, ass_path, ass_title_path, 
                                                   final_output_video_path_1, final_output_video_path_2)


async def _add_audio_subtitles_to_video_file(input_video_path, audio_path, ass_path, ass_title_path, 
                                           final_output_video_path_1, final_output_video_path_2):
    """核心函数：将音频和字幕添加到视频文件"""
    try:
        # 检查字幕文件是否存在
        use_subtitle = ass_path and os.path.exists(ass_path)
        
        if use_subtitle:
            print(f"📝 使用字幕文件: {ass_path}")
            # 转换字幕路径
            ass_path_fixed = ass_path.replace('\\', '//').replace(':', '\\:')
            
            command1 = [
                'ffmpeg',
                '-y',  # 覆盖输出文件
                '-i', input_video_path,
                '-i', audio_path,  # 直接添加音频
                '-map', '0:v',  # 使用第一个输入的视频流
                '-map', '1:a',  # 使用第二个输入的音频流（新音频）
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-preset', 'medium',
                '-crf', '23',
                '-vf', f"ass='{ass_path_fixed}'",
                '-shortest',  # 确保输出时长不超过最短输入流
                str(final_output_video_path_1)
            ]
        else:
            print(f"⏭️ 跳过字幕，只添加音频")
            command1 = [
                'ffmpeg',
                '-y',  # 覆盖输出文件
                '-i', input_video_path,
                '-i', audio_path,  # 直接添加音频
                '-map', '0:v',  # 使用第一个输入的视频流
                '-map', '1:a',  # 使用第二个输入的音频流（新音频）
                '-c:v', 'copy',  # 保持视频编码
                '-c:a', 'aac',
                '-b:a', '128k',
                '-shortest',  # 确保输出时长不超过最短输入流
                str(final_output_video_path_1)
            ]
        
        subprocess.run(command1, check=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
        print(f"✅ 第一步：音频添加完成")
        
        # 第二步：如果需要，添加第二个字幕
        if not ass_title_path or not os.path.exists(ass_title_path):
            print(f"⏭️ 无标题字幕，跳过第二步")
            # 清理临时文件
            if input_video_path != final_output_video_path_1 and os.path.exists(input_video_path):
                os.remove(input_video_path)
            return final_output_video_path_1
        else:
            print(f"📝 添加标题字幕...")
            ass_title_path_fixed = ass_title_path.replace('\\', '//').replace(':', '\\:')
            
            command2 = [
                'ffmpeg',
                '-y',  # 覆盖输出文件
                '-i', final_output_video_path_1,
                '-c:v', 'libx264',
                '-c:a', 'copy',
                '-preset', 'medium',
                '-crf', '23',
                '-vf', f"ass='{ass_title_path_fixed}'",
                str(final_output_video_path_2)
            ]
            
            subprocess.run(command2, check=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
            print(f"✅ 第二步：标题字幕添加完成")
            
            # 清理临时文件
            if input_video_path != final_output_video_path_1 and os.path.exists(input_video_path):
                os.remove(input_video_path)
            if os.path.exists(final_output_video_path_1):
                os.remove(final_output_video_path_1)
            
            return final_output_video_path_2
            
    except subprocess.CalledProcessError as e:
        error_output = e.stderr if e.stderr else e.stdout
        print(f"❌ 字幕音频添加失败，错误详情:\n{error_output}")
        # 清理所有临时文件
        if input_video_path != final_output_video_path_1 and os.path.exists(input_video_path):
            try:
                os.remove(input_video_path)
            except:
                pass
        if os.path.exists(final_output_video_path_1):
            try:
                os.remove(final_output_video_path_1)
            except:
                pass
        if os.path.exists(final_output_video_path_2):
            try:
                os.remove(final_output_video_path_2)
            except:
                pass
        return ''


# async def add_audio_and_subtitles_to_part(video_path, audio_path, ass_path, ass_title_path):
#     """主函数：智能选择音频和字幕添加策略"""
#     # 获取音频和视频时长
#     audio_length = get_audio_length(audio_path)
#     video_length = get_video_length(video_path)
#
#     print(f"🎬 视频时长: {video_length:.2f}秒")
#     print(f"🎵 音频时长: {audio_length:.2f}秒")
#     print(f"📊 音频/视频比例: {audio_length/video_length:.2f}")
#
#     # 判断处理策略
#     ratio = audio_length / video_length
#
#     if ratio > 2.0:  # 音频时长超过视频2倍以上，使用视频循环
#         print(f"🔄 音频时长远大于视频({ratio:.1f}x)，使用视频循环策略")
#         return await _add_audio_subtitles_with_loop(video_path, audio_path, ass_path, ass_title_path, video_length, audio_length)
#     elif ratio > 1.3:  # 音频时长超过视频30%以上，使用慢速播放
#         print(f"🐌 音频时长大于视频({ratio:.1f}x)，使用慢速播放策略")
#         return await _add_audio_subtitles_with_speed_adjust(video_path, audio_path, ass_path, ass_title_path)
#     elif ratio < 0.7:  # 音频时长小于视频70%以下，使用快速播放
#         print(f"⚡ 音频时长小于视频({ratio:.1f}x)，使用快速播放策略")
#         return await _add_audio_subtitles_with_speed_adjust(video_path, audio_path, ass_path, ass_title_path)
#     else:  # 时长相近，正常处理
#         print(f"✅ 音频时长与视频相近({ratio:.1f}x)，正常处理")
#         return await _add_audio_subtitles_normal(video_path, audio_path, ass_path, ass_title_path)
async def add_audio_and_subtitles_to_part(video_path, audio_path, ass_path, ass_title_path):
    # 调整后的视频
    file_name = os.path.basename(video_path)
    directory_path = _get_temp_output_directory(audio_path)

    # 在文件名前面添加 "temp_final_"，使用毫秒级时间戳避免并发冲突
    timestamp = str(int(time.time() * 1000))
    thread_id = str(id(audio_path) % 10000)

    new_file_name_1 = f"{timestamp}_{thread_id}_temp_final_{file_name}"
    new_file_name_2 = f"{timestamp}_{thread_id}_temp_final_title{file_name}"

    # 重新拼接完整的路径
    final_output_video_path_1 = os.path.join(directory_path, new_file_name_1)
    final_output_video_path_2 = os.path.join(directory_path, new_file_name_2)

    # 根据音频调整视频播放速度
    adjust_video_path = adjust_video_speed_from_audio_path(audio_path, video_path)

    # 转换路径为Windows原生格式
    ass_path = ass_path.replace('\\', '//').replace(':', '\\:')

    command1 = [
        'ffmpeg',
        '-y',  # 覆盖输出文件
        '-i', str(adjust_video_path),
        '-vf', f"ass='{ass_path}'",
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        str(final_output_video_path_1)
    ]
    try:
        subprocess.run(command1, check=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
        if not ass_title_path or not os.path.exists(ass_title_path):
            if os.path.exists(adjust_video_path):
                os.remove(adjust_video_path)
            return final_output_video_path_1
        else:
            ass_title_path = ass_title_path.replace('\\', '//').replace(':', '\\:')
            command2 = [
                'ffmpeg',
                '-y',  # 覆盖输出文件
                '-i', str(final_output_video_path_1),
                '-vf', f"ass='{ass_title_path}'",
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                str(final_output_video_path_2)
            ]
            subprocess.run(command2, check=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
            if os.path.exists(adjust_video_path):
                os.remove(adjust_video_path)
            if os.path.exists(final_output_video_path_1):
                os.remove(final_output_video_path_1)
            return final_output_video_path_2
    except subprocess.CalledProcessError as e:
        print(f"字幕音频添加失败，错误详情:\n{e.stderr}")
        # 清理所有临时文件
        if os.path.exists(adjust_video_path):
            try:
                os.remove(adjust_video_path)
            except:
                pass
        if os.path.exists(final_output_video_path_1):
            try:
                os.remove(final_output_video_path_1)
            except:
                pass
        if os.path.exists(final_output_video_path_2):
            try:
                os.remove(final_output_video_path_2)
            except:
                pass
        return ''


# 获取指定格式文件列表
def find_files(path, suffixes):
    """
    用来获取path下的所有指定格式文件
    @params:
        path      - Required  : 目标路径 (str)
        suffixes  - Required  : 文件格式列表 (list)
    """
    files = []
    for root, dirs, filenames in os.walk(path):
        for file in filenames:
            if any(file.lower().endswith('.' + suffix.lower()) for suffix in suffixes):
                files.append(os.path.abspath(os.path.join(root, file)))
    return files


# 秒转时分秒毫秒
def seconds_to_hmsm(seconds):
    """
    输入一个秒数，输出为H:M:S:M时间格式
    @params:
        seconds   - Required  : 秒 (float)
    """
    hours = str(int(seconds // 3600))
    minutes = str(int((seconds % 3600) // 60))
    seconds = seconds % 60
    milliseconds = str(int((seconds - int(seconds)) * 1000))  # 毫秒留三位
    seconds = str(int(seconds))
    # 补0
    if len(hours) < 2:
        hours = '0' + hours
    if len(minutes) < 2:
        minutes = '0' + minutes
    if len(seconds) < 2:
        seconds = '0' + seconds
    if len(milliseconds) < 3:
        milliseconds = '0' * (3 - len(milliseconds)) + milliseconds
    return f"{hours}:{minutes}:{seconds},{milliseconds}"


def voice_to_subtitles(file_path):
    import whisper

    supported_formats = ['mp4', 'mp3', 'wav', 'avi']

    if os.path.isdir(file_path):
        files = find_files(file_path, supported_formats)
    elif os.path.isfile(file_path) and file_path.lower().endswith(tuple(supported_formats)):
        files = [file_path]
    else:
        print("The provided path is neither a file nor a directory with supported files.")
        return

    if not files:
        print("No supported files found in the specified directory.")
        return

    # 获取模型 中等
    model = whisper.load_model('base')

    for file in tqdm(files):
        # 字幕文件保存路径
        save_file = file.rsplit('.', 1)[0] + ".srt"  # 替换文件扩展名为.srt
        # 判断文件是否存在，存在则说明已经有字幕，跳过
        if os.path.exists(save_file):
            tqdm.write(f"Skipping {file}, subtitle file already exists.")
            continue

        # 获取当前文件识别开始时间
        start_time = datetime.datetime.now()
        tqdm.write(f"Processing: {file} -- {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 文字识别
        res = model.transcribe(file, fp16=False, language='Chinese')

        # 写入字幕文件
        with open(save_file, 'w', encoding='utf-8') as f:
            i = 1
            for r in res['segments']:
                f.write(str(i) + '\n')
                f.write(seconds_to_hmsm(float(r['start'])) + ' --> ' + seconds_to_hmsm(float(r['end'])) + '\n')
                i += 1
                f.write(convert(r['text'], 'zh-cn') + '\n')  # 结果可能是繁体，转为简体zh-cn
                f.write('\n')

        # 获取当前文件识别结束时间
        end_time = datetime.datetime.now()
        tqdm.write(f"Completed: {file} -- {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        tqdm.write(f"Time taken: {end_time - start_time}")


# 给视频添加字幕
async def add_subtitles(subtitle_path, video_path, out_path):
    # 转换路径为 Windows 原生格式
    win_video_path = video_path.replace('/', '\\')
    win_srt_path = subtitle_path.replace('\\', '//').replace(':', '\\:')  # 使用标准替换
    command = [
        'ffmpeg',
        '-y',  # 覆盖输出文件
        '-i', str(win_video_path),
        '-vf', f"ass='{win_srt_path}'",  # 直接使用 ass 过滤器
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'copy',  # 保持原音频编码
        str(out_path)
    ]
    try:
        # subprocess.run(command, check=True, encoding='utf-8', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run(command, check=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
        return True
    except subprocess.CalledProcessError as e:
        print(f"字幕添加失败，错误详情:\n{e.stderr}")
        return False


# 给视频添加音频
async def add_audio(audio_path, video_path, out_path):
    # 获取音频和视频的长度
    audio_length = get_audio_length(audio_path)
    video_length = get_video_length(video_path)

    # 计算目标播放速度
    speed_factor = audio_length / video_length
    command = [
        "ffmpeg",
        "-i", video_path,
        "-i", audio_path,
        "-filter_complex",
        f"[0:v]setpts={speed_factor:.4f}*PTS[v]",
        "-map", "[v]",  # 选择调整后的视频流
        "-map", "1:a",  # 选择输入音频流
        "-c:v", "libx264",  # 使用 H.264 编码器
        "-preset", "fast",  # 编码速度设置为快速
        "-crf", "23",  # 质量设置为默认值 23
        "-c:a", "aac",  # 使用 AAC 编码器
        "-b:a", "128k",  # 音频比特率设置为 128k
        out_path
    ]
    # 执行 FFmpeg 命令
    # subprocess.run(command, check=True)
    run_ffmpeg(command)

def run_ffmpeg(command):
    try:
        # 调用 FFmpeg 命令（带超时控制）
        subprocess.run(
            command,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=300  # 5分钟超时
        )
    except subprocess.TimeoutExpired:
        print(f"FFmpeg 命令执行超时: {command[0]}")
        raise
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg 错误: {e}")
        raise
    except Exception as e:
        print(f"运行 FFmpeg 时发生错误: {e}")
        raise


async def generate_title_voice(one_text, voice_name="zh-CN-YunxiNeural", speed="+0%"):
    temp_title_output_path = "temp_title_voice.mp3"
    # 删除临时文件（可选）
    if os.path.exists(temp_title_output_path):
        os.remove(temp_title_output_path)
    # zh-CN-YunxiNeural zh-CN-XiaoxiaoNeural
    max_retries = 3  # 最大重试次数
    retries = 0
    while retries < max_retries:
        try:
            voice = Communicate(text=one_text, voice=voice_name, rate=speed)
            await voice.save(temp_title_output_path)
            break  # 如果成功生成语音，退出循环
        except Exception as e:
            print(f"Service Unavailable: {e}. Retrying ({retries + 1}/{max_retries})...")
            retries += 1
    if retries == max_retries:
        print('已结束尝试生成标题语言，未能生成')
        return ''
    audio_time = get_audio_length(temp_title_output_path)
    # 删除临时文件（可选）
    os.remove(temp_title_output_path)
    return audio_time


def bd_generate_voice(text, out_path, role, spd, pit, vol):
    url = "https://tsn.baidu.com/text2audio"

    # 使用正则表达式匹配数字和百分号
    def replace_percentage(match):
        number = match.group(1)
        return f"百分之{number}"

    # 替换百分号
    text = re.sub(r'(\d+)%', replace_percentage, text)

    text = text.replace("@", "艾特")

    payload = f'tex={text}&tok=' + get_access_token() + f'&cuid=fRKFpYhjEDBs2LyUHH78JkZv3h7nEURb&ctp=1&lan=zh&spd={spd}&pit={pit}&vol={vol}&per={role}&aue=3'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '*/*'
    }

    response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))

    # 检查响应是否成功
    if response.status_code == 200:
        # 将响应内容保存为 MP3 文件
        with open(out_path, "wb") as f:
            f.write(response.content)
        print(f"音频文件已保存为{out_path}")
    else:
        print(f"请求失败，状态码：{response.status_code}")
    print('生成语言')


def get_access_token():
    """
    使用 AK，SK 生成鉴权签名（Access Token）
    :return: access_token，或是None(如果错误)
    """
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    return str(requests.post(url, params=params).json().get("access_token"))


# split_and_restore_speakers('白墙泡在油菜花里')
