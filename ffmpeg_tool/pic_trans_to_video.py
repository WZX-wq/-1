import math
import shutil
import subprocess
import os
import tempfile
from datetime import datetime
from typing import Tuple, Optional

from zhdate import ZhDate

from ai_tool.ai_text_production import deepseek_ai_greetings_1, deepseek_ai_greetings_2


async def image_to_video(image_path, video_duration, output_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件未找到：{image_path}")

    # 1. 先创建一个无音频的临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp_video = tmp.name

    try:
        # 纯图片 → 无音频
        # 使用引号包围路径以防止路径中包含特殊字符导致的问题
        # 确保路径使用正确的分隔符
        normalized_image_path = os.path.normpath(image_path)
        normalized_tmp_video = os.path.normpath(tmp_video)
        
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", normalized_image_path,
            "-c:v", "libx264",
            "-t", str(video_duration),
            "-pix_fmt", "yuv420p",
            "-vf", "fps=25,scale=trunc(iw/2)*2:trunc(ih/2)*2",  # 确保尺寸为偶数，添加scale滤镜
            "-an",           # 先别带音轨
            normalized_tmp_video
        ], check=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)

        # 2. 补一条静音轨
        # 对第二个命令也进行路径标准化
        normalized_output_path = os.path.normpath(output_path)
        
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-i", normalized_tmp_video,
            "-shortest",
            "-c:v", "copy",
            "-c:a", "aac",
            normalized_output_path
        ], check=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)

        print(f"视频已生成（含静音轨）：{output_path}")

    except subprocess.CalledProcessError as e:
        print(f"生成视频时出错：{e}")
    finally:
        # 清理临时文件
        normalized_tmp_video = os.path.normpath(tmp_video)
        if os.path.exists(normalized_tmp_video):
            os.remove(normalized_tmp_video)


