# SIDEKICK - Coding Agent

A lightweight terminal-based coding agent powered by the OpenAI API. It can read, write, and search files, list directories, and run shell commands in a scoped workspace — looping on tool calls until a task is complete. Includes a separate sandboxed executor/validator pair for safely running untrusted Python snippets.

## Features

- **Conversational CLI agent** (`agent.py`) that plans and executes multi-step coding tasks using OpenAI's function-calling API
- **Workspace-scoped file tools** — reads, writes, and lists are resolved against the working directory and rejected if they'd escape it
- **Shell command execution** with output capture, truncation, and a 60-second timeout
- **Text search across files** (`search_files`) with glob filtering and noise-directory skipping (`.git`, `node_modules`, `venv`, `__pycache__`)
- **Sandboxed Python executor** (`executor.py` + `validator.py`) that statically validates code with an AST walk before running it in a subprocess with a restricted environment and timeout

## Project structure

```
.
├── agent.py       # CLI agent loop, tool definitions, and tool execution
├── executor.py     # Runs validated Python code in an isolated subprocess
├── validator.py    # AST-based static checks that block risky imports/builtins
└── README.md
```

## How it works

1. `agent.py` sends the conversation history to the model along with a set of tool schemas (`read_file`, `write_file`, `list_files`, `run_command`).
2. The model responds with either a final answer or one or more tool calls.
3. Tool calls are dispatched through `execute_tool`, results are appended to the conversation, and the loop repeats until the model stops requesting tools.
4. `executor.py` is a standalone utility for running arbitrary Python snippets safely: it first passes the code through `validator.py`'s `SafetyValidator`, which walks the AST and rejects blocked imports (`os`, `subprocess`, `sys`, etc.) and blocked builtins (`eval`, `exec`, `open`, etc.). Only code that passes validation is written to a temp file and executed in a subprocess with a minimal environment and a 10-second timeout.

## Requirements

- Python 3.9+
- An OpenAI API key with access to the configured model
- `openai` Python package

## Installation

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
pip install openai
export OPENAI_API_KEY="sk-..."
```

## Usage

```bash
python agent.py
```

```
welcome
Commands: 'quit' to exit, 'clear' to reset conversation

You: list the files in the src directory and summarize what main.py does

Agent:
Using tool: list_files
Using tool: read_file
...
```

Type `clear` to reset the conversation history, or `quit` to exit.

## Available tools

| Tool | Description |
|---|---|
| `read_file` | Read the contents of a file in the workspace |
| `write_file` | Create or overwrite a file with given content |
| `list_files` | List files and directories at a given path |
| `run_command` | Execute a shell command in the workspace and return its output |

## Configuration

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Required by the `openai` client |
| `MODEL` (in `agent.py`) | Change the `MODEL` constant to switch models |

## Security notes

Please read this before using the agent on anything you care about:

- **`run_command` grants full shell access** within the working directory's context. There is no allowlist or sandboxing on shell commands themselves — treat this the same as giving the model a terminal. Only run it in a disposable environment or container, and review commands if you add any confirmation step.
- **The file tools are workspace-scoped, not fully sandboxed.** `resolve_workspace_path` blocks path traversal outside the workspace root, but it doesn't stop the agent from overwriting existing files or reading sensitive files that happen to live inside the workspace.
- **The Python validator is a blocklist, not a true sandbox.** `SafetyValidator` catches obvious risky imports and builtins via static AST analysis, but blocklists are inherently bypassable (e.g. dynamic attribute access, indirect references, or import tricks not covered by the list). Don't rely on it to run genuinely untrusted or adversarial code — it's best suited to catching accidental misuse, not malicious input.

## Known limitations

- `search_files` is implemented in `agent.py` but not yet registered in `TOOLS` or wired into `execute_tool`, so the model can't call it directly today.
- Tool errors are caught and returned as strings rather than raised, which keeps the agent loop alive but can make failures easy to miss in the transcript.

## Contributing

Issues and pull requests are welcome. If you extend the sandbox, please keep the security notes above up to date.

## License

Add a license of your choice (MIT is a common default for small tooling like this).
