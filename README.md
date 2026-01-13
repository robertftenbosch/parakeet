# parakeet

AI agent that uses LLM models to execute coding tasks with tool support.

## Features

- File reading, listing, and editing capabilities
- Interactive REPL interface
- Tool execution through LLM reasoning
- Uses Ollama for local LLM inference

## Installation (Linux Server)

Install directly from GitHub:
```bash
# Install uv first (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install parakeet as a tool (installs to ~/.local/bin)
uv tool install git+ssh://git@github.com/robertftenbosch/parakeet.git

# Or with HTTPS:
uv tool install git+https://github.com/robertftenbosch/parakeet.git
```

Make sure `~/.local/bin` is in your PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then run:
```bash
parakeet
```

## Development Setup

1. Clone the repository

2. Install Ollama:
   - Visit [ollama.ai](https://ollama.ai) and follow installation instructions
   - Pull a model: `ollama pull llama3.2`

3. Install uv (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

4. Install dependencies:
   ```bash
   uv sync
   ```

5. Run from source:
   ```bash
   uv run parakeet
   ```

## Usage

```bash
# First run: interactive model selection
parakeet

# Specify host and model directly
parakeet --host http://192.168.1.100:11434 --model llama3.1
```

Configuration is saved to `~/.parakeet/config.json`.

The agent will start an interactive loop where you can ask it to perform coding tasks. It has access to:
- `read_file`: Read file contents
- `list_files`: List files in a directory
- `edit_file`: Edit files by replacing strings

## Available Models

You can use any model available in your Ollama installation. Popular options include:
- `llama3.2` (default)
- `llama3.1`
- `codellama`
- `mistral`
- `phi3`

To use a different model, set the `OLLAMA_MODEL` environment variable in your `.env` file.
