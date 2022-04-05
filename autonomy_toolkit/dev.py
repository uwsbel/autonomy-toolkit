# SPDX-License-Identifier: MIT
"""
CLI command that handles working with the ATK development environment
"""

# Imports from atk
from autonomy_toolkit.utils import getuser, getuid, getgid
from autonomy_toolkit.utils.atk_config import ATKConfig
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.parsing import ATKYamlFile, ATKJsonFile
from autonomy_toolkit.utils.files import search_upwards_for_file
from autonomy_toolkit.utils.system import is_port_available

from autonomy_toolkit.containers.container_client import ContainerException

# Other imports
import yaml, os, argparse, getpass

def _parse_ports(client, config, args, unknown_args):
    # Loop through each port mapping
    mappings = {}
    for mapping in args.port_mappings:
        if mapping.count(':') != 1:
            LOGGER.fatal(f"'{mapping}' is an incorrect format. Must contain one ':'.")
            return False

        old, new = mapping.split(":")

        if any(not x.isdigit() for x in old) or len(old) == 0 or any(not x.isdigit() for x in new) or len(new) == 0:
            LOGGER.fatal(f"'{mapping}' is an incorrect format. Must be mapping of '<int>:<int>'.")
            return False

        old = int(old)
        new = int(new)
        mappings[old] = new

    # For each service that we're spinning up, check the port mappings to ensure the host
    # port is available.
    compose = ATKYamlFile(text=client.run_cmd("config", stdout=-1)[0])
    for service_name, service in compose.data['services'].items():
        # Check ports
        if args.up or args.run:
            for ports in service.get('ports', []):
                if ports['published'] in mappings:
                    ports['published'] = mappings[ports['published']]

                if not is_port_available(ports['published']):
                    LOGGER.fatal(f"Host port '{ports['published']}' is requested for the '{service_name}' service, but it is already in use. Consider using '--port-mappings'.")
                    return False

    # Rewrite with the parsed config
    config.write_compose(compose.data)

    return True


def _parse_custom_cli_arguments(config, args, unknown_args):
    # For each service that we're spinning up, check for the custom cli arguments
    compose = config.compose
    for service_name, service in compose['services'].items():
        # Add custom cli arguments
        # TODO: Disable 'argparse' as a service name
        service_args = {k: v for k,v in config.custom_cli_arguments.items() if service_name in v}
        if service_args:
            # We'll use argparse to parse the unknown flags
            parser = argparse.ArgumentParser(prog=service_name, add_help=False)
            for arg_name, arg_dict in service_args.items():
                if arg_name[:2] != '--':
                    LOGGER.fatal(f"The argparse argument must begin with '--'. Got '{arg_name}' instead.")
                    return
                parser.add_argument(arg_name, **config.custom_cli_arguments[arg_name].get("argparse", {}))
            known, unknown = parser.parse_known_args(unknown_args)
            output = ATKYamlFile(text=yaml.dump(service_args))
            output.replace_vars(vars(known))
            for k,v in output.data.items():
                # Only use if the arg is set
                # Assumed it is set if it passes a boolean conversion
                if getattr(known, v.get('argparse', {}).get('dest', k[2:])):
                    added_dict = v[service_name].get(config.container_runtime, v[service_name])
                    service.update(ATKConfig._merge_dictionaries(service, added_dict))

            if unknown:
                LOGGER.warn(f"Found unknown arguments in custom arguents for service '{service_name}': '{', '.join(unknown)}'. Ignoring.")

