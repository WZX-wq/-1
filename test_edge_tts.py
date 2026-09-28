#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Edge TTS 连接测试脚本
用于测试 Edge TTS 服务是否可用
"""

import asyncio
import time
import os
from edge_tts import Communicate

# 测试文本列表
TEST_TEXTS = [
    "你好，世界",
    "今天天气真不错",
    "这是一个测试文本，用于验证Edge TTS是否正常工作",
    "Edge TTS is a text-to-speech service that uses the Microsoft Edge browser's online voices"
]

# 支持的中文声音
CHINESE_VOICES = [
    "zh-CN-XiaoxiaoNeural",  # 女声，语速适中
    "zh-CN-YunxiNeural",      # 男声
    "zh-CN-YunjianNeural",    # 男声
    "zh-CN-YunyangNeural",    # 男声
    "zh-CN-XiaoyiNeural",    # 女声
    "zh-CN-YunzeNeural",     # 男声
]


async def test_single_voice(text, voice_name, output_file):
    """测试单个声音"""
    print(f"\n{'='*60}")
    print(f"测试声音: {voice_name}")
    print(f"测试文本: {text[:50]}{'...' if len(text) > 50 else ''}")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        # 创建 Communicate 对象
        print(f"📝 正在创建语音对象...")
        communicate = Communicate(text=text, voice=voice_name, rate="+0%", pitch="+0Hz")

        # 生成语音并保存
        print(f"⏳ 正在生成语音...")
        await asyncio.wait_for(communicate.save(output_file), timeout=30)

        elapsed_time = time.time() - start_time

        # 检查文件是否成功生成
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ 成功生成语音文件: {output_file}")
            print(f"📦 文件大小: {file_size:,} 字节")
            print(f"⏱️ 耗时: {elapsed_time:.2f} 秒")
            return True, elapsed_time
        else:
            print(f"❌ 文件未生成: {output_file}")
            return False, 0

    except asyncio.TimeoutError:
        elapsed_time = time.time() - start_time
        print(f"❌ 超时错误: 生成语音超过30秒")
        print(f"⏱️ 耗时: {elapsed_time:.2f} 秒")
        return False, elapsed_time

    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ 发生错误: {type(e).__name__}")
        print(f"   错误信息: {str(e)}")
        print(f"⏱️ 耗时: {elapsed_time:.2f} 秒")
        return False, elapsed_time


async def test_all_voices():
    """测试所有声音"""
    print("\n" + "="*60)
    print("🎤 Edge TTS 连接测试")
    print("="*60)

    test_results = []

    # 测试每种声音
    for i, voice_name in enumerate(CHINESE_VOICES):
        output_file = f"test_voice_{i}_{voice_name}.mp3"

        # 删除已存在的测试文件
        if os.path.exists(output_file):
            os.remove(output_file)

        # 测试
        success, elapsed_time = await test_single_voice(TEST_TEXTS[i % len(TEST_TEXTS)], voice_name, output_file)

        test_results.append({
            'voice': voice_name,
            'success': success,
            'time': elapsed_time,
            'file': output_file
        })

        # 短暂延迟，避免请求过于频繁
        await asyncio.sleep(1)

    # 输出汇总
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)

    success_count = sum(1 for r in test_results if r['success'])
    total_count = len(test_results)
    avg_time = sum(r['time'] for r in test_results) / total_count if test_results else 0

    print(f"✅ 成功: {success_count}/{total_count}")
    print(f"❌ 失败: {total_count - success_count}/{total_count}")
    print(f"⏱️ 平均耗时: {avg_time:.2f} 秒")

    print("\n详细结果:")
    print("-" * 60)
    for i, result in enumerate(test_results, 1):
        status = "✅ 成功" if result['success'] else "❌ 失败"
        print(f"{i}. {result['voice']:<30} {status:<8} {result['time']:.2f}s")

    # 清理测试文件
    print("\n" + "="*60)
    print("是否删除测试文件? (y/n): ", end="", flush=True)
    # 注意：在非交互环境中，这个输入可能需要修改
    try:
        choice = input().strip().lower()
        if choice == 'y':
            for result in test_results:
                if os.path.exists(result['file']):
                    os.remove(result['file'])
                    print(f"🗑️ 已删除: {result['file']}")
        else:
            print("✋ 保留测试文件")
    except:
        print("\n⚠️ 非交互环境，保留测试文件用于检查")

    return success_count > 0


async def test_speed_variations():
    """测试不同语速"""
    print("\n" + "="*60)
    print("🚀 Edge TTS 语速测试")
    print("="*60)

    speeds = [
        ("+20%", "极快"),
        ("+10%", "快"),
        ("+0%", "正常"),
        ("-10%", "慢"),
        ("-20%", "极慢")
    ]

    test_voice = "zh-CN-XiaoxiaoNeural"
    test_text = TEST_TEXTS[1]

    print(f"测试声音: {test_voice}")
    print(f"测试文本: {test_text}")
    print("-" * 60)

    results = []

    for speed, desc in speeds:
        output_file = f"test_speed_{speed.replace('+', 'p').replace('-', 'm').replace('%', '')}.mp3"

        # 删除已存在的测试文件
        if os.path.exists(output_file):
            os.remove(output_file)

        print(f"\n测试语速: {speed} ({desc})")

        start_time = time.time()
        try:
            communicate = Communicate(text=test_text, voice=test_voice, rate=speed, pitch="+0Hz")
            await asyncio.wait_for(communicate.save(output_file), timeout=30)

            elapsed_time = time.time() - start_time

            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"✅ 成功 | 文件大小: {file_size:,} 字节 | 耗时: {elapsed_time:.2f}s")
                results.append({'speed': speed, 'desc': desc, 'time': elapsed_time, 'success': True})
            else:
                print(f"❌ 失败: 文件未生成")
                results.append({'speed': speed, 'desc': desc, 'time': 0, 'success': False})

        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"❌ 失败: {type(e).__name__} - {str(e)[:50]}")
            results.append({'speed': speed, 'desc': desc, 'time': elapsed_time, 'success': False})

        await asyncio.sleep(0.5)

    # 清理测试文件
    print(f"\n🗑️ 清理测试文件...")
    for speed, _ in speeds:
        file_name = f"test_speed_{speed.replace('+', 'p').replace('-', 'm').replace('%', '')}.mp3"
        if os.path.exists(file_name):
            os.remove(file_name)


async def test_network_connection():
    """测试网络连接"""
    print("\n" + "="*60)
    print("🌐 网络连接测试")
    print("="*60)

    import aiohttp

    urls = [
        ("https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1", "Edge TTS API"),
        ("https://www.bing.com", "Bing"),
        ("https://www.microsoft.com", "Microsoft")
    ]

    async with aiohttp.ClientSession() as session:
        for url, name in urls:
            print(f"\n测试连接: {name}")
            print(f"URL: {url}")

            start_time = time.time()
            try:
                async with session.get(url, timeout=10) as response:
                    elapsed_time = time.time() - start_time
                    print(f"✅ 成功 | 状态码: {response.status} | 耗时: {elapsed_time:.2f}s")

            except asyncio.TimeoutError:
                elapsed_time = time.time() - start_time
                print(f"❌ 超时 (10秒) | 耗时: {elapsed_time:.2f}s")

            except Exception as e:
                elapsed_time = time.time() - start_time
                print(f"❌ 失败: {type(e).__name__} - {str(e)[:50]} | 耗时: {elapsed_time:.2f}s")


async def main():
    """主测试函数"""
    print("\n" + "🎯"*30)
    print("  Edge TTS 完整测试套件")
    print("🎯"*30)

    # 1. 测试网络连接
    try:
        await test_network_connection()
    except ImportError:
        print("\n⚠️ 未安装 aiohttp，跳过网络连接测试")
        print("   安装命令: pip install aiohttp")
    except Exception as e:
        print(f"\n⚠️ 网络连接测试失败: {e}")

    # 2. 测试所有声音
    all_success = await test_all_voices()

    # 3. 测试语速变化
    if all_success:
        try:
            await test_speed_variations()
        except Exception as e:
            print(f"\n⚠️ 语速测试失败: {e}")

    # 最终结论
    print("\n" + "="*60)
    print("🎯 最终结论")
    print("="*60)

    if all_success:
        print("✅ Edge TTS 服务正常可用")
        print("\n💡 建议:")
        print("   1. 可以正常使用 Edge TTS 进行语音生成")
        print("   2. 推荐使用声音: zh-CN-XiaoxiaoNeural 或 zh-CN-YunxiNeural")
        print("   3. 默认语速: +0% (正常语速)")
        print("   4. 注意控制请求频率，避免被限流")
    else:
        print("❌ Edge TTS 服务不可用")
        print("\n🔍 可能的原因:")
        print("   1. 网络连接问题 - 请检查网络设置")
        print("   2. 防火墙阻止 - 请检查防火墙设置")
        print("   3. Edge TTS 服务故障 - 请稍后重试")
        print("   4. edge-tts 库版本问题 - 尝试更新: pip install --upgrade edge-tts")

    print("\n" + "="*60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试程序出错: {e}")
        import traceback
        traceback.print_exc()
