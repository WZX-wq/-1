"""
日志显示增强示例
提供多种日志显示方式的实现
"""

from datetime import datetime
from PySide6.QtGui import QTextCursor

class LogDisplayEnhancer:
    """日志显示增强器"""
    
    @staticmethod
    def add_log_top(widget, text: str, max_lines: int = 1000, show_timestamp: bool = False):
        """最新日志显示在最上面（推荐）"""
        cursor = widget.textCursor()
        
        # 可选：添加时间戳
        if show_timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_text = f"[{timestamp}] {text}\n"
        else:
            log_text = f"{text}\n"
        
        # 在开头插入
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.insertText(log_text)
        
        # 限制行数
        if widget.document().blockCount() > max_lines:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
        
        # 滚动到顶部
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        widget.setTextCursor(cursor)
        widget.ensureCursorVisible()
    
    @staticmethod
    def add_log_bottom(widget, text: str, max_lines: int = 1000, show_timestamp: bool = False):
        """最新日志显示在最下面（默认方式）"""
        if show_timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_text = f"[{timestamp}] {text}"
        else:
            log_text = text
        
        widget.append(log_text)
        
        # 限制行数
        if widget.document().blockCount() > max_lines:
            cursor = widget.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
        
        # 滚动到底部
        cursor = widget.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        widget.setTextCursor(cursor)
        widget.ensureCursorVisible()
    
    @staticmethod
    def add_log_with_level(widget, text: str, level: str = "INFO", max_lines: int = 1000):
        """带日志级别的显示"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 不同级别使用不同颜色
        level_colors = {
            "INFO": "black",
            "SUCCESS": "green", 
            "WARNING": "orange",
            "ERROR": "red",
            "DEBUG": "gray"
        }
        
        color = level_colors.get(level, "black")
        log_text = f'<span style="color: {color};">[{timestamp}] [{level}] {text}</span>'
        
        # 在开头插入
        cursor = widget.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.insertHtml(log_text + "<br>")
        
        # 限制行数
        if widget.document().blockCount() > max_lines:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
        
        # 滚动到顶部
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        widget.setTextCursor(cursor)
        widget.ensureCursorVisible()

# 使用示例：在你的类中替换原来的 add_log 方法

"""
# 方式1：简单替换（最新在上面）
def add_log(self, text: str):
    LogDisplayEnhancer.add_log_top(self.run_label, text, MAX_LINES)

# 方式2：带时间戳
def add_log(self, text: str):
    LogDisplayEnhancer.add_log_top(self.run_label, text, MAX_LINES, show_timestamp=True)

# 方式3：带日志级别
def add_log(self, text: str, level: str = "INFO"):
    LogDisplayEnhancer.add_log_with_level(self.run_label, text, level, MAX_LINES)

# 使用带级别的方式示例：
# self.add_log("视频开始处理", "INFO")
# self.add_log("处理完成", "SUCCESS") 
# self.add_log("发现错误", "ERROR")
# self.add_log("调试信息", "DEBUG")
"""

# 向后兼容的替换方案
def create_enhanced_add_log_method(widget_name: str = "run_label", max_lines_var: str = "MAX_LINES"):
    """创建增强的add_log方法"""
    
    def add_log_enhanced(self, text: str):
        """增强版add_log，最新日志显示在最上面"""
        widget = getattr(self, widget_name)
        max_lines = getattr(self, max_lines_var)
        
        cursor = widget.textCursor()
        
        # 在开头插入
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.insertText(text + '\n')
        
        # 限制行数
        if widget.document().blockCount() > max_lines:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
        
        # 滚动到顶部
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        widget.setTextCursor(cursor)
        widget.ensureCursorVisible()
    
    return add_log_enhanced

# 在你的类中这样使用：
# add_log = create_enhanced_add_log_method()()