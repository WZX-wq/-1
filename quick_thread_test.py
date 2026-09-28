#!/usr/bin/env python3
"""
快速测试多线程是否真正并行工作
"""

import threading
import time
import concurrent.futures

def test_thread_pool():
    """测试线程池并行行为"""
    print("🧵 测试线程池并行行为...")
    
    def worker(task_id, duration=2):
        """工作函数"""
        thread_id = threading.get_ident()
        print(f"  [开始] 线程 {thread_id} 执行任务 {task_id}")
        time.sleep(duration)
        print(f"  [结束] 线程 {thread_id} 完成任务 {task_id}")
        return f"任务{task_id}_结果"
    
    # 创建3个任务，使用2个工作线程
    tasks = [0, 1, 2]
    max_workers = 2
    
    print(f"提交{len(tasks)}个任务到{max_workers}个线程池...")
    
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = [executor.submit(worker, task_id, 2) for task_id in tasks]
        
        print("等待任务完成...")
        # 等待所有任务完成
        concurrent.futures.wait(futures)
        
        # 收集结果
        results = []
        for i, future in enumerate(futures):
            result = future.result()
            results.append((i, result))
            print(f"收集结果 {i}: {result}")
    
    total_time = time.time() - start_time
    print(f"\n⏱️ 总耗时: {total_time:.2f}s")
    
    # 分析
    if total_time < 3.5:  # 理论上应该接近4秒（2个任务并行2秒 + 第3个任务2秒）
        print("✅ 观察到并行执行！")
        return True
    else:
        print("❌ 没有观察到并行执行（可能顺序执行）")
        return False

def test_video_concat_threading():
    """测试视频合并的多线程行为"""
    print("\n🎬 测试视频合并多线程行为...")
    
    # 模拟视频文件路径
    test_videos = [f"video_{i}.mp4" for i in range(6)]
    
    print(f"模拟视频列表: {test_videos}")
    
    # 检查性能检测
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent
    sys.path.append(str(project_root))
    
    try:
        from ffmpeg_tool.video_concat_tool import check_system_performance
        perf = check_system_performance()
        print(f"系统性能: {perf['cpu_count']}核, 推荐线程数: {perf['recommended_threads']}")
        print(f"是否使用多线程: {perf['is_high_performance'] and len(test_videos) >= 4}")
    except Exception as e:
        print(f"性能检测失败: {e}")

if __name__ == "__main__":
    print("="*50)
    print("快速多线程测试")
    print("="*50)
    
    # 测试线程池
    pool_works = test_thread_pool()
    
    # 测试视频合并设置
    test_video_concat_threading()
    
    print("\n" + "="*50)
    if pool_works:
        print("🎉 多线程环境正常！")
    else:
        print("⚠️  多线程可能存在问题")
    print("="*50)