import unittest
from collections import deque
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

from database_tool.mysql_read_tool import DatabaseReadError
from sanong_generation.composer import SanongVideoResult
from sanong_generation.errors import (
    MediaGenerationError,
    SystemGenerationError,
    TitleGenerationError,
)
from sanong_generation.repository import SanongTitle
from sanong_generation.service import SanongGenerationService


def title(title_id):
    return SanongTitle(
        (
            title_id,
            f"标题{title_id}",
            f"标题{title_id}&&三农&&片段1&&片段2&&片段3",
            "标签1&&标签2&&标签3",
            None,
            "账号",
            6,
            None,
            0,
        )
    )


def success(title_id):
    return [
        SanongVideoResult(
            video_path=Path(f"标题{title_id}.mp4"),
            title=f"标题{title_id}",
            tag="三农",
            description=("片段1", "片段2", "片段3"),
            material_ids=(1, 2, 3),
        )
    ]


class FakeRepository:
    def __init__(self, queues=None, fetch_error=None):
        self.queues = {
            name: deque(items) for name, items in (queues or {}).items()
        }
        self.fetch_error = fetch_error
        self.fetch_order = []
        self.fetch_scopes = []
        self.failed_ids = []
        self.generated_ids = []
        self.fetch_count = 0

    def fetch_next(self, account, allowed_titles=None):
        self.fetch_count += 1
        self.fetch_order.append(account)
        self.fetch_scopes.append(tuple(allowed_titles or ()))
        if self.fetch_error:
            raise self.fetch_error
        return self.queues[account].popleft()

    def record_failure(self, item):
        self.failed_ids.append(item.id)

    def mark_generated(self, item):
        self.generated_ids.append(item.id)


def make_service(repository, compose_side_effect=None, failure_limit=3):
    config = SimpleNamespace(
        max_consecutive_system_failures=failure_limit,
        create_upload_tasks=False,
        output_dir=Path("output"),
        base_dir=Path("."),
        minimum_free_space_mb=0,
    )
    composer = Mock()
    if compose_side_effect is None:
        composer.compose.return_value = success(1)
    else:
        composer.compose.side_effect = compose_side_effect
    return SanongGenerationService(
        config=config,
        repository=repository,
        copywriter=Mock(),
        composer=composer,
        account_settings_loader=lambda _account: {},
        task_publisher=lambda _account, _result: None,
        log=lambda _message: None,
    )


