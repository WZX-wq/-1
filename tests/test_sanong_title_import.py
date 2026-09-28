import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from sanong_generation.title_import import read_title_workbook


def write_workbook(path: Path, rows) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(list(row))
    workbook.save(path)
    workbook.close()
    return path


class ReadTitleWorkbookTests(unittest.TestCase):
    def test_workbook_without_header_keeps_first_title_and_removes_duplicates(self):
        with tempfile.TemporaryDirectory() as root:
            path = write_workbook(
                Path(root) / "无表头.xlsx",
                [
                    (" 第一条标题 ", "文案一"),
                    ("第二条标题", "文案二"),
                    ("第一条标题", "重复文案"),
                    (None, None),
                    ("   ", "空标题"),
                ],
            )

            titles = read_title_workbook(path)

        self.assertEqual(titles, ["第一条标题", "第二条标题"])

    def test_workbook_with_header_skips_header_only(self):
        with tempfile.TemporaryDirectory() as root:
            path = write_workbook(
                Path(root) / "有表头.xlsx",
                [("标题", "文案"), ("宅基地政策", "正文")],
            )

            titles = read_title_workbook(path)

        self.assertEqual(titles, ["宅基地政策"])


if __name__ == "__main__":
    unittest.main()
