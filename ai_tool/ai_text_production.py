# 调用Ai
import ast
import json
import os
import re
import jieba.posseg as psg
import requests
from ai_tool.runtime_config import create_ai_client
from openpyxl.reader.excel import load_workbook
from openpyxl.workbook import Workbook
import jieba

# 配置由 VIDEO_AI_API_KEY 或程序目录下的 video_ai_config.json 提供。
code = os.getenv("VIDEO_AI_API_KEY", "").strip()


# def deepseek_ai(title, text):
#     client = OpenAI(api_key=code, base_url="https://api.deepseek.com")
#
#     response = client.chat.completions.create(
#         model="deepseek-chat",
#         messages=[
#             {"role": "user",
#              # "content": f"这是一个视频的标题：{title}，视频要求是{text}，请根据标题和要求设计一段视频字幕文案，句子之间用空格隔开，视频需要开场和结束，开场只要一句话就是标题，结束有一句话并且不要包含点赞关注评论等话语，按视频每个地方转场将视频字幕文案拆分，一个转场对应一个字符串，包括开场结束各地方介绍按顺序组成字符串数组返回，内容是中文且不包含其他符号和换行"},
#              'content': f'这是一个视频的标题：{title}，视频要求是{text}，视频结构是：开场（1句） -> 地方1（名称+1句话）-> 地方2（名称+1句话）-> ... -> 结束（两句话），'
#                         f'开场1句话就是标题，结束语不要包含点赞关注评论等话语，只要点题且简单一点就行，结束语的两句话也是用空格隔开，这两句话是一个整体，'
#                         f'然后地方名称和地方介绍之间需要空格隔开，内容里面不需要标点符号，句子与句子中间用空格隔开，介绍语要符合标题，开场结束各地方介绍按顺序组成字符串数组返回', },
#         ],
#         stream=False
#     )
#     result = response.choices[0].message.content
#
#     # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
#     pattern = r'\[(.*?)\]'
#
#     # 查找所有匹配的数组字符串
#     match = re.search(pattern, result, re.DOTALL)
#
#     if match:
#         array_str = match.group(1)  # 获取匹配的数组字符串部分
#
#         # 尝试将匹配的字符串转换为 Python 列表
#         try:
#             array = json.loads(f'[{array_str}]')
#             print(array)
#             return array
#         except json.JSONDecodeError:
#             print("提取的字符串不是有效的 JSON 格式。")
#             return []
#     else:
#         print("未找到匹配的数组。")
#         return []