class SanongGenerationServiceTests(unittest.TestCase):
    def test_low_disk_space_stops_before_claiming_a_title(self):
        repository = FakeRepository({"甲": [title(1), None]})
        service = make_service(repository=repository)
        service.config.minimum_free_space_mb = 1

        with patch(
            "sanong_generation.service.shutil.disk_usage",
            return_value=SimpleNamespace(free=512 * 1024),
        ), self.assertRaisesRegex(SystemGenerationError, "磁盘空间不足"):
            service.run(["甲"])

        self.assertEqual(repository.fetch_count, 0)

    def test_title_work_directory_is_removed_after_generation(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            repository = FakeRepository({"甲": [title(1), None]})
            service = make_service(repository=repository)
            service.config.base_dir = root_path
            service.config.output_dir = root_path / "output"
            service.config.minimum_free_space_mb = 0
            service.account_settings_loader = lambda _account: {}

            summary = service.run(["甲"])

            self.assertEqual(summary.generated, 1)
            self.assertFalse((root_path / "temp_title" / "sanong_1").exists())

    def test_round_robins_accounts_until_each_is_exhausted(self):
        repository = FakeRepository(
            {
                "甲": [title(1), title(3), None],
                "乙": [title(2), None],
            }
        )
        service = make_service(repository=repository)

        summary = service.run(["甲", "乙"])

        self.assertEqual(repository.fetch_order, ["甲", "乙", "甲", "乙", "甲"])
        self.assertEqual(repository.generated_ids, [1, 2, 3])
        self.assertEqual(summary.generated, 3)
        self.assertEqual(summary.exhausted_accounts, 2)

    def test_title_failure_is_recorded_and_next_title_runs(self):
        repository = FakeRepository({"甲": [title(1), title(2), None]})
        service = make_service(
            repository=repository,
            compose_side_effect=[TitleGenerationError("素材不足"), success(2)],
        )

        summary = service.run(["甲"])

        self.assertEqual(repository.failed_ids, [1])
        self.assertEqual(repository.generated_ids, [2])
        self.assertEqual(summary.generated, 1)
        self.assertEqual(summary.title_failures, 1)

    def test_only_fetches_titles_from_the_imported_workbook(self):
        repository = FakeRepository({"甲": [title(1), None]})
        service = make_service(repository=repository)

        service.run(["甲"], ["本次标题一", "本次标题二"])

        self.assertEqual(
            repository.fetch_scopes,
            [
                ("本次标题一", "本次标题二"),
                ("本次标题一", "本次标题二"),
            ],
        )

    def test_three_consecutive_database_failures_abort(self):
        repository = FakeRepository(fetch_error=DatabaseReadError("down"))
        service = make_service(repository=repository, failure_limit=3)

        with self.assertRaises(SystemGenerationError):
            service.run(["甲", "乙"])

        self.assertEqual(repository.fetch_count, 3)

    def test_three_consecutive_generation_system_failures_abort(self):
        repository = FakeRepository(
            {"甲": [title(1), title(2), title(3), title(4)]}
        )
        service = make_service(
            repository=repository,
            compose_side_effect=RuntimeError("AI endpoint unavailable"),
            failure_limit=3,
        )

        with self.assertRaisesRegex(SystemGenerationError, "连续 3 次系统错误"):
            service.run(["甲"])

        self.assertEqual(repository.fetch_count, 3)
        self.assertEqual(service.composer.compose.call_count, 3)

    def test_three_consecutive_ai_endpoint_failures_abort_without_skipping_titles(self):
        repository = FakeRepository({
            "甲": [
                SanongTitle((index, f"标题{index}", None, None, None, "账号", 6, None, 0))
                for index in range(1, 5)
            ]
        })
        messages = []
        service = make_service(repository=repository, failure_limit=3)
        service.log = messages.append
        service.copywriter.side_effect = RuntimeError("InvalidEndpoint.ClosedEndpoint")

        with self.assertRaisesRegex(SystemGenerationError, "连续 3 次系统错误"):
            service.run(["甲"])

        self.assertEqual(repository.fetch_count, 3)
        self.assertEqual(service.copywriter.call_count, 3)
        self.assertEqual(repository.failed_ids, [])
        self.assertEqual(repository.generated_ids, [])
        self.assertTrue(any("(1/3)" in message for message in messages))
        self.assertTrue(any("(2/3)" in message for message in messages))
        self.assertTrue(any("(3/3)" in message for message in messages))

    def test_memory_exhaustion_stops_without_marking_title_as_failed(self):
        repository = FakeRepository({"甲": [title(1), title(2), None]})
        service = make_service(
            repository=repository,
            compose_side_effect=MediaGenerationError("Cannot allocate memory"),
        )

        with self.assertRaisesRegex(SystemGenerationError, "内存不足"):
            service.run(["甲"])

        self.assertEqual(repository.fetch_count, 1)
        self.assertEqual(repository.failed_ids, [])
        self.assertEqual(repository.generated_ids, [])

    def test_memory_error_stops_immediately_with_actionable_message(self):
        repository = FakeRepository({"甲": [title(1), title(2), None]})
        service = make_service(repository=repository, compose_side_effect=MemoryError())

        with self.assertRaisesRegex(SystemGenerationError, "关闭其他程序"):
            service.run(["甲"])

        self.assertEqual(repository.fetch_count, 1)
        self.assertEqual(repository.failed_ids, [])

    def test_windows_pagefile_exhaustion_stops_with_memory_message(self):
        repository = FakeRepository({"甲": [title(1), title(2)]})
        service = make_service(
            repository=repository,
            compose_side_effect=OSError(1455, "The paging file is too small"),
        )

        with self.assertRaisesRegex(SystemGenerationError, "内存不足"):
            service.run(["甲"])

        self.assertEqual(repository.fetch_count, 1)
        self.assertEqual(repository.failed_ids, [])

    def test_stop_request_exits_before_fetching_another_title(self):
        repository = FakeRepository({"甲": [title(1), title(2), None]})
        service = make_service(repository=repository)

        def compose_and_stop(*_args):
            service.request_stop()
            return success(1)

        service.composer.compose.side_effect = compose_and_stop

        summary = service.run(["甲"])

        self.assertEqual(repository.fetch_order, ["甲"])
        self.assertEqual(repository.generated_ids, [1])
        self.assertEqual(summary.generated, 1)
        self.assertEqual(summary.exhausted_accounts, 0)


if __name__ == "__main__":
    unittest.main()
