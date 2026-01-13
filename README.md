# Parakeet

AI coding agent specialized in biotech and robotics applications.

## Features

- **Native Ollama tool calling** - Reliable tool execution via Ollama API
- **Biotech expertise** - BioPython, FASTA, sequence alignment, BLAST
- **Robotics expertise** - ROS2, PyBullet, MuJoCo, Gazebo, OpenCV
- **Code execution** - Run bash commands and Python code (with confirmation)
- **File operations** - Read, list, and edit files
- **Rich CLI** - Loading spinners, syntax highlighting, colored output
- **Virtual environments** - Automatic venv creation with uv, conda, or venv

## Installation

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install parakeet (SSH)
uv tool install git+ssh://git@github.com/robertftenbosch/parakeet.git

# Or with HTTPS
uv tool install git+https://github.com/robertftenbosch/parakeet.git
```

Ensure `~/.local/bin` is in your PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai) with a model that supports tools (e.g., `llama3.1`, `llama3.2`, `qwen2.5`)

```bash
# Install Ollama and pull a model
ollama pull llama3.2
```

## Usage

### Commands

```bash
parakeet                # Start chat (default)
parakeet chat           # Start interactive chat session
parakeet config         # Show current configuration
parakeet config --host URL --model NAME  # Update configuration
parakeet init           # Initialize project in current directory
parakeet --version      # Show version
```

### Options

```bash
parakeet --host http://localhost:11434  # Specify Ollama host
parakeet --model llama3.2               # Specify model
```

### First Run

On first run, Parakeet will:
1. Connect to Ollama (default: `http://localhost:11434`)
2. Show available models and let you select one
3. Save configuration to `~/.parakeet/config.json`

### Project Initialization

```bash
cd your-project
parakeet init              # Basic initialization
parakeet init --venv       # With virtual environment
parakeet init --venv -p 3.11  # With specific Python version
```

Creates `.parakeet/` directory with:
- `context.md` - Project-specific instructions for the AI
- `config.json` - Project configuration

With `--venv`, also creates a `.venv/` virtual environment using:
1. **uv** (preferred) - Fast, modern Python package manager
2. **conda** - If uv not available
3. **venv** - Standard library fallback

If no package manager is found, Parakeet will offer to install uv.

## Tools

The agent has access to:

### File & Code Operations
| Tool | Description |
|------|-------------|
| `read_file_tool` | Read file contents |
| `list_files_tool` | List directory contents |
| `edit_file_tool` | Edit or create files |
| `search_code_tool` | Search for patterns in files (regex) |
| `sqlite_tool` | Query SQLite databases (write queries require confirmation) |

### Environment Management
| Tool | Description |
|------|-------------|
| `create_venv_tool` | Create virtual environment for a project |
| `install_deps_tool` | Install dependencies (requires confirmation) |

### Code Execution
| Tool | Description |
|------|-------------|
| `run_bash_tool` | Execute bash commands (requires confirmation) |
| `run_python_tool` | Execute Python code (requires confirmation) |

### Bioinformatics Databases
| Tool | Description |
|------|-------------|
| `kegg_tool` | Query KEGG for metabolic pathways, enzymes, reactions |
| `pdb_tool` | Search RCSB PDB for protein structures |
| `uniprot_tool` | Query UniProt for protein sequences and annotations |
| `ncbi_tool` | Search NCBI databases (protein, nucleotide, gene) |
| `ontology_tool` | Query biological ontologies (GO, CHEBI) |
| `blast_tool` | Run BLAST sequence similarity searches |

## Configuration

Configuration is stored in `~/.parakeet/config.json`:

```json
{
  "ollama_host": "http://localhost:11434",
  "ollama_model": "llama3.2"
}
```

Environment variables (`.env`) are also supported:
- `OLLAMA_HOST` - Ollama server URL
- `OLLAMA_MODEL` - Model name

Priority: CLI args > config file > environment variables > defaults

## Development

```bash
git clone git@github.com:robertftenbosch/parakeet.git
cd parakeet
uv sync
uv run parakeet
```

## Supported Models

Any Ollama model with tool support:
- `llama3.2` (recommended)
- `llama3.1`
- `qwen2.5`
- `mistral`

Check [ollama.com/library](https://ollama.com/library) for models with the "tools" badge.
