:mod:`autonomy_toolkit.utils`
=============================

.. py:module:: autonomy_toolkit.utils

.. autoapi-nested-parse::

   Utilities for the autonomy_toolkit package



Submodules
----------
.. toctree::
   :titlesonly:
   :maxdepth: 1

   atk_config/index.rst
   docker/index.rst
   files/index.rst
   logger/index.rst
   yaml_parser/index.rst


Package Contents
----------------


Functions
~~~~~~~~~

.. autoapisummary::

   autonomy_toolkit.utils.getuser
   autonomy_toolkit.utils.getuid
   autonomy_toolkit.utils.getgid


.. function:: getuser() -> str

   Get the username of the current user.

   Will leverage the ``getpass`` package.

   :returns: *str* -- The username of the current user


.. function:: getuid(default: int = 1000) -> int

   Get the uid (user id) for the current user.

   If a Posix system (Linux, Mac) is detected, ``os.getuid`` is used. Otherwise, ``default`` is returned.

   :Parameters: **default** (*int*) -- The default value if a posix system is not detected. Defaults to 1000.

   :returns: *int* -- The uid, either grabbed from the current user or the default if not a posix system.


.. function:: getgid(default: int = 1000) -> int

   Get the gid (group id) for the current user.

   If a Posix system (Linux, Mac) is detected, ``os.getgid`` is used. Otherwise, ``default`` is returned.

   :Parameters: **default** (*int*) -- The default value if a posix system is not detected. Defaults to 1000.

   :returns: *int* -- The gid, either grabbed from the current user or the default if not a posix system.


