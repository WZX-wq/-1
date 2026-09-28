import subprocess
import os


def compress_video(input_video_path, output_path, quality='medium', speed='medium'):
    """
    视频压缩功能，在保证清晰度的同时尽量减小文件大小
    
    参数：
        input_video_path: 输入视频路径
        output_path: 输出视频路径
        quality: 压缩质量 ('low', 'medium', 'high') - 默认medium保证较好的清晰度
        speed: 压缩速度 ('slow', 'medium', 'fast') - 默认medium平衡速度和效率
    """
    try:
        # 根据质量设置CRF值 (越小质量越好，文件越大)
        # libx264编码器的CRF范围是0-51，默认23
        quality_settings = {
            'high': 23,    # 高质量，文件较大
            'medium': 28,  # 中等质量，压缩更多
            'low': 32      # 较低质量，文件最小
        }
        
        # 根据速度设置预设值
        speed_settings = {
            'slow': 'slow',      # 最慢但压缩率最高
            'medium': 'medium',  # 中等速度
            'fast': 'fast'       # 快速但压缩率较低
        }
        
        crf = quality_settings.get(quality, 25)
        preset = speed_settings.get(speed, 'medium')
        
        # 压缩命令 - 使用libx264编码器
        command = [
            "ffmpeg",
            "-i", input_video_path,
            "-c:v", "libx264",           # 视频编码器
            "-crf", str(crf),           # 质量控制因子
            "-preset", preset,           # 编码速度预设
            "-c:a", "aac",              # 音频编码器
            "-b:a", "96k",              # 音频比特率96kbps，压缩更多
            "-ar", "22050",             # 采样率22kHz，降低采样率
            "-y",                        # 覆盖已存在的输出文件
            output_path
        ]
        
        # 执行压缩命令
        max_retries = 2
        for attempt in range(max_retries):
            try:
                print(f"🔄 开始压缩 (尝试 {attempt + 1}/{max_retries})")
                
                # 使用subprocess.run但不捕获输出，避免编码问题
                process = subprocess.run(
                    command,
                    capture_output=False,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                    timeout=600
                )
                
                if process.returncode == 0 and os.path.exists(output_path):
                    # 验证输出文件是否有效（非空且可读）
                    if os.path.getsize(output_path) > 0:
                        # 计算压缩比
                        original_size = os.path.getsize(input_video_path)
                        compressed_size = os.path.getsize(output_path)
                        compression_ratio = (original_size - compressed_size) / original_size * 100
                        
                        print(f"✅ 视频压缩完成")
                        print(f"📊 原始大小: {original_size / (1024*1024):.1f} MB")
                        print(f"📊 压缩后大小: {compressed_size / (1024*1024):.1f} MB")
                        print(f"📊 压缩率: {compression_ratio:.1f}%")
                        
                        return True
                    else:
                        print(f"❌ 压缩文件为空或损坏")
                        if attempt < max_retries - 1:
                            print(f"🔄 将重试...")
                            continue
                        return False
                else:
                    print(f"❌ 视频压缩失败，返回码: {process.returncode}")
                    if attempt < max_retries - 1:
                        print(f"🔄 将重试...")
                        continue
                    return False
                    
            except FileNotFoundError:
                print(f"❌ 找不到FFmpeg程序，请确保已安装FFmpeg")
                return False
            except Exception as e:
                print(f"❌ 视频压缩执行异常: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"🔄 将重试...")
                    continue
                return False
        
        return False
            
    except Exception as e:
        print(f"❌ 视频压缩异常: {str(e)}")
        return False


def compress_video_fast(input_video_path, output_path):
    """
    快速视频压缩函数，使用默认参数
    """
    return compress_video(input_video_path, output_path, quality='medium', speed='medium')