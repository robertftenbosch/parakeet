# Multi-Agent System

Parakeet's multi-agent system enables specialized AI agents to collaborate on complex tasks through an orchestrator-based architecture.

## Architecture

### Orchestrator Model
The system uses an **Orchestrator Agent** that coordinates specialist agents:
- Breaks down complex tasks into subtasks
- Delegates work to appropriate specialists
- Manages workflow and dependencies
- Integrates results from multiple agents

### Specialist Agents

#### 1. **Coding Agent** (`coding`)
**Specialties:**
- Writing clean, maintainable code
- Implementing features and functionality
- Refactoring existing code
- Setting up development environments

**Tools:** File operations, code execution, shell sessions, venv management

**Best for:** Implementation tasks, refactoring, environment setup

#### 2. **Research Agent** (`research`)
**Specialties:**
- Analyzing codebases and architecture
- Finding relevant code and patterns
- Reading documentation
- Understanding project structure

**Tools:** File operations, code search

**Best for:** Code analysis, understanding patterns, documentation research

#### 3. **Testing Agent** (`testing`)
**Specialties:**
- Writing unit and integration tests
- Running test suites
- Analyzing test results
- Ensuring code quality

**Tools:** File operations, code search, execution, shell sessions

**Best for:** Test development, test execution, quality assurance

#### 4. **Bioinformatics Agent** (`bioinformatics`)
**Specialties:**
- Querying biological databases (KEGG, PDB, UniProt, NCBI)
- Pathway analysis and enzyme research
- BioPython implementations
- Metabolic engineering

**Tools:** All bio database tools, pathway analysis, BioPython execution

**Best for:** Bio-specific tasks, database queries, pathway analysis

## Usage

### Enable Multi-Agent Mode

```bash
# Using the flag
parakeet --multi-agent

# Or with chat command
parakeet chat --multi-agent
```

### How It Works

1. **User gives a task** → Orchestrator receives it
2. **Orchestrator creates a plan** → Breaks down into subtasks
3. **Orchestrator delegates** → Assigns subtasks to specialist agents
4. **Specialists execute** → Each agent works on their part
5. **Orchestrator integrates** → Combines results and presents to user

### Example Workflow: Feature Implementation

```
User: "Add a user authentication system with tests"

Orchestrator Plan:
├─ 1. Research Agent → Analyze existing auth patterns in codebase
├─ 2. Coding Agent → Implement authentication module
└─ 3. Testing Agent → Write and run tests for auth system

Results integrated and presented to user.
```

### Example Workflow: Bioinformatics Analysis

```
User: "Analyze nitrogen fixation pathway and implement BioPython scripts"

Orchestrator Plan:
├─ 1. Bioinformatics Agent → Query KEGG for nitrogen metabolism pathway
├─ 2. Research Agent → Analyze existing bio code patterns
├─ 3. Coding Agent → Implement BioPython analysis scripts
└─ 4. Testing Agent → Validate the analysis pipeline

Results integrated and presented to user.
```

## Agent Communication

### Delegation Format
The Orchestrator uses the `delegate_task` tool:

```python
delegate_task(
    agent="coding",
    task="Implement user authentication with JWT tokens",
    context={
        "style": "match existing patterns",
        "files": ["src/auth/"],
        "requirements": ["jwt library", "password hashing"]
    }
)
```

### Result Integration
Each agent returns:
- Task results and outputs
- Files modified or created
- Issues or limitations encountered
- Suggestions for next steps

## Benefits

1. **Specialization**: Each agent is optimized for specific tasks
2. **Focus**: Agents use only relevant tools for their domain
3. **Efficiency**: Parallel-capable architecture (future enhancement)
4. **Quality**: Specialized prompts ensure high-quality outputs
5. **Clarity**: Clear separation of concerns

## Comparison: Single vs Multi-Agent

### Single Agent Mode (Default)
- One generalist agent with all tools
- Good for: Simple tasks, quick interactions
- User directly interacts with agent

### Multi-Agent Mode
- Orchestrator + 4 specialist agents
- Good for: Complex tasks, multi-step workflows
- User interacts with orchestrator who delegates

## Agent Capabilities Matrix

| Agent | Code Writing | Research | Testing | Bio | Planning |
|-------|-------------|----------|---------|-----|----------|
| Orchestrator | ❌ | ❌ | ❌ | ❌ | ✅ |
| Coding | ✅ | ❌ | ❌ | ❌ | ❌ |
| Research | ❌ | ✅ | ❌ | ❌ | ❌ |
| Testing | ❌ | ✅ | ✅ | ❌ | ❌ |
| Bioinformatics | ✅* | ✅ | ❌ | ✅ | ❌ |

*Bio-specific code only

## Technical Details

### File Structure
```
parakeet/core/agents/
├── __init__.py           # Agent exports
├── base.py               # Base Agent class
├── orchestrator.py       # Orchestrator Agent
├── coding.py             # Coding Agent
├── research.py           # Research Agent
├── testing.py            # Testing Agent
└── bioinformatics.py     # Bioinformatics Agent

parakeet/core/
└── multi_agent.py        # MultiAgentCoordinator
```

### Key Classes

- **`Agent`**: Base class for all agents
- **`AgentCapability`**: Enum of agent capabilities
- **`AgentTask`**: Task definition for delegation
- **`AgentResult`**: Result from agent execution
- **`MultiAgentCoordinator`**: Coordinates agent interactions

### Extending the System

To add a new specialist agent:

1. Create new agent file: `parakeet/core/agents/new_agent.py`
2. Inherit from `Agent` base class
3. Define capabilities and tools
4. Override `_build_system_prompt()`
5. Add to `MultiAgentCoordinator.__init__()`
6. Update orchestrator prompt with new agent info

## Future Enhancements

- [ ] Parallel agent execution
- [ ] Agent-to-agent direct communication
- [ ] Persistent agent memory across sessions
- [ ] Agent performance metrics and optimization
- [ ] Dynamic agent creation based on task type
- [ ] Web UI for visualizing agent collaboration
