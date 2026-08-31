import ast
import json
from pathlib import PurePosixPath
import re
import shlex
import tomllib

from mr_moneybags.context.models import ContextConflict, DerivedClaim, ProjectContext
from mr_moneybags.context.sources import read_sources
from mr_moneybags.observation import WorkspaceObservation


PYTHON_REQUIREMENT = re.compile(
    r"\bPython\s*(>=|<=|==|~=|>|<)?\s*(\d+\.\d+(?:\.\d+)?)(\+)?"
    r"(\s*(?:或更高版本|及以上|or later|or newer|or higher))?", re.IGNORECASE,
)


def _add(claims: list[DerivedClaim], value: object, source: str) -> None:
    if not isinstance(value, str) or not value.strip():
        return
    value = value.strip()
    for claim in claims:
        if claim.value == value:
            if source not in claim.sources:
                claim.sources.append(source)
            return
    claims.append(DerivedClaim(value, [source]))


def _resolve(context: ProjectContext, field: str, claims: list[DerivedClaim]) -> DerivedClaim | None:
    if len(claims) == 1:
        return claims[0]
    if len(claims) > 1:
        context.conflicts.append(ContextConflict(field, claims))
    return None


def _command(context: ProjectContext, command: str, source: str) -> None:
    try:
        words = shlex.split(command)
    except ValueError:
        return
    if not words:
        return
    if words[0] in {"python", "python3", "py"}:
        if len(words) >= 3 and words[1] == "-m":
            if words[2] in {"unittest", "pytest"}:
                _add(context.test_commands, command, source)
            elif words[2] not in {"pip", "venv", "build", "compileall"}:
                _add(context.entry_points, command, source)
        elif len(words) >= 2 and words[1].endswith(".py"):
            _add(context.entry_points, command, source)
    elif words[0] == "pytest" or words[:2] == ["npm", "test"] or words[:3] == ["npm", "run", "test"]:
        _add(context.test_commands, command, source)
    elif words[:2] == ["npm", "start"] or words[:3] in (["npm", "run", "start"], ["npm", "run", "dev"]):
        _add(context.entry_points, command, source)


def _markdown(context: ProjectContext, text: str, source: str) -> tuple[str | None, str | None]:
    title = None
    summary = None
    fence = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("```"):
            fence = line[3:].strip().casefold() if fence is None else None
            continue
        if fence is not None:
            if fence in {"", "sh", "bash", "shell", "powershell", "ps1", "console", "text"}:
                _command(context, line.removeprefix("$ "), source)
            continue
        for command in re.findall(r"(?<!`)`([^`\n]+)`(?!`)", line):
            _command(context, command, source)
        for match in PYTHON_REQUIREMENT.finditer(line):
            operator, version, plus, higher = match.groups()
            requirement = (operator or (">=" if plus or higher else "")) + version
            _add(context.python_requirements, requirement, source)
        if title is None and line.startswith("# "):
            title = line[2:].strip()
        elif summary is None and line and not line.startswith(("#", "-", "*", "|", ">", "`")):
            summary = line
    return title, summary


def _metadata(context: ProjectContext, path: str, text: str,
              names: list[DerivedClaim], summaries: list[DerivedClaim]) -> None:
    try:
        document = json.loads(text) if path.casefold() == "package.json" else tomllib.loads(text)
    except (ValueError, RecursionError):
        context.warnings.append(f"invalid_metadata:{path}")
        return
    if not isinstance(document, dict):
        context.warnings.append(f"invalid_metadata:{path}")
        return
    if path.casefold() == "pyproject.toml":
        project = document.get("project")
        if not isinstance(project, dict):
            return
        if isinstance(project.get("name"), str) or isinstance(project.get("requires-python"), str):
            _add(context.detected_technologies, "Python", path)
        _add(context.python_requirements, project.get("requires-python"), path)
        scripts = project.get("scripts", {})
        if isinstance(scripts, dict):
            for name, target in scripts.items():
                if isinstance(target, str):
                    _add(context.entry_points, name, path)
    else:
        project = document
        if isinstance(project.get("name"), str) or isinstance(project.get("scripts"), dict):
            _add(context.detected_technologies, "Node.js", path)
        scripts = project.get("scripts", {})
        if isinstance(scripts, dict):
            for name in ("test", "start", "dev"):
                if isinstance(scripts.get(name), str):
                    claims = context.test_commands if name == "test" else context.entry_points
                    _add(claims, f"npm run {name}", path)
    _add(names, project.get("name"), path)
    _add(summaries, project.get("description"), path)


def build_project_context(observation: WorkspaceObservation) -> ProjectContext:
    context = ProjectContext()
    context.sources, evidence, context.warnings, context.bytes_read = read_sources(observation)
    context.warnings.append("source_declarations_are_unverified")
    names = []
    summaries = []
    readme_title = None
    readme_summary = None
    readme_path = None
    for path, text in evidence.items():
        _add(context.important_files, path, path)
        lower = path.casefold()
        if lower in {"pyproject.toml", "package.json"}:
            _metadata(context, path, text, names, summaries)
        elif lower.endswith(".md"):
            title, summary = _markdown(context, text, path)
            if lower == "readme.md":
                readme_title, readme_summary, readme_path = title, summary, path
        elif lower.endswith(".py"):
            try:
                ast.parse(text, filename=path)
            except (SyntaxError, ValueError, RecursionError):
                context.warnings.append(f"invalid_python_source:{path}")
                continue
            _add(context.detected_technologies, "Python", path)
            parts = PurePosixPath(path).parts
            command = f"python -m {'.'.join(parts[:-1])}" if parts[-1] == "__main__.py" and len(parts) > 1 else f"python {path}"
            _add(context.entry_points, command, path)
        elif lower == "requirements.txt" and any(
            re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]*", line.strip()) for line in text.splitlines()
        ):
            _add(context.detected_technologies, "Python", path)
    if not names and readme_title:
        _add(names, readme_title, readme_path)
    if not summaries and readme_summary:
        _add(summaries, readme_summary, readme_path)
    context.project_name = _resolve(context, "project_name", names)
    context.project_summary = _resolve(context, "project_summary", summaries)
    if len(context.python_requirements) > 1:
        context.conflicts.append(ContextConflict("python_requirements", context.python_requirements.copy()))
    return context
