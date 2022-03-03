:mod:`autonomy_toolkit.utils.atk_config`
========================================

.. py:module:: autonomy_toolkit.utils.atk_config

.. autoapi-nested-parse::

   Abstracted helper class :class:`ATKConfig` used for reading/writing configuration files for ``autonomy-toolkit``.



Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   autonomy_toolkit.utils.atk_config.ATKConfig



.. py:class:: ATKConfig(filename: Union[Path, str] = '.atk.yml')

   Helper class that abstracts reading the ``.atk.yml`` file that defines configurations

   .. method:: add_custom_attribute(*args, default=None)

      Add a custom attribute to the ``autonomy-toolkit`` YAML specification.

      A custom attribute is any root-level attribute that's outside of the regular ``docker compose``
      YAML specification. After being read, it will be deleted from the written ``docker compose`` generated
      config file.

      The args list should begin with a list of len(*args)-1 of nested keys. For instance, if a custom attribute
      should be structured like the following example, then ``add_custom_attribute("project", ...)``
      and ``add_custom_attribute("user", "name", ...)`` should be called.

      .. code-block:: yaml

          project: example
          user:
              name: example



