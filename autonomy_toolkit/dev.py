# Imports from atk
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.atk_config import ATKConfig
from autonomy_toolkit.containers.docker_client import DockerClient

# External imports
from typing import Tuple


def _run_cmd(client, cmd, num_required_services=-1):
    if num_required_services >= 0 and num_required_services != len(client.services):
        LOGGER.fatal(
            f"The command '{cmd}' requires {num_required_services} service(s). You provided {len(client.services)}."
        )
        return False

    LOGGER.info(f"Running '{cmd}'...")
    if not getattr(client, cmd)():
        LOGGER.fatal(f"Failed to run '{cmd}'.")
        return False
    LOGGER.info(f"Finished running '{cmd}'.")

    return True


def _run_dev(args):
    LOGGER.info("Running 'dev' entrypoint...")

    # Find the atk.yml file
    filename = args.filename
    try:
        config = ATKConfig(filename, args.services)
    except Exception as e:
        LOGGER.fatal(e)
        return False

    # Update the config with optionals
    config.update_services_with_optionals(args.optionals)

    # Write the new configuration file
    config.write()

    # Create the docker client
    client = DockerClient(
        config,
        dry_run=args.dry_run,
        opts=args.compose_opts,
        args=args.compose_args,
    )

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

    if args.run and not _run_cmd(client, "run", 1):
        return False

    LOGGER.info("Finished running 'dev' entrypoint.")


def _init(subparser):
    LOGGER.debug("Initializing 'dev' entrypoint...")

    subparser.add_argument(
        "-s",
        "--services",
        nargs="+",
        help="The services to use. This is a required argument.",
        action="extend",
        default=[],
        required=True,
    )

    subparser.add_argument(
        "-b", "--build", action="store_true", help="Build the env.", default=False
    )
    subparser.add_argument(
        "-u", "--up", action="store_true", help="Spin up the env.", default=False
    )
    subparser.add_argument(
        "-d", "--down", action="store_true", help="Tear down the env.", default=False
    )
    subparser.add_argument(
        "-a", "--attach", action="store_true", help="Attach to the env.", default=False
    )
    subparser.add_argument(
        "-r",
        "--run",
        action="store_true",
        help="Run a command in the provided service. Only one service may be provided.",
        default=False,
    )
    subparser.add_argument(
        "-f",
        "--filename",
        help="The ATK config file. Defaults to 'atk.yml'",
        default="atk.yml",
    )
    subparser.add_argument(
        "--optionals",
        nargs="*",
        help="Custom CLI arguments that are cross referenced with the 'x-optionals' field in the ATK config file.",
        default=[],
    )
    subparser.add_argument(
        "--compose-opts",
        nargs="*",
        help="Additional options that are passed to the compose command. Use command as it would be used for the compose argument without the '--'. For docker, 'atk dev -b --opts no-cache -s dev' will equate to 'docker compose build --no-cache dev'. Will be passed to _all_ subcommands (i.e. build, up, etc.) if multiple are used.",
        default=[],
    )
    subparser.add_argument(
        "--compose-args",
        nargs="*",
        help="Additional arguments to pass to the compose command. All character following '--args' is passed at the very end of the compose command, i.e. 'atk dev -r -s dev --args ls' will run '... compose run dev ls'. Will be passed to _all_ subcommands (i.e. build, up, etc.) if multiple are used.",
        default=[],
    )

    subparser.set_defaults(cmd=_run_dev)
