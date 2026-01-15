"""Tool definitions for the Parakeet agent."""

import re
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

from ..ui import console


def resolve_abs_path(path_str: str) -> Path:
    """Convert relative path to absolute path."""
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def read_file_tool(path: str) -> dict[str, Any]:
    """
    Read the contents of a file.

    Args:
        path: The path to the file to read

    Returns:
        Dict with path and content
    """
    full_path = resolve_abs_path(path)
    console.print(f"  [dim]Reading:[/] {full_path}")
    with open(str(full_path), "r") as f:
        content = f.read()
    return {
        "path": str(full_path),
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


def run_bash_tool(
    command: str,
    timeout: Optional[float] = None,
    cwd: Optional[str] = None,
    env: Optional[dict[str, str]] = None,
    session_id: Optional[str] = None,
    sudo_password: Optional[str] = None
) -> dict[str, Any]:
    """
    Execute a bash command. Requires user confirmation.

    Args:
        command: The bash command to execute
        timeout: Timeout in seconds (default: 60 for one-off, 300 for sessions)
        cwd: Working directory (default: current directory)
        env: Environment variables to set (merged with current env)
        session_id: Optional session ID for persistent shell (maintains state between commands)
        sudo_password: Sudo password for commands requiring sudo (internal, passed by confirmation)

    Returns:
        Dict with stdout, stderr, return_code, and optionally session_id
    """
    from .shell_session import get_session, create_session

    # Handle sudo password
    if sudo_password and "sudo" in command.lower():
        # Use echo to pipe password to sudo -S
        # -S tells sudo to read password from stdin
        command = f"echo '{sudo_password}' | sudo -S {command.replace('sudo', '', 1).strip()}"

    # Handle persistent shell sessions
    if session_id:
        session = get_session(session_id)

        # Create new session if it doesn't exist
        if not session:
            session = create_session(session_id, cwd=cwd, env=env)
            console.print(f"  [dim]Created shell session:[/] {session_id}")

        # Execute in session
        timeout_val = timeout if timeout is not None else 300.0
        result = session.execute(command, timeout=timeout_val)
        result["session_id"] = session_id
        return result

    # One-off command execution (original behavior)
    timeout_val = timeout if timeout is not None else 60.0

    try:
        # Build environment
        exec_env = None
        if env:
            import os
            exec_env = os.environ.copy()
            exec_env.update(env)

        # Determine working directory
        exec_cwd = resolve_abs_path(cwd) if cwd else Path.cwd()

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_val,
            cwd=str(exec_cwd),
            env=exec_env
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "error": f"Command timed out after {timeout_val} seconds",
            "return_code": -1
        }
    except Exception as e:
        return {
            "error": str(e),
            "return_code": -1
        }


def manage_shell_session_tool(action: str, session_id: Optional[str] = None) -> dict[str, Any]:
    """
    Manage persistent shell sessions.

    Args:
        action: Action to perform - 'list', 'terminate', 'terminate_all', or 'cleanup'
        session_id: Session ID (required for 'terminate' action)

    Returns:
        Dict with action result
    """
    from .shell_session import (
        list_sessions,
        terminate_session,
        terminate_all_sessions,
        cleanup_dead_sessions
    )

    console.print(f"  [dim]Shell session action:[/] {action}")

    if action == "list":
        sessions = list_sessions()
        return {
            "action": "list",
            "sessions": sessions,
            "count": len(sessions)
        }

    elif action == "terminate":
        if not session_id:
            return {"error": "session_id required for terminate action"}

        success = terminate_session(session_id)
        if success:
            return {
                "action": "terminate",
                "session_id": session_id,
                "status": "terminated"
            }
        else:
            return {
                "action": "terminate",
                "session_id": session_id,
                "error": "Session not found"
            }

    elif action == "terminate_all":
        count = terminate_all_sessions()
        return {
            "action": "terminate_all",
            "terminated_count": count
        }

    elif action == "cleanup":
        count = cleanup_dead_sessions()
        return {
            "action": "cleanup",
            "cleaned_count": count
        }

    else:
        return {"error": f"Unknown action: {action}"}


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


