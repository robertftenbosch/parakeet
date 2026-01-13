"""Tests for Parakeet environment management."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from parakeet.core import environment


class TestDetectPackageManager:
    """Tests for detect_package_manager."""

    def test_detect_uv(self):
        """Detects uv when available."""
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda x: "/usr/bin/uv" if x == "uv" else None
            result = environment.detect_package_manager()
        assert result == "uv"

    def test_detect_conda(self):
        """Detects conda when uv not available."""
        with patch("shutil.which") as mock_which:
            def which_side_effect(cmd):
                if cmd == "conda":
                    return "/usr/bin/conda"
                return None
            mock_which.side_effect = which_side_effect
            result = environment.detect_package_manager()
        assert result == "conda"

    def test_detect_venv(self):
        """Falls back to venv when no package manager."""
        with patch("shutil.which") as mock_which:
            def which_side_effect(cmd):
                if cmd == "python3":
                    return "/usr/bin/python3"
                return None
            mock_which.side_effect = which_side_effect
            result = environment.detect_package_manager()
        assert result == "venv"

    def test_detect_none(self):
        """Returns None when nothing available."""
        with patch("shutil.which", return_value=None):
            result = environment.detect_package_manager()
        assert result is None


class TestGetPackageManagerVersion:
    """Tests for get_package_manager_version."""

    def test_uv_version(self):
        """Gets uv version."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="uv 0.1.0")
            result = environment.get_package_manager_version("uv")
        assert result == "uv 0.1.0"

    def test_conda_version(self):
        """Gets conda version."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="conda 23.1.0")
            result = environment.get_package_manager_version("conda")
        assert result == "conda 23.1.0"

    def test_venv_version(self):
        """Gets Python version for venv."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Python 3.11.0")
            result = environment.get_package_manager_version("venv")
        assert "venv" in result
        assert "Python" in result

    def test_unknown_manager(self):
        """Returns None for unknown manager."""
        result = environment.get_package_manager_version("unknown")
        assert result is None


class TestCreateVenv:
    """Tests for create_venv."""

    def test_create_venv_path_not_exists(self, temp_dir):
        """Returns error if path doesn't exist."""
        result = environment.create_venv(temp_dir / "nonexistent")
        assert "error" in result

    def test_create_venv_already_exists(self, temp_dir):
        """Returns exists status if venv already present."""
        venv_path = temp_dir / ".venv"
        venv_path.mkdir()

        result = environment.create_venv(temp_dir)

        assert result["status"] == "exists"
        assert result["path"] == str(venv_path)

    def test_create_venv_no_manager(self, temp_dir):
        """Returns error if no package manager."""
        with patch.object(environment, "detect_package_manager", return_value=None):
            result = environment.create_venv(temp_dir)
        assert "error" in result
        assert "No package manager" in result["error"]

    def test_create_venv_with_uv(self, temp_dir):
        """Creates venv with uv."""
        with patch.object(environment, "detect_package_manager", return_value="uv"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = environment.create_venv(temp_dir, manager="uv")

        assert result["status"] == "created"
        assert result["manager"] == "uv"
        mock_run.assert_called_once()
        assert "uv" in mock_run.call_args[0][0]

    def test_create_venv_with_python_version(self, temp_dir):
        """Passes python version to uv."""
        with patch.object(environment, "detect_package_manager", return_value="uv"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            environment.create_venv(temp_dir, manager="uv", python_version="3.11")

        cmd = mock_run.call_args[0][0]
        assert "--python" in cmd
        assert "3.11" in cmd

    def test_create_venv_failure(self, temp_dir):
        """Handles venv creation failure."""
        with patch.object(environment, "detect_package_manager", return_value="uv"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="Error message")
            result = environment.create_venv(temp_dir, manager="uv")

        assert "error" in result


class TestGetVenvInfo:
    """Tests for get_venv_info."""

    def test_no_venv(self, temp_dir):
        """Returns exists=False when no venv."""
        result = environment.get_venv_info(temp_dir)
        assert result["exists"] is False

    def test_venv_exists(self, temp_dir):
        """Returns info when venv exists."""
        venv_path = temp_dir / ".venv"
        venv_path.mkdir()

        result = environment.get_venv_info(temp_dir)

        assert result["exists"] is True
        assert result["path"] == str(venv_path)

    def test_detects_pyproject(self, temp_dir):
        """Detects pyproject.toml."""
        venv_path = temp_dir / ".venv"
        venv_path.mkdir()
        (temp_dir / "pyproject.toml").write_text("[project]")

        result = environment.get_venv_info(temp_dir)

        assert result["project_type"] == "pyproject.toml"

    def test_detects_requirements(self, temp_dir):
        """Detects requirements.txt."""
        venv_path = temp_dir / ".venv"
        venv_path.mkdir()
        (temp_dir / "requirements.txt").write_text("requests")

        result = environment.get_venv_info(temp_dir)

        assert result["project_type"] == "requirements.txt"


class TestInstallDependencies:
    """Tests for install_dependencies."""

    def test_no_manager(self, temp_dir):
        """Returns error if no package manager."""
        with patch.object(environment, "detect_package_manager", return_value=None):
            result = environment.install_dependencies(temp_dir)
        assert "error" in result

    def test_no_project_files(self, temp_dir):
        """Returns error if no pyproject.toml or requirements.txt."""
        with patch.object(environment, "detect_package_manager", return_value="uv"):
            result = environment.install_dependencies(temp_dir)
        assert "error" in result
        assert "No pyproject.toml" in result["error"]

    def test_install_with_pyproject(self, temp_dir):
        """Installs with pyproject.toml."""
        (temp_dir / "pyproject.toml").write_text("[project]")

        with patch.object(environment, "detect_package_manager", return_value="uv"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = environment.install_dependencies(temp_dir)

        assert result["status"] == "installed"
        cmd = mock_run.call_args[0][0]
        assert "uv" in cmd
        assert "sync" in cmd

    def test_install_with_requirements(self, temp_dir):
        """Installs with requirements.txt."""
        (temp_dir / "requirements.txt").write_text("requests")

        with patch.object(environment, "detect_package_manager", return_value="uv"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = environment.install_dependencies(temp_dir)

        assert result["status"] == "installed"
        cmd = mock_run.call_args[0][0]
        assert "requirements.txt" in cmd

    def test_install_failure(self, temp_dir):
        """Handles installation failure."""
        (temp_dir / "requirements.txt").write_text("requests")

        with patch.object(environment, "detect_package_manager", return_value="uv"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="Error")
            result = environment.install_dependencies(temp_dir)

        assert "error" in result
