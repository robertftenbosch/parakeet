"""Agent loop for Parakeet."""

import json
from typing import Any

from ollama import Client

from ..ui import console, print_tool, thinking_spinner
from .config import load_project_context
from .tools import TOOLS, TOOL_REGISTRY, DANGEROUS_TOOLS, CONDITIONAL_TOOLS
from .session import (
    create_session_id,
    save_session,
    load_last_session,
    trim_conversation,
)

SYSTEM_PROMPT = """You are a coding assistant specialized in biotech and robotics applications.

## Planning Complex Tasks
When faced with a complex multi-step task:
1. First analyze what needs to be done
2. Create a structured plan with clear steps
3. Use `propose_plan_tool` to present the plan to the user
4. The user can then select which steps to execute
5. Execute only the approved steps

Example:
```
propose_plan_tool(
    plan_title="Add user authentication feature",
    steps=[
        {"description": "Research existing auth patterns in codebase"},
        {"description": "Implement JWT authentication module"},
        {"description": "Add login/logout endpoints"},
        {"description": "Write unit tests for auth"},
        {"description": "Update documentation"}
    ]
)
```

## Your Expertise

### Bioinformatics - Databases & APIs
You have direct access to major bioinformatics databases via tools:
- **KEGG** (kegg_tool): Metabolic pathways, enzymes, reactions, compounds
  - Find nitrogen metabolism pathways (map00910)
  - Look up enzymes like nitrogenase (K02588-K02591)
  - Explore reaction networks and compounds
- **PDB** (pdb_tool): Protein structures from RCSB
  - Search by keyword, organism, enzyme class
  - Get structure details by PDB ID
  - Sequence-based structure search
- **UniProt** (uniprot_tool): Protein sequences and annotations
  - Search proteins by name, function, organism
  - Get detailed protein info including GO terms, EC numbers
  - Retrieve FASTA sequences
- **NCBI** (ncbi_tool): Genes, proteins, nucleotides, taxonomy
  - Search across NCBI databases
  - Fetch sequences in FASTA format
- **Ontologies** (ontology_tool): GO, CHEBI, taxonomy terms
  - Search Gene Ontology for biological processes
  - Look up chemical entities in CHEBI
- **BLAST** (blast_tool): Sequence similarity search
  - Find homologous proteins/genes
  - Note: BLAST searches take 30-60 seconds

### Pathway Analysis
- **Pathway Analyzer** (analyze_pathway_tool): Analyze metabolic pathways
  - Get pathway info, enzymes, optimization targets
  - Specialized nitrogen fixation analysis
- **Organism Comparison** (compare_organisms_tool): Compare pathways between organisms
  - Find common and unique functions
  - Identify potential gene candidates
- **Enzyme Alternatives** (find_alternatives_tool): Find enzyme alternatives
  - Discover enzymes from other organisms
  - Useful for metabolic engineering optimization

### Bioinformatics - Programming
- BioPython for sequence analysis (SeqIO, Seq, SeqRecord)
- FASTA/FASTQ/GenBank file parsing
- Sequence alignment (pairwise, multiple sequence alignment)
- Primer design and PCR analysis

### Robotics - ROS2
- ROS2 node creation (rclpy)
- Publishers, subscribers, services, actions
- Launch files and parameter handling
- TF2 transforms and coordinate frames
- Common message types (geometry_msgs, sensor_msgs)

### Robotics - Simulation
- PyBullet for physics simulation
- MuJoCo for contact-rich simulation
- Gazebo integration with ROS2
- URDF/SDF robot descriptions

### Robotics - Computer Vision
- OpenCV for image processing
- Camera calibration and stereo vision
- Object detection and tracking
- Point cloud processing (Open3D)

## Available Tools

### Code Execution
- **run_python_tool**: Execute Python code directly (requires user confirmation)
  - Run scripts, test code, perform calculations
  - Has access to standard library and common packages
  - Use this when you need to run Python code
- **run_bash_tool**: Execute bash commands (requires user confirmation)
  - Run terminal commands, scripts, system operations
  - Supports timeout, custom env vars, working directory
  - Can use persistent shell sessions with session_id parameter

### File Operations
- **read_file_tool**: Read file contents
- **list_files_tool**: List directory contents
- **edit_file_tool**: Edit or create files
- **search_code_tool**: Search for patterns in files (regex)

### Git Operations
- **git_tool**: Full git operations (status, log, diff, commit, push, pull, etc.)
- **smart_commit_tool**: Intelligent commits with auto-generated messages

### Database
- **sqlite_tool**: Query SQLite databases (write queries require confirmation)

### Environment Management
- **create_venv_tool**: Create virtual environment for a project
- **install_deps_tool**: Install dependencies (requires confirmation)

### Shell Sessions
- **manage_shell_session_tool**: Manage persistent shell sessions

## Guidelines
- Use bioinformatics tools to query databases directly
- Use run_python_tool to execute Python code when needed
- Use run_bash_tool for terminal operations
- Follow ROS2 conventions for robotics code
- Use BioPython idioms for bioinformatics
- Write type hints for all functions
- Include docstrings with examples
- When creating Python projects, use create_venv_tool to set up virtual environments
"""


