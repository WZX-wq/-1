import unittest
from unittest.mock import patch

import mysql.connector

from database_tool import mysql_read_tool
from sanong_generation.errors import DatabaseWriteError
from sanong_generation.repository import SanongTitle, SanongTitleRepository


class SanongTitleRepositoryTests(unittest.TestCase):
    def test_fetch_next_returns_none_for_successful_empty_query(self):
        with patch("sanong_generation.repository.fetch_with_retry", return_value=None) as query:
            result = SanongTitleRepository().fetch_next("账号A")

        self.assertIsNone(result)
        sql = query.call_args.args[1]
        params = query.call_args.args[2]
        self.assertIn("title_type = %s", sql)
        self.assertEqual(params[:2], ("账号A", 6))
        self.assertTrue(query.call_args.kwargs["raise_on_failure"])

    def test_fetch_next_maps_database_row(self):
        row = (21, "宅基地政策", "标题&&三农&&正文", "宅基地", None, "账号A", 6, None, 0)
        with patch("sanong_generation.repository.fetch_with_retry", return_value=row):
            title = SanongTitleRepository().fetch_next("账号A")

        self.assertIsInstance(title, SanongTitle)
        self.assertEqual(title.id, 21)
        self.assertEqual(title.title, "宅基地政策")
        self.assertEqual(title.content, "标题&&三农&&正文")

    def test_fetch_next_is_limited_to_imported_titles(self):
        with patch("sanong_generation.repository.fetch_with_retry", return_value=None) as query:
            SanongTitleRepository().fetch_next(
                "账号A", ["本次标题一", "本次标题二"]
            )

        sql = query.call_args.args[1]
        params = query.call_args.args[2]
        self.assertIn("title IN (%s, %s)", sql)
        self.assertEqual(
            params,
            ("账号A", 6, params[2], "本次标题一", "本次标题二"),
        )

    def test_fetch_with_retry_can_raise_after_retries(self):
        with patch.object(
            mysql_read_tool.mysql.connector,
            "connect",
            side_effect=mysql.connector.Error("down"),
        ), patch.object(mysql_read_tool.time, "sleep"):
            with self.assertRaisesRegex(mysql_read_tool.DatabaseReadError, "测试查询"):
                mysql_read_tool.fetch_with_retry(
                    {}, "SELECT 1", operation_name="测试查询", raise_on_failure=True
                )

    def test_mark_generated_raises_when_database_write_fails(self):
        title = SanongTitle((21, "标题", None, None, None, "账号A", 6, None, 0))
        with patch("sanong_generation.repository.mark_title_generated", return_value=False):
            with self.assertRaisesRegex(DatabaseWriteError, "标记标题"):
                SanongTitleRepository().mark_generated(title)

    def test_import_titles_writes_selected_account_as_type_six(self):
        connection = FakeConnection(rowcount=2)
        repository = SanongTitleRepository(
            connection_factory=lambda **_config: connection
        )

        summary = repository.import_titles("账号A", ["标题一", "标题二"])

        self.assertIn("INSERT IGNORE INTO video_title_info", connection.cursor_value.sql)
        self.assertEqual(
            connection.cursor_value.params,
            [("标题一", "账号A", 6), ("标题二", "账号A", 6)],
        )
        self.assertTrue(connection.committed)
        self.assertTrue(connection.closed)
        self.assertEqual(summary.read, 2)
        self.assertEqual(summary.inserted, 2)
        self.assertEqual(summary.duplicates, 0)
        self.assertEqual(summary.account_name, "账号A")
        self.assertEqual(summary.titles, ("标题一", "标题二"))

    def test_import_titles_rolls_back_database_error(self):
        connection = FakeConnection(error=mysql.connector.Error("write failed"))
        repository = SanongTitleRepository(
            connection_factory=lambda **_config: connection
        )

        with self.assertRaisesRegex(DatabaseWriteError, "导入三农标题失败"):
            repository.import_titles("账号A", ["标题一"])

        self.assertTrue(connection.rolled_back)
        self.assertTrue(connection.closed)


class FakeCursor:
    def __init__(self, rowcount=0, error=None):
        self.rowcount = rowcount
        self.error = error
        self.sql = None
        self.params = None
        self.closed = False

    def executemany(self, sql, params):
        if self.error:
            raise self.error
        self.sql = sql
        self.params = list(params)

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, rowcount=0, error=None):
        self.cursor_value = FakeCursor(rowcount=rowcount, error=error)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


if __name__ == "__main__":
    unittest.main()
