import json
import os

from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QWidget, QMessageBox, QColorDialog

from ui.show_title_setting import Ui_title_setting


class TitleSetting(QWidget, Ui_title_setting):
    def __init__(self, title_type='1'):
        super(TitleSetting, self).__init__()
        self.setupUi(self)
        self.title_type = title_type
        self.ass_head_file_path = ''
        self.title_style_dict = None
        self.part_title_style_dict = None
        self.initUI()

    def initUI(self):

        self.setWindowTitle('添加标题设置')

        self.show_setting()

        self.confirmSaveTitletoolButton.clicked.connect(self.save_setting)

        # 字体颜色
        self.fontColorToolButton.clicked.connect(self.choose_font_color)

        # 边框颜色
        self.borderColorToolButton.clicked.connect(self.choose_border_color)

        # 背景颜色
        self.shadowColorToolButton.clicked.connect(self.choose_background_color)

    # 展示设置
    def show_setting(self):

        self.scrollCombo.addItems(
            ['无', "淡入淡出效果", "缩放效果", "旋转效果", "颜色渐变效果", "模糊效果+淡入"])

        with open('setting.txt', 'r', encoding='utf-8') as file:
            dictionary = json.load(file)

        if self.title_type == '1':
            show_style_dict = dictionary[f'title_set']
        else:
            show_style_dict = dictionary[f'part_title_set']

        # 字体设置
        self.fontFamilyComboBox.setCurrentFont(QFont(show_style_dict['fontFamily']))

        # 边框大小
        self.borderSizeSpin.setValue(int(show_style_dict['fontBorderSize']))

        # 阴影深度
        self.shadowDepthSpin.setValue(int(show_style_dict['shadowDepth']))

        # 粗体
        if show_style_dict['fontBold'] == 1:
            self.boldCheck.setChecked(True)

        # 字体颜色
        self.fontColorLineEdit.setText(show_style_dict['fontColor'])

        # 字体大小
        self.fontSizeSpin.setValue(int(show_style_dict['fontSize']))

        # 斜体
        if show_style_dict['fontItalic'] == 1:
            self.italicCheck.setChecked(True)

        # 边框颜色
        self.borderColorLineEdit.setText(show_style_dict['borderColor'])

        # # 特效
        # self.scrollCombo.setCurrentIndex(show_style_dict['fontScroll'])

        # 下划线
        if show_style_dict['fontUnderline'] == 1:
            self.underlineCheck.setChecked(True)


        # 阴影颜色
        self.shadowColorLineEdit.setText(show_style_dict['shadowColor'])

        # # 标题时间
        # self.titleTimeSpin.setValue(int(show_style_dict['titleTime']))
        #
        # 行间距
        self.titleLineSpaceSpin.setValue(int(show_style_dict['titleLineSpace']))
        #
        # 位置调整
        self.titleSpaceSpin.setValue(int(show_style_dict['titleSpace']))

    def save_setting(self):

        show_style_dict = {
            'fontFamily': self.fontFamilyComboBox.currentFont().family(),  #字体
            'fontBorderSize': self.borderSizeSpin.value(),  #边框大小
            'shadowDepth': self.shadowDepthSpin.value(),  #阴影大小
            'fontBold': 1 if self.boldCheck.isChecked() else 0,  #粗体
            'fontColor': self.fontColorLineEdit.text(),  #字体颜色
            'fontSize': self.fontSizeSpin.value(),  #字体大小
            'fontItalic': 1 if self.italicCheck.isChecked() else 0,  #斜体
            'borderColor': self.borderColorLineEdit.text(),  #边框颜色
            'fontScroll': self.scrollCombo.currentIndex(),  #特效
            'fontUnderline': 1 if self.underlineCheck.isChecked() else 0,  #下划线
            'shadowColor': self.shadowColorLineEdit.text(),  #阴影颜色
            'titleTime': self.titleTimeSpin.value(),  #标题时间
            'titleLineSpace': self.titleLineSpaceSpin.value(),  #行间距
            'titleSpace': self.titleSpaceSpin.value(),  #位置调整
        }

        with open('setting.txt', 'r', encoding='utf-8') as file:
            dictionary = json.load(file)

        if self.title_type == '1':
            self.title_style_dict = show_style_dict
            dictionary['title_set'] = show_style_dict
            write_dict_to_txt('setting.txt', dictionary)
            self.show_setting()
        else:
            self.part_title_style_dict = show_style_dict
            dictionary['part_title_set'] = show_style_dict
            write_dict_to_txt('setting.txt', dictionary)
            self.show_setting()
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
        msg_box.setText("保存设置成功")
        msg_box.exec()

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


def read_dict_from_txt(file_path):
    """从文本文件读取字典，如果文件不存在则创建一个空文件"""
    try:
        show_style_dict = {
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
        if not os.path.exists(file_path):
            # 如果文件不存在，创建一个空文件
            open(file_path, 'w', encoding='utf-8').close()
            print(f"文件已创建: {file_path}")
            return show_style_dict

        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            if not content:
                print(f"文件内容为空: {file_path}")
                return show_style_dict

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

