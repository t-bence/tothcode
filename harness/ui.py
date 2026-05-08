"""
All Rich display logic lives here.
Logic modules (agent, hitl) call into this module and own no console.print calls.
"""

from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm

from .console import console, err_console
from .utils import truncate


def welcome(model: str) -> None:
    lines = [
        f"[dim]Model: {model}",
        "/help for commands",
        "/compact to compact",
        "/clear to start a new session[/]",
    ]
    console.print(
        Panel(
            "\n".join(lines),
            title="[green]Welcome to TOTHCODE[/]",
            border_style="green",
        )
    )


def tool_auto_approved(tool_name: str, args: dict) -> None:
    arg_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
    console.print(f"[dim]  → {tool_name}({arg_str})[/]")


def tool_request(tool_name: str, args: dict) -> None:
    lines = [f"[bold yellow]{tool_name}[/]"]
    for key, value in args.items():
        if isinstance(value, str) and "\n" in value:
            lines.append(f"  [dim]{key}:[/]")
            lines.append(f"    [italic]{truncate(value, 400)}[/]")
        else:
            lines.append(f"  [dim]{key}:[/] {value!r}")
    console.print(
        Panel("\n".join(lines), title="[yellow]Tool request[/]", border_style="yellow")
    )


def tool_result(tool_name: str, content: str, ok: bool) -> None:
    color, label = ("green", "ok") if ok else ("red", "error")
    console.print(
        f"  [{color}][{label}][/] [dim]{tool_name}:[/] {truncate(content, 300)}"
    )


def assistant_message(content: str) -> None:
    console.print(Markdown(content))


def iteration_limit() -> None:
    console.print("[red]Reached iteration limit.[/]")


def info(msg: str) -> None:
    console.print(f"[dim]{msg}[/]")


def error(msg: str) -> None:
    console.print(f"[red]Error:[/] {msg}")


def commands(cmd_map: dict[str, str]) -> None:
    for cmd, desc in cmd_map.items():
        console.print(f"  [cyan]{cmd}[/]  {desc}")


def prompt_user() -> str | None:
    try:
        return console.input("\n[bold cyan]>[/] ").strip() or None
    except EOFError:
        return None


# --- sandbox status (written to stderr to stay off the agent output stream) ---


def sandbox_building(reason: str = "") -> None:
    msg = "[dim]Building sandbox image…[/]"
    if reason:
        msg += f" [yellow]({reason})[/]"
    err_console.print(msg)


def sandbox_reusing(short_hash: str) -> None:
    err_console.print(
        f"[dim]Reusing sandbox image[/] [green](runner hash: {short_hash})[/]"
    )


def sandbox_starting() -> None:
    err_console.print("[dim]Starting sandbox container…[/]")


def sandbox_ready(short_id: str) -> None:
    err_console.print(f"[green]Sandbox ready[/] [dim](id: {short_id})[/]")


def sandbox_stopped() -> None:
    err_console.print("[dim]Sandbox stopped.[/]")


def prompt_allow_tool() -> bool:
    try:
        return Confirm.ask("  Allow?", default=True)
    except EOFError:
        info("No TTY — defaulting to deny.")
        return False
