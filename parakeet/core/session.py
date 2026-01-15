"""Session management for conversation history."""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional


SESSION_DIR = Path.home() / ".parakeet" / "sessions"
CURRENT_SESSION_FILE = Path.home() / ".parakeet" / "current_session.txt"
MAX_MESSAGES = 100  # Keep last 100 messages (50 exchanges)


def ensure_session_dir() -> None:
    """Ensure session directory exists."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def get_session_path(session_id: str) -> Path:
    """Get path for a session file."""
    return SESSION_DIR / f"{session_id}.json"


def create_session_id() -> str:
    """Create a new session ID based on timestamp."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_session(session_id: str, conversation: list[dict[str, Any]]) -> None:
    """Save conversation history to a session file."""
    ensure_session_dir()
    session_path = get_session_path(session_id)

    session_data = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "messages": conversation
    }

    with open(session_path, "w") as f:
        json.dump(session_data, f, indent=2)

    # Update current session pointer
    with open(CURRENT_SESSION_FILE, "w") as f:
        f.write(session_id)


def load_session(session_id: str) -> Optional[list[dict[str, Any]]]:
    """Load conversation history from a session file."""
    session_path = get_session_path(session_id)

    if not session_path.exists():
        return None

    try:
        with open(session_path) as f:
            session_data = json.load(f)
        return session_data.get("messages", [])
    except (json.JSONDecodeError, KeyError):
        return None


def get_current_session_id() -> Optional[str]:
    """Get the current/last session ID."""
    if not CURRENT_SESSION_FILE.exists():
        return None

    try:
        with open(CURRENT_SESSION_FILE) as f:
            return f.read().strip()
    except Exception:
        return None


def load_last_session() -> Optional[tuple[str, list[dict[str, Any]]]]:
    """Load the last session if it exists."""
    session_id = get_current_session_id()
    if not session_id:
        return None

    conversation = load_session(session_id)
    if not conversation:
        return None

    return session_id, conversation


def list_sessions() -> list[dict[str, Any]]:
    """List all available sessions."""
    ensure_session_dir()
    sessions = []

    for session_file in sorted(SESSION_DIR.glob("*.json"), reverse=True):
        try:
            with open(session_file) as f:
                session_data = json.load(f)

            # Count actual user messages (exclude system prompt)
            message_count = sum(1 for m in session_data.get("messages", []) if m.get("role") == "user")

            sessions.append({
                "session_id": session_data.get("session_id", session_file.stem),
                "created_at": session_data.get("created_at", "Unknown"),
                "message_count": message_count,
                "path": str(session_file)
            })
        except (json.JSONDecodeError, KeyError):
            continue

    return sessions


def delete_session(session_id: str) -> bool:
    """Delete a session file."""
    session_path = get_session_path(session_id)

    if not session_path.exists():
        return False

    session_path.unlink()

    # Clear current session pointer if this was the current session
    current = get_current_session_id()
    if current == session_id:
        CURRENT_SESSION_FILE.unlink(missing_ok=True)

    return True


def clear_all_sessions() -> int:
    """Delete all session files."""
    ensure_session_dir()
    count = 0

    for session_file in SESSION_DIR.glob("*.json"):
        session_file.unlink()
        count += 1

    CURRENT_SESSION_FILE.unlink(missing_ok=True)

    return count


def trim_conversation(conversation: list[dict[str, Any]], max_messages: int = MAX_MESSAGES) -> list[dict[str, Any]]:
    """Trim conversation to keep only recent messages while preserving system prompt."""
    if len(conversation) <= max_messages:
        return conversation

    # Keep system prompt (first message) and most recent messages
    system_prompt = [conversation[0]] if conversation and conversation[0].get("role") == "system" else []
    recent_messages = conversation[-(max_messages - len(system_prompt)):]

    return system_prompt + recent_messages
