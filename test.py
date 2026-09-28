# import subprocess
#
# def add_text_to_video(input_file, output_file, text, font_file, font_color, font_size, y, shadow_color, shadow_x,
#                       shadow_y, border_color, border_width, box_color, box_border_width):
#     """
#     在视频上添加带背景色和阴影的文本，并确保文本水平居中。
#
#     参数:
#     input_file (str): 输入视频文件路径。
#     output_file (str): 输出视频文件路径。
#     text (str): 要添加的文本。
#     font_file (str): 字体文件路径。
#     font_color (str): 字体颜色，例如 'yellow@0.8'。
#     font_size (int): 字体大小。
#     y (int): 文本的y坐标。
#     shadow_color (str): 阴影颜色，例如 'black@1'。
#     shadow_x (int): 阴影的x偏移量。
#     shadow_y (int): 阴影的y偏移量。
#     border_color (str): 边框颜色，例如 'yellow@0.8'。
#     border_width (int): 边框宽度。
#     box_color (str): 背景色，例如 'black@0.5'。
#     box_border_width (int): 背景框的边框宽度。
#     """
#     # 构建ffmpeg命令
#     command = [
#         'ffmpeg',
#         '-i', input_file,
#         '-vf', f'drawtext=fontfile={font_file}:text={text}:fontcolor={font_color}:fontsize={font_size}:' +
#                f'x=(w-text_w)/2:y={y}:' +
#                f'shadowcolor={shadow_color}:shadowx={shadow_x}:shadowy={shadow_y}:bordercolor={border_color}:' +
#                f'borderw={border_width}:box=1:boxcolor={box_color}:boxborderw={box_border_width}',
#         output_file
#     ]
#
#     # 执行ffmpeg命令
#     subprocess.run(command, check=True)
#
#
# # 示例用法
# input_video = 'test_preview_video0.mp4'
# output_video = 'output123.mp4'
# text_to_add = '中国绝美风景排行盘点'
# font_file_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'  # 请根据你的系统调整字体文件路径
#
# add_text_to_video(
#     input_file=input_video,
#     output_file=output_video,
#     text=text_to_add,
#     font_file=font_file_path,
#     font_color='white@1',
#     font_size=100,
#     y=200,
#     shadow_color='black@0.1',
#     shadow_x=2,
#     shadow_y=2,
#     border_color='black@1',
#     border_width=5,
#     box_color='yellow@1',  # 背景色为半透明黑色
#     box_border_width=20
# )


# import subprocess
# import textwrap
#
# def add_text_to_video(input_file, output_file, text, font_file, font_color, font_size, y, shadow_color, shadow_x,
#                       shadow_y, border_color, border_width, box_color, box_border_width, max_width):
#     """
#     在视频上添加带背景色和阴影的文本，并确保文本水平居中。如果文本超出指定宽度，则自动换行。
#
#     参数:
#     input_file (str): 输入视频文件路径。
#     output_file (str): 输出视频文件路径。
#     text (str): 要添加的文本。
#     font_file (str): 字体文件路径。
#     font_color (str): 字体颜色，例如 'yellow@0.8'。
#     font_size (int): 字体大小。
#     y (int): 文本的y坐标。
#     shadow_color (str): 阴影颜色，例如 'black@1'。
#     shadow_x (int): 阴影的x偏移量。
#     shadow_y (int): 阴影的y偏移量。
#     border_color (str): 边框颜色，例如 'yellow@0.8'。
#     border_width (int): 边框宽度。
#     box_color (str): 背景色，例如 'black@0.5'。
#     box_border_width (int): 背景框的边框宽度。
#     max_width (int): 文本的最大宽度（以字符数为单位）。
#     """
#     # 自动换行文本
#     wrapped_text = textwrap.fill(text, width=max_width)
#
#     # 构建ffmpeg命令
#     command = [
#         'ffmpeg',
#         '-i', input_file,
#         '-vf', f'drawtext=fontfile={font_file}:text={wrapped_text}:fontcolor={font_color}:fontsize={font_size}:' +
#                f'x=(w-text_w)/2:y={y}:' +
#                f'shadowcolor={shadow_color}:shadowx={shadow_x}:shadowy={shadow_y}:bordercolor={border_color}:' +
#                f'borderw={border_width}:box=1:boxcolor={box_color}:boxborderw={box_border_width}',
#         output_file
#     ]
#
#     # 执行ffmpeg命令
#     subprocess.run(command, check=True)
#
#
# # 示例用法
# input_video = 'test_preview_video0.mp4'
# output_video = 'output123.mp4'
# text_to_add = '中国绝美风景排行盘点，这些地方你去过几个？'
# font_file_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'  # 请根据你的系统调整字体文件路径
#
# add_text_to_video(
#     input_file=input_video,
#     output_file=output_video,
#     text=text_to_add,
#     font_file=font_file_path,
#     font_color='white@1',
#     font_size=100,
#     y=200,
#     shadow_color='black@0.1',
#     shadow_x=2,
#     shadow_y=2,
#     border_color='black@1',
#     border_width=5,
#     box_color='yellow@1',  # 背景色为半透明黄色
#     box_border_width=20,
#     max_width=10  # 每行最多20个字符
# )