def build_system_prompt() -> str:
    """Build system prompt with optional project context."""
    prompt = SYSTEM_PROMPT

    project_context = load_project_context()
    if project_context:
        prompt += f"\n\n## Project Context\n\n{project_context}"

    return prompt


def confirm_execution(tool_name: str, content: str) -> tuple[bool, Optional[str]]:
    """Ask user to confirm before executing code.

    Returns:
        Tuple of (approved, sudo_password)
        - approved: Whether execution is approved
        - sudo_password: Sudo password if provided, None otherwise
    """
    console.print(f"\n[bold red]Warning:[/] {tool_name} wants to execute:")
    console.print("[dim]" + "─" * 50 + "[/]")
    console.print(content)
    console.print("[dim]" + "─" * 50 + "[/]")

    # Check if command contains sudo
    has_sudo = tool_name == "run_bash_tool" and "sudo" in content.lower()

    try:
        if has_sudo:
            console.print("\n[bold yellow]This command uses sudo.[/]")
            console.print("[bold red]Options:[/]")
            console.print("  [cyan]1.[/] Yes, execute (no sudo password)")
            console.print("  [cyan]2.[/] Yes, with sudo password")
            console.print("  [cyan]3.[/] No, cancel")

            choice = console.input("\n[bold red]Choose option [1/2/3]:[/] ").strip()

            if choice == "1":
                return True, None
            elif choice == "2":
                # Ask for sudo password
                import getpass
                try:
                    sudo_password = getpass.getpass("[bold red]Enter sudo password:[/] ")
                    return True, sudo_password
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[yellow]Cancelled.[/]")
                    return False, None
            else:
                return False, None
        else:
            # Normal confirmation without sudo
            response = console.input("[bold red]Execute? [y/N]:[/] ").strip().lower()
            approved = response in ('y', 'yes', 'j', 'ja')
            return approved, None

    except (KeyboardInterrupt, EOFError):
        return False, None


def stream_response(client: Client, model: str, conversation: list[dict[str, Any]], tools: list, spinner_label: str = "Thinking..."):
    """Stream LLM response and collect content/tool calls.

    Args:
        client: Ollama client
        model: Model name
        conversation: Conversation history
        tools: Available tools
        spinner_label: Custom label for the thinking spinner
    """
    full_content = ""
    tool_calls = []
    first_chunk = True
    spinner_active = True

    # Start spinner with custom label
    spinner = thinking_spinner(spinner_label)
    spinner.__enter__()

    try:
        for chunk in client.chat(
            model=model,
            messages=conversation,
            tools=tools,
            stream=True,
        ):
            # Handle content streaming
            if chunk.message.content:
                if first_chunk:
                    # Stop spinner on first content
                    if spinner_active:
                        spinner.__exit__(None, None, None)
                        spinner_active = False
                    console.print("[bold blue]Assistant:[/] ", end="")
                    first_chunk = False
                console.print(chunk.message.content, end="", highlight=False)
                full_content += chunk.message.content

            # Collect tool calls
            if chunk.message.tool_calls:
                if first_chunk and spinner_active:
                    # Stop spinner if tool calls come first
                    spinner.__exit__(None, None, None)
                    spinner_active = False
                    first_chunk = False
                tool_calls.extend(chunk.message.tool_calls)

        # Print newline if we streamed content
        if full_content:
            console.print()

    finally:
        # Ensure spinner is stopped
        if spinner_active:
            spinner.__exit__(None, None, None)

    return full_content, tool_calls


