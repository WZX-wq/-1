#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人物图片添加 Worker
用于将人物图片居中添加到视频上，支持移动动画效果
"""

import os
import subprocess
from PyQt6.QtCore import QRunnable, pyqtSignal
from worker.worker_signals import WorkerSignals


class AddPersonPicWorker(QRunnable):
    """添加人物图片到视频中心的 Worker"""

    def __init__(self, input_video_path, person_pic_path, output_video_path, position="center", scale_factor=1.5):
        """
        初始化人物图片添加 Worker

        Args:
            input_video_path: 输入视频路径
            person_pic_path: 人物图片路径
            output_video_path: 输出视频路径
            position: 图片位置，可选值: "center", "top-left", "top-right",
                     "bottom-left", "bottom-right", "top-center", "bottom-center"
            scale_factor: 缩放比例，默认 1.5（放大50%），例如 2.0 放大一倍
        """
        super().__init__()
        self.input_video_path = input_video_path
        self.person_pic_path = person_pic_path
        self.output_video_path = output_video_path
        self.position = position
        self.scale_factor = scale_factor
        self.signals = WorkerSignals()

    def run(self):
        """执行人物图片添加任务"""
        try:
            print(f"👤 开始添加人物图片到视频")
            print(f"📹 输入视频: {self.input_video_path}")
            print(f"👤 人物图片: {self.person_pic_path}")
            print(f"📍 位置: {self.position}")

            # 获取视频分辨率
            video_width, video_height = self.get_video_resolution()

            if not video_width or not video_height:
                raise Exception("无法获取视频分辨率")

            print(f"📐 视频分辨率: {video_width}x{video_height}")

            # 获取人物图片尺寸
            pic_width, pic_height = self.get_image_resolution()

            if not pic_width or not pic_height:
                raise Exception("无法获取图片分辨率")

            print(f"📐 人物图片尺寸: {pic_width}x{pic_height}")

            # 计算缩放后的尺寸（用于信息输出）
            scaled_width = int(pic_width * self.scale_factor)
            scaled_height = int(pic_height * self.scale_factor)

            print(f"📐 原始尺寸: {pic_width}x{pic_height}")
            print(f"📐 缩放后尺寸: {scaled_width}x{scaled_height} (比例: {self.scale_factor})")

            # 计算起始位置（始终使用居中，使用原始尺寸）
            orig_x = (video_width - pic_width) // 2
            orig_y = (video_height - pic_height) // 2

            print(f"📍 起始位置（居中）: ({orig_x}, {orig_y})")

            # 计算目标位置（使用原始尺寸）
            target_x, target_y = self.calculate_target_position(
                video_width, video_height, pic_width, pic_height
            )

            print(f"📍 目标位置: ({target_x}, {target_y})")

            # 构建filter_complex（使用if嵌套表达式实现平滑动画）
            filter_complex = (
                f'[1:v]scale={pic_width}:{pic_height}:flags=lanczos,format=argb,colorchannelmixer=aa=1.0[person];'
                f'[0:v][person]overlay='
                f"'if(lt(t,3),{orig_x},if(lt(t,5),{orig_x}+({target_x}-{orig_x})*(t-3)/2,{target_x}))':"
                f"'if(lt(t,3),{orig_y},if(lt(t,5),{orig_y}+({target_y}-{orig_y})*(t-3)/2,{target_y}))',"
                f'format=yuv420p'
            )

            command = [
                'ffmpeg', '-y',
                '-i', self.input_video_path,
                '-i', self.person_pic_path,
                '-threads', '4',
                '-preset', 'faster',
                '-tune', 'fastdecode',
                '-filter_complex', filter_complex,
                '-c:v', 'libx264',
                '-crf', '23',
                '-c:a', 'copy',
                '-movflags', '+faststart',
                self.output_video_path
            ]

            print(f"🔧 FFmpeg命令: {' '.join(command)}")

            # 执行 FFmpeg 命令
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if result.returncode != 0:
                print(f"❌ FFmpeg返回码: {result.returncode}")
                print(f"❌ 标准错误: {result.stderr}")
                print(f"❌ 标准输出: {result.stdout}")
                raise Exception(f"FFmpeg执行失败 (返回码: {result.returncode})")

            # 验证输出文件
            if not os.path.exists(self.output_video_path):
                raise Exception("输出文件未生成")

            output_size = os.path.getsize(self.output_video_path)
            print(f"✅ 人物图片添加成功")
            print(f"📦 输出文件大小: {output_size:,} 字节")
            print(f"📁 输出文件: {self.output_video_path}")

            # 发送完成信号
            self.signals.finished.emit('完成')

        except Exception as e:
            print(f"❌ 添加人物图片失败: {str(e)}")
            # 发送错误信号
            self.signals.errorOccurred.emit(str(e))

    def get_video_resolution(self):
        """获取视频分辨率"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'default',
                '-show_entries', 'stream=width,height',
                self.input_video_path
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            width, height = None, None
            for line in result.stdout.split('\n'):
                if 'width=' in line:
                    width = int(line.split('=')[1].strip())
                elif 'height=' in line:
                    height = int(line.split('=')[1].strip())

            return width, height
        except Exception as e:
            print(f"⚠️ 获取视频分辨率失败: {e}")
            return None, None

    def get_image_resolution(self):
        """获取图片分辨率"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'default',
                '-show_entries', 'stream=width,height',
                self.person_pic_path
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            width, height = None, None
            for line in result.stdout.split('\n'):
                if 'width=' in line:
                    width = int(line.split('=')[1].strip())
                elif 'height=' in line:
                    height = int(line.split('=')[1].strip())

            return width, height
        except Exception as e:
            print(f"⚠️ 获取图片分辨率失败: {e}")
            return None, None

    def calculate_center_position(self, video_width, video_height, pic_width, pic_height):
        """
        计算人物图片居中位置

        Args:
            video_width: 视频宽度
            video_height: 视频高度
            pic_width: 人物图片宽度
            pic_height: 人物图片高度

        Returns:
            tuple: (x, y) 位置坐标
        """
        # 定义所有位置计算方式
        positions = {
            "center": ((video_width - pic_width) // 2, (video_height - pic_height) // 2),
            "top-left": (20, 20),
            "top-center": ((video_width - pic_width) // 2, 20),
            "top-right": (video_width - pic_width - 20, 20),
            "bottom-left": (20, video_height - pic_height - 20),
            "bottom-center": ((video_width - pic_width) // 2, video_height - pic_height - 20),
            "bottom-right": (video_width - pic_width - 20, video_height - pic_height - 20),
            "center-left": (20, (video_height - pic_height) // 2),
            "center-right": (video_width - pic_width - 20, (video_height - pic_height) // 2)
        }

        # 获取指定位置
        x, y = positions.get(self.position, positions["center"])

        # 边界检查，确保图片不会超出视频范围
        x = max(0, min(x, video_width - pic_width))
        y = max(0, min(y, video_height - pic_height))

        return x, y

    def calculate_target_position(self, video_width, video_height, pic_width, pic_height):
        """
        计算人物图片目标位置（用于动画终点）

        Args:
            video_width: 视频宽度
            video_height: 视频高度
            pic_width: 人物图片宽度
            pic_height: 人物图片高度

        Returns:
            tuple: (x, y) 位置坐标
        """
        # 定义所有位置计算方式
        positions = {
            "center": ((video_width - pic_width) // 2, (video_height - pic_height) // 2),
            "top-left": (40, 250),  # 左上角，y=250像素
            "top-center": ((video_width - pic_width) // 2, 20),
            "top-right": (video_width - pic_width - 20, 20),
            "bottom-left": (20, video_height - pic_height - 20),
            "bottom-center": ((video_width - pic_width) // 2, video_height - pic_height - 20),
            "bottom-right": (video_width - pic_width - 20, video_height - pic_height - 20),
            "center-left": (100, (video_height - pic_height) // 2),  # 居中左侧
            "center-right": (video_width - pic_width - 20, (video_height - pic_height) // 2)
        }

        # 获取指定位置
        x, y = positions.get(self.position, positions["center"])

        # 边界检查，确保图片不会超出视频范围
        x = max(0, min(x, video_width - pic_width))
        y = max(0, min(y, video_height - pic_height))

        return x, y
