# SPDX-License-Identifier: MIT
"""
Utilities for the autonomy_toolkit package
"""

def getuser() -> str:
    """
    Get the username of the current user.

    Will leverage the ``getpass`` package.

    Returns:
        str: The username of the current user
    """
    import getpass
    return getpass.getuser()

def getuid(default: int = 1000) -> int:
    """
    Get the uid (user id) for the current user.

    If a Posix system (Linux, Mac) is detected, ``os.getuid`` is used. Otherwise, ``default`` is returned.

    Args:
        default (int): The default value if a posix system is not detected. Defaults to 1000. 

    Returns:
        int: The uid, either grabbed from the current user or the default if not a posix system.
    """
    import os
    return os.getuid() if os.name == "posix" else default

def getgid(default: int = 1000) -> int:
    """
    Get the gid (group id) for the current user.

    If a Posix system (Linux, Mac) is detected, ``os.getgid`` is used. Otherwise, ``default`` is returned.

    Args:
        default (int): The default value if a posix system is not detected. Defaults to 1000. 

    Returns:
        int: The gid, either grabbed from the current user or the default if not a posix system.
    """
    import os
    return os.getgid() if os.name == "posix" else default
