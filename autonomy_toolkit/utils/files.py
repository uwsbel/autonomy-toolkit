# SPDX-License-Identifier: MIT
"""
Provides helper methods for interacting with the filesystem.
"""

# Import some utils
from autonomy_toolkit.utils.logger import LOGGER

# External library imports
from pathlib import Path
import os

def file_exists(filename: str, throw_error: bool = False, can_be_directory: bool = False) -> bool:
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


def search_upwards_for_file(filename: str) -> Path:
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

def unlink_file(filename: str):
    """Unlink (remove) a file

    Args:
        filename (str): The file to remove
    """
    if not Path(filename).exists():
        LOGGER.warn(f"'{filename}' was deleted prematurely. This may be a bug.")
        return 1
    else:
        os.unlink(filename)
        return 0
