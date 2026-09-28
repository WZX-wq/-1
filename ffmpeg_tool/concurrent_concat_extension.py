import threading
import queue
import concurrent.futures
from typing import List, Dict, Any

def _concatenate_videos_multithread_concurrent_safe(video_paths, output_path, transition, transition_duration, perf_info):
    """
    真正安全的并发版本：使用队列保证顺序，多线程处理性能
    
    核心思想：
    1. 使用有序队列确保输出顺序
    2. 多线程并行处理不依赖的段
    3. 结果收集时严格按顺序重组
    """
    
    total_videos = len(video_paths)
    num_threads = perf_info['recommended_threads']
    segment_size = min(3, max(2, total_videos // num_threads))
    
    print(f"安全并发模式: {total_videos}个视频, {num_threads}线程, 段大小={segment_size}")
    
    if os.path.exists(output_path):
        os.remove(output_path)
    
    try:
        temp_files = []
        current_files = video_paths.copy()
        failed_segments = []
        round_count = 0
        
        # 结果队列：使用带索引的队列保证顺序
        result_queue = queue.PriorityQueue()
        
        # 循环处理直到只剩一个文件
        while len(current_files) > 1:
            round_count += 1
            next_files = []
            
            # 准备段参数
            segment_args = []
            for i in range(0, len(current_files), segment_size):
                segment = current_files[i:i + segment_size]
                segment_index = i // segment_size
                
                if len(segment) >= 2:
                    segment_args.append((segment, segment_index, transition, transition_duration))
                elif len(segment) == 1:
                    next_files.append(segment[0])
            
            # 多线程处理，但使用优先队列保证顺序
            if segment_args:
                print(f"第{round_count}轮: 并发处理{len(segment_args)}个段")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                    # 提交所有任务
                    future_to_index = {}
                    for args in segment_args:
                        segment_index = args[1]
                        future = executor.submit(_process_segment_multithread_safe, args)
                        future_to_index[segment_index] = future
                    
                    # 收集结果到优先队列
                    for segment_index, future in future_to_index.items():
                        try:
                            result = future.result()
                            # 使用索引作为优先级，确保顺序
                            result_queue.put((segment_index, result))
                        except Exception as e:
                            error_result = {
                                'success': False, 
                                'segment_index': segment_index, 
                                'error': str(e)
                            }
                            result_queue.put((segment_index, error_result))
                    
                    # 按顺序从队列中取出结果
                    while not result_queue.empty():
                        segment_index, result = result_queue.get()
                        
                        if result['success']:
                            temp_files.extend(result.get('temp_files', []))
                            next_files.append(result['output_file'])
                            print(f"✅ 段 {segment_index} 按顺序处理成功")
                        else:
                            print(f"❌ 段 {segment_index} 处理失败: {result['error']}")
                            failed_segments.append(result)
                            # 保持原始视频片段顺序
                            original_segment = segment_args[segment_index][0]
                            for video_file in original_segment:
                                next_files.append(video_file)
            
            current_files = next_files.copy()
            print(f"第{round_count}轮完成，剩余文件数: {len(current_files)}")
            
            if round_count > 10:
                print("警告：处理轮数过多，强制停止")
                break
        
        # 处理最终结果
        if len(current_files) == 1 and os.path.exists(current_files[0]):
            os.rename(current_files[0], output_path)
            print(f"✅ 安全并发视频合并完成，输出路径: {output_path}")
        else:
            print("❌ 安全并发处理失败，降级到单线程模式")
            return _concatenate_videos_single_thread(video_paths, output_path, transition, transition_duration)
        
        # 清理临时文件
        for file in temp_files:
            if os.path.exists(file) and file != output_path:
                try:
                    os.remove(file)
                except:
                    pass
        
        return True
        
    except Exception as e:
        print(f"安全并发合成视频出错: {e}")
        return _concatenate_videos_single_thread(video_paths, output_path, transition, transition_duration)


def _process_segment_multithread_safe(args):
    """
    线程安全的段处理函数
    添加了更详细的错误处理和资源管理
    """
    segment, segment_index, transition, transition_duration = args
    
    # 为每个线程创建独立的临时目录
    thread_id = threading.get_ident()
    thread_temp_dir = f"temp_thread_{thread_id}"
    os.makedirs(thread_temp_dir, exist_ok=True)
    
    try:
        temp_files_segment = []
        
        # 创建临时输出文件（线程安全）
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix='.mp4', 
            dir=thread_temp_dir,
            prefix=f"segment_{segment_index}_"
        ) as f:
            temp_output = f.name
            temp_files_segment.append(temp_output)
        
        print(f"线程{thread_id} - 开始处理段 {segment_index}: {len(segment)}个视频")
        
        # 处理段内视频（这部分是顺序的，无并发问题）
        if len(segment) >= 2:
            # 先处理前两个视频
            merged = process_video_pair(segment[0], segment[1], temp_output, transition, transition_duration)
            
            if merged is None:
                return {
                    'success': False, 
                    'segment_index': segment_index, 
                    'error': '前两个视频合并失败'
                }
            
            # 处理段内剩余视频
            for j in range(2, len(segment)):
                with tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix='.mp4', 
                    dir=thread_temp_dir,
                    prefix=f"segment_{segment_index}_step_{j}_"
                ) as f:
                    next_temp = f.name
                    temp_files_segment.append(next_temp)
                
                merged = process_video_pair(merged, segment[j], next_temp, transition, transition_duration)
                if merged is None:
                    return {
                        'success': False, 
                        'segment_index': segment_index, 
                        'error': f'第{j+1}个视频合并失败'
                    }
                
                # 删除不再需要的临时文件
                if os.path.exists(temp_output) and temp_output != merged:
                    os.remove(temp_output)
                temp_output = next_temp
            
            print(f"线程{thread_id} - 段 {segment_index} 处理完成")
            return {
                'success': True, 
                'segment_index': segment_index, 
                'output_file': merged,
                'temp_files': temp_files_segment
            }
        else:
            return {
                'success': False, 
                'segment_index': segment_index, 
                'error': '段内视频数量不足'
            }
            
    except Exception as e:
        print(f"线程{thread_id} - 段 {segment_index} 处理异常: {e}")
        return {
            'success': False, 
            'segment_index': segment_index, 
            'error': str(e)
        }
    finally:
        # 清理线程临时目录
        if os.path.exists(thread_temp_dir):
            try:
                for file in os.listdir(thread_temp_dir):
                    file_path = os.path.join(thread_temp_dir, file)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                os.rmdir(thread_temp_dir)
            except:
                pass


# 配置选项
CONCURRENT_CONFIGS = {
    'sequential': {
        'name': '顺序处理（推荐）',
        'function': '_concatenate_videos_multithread_sequential',
        'guarantees_order': True,
        'performance': 'Medium',
        'stability': 'High'
    },
    'concurrent_safe': {
        'name': '安全并发（高级）',
        'function': '_concatenate_videos_multithread_concurrent_safe',
        'guarantees_order': True,
        'performance': 'High',
        'stability': 'High'
    },
    'original': {
        'name': '原始并发（不推荐）',
        'function': '_concatenate_videos_multithread_original',
        'guarantees_order': False,
        'performance': 'High',
        'stability': 'Low'
    }
}