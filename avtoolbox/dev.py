"""
CLI command that handles working with the AV development environment
"""

# Imports from av
from avtoolbox.utils.logger import LOGGER
from avtoolbox.utils.yaml_parser import YAMLParser
from avtoolbox.utils.files import search_upwards_for_file
from avtoolbox.utils.docker import get_docker_client_binary_path, run_docker_cmd, compose_is_installed, DockerComposeClient

# Other imports
import yaml, os, argparse, json, subprocess

def _check_avtoolbox(avtoolbox_yml, *args, default=None):
    if not avtoolbox_yml.contains(*args):
        if default is None:
            LOGGER.fatal(f"'{'.'.join(*args)}' must be in '.avtoolbox.yml'. '{'.'.join(*args)}'")
            return None
        else:
            return default
    return avtoolbox_yml.get(*args)

def _merge_dictionaries(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            _merge_dictionaries(value, node)
        else:
            destination[key] = value

    return destination

def _run_env(args):
    """
    Entrypoint for the `dev` command.

    The `dev` command essentially wraps `docker compose` to automatically build, spin-up, attach, and
    tear down the AV development environment. `docker compose` is therefore necessary to install.

    The `dev` command will search for a file called `.avtoolbox.yml`. This is a hidden file, and it defines some custom
    configurations for the development environment. It allows users to quickly start and attach to the AV development environment
    based on a shared docker-compose file and any Dockerfile build configurations. 

    There are four possible options that can be used using the `dev` subcommand:
    `build`, `up`, `down`, and `attach`. For example, if you'd like to build the container, you'd run 
    the following command:

    ```bash
    av dev --build
    ```

    If you'd like to build, start the container, then attach to it, run the following command:

    ```bash
    av dev --build --up --attach
    # OR
    av dev -b -u -a
    # OR
    av dev -bua
    ```

    If no arguments are passed, this is equivalent to the following command:

    ```bash
    av dev --up --attach
    ```

    If desired, pass `--down` to stop the container. Further, if the container exists and changes are
    made to the repository, the container will _not_ be built automatically. To do that, add the 
    `--build` argument.
    """
    LOGGER.info("Running 'dev' entrypoint...")

    # Check docker is installed
    if get_docker_client_binary_path() is None:
        LOGGER.fatal(f"Docker was not found to be installed. Cannot continue.")
        return

    # Check docker compose is installed
    LOGGER.debug("Checking if 'docker compose' (V2) is installed...")
    if not compose_is_installed():
        LOGGER.fatal("The command 'docker compose' is not installed. See http://projects.sbel.org/avtoolbox/tutorials/using_the_development_environment.html for more information.")
        return
    LOGGER.debug("'docker compose' (V2) is installed.")

    # Check that the .avtoolbox.conf file is located in this directory or any parent directories
    # This file should be at the root of any avtoolbox compatible stack
    LOGGER.info("Searching for '.avtoolbox.yml'...")
    conf = search_upwards_for_file('.avtoolbox.yml')
    if conf is None:
        LOGGER.fatal("No .avtoolbox.yml file was found in this directory or any parent directories. Make sure you are running this command in an avtoolbox compatible repository.")
        return
    root = conf.parent
    LOGGER.info(f"Found '.avtoolbox.yml' at {conf}.")

    # Parse the .avtoolbox.yml file
    LOGGER.debug("Parsering '.avtoolbox.yml' file.")
    avtoolbox_yml = YAMLParser(conf)

    # Read the avtoolbox yml fil
    project = _check_avtoolbox(avtoolbox_yml, "project")
    if project is None: return
    username = _check_avtoolbox(avtoolbox_yml, "username", default=os.getlogin())
    default_services = _check_avtoolbox(avtoolbox_yml, "default_services", default=["dev"])
    services = _check_avtoolbox(avtoolbox_yml, "services")
    if services is None: return
    dev = _check_avtoolbox(avtoolbox_yml, "services", "dev")
    if dev is None: return
    networks = _check_avtoolbox(avtoolbox_yml, "networks", default={})

    # Additional checks
    if any(c.isupper() for c in project):
        LOGGER.fatal(f"'project' is set to '{project}' which is not allowed since it has capital letters. Please choose a name with only lowercase.")
        return

    # Get the services we'll use
    if args.services is None: args.services = default_services 
    if 'dev' not in args.services and 'all' not in args.services and args.attach:
        LOGGER.fatal(f"'--services' requires 'dev' (or 'all') when attach is set to true.")
        return
    args.services = args.services if 'all' not in args.services else []

    # Load in the default values
    default_compose_yml = os.path.realpath(os.path.join(__file__, "..", "docker", "default-compose.yml"))
    with open(default_compose_yml, "r") as f:
        default_configs = YAMLParser(text=eval(f"f'''{f.read()}'''")).get_data()

    # The docker containers are generated from a docker-compose.yml file
    # We'll write this ourselves from the .avtoolbox file and the defaults
    temp = dict(**avtoolbox_yml.get_data())
    temp.pop("project", None); temp.pop("username", None); temp.pop("default_services", None)
    docker_compose = _merge_dictionaries(temp, default_configs)

    # If no command is passed, start up the container and attach to it
    cmds = [args.build, args.up, args.down, args.attach] 
    if all(not c for c in cmds):
        args.up = True
        args.attach = True

    # Complete the arguments
    if not args.dry_run:

        try:
            yaml_file = open(root / "docker-compose.yml", "w")
            yaml.dump(docker_compose, yaml_file)

            client = DockerComposeClient(project=project, services=args.services, compose_file=yaml_file.name)

            if args.down:
                LOGGER.info(f"Tearing down...")

                client.run("down")

            if args.build:
                LOGGER.info(f"Building...")

                client.run("build")

            if args.up:
                LOGGER.info(f"Spinning up...")

                client.run("up", "-d")

            if args.attach:
                LOGGER.info(f"Attaching...")

                # Get the shell we'll use
                dev_name = docker_compose["services"]["dev"]["container_name"]
                env = run_docker_cmd("exec", dev_name, "env", stdout=-1)
                shellcmd = env.split("USERSHELLPATH=")[1].split('\n')[0]

                client.run("exec", "dev", exec_cmd=shellcmd)
        finally:
            yaml_file.close()
            if not args.keep_yml:
                os.unlink(yaml_file.name)

def _init(subparser):
    """Initializer method for the `dev` entrypoint

    This entrypoint provides easy access to the AV development environment. The dev environment
    leverages [Docker](https://docker.com) to allow interoperability across operating systems. `docker compose`
    is used to build, spin up, attach, and tear down the containers. The `dev` entrypoint will basically wrap
    the `docker compose` commands to make it easier to customize the workflow to work best for AV.

    The primary container, titled `dev`, has [ROS 2](https://docs.ros.org/en/galactic/index.html)
    pre-installed. The software stack for the AV vehicle utilizes ROS 2 and will use
    the same container that is used for development. 

    Additional containers may be provided to allow for GUI windows or run simulations.
    """
    LOGGER.debug("Initializing 'dev' entrypoint...")

    # Add a base 
    subparser.add_argument("-b", "--build", action="store_true", help="Build the env.", default=False)
    subparser.add_argument("-u", "--up", action="store_true", help="Spin up the env.", default=False)
    subparser.add_argument("-d", "--down", action="store_true", help="Tear down the env.", default=False)
    subparser.add_argument("-a", "--attach", action="store_true", help="Attach to the env.", default=False)
    subparser.add_argument("--keep-yml", action="store_true", help="Don't delete the generated docker-compose file.", default=False)
    subparser.add_argument("--services", nargs='+', help="The services to use. Defaults to 'all' or whatever 'default_services' is set to in .avtoolbox.yml. 'dev' or 'all' is required for the 'attach' argument. If 'all' is passed, all the services are used.", default=None)
    subparser.set_defaults(cmd=_run_env)
