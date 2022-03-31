# SPDX-License-Identifier: MIT
"""Helpful utilities for interacting with docker. Many of these helpers came from the [python_on_whales](https://gabrieldemarmiesse.github.io/python-on-whales/) package."""

# Imports from autonomy_toolkit
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.containers.container_client import ContainerClient, ContainerException

# External imports
import subprocess
import shutil
import os
from pathlib import Path
from typing import Optional, Any

ENV = os.environ.copy()
ENV["COMPOSE_IGNORE_ORPHANS"] = "true"

class DockerClient(ContainerClient):
    """
    Helper class that provides the :meth:`run` method to execute a command using the ``docker compose``
    entrypoint.

    Args:
        config (ATKConfig): The config definition
        project (str): The name of the project to use. Analagous with ``--project-name`` in ``docker compose``.
        services (List[str]): List of services to use when running the ``docker compose`` command.
        compose_file (str): The name of the compose file to use. Defaults to ``.atk-compose.yml``.
    """

    def __init__(self, config: 'ATKConfig', project: 'str' = None, compose_file: str = '.atk-compose.yml', services = [], **kwargs):
        super().__init__(config, project, compose_file, **kwargs)

        self._services = services

        self._pre = []
        self._pre.extend(["-p", self.project])
        self._pre.extend(["-f", self.compose_file])

        self._post = []

        # Get the docker binary path
        docker_sys = shutil.which("docker")
        if docker_sys is None:
            LOGGER.fatal("The docker binary was not found. It may not be installed properly.")
            exit(-1)
        self._binary = Path(docker_sys)

    def is_installed() -> bool:
        """Checks whether the docker client binary file is present and whether docker compose v2 is installed.

        Returns:
            bool: True if everything checks out, False if not.
        """

        docker_sys = shutil.which("docker")
        docker_binary = Path(docker_sys) if docker_sys is not None else None
        docker_is_installed = docker_binary is not None

        if not docker_is_installed:
            LOGGER.fatal(f"Docker was not found to be installed. Cannot continue.")
            return False

        help_output, _ = ContainerClient._run_cmd(docker_binary, "compose", "--help", stdout=subprocess.PIPE)
        docker_compose_is_installed = "compose" in help_output

        if not docker_compose_is_installed:
            LOGGER.fatal("The command 'docker compose' is not installed. See http://projects.sbel.org/autonomy_toolkit/tutorials/using_the_development_environment.html for more information.")
            return False

        return True
    
    def shell(self, service: str, *args) -> bool:
        """Enter the shell for a specific container.

        Will check for the USERSHELLPATH environment variable in the container.

        Args:
            service (str): The service to run the shell for
        """

        container = self.config.compose["services"][service]["container_name"]
        super().shell(service, container, *args)

    def _run_compose_cmd(self, *args, **kwargs):
        """Run a docker compose command.
        """
        return self._run_cmd(self._binary, "compose", *args, **kwargs)
