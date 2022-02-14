"""
The entrypoint for the AV Toolkit CLI is `av`
The main parser will have a few commands, such as verbosity or a help menu.
For the most part, the entrypoint will be used to access subparsers,
such as `db` to interact with the AV database.
"""
# Command imports
import avtoolbox.db as db
import avtoolbox.dev as dev

# Utility imports
from avtoolbox.utils.logger import set_verbosity

# General imports
import argparse

def _init():
    """
    The root entrypoint for the AV CLI is `av`. This the first command you need to access the CLI. All subsequent subcommands succeed `av`.
    """
    # Main entrypoint and initialize the cmd method
    # set_defaults specifies a method that is called if that parser is used
    parser = argparse.ArgumentParser(description="AV Toolkit Command Line Interface")
    parser.add_argument('-v', '--verbose', dest='verbosity', action='count', help='Level of verbosity', default=0)
    parser.add_argument('--dry-run', action="store_true", help="Test run that will print out the commands it would run but not actually run them")
    parser.set_defaults(cmd=lambda x: x)

    # Initialize the subparsers
    subparsers = parser.add_subparsers()
    db._init(subparsers.add_parser("db", description="Interact with the AV database"))  # noqa
    dev._init(subparsers.add_parser("dev", description="Work with the AV development environment"))

    return parser

def _main():
    # Create the parser
    parser = _init()

    # Parse the arguments and update logging
    known_args, unknown_args = parser.parse_known_args()
    set_verbosity(known_args.verbosity)

    # Calls the cmd for the used subparser
    from inspect import signature
    if len(signature(known_args.cmd).parameters) == 1:
        known_args.cmd(known_args)
    else:
        known_args.cmd(known_args, unknown_args)
