"""Tool definitions for the Parakeet agent."""

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from ..ui import console


def resolve_abs_path(path_str: str) -> Path:
    """Convert relative path to absolute path."""
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def read_file_tool(filename: str) -> dict[str, Any]:
    """
    Read the contents of a file.

    Args:
        filename: The path to the file to read

    Returns:
        Dict with file_path and content
    """
    full_path = resolve_abs_path(filename)
    console.print(f"  [dim]Reading:[/] {full_path}")
    with open(str(full_path), "r") as f:
        content = f.read()
    return {
        "file_path": str(full_path),
        "content": content
    }


def list_files_tool(path: str) -> dict[str, Any]:
    """
    List files in a directory.

    Args:
        path: The path to the directory to list

    Returns:
        Dict with path and list of files
    """
    full_path = resolve_abs_path(path)
    console.print(f"  [dim]Listing:[/] {full_path}")
    all_files = []
    for item in full_path.iterdir():
        all_files.append({
            "filename": item.name,
            "type": "file" if item.is_file() else "dir"
        })
    return {
        "path": str(full_path),
        "files": all_files
    }


def edit_file_tool(path: str, old_str: str, new_str: str) -> dict[str, Any]:
    """
    Edit a file by replacing text. If old_str is empty, creates a new file.

    Args:
        path: The path to the file to edit
        old_str: The string to replace (empty string to create new file)
        new_str: The replacement string (or content for new file)

    Returns:
        Dict with path and action taken
    """
    full_path = resolve_abs_path(path)
    console.print(f"  [dim]Editing:[/] {full_path}")
    if old_str == "":
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(new_str, encoding="utf-8")
        return {
            "path": str(full_path),
            "action": "created_file"
        }
    original = full_path.read_text(encoding="utf-8")
    if original.find(old_str) == -1:
        return {
            "path": str(full_path),
            "action": "old_str not found"
        }
    edited = original.replace(old_str, new_str, 1)
    full_path.write_text(edited, encoding="utf-8")
    return {
        "path": str(full_path),
        "action": "edited"
    }


def run_bash_tool(command: str) -> dict[str, Any]:
    """
    Execute a bash command. Requires user confirmation.

    Args:
        command: The bash command to execute

    Returns:
        Dict with stdout, stderr, and return_code
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path.cwd()
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "Command timed out after 60 seconds",
            "return_code": -1
        }
    except Exception as e:
        return {
            "error": str(e),
            "return_code": -1
        }


def run_python_tool(code: str) -> dict[str, Any]:
    """
    Execute Python code. Requires user confirmation.

    Args:
        code: The Python code to execute

    Returns:
        Dict with stdout, stderr, and return_code
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ['python', temp_path],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=Path.cwd()
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        finally:
            Path(temp_path).unlink(missing_ok=True)
    except subprocess.TimeoutExpired:
        return {
            "error": "Python execution timed out after 60 seconds",
            "return_code": -1
        }
    except Exception as e:
        return {
            "error": str(e),
            "return_code": -1
        }


# Tools list for native Ollama tool calling
TOOLS = [read_file_tool, list_files_tool, edit_file_tool, run_bash_tool, run_python_tool]

# Registry for looking up tools by name
TOOL_REGISTRY = {
    "read_file_tool": read_file_tool,
    "list_files_tool": list_files_tool,
    "edit_file_tool": edit_file_tool,
    "run_bash_tool": run_bash_tool,
    "run_python_tool": run_python_tool,
}

# Tools that require user confirmation before execution
DANGEROUS_TOOLS = {"run_bash_tool", "run_python_tool"}
