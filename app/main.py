import argparse
import os
import sys
import json
from openai import OpenAI

# API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
API_KEY="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"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    messages = [{"role": "user", "content": args.p}]
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)
    while True:
        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=messages,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "Read",
                        "description": "Read and return the contents of a file",
                        "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                            "type": "string",
                            "description": "The path to the file to read"
                            }
                        },
                        "required": ["file_path"]
                        }
                    }
                }
            ]
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("no choices in response")

        message = chat.choices[0].message
        messages.append(message)
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            if tool_call.function.name == "Read":
                args = json.loads(tool_call.function.arguments)
                print("Reading file", args["file_path"])
                with open(args["file_path"], "r") as f:
                    content = f.read()
                    result = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content
                    }
                    messages.append(result)
        else:
            print(message.content)
            break


if __name__ == "__main__":
    main()
