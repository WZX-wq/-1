import os
import random
import subprocess

def get_video_resolution(video_path):
    """获取视频分辨率"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'default',
            '-show_entries', 'stream=width,height',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        width, height = None, None
        for line in result.stdout.split('\n'):
            if 'width=' in line:
                width = int(line.split('=')[1].strip())
            elif 'height=' in line:
                height = int(line.split('=')[1].strip())
        
        if width and height:
            return width, height
        return None, None
    except:
        return None, None

def calculate_overlay_position(position, video_width=1920, video_height=1080, overlay_width=640, overlay_height=480):
    """
    计算绿幕叠加位置，支持横屏和竖屏视频
    
    Args:
        position: 位置参数
        video_width: 主视频宽度
        video_height: 主视频高度
        overlay_width: 绿幕宽度
        overlay_height: 绿幕高度
    
    Returns:
        tuple: (x, y) 位置坐标
    """
    print(f"🎬 视频分辨率: {video_width}x{video_height}")
    print(f"🎬 绿幕尺寸: {overlay_width}x{overlay_height}")
    
    # 预定义位置 - 自动适配横屏/竖屏
    positions = {
        "top-left": (10, 10),
        "top-center": ((video_width - overlay_width) // 2, 10),
        "top-right": (video_width - overlay_width - 10, 10),
        "center-left": (10, (video_height - overlay_height) // 2),
        "center": ((video_width - overlay_width) // 2, (video_height - overlay_height) // 2),
        "center-right": (video_width - overlay_width - 10, (video_height - overlay_height) // 2),
        "bottom-left": (10, video_height - overlay_height - 10),
        "bottom-center": ((video_width - overlay_width) // 2, video_height - overlay_height - 10),
        "bottom-right": (video_width - overlay_width - 10, video_height - overlay_height - 10)
    }
    
    # 如果是自定义坐标
    if ":" in position:
        try:
            x, y = position.split(":")
            custom_x, custom_y = int(x), int(y)
            
            # 检查自定义坐标是否在视频范围内
            if custom_x < 0 or custom_y < 0:
                print(f"⚠️ 自定义坐标不能为负数: {position}")
                return positions["bottom-right"]
            if custom_x + overlay_width > video_width or custom_y + overlay_height > video_height:
                print(f"⚠️ 自定义坐标超出视频范围: {position}，视频尺寸: {video_width}x{video_height}")
                return positions["bottom-right"]
            
            return (custom_x, custom_y)
        except:
            print(f"⚠️ 无效的自定义坐标: {position}，使用默认位置")
            return positions["bottom-right"]
    
    # 获取预定义位置
    result = positions.get(position, positions["bottom-right"])
    
    # 检查位置是否在有效范围内，如果超出边界则自动调整
    x, y = result
    
    # 确保绿幕不会超出视频边界
    if x < 0:
        x = 10  # 最小左边距
    if y < 0:
        y = 10  # 最小上边距
    if x + overlay_width > video_width:
        x = max(10, video_width - overlay_width - 10)  # 调整到右侧边界内
    if y + overlay_height > video_height:
        y = max(10, video_height - overlay_height - 10)  # 调整到下侧边界内
    
    result = (x, y)
    print(f"📍 计算位置: {result} - {position}")
    
    # 检查是否发生了位置调整
    original_pos = positions.get(position, positions["bottom-right"])
    if result != original_pos:
        print(f"🔧 位置自动调整: 原始位置 {original_pos} -> 调整后 {result}")
        print(f"📐 绿幕尺寸 {overlay_width}x{overlay_height} 在视频 {video_width}x{video_height} 中会超出边界")
    
    return result

def get_video_duration_ffprobe(video_path):
    """获取视频时长"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'default',
            '-show_entries', 'stream=duration',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'duration=' in line:
                return float(line.split('=')[1].strip())
        return None
    except:
        return None

