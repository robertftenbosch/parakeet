"""Git operations for Parakeet."""

import subprocess
from pathlib import Path
from typing import Any, Optional


def run_git_command(args: list[str], cwd: Optional[Path] = None) -> dict[str, Any]:
    """Run a git command and return the result.

    Args:
        args: Git command arguments (e.g., ["status", "-s"])
        cwd: Working directory (default: current directory)

    Returns:
        Dict with stdout, stderr, and return_code
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(cwd) if cwd else None
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "Git command timed out after 30 seconds",
            "return_code": -1,
            "success": False
        }
    except FileNotFoundError:
        return {
            "error": "Git is not installed or not in PATH",
            "return_code": -1,
            "success": False
        }
    except Exception as e:
        return {
            "error": str(e),
            "return_code": -1,
            "success": False
        }


def git_status(cwd: Optional[Path] = None, short: bool = True) -> dict[str, Any]:
    """Get git status.

    Args:
        cwd: Working directory
        short: Use short format

    Returns:
        Dict with status information
    """
    args = ["status"]
    if short:
        args.append("-s")

    result = run_git_command(args, cwd)
    if result["success"]:
        result["message"] = "Repository status retrieved"
        result["changes"] = result["stdout"].strip().split("\n") if result["stdout"].strip() else []
    return result


def git_log(cwd: Optional[Path] = None, limit: int = 10, oneline: bool = True) -> dict[str, Any]:
    """Get git log.

    Args:
        cwd: Working directory
        limit: Number of commits to show
        oneline: Use oneline format

    Returns:
        Dict with log information
    """
    args = ["log", f"-{limit}"]
    if oneline:
        args.append("--oneline")

    result = run_git_command(args, cwd)
    if result["success"]:
        result["message"] = f"Last {limit} commits retrieved"
        result["commits"] = result["stdout"].strip().split("\n") if result["stdout"].strip() else []
    return result


def git_diff(cwd: Optional[Path] = None, staged: bool = False, file: Optional[str] = None) -> dict[str, Any]:
    """Get git diff.

    Args:
        cwd: Working directory
        staged: Show staged changes (--cached)
        file: Specific file to diff

    Returns:
        Dict with diff information
    """
    args = ["diff"]
    if staged:
        args.append("--cached")
    if file:
        args.append(file)

    result = run_git_command(args, cwd)
    if result["success"]:
        result["message"] = "Diff retrieved"
        result["has_changes"] = bool(result["stdout"].strip())
    return result


def git_branch(cwd: Optional[Path] = None, list_all: bool = False) -> dict[str, Any]:
    """List git branches.

    Args:
        cwd: Working directory
        list_all: List all branches including remote

    Returns:
        Dict with branch information
    """
    args = ["branch"]
    if list_all:
        args.append("-a")

    result = run_git_command(args, cwd)
    if result["success"]:
        branches = result["stdout"].strip().split("\n")
        current = next((b.replace("* ", "") for b in branches if b.startswith("*")), None)
        result["message"] = "Branches retrieved"
        result["branches"] = [b.strip().replace("* ", "") for b in branches]
        result["current_branch"] = current
    return result


def git_add(files: list[str], cwd: Optional[Path] = None) -> dict[str, Any]:
    """Stage files for commit.

    Args:
        files: List of files to add (use ["."] for all)
        cwd: Working directory

    Returns:
        Dict with result
    """
    args = ["add"] + files
    result = run_git_command(args, cwd)
    if result["success"]:
        result["message"] = f"Staged {len(files)} file(s)"
    return result


def git_commit(message: str, cwd: Optional[Path] = None, amend: bool = False) -> dict[str, Any]:
    """Create a git commit.

    Args:
        message: Commit message
        cwd: Working directory
        amend: Amend previous commit

    Returns:
        Dict with result
    """
    args = ["commit", "-m", message]
    if amend:
        args.append("--amend")

    result = run_git_command(args, cwd)
    if result["success"]:
        result["message"] = "Commit created successfully"
    return result


def git_push(remote: str = "origin", branch: Optional[str] = None, cwd: Optional[Path] = None, force: bool = False) -> dict[str, Any]:
    """Push commits to remote.

    Args:
        remote: Remote name
        branch: Branch name (default: current branch)
        cwd: Working directory
        force: Force push (dangerous!)

    Returns:
        Dict with result
    """
    args = ["push", remote]
    if branch:
        args.append(branch)
    if force:
        args.append("--force")

    result = run_git_command(args, cwd)
    if result["success"]:
        result["message"] = f"Pushed to {remote}"
    return result


def git_pull(remote: str = "origin", branch: Optional[str] = None, cwd: Optional[Path] = None) -> dict[str, Any]:
    """Pull commits from remote.

    Args:
        remote: Remote name
        branch: Branch name (default: current branch)
        cwd: Working directory

    Returns:
        Dict with result
    """
    args = ["pull", remote]
    if branch:
        args.append(branch)

    result = run_git_command(args, cwd)
    if result["success"]:
        result["message"] = f"Pulled from {remote}"
    return result


def git_checkout(branch: str, cwd: Optional[Path] = None, create: bool = False) -> dict[str, Any]:
    """Checkout a branch.

    Args:
        branch: Branch name
        cwd: Working directory
        create: Create new branch (-b)

    Returns:
        Dict with result
    """
    args = ["checkout"]
    if create:
        args.append("-b")
    args.append(branch)

    result = run_git_command(args, cwd)
    if result["success"]:
        result["message"] = f"Checked out branch: {branch}"
    return result


def git_stash(action: str = "push", message: Optional[str] = None, cwd: Optional[Path] = None) -> dict[str, Any]:
    """Stash changes.

    Args:
        action: Stash action (push, pop, list, apply)
        message: Stash message (for push)
        cwd: Working directory

    Returns:
        Dict with result
    """
    args = ["stash", action]
    if action == "push" and message:
        args.extend(["-m", message])

    result = run_git_command(args, cwd)
    if result["success"]:
        result["message"] = f"Stash {action} completed"
    return result


def git_merge(branch: str, cwd: Optional[Path] = None, no_ff: bool = False) -> dict[str, Any]:
    """Merge a branch.

    Args:
        branch: Branch to merge
        cwd: Working directory
        no_ff: No fast-forward

    Returns:
        Dict with result
    """
    args = ["merge", branch]
    if no_ff:
        args.append("--no-ff")

    result = run_git_command(args, cwd)
    if result["success"]:
        result["message"] = f"Merged branch: {branch}"
    return result


def git_reset(mode: str = "soft", commit: str = "HEAD", cwd: Optional[Path] = None) -> dict[str, Any]:
    """Reset git state.

    Args:
        mode: Reset mode (soft, mixed, hard)
        commit: Commit to reset to
        cwd: Working directory

    Returns:
        Dict with result
    """
    args = ["reset", f"--{mode}", commit]
    result = run_git_command(args, cwd)
    if result["success"]:
        result["message"] = f"Reset {mode} to {commit}"
    return result


def git_remote(action: str = "show", name: Optional[str] = None, url: Optional[str] = None, cwd: Optional[Path] = None) -> dict[str, Any]:
    """Manage git remotes.

    Args:
        action: Action (show, add, remove, set-url)
        name: Remote name
        url: Remote URL (for add/set-url)
        cwd: Working directory

    Returns:
        Dict with result
    """
    args = ["remote"]

    if action == "show":
        args.append("-v")
    elif action in ["add", "remove", "set-url"]:
        if not name:
            return {"error": "Remote name required", "success": False}
        args.extend([action, name])
        if action in ["add", "set-url"] and url:
            args.append(url)

    result = run_git_command(args, cwd)
    if result["success"]:
        result["message"] = f"Remote {action} completed"
        if action == "show":
            result["remotes"] = result["stdout"].strip().split("\n") if result["stdout"].strip() else []
    return result
