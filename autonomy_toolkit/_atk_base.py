# SPDX-License-Identifier: MIT
"""
The entrypoint for the Autonomy Toolkit CLI is `atk`
The main parser will have a few commands, such as verbosity or a help menu.
For the most part, the entrypoint will be used to access subparsers,
such as `db` to interact with the ATK database.
"""
# Command imports
import autonomy_toolkit.db as db
import autonomy_toolkit.dev as dev
# import autonomy_toolkit.run as run

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
    parser = argparse.ArgumentParser(description="Autonomy Toolkit Command Line Interface")
    parser.add_argument('--version', action="store_true",  help='Level of verbosity', default=False)
    parser.add_argument('-v', '--verbose', dest='verbosity', action='count', help='Level of verbosity', default=0)
    parser.add_argument('--dry-run', action="store_true", help="Test run that will print out the commands it would run but not actually run them")
    parser.set_defaults(cmd=lambda x: x)

    # Initialize the subparsers
    subparsers = parser.add_subparsers()
    db._init(subparsers.add_parser("db", description="Interact with the ATK database"))  # noqa
    dev._init(subparsers.add_parser("dev", description="Work with the ATK development environment"))
    # run._init(subparsers.add_parser("run", description="Work with the ATK config files and generate generic docker compose systems"))

    return parser

def _main():
    # Create the parser
    parser = _init()

    # Parse the arguments and update logging
    known_args, unknown_args = parser.parse_known_args()

    # Return version if desired and exit
    if known_args.version:
        from autonomy_toolkit import __version__
        print(__version__)
        return

    set_verbosity(known_args.verbosity)

    # Calls the cmd for the used subparser
    from inspect import signature
    if len(signature(known_args.cmd).parameters) == 1:
        known_args.cmd(known_args)
    else:
        known_args.cmd(known_args, unknown_args)
