from pathlib import Path

import typer

from . import ui
from .agent import Agent
from .sandbox import Sandbox

app = typer.Typer(help="CLI coding agent harness with Docker sandbox isolation.")

DEFAULT_MODEL = "deepseek/deepseek-v4-pro"


@app.command()
def main(
    workspace: Path = typer.Option(
        Path("./workspace"),
        "--workspace",
        "-w",
        help="Project directory to mount into the sandbox",
    ),
    model: str = typer.Option(
        DEFAULT_MODEL,
        "--model",
        "-m",
        help="OpenRouter model ID (e.g. anthropic/claude-opus-4-5, openai/gpt-4o)",
    ),
) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    sandbox = Sandbox(workspace.resolve())
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
