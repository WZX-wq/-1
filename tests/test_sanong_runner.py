import unittest
from unittest.mock import patch

from sanong_generation.errors import StartupConfigurationError
from sanong_runner import main


class SanongRunnerTests(unittest.TestCase):
    def test_check_validates_without_fetching_title(self):
        with patch("sanong_runner.build_runtime") as build_runtime:
            runtime = build_runtime.return_value
            runtime.accounts = ["账号A"]
            runtime.repository.health_check.return_value = None

            code = main(["--check"])

        self.assertEqual(code, 0)
        runtime.repository.fetch_next.assert_not_called()
        runtime.service.run.assert_not_called()

    def test_configuration_error_returns_two(self):
        with patch(
            "sanong_runner.build_runtime",
            side_effect=StartupConfigurationError("缺少音乐"),
        ):
            self.assertEqual(main([]), 2)

    def test_runtime_failure_returns_one(self):
        with patch("sanong_runner.build_runtime") as build_runtime:
            runtime = build_runtime.return_value
            runtime.repository.health_check.return_value = None
            runtime.service.run.side_effect = RuntimeError("boom")

            self.assertEqual(main([]), 1)


if __name__ == "__main__":
    unittest.main()
