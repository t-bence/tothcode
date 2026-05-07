from rich.panel import Panel
from rich.prompt import Confirm

from .console import console
from .tools.registry import READ_ONLY_TOOLS
from .utils import truncate


def gate(tool_name: str, args: dict) -> bool:
    if tool_name in READ_ONLY_TOOLS:
        _print_auto_approved(tool_name, args)
        return True
    _print_tool_call(tool_name, args)
    try:
        return Confirm.ask("  Allow?", default=True)
    except EOFError:
        console.print("[yellow]  No TTY — defaulting to deny.[/]")
        return False


def _print_auto_approved(tool_name: str, args: dict) -> None:
    arg_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
    console.print(f"[dim]  → {tool_name}({arg_str})[/]")


def _print_tool_call(tool_name: str, args: dict) -> None:
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
