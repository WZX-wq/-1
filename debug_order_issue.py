#!/usr/bin/env python3
"""
调试多线程顺序问题的脚本
"""

def debug_segmentation():
    """调试分段逻辑"""
    print("🔍 调试分段逻辑...")
    
    # 模拟不同数量的视频
    test_cases = [
        (4, 2),  # 4个视频，段大小2
        (5, 2),  # 5个视频，段大小2  
        (6, 2),  # 6个视频，段大小2
        (7, 3),  # 7个视频，段大小3
        (8, 3),  # 8个视频，段大小3
    ]
    
    for video_count, segment_size in test_cases:
        print(f"\n--- 测试: {video_count}个视频, 段大小={segment_size} ---")
        
        # 模拟视频列表
        videos = [f"video_{i}" for i in range(video_count)]
        print(f"原始视频: {videos}")
        
        # 当前的分段逻辑
        current_files = videos.copy()
        segment_args = []
        next_files = []
        
        for i in range(0, len(current_files), segment_size):
            segment = current_files[i:i + segment_size]
            segment_index = i // segment_size
            
            print(f"  段{segment_index}: {segment} (位置{i}-{i+len(segment)-1})")
            
            if len(segment) >= 2:
                segment_args.append((segment, segment_index))
            elif len(segment) == 1:
                next_files.append(segment[0])
        
        print(f"  分段参数: {[(args[1], args[0]) for args in segment_args]}")
        print(f"  直接加入下一轮: {next_files}")
        
        # 模拟处理完成后的重组
        final_files = next_files.copy()
        for i, (segment, index) in enumerate(segment_args):
            # 模拟每个段处理后的输出文件
            output_file = f"merged_segment_{index}"
            final_files.insert(index * 2 + len(next_files), output_file)  # 这里有问题！
            
        print(f"  重组后文件: {final_files}")
        print(f"  ⚠️  这里的插入位置计算可能有问题！")

def analyze_segment_index_issue():
    """分析分段索引问题"""
    print("\n🔍 分析分段索引问题...")
    
    # 问题场景：5个视频，段大小2
    videos = ["v1", "v2", "v3", "v4", "v5"]
    print(f"输入: {videos}")
    
    # 当前逻辑
    segment_size = 2
    segment_args = []
    next_files = []
    
    for i in range(0, len(videos), segment_size):
        segment = videos[i:i + segment_size]
        segment_index = i // segment_size
        
        if len(segment) >= 2:
            segment_args.append((segment, segment_index))
        elif len(segment) == 1:
            next_files.append(segment[0])
    
    print(f"分段args: {segment_args}")
    print(f"直接加入: {next_files}")
    
    # 重组逻辑问题
    print("\n❌ 当前重组逻辑的问题:")
    print("1. next_files 和 segment_args 的顺序混合")
    print("2. segment_args 中的索引是基于当前轮，不是最终位置")
    
    # 正确的逻辑应该是
    print("\n✅ 正确的重组逻辑:")
    current_pos = 0
    i = 0
    final_files = []
    
    while i < len(videos):
        if i + segment_size <= len(videos):
            # 完整的段
            segment = videos[i:i + segment_size]
            final_files.append(f"merged_{i // segment_size}")
            i += segment_size
        else:
            # 剩余的单个视频
            final_files.append(videos[i])
            i += 1
    
    print(f"正确结果: {final_files}")

if __name__ == "__main__":
    debug_segmentation()
    analyze_segment_index_issue()