OpenAI = lambda **_kwargs: create_ai_client()
def deepseek_ai_intro_topic(text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"这是一个视频的标题：{text}，请总结这个视频发布时适合添加的话题标签，"
                        f"标签前不需要带#号，不要超过4个，然后将其组成字符串数组返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def deepseek_ai_strategy_topic(text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"这是一个视频的标题：{text}，请总结这个视频发布时适合添加的话题标签，标题涉及到的市级或县级的标准简称也要单独作为标签，标签前不需要带#号，不要超过4个，然后将其组成字符串数组返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def deepseek_ai_history_strategy_topic(text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"这是一个视频的标题：{text}，请总结这个视频发布时适合添加的话题标签，标题涉及到的市级或县级的标准简称也要单独作为标签，标签前不需要带#号，不要超过4个，然后将其组成字符串数组返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []

def deepseek_ai_strategy_scenic_topic(text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"这是一个视频的标题：{text}，请总结这个视频发布时适合添加的话题标签，标题涉及到的景点名称单独作为标签，标签前不需要带#号，不要超过4个，然后将其组成字符串数组返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []

def deepseek_ai_topic(text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"这是一个视频的标题：{text}，请总结这个视频发布时适合添加的话题标签，标签前不需要带#号，不要超过4个，然后将其组成字符串数组返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def deepseek_ai_first_tag(text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"这是一个视频的内容：{text}，请提取这个内容涉及到的地点人物事物的名词或名称，按视频内容展示的重要性排序，词前面不需要带#号，然后将其组成字符串数组返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def deepseek_ai_intro_tag(title, text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"这是视频标题：{title}，这是一个视频的内容：{text}，"
                        f"请提取这个视频内容涉及到主要的地点人物东西事物的名词或名称或要素，"
                        f"按视频内容展示的重要性排序，词一共不超过5个，词前面不需要带#号，"
                        f"然后将其组成字符串数组返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            array.insert(0,
                         array.pop(array.index(text.split(' ')[0])) if text.split(' ')[0] in array else text.split(' ')[
                             0])
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def deepseek_ai_intro_1_tag(title, text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"这是视频标题：{title}，这是一个视频的内容：{text}，"
                        f"请提取这个视频内容涉及到主要的地点人物东西事物的名词或名称或要素，"
                        f"按视频内容展示的重要性排序，词一共不超过5个，词前面不需要带#号，"
                        f"然后将其组成字符串数组返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def deepseek_ai_strategy_tag(title, text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        # messages=[
        #     {"role": "user",
        #      "content": f"这是视频标题{title}，这是一个视频的其中一段内容：{text}，"
        #                 f"请提取这段视频内容涉及到主要的地点人物东西事物的名词或名称或要素，"
        #                 f"按视频内容展示的重要性排序，一般是将与此内容相关的地方的名称放在前面，词一共不超过5个，"
        #                 f"如果该段视频内容没有提到任何地名，就把标题里的相关地名放到前面，词前面不需要带#号，"
        #                 f"然后将其组成字符串数组返回"},
        # ],
        messages=[
            {"role": "user",
             "content": f"这是视频标题{title}，"
                        f"请提取这段视频标题涉及到的主要县级行政区（标准简称)，只要提取一个"
                        f"然后将其放到字符串数组内返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def deepseek_ai_strategy_scenic_tag(title, text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"现在需要提取这段视频内容涉及到的词语，"
                        f"首先提取的第一个词必须是标题：‘{title}’中提取的景点名称，"
                        f"名称只保留景点纯名称，删除‘景区、风景区、旅游区、景点、园区、度假区、风景名胜区、国家5A、世界自然遗产’等所有后缀；"
                        f"若名称中出现上述词，一律截断去掉，不得留痕。"
                        f"再根据提供的这一段视频内容：‘{text}’，补充一些相关的地点人物东西事物的名词或名称或要素，补充的要素不要超过4个，"
                        f"然后将其放到字符串数组内返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def deepseek_ai_strategy_history_tag(title, text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"现在需要提取这段视频内容涉及到的词语，"
                        f"这是标题：‘{title}’，"
                        f"再根据提供的这一段视频内容：‘{text}’，请提取主要讲诉的故事主人翁是哪个省的，比如：安徽、江苏、广东等，"
                        f"然后将其放到字符串数组内返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def deepseek_ai_history_person(title):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"现在需要提取这段视频内容涉及到的词语，"
                        f"这是标题：‘{title}’，"
                        f"请提取主要讲诉的故事主人翁名字，比如标题是‘道光最硬核钦差林则徐’，提取的就是‘林则徐’，"
                        f"然后将其放到字符串数组内返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array[0]
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def deepseek_ai_scenic_tag(title, text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"现在需要提取这段视频内容涉及到的词语，"
                        f"根据提供的这一段视频内容：‘{text}’,提取的第一个词必须是内容相关景点名称，"
                        f"名称只保留景点纯名称，删除‘景区、风景区、旅游区、景点、园区、度假区、风景名胜区、国家5A、世界自然遗产’等所有后缀；"
                        f"若名称中出现上述词，一律截断去掉，不得留痕。"
                        f"补充一些相关的地点人物东西事物的名词或名称或要素，补充的要素不要超过4个，"
                        f"然后将其放到字符串数组内返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def segment_title(title: str, width: int = 7) -> str:
    """
    按词语折行，字不会拆散
    :param title: 原始标题
    :param width: 每行最多容纳的字符数（汉字算 1）
    :return: 已分段字符串，每行用换行符分隔
    """
    words = jieba.lcut(title)  # 先切成词语
    lines, cur = [], ''
    for w in words:
        # 如果当前行放不下，就换行
        if cur and (len(cur) + len(w)) > width:
            lines.append(cur.strip())
            cur = w
        else:
            cur += w
    if cur:
        lines.append(cur)
    print('|'.join(lines))
    return '|'.join(lines)


def deepseek_ai_intro_title(title):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        # messages=[
        #     {"role": "user",
        #      "content": f"这是视频标题：'{title}'，"
        #                 f"需要根据美观、词语连续性对这个标题进行分段，请你用|符号对这个标题进行分割，只分成三段，"
        #                 f"组成一个字符串，然后将这个字符串放到数组里，以数组形式返回"},
        # ],
        messages=[
            {"role": "user",
             "content": f"这是视频标题：'{title}'，"
                        f"需要对标题进行分段，请你用|符号对这个标题进行分割，分割段数不能超过三段，分多少段由字数多少决定，标题字数少就少分或者不分，"
                        f"而且分割的每段字数一定不能超过7个，字数多时分好的每段字数尽量平均相等，"
                        f"最后组成一个字符串，然后将这个字符串放到一个数组，数组里只有一个字符串，最后返回这个数组"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = ast.literal_eval(array_str)
            print(array)
            return str(array)
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return ''
    else:
        print("未找到匹配的数组。")
        return ''


# def deepseek_ai_strategy_title(title):
#     client = OpenAI(api_key=code, base_url="https://api.deepseek.com")
#
#     response = client.chat.completions.create(
#         model="deepseek-chat",
#         messages=[
#             {"role": "user",
#              # "content": f"这是视频标题：'{title}'，如果这个标题字数超15个字，需要将标题进行简化缩减，修改为陈述句，关键的景点名称最好出现在最后，不需要标点符号以及换行符，"
#              #            f"然后依据词语连续性对简化的标题进行分段，请你用|符号对简化的标题进行分隔，分隔总数不能超过三段，字数少可以分两段，景点整个名称单独作为为一段，"
#              #            f"但是每一段的字数不能超过7个，这个需要你在标题缩减时考虑好，最后组成一个字符串，然后将这个字符串放到一个数组，数组里只有一个字符串，最后返回这个数组"},
#              "content": f"这是视频标题：'{title}'，去除里面的标点符号和换行符，"
#                        f"需要对标题进行分段，请你用|符号对这个标题进行分割，分割段数不能超过三段，分多少段由字数多少决定，标题字数少就少分或者不分，"
#                        f"而且分隔好每段的字数不能超过8个，每一段段字数也要大致相等，最后一段最好是一个完整的话，"
#                        f"最后组成一个字符串，然后将这个字符串放到一个数组，数组里只有一个字符串，最后返回这个数组"},
#
#         ],
#         stream=False
#     )
#     result = response.choices[0].message.content
#
#     # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
#     pattern = r'\[(.*?)\]'
#
#     # 查找所有匹配的数组字符串
#     match = re.search(pattern, result, re.DOTALL)
#
#     if match:
#         array_str = match.group(1)  # 获取匹配的数组字符串部分
#
#         # 尝试将匹配的字符串转换为 Python 列表
#         try:
#             array = ast.literal_eval(array_str)
#             print(array)
#             return str(array)
#         except json.JSONDecodeError:
#             print("提取的标题格式错误。")
#             return []
#     else:
#         print("未找到匹配的数组。")
#         return []


# ---------- 新增：兜底再切 ----------
def _cut_once(seg: str, max_len: int = 8):
    """把一段字符串按 max_len 强制再切，优先在停顿词后切，否则硬切"""
    if len(seg) <= max_len:
        return [seg]
    # 常见语义间隙词，按出现顺序优先
    for pivot in ['的','了','在','去','和','与','跟','同','到','上','下','带','最']:
        pos = seg.rfind(pivot, 0, max_len + 1)
        if pos > 0:
            return [seg[:pos+1], seg[pos+1:]]
    # 找不到就硬切
    return [seg[:max_len], seg[max_len:]]

def _force_len(segs):
    """保证每段≤8 且总段数≤3"""
    # 1. 先逐个段检查
    new_segs = []
    for s in segs:
        new_segs.extend(_cut_once(s))
    # 2. 如果段数超 3，合并最短相邻段
    while len(new_segs) > 3:
        lens = [len(x) for x in new_segs]
        idx = min(range(len(lens)-1), key=lambda i: lens[i]+lens[i+1])
        new_segs[idx:idx+2] = [''.join(new_segs[idx:idx+2])]
    return '|'.join(new_segs)

def deepseek_ai_strategy_title(title: str):
    """
    调用 DeepSeek 对视频标题做「语义+字数」双重分段。
    返回：字符串形式的单元素数组，例 "['答应我这辈子|一定要带|最爱的人去一次三清山景区']"
    """
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")

    # 1. 去脏字符
    clean_title = re.sub(r"[，。！？；：、“”‘’\n\r]", "", title).strip()

    # 2. 构造系统级 prompt，让模型一次性输出合规数组
    system_prompt = (
        "你是中文标题分段专家。请严格按以下规则处理：\n"
        "1. 只能输出一段 Python 可解析的单元素数组，形如 ['a|b|c']，禁止任何解释、禁止换行、禁止多余空格。\n"
        "2. 分段策略：\n"
        "   - 总段数≤3；字数很少时可 2 段甚至 1 段。\n"
        "   - 每段字数≤8，且三段字数差距≤4。\n"
        "   - 优先在「语义角色」边界（主语/动作/结果）下刀，保证最后一段语义完整。\n"
        "3. 用 '|' 连接各段，不再出现其他标点，不能增加删改文字。"
    )

    user_prompt = f"标题：{clean_title}"

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1,   # 低温度保稳定
        stream=False
    )

    result = response.choices[0].message.content.strip()

    # 3. 提取数组
    match = re.search(r"\[(.*?)\]", result, re.S)
    if not match:
        return "[]"

    try:
        arr = ast.literal_eval(match.group(0))   # 直接解析完整数组
        first_cut = str(arr[0])  # DeepSeek 的第一刀
        segs = first_cut.split('|')
        final = _force_len(segs)  # 兜底再切
        print(final)
        return final
    except Exception:
        return "[]"


# 短祝福语
def deepseek_ai_greetings_1(morning_date):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"今天是阳历{morning_date}，请生成类似'福星高照生财道,吉日长临致富门'但不同的两行每日早安祝福语，如果是特殊日子需要符合当天的主题，每行祝福语最好是7"
                        f"个字，即2*7的格式，不用带任何符号包括换行，一行作为一个元素，分别放入数组进行返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


# 短祝福语
def deepseek_ai_greetings_2(morning_date):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"今天是阳历{morning_date}，请生成类似'福星高照生财道,吉日长临致富门'但不同的4行每日早安祝福语，如果是特殊日子需要符合当天的主题，每行祝福语最好是7"
                        f"个字，即4*7的格式，内容不用带任何符号包括换行，一行作为一个元素，分别放入数组进行返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


# 提取文案标题
def ai_extract_title(intro_text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": f"这是视频文案{intro_text}，请根据文案提取视频标题，标题字数不能超过18字，将这个标题放到数组中返回"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分

        # 尝试将匹配的字符串转换为 Python 列表
        try:
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


# 修正文案错误
def ai_fix_errors(title, text):
    client = OpenAI(api_key=code, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个文本修正助手。"},
            {"role": "user",
             "content": f"这是这段文案的标题：{title}，这是文案：{text}， 请你帮忙修改这段文案的错误，包括：\n1. 错别字和同音字错误\n2. 标点符号错误\n3. 语法错误\n4. 语句不通顺的地方\n5. 删掉所有无关的互动文案，如'记得点赞关注评论'、'喜欢的话请关注'、'别忘了订阅'、'感谢观看'等类似内容\n6. 删掉所有营销性质的话语和呼吁行动的语句\n\n请保持原文的核心内容和风格，只输出纯净的正文内容，不要任何互动提示。"
                        f"，需要修改其中错误，内容修改完后必须符合标题描述，将整个返回的结果放到数组中"},
        ],
        stream=False
    )
    result = response.choices[0].message.content

    # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
    pattern = r'\[(.*?)\]'

    # 查找所有匹配的数组字符串
    match = re.search(pattern, result, re.DOTALL)

    if match:
        array_str = match.group(1)  # 获取匹配的数组字符串部分
        return array_str
    else:
        print("未找到匹配的数组。")
        return []


def ai_analyse_title_special_tag(title, text):
    try:
        client = OpenAI(api_key=code, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个根据标题和文案对其关键词分析提取的工具。你需要根据标题和文案分析，"
                                              "从下面这些词中选择出标题文案中涉及的词语，词语有'冬天，大海，夜景'，"
                                              "如果没涉及就返回空"
                 },
                {"role": "user",
                 "content": f"这是这段文案的标题：{title}，这是文案内容：{text}，请返回与之相关的词语，每个词语作为一个元素，需要放在数组内返回"},
            ],
            stream=False,
            timeout=15
        )
        result = response.choices[0].message.content

        # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
        pattern = r'\[(.*?)\]'

        # 查找所有匹配的数组字符串
        match = re.search(pattern, result, re.DOTALL)

        if match:
            array_str = match.group(1)  # 获取匹配的数组字符串部分
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        else:
            print("未找到匹配的数组。")
            return []
    except Exception as e:
        print(f"封面匹配调用AI接口出错: {e}")
        return []


def ai_analyse_title_usual_tag(title, text):
    try:
        client = OpenAI(api_key=code, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个根据标题和文案对其关键词分析提取的工具。你需要根据标题和文案分析，"
                                              "从下面这些词中选择出标题文案中涉及的词语，词语有'春天,夏天,秋天,漂流,"
                                              "自驾,情侣,亲子,老人,夫妻,古镇,城市,博物馆,一个人,散步,公园,瀑布,"
                                              "雪,草原,云海,花,夜景,湖,日出,晚霞,山,沙滩,雨,城市,儿童,游乐园,峡谷,河,"
                                              "烟花,丹霞,公园,动物,避暑,寺庙,森林,荷花,桥,候鸟,古建筑,摩天轮,梯田'，"
                                              "选择好后进行返回，如果没涉及就返回空"
                 },
                {"role": "user",
                 "content": f"这是这段文案的标题：{title}，这是文案内容：{text}，请返回与之相关的词语，"
                            f"每个词语作为一个元素，需要放在数组内返回"},
            ],
            stream=False,
            timeout=15
        )
        result = response.choices[0].message.content

        # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
        pattern = r'\[(.*?)\]'

        # 查找所有匹配的数组字符串
        match = re.search(pattern, result, re.DOTALL)

        if match:
            array_str = match.group(1)  # 获取匹配的数组字符串部分
            array = json.loads(f'[{array_str}]')
            print(array)
            return array
        else:
            print("未找到匹配的数组。")
            return []
    except Exception as e:
        print(f"封面匹配调用AI接口出错: {e}")
        return []

# ai获取同义词,同地名的不同名称
def ai_get_synonym_words(word):
    """
    获取地名的同义词，带有超时保护机制
    
    Args:
        word (str): 要查询的地名
        
    Returns:
        list: 同义词列表，超时或失败时返回空列表
    """
    import threading
    import time
    
    # 超时处理类
    class AITimeoutException(Exception):
        pass
    
    def call_ai_api():
        """调用AI API的内部函数"""
        try:
            client = OpenAI(api_key=code, base_url="https://api.deepseek.com")
            
            # 设置请求超时
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user",
                     "content": f"请帮我找出与'{word}'这个地名的不同名称，"
                                f"这个名称可以是这个地方常用的正式名称、简称，但是不要外号，"
                                f"如果没有就返回空，每个词语作为一个元素，"
                                f"返回词语最多不能超过5个，不能重复，且不能包含原词，"
                                f"需要放在数组内返回"},
                ],
                stream=False,
                timeout=15  # 🔥 API请求超时15秒
            )
            
            result = response.choices[0].message.content
            
            # 正则表达式模式，匹配方括号内的 JSON 数组格式的字符串
            pattern = r'\[(.*?)\]'
            
            # 查找所有匹配的数组字符串
            match = re.search(pattern, result, re.DOTALL)
            
            if match:
                array_str = match.group(1)  # 获取匹配的数组字符串部分
                
                # 验证和解析JSON
                try:
                    array = json.loads(f'[{array_str}]')
                    # 确保是列表类型
                    if isinstance(array, list):
                        print(f"✅ AI同义词获取成功: {array}")
                        return array
                    else:
                        print(f"⚠️ AI返回格式错误: {array_str}")
                        return []
                except json.JSONDecodeError:
                    print(f"⚠️ AI返回JSON解析失败: {array_str}")
                    return []
            else:
                print("⚠️ AI返回内容未找到数组格式")
                return []
                
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                print(f"⏰ AI API请求超时: {error_msg}")
            else:
                print(f"❌ 调用AI接口出错: {error_msg}")
            return []
    
    try:
        # 使用线程执行AI调用，设置30秒总超时
        result_container = []
        exception_container = []
        
        def api_thread():
            try:
                result = call_ai_api()
                result_container.append(result)
            except Exception as e:
                exception_container.append(e)
        
        # 创建并启动API调用线程
        thread = threading.Thread(target=api_thread)
        thread.daemon = True  # 设为守护线程
        thread.start()
        
        # 等待线程完成，最多30秒
        thread.join(timeout=30)
        
        # 检查结果
        if exception_container:
            print(f"❌ AI调用线程异常: {exception_container[0]}")
            return []
        
        if thread.is_alive():
            print(f"⏰ ai_get_synonym_words 调用超时 (关键词: {word})")
            return []
        
        if result_container:
            return result_container[0]
        else:
            print(f"⚠️ ai_get_synonym_words 无返回结果 (关键词: {word})")
            return []
            
    except Exception as e:
        print(f"❌ ai_get_synonym_words 总体异常: {e}")
        return []

