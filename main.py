import argparse
import inspect
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


SYSTEM_PROMPT = """
You are a coding assistant specialized in biotech and robotics applications.

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

## Tools

{tool_list_repr}

When you want to use a tool, reply with exactly one line in the format: 'tool: TOOL_NAME({{JSON_ARGS}})' and nothing else.
Use compact single-line JSON with double quotes. After receiving a tool_result(...) message, continue the task.
If no tool is needed, respond normally.
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
    Gets the full content of a file provided by the user.
    :param filename: The name of the file to read.
    :return: The full content of the file.
    """
    full_path = resolve_abs_path(filename)
    print(full_path)
    with open(str(full_path), "r") as f:
        content = f.read()
    return {
        "file_path": str(full_path),
        "content": content
    }

def list_files_tool(path: str) -> Dict[str, Any]:
    """
    Lists the files in a directory provided by the user.
    :param path: The path to a directory to list files from.
    :return: A list of files in the directory.
    """
    full_path = resolve_abs_path(path)
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
    Replaces first occurrence of old_str with new_str in file. If old_str is empty,
    create/overwrite file with new_str.
    :param path: The path to the file to edit.
    :param old_str: The string to replace.
    :param new_str: The string to replace with.
    :return: A dictionary with the path to the file and the action taken.
    """
    full_path = resolve_abs_path(path)
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
    Executes a bash command. Requires user confirmation.
    :param command: The bash command to execute.
    :return: stdout, stderr, and return code.
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
    Executes Python code. Requires user confirmation.
    :param code: The Python code to execute.
    :return: stdout, stderr, and return code.
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


TOOL_REGISTRY = {
    "read_file": read_file_tool,
    "list_files": list_files_tool,
    "edit_file": edit_file_tool,
    "run_bash": run_bash_tool,
    "run_python": run_python_tool,
}

def get_tool_str_representation(tool_name: str) -> str:
    tool = TOOL_REGISTRY[tool_name]
    return f"""
    Name: {tool_name}
    Description: {tool.__doc__}
    Signature: {inspect.signature(tool)}
    """

def get_full_system_prompt():
    tool_str_repr = ""
    for tool_name in TOOL_REGISTRY:
        tool_str_repr += "TOOL\n===" + get_tool_str_representation(tool_name)
        tool_str_repr += f"\n{'='*15}\n"
    return SYSTEM_PROMPT.format(tool_list_repr=tool_str_repr)

def extract_tool_invocations(text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Return list of (tool_name, args) requested in 'tool: name({...})' lines.
    The parser expects single-line, compact JSON in parentheses.
    """
    invocations = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("tool:"):
            continue
        try:
            after = line[len("tool:"):].strip()
            name, rest = after.split("(", 1)
            name = name.strip()
            if not rest.endswith(")"):
                continue
            json_str = rest[:-1].strip()
            args = json.loads(json_str)
            invocations.append((name, args))
        except Exception:
            continue
    return invocations

def execute_llm_call(client: Client, model: str, conversation: List[Dict[str, str]]):
    response = client.chat(
        model=model,
        messages=conversation,
    )
    return response['message']['content']


def run_coding_agent_loop(client: Client, model: str):
    print(f"Using model: {model}")
    print(get_full_system_prompt())
    conversation = [{
        "role": "system",
        "content": get_full_system_prompt()
    }]
    while True:
        try:
            user_input = input(f"{YOU_COLOR}You:{RESET_COLOR}:")
        except (KeyboardInterrupt, EOFError):
            break
        conversation.append({
            "role": "user",
            "content": user_input.strip()
        })
        while True:
            assistant_response = execute_llm_call(client, model, conversation)
            tool_invocations = extract_tool_invocations(assistant_response)
            if not tool_invocations:
                print(f"{ASSISTANT_COLOR}Assistant:{RESET_COLOR}: {assistant_response}")
                conversation.append({
                    "role": "assistant",
                    "content": assistant_response
                })
                break
            for name, args in tool_invocations:
                if name not in TOOL_REGISTRY:
                    resp = {"error": f"Unknown tool: {name}"}
                else:
                    tool = TOOL_REGISTRY[name]
                    resp = ""
                    print(name, args)
                    if name == "read_file":
                        resp = tool(args.get("filename", "."))
                    elif name == "list_files":
                        resp = tool(args.get("path", "."))
                    elif name == "edit_file":
                        resp = tool(args.get("path", "."),
                                    args.get("old_str", ""),
                                    args.get("new_str", ""))
                    elif name == "run_bash":
                        cmd = args.get("command", "")
                        if confirm_execution("run_bash", cmd):
                            resp = tool(cmd)
                        else:
                            resp = {"status": "cancelled", "message": "User cancelled execution"}
                    elif name == "run_python":
                        code = args.get("code", "")
                        if confirm_execution("run_python", code):
                            resp = tool(code)
                        else:
                            resp = {"status": "cancelled", "message": "User cancelled execution"}
                conversation.append({
                    "role": "user",
                    "content": f"tool_result({json.dumps(resp)})"
                })


def main():
    """Entry point for the parakeet command."""
    args = parse_args()
    host, model = get_ollama_config(args)
    client = Client(host=host)
    run_coding_agent_loop(client, model)


if __name__ == "__main__":
    main()
