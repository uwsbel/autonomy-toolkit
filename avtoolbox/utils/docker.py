"""Helpful utilities for interacting with docker. Many of these helpers came from the [python_on_whales](https://gabrieldemarmiesse.github.io/python-on-whales/) package."""

# Imports from av
from avtoolbox.utils.logger import LOGGER

# External imports
import subprocess
import shutil
from pathlib import Path
from typing import Optional

class DockerComposeClient:
    def __init__(self, project=None, services=[], compose_file='docker-compose.yml'):
        self._services = services

        self._pre = []
        self._pre.extend(["-p", project])
        self._pre.extend(["-f", compose_file])

        self._post = []

    def run(self, cmd,  *args, **kwargs):
        if cmd == "exec":
            exec_cmd = kwargs.pop("exec_cmd")
            run_compose_cmd(*self._pre, cmd, *args, *self._services, exec_cmd, *self._post, **kwargs)
        else:
            run_compose_cmd(*self._pre, cmd, *args, *self._services, *self._post, **kwargs)

def get_docker_client_binary_path() -> Optional[Path]:
    """Return the path of the docker client binary file.

    If `None` is returned, the docker client binary is not available and must be downloaded.

    Returns
        `Optional[Path]`: The path of the docker client binary file.
    """
    docker_sys = shutil.which("docker")
    if docker_sys is not None:
        return Path(docker_sys)
    else:
        return None

def compose_is_installed() -> bool:
    """Returns `True` if docker compose (the one written in Go)
    is installed and working.
    
    Returns:
        bool: whether docker compose (v2) is installed.
    """
    help_output = run_docker_cmd("compose", "--help", stdout=subprocess.PIPE)
    return "compose" in help_output

def run_compose_cmd(*args, **kwargs):
    return run_docker_cmd("compose", *args, **kwargs)

def run_docker_cmd(*args, **kwargs):
    """Run a docker command.
    """

    docker_binary = get_docker_client_binary_path()
    return _run([docker_binary, *args], **kwargs)

def _run(*args, **kwargs):
    LOGGER.info(f"{' '.join([str(arg) for arg in args[0]])}")

    def post_process_stream(stream: Optional[bytes]):
        if stream is None:
            return ""
        stream = stream.decode()
        if len(stream) != 0 and stream[-1] == "\n":
            stream = stream[:-1]
        return stream

    completed_process = subprocess.run(*args, **kwargs)
    return post_process_stream(completed_process.stdout)

