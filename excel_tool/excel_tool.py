import os

import xlwt
from openpyxl.reader.excel import load_workbook
from openpyxl.workbook import Workbook


# 获取指定行的数据
def get_row_data(file_path, row_number):
    """
    从指定的 Excel 文件中读取指定行的数据，并以数组的形式返回。

    参数：
        file_path: Excel 文件路径
        row_number: 要读取的行号（从 1 开始）

    返回：
        指定行的数据，以数组形式返回
    """
    try:
        # 加载 Excel 文件
        workbook = load_workbook(filename=file_path)
        sheet = workbook.active  # 获取活动工作表

        # 检查行号是否有效
        if row_number < 1 or row_number > sheet.max_row:
            raise ValueError(f"行号 {row_number} 超出范围。有效范围是 1 到 {sheet.max_row}")

        # 获取指定行的数据
        row_data = [cell.value for cell in sheet[row_number] if cell.value is not None]

        return row_data

    except FileNotFoundError:
        return []
    except Exception as e:
        return []


# 获取起始有 数据行的行号
def get_first_data_row(file_path):
    """
    获取 Excel 表格中第一个有数据的行的行号。

    参数：
        file_path: Excel 文件路径

    返回：
        第一个有数据的行的行号（从1开始）
    """
    try:
        # 加载 Excel 文件
        workbook = load_workbook(filename=file_path)
        sheet = workbook.active  # 获取活动工作表

        # 遍历每一行，直到找到第一个有数据的行
        for row in sheet.iter_rows(min_row=1, max_col=1, values_only=True):
            if row[0] is not None:  # 检查第一列是否有数据
                # 获取当前行的行号
                current_row = sheet.iter_rows(min_row=1, max_col=1, values_only=False)
                for _ in range(len(list(sheet.iter_rows(min_row=1, max_col=1, values_only=False)))):
                    next_row = next(current_row)
                    if next_row[0].value is not None:
                        return next_row[0].row  # 返回第一个有数据的行号

        # 如果没有找到任何数据，返回 None
        return None

    except Exception as e:
        print(f"读取 Excel 文件时出错: {e}")
        return None

def write_to_excel(file_name, data_dict):
    """
    写入数据到 Excel 文件中。

    :param file_name: Excel 文件名
    :param data_dict: 包含数据的字典
    """
    # 定义表格标题
    headers = ["标题", "标签", "文件路径", "描述", "封面路径", "图片集合", "关联商品", "分区分类", "备注"]

    # 检查文件是否存在
    if not os.path.exists(file_name):
        # 文件不存在，创建一个新的 Excel 文件并写入标题
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(headers)
    else:
        # 文件已存在，加载现有文件
        workbook = load_workbook(file_name)
        sheet = workbook.active

    # 将字典数据写入表格
    row = [data_dict.get(header, "") for header in headers]
    sheet.append(row)

    # 保存文件
    workbook.save(file_name)
    print(f"数据已写入到文件：{file_name}")


def write_to_old_excel(file_name, data_dict):
    """
    写入数据到 Excel 文件中。

    :param file_name: Excel 文件名
    :param data_dict: 包含数据的字典
    """
    # 定义表格标题
    headers = ["标题", "标签", "文件路径", "描述", "封面路径", "图片集合", "关联商品", "分区分类", "备注"]

    # 检查文件是否存在
    if not os.path.exists(file_name):
        # 文件不存在，创建一个新的 Excel 文件并写入标题
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet("Sheet1")

        # 写入标题行
        for col, header in enumerate(headers):
            sheet.write(0, col, header)

        # 写入数据行
        row_index = 1
    else:
        # 文件已存在，加载现有文件
        # 注意：xlwt 不支持直接读取和追加到现有的 .xls 文件
        # 因此，我们需要先读取现有数据，然后追加新数据
        from xlrd import open_workbook
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet("Sheet1")

        # 读取现有数据
        existing_workbook = open_workbook(file_name)
        existing_sheet = existing_workbook.sheet_by_index(0)

        # 写入现有数据
        for row in range(existing_sheet.nrows):
            for col in range(existing_sheet.ncols):
                sheet.write(row, col, existing_sheet.cell(row, col).value)

        # 确定新的行索引
        row_index = existing_sheet.nrows

    # 将字典数据写入表格
    row_data = [data_dict.get(header, "") for header in headers]
    for col, value in enumerate(row_data):
        sheet.write(row_index, col, value)

    # 保存文件
    workbook.save(file_name)
    print(f"数据已写入到文件：{file_name}")


# get_row_data('上饶话题100个_copy.xlsx', 3)
# write_to_excel('D:\\batchAiCutter\\batchAiCutter\\task\\task_1751290842.xlsx', {
#     "标题": "示例标题1",
#     "标签": "标签1",
#     "文件路径": "/path/to/file1",
#     "描述": "这是描述1",
#     "封面路径": "/path/to/cover1",
#     "图片集合": "图片1,图片2",
#     "关联商品": "商品1",
#     "分区分类": "分类1",
#     "备注": "备注1"
# })
