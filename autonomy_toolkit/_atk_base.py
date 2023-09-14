# SPDX-License-Identifier: MIT
"""
The entrypoint for the Autonomy Toolkit CLI is `atk`
The main parser will have a few commands, such as verbosity or a help menu.
For the most part, the entrypoint will be used to access subparsers,
such as `db` to interact with the ATK database.
"""
# Command imports
import autonomy_toolkit.dev as dev

# Utility imports
from autonomy_toolkit.utils.logger import set_verbosity

# General imports
import argparse


def _init():
    """
    The root entrypoint for the ATK CLI is `atk`. This the first command you need to access the CLI. All subsequent subcommands succeed `atk`.
    """
    # Main entrypoint and initialize the cmd method
    # set_defaults specifies a method that is called if that parser is used
    parser = argparse.ArgumentParser(
        description="Autonomy Toolkit Command Line Interface"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show the Autonomy Toolkit version information",
        default=False,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        action="count",
        help="Level of verbosity",
        default=0,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test run that will print out the commands it would run but not actually run them",
    )
    parser.set_defaults(cmd=lambda x: x)

    # Initialize the subparsers
    subparsers = parser.add_subparsers()
    dev._init(
        subparsers.add_parser(
            "dev", description="Work with the ATK development environment"
        )
    )

    return parser


def _main():
    # Create the parser
    parser = _init()

    # Parse the arguments and update logging
    args, unknown = parser.parse_known_args()
    args._unknown_args = unknown

    # Return version if desired and exit
    if args.version:
        from autonomy_toolkit import __version__

        print(__version__)
        return

    set_verbosity(args.verbosity)

    # Calls the cmd for the used subparser
    args.cmd(args)
