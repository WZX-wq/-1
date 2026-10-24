# 添加水印
import os
import subprocess
import sys
from PIL import Image, ImageOps
from pathlib import Path


def resolve_watermark_path(configured_path):
    """Find the same watermark after moving a portable installation."""
    configured_path = str(configured_path or '').strip()
    if not configured_path:
        return None
    path = Path(configured_path)
    if path.is_file():
        return str(path.resolve())
    roots = [Path.cwd(), Path(__file__).resolve().parent.parent]
    if getattr(sys, 'frozen', False):
        roots.insert(0, Path(sys.executable).resolve().parent)
    if getattr(sys, '_MEIPASS', ''):
        roots.append(Path(sys._MEIPASS))
    for root in roots:
        for folder in ('', 'watermarks', 'soft_pic'):
            candidate = root / folder / path.name
            if candidate.is_file():
                return str(candidate.resolve())
    return None


def _decode_process_output(value):
    """Decode optional subprocess output without masking the FFmpeg error."""
    if value is None:
        return ''
    if isinstance(value, bytes):
        return value.decode(sys.getdefaultencoding(), errors='replace')
    return str(value)


# 添加文字水印
def add_text_watermark(video_path, output_path, watermark_setting):
    text = watermark_setting['watermark_text']
    font_size = watermark_setting['font_size']
    x_position = watermark_setting['watermark_location'][0]
    y_position = watermark_setting['watermark_location'][1]
    font_color = watermark_setting['font_color']
    shadow_color = watermark_setting['shadow_color']
    shadow_x = watermark_setting['shadow_direction'][0]
    shadow_y = watermark_setting['shadow_direction'][1]
    alpha = watermark_setting['font_alpha']
    font_text = watermark_setting['font_selection']
    # Windows字体路径（使用双反斜杠）
    font_file = f'C:\\Windows\\Fonts\\{font_text}'

    # 检查字体文件是否存在
    if not os.path.exists(font_file):
        raise FileNotFoundError(f"水印字体不存在，请重新选择字体：{font_file}")

    # 转义字体路径和文本内容
    escaped_font_file = escape_filter_arg(font_file)
    escaped_text = escape_filter_arg(text)

    # 构造drawtext滤镜参数（关键修改点）
    drawtext_filter = (
        f'drawtext=fontfile=\'{escaped_font_file}\':'
        f'text=\'{escaped_text}\':'
        f'fontsize={font_size}:'
        f'x={x_position}:y={y_position}:'
        f'fontcolor={font_color}:'
        f'shadowcolor={shadow_color}:'
        f'shadowx={shadow_x}:shadowy={shadow_y}:'
        f'alpha={alpha}'
    )

    # 构造FFmpeg命令（性能优化版本）
    command = [
        'ffmpeg', '-y',
        '-i', video_path,
        # 性能优化参数
        '-threads', '4',  # 限制线程数，避免资源竞争
        '-preset', 'faster',  # 速度优化的预设
        '-tune', 'fastdecode',  # 优化解码速度
        '-vf', drawtext_filter,
        '-c:v', 'libx264',  # 明确指定视频编码器
        '-crf', '23',  # 平衡质量和速度
        '-c:a', 'copy',  # 音频流直接复制
        '-movflags', '+faststart',  # 优化MP4播放
        output_path
    ]

    print("执行的命令:", " ".join(command))  # 打印完整命令用于调试

    try:
        # 执行命令，禁用text模式以避免编码问题
        process = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        # 手动解码输出，使用系统默认编码
        stdout = _decode_process_output(process.stdout)
        stderr = _decode_process_output(process.stderr)

        print("标准输出:", stdout)
        print("错误输出:", stderr)
        print("文字水印添加成功！")

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg执行失败 (返回码: {e.returncode})")
        # 手动解码错误输出
        stderr = _decode_process_output(e.stderr)
        print("错误详情:", stderr)
        raise RuntimeError(f"FFmpeg文字水印失败（返回码 {e.returncode}）：{stderr[-1000:]}") from e
    except FileNotFoundError as e:
        raise RuntimeError('未找到软件自带的FFmpeg，请完整解压软件目录') from e