def search_code_tool(pattern: str, path: str = ".", file_pattern: Optional[str] = None) -> dict[str, Any]:
    """
    Search for a pattern in files using regex.

    Args:
        pattern: The regex pattern to search for
        path: Directory to search in (default: current directory)
        file_pattern: Optional glob pattern to filter files (e.g., "*.py")

    Returns:
        Dict with matches: list of {file, line, content}
    """
    search_path = resolve_abs_path(path)
    console.print(f"  [dim]Searching:[/] {search_path} for '{pattern}'")
    matches = []

    # Determine files to search
    if file_pattern:
        files = search_path.rglob(file_pattern)
    else:
        files = search_path.rglob("*")

    # Common binary/ignored extensions
    ignore_ext = {'.pyc', '.pyo', '.so', '.dll', '.exe', '.bin', '.jpg', '.png', '.gif', '.pdf', '.ico', '.woff', '.woff2', '.ttf', '.eot'}
    ignore_dirs = {'.git', '.venv', 'venv', '__pycache__', 'node_modules', '.parakeet', '.mypy_cache', '.pytest_cache'}

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return {"error": f"Invalid regex: {e}"}

    for file in files:
        # Skip directories and ignored paths
        if file.is_dir():
            continue
        if any(ignored in file.parts for ignored in ignore_dirs):
            continue
        if file.suffix.lower() in ignore_ext:
            continue

        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(content.splitlines(), 1):
                if regex.search(line):
                    matches.append({
                        "file": str(file.relative_to(search_path)),
                        "line": i,
                        "content": line.strip()[:200]  # Truncate long lines
                    })
                    if len(matches) >= 50:  # Limit results
                        return {"matches": matches, "truncated": True}
        except Exception:
            continue

    return {"matches": matches, "truncated": False}


def sqlite_tool(database: str, query: str, params: Optional[list[str]] = None) -> dict[str, Any]:
    """
    Execute a SQL query on a SQLite database.

    Args:
        database: Path to the SQLite database file
        query: SQL query to execute
        params: Optional list of parameters for parameterized queries

    Returns:
        Dict with columns, rows, and rows_affected
    """
    db_path = resolve_abs_path(database)
    console.print(f"  [dim]SQLite:[/] {db_path}")
    console.print(f"  [dim]Query:[/] {query[:100]}{'...' if len(query) > 100 else ''}")

    if not db_path.exists():
        return {"error": f"Database not found: {db_path}"}

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # Check if this is a SELECT or PRAGMA query
        query_upper = query.strip().upper()
        if query_upper.startswith(("SELECT", "PRAGMA")):
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            result = {
                "columns": columns,
                "rows": [dict(row) for row in rows],
                "row_count": len(rows)
            }
        else:
            conn.commit()
            result = {
                "rows_affected": cursor.rowcount,
                "last_rowid": cursor.lastrowid
            }

        conn.close()
        return result

    except sqlite3.Error as e:
        return {"error": f"SQLite error: {e}"}
    except Exception as e:
        return {"error": str(e)}


def is_sqlite_write_query(query: str) -> bool:
    """Check if a SQL query modifies data."""
    query_upper = query.strip().upper()
    write_keywords = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "REPLACE", "TRUNCATE")
    return query_upper.startswith(write_keywords)


def is_git_dangerous_action(action: str) -> bool:
    """Check if a git action requires confirmation."""
    # Safe actions that don't need confirmation
    safe_actions = {"status", "log", "diff", "branch", "remote"}

    # Everything else needs confirmation (commit, push, pull, merge, reset, checkout, stash, add)
    return action not in safe_actions


def create_venv_tool(path: str, python_version: Optional[str] = None) -> dict[str, Any]:
    """
    Create a virtual environment for a Python project.

    Args:
        path: The project directory path where .venv will be created
        python_version: Optional Python version (e.g., '3.11', '3.12')

    Returns:
        Dict with status, path, and manager used
    """
    from .environment import create_venv, detect_package_manager

    project_path = resolve_abs_path(path)
    console.print(f"  [dim]Creating venv:[/] {project_path}")

    manager = detect_package_manager()
    if manager:
        console.print(f"  [dim]Using:[/] {manager}")

    result = create_venv(project_path, python_version=python_version)
    return result


