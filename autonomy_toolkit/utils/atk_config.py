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


class ATKConfig:
    """Helper class that abstracts reading the ``atk.yml`` file that defines configurations"""

    def __init__(
        self,
        filename: Union[Path, str],
        services: List[str] = [],
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

        # Grab the project name
        if "x-project" not in self.config:
            raise Exception(
                f"The 'x-project' field was not found in {filename}. Cannot continue."
            )
        self.project = self.config["x-project"]

    def update_services(self, arg) -> bool:
        for service in self.config["services"].values():
            mergedeep.merge(service, arg, strategy=mergedeep.Strategy.ADDITIVE)

    def update_services_with_optionals(self, optionals: List[str]):
        for opt in optionals:
            if opt not in self.config["x-optionals"]:
                LOGGER.warn(
                    f"Optional '{opt}' was not found in the 'x-optionals' field. Ignoring."
                )
                continue
            self.update_services(self.config["x-optionals"][opt])

    def write(self) -> bool:
        # Rewrite the compose file
        with open(self.compose_file, "w") as f:
            yaml.dump(self.config, f)
