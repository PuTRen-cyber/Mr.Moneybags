from pathlib import Path
import subprocess
import sys
import unittest


class StartupTest(unittest.TestCase):
    def test_module_starts_successfully(self):
        result = subprocess.run(
            [sys.executable, "-m", "mr_moneybags"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Mr.Moneybags", result.stdout)
        self.assertIn("JIA", result.stdout)
        self.assertIn("Phase 0", result.stdout)
        self.assertEqual(result.stderr, "")
