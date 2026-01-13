# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Run Commands

```bash
# Install dependencies
uv sync

# Run the agent
uv run parakeet

# Install globally (to ~/.local/bin)
uv tool install .
```

## Environment Configuration

Copy `.env.example` to `.env` to customize:
- `OLLAMA_HOST`: Ollama server URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model to use (default: llama3.2)

Requires Ollama running locally with a model pulled (e.g., `ollama pull llama3.2`).

## Architecture

This is a single-file coding agent (`main.py`) that uses Ollama for local LLM inference.

**Tool System**: Tools are registered in `TOOL_REGISTRY` dict mapping names to functions. Each tool function has a docstring used to generate the system prompt. Available tools:
- `read_file`: Read file contents
- `list_files`: List directory contents
- `edit_file`: Replace strings in files or create new files

**Agent Loop** (`run_coding_agent_loop`): REPL that maintains conversation history and processes tool invocations. The LLM requests tools via `tool: TOOL_NAME({JSON_ARGS})` format, which `extract_tool_invocations` parses. Tool results are fed back as `tool_result(...)` messages.

**Path Resolution**: `resolve_abs_path` converts relative paths to absolute using current working directory.
