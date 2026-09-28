from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Sequence

import mysql.connector

from database_tool.mysql_read_tool import DatabaseReadError, fetch_with_retry
from database_tool.video_load_tool import mark_title_generated, record_unsuccess_title_info

from .errors import DatabaseWriteError


TITLE_DB_CONFIG = {
    "host": "82.157.237.217",
    "database": "ai_video",
    "user": "ljx_lepin123",
    "password": "ea.367GZX!#EmwfpEYW$f",
    "port": "35008",
}

SANONG_TITLE_QUERY = """
    SELECT * FROM video_title_info
    WHERE is_generate = 0
      AND account_name = %s
      AND title_type = %s
      AND (last_time IS NULL OR last_time NOT LIKE %s)
    ORDER BY RAND()
    LIMIT 1
"""


@dataclass(frozen=True)
class SanongTitle:
    raw: tuple

    @property
    def id(self) -> int:
        return int(self.raw[0])

    @property
    def title(self) -> str:
        return str(self.raw[1])

    @property
    def content(self) -> str | None:
        return self.raw[2]

    @property
    def label(self) -> str | None:
        return self.raw[3]


@dataclass(frozen=True)
class TitleImportSummary:
    read: int
    inserted: int
    duplicates: int
    account_name: str = ""
    titles: tuple[str, ...] = ()


class SanongTitleRepository:
    TITLE_TYPE = 6

    def __init__(self, connection_factory: Callable[..., object] | None = None):
        self._connection_factory = connection_factory or mysql.connector.connect

    def fetch_next(
        self,
        account_name: str,
        allowed_titles: Sequence[str] | None = None,
    ) -> SanongTitle | None:
        today_pattern = f"%{datetime.now().strftime('%Y-%m-%d')}%"
        query = SANONG_TITLE_QUERY
        params: list[object] = [account_name, self.TITLE_TYPE, today_pattern]
        if allowed_titles is not None:
            scoped_titles = tuple(
                dict.fromkeys(
                    str(title).strip()
                    for title in allowed_titles
                    if str(title).strip()
                )
            )
            if not scoped_titles:
                return None
            placeholders = ", ".join(["%s"] * len(scoped_titles))
            query = query.replace(
                "    ORDER BY RAND()",
                f"      AND title IN ({placeholders})\n    ORDER BY RAND()",
            )
            params.extend(scoped_titles)
        row = fetch_with_retry(
            TITLE_DB_CONFIG,
            query,
            tuple(params),
            operation_name="获取三农标题",
            raise_on_failure=True,
        )
        return SanongTitle(tuple(row)) if row is not None else None

    def health_check(self) -> None:
        fetch_with_retry(
            TITLE_DB_CONFIG,
            "SELECT 1",
            operation_name="检查标题数据库",
            raise_on_failure=True,
        )

    def mark_generated(self, title: SanongTitle) -> None:
        if not mark_title_generated(title.id):
            raise DatabaseWriteError(f"标记标题 {title.id} 已生成失败")

    def record_failure(self, title: SanongTitle) -> None:
        if not record_unsuccess_title_info(title.raw):
            raise DatabaseWriteError(f"记录标题 {title.id} 失败状态失败")

    def import_titles(
        self, account_name: str, titles: Sequence[str]
    ) -> TitleImportSummary:
        rows = [(title, account_name, self.TITLE_TYPE) for title in titles]
        connection = None
        cursor = None
        try:
            connection = self._connection_factory(**TITLE_DB_CONFIG)
            cursor = connection.cursor()
            cursor.executemany(
                """
                INSERT IGNORE INTO video_title_info
                    (title, account_name, title_type)
                VALUES (%s, %s, %s)
                """,
                rows,
            )
            connection.commit()
            inserted = max(0, int(cursor.rowcount))
            return TitleImportSummary(
                read=len(rows),
                inserted=inserted,
                duplicates=max(0, len(rows) - inserted),
                account_name=account_name,
                titles=tuple(title for title, _account, _type in rows),
            )
        except mysql.connector.Error as exc:
            if connection is not None:
                connection.rollback()
            raise DatabaseWriteError(f"导入三农标题失败: {exc}") from exc
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()


__all__ = [
    "DatabaseReadError",
    "SanongTitle",
    "SanongTitleRepository",
    "TitleImportSummary",
]
