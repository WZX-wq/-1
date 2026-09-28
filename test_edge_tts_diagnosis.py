#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Edge TTS 诊断脚本
详细诊断 Edge TTS 连接问题
"""

import asyncio
import sys
import os

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


async def diagnose_edge_tts():
    """详细诊断"""

    print("=" * 70)
    print("Edge TTS 诊断报告")
    print("=" * 70)

    # 1. 检查 edge-tts 版本
    print("\n[1] 检查 edge-tts 版本")
    print("-" * 70)
    try:
        import edge_tts
        print(f"edge-tts 版本: {edge_tts.__version__ if hasattr(edge_tts, '__version__') else '未知'}")
    except ImportError:
        print("错误: edge-tts 未安装")
        print("安装命令: pip install edge-tts")
        return False

    # 2. 测试网络连接
    print("\n[2] 测试网络连接")
    print("-" * 70)
    try:
        import aiohttp

        urls_to_test = [
            "https://speech.platform.bing.com",
            "https://www.bing.com",
            "https://www.microsoft.com"
        ]

        async with aiohttp.ClientSession() as session:
            for url in urls_to_test:
                try:
                    async with session.get(url, timeout=5) as response:
                        print(f"[通过] {url}")
                        print(f"       状态码: {response.status}")
                except Exception as e:
                    print(f"[失败] {url}")
                    print(f"       错误: {type(e).__name__}")
    except ImportError:
        print("未安装 aiohttp，跳过网络测试")

    # 3. 测试不同的声音和参数
    print("\n[3] 测试不同的声音配置")
    print("-" * 70)

    from edge_tts import Communicate

    test_configs = [
        ("zh-CN-XiaoxiaoNeural", "+0%", "+0Hz", "默认配置"),
        ("zh-CN-XiaoxiaoNeural", "+10%", "+0Hz", "加速10%"),
        ("zh-CN-YunxiNeural", "+0%", "+0Hz", "男声"),
        ("en-US-JennyNeural", "+0%", "+0Hz", "英文女声"),
    ]

    test_text = "测试"

    for voice, rate, pitch, desc in test_configs:
        output_file = f"diagnostic_{voice}.mp3"
        if os.path.exists(output_file):
            os.remove(output_file)

        print(f"\n测试配置: {desc}")
        print(f"  声音: {voice}")
        print(f"  语速: {rate}")
        print(f"  音调: {pitch}")

        try:
            communicate = Communicate(text=test_text, voice=voice, rate=rate, pitch=pitch)
            await asyncio.wait_for(communicate.save(output_file), timeout=10)

            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"  [成功] 文件大小: {file_size} 字节")
                os.remove(output_file)
            else:
                print(f"  [失败] 文件未生成")

        except asyncio.TimeoutError:
            print(f"  [失败] 超时")
        except Exception as e:
            print(f"  [失败] {type(e).__name__}: {str(e)[:100]}")

        await asyncio.sleep(0.5)

    # 4. 测试简短文本
    print("\n[4] 测试不同长度的文本")
    print("-" * 70)

    texts = [
        ("A", "单字符"),
        ("你好", "中文短语"),
        ("Hello World", "英文短语"),
        ("这是一个测试文本，用于验证Edge TTS服务是否正常工作。", "中文句子"),
    ]

    for text, desc in texts:
        output_file = f"diagnostic_{len(text)}chars.mp3"
        if os.path.exists(output_file):
            os.remove(output_file)

        print(f"\n测试: {desc}")
        print(f"  文本: {text}")

        try:
            communicate = Communicate(text=text, voice="zh-CN-XiaoxiaoNeural", rate="+0%")
            await asyncio.wait_for(communicate.save(output_file), timeout=10)

            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"  [成功] 文件大小: {file_size} 字节")
                os.remove(output_file)
            else:
                print(f"  [失败] 文件未生成")

        except asyncio.TimeoutError:
            print(f"  [失败] 超时")
        except Exception as e:
            print(f"  [失败] {type(e).__name__}: {str(e)[:100]}")

        await asyncio.sleep(0.5)

    # 5. 详细错误信息
    print("\n[5] 详细错误信息")
    print("-" * 70)

    output_file = "diagnostic_detailed.mp3"
    if os.path.exists(output_file):
        os.remove(output_file)

    print("正在尝试生成详细的错误信息...")
    try:
        communicate = Communicate(text="测试", voice="zh-CN-XiaoxiaoNeural", rate="+0%")
        await communicate.save(output_file)
    except Exception as e:
        print(f"异常类型: {type(e).__name__}")
        print(f"异常信息: {str(e)}")

        # 检查是否是 HTTP 错误
        if hasattr(e, 'status_code'):
            print(f"HTTP 状态码: {e.status_code}")

        # 检查是否是 WebSocket 错误
        if hasattr(e, 'message'):
            print(f"错误消息: {e.message}")

        if hasattr(e, 'url'):
            print(f"请求URL: {e.url}")

    # 6. 结论和建议
    print("\n" + "=" * 70)
    print("诊断结论和建议")
    print("=" * 70)

    print("""
Edge TTS 返回 403 错误的可能原因:

1. IP 地址被限制
   - Edge TTS 可能检测到来自服务器的请求并阻止
   - 建议使用本地网络或更换IP

2. User-Agent 或 Headers 问题
   - edge-tts 库可能需要更新
   - 建议: pip install --upgrade edge-tts

3. 地域限制
   - 某些地区可能无法访问 Edge TTS
   - 建议使用 VPN 或代理

4. Token 过期
   - Edge TTS 使用的 Token 可能已失效
   - 建议: 更新 edge-tts 库

推荐的解决方案:

方案 1: 使用百度 TTS (已集成)
   - 优点: 稳定可靠，国内访问快
   - 缺点: 需要API密钥

方案 2: 更新 edge-tts 库
   pip install --upgrade edge-tts

方案 3: 使用其他 TTS 服务
   - Azure TTS
   - Google TTS
   - 讯飞 TTS

方案 4: 使用本地 TTS
   - 浏览器的 Web Speech API
   - 离线 TTS 引擎 (如 coqui-tts)
""")

    return False


if __name__ == "__main__":
    try:
        asyncio.run(diagnose_edge_tts())
    except KeyboardInterrupt:
        print("\n\n测试被中断")
    except Exception as e:
        print(f"\n\n诊断程序错误: {e}")
        import traceback
        traceback.print_exc()
