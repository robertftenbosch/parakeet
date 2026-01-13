"""Agent loop for Parakeet."""

import json
from typing import Any

from ollama import Client

from ..ui import console, print_tool, thinking_spinner
from .config import load_project_context
from .tools import TOOLS, TOOL_REGISTRY, DANGEROUS_TOOLS

SYSTEM_PROMPT = """You are a coding assistant specialized in biotech and robotics applications.

## Your Expertise

### Bioinformatics
- BioPython for sequence analysis (SeqIO, Seq, SeqRecord)
- FASTA/FASTQ/GenBank file parsing
- Sequence alignment (pairwise, multiple sequence alignment)
- BLAST searches and result parsing
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

## Guidelines
- Use appropriate libraries for the domain
- Follow ROS2 conventions for robotics code
- Use BioPython idioms for bioinformatics
- Write type hints for all functions
- Include docstrings with examples

You have access to tools for file operations and code execution. Use them when needed to complete tasks.
"""


def build_system_prompt() -> str:
    """Build system prompt with optional project context."""
    prompt = SYSTEM_PROMPT

    project_context = load_project_context()
    if project_context:
        prompt += f"\n\n## Project Context\n\n{project_context}"

    return prompt


def confirm_execution(tool_name: str, content: str) -> bool:
    """Ask user to confirm before executing code."""
    console.print(f"\n[bold red]Warning:[/] {tool_name} wants to execute:")
    console.print("[dim]" + "─" * 50 + "[/]")
    console.print(content)
    console.print("[dim]" + "─" * 50 + "[/]")
    try:
        response = console.input("[bold red]Execute? [y/N]:[/] ").strip().lower()
        return response in ('y', 'yes', 'j', 'ja')
    except (KeyboardInterrupt, EOFError):
        return False


def stream_response(client: Client, model: str, conversation: list[dict[str, Any]], tools: list):
    """Stream LLM response and collect content/tool calls."""
    full_content = ""
    tool_calls = []
    first_chunk = True

    for chunk in client.chat(
        model=model,
        messages=conversation,
        tools=tools,
        stream=True,
    ):
        # Handle content streaming
        if chunk.message.content:
            if first_chunk:
                console.print("[bold blue]Assistant:[/] ", end="")
                first_chunk = False
            console.print(chunk.message.content, end="", highlight=False)
            full_content += chunk.message.content

        # Collect tool calls
        if chunk.message.tool_calls:
            tool_calls.extend(chunk.message.tool_calls)

    # Print newline if we streamed content
    if full_content:
        console.print()

    return full_content, tool_calls


def run_agent_loop(client: Client, model: str) -> None:
    """Run the main agent interaction loop."""
    console.print(f"[bold green]Parakeet[/] v0.1.0")
    console.print(f"[dim]Model:[/] {model}")
    console.print(f"[dim]Tools:[/] {', '.join(t.__name__ for t in TOOLS)}")

    # Check for project context
    project_context = load_project_context()
    if project_context:
        console.print(f"[dim]Project:[/] .parakeet/context.md loaded")

    console.print()
    console.print("[dim]Type your message or Ctrl+C to exit[/]")
    console.print()

    system_prompt = build_system_prompt()
    conversation = [{
        "role": "system",
        "content": system_prompt
    }]

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
                        # Check if confirmation is needed
                        if tool_name in DANGEROUS_TOOLS:
                            # Format the content for confirmation
                            if tool_name == "run_bash_tool":
                                confirm_content = tool_args.get("command", "")
                            else:  # run_python_tool
                                confirm_content = tool_args.get("code", "")

                            if confirm_execution(tool_name, confirm_content):
                                with thinking_spinner("Executing..."):
                                    func = TOOL_REGISTRY[tool_name]
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
