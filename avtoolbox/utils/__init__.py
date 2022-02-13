"""
Utilities for the avtoolbox package
"""

def is_posix():
    """
    Determine whether the current OS is a posix (Linux, Mac) system.

    Returns:
        bool: whether current OS is a posix system
    """
    import os
    return os.name == "posix"