def install_deps_tool(path: str) -> dict[str, Any]:
    """
    Install dependencies for a Python project from pyproject.toml or requirements.txt.

    Args:
        path: The project directory path

    Returns:
        Dict with status and details
    """
    from .environment import install_dependencies, detect_package_manager

    project_path = resolve_abs_path(path)
    console.print(f"  [dim]Installing deps:[/] {project_path}")

    manager = detect_package_manager()
    if manager:
        console.print(f"  [dim]Using:[/] {manager}")

    result = install_dependencies(project_path)
    return result


# Import bioinformatics tools
from .bio_tools import kegg_tool, pdb_tool, uniprot_tool, ncbi_tool, ontology_tool, blast_tool

# Import pathway analyzer
from .pathway_analyzer import (
    get_pathway_info,
    get_pathway_enzymes,
    compare_pathway_organisms,
    find_alternative_enzymes,
    analyze_nitrogen_fixation_pathway,
    suggest_optimization_targets,
)


def analyze_pathway_tool(
    pathway_id: str,
    organism: Optional[str] = None,
    analysis_type: str = "info"
) -> dict[str, Any]:
    """
    Analyze a metabolic pathway from KEGG.

    Args:
        pathway_id: KEGG pathway ID (e.g., '00910' for nitrogen metabolism)
        organism: Optional organism code (e.g., 'eco' for E. coli, 'avn' for Azotobacter)
        analysis_type: Type of analysis - 'info', 'enzymes', 'optimization', or 'nitrogen'

    Returns:
        Dict with pathway analysis results
    """
    console.print(f"  [dim]Analyzing pathway:[/] {pathway_id}")

    if analysis_type == "nitrogen":
        org = organism or "avn"
        return analyze_nitrogen_fixation_pathway(org)

    # Build full pathway ID if organism is provided
    full_id = f"{organism}{pathway_id}" if organism else pathway_id

    if analysis_type == "info":
        return get_pathway_info(full_id)
    elif analysis_type == "enzymes":
        return get_pathway_enzymes(full_id)
    elif analysis_type == "optimization":
        if not organism:
            return {"error": "Organism code required for optimization analysis"}
        return suggest_optimization_targets(pathway_id, organism)
    else:
        return {"error": f"Unknown analysis type: {analysis_type}"}


def compare_organisms_tool(
    pathway_id: str,
    organism1: str,
    organism2: str
) -> dict[str, Any]:
    """
    Compare a metabolic pathway between two organisms.

    Args:
        pathway_id: KEGG pathway number (e.g., '00910')
        organism1: First organism code (e.g., 'eco' for E. coli)
        organism2: Second organism code (e.g., 'avn' for Azotobacter)

    Returns:
        Dict with comparison results including common and unique functions
    """
    console.print(f"  [dim]Comparing:[/] {organism1} vs {organism2} for pathway {pathway_id}")
    return compare_pathway_organisms(pathway_id, organism1, organism2)


def find_alternatives_tool(
    ec_number: str,
    source_organism: Optional[str] = None,
    target_organisms: Optional[str] = None
) -> dict[str, Any]:
    """
    Find alternative enzymes from different organisms.

    Useful for finding enzymes with potentially better properties
    for metabolic engineering.

    Args:
        ec_number: EC number of the enzyme (e.g., '1.18.6.1' for nitrogenase)
        source_organism: Current organism to exclude from results
        target_organisms: Comma-separated list of organisms to search in

    Returns:
        Dict with alternative enzymes from different organisms
    """
    console.print(f"  [dim]Finding alternatives for:[/] EC {ec_number}")

    targets = None
    if target_organisms:
        targets = [t.strip() for t in target_organisms.split(",")]

    return find_alternative_enzymes(ec_number, source_organism, targets)


