# tothcode

A CLI coding agent harness that runs an LLM-powered agent with all file and shell access confined to a Docker sandbox.

## Features

- **Docker-isolated sandbox** — the agent can only touch files inside a mounted workspace directory; no network access, no host filesystem access
- **Human-in-the-loop (HITL) gate** — read-only tools (file reads, directory listing, grep) are auto-approved; write and exec tools require explicit user confirmation
- **OpenRouter backend** — any model available on OpenRouter can be used via a single flag
- **Skill system** — drop markdown skill files into the workspace's `skills/` directory; the agent discovers and applies them automatically
- **Session commands** — `/clear`, `/compact`, `/help`, `/exit` available at any prompt
- **Conversation compaction** — `/compact` summarizes history into a single context message to stay within token limits

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- Docker Desktop (must be running)
- An [OpenRouter](https://openrouter.ai) API key

## Setup

```bash
uv venv && uv pip install -e .

# Required for OpenRouter models; not needed for Ollama
export OPENROUTER_API_KEY=sk-or-...
```

The Docker sandbox image is built automatically on the first `tothcode` invocation.

## Usage

```bash
# Start an interactive session against the default ./workspace directory
tothcode

# Use a specific project directory and model
tothcode --workspace ./my-project --model anthropic/claude-opus-4-5
tothcode -w ./my-project -m openai/gpt-4o

# Use a local Ollama model (prefix with ollama/)
tothcode --model ollama/llama3
tothcode --model ollama/mistral

# Custom Ollama host
tothcode --ollama-host http://192.168.1.10:11434 --model ollama/llama3
```

The provider is selected automatically from the model name: `ollama/<model>` routes to the local Ollama server; anything else routes to OpenRouter.

The agent then runs interactively. Type your task and press Enter. Available session commands:

| Command    | Description                                         |
|------------|-----------------------------------------------------|
| `/help`    | Show available commands                             |
| `/clear`   | Clear conversation history                          |
| `/compact` | Summarize history into a single context message     |
| `/exit`    | Exit the session (also `/quit` or Ctrl-C)           |

## Architecture

Two processes communicate across a Docker boundary:

```text
Host                          Docker container
────────────────────          ──────────────────────
cli.py                        sandbox/runner.py
  └─ agent.py  ──tool call──▶   executes tool
       └─ sandbox.py ◀──result── prints JSON result
```

**Host side (`harness/`)** — runs on your machine, never touches workspace files directly:

| File | Role |
| ---- | ---- |
| `cli.py` | Typer entry point; owns sandbox lifetime (`start`/`stop`) |
| `agent.py` | Agentic loop; calls OpenRouter, dispatches tool calls, renders output via Rich |
| `sandbox.py` | Wraps `docker-py`; builds image, starts container, calls `exec_run()` per tool call |
| `hitl.py` | HITL gate; auto-approves read-only tools, prompts for everything else |
| `history.py` | Conversation history with sliding-window trim (preserves first message + last 39) |
| `prompts/` | Markdown files for the system prompt and `/compact` prompt |
| `tools/models.py` | Pydantic models for every tool's input arguments (single source of truth for schemas) |
| `tools/registry.py` | Derives OpenAI-compatible JSON schemas from Pydantic models; tracks `read_only` flag |
| `tools/impl.py` | Tool implementations; also provides the `TOOLS` dict for the sandbox runner |

**Sandbox side (`sandbox/runner.py`)** — runs inside the Docker container with no network access:

- Invoked as `python3 /agent/runner.py '<json>'` for each tool call
- Accepts `{"tool": "<name>", "args": {...}}` on `sys.argv[1]`
- Prints `{"ok": bool, "result"/"error": ...}` to stdout
- All paths are validated to stay inside `/workspace`

**Communication flow:**

```text
LLM response → agent.py validates args → hitl.gate() → sandbox.call() → runner.py → result
```

## Available tools

| Tool | Read-only | Description |
| ---- | --------- | ----------- |
| `read_file` | yes | Read a file's full contents |
| `list_dir` | yes | List a directory tree |
| `grep_files` | yes | Search files with a regex pattern |
| `list_skills` | yes | List available skills |
| `use_skill` | yes | Load and apply a skill by name |
| `write_file` | no | Write (or create) a file |
| `edit_file` | no | Replace an exact text block in a file |
| `run_bash` | no | Run a shell command inside the sandbox |

## Adding a tool

1. Add a Pydantic model to [harness/tools/models.py](harness/tools/models.py)
2. Register it in [harness/tools/registry.py](harness/tools/registry.py) (`_REGISTRY` dict; third field is `read_only` bool)
3. Implement the function in [harness/tools/impl.py](harness/tools/impl.py) and add it to the `TOOLS` dict
4. Rebuild the Docker image (happens automatically on next `tothcode` run)

## Skills

Place markdown files in `skills/` inside the workspace. The agent loads them at session start via `list_skills` / `use_skill`. Skills provide specialized instructions for domain-specific tasks (e.g. a Django skill, a testing skill, a style guide).

## Key constraints

- The sandbox runs with `--network none`, `--cap-drop=ALL`, `--memory=512m`, `1 CPU`
- `run_bash` has a 60-second timeout per command
- The agent loop stops after 30 iterations per turn
- History trim always preserves `messages[0]` (the original user request) to keep the agent on-task
- OpenRouter is used with the `openai` Python SDK (`base_url="https://openrouter.ai/api/v1"`); the `anthropic` SDK is not used

## Default model

The default model is `deepseek/deepseek-v4-flash`. Override with `--model`.

## License

See [LICENSE](LICENSE).
