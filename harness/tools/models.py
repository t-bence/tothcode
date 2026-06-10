"""
Pydantic models for all tool inputs.
Single source of truth — used to auto-generate OpenAI tool schemas.
"""

from pydantic import BaseModel, Field


class ReadFileInput(BaseModel):
    path: str = Field(..., description="Relative path to the file inside the workspace")


class WriteFileInput(BaseModel):
    path: str = Field(..., description="Relative path to the file inside the workspace")
    content: str = Field(..., description="Full content to write to the file")


class EditFileInput(BaseModel):
    path: str = Field(..., description="Relative path to the file to edit")
    search_block: str = Field(
        ...,
        description="The exact block of text to find and replace. Must match character-for-character including whitespace and indentation.",
    )
    replace_block: str = Field(
        ..., description="The new text to put in place of search_block"
    )


class ListDirInput(BaseModel):
    path: str = Field(
        ".",
        description="Relative path to the directory to list (default: workspace root)",
    )


class RunBashInput(BaseModel):
    command: str = Field(
        ...,
        description="Shell command to run in the workspace. Must start with 'uv' or 'python'. Chain commands with && to preserve context across steps.",
    )


class GrepFilesInput(BaseModel):
    pattern: str = Field(..., description="Regex pattern to search for")
    path: str = Field(
        ".", description="Directory or file to search (default: entire workspace)"
    )


class ListSkillsInput(BaseModel):
    pass


class UseSkillInput(BaseModel):
    skill_name: str = Field(..., description="Name of the skill to load")
