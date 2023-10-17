# SPDX-License-Identifier: MIT
"""Helpful utilities for interacting with docker."""

# Imports from autonomy_toolkit
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.atk_config import ATKConfig
from autonomy_toolkit.utils.files import file_exists

# External imports
import subprocess
import os
from typing import Optional, Any, List, Dict

ENV = os.environ.copy()
ENV["COMPOSE_IGNORE_ORPHANS"] = 1


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


class DockerClient:
    """Client interface for interacting with docker compose orchestration.

    Args:
        config (ATKConfig): The ATK configuration object.
        dry_run (bool): Whether to actually run the commands or just print them. Use DEBUG logging level to see the commands.
        opts (List[str]): Options to pass to the ``docker compose`` command.
        args (List[str]): Arguments to pass to the ``docker compose <command>`` command.
    """

    def __init__(
        self,
        config: ATKConfig,
        *,
        dry_run: bool = False,
        opts: List[str] = [],
        args: List[str] = [],
    ):
        self.config = config
        self.dry_run = dry_run
        self.services = config.services

        # Options passed to the compose command
        # i.e. .. compose ..opts <command>
        self._opts = opts
        self._opts = ["-f", self.config.compose_file] + self._opts
        for env_file in self.config.env_files:
            if file_exists(env_file):
                self._opts = ["--env-file", env_file] + self._opts

        # Args passed to the compose subcommand
        # i.e. .. compose <command> ...args
        self._args = args

    def down(self) -> bool:
        """Bring down the containers.

        Returns:
            bool: Whether the command succeeded.
        """
        return self.run_cmd("down")

    def build(self) -> bool:
        """Build the images.

        Returns:
            bool: Whether the command succeeded.
        """
        return self.run_cmd("build")

    def up(self) -> bool:
        """Bring up the containers.

        Returns:
            bool: Whether the command succeeded.
        """
        return self.run_cmd("up", "-d")

    def run(self) -> bool:
        """Run a command in a container.

        Returns:
            bool: Whether the command succeeded.
        """
        return self.run_cmd("run")

    def attach(self) -> bool:
        """Attach to a container.

        NOTE: We assume a shell session is desired.

        This is somewhat difficult, as we don't know the default shell of the user in the container. We therefore have to determine this at runtime with a pretty nasty command.

        Returns:
            bool: Whether the command succeeded.
        """
        # fmt: off
        exec_cmd = "($(awk -F: -v user=\"$(whoami)\" '$1 == user {print $NF}' /etc/passwd) || true)"
        # fmt: on
        self._args += ["sh", "-c", exec_cmd]

        return self.run_cmd("exec")

    def run_cmd(self, cmd, *args, without_ots: bool = False, **kwargs) -> bool:
        """Run a command using the system wide ``compose`` command

        Additional positional args (``*args``) will be passed as command arguments when running the command.
        Named arguments will be passed to :meth:`subprocess.run`
        (`see their docs <https://docs.python.org/3/library/subprocess.html#subprocess.run>`_).

        Args:
            cmd (str): The command to run.

        Returns:
            Bool: Whether the command succeeded.
        """

        return self.run_compose_cmd(
            *self._opts, cmd, *args, *self.services, *self._args, **kwargs
        )

    def run_compose_cmd(self, *args, **kwargs) -> bool:
        """Run a docker compose command."""
        return self._run_cmd("docker", "compose", *args, **kwargs)

    def _run_cmd(self, *args, return_output=False, **kwargs):
        if return_output:
            kwargs["stdout"] = subprocess.PIPE
            kwargs["stderr"] = subprocess.PIPE

        cmd = " ".join([str(arg) for arg in args])
        LOGGER.debug(f"{cmd}")

        def post_process_stream(stream: Optional[bytes]):
            if stream is None:
                return ""
            stream = stream.decode()
            if len(stream) != 0 and stream[-1] == "\n":
                stream = stream[:-1]
            return stream

        args = [arg for arg in args if arg]
        if not self.dry_run:
            completed_process = subprocess.run(args, **kwargs)
        else:
            LOGGER.info(f"'dry_run' set to true. Not running command.")
            return "", ""

        stdout = post_process_stream(completed_process.stdout)
        stderr = post_process_stream(completed_process.stderr)

        if completed_process.returncode:
            LOGGER.debug(
                f"Got an error code of '{completed_process.returncode}': {cmd}: {stdout}: {stderr}",
            )

        if return_output:
            return stdout, stderr
        return completed_process.returncode
