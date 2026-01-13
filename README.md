# parakeet

AI agent that uses LLM models to execute coding tasks with tool support.

## Features

- File reading, listing, and editing capabilities
- Interactive REPL interface
- Tool execution through LLM reasoning
- Uses Ollama for local LLM inference

## Setup

1. Clone the repository

2. Install Ollama:
   - Visit [ollama.ai](https://ollama.ai) and follow installation instructions
   - Pull a model: `ollama pull llama3.2`

3. Install uv (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Or on Windows:
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

4. Install dependencies and create virtual environment:
   ```bash
   uv sync
   ```

5. (Optional) Create a `.env` file to customize settings:
   ```bash
   cp .env.example .env
   ```

   You can configure:
   - `OLLAMA_HOST`: Ollama server URL (default: http://localhost:11434)
   - `OLLAMA_MODEL`: Model to use (default: llama3.2)

## Usage

Run the coding agent:
```bash
uv run python main.py
```

Or activate the virtual environment first:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python main.py
```

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
