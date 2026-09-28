import os
import json
import requests
from openai import OpenAI


def correct_text_with_deepseek_api(api_key, text, title=""):
    """使用DeepSeek API纠错文本"""
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的文本纠错助手。请修正文本中的错别字、语法错误和语音识别错误，同时删除所有互动文案和营销话语，保持核心内容不变。"},
                {"role": "user", 
                 "content": f"请纠正以下语音识别文本中的错误，包括：\n1. 错别字和同音字错误\n2. 标点符号错误\n3. 语法错误\n4. 语句不通顺的地方\n5. 删掉所有无关的互动文案，如'记得点赞关注评论'、'喜欢的话请关注'、'别忘了订阅'、'感谢观看'等类似内容\n6. 删掉所有营销性质的话语和呼吁行动的语句\n\n请保持原文的核心内容和风格，只输出纯净的正文内容，不要任何互动提示。\n\n原文：\n{text}\n\n纠正后的文本："}
            ],
            stream=False,
            temperature=0.1
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"DeepSeek API调用失败：{e}")
        return None


def correct_text_with_local_api(api_url, text, title=""):
    """使用本地部署的AI API纠错文本"""
    try:
        url = api_url.rstrip('/') + "/api/chat"
        payload = {
            "model": "deepseek-r1:7b",
            "messages": [
                {"role": "system", "content": "你是一个专业的文本纠错助手。请修正文本中的错别字、语法错误和语音识别错误，同时删除所有互动文案和营销话语，保持核心内容不变。"},
                {"role": "user", 
                 "content": f"请纠正以下文本中的错误，包括：\n1. 错别字和同音字错误\n2. 标点符号错误\n3. 语法错误\n4. 语句不通顺的地方\n5. 删掉所有无关的互动文案，如'记得点赞关注评论'、'喜欢的话请关注'、'别忘了订阅'、'感谢观看'等类似内容\n6. 删掉所有营销性质的话语和呼吁行动的语句\n\n请保持原文的核心内容和风格，只输出纯净的正文内容，不要任何互动提示。\n\n标题：{title}\n\n内容：{text}\n\n请只返回纠正后的文本内容，不要添加任何解释。"}
            ],
            "stream": False,
            "temperature": 0.1
        }
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, verify=False, timeout=60)
        
        if response.status_code == 200:
            result = json.loads(response.text)
            content = result['message']['content']
            # 如果包含思考过程，提取最终结果
            if '</think>' in content:
                content = content.split('</think>')[-1].strip()
            return content
        else:
            print(f"本地API调用失败，状态码：{response.status_code}")
            return None
    except Exception as e:
        print(f"本地API调用失败：{e}")
        return None


def process_text_files(folder_path, correction_method):
    """批量处理文件夹中的txt文件"""
    if not os.path.exists(folder_path):
        print(f"文件夹 {folder_path} 不存在")
        return
    
    # 获取API配置
    api_key = ""
    api_url = ""
    
    if correction_method == "1":
        # Use the configured key without storing credentials in source code.
        default_api_key = os.getenv("VIDEO_AI_API_KEY", "").strip()
        if not default_api_key:
            print("❌ 未配置 VIDEO_AI_API_KEY，请输入自定义 DeepSeek API 密钥")

        use_default = input("是否使用已配置的 API 密钥？(y/n，直接回车默认为y)：").strip().lower()
        if default_api_key and use_default in ['', 'y', 'yes', '是']:
            api_key = default_api_key
        else:
            api_key = input("请输入自定义DeepSeek API密钥：").strip()
            if not api_key:
                print("❌ API密钥不能为空")
                return
    elif correction_method == "2":
        # 使用默认本地API地址
        default_api_url = "http://localhost:11434"
        print(f"🌐 默认本地API地址：{default_api_url}")
        
        # 询问是否使用默认地址
        use_default = input("是否使用默认API地址？(y/n，直接回车默认为y)：").strip().lower()
        if use_default in ['', 'y', 'yes', '是']:
            api_url = default_api_url
        else:
            api_url = input("请输入自定义本地API地址：").strip()
            if not api_url:
                print("❌ API地址不能为空")
                return
    
    # 遍历文件夹中的txt文件
    txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    
    if not txt_files:
        print("文件夹中没有找到txt文件")
        return
    
    processed_count = 0
    failed_count = 0
    
    print(f"📊 开始批量处理 {len(txt_files)} 个txt文件")
    
    for i, filename in enumerate(txt_files, 1):
        file_path = os.path.join(folder_path, filename)
        
        # 显示进度
        print(f"\n📄 [{i}/{len(txt_files)}] 正在处理：{filename}")
        
        # 读取原始文本
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_text = f.read().strip()
            
            if not original_text:
                print(f"⚠️ 跳过空文件：{filename}")
                continue
            
            # 显示文件信息
            file_size = os.path.getsize(file_path) / 1024  # KB
            print(f"📏 文件大小：{file_size:.1f}KB | 文本长度：{len(original_text)} 字符")
            
            # 显示文本预览
            preview_text = original_text[:100].replace('\n', ' ')
            print(f"👀 内容预览：{preview_text}...")
            
            # 提取标题（文件名去掉扩展名）
            title = os.path.splitext(filename)[0]
            
            # 调用AI纠错
            print(f"🤖 正在使用{'DeepSeek API' if correction_method == '1' else '本地AI'}处理...")
            corrected_text = None
            if correction_method == "1":
                corrected_text = correct_text_with_deepseek_api(api_key, original_text, title)
            elif correction_method == "2":
                corrected_text = correct_text_with_local_api(api_url, original_text, title)
            
            if corrected_text:
                # 生成纠错后的文件名
                base_name = os.path.splitext(filename)[0]
                corrected_filename = f"{base_name}_corrected.txt"
                corrected_file_path = os.path.join(folder_path, corrected_filename)
                
                # 保存纠错后的文本
                with open(corrected_file_path, 'w', encoding='utf-8') as f:
                    f.write(corrected_text)
                
                # 显示结果
                print(f"✅ 纠错完成！已保存到：{corrected_filename}")
                print(f"📊 纠错后长度：{len(corrected_text)} 字符")
                
                # 显示纠错后的预览
                corrected_preview = corrected_text[:100].replace('\n', ' ')
                print(f"🔍 纠错预览：{corrected_preview}...")
                
                processed_count += 1
            else:
                print(f"❌ 文件 {filename} 纠错失败")
                failed_count += 1
                
        except Exception as e:
            print(f"❌ 处理文件 {filename} 时出错：{e}")
            failed_count += 1
    
    # 显示最终统计
    print(f"\n📈 处理完成统计：")
    print(f"✅ 成功处理：{processed_count} 个文件")
    if failed_count > 0:
        print(f"❌ 处理失败：{failed_count} 个文件")
    print(f"📁 输出目录：{folder_path}")


