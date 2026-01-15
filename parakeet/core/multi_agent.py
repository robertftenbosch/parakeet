"""Multi-agent coordination system."""

import json
from typing import Any, Optional
from ollama import Client

from ..ui import console, print_tool, thinking_spinner
from .agents import (
    OrchestratorAgent,
    CodingAgent,
    ResearchAgent,
    TestingAgent,
    BioinformaticsAgent,
)
from .agents.base import AgentTask, AgentResult
from .tools import TOOL_REGISTRY, DANGEROUS_TOOLS, CONDITIONAL_TOOLS, propose_plan_tool
from .agent import confirm_execution, stream_response


class MultiAgentCoordinator:
    """Coordinates multiple specialist agents."""

    def __init__(self, client: Client, model: str):
        """Initialize the multi-agent system.

        Args:
            client: Ollama client
            model: Model name to use for all agents
        """
        self.client = client
        self.model = model

        # Initialize all agents
        self.orchestrator = OrchestratorAgent(client, model)
        self.agents = {
            "coding": CodingAgent(client, model),
            "research": ResearchAgent(client, model),
            "testing": TestingAgent(client, model),
            "bioinformatics": BioinformaticsAgent(client, model),
        }

        # Add orchestrator to agents dict
        self.agents["orchestrator"] = self.orchestrator

        # Track active agent conversations
        self.agent_conversations: dict[str, list[dict[str, Any]]] = {}

    def get_agent(self, agent_name: str):
        """Get an agent by name."""
        return self.agents.get(agent_name)

    def list_agents(self) -> list[dict[str, Any]]:
        """List all available agents and their info."""
        return [agent.get_info() for agent in self.agents.values()]

    def delegate_task_tool(self, agent: str, task: str, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Tool for orchestrator to delegate tasks to specialist agents.

        Args:
            agent: Name of the agent to delegate to (coding, research, testing, bioinformatics)
            task: Description of the task
            context: Optional context dict

        Returns:
            Dict with task result
        """
        # Show delegation message
        console.print()
        console.print(f"[bold magenta]→ Delegating to [cyan]{agent}[/] agent[/]")
        console.print(f"  [dim]Task: {task[:100]}{'...' if len(task) > 100 else ''}[/]")
        console.print()

        target_agent = self.get_agent(agent)
        if not target_agent:
            return {"error": f"Unknown agent: {agent}"}

        # Initialize conversation for this agent if needed
        if agent not in self.agent_conversations:
            self.agent_conversations[agent] = [{
                "role": "system",
                "content": target_agent.system_prompt
            }]

        # Add task as user message
        task_message = task
        if context:
            task_message += f"\n\nContext: {json.dumps(context, indent=2)}"

        self.agent_conversations[agent].append({
            "role": "user",
            "content": task_message
        })

        # Execute agent with its tools
        result = self._execute_agent_with_tools(agent, target_agent)

        # Show completion message
        console.print(f"[bold green]✓ {agent} agent completed[/]")
        console.print()

        return {
            "agent": agent,
            "task": task,
            "result": result,
            "success": True
        }

    def _execute_agent_with_tools(self, agent_name: str, agent) -> str:
        """Execute an agent with its tools in a loop until completion.

        Args:
            agent_name: Name of the agent
            agent: Agent instance

        Returns:
            Final response content
        """
        conversation = self.agent_conversations[agent_name]
        final_response = ""

        # Create agent-specific spinner label
        agent_display = agent.role  # e.g., "Coding Specialist"
        spinner_label = f"{agent_display} working..."

        # Agent loop - keep processing until no more tool calls
        while True:
            # Stream response with agent-specific spinner
            content, tool_calls = stream_response(
                self.client,
                self.model,
                conversation,
                agent.tools,
                spinner_label=spinner_label
            )

            if tool_calls:
                # Add assistant message with tool calls
                conversation.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls
                })

                # Execute tool calls
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments

                    # Ensure tool_args is a dict
                    if not isinstance(tool_args, dict):
                        console.print(f"  [yellow][{agent_name}] Warning: Tool arguments are not a dict, got {type(tool_args)}[/]")
                        tool_args = {}

                    console.print(f"  [dim][{agent_name}][/] ", end="")
                    print_tool(tool_name, tool_args)

                    if tool_name not in TOOL_REGISTRY:
                        # Unknown tool - provide helpful error
                        available_tools = ", ".join(sorted(TOOL_REGISTRY.keys())[:10])
                        result = {
                            "error": f"Unknown tool: {tool_name}",
                            "message": f"Tool '{tool_name}' is not available. Try using one of the available tools.",
                            "available_tools_sample": available_tools
                        }
                        console.print(f"  [red][{agent_name}] Error: Unknown tool '{tool_name}'[/]")
                    else:
                        # Handle confirmations same as main agent
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

                    # Add tool result
                    conversation.append({
                        "role": "tool",
                        "content": json.dumps(result)
                    })
            else:
                # No tool calls - agent is done
                conversation.append({
                    "role": "assistant",
                    "content": content
                })
                final_response = content
                break

        return final_response

    def run_multi_agent_loop(self, system_prompt: str, initial_conversation: list[dict[str, Any]]):
        """Run the multi-agent orchestrator loop.

        Args:
            system_prompt: System prompt with project context
            initial_conversation: Initial conversation history
        """
        console.print("\n[bold green]Multi-Agent Mode Enabled[/]")
        console.print(f"[dim]Orchestrator:[/] Coordinating {len(self.agents) - 1} specialist agents")
        console.print()

        # Show available agents
        for agent_name, agent in self.agents.items():
            if agent_name != "orchestrator":
                console.print(f"  • [cyan]{agent.role}[/] ({agent_name})")
        console.print()

        # Initialize orchestrator conversation with system prompt and context
        orchestrator_system = self.orchestrator.system_prompt
        if system_prompt:
            orchestrator_system += f"\n\n## Project Context\n\n{system_prompt}"

        orchestrator_conversation = [{
            "role": "system",
            "content": orchestrator_system
        }]

        # Add orchestrator-specific tools dynamically
        orchestrator_tools = [propose_plan_tool, self.delegate_task_tool]

        while True:
            try:
                user_input = console.input("[bold cyan]You:[/] ").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Goodbye![/]")
                break

            if not user_input:
                continue

            orchestrator_conversation.append({
                "role": "user",
                "content": user_input
            })

            # Orchestrator loop with delegation
            while True:
                # Stream orchestrator response with custom spinner
                content, tool_calls = stream_response(
                    self.client,
                    self.model,
                    orchestrator_conversation,
                    orchestrator_tools,
                    spinner_label="Orchestrator planning..."
                )

                if tool_calls:
                    # Orchestrator is delegating
                    orchestrator_conversation.append({
                        "role": "assistant",
                        "content": content,
                        "tool_calls": tool_calls
                    })

                    for tool_call in tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = tool_call.function.arguments

                        # Execute delegation
                        if tool_name == "delegate_task_tool":
                            result = self.delegate_task_tool(**tool_args)
                        else:
                            result = {"error": f"Unknown orchestrator tool: {tool_name}"}

                        # Add delegation result to orchestrator conversation
                        orchestrator_conversation.append({
                            "role": "tool",
                            "content": json.dumps(result)
                        })
                else:
                    # Orchestrator is done
                    orchestrator_conversation.append({
                        "role": "assistant",
                        "content": content
                    })
                    break
