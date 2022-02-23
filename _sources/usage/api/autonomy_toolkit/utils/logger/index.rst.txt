:mod:`autonomy_toolkit.utils.logger`
====================================

.. py:module:: autonomy_toolkit.utils.logger

.. autoapi-nested-parse::

   Provides a custom logger object.

   Should be used like the following:

   .. highlight:: python
   .. code-block:: python

       from autonomy_toolkit.utils.logger import LOGGER

       LOGGER.fatal("Fatal")
       LOGGER.error("Error")
       LOGGER.warn("Warning")
       LOGGER.info("Information")
       LOGGER.debug("Debug")



Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   autonomy_toolkit.utils.logger.set_verbosity
   autonomy_toolkit.utils.logger.dumps_dict


.. function:: set_verbosity(verbosity: int)

   Set the verbosity level for the logger.
   Default verbosity is WARNING. ``verbosity`` should be a value
   greater than 0 and less than 2 that represents how many levels below WARNING is desired.
   For instance, if ``verbosity`` is 1, the new level will be INFO because
   that is one below WARNING. If ``verbosity`` is 2, the new level is DEBUG.
   DEBUG and INFO are currently the only two implemented

   :Parameters: **verbosity** (*int*) -- A value between 0 and 2 that represents the number of levels below WARNING that should be used when logging.


.. function:: dumps_dict(dic: dict) -> str

   Dumps a dictionary in a pretty-ish format to the logger.

   :Parameters: **dic** (*dict*) -- The dictionary to print

   :returns: *str* -- The pretty-ish string representation of the dict argument


