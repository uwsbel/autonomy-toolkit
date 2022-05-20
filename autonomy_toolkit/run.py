# SPDX-License-Identifier: MIT
"""
CLI command that handles allows generic handling of an ATK config file for running docker containers

Entrypoint for the `run` command

This entrypoint provides easy running of generic docker containers. It's exactly a wrapper of docker compose,
where the ATK config file is used. This allows `atk` to be used.

To use this entrypoint, you simply need to run the following:

```bash
atk run
```

It will search for an ATK config file in all parent directories (defaults for looking for `atk.yml`; this can
be overridden with `--filename`) and then use `docker compose run`. Not many checks are done to ensure the
file is formatted correctly for `docker compose`, so please refer to any errors output from the command for debugging.
"""

# Imports from atk
from autonomy_toolkit.utils.atk_config import ATKConfig
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.files import search_upwards_for_file
from autonomy_toolkit.containers.container_client import ContainerException

# Other imports
import os, argparse

def _run_run(args):
    LOGGER.info("Running 'run' entrypoint...")

    # Instantiate the client
    # Create the abstracted client we'll use for interacting with the compose client
    container_runtime = os.environ.get("ATK_CONTAINER_RUNTIME", "docker")
    if container_runtime == "docker":
        from autonomy_toolkit.containers.docker_client import DockerClient
        client = DockerClient
    else:
        LOGGER.fatal(f"Environment variable 'ATK_CONTAINER_RUNTIME' is set to '{container_runtime}', which is not allowed.")
        return

    # Check that the client libraries are installed properly
    if not client.is_installed():
        return

    # Grab the ATK config file
    LOGGER.debug(f"Loading '{args.filename}' file.")
    config = ATKConfig(args.filename, container_runtime)

    # Add some required attributes
    config.add_required_attribute("services")

    # Add some default custom attributes
    config.add_custom_attribute("services", type=dict, delete=False)

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

    # Generate the compose file
    config.generate_compose(services=args.services)

    # Now actually instantiate the client
    client = client(config, config.project, config.compose_path, **vars(args))

    # Complete the arguments
    try:
        # And write the compose file
        config.write_compose()

        # Run!!
        LOGGER.info(f"Running...")
        client.run("--service-ports", "--rm", args.services[0], *args.args)

    except ContainerException as e:
        LOGGER.fatal(e)
        if e.stderr:
            LOGGER.fatal(e.stderr)
    finally:
        del client

def _init(subparser):
    LOGGER.debug("Initializing 'run' entrypoint...")

    # Add arguments
    subparser.add_argument("-s", "--services", nargs='+', help="The services to use. Defaults to 'all' or whatever 'default_services' is set to in atk.yml. If 'all' is passed, all the services are used.", default=None)
    subparser.add_argument("-f", "--filename", help="The ATK config file. Defaults to 'atk.yml'", default='atk.yml')
    subparser.add_argument("--args", nargs=argparse.REMAINDER, help="Additional arguments to pass to the docker compose command. No logic is done on the args, the docker command will error out if there is a problem.", default=[])
    subparser.set_defaults(cmd=_run_run)

