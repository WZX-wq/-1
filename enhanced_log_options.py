"""
增强的日志选项
为你的 add_log 函数提供更多选择
"""

from datetime import datetime
from PySide6.QtGui import QTextCursor

# 选项1：简单的顶部显示（推荐，已应用到main.py）
def add_log_simple_top(self, text: str):
    """最简单的顶部显示版本"""
    cursor = self.run_label.textCursor()
    cursor.movePosition(cursor.MoveOperation.Start)
    cursor.insertText(text + '\n')
    
    if self.run_label.document().blockCount() > MAX_LINES:
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.select(cursor.SelectionType.BlockUnderCursor)
        cursor.removeSelectedText()
    
    cursor.movePosition(cursor.MoveOperation.Start)
    self.run_label.setTextCursor(cursor)
    self.run_label.ensureCursorVisible()

# 选项2：带时间戳的版本
def add_log_with_timestamp(self, text: str):
    """带时间戳的顶部显示版本"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_text = f"[{timestamp}] {text}"
    
    cursor = self.run_label.textCursor()
    cursor.movePosition(cursor.MoveOperation.Start)
    cursor.insertText(log_text + '\n')
    
    if self.run_label.document().blockCount() > MAX_LINES:
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.select(cursor.SelectionType.BlockUnderCursor)
        cursor.removeSelectedText()
    
    cursor.movePosition(cursor.MoveOperation.Start)
    self.run_label.setTextCursor(cursor)
    self.run_label.ensureCursorVisible()

# 选项3：可选择显示位置
def add_log_flexible(self, text: str, show_at_top: bool = True, show_timestamp: bool = False):
    """灵活的日志显示版本"""
    if show_timestamp:
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_text = f"[{timestamp}] {text}"
    else:
        log_text = text
    
    cursor = self.run_label.textCursor()
    
    if show_at_top:
        # 在顶部插入
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.insertText(log_text + '\n')
        
        # 删除超出的行
        if self.run_label.document().blockCount() > MAX_LINES:
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
        
        # 移动到顶部
        cursor.movePosition(cursor.MoveOperation.Start)
        self.run_label.setTextCursor(cursor)
        self.run_label.ensureCursorVisible()
    else:
        # 在底部添加（原方式）
        self.run_label.append(log_text)
        
        # 删除超出的行
        if self.run_label.document().blockCount() > MAX_LINES:
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()

# 选项4：使用HTML格式的彩色日志
def add_log_colored(self, text: str, level: str = "INFO"):
    """带颜色和级别的日志显示"""
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # 定义颜色
    colors = {
        "INFO": "#000000",     # 黑色
        "SUCCESS": "#00AA00",  # 绿色
        "WARNING": "#FF8800",  # 橙色
        "ERROR": "#FF0000",    # 红色
        "DEBUG": "#888888"     # 灰色
    }
    
    color = colors.get(level, "#000000")
    html_text = f'<span style="color: {color};">[{timestamp}] [{level}] {text}</span>'
    
    cursor = self.run_label.textCursor()
    cursor.movePosition(cursor.MoveOperation.Start)
    cursor.insertHtml(html_text + "<br>")
    
    if self.run_label.document().blockCount() > MAX_LINES:
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.select(cursor.SelectionType.BlockUnderCursor)
        cursor.removeSelectedText()
    
    cursor.movePosition(cursor.MoveOperation.Start)
    self.run_label.setTextCursor(cursor)
    self.run_label.ensureCursorVisible()

# 使用说明：
"""
选择适合你的版本，然后替换 main.py 中的 add_log 方法：

1. 简单版本（已应用）：
   - 最新日志在最上面
   - 简单直接

2. 带时间戳版本：
   add_log = add_log_with_timestamp

3. 灵活版本：
   add_log = add_log_flexible
   # 使用：add_log("test", show_at_top=True, show_timestamp=True)

4. 彩色版本：
   add_log = add_log_colored
   # 使用：add_log("成功", "SUCCESS")
"""

# 如果你想要带时间戳，可以替换 main.py 中的方法为：
# 将 add_log 方法替换为：
"""
def add_log(self, text: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_text = f"[{timestamp}] {text}"
    
    cursor = self.run_label.textCursor()
    cursor.movePosition(cursor.MoveOperation.Start)
    cursor.insertText(log_text + '\n')
    
    if self.run_label.document().blockCount() > MAX_LINES:
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.select(cursor.SelectionType.BlockUnderCursor)
        cursor.removeSelectedText()
    
    cursor.movePosition(cursor.MoveOperation.Start)
    self.run_label.setTextCursor(cursor)
    self.run_label.ensureCursorVisible()
"""