import asyncio
import json
import re

from ai_tool.ai_text_production import add_suffix_to_file_path, \
    write_arrays_to_excel, deepseek_ai_intro_title, deepseek_ai_intro_topic, \
    deepseek_ai_intro_tag, deepseek_ai_strategy_title, deepseek_ai_strategy_topic, deepseek_ai_strategy_tag, \
    segment_title, ai_extract_title, ai_fix_errors, deepseek_ai_topic, deepseek_ai_strategy_scenic_topic, \
    deepseek_ai_strategy_scenic_tag, deepseek_ai_intro_1_tag, deepseek_ai_scenic_tag, \
    deepseek_ai_history_strategy_topic, deepseek_ai_strategy_history_tag
from ai_tool.doubao_ai_production import douBao_ai_title, douBao_ai_topic, douBao_ai_tag, \
    douBao_ai_intro_content, douBao_ai_strategy_content, douBao_ai_word_intro_content, douBao_ai_sr_intro_content, \
    douBao_ai_dispose_intro_content, douBao_ai_life_strategy_content, douBao_ai_qa_content, \
    douBao_ai_sights_strategy_content, douBao_ai_history_strategy_content, douBao_ai_food_strategy_content, \
    douBao_ai_festival_customs_content, douBao_ai_festival_customs_tag
from database_tool.video_load_tool import update_video_title_info
from sanong_generation.copywriter import generate_sanong_copywriting
from worker.worker_signals import WorkerSignals
from PyQt6.QtCore import QRunnable


def _read_excel(*args, **kwargs):
    """Load pandas only when an AI workbook job actually starts."""
    import pandas as pd

    return _read_excel(*args, **kwargs)


