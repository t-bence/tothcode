# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
uv venv && uv pip install -e .
export OPENROUTER_API_KEY=sk-or-...
```

Docker Desktop must be running. The sandbox image is built automatically on first `agent` invocation.

## Running

```bash
source .venv/bin/activate
agent "your task here"
agent --workspace ./my-project --model openai/gpt-4o "fix the bug in main.py"
```

Default model: `anthropic/claude-opus-4-5` via OpenRouter.

## Architecture

Two processes talk to each other, separated by a Docker boundary:

**Host side (`harness/`)** — runs on your machine, never touches the workspace files directly:
- `cli.py` — Typer entry point; owns sandbox lifetime (`start` / `stop` around the session)
- `agent.py` — the agentic loop; calls OpenRouter, dispatches tool calls, renders output via Rich
- `sandbox.py` — wraps `docker-py`; builds the image, starts the container, calls `container.exec_run()` per tool call
- `hitl.py` — human-in-the-loop gate; auto-approves read-only tools, prompts for everything else
- `history.py` — conversation history with a sliding-window trim (keeps first message + last 30)
- `tools/models.py` — Pydantic models for every tool's input arguments (single source of truth)
- `tools/registry.py` — derives OpenAI-compatible JSON schemas from the Pydantic models via `model_json_schema()`

**Sandbox side (`sandbox/runner.py`)** — runs inside the Docker container, has no network access:
- Invoked as `python3 /agent/runner.py '<json>'` for each tool call
- Accepts `{"tool": "<name>", "args": {...}}` on `sys.argv[1]`, prints `{"ok": bool, "result"/"error": ...}` to stdout
- `_safe_path()` resolves and validates all paths stay inside `/workspace`

**Communication flow:**
1. LLM returns a tool call JSON → `agent.py` validates args with Pydantic → `hitl.gate()` → `sandbox.call()` → `runner.py` → result back to LLM

## Adding a tool

1. Add a Pydantic model to `harness/tools/models.py`
2. Register it in `harness/tools/registry.py` (`_REGISTRY` dict, third field is `read_only` bool)
3. Implement the function in `sandbox/runner.py` and add it to `TOOLS`
4. Rebuild the Docker image (happens automatically on next `agent` run)

Read-only tools (flagged `True` in registry) are auto-approved by the HITL gate; write/exec tools require explicit user confirmation.

## Key constraints

- The sandbox container runs with `--network none`, `--cap-drop=ALL`, `--memory=512m`, `1 CPU`. Tools that need network access cannot work as-is.
- `run_bash` has a 60-second timeout per command.
- The agent loop stops after 30 iterations regardless of task completion.
- History trim always preserves `messages[0]` (the original user request) to keep the agent on-task.
- OpenRouter is used with the `openai` Python SDK (`base_url="https://openrouter.ai/api/v1"`). The `anthropic` SDK is not used.
