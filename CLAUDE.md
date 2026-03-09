# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About This Project

This is a CodeCrafters challenge to build a minimal "Claude Code"-like AI coding assistant in Python. The program accepts a prompt via CLI, runs an agent loop using an OpenAI-compatible API (OpenRouter), and executes tool calls (Read, Write, Bash) until the model produces a final text response.

## Commands

**Run the program locally:**
```sh
./your_program.sh -p "your prompt here"
```

**Submit to CodeCrafters:**
```sh
codecrafters submit
```

**Install dependencies (uses uv):**
```sh
uv sync
```

## Architecture

All logic lives in `app/main.py`. The program follows a simple agent loop:

1. Parse CLI args (`-p <prompt>`)
2. Initialize an `OpenAI` client pointed at OpenRouter (`OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` from env)
3. Loop: send messages → if model returns tool calls, execute them and append results → if model returns text, print and exit

**Tools exposed to the model:**
- `Read(file_path)` — reads a file
- `Write(file_path, content)` — writes a file
- `Bash(command)` — runs a shell command via `subprocess`

**Environment variables required:**
- `OPENROUTER_API_KEY` — API key for OpenRouter
- `OPENROUTER_BASE_URL` — defaults to `https://openrouter.ai/api/v1`

The model used is `anthropic/claude-haiku-4.5` via OpenRouter. The `.env` file is loaded automatically via `python-dotenv`.

## Runtime

- Python 3.14, managed with `uv`
- Entry point: `app/main.py` (invoked as `-m app.main`)
- The `.codecrafters/run.sh` script sets `PYTHONSAFEPATH=1` to avoid accidental module shadowing
