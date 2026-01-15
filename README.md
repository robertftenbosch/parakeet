# Parakeet

AI coding agent specialized in biotech and robotics applications with multi-agent collaboration, conversation memory, and interactive planning.

## ✨ Key Features

### 🤖 Multi-Agent System
- **Orchestrator-based coordination** - Intelligent task delegation to specialist agents
- **5 Specialist Agents** - Coding, Research, Testing, Bioinformatics, and Orchestrator
- **Collaborative workflows** - Agents work together on complex tasks
- **Transparent delegation** - See which agent handles each step

### 💬 Conversation Memory
- **Persistent sessions** - Conversations saved and auto-resumed
- **Session management** - List, view, and manage conversation history
- **Context retention** - Remember previous interactions across restarts
- **Smart truncation** - Automatic context window management

### 📋 Interactive Planning
- **Plan proposals** - Agents present multi-step plans for approval
- **Checkbox selection** - Choose which steps to execute
- **Iterative execution** - Approve steps incrementally
- **Full transparency** - See the complete workflow before execution

### 🔧 Enhanced Development Tools
- **Git integration** - Full git operations with smart commits
- **Persistent shell sessions** - Maintain state between commands
- **Environment variables** - Custom env vars for execution
- **Configurable timeouts** - Flexible command execution

### 🧬 Specialized Expertise
- **Bioinformatics** - Direct access to KEGG, PDB, UniProt, NCBI, BLAST
- **Pathway analysis** - Metabolic pathway optimization and comparison
- **Robotics** - ROS2, PyBullet, MuJoCo, Gazebo, OpenCV
- **BioPython** - Sequence analysis, alignment, primer design

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
parakeet                    # Start chat (auto-resumes last session)
parakeet --new              # Start fresh session
parakeet --multi-agent      # Enable multi-agent mode
parakeet chat               # Explicit chat command
parakeet config             # Show current configuration
parakeet config --host URL --model NAME  # Update configuration
parakeet init               # Initialize project in current directory
parakeet sessions list      # List all saved sessions
parakeet sessions show [ID] # View session conversation
parakeet sessions delete ID # Delete a session
parakeet sessions clear     # Delete all sessions
parakeet --version          # Show version
```

### Options

```bash
parakeet --host http://localhost:11434  # Specify Ollama host
parakeet --model llama3.2               # Specify model
parakeet --new                          # Start new session (don't resume)
parakeet --multi-agent                  # Enable multi-agent mode
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

## Multi-Agent Mode

Enable specialized agents that collaborate on complex tasks:

```bash
parakeet --multi-agent
```

### Available Agents

| Agent | Role | Specialization |
|-------|------|----------------|
| **Orchestrator** | Coordination | Plans tasks, delegates to specialists, integrates results |
| **Coding** | Implementation | Writes code, refactors, implements features |
| **Research** | Analysis | Analyzes codebases, finds patterns, reads documentation |
| **Testing** | Quality | Writes tests, runs test suites, ensures quality |
| **Bioinformatics** | Bio Data | Queries databases, analyzes pathways, BioPython |

### How It Works

1. **User gives task** → Orchestrator receives it
2. **Orchestrator creates plan** → Uses `propose_plan_tool`
3. **User selects steps** → Interactive checkbox UI
4. **Orchestrator delegates** → Each agent works on their part
5. **Results integrated** → Combined and presented to user

**Example:**
```
You: "Implement authentication with tests"

Orchestrator Plan:
  1. Research existing auth patterns (research agent)
  2. Implement JWT auth module (coding agent)
  3. Write unit tests (testing agent)

Select steps: 1 2 3
[Agents execute their assigned steps]
```

See [parakeet/core/agents/README.md](parakeet/core/agents/README.md) for details.

## Interactive Planning

Agents can propose multi-step plans and let you select which steps to execute:

```
┌─ 📋 Plan Proposal ────────────────────────────────┐
│    Add user authentication feature                 │
└────────────────────────────────────────────────────┘

   #  Step                              Agent     Selected
─────────────────────────────────────────────────────────
   1  Research existing patterns        research  ☐
   2  Implement auth module             coding    ☐
   3  Write tests                       testing   ☐

Select steps: 1 2
```

- Select specific steps: `1 2 4`
- Select all: `all`
- Cancel: `none` or Enter

See [PLAN_SELECTION.md](PLAN_SELECTION.md) for details.

## Session Management

Conversations are automatically saved and can be resumed:

