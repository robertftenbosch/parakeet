"""Tests for Parakeet CLI commands."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from parakeet.main import app
from parakeet.cli import init_cmd, config_cmd


runner = CliRunner()


class TestMainCLI:
    """Tests for main CLI entry point."""

    def test_help(self):
        """Shows help message."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "parakeet" in result.output.lower() or "AI coding agent" in result.output

    def test_version(self):
        """Shows version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "parakeet" in result.output.lower()

    def test_subcommand_help_chat(self):
        """Shows help for chat subcommand."""
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "chat" in result.output.lower() or "interactive" in result.output.lower()

    def test_subcommand_help_config(self):
        """Shows help for config subcommand."""
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "config" in result.output.lower()

    def test_subcommand_help_init(self):
        """Shows help for init subcommand."""
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "init" in result.output.lower()


class TestInitCommand:
    """Tests for init command."""

    def test_init_creates_directory(self, temp_dir):
        """Creates .parakeet directory."""
        result = runner.invoke(app, ["init", str(temp_dir)])

        assert result.exit_code == 0
        assert (temp_dir / ".parakeet").exists()

    def test_init_creates_context_file(self, temp_dir):
        """Creates context.md file."""
        runner.invoke(app, ["init", str(temp_dir)])

        context_file = temp_dir / ".parakeet" / "context.md"
        assert context_file.exists()
        content = context_file.read_text()
        assert "Project Context" in content

    def test_init_creates_config_file(self, temp_dir):
        """Creates config.json file."""
        runner.invoke(app, ["init", str(temp_dir)])

        config_file = temp_dir / ".parakeet" / "config.json"
        assert config_file.exists()
        config = json.loads(config_file.read_text())
        assert "project_name" in config

    def test_init_creates_gitignore(self, temp_dir):
        """Creates .gitignore file."""
        runner.invoke(app, ["init", str(temp_dir)])

        gitignore = temp_dir / ".parakeet" / ".gitignore"
        assert gitignore.exists()
        assert "config.json" in gitignore.read_text()

    def test_init_fails_if_already_initialized(self, temp_dir):
        """Fails if project already initialized."""
        # First init
        runner.invoke(app, ["init", str(temp_dir)])

        # Second init should fail
        result = runner.invoke(app, ["init", str(temp_dir)])
        assert result.exit_code == 1

    def test_init_current_directory(self, temp_dir, monkeypatch):
        """Initializes current directory by default."""
        monkeypatch.chdir(temp_dir)
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert (temp_dir / ".parakeet").exists()


class TestConfigCommand:
    """Tests for config command."""

    def test_config_show_empty(self, monkeypatch, temp_dir):
        """Shows empty config when no config file."""
        from parakeet.core import config as config_module

        monkeypatch.setattr(config_module, "CONFIG_FILE", temp_dir / "config.json")
        monkeypatch.setattr(config_module, "CONFIG_DIR", temp_dir)

        result = runner.invoke(app, ["config", "--show"])

        assert result.exit_code == 0
        assert "Configuration" in result.output

    def test_config_show_with_values(self, monkeypatch, temp_dir):
        """Shows config values when config file exists."""
        from parakeet.core import config as config_module

        config_file = temp_dir / "config.json"
        config_file.write_text(json.dumps({
            "ollama_host": "http://test:11434",
            "ollama_model": "test-model"
        }))

        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)
        monkeypatch.setattr(config_module, "CONFIG_DIR", temp_dir)

        result = runner.invoke(app, ["config", "--show"])

        assert result.exit_code == 0
        assert "test:11434" in result.output or "test-model" in result.output

    def test_config_reset(self, monkeypatch, temp_dir):
        """Resets config by deleting config file."""
        from parakeet.core import config as config_module
        from parakeet.cli import config_cmd

        config_file = temp_dir / "config.json"
        config_file.write_text(json.dumps({"key": "value"}))

        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)
        monkeypatch.setattr(config_module, "CONFIG_DIR", temp_dir)
        # Also patch in config_cmd where it's imported
        monkeypatch.setattr(config_cmd, "CONFIG_FILE", config_file)

        result = runner.invoke(app, ["config", "--reset"])

        assert result.exit_code == 0
        assert not config_file.exists()

    def test_config_reset_no_file(self, monkeypatch, temp_dir):
        """Handles reset when no config file exists."""
        from parakeet.core import config as config_module

        monkeypatch.setattr(config_module, "CONFIG_FILE", temp_dir / "nonexistent.json")
        monkeypatch.setattr(config_module, "CONFIG_DIR", temp_dir)

        result = runner.invoke(app, ["config", "--reset"])

        assert result.exit_code == 0

    def test_config_set_host(self, monkeypatch, temp_dir):
        """Sets host in config."""
        from parakeet.core import config as config_module

        monkeypatch.setattr(config_module, "CONFIG_FILE", temp_dir / "config.json")
        monkeypatch.setattr(config_module, "CONFIG_DIR", temp_dir)

        with patch("parakeet.core.config.Client"):
            result = runner.invoke(app, ["config", "--host", "http://newhost:11434"])

        assert result.exit_code == 0

    def test_config_set_model(self, monkeypatch, temp_dir):
        """Sets model in config."""
        from parakeet.core import config as config_module

        monkeypatch.setattr(config_module, "CONFIG_FILE", temp_dir / "config.json")
        monkeypatch.setattr(config_module, "CONFIG_DIR", temp_dir)

        with patch("parakeet.core.config.Client"):
            result = runner.invoke(app, ["config", "--model", "newmodel"])

        assert result.exit_code == 0


class TestChatCommand:
    """Tests for chat command."""

    def test_chat_starts_with_mocked_agent(self, monkeypatch, temp_dir):
        """Chat command starts agent loop."""
        from parakeet.core import config as config_module

        monkeypatch.setattr(config_module, "CONFIG_FILE", temp_dir / "config.json")
        monkeypatch.setattr(config_module, "CONFIG_DIR", temp_dir)

        with patch("parakeet.cli.chat.Client"), \
             patch("parakeet.cli.chat.run_agent_loop") as mock_agent, \
             patch("parakeet.core.config.Client"):
            result = runner.invoke(app, ["chat", "--host", "http://test:11434", "--model", "test"])

        mock_agent.assert_called_once()

    def test_chat_passes_options(self, monkeypatch, temp_dir):
        """Chat command passes host and model to agent."""
        from parakeet.core import config as config_module

        monkeypatch.setattr(config_module, "CONFIG_FILE", temp_dir / "config.json")
        monkeypatch.setattr(config_module, "CONFIG_DIR", temp_dir)

        with patch("parakeet.cli.chat.Client") as mock_client_class, \
             patch("parakeet.cli.chat.run_agent_loop") as mock_agent, \
             patch("parakeet.core.config.Client"):
            result = runner.invoke(app, [
                "chat",
                "--host", "http://custom:11434",
                "--model", "custom-model"
            ])

        # Verify the Client was called with the right host
        mock_client_class.assert_called_with(host="http://custom:11434")
        # Verify run_agent_loop was called with the model
        mock_agent.assert_called_once()
        args = mock_agent.call_args
        assert args[0][1] == "custom-model"  # Second argument is model