def overlay_transparent_animation(
        background_video: str,
        material_path_dir: str,
        output_path: str,
        position: Tuple[int, int] = (0, 0),
        size: Optional[Tuple[int, int]] = None,  # 修复：使用Optional类型注解
        fps: int = 30,
        crf: int = 22
) -> None:
    """
    使用FFmpeg命令实现透明动画叠加

    Args:
        background_video: 背景视频路径
        material_path_dir: 黑底素材视频路径
        output_path: 输出路径
        position: (x, y) 叠加位置
        size: (width, height) 缩放尺寸，None保持原尺寸
        loop_duration: 循环时长(秒)，None为自动
        fps: 输出帧率
        crf: 画质(18-28，越小质量越高)
    """

    try:
        # 标准化路径以确保兼容性
        normalized_background_video = os.path.normpath(background_video)
        normalized_output_path = os.path.normpath(output_path)
        
        # 叠加到背景视频
        cmd2 = [
            'ffmpeg',
            '-i', normalized_background_video,
            '-framerate', str(fps),
            '-i', os.path.join(material_path_dir, 'frame_%04d.png'),  # 这里是图像序列模式，不需要标准化
            '-filter_complex',
            _build_filter_complex(position, size),
            '-c:v', 'libx264',
            '-crf', str(crf),
            '-c:a', 'copy',
            '-movflags', '+faststart',
            '-y',  # 覆盖输出文件
            normalized_output_path
        ]
        subprocess.run(cmd2, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
    except Exception as e:
        print(str(e))


def _build_filter_complex(
        position: Tuple[int, int],
        size: Optional[Tuple[int, int]] = None  # 修复：使用Optional类型注解
) -> str:
    """构建filter_complex字符串"""
    x, y = position
    width, _ = size if size else (300, -1)  # 默认宽度为300，高度自动保持比例

    filters = [
        f"[1:v]format=rgba,scale={width}:-1[fg]",
        f"[0:v][fg]overlay=x={x}:y={y}:shortest=1"
    ]

    return ";".join(filters)


# 黑色背景素材视频转为图片png序列
def video_trans_to_pic_list(video_path, material_file_name):
    # 临时目录存放PNG序列
    current_path = os.getcwd()

    # 存放素材的文件夹

    material_origin_file_path = os.path.join(current_path, 'material')

    material_file_path = os.path.join(material_origin_file_path, material_file_name)

    try:
        # 标准化路径以确保兼容性
        normalized_video_path = os.path.normpath(video_path)
        
        # 阶段1：黑底视频转透明PNG序列
        cmd1 = [
            'ffmpeg',
            '-i', normalized_video_path,
            '-vf', f"colorkey=0x000000:0.1:0.1,format=rgba",
            '-compression_level', '6',
            os.path.join(material_file_path, 'frame_%04d.png')
        ]
        subprocess.run(cmd1, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
        print('素材视频转图片以完成')
    except Exception as e:
        print('素材视频转图片序列失败：' + str(e))


# 复制延长素材图片序列，以延长添加上素材的时间

def copy_and_rename_png_in_same_folder(folder_path, start_index):
    """
    在同一文件夹中复制并重命名 PNG 文件序列。

    Args:
        folder_path (str): 包含 PNG 文件的文件夹路径。
        start_index (int): 新文件命名的起始索引。
    """
    # 确保文件夹存在
    if not os.path.exists(folder_path):
        print(f"文件夹 {folder_path} 不存在")
        return

    # 获取文件夹中的所有文件
    files = os.listdir(folder_path)
    png_files = [f for f in files if f.startswith("frame_") and f.endswith(".png")]

    # 对 PNG 文件按名称排序（按数字部分排序）
    # 提取数字部分并转换为整数进行排序
    png_files.sort(key=lambda x: int(x.split("_")[1].split(".")[0]))

    # 复制并重命名文件
    for i, file_name in enumerate(png_files):
        # 构建原始文件的完整路径
        source_path = os.path.join(folder_path, file_name)

        # 构建新文件名和路径
        new_index = start_index + i
        new_file_name = f"frame_{new_index:04d}.png"
        new_path = os.path.join(folder_path, new_file_name)

        # 检查新文件是否已存在，避免覆盖
        if os.path.exists(new_path):
            print(f"跳过已存在的文件: {new_file_name}")
            continue

        # 复制文件并重命名
        shutil.copy2(source_path, new_path)
        print(f"已复制并重命名为: {new_file_name}")


def process_poem(poem_lines, font_size, output_path):
    """处理一首诗，将每句诗转换为带有抖动效果的字幕"""
    try:
        # 目标分辨率（1080p）
        target_width = 1080
        target_height = 1920

        # 创建一个字幕文件
        with open(output_path, 'w', encoding='utf-8') as f:
            # 写入字幕文件的头部信息
            f.write("[Script Info]\n")
            f.write("ScriptType: v4.00+\n")
            f.write("PlayResX: 1080\n")
            f.write("PlayResY: 1920\n")
            f.write("\n")
            f.write("[V4+ Styles]\n")
            f.write(
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write(
                f"Style: Default,三极行楷简体-粗,{font_size},&H0000FFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,20,1\n")
            f.write("\n")
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

            # 定义每个字的抖动效果
            def create_jitter_effect(char, position, direction, font_size):
                # 抖动的持续时间（5000ms）
                duration = 5000
                # 每个抖动周期的时间（ms）
                cycle = 500
                # 抖动的角度范围
                angle_range = 1
                # 抖动的偏移范围（像素）
                offset_range = 5

                # 生成抖动效果的ASS代码
                effect = [
                    r"{{\pos({},{})\fs{}\bord1}}".format(position[0], position[1], font_size)
                ]
                current_time = 0
                for i in range(int(duration / cycle)):
                    if direction == 0:
                        # 向右倾斜并偏移
                        effect.append(r"{{\t({}, {}, \frz{}\\fscx110\\fscy110\pos({},{}))}}".format(
                            current_time, current_time + cycle // 2, angle_range, position[0] + offset_range, position[1]
                        ))
                        # 向左倾斜并偏移
                        effect.append(r"{{\t({}, {}, \frz-{}\\fscx110\\fscy110\pos({},{}))}}".format(
                            current_time + cycle // 2, current_time + cycle, angle_range, position[0] - offset_range,
                            position[1]
                        ))
                    else:
                        # 向右倾斜并偏移
                        effect.append(r"{{\t({}, {}, \frz-{}\\fscx110\\fscy110\pos({},{}))}}".format(
                            current_time, current_time + cycle // 2, angle_range, position[0] + offset_range,
                            position[1]
                        ))
                        # 向左倾斜并偏移
                        effect.append(r"{{\t({}, {}, \frz{}\\fscx110\\fscy110\pos({},{}))}}".format(
                            current_time + cycle // 2, current_time + cycle, angle_range, position[0] - offset_range,
                            position[1]
                        ))
                    current_time += cycle
                # 恢复到原始状态
                effect.append(r"{{\t({}, {}, \frz0\\fscx100\\fscy100\pos({},{})}}".format(
                    current_time, current_time + cycle, position[0], position[1]
                ))
                return ''.join(effect) + char

            # 计算每句诗的位置
            line_height = font_size + 20  # 每行的高度（像素）行间隙
            start_y = 1200  # 第一行的起始Y坐标

            # 设定字幕的起始时间为5秒（5000ms），结束时间为10秒（10000ms）
            start_time = 5000  # 5秒
            end_time = 10000  # 10秒

            # 处理每一句诗
            for line_index, line in enumerate(poem_lines):
                # 计算这句诗的Y坐标
                y = start_y + line_index * line_height

                # 计算这句诗的起始X坐标，使其居中
                line_width = len(line) * (font_size * 0.8)   # 假设每个字符宽度为20像素
                x = (target_width - line_width) // 2 - 35

                direction = 0

                # 处理每个字符
                for char_index, char in enumerate(line):
                    # 计算字符的X坐标
                    char_x = x + char_index * font_size  # 假设字符间距为20像素

                    if char_index % 2 == 0:
                        direction = 0
                    else:
                        direction = 1

                    # 创建抖动效果
                    effect = create_jitter_effect(char, (char_x, y), direction, font_size)

                    # 写入字幕行（所有字符在5秒时出现，10秒时消失）
                    f.write(
                        "Dialogue: 0,{:d}:{:02d}:{:02d}.00,{:d}:{:02d}:{:02d}.00,Default,,0000,0000,0000,,{}\n".format(
                            start_time // 3600000, (start_time // 60000) % 60, (start_time // 1000) % 60,
                            end_time // 3600000, (end_time // 60000) % 60, (end_time // 1000) % 60,
                            effect
                        ))

        print(f"成功生成字幕文件: {output_path}")
        return output_path

    except Exception as e:
        print(f"处理字幕出错: {e}")
        return None


# 创建扇形的标题 日期
def create_radial_title(title_text, output_path, font_size=80, radius=500, center_x=280, center_y=800, duration=10000):
    """
    创建每个文字底部指向圆心的扇形标题，根据字符类型动态调整间隔

    参数:
        title_text: 标题文本(从左到右顺序)
        output_path: 输出ASS文件路径
        font_size: 字体大小(默认60)
        radius: 半径(像素，默认500)
        center_x: 圆心X坐标(默认540)
        center_y: 圆心Y坐标(默认1200，置于画面下方)
        duration: 总持续时间(毫秒，默认5000=5秒) 设置
    """
    # title_text = date_title_setting['title_text']
    # font_size = date_title_setting['font_size']
    # fontname = date_title_setting['font_name']
    # font_color = date_title_setting['font_color']
    # border_color = date_title_setting['border_color']
    # background_color = date_title_setting['background_color']
    # coordinate_location = date_title_setting['coordinate_location']
    # coordinate_location_xy = []
    # if
    #
    #
    #
    # date_title_setting =

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # 写入ASS文件头部
            f.write("[Script Info]\n")
            f.write("ScriptType: v4.00+\n")
            f.write("PlayResX: 1080\n")
            f.write("PlayResY: 1920\n")
            f.write("\n")
            f.write("[V4+ Styles]\n")
            f.write(
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write(
                f"Style: TitleStyle,三极行楷简体-粗,{font_size},&H0000FFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,7,0,0,0,1\n")
            f.write("\n")
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            year = int(title_text[:4])
            month = int(title_text[4:6])
            day = int(title_text[6:8])
            formatted_date = f"{year}年{month}月{day}日"
            formatted_date_length = len(formatted_date)
            if formatted_date_length == 0:
                return

            # 初始化总角度
            total_angle = 0

            # 计算每个字符之间的角度间隔
            for i in range(formatted_date_length - 1):
                current_char = formatted_date[i]
                next_char = formatted_date[i + 1]
                # 判断字符类型
                if current_char.isdigit() and next_char.isdigit():
                    total_angle += 6
                elif (current_char.isdigit() and next_char.isalpha()) or (
                        current_char.isalpha() and next_char.isdigit()):
                    total_angle += 8
                # else:
                #     total_angle += 8

            # 起始和结束角度，居中分布
            start_angle = 90 + total_angle / 2
            end_angle = 90 - total_angle / 2

            # 时间设置
            start_time = 0
            end_time = duration

            # 为每个字符创建位置和旋转角度
            current_angle = start_angle
            for i, char in enumerate(formatted_date):
                # 计算当前字符的角度(弧度)
                angle_deg = current_angle
                angle_rad = math.radians(angle_deg)

                # 计算字符位置(沿圆弧)
                x = center_x + radius * math.cos(angle_rad)
                y = center_y - radius * math.sin(angle_rad)  # Y轴向下为正

                # 计算文字旋转角度(底部指向圆心)
                text_angle = angle_deg - 90  # 底部指向圆心

                # 创建效果(包含淡入淡出、位置和旋转)
                effect = (
                        r"{\pos(%.1f,%.1f)\frz%.1f}"  # 位置和旋转
                        % (x, y, text_angle)
                )

                # 写入字幕行
                f.write(
                    "Dialogue: 0,{0:01d}:{1:02d}:{2:02d}.00,{3:01d}:{4:02d}:{5:02d}.00,TitleStyle,,0,0,0,,{6}{7}\n".format(
                        start_time // 3600000, (start_time // 60000) % 60, (start_time // 1000) % 60,
                        end_time // 3600000, (end_time // 60000) % 60, (end_time // 1000) % 60,
                        effect, char
                    ))

                # 更新当前角度
                if i < formatted_date_length - 1:
                    next_char = formatted_date[i + 1]
                    if char.isdigit() and next_char.isdigit():
                        current_angle -= 6
                    elif (char.isdigit() and next_char.isalpha()) or (char.isalpha() and next_char.isdigit()):
                        current_angle -= 8
                    # else:
                    #     current_angle -= 8

            nl_text = solar_to_lunar(title_text)
            # 计算农历日期标题的宽度
            nl_text_width = len(nl_text) * font_size * 0.7  # 假设每个字符宽度为30像素
            nl_text_x = center_x - nl_text_width // 2  # 居中对齐
            nl_text_y = center_y + radius - 800  # 放在扇形文字下方
            # 写入农历日期标题
            f.write(
                "Dialogue: 0,{0:01d}:{1:02d}:{2:02d}.00,{3:01d}:{4:02d}:{5:02d}.00,TitleStyle,,0,0,0,,{{\\pos({6},"
                "{7})}}{8}\n".format(
                    start_time // 3600000, (start_time // 60000) % 60, (start_time // 1000) % 60,
                    end_time // 3600000, (end_time // 60000) % 60, (end_time // 1000) % 60,
                    nl_text_x, nl_text_y, nl_text
                ))

        print(f"成功创建径向标题文件: {output_path}")
        return output_path

    except Exception as e:
        print(f"创建径向标题出错: {e}")
        return None


# 将公历日期转换为农历日期
def solar_to_lunar(solar_date_str):
    """
    将公历日期转换为农历日期（更精确版本）
    例如：20250619 -> "农历乙巳年五月廿四"

    参数:
        solar_date_str: 公历日期字符串，格式为YYYYMMDD

    返回:
        农历日期字符串，格式为"农历[年干支][年属相]年[月][日]"
    """
    try:
        # 安装依赖：pip install zhdate
        year = int(solar_date_str[:4])
        month = int(solar_date_str[4:6])
        day = int(solar_date_str[6:8])

        # 转换为农历日期
        lunar_date = ZhDate.from_datetime(datetime(year, month, day))

        # 天干地支和生肖映射
        heavenly_stems = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        earthly_branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        zodiacs = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

        # 计算年干支和属相
        year_cyc = (lunar_date.lunar_year - 4) % 60  # 1984年是甲子年(60年周期)
        stem_index = year_cyc % 10
        branch_index = year_cyc % 12
        year_name = heavenly_stems[stem_index] + earthly_branches[branch_index]
        zodiac = zodiacs[branch_index]

        # 处理月份
        month_names = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
        month_name = month_names[lunar_date.lunar_month - 1]
        # if lunar_date.is_leap:
        #     month_name = "闰" + month_name

        # 处理日期
        day_names = ["初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
                     "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
                     "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"]
        day_name = day_names[lunar_date.lunar_day - 1]

        # return f"农历{year_name}{zodiac}年{month_name}月{day_name}"
        return f"农历{month_name}月{day_name}"

    except Exception as e:
        print(f"日期转换出错: {e}")
        return ""  # 修复：返回空字符串而不是None


# 添加滑动文字字幕
def create_poem_ass(poem_lines, output_file="poem.ass",
                    start_time=1.0, line_interval=1.8,
                    slide_in_duration=1.0, hold_duration=2.6,
                    fade_out_duration=0.8, font_size=150,
                    font_name="SimSun", positions=None):
    """
    创建诗句逐行滑入并最终统一消失的ASS字幕文件

    参数:
        poem_lines: 诗句列表
        output_file: 输出文件名
        start_time: 第一句开始时间(秒)
        line_interval: 每句开始时间间隔(秒)
        slide_in_duration: 滑入动画持续时间(秒)
        hold_duration: 从第一句开始到淡出的总时间(秒)
        fade_out_duration: 淡出动画持续时间(秒)
        font_size: 字体大小
        font_name: 字体名称
        positions: 每行诗句的最终位置列表[(x1,y1),(x2,y2),...]
    """
    # 默认位置
    if positions is None:
        positions = []
        for i in range(len(poem_lines)):
            y = 1100 + i * 180
            x = 540
            positions.append((x, y))

    # 计算关键时间点
    last_slide_start = start_time + (len(poem_lines) - 1) * line_interval  # 最后一句开始时间 6.40
    last_slide_end = last_slide_start + slide_in_duration  # 最后一句滑入结束 7.40
    fade_out_start = start_time + hold_duration  # 淡出开始时间 10.00
    total_end = fade_out_start + fade_out_duration  # 完全结束时间 10.80

    # ASS文件头部
    header = f"""[Script Info]
Title: Poem Animation
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Poem,{font_name},{font_size},&H0000FFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,3,5,0,0,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # 时间格式化
    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(header)

        # 滑入动画层（持续到淡出开始）
        for i, (line, (x, y)) in enumerate(zip(poem_lines, positions)):
            line_start = start_time + i * line_interval
            line_end = fade_out_start  # 持续到淡出开始

            # 交替滑入方向
            if i % 2 == 0:
                start_x = -500
            else:
                start_x = 1580
            start_y = y

            # 滑入动画
            effect = f"{{\\move({start_x},{start_y},{x},{y})}}"
            f.write(f"Dialogue: 0,{format_time(line_start)},{format_time(line_end)},Poem,,0,0,0,,{effect}{line}\\N\n")

        # 淡出层（精确时间控制）
        for i, (line, (x, y)) in enumerate(zip(poem_lines, positions)):
            effect = f"{{\\pos({x},{y})\\fad(0,{int(fade_out_duration * 1000)})}}"
            f.write(
                f"Dialogue: 1,{format_time(fade_out_start)},{format_time(total_end)},Poem,,0,0,0,,{effect}{line}\\N\n")


# 竖直添加标题
def add_vertical_title_pro(
        text="早安中国",
        output_file="vertical_pro.ass",
        position=(800, 200),  # 文字块左上角坐标
        font_size=60,
        font_name="KaiTi",
        line_spacing=30,  # 行间距（实际是字间距）
        primary_color="&H00FFFFFF",
        outline_color="&H00000000",
        outline_width=5,
        start_time=0.0,
        duration=10.0
):
    """
    专业竖排实现（每个文字正立，整体竖排）
    参数：
        line_spacing: 实际控制字与字之间的垂直间距
    """
    # 计算结束时间    `
    end_time = start_time + duration

    # ASS文件头部
    header = f"""[Script Info]
Title: Professional Vertical Title
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: VerticalPro,{font_name},{font_size},{primary_color},,{outline_color},,0,0,0,0,100,100,0,0,1,{outline_width},0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(header)

        def format_time(seconds):
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = seconds % 60
            return f"{h}:{m:02d}:{s:05.2f}"

        # 计算每个字的位置（垂直排列）
        x_pos = position[0]
        y_positions = [position[1] + i * (font_size + line_spacing)
                       for i in range(len(text))]

        # 写入每个字单独的控制行
        for char, y_pos in zip(text, y_positions):
            effect = f"{{\\pos({x_pos},{y_pos})}}"
            dialogue_line = f"Dialogue: 0,{format_time(start_time)},{format_time(end_time)},VerticalPro,,0,0,0,,{effect}{char}\n"  # 注意末尾的\n
            f.write(dialogue_line)


# 将多个 ASS 字幕文件烧录到视频中
def burn_multiple_subtitles_to_video(input_video_path, ass_paths, output_video_path):
    """
    将多个 ASS 字幕文件烧录到视频中

    参数:
    - input_video_path: 输入视频文件路径
    - ass_paths: 包含多个 ASS 字幕文件路径的列表
    - output_video_path: 输出视频文件路径
    """
    if not ass_paths:
        print("没有提供字幕文件路径")
        return

    # 构建 ffmpeg 命令
    command = [
        'ffmpeg',
        '-y',  # 覆盖输出文件
        '-i', str(input_video_path),
    ]

    # 构建复杂的滤镜图
    filter_complex = []
    previous = "0:v"  # 初始为视频流
    for i, ass_path in enumerate(ass_paths):
        current_filter = f"[{previous}]subtitles='{ass_path}'"
        if i < len(ass_paths) - 1:
            current_filter += f"[v{i + 1}]"
            filter_complex.append(current_filter)
            previous = f"v{i + 1}"
        else:
            current_filter += f"[v]"
            filter_complex.append(current_filter)

    command.extend([
        '-filter_complex', ';'.join(filter_complex),
        '-map', '[v]',
        # '-map', '0:a',  # 映射音频流
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        # '-c:a', 'copy',  # 复制音频流，不重新编码
        str(output_video_path)
    ])

    # 执行命令
    try:
        os.system(" ".join(command))
        print(f"字幕已成功烧录到视频: {output_video_path}")
    except Exception as e:
        print(f"处理视频时出错: {e}")


# 早安视频生成的整个流程

def produce_morning_video_process(morning_date, pic_path, morning_text, out_path):
    # 第一步根据图片生成视频，视频默认时长10s

    # 缓存早安素材中间视频文件路径
    current_path = os.getcwd()

    tamp_path = os.path.join(current_path, 'tempConcateVideo')

    tamp_morning_video_path = os.path.join(tamp_path, 'video_morning_cache_file')

    if not os.path.exists(tamp_morning_video_path):
        os.makedirs(tamp_morning_video_path)
    else:
        shutil.rmtree(tamp_morning_video_path, ignore_errors=True)
        os.makedirs(tamp_morning_video_path)

    # 第一个缓存视频
    tamp_morning_video1 = os.path.join(tamp_morning_video_path, 'morning_video1.mp4')

    # 修复：正确调用异步函数
    import asyncio
    asyncio.run(image_to_video(pic_path, '10', tamp_morning_video1))

    # 第二步视频内添加各素材，例如烟花，鞭炮，灯笼等， 举例添加两个灯笼

    # 第二个缓存视频
    tamp_morning_video2 = os.path.join(tamp_morning_video_path, 'morning_video2.mp4')

    tamp_material_path = os.path.join(current_path, 'material')

    material1_path_dir = os.path.join(tamp_material_path, '灯笼')

    overlay_transparent_animation(
        background_video=tamp_morning_video1,
        material_path_dir=material1_path_dir,
        output_path=tamp_morning_video2,
        position=(-200, 50),
        size=(800, -1),  # 宽度300，高度等比缩放
        fps=30,
        crf=20
    )
    tamp_morning_video3 = os.path.join(tamp_morning_video_path, 'morning_video3.mp4')
    overlay_transparent_animation(
        background_video=tamp_morning_video2,
        material_path_dir=material1_path_dir,
        output_path=tamp_morning_video3,
        position=(500, 50),
        size=(800, -1),  # 宽度300，高度等比缩放
        fps=30,
        crf=20
    )
    material2_path_dir = os.path.join(tamp_material_path, '烟花')
    tamp_morning_video4 = os.path.join(tamp_morning_video_path, 'morning_video4.mp4')
    overlay_transparent_animation(
        background_video=tamp_morning_video3,
        material_path_dir=material2_path_dir,
        output_path=tamp_morning_video4,
        position=(-200, 500),
        size=(1200, -1),  # 宽度300，高度等比缩放
        fps=30,
        crf=20
    )

    # 第三步ai获取当日问候语，以及祝福语
    greetings_1 = deepseek_ai_greetings_1(morning_date)

    greetings_2 = deepseek_ai_greetings_2(morning_date)

    # 第四步生成日期、标题以及问候、祝福语 字幕特效文件

    # 扇形日期标题
    create_radial_title(morning_date, "radial_title.ass")

    # 竖直标题
    add_vertical_title_pro(
        text=morning_text,
        output_file='vertical_pro.ass',
        position=(850, 110),  # 右侧区域
        font_size=180,
        font_name="山海若诗楷 75W",
        primary_color="&H0000FFFF",  # 金色
        outline_width=3,
        line_spacing=6
    )

    # 第一遍出现的祝福语
    create_poem_ass(greetings_1,
                    output_file="poem1_final.ass",
                    start_time=0.0,
                    line_interval=0.5,
                    slide_in_duration=0.5,
                    hold_duration=2,  # 1.0 + (4-1)*1.8 + 1.0 + 2.6 = 10.0
                    fade_out_duration=3,
                    font_size=140,
                    font_name="三极行楷简体-粗")

    # 第二遍出现的祝福语
    process_poem(greetings_2, 120, "poem2_final.ass")

    ass_paths = ["radial_title.ass",  'vertical_pro.ass', 'poem1_final.ass', 'poem2_final.ass',]

    # 第五步将所有特效字幕文件添加至视频中
    burn_multiple_subtitles_to_video(tamp_morning_video4, ass_paths, out_path)

#
# produce_morning_video_process('20250708', 'xq.png', '早安上饶', 'zaoan.mp4')


# # 示例用法
# folder_path = r"D:\batchAiCutter\batchAiCutter\灯笼"  # 替换为你的文件夹路径
# start_index = 341  # 从 frame_0086.png 开始命名
#
# copy_and_rename_png_in_same_folder(folder_path, start_index)


# video_trans_to_pic_list('烟花.mp4', '烟花')
