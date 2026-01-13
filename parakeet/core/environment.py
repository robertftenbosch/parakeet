"""Environment and package manager utilities for Parakeet."""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from ..ui import console, print_error, print_success


def detect_package_manager() -> Optional[str]:
    """
    Detect available package manager.

    Returns:
        'uv', 'conda', 'venv', or None if nothing found
    """
    # Prefer uv (fastest, modern)
    if shutil.which("uv"):
        return "uv"

    # Then conda
    if shutil.which("conda"):
        return "conda"

    # Fallback to standard venv (requires python)
    if shutil.which("python3") or shutil.which("python"):
        return "venv"

    return None


def get_package_manager_version(manager: str) -> Optional[str]:
    """Get version of a package manager."""
    try:
        if manager == "uv":
            result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
            return result.stdout.strip()
        elif manager == "conda":
            result = subprocess.run(["conda", "--version"], capture_output=True, text=True)
            return result.stdout.strip()
        elif manager == "venv":
            result = subprocess.run(["python3", "--version"], capture_output=True, text=True)
            return f"venv (Python {result.stdout.strip()})"
    except Exception:
        pass
    return None


def install_uv() -> bool:
    """
    Install uv package manager.

    Returns:
        True if installation successful, False otherwise
    """
    console.print("[dim]Installing uv...[/]")
    try:
        # Use the official install script
        result = subprocess.run(
            ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print_success("uv installed successfully")
            console.print("[dim]You may need to restart your shell or run: source ~/.local/bin/env[/]")
            return True
        else:
            print_error(f"Failed to install uv: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print_error("Installation timed out")
        return False
    except Exception as e:
        print_error(f"Failed to install uv: {e}")
        return False


def ask_install_package_manager() -> Optional[str]:
    """
    Ask user if they want to install a package manager.

    Returns:
        The installed package manager name, or None if declined
    """
    console.print("\n[bold yellow]No package manager found![/]")
    console.print("Parakeet works best with a package manager for virtual environments.")
    console.print("\n[bold]Options:[/]")
    console.print("  [cyan]1.[/] Install uv (recommended - fast, modern Python package manager)")
    console.print("  [cyan]2.[/] Skip (use system Python, not recommended)")

    try:
        choice = console.input("\n[bold]Select option [1/2]:[/] ").strip()
        if choice == "1":
            if install_uv():
                return "uv"
        return None
    except (KeyboardInterrupt, EOFError):
        return None


def create_venv(
    project_path: Path,
    manager: Optional[str] = None,
    python_version: Optional[str] = None
) -> dict:
    """
    Create a virtual environment for a project.

    Args:
        project_path: Path to the project directory
        manager: Package manager to use ('uv', 'conda', 'venv'), auto-detected if None
        python_version: Python version to use (e.g., '3.11'), uses default if None

    Returns:
        Dict with status and details
    """
    project_path = Path(project_path).resolve()

    if not project_path.exists():
        return {"error": f"Project path does not exist: {project_path}"}

    # Auto-detect package manager if not specified
    if manager is None:
        manager = detect_package_manager()

    if manager is None:
        return {"error": "No package manager found. Please install uv, conda, or Python."}

    venv_path = project_path / ".venv"

    # Check if venv already exists
    if venv_path.exists():
        return {
            "status": "exists",
            "path": str(venv_path),
            "manager": manager,
            "message": "Virtual environment already exists"
        }

    try:
        if manager == "uv":
            cmd = ["uv", "venv", str(venv_path)]
            if python_version:
                cmd.extend(["--python", python_version])
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)

        elif manager == "conda":
            env_name = project_path.name
            cmd = ["conda", "create", "-p", str(venv_path), "-y"]
            if python_version:
                cmd.append(f"python={python_version}")
            else:
                cmd.append("python")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)

        elif manager == "venv":
            python_cmd = "python3" if shutil.which("python3") else "python"
            cmd = [python_cmd, "-m", "venv", str(venv_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)

        else:
            return {"error": f"Unknown package manager: {manager}"}

        if result.returncode == 0:
            return {
                "status": "created",
                "path": str(venv_path),
                "manager": manager,
                "message": f"Virtual environment created with {manager}"
            }
        else:
            return {
                "error": f"Failed to create venv: {result.stderr or result.stdout}",
                "manager": manager
            }

    except Exception as e:
        return {"error": str(e), "manager": manager}


def get_venv_info(project_path: Path) -> dict:
    """
    Get information about an existing virtual environment.

    Args:
        project_path: Path to the project directory

    Returns:
        Dict with venv information
    """
    project_path = Path(project_path).resolve()
    venv_path = project_path / ".venv"

    if not venv_path.exists():
        return {"exists": False}

    info = {
        "exists": True,
        "path": str(venv_path),
    }

    # Try to get Python version from venv
    python_path = venv_path / "bin" / "python"
    if not python_path.exists():
        python_path = venv_path / "Scripts" / "python.exe"  # Windows

    if python_path.exists():
        try:
            result = subprocess.run(
                [str(python_path), "--version"],
                capture_output=True,
                text=True
            )
            info["python_version"] = result.stdout.strip()
        except Exception:
            pass

    # Check for pyproject.toml or requirements.txt
    if (project_path / "pyproject.toml").exists():
        info["project_type"] = "pyproject.toml"
    elif (project_path / "requirements.txt").exists():
        info["project_type"] = "requirements.txt"

    return info


def install_dependencies(
    project_path: Path,
    manager: Optional[str] = None
) -> dict:
    """
    Install dependencies for a project.

    Args:
        project_path: Path to the project directory
        manager: Package manager to use, auto-detected if None

    Returns:
        Dict with status and details
    """
    project_path = Path(project_path).resolve()

    if manager is None:
        manager = detect_package_manager()

    if manager is None:
        return {"error": "No package manager found"}

    # Determine project type
    has_pyproject = (project_path / "pyproject.toml").exists()
    has_requirements = (project_path / "requirements.txt").exists()

    if not has_pyproject and not has_requirements:
        return {"error": "No pyproject.toml or requirements.txt found"}

    try:
        if manager == "uv":
            if has_pyproject:
                cmd = ["uv", "sync"]
            else:
                cmd = ["uv", "pip", "install", "-r", "requirements.txt"]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)

        elif manager == "conda":
            venv_path = project_path / ".venv"
            if has_requirements:
                cmd = ["conda", "run", "-p", str(venv_path), "pip", "install", "-r", "requirements.txt"]
            else:
                cmd = ["conda", "run", "-p", str(venv_path), "pip", "install", "-e", "."]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)

        elif manager == "venv":
            venv_path = project_path / ".venv"
            pip_path = venv_path / "bin" / "pip"
            if not pip_path.exists():
                pip_path = venv_path / "Scripts" / "pip.exe"

            if has_requirements:
                cmd = [str(pip_path), "install", "-r", "requirements.txt"]
            else:
                cmd = [str(pip_path), "install", "-e", "."]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)

        else:
            return {"error": f"Unknown package manager: {manager}"}

        if result.returncode == 0:
            return {
                "status": "installed",
                "manager": manager,
                "message": "Dependencies installed successfully"
            }
        else:
            return {
                "error": f"Failed to install dependencies: {result.stderr or result.stdout}",
                "manager": manager
            }

    except Exception as e:
        return {"error": str(e), "manager": manager}
