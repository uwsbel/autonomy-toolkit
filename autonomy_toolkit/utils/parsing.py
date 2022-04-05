# SPDX-License-Identifier: MIT
"""
Helper methods/classes for parsing files.
"""

# Import some utilities
from autonomy_toolkit.utils.logger import LOGGER
from autonomy_toolkit.utils.files import file_exists

# External library imports
from abc import ABC, abstractmethod
import yaml, re, json

# =======
# Helpers
# =======

def replace_vars_in_file(file: 'ATKFile', vars_dict: dict):
    """Performs bash-like substitution in the passed file.

    See :meth:`replace_vars` for further information on implementation.

    Args:
        file (ATKFile): The file to do variable replacement for
        vars_dict (dict): The variable mapping to do the replacement
    """ 
    file.data = replace_vars(file.data, vars_dict)

def replace_vars(value: 'Union[Dict,Str,Iterable]', vars_dict: dict) -> 'Union[Dict,Str,Iterable]':
    """bash-like substitution for variables in the yaml file

    Will replace all variables with the following specification with variables in the ``vars_dict`` parameter.
    Code adapted from `podman compose <https://github.com/containers/podman-compose/blob/701311aa7a278eaa8b3a67d5928ee3531b60a9d7/podman_compose.py#L194>`_.
    
    This method functions similarly to docker and docker compose support subset of bash variable substitution,
    as defined `here <https://docs.docker.com/compose/compose-file/#variable-substitution>`_, `here <https://docs.docker.com/compose/env-file/>`_, and
    `here <https://www.gnu.org/software/bash/manual/html_node/Shell-Parameter-Expansion.html>`_. In docker/docker compose, variable substitution is defined
    through a variety of means, all which use $ as the identifier. To not cause any conflicts, @ is used instead for ``autonomy-toolkit``.

    The following attributes may be used:

    - ``@VARIABLE``: Simple variable replacement

    - ``@{VARIABLE}``: Simple variable replacement

    - ``@{VARIABLE:-default}``: default if not set or empty
    
    - ``@{VARIABLE-default}``: default if not set

    - ``@{VARIABLE:?err}``: raise error if not set or empty

    - ``@{VARIABLE?err}``: raise error if not set
    
    - ``@@``: escape that means @
    
    Args:
        value (Union[Dict,Str,Iterable]): The value to do variable placement on
        vars_dict (dict): The dictionary holding the variable mapping for replacement

    Returns:
        Union[Dict,Str,Iterable]: Value with replacements
    """
    var_re = re.compile(
        r"""
        \@(?:
            (?P<escaped>\@) |
            (?P<named>[_a-zA-Z][_a-zA-Z0-9]*) |
            (?:{
                (?P<braced>[_a-zA-Z][_a-zA-Z0-9]*)
                (?:(?P<empty>:)?(?:
                    (?:-(?P<default>[^}]*)) |
                    (?:\?(?P<err>[^}]*))
                ))?
            })
        )
    """,
        re.VERBOSE,
    )

    if isinstance(value, dict):
        value = {k: replace_vars(v, vars_dict) for k, v in value.items()}
    elif isinstance(value, str):
        def convert(m):
            if m.group("escaped") is not None:
                return "@"
            name = m.group("named") or m.group("braced")
            value = vars_dict.get(name)
            if value == "" and m.group("empty"):
                value = None
            if value is not None:
                return str(value)
            if m.group("err") is not None:
                raise RuntimeError(m.group("err"))
            return m.group("default") or m.group(0)

        value = var_re.sub(convert, value)
    elif hasattr(value, "__iter__"):
        value = [replace_vars(i, vars_dict) for i in value]
    return value

# ==============
# Helper Classes
# ==============