```bash
# Conversations auto-save to ~/.parakeet/sessions/

parakeet              # Auto-resumes last session
parakeet --new        # Start fresh session

# Manage sessions
parakeet sessions list              # List all sessions
parakeet sessions show [ID]         # View conversation
parakeet sessions delete <ID>       # Delete session
parakeet sessions clear             # Delete all sessions
```

Sessions include:
- Full conversation history
- Context window management (max 100 messages)
- Session metadata (created time, message count)

## Tools

The agent has access to:

### Planning & Coordination
| Tool | Description |
|------|-------------|
| `propose_plan_tool` | Present multi-step plans for user approval with checkbox selection |

### File & Code Operations
| Tool | Description |
|------|-------------|
| `read_file_tool` | Read file contents |
| `list_files_tool` | List directory contents |
| `edit_file_tool` | Edit or create files |
| `search_code_tool` | Search for patterns in files (regex) |
| `sqlite_tool` | Query SQLite databases (write queries require confirmation) |

### Git Operations
| Tool | Description |
|------|-------------|
| `git_tool` | Full git operations (status, log, diff, branch, add, commit, push, pull, checkout, merge, stash, reset, remote) |
| `smart_commit_tool` | Intelligent commits with auto-generated messages (requires confirmation) |

### Environment Management
| Tool | Description |
|------|-------------|
| `create_venv_tool` | Create virtual environment for a project |
| `install_deps_tool` | Install dependencies (requires confirmation) |

### Code Execution
| Tool | Description |
|------|-------------|
| `run_bash_tool` | Execute bash commands with timeout, env vars, cwd, and persistent shell sessions (requires confirmation) |
| `manage_shell_session_tool` | Manage persistent shell sessions (list, terminate, cleanup) |
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

### Pathway Analysis
| Tool | Description |
|------|-------------|
| `analyze_pathway_tool` | Analyze metabolic pathways (info, enzymes, optimization) |
| `compare_organisms_tool` | Compare pathways between two organisms |
| `find_alternatives_tool` | Find alternative enzymes from different organisms |

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

## Advanced Features

### Persistent Shell Sessions

Maintain shell state between commands:

```python
# Commands in same session preserve environment
run_bash_tool("cd /tmp", session_id="dev")
run_bash_tool("export VAR=123", session_id="dev")
run_bash_tool("echo $VAR", session_id="dev")  # Output: 123
```

### Git Workflow

Smart git operations with automatic confirmations:

```python
# Check status
git_tool(action="status")

# Smart commit with auto-generated message
smart_commit_tool(auto_message=True)

# Push to remote
git_tool(action="push", remote="origin", branch="main")
```

### Custom Environment Variables

Execute commands with custom environment:

```python
run_bash_tool(
    "npm test",
    env={"NODE_ENV": "test", "API_KEY": "secret"},
    timeout=120.0
)
```

## Examples

### Single Agent: Feature Implementation
```
You: Add JWT authentication to the API

Agent: Let me propose a plan...
  1. Research existing auth patterns
  2. Implement JWT module
  3. Add auth middleware
  4. Write tests

Select steps: all

[Agent executes all steps]
```

### Multi-Agent: Complete Feature with Tests
```
You: Implement user login with full test coverage

Orchestrator: Creating plan...
  1. Analyze codebase structure (research)
  2. Design login architecture (orchestrator)
  3. Implement login endpoints (coding)
  4. Write unit tests (testing)
  5. Write integration tests (testing)

Select steps: 1 2 3 4

[Each specialist agent executes their part]
```

### Bioinformatics: Pathway Analysis
```
You: Analyze nitrogen fixation pathway and find optimization targets

Bioinformatics Agent: Proposing analysis plan...
  1. Query KEGG for nitrogen metabolism
  2. Identify key enzymes
  3. Compare with other organisms
  4. Find alternative enzymes
  5. Generate optimization report

Select steps: all

[Agent queries databases and generates report]
```

## Supported Models

Any Ollama model with tool support:
- `llama3.2` (recommended)
- `llama3.1`
- `qwen2.5`
- `mistral`

Check [ollama.com/library](https://ollama.com/library) for models with the "tools" badge.

## Documentation

- [Multi-Agent System](parakeet/core/agents/README.md) - Detailed agent documentation
- [Interactive Planning](PLAN_SELECTION.md) - Plan selection guide
- [Project Context](CLAUDE.md) - Codebase context for Claude

## License

MIT