def add_green_screen_overlay_to_video(input_video_path, output_video_path, overlay_duration=3.0, 
                                      position="bottom-right", scale=1.0, opacity=1.0):
    """
    为视频添加绿幕素材叠加层（绿幕叠加在原视频上）
    
    Args:
        input_video_path: 输入视频路径
        output_video_path: 输出视频路径
        overlay_duration: 绿幕素材持续时间（秒）
        position: 绿幕位置，可选值：
                 "top-left", "top-center", "top-right",
                 "center-left", "center", "center-right", 
                 "bottom-left", "bottom-center", "bottom-right"
                 或自定义坐标 "x:y" (如 "100:50")
        scale: 绿幕缩放比例 (0.1-2.0)
        opacity: 绿幕透明度 (0.0-1.0)
    
    Returns:
        bool: 是否成功
    """
    try:
        # 获取绿幕素材文件夹路径
        current_dir = os.getcwd()
        green_screen_folder = os.path.join(current_dir, 'DigitalHumans')
        
        if not os.path.exists(green_screen_folder):
            print(f"❌ 绿幕素材文件夹不存在: {green_screen_folder}")
            return False
        
        # 获取所有绿幕素材文件
        green_screen_files = []
        for file in os.listdir(green_screen_folder):
            if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                green_screen_files.append(os.path.join(green_screen_folder, file))
        
        if not green_screen_files:
            print(f"❌ 绿幕素材文件夹中没有找到视频文件")
            return False
        
        # 随机选择一个绿幕素材
        selected_green_screen = random.choice(green_screen_files)
        print(f"🎬 选择绿幕素材: {os.path.basename(selected_green_screen)}")
        
        # 获取绿幕素材的实际时长
        green_screen_duration = get_video_duration_ffprobe(selected_green_screen)
        if green_screen_duration is None:
            print(f"❌ 无法获取绿幕素材时长")
            return False
        
        print(f"📊 绿幕素材时长: {green_screen_duration:.2f}秒")
        print(f"📊 需要叠加时长: {overlay_duration:.2f}秒")
        
        # 验证参数范围
        scale = max(0.1, min(2.0, scale))
        opacity = max(0.0, min(1.0, opacity))
        
        # 获取输入视频的实际分辨率
        video_width, video_height = get_video_resolution(input_video_path)
        if not video_width or not video_height:
            print("⚠️ 无法获取视频分辨率，使用默认1920x1080")
            video_width, video_height = 1920, 1080
        
        # 获取绿幕素材的实际分辨率
        green_width, green_height = get_video_resolution(selected_green_screen)
        if not green_width or not green_height:
            print("⚠️ 无法获取绿幕分辨率，使用默认640x480")
            green_width, green_height = 640, 480
        
        print(f"🎬 绿幕原始尺寸: {green_width}x{green_height}")
        
        # 智能缩放：如果绿幕相对于视频太大，自动缩小
        max_width_ratio = 0.5  # 绿幕最大宽度不超过视频的60%（可调整）
        max_height_ratio = 0.5  # 绿幕最大高度不超过视频的60%（可调整）
        
        # 计算基于视频尺寸的最大允许绿幕尺寸
        max_allowed_width = video_width * max_width_ratio
        max_allowed_height = video_height * max_height_ratio
        
        # 计算需要的缩放比例
        width_scale_needed = max_allowed_width / green_width if green_width > max_allowed_width else 1.0
        height_scale_needed = max_allowed_height / green_height if green_height > max_allowed_height else 1.0
        
        # 选择更严格的缩放比例（确保两个维度都在限制内）
        auto_scale = min(width_scale_needed, height_scale_needed)
        
        # 最终缩放比例：用户指定的缩放 × 自动缩放
        final_scale = scale * auto_scale
        
        # 确保最终缩放比例在合理范围内
        final_scale = max(0.1, min(3.0, final_scale))  # 最大允许3倍放大
        
        if auto_scale < 1.0:
            print(f"🔧 绿幕尺寸过大，自动缩小比例: {auto_scale:.2f}x")
        else:
            print(f"✅ 绿幕尺寸合适，无需自动缩小")
        
        # 计算缩放后的绿幕尺寸（保持长宽比）
        scaled_width = int(green_width * final_scale)
        scaled_height = int(green_height * final_scale)
        
        print(f"🎬 最终缩放比例: {final_scale:.2f}x (用户: {scale}x × 自动: {auto_scale:.2f}x)")
        print(f"🎬 缩放后绿幕尺寸: {scaled_width}x{scaled_height}")
        
        # 计算叠加位置（使用实际视频分辨率和实际绿幕尺寸）
        overlay_x, overlay_y = calculate_overlay_position(position, video_width, video_height, scaled_width, scaled_height)
        print(f"🔍 缩放比例: {scale:.1f}x")
        print(f"👁️ 透明度: {opacity:.1f}")
        
        # 判断时长关系并选择处理方式
        if green_screen_duration < overlay_duration:
            # 绿幕素材时长不够 - 使用更可靠的循环方法
            print(f"⚠️ 绿幕素材时长不够，将使用循环叠加")
            # 计算需要循环多少次
            loop_times = int(overlay_duration / green_screen_duration) + 1
            # 先创建循环的绿幕素材文件，然后叠加
            print(f"🔄 创建循环绿幕素材，循环次数: {loop_times}")
            
            # 创建临时循环绿幕文件
            temp_green_screen = output_video_path.replace('.mp4', '_temp_green.mp4')
            
            # 使用FFmpeg创建循环绿幕
            loop_cmd = [
                'ffmpeg',
                '-stream_loop', str(loop_times),
                '-i', selected_green_screen,
                '-t', str(overlay_duration),
                '-c', 'copy',
                '-y',
                temp_green_screen
            ]
            
            try:
                loop_result = subprocess.run(loop_cmd, capture_output=True, text=True)
                if loop_result.returncode != 0:
                    print(f"❌ 创建循环绿幕失败: {loop_result.stderr}")
                    return False
                    
                # 使用循环后的绿幕进行叠加（支持位置、缩放、透明度）
                filter_complex_parts = [
                    f'[1:v]scale={scaled_width}:{scaled_height}[gs]',
                    f'[gs]colorkey=0x00FF00:0.1:0.2[gs_ck]',
                    f'[gs_ck]trim=duration={overlay_duration}[gs_trim]'
                ]
                
                # 添加透明度效果（如果需要）
                if opacity < 1.0:
                    filter_complex_parts.append(f'[gs_trim]format=yuva420p,colorchannelmixer=aa={opacity}[gs_alpha]')
                    overlay_input = '[gs_alpha]'
                else:
                    overlay_input = '[gs_trim]'
                
                filter_complex_parts.append(f'[0:v]{overlay_input}overlay={overlay_x}:{overlay_y}:repeatlast=0[outv]')
                filter_complex = ';'.join(filter_complex_parts)
                
                # 更新命令使用临时循环文件
                selected_green_screen = temp_green_screen
                need_cleanup_temp = True  # 标记需要清理临时文件
                
            except Exception as e:
                print(f"❌ 创建循环绿幕异常: {e}")
                return False
            
        elif green_screen_duration > overlay_duration:
            # 绿幕素材时长超出 - 截取前N秒
            print(f"✅ 绿幕素材时长充足，将截取前{overlay_duration}秒")
            filter_complex_parts = [
                f'[1:v]scale={scaled_width}:{scaled_height}[gs]',
                f'[gs]colorkey=0x00FF00:0.1:0.2[gs_ck]',
                f'[gs_ck]trim=duration={overlay_duration}[gs_trim]'
            ]
            
            # 添加透明度效果（如果需要）
            if opacity < 1.0:
                filter_complex_parts.append(f'[gs_trim]format=yuva420p,colorchannelmixer=aa={opacity}[gs_alpha]')
                overlay_input = '[gs_alpha]'
            else:
                overlay_input = '[gs_trim]'
            
            filter_complex_parts.append(f'[0:v]{overlay_input}overlay={overlay_x}:{overlay_y}:repeatlast=0[outv]')
            filter_complex = ';'.join(filter_complex_parts)
            
        else:
            # 绿幕素材时长正好 - 直接使用
            print(f"✅ 绿幕素材时长正好，直接使用")
            filter_complex_parts = [
                f'[1:v]scale={scaled_width}:{scaled_height}[gs]',
                f'[gs]colorkey=0x00FF00:0.1:0.2[gs_ck]',
                f'[gs_ck]trim=duration={overlay_duration}[gs_trim]'
            ]
            
            # 添加透明度效果（如果需要）
            if opacity < 1.0:
                filter_complex_parts.append(f'[gs_trim]format=yuva420p,colorchannelmixer=aa={opacity}[gs_alpha]')
                overlay_input = '[gs_alpha]'
            else:
                overlay_input = '[gs_trim]'
            
            filter_complex_parts.append(f'[0:v]{overlay_input}overlay={overlay_x}:{overlay_y}:repeatlast=0[outv]')
            filter_complex = ';'.join(filter_complex_parts)
        
        # 使用FFmpeg添加绿幕叠加层
        command = [
            'ffmpeg',
            '-i', input_video_path,  # 主视频
            '-i', selected_green_screen,  # 绿幕素材
            '-filter_complex', filter_complex,
            '-map', '[outv]',  # 映射视频流
            '-map', '0:a',    # 保留原音频
            '-c:v', 'libx264',  # 视频编码
            '-c:a', 'aac',      # 音频编码
            '-preset', 'medium',  # 编码预设
            '-crf', '23',       # 质量控制
            '-y',  # 覆盖输出文件
            output_video_path
        ]
        
        # 使用FFmpeg添加绿幕叠加层
        command = [
            'ffmpeg',
            '-i', input_video_path,  # 主视频
            '-i', selected_green_screen,  # 绿幕素材（可能是原始文件或临时循环文件）
            '-filter_complex', filter_complex,
            '-map', '[outv]',  # 映射视频流
            '-map', '0:a',    # 保留原音频
            '-c:v', 'libx264',  # 视频编码
            '-c:a', 'aac',      # 音频编码
            '-preset', 'medium',  # 编码预设
            '-crf', '23',       # 质量控制
            '-y', output_video_path  # 覆盖输出文件
        ]
        
        # 记录是否需要清理临时文件
        need_cleanup_temp = False
        
        print(f"🔄 开始叠加绿幕素材...")
        print(f"📝 FFmpeg命令: {' '.join(command)}")
        
        # 执行命令
        try:
            result = subprocess.run(
                command,
                capture_output=True,  # 获取错误信息
                text=True,
                encoding='utf-8',  # 明确指定编码
                errors='replace',  # 处理编码错误
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            print(f"📊 返回码: {result.returncode}")
            if result.stdout:
                print(f"📊 标准输出: {result.stdout[:500]}")  # 限制输出长度
            if result.stderr:
                print(f"📊 错误输出: {result.stderr[:500]}")  # 限制输出长度
                
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，使用GBK重试
            print("⚠️ UTF-8解码失败，尝试GBK编码...")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            print(f"📊 返回码: {result.returncode}")
            if result.stdout:
                print(f"📊 标准输出: {result.stdout[:500]}")
            if result.stderr:
                print(f"📊 错误输出: {result.stderr[:500]}")
        
        if result.returncode == 0 and os.path.exists(output_video_path):
            # 验证输出文件
            if os.path.getsize(output_video_path) > 0:
                print(f"✅ 绿幕叠加完成")
                print(f"📊 绿幕素材: {os.path.basename(selected_green_screen)}")
                print(f"📊 原始时长: {green_screen_duration:.2f}秒")
                print(f"📊 实际叠加: {overlay_duration:.2f}秒")
                
                # 清理临时文件
                if need_cleanup_temp and os.path.exists(temp_green_screen):
                    try:
                        os.remove(temp_green_screen)
                        print(f"🧹 清理临时绿幕文件: {temp_green_screen}")
                    except Exception as e:
                        print(f"⚠️ 清理临时文件失败: {e}")
                
                return True
            else:
                print(f"❌ 输出文件为空")
                # 清理临时文件
                if need_cleanup_temp and os.path.exists(temp_green_screen):
                    try:
                        os.remove(temp_green_screen)
                    except:
                        pass
                return False
        else:
            print(f"❌ 绿幕叠加失败，返回码: {result.returncode}")
            # 清理临时文件
            if need_cleanup_temp and os.path.exists(temp_green_screen):
                try:
                    os.remove(temp_green_screen)
                except:
                    pass
            return False
            
    except Exception as e:
        print(f"❌ 绿幕叠加异常: {str(e)}")
        return False

def add_green_screen_to_video(input_video_path, output_video_path, green_screen_duration=2.0, 
                              position="bottom-right", scale=1.0, opacity=1.0):
    """
    兼容性函数，调用新的叠加函数
    
    Args:
        input_video_path: 输入视频路径
        output_video_path: 输出视频路径
        green_screen_duration: 绿幕素材持续时间（秒）
        position: 绿幕位置
        scale: 绿幕缩放比例
        opacity: 绿幕透明度
    """
    return add_green_screen_overlay_to_video(input_video_path, output_video_path, 
                                            green_screen_duration, position, scale, opacity)

def process_green_screen_for_videos(video_list, output_folder, position="bottom-right", scale=1.0, opacity=1.0):
    """
    批量为视频添加绿幕叠加层
    
    Args:
        video_list: 视频路径列表
        output_folder: 输出文件夹
        position: 绿幕位置（所有视频统一设置）
        scale: 绿幕缩放比例
        opacity: 绿幕透明度
    
    Returns:
        list: 处理后的视频路径列表
    """
    processed_videos = []
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"🎬 批量处理绿幕叠加 - 位置: {position}, 缩放: {scale}x, 透明度: {opacity}")
    
    for i, video_path in enumerate(video_list):
        if not os.path.exists(video_path):
            print(f"⚠️ 视频文件不存在，跳过: {video_path}")
            continue
            
        # 生成输出文件名
        video_name = os.path.basename(video_path)
        name, ext = os.path.splitext(video_name)
        output_path = os.path.join(output_folder, f"{name}_green{ext}")
        
        print(f"📹 处理视频 {i+1}/{len(video_list)}: {video_name}")
        
        # 添加绿幕叠加
        if add_green_screen_overlay_to_video(video_path, output_path, 
                                            position=position, scale=scale, opacity=opacity):
            processed_videos.append(output_path)
        else:
            # 如果失败，使用原视频
            print(f"⚠️ 绿幕叠加失败，使用原视频: {video_path}")
            processed_videos.append(video_path)
    
    print(f"✅ 批量处理完成，成功处理 {len([v for v in processed_videos if '_green' in v])} 个视频")
    return processed_videos