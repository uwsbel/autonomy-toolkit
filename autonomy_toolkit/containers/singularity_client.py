# SPDX-License-Identifier: MIT
"""Helpful utilities for interacting with singularity."""

# Imports from autonomy_toolkit
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.parsing import ATKTextFile
from autonomy_toolkit.utils.atk_config import ATKConfig
from autonomy_toolkit.containers.container_client import ContainerClient, ContainerException

# External imports
from pathlib import Path
import shutil
from typing import Optional, Any
import json
import tempfile
import os

class SingularityClient(ContainerClient):
    """
    Helper class that provides the :meth:`run` method to execute a command using the ``singularity compose``
    entrypoint.

    Args:
        project (str): The name of the project to use. Analagous with ``--project-name`` in ``singularity compose``.
        services (List[str]): List of services to use when running the ``singularity compose`` command.
        compose_file (str): The name of the compose file to use. Defaults to ``.atk-compose.yml``.
    """

    def __init__(self, config: 'ATKConfig', project: 'str' = None, compose_file: str = '.atk-compose.yml', services = [], **kwargs):
        super().__init__(config, project, compose_file, **kwargs)

        self._services = services

        self._pre = []
        self._pre.extend(["-p", self.project])
        self._pre.extend(["-f", self.compose_file])
        self._pre.append("--debug")

        self._post = []

        # Get the singularity binary path
        singularity_sys = shutil.which("singularity")
        if singularity_sys is None:
            LOGGER.fatal("The singularity binary was not found. It may not be installed properly.")
            exit(-1)
        self._binary = Path(singularity_sys)

        # Make custom updates to the config file
        self._tmpdirs = []
        self._tmpfiles = []
        self._update_config()

    def is_installed() -> bool:
        """Checks whether the docker client binary file is present and whether docker compose v2 is installed.

        Returns:
            bool: True if everything checks out, False if not.
        """

        singularity_sys = shutil.which("singularity")
        singularity_is_installed = singularity_sys is not None
        if not singularity_is_installed:
            LOGGER.fatal(f"Singularity was not found to be installed. Cannot continue.")

        singularity_compose_sys = shutil.which("singularity-compose")
        singularity_compose_is_installed = singularity_compose_sys is not None

        if not singularity_compose_is_installed:
            LOGGER.fatal("The command 'singularity-compose' is not installed. Visit https://singularityhub.github.io/singularity-compose/ for more information.")

        return singularity_is_installed and singularity_compose_is_installed

    def _update_config(self) -> bool:
        """Update the config based on the specific runtime that implements this class.
        """

        # Need to pass --no-home to not bind the user directory to the container
        # This is consistent to docker, which is what we're aiming for
        compose = self.config.compose
        compose["instances"] = compose.pop("services")
        for service_name, service in compose["instances"].items():
            tmpdir = tempfile.TemporaryDirectory(dir=Path(".").resolve())
            self._tmpdirs.append(tmpdir)

            # Replicate docker and don't share home
            start = {"options": ["no-home"]}
            service["start"] = ATKConfig._merge_dictionaries(start, service.get("start", {}))

            if "environment" in service:
                atk_env = f".atk-singularity-{service_name}.env"
                with open(atk_env, "w") as f:
                    for e,v in service["environment"].items():
                        f.write(f"export {e}={v}\n")

                vol = [f"./{str(atk_env)}:/.singularity.d/env/atk.sh"]
                if "volumes" in service:
                    service["volumes"].extend(vol)
                else:
                    service["volumes"] = vol 

            # We want singularity compose to not use any networks
            # This means that singularity will use the host network by default
            if "network" not in service:
                service["network"] = {"enable": False}

            service.pop("ports", None) # Ports require sudo; we'll use the host network anyways

            if "build" in service:
                build = service["build"]
                build["options"] = []
                build["options"].append("fakeroot")
                build["options"].append("fix-perms")
                build["options"].append(f"tmpdir={tmpdir.name}")

                # The name for the build definition in singularity compose is "recipe", not "dockerfile"
                if "dockerfile" in build:
                    dockerfile = build.pop("dockerfile")
                    build["recipe"] = dockerfile.replace("dockerfile", "singularity")

                # Singularity def files don't support arguments, so we'll implement this ourselves
                if "args" in build:
                    args = build["args"]

                    context = (Path(self.config.project_root) / build["context"]).resolve()
                    recipe = (Path(context) / build["recipe"]).resolve()
                    temp_recipe = str(recipe) + ".temp"

                    temp_recipe_file = ATKTextFile(recipe)
                    temp_recipe_file.replace_vars(args)
                    temp_recipe_file.write(temp_recipe)

                    build["recipe"] = temp_recipe
                    self._tmpfiles.append(temp_recipe)

        self.config.write_compose(compose)

    def build(self, *args) -> bool:
        """Build the images.

        ``singularity-compose`` won't overwrite an existing sif it already exists. Do that here.

        Returns:
            bool: Whether the command succeeded.
        """

        for service_name, service in self.config.compose["instances"].items():
            if service_name not in self._services or "build" not in service:
                continue

            build = service["build"]

            sif = Path(build.get("context", ".")) / f"{service_name}.sif"
            if sif.exists():
                res = input(f"The image for {service_name} has already been built. Okay to overwrite? (y|[n]) ") or "n"
                if res == "y":
                    os.unlink(sif)
                elif res == "n":
                    LOGGER.info(f"Not overwriting {service_name}.sif.")
                else:
                    LOGGER.warn(f"Response '{res}' is not recognized. Pass either 'y' or 'n'. Not overwriting {service_name}.sif.")
        return super().build(*args)

    def up(self, *args) -> bool:
        """Bring up the containers.

        Returns:
            bool: Whether the command succeeded.
        """
        if "--resolv" not in args:
            args = [*args, "--no-resolv"]
        return super().up(*args)

    def run(self, service, *exec_cmd) -> bool:
        """Run a command in a container.

        Returns:
            bool: Whether the command succeeded.
        """
        # Load in some configs
        # working_dir is not supported in singularity-compose, so we basically implement it here
        pwd = self.config.compose["instances"][service].get("working_dir", "/")

        # Start up the containers
        if service in self.run_cmd("ps", service, stdout=-1)[0]:
            LOGGER.warn(f"'{service}' is already up. You may need to tear it down (i.e. '--down') for '--run' to work correctly.")
        self.up()
        return self.run_cmd("exec", f"--pwd={pwd}", f"instance://{service}", exec_cmd=exec_cmd) 

    def shell(self, service: str, *args) -> bool:
        """Enter the shell of the given container.

        Should check for the USERSHELLPATH environment variable in the container.

        Args:
            service (str): The service to enter
        """
        # Load in some configs
        # working_dir is not supported in singularity-compose, so we basically implement it here
        pwd = self.config.compose["instances"][service].get("working_dir", "/")

        ret = super().shell(f"instance://{service}", f"instance://{service}", *args, exec_flags=f"--pwd={pwd}" )

        return ret

    def run_cmd(self, cmd,  *args, **kwargs) -> 'Tuple[str, str]':
        """Run a command using the system wide ``docker-compose`` command

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
            return self._run_cmd(self._binary, cmd, *args, *exec_cmd, *self._post, **kwargs)
        else:
            return super().run_cmd(cmd, *args, **kwargs)

    def _run_compose_cmd(self, *args, **kwargs):
        """Run a docker compose command.
        """
        return self._run_cmd("singularity-compose", *args, **kwargs)

    def __del__(self):
        for tmpfile in self._tmpfiles:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)

        for tmpdir in self._tmpdirs:
            tmpdir.cleanup()
