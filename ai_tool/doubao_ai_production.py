import json
import os
import random
import re

from ai_tool.runtime_config import create_ai_client, get_ai_config

# Keep the historical constants and function names for compatibility with the
# worker modules.  The client now targets the configured OpenAI-compatible
# endpoint (DeepSeek by default), never the closed Volcengine endpoint.
ARK_API_KEY = os.getenv("VIDEO_AI_API_KEY", "")
MODEL_NAME = os.getenv("VIDEO_AI_MODEL", "deepseek-flash")
MODEL_THINK_NAME = MODEL_NAME


def _client():
    return create_ai_client()


# Existing functions below call OpenAI(...). Preserve that surface while
# routing every call through the central runtime configuration.
def OpenAI(**_kwargs):
    return _client()


def _normalize_text_list(value):
    """Normalize model JSON arrays before callers join or persist them.

    Some compatible endpoints occasionally return an object such as
    ``{"word": "三清山"}`` for an array element even though the prompt asks
    for strings.  Keeping that object out of the rest of the pipeline avoids
    ``sequence item ... expected str instance`` failures during label and
    subtitle generation.
    """
    if value is None:
        return []
    if isinstance(value, (str, dict)):
        value = [value]
    if not isinstance(value, (list, tuple)):
        value = [value]

    normalized = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = ""
            for key in ("word", "text", "content", "name", "description", "value"):
                candidate = item.get(key)
                if candidate is not None:
                    text = str(candidate).strip()
                    if text:
                        break
            if not text:
                text = " ".join(str(part).strip() for part in item.values() if part is not None).strip()
        else:
            text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def douBao_ai_sr_intro_content(title, text):
    client = OpenAI()
    lead_model_list = [
        '导语的第一句要这样的句式：******个，第二句句式：到过*个**算的上***',
        '导语的第一句要这样的句式：其中*****，第二句句式：***一定***',
        # '导语的第一句要这样的句式：去过*个你就是*****，第二句句式：去过*个更是*****，第三句句式：快来看看你***',
        '导语的第一句要这样的句式：其中******，第二句句式：尤其******',
        '导语的第一句要这样的句式：你知道几个，第二句句式：特别******',
        '导语的第一句要这样的句式：到过*个此生无憾，第二句句式：特别是最后一个',
        '导语的第一句要这样的句式：去过一半，第二句句式：此生无憾',
        '导语的第一句要这样的句式：看看你去过几个，第二句句式：这份攻略以后肯定用的上',

        '导语的第一句要这样的句式：让我们一起看看，第二句句式：盘点这些******',
        '导语的第一句要这样的句式：这些******，第二句句式：你都去过吗',
        '']
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[  #random.choice(lead_model_list)
            {"role": "user",
             'content': f'这是一个视频的标题：{title}，视频要求是{text}，'
                        f'视频结构是：开场（3句） -> 地方或东西1（名称+1句话）-> 地方或东西2（名称+1句话）-> ... -> 结束（两句话），'
                        f'开场有4句话就是视频标题加上两句开场导语，{random.choice(lead_model_list)}，这开头4句话是一个整体，用空格隔开，句式可以根据标题适当的变化'
                        f'，结束语不要包含点赞关注评论等话语，只要点题且简单一点就行，结束语的两句话也是用空格隔开，这结束两句话也是一个整体，用空格隔开'
                        f'，然后地方或东西的名称和地方或东西的介绍之间需要空格隔开，内容里面不需要标点符号，句子与句子中间用空格隔开，介绍语要符合标题，开场结束各地方的介绍每个作为字符串元素按顺序放到数组内返回'},
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
            return _normalize_text_list(array)
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def douBao_ai_intro_content(title, text):
    client = OpenAI()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user",
            'content': f'这是一个视频的标题：{title}，视频要求是{text}，视频结构是：开场（2句） -> 地方或东西1（名称+1句话）-> 地方或东西2（名称+1句话）-> ... -> 结束（两句话），开场只有两句话就是视频标题加上一句夸张的导语，这句导语不能超过15字，这开头两句话是一个整体，用空格隔开，结束语不要包含点赞关注评论等话语，只要点题且简单一点就行，结束语的两句话也是用空格隔开，这结束两句话也是一个整体，用空格隔开，然后地方或东西的名称和地方或东西的介绍之间需要空格隔开，内容里面不需要标点符号，句子与句子中间用空格隔开，介绍语要符合标题，开场结束各地方介绍按顺序组成字符串数组返回', },
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
            return _normalize_text_list(array)
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def douBao_ai_dispose_intro_content(title, text):
    client = OpenAI()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user",
             # "content": f"这是一个视频的标题：{title}，视频要求是{text}，请根据标题和要求设计一段视频字幕文案，句子之间用空格隔开，视频需要开场和结束，开场只要一句话就是标题，结束有两句话并且不要包含点赞关注评论等话语，按视频每个地方转场将视频字幕文案拆分，每个地方文案开头必须是这个地方的名称，名称后面加一个空格，一个转场对应一个字符串，包括开场结束各地方介绍按顺序组成字符串数组返回，内容是中文且不包含其他符号和换行"},
             'content': f'这是一个视频的标题：{title}，视频要求是{text}，视频结构是：开场（标题+导语） -> 地方或东西1（名称+几句话）-> 地方或东西2（名称+几句话）-> ... -> 结束（两句话），开场就是视频标题加上导语部分，标题是一句话，中间用空格隔开，结束语不要包含点赞关注评论等话语，只要点题且简单一点就行，结束语的两句话也是用空格隔开，这结束两句话也是一个整体，用空格隔开，然后地方或东西的名称和地方或东西的介绍之间需要空格隔开，内容里面不需要标点符号，句子与句子中间用空格隔开，介绍语要符合标题，开场结束各地方介绍按顺序组成字符串数组返回', },
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
            return _normalize_text_list(array)
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def douBao_ai_strategy_content(title, text):
    """
    生成图片攻略类/本地攻略类文案
    返回格式: ["开场标题", "内容段落1", "内容段落2", ..., "结束语"]
    """
    client = OpenAI()

    prompt_content = f"""
    任务：根据短视频标题生成视频字幕文案数组，严格遵循以下规则：
    【重要】输出必须是纯JSON数组，不要有任何其他文字、markdown标记或说明。
    
    1. 输出格式要求（必须严格遵守）：
       - 仅返回标准JSON数组，以[开头，以]结尾
       - 数组内每个元素是一个字符串，使用双引号包裹
       - 无其他多余文字、解释、备注或markdown代码块标记
       - JSON必须可被Python的json.loads()直接解析
    
    2. 视频结构要求：
       - 开场：1句话作为标题/开场，吸引观众注意
       - 中间内容：根据标题{text}要求，分段介绍相关内容
       - 结尾：2句话作为结束语，总结或引导互动
    
    3. 内容格式要求：
       - 开场标题作为数组第一个元素
       - 结尾的2句话分别作为数组最后两个元素
       - 中间内容分成多段，每段不超过30字
       - 内容里面不需要标点符号，逗号句号用空格替换
       - 介绍语要符合标题主题，语言生动有趣
       - 数组总元素数量控制在6-10个为宜
    
    4. 【关键】JSON格式检查清单：
       - 所有字符串用双引号""包裹，不要用单引号
       - 不要在字符串内部使用双引号，如需使用请转义
       - 不要在JSON中包含换行符或特殊控制字符
       - 数组和字符串的括号必须正确闭合
       - 数组元素之间用逗号分隔
    
    5. 标题和输入信息：
       - 标题：{title}
       - 要求：{text}
    
    示例输出格式：
    ["开场标题内容", "第一段介绍内容", "第二段介绍内容", "第三段介绍内容", "结束语第一句", "结束语第二句"]
    
    请直接返回JSON数组，不要添加任何其他说明文字。
    """

    response = client.chat.completions.create(
        model=MODEL_THINK_NAME,
        messages=[
            {"role": "user", "content": prompt_content},
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
            return _normalize_text_list(array)
        except json.JSONDecodeError as e:
            print(f"提取的字符串不是有效的 JSON 格式: {e}")
            print(f"问题字符串: [{array_str[:200]}...]")
            return []
    else:
        print("未找到匹配的数组。")
        print(f"原始返回: {result[:200]}...")
        return []


def douBao_ai_qa_content(title, text):
    client = OpenAI()
    content_model_request_list = [
        '给一个视频脚本：A负责问，B负责答，几轮小对话，只需要一段开场对话和一段结束对话，中间其他都是介绍景点的对话，结构是：一段开场对话+内容对话+....+内容对话+一段结束对话，A的追问需要自然一点，B的回答句子需要简短且有趣一点，对话前面需要用A:B:表明角色，A与B之间的每一段对话作为数组的一个元素，比如A:...... B:......，每段对话精短一些，每段介绍景点的对话只涉及一个景点，最后返回这个数组，数组结构如下：["A:...... B:......","A:...... B:......",...]',
    ]
    response = client.chat.completions.create(
        model=MODEL_THINK_NAME,
        messages=[
            {"role": "user",
             'content': f'这是一个短视频的标题：{title}，短视频要求是{text}，'
                        f'给一个视频脚本：A负责问，B负责答，几轮小对话，只需要一段开场对话和一段结束对话，中间其他都是介绍景点的对话，'
                        f'结构是：一段开场对话+内容对话+....+内容对话+一段结束对话，A的追问需要自然一点，B的回答句子需要简短且有趣一点，'
                        f'对话前面需要用A:B:表明角色，A与B之间的每一段对话作为数组的一个元素，比如A:...... B:......，每段对话精短一些，'
                        f'每段介绍景点的对话只涉及一个景点，最后返回这个数组，数组结构如下：["A:...... B:......","A:...... B:......",...]'},
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
            return _normalize_text_list(array)
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def douBao_ai_life_strategy_content(title):
    client = OpenAI()

    response = client.chat.completions.create(
        model=MODEL_THINK_NAME,
        messages=[
            {"role": "user",
             'content': f'写一段与"{title}"相关心灵鸡汤的经典励志语录，字数在100字左右，并以两个字概括相关主题，这两个字作为第一个元素，而文案中每一句话单独作为一个元素，一句话不要超过30字，这些元素按顺序元素放到数组里返回'},
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
            return _normalize_text_list(array)
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def douBao_ai_title(title):
    client = OpenAI()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user",
             "content": f"这是竖屏视频标题{title}，需要分段放在封面上，如果几个字开头是地方名称比如地名就得单独分隔出来，这段除了地名或景点名称不能包含其他词语，"
                        f"其他段还需要根据美观、词语连续性进行分段，每段中间用|符号分割，只分成三段，还有每段文字不易过长"
                        f"组成一个字符串，然后将这个字符串放到数组返回，字符串不能添加和删除文字，所以数组只有一个元素"},
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
            return _normalize_text_list(array)
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def douBao_ai_topic(text):
    client = OpenAI()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user",
             "content": f"这是一个视频的内容：{text}，请总结这个视频发布时适合添加的话题标签，标签前不需要带#号，不要超过4个，然后将其组成字符串数组返回"},
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
            return _normalize_text_list(array)
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def douBao_ai_tag(title, text):
    client = OpenAI()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user",
             "content": f"这是视频标题{title}，这是一个视频的内容：{text}，请提取这个视频内容涉及到主要的地点人物事物的名词或名称或要素，按视频内容展示的重要性排序，词一共不超过5个，词前面不需要带#号，然后将其组成字符串数组返回"},
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
            return _normalize_text_list(array)
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def douBao_ai_word_intro_content(title, text):
    client = OpenAI()

    response = client.chat.completions.create(
        model=MODEL_THINK_NAME,
        messages=[
            {"role": "user",
             'content': f'这是一个视频标题：{title}，内容要求是{text}，并且每个需要按小标题输出，只需要小标题，不需要其他解释，一个小标题最好不能超过15个字'
                        f'，如果视频标题里面没有具体数量要求，那就不要超过16个小标题且小标题数量是8的倍数，提到了就按标题数量，'
                        f'每一个小标题作为一个元素放入数组中，最后返回这个数组', },
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
            return _normalize_text_list(array)
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def douBao_ai_history_strategy_content(title, text):
    client = OpenAI()

    response = client.chat.completions.create(
        model=MODEL_THINK_NAME,
        messages=[
            {"role": "user",
             "content": (
                 f"标题：{title} 要求：{text}\n"
                 "写短视频口播文案，规则：\n"
                 "1 第1句是开场，必须带标题关键词，单独一段；\n"
                 "2 之后每段由两句话组成，用1个空格隔开，每句15-25字；\n"
                 "3 最后一段也是两句话，作为结尾；\n"
                 "4 全程大白话，别要标点；\n"
                 "5 直接返回纯JSON数组，不要解释。"
             )}
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
            # title_init = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', title)
            # title_array_str = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', array[0])
            # if title_init not in title_array_str:
            #     array = [title] + array
            print(array)
            return array
        except json.JSONDecodeError:
            print("提取的字符串不是有效的 JSON 格式。")
            return []
    else:
        print("未找到匹配的数组。")
        return []


def douBao_ai_sights_strategy_content(title, text):
    client = OpenAI()

    # 优化后的指令模板，核心是明确格式、提供示例、强化约束
    prompt_content = f"""
    任务：根据短视频标题和要求，生成结构化的旅游攻略数组，严格遵循以下规则：
    【重要】输出必须是纯JSON数组，不要有任何其他文字、markdown标记或说明。
    
    1. 输出格式要求（必须严格遵守）：
       - 仅返回标准JSON数组，以[开头，以]结尾
       - 数组内每个元素是一个字典，使用双引号包裹所有字符串
       - 无其他多余文字、解释、备注或markdown代码块标记
       - JSON必须可被Python的json.loads()直接解析
    
    2. 数组元素规则：
       - 如果标题是每日行程类（如"西安3日游攻略"），每个元素对应1天行程，key为"XXDayN·行程主题"（如"西安Day1·临潼秦唐双璧之旅"），且这个key不能超过15个字
       - 如果标题是单一景点类（如"兵马俑游玩攻略"），数组仅含1个元素，key为景点名称
    
    3. 字典必须包含以下固定字段（缺一不可，严格控制字数范围）：
       - 行程安排：详细的交通方式、时间、路线，60-100字（既详细又简洁）
       - 玩点亮点：核心游玩景点、特色体验，50-80字（2-3个亮点，每个亮点具体描述）
       - 特色美食：当地特色小吃、推荐店铺，40-60字（2-3个美食，有特色说明）
       - 注意事项：门票预约、消费提示、游玩建议，40-60字（关键事项，实用性强）
    
    4. 颜色标记要求（重要）：
       - 所有景点名称必须用【】标记，例如：【兵马俑】、【华清宫】、【陕历博】
       - 所有美食名称必须用《》标记，例如：《biangbiang面》、《葫芦鸡》、《灌汤包》
       - 标记必须在景点/美食名称第一次出现时就添加，后续提及可选择性添加
    
    5. 重要禁止事项（必须遵守）：
       - 注意事项内容中严禁出现"免费"两个字
       - 所有价格信息必须使用"¥"作为货币单位，绝对不能使用"元"或"r"
       - 价格格式示例：120¥/人、10¥/杯、80¥/人，绝不能写成"120元/人"或"120r/人"
       - 票务信息中如需提及票务，只能说"票"或"票务"，不能说"免费票"或"免费参观"
    
    6. 【关键】JSON格式检查清单：
       - 所有字符串用双引号""包裹，不要用单引号
       - 字典key和value都用双引号
       - 不要在JSON中包含换行符或特殊控制字符
       - 数组和字典的括号必须正确闭合


    示例输出（西安3日游）：
    [
        {{
            "西安Day1·临潼秦唐双璧之旅": {{
                "行程安排": "早8点乘地铁9号线至华清池站，转公交到【秦始皇兵马俑博物馆】；下午步行1公里到【华清宫】；晚上乘地铁9号线返回市区",
                "玩点亮点": "【兵马俑】1号坑千人千面军阵、2号坑铜车马；【华清宫】兵谏亭、《长恨歌》实景演出",
                "特色美食": "老童家《biangbiang面》（宽面裹油泼辣子）、现榨临潼《石榴汁》（10¥/杯）",
                "注意事项": "【兵马俑】需提前1天公众号预约（旺季120¥/人，淡季80¥/人）；【华清宫】演出建议买中间区域门票"
            }}
        }},
        {{
            "西安Day2·古城墙下的烟火与文明": {{
                "行程安排": "早9点到【陕西历史博物馆】；中午逛小寨赛格；下午乘地铁2号线到永宁门上【西安古城墙】；晚上逛【钟楼】【鼓楼】+回民街",
                "玩点亮点": "【陕历博】何家村遗宝（镶金兽首玛瑙杯、鎏金舞马衔杯银壶）；【城墙】骑行（13.74公里，看古城与现代建筑同框）",
                "特色美食": "长安大排档《葫芦鸡》、《毛笔酥》；贾三《灌汤包》（牛肉灌汤包皮薄汁多）",
                "注意事项": "【陕历博】票每天限6000张，早8点放票需抢；【城墙】自行车选带减震款，避免太累"
            }}
        }}
    ]

    现在，请根据以下信息生成攻略：
    短视频标题：{title}
    短视频要求：{text}

    再次强调（必须严格遵守）：
    1. 价格单位只能用"¥"，绝对不能用"元"或"r"
    2. 注意事项中绝对不能出现"免费"两个字
    3. 输出必须是纯JSON数组，不要有任何其他文字或说明
    """

    response = client.chat.completions.create(
        model=MODEL_THINK_NAME,
        messages=[
            {"role": "user", "content": prompt_content}
        ],
        stream=False,
        # 增加格式约束参数
        temperature=0.3,  # 降低随机性，提升格式稳定性
        max_tokens=2000  # 确保有足够长度容纳完整攻略
    )
    result = response.choices[0].message.content

    try:
        # 直接尝试解析完整结果（因为指令要求仅返回JSON）
        array = json.loads(result)
        print("解析成功：", array)
        return array
    except json.JSONDecodeError:
        # 备用方案：提取数组部分再解析
        pattern = r'\[(.*?)\]'
        match = re.search(pattern, result, re.DOTALL)
        if match:
            try:
                array = json.loads(match.group(0))  # 直接匹配完整数组
                print("提取后解析成功：", array)
                return array
            except:
                print("提取的字符串仍不是有效的JSON格式")
                return []
        else:
            print("未找到匹配的数组")
            return []


def douBao_ai_food_strategy_content(title, text):
    """
    生成地方攻略文案（支持美食、特产、地方特色等）
    返回格式: [{"第1页·页标题": {"项目1": {...}, "项目2": {...}}}, ...]
    每页包含2个项目
    """
    client = OpenAI()

    prompt_content = f"""
    任务：根据短视频标题生成结构化的地方攻略数组，严格遵循以下规则：
    【重要】输出必须是纯JSON数组，不要有任何其他文字、markdown标记或说明。
    
    1. 输出格式要求（必须严格遵守）：
       - 仅返回标准JSON数组，以[开头，以]结尾
       - 数组内每个元素是一个字典，使用双引号包裹所有字符串
       - 无其他多余文字、解释、备注或markdown代码块标记
       - JSON必须可被Python的json.loads()直接解析
    
    2. 智能判断标题类型（优先级从高到低）：
       - 【第一优先级】如果标题明确包含"特产"、"纪念品"、"伴手礼"、"值得买"、"购物"等关键词，必须返回特产攻略（如"南昌有什么特产"、"杭州买什么"）
       - 【第二优先级】如果标题包含"美食"、"吃的"、"小吃"、"美食推荐"、"好吃"等关键词，返回美食攻略
       - 【第三优先级】如果标题包含"景点"、"好玩"、"必去"、"打卡"、"游览"等关键词，返回景点攻略
       - 其他情况根据标题判断返回最合适的内容类型

    3. 数组元素规则：
       - 每个元素对应一页内容，key为"第N页·页标题"（如"第1页·经典名菜"、"第2页·必买特产"）
       - 页标题要简洁生动，不能超过12个字，要与内容类型匹配
    
    4. 每页字典必须包含2个项目，每个项目的key为"项目1"和"项目2"，每个项目包含以下字段（共3个字段）：
       - 名称：项目名称（如美食名、特产名、景点名），10字以内，用【】标记包裹
       - 简介/特色：项目的特色、口感、历史背景、工艺等描述，50-70字，语言生动有吸引力
       - 价格信息：价格范围或人均消费，使用"¥"作为货币单位，如人均50¥、15¥/份，对于景点可以说门票信息
    
    5. 颜色标记要求（重要）：
       - 所有名称必须用【】标记，例如：【西湖醋鱼】、【丝绸】、【灵隐寺】
    
    6. 重要禁止事项（必须遵守）：
       - 所有价格信息必须使用"¥"作为货币单位，绝对不能使用"元"或"r"
       - 价格格式示例：人均50¥、15¥/份、120¥/人、10¥/杯、门票80¥
    
    7. 【关键】JSON格式检查清单：
       - 所有字符串用双引号""包裹，不要用单引号
       - 字典key和value都用双引号
       - 不要在JSON中包含换行符或特殊控制字符
       - 数组和字典的括号必须正确闭合

    示例输出1（杭州美食攻略 - 标题："杭州有什么好吃的"）：
    [
        {{
            "第1页·经典名菜": {{
                "项目1": {{
                    "名称": "【西湖醋鱼】",
                    "简介/特色": "杭州最具代表性的传统名菜，选用西湖草鱼饿养去腥后烹制，鱼肉鲜嫩洁白，酸甜酱汁带有蟹味",
                    "价格信息": "人均150¥，醋鱼单点88¥/份"
                }},
                "项目2": {{
                    "名称": "【东坡肉】",
                    "简介/特色": "相传与苏东坡有关，选用薄皮五花肉，用冰糖酱油绍酒焖制，色泽红亮如玛瑙",
                    "价格信息": "人均80¥，东坡肉28¥/份"
                }}
            }}
        }}
    ]

    示例输出2（杭州特产攻略 - 标题："杭州有什么特产"）：
    [
        {{
            "第1页·丝绸织品": {{
                "项目1": {{
                    "名称": "【杭罗】",
                    "简介/特色": "杭州传统丝织品，质地轻薄透凉，色泽柔和，是中国四大名绣之一，极具收藏价值",
                    "价格信息": "围巾80-150¥，旗袍300-800¥"
                }},
                "项目2": {{
                    "名称": "【西湖绸伞】",
                    "简介/特色": "杭州传统手工艺品，用丝绸制成，伞面绘制西湖美景，工艺精湛，极具地方特色",
                    "价格信息": "50-100¥"
                }}
            }}
        }},
        {{
            "第2页·必买伴手礼": {{
                "项目1": {{
                    "名称": "【龙井茶】",
                    "简介/特色": "杭州特产茶品，茶叶扁平光滑，色泽翠绿，香气清雅，是中国十大名茶之一",
                    "价格信息": "明前茶300-500¥/斤，普通茶100-200¥/斤"
                }},
                "项目2": {{
                    "名称": "【杭州糕点】",
                    "简介/特色": "杭州传统糕点，有桂花糕、绿豆糕、定胜糕等，口感松软香甜，是节庆必备",
                    "价格信息": "8-20¥/盒"
                }}
            }}
        }}
    ]

    现在，请根据以下信息生成攻略：
    短视频标题：{title}
    短视频要求：{text}

    再次强调（必须严格遵守）：
    1. 【首要】如果标题包含"特产"关键词，必须返回特产攻略，不要返回美食
    2. 价格单位只能用"¥"，绝对不能用"元"或"r"
    3. 所有名称必须用【】标记
    4. 输出必须是纯JSON数组，不要有任何其他文字或说明
    5. 每页必须包含2个项目（"项目1"和"项目2"）
    6. 生成3-4页（6-8个项目）
    7. 【特别重要】严格按照优先级判断：特产 > 美食 > 景点
    """

    response = client.chat.completions.create(
        model=MODEL_THINK_NAME,
        messages=[
            {"role": "user", "content": prompt_content}
        ],
        stream=False,
        temperature=0.3,
        max_tokens=2000
    )
    result = response.choices[0].message.content

    try:
        array = json.loads(result)
        print("美食攻略解析成功：", array)
        return array
    except json.JSONDecodeError:
        pattern = r'\[(.*?)\]'
        match = re.search(pattern, result, re.DOTALL)
        if match:
            try:
                array = json.loads(match.group(0))
                print("提取后解析成功：", array)
                return array
            except:
                print("提取的字符串仍不是有效的JSON格式")
                return []
        else:
            print("未找到匹配的数组")
            return []


def douBao_ai_festival_customs_tag(title, content):
    """
    为节日风俗类生成标签，第一个标签是省份名
    """
    client = OpenAI()

    prompt_content = f"""
    任务：为节日风俗/民族风俗内容生成视频标签，第一个标签必须是省份名称。

    要求：
    1. 分析标题："{title}"，从中提取省份或主要地域名称
    2. 标签规则：
       - 第一个标签必须是省份名（如"宁夏"、"云南"、"广西"、"新疆"、"陕西"等）
       - 若标题提到"傈僳族"→提取"云南"，"回族"→提取"宁夏"，"壮族"→提取"广西"
       - 若标题提到具体节日如"春节"→提取"全国"
       - 后续标签包括：民族名称、节日相关术语、文化关键词等
       - 标签数量3-5个

    请生成标签列表，用逗号分隔返回。
    """

    response = client.chat.completions.create(
        model=MODEL_THINK_NAME,
        messages=[
            {"role": "user", "content": prompt_content}
        ],
        stream=False,
        temperature=0.3,
        max_tokens=200
    )

    result = response.choices[0].message.content
    tags = [tag.strip() for tag in result.split(',') if tag.strip()]
    return tags


# douBao_ai_word_intro_content('世界最出名的十大自然景点',
#                              '介绍的东西或者地方一定要符合标题要求，一定得是在标题描述的地区范围内，必须要检查一遍介绍的东西或者地方是否真实存在且在这个标题描述的地区范围，如果标题描述的是中国范围的，最好介绍的东西或者地方前面加上所属省的省名，需要不能出错，介绍顺序随机。')

# douBao_ai('上饶周末亲子游', '介绍的地方一定要符合主题，介绍的顺序随机，每次打乱介绍顺序，并且简单介绍每个地方的特色')

# deepseek_ai_title('中国只有上饶才有的5大绝景第3个震撼全网')

# douBao_ai_qa_content('中国最出名的人文景点有哪些', '介绍的地方一定要符合标题描述')

# douBao_ai_sights_strategy_content('南昌三日游攻略', '详细的每日行程安排，包含交通、玩点、美食、注意事项')

# douBao_ai_food_strategy_content('杭州有什么好吃的', '介绍杭州本地特色美食，包含传统名菜和街头小吃')


def douBao_ai_festival_customs_content(title, text):
    """
    生成节日风俗/民族风俗类文案
    返回格式: [{"第1页·页标题": {"项目1": {...}, "项目2": {...}}}, ...]
    每页包含2个风俗项目
    """
    client = OpenAI()

    prompt_content = f"""
    任务：根据短视频标题生成结构化的节日风俗/民族风俗数组，严格遵循以下规则：
    【重要】输出必须是纯JSON数组，不要有任何其他文字、markdown标记或说明。
    
    1. 输出格式要求（必须严格遵守）：
       - 仅返回标准JSON数组，以[开头，以]结尾
       - 数组内每个元素是一个字典，使用双引号包裹所有字符串
       - 无其他多余文字、解释、备注或markdown代码块标记
       - JSON必须可被Python的json.loads()直接解析
    
    2. 智能判断标题类型（优先级从高到低）：
       - 【第一优先级】如果标题包含"族"字（如"傈僳族"、"彝族"、"苗族"），生成该民族的风俗文化内容，包括：传统节日、婚俗习惯、服饰文化、饮食文化、宗教信仰等
       - 【第二优先级】如果标题包含具体节日名称（如"春节"、"破五"、"元宵节"、"端午节"），生成该节日的传统习俗和风俗
       - 【第三优先级】如果标题包含"风俗"、"习俗"、"传统"等关键词，根据内容判断生成多风俗列表或单个风俗的详细介绍
    
    3. 标签提取规则（非常重要）：
       - 第一个标签必须是省份名称（如"宁夏"、"云南"、"广西"、"新疆"等）
       - 从标题中智能提取相关省份，若标题包含民族名则提取该民族主要分布的省份（如"傈僳族"→"云南"，"回族"→"宁夏"）
       - 若无明确省份则使用"全国"作为第一个标签
       - 确保第一个标签是省级地域名称，而非民族名称或通用词汇

    4. 数组元素规则：
       - 每个元素对应一页内容，key为"第N页·页标题"（如"第1页·传统节日"、"第2页·婚俗习惯"）
       - 页标题要简洁生动，不能超过12个字，要与内容类型匹配
       - 如果是民族类，按风俗类别分页（传统节日、婚俗习惯、服饰文化、饮食特色等）
       - 如果是具体节日类，按习俗类型分页（节日起源、传统活动、饮食习俗、禁忌讲究等）
    
    5. 每页字典必须包含2个项目，每个项目的key为"项目1"和"项目2"，每个项目包含以下字段：
       - 风俗名称：风俗或习俗的名称，15字以内，用【】标记包裹，如【刀杆节】、【拜年】、【抢亲习俗】
       - 简介寓意：该风俗的简介、文化寓意或历史渊源，50-80字，语言生动有文化内涵
       - 具体做法：该风俗的具体做法、活动流程或表现形式，30-50字，描述具体可操作
       - 时间地域：该风俗的时间（如农历日期、节气）或地域分布（如云南怒江、全国各地），20-30字
    
    6. 颜色标记要求（重要）：
       - 所有风俗名称必须用【】标记，例如：【刀杆节】、【拜年】、【赛龙舟】
       - 重要的文化概念、民族名称可选使用《》标记
    
    7. 内容生成原则：
       - 确保风俗内容准确，符合传统文化常识
       - 对于民族风俗，要体现该民族的特色和文化内涵
       - 对于节日风俗，要体现节日的传统寓意和文化传承
       - 避免出现商业化、功利化的描述
    
    8. 【关键】JSON格式检查清单：
       - 所有字符串用双引号""包裹，不要用单引号
       - 字典key和value都用双引号
       - 不要在JSON中包含换行符或特殊控制字符
       - 数组和字典的括号必须正确闭合

    示例输出1（民族风俗 - 标题："傈僳族的特点和风俗"）：
    [
        {{
            "第1页·传统节日": {{
                "项目1": {{
                    "风俗名称": "【刀杆节】",
                    "简介寓意": "傈僳族最盛大的传统节日，展示勇敢精神，祈求平安健康，已被列入国家级非物质文化遗产",
                    "具体做法": "农历二月初八举行，勇士赤脚攀爬36把钢刀组成的刀杆，在刀尖进行惊险表演",
                    "时间地域": "农历二月初八/云南怒江傈僳族自治州"
                }},
                "项目2": {{
                    "风俗名称": "【澡塘会】",
                    "简介寓意": "傈僳族独特的温泉沐浴习俗，人们相信温泉能洗去晦气，带来健康和好运",
                    "具体做法": "春节期间在怒江峡谷温泉边搭建帐篷，全家老小一起泡温泉、对歌跳舞",
                    "时间地域": "春节前后/怒江峡谷温泉地带"
                }}
            }}
        }},
        {{
            "第2页·婚俗习惯": {{
                "项目1": {{
                    "风俗名称": "【抢亲习俗】",
                    "简介寓意": "傈僳族传统婚俗，体现男方的勇敢和诚意，是现代婚礼前的一种仪式性表演",
                    "具体做法": "男方亲友佯装抢亲，女方亲友阻拦，经过一番嬉闹后将新娘迎娶回家",
                    "时间地域": "婚礼当天/傈僳族聚居区"
                }},
                "项目2": {{
                    "风俗名称": "【同心酒】",
                    "简介寓意": "傈僳族独特的饮酒礼仪，象征情谊深厚、同心同德，是待客的最高礼节",
                    "具体做法": "两人共喝一杯酒，手臂相交，同时饮酒，表示亲密无间和真诚相待",
                    "时间地域": "节庆待客/全国各地傈僳族"
                }}
            }}
        }}
    ]

    示例输出2（节日风俗 - 标题："破五的风俗有哪些"）：
    [
        {{
            "第1页·传统习俗": {{
                "项目1": {{
                    "风俗名称": "【送穷鬼】",
                    "简介寓意": "正月初五送穷是中国传统习俗，寓意送走贫穷晦气，迎接新一年的财富和好运",
                    "具体做法": "清晨打扫卫生，将垃圾倒出门外，燃放鞭炮驱赶穷气，祈求新年财源广进",
                    "时间地域": "正月初五清晨/全国各地"
                }},
                "项目2": {{
                    "风俗名称": "【迎财神】",
                    "简介寓意": "正月初五是财神诞辰，商家和家庭都会举行仪式迎接财神，祈求生意兴隆",
                    "具体做法": "摆放财神像或画像，供奉水果、糕点、酒水，燃放鞭炮，开门纳财",
                    "时间地域": "正月初五/全国各地，尤甚商贾"
                }}
            }}
        }},
        {{
            "第2页·饮食禁忌": {{
                "项目1": {{
                    "风俗名称": "【吃饺子】",
                    "简介寓意": "破五吃饺子寓意捏小人嘴，防止小人谗言，同时也是对新年美好生活的期盼",
                    "具体做法": "包制饺子时要用力捏紧，象征捏住小人嘴巴，饺子的形状像元宝寓意招财",
                    "时间地域": "正月初五/北方地区为主"
                }},
                "项目2": {{
                    "风俗名称": "【禁针线】",
                    "简介寓意": "破五前禁止动针线，传说会刺伤龙眼，影响一年的运势和收成",
                    "具体做法": "从除夕到初五不动针线，初五后才可恢复缝补，体现了对传统禁忌的尊重",
                    "时间地域": "除夕至初五/传统汉族地区"
                }}
            }}
        }}
    ]

    现在，请根据以下信息生成节日风俗内容：
    短视频标题：{title}
    短视频要求：{text}

    再次强调（必须严格遵守）：
    1. 智能判断内容类型：民族类 > 具体节日类 > 通用风俗类
    2. 所有风俗名称必须用【】标记
    3. 输出必须是纯JSON数组，不要有任何其他文字或说明
    4. 每页必须包含2个项目（"项目1"和"项目2"）
    5. 生成3-4页（6-8个项目），确保内容丰富多样
    6. 内容要准确体现传统文化，避免错误信息
    """

    response = client.chat.completions.create(
        model=MODEL_THINK_NAME,
        messages=[
            {"role": "user", "content": prompt_content}
        ],
        stream=False,
        temperature=0.3,
        max_tokens=2500
    )
    result = response.choices[0].message.content

    try:
        array = json.loads(result)
        print("节日风俗解析成功：", array)
        return array
    except json.JSONDecodeError:
        pattern = r'\[(.*?)\]'
        match = re.search(pattern, result, re.DOTALL)
        if match:
            try:
                array = json.loads(match.group(0))
                print("提取后解析成功：", array)
                return array
            except:
                print("提取的字符串仍不是有效的JSON格式")
                return []
        else:
            print("未找到匹配的数组")
            return []
