import hashlib
import os
from pathlib import Path, PurePosixPath
import stat

from mr_moneybags.context.models import SourceArtifact
from mr_moneybags.observation import WorkspaceObservation


MAX_SOURCE_BYTES = 32 * 1024
MAX_TOTAL_BYTES = 96 * 1024
MAX_SOURCE_FILES = 8
MAX_ENTRY_FILES = 2
PROBE_BYTES = 512
SOURCE_NAMES = (
    "pyproject.toml", "readme.md", "project.md", "package.json", "requirements.txt",
    "cargo.toml", "go.mod", "pom.xml", "build.gradle", "makefile", "agents.md",
)
EXCLUDED_PARTS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".cache", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox", ".nox", "node_modules", "dist", "build",
    "target", "out", "vendor", "coverage", "htmlcov", ".gradle", ".next", ".nuxt",
}
ENTRY_NAMES = {"__main__.py", "main.py", "app.py", "manage.py"}


def _blocked(part: str) -> bool:
    name = part.casefold()
    return (name in EXCLUDED_PARTS or name == ".env"
            or name.startswith((".env.", "credentials", "secrets"))
            or name.endswith((".pem", ".key", ".egg-info")))


def _select_sources(observation: WorkspaceObservation) -> list[str]:
    manifests = {}
    entries = set()
    for name in observation.files[:200]:
        if "\\" in name or ":" in name:
            continue
        parts = name.split("/")
        if any(part in ("", ".", "..") or _blocked(part) for part in parts):
            continue
        if len(parts) == 1 and name.casefold() in SOURCE_NAMES:
            manifests.setdefault(name.casefold(), name)
        elif (len(parts) <= 4 and parts[-1] in ENTRY_NAMES
              and all(part.isidentifier() for part in parts[:-1])):
            entries.add(name)
    selected = [manifests[name] for name in SOURCE_NAMES if name in manifests]
    selected.extend(sorted(entries, key=lambda name: (PurePosixPath(name).name != "__main__.py", name))[:MAX_ENTRY_FILES])
    return selected


def _checked_path(root: Path, relative: str) -> tuple[Path, os.stat_result]:
    path = Path(root.anchor)
    for part in (None, *root.parts[1:], *PurePosixPath(relative).parts):
        if part is not None:
            path = path / part
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_reparse_tag", 0):
            raise ValueError("source_link_rejected")
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("source_not_regular")
    if metadata.st_nlink > 1:
        raise ValueError("source_hardlink_rejected")
    return path, metadata


def _signature(metadata: os.stat_result) -> tuple[int, int, int, int]:
    return metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns


def _binary(data: bytes) -> bool:
    return (data.startswith((b"%PDF-", b"PK\x03\x04", b"\x7fELF", b"\x89PNG", b"GIF87a", b"GIF89a"))
            or any(byte < 9 or 13 < byte < 32 for byte in data))


def read_sources(observation: WorkspaceObservation) -> tuple[list[SourceArtifact], dict[str, str], list[str], int]:
    artifacts = []
    evidence = {}
    warnings = []
    bytes_read = 0
    root = Path(observation.cwd)
    if not root.is_absolute() or any(_blocked(part) for part in root.parts):
        return artifacts, evidence, ["workspace_path_rejected"], bytes_read
    if observation.files_truncated or len(observation.files) > 200:
        warnings.append("observation_file_list_incomplete")
    candidates = _select_sources(observation)
    if len(candidates) > MAX_SOURCE_FILES:
        warnings.append("source_count_limit")
    for relative in candidates[:MAX_SOURCE_FILES]:
        try:
            path, metadata = _checked_path(root, relative)
            if metadata.st_size > MAX_SOURCE_BYTES:
                raise ValueError("file_size_limit")
            if metadata.st_size > MAX_TOTAL_BYTES - bytes_read:
                raise ValueError("total_size_limit")
            flags = (os.O_RDONLY | getattr(os, "O_BINARY", 0)
                     | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
            with os.fdopen(os.open(path, flags), "rb", buffering=0) as stream:
                if _signature(os.fstat(stream.fileno())) != _signature(metadata):
                    raise ValueError("source_changed")
                data = stream.read(min(metadata.st_size, PROBE_BYTES))
                bytes_read += len(data)
                if _binary(data):
                    raise ValueError("binary_source_rejected")
                remainder = stream.read(metadata.st_size - len(data))
                bytes_read += len(remainder)
                data += remainder
                if len(data) != metadata.st_size or _signature(os.fstat(stream.fileno())) != _signature(metadata):
                    raise ValueError("source_changed")
            if _binary(data):
                raise ValueError("binary_source_rejected")
            text = data.decode("utf-8-sig")
            artifacts.append(SourceArtifact(relative, hashlib.sha256(data).hexdigest(), len(data)))
            evidence[relative] = text
        except UnicodeDecodeError:
            warnings.append(f"invalid_utf8:{relative}")
        except ValueError as error:
            warnings.append(f"{error}:{relative}")
        except OSError:
            warnings.append(f"source_unreadable:{relative}")
    return artifacts, evidence, warnings, bytes_read
