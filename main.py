# 主页面
import asyncio
import ctypes
import hashlib
import json
import math
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from collections import defaultdict, Counter
from datetime import datetime

from pathlib import Path
from typing import List


def _prepare_qt_runtime():
    """Make the bundled Qt DLL directory explicit before importing PyQt6."""
    if not getattr(sys, "frozen", False):
        return

    runtime_root = Path(sys.executable).resolve().parent / "_internal"
    qt_bin = runtime_root / "PyQt6" / "Qt6" / "bin"
    if not qt_bin.is_dir():
        return

    os.environ["PATH"] = str(qt_bin) + os.pathsep + os.environ.get("PATH", "")
    os.environ["QT_PLUGIN_PATH"] = str(qt_bin.parent / "plugins")
    try:
        os.add_dll_directory(str(qt_bin))
    except (AttributeError, OSError):
        pass


def _write_qt_load_diagnostics(import_error):
    """Record native loader errors so unsupported target systems are actionable."""
    try:
        executable_dir = Path(sys.executable).resolve().parent
        internal_dir = executable_dir / "_internal"
        qt_bin = internal_dir / "PyQt6" / "Qt6" / "bin"
        candidates = [qt_bin, internal_dir]
        lines = [
            "PyQt6 import failed",
            f"error={import_error!r}",
            f"python={sys.version}",
            f"platform={platform.platform()}",
            f"executable={sys.executable}",
            f"qt_bin={qt_bin}",
        ]
        try:
            lines.append(f"windows={sys.getwindowsversion()!r}")
        except AttributeError:
            pass

        for directory in candidates:
            lines.append(f"directory={directory} exists={directory.is_dir()}")

        win_dll = getattr(ctypes, "WinDLL", None)
        for name in (
            "Qt6Core.dll",
            "Qt6Gui.dll",
            "Qt6Widgets.dll",
            "icu.dll",
            "icuin.dll",
            "icuuc.dll",
            "msvcp140.dll",
            "vcruntime140.dll",
            "ucrtbase.dll",
            "QtWidgets.pyd",
        ):
            for directory in candidates:
                candidate = directory / name
                if not candidate.is_file():
                    lines.append(f"{candidate}: MISSING")
                    continue
                if win_dll is None:
                    lines.append(f"{candidate}: PRESENT (WinDLL unavailable)")
                    continue
                try:
                    win_dll(str(candidate))
                    lines.append(f"{candidate}: LOAD_OK size={candidate.stat().st_size}")
                except OSError as error:
                    lines.append(
                        f"{candidate}: LOAD_FAIL winerror={getattr(error, 'winerror', None)} "
                        f"errno={getattr(error, 'errno', None)} message={error}"
                    )

        (executable_dir / "qt_load_diagnostics.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
    except Exception:
        # Diagnostics must never hide the original import exception.
        pass


_prepare_qt_runtime()

import send2trash
import mysql.connector
import zhconv
try:
    from PyQt6 import QtWidgets
except ImportError as error:
    _write_qt_load_diagnostics(error)
    raise
from PyQt6.QtCore import QEventLoop, QThreadPool, Qt, QUrl, QRect, QPoint
from PyQt6.QtGui import QFont, QColor, QPixmap, QStandardItemModel, QStandardItem, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox, QFileDialog, QColorDialog, QSlider, QPushButton, QLabel, \
    QStackedWidget, QTableWidgetItem, QTableWidget
from openpyxl.workbook import Workbook

from ai_tool.ai_text_production import write_arrays_to_excel, title_keyword, \
    ai_analyse_title_special_tag, ai_analyse_title_usual_tag
from ai_tool.runtime_config import ai_error_message, get_ai_config, save_ai_config
from database_tool.user_load_tool import add_user_task, get_account_by_name, update_image_user_by_id
from database_tool.mysql_read_tool import fetch_with_retry
from database_tool.material_download_tool import get_last_material_download_error
from database_tool.video_load_tool import get_videos_by_keyword_1, get_videos_by_keyword, download_video, get_random_id, \
    add_lost_video_record, cut_video_by_audio_length, get_random_cover_video, get_cover_video_collect_all, download_cover_video, ftp_ai_upload, \
    download_cn_video, get_video_model_list, delete_video_model, \
    update_video_model, add_video_model, get_random_video_model, get_unused_title_info, mark_title_generated, \
    add_lost_cn_video_record, record_unsuccess_title_info, upload_video_info_to_site, upload_video_pic_to_site, \
    get_content_label, download_afr_video, get_afr_random_id, get_afr_videos_by_keyword, merge_videos, merge_videos_with_duration, \
    get_random_cover_video_by_cate, \
    download_word_pic, get_random_cover_pic, mark_title_ftp_uploaded, ftp_upload_video_to_site, get_person_pic_path, \
    get_person_id, download_person_pic
from excel_tool.excel_tool import get_first_data_row, get_row_data, write_to_excel, write_to_old_excel
from ffmpeg_tool.add_watermark_tool import add_watermark
from ffmpeg_tool.subtitles_audio_tool import get_audio_length, add_subtitles
from ffmpeg_tool.video_concat_tool import get_video_duration, concatenate_videos_in_segments, \
    extract_and_blur_random_frame
from title_setting.title_part_setting import TitlePartSetting
from title_setting.title_setting import TitleSetting
from ui.batch_ai_autocut import Ui_batch_ai_autocut
from ui.new_batch_ai_autocut import Ui_new_batch_ai_autocut
from worker.add_music_worker import AddMusicWorker
from worker.add_pic_worker import AddPicWorker
from worker.add_person_pic_worker import AddPersonPicWorker
from ffmpeg_tool.add_green_screen_tool import add_green_screen_overlay_to_video
from worker.add_watermark_worker import AddWatermarkWorker
from worker.compress_video_worker import CompressVideoWorker
from worker.add_green_screen_worker import AddGreenScreenWorker
from worker.ai_worker import AiDisposeIntroTitle, AiDisposeStrategyTitle, AiDisposeCNIntroTitle, AiDisposeMsIntroTitle, \
    AiDisposeIntro, AiDisposeStrategy, AiDisposeWordIntroTitle, AiDisposeMaterialStrategyTitle, \
    AiDisposeLifeStrategyTitle, AiDisposeScenicSpotTitle, AiDisposeQATitle, AiDisposeIMGTitle, \
    AiDisposeHistoryStrategyTitle, AiDisposeFoodStrategyTitle, AiDisposeFestivalCustomsTitle
from worker.composite_video_worker import CompositeVideo
from worker.composite_word_intro_video_worker import CompositeWordIntroVideo
from worker.sa_worker import SaWorker, SaDHWorker
from worker.test_audio_worker import TestAudioWorker
from sanong_generation.composer import SanongComposer, SanongComposeOptions
from runtime_errors import (
    MEMORY_EXHAUSTION_MESSAGE,
    is_memory_exhaustion,
    is_system_generation_error,
)
from windows_app_identity import apply_native_window_icon, set_process_app_id
import logging

# # 设置日志配置
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     filename='app.log',
#     filemode='a'
# )
MAX_LINES = 50


def runtime_asset_path(relative_path):
    """Find an asset beside the executable, then inside PyInstaller's bundle."""
    relative_path = Path(relative_path)
    roots = []
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent)
    bundle_dir = getattr(sys, "_MEIPASS", "")
    if bundle_dir:
        roots.append(Path(bundle_dir))
    roots.append(Path.cwd())
    roots.append(Path(__file__).resolve().parent)

    seen = set()
    for root in roots:
        candidate = (root / relative_path).resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return candidate
    return None


def _read_excel(*args, **kwargs):
    """Load pandas only for spreadsheet workflows, keeping startup light."""
    import pandas as pd

    return pd.read_excel(*args, **kwargs)


# 账号轮询相关函数
def get_account_available_title_types(account_name):
    """获取账号可用的标题类型列表"""
    today_pattern = f"%{datetime.now().strftime('%Y-%m-%d')}%"
    query = """
        SELECT DISTINCT title_type
        FROM video_title_info
        WHERE is_generate = 0
        AND account_name = %s
        AND (last_time IS NULL OR last_time NOT LIKE %s)
        ORDER BY title_type
    """
    result = fetch_with_retry(
        {
            'host': '82.157.237.217', 'database': 'ai_video',
            'user': 'ljx_lepin123', 'password': 'ea.367GZX!#EmwfpEYW$f', 'port': '35008'
        },
        query,
        (account_name, today_pattern),
        fetch_all=True,
        operation_name='获取账号可用标题类型',
    )
    return [row[0] for row in result] if result is not None else []


def get_title_info_by_type(account_name, title_type):
    """根据账号和标题类型获取标题信息"""
    today_pattern = f"%{datetime.now().strftime('%Y-%m-%d')}%"
    query = """
        SELECT * FROM video_title_info
        WHERE is_generate = 0
        AND account_name = %s
        AND title_type = %s
        AND (last_time IS NULL OR last_time NOT LIKE %s)
        ORDER BY RAND() LIMIT 1
    """
    return fetch_with_retry(
        {
            'host': '82.157.237.217', 'database': 'ai_video',
            'user': 'ljx_lepin123', 'password': 'ea.367GZX!#EmwfpEYW$f', 'port': '35008'
        },
        query,
        (account_name, title_type, today_pattern),
        operation_name='根据类型获取标题信息',
    )


def get_account_last_index():
    """获取账号轮询的最后一次索引"""
    index_file = os.path.join(os.getcwd(), 'account_polling_index.txt')
    try:
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                return int(f.read().strip())
    except:
        pass
    return 0


def save_account_index(index):
    """保存账号轮询索引"""
    index_file = os.path.join(os.getcwd(), 'account_polling_index.txt')
    try:
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(str(index))
    except Exception as e:
        print(f"保存账号索引失败: {e}")


def get_account_last_type_index(account_name):
    """获取账号内标题类型轮询的最后一次索引"""
    index_file = os.path.join(os.getcwd(), f'account_type_index_{account_name}.txt')
    try:
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                return int(f.read().strip())
    except:
        pass
    return 0


def get_polling_type_by_priority(account_name, available_title_types):
    """
    根据新的轮询规则获取标题类型
    规则：除类型5外的其他类型进行三轮交替生成，然后加入类型5
    
    例如:
        [2, 5, 7] -> 优先类型 [2, 7] 交替三轮: 2,7,2,7,2,7，然后是 5，循环
        [1, 2, 5, 7] -> 优先类型 [1, 2, 7] 交替三轮: 1,2,7,1,2,7,1,2,7，然后是 5，循环
    
    参数:
        account_name: 账号名称
        available_title_types: 可用的标题类型列表，例如 [2, 5, 7] 或 [1, 2, 5, 7]
    
    返回:
        selected_type: 选中的标题类型
    """
    # 获取当前索引
    current_index = get_account_last_type_index(account_name)

    # 如果没有类型或只有一个类型，直接返回
    if not available_title_types:
        return None
    if len(available_title_types) == 1:
        return available_title_types[0]

    # 检查是否包含类型5
    if 5 not in available_title_types:
        # 如果不包含类型5，按正常顺序轮询
        return available_title_types[current_index % len(available_title_types)]

    # 分离优先类型（除类型5外）和延迟类型（类型5）
    priority_types = [t for t in available_title_types if t != 5]
    delayed_type = 5

    # 计算一个完整循环的长度：优先类型循环三轮，再加上延迟类型
    cycle_length = len(priority_types) * 3 + 1  # 3轮优先类型 + 1个延迟类型

    # 在循环中的位置
    position = current_index % cycle_length

    # 如果在前三轮优先类型范围内
    if position < len(priority_types) * 3:
        type_index = position % len(priority_types)
        return priority_types[type_index]
    else:
        # 到了延迟类型的位置
        return delayed_type


def save_account_type_index(account_name, index):
    """保存账号内标题类型轮询索引"""
    index_file = os.path.join(os.getcwd(), f'account_type_index_{account_name}.txt')
    try:
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(str(index))
    except Exception as e:
        print(f"保存账号类型索引失败: {e}")


class BatchAICutter(QWidget, Ui_new_batch_ai_autocut):

    def __init__(self):
        super(BatchAICutter, self).__init__()
        self.pic_time = None
        self.part_title_part_setting = None
        self.setupUi(self)
        self.all_setting_dict = read_dict_from_txt('setting.txt')
        self.part_title_setting_win = None
        self.title_setting_win = None
        self.video_url = ''
        self.thread_pool = QThreadPool.globalInstance()
        # 自动生成时，任务入库不应依赖“是否上传服务器”复选框。
        self._auto_generation_active = False
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        icon_path = runtime_asset_path("tb.ico")
        if icon_path is not None:
            self.setWindowIcon(QIcon(str(icon_path)))

        self.step_timings = {}
        self.video_start_time = 0

        self.dragging = False  # 拖动状态
        self.resizing = False  # 缩放状态
        self.drag_pos = QPoint()
        self.last_rect = QRect()  # 记录最大化前的窗口位置和大小
        self.resize_direction = None  # 缩放方向

        self.minBtn.clicked.connect(self.showMinimized)
        self.maxBtn.clicked.connect(self.toggle_maximize)
        self.closeBtn.clicked.connect(self.close)

        # 绑定可拖动Widget的鼠标事件
        # 拖动相关变量
        self.dragging = False  # 是否正在拖动
        self.drag_offset = QPoint()  # 鼠标相对于窗口的偏移量
        self.widget.mousePressEvent = self.on_drag_press
        self.widget.mouseMoveEvent = self.on_drag_move
        self.widget.mouseReleaseEvent = self.on_drag_release

        # 模板选项
        pic_folder = 'soft_pic'
        current_directory = os.getcwd()
        pic_folder_path = os.path.join(current_directory, pic_folder)
        # 设置选择设置文件
        logo_pic_path = os.path.join(pic_folder_path, 'cylogo.png')
        self.label_4.setPixmap(QPixmap(logo_pic_path))

        # 初始化所有的tab图片
        self.init_tab_pic()

        # self.tabWidget.tabBar().hide()
        # 事件循环
        self.loop = QEventLoop()
        # 失败标签
        self.error_flag = False
        self.last_error_message = ''
        self._consecutive_system_failures = 0
        self._stop_auto_generation = False
        # tts角色
        self.audio_role_list = ["zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural", "zh-CN-XiaoxuanNeural",
                                "zh-CN-XiaoyiNeural", "zh-CN-YunjianNeural", "zh-CN-YunxiaNeural",
                                "zh-CN-YunyangNeural", "zh-CN-liaoning-XiaobeiNeural", "zh-CN-shaanxi-XiaoniNeural"]

        # 百度角色
        self.audio_bd_role_list = [
            '度小宇:1',
            '度小美:0',
            '度逍遥:3',
            '度丫丫:4',
            '度逍遥-情感男声:5003',
            '度小鹿-甜美女声:5118',
            '度博文-专业男主播:106',
            '度小娇-成熟女主播:5',
            '度逍遥-情感男声:4003',
            '度博文-专业男主播:4106',
            '度小贤-电台男主播:4115',
            '度常盈-电台女主播:5147',
            '度小皮-萌娃童声:5976',
            '度皮特-老外男声:5971',
            '度阿肯-主播男声:4164',
            '度有为-磁性男声:4176',
            '度小新-播音女声:4259',
            '度小鹿-甜美女声:4119',
            '度灵儿-清激女声:4105',
            '度小乔-活泼女声:4117',
            '度晴岚-甜美女声:4288',
            '度青川-温柔男声:4192',
            '度小雯-活力女主播:4100',
            '度米朵-可爱女声:4103',
            '度姗姗-娱乐女声:4144',
            '度小贝-知识女主播:4278',
            '度清风-配音男声:4143',
            '度小新-专业女主播:4140',
            '度小彦-知识男主播:4129',
            '度星河-广告男声:4149',
            '度小清-广告女声:4254',
            '度博文-综艺男声:4206',
            '度云朵-可爱童声:4147',
            '度婉婉-甜美女声:4141',
            '南方-电台女主播:4226',
            '度泽言-温暖男声:4179',
            '度禧禧-阳光女声:4146',
            '度小柔-温柔女声:6567',
            '度言浩-年轻男声:4156',
            '度涵竹-开朗女声:4189',
            '度嫣然-活泼女声:4194',
            '度泽言-开朗男声:4193',
            '度怀安-磁性男声:4195',
            '度清影-甜美女声:4196',
            '度沁遥-知性女声:4197']
        self.stack = QStackedWidget()
        self.stack.setMaximumSize(660, 430)
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background: #000000;")
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        # 8. 播放完回到图片
        self.media_player.mediaStatusChanged.connect(
            lambda s: self.stack.setCurrentWidget(self.image_label)
            if s == QMediaPlayer.MediaStatus.EndOfMedia else None
        )

        # self.verticalLayout.addWidget(self.video_widget)

        self.image_label = QLabel()
        self.image_label.setStyleSheet("background-color:black;")
        self.image_label.setMinimumSize(660, 430)
        pixmap = QPixmap("img.jpg")  # 替换为你的图片路径
        pixmap = pixmap.scaled(660, 430, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 添加到布局
        self.stack.addWidget(self.image_label)  # index 0
        self.stack.addWidget(self.video_widget)  # index 1
        self.verticalLayout.addWidget(self.stack)

        # 预览标题
        self.previewTitleTypeButton.clicked.connect(self.showPreviewTitleInTestVideo)

        # 预览小标题
        self.previewPartTitleTypeButton.clicked.connect(self.showPreviewPartTitleInTestVideo)

        # # 预览字幕
        # self.previewToolButton.clicked.connect(self.apply_preview_style)

        # 试听音频
        self.testAudioToolButton.clicked.connect(self.playTestAudio1)

        self.testAudioToolButton_2.clicked.connect(self.playTestAudio2)

        # 视频类别点击事件
        self.videoTypeComboBox.currentIndexChanged.connect(self.select_video_type)

        # 修改选择视频模板，就使用改设置
        self.videoModelSetComboBox.currentIndexChanged.connect(self.select_video_model_set)

        # 保存当前设置
        self.addVideoModelSetPushButton.clicked.connect(self.save_video_model_set)

        self.showPartTitlePartOneSetting()
        self.modifyOneOfPartTitleTypeButton.clicked.connect(self.showPartTitlePartOneSetting)

        # 音频设置
        self.audioSpeedHorizontalSlider.valueChanged.connect(self.updateSpeedLabel)
        self.audioVolumeHorizontalSlider.valueChanged.connect(self.updateVolumeLabel)

        self.audioSpeedHorizontalSlider_2.valueChanged.connect(self.updateSpeedLabel_2)
        self.audioVolumeHorizontalSlider_2.valueChanged.connect(self.updateVolumeLabel_2)
        self.audioToneHorizontalSlider_2.valueChanged.connect(self.updateToneLabel_2)

        self.showModelSetList()

        # 以下其他按钮事件

        # 保存大标题样式
        self.modifyTitleTypeButton.clicked.connect(self.showTitleSetting)

        # 大标题排版样式
        self.titleTypeComboBox.currentIndexChanged.connect(self.saveTitleType)

        # 保存小标题样式
        # self.modifyPartTitleTypeButton.clicked.connect(self.showPartTitleSetting)
        self.showPartTitleSetting()

        # 保存音频设置
        self.saveVioceSettButton.clicked.connect(self.saveVideoSetting)

        # 保存字幕设置
        self.savePreviewToolButton.clicked.connect(self.saveSrtSetting)

        # 保存水印设置
        self.saveWaterButton.clicked.connect(self.saveWaterSetting)

        # 打开excel
        self.openTilteFileButton.clicked.connect(self.openTitleExcel)

        # ai处理
        self.aiProductButton.clicked.connect(self.aiDisposeTitle)

        # 打开copy
        self.openCopyFileButton.clicked.connect(self.openCopyExcel)

        # 打开label
        self.openLabelFileButton.clicked.connect(self.openLabelExcel)

        # 合成视频
        self.compositeVideoButton.clicked.connect(self.compositeVideo)

        # 存放视频位置
        self.saveVideoToolButton.clicked.connect(self.selectSaveVideoPath)

        # 字体颜色
        self.fontColorToolButton.clicked.connect(self.choose_font_color)

        # 边框颜色
        self.borderColorToolButton.clicked.connect(self.choose_border_color)

        # 背景颜色
        self.shadowColorToolButton.clicked.connect(self.choose_background_color)

        # 片尾视频选择保存
        self.endVideoToolButton.clicked.connect(self.select_end_video)

        # 账号所属地区
        self.accountLocationLineEdit.textChanged.connect(self.select_account_location)

        # 水印选择
        self.selectPicVideoToolButton.clicked.connect(self.selectWaterMarkPic)

        # # 选择上传视频位置
        # self.selectUploadVideoToolButton.clicked.connect(self.chooseUploadVideoDirPath)

        # # 同步视频到站点
        # self.confirmVideoUploadPushButton.clicked.connect(self.uploadVideoToSite)

        # 查看引用
        self.applyModelButton.clicked.connect(self.video_model_select)

        # 删除视频模板
        self.deleteModelButton.clicked.connect(self.video_model_delete)

        # 更新覆盖模板
        self.updateModelButton.clicked.connect(self.video_model_update)

        # 新镇增加模板
        self.addModelButton.clicked.connect(self.video_model_add)

        # 自动生成视频
        self.autoGenerateButton.clicked.connect(self.auto_generate)

        # 视频类型
        self.videoTypeComboBox.addItems(
            ['景点介绍类', '美食介绍类', '城市通用类', '全国景点介绍类', '图片文字介绍类', '素材通用类', '励志通用类',
             '景点通用类', '历史视频类', '问答知识类', '图片攻略类', '地方攻略类', '节日风俗类'])

        # 小标题分段
        self.oneOfNumComboBox.addItems(['第一段', '第二段', '第三段', '第四段', '第五段'])

        # 标题设置切换
        self.titleTypeButton.clicked.connect(self.setTitleTypePic)

        # 配音设置切换
        self.vioceSetButton.clicked.connect(self.setVioceSetPic)

        # 字幕水印设置切换
        self.srtSetButton.clicked.connect(self.setSrtSetPic)

        # 生成视频切换
        self.productVideoButton.clicked.connect(self.setProductVideo)

        # 随机模板
        self.videoModelButton.clicked.connect(self.setVideoModel)

        # ai设置切换
        self.aiSetButton.clicked.connect(self.setAiSet)
        self.toolButton.clicked.connect(self.save_ai_settings)
        self.label_13.setText('AI 接口设置')
        self.aiAutoUpdateCheckBox = QtWidgets.QCheckBox('自动更新同档位模型', self.widget_23)
        self.aiAutoUpdateCheckBox.setGeometry(40, 285, 175, 30)
        self.aiAutoUpdateCheckBox.setStyleSheet('color: white;')
        self.aiAutoUpdateCheckBox.setToolTip('每天首次 AI 任务检查同服务商、同系列和同档位的新版；验证可用后保存，失败时保留原模型')
        self.load_ai_settings()

        # 分段切换
        self.oneOfNumComboBox.currentIndexChanged.connect(self.on_currentIndexChanged)

        # edge tts
        self.edgeApiButton.clicked.connect(self.selectEdgeTTSApi)

        # baidu
        self.baiduApiButton.clicked.connect(self.selectBaiduApi)

        # 识别音频处理文案
        self.scriptVideoToolButton.clicked.connect(self.select_script_file_path)
        self.getScriptToolButton.clicked.connect(self.get_copy_from_video)

        # 模板选项
        video_model_folder_name = 'video_model_set'
        current_directory = os.getcwd()
        video_model_folder_path = os.path.join(current_directory, video_model_folder_name)
        os.makedirs(video_model_folder_path, exist_ok=True)
        self.videoModelSetComboBox.clear()
        self.videoModelSetComboBox.addItems(
            ['默认'] + [f for f in os.listdir(video_model_folder_path) if f.endswith('.txt')])

        # 初始化设置
        self.init_setting()

        # 自动检查更新
        self.auto_check_update()

    def toggle_maximize(self):
        """切换最大化/还原状态"""
        if self.isMaximized():
            # 还原窗口
            self.showNormal()
            self.setGeometry(self.last_rect)  # 恢复之前的位置和大小
            self.maxBtn.setText("□")
        else:
            # 最大化窗口
            self.last_rect = self.geometry()  # 记录当前位置和大小
            self.showMaximized()
            self.maxBtn.setText("◱")

    def on_drag_press(self, event):
        """鼠标按下：记录偏移量"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            # 计算鼠标相对于窗口左上角的偏移量（关键）
            # 窗口全局位置：self.mapToGlobal(QPoint(0, 0))
            # 鼠标全局位置：event.globalPosition().toPoint()
            self.drag_offset = event.globalPosition().toPoint() - self.mapToGlobal(QPoint(0, 0))
            event.accept()

    def on_drag_move(self, event):
        """鼠标移动：拖动窗口"""
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            # 根据偏移量计算新位置
            new_pos = event.globalPosition().toPoint() - self.drag_offset
            self.move(new_pos)
            event.accept()

    def on_drag_release(self, event):
        """鼠标释放：结束拖动"""
        self.dragging = False

    def setTitleTypePic(self):
        self.init_tab_pic()
        pic_folder = 'soft_pic'
        current_directory = os.getcwd()
        pic_folder_path = os.path.join(current_directory, pic_folder)
        # 设置选择设置文件
        pic_path = os.path.join(pic_folder_path, '1-1.png')
        self.titleTypeButton.setIcon(QIcon(QPixmap(pic_path)))
        self.tabWidget.setCurrentIndex(0)

    def setVioceSetPic(self):
        self.init_tab_pic()
        pic_folder = 'soft_pic'
        current_directory = os.getcwd()
        pic_folder_path = os.path.join(current_directory, pic_folder)
        # 设置选择设置文件
        pic_path = os.path.join(pic_folder_path, '2-1.png')
        self.vioceSetButton.setIcon(QIcon(QPixmap(pic_path)))
        self.tabWidget.setCurrentIndex(1)

    def setSrtSetPic(self):
        self.init_tab_pic()
        pic_folder = 'soft_pic'
        current_directory = os.getcwd()
        pic_folder_path = os.path.join(current_directory, pic_folder)
        # 设置选择设置文件
        pic_path = os.path.join(pic_folder_path, '3-1.png')
        self.srtSetButton.setIcon(QIcon(QPixmap(pic_path)))
        self.tabWidget.setCurrentIndex(2)

    def setProductVideo(self):
        self.init_tab_pic()
        pic_folder = 'soft_pic'
        current_directory = os.getcwd()
        pic_folder_path = os.path.join(current_directory, pic_folder)
        # 设置选择设置文件
        pic_path = os.path.join(pic_folder_path, '4-1.png')
        self.productVideoButton.setIcon(QIcon(QPixmap(pic_path)))
        self.tabWidget.setCurrentIndex(3)

    def setVideoModel(self):
        self.init_tab_pic()
        pic_folder = 'soft_pic'
        current_directory = os.getcwd()
        pic_folder_path = os.path.join(current_directory, pic_folder)
        # 设置选择设置文件
        pic_path = os.path.join(pic_folder_path, '5-1.png')
        self.videoModelButton.setIcon(QIcon(QPixmap(pic_path)))
        self.tabWidget.setCurrentIndex(4)

    def setAiSet(self):
        self.load_ai_settings()
        self.init_tab_pic()
        pic_folder = 'soft_pic'
        current_directory = os.getcwd()
        pic_folder_path = os.path.join(current_directory, pic_folder)
        # 设置选择设置文件
        pic_path = os.path.join(pic_folder_path, '6-1.png')
        self.aiSetButton.setIcon(QIcon(QPixmap(pic_path)))
        self.tabWidget.setCurrentIndex(5)

    def load_ai_settings(self):
        try:
            config = get_ai_config(require_key=False)
        except RuntimeError as error:
            self.add_log(str(error))
            return
        self.apiBaseUrlLineEdit.setText(config['base_url'])
        self.aiModelNameLineEdit.setText(config['model'])
        self.apiKeyLineEdit.setText(config['api_key'])
        self.aiAutoUpdateCheckBox.setChecked(config['auto_update_model'])

    def save_ai_settings(self):
        try:
            path = save_ai_config({
                'base_url': self.apiBaseUrlLineEdit.text(),
                'model': self.aiModelNameLineEdit.text(),
                'api_key': self.apiKeyLineEdit.text(),
                'auto_update_model': self.aiAutoUpdateCheckBox.isChecked(),
            })
            self.load_ai_settings()
            self.add_log(f'AI 配置已保存并立即生效：{path}')
            QMessageBox.information(self, 'AI 配置', '配置已保存，后续文案、话题和标签将使用此配置，无需重启。')
        except (OSError, RuntimeError) as error:
            QMessageBox.warning(self, 'AI 配置保存失败', str(error))

    def on_currentIndexChanged(self):
        self.showPartTitlePartOneSetting()

    # 7. 一行切换函数
    def play_video(self):
        self.stack.setCurrentWidget(self.video_widget)
        self.media_player.play()

    def pauseVideo(self):
        self.media_player.pause()  # 暂停视频

    def setPosition(self, position):
        # 设置播放进度
        self.media_player.setPosition(position)

    def init_tab_pic(self):
        # 模板选项
        pic_folder = 'soft_pic'
        current_directory = os.getcwd()
        pic_folder_path = os.path.join(current_directory, pic_folder)
        # 设置选择设置文件
        pic_1_path = os.path.join(pic_folder_path, '1.png')
        pic_2_path = os.path.join(pic_folder_path, '2.png')
        pic_3_path = os.path.join(pic_folder_path, '3.png')
        pic_4_path = os.path.join(pic_folder_path, '4.png')
        pic_5_path = os.path.join(pic_folder_path, '5.png')
        pic_6_path = os.path.join(pic_folder_path, '6.png')
        self.titleTypeButton.setIcon(QIcon(QPixmap(pic_1_path)))
        self.vioceSetButton.setIcon(QIcon(QPixmap(pic_2_path)))
        self.srtSetButton.setIcon(QIcon(QPixmap(pic_3_path)))
        self.productVideoButton.setIcon(QIcon(QPixmap(pic_4_path)))
        self.videoModelButton.setIcon(QIcon(QPixmap(pic_5_path)))
        self.aiSetButton.setIcon(QIcon(QPixmap(pic_6_path)))

    def init_setting(self):

        self.videoTypeComboBox.setCurrentIndex(int(self.all_setting_dict['video_type']['type']))

        self.oneOfNumComboBox.setCurrentIndex(0)

        # 小标题
        self.showPartTitleSetting()

        #  字幕设置
        self.zm_setting_init()

        # 初始化设置 配音
        self.voice_setting_init()

        # 初始化设置 水印
        self.water_setting_init()

        # 片尾选择初始化
        self.end_video_init()

        # 所属地区
        if self.all_setting_dict.get('account_location'):
            self.accountLocationLineEdit.setText(self.all_setting_dict['account_location']['location'])
        else:
            self.accountLocationLineEdit.clear()

    # 初始化字幕设置
    def zm_setting_init(self):

        # 标题样式设置
        self.titleTypeComboBox.setCurrentIndex(int(self.all_setting_dict['title_type']['type']))

        # 字幕字体
        self.fontFamilyComboBox.setCurrentFont(QFont(self.all_setting_dict['srt_set']['fontFamily']))

        # 边框大小
        self.borderSizeSpin.setValue(int(self.all_setting_dict['srt_set']['fontBorderSize']))

        # 阴影深度
        self.shadowDepthSpin.setValue(int(self.all_setting_dict['srt_set']['shadowDepth']))

        # 字体颜色
        self.fontColorLineEdit.setText(self.all_setting_dict['srt_set']['fontColor'])

        # 边框颜色
        self.borderColorLineEdit.setText(self.all_setting_dict['srt_set']['borderColor'])

        # 阴影颜色
        self.shadowColorLineEdit.setText(self.all_setting_dict['srt_set']['shadowColor'])

        # 粗体
        if self.all_setting_dict['srt_set']['fontBold'] == -1:
            self.boldCheck.setChecked(True)
        else:
            self.boldCheck.setChecked(False)

        # 斜体
        if self.all_setting_dict['srt_set']['fontItalic'] == -1:
            self.italicCheck.setChecked(True)
        else:
            self.italicCheck.setChecked(False)

        # 下划线
        if self.all_setting_dict['srt_set']['fontUnderline'] == -1:
            self.underlineCheck.setChecked(True)
        else:
            self.underlineCheck.setChecked(False)

    # 初始化音频设置
    def voice_setting_init(self):

        # tts
        self.audioRoleComboBox.addItems(self.audio_role_list)

        # 百度
        self.audioRoleComboBox_2.addItems(self.audio_bd_role_list)

        self.speedLabel.setText(f"{self.all_setting_dict['voice_set']['spd_0']}%")
        self.volumeLabel.setText(f"{self.all_setting_dict['voice_set']['vol_0']}")

        self.speedLabel_2.setText(f"{self.all_setting_dict['voice_set']['spd_1']}")
        self.volumeLabel_2.setText(f"{self.all_setting_dict['voice_set']['vol_1']}")
        self.toneLabel_2.setText(f"{self.all_setting_dict['voice_set']['pit_1']}")

        if self.all_setting_dict['voice_set']['api_type'] == 0:
            self.freeApiRadioButton.setChecked(True)
            self.audioRoleComboBox.setCurrentIndex(self.all_setting_dict['voice_set']['role_0'])
            self.audioSpeedHorizontalSlider.setValue(self.all_setting_dict['voice_set']['spd_0'])
            self.audioVolumeHorizontalSlider.setValue(self.all_setting_dict['voice_set']['vol_0'])

        elif self.all_setting_dict['voice_set']['api_type'] == 1:
            self.bdApiRadioButton.setChecked(True)
            self.audioRoleComboBox_2.setCurrentIndex(self.all_setting_dict['voice_set']['role_1'])
            self.audioSpeedHorizontalSlider_2.setValue(self.all_setting_dict['voice_set']['spd_1'])
            self.audioVolumeHorizontalSlider_2.setValue(self.all_setting_dict['voice_set']['vol_1'])
            self.audioToneHorizontalSlider_2.setValue(self.all_setting_dict['voice_set']['pit_1'])

    # 初始化水印设置
    def water_setting_init(self):
        self.selectPicPathLabel.setText(self.all_setting_dict['water_set']['filePath'])

        self.picWatermarkSpaceComboBox.setCurrentIndex(self.all_setting_dict['water_set']['position'])

        self.ZoomPicDoubleSpinBox.setValue(self.all_setting_dict['water_set']['zoom'])

        self.alphaPicDoubleSpinBox.setValue(self.all_setting_dict['water_set']['alpha'])

        # 水印位置选择
        self.picWatermarkSpaceComboBox.addItems(['左上角', '右上角', '左下角', '右下角', '水平居中', '垂直居中'])

    def end_video_init(self):
        if 'end_video' in self.all_setting_dict:
            self.endVideoPathLabel.setText(self.all_setting_dict['end_video']['end_video_path'])
        else:
            self.endVideoPathLabel.setText('')

    def add_log(self, text: str):
        """添加日志，最新信息显示在最上面"""
        cursor = self.run_label.textCursor()

        # 保存当前滚动位置
        scroll_bar = self.run_label.verticalScrollBar()
        was_at_bottom = scroll_bar.value() >= scroll_bar.maximum() - 10

        # 在开头插入最新日志
        cursor.movePosition(cursor.MoveOperation.Start)
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_text = f"[{timestamp}] {text}"
        cursor.insertText(log_text + '\n')

        # 超限时删除最后一行旧行
        if self.run_label.document().blockCount() > MAX_LINES:
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()

        # 移动光标到顶部并可见
        cursor.movePosition(cursor.MoveOperation.Start)
        self.run_label.setTextCursor(cursor)
        self.run_label.ensureCursorVisible()

    def get_upload_accounts(self, account_name):
        """获取发布账号；自动生成时始终读取账号以创建数据库任务。"""
        if not self._auto_generation_active and not self.uploadCheckBox.isChecked():
            return []
        return get_account_by_name(account_name)

    # 音频语速更新
    def updateSpeedLabel(self, value):
        # 更新语速标签
        speed = value  # 转换为百分比
        self.speedLabel.setText(f"{speed}%")

    # 音频音量更新
    def updateVolumeLabel(self, value):
        # 更新音量标签
        volume = value
        self.volumeLabel.setText(f"{volume}")

    # 音频语速更新
    def updateSpeedLabel_2(self, value):
        # 更新语速标签
        speed = value  # 转换为百分比
        self.speedLabel_2.setText(f"{speed}")

    # 音频音量更新
    def updateVolumeLabel_2(self, value):
        # 更新音量标签
        volume = value
        self.volumeLabel_2.setText(f"{volume}")

    def updateToneLabel_2(self, value):
        # 更新语速标签
        tone = value  # 转换为百分比
        self.toneLabel_2.setText(f"{tone}")

    def showTitleSetting(self):
        self.modifyTitleTypeButton.setStyleSheet("""
                           QPushButton {
                               background-color: rgb(19, 171, 234);
                               color: white;
                           }
                           """)
        self.modifyOneOfPartTitleTypeButton.setStyleSheet("""
                           QPushButton {
                            color: rgb(255, 255, 255);
	                        background-color: rgb(22, 23, 25);
                           }
                           """)
        # 大标题设置
        while self.verticalLayout_4.count():
            item = self.verticalLayout_4.takeAt(0)  # 从布局中移除
            if item.widget():  # 如果是控件
                w = item.widget()
                w.setParent(None)  # 从父控件脱离
                w.deleteLater()
        self.verticalLayout_4.addWidget(TitleSetting('1'))
        self.tabWidget_2.setCurrentIndex(1)
        # self.title_setting_win.show()

    def showPartTitleSetting(self):
        # 大标题设置
        while self.verticalLayout_6.count():
            item = self.verticalLayout_6.takeAt(0)  # 从布局中移除
            if item.widget():  # 如果是控件
                w = item.widget()
                w.setParent(None)  # 从父控件脱离
                w.deleteLater()
        # 小标题设置
        self.verticalLayout_6.addWidget(TitleSetting('2'))

    def showPartTitlePartOneSetting(self):
        self.modifyTitleTypeButton.setStyleSheet("""
                                   QPushButton {
                                      color: rgb(255, 255, 255);
	                           background-color: rgb(22, 23, 25);
                                   }
                                   """)
        self.modifyOneOfPartTitleTypeButton.setStyleSheet("""
                   QPushButton {
                       background-color: rgb(19, 171, 234);
                       color: white;
                   }
                   """)
        if self.oneOfNumComboBox.currentIndex() == -1:
            part_num = 0
        else:
            part_num = self.oneOfNumComboBox.currentIndex()
        self.part_title_part_setting = TitlePartSetting(part_num)
        while self.verticalLayout_7.count():
            item = self.verticalLayout_7.takeAt(0)  # 从布局中移除
            if item.widget():  # 如果是控件
                w = item.widget()
                w.setParent(None)  # 从父控件脱离
                w.deleteLater()
        self.verticalLayout_7.addWidget(self.part_title_part_setting)
        self.tabWidget_2.setCurrentIndex(0)

    def selectEdgeTTSApi(self):
        self.baiduApiButton.setStyleSheet("""
                                           QPushButton {
                                              color: rgb(255, 255, 255);
        	                                  background-color: rgb(22, 23, 25);
                                           }
                                           """)
        self.edgeApiButton.setStyleSheet("""
                           QPushButton {
                               background-color: rgb(19, 171, 234);
                               color: white;
                           }
                           """)
        self.tabWidget_3.setCurrentIndex(0)

    def selectBaiduApi(self):
        self.edgeApiButton.setStyleSheet("""
                                                   QPushButton {
                                                      color: rgb(255, 255, 255);
                	                                  background-color: rgb(22, 23, 25);
                                                   }
                                                   """)
        self.baiduApiButton.setStyleSheet("""
                                   QPushButton {
                                       background-color: rgb(19, 171, 234);
                                       color: white;
                                   }
                                   """)
        self.tabWidget_3.setCurrentIndex(1)

    def saveVideoSetting(self):
        # 配音
        voice_set_dict = {
            'api_type': 0 if self.freeApiRadioButton.isChecked() else 1,
            'role_0': self.audioRoleComboBox.currentIndex(),
            'spd_0': self.audioSpeedHorizontalSlider.value(),
            'vol_0': self.audioVolumeHorizontalSlider.value(),
            'role_1': self.audioRoleComboBox_2.currentIndex(),
            'pit_1': self.audioToneHorizontalSlider_2.value(),
            'spd_1': self.audioSpeedHorizontalSlider_2.value(),
            'vol_1': self.audioVolumeHorizontalSlider_2.value()
        }

        with open('setting.txt', 'r', encoding='utf-8') as file:
            dictionary = json.load(file)

        dictionary[f'voice_set'] = voice_set_dict

        write_dict_to_txt('setting.txt', dictionary)

        msg_box = QMessageBox()
        msg_box.setStyleSheet("""
             QMessageBox QLabel {
             background-color: rgb(22, 23, 25);
             color: rgb(255, 255, 255);
            }
            QMessageBox {
            background-color: rgb(22, 23, 25);
            color: rgb(255, 255, 255);
            }
        """)
        msg_box.setWindowTitle("提示")
        msg_box.setText(f"保存配音设置完成")
        msg_box.exec()

    def saveTitleType(self):

        title_type_dict = {
            'type': self.titleTypeComboBox.currentIndex(),
        }
        with open('setting.txt', 'r', encoding='utf-8') as file:
            dictionary = json.load(file)

        dictionary['title_type'] = title_type_dict

        write_dict_to_txt('setting.txt', dictionary)

    def saveSrtSetting(self):
        title_set_dict = {
            'fontFamily': self.fontFamilyComboBox.currentFont().family(),  # 字体
            'fontBorderSize': self.borderSizeSpin.value(),  # 边框大小
            'shadowDepth': self.shadowDepthSpin.value(),  # 阴影大小
            'fontBold': -1 if self.boldCheck.isChecked() else 0,  # 粗体
            'fontColor': self.fontColorLineEdit.text(),  # 字体颜色
            'fontSize': '16',  # 字体大小
            'fontItalic': -1 if self.italicCheck.isChecked() else 0,  # 斜体
            'borderColor': self.borderColorLineEdit.text(),  # 边框颜色
            'fontUnderline': -1 if self.underlineCheck.isChecked() else 0,  # 下划线
            'shadowColor': self.shadowColorLineEdit.text(),  # 阴影颜色
            'position': 0,
        }
        with open('setting.txt', 'r', encoding='utf-8') as file:
            dictionary = json.load(file)

        dictionary[f'srt_set'] = title_set_dict

        write_dict_to_txt('setting.txt', dictionary)

        msg_box = QMessageBox()
        msg_box.setStyleSheet("""
             QMessageBox QLabel {
             background-color: rgb(22, 23, 25);
             color: rgb(255, 255, 255);
            }
            QMessageBox {
            background-color: rgb(22, 23, 25);
            color: rgb(255, 255, 255);
            }
        """)
        msg_box.setWindowTitle("提示")
        msg_box.setText(f"保存字幕设置完成")
        msg_box.exec()

    def saveWaterSetting(self):
        # 水印
        water_set_dict = {
            'filePath': self.selectPicPathLabel.text(),
            'position': self.picWatermarkSpaceComboBox.currentIndex(),
            'zoom': self.ZoomPicDoubleSpinBox.value(),
            'alpha': self.alphaPicDoubleSpinBox.value()
        }

        with open('setting.txt', 'r', encoding='utf-8') as file:
            dictionary = json.load(file)

        dictionary[f'water_set'] = water_set_dict

        write_dict_to_txt('setting.txt', dictionary)

        msg_box = QMessageBox()
        msg_box.setStyleSheet("""
             QMessageBox QLabel {
             background-color: rgb(22, 23, 25);
             color: rgb(255, 255, 255);
            }
            QMessageBox {
            background-color: rgb(22, 23, 25);
            color: rgb(255, 255, 255);
            }
        """)
        msg_box.setWindowTitle("提示")
        msg_box.setText(f"保存水印设置完成")
        msg_box.exec()

    # 保存当前设置
    def save_video_model_set(self):
        video_model_set_name = self.videoModelNameLineEdit.text() + '.txt'
        # 模板选项
        video_model_folder_name = 'video_model_set'
        current_directory = os.getcwd()
        video_model_folder_path = os.path.join(current_directory, video_model_folder_name)
        os.makedirs(video_model_folder_path, exist_ok=True)
        # 设置选择设置文件
        video_model_set_path = os.path.join(video_model_folder_path, video_model_set_name)
        copy_txt_overwrite('setting.txt', video_model_set_path)
        if os.path.exists(video_model_folder_path):
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                 QMessageBox QLabel {
                 background-color: rgb(22, 23, 25);
                 color: rgb(255, 255, 255);
                }
                QMessageBox {
                background-color: rgb(22, 23, 25);
                color: rgb(255, 255, 255);
                }
            """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"保存模板设置完成")
            msg_box.exec()
            if self.videoModelSetComboBox.findText(video_model_set_name) == -1:
                self.videoModelSetComboBox.addItem(video_model_set_name)
                self.videoModelSetComboBox.setCurrentIndex(self.videoModelSetComboBox.count() - 1)

    # 选择视频模板
    def select_video_model_set(self):
        if self.videoModelSetComboBox.currentIndex() != 0:
            video_model_set_name = self.videoModelSetComboBox.currentText()
            self.videoModelNameLineEdit.setText(video_model_set_name.replace('.txt', ''))
            self.accountNameLineEdit.setText(video_model_set_name.replace('.txt', ''))
            # 模板选项
            video_model_folder_name = 'video_model_set'
            current_directory = os.getcwd()
            video_model_folder_path = os.path.join(current_directory, video_model_folder_name)
            os.makedirs(video_model_folder_path, exist_ok=True)
            if os.path.exists(video_model_folder_path):
                # 设置选择设置文件
                video_model_set_path = os.path.join(video_model_folder_path, video_model_set_name)
                copy_txt_overwrite(video_model_set_path, 'setting.txt')
                self.all_setting_dict = read_dict_from_txt('setting.txt')
                self.init_setting()

    # 选择片尾
    def select_end_video(self):
        input_file, _ = QFileDialog.getOpenFileName(self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mkv)")
        if input_file:
            self.endVideoPathLabel.setText(input_file)

            end_video_dict = {
                'end_video_path': str(input_file)
            }
            with open('setting.txt', 'r', encoding='utf-8') as file:
                dictionary = json.load(file)

            dictionary['end_video'] = end_video_dict

            write_dict_to_txt('setting.txt', dictionary)

    # 账号所属地区
    def select_account_location(self):
        location = self.accountLocationLineEdit.text()
        location_dict = {
            'location': str(location)
        }
        with open('setting.txt', 'r', encoding='utf-8') as file:
            dictionary = json.load(file)

        dictionary['account_location'] = location_dict

        write_dict_to_txt('setting.txt', dictionary)

    # 视频类型选择
    def select_video_type(self):

        video_type_dict = {
            'type': str(self.videoTypeComboBox.currentIndex())
        }
        with open('setting.txt', 'r', encoding='utf-8') as file:
            dictionary = json.load(file)

        dictionary['video_type'] = video_type_dict

        write_dict_to_txt('setting.txt', dictionary)

    def selectWaterMarkPic(self):
        image_file, _ = QFileDialog.getOpenFileName(self, "Open Image File", "",
                                                    "Image Files (*.jpg *.jpeg *.png *.bmp *.gif)")
        if image_file:
            self.selectPicPathLabel.setText(image_file)

    def openTitleExcel(self):
        # 打开文件对话框，只允许选择 Excel 文件
        excel_file, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "",
                                                    "Excel Files (*.xlsx *.xls)")
        if excel_file:
            self.titleFileLabel.setText(excel_file)

    def openCopyExcel(self):
        # 打开文件对话框，只允许选择 Excel 文件
        excel_file, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "",
                                                    "Excel Files (*.xlsx *.xls)")
        if excel_file:
            self.copyFileLabel.setText(excel_file)

    def openLabelExcel(self):
        # 打开文件对话框，只允许选择 Excel 文件
        excel_file, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "",
                                                    "Excel Files (*.xlsx *.xls)")
        if excel_file:
            self.labelFilelabel.setText(excel_file)

    def aiDisposeTitle(self):

        # 创建确认框
        confirmation_dialog = QMessageBox(self)
        confirmation_dialog.setWindowTitle("确认操作")
        confirmation_dialog.setText(f"<b style='color:red'>{self.accountNameLineEdit.text()}</b>"
                                    f"<b style='color:white'>确定是</b>"
                                    f"<b style='color:red'>{self.videoTypeComboBox.currentText()}</b>"
                                    f"<b style='color:white'>吗？确认则开始处理</b>")
        confirmation_dialog.setIcon(QMessageBox.Icon.Question)  # 设置问号图标

        # 创建自定义按钮
        no_button = confirmation_dialog.addButton("No", QMessageBox.ButtonRole.RejectRole)
        yes_button = confirmation_dialog.addButton("Yes", QMessageBox.ButtonRole.AcceptRole)

        # 设置按钮样式
        yes_button.setStyleSheet("QPushButton { color: red; }")
        no_button.setStyleSheet("QPushButton { color: red; }")

        # 显示确认框并获取用户响应
        reply = confirmation_dialog.exec()

        # 2. 根据返回值决定是否继续
        if reply != QMessageBox.DialogCode.Accepted:
            return

        title_file_path = self.titleFileLabel.text()

        account_name = self.accountNameLineEdit.text()
        # if account_name == '':
        #     QMessageBox.information(self, "提示", f"请输入账号名称")
        #     return

        if os.path.exists(title_file_path):
            self.run_label.setText('正在ai分析处理话题标题')
            # 默认上饶景点介绍
            ai_worker = AiDisposeIntroTitle(title_file_path, account_name)
            if self.videoTypeComboBox.currentIndex() == 0:
                # 上饶景点介绍
                ai_worker = AiDisposeIntroTitle(title_file_path, account_name)
            if self.videoTypeComboBox.currentIndex() == 1:
                # 上饶美食介绍
                ai_worker = AiDisposeMsIntroTitle(title_file_path, account_name)
            if self.videoTypeComboBox.currentIndex() == 2:
                # 上饶城市通用
                ai_worker = AiDisposeStrategyTitle(title_file_path, account_name)
            if self.videoTypeComboBox.currentIndex() == 3:
                # 全国景点介绍
                ai_worker = AiDisposeCNIntroTitle(title_file_path, account_name)
            if self.videoTypeComboBox.currentIndex() == 4:
                # 图片文字介绍
                ai_worker = AiDisposeWordIntroTitle(title_file_path, account_name)
            if self.videoTypeComboBox.currentIndex() == 5:
                # 通用素材材料
                ai_worker = AiDisposeMaterialStrategyTitle(title_file_path, account_name)
            if self.videoTypeComboBox.currentIndex() == 6:
                # 励志鸡汤通用
                ai_worker = AiDisposeLifeStrategyTitle(title_file_path, account_name)
            if self.videoTypeComboBox.currentIndex() == 7:
                # 景点通用
                ai_worker = AiDisposeScenicSpotTitle(title_file_path, account_name)
            if self.videoTypeComboBox.currentIndex() == 8:
                # 历史视频类 - 使用全国景点介绍的AI处理
                ai_worker = AiDisposeHistoryStrategyTitle(title_file_path, account_name)
            if self.videoTypeComboBox.currentIndex() == 9:
                # 问答知识类
                ai_worker = AiDisposeQATitle(title_file_path, account_name)
            if self.videoTypeComboBox.currentIndex() == 10:
                # 图片介绍类
                ai_worker = AiDisposeIMGTitle(title_file_path, account_name)
            if self.videoTypeComboBox.currentIndex() == 11:
                # 美食攻略类
                ai_worker = AiDisposeFoodStrategyTitle(title_file_path, account_name)
            if self.videoTypeComboBox.currentIndex() == 12:
                # 节日风俗类
                ai_worker = AiDisposeFestivalCustomsTitle(title_file_path, account_name)

            ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
            ai_worker.signals.finished.connect(self.on_success_occurred)
            ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
            QThreadPool.globalInstance().start(ai_worker)

        # 获取文件的目录、文件名和扩展名
        file_dir = os.path.dirname(title_file_path)  # 文件所在的目录
        file_name = os.path.basename(title_file_path)  # 文件名（包含扩展名）
        name, ext = os.path.splitext(file_name)  # 分离文件名和扩展名

        # 文案文件名
        copy_file_name = f"{name}{'_copy'}{ext}"
        copy_file_path = os.path.join(file_dir, copy_file_name)

        # 标签文件名
        label_file_name = f"{name}{'_label'}{ext}"
        label_file_path = os.path.join(file_dir, label_file_name)

        self.copyFileLabel.setText(copy_file_path)

        self.labelFilelabel.setText(label_file_path)

    def selectSaveVideoPath(self):
        select_path = QFileDialog.getExistingDirectory(self, "Select Video Folder", "")
        if os.path.exists(select_path):
            self.saveVideoPathLabel.setText(select_path)
            # self.selectUploadVideoPathLabel.setText(select_path)

    # 字体颜色选择
    def choose_font_color(self):
        color = QColorDialog.getColor(QColor(self.fontColorLineEdit.text()), self)
        if color.isValid():
            self.fontColorLineEdit.setText(color.name())

    # 边框颜色选择
    def choose_border_color(self):
        color = QColorDialog.getColor(QColor(self.borderColorLineEdit.text()), self)
        if color.isValid():
            self.borderColorLineEdit.setText(color.name())

    # 阴影颜色选择
    def choose_background_color(self):
        color = QColorDialog.getColor(QColor(self.shadowColorLineEdit.text()), self)
        if color.isValid():
            self.shadowColorLineEdit.setText(color.name())

    def showPreviewTitleInTestVideo(self):
        self.all_setting_dict = read_dict_from_txt('setting.txt')
        # 清除媒体源
        self.media_player.setSource(QUrl())
        # 测试字幕源文件
        test_preview_srt_title = 'test_preview_srt_title.srt'
        # 测试字幕特效文件
        test_preview_ass_title = 'test_preview_ass_title.ass'
        # 测试视频
        test_preview_video = 'test_preview_video0.mp4'
        # 测试输出视频
        test_output_preview_video = 'test_output_preview_title_video.mp4'

        if os.path.exists(test_output_preview_video):
            # 删除之前视频
            os.remove(test_output_preview_video)

        if self.screenComboBox.currentIndex() == 1:
            test_preview_video = 'test_preview_video1.mp4'

        test_title = self.testTitleLineEdit.text().replace('|', '')

        modify_srt_file(test_preview_srt_title, '你好世界', test_title)

        create_title(self.all_setting_dict, '1', self.screenComboBox.currentIndex(),
                     self.testTitleLineEdit.text(), test_preview_ass_title, test_preview_srt_title
                     )

        asyncio.run(add_subtitles(test_preview_ass_title, test_preview_video, test_output_preview_video))

        self.run_label.setText('标题预览视频生成')

        self.media_player.setSource(QUrl.fromLocalFile(test_output_preview_video))  # 设置视频文件

        self.video_url = test_output_preview_video

        self.play_video()  # 播放视频

    # 生成预览小标题的视频
    def showPreviewPartTitleInTestVideo(self):

        self.all_setting_dict = read_dict_from_txt('setting.txt')

        # 清除媒体源
        self.media_player.setSource(QUrl())

        # 测试字幕源文件
        test_preview_srt_part_title = 'test_preview_srt_part_title.srt'
        # 测试字幕特效文件
        test_preview_ass_part_title = 'test_preview_ass_part_title.ass'

        # 测试视频
        test_preview_video = 'test_preview_video0.mp4'
        # 测试输出视频
        test_output_preview_video = 'test_output_preview_part_title_video.mp4'

        if os.path.exists(test_output_preview_video):
            # 删除之前视频
            os.remove(test_output_preview_video)

        if self.screenComboBox.currentIndex() == 1:
            test_preview_video = 'test_preview_video1.mp4'

        test_title = self.testPartTitleLineEdit.text()

        modify_srt_file(test_preview_srt_part_title, '你好世界', test_title)

        create_title(self.all_setting_dict, '2', self.screenComboBox.currentIndex(),
                     self.testPartTitleLineEdit.text(), test_preview_ass_part_title, test_preview_srt_part_title
                     )

        asyncio.run(add_subtitles(test_preview_ass_part_title, test_preview_video, test_output_preview_video))

        self.run_label.setText('片段标题预览视频生成')

        self.media_player.setSource(QUrl.fromLocalFile(test_output_preview_video))  # 设置视频文件

        self.video_url = test_output_preview_video

        self.play_video()  # 播放视频

    def apply_preview_style(self):
        self.all_setting_dict = read_dict_from_txt('setting.txt')
        tamp_folder_name = 'tempConcateVideo'
        current_directory = os.getcwd()
        tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
        video_tamp_path_name = 'video_cache_file'
        video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)
        srt_file_name = f"temp_subtitle1.srt"
        # 原字幕文件
        part_subtitle_url = os.path.join(video_tamp_path, srt_file_name)
        ass_path = part_subtitle_url.replace('.srt', '.ass')

        # 转换成ass
        convert_srt_to_ass(part_subtitle_url, ass_path, self.all_setting_dict['srt_set'])

        # 清除媒体源
        self.media_player.setSource(QUrl())
        if ass_path:

            # test_preview_video = self.temp_video_list[i].part_video_url

            # if test_preview_video == '':

            if self.screenComboBox.currentIndex() == 1:
                test_preview_video = 'test_preview_video1.mp4'
            else:
                test_preview_video = 'test_preview_video0.mp4'

            file_dir = os.path.dirname(ass_path)
            test_output_preview_video = os.path.join(file_dir, f'test_preview_ass_zm_video1.mp4')

            asyncio.run(
                add_subtitles(ass_path, test_preview_video,
                              test_output_preview_video))

            self.run_label.setText('片段字幕预览视频生成')

            self.media_player.setSource(QUrl.fromLocalFile(test_output_preview_video))  # 设置视频文件
            try:
                self.play_video()  # 播放视频
            except Exception as e:
                print(f'播放错误{str(e)}')
            self.video_url = test_output_preview_video

        # 播放测试音频

    def playTestAudio1(self):
        self.media_player.setSource(QUrl())

        # delete_file_if_exists("testoutput.mp3")

        audio_role = self.audio_role_list[self.audioRoleComboBox.currentIndex()]

        test_text = self.testAudioLineEdit.text()

        speed_value = str(self.audioSpeedHorizontalSlider.value())

        if not str(speed_value).startswith('-'):
            speed_value = '+' + speed_value

        speed_value = speed_value + '%'

        volume_value = self.audioVolumeHorizontalSlider.value()

        audio_setting = {
            'api_type': 1,
            'audio_role': audio_role,
            'test_text': test_text,
            'speed_value': speed_value,
            'volume_value': volume_value
        }

        playTest_worker = TestAudioWorker(audio_setting)
        playTest_worker.signals.testAudioResultReady.connect(self.playAudio)
        QThreadPool.globalInstance().start(playTest_worker)

    def playTestAudio2(self):
        self.media_player.setSource(QUrl())

        # delete_file_if_exists("testoutput.mp3")

        audio_role_2 = int(self.audio_bd_role_list[self.audioRoleComboBox_2.currentIndex()].split(':')[1])

        speed_value_2 = self.audioSpeedHorizontalSlider_2.value()

        volume_value_2 = self.audioVolumeHorizontalSlider_2.value()

        tone_value_2 = self.audioToneHorizontalSlider_2.value()

        test_text = self.testAudioLineEdit_2.text()

        audio_setting = {
            'api_type': 2,
            'test_text': test_text,
            'audio_role': audio_role_2,
            'speed_value': speed_value_2,
            'tone_value': tone_value_2,
            'volume_value': volume_value_2
        }

        playTest_worker = TestAudioWorker(audio_setting)
        playTest_worker.signals.testAudioResultReady.connect(self.playAudio)
        QThreadPool.globalInstance().start(playTest_worker)

        # 播放音频

    def playAudio(self):
        audio_url = QUrl.fromLocalFile("testoutput.mp3")
        self.media_player.setSource(audio_url)  # 设置测试音频文件
        self.media_player.play()

    def on_process_result_ready(self, result):
        self.run_label.setText(result)

    def on_success_occurred(self, _result=None):
        self.error_flag = False
        self.last_error_message = ''
        self._consecutive_system_failures = 0
        self.loop.quit()

    def on_error_occurred(self, error_message=''):
        self.error_flag = True
        self.last_error_message = ai_error_message(error_message) or str(error_message or '未知错误')
        self.add_log(f'处理失败：{self.last_error_message}')
        if is_memory_exhaustion(error_message):
            self._stop_auto_generation = True
            self.add_log(MEMORY_EXHAUSTION_MESSAGE)
            if QApplication.instance() is not None:
                QMessageBox.warning(self, '内存不足', MEMORY_EXHAUSTION_MESSAGE)
        elif is_system_generation_error(error_message):
            self._consecutive_system_failures += 1
            self.add_log(
                f'系统错误连续计数：{self._consecutive_system_failures}/3'
            )
            if self._consecutive_system_failures >= 3:
                self._stop_auto_generation = True
                self.add_log('连续 3 次系统错误，自动生成已停止；当前标题未标记成功。')
        else:
            self._consecutive_system_failures = 0
        QApplication.processEvents()
        self.loop.quit()

    # 合成视频
    def compositeVideo(self):

        # 1. 弹出确认框
        # 创建确认框
        confirmation_dialog = QMessageBox(self)
        confirmation_dialog.setWindowTitle("确认操作")
        confirmation_dialog.setText(f"<b style='color:red'>{self.accountNameLineEdit.text()}</b>"
                                    f"<b style='color:white'>确定是</b>"
                                    f"<b style='color:red'>{self.videoTypeComboBox.currentText()}</b>"
                                    f"<b style='color:white'>吗？确认则开始处理</b>", )
        confirmation_dialog.setIcon(QMessageBox.Icon.Question)  # 设置问号图标

        # 创建自定义按钮
        no_button = confirmation_dialog.addButton("No", QMessageBox.ButtonRole.RejectRole)
        yes_button = confirmation_dialog.addButton("Yes", QMessageBox.ButtonRole.AcceptRole)

        # 设置按钮样式
        yes_button.setStyleSheet("QPushButton { color: red; }")
        no_button.setStyleSheet("QPushButton { color: red; }")

        # 显示确认框并获取用户响应
        reply = confirmation_dialog.exec()

        # 2. 根据返回值决定是否继续
        if reply != QMessageBox.DialogCode.Accepted:
            self.compositeVideoButton.setEnabled(True)
            return

        self.compositeVideoButton.setEnabled(False)

        copy_path = self.copyFileLabel.text()

        label_path = self.labelFilelabel.text()

        out_dir_path = self.saveVideoPathLabel.text()

        account_name = self.accountNameLineEdit.text()

        # 景点介绍类
        if self.videoTypeComboBox.currentIndex() == 0:
            self.compositeIntroVideo(copy_path, label_path, out_dir_path, account_name)

        # 美食介绍类
        if self.videoTypeComboBox.currentIndex() == 1:
            self.compositeMsInforVideo(copy_path, label_path, out_dir_path, account_name)

        # 城市通用类
        if self.videoTypeComboBox.currentIndex() == 2:
            self.compositeCityStrategyVideo(copy_path, label_path, out_dir_path, account_name)

        # 全国介绍类
        if self.videoTypeComboBox.currentIndex() == 3:
            self.compositeCNIntroVideo(copy_path, label_path, out_dir_path, account_name)

        # 文字介绍类
        if self.videoTypeComboBox.currentIndex() == 4:
            self.compositeWordIntroVideo(copy_path, out_dir_path, account_name)

        # 素材通用类
        if self.videoTypeComboBox.currentIndex() == 5:
            self.compositeMaterialStrategyVideo(copy_path, out_dir_path, account_name, label_path)

        # 励志通用类
        if self.videoTypeComboBox.currentIndex() == 6:
            self.compositeLifeStrategyVideo(copy_path, out_dir_path, account_name)

        # 景点通用类
        if self.videoTypeComboBox.currentIndex() == 7:
            self.compositeScenicSpotVideo(copy_path, label_path, out_dir_path, account_name)

        # 历史视频类
        if self.videoTypeComboBox.currentIndex() == 8:
            self.compositeGreenScreenVideo(copy_path, label_path, out_dir_path, account_name)

        # 问答知识类
        if self.videoTypeComboBox.currentIndex() == 9:
            self.compositeQaVideo(copy_path, label_path, out_dir_path, account_name)

        # 图片介绍类
        if self.videoTypeComboBox.currentIndex() == 10:
            self.compositeImageIntroVideo(copy_path, label_path, out_dir_path, account_name)

        # 美食攻略类
        if self.videoTypeComboBox.currentIndex() == 11:
            self.compositeLocalStrategyVideo(copy_path, label_path, out_dir_path, account_name)

        # 节日风俗类
        if self.videoTypeComboBox.currentIndex() == 12:
            self.compositeFestivalCustomsVideo(copy_path, label_path, out_dir_path, account_name)

        self.compositeVideoButton.setEnabled(True)

    # 自动生成视频
    def auto_generate(self):
        self.autoGenerateButton.setEnabled(False)
        self._auto_generation_active = True
        self._stop_auto_generation = False
        self._consecutive_system_failures = 0
        try:
            self._auto_generate_impl()
        except Exception as error:
            if hasattr(self, 'on_error_occurred'):
                self.on_error_occurred(error)
            else:
                self.add_log(f'自动生成异常：{error}')
            QApplication.processEvents()
        finally:
            self._auto_generation_active = False
            self.autoGenerateButton.setEnabled(True)

    def _auto_generate_impl(self):
        clean_cache()
        clean_cut_cache()
        clean_title_cache()
        clean_permanent_cache(max_size_gb=100)  # 清理永久缓存，限制100GB
        clean_temp_files()  # 清理临时文件
        # 运行次数
        times = self.compositeTimeSpinBox.value()
        now_times = 0

        # 初始化账号轮询索引
        account_last_index = get_account_last_index()

        # 获取所有账号
        video_model_folder_name = 'video_model_set'
        current_directory = os.getcwd()
        video_model_folder_path = os.path.join(current_directory, video_model_folder_name)
        os.makedirs(video_model_folder_path, exist_ok=True)
        account_name_list = [f.replace('.txt', '') for f in os.listdir(video_model_folder_path) if
                             f.endswith('.txt')]

        if not account_name_list:
            self.add_log('没有找到账号配置文件')
            return

        attempt_count = 0
        max_attempts = max(times * len(account_name_list) * 3, times)
        while (
            now_times < times
            and attempt_count < max_attempts
            and not self._stop_auto_generation
        ):
            attempt_count += 1
            # 账号轮询：从上次的位置开始
            current_account_index = account_last_index % len(account_name_list)
            account_name = account_name_list[current_account_index]

            # 更新账号索引为下次使用
            account_last_index = (current_account_index + 1) % len(account_name_list)
            save_account_index(account_last_index)

            # 设置账号配置文件
            video_model_folder_name = 'video_model_set'
            current_directory = os.getcwd()
            video_model_folder_path = os.path.join(current_directory, video_model_folder_name)
            os.makedirs(video_model_folder_path, exist_ok=True)
            if os.path.exists(video_model_folder_path):
                # 设置选择设置文件
                video_model_set_path = os.path.join(video_model_folder_path, account_name + '.txt')
                copy_txt_overwrite(video_model_set_path, 'setting.txt')
                self.all_setting_dict = read_dict_from_txt('setting.txt')

            # 创建存储文件夹
            today_str = datetime.now().strftime("%Y%m%d")
            root = Path(os.getcwd()).anchor  # Windows 得到 'C:'，Linux 得到 '/'
            folder = Path(root) / "Ai视频" / account_name / today_str
            folder.mkdir(parents=True, exist_ok=True)
            out_dir_path = str(folder)

            # 获取该账号可用的标题类型列表
            available_title_types = get_account_available_title_types(account_name)

            if not available_title_types:
                self.add_log(f'{account_name}没有可用的标题类型')
                QApplication.processEvents()
                continue

            # 标题类型轮询：根据新的优先级规则获取类型
            # 规则：除类型5外的其他类型进行三轮交替生成，然后加入类型5
            # 如果不包含类型5，则按正常顺序轮询
            selected_title_type = get_polling_type_by_priority(account_name, available_title_types)

            # 更新类型索引为下次使用（递增索引）
            current_type_index = get_account_last_type_index(account_name)
            next_type_index = current_type_index + 1
            save_account_type_index(account_name, next_type_index)

            # 根据选中的标题类型获取标题信息
            video_info_result = get_title_info_by_type(account_name, selected_title_type)

            if video_info_result is None:
                self.add_log(f'{account_name}的标题类型{selected_title_type}没有可用标题')
                QApplication.processEvents()
                continue

            self._current_auto_title = video_info_result

            # 创建临时存放标题的文件
            temp_title_path = write_title(video_info_result[1])

            # 获取文件的目录、文件名和扩展名
            file_dir = os.path.dirname(temp_title_path)  # 文件所在的目录
            file_name = os.path.basename(temp_title_path)  # 文件名（包含扩展名）
            name, ext = os.path.splitext(file_name)  # 分离文件名和扩展名
            # 文案文件名
            copy_file_name = f"{name}{'_copy'}{ext}"
            copy_file_path = os.path.join(file_dir, copy_file_name)
            # 标签文件名
            label_file_name = f"{name}{'_label'}{ext}"
            label_file_path = os.path.join(file_dir, label_file_name)

            # 上饶景点介绍类
            if video_info_result[6] == 1:
                # 生成文案
                if (video_info_result[2] is not None and video_info_result[3] is not None
                        and video_info_result[2] != '' and video_info_result[3] != ''
                        and not is_date_today(video_info_result[7]) and video_info_result[8] < 3):
                    ai_title_word_list = video_info_result[2].split('&&')
                    tag_list_str_list = video_info_result[3].split('&&')
                    # 将标题和文案写入excel表格中
                    write_arrays_to_excel(copy_file_path, ai_title_word_list)
                    # 将片段标签写入excel表格中
                    write_arrays_to_excel(label_file_path, tag_list_str_list)
                else:
                    temp_ai_worker = AiDisposeIntroTitle(temp_title_path, account_name, video_info_result[0])
                    self.add_log('Ai开始生成文案及标签')
                    QApplication.processEvents()
                    self.thread_pool.start(temp_ai_worker)
                    temp_ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
                    temp_ai_worker.signals.finished.connect(self.on_success_occurred)
                    temp_ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                self.add_log('开始生成视频')
                QApplication.processEvents()

                # 合成视频
                self.compositeIntroVideo(copy_file_path, label_file_path, out_dir_path, account_name)
            # 全国景点介绍类
            if video_info_result[6] == 2:
                if (video_info_result[2] is not None and video_info_result[3] is not None
                        and video_info_result[2] != '' and video_info_result[3] != ''
                        and not is_date_today(video_info_result[7]) and video_info_result[8] < 3):
                    ai_title_word_list = video_info_result[2].split('&&')
                    tag_list_str_list = video_info_result[3].split('&&')
                    # 将标题和文案写入excel表格中
                    write_arrays_to_excel(copy_file_path, ai_title_word_list)
                    # 将片段标签写入excel表格中
                    write_arrays_to_excel(label_file_path, tag_list_str_list)
                else:
                    temp_ai_worker = AiDisposeCNIntroTitle(temp_title_path, account_name, video_info_result[0])
                    self.add_log('Ai开始生成文案及标签')
                    QApplication.processEvents()
                    self.thread_pool.start(temp_ai_worker)
                    temp_ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
                    temp_ai_worker.signals.finished.connect(self.on_success_occurred)
                    temp_ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                # 合成视频
                self.compositeCNIntroVideo(copy_file_path, label_file_path, out_dir_path, account_name)

            # 城市科普通用类
            if video_info_result[6] == 3:
                if (video_info_result[2] is not None and video_info_result[3] is not None
                        and video_info_result[2] != '' and video_info_result[3] != ''
                        and not is_date_today(video_info_result[7]) and video_info_result[8] < 3):
                    ai_title_word_list = video_info_result[2].split('&&')
                    tag_list_str_list = video_info_result[3].split('&&')
                    # 将标题和文案写入excel表格中
                    write_arrays_to_excel(copy_file_path, ai_title_word_list)
                    # 将片段标签写入excel表格中
                    write_arrays_to_excel(label_file_path, tag_list_str_list)
                else:
                    temp_ai_worker = AiDisposeStrategyTitle(temp_title_path, account_name, video_info_result[0])
                    self.add_log('Ai开始生成文案及标签')
                    QApplication.processEvents()
                    self.thread_pool.start(temp_ai_worker)
                    temp_ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
                    temp_ai_worker.signals.finished.connect(self.on_success_occurred)
                    temp_ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                # 合成视频
                self.compositeCityStrategyVideo(copy_file_path, label_file_path, out_dir_path, account_name)

            # 美食介绍类
            if video_info_result[6] == 4:
                if (video_info_result[2] is not None and video_info_result[3] is not None
                        and video_info_result[2] != '' and video_info_result[3] != ''
                        and not is_date_today(video_info_result[7]) and video_info_result[8] < 3):
                    ai_title_word_list = video_info_result[2].split('&&')
                    tag_list_str_list = video_info_result[3].split('&&')
                    # 将标题和文案写入excel表格中
                    write_arrays_to_excel(copy_file_path, ai_title_word_list)
                    # 将片段标签写入excel表格中
                    write_arrays_to_excel(label_file_path, tag_list_str_list)
                else:
                    temp_ai_worker = AiDisposeMsIntroTitle(temp_title_path, account_name, video_info_result[0])
                    self.add_log('Ai开始生成文案及标签')
                    QApplication.processEvents()
                    self.thread_pool.start(temp_ai_worker)
                    temp_ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
                    temp_ai_worker.signals.finished.connect(self.on_success_occurred)
                    temp_ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                # 合成视频
                self.compositeMsInforVideo(copy_file_path, label_file_path, out_dir_path, account_name)

            # 文字介绍类
            if video_info_result[6] == 5:
                if (video_info_result[2] is not None and video_info_result[2] != ''
                        and not is_date_today(video_info_result[7]) and video_info_result[8] < 3):
                    ai_title_word_list = video_info_result[2].split('&&')
                    # 将标题和文案写入excel表格中
                    write_arrays_to_excel(copy_file_path, ai_title_word_list)
                else:
                    temp_ai_worker = AiDisposeWordIntroTitle(temp_title_path, account_name, video_info_result[0])
                    self.add_log('Ai开始生成文案')
                    QApplication.processEvents()
                    self.thread_pool.start(temp_ai_worker)
                    temp_ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
                    temp_ai_worker.signals.finished.connect(self.on_success_occurred)
                    temp_ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                # 合成视频
                self.compositeWordIntroVideo(copy_file_path, out_dir_path, account_name)

            # 素材通用类
            if video_info_result[6] == 6:
                if (video_info_result[2] is not None and video_info_result[3] is not None
                        and video_info_result[2] != '' and video_info_result[3] != ''
                        and not is_date_today(video_info_result[7]) and video_info_result[8] < 3):
                    ai_title_word_list = video_info_result[2].split('&&')
                    # 将标题和文案写入excel表格中
                    write_arrays_to_excel(copy_file_path, ai_title_word_list)
                    # 将片段标签写入excel表格中
                    write_arrays_to_excel(label_file_path, video_info_result[3].split('&&'))
                else:
                    temp_ai_worker = AiDisposeMaterialStrategyTitle(temp_title_path, account_name,
                                                                    video_info_result[0])
                    self.add_log('Ai开始生成三农文案及标签')
                    QApplication.processEvents()
                    temp_ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
                    temp_ai_worker.signals.finished.connect(self.on_success_occurred)
                    temp_ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.thread_pool.start(temp_ai_worker)
                    self.loop.exec()

                    if self.error_flag:
                        self.add_log(f'三农标题文案或标签生成失败：{self.last_error_message}')
                        record_unsuccess_title_info(video_info_result)
                        self.error_flag = False
                        QApplication.processEvents()
                        continue

                # 合成视频
                self.compositeMaterialStrategyVideo(copy_file_path, out_dir_path, account_name, label_file_path)

            # 励志通用类（数据库值13）
            if video_info_result[6] == 13:
                if (video_info_result[2] is not None and video_info_result[2] != ''
                        and not is_date_today(video_info_result[7]) and video_info_result[8] < 3):
                    write_arrays_to_excel(copy_file_path, video_info_result[2].split('&&'))
                else:
                    temp_ai_worker = AiDisposeLifeStrategyTitle(temp_title_path, account_name)
                    self.add_log('Ai开始生成励志通用文案')
                    QApplication.processEvents()
                    self.thread_pool.start(temp_ai_worker)
                    temp_ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
                    temp_ai_worker.signals.finished.connect(self.on_success_occurred)
                    temp_ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                self.compositeLifeStrategyVideo(copy_file_path, out_dir_path, account_name)

            # 景点通用类
            if video_info_result[6] == 7:
                if (video_info_result[2] is not None and video_info_result[3] is not None
                        and video_info_result[2] != '' and video_info_result[3] != ''
                        and not is_date_today(video_info_result[7]) and video_info_result[8] < 3):
                    ai_title_word_list = video_info_result[2].split('&&')
                    tag_list_str_list = video_info_result[3].split('&&')
                    # 将标题和文案写入excel表格中
                    write_arrays_to_excel(copy_file_path, ai_title_word_list)
                    # 将片段标签写入excel表格中
                    write_arrays_to_excel(label_file_path, tag_list_str_list)
                else:
                    temp_ai_worker = AiDisposeScenicSpotTitle(temp_title_path, account_name, video_info_result[0])
                    self.add_log('Ai开始生成文案及标签')
                    QApplication.processEvents()
                    self.thread_pool.start(temp_ai_worker)
                    temp_ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
                    temp_ai_worker.signals.finished.connect(self.on_success_occurred)
                    temp_ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                # 合成视频
                self.compositeScenicSpotVideo(copy_file_path, label_file_path, out_dir_path, account_name)

            # 历史视频类 (使用数据库值8)
            if video_info_result[6] == 8:
                if (video_info_result[2] is not None and video_info_result[3] is not None
                        and video_info_result[2] != '' and video_info_result[3] != ''
                        and not is_date_today(video_info_result[7]) and video_info_result[8] < 3):
                    ai_title_word_list = video_info_result[2].split('&&')
                    tag_list_str_list = video_info_result[3].split('&&')
                    # 将标题和文案写入excel表格中
                    write_arrays_to_excel(copy_file_path, ai_title_word_list)
                    # 将片段标签写入excel表格中
                    write_arrays_to_excel(label_file_path, tag_list_str_list)
                else:
                    temp_ai_worker = AiDisposeHistoryStrategyTitle(temp_title_path, account_name, video_info_result[0])
                    self.add_log('Ai开始生成文案及标签')
                    QApplication.processEvents()
                    self.thread_pool.start(temp_ai_worker)
                    temp_ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
                    temp_ai_worker.signals.finished.connect(self.on_success_occurred)
                    temp_ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                # 合成视频
                self.compositeGreenScreenVideo(copy_file_path, label_file_path, out_dir_path, account_name)

            # 问答知识类
            if video_info_result[6] == 9:
                if (video_info_result[2] is not None and video_info_result[3]
                        and video_info_result[2] != '' and video_info_result[3] != ''
                        and not is_date_today(video_info_result[7]) and video_info_result[8]
                        < 3):
                    ai_title_word_list = video_info_result[2].split('&&')
                    tag_list_str_list = video_info_result[3].split('&&')
                    # 将标题和文案写入excel表格中
                    write_arrays_to_excel(copy_file_path, ai_title_word_list)
                    # 将片段标签写入excel表格中
                    write_arrays_to_excel(label_file_path, tag_list_str_list)
                else:
                    temp_ai_worker = AiDisposeQATitle(temp_title_path, account_name, video_info_result[0])
                    self.add_log('Ai开始生成文案及标签')
                    QApplication.processEvents()
                    self.thread_pool.start(temp_ai_worker)
                    temp_ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
                    temp_ai_worker.signals.finished.connect(self.on_success_occurred)
                    temp_ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                # 合成视频
                self.compositeQaVideo(copy_file_path, label_file_path, out_dir_path, account_name)

            # 图片介绍类
            if video_info_result[6] == 10:
                if (video_info_result[2] is not None and video_info_result[3]
                        and video_info_result[2] != '' and video_info_result[3] != ''
                        and not is_date_today(video_info_result[7]) and video_info_result[8]
                        < 3):
                    ai_title_word_list = video_info_result[2].split('&&')
                    tag_list_str_list = video_info_result[3].split('&&')
                    # 将标题和文案写入excel表格中
                    write_arrays_to_excel(copy_file_path, ai_title_word_list)
                    # 将片段标签写入excel表格中
                    write_arrays_to_excel(label_file_path, tag_list_str_list)
                else:
                    temp_ai_worker = AiDisposeIMGTitle(temp_title_path, account_name, video_info_result[0])
                    self.add_log('Ai开始生成文案及标签')
                    QApplication.processEvents()
                    self.thread_pool.start(temp_ai_worker)

                    temp_ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
                    temp_ai_worker.signals.finished.connect(self.on_success_occurred)
                    temp_ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                # 合成视频
                self.compositeImageIntroVideo(copy_file_path, label_file_path, out_dir_path, account_name)

            # 美食攻略类
            if video_info_result[6] == 11:
                if (video_info_result[2] is not None and video_info_result[3]
                        and video_info_result[2] != '' and video_info_result[3] != ''
                        and not is_date_today(video_info_result[7]) and video_info_result[8]
                        < 3):
                    ai_title_word_list = video_info_result[2].split('&&')
                    tag_list_str_list = video_info_result[3].split('&&')
                    write_arrays_to_excel(copy_file_path, ai_title_word_list)
                    write_arrays_to_excel(label_file_path, tag_list_str_list)
                else:
                    temp_ai_worker = AiDisposeFoodStrategyTitle(temp_title_path, account_name, video_info_result[0])
                    self.add_log('Ai开始生成美食攻略文案及标签')
                    QApplication.processEvents()
                    self.thread_pool.start(temp_ai_worker)

                    temp_ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
                    temp_ai_worker.signals.finished.connect(self.on_success_occurred)
                    temp_ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                # 合成视频
                self.compositeLocalStrategyVideo(copy_file_path, label_file_path, out_dir_path, account_name)

            # 节日风俗类
            if video_info_result[6] == 12:
                if (video_info_result[2] is not None and video_info_result[3]
                        and video_info_result[2] != '' and video_info_result[3] != ''
                        and not is_date_today(video_info_result[7]) and video_info_result[8]
                        < 3):
                    ai_title_word_list = video_info_result[2].split('&&')
                    tag_list_str_list = video_info_result[3].split('&&')
                    write_arrays_to_excel(copy_file_path, ai_title_word_list)
                    write_arrays_to_excel(label_file_path, tag_list_str_list)
                else:
                    temp_ai_worker = AiDisposeFestivalCustomsTitle(temp_title_path, account_name, video_info_result[0])
                    self.add_log('Ai开始生成节日风俗文案及标签')
                    QApplication.processEvents()
                    self.thread_pool.start(temp_ai_worker)

                    temp_ai_worker.signals.progressResultReady.connect(self.on_process_result_ready)
                    temp_ai_worker.signals.finished.connect(self.on_success_occurred)
                    temp_ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                # 合成视频
                self.compositeFestivalCustomsVideo(copy_file_path, label_file_path, out_dir_path, account_name)

            # Every worker reports through the same flag. Handle failures here
            # before deriving an output name so a failed title is never marked
            # as generated or uploaded.
            if self.error_flag:
                record_unsuccess_title_info(video_info_result)
                self.error_flag = False
                if self._stop_auto_generation:
                    break
                QApplication.processEvents()
                continue

            title_str = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', video_info_result[1])
            video_file_path = os.path.join(out_dir_path, title_str + '.mp4')

            video_generated = os.path.exists(video_file_path)
            if video_generated:
                mark_title_generated(video_info_result[0])

            if self.uploadCheckBox.isChecked() and video_generated:
                if video_info_result[6] != 5 and video_info_result[6] != 6:
                    try:
                        self.add_log('正在上传视频到站点')
                        QApplication.processEvents()
                        if video_info_result[2] is None or video_info_result[2] == '':
                            video_info_result = get_content_label(video_info_result[0])
                        if self.all_setting_dict.get('account_location'):
                            account_location = self.all_setting_dict['account_location']['location']
                        else:
                            account_location = '上饶市'

                        if account_location != '中国':
                            video_id = upload_video_info_to_site(video_info_result, account_location)
                            if upload_video_pic_to_site(video_id, video_file_path):
                                self.add_log('上传视频到站点成功')
                                QApplication.processEvents()
                    except Exception as e:
                        self.add_log(f'上传视频到站点错误{str(e)}')
                        QApplication.processEvents()

                time.sleep(2)
                # ftp上传视频 集中到一台服务器
                try:
                    self.add_log('正在ftp上传视频到服务器FTP站点')
                    QApplication.processEvents()
                    # 上传视频到站点
                    if ftp_upload_video_to_site(video_file_path, video_info_result[0]):
                        mark_title_ftp_uploaded(video_info_result[5], video_info_result[0], title_str)
                        self.add_log('ftp上传视频到服务器FTP站点成功')
                        QApplication.processEvents()
                    else:
                        self.add_log('ftp上传视频到服务器站点失败')
                        QApplication.processEvents()
                except Exception as e:
                    self.add_log(f'ftp上传视频到站点错误{str(e)}')
                    QApplication.processEvents()

            elif not video_generated:
                record_unsuccess_title_info(video_info_result)
            if video_generated:
                now_times += 1

        if now_times < times:
            self.add_log(f'自动生成在{attempt_count}次尝试后停止，成功{now_times}/{times}个视频')
            QApplication.processEvents()

    # --美食介绍视频
    def compositeMsInforVideo(self, copy_file, label_file, out_dir_path, account_name):
        self.add_log('开始合成根据文案合成视频')
        QApplication.processEvents()

        # 时间
        timestamp = int(time.time())
        generated_count = 0
        failed_count = 0

        self.all_setting_dict = read_dict_from_txt('setting.txt')

        if not os.path.exists(self.all_setting_dict['end_video']['end_video_path']):
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                                    QMessageBox QLabel {
                                    background-color: rgb(22, 23, 25);
                                    color: rgb(255, 255, 255);
                                   }
                                   QMessageBox {
                                   background-color: rgb(22, 23, 25);
                                   color: rgb(255, 255, 255);
                                   }
                               """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"请选择视频添加的片尾")
            msg_box.exec()
            return

        # 删除video缓存
        clean_cut_cache()
        clean_cache()

        # copy 起始行
        copy_start_num = get_first_data_row(copy_file)

        # label 起始行
        label_start_num = get_first_data_row(label_file)

        self.add_log(f'读取视频文案,文案文件路径是{str(copy_file)},标签文件路径是{str(label_file)}')

        if copy_start_num == -1 or label_start_num == -1 or copy_start_num is None or label_start_num is None:
            self.add_log('文案文件或者标签文件没有数据可读，结束合成视频')
            QApplication.processEvents()
            return

        while True:

            if self.randomVideoModelCheckBox.isChecked():
                model_result = get_random_video_model()
                model_set_dict = json.loads(model_result['model_set'])
                self.all_setting_dict['title_set'] = model_set_dict['title_set']
                self.all_setting_dict['part_title_set'] = model_set_dict['part_title_set']
                self.all_setting_dict['srt_set'] = model_set_dict['srt_set']
                self.all_setting_dict['voice_set'] = model_set_dict['voice_set']
                self.all_setting_dict['part_title_part_0_set'] = model_set_dict['part_title_part_0_set']
                self.all_setting_dict['part_title_part_1_set'] = model_set_dict['part_title_part_1_set']
                self.all_setting_dict['part_title_part_2_set'] = model_set_dict['part_title_part_2_set']
                self.all_setting_dict['part_title_part_3_set'] = model_set_dict['part_title_part_3_set']
                self.all_setting_dict['part_title_part_4_set'] = model_set_dict['part_title_part_4_set']
                self.all_setting_dict['part_title_part_5_set'] = model_set_dict['part_title_part_5_set']

            # tts 速度
            speed_value = str(self.all_setting_dict['voice_set']['spd_0'])
            if not str(speed_value).startswith('-'):
                speed_value = '+' + speed_value
            speed_value = speed_value + '%'

            # 获取音频设置
            audio_setting = {
                'api_type': self.all_setting_dict['voice_set']['api_type'],
                'audio_role': self.audio_role_list[self.all_setting_dict['voice_set']['role_0']],
                'speed_value': speed_value,
                'volume_value': self.all_setting_dict['voice_set']['vol_0']
            }

            if self.all_setting_dict['voice_set']['api_type'] == 1:
                # 获取音频设置
                audio_setting = {
                    'api_type': self.all_setting_dict['voice_set']['api_type'],
                    'audio_role': int(
                        self.audio_bd_role_list[self.all_setting_dict['voice_set']['role_1']].split(':')[1]),
                    'speed_value': self.all_setting_dict['voice_set']['spd_1'],
                    'volume_value': self.all_setting_dict['voice_set']['vol_1'],
                    'tone_value': self.all_setting_dict['voice_set']['pit_1']
                }

            # 获取视频文案
            video_title_text = get_row_data(copy_file, copy_start_num)

            self.add_log('读取视频文案')
            QApplication.processEvents()

            video_title_text.append('记得点赞关注评论')

            # 获取视频标签
            label_text = get_row_data(label_file, label_start_num)

            self.add_log(f'读取视频标签，{"&&".join(video_title_text)}，{"&&".join(label_text)}')
            QApplication.processEvents()

            if len(video_title_text) < 3:
                self.add_log('文案记录读取完毕')
                QApplication.processEvents()
                # QMessageBox.information(self, "完成", f"所有视频已生成处理完成，已生成任务列表")
                break

            label_text.append('点赞,关注,评论')

            # 标题
            video_title = video_title_text[0].strip()

            # 标签
            video_tag = video_title_text[1].strip()

            # 文案
            video_text = video_title_text[2:]

            # 文案段数
            video_text_part_num = len(video_text)

            if video_text_part_num <= 2:
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                label_start_num += 1
                failed_count += 1
                self.add_log('文案格式不完整，本条视频未生成')
                QApplication.processEvents()
                logging.debug(f'合成一个视频失败')
                continue

            try:
                # 处理空格
                for i, part_video_text in enumerate(video_text):

                    part_video_text_list = part_video_text.split(' ')

                    part_label_text_list = label_text[i].split(',')

                    if (part_label_text_list[0] not in part_video_text_list[0] and i != 0
                            and i != len(video_text) - 1 and i != len(video_text) - 2):
                        part_video_text_list = [part_video_text_list[0] + part_video_text_list[
                            1]] + part_video_text_list[
                                  2:]

                        video_text[i] = ' '.join(part_video_text_list)
            except Exception as e:
                print(f'可能不符合格式要求{e}')
                failed_count += 1
                self.add_log(f'文案与标签格式不匹配，本条视频未生成：{e}')
                QApplication.processEvents()
                clean_cache()
                copy_start_num += 1
                label_start_num += 1
                continue

            # 视频处理缓存文件夹
            tamp_folder_name = 'tempConcateVideo'
            current_directory = os.getcwd()
            tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
            video_tamp_path_name = 'video_cache_file'
            video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)

            if len(video_text) > 0:

                # 素材缓存路径
                part_video_list = []

                # 字幕缓存路径
                part_srt_ass_list = []

                # 音频缓存路径
                part_audio_list = []

                # 标题缓存路径
                part_title_ass_list = []

                # 配音初始字幕生成-----------------------------------------------------------
                product_worker = SaWorker(video_text, audio_setting)
                self.thread_pool.start(product_worker)
                # 事件循环
                product_worker.signals.finished.connect(self.on_success_occurred)
                product_worker.signals.errorOccurred.connect(self.on_error_occurred)
                self.loop.exec()
                if self.error_flag:
                    # 删除cut video缓存
                    clean_cut_cache()
                    clean_cache()
                    copy_start_num += 1
                    label_start_num += 1
                    failed_count += 1
                    self.add_log(f'字幕配音生成失败，本条视频未生成：{self.last_error_message}')
                    QApplication.processEvents()
                    logging.debug(f'合成一个视频失败')
                    continue
                time.sleep(1)
                self.add_log('ai分析文案，已经为视频生成字幕配音即标签')
                QApplication.processEvents()

                # 生成标题、小标题以及字幕的ass文件-----------------------------------------------------------
                start_audio_length = 0
                for i in range(video_text_part_num):

                    srt_file_name = f"temp_subtitle{i}.srt"

                    audio_file_name = f"temp_final_audio{i}.mp3"

                    # 原字幕文件
                    part_subtitle_url = os.path.join(video_tamp_path, srt_file_name)

                    # ass字幕文件
                    output_path = part_subtitle_url.replace('.srt', '.ass')

                    # 标题字幕文件
                    output_title_path = part_subtitle_url.replace('.srt', '_title.ass')

                    # 音频文件
                    output_audio_path = os.path.join(video_tamp_path, audio_file_name)

                    # 转换成ass
                    convert_srt_to_ass(part_subtitle_url, output_path, self.all_setting_dict['srt_set'])

                    # # 旅游景点介绍类
                    # if i == 0 or i == video_text_part_num - 1:
                    #     remove_all_dialogue_text(output_path)
                    #
                    # if i != 0 and i != video_text_part_num - 1 and i != video_text_part_num - 2:
                    #     remove_dialogue_text(output_path)

                    if i == 0:
                        remove_dialogue_text(output_path)

                    if i == video_text_part_num - 1:
                        remove_all_dialogue_text(output_path)

                    if i != video_text_part_num - 1 and i != video_text_part_num - 2:
                        remove_dialogue_text(output_path)

                    # 转换完成后 记录ass字幕位置
                    part_srt_ass_list.append(output_path)

                    # 记录音频位置
                    part_audio_list.append(output_audio_path)

                    # 创建标题ass，包括大标题和小标题
                    if i == 0:
                        self.pic_time = create_title(self.all_setting_dict, '1',
                                                     self.screenComboBox.currentIndex(),
                                                     video_title, output_title_path, part_subtitle_url)

                    elif i != video_text_part_num - 1 and i != video_text_part_num - 2:
                        part_title = label_text[i].split(',')[0]
                        create_title(self.all_setting_dict, '2', self.screenComboBox.currentIndex(),
                                     part_title, output_title_path,
                                     part_subtitle_url)

                    if i != video_text_part_num - 1 and i != video_text_part_num - 2:
                        part_title_ass_list.append(output_title_path)

                    self.add_log('视频样式字幕已生成')
                    QApplication.processEvents()

                    # 匹配视频素材-----------------------------------------------------------
                    # 视频片段标签
                    part_video_tags = label_text[i].split(',')

                    # 片段配音
                    part_audio_url = output_audio_path

                    # 配音时长
                    audio_length = get_audio_length(part_audio_url)

                    video_path = ''

                    if i == video_text_part_num - 1:

                        # 处理片头合成
                        start_video = merge_videos_with_duration(part_video_list, '111', start_audio_length)
                        if os.path.exists(start_video):
                            part_video_list.insert(0, start_video)

                        video_path = self.all_setting_dict['end_video']['end_video_path']
                        if os.path.exists(video_path):
                            part_video_list.append(video_path)
                    else:
                        # 匹配视频重复
                        unSuccessVideoLabel = str(timestamp) + '_videoLabel.xlsx'
                        notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                        notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessVideoLabel)

                        if i == 0:
                            # 随机获取一个封面封面素材
                            start_audio_length = audio_length

                        # 片尾随机匹配其中景点视频
                        elif i == video_text_part_num - 2:
                            sights_word_key = label_text[random.randint(1, video_text_part_num - 3)].split(',')[0]
                            ftp_videos = get_videos_by_keyword_1(sights_word_key, self.screenComboBox.currentIndex()
                                                                 , self.locationlineEdit.text().strip(), audio_length,
                                                                 20, "美食素材")
                            ftp_video_ids = [video['id'] for video in ftp_videos]
                            if len(ftp_videos) > 0:
                                video_id = random.choice(ftp_video_ids)
                                video_path = download_video(video_id, self.screenComboBox.currentIndex())
                                if video_path is not None:
                                    if os.path.exists(video_path):
                                        # 音频时长截取视频内容
                                        cut_video_path = cut_video_by_audio_length(video_path, video_id, audio_length)
                                        if os.path.exists(cut_video_path):
                                            self.add_log(
                                                f'正在匹配素材，已经为视频匹配了{len(part_video_list) + 1}个素材')
                                            QApplication.processEvents()

                                            part_video_list.append(cut_video_path)
                                    else:
                                        self.add_log(f'下载素材失败')
                                        QApplication.processEvents()
                        else:
                            while True:
                                ftp_video_List = []
                                # 地区景区匹配到的id
                                location_id_list = []
                                for n, tag in enumerate(part_video_tags):
                                    if len(location_id_list) == 0 and n == 0:
                                        ftp_videos = get_videos_by_keyword_1(tag, self.screenComboBox.currentIndex(),
                                                                             self.locationlineEdit.text().strip(),
                                                                             audio_length, 20, "美食素材")

                                        if len(ftp_videos) <= 0:
                                            print('缺少该关键字的素材')
                                            # part_video_tags.append(str(audio_length))
                                            # 记入未匹配的文案和视频标签

                                            lost_video_param = {
                                                'title': part_video_tags[0],
                                                'firstTags': '_'.join(part_video_tags),
                                                'secondTags': '',
                                                'videoLength': audio_length,
                                                'screen': self.screenComboBox.currentIndex(),
                                                'accountName': account_name,
                                                'titleType': '4'
                                            }
                                            # 将缺少的视频信息记入库中
                                            add_lost_cn_video_record(lost_video_param)

                                            # 将缺少的视频信息记入表中
                                            write_arrays_to_excel(notSuccess_label_folder_path, part_video_tags)
                                            break

                                        for video in ftp_videos:
                                            location_id_list.append(video['id'])

                                    elif len(location_id_list) > 0:
                                        ftp_videos = get_videos_by_keyword(tag, self.screenComboBox.currentIndex(),
                                                                           self.locationlineEdit.text().strip(),
                                                                           location_id_list,
                                                                           audio_length, 20, "美食素材")
                                    else:
                                        ftp_videos = []

                                    # 提取视频ID列表
                                    if len(ftp_videos) > 0:
                                        ftp_ideo_ids = [video['id'] for video in ftp_videos]
                                        if len(ftp_ideo_ids) <= 0:
                                            continue
                                        ftp_video_List.append(ftp_ideo_ids)

                                # 没有素材退出匹配
                                if len(ftp_video_List) <= 0:
                                    print('缺少该素材，退出合成')
                                    self.add_log(f'缺少该素材，退出合成')
                                    QApplication.processEvents()
                                    return

                                if len(ftp_video_List) == 1:
                                    video_id = random.choice(ftp_video_List[0])
                                else:
                                    video_id = count_and_sort(ftp_video_List)

                                try:
                                    video_path = download_video(video_id, self.screenComboBox.currentIndex())

                                    time.sleep(1)
                                    if video_path is not None:
                                        if os.path.exists(video_path):
                                            # 音频时长截取视频内容
                                            cut_video_path = cut_video_by_audio_length(video_path, video_id,
                                                                                       audio_length)

                                            logging.debug(f'这个下载的视频{video_path}的')

                                            if os.path.exists(cut_video_path):
                                                logging.debug(f'存在下载的视频{cut_video_path}')
                                                self.add_log(
                                                    f'正在匹配素材，已经为视频匹配了{len(part_video_list)}个素材')
                                                QApplication.processEvents()

                                                part_video_list.append(cut_video_path)
                                                break
                                            else:
                                                self.add_log(f'下载素材失败')
                                                QApplication.processEvents()
                                                break
                                        else:
                                            self.add_log(f'下载素材失败')
                                            QApplication.processEvents()
                                            break
                                    else:
                                        self.add_log(f'下载素材失败')
                                        QApplication.processEvents()
                                        break
                                except Exception as e:
                                    logging.debug(f'这个下载的视频{video_path}的错误{str(e)}')
                                    self.add_log(f'下载素材异常：{str(e)}，跳出该段匹配')
                                    QApplication.processEvents()
                                    break

                if len(part_video_list) == video_text_part_num:
                    transitionSetting = {
                        'transitionNum': 0,
                        'transitionTime': 0
                    }
                    saveVideoPath = out_dir_path

                    video_id_path_name = 'video_id.xlsx'
                    # 任务文件输出路径
                    video_id_excel_file_path = os.path.join(saveVideoPath, video_id_path_name)

                    # 记录每个视频匹配的素材
                    write_arrays_to_excel(video_id_excel_file_path, [video_title] + part_video_list)

                    # 输出路径
                    video_name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', video_title) + '_0.mp4'

                    video_file_path = os.path.join(saveVideoPath, video_name)

                    excel_file_path_name = '1.xls'
                    # 任务文件输出路径
                    excel_file_path = os.path.join(saveVideoPath, excel_file_path_name)

                    composite_worker = CompositeVideo(part_video_list, part_audio_list, part_srt_ass_list,
                                                      part_title_ass_list, video_file_path,
                                                      transitionSetting, self.pic_time)

                    self.add_log('正在合成一个视频。。。')
                    QApplication.processEvents()

                    self.thread_pool.start(composite_worker)
                    # 创建一个事件循环
                    composite_worker.signals.finished.connect(self.on_success_occurred)
                    composite_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()
                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'合成一个视频失败')
                        continue

                    self.add_log('已经合成一个视频，接下来进行后期处理。')
                    QApplication.processEvents()

                    if not os.path.exists(video_file_path):
                        self.add_log('没有已经合成一个视频，跳过。')
                        QApplication.processEvents()
                        continue

                    # 匹配添加音乐
                    parent_dir = os.getcwd()
                    # 构造同级的缓存文件夹路径
                    cache_music_dir_path = os.path.join(parent_dir, 'cacheMusic')
                    # 获取文件夹中的所有MP3文件
                    mp3_files = [f for f in os.listdir(cache_music_dir_path) if
                                 f.endswith('.mp3') or f.endswith('.MP3')]

                    # 如果文件夹中有MP3文件，则随机选择一个
                    if mp3_files:
                        random_mp3_file = random.choice(mp3_files)
                        random_mp3_file_path = os.path.join(cache_music_dir_path, random_mp3_file)
                        print(f"随机选择的MP3文件路径为：{random_mp3_file_path}")
                    else:
                        print("文件夹中没有找到MP3文件,缺少音乐。")
                        break

                    # 加载音频文件
                    bgAudioVolume = 40
                    output_bgm_video_path = video_file_path.replace('_0.mp4', '_1.mp4')
                    addMusicWorker = AddMusicWorker(video_file_path, random_mp3_file_path, 100, bgAudioVolume,
                                                    output_bgm_video_path)

                    self.thread_pool.start(addMusicWorker)
                    # 创建一个事件循环
                    addMusicWorker.signals.finished.connect(self.on_success_occurred)
                    addMusicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加音乐失败')
                        continue

                    self.add_log('后期处理,已添加音乐。')
                    QApplication.processEvents()

                    # 添加水印
                    watermark_location_examples = [['50', '50'], ['main_w-overlay_w-100', '50'],
                                                   ['50', 'main_h-overlay_h-50'],
                                                   ['main_w-overlay_w-50', 'main_h-overlay_h-50'],
                                                   ['(main_w-overlay_w)/2', '(main_h-overlay_h)/2'],
                                                   ['(main_w-overlay_w)/2', '50'],
                                                   ['(main_w-overlay_w)/2', 'main_h-overlay_h-100']]

                    watermark_setting = {
                        'watermark_location': watermark_location_examples[
                            self.all_setting_dict['water_set']['position']],
                        'zoom_size': self.all_setting_dict['water_set']['zoom'],
                        'pic_alpha': self.all_setting_dict['water_set']['alpha']
                    }
                    final_output_path = output_bgm_video_path.replace('_1.mp4', '.mp4')
                    add_text_watermark_worker = AddWatermarkWorker(output_bgm_video_path, final_output_path,
                                                                   watermark_setting, 2,
                                                                   self.all_setting_dict['water_set']['filePath'])
                    self.thread_pool.start(add_text_watermark_worker)
                    # 创建一个事件循环
                    add_text_watermark_worker.signals.finished.connect(self.on_success_occurred)
                    add_text_watermark_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加水印失败')
                        continue

                    self.add_log('后期处理,已添加水印。')
                    QApplication.processEvents()

                    # 视频压缩
                    temp_compressed_path = final_output_path.replace('.mp4', '_temp_compressed.mp4')
                    compress_video_worker = CompressVideoWorker(final_output_path, temp_compressed_path)

                    self.thread_pool.start(compress_video_worker)
                    compress_video_worker.signals.finished.connect(self.on_success_occurred)
                    compress_video_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        self.add_log('视频压缩失败，使用原始文件')
                        QApplication.processEvents()
                    else:
                        self.add_log('视频压缩完成')
                        QApplication.processEvents()

                    # 移除中间视频
                    if os.path.exists(video_file_path):
                        os.remove(video_file_path)

                    if os.path.exists(output_bgm_video_path):
                        os.remove(output_bgm_video_path)

                    data_dict = {
                        "标题": video_title.replace('|', ''),
                        "标签": video_tag,
                        "文件路径": final_output_path.replace('/', '\\'),
                        "描述": ','.join(video_text),
                        "封面路径": "",
                        "图片集合": "",
                        "关联商品": "",
                        "分区分类": "旅游",
                        "备注": ""
                    }

                    write_to_old_excel(excel_file_path, data_dict)

                    # 上传任务信息
                    # 账号account
                    account_result = self.get_upload_accounts(account_name)

                    # 上传任务
                    if len(account_result) > 0:
                        for (account, mac) in account_result:
                            print(account)
                            task_param = {
                                'name': account_name,
                                'account': account,
                                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'title': data_dict.get('标题'),
                                'mac': mac,
                                'tag': data_dict.get('标签'),
                                'path': data_dict.get('文件路径'),
                                'describe': data_dict.get('描述'),
                                'classify': data_dict.get('分区分类'),
                                'task_type': 4,
                            }
                            add_user_task(task_param)
                            self.add_log(f'{account_name}{account}上传视频任务:{final_output_path}')
                            QApplication.processEvents()
                    self.add_log(f'生成完成一个视频:{final_output_path}')
                    QApplication.processEvents()
                    generated_count += 1

                else:
                    failed_count += 1
                    logging.debug(f'匹配的视频与文案数量不一致')
                    print('匹配的视频与文案数量不一致')
                    unSuccessCopy = str(timestamp) + '_copy.xlsx'
                    unSuccessLabel = str(timestamp) + '_label.xlsx'
                    notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                    notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
                    notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
                    # 记入未匹配的文案和视频标签
                    write_arrays_to_excel(notSuccess_copy_folder_path, video_title_text[0:-1])
                    write_arrays_to_excel(notSuccess_label_folder_path, label_text[0:-1])
                    self.add_log('跳过一个脚本文案，可能是没有匹配到视频，已记录')
                    QApplication.processEvents()

            # 删除cut video缓存
            clean_cut_cache()
            clean_cache()
            copy_start_num += 1
            label_start_num += 1

        current_directory = os.getcwd()
        unSuccessCopy = str(timestamp) + '_copy.xlsx'
        unSuccessLabel = str(timestamp) + '_label.xlsx'
        notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
        notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
        notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
        if os.path.exists(notSuccess_copy_folder_path) and os.path.exists(notSuccess_label_folder_path):
            try:
                self.add_log('有视频记录没有生成完毕，可补充素材后点击继续生成')
                QApplication.processEvents()
                self.copyFileLabel.setText(notSuccess_copy_folder_path)
                self.labelFilelabel.setText(notSuccess_label_folder_path)

                # 展示缺少的标签
                unSuccessVideoLabel = str(timestamp) + '_videoLabel.xlsx'
                notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessVideoLabel)
                # 读取整个工作表（默认第一张）
                df = _read_excel(notSuccess_label_folder_path)
                # 设置表格的行列数
                self.lostVideoTableWidget.setRowCount(df.shape[0])
                self.lostVideoTableWidget.setColumnCount(df.shape[1])

                # 获取水平表头视图
                horizontal_header = self.lostVideoTableWidget.horizontalHeader()

                # 设置表头样式表（背景色、文字颜色等）
                horizontal_header.setStyleSheet("""
                                                   QHeaderView::section {
                                                       background-color: rgb(56, 56, 56);
                                                       color: white;                     
                                                       ont-weight: bold;          /* 文字加粗 */
                                                       border-right: 1px solid #ddd; /* 右侧边框 */
                                                       text-align: center;         /* 文字居中 */
                                                   }
                                               """)
                vertical_header = self.lostVideoTableWidget.verticalHeader()

                vertical_header.setStyleSheet("""
                                                   QHeaderView::section {
                                                       background-color: rgb(56, 56, 56);
                                                       color: white;                    
                                                       font-weight: bold;          /* 文字加粗 */
                                                       border-right: 1px solid #ddd; /* 右侧边框 */
                                                       text-align: center;         /* 文字居中 */
                                                   }
                                               """)

                # 填充数据
                for row in range(df.shape[0]):
                    for col in range(df.shape[1]):
                        item = QTableWidgetItem(str(df.iat[row, col]))
                        self.lostVideoTableWidget.setItem(row, col, item)
                self.lostVideoTableWidget.resizeColumnsToContents()
            except Exception as e:
                print(f'展示缺少的标签错误{str(e)}')
                pass

        else:
            if failed_count > 0:
                self.add_log(f'本次生成结束：成功{generated_count}个，失败{failed_count}个')
            elif generated_count > 0:
                self.add_log(f'所有视频记录生成完毕，共生成{generated_count}个视频')
            else:
                self.add_log('本次没有生成视频，请查看前面的失败原因')
            QApplication.processEvents()

    # --介绍类视频
    def compositeIntroVideo(self, copy_file, label_file, out_dir_path, account_name):
        # if self.saveVideoPathLabel.text() == '':
        #     QMessageBox.information(self, "提示", f"请选择视频保存路径")
        #     return

        self.add_log('开始合成根据文案合成视频')
        QApplication.processEvents()

        # 时间
        timestamp = int(time.time())
        generated_count = 0
        failed_count = 0

        self.all_setting_dict = read_dict_from_txt('setting.txt')

        if not os.path.exists(self.all_setting_dict['end_video']['end_video_path']):
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                             QMessageBox QLabel {
                             background-color: rgb(22, 23, 25);
                             color: rgb(255, 255, 255);
                            }
                            QMessageBox {
                            background-color: rgb(22, 23, 25);
                            color: rgb(255, 255, 255);
                            }
                        """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"请选择视频添加的片尾")
            msg_box.exec()
            return

        # 删除video缓存
        clean_cut_cache()
        clean_cache()

        # copy 起始行
        copy_start_num = get_first_data_row(copy_file)

        # label 起始行
        label_start_num = get_first_data_row(label_file)

        self.add_log(f'读取视频文案,文案文件路径是{str(copy_file)},标签文件路径是{str(label_file)}')

        if copy_start_num == -1 or label_start_num == -1 or copy_start_num is None or label_start_num is None:
            self.add_log('文案文件或者标签文件没有数据可读，结束合成视频')
            QApplication.processEvents()
            return

        while True:

            if self.randomVideoModelCheckBox.isChecked():
                model_result = get_random_video_model()
                model_set_dict = json.loads(model_result['model_set'])
                self.all_setting_dict['title_set'] = model_set_dict['title_set']
                self.all_setting_dict['part_title_set'] = model_set_dict['part_title_set']
                self.all_setting_dict['srt_set'] = model_set_dict['srt_set']
                self.all_setting_dict['voice_set'] = model_set_dict['voice_set']
                self.all_setting_dict['part_title_part_0_set'] = model_set_dict['part_title_part_0_set']
                self.all_setting_dict['part_title_part_1_set'] = model_set_dict['part_title_part_1_set']
                self.all_setting_dict['part_title_part_2_set'] = model_set_dict['part_title_part_2_set']
                self.all_setting_dict['part_title_part_3_set'] = model_set_dict['part_title_part_3_set']
                self.all_setting_dict['part_title_part_4_set'] = model_set_dict['part_title_part_4_set']
                self.all_setting_dict['part_title_part_5_set'] = model_set_dict['part_title_part_5_set']

            # tts 速度
            speed_value = str(self.all_setting_dict['voice_set']['spd_0'])
            if not str(speed_value).startswith('-'):
                speed_value = '+' + speed_value
            speed_value = speed_value + '%'

            # 获取音频设置
            audio_setting = {
                'api_type': self.all_setting_dict['voice_set']['api_type'],
                'audio_role': self.audio_role_list[self.all_setting_dict['voice_set']['role_0']],
                'speed_value': speed_value,
                'volume_value': self.all_setting_dict['voice_set']['vol_0']
            }

            if self.all_setting_dict['voice_set']['api_type'] == 1:
                # 获取音频设置
                audio_setting = {
                    'api_type': self.all_setting_dict['voice_set']['api_type'],
                    'audio_role': int(
                        self.audio_bd_role_list[self.all_setting_dict['voice_set']['role_1']].split(':')[1]),
                    'speed_value': self.all_setting_dict['voice_set']['spd_1'],
                    'volume_value': self.all_setting_dict['voice_set']['vol_1'],
                    'tone_value': self.all_setting_dict['voice_set']['pit_1']
                }

            # 获取视频文案
            video_title_text = get_row_data(copy_file, copy_start_num)

            self.add_log('读取视频文案')
            QApplication.processEvents()

            video_title_text.append('记得点赞关注评论')

            # 获取视频标签
            label_text = get_row_data(label_file, label_start_num)

            self.add_log(f'读取视频标签，{"&&".join(video_title_text)}，{"&&".join(label_text)}')
            QApplication.processEvents()

            if len(video_title_text) < 3:
                self.add_log('文案记录读取完毕')
                QApplication.processEvents()
                # QMessageBox.information(self, "完成", f"所有视频已生成处理完成，已生成任务列表")
                break

            label_text.append('点赞,关注,评论')

            # 标题
            video_title = video_title_text[0].strip()

            # 标签
            video_tag = video_title_text[1].strip()

            # 文案
            video_text = video_title_text[2:]

            # 文案段数
            video_text_part_num = len(video_text)

            if video_text_part_num <= 2:
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                label_start_num += 1
                failed_count += 1
                self.add_log('文案格式不完整，本条视频未生成')
                QApplication.processEvents()
                logging.debug(f'合成一个视频失败')
                continue

            try:
                # 处理空格
                for i, part_video_text in enumerate(video_text):

                    part_video_text_list = part_video_text.split(' ')

                    part_label_text_list = label_text[i].split(',')

                    if (part_label_text_list[0] not in part_video_text_list[0] and i != 0
                            and i != len(video_text) - 1 and i != len(video_text) - 2):
                        part_video_text_list = [part_video_text_list[0] + part_video_text_list[
                            1]] + part_video_text_list[
                                  2:]

                        video_text[i] = ' '.join(part_video_text_list)
            except Exception as e:
                print(f'可能不符合格式要求{e}')
                failed_count += 1
                self.add_log(f'文案与标签格式不匹配，本条视频未生成：{e}')
                QApplication.processEvents()
                clean_cache()
                copy_start_num += 1
                label_start_num += 1
                continue

            # 视频处理缓存文件夹
            tamp_folder_name = 'tempConcateVideo'
            current_directory = os.getcwd()
            tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
            video_tamp_path_name = 'video_cache_file'
            video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)

            if len(video_text) > 0:

                # 素材缓存路径
                part_video_list = []

                # 字幕缓存路径
                part_srt_ass_list = []

                # 音频缓存路径
                part_audio_list = []

                # 标题缓存路径
                part_title_ass_list = []

                # 配音初始字幕生成-----------------------------------------------------------
                product_worker = SaWorker(video_text, audio_setting)
                self.thread_pool.start(product_worker)
                # 事件循环
                product_worker.signals.finished.connect(self.on_success_occurred)
                product_worker.signals.errorOccurred.connect(self.on_error_occurred)
                self.loop.exec()
                if self.error_flag:
                    # 删除cut video缓存
                    clean_cut_cache()
                    clean_cache()
                    copy_start_num += 1
                    label_start_num += 1
                    failed_count += 1
                    self.add_log(f'字幕配音生成失败，本条视频未生成：{self.last_error_message}')
                    QApplication.processEvents()
                    logging.debug(f'合成一个视频失败')
                    continue
                time.sleep(1)
                self.add_log('ai分析文案，已经为视频生成字幕配音即标签')
                QApplication.processEvents()

                # 生成标题、小标题以及字幕的ass文件-----------------------------------------------------------
                # 封面帧字幕获取
                pic_title_ass = ''
                pic_title_video = ''

                for i in range(video_text_part_num):

                    srt_file_name = f"temp_subtitle{i}.srt"

                    audio_file_name = f"temp_final_audio{i}.mp3"

                    # 原字幕文件
                    part_subtitle_url = os.path.join(video_tamp_path, srt_file_name)

                    # ass字幕文件
                    output_path = part_subtitle_url.replace('.srt', '.ass')

                    # 标题字幕文件
                    output_title_path = part_subtitle_url.replace('.srt', '_title.ass')

                    # 音频文件
                    output_audio_path = os.path.join(video_tamp_path, audio_file_name)

                    # clear_recycle_bin()
                    # # 判断是否存在ass文件,是则删除掉
                    # if os.path.exists(output_path):
                    #     send2trash.send2trash(output_path)

                    # 转换成ass
                    convert_srt_to_ass(part_subtitle_url, output_path, self.all_setting_dict['srt_set'])

                    # 大标题字幕
                    # if i == 0:
                    #     remove_dialogue_text(output_path)

                    # 去除结束语的字幕
                    if i == video_text_part_num - 1:
                        remove_all_dialogue_text(output_path)

                    # 小标题下的字幕
                    # if i != video_text_part_num - 1 and i != video_text_part_num - 2:
                    #     remove_dialogue_text(output_path)

                    # 转换完成后 记录ass字幕位置
                    part_srt_ass_list.append(output_path)

                    # 记录音频位置
                    part_audio_list.append(output_audio_path)

                    # # 创建标题ass，包括大标题和小标题
                    if i == 0:
                        # 封面帧
                        output_title_path = part_subtitle_url.replace('.srt', '_pic_title.ass')
                        self.pic_time = create_title(self.all_setting_dict, '1',
                                                     self.screenComboBox.currentIndex(),
                                                     video_title, output_title_path, part_subtitle_url)

                        if os.path.exists(output_title_path):
                            pic_title_ass = output_title_path
                    #
                    # elif i != video_text_part_num - 1 and i != video_text_part_num - 2:
                    #     part_title = label_text[i].split(',')[0]
                    #     create_title(self.all_setting_dict, '2', self.screenComboBox.currentIndex(),
                    #                  part_title, output_title_path,
                    #                  part_subtitle_url)

                    if i != 0 and i != video_text_part_num - 1 and i != video_text_part_num - 2:
                        part_title_ass_list.append(output_title_path)

                    self.add_log('视频样式字幕已生成')
                    QApplication.processEvents()

                    # 匹配视频素材-----------------------------------------------------------
                    # 视频片段标签
                    part_video_tags = label_text[i].split(',')

                    # 片段配音
                    part_audio_url = output_audio_path

                    # 配音时长
                    audio_length = get_audio_length(part_audio_url)

                    video_path = ''

                    if i == video_text_part_num - 1:
                        # parent_dir = os.getcwd()
                        # # 构造同级的缓存文件夹路径
                        # end_video_dir_path = os.path.join(parent_dir, 'endCredits')
                        # if self.screenComboBox.currentIndex() == 0:
                        #     end_text = self.locationlineEdit.text() + '游片尾_0.mp4'
                        # else:
                        #     end_text = self.locationlineEdit.text() + '游片尾_1.mp4'
                        # video_path = os.path.join(end_video_dir_path, end_text)
                        video_path = self.all_setting_dict['end_video']['end_video_path']
                        if os.path.exists(video_path):
                            part_video_list.append(video_path)
                    else:
                        # 匹配视频重复
                        unSuccessVideoLabel = str(timestamp) + '_videoLabel.xlsx'
                        notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                        notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessVideoLabel)

                        # # 只景点匹配
                        # sights_word_key = part_video_tags[0]
                        #
                        # # 视频开头 结束片段 随机选择一个景点作为关键词
                        # if i == 0:
                        #     # 开头视频选取第一个景点
                        #     sights_word_key = label_text[random.randint(1, video_text_part_num - 3)].split(',')[0]
                        #
                        # if i == video_text_part_num - 2:
                        #     # 结束视频选取最后一个景点
                        #     sights_word_key = label_text[random.randint(1, video_text_part_num - 3)].split(',')[0]
                        #
                        # ftp_videos = get_videos_by_keyword_1(sights_word_key, self.screenComboBox.currentIndex()
                        #                                      , self.locationlineEdit.text(), audio_length)
                        # # 如果这个景区只有一个视频就换景点做封面
                        # if i == 0 or i == video_text_part_num - 2:
                        #     while len(ftp_videos) <= 1:
                        #         sights_word_key = label_text[random.randint(1, video_text_part_num - 3)].split(',')[0]
                        #         ftp_videos = get_videos_by_keyword_1(sights_word_key, self.screenComboBox.currentIndex()
                        #                                              , self.locationlineEdit.text(), audio_length)
                        #
                        # if len(ftp_videos) > 0:
                        #     ftp_video_ids = [video['id'] for video in ftp_videos]
                        #     while (video_path != '' and video_path in part_video_list) or video_path == '':
                        #         video_id = random.choice(ftp_video_ids)
                        #         video_path = download_video(video_id)
                        #         if video_path not in part_video_list and os.path.exists(video_path):
                        #             logging.debug(f'存在下载的视频{video_path}')
                        #             self.run_label.setText(f'正在匹配素材，已经为视频匹配了{len(part_video_list)}个素材')
                        #             part_video_list.append(video_path)
                        #             break
                        # else:
                        #     logging.debug(f'缺少素材,{video_title}这是第{i}段')
                        #     write_arrays_to_excel(notSuccess_label_folder_path, part_video_tags)

                        # 尝试匹配次数 （精确匹配）
                        # 开头使用封面素材

                        if i == 0:
                            cover_time = 0
                            cover_video_path_list = []
                            cover_video_id_list = []
                            attempted_cover_video_ids = set()
                            # 特殊标签处理
                            title_keyword_list = ai_analyse_title_special_tag(video_title, video_text)
                            if len(title_keyword_list) <= 0:
                                #  ai分析标题获取其关键词
                                title_keyword_list = ai_analyse_title_usual_tag(video_title, video_text)
                            if len(title_keyword_list) <= 0:
                                #  标题获取其分词
                                title_keyword_list = title_keyword(video_title)
                            # 单次下载内部已经有 3 次网络重试；外层只为更换候选素材。
                            # 按每段约 3 秒、预留 3 倍候选计算，避免无素材时空转 100 次。
                            max_cover_attempts = max(12, math.ceil(audio_length / 3) * 3)
                            cover_attempts = 0
                            while cover_time + 0.05 < audio_length and cover_attempts < max_cover_attempts:
                                cover_attempts += 1
                                # 随机获取一个封面素材
                                # title_keyword_list = title_keyword(video_title)

                                # ai分析标题获取其关键词
                                self.add_log(f'正在分析标题文案关键词（第{cover_attempts}/{max_cover_attempts}次）')
                                QApplication.processEvents()

                                ftp_cover_video_id = get_cover_video_collect_all(title_keyword_list, '普通素材')
                                if not ftp_cover_video_id:
                                    self.add_log(f'未找到合适的封面素材，继续尝试')
                                    continue
                                if ftp_cover_video_id in attempted_cover_video_ids:
                                    ftp_cover_video_id = get_random_cover_video_by_cate('普通素材')
                                if not ftp_cover_video_id:
                                    self.add_log(f'备选封面素材为空，继续尝试')
                                    continue
                                if ftp_cover_video_id in attempted_cover_video_ids:
                                    self.add_log(f'封面素材候选重复，跳过本次')
                                    continue
                                attempted_cover_video_ids.add(ftp_cover_video_id)
                                video_path = download_cover_video(ftp_cover_video_id)
                                if not video_path or not isinstance(video_path, str) or not os.path.exists(video_path):
                                    failure_reason = get_last_material_download_error() or '本地视频校验未通过'
                                    self.add_log(f'封面素材 {ftp_cover_video_id} 失败：{failure_reason}，尝试下一个')
                                    continue

                                duration = get_video_duration(video_path)
                                remaining_duration = audio_length - cover_time
                                cover_clip_path = video_path
                                if duration > remaining_duration:
                                    cover_clip_path = cut_video_by_audio_length(
                                        video_path,
                                        f'cover_{ftp_cover_video_id}_{cover_attempts}',
                                        remaining_duration
                                    )
                                    if not cover_clip_path or not os.path.exists(cover_clip_path):
                                        self.add_log(f'封面素材 {ftp_cover_video_id} 截取失败，尝试下一个')
                                        continue
                                    duration = get_video_duration(cover_clip_path)

                                if pic_title_video == '':
                                    pic_title_video = video_path
                                cover_video_id_list.append(ftp_cover_video_id)
                                cover_video_path_list.append(cover_clip_path)
                                cover_time += duration
                                self.add_log(f'已匹配封面 {ftp_cover_video_id}，累计时长 {cover_time:.1f}s/{audio_length}s')
                                QApplication.processEvents()

                            if cover_time < audio_length:
                                self.add_log(f'封面匹配达到上限，已匹配时长 {cover_time:.1f}s，继续后续合成')
                                QApplication.processEvents()

                            # 音频时长截取视频内容
                            time.sleep(1)
                            merge_video_path = merge_videos(cover_video_path_list,
                                                            '_'.join(map(str, cover_video_id_list)))
                            if os.path.exists(merge_video_path):
                                self.add_log(f'正在匹配素材，已经为视频匹配了{len(part_video_list) + 1}个素材')
                                QApplication.processEvents()
                                part_video_list.append(merge_video_path)
                            else:
                                failure_reason = get_last_material_download_error() or '没有取得可用于合成的封面素材'
                                self.add_log(f'封面素材合成失败：{failure_reason}')
                                QApplication.processEvents()
                        # 片头片尾随机匹配其中景点视频
                        elif i == video_text_part_num - 2:
                            sights_word_key = label_text[random.randint(1, video_text_part_num - 3)].split(',')[0]
                            ftp_videos = get_videos_by_keyword_1(sights_word_key, self.screenComboBox.currentIndex()
                                                                 , self.locationlineEdit.text().strip(), audio_length,
                                                                 20, "普通素材")
                            ftp_video_ids = [video['id'] for video in ftp_videos]
                            if len(ftp_videos) > 0:
                                video_id = random.choice(ftp_video_ids)
                                video_path = download_video(video_id, self.screenComboBox.currentIndex())
                                if video_path is not None:
                                    if os.path.exists(video_path):
                                        # 音频时长截取视频内容
                                        cut_video_path = cut_video_by_audio_length(video_path, video_id, audio_length)
                                        if os.path.exists(cut_video_path):
                                            self.add_log(
                                                f'正在匹配素材，已经为视频匹配了{len(part_video_list) + 1}个素材')
                                            QApplication.processEvents()

                                            part_video_list.append(cut_video_path)
                                    else:
                                        self.add_log(f'下载素材失败')
                                        QApplication.processEvents()
                        else:
                            while True:
                                ftp_video_List = []
                                # 地区景区匹配到的id
                                location_id_list = []
                                for n, tag in enumerate(part_video_tags):
                                    if len(location_id_list) == 0 and n == 0:
                                        ftp_videos = get_videos_by_keyword_1(tag, self.screenComboBox.currentIndex(),
                                                                             self.locationlineEdit.text().strip(),
                                                                             audio_length, 20, "普通素材")

                                        if len(ftp_videos) <= 0:
                                            print('缺少该关键字的素材')
                                            # part_video_tags.append(str(audio_length))
                                            # 记入未匹配的文案和视频标签
                                            self.add_log(
                                                f'缺少该关键字的素材：{tag}')
                                            QApplication.processEvents()

                                            lost_video_param = {
                                                'title': part_video_tags[0],
                                                'firstTags': '_'.join(part_video_tags),
                                                'secondTags': '',
                                                'videoLength': audio_length,
                                                'screen': self.screenComboBox.currentIndex(),
                                                'accountName': account_name
                                            }
                                            # 将缺少的视频信息记入库中
                                            add_lost_video_record(lost_video_param)

                                            # 将缺少的视频信息记入表中
                                            write_arrays_to_excel(notSuccess_label_folder_path, part_video_tags)
                                            break

                                        for video in ftp_videos:
                                            location_id_list.append(video['id'])

                                    elif len(location_id_list) > 0:
                                        ftp_videos = get_videos_by_keyword(tag, self.screenComboBox.currentIndex(),
                                                                           self.locationlineEdit.text().strip(),
                                                                           location_id_list,
                                                                           audio_length, 20, "普通素材")
                                    else:
                                        ftp_videos = []
                                    # else:
                                    #     part_video_tags.append(str(audio_length))
                                    #     write_arrays_to_excel(notSuccess_label_folder_path, part_video_tags)
                                    #     break

                                    # 提取视频ID列表
                                    if len(ftp_videos) > 0:
                                        ftp_ideo_ids = [video['id'] for video in ftp_videos]
                                        if len(ftp_ideo_ids) <= 0:
                                            continue
                                        ftp_video_List.append(ftp_ideo_ids)

                                # 没有素材退出匹配
                                if len(ftp_video_List) <= 0:
                                    print('缺少该素材，退出合成')
                                    self.add_log(f'缺少该素材，退出合成')
                                    QApplication.processEvents()
                                    return
                                if len(ftp_video_List) == 1:
                                    video_id = random.choice(ftp_video_List[0])
                                else:
                                    video_id = count_and_sort(ftp_video_List)

                                # if try_num > 0:
                                #     video_id = random.choice(count_and_sort(ftp_video_List))

                                # if try_num > 3:
                                #     # 记入未匹配的文案和视频标签
                                #     part_video_tags.append(str(audio_length))
                                #     write_arrays_to_excel(notSuccess_label_folder_path, part_video_tags)
                                #     break
                                try:
                                    video_path = download_video(video_id, self.screenComboBox.currentIndex())

                                    time.sleep(1)
                                    if video_path is not None:
                                        if os.path.exists(video_path):
                                            # 音频时长截取视频内容
                                            cut_video_path = cut_video_by_audio_length(video_path, video_id,
                                                                                       audio_length)

                                            logging.debug(f'这个下载的视频{video_path}的')

                                            if os.path.exists(cut_video_path):
                                                logging.debug(f'存在下载的视频{cut_video_path}')
                                                self.add_log(
                                                    f'正在匹配素材，已经为视频匹配了{len(part_video_list)}个素材')
                                                QApplication.processEvents()

                                                part_video_list.append(cut_video_path)
                                                break
                                            else:
                                                self.add_log(f'下载素材失败')
                                                QApplication.processEvents()
                                                break
                                        else:
                                            self.add_log(f'下载素材失败')
                                            QApplication.processEvents()
                                            break
                                except Exception as e:
                                    logging.debug(f'这个下载的视频{video_path}的错误{str(e)}')
                                    self.add_log(f'下载素材异常：{str(e)}，跳出该段匹配')
                                    QApplication.processEvents()
                                    break

                                # try_num += 1

                # 如果素材数量和文案一样，就进行合成 未处理成功
                video_file_path = ''
                if len(part_video_list) == video_text_part_num:
                    transitionSetting = {
                        'transitionNum': 0,
                        'transitionTime': 0
                    }
                    saveVideoPath = out_dir_path

                    video_id_path_name = 'video_id.xlsx'
                    # 任务文件输出路径
                    video_id_excel_file_path = os.path.join(saveVideoPath, video_id_path_name)

                    # 记录每个视频匹配的素材
                    write_arrays_to_excel(video_id_excel_file_path, [video_title] + part_video_list)

                    # 输出路径
                    video_name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', video_title) + '_0.mp4'

                    video_file_path = os.path.join(saveVideoPath, video_name)

                    excel_file_path_name = '1.xls'
                    # 任务文件输出路径
                    excel_file_path = os.path.join(saveVideoPath, excel_file_path_name)
                    self.pic_time = 0
                    composite_worker = CompositeVideo(part_video_list, part_audio_list, part_srt_ass_list,
                                                      part_title_ass_list, video_file_path,
                                                      transitionSetting, self.pic_time)

                    self.add_log('正在合成一个视频。。。')
                    QApplication.processEvents()

                    self.thread_pool.start(composite_worker)
                    # 创建一个事件循环
                    composite_worker.signals.finished.connect(self.on_success_occurred)
                    composite_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()
                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'合成一个视频失败')
                        continue

                    self.add_log('已经合成一个视频，接下来进行后期处理。')
                    QApplication.processEvents()

                    if not os.path.exists(video_file_path):
                        self.add_log('没有已经合成一个视频，跳过。')
                        QApplication.processEvents()
                        continue

                    # 添加图片封面
                    output_pic_video_path = video_file_path.replace('_0.mp4', '_1.mp4')
                    # 添加视频封面工作流
                    addPicWorker = AddPicWorker(video_file_path, pic_title_video, 'white.png', pic_title_ass,
                                                output_pic_video_path)
                    self.thread_pool.start(addPicWorker)
                    addPicWorker.signals.finished.connect(self.on_success_occurred)
                    addPicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    # 匹配添加音乐
                    parent_dir = os.getcwd()
                    # 构造同级的缓存文件夹路径
                    cache_music_dir_path = os.path.join(parent_dir, 'cacheMusic')
                    # 获取文件夹中的所有MP3文件
                    mp3_files = [f for f in os.listdir(cache_music_dir_path) if
                                 f.endswith('.mp3') or f.endswith('.MP3')]

                    # 如果文件夹中有MP3文件，则随机选择一个
                    if mp3_files:
                        random_mp3_file = random.choice(mp3_files)
                        random_mp3_file_path = os.path.join(cache_music_dir_path, random_mp3_file)
                        print(f"随机选择的MP3文件路径为：{random_mp3_file_path}")
                    else:
                        print("文件夹中没有找到MP3文件,缺少音乐。")
                        break

                    # 加载音频文件
                    # audio = AudioSegment.from_file(mp4_files)

                    # 获取音乐音频的音量（响度）
                    # music_volume = audio.dBFS  # 返回音频的响度，单位为分贝
                    # mb_db = 20.0
                    bgAudioVolume = 40
                    output_bgm_video_path = output_pic_video_path.replace('_1.mp4', '_2.mp4')
                    addMusicWorker = AddMusicWorker(output_pic_video_path, random_mp3_file_path, 100, bgAudioVolume,
                                                    output_bgm_video_path)

                    self.thread_pool.start(addMusicWorker)
                    # 创建一个事件循环
                    addMusicWorker.signals.finished.connect(self.on_success_occurred)
                    addMusicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加音乐失败')
                        continue

                    self.add_log('后期处理,已添加音乐。')
                    QApplication.processEvents()

                    # 添加水印
                    watermark_location_examples = [['50', '50'], ['main_w-overlay_w-100', '50'],
                                                   ['50', 'main_h-overlay_h-50'],
                                                   ['main_w-overlay_w-50', 'main_h-overlay_h-50'],
                                                   ['(main_w-overlay_w)/2', '(main_h-overlay_h)/2'],
                                                   ['(main_w-overlay_w)/2', '50'],
                                                   ['(main_w-overlay_w)/2', 'main_h-overlay_h-100']]

                    watermark_setting = {
                        'watermark_location': watermark_location_examples[
                            self.all_setting_dict['water_set']['position']],
                        'zoom_size': self.all_setting_dict['water_set']['zoom'],
                        'pic_alpha': self.all_setting_dict['water_set']['alpha']
                    }
                    final_output_path = output_bgm_video_path.replace('_2.mp4', '.mp4')
                    add_text_watermark_worker = AddWatermarkWorker(output_bgm_video_path, final_output_path,
                                                                   watermark_setting, 2,
                                                                   self.all_setting_dict['water_set']['filePath'])
                    self.thread_pool.start(add_text_watermark_worker)
                    # 创建一个事件循环
                    add_text_watermark_worker.signals.finished.connect(self.on_success_occurred)
                    add_text_watermark_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加水印失败')
                        continue

                    self.add_log('后期处理,已添加水印。')
                    QApplication.processEvents()

                    # 视频压缩
                    temp_compressed_path = final_output_path.replace('.mp4', '_temp_compressed.mp4')
                    compress_video_worker = CompressVideoWorker(final_output_path, temp_compressed_path)

                    self.thread_pool.start(compress_video_worker)
                    compress_video_worker.signals.finished.connect(self.on_success_occurred)
                    compress_video_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        self.add_log('视频压缩失败，使用原始文件')
                        QApplication.processEvents()
                    else:
                        self.add_log('视频压缩完成')
                        QApplication.processEvents()

                    # 移除中间视频
                    if os.path.exists(video_file_path):
                        os.remove(video_file_path)

                    if os.path.exists(output_pic_video_path):
                        os.remove(output_pic_video_path)

                    if os.path.exists(output_bgm_video_path):
                        os.remove(output_bgm_video_path)

                    data_dict = {
                        "标题": video_title.replace('|', ''),
                        "标签": video_tag,
                        "文件路径": final_output_path.replace('/', '\\'),
                        "描述": ','.join(video_text),
                        "封面路径": "",
                        "图片集合": "",
                        "关联商品": "",
                        "分区分类": "旅游",
                        "备注": ""
                    }

                    write_to_old_excel(excel_file_path, data_dict)

                    # 上传任务信息
                    # 账号姓名
                    # account_name = self.accountNameLineEdit.text()
                    # 账号account
                    account_result = self.get_upload_accounts(account_name)

                    # 上传任务
                    if len(account_result) > 0:
                        for (account, mac) in account_result:
                            print(account)
                            task_param = {
                                'name': account_name,
                                'account': account,
                                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'title': data_dict.get('标题'),
                                'mac': mac,
                                'tag': data_dict.get('标签'),
                                'path': data_dict.get('文件路径'),
                                'describe': data_dict.get('描述'),
                                'classify': data_dict.get('分区分类'),
                                'task_type': 1,
                            }
                            add_user_task(task_param)
                            self.add_log(f'{account_name}{account}上传视频任务:{final_output_path}')
                            QApplication.processEvents()
                    self.add_log(f'生成完成一个视频:{final_output_path}')
                    QApplication.processEvents()
                    generated_count += 1

                else:
                    failed_count += 1
                    logging.debug(f'匹配的视频与文案数量不一致')
                    print('匹配的视频与文案数量不一致')
                    unSuccessCopy = str(timestamp) + '_copy.xlsx'
                    unSuccessLabel = str(timestamp) + '_label.xlsx'
                    notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                    notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
                    notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
                    # 记入未匹配的文案和视频标签
                    write_arrays_to_excel(notSuccess_copy_folder_path, video_title_text[0:-1])
                    write_arrays_to_excel(notSuccess_label_folder_path, label_text[0:-1])
                    self.add_log('跳过一个脚本文案，可能是没有匹配到视频，已记录')
                    QApplication.processEvents()

            # 删除cut video缓存
            clean_cut_cache()
            clean_cache()
            copy_start_num += 1
            label_start_num += 1

        current_directory = os.getcwd()
        unSuccessCopy = str(timestamp) + '_copy.xlsx'
        unSuccessLabel = str(timestamp) + '_label.xlsx'
        notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
        notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
        notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
        if os.path.exists(notSuccess_copy_folder_path) and os.path.exists(notSuccess_label_folder_path):
            try:
                self.add_log('有视频记录没有生成完毕，可补充素材后点击继续生成')
                QApplication.processEvents()
                self.copyFileLabel.setText(notSuccess_copy_folder_path)
                self.labelFilelabel.setText(notSuccess_label_folder_path)

                # 展示缺少的标签
                unSuccessVideoLabel = str(timestamp) + '_videoLabel.xlsx'
                notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessVideoLabel)
                # 读取整个工作表（默认第一张）
                df = _read_excel(notSuccess_label_folder_path)
                # 设置表格的行列数
                self.lostVideoTableWidget.setRowCount(df.shape[0])
                self.lostVideoTableWidget.setColumnCount(df.shape[1])

                # 获取水平表头视图
                horizontal_header = self.lostVideoTableWidget.horizontalHeader()

                # 设置表头样式表（背景色、文字颜色等）
                horizontal_header.setStyleSheet("""
                                                   QHeaderView::section {
                                                       background-color: rgb(56, 56, 56);
                                                       color: white;                     
                                                       ont-weight: bold;          /* 文字加粗 */
                                                       border-right: 1px solid #ddd; /* 右侧边框 */
                                                       text-align: center;         /* 文字居中 */
                                                   }
                                               """)
                vertical_header = self.lostVideoTableWidget.verticalHeader()

                vertical_header.setStyleSheet("""
                                                   QHeaderView::section {
                                                       background-color: rgb(56, 56, 56);
                                                       color: white;                    
                                                       font-weight: bold;          /* 文字加粗 */
                                                       border-right: 1px solid #ddd; /* 右侧边框 */
                                                       text-align: center;         /* 文字居中 */
                                                   }
                                               """)

                # 填充数据
                for row in range(df.shape[0]):
                    for col in range(df.shape[1]):
                        item = QTableWidgetItem(str(df.iat[row, col]))
                        self.lostVideoTableWidget.setItem(row, col, item)
                self.lostVideoTableWidget.resizeColumnsToContents()
            except Exception as e:
                print(f'展示缺少的标签错误{str(e)}')
                pass

        else:
            if failed_count > 0:
                self.add_log(f'本次生成结束：成功{generated_count}个，失败{failed_count}个')
            elif generated_count > 0:
                self.add_log(f'所有视频记录生成完毕，共生成{generated_count}个视频')
            else:
                self.add_log('本次没有生成视频，请查看前面的失败原因')
            QApplication.processEvents()

    # --城市通用类视频
    def compositeCityStrategyVideo(self, copy_file, label_file, out_dir_path, account_name):
        # if self.saveVideoPathLabel.text() == '':
        #     QMessageBox.information(self, "提示", f"请选择视频保存路径")
        #     return

        self.add_log('开始合成根据文案合成视频')
        QApplication.processEvents()

        # 时间
        timestamp = int(time.time())

        if self.randomVideoModelCheckBox.isChecked():
            model_result = get_random_video_model()
            model_set_dict = json.loads(model_result['model_set'])
            self.all_setting_dict['title_set'] = model_set_dict['title_set']
            self.all_setting_dict['part_title_set'] = model_set_dict['part_title_set']
            self.all_setting_dict['srt_set'] = model_set_dict['srt_set']
            self.all_setting_dict['voice_set'] = model_set_dict['voice_set']
            self.all_setting_dict['part_title_part_0_set'] = model_set_dict['part_title_part_0_set']
            self.all_setting_dict['part_title_part_1_set'] = model_set_dict['part_title_part_1_set']
            self.all_setting_dict['part_title_part_2_set'] = model_set_dict['part_title_part_2_set']
            self.all_setting_dict['part_title_part_3_set'] = model_set_dict['part_title_part_3_set']
            self.all_setting_dict['part_title_part_4_set'] = model_set_dict['part_title_part_4_set']
            self.all_setting_dict['part_title_part_5_set'] = model_set_dict['part_title_part_5_set']
        else:
            self.all_setting_dict = read_dict_from_txt('setting.txt')

        if not os.path.exists(self.all_setting_dict['end_video']['end_video_path']):
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                             QMessageBox QLabel {
                             background-color: rgb(22, 23, 25);
                             color: rgb(255, 255, 255);
                            }
                            QMessageBox {
                            background-color: rgb(22, 23, 25);
                            color: rgb(255, 255, 255);
                            }
                        """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"请选择视频添加的片尾")
            msg_box.exec()
            return

        # 删除video缓存
        clean_cut_cache()
        clean_cache()

        # copy 起始行
        copy_start_num = get_first_data_row(copy_file)

        # label 起始行
        label_start_num = get_first_data_row(label_file)

        self.add_log(f'读取视频文案,文案文件路径是{str(copy_file)},标签文件路径是{str(label_file)}')

        if copy_start_num == -1 or label_start_num == -1 or copy_start_num is None or label_start_num is None:
            self.add_log('文案文件或者标签文件没有数据可读，结束合成视频')
            QApplication.processEvents()
            return

        # tts 速度
        speed_value = str(self.all_setting_dict['voice_set']['spd_0'])
        if not str(speed_value).startswith('-'):
            speed_value = '+' + speed_value
        speed_value = speed_value + '%'

        # 获取音频设置
        audio_setting = {
            'api_type': self.all_setting_dict['voice_set']['api_type'],
            'audio_role': self.audio_role_list[self.all_setting_dict['voice_set']['role_0']],
            'speed_value': speed_value,
            'volume_value': self.all_setting_dict['voice_set']['vol_0']
        }

        if self.all_setting_dict['voice_set']['api_type'] == 1:
            # 获取音频设置
            audio_setting = {
                'api_type': self.all_setting_dict['voice_set']['api_type'],
                'audio_role': int(
                    self.audio_bd_role_list[self.all_setting_dict['voice_set']['role_1']].split(':')[1]),
                'speed_value': self.all_setting_dict['voice_set']['spd_1'],
                'volume_value': self.all_setting_dict['voice_set']['vol_1'],
                'tone_value': self.all_setting_dict['voice_set']['pit_1']
            }

        while True:

            # 获取视频文案
            video_title_text = get_row_data(copy_file, copy_start_num)

            self.add_log('读取视频文案')
            QApplication.processEvents()

            video_title_text.append('记得点赞关注评论')

            # 获取视频标签
            label_text = get_row_data(label_file, label_start_num)

            self.add_log(f'读取视频标签，{"&&".join(video_title_text)}，{"&&".join(label_text)}')
            QApplication.processEvents()

            if len(video_title_text) < 3:
                self.add_log('全部生成完成')
                QApplication.processEvents()
                # QMessageBox.information(self, "完成", f"所有视频已生成处理完成，已生成任务列表")
                break

            label_text.append('点赞,关注,评论')

            # 标题
            video_title = video_title_text[0].strip()

            # 标签
            video_tag = video_title_text[1].strip()

            # 文案
            video_text = video_title_text[2:]

            # 文案段数
            video_text_part_num = len(video_text)
            if video_text_part_num <= 2:
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                label_start_num += 1
                logging.debug(f'合成一个视频失败')
                continue

            # 视频处理缓存文件夹
            tamp_folder_name = 'tempConcateVideo'
            current_directory = os.getcwd()
            tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
            video_tamp_path_name = 'video_cache_file'
            video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)

            if len(video_text) > 0:

                # 素材缓存路径
                part_video_list = []

                # 字幕缓存路径
                part_srt_ass_list = []

                # 音频缓存路径
                part_audio_list = []

                # 标题缓存路径
                part_title_ass_list = []

                # 配音初始字幕生成-----------------------------------------------------------
                product_worker = SaWorker(video_text, audio_setting)
                self.thread_pool.start(product_worker)
                # 事件循环
                product_worker.signals.finished.connect(self.on_success_occurred)
                product_worker.signals.errorOccurred.connect(self.on_error_occurred)
                self.loop.exec()
                if self.error_flag:
                    # 删除cut video缓存
                    clean_cut_cache()
                    clean_cache()
                    copy_start_num += 1
                    label_start_num += 1
                    logging.debug(f'合成一个视频失败')
                    continue

                self.add_log('ai分析文案，已经为视频生成字幕配音即标签')
                QApplication.processEvents()

                # 生成标题、小标题以及字幕的ass文件-----------------------------------------------------------

                # 视频不重复记录
                video_id_list = []

                for i in range(video_text_part_num):

                    srt_file_name = f"temp_subtitle{i}.srt"

                    audio_file_name = f"temp_final_audio{i}.mp3"

                    # 原字幕文件
                    part_subtitle_url = os.path.join(video_tamp_path, srt_file_name)

                    # ass字幕文件
                    output_path = part_subtitle_url.replace('.srt', '.ass')

                    # 标题字幕文件
                    output_title_path = part_subtitle_url.replace('.srt', '_title.ass')

                    # 音频文件
                    output_audio_path = os.path.join(video_tamp_path, audio_file_name)

                    # 转换成ass
                    convert_srt_to_ass(part_subtitle_url, output_path, self.all_setting_dict['srt_set'])

                    if i == 0:
                        remove_dialogue_text(output_path)

                    # 通用类需要去除开头和片尾标题
                    if i == video_text_part_num - 1:
                        remove_all_dialogue_text(output_path)

                    # 转换完成后 记录ass字幕位置
                    part_srt_ass_list.append(output_path)

                    # 记录音频位置
                    part_audio_list.append(output_audio_path)

                    # 创建标题ass，通用只有大标题
                    if i == 0:
                        self.pic_time = create_title(self.all_setting_dict, '1',
                                                     self.screenComboBox.currentIndex(),
                                                     video_title, output_title_path, part_subtitle_url)

                        part_title_ass_list.append(output_title_path)

                    self.add_log('视频样式字幕已生成')
                    QApplication.processEvents()

                    # 匹配视频素材-----------------------------------------------------------
                    # 视频片段标签
                    part_video_tags = label_text[i].split(',')

                    # 片段配音
                    part_audio_url = output_audio_path

                    # 配音时长
                    audio_length = get_audio_length(part_audio_url)

                    if i == video_text_part_num - 1:
                        video_path = self.all_setting_dict['end_video']['end_video_path']
                        if os.path.exists(video_path):
                            part_video_list.append(video_path)
                    else:
                        # 匹配视频
                        unSuccessVideoLabel = str(timestamp) + '_videoLabel.xlsx'
                        notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                        notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessVideoLabel)

                        # 片头片尾随机匹配其中景点视频
                        if i == 0 or i == video_text_part_num - 2:
                            sights_word_key = label_text[random.randint(1, video_text_part_num - 3)].split(',')[0]
                            ftp_videos = get_videos_by_keyword_1(sights_word_key, self.screenComboBox.currentIndex()
                                                                 , self.locationlineEdit.text().strip(), audio_length,
                                                                 20, '城市通用')
                            ftp_video_ids = [video['id'] for video in ftp_videos]
                            if len(ftp_videos) > 0:
                                video_id = random.choice(ftp_video_ids)

                                try_time = 0
                                while video_id in video_id_list and try_time < 5:
                                    video_id = random.choice(ftp_video_ids)
                                    try_time += 1

                                video_id_list.append(video_id)

                                video_path = download_video(video_id, self.screenComboBox.currentIndex())
                                if video_path is not None:
                                    if os.path.exists(video_path):
                                        # 音频时长截取视频内容
                                        time.sleep(1)
                                        cut_video_path = cut_video_by_audio_length(video_path, video_id, audio_length)
                                        if os.path.exists(cut_video_path):
                                            self.add_log(
                                                f'正在匹配素材，已经为视频匹配了{len(part_video_list) + 1}个素材')
                                            QApplication.processEvents()

                                            part_video_list.append(cut_video_path)
                                    else:
                                        self.add_log(f'下载素材失败')
                                        QApplication.processEvents()
                        else:
                            while True:
                                ftp_video_List = []
                                # 地区景区匹配到的id
                                location_id_list = []
                                for n, tag in enumerate(part_video_tags):
                                    if len(location_id_list) == 0 and n == 0:
                                        ftp_videos = get_videos_by_keyword_1(tag,
                                                                             self.screenComboBox.currentIndex(),
                                                                             self.locationlineEdit.text().strip(),
                                                                             audio_length, 20,'城市通用')

                                        if len(ftp_videos) <= 0:
                                            print('缺少该关键字的素材')
                                            # part_video_tags.append(str(audio_length))
                                            # 记入未匹配的文案和视频标签

                                            # lost_video_param = {
                                            #     'title': part_video_tags[0],
                                            #     'firstTags': '_'.join(part_video_tags),
                                            #     'secondTags': '',
                                            #     'videoLength': audio_length,
                                            #     'screen': self.screenComboBox.currentIndex()
                                            # }
                                            # # 将缺少的视频信息记入库中
                                            # add_lost_video_record(lost_video_param)

                                            # 将缺少的视频信息记入表中
                                            write_arrays_to_excel(notSuccess_label_folder_path, part_video_tags)
                                            break

                                        for video in ftp_videos:
                                            location_id_list.append(video['id'])

                                    elif len(location_id_list) > 0:
                                        ftp_videos = get_videos_by_keyword(tag, self.screenComboBox.currentIndex(),
                                                                           self.locationlineEdit.text().strip(),
                                                                           location_id_list,
                                                                           audio_length, 20, '城市通用')
                                    else:
                                        ftp_videos = []

                                    # 提取视频ID列表
                                    if len(ftp_videos) > 0:
                                        ftp_ideo_ids = [video['id'] for video in ftp_videos]
                                        if len(ftp_ideo_ids) <= 0:
                                            continue
                                        ftp_video_List.append(ftp_ideo_ids)

                                # 没有素材退出匹配
                                if len(ftp_video_List) <= 0:
                                    print('缺少该素材，退出合成')
                                    self.add_log(f'缺少该素材，退出合成')
                                    QApplication.processEvents()
                                    return

                                if len(ftp_video_List) == 1:
                                    video_id = random.choice(ftp_video_List[0])
                                else:
                                    video_id = count_and_sort(ftp_video_List)

                                try_time = 0
                                while video_id in video_id_list and try_time < 5:
                                    if len(ftp_video_List) == 1:
                                        video_id = random.choice(ftp_video_List[0])
                                    else:
                                        video_id = count_and_sort(ftp_video_List)
                                    try_time += 1
                                video_id_list.append(video_id)

                                video_path = download_video(video_id, self.screenComboBox.currentIndex())

                                time.sleep(1)
                                if video_path is not None:
                                    if os.path.exists(video_path):
                                        # 音频时长截取视频内容
                                        cut_video_path = cut_video_by_audio_length(video_path, video_id, audio_length)

                                        logging.debug(f'这个下载的视频{video_path}的')

                                        if os.path.exists(cut_video_path):
                                            logging.debug(f'存在下载的视频{cut_video_path}')
                                            self.add_log(
                                                f'正在匹配素材，已经为视频匹配了{len(part_video_list) + 1}个素材')
                                            QApplication.processEvents()
                                            part_video_list.append(cut_video_path)
                                            break
                                        else:
                                            self.add_log(f'下载素材失败')
                                            QApplication.processEvents()
                                            break
                                    else:
                                        self.add_log(f'下载素材失败')
                                        QApplication.processEvents()
                                        break

                                # try_num += 1

                # 如果素材数量和文案一样，就进行合成 未处理成功
                if len(part_video_list) == video_text_part_num:
                    transitionSetting = {
                        'transitionNum': 0,
                        'transitionTime': 0
                    }
                    saveVideoPath = out_dir_path

                    video_id_path_name = 'video_id.xlsx'
                    # 任务文件输出路径
                    video_id_excel_file_path = os.path.join(saveVideoPath, video_id_path_name)

                    # 记录每个视频匹配的素材
                    write_arrays_to_excel(video_id_excel_file_path, [video_title] + part_video_list)

                    # 输出路径
                    video_name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', video_title) + '_0.mp4'

                    video_file_path = os.path.join(saveVideoPath, video_name)

                    excel_file_path_name = '1.xls'
                    # 任务文件输出路径
                    excel_file_path = os.path.join(saveVideoPath, excel_file_path_name)

                    composite_worker = CompositeVideo(part_video_list, part_audio_list, part_srt_ass_list,
                                                      part_title_ass_list, video_file_path,
                                                      transitionSetting, self.pic_time)

                    self.add_log(f'正在合成拼接一个视频。。。')
                    QApplication.processEvents()

                    self.thread_pool.start(composite_worker)
                    # 创建一个事件循环
                    composite_worker.signals.finished.connect(self.on_success_occurred)
                    composite_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()
                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'合成一个视频失败')
                        continue

                    self.add_log(f'已经合成一个视频，接下来进行后期处理。')
                    QApplication.processEvents()

                    # 匹配添加音乐
                    parent_dir = os.getcwd()
                    # 构造同级的缓存文件夹路径
                    cache_music_dir_path = os.path.join(parent_dir, 'cacheMusic1')
                    # 获取文件夹中的所有MP3文件
                    mp3_files = [f for f in os.listdir(cache_music_dir_path) if
                                 f.endswith('.mp3') or f.endswith('.MP3')]

                    # 如果文件夹中有MP3文件，则随机选择一个
                    if mp3_files:
                        random_mp3_file = random.choice(mp3_files)
                        random_mp3_file_path = os.path.join(cache_music_dir_path, random_mp3_file)
                        print(f"随机选择的MP3文件路径为：{random_mp3_file_path}")
                    else:
                        print("文件夹中没有找到MP3文件,缺少音乐。")
                        break

                    # 加载音频文件
                    # audio = AudioSegment.from_file(mp4_files)

                    # 获取音乐音频的音量（响度）
                    # music_volume = audio.dBFS  # 返回音频的响度，单位为分贝
                    # mb_db = 20.0
                    bgAudioVolume = 40
                    output_bgm_video_path = video_file_path.replace('_0.mp4', '_1.mp4')
                    addMusicWorker = AddMusicWorker(video_file_path, random_mp3_file_path, 100, bgAudioVolume,
                                                    output_bgm_video_path)

                    self.thread_pool.start(addMusicWorker)
                    # 创建一个事件循环
                    addMusicWorker.signals.finished.connect(self.on_success_occurred)
                    addMusicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加音乐失败')
                        continue

                    self.add_log(f'后期处理,已添加音乐。')
                    QApplication.processEvents()

                    # 添加水印
                    watermark_location_examples = [['50', '50'], ['main_w-overlay_w-100', '50'],
                                                   ['50', 'main_h-overlay_h-50'],
                                                   ['main_w-overlay_w-50', 'main_h-overlay_h-50'],
                                                   ['(main_w-overlay_w)/2', '(main_h-overlay_h)/2'],
                                                   ['(main_w-overlay_w)/2', '50'],
                                                   ['(main_w-overlay_w)/2', 'main_h-overlay_h-100']]

                    watermark_setting = {
                        'watermark_location': watermark_location_examples[
                            self.all_setting_dict['water_set']['position']],
                        'zoom_size': self.all_setting_dict['water_set']['zoom'],
                        'pic_alpha': self.all_setting_dict['water_set']['alpha']
                    }
                    final_output_path = output_bgm_video_path.replace('_1.mp4', '.mp4')
                    add_text_watermark_worker = AddWatermarkWorker(output_bgm_video_path, final_output_path,
                                                                   watermark_setting, 2,
                                                                   self.all_setting_dict['water_set']['filePath'])
                    self.thread_pool.start(add_text_watermark_worker)
                    # 创建一个事件循环
                    add_text_watermark_worker.signals.finished.connect(self.on_success_occurred)
                    add_text_watermark_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加水印失败')
                        continue

                    self.add_log(f'后期处理,已添加水印。')
                    QApplication.processEvents()

                    # 视频压缩
                    temp_compressed_path = final_output_path.replace('.mp4', '_temp_compressed.mp4')
                    compress_video_worker = CompressVideoWorker(final_output_path, temp_compressed_path)

                    self.thread_pool.start(compress_video_worker)
                    compress_video_worker.signals.finished.connect(self.on_success_occurred)
                    compress_video_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        self.add_log('视频压缩失败，使用原始文件')
                        QApplication.processEvents()
                    else:
                        self.add_log('视频压缩完成')
                        QApplication.processEvents()

                    # 移除中间视频
                    if os.path.exists(video_file_path):
                        os.remove(video_file_path)

                    if os.path.exists(output_bgm_video_path):
                        os.remove(output_bgm_video_path)

                    data_dict = {
                        "标题": video_title.replace('|', ''),
                        "标签": video_tag,
                        "文件路径": final_output_path.replace('/', '\\'),
                        "描述": ','.join(video_text),
                        "封面路径": "",
                        "图片集合": "",
                        "关联商品": "",
                        "分区分类": "旅游",
                        "备注": ""
                    }

                    write_to_old_excel(excel_file_path, data_dict)

                    # 上传任务信息
                    # 账号姓名
                    # account_name = self.accountNameLineEdit.text()
                    # 账号account
                    account_result = self.get_upload_accounts(account_name)

                    # 上传任务
                    if len(account_result) > 0:
                        for (account, mac) in account_result:
                            print(account)
                            task_param = {
                                'name': account_name,
                                'account': account,
                                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'title': data_dict.get('标题'),
                                'mac': mac,
                                'tag': data_dict.get('标签'),
                                'path': data_dict.get('文件路径'),
                                'describe': data_dict.get('描述'),
                                'classify': data_dict.get('分区分类'),
                                'task_type': 3,
                            }
                            add_user_task(task_param)
                            self.add_log(f'{account_name}{account}上传视频任务:{final_output_path}')
                            QApplication.processEvents()

                    self.run_label.setText(f'生成完成一个视频:{final_output_path}')
                else:
                    logging.debug(f'匹配的视频与文案数量不一致')
                    print('匹配的视频与文案数量不一致')
                    unSuccessCopy = str(timestamp) + '_copy.xlsx'
                    unSuccessLabel = str(timestamp) + '_label.xlsx'
                    notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                    notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
                    notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
                    # 记入未匹配的文案和视频标签
                    write_arrays_to_excel(notSuccess_copy_folder_path, video_title_text[0:-1])
                    write_arrays_to_excel(notSuccess_label_folder_path, label_text[0:-1])
                    self.add_log(f'跳过一个脚本文案，可能是没有匹配到视频，已记录')
                    QApplication.processEvents()

            # 删除cut video缓存
            clean_cut_cache()
            clean_cache()
            copy_start_num += 1
            label_start_num += 1

        current_directory = os.getcwd()
        unSuccessCopy = str(timestamp) + '_copy.xlsx'
        unSuccessLabel = str(timestamp) + '_label.xlsx'
        notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
        notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
        notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
        if os.path.exists(notSuccess_copy_folder_path) and os.path.exists(notSuccess_label_folder_path):
            self.add_log('有视频记录没有生成完毕，可补充素材后点击继续生成')
            QApplication.processEvents()
            self.copyFileLabel.setText(notSuccess_copy_folder_path)
            self.labelFilelabel.setText(notSuccess_label_folder_path)
        else:
            self.add_log('所有视频记录已经生成完毕，无记录可生成')
            QApplication.processEvents()

    # ========== 辅助函数：记录时间 ==========
    def _record_step_time(self, step_name, step_start_time):
        """记录步骤耗时"""
        elapsed = time.time() - step_start_time
        self.step_timings[step_name] = elapsed
        self.add_log(f'⏱️ {step_name} 耗时: {elapsed:.2f}秒')
        QApplication.processEvents()
        return elapsed

    def _print_total_time(self, total_start_time, video_title):
        """打印总耗时统计"""
        total_time = time.time() - total_start_time

        self.add_log('=' * 60)
        self.add_log(f'📊 视频合成完成: {video_title}')
        self.add_log(f'⏱️ 总耗时: {total_time:.2f}秒')
        self.add_log('=' * 60)

        # 打印各步骤耗时
        self.add_log('各步骤耗时统计:')
        sorted_steps = sorted(self.step_timings.items(), key=lambda x: x[1], reverse=True)
        for step, elapsed in sorted_steps:
            percentage = (elapsed / total_time) * 100 if total_time > 0 else 0
            self.add_log(f'  - {step}: {elapsed:.2f}秒 ({percentage:.1f}%)')

        # 找出最慢的步骤
        if sorted_steps:
            slowest_step, slowest_time = sorted_steps[0]
            self.add_log(f'⚠️ 最慢步骤: {slowest_step} ({slowest_time:.2f}秒)')
        self.add_log('=' * 60)
        QApplication.processEvents()

    # --全国介绍类视频
    def compositeCNIntroVideo(self, copy_file, label_file, out_dir_path, account_name):

        self.add_log('开始合成根据文案合成视频')
        QApplication.processEvents()

        # 时间
        timestamp = int(time.time())

        self.all_setting_dict = read_dict_from_txt('setting.txt')

        if not os.path.exists(self.all_setting_dict['end_video']['end_video_path']):
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                             QMessageBox QLabel {
                             background-color: rgb(22, 23, 25);
                             color: rgb(255, 255, 255);
                            }
                            QMessageBox {
                            background-color: rgb(22, 23, 25);
                            color: rgb(255, 255, 255);
                            }
                        """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"请选择视频添加的片尾")
            msg_box.exec()
            return

        # 删除video缓存
        clean_cut_cache()
        clean_cache()

        # copy 起始行
        copy_start_num = get_first_data_row(copy_file)

        # label 起始行
        label_start_num = get_first_data_row(label_file)

        self.add_log(f'读取视频文案,文案文件路径是{str(copy_file)},标签文件路径是{str(label_file)}')
        QApplication.processEvents()

        if copy_start_num == -1 or label_start_num == -1 or copy_start_num is None or label_start_num is None:
            self.add_log('文案文件或者标签文件没有数据可读，结束合成视频')
            QApplication.processEvents()
            return

        while True:

            if self.randomVideoModelCheckBox.isChecked():
                model_result = get_random_video_model()
                model_set_dict = json.loads(model_result['model_set'])
                self.all_setting_dict['title_set'] = model_set_dict['title_set']
                self.all_setting_dict['part_title_set'] = model_set_dict['part_title_set']
                self.all_setting_dict['srt_set'] = model_set_dict['srt_set']
                self.all_setting_dict['voice_set'] = model_set_dict['voice_set']
                self.all_setting_dict['part_title_part_0_set'] = model_set_dict['part_title_part_0_set']
                self.all_setting_dict['part_title_part_1_set'] = model_set_dict['part_title_part_1_set']
                self.all_setting_dict['part_title_part_2_set'] = model_set_dict['part_title_part_2_set']
                self.all_setting_dict['part_title_part_3_set'] = model_set_dict['part_title_part_3_set']
                self.all_setting_dict['part_title_part_4_set'] = model_set_dict['part_title_part_4_set']
                self.all_setting_dict['part_title_part_5_set'] = model_set_dict['part_title_part_5_set']

            # tts 速度
            speed_value = str(self.all_setting_dict['voice_set']['spd_0'])
            if not str(speed_value).startswith('-'):
                speed_value = '+' + speed_value
            speed_value = speed_value + '%'

            # 获取音频设置
            audio_setting = {
                'api_type': self.all_setting_dict['voice_set']['api_type'],
                'audio_role': self.audio_role_list[self.all_setting_dict['voice_set']['role_0']],
                'speed_value': speed_value,
                'volume_value': self.all_setting_dict['voice_set']['vol_0']
            }

            if self.all_setting_dict['voice_set']['api_type'] == 1:
                # 获取音频设置
                audio_setting = {
                    'api_type': self.all_setting_dict['voice_set']['api_type'],
                    'audio_role': int(
                        self.audio_bd_role_list[self.all_setting_dict['voice_set']['role_1']].split(':')[1]),
                    'speed_value': self.all_setting_dict['voice_set']['spd_1'],
                    'volume_value': self.all_setting_dict['voice_set']['vol_1'],
                    'tone_value': self.all_setting_dict['voice_set']['pit_1']
                }

            # 获取视频文案
            video_title_text = get_row_data(copy_file, copy_start_num)

            self.add_log('读取视频文案')
            QApplication.processEvents()

            # video_title_text.append('记得点赞关注评论')

            # 获取视频标签
            label_text = get_row_data(label_file, label_start_num)

            self.add_log(f'读取视频标签，{"&&".join(video_title_text)}，{"&&".join(label_text)}')
            QApplication.processEvents()

            if len(video_title_text) < 3:
                self.add_log('全部生成完成')
                QApplication.processEvents()
                break

            # label_text.append('点赞,关注,评论')

            # 标题
            video_title = video_title_text[0].strip()

            # 标签
            video_tag = video_title_text[1].strip()

            # 文案
            video_text = video_title_text[2:]

            # 文案段数
            video_text_part_num = len(video_text)
            if video_text_part_num <= 2:
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                label_start_num += 1
                logging.debug(f'合成一个视频失败')
                continue

            try:
                # 处理空格
                for i, part_video_text in enumerate(video_text):

                    part_video_text_list = part_video_text.split(' ')

                    part_label_text_list = label_text[i].split(',')

                    if (part_label_text_list[0] not in part_video_text_list[0] and i != 0
                            and i != len(video_text) - 1 and i != len(video_text) - 2):
                        part_video_text_list = [part_video_text_list[0] + part_video_text_list[
                            1]] + part_video_text_list[
                                  2:]

                        video_text[i] = ' '.join(part_video_text_list)
            except Exception as e:
                print(f'可能不符合格式要求{e}')
                clean_cache()
                copy_start_num += 1
                label_start_num += 1
                continue

            # 视频处理缓存文件夹
            tamp_folder_name = 'tempConcateVideo'
            current_directory = os.getcwd()
            tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
            video_tamp_path_name = 'video_cache_file'
            video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)

            if len(video_text) > 0:

                # 素材缓存路径
                part_video_list = []

                # 字幕缓存路径
                part_srt_ass_list = []

                # 音频缓存路径
                part_audio_list = []

                # 标题缓存路径
                part_title_ass_list = []

                # 配音初始字幕生成-----------------------------------------------------------
                product_worker = SaWorker(video_text, audio_setting)
                self.thread_pool.start(product_worker)
                # 事件循环
                product_worker.signals.finished.connect(self.on_success_occurred)
                product_worker.signals.errorOccurred.connect(self.on_error_occurred)
                self.loop.exec()
                if self.error_flag:
                    # 删除cut video缓存
                    clean_cut_cache()
                    clean_cache()
                    copy_start_num += 1
                    label_start_num += 1
                    logging.debug(f'合成一个视频失败')
                    continue
                time.sleep(1)
                self.add_log('ai分析文案，已经为视频生成字幕配音即标签')
                QApplication.processEvents()

                # 生成标题、小标题以及字幕的ass文件-----------------------------------------------------------

                for i in range(video_text_part_num):

                    srt_file_name = f"temp_subtitle{i}.srt"

                    audio_file_name = f"temp_final_audio{i}.mp3"

                    # 原字幕文件
                    part_subtitle_url = os.path.join(video_tamp_path, srt_file_name)

                    # ass字幕文件
                    output_path = part_subtitle_url.replace('.srt', '.ass')

                    # 标题字幕文件
                    output_title_path = part_subtitle_url.replace('.srt', '_title.ass')

                    # 音频文件
                    output_audio_path = os.path.join(video_tamp_path, audio_file_name)

                    # 转换成ass
                    convert_srt_to_ass(part_subtitle_url, output_path, self.all_setting_dict['srt_set'])

                    # # 旅游景点介绍类
                    # if i == 0 or i == video_text_part_num - 1:
                    #     remove_all_dialogue_text(output_path)
                    #
                    # if i != 0 and i != video_text_part_num - 1 and i != video_text_part_num - 2:
                    #     remove_dialogue_text(output_path)

                    if i == 0 and len(video_title) <= 20:
                        remove_dialogue_text(output_path)

                    # if i == video_text_part_num - 1:
                    #     remove_all_dialogue_text(output_path)

                    if i != video_text_part_num - 1 and i != 0:#and i != video_text_part_num - 2
                        remove_dialogue_text(output_path)

                    # 转换完成后 记录ass字幕位置
                    part_srt_ass_list.append(output_path)

                    # 记录音频位置
                    part_audio_list.append(output_audio_path)

                    # 创建标题ass，包括大标题和小标题
                    if i == 0 and len(video_title) <= 20:
                        self.pic_time = create_title(self.all_setting_dict, '1',
                                                     self.screenComboBox.currentIndex(),
                                                     video_title, output_title_path, part_subtitle_url)
                    elif i == 0 and len(video_title) > 20:
                        self.pic_time = 0.8

                    elif i != video_text_part_num - 1 and i != 0:#and i != video_text_part_num - 2
                        part_title = label_text[i].split(',')[0]
                        create_title(self.all_setting_dict, '2', self.screenComboBox.currentIndex(),
                                     part_title, output_title_path,
                                     part_subtitle_url)

                    if i != video_text_part_num - 1 :#and i != video_text_part_num - 2
                        part_title_ass_list.append(output_title_path)

                    self.add_log('视频样式字幕已生成')
                    QApplication.processEvents()

                    # 匹配视频素材-----------------------------------------------------------
                    # 视频片段标签
                    part_video_tags = label_text[i].split(',')

                    # 片段配音
                    part_audio_url = output_audio_path

                    # 配音时长
                    audio_length = get_audio_length(part_audio_url)

                    video_path = ''

                    # if i == video_text_part_num - 1:
                    #     video_path = self.all_setting_dict['end_video']['end_video_path']
                    #     if os.path.exists(video_path):
                    #         part_video_list.append(video_path)
                    # else:
                    # 匹配视频重复
                    unSuccessVideoLabel = str(timestamp) + '_videoLabel.xlsx'
                    notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                    notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessVideoLabel)
                    if i == 0:
                        # 片头随机匹配视频封面素材
                        self.add_log('正在为视频匹配封面素材')
                        QApplication.processEvents()
                        # cover_time = 0
                        zm_times = parse_srt_num_time(part_subtitle_url)
                        zm_num = len(zm_times)

                        cover_video_path_list = []
                        cover_video_id_list = []
                        # 特殊标签处理
                        title_keyword_list = ai_analyse_title_special_tag(video_title, video_text)
                        if len(title_keyword_list) <= 0:
                            #  ai分析标题获取其关键词
                            title_keyword_list = ai_analyse_title_usual_tag(video_title, video_text)
                            self.add_log('ai分析标题获取其关键词:' + ','.join(title_keyword_list))
                            QApplication.processEvents()
                        if len(title_keyword_list) <= 0:
                            #  标题获取其分词
                            title_keyword_list = title_keyword(video_title)
                            self.add_log('标题获取其分词' + ','.join(title_keyword_list))
                            QApplication.processEvents()
                        for zm_i in range(zm_num):
                            try:
                                # 智能封面选择：收集所有关键词候选再随机选择
                                # title_keyword_list = title_keyword(video_title)
                                ftp_cover_video_id = get_cover_video_collect_all(title_keyword_list, '普通素材')
                                if ftp_cover_video_id in cover_video_id_list:
                                    ftp_cover_video_id = get_random_cover_video_by_cate('普通素材')
                                video_path = download_cover_video(ftp_cover_video_id)
                                cut_video_path = cut_video_by_audio_length(video_path, ftp_cover_video_id,
                                                                           math.ceil(zm_times[zm_i]))
                                if os.path.exists(cut_video_path):
                                    cover_video_id_list.append(ftp_cover_video_id)
                                    cover_video_path_list.append(cut_video_path)
                            except Exception as e:
                                self.add_log(f'封面素材处理失败：{e}')
                                break
                        if len(cover_video_path_list) < zm_num:
                            failure_reason = get_last_material_download_error() or '封面素材未能完成下载或裁剪'
                            self.add_log(f'封面素材处理失败：{failure_reason}，退出合成')
                            QApplication.processEvents()
                            return

                        # 音频时长截取视频内容
                        time.sleep(1)
                        merge_video_path = merge_videos(cover_video_path_list,
                                                        '_'.join(map(str, cover_video_id_list)))

                        if os.path.exists(merge_video_path):
                            self.add_log(f'正在匹配素材，已经为视频匹配了{len(part_video_list) + 1}个素材')
                            QApplication.processEvents()

                            part_video_list.append(merge_video_path)
                        else:
                            self.add_log(f'下载合并视频素材失败')
                            QApplication.processEvents()
                            return
                    # 片尾随机匹配视频脚本中某个关键字的景点视频
                    elif i == video_text_part_num - 1:
                        self.add_log('正在为视频匹配片尾素材')
                        QApplication.processEvents()
                        sights_word_key = label_text[random.randint(1, video_text_part_num - 3)].split(',')[0]
                        ftp_videos = get_videos_by_keyword_1(sights_word_key, self.screenComboBox.currentIndex()
                                                             , self.locationlineEdit.text().strip(), audio_length, 10)
                        sights_word_key = re.sub(r'[^\w\s]', '', sights_word_key)
                        ftp_video_ids = [video['id'] for video in ftp_videos]
                        if len(ftp_videos) > 0:
                            video_id = random.choice(ftp_video_ids)
                            video_path = download_cn_video(video_id, self.screenComboBox.currentIndex())
                            # 音频时长截取视频内容
                            cut_video_path = cut_video_by_audio_length(video_path, video_id, audio_length)
                            if os.path.exists(cut_video_path):
                                self.add_log(f'正在匹配素材，已经为视频匹配了{len(part_video_list) + 1}个素材')
                                QApplication.processEvents()

                                part_video_list.append(cut_video_path)
                            else:
                                self.add_log(f'下载素材失败')
                                QApplication.processEvents()
                    else:
                        self.add_log('正在为视频匹配素材')
                        QApplication.processEvents()
                        # 普通片段匹配视频
                        while True:
                            ftp_video_List = []
                            # 地区景区匹配到的id
                            location_id_list = []
                            for n, tag in enumerate(part_video_tags):
                                if len(location_id_list) == 0 and n == 0:
                                    # 去除tag中所有标点符号
                                    tag = re.sub(r'[^\w\s]', '', tag)

                                    # 尝试关键字匹配视频，未匹配上Ai处理更换同义关键字再进行匹配
                                    ftp_videos = get_videos_by_keyword_1(tag, self.screenComboBox.currentIndex(),
                                                                         self.locationlineEdit.text().strip(),
                                                                         audio_length, 10)

                                    synonyms_list = []

                                    if len(ftp_videos) <= 0:
                                        print('缺少该关键字的素材')
                                        # part_video_tags.append(str(audio_length))
                                        # 记入未匹配的文案和视频标签

                                        lost_video_param = {
                                            'title': part_video_tags[0],
                                            'firstTags': '_'.join(synonyms_list) + '_'.join(part_video_tags),
                                            'secondTags': '',
                                            'videoLength': audio_length,
                                            'screen': self.screenComboBox.currentIndex(),
                                            'accountName': account_name,
                                            'titleType': '2'
                                        }
                                        # 将缺少的视频信息记入库中
                                        add_lost_cn_video_record(lost_video_param)

                                        # 将缺少的视频信息记入表中
                                        write_arrays_to_excel(notSuccess_label_folder_path, part_video_tags)
                                        break

                                    for video in ftp_videos:
                                        location_id_list.append(video['id'])

                                elif len(location_id_list) > 0:
                                    ftp_videos = get_videos_by_keyword(tag, self.screenComboBox.currentIndex(),
                                                                       self.locationlineEdit.text().strip(),
                                                                       location_id_list, audio_length)
                                else:
                                    ftp_videos = []

                                # 提取视频ID列表
                                if len(ftp_videos) > 0:
                                    ftp_ideo_ids = [video['id'] for video in ftp_videos]
                                    if len(ftp_ideo_ids) <= 0:
                                        continue
                                    ftp_video_List.append(ftp_ideo_ids)

                            # 没有素材退出匹配
                            if len(ftp_video_List) <= 0:
                                print('缺少该素材，退出合成')
                                self.add_log(f'缺少该素材，退出合成')
                                QApplication.processEvents()
                                return

                            if len(ftp_video_List) == 1:
                                video_id = random.choice(ftp_video_List[0])
                            else:
                                video_id = count_and_sort(ftp_video_List)

                            try:
                                video_path = download_cn_video(video_id, self.screenComboBox.currentIndex())

                                time.sleep(1)

                                # 音频时长截取视频内容
                                cut_video_path = cut_video_by_audio_length(video_path, video_id, audio_length)

                                logging.debug(f'这个下载的视频{video_path}的')

                                if os.path.exists(cut_video_path):
                                    logging.debug(f'存在下载的视频{cut_video_path}')
                                    self.add_log(
                                        f'正在匹配素材，已经为视频匹配了{len(part_video_list)}个素材')
                                    QApplication.processEvents()

                                    part_video_list.append(cut_video_path)
                                    break
                                else:
                                    self.add_log(f'下载素材失败')
                                    QApplication.processEvents()
                                    break
                            except Exception as e:
                                logging.debug(f'这个下载的视频{video_path}的错误{str(e)}')
                                break

                                # try_num += 1

                # 如果素材数量和文案一样，就进行合成 未处理成功
                video_file_path = ''
                if len(part_video_list) == video_text_part_num:
                    transitionSetting = {
                        'transitionNum': 0,
                        'transitionTime': 0
                    }
                    saveVideoPath = out_dir_path

                    video_id_path_name = 'video_id.xlsx'
                    # 任务文件输出路径
                    video_id_excel_file_path = os.path.join(saveVideoPath, video_id_path_name)

                    # 记录每个视频匹配的素材
                    write_arrays_to_excel(video_id_excel_file_path, [video_title] + part_video_list)

                    # 输出路径
                    video_name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', video_title) + '_0.mp4'

                    video_file_path = os.path.join(saveVideoPath, video_name)

                    excel_file_path_name = '1.xls'
                    # 任务文件输出路径
                    excel_file_path = os.path.join(saveVideoPath, excel_file_path_name)

                    composite_worker = CompositeVideo(part_video_list, part_audio_list, part_srt_ass_list,
                                                      part_title_ass_list, video_file_path,
                                                      transitionSetting, self.pic_time)

                    self.add_log('正在合成一个视频。。。')
                    QApplication.processEvents()

                    self.thread_pool.start(composite_worker)
                    # 创建一个事件循环
                    composite_worker.signals.finished.connect(self.on_success_occurred)
                    composite_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()
                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'合成一个视频失败')
                        continue

                    self.add_log('已经合成一个视频，接下来进行后期处理。')
                    QApplication.processEvents()

                    if not os.path.exists(video_file_path):
                        self.add_log('没有已经合成一个视频，跳过。')
                        QApplication.processEvents()
                        continue

                    # 匹配添加音乐
                    parent_dir = os.getcwd()
                    # 构造同级的缓存文件夹路径
                    cache_music_dir_path = os.path.join(parent_dir, 'cacheMusic')
                    # 获取文件夹中的所有MP3文件
                    mp3_files = [f for f in os.listdir(cache_music_dir_path) if
                                 f.endswith('.mp3') or f.endswith('.MP3')]

                    # 如果文件夹中有MP3文件，则随机选择一个
                    if mp3_files:
                        random_mp3_file = random.choice(mp3_files)
                        random_mp3_file_path = os.path.join(cache_music_dir_path, random_mp3_file)
                        print(f"随机选择的MP3文件路径为：{random_mp3_file_path}")
                    else:
                        print("文件夹中没有找到MP3文件,缺少音乐。")
                        break

                    # 加载音频文件
                    # audio = AudioSegment.from_file(mp4_files)

                    # 获取音乐音频的音量（响度）
                    # music_volume = audio.dBFS  # 返回音频的响度，单位为分贝
                    # mb_db = 20.0
                    bgAudioVolume = 40
                    output_bgm_video_path = video_file_path.replace('_0.mp4', '_1.mp4')
                    addMusicWorker = AddMusicWorker(video_file_path, random_mp3_file_path, 100, bgAudioVolume,
                                                    output_bgm_video_path)

                    self.thread_pool.start(addMusicWorker)
                    # 创建一个事件循环
                    addMusicWorker.signals.finished.connect(self.on_success_occurred)
                    addMusicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加音乐失败')
                        continue

                    self.add_log('后期处理,已添加音乐。')
                    QApplication.processEvents()

                    # 添加水印
                    watermark_location_examples = [['50', '50'], ['main_w-overlay_w-100', '50'],
                                                   ['50', 'main_h-overlay_h-50'],
                                                   ['main_w-overlay_w-50', 'main_h-overlay_h-50'],
                                                   ['(main_w-overlay_w)/2', '(main_h-overlay_h)/2'],
                                                   ['(main_w-overlay_w)/2', '50'],
                                                   ['(main_w-overlay_w)/2', 'main_h-overlay_h-100']]

                    watermark_setting = {
                        'watermark_location': watermark_location_examples[
                            self.all_setting_dict['water_set']['position']],
                        'zoom_size': self.all_setting_dict['water_set']['zoom'],
                        'pic_alpha': self.all_setting_dict['water_set']['alpha']
                    }
                    final_output_path = output_bgm_video_path.replace('_1.mp4', '.mp4')
                    add_text_watermark_worker = AddWatermarkWorker(output_bgm_video_path, final_output_path,
                                                                   watermark_setting, 2,
                                                                   self.all_setting_dict['water_set']['filePath'])
                    self.thread_pool.start(add_text_watermark_worker)
                    # 创建一个事件循环
                    add_text_watermark_worker.signals.finished.connect(self.on_success_occurred)
                    add_text_watermark_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加水印失败')
                        continue

                    self.add_log('后期处理,已添加水印。')
                    QApplication.processEvents()

                    # 视频压缩
                    temp_compressed_path = final_output_path.replace('.mp4', '_temp_compressed.mp4')
                    compress_video_worker = CompressVideoWorker(final_output_path, temp_compressed_path)

                    self.thread_pool.start(compress_video_worker)
                    compress_video_worker.signals.finished.connect(self.on_success_occurred)
                    compress_video_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        self.add_log('视频压缩失败，使用原始文件')
                        QApplication.processEvents()
                    else:
                        self.add_log('视频压缩完成')
                        QApplication.processEvents()

                    # 移除中间视频
                    if os.path.exists(video_file_path):
                        os.remove(video_file_path)

                    if os.path.exists(output_bgm_video_path):
                        os.remove(output_bgm_video_path)

                    data_dict = {
                        "标题": video_title.replace('|', ''),
                        "标签": video_tag,
                        "文件路径": final_output_path.replace('/', '\\'),
                        "描述": ','.join(video_text),
                        "封面路径": "",
                        "图片集合": "",
                        "关联商品": "",
                        "分区分类": "旅游",
                        "备注": ""
                    }

                    write_to_old_excel(excel_file_path, data_dict)

                    # 上传任务信息
                    # 账号姓名
                    # account_name = self.accountNameLineEdit.text()
                    # 账号account
                    account_result = self.get_upload_accounts(account_name)

                    # 上传任务
                    if len(account_result) > 0:
                        for (account, mac) in account_result:
                            print(account)
                            task_param = {
                                'name': account_name,
                                'account': account,
                                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'title': data_dict.get('标题'),
                                'mac': mac,
                                'tag': data_dict.get('标签'),
                                'path': data_dict.get('文件路径'),
                                'describe': data_dict.get('描述'),
                                'classify': data_dict.get('分区分类'),
                                'task_type': 2,
                            }
                            add_user_task(task_param)
                            self.add_log(f'{account_name}{account}上传视频任务:{final_output_path}')
                            QApplication.processEvents()

                    self.add_log(f'生成完成一个视频:{final_output_path}')
                    QApplication.processEvents()

                else:
                    logging.debug(f'匹配的视频与文案数量不一致')
                    print('匹配的视频与文案数量不一致')
                    unSuccessCopy = str(timestamp) + '_copy.xlsx'
                    unSuccessLabel = str(timestamp) + '_label.xlsx'
                    notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                    notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
                    notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
                    # 记入未匹配的文案和视频标签
                    write_arrays_to_excel(notSuccess_copy_folder_path, video_title_text[0:-1])
                    write_arrays_to_excel(notSuccess_label_folder_path, label_text[0:-1])
                    self.add_log('跳过一个脚本文案，可能是没有匹配到视频，已记录')
                    QApplication.processEvents()

            # 删除cut video缓存
            clean_cut_cache()
            clean_cache()
            copy_start_num += 1
            label_start_num += 1

        current_directory = os.getcwd()
        unSuccessCopy = str(timestamp) + '_copy.xlsx'
        unSuccessLabel = str(timestamp) + '_label.xlsx'
        notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
        notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
        notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
        if os.path.exists(notSuccess_copy_folder_path) and os.path.exists(notSuccess_label_folder_path):
            try:
                self.add_log('有视频记录没有生成完毕，可补充素材后点击继续生成')
                QApplication.processEvents()
                self.copyFileLabel.setText(notSuccess_copy_folder_path)
                self.labelFilelabel.setText(notSuccess_label_folder_path)

                # 展示缺少的标签
                unSuccessVideoLabel = str(timestamp) + '_videoLabel.xlsx'
                notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessVideoLabel)
                # 读取整个工作表（默认第一张）
                df = _read_excel(notSuccess_label_folder_path)
                # 设置表格的行列数
                self.lostVideoTableWidget.setRowCount(df.shape[0])
                self.lostVideoTableWidget.setColumnCount(df.shape[1])

                # 获取水平表头视图
                horizontal_header = self.lostVideoTableWidget.horizontalHeader()

                # 设置表头样式表（背景色、文字颜色等）
                horizontal_header.setStyleSheet("""
                                        QHeaderView::section {
                                            background-color: rgb(56, 56, 56);
                                            color: white;                     
                                            ont-weight: bold;          /* 文字加粗 */
                                            border-right: 1px solid #ddd; /* 右侧边框 */
                                            text-align: center;         /* 文字居中 */
                                        }
                                    """)
                vertical_header = self.lostVideoTableWidget.verticalHeader()

                vertical_header.setStyleSheet("""
                                        QHeaderView::section {
                                            background-color: rgb(56, 56, 56);
                                            color: white;                    
                                            font-weight: bold;          /* 文字加粗 */
                                            border-right: 1px solid #ddd; /* 右侧边框 */
                                            text-align: center;         /* 文字居中 */
                                        }
                                    """)

                # 填充数据
                for row in range(df.shape[0]):
                    for col in range(df.shape[1]):
                        item = QTableWidgetItem(str(df.iat[row, col]))
                        self.lostVideoTableWidget.setItem(row, col, item)
                self.lostVideoTableWidget.resizeColumnsToContents()
            except Exception as e:
                print(f'展示缺少的标签错误{str(e)}')
                pass
        else:
            self.add_log('所有视频记录已经生成完毕，无记录可生成')
            QApplication.processEvents()

    # 历史视频类
    def compositeGreenScreenVideo(self, copy_file, label_file, out_dir_path, account_name):
        self.add_log('开始合成根据文案合成视频')
        QApplication.processEvents()

        # 时间
        timestamp = int(time.time())

        if self.randomVideoModelCheckBox.isChecked():
            model_result = get_random_video_model()
            model_set_dict = json.loads(model_result['model_set'])
            self.all_setting_dict['title_set'] = model_set_dict['title_set']
            self.all_setting_dict['part_title_set'] = model_set_dict['part_title_set']
            self.all_setting_dict['srt_set'] = model_set_dict['srt_set']
            self.all_setting_dict['voice_set'] = model_set_dict['voice_set']
            self.all_setting_dict['part_title_part_0_set'] = model_set_dict['part_title_part_0_set']
            self.all_setting_dict['part_title_part_1_set'] = model_set_dict['part_title_part_1_set']
            self.all_setting_dict['part_title_part_2_set'] = model_set_dict['part_title_part_2_set']
            self.all_setting_dict['part_title_part_3_set'] = model_set_dict['part_title_part_3_set']
            self.all_setting_dict['part_title_part_4_set'] = model_set_dict['part_title_part_4_set']
            self.all_setting_dict['part_title_part_5_set'] = model_set_dict['part_title_part_5_set']
        else:
            self.all_setting_dict = read_dict_from_txt('setting.txt')

        if not os.path.exists(self.all_setting_dict['end_video']['end_video_path']):
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                                         QMessageBox QLabel {
                                         background-color: rgb(22, 23, 25);
                                         color: rgb(255, 255, 255);
                                        }
                                        QMessageBox {
                                        background-color: rgb(22, 23, 25);
                                        color: rgb(255, 255, 255);
                                        }
                                    """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"请选择视频添加的片尾")
            msg_box.exec()
            return

        # 删除video缓存
        clean_cut_cache()
        clean_cache()

        # copy 起始行
        copy_start_num = get_first_data_row(copy_file)

        # label 起始行
        label_start_num = get_first_data_row(label_file)

        self.add_log(f'读取视频文案,文案文件路径是{str(copy_file)},标签文件路径是{str(label_file)}')

        if copy_start_num == -1 or label_start_num == -1 or copy_start_num is None or label_start_num is None:
            self.add_log('文案文件或者标签文件没有数据可读，结束合成视频')
            QApplication.processEvents()
            return

        # tts 速度
        speed_value = str(self.all_setting_dict['voice_set']['spd_0'])
        if not str(speed_value).startswith('-'):
            speed_value = '+' + speed_value
        speed_value = speed_value + '%'

        # 获取音频设置
        audio_setting = {
            'api_type': self.all_setting_dict['voice_set']['api_type'],
            'audio_role': self.audio_role_list[self.all_setting_dict['voice_set']['role_0']],
            'speed_value': speed_value,
            'volume_value': self.all_setting_dict['voice_set']['vol_0']
        }

        if self.all_setting_dict['voice_set']['api_type'] == 1:
            # 获取音频设置
            audio_setting = {
                'api_type': self.all_setting_dict['voice_set']['api_type'],
                'audio_role': int(
                    self.audio_bd_role_list[self.all_setting_dict['voice_set']['role_1']].split(':')[1]),
                'speed_value': self.all_setting_dict['voice_set']['spd_1'],
                'volume_value': self.all_setting_dict['voice_set']['vol_1'],
                'tone_value': self.all_setting_dict['voice_set']['pit_1']
            }

        while True:

            # 获取视频文案
            video_title_text = get_row_data(copy_file, copy_start_num)

            self.add_log('读取视频文案')
            QApplication.processEvents()

            # video_title_text.append('记得点赞关注评论')

            # 获取视频标签
            label_text = get_row_data(label_file, label_start_num)

            self.add_log(f'读取视频标签，{"&&".join(video_title_text)}，{"&&".join(label_text)}')
            QApplication.processEvents()

            if len(video_title_text) < 3:
                self.add_log('全部生成完成')
                QApplication.processEvents()
                # QMessageBox.information(self, "完成", f"所有视频已生成处理完成，已生成任务列表")
                break

            # label_text.append('点赞,关注,评论')

            # 标题
            video_title = video_title_text[0].strip()

            # 标签
            video_tag = video_title_text[1].strip()

            # 文案
            video_text = video_title_text[2:]

            # 文案段数
            video_text_part_num = len(video_text)
            if video_text_part_num <= 2:
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                label_start_num += 1
                logging.debug(f'合成一个视频失败')
                continue

            # 视频处理缓存文件夹
            tamp_folder_name = 'tempConcateVideo'
            current_directory = os.getcwd()
            tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
            video_tamp_path_name = 'video_cache_file'
            video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)

            if len(video_text) > 0:

                # 素材缓存路径
                part_video_list = []

                # 字幕缓存路径
                part_srt_ass_list = []

                # 音频缓存路径
                part_audio_list = []

                # 标题缓存路径
                part_title_ass_list = []

                # 配音初始字幕生成-----------------------------------------------------------
                product_worker = SaWorker(video_text, audio_setting)
                self.thread_pool.start(product_worker)
                # 事件循环
                product_worker.signals.finished.connect(self.on_success_occurred)
                product_worker.signals.errorOccurred.connect(self.on_error_occurred)
                self.loop.exec()
                if self.error_flag:
                    # 删除cut video缓存
                    clean_cut_cache()
                    clean_cache()
                    copy_start_num += 1
                    label_start_num += 1
                    logging.debug(f'合成一个视频失败')
                    continue

                self.add_log('ai分析文案，已经为视频生成字幕配音即标签')
                QApplication.processEvents()

                # 生成标题、小标题以及字幕的ass文件-----------------------------------------------------------

                # 视频不重复记录
                video_id_list = []
                pic_title_ass = ''
                pic_title_video = ''
                # 尝试匹配的过程并记录所有同义的词语
                synonyms_list = []
                for i in range(video_text_part_num):

                    srt_file_name = f"temp_subtitle{i}.srt"

                    audio_file_name = f"temp_final_audio{i}.mp3"

                    # 原字幕文件
                    part_subtitle_url = os.path.join(video_tamp_path, srt_file_name)

                    # ass字幕文件
                    output_path = part_subtitle_url.replace('.srt', '.ass')

                    # 标题字幕文件
                    output_title_path = part_subtitle_url.replace('.srt', '_title.ass')

                    # 音频文件
                    output_audio_path = os.path.join(video_tamp_path, audio_file_name)

                    # 转换成ass
                    convert_srt_to_ass(part_subtitle_url, output_path, self.all_setting_dict['srt_set'])

                    # if i == 0:
                    #     remove_dialogue_text(output_path)

                    # # 通用类需要去除开头和片尾标题
                    # if i == video_text_part_num - 1:
                    #     remove_all_dialogue_text(output_path)

                    # 转换完成后 记录ass字幕位置
                    part_srt_ass_list.append(output_path)

                    # 记录音频位置
                    part_audio_list.append(output_audio_path)

                    # # 创建标题ass，通用只有大标题
                    # if i == 0:
                    #     self.pic_time = create_title(self.all_setting_dict, '1',
                    #                                  self.screenComboBox.currentIndex(),
                    #                                  video_title, output_title_path, part_subtitle_url)
                    #
                    #     part_title_ass_list.append(output_title_path)

                    if i == 0:
                        # 封面帧
                        output_title_path = part_subtitle_url.replace('.srt', '_pic_title.ass')
                        self.pic_time = create_tagging_title(self.all_setting_dict, '1',
                                                             self.screenComboBox.currentIndex(),
                                                             video_title, output_title_path, part_subtitle_url,
                                                             label_text[1].split(',')[0])

                        if os.path.exists(output_title_path):
                            pic_title_ass = output_title_path

                    self.add_log('视频样式字幕已生成')
                    QApplication.processEvents()

                    # 匹配视频素材-----------------------------------------------------------
                    # 视频片段标签
                    part_video_tags = label_text[i].split(',')

                    # 片段配音
                    part_audio_url = output_audio_path

                    # 配音时长
                    audio_length = get_audio_length(part_audio_url)

                    # if i == video_text_part_num - 1:
                    #     video_path = self.all_setting_dict['end_video']['end_video_path']
                    #     if os.path.exists(video_path):
                    #         part_video_list.append(video_path)
                    # else:
                    # 匹配视频
                    unSuccessVideoLabel = str(timestamp) + '_videoLabel.xlsx'
                    notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                    notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessVideoLabel)

                    while True:
                        ftp_video_List = []
                        # 地区景区匹配到的id
                        location_id_list = []
                        for n, tag in enumerate(part_video_tags):
                            if len(location_id_list) == 0 and n == 0:
                                ftp_videos = get_videos_by_keyword_1(tag,
                                                                     self.screenComboBox.currentIndex(),
                                                                     self.locationlineEdit.text().strip(),
                                                                     audio_length, 20, "普通素材")

                                # 重试关键字匹配
                                n = 0
                                while len(ftp_videos) <= 0 and n < 4:
                                    time.sleep(5)
                                    ftp_videos = get_videos_by_keyword_1(tag,
                                                                         self.screenComboBox.currentIndex(),
                                                                         self.locationlineEdit.text().strip(),
                                                                         audio_length, 20, "普通素材")
                                    n += 1

                                if len(ftp_videos) <= 0:
                                    print('缺少该关键字的素材')
                                    # 记入未匹配的文案和视频标签

                                    lost_video_param = {
                                        'title': part_video_tags[0],
                                        'firstTags': '_'.join(synonyms_list) + '_'.join(part_video_tags),
                                        'secondTags': '',
                                        'videoLength': audio_length,
                                        'screen': self.screenComboBox.currentIndex(),
                                        'accountName': account_name,
                                        'titleType': '8'
                                    }
                                    # 将缺少的视频信息记入库中
                                    add_lost_cn_video_record(lost_video_param)

                                    # 将缺少的视频信息记入表中
                                    write_arrays_to_excel(notSuccess_label_folder_path, part_video_tags)
                                    break

                                for video in ftp_videos:
                                    location_id_list.append(video['id'])

                        # 没有素材退出匹配
                        if len(location_id_list) <= 0:
                            print('缺少该素材，退出合成')
                            self.add_log(f'缺少该素材，退出合成')
                            QApplication.processEvents()
                            return

                        video_id = random.choice(location_id_list)

                        try_time = 0
                        while video_id in video_id_list and try_time < 6:
                            video_id = random.choice(location_id_list)
                            try_time += 1

                        video_id_list.append(video_id)

                        # 当前重复率判断，并记录信息
                        if enough_unique(video_id_list, 0.6) is False:
                            logging.debug(f'当前素材重复率过高，重新匹配')
                            print('当前素材重复率过高，重新匹配')
                            lost_video_param = {
                                'title': part_video_tags[0],
                                'firstTags': '_'.join(synonyms_list) + '_' + '_'.join(part_video_tags),
                                'secondTags': '',
                                'videoLength': audio_length,
                                'screen': self.screenComboBox.currentIndex(),
                                'accountName': account_name,
                                'titleType': '8'
                            }
                            # 将缺少的视频信息记入库中
                            add_lost_cn_video_record(lost_video_param)

                        video_path = download_cn_video(video_id, self.screenComboBox.currentIndex())

                        time.sleep(1)
                        if video_path is not None:
                            if os.path.exists(video_path):
                                # 音频时长截取视频内容
                                cut_video_path = cut_video_by_audio_length(video_path, video_id,
                                                                           audio_length)

                                logging.debug(f'这个下载的视频{video_path}的')

                                if os.path.exists(cut_video_path):
                                    logging.debug(f'存在下载的视频{cut_video_path}')
                                    self.add_log(
                                        f'正在匹配素材，已经为视频匹配了{len(part_video_list) + 1}个素材')
                                    QApplication.processEvents()
                                    part_video_list.append(cut_video_path)
                                    if pic_title_video == '':
                                        pic_title_video = cut_video_path
                                    break
                                else:
                                    self.add_log(f'下载素材失败')
                                    QApplication.processEvents()
                                    break
                            else:
                                self.add_log(f'下载素材失败')
                                QApplication.processEvents()
                                break

                        else:
                            self.add_log(f'匹配下载素材失败')
                            QApplication.processEvents()
                            break

                # 重复率判断
                if enough_unique(video_id_list, 0.6) is False:
                    self.add_log('素材重复率过高，跳过该视频合成')
                    print('素材重复率过高，跳过该视频合成')
                    QApplication.processEvents()
                    # 删除cut video缓存
                    clean_cut_cache()
                    clean_cache()
                    copy_start_num += 1
                    label_start_num += 1
                    logging.debug(f'合成一个视频失败')
                    continue

                # 如果素材数量和文案一样，就进行合成 未处理成功
                if len(part_video_list) == video_text_part_num:
                    transitionSetting = {
                        'transitionNum': 0,
                        'transitionTime': 0
                    }
                    saveVideoPath = out_dir_path

                    video_id_path_name = 'video_id.xlsx'
                    # 任务文件输出路径
                    video_id_excel_file_path = os.path.join(saveVideoPath, video_id_path_name)

                    # 记录每个视频匹配的素材
                    write_arrays_to_excel(video_id_excel_file_path, [video_title] + part_video_list)

                    # 输出路径
                    video_name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', video_title) + '_0.mp4'

                    video_file_path = os.path.join(saveVideoPath, video_name)

                    excel_file_path_name = '1.xls'
                    # 任务文件输出路径
                    excel_file_path = os.path.join(saveVideoPath, excel_file_path_name)

                    composite_worker = CompositeVideo(part_video_list, part_audio_list, part_srt_ass_list,
                                                      part_title_ass_list, video_file_path,
                                                      transitionSetting, self.pic_time)

                    self.add_log(f'正在合成拼接一个视频。。。')
                    QApplication.processEvents()

                    self.thread_pool.start(composite_worker)
                    # 创建一个事件循环
                    composite_worker.signals.finished.connect(self.on_success_occurred)
                    composite_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()
                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'合成一个视频失败')
                        continue

                    self.add_log(f'已经合成一个视频，接下来进行后期处理。')
                    QApplication.processEvents()

                    if not os.path.exists(video_file_path):
                        self.add_log('没有已经合成一个视频，跳过。')
                        QApplication.processEvents()
                        continue

                    # 匹配添加音乐
                    parent_dir = os.getcwd()
                    # 构造同级的缓存文件夹路径
                    cache_music_dir_path = os.path.join(parent_dir, 'cacheMusic1')
                    # 获取文件夹中的所有MP3文件
                    mp3_files = [f for f in os.listdir(cache_music_dir_path) if
                                 f.endswith('.mp3') or f.endswith('.MP3')]

                    # 如果文件夹中有MP3文件，则随机选择一个
                    if mp3_files:
                        random_mp3_file = random.choice(mp3_files)
                        random_mp3_file_path = os.path.join(cache_music_dir_path, random_mp3_file)
                        print(f"随机选择的MP3文件路径为：{random_mp3_file_path}")
                    else:
                        print("文件夹中没有找到MP3文件,缺少音乐。")
                        break

                    bgAudioVolume = 40
                    output_bgm_video_path = video_file_path.replace('_0.mp4', '_1.mp4')
                    addMusicWorker = AddMusicWorker(video_file_path, random_mp3_file_path, 100, bgAudioVolume,
                                                    output_bgm_video_path)

                    self.thread_pool.start(addMusicWorker)
                    # 创建一个事件循环
                    addMusicWorker.signals.finished.connect(self.on_success_occurred)
                    addMusicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加音乐失败')
                        continue

                    self.add_log('后期处理,已添加音乐。')
                    QApplication.processEvents()

                    # 添加人物图片
                    Person_output_path = output_bgm_video_path.replace('_1.mp4', '_2.mp4')
                    
                    # 获取人物图片ID（从数据库查询或使用默认值）
                    try:
                        # 获取人物图片ID（这里可以根据标题、标签等条件查询）
                        # 示例：根据标题获取人物ID，或随机选择
                        person_id = 1  # 默认使用ID为1的人物
                        # 如果有get_person_id函数，可以这样使用：
                        person_result = get_person_id(video_title)
                        if person_result:
                            person_id = person_result[0]
                        
                        # 优先使用已同步的本地人物库，本地没有时才尝试 FTP。
                        person_pic_path = get_person_pic_path(person_id)
                        if not person_pic_path:
                            person_pic_path = download_person_pic(person_id)
                        
                        if person_pic_path and os.path.exists(person_pic_path):
                            self.add_log(f'找到人物图片: {person_pic_path}')
                            QApplication.processEvents()
                            
                            # 创建并启动人物图片添加Worker
                            add_person_pic_worker = AddPersonPicWorker(
                                input_video_path=output_bgm_video_path,
                                person_pic_path=person_pic_path,
                                output_video_path=Person_output_path,
                                position="top-left"
                            )
                            
                            self.thread_pool.start(add_person_pic_worker)
                            add_person_pic_worker.signals.finished.connect(self.on_success_occurred)
                            add_person_pic_worker.signals.errorOccurred.connect(self.on_error_occurred)
                            self.loop.exec()
                        else:
                            self.add_log('未找到人物图片，跳过可选的人物叠加')
                            Person_output_path = output_bgm_video_path
                            
                    except Exception as e:
                        self.add_log(f'添加人物图片失败: {str(e)}')
                        QApplication.processEvents()
                        # 使用原视频继续
                        Person_output_path = output_bgm_video_path

                    # 添加水印
                    watermark_location_examples = [['50', '50'], ['main_w-overlay_w-100', '50'],
                                                   ['50', 'main_h-overlay_h-50'],
                                                   ['main_w-overlay_w-50', 'main_h-overlay_h-50'],
                                                   ['(main_w-overlay_w)/2', '(main_h-overlay_h)/2'],
                                                   ['(main_w-overlay_w)/2', '50'],
                                                   ['(main_w-overlay_w)/2', 'main_h-overlay_h-100']]

                    watermark_setting = {
                        'watermark_location': watermark_location_examples[
                            self.all_setting_dict['water_set']['position']],
                        'zoom_size': self.all_setting_dict['water_set']['zoom'],
                        'pic_alpha': self.all_setting_dict['water_set']['alpha']
                    }
                    if Person_output_path.endswith('_2.mp4'):
                        watermark_output_path = Person_output_path.replace('_2.mp4', '_3.mp4')
                    else:
                        watermark_output_path = Person_output_path.replace('_1.mp4', '_3.mp4')
                    add_text_watermark_worker = AddWatermarkWorker(Person_output_path, watermark_output_path,
                                                                   watermark_setting, 2,
                                                                   self.all_setting_dict['water_set']['filePath'])
                    self.thread_pool.start(add_text_watermark_worker)
                    # 创建一个事件循环
                    add_text_watermark_worker.signals.finished.connect(self.on_success_occurred)
                    add_text_watermark_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加水印失败')
                        continue

                    self.add_log('后期处理,已添加水印。')
                    QApplication.processEvents()

                    # 视频压缩
                    temp_compressed_path = watermark_output_path.replace('_3.mp4', '_temp_compressed.mp4')
                    compress_video_worker = CompressVideoWorker(watermark_output_path, temp_compressed_path)

                    self.thread_pool.start(compress_video_worker)
                    compress_video_worker.signals.finished.connect(self.on_success_occurred)
                    compress_video_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        self.add_log('视频压缩失败，使用原始文件')
                        QApplication.processEvents()
                    else:
                        self.add_log('视频压缩完成')
                        QApplication.processEvents()

                    # 添加图片封面
                    final_output_path = watermark_output_path.replace('_3.mp4', '.mp4')
                    # 添加视频封面工作流
                    addPicWorker = AddPicWorker(watermark_output_path, pic_title_video, 'white.png', pic_title_ass,
                                                final_output_path)
                    self.thread_pool.start(addPicWorker)
                    addPicWorker.signals.finished.connect(self.on_success_occurred)
                    addPicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    # 移除中间视频
                    if os.path.exists(video_file_path):
                        os.remove(video_file_path)

                    if os.path.exists(watermark_output_path):
                        os.remove(watermark_output_path)

                    if os.path.exists(Person_output_path):
                        os.remove(Person_output_path)

                    if os.path.exists(output_bgm_video_path):
                        os.remove(output_bgm_video_path)

                    if os.path.exists(temp_compressed_path):
                        os.remove(temp_compressed_path)

                    data_dict = {
                        "标题": video_title.replace('|', ''),
                        "标签": video_tag,
                        "文件路径": final_output_path.replace('/', '\\'),
                        "描述": ','.join(video_text),
                        "封面路径": "",
                        "图片集合": "",
                        "关联商品": "",
                        "分区分类": "旅游",
                        "备注": ""
                    }

                    write_to_old_excel(excel_file_path, data_dict)

                    # 上传任务信息
                    # 账号姓名
                    # account_name = self.accountNameLineEdit.text()
                    # 账号account
                    account_result = self.get_upload_accounts(account_name)

                    # 上传任务
                    if len(account_result) > 0:
                        for (account, mac) in account_result:
                            print(account)
                            task_param = {
                                'name': account_name,
                                'account': account,
                                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'title': data_dict.get('标题'),
                                'mac': mac,
                                'tag': data_dict.get('标签'),
                                'path': data_dict.get('文件路径'),
                                'describe': data_dict.get('描述'),
                                'classify': data_dict.get('分区分类'),
                                'task_type': 8,
                            }
                            add_user_task(task_param)
                            self.add_log(f'{account_name}{account}上传视频任务:{final_output_path}')
                            QApplication.processEvents()

                    self.run_label.setText(f'生成完成一个视频:{final_output_path}')
                else:
                    logging.debug(f'匹配的视频与文案数量不一致')
                    print('匹配的视频与文案数量不一致')
                    unSuccessCopy = str(timestamp) + '_copy.xlsx'
                    unSuccessLabel = str(timestamp) + '_label.xlsx'
                    notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                    notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
                    notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
                    # 记入未匹配的文案和视频标签
                    write_arrays_to_excel(notSuccess_copy_folder_path, video_title_text[0:-1])
                    write_arrays_to_excel(notSuccess_label_folder_path, label_text[0:-1])
                    self.add_log(f'跳过一个脚本文案，可能是没有匹配到视频，已记录')
                    QApplication.processEvents()

            # 删除cut video缓存
            clean_cut_cache()
            clean_cache()
            copy_start_num += 1
            label_start_num += 1

        current_directory = os.getcwd()
        unSuccessCopy = str(timestamp) + '_copy.xlsx'
        unSuccessLabel = str(timestamp) + '_label.xlsx'
        notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
        notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
        notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
        if os.path.exists(notSuccess_copy_folder_path) and os.path.exists(notSuccess_label_folder_path):
            self.add_log('有视频记录没有生成完毕，可补充素材后点击继续生成')
            QApplication.processEvents()
            self.copyFileLabel.setText(notSuccess_copy_folder_path)
            self.labelFilelabel.setText(notSuccess_label_folder_path)
        else:
            self.add_log('所有视频记录已经生成完毕，无记录可生成')
            QApplication.processEvents()

    # 文字介绍类
    def compositeWordIntroVideo(self, copy_file, out_dir_path, account_name):

        self.add_log('开始合成根据文案合成视频')
        QApplication.processEvents()

        if not os.path.exists(self.all_setting_dict['end_video']['end_video_path']):
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                             QMessageBox QLabel {
                             background-color: rgb(22, 23, 25);
                             color: rgb(255, 255, 255);
                            }
                            QMessageBox {
                            background-color: rgb(22, 23, 25);
                            color: rgb(255, 255, 255);
                            }
                        """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"请选择视频添加的片尾")
            msg_box.exec()
            return

        # 删除video缓存
        clean_cut_cache()
        clean_cache()

        self.all_setting_dict = read_dict_from_txt('setting.txt')

        # copy 起始行
        copy_start_num = get_first_data_row(copy_file)

        self.add_log(f'读取视频文案,文案文件路径是{str(copy_file)}')

        parent_dir = os.getcwd()
        # 构造同级的缓存文件夹路径
        pic_infor_model_dir = os.path.join(parent_dir, 'pic_infor_model')
        # 确保图片模板文件夹存在
        if not os.path.exists(pic_infor_model_dir):
            os.makedirs(pic_infor_model_dir)

        while True:
            model_txt_path = random_txt_file_path(pic_infor_model_dir)
            if not os.path.exists(model_txt_path):
                model_txt_path = 'setting.txt'
            model_set_dict = read_dict_from_txt(model_txt_path)

            # 获取视频文案
            video_title_text = get_row_data(copy_file, copy_start_num)

            self.add_log('读取视频文案')
            QApplication.processEvents()

            if len(video_title_text) < 3:
                self.add_log('全部生成完成')
                QApplication.processEvents()
                break

            # 标题
            video_title = video_title_text[0].strip()

            # 标签
            video_tag = video_title_text[1].strip()

            # 文案
            video_text = video_title_text[2:]

            show_time = len(video_text) * 0.8

            # 文案段数
            video_text_part_num = len(video_text)
            if video_text_part_num <= 2:
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                if label_start_num:
                    label_start_num += 1
                logging.debug(f'合成一个视频失败')
                continue

            # 视频处理缓存文件夹
            tamp_folder_name = 'tempConcateVideo'
            current_directory = os.getcwd()
            tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
            video_tamp_path_name = 'video_cache_file'
            video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)

            # 生成标题字幕
            ass_events = ''
            ass_header = file_create_title_ass_header(model_set_dict['title_set'])
            title_part_text_list = video_title.split('|')
            # 定义常见符号的正则表达式模式
            # 使用正则表达式替换所有符号为空字符串
            title_pos_x = 190
            title_pos_y = 50
            part_num = len(title_part_text_list)
            for i, title_part_text in enumerate(title_part_text_list):
                if title_part_text == '':
                    continue
                start_time = 0
                end_time = 30
                # 标题特效添加
                # text = file_word_infor_title_apply_effects_to_text(title_part_text, pos_x, pos_y)
                text = file_word_infor_title_static_text(title_part_text, model_set_dict['title_set'], title_pos_x,
                                                         title_pos_y)
                ass_events += f"Dialogue: 0,{sec_to_ass(start_time)},{sec_to_ass(end_time)},Default,,0,0,0,,{text}" + '\n'
                # 换行间隔
                title_pos_y += 20
            # ASS文件内容
            ass_content = ass_header + "\n" + ass_events
            out_title_ass_path = os.path.join(video_tamp_path, 'wordIntroTitle.ass')
            with open(out_title_ass_path, "w", encoding="utf-8") as f:
                f.write(ass_content)

            # 生成内容逐行显示字幕
            ass_events = ''
            ass_header = file_create_title_ass_header(model_set_dict['part_title_set'])

            start_time = 0
            end_time = show_time
            ime_per_segment = float((end_time - 4) / len(video_text))

            random_number = random.randint(0, 3)
            numbers_0 = [
                "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.",
                "11.", "12.", "13.", "14.", "15.", "16.", "17.", "18.", "19.", "20.",
                "21.", "22.", "23.", "24.", "25.", "26.", "27.", "28.", "29.", "30."
            ]

            numbers_1 = [
                "①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩",
                "⑪", "⑫", "⑬", "⑭", "⑮", "⑯", "⑰", "⑱", "⑲", "⑳",
                "㉑", "㉒", "㉓", "㉔", "㉕", "㉖", "㉗", "㉘", "㉙", "㉚"
            ]

            numbers_2 = [
                "一、", "二、", "三、", "四、", "五、", "六、", "七、", "八、", "九、", "十、",
                "十一、", "十二、", "十三、", "十四、", "十五、", "十六、", "十七、", "十八、", "十九、", "二十、",
                "二十一、", "二十二、", "二十三、", "二十四、", "二十五、", "二十六、", "二十七、", "二十八、", "二十九、", "三十、"
            ]

            numbers_3 = [
                "(1)", "(2)", "(3)", "(4)", "(5)", "(6)", "(7)", "(8)", "(9)", "(10)",
                "(11)", "(12)", "(13)", "(14)", "(15)", "(16)", "(17)", "(18)", "(19)", "(20)",
                "(21)", "(22)", "(23)", "(24)", "(25)", "(26)", "(27)", "(28)", "(29)", "(30)"
            ]
            # 根据随机数选择对应的数字序号样式
            if random_number == 0:
                numbers = numbers_0
            elif random_number == 1:
                numbers = numbers_1
            elif random_number == 2:
                numbers = numbers_2
            else:  # random_number == 3
                numbers = numbers_3

            # 白底图片尺寸参数
            white_bg_width = 980  # 白底图片宽度
            white_bg_height = 1400  # 白底图片高度
            content_start_y = 85 + (part_num - 1) * 10  # 内容起始Y位置
            content_end_y = white_bg_height - 50  # 内容结束Y位置（留50像素底边距）
            available_height = content_end_y - content_start_y  # 可用高度

            # 文本换行和高度计算函数
            def calculate_text_display_height(text, font_size=16, max_width=920):
                """
                精确计算文本显示所需高度，考虑换行
                """
                if not text:
                    return 25  # 默认行高

                # 中文字符约占字体大小的全宽，英文字符约占0.6倍
                # 为了安全起见，使用0.8倍作为平均字符宽度
                avg_char_width = font_size * 0.8
                chars_per_line = max(1, int(max_width / avg_char_width))

                # 计算需要的行数
                lines_needed = max(1, (len(text) + chars_per_line - 1) // chars_per_line)

                # 每行高度25像素，包含行间距
                return lines_needed * 20

            # 智能分页算法
            def create_pages_with_line_animation(video_text_list, available_height):
                """
                创建支持逐行显示的多页布局
                每页最多8条记录
                返回: [(页码, [(条目索引, 文本, Y位置, 高度)])] 
                """
                pages = []
                current_page_items = []
                current_page_height = 0
                page_num = 0
                MAX_ITEMS_PER_PAGE = 8  # 每页最多8条记录

                for i, text in enumerate(video_text_list):
                    if not text.strip():
                        continue

                    # 生成带序号的完整文本
                    full_text = numbers[i] + '' + text
                    text_height = calculate_text_display_height(full_text, model_set_dict['part_title_set']['fontSize'],
                                                                white_bg_width - 130)

                    # 检查是否需要换页（两个条件：1.超过8条 2.超出可用高度）
                    need_new_page = (
                            len(current_page_items) >= MAX_ITEMS_PER_PAGE or
                            (current_page_height + text_height > available_height and current_page_items)
                    )

                    if need_new_page:
                        # 保存当前页
                        pages.append((page_num, current_page_items))
                        page_num += 1
                        current_page_items = []
                        current_page_height = 0

                    # 计算Y位置
                    item_y = content_start_y + current_page_height

                    # 添加到当前页
                    current_page_items.append((i, full_text, item_y, text_height))
                    current_page_height += text_height

                # 添加最后一页
                if current_page_items:
                    pages.append((page_num, current_page_items))

                return pages

            # 生成页面布局
            pages_layout = create_pages_with_line_animation(video_text, available_height)
            total_pages = len(pages_layout)

            # 添加调试日志
            self.add_log(f'文本内容分成{total_pages}页显示')
            for page_idx, page_items in pages_layout:
                self.add_log(f'第{page_idx + 1}页包含{len(page_items)}条记录')
            QApplication.processEvents()

            pos_x = 65
            # 根据文本长度调整水平位置
            for part_video_text in video_text:
                if len(part_video_text) > 7:
                    pos_x = 30
                    break

            # 根据文本长度调整字体大小
            for part_video_text in video_text:
                if len(part_video_text) > 10:
                    model_set_dict['part_title_set']['fontSize'] = 12
                    break

            # 生成多页逐行显示的字幕
            PAGE_PAUSE_DURATION = 3.0  # 每页暂停2秒
            UNIFORM_LINE_INTERVAL = 0.5  # 统一的逐行显示间隔（秒），确保所有页面出现速度一致

            # 计算实际需要的视频总时长
            total_video_duration = 0
            for page_idx, page_items in pages_layout:
                page_duration = len(page_items) * UNIFORM_LINE_INTERVAL + PAGE_PAUSE_DURATION
                total_video_duration += page_duration

            # 更新视频时长为实际需要的时长
            show_time = total_video_duration

            # 计算第一页完整显示的时间点（用于截取封面）
            first_page_complete_time = None
            if total_pages > 0:
                # 第一页的最后一条字幕出现的时间 = (第一页条目数 - 1) * 间隔
                first_page_items_count = len(pages_layout[0][1])
                first_page_complete_time = (first_page_items_count - 1) * UNIFORM_LINE_INTERVAL + 1

            self.add_log(
                f'计算视频时长: {show_time}秒 (共{total_pages}页), 第一页完整显示时间: {first_page_complete_time}秒')
            QApplication.processEvents()

            for page_idx, page_items in pages_layout:
                # 计算页面显示时间（包含暂停时间）
                if total_pages > 1:
                    # 多页模式：每页内容显示时间根据实际条目数量 × 统一间隔计算
                    page_content_duration = len(page_items) * UNIFORM_LINE_INTERVAL

                    # 计算当前页的时间范围
                    if page_idx == 0:
                        page_start_time = 0
                    else:
                        # 累加前面所有页面的时间（内容时间 + 暂停时间）
                        page_start_time = sum(
                            len(pages_layout[i][1]) * UNIFORM_LINE_INTERVAL + PAGE_PAUSE_DURATION
                            for i in range(page_idx)
                        )

                    page_content_end_time = page_start_time + page_content_duration
                    page_end_time = page_content_end_time + PAGE_PAUSE_DURATION  # 所有页面都包含暂停时间

                    # 使用统一的逐行显示间隔
                    line_interval = UNIFORM_LINE_INTERVAL
                else:
                    # 单页模式：使用统一间隔，末尾也停留2秒
                    page_start_time = 0
                    page_content_duration = len(page_items) * UNIFORM_LINE_INTERVAL
                    page_content_end_time = page_content_duration
                    page_end_time = page_content_end_time + PAGE_PAUSE_DURATION

                    # 使用统一的逐行显示间隔
                    line_interval = UNIFORM_LINE_INTERVAL

                # 为当前页的每一行生成字幕
                for line_idx, (item_idx, full_text, item_y, text_height) in enumerate(page_items):
                    # 计算每行的显示时间（逐行出现效果）
                    line_start_time = page_start_time + (line_idx * line_interval)

                    # 字幕结束时间：所有页面都包含2秒停留时间
                    line_end_time = page_start_time + page_content_duration + PAGE_PAUSE_DURATION

                    # 生成字幕
                    text = file_word_infor_content_apply_effects_to_text(full_text,
                                                                         model_set_dict['part_title_set'],
                                                                         len(video_text), pos_x, item_y)
                    ass_events += f"Dialogue: 0,{sec_to_ass(line_start_time)},{sec_to_ass(line_end_time)},Default,,0,0,0,,{text}" + '\n'

            # ASS文件内容
            ass_content = ass_header + "\n" + ass_events
            out_content_ass_path = os.path.join(video_tamp_path, 'wordIntroContent.ass')
            with open(out_content_ass_path, "w", encoding="utf-8") as f:
                f.write(ass_content)

            # 输出路径
            video_name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', video_title) + '_0.mp4'

            saveVideoPath = out_dir_path

            video_file_path = os.path.join(saveVideoPath, video_name)

            excel_file_path_name = '1.xls'
            # 任务文件输出路径
            excel_file_path = os.path.join(saveVideoPath, excel_file_path_name)

            # 根据关键词获取一张图片
            title_keyword_list = title_keyword(video_title)
            ftp_cover_video_id = get_random_cover_pic(title_keyword_list, account_name)

            # 旅游图片
            random_pic_path = download_word_pic(ftp_cover_video_id)

            if not random_pic_path or not os.path.exists(random_pic_path):
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                logging.debug(f'下载图片失败')
                continue

            position = (50, 410 + (part_num - 1) * 65)  # 水印图片的位置
            # size = (980, min(len(video_text) * 150, 1450 - ((part_num - 1) * 45)))  # 水印图片的大小
            size = (980, 1200)  # 水印图片的大小
            opacity = 100  # 水印图片的透明度

            white_pic_path = os.path.join(video_tamp_path, 'onWhite.png')

            # 添加透明图片
            add_watermark(random_pic_path, 'white.png', white_pic_path, position, size, opacity)

            if not os.path.exists(white_pic_path):
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                self.add_log('图片添加白色背景失败')
                QApplication.processEvents()
                continue

            composite_worker = CompositeWordIntroVideo(white_pic_path, out_title_ass_path, out_content_ass_path,
                                                       video_file_path, show_time, first_page_complete_time)

            self.add_log('正在合成一个视频。。。')
            QApplication.processEvents()

            self.thread_pool.start(composite_worker)
            # 创建一个事件循环
            composite_worker.signals.finished.connect(self.on_success_occurred)
            composite_worker.signals.errorOccurred.connect(self.on_error_occurred)
            self.loop.exec()
            if self.error_flag:
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                logging.debug(f'合成一个视频失败')
                continue

            self.add_log('已经合成一个视频，接下来进行后期处理。')
            QApplication.processEvents()

            if not os.path.exists(video_file_path):
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                self.add_log('没有已经合成一个视频，跳过。')
                QApplication.processEvents()
                continue

            # 匹配添加音乐
            parent_dir = os.getcwd()
            # 构造同级的缓存文件夹路径
            cache_music_dir_path = os.path.join(parent_dir, 'cacheMusic2')
            # 获取文件夹中的所有MP3文件
            mp3_files = [f for f in os.listdir(cache_music_dir_path) if
                         f.endswith('.mp3') or f.endswith('.MP3')]

            # 如果文件夹中有MP3文件，则随机选择一个
            if mp3_files:
                random_mp3_file = random.choice(mp3_files)
                random_mp3_file_path = os.path.join(cache_music_dir_path, random_mp3_file)
                print(f"随机选择的MP3文件路径为：{random_mp3_file_path}")
            else:
                print("文件夹中没有找到MP3文件,缺少音乐。")
                break

            bgAudioVolume = 80
            output_bgm_video_path = video_file_path.replace('_0.mp4', '_1.mp4')
            addMusicWorker = AddMusicWorker(video_file_path, random_mp3_file_path, 100, bgAudioVolume,
                                            output_bgm_video_path)

            self.thread_pool.start(addMusicWorker)
            # 创建一个事件循环
            addMusicWorker.signals.finished.connect(self.on_success_occurred)
            addMusicWorker.signals.errorOccurred.connect(self.on_error_occurred)
            self.loop.exec()

            if self.error_flag:
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                logging.debug(f'添加音乐失败')
                continue

            self.add_log('后期处理,已添加音乐。')
            QApplication.processEvents()

            # 添加水印
            watermark_location_examples = [['50', '50'], ['main_w-overlay_w-100', '50'],
                                           ['50', 'main_h-overlay_h-50'],
                                           ['main_w-overlay_w-50', 'main_h-overlay_h-50'],
                                           ['(main_w-overlay_w)/2', '(main_h-overlay_h)/2'],
                                           ['(main_w-overlay_w)/2', '50'],
                                           ['(main_w-overlay_w)/2', 'main_h-overlay_h-100']]

            watermark_setting = {
                'watermark_location': watermark_location_examples[
                    self.all_setting_dict['water_set']['position']],
                'zoom_size': self.all_setting_dict['water_set']['zoom'],
                'pic_alpha': self.all_setting_dict['water_set']['alpha']
            }
            final_output_path = output_bgm_video_path.replace('_1.mp4', '.mp4')
            add_text_watermark_worker = AddWatermarkWorker(output_bgm_video_path, final_output_path,
                                                           watermark_setting, 2,
                                                           self.all_setting_dict['water_set']['filePath'])
            self.thread_pool.start(add_text_watermark_worker)
            # 创建一个事件循环
            add_text_watermark_worker.signals.finished.connect(self.on_success_occurred)
            add_text_watermark_worker.signals.errorOccurred.connect(self.on_error_occurred)
            self.loop.exec()

            if self.error_flag:
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                logging.debug(f'添加水印失败')
                continue

            self.add_log('后期处理,已添加水印。')
            QApplication.processEvents()

            # 视频压缩
            temp_compressed_path = final_output_path.replace('.mp4', '_temp_compressed.mp4')
            compress_video_worker = CompressVideoWorker(final_output_path, temp_compressed_path)

            self.thread_pool.start(compress_video_worker)
            compress_video_worker.signals.finished.connect(self.on_success_occurred)
            compress_video_worker.signals.errorOccurred.connect(self.on_error_occurred)
            self.loop.exec()

            if self.error_flag:
                self.add_log('视频压缩失败，使用原始文件')
                QApplication.processEvents()
            else:
                self.add_log('视频压缩完成')
                QApplication.processEvents()

            # 移除中间视频
            if os.path.exists(video_file_path):
                os.remove(video_file_path)

            if os.path.exists(output_bgm_video_path):
                os.remove(output_bgm_video_path)

            data_dict = {
                "标题": video_title.replace('|', ''),
                "标签": video_tag,
                "文件路径": final_output_path.replace('/', '\\'),
                "描述": ','.join(video_text),
                "封面路径": "",
                "图片集合": "",
                "关联商品": "",
                "分区分类": "旅游",
                "备注": ""
            }

            write_to_old_excel(excel_file_path, data_dict)

            # 上传任务信息
            # 账号姓名
            # account_name = self.accountNameLineEdit.text()
            # 账号account
            account_result = self.get_upload_accounts(account_name)

            # 上传任务
            if len(account_result) > 0:
                for (account, mac) in account_result:
                    print(account)
                    task_param = {
                        'name': account_name,
                        'account': account,
                        'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'title': data_dict.get('标题'),
                        'mac': mac,
                        'tag': data_dict.get('标签'),
                        'path': data_dict.get('文件路径'),
                        'describe': data_dict.get('描述'),
                        'classify': data_dict.get('分区分类'),
                        'task_type': 5,
                    }
                    add_user_task(task_param)
                    update_image_user_by_id(ftp_cover_video_id, account_name)
                    self.add_log(f'{account_name}{account}上传视频任务:{final_output_path}')
                    QApplication.processEvents()

            self.add_log(f'生成完成一个视频:{final_output_path}')
            QApplication.processEvents()

            # 删除cut video缓存
            clean_cut_cache()
            clean_cache()
            copy_start_num += 1

    # 素材通用类
    def compositeMaterialStrategyVideo(self, copy_file, out_dir_path, account_name, label_file=None):
        settings = read_dict_from_txt('setting.txt')
        options = SanongComposeOptions(
            screen=self.screenComboBox.currentIndex(),
            random_video_model=self.randomVideoModelCheckBox.isChecked(),
        )
        composer = SanongComposer(
            options=options,
            log=self.add_log,
            base_dir=Path.cwd(),
            music_dir=Path.cwd() / 'cacheMusic1',
        )
        results = composer.compose(
            Path(copy_file),
            Path(label_file) if label_file else None,
            Path(out_dir_path),
            account_name,
            settings,
        )

        account_result = self.get_upload_accounts(account_name)
        for result in results:
            for account, mac in account_result:
                add_user_task({
                    'name': account_name,
                    'account': account,
                    'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'title': result.title,
                    'mac': mac,
                    'tag': result.tag,
                    'path': str(result.video_path),
                    'describe': ','.join(result.description),
                    'classify': '旅游',
                    'task_type': 6,
                })
                self.add_log(f'{account_name}{account}上传视频任务:{result.video_path}')
            self.run_label.setText(f'生成完成一个视频:{result.video_path}')
        return results


    # 励志通用类
    def compositeLifeStrategyVideo(self, copy_file, out_dir_path, account_name):

        self.add_log('开始合成根据文案合成视频')
        QApplication.processEvents()

        # 时间
        timestamp = int(time.time())

        if self.randomVideoModelCheckBox.isChecked():
            model_result = get_random_video_model()
            model_set_dict = json.loads(model_result['model_set'])
            self.all_setting_dict['title_set'] = model_set_dict['title_set']
            self.all_setting_dict['part_title_set'] = model_set_dict['part_title_set']
            self.all_setting_dict['srt_set'] = model_set_dict['srt_set']
            self.all_setting_dict['voice_set'] = model_set_dict['voice_set']
            self.all_setting_dict['part_title_part_0_set'] = model_set_dict['part_title_part_0_set']
            self.all_setting_dict['part_title_part_1_set'] = model_set_dict['part_title_part_1_set']
            self.all_setting_dict['part_title_part_2_set'] = model_set_dict['part_title_part_2_set']
            self.all_setting_dict['part_title_part_3_set'] = model_set_dict['part_title_part_3_set']
            self.all_setting_dict['part_title_part_4_set'] = model_set_dict['part_title_part_4_set']
            self.all_setting_dict['part_title_part_5_set'] = model_set_dict['part_title_part_5_set']
        else:
            self.all_setting_dict = read_dict_from_txt('setting.txt')

        if not os.path.exists(self.all_setting_dict['end_video']['end_video_path']):
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                             QMessageBox QLabel {
                             background-color: rgb(22, 23, 25);
                             color: rgb(255, 255, 255);
                            }
                            QMessageBox {
                            background-color: rgb(22, 23, 25);
                            color: rgb(255, 255, 255);
                            }
                        """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"请选择视频添加的片尾")
            msg_box.exec()
            return

        # 删除video缓存
        clean_cut_cache()
        clean_cache()

        # copy 起始行
        copy_start_num = get_first_data_row(copy_file)

        self.add_log(f'读取视频文案,文案文件路径是{str(copy_file)}')

        # tts 速度
        speed_value = str(self.all_setting_dict['voice_set']['spd_0'])
        if not str(speed_value).startswith('-'):
            speed_value = '+' + speed_value
        speed_value = speed_value + '%'

        # 获取音频设置
        audio_setting = {
            'api_type': self.all_setting_dict['voice_set']['api_type'],
            'audio_role': self.audio_role_list[self.all_setting_dict['voice_set']['role_0']],
            'speed_value': speed_value,
            'volume_value': self.all_setting_dict['voice_set']['vol_0']
        }

        if self.all_setting_dict['voice_set']['api_type'] == 1:
            # 获取音频设置
            audio_setting = {
                'api_type': self.all_setting_dict['voice_set']['api_type'],
                'audio_role': int(
                    self.audio_bd_role_list[self.all_setting_dict['voice_set']['role_1']].split(':')[1]),
                'speed_value': self.all_setting_dict['voice_set']['spd_1'],
                'volume_value': self.all_setting_dict['voice_set']['vol_1'],
                'tone_value': self.all_setting_dict['voice_set']['pit_1']
            }

        while True:

            # 获取视频文案
            video_title_text = get_row_data(copy_file, copy_start_num)

            self.add_log('读取视频文案')
            QApplication.processEvents()

            # video_title_text.append('记得点赞关注评论')

            self.add_log(f'读取视频标签，{"&&".join(video_title_text)}')
            QApplication.processEvents()

            if len(video_title_text) < 3:
                self.add_log('全部生成完成')
                QApplication.processEvents()
                # QMessageBox.information(self, "完成", f"所有视频已生成处理完成，已生成任务列表")
                break

            # 标题
            video_title = video_title_text[0].strip()

            # 标签
            video_tag = video_title_text[1].strip()

            # 文案
            video_text = video_title_text[2:]

            # 文案段数
            video_text_part_num = len(video_text)
            if video_text_part_num <= 2:
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                logging.debug(f'合成一个视频失败')
                continue

            # 视频处理缓存文件夹
            tamp_folder_name = 'tempConcateVideo'
            current_directory = os.getcwd()
            tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
            video_tamp_path_name = 'video_cache_file'
            video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)

            if len(video_text) > 0:

                # 素材缓存路径
                part_video_list = []

                # 字幕缓存路径
                part_srt_ass_list = []

                # 音频缓存路径
                part_audio_list = []

                # 标题缓存路径
                part_title_ass_list = []

                # 配音初始字幕生成-----------------------------------------------------------
                product_worker = SaWorker(video_text, audio_setting)
                self.thread_pool.start(product_worker)
                # 事件循环
                product_worker.signals.finished.connect(self.on_success_occurred)
                product_worker.signals.errorOccurred.connect(self.on_error_occurred)
                self.loop.exec()
                if self.error_flag:
                    # 删除cut video缓存
                    clean_cut_cache()
                    clean_cache()
                    copy_start_num += 1
                    logging.debug(f'合成一个视频失败')
                    continue

                self.add_log('ai分析文案，已经为视频生成字幕配音即标签')
                QApplication.processEvents()

                # 生成标题、小标题以及字幕的ass文件-----------------------------------------------------------

                # 视频不重复记录
                video_id_list = []

                for i in range(video_text_part_num):

                    srt_file_name = f"temp_subtitle{i}.srt"

                    audio_file_name = f"temp_final_audio{i}.mp3"

                    # 原字幕文件
                    part_subtitle_url = os.path.join(video_tamp_path, srt_file_name)

                    # ass字幕文件
                    output_path = part_subtitle_url.replace('.srt', '.ass')

                    # 标题字幕文件
                    output_title_path = part_subtitle_url.replace('.srt', '_title.ass')

                    # 音频文件
                    output_audio_path = os.path.join(video_tamp_path, audio_file_name)

                    # 转换成ass
                    convert_srt_to_ass(part_subtitle_url, output_path, self.all_setting_dict['srt_set'])

                    if i == 0:
                        remove_dialogue_text(output_path)

                    # 转换完成后 记录ass字幕位置
                    part_srt_ass_list.append(output_path)

                    # 记录音频位置
                    part_audio_list.append(output_audio_path)

                    # 创建标题ass，通用只有大标题
                    if i == 0:
                        self.pic_time = create_title(self.all_setting_dict, '1',
                                                     self.screenComboBox.currentIndex(),
                                                     video_title, output_title_path, part_subtitle_url)

                        part_title_ass_list.append(output_title_path)
                    # self.pic_time = 0.1

                    self.add_log('视频样式字幕已生成')
                    QApplication.processEvents()

                    # 选取视频素材-----------------------------------------------------------
                    # 片段配音
                    part_audio_url = output_audio_path

                    # 配音时长
                    audio_length = get_audio_length(part_audio_url)

                    # if i == video_text_part_num - 1:
                    #     video_path = self.all_setting_dict['end_video']['end_video_path']
                    #     if os.path.exists(video_path):
                    #         part_video_list.append(video_path)

                    # 随机视频
                    video_match_attempts = 0
                    max_video_match_attempts = 20
                    while True:
                        video_match_attempts += 1
                        if video_match_attempts > max_video_match_attempts:
                            self.add_log(f'匹配素材超过{max_video_match_attempts}次仍无可用素材，跳过该段')
                            QApplication.processEvents()
                            video_path = ''
                            break
                        print('获取不同素材中')
                        ftp_cover_video_id = get_random_cover_video_by_cate('普通素材')
                        video_path = download_cover_video(ftp_cover_video_id)
                        if os.path.exists(video_path) and ftp_cover_video_id not in video_id_list:
                            break
                    if not video_path or not os.path.exists(video_path):
                        continue
                    # 音频时长截取视频内容
                    time.sleep(1)
                    cut_video_path = cut_video_by_audio_length(video_path, ftp_cover_video_id, audio_length)
                    if os.path.exists(cut_video_path):
                        video_id_list.append(ftp_cover_video_id)
                        self.add_log(f'正在匹配素材，已经为视频随机选取了{len(part_video_list) + 1}个素材')
                        QApplication.processEvents()
                        part_video_list.append(cut_video_path)

                # 片尾加一段空白字幕音频
                # 空白字幕
                blank_sub_file_path = os.path.join(current_directory, 'blank.ass')
                part_srt_ass_list.append(blank_sub_file_path)
                # 空白音频
                blank_audio_file_path = os.path.join(current_directory, 'blank.mp3')
                part_audio_list.append(blank_audio_file_path)
                audio_length = get_audio_length(blank_audio_file_path)
                video_match_attempts = 0
                max_video_match_attempts = 20
                while True:
                    video_match_attempts += 1
                    if video_match_attempts > max_video_match_attempts:
                        self.add_log(f'匹配素材超过{max_video_match_attempts}次仍无可用素材，跳过该段')
                        QApplication.processEvents()
                        video_path = ''
                        break
                    print('获取不同素材中')
                    ftp_cover_video_id = get_random_cover_video_by_cate('普通素材')
                    video_path = download_cover_video(ftp_cover_video_id)
                    if os.path.exists(video_path) and ftp_cover_video_id not in video_id_list:
                        break
                if not video_path or not os.path.exists(video_path):
                    continue
                # 音频时长截取视频内容
                time.sleep(1)
                cut_video_path = cut_video_by_audio_length(video_path, ftp_cover_video_id, audio_length)
                if os.path.exists(cut_video_path):
                    video_id_list.append(ftp_cover_video_id)
                    self.add_log(f'正在匹配素材，已经为视频随机选取了{len(part_video_list) + 1}个素材')
                    QApplication.processEvents()
                    part_video_list.append(cut_video_path)

                # 如果素材数量和文案一样，就进行合成 未处理成功
                if len(part_video_list) - 1 == video_text_part_num:
                    transitionSetting = {
                        'transitionNum': 0,
                        'transitionTime': 0
                    }
                    saveVideoPath = out_dir_path

                    video_id_path_name = 'video_id.xlsx'
                    # 任务文件输出路径
                    video_id_excel_file_path = os.path.join(saveVideoPath, video_id_path_name)

                    # 记录每个视频匹配的素材
                    write_arrays_to_excel(video_id_excel_file_path, [video_title] + part_video_list)

                    # 输出路径
                    video_name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', video_title) + '_0.mp4'

                    video_file_path = os.path.join(saveVideoPath, video_name)

                    excel_file_path_name = '1.xls'
                    # 任务文件输出路径
                    excel_file_path = os.path.join(saveVideoPath, excel_file_path_name)

                    composite_worker = CompositeVideo(part_video_list, part_audio_list, part_srt_ass_list,
                                                      part_title_ass_list, video_file_path,
                                                      transitionSetting, self.pic_time)

                    self.add_log(f'正在合成拼接一个视频。。。')
                    QApplication.processEvents()

                    self.thread_pool.start(composite_worker)
                    # 创建一个事件循环
                    composite_worker.signals.finished.connect(self.on_success_occurred)
                    composite_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()
                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        logging.debug(f'合成一个视频失败')
                        continue

                    self.add_log(f'已经合成一个视频，接下来进行后期处理。')
                    QApplication.processEvents()

                    # 匹配添加音乐
                    parent_dir = os.getcwd()
                    # 构造同级的缓存文件夹路径
                    cache_music_dir_path = os.path.join(parent_dir, 'cacheMusic3')
                    # 获取文件夹中的所有MP3文件
                    mp3_files = [f for f in os.listdir(cache_music_dir_path) if
                                 f.endswith('.mp3') or f.endswith('.MP3')]

                    if not mp3_files:
                        cache_music_dir_path = os.path.join(parent_dir, 'cacheMusic1')
                        mp3_files = [f for f in os.listdir(cache_music_dir_path) if
                                     f.endswith('.mp3') or f.endswith('.MP3')]
                        self.add_log('励志音乐库为空，使用通用音乐库')

                    # 如果文件夹中有MP3文件，则随机选择一个
                    if mp3_files:
                        random_mp3_file = random.choice(mp3_files)
                        random_mp3_file_path = os.path.join(cache_music_dir_path, random_mp3_file)
                        print(f"随机选择的MP3文件路径为：{random_mp3_file_path}")
                    else:
                        print("文件夹中没有找到MP3文件,缺少音乐。")
                        break

                    bgAudioVolume = 40
                    final_output_path = video_file_path.replace('_0.mp4', '.mp4')
                    addMusicWorker = AddMusicWorker(video_file_path, random_mp3_file_path, 100, bgAudioVolume,
                                                    final_output_path)

                    self.thread_pool.start(addMusicWorker)
                    # 创建一个事件循环
                    addMusicWorker.signals.finished.connect(self.on_success_occurred)
                    addMusicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        logging.debug(f'添加音乐失败')
                        continue

                    self.add_log(f'后期处理,已添加音乐。')
                    QApplication.processEvents()

                    # 移除中间视频
                    if os.path.exists(video_file_path):
                        os.remove(video_file_path)

                    data_dict = {
                        "标题": video_title.replace('|', ''),
                        "标签": video_tag,
                        "文件路径": final_output_path.replace('/', '\\'),
                        "描述": ','.join(video_text),
                        "封面路径": "",
                        "图片集合": "",
                        "关联商品": "",
                        "分区分类": "旅游",
                        "备注": ""
                    }

                    write_to_old_excel(excel_file_path, data_dict)

                    account_result = self.get_upload_accounts(account_name)

                    # 上传任务
                    if len(account_result) > 0:
                        for (account, mac) in account_result:
                            print(account)
                            task_param = {
                                'name': account_name,
                                'account': account,
                                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'title': data_dict.get('标题'),
                                'mac': mac,
                                'tag': data_dict.get('标签'),
                                'path': data_dict.get('文件路径'),
                                'describe': data_dict.get('描述'),
                                'classify': data_dict.get('分区分类'),
                                'task_type': 0,
                            }
                            add_user_task(task_param)
                            self.add_log(f'{account_name}{account}上传视频任务:{final_output_path}')
                            QApplication.processEvents()

                    self.run_label.setText(f'生成完成一个视频:{final_output_path}')
                else:
                    logging.debug(f'匹配的视频与文案数量不一致')
                    print('匹配的视频与文案数量不一致')
                    unSuccessCopy = str(timestamp) + '_copy.xlsx'
                    notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                    notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
                    # 记入未匹配的文案和视频标签
                    write_arrays_to_excel(notSuccess_copy_folder_path, video_title_text[0:-1])
                    self.add_log(f'跳过一个脚本文案，可能是没有匹配到视频，已记录')
                    QApplication.processEvents()

            # 删除cut video缓存
            clean_cut_cache()
            clean_cache()
            copy_start_num += 1

        current_directory = os.getcwd()
        unSuccessCopy = str(timestamp) + '_copy.xlsx'
        notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
        notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
        if os.path.exists(notSuccess_copy_folder_path):
            self.add_log('有视频记录没有生成完毕')
            QApplication.processEvents()
            self.copyFileLabel.setText(notSuccess_copy_folder_path)
        else:
            self.add_log('所有视频记录已经生成完毕，无记录可生成')
            QApplication.processEvents()

    # 景点通用介绍类
    def compositeScenicSpotVideo(self, copy_file, label_file, out_dir_path, account_name):
        self.add_log('开始合成根据文案合成视频')
        QApplication.processEvents()

        # 时间
        timestamp = int(time.time())

        if self.randomVideoModelCheckBox.isChecked():
            model_result = get_random_video_model()
            model_set_dict = json.loads(model_result['model_set'])
            self.all_setting_dict['title_set'] = model_set_dict['title_set']
            self.all_setting_dict['part_title_set'] = model_set_dict['part_title_set']
            self.all_setting_dict['srt_set'] = model_set_dict['srt_set']
            self.all_setting_dict['voice_set'] = model_set_dict['voice_set']
            self.all_setting_dict['part_title_part_0_set'] = model_set_dict['part_title_part_0_set']
            self.all_setting_dict['part_title_part_1_set'] = model_set_dict['part_title_part_1_set']
            self.all_setting_dict['part_title_part_2_set'] = model_set_dict['part_title_part_2_set']
            self.all_setting_dict['part_title_part_3_set'] = model_set_dict['part_title_part_3_set']
            self.all_setting_dict['part_title_part_4_set'] = model_set_dict['part_title_part_4_set']
            self.all_setting_dict['part_title_part_5_set'] = model_set_dict['part_title_part_5_set']
        else:
            self.all_setting_dict = read_dict_from_txt('setting.txt')

        if not os.path.exists(self.all_setting_dict['end_video']['end_video_path']):
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                                 QMessageBox QLabel {
                                 background-color: rgb(22, 23, 25);
                                 color: rgb(255, 255, 255);
                                }
                                QMessageBox {
                                background-color: rgb(22, 23, 25);
                                color: rgb(255, 255, 255);
                                }
                            """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"请选择视频添加的片尾")
            msg_box.exec()
            return

        # 删除video缓存
        clean_cut_cache()
        clean_cache()

        # copy 起始行
        copy_start_num = get_first_data_row(copy_file)

        # label 起始行
        label_start_num = get_first_data_row(label_file)

        self.add_log(f'读取视频文案,文案文件路径是{str(copy_file)},标签文件路径是{str(label_file)}')

        if copy_start_num == -1 or label_start_num == -1 or copy_start_num is None or label_start_num is None:
            self.add_log('文案文件或者标签文件没有数据可读，结束合成视频')
            QApplication.processEvents()
            return

        # tts 速度
        speed_value = str(self.all_setting_dict['voice_set']['spd_0'])
        if not str(speed_value).startswith('-'):
            speed_value = '+' + speed_value
        speed_value = speed_value + '%'

        # 获取音频设置
        audio_setting = {
            'api_type': self.all_setting_dict['voice_set']['api_type'],
            'audio_role': self.audio_role_list[self.all_setting_dict['voice_set']['role_0']],
            'speed_value': speed_value,
            'volume_value': self.all_setting_dict['voice_set']['vol_0']
        }

        if self.all_setting_dict['voice_set']['api_type'] == 1:
            # 获取音频设置
            audio_setting = {
                'api_type': self.all_setting_dict['voice_set']['api_type'],
                'audio_role': int(
                    self.audio_bd_role_list[self.all_setting_dict['voice_set']['role_1']].split(':')[1]),
                'speed_value': self.all_setting_dict['voice_set']['spd_1'],
                'volume_value': self.all_setting_dict['voice_set']['vol_1'],
                'tone_value': self.all_setting_dict['voice_set']['pit_1']
            }

        while True:

            # 获取视频文案
            video_title_text = get_row_data(copy_file, copy_start_num)

            self.add_log('读取视频文案')
            QApplication.processEvents()

            # video_title_text.append('记得点赞关注评论')

            # 获取视频标签
            label_text = get_row_data(label_file, label_start_num)

            self.add_log(f'读取视频标签，{"&&".join(video_title_text)}，{"&&".join(label_text)}')
            QApplication.processEvents()

            if len(video_title_text) < 3:
                self.add_log('全部生成完成')
                QApplication.processEvents()
                # QMessageBox.information(self, "完成", f"所有视频已生成处理完成，已生成任务列表")
                break

            # label_text.append('点赞,关注,评论')

            # 标题
            video_title = video_title_text[0].strip()

            # 标签
            video_tag = video_title_text[1].strip()

            # 文案
            video_text = video_title_text[2:]

            # 文案段数
            video_text_part_num = len(video_text)
            if video_text_part_num <= 2:
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                label_start_num += 1
                logging.debug(f'合成一个视频失败')
                continue

            # 视频处理缓存文件夹
            tamp_folder_name = 'tempConcateVideo'
            current_directory = os.getcwd()
            tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
            video_tamp_path_name = 'video_cache_file'
            video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)

            if len(video_text) > 0:

                # 素材缓存路径
                part_video_list = []

                # 字幕缓存路径
                part_srt_ass_list = []

                # 音频缓存路径
                part_audio_list = []

                # 标题缓存路径
                part_title_ass_list = []

                # 配音初始字幕生成-----------------------------------------------------------
                product_worker = SaWorker(video_text, audio_setting)
                self.thread_pool.start(product_worker)
                # 事件循环
                product_worker.signals.finished.connect(self.on_success_occurred)
                product_worker.signals.errorOccurred.connect(self.on_error_occurred)
                self.loop.exec()
                if self.error_flag:
                    # 删除cut video缓存
                    clean_cut_cache()
                    clean_cache()
                    copy_start_num += 1
                    label_start_num += 1
                    logging.debug(f'合成一个视频失败')
                    continue

                self.add_log('ai分析文案，已经为视频生成字幕配音即标签')
                QApplication.processEvents()

                # 生成标题、小标题以及字幕的ass文件-----------------------------------------------------------

                # 视频不重复记录
                video_id_list = []
                pic_title_ass = ''
                pic_title_video = ''
                # 尝试匹配的过程并记录所有同义的词语
                synonyms_list = []
                for i in range(video_text_part_num):

                    srt_file_name = f"temp_subtitle{i}.srt"

                    audio_file_name = f"temp_final_audio{i}.mp3"

                    # 原字幕文件
                    part_subtitle_url = os.path.join(video_tamp_path, srt_file_name)

                    # ass字幕文件
                    output_path = part_subtitle_url.replace('.srt', '.ass')

                    # 标题字幕文件
                    output_title_path = part_subtitle_url.replace('.srt', '_title.ass')

                    # 音频文件
                    output_audio_path = os.path.join(video_tamp_path, audio_file_name)

                    # 转换成ass
                    convert_srt_to_ass(part_subtitle_url, output_path, self.all_setting_dict['srt_set'])

                    # if i == 0:
                    #     remove_dialogue_text(output_path)

                    # # 通用类需要去除开头和片尾标题
                    # if i == video_text_part_num - 1:
                    #     remove_all_dialogue_text(output_path)

                    # 转换完成后 记录ass字幕位置
                    part_srt_ass_list.append(output_path)

                    # 记录音频位置
                    part_audio_list.append(output_audio_path)

                    # # 创建标题ass，通用只有大标题
                    # if i == 0:
                    #     self.pic_time = create_title(self.all_setting_dict, '1',
                    #                                  self.screenComboBox.currentIndex(),
                    #                                  video_title, output_title_path, part_subtitle_url)
                    #
                    #     part_title_ass_list.append(output_title_path)

                    if i == 0:
                        # 封面帧
                        output_title_path = part_subtitle_url.replace('.srt', '_pic_title.ass')
                        self.pic_time = create_tagging_title(self.all_setting_dict, '1',
                                                             self.screenComboBox.currentIndex(),
                                                             video_title, output_title_path, part_subtitle_url,
                                                             label_text[1].split(',')[0])

                        if os.path.exists(output_title_path):
                            pic_title_ass = output_title_path

                    self.add_log('视频样式字幕已生成')
                    QApplication.processEvents()

                    # 匹配视频素材-----------------------------------------------------------
                    # 视频片段标签
                    part_video_tags = label_text[i].split(',')

                    # 片段配音
                    part_audio_url = output_audio_path

                    # 配音时长
                    audio_length = get_audio_length(part_audio_url)

                    # if i == video_text_part_num - 1:
                    #     video_path = self.all_setting_dict['end_video']['end_video_path']
                    #     if os.path.exists(video_path):
                    #         part_video_list.append(video_path)
                    # else:
                    # 匹配视频
                    unSuccessVideoLabel = str(timestamp) + '_videoLabel.xlsx'
                    notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                    notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessVideoLabel)

                    # # 片头片尾随机匹配其中景点视频
                    # if i == 0 or i == video_text_part_num - 1:
                    #     sights_word_key = label_text[random.randint(1, video_text_part_num - 3)].split(',')[0]
                    #     ftp_videos = get_videos_by_keyword_1(sights_word_key, self.screenComboBox.currentIndex()
                    #                                          , self.locationlineEdit.text().strip(),
                    #                                          audio_length)
                    #     ftp_video_ids = [video['id'] for video in ftp_videos]
                    #     if len(ftp_videos) > 0:
                    #         video_id = random.choice(ftp_video_ids)
                    #
                    #         try_time = 0
                    #         while video_id in video_id_list and try_time < 5:
                    #             video_id = random.choice(ftp_video_ids)
                    #             try_time += 1
                    #
                    #         video_id_list.append(video_id)
                    #
                    #         video_path = download_video(video_id, self.screenComboBox.currentIndex())
                    #         if video_path is not None:
                    #             if os.path.exists(video_path):
                    #                 # 音频时长截取视频内容
                    #                 time.sleep(1)
                    #                 cut_video_path = cut_video_by_audio_length(video_path, video_id,
                    #                                                            audio_length)
                    #                 if os.path.exists(cut_video_path):
                    #                     self.add_log(
                    #                         f'正在匹配素材，已经为视频匹配了{len(part_video_list) + 1}个素材')
                    #                     QApplication.processEvents()
                    #
                    #                     part_video_list.append(cut_video_path)
                    #
                    #                     if pic_title_video == '':
                    #                         pic_title_video = cut_video_path
                    #             else:
                    #                 self.add_log(f'下载素材失败')
                    #                 QApplication.processEvents()
                    # else:
                    while True:
                        ftp_video_List = []
                        # 地区景区匹配到的id
                        location_id_list = []
                        for n, tag in enumerate(part_video_tags):
                            if len(location_id_list) == 0 and n == 0:
                                ftp_videos = get_videos_by_keyword_1(tag,
                                                                     self.screenComboBox.currentIndex(),
                                                                     self.locationlineEdit.text().strip(),
                                                                     audio_length, 20)

                                synonyms_list = []

                                if len(ftp_videos) <= 0:
                                    print('缺少该关键字的素材')
                                    # 记入未匹配的文案和视频标签

                                    lost_video_param = {
                                        'title': part_video_tags[0],
                                        'firstTags': '_'.join(synonyms_list) + '_'.join(part_video_tags),
                                        'secondTags': '',
                                        'videoLength': audio_length,
                                        'screen': self.screenComboBox.currentIndex(),
                                        'accountName': account_name,
                                        'titleType': '7'
                                    }
                                    # 将缺少的视频信息记入库中
                                    add_lost_cn_video_record(lost_video_param)

                                    # 将缺少的视频信息记入表中
                                    write_arrays_to_excel(notSuccess_label_folder_path, part_video_tags)
                                    break

                                for video in ftp_videos:
                                    location_id_list.append(video['id'])

                            elif len(location_id_list) > 0:
                                ftp_videos = get_videos_by_keyword(tag, self.screenComboBox.currentIndex(),
                                                                   self.locationlineEdit.text().strip(),
                                                                   location_id_list,
                                                                   audio_length)
                            else:
                                ftp_videos = []

                            # 提取视频ID列表
                            if len(ftp_videos) > 0:
                                ftp_ideo_ids = [video['id'] for video in ftp_videos]
                                if len(ftp_ideo_ids) <= 0:
                                    continue
                                ftp_video_List.append(ftp_ideo_ids)

                        # 没有素材退出匹配
                        if len(ftp_video_List) <= 0:
                            print('缺少该素材，退出合成')
                            self.add_log(f'缺少该素材，退出合成')
                            QApplication.processEvents()
                            return

                        if len(ftp_video_List) == 1:
                            video_id = random.choice(ftp_video_List[0])
                        else:
                            video_id = count_and_sort(ftp_video_List)

                        try_time = 0
                        while video_id in video_id_list and try_time < 6:
                            video_id = random.choice(location_id_list)
                            try_time += 1

                        video_id_list.append(video_id)

                        # 当前重复率判断，并记录信息
                        if enough_unique(video_id_list) is False:
                            logging.debug(f'当前素材重复率过高，重新匹配')
                            lost_video_param = {
                                'title': part_video_tags[0],
                                'firstTags': '_'.join(synonyms_list) + '_' + '_'.join(part_video_tags),
                                'secondTags': '',
                                'videoLength': audio_length,
                                'screen': self.screenComboBox.currentIndex(),
                                'accountName': account_name,
                                'titleType': '7'
                            }
                            # 将缺少的视频信息记入库中
                            add_lost_cn_video_record(lost_video_param)

                        video_path = download_cn_video(video_id, self.screenComboBox.currentIndex())

                        time.sleep(1)
                        if video_path is not None:
                            if os.path.exists(video_path):
                                # 音频时长截取视频内容
                                cut_video_path = cut_video_by_audio_length(video_path, video_id,
                                                                           audio_length)

                                logging.debug(f'这个下载的视频{video_path}的')

                                if os.path.exists(cut_video_path):
                                    logging.debug(f'存在下载的视频{cut_video_path}')
                                    self.add_log(
                                        f'正在匹配素材，已经为视频匹配了{len(part_video_list) + 1}个素材')
                                    QApplication.processEvents()
                                    part_video_list.append(cut_video_path)
                                    if pic_title_video == '':
                                        pic_title_video = cut_video_path
                                    break
                                else:
                                    self.add_log(f'下载素材失败')
                                    QApplication.processEvents()
                                    break
                            else:
                                self.add_log(f'下载素材失败')
                                QApplication.processEvents()
                                break

                        else:
                            self.add_log(f'匹配下载素材失败')
                            QApplication.processEvents()
                            break

                # 重复率判断
                if enough_unique(video_id_list) is False:
                    self.add_log('素材重复率过高，跳过该视频合成')
                    QApplication.processEvents()
                    # 删除cut video缓存
                    clean_cut_cache()
                    clean_cache()
                    copy_start_num += 1
                    label_start_num += 1
                    logging.debug(f'合成一个视频失败')
                    continue

                # 如果素材数量和文案一样，就进行合成 未处理成功
                if len(part_video_list) == video_text_part_num:
                    transitionSetting = {
                        'transitionNum': 0,
                        'transitionTime': 0
                    }
                    saveVideoPath = out_dir_path

                    video_id_path_name = 'video_id.xlsx'
                    # 任务文件输出路径
                    video_id_excel_file_path = os.path.join(saveVideoPath, video_id_path_name)

                    # 记录每个视频匹配的素材
                    write_arrays_to_excel(video_id_excel_file_path, [video_title] + part_video_list)

                    # 输出路径
                    video_name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', video_title) + '_0.mp4'

                    video_file_path = os.path.join(saveVideoPath, video_name)

                    excel_file_path_name = '1.xls'
                    # 任务文件输出路径
                    excel_file_path = os.path.join(saveVideoPath, excel_file_path_name)

                    composite_worker = CompositeVideo(part_video_list, part_audio_list, part_srt_ass_list,
                                                      part_title_ass_list, video_file_path,
                                                      transitionSetting, self.pic_time)

                    self.add_log(f'正在合成拼接一个视频。。。')
                    QApplication.processEvents()

                    self.thread_pool.start(composite_worker)
                    # 创建一个事件循环
                    composite_worker.signals.finished.connect(self.on_success_occurred)
                    composite_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()
                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'合成一个视频失败')
                        continue

                    self.add_log(f'已经合成一个视频，接下来进行后期处理。')
                    QApplication.processEvents()

                    if not os.path.exists(video_file_path):
                        self.add_log('没有已经合成一个视频，跳过。')
                        QApplication.processEvents()
                        continue

                    # 匹配添加音乐
                    parent_dir = os.getcwd()
                    # 构造同级的缓存文件夹路径
                    cache_music_dir_path = os.path.join(parent_dir, 'cacheMusic1')
                    # 获取文件夹中的所有MP3文件
                    mp3_files = [f for f in os.listdir(cache_music_dir_path) if
                                 f.endswith('.mp3') or f.endswith('.MP3')]

                    # 如果文件夹中有MP3文件，则随机选择一个
                    if mp3_files:
                        random_mp3_file = random.choice(mp3_files)
                        random_mp3_file_path = os.path.join(cache_music_dir_path, random_mp3_file)
                        print(f"随机选择的MP3文件路径为：{random_mp3_file_path}")
                    else:
                        print("文件夹中没有找到MP3文件,缺少音乐。")
                        break

                    # 加载音频文件
                    # audio = AudioSegment.from_file(mp4_files)

                    # 获取音乐音频的音量（响度）
                    # music_volume = audio.dBFS  # 返回音频的响度，单位为分贝
                    # mb_db = 20.0
                    bgAudioVolume = 40
                    output_bgm_video_path = video_file_path.replace('_0.mp4', '_1.mp4')
                    addMusicWorker = AddMusicWorker(video_file_path, random_mp3_file_path, 100, bgAudioVolume,
                                                    output_bgm_video_path)

                    self.thread_pool.start(addMusicWorker)
                    # 创建一个事件循环
                    addMusicWorker.signals.finished.connect(self.on_success_occurred)
                    addMusicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加音乐失败')
                        continue

                    self.add_log('后期处理,已添加音乐。')
                    QApplication.processEvents()

                    # 添加水印
                    watermark_location_examples = [['50', '50'], ['main_w-overlay_w-100', '50'],
                                                   ['50', 'main_h-overlay_h-50'],
                                                   ['main_w-overlay_w-50', 'main_h-overlay_h-50'],
                                                   ['(main_w-overlay_w)/2', '(main_h-overlay_h)/2'],
                                                   ['(main_w-overlay_w)/2', '50'],
                                                   ['(main_w-overlay_w)/2', 'main_h-overlay_h-100']]

                    watermark_setting = {
                        'watermark_location': watermark_location_examples[
                            self.all_setting_dict['water_set']['position']],
                        'zoom_size': self.all_setting_dict['water_set']['zoom'],
                        'pic_alpha': self.all_setting_dict['water_set']['alpha']
                    }
                    watermark_output_path = output_bgm_video_path.replace('_1.mp4', '_2.mp4')
                    add_text_watermark_worker = AddWatermarkWorker(output_bgm_video_path, watermark_output_path,
                                                                   watermark_setting, 2,
                                                                   self.all_setting_dict['water_set']['filePath'])
                    self.thread_pool.start(add_text_watermark_worker)
                    # 创建一个事件循环
                    add_text_watermark_worker.signals.finished.connect(self.on_success_occurred)
                    add_text_watermark_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加水印失败')
                        continue

                    self.add_log('后期处理,已添加水印。')
                    QApplication.processEvents()

                    # 视频压缩
                    temp_compressed_path = watermark_output_path.replace('_2.mp4', '_temp_compressed.mp4')
                    compress_video_worker = CompressVideoWorker(watermark_output_path, temp_compressed_path)

                    self.thread_pool.start(compress_video_worker)
                    compress_video_worker.signals.finished.connect(self.on_success_occurred)
                    compress_video_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        self.add_log('视频压缩失败，使用原始文件')
                        QApplication.processEvents()
                    else:
                        self.add_log('视频压缩完成')
                        QApplication.processEvents()

                    # 添加图片封面
                    final_output_path = watermark_output_path.replace('_2.mp4', '.mp4')
                    # 添加视频封面工作流
                    addPicWorker = AddPicWorker(watermark_output_path, pic_title_video, 'white.png', pic_title_ass,
                                                final_output_path)
                    self.thread_pool.start(addPicWorker)
                    addPicWorker.signals.finished.connect(self.on_success_occurred)
                    addPicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    # 移除中间视频
                    if os.path.exists(video_file_path):
                        os.remove(video_file_path)

                    if os.path.exists(watermark_output_path):
                        os.remove(watermark_output_path)

                    if os.path.exists(output_bgm_video_path):
                        os.remove(output_bgm_video_path)

                    if os.path.exists(temp_compressed_path):
                        os.remove(temp_compressed_path)

                    data_dict = {
                        "标题": video_title.replace('|', ''),
                        "标签": video_tag,
                        "文件路径": final_output_path.replace('/', '\\'),
                        "描述": ','.join(video_text),
                        "封面路径": "",
                        "图片集合": "",
                        "关联商品": "",
                        "分区分类": "旅游",
                        "备注": ""
                    }

                    write_to_old_excel(excel_file_path, data_dict)

                    # 上传任务信息
                    # 账号姓名
                    # account_name = self.accountNameLineEdit.text()
                    # 账号account
                    account_result = self.get_upload_accounts(account_name)

                    # 上传任务
                    if len(account_result) > 0:
                        for (account, mac) in account_result:
                            print(account)
                            task_param = {
                                'name': account_name,
                                'account': account,
                                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'title': data_dict.get('标题'),
                                'mac': mac,
                                'tag': data_dict.get('标签'),
                                'path': data_dict.get('文件路径'),
                                'describe': data_dict.get('描述'),
                                'classify': data_dict.get('分区分类'),
                                'task_type': 7,
                            }
                            add_user_task(task_param)
                            self.add_log(f'{account_name}{account}上传视频任务:{final_output_path}')
                            QApplication.processEvents()

                    self.run_label.setText(f'生成完成一个视频:{final_output_path}')
                else:
                    logging.debug(f'匹配的视频与文案数量不一致')
                    print('匹配的视频与文案数量不一致')
                    unSuccessCopy = str(timestamp) + '_copy.xlsx'
                    unSuccessLabel = str(timestamp) + '_label.xlsx'
                    notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                    notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
                    notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
                    # 记入未匹配的文案和视频标签
                    write_arrays_to_excel(notSuccess_copy_folder_path, video_title_text[0:-1])
                    write_arrays_to_excel(notSuccess_label_folder_path, label_text[0:-1])
                    self.add_log(f'跳过一个脚本文案，可能是没有匹配到视频，已记录')
                    QApplication.processEvents()

            # 删除cut video缓存
            clean_cut_cache()
            clean_cache()
            copy_start_num += 1
            label_start_num += 1

        current_directory = os.getcwd()
        unSuccessCopy = str(timestamp) + '_copy.xlsx'
        unSuccessLabel = str(timestamp) + '_label.xlsx'
        notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
        notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
        notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
        if os.path.exists(notSuccess_copy_folder_path) and os.path.exists(notSuccess_label_folder_path):
            self.add_log('有视频记录没有生成完毕，可补充素材后点击继续生成')
            QApplication.processEvents()
            self.copyFileLabel.setText(notSuccess_copy_folder_path)
            self.labelFilelabel.setText(notSuccess_label_folder_path)
        else:
            self.add_log('所有视频记录已经生成完毕，无记录可生成')
            QApplication.processEvents()

    # 问答知识类
    def compositeQaVideo(self, copy_file, label_file, out_dir_path, account_name):
        # if self.saveVideoPathLabel.text() == '':
        #     QMessageBox.information(self, "提示", f"请选择视频保存路径")
        #     return

        self.add_log('开始合成根据文案合成视频')
        QApplication.processEvents()

        # 时间
        timestamp = int(time.time())

        self.all_setting_dict = read_dict_from_txt('setting.txt')

        if not os.path.exists(self.all_setting_dict['end_video']['end_video_path']):
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                                     QMessageBox QLabel {
                                     background-color: rgb(22, 23, 25);
                                     color: rgb(255, 255, 255);
                                    }
                                    QMessageBox {
                                    background-color: rgb(22, 23, 25);
                                    color: rgb(255, 255, 255);
                                    }
                                """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"请选择视频添加的片尾")
            msg_box.exec()
            return

        # 删除video缓存
        clean_cut_cache()
        clean_cache()

        # copy 起始行
        copy_start_num = get_first_data_row(copy_file)

        # label 起始行
        label_start_num = get_first_data_row(label_file)

        self.add_log(f'读取视频文案,文案文件路径是{str(copy_file)},标签文件路径是{str(label_file)}')
        QApplication.processEvents()

        if copy_start_num == -1 or label_start_num == -1 or copy_start_num is None or label_start_num is None:
            self.add_log('文案文件或者标签文件没有数据可读，结束合成视频')
            QApplication.processEvents()
            return

        while True:

            if self.randomVideoModelCheckBox.isChecked():
                model_result = get_random_video_model()
                model_set_dict = json.loads(model_result['model_set'])
                self.all_setting_dict['title_set'] = model_set_dict['title_set']
                self.all_setting_dict['part_title_set'] = model_set_dict['part_title_set']
                self.all_setting_dict['srt_set'] = model_set_dict['srt_set']
                self.all_setting_dict['voice_set'] = model_set_dict['voice_set']
                self.all_setting_dict['part_title_part_0_set'] = model_set_dict['part_title_part_0_set']
                self.all_setting_dict['part_title_part_1_set'] = model_set_dict['part_title_part_1_set']
                self.all_setting_dict['part_title_part_2_set'] = model_set_dict['part_title_part_2_set']
                self.all_setting_dict['part_title_part_3_set'] = model_set_dict['part_title_part_3_set']
                self.all_setting_dict['part_title_part_4_set'] = model_set_dict['part_title_part_4_set']
                self.all_setting_dict['part_title_part_5_set'] = model_set_dict['part_title_part_5_set']

            # tts 速度
            speed_value = str(self.all_setting_dict['voice_set']['spd_0'])
            if not str(speed_value).startswith('-'):
                speed_value = '+' + speed_value
            speed_value = speed_value + '%'

            # 获取音频设置
            audio_setting = {
                'api_type': self.all_setting_dict['voice_set']['api_type'],
                'audio_role': self.audio_role_list[self.all_setting_dict['voice_set']['role_0']],
                'speed_value': speed_value,
                'volume_value': self.all_setting_dict['voice_set']['vol_0']
            }

            if self.all_setting_dict['voice_set']['api_type'] == 1:
                # 获取音频设置
                audio_setting = {
                    'api_type': self.all_setting_dict['voice_set']['api_type'],
                    'audio_role': int(
                        self.audio_bd_role_list[self.all_setting_dict['voice_set']['role_1']].split(':')[1]),
                    'speed_value': self.all_setting_dict['voice_set']['spd_1'],
                    'volume_value': self.all_setting_dict['voice_set']['vol_1'],
                    'tone_value': self.all_setting_dict['voice_set']['pit_1']
                }

            # 获取视频文案
            video_title_text = get_row_data(copy_file, copy_start_num)

            self.add_log('读取视频文案')
            QApplication.processEvents()

            # video_title_text.append('记得点赞关注评论')

            # 获取视频标签
            label_text = get_row_data(label_file, label_start_num)

            self.add_log(f'读取视频标签，{"&&".join(video_title_text)}，{"&&".join(label_text)}')
            QApplication.processEvents()

            if len(video_title_text) < 3:
                self.add_log('全部生成完成')
                QApplication.processEvents()
                break

            # 去除片尾
            # label_text.append('点赞,关注,评论')

            # 标题
            video_title = video_title_text[0].strip()

            # 标签
            video_tag = video_title_text[1].strip()

            # 文案
            video_text = video_title_text[2:]

            # 文案段数
            video_text_part_num = len(video_text)
            if video_text_part_num <= 2:
                # 删除cut video缓存
                clean_cut_cache()
                clean_cache()
                copy_start_num += 1
                label_start_num += 1
                logging.debug(f'合成一个视频失败')
                continue

            # try:
            #     # 处理空格
            #     for i, part_video_text in enumerate(video_text):
            #
            #         part_video_text_list = part_video_text.split(' ')
            #
            #         part_label_text_list = label_text[i].split(',')
            #
            #         if (part_label_text_list[0] not in part_video_text_list[0] and i != 0
            #                 and i != len(video_text) - 1 and i != len(video_text) - 2):
            #             part_video_text_list = [part_video_text_list[0] + part_video_text_list[1]] + part_video_text_list[2:]
            #             video_text[i] = ' '.join(part_video_text_list)
            # except Exception as e:
            #     print(f'可能不符合格式要求{e}')
            #     clean_cache()
            #     copy_start_num += 1
            #     label_start_num += 1
            #     continue

            # 视频处理缓存文件夹
            tamp_folder_name = 'tempConcateVideo'
            current_directory = os.getcwd()
            tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
            video_tamp_path_name = 'video_cache_file'
            video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)

            if len(video_text) > 0:

                # 素材缓存路径
                part_video_list = []

                # 字幕缓存路径
                part_srt_ass_list = []

                # 音频缓存路径
                part_audio_list = []

                # 标题缓存路径
                part_title_ass_list = []

                # 配音初始字幕生成-----------------------------------------------------------
                product_worker = SaDHWorker(video_text, audio_setting)
                self.thread_pool.start(product_worker)
                # 事件循环
                product_worker.signals.finished.connect(self.on_success_occurred)
                product_worker.signals.errorOccurred.connect(self.on_error_occurred)
                self.loop.exec()
                if self.error_flag:
                    # 删除cut video缓存
                    clean_cut_cache()
                    clean_cache()
                    copy_start_num += 1
                    label_start_num += 1
                    logging.debug(f'合成一个视频失败')
                    continue
                time.sleep(1)
                self.add_log('ai分析文案，已经为视频生成字幕配音即标签')
                QApplication.processEvents()

                # 生成标题、小标题以及字幕的ass文件-----------------------------------------------------------
                # 封面帧字幕获取
                pic_title_ass = ''
                pic_title_video = ''

                for i in range(video_text_part_num):

                    srt_file_name = f"temp_subtitle{i}.srt"

                    audio_file_name = f"temp_final_audio{i}.mp3"

                    # 原字幕文件
                    part_subtitle_url = os.path.join(video_tamp_path, srt_file_name)

                    # ass字幕文件
                    output_path = part_subtitle_url.replace('.srt', '.ass')

                    # 标题字幕文件
                    output_title_path = part_subtitle_url.replace('.srt', '_title.ass')

                    # 音频文件
                    output_audio_path = os.path.join(video_tamp_path, audio_file_name)

                    # 转换成ass
                    convert_srt_to_ass(part_subtitle_url, output_path, self.all_setting_dict['srt_set'])

                    # # 旅游景点介绍类
                    # if i == 0 or i == video_text_part_num - 1:
                    #     remove_all_dialogue_text(output_path)
                    #
                    # if i != 0 and i != video_text_part_num - 1 and i != video_text_part_num - 2:
                    #     remove_dialogue_text(output_path)

                    # if i == 0 and len(video_title) <= 20:
                    #     remove_dialogue_text(output_path)

                    # 去除片尾
                    # if i == video_text_part_num - 1:
                    #     remove_all_dialogue_text(output_path)

                    # if i != video_text_part_num - 1 and i != video_text_part_num - 2 and i != 0:
                    #     remove_dialogue_text(output_path)

                    # 转换完成后 记录ass字幕位置
                    part_srt_ass_list.append(output_path)

                    # 记录音频位置
                    part_audio_list.append(output_audio_path)

                    # 创建标题ass，包括大标题和小标题
                    # if i == 0 and len(video_title) <= 20:
                    #     self.pic_time = create_title(self.all_setting_dict, '1',
                    #                                  self.screenComboBox.currentIndex(),
                    #                                  video_title, output_title_path, part_subtitle_url)
                    # elif i == 0 and len(video_title) > 20:
                    #     self.pic_time = 0.8
                    #
                    # elif i != video_text_part_num - 1 and i != video_text_part_num - 2 and i != 0:
                    #     part_title = label_text[i].split(',')[0]
                    #     create_title(self.all_setting_dict, '2', self.screenComboBox.currentIndex(),
                    #                  part_title, output_title_path,
                    #                  part_subtitle_url)
                    if i == 0:
                        # 封面帧
                        output_title_path = part_subtitle_url.replace('.srt', '_pic_title.ass')
                        self.pic_time = create_title(self.all_setting_dict, '1',
                                                     self.screenComboBox.currentIndex(),
                                                     video_title, output_title_path, part_subtitle_url)

                        if os.path.exists(output_title_path):
                            pic_title_ass = output_title_path

                    # if i != video_text_part_num - 1 and i != video_text_part_num - 2:
                    #     part_title_ass_list.append(output_title_path)

                    self.add_log('视频样式字幕已生成')
                    QApplication.processEvents()

                    # 匹配视频素材-----------------------------------------------------------
                    # 视频片段标签
                    part_video_tags = label_text[i].split(',')

                    # 片段配音
                    part_audio_url = output_audio_path

                    # 配音时长
                    audio_length = get_audio_length(part_audio_url)

                    video_path = ''

                    # if i == video_text_part_num - 1:
                    #     video_path = self.all_setting_dict['end_video']['end_video_path']
                    #     # if os.path.exists(video_path):
                    #     #     part_video_list.append(video_path)
                    # else:
                    # 匹配视频重复
                    unSuccessVideoLabel = str(timestamp) + '_videoLabel.xlsx'
                    notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                    notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessVideoLabel)
                    if i == 0:
                        # 片头随机匹配视频封面素材
                        self.add_log('正在为视频匹配封面素材')
                        QApplication.processEvents()
                        # cover_time = 0
                        zm_times = parse_srt_num_time(part_subtitle_url)
                        zm_num = len(zm_times)

                        cover_video_path_list = []
                        cover_video_id_list = []
                        # 特殊标签处理
                        title_keyword_list = ai_analyse_title_special_tag(video_title, video_text)
                        if len(title_keyword_list) <= 0:
                            #  ai分析标题获取其关键词
                            title_keyword_list = ai_analyse_title_usual_tag(video_title, video_text)
                            self.add_log('ai分析标题获取其关键词:' + ','.join(title_keyword_list))
                            QApplication.processEvents()
                        if len(title_keyword_list) <= 0:
                            #  标题获取其分词
                            title_keyword_list = title_keyword(video_title)
                            self.add_log('标题获取其分词' + ','.join(title_keyword_list))
                            QApplication.processEvents()
                        for zm_i in range(zm_num):
                            try:
                                # 智能封面选择：收集所有关键词候选再随机选择
                                # title_keyword_list = title_keyword(video_title)
                                ftp_cover_video_id = get_cover_video_collect_all(title_keyword_list, '普通素材')
                                if ftp_cover_video_id in cover_video_id_list:
                                    ftp_cover_video_id = get_random_cover_video_by_cate('普通素材')
                                video_path = download_cover_video(ftp_cover_video_id)
                                cut_video_path = cut_video_by_audio_length(video_path, ftp_cover_video_id,
                                                                           math.ceil(zm_times[zm_i]))
                                if os.path.exists(cut_video_path):
                                    if pic_title_video == '':
                                        pic_title_video = cut_video_path
                                    cover_video_id_list.append(ftp_cover_video_id)
                                    cover_video_path_list.append(cut_video_path)
                            except Exception as e:
                                self.add_log(f'封面素材处理失败：{e}')
                                break
                        if len(cover_video_path_list) < zm_num:
                            failure_reason = get_last_material_download_error() or '封面素材未能完成下载或裁剪'
                            self.add_log(f'封面素材处理失败：{failure_reason}，退出合成')
                            QApplication.processEvents()
                            return

                        # 音频时长截取视频内容
                        time.sleep(1)
                        merge_video_path = merge_videos(cover_video_path_list,
                                                        '_'.join(map(str, cover_video_id_list)))

                        if os.path.exists(merge_video_path):
                            self.add_log(f'正在匹配素材，已经为视频匹配了{len(part_video_list) + 1}个素材')
                            QApplication.processEvents()

                            part_video_list.append(merge_video_path)
                        else:
                            self.add_log(f'下载合并视频素材失败')
                            QApplication.processEvents()
                            return
                    # # 片尾随机匹配视频脚本中某个关键字的景点视频 去除片尾 点赞关注评论 修改匹配逻辑
                    # elif i == video_text_part_num - 1:
                    #     self.add_log('正在为视频匹配片尾素材')
                    #     QApplication.processEvents()
                    #     sights_word_key = label_text[random.randint(1, video_text_part_num - 3)].split(',')[0]
                    #     ftp_videos = get_videos_by_keyword_1(sights_word_key, self.screenComboBox.currentIndex()
                    #                                          , self.locationlineEdit.text().strip(), audio_length)
                    #     sights_word_key = re.sub(r'[^\w\s]', '', sights_word_key)
                    #     if len(ftp_videos) <= 0:
                    #         # 没有匹配上素材，ai获取同义词，同地名的不同名称,尝试生成5次
                    #         synonyms_list = []
                    #         try_time = 0
                    #
                    #         synonyms_list = ai_get_synonym_words(sights_word_key)
                    #
                    #         if len(synonyms_list) > 0:
                    #             for synonym_word in synonyms_list:
                    #                 sights_word_key = synonym_word
                    #                 ftp_videos = get_videos_by_keyword_1(sights_word_key,
                    #                                                      self.screenComboBox.currentIndex(),
                    #                                                      self.locationlineEdit.text().strip(),
                    #                                                      audio_length)
                    #                 if len(ftp_videos) > 0:
                    #                     break
                    #     ftp_video_ids = [video['id'] for video in ftp_videos]
                    #     if len(ftp_videos) > 0:
                    #         video_id = random.choice(ftp_video_ids)
                    #         video_path = download_cn_video(video_id, self.screenComboBox.currentIndex())
                    #         # 音频时长截取视频内容
                    #         cut_video_path = cut_video_by_audio_length(video_path, video_id, audio_length)
                    #         if os.path.exists(cut_video_path):
                    #             self.add_log(f'正在匹配素材，已经为视频匹配了{len(part_video_list) + 1}个素材')
                    #             QApplication.processEvents()
                    #
                    #             part_video_list.append(cut_video_path)
                    #         else:
                    #             self.add_log(f'下载素材失败')
                    #             QApplication.processEvents()
                    else:
                        self.add_log('正在为视频匹配素材')
                        QApplication.processEvents()
                        # 普通片段匹配视频
                        while True:
                            ftp_video_List = []
                            # 地区景区匹配到的id
                            location_id_list = []
                            for n, tag in enumerate(part_video_tags):
                                if len(location_id_list) == 0 and n == 0:
                                    # 去除tag中所有标点符号
                                    tag = re.sub(r'[^\w\s]', '', tag)

                                    # 尝试关键字匹配视频，未匹配上Ai处理更换同义关键字再进行匹配
                                    ftp_videos = get_videos_by_keyword_1(tag, self.screenComboBox.currentIndex(),
                                                                         self.locationlineEdit.text().strip(),
                                                                         audio_length, 20)

                                    synonyms_list = []

                                    if len(ftp_videos) <= 0:
                                        print('缺少该关键字的素材')
                                        # part_video_tags.append(str(audio_length))
                                        # 记入未匹配的文案和视频标签

                                        lost_video_param = {
                                            'title': part_video_tags[0],
                                            'firstTags': '_'.join(synonyms_list) + '_'.join(part_video_tags),
                                            'secondTags': '',
                                            'videoLength': audio_length,
                                            'screen': self.screenComboBox.currentIndex(),
                                            'accountName': account_name,
                                            'titleType': '9'
                                        }
                                        # 将缺少的视频信息记入库中
                                        add_lost_cn_video_record(lost_video_param)

                                        # 将缺少的视频信息记入表中
                                        write_arrays_to_excel(notSuccess_label_folder_path, part_video_tags)
                                        break

                                    for video in ftp_videos:
                                        location_id_list.append(video['id'])

                                elif len(location_id_list) > 0:
                                    ftp_videos = get_videos_by_keyword(tag, self.screenComboBox.currentIndex(),
                                                                       self.locationlineEdit.text().strip(),
                                                                       location_id_list, audio_length)
                                else:
                                    ftp_videos = []

                                # 提取视频ID列表
                                if len(ftp_videos) > 0:
                                    ftp_ideo_ids = [video['id'] for video in ftp_videos]
                                    if len(ftp_ideo_ids) <= 0:
                                        continue
                                    ftp_video_List.append(ftp_ideo_ids)

                            # 没有素材退出匹配
                            if len(ftp_video_List) <= 0:
                                print('缺少该素材，退出合成')
                                self.add_log(f'缺少该素材，退出合成')
                                QApplication.processEvents()
                                return

                            # if len(ftp_video_List) == 1:
                            #     video_id = random.choice(ftp_video_List[0])
                            # else:
                            #     video_id = count_and_sort(ftp_video_List)

                            # 素材id 交叉组合后选择出现频率最高的
                            id_array = count_and_sort_to_array(ftp_video_List)

                            # 根据字幕
                            zm_times = parse_srt_num_time(part_subtitle_url)

                            if len(id_array) < len(zm_times):
                                select_id_array = id_array
                            else:
                                select_id_array = id_array[0:len(zm_times)]

                            try:
                                # 记录下载好的视频位置
                                video_path_list = []
                                video_id = ''
                                # 下载视频
                                for n, vid in enumerate(select_id_array):
                                    video_path = download_cn_video(vid, self.screenComboBox.currentIndex())
                                    cut_video_path = cut_video_by_audio_length(video_path, vid, math.ceil(zm_times[n]))
                                    if os.path.exists(cut_video_path):
                                        video_path_list.append(cut_video_path)
                                    video_id = video_id + '_' + str(vid)
                                    # 打印下载的视频id
                                    logging.debug(f'下载的视频id为{vid}的视频路径为{video_path}')

                                # 合并视频
                                merge_video_path = merge_videos(video_path_list,
                                                                '_'.join(map(str, select_id_array)))

                                time.sleep(1)

                                # # 音频时长截取视频内容
                                # cut_video_path = cut_video_by_audio_length(merge_video_path, video_id, audio_length)

                                logging.debug(f'这个下载处理后的视频{merge_video_path}的')

                                if os.path.exists(merge_video_path):
                                    logging.debug(f'确认存在下载的视频{merge_video_path}')
                                    self.add_log(
                                        f'正在匹配素材，已经为视频匹配了{len(part_video_list) + 1}个景点')
                                    QApplication.processEvents()

                                    part_video_list.append(merge_video_path)
                                    break
                                else:
                                    self.add_log(f'下载素材失败')
                                    QApplication.processEvents()
                                    break
                            except Exception as e:
                                logging.debug(f'这个下载的视频{video_path}的错误{str(e)}')
                                self.add_log(f'下载素材异常：{str(e)}，跳出该段匹配')
                                QApplication.processEvents()
                                break

                            # try_num += 1

                # 如果素材数量和文案一样，就进行合成 未处理成功
                video_file_path = ''
                if len(part_video_list) == video_text_part_num:
                    transitionSetting = {
                        'transitionNum': 0,
                        'transitionTime': 0
                    }
                    saveVideoPath = out_dir_path

                    video_id_path_name = 'video_id.xlsx'
                    # 任务文件输出路径
                    video_id_excel_file_path = os.path.join(saveVideoPath, video_id_path_name)

                    # 记录每个视频匹配的素材
                    write_arrays_to_excel(video_id_excel_file_path, [video_title] + part_video_list)

                    # 输出路径
                    video_name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', video_title) + '_0.mp4'

                    video_file_path = os.path.join(saveVideoPath, video_name)

                    excel_file_path_name = '1.xls'
                    # 任务文件输出路径
                    excel_file_path = os.path.join(saveVideoPath, excel_file_path_name)

                    composite_worker = CompositeVideo(part_video_list, part_audio_list, part_srt_ass_list,
                                                      part_title_ass_list, video_file_path,
                                                      transitionSetting, self.pic_time)

                    self.add_log('正在合成一个视频。。。')
                    QApplication.processEvents()

                    self.thread_pool.start(composite_worker)
                    # 创建一个事件循环
                    composite_worker.signals.finished.connect(self.on_success_occurred)
                    composite_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()
                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'合成一个视频失败')
                        continue

                    self.add_log('已经合成一个视频，接下来进行后期处理。')
                    QApplication.processEvents()

                    if not os.path.exists(video_file_path):
                        self.add_log('没有已经合成一个视频，跳过。')
                        QApplication.processEvents()
                        continue

                    # 匹配添加音乐
                    parent_dir = os.getcwd()
                    # 构造同级的缓存文件夹路径
                    cache_music_dir_path = os.path.join(parent_dir, 'cacheMusic')
                    # 获取文件夹中的所有MP3文件
                    mp3_files = [f for f in os.listdir(cache_music_dir_path) if
                                 f.endswith('.mp3') or f.endswith('.MP3')]

                    # 如果文件夹中有MP3文件，则随机选择一个
                    if mp3_files:
                        random_mp3_file = random.choice(mp3_files)
                        random_mp3_file_path = os.path.join(cache_music_dir_path, random_mp3_file)
                        print(f"随机选择的MP3文件路径为：{random_mp3_file_path}")
                    else:
                        print("文件夹中没有找到MP3文件,缺少音乐。")
                        break

                    # 加载音频文件
                    # audio = AudioSegment.from_file(mp4_files)

                    # 获取音乐音频的音量（响度）
                    # music_volume = audio.dBFS  # 返回音频的响度，单位为分贝
                    # mb_db = 20.0
                    bgAudioVolume = 40
                    output_bgm_video_path = video_file_path.replace('_0.mp4', '_1.mp4')
                    addMusicWorker = AddMusicWorker(video_file_path, random_mp3_file_path, 100, bgAudioVolume,
                                                    output_bgm_video_path)

                    self.thread_pool.start(addMusicWorker)
                    # 创建一个事件循环
                    addMusicWorker.signals.finished.connect(self.on_success_occurred)
                    addMusicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加音乐失败')
                        continue

                    self.add_log('后期处理,已添加音乐。')
                    QApplication.processEvents()

                    # 添加水印
                    watermark_location_examples = [['50', '50'], ['main_w-overlay_w-100', '50'],
                                                   ['50', 'main_h-overlay_h-50'],
                                                   ['main_w-overlay_w-50', 'main_h-overlay_h-50'],
                                                   ['(main_w-overlay_w)/2', '(main_h-overlay_h)/2'],
                                                   ['(main_w-overlay_w)/2', '50'],
                                                   ['(main_w-overlay_w)/2', 'main_h-overlay_h-100']]

                    watermark_setting = {
                        'watermark_location': watermark_location_examples[
                            self.all_setting_dict['water_set']['position']],
                        'zoom_size': self.all_setting_dict['water_set']['zoom'],
                        'pic_alpha': self.all_setting_dict['water_set']['alpha']
                    }
                    watermark_output_path = output_bgm_video_path.replace('_1.mp4', '_2.mp4')
                    add_text_watermark_worker = AddWatermarkWorker(output_bgm_video_path, watermark_output_path,
                                                                   watermark_setting, 2,
                                                                   self.all_setting_dict['water_set']['filePath'])
                    self.thread_pool.start(add_text_watermark_worker)
                    # 创建一个事件循环
                    add_text_watermark_worker.signals.finished.connect(self.on_success_occurred)
                    add_text_watermark_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        # 删除cut video缓存
                        clean_cut_cache()
                        clean_cache()
                        copy_start_num += 1
                        label_start_num += 1
                        logging.debug(f'添加水印失败')
                        continue

                    self.add_log('后期处理,已添加水印。')
                    QApplication.processEvents()

                    # 视频压缩
                    temp_compressed_path = watermark_output_path.replace('_2.mp4', '_temp_compressed.mp4')
                    compress_video_worker = CompressVideoWorker(watermark_output_path, temp_compressed_path)

                    self.thread_pool.start(compress_video_worker)
                    compress_video_worker.signals.finished.connect(self.on_success_occurred)
                    compress_video_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        self.add_log('视频压缩失败，使用原始文件')
                        QApplication.processEvents()
                    else:
                        self.add_log('视频压缩完成')
                        QApplication.processEvents()

                    # 添加图片封面
                    final_output_path = watermark_output_path.replace('_2.mp4', '.mp4')
                    # 添加视频封面工作流
                    addPicWorker = AddPicWorker(watermark_output_path, pic_title_video, 'white.png', pic_title_ass,
                                                final_output_path)
                    self.thread_pool.start(addPicWorker)
                    addPicWorker.signals.finished.connect(self.on_success_occurred)
                    addPicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    # 移除中间视频
                    if os.path.exists(video_file_path):
                        os.remove(video_file_path)

                    if os.path.exists(watermark_output_path):
                        os.remove(watermark_output_path)

                    if os.path.exists(output_bgm_video_path):
                        os.remove(output_bgm_video_path)

                    if os.path.exists(temp_compressed_path):
                        os.remove(temp_compressed_path)

                    data_dict = {
                        "标题": video_title.replace('|', ''),
                        "标签": video_tag,
                        "文件路径": final_output_path.replace('/', '\\'),
                        "描述": ','.join(video_text),
                        "封面路径": "",
                        "图片集合": "",
                        "关联商品": "",
                        "分区分类": "旅游",
                        "备注": ""
                    }

                    write_to_old_excel(excel_file_path, data_dict)

                    # 上传任务信息
                    # 账号姓名
                    # account_name = self.accountNameLineEdit.text()
                    # 账号account
                    account_result = self.get_upload_accounts(account_name)

                    # 上传任务
                    if len(account_result) > 0:
                        for (account, mac) in account_result:
                            print(account)
                            task_param = {
                                'name': account_name,
                                'account': account,
                                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'title': data_dict.get('标题'),
                                'mac': mac,
                                'tag': data_dict.get('标签'),
                                'path': data_dict.get('文件路径'),
                                'describe': data_dict.get('描述'),
                                'classify': data_dict.get('分区分类'),
                                'task_type': 0,
                            }
                            add_user_task(task_param)
                            self.add_log(f'{account_name}{account}上传视频任务:{final_output_path}')
                            QApplication.processEvents()

                    self.add_log(f'生成完成一个视频:{final_output_path}')
                    QApplication.processEvents()

                else:
                    logging.debug(f'匹配的视频与文案数量不一致')
                    print('匹配的视频与文案数量不一致')
                    unSuccessCopy = str(timestamp) + '_copy.xlsx'
                    unSuccessLabel = str(timestamp) + '_label.xlsx'
                    notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                    notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
                    notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
                    # 记入未匹配的文案和视频标签
                    write_arrays_to_excel(notSuccess_copy_folder_path, video_title_text[0:-1])
                    write_arrays_to_excel(notSuccess_label_folder_path, label_text[0:-1])
                    self.add_log('跳过一个脚本文案，可能是没有匹配到视频，已记录')
                    QApplication.processEvents()

            # 删除cut video缓存
            clean_cut_cache()
            clean_cache()
            copy_start_num += 1
            label_start_num += 1

        current_directory = os.getcwd()
        unSuccessCopy = str(timestamp) + '_copy.xlsx'
        unSuccessLabel = str(timestamp) + '_label.xlsx'
        notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
        notSuccess_copy_folder_path = os.path.join(notSuccess_folder_path, unSuccessCopy)
        notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessLabel)
        if os.path.exists(notSuccess_copy_folder_path) and os.path.exists(notSuccess_label_folder_path):
            try:
                self.add_log('有视频记录没有生成完毕，可补充素材后点击继续生成')
                QApplication.processEvents()
                self.copyFileLabel.setText(notSuccess_copy_folder_path)
                self.labelFilelabel.setText(notSuccess_label_folder_path)

                # 展示缺少的标签
                unSuccessVideoLabel = str(timestamp) + '_videoLabel.xlsx'
                notSuccess_folder_path = os.path.join(current_directory, 'notSuccess')
                notSuccess_label_folder_path = os.path.join(notSuccess_folder_path, unSuccessVideoLabel)
                # 读取整个工作表（默认第一张）
                df = _read_excel(notSuccess_label_folder_path)
                # 设置表格的行列数
                self.lostVideoTableWidget.setRowCount(df.shape[0])
                self.lostVideoTableWidget.setColumnCount(df.shape[1])

                # 获取水平表头视图
                horizontal_header = self.lostVideoTableWidget.horizontalHeader()

                # 设置表头样式表（背景色、文字颜色等）
                horizontal_header.setStyleSheet("""
                                                QHeaderView::section {
                                                    background-color: rgb(56, 56, 56);
                                                    color: white;                     
                                                    ont-weight: bold;          /* 文字加粗 */
                                                    border-right: 1px solid #ddd; /* 右侧边框 */
                                                    text-align: center;         /* 文字居中 */
                                                }
                                            """)
                vertical_header = self.lostVideoTableWidget.verticalHeader()

                vertical_header.setStyleSheet("""
                                                QHeaderView::section {
                                                    background-color: rgb(56, 56, 56);
                                                    color: white;                    
                                                    font-weight: bold;          /* 文字加粗 */
                                                    border-right: 1px solid #ddd; /* 右侧边框 */
                                                    text-align: center;         /* 文字居中 */
                                                }
                                            """)

                # 填充数据
                for row in range(df.shape[0]):
                    for col in range(df.shape[1]):
                        item = QTableWidgetItem(str(df.iat[row, col]))
                        self.lostVideoTableWidget.setItem(row, col, item)
                self.lostVideoTableWidget.resizeColumnsToContents()
            except Exception as e:
                print(f'展示缺少的标签错误{str(e)}')
                pass
        else:
            self.add_log('所有视频记录已经生成完毕，无记录可生成')
            QApplication.processEvents()

    # 图片攻略类
    # 图片攻略类视频合成
    def compositeImageIntroVideo(self, copy_file, label_file, out_dir_path, account_name):
        self.add_log('开始合成图片攻略类视频')
        QApplication.processEvents()

        # 计算文本的实际显示宽度（中文字符/全角标点=1，英文字符/数字/半角标点=0.5）
        def get_text_display_width(text):
            total_width = 0
            for char in text:
                # 中文字符
                if '\u4e00' <= char <= '\u9fff':
                    total_width += 1
                # 全角标点符号（与汉字同宽）- 含中文单双引号
                elif char in '，。、；：！？""''（）【】《》''""':
                    total_width += 1
                # 英文、数字、半角标点
                elif ('a' <= char <= 'z') or ('A' <= char <= 'Z') or ('0' <= char <= '9') or char in '.,;:?!-+*/()[]{}"<>\'':
                    total_width += 0.5
                else:
                    total_width += 1
            return total_width

        # 基于显示宽度的换行函数
        def smart_split_by_width(text, max_width, field_label):
            """按宽度强制换行：只按字数限制切分，不考虑标点"""
            lines = []
            remaining = text

            while remaining:
                # 如果剩余文本不超宽，直接作为最后一行
                if get_text_display_width(remaining) <= max_width:
                    lines.append(remaining.strip())
                    break

                # 计算每个字符的宽度，找到最大可容纳位置
                current_width = 0
                cut_pos = 0
                for i, char in enumerate(remaining):
                    if '\u4e00' <= char <= '\u9fff':
                        char_width = 1
                    elif ('a' <= char <= 'z') or ('A' <= char <= 'Z') or ('0' <= char <= '9') or char in '.,;:?!-+*/()[]{}"<>\'':
                        char_width = 0.5
                    else:
                        char_width = 1

                    # 【关键修复】使用 >= 确保不超出max_width
                    if current_width + char_width > max_width:
                        break
                    current_width += char_width
                    cut_pos = i + 1

                # 【安全检查】如果cut_pos为0，强制取第一个字符避免死循环
                if cut_pos == 0:
                    cut_pos = 1
                    
                # 切分行（强制按宽度切分）
                line = remaining[:cut_pos].strip()
                if line:
                    lines.append(line)
                remaining = remaining[cut_pos:].lstrip()

            return lines

        self.all_setting_dict = read_dict_from_txt('setting.txt')

        # 使用随机模板（在读取设置之后）
        if self.randomVideoModelCheckBox.isChecked():
            model_result = get_random_video_model()
            model_set_dict = json.loads(model_result['model_set'])
            self.all_setting_dict['title_set'] = model_set_dict['title_set']
            self.add_log(f'已应用随机视频模板，字体: {model_set_dict["title_set"]["fontFamily"]}')

        # 删除video缓存
        clean_cut_cache()
        clean_cache()

        # copy 起始行
        copy_start_num = get_first_data_row(copy_file)

        # label 起始行
        label_start_num = get_first_data_row(label_file)

        self.add_log(f'读取视频文案,文案文件路径是{str(copy_file)}')

        while True:
            # 获取视频文案
            video_title_text = get_row_data(copy_file, copy_start_num)

            self.add_log('读取视频文案')
            QApplication.processEvents()

            if len(video_title_text) < 3:
                self.add_log('全部生成完成')
                QApplication.processEvents()
                break

            # 标题 (视频标题,如"西安三日游")
            video_title = video_title_text[0].strip()

            # 标签
            video_fabu_tag = video_title_text[1].strip()

            # 视频标签
            label_text = get_row_data(label_file, label_start_num)

            # 文案 (从第3列开始是JSON格式的每日行程数据)
            video_text = video_title_text[2:]

            # 文案段数 (即天数)
            video_text_part_num = len(video_text)

            if video_text_part_num <= 0:
                copy_start_num += 1
                logging.debug(f'文案数据为空')
                continue

            # 解析JSON格式的行程数据
            day_data_list = []
            for json_str in video_text:
                try:
                    day_data = json.loads(json_str)
                    day_data_list.append(day_data)
                except json.JSONDecodeError as e:
                    self.add_log(f'解析行程数据失败: {e}')
                    QApplication.processEvents()
                    continue

            if not day_data_list:
                self.add_log('没有有效的行程数据')
                copy_start_num += 1
                continue

            # 视频处理缓存文件夹
            tamp_folder_name = 'tempConcateVideo'
            current_directory = os.getcwd()
            tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
            video_tamp_path_name = 'video_cache_file'
            video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)

            # 从数据库获取匹配的视频，截取背景图
            bg_image_path = os.path.join(video_tamp_path, f'bg_{copy_start_num}.jpg')
            bg_success = False

            try:
                # 调用 get_videos_by_keyword_1 获取视频
                # 参数: keyword, screen=1(竖屏), location="", audio_length=10, cate=None

                ftp_videos = []
                video_tag = ''
                for i in range(video_text_part_num):
                    video_tag = label_text[i].split(',')[0]  # 使用每段文案的第一个标签作为视频标签
                    ftp_videos = get_videos_by_keyword_1(
                        video_tag,
                        0,  # 竖屏
                        "",  # 不限制地区
                        10,  # 时长不重要，设为10秒
                    )
                    if ftp_videos and len(ftp_videos) > 0:
                        break

                if ftp_videos and len(ftp_videos) > 0:
                    # 随机选择一个视频
                    video_info = random.choice(ftp_videos)
                    video_id = video_info['id']

                    self.add_log(f'根据标签"{video_tag}"找到视频ID: {video_id}')
                    QApplication.processEvents()

                    # 下载视频
                    video_path = download_cn_video(video_id, 0)  # screen=0 表示竖屏

                    if video_path and os.path.exists(video_path):
                        self.add_log(f'视频下载成功: {video_path}')
                        QApplication.processEvents()

                        # 截取并虚化图片
                        from ffmpeg_tool.video_concat_tool import extract_and_blur_random_frame

                        if extract_and_blur_random_frame(
                            video_path,
                            bg_image_path,
                            target_width=1080,
                            target_height=1920,
                            blur_sigma=5  # 中度虚化
                        ):
                            self.add_log(f'背景图生成成功: {bg_image_path}')
                            QApplication.processEvents()
                            bg_success = True
                        else:
                            self.add_log(f'背景图生成失败')
                            QApplication.processEvents()

                        # 删除下载的视频
                        try:
                            os.remove(video_path)
                            self.add_log(f'已删除临时视频: {video_path}')
                            QApplication.processEvents()
                        except Exception as e:
                            print(f'删除视频失败: {str(e)}')
                    else:
                        self.add_log(f'视频下载失败')
                        QApplication.processEvents()
                else:
                    self.add_log(f'未找到匹配标签"{video_tag}"的视频')
                    QApplication.processEvents()

            except Exception as e:
                self.add_log(f'获取背景图时出错: {str(e)}')
                QApplication.processEvents()

            # 如果没有成功生成背景图，跳过当前视频
            if not bg_success:
                self.add_log(f'跳过当前视频（无法生成背景图）')
                QApplication.processEvents()
                copy_start_num += 1
                continue

            # 每页显示时长(至少8秒,根据内容长度适当调整)
            MIN_PAGE_DURATION = 8.0
            PAGE_DURATION = MIN_PAGE_DURATION

            # 计算每页内容长度,适当增加时长
            for day_data in day_data_list:
                content_length = 0
                for day_key, day_content in day_data.items():
                    if isinstance(day_content, dict):
                        for field_name, field_content in day_content.items():
                            content_length += len(str(field_content))
                if content_length > 300:
                    PAGE_DURATION = max(MIN_PAGE_DURATION, 10.0)
                    break
                if content_length > 500:
                    PAGE_DURATION = max(MIN_PAGE_DURATION, 12.0)
                    break

            self.add_log(f'计算每页显示时长: {PAGE_DURATION}秒')
            QApplication.processEvents()

            # 生成每页的视频和字幕
            page_video_list = []
            total_duration = 0

            for day_idx, day_data in enumerate(day_data_list):
                # 解析每天的标题和内容
                for day_key, day_content in day_data.items():
                    day_title = day_key  # 如 "Day1·临潼秦唐双璧之旅"
                    if isinstance(day_content, dict):
                        content_dict = day_content  # 包含四个字段的字典
                    else:
                        content_dict = {}
                        self.add_log(f'第{day_idx + 1}天数据格式错误')
                        continue

                # 定义颜色 - 优化后的配色方案（淡雅风格）
                # 总标题颜色 - 深棕色（突出且优雅）
                main_title_color = '#5D4037'  # 深棕色
                # 日期标题颜色 - 深青色（与总标题区分）
                date_title_color = '#00695C'  # 深青色
                # 四个字段标题颜色（各模块区分）- 全部多巴胺风格
                field_colors = {
                    '行程安排': '#4287F5',  # 亮紫色
                    '玩点亮点': '#FF4757',  # 珊瑚红
                    '特色美食': '#FFA500',  # 橙黄色
                    '注意事项': '#EF4444'   # 活力橙红
                }
                # 内容文字颜色 - 深灰色（高对比度）
                content_text_color = '#212121'  # 深灰色
                content_border_color = '#000000'  # 黑色

                # 3. 四个字段标题和内容 - 使用全局动态Y坐标，改成2页显示逻辑
                field_labels = ['行程安排', '玩点亮点', '特色美食', '注意事项']
                field_icons = {'行程安排': '🚗', '玩点亮点': '📍', '特色美食': '🍜', '注意事项': '⚠️'}
                content_pos_x = 40  # 向左移动，为内容留出更多空间
                line_height = 82  # 行高增大
                field_font_size = 64  # 字段标题字体再增大
                content_font_size = 56  # 内容字体再增大（从52增加到56）
                block_bg_height = 85  # 色块高度

                # === 安全边距设置 ===
                SCREEN_HEIGHT = 1920
                SAFE_MARGIN_BOTTOM = 180  # 底部安全边距180px
                MAX_Y_POSITION = SCREEN_HEIGHT - SAFE_MARGIN_BOTTOM  # 1770px

                # 【关键修复】标题占用的高度需要与实际渲染一致
                # 实际渲染逻辑：
                # 1. 初始Y = 340
                # 2. 总标题占位 = max(120, 标题行数 * 95 + 20)
                # 3. 日期标题占位 = 90
                # 为了简化估算，使用最大可能值（假设标题2行）：max(120, 2*95+20) = 210
                # 但这样估算会过于保守，导致可用空间变小
                # 解决方案：使用标题实际行数计算
                
                # 计算标题实际行数（与实际渲染使用相同逻辑）
                video_title_clean = video_title.replace('|', '').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
                title_max_width = 8
                title_width = get_text_display_width(video_title_clean)
                if title_width > title_max_width:
                    title_lines = smart_split_by_width(video_title_clean, title_max_width, '标题')
                    title_lines = title_lines[:2]  # 最多2行
                else:
                    title_lines = [video_title_clean]
                title_line_count = len(title_lines)
                
                # 计算标题实际占位高度（与实际渲染一致）
                line_height_title = 95
                title_total_height = title_line_count * line_height_title
                title_block_height = max(120, title_total_height + 20)  # 与实际渲染一致
                
                # 标题占用的高度（大标题占位 + 日期标题占位）
                START_Y_POSITION = 340 + title_block_height + 90  # 340是初始Y，90是日期标题占位

                # 调试：输出可用高度
                available_height_debug = MAX_Y_POSITION - START_Y_POSITION
                self.add_log(f'分页调试：屏幕高度={SCREEN_HEIGHT}, 安全边距={SAFE_MARGIN_BOTTOM}, 起始Y={START_Y_POSITION}, 标题行数={title_line_count}, 标题占位={title_block_height}, 可用高度={available_height_debug}px')
                QApplication.processEvents()

                # === 智能分页：字段级别，一个板块必须完整显示在一页 ===

                def parse_field_items(field_label, field_content):
                    """解析字段内容为item列表"""
                    items = []
                    if not field_content:
                        return items

                    merged = field_content.replace('\n', ' ').replace('\r', '')

                    if field_label in ['玩点亮点', '特色美食', '注意事项']:
                        items = [s.strip() for s in merged.split('；') if s.strip()]
                    else:
                        for line in merged.split('\n'):
                            line = line.strip()
                            if not line:
                                continue
                            if '；' in line:
                                items.extend([s.strip() for s in line.split('；') if s.strip()])
                            elif ';' in line:
                                items.extend([s.strip() for s in line.split(';') if s.strip()])
                            else:
                                items.append(line)
                    return items

                def estimate_item_height(item_text, field_label):
                    """估算单个item的渲染高度 - 使用与实际渲染完全一致的换行逻辑
                    
                    【重要】渲染流程是：先用原始文本换行 → 对每行清理特殊字符 → 显示
                    所以估算时也应该：先用原始文本换行（与渲染一致）
                    
                    注意：渲染时换行判断使用原始文本，但显示时用清理后的文本
                    这可能导致每行实际显示宽度超过换行判断宽度，但不影响行数
                    """
                    HANZI_WIDTH_18 = 13  # 必须与渲染时一致
                    
                    # 【关键修复】使用原始文本进行换行判断（与渲染一致）
                    # 渲染代码中：get_text_display_width(item) 和 smart_split_by_width(item, ...) 使用原始文本
                    
                    if field_label == '行程安排':
                        # 行程安排：第一行和后续行宽度不同（与实际渲染逻辑完全一致）
                        first_line_max_width = HANZI_WIDTH_18 - 2  # 第一行（有序号，少2字）
                        other_line_max_width = HANZI_WIDTH_18      # 后续行（无序号，多2个字）
                        
                        # 使用原始文本进行换行判断（与渲染一致）
                        item_width = get_text_display_width(item_text)
                        
                        if item_width <= first_line_max_width:
                            line_count = 1
                        else:
                            # 使用原始文本换行
                            first_lines = smart_split_by_width(item_text, first_line_max_width, field_label)
                            first_line = first_lines[0] if first_lines else ''
                            line_count = 1
                            remaining = item_text[len(first_line):].strip() if first_line else item_text.strip()
                            if remaining:
                                remaining_lines = smart_split_by_width(remaining, other_line_max_width, field_label)
                                line_count += len(remaining_lines)
                    else:
                        # 其他板块：所有行宽度一致（与实际渲染逻辑完全一致）
                        max_width = HANZI_WIDTH_18
                        # 使用原始文本进行换行判断（与渲染一致）
                        item_width = get_text_display_width(item_text)
                        if item_width > max_width:
                            lines = smart_split_by_width(item_text, max_width, field_label)
                            line_count = len(lines)
                        else:
                            line_count = 1

                    return line_count * line_height

                def estimate_field_total_height(field_label, field_content):
                    """估算整个字段的总高度（包含卡片边距）"""
                    items = parse_field_items(field_label, field_content)
                    card_padding = 30  # 卡片内边距

                    if not items:
                        # 空字段：上下内边距 + 标题栏高度
                        return card_padding + block_bg_height + card_padding + 30

                    # 卡片总高度 = 上内边距 + 标题栏 + 间距 + 内容 + 下内边距 + 模块间距
                    total_height = card_padding  # 上内边距
                    total_height += block_bg_height  # 标题栏
                    total_height += 30  # 标题与内容间距
                    for item in items:
                        total_height += estimate_item_height(item, field_label)
                    total_height += card_padding  # 下内边距
                    total_height += 30  # 模块底部间距
                    return total_height

                # 构建页面数据结构（紧凑显示模式：充分利用每页空间，字段可跨页）
                # 每个页面包含: [{'field': '行程安排', 'items': [...]}, ...]
                pages_data = []
                current_page_data = []
                current_page_height = 0
                available_height = MAX_Y_POSITION - START_Y_POSITION

                # 卡片头部高度（上内边距+标题栏+标题与内容间距）
                # 必须与 estimate_field_total_height 中的计算一致
                card_header_height = 30 + block_bg_height + 30  # 30(上内边距) + 85(标题栏) + 30(间距) = 145
                
                # 卡片底部间距（下内边距+模块间距）
                # 必须与 estimate_field_total_height 中的计算一致
                # estimate_field_total_height: total_height += card_padding(30) + 30(模块间距)
                card_footer_spacing = 30 + 30  # 下内边距 + 模块间距 = 60

                # 遍历每个字段
                for field_idx, field_label in enumerate(field_labels):
                    field_content = content_dict.get(field_label, '')
                    items = parse_field_items(field_label, field_content)
                    field_total_height = estimate_field_total_height(field_label, field_content)

                    # 调试：输出每个板块的详细信息
                    self.add_log(f'分页调试：板块"{field_label}"，内容长度={len(field_content) if field_content else 0}，items数={len(items)}，估算高度={field_total_height}px，当前页已用高度={current_page_height}px')
                    if items:
                        for i, item in enumerate(items[:3]):  # 只显示前3个
                            self.add_log(f'  item{i}: {str(item)[:50]}...')
                    QApplication.processEvents()

                    # 跳过没有内容的字段（不创建空卡片）
                    if not items:
                        self.add_log(f'分页调试：板块"{field_label}"没有内容，跳过')
                        QApplication.processEvents()
                        continue

                    # 检查是否能完整放入当前页
                    if current_page_height + field_total_height <= available_height:
                        # 能完整放下，加入当前页
                        current_page_data.append({
                            'field': field_label,
                            'items': items
                        })
                        current_page_height += field_total_height
                        self.add_log(f'分页调试：板块"{field_label}"完整加入当前页，当前页高度={current_page_height}px')
                        QApplication.processEvents()
                    else:
                        # 放不下完整字段，尝试拆分items到当前页和下一页
                        remaining_space = available_height - current_page_height
                        
                        # 检查剩余空间是否至少能放下卡片头部+一个item
                        if remaining_space >= card_header_height + line_height:
                            self.add_log(f'分页调试：板块"{field_label}"拆分显示，剩余空间{remaining_space}px')
                            QApplication.processEvents()
                            
                            # 计算当前页能放多少个items
                            # 【关键修复】current_items_height 初始值应该为 0，因为只跟踪内容高度
                            # 卡片头部高度(card_header_height)和底部间距(card_footer_spacing)会在最后加上
                            current_page_items = []
                            next_page_items = []
                            current_items_height = 0  # 只跟踪内容高度
                            
                            # 【调试】输出详细的判断过程
                            self.add_log(f'分页调试：开始拆分板块"{field_label}"，共{len(items)}个items，剩余空间={remaining_space}px，卡片头部={card_header_height}px，底部间距={card_footer_spacing}px')
                            
                            for original_idx, item in enumerate(items):
                                item_height = estimate_item_height(item, field_label)
                                # 【调试】输出每个item的判断细节
                                check_height = card_header_height + current_items_height + item_height + card_footer_spacing
                                can_fit = check_height <= remaining_space
                                self.add_log(f'  item{original_idx}: 估算高度={item_height}px，总高度={check_height}px，能放入={can_fit}，内容="{str(item)[:30]}..."')
                                
                                # 【关键修复】检查是否能放入：头部高度 + 内容高度 + 底部间距 <= 剩余空间
                                if can_fit:
                                    # 能放下，加入当前页
                                    current_page_items.append((original_idx, item))
                                    current_items_height += item_height
                                else:
                                    # 放不下，放到下一页
                                    next_page_items.append((original_idx, item))
                            
                            # 将能放下的部分加入当前页
                            if current_page_items:
                                current_page_data.append({
                                    'field': field_label,
                                    'items': current_page_items
                                })
                                # 【关键修复】更新当前页高度 = 头部 + 内容 + 底部
                                current_page_height += card_header_height + current_items_height + card_footer_spacing
                                self.add_log(f'分页调试：板块"{field_label}"第一部分{len(current_page_items)}个item放入当前页，当前页高度={current_page_height}px')
                            QApplication.processEvents()
                            
                            # 新建一页放剩余items
                            if next_page_items:
                                # 先保存当前页（只有在有剩余items时才保存）
                                if current_page_data:
                                    pages_data.append(current_page_data)
                                    self.add_log(f'分页调试：保存当前页到pages_data（有剩余items），当前pages_data长度={len(pages_data)}')
                                
                                current_page_data = [{
                                    'field': field_label,
                                    'items': next_page_items
                                }]
                                # 【关键修复】正确计算新页高度 = 头部 + 内容 + 底部
                                next_page_content_height = 0
                                for _, item in next_page_items:
                                    next_page_content_height += estimate_item_height(item, field_label)
                                current_page_height = card_header_height + next_page_content_height + card_footer_spacing
                                self.add_log(f'分页调试：板块"{field_label}"剩余{len(next_page_items)}个item放入新页，高度={current_page_height}px')
                                QApplication.processEvents()
                            # 如果没有剩余items，继续处理下一个字段（不保存当前页）
                        else:
                            # 剩余空间不够放卡片头部+一个item，需要另起新页
                            self.add_log(f'分页调试：板块"{field_label}"另起新页，剩余空间{remaining_space}px不够（需要至少{card_header_height + line_height}px）')
                            QApplication.processEvents()
                            
                            # 【关键】先保存当前页（如果有内容），这是之前可能丢失的地方！
                            if current_page_data:
                                pages_data.append(current_page_data)
                                self.add_log(f'分页调试：保存当前页到pages_data（另起新页前），当前pages_data长度={len(pages_data)}')
                            
                            # 检查新一页是否能放下整个字段
                            # 【调试】输出判断细节
                            self.add_log(f'分页调试：新页判断，field_total_height={field_total_height}px，available_height={available_height}px')
                            
                            if field_total_height > available_height:
                                # 字段本身超过一页，需要拆分
                                self.add_log(f'分页调试：板块"{field_label}"内容过多（{field_total_height}px > {available_height}px），将拆分到多页显示')
                                QApplication.processEvents()
                                
                                current_page_items = []
                                current_items_height = 0  # 【关键修复】只跟踪内容高度
                                
                                for original_idx, item in enumerate(items):
                                    item_height = estimate_item_height(item, field_label)
                                    
                                    # 【调试】输出每个item的判断细节
                                    check_height = card_header_height + current_items_height + item_height + card_footer_spacing
                                    can_fit = check_height <= available_height
                                    self.add_log(f'  新页item{original_idx}: 估算高度={item_height}px，总高度={check_height}px，能放入={can_fit}')
                                    
                                    # 【关键修复】正确判断是否能放入
                                    if can_fit:
                                        current_page_items.append((original_idx, item))
                                        current_items_height += item_height
                                    else:
                                        # 【安全检查】如果当前item本身就超过一页，强制放入（避免死循环）
                                        if item_height > available_height - card_header_height - card_footer_spacing:
                                            self.add_log(f'  警告：item{original_idx}高度{item_height}px超过单页可用高度')
                                        
                                        if current_page_items:
                                            pages_data.append([{
                                                'field': field_label,
                                                'items': current_page_items
                                            }])
                                            self.add_log(f'  新页拆分：保存当前{len(current_page_items)}个items')
                                        current_page_items = [(original_idx, item)]
                                        current_items_height = item_height
                                
                                if current_page_items:
                                    current_page_data = [{
                                        'field': field_label,
                                        'items': current_page_items
                                    }]
                                    # 【关键修复】正确计算高度 = 头部 + 内容 + 底部
                                    current_page_height = card_header_height + current_items_height + card_footer_spacing
                            else:
                                # 字段能放入一页
                                current_page_data = [{
                                    'field': field_label,
                                    'items': items
                                }]
                                current_page_height = field_total_height
                                self.add_log(f'分页调试：板块"{field_label}"放入新页，items数={len(items)}')

                # 添加最后一页
                if current_page_data:
                    pages_data.append(current_page_data)
                    self.add_log(f'分页完成：最后一天共{len(pages_data)}页，最后页包含{len(current_page_data)}个字段')
                    for idx, field_info in enumerate(current_page_data):
                        self.add_log(f'  最后页字段{idx+1}: {field_info["field"]}, items数={len(field_info["items"])}')
                    QApplication.processEvents()

                # 记录分页信息
                self.add_log(f'第{day_idx + 1}天分页完成：共{len(pages_data)}页')
                for p_idx, page in enumerate(pages_data):
                    field_names = [f["field"] for f in page]
                    self.add_log(f'  第{p_idx+1}页: {field_names}')
                QApplication.processEvents()

                # 为每页生成ASS文件
                self.add_log(f'开始渲染第{day_idx+1}天，共{len(pages_data)}页')
                for page_idx, current_page_data in enumerate(pages_data):
                    field_names = [f['field'] for f in current_page_data]
                    self.add_log(f'渲染第{page_idx+1}页: {field_names}')
                    # 创建当天页面的ASS字幕（使用竖屏分辨率1080*1920）
                    # 强制使用黑体，不使用随机模板字体
                    image_title_set = self.all_setting_dict['title_set'].copy()
                    image_title_set['fontFamily'] = '黑体'
                    image_title_set['fontSize'] = 24
                    ass_header = file_create_title_ass_header(image_title_set, play_res_x=1080, play_res_y=1920)

                    # 生成字幕事件
                    ass_events = ''

                    # 重置全局Y坐标
                    global_current_y = 340

                    # 总标题（每页都显示）- 支持自动换行
                    main_title_pos_x = 540
                    main_title_font_size = 80  # 标题字体稍微减小
                    main_title_bold = 1

                    # 清理标题中的特殊字符（避免ASS解析问题）
                    video_title_clean = video_title.replace('|', '').replace('\\', '＼').replace('{', '｛').replace('}', '｝')

                    # 计算标题可用宽度（屏幕宽度1080，左右各留边距，居中显示）
                    # 字体大小80，每行约容纳8个汉字（减小换行字数条件）
                    title_max_width = 8  # 每行最大字符宽度（汉字单位）

                    # 分割长标题
                    title_lines = []
                    title_width = get_text_display_width(video_title_clean)
                    if title_width > title_max_width:
                        title_lines = smart_split_by_width(video_title_clean, title_max_width, '标题')
                        self.add_log(f'标题过长({title_width}字符)，已自动换行为{len(title_lines)}行')
                        QApplication.processEvents()
                    else:
                        title_lines = [video_title_clean]

                    # 限制最多2行，不缩小字体，只取前2行
                    if len(title_lines) > 2:
                        title_lines = title_lines[:2]  # 最多只取前2行
                        self.add_log(f'标题过长，只显示前2行')
                        QApplication.processEvents()

                    # 计算标题起始Y坐标（居中偏上）
                    line_height_title = 95  # 标题行高（适应减小后的字体）
                    title_total_height = len(title_lines) * line_height_title
                    main_title_start_y = global_current_y

                    # 生成每行标题的ASS代码
                    for line_idx, title_line in enumerate(title_lines):
                        line_y = main_title_start_y + line_idx * line_height_title
                        main_title_ass_code = f"{{\\fn黑体\\fs{main_title_font_size}" \
                                              f"\\b{main_title_bold}" \
                                              f"\\c&H{convert_to_ass_color(main_title_color)[2:]}&" \
                                              f"\\3c&H{convert_to_ass_color('#FFFFFF')[2:]}&" \
                                              f"\\4c&H{convert_to_ass_color('#FFFFFF')[2:]}&" \
                                              f"\\4a&H80&" \
                                              f"\\xbord8" \
                                              f"\\ybord6" \
                                              f"\\an2" \
                                              f"\\pos({main_title_pos_x},{line_y})" \
                                              f"}} {title_line}\\N"
                        ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(5.0)},Default,,0,0,0,,{main_title_ass_code}\n"

                    # 总标题占位（根据实际行数调整）
                    global_current_y += max(120, title_total_height + 20)

                    # 日期标题
                    date_title_pos_y = global_current_y
                    date_title_pos_x = 540
                    date_title_font_size = 65  # 增大日期标题字体
                    date_title_bold = 1

                    # 清理日期标题中的特殊字符
                    day_title_clean = day_title.replace('|', '').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
                    date_title_ass_code = f"{{\\fn黑体\\fs{date_title_font_size}" \
                                          f"\\b{date_title_bold}" \
                                          f"\\c&H{convert_to_ass_color(date_title_color)[2:]}&" \
                                          f"\\3c&H{convert_to_ass_color('#FFFFFF')[2:]}&" \
                                          f"\\an2" \
                                          f"\\pos({date_title_pos_x},{date_title_pos_y})" \
                                          f"}} {day_title_clean}\\N"
                    ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(5.0)},Default,,0,0,0,,{date_title_ass_code}\n"

                    # 日期标题占位
                    global_current_y += 90

                    # 显示当前页的板块
                    # 卡片布局参数
                    card_width = 900  # 卡片宽度
                    card_x = (1080 - card_width) // 2  # 水平居中
                    card_padding = 30  # 卡片内边距
                    card_corner_radius = 25  # 卡片圆角半径
                    card_bg_alpha = '70'  # 卡片背景透明度
                    title_bar_corner_radius = 15  # 标题栏圆角半径
                    HANZI_WIDTH_18 = 13  # 13个汉字宽度（减少换行字数，让字体更大更清晰）

                    for field_info in current_page_data:
                        field_label = field_info['field']
                        field_items = field_info['items']

                        # 模块背景块 - 使用全局Y坐标
                        block_start_y = global_current_y

                        # 卡片背景延后绘制，先计算内容高度
                        content_start_y = block_start_y + card_padding + block_bg_height + 30

                        # 准备标题栏参数（稍后绘制）
                        block_bg_color = field_colors[field_label]
                        title_bar_width = int(card_width * 0.6)  # 标题栏宽度为卡片的60%
                        title_bar_x = (card_width - title_bar_width) // 2  # 居中
                        tr = title_bar_corner_radius
                        tw = title_bar_width
                        th = block_bg_height
                        title_bar_pos_y = block_start_y + card_padding

                        # 模块标题参数（稍后绘制）
                        field_title_color_current = '#FFFFFF'  # 白色
                        title_center_x = card_x + title_bar_x + title_bar_width // 2
                        title_center_y = block_start_y + card_padding + block_bg_height // 2 + 35  # 向下偏移35像素

                        # 临时存储字段内容事件
                        field_content_events = []

                        # 标题栏和间距占位
                        global_current_y = content_start_y

                        # 字段内容（自动换行,深色文字，结构化显示）
                        if field_items:
                            # 使用已分页的items（不再需要解析）
                            items = field_items

                            # 显示列表项（每项带序号/符号）- 使用全局动态Y坐标
                            # 内容在卡片内显示，左侧对齐
                            content_pos_x_content = card_x + card_padding + 40

                                # 颜色标记处理：景点名称用【】标记，美食名称用《》标记
                            def apply_color_marks(text):
                                """
                                应用颜色标记到文本中，处理跨行情况

                                规则：
                                - 如果当前行有未闭合的【，在行尾补上】
                                - 如果当前行开头有未闭合的】（且行首不是】），在行首补上【
                                """
                                # 如果文本为空或只有空格，直接返回
                                if not text or not text.strip():
                                    return text

                                # 获取默认颜色
                                default_color = convert_to_ass_color(content_text_color)[2:]
                                # 景点名称颜色（亮蓝色）
                                spot_color = convert_to_ass_color('#4287F5')[2:]
                                # 美食名称颜色（橙黄色）
                                food_color = convert_to_ass_color('#FFA500')[2:]

                                # 先处理原始文本，补充缺失的标记符号
                                processed_text = text

                                # 处理景点标记 【】
                                spot_open_count = processed_text.count('【')
                                spot_close_count = processed_text.count('】')
                                if spot_open_count > spot_close_count:
                                    # 有未闭合的【，在行尾补上】
                                    processed_text += '】'
                                elif spot_close_count > spot_open_count:
                                    # 有未闭合的】，需要判断是否在行首
                                    # 只有当行首不是】时，才需要补【（说明是跨行的情况）
                                    stripped = processed_text.lstrip()
                                    if stripped and not stripped.startswith('】'):
                                        processed_text = '【' + processed_text

                                # 处理美食标记 《》
                                food_open_count = processed_text.count('《')
                                food_close_count = processed_text.count('》')
                                if food_open_count > food_close_count:
                                    # 有未闭合的《，在行尾补上》
                                    processed_text += '》'
                                elif food_close_count > food_open_count:
                                    # 有未闭合的》，需要判断是否在行首
                                    stripped = processed_text.lstrip()
                                    if stripped and not stripped.startswith('》'):
                                        processed_text = '《' + processed_text

                                # 然后将标记替换为颜色代码
                                result = processed_text
                                result = result.replace('【', f'{{\\c&H{spot_color}&}}')
                                result = result.replace('】', f'{{\\c&H{default_color}&}}')
                                result = result.replace('《', f'{{\\c&H{food_color}&}}')
                                result = result.replace('》', f'{{\\c&H{default_color}&}}')

                                return result

                            # 智能切分函数：确保不拆分标记对【】或《》，同时控制行长度
                            def smart_split_with_brackets(text, max_length, field_label):
                                """智能切分文本，确保标记对不被拆分，同时控制每行长度"""
                                if len(text) <= max_length:
                                    return [text]

                                lines = []
                                start = 0

                                while start < len(text):
                                    # 根据板块类型设置最大允许长度
                                    if field_label == '行程安排':
                                        # 行程安排已考虑序号，文本部分不能超长
                                        max_allow = max_length
                                    else:
                                        # 其他板块允许稍微超长以容纳完整标记（最多超长4字）
                                        max_allow = max_length + 4

                                    segment = text[start:start + max_allow]

                                    # 检查段末是否在标记内部
                                    # 统计【和】的数量
                                    bracket_count_open = segment.count('【') + segment.count('《')
                                    bracket_count_close = segment.count('】') + segment.count('》')

                                    # 如果开标记多于关标记，说明在标记内部
                                    if bracket_count_open > bracket_count_close:
                                        # 尝试在当前段内找到对应的关标记
                                        # 查找最后一个开标记的位置
                                        last_open_pos = -1
                                        open_char = None
                                        for char in ['【', '《']:
                                            pos = segment.rfind(char)
                                            if pos > last_open_pos:
                                                last_open_pos = pos
                                                open_char = char

                                        if last_open_pos != -1 and open_char:
                                            close_char = '】' if open_char == '【' else '》'
                                            # 在剩余文本中查找关标记
                                            remaining = text[start + last_open_pos:]
                                            close_pos = remaining.find(close_char)

                                            if close_pos != -1 and close_pos + last_open_pos <= max_allow:
                                                # 在合理范围内找到关标记，调整切分点
                                                segment = text[start:start + last_open_pos + close_pos + 1]

                                    # 如果段太长，在空格处切分（但要检查是否在标记内）
                                    if len(segment) > max_length and ' ' in segment:
                                        # 检查最后一个开标记的位置和最后一个空格的位置
                                        last_space = segment.rfind(' ')
                                        last_open_bracket = -1
                                        for char in ['【', '《']:
                                            pos = segment.rfind(char)
                                            if pos > last_open_bracket:
                                                last_open_bracket = pos

                                        # 如果空格在最后一个开标记之前，可以切分
                                        if last_space < last_open_bracket or last_open_bracket == -1:
                                            if last_space >= max_length * 0.6:  # 至少在60%的位置
                                                segment = segment[:last_space]
                                                segment = segment.rstrip()
                                        # 否则尝试保留完整标记（即使超长）

                                    lines.append(segment)
                                    start += len(segment)

                                return lines

                            for item_tuple in items:
                                # 解包元组获取原始索引和内容
                                if isinstance(item_tuple, tuple):
                                    original_idx, item = item_tuple
                                else:
                                    # 兼容非拆分的情况
                                    original_idx = items.index(item_tuple)
                                    item = item_tuple
                                # 序号/符号（只有"行程安排"使用序号，其他板块不需要符号）
                                item_prefix = f"{original_idx + 1}." if field_label == '行程安排' else ""
                                # 处理长文本自动换行，使用智能切分
                                # 使用字符宽度计算，而非字符数量

                                sub_lines = []
                                if field_label == '行程安排':
                                    # 行程安排：第一行和后续行宽度不同
                                    # 序号"1. "占用约2个汉字宽度，所以后续行比第一行多2个字宽度
                                    first_line_max_width = HANZI_WIDTH_18 - 2  # 第一行（有序号）
                                    other_line_max_width = HANZI_WIDTH_18      # 后续行（无序号，多2个字）
                                    
                                    if get_text_display_width(item) > first_line_max_width:
                                        # 第一行使用较窄宽度
                                        first_lines = smart_split_by_width(item, first_line_max_width, field_label)
                                        first_line = first_lines[0] if first_lines else ''
                                        sub_lines.append(first_line)
                                        # 剩余部分使用较宽宽度
                                        # 【关键修复】使用smart_split_by_width的结果获取剩余文本
                                        remaining = item[len(first_line):].strip() if first_line else item.strip()
                                        if remaining:
                                            remaining_lines = smart_split_by_width(remaining, other_line_max_width, field_label)
                                            sub_lines.extend(remaining_lines)
                                    else:
                                        sub_lines = [item]
                                else:
                                    # 其他板块：所有行宽度一致
                                    max_width = HANZI_WIDTH_18
                                    if get_text_display_width(item) > max_width:
                                        sub_lines = smart_split_by_width(item, max_width, field_label)
                                    else:
                                        sub_lines = [item]

                                # 过滤掉空行
                                sub_lines = [line for line in sub_lines if line and line.strip()]

                                # 显示每行 - 每行后更新全局Y坐标
                                for sub_idx, sub_line in enumerate(sub_lines):
                                    # 跳过空行
                                    if not sub_line or not sub_line.strip():
                                        continue
                                    # 先清理原始文本中的ASS特殊字符（避免破坏后续的颜色标签）
                                    sub_line_clean = sub_line.replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
                                    # 再次检查清理后是否为空
                                    if not sub_line_clean or not sub_line_clean.strip():
                                        continue
                                    # 对清理后的文本应用颜色标记
                                    colored_line = apply_color_marks(sub_line_clean)
                                    # 检查处理后的内容是否只有颜色代码（移除所有 ASS 标签后检查）
                                    import re
                                    text_only = re.sub(r'\{\\[^}]*\}', '', colored_line)  # 移除所有 ASS 标签
                                    if not text_only or not text_only.strip():
                                        continue
                                    content_line_ass_code = f"{{\\fn黑体\\fs{content_font_size}" \
                                                        f"\\c&H{convert_to_ass_color(content_text_color)[2:]}&" \
                                                        f"\\3c&H{convert_to_ass_color('#FFFFFF')[2:]}&" \
                                                        f"\\3a&H00&" \
                                                        f"\\xbord4\\ybord4" \
                                                        f"\\an7" \
                                                        f"\\pos({content_pos_x_content},{global_current_y})" \
                                                        f"}} {item_prefix if sub_idx == 0 else '  '} {colored_line}"
                                    field_content_events.append(f"Dialogue: 0,00:00:00.00,{sec2ass(5.0)},Default,,0,0,0,,{content_line_ass_code}\n")

                                    # 每行后增加全局Y坐标
                                    global_current_y += line_height

                        # 计算实际卡片高度
                        actual_card_height = global_current_y - block_start_y + card_padding

                        # 绘制卡片背景（在最底层）
                        r = card_corner_radius
                        cw = card_width
                        ch = actual_card_height
                        card_bg_path = (f"m {r} 0 "
                                       f"l {cw-r} 0 b {cw} 0 {cw} 0 {cw} {r} "
                                       f"l {cw} {ch-r} b {cw} {ch} {cw} {ch} {cw-r} {ch} "
                                       f"l {r} {ch} b 0 {ch} 0 {ch} 0 {ch-r} "
                                       f"l 0 {r} b 0 0 0 0 {r} 0")
                        card_bg_ass = f"{{\\p1\\c&HFFFFFF&\\1a&H{card_bg_alpha}&\\an7\\pos({card_x},{block_start_y})}} {card_bg_path}{{\\p0}}"
                        ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(5.0)},Default,,0,0,0,,{card_bg_ass}\n"

                        # 绘制标题栏
                        title_bar_path = (f"m {tr} 0 "
                                          f"l {tw-tr} 0 b {tw} 0 {tw} 0 {tw} {tr} "
                                          f"l {tw} {th-tr} b {tw} {th} {tw} {th} {tw-tr} {th} "
                                          f"l {tr} {th} b 0 {th} 0 {th} 0 {th-tr} "
                                          f"l 0 {tr} b 0 0 0 0 {tr} 0")
                        title_bar_ass = f"{{\\p1\\c&H{convert_to_ass_color(block_bg_color)[2:]}&\\1a&H00&\\an7\\pos({card_x + title_bar_x},{title_bar_pos_y})}} {title_bar_path}{{\\p0}}"
                        ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(5.0)},Default,,0,0,0,,{title_bar_ass}\n"

                        # 绘制模块标题
                        field_title_ass_code = f"{{\\fn黑体\\fs{field_font_size}" \
                                               f"\\b1" \
                                               f"\\c&H{convert_to_ass_color(field_title_color_current)[2:]}&" \
                                               f"\\an2" \
                                               f"\\pos({title_center_x},{title_center_y})" \
                                               f"}} {field_icons[field_label]} {field_label}\\N"
                        ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(5.0)},Default,,0,0,0,,{field_title_ass_code}\n"

                        # 添加字段内容事件
                        ass_events += ''.join(field_content_events)

                        # 模块之间增加间距（加上卡片底部内边距和额外间距）
                        global_current_y += card_padding + 30  # 卡片底部内边距 + 模块间距

                    # 生成当前页的ASS文件
                    ass_content = ass_header + "\n" + ass_events
                    page_ass_path = os.path.join(video_tamp_path, f'page_{day_idx}_{page_idx}.ass')
                    with open(page_ass_path, "w", encoding="utf-8") as f:
                        f.write(ass_content)

                    # 生成当前页的视频
                    page_output_path = os.path.join(video_tamp_path, f'page_{day_idx}_{page_idx}_video.mp4')

                    # 背景图片转视频,时长5秒
                    asyncio.run(self.create_page_video(bg_image_path, 5.0, page_output_path, page_ass_path))

                    if os.path.exists(page_output_path):
                        page_video_list.append(page_output_path)
                        total_duration += 5.0
                        self.add_log(f'已生成第{day_idx + 1}天第{page_idx + 1}页视频')
                        QApplication.processEvents()
                    else:
                        self.add_log(f'第{day_idx + 1}天第{page_idx + 1}页视频生成失败')
                        QApplication.processEvents()

            # 合并所有页面的视频(添加过渡效果)
            if len(page_video_list) > 0:
                # 随机选择过渡效果
                transition_effects = ['0', '1', '2', '3']  # 0:硬切, 1:淡入淡出, 2:左滑, 3:右滑
                transition = random.choice(transition_effects)
                transition_duration = 0.8  # 过渡时长0.8秒

                self.add_log(f'使用过渡效果{transition}合并{len(page_video_list)}页视频')
                QApplication.processEvents()

                # 合并视频
                merged_video_path = os.path.join(video_tamp_path, 'merged_video.mp4')
                concatenate_videos_in_segments(page_video_list, merged_video_path, transition, transition_duration)

                if not os.path.exists(merged_video_path):
                    self.add_log('视频合并失败')
                    copy_start_num += 1
                    continue

                # 添加背景音乐
                parent_dir = os.getcwd()
                bg_music_dir = os.path.join(parent_dir, 'cacheMusic')
                mp3_files = [f for f in os.listdir(bg_music_dir) if f.lower().endswith('.mp3')]

                bgm_video_path = None  # 初始化变量
                if mp3_files:
                    random_mp3_file = random.choice(mp3_files)
                    random_mp3_path = os.path.join(bg_music_dir, random_mp3_file)

                    bgm_video_path = merged_video_path.replace('.mp4', '_bgm.mp4')
                    bgAudioVolume = 40

                    addMusicWorker = AddMusicWorker(merged_video_path, random_mp3_path, 100, bgAudioVolume,
                                                    bgm_video_path)
                    self.thread_pool.start(addMusicWorker)
                    addMusicWorker.signals.finished.connect(self.on_success_occurred)
                    addMusicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        self.add_log('添加音乐失败')
                        copy_start_num += 1
                        continue

                    self.add_log('已添加背景音乐')
                    QApplication.processEvents()

                    final_video_path = bgm_video_path
                else:
                    self.add_log('没有找到背景音乐文件,跳过添加音乐')
                    final_video_path = merged_video_path

                # 添加水印
                watermark_location_examples = [
                    ['50', '50'],
                    ['main_w-overlay_w-100', '50'],
                    ['50', 'main_h-overlay_h-50'],
                    ['main_w-overlay_w-50', 'main_h-overlay_h-50'],
                    ['(main_w-overlay_w)/2', '(main_h-overlay_h)/2'],
                    ['(main_w-overlay_w)/2', '50'],
                    ['(main_w-overlay_w)/2', 'main_h-overlay_h-100']
                ]

                watermark_setting = {
                    'watermark_location': watermark_location_examples[self.all_setting_dict['water_set']['position']],
                    'zoom_size': self.all_setting_dict['water_set']['zoom'],
                    'pic_alpha': self.all_setting_dict['water_set']['alpha']
                }

                watermarked_video_path = os.path.join(video_tamp_path, os.path.basename(final_video_path).replace('.mp4', '_watermarked.mp4'))
                add_text_watermark_worker = AddWatermarkWorker(
                    final_video_path, watermarked_video_path, watermark_setting, 2,
                    self.all_setting_dict['water_set']['filePath']
                )

                self.thread_pool.start(add_text_watermark_worker)
                add_text_watermark_worker.signals.finished.connect(self.on_success_occurred)
                add_text_watermark_worker.signals.errorOccurred.connect(self.on_error_occurred)
                self.loop.exec()

                if self.error_flag:
                    self.add_log('添加水印失败')
                    copy_start_num += 1
                    continue

                self.add_log('已添加水印')
                QApplication.processEvents()

                # 视频压缩
                compressed_video_path = os.path.join(video_tamp_path, os.path.basename(watermarked_video_path).replace('_watermarked.mp4', '_compressed.mp4'))
                compress_video_worker = CompressVideoWorker(watermarked_video_path, compressed_video_path)

                self.thread_pool.start(compress_video_worker)
                compress_video_worker.signals.finished.connect(self.on_success_occurred)
                compress_video_worker.signals.errorOccurred.connect(self.on_error_occurred)
                self.loop.exec()

                # 保存最终视频
                video_name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', video_title) + '.mp4'
                final_output_path = os.path.join(out_dir_path, video_name)

                # 移动最终视频文件
                if os.path.exists(watermarked_video_path):
                    shutil.move(watermarked_video_path, final_output_path)
                    self.add_log(f'视频已保存到: {final_output_path}')
                else:
                    self.add_log(f'错误: 找不到压缩视频文件 {compressed_video_path}')
                    copy_start_num += 1
                    continue

                # 清理中间文件（在移动完成后再删除）
                for temp_file in [merged_video_path, bgm_video_path if 'bgm_video_path' in locals() else None,
                                  watermarked_video_path]:
                    if temp_file and os.path.exists(temp_file):
                        os.remove(temp_file)

                # 生成任务信息
                excel_file_path_name = '1.xls'
                excel_file_path = os.path.join(out_dir_path, excel_file_path_name)

                data_dict = {
                    "标题": video_title.replace('|', ''),
                    "标签": video_fabu_tag,
                    "文件路径": final_output_path.replace('/', '\\'),
                    "描述": f"{video_title} - {len(day_data_list)}天行程",
                    "封面路径": "",
                    "图片集合": "",
                    "关联商品": "",
                    "分区分类": "旅游",
                    "备注": ""
                }

                write_to_old_excel(excel_file_path, data_dict)

                self.add_log(f'生成完成一个视频: {final_output_path}')
                QApplication.processEvents()

                # 上传任务信息
                account_result = self.get_upload_accounts(account_name)
                if len(account_result) > 0:
                    for (account, mac) in account_result:
                        task_param = {
                            'name': account_name,
                            'account': account,
                            'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'title': data_dict.get('标题'),
                            'mac': mac,
                            'tag': data_dict.get('标签'),
                            'path': data_dict.get('文件路径'),
                            'describe': data_dict.get('描述'),
                            'classify': data_dict.get('分区分类'),
                            'task_type': 10,
                        }
                        add_user_task(task_param)
                        self.add_log(f'{account_name}{account}上传视频任务:{final_output_path}')
                        QApplication.processEvents()

            # 清理缓存
            clean_cut_cache()
            clean_cache()
            copy_start_num += 1

        self.add_log('所有视频生成完毕')
        QApplication.processEvents()

    # 节日风俗类视频合成
    def compositeFestivalCustomsVideo(self, copy_file, label_file, out_dir_path, account_name):
        self.add_log('开始合成节日风俗类视频')
        QApplication.processEvents()

        # 读取设置并应用随机模板
        self.all_setting_dict = read_dict_from_txt('setting.txt')
        if self.randomVideoModelCheckBox.isChecked():
            model_result = get_random_video_model()
            model_set_dict = json.loads(model_result['model_set'])
            self.all_setting_dict['title_set'] = model_set_dict['title_set']
            self.add_log(f'已应用随机视频模板，字体: {model_set_dict["title_set"]["fontFamily"]}')
            QApplication.processEvents()

        # 将秒数转换为ASS时间格式 H:MM:SS.cc
        def sec2ass(seconds):
            """将秒数转换为ASS时间格式 H:MM:SS.cc"""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            centis = int((seconds % 1) * 100)
            return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

        # 计算文本的实际显示宽度（中文字符=1，英文字符/数字/标点=0.5）
        def get_text_display_width(text):
            total_width = 0
            for char in text:
                if '\u4e00' <= char <= '\u9fff':
                    total_width += 1
                elif ('a' <= char <= 'z') or ('A' <= char <= 'Z') or ('0' <= char <= '9') or char in '.,;:?!-+*/()[]{}"<>\'':
                    total_width += 0.5
                else:
                    total_width += 1
            return total_width

        # 基于显示宽度的智能换行函数
        def smart_split_by_width(text, max_width, field_label, first_line_indent_width=0):
            """
            智能换行函数
            first_line_indent_width: 首行额外缩进宽度（如两个全角空格=2）
            """
            lines = []
            current_line = ""
            current_width = 0
            is_first_line = True
            i = 0
            while i < len(text):
                char = text[i]
                # 汉字和标点符号都按1个宽度计算，英文字母/数字按0.5
                if '\u4e00' <= char <= '\u9fff':
                    char_width = 1  # 汉字
                elif char in '，。、；：！？""''（）【】《》''""':
                    char_width = 1  # 全角标点符号（含中文单双引号）
                else:
                    char_width = 0.5  # 英文/数字/半角字符
                # 计算当前行可用宽度（首行要考虑缩进）
                available_width = max_width - (first_line_indent_width if is_first_line else 0)
                if current_width + char_width > available_width and current_line:
                    lines.append(current_line.strip())
                    current_line = ""
                    current_width = 0
                    is_first_line = False
                if char in '【《':
                    bracket_content = ""
                    j = i + 1
                    while j < len(text) and text[j] not in '】》':
                        bracket_content += text[j]
                        j += 1
                    if j < len(text):
                        bracket_content += text[j]  # 包含右括号
                    # 书名号内的字符宽度计算（标点和汉字同宽）
                    def get_char_width(c):
                        if '\u4e00' <= c <= '\u9fff':
                            return 1
                        elif c in '，。、；：！？""''（）【】《》''""':
                            return 1
                        else:
                            return 0.5
                    bracket_width = sum(get_char_width(c) for c in bracket_content)
                    # 计算当前行可用宽度（首行要考虑缩进）
                    available_width = max_width - (first_line_indent_width if is_first_line else 0)
                    if current_width + bracket_width > available_width and current_line:
                        lines.append(current_line.strip())
                        current_line = ""
                        current_width = 0
                        is_first_line = False
                    current_line += bracket_content
                    current_width += bracket_width
                    i = j + 1
                else:
                    current_line += char
                    current_width += char_width
                    i += 1
            if current_line:
                lines.append(current_line.strip())
            if field_label and not lines:
                lines = [field_label]
            return lines if lines else [text[:max_width]] if text else ['']

        def create_single_customs_page(customs_name, intro_meaning, practice, time_region, page_title, video_title=None, page_num=1, total_pages=1, fields_to_show=None, page_duration=8):
            """创建单个风俗页面（参考图片攻略类样式，使用色块+沉稳配色）
            fields_to_show: 指定要显示的字段列表，如 ['简介寓意', '具体做法']，None表示显示全部
            page_duration: 页面显示时长（秒），默认8秒
            """

            # ========== 古籍风格配色（参考HTML设计：墨黑+淡墨灰+朱砂竖线）==========
            # 主文字：墨黑
            title_text_color = '#2C2C2C'      # 墨黑（参考HTML --ink）
            title_border_color = '#E8E8E8'    # 淡墨边
            # 强调色：朱砂（仅用于竖线装饰）
            accent_color = '#B83E2F'          # 朱砂（竖线装饰）
            accent_border_color = '#8B0000'   # 深红边
            # 辅助文字：淡墨灰（参考HTML --ink-light）
            secondary_text_color = '#5A5A5A'  # 淡墨灰
            secondary_border_color = '#E8E8E8'
            # 界栏线色
            border_line_color = '#B8B8B8'     # 浅灰界栏线
            # 布局配置 - 居中式题签风格
            center_x = 540                    # 屏幕中心X坐标
            content_start_x = 120             # 内容起始X（缩进用）
            content_width = 840               # 内容区宽度

            # 创建ASS头部（使用file_create_title_ass_header获取随机模板字体）
            ass_header = file_create_title_ass_header(self.all_setting_dict['title_set'], play_res_x=1080, play_res_y=1920)
            ass_content = ass_header + "\n"

            # 辅助函数：十六进制颜色转ASS颜色格式
            def convert_to_ass_color(hex_color):
                r = int(hex_color[1:3], 16)
                g = int(hex_color[3:5], 16)
                b = int(hex_color[5:7], 16)
                return f"&H00{b:02X}{g:02X}{r:02X}&"

            current_time = 0

            # 全局Y坐标（整体往下移）
            global_y = 360

            # ========== 视频总标题（居中题签式，黑色加重） ==========
            if video_title:
                # 清理标题中的特殊字符（去掉|，避免ASS解析问题）
                video_title_clean = video_title.replace('|', '').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
                title_font_size = 105  # 加大字号
                
                # 计算标题可用宽度（字体105，每行约容纳7个汉字）
                title_max_width = 7  # 每行最大字符宽度
                
                # 分割长标题
                title_lines = []
                title_width = get_text_display_width(video_title_clean)
                if title_width > title_max_width:
                    title_lines = smart_split_by_width(video_title_clean, title_max_width, '标题')
                else:
                    title_lines = [video_title_clean]
                
                # 限制最多2行
                if len(title_lines) > 2:
                    title_lines = title_lines[:2]
                
                # 生成每行标题
                line_height_title = 115
                for line_idx, title_line in enumerate(title_lines):
                    line_y = global_y + line_idx * line_height_title
                    title_ass = f"{{\\fn楷体\\fs{title_font_size}\\b1\\c&H{convert_to_ass_color('#1A1A1A')[2:]}&\\3c&H{convert_to_ass_color('#CCCCCC')[2:]}&\\3a&H00&\\bord8\\an2\\pos({center_x},{line_y})}}{title_line}\n"
                    ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{title_ass}"
                
                global_y += len(title_lines) * line_height_title + 20  # 根据实际行数调整

            # ========== 页标题 + 风俗名称（并列显示，褐色减淡） ==========
            page_title_clean = ""
            if page_title:
                page_title_clean = page_title.replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
            
            # 去掉风俗名称中的【】括号
            customs_name_clean = customs_name.replace('【', '').replace('】', '').replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
            
            # 组合显示：页标题 : 风俗名称
            if page_title_clean:
                combined_text = f"{page_title_clean}：{customs_name_clean}"
            else:
                combined_text = customs_name_clean
            
            combined_font_size = 72  # 统一字号
            # 使用褐色减淡 #8B6F47
            combined_ass = f"{{\\fn楷体\\fs{combined_font_size}\\b1\\c&H{convert_to_ass_color('#8B6F47')[2:]}&\\3c&H{convert_to_ass_color('#E8E0D5')[2:]}&\\3a&H00&\\bord5\\an2\\pos({center_x},{global_y})}}{combined_text}\n"
            ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{combined_ass}"
            global_y += 80  # 增加与卡片的间距

            # 字段配置
            all_field_config = [
                {'name': '简介寓意', 'value': intro_meaning},
                {'name': '具体做法', 'value': practice},
                {'name': '时间地域', 'value': time_region}
            ]
            
            # 如果指定了要显示的字段，则过滤
            if fields_to_show:
                field_config = [f for f in all_field_config if f['name'] in fields_to_show]
            else:
                field_config = all_field_config

            # ========== 三个字段模块（圆角卡片包裹式）==========
            line_height = 72
            field_font_size = 62   # 标题字体
            content_font_size = 52  # 内容字体
            section_spacing = 50   # 模块间距

            # 计算内容总高度以绘制背景卡片
            card_padding_top = 50
            card_padding_bottom = 80  # 大幅增加底部边距，防止内容溢出+预留页码空间
            card_padding_left = 40
            card_padding_right = 40
            card_start_y = global_y - 25
            content_total_height = card_padding_top + card_padding_bottom

            # 预计算高度（多预留一些空间）
            temp_y = global_y
            for field_info in field_config:
                field_value = field_info['value']
                temp_y += 85  # 标题高度（增加5px缓冲）
                if field_value:
                    value_lines = smart_split_by_width(field_value, 15, field_info['name'], first_line_indent_width=2)
                    temp_y += len(value_lines) * line_height
                temp_y += section_spacing + 35  # 增加模块间距
            content_total_height += temp_y - global_y

            card_width = content_width + card_padding_left + card_padding_right
            card_height = content_total_height
            card_x = content_start_x - card_padding_left
            card_y = card_start_y
            corner_radius = 20

            # 绘制宣纸米白半透明圆角卡片背景（rgba(249,246,240,0.9)）
            # 使用简单的矩形而非圆角（ASS圆角绘制复杂，改用简洁矩形）
            r = corner_radius
            w = card_width
            h = card_height
            
            # 宣纸米白色 #F9F6F0（更暖的米白）
            rice_paper_color = '#F9F6F0'
            # 浅驼色边框 #E8E0D5
            border_color = '#E8E0D5'
            
            # 使用多边形近似圆角矩形（8边形近似）
            # 从左上圆角开始，顺时针
            card_path = (f"m {r} 0 "  # 上边左起
                        f"l {w-r} 0 "  # 上边到右上圆角
                        f"l {w} {r} "  # 简化：直接到右边
                        f"l {w} {h-r} "  # 右边到下
                        f"l {w-r} {h} "  # 右下到底边
                        f"l {r} {h} "  # 底边到左下
                        f"l 0 {h-r} "  # 左下
                        f"l 0 {r} "  # 左边回到起点
                        "c")  # 闭合
            # 填充背景
            card_ass = f"{{\\p1\\c&H{convert_to_ass_color(rice_paper_color)[2:]}&\\1a&H19&\\an7\\pos({card_x},{card_y})}} {card_path} {{\\p0}}\n"
            ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{card_ass}"
            # 绘制1px浅驼色边框
            border_ass = f"{{\\p1\\c&H{convert_to_ass_color(border_color)[2:]}&\\1a&H00&\\an7\\pos({card_x},{card_y})}} {card_path} {{\\p0}}\n"
            ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{border_ass}"

            # 绘制卡片内容
            for idx, field_info in enumerate(field_config):
                field_name = field_info['name']
                field_value = field_info['value']

                # ========== 字段标题（左侧朱砂竖线 + 墨黑文字 + Bold字重）=========
                field_name_clean = field_name.replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')

                # 左侧朱砂竖线（参考HTML .block-title::before）
                vertical_bar_width = 6
                vertical_bar_height = field_font_size * 0.6
                bar_ass = f"{{\\p1\\c&H{convert_to_ass_color(accent_color)[2:]}&\\1a&H00&\\an7\\pos({content_start_x},{global_y + 15})}} m 0 0 l {vertical_bar_width} 0 l {vertical_bar_width} {vertical_bar_height} l 0 {vertical_bar_height} {{\\p0}}\n"
                ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{bar_ass}"

                # 字段名（墨黑，Bold字重，位于竖线右侧）
                title_text_offset = vertical_bar_width + 18
                name_x = content_start_x + title_text_offset
                name_ass = f"{{\\fn楷体\\fs{field_font_size}\\b1\\c&H{convert_to_ass_color(title_text_color)[2:]}&\\3c&H{convert_to_ass_color(title_border_color)[2:]}&\\3a&H00&\\bord4\\an7\\pos({name_x},{global_y})}}{field_name_clean}\n"
                ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{name_ass}"
                global_y += 80

                # ========== 字段内容（淡墨灰，Regular字重，与竖线对齐，首行缩进两格）=========
                content_x = content_start_x
                max_line_width = 14  # 换行计算保持14个字，只有第一行显示时添加缩进

                if field_value:
                    value_lines = smart_split_by_width(field_value, max_line_width, field_name, first_line_indent_width=2)

                    for line_idx, line in enumerate(value_lines):
                        line_clean = line.replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')

                        # 内容文字（黑字白边，与compositeImageIntroVideo一致）
                        # 添加两个全角空格作为首行缩进
                        indented_line = '　　' + line_clean if line_idx == 0 else line_clean
                        line_ass = f"{{\\fn楷体\\fs{content_font_size}" \
                                   f"\\c&H{convert_to_ass_color('#212121')[2:]}&" \
                                   f"\\3c&H{convert_to_ass_color('#FFFFFF')[2:]}&" \
                                   f"\\3a&H00&" \
                                   f"\\xbord6\\ybord6" \
                                   f"\\shad0" \
                                   f"\\an7" \
                                   f"\\pos({content_x},{global_y})" \
                                   f"}}{indented_line}\n"
                        ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{line_ass}"
                        global_y += line_height

                global_y += section_spacing

                # 模块间间距
                global_y += 30

            # ========== 页码（右下角）==========
            page_num_x = card_x + card_width - 40  # 卡片右下角偏左
            page_num_y = card_y + card_height - 45  # 卡片底部偏上
            page_num_font_size = 42  # 增大字体
            # 使用深色页码，加粗，加粗边框，更显眼
            page_num_ass = f"{{\\fs{page_num_font_size}\\b1\\c&H{convert_to_ass_color('#5A4A3A')[2:]}&\\3c&H{convert_to_ass_color('#F5F0E8')[2:]}&\\3a&H00&\\bord4\\an3\\pos({page_num_x},{page_num_y})}}{page_num}/{total_pages}\n"
            ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{page_num_ass}"

            return ass_content

        def estimate_field_height(field_value, field_name):
            """估算字段渲染所需高度"""
            height = 85  # 标题高度
            if field_value:
                value_lines = smart_split_by_width(field_value, 14, field_name, first_line_indent_width=2)
                height += len(value_lines) * 72  # line_height = 72
            height += 50 + 30  # section_spacing + 模块间距
            return height

        def paginate_fields(intro_meaning, practice, time_region, available_height):
            """智能分页：将字段分配到各页"""
            fields = [
                {'name': '简介寓意', 'value': intro_meaning},
                {'name': '具体做法', 'value': practice},
                {'name': '时间地域', 'value': time_region}
            ]
            
            pages = []
            current_page = []
            current_height = 0
            
            for field in fields:
                field_h = estimate_field_height(field['value'], field['name'])
                
                if not current_page:
                    current_page.append(field['name'])
                    current_height = field_h
                elif current_height + field_h <= available_height:
                    current_page.append(field['name'])
                    current_height += field_h
                else:
                    # 放不下，保存当前页，新建一页
                    pages.append(current_page)
                    current_page = [field['name']]
                    current_height = field_h
            
            if current_page:
                pages.append(current_page)
            
            return pages

        try:
            # 读取文案Excel
            df_copy = _read_excel(copy_file)

            # 读取标签Excel
            df_label = _read_excel(label_file)

            # 获取总行数和列数
            total_rows = len(df_copy)
            total_cols = df_copy.shape[1]

            self.add_log(f'文案Excel: {total_rows}行 x {total_cols}列')
            QApplication.processEvents()

            # 读取第一行（索引0）
            # 第1列（索引0）：标题
            # 第2列（索引1）：标签
            # 第3列起（索引2+）：各页JSON数据
            title = df_copy.iloc[0, 0] if total_rows > 0 else "风俗介绍"
            tags = df_copy.iloc[0, 1] if total_cols > 1 and total_rows > 0 else ""

            self.add_log(f'标题: {title}')
            self.add_log(f'标签: {tags}')

            # 读取标签文件的所有行（每个标签占一行）
            label_data = df_label.iloc[:, 0].tolist()

            # 解析各页内容
            # 格式：第一行 = [标题, 标签, 第1页JSON, 第2页JSON, ...]
            pages_data = []

            if total_cols > 2:
                # 从第3列（索引2）开始读取各页JSON数据
                for col in range(2, total_cols):
                    try:
                        cell_value = df_copy.iloc[0, col]
                        if isinstance(cell_value, str) and cell_value.strip():
                            self.add_log(f'尝试解析第1行第{col}列: {cell_value[:80]}...')
                            page_data = json.loads(cell_value)
                            pages_data.append(page_data)
                            self.add_log(f'第1行第{col}列解析成功')
                    except json.JSONDecodeError as e:
                        self.add_log(f'第1行第{col}列JSON解析失败: {str(e)[:100]}')
                        continue
                    except Exception as e:
                        self.add_log(f'第1行第{col}列处理出错: {str(e)[:100]}')
                        continue

            if not pages_data:
                self.add_log('没有有效的内容数据')
                return

            self.add_log(f'共 {len(pages_data)} 页内容')
            QApplication.processEvents()

            # 智能判断展示模式
            is_multi_customs = False
            # 检查是否有多个不同的页标题（表示多风俗列表）
            page_titles = []
            for page in pages_data:
                for key in page.keys():
                    page_titles.append(key.split('·')[1] if '·' in key else key)
            # 如果页标题不重复，说明是多风俗列表
            is_multi_customs = len(set(page_titles)) > 1

            self.add_log(f'展示模式: {"多风俗列表" if is_multi_customs else "单风俗详解"}')
            QApplication.processEvents()

            # 读取标签文件的所有行
            label_data = df_label.iloc[:, 0].tolist()
            self.add_log(f'标签文件有{len(label_data)}行标签')

            # 获取共用背景图片（所有页面共用），使用第一个标签匹配
            bg_image_path = None
            bg_success = False

            # 使用第一个风俗的标签来匹配背景视频
            bg_video_tag = None
            if label_data and len(label_data) > 0:
                bg_video_tag = label_data[0].split(',')[0] if label_data[0] else '风俗'
                self.add_log(f'使用第1个标签匹配背景: {bg_video_tag}')
            else:
                bg_video_tag = '风俗'

            video_path = ''
            try:
                # 如果标签是"全国"，则随机获取视频；否则按关键词匹配
                if bg_video_tag == '全国':
                    video_id = get_random_cover_video(['全国'], '普通素材')
                    if video_id:
                        self.add_log(f'随机获取全国素材，视频ID: {video_id}')
                        QApplication.processEvents()
                        video_path = download_cn_video(video_id, 0)
                        if video_path and os.path.exists(video_path):
                            self.add_log(f'视频下载成功: {video_path}')
                            QApplication.processEvents()
                else:
                    ftp_videos = get_videos_by_keyword_1(bg_video_tag, screen=0, location="", audio_length=8, cate=None)

                    if ftp_videos and len(ftp_videos) > 0:
                        video_id = ftp_videos[0]['video_id']
                        self.add_log(f'根据标签"{bg_video_tag}"找到视频ID: {video_id}')
                        QApplication.processEvents()
                        video_path = download_cn_video(video_id, 0)
                        if video_path and os.path.exists(video_path):
                            self.add_log(f'视频下载成功: {video_path}')
                            QApplication.processEvents()
                    else:
                        self.add_log(f'未找到标签"{bg_video_tag}"的匹配视频，尝试随机获取')
                        QApplication.processEvents()
                        # 尝试随机获取视频
                        video_id = get_random_cover_video(['风俗'], '普通素材')
                        if video_id:
                            self.add_log(f'随机获取视频ID: {video_id}')
                            QApplication.processEvents()
                            video_path = download_cn_video(video_id, 0)
                            if video_path and os.path.exists(video_path):
                                self.add_log(f'视频下载成功: {video_path}')
                                QApplication.processEvents()

                if video_path and os.path.exists(video_path):
                    self.add_log(f'视频下载成功: {video_path}')
                    QApplication.processEvents()
                    tamp_folder_name = 'tempConcateVideo'
                    current_directory = os.getcwd()
                    tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
                    video_tamp_path_name = 'video_cache_file'
                    video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)
                    bg_image_path = os.path.join(video_tamp_path, 'bg_customs_common.jpg')

                    # 如果背景图已存在，先删除以确保重新生成
                    if os.path.exists(bg_image_path):
                        try:
                            os.remove(bg_image_path)
                            self.add_log(f'已删除旧背景图: {bg_image_path}')
                            QApplication.processEvents()
                        except Exception as e:
                            self.add_log(f'删除旧背景图失败: {str(e)}')
                            QApplication.processEvents()

                    from ffmpeg_tool.video_concat_tool import extract_and_blur_random_frame
                    if extract_and_blur_random_frame(
                        video_path, bg_image_path, target_width=1080, target_height=1920, blur_sigma=5
                    ):
                        self.add_log(f'背景图生成成功: {bg_image_path}')
                        QApplication.processEvents()
                        bg_success = True
                    else:
                        self.add_log(f'背景图生成失败')
                        QApplication.processEvents()

            except Exception as e:
                self.add_log(f'获取背景图出错: {str(e)}')
                QApplication.processEvents()

            if not bg_success or not os.path.exists(bg_image_path):
                self.add_log('背景图获取失败')
                return

            # 验证背景图文件有效性
            file_size = os.path.getsize(bg_image_path)
            if file_size == 0:
                self.add_log(f'背景图文件无效（大小为0）: {bg_image_path}')
                return
            self.add_log(f'背景图验证成功，大小: {file_size} bytes')
            QApplication.processEvents()

            # 生成各页视频
            output_videos = []
            total_duration = 0

            if is_multi_customs:
                # 多风俗列表模式：每页展示一个风俗的4个字段
                # 先收集所有风俗数据并计算每个风俗的分页情况
                customs_list = []
                for page in pages_data:
                    for page_key, customs_dict in page.items():
                        for item_key, item_data in customs_dict.items():
                            customs_list.append({
                                'page_key': page_key,
                                'item_data': item_data
                            })
                
                # 不限制风俗数量，处理所有风俗
                # customs_list = customs_list[:10]  # 取消限制
                total_customs = len(customs_list)
                
                # 智能分页：检查内容是否溢出
                # 可用高度 = 屏幕高度 - 顶部标题区域 - 底部安全边距
                # 标题区域约 360 + 标题高度(约230) + 页标题(约80) = 670
                SCREEN_HEIGHT = 1920
                SAFE_MARGIN_BOTTOM = 200
                available_content_height = SCREEN_HEIGHT - 670 - SAFE_MARGIN_BOTTOM  # 约1050
                
                # 先预计算每个风俗的分页情况
                customs_with_pagination = []
                for customs_info in customs_list:
                    page_key = customs_info['page_key']
                    item_data = customs_info['item_data']
                    
                    customs_name = item_data.get('风俗名称', '')
                    intro_meaning = item_data.get('简介寓意', '')
                    practice = item_data.get('具体做法', '')
                    time_region = item_data.get('时间地域', '')
                    
                    page_title = page_key.split('·')[1] if '·' in page_key else page_key
                    page_title = page_title.replace('|', '｜').replace('\\', '＼')
                    
                    # 计算分页
                    field_pages = paginate_fields(intro_meaning, practice, time_region, available_content_height)
                    
                    customs_with_pagination.append({
                        'customs_name': customs_name,
                        'intro_meaning': intro_meaning,
                        'practice': practice,
                        'time_region': time_region,
                        'page_title': page_title,
                        'field_pages': field_pages,
                        'total_field_pages': len(field_pages)
                    })
                    
                    if len(field_pages) > 1:
                        self.add_log(f'风俗"{customs_name}"内容较多，分为{len(field_pages)}页显示')
                        QApplication.processEvents()
                
                # 计算总页数（所有风俗的页数之和）
                total_pages_all = sum(c['total_field_pages'] for c in customs_with_pagination)
                
                current_page_num = 0
                # 为每个风俗生成视频页面
                for customs_idx, customs_info in enumerate(customs_with_pagination):
                    customs_name = customs_info['customs_name']
                    intro_meaning = customs_info['intro_meaning']
                    practice = customs_info['practice']
                    time_region = customs_info['time_region']
                    page_title = customs_info['page_title']
                    field_pages = customs_info['field_pages']

                    # 判断是否需要分页展示（分页时缩短时长为4秒）
                    is_paginated = len(field_pages) > 1

                    # 为每个分页生成视频
                    for field_page_idx, fields_to_show in enumerate(field_pages):
                        current_page_num += 1

                        # 分页时展示4秒，单页时展示8秒
                        page_duration = 4 if is_paginated else 8

                        # 生成ASS字幕（传递视频标题和页码，以及要显示的字段）
                        ass_content = create_single_customs_page(
                            customs_name, intro_meaning, practice, time_region, page_title, title,
                            current_page_num, total_pages_all, fields_to_show, page_duration
                        )

                        # 临时文件路径
                        ass_path = os.path.join(out_dir_path, f'temp_{customs_idx}_{len(output_videos)}.ass')
                        output_path = os.path.join(out_dir_path, f'page_{customs_idx}_{len(output_videos)}.mp4')

                        # 保存ASS文件
                        with open(ass_path, 'w', encoding='utf-8') as f:
                            f.write(ass_content)

                        # 使用现有方法创建页面视频
                        from ffmpeg_tool.pic_trans_to_video import image_to_video
                        from ffmpeg_tool.subtitles_audio_tool import add_subtitles
                        import asyncio

                        async def create_video():
                            temp_video_path = output_path.replace('.mp4', '_temp.mp4')
                            # 背景图转换为视频（使用动态时长）
                            await image_to_video(bg_image_path, page_duration, temp_video_path)
                            await add_subtitles(ass_path, temp_video_path, output_path)
                            if os.path.exists(temp_video_path):
                                os.remove(temp_video_path)

                        # 在当前事件循环中运行
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(create_video())
                        finally:
                            loop.close()

                        # 删除临时ASS文件
                        if os.path.exists(ass_path):
                            os.remove(ass_path)

                        output_videos.append(output_path)
                        total_duration += page_duration

                    # 不限制视频数量
                    # if len(output_videos) >= 10:
                    #     break
            else:
                # 单风俗详解模式：一个风俗分成多个方面展示
                # 取第一个风俗，将其4个字段分别放在不同页面
                if pages_data and len(pages_data) > 0:
                    first_page = pages_data[0]
                    for page_key, customs_dict in first_page.items():
                        page_title = page_key.split('·')[1] if '·' in page_key else page_key
                        page_title = page_title.replace('|', '｜').replace('\\', '＼')

                        # 获取第一个项目
                        item_data = None
                        for item_key in ['项目1', '项目2']:
                            if item_key in customs_dict:
                                item_data = customs_dict[item_key]
                                break

                        if item_data:
                            customs_name = item_data.get('风俗名称', '')

                            # 将4个字段分别做4页，每页突出一个方面
                            fields = [
                                ('简介寓意', item_data.get('简介寓意', ''), '详细介绍风俗的文化内涵和寓意'),
                                ('具体做法', item_data.get('具体做法', ''), '详细展示风俗的操作流程'),
                                ('时间地域', item_data.get('时间地域', ''), '说明风俗的时间背景和地域分布'),
                                ('风俗名称', item_data.get('风俗名称', ''), '总结这个风俗的核心特点')
                            ]

                            for field_idx, (field_label, field_value, field_desc) in enumerate(fields):
                                # 生成单页（参考图片攻略类样式，使用色块+统一配色）

                                # ========== 古籍风格配色（参考HTML设计：墨黑+淡墨灰+朱砂竖线）==========
                                # 主文字：墨黑
                                title_text_color = '#2C2C2C'      # 墨黑（参考HTML --ink）
                                title_border_color = '#E8E8E8'    # 淡墨边
                                # 强调色：朱砂（仅用于竖线装饰）
                                accent_color = '#B83E2F'          # 朱砂（竖线装饰）
                                accent_border_color = '#8B0000'   # 深红边
                                # 辅助文字：淡墨灰（参考HTML --ink-light）
                                secondary_text_color = '#5A5A5A'  # 淡墨灰
                                secondary_border_color = '#E8E8E8'
                                # 界栏线色
                                border_line_color = '#B8B8B8'     # 浅灰界栏线
                                # 布局配置 - 居中式题签风格
                                center_x = 540                    # 屏幕中心X坐标
                                content_start_x = 120             # 内容起始X（缩进用）
                                content_width = 840               # 内容区宽度

                                # 辅助函数
                                def convert_to_ass_color(hex_color):
                                    r = int(hex_color[1:3], 16)
                                    g = int(hex_color[3:5], 16)
                                    b = int(hex_color[5:7], 16)
                                    return f"&H00{b:02X}{g:02X}{r:02X}&"

                                # 创建ASS头部（使用file_create_title_ass_header获取随机模板字体）
                                ass_header = file_create_title_ass_header(self.all_setting_dict['title_set'], play_res_x=1080, play_res_y=1920)
                                ass_content = ass_header + "\n"

                                current_time = 0
                                page_duration = 8

                                # 全局Y坐标（整体往下移）
                                global_y = 280

                                # ========== 视频总标题（居中题签式，黑色加重） ==========
                                if title:
                                    # 清理标题中的特殊字符
                                    title_clean = title.replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
                                    title_font_size = 105  # 加大字号
                                    
                                    # 计算标题可用宽度（字体105，每行约容纳7个汉字）
                                    title_max_width = 7  # 每行最大字符宽度
                                    
                                    # 分割长标题
                                    title_lines = []
                                    title_width = get_text_display_width(title_clean)
                                    if title_width > title_max_width:
                                        title_lines = smart_split_by_width(title_clean, title_max_width, '标题')
                                    else:
                                        title_lines = [title_clean]
                                    
                                    # 限制最多2行
                                    if len(title_lines) > 2:
                                        title_lines = title_lines[:2]
                                    
                                    # 生成每行标题
                                    line_height_title = 115
                                    for line_idx, title_line in enumerate(title_lines):
                                        line_y = global_y + line_idx * line_height_title
                                        title_ass = f"{{\\fn楷体\\fs{title_font_size}\\b1\\c&H{convert_to_ass_color('#1A1A1A')[2:]}&\\3c&H{convert_to_ass_color('#CCCCCC')[2:]}&\\3a&H00&\\bord8\\an2\\pos({center_x},{line_y})}}{title_line}\n"
                                        ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{title_ass}"
                                    
                                    global_y += len(title_lines) * line_height_title + 20  # 根据实际行数调整

                                # ========== 页标题 + 风俗名称（并列显示，褐色减淡） ==========
                                page_title_clean = ""
                                if page_title:
                                    page_title_clean = page_title.replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
                                
                                # 去掉风俗名称中的【】括号
                                customs_name_clean = customs_name.replace('【', '').replace('】', '').replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
                                
                                # 组合显示：页标题 : 风俗名称
                                if page_title_clean:
                                    combined_text = f"{page_title_clean}：{customs_name_clean}"
                                else:
                                    combined_text = customs_name_clean
                                
                                combined_font_size = 68  # 统一字号（单风俗模式稍小）
                                # 使用褐色减淡 #8B6F47
                                combined_ass = f"{{\\fn楷体\\fs{combined_font_size}\\b1\\c&H{convert_to_ass_color('#8B6F47')[2:]}&\\3c&H{convert_to_ass_color('#E8E0D5')[2:]}&\\3a&H00&\\bord5\\an2\\pos({center_x},{global_y})}}{combined_text}\n"
                                ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{combined_ass}"
                                global_y += 135  # 增加与卡片的间距

                                # ========== 当前字段模块（圆角卡片包裹式）==========
                                line_height = 75
                                field_font_size = 62   # 标题字体
                                content_font_size = 52  # 内容字体

                                # 计算卡片尺寸
                                card_padding_top = 55
                                card_padding_bottom = 70  # 增加底部边距
                                card_padding_left = 45
                                card_padding_right = 45
                                card_start_y = global_y - 25

                                # 计算内容高度（增加缓冲）
                                content_height = 85  # 标题高度
                                if field_value:
                                    value_lines = smart_split_by_width(field_value, 13, field_label, first_line_indent_width=2)
                                    content_height += len(value_lines) * line_height
                                card_height = card_padding_top + content_height + card_padding_bottom
                                card_width = content_width + card_padding_left + card_padding_right
                                card_x = content_start_x - card_padding_left
                                card_y = card_start_y
                                corner_radius = 25

                                # 绘制宣纸米白半透明圆角卡片背景（rgba(249,246,240,0.9)）
                                r = corner_radius
                                w = card_width
                                h = card_height
                                
                                # 宣纸米白色 #F9F6F0（更暖的米白）
                                rice_paper_color = '#F9F6F0'
                                # 浅驼色边框 #E8E0D5
                                border_color = '#E8E0D5'
                                
                                # 使用多边形近似圆角矩形（8边形近似）
                                card_path = (f"m {r} 0 "
                                            f"l {w-r} 0 "
                                            f"l {w} {r} "
                                            f"l {w} {h-r} "
                                            f"l {w-r} {h} "
                                            f"l {r} {h} "
                                            f"l 0 {h-r} "
                                            f"l 0 {r} "
                                            "c")
                                # 填充背景
                                card_ass = f"{{\\p1\\c&H{convert_to_ass_color(rice_paper_color)[2:]}&\\1a&H19&\\an7\\pos({card_x},{card_y})}} {card_path} {{\\p0}}\n"
                                ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{card_ass}"
                                # 绘制1px浅驼色边框
                                border_ass = f"{{\\p1\\c&H{convert_to_ass_color(border_color)[2:]}&\\1a&H00&\\an7\\pos({card_x},{card_y})}} {card_path} {{\\p0}}\n"
                                ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{border_ass}"

                                # ========== 字段标题（左侧朱砂竖线 + 墨黑文字 + Bold字重）=========
                                field_label_clean = field_label.replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')

                                # 左侧朱砂竖线（参考HTML .block-title::before）
                                vertical_bar_width = 6
                                vertical_bar_height = field_font_size * 0.6
                                bar_ass = f"{{\\p1\\c&H{convert_to_ass_color(accent_color)[2:]}&\\1a&H00&\\an7\\pos({content_start_x},{global_y + 15})}} m 0 0 l {vertical_bar_width} 0 l {vertical_bar_width} {vertical_bar_height} l 0 {vertical_bar_height} {{\\p0}}\n"
                                ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{bar_ass}"

                                # 字段名（墨黑，Bold字重，位于竖线右侧）
                                title_text_offset = vertical_bar_width + 18
                                name_x = content_start_x + title_text_offset
                                name_ass = f"{{\\fn楷体\\fs{field_font_size}\\b1\\c&H{convert_to_ass_color(title_text_color)[2:]}&\\3c&H{convert_to_ass_color(title_border_color)[2:]}&\\3a&H00&\\bord4\\an7\\pos({name_x},{global_y})}}{field_label_clean}\n"
                                ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{name_ass}"
                                global_y += 80

                                # ========== 字段内容（淡墨灰，Regular字重，与竖线对齐，首行缩进两格）=========
                                content_x = content_start_x
                                max_line_width = 13  # 换行计算保持13个字，只有第一行显示时添加缩进

                                if field_value:
                                    value_lines = smart_split_by_width(field_value, max_line_width, field_label, first_line_indent_width=2)

                                    for line_idx, line in enumerate(value_lines):
                                        line_clean = line.replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')

                                        # 内容文字（黑字白边，与compositeImageIntroVideo一致）
                                        # 添加两个全角空格作为首行缩进
                                        indented_line = '　　' + line_clean if line_idx == 0 else line_clean
                                        line_ass = f"{{\\fn楷体\\fs{content_font_size}" \
                                                   f"\\c&H{convert_to_ass_color('#212121')[2:]}&" \
                                                   f"\\3c&H{convert_to_ass_color('#FFFFFF')[2:]}&" \
                                                   f"\\3a&H00&" \
                                                   f"\\xbord6\\ybord6" \
                                                   f"\\shad0" \
                                                   f"\\an7" \
                                                   f"\\pos({content_x},{global_y})" \
                                                   f"}}{indented_line}\n"
                                        ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{line_ass}"
                                        global_y += line_height

                                # ========== 页码（右下角）==========
                                page_num_x = card_x + card_width - 40
                                page_num_y = card_y + card_height - 45
                                page_num_font_size = 42  # 增大字体
                                # 使用深色页码，加粗，加粗边框，更显眼
                                page_num_ass = f"{{\\fs{page_num_font_size}\\b1\\c&H{convert_to_ass_color('#5A4A3A')[2:]}&\\3c&H{convert_to_ass_color('#F5F0E8')[2:]}&\\3a&H00&\\bord4\\an3\\pos({page_num_x},{page_num_y})}}{field_idx+1}/4\n"
                                ass_content += f"Dialogue: 0,{sec2ass(current_time)},{sec2ass(current_time + page_duration)},Default,,0,0,0,,{page_num_ass}"

                                # 保存ASS
                                ass_path = os.path.join(out_dir_path, f'temp_detail_{field_idx}.ass')
                                with open(ass_path, 'w', encoding='utf-8') as f:
                                    f.write(ass_content)

                                output_path = os.path.join(out_dir_path, f'page_detail_{field_idx}.mp4')

                                # 创建视频
                                async def create_detail_video():
                                    temp_video_path = output_path.replace('.mp4', '_temp.mp4')
                                    # 背景图转换为视频
                                    await image_to_video(bg_image_path, 8, temp_video_path)
                                    await add_subtitles(ass_path, temp_video_path, output_path)
                                    if os.path.exists(temp_video_path):
                                        os.remove(temp_video_path)

                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    loop.run_until_complete(create_detail_video())
                                finally:
                                    loop.close()

                                if os.path.exists(ass_path):
                                    os.remove(ass_path)

                                output_videos.append(output_path)
                                total_duration += 8

            # 合并所有视频片段
            if output_videos:
                self.add_log(f'开始合并{len(output_videos)}个视频片段')
                QApplication.processEvents()

                # 随机选择过渡效果
                transition_effects = ['0', '1', '2', '3']  # 0:硬切, 1:淡入淡出, 2:左滑, 3:右滑
                transition = random.choice(transition_effects)
                transition_duration = 0.8  # 过渡时长0.8秒

                self.add_log(f'使用过渡效果{transition}合并{len(output_videos)}个视频片段')
                QApplication.processEvents()

                # 合并视频 - 清理标题中的非法字符
                video_name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', title) + '.mp4'
                final_output_path = os.path.join(out_dir_path, video_name)
                from ffmpeg_tool.video_concat_tool import concatenate_videos_in_segments
                concatenate_videos_in_segments(output_videos, final_output_path, transition, transition_duration)

                if os.path.exists(final_output_path):
                    self.add_log(f'视频合成完成: {final_output_path}')
                    QApplication.processEvents()

                    # 添加背景音乐
                    parent_dir = os.getcwd()
                    bg_music_dir = os.path.join(parent_dir, 'cacheMusic2')
                    mp3_files = [f for f in os.listdir(bg_music_dir) if f.lower().endswith('.mp3')]

                    if mp3_files:
                        random_mp3_file = random.choice(mp3_files)
                        random_mp3_path = os.path.join(bg_music_dir, random_mp3_file)

                        bgm_video_path = final_output_path.replace('.mp4', '_bgm.mp4')
                        bgAudioVolume = 40

                        addMusicWorker = AddMusicWorker(final_output_path, random_mp3_path, 100, bgAudioVolume,
                                                        bgm_video_path)
                        self.thread_pool.start(addMusicWorker)
                        addMusicWorker.signals.finished.connect(self.on_success_occurred)
                        addMusicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                        self.loop.exec()

                        if self.error_flag:
                            self.add_log('添加音乐失败')
                            QApplication.processEvents()
                        else:
                            self.add_log('已添加背景音乐')
                            # 替换为带音乐的视频路径
                            if os.path.exists(final_output_path):
                                os.remove(final_output_path)
                            os.rename(bgm_video_path, final_output_path)
                            QApplication.processEvents()
                    else:
                        self.add_log('没有找到背景音乐文件,跳过添加音乐')
                        QApplication.processEvents()

                    # 添加水印
                    watermark_location_examples = [['50', '50'], ['main_w-overlay_w-100', '50'],
                                                   ['50', 'main_h-overlay_h-50'],
                                                   ['main_w-overlay_w-50', 'main_h-overlay_h-50'],
                                                   ['(main_w-overlay_w)/2', '(main_h-overlay_h)/2'],
                                                   ['(main_w-overlay_w)/2', '50'],
                                                   ['(main_w-overlay_w)/2', 'main_h-overlay_h-100']]

                    watermark_setting = {
                        'watermark_location': watermark_location_examples[
                            self.all_setting_dict['water_set']['position']],
                        'zoom_size': self.all_setting_dict['water_set']['zoom'],
                        'pic_alpha': self.all_setting_dict['water_set']['alpha']
                    }
                    watermarked_output_path = final_output_path.replace('.mp4', '_wm.mp4')
                    add_text_watermark_worker = AddWatermarkWorker(final_output_path, watermarked_output_path,
                                                                   watermark_setting, 2,
                                                                   self.all_setting_dict['water_set']['filePath'])
                    self.thread_pool.start(add_text_watermark_worker)
                    add_text_watermark_worker.signals.finished.connect(self.on_success_occurred)
                    add_text_watermark_worker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        self.add_log('添加水印失败')
                        QApplication.processEvents()
                    else:
                        self.add_log('已添加水印')
                        # 重命名为最终路径
                        if os.path.exists(watermarked_output_path):
                            os.remove(final_output_path)
                            os.rename(watermarked_output_path, final_output_path)
                    QApplication.processEvents()

                    # 上传任务信息
                    account_result = self.get_upload_accounts(account_name)
                    if len(account_result) > 0:
                        for (account, mac) in account_result:
                            task_param = {
                                'name': account_name,
                                'account': account,
                                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'title': title.replace('|', ''),
                                'mac': mac,
                                'tag': tags,
                                'path': final_output_path,
                                'describe': f'{title} - 节日风俗视频',
                                'classify': '民俗',
                                'task_type': 12,
                            }
                            add_user_task(task_param)
                            self.add_log(f'{account_name}{account}节日风俗视频任务: {final_output_path}')
                            QApplication.processEvents()
                else:
                    self.add_log('视频合成失败')
            else:
                self.add_log('没有可合并的视频片段')

        except Exception as e:
            self.add_log(f'节日风俗类视频合成出错: {str(e)}')
            import traceback
            traceback.print_exc()

    # 创建页面视频的辅助函数
    async def create_page_video(self, image_path, duration, output_path, ass_path):
        """将背景图片转换为视频并添加ASS字幕"""
        from ffmpeg_tool.pic_trans_to_video import image_to_video
        from ffmpeg_tool.subtitles_audio_tool import add_subtitles

        # 1. 图片转视频
        temp_video_path = output_path.replace('.mp4', '_temp.mp4')
        await image_to_video(image_path, duration, temp_video_path)

        # 2. 添加ASS字幕
        await add_subtitles(ass_path, temp_video_path, output_path)

        # 3. 删除临时文件
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)

        # 辅助函数:秒转ASS时间格式

    def sec2ass(sec: float) -> str:
        """秒 → 0:00:00.00 格式"""
        h, rem = divmod(sec, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h):01d}:{int(m):02d}:{s:05.2f}"

    # 地方攻略类（支持美食、特产、地方特色等）
    # 地方攻略类视频合成
    def compositeLocalStrategyVideo(self, copy_file, label_file, out_dir_path, account_name):
        self.add_log('开始合成地方攻略类视频')
        QApplication.processEvents()

        # 计算文本的实际显示宽度（中文字符/全角标点=1，英文字符/数字/半角标点=0.5）
        def get_text_display_width(text):
            total_width = 0
            for char in text:
                # 中文字符
                if '\u4e00' <= char <= '\u9fff':
                    total_width += 1
                # 全角标点符号（与汉字同宽）- 含中文单双引号
                elif char in '，。、；：！？""''（）【】《》''""':
                    total_width += 1
                # 英文、数字、半角标点
                elif ('a' <= char <= 'z') or ('A' <= char <= 'Z') or ('0' <= char <= '9') or char in '.,;:?!-+*/()[]{}"<>\'':
                    total_width += 0.5
                else:
                    total_width += 1
            return total_width

        # 基于显示宽度的智能换行函数
        def smart_split_by_width(text, max_width, field_label):
            lines = []
            current_line = ""
            current_width = 0
            i = 0
            while i < len(text):
                char = text[i]
                # 与 get_text_display_width 保持一致的宽度计算
                if '\u4e00' <= char <= '\u9fff':
                    char_width = 1  # 汉字
                elif char in '，。、；：！？""''（）【】《》''""':
                    char_width = 1  # 全角标点符号
                elif ('a' <= char <= 'z') or ('A' <= char <= 'Z') or ('0' <= char <= '9') or char in '.,;:?!-+*/()[]{}"<>\'':
                    char_width = 0.5  # 英文/数字/半角标点
                else:
                    char_width = 1  # 其他字符
                if current_width + char_width > max_width and current_line:
                    lines.append(current_line.strip())
                    current_line = ""
                    current_width = 0
                if char in '【《':
                    bracket_content = ""
                    bracket_width = 0
                    j = i
                    match_char = '】' if char == '【' else '》'
                    depth = 1
                    j += 1
                    while j < len(text) and depth > 0:
                        if text[j] == char:
                            depth += 1
                        elif text[j] == match_char:
                            depth -= 1
                            if depth == 0:
                                break
                        j += 1
                    if depth == 0:
                        bracket_content = text[i:j+1]
                        bracket_width = get_text_display_width(bracket_content)
                        if current_line and current_width + bracket_width > max_width:
                            lines.append(current_line.strip())
                            current_line = ""
                            current_width = 0
                        current_line += bracket_content
                        current_width += bracket_width
                        i = j + 1
                        continue
                current_line += char
                current_width += char_width
                i += 1
            if current_line.strip():
                lines.append(current_line.strip())
            return lines

        self.all_setting_dict = read_dict_from_txt('setting.txt')

        if self.randomVideoModelCheckBox.isChecked():
            model_result = get_random_video_model()
            model_set_dict = json.loads(model_result['model_set'])
            self.all_setting_dict['title_set'] = model_set_dict['title_set']
            self.add_log(f'已应用随机视频模板，字体: {model_set_dict["title_set"]["fontFamily"]}')

        clean_cut_cache()
        clean_cache()

        copy_start_num = get_first_data_row(copy_file)
        label_start_num = get_first_data_row(label_file)

        self.add_log(f'读取视频文案,文案文件路径是{str(copy_file)}')

        while True:
            video_title_text = get_row_data(copy_file, copy_start_num)
            self.add_log('读取视频文案')
            QApplication.processEvents()

            if len(video_title_text) < 3:
                self.add_log('全部生成完成')
                QApplication.processEvents()
                break

            video_title = video_title_text[0].strip()
            video_fabu_tag = video_title_text[1].strip()
            label_text = get_row_data(label_file, label_start_num)
            video_text = video_title_text[2:]
            video_text_part_num = len(video_text)

            if video_text_part_num <= 0:
                copy_start_num += 1
                logging.debug(f'文案数据为空')
                continue

            # 解析JSON格式的美食数据（新格式：每页包含2个美食）
            food_data_list = []
            for json_str in video_text:
                try:
                    page_data = json.loads(json_str)
                    food_data_list.append(page_data)
                except json.JSONDecodeError as e:
                    self.add_log(f'解析美食数据失败: {e}')
                    QApplication.processEvents()
                    continue

            if not food_data_list:
                self.add_log('没有有效的美食数据')
                copy_start_num += 1
                continue

            self.add_log(f'成功解析 {len(food_data_list)} 页美食数据')
            QApplication.processEvents()

            # 视频处理缓存文件夹
            tamp_folder_name = 'tempConcateVideo'
            current_directory = os.getcwd()
            tamp_folder_path = os.path.join(current_directory, tamp_folder_name)
            video_tamp_path_name = 'video_cache_file'
            video_tamp_path = os.path.join(tamp_folder_path, video_tamp_path_name)

            # 从数据库获取匹配的视频，截取背景图
            bg_image_path = os.path.join(video_tamp_path, f'bg_{copy_start_num}.jpg')
            bg_success = False

            try:
                ftp_videos = []
                video_tag = ''
                # 使用美食相关标签
                food_tags = ['美食', '小吃', '食物']
                for i in range(min(video_text_part_num, len(label_text))):
                    base_tag = label_text[i].split(',')[0]
                    # 组合地名+美食标签
                    for food_tag in food_tags:
                        video_tag = f"{base_tag},{food_tag}"
                        ftp_videos = get_videos_by_keyword_1(
                            base_tag, 0, "", 10
                        )
                        if ftp_videos and len(ftp_videos) > 0:
                            break
                    if ftp_videos and len(ftp_videos) > 0:
                        break

                if ftp_videos and len(ftp_videos) > 0:
                    video_info = random.choice(ftp_videos)
                    video_id = video_info['id']
                    self.add_log(f'根据标签"{video_tag}"找到视频ID: {video_id}')
                    QApplication.processEvents()

                    video_path = download_cn_video(video_id, 0)
                    if video_path and os.path.exists(video_path):
                        self.add_log(f'视频下载成功: {video_path}')
                        QApplication.processEvents()

                        from ffmpeg_tool.video_concat_tool import extract_and_blur_random_frame
                        if extract_and_blur_random_frame(
                            video_path, bg_image_path, target_width=1080, target_height=1920, blur_sigma=5
                        ):
                            self.add_log(f'背景图生成成功: {bg_image_path}')
                            QApplication.processEvents()
                            bg_success = True
                        else:
                            self.add_log(f'背景图生成失败')
                            QApplication.processEvents()

                        try:
                            os.remove(video_path)
                            self.add_log(f'已删除临时视频: {video_path}')
                            QApplication.processEvents()
                        except Exception as e:
                            print(f'删除视频失败: {str(e)}')
                    else:
                        self.add_log(f'视频下载失败')
                        QApplication.processEvents()
                else:
                    self.add_log(f'未找到匹配标签"{video_tag}"的视频')
                    QApplication.processEvents()
            except Exception as e:
                self.add_log(f'获取背景图时出错: {str(e)}')
                QApplication.processEvents()

            if not bg_success:
                self.add_log(f'跳过当前视频（无法生成背景图）')
                QApplication.processEvents()
                copy_start_num += 1
                continue

            # 每页显示8秒（每页2个美食）
            PAGE_DURATION = 8.0
            self.add_log(f'计算每页显示时长: {PAGE_DURATION}秒')
            QApplication.processEvents()

            # 生成每页的视频和字幕
            page_video_list = []
            total_duration = 0

            # 定义颜色（特产类新样式）
            main_title_color = '#FFFFFF'
            page_title_color = '#FFC107'
            card_bg_color = '#FFFFFF'
            name_title_bg_color = '#FFC107'
            name_title_text_color = '#1A1A1A'
            content_text_color = '#333333'
            price_text_color = '#C41E3A'
            price_icon_bg_color = '#C41E3A'

            # 辅助函数：计算单个项目所需高度（支持限制最大高度）
            def estimate_item_height_local(item_content, card_padding, name_title_height, max_desc_lines=None):
                if not item_content:
                    return 0
                item_name = item_content.get('名称', '')
                item_desc = item_content.get('简介/特色', '')
                item_price = item_content.get('价格信息', '')

                # 计算名称行数（考虑换行）
                name_lines_count = 1
                if item_name:
                    name_clean = item_name
                    if not (name_clean.startswith('【') and name_clean.endswith('】')):
                        name_display = f"【{name_clean}】"
                    else:
                        name_display = name_clean
                    max_name_width = 13
                    if get_text_display_width(name_display) > max_name_width:
                        name_lines = smart_split_by_width(name_display, max_name_width, '名称')
                        name_lines_count = min(len(name_lines), 2)
                # 标题栏高度根据行数调整（每行60像素）
                adjusted_name_height = max(name_title_height, 55 + name_lines_count * 60)

                # 基础高度：上下padding + 标题栏 + 间距
                height = card_padding + adjusted_name_height + 20  # 间隙缩小（25->20）

                # 描述内容高度
                if item_desc:
                    max_desc_width_first = 12  # 与渲染一致
                    max_desc_width_other = 14  # 与渲染一致
                    total_width = get_text_display_width(item_desc)
                    desc_lines = 1
                    if total_width > max_desc_width_first:
                        first_line_lines = smart_split_by_width(item_desc, max_desc_width_first, '简介/特色')
                        desc_lines = 1  # 第一行
                        if len(first_line_lines) > 1:
                            remaining_text = ''.join(first_line_lines[1:])
                            other_lines = smart_split_by_width(remaining_text, max_desc_width_other, '简介/特色')
                            desc_lines += len(other_lines)
                    # 如果指定了最大行数，限制高度
                    if max_desc_lines is not None:
                        desc_lines = min(desc_lines, max_desc_lines)
                    height += desc_lines * 65 + 20  # 行高和间隙缩小

                # 价格高度
                if item_price:
                    max_price_width = 12  # 调整宽度以平衡空间利用和视觉效果
                    price_clean = item_price.replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
                    if get_text_display_width(price_clean) > max_price_width:
                        price_lines = smart_split_by_width(price_clean, max_price_width, '价格信息')
                        height += len(price_lines) * 55 + 15  # 行高和间隙缩小
                    else:
                        height += 55 + 15

                height += card_padding  # 底部padding
                return height

            # 辅助函数：计算描述内容的行数
            def calculate_desc_lines(item_desc):
                if not item_desc:
                    return 0
                max_desc_width_first = 12  # 减少2个字（从14改为12）
                max_desc_width_other = 14  # 减少2个字（从16改为14）
                total_width = get_text_display_width(item_desc)
                if total_width <= max_desc_width_first:
                    return 1
                first_line_lines = smart_split_by_width(item_desc, max_desc_width_first, '简介/特色')
                desc_lines = 1
                if len(first_line_lines) > 1:
                    remaining_text = ''.join(first_line_lines[1:])
                    other_lines = smart_split_by_width(remaining_text, max_desc_width_other, '简介/特色')
                    desc_lines += len(other_lines)
                return desc_lines

            # 辅助函数：截取指定行数的描述内容
            def truncate_desc_to_lines(item_desc, max_lines):
                if not item_desc or max_lines <= 0:
                    return "", item_desc
                max_desc_width_first = 12  # 减少2个字
                max_desc_width_other = 14  # 减少2个字
                all_lines = []
                # 第一行
                first_line_lines = smart_split_by_width(item_desc, max_desc_width_first, '简介/特色')
                if first_line_lines:
                    all_lines.append(first_line_lines[0])
                    if len(first_line_lines) > 1 and max_lines > 1:
                        remaining_text = ''.join(first_line_lines[1:])
                        other_lines = smart_split_by_width(remaining_text, max_desc_width_other, '简介/特色')
                        for line in other_lines[:max_lines-1]:
                            all_lines.append(line)
                shown_text = ''.join(all_lines)
                # 计算剩余内容
                remaining_start = len(shown_text)
                remaining_text = item_desc[remaining_start:].strip()
                return shown_text, remaining_text

            # 收集所有需要显示的项目
            all_pages_items = []
            for page_idx, page_data in enumerate(food_data_list):
                page_title = ""
                for key in page_data.keys():
                    page_title = key
                    break

                items_on_page = page_data.get(page_title, {})
                item1 = items_on_page.get("项目1", {})
                item2 = items_on_page.get("项目2", {})

                if item1:
                    all_pages_items.append({
                        'page_title': page_title,
                        'item': item1,
                        'original_page': page_idx
                    })
                if item2:
                    all_pages_items.append({
                        'page_title': page_title,
                        'item': item2,
                        'original_page': page_idx
                    })

            # 智能分页：根据内容高度决定每页显示几个卡片
            card_padding = 30
            name_title_height = 72  # 从80改为72
            card_gap = 30  # 从40改为30

            # 计算标题占用高度（注意：标题字体改小了，行高也相应调整）
            title_lines_count = 1
            video_title_clean = video_title.replace('|', '').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
            title_max_width = 8  # 从10改为8
            if get_text_display_width(video_title_clean) > title_max_width:
                title_lines_list = smart_split_by_width(video_title_clean, title_max_width, '标题')
                title_lines_count = min(len(title_lines_list), 2)
            header_height = 260 + 40 + title_lines_count * 85 + 20 + 70  # 间隙和行高都缩小

            max_content_y = 1800  # 安全边界（缩小一些，从1750改为1800）
            available_height = max_content_y - header_height

            # 分页处理（支持单个项目拆分到多页）
            page_groups = []
            current_group = []
            current_group_height = 0

            for item_data in all_pages_items:
                item = item_data['item']
                item_desc = item.get('简介/特色', '') if item else ''
                total_desc_lines = calculate_desc_lines(item_desc)
                item_height = estimate_item_height_local(item, card_padding, name_title_height)

                if current_group_height + item_height + (card_gap if current_group else 0) <= available_height:
                    # 能完整放下
                    current_group.append(item_data)
                    current_group_height += item_height + (card_gap if len(current_group) > 1 else 0)
                elif not current_group:
                    # 当前组为空，但单个项目就超出整页高度，需要拆分
                    # 计算能显示多少行描述
                    header_footer_height = card_padding + name_title_height + 20 + card_padding  # 基础高度（无描述，间隙统一为20）
                    price_height = 0
                    item_price = item.get('价格信息', '') if item else ''
                    if item_price:
                        price_height = 80  # 价格区域大约高度
                    usable_height = available_height - header_footer_height - price_height
                    max_lines_can_show = max(1, usable_height // 65)  # 每行65像素（行高缩小）

                    # 拆分到多页
                    remaining_desc = item_desc
                    part_num = 0
                    while remaining_desc:
                        shown_desc, remaining_desc = truncate_desc_to_lines(remaining_desc, max_lines_can_show)
                        if shown_desc:
                            part_num += 1
                            # 创建分页项目
                            split_item = {
                                'page_title': item_data['page_title'],
                                'item': {
                                    '名称': item.get('名称', ''),
                                    '简介/特色': shown_desc,
                                    '价格信息': item_price if part_num == 1 else ''  # 只有第一页显示价格
                                },
                                'original_page': item_data['original_page'],
                                'is_split': True,
                                'part_num': part_num
                            }
                            page_groups.append([split_item])
                        if not remaining_desc:
                            break
                    current_group_height = 0
                else:
                    # 放不下，保存当前组并开始新组
                    if current_group:
                        page_groups.append(current_group)
                    current_group = [item_data]
                    current_group_height = item_height

            if current_group:
                page_groups.append(current_group)

            self.add_log(f'内容分为 {len(page_groups)} 页显示')
            QApplication.processEvents()

            # 逐页生成
            for group_idx, page_items in enumerate(page_groups):
                current_page_num = group_idx + 1
                page_title = page_items[0]['page_title'] if page_items else ""

                self.add_log(f'正在处理第{current_page_num}页，包含 {len(page_items)} 个项目')
                QApplication.processEvents()

                # 创建ASS字幕
                food_title_set = self.all_setting_dict['title_set'].copy()
                food_title_set['fontFamily'] = '黑体'
                food_title_set['fontSize'] = 24
                ass_header = file_create_title_ass_header(food_title_set, play_res_x=1080, play_res_y=1920)
                ass_events = ''
                global_current_y = 260

                # 总标题（重新计算换行）
                main_title_font_size = 75  # 字体调小
                video_title_clean = video_title.replace('|', '').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
                title_max_width = 9  # 减少换行字数条件
                title_lines = []
                if get_text_display_width(video_title_clean) > title_max_width:
                    title_lines = smart_split_by_width(video_title_clean, title_max_width, '标题')
                else:
                    title_lines = [video_title_clean]
                if len(title_lines) > 2:
                    title_lines = title_lines[:2]

                title_line_height = 85  # 行高调小
                for line_idx, title_line in enumerate(title_lines):
                    line_y = global_current_y + 40 + line_idx * title_line_height
                    main_title_ass_code = f"{{\\fs{main_title_font_size}\\b1\\c&H{convert_to_ass_color(main_title_color)[2:]}&\\3c&H1A1A1A&\\bord6\\shad0\\an2\\pos(540,{line_y})}} {title_line}\\N"
                    ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(PAGE_DURATION)},Default,,0,0,0,,{main_title_ass_code}\n"
                global_current_y += 40 + len(title_lines) * title_line_height + 20

                # 页标题
                page_title_font_size = 48  # 字体调小
                page_title_clean = page_title.replace('|', '').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
                page_title_ass_code = f"{{\\fs{page_title_font_size}\\b1\\c&H{convert_to_ass_color(page_title_color)[2:]}&\\3c&H1A1A1A&\\bord3\\an2\\pos(540,{global_current_y + 10})}} {page_title_clean}\\N"
                ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(PAGE_DURATION)},Default,,0,0,0,,{page_title_ass_code}\n"
                global_current_y += 70  # 间隙缩小

                # 卡片布局参数
                card_width = 900
                card_x = (1080 - card_width) // 2
                corner_radius = 35
                card_gap = 30  # 卡片间隙缩小（从40改为30）

                # 显示当前页的项目
                for item_idx, page_item in enumerate(page_items):
                    item_content = page_item['item']
                    if not item_content:
                        continue

                    # 获取字段内容
                    item_name = item_content.get('名称', '')
                    item_desc = item_content.get('简介/特色', '')
                    item_price = item_content.get('价格信息', '')

                    if not item_name:
                        continue

                    # 字体大小（调小）
                    name_font_size = 55  # 从62改为55
                    desc_font_size = 48  # 从54改为48
                    price_font_size = 46  # 从52改为46

                    # 名称标题栏高度
                    name_title_height = 72  # 从80改为72

                    # 计算卡片起始Y位置
                    card_start_y = global_current_y

                    # 描述内容 - 预先计算行数
                    max_desc_width_first = 12  # 减少2个字（从14改为12）
                    max_desc_width_other = 14  # 减少2个字（从16改为14）
                    desc_lines = []
                    if item_desc:
                        desc_clean = item_desc.replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
                        total_width = get_text_display_width(item_desc)
                        if total_width > max_desc_width_first:
                            first_line_lines = smart_split_by_width(item_desc, max_desc_width_first, '简介/特色')
                            if first_line_lines:
                                desc_lines.append(first_line_lines[0])
                                if len(first_line_lines) > 1:
                                    remaining_text = ''.join(first_line_lines[1:])
                                    other_lines = smart_split_by_width(remaining_text, max_desc_width_other, '简介/特色')
                                    desc_lines.extend(other_lines)
                        else:
                            desc_lines = [desc_clean]
                        # 不限制描述行数，让卡片根据内容自适应高度

                    # 预先计算价格行数（限制宽度防止超出卡片）
                    price_lines = []
                    if item_price:
                        price_clean = item_price.replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
                        max_price_width = 12  # 调整宽度以平衡空间利用和视觉效果
                        if get_text_display_width(price_clean) > max_price_width:
                            price_lines = smart_split_by_width(price_clean, max_price_width, '价格信息')
                        else:
                            price_lines = [price_clean]

                    # 计算卡片高度（根据实际行数自适应）
                    card_height = card_padding
                    card_height += name_title_height + 20  # 间隙缩小（25->20）
                    if desc_lines:
                        card_height += len(desc_lines) * 65 + 20  # 行高缩小（75->65），间隙缩小（25->20）
                    if price_lines:
                        card_height += len(price_lines) * 55 + 15  # 行高缩小（60->55），间隙缩小（20->15）
                    card_height += card_padding

                    # 绘制白色半透明圆角卡片背景
                    card_bg_alpha = '80'  # 更透明
                    r = corner_radius
                    cw = card_width
                    ch = card_height

                    # 使用简单的圆角矩形路径（简化版，4个圆角）
                    # 左上圆角开始
                    card_bg_path = (f"m {r} 0 "
                                   f"l {cw-r} 0 b {cw} 0 {cw} 0 {cw} {r} "
                                   f"l {cw} {ch-r} b {cw} {ch} {cw} {ch} {cw-r} {ch} "
                                   f"l {r} {ch} b 0 {ch} 0 {ch} 0 {ch-r} "
                                   f"l 0 {r} b 0 0 0 0 {r} 0")
                    card_bg_ass = f"{{\\p1\\c&H{convert_to_ass_color(card_bg_color)[2:]}&\\1a&H{card_bg_alpha}&\\an7\\pos({card_x},{card_start_y})}} {card_bg_path}{{\\p0}}"
                    ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(PAGE_DURATION)},Default,,0,0,0,,{card_bg_ass}\n"

                    # 绘制白色半透明圆角边框
                    border_color = '#FFFFFF'
                    border_alpha = '80'
                    border_thickness = 4

                    # 外框路径（比背景大一点形成边框效果）
                    border_path = (f"m {r} 0 "
                                  f"l {cw-r} 0 b {cw} 0 {cw} 0 {cw} {r} "
                                  f"l {cw} {ch-r} b {cw} {ch} {cw} {ch} {cw-r} {ch} "
                                  f"l {r} {ch} b 0 {ch} 0 {ch} 0 {ch-r} "
                                  f"l 0 {r} b 0 0 0 0 {r} 0 "
                                  f"m {border_thickness} {r} "
                                  f"l {border_thickness} {ch-r} b {border_thickness} {ch-border_thickness} {border_thickness} {ch-border_thickness} {r} {ch-border_thickness} "
                                  f"l {cw-r} {ch-border_thickness} b {cw-border_thickness} {ch-border_thickness} {cw-border_thickness} {ch-border_thickness} {cw-border_thickness} {ch-r} "
                                  f"l {cw-border_thickness} {r} b {cw-border_thickness} {border_thickness} {cw-border_thickness} {border_thickness} {cw-r} {border_thickness} "
                                  f"l {r} {border_thickness} b {border_thickness} {border_thickness} {border_thickness} {border_thickness} {border_thickness} {r}")
                    border_ass = f"{{\\p1\\c&H{convert_to_ass_color(border_color)[2:]}&\\1a&H{border_alpha}&\\an7\\pos({card_x},{card_start_y})}} {border_path}{{\\p0}}"
                    ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(PAGE_DURATION)},Default,,0,0,0,,{border_ass}\n"

                    # 重置当前Y到卡片内容起始位置
                    card_current_y = card_start_y + card_padding

                    # 黄色标题栏背景（简化版矩形）
                    name_title_width = card_width - card_padding * 2
                    name_title_ass = f"{{\\p1\\c&H{convert_to_ass_color(name_title_bg_color)[2:]}&\\1a&H00&\\an7\\pos({card_x + card_padding},{card_current_y})}} m 0 0 l {name_title_width} 0 l {name_title_width} {name_title_height} l 0 {name_title_height}{{\\p0}}"
                    ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(PAGE_DURATION)},Default,,0,0,0,,{name_title_ass}\n"

                    # 特产名称文字（居中，在色块中间）- 去掉【】，因为数据里可能已经有了
                    name_clean = item_name.replace('|', '｜').replace('\\', '＼').replace('{', '｛').replace('}', '｝')
                    # 如果名称已经有【】就不再加
                    if not (name_clean.startswith('【') and name_clean.endswith('】')):
                        display_name = f"【{name_clean}】"
                    else:
                        display_name = name_clean
                    
                    # 名称换行处理（限制宽度防止溢出）
                    max_name_width = 13  # 名称最多13个汉字宽度
                    name_lines = []
                    if get_text_display_width(display_name) > max_name_width:
                        name_lines = smart_split_by_width(display_name, max_name_width, '名称')
                    else:
                        name_lines = [display_name]
                    # 限制名称最多2行
                    if len(name_lines) > 2:
                        name_lines = name_lines[:2]
                    
                    # 调整Y位置到标题栏正中间
                    name_line_height = name_font_size + 5
                    name_start_y = card_current_y + name_title_height//2 - (len(name_lines) - 1) * name_line_height // 2 + 26
                    for name_line_idx, name_line in enumerate(name_lines):
                        name_y = name_start_y + name_line_idx * name_line_height
                        name_ass_code = f"{{\\fs{name_font_size}\\b1\\c&H{convert_to_ass_color(name_title_text_color)[2:]}&\\3c&HFFFFFF&\\3a&H00&\\xbord6\\ybord6\\shad0\\an2\\pos(540,{name_y})}}{name_line}\\N"
                        ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(PAGE_DURATION)},Default,,0,0,0,,{name_ass_code}\n"
                    card_current_y += name_title_height + 20  # 间隙缩小

                    # 描述内容（直接显示，无字段标题，第一行空两个字）
                    if desc_lines:
                        line_height = 65  # 行高缩小（75->65）
                        for desc_line_idx, desc_line in enumerate(desc_lines):
                            # 确保不超出卡片右边界，只有第一行开头添加两个全角空格
                            if desc_line_idx == 0:
                                desc_with_indent = "\u3000\u3000" + desc_line
                            else:
                                desc_with_indent = desc_line
                            desc_ass_code = f"{{\\fs{desc_font_size}\\c&H{convert_to_ass_color(content_text_color)[2:]}&\\3c&HFFFFFF&\\3a&H00&\\xbord6\\ybord6\\shad0\\an7\\pos({card_x + card_padding + 15},{card_current_y})}}{desc_with_indent}\\N"
                            ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(PAGE_DURATION)},Default,,0,0,0,,{desc_ass_code}\n"
                            card_current_y += line_height
                        card_current_y += 20  # 间隙缩小（25->20）

                    # 价格信息（圆形¥图标 + 黄色文字）
                    if price_lines:
                        # 绘制红色圆形¥图标
                        icon_size = 65  # 增大图标
                        icon_center_x = card_x + card_padding + 32
                        icon_center_y = card_current_y + 32

                        # 使用多边形近似圆形（12边形）- 增大后的坐标
                        circle_ass = f"{{\\p1\\c&H{convert_to_ass_color(price_icon_bg_color)[2:]}&\\an7\\pos({icon_center_x - icon_size//2},{icon_center_y - icon_size//2})}} m 32 0 l 48 6 l 59 17 l 65 32 l 59 47 l 48 58 l 32 65 l 17 58 l 6 47 l 0 32 l 6 17 l 17 6{{\\p0}}"
                        ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(PAGE_DURATION)},Default,,0,0,0,,{circle_ass}\n"

                        # ¥符号（增大字体，调整位置使其在圆圈正中 - 往右下移）
                        yuan_ass = f"{{\\fs{50}\\b1\\c&HFFFFFF&\\an2\\pos({icon_center_x + 3},{icon_center_y + 18})}}¥\\N"
                        ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(PAGE_DURATION)},Default,,0,0,0,,{yuan_ass}\n"

                        # 价格文字（黄色）- 直接使用预计算的price_lines
                        price_line_height = 55  # 行高缩小（60->55）
                        price_start_y = card_current_y + 5
                        for price_line_idx, price_line in enumerate(price_lines):
                            price_y = price_start_y + price_line_idx * price_line_height
                            price_x = icon_center_x + icon_size//2 + 15
                            price_ass_code = f"{{\\fs{price_font_size}\\b1\\c&H{convert_to_ass_color(price_text_color)[2:]}&\\3c&HFFFFFF&\\3a&H00&\\xbord6\\ybord6\\shad0\\an7\\pos({price_x},{price_y})}} {price_line}\\N"
                            ass_events += f"Dialogue: 0,00:00:00.00,{sec2ass(PAGE_DURATION)},Default,,0,0,0,,{price_ass_code}\n"

                        card_current_y += max(75, len(price_lines) * price_line_height + 10)  # 间隙缩小

                    # 更新全局Y位置为下一个卡片的起始位置
                    global_current_y = card_start_y + card_height + card_gap

                # 生成当前页的ASS文件
                ass_content = ass_header + "\n" + ass_events
                page_ass_path = os.path.join(video_tamp_path, f'page_{group_idx}.ass')
                with open(page_ass_path, "w", encoding="utf-8") as f:
                    f.write(ass_content)

                # 生成当前页的视频
                page_output_path = os.path.join(video_tamp_path, f'page_{group_idx}_video.mp4')
                self.add_log(f'开始生成第{current_page_num}页视频: {page_output_path}')
                QApplication.processEvents()
                asyncio.run(self.create_page_video(bg_image_path, PAGE_DURATION, page_output_path, page_ass_path))

                if os.path.exists(page_output_path):
                    page_video_list.append(page_output_path)
                    total_duration += PAGE_DURATION
                    self.add_log(f'已生成第{current_page_num}页视频')
                    QApplication.processEvents()
                else:
                    self.add_log(f'第{current_page_num}页视频生成失败')
                    QApplication.processEvents()

            # 合并所有页面的视频
            self.add_log(f'共生成 {len(page_video_list)} 个页面视频')
            for i, video_path in enumerate(page_video_list):
                self.add_log(f'  第{i + 1}页: {video_path}')
            QApplication.processEvents()

            if len(page_video_list) > 0:
                transition_effects = ['0', '1', '2', '3']
                transition = random.choice(transition_effects)
                transition_duration = 0.8

                self.add_log(f'使用过渡效果{transition}合并{len(page_video_list)}页视频')
                QApplication.processEvents()

                merged_video_path = os.path.join(video_tamp_path, 'merged_video.mp4')
                concatenate_videos_in_segments(page_video_list, merged_video_path, transition, transition_duration)

                if not os.path.exists(merged_video_path):
                    self.add_log('视频合并失败')
                    copy_start_num += 1
                    continue

                # 添加背景音乐
                parent_dir = os.getcwd()
                bg_music_dir = os.path.join(parent_dir, 'cacheMusic2')
                mp3_files = [f for f in os.listdir(bg_music_dir) if f.lower().endswith('.mp3')]

                bgm_video_path = None
                if mp3_files:
                    random_mp3_file = random.choice(mp3_files)
                    random_mp3_path = os.path.join(bg_music_dir, random_mp3_file)
                    bgm_video_path = merged_video_path.replace('.mp4', '_bgm.mp4')
                    bgAudioVolume = 40

                    addMusicWorker = AddMusicWorker(merged_video_path, random_mp3_path, 100, bgAudioVolume, bgm_video_path)
                    self.thread_pool.start(addMusicWorker)
                    addMusicWorker.signals.finished.connect(self.on_success_occurred)
                    addMusicWorker.signals.errorOccurred.connect(self.on_error_occurred)
                    self.loop.exec()

                    if self.error_flag:
                        self.add_log('添加音乐失败')
                        copy_start_num += 1
                        continue

                    self.add_log('已添加背景音乐')
                    QApplication.processEvents()
                    final_video_path = bgm_video_path
                else:
                    self.add_log('没有找到背景音乐文件,跳过添加音乐')
                    final_video_path = merged_video_path

                # 添加水印
                watermark_location_examples = [
                    ['50', '50'], ['main_w-overlay_w-100', '50'],
                    ['50', 'main_h-overlay_h-50'], ['main_w-overlay_w-50', 'main_h-overlay_h-50'],
                    ['(main_w-overlay_w)/2', '(main_h-overlay_h)/2'],
                    ['(main_w-overlay_w)/2', '50'], ['(main_w-overlay_w)/2', 'main_h-overlay_h-100']
                ]
                watermark_setting = {
                    'watermark_location': watermark_location_examples[self.all_setting_dict['water_set']['position']],
                    'zoom_size': self.all_setting_dict['water_set']['zoom'],
                    'pic_alpha': self.all_setting_dict['water_set']['alpha']
                }
                watermarked_video_path = os.path.join(video_tamp_path, os.path.basename(final_video_path).replace('.mp4', '_watermarked.mp4'))
                add_text_watermark_worker = AddWatermarkWorker(
                    final_video_path, watermarked_video_path, watermark_setting, 2, self.all_setting_dict['water_set']['filePath']
                )
                self.thread_pool.start(add_text_watermark_worker)
                add_text_watermark_worker.signals.finished.connect(self.on_success_occurred)
                add_text_watermark_worker.signals.errorOccurred.connect(self.on_error_occurred)
                self.loop.exec()

                if self.error_flag:
                    self.add_log('添加水印失败')
                    copy_start_num += 1
                    continue

                self.add_log('已添加水印')
                QApplication.processEvents()

                # 保存最终视频
                video_name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', video_title) + '.mp4'
                final_output_path = os.path.join(out_dir_path, video_name)

                if os.path.exists(watermarked_video_path):
                    shutil.move(watermarked_video_path, final_output_path)
                    self.add_log(f'视频已保存到: {final_output_path}')
                else:
                    self.add_log(f'错误: 找不到视频文件')
                    copy_start_num += 1
                    continue

                # 清理中间文件
                for temp_file in [merged_video_path, bgm_video_path if 'bgm_video_path' in locals() else None, watermarked_video_path]:
                    if temp_file and os.path.exists(temp_file):
                        os.remove(temp_file)

                # 生成任务信息
                excel_file_path_name = '1.xls'
                excel_file_path = os.path.join(out_dir_path, excel_file_path_name)
                data_dict = {
                    "标题": video_title.replace('|', ''),
                    "标签": video_fabu_tag,
                    "文件路径": final_output_path.replace('/', '\\'),
                    "描述": f"{video_title} - 地方特色推荐",
                    "封面路径": "", "图片集合": "", "关联商品": "",
                    "分区分类": "生活", "备注": ""
                }
                write_to_old_excel(excel_file_path, data_dict)
                self.add_log(f'生成完成一个视频: {final_output_path}')
                QApplication.processEvents()

                # 上传任务信息
                account_result = self.get_upload_accounts(account_name)
                if len(account_result) > 0:
                    for (account, mac) in account_result:
                        task_param = {
                            'name': account_name, 'account': account,
                            'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'title': data_dict.get('标题'), 'mac': mac,
                            'tag': data_dict.get('标签'), 'path': data_dict.get('文件路径'),
                            'describe': data_dict.get('描述'), 'classify': data_dict.get('分区分类'),
                            'task_type': 11,
                        }
                        add_user_task(task_param)
                        self.add_log(f'{account_name}{account}上传视频任务:{final_output_path}')
                        QApplication.processEvents()

            clean_cut_cache()
            clean_cache()
            copy_start_num += 1

        self.add_log('所有视频生成完毕')
        QApplication.processEvents()

    # 展示模板
    def showModelSetList(self):

        self.modelTableWidget.clear()
        col_result, row, vol, result = get_video_model_list()
        if result is None:
            return
        self.modelTableWidget.setRowCount(row)
        self.modelTableWidget.setColumnCount(vol)

        a = 0
        for i in col_result:  # 设置表头信息，将mysql数据表中的表头信息拿出来，放进TableWidget中
            item = QtWidgets.QTableWidgetItem()
            self.modelTableWidget.setHorizontalHeaderItem(a, item)
            item = self.modelTableWidget.horizontalHeaderItem(a)
            item.setText(i[0])
            a = a + 1

        # 获取水平表头视图
        horizontal_header = self.modelTableWidget.horizontalHeader()

        # 设置表头样式表（背景色、文字颜色等）
        horizontal_header.setStyleSheet("""
            QHeaderView::section {
                background-color: rgb(56, 56, 56);
                color: white;                     
                ont-weight: bold;          /* 文字加粗 */
                border-right: 1px solid #ddd; /* 右侧边框 */
                text-align: center;         /* 文字居中 */
            }
        """)
        vertical_header = self.modelTableWidget.verticalHeader()

        vertical_header.setStyleSheet("""
            QHeaderView::section {
                background-color: rgb(56, 56, 56);
                color: white;                    
                font-weight: bold;          /* 文字加粗 */
                border-right: 1px solid #ddd; /* 右侧边框 */
                text-align: center;         /* 文字居中 */
            }
        """)

        # 填充QTableWidget
        for row_num, row_data in enumerate(result):
            for col_num, col_data in enumerate(row_data):
                item = QTableWidgetItem(str(col_data if col_data is not None else ''))
                self.modelTableWidget.setItem(row_num, col_num, item)

        self.modelTableWidget.setColumnWidth(0, 80)
        self.modelTableWidget.setColumnWidth(1, 100)
        self.modelTableWidget.setColumnWidth(2, 400)

        # 设置水平滚动条政策为总是显示
        self.modelTableWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.modelTableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.modelTableWidget.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.modelTableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

    # 获取选中行
    def on_items_selection(self):
        try:
            selected_rows = []
            for item in self.modelTableWidget.selectedItems():
                row = item.row()
                if row not in selected_rows:
                    selected_rows.append(row)

            row_datas = []
            # 获取选中行的内容
            for row in selected_rows:
                row_data = []
                for column in range(self.modelTableWidget.columnCount()):
                    item = self.modelTableWidget.item(row, column)
                    if item:
                        row_data.append(item.text())
                row_datas.append(row_data)
            return row_datas
        except Exception as e:
            print('获取行信息出错了%s' % e)
            return None

    # 获取选中的单行
    def on_item_selection(self):
        row_data = None
        try:
            selected_items = self.modelTableWidget.selectedItems()
            if selected_items:
                selected_row = selected_items[0].row()
                row_data = []
                for column in range(self.modelTableWidget.columnCount()):
                    item = self.modelTableWidget.item(selected_row, column)
                    if item:
                        row_data.append(item.text())
                return row_data
        except Exception as e:
            print('获取行信息出错了%s' % e)
            return None

    # 视频模板删除
    def video_model_delete(self):
        try:
            row_datas = self.on_items_selection()
            if row_datas is not None:
                # 弹出确认框

                # 1. 弹出确认框
                # 创建确认框
                confirmation_dialog = QMessageBox(self)
                confirmation_dialog.setWindowTitle("确认操作")
                confirmation_dialog.setText("<b style='color:white'>你是否要删除所选模板？</b>")
                confirmation_dialog.setIcon(QMessageBox.Icon.Question)  # 设置问号图标

                # 创建自定义按钮
                no_button = confirmation_dialog.addButton("No", QMessageBox.ButtonRole.RejectRole)
                yes_button = confirmation_dialog.addButton("Yes", QMessageBox.ButtonRole.AcceptRole)

                # 设置按钮样式
                yes_button.setStyleSheet("QPushButton { color: red; }")
                no_button.setStyleSheet("QPushButton { color: red; }")

                # 显示确认框并获取用户响应
                reply = confirmation_dialog.exec()

                # 2. 根据返回值决定是否继续
                if reply == QMessageBox.DialogCode.Accepted:
                    # 删除操作
                    for row_data in row_datas:
                        try:
                            if delete_video_model(row_data[0]):
                                self.showModelSetList()
                            else:
                                raise Exception
                        except Exception as e:
                            QMessageBox.information(self, "<b style='color:white'>错误</b>",
                                                    f"<b style='color:white'>数据库删除的目标模板错误{str(e)}</b>")
                else:
                    QMessageBox.information(self, "<b style='color:white'>提示</b>",
                                            f"<b style='color:white'>取消删除</b>")
            else:
                QMessageBox.information(self, "<b style='color:white'>提示</b>",
                                        f"<b style='color:white'>请选择要删除的行</b>")
        except Exception as e:
            QMessageBox.information(self, "<b style='color:white'>提示</b>",
                                    f"<b style='color:white'>视频模板删除错误{str(e)}</b>")

    # 模板选择
    def video_model_select(self):
        row_data = self.on_item_selection()
        if row_data is not None:
            set_param = {
                'id': row_data[0],
                'model_name': row_data[1],
                'model_set': row_data[2],
            }
            dictionary = json.loads(set_param['model_set'])

            self.all_setting_dict['title_set'] = dictionary['title_set']
            self.all_setting_dict['part_title_set'] = dictionary['part_title_set']
            self.all_setting_dict['srt_set'] = dictionary['srt_set']
            self.all_setting_dict['voice_set'] = dictionary['voice_set']
            self.all_setting_dict['part_title_part_0_set'] = dictionary['part_title_part_0_set']
            self.all_setting_dict['part_title_part_1_set'] = dictionary['part_title_part_1_set']
            self.all_setting_dict['part_title_part_2_set'] = dictionary['part_title_part_2_set']
            self.all_setting_dict['part_title_part_3_set'] = dictionary['part_title_part_3_set']
            self.all_setting_dict['part_title_part_4_set'] = dictionary['part_title_part_4_set']
            self.all_setting_dict['part_title_part_5_set'] = dictionary['part_title_part_5_set']
            write_dict_to_txt('setting.txt', self.all_setting_dict)
            self.all_setting_dict = read_dict_from_txt('setting.txt')
            self.init_setting()
            self.showModelSetList()
            self.modelNameLineEdit.setText(row_data[1])
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                             QMessageBox QLabel {
                             background-color: rgb(22, 23, 25);
                             color: rgb(255, 255, 255);
                            }
                            QMessageBox {
                            background-color: rgb(22, 23, 25);
                            color: rgb(255, 255, 255);
                            }
                        """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"已将当前设置改为线上模板{row_data[0]}")
            msg_box.exec()

    # 模板修改
    def video_model_update(self):
        row_data = self.on_item_selection()
        if row_data is not None:
            model_id = row_data[0]
            set_param = {
                'model_name': self.modelNameLineEdit.text().strip() or row_data[1],
                'model_set': json.dumps(read_dict_from_txt('setting.txt'), ensure_ascii=False)
            }
            if update_video_model(model_id, set_param):
                self.showModelSetList()
                msg_box = QMessageBox()
                msg_box.setStyleSheet("""
                                 QMessageBox QLabel {
                                 background-color: rgb(22, 23, 25);
                                 color: rgb(255, 255, 255);
                                }
                                QMessageBox {
                                background-color: rgb(22, 23, 25);
                                color: rgb(255, 255, 255);
                                }
                            """)
                msg_box.setWindowTitle("提示")
                msg_box.setText(f"{model_id}视频模板更新成功")
                msg_box.exec()
            else:
                msg_box = QMessageBox()
                msg_box.setStyleSheet("""
                                                 QMessageBox QLabel {
                                                 background-color: rgb(22, 23, 25);
                                                 color: rgb(255, 255, 255);
                                                }
                                                QMessageBox {
                                                background-color: rgb(22, 23, 25);
                                                color: rgb(255, 255, 255);
                                                }
                                            """)
                msg_box.setWindowTitle("提示")
                msg_box.setText(f"{model_id}视频模板更新失败")
                msg_box.exec()

    # 模板增加
    def video_model_add(self):
        if self.modelNameLineEdit.text() == '':
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                                             QMessageBox QLabel {
                                             background-color: rgb(22, 23, 25);
                                             color: rgb(255, 255, 255);
                                            }
                                            QMessageBox {
                                            background-color: rgb(22, 23, 25);
                                            color: rgb(255, 255, 255);
                                            }
                                        """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"请输入新视频模板名称")
            msg_box.exec()
            return
        set_param = {
            'model_name': self.modelNameLineEdit.text().strip(),
            'model_set': json.dumps(read_dict_from_txt('setting.txt'), ensure_ascii=False)
        }
        if add_video_model(set_param):
            self.showModelSetList()
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                                             QMessageBox QLabel {
                                             background-color: rgb(22, 23, 25);
                                             color: rgb(255, 255, 255);
                                            }
                                            QMessageBox {
                                            background-color: rgb(22, 23, 25);
                                            color: rgb(255, 255, 255);
                                            }
                                        """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"新增视频模板成功")
            msg_box.exec()
        else:
            msg_box = QMessageBox()
            msg_box.setStyleSheet("""
                                                        QMessageBox QLabel {
                                                        background-color: rgb(22, 23, 25);
                                                        color: rgb(255, 255, 255);
                                                       }
                                                       QMessageBox {
                                                       background-color: rgb(22, 23, 25);
                                                       color: rgb(255, 255, 255);
                                                       }
                                                   """)
            msg_box.setWindowTitle("提示")
            msg_box.setText(f"新增视频模板失败")
            msg_box.exec()

    def select_script_file_path(self):
        select_path = QFileDialog.getExistingDirectory(self, "Select Video Folder", "")
        if os.path.exists(select_path):
            self.scriptVideoPathLineEdit.setText(select_path)

    def get_copy_from_video(self):
        import whisper

        # model_type = input('请选择语音识别模型类型 tiny、base、small、medium、large:\n')
        model_type = 'small'
        self.add_log(f'正在加载语音识别模型openai-whisper---{model_type}，首次打开需要下载')
        QApplication.processEvents()
        print(f'正在加载语音识别模型openai-whisper---{model_type}，首次打开需要下载')
        # 加载模型（首次运行会自动下载模型）
        model = whisper.load_model(model_type)  # 中文建议用 medium 或 large
        VIDEO_SUFFIX = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.rmvb', '.m4v'}
        # excel文案文件
        timestamp = int(time.time() * 1000)  # 当前时间戳，毫秒级
        task_copy_file_name = f"{timestamp}_copy.xlsx"
        task_label_file_name = f"{timestamp}_label.xlsx"
        task_copy_file_path = os.path.join(self.scriptVideoPathLineEdit.text(), task_copy_file_name)
        task_label_file_path = os.path.join(self.scriptVideoPathLineEdit.text(), task_label_file_name)

        # 遍历文件夹中的所有文件
        for filename in os.listdir(self.scriptVideoPathLineEdit.text()):
            if os.path.isfile(os.path.join(self.scriptVideoPathLineEdit.text(), filename)):
                if os.path.splitext(filename)[1].lower() in VIDEO_SUFFIX:
                    # 构造文件的完整路径
                    file_path = os.path.join(self.scriptVideoPathLineEdit.text(), filename)
                    # 检查是否是视频文件
                    if os.path.isfile(file_path):
                        # 使用 initial_prompt 参数，确保输出简体中文
                        self.add_log('视频音频识别中')
                        QApplication.processEvents()
                        result = model.transcribe(file_path, language="zh", initial_prompt="以下是普通话的句子。")
                        # 如果仍然输出繁体字，使用 zhconv 转换为简体
                        result["text"] = zhconv.convert(result["text"], "zh-cn")
                        print(result["text"])
                        self.add_log('完成识别，处理文案中。。。')
                        QApplication.processEvents()
                        ai_worker = AiDisposeIntro(task_copy_file_path, task_label_file_path
                                                   , self.accountNameLineEdit.text(), result["text"])
                        # Ai处理识别到的文案
                        if self.videoTypeComboBox.currentIndex() == 2:
                            ai_worker = AiDisposeStrategy(task_copy_file_path, task_label_file_path,
                                                          self.accountNameLineEdit.text(), result["text"])
                        ai_worker.signals.finished.connect(self.on_success_occurred)
                        ai_worker.signals.errorOccurred.connect(self.on_error_occurred)
                        QThreadPool.globalInstance().start(ai_worker)
                        self.loop.exec()
                        self.add_log('处理完成一个文案')
                        QApplication.processEvents()

    def auto_check_update(self):
        """自动检查更新（静默）"""
        try:
            from update_system.update_config import UpdateConfig
            from update_system.update_checker import UpdateChecker

            config = UpdateConfig()
            config_data = config.load_config()

            # 只有开启自动检查才执行
            if config_data.get('auto_check_update', True):
                checker = UpdateChecker(config)

                # 检查是否应该检查更新
                if checker.should_check_update():
                    has_update, update_info = checker.check_for_updates()

                    if has_update and update_info:
                        # 发现更新，显示对话框
                        from update_system.update_ui import UpdateDialog
                        dialog = UpdateDialog(config, update_info, self)
                        dialog.show()

        except Exception as e:
            print(f"自动检查更新失败: {e}")

    def check_for_updates_manual(self):
        """手动检查更新"""
        try:
            from update_system.update_ui import check_and_show_update
            has_update = check_and_show_update(self)

            if not has_update:
                QMessageBox.information(
                    self,
                    "检查更新",
                    "当前已是最新版本！"
                )
        except Exception as e:
            QMessageBox.warning(
                self,
                "检查更新失败",
                f"无法检查更新: {e}\n请稍后重试"
            )


def clean_cache():
    # 获取当前脚本所在目录
    current_dir = os.getcwd()

    tamp_name = 'tempConcateVideo'

    video_temp_name = 'video_cache_file'

    cache_dir = os.path.join(current_dir, str(tamp_name))

    video_temp_dir = os.path.join(cache_dir, str(video_temp_name))

    # 确保缓存文件夹存在
    if not os.path.exists(video_temp_dir):
        os.makedirs(video_temp_dir)
        print(f"缓存文件夹 {video_temp_dir} 创建成功")
        return  # 如果刚创建，文件夹为空，直接返回

    # 遍历缓存文件夹中的所有文件和子文件夹
    for item in os.listdir(video_temp_dir):
        item_path = os.path.join(video_temp_dir, item)
        # 如果是文件，直接删除
        if os.path.isfile(item_path):
            os.remove(item_path)
            print(f"已删除文件: {item_path}")
        # 如果是文件夹，递归删除
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
            print(f"已删除文件夹: {item_path}")

    print(f"缓存文件夹 {video_temp_dir} 已清空")


def clean_cut_cache():
    # 获取当前脚本所在目录
    current_dir = os.getcwd()

    tamp_name = 'cacheCutVideo'

    cache_cut_dir = os.path.join(current_dir, str(tamp_name))

    # 确保缓存文件夹存在
    if not os.path.exists(cache_cut_dir):
        os.makedirs(cache_cut_dir)
        print(f"缓存文件夹 {cache_cut_dir} 创建成功")
        return  # 如果刚创建，文件夹为空，直接返回

    # 遍历缓存文件夹中的所有文件和子文件夹
    for item in os.listdir(cache_cut_dir):
        item_path = os.path.join(cache_cut_dir, item)
        # 如果是文件，直接删除
        if os.path.isfile(item_path):
            os.remove(item_path)
            print(f"已删除文件: {item_path}")
        # 如果是文件夹，递归删除
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
            print(f"已删除文件夹: {item_path}")

    print(f"缓存文件夹 {cache_cut_dir} 已清空")


def clean_title_cache():
    # 获取当前脚本所在目录
    current_dir = os.getcwd()

    tamp_name = 'temp_title'

    cache_cut_dir = os.path.join(current_dir, str(tamp_name))

    # 确保缓存文件夹存在
    if not os.path.exists(cache_cut_dir):
        os.makedirs(cache_cut_dir)
        print(f"缓存文件夹 {cache_cut_dir} 创建成功")
        return  # 如果刚创建，文件夹为空，直接返回

    # 遍历缓存文件夹中的所有文件和子文件夹
    for item in os.listdir(cache_cut_dir):
        item_path = os.path.join(cache_cut_dir, item)
        # 如果是文件，直接删除
        if os.path.isfile(item_path):
            os.remove(item_path)
            print(f"已删除文件: {item_path}")
        # 如果是文件夹，递归删除
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
            print(f"已删除文件夹: {item_path}")

    print(f"缓存文件夹 {cache_cut_dir} 已清空")


def clean_temp_files():
    """
    清理所有临时文件，包括：
    - 临时合并视频文件 (temp_merge.mp4)
    - 临时调整速度视频 (temp_adjust_*.mp4)
    - 临时最终视频 (*_temp_final_*.mp4)
    - 临时音频文件 (temp_voice.mp3, adjust_temp_voice.mp3)
    - 当前目录下的临时视频文件 (以 'tmp' 开头的文件)
    - 缓存片段文件 (cacheCutVideo 中的 clip_*.mp4 和 temp_*.txt)
    """
    import re

    current_dir = os.getcwd()
    deleted_count = 0
    deleted_size = 0

    print("🧹 开始清理临时文件...")

    # 1. 清理当前目录下的临时文件
    temp_patterns = [
        r'^temp_merge\.mp4$',
        r'^temp_adjust_.*\.mp4$',
        r'^.*_temp_final_.*\.mp4$',
        r'^temp_voice\.mp3$',
        r'^adjust_temp_voice\.mp3$',
        r'^tmp.*\.mp4$',
        r'^tmp.*\.avi$',
        r'^tmp.*\.mkv$',
    ]

    for item in os.listdir(current_dir):
        item_path = os.path.join(current_dir, item)
        if os.path.isfile(item_path):
            # 检查文件名是否匹配任何临时文件模式
            for pattern in temp_patterns:
                if re.match(pattern, item, re.IGNORECASE):
                    try:
                        file_size = os.path.getsize(item_path)
                        os.remove(item_path)
                        deleted_count += 1
                        deleted_size += file_size
                        print(f"  🗑️  删除临时文件: {item} ({file_size / 1024 / 1024:.2f} MB)")
                    except Exception as e:
                        print(f"  ⚠️  无法删除文件 {item}: {e}")
                    break

    # 2. 清理 cacheCutVideo 文件夹中的临时文件
    cache_cut_dir = os.path.join(current_dir, 'cacheCutVideo')
    if os.path.exists(cache_cut_dir):
        for item in os.listdir(cache_cut_dir):
            item_path = os.path.join(cache_cut_dir, item)
            if os.path.isfile(item_path):
                # 删除 clip_*.mp4 和 temp_*.txt 文件
                if (item.startswith('clip_') and item.endswith('.mp4')) or \
                   (item.startswith('temp_') and item.endswith('.txt')):
                    try:
                        file_size = os.path.getsize(item_path)
                        os.remove(item_path)
                        deleted_count += 1
                        deleted_size += file_size
                        print(f"  🗑️  删除缓存片段: {item} ({file_size / 1024 / 1024:.2f} MB)")
                    except Exception as e:
                        print(f"  ⚠️  无法删除文件 {item}: {e}")

    # 3. 清理 subtitles 开头的临时文件夹（如果存在）
    for item in os.listdir(current_dir):
        item_path = os.path.join(current_dir, item)
        if os.path.isdir(item_path) and item.startswith('subtitles'):
            try:
                # 检查文件夹是否是旧的（超过1天）
                folder_mtime = os.path.getmtime(item_path)
                if (time.time() - folder_mtime) > 86400:  # 1天 = 86400秒
                    shutil.rmtree(item_path)
                    print(f"  🗑️  删除旧的字幕文件夹: {item}")
                    deleted_count += 1
            except Exception as e:
                print(f"  ⚠️  无法删除文件夹 {item}: {e}")

    print(f"✅ 临时文件清理完成！共删除 {deleted_count} 个文件，释放 {deleted_size / 1024 / 1024:.2f} MB 空间")
    return deleted_count, deleted_size


def clean_permanent_cache(max_size_gb=20):
    """
    清理永久缓存文件夹，当总大小超过指定限制时，删除最早的缓存文件

    Args:
        max_size_gb: 最大缓存大小限制（GB），默认20GB

    清理的文件夹包括:
        - cacheVideo: 通用视频素材缓存
        - cacheCNVideo: 全国介绍类视频素材
        - cacheAFRVideo: 三农视频素材
        - cacheCoverVideo: 封面视频素材
    """
    max_size_bytes = max_size_gb * 1024 * 1024 * 1024  # 转换为字节

    # 永久缓存文件夹列表
    cache_folders = ['cacheVideo', 'cacheCNVideo', 'cacheAFRVideo', 'cacheCoverVideo']
    current_dir = os.getcwd()

    # 收集所有缓存文件及其信息
    all_files = []

    for folder_name in cache_folders:
        cache_dir = os.path.join(current_dir, folder_name)

        if not os.path.exists(cache_dir):
            continue

        try:
            for filename in os.listdir(cache_dir):
                filepath = os.path.join(cache_dir, filename)
                if os.path.isfile(filepath):
                    # 获取文件信息
                    file_stat = os.stat(filepath)
                    all_files.append({
                        'path': filepath,
                        'size': file_stat.st_size,
                        'mtime': file_stat.st_mtime,  # 最后修改时间
                        'folder': folder_name
                    })
        except Exception as e:
            print(f"⚠️ 读取缓存文件夹 {folder_name} 时出错: {e}")
            continue

    # 如果没有缓存文件，直接返回
    if not all_files:
        print("✅ 没有需要清理的缓存文件")
        return

    # 计算总大小
    total_size = sum(f['size'] for f in all_files)
    total_size_gb = total_size / (1024 * 1024 * 1024)

    print(f"📊 当前永久缓存总大小: {total_size_gb:.2f} GB / {max_size_gb} GB")

    # 如果未超过限制，不清理
    if total_size <= max_size_bytes:
        print(f"✅ 缓存大小在限制范围内，无需清理")
        return

    # 需要删除的大小
    size_to_free = total_size - max_size_bytes
    size_to_free_gb = size_to_free / (1024 * 1024 * 1024)

    print(f"⚠️ 缓存超出限制 {size_to_free_gb:.2f} GB，开始清理最早的文件...")

    # 按最后修改时间排序（最早的在前）
    all_files.sort(key=lambda x: x['mtime'])

    # 计算需要删除的文件
    deleted_files = []
    deleted_size = 0

    for file_info in all_files:
        if deleted_size >= size_to_free:
            break

        try:
            # 删除文件
            os.remove(file_info['path'])
            deleted_files.append(file_info['path'])
            deleted_size += file_info['size']

            print(f"🗑️ 已删除: {file_info['folder']}/{os.path.basename(file_info['path'])} "
                  f"({file_info['size'] / (1024 * 1024):.2f} MB)")

        except Exception as e:
            print(f"❌ 删除文件失败 {file_info['path']}: {e}")

    # 统计清理结果
    deleted_count = len(deleted_files)
    deleted_size_gb = deleted_size / (1024 * 1024 * 1024)
    remaining_size_gb = (total_size - deleted_size) / (1024 * 1024 * 1024)

    print(f"\n✅ 缓存清理完成:")
    print(f"   - 删除文件数: {deleted_count}")
    print(f"   - 释放空间: {deleted_size_gb:.2f} GB")
    print(f"   - 剩余缓存: {remaining_size_gb:.2f} GB / {max_size_gb} GB")


# 单个srt文件转ass文件
def convert_srt_to_ass(srt_file_path, output_path, srt_srt_dict):
    try:
        # 1. 读取SRT文件内容
        srt_content = read_srt_file(srt_file_path)

        # 2. 解析SRT内容为事件列表
        srt_entries = parse_srt(srt_content)

        # 3. 生成ASS头部
        ass_header = create_ass_header(srt_srt_dict)

        # 转换SRT条目为ASS格式
        ass_events = []
        for entry in srt_entries:
            ass_event = create_ass_event(entry)
            ass_events.append(ass_event)

        # 4. 组合ASS文件内容
        ass_content = ass_header + "\n".join(ass_events)

        # 5. 保存ASS文件
        # output_path = srt_file_path.replace('.srt', '.ass')
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        return True, f"转换一个片段字幕成功，保存至：{output_path}"
    except Exception as e:
        return False, f"转换失败：{str(e)}"


def create_ass_header(setting_dict):
    """创建ASS文件头部"""
    font_name = setting_dict['fontFamily']

    font_size = 12

    primary_color_ass = convert_to_ass_color(setting_dict['fontColor'])

    border_color_ass = convert_to_ass_color(setting_dict['borderColor'])

    shadow_color_ass = convert_to_ass_color(setting_dict['shadowColor'])

    # 获取样式设置（将True/False转换为-1/0）
    bold = setting_dict['fontBold']
    italic = setting_dict['fontItalic']
    underline = setting_dict['fontUnderline']

    fontBorderSize = setting_dict['fontBorderSize']
    shadowDepth = setting_dict['shadowDepth']

    # 标题默认在视频中间
    align_value = 2

    header = f"""[Script Info]
Title: Default Aegisub file
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None

[V4+ Styles] Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color_ass},{primary_color_ass},{border_color_ass},{shadow_color_ass},{bold},{italic},{underline},0,100,100,0,0,1,{fontBorderSize},{shadowDepth},{align_value},10,10,70,65001  # 注意参数顺序和数量

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return header


def create_ass_event(entry):
    """创建ASS事件行"""
    start_time = entry['start_time']
    end_time = entry['end_time']
    text = entry['text'].replace('A:', '').replace('B:', '')

    # 检查字符串长度
    if len(text) > 12:
        text = '\\N'.join(text[i:i + 12] for i in range(0, len(text), 12))

    # 创建ASS事件行
    return f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}"


def read_srt_file(file_path):
    """读取本地SRT文件并返回内容字符串"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"读取文件失败: {str(e)}")
        return None


def parse_srt(srt_content):
    """解析SRT内容为条目列表"""
    entries = []
    srt_parts = re.split(r'\n\s*\n', srt_content.strip())

    for part in srt_parts:
        if not part.strip():
            continue

        lines = part.strip().split('\n')
        if len(lines) < 2:
            continue

        try:
            index = lines[0].strip()
            timecode = lines[1].strip()
            text = '\n'.join(lines[2:]).strip()

            start_time, end_time = parse_timecode(timecode)
            entries.append({
                'index': index,
                'start_time': start_time,
                'end_time': end_time,
                'text': text
            })
        except Exception as e:
            print(f"解析SRT条目失败: {str(e)}")
            continue

    return entries


def parse_srt_num_time(path: str) -> List[float]:
    """
    读取 .srt 文件，返回各字幕段落的持续时长（秒）
    顺序与文件里出现顺序一致
    """
    with open(path, encoding='utf-8') as f:
        text = f.read()

    # 匹配一个时间戳
    pattern = re.compile(r'\d{2}:\d{2}:\d{2},\d{3}')

    durations: List[float] = []

    def to_seconds(t: str) -> float:
        """t = 'hh:mm:ss,mmm' -> 秒(float)"""
        time_part, ms_part = t.split(',')  # '00:00:00' , '000'
        h, m, s = time_part.split(':')  # '00','00','00'
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms_part) / 1000

    for line in text.splitlines():
        if '-->' in line:
            start, end = pattern.findall(line)
            durations.append(to_seconds(end) - to_seconds(start))
    return durations


def parse_timecode(timecode):
    """解析SRT时间码为ASS格式的时间"""
    # 处理格式如: 00:01:23,456 --> 00:01:25,789
    parts = timecode.split('-->')
    if len(parts) != 2:
        raise ValueError("无效的时间码格式")

    start_time = str_format_time(parts[0].strip())
    end_time = str_format_time(parts[1].strip())

    return start_time, end_time


def str_format_time(time_str):
    """将SRT时间格式转换为ASS时间格式"""
    # 处理格式如: 00:01:23,456 转换为 0:01:23.45
    time_str = time_str.replace(',', '.')
    h, m, s = time_str.split(':')
    s, cs = s.split('.')

    # 确保小数部分只有两位
    cs = cs[:2]

    return f"{h}:{m}:{s}.{cs}"


def convert_to_ass_color(hex_color):
    """
    将 RGB 十六进制颜色代码转换为 ASS 字幕格式的颜色代码。

    参数:
        hex_color (str): RGB 颜色代码，如 '#FF0000' 或 'FF0000'

    返回:
        str: ASS 格式的颜色代码，如 '&H0000FF'
    """
    # 移除可能存在的 '#' 前缀
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]

    # 确保颜色代码长度正确
    if len(hex_color) != 6:
        raise ValueError("颜色代码必须是6个字符的十六进制值（不包括'#'）")

    # 提取 R、G、B 分量
    r = hex_color[0:2]
    g = hex_color[2:4]
    b = hex_color[4:6]

    # 按 BGR 顺序重新组合，并添加 ASS 前缀 '&H'
    return f'&H{b}{g}{r}'


# 创建标题文件
def create_title(ass_header_dict, title_type, screen_type, title_text, out_path, file_path=None):
    try:
        if title_text == '':
            return

        # 判断是否存在ass文件,是则删除掉
        if os.path.exists(out_path):
            send2trash.send2trash(out_path)

        if title_type == '1':
            # 标题样式1 分段式横屏
            def opening_style_1():
                ass_events = ''

                ass_header = file_create_title_ass_header(ass_header_dict['title_set'])

                title_part_text_list = title_text.split('|')

                part_num = len(title_part_text_list)
                # 1. 读取SRT文件内容
                srt_content = read_srt_file(file_path)

                # 2. 解析SRT内容为事件列表
                srt_entries = parse_srt(srt_content)

                all_end_time = srt_entries[0]['end_time']

                float_end_time = time_format_to_float_seconds(all_end_time) - 0.1

                # 定义常见符号的正则表达式模式
                symbols_pattern = r'[!-/:-@[-`{-~]'

                # 使用正则表达式替换所有符号为空字符串
                text_without_symbols = re.sub(symbols_pattern, '', title_text)

                text_length = len(text_without_symbols)

                # time_per_character = float(float_end_time / text_length) - 0.2

                for i, title_part_text in enumerate(title_part_text_list):
                    if title_part_text == '':
                        continue
                    num = i
                    start_time = 0
                    # while num != 0:
                    #     start_time += float(time_per_character * len(title_part_text_list[num - 1]))
                    #     num -= 1
                    # start_time = float_seconds_to_time_format(start_time)
                    end_time = all_end_time
                    text = file_title_apply_effects_to_text(title_part_text, i, part_num,
                                                            ass_header_dict[f'part_title_part_{i}_set'])
                    ass_events += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}" + '\n'
                # ASS文件内容
                ass_content = ass_header + "\n" + ass_events
                return ass_content, float_end_time

            # 标题样式2 分段式竖屏
            def opening_style_2():
                ass_events = ''

                ass_header = file_create_title_ass_header(ass_header_dict['title_set'])

                title_part_text_list = title_text.split('|')

                part_num = len(title_part_text_list)
                # 1. 读取SRT文件内容
                srt_content = read_srt_file(file_path)

                # 2. 解析SRT内容为事件列表
                srt_entries = parse_srt(srt_content)

                all_end_time = srt_entries[0]['end_time']

                float_end_time = time_format_to_float_seconds(all_end_time) - 0.1

                # 定义常见符号的正则表达式模式
                symbols_pattern = r'[!-/:-@[-`{-~]'

                # 使用正则表达式替换所有符号为空字符串
                # text_without_symbols = re.sub(symbols_pattern, '', title_text)

                # text_length = len(text_without_symbols)

                # time_per_character = float(float_end_time / text_length) - 0.2

                # 标题位置
                x = ass_header_dict['title_set']['titleSpace']
                y = 140
                for i, title_part_text in enumerate(title_part_text_list):
                    if title_part_text == '':
                        continue
                    num = i
                    start_time = 0
                    # while num != 0:
                    #     start_time += float(time_per_character * len(title_part_text_list[num - 1]))
                    #     num -= 1
                    # start_time = float_seconds_to_time_format(start_time)
                    end_time = all_end_time
                    text = file_title_apply_effects_to_text(title_part_text, i, part_num,
                                                            ass_header_dict[f'part_title_part_{i}_set'])
                    effect = f"{{\\an5\\pos({x + 100},{y})}}"
                    x = x + 100
                    ass_events += f"Dialogue: 0,{start_time},{end_time},VerticalPro,,0,0,0,,{{\\frz{-90}}}{effect}{text}" + '\n'
                # ASS文件内容
                ass_content = ass_header + "\n" + ass_events
                return ass_content, float_end_time

            if ass_header_dict['title_type']['type'] == 0:
                ass_content, float_end_time = opening_style_1()
            else:
                ass_content, float_end_time = opening_style_2()

            # 保存ASS文件
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(ass_content)
            return float_end_time
        else:
            ass_header = file_create_title_ass_header(ass_header_dict['part_title_set'])
            # 1. 读取SRT文件内容
            srt_content = read_srt_file(file_path)

            # 2. 解析SRT内容为事件列表
            srt_entries = parse_srt(srt_content)

            end_time = srt_entries[0]['end_time']

            text = file_apply_effects_to_text(title_text, screen_type, ass_header_dict['part_title_set']['fontScroll'])

            # 超过8字换行
            if len(text) > 6:
                text = '\\N'.join(text[i:i + 8] for i in range(0, len(text), 8))

            # 创建ASS事件行
            ass_events = f"Dialogue: 0,00:00:00.00,{end_time},Default,,0,0,0,,{text}"
            # ASS文件内容
            ass_content = ass_header + "\n" + ass_events
            # 保存ASS文件
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(ass_content)
            return None
    except Exception as e:
        print(f'特效标题文件出错了{e}')


# 创建标注特效标题文件
def create_tagging_title(ass_header_dict, title_type, screen_type, title_text, out_path, file_path=None, key_word=''):
    try:
        if title_text == '':
            return

        # 判断是否存在ass文件,是则删除掉
        if os.path.exists(out_path):
            send2trash.send2trash(out_path)

        if title_type == '1':
            # 标题样式1 分段式横屏
            def opening_style_1():
                ass_events = ''

                ass_header_dict['title_set']['titleLineSpace'] = 1
                ass_header = file_create_title_ass_header(ass_header_dict['title_set'])

                title_part_text_list = title_text.split('|')

                part_num = len(title_part_text_list)
                # 1. 读取SRT文件内容
                srt_content = read_srt_file(file_path)

                # 2. 解析SRT内容为事件列表
                srt_entries = parse_srt(srt_content)

                all_end_time = srt_entries[0]['end_time']

                float_end_time = time_format_to_float_seconds(all_end_time) - 0.1

                # 定义常见符号的正则表达式模式
                symbols_pattern = r'[!-/:-@[-`{-~]'

                # 使用正则表达式替换所有符号为空字符串
                text_without_symbols = re.sub(symbols_pattern, '', title_text)

                text_length = len(text_without_symbols)

                # time_per_character = float(float_end_time / text_length) - 0.2

                for i, title_part_text in enumerate(title_part_text_list):
                    if title_part_text == '':
                        continue
                    num = i
                    start_time = 0
                    # while num != 0:
                    #     start_time += float(time_per_character * len(title_part_text_list[num - 1]))
                    #     num -= 1
                    # start_time = float_seconds_to_time_format(start_time)
                    end_time = all_end_time

                    if i != len(title_part_text_list) - 1:
                        ass_header_dict[f'part_title_part_{i}_set']['fontColor'] = '#FFFFFF'
                        ass_header_dict[f'part_title_part_{i}_set']['borderColor'] = '#000000'
                        ass_header_dict[f'part_title_part_{i}_set']['fontSize'] = 22
                    else:
                        ass_header_dict[f'part_title_part_{i}_set']['fontColor'] = '#FFFF00'
                        ass_header_dict[f'part_title_part_{i}_set']['borderColor'] = '#000000'
                        ass_header_dict[f'part_title_part_{i}_set']['fontSize'] = 22
                    text = file_title_apply_effects_to_text(title_part_text, i, part_num,
                                                            ass_header_dict[f'part_title_part_{i}_set'], key_word)
                    ass_events += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}" + '\n'
                # ASS文件内容
                ass_content = ass_header + "\n" + ass_events
                return ass_content, float_end_time

            # 标题样式2 分段式竖屏
            def opening_style_2():
                ass_events = ''

                ass_header = file_create_title_ass_header(ass_header_dict['title_set'])

                title_part_text_list = title_text.split('|')

                part_num = len(title_part_text_list)
                # 1. 读取SRT文件内容
                srt_content = read_srt_file(file_path)

                # 2. 解析SRT内容为事件列表
                srt_entries = parse_srt(srt_content)

                all_end_time = srt_entries[0]['end_time']

                float_end_time = time_format_to_float_seconds(all_end_time) - 0.1

                # 定义常见符号的正则表达式模式
                symbols_pattern = r'[!-/:-@[-`{-~]'

                # 使用正则表达式替换所有符号为空字符串
                # text_without_symbols = re.sub(symbols_pattern, '', title_text)

                # text_length = len(text_without_symbols)

                # time_per_character = float(float_end_time / text_length) - 0.2

                # 标题位置
                x = ass_header_dict['title_set']['titleSpace']
                y = 140
                for i, title_part_text in enumerate(title_part_text_list):
                    if title_part_text == '':
                        continue
                    num = i
                    start_time = 0
                    # while num != 0:
                    #     start_time += float(time_per_character * len(title_part_text_list[num - 1]))
                    #     num -= 1
                    # start_time = float_seconds_to_time_format(start_time)
                    end_time = all_end_time

                    text = file_title_apply_effects_to_text(title_part_text, i, part_num,
                                                            ass_header_dict[f'part_title_part_{i}_set'])
                    effect = f"{{\\an5\\pos({x + 100},{y})}}"
                    x = x + 100
                    ass_events += f"Dialogue: 0,{start_time},{end_time},VerticalPro,,0,0,0,,{{\\frz{-90}}}{effect}{text}" + '\n'
                # ASS文件内容
                ass_content = ass_header + "\n" + ass_events
                return ass_content, float_end_time

            if ass_header_dict['title_type']['type'] == 0:
                ass_content, float_end_time = opening_style_1()
            else:
                ass_content, float_end_time = opening_style_2()

            # 保存ASS文件
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(ass_content)
            return float_end_time
        else:
            ass_header = file_create_title_ass_header(ass_header_dict['part_title_set'])
            # 1. 读取SRT文件内容
            srt_content = read_srt_file(file_path)

            # 2. 解析SRT内容为事件列表
            srt_entries = parse_srt(srt_content)

            end_time = srt_entries[0]['end_time']

            text = file_apply_effects_to_text(title_text, screen_type, ass_header_dict['part_title_set']['fontScroll'])

            # 超过8字换行
            if len(text) > 6:
                text = '\\N'.join(text[i:i + 8] for i in range(0, len(text), 8))

            # 创建ASS事件行
            ass_events = f"Dialogue: 0,00:00:00.00,{end_time},Default,,0,0,0,,{text}"
            # ASS文件内容
            ass_content = ass_header + "\n" + ass_events
            # 保存ASS文件
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(ass_content)
            return None
    except Exception as e:
        print(f'特效标题文件出错了{e}')


# 时间转成ass时间格式
def sec2ass(sec: float) -> str:
    """秒 → 0:00:00.00 格式"""
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):01d}:{int(m):02d}:{s:05.2f}"


# 创建标题ass头部文本
def file_create_title_ass_header(ass_header_dict, play_res_x=None, play_res_y=None):
    """创建ASS文件头部"""
    font_name = ass_header_dict['fontFamily']
    font_size = ass_header_dict['fontSize']

    primary_color_ass = convert_to_ass_color(ass_header_dict['fontColor'])

    border_color_ass = convert_to_ass_color(ass_header_dict['borderColor'])

    shadow_color_ass = convert_to_ass_color(ass_header_dict['shadowColor'])

    # 获取样式
    bold = ass_header_dict['fontBold']
    italic = ass_header_dict['fontItalic']
    underline = ass_header_dict['fontUnderline']

    borderSize = ass_header_dict['fontBorderSize']
    shadowDepth = ass_header_dict['shadowDepth']
    align_value = 2
    MarginV = ass_header_dict['titleSpace']
    titleLineSpace = ass_header_dict['titleLineSpace']

    # 如果指定了分辨率，则添加到头部；否则使用默认（不指定，兼容旧代码）
    play_res_line = ""
    if play_res_x is not None and play_res_y is not None:
        play_res_line = f"        PlayResX: {play_res_x}\n        PlayResY: {play_res_y}\n"

    header = f"""[Script Info]
        Title: Default Aegisub file
        ScriptType: v4.00+
        WrapStyle: 0
        ScaledBorderAndShadow: yes
        YCbCr Matrix: None
{play_res_line}
        [V4+ Styles] Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
        Style: Default,{font_name},{font_size},{primary_color_ass},{primary_color_ass},{border_color_ass},{shadow_color_ass},{bold},{italic},{underline},0,100,100,{titleLineSpace},0,1,{borderSize},{shadowDepth},{align_value},10,10,{MarginV},65001  # 注意参数顺序和数量
        Style: VerticalPro,@{font_name},{font_size},{primary_color_ass},{primary_color_ass},{border_color_ass},{shadow_color_ass},{bold},{italic},{underline},0,100,100,{titleLineSpace},0,1,{borderSize},{shadowDepth},{align_value},10,10,{MarginV},65001
        [Events]
        Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        """
    return header


def time_format_to_float_seconds(d_time_str: str) -> float:
    """
    将时间格式字符串（00:00:00.00）转换为浮点数秒。

    Args:
        d_time_str: 时间格式字符串，如 "00:00:00.00"。

    Returns:
        转换后的浮点数秒。
    """
    # 分割时间字符串
    parts = d_time_str.split(':')
    if len(parts) != 3:
        raise ValueError("时间格式字符串无效，应为 00:00:00.00")

    hours = int(parts[0])
    minutes = int(parts[1])
    seconds_part = parts[2].split('.')
    if len(seconds_part) != 2:
        raise ValueError("时间格式字符串无效，应为 00:00:00.00")

    seconds = int(seconds_part[0])
    milliseconds = int(seconds_part[1])

    # 计算总秒数
    total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 100

    return total_seconds


def float_seconds_to_time_format(seconds: float) -> str:
    """
    将浮点数秒转换为 00:00:00.00 格式。

    Args:
        seconds: 浮点数秒。

    Returns:
        转换后的字符串格式时间。
    """
    # 将秒数分解为整数部分和小数部分
    int_seconds = int(seconds)
    milliseconds = round((seconds - int_seconds) * 100)  # 毫秒部分，保留两位小数

    # 计算小时、分钟和秒
    hours = int_seconds // 3600  # 小时
    minutes = (int_seconds % 3600) // 60  # 分钟
    seconds = int_seconds % 60  # 秒

    # 格式化为 00:00:00.00 格式
    time_format = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:02d}"

    return time_format


def file_title_apply_effects_to_text(title_part_text, i, part_num, title_part_dict, key_word=''):
    """应用特效到文本"""
    # # 转义换行符和特殊字符
    # text = text.replace('\n', '\\N')

    # if screen_type == 0:
    #     # 获取屏幕尺寸
    #     screen_width = 1080
    #     screen_height = 1920
    # else:
    #     # 获取屏幕尺寸
    #     screen_width = 1920
    #     screen_height = 1080

    # 应用淡入淡出效果
    fade_in = 300
    fade_out = 300

    # 构建ASS样式代码
    ass_code = ""

    # title_part_list = title_text.split('|')
    # for i, title_part in enumerate(title_part_list):

    # all_setting_dict = read_dict_from_txt('setting1.txt')

    # title_part_dict = all_setting_dict[f'part_title_part_{i}_set']

    alignment_list = [2, 7, 4, 1, 9, 6, 3]

    # if title_part == '':
    #     ass_code += r'\N'

    # if title_part_dict['fontScroll'] == 0:
    #     ass_code += f"{{\\fs{title_part_dict['fontSize']}\\c&H{convert_to_ass_color(title_part_dict['fontColor'])[2:]}&\\3c&H{convert_to_ass_color(title_part_dict['borderColor'])[2:]}&\\an{alignment_list[title_part_dict['align']]}\\Y{title_part_dict['VSpace']}}}" + title_part_text + r'\N'
    #
    # #  添加其他特效（非滚动效果）
    # if title_part_dict['fontScroll'] == 1:
    #     ass_code += f"{{\\fs{title_part_dict['fontSize']}\\c&H{convert_to_ass_color(title_part_dict['fontColor'])[2:]}&\\3c&H{convert_to_ass_color(title_part_dict['borderColor'])[2:]}&\\an{alignment_list[title_part_dict['align']]}\\Y{title_part_dict['VSpace']}\\fad({fade_in},{fade_out})}}" + title_part_text + r'\N'

    # # ---------- 1. 先把关键词高亮拼成普通字符串 ----------
    # if key_word and key_word in title_part_text:
    #     # 高亮片段：黄体 + 黑边 + 粗体
    #     highlight = (r"{\\c&H00FFFF&\\3c&H000000&\\bord2\\b1}" +
    #                  key_word +
    #                  r"{\\c&H" + convert_to_ass_color(title_part_dict['fontColor'])[2:] +
    #                  r"&\\3c&H" + convert_to_ass_color(title_part_dict['borderColor'])[2:] +
    #                  r"&\\bord1\\b0}")
    #     # 用 re.sub 但先把关键词 re.escape，避免用户输入含正则特殊符号
    #     title_part_text = re.sub(re.escape(key_word), highlight, title_part_text, flags=re.IGNORECASE)

    if title_part_dict['fontScroll'] == 0:  # 缩放效果（从小变大）
        # 修改为垂直滚动，从底部外到顶部外
        scale_start = 20  # 起始缩放比例(%)
        scale_end = 100  # 结束缩放比例(%)
        duration = 200  # 动画时长(ms)
        ass_code += f"{{\\fs{title_part_dict['fontSize']}\\c&H{convert_to_ass_color(title_part_dict['fontColor'])[2:]}&\\3c&H{convert_to_ass_color(title_part_dict['borderColor'])[2:]}&\\an{alignment_list[title_part_dict['align']]}\\pos({title_part_dict['x']},{title_part_dict['y']})\\Y{title_part_dict['VSpace']}\\fscx{scale_start}\\fscy{scale_start}\\t(0,{duration},\\fscx{scale_end}\\fscy{scale_end})}}" + title_part_text + r'\N'

    elif title_part_dict['fontScroll'] == 1:  # 从左到右（垂直方向改为从顶部到底部）
        rotate_angle = 360  # 旋转角度(度)
        duration = 3000  # 动画时长(ms)
        ass_code += f"{{\\fs{title_part_dict['fontSize']}\\c&H{convert_to_ass_color(title_part_dict['fontColor'])[2:]}&\\3c&H{convert_to_ass_color(title_part_dict['borderColor'])[2:]}&\\an{alignment_list[title_part_dict['align']]}\\pos({title_part_dict['x']},{title_part_dict['y']})\\Y{title_part_dict['VSpace']}\\fr0\\t(0,{duration},\\fr{rotate_angle})}}" + title_part_text + r'\N'

    elif title_part_dict['fontScroll'] == 2:  # 颜色渐变效果
        start_color = "&H0000FF&"  # 起始颜色(蓝色)
        end_color = "&HFF0000&"  # 结束颜色(红色)
        duration = 2500  # 动画时长(ms)
        ass_code += f"{{\\fs{title_part_dict['fontSize']}\\c&H{convert_to_ass_color(title_part_dict['fontColor'])[2:]}&\\3c&H{convert_to_ass_color(title_part_dict['borderColor'])[2:]}&\\an{alignment_list[title_part_dict['align']]}\\pos({title_part_dict['x']},{title_part_dict['y']})\\Y{title_part_dict['VSpace']}\\c{start_color}\\t(0,{duration},\\c{end_color})}}" + title_part_text + r'\N'

    elif title_part_dict['fontScroll'] == 3:  # 模糊效果+淡入
        blur_amount = 5  # 模糊程度
        fade_in = 80  # 淡入时间(ms)
        ass_code += f"{{\\fs{title_part_dict['fontSize']}\\c&H{convert_to_ass_color(title_part_dict['fontColor'])[2:]}&\\3c&H{convert_to_ass_color(title_part_dict['borderColor'])[2:]}&\\an{alignment_list[title_part_dict['align']]}\\pos({title_part_dict['x']},{title_part_dict['y']})\\Y{title_part_dict['VSpace']}\\blur{blur_amount}\\fad({fade_in},0)\\t({fade_in // 2},{fade_in},\\blur0)}}" + title_part_text + r'\N'

    # elif fontScroll == 6:  # 弹跳效果
    #     start_y = screen_height + 100  # 起始Y位置
    #     end_y = screen_height // 2  # 结束Y位置
    #     duration = 1500  # 动画时长(ms)
    #     ass_code += (f"{{\\pos({screen_width // 2},{start_y})\\t(0,{duration},\\pos({screen_width // 2},{end_y}),"
    #                  f"\\bounce)}}")
    # 组合最终文本

    # for n in range(2 * (part_num - i) - 1):
    #     ass_code += r'{\fs15} \N'

    final_text = ass_code
    return final_text


# # 文字介绍类 生成标题
# def file_word_infor_title_apply_effects_to_text(title_part_text, pos_x, pos_y):
#     start_color = "&H00FFFF&"
#     end_color = "&H0000FF&"
#     cycle = 2500  # 2.5 s
#     half = cycle // 2  # 1.25 s
#     # 构建ASS样式代码
#     ass_code = ""
#     ass_code += (
#                     f"{{\\fs{15}"
#                     f"\\an{2}"
#                     f"\\pos({pos_x},{pos_y})"
#                     f"\\Y{1}"
#                     # 第 1 周期 (0-2.5s)
#                     f"\\c{start_color}\\t(0,{half},\\c{end_color})\\t({half},{cycle},\\c{start_color})"
#                     # 第 2 周期 (2.5-5s)
#                     f"\\t({cycle},{cycle + half},\\c{end_color})\\t({cycle + half},{2 * cycle},\\c{start_color})"
#                     # 第 3 周期 (5-7.5s)
#                     f"\\t({2 * cycle},{2 * cycle + half},\\c{end_color})\\t({2 * cycle + half},{3 * cycle},\\c{start_color})"
#                     # 第 4 周期 (7.5-10s)
#                     f"\\t({3 * cycle},{3 * cycle + half},\\c{end_color})\\t({3 * cycle + half},{4 * cycle},\\c{start_color})"
#                     f"}}"
#                 ) + title_part_text + r"\N"
#     return ass_code

def get_random_ass_color():
    # 生成柔和随机色（限制亮度范围避免刺眼）
    r = random.randint(80, 220)
    g = random.randint(80, 220)
    b = random.randint(80, 220)
    return f"&H{b:02X}{g:02X}{r:02X}&"  # 修正：补充闭合引号


# 渐变
def file_word_infor_title_apply_effects_to_text(title_part_text, pos_x, pos_y):
    cycle = 2500  # 单个周期总时长
    segments = 4  # 每个周期分4段过渡（插入2个中间色）
    step_time = cycle // segments  # 每段过渡时间：2500/4=625ms
    ass_code = f"{{\\fs15\\an2\\pos({pos_x},{pos_y})\\Y1"
    # 生成4个周期的平滑渐变
    for cycle_idx in range(4):
        # 每个周期生成5个随机色（含首尾）
        colors = [get_random_ass_color() for _ in range(segments + 1)]
        # 生成该周期内的多段渐变
        for seg_idx in range(segments):
            start_t = cycle_idx * cycle + seg_idx * step_time
            end_t = cycle_idx * cycle + (seg_idx + 1) * step_time
            ass_code += f"\\t({start_t},{end_t},\\c{colors[seg_idx + 1]})"
    ass_code += f"}} {title_part_text}\\N"
    return ass_code


# 缩放
def file_word_infor_title_scale_effects_to_text(title_part_text, title_dict, pos_x, pos_y):
    cycle = 2000  # 单个周期总时长
    segments = 4  # 每个周期分4段过渡
    step_time = cycle // segments  # 每段过渡时间
    ass_code = f"{{\\fs{title_dict['fontSize']}\\an2\\pos({pos_x},{pos_y})\\Y1\\fsp{1}"
    # 生成4个周期的缩放
    for cycle_idx in range(4):
        # 每个周期生成5个随机大小（含首尾）
        sizes = [title_dict['fontSize'] + 2 if i % 2 == 0 else title_dict['fontSize'] for i in range(segments + 1)]
        # 生成该周期内的多段缩放
        for seg_idx in range(segments):
            start_t = cycle_idx * cycle + seg_idx * step_time
            end_t = cycle_idx * cycle + (seg_idx + 1) * step_time
            ass_code += f"\\t({start_t},{end_t},\\fs{sizes[seg_idx + 1]}\\fsp{1})"
        # 添加字体颜色和边框颜色
    ass_code += (f"\\c&H{convert_to_ass_color(title_dict['fontColor'])[2:]}&"
                 f"\\3c&H{convert_to_ass_color(title_dict['borderColor'])[2:]}&}}")
    ass_code += f" {title_part_text}\\N"
    return ass_code


def file_word_infor_title_static_text(title_part_text, title_dict, pos_x, pos_y):
    """
    生成静态显示文字的 ASS 代码
    :param title_part_text: 要显示的文本内容
    :param title_dict: 包含样式信息的字典，如字体大小、颜色等
    :param pos_x: 文本的水平位置
    :param pos_y: 文本的垂直位置
    """
    ass_code = f"{{\\fs{title_dict['fontSize']}"  # 设置字体大小
    ass_code += f"\\c&H{convert_to_ass_color(title_dict['fontColor'])[2:]}&"  # 设置字体颜色
    ass_code += f"\\3c&H{convert_to_ass_color(title_dict['borderColor'])[2:]}&"  # 设置描边颜色
    ass_code += f"\\an2"  # 设置对齐方式为居中
    ass_code += f"\\fsp1"  # 字间距
    ass_code += f"\\pos({pos_x},{pos_y})"  # 设置文本位置
    # ass_code += f"\\fscx100\\fscy100"  # 设置字体缩放比例
    # ass_code += f"\\fad(500,500)"  # 设置淡入淡出时间
    ass_code += f"}} {title_part_text}\\N"  # 添加文本内容并换行
    return ass_code


# 文字介绍类 生成内容
def file_word_infor_content_apply_effects_to_text(title_part_text, title_part_dict, segment_num, pos_x, pos_y):
    blur_amount = 5  # 模糊程度
    fade_in = 8000 / segment_num - 500  # 淡入时间(ms)
    ass_code = ''
    ass_code += (f"{{\\fs{title_part_dict['fontSize']}"
                 f"\\c&H{convert_to_ass_color(title_part_dict['fontColor'])[2:]}&"
                 f"\\3c&H{convert_to_ass_color(title_part_dict['borderColor'])[2:]}&"
                 f"\\an{1}"
                 f"\\fsp2"
                 f"\\pos({pos_x},{pos_y})"
                 # f"\\Y{5}"  # 行间距
                 f"\\blur{blur_amount}"
                 f"\\fad({fade_in},0)"
                 f"\\t({fade_in // 2},{fade_in},\\blur3)}}") + title_part_text + r'\N'
    return ass_code


def read_dict_from_txt(file_path):
    """从文本文件读取字典，如果文件不存在则创建一个空文件"""
    try:
        # 标题
        title_set_dict = {
            'fontFamily': 'SimHei',  # 字体
            'fontBorderSize': 1,  # 边框大小
            'shadowDepth': 0,  # 阴影大小
            'fontBold': 0,  # 粗体
            'fontColor': '#FFFFFF',  # 字体颜色
            'fontSize': 12,  # 字体大小
            'fontItalic': 0,  # 斜体
            'borderColor': '#000000',  # 边框颜色
            'fontScroll': 0,  # 特效
            'fontUnderline': 0,  # 下划线
            'shadowColor': '#000000',  # 阴影颜色
            'titleTime': 3,  # 标题时间
            'titleLineSpace': 1,  # 行间距
            'titleSpace': 10,  # 位置调整
            'position': 0,
        }

        # 小标题
        part_title_set_dict = {
            'fontFamily': 'SimHei',  # 字体
            'fontBorderSize': 1,  # 边框大小
            'shadowDepth': 0,  # 阴影大小
            'fontBold': 0,  # 粗体
            'fontColor': '#FFFFFF',  # 字体颜色
            'fontSize': 12,  # 字体大小
            'fontItalic': 0,  # 斜体
            'borderColor': '#000000',  # 边框颜色
            'fontScroll': 0,  # 特效
            'fontUnderline': 0,  # 下划线
            'shadowColor': '#000000',  # 阴影颜色
            'titleTime': 3,  # 标题时间
            'titleLineSpace': 1,  # 行间距
            'titleSpace': 10,  # 位置调整
            'position': 0,
            'x': 0,
            'y': 0,
        }

        part_title_part_0_set_dict = {
            'fontBorderSize': 1,  # 边框大小
            'fontColor': '#ffff00',  # 字体颜色
            'borderColor': '#000000',
            'fontSize': 16,  # 字体大小
            'fontScroll': 0,  # 特效
            'VSpace': 1,  # 行间距
            'align': 0,  # 对齐
            'x': 0,
            'y': 0
        }

        part_title_part_1_set_dict = {
            'fontBorderSize': 1,  # 边框大小
            'fontColor': '#ffff00',  # 字体颜色
            'borderColor': '#000000',
            'fontSize': 16,  # 字体大小
            'fontScroll': 0,  # 特效
            'VSpace': 1,  # 行间距
            'align': 0,  # 对齐
            'x': 0,
            'y': 0
        }

        part_title_part_2_set_dict = {
            'fontBorderSize': 1,  # 边框大小
            'fontColor': '#ffff00',  # 字体颜色
            'borderColor': '#000000',
            'fontSize': 16,  # 字体大小
            'fontScroll': 0,  # 特效
            'VSpace': 1,  # 行间距
            'align': 0,  # 对齐
            'x': 0,
            'y': 0
        }

        part_title_part_3_set_dict = {
            'fontBorderSize': 1,  # 边框大小
            'fontColor': '#ffff00',  # 字体颜色
            'borderColor': '#000000',
            'fontSize': 16,  # 字体大小
            'fontScroll': 0,  # 特效
            'VSpace': 1,  # 行间距
            'align': 0,  # 对齐
            'x': 0,
            'y': 0
        }

        part_title_part_4_set_dict = {
            'fontBorderSize': 1,  # 边框大小
            'fontColor': '#ffff00',  # 字体颜色
            'borderColor': '#000000',
            'fontSize': 16,  # 字体大小
            'fontScroll': 0,  # 特效
            'VSpace': 1,  # 行间距
            'align': 0,  # 对齐
            'x': 0,
            'y': 0
        }

        part_title_part_5_set_dict = {
            'fontBorderSize': 1,  # 边框大小
            'fontColor': '#ffff00',  # 字体颜色
            'borderColor': '#000000',
            'fontSize': 16,  # 字体大小
            'fontScroll': 0,  # 特效
            'VSpace': 1,  # 行间距
            'align': 0,  # 对齐
            'x': 0,
            'y': 0
        }

        # 字幕
        srt_set_dict = {
            'fontFamily': 'SimHei',  # 字体
            'fontBorderSize': 1,  # 边框大小
            'shadowDepth': 0,  # 阴影大小
            'fontBold': 0,  # 粗体
            'fontColor': '#FFFFFF',  # 字体颜色
            'fontSize': 12,  # 字体大小
            'fontItalic': 0,  # 斜体
            'borderColor': '#000000',  # 边框颜色
            'fontScroll': 0,  # 特效
            'fontUnderline': 0,  # 下划线
            'shadowColor': '#000000',  # 阴影颜色
            'titleTime': 3,  # 标题时间
            'titleLineSpace': 1,  # 行间距
            'titleSpace': 10,  # 位置调整
        }

        # 配音
        voice_set_dict = {
            'api_type': 0,
            'role_0': 0,
            'pit_0': 0,
            'spd_0': 0,
            'vol_0': 0,
            'role_1': 0,
            'pit_1': 5,
            'spd_1': 5,
            'vol_1': 5,
        }

        # 水印
        water_set_dict = {
            'filePath': '',
            'position': 0,
            'zoom': 1.0,
            'alpha': 1.0
        }

        title_type_dict = {
            'type': 0
        }
        video_type_dict = {
            'type': 0
        }

        all_dict = {
            'video_type': video_type_dict,
            'title_type': title_type_dict,
            'title_set': title_set_dict,
            'part_title_set': part_title_set_dict,
            'srt_set': srt_set_dict,
            'voice_set': voice_set_dict,
            'water_set': water_set_dict,
            'end_video': '',
            'account_location': '',
            'part_title_part_0_set': part_title_part_0_set_dict,
            'part_title_part_1_set': part_title_part_1_set_dict,
            'part_title_part_2_set': part_title_part_2_set_dict,
            'part_title_part_3_set': part_title_part_3_set_dict,
            'part_title_part_4_set': part_title_part_4_set_dict,
            'part_title_part_5_set': part_title_part_5_set_dict,
        }

        if not os.path.exists(file_path):
            # 如果文件不存在，创建一个空文件
            open(file_path, 'w', encoding='utf-8').close()
            print(f"文件已创建: {file_path}")
            return all_dict

        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            if not content:
                print(f"文件内容为空: {file_path}")
                try:
                    # 使用 'w' 模式打开文件，自动清空文件内容
                    with open(file_path, 'w', encoding='utf-8') as file:
                        json.dump(all_dict, file, ensure_ascii=False, indent=4)
                    print(f"字典已成功写入文件: {file_path}")
                    return all_dict
                except Exception as e:
                    print(f"写入字典时出错: {e}")
                    return {}

        with open(file_path, 'r', encoding='utf-8') as file:
            dictionary = json.load(file)
        print(f"字典已成功从文件读取: {file_path}")
        return dictionary
    except json.JSONDecodeError:
        print(f"文件内容不是有效的 JSON 格式: {file_path}")
        return {}
    except Exception as e:
        print(f"读取字典时出错: {e}")
        return {}


def sec_to_ass(t: float) -> str:
    """把秒数转成 hh:mm:ss.cc 格式的 ASS 时间字符串"""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    c = int((t % 1) * 100)  # 百分秒
    return f"{h:d}:{m:02d}:{s:02d}.{c:02d}"


def file_apply_effects_to_text(title_text, screen_type, fontScroll):
    """应用特效到文本"""
    # # 转义换行符和特殊字符
    # text = text.replace('\n', '\\N')

    # if screen_type == 0:
    #     # 获取屏幕尺寸
    #     screen_width = 1080
    #     screen_height = 1920
    # else:
    #     # 获取屏幕尺寸
    #     screen_width = 1920
    #     screen_height = 1080

    # 应用淡入淡出效果
    fade_in = 300
    fade_out = 300

    # 构建ASS样式代码
    ass_code = ""

    #  添加其他特效（非滚动效果）
    if fontScroll == 1:
        ass_code += f"{{\\fad({fade_in},{fade_out})}}"

    elif fontScroll == 2:  # 缩放效果（从小变大）
        # 修改为垂直滚动，从底部外到顶部外
        scale_start = 20  # 起始缩放比例(%)
        scale_end = 100  # 结束缩放比例(%)
        duration = 2000  # 动画时长(ms)
        ass_code += f"{{\\fscx{scale_start}\\fscy{scale_start}\\t(0,{duration},\\fscx{scale_end}\\fscy{scale_end})}}"

    elif fontScroll == 3:  # 从左到右（垂直方向改为从顶部到底部）
        rotate_angle = 360  # 旋转角度(度)
        duration = 3000  # 动画时长(ms)
        ass_code += f"{{\\fr0\\t(0,{duration},\\fr{rotate_angle})}}"

    elif fontScroll == 4:  # 颜色渐变效果
        start_color = "&H0000FF&"  # 起始颜色(蓝色)
        end_color = "&HFF0000&"  # 结束颜色(红色)
        duration = 2500  # 动画时长(ms)
        ass_code += f"{{\\c{start_color}\\t(0,{duration},\\c{end_color})}}"

    elif fontScroll == 5:  # 模糊效果+淡入
        blur_amount = 5  # 模糊程度
        fade_in = 800  # 淡入时间(ms)
        ass_code += f"{{\\blur{blur_amount}\\fad({fade_in},0)\\t({fade_in // 2},{fade_in},\\blur0)}}"

    # elif fontScroll == 6:  # 弹跳效果
    #     start_y = screen_height + 100  # 起始Y位置
    #     end_y = screen_height // 2  # 结束Y位置
    #     duration = 1500  # 动画时长(ms)
    #     ass_code += (f"{{\\pos({screen_width // 2},{start_y})\\t(0,{duration},\\pos({screen_width // 2},{end_y}),"
    #                  f"\\bounce)}}")

    # 组合最终文本
    final_text = ass_code + title_text
    return final_text


def write_dict_to_txt(file_path, dictionary):
    try:
        # 使用 'w' 模式打开文件，自动清空文件内容
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(dictionary, file, ensure_ascii=False, indent=4)
        print(f"字典已成功写入文件: {file_path}")
        return True
    except Exception as e:
        print(f"写入字典时出错: {e}")
        return False


def count_and_sort(arrays):
    """
    统计多个数组中每个元素的出现次数，并随机返回一个出现次数最多的元素

    参数：
        arrays: 包含多个数组的列表

    返回：
        随机选择的一个出现次数最多的元素
    """
    count_dict = defaultdict(int)
    for arr in arrays:
        for elem in arr:
            # 将元素转换为字符串以统一处理
            elem_str = str(elem)
            count_dict[elem_str] += 1

    # 找到出现次数最多的次数
    max_count = max(count_dict.values(), default=0)

    # 获取所有出现次数等于 max_count 的元素
    most_frequent_elements = [elem for elem, count in count_dict.items() if count == max_count]

    # 如果有多个元素出现次数相同且都是最多的，随机选择一个
    if most_frequent_elements:
        return random.choice(most_frequent_elements)
    else:
        return None


def count_and_sort_to_array(arrays):
    """
    统计多个数组中每个元素的出现次数，并随机返回一个出现次数最多的元素

    参数：
        arrays: 包含多个数组的列表

    返回：
       按元素出现次数，从多到少，返回一个数组
    """
    # 合并所有数组
    all_elements = []
    for array in arrays:
        all_elements.extend(array)

    # 统计元素出现次数
    counter = Counter(all_elements)

    # 按出现次数从多到少排序
    sorted_items = sorted(counter.items(), key=lambda x: x[1], reverse=True)

    # 提取排序后的元素
    sorted_elements = [item[0] for item in sorted_items]

    return sorted_elements


def modify_srt_file(file_path, old_text, new_text):
    """
    修改 SRT 文件中的字幕内容，并将结果保存回原文件。

    :param file_path: SRT 文件的路径
    :param old_text: 要被替换的字幕内容
    :param new_text: 替换后的内容
    """
    # 读取 SRT 文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换字幕内容
    modified_content = content.replace(old_text, new_text)

    # 将修改后的内容写回原文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)


def remove_dialogue_text(input_file):
    """
    从 ASS 字幕文件中去除指定行的文字内容，并保存到原始文件

    参数：
        input_file: 输入的 ASS 文件路径
        target_lines: 需要去除文字内容的行号列表（从1开始）
    """
    # 创建一个临时文件
    n = 0
    with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
        with open(input_file, 'r', encoding='utf-8') as file:
            for i, line in enumerate(file, start=1):
                if line.startswith("Dialogue:") and n == 0:
                    n += 1
                    # 去除文字内容，保留其他字段
                    parts = line.split(',', 9)
                    parts[-1] = ''  # 将文字内容替换为空
                    line = ','.join(parts) + '\n'
                temp_file.write(line)

        # 获取临时文件的路径
        temp_file_path = temp_file.name

    # 替换原始文件
    shutil.move(temp_file_path, input_file)


def remove_all_dialogue_text(input_file):
    """
    从 ASS 字幕文件中去除所有 Dialogue 行的文字内容，并保存到原始文件

    参数：
        input_file: 输入的 ASS 文件路径
    """
    # 创建一个临时文件
    with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
        with open(input_file, 'r', encoding='utf-8') as file:
            for line in file:
                if line.startswith("Dialogue:"):
                    # 去除文字内容，保留其他字段
                    parts = line.split(',', 9)
                    parts[-1] = ''  # 将文字内容替换为空
                    line = ','.join(parts) + '\n'
                temp_file.write(line)

        # 获取临时文件的路径
        temp_file_path = temp_file.name

    # 替换原始文件
    shutil.move(temp_file_path, input_file)


def write_dict_to_file(data_dict, file_name):
    """
    将字典内容写入指定的文件中。如果文件不存在，则创建文件；如果文件已存在，则覆盖文件内容。

    参数：
        data_dict: 要写入文件的字典
        file_name: 文件名
    """
    # 判断文件是否存在
    if not os.path.exists(file_name):
        print(f"文件 {file_name} 不存在，将创建新文件。")
    else:
        print(f"文件 {file_name} 已存在，将覆盖文件内容。")

    # 将字典转换为 JSON 格式
    json_content = json.dumps(data_dict, indent=4, ensure_ascii=False)

    # 写入文件
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(json_content)

    print(f"字典内容已写入文件 {file_name}")


def read_file_to_dict(file_name):
    """
    从文件读取内容并将其转换为字典。如果文件不存在，则创建文件并返回空字典。

    参数：
        file_name: 文件名

    返回：
        从文件读取的字典，如果文件不存在则返回空字典
    """
    # 判断文件是否存在
    if not os.path.exists(file_name):
        print(f"文件 {file_name} 不存在，将创建新文件并返回空字典。")
        # 创建文件
        open(file_name, "w", encoding="utf-8").close()
        return {}

    # 读取文件内容
    with open(file_name, "r", encoding="utf-8") as f:
        content = f.read()

    # 将内容转换为字典
    try:
        data_dict = json.loads(content)
    except json.JSONDecodeError:
        print(f"文件 {file_name} 的内容格式不正确，无法解析为字典。")
        return {}

    return data_dict


def copy_txt_overwrite(src_file: str, dst_file: str) -> None:
    """
    将 src_file 的内容覆盖写入 dst_file。
    若目标文件不存在会自动创建；已存在则直接覆盖。
    """
    try:
        src_path = Path(src_file)
        dst_path = Path(dst_file)

        if not src_path.is_file():
            raise FileNotFoundError(f"源文件不存在：{src_path}")

        # 读取源文件全部内容
        text = src_path.read_text(encoding='utf-8')

        # 写入目标文件（覆盖模式）
        dst_path.write_text(text, encoding='utf-8')
    except Exception as e:
        print(f'选择覆盖设置错误:{e}')


def get_pc_mac_address_upper():
    """
    获取PC的Mac地址，返回大写地址，如：F8-A2-D6-CC-BB-AA
    :return:
    """
    # print('\n=========    获取电脑mac地址   =========')
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    # 转大写
    mac_1 = "-".join([mac[e:e + 2] for e in range(0, 11, 2)]).upper()
    return md5_encrypt(mac_1)


def md5_encrypt(text):
    md5 = hashlib.md5()
    md5.update(text.encode('utf-8'))
    return md5.hexdigest()


def enough_unique(video_id_list, threshold: float = 0.8) -> bool:
    """
    不重复率 = 去重后数量 / 原始数量
    返回 True 表示不重复率 ≥ threshold
    """
    if not video_id_list:  # 空数组直接算不合格
        return False
    return len(set(video_id_list)) / len(video_id_list) >= threshold


def write_title(title: str):
    """
    在当前目录下创建 temp_title 文件夹，
    文件名为 title + 时间戳.xlsx
    把 title 写入该 Excel 的第二行第二列（B2）
    """
    dir_path = Path.cwd() / "temp_title"
    dir_path.mkdir(exist_ok=True)

    # 生成文件名：title_年月日时分秒.xlsx
    time_str = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f"{time_str}.xlsx"
    file_path = dir_path / file_name

    wb = Workbook()
    ws = wb.active
    ws["B2"] = title
    wb.save(file_path)
    print(f"已写入 {file_path.resolve()}")
    return file_path


def is_date_today(date_str):
    if date_str is None or date_str == '':
        print("日期字符串为空或 None")
        return False
    # 将字符串解析为 datetime 对象
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        # 从 datetime 对象中提取日期部分
        date_only = date_obj.date()
        # 获取今天的日期
        today = datetime.today().date()
        # 比较两个日期
        return date_only == today
    except Exception as e:
        print('日期解析出错%s' % e)
        return False


def random_txt_file_path(folder_path):
    # 获取文件夹中所有文件
    files = os.listdir(folder_path)
    # 筛选出所有 .txt 文件
    txt_files = [file for file in files if file.endswith('.txt')]
    if txt_files:
        # 随机选择一个 .txt 文件
        random_file = random.choice(txt_files)
        # 返回文件的完整路径
        return os.path.join(folder_path, random_file)
    else:
        return ''


# ffmpeg系统环境设置
def setup_ffmpeg_path():
    """找到源码目录或安装包内的 FFmpeg，仅配置当前进程的 PATH。"""
    executable_dir = os.path.dirname(os.path.abspath(sys.executable))
    source_dir = os.path.dirname(os.path.abspath(__file__))
    bundle_dir = getattr(sys, '_MEIPASS', '')
    candidates = [
        os.path.join(executable_dir, 'ffmpeg-7.1.1-essentials_build', 'bin'),
        os.path.join(source_dir, 'ffmpeg-7.1.1-essentials_build', 'bin'),
        os.path.join(os.getcwd(), 'ffmpeg-7.1.1-essentials_build', 'bin'),
    ]
    if bundle_dir:
        candidates.insert(0, os.path.join(bundle_dir, 'ffmpeg-bin'))

    ffmpeg_path = next((path for path in candidates
                        if os.path.isfile(os.path.join(path, 'ffmpeg.exe'))
                        and os.path.isfile(os.path.join(path, 'ffprobe.exe'))), None)
    if not ffmpeg_path:
        raise FileNotFoundError('未找到完整的 FFmpeg（缺少 ffmpeg.exe 或 ffprobe.exe）')

    os.environ['PATH'] = ffmpeg_path + os.pathsep + os.environ.get('PATH', '')
    os.environ['IMAGEIO_FFMPEG_EXE'] = os.path.join(ffmpeg_path, 'ffmpeg.exe')
    print(f"当前程序使用 FFmpeg: {ffmpeg_path}")


def setup_runtime_directory():
    """让打包程序的相对路径固定到 exe 目录，并补齐首次运行的默认配置。"""
    if not getattr(sys, 'frozen', False):
        return
    executable_dir = os.path.dirname(os.path.abspath(sys.executable))
    os.chdir(executable_dir)

    # These folders are writable runtime workspaces.  Creating them here keeps
    # a clean deployment usable even when no old user data is copied over.
    for directory_name in (
        'cacheVideo', 'cacheAFRVideo', 'cacheCNVideo', 'cacheCoverVideo',
        'cacheCutVideo', 'cacheMusic3', 'notSuccess', 'output', 'tempConcateVideo',
        'temp_title', 'syncVideo', 'person_images', 'pic_infor_model',
        'pic_infor_model2', 'coverPicMaterial',
    ):
        os.makedirs(os.path.join(executable_dir, directory_name), exist_ok=True)

    # PyInstaller stores bundled data below _internal, while the application
    # intentionally uses paths relative to the executable directory.  Restore
    # the original layout on first run without overwriting user files.
    bundle_dir = getattr(sys, '_MEIPASS', '')
    if bundle_dir and os.path.isdir(bundle_dir):
        bundled_names = (
            'soft_pic', 'endCredits', 'gifMaterial', 'strategy_pic',
            'video_model_set', 'cacheMusic', 'cacheMusic1', 'cacheMusic2',
            'cacheMusic3', 'img.jpg', 'blank.ass', 'blank.mp3',
            'version.json', 'white.png', 'xq.png', 'video_ai_config.example.json',
        )
        for bundled_name in bundled_names:
            source_path = Path(bundle_dir) / bundled_name
            target_path = Path(executable_dir) / bundled_name
            if source_path.is_dir():
                for source_file in source_path.rglob('*'):
                    relative_path = source_file.relative_to(source_path)
                    destination = target_path / relative_path
                    if source_file.is_dir():
                        destination.mkdir(parents=True, exist_ok=True)
                    elif not destination.exists():
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_file, destination)
            elif source_path.is_file() and not target_path.exists():
                shutil.copy2(source_path, target_path)

    setting_path = os.path.join(executable_dir, 'setting.txt')
    setting_is_valid = False
    try:
        with open(setting_path, 'r', encoding='utf-8') as file_obj:
            setting_data = json.load(file_obj)
        setting_is_valid = all(key in setting_data for key in ('title_set', 'part_title_set'))
    except (OSError, json.JSONDecodeError, TypeError):
        pass

    if not setting_is_valid:
        bundled_setting = os.path.join(getattr(sys, '_MEIPASS', ''), 'setting.txt')
        if not os.path.isfile(bundled_setting):
            raise FileNotFoundError('安装包内缺少默认配置 setting.txt')
        shutil.copyfile(bundled_setting, setting_path)


def clear_recycle_bin():
    """
    使用 PowerShell 清空回收站
    """
    try:
        # 调用 PowerShell 命令清空回收站
        subprocess.run(["powershell", "-Command", "Clear-RecycleBin -Confirm:$false"], check=True)
        print("回收站已成功清空。")
    except subprocess.CalledProcessError as e:
        print(f"清空回收站时发生错误：{e}")


if __name__ == "__main__":
    # GBK 控制台打印 emoji 会触发 UnicodeEncodeError 崩溃，此处改为容错编码
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(errors='replace')
        except Exception:
            pass

    setup_runtime_directory()

    # ffmpeg设置到当前进程环境
    setup_ffmpeg_path()

    # 启动时清理临时文件
    print("🚀 程序启动，清理临时文件...")
    try:
        clean_temp_files()
    except Exception as e:
        print(f"⚠️  启动时清理临时文件失败: {e}")

    set_process_app_id()
    app = QApplication(sys.argv)
    icon_path = runtime_asset_path("tb.ico")
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))
    window = BatchAICutter()
    window.show()
    if icon_path is not None:
        apply_native_window_icon(int(window.winId()), icon_path)
    sys.exit(app.exec())