def git_tool(
    action: str,
    files: Optional[list[str]] = None,
    message: Optional[str] = None,
    branch: Optional[str] = None,
    remote: Optional[str] = None,
    limit: Optional[int] = None,
    staged: bool = False,
    create: bool = False,
    force: bool = False,
    cwd: Optional[str] = None
) -> dict[str, Any]:
    """
    Execute git operations.

    Args:
        action: Git action - 'status', 'log', 'diff', 'branch', 'add', 'commit',
                'push', 'pull', 'checkout', 'stash', 'merge', 'reset', 'remote'
        files: Files to add (for 'add' action)
        message: Commit or stash message
        branch: Branch name (for checkout, merge, push, pull)
        remote: Remote name (default: 'origin')
        limit: Number of commits for log (default: 10)
        staged: Show staged changes for diff
        create: Create new branch for checkout
        force: Force operation (push --force, etc.)
        cwd: Working directory

    Returns:
        Dict with operation result
    """
    from .git_operations import (
        git_status, git_log, git_diff, git_branch, git_add,
        git_commit, git_push, git_pull, git_checkout, git_stash,
        git_merge, git_reset, git_remote
    )

    console.print(f"  [dim]Git:[/] {action}")

    work_dir = resolve_abs_path(cwd) if cwd else Path.cwd()

    # Safe operations (no confirmation needed)
    if action == "status":
        return git_status(work_dir)
    elif action == "log":
        return git_log(work_dir, limit=limit or 10)
    elif action == "diff":
        return git_diff(work_dir, staged=staged)
    elif action == "branch":
        return git_branch(work_dir, list_all=False)
    elif action == "remote":
        return git_remote("show", cwd=work_dir)

    # Potentially dangerous operations (will be confirmed by agent system)
    elif action == "add":
        if not files:
            return {"error": "files parameter required for 'add' action", "success": False}
        return git_add(files, work_dir)
    elif action == "commit":
        if not message:
            return {"error": "message parameter required for 'commit' action", "success": False}
        return git_commit(message, work_dir)
    elif action == "push":
        return git_push(remote or "origin", branch, work_dir, force)
    elif action == "pull":
        return git_pull(remote or "origin", branch, work_dir)
    elif action == "checkout":
        if not branch:
            return {"error": "branch parameter required for 'checkout' action", "success": False}
        return git_checkout(branch, work_dir, create)
    elif action == "stash":
        stash_action = "push"  # Default stash action
        return git_stash(stash_action, message, work_dir)
    elif action == "merge":
        if not branch:
            return {"error": "branch parameter required for 'merge' action", "success": False}
        return git_merge(branch, work_dir)
    elif action == "reset":
        return git_reset("soft", "HEAD", work_dir)
    else:
        return {"error": f"Unknown git action: {action}", "success": False}


def propose_plan_tool(
    plan_title: str,
    steps: list[dict[str, str]]
) -> dict[str, Any]:
    """
    Propose a plan to the user and let them select which steps to execute.

    This tool allows agents to present a multi-step plan and get user approval
    for which steps should be executed. User can select specific steps via checkboxes.

    Args:
        plan_title: Title/description of the overall plan
        steps: List of step dicts, each containing:
               - 'description': What the step does (required)
               - 'agent': Which agent will execute (optional, for multi-agent mode)
               - 'rationale': Why this step is needed (optional)

    Returns:
        Dict with:
        - approved: Boolean, whether plan was approved
        - selected_steps: List of step indices that were selected
        - original_steps: The original plan steps
    """
    from ..ui import select_plan_steps

    console.print("\n[bold yellow]📋 Plan Proposal[/]")

    # Validate steps
    if not steps:
        return {
            "approved": False,
            "error": "No steps provided in plan",
            "selected_steps": []
        }

    # Get user selection
    selected_indices = select_plan_steps(plan_title, steps)

    if not selected_indices:
        return {
            "approved": False,
            "selected_steps": [],
            "original_steps": steps,
            "message": "Plan cancelled by user"
        }

    return {
        "approved": True,
        "selected_steps": selected_indices,
        "original_steps": steps,
        "message": f"User approved {len(selected_indices)} of {len(steps)} steps"
    }


