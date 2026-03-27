"""
NEXUS Cerebro — Docker-in-Docker Sandbox Tool.

Gives AI agents their own persistent compute environment.
Each sandbox is a Docker container with resource limits.
State persists between sessions via mounted volumes.
"""

import docker
from docker.errors import DockerException, NotFound

from agno.tools.decorator import tool

_SANDBOX_IMAGE = "python:3.12-slim"
_SANDBOX_PREFIX = "nexus-sandbox-"
_SANDBOX_VOLUME_BASE = "/opt/sandboxes"
_MEMORY_LIMIT = "512m"
_CPU_LIMIT = 1.0  # 1 core max


def _get_client() -> docker.DockerClient:
    """Get Docker client. Fails gracefully if Docker socket is not mounted."""
    try:
        return docker.from_env()
    except DockerException:
        raise RuntimeError(
            "Docker socket not available. Mount /var/run/docker.sock to enable sandboxes."
        )


@tool()
def create_sandbox(sandbox_id: str = "default") -> str:
    """Create or start a persistent sandbox container for code execution.

    The sandbox is an isolated Docker container where you can run code,
    install packages, and store files. State persists between sessions.

    Args:
        sandbox_id: Unique identifier for this sandbox (default: "default").
    """
    client = _get_client()
    name = f"{_SANDBOX_PREFIX}{sandbox_id}"

    # Check if sandbox already exists
    try:
        container = client.containers.get(name)
        if container.status != "running":
            container.start()
        return f"SANDBOX_READY: {name} (resumed existing)"
    except NotFound:
        pass

    # Create new sandbox
    container = client.containers.run(
        _SANDBOX_IMAGE,
        command="sleep infinity",
        name=name,
        detach=True,
        mem_limit=_MEMORY_LIMIT,
        nano_cpus=int(_CPU_LIMIT * 1e9),
        volumes={
            f"{_SANDBOX_VOLUME_BASE}/{sandbox_id}": {
                "bind": "/workspace",
                "mode": "rw",
            }
        },
        working_dir="/workspace",
        network_mode="none",  # No network access by default (security)
    )

    return f"SANDBOX_CREATED: {name} (image={_SANDBOX_IMAGE}, memory={_MEMORY_LIMIT})"


@tool()
def run_in_sandbox(code: str, sandbox_id: str = "default") -> str:
    """Execute Python code inside the sandbox container.

    Args:
        code: Python code to execute.
        sandbox_id: Which sandbox to use (default: "default").

    Returns:
        stdout + stderr from the execution (truncated to 4000 chars).
    """
    client = _get_client()
    name = f"{_SANDBOX_PREFIX}{sandbox_id}"

    try:
        container = client.containers.get(name)
    except NotFound:
        return f"ERROR: Sandbox '{sandbox_id}' not found. Create it first with create_sandbox."

    if container.status != "running":
        container.start()

    exit_code, output = container.exec_run(
        ["python3", "-c", code],
        workdir="/workspace",
    )

    result = output.decode("utf-8", errors="replace")[:4000]
    status = "OK" if exit_code == 0 else f"ERROR (exit={exit_code})"
    return f"[{status}]\n{result}"


@tool()
def sandbox_shell(command: str, sandbox_id: str = "default") -> str:
    """Execute a shell command inside the sandbox container.

    Use for: installing packages (pip install), listing files, etc.

    Args:
        command: Shell command to execute.
        sandbox_id: Which sandbox to use (default: "default").
    """
    client = _get_client()
    name = f"{_SANDBOX_PREFIX}{sandbox_id}"

    try:
        container = client.containers.get(name)
    except NotFound:
        return f"ERROR: Sandbox '{sandbox_id}' not found. Create it first."

    if container.status != "running":
        container.start()

    exit_code, output = container.exec_run(
        ["sh", "-c", command],
        workdir="/workspace",
    )

    result = output.decode("utf-8", errors="replace")[:4000]
    status = "OK" if exit_code == 0 else f"ERROR (exit={exit_code})"
    return f"[{status}]\n{result}"


@tool()
def stop_sandbox(sandbox_id: str = "default") -> str:
    """Stop a sandbox container. State is preserved for next session.

    Args:
        sandbox_id: Which sandbox to stop.
    """
    client = _get_client()
    name = f"{_SANDBOX_PREFIX}{sandbox_id}"

    try:
        container = client.containers.get(name)
        container.stop(timeout=10)
        return f"SANDBOX_STOPPED: {name} (state preserved)"
    except NotFound:
        return f"SANDBOX_NOT_FOUND: {sandbox_id}"
