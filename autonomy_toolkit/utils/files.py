# SPDX-License-Identifier: MIT
"""
Provides helper methods for interacting with the filesystem.
"""

# Import some utils
from autonomy_toolkit.utils.logger import LOGGER

# External library imports
from typing import Union
from pathlib import Path


def file_exists(
    filename: str, throw_error: bool = False, can_be_directory: bool = False
) -> bool:
    """
    Check if the passed filename is an actual file

    Args:
        filename (str): The filename to check
        throw_error (bool): If True, will throw an error if the file doesn't exist. Defaults to False.
        can_be_directory (bool): If True, will check if it is a directory, in addition to a file

    Returns:
        bool: True if the file exists, false otherwise

    Throws:
        FileNotFoundError: If filename is not a file and throw_error is set to true
    """
    if can_be_directory:
        is_file = Path(filename).exists()
    else:
        is_file = Path(filename).is_file()
    if throw_error and not is_file:
        raise FileNotFoundError(f"{filename} is not a file.")
    return is_file


def search_upwards_for_file(filename: Union[Path, str]) -> Path:
    """Search in the current directory and all directories above it
    for a file of a particular name.

    Arg:
        filename (str): the filename to look for.

    Returns:
        Path: the location of the first file found or None, if none was found
    """
    d = Path.cwd()
    root = Path(d.root)

    while d != root:
        attempt = d / filename
        if attempt.exists():
            return attempt
        if d == d.parent:
            break
        d = d.parent

    return None


def read_file(filename: Union[Path, str]) -> str:
    """Read in the passed file and return it as a string.

    Args:
        filename (str): the file to read

    Returns:
        str: the file's contents as a string
    """
    if not file_exists(filename):
        LOGGER.warn(f"'{filename}' does not exist. Using an empty string.")
        return ""

    # Load the file
    LOGGER.debug(f"Reading '{filename}' as 'yaml'...")
    with open(filename, "r") as f:
        text = f.read()
    LOGGER.debug(f"Read '{filename}' as 'yaml'.")

    return text
