"""Helpful utilities for interacting with docker. Many of these helpers came from the [python_on_whales](https://gabrieldemarmiesse.github.io/python-on-whales/) package."""

# Imports from autonomy_toolkit
from autonomy_toolkit.utils.logger import LOGGER

# External imports
import subprocess
import shutil
import os
from pathlib import Path
from typing import Optional, Any

ENV = os.environ.copy()
ENV["COMPOSE_IGNORE_ORPHANS"] = "true"

class DockerException(Exception):
    """
    Exception class that is used by the :class:`DockerComposeClient` when an error occurs

    Args:
        message (Any): The message to be stored in the base class Exception
        stdout (str): The stdout from the command 
        stderr (str): The stderr from the command
    """

    def __init__(self, message: Any, stdout: str = None, stderr: str = None):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


class DockerComposeClient:
    """
    Helper class that provides the :meth:`run` method to execute a command using the ``docker compose``
    entrypoint.

    Args:
        project (str): The name of the project to use. Analagous with ``--project-name`` in ``docker compose``.
        services (List[str]): List of services to use when running the ``docker compose`` command.
        compose_file (str): The name of the compose file to use. Defaults to ``.docker-compose.yml``.
    """

    def __init__(self, project=None, services=[], compose_file='.docker-compose.yml'):
        self._services = services

        self._pre = []
        self._pre.extend(["-p", project])
        self._pre.extend(["-f", compose_file])

        self._post = []

    def run(self, cmd,  *args, **kwargs):
        """Run a command using the system wide ``docker compose`` command

        If cmd is equal to ``exec``, ``exec_cmd`` will expect to be passed as a named argument. If not, a :class:`DockerException` will be thrown.

        Additional positional args (*args) will be passed as command arguments when running the command. Named arguments
        will be passed to :meth:`subprocess.run` (`see their docs <https://docs.python.org/3/library/subprocess.html#subprocess.run>`_).

        Args:
            cmd (str): The command to run.

        Returns:
            Tuple[str, str]: The stdout and stderr resulting from the command as a tuple.
        """
        if cmd == "exec":
            if "exec_cmd" not in kwargs:
                msg = f"The command is '{cmd}' and this requires 'exec_cmd' as another named argument."
                LOGGER.fatal(msg)
                raise DockerException(msg)
            exec_cmd = kwargs.pop("exec_cmd")
            return run_compose_cmd(*self._pre, cmd, *args, exec_cmd, *self._post, **kwargs)
        elif cmd == "run":
            return run_compose_cmd(*self._pre, cmd, *args, *self._post, **kwargs)
        else:
            return run_compose_cmd(*self._pre, cmd, *args, *self._services, *self._post, **kwargs)


def get_docker_client_binary_path() -> Optional[Path]:
    """Return the path of the docker client binary file.

    If ``None`` is returned, the docker client binary is not available and must be downloaded.

    Returns
        Optional[Path]: The path of the docker client binary file.
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
    help_output, _ = run_docker_cmd(
        "compose", "--help", stdout=subprocess.PIPE)
    return "compose" in help_output


def run_compose_cmd(*args, **kwargs):
    """Run a docker compose command.
    """

    return run_docker_cmd("compose", *args, **kwargs)


def run_docker_cmd(*args, **kwargs):
    """Run a docker command.
    """

    docker_binary = get_docker_client_binary_path()
    return _run(*[docker_binary, *args], **kwargs)


def _run(*args, **kwargs):
    cmd = ' '.join([str(arg) for arg in args])
    LOGGER.info(f"{cmd}")

    def post_process_stream(stream: Optional[bytes]):
        if stream is None:
            return ""
        stream = stream.decode()
        if len(stream) != 0 and stream[-1] == "\n":
            stream = stream[:-1]
        return stream

    args = [arg for arg in args if arg]
    completed_process = subprocess.run(args, **kwargs, env=ENV)

    stdout = post_process_stream(completed_process.stdout)
    stderr = post_process_stream(completed_process.stderr)

    if completed_process.returncode:
        raise DockerException(
            f"Got an error code of '{completed_process.returncode}': {cmd}", stdout, stderr)

    return stdout, stderr

# Ports
# From https://github.com/containers/podman-compose/blob/devel/podman_compose.py


def port_dict_to_str(port_desc):
    # NOTE: `mode: host|ingress` is ignored
    cnt_port = port_desc.get("target", None)
    published = port_desc.get("published", None) or ""
    host_ip = port_desc.get("host_ip", None)
    protocol = port_desc.get("protocol", None) or "tcp"
    if not cnt_port:
        raise ValueError("target container port must be specified")
    if host_ip:
        ret = f"{host_ip}:{published}:{cnt_port}"
    else:
        ret = f"{published}:{cnt_port}" if published else f"{cnt_port}"
    if protocol != "tcp":
        ret += f"/{protocol}"
    return ret


def norm_ports(ports_in):
    if not ports_in:
        ports_in = []
    if isinstance(ports_in, str):
        ports_in = [ports_in]
    ports_out = []
    for port in ports_in:
        if isinstance(port, dict):
            port = port_dict_to_str(port)
        elif not isinstance(port, str):
            raise TypeError("port should be either string or dict")
        ports_out.append(port)
    return ports_out

def is_port_available(port):
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        in_use = s.connect_ex(('localhost', port)) == 0

    return not in_use

def find_available_port(port, trys=5):
    orig_port = port
    for _ in range(trys):
        # Check if port is in use
        in_use = not is_port_available(port)

        if in_use:
            LOGGER.info(
                f"Port '{port}' already in use. Trying with '{port+1}'.")
            port += 1
        else:
            break
    return port if not in_use else None
