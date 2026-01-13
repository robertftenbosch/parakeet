"""Tests for Parakeet configuration."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from parakeet.core import config


class TestLoadConfig:
    """Tests for load_config."""

    def test_load_config_file_not_exists(self, monkeypatch, temp_dir):
        """Returns empty dict when config file doesn't exist."""
        monkeypatch.setattr(config, "CONFIG_FILE", temp_dir / "nonexistent.json")
        result = config.load_config()
        assert result == {}

    def test_load_config_valid_json(self, monkeypatch, temp_dir):
        """Loads config from valid JSON file."""
        config_file = temp_dir / "config.json"
        config_data = {"ollama_host": "http://localhost:11434", "ollama_model": "llama3.2"}
        config_file.write_text(json.dumps(config_data))

        monkeypatch.setattr(config, "CONFIG_FILE", config_file)
        result = config.load_config()

        assert result == config_data

    def test_load_config_invalid_json(self, monkeypatch, temp_dir):
        """Returns empty dict for invalid JSON."""
        config_file = temp_dir / "config.json"
        config_file.write_text("not valid json {{{")

        monkeypatch.setattr(config, "CONFIG_FILE", config_file)
        result = config.load_config()

        assert result == {}


class TestSaveConfig:
    """Tests for save_config."""

    def test_save_config_creates_directory(self, monkeypatch, temp_dir):
        """Creates config directory if it doesn't exist."""
        config_dir = temp_dir / "new_dir"
        config_file = config_dir / "config.json"

        monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config, "CONFIG_FILE", config_file)

        config.save_config({"key": "value"})

        assert config_dir.exists()
        assert config_file.exists()

    def test_save_config_writes_json(self, monkeypatch, temp_dir):
        """Saves config as formatted JSON."""
        config_file = temp_dir / "config.json"
        monkeypatch.setattr(config, "CONFIG_DIR", temp_dir)
        monkeypatch.setattr(config, "CONFIG_FILE", config_file)

        config_data = {"ollama_host": "http://localhost:11434", "ollama_model": "llama3.2"}
        config.save_config(config_data)

        saved = json.loads(config_file.read_text())
        assert saved == config_data

    def test_save_config_overwrites_existing(self, monkeypatch, temp_dir):
        """Overwrites existing config file."""
        config_file = temp_dir / "config.json"
        config_file.write_text(json.dumps({"old": "data"}))

        monkeypatch.setattr(config, "CONFIG_DIR", temp_dir)
        monkeypatch.setattr(config, "CONFIG_FILE", config_file)

        config.save_config({"new": "data"})

        saved = json.loads(config_file.read_text())
        assert saved == {"new": "data"}


class TestLoadProjectContext:
    """Tests for load_project_context."""

    def test_load_context_file_exists(self, monkeypatch, temp_dir):
        """Loads context from .parakeet/context.md."""
        context_dir = temp_dir / ".parakeet"
        context_dir.mkdir()
        context_file = context_dir / "context.md"
        context_file.write_text("# Project Context\n\nThis is my project.")

        monkeypatch.chdir(temp_dir)
        result = config.load_project_context()

        assert result == "# Project Context\n\nThis is my project."

    def test_load_context_file_not_exists(self, monkeypatch, temp_dir):
        """Returns None when context file doesn't exist."""
        monkeypatch.chdir(temp_dir)
        result = config.load_project_context()

        assert result is None

    def test_load_context_directory_not_exists(self, monkeypatch, temp_dir):
        """Returns None when .parakeet directory doesn't exist."""
        monkeypatch.chdir(temp_dir)
        result = config.load_project_context()

        assert result is None


class TestListAvailableModels:
    """Tests for list_available_models."""

    def test_list_models_success(self):
        """Returns list of model names."""
        mock_client = MagicMock()
        mock_client.list.return_value = {
            "models": [
                {"name": "llama3.2"},
                {"name": "mistral"},
                {"name": "codellama"},
            ]
        }

        result = config.list_available_models(mock_client)

        assert result == ["llama3.2", "mistral", "codellama"]

    def test_list_models_empty(self):
        """Returns empty list when no models available."""
        mock_client = MagicMock()
        mock_client.list.return_value = {"models": []}

        result = config.list_available_models(mock_client)

        assert result == []

    def test_list_models_error(self):
        """Returns empty list on error."""
        mock_client = MagicMock()
        mock_client.list.side_effect = Exception("Connection error")

        result = config.list_available_models(mock_client)

        assert result == []


