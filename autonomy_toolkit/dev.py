"""
CLI command that handles working with the ATK development environment
"""

# Imports from atk
from autonomy_toolkit.utils import is_posix
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.yaml_parser import YAMLParser
from autonomy_toolkit.utils.files import search_upwards_for_file
from autonomy_toolkit.utils.docker import get_docker_client_binary_path, run_docker_cmd, compose_is_installed, DockerComposeClient, norm_ports, find_available_port, DockerException

# Other imports
import yaml, os, argparse, getpass

# Check that the .autonomy_toolkit.conf file is located in this directory or any parent directories
# This file should be at the root of any autonomy_toolkit compatible stack
def _update_globals():
    AUTONOMY_TOOLKIT_YML_PATH = search_upwards_for_file('.autonomy_toolkit.yml')
    if AUTONOMY_TOOLKIT_YML_PATH is None:
        LOGGER.fatal("No .autonomy_toolkit.yml file was found in this directory or any parent directories. Make sure you are running this command in an autonomy_toolkit compatible repository.")
        exit(-1)
    LOGGER.info(f"Found '.autonomy_toolkit.yml' at {AUTONOMY_TOOLKIT_YML_PATH}.")

    # Globals
    # PATHS
    ROOT = AUTONOMY_TOOLKIT_YML_PATH.parent
    DOCKER_COMPOSE_PATH = ROOT / ".docker-compose.yml"
    DOCKER_IGNORE_PATH = ROOT / ".dockerignore"
    AUTONOMY_TOOLKIT_USER_COUNT_PATH = ROOT / ".autonomy_toolkit.user_count"
    # CUSTOM ATTRIBUTES ALLOWED IN THE AUTONOMY_TOOLKIT_YML FILE
    CUSTOM_ATTRS = ["project", "user", "default_services", "desired_runtime", "overwrite_lists", "custom_cli_arguments"]

    globals().update(locals())

def _check_autonomy_toolkit(autonomy_toolkit_yml, *args, default=None):
    if not autonomy_toolkit_yml.contains(*args):
        if default is None:
            LOGGER.fatal(f"'{'.'.join(*args)}' must be in '.autonomy_toolkit.yml'. '{'.'.join(*args)}'")
            raise AttributeError('')
        else:
            return default
    return autonomy_toolkit_yml.get(*args)

def _merge_dictionaries(source, destination, overwrite_lists=False):
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            _merge_dictionaries(value, node, overwrite_lists)
        elif not overwrite_lists and key in destination and isinstance(destination[key], list):
            if isinstance(value, list):
                destination[key].extend(value)
            else:
                destination[key].append(value)
        else:
            destination[key] = value

    return destination

def _parse_autonomy_toolkit(autonomy_toolkit_yml):
    # Read the autonomy_toolkit yml file
    custom_config = {}
    try:
        # Custom config
        custom_config["root"] = ROOT
        custom_config["project"] = _check_autonomy_toolkit(autonomy_toolkit_yml, "project")
        custom_config["username"] = _check_autonomy_toolkit(autonomy_toolkit_yml, "user", "container_username", default=custom_config["project"])
        custom_config["host_username"] = _check_autonomy_toolkit(autonomy_toolkit_yml, "user", "host_username", default=getpass.getuser())
        custom_config["uid"] = _check_autonomy_toolkit(autonomy_toolkit_yml, "user", "uid", default=os.getuid() if is_posix() else 1000)
        custom_config["gid"] = _check_autonomy_toolkit(autonomy_toolkit_yml, "user", "gid", default=os.getgid() if is_posix() else 1000)
        custom_config["default_services"] = _check_autonomy_toolkit(autonomy_toolkit_yml, "default_services", default=["dev"])
        custom_config["overwrite_lists"] = _check_autonomy_toolkit(autonomy_toolkit_yml, "overwrite_lists", default=False)
        custom_config["custom_cli_arguments"] = _check_autonomy_toolkit(autonomy_toolkit_yml, "custom_cli_arguments", default={})

        custom_config["project"] = eval(f"f'''{custom_config['project']}'''", custom_config)
        custom_config["username"] = eval(f"f'''{custom_config['username']}'''", custom_config)

        # Check these two attributes exist
        # Will exit if they don't
        _check_autonomy_toolkit(autonomy_toolkit_yml, "services")
        _check_autonomy_toolkit(autonomy_toolkit_yml, "services", "dev")
    except AttributeError as e:
        return

    return custom_config

def _read_text(*args):
    filepath = os.path.realpath(os.path.join(*args))
    LOGGER.info(f"Reading from '{filepath}'...")
    with open(filepath, 'r') as f:
        text = f.read()
    LOGGER.info(f"Finished reading from '{filepath}'.")

    return text

