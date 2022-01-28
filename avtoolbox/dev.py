"""
CLI command that handles working with the AV development environment
"""

# Imports from av
from avtoolbox.utils.logger import LOGGER
from avtoolbox.utils.files import search_upwards_for_file

# Docker imports
from python_on_whales import docker, DockerClient, exceptions as docker_exceptions

def _run_env(args):
    """
    Entrypoint for the `dev env` command.

    The `env` command essentially wraps `docker-compose` to automatically build, spin-up, attach, and
    tear down the AV development environment.

    The command is completely redundant; it simply combines all the building, starting, attaching, and destroying
    into a single command. It allows users to quickly start and attach to the AV development environment based
    on the docker-compose file.

    There are four possible options that can be used using the `env` subcommand:
    `build`, `up`, `down`, and `attach`. For example, if you'd like to build the container, you'd run 
    the following command:

    ```bash
    av dev env --build
    ```

    If you'd like to build, start the container, then attach to it, run the following command:

    ```bash
    av dev env --build --up --attach
    # OR
    av dev env -b -u -a
    # OR
    av dev env -bua
    ```

    If no arguments are passed, this is equivalent to the following command:

    ```bash
    av dev env --up --attach
    ```

    If desired, pass `--down` to stop the container. Further, if the container exists and changes are
    made to the repository, the container will _not_ be built automatically. To do that, add the 
    `--build` argument.

    ```{note}
    `av dev` is an alias for `av dev env`. `env` can therefore be omitted for brevity.
    </div></div>
    ```
    """
    LOGGER.info("Running 'dev env' entrypoint...")

    # Check docker-compose is installed
    if not docker.compose.is_installed():
        LOGGER.fatal("The command 'docker compose' is not installed. See http://projects.sbel.org/avtoolbox/tutorials/using_the_development_environment.html for more information.")
        return

    # If no command is passed, start up the container and attach to it
    cmds = [args.build, args.up, args.down, args.attach] 
    if all(not c for c in cmds):
        args.up = True
        args.attach = True

    # Search for a file called docker-compose.yml in any of the parent directories. This file
    # is what holds the default configuration for the docker compose package. We'll read this file,
    # update any of the config (if necessary), then generate a temporary file which will be passed to
    # the docker compose command
    compose_file = search_upwards_for_file('docker-compose.yml')
    if compose_file is None:
        LOGGER.fatal("No docker-compose.yml configuration was found in this directory or any parent directories. Make sure you are running this command in the AV repository.")
        return

    if any([a not in docker.compose.config().services.keys() for a in ['dev', 'vnc']]):
        LOGGER.fatal("The docker-compose.yml configuration does not contain the services 'dev' and/or 'vnc'. Make sure you are running this command in the AV repository.")
        return

    # Complete the arguments
    if not args.dry_run:
        import socket, os, tempfile, yaml

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

            # Read the docker compose file and grab it's config
            config = docker.compose.config(return_json=True)

            # Get main dev name
            if not any('dev' in service for service in config['services']):
                LOGGER.fatal(f"The docker-compose.yml configuration file doesn't contain a service that has 'dev' in it. Make sure you're running in this the correct place.")
                return

            for service_name, service in config['services'].items():
                if 'dev' in service_name:
                    dev_name = service['container_name']
                    break

            if args.up:
                # Ignore all running services
                config['services'] = {name : service for name, service in config['services'].items() if len(docker.container.list(filters={"name": service["container_name"]})) == 0 }

                # If all the services are already running, don't try to spin up
                if len(config['services']) == 0:
                    LOGGER.warn(f"No services need to be initialized. Turning off 'up'. If you didn't explicitly call 'up', this may be safely ignored.")
                    args.up = False

                for service_name, service in config['services'].items():

                    # For each port in each service, make sure they map to available ports
                    # If not, increment the published port by one. Only do this 5 times. If a port can't be found,
                    # stop trying.
                    LOGGER.debug("Checking if any host ports are already in use for service '{service_name}'.")

                    if not 'ports' in service:
                        LOGGER.debug(f"'{service_name}' has no ports mapped. Continuing to next service...")
                        continue

                    for port in service['ports']:
                        for i in range(5):
                            if _is_port_in_use(port['published']):
                                LOGGER.warn(f"Tried to map container port '{port['target']}' to host port '{port['published']}' for service '{service_name}', but it is in use. Trying again with '{port['published'] + 1}'.")
                                port['published'] += 1
                            break

            # Write the config to the temporary yaml file
            with open(tmp.name, 'w') as yaml_file:
                yaml.dump(config, yaml_file)

            # Now set the compose file to the temporary file
            client = DockerClient(compose_files=[tmp.name])

            if args.down:
                LOGGER.info(f"Tearing down...")
                client.compose.down()
            if args.build:
                LOGGER.info(f"Building...")
                client.compose.build()
            if args.up:
                LOGGER.info(f"Spinning up...")
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
            LOGGER.error(f"Docker command raised exception: {msg}")
        finally:
            tmp.close()
            os.unlink(tmp.name)

def _init(subparser):
    """Initializer method for the `dev` entrypoint

    This entrypoint provides easy access to the AV development environment. The dev environment
    leverages [Docker](https://docker.com) to allow interoperability across operating systems. `docker-compose`
    is used to build, spin up, attach, and tear down the containers. The `dev` entrypoint will basically wrap
    the `docker-compose` commands to make it easier to customize the workflow to work best for AV.

    The primary container, titled `dev` in the `docker-compose.yml` file in the 
    [`av` github](https://github.com/uwsbel/avtoolbox), has [ROS 2](https://docs.ros.org/en/galactic/index.html)
    pre-installed. The software stack for the AV vehicle utilizes ROS 2 and will use
    the same container that is used for development. 

    Additional containers may be provided to allow for GUI windows or run simulations.
    """
    LOGGER.debug("Initializing 'dev' entrypoint...")

    def _add_dev_commands(parser):
        parser.add_argument("-b", "--build", action="store_true", help="Build the env.", default=False)
        parser.add_argument("-u", "--up", action="store_true", help="Spin up the env.", default=False)
        parser.add_argument("-d", "--down", action="store_true", help="Tear down the env.", default=False)
        parser.add_argument("-a", "--attach", action="store_true", help="Attach to the env.", default=False)
        parser.set_defaults(cmd=_run_env)

    # Add a base 
    _add_dev_commands(subparser)

    # Create some entrypoints for additinal commands
    subparsers = subparser.add_subparsers(required=False)

    # Subcommand that can build, spin up, attach and tear down the dev environment
    env = subparsers.add_parser("env", description="Command to simplify usage of the docker-based development workflow. Basically wraps docker-compose.")
    _add_dev_commands(env)

