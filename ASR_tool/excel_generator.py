import os
import pandas as pd
import json
import requests
from openai import OpenAI
import re
from openpyxl import Workbook, load_workbook


def deepseek_ai_strategy_title(title, api_key=None, api_url=None):
    """使用AI对标题进行分割，添加|分隔符"""
    try:
        if api_key:
            # 使用DeepSeek API
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的标题分割助手。你需要在标题的适当位置添加|符号来分割标题，使其更有层次感。"},
                    {"role": "user", "content": f"请在这个标题中添加|符号进行分割：{title}。例如：'从兴山到横峰'应该分割为'从兴山|到横峰'。只返回分割后的标题，不要解释。"}
                ],
                stream=False,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        elif api_url:
            # 使用本地API
            url = api_url.rstrip('/') + "/api/chat"
            payload = {
                "model": "deepseek-r1:7b",
                "messages": [
                    {"role": "system", "content": "你是一个专业的标题分割助手。你需要在标题的适当位置添加|符号来分割标题，使其更有层次感。"},
                    {"role": "user", "content": f"请在这个标题中添加|符号进行分割：{title}。例如：'从兴山到横峰'应该分割为'从兴山|到横峰'。只返回分割后的标题，不要解释。"}
                ],
                "stream": False,
                "temperature": 0.3
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, verify=False, timeout=60)
            
            if response.status_code == 200:
                result = json.loads(response.text)
                content = result['message']['content']
                if '</think>' in content:
                    content = content.split('</think>')[-1].strip()
                return content
        return title  # 如果AI调用失败，返回原标题
    except Exception as e:
        print(f"标题分割失败：{e}")
        return title


def deepseek_ai_strategy_topic(content, api_key=None, api_url=None):
    """基于内容生成话题标签"""
    try:
        if api_key:
            # 使用DeepSeek API
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的话题标签生成助手。"},
                    {"role": "user", "content": f"基于以下内容生成3-5个相关的话题标签，用逗号分隔：{content[:500]}..."}
                ],
                stream=False,
                temperature=0.3
            )
            return response.choices[0].message.content.strip().split(',')
        elif api_url:
            # 使用本地API
            url = api_url.rstrip('/') + "/api/chat"
            payload = {
                "model": "deepseek-r1:7b",
                "messages": [
                    {"role": "system", "content": "你是一个专业的话题标签生成助手。"},
                    {"role": "user", "content": f"基于以下内容生成3-5个相关的话题标签，用逗号分隔：{content[:500]}..."}
                ],
                "stream": False,
                "temperature": 0.3
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, verify=False, timeout=60)
            
            if response.status_code == 200:
                result = json.loads(response.text)
                content = result['message']['content']
                if '</think>' in content:
                    content = content.split('</think>')[-1].strip()
                return content.split(',')
        return ["通用话题"]  # 如果AI调用失败，返回默认话题
    except Exception as e:
        print(f"话题生成失败：{e}")
        return ["通用话题"]


def add_suffix_to_file_path(file_path, suffix):
    """为文件路径添加后缀"""
    base_name = os.path.splitext(file_path)[0]
    extension = os.path.splitext(file_path)[1]
    return f"{base_name}{suffix}{extension}"