def _write_text(filepath, text):
    filepath = str(filepath)
    LOGGER.info(f"Writing to '{filepath}'...")
    with open(filepath, 'w') as file:
        file.write(text)
    LOGGER.info(f"Done writing to '{filepath}'.")

def _update_user_count(filepath, val):
    num = 0
    if os.path.isfile(filepath):
        num = int(_read_text(str(filepath)))
    num += val
    _write_text(filepath, str(num))

    return num

def _unlink_file(filepath):
    if not os.path.isfile(filepath):
        LOGGER.warn(f"'{filepath}' was deleted prematurely. This may be a bug.")
        return 1
    else:
        os.unlink(filepath)
        return 0

def _update_compose(client, custom_config, args, unknown_args):
    # For each service that we're spinning up, check some arguments
    # For instance, if two ports match between different containers (common if you 
    # have different projects which is the autonomy_toolkit framework and export the same ports),
    # you will run into issues when they're both running
    config = YAMLParser(text=client.run("config", stdout=-1)[0])
    for service_name, service in config.get_data()['services'].items():
        # Check ports
        if args.up:
            for ports in service.get('ports', []):
                port = find_available_port(ports['published'])
                if port is None:
                    LOGGER.fatal(f"PORT CONFLICT: Could not find an available port within range of '{ports['published']}' to use for the '{service_name}' service.")
                    return
                elif port != ports['published']:
                    LOGGER.warn(f"PORT CONFLICT: Adjusted port mapping for '{service_name}' service from '{ports['published']}' to '{port}'.")
                    ports['published'] = port 

        # Add custom cli arguments
        # TODO: Disable 'argparse' as a service name
        service_args = {k: v for k,v in custom_config["custom_cli_arguments"].items() if service_name in v}
        if service_args:
            # We'll use argparse to parse the unknown flags
            parser = argparse.ArgumentParser(prog=service_name, add_help=False)
            for arg_name, arg_dict in service_args.items():
                if arg_name[:2] != '--':
                    LOGGER.fatal(f"The argparse argument must begin with '--'. Got '{arg_name}' instead.")
                    return
                parser.add_argument(arg_name, **custom_config["custom_cli_arguments"][arg_name].get("argparse", {}))
            known, unknown = parser.parse_known_args(unknown_args)
            output = yaml.load(eval(f"f'''{yaml.dump(service_args)}'''", vars(known)), Loader=yaml.Loader)
            for k,v in output.items():
                # Only use if the arg is set
                # Assumed it is set if it passes a boolean conversion
                if getattr(known, v.get('argparse', {}).get('dest', k[2:])):
                    service.update(_merge_dictionaries(service, v[service_name]))

            if unknown:
                LOGGER.warn(f"Found unknown arguments in custom arguents for service '{service_name}': '{', '.join(unknown)}'. Ignoring.")

    # Rewrite with the parsed config
    with open(DOCKER_COMPOSE_PATH, "w") as yaml_file:
        yaml.dump(config.get_data(), yaml_file)

