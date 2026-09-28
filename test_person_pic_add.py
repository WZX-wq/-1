#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试人物图片添加功能
"""

import os
import sys
from worker.add_person_pic_worker import AddPersonPicWorker
from PyQt6.QtCore import QThreadPool, QEventLoop, QObject, pyqtSignal


def test_add_person_pic():
    """测试人物图片添加功能"""
    print("=" * 60)
    print("测试人物图片添加功能")
    print("=" * 60)
    
    # 测试视频路径
    test_video = "test_preview_video0.mp4"
    if not os.path.exists(test_video):
        print(f"❌ 测试视频不存在: {test_video}")
        print("请先生成一个测试视频")
        return
    
    # 测试人物图片路径
    person_images_dir = os.path.join(os.getcwd(), 'person_images')
    
    # 查找person_images文件夹中的任意图片
    person_pic = None
    if os.path.exists(person_images_dir):
        for file in os.listdir(person_images_dir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                person_pic = os.path.join(person_images_dir, file)
                break
    
    if not person_pic or not os.path.exists(person_pic):
        print(f"❌ 未找到人物图片")
        print(f"📁 请在 {person_images_dir} 文件夹中添加人物图片")
        print("支持的格式: .png, .jpg, .jpeg")
        return
    
    print(f"✅ 测试视频: {test_video}")
    print(f"✅ 人物图片: {person_pic}")
    
    # 输出路径
    output_video = "test_with_person.mp4"
    
    # 创建事件循环（用于测试）
    class TestLoop(QEventLoop):
        pass
    
    loop = TestLoop()
    
    # 创建 Worker
    worker = AddPersonPicWorker(
        input_video_path=test_video,
        person_pic_path=person_pic,
        output_video_path=output_video,
        position="center"
    )
    
    # 连接信号
    class SignalHandler(QObject):
        def __init__(self):
            super().__init__()
            self.success = False
            self.error_msg = ""
        
        def on_finished(self, result):
            print(f"\n✅ 成功: {result}")
            self.success = True
            loop.quit()
        
        def on_error(self, error_msg):
            print(f"\n❌ 错误: {error_msg}")
            self.error_msg = error_msg
            self.success = False
            loop.quit()
    
    handler = SignalHandler()
    worker.signals.finished.connect(handler.on_finished)
    worker.signals.errorOccurred.connect(handler.on_error)
    
    # 启动 Worker
    thread_pool = QThreadPool.globalInstance()
    thread_pool.start(worker)
    
    # 执行事件循环
    loop.exec()
    
    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    
    if handler.success and os.path.exists(output_video):
        file_size = os.path.getsize(output_video)
        print(f"✅ 人物图片添加成功")
        print(f"📦 输出文件: {output_video}")
        print(f"📏 文件大小: {file_size:,} 字节")
        print("\n可以用播放器打开查看效果")
    else:
        print(f"❌ 人物图片添加失败")
        if handler.error_msg:
            print(f"错误信息: {handler.error_msg}")
        if not os.path.exists(output_video):
            print("输出文件未生成")


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    # 创建QApplication
    app = QApplication(sys.argv)
    
    try:
        test_add_person_pic()
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n按任意键退出...")
    input()
