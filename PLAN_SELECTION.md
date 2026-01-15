# Interactive Plan Selection

Parakeet agents can propose multi-step plans and let you select which steps to execute using interactive checkboxes.

## Overview

When an agent receives a complex task, it can:
1. Break down the task into multiple steps
2. Present the plan using `propose_plan_tool`
3. Show an interactive checkbox UI
4. Execute only the steps you approve

## How It Works

### Agent Proposes Plan

The agent uses `propose_plan_tool` to present a structured plan:

```python
propose_plan_tool(
    plan_title="Add user authentication feature",
    steps=[
        {"description": "Research existing auth patterns in codebase", "agent": "research"},
        {"description": "Implement JWT authentication module", "agent": "coding"},
        {"description": "Add login/logout endpoints", "agent": "coding"},
        {"description": "Write unit tests for auth", "agent": "testing"},
        {"description": "Update documentation", "agent": "coding"}
    ]
)
```

### Interactive Selection UI

You'll see a table with all steps:

```
┌─ 📋 Plan Proposal ──────────────────────────────────────────┐
│          Add user authentication feature                     │
└──────────────────────────────────────────────────────────────┘

   #  Step                                      Agent     Selected
───────────────────────────────────────────────────────────────────
   1  Research existing auth patterns           research  ☐
   2  Implement JWT authentication module       coding    ☐
   3  Add login/logout endpoints                coding    ☐
   4  Write unit tests for auth                 testing   ☐
   5  Update documentation                      coding    ☐

Select steps to execute:
  • Enter step numbers separated by spaces (e.g., '1 2 4')
  • Enter 'all' to select all steps
  • Enter 'none' or leave empty to cancel

Select steps: _
```

### Selection Options

**Select specific steps:**
```
Select steps: 1 2 3
```

**Select all steps:**
```
Select steps: all
```

**Cancel the plan:**
```
Select steps: none
```
or just press Enter

### Confirmation

After selection, you'll see a summary and confirmation:

```
Selected steps:
  ✓ 1. Research existing auth patterns in codebase (research)
  ✓ 2. Implement JWT authentication module (coding)
  ✓ 3. Add login/logout endpoints (coding)

Execute these steps? [Y/n]: _
```

## When Plans Are Proposed

### Single Agent Mode

The agent will propose a plan when:
- The task is complex with multiple steps
- The user asks for a feature that requires several changes
- There are multiple approaches that need approval

Example:
```
You: Add user authentication with JWT tokens

Agent: I'll create a plan for implementing authentication...
[Shows plan with checkboxes]
```

### Multi-Agent Mode

The **Orchestrator** will propose a plan showing which specialist agents will handle each step:

```
You: Implement a login system with tests

Orchestrator: Here's my plan for the login system...

   #  Step                              Agent        Selected
────────────────────────────────────────────────────────────
   1  Analyze current code structure    research     ☐
   2  Design login architecture         orchestrator ☐
   3  Implement login module            coding       ☐
   4  Write integration tests           testing      ☐
   5  Deploy to staging                 coding       ☐

Select steps: _
```

## Benefits

### Selective Execution
- Skip steps you've already done
- Omit steps you don't need (e.g., skip documentation updates)
- Focus on specific parts of a larger plan

### Transparency
- See exactly what the agent plans to do
- Understand the workflow before execution
- Know which specialist agent handles each step (multi-agent mode)

### Control
- Fine-grained control over agent actions
- Prevent unwanted changes
- Iterative development (approve steps one at a time)

## Use Cases

### Feature Development
```
Task: "Add dark mode to the app"

Plan:
1. Research existing theme system
2. Create dark theme CSS variables
3. Add theme toggle component
4. Update all components for dark mode
5. Test theme persistence
6. Update documentation

You might select: 1, 2, 3 (research and core implementation)
Skip for now: 4, 5, 6 (testing and docs - do later)
```

### Bug Fixing
```
Task: "Fix the authentication bug"

Plan:
1. Analyze the bug and find root cause
2. Write failing test that reproduces bug
3. Implement fix
4. Verify test passes
5. Check for similar bugs elsewhere

You might select: 1, 2 (investigation first)
Then run again to select: 3, 4 (after reviewing findings)
```

### Bioinformatics Workflow
```
Task: "Analyze nitrogen fixation pathway for optimization"

Plan:
1. Query KEGG for nitrogen metabolism pathway
2. Identify key enzymes and reactions
3. Compare with other organisms
4. Find enzyme alternatives
5. Generate BioPython analysis scripts
6. Create optimization recommendations

You might select: 1, 2, 3 (data gathering)
Skip: 4, 5, 6 (manual review first)
```

## Technical Details

### Tool: `propose_plan_tool`

**Parameters:**
- `plan_title` (str): Title describing the overall goal
- `steps` (list[dict]): List of step dictionaries

**Step Dictionary:**
- `description` (str, required): What the step does
- `agent` (str, optional): Which agent executes (for multi-agent mode)
- `rationale` (str, optional): Why this step is needed

**Returns:**
```python
{
    "approved": bool,              # Whether plan was approved
    "selected_steps": list[int],   # Indices of selected steps (0-based)
    "original_steps": list[dict],  # The original plan
    "message": str                 # Status message
}
```

### Agent Implementation

The agent receives the result and only executes approved steps:

```python
# Agent proposes plan
result = propose_plan_tool(plan_title="...", steps=[...])

if result["approved"]:
    # Execute only selected steps
    for idx in result["selected_steps"]:
        step = result["original_steps"][idx]
        # Execute step...
else:
    # Plan was cancelled
    return "Plan cancelled by user"
```

## Examples

### Simple Plan (Single Agent)
```python
propose_plan_tool(
    plan_title="Refactor authentication module",
    steps=[
        {"description": "Extract auth logic into separate module"},
        {"description": "Update all imports"},
        {"description": "Run tests to verify no breakage"}
    ]
)
```

### Complex Plan (Multi-Agent)
```python
propose_plan_tool(
    plan_title="Build complete feature with tests",
    steps=[
        {
            "description": "Research existing patterns",
            "agent": "research",
            "rationale": "Ensure consistency with codebase"
        },
        {
            "description": "Implement feature logic",
            "agent": "coding",
            "rationale": "Core functionality"
        },
        {
            "description": "Write unit tests",
            "agent": "testing",
            "rationale": "Verify correctness"
        },
        {
            "description": "Write integration tests",
            "agent": "testing",
            "rationale": "Verify end-to-end behavior"
        }
    ]
)
```

## Tips

**Start with research steps:**
Select only research/analysis steps first, review the findings, then run again to execute implementation steps.

**Iterative approach:**
Approve 1-2 steps at a time for complex changes. Review results before proceeding.

**Skip optional steps:**
Documentation, deployment, and cleanup steps can often be skipped initially and done later.

**Trust the agent for simple plans:**
If the plan looks good and has only 2-3 steps, just select 'all'.

**Modify the plan:**
If the plan isn't quite right, type 'none' to cancel and ask the agent to adjust the approach.

## Configuration

The plan selection feature is always available. No configuration needed.

Both single-agent and multi-agent modes support plan proposals.

## Future Enhancements

- [ ] Reorder steps interactively
- [ ] Edit step descriptions before execution
- [ ] Save approved plans for reuse
- [ ] Show estimated time for each step
- [ ] Allow skipping already-completed steps automatically
- [ ] Plan templates for common workflows