def _run_dev(args, unknown_args):
    LOGGER.info("Running 'dev' entrypoint...")

    # Instantiate the client
    # Create the abstracted client we'll use for interacting with the compose client
    container_runtime = os.environ.get("ATK_CONTAINER_RUNTIME", "docker")
    if container_runtime == "docker":
        from autonomy_toolkit.containers.docker_client import DockerClient
        client = DockerClient
    elif container_runtime == "singularity":
        from autonomy_toolkit.containers.singularity_client import SingularityClient 
        client = SingularityClient
    else:
        LOGGER.fatal(f"Environment variable 'ATK_CONTAINER_RUNTIME' is set to '{container_runtime}', which is not allowed.")
        return

    # Check that the client libraries are installed properly
    if not client.is_installed():
        return

    # Grab the ATK config file
    LOGGER.debug(f"Loading '{args.filename}' file.")
    config = ATKConfig(args.filename, container_runtime, os.environ.get("ATK_DEFAULT_CONTAINER", "dev"))
    
    # Add some required attributes
    config.add_required_attribute("services")
    config.add_required_attribute("services", config.default_container)

    # Add some default custom attributes
    config.add_custom_attribute("user", type=dict, default={})
    config.add_custom_attribute("user", "host_username", type=str, default=getuser())
    config.add_custom_attribute("user", "container_username", type=str, default="@{project}")
    config.add_custom_attribute("user", "uid", type=int, default=getuid())
    config.add_custom_attribute("user", "gid", type=int, default=getgid())
    config.add_custom_attribute("default_services", type=list, default=[config.default_container])
    config.add_custom_attribute("overwrite_lists", type=bool, default=False)
    config.add_custom_attribute("custom_cli_arguments", type=dict, default={})
    # config.add_custom_attribute("build_depends", type=dict, default={}) TODO

    # Parse the ATK config file
    if not config.parse():
        return

    # Additional checks
    if any(c.isupper() for c in config.project):
        LOGGER.fatal(f"'project' is set to '{config.project}' which is not allowed since it has capital letters. Please choose a name with only lowercase.")
        return

    # If no command is passed, start up the container and attach to it
    cmds = [args.build, args.up, args.down, args.attach, args.run] 
    if all(not c for c in cmds):
        LOGGER.debug("No commands passed. Setting commands to '--up' and '--attach'.")
        args.up = True
        args.attach = True
    
    if args.run and any([args.build, args.up, args.down, args.attach]):
        LOGGER.fatal("The '--run' command can be the only command.")
        return
    elif args.run and (args.services is None or len(args.services) != 1):
        LOGGER.fatal("The '--run' command requires one service.")
        return

    # Get the services we'll use
    if args.services is None: 
        args.services = config.default_services
    args.services = args.services if 'all' not in args.services else []

    # Generate the compose file
    config.generate_compose(services=args.services, overwrite_lists=config.overwrite_lists)
    _parse_custom_cli_arguments(config, args, unknown_args)

    # Now actually instantiate the client
    client = client(config, config.project, config.compose_path, **vars(args))

    # Complete the arguments
    if not args.dry_run:

        try:
            # And write the compose file
            config.write_compose()

            # Keep track of the number of users so we aren't deleting files when they need to persist
            config.update_user_count(1)

            if args.down:
                LOGGER.info(f"Tearing down...")
                client.down(*args.args)

            # Make any custom updates at runtime after the compose file has been loaded once
            # Only do if docker, singularity uses the host network
            if container_runtime != "singularity" and not _parse_ports(client, config, args, unknown_args): return

            if args.build:
                LOGGER.info(f"Building...")
                client.build(*args.args)

            if args.up:
                LOGGER.info(f"Spinning up...")
                client.up(*args.args)

            if args.attach:
                LOGGER.info(f"Attaching...")

                if len(args.services) > 1 and config.default_container not in args.services:
                    LOGGER.fatal(f"'--services' must have either one service or '{config.default_container}' (or 'all', which will attach to '{config.default_container}') when attach is set to true.")
                    return

                # Determine the service we'd like to attach to
                # If '{config.default_container}' or 'all' is passed, 
                # {config.default_container} will be attached to
                # Otherwise, one service must be selected and that service will be attached to
                service_name = f"{config.default_container}" if f"{config.default_container}" in args.services or len(args.services) == 0 else args.services[0]

                client.shell(service_name, *args.args)

            if args.run:
                LOGGER.info(f"Running...")
                client.run(args.services[0], *args.args)

        except ContainerException as e:
            LOGGER.fatal(e)
            if e.stderr:
                LOGGER.fatal(e.stderr)
        finally:
            del client
            if config.update_user_count(-1) == 0 or args.down:
                config.cleanup(args.keep_yml)

def _init(subparser):
    """Entrypoint for the `dev` command

    This entrypoint provides easy access to the ATK development environment. The dev environment
    leverages [Docker](https://docker.com) to allow interoperability across operating systems. `docker compose`
    is used to build, spin up, attach, and tear down the containers. The `dev` entrypoint will basically wrap
    the `docker compose` commands to make it easier to customize the workflow to work best for ATK.

    The `dev` command will search for a file called `.atk.yml`. This is a hidden file, and it defines some custom
    configurations for the development environment. It allows users to quickly start and attach to the ATK development environment
    based on a shared `docker-compose.yml` file and any Dockerfile build configurations. 

    There are five possible options that can be used using the `dev` subcommand:
    `build`, `up`, `down`, `attach`, and `run`. For example, if you'd like to build the container, you'd run 
    the following command:

    ```bash
    atk dev --build
    ```

    If you'd like to build, start the container, then attach to it, run the following command:

    ```bash
    atk dev --build --up --attach
    # OR
    atk dev -b -u -a
    # OR
    atk dev -bua
    ```

    If no arguments are passed, this is equivalent to the following command:

    ```bash
    atk dev
    # === is equivalent to ===
    atk dev --up --attach
    ```

    If desired, pass `--down` to stop the container. Further, if the container exists and changes are
    made to the repository, the container will _not_ be built automatically. To do that, add the 
    `--build` argument.
    """
    LOGGER.debug("Initializing 'dev' entrypoint...")

    # Add arguments
    subparser.add_argument("-b", "--build", action="store_true", help="Build the env.", default=False)
    subparser.add_argument("-u", "--up", action="store_true", help="Spin up the env.", default=False)
    subparser.add_argument("-d", "--down", action="store_true", help="Tear down the env.", default=False)
    subparser.add_argument("-a", "--attach", action="store_true", help="Attach to the env.", default=False)
    subparser.add_argument("-r", "--run", action="store_true", help="Run a command in the provided service. Only one service may be provided.", default=False)
    subparser.add_argument("-s", "--services", nargs='+', help="The services to use. Defaults to 'all' or whatever 'default_services' is set to in .atk.yml. 'dev' or 'all' is required for the 'attach' argument. If 'all' is passed, all the services are used.", default=None)
    subparser.add_argument("-f", "--filename", help="The ATK config file. Defaults to '.atk.yml'", default='.atk.yml')
    subparser.add_argument("--keep-yml", action="store_true", help="Don't delete the generated docker-compose file.", default=False)
    subparser.add_argument("--port-mappings", nargs='+', help="Mappings to replace conflicting host ports at runtime.", default=[])
    subparser.add_argument("--args", nargs=argparse.REMAINDER, help="Additional arguments to pass to the docker compose command. No logic is done on the args, the docker command will error out if there is a problem.", default=[])
    subparser.set_defaults(cmd=_run_dev)

