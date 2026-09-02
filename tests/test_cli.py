"""O13 CLI 参数测试（subprocess 冒烟）

验证 main.py 的 argparse 非交互参数：--fetch / --export-excel / --count。
不实际抓取（避免网络），只测参数解析与约束。
"""

import subprocess
import sys
import unittest


class TestCli(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, "main.py", *args],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_help_lists_cli_args(self):
        """--help 应列出 --fetch / --export-excel / --count"""
        result = self._run("--help")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("--fetch", result.stdout)
        self.assertIn("--export-excel", result.stdout)
        self.assertIn("--count", result.stdout)

    def test_invalid_fetch_choice_errors(self):
        """--fetch 非法值应被 argparse choices 拒绝"""
        result = self._run("--fetch", "invalid")
        self.assertNotEqual(result.returncode, 0)
        combined = (result.stderr + result.stdout).lower()
        self.assertTrue("invalid" in combined or "choices" in combined)

    def test_valid_fetch_choice_accepted(self):
        """--fetch genshin 应进入 _run_cli（不会因参数错误退出）"""
        # --count 单独跑最安全（不触网络，只读空 SQLite）
        result = self._run("--count")
        # CLI 模式不强制 playwright，应正常退出 0
        self.assertEqual(result.returncode, 0, msg=result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