def write_arrays_to_excel(file_path, data_list, append=True):
    """将数据写入Excel文件 - 横向排列格式"""
    import time
    import tempfile
    
    try:
        # 检查文件是否被占用
        if os.path.exists(file_path):
            try:
                # 尝试以写入模式打开文件来检查是否被占用
                with open(file_path, 'r+b'):
                    pass
            except PermissionError:
                # 文件被占用，生成新的文件名
                base_name = os.path.splitext(file_path)[0]
                extension = os.path.splitext(file_path)[1]
                timestamp = int(time.time())
                file_path = f"{base_name}_{timestamp}{extension}"
                print(f"⚠️ 原文件被占用，将保存为：{file_path}")
        
        # 如果文件存在且需要追加，加载现有工作簿
        if append and os.path.exists(file_path):
            try:
                workbook = load_workbook(file_path)
                sheet = workbook.active
                # 获取下一行的行号
                next_row = sheet.max_row + 1
            except Exception:
                # 如果加载失败，创建新工作簿
                workbook = Workbook()
                sheet = workbook.active
                next_row = 1
        else:
            # 创建新的工作簿或覆盖现有文件
            workbook = Workbook()
            sheet = workbook.active
            next_row = 1
        
        # 将数据写入新行
        for col_num, value in enumerate(data_list, 1):
            sheet.cell(row=next_row, column=col_num, value=value)
        
        # 尝试保存工作簿
        try:
            workbook.save(file_path)
            print(f"✅ 数据已写入：{file_path}")
        except PermissionError:
            # 如果权限不足，尝试保存到临时目录
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, os.path.basename(file_path))
            workbook.save(temp_file)
            print(f"⚠️ 原路径权限不足，已保存到临时目录：{temp_file}")
            
    except Exception as e:
        print(f"❌ 写入Excel失败：{e}")
        # 尝试保存到当前目录
        try:
            current_dir_file = os.path.join(os.getcwd(), os.path.basename(file_path))
            workbook.save(current_dir_file)
            print(f"🔄 已保存到当前目录：{current_dir_file}")
        except Exception as e2:
            print(f"❌ 保存到当前目录也失败：{e2}")


def clean_content(content):
    """清理文案内容，去掉标签和特殊符号"""
    # 去掉常见的标签
    content = re.sub(r'标题[:：]\s*', '', content)
    content = re.sub(r'内容[:：]\s*', '', content)
    content = re.sub(r'正文[:：]\s*', '', content)
    content = re.sub(r'文案[:：]\s*', '', content)
    content = re.sub(r'描述[:：]\s*', '', content)
    content = re.sub(r'简介[:：]\s*', '', content)
    
    # 去掉书名号
    content = re.sub(r'[《》]', '', content)
    
    # 去掉多余的空行和空格
    content = re.sub(r'\n\s*\n', '\n', content)
    content = content.strip()
    
    return content


def clean_tags(tags):
    """清理标签，去掉#号"""
    # 去掉#号
    tags = re.sub(r'#', '', tags)
    return tags


def remove_punctuation(text):
    """删掉文案中的标点符号，用空格代替"""
    # 定义中英文标点符号列表
    punctuation_chars = '，。！？；：""''（）【】《》、,.!?;:"\'()<>/\\'
    # 逐个替换标点符号
    for char in punctuation_chars:
        text = text.replace(char, ' ')
    # 去掉多余的空格
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_keywords_with_ai(text, api_key=None, api_url=None):
    """使用AI从文本中提取关键词"""
    try:
        # 构建更精确的prompt
        system_prompt = """你是一个专业的中文关键词提取助手。请严格按照以下要求提取关键词：
1. 从文本中提取3-5个最重要的关键词
2. 关键词必须是有意义的名词或名词短语
3. 避免提取无意义的文字片段
4. 优先提取地名、人名、概念词、主题词
5. 用逗号分隔，不要包含任何标点符号
6. 只返回关键词，不要解释"""

        user_prompt = f"""请从以下文本中提取关键词：
文本：{text[:300]}

要求：提取3-5个最重要的关键词，用逗号分隔，例如：兴山,横峰,历史文化,江西地理,山川形胜"""

        if api_key:
            print("🤖 正在使用AI提取关键词...")
            # 使用DeepSeek API
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=False,
                temperature=0.1  # 降低温度，提高一致性
            )
            keywords = response.choices[0].message.content.strip()
            
            # 清理关键词
            keywords = re.sub(r'[，。！？；：""''（）【】《》、.!?;:"\'()<>/\\\\]', '', keywords)
            keywords = keywords.replace(' ', '')  # 去掉空格
            
            # 验证结果
            if keywords and ',' in keywords:
                keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
                if len(keyword_list) >= 2:
                    print(f"✅ AI提取成功: {keywords}")
                    return keywords
            
            print("⚠️ AI返回格式不正确，使用备用方法")
            
        elif api_url:
            print("🤖 正在使用本地AI提取关键词...")
            # 使用本地API
            url = api_url.rstrip('/') + "/api/chat"
            payload = {
                "model": "deepseek-r1:7b",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "temperature": 0.1
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, verify=False, timeout=60)
            
            if response.status_code == 200:
                result = json.loads(response.text)
                content = result['message']['content']
                if '</think>' in content:
                    content = content.split('</think>')[-1].strip()
                
                # 清理关键词
                keywords = re.sub(r'[，。！？；：""''（）【】《》、.!?;:"\'()<>/\\\\]', '', content)
                keywords = keywords.replace(' ', '')
                
                # 验证结果
                if keywords and ',' in keywords:
                    keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
                    if len(keyword_list) >= 2:
                        print(f"✅ 本地AI提取成功: {keywords}")
                        return keywords
                
                print("⚠️ 本地AI返回格式不正确，使用备用方法")
            else:
                print(f"❌ 本地API调用失败，状态码：{response.status_code}")
                
    except Exception as e:
        print(f"❌ AI关键词提取失败：{e}")
    
    # 如果AI提取失败，回退到改进的备用方法
    print("🔄 回退到备用关键词提取方法")
    return extract_keywords_fallback(text)


