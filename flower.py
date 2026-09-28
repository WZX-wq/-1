# 花开富贵视频批量合成脚本
import asyncio
import json
import os
import random
import subprocess
import time

from ffmpeg_tool.add_music_tool import add_bgm_to_video
from ffmpeg_tool.pic_trans_to_video import overlay_transparent_animation
from worker.composite_word_intro_video_worker import imgToVideo, addAss


def read_dict_from_txt(file_path):
    """从文本文件读取字典，如果文件不存在则创建一个空文件"""
    try:
        # 标题
        title_set_dict = {
            'fontFamily': 'SimHei',  # 字体
            'fontBorderSize': 1,  # 边框大小
            'shadowDepth': 0,  # 阴影大小
            'fontBold': 0,  # 粗体
            'fontColor': '#FFFFFF',  # 字体颜色
            'fontSize': 12,  # 字体大小
            'fontItalic': 0,  # 斜体
            'borderColor': '#000000',  # 边框颜色
            'fontScroll': 0,  # 特效
            'fontUnderline': 0,  # 下划线
            'shadowColor': '#000000',  # 阴影颜色
            'titleTime': 3,  # 标题时间
            'titleLineSpace': 1,  # 行间距
            'titleSpace': 10,  # 位置调整
            'position': 0,
        }

        # 小标题
        part_title_set_dict = {
            'fontFamily': 'SimHei',  # 字体
            'fontBorderSize': 1,  # 边框大小
            'shadowDepth': 0,  # 阴影大小
            'fontBold': 0,  # 粗体
            'fontColor': '#FFFFFF',  # 字体颜色
            'fontSize': 12,  # 字体大小
            'fontItalic': 0,  # 斜体
            'borderColor': '#000000',  # 边框颜色
            'fontScroll': 0,  # 特效
            'fontUnderline': 0,  # 下划线
            'shadowColor': '#000000',  # 阴影颜色
            'titleTime': 3,  # 标题时间
            'titleLineSpace': 1,  # 行间距
            'titleSpace': 10,  # 位置调整
            'position': 0,
            'x': 0,
            'y': 0,
        }

        part_title_part_0_set_dict = {
            'fontBorderSize': 1,  # 边框大小
            'fontColor': '#ffff00',  # 字体颜色
            'borderColor': '#000000',
            'fontSize': 16,  # 字体大小
            'fontScroll': 0,  # 特效
            'VSpace': 1,  # 行间距
            'align': 0,  # 对齐
            'x': 0,
            'y': 0
        }

        part_title_part_1_set_dict = {
            'fontBorderSize': 1,  # 边框大小
            'fontColor': '#ffff00',  # 字体颜色
            'borderColor': '#000000',
            'fontSize': 16,  # 字体大小
            'fontScroll': 0,  # 特效
            'VSpace': 1,  # 行间距
            'align': 0,  # 对齐
            'x': 0,
            'y': 0
        }

        part_title_part_2_set_dict = {
            'fontBorderSize': 1,  # 边框大小
            'fontColor': '#ffff00',  # 字体颜色
            'borderColor': '#000000',
            'fontSize': 16,  # 字体大小
            'fontScroll': 0,  # 特效
            'VSpace': 1,  # 行间距
            'align': 0,  # 对齐
            'x': 0,
            'y': 0
        }

        part_title_part_3_set_dict = {
            'fontBorderSize': 1,  # 边框大小
            'fontColor': '#ffff00',  # 字体颜色
            'borderColor': '#000000',
            'fontSize': 16,  # 字体大小
            'fontScroll': 0,  # 特效
            'VSpace': 1,  # 行间距
            'align': 0,  # 对齐
            'x': 0,
            'y': 0
        }

        part_title_part_4_set_dict = {
            'fontBorderSize': 1,  # 边框大小
            'fontColor': '#ffff00',  # 字体颜色
            'borderColor': '#000000',
            'fontSize': 16,  # 字体大小
            'fontScroll': 0,  # 特效
            'VSpace': 1,  # 行间距
            'align': 0,  # 对齐
            'x': 0,
            'y': 0
        }

        part_title_part_5_set_dict = {
            'fontBorderSize': 1,  # 边框大小
            'fontColor': '#ffff00',  # 字体颜色
            'borderColor': '#000000',
            'fontSize': 16,  # 字体大小
            'fontScroll': 0,  # 特效
            'VSpace': 1,  # 行间距
            'align': 0,  # 对齐
            'x': 0,
            'y': 0
        }

        # 字幕
        srt_set_dict = {
            'fontFamily': 'SimHei',  # 字体
            'fontBorderSize': 1,  # 边框大小
            'shadowDepth': 0,  # 阴影大小
            'fontBold': 0,  # 粗体
            'fontColor': '#FFFFFF',  # 字体颜色
            'fontSize': 12,  # 字体大小
            'fontItalic': 0,  # 斜体
            'borderColor': '#000000',  # 边框颜色
            'fontScroll': 0,  # 特效
            'fontUnderline': 0,  # 下划线
            'shadowColor': '#000000',  # 阴影颜色
            'titleTime': 3,  # 标题时间
            'titleLineSpace': 1,  # 行间距
            'titleSpace': 10,  # 位置调整
        }

        # 配音
        voice_set_dict = {
            'api_type': 0,
            'role_0': 0,
            'pit_0': 0,
            'spd_0': 0,
            'vol_0': 0,
            'role_1': 0,
            'pit_1': 5,
            'spd_1': 5,
            'vol_1': 5,
        }

        # 水印
        water_set_dict = {
            'filePath': '',
            'position': 0,
            'zoom': 1.0,
            'alpha': 1.0
        }

        title_type_dict = {
            'type': 0
        }
        video_type_dict = {
            'type': 0
        }

        all_dict = {
            'video_type': video_type_dict,
            'title_type': title_type_dict,
            'title_set': title_set_dict,
            'part_title_set': part_title_set_dict,
            'srt_set': srt_set_dict,
            'voice_set': voice_set_dict,
            'water_set': water_set_dict,
            'end_video': '',
            'account_location': '',
            'part_title_part_0_set': part_title_part_0_set_dict,
            'part_title_part_1_set': part_title_part_1_set_dict,
            'part_title_part_2_set': part_title_part_2_set_dict,
            'part_title_part_3_set': part_title_part_3_set_dict,
            'part_title_part_4_set': part_title_part_4_set_dict,
            'part_title_part_5_set': part_title_part_5_set_dict,
        }

        if not os.path.exists(file_path):
            # 如果文件不存在，创建一个空文件
            open(file_path, 'w', encoding='utf-8').close()
            print(f"文件已创建: {file_path}")
            return all_dict

        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            if not content:
                print(f"文件内容为空: {file_path}")
                try:
                    # 使用 'w' 模式打开文件，自动清空文件内容
                    with open(file_path, 'w', encoding='utf-8') as file:
                        json.dump(all_dict, file, ensure_ascii=False, indent=4)
                    print(f"字典已成功写入文件: {file_path}")
                    return all_dict
                except Exception as e:
                    print(f"写入字典时出错: {e}")
                    return {}

        with open(file_path, 'r', encoding='utf-8') as file:
            dictionary = json.load(file)
        print(f"字典已成功从文件读取: {file_path}")
        return dictionary
    except json.JSONDecodeError:
        print(f"文件内容不是有效的 JSON 格式: {file_path}")
        return {}
    except Exception as e:
        print(f"读取字典时出错: {e}")
        return {}


