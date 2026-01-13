import argparse
import json
import os
import subprocess
import tempfile

from ollama import Client
from dotenv import load_dotenv
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

load_dotenv()

CONFIG_DIR = Path.home() / ".parakeet"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> Dict[str, str]:
    """Load config from ~/.parakeet/config.json or return empty dict."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_config(config: Dict[str, str]) -> None:
    """Save config to ~/.parakeet/config.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def list_available_models(client: Client) -> List[str]:
    """Get list of available models from Ollama."""
    try:
        response = client.list()
        return [model['name'] for model in response.get('models', [])]
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []


def select_model_interactive(client: Client) -> Optional[str]:
    """Show available models and let user select one."""
    models = list_available_models(client)
    if not models:
        print("No models found. Please pull a model first: ollama pull <model>")
        return None

    print("\nAvailable models:")
    for i, model in enumerate(models, 1):
        print(f"  {i}. {model}")

    while True:
        try:
            choice = input("\nSelect model number: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                return models[idx]
            print(f"Please enter a number between 1 and {len(models)}")
        except ValueError:
            print("Please enter a valid number")
        except (KeyboardInterrupt, EOFError):
            return None


def get_ollama_config(args: argparse.Namespace) -> Tuple[str, str]:
    """
    Determine Ollama host and model based on priority:
    1. CLI arguments
    2. Config file
    3. Environment variables
    4. Interactive prompt (and save to config)
    """
    config = load_config()

    # Determine host
    host = (
        args.host or
        config.get("ollama_host") or
        os.environ.get("OLLAMA_HOST") or
        "http://localhost:11434"
    )

    # Create client to check connection / list models
    client = Client(host=host)

    # Determine model
    model = args.model or config.get("ollama_model") or os.environ.get("OLLAMA_MODEL")

    if not model:
        print(f"Connected to Ollama at: {host}")
        model = select_model_interactive(client)
        if not model:
            model = "llama3.2"  # fallback default

    # Save to config if changed
    if host != config.get("ollama_host") or model != config.get("ollama_model"):
        config["ollama_host"] = host
        config["ollama_model"] = model
        save_config(config)
        print(f"Configuration saved to {CONFIG_FILE}")

    return host, model


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AI coding agent using Ollama")
    parser.add_argument("--host", help="Ollama server URL")
    parser.add_argument("--model", help="Model name to use")
    return parser.parse_args()


SYSTEM_PROMPT = """You are a coding assistant specialized in biotech and robotics applications.

## Your Expertise

### Bioinformatics
- BioPython for sequence analysis (SeqIO, Seq, SeqRecord)
- FASTA/FASTQ/GenBank file parsing
- Sequence alignment (pairwise, multiple sequence alignment)
- BLAST searches and result parsing
- Primer design and PCR analysis

### Robotics - ROS2
- ROS2 node creation (rclpy)
- Publishers, subscribers, services, actions
- Launch files and parameter handling
- TF2 transforms and coordinate frames
- Common message types (geometry_msgs, sensor_msgs)

### Robotics - Simulation
- PyBullet for physics simulation
- MuJoCo for contact-rich simulation
- Gazebo integration with ROS2
- URDF/SDF robot descriptions

### Robotics - Computer Vision
- OpenCV for image processing
- Camera calibration and stereo vision
- Object detection and tracking
- Point cloud processing (Open3D)

## Guidelines
- Use appropriate libraries for the domain
- Follow ROS2 conventions for robotics code
- Use BioPython idioms for bioinformatics
- Write type hints for all functions
- Include docstrings with examples

You have access to tools for file operations and code execution. Use them when needed to complete tasks.
"""


YOU_COLOR = "\u001b[94m"
ASSISTANT_COLOR = "\u001b[93m"
RESET_COLOR = "\u001b[0m"

def resolve_abs_path(path_str: str) -> Path:
    """
    file.py -> /Users/home/mihail/modern-software-dev-lectures/file.py
    """
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path

def read_file_tool(filename: str) -> Dict[str, Any]:
    """
    Read the contents of a file.

    Args:
        filename: The path to the file to read

    Returns:
        Dict with file_path and content
    """
    full_path = resolve_abs_path(filename)
    print(f"  Reading: {full_path}")
    with open(str(full_path), "r") as f:
        content = f.read()
    return {
        "file_path": str(full_path),
        "content": content
    }


def list_files_tool(path: str) -> Dict[str, Any]:
    """
    List files in a directory.

    Args:
        path: The path to the directory to list

    Returns:
        Dict with path and list of files
    """
    full_path = resolve_abs_path(path)
    print(f"  Listing: {full_path}")
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


def edit_file_tool(path: str, old_str: str, new_str: str) -> Dict[str, Any]:
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
    print(f"  Editing: {full_path}")
    if old_str == "":
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


CONFIRM_COLOR = "\u001b[91m"  # Red for warnings


def confirm_execution(tool_name: str, content: str) -> bool:
    """Ask user to confirm before executing code."""
    print(f"\n{CONFIRM_COLOR}⚠️  {tool_name} wil uitvoeren:{RESET_COLOR}")
    print(f"{'─'*50}")
    print(content)
    print(f"{'─'*50}")
    try:
        response = input(f"{CONFIRM_COLOR}Uitvoeren? [y/N]:{RESET_COLOR} ").strip().lower()
        return response in ('y', 'yes', 'j', 'ja')
    except (KeyboardInterrupt, EOFError):
        return False


def run_bash_tool(command: str) -> Dict[str, Any]:
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


def run_python_tool(code: str) -> Dict[str, Any]:
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


def execute_llm_call(client: Client, model: str, conversation: List[Dict[str, Any]], tools: List):
    """Execute LLM call with native tool support."""
    response = client.chat(
        model=model,
        messages=conversation,
        tools=tools,
    )
    return response


def run_coding_agent_loop(client: Client, model: str):
    print(f"Using model: {model}")
    print(f"Tools: {', '.join(t.__name__ for t in TOOLS)}")
    print()

    conversation = [{
        "role": "system",
        "content": SYSTEM_PROMPT
    }]

    while True:
        try:
            user_input = input(f"{YOU_COLOR}You:{RESET_COLOR} ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        conversation.append({
            "role": "user",
            "content": user_input
        })

        # Agent loop - keep processing until no more tool calls
        while True:
            response = execute_llm_call(client, model, conversation, TOOLS)
            message = response.message

            # Check if there are tool calls
            if message.tool_calls:
                # Add assistant message with tool calls to conversation
                conversation.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": message.tool_calls
                })

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments

                    print(f"{ASSISTANT_COLOR}Tool:{RESET_COLOR} {tool_name}({tool_args})")

                    if tool_name not in TOOL_REGISTRY:
                        result = {"error": f"Unknown tool: {tool_name}"}
                    else:
                        # Check if confirmation is needed
                        if tool_name in DANGEROUS_TOOLS:
                            # Format the content for confirmation
                            if tool_name == "run_bash_tool":
                                content = tool_args.get("command", "")
                            else:  # run_python_tool
                                content = tool_args.get("code", "")

                            if confirm_execution(tool_name, content):
                                func = TOOL_REGISTRY[tool_name]
                                result = func(**tool_args)
                            else:
                                result = {"status": "cancelled", "message": "User cancelled execution"}
                        else:
                            func = TOOL_REGISTRY[tool_name]
                            result = func(**tool_args)

                    # Add tool result to conversation
                    conversation.append({
                        "role": "tool",
                        "content": json.dumps(result)
                    })
            else:
                # No tool calls - print response and break
                if message.content:
                    print(f"{ASSISTANT_COLOR}Assistant:{RESET_COLOR} {message.content}")
                conversation.append({
                    "role": "assistant",
                    "content": message.content or ""
                })
                break


def main():
    """Entry point for the parakeet command."""
    args = parse_args()
    host, model = get_ollama_config(args)
    client = Client(host=host)
    run_coding_agent_loop(client, model)


if __name__ == "__main__":
    main()