class ATKFile(ABC):
    """Base class that defines a file.

    Derived classes should inherit from :class:`ATKFile` and should represent a specific file type (such as
    YAML, JSON, etc.). They `must` utilize the ``self._data`` attribute to maintain it's internal data structure.

    Args:
        type (str): The type of file this represents as string (i.e. 'yaml', 'json', etc.). Used for logging.
    """

    def __init__(self, type: str):
        self._type = type
        self._data = None

    def replace_vars(self, vars_dict: dict):
        """Performs bash-like substitution in the passed file.

        See :meth:`replace_vars` for further information on implementation.

        Args:
            vars_dict (dict): The variable mapping to do the replacement
        """ 
        replace_vars_in_file(self, vars_dict)

    @property
    def data(self) -> 'Any':
        """Get the data stored by this file

        Returns:
            Any: the file's data
        """
        return self._data

    @data.setter
    def data(self, new_data: 'Any'):
        """Set the data stored by this file

        Args:
            new_data (Any): The new information to set to this file's data
        """
        self._data = new_data

    @abstractmethod
    def __str__(self) -> str:
        """Should implement some functionality to convert the underlying data to a string."""
        pass

    def write(self, output: str) -> bool:
        """Write this file to some output location.

        Args:
            output (str): The output file to write to

        Returns:
            bool: whether the operation was successful
        """
        with open(output, 'w') as f:
            f.write(str(self))

        return True

    def read(self, filename: str) -> str:
        """Read in the passed file and return it as a string.

        Args:
            filename (str): the file to read

        Returns:
            str: the file's contents as a string
        """
        if not file_exists(filename):
            LOGGER.warn(f"'{filename}' does not exist. Using an empty string.")
            return ""

        # Load the file
        LOGGER.debug(f"Reading '{filename}' as '{self._type}'...")
        with open(filename, "r") as f:
            text = f.read()
        LOGGER.debug(f"Read '{filename}' as '{self._type}'.")

        return text

class _ATKDictWrapperFile(ATKFile):
    def contains(self, *args) -> bool:
        LOGGER.debug(f"Checking if f{self._type} contains nested attributes: {args}...")

        # If no data is available, always return False:
        if self._data is None:
            return False

        _contains = True
        temp = self._data
        for arg in args:
            if arg not in temp:
                _contains = False
                LOGGER.debug(f"f{self._type} does not contain nested attributes: {args}.")
                break
            temp = temp[arg]
        return _contains

    def get(self, *args, default=None, throw_error=True) -> 'Any':
        LOGGER.debug(f"Getting nested attributes from f{self._type}: {args}...")

        temp = self._data
        if temp is not None:
            for arg in args:
                if arg not in temp:
                    LOGGER.info(f"f{self._type} does not contain nested attributes: {args}.")
                    if default is not None:
                        LOGGER.info(f"Using default: {default}.")
                    temp = default
                    break
                temp = temp[arg]

        if temp is None and throw_error:
            raise AttributeError(f"Default is not set and the nested attribute was not found: {args}.")

        return temp 

    def set(self, *args, value: 'Any', update_key: bool = False, throw_error: bool = True):
        temp = self._data
        args = list(args)
        while len(args):
            arg = args.pop(0)

            if arg in temp:
                if not len(args):
                    if update_key:
                        temp[value] = temp.pop(arg)
                    else:
                        temp[arg] = value
                else:
                    temp = temp[arg]
            else:
                raise AttributeError(f"The nested attribute was not found: {args}.")

        self._data = temp

    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]

class ATKJsonFile(_ATKDictWrapperFile):
    """A class to aid in parsing json configuration files

    The JsonParser can take in `either` a ``filename`` or a ``text`` parameter. If ``filename`` is passed,
    a file will be read and parsed using the json specification. If ``text`` is passed, the text will be 
    read and parsed using the json specification.

    Args:
        filename (str): the filename of the path to read
        text (str): the text to parse
    """
    def __init__(self, filename: str = None, text: str = None):
        super().__init__('json')

        if filename is None and text is None:
            LOGGER.fatal(f"filename and text in ATKJsonParser __init__ function are unset!!")
        else:
            if filename is not None and text is not None:
                LOGGER.warn(f"filename and text are both set in ATKJsonParser __init__ function. Using filename.")

            text = self.read(filename) if filename is not None else text

            self._data = json.loads(text)

    def __str__(self):
        return json.dumps(self._data)

