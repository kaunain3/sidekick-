import subprocess
from pathlib import Path
from openai import OpenAI
import fnmatch
from pathlib import Path

client = OpenAI()

MODEL = "gpt-5"

SYSTEM_PROMPT = """You are a helpful coding assistant that can read, write, and manage files, and explain your actions.

You have access to the following tools:
- read_file: Read the contents of a file
- write_file: Write content to a file (creates or overwrites)
- list_files: List files in a directory

When given a task:
1. Think about what you need to do
2. Use tools to gather information or make changes
3. Continue until the task is complete
4. Explain what you did

Always be careful when writing files - make sure you understand the existing content first."""

TOOLS = [
    {
        "type": "function",
        "name": "read_file",
        "description": "Read the contents of a file at the given path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to read.",
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "write_file",
        "description": (
            "Write content to a file at the given path. Creates the file if it"
            " does not exist and overwrites it if it does."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to write.",
                },
                "content": {
                    "type": "string",
                    "description": (
                        "The complete content that should be written to the"
                        " file."
                    ),
                },
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_files",
        "description": "List files and directories at the given path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "The directory path to list. Use '.' for the project"
                        " root."
                    ),
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    }, 
    {
        "type": "function",
        "name": "run_command",
        "description": (
            "Execute a shell command in the project workspace and return its"
            " output."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                }
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "search_files",
        "description": (
            "Search for a text pattern (case-insensitive) across files in a"
            " directory, optionally filtered by a filename glob pattern."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory to search in.",
                },
                "pattern": {
                    "type": "string",
                    "description": "The text pattern to search for.",
                },
                "file_pattern": {
                    "type": "string",
                    "description": (
                        "Optional filename glob to filter which files are"
                        " searched, e.g. '*.py'."
                    ),
                },
            },
            "required": ["path", "pattern"],
            "additionalProperties": False,
        },
    },
]



WORKSPACE = Path.cwd().resolve()


def resolve_workspace_path(path: str) -> Path:
  resolved = (WORKSPACE / path).resolve()
  if resolved != WORKSPACE and WORKSPACE not in resolved.parents:
    raise ValueError(f"Path {path} is outside the workspace.")
  return resolved


def read_file(path: str) -> str:
  try:
    safe_path = resolve_workspace_path(path)
    with safe_path.open("r") as f:
      return f.read()
  except FileNotFoundError:
    return f"File {path} not found."
  except PermissionError:
    return f"Permission denied for file {path}."
  except Exception as e:
    return f"Error reading file: {e}"


def write_file(path: str, content: str) -> str:
  try:
    safe_path = resolve_workspace_path(path)
    safe_path.parent.mkdir(parents=True, exist_ok=True)

    with safe_path.open("w", encoding="utf-8") as f:
      f.write(content)

    return f"Successfully wrote to {path}."
  except PermissionError:
    return f"Permission denied for file {path}."
  except Exception as e:
    return f"Error writing file: {e}"


def list_files(path: str = ".") -> str:
  try:
    safe_path = resolve_workspace_path(path)

    if not safe_path.exists():
      return f"Directory {path} not found."

    if not safe_path.is_dir():
      return f"{path} is not a directory."

    entries = []
    for item in sorted(safe_path.iterdir()):
      if item.is_dir():
        entries.append(f"[DIR]  {item.name}/")
      else:
        entries.append(f"[FILE] {item.name}")

    if not entries:
      return "Directory is empty."

    return "\n".join(entries)
  except PermissionError:
    return f"Permission denied for directory {path}."
  except Exception as e:
    return f"Error listing files: {e}"


def run_command(command: str) -> str:
  try:
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=WORKSPACE,
    )

    output = result.stdout
    if result.stderr:
      output += "\n--- stderr ---\n" + result.stderr

    if len(output) > 10000:
      output = output[:10000] + "\n... (output truncated)"

    if result.returncode == 0:
      return output if output else "(no output)"

    return (
        f"Command failed (exit code {result.returncode}):\n"
        f"{output}"
    )
  except subprocess.TimeoutExpired:
    return "Error: Command timed out after 60 seconds."
  except Exception as e:
    return f"Error executing command: {e}"


def execute_tool(tool_name: str, tool_input: dict) -> str:
  try:
    if tool_name == "read_file":
      return read_file(tool_input["path"])
    elif tool_name == "write_file":
      return write_file(tool_input["path"], tool_input["content"])
    elif tool_name == "list_files":
      return list_files(tool_input.get("path", "."))
    elif tool_name == "run_command":
      
      return run_command(tool_input["command"])
    elif tool_name == "search_files":
      return search_files(
          tool_input["path"],
          tool_input["pattern"],
          tool_input.get("file_pattern"),
      )
    else:
      return f"Error: Unknown tool: {tool_name}"
  except Exception as e:
    return f"Error executing {tool_name}: {e}"


def run_agent(user_message: str, conversation_history: list = None) -> None:
  if conversation_history is None:
    conversation_history = []

  
  conversation_history.append({"role": "user", "content": user_message})

  while True:
   
    response = client.responses.create(
        model=MODEL,
        instructions=SYSTEM_PROMPT,
        input=conversation_history,
        tools=TOOLS,
    )

    
    conversation_history.extend(response.output)

    
    tool_calls = [
        item for item in response.output if item.type == "function_call"
    ]

    
    if not tool_calls:
      print(response.output_text)
      return

    
    for tool_call in tool_calls:
      print(f"\nUsing tool: {tool_call.name}")

      result = execute_tool(tool_call.name, tool_call.arguments)

      
      conversation_history.append({
          "type": "function_call_output",
          "call_id": tool_call.call_id,
          "output": result,
      })

def search_files(path: str, pattern: str, file_pattern: str = None) -> str:
    results = []
    for file_path in Path(path).rglob("*"):
        if not file_path.is_file():
            continue

       
        if any(part in ['node_modules', '__pycache__', '.git', 'venv']
               for part in file_path.parts):
            continue

       
        if file_pattern and not fnmatch.fnmatch(file_path.name, file_pattern):
            continue

        try:
            with open(file_path, 'r') as f:
                for i, line in enumerate(f, 1):
                    if pattern.lower() in line.lower():
                        display = line.rstrip()[:200]  
                        results.append(f"{file_path}:{i}: {display}")
                        if len(results) >= 50:
                            return '\n'.join(results) + "\n... (limited to 50 results)"
        except (UnicodeDecodeError, PermissionError):
            continue

    return '\n'.join(results) if results else f"No matches for '{pattern}'"


def main():
  """Main CLI loop."""
  print("welcome")
  print("Commands: 'quit' to exit, 'clear' to reset conversation\n")

  conversation_history = []

  while True:
    try:
      user_input = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
      print("\nGoodbye!")
      break

    if not user_input:
      continue

    if user_input.lower() == "quit":
      print("Goodbye!")
      break

    if user_input.lower() == "clear":
      conversation_history = []
      print("Conversation cleared.\n")
      continue

    print("\nAgent: ", end="", flush=True)
    run_agent(user_input, conversation_history)
    print()


if __name__ == "__main__":
  main()
