"""Persistent shell session management."""

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional, Any


class ShellSession:
    """A persistent shell session that maintains state between commands."""

    def __init__(self, session_id: str, cwd: Optional[str] = None, env: Optional[dict[str, str]] = None):
        """Initialize a shell session.

        Args:
            session_id: Unique identifier for this session
            cwd: Working directory (default: current directory)
            env: Environment variables to set (merged with current env)
        """
        self.session_id = session_id
        self.cwd = Path(cwd).resolve() if cwd else Path.cwd()

        # Merge environment variables
        self.env = os.environ.copy()
        if env:
            self.env.update(env)

        # Start shell process
        self.process = subprocess.Popen(
            ["/bin/bash"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(self.cwd),
            env=self.env,
        )

        self.lock = threading.Lock()
        self.created_at = time.time()

    def execute(self, command: str, timeout: float = 60.0) -> dict[str, Any]:
        """Execute a command in this shell session.

        Args:
            command: The command to execute
            timeout: Timeout in seconds (default: 60)

        Returns:
            Dict with stdout, stderr, return_code
        """
        with self.lock:
            if self.process.poll() is not None:
                return {
                    "error": "Shell session has terminated",
                    "return_code": self.process.returncode
                }

            try:
                # Use a marker to detect command completion
                marker = f"__PARAKEET_END_{int(time.time() * 1000)}__"

                # Execute command and echo marker + exit code
                full_command = f"{command}\necho {marker} $?\n"

                self.process.stdin.write(full_command)
                self.process.stdin.flush()

                # Read output until we see the marker
                stdout_lines = []
                stderr_lines = []
                return_code = 0

                start_time = time.time()
                while True:
                    if time.time() - start_time > timeout:
                        return {
                            "error": f"Command timed out after {timeout} seconds",
                            "stdout": "\n".join(stdout_lines),
                            "stderr": "\n".join(stderr_lines),
                            "return_code": -1
                        }

                    # Try to read stdout
                    line = self.process.stdout.readline()
                    if line:
                        line = line.rstrip('\n')
                        # Check if this is our marker
                        if line.startswith(marker):
                            # Extract return code
                            parts = line.split()
                            if len(parts) > 1:
                                try:
                                    return_code = int(parts[1])
                                except ValueError:
                                    pass
                            break
                        stdout_lines.append(line)

                return {
                    "stdout": "\n".join(stdout_lines),
                    "stderr": "",  # stderr is harder to capture cleanly in interactive shell
                    "return_code": return_code
                }

            except Exception as e:
                return {
                    "error": str(e),
                    "return_code": -1
                }

    def is_alive(self) -> bool:
        """Check if the shell process is still running."""
        return self.process.poll() is None

    def terminate(self) -> None:
        """Terminate the shell session."""
        if self.is_alive():
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def get_info(self) -> dict[str, Any]:
        """Get information about this session."""
        return {
            "session_id": self.session_id,
            "cwd": str(self.cwd),
            "alive": self.is_alive(),
            "pid": self.process.pid,
            "age_seconds": int(time.time() - self.created_at)
        }


# Global registry of active sessions
_sessions: dict[str, ShellSession] = {}
_session_lock = threading.Lock()


def get_session(session_id: str) -> Optional[ShellSession]:
    """Get an existing shell session."""
    with _session_lock:
        return _sessions.get(session_id)


def create_session(
    session_id: str,
    cwd: Optional[str] = None,
    env: Optional[dict[str, str]] = None
) -> ShellSession:
    """Create a new shell session.

    Args:
        session_id: Unique identifier for this session
        cwd: Working directory (default: current directory)
        env: Environment variables to set

    Returns:
        ShellSession object
    """
    with _session_lock:
        if session_id in _sessions:
            # Terminate old session with same ID
            _sessions[session_id].terminate()

        session = ShellSession(session_id, cwd, env)
        _sessions[session_id] = session
        return session


def list_sessions() -> list[dict[str, Any]]:
    """List all active sessions."""
    with _session_lock:
        return [s.get_info() for s in _sessions.values()]


def terminate_session(session_id: str) -> bool:
    """Terminate a specific session.

    Args:
        session_id: Session to terminate

    Returns:
        True if session was found and terminated
    """
    with _session_lock:
        session = _sessions.get(session_id)
        if session:
            session.terminate()
            del _sessions[session_id]
            return True
        return False


def terminate_all_sessions() -> int:
    """Terminate all sessions.

    Returns:
        Number of sessions terminated
    """
    with _session_lock:
        count = len(_sessions)
        for session in _sessions.values():
            session.terminate()
        _sessions.clear()
        return count


def cleanup_dead_sessions() -> int:
    """Remove dead sessions from registry.

    Returns:
        Number of sessions cleaned up
    """
    with _session_lock:
        dead_ids = [sid for sid, sess in _sessions.items() if not sess.is_alive()]
        for sid in dead_ids:
            del _sessions[sid]
        return len(dead_ids)
