import tempfile, os, subprocess

# 创建临时测试
with tempfile.TemporaryDirectory() as temp_dir:
    # 创建5秒视频
    video_path = os.path.join(temp_dir, 'test.mp4')
    cmd = ['ffmpeg', '-f', 'lavfi', '-i', 'testsrc2=duration=5:size=640x480:rate=30', '-c:v', 'libx264', '-preset', 'fast', '-y', video_path]
    subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    
    # 创建15秒音频（3倍时长）
    audio_path = os.path.join(temp_dir, 'test.mp3') 
    cmd = ['ffmpeg', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=15', '-c:a', 'libmp3lame', '-y', audio_path]
    subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    
    # 检查文件
    if os.path.exists(video_path) and os.path.exists(audio_path):
        print('✅ 测试文件创建成功')
        
        # 获取时长
        def get_duration(path):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', path]
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return float(result.stdout.strip())
        
        video_len = get_duration(video_path)
        audio_len = get_duration(audio_path)
        ratio = audio_len / video_len
        
        print(f'📊 视频时长: {video_len:.2f}秒')
        print(f'📊 音频时长: {audio_len:.2f}秒') 
        print(f'📊 比例: {ratio:.2f}x')
        
        if ratio > 2.0:
            print('🔄 应该使用循环策略')
        else:
            print('🐌 应该使用速度调整策略')
    else:
        print('❌ 测试文件创建失败')