# ai分析文案 通用类
class AiDisposeStrategyTitle(QRunnable):
    def __init__(self, excel_file_path, account_name, title_id=-1):
        super().__init__()
        self.excel_file_path = excel_file_path
        self.account_name = account_name
        self.title_id = title_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 读取 Excel 文件
            df = _read_excel(self.excel_file_path)

            # 获取第二列的所有内容（除了第一行）
            second_column = df.iloc[0:, 1].tolist()  # iloc[1:, 1] 表示从第二行开始，第二列

            # 文案excel
            copy_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_copy')

            # 标签excel
            label_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_label')

            for i, title in enumerate(second_column):

                title = title

                # ai获取文案
                ai_word_list = []

                n = 0
                while len(ai_word_list) == 0 and n < 2:  # 从3改为2，减少重试
                    self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题文案(第{n+1}次)')
                    ai_word_list = douBao_ai_strategy_content(title,
                                                              '文案要符合标题，视频文案对观看者有实质性的帮助学习，以叙事的口吻讲述,文案需要控制在大概三百字')
                    n += 1

                # ai_title = deepseek_ai_strategy_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))[0]
                ai_title = segment_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))
                ai_topic = ','.join(deepseek_ai_strategy_topic(','.join(ai_word_list)))

                if self.account_name != '':
                    ai_topic = ai_topic + ',' + self.account_name

                ai_title_word_list = [ai_title] + [ai_topic] + ai_word_list

                # 将标题和文案写入excel表格中
                write_arrays_to_excel(copy_excel_file_path, ai_title_word_list)

                # 片段标签字符串列表
                tag_list_str_list = []

                for ai_word in ai_word_list:
                    # 提取每个片段的关键词, 片段关键词列表
                    tag_list = []
                    tag_retry_count = 0
                    while len(tag_list) == 0 and tag_retry_count < 3:
                        # 获取关键词
                        tag_retry_count += 1
                        self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题标签')
                        tag_list = deepseek_ai_strategy_tag(title, ai_word)

                    # 关键词字符串
                    tag_list_str = ','.join(tag_list)
                    tag_list_str_list.append(tag_list_str)

                # 将片段标签写入excel表格中
                write_arrays_to_excel(label_excel_file_path, tag_list_str_list)
                self.signals.progressResultReady.emit(f'这是第{i + 1}个话题， 已经ai处理完成')
                if self.title_id != -1:
                    # 同步文案标签信息
                    update_video_title_info(self.title_id, '&&'.join(ai_title_word_list), '&&'.join(tag_list_str_list))
            self.signals.finished.emit('分析文案完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))


# ai分析文案 景点通用类
class AiDisposeScenicSpotTitle(QRunnable):
    def __init__(self, excel_file_path, account_name, title_id=-1):
        super().__init__()
        self.excel_file_path = excel_file_path
        self.account_name = account_name
        self.title_id = title_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 读取 Excel 文件
            df = _read_excel(self.excel_file_path)

            # 获取第二列的所有内容（除了第一行）
            second_column = df.iloc[0:, 1].tolist()  # iloc[1:, 1] 表示从第二行开始，第二列

            # 文案excel
            copy_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_copy')

            # 标签excel
            label_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_label')

            for i, title in enumerate(second_column):

                title = title

                # ai获取文案
                ai_word_list = []
                retry_count = 0
                max_retries = 3

                while len(ai_word_list) == 0 and retry_count < max_retries:
                    self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题文案 (尝试 {retry_count + 1}/{max_retries})')
                    ai_word_list = douBao_ai_strategy_content(title, '生成的文案需要介绍与标题相关的景点，内容可以包含景区的历史背景、文化内涵、地理环境等，'
                                                                     '让读者对景区有一个全面的认识，内容要引人入胜，适当点题，文案需要控制在大概4百字')
                    retry_count += 1
                
                if len(ai_word_list) == 0:
                    self.signals.progressResultReady.emit(f'⚠️ 第{i + 1}个标题生成失败，已跳过')
                    continue

                # ai_title = segment_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))
                ai_title = deepseek_ai_strategy_title(title)
                ai_topic = ','.join(deepseek_ai_strategy_scenic_topic(','.join(ai_word_list)))

                if self.account_name != '':
                    ai_topic = ai_topic + ',' + self.account_name

                ai_title_word_list = [ai_title] + [ai_topic] + ai_word_list

                # 将标题和文案写入excel表格中
                write_arrays_to_excel(copy_excel_file_path, ai_title_word_list)

                # 片段标签字符串列表
                tag_list_str_list = []

                for ai_word in ai_word_list:
                    # 提取每个片段的关键词, 片段关键词列表
                    tag_list = []
                    tag_retry_count = 0
                    while len(tag_list) == 0 and tag_retry_count < 3:
                        # 获取关键词
                        tag_retry_count += 1
                        self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题标签')
                        tag_list = deepseek_ai_strategy_scenic_tag(title, ai_word)

                    # 关键词字符串
                    tag_list_str = ','.join(tag_list)
                    tag_list_str_list.append(tag_list_str)

                # 将片段标签写入excel表格中
                write_arrays_to_excel(label_excel_file_path, tag_list_str_list)
                self.signals.progressResultReady.emit(f'这是第{i + 1}个话题， 已经ai处理完成')
                if self.title_id != -1:
                    # 同步文案标签信息
                    update_video_title_info(self.title_id, '&&'.join(ai_title_word_list), '&&'.join(tag_list_str_list))
            self.signals.finished.emit('分析文案完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))


# ai分析文案 素材通用类
class AiDisposeMaterialStrategyTitle(QRunnable):
    def __init__(self, excel_file_path, account_name, title_id=-1):
        super().__init__()
        self.excel_file_path = excel_file_path
        self.account_name = account_name
        self.title_id = title_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            generate_sanong_copywriting(
                self.excel_file_path,
                self.account_name,
                self.title_id,
                self.signals.progressResultReady.emit,
            )
            self.signals.finished.emit('分析文案完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))


# ai分析文案 励志人生感悟类
class AiDisposeLifeStrategyTitle(QRunnable):
    def __init__(self, excel_file_path, account_name):
        super().__init__()
        self.account_name = account_name
        self.excel_file_path = excel_file_path
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 读取 Excel 文件
            df = _read_excel(self.excel_file_path)

            # 获取第二列的所有内容（除了第一行）
            second_column = df.iloc[0:, 1].tolist()  # iloc[1:, 1] 表示从第二行开始，第二列

            # 文案excel
            copy_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_copy')

            for i, title in enumerate(second_column):

                title = title

                # ai获取文案
                ai_word_list = []

                content_retry_count = 0
                while len(ai_word_list) == 0 and content_retry_count < 3:
                    content_retry_count += 1
                    self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题文案（第{content_retry_count}次）')
                    ai_word_list = douBao_ai_life_strategy_content(title)

                # ai_title = deepseek_ai_strategy_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))[0]
                if len(ai_word_list) == 0:
                    self.signals.progressResultReady.emit(f'⚠️ 第{i + 1}个标题AI生成失败，已跳过')
                    continue
                ai_title = ai_word_list[0]
                ai_topic = ','.join(deepseek_ai_topic(','.join(ai_word_list)))

                if self.account_name != '':
                    ai_topic = ai_topic + ',' + self.account_name

                ai_title_word_list = [ai_title] + [ai_topic] + ai_word_list

                # 将标题和文案写入excel表格中
                write_arrays_to_excel(copy_excel_file_path, ai_title_word_list)

                self.signals.progressResultReady.emit(f'这是第{i + 1}个话题， 已经ai处理完成')

            self.signals.finished.emit('分析文案完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))


# ai分析文案 介绍类
class AiDisposeIntroTitle(QRunnable):
    def __init__(self, excel_file_path, account_name, title_id=-1):
        super().__init__()
        self.excel_file_path = excel_file_path
        self.account_name = account_name
        self.title_id = title_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 读取 Excel 文件
            df = _read_excel(self.excel_file_path)

            # 获取第二列的所有内容（除了第一行）
            second_column = df.iloc[0:, 1].tolist()  # iloc[1:, 1] 表示从第二行开始，第二列

            # 文案excel
            copy_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_copy')

            # 标签excel
            label_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_label')

            for i, title in enumerate(second_column):

                title = title

                # ai获取文案
                ai_word_list = []

                content_retry_count = 0
                while len(ai_word_list) == 0 and content_retry_count < 3:
                    content_retry_count += 1
                    self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题文案（第{content_retry_count}次）')
                    ai_word_list = douBao_ai_sr_intro_content(title,
                                                              '介绍的东西或者地方一定要符合标题要求，一定得是在标题描述的地区范围内，必须要检查一遍介绍的东西或者地方是否真实存在且在这个标题描述的地区范围，而且介绍的地方不能太偏僻，除了在介绍其他地方外，也尽量包含大茅山、灵山、龟峰这几个地方，这几个地方不符合标题提到的介绍范围或者地区范围的的可以不用加进去介绍，但是介绍的时候也不能只包含这几个，不能出错，介绍话语也要符合标题语气，介绍顺序随机，并且简单两句话对其介绍,介绍的话术要符合标题')

                # ai_title = deepseek_ai_intro_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))
                ai_title = segment_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))

                ai_topic = ','.join(deepseek_ai_intro_topic(title))

                if self.account_name != '':
                    ai_topic = ai_topic + ',' + self.account_name

                ai_title_word_list = [ai_title] + [ai_topic] + ai_word_list

                # 将标题和文案写入excel表格中
                write_arrays_to_excel(copy_excel_file_path, ai_title_word_list)

                # 片段标签字符串列表
                tag_list_str_list = []

                for ai_word in ai_word_list:
                    # 提取每个片段的关键词, 片段关键词列表
                    tag_list = []
                    tag_retry_count = 0
                    while len(tag_list) == 0 and tag_retry_count < 3:
                        # 获取关键词
                        tag_retry_count += 1
                        self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题标签')
                        tag_list = deepseek_ai_intro_tag(title, ai_word)

                    # 关键词字符串
                    tag_list_str = ','.join(tag_list)
                    tag_list_str_list.append(tag_list_str)

                # 将片段标签写入excel表格中
                write_arrays_to_excel(label_excel_file_path, tag_list_str_list)
                self.signals.progressResultReady.emit(f'这是第{i + 1}个话题， 已经ai处理完成')

                if self.title_id != -1:
                    # 同步文案标签信息
                    update_video_title_info(self.title_id, '&&'.join(ai_title_word_list), '&&'.join(tag_list_str_list))

            self.signals.finished.emit('分析文案完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))


# ai分析文案 全国介绍类
class AiDisposeCNIntroTitle(QRunnable):
    def __init__(self, excel_file_path, account_name, title_id=-1):
        super().__init__()
        self.excel_file_path = excel_file_path
        self.account_name = account_name
        self.title_id = title_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 读取 Excel 文件
            df = _read_excel(self.excel_file_path)

            # 获取第二列的所有内容（除了第一行）
            second_column = df.iloc[0:, 1].tolist()  # iloc[1:, 1] 表示从第二行开始，第二列

            # 文案excel
            copy_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_copy')

            # 标签excel
            label_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_label')

            for i, title in enumerate(second_column):

                title = re.sub(r'\s+', '', title)

                # ai获取文案
                ai_word_list = []

                content_retry_count = 0
                while len(ai_word_list) == 0 and content_retry_count < 3:
                    content_retry_count += 1
                    self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题文案（第{content_retry_count}次）')
                    ai_word_list = douBao_ai_sr_intro_content(title,
                                                              '介绍的东西或者地方一定要符合标题要求，一定要符合标题描述的范围，不能出错，介绍话语也要符合标题语气，介绍顺序随机，并且简单两句话对其介绍,介绍的话术要符合标题')

                ai_title = segment_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))

                ai_topic = ','.join(deepseek_ai_intro_topic(title))

                # 随机添加账号标签 #景点打卡#景点推荐     #旅游推荐官 #旅游景点#寻找中国最美城市

                if self.account_name != '':
                    ai_topic = ai_topic + ',' + self.account_name
                random_tag_list = ['景点打卡', '景点推荐', '旅游推荐官', '旅游景点', '寻找中国最美城市']
                import random
                # 随机选择两个标签添加到话题中，使用,分割
                random_tags = random.sample(random_tag_list, 2)
                ai_topic = ai_topic + ',' + ','.join(random_tags)

                ai_title_word_list = [ai_title] + [ai_topic] + ai_word_list

                # 将标题和文案写入excel表格中
                write_arrays_to_excel(copy_excel_file_path, ai_title_word_list)

                # 片段标签字符串列表
                tag_list_str_list = []

                for ai_word in ai_word_list:
                    # 提取每个片段的关键词, 片段关键词列表
                    tag_list = []
                    tag_retry_count = 0
                    while len(tag_list) == 0 and tag_retry_count < 3:
                        # 获取关键词
                        tag_retry_count += 1
                        self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题标签')
                        tag_list = deepseek_ai_intro_tag(title, ai_word)

                    # 关键词字符串
                    tag_list_str = ','.join(tag_list)
                    tag_list_str_list.append(tag_list_str)

                # 将片段标签写入excel表格中
                write_arrays_to_excel(label_excel_file_path, tag_list_str_list)
                self.signals.progressResultReady.emit(f'这是第{i + 1}个话题， 已经ai处理完成')
                if self.title_id != -1:
                    # 同步文案标签信息
                    update_video_title_info(self.title_id, '&&'.join(ai_title_word_list), '&&'.join(tag_list_str_list))
            self.signals.finished.emit('分析文案完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))


# ai分析文案 介绍类
class AiDisposeMsIntroTitle(QRunnable):
    def __init__(self, excel_file_path, account_name, title_id=-1):
        super().__init__()
        self.excel_file_path = excel_file_path
        self.account_name = account_name
        self.title_id = title_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 读取 Excel 文件
            df = _read_excel(self.excel_file_path)

            # 获取第二列的所有内容（除了第一行）
            second_column = df.iloc[0:, 1].tolist()  # iloc[1:, 1] 表示从第二行开始，第二列

            # 文案excel
            copy_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_copy')

            # 标签excel
            label_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_label')

            for i, title in enumerate(second_column):

                title = title

                # ai获取文案
                ai_word_list = []

                content_retry_count = 0
                while len(ai_word_list) == 0 and content_retry_count < 3:
                    content_retry_count += 1
                    self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题文案（第{content_retry_count}次）')
                    ai_word_list = douBao_ai_intro_content(title,
                                                           '介绍的东西一定要符合标题要求，且一定得是在标题描述的地区范围内，'
                                                           '必须要检查一遍介绍的东西是否真实存在且在这个标题描述的地区范围，'
                                                           '而且介绍的东西能太偏，不能出错，介绍话语也要符合标题语气，介绍顺序随机，'
                                                           '并且简单两句话对其介绍,介绍的话术要符合标题')

                # ai_title = deepseek_ai_intro_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))
                ai_title = segment_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))

                ai_topic = ','.join(deepseek_ai_intro_topic(title))

                if self.account_name != '':
                    ai_topic = ai_topic + ',' + self.account_name

                ai_title_word_list = [ai_title] + [ai_topic] + ai_word_list

                # 将标题和文案写入excel表格中
                write_arrays_to_excel(copy_excel_file_path, ai_title_word_list)

                # 片段标签字符串列表
                tag_list_str_list = []

                for ai_word in ai_word_list:
                    # 提取每个片段的关键词, 片段关键词列表
                    tag_list = []
                    tag_retry_count = 0
                    while len(tag_list) == 0 and tag_retry_count < 3:
                        # 获取关键词
                        tag_retry_count += 1
                        self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题标签')
                        tag_list = deepseek_ai_intro_tag(title, ai_word)

                    # 关键词字符串
                    tag_list_str = ','.join(tag_list)
                    tag_list_str_list.append(tag_list_str)

                # 将片段标签写入excel表格中
                write_arrays_to_excel(label_excel_file_path, tag_list_str_list)
                self.signals.progressResultReady.emit(f'这是第{i + 1}个话题， 已经ai处理完成')

                if self.title_id != -1:
                    # 同步文案标签信息
                    update_video_title_info(self.title_id, '&&'.join(ai_title_word_list), '&&'.join(tag_list_str_list))

            self.signals.finished.emit('分析文案完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))


# ai分析文案 文字介绍类
class AiDisposeWordIntroTitle(QRunnable):
    def __init__(self, excel_file_path, account_name, title_id=-1):
        super().__init__()
        self.excel_file_path = excel_file_path
        self.account_name = account_name
        self.title_id = title_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 读取 Excel 文件
            df = _read_excel(self.excel_file_path)

            # 获取第二列的所有内容（除了第一行）
            second_column = df.iloc[0:, 1].tolist()  # iloc[1:, 1] 表示从第二行开始，第二列

            # 文案excel
            copy_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_copy')

            for i, title in enumerate(second_column):

                title = title

                # ai获取文案
                ai_word_list = []

                content_retry_count = 0
                while len(ai_word_list) == 0 and content_retry_count < 3:
                    content_retry_count += 1
                    self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题文案（第{content_retry_count}次）')
                    ai_word_list = douBao_ai_word_intro_content(title,
                                                                '列出符合标题描述地方的名称，介绍地方一定要符合标题要求，一定得是在标题描述的范围内，必须要检查一遍介绍地方是否真实存在且在这个标题描述的范围，不能出错，介绍顺序随机。')

                ai_title = segment_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title), 8)

                ai_topic = ','.join(deepseek_ai_intro_topic(title))

                if self.account_name != '':
                    ai_topic = ai_topic + ',' + self.account_name

                ai_title_word_list = [ai_title] + [ai_topic] + ai_word_list

                # 将标题和文案写入excel表格中
                write_arrays_to_excel(copy_excel_file_path, ai_title_word_list)

                self.signals.progressResultReady.emit(f'这是第{i + 1}个话题， 已经ai处理完成')

                if self.title_id != -1:
                    # 同步文案标签信息
                    update_video_title_info(self.title_id, '&&'.join(ai_title_word_list), '')

            self.signals.finished.emit('分析文案完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))


# 介绍类视频文案提取
class AiDisposeIntro(QRunnable):
    def __init__(self, copy_excel_file_path, label_excel_file_path, account_name, intro_text):
        super().__init__()
        self.copy_excel_file_path = copy_excel_file_path
        self.label_excel_file_path = label_excel_file_path
        self.intro_text = intro_text
        self.account_name = account_name
        self.signals = WorkerSignals()

    def run(self):
        try:
            # ai获取文案
            ai_word_list = []
            ai_title = ''
            # 获取标题
            title_retry_count = 0
            while ai_title == '' and title_retry_count < 3:
                title_retry_count += 1
                ai_title = ai_extract_title(self.intro_text)[0]
                ai_title = segment_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', ai_title))

            # 修正文案
            self.intro_text = ai_fix_errors(ai_title, self.intro_text)

            content_retry_count = 0
            while len(ai_word_list) == 0 and content_retry_count < 3:
                content_retry_count += 1
                if len(ai_word_list) == 0:
                    # 视频文案
                    ai_word_list = douBao_ai_dispose_intro_content(ai_title.replace('|', ''),
                                                                   f'这是原文案：{self.intro_text}，'
                                                                   f'需要把它按照不同的表述并且按指定格式结构输出返回'
                                                                   f'，文案中介绍的东西或地点的名称可能存在一些错误，'
                                                                   f'请根据标题描述把名称调整正确，内容主题不能改变，'
                                                                   f'文案整体的意思不变。')
            # 视频标签
            ai_topic = ','.join(deepseek_ai_intro_topic(ai_title))
            if self.account_name != '':
                ai_topic = ai_topic + ',' + self.account_name

            ai_title_word_list = [ai_title] + [ai_topic] + ai_word_list

            # 将标题和文案写入excel表格中
            write_arrays_to_excel(self.copy_excel_file_path, ai_title_word_list)

            # 片段标签字符串列表
            tag_list_str_list = []

            for ai_word in ai_word_list:
                # 提取每个片段的关键词, 片段关键词列表
                tag_list = []
                tag_retry_count = 0
                while len(tag_list) == 0 and tag_retry_count < 3:
                    # 获取关键词
                    tag_retry_count += 1
                    tag_list = deepseek_ai_intro_tag(ai_title, ai_word)

                # 关键词字符串
                tag_list_str = ','.join(tag_list)
                tag_list_str_list.append(tag_list_str)

            # 将片段标签写入excel表格中
            write_arrays_to_excel(self.label_excel_file_path, tag_list_str_list)

            self.signals.finished.emit('提取文案完成')
        except Exception as e:
            print(str(e))
            self.signals.errorOccurred.emit(str(e))


# 通用类视频文案提取
class AiDisposeStrategy(QRunnable):
    def __init__(self, copy_excel_file_path, label_excel_file_path, account_name, intro_text):
        super().__init__()
        self.copy_excel_file_path = copy_excel_file_path
        self.label_excel_file_path = label_excel_file_path
        self.intro_text = intro_text
        self.account_name = account_name
        self.signals = WorkerSignals()

    def run(self):
        try:
            # ai获取文案
            ai_word_list = []
            title = ''
            ai_title = ''
            # 获取标题
            title_retry_count = 0
            while ai_title == '' and title_retry_count < 3:
                title_retry_count += 1
                title = ai_extract_title(self.intro_text)[0]
                ai_title = segment_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))

            # 修正文案
            self.intro_text = ai_fix_errors(ai_title, self.intro_text)

            retry_count = 0
            max_retries = 3
            while len(ai_word_list) == 0 and retry_count < max_retries:
                # 视频文案
                self.signals.progressResultReady.emit(f'正在AI提取文案 (尝试 {retry_count + 1}/{max_retries})')
                ai_word_list = douBao_ai_strategy_content(title, f'这是原文案：{self.intro_text}，'
                                                                 f'需要把它按照不同的表述并且按指定格式结构输出返回'
                                                                 f'，文案中介绍的东西或地点的名称可能存在一些错误，'
                                                                 f'请根据标题描述把名称调整正确，内容主题不能改变，'
                                                                 f'文案整体的意思不变。')
                retry_count += 1
            
            if len(ai_word_list) == 0:
                self.signals.progressResultReady.emit('⚠️ 文案生成失败，使用原文案')
                # 将原文案分段作为备选
                ai_word_list = [self.intro_text[i:i+30] for i in range(0, len(self.intro_text), 30)]
            # 视频标签
            ai_topic = ','.join(deepseek_ai_strategy_topic(ai_title))
            if self.account_name != '':
                ai_topic = ai_topic + ',' + self.account_name

            ai_title_word_list = [ai_title] + [ai_topic] + ai_word_list

            # 将标题和文案写入excel表格中
            write_arrays_to_excel(self.copy_excel_file_path, ai_title_word_list)

            # 片段标签字符串列表
            tag_list_str_list = []

            for ai_word in ai_word_list:
                # 提取每个片段的关键词, 片段关键词列表
                tag_list = []
                tag_retry_count = 0
                while len(tag_list) == 0 and tag_retry_count < 3:
                    # 获取关键词
                    tag_retry_count += 1
                    tag_list = deepseek_ai_strategy_tag(ai_title, ai_word)

                # 关键词字符串
                tag_list_str = ','.join(tag_list)
                tag_list_str_list.append(tag_list_str)

            # 将片段标签写入excel表格中
            write_arrays_to_excel(self.label_excel_file_path, tag_list_str_list)

            self.signals.finished.emit('提取文案完成')
        except Exception as e:
            print(str(e))
            self.signals.errorOccurred.emit(str(e))


