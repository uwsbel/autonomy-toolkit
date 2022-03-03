"""
CLI command that handles working with the ATK development environment
"""

# Imports from atk
from autonomy_toolkit.utils import getuser, getuid, getgid
from autonomy_toolkit.utils.atk_config import ATKConfig
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.yaml_parser import YAMLParser
from autonomy_toolkit.utils.files import search_upwards_for_file
from autonomy_toolkit.utils.docker import get_docker_client_binary_path, run_docker_cmd, compose_is_installed, DockerComposeClient, is_port_available, DockerException

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

        if any(not x.isdigit() for x in old) or len(old) > 0 or any(not x.isdigit() for x in new) or len(new) == 0:
            LOGGER.fatal(f"'{mapping}' is an incorrect format. Must be mapping of '<int>:<int>'.")
            return False

        old = int(old)
        new = int(new)
        mappings[old] = new

    # For each service that we're spinning up, check the port mappings to ensure the host
    # port is available.
    compose = YAMLParser(text=client.run("config", stdout=-1)[0])
    for service_name, service in compose.get_data()['services'].items():
        # Check ports
        if args.up or args.run:
            for ports in service.get('ports', []):
                if ports['published'] in mappings:
                    ports['published'] = mappings[ports['published']]

                if not is_port_available(ports['published']):
                    LOGGER.fatal(f"Host port '{ports['published']}' is requested for the '{service_name}' service, but it is already in use. Consider using '--port-mappings'.")
                    return False

    return True


def _parse_custom_cli_arguments(client, config, args, unknown_args):
    # For each service that we're spinning up, check for the custom cli arguments
    compose = YAMLParser(text=client.run("config", stdout=-1)[0])
    for service_name, service in compose.get_data()['services'].items():
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
            output = yaml.load(eval(f"f'''{yaml.dump(service_args)}'''", vars(known)), Loader=yaml.Loader)
            for k,v in output.items():
                # Only use if the arg is set
                # Assumed it is set if it passes a boolean conversion
                if getattr(known, v.get('argparse', {}).get('dest', k[2:])):
                    service.update(ATKConfig._merge_dictionaries(service, v[service_name]))

            if unknown:
                LOGGER.warn(f"Found unknown arguments in custom arguents for service '{service_name}': '{', '.join(unknown)}'. Ignoring.")

    # Rewrite with the parsed config
    config.overwrite_compose(compose.get_data())

