# SPDX-License-Identifier: MIT
"""
Abstracted helper class :class:`ATKConfig` used for reading/writing configuration files for ``autonomy-toolkit``.
"""

# Imports from atk
import autonomy_toolkit
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.files import search_upwards_for_file, unlink_file
from autonomy_toolkit.utils.parsing import ATKYamlFile, ATKTextFile, replace_vars

# Other imports
from typing import Union
from pathlib import Path
import yaml

class ATKConfig:
    """Helper class that abstracts reading the ``.atk.yml`` file that defines configurations
    """

    class _Attr:
        """Helper class to store an attribute
        """

        def __init__(self, name: 'List[str]', type: 'type', default: 'Any' = None, delete: bool = True):
            self.name = name
            self.path = '.'.join(name)
            self.type = type
            self.value = default
            self.required = default is None
            self.delete = delete

        def __str__(self):
            return str(self.value)

    def __init__(self, filename: Union[Path, str] = '.atk.yml', container_runtime: str = "docker", default_container: str = "dev"):
        # First, grab the atk file
        self.atk_yml_path = search_upwards_for_file(str(filename))
        if self.atk_yml_path is None:
            LOGGER.fatal(
                f"No '{filename}' file was found in this directory or any parent directories. Make sure you are running this command in an autonomy-toolkit compatible repository.")
            exit(-1)

        self.container_runtime = container_runtime
        self.default_container = default_container

        # Fill out file paths we'll create later on
        self.root = self.atk_yml_path.parent
        self.compose_path = self.root / ".atk-compose.yml"
        self.atk_user_count_path = self.root / ".atk.user_count"
        self.atk_root = Path(autonomy_toolkit.__file__).parent

        # Docker specifics
        self.docker_ignore_path = self.root / ".dockerignore"

        # Add some required attributes
        self._required_attributes = []

        # Add some default custom attributes
        self._custom_attributes = {} 
        self.add_custom_attribute("project", type=str)
        self.add_custom_attribute("project_root", type=str, default=str(self.root))
        self.add_custom_attribute("external", type=dict, default={})

        # Translate rules are meant to aid in making the atk useable by different container runtimes
        # As an example, singularity-compose uses instances whereas docker composes services
        self._attribute_translation_rules = []

        self._config : 'ATKYamlFile' = None

    def add_required_attribute(self, *args):
        """
        Add a required attribute that must be present in the ``autonomy-toolkit`` YAML specification.

        Will be checked for existence when :meth:`parse` is called.

        Args:
            *args: The nested path of the required attribute, i.e. ``add_required_attribute("first_level", "second_level")`` corresponds to ``first_level: second_level: ...``.
        """
        self._required_attributes.append(args)

    def add_custom_attribute(self, *path: 'List[str]', type: 'type', default: 'Any' = None, dest: 'str' = None, delete: bool = True):
        """
        Add a custom attribute to the ``autonomy-toolkit`` YAML specification.

        A custom attribute is any root-level attribute that's outside of the regular ``docker compose``
        YAML specification. After being read, it will be deleted from the written ``docker compose`` generated
        config file.

        The first argument should be a list of nested keys. For instance, if a custom attribute
        should be structured like the following example, then ``add_custom_attribute("project", ...)`` 
        and ``add_custom_attribute("user", "name", ...)`` should be called.

        .. code-block:: yaml

            project: example
            user:
                name: example

        :attr:`type` should then be a type that describes the expected type of the variable. This is a required type.
        If the parsed type is not the same as this, an error will be thrown.

        ``default`` is the final argument. If it is unset (i.e. remains ``None``), the attribute will be assumed to be required.
        If set, when parsing, the value will be updated to be ``default`` if it is not set in the ATK config file.

        ``dest`` is the destination name for the variable that's generated from the custom attribute. By default, 
        if ``dest`` is ``None``, the last path element in ``args`` will be used. For instance,
        provided the yaml config above, if ``dest`` isn't provided for the ``user: name`` attribute, it will be
        set to ``'name'``.

        Args:
            path (List[str]): The nested argument list (see docs).
            type (type): Represents the type of the attribute.
            default (Any): The default value to set to the attribute when parsing.
            dest (str): The destination name for the variable that's generated.
            delete (bool): If False, the attribute will `not` be removed from the config file after parsing. Defaults to True.
        """
        # Create the attribute and add it
        attr = self._Attr(path, type, default=default, delete=delete)
        self._custom_attributes[path[-1] if dest is None else dest] = attr

    def add_attribute_translation_rule(self, *path: 'List[str]', rule: 'Tuple[str, str]'):
        """
        Add a translation rule to the ``autonomy-toolkit`` YAML specification.

        Translate rules are meant to aid in making the atk useable by different container runtimes.
        As an example, singularity-compose uses "instances" whereas docker composes "services". In this instance
        a translation such as the following would be added.

        .. code-block:: python

            config = ATKConfig()
            config.add_attribute_translation_rule(rule=("services", "instances"))

        The above rule will then find "services" at the root of the yaml config and replace it
        with "instances".

        .. code-block: python
            
            config = ATKConfig()
            config.add_attribute_translation_rule("services", "dev", rule=("before", "after"))

        This example will walk up to "services->dev" and replace "before" with "after".

        .. note::

            The translation rules are used only when the ATK config file is written. 
            Otherwise, analagous compose terms should be refered to as they are in the ``docker compose`` docs.

        Args:
            path (List[str]): The nested argument list (see docs).
            rule (Tuple[str, str]): translation rule (from, to) such that all "from"'s are translated to "to"'s.
        """
        self._attribute_translation_rules.append((path, rule))

    def parse(self) -> bool:
        """Parse the ATK config file.

        Will read in the ATK config file as a yaml file. Utilizes the :class:`ATKYamlFile` class as the parser.

        The parser will walk through each custom attribute defined prior to :meth:`func` being called and 
        evaluate the attribute. Checks will be made to verify the types are correct, and if required attributes
        are defined. If a required attribute is not defined, an error will be thrown and parsing will stop. If an
        attribute has a wrong type, an error will be thrown and parsing will stop.

        Returns:
            bool: whether the file was successfully parsed
        """

        # First read in the config file
        self._config = ATKYamlFile(self.atk_yml_path)

        # For each required attribute, check that it exists
        for path in self._required_attributes:
            if not self._config.contains(*path):
                LOGGER.fatal(f"Attribute at location '{'.'.join(path)}' is required, but it wasn't found.")
                return False

        # For each custom attribute, evalute it and remove it from the config
        for path, attr in self._custom_attributes.items():
            attr.value = self._config.get(*attr.name, default=attr.value)

            # Checks
            if attr.required and attr.value is None:
                LOGGER.fatal(f"Attribute '{path}' is required, but was not found.")
                return False
            if not isinstance(attr.value, attr.type):
                LOGGER.fatal(f"Attribute '{path}' expected to be of type '{attr.type}', but got '{type(attr.value)}'.")
                return False

            # Delete the attribute from the config
            # If it isn't present, this statement does nothing
            if attr.delete:
                del self._config[attr.name[0]]

        # Users may use mappings in custom attributes, so replace vars here
        temp = {k: v.value for k,v in self._custom_attributes.items()} # map only to the values
        self._custom_attributes = replace_vars(temp, temp)

        # For each custom attribute, make it a class member for easy grabbing
        for k,v in self._custom_attributes.items():
            # Add the custom attribute as a class member for easy grabbing
            if not hasattr(self, k):
                setattr(self, k, v)

        return True

    def generate_compose(self, services: 'List[str]' = [], overwrite_lists: bool = False):
        """Generates a ``atk-compose.yml`` specification file that's used by ``docker compose``

        This method will grab the defaults that are shipped with ``autonomy-toolkit`` and merge them with
        the custom configurations provided through the custom yaml config file.

        The file will `not` be written. See :meth:`write_compose`.

        Args:
            services (List[str]): List of services to maintain in the compose file. If none are passed, all are kept.
            overwrite_lists (bool): If true, all lists in the default that conflict with lists in the custom config will be overwritten. If false, the lists will be extended.
        """

        compose_config = self._config

        # Update the compose config to only include services that are in the services argument
        if compose_config.contains("services") and len(services):
            compose_config.set("services", value={k: v for k,v in compose_config.data["services"].items() if k in services})
            
        # Walk through translations and update any, if desired
        for path, (rfrom, rto) in self._attribute_translation_rules:
            compose_config.set(*[*path, rfrom], value=rto, update_key=True)

        # Do final variable replacement
        compose_config.replace_vars(self._custom_attributes)

        # Save vars
        self.compose_config = compose_config
        self.compose = compose_config.data

    def write_compose(self, compose: dict = None):
        """Writes the ``docker compose`` config file. 

        If ``compose`` is not None, the ``docker compose`` config file will be overwritten 
        with a custom dictionary which is parsed as yaml.

        Args:
            compose (dict): The dictionary to parse as yaml to be used to overwrite the compose file. Defaults to None (unused).
        """

        if compose is not None:
            # Update vars
            self.compose_config.data = compose
            self.compose = compose

        # Write the compose file
        self.compose_config.write(self.compose_path)

    def generate_dockerignore(self):
        """Generates a ``.dockerignore`` file that's used by ``docker``
        """

        # First grab the defaults
        ignore_text = ATKTextFile(self.atk_root / "containers" / "config" / "dockerignore")

        # Then concatenate with the existing dockerignore file, if there is one
        if (existing_ignore := search_upwards_for_file('.dockerignore')) is not None:
            ignore_text += ATKTextFile(existing_ignore)

        # And finally, write the file back to the dockerignore path
        ignore_text.write(self.docker_ignore_path)

    def update_user_count(self, val: int):
        """Update the user count file to keep track of how many instances of the ATK 
        container system has been initialized.

        An early issue with the ``autonomy-toolkit`` package was that if there were 
        two instances of a container running, when one would exit, the clean-up process 
        would take place (i.e. docker compose file would be deleted, etc.), but this wasn't 
        desired. The user count was introduced to alleviate this issue, where the number of containers
        are kept track of. Only when there are zero current "users" will cleanup take place.

        This is implemented through a file that's constantly updated as new users are added/removed.

        .. warning::

            This doesnt' work.

        Args:
            val (int): Either 1 or -1 for an added and removed user, respectively.

        Returns:
            int: The number of current members (including the changes introduced by this method call)
        """

        # First, read the existing file
        if not Path(self.atk_user_count_path).exists():
            atk_user_count_file = ATKTextFile(self.atk_user_count_path, create=True)

            # Start out with it being zero
            atk_user_count_file.data = "0"
            atk_user_count_file.write(self.atk_user_count_path)
        else:
            atk_user_count_file = ATKTextFile(self.atk_user_count_path)

        atk_user_count_file.data = str(int(atk_user_count_file.data) + val)
        atk_user_count_file.write(self.atk_user_count_path)

        return atk_user_count_file.data

    def cleanup(self, keep_compose: bool = False):
        """Cleanup the system.

        Cleanup consists of deleting the ``docker compose`` config and ignore files, as well as 
        the ``autonomy-toolkit`` user count file

        Args:
            keep_compose (bool): If true, will `not` delete the ``docker compose`` config file. Otherwise, it will be deleted.
        """
        unlink_file(self.atk_user_count_path)
        if not keep_compose: unlink_file(self.compose_path)

    def _merge_dictionaries(source, destination, overwrite_lists=False):
        for key, value in source.items():
            if isinstance(value, dict):
                node = destination.setdefault(key, {})
                ATKConfig._merge_dictionaries(value, node, overwrite_lists)
            elif not overwrite_lists and key in destination and isinstance(destination[key], list):
                if isinstance(value, list):
                    destination[key].extend(value)
                else:
                    destination[key].append(value)
            else:
                destination[key] = value

        return destination