# # ai分析文案 问答知识类
class AiDisposeQATitle(QRunnable):
    def __init__(self, excel_file_path, account_name, title_id=-1):
        super().__init__()
        self.excel_file_path = excel_file_path
        self.account_name = account_name
        self.title_id = title_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 读取 Excel 文件
            df = _read_excel(self.excel_file_path)

            # 获取第二列的所有内容（除了第一行）
            second_column = df.iloc[0:, 1].tolist()  # iloc[1:, 1] 表示从第二行开始，第二列

            # 文案excel
            copy_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_copy')

            # 标签excel
            label_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_label')

            for i, title in enumerate(second_column):

                title = re.sub(r'\s+', '', title)

                # ai获取文案
                ai_word_list = []

                content_retry_count = 0
                while len(ai_word_list) == 0 and content_retry_count < 3:
                    content_retry_count += 1
                    self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题文案（第{content_retry_count}次）')
                    ai_word_list = douBao_ai_qa_content(title, '介绍的地方一定要符合标题要求，通常内容是需要介绍与标题相关的几个地方')

                ai_title = segment_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))

                ai_topic = ','.join(deepseek_ai_intro_topic(title))

                # 随机添加账号标签 #景点打卡#景点推荐     #旅游推荐官 #旅游景点#寻找中国最美城市

                if self.account_name != '':
                    ai_topic = ai_topic + ',' + self.account_name
                random_tag_list = ['景点打卡', '景点推荐', '旅游推荐官', '旅游景点', '寻找中国最美城市']
                import random
                # 随机选择两个标签添加到话题中，使用,分割
                random_tags = random.sample(random_tag_list, 2)
                ai_topic = ai_topic + ',' + ','.join(random_tags)

                ai_title_word_list = [ai_title] + [ai_topic] + ai_word_list

                # 将标题和文案写入excel表格中
                write_arrays_to_excel(copy_excel_file_path, ai_title_word_list)

                # 片段标签字符串列表
                tag_list_str_list = []

                for ai_word in ai_word_list:
                    # 提取每个片段的关键词, 片段关键词列表
                    tag_list = []
                    tag_retry_count = 0
                    while len(tag_list) == 0 and tag_retry_count < 3:
                        # 获取关键词
                        tag_retry_count += 1
                        self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题标签')
                        tag_list = deepseek_ai_intro_1_tag(title, ai_word)

                    # 关键词字符串
                    tag_list_str = ','.join(tag_list)
                    tag_list_str_list.append(tag_list_str)

                # 将片段标签写入excel表格中
                write_arrays_to_excel(label_excel_file_path, tag_list_str_list)
                self.signals.progressResultReady.emit(f'这是第{i + 1}个话题， 已经ai处理完成')
                if self.title_id != -1:
                    # 同步文案标签信息
                    update_video_title_info(self.title_id, '&&'.join(ai_title_word_list), '&&'.join(tag_list_str_list))
            self.signals.finished.emit('分析文案完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))


# ai分析文案 图片介绍类
class AiDisposeIMGTitle(QRunnable):
    def __init__(self, excel_file_path, account_name, title_id=-1):
        super().__init__()
        self.excel_file_path = excel_file_path
        self.account_name = account_name
        self.title_id = title_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 读取 Excel 文件
            df = _read_excel(self.excel_file_path)

            # 获取第二列的所有内容（除了第一行）
            second_column = df.iloc[0:, 1].tolist()  # iloc[1:, 1] 表示从第二行开始，第二列

            # 文案excel
            copy_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_copy')

            # 标签excel
            label_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_label')

            for i, title in enumerate(second_column):

                title = title

                # ai获取文案（最多重试3次）
                ai_word_list = []
                retry_count = 0
                max_retries = 3

                while len(ai_word_list) == 0 and retry_count < max_retries:
                    self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题文案（第{retry_count + 1}次尝试）')
                    ai_word_list = douBao_ai_sights_strategy_content(title, '详细的每日行程安排，包含交通、玩点、美食、注意事项')
                    retry_count += 1

                # 如果重试3次仍然失败，跳过该标题
                if len(ai_word_list) == 0:
                    self.signals.progressResultReady.emit(f'⚠️ 第{i + 1}个标题"{title}"AI生成失败，已跳过（JSON解析错误）')
                    continue

                # 将价格中的"r"替换为人民币符号"¥"（只匹配数字后的r，如120r/人→120¥/人）
                import re
                def replace_price_r(text):
                    if not isinstance(text, str):
                        return text
                    # 匹配数字后跟r的价格格式，如120r、10r/杯、80r/人
                    return re.sub(r'(\d+)r(?=/|$|[^a-zA-Z])', r'\1¥', text)

                for ai_word in ai_word_list:
                    for key, value in ai_word.items():
                        if isinstance(value, dict):
                            for sub_key, sub_value in value.items():
                                if isinstance(sub_value, str):
                                    value[sub_key] = replace_price_r(sub_value)
                        elif isinstance(value, str):
                            ai_word[key] = replace_price_r(value)

                ai_title = segment_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))
                # ai_title = deepseek_ai_strategy_title(title)
                ai_topic = ','.join(deepseek_ai_strategy_scenic_topic(title))

                if self.account_name != '':
                    ai_topic = ai_topic + ',' + self.account_name

                ai_title_word_list = [ai_title] + [ai_topic] + [json.dumps(d, ensure_ascii=False) for d in ai_word_list]

                # 将标题和文案写入excel表格中
                write_arrays_to_excel(copy_excel_file_path, ai_title_word_list)

                # 片段标签字符串列表
                tag_list_str_list = []

                for ai_word in ai_word_list:
                    # 提取每个片段的关键词（最多重试3次）
                    tag_list = []
                    tag_retry_count = 0

                    while len(tag_list) == 0 and tag_retry_count < max_retries:
                        # 获取关键词
                        self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题标签（第{tag_retry_count + 1}次尝试）')
                        tag_list = deepseek_ai_scenic_tag(title, str(ai_word))
                        tag_retry_count += 1

                    # 如果标签生成失败，使用空标签
                    if len(tag_list) == 0:
                        self.signals.progressResultReady.emit(f'⚠️ 第{i + 1}个标签生成失败，使用空标签')
                        tag_list = []

                    # 关键词字符串
                    tag_list_str = ','.join(tag_list)
                    tag_list_str_list.append(tag_list_str)

                # 将片段标签写入excel表格中
                write_arrays_to_excel(label_excel_file_path, tag_list_str_list)
                self.signals.progressResultReady.emit(f'这是第{i + 1}个话题， 已经ai处理完成')
                if self.title_id != -1:
                    # 同步文案标签信息
                    update_video_title_info(self.title_id, '&&'.join(ai_title_word_list), '&&'.join(tag_list_str_list))
            self.signals.finished.emit('分析文案完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))


# ai分析文案 素材通用类
class AiDisposeHistoryStrategyTitle(QRunnable):
    def __init__(self, excel_file_path, account_name, title_id=-1):
        super().__init__()
        self.excel_file_path = excel_file_path
        self.account_name = account_name
        self.title_id = title_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 读取 Excel 文件
            df = _read_excel(self.excel_file_path)

            # 获取第二列的所有内容（除了第一行）
            second_column = df.iloc[0:, 1].tolist()  # iloc[1:, 1] 表示从第二行开始，第二列

            # 文案excel
            copy_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_copy')

            # 标签excel
            label_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_label')

            for i, title in enumerate(second_column):

                title = title

                # ai获取文案
                ai_word_list = []

                content_retry_count = 0
                while len(ai_word_list) == 0 and content_retry_count < 3:
                    content_retry_count += 1
                    self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题文案（第{content_retry_count}次）')
                    ai_word_list = douBao_ai_history_strategy_content(title, '生成的文案需要介绍与标题相关的人物历史事迹，内容讲解需要有趣不无聊，'
                                                                     '，引人入胜需要适当点题，文案需要控制在大概4百字')

                # ai_title = segment_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))
                ai_title = deepseek_ai_strategy_title(title)
                ai_topic = ','.join(deepseek_ai_strategy_scenic_topic(','.join(ai_word_list)))

                if self.account_name != '':
                    ai_topic = ai_topic + ',' + self.account_name

                ai_title_word_list = [ai_title] + [ai_topic] + ai_word_list

                # 将标题和文案写入excel表格中
                write_arrays_to_excel(copy_excel_file_path, ai_title_word_list)

                # 片段标签字符串列表
                tag_list_str_list = []

                for ai_word in ai_word_list:
                    # 提取每个片段的关键词, 片段关键词列表
                    tag_list = []
                    tag_retry_count = 0
                    while len(tag_list) == 0 and tag_retry_count < 3:
                        # 获取关键词
                        tag_retry_count += 1
                        self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题标签')
                        tag_list = deepseek_ai_strategy_history_tag(title, ai_word)

                    # 关键词字符串
                    tag_list_str = ','.join(tag_list)
                    tag_list_str_list.append(tag_list_str)

                # 将片段标签写入excel表格中
                write_arrays_to_excel(label_excel_file_path, tag_list_str_list)
                self.signals.progressResultReady.emit(f'这是第{i + 1}个话题， 已经ai处理完成')
                if self.title_id != -1:
                    # 同步文案标签信息
                    update_video_title_info(self.title_id, '&&'.join(ai_title_word_list),
                                            '&&'.join(tag_list_str_list))
            self.signals.finished.emit('分析文案完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))


# ai分析文案 美食攻略类
class AiDisposeFoodStrategyTitle(QRunnable):
    def __init__(self, excel_file_path, account_name, title_id=-1):
        super().__init__()
        self.excel_file_path = excel_file_path
        self.account_name = account_name
        self.title_id = title_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 读取 Excel 文件
            df = _read_excel(self.excel_file_path)

            # 获取第二列的所有内容（除了第一行）
            second_column = df.iloc[0:, 1].tolist()  # iloc[1:, 1] 表示从第二行开始，第二列

            # 文案excel
            copy_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_copy')

            # 标签excel
            label_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_label')

            for i, title in enumerate(second_column):

                title = title

                # ai获取文案（最多重试2次）
                ai_word_list = []
                retry_count = 0
                max_retries = 2

                while len(ai_word_list) == 0 and retry_count < max_retries:
                    self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题文案（第{retry_count + 1}次尝试）')
                    ai_word_list = douBao_ai_food_strategy_content(title, '生成当地必吃的美食攻略，包含传统名菜、特色小吃，每个美食要有详细的特色介绍和价格信息')
                    retry_count += 1

                # 如果重试3次仍然失败，跳过该标题
                if len(ai_word_list) == 0:
                    self.signals.progressResultReady.emit(f'⚠️ 第{i + 1}个标题"{title}"AI生成失败，已跳过（JSON解析错误）')
                    continue

                ai_title = segment_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))
                ai_topic = ','.join(deepseek_ai_strategy_scenic_topic(title))

                if self.account_name != '':
                    ai_topic = ai_topic + ',' + self.account_name

                # 将JSON列表转换为字符串存储
                ai_title_word_list = [ai_title] + [ai_topic] + [json.dumps(d, ensure_ascii=False) for d in ai_word_list]

                # 将标题和文案写入excel表格中
                write_arrays_to_excel(copy_excel_file_path, ai_title_word_list)

                # 片段标签字符串列表
                tag_list_str_list = []

                for ai_word in ai_word_list:
                    # 提取每个片段的关键词（最多重试3次）
                    tag_list = []
                    tag_retry_count = 0

                    while len(tag_list) == 0 and tag_retry_count < max_retries:
                        # 获取关键词
                        self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题标签（第{tag_retry_count + 1}次尝试）')
                        # 使用json.dumps确保格式正确（不要用str()，会产生Python字典格式而非JSON）
                        ai_word_json = json.dumps(ai_word, ensure_ascii=False)
                        tag_list = deepseek_ai_scenic_tag(title, ai_word_json)
                        tag_retry_count += 1

                    # 如果标签生成失败，使用空标签
                    if len(tag_list) == 0:
                        self.signals.progressResultReady.emit(f'⚠️ 第{i + 1}个标签生成失败，使用空标签')
                        tag_list = []

                    # 关键词字符串
                    tag_list_str = ','.join(tag_list)
                    tag_list_str_list.append(tag_list_str)

                # 将片段标签写入excel表格中
                write_arrays_to_excel(label_excel_file_path, tag_list_str_list)
                self.signals.progressResultReady.emit(f'这是第{i + 1}个话题， 已经ai处理完成')
                if self.title_id != -1:
                    # 同步文案标签信息
                    update_video_title_info(self.title_id, '&&'.join(ai_title_word_list), '&&'.join(tag_list_str_list))
            self.signals.finished.emit('分析文案完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))


# ai分析文案 节日风俗类
class AiDisposeFestivalCustomsTitle(QRunnable):
    def __init__(self, excel_file_path, account_name, title_id=-1):
        super().__init__()
        self.excel_file_path = excel_file_path
        self.account_name = account_name
        self.title_id = title_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            # 读取 Excel 文件
            df = _read_excel(self.excel_file_path)

            # 获取第二列的所有内容（除了第一行）
            second_column = df.iloc[0:, 1].tolist()  # iloc[1:, 1] 表示从第二行开始，第二列

            # 文案excel
            copy_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_copy')

            # 标签excel
            label_excel_file_path = add_suffix_to_file_path(self.excel_file_path, '_label')

            for i, title in enumerate(second_column):

                title = title

                # ai获取文案（最多重试3次）
                ai_word_list = []
                retry_count = 0
                max_retries = 3

                while len(ai_word_list) == 0 and retry_count < max_retries:
                    self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题文案（第{retry_count + 1}次尝试）')
                    ai_word_list = douBao_ai_festival_customs_content(title, '生成传统节日或民族风俗相关内容，包含风俗名称、简介寓意、具体做法、时间地域等信息')
                    retry_count += 1

                # 如果重试3次仍然失败，跳过该标题
                if len(ai_word_list) == 0:
                    self.signals.progressResultReady.emit(f'⚠️ 第{i + 1}个标题"{title}"AI生成失败，已跳过（JSON解析错误）')
                    continue

                ai_title = segment_title(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', title))
                ai_topic = ','.join(deepseek_ai_strategy_scenic_topic(title))

                if self.account_name != '':
                    ai_topic = ai_topic + ',' + self.account_name

                # 将JSON列表转换为字符串存储
                ai_title_word_list = [ai_title] + [ai_topic] + [json.dumps(d, ensure_ascii=False) for d in ai_word_list]

                # 将标题和文案写入excel表格中
                write_arrays_to_excel(copy_excel_file_path, ai_title_word_list)

                # 片段标签字符串列表
                tag_list_str_list = []

                for ai_word in ai_word_list:
                    # 提取每个片段的关键词（最多重试3次）
                    tag_list = []
                    tag_retry_count = 0

                    while len(tag_list) == 0 and tag_retry_count < max_retries:
                        # 获取关键词 - 使用专门的节日风俗标签生成函数
                        self.signals.progressResultReady.emit(f'这是第{i + 1}个， 正在ai提取该话题标签（第{tag_retry_count + 1}次尝试）')
                        tag_list = douBao_ai_festival_customs_tag(title, str(ai_word))
                        tag_retry_count += 1

                    # 如果标签生成失败，使用空标签
                    if len(tag_list) == 0:
                        self.signals.progressResultReady.emit(f'⚠️ 第{i + 1}个标签生成失败，使用空标签')
                        tag_list = []

                    # 关键词字符串
                    tag_list_str = ','.join(tag_list)
                    tag_list_str_list.append(tag_list_str)

                # 将片段标签写入excel表格中
                write_arrays_to_excel(label_excel_file_path, tag_list_str_list)
                self.signals.progressResultReady.emit(f'这是第{i + 1}个话题， 已经ai处理完成')
                if self.title_id != -1:
                    # 同步文案标签信息
                    update_video_title_info(self.title_id, '&&'.join(ai_title_word_list), '&&'.join(tag_list_str_list))
            self.signals.finished.emit('分析文案完成')
        except Exception as e:
            self.signals.errorOccurred.emit(str(e))

