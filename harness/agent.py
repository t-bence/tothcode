import json
import os

from openai import OpenAI
from rich.markdown import Markdown
from rich.rule import Rule

from .console import console
from .history import ConversationHistory
from .hitl import gate
from .sandbox import Sandbox
from .tools.registry import get_openai_schemas, is_known, validate_args
from .utils import truncate

SYSTEM_PROMPT = """\
You are a coding agent with access to a sandboxed workspace.

Guidelines:
- Use list_dir and read_file first to understand the project before making changes.
- Prefer edit_file over write_file for targeted changes — it is safer and easier to review.
- edit_file requires an exact match of search_block (including whitespace and indentation).
- When running bash, chain dependent commands with && (e.g. cd src && python main.py).
- Keep tool calls focused — one logical action per call.
- If a tool returns an error, diagnose it before retrying.
"""

MAX_ITERATIONS = 30

COMMANDS = {
    "/exit": "Exit the session",
    "/quit": "Exit the session",
    "/clear": "Clear conversation history",
    "/help": "Show available commands",
}


def run_session(sandbox: Sandbox, model: str) -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    history = ConversationHistory()

    console.print(f"[dim]Model: {model} · /help for commands[/]")
    console.print(Rule(style="dim"))

    while True:
        try:
            user_input = console.input("\n[bold cyan]>[/] ").strip()
        except EOFError:
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            if user_input in ("/exit", "/quit"):
                break
            elif user_input == "/clear":
                history = ConversationHistory()
                console.print("[dim]History cleared.[/]")
            elif user_input == "/help":
                for cmd, desc in COMMANDS.items():
                    console.print(f"  [cyan]{cmd}[/]  {desc}")
            else:
                console.print(f"[yellow]Unknown command.[/] Type /help for available commands.")
            continue

        history.add_user(user_input)
        _run_turn(client, sandbox, history, model)


def _run_turn(client: OpenAI, sandbox: Sandbox, history: ConversationHistory, model: str) -> None:
    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history.messages,
            tools=get_openai_schemas(),
            tool_choice="auto",
        )
        message = response.choices[0].message
        history.add_assistant(_message_to_dict(message))

        if not message.tool_calls:
            if message.content:
                console.print(Markdown(message.content))
            break

        tool_results = [_dispatch(tc, sandbox) for tc in message.tool_calls]
        history.add_tool_results(tool_results)
    else:
        console.print("[red]Reached iteration limit.[/]")


def _dispatch(tc, sandbox: Sandbox) -> dict:
    name = tc.function.name
    raw_args = json.loads(tc.function.arguments)
    result_content = _execute(name, raw_args, sandbox)
    _print_result(name, result_content, ok=not result_content.startswith("Error:"))
    return {"role": "tool", "tool_call_id": tc.id, "content": result_content}


def _execute(name: str, raw_args: dict, sandbox: Sandbox) -> str:
    if not is_known(name):
        return f"Error: unknown tool {name!r}"
    try:
        args = validate_args(name, raw_args)
    except Exception as e:
        return f"Error: invalid arguments — {e}"
    if not gate(name, args):
        return "Error: tool call denied by user."
    result = sandbox.call(name, args)
    return result["result"] if result.get("ok") else f"Error: {result.get('error', 'unknown error')}"


def _message_to_dict(message) -> dict:
    d: dict = {"role": "assistant"}
    if message.content:
        d["content"] = message.content
    if message.tool_calls:
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in message.tool_calls
        ]
    return d


def _print_result(tool_name: str, content: str, ok: bool) -> None:
    color, label = ("green", "ok") if ok else ("red", "error")
    console.print(f"  [{color}][{label}][/] [dim]{tool_name}:[/] {truncate(content, 300)}")