# 创建标题ass头部文本
def file_create_title_ass_header(ass_header_dict):
    """创建ASS文件头部"""
    font_name = ass_header_dict['fontFamily']
    font_size = ass_header_dict['fontSize']

    primary_color_ass = convert_to_ass_color(ass_header_dict['fontColor'])

    border_color_ass = convert_to_ass_color(ass_header_dict['borderColor'])

    shadow_color_ass = convert_to_ass_color(ass_header_dict['shadowColor'])

    # 获取样式
    bold = ass_header_dict['fontBold']
    italic = ass_header_dict['fontItalic']
    underline = ass_header_dict['fontUnderline']

    borderSize = ass_header_dict['fontBorderSize']
    shadowDepth = ass_header_dict['shadowDepth']
    align_value = 2
    MarginV = ass_header_dict['titleSpace']
    titleLineSpace = ass_header_dict['titleLineSpace']

    header = f"""[Script Info]
        Title: Default Aegisub file
        ScriptType: v4.00+
        WrapStyle: 0
        ScaledBorderAndShadow: yes
        YCbCr Matrix: None

        [V4+ Styles] Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
        Style: Default,{font_name},{font_size},{primary_color_ass},{primary_color_ass},{border_color_ass},{shadow_color_ass},{bold},{italic},{underline},0,100,100,{titleLineSpace},0,1,{borderSize},{shadowDepth},{align_value},10,10,{MarginV},65001  # 注意参数顺序和数量
        Style: VerticalPro,@{font_name},{font_size},{primary_color_ass},{primary_color_ass},{border_color_ass},{shadow_color_ass},{bold},{italic},{underline},0,100,100,{titleLineSpace},0,1,{borderSize},{shadowDepth},{align_value},10,10,{MarginV},65001
        [Events]
        Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        """
    return header


