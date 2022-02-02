"""
CLI command that handles working with the AV development environment
"""

# Imports from av
from avtoolbox.utils.logger import LOGGER
from avtoolbox.utils.yaml_parser import YAMLParser
from avtoolbox.utils.files import search_upwards_for_file, read_text

# Other imports
from python_on_whales import docker, DockerClient, exceptions as docker_exceptions, get_docker_client_binary_path
import yaml
import pkgutil
import os
import tempfile
import socket
import pathlib

def _run_env(args):
    """
    Entrypoint for the `dev` command.

    The `dev` command essentially wraps `docker compose` to automatically build, spin-up, attach, and
    tear down the AV development environment. `docker compose` is therefore necessary to install.

    The `dev` command will search for a file called `.avtoolbox.yml`. This is a hidden file, and it defines some custom
    configurations for the development environment. It allows users to quickly start and attach to the AV development environment
    based on a shared docker-compose file and any Dockerfile build configurations. 

    There are four possible options that can be used using the `idev` subcommand:
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
    if not docker.compose.is_installed():
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

    # Read the conf file 
    # The conf file _can_ contain the following information (none required):
    # 
    # project: <str> (required)
    #   This is the name of the project that the docker containers will be named after
    #   The main development environment will be called {project}-dev and so on.
	#
    # user: <dict> (optional)
    #   name: <str> (optional)
    #       The user to create in the container. If not set, will grab the current user.
    #
    #   uid: <int> (optional)
    #       The user id to use. If not set, will grab it from the current user. (NOT USED)
    #
    #   gid: <int> (optional)
    #       The group id to use. If not set, will grab it from the current user. (NOT USED)
    #
    # dev: <dict> (optional)
    #   scripts: <path> (optional)
    #     This is the directory that holds any docker specific files (like custom dockerfiles or
    #     packages/scripts/dependencies that needed to be used when building the docker image).
    #     The path is relative to the .avtoolbox.yml file.
    #
    #   apt-dependences: <list> (optional)
    #       A list of requirements that should be installed in the image through apt.
    #
    #   pip-requirements: <list> (optional)
    #       A list of requirements that should be installed in the image through pip.
    #
    #   ports: <list> (optional)
    #       A list of ports to be exposed.
    #
    #   ros: <dict> (optional)
    #     workspace: <path> (optional)
    #       This is the directory which holds the ROS 2 workspace code
    #       The path is relative to the .avtoolbox.yml file.
    #
    #     distro: <str> (optional)
    #         The ros 2 distro to use. Must be compatible with osrf/ros distrobutions
    #         on DockerHub. Defaults to galactic.
    #
    # vnc: <dict> (optional)
    #   novnc_port: <int> (optional)
    #       The port that novnc is displayed on. Defaults to 8080.
    #
    #   vnc_port: <int> (optional)
    #       The port that vnc is displayed on. Defaults to 5900.
    #
    #   password: <str> (optional)
    #       The password to use for vnc. Defaults to the project name.

    LOGGER.debug("Parsering '.avtoolbox.yml' file.")
    conf_parser = YAMLParser(conf)

    def get_attr(*args, default=None):
        if not conf_parser.contains(*args):
            LOGGER.debug(f"'{'.'.join(args)}' wasn't found in the .avtoolbox.yml file. Assuming '{'.'.join(args)}' to be '{default}'")
            ret = default
        else:
            ret = conf_parser.get(*args)
        return ret

    def read_data(*args):
        path = os.path.realpath(os.path.join(__file__, "..", *args))
        return read_text(path), path

    # project
    project = get_attr("project")
    if project is None:
        LOGGER.fatal(f"'project' must be provided in '.avtoolbox.yml'. Wasn't found, cannot continue.")
        return
    elif any(c.isupper() for c in project):
        LOGGER.fatal(f"'project' is set to '{project}' which is not allowed since it has capital letters. Please choose a name with only lowercase.")
        return

    # user
    username = get_attr("user", "name", default=os.getlogin())
    uid = get_attr("user", "uid", default=os.getuid())
    gid = get_attr("user", "gid", default=os.getgid())

    # dev
    dev_dockerfile, dev_dockerfile_path = read_data("docker", "dev", "dev.dockerfile")
    apt_dependencies = ' '.join(get_attr("dev", "apt-dependencies", default=""))
    pip_requirements = ' '.join(get_attr("dev", "pip-requirements", default=""))
    ports = get_attr("dev", "ports", default=[])
    expose = get_attr("dev", "expose", default=[])

    scripts = get_attr("dev", "scripts", default=os.path.join("docker", "dev", "scripts"))
    if not os.path.isdir(root / scripts):
        LOGGER.fatal(f"dev.scripts must be a directory, got '{scripts}'")
        return

    # dev.ros
    workspace = get_attr("ros", "workspace", default="workspace")
    distro = get_attr("ros", "distro", default="galactic")
    
    # vnc
    novnc_port = get_attr("vnc", "novnc_port", default="8080")
    vnc_port = get_attr("vnc", "vnc_port", default="5900")
    vnc_password = get_attr("vnc", "password", default=project)
    vnc_dockerfile, vnc_dockerfile_path = read_data("docker", "vnc", "vnc.dockerfile")

    # The docker containers are generated from a docker-compose.yml file
    # Grab the shipped configuration files that come with the toolbox package
    docker_compose, docker_compose_path = read_data("docker", "docker-compose.yml")
    docker_compose_fmt = {
        "PROJECT": project,
        "ROOT": root,
        "DEV.DOCKERFILE": dev_dockerfile_path,
        "VNC.DOCKERFILE": vnc_dockerfile_path,
        "USERNAME": username,
        "USER": f"{uid}:{gid}",
        "SCRIPTS": scripts,
        "APT-DEPENDENCIES": apt_dependencies,
        "PIP-REQUIREMENTS": pip_requirements,
        "NOVNC_PORT": novnc_port,
        "VNC_PORT": vnc_port,
        "VNC_PASSWORD": vnc_password,
        "WORKSPACE": workspace,
        "ROSDISTRO": distro,
    }

    for k,v in docker_compose_fmt.items():
        k = f"${{{k}}}"
        v = str(v)
        docker_compose = docker_compose.replace(k, v)
    docker_compose_yml = yaml.load(docker_compose, Loader=yaml.SafeLoader)

    # If no command is passed, start up the container and attach to it
    cmds = [args.build, args.up, args.down, args.attach] 
    if all(not c for c in cmds):
        args.up = True
        args.attach = True

    # Complete the arguments
    if not args.dry_run:
        def _is_port_in_use(port: int) -> bool:
            """Helper function to check if a port is currently in use."""
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) == 0

        
        # We need to provide the ability to dynamically change the docker-compose file without it being in
        # version control. Meaning, for instance, if someone has an existing program using port 5900, we can
        # overwrite this value and give a new one. To accomplish this, we'll create a temporary file,
        # make any necessary edits to the yaml which is now in the temp file, run the commands we need,
        # then delete the temp file

        # Do this in a try/except so that the temp file will always be deleted
        try:

            # Create the temporary file and don't let it delete automatically yet
            tmp = tempfile.NamedTemporaryFile(delete=False)

            # Write the config to the temporary yaml file (first time)
            with open(tmp.name, 'w') as yaml_file:
                yaml.dump(docker_compose_yml, yaml_file)

            # Set the compose file to the temporary file
            client = DockerClient(compose_files=[tmp.name])
            config = client.compose.config(return_json=True)

            # Get main dev name
            if not any('dev' in service for service in config['services']):
                LOGGER.fatal(f"The docker-compose.yml configuration file doesn't contain a service that has 'dev' in it. Make sure you're running in this the correct place.")
                return

            for service_name, service in config['services'].items():
                if 'dev' in service_name:
                    dev_name = service['container_name']
                    break

            if args.down:
                LOGGER.info(f"Tearing down...")
                client.compose.down()

            if args.build:
                LOGGER.info(f"Building...")
                client.compose.build()

            # Ignore all running services
            services = {name : service for name, service in config['services'].items() if len(docker.container.list(filters={"name": service["container_name"]})) == 0 }

            # If all the services are already running, don't try to spin up
            if len(services) == 0:
                LOGGER.warn(f"No services need to be initialized. Turning off 'up'. If you didn't explicitly call 'up', this may be safely ignored.")
                args.up = False

            if args.up:
                LOGGER.info(f"Spinning up...")

                config['services'] = services
                for service_name, service in config['services'].items():

                    # For each port in each service, make sure they map to available ports
                    # If not, increment the published port by one. Only do this 5 times. If a port can't be found,
                    # stop trying.
                    LOGGER.debug("Checking if any host ports are already in use for service '{service_name}'.")

                    # Add any custom ports
                    if 'dev' in service_name:
                        if 'ports' in service:
                            service['ports'].extend(ports)
                        else:
                            service['ports'] = ports

                        if 'expose' in service:
                            service['expose'].extend(expose)
                        else:
                            service['expose'] = expose

                    if not 'ports' in service:
                        LOGGER.debug(f"'{service_name}' has no ports mapped. Continuing to next service...")
                        continue

                    for port in service['ports']:
                        for i in range(5):
                            published = port['published'] if isinstance(port, dict) else int(port.split(":")[0])
                            target = port['target'] if isinstance(port, dict) else port.split(":")[1]
                            if _is_port_in_use(published):
                                LOGGER.warn(f"Tried to map container port '{target}' to host port '{published}' for service '{service_name}', but it is in use. Trying again with '{published + 1}'.")
                                if isinstance(port, str):
                                    port = f"{published + 1}:{target}"
                                else:
                                    port['published'] += 1
                            else:
                                break

                # Write the config again to solidify any changes
                with open(tmp.name, 'w') as yaml_file:
                    yaml.dump(config, yaml_file)

                client.compose.up(detach=True)

            if args.attach:
                LOGGER.info(f"Attaching...")
                try:
                    usershell = [e for e in client.container.inspect(dev_name).config.env if "USERSHELL" in e][0]
                    shellcmd = usershell.split("=")[-1]
                    shellcmd = [shellcmd, "-c", f"{shellcmd}"]
                    print(client.execute(dev_name, shellcmd, interactive=True, tty=True))
                except docker_exceptions.NoSuchContainer as e:
                    LOGGER.fatal(f"The containers have not been started. Please run again with the 'up' command.")
        except docker_exceptions.DockerException as e:
            msg = str(e)
            if 'Error response from daemon:' in msg:
                msg = msg.split('Error response from daemon:')[1][:-3]
            elif "The content of stdout can be found above the stacktrace (it wasn't captured)" in msg:
                LOGGER.warn(f"Got error in Docker container. You can probably ignore this message.")
            else:
                LOGGER.error(f"Docker command raised exception: {msg}")
        finally:
            tmp.close()
            os.unlink(tmp.name)


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
    subparser.set_defaults(cmd=_run_env)

