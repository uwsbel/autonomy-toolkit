:mod:`autonomy_toolkit.utils.files`
===================================

.. py:module:: autonomy_toolkit.utils.files

.. autoapi-nested-parse::

   Provides helper methods for interacting with the filesystem.



Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   autonomy_toolkit.utils.files.file_exists
   autonomy_toolkit.utils.files.search_upwards_for_file


.. function:: file_exists(filename: str, throw_error: bool = False, can_be_directory: bool = False) -> bool

   Check if the passed filename is an actual file

   :Parameters: * **filename** (*str*) -- The filename to check
                * **throw_error** (*bool*) -- If True, will throw an error if the file doesn't exist. Defaults to False.
                * **can_be_directory** (*bool*) -- If True, will check if it is a directory, in addition to a file

   :returns: *bool* -- True if the file exists, false otherwise

   Throws:
       FileNotFoundError: If filename is not a file and throw_error is set to true


.. function:: search_upwards_for_file(filename: str) -> Path

   Search in the current directory and all directories above it
   for a file of a particular name.

   Arg:
       filename (str): the filename to look for.

   :returns: *Path* -- the location of the first file found or None, if none was found