def extract_keywords_fallback(text):
    """智能备用关键词提取方法（当AI不可用时）"""
    # 去掉标点符号和空格
    punctuation_chars = '，。！？；：""''（）【】《》、,.!?;:"\'()<>/\\ '
    clean_text = text
    for char in punctuation_chars:
        clean_text = clean_text.replace(char, '')
    
    if not clean_text:
        return ""
    
    # 常见有意义的词汇模式（优先匹配）
    meaningful_patterns = [
        # 地理相关
        r'[\u4e00-\u9fa5]*历史[\u4e00-\u9fa5]*', r'[\u4e00-\u9fa5]*文化[\u4e00-\u9fa5]*', 
        r'[\u4e00-\u9fa5]*地理[\u4e00-\u9fa5]*', r'[\u4e00-\u9fa5]*地名[\u4e00-\u9fa5]*',
        r'[\u4e00-\u9fa5]*山川[\u4e00-\u9fa5]*', r'[\u4e00-\u9fa5]*人文[\u4e00-\u9fa5]*',
        # 技术相关
        r'[\u4e00-\u9fa5]*技术[\u4e00-\u9fa5]*', r'[\u4e00-\u9fa5]*智能[\u4e00-\u9fa5]*',
        r'[\u4e00-\u9fa5]*科学[\u4e00-\u9fa5]*', r'[\u4e00-\u9fa5]*工程[\u4e00-\u9fa5]*',
        # 艺术相关
        r'[\u4e00-\u9fa5]*艺术[\u4e00-\u9fa5]*', r'[\u4e00-\u9fa5]*建筑[\u4e00-\u9fa5]*',
        r'[\u4e00-\u9fa5]*文学[\u4e00-\u9fa5]*', r'[\u4e00-\u9fa5]*音乐[\u4e00-\u9fa5]*',
        # 其他有意义词汇
        r'[\u4e00-\u9fa5]*社会[\u4e00-\u9fa5]*', r'[\u4e00-\u9fa5]*经济[\u4e00-\u9fa5]*',
        r'[\u4e00-\u9fa5]*政治[\u4e00-\u9fa5]*', r'[\u4e00-\u9fa5]*教育[\u4e00-\u9fa5]*'
    ]
    
    # 无意义词汇（过滤掉）
    stop_words = {'这是', '一个', '一段', '这里', '那里', '可以', '能够', '应该', '需要', 
                  '因为', '所以', '但是', '然而', '虽然', '如果', '当时', '现在', '以后',
                  '之前', '之后', '时候', '地方', '方面', '情况', '问题', '事情', '东西',
                  '或许', '就是', '不是', '还是', '只是', '就会', '会有', '有的', '的是'}
    
    keywords = set()
    
    # 1. 首先尝试匹配有意义的词汇模式
    for pattern in meaningful_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) >= 2 and match not in stop_words:
                keywords.add(match)
    
    # 2. 如果模式匹配不够，智能提取词组
    if len(keywords) < 3:
        # 提取常见的有意义词汇
        common_words = ['历史', '文化', '地理', '技术', '艺术', '社会', '经济', '政治', 
                       '教育', '科学', '建筑', '音乐', '文学', '哲学', '宗教', '传统',
                       '现代', '古代', '中国', '世界', '发展', '创新', '研究', '学习']
        
        for word in common_words:
            if word in text:
                keywords.add(word)
        
        # 提取地名（通常以山、河、城、县、市、省结尾）
        place_patterns = [r'[\u4e00-\u9fa5]+[山河城县市省区]', r'[\u4e00-\u9fa5]+峰']
        for pattern in place_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) >= 2:
                    keywords.add(match)
    
    # 3. 如果还是不够，提取4字有意义词组
    if len(keywords) < 3:
        for i in range(len(clean_text) - 3):
            word = clean_text[i:i+4]
            if (re.match(r'^[\u4e00-\u9fa5]+$', word) and 
                word not in stop_words and 
                len(set(word)) > 2):  # 至少包含3个不同字符
                keywords.add(word)
    
    # 4. 最后提取3字词组
    if len(keywords) < 3:
        for i in range(len(clean_text) - 2):
            word = clean_text[i:i+3]
            if (re.match(r'^[\u4e00-\u9fa5]+$', word) and 
                word not in stop_words and 
                len(set(word)) > 1):
                keywords.add(word)
    
    # 转换为列表，按意义和长度排序
    keyword_list = list(keywords)
    
    # 优先级排序：有意义的词汇 > 长词组 > 短词组
    def keyword_priority(word):
        # 检查是否包含有意义的核心词汇
        meaningful_cores = ['历史', '文化', '地理', '技术', '艺术', '社会', '经济', '政治', '教育']
        has_meaning = any(core in word for core in meaningful_cores)
        return (has_meaning, len(word), len(set(word)))
    
    keyword_list.sort(key=keyword_priority, reverse=True)
    
    # 限制数量并返回
    final_keywords = keyword_list[:5]
    return ','.join(final_keywords) if final_keywords else "文本,内容,信息,数据,资料"


