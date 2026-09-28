#!/usr/bin/env python3
"""
优化的水印添加工具
性能优化版本 - 显著减少处理时间
"""

import os
import sys
import subprocess
import platform
import psutil
from pathlib import Path

def get_system_info():
    """获取系统信息用于优化"""
    system = platform.system()
    cpu_count = psutil.cpu_count()
    
    # 检测GPU
    gpu_available = False
    gpu_type = None
    try:
        import torch
        if torch.cuda.is_available():
            gpu_available = True
            gpu_type = "CUDA"
    except ImportError:
        pass
    
    return {
        'system': system,
        'cpu_count': cpu_count,
        'gpu_available': gpu_available,
        'gpu_type': gpu_type
    }

def get_optimal_encoding_params():
    """获取最优的编码参数"""
    system_info = get_system_info()
    
    # 基础优化参数
    params = {
        'preset': 'faster',  # 平衡速度和质量
        'crf': 23,
        'tune': 'fastdecode',  # 优化解码速度
        'threads': min(8, system_info['cpu_count']),  # 限制线程数
    }
    
    # 根据系统调整
    if system_info['system'] == 'Windows':
        # Windows 优化
        params.update({
            'movflags': '+faststart+frag_keyframe+empty_moov',
            'brand': 'mp42',  # 更好的兼容性
        })
    elif system_info['system'] == 'Darwin':
        # macOS 优化
        params.update({
            'preset': 'medium',
            'tune': 'zerolatency',
        })
    
    # GPU 加速
    if system_info['gpu_available'] and system_info['gpu_type'] == 'CUDA':
        params.update({
            'c:v': 'h264_nvenc',  # NVIDIA GPU 加速
            'preset': 'p4',  # NVENC 预设
            'tune': 'll',  # 低延迟
            'rc': 'vbr',  # 可变比特率
            'cq': 23,
        })
    
    return params, system_info

def add_text_watermark_optimized(video_path, output_path, watermark_setting):
    """优化的文字水印添加"""
    print("🚀 使用优化版本添加文字水印...")
    
    # 获取优化参数
    encoding_params, system_info = get_optimal_encoding_params()
    print(f"系统信息: {system_info['system']}, CPU核心: {system_info['cpu_count']}")
    if system_info['gpu_available']:
        print(f"🎮 检测到GPU加速: {system_info['gpu_type']}")
    
    # 解析水印设置
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
    
    # Windows字体路径
    font_file = f'C:\\Windows\\Fonts\\{font_text}'
    
    # 检查字体文件
    if not os.path.exists(font_file):
        print(f"错误: 字体文件不存在: {font_file}")
        sys.exit(1)
    
    # 转义参数
    escaped_font_file = escape_filter_arg(font_file)
    escaped_text = escape_filter_arg(text)
    
    # 优化的滤镜链
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
    
    # 构造优化的FFmpeg命令
    command = ['ffmpeg', '-y']
    
    # 输入
    command.extend(['-i', video_path])
    
    # 优化线程数
    command.extend(['-threads', str(encoding_params['threads'])])
    
    # 滤镜
    command.extend(['-vf', drawtext_filter])
    
    # 视频编码器选择
    if encoding_params.get('c:v') == 'h264_nvenc':
        command.extend(['-c:v', 'h264_nvenc'])
        command.extend(['-preset', encoding_params.get('preset', 'p4')])
        command.extend(['-tune', encoding_params.get('tune', 'll')])
        command.extend(['-rc', encoding_params.get('rc', 'vbr')])
        command.extend(['-cq', str(encoding_params.get('cq', 23))])
    else:
        command.extend(['-c:v', 'libx264'])
        command.extend(['-preset', encoding_params.get('preset', 'faster')])
        command.extend(['-tune', encoding_params.get('tune', 'fastdecode')])
        command.extend(['-crf', str(encoding_params.get('crf', 23))])
    
    # 音频编码（直接复制，最快）
    command.extend(['-c:a', 'copy'])
    
    # 优化标志
    if system_info['system'] == 'Windows':
        command.extend(['-movflags', '+faststart+frag_keyframe+empty_moov'])
        command.extend(['-brand', 'mp42'])
    else:
        command.extend(['-movflags', '+faststart'])
    
    # 输出
    command.append(output_path)
    
    print("执行优化命令:", " ".join(command[:8]) + "...")
    
    try:
        start_time = time.time()
        
        # 执行命令
        process = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if system_info['system'] == 'Windows' else 0
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"✅ 文字水印添加完成！耗时: {processing_time:.2f}秒")
        return processing_time
        
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg执行失败 (返回码: {e.returncode})")
        stderr = e.stderr.decode(sys.getdefaultencoding(), errors='replace')
        print("错误详情:", stderr)
        sys.exit(1)