def _run_env(args, unknown_args):
    LOGGER.info("Running 'dev' entrypoint...")

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
    config.add_required_attribute("services", "dev")

    # Add some default custom attributes
    config.add_custom_attribute("project", str)
    config.add_custom_attribute("project_root", str, default=str(config.root))
    config.add_custom_attribute("atk_root", str, default=str(config.atk_root))
    config.add_custom_attribute("user", dict, default={})
    config.add_custom_attribute("user", "host_username", str, default=getuser())
    config.add_custom_attribute("user", "container_username", str, default="{project}")
    config.add_custom_attribute("user", "uid", int, default=getuid())
    config.add_custom_attribute("user", "gid", int, default=getgid())
    config.add_custom_attribute("default_services", list, default=['dev'])
    config.add_custom_attribute("overwrite_lists", bool, default=False)
    config.add_custom_attribute("custom_cli_arguments", dict, default={})
    # config.add_custom_attribute("build_depends", dict, default={}) TODO

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
    elif args.run and len(args.services) != 1:
        LOGGER.fatal("The '--run' command requires only one service.")
        return

    # Get the services we'll use
    if args.services is None: 
        args.services = config.default_services
    args.services = args.services if 'all' not in args.services else []

    # Complete the arguments
    if not args.dry_run:

        try:
            # Write the compose file
            config.generate_compose(config.overwrite_lists)

            # Write the dockerignore
            config.generate_ignore()

            # Keep track of the number of users so we aren't deleting files when they need to persist
            config.update_user_count(1)

            # Create the abstracted client we'll use for interacting with docker compose
            client = DockerComposeClient(project=config.project, services=args.services, compose_file=config.docker_compose_path)

            # First check if the dev container is running.
            # If it is, don't run args.up
            if args.up and not args.down:
                try:
                    stdout, stderr = client.run("ps", "--services", *args.services, "--filter", "status=running", stdout=-1, stderr=-1)
                    LOGGER.warn("The services are already running. If you didn't explicitly call '--up', you can safely ignore this warning.")
                    args.up = False
                except DockerException as e:
                    if "no such service: " not in e.stderr:
                        raise e

            # Make any custom updates at runtime after the compose file has been loaded once
            if not _parse_ports(client, config, args, unknown_args): return
            return
            _parse_custom_cli_arguments(client, config, args, unknown_args)

            if args.down:
                LOGGER.info(f"Tearing down...")

                client.run("down", *args.args)

            if args.build:
                LOGGER.info(f"Building...")

                client.run("build", *args.args)

            if args.up:
                LOGGER.info(f"Spinning up...")

                client.run("up", "-d", *args.args)

            if args.attach:
                LOGGER.info(f"Attaching...")

                if len(args.services) > 1 and 'dev' not in args.services:
                    LOGGER.fatal(f"'--services' must have either one service or 'dev' (or 'all', which will attach to 'dev') when attach is set to true.")
                    return

                # Determine the service we'd like to attach to
                # If 'dev' or 'all' is passed, dev will be attached to
                # Otherwise, one service must be selected and that service will be attached to
                service_name = 'dev' if 'dev' in args.services or len(args.services) == 0 else args.services[0]

                # Get the shell we'll use
                container_name = config.compose["services"][service_name]["container_name"]
                try:
                    env, err = run_docker_cmd("exec", container_name, "env", stdout=-1, stderr=-1)
                except DockerException as e:
                    if "Error: No such container: " in e.stderr:
                        LOGGER.fatal(f"Please rerun the command with '--up'. The container cannot be attached to since it hasn't been created.")
                        return
                    raise e
                if "USERSHELLPATH" not in env:
                    LOGGER.fatal(f"To attach to a container using autonomy_toolkit, the environment variable \"USERSHELLPATH\" must be defined within the container. Was not found, please add it to the container.")
                    return
                shellcmd = env.split("USERSHELLPATH=")[1].split('\n')[0]

                try:
                    client.run("exec", service_name, exec_cmd=shellcmd, *args.args)
                except DockerException as e:
                    LOGGER.debug(e)

            if args.run:
                LOGGER.info(f"Running...")

                client.run("run", args.services[0], *args.args)

        except DockerException as e:
            LOGGER.fatal(e)
            if e.stderr:
                LOGGER.fatal(e.stderr)
        finally:
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

    # Add a base 
    subparser.add_argument("-b", "--build", action="store_true", help="Build the env.", default=False)
    subparser.add_argument("-u", "--up", action="store_true", help="Spin up the env.", default=False)
    subparser.add_argument("-d", "--down", action="store_true", help="Tear down the env.", default=False)
    subparser.add_argument("-a", "--attach", action="store_true", help="Attach to the env.", default=False)
    subparser.add_argument("-r", "--run", action="store_true", help="Run a command in the provided service. Only one service may be provided. No other arguments may be called.", default=False)
    subparser.add_argument("-s", "--services", nargs='+', help="The services to use. Defaults to 'all' or whatever 'default_services' is set to in .atk.yml. 'dev' or 'all' is required for the 'attach' argument. If 'all' is passed, all the services are used.", default=None)
    subparser.add_argument("-f", "--filename", help="The ATK config file. Defaults to '.atk.yml'", default='.atk.yml')
    subparser.add_argument("--keep-yml", action="store_true", help="Don't delete the generated docker-compose file.", default=False)
    subparser.add_argument("--port-mappings", nargs='+', help="Mappings to replace conflicting host ports at runtime.", default=[])
    subparser.add_argument("--args", nargs=argparse.REMAINDER, help="Additional arguments to pass to the docker compose command. No logic is done on the args, the docker command will error out if there is a problem.", default=[])
    subparser.set_defaults(cmd=_run_env)