# 获取标题中的关键词
def title_keyword(title):
    words = [w.word for w in psg.cut(title)
             if w.flag.startswith('n')]
    print(','.join(words))
    return words


def write_arrays_to_excel(file_path, arrays):
    """
    将字符串数组写入 Excel 表格，每一行代表一个数组，数组中的每个元素分别写入一个单元格。
    如果文件已存在，每次写入会从最后一行的下一行开始，不会覆盖原有数据。

    参数：
        file_path: Excel 文件路径
        arrays: 包含字符串数组的列表
    """
    # 检查 arrays 是否为 None 或不可迭代
    if arrays is None:
        raise ValueError("arrays 参数不能为 None")
    if not isinstance(arrays, (list, tuple)):
        raise TypeError("arrays 参数必须是列表或元组")

    try:
        # 尝试加载已存在的 Excel 文件
        workbook = load_workbook(file_path)
        sheet = workbook.active
    except FileNotFoundError:
        # 如果文件不存在，创建一个新的 Excel 文件
        workbook = Workbook()
        sheet = workbook.active

    # 获取当前表格的最后一行
    last_row = sheet.max_row + 1

    # 从最后一行的下一行开始写入
    j = 1
    for i, array in enumerate(arrays):
        sheet.cell(row=last_row, column=j, value=array)
        j += 1

    # 保存文件
    workbook.save(file_path)
    print(f"数据已成功写入文件：{file_path}")


def add_suffix_to_file_path(file_path, suffix="_copy"):
    """
    在文件名后面添加指定的后缀，不改变文件路径和扩展名

    参数：
        file_path: 原始文件路径
        suffix: 要添加的后缀，默认为 "_copy"

    返回：
        修改后的文件路径
    """
    # 获取文件的目录、文件名和扩展名
    file_dir = os.path.dirname(file_path)  # 文件所在的目录
    file_name = os.path.basename(file_path)  # 文件名（包含扩展名）
    name, ext = os.path.splitext(file_name)  # 分离文件名和扩展名

    # 构造新的文件名
    new_file_name = f"{name}{suffix}{ext}"
    new_file_path = os.path.join(file_dir, new_file_name)

    return new_file_path


# deepseek_ai_strategy_title('导游不会带你去的角落才是金山岭的精髓')
