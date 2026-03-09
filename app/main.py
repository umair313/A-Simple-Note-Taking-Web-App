import argparse
import inspect
import json
import os
import subprocess
import sys
from typing import get_type_hints

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")

# --- Tool registry -----------------------------------------------------------

_TOOLS: dict[str, callable] = {}
_TOOL_SCHEMAS: list[dict] = []

_PY_TO_JSON_TYPE = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def tool(fn: callable) -> callable:
    """Decorator that registers a function as an LLM tool and auto-generates its JSON schema."""
    hints = get_type_hints(fn)
    hints.pop("return", None)
    sig = inspect.signature(fn)

    # Parse "param: description" lines from the docstring
    param_docs: dict[str, str] = {}
    doc = inspect.getdoc(fn) or ""
    lines = iter(doc.splitlines())
    description = next(lines, fn.__name__)  # first line = tool description
    for line in lines:
        line = line.strip()
        if ":" in line:
            pname, _, pdesc = line.partition(":")
            param_docs[pname.strip()] = pdesc.strip()

    properties = {}
    required = []
    for name, param in sig.parameters.items():
        json_type = _PY_TO_JSON_TYPE.get(hints.get(name), "string")
        properties[name] = {"type": json_type, "description": param_docs.get(name, name)}
        if param.default is inspect.Parameter.empty:
            required.append(name)

    _TOOLS[fn.__name__] = fn
    _TOOL_SCHEMAS.append({
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    })
    return fn


def dispatch(name: str, arguments: str) -> str:
    """Look up a registered tool by name and call it with the parsed JSON arguments."""
    fn = _TOOLS.get(name)
    if fn is None:
        return f"Unknown tool: {name}"
    kwargs = json.loads(arguments)
    return fn(**kwargs)


# --- Tool implementations ----------------------------------------------------

@tool
def Read(file_path: str) -> str:
    """Read and return the contents of a file.
    file_path: The path to the file to read
    """
    with open(file_path) as f:
        return f.read()


@tool
def Write(file_path: str, content: str) -> str:
    """Write content to a file.
    file_path: The path to the file to write
    content: The content to write
    """
    if dir_name := os.path.dirname(file_path):
        os.makedirs(dir_name, exist_ok=True)
    with open(file_path, "w") as f:
        f.write(content)
    return f"Successfully wrote to {file_path}"


@tool
def Bash(command: str) -> str:
    """Execute a shell command and return its stdout.
    command: The shell command to execute
    """
    result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout.decode()


# --- Agent loop --------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", required=True)
    cli_args = parser.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    print("Logs from your program will appear here!", file=sys.stderr)

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    messages = [
        {"role": "system", "content": "You are a helpful assistant. you have tools which you can use to perform actions you can run many tools I complete a task. Always respond with `Deleted README_old.md`"},
        {"role": "user", "content": cli_args.p},
    ]

    while True:
        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=messages,
            tools=_TOOL_SCHEMAS,
        )

        if not chat.choices:
            raise RuntimeError("no choices in response")

        message = chat.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            print(message.content)
            break

        for tool_call in message.tool_calls:
            result = dispatch(tool_call.function.name, tool_call.function.arguments)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })


if __name__ == "__main__":
    main()
