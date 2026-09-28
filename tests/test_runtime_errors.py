import unittest

from runtime_errors import (
    MEMORY_EXHAUSTION_MESSAGE,
    is_memory_exhaustion,
    is_system_generation_error,
)


class RuntimeErrorClassificationTests(unittest.TestCase):
    def test_recognizes_python_memory_error(self):
        self.assertTrue(is_memory_exhaustion(MemoryError()))

    def test_recognizes_windows_pagefile_error(self):
        self.assertTrue(is_memory_exhaustion(OSError(1455, "The paging file is too small")))

    def test_memory_message_is_actionable(self):
        self.assertIn("关闭其他程序", MEMORY_EXHAUSTION_MESSAGE)
        self.assertIn("虚拟内存", MEMORY_EXHAUSTION_MESSAGE)

    def test_endpoint_failures_are_system_errors(self):
        self.assertTrue(is_system_generation_error("InvalidEndpoint.ClosedEndpoint"))
        self.assertTrue(is_system_generation_error("HTTPSConnectionPool timeout"))
        self.assertTrue(is_system_generation_error("未配置 AI 接口密钥"))

    def test_title_validation_failure_is_not_system_error(self):
        self.assertFalse(is_system_generation_error("文案格式不符合要求"))


if __name__ == "__main__":
    unittest.main()