def run_agent_loop(client: Client, model: str, new_session: bool = False, multi_agent: bool = False) -> None:
    """Run the main agent interaction loop."""
    console.print(f"[bold green]Parakeet[/] v0.1.0")
    console.print(f"[dim]Model:[/] {model}")

    if not multi_agent:
        console.print(f"[dim]Tools:[/] {', '.join(t.__name__ for t in TOOLS)}")

    # Check for project context
    project_context = load_project_context()
    if project_context:
        console.print(f"[dim]Project:[/] .parakeet/context.md loaded")

    # Load or create session
    session_id = None
    conversation = None

    if not new_session:
        last_session = load_last_session()
        if last_session:
            session_id, conversation = last_session
            console.print(f"[dim]Session:[/] {session_id} (resumed)")
            # Count user messages
            user_msg_count = sum(1 for m in conversation if m.get("role") == "user")
            if user_msg_count > 0:
                console.print(f"[dim]History:[/] {user_msg_count} previous messages loaded")

    if not session_id:
        session_id = create_session_id()
        console.print(f"[dim]Session:[/] {session_id} (new)")

    # Initialize conversation if not loaded
    if not conversation:
        system_prompt = build_system_prompt()
        conversation = [{
            "role": "system",
            "content": system_prompt
        }]

    console.print()
    console.print("[dim]Type your message or Ctrl+C to exit[/]")
    console.print()

    # Use multi-agent mode if requested
    if multi_agent:
        from .multi_agent import MultiAgentCoordinator

        coordinator = MultiAgentCoordinator(client, model)
        system_prompt = build_system_prompt()
        coordinator.run_multi_agent_loop(system_prompt, conversation)
        return

    while True:
        try:
            user_input = console.input("[bold cyan]You:[/] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/]")
            break

        if not user_input:
            continue

        conversation.append({
            "role": "user",
            "content": user_input
        })

        # Agent loop - keep processing until no more tool calls
        while True:
            # Stream response
            content, tool_calls = stream_response(client, model, conversation, TOOLS)

            # Check if there are tool calls
            if tool_calls:
                # Add assistant message with tool calls to conversation
                conversation.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls
                })

                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments

                    print_tool(tool_name, tool_args)

                    if tool_name not in TOOL_REGISTRY:
                        result = {"error": f"Unknown tool: {tool_name}"}
                    else:
                        # Determine if confirmation is needed
                        needs_confirmation = False
                        confirm_content = ""

                        if tool_name in DANGEROUS_TOOLS:
                            needs_confirmation = True
                            if tool_name == "run_bash_tool":
                                confirm_content = tool_args.get("command", "")
                            elif tool_name == "run_python_tool":
                                confirm_content = tool_args.get("code", "")
                            elif tool_name == "install_deps_tool":
                                confirm_content = f"Install dependencies in {tool_args.get('path', '.')}"
                            elif tool_name == "smart_commit_tool":
                                files = tool_args.get("files", ["all changes"])
                                custom_msg = tool_args.get("custom_message")
                                confirm_content = f"Commit {', '.join(files[:3])}"
                                if custom_msg:
                                    confirm_content += f"\nMessage: {custom_msg[:100]}"
                        elif tool_name in CONDITIONAL_TOOLS:
                            # Check condition for conditional tools
                            check_func = CONDITIONAL_TOOLS[tool_name]
                            if tool_name == "sqlite_tool":
                                query = tool_args.get("query", "")
                                if check_func(query):
                                    needs_confirmation = True
                                    confirm_content = query
                            elif tool_name == "git_tool":
                                action = tool_args.get("action", "")
                                if check_func(action):
                                    needs_confirmation = True
                                    # Build confirmation content based on action
                                    if action == "commit":
                                        confirm_content = f"git commit -m \"{tool_args.get('message', '')[:100]}\""
                                    elif action == "push":
                                        confirm_content = f"git push {tool_args.get('remote', 'origin')} {tool_args.get('branch', '')}"
                                    elif action == "pull":
                                        confirm_content = f"git pull {tool_args.get('remote', 'origin')} {tool_args.get('branch', '')}"
                                    elif action == "merge":
                                        confirm_content = f"git merge {tool_args.get('branch', '')}"
                                    elif action == "checkout":
                                        confirm_content = f"git checkout {tool_args.get('branch', '')}"
                                    elif action == "reset":
                                        confirm_content = f"git reset --soft HEAD"
                                    else:
                                        confirm_content = f"git {action}"

                        if needs_confirmation:
                            approved, sudo_password = confirm_execution(tool_name, confirm_content)
                            if approved:
                                with thinking_spinner("Executing..."):
                                    func = TOOL_REGISTRY[tool_name]
                                    # Pass sudo_password to run_bash_tool if provided
                                    if tool_name == "run_bash_tool" and sudo_password:
                                        tool_args["sudo_password"] = sudo_password
                                    result = func(**tool_args)
                            else:
                                result = {"status": "cancelled", "message": "User cancelled execution"}
                        else:
                            func = TOOL_REGISTRY[tool_name]
                            result = func(**tool_args)

                    # Add tool result to conversation
                    conversation.append({
                        "role": "tool",
                        "content": json.dumps(result)
                    })
            else:
                # No tool calls - add to conversation and break
                conversation.append({
                    "role": "assistant",
                    "content": content
                })
                break

        # After completing the exchange, trim and save conversation
        conversation = trim_conversation(conversation)
        save_session(session_id, conversation)