class TestGetOllamaConfig:
    """Tests for get_ollama_config."""

    def test_config_from_arguments(self, monkeypatch, temp_dir):
        """Uses host and model from function arguments."""
        monkeypatch.setattr(config, "CONFIG_DIR", temp_dir)
        monkeypatch.setattr(config, "CONFIG_FILE", temp_dir / "config.json")

        with patch("parakeet.core.config.Client"):
            host, model = config.get_ollama_config(
                host="http://custom:11434",
                model="custom-model",
                interactive=False
            )

        assert host == "http://custom:11434"
        assert model == "custom-model"

    def test_config_from_config_file(self, monkeypatch, temp_dir):
        """Uses host and model from config file."""
        config_file = temp_dir / "config.json"
        config_file.write_text(json.dumps({
            "ollama_host": "http://saved:11434",
            "ollama_model": "saved-model"
        }))

        monkeypatch.setattr(config, "CONFIG_DIR", temp_dir)
        monkeypatch.setattr(config, "CONFIG_FILE", config_file)

        with patch("parakeet.core.config.Client"):
            host, model = config.get_ollama_config(interactive=False)

        assert host == "http://saved:11434"
        assert model == "saved-model"

    def test_config_from_environment(self, monkeypatch, temp_dir):
        """Uses host and model from environment variables."""
        monkeypatch.setattr(config, "CONFIG_DIR", temp_dir)
        monkeypatch.setattr(config, "CONFIG_FILE", temp_dir / "config.json")
        monkeypatch.setenv("OLLAMA_HOST", "http://env:11434")
        monkeypatch.setenv("OLLAMA_MODEL", "env-model")

        with patch("parakeet.core.config.Client"):
            host, model = config.get_ollama_config(interactive=False)

        assert host == "http://env:11434"
        assert model == "env-model"

    def test_config_default_fallback(self, monkeypatch, temp_dir):
        """Uses default values when nothing else specified."""
        monkeypatch.setattr(config, "CONFIG_DIR", temp_dir)
        monkeypatch.setattr(config, "CONFIG_FILE", temp_dir / "config.json")
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)

        with patch("parakeet.core.config.Client"):
            host, model = config.get_ollama_config(interactive=False)

        assert host == "http://localhost:11434"
        assert model == "llama3.2"

    def test_config_priority_args_over_file(self, monkeypatch, temp_dir):
        """Function arguments take priority over config file."""
        config_file = temp_dir / "config.json"
        config_file.write_text(json.dumps({
            "ollama_host": "http://saved:11434",
            "ollama_model": "saved-model"
        }))

        monkeypatch.setattr(config, "CONFIG_DIR", temp_dir)
        monkeypatch.setattr(config, "CONFIG_FILE", config_file)

        with patch("parakeet.core.config.Client"):
            host, model = config.get_ollama_config(
                host="http://override:11434",
                model="override-model",
                interactive=False
            )

        assert host == "http://override:11434"
        assert model == "override-model"


class TestSelectModelInteractive:
    """Tests for select_model_interactive."""

    def test_select_model_no_models(self):
        """Returns None when no models available."""
        mock_client = MagicMock()
        mock_client.list.return_value = {"models": []}

        result = config.select_model_interactive(mock_client)

        assert result is None

    def test_select_model_valid_choice(self):
        """Returns selected model name."""
        mock_client = MagicMock()
        mock_client.list.return_value = {
            "models": [{"name": "llama3.2"}, {"name": "mistral"}]
        }

        # Patch console in parakeet.ui where config.py imports from
        import parakeet.ui as ui_module
        with patch.object(ui_module, "console") as mock_console:
            mock_console.input.return_value = "1"
            result = config.select_model_interactive(mock_client)

        assert result == "llama3.2"

    def test_select_model_second_choice(self):
        """Returns second model when user selects 2."""
        mock_client = MagicMock()
        mock_client.list.return_value = {
            "models": [{"name": "llama3.2"}, {"name": "mistral"}]
        }

        import parakeet.ui as ui_module
        with patch.object(ui_module, "console") as mock_console:
            mock_console.input.return_value = "2"
            result = config.select_model_interactive(mock_client)

        assert result == "mistral"

    def test_select_model_keyboard_interrupt(self):
        """Returns None on keyboard interrupt."""
        mock_client = MagicMock()
        mock_client.list.return_value = {
            "models": [{"name": "llama3.2"}]
        }

        import parakeet.ui as ui_module
        with patch.object(ui_module, "console") as mock_console:
            mock_console.input.side_effect = KeyboardInterrupt()
            result = config.select_model_interactive(mock_client)

        assert result is None
