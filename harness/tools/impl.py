"""
Tool implementations for the sandbox.
Runs inside the Docker container — BASE is /workspace.
"""

import os
import subprocess
from pathlib import Path

BASE = Path("/workspace").resolve()


def _safe_path(path: str) -> Path:
    resolved = (BASE / path).resolve()
    resolved.relative_to(BASE)
    return resolved


def read_file(path: str) -> str:
    return _safe_path(path).read_text()


def write_file(path: str, content: str) -> str:
    full = _safe_path(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)
    return f"Written {path}"


def edit_file(path: str, search_block: str, replace_block: str) -> str:
    full = _safe_path(path)
    content = full.read_text()
    if search_block not in content:
        raise ValueError(
            f"search_block not found in {path}. Make sure it matches exactly including whitespace."
        )
    full.write_text(content.replace(search_block, replace_block, 1))
    return f"Successfully edited {path}"


def list_dir(path: str = ".") -> str:
    full = _safe_path(path)
    if not full.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")
    lines = []
    for root, dirs, files in os.walk(full):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        level = Path(root).relative_to(full).parts.__len__()
        indent = "  " * level
        rel = Path(root).relative_to(full)
        if str(rel) != ".":
            lines.append(f"{indent}{Path(root).name}/")
        for fname in sorted(files):
            lines.append(f"{'  ' * (level + 1)}{fname}")
    return "\n".join(lines) if lines else "(empty directory)"


def run_bash(command: str) -> str:
    result = subprocess.run(
        command,
        shell=True,
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=60,
    )
    out = result.stdout
    if result.stderr:
        out += f"\n[stderr]\n{result.stderr}"
    if result.returncode != 0:
        out += f"\n[exit code: {result.returncode}]"
    return out or "(no output)"


def grep_files(pattern: str, path: str = ".") -> str:
    full = _safe_path(path)
    result = subprocess.run(
        ["grep", "-rn", pattern, str(full)],
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip().replace(str(BASE) + "/", "")
    return output or f"No matches for {pattern!r}"


def list_skills() -> str:
    full = _safe_path(".agents")
    lines = []

    def _read_skill_head(path: Path) -> tuple[str, str]:
        name = ""
        desc = ""
        for line in path.read_text().splitlines():
            line_stripped = line.strip()
            if not name and line_stripped.startswith("name:"):
                name = line_stripped.replace("name:", "").strip()
            elif not desc and line_stripped.startswith("description:"):
                desc = line_stripped.replace("description:", "").strip()
            elif name and desc:
                break
        return name, desc

    for skill_file in full.glob("*/SKILL.md"):
        name, desc = _read_skill_head(skill_file)
        lines.append(f"{name}: {desc}")
    return "\n".join(lines)


def use_skill(skill_name: str) -> str:
    md_path = _safe_path(".agents") / skill_name / "SKILL.md"
    return md_path.read_text()


TOOLS = {
    "read_file": lambda a: read_file(**a),
    "write_file": lambda a: write_file(**a),
    "edit_file": lambda a: edit_file(**a),
    "list_dir": lambda a: list_dir(**a),
    "run_bash": lambda a: run_bash(**a),
    "grep_files": lambda a: grep_files(**a),
    "list_skills": lambda a: list_skills(**a),
    "use_skill": lambda a: use_skill(**a),
}

__all__ = ["TOOLS"]
