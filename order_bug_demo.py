#!/usr/bin/env python3
"""
演示多线程顺序错误的具体问题
"""

def demonstrate_order_bug():
    """演示顺序错误的具体场景"""
    print("🐛 演示多线程顺序错误问题")
    print("="*60)
    
    # 场景：5个视频，段大小2
    videos = ["video1", "video2", "video3", "video4", "video5"]
    print(f"输入视频顺序: {videos}")
    
    # 当前错误的处理流程
    segment_size = 2
    current_files = videos.copy()
    segment_args = []
    next_files = []
    
    # 1. 分段（这部分是对的）
    for i in range(0, len(current_files), segment_size):
        segment = current_files[i:i + segment_size]
        segment_index = i // segment_size
        
        if len(segment) >= 2:
            segment_args.append((segment, segment_index))
        elif len(segment) == 1:
            # ❌ 问题：这里直接添加到 next_files
            next_files.append(segment[0])
    
    print(f"\n分段结果:")
    print(f"  需要合并的段: {[(i, seg) for seg, i in segment_args]}")
    print(f"  直接加入下一轮: {next_files}")
    
    # 2. 模拟多线程处理结果
    print(f"\n模拟多线程处理...")
    ordered_results = {}
    for segment_index, (segment, idx) in enumerate(segment_args):
        # 假设所有段都成功
        ordered_results[idx] = {
            'success': True,
            'output_file': f"merged_{idx}"
        }
    
    # 3. ❌ 问题所在：重组时的顺序
    print(f"\n❌ 错误的重组逻辑:")
    wrong_next_files = next_files.copy()  # 已经包含单独的视频
    for segment_index in sorted(ordered_results.keys()):
        result = ordered_results[segment_index]
        if result['success']:
            wrong_next_files.append(result['output_file'])  # 错误：append到末尾！
    
    print(f"  错误结果: {wrong_next_files}")
    print(f"  期望结果: ['merged_0', 'merged_1', 'video5']")
    print(f"  ❌ video5 跑到最后去了！")
    
    # 4. ✅ 正确的重组逻辑
    print(f"\n✅ 正确的重组逻辑:")
    correct_next_files = []
    i = 0
    while i < len(videos):
        if i + segment_size <= len(videos):
            # 这是一个完整的段
            segment_index = i // segment_size
            if segment_index in ordered_results and ordered_results[segment_index]['success']:
                correct_next_files.append(ordered_results[segment_index]['output_file'])
            else:
                # 失败的段，添加原始视频
                correct_next_files.extend(videos[i:i + segment_size])
            i += segment_size
        else:
            # 剩余的单个视频
            correct_next_files.append(videos[i])
            i += 1
    
    print(f"  正确结果: {correct_next_files}")
    print(f"  ✅ 顺序正确！")

def analyze_edge_cases():
    """分析边界情况"""
    print(f"\n" + "="*60)
    print("🔍 分析边界情况")
    print("="*60)
    
    test_cases = [
        (4, 2, ["v1", "v2", "v3", "v4"]),
        (5, 2, ["v1", "v2", "v3", "v4", "v5"]),
        (6, 2, ["v1", "v2", "v3", "v4", "v5", "v6"]),
        (7, 3, ["v1", "v2", "v3", "v4", "v5", "v6", "v7"]),
    ]
    
    for video_count, segment_size, videos in test_cases:
        print(f"\n测试: {video_count}个视频, 段大小{segment_size}")
        print(f"输入: {videos}")
        
        # 错误逻辑
        current_files = videos
        next_files = []
        segment_args = []
        
        for i in range(0, len(current_files), segment_size):
            segment = current_files[i:i + segment_size]
            if len(segment) >= 2:
                segment_args.append((segment, i // segment_size))
            else:
                next_files.append(segment[0])
        
        # 模拟成功处理
        ordered_results = {}
        for idx, (segment, seg_idx) in enumerate(segment_args):
            ordered_results[seg_idx] = {'success': True, 'output_file': f"merged_{seg_idx}"}
        
        # 错误重组
        wrong_result = next_files.copy()
        for seg_idx in sorted(ordered_results.keys()):
            wrong_result.append(ordered_results[seg_idx]['output_file'])
        
        print(f"  ❌ 错误结果: {wrong_result}")
        
        # 正确重组
        correct_result = []
        i = 0
        while i < len(videos):
            if i + segment_size <= len(videos):
                seg_idx = i // segment_size
                if seg_idx in ordered_results:
                    correct_result.append(ordered_results[seg_idx]['output_file'])
                else:
                    correct_result.extend(videos[i:i + segment_size])
                i += segment_size
            else:
                correct_result.append(videos[i])
                i += 1
        
        print(f"  ✅ 正确结果: {correct_result}")
        
        if wrong_result != correct_result:
            print(f"  🚨 顺序错误！")
        else:
            print(f"  ✅ 顺序正确")

if __name__ == "__main__":
    demonstrate_order_bug()
    analyze_edge_cases()