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

# Tools list for native Ollama tool calling
TOOLS = [
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
    run_python_tool,
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
    "read_file_tool": read_file_tool,
    "list_files_tool": list_files_tool,
    "edit_file_tool": edit_file_tool,
    "run_bash_tool": run_bash_tool,
    "run_python_tool": run_python_tool,
    "search_code_tool": search_code_tool,
    "sqlite_tool": sqlite_tool,
    "create_venv_tool": create_venv_tool,
    "install_deps_tool": install_deps_tool,
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
DANGEROUS_TOOLS = {"run_bash_tool", "run_python_tool", "install_deps_tool"}

# Tools that need conditional confirmation (checked per-call)
CONDITIONAL_TOOLS = {"sqlite_tool": is_sqlite_write_query}
