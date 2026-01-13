"""Tests for Parakeet agent."""

import json
from unittest.mock import MagicMock, patch, call

import pytest

from parakeet.core import agent


class TestBuildSystemPrompt:
    """Tests for build_system_prompt."""

    def test_basic_prompt_without_context(self):
        """Returns base system prompt when no project context."""
        with patch("parakeet.core.agent.load_project_context", return_value=None):
            result = agent.build_system_prompt()

        assert "coding assistant" in result
        assert "biotech" in result.lower() or "robotics" in result.lower()
        assert "Project Context" not in result

    def test_prompt_with_project_context(self):
        """Appends project context to system prompt."""
        context = "This is a bioinformatics project using BioPython."

        with patch("parakeet.core.agent.load_project_context", return_value=context):
            result = agent.build_system_prompt()

        assert "Project Context" in result
        assert context in result


class TestConfirmExecution:
    """Tests for confirm_execution."""

    def test_confirm_yes(self):
        """Returns True when user confirms with 'y'."""
        with patch("parakeet.core.agent.console") as mock_console:
            mock_console.input.return_value = "y"
            result = agent.confirm_execution("run_bash_tool", "echo hello")

        assert result is True

    def test_confirm_yes_uppercase(self):
        """Returns True when user confirms with 'Y'."""
        with patch("parakeet.core.agent.console") as mock_console:
            mock_console.input.return_value = "Y"
            result = agent.confirm_execution("run_bash_tool", "echo hello")

        assert result is True

    def test_confirm_yes_full(self):
        """Returns True when user confirms with 'yes'."""
        with patch("parakeet.core.agent.console") as mock_console:
            mock_console.input.return_value = "yes"
            result = agent.confirm_execution("run_bash_tool", "echo hello")

        assert result is True

    def test_confirm_no(self):
        """Returns False when user declines with 'n'."""
        with patch("parakeet.core.agent.console") as mock_console:
            mock_console.input.return_value = "n"
            result = agent.confirm_execution("run_bash_tool", "echo hello")

        assert result is False

    def test_confirm_empty(self):
        """Returns False when user presses enter (empty input)."""
        with patch("parakeet.core.agent.console") as mock_console:
            mock_console.input.return_value = ""
            result = agent.confirm_execution("run_bash_tool", "echo hello")

        assert result is False

    def test_confirm_keyboard_interrupt(self):
        """Returns False on keyboard interrupt."""
        with patch("parakeet.core.agent.console") as mock_console:
            mock_console.input.side_effect = KeyboardInterrupt()
            result = agent.confirm_execution("run_bash_tool", "echo hello")

        assert result is False

    def test_confirm_eof(self):
        """Returns False on EOF."""
        with patch("parakeet.core.agent.console") as mock_console:
            mock_console.input.side_effect = EOFError()
            result = agent.confirm_execution("run_bash_tool", "echo hello")

        assert result is False


class TestStreamResponse:
    """Tests for stream_response."""

    def test_stream_content_only(self):
        """Streams content without tool calls."""
        mock_client = MagicMock()

        # Create mock chunks
        chunk1 = MagicMock()
        chunk1.message.content = "Hello "
        chunk1.message.tool_calls = None

        chunk2 = MagicMock()
        chunk2.message.content = "World!"
        chunk2.message.tool_calls = None

        mock_client.chat.return_value = [chunk1, chunk2]

        with patch("parakeet.core.agent.console"):
            content, tool_calls = agent.stream_response(
                mock_client, "llama3.2", [], []
            )

        assert content == "Hello World!"
        assert tool_calls == []

    def test_stream_with_tool_calls(self):
        """Collects tool calls from stream."""
        mock_client = MagicMock()

        # Create mock tool call
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "read_file_tool"
        mock_tool_call.function.arguments = {"path": "test.py"}

        chunk = MagicMock()
        chunk.message.content = ""
        chunk.message.tool_calls = [mock_tool_call]

        mock_client.chat.return_value = [chunk]

        with patch("parakeet.core.agent.console"):
            content, tool_calls = agent.stream_response(
                mock_client, "llama3.2", [], []
            )

        assert content == ""
        assert len(tool_calls) == 1
        assert tool_calls[0].function.name == "read_file_tool"

    def test_stream_mixed_content_and_tools(self):
        """Handles both content and tool calls."""
        mock_client = MagicMock()

        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "list_files_tool"
        mock_tool_call.function.arguments = {"path": "."}

        chunk1 = MagicMock()
        chunk1.message.content = "Let me check "
        chunk1.message.tool_calls = None

        chunk2 = MagicMock()
        chunk2.message.content = "the files."
        chunk2.message.tool_calls = [mock_tool_call]

        mock_client.chat.return_value = [chunk1, chunk2]

        with patch("parakeet.core.agent.console"):
            content, tool_calls = agent.stream_response(
                mock_client, "llama3.2", [], []
            )

        assert content == "Let me check the files."
        assert len(tool_calls) == 1

    def test_stream_empty_response(self):
        """Handles empty response."""
        mock_client = MagicMock()
        mock_client.chat.return_value = []

        with patch("parakeet.core.agent.console"):
            content, tool_calls = agent.stream_response(
                mock_client, "llama3.2", [], []
            )

        assert content == ""
        assert tool_calls == []


class TestSystemPromptContent:
    """Tests for SYSTEM_PROMPT content."""

    def test_contains_bioinformatics(self):
        """System prompt includes bioinformatics expertise."""
        assert "BioPython" in agent.SYSTEM_PROMPT or "bioinformatics" in agent.SYSTEM_PROMPT.lower()

    def test_contains_robotics(self):
        """System prompt includes robotics expertise."""
        assert "ROS2" in agent.SYSTEM_PROMPT or "robotics" in agent.SYSTEM_PROMPT.lower()

    def test_contains_tools_mention(self):
        """System prompt mentions available tools."""
        assert "tool" in agent.SYSTEM_PROMPT.lower()

    def test_contains_guidelines(self):
        """System prompt includes coding guidelines."""
        assert "type hint" in agent.SYSTEM_PROMPT.lower() or "docstring" in agent.SYSTEM_PROMPT.lower()