def _run_env(args, unknown_args):
    """
    Entrypoint for the `dev` command.

    The `dev` command essentially wraps `docker compose` to automatically build, spin-up, attach, and
    tear down the ATK development environment. `docker compose` is therefore necessary to install.

    The `dev` command will search for a file called `.autonomy_toolkit.yml`. This is a hidden file, and it defines some custom
    configurations for the development environment. It allows users to quickly start and attach to the ATK development environment
    based on a shared docker-compose file and any Dockerfile build configurations. 

    There are four possible options that can be used using the `dev` subcommand:
    `build`, `up`, `down`, and `attach`. For example, if you'd like to build the container, you'd run 
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
    atk dev --up --attach
    ```

    If desired, pass `--down` to stop the container. Further, if the container exists and changes are
    made to the repository, the container will _not_ be built automatically. To do that, add the 
    `--build` argument.
    """
    LOGGER.info("Running 'dev' entrypoint...")
    _update_globals()

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

    # Parse the .autonomy_toolkit.yml file
    LOGGER.debug("Parsing '.autonomy_toolkit.yml' file.")
    autonomy_toolkit_yml = YAMLParser(AUTONOMY_TOOLKIT_YML_PATH)

    # Read the autonomy_toolkit yml file
    custom_config = _parse_autonomy_toolkit(autonomy_toolkit_yml)

    # Additional checks
    if any(c.isupper() for c in custom_config["project"]):
        LOGGER.fatal(f"'project' is set to '{project}' which is not allowed since it has capital letters. Please choose a name with only lowercase.")
        return

    # Load in the default values
    default_configs = YAMLParser(text=_read_text(__file__, "..", "docker", "default-compose.yml")).get_data()

    # Grab the default dockerignore file
    dockerignore = _read_text(__file__, "..", "docker", "dockerignore")
    if (existing_dockerignore := search_upwards_for_file('.dockerignore')) is not None:
        dockerignore += _read_text(existing_dockerignore)

    # The docker containers are generated from a docker-compose.yml file
    # We'll write this ourselves from the .autonomy_toolkit file and the defaults
    temp = dict(**autonomy_toolkit_yml.get_data())
    temp = { k: v for k,v in temp.items() if k not in CUSTOM_ATTRS }
    docker_compose = _merge_dictionaries(temp, default_configs, custom_config["overwrite_lists"])

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
        args.services = custom_config["default_services"]
    args.services = args.services if 'all' not in args.services else []

    # Complete the arguments
    if not args.dry_run:

        try:
            # Write the compose file
            docker_compose_str = eval(f"f'''{yaml.dump(docker_compose)}'''", globals(), custom_config)
            docker_compose = YAMLParser(text=docker_compose_str).get_data()
            _write_text(DOCKER_COMPOSE_PATH, docker_compose_str)

            # Write the dockerignore
            _write_text(DOCKER_IGNORE_PATH, dockerignore)

            # Keep track of the number of users so we aren't deleting files when they need to persist
            _update_user_count(AUTONOMY_TOOLKIT_USER_COUNT_PATH, 1)

            client = DockerComposeClient(project=custom_config["project"], services=args.services, compose_file=DOCKER_COMPOSE_PATH)

            # Make any custom updates at runtime after the compose file has been loaded once
            _update_compose(client, custom_config, args, unknown_args)

            if args.down:
                LOGGER.info(f"Tearing down...")

                client.run("down", *args.args)

            if args.build:
                LOGGER.info(f"Building...")

                client.run("build", *args.args)

            if args.up:
                # First check if the dev container is running.
                # If it is, don't run args.up
                try:
                    stdout, stderr = client.run("ps", "--services", *args.services, "--filter", "status=running", stdout=-1, stderr=-1)
                    LOGGER.warn("The services are already running. If you didn't explicitly call '--up', you can safely ignore this warning.")
                    args.up = False
                except DockerException as e:
                    if "no such service: " not in e.stderr:
                        raise e

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
                container_name = docker_compose["services"][service_name]["container_name"]
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
            if _update_user_count(AUTONOMY_TOOLKIT_USER_COUNT_PATH, -1) == 0 or args.down:
                _unlink_file(AUTONOMY_TOOLKIT_USER_COUNT_PATH)
                _unlink_file(DOCKER_IGNORE_PATH)
                if not args.keep_yml: _unlink_file(DOCKER_COMPOSE_PATH)

def _init(subparser):
    """Initializer method for the `dev` entrypoint

    This entrypoint provides easy access to the ATK development environment. The dev environment
    leverages [Docker](https://docker.com) to allow interoperability across operating systems. `docker compose`
    is used to build, spin up, attach, and tear down the containers. The `dev` entrypoint will basically wrap
    the `docker compose` commands to make it easier to customize the workflow to work best for ATK.

    The primary container, titled `dev`, has [ROS 2](https://docs.ros.org/en/galactic/index.html)
    pre-installed. The software stack for the ATK vehicle utilizes ROS 2 and will use
    the same container that is used for development. 

    Additional containers may be provided to allow for GUI windows or run simulations.
    """
    LOGGER.debug("Initializing 'dev' entrypoint...")

    # Add a base 
    subparser.add_argument("-b", "--build", action="store_true", help="Build the env.", default=False)
    subparser.add_argument("-u", "--up", action="store_true", help="Spin up the env.", default=False)
    subparser.add_argument("-d", "--down", action="store_true", help="Tear down the env.", default=False)
    subparser.add_argument("-a", "--attach", action="store_true", help="Attach to the env.", default=False)
    subparser.add_argument("-r", "--run", action="store_true", help="Run a command in the provided service. Only one service may be provided. No other arguments may be called.", default=False)
    subparser.add_argument("-s", "--services", nargs='+', help="The services to use. Defaults to 'all' or whatever 'default_services' is set to in .autonomy_toolkit.yml. 'dev' or 'all' is required for the 'attach' argument. If 'all' is passed, all the services are used.", default=None)
    subparser.add_argument("--keep-yml", action="store_true", help="Don't delete the generated docker-compose file.", default=False)
    subparser.add_argument("--args", nargs=argparse.REMAINDER, help="Additional arguments to pass to the docker compose command. No logic is done on the args, the docker command will error out if there is a problem.", default=[])
    subparser.set_defaults(cmd=_run_env)

