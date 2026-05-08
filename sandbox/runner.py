"""
RPC dispatcher that runs inside the Docker container.
Called by the host orchestrator via: python3 /agent/runner.py '<json>'
"""

import json
import sys

from harness.tools.impl import TOOLS


if __name__ == "__main__":
    try:
        data = json.loads(sys.argv[1])
        tool_name = data["tool"]
        args = data.get("args", {})
        fn = TOOLS.get(tool_name)
        if fn is None:
            raise ValueError(f"Unknown tool: {tool_name!r}")
        print(json.dumps({"ok": True, "result": fn(args)}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
