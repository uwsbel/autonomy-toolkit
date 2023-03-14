# SPDX-License-Identifier: MIT
"""
CLI command that handles working with the ATK development environment

Entrypoint for the `dev` command

This entrypoint provides easy access to the ATK development environment. The dev environment
leverages containers (think [Docker](https://docker.com)) to allow interoperability across operating systems. Similar to
`docker compose`, `atk dev` provides configurability through a YAML file that defines how a container should be spun up.
Further, the configuration is used to build, attach, tear down, and possibly run specific command. The `dev` entrypoint will basically wrap
the `docker compose` (or any other container system) commands to make it easier to customize the workflow to work best for ATK.

The `dev` command will search for a file called `atk.yml`. This is a hidden file, and it defines some custom
configurations for the development environment. It allows users to quickly start and attach to the ATK development environment.

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

# Imports from atk
from autonomy_toolkit.utils.atk_config import ATKConfig
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.parsing import ATKYamlFile, ATKJsonFile
from autonomy_toolkit.utils.files import search_upwards_for_file
from autonomy_toolkit.utils.system import is_port_available, getuser, getuid, getgid

from autonomy_toolkit.containers.container_client import ContainerException

# Other imports
import yaml, os, argparse, getpass

def _parse_ports(client, config, args):
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
    if not args.dry_run:
        compose = client.get_parsed_config(client)
        services = compose.data.get('services', compose.data.get('instances'))
        for service_name, service in services.items():
            # Check ports
            if args.up or args.run:
                ports = service.get("ports", [])
                for i, port in enumerate(ports):
                    if 'published' in port:
                        port['published'] = int(port['published'])
                        if port['published'] in mappings:
                            port['published'] = mappings[port['published']]

                        published = port['published']
                    else:
                        # Assumed to be host:container
                        published,container = port.split(":")
                        published = int(published)
                        if published in mappings:
                            published = mappings[published]
                            ports[i] = f"{published}:{container}"

                    if not is_port_available(published, udp='udp' in port):
                        LOGGER.fatal(f"Host port '{published}' is requested for the '{service_name}' service, but it is already in use. Consider using '--port-mappings'.")
                        return False

        # Rewrite with the parsed config
        config.write_compose(compose.data)

    return True


def _parse_additional_attributes(config, args):
    # For each service that we're spinning up, check for the custom cli arguments
    compose = config.compose
    for service_name, service in compose['services'].items():
        # ------------------------
        # Add custom cli arguments
        # ------------------------

        # TODO: Disable 'argparse' as a service name
        service_args = {k: v for k,v in config.custom_cli_arguments.items() if service_name in v or 'all' in v}
        if service_args:
            # We'll use argparse to parse the unknown flags
            parser = argparse.ArgumentParser(prog=service_name, add_help=False)
            for arg_name, arg_dict in service_args.items():
                parser.add_argument(f"--{arg_name}", **config.custom_cli_arguments[arg_name].get("argparse", {}))

            known, unknown = parser.parse_known_args([f"--{arg}" for arg in args.custom_cli_args])
            output = ATKYamlFile(text=yaml.dump(service_args))
            output.replace_vars(vars(known))
            for k,v in output.data.items():
                # Only use if the arg is set
                # Assumed it is set if it passes a boolean conversion
                if getattr(known, v.get('argparse', {}).get('dest', k)):
                    _service_name = service_name if 'all' not in v else 'all'
                    added_dict = v[_service_name].get(config.container_runtime, v[_service_name])
                    service.update(ATKConfig._merge_dictionaries(added_dict, service))

            if unknown:
                LOGGER.warn(f"Found unknown arguments in custom arguments for service '{service_name}': '{', '.join(unknown)}'. Ignoring.")

        # ---------------------------
        # Add hardware specific attrs
        # ---------------------------

        if config.hardware_specific_attributes:
            from autonomy_toolkit.utils.system import get_mac_address
             
            mac = get_mac_address()
            LOGGER.debug(f"MAC Address: {mac}.")

            user = getuser()

            for attr in config.hardware_specific_attributes:
                if 'mac_address' not in attr and 'user' not in attr:
                    LOGGER.warn(f"'mac_address' and 'user' are not specified in the hardware specific attribute. Cannot parse.")

                do = False
                if 'user' in attr:
                    do = attr['user'] == user
                if 'mac_address' in attr:
                    do = attr['mac_address'] == mac

                if do:
                    _service_name = service_name if 'all' not in attr else 'all'
                    added_dict = attr[_service_name].get(config.container_runtime, attr[_service_name])
                    service.update(ATKConfig._merge_dictionaries(added_dict, service))

def _run_dev(args):
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
    default_containers = os.environ.get("ATK_DEFAULT_CONTAINERS", "dev").split(",")
    config = ATKConfig(args.filename, container_runtime, default_containers[0])

    
    # Add some required attributes
    config.add_required_attribute("services")
    config.add_required_attribute("services", config.default_container)

    # Add some default custom attributes
    config.add_custom_attribute("user", type=dict, default={})
    config.add_custom_attribute("user", "host_username", type=str, default=getuser())
    config.add_custom_attribute("user", "container_username", type=str, default="@{project}")
    config.add_custom_attribute("user", "uid", type=int, default=getuid())
    config.add_custom_attribute("user", "gid", type=int, default=getgid())
    config.add_custom_attribute("default_containers", type=list, default=default_containers, force_default="ATK_DEFAULT_CONTAINERS" in os.environ)
    config.add_custom_attribute("overwrite_lists", type=bool, default=False)
    config.add_custom_attribute("custom_cli_arguments", type=dict, default={})
    config.add_custom_attribute("hardware_specific_attributes", type=list, default=[])
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
        args.services = config.default_containers
    args.services = args.services if 'all' not in args.services else []

    # Generate the compose file
    config.generate_compose(services=args.services, overwrite_lists=config.overwrite_lists)
    _parse_additional_attributes(config, args)

    # Now actually instantiate the client
    client = client(config, config.project, config.compose_path, **vars(args))

    # Complete the arguments
    try:
        # And write the compose file
        config.write_compose()

        if args.down:
            LOGGER.info(f"Tearing down...")
            client.down(*args.args)

        # Make any custom updates at runtime after the compose file has been loaded once
        if not _parse_ports(client, config, args): return

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

def _init(subparser):
    LOGGER.debug("Initializing 'dev' entrypoint...")

    # Add arguments
    subparser.add_argument("-b", "--build", action="store_true", help="Build the env.", default=False)
    subparser.add_argument("-u", "--up", action="store_true", help="Spin up the env.", default=False)
    subparser.add_argument("-d", "--down", action="store_true", help="Tear down the env.", default=False)
    subparser.add_argument("-a", "--attach", action="store_true", help="Attach to the env.", default=False)
    subparser.add_argument("-r", "--run", action="store_true", help="Run a command in the provided service. Only one service may be provided.", default=False)
    subparser.add_argument("-s", "--services", nargs='+', help="The services to use. Defaults to 'all' or whatever 'default_containers' is set to in atk.yml (can be overwritten with ATK_DEFAULT_CONTAINERS environment variable). If 'all' is passed, all the services are used.", default=None)
    subparser.add_argument("-f", "--filename", help="The ATK config file. Defaults to 'atk.yml'", default='atk.yml')
    subparser.add_argument("--port-mappings", nargs='+', help="Mappings to replace conflicting host ports at runtime. Ex: remap exposed port 8080 to be 8081: '--port-mappings 8080:8081 9090:9091'.", default=[])
    subparser.add_argument("--custom-cli-args", nargs="*", help="Custom CLI arguments that are cross referenced with the 'custom_cli_arguments' field in the ATK config file.", default=[])
    subparser.add_argument("--opts", nargs="*", help="Additional options that are passed to the compose command. Use command as it would be used for the compose argument without the '--'. For docker, 'atk dev -b --opts no-cache -s dev' will equate to 'docker compose build --no-cache dev'. Will be passed to _all_ subcommands (i.e. build, up, etc.) if multiple are used.", default=[])
    subparser.add_argument("--args", nargs="*", help="Additional arguments to pass to the compose command. All character following '--args' is passed at the very end of the compose command, i.e. 'atk dev -r -s dev --args ls' will run '... compose run dev ls'. Will be passed to _all_ subcommands (i.e. build, up, etc.) if multiple are used.", default=[])

    subparser.set_defaults(cmd=_run_dev)

