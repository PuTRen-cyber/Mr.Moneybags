from pathlib import Path
import json
import os
import subprocess
import sys
import unittest


class StartupTest(unittest.TestCase):
    def run_cli(self, user_input):
        return subprocess.run(
            [sys.executable, "-m", "mr_moneybags"],
            cwd=Path(__file__).resolve().parents[1],
            input=user_input,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=10,
        )

    def test_module_creates_one_task_and_exits(self):
        raw_input = "  请整理本周工作计划  "
        result = self.run_cli(raw_input + "\n不要处理第二条任务\n")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Mr.Moneybags", result.stdout)
        self.assertIn("JIA", result.stdout)
        task = json.loads(result.stdout[result.stdout.index("{"):])
        self.assertEqual(
            set(task),
            {"id", "raw_input", "goal", "expected_outcome", "constraints",
             "acceptance_criteria", "status"},
        )
        self.assertTrue(task["id"])
        self.assertEqual(task["raw_input"], raw_input)
        self.assertEqual(task["goal"], raw_input.strip())
        self.assertEqual(task["status"], "NEW")
        self.assertIsNone(task["expected_outcome"])
        self.assertIsNone(task["constraints"])
        self.assertIsNone(task["acceptance_criteria"])
        self.assertEqual(result.stderr, "")

    def test_blank_input_exits_without_creating_task(self):
        result = self.run_cli("  \t\n")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Task input must not be blank.", result.stderr)
        self.assertNotIn("{", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_end_of_input_exits_normally(self):
        result = self.run_cli("")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("{", result.stdout)
        self.assertEqual(result.stderr, "")
