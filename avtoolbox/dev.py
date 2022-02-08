"""
CLI command that handles working with the AV development environment
"""

# Imports from av
from avtoolbox.utils.logger import LOGGER
from avtoolbox.utils.yaml_parser import YAMLParser
from avtoolbox.utils.files import search_upwards_for_file
from avtoolbox.utils.docker import get_docker_client_binary_path, run_docker_cmd, compose_is_installed, DockerComposeClient, norm_ports, find_available_port

# Other imports
import yaml, os, socket

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

    # Read the avtoolbox yml file
    custom_attrs = ["project", "user", "default_services"]
    project = _check_avtoolbox(avtoolbox_yml, "project")
    if project is None: return
    username = _check_avtoolbox(avtoolbox_yml, "user", "username", default=project)
    is_posix = lambda  : os.name == "posix"
    uid = _check_avtoolbox(avtoolbox_yml, "user", "uid", default=os.getuid() if is_posix() else 1000)
    gid = _check_avtoolbox(avtoolbox_yml, "user", "gid", default=os.getgid() if is_posix() else 1000)
    default_services = _check_avtoolbox(avtoolbox_yml, "default_services", default=["dev"])
    services = _check_avtoolbox(avtoolbox_yml, "services")
    if services is None: return
    dev = _check_avtoolbox(avtoolbox_yml, "services", "dev")
    if dev is None: return
    networks = _check_avtoolbox(avtoolbox_yml, "networks", default={})

    info, err = run_docker_cmd("--debug", "info", stdout=-1, stderr=-1)
    avail_runtimes = info.split("Runtimes: ")[1].split('\n')[0].split(' ')
    runtime_name = info.split("Default Runtime: ")[1].split('\n')[0].split(' ')[0]
    if("nvidia" in avail_runtimes):
        runtime_name = "nvidia"

    # Additional checks
    if any(c.isupper() for c in project):
        LOGGER.fatal(f"'project' is set to '{project}' which is not allowed since it has capital letters. Please choose a name with only lowercase.")
        return

    # Load in the default values
    default_compose_yml = os.path.realpath(os.path.join(__file__, "..", "docker", "default-compose.yml"))
    with open(default_compose_yml, "r") as f:
        default_configs = YAMLParser(text=eval(f"f'''{f.read()}'''")).get_data()

    # Grab the default dockerignore file
    dockerignore = ""
    default_dockerignore = os.path.realpath(os.path.join(__file__, "..", "docker", "dockerignore"))
    with open(default_dockerignore, "r") as f:
        dockerignore = f.read()
    existing_dockerignore = search_upwards_for_file('.dockerignore')
    if existing_dockerignore is not None:
        with open(existing_dockerignore, "r") as f:
            dockerignore += f.read()

    # The docker containers are generated from a docker-compose.yml file
    # We'll write this ourselves from the .avtoolbox file and the defaults
    temp = dict(**avtoolbox_yml.get_data())
    temp = { k: v for k,v in temp.items() if k not in custom_attrs }
    docker_compose = _merge_dictionaries(temp, default_configs)

    # If no command is passed, start up the container and attach to it
    cmds = [args.build, args.up, args.down, args.attach] 
    if all(not c for c in cmds):
        args.up = True
        args.attach = True

    # Get the services we'll use
    if args.services is None: args.services = default_services 
    if 'dev' not in args.services and 'all' not in args.services and args.attach:
        LOGGER.fatal(f"'--services' requires 'dev' (or 'all') when attach is set to true.")
        return
    args.services = args.services if 'all' not in args.services else []

    # Complete the arguments
    if not args.dry_run:

        try:
            # Write the compose file
            with open(root / "docker-compose.yml", "w") as yaml_file:
                yaml.dump(docker_compose, yaml_file)

            # Write the dockerignore
            with open(root / ".dockerignore", "w") as dockerignore_file:
                dockerignore_file.write(dockerignore)

            client = DockerComposeClient(project=project, services=args.services, compose_file=yaml_file.name)

            if args.down:
                LOGGER.info(f"Tearing down...")

                client.run("down")

            if args.build:
                LOGGER.info(f"Building...")

                no_cache = "--no-cache" if args.no_cache else ""
                client.run("build", no_cache)

            if args.up:
                LOGGER.info(f"Spinning up...")

                # For each service that we're spinning up, check some arguments
                # For instance, if two ports match between different containers (common if you 
                # have different projects which is the avtoolbox framework and export the same ports),
                # you will run into issues when they're both running
                config = YAMLParser(text=client.run("config", stdout=-1)[0])
                for service_name, service in config.get_data()['services'].items():
                    # Check ports
                    for ports in service.get('ports', []):
                        port = find_available_port(ports['published'])
                        if port is None:
                            LOGGER.fatal(f"PORT CONFLICT: Could not find an available port within range of '{ports['published']}' to use for the '{service_name}' service.")
                            return
                        elif port != ports['published']:
                            LOGGER.warn(f"PORT CONFLICT: Adjusted port mapping for '{service_name}' service from '{ports['published']}' to '{port}'.")
                            ports['published'] = port 

                # Rewrite with the parsed config
                with open(root / "docker-compose.yml", "w") as yaml_file:
                    yaml.dump(config.get_data(), yaml_file)

                client.run("up", "-d")

            if args.attach:
                LOGGER.info(f"Attaching...")

                # Get the shell we'll use
                dev_name = docker_compose["services"]["dev"]["container_name"]
                env, err = run_docker_cmd("exec", dev_name, "env", stdout=-1, stderr=-1)
                if err:
                    if "Error: No such container: " in err:
                        LOGGER.fatal(f"Please rerun the command with '--up'. The container cannot be attached to since it hasn't been created.")
                        return
                    else:
                        LOGGER.fatal(f"Got error while trying to attach to the container: '{err}'.")
                        return
                shellcmd = env.split("USERSHELLPATH=")[1].split('\n')[0]

                client.run("exec", "dev", exec_cmd=shellcmd)
        finally:
            os.unlink(dockerignore_file.name)
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
    subparser.add_argument("--no-cache", action="store_true", help="Build with no cache. Only used if --build is set to True.", default=False)
    subparser.add_argument("--keep-yml", action="store_true", help="Don't delete the generated docker-compose file.", default=False)
    subparser.add_argument("--services", nargs='+', help="The services to use. Defaults to 'all' or whatever 'default_services' is set to in .avtoolbox.yml. 'dev' or 'all' is required for the 'attach' argument. If 'all' is passed, all the services are used.", default=None)
    subparser.set_defaults(cmd=_run_env)

