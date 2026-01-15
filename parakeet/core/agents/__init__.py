"""Multi-agent system for Parakeet."""

from .base import Agent, AgentCapability
from .coding import CodingAgent
from .research import ResearchAgent
from .testing import TestingAgent
from .bioinformatics import BioinformaticsAgent
from .orchestrator import OrchestratorAgent

__all__ = [
    "Agent",
    "AgentCapability",
    "CodingAgent",
    "ResearchAgent",
    "TestingAgent",
    "BioinformaticsAgent",
    "OrchestratorAgent",
]