def convert_to_ass_color(hex_color):
    """
    将 RGB 十六进制颜色代码转换为 ASS 字幕格式的颜色代码。

    参数:
        hex_color (str): RGB 颜色代码，如 '#FF0000' 或 'FF0000'

    返回:
        str: ASS 格式的颜色代码，如 '&H0000FF'
    """
    # 移除可能存在的 '#' 前缀
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]

    # 确保颜色代码长度正确
    if len(hex_color) != 6:
        raise ValueError("颜色代码必须是6个字符的十六进制值（不包括'#'）")

    # 提取 R、G、B 分量
    r = hex_color[0:2]
    g = hex_color[2:4]
    b = hex_color[4:6]

    # 按 BGR 顺序重新组合，并添加 ASS 前缀 '&H'
    return f'&H{b}{g}{r}'


def get_random_ass_color():
    # 生成柔和随机色（限制亮度范围避免刺眼）
    r = random.randint(80, 220)
    g = random.randint(80, 220)
    b = random.randint(80, 220)
    return f"&H{b:02X}{g:02X}{r:02X}&"  # 修正：补充闭合引号


# # 渐变
# def file_word_infor_title_apply_effects_to_text(title_part_text, pos_x, pos_y):
#     cycle = 2500  # 单个周期总时长
#     segments = 4  # 每个周期分4段过渡（插入2个中间色）
#     step_time = cycle // segments  # 每段过渡时间：2500/4=625ms
#     ass_code = f"{{\\fs15\\an2\\pos({pos_x},{pos_y})\\Y1"
#     # 生成4个周期的平滑渐变
#     for cycle_idx in range(4):
#         # 每个周期生成5个随机色（含首尾）
#         colors = [get_random_ass_color() for _ in range(segments + 1)]
#         # 生成该周期内的多段渐变
#         for seg_idx in range(segments):
#             start_t = cycle_idx * cycle + seg_idx * step_time
#             end_t = cycle_idx * cycle + (seg_idx + 1) * step_time
#             ass_code += f"\\t({start_t},{end_t},\\c{colors[seg_idx + 1]})"
#     ass_code += f"}} {title_part_text}\\N"
#     return ass_code

#
# def get_random_ass_color():
#     """生成随机的ASS颜色代码"""
#     return f"&H{random.randint(0, 255):02X}{random.randint(0, 255):02X}{random.randint(0, 255):02X}"


def get_rainbow_colors():
    """生成彩虹色序列"""
    return [
        "&H0000FF",  # 蓝色
        "&H00FFFF",  # 青色
        "&H00FF00",  # 绿色
        "&HFFFF00",  # 黄色
        "&HFF0000",  # 红色
        "&HFF00FF",  # 紫色
        "&H0000FF"  # 蓝色（回到起点）
    ]


