# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Run Commands

```bash
uv sync                 # Install dependencies
uv run parakeet         # Run the agent
uv run parakeet --help  # Show CLI help
uv tool install .       # Install globally
```

## Architecture

```
parakeet/
├── main.py           # Typer CLI entry point
├── cli/              # CLI commands
│   ├── chat.py       # Chat command (default)
│   ├── config_cmd.py # Config command
│   └── init_cmd.py   # Init command
├── core/             # Core logic
│   ├── agent.py      # Agent loop + SYSTEM_PROMPT
│   ├── config.py     # Config loading/saving
│   └── tools.py      # Tool definitions (TOOLS, TOOL_REGISTRY)
└── ui/               # Rich console components
    ├── console.py    # Colored output, syntax highlighting
    └── spinner.py    # Loading spinner
```

## Key Components

**Tools** (`core/tools.py`):
- `TOOLS` list - Python functions passed to Ollama for native tool calling
- `TOOL_REGISTRY` dict - Maps function names to functions
- `DANGEROUS_TOOLS` set - Tools requiring user confirmation

**Agent Loop** (`core/agent.py`):
- Uses native Ollama tool calling (`client.chat(tools=TOOLS)`)
- Processes `response.message.tool_calls`
- Shows spinner during LLM calls

**CLI** (`main.py`):
- Typer app with subcommands: `chat`, `config`, `init`
- Default command is `chat`

## Configuration

- Global: `~/.parakeet/config.json`
- Project: `.parakeet/context.md` (created by `parakeet init`)
