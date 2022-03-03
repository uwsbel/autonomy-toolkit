:mod:`autonomy_toolkit.utils.docker`
====================================

.. py:module:: autonomy_toolkit.utils.docker

.. autoapi-nested-parse::

   Helpful utilities for interacting with docker. Many of these helpers came from the [python_on_whales](https://gabrieldemarmiesse.github.io/python-on-whales/) package.



Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   autonomy_toolkit.utils.docker.DockerComposeClient



Functions
~~~~~~~~~

.. autoapisummary::

   autonomy_toolkit.utils.docker.get_docker_client_binary_path
   autonomy_toolkit.utils.docker.compose_is_installed
   autonomy_toolkit.utils.docker.run_compose_cmd
   autonomy_toolkit.utils.docker.run_docker_cmd


.. py:exception:: DockerException(message: Any, stdout: str = None, stderr: str = None)

   Bases: :class:`Exception`

   Exception class that is used by the :class:`DockerComposeClient` when an error occurs

   :Parameters: * **message** (*Any*) -- The message to be stored in the base class Exception
                * **stdout** (*str*) -- The stdout from the command
                * **stderr** (*str*) -- The stderr from the command


.. py:class:: DockerComposeClient(project=None, services=[], compose_file='.docker-compose.yml')

   Helper class that provides the :meth:`run` method to execute a command using the ``docker compose``
   entrypoint.

   :Parameters: * **project** (*str*) -- The name of the project to use. Analagous with ``--project-name`` in ``docker compose``.
                * **services** (*List[str]*) -- List of services to use when running the ``docker compose`` command.
                * **compose_file** (*str*) -- The name of the compose file to use. Defaults to ``.docker-compose.yml``.

   .. method:: run(self, cmd, *args, **kwargs)

      Run a command using the system wide ``docker compose`` command

      If cmd is equal to ``exec``, ``exec_cmd`` will expect to be passed as a named argument. If not, a :class:`DockerException` will be thrown.

      Additional positional args (*args) will be passed as command arguments when running the command. Named arguments
      will be passed to :meth:`subprocess.run` (`see their docs <https://docs.python.org/3/library/subprocess.html#subprocess.run>`_).

      :Parameters: **cmd** (*str*) -- The command to run.

      :returns: *Tuple[str, str]* -- The stdout and stderr resulting from the command as a tuple.



.. function:: get_docker_client_binary_path() -> Optional[Path]

   Return the path of the docker client binary file.

   If ``None`` is returned, the docker client binary is not available and must be downloaded.

   Returns
       Optional[Path]: The path of the docker client binary file.


.. function:: compose_is_installed() -> bool

   Returns `True` if docker compose (the one written in Go)
   is installed and working.

   :returns: *bool* -- whether docker compose (v2) is installed.


.. function:: run_compose_cmd(*args, **kwargs)

   Run a docker compose command.


.. function:: run_docker_cmd(*args, **kwargs)

   Run a docker command.


