# SPDX-License-Identifier: MIT
"""
CLI command that handles allows generic handling of an ATK config file for running docker containers
"""

# Imports from atk
from autonomy_toolkit.utils.atk_config import ATKConfig
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.files import search_upwards_for_file
# from autonomy_toolkit.utils.docker import get_docker_client_binary_path, compose_is_installed, DockerComposeClient, DockerException

# Other imports
import argparse

def _run_run(args):
    LOGGER.info("Running 'run' entrypoint...")

    # Check docker is installed
    if get_docker_client_binary_path() is None:
        LOGGER.fatal(f"Docker was not found to be installed. Cannot continue.")
        return

    # Check docker compose is installed
    LOGGER.debug("Checking if 'docker compose' (V2) is installed...")
    if not compose_is_installed():
        LOGGER.fatal("The command 'docker compose' is not installed. See http://projects.sbel.org/autonomy_toolkit/tutorials/using_the_development_environment.html for more information.")
        return
    LOGGER.debug("'docker compose' (V2) is installed.")

    # Grab the ATK config file
    LOGGER.debug(f"Loading '{args.filename}' file.")
    config = ATKConfig(args.filename)

    # Add some required attributes
    config.add_required_attribute("services")

    # Add some default custom attributes
    config.add_custom_attribute("services", dict, delete=False)

    # Parse the ATK config file
    if not config.parse():
        return

    # If not service is passed and only one service is present in the ATK config file, we'll assume this is the one
    # that wants to be used
    if len(config.services) == 1:
        args.services = [next(iter(config.services))]

    if args.services is None or len(args.services) != 1:
        LOGGER.fatal("The 'run' command requires one service.")
        return

    # Complete the arguments
    if not args.dry_run:

        try:
            # Write the compose file
            config.generate_compose(use_default_compose=False)

            # Write the dockerignore
            config.generate_ignore()

            # Keep track of the number of users so we aren't deleting files when they need to persist
            config.update_user_count(1)

            # Create the abstracted client we'll use for interacting with docker compose
            client = DockerComposeClient(project=config.project, services=args.services, compose_file=config.docker_compose_path)

            # Run!!
            LOGGER.info(f"Running...")
            client.run("run", "--service-ports", "--rm", args.services[0], *args.args)

        except DockerException as e:
            LOGGER.fatal(e)
            if e.stderr:
                LOGGER.fatal(e.stderr)
        finally:
            if config.update_user_count(-1) == 0:
                config.cleanup(args.keep_yml)

def _init(subparser):
    """Entrypoint for the `run` command

    This entrypoint provides easy running of generic docker containers. It's exactly a wrapper of docker compose,
    where the ATK config file is used. This allows `atk` to be used.

    To use this entrypoint, you simply need to run the following:

    ```bash
    atk run
    ```

    It will search for an ATK config file in all parent directories (defaults for looking for `.atk.yml`; this can
    be overridden with `--filename`) and then use `docker compose run`. Not many checks are done to ensure the
    file is formatted correctly for `docker compose`, so please refer to any errors output from the command for debugging.
    """
    LOGGER.debug("Initializing 'run' entrypoint...")

    # Add arguments
    subparser.add_argument("-s", "--services", nargs='+', help="The services to use. Defaults to 'all' or whatever 'default_services' is set to in .atk.yml. 'dev' or 'all' is required for the 'attach' argument. If 'all' is passed, all the services are used.", default=None)
    subparser.add_argument("-f", "--filename", help="The ATK config file. Defaults to '.atk.yml'", default='.atk.yml')
    subparser.add_argument("--args", nargs=argparse.REMAINDER, help="Additional arguments to pass to the docker compose command. No logic is done on the args, the docker command will error out if there is a problem.", default=[])
    subparser.set_defaults(cmd=_run_run)