# 添加图片水印
def add_pic_watermark(video_path, pic_path, output_path, watermark_setting):
    resolved_pic = resolve_watermark_path(pic_path)
    if not resolved_pic:
        raise FileNotFoundError(f'水印图片不存在，请在设置中重新选择：{pic_path or "未设置"}')
    pic_path = resolved_pic
    # 控制水印的位置、大小等参数
    x_offset = watermark_setting['watermark_location'][0]  # 水印距离视频左边缘的偏移量
    y_offset = watermark_setting['watermark_location'][1]  # 水印距离视频上边缘的偏移量
    scale_size = watermark_setting['zoom_size']  # 水印图片的缩放比例
    alpha = watermark_setting['pic_alpha']  # 水印的透明度（0.0 完全透明，1.0 完全不透明）

    # 构造 FFmpeg 命令，给视频添加水印并控制水印参数（性能优化版本）
    command = [
        'ffmpeg', '-y',
        '-i', video_path,  # 输入视频
        '-i', pic_path,  # 输入水印
        # 性能优化参数
        '-threads', '4',  # 限制线程数
        '-preset', 'faster',  # 速度优化预设
        '-tune', 'fastdecode',  # 优化解码速度
        '-filter_complex',  # 使用复杂的滤镜
        f'[1:v]scale=iw*{scale_size}:ih*{scale_size},format=argb,colorchannelmixer=aa={alpha}[watermark];'
        f'[0:v][watermark]overlay={x_offset}:{y_offset}:format=auto,format=yuv420p',
        '-c:v', 'libx264',  # 明确指定视频编码器
        '-crf', '23',  # 平衡质量和速度
        '-c:a', 'copy',  # 音频流直接复制，不重新编码
        '-movflags', '+faststart',  # 优化 MP4 文件播放
        output_path  # 输出文件
    ]
    try:
        # 执行 FFmpeg 命令
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg执行失败 (返回码: {e.returncode})")
        # 手动解码错误输出
        stderr = _decode_process_output(e.stderr)
        print("错误详情:", stderr)
        raise RuntimeError(f"FFmpeg图片水印失败（返回码 {e.returncode}）：{stderr[-1000:]}") from e
    except FileNotFoundError as e:
        raise RuntimeError('未找到软件自带的FFmpeg，请完整解压软件目录') from e


# 手动转义滤镜参数中的特殊字符
def escape_filter_arg(arg):
    # 转义特殊字符: , ; [ ] =
    arg = arg.replace('\\', '\\\\')  # 先转义反斜杠
    arg = arg.replace(':', '\\:')  # 转义冒号
    arg = arg.replace('"', '\\"')  # 转义双引号
    arg = arg.replace("'", "\\'")  # 转义单引号
    return arg


def add_watermark(input_image_path, watermark_image_path, output_image_path, position, size=None, opacity=255):
    """
    将一张图片作为水印添加到另一张图片上
    :param input_image_path: 输入图片的路径
    :param watermark_image_path: 水印图片的路径
    :param output_image_path: 输出图片的路径
    :param position: 水印图片的位置 (x, y)
    :param size: 水印图片的大小 (width, height)，如果为 None，则保持原始大小
    :param opacity: 水印图片的透明度 (0-255，0 完全透明，255 完全不透明)
    """
    # 打开输入图片和水印图片
    input_image = Image.open(input_image_path)
    watermark_image = Image.open(watermark_image_path)

    # 图文视频使用竖屏画布；缓存缩略图不应决定最终视频分辨率。
    if input_image.size != (1080, 1920):
        input_image = ImageOps.fit(
            input_image.convert("RGB"), (1080, 1920), method=Image.Resampling.LANCZOS)

    # 如果指定了大小，则调整水印图片的大小
    if size:
        watermark_image = watermark_image.resize(size, Image.Resampling.LANCZOS)

    # 将水印图片转换为 RGBA 模式
    watermark_image = watermark_image.convert("RGBA")

    # 创建一个与输入图片同样大小的透明图层
    transparent_layer = Image.new("RGBA", input_image.size, (0, 0, 0, 0))

    # 将水印图片粘贴到透明图层的指定位置
    transparent_layer.paste(watermark_image, position, watermark_image)

    # 调整水印图片的透明度
    datas = transparent_layer.getdata()
    newData = []
    for item in datas:
        newData.append((item[0], item[1], item[2], int(item[3] * opacity / 255)))
    transparent_layer.putdata(newData)

    # 将透明图层与输入图片进行合成
    composite_image = Image.alpha_composite(input_image.convert("RGBA"), transparent_layer)

    # 保存图片
    composite_image.convert("RGB").save(output_image_path)



# 添加图片到视频
def add_image_to_video(input_video, output_video, image_path, position, size, opacity, duration):
    """
    给视频添加图片，并调整图片的大小、位置、透明度和显示时间。

    :param input_video: 输入视频的路径
    :param output_video: 输出视频的路径
    :param image_path: 图片的路径
    :param position: 图片的位置，格式为 (x, y)
    :param size: 图片的大小，格式为 (width, height)
    :param opacity: 图片的透明度，范围为 0.0 (完全透明) 到 1.0 (完全不透明)
    :param duration: 图片的显示时间，格式为 (start_time, end_time)
    """
    try:
        # 标准化路径以确保兼容性
        normalized_input_video = os.path.normpath(input_video)
        normalized_output_video = os.path.normpath(output_video)
        normalized_image_path = os.path.normpath(image_path)
        
        # 构建ffmpeg命令
        command = [
            'ffmpeg',
            '-i', normalized_input_video,
            '-i', normalized_image_path,
            '-filter_complex',
            f"[1:v]scale={size[0]}:{size[1]},format=rgba,colorchannelmixer=aa={opacity}[logo];"
            f"[0:v][logo]overlay={position[0]}:{position[1]}:enable='between(t,{duration[0]},{duration[1]})'",
            '-c:a', 'copy',
            normalized_output_video
        ]
        # 执行命令
        subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f'添加封面元素图片失败: {str(e)}')
