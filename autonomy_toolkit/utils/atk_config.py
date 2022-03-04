"""
Abstracted helper class :class:`ATKConfig` used for reading/writing configuration files for ``autonomy-toolkit``.
"""

# Imports from atk
import autonomy_toolkit
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.files import search_upwards_for_file, unlink_file
from autonomy_toolkit.utils.yaml_parser import YAMLParser

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

        def __init__(self, name: 'List[str]', type: 'type', default: 'Any' = None):
            self.name = name
            self.path = '.'.join(name)
            self.type = type
            self.value = default
            self.required = default is None

        def __str__(self):
            return str(self.value)

    def __init__(self, filename: Union[Path, str] = '.atk.yml'):
        # First, grab the atk file
        self.atk_yml_path = search_upwards_for_file(str(filename))
        if self.atk_yml_path is None:
            LOGGER.fatal(
                f"No '{filename}' file was found in this directory or any parent directories. Make sure you are running this command in an autonomy-toolkit compatible repository.")
            exit(-1)

        # Fill out file paths we'll create later on
        self.root = self.atk_yml_path.parent
        self.docker_compose_path = self.root / ".docker-compose.yml"
        self.docker_ignore_path = self.root / ".dockerignore"
        self.atk_user_count_path = self.root / ".atk.user_count"
        self.atk_root = Path(autonomy_toolkit.__file__).parent

        # Add some required attributes
        self._required_attributes = []

        # Add some default custom attributes
        self._custom_attributes = {} 
        self.add_custom_attribute("project", str)
        self.add_custom_attribute("project_root", str, default=str(self.root))
        self.add_custom_attribute("external", dict, default={})

        self._config : 'YAMLParser' = None

    def add_required_attribute(self, *args):
        """
        Add a required attribute that must be present in the ``autonomy-toolkit`` YAML specification.

        Will be checked for existence when :meth:`parse` is called.

        Args:
            *args: The nested path of the required attribute, i.e. ``add_required_attribute("first_level", "second_level")`` corresponds to ``first_level: second_level: ...``.
        """
        self._required_attributes.append(args)

    def add_custom_attribute(self, *args, default: 'Any' = None, dest: 'str' = None):
        """
        Add a custom attribute to the ``autonomy-toolkit`` YAML specification.

        A custom attribute is any root-level attribute that's outside of the regular ``docker compose``
        YAML specification. After being read, it will be deleted from the written ``docker compose`` generated
        config file.

        The args list should begin with a list of ``len(*args)-1`` of nested keys. For instance, if a custom attribute
        should be structured like the following example, then ``add_custom_attribute("project", ...)`` 
        and ``add_custom_attribute("user", "name", ...)`` should be called.

        .. code-block:: yaml

            project: example
            user:
                name: example

        ``args[-1]`` should then be a type that describes the expected type of the variable. This is a required type.
        If the parsed type is not the same as this, an error will be thrown.

        ``default`` is the final argument. If it is unset (i.e. remains ``None``), the attribute will be assumed to be required.
        If set, when parsing, the value will be updated to be ``default`` if it is not set in the ATK config file.

        ``dest`` is the destination name for the variable that's generated from the custom attribute. By default, 
        if ``dest`` is ``None``, the last path element in ``args`` will be used. For instance,
        provided the yaml config above, if ``dest`` isn't provided for the ``user: name`` attribute, it will be
        set to ``'name'``.

        Args:
            *args: The list of arguments where the first ``len(args)-1`` represent a nested argument list (see docs) and ``args[-1]`` represents the type of the attribute.
            default (Any): The default value to set to the attribute when parsing.
            dest (str): The destination name for the variable that's generated.
        """
        path = args[:-1]
        type = args[-1]

        # Create the attribute and add it
        attr = self._Attr(path, type, default=default)
        self._custom_attributes[path[-1] if dest is None else dest] = attr

    def parse(self) -> bool:
        """Parse the ATK config file.

        Will read in the ATK config file as a yaml file. Utilizes the :class:`YAMLParser` class as the parser.

        The parser will walk through each custom attribute defined prior to :meth:`func` being called and 
        evaluate the attribute. Checks will be made to verify the types are correct, and if required attributes
        are defined. If a required attribute is not defined, an error will be thrown and parsing will stop. If an
        attribute has a wrong type, an error will be thrown and parsing will stop.

        Returns:
            bool: whether the file was successfully parsed
        """

        # First read in the config file
        self._config = YAMLParser(self.atk_yml_path)

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
            del self._config[attr.name[0]]

        # Need to eval custom_attributes twice since they might be nested
        # TODO: Fix this logic
        class _CustomAttrs(dict):
            """Helper class that won't through a KeyError when a key isn't found when using ``eval``
            """
            def __missing__(self, key):
                return key
        custom_attributes = {k: v.value for k,v in self._custom_attributes.items() if v.value != {}}
        custom_attributes = yaml.safe_load(eval(f"f'''{yaml.dump(custom_attributes)}'''", _CustomAttrs(custom_attributes)))
        custom_attributes = yaml.safe_load(eval(f"f'''{yaml.dump(custom_attributes)}'''", custom_attributes))

        # For each custom attribute, make it a class member for easy grabbing
        for k,v in self._custom_attributes.items():
            # Add the custom attribute as a class member for easy grabbing
            if not hasattr(self, k):
                if k in custom_attributes:
                    setattr(self, k, custom_attributes[k])
                else:
                    setattr(self, k, v.value)

        self._custom_attributes = custom_attributes

        return True

    def generate_compose(self, overwrite_lists: bool = False):
        """Generates a ``docker-compose.yml`` specification file that's used by ``docker compose``

        This method will grab the defaults that are shipped with ``autonomy-toolkit`` and merge them with
        the custom configurations provided through the custom yaml config file.

        The file will then be written to :attr:`self.docker_compose.path`

        Args:
            overwrite_lists (bool): If true, all lists in the default that conflict with lists in the custom config will be overwritten. If false, the lists will be extended.
        """

        # Load in the default docker-compose.yml file
        default_configs = YAMLParser(self.atk_root / "docker" / "default-compose.yml")

        # Merge the defaults with the atk config
        compose_config = ATKConfig._merge_dictionaries(self._config.get_data(), default_configs.get_data(), overwrite_lists)

        # Run an f-string eval on the entire file
        compose_config = eval(f"f'''{yaml.dump(compose_config)}'''", self._custom_attributes)
        
        # Write the docker compose file
        docker_compose_path = str(self.docker_compose_path)
        with open(docker_compose_path, 'w') as f:
            f.write(compose_config)

        self.compose = yaml.safe_load(compose_config)

    def overwrite_compose(self, compose: dict):
        """Overwrites the ``docker compose`` config file with a custom dictionary which is parsed as yaml

        Args:
            compose (dict): The dictionary to parse as yaml to be used to overwrite the compose file.
        """
        # Write the docker compose file
        with open(self.docker_compose_path, 'w') as f:
            f.write(yaml.dump(compose))

    def generate_ignore(self):
        """Generates a ``.dockerignore`` file that's used by ``docker``
        """

        # First grab the defaults
        with open(self.atk_root / "docker" / "dockerignore", 'r') as f:
            ignore_text = f.read()

        # Then concatenate with the existing dockerignore file, if there is one
        if (existing_ignore := search_upwards_for_file('.dockerignore')) is not None:
            with open(existing_ignore, 'r') as f:
                ignore_text += f.read()

        # And finally, write the file back to the dockerignore path
        with open(self.docker_ignore_path, "w") as f:
            f.write(ignore_text)

    def update_user_count(self, val: int):
        """Update the user count file to keep track of how many instances of the ATK container system has been initialized.

        An early issue with the ``autonomy-toolkit`` package was that if there were two instances of a container running,
        when one would exit, the clean-up process would take place (i.e. docker compose file would be deleted, etc.),
        but this wasn't desired. The user count was introduced to alleviate this issue, where the number of containers
        are kept track of. Only when there are zero current "users" will cleanup take place.

        This is implemented through a file that's constantly updated as new users are added/removed.

        Args:
            val (int): Either 1 or -1 for an added and removed user, respectively.

        Returns:
            int: The number of current members (including the changes introduced by this method call)
        """
        num = 0

        # First, read the existing file
        if Path(self.atk_user_count_path).exists():
            with open(self.atk_user_count_path, 'r') as f:
                num = int(f.read())

        num += val
        with open(self.atk_user_count_path, 'w') as f:
            f.write(str(num))

        return num

    def cleanup(self, keep_compose: bool = False):
        """Cleanup the system.

        Cleanup consists of deleting the ``docker compose`` config and ignore files, as well as the ``autonomy-toolkit`` user count file

        Args:
            keep_compose (bool): If true, will `not` delete the ``docker compose`` config file. Otherwise, it will be deleted.
        """
        unlink_file(self.atk_user_count_path)
        unlink_file(self.docker_ignore_path)
        if not keep_compose: unlink_file(self.docker_compose_path)

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
