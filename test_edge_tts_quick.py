#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Edge TTS 快速测试脚本
快速验证 Edge TTS 是否可用
"""

import asyncio
import os
import sys
from edge_tts import Communicate

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


async def quick_test():
    """快速测试"""
    print("[Edge TTS] 快速测试")
    print("=" * 50)

    test_text = "你好，这是一个测试文本"
    voice_name = "zh-CN-XiaoxiaoNeural"
    output_file = "test_quick_tts.mp3"

    print(f"测试声音: {voice_name}")
    print(f"测试文本: {test_text}")
    print(f"输出文件: {output_file}")
    print("-" * 50)

    # 清理旧文件
    if os.path.exists(output_file):
        os.remove(output_file)

    try:
        print("[正在生成] 语音...")

        # 创建语音对象并生成
        communicate = Communicate(text=test_text, voice=voice_name, rate="+0%", pitch="+0Hz")

        # 30秒超时
        await asyncio.wait_for(communicate.save(output_file), timeout=30)

        # 检查结果
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print("[成功] 测试通过!")
            print(f"文件大小: {file_size:,} 字节")
            print(f"文件路径: {os.path.abspath(output_file)}")

            # 播放提示
            print("\n可以用播放器打开测试生成的语音文件")

            # 询问是否删除
            try:
                delete = input("\n是否删除测试文件? (y/n): ").strip().lower()
                if delete == 'y':
                    os.remove(output_file)
                    print("[已删除] 测试文件")
            except:
                print("\n保留测试文件")

            return True
        else:
            print("[失败] 文件未生成")
            return False

    except asyncio.TimeoutError:
        print("[失败] 超时 (30秒)")
        print("\n可能原因:")
        print("   - 网络连接问题")
        print("   - Edge TTS 服务响应慢")
        print("   - 防火墙阻止")
        return False

    except Exception as e:
        print(f"[失败] {type(e).__name__}")
        print(f"   错误信息: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(quick_test())

        print("\n" + "=" * 50)
        if success:
            print("[通过] Edge TTS 可用，可以正常使用")
        else:
            print("[警告] Edge TTS 不可用，请检查网络和配置")
        print("=" * 50)

    except KeyboardInterrupt:
        print("\n\n测试被中断")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
