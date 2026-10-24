from PyQt6.QtCore import QObject, pyqtSignal


# 信号
class WorkerSignals(QObject):
    # 执行完成信号
    finished = pyqtSignal(str)

    # 错误信号
    errorOccurred = pyqtSignal(str)

    # 视频文案内容返回信号
    textResultReady = pyqtSignal(list)

    # 视频话题标签返回信号
    topicResultReady = pyqtSignal(list)

    # 文案片段处理进度信号
    progressResultReady = pyqtSignal(str)

    # 处理素材临时文件路径
    tempPathResultReady = pyqtSignal(dict)

    # 测试音频生成信号
    testAudioResultReady = pyqtSignal()

    # 添加背景音乐信号
    addMusicResultReady = pyqtSignal()

    # 音乐风格标签
    musicTagResultReady = pyqtSignal(list)

    # 添加水印信号
    addWatermarkResultReady = pyqtSignal()

    # 添加标题信号
    addTitle = pyqtSignal()

    # 返回文案标签信息信号
    copyLabelResultReady = pyqtSignal(dict)

    # 通用进度信号 (current, total, message)
    progress = pyqtSignal(int, int, str)

    # 后台更新检查结果
    updateResultReady = pyqtSignal(object)