def extract_keywords(text, api_key=None, api_url=None):
    """从文本中提取关键词的主函数"""
    # 如果有API配置，优先使用AI提取
    if api_key or api_url:
        return extract_keywords_with_ai(text, api_key, api_url)
    else:
        # 否则使用备用方法
        return extract_keywords_fallback(text)


def split_content_into_pairs(content):
    """将文案内容按两句话分组"""
    # 先清理内容
    content = clean_content(content)
    
    # 按句号、感叹号、问号分割句子
    sentences = re.split(r'[。！？]', content)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # 每两句话组成一组
    pairs = []
    for i in range(0, len(sentences), 2):
        if i + 1 < len(sentences):
            # 两句话组成一组
            pair = sentences[i] + '。' + sentences[i + 1] + '。'
        else:
            # 最后一句单独成组
            pair = sentences[i] + '。'
        
        # 去掉标点符号，用空格代替
        pair_clean = remove_punctuation(pair)
        pairs.append(pair_clean)
    
    return pairs


def process_corrected_texts(folder_path, account_name="", api_method="0"):
    """处理纠正后的文本文件并生成Excel"""
    
    # 获取API配置
    api_key = ""
    api_url = ""
    
    if api_method == "1":
        api_key = os.getenv("VIDEO_AI_API_KEY", "").strip()
        if not api_key:
            print("❌ 未配置 VIDEO_AI_API_KEY，AI 文案处理将跳过")
    elif api_method == "2":
        api_url = input("请输入本地API地址：")
    
    # 查找所有纠正后的文本文件
    corrected_files = [f for f in os.listdir(folder_path) if f.endswith('_corrected.txt')]
    
    if not corrected_files:
        print("未找到纠正后的文本文件（*_corrected.txt）")
        return
    
    print(f"找到 {len(corrected_files)} 个纠正后的文本文件")
    
    # 生成输出文件路径
    output_copy_path = os.path.join(folder_path, "generated_copy.xlsx")
    output_label_path = os.path.join(folder_path, "generated_label.xlsx")
    
    # 输出文件将被覆盖或追加
    print(f"输出文件路径：")
    print(f"文案文件：{output_copy_path}")
    print(f"标签文件：{output_label_path}")
    
    # 标记是否是第一次写入
    first_write = True
    
    for i, filename in enumerate(corrected_files):
        file_path = os.path.join(folder_path, filename)
        
        try:
            # 读取纠正后的文本
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                print(f"跳过空文件：{filename}")
                continue
            
            print(f"\n正在处理第 {i+1} 个文件：{filename}")
            
            # 从文件名提取原始标题
            base_title = filename.replace('_corrected.txt', '')
            
            # A列：原始标题（保持原格式，可能包含|符号）
            original_title = base_title
            
            # 清理标题用于AI处理
            clean_title = re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9\s]', '', base_title)
            
            # 使用AI对标题进行分割，添加|分隔符
            if api_method != "0":
                print("正在分割标题...")
                segmented_title = deepseek_ai_strategy_title(clean_title, api_key, api_url)
            else:
                segmented_title = clean_title
            
            # C列：复述标题（去掉|符号，连贯表达）
            restated_title = clean_title.replace('|', '').replace(' ', '')
            
            # 生成话题标签
            if api_method != "0":
                print("正在生成话题标签...")
                # 将标题和内容合并作为一个参数传递
                combined_content = f"标题：{clean_title}\n内容：{content[:500]}"
                if api_method == "1":
                    topic_list = deepseek_ai_strategy_topic(combined_content, api_key)
                else:
                    topic_list = deepseek_ai_strategy_topic(combined_content, None, api_url)
                ai_topic = ','.join([tag.strip() for tag in topic_list])
            else:
                # 基于标题生成默认标签
                ai_topic = f"{clean_title},旅游景点,必游胜地,自然人文"
            
            # 清理标签中的#号
            ai_topic = clean_tags(ai_topic)
            
            # D列及以后：将文案按两句话分组
            content_pairs = split_content_into_pairs(content)
            
            # 构建Excel行数据：[A列:分割标题, B列:标签, C列:复述标题, D列:文案1, E列:文案2, ...]
            excel_row_data = [segmented_title, ai_topic, restated_title] + content_pairs
            
            # 写入文案Excel
            write_arrays_to_excel(output_copy_path, excel_row_data, append=not first_write)
            
            # 生成标签数据：为每列提取关键词
            label_data = []
            
            # A列关键词：从分割标题提取
            if api_method != "0":
                print("正在提取标题关键词...")
            title_keywords = extract_keywords(segmented_title, api_key, api_url)
            label_data.append(title_keywords)
            
            # B列关键词：从标签中提取（已经是关键词了，直接使用）
            label_data.append(ai_topic)
            
            # C列关键词：从复述标题提取
            if api_method != "0":
                print("正在提取复述标题关键词...")
            restated_keywords = extract_keywords(restated_title, api_key, api_url)
            label_data.append(restated_keywords)
            
            # D列及以后：从每个文案段落提取关键词
            if api_method != "0":
                print("正在提取文案段落关键词...")
            for pair in content_pairs:
                pair_keywords = extract_keywords(pair, api_key, api_url)
                label_data.append(pair_keywords)
            
            write_arrays_to_excel(output_label_path, label_data, append=not first_write)
            
            # 标记已经不是第一次写入
            first_write = False
            
            print(f"完成处理：{filename}")
            print(f"A列-原始标题：{original_title}")
            print(f"B列-标签：{ai_topic}")
            print(f"C列-复述标题：{restated_title}")
            print(f"D列及以后-文案分组数：{len(content_pairs)}")
            
        except Exception as e:
            print(f"处理文件 {filename} 时出错：{e}")
    
    print(f"\n处理完成！")
    print(f"文案文件：{output_copy_path}")
    print(f"标签文件：{output_label_path}")


def main():
    print("=== 基于纠正文案生成Excel工具 ===")
    print("此工具读取text_corrector.py生成的纠正后文案，生成Excel内容结构")
    
    # 获取文件夹路径
    folder_path = input("\n请输入包含纠正后txt文件的文件夹路径（默认为当前目录）：").strip()
    if not folder_path:
        folder_path = os.getcwd()
    
    # 选择AI处理方法
    print("\n请选择AI处理方法：")
    print("0. 不使用AI（仅基础处理）")
    print("1. 使用DeepSeek API（需要API密钥）")
    print("2. 使用本地部署的AI模型")
    
    api_method = input("请输入选择（0/1/2）：").strip()
    
    if api_method not in ["0", "1", "2"]:
        print("无效选择，使用默认方法（不使用AI）")
        api_method = "0"
    
    # 开始处理（不再传递账户名）
    process_corrected_texts(folder_path, "", api_method)


if __name__ == "__main__":
    main()