def smart_commit_tool(
    files: Optional[list[str]] = None,
    auto_message: bool = True,
    custom_message: Optional[str] = None,
    cwd: Optional[str] = None
) -> dict[str, Any]:
    """
    Create an intelligent git commit with auto-generated message.

    This tool analyzes changes and creates appropriate commit messages.
    Requires user confirmation before committing.

    Args:
        files: Files to stage and commit (default: all changes)
        auto_message: Generate commit message from changes (default: True)
        custom_message: Custom commit message (overrides auto_message)
        cwd: Working directory

    Returns:
        Dict with commit result including message used
    """
    from .git_operations import git_status, git_diff, git_add, git_commit

    console.print("  [dim]Smart Commit:[/] Analyzing changes...")

    work_dir = resolve_abs_path(cwd) if cwd else Path.cwd()

    # Get status to see what changed
    status_result = git_status(work_dir, short=True)
    if not status_result.get("success"):
        return status_result

    changes = status_result.get("changes", [])
    if not changes:
        return {"error": "No changes to commit", "success": False}

    # Stage files
    files_to_add = files or ["."]
    add_result = git_add(files_to_add, work_dir)
    if not add_result.get("success"):
        return add_result

    # Generate or use commit message
    if custom_message:
        commit_message = custom_message
    elif auto_message:
        # Get diff to analyze changes
        diff_result = git_diff(work_dir, staged=True)

        # Simple message generation based on file changes
        modified = [c for c in changes if c.startswith(" M") or c.startswith("M")]
        added = [c for c in changes if c.startswith("A") or c.startswith("??")]
        deleted = [c for c in changes if c.startswith("D")]

        # Build message
        parts = []
        if added:
            parts.append(f"Add {len(added)} file(s)")
        if modified:
            parts.append(f"Update {len(modified)} file(s)")
        if deleted:
            parts.append(f"Remove {len(deleted)} file(s)")

        commit_message = ", ".join(parts) if parts else "Update files"

        # Add file details if reasonable number
        if len(changes) <= 5:
            file_list = [c.split()[-1] for c in changes]
            commit_message += f"\n\n- " + "\n- ".join(file_list)
    else:
        commit_message = "Update files"

    # Create commit
    commit_result = git_commit(commit_message, work_dir)
    commit_result["commit_message"] = commit_message
    commit_result["files_staged"] = len(files_to_add)

    return commit_result

# Tools list for native Ollama tool calling
TOOLS = [
    # Planning
    propose_plan_tool,
    # File operations
    read_file_tool,
    list_files_tool,
    edit_file_tool,
    search_code_tool,
    # Database
    sqlite_tool,
    # Environment
    create_venv_tool,
    install_deps_tool,
    # Code execution
    run_bash_tool,
    manage_shell_session_tool,
    run_python_tool,
    # Git operations
    git_tool,
    smart_commit_tool,
    # Bioinformatics
    kegg_tool,
    pdb_tool,
    uniprot_tool,
    ncbi_tool,
    ontology_tool,
    blast_tool,
    # Pathway analysis
    analyze_pathway_tool,
    compare_organisms_tool,
    find_alternatives_tool,
]

# Registry for looking up tools by name
TOOL_REGISTRY = {
    "propose_plan_tool": propose_plan_tool,
    "read_file_tool": read_file_tool,
    "list_files_tool": list_files_tool,
    "edit_file_tool": edit_file_tool,
    "run_bash_tool": run_bash_tool,
    "manage_shell_session_tool": manage_shell_session_tool,
    "run_python_tool": run_python_tool,
    "search_code_tool": search_code_tool,
    "sqlite_tool": sqlite_tool,
    "create_venv_tool": create_venv_tool,
    "install_deps_tool": install_deps_tool,
    "git_tool": git_tool,
    "smart_commit_tool": smart_commit_tool,
    "kegg_tool": kegg_tool,
    "pdb_tool": pdb_tool,
    "uniprot_tool": uniprot_tool,
    "ncbi_tool": ncbi_tool,
    "ontology_tool": ontology_tool,
    "blast_tool": blast_tool,
    "analyze_pathway_tool": analyze_pathway_tool,
    "compare_organisms_tool": compare_organisms_tool,
    "find_alternatives_tool": find_alternatives_tool,
}

# Tools that require user confirmation before execution
DANGEROUS_TOOLS = {"run_bash_tool", "run_python_tool", "install_deps_tool", "smart_commit_tool"}

# Tools that need conditional confirmation (checked per-call)
CONDITIONAL_TOOLS = {
    "sqlite_tool": is_sqlite_write_query,
    "git_tool": is_git_dangerous_action,
}