class ATKYamlFile(_ATKDictWrapperFile):
    """A class to aid in parsing yaml configuration files

    Yaml files are human readable configuration files: https://yaml.org/.

    The YamlParser can take in `either` a ``filename`` or a ``text`` parameter. If ``filename`` is passed,
    a file will be read and parsed using the yaml specification. If ``text`` is passed, the text will be 
    read and parsed using the yaml specification.

    Args:
        filename (str): the filename of the path to read
        text (str): the text to parse
    """

    def __init__(self, filename: str = None, text: str = None):
        super().__init__('yaml')

        if filename is None and text is None:
            LOGGER.fatal(f"filename and text in ATKYamlParser __init__ function are unset!!")
        else:
            if filename is not None and text is not None:
                LOGGER.warn(f"filename and text are both set in ATKYamlParser __init__ function. Using filename.")

            text = self.read(filename) if filename is not None else text

            self._data = yaml.safe_load(text)

    def contains(self, *args) -> bool:
        """
        Checks whether the yaml file contains a certain nested attribute

        Ex:
            ```test.yml
            test:
                one: red
                two: blue
                three: green
            ```

            parser = YAMLParser('test.yml')
            parser.contains('test', 'one')          // true
            parser.contains('test', 'four')         // false
            parser.contains('test', 'one', 'red')   // false; only will search keys
           
        Args:
            *args: A list of arguments to search in the file

        Returns:
            bool: Whether the nested attributes are contained in the file
        """
        return super().contains(*args)

    def get(self, *args, default=None, throw_error=True) -> 'Any':
        """
        Grabs the attribute at the nested location provided by args

        Ex:
            ```test.yml
            test:
                one: red
                two: blue
                three: green
            ```

            parser = YAMLParser('test.yml')
            parser.get('test', 'one')               // red 
            parser.get('test', 'green', 'test')     // test
            parser.get('test', 'green')             // raises AttributeError
           
        Args:
            *args: A list of arguments to search in the file
            default (Any): The default value if the nested attribute isn't found
            throw_error (bool): Throw an error if default is None and the attribute isn't found. Defaults to True.

        Returns:
            Any: The value at the nested attributes

        Raises:
            AttributeError: If the nested attributes don't actually point to a value (i.e. contains(args) == False)
        """
        return super().get(*args, default=default, throw_error=throw_error)

    def set(self, *args, value: 'Any', update_key: bool = False, throw_error: bool = True):
        """
        Sets the attribute at the nested location provided by args

        Ex:
            ```test.yml
            test:
                one: red
                two: blue
                three: green
            ```

            parser = YAMLParser('test.yml')
            parser.set('test', 'one', value='black')
            parser.set('test', 'three', value='twenty', update_key=True)
            print(yaml.dump(parser.data))

            test:
                one: black
                two: blue
                twenty: green
           
        Args:
            *args: A list of arguments to search in the file
            value (Any): The value to set the found attribute to 
            update_key (bool): Updates the key rather than the value if True. Defaults to False.
            throw_error (bool): Throw an error if the attribute isn't found. Defaults to True.

        Raises:
            AttributeError: If the nested attributes don't actually point to a value (i.e. contains(args) == False)
        """
        return super().set(*args, value=value, update_key=update_key, throw_error=throw_error)

    def __str__(self):
        return yaml.dump(self._data)

class ATKTextFile(ATKFile):
    """Wrapper class around a simple text file.

    Args:
        filename (str): the filename of the path to read
        create (bool): if true, will create filename
    """

    def __init__(self, filename: str, create: bool = False):
        super().__init__('text')

        if create:
            self._data = ""
            self.write(filename)

        self._data = self.read(filename)

    def __str__(self):
        return self._data

    def __iadd__(self, data):
        if isinstance(data, ATKFile):
            self._data += data.data
        else:
            self._data += data

        return self
