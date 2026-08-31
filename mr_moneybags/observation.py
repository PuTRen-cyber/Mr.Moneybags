from dataclasses import dataclass, field
import os
from pathlib import Path
import stat
import subprocess


MAX_FILES = 200
MAX_ENTRIES = 2_000
MAX_DEPTH = 3
GIT_TIMEOUT_SECONDS = 5
EXCLUDED_NAMES = {
    ".git", ".venv", "venv", "__pycache__", ".cache", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox", ".nox", "node_modules", "dist",
    "build", "secrets", ".env",
}


@dataclass
class WorkspaceObservation:
    cwd: str
    is_git_repository: bool | None = None
    is_inside_work_tree: bool | None = None
    git_root: str | None = None
    branch: str | None = None
    head_commit: str | None = None
    working_tree_clean: bool | None = None
    files: list[str] = field(default_factory=list)
    trust_level: str = field(default="Tier 0 — Direct Evidence", init=False)
    files_truncated: bool = False
    errors: list[str] = field(default_factory=list)


def _scan_files(root: Path) -> tuple[list[str], bool, list[str]]:
    files = []
    errors = []
    examined = 0
    truncated = False

    def visit(directory: Path, depth: int) -> None:
        nonlocal examined, truncated
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if examined >= MAX_ENTRIES or len(files) >= MAX_FILES:
                        truncated = True
                        return
                    examined += 1
                    name = entry.name.casefold()
                    if (name in EXCLUDED_NAMES or name.startswith(".env.")
                            or name.endswith((".egg-info", ".pyc", ".pyo", ".key", ".pem"))):
                        continue
                    try:
                        metadata = entry.stat(follow_symlinks=False)
                        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_reparse_tag", 0):
                            continue
                        path = Path(entry.path)
                        if stat.S_ISDIR(metadata.st_mode):
                            if depth >= MAX_DEPTH:
                                truncated = True
                            else:
                                visit(path, depth + 1)
                        elif stat.S_ISREG(metadata.st_mode):
                            files.append(path.relative_to(root).as_posix())
                    except OSError:
                        errors.append("file_entry_unreadable")
                        truncated = True
        except OSError:
            errors.append("directory_unreadable")
            truncated = True

    visit(root, 0)
    return sorted(files), truncated, sorted(set(errors))


def _run_git(cwd: Path, *arguments: str) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    for name in (
        "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE",
    ):
        environment.pop(name, None)
    environment.update({"LC_ALL": "C", "LANG": "C", "GIT_OPTIONAL_LOCKS": "0"})
    return subprocess.run(
        ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", *arguments],
        cwd=cwd, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT_SECONDS,
    )


def _observe_git(cwd: Path, observation: WorkspaceObservation) -> None:
    try:
        repository = _run_git(cwd, "rev-parse", "--is-inside-work-tree")
        if repository.returncode:
            if "not a git repository" in repository.stderr:
                observation.is_git_repository = False
            else:
                observation.errors.append("git_repository_check_failed")
            return
        observation.is_git_repository = True
        observation.is_inside_work_tree = repository.stdout.strip() == "true"
        if not observation.is_inside_work_tree:
            observation.errors.append("not_in_working_tree")
            return

        root = _run_git(cwd, "rev-parse", "--show-toplevel")
        if root.returncode == 0:
            observation.git_root = root.stdout.strip()
        else:
            observation.errors.append("git_root_failed")

        branch = _run_git(cwd, "symbolic-ref", "--quiet", "--short", "HEAD")
        if branch.returncode == 0:
            observation.branch = branch.stdout.strip()
        elif branch.returncode != 1:
            observation.errors.append("git_branch_failed")

        head = _run_git(cwd, "rev-parse", "--verify", "--quiet", "HEAD^{commit}")
        if head.returncode == 0:
            observation.head_commit = head.stdout.strip()
        elif head.returncode != 1:
            observation.errors.append("git_head_failed")

        status = _run_git(cwd, "status", "--porcelain=v1", "--untracked-files=normal",
                          "--ignore-submodules=none")
        if status.returncode:
            observation.errors.append("git_status_failed")
        elif status.stderr:
            observation.errors.append("git_status_warning")
        else:
            observation.working_tree_clean = not bool(status.stdout)
    except FileNotFoundError:
        observation.errors.append("git_unavailable")
    except subprocess.TimeoutExpired:
        observation.errors.append("git_timeout")
    except OSError:
        observation.errors.append("git_unreadable")


def observe_workspace() -> WorkspaceObservation:
    cwd = Path.cwd()
    observation = WorkspaceObservation(cwd=str(cwd))
    _observe_git(cwd, observation)
    if (observation.is_inside_work_tree is not False
            and not any(part.casefold() == ".git" for part in cwd.parts)):
        files, truncated, errors = _scan_files(cwd)
        observation.files = files
        observation.files_truncated = truncated
        observation.errors.extend(errors)
    return observation