# import subprocess
#
# import jieba
#
# def segment_title(title: str, width: int = 7) -> str:
#     """
#     按词语折行，字不会拆散
#     :param title: 原始标题
#     :param width: 每行最多容纳的字符数（汉字算 1）
#     :return: 已分段字符串，每行用换行符分隔
#     """
#     words = jieba.lcut(title)  # 先切成词语
#     lines, cur = [], ''
#     for w in words:
#         # 如果当前行放不下，就换行
#         if cur and (len(cur) + len(w)) > width:
#             lines.append(cur.strip())
#             cur = w
#         else:
#             cur += w
#     if cur:
#         lines.append(cur)
#     print('\n'.join(lines))
#     return '\n'.join(lines)
#
# def add_text_to_video(input_file, output_file, text, font_file, font_color, font_size, y, shadow_color, shadow_x,
#                       shadow_y, border_color, border_width, box_color, box_border_width, max_width):
#     """
#     在视频上添加带背景色和阴影的文本，并确保每行文本水平居中。如果文本超出指定宽度，则自动换行。
#
#     参数:
#     input_file (str): 输入视频文件路径。
#     output_file (str): 输出视频文件路径。
#     text (str): 要添加的文本。
#     font_file (str): 字体文件路径。
#     font_color (str): 字体颜色，例如 'yellow@0.8'。
#     font_size (int): 字体大小。
#     y (int): 文本的y坐标。
#     shadow_color (str): 阴影颜色，例如 'black@1'。
#     shadow_x (int): 阴影的x偏移量。
#     shadow_y (int): 阴影的y偏移量。
#     border_color (str): 边框颜色，例如 'yellow@0.8'。
#     border_width (int): 边框宽度。
#     box_color (str): 背景色，例如 'black@0.5'。
#     box_border_width (int): 背景框的边框宽度。
#     max_width (int): 文本的最大宽度（以字符数为单位）。
#     """
#     # 自动换行文本
#     wrapped_text = segment_title(text, width=max_width)
#
#     # 构建ffmpeg命令
#     command = [
#         'ffmpeg',
#         '-i', input_file,
#         '-vf', f"""
#         drawtext=fontfile={font_file}:text='{wrapped_text}':fontcolor={font_color}:fontsize={font_size}:
#         x=(w-text_w)/2:y={y}:
#         shadowcolor={shadow_color}:shadowx={shadow_x}:shadowy={shadow_y}:bordercolor={border_color}:
#         borderw={border_width}:box=1:boxcolor={box_color}:boxborderw={box_border_width}
#         """,
#         output_file
#     ]
#
#     # 执行ffmpeg命令
#     subprocess.run(command, check=True)
#
#
# # 示例用法
# input_video = 'test_preview_video0.mp4'
# output_video = 'output123.mp4'
# text_to_add = '中国绝美风景排行盘点 看看你到过几个'
# font_file_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'  # 请根据你的系统调整字体文件路径
#
# add_text_to_video(
#     input_file=input_video,
#     output_file=output_video,
#     text=text_to_add,
#     font_file=font_file_path,
#     font_color='white@1',
#     font_size=60,
#     y=200,
#     shadow_color='black@0.1',
#     shadow_x=2,
#     shadow_y=2,
#     border_color='black@1',
#     border_width=5,
#     box_color='yellow@1',  # 背景色为半透明黄色
#     box_border_width=40,
#     max_width=10  # 每行最多20个字符
# )

# from pydub import AudioSegment
#
#
# def generate_silence(duration):
#     silence = AudioSegment.silent(duration)
#     return silence
#
#
# def save_as_mp3(audio, filename):
#     audio.export(filename, format='mp3')
#
#
# if __name__ == '__main__':
#     duration = 6000
#     silence = generate_silence(duration)
#     save_as_mp3(silence, 'blank.mp3')


import subprocess
import os
from typing import Tuple

from ffmpeg_tool.pic_trans_to_video import overlay_transparent_animation


import os
import subprocess
from typing import Tuple


# 黑色背景素材视频转为图片png序列
def video_trans_to_pic_list(video_path, material_file_name):
    # 临时目录存放PNG序列
    current_path = os.getcwd()

    # 存放素材的文件夹

    material_origin_file_path = os.path.join(current_path, 'material')

    material_file_path = os.path.join(material_origin_file_path, material_file_name)

    if not os.path.exists(video_path):
        return

    try:
        # 阶段1：黑底视频转透明PNG序列
        cmd1 = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f"colorkey=0x009d04:0.1:0.1,format=rgba",
            '-compression_level', '6',
            os.path.join(material_file_path, 'frame_%04d.png')
        ]
        subprocess.run(cmd1, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        print('素材视频转图片以完成')
    except Exception as e:
        print('素材视频转图片序列失败：' + str(e))


current_path = os.getcwd()

tamp_material_path = os.path.join(current_path, 'material')

material1_path_dir = os.path.join(tamp_material_path, '花2')

print(material1_path_dir)
if not os.path.exists(material1_path_dir):
    exit()

# material1_path_dir = material1_path_dir.replace('\\\\', '\\')
overlay_transparent_animation(
    background_video='123.mp4',
    material_path_dir=material1_path_dir,
    output_path='321.mp4',
    position=(0, 0),
    fps=30,
    crf=20
)
