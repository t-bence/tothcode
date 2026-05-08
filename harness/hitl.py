from . import ui
from .tools.registry import READ_ONLY_TOOLS


def gate(tool_name: str, args: dict) -> bool:
    if tool_name in READ_ONLY_TOOLS:
        ui.tool_auto_approved(tool_name, args)
        return True
    ui.tool_request(tool_name, args)
    return ui.prompt_allow_tool()
