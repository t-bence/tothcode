import sys
from pathlib import Path

from . import ui


class Sandbox:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    def start(self) -> None:
        from harness.tools.impl import configure
        configure(self.workspace)

        try:
            from nono_py import CapabilitySet, AccessMode, apply, is_supported
        except ImportError:
            ui.info("nono-py not installed — running without kernel sandbox.")
            ui.sandbox_ready("no-sandbox")
            return

        if not is_supported():
            ui.info("nono sandbox not supported on this platform — running without isolation.")
            ui.sandbox_ready("no-sandbox")
            return

        caps = CapabilitySet()
        caps.allow_path(str(self.workspace), AccessMode.READ_WRITE)
        caps.allow_path("/", AccessMode.READ)
        apply(caps)

        ui.sandbox_ready("nono")

    def call(self, tool_name: str, args: dict) -> dict:
        from harness.tools.impl import TOOLS
        try:
            result = TOOLS[tool_name](args)
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def stop(self) -> None:
        pass