def main():
    print("\n=== 📝 文本纠错工具 ===")
    print("🎯 功能：纠正语音识别生成的txt文件中的错误")
    print("✨ 特点：自动删除互动文案和营销话语，保留核心内容")
    
    # 检查当前目录是否有txt文件
    current_dir = os.getcwd()
    current_txt_files = [f for f in os.listdir(current_dir) if f.endswith('.txt')]
    
    if current_txt_files:
        print(f"\n📂 当前目录发现 {len(current_txt_files)} 个txt文件：")
        for i, filename in enumerate(current_txt_files[:5], 1):  # 最多显示5个
            print(f"  {i}. {filename}")
        if len(current_txt_files) > 5:
            print(f"  ... 还有 {len(current_txt_files) - 5} 个文件")
        
        use_current = input("\n是否使用当前目录？(y/n，直接回车默认为y)：").strip().lower()
        if use_current in ['', 'y', 'yes', '是']:
            folder_path = current_dir
            print(f"✅ 使用当前目录：{folder_path}")
        else:
            folder_path = None
    else:
        print(f"\n📂 当前目录：{current_dir}")
        print("❌ 当前目录中没有txt文件")
        folder_path = None
    
    # 如果没有选择当前目录或当前目录没有txt文件，则要求用户输入路径
    if folder_path is None:
        while True:
            folder_path = input("\n📁 请输入包含txt文件的文件夹路径：").strip().strip('"\'')
            if not folder_path:
                print("❌ 路径不能为空")
                continue
            if os.path.exists(folder_path):
                # 检查是否有txt文件
                txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
                if txt_files:
                    print(f"✅ 找到 {len(txt_files)} 个txt文件")
                    break
                else:
                    print("❌ 该文件夹中没有txt文件，请重新选择")
            else:
                print(f"❌ 路径不存在：{folder_path}")
    
    # 选择纠错方法
    print("\n🤖 请选择AI纠错方法：")
    print("1. 💰 DeepSeek API（在线，效果最好，已配置默认密钥）")
    print("2. 🏠 本地部署AI模型（免费，需要本地服务）")
    print("0. ❌ 退出程序")
    
    while True:
        correction_method = input("\n请输入选择（0/1/2）：").strip()
        if correction_method in ["0", "1", "2"]:
            break
        else:
            print("❌ 无效选择！请输入 0、1 或 2")
    
    if correction_method == "0":
        print("👋 程序已退出")
        return
    
    # 开始处理
    try:
        print(f"\n🚀 开始处理，使用方法：{'DeepSeek API' if correction_method == '1' else '本地AI模型'}")
        process_text_files(folder_path, correction_method)
        print("\n🎉 所有文件处理完成！")
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 处理过程中出错：{e}")


if __name__ == "__main__":
    main()
