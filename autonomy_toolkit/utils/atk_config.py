# SPDX-License-Identifier: MIT
"""
Abstracted helper class :class:`ATKConfig` used for reading/writing configuration files for ``autonomy-toolkit``.
"""

# Imports from atk
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.files import search_upwards_for_file, read_file, file_exists

# Other imports
import tempfile
from typing import Union, List, Optional
from pathlib import Path
import yaml
import mergedeep
import os


class ATKConfig:
    """Helper class that abstracts reading the ``atk.yml`` file that defines configurations.

    Args:
        filename (Union[Path, str]): The name of the file to read. This can be a path or just the name of the file. The file should be located at or above the current working directory.
        services (List[str]): List of services to use when running the ``docker compose`` command.

    Keyword Args:
        compose_file (Union[Path, str]): The name of the compose file to use. Relative to ``filename``. Defaults to ``.atk-compose.yml``.
        env_files (List[Union[Path, str]]): env_files that are passed to docker compose using the ``--env-file`` flag. Defaults to ``[atk.env, .env]``.
    """

    def __init__(
        self,
        filename: Union[Path, str],
        services: List[str],
        *,
        compose_file: Union[Path, str] = ".atk-compose.yml",
        env_files: List[Union[Path, str]] = ["atk.env", ".env"],
    ):
        self.services = services

        # Search for the atk.yml file
        self.atk_yml_path = search_upwards_for_file(filename)
        if self.atk_yml_path is None:
            raise FileNotFoundError(
                f"No '{filename}' file was found in this directory or any parent directories. Make sure you are running this command in an autonomy-toolkit compatible repository. Cannot continue."
            )

        # Set the path of the generated compose file
        self.compose_file = self.atk_yml_path.parent / compose_file
        self.env_files = [self.atk_yml_path.parent / env_file for env_file in env_files]

        # Parse the atk yml file
        self.read()

    def update_services(self, arg):
        """Uses ``mergedeep`` to update the services with the given argument

        Args:
            arg (Any): The argument to update the services with. This can be a dictionary, list, or any other type that ``mergedeep`` supports.
        """
        for service in self.config["services"].values():
            mergedeep.merge(service, arg, strategy=mergedeep.Strategy.ADDITIVE)

    def update_services_with_optionals(self, optionals: List[str]) -> bool:
        """Updates the services with the given optionals.

        The optionals arg defines which optionals to add to the services. The optionals are defined in the ``x-optionals`` field of the atk.yml file.

        Args:
            optionals (List[str]): List of optionals to add to the services.
        """
        if len(optionals) and "x-optionals" not in self.config:
            LOGGER.error(
                "Optionals must be in the 'x-optionals' field at the root of the docker compose file. 'x-optionals' not found."
            )
            return False

        for opt in optionals:
            if opt not in self.config["x-optionals"]:
                LOGGER.error(
                    f"Optional '{opt}' was not found in the 'x-optionals' field."
                )
                return False
            self.update_services(self.config["x-optionals"][opt])

        return True

    def write(self, filename: Optional[Union[Path, str]] = None) -> bool:
        """Dump the config to the compose file to be read by docker compose"""
        filename = filename or self.compose_file

        try:
            with open(self.compose_file, "w") as f:
                yaml.dump(self.config, f)
        except Exception as e:
            LOGGER.fatal(f"Failed to write compose file: {e}")
            return False

        return True

    def read(self, filename: Optional[Union[Path, str]] = None) -> bool:
        """Read the config to the compose file to be used by docker compose"""
        filename = filename or self.atk_yml_path

        try:
            self.config = yaml.safe_load(read_file(filename))
        except yaml.YAMLError as e:
            LOGGER.fatal(f"Failed to read compose file: {e}")
            return False
        return True

    def load(self, client: "DockerClient", opts: List[str]) -> bool:
        """Loads the config file using `docker compose config`

        This allows us to use docker's multi-file loading (e.g. `-f <file1>.yaml -f <file2>.yaml`), `include` and other docker compose features.

        Args:
            client (DockerClient): The docker client to use to write the compose file.
        """
        with tempfile.NamedTemporaryFile("w") as temp_file:
            if not self.write(temp_file.name):
                return False
            returncode = client.run_compose_cmd(
                "-f",
                self.atk_yml_path,
                *opts,
                "config",
                "-o",
                temp_file.name,
                "--no-interpolate",
                "--no-path-resolution",
                "--no-normalize",
                "--no-consistency",
            )
            if returncode:
                LOGGER.error("Could not parse the config file.")
                return False
            if not self.read(temp_file.name):
                return False
        return True
