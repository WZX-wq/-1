import json
import os
import random
import subprocess
import tempfile
import time
from pathlib import Path
import threading
import concurrent.futures
import platform
import subprocess as sp

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("警告: psutil未安装，将使用基础性能检测")

import cv2
import ffmpeg


def is_video_file(file_path):
    """检查文件是否是视频文件"""
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm'}
    _, ext = os.path.splitext(file_path)
    return ext.lower() in video_extensions


def get_video_duration(file_path):
    """获取视频时长（秒）"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
             file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return float(result.stdout.strip())
    except:
        return 0.0


def check_system_performance():
    """检查系统性能，决定是否使用多线程"""
    try:
        if PSUTIL_AVAILABLE:
            # 获取CPU信息
            cpu_count = psutil.cpu_count()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 获取内存信息
            memory = psutil.virtual_memory()
            available_memory_gb = memory.available / (1024**3)
            
            # 计算推荐线程数
            recommended_threads = min(max(1, cpu_count - 1), 4)  # 最多4个线程
            
            # 性能判断标准
            is_high_performance = (
                cpu_count >= 4 and 
                cpu_percent < 80 and 
                available_memory_gb >= 4 and
                platform.system() != "Darwin"  # macOS可能有不同的资源管理
            )
            
            performance_info = {
                'cpu_count': cpu_count,
                'cpu_percent': cpu_percent,
                'available_memory_gb': available_memory_gb,
                'recommended_threads': recommended_threads,
                'is_high_performance': is_high_performance
            }
            
            print(f"系统性能检测: CPU={cpu_count}核({cpu_percent:.1f}%), 内存={available_memory_gb:.1f}GB, 推荐线程数={recommended_threads}")
            
            return performance_info
        else:
            # 基础性能检测（不使用psutil）
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            recommended_threads = min(max(1, cpu_count - 1), 2)  # 保守估计，最多2个线程
            
            performance_info = {
                'cpu_count': cpu_count,
                'cpu_percent': 50,  # 假设值
                'available_memory_gb': 4,  # 假设值
                'recommended_threads': recommended_threads,
                'is_high_performance': cpu_count >= 4 and platform.system() != "Darwin"
            }
            
            print(f"基础性能检测: CPU={cpu_count}核, 推荐线程数={recommended_threads}")
            return performance_info
        
    except Exception as e:
        print(f"性能检测失败，使用单线程模式: {e}")
        return {
            'cpu_count': 1,
            'cpu_percent': 0,
            'available_memory_gb': 2,
            'recommended_threads': 1,
            'is_high_performance': False
        }


def validate_video_files(video_paths):
    """验证所有视频文件是否存在且完整"""
    invalid_files = []
    for i, video_path in enumerate(video_paths):
        if not os.path.exists(video_path):
            invalid_files.append(f"片段{i+1}: 文件不存在 - {video_path}")
        elif os.path.getsize(video_path) == 0:
            invalid_files.append(f"片段{i+1}: 文件为空 - {video_path}")
        else:
            duration = get_video_duration(video_path)
            if duration <= 0:
                invalid_files.append(f"片段{i+1}: 视频时长无效 - {video_path}")
    
    return invalid_files

#
# def process_video_pair(video1, video2, output, transition="0", transition_duration=1.0):
#     """处理两个视频之间的转场，生成一个包含转场的新视频"""
#     if not os.path.exists(video1) or not os.path.exists(video2):
#         raise FileNotFoundError("视频文件不存在")
#
#     try:
#         filter_complex = []
#         duration1 = get_video_duration(video1)
#         duration2 = get_video_duration(video2)
#
#         # 验证视频时长，避免offset计算错误
#         if duration1 <= 0 or duration2 <= 0:
#             raise ValueError(f"视频时长无效: {video1} 时长={duration1}, {video2} 时长={duration2}")
#
#         # 计算安全的offset值，确保转场不会超出视频时长
#         safe_offset = max(0.0, duration1 - transition_duration)
#
#         # 调整视频帧率以保持一致
#         filter_complex.append(
#             f"[0:v] fps=fps=30 [v0];"
#             f"[1:v] fps=fps=30 [v1];"
#         )
#
#         # 处理音频流
#         filter_complex.append(
#             f"[0:a] aresample=44100 [a0];"
#             f"[1:a] aresample=44100 [a1];"
#         )
#
#         # 添加转场特效
#         if transition == "1":
#             filter_complex.append(
#                 f"[v0] fade=t=out:st={duration1 - transition_duration}:d={transition_duration} [v0_out];"
#                 f"[v1] fade=t=in:st=0:d={transition_duration} [v1_in];"
#                 f"[v0_out][v1_in] concat=n=2:v=1:a=0 [v_out];"
#             )
#         elif transition == "2":
#             filter_complex.append(
#                 f"[v0][v1] xfade=transition=fade:duration={transition_duration}:"
#                 f"offset={duration1 - transition_duration} [v_out];"
#             )
#         elif transition == "3":
#             filter_complex.append(
#                 f"[v0][v1] xfade=transition=slideleft:duration={transition_duration}:"
#                 f"offset={duration1 - transition_duration} [v_out];"
#             )
#         elif transition == "4":
#             filter_complex.append(
#                 f"[v0][v1] xfade=transition=wiperight:duration={transition_duration}:"
#                 f"offset={duration1 - transition_duration} [v_out];"
#             )
#         else:  # 无转场
#             filter_complex.append(
#                 f"[v0][v1] concat=n=2:v=1:a=0 [v_out];"
#             )
#
#         # 拼接音频
#         filter_complex.append(f"[a0][a1] concat=n=2:v=0:a=1 [a_out];")
#
#         # 构建完整的滤镜字符串
#         filter_string = "".join(filter_complex)
#
#         # 构建FFmpeg命令
#         command = [
#             "ffmpeg",
#             "-y",
#             "-i", video1,
#             "-i", video2,
#             "-filter_complex", filter_string,
#             "-map", "[v_out]",
#             "-map", "[a_out]",
#             "-c:v", "libx264",
#             "-preset", "medium",
#             "-crf", "23",
#             "-c:a", "aac",
#             "-b:a", "192k",
#             "-shortest",
#             output
#         ]
#
#         # 执行命令（带超时控制）
#         try:
#             subprocess.run(
#                 command,
#                 check=True,
#                 creationflags=subprocess.CREATE_NO_WINDOW,
#                 timeout=300  # 5分钟超时
#             )
#             return output
#         except subprocess.TimeoutExpired:
#             print(f"处理视频对超时: {video1} + {video2}")
#             if os.path.exists(output):
#                 os.remove(output)
#             return None
#
#     except Exception as e:
#         print(f"处理视频对出错: {e}")
#         if os.path.exists(output):
#             os.remove(output)
#         return None
def process_video_pair(video1, video2, output, transition="0", transition_duration=1.0):
    if not os.path.exists(video1) or not os.path.exists(video2):
        raise FileNotFoundError("视频文件不存在")

    try:
        duration1 = get_video_duration(video1)
        duration2 = get_video_duration(video2)
        if duration1 <= 0 or duration2 <= 0:
            raise ValueError(f"视频时长无效: {video1}={duration1}, {video2}={duration2}")

        offset = max(0.0, duration1 - transition_duration)

        # 统一格式：30 fps、44100 Hz、1080×1920、正方形像素、yuv420p
        base = (
            "fps=30,scale=1080:1920:force_original_aspect_ratio=disable,"
            "setsar=1/1,format=yuv420p"
        )

        # 音频统一
        a_base = "aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo"

        # 先统一两段视频/音频的格式
        filter_complex = (
            f"[0:v]{base}[v0];[1:v]{base}[v1];"
            f"[0:a]{a_base}[a0];[1:a]{a_base}[a1];"
        )

        # 转场部分
        if transition == "0":          # 硬切
            filter_complex += "[v0][v1]concat=n=2:v=1:a=0[v_out];"
        else:                          # xfade 统一出口
            trans_dict = {"1": "fade", "2": "slideleft", "3": "wiperight"}
            xf_name = trans_dict.get(transition, "fade")
            filter_complex += (
                f"[v0][v1]xfade=transition={xf_name}:duration={transition_duration}:offset={offset}[v_out];"
            )

        # 音频直接 concat
        filter_complex += "[a0][a1]concat=n=2:v=0:a=1[a_out];"

        cmd = [
            "ffmpeg", "-y",
            "-i", video1,
            "-i", video2,
            "-filter_complex", filter_complex,
            "-map", "[v_out]",
            "-map", "[a_out]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", output
        ]

        subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
        return output

    except Exception as e:
        print(f"处理视频对出错: {e}")
        if os.path.exists(output):
            os.remove(output)
        return None


def concatenate_videos_in_segments(video_paths, output_path, transition="0", transition_duration=1.0):
    """智能分段处理视频，根据系统性能选择单线程或多线程模式"""
    
    # 验证所有视频文件
    print("验证视频文件完整性...")
    invalid_files = validate_video_files(video_paths)
    if invalid_files:
        print("视频文件验证失败:")
        for error in invalid_files:
            print(f"  - {error}")
        raise ValueError(f"视频文件不完整，无法继续处理")
    print(f"✅ 所有{len(video_paths)}个视频片段验证通过")
    
    # 检测系统性能
    perf_info = check_system_performance()
    
    # 根据性能决定处理方式
    if perf_info['is_high_performance'] and len(video_paths) >= 4:
        print(f"使用改进的多线程顺序处理模式 ({perf_info['recommended_threads']}个线程)")
        return _concatenate_videos_multithread_sequential(video_paths, output_path, transition, transition_duration, perf_info)
    else:
        print("使用单线程模式处理")
        return _concatenate_videos_single_thread(video_paths, output_path, transition, transition_duration)


def _process_segment_multithread(args):
    """多线程处理的单个段函数"""
    segment, segment_index, transition, transition_duration = args
    
    try:
        temp_files_segment = []
        
        # 创建临时输出文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4', dir='.') as f:
            temp_output = f.name
            temp_files_segment.append(temp_output)
        
        print(f"线程{threading.get_ident()} - 处理段 {segment_index}: {len(segment)}个视频")
        
        # 处理段内视频
        if len(segment) >= 2:
            # 先处理前两个视频
            merged = process_video_pair(segment[0], segment[1], temp_output, transition, transition_duration)
            
            if merged is None:
                print(f"线程{threading.get_ident()} - 段 {segment_index} 处理失败")
                return {'success': False, 'segment_index': segment_index, 'error': '前两个视频合并失败'}
            
            # 处理段内剩余视频
            for j in range(2, len(segment)):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4', dir='.') as f:
                    next_temp = f.name
                    temp_files_segment.append(next_temp)
                
                merged = process_video_pair(merged, segment[j], next_temp, transition, transition_duration)
                if merged is None:
                    print(f"线程{threading.get_ident()} - 段 {segment_index} 处理失败")
                    return {'success': False, 'segment_index': segment_index, 'error': f'第{j+1}个视频合并失败'}
                
                # 删除不再需要的临时文件
                if os.path.exists(temp_output) and temp_output != merged:
                    os.remove(temp_output)
                temp_output = next_temp
            
            return {
                'success': True, 
                'segment_index': segment_index, 
                'output_file': merged,
                'temp_files': temp_files_segment
            }
        else:
            return {'success': False, 'segment_index': segment_index, 'error': '段内视频数量不足'}
            
    except Exception as e:
        print(f"线程{threading.get_ident()} - 段 {segment_index} 处理异常: {e}")
        return {'success': False, 'segment_index': segment_index, 'error': str(e)}


def _concatenate_videos_multithread_sequential(video_paths, output_path, transition, transition_duration, perf_info):
    """真正的多线程版本：并行处理段，按顺序收集结果，严格保持视频顺序"""
    
    # 计算合适的分段大小，确保不会过度分割
    total_videos = len(video_paths)
    num_threads = perf_info['recommended_threads']
    
    # 动态调整分段策略
    if total_videos <= num_threads * 2:
        # 视频数量较少，使用保守的分段大小
        segment_size = 2
    else:
        # 视频数量较多，可以适当增大分段大小
        segment_size = min(3, max(2, total_videos // num_threads))
    
    print(f"多线程策略: {total_videos}个视频, {num_threads}线程, 段大小={segment_size}")
    
    if os.path.exists(output_path):
        os.remove(output_path)

    try:
        temp_files = []
        current_files = video_paths.copy()
        failed_segments = []
        round_count = 0
        
        # 循环处理直到只剩一个文件
        while len(current_files) > 1:
            round_count += 1
            previous_files = current_files.copy()
            next_files = []
            
            # 准备段参数 - 严格按顺序，但不立即构建 next_files
            segment_args = []
            single_videos = []  # 记录单个视频及其位置
            
            for i in range(0, len(current_files), segment_size):
                segment = current_files[i:i + segment_size]
                segment_index = i // segment_size
                
                if len(segment) >= 2:  # 只处理需要合并的段
                    segment_args.append((segment, segment_index, transition, transition_duration))
                elif len(segment) == 1:
                    # 单独的视频段记录位置信息，稍后正确处理
                    print(f"段 {segment_index}: 记录单独视频 - {segment[0]} (位置{i})")
                    single_videos.append((i, segment[0]))
            
            # 多线程处理段
            if segment_args:
                print(f"第{round_count}轮: 处理{len(segment_args)}个段, 使用{num_threads}个线程")
                
                # 真正的多线程处理：使用线程池并行执行，但结果按顺序收集
                print(f"第{round_count}轮: 并行处理{len(segment_args)}个段，保证输出顺序")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                    # 提交所有任务
                    future_to_segment = {}
                    for args in segment_args:
                        segment_index = args[1]
                        print(f"线程池提交段 {segment_index}...")
                        future = executor.submit(_process_segment_multithread, args)
                        future_to_segment[segment_index] = future
                    
                    # 等待所有任务完成
                    print(f"等待 {len(future_to_segment)} 个并行任务完成...")
                    concurrent.futures.wait(future_to_segment.values())
                    
                    # 按原始顺序收集结果，确保视频顺序不变
                    ordered_results = {}
                    for segment_index in sorted(future_to_segment.keys()):
                        future = future_to_segment[segment_index]
                        try:
                            result = future.result(timeout=60)  # 添加超时防止死锁
                            ordered_results[segment_index] = result
                            
                            if result['success']:
                                temp_files.extend(result.get('temp_files', []))
                                print(f"✅ 段 {segment_index} 处理成功")
                            else:
                                print(f"❌ 段 {segment_index} 处理失败: {result['error']}")
                                failed_segments.append(result)
                        except concurrent.futures.TimeoutError:
                            print(f"❌ 段 {segment_index} 处理超时")
                            failed_segments.append({'success': False, 'segment_index': segment_index, 'error': '处理超时'})
                        except Exception as e:
                            print(f"❌ 段 {segment_index} 处理异常: {e}")
                            failed_segments.append({'success': False, 'segment_index': segment_index, 'error': str(e)})
                    
                    # ✅ 正确的重组逻辑：按原始位置顺序重建 next_files
                    next_files = []
                    i = 0
                    processed_segments = set()
                    
                    while i < len(current_files):
                        if i + segment_size <= len(current_files):
                            # 这是一个完整的段位置
                            segment_index = i // segment_size
                            
                            if segment_index in ordered_results and ordered_results[segment_index]['success']:
                                # 段处理成功，使用合并后的文件
                                next_files.append(ordered_results[segment_index]['output_file'])
                                processed_segments.add(segment_index)
                                print(f"✅ 位置{i}: 使用合并结果 段{segment_index}")
                            else:
                                # 段处理失败，使用原始视频片段
                                original_segment = current_files[i:i + segment_size]
                                next_files.extend(original_segment)
                                print(f"⚠️ 位置{i}: 使用原始片段 {original_segment}")
                            
                            i += segment_size
                        else:
                            # 剩余的单个视频
                            video_file = current_files[i]
                            next_files.append(video_file)
                            print(f"📹 位置{i}: 单独视频 {video_file}")
                            i += 1
                    
                    print(f"✅ 正确重组结果: {next_files}")
            
            current_files = next_files.copy()
            print(f"第{round_count}轮完成，剩余文件数: {len(current_files)}")

            # 所有分段均失败时，再重试同一组输入不会有进展。
            if current_files == previous_files:
                print("多线程合并未取得进展，立即降级到单线程模式")
                return _concatenate_videos_single_thread(
                    video_paths, output_path, transition, transition_duration)
            
            # 安全限制：防止无限循环
            if round_count > 10:
                print("警告：处理轮数过多，强制停止")
                break
        
        # 检查最终结果
        if len(current_files) == 1 and os.path.exists(current_files[0]):
            os.rename(current_files[0], output_path)
            print(f"✅ 多线程视频合并完成，输出路径: {output_path}")
        else:
            print("❌ 多线程处理失败，最终文件状态异常")
            # 降级到单线程模式
            print("降级到单线程模式...")
            return _concatenate_videos_single_thread(video_paths, output_path, transition, transition_duration)
        
        # 清理临时文件
        for file in temp_files:
            if os.path.exists(file) and file != output_path:
                try:
                    os.remove(file)
                except:
                    pass
        
        # 清除中间处理获取的片段
        for file_path in video_paths:
            if is_video_file(file_path) and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except:
                    print(f"无法删除: {file_path}")
                    
    except Exception as e:
        print(f"多线程合成视频出错: {e}")
        # 清理所有临时文件（包括失败的情况）
        print("清理多线程临时文件...")
        for file in temp_files:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass
        # 降级到单线程模式
        print("降级到单线程模式...")
        return _concatenate_videos_single_thread(video_paths, output_path, transition, transition_duration)


def _concatenate_videos_multithread_original(video_paths, output_path, transition, transition_duration, perf_info):
    """原始多线程版本（保留用于对比）"""
    # 这个函数保留了原始的并发逻辑，但不推荐使用，因为会导致顺序混乱
    # 如果需要真正的高性能并发，建议使用 _concatenate_videos_multithread_concurrent_safe 版本
    return _concatenate_videos_single_thread(video_paths, output_path, transition, transition_duration)


def _concatenate_videos_single_thread(video_paths, output_path, transition, transition_duration):
    """单线程版本的视频合并（原始实现）"""
    segment_size = 2
    
    if os.path.exists(output_path):
        os.remove(output_path)

    try:
        temp_files = []
        current_files = video_paths.copy()
        failed_segments = []

        # 循环处理直到只剩一个文件
        while len(current_files) > 1:
            next_files = []

            # 每次处理segment_size个视频
            for i in range(0, len(current_files), segment_size):
                segment = current_files[i:i + segment_size]

                if len(segment) == 1:
                    # 只剩一个视频，直接添加到下一轮
                    next_files.append(segment[0])
                    continue

                # 创建临时输出文件
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4', dir='.') as f:
                    temp_output = f.name
                    temp_files.append(temp_output)

                # 合并当前段的视频
                print(f"处理段 {i // segment_size + 1}/{(len(current_files) + segment_size - 1) // segment_size}: {segment}")

                try:
                    # 先处理前两个视频
                    merged = process_video_pair(segment[0], segment[1], temp_output, transition, transition_duration)
                    
                    if merged is None:
                        print(f"段 {i//segment_size + 1} 处理失败，跳过此段")
                        failed_segments.append(segment)
                        continue

                    # 处理段内剩余视频
                    for j in range(2, len(segment)):
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4', dir='.') as f:
                            next_temp = f.name
                            temp_files.append(next_temp)

                        merged = process_video_pair(merged, segment[j], next_temp, transition, transition_duration)
                        if merged is None:
                            print(f"段 {i//segment_size + 1} 处理失败，跳过此段")
                            failed_segments.append(segment)
                            break
                            
                        # 删除不再需要的临时文件
                        if os.path.exists(temp_output) and temp_output != merged:
                            os.remove(temp_output)
                        temp_output = next_temp
                    
                    if merged is not None:
                        next_files.append(merged)
                        
                except Exception as e:
                    print(f"段 {i//segment_size + 1} 处理异常: {e}")
                    failed_segments.append(segment)
                    continue

            current_files = next_files.copy()
            print(f"完成一轮处理，剩余文件数: {len(current_files)}")

        # 重命名最终输出文件
        if current_files and os.path.exists(current_files[0]) and len(failed_segments) == 0:
            os.rename(current_files[0], output_path)
            print(f"✅ 单线程视频合并完成，输出路径: {output_path}")
        else:
            print("❌ 没有生成最终视频")
            if failed_segments:
                print(f"失败的段数: {len(failed_segments)}")
            raise ValueError("视频合成失败")

        # 清理临时文件
        for file in temp_files:
            if os.path.exists(file) and file != output_path:
                try:
                    os.remove(file)
                except:
                    pass

        # 清除中间处理获取的片段
        for file_path in video_paths:
            if is_video_file(file_path) and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except:
                    print(f"无法删除: {file_path}")

    except Exception as e:
        print(f"单线程合成视频出错: {e}")
        # 清理所有临时文件（包括失败的情况）
        print("清理单线程临时文件...")
        for file in temp_files:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass
        raise


def crop_video(input_video, output_video, width, height):
    """裁剪视频以恢复原始尺寸"""
    command = [
        "ffmpeg",
        "-y",
        "-i", input_video,
        "-vf", f"crop={width}:{height}",
        "-c:a", "copy",
        output_video
    ]

    try:
        subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
        if os.path.exists(input_video):
            os.remove(input_video)
        print(f"已裁剪视频: {output_video}")
    except subprocess.CalledProcessError as e:
        print(f"裁剪视频出错: {e}")
        if os.path.exists(output_video):
            os.remove(output_video)


def extract_specific_frame(video_path, output_image_path, time=3):
    """
    截取视频指定时间的图片

    参数:
    - video_path: 输入视频文件路径
    - output_image_path: 输出图片文件路径
    - time: 截取的时间（秒）
    """
    try:
        # 标准化路径以确保兼容性
        normalized_video_path = os.path.normpath(video_path)
        normalized_output_image_path = os.path.normpath(output_image_path)
        
        command = [
            'ffmpeg',
            '-y',  # 覆盖输出文件
            '-i', normalized_video_path,
            '-ss', f'{time}',  # 开始时间
            '-vframes', '1',  # 只截取一帧
            '-q:v', '2',  # 图片质量
            normalized_output_image_path
        ]
        subprocess.run(command, creationflags=subprocess.CREATE_NO_WINDOW, timeout=60)
    except Exception as e:
        print(f'{str(e)}')


# def create_video_with_image_start(video_path, image_path, output_path, image_duration=0.2):
#     """
#     创建一个新视频，其开头展示指定图片
#
#     参数:
#     - video_path: 输入视频文件路径
#     - image_path: 输入图片文件路径
#     - output_path: 输出视频文件路径
#     - image_duration: 图片展示的时长（秒）
#     """
#     try:
#         command = [
#             'ffmpeg',
#             '-y',  # 覆盖输出文件
#             '-loop', '1',  # 循环图片
#             '-i', image_path,
#             '-i', video_path,
#             '-c:v', 'libx264',
#             '-preset', 'medium',
#             '-crf', '23',
#             '-shortest',
#             '-filter_complex',
#             f'[0:v]trim=duration={image_duration},setpts=PTS-STARTPTS[v0];'
#             f'[1:v]setpts=PTS-STARTPTS+{image_duration}/TB[v1];'
#             f'[v0][v1]concat=n=2:v=1:a=0',
#             output_path
#         ]
#         subprocess.run(command, creationflags=subprocess.CREATE_NO_WINDOW)
#     except Exception as e:
#         print(f'{str(e)}')
#

