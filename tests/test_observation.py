from contextlib import chdir
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from mr_moneybags.observation import observe_workspace


class ObservationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.environment = {
            key: value for key, value in os.environ.items()
            if not key.startswith("GIT_")
        }
        self.environment.update({
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.excludesFile",
            "GIT_CONFIG_VALUE_0": os.devnull,
            "GIT_CEILING_DIRECTORIES": str(self.root.parent),
            "GIT_AUTHOR_NAME": "Test Author",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test Author",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        })

    def git(self, *arguments):
        if shutil.which("git") is None:
            self.skipTest("Git is not installed; real repository fixtures require Git")
        return subprocess.run(
            ["git", *arguments], cwd=self.root, env=self.environment,
            check=True, capture_output=True, text=True, encoding="utf-8",
            timeout=10,
        ).stdout.strip()

    def create_repository(self):
        self.git("init", "--initial-branch=main", "--template=")

    def create_commit(self):
        self.create_repository()
        (self.root / "tracked.txt").write_text("initial\n", encoding="utf-8")
        self.git("add", "tracked.txt")
        self.git("-c", "commit.gpgsign=false", "commit", "-m", "test: create fixture")

    def observe(self):
        with chdir(self.root), patch.dict(os.environ, self.environment, clear=True):
            return observe_workspace()

    def snapshot(self):
        return {
            path.relative_to(self.root).as_posix(): (
                path.read_bytes() if path.is_file() else None,
                path.stat().st_mtime_ns,
            )
            for path in self.root.rglob("*")
        }

    def test_committed_repository_is_clean(self):
        self.create_commit()

        result = self.observe()

        self.assertEqual(Path(result.cwd), self.root)
        self.assertIs(result.is_git_repository, True)
        self.assertEqual(Path(result.git_root), self.root)
        self.assertEqual(result.branch, "main")
        self.assertEqual(result.head_commit, self.git("rev-parse", "HEAD"))
        self.assertIs(result.working_tree_clean, True)
        self.assertEqual(result.files, ["tracked.txt"])
        self.assertEqual(result.trust_level, "Tier 0 — Direct Evidence")
        self.assertFalse(result.files_truncated)
        self.assertEqual(result.errors, [])

    def test_non_repository(self):
        if shutil.which("git") is None:
            self.skipTest("Git is not installed; non-repository detection requires Git")
        (self.root / "plain.txt").touch()

        result = self.observe()

        self.assertIs(result.is_git_repository, False)
        self.assertIsNone(result.git_root)
        self.assertIsNone(result.branch)
        self.assertIsNone(result.head_commit)
        self.assertIsNone(result.working_tree_clean)
        self.assertEqual(result.files, ["plain.txt"])

    def test_repository_without_commit(self):
        self.create_repository()

        result = self.observe()

        self.assertIs(result.is_git_repository, True)
        self.assertEqual(result.branch, "main")
        self.assertIsNone(result.head_commit)
        self.assertIs(result.working_tree_clean, True)
        (self.root / "untracked.txt").touch()
        self.assertIs(self.observe().working_tree_clean, False)

    def test_modified_untracked_and_staged_files_are_dirty(self):
        self.create_commit()
        tracked = self.root / "tracked.txt"
        tracked.write_text("modified\n", encoding="utf-8")
        self.assertIs(self.observe().working_tree_clean, False)
        tracked.write_text("initial\n", encoding="utf-8")
        (self.root / "untracked.txt").touch()
        self.assertIs(self.observe().working_tree_clean, False)
        self.git("add", "untracked.txt")
        self.assertIs(self.observe().working_tree_clean, False)

    def test_detached_head(self):
        self.create_commit()
        self.git("checkout", "--detach", "HEAD")

        result = self.observe()

        self.assertIsNone(result.branch)
        self.assertEqual(result.head_commit, self.git("rev-parse", "HEAD"))
        self.assertIs(result.working_tree_clean, True)

    def test_subdirectory_uses_real_cwd_and_repository_root(self):
        self.create_commit()
        directory = self.root / "src"
        directory.mkdir()
        (directory / "app.py").touch()

        with chdir(directory), patch.dict(os.environ, self.environment, clear=True):
            result = observe_workspace()

        self.assertEqual(Path(result.cwd), directory)
        self.assertEqual(Path(result.git_root), self.root)
        self.assertEqual(result.files, ["app.py"])
        self.assertIs(result.working_tree_clean, False)

    def test_git_unavailable_still_observes_files(self):
        (self.root / "plain.txt").touch()
        with patch("mr_moneybags.observation.subprocess.run", side_effect=FileNotFoundError):
            result = self.observe()

        self.assertIsNone(result.is_git_repository)
        self.assertIsNone(result.working_tree_clean)
        self.assertEqual(result.files, ["plain.txt"])
        self.assertIn("git_unavailable", result.errors)

    def test_git_timeout_is_reported_as_unknown(self):
        with patch("mr_moneybags.observation.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("git", 5)):
            result = self.observe()

        self.assertIsNone(result.is_git_repository)
        self.assertIsNone(result.working_tree_clean)
        self.assertIn("git_timeout", result.errors)

    def test_git_failure_is_not_reported_as_non_repository(self):
        failure = subprocess.CompletedProcess([], 128, "", "fatal: permission denied")
        with patch("mr_moneybags.observation.subprocess.run", return_value=failure):
            result = self.observe()

        self.assertIsNone(result.is_git_repository)
        self.assertIn("git_repository_check_failed", result.errors)

    def test_git_status_warning_or_failure_leaves_cleanliness_unknown(self):
        self.create_commit()
        real_run = subprocess.run
        for returncode, error in ((0, "warning: unreadable ignore file"), (128, "fatal: denied")):
            with self.subTest(returncode=returncode):
                def run(arguments, **kwargs):
                    if "status" in arguments:
                        return subprocess.CompletedProcess(arguments, returncode, "", error)
                    return real_run(arguments, **kwargs)

                with patch("mr_moneybags.observation.subprocess.run", side_effect=run):
                    result = self.observe()

                self.assertIs(result.is_git_repository, True)
                self.assertIsNone(result.working_tree_clean)
                code = "git_status_warning" if returncode == 0 else "git_status_failed"
                self.assertIn(code, result.errors)

    def test_repository_environment_does_not_redirect_observation(self):
        self.create_commit()
        self.environment["GIT_DIR"] = str(self.root / "does-not-exist")
        self.environment["GIT_WORK_TREE"] = str(self.root / "elsewhere")

        result = self.observe()

        self.assertEqual(Path(result.git_root), self.root)
        self.assertIs(result.working_tree_clean, True)

    def test_bare_repository_has_no_working_tree(self):
        self.git("init", "--bare", "--initial-branch=main", "--template=")

        result = self.observe()

        self.assertIs(result.is_git_repository, True)
        self.assertIsNone(result.git_root)
        self.assertIsNone(result.working_tree_clean)
        self.assertIn("not_in_working_tree", result.errors)
        self.assertEqual(result.files, [])

    def test_git_internal_directory_is_not_scanned(self):
        self.create_commit()
        with chdir(self.root / ".git"), patch.dict(os.environ, self.environment, clear=True):
            result = observe_workspace()

        self.assertEqual(result.files, [])
        self.assertIn("not_in_working_tree", result.errors)

    def test_file_filters(self):
        for directory in (".git", ".venv", "venv", "__pycache__", ".pytest_cache",
                          ".mypy_cache", ".ruff_cache", "node_modules", "dist",
                          "build", "secrets", "package.egg-info"):
            (self.root / directory).mkdir()
            (self.root / directory / "ignored.txt").touch()
        for name in (".env", ".env.local", "private.key", "private.pem", "cache.pyc"):
            (self.root / name).touch()
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").touch()
        (self.root / ".gitignore").touch()
        (self.root / "README.md").touch()

        result = self.observe()

        self.assertEqual(result.files, [".gitignore", "README.md", "src/app.py"])
        self.assertFalse(result.files_truncated)

    def test_scan_file_limit(self):
        for number in range(5):
            (self.root / f"{number}.txt").touch()
        with patch("mr_moneybags.observation.MAX_FILES", 2):
            result = self.observe()

        self.assertEqual(len(result.files), 2)
        self.assertTrue(result.files_truncated)

    def test_scan_entry_limit_includes_filtered_entries(self):
        for number in range(5):
            (self.root / f"{number}.pyc").touch()
        with patch("mr_moneybags.observation.MAX_ENTRIES", 2):
            result = self.observe()

        self.assertEqual(result.files, [])
        self.assertTrue(result.files_truncated)

    def test_scan_depth_limit(self):
        directory = self.root / "a" / "b" / "c" / "d"
        directory.mkdir(parents=True)
        (directory / "too_deep.txt").touch()
        (directory.parent / "visible.txt").touch()

        result = self.observe()

        self.assertEqual(result.files, ["a/b/c/visible.txt"])
        self.assertTrue(result.files_truncated)

    def test_symlink_does_not_escape_workspace(self):
        with TemporaryDirectory() as outside:
            (Path(outside) / "outside.txt").touch()
            link = self.root / "link"
            if os.name == "nt":
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(link), outside],
                    check=True, capture_output=True, timeout=10,
                )
            else:
                link.symlink_to(outside, target_is_directory=True)
            try:
                self.assertEqual(self.observe().files, [])
            finally:
                if os.name == "nt":
                    os.rmdir(link)
                else:
                    link.unlink()

    def test_observation_does_not_modify_workspace_or_git_index(self):
        self.create_commit()
        (self.root / "tracked.txt").write_text("changed\n", encoding="utf-8")
        before = self.snapshot()

        self.observe()

        self.assertEqual(self.snapshot(), before)

    def test_scanner_does_not_open_file_contents(self):
        (self.root / "README.md").write_text("Do not interpret this file.", encoding="utf-8")
        with patch.object(Path, "open", side_effect=AssertionError("File content read")):
            result = self.observe()

        self.assertEqual(result.files, ["README.md"])

    def test_scan_permission_error_is_reported(self):
        with patch("mr_moneybags.observation.os.scandir", side_effect=PermissionError):
            result = self.observe()

        self.assertEqual(result.files, [])
        self.assertTrue(result.files_truncated)
        self.assertIn("directory_unreadable", result.errors)
