#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Edge TTS 快速验证测试"""
import asyncio
import sys
from edge_tts import Communicate

async def test():
    print("测试 Edge TTS (v7.2.7)...")

    try:
        # 使用最简单的配置
        communicate = Communicate(text="你好", voice="zh-CN-XiaoxiaoNeural")
        await asyncio.wait_for(communicate.save("test.mp3"), timeout=15)

        import os
        if os.path.exists("test.mp3"):
            print(f"[成功] 文件大小: {os.path.getsize('test.mp3')} 字节")
            os.remove("test.mp3")
            return True
    except Exception as e:
        print(f"[失败] {type(e).__name__}: {str(e)[:100]}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
    print(f"\n结果: {'Edge TTS 可用' if success else 'Edge TTS 不可用'}")
