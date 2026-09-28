# import subprocess
# import os
#
#
# def mirror_video(input_path, output_path, flip_horizontal=True):
#     """
#     将视频素材镜像。
#
#     参数:
#     input_path (str): 输入视频的路径。
#     output_path (str): 输出视频的路径。
#     flip_horizontal (bool, optional): 是否水平翻转。默认为 True（水平翻转）。如果设置为 False，则垂直翻转。
#     """
#     # 检查输入路径是否存在
#     if not os.path.exists(input_path):
#         raise FileNotFoundError(f"输入文件未找到：{input_path}")
#
#     # 构造 FFmpeg 命令
#     flip_filter = "hflip" if flip_horizontal else "vflip"
#     ffmpeg_command = [
#         "ffmpeg",
#         "-i", input_path,  # 输入视频
#         "-vf", flip_filter,  # 应用翻转滤镜
#         "-c:v", "libx264",  # 使用 H.264 编码器
#         "-c:a", "copy",  # 复制音频流，不重新编码
#         "-preset", "fast",  # 设置编码速度与压缩比的平衡
#         "-movflags", "+faststart",  # 优化 FLV 文件，使视频更快开始播放
#         "-y",  # 覆盖输出文件
#         output_path  # 输出视频路径
#     ]
#
#     try:
#         # 执行 FFmpeg 命令
#         subprocess.run(ffmpeg_command, check=True)
#         print(f"视频已生成并镜像：{output_path}")
#
#     except subprocess.CalledProcessError as e:
#         print(f"镜像视频时出错：{e}")
#     except Exception as e:
#         print(f"发生错误：{e}")
#
#
# # 示例用法
# if __name__ == "__main__":
#     input_path = "sc.mp4"  # 替换为你的输入视频路径
#     output_path = "sc1.mp4"  # 替换为输出视频路径
#
#     # 水平翻转（镜像效果）
#     mirror_video(input_path, output_path, flip_horizontal=True)
import os
import shutil


# 垂直翻转
# mirror_video(input_path, output_path, flip_horizontal=False)


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


# 示例用法
folder_path = r"D:\batchAiCutter\batchAiCutter\灯笼"  # 替换为你的文件夹路径
start_index = 341  # 从 frame_0086.png 开始命名

copy_and_rename_png_in_same_folder(folder_path, start_index)