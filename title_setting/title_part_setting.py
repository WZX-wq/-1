# 标题行设置
import json
import os
import re
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QWidget, QMessageBox, QColorDialog

from ui.show_title_part_setting import Ui_title_part_setting


class TitlePartSetting(QWidget, Ui_title_part_setting):
    def __init__(self, part_num):
        super(TitlePartSetting, self).__init__()
        self.setupUi(self)
        self.part_num = part_num
        self.initUI()

    def initUI(self):
        self.setWindowTitle('标题行设置添加')
        self.fontColorToolButton.clicked.connect(self.choose_font_color)
        self.pushButton.clicked.connect(self.save_part_setting)
        self.borderColorToolButton.clicked.connect(self.choose_border_color)
        self.show_part_setting()

    def show_part_setting(self):
        self.setWindowTitle(f'标题第{self.part_num}行设置添加')
        # 特效
        self.scrollCombo.addItems(
            ["缩放效果", "旋转效果", "颜色渐变效果", "模糊效果+淡入"])

        self.scrollCombo.setCurrentIndex(3)

        # 对齐
        self.alignCombo.addItems(['默认', '左上', '左中', '左下', '右上', '右中', '右下'])

        with open('setting.txt', 'r', encoding='utf-8') as file:
            dictionary = json.load(file)

        style_dict = dictionary[f'part_title_part_{self.part_num}_set']

        # 有配置就使用，没有就默认值
        if style_dict:
            # 字体颜色
            self.fontColorLineEdit.setText(style_dict['fontColor'])

            # 边框颜色
            self.borderColorLineEdit.setText(style_dict['borderColor'])

            # 字体大小
            self.fontSizeSpin.setValue(int(style_dict['fontSize']))

            # 字体换行间距
            self.titleYSpaceSpin.setValue(int(style_dict['VSpace']))

            # 特效
            self.scrollCombo.setCurrentIndex(style_dict['fontScroll'])

            # 对齐
            self.alignCombo.setCurrentIndex(style_dict['align'])

            # X
            self.xSpin.setValue(int(style_dict['x']))

            # Y
            self.ySpin.setValue(int(style_dict['y']))

    def save_part_setting(self):
        show_style_dict = {
            'fontColor': self.fontColorLineEdit.text(),  # 字体颜色
            'borderColor': self.borderColorLineEdit.text(),  # 边框颜色
            'fontSize': self.fontSizeSpin.value(),  # 字体大小
            'fontScroll': self.scrollCombo.currentIndex(),  # 特效
            'VSpace': self.titleYSpaceSpin.value(),  # 行间距
            'align': self.alignCombo.currentIndex(),  # 对齐
            'x': self.xSpin.value(),
            'y': self.ySpin.value()
        }

        with open('setting.txt', 'r', encoding='utf-8') as file:
            dictionary = json.load(file)

        dictionary[f'part_title_part_{self.part_num}_set'] = show_style_dict

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
        msg_box.setText(f"保存{self.part_num}行设置成功")
        msg_box.exec()

    def choose_font_color(self):
        color = QColorDialog.getColor(QColor(self.fontColorLineEdit.text()), self)
        if color.isValid():
            self.fontColorLineEdit.setText(color.name())

    def choose_border_color(self):
        color = QColorDialog.getColor(QColor(self.borderColorLineEdit.text()), self)
        if color.isValid():
            self.borderColorLineEdit.setText(color.name())


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


def read_title_part_dict_from_txt(file_path):
    """从文本文件读取字典，如果文件不存在则创建一个空文件"""
    try:
        show_style_dict = {
            'fontBorderSize': 1,  # 边框大小
            'fontColor': '#ffff00',  # 字体颜色
            'borderColor': '#000000',
            'fontSize': 16,  # 字体大小
            'fontScroll': 0,  # 特效
            'VSpace': 1,  # 行间距
            'align': 0,  # 对齐
            'x': 0,
            'y': 0,
        }
        if not os.path.exists(file_path):
            # 如果文件不存在，创建一个空文件
            open(file_path, 'w', encoding='utf-8').close()
            write_dict_to_txt(file_path, show_style_dict)
            print(f"文件已创建: {file_path}")
            return show_style_dict

        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            if not content:
                print(f"文件内容为空: {file_path}")
                write_dict_to_txt(file_path, show_style_dict)
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
