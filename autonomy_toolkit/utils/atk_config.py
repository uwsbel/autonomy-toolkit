# SPDX-License-Identifier: MIT
"""
Abstracted helper class :class:`ATKConfig` used for reading/writing configuration files for ``autonomy-toolkit``.
"""

# Imports from atk
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.files import search_upwards_for_file, read_file, file_exists

# Other imports
from typing import Union, List
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
        compose_file (Union[Path, str]): The name of the compose file to use. Defaults to ``.atk-compose.yml``.
    """

    def __init__(
        self,
        filename: Union[Path, str],
        services: List[str],
        *,
        compose_file: Union[Path, str] = ".atk-compose.yml",
    ):
        self.services = services

        # Search for the atk.yml file
        self.atk_yml_path = search_upwards_for_file(filename)
        if self.atk_yml_path is None:
            raise FileNotFoundError(
                f"No '{filename}' file was found in this directory or any parent directories. Make sure you are running this command in an autonomy-toolkit compatible repository. Cannot continue."
            )

        # Save the generated compose file at the same level as the atk.yml file
        self.compose_file = self.atk_yml_path.parent / compose_file

        # Parse the atk yml file
        try:
            self.config = yaml.safe_load(read_file(self.atk_yml_path))
        except yaml.YAMLError as e:
            LOGGER.info(e)
            raise Exception(
                f"An error occurred while parsing {filename}. Set verbosity to info for more details."
            )

    def update_services(self, arg):
        """Uses ``mergedeep`` to update the services with the given argument

        Args:
            arg (Any): The argument to update the services with. This can be a dictionary, list, or any other type that ``mergedeep`` supports.
        """
        for service in self.config["services"].values():
            mergedeep.merge(service, arg, strategy=mergedeep.Strategy.ADDITIVE)

    def update_services_with_optionals(self, optionals: List[str]):
        """Updates the services with the given optionals.

        The optionals arg defines which optionals to add to the services. The optionals are defined in the ``x-optionals`` field of the atk.yml file.

        Args:
            optionals (List[str]): List of optionals to add to the services.
        """
        for opt in optionals:
            if opt not in self.config["x-optionals"]:
                LOGGER.warn(
                    f"Optional '{opt}' was not found in the 'x-optionals' field. Ignoring."
                )
                continue
            self.update_services(self.config["x-optionals"][opt])

    def write(self) -> bool:
        """Dump the config to the compose file to be read by docker compose"""
        # Rewrite the compose file
        try:
            with open(self.compose_file, "w") as f:
                yaml.dump(self.config, f)
        except Exception as e:
            LOGGER.fatal(f"Failed to write compose file: {e}")
            return False

        return True