def add_pic_watermark_optimized(video_path, pic_path, output_path, watermark_setting):
    """优化的图片水印添加"""
    print("🚀 使用优化版本添加图片水印...")
    
    # 获取优化参数
    encoding_params, system_info = get_optimal_encoding_params()
    
    # 解析设置
    x_offset = watermark_setting['watermark_location'][0]
    y_offset = watermark_setting['watermark_location'][1]
    scale_size = watermark_setting['zoom_size']
    alpha = watermark_setting['pic_alpha']
    
    # 优化的滤镜链 - 减少不必要的格式转换
    overlay_filter = (
        f'[1:v]scale=iw*{scale_size}:ih*{scale_size},'
        f'format=argb,colorchannelmixer=aa={alpha}[watermark];'
        f'[0:v][watermark]overlay={x_offset}:{y_offset}:format=auto,'
        f'format=yuv420p'
    )
    
    # 构造优化的FFmpeg命令
    command = ['ffmpeg', '-y']
    
    # 输入
    command.extend(['-i', video_path, '-i', pic_path])
    
    # 优化线程数
    command.extend(['-threads', str(encoding_params['threads'])])
    
    # 滤镜
    command.extend(['-filter_complex', overlay_filter])
    
    # 视频编码器选择
    if encoding_params.get('c:v') == 'h264_nvenc':
        command.extend(['-c:v', 'h264_nvenc'])
        command.extend(['-preset', encoding_params.get('preset', 'p4')])
        command.extend(['-tune', encoding_params.get('tune', 'll')])
        command.extend(['-rc', encoding_params.get('rc', 'vbr')])
        command.extend(['-cq', str(encoding_params.get('cq', 23))])
    else:
        command.extend(['-c:v', 'libx264'])
        command.extend(['-preset', encoding_params.get('preset', 'faster')])
        command.extend(['-tune', encoding_params.get('tune', 'fastdecode')])
        command.extend(['-crf', str(encoding_params.get('crf', 23))])
    
    # 音频直接复制
    command.extend(['-c:a', 'copy'])
    
    # 优化标志
    if system_info['system'] == 'Windows':
        command.extend(['-movflags', '+faststart+frag_keyframe+empty_moov'])
        command.extend(['-brand', 'mp42'])
    else:
        command.extend(['-movflags', '+faststart'])
    
    # 输出
    command.append(output_path)
    
    try:
        start_time = time.time()
        
        process = subprocess.run(
            command,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if system_info['system'] == 'Windows' else 0
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"✅ 图片水印添加完成！耗时: {processing_time:.2f}秒")
        return processing_time
        
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg执行失败 (返回码: {e.returncode})")
        stderr = e.stderr.decode(sys.getdefaultencoding(), errors='replace')
        print("错误详情:", stderr)
        sys.exit(1)

def escape_filter_arg(arg):
    """转义滤镜参数中的特殊字符"""
    arg = arg.replace('\\', '\\\\')
    arg = arg.replace(':', '\\:')
    arg = arg.replace('"', '\\"')
    arg = arg.replace("'", "\\'")
    return arg

# 导入时间模块
import time

# 向后兼容的函数名
def add_text_watermark(video_path, output_path, watermark_setting):
    """向后兼容函数"""
    return add_text_watermark_optimized(video_path, output_path, watermark_setting)

def add_pic_watermark(video_path, pic_path, output_path, watermark_setting):
    """向后兼容函数"""
    return add_pic_watermark_optimized(video_path, pic_path, output_path, watermark_setting)