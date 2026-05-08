import json
import os
from pathlib import Path

from openai import OpenAI

from . import ui
from .history import ConversationHistory
from .hitl import gate
from .sandbox import Sandbox
from .tools.registry import get_openai_schemas, is_known, validate_args

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
SYSTEM_PROMPT = (_PROMPTS_DIR / "system.md").read_text()
COMPACT_PROMPT = (_PROMPTS_DIR / "compact.md").read_text()

MAX_ITERATIONS = 30

COMMANDS = {
    "/exit": "Exit the session",
    "/quit": "Exit the session",
    "/clear": "Clear conversation history",
    "/compact": "Summarize history into a single context message",
    "/help": "Show available commands",
}


class Agent:
    def __init__(self, sandbox: Sandbox, model: str) -> None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

        self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        self.sandbox = sandbox
        self.model = model
        self.history = ConversationHistory()
        self.system_prompt = self._get_system_prompt()

    def run_session(self) -> None:
        ui.welcome(self.model)

        while True:
            user_input = ui.prompt_user()
            if user_input is None:
                break

            if user_input.startswith("/"):
                should_exit = self._handle_command(user_input)
                if should_exit:
                    break
                continue

            self.history.add_user(user_input)
            self._run_turn()

    # --- commands ---

    def _handle_command(self, cmd: str) -> bool:
        """Returns True if the session should exit."""
        if cmd in ("/exit", "/quit"):
            return True
        if cmd == "/clear":
            self.history.clear_messages()
            ui.info("History cleared.")
        elif cmd == "/compact":
            self._compact()
        elif cmd == "/help":
            ui.commands(COMMANDS)
        else:
            ui.info("Unknown command. Type /help for available commands.")
        return False

    def _compact(self) -> None:
        ui.info("Compacting history…")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.history.messages
            + [{"role": "user", "content": COMPACT_PROMPT}],
        )
        summary = response.choices[0].message.content
        self.history.compact(summary)
        ui.info("History compacted.")

    # --- agentic loop ---

    def _run_turn(self) -> None:
        for _ in range(MAX_ITERATIONS):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": self.system_prompt}]
                + self.history.messages,
                tools=get_openai_schemas(),
                tool_choice="auto",
            )
            message = response.choices[0].message
            self.history.add_assistant(_message_to_dict(message))

            if not message.tool_calls:
                if message.content:
                    ui.assistant_message(message.content)
                break

            tool_results = [self._dispatch(tc) for tc in message.tool_calls]
            self.history.add_tool_results(tool_results)
        else:
            ui.iteration_limit()

    def _dispatch(self, tc) -> dict:
        name = tc.function.name
        raw_args = json.loads(tc.function.arguments)
        content = self._execute(name, raw_args)
        ui.tool_result(name, content, ok=not content.startswith("Error:"))
        return {"role": "tool", "tool_call_id": tc.id, "content": content}

    def _execute(self, name: str, raw_args: dict) -> str:
        if not is_known(name):
            return f"Error: unknown tool {name!r}"
        try:
            args = validate_args(name, raw_args)
        except Exception as e:
            return f"Error: invalid arguments — {e}"
        if not gate(name, args):
            return "Error: tool call denied by user."
        return self._call_tool(name, args)

    def _call_tool(self, name: str, args: dict[str, str]) -> str:
        result = self.sandbox.call(name, args)
        return (
            result["result"]
            if result.get("ok")
            else f"Error: {result.get('error', 'unknown error')}"
        )

    def _get_system_prompt(self) -> str:
        """Set up system prompt with TOTH.md and skills

        Returns
        -------
        str
            System prompt augmented with contents of the TOTH.md file and skills
        """
        prompt_items = [SYSTEM_PROMPT]

        markdown = self._call_tool("read_file", {"path": "TOTH.md"})
        if markdown:
            ui.info("Read TOTH.md")
            prompt_items.append("Workspace instructions:")
            prompt_items.append(markdown)

        skills = self._call_tool("list_skills", {})
        if skills:
            ui.info(f"Found {len(skills.splitlines())} skills")
            prompt_items.append("You have access to the following skills.")
            prompt_items.append(
                "You can use them by using the use_skill tool with the skill name as argument."
            )
            prompt_items.append(skills)

        return "\n".join(prompt_items)


def _message_to_dict(message) -> dict:
    d: dict = {"role": "assistant"}
    if message.content:
        d["content"] = message.content
    if message.tool_calls:
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in message.tool_calls
        ]
    return d
