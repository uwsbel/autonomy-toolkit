# Imports from atk
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.atk_config import ATKConfig
from autonomy_toolkit.containers.docker_client import DockerClient

# External imports
import inspect
from functools import partial


def _run_cmd(client, cmd, num_required_services=-1):
    if num_required_services >= 0 and num_required_services != len(client.services):
        LOGGER.fatal(
            f"The command '{cmd}' requires {num_required_services} service(s). You provided {len(client.services)}."
        )
        return False

    LOGGER.info(f"Running '{cmd}'...")
    try:
        method = getattr(client, cmd)
        if not inspect.ismethod(method):
            raise AttributeError
    except AttributeError:
        method = partial(client.run_cmd, cmd)

    if returncode := method():
        LOGGER.fatal(f"Failed to run '{cmd}' with returncode {returncode}.")
        return False

    LOGGER.info(f"Finished running '{cmd}'.")
    return True


def _run_dev(args):
    LOGGER.info("Running 'dev' entrypoint...")

    # Find the atk.yml file
    try:
        config = ATKConfig(args.filename_override, args.services)
    except Exception as e:
        LOGGER.fatal(e)
        return False

    # Create the docker client
    args.compose_opts.extend(args._unknown_args)
    client = DockerClient(
        config,
        dry_run=args.dry_run,
        opts=args.compose_opts,
        args=args.compose_args,
    )

    # Load the config with the docker client before updating the services
    if not config.load(client, args.compose_opts):
        return False

    # Update the config with optionals
    if not config.update_services_with_optionals(args.optionals):
        return False

    # Write the new configuration file
    if not config.write():
        return False

    # Run the commands
    # Will do in this order: down, build, up, attach
    if args.down and not _run_cmd(client, "down"):
        return False

    if args.build and not _run_cmd(client, "build"):
        return False

    if args.up and not _run_cmd(client, "up"):
        return False

    if args.attach and not _run_cmd(client, "attach", 1):
        return False

    if args.command and not _run_cmd(client, args.command, 1):
        return False

    LOGGER.info("Finished running 'dev' entrypoint.")


def _init(subparser):
    LOGGER.debug("Initializing 'dev' entrypoint...")

    subparser.add_argument(
        "-s",
        "--services",
        nargs="+",
        help="The services to use. Can be passed as `-s service1 service2` or `-s service1 -s service2`. This is a required argument to promote explicitness.",
        action="extend",
        default=[],
        required=True,
    )

    subparser.add_argument(
        "-b", "--build", action="store_true", help="Build the image(s).", default=False
    )
    subparser.add_argument(
        "-u",
        "--up",
        action="store_true",
        help="Spin up the container(s).",
        default=False,
    )
    subparser.add_argument(
        "-d",
        "--down",
        action="store_true",
        help="Tear down the container(s).",
        default=False,
    )
    subparser.add_argument(
        "-a",
        "--attach",
        action="store_true",
        help="Attach to the container. Only one service may be provided.",
        default=False,
    )
    subparser.add_argument(
        "-c",
        "--cmd",
        dest="command",
        type=str,
        help="A tool to circumvent the atk interface and directly run a docker compose command. Example: `atk dev -c config -s dev` is equivalent to `docker compose -f <path-in-parent>/atk.yml config dev`.",
        default=None,
    )
    subparser.add_argument(
        "--filename-override",
        help="Override the default ATK config filename. Will search upwards for file. Defaults to 'atk.yml'",
        default="atk.yml",
    )
    subparser.add_argument(
        "-o",
        "--optionals",
        nargs="+",
        help="Custom CLI arguments that are cross referenced with the 'x-optionals' field in the ATK config file.",
        default=[],
    )
    subparser.add_argument(
        "--compose-arg",
        dest="compose_args",
        nargs=1,
        help="Additional arguments that are passed to the compose command. If the arg has a `--`, you must use an `=`. Example: `atk dev -s dev -r --compose-arg=ls` will evaluate to `docker compose run dev ls`. You may use `--compose-arg` multiple times to append multiple options. Will be passed to _all_ selected subcommands (i.e. build, up, etc.).",
        action="extend",
        default=[],
    )
    subparser.add_argument(
        "--compose-opt",
        dest="compose_opts",
        nargs=1,
        help="NOTE: unknown flags passed to `atk dev` are directly passed to `docker compose` as options, this is merely an explicit alias for that functionality. Additional options that are passed to the compose command. If the arg has a `--`, you must use an `=`. Example: `atk dev -s dev -b --compose-opt=--no-cache` will evaluate to `docker compose build --no-cache dev`. You may use `--compose-opt` multiple times to append multiple options. Will be passed to _all_ selected subcommands (i.e. build, up, etc.).",
        action="extend",
        default=[],
    )

    subparser.set_defaults(cmd=_run_dev)
