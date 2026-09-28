import subprocess
import os
import shutil
from typing import Tuple


def overlay_transparent_animation(
        background_video: str,
        material_path_dir: str,
        output_path: str,
        position: Tuple[int, int] = (0, 0),
        size: Tuple[int, int] = None,
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

    # 获取背景视频时长
    probe_cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        background_video
    ]
    bg_duration = float(subprocess.run(probe_cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout)

    # 临时目录存放PNG序列
    # temp_dir = r"D:\batchAiCutter\batchAiCutter\灯笼"
    # os.makedirs(temp_dir, exist_ok=True)

    try:
        # # 阶段1：黑底视频转透明PNG序列
        # cmd1 = [
        #     'ffmpeg',
        #     '-i', black_bg_video,
        #     '-vf', f"colorkey=0x000000:0.1:0.1,format=rgba",
        #     '-compression_level', '6',
        #     os.path.join(temp_dir, 'frame_%04d.png')
        # ]
        # subprocess.run(cmd1, check=True, capture_output=True)

        # 阶段2：叠加到背景视频
        cmd2 = [
            'ffmpeg',
            # '-stream_loop', '-1',  # 背景循环
            '-i', background_video,
            '-framerate', str(fps),
            '-i', os.path.join(material_path_dir, 'frame_%04d.png'),
            '-filter_complex',
            _build_filter_complex(position, size),
            '-c:v', 'libx264',
            '-crf', str(crf),
            # '-preset', 'fast',
            # '-pix_fmt', 'yuv420p',
            '-c:a', 'copy',
            '-movflags', '+faststart',
            '-y',  # 覆盖输出文件
            output_path
        ]
        subprocess.run(cmd2, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(str(e))

    # finally:
    #     # 清理临时文件
    #     shutil.rmtree(temp_dir, ignore_errors=True)


def _build_filter_complex(
        position: Tuple[int, int],
        size: Tuple[int, int]
) -> str:
    """构建filter_complex字符串"""
    x, y = position
    width, _ = size if size else (300, -1)  # 默认宽度为300，高度自动保持比例

    filters = [
        f"[1]format=rgba,scale={width}:-1[fg]",
        f"[0][fg]overlay=format=auto:x={x}:y={y}:shortest=1"
    ]

    return ";".join(filters)


# 使用示例
if __name__ == "__main__":
    material_path_dir = r"/material/灯笼"

    overlay_transparent_animation(
        background_video="cover.mp4",
        material_path_dir=material_path_dir,
        output_path="sptx.mp4",
        position=(-200, 50),
        size=(800, -1),  # 宽度300，高度等比缩放
        fps=30,
        crf=20
    )
    overlay_transparent_animation(
        background_video="sptx.mp4",
        material_path_dir=material_path_dir,
        output_path="sptx1.mp4",
        position=(500, 50),
        size=(800, -1),  # 宽度300，高度等比缩放
        fps=30,
        crf=20
    )
