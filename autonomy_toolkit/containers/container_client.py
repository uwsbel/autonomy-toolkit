# SPDX-License-Identifier: MIT
"""Base class that container runtimes will inherit from to be used by ATK commands."""

# Imports from atk
from autonomy_toolkit.utils.logger import LOGGER

# Other imports
from abc import ABC, abstractmethod
from typing import Any, Optional
import subprocess

class ContainerException(Exception):
    """
    Exception class that is used by the :class:`ContainerClient` when an error occurs

    Args:
        message (Any): The message to be stored in the base class Exception
        stdout (str): The stdout from the command 
        stderr (str): The stderr from the command
    """

    def __init__(self, message: Any, stdout: str = None, stderr: str = None):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr

class ContainerClient(ABC):
    """
    Base class that provides an entrypoint for specific container runtimes (i.e. Docker or Singularity).

    Args:
        config (ATKConfig): The config definition
        project (str): The name of the project to use. Analagous with ``--project-name`` in ``docker compose``.
        compose_file (str): The name of the compose file to use. Defaults to ``.atk-compose.yml``.
    """

    def __init__(self, config: 'ATKConfig', project=None, compose_file='.atk-compose.yml', **kwargs):
        self.config = config
        self.project = project
        self.compose_file = compose_file

    @staticmethod
    @abstractmethod
    def is_installed() -> bool:
        """Should check if all the necessary packages/binaries are installed and return True, if yes.

        Returns:
            bool: True if everything is installed/setup properly.
        """
        pass

    def down(self, *args) -> bool:
        """Bring down the containers.

        Returns:
            bool: Whether the command succeeded.
        """
        return self.run_cmd("down", *args)

    def build(self, *args) -> bool:
        """Build the images.

        Returns:
            bool: Whether the command succeeded.
        """
        return self.run_cmd("build", *args)

    def up(self, *args) -> bool:
        """Bring up the containers.

        Returns:
            bool: Whether the command succeeded.
        """
        return self.run_cmd("up", "-d", *args)

    def run(self, *args) -> bool:
        """Run a command in a container.

        Returns:
            bool: Whether the command succeeded.
        """
        return self.run_cmd("run", *args) 


    def shell(self, service: str, container: str, *args, exec_flags=None) -> bool:
        """Enter the shell for a specific container.

        Will check for the USERSHELLPATH and USERSHELLPROFILE environment variable in the container (where the latter isn't required).

        Args:
            service (str): The service to enter
            container (str): The container to enter
        """
        try:
            env, err = self._run_cmd(self._binary, "exec", container, "env", stdout=-1, stderr=-1)
        except ContainerException as e:
            if "Error: No such container: " in e.stderr:
                LOGGER.fatal(f"Please rerun the command with '--up'. The container cannot be attached to since it hasn't been created.")
                return False
            raise e

        if "USERSHELLPATH" not in env:
            LOGGER.fatal(f"To attach to a container using autonomy_toolkit, the environment variable \"USERSHELLPATH\" must be defined within the container. Was not found, please add it to the container.")
            return False
        shellcmd = [env.split("USERSHELLPATH=")[1].split('\n')[0]]

        if "USERSHELLPROFILE" in env:
            shellprofile = env.split("USERSHELLPROFILE=")[1].split('\n')[0]
            shellcmd += ["--rcfile", shellprofile]

        self.run_cmd("exec", exec_flags, service, *args, exec_cmd=shellcmd)

        return True

    def run_cmd(self, cmd,  *args, **kwargs) -> 'Tuple[str, str]':
        """Run a command using the system wide ``compose`` command

        If cmd is equal to ``exec``, ``exec_cmd`` will expect to be passed as a named argument. 
        If not, a :class:`ContainerException` will be thrown.

        Additional positional args (*args) will be passed as command arguments when running the command. 
        Named arguments will be passed to :meth:`subprocess.run` 
        (`see their docs <https://docs.python.org/3/library/subprocess.html#subprocess.run>`_).

        Args:
            cmd (str): The command to run.

        Returns:
            Tuple[str, str]: The stdout and stderr resulting from the command as a tuple.
        """
        if cmd == "exec":
            if "exec_cmd" not in kwargs:
                msg = f"The command is '{cmd}' and this requires 'exec_cmd' as another named argument."
                LOGGER.fatal(msg)
                raise ContainerException(msg)
            exec_cmd = kwargs.pop("exec_cmd")
            return self._run_compose_cmd(*self._pre, cmd, *args, *exec_cmd, *self._post, **kwargs)
        elif cmd == "run":
            return self._run_compose_cmd(*self._pre, cmd, *args, *self._post, **kwargs)
        else:
            return self._run_compose_cmd(*self._pre, cmd, *args, *self._services, *self._post, **kwargs)

    @abstractmethod
    def _run_compose_cmd(self, *args, **kwargs):
        pass

    @staticmethod
    def _run_cmd(*args, **kwargs):
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
        completed_process = subprocess.run(args, **kwargs)

        stdout = post_process_stream(completed_process.stdout)
        stderr = post_process_stream(completed_process.stderr)

        if completed_process.returncode:
            raise ContainerException(
                f"Got an error code of '{completed_process.returncode}': {cmd}", stdout, stderr)

        return stdout, stderr
