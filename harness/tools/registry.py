from functools import lru_cache
from typing import NamedTuple

from pydantic import BaseModel

from .models import (
    EditFileInput,
    GrepFilesInput,
    ListDirInput,
    ListSkillsInput,
    ReadFileInput,
    RunBashInput,
    UseSkillInput,
    WriteFileInput,
)


class ToolEntry(NamedTuple):
    model: type[BaseModel]
    description: str
    read_only: bool


_REGISTRY: dict[str, ToolEntry] = {
    "read_file": ToolEntry(
        ReadFileInput, "Read the full contents of a file in the workspace.", True
    ),
    "write_file": ToolEntry(
        WriteFileInput,
        "Write content to a file, creating it if it doesn't exist.",
        False,
    ),
    "edit_file": ToolEntry(
        EditFileInput,
        "Replace an exact block of text in a file. Prefer this over write_file for targeted edits.",
        False,
    ),
    "list_dir": ToolEntry(
        ListDirInput,
        "List the directory tree of the workspace or a subdirectory.",
        True,
    ),
    "run_bash": ToolEntry(
        RunBashInput, "Run a shell command inside the sandboxed workspace.", False
    ),
    "grep_files": ToolEntry(
        GrepFilesInput,
        "Search for a regex pattern across files in the workspace.",
        True,
    ),
    "list_skills": ToolEntry(ListSkillsInput, "List available agent skills", True),
    "use_skill": ToolEntry(
        UseSkillInput,
        "Load and apply a skill by name. Skills provide specialized instructions for specific tasks.",
        True,
    ),
}

READ_ONLY_TOOLS: frozenset[str] = frozenset(
    name for name, entry in _REGISTRY.items() if entry.read_only
)


@lru_cache(maxsize=None)
def get_openai_schemas() -> list[dict]:
    schemas = []
    for name, entry in _REGISTRY.items():
        schema = entry.model.model_json_schema()
        schema.pop("title", None)
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": entry.description,
                    "parameters": schema,
                },
            }
        )
    return schemas


def validate_args(tool_name: str, raw_args: dict) -> dict:
    return _REGISTRY[tool_name].model.model_validate(raw_args).model_dump()


def is_known(tool_name: str) -> bool:
    return tool_name in _REGISTRY
