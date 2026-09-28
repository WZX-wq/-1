# 删除main.py中9502-9555行的重复背景获取逻辑
import os

file_path = r'd:/batchAiCutter/batchAiCutter_1/main.py'

# 读取文件
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 删除9502-9555行（重复的背景获取逻辑）
new_lines = lines[:9501] + lines[9556:]

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'已删除第9502-9555行，共删除{9555-9501+1}行')