def create_video_with_image_start(video_path, image_path, output_path, image_duration=0.1):
    """
    创建一个新视频，其开头展示指定图片，图片展示部分为静音
    """
    try:
        sp.run([
            'ffmpeg', '-y',
            '-loop', '1', '-i', image_path,
            '-i', video_path,
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac',
            '-filter_complex',
            f'[0:v]trim=duration={image_duration},setpts=PTS-STARTPTS,setsar=1/1[v0];'
            f'[1:v]setpts=PTS-STARTPTS+{image_duration}/TB[v1];'
            f'[1:a]adelay={int(image_duration*1000)}|{int(image_duration*1000)}[a1];'
            f'[v0][v1]concat=n=2:v=1:a=0[out_video]',
            '-map', '[out_video]',
            '-map', '[a1]',
            '-shortest',
            output_path
        ], creationflags=sp.CREATE_NO_WINDOW, check=True)
    except sp.CalledProcessError as e:
        print('ffmpeg 报错：', e.stderr or e)
    except Exception as e:
        print('异常：', e)


def addCover(video_path, output_path, pic_time=2):
    output_image_path = 'cover.jpg'
    if os.path.exists(output_image_path):
        os.remove(output_image_path)
    extract_specific_frame(video_path, output_image_path, pic_time)
    create_video_with_image_start(video_path, output_image_path, output_path)


def extract_and_blur_random_frame(
    video_path,
    output_image_path,
    target_width=1080,
    target_height=1920,
    blur_sigma=10
):
    """
    从视频中随机时间点截取一帧图片，进行虚化和尺寸调整

    参数:
    - video_path: 输入视频文件路径
    - output_image_path: 输出图片文件路径
    - target_width: 目标宽度 (默认1080)
    - target_height: 目标高度 (默认1920)
    - blur_sigma: 虚化程度 (默认10，中度虚化)
    """
    try:
        # 标准化路径以确保兼容性
        normalized_video_path = os.path.normpath(video_path)
        normalized_output_image_path = os.path.normpath(output_image_path)

        # 如果输出文件已存在，先删除以确保重新生成
        if os.path.exists(normalized_output_image_path):
            try:
                os.remove(normalized_output_image_path)
                print(f'已删除旧背景图: {normalized_output_image_path}')
            except Exception as e:
                print(f'删除旧背景图失败: {str(e)}')

        # 第一步：获取视频时长
        duration_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            normalized_video_path
        ]
        result = subprocess.run(
            duration_cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=60
        )
        video_duration = float(result.stdout.strip())

        # 第二步：随机选择截取时间点 (避免太接近开头和结尾)
        import random
        min_time = max(1.0, video_duration * 0.1)  # 至少1秒，或10%处
        max_time = max(2.0, video_duration * 0.9)  # 最多90%处
        random_time = random.uniform(min_time, max_time)

        # 第三步：截取帧并应用虚化滤镜 + 尺寸调整
        # 使用 gblur 滤镜进行虚化(80%模糊效果)
        filter_complex = f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,gblur=sigma=20"

        command = [
            'ffmpeg',
            '-y',  # 覆盖输出文件
            '-ss', f'{random_time:.2f}',  # 随机时间点
            '-i', normalized_video_path,
            '-vframes', '1',  # 只截取一帧
            '-vf', filter_complex,  # 应用滤镜
            '-q:v', '2',  # 图片质量
            normalized_output_image_path
        ]

        # 执行 FFmpeg 命令并检查返回值
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=60
        )

        # 检查命令是否成功执行
        if result.returncode != 0:
            print(f'FFmpeg 执行失败: {result.stderr}')
            return False

        # 验证输出文件是否真的存在且非空
        if not os.path.exists(normalized_output_image_path):
            print(f'背景图生成失败: 文件不存在')
            return False

        file_size = os.path.getsize(normalized_output_image_path)
        if file_size == 0:
            print(f'背景图生成失败: 文件大小为0')
            os.remove(normalized_output_image_path)
            return False

        print(f'背景图生成成功: {normalized_output_image_path} ({file_size} bytes)')
        return True

    except Exception as e:
        print(f'截取并虚化图片失败: {str(e)}')
        return False