def file_word_infor_title_apply_effects_to_text(title_part_text, pos_x, pos_y):
    cycle = 2500  # 单个周期总时长
    segments = 6  # 每个周期分6段过渡（插入4个中间色）
    step_time = cycle // segments  # 每段过渡时间：2500/6≈416ms
    ass_code = f"{{\\fs20\\an2\\pos({pos_x},{pos_y})\\Y1"

    # 生成4个周期的平滑渐变
    for cycle_idx in range(4):
        # 每个周期使用彩虹色序列
        colors = get_rainbow_colors()
        # 生成该周期内的多段渐变
        for seg_idx in range(segments):
            start_t = cycle_idx * cycle + seg_idx * step_time
            end_t = cycle_idx * cycle + (seg_idx + 1) * step_time
            ass_code += f"\\t({start_t},{end_t},\\c{colors[seg_idx % len(colors)]})"

    # # 添加缩放动画
    # for cycle_idx in range(4):
    #     start_t = cycle_idx * cycle
    #     end_t = (cycle_idx + 1) * cycle
    #     ass_code += f"\\t({start_t},{end_t},\\fscx100\\fscy100)"
    #     ass_code += f"\\t({start_t},{start_t + cycle // 2},\\fscx150\\fscy150)"
    #     ass_code += f"\\t({start_t + cycle // 2},{end_t},\\fscx100\\fscy100)"

    ass_code += f"}} {title_part_text}\\N"
    return ass_code


def sec_to_ass(t: float) -> str:
    """把秒数转成 hh:mm:ss.cc 格式的 ASS 时间字符串"""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    c = int((t % 1) * 100)  # 百分秒
    return f"{h:d}:{m:02d}:{s:02d}.{c:02d}"


# 选取背景素材
def random_image_path(folder_path):
    """
    从指定文件夹中随机抽取一个图片文件，并返回它的路径。

    参数:
        folder_path (str): 图片文件所在的文件夹路径。

    返回:
        str: 随机抽取的图片文件的路径，如果没有图片文件则返回None。
    """
    # 支持的图片文件扩展名
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']

    # 获取文件夹中的所有文件
    files = os.listdir(folder_path)

    # 筛选出图片文件
    image_files = [file for file in files if os.path.splitext(file)[1].lower() in image_extensions]

    if not image_files:
        print("文件夹中没有找到图片文件。")
        return None

    # 随机选择一个图片文件
    random_image = random.choice(image_files)

    # 返回图片文件的完整路径
    return os.path.join(folder_path, random_image)


def get_random_gif_from_folder(folder_path):
    """
    从指定文件夹中随机选择一个 GIF 图片。

    :param folder_path: 包含 GIF 图片的文件夹路径
    :return: 随机选择的 GIF 图片的完整路径
    """
    # 获取文件夹中的所有文件
    files = os.listdir(folder_path)

    # 筛选出所有 GIF 文件
    gif_files = [file for file in files if file.lower().endswith('.gif')]

    # 如果没有找到 GIF 文件，返回 None
    if not gif_files:
        print("没有找到 GIF 文件。")
        return None

    # 随机选择一个 GIF 文件
    random_gif = random.choice(gif_files)

    # 返回随机选择的 GIF 文件的完整路径
    return os.path.join(folder_path, random_gif)


def add_gif_to_video(input_video, gif_path, output_video, gif_size, position):
    """
    将 GIF 添加到视频中，并控制大小和位置。

    :param input_video: 输入视频文件路径
    :param gif_path: GIF 文件路径
    :param output_video: 输出视频文件路径
    :param gif_size: GIF 的大小，格式为 "宽:高"，例如 "300:300"
    :param position: GIF 的位置，格式为 "x:y"，例如 "100:100"
    """
    # 构建 FFmpeg 命令
    ffmpeg_command = [
        'ffmpeg',
        '-i', input_video,
        '-ignore_loop', '0',  # GIF 循环播放
        '-i', gif_path,
        '-filter_complex',
        f'[1:v]scale={gif_size}[wm];[0:v][wm]overlay={position}:shortest=1',
        '-c:v', 'libx264',
        '-c:a', 'copy',
        output_video
    ]

    # 使用 subprocess 调用 FFmpeg 命令
    try:
        subprocess.run(ffmpeg_command, check=True)
        print(f'GIF 已成功添加到视频中，输出文件为：{output_video}')
    except subprocess.CalledProcessError as e:
        print(f'发生错误：{e}')


