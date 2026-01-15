"""Base agent class for multi-agent system."""

from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass

from ollama import Client


class AgentCapability(Enum):
    """Agent capability types."""
    CODE_WRITING = "code_writing"
    CODE_ANALYSIS = "code_analysis"
    RESEARCH = "research"
    TESTING = "testing"
    BIOINFORMATICS = "bioinformatics"
    PLANNING = "planning"
    FILE_OPERATIONS = "file_operations"
    SHELL_EXECUTION = "shell_execution"


@dataclass
class AgentTask:
    """A task for an agent to execute."""
    task_id: str
    description: str
    context: dict[str, Any]
    requester: Optional[str] = None  # Which agent requested this task


@dataclass
class AgentResult:
    """Result from agent task execution."""
    task_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    agent_name: str = ""


class Agent:
    """Base agent class with common functionality."""

    def __init__(
        self,
        name: str,
        role: str,
        capabilities: list[AgentCapability],
        tools: list,
        client: Client,
        model: str
    ):
        """Initialize agent.

        Args:
            name: Agent identifier (e.g., "coding", "research")
            role: Human-readable role description
            capabilities: List of agent capabilities
            tools: List of tool functions this agent can use
            client: Ollama client
            model: Model name to use
        """
        self.name = name
        self.role = role
        self.capabilities = capabilities
        self.tools = tools
        self.client = client
        self.model = model
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build system prompt for this agent. Override in subclasses."""
        return f"""You are a {self.role}.

Your capabilities: {', '.join(c.value for c in self.capabilities)}

You have access to tools to help you complete your tasks.
Focus on your specialty and provide high-quality results.
"""

    def can_handle(self, task: AgentTask) -> bool:
        """Check if this agent can handle a given task.

        Args:
            task: Task to evaluate

        Returns:
            True if agent can handle this task
        """
        # Default: check if task mentions any of our capabilities
        task_lower = task.description.lower()

        for cap in self.capabilities:
            if cap.value in task_lower:
                return True

        return False

    def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a task.

        Args:
            task: Task to execute

        Returns:
            AgentResult with execution results
        """
        # To be implemented in coordination system
        raise NotImplementedError("Task execution handled by multi-agent coordinator")

    def get_info(self) -> dict[str, Any]:
        """Get agent information."""
        return {
            "name": self.name,
            "role": self.role,
            "capabilities": [c.value for c in self.capabilities],
            "tool_count": len(self.tools),
            "model": self.model
        }

    def __repr__(self) -> str:
        return f"<Agent: {self.name} ({self.role})>"
