# SPDX-License-Identifier: MIT

def is_port_available(port: int) -> bool:
    """Checks whether a specified port is available to be attached to.

    From `podman_compose <https://github.com/containers/podman-compose/blob/devel/podman_compose.py>`_.

    Args:
        port (int): The port to check.

    Returns:
        bool: True if available, False otherwise.
    """
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        in_use = s.connect_ex(('localhost', int(port))) == 0

    return not in_use