if __name__ == '__main__':
    # 运行次数
    while True:
        try:
            run_num = int(input('请输入需要合成的次数：'))  # 将输入转换为整数
            if run_num < 0:
                print("请输入一个非负整数！")
            else:
                break  # 如果输入有效，跳出循环
        except ValueError:
            print("输入无效，请输入一个整数！")

    model_txt_path = 'setting.txt'
    model_set_dict = read_dict_from_txt(model_txt_path)
    ass_header = file_create_title_ass_header(model_set_dict['title_set'])

    # 使用 for 循环迭代范围
    for i in range(run_num):
        print(f"当前视频合成次数：第{i + 1}次")

        # 选取背景素材 文件夹中随机获取
        current_path = os.getcwd()
        # 随机图片文件夹路径
        pic_list_file_path = os.path.join(current_path, 'touristPictures')
        pic_file_path = random_image_path(pic_list_file_path)

        # 图片生成视频
        timestamp = int(time.time() * 1000)  # 当前时间戳，毫秒级
        pic_video_path = f'pic1_{timestamp}.mp4'
        pic_flower_video_path = f'pic2_{timestamp}.mp4'
        pic_flower_gif_video_path = f'pic3_{timestamp}.mp4'
        pic_flower_gif_srt_video_path = f'pic4_{timestamp}.mp4'
        final_video_path = f'final_{timestamp}.mp4'

        asyncio.run(imgToVideo(pic_file_path, 8, pic_video_path))
        # 随机全屏素材
        tamp_material_path = os.path.join(current_path, 'material')
        random_num = random.randint(0, 11)
        folder_path = f'花{random_num}'
        material1_path_dir = os.path.join(tamp_material_path, folder_path)
        overlay_transparent_animation(
            background_video=pic_video_path,
            material_path_dir=material1_path_dir,
            output_path=pic_flower_video_path,
            position=(0, 0),
            fps=30,
            crf=20,
            size=(1080, -1),  # 宽度300，高度等比缩放
        )

        # 随机点缀素材
        tamp_gif_material_path = os.path.join(current_path, 'gifMaterial')
        gif_file_path = get_random_gif_from_folder(tamp_gif_material_path)
        add_gif_to_video(pic_flower_video_path, gif_file_path, pic_flower_gif_video_path, '400:400', '700:100')

        # 文案
        text_list = ['祝您', '身体倍儿棒', '好运滚滚来', '钱包鼓鼓的', '一生平安顺遂', '富贵无忧']
        ass_content = ''
        out_title_ass_path = r'flowerTitle.ass'
        pos_x = 190
        pos_y = 60
        for text in text_list:
            # 文案添加
            start_time = 0
            end_time = 8
            text = file_word_infor_title_apply_effects_to_text(text, pos_x, pos_y)
            ass_events = f"Dialogue: 0,{sec_to_ass(start_time)},{sec_to_ass(end_time)},Default,,0,0,0,,{text}" + '\n'
            ass_content += ass_header + "\n" + ass_events
            pos_y += 30

        with open(out_title_ass_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        asyncio.run(addAss(out_title_ass_path, pic_flower_gif_video_path, pic_flower_gif_srt_video_path))

        # # 添加音乐
        # add_bgm_to_video(pic_flower_gif_srt_video_path, music_path, 100, 40, final_video_path)

        if os.path.exists(pic_video_path):
            os.remove(pic_video_path)

        if os.path.exists(pic_flower_video_path):
            os.remove(pic_flower_video_path)

        if os.path.exists(pic_flower_gif_video_path):
            os.remove(pic_flower_gif_video_path)

        # if os.path.exists(pic_flower_gif_srt_video_path):
        #     os.remove(pic_flower_gif_srt_video_path)