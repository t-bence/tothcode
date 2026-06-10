from pathlib import Path

import typer

from . import ui
from .agent import Agent
from .sandbox import Sandbox

app = typer.Typer(help="CLI coding agent harness.")

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
_STATE_FILE = Path.home() / ".config" / "tothcode" / "last_workspace"


def _load_last() -> str | None:
    try:
        return _STATE_FILE.read_text().strip() or None
    except FileNotFoundError:
        return None


def _save_last(path: Path) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(str(path))


@app.command()
def main(
    model: str = typer.Option(
        DEFAULT_MODEL,
        "--model",
        "-m",
        help="OpenRouter model ID (e.g. anthropic/claude-opus-4-5, openai/gpt-4o)",
    ),
) -> None:
    last = _load_last()
    work_dir = typer.prompt("Work directory", default=last or "")
    workspace = Path(work_dir).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    _save_last(workspace)
    sandbox = Sandbox(workspace)
    try:
        sandbox.start()
        Agent(sandbox, model).run_session()
    except KeyboardInterrupt:
        ui.info("Interrupted.")
    except Exception as e:
        ui.error(str(e))
        raise typer.Exit(1)
    finally:
        sandbox.stop()
