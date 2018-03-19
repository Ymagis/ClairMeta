# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import contextlib
import six
import re


@contextlib.contextmanager
def modified_dict(in_dict, *remove, **update):
    """ Temporarily updates the ``in_dict`` dictionary in-place.

        The ``in_dict`` dictionary is updated in-place so that the modification
        is sure to work in all situations.
        Source : https://stackoverflow.com/a/34333710/4814046

        Args:
            in_dict (dict): Input dict.
            remove: Environment variables to remove.
            update: Dict of environment variables and values to add/update.

    """
    env = in_dict
    update = update or {}
    remove = remove or []

    # List of environment variables being updated or removed.
    stomped = (set(update.keys()) | set(remove)) & set(env.keys())
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        [env.pop(k, None) for k in remove]
        yield
    finally:
        env.update(update_after)
        [env.pop(k) for k in remove_after]


def all_keys_in_dict(in_dict, keys):
    """ Check that all keys are present in a dictionary.

        Args:
            in_dict (dict): Input dict.
            keys (list): Keys that must be present in ``in_dict``.

        Returns:
            True if all ``keys`` are in ``in_dict``, False otherwise.

        >>> all_keys_in_dict(
        ... {'key1': '', 'key2': '', 'key3': ''}, ['key1', 'key2'])
        True
        >>> all_keys_in_dict(
        ... {'key1': '', 'key2': '', 'key3': ''}, ['key1', 'key4'])
        False

    """
    return all(k in in_dict for k in keys)


def any_keys_in_dict(in_dict, keys):
    """ Check that at least one key is present in a dictionary.

        Args:
            in_dict (dict): Input dict.
            keys (list): Keys that can be present in ``in_dict``.

        Returns:
            True if at least one key in ``keys`` is in ``in_dict``, False
            otherwise.

        >>> any_keys_in_dict(
        ... {'key1': '', 'key2': '', 'key3': ''}, ['key1', 'key2'])
        True
        >>> any_keys_in_dict(
        ... {'key1': '', 'key2': '', 'key3': ''}, ['key1', 'key4'])
        True
        >>> any_keys_in_dict(
        ... {'key1': '', 'key2': '', 'key3': ''}, ['key4'])
        False

    """
    return any(k in in_dict for k in keys)


def key_by_value_dict(in_dict, value):
    """ Reverse dictionary lookup.

        Args:
            in_dict (dict): Input dict.
            value: Lookup value.

        Returns:
            Key in ``in_dict`` containing ``value`` if found.

        >>> key_by_value_dict({'key1': 42, 'key2': 'forty-two'}, 42)
        'key1'
        >>> key_by_value_dict({'key1': 42, 'key2': 'forty-two'}, 'forty-two')
        'key2'
        >>> key_by_value_dict({'key1': 42, 'key2': 'forty-two'}, '1') is None
        True

    """
    for k, v in six.iteritems(in_dict):
        if value == v:
            return k


def key_by_path_dict(in_dict, path):
    """ Path-based dictionary lookup.

        Args:
            in_dict (dict): Input dict.
            path (str): Full path to the key (key.subkey1.subkey2).

        Returns:
            Value for key at ``path`` if found in ``in_dict``.

        >>> key_by_path_dict(
        ...     {'key1': {'subkey1': {'subkey2': 42}}},
        ...     'key1.subkey1.subkey2'
        ... )
        42
        >>> key_by_path_dict(
        ...     {'key1': {'subkey1': {'subkey2': 42}}},
        ...     'key1.subkey2.subkey1'
        ... ) is None
        True

    """
    node = in_dict
    node_path = path.split('.')

    while True:
        k = node_path.pop(0)
        if isinstance(node, dict) and k in node:
            node = node[k]
        else:
            return

        if len(node_path) == 0:
            break

    return node


def keys_by_name_dict(in_dict, name, matchs=None):
    """ Recursive dictionary lookup by name.

        Args:
            in_dict (dict): Input dict.
            name (str): Lookup key name.
            matchs (list): Match accumulator (recursive call only).

        Returns:
            List of Value for each key found in ``in_dict``.

        >>> sorted(
        ...  keys_by_name_dict(
        ...   {'key1': {'mykey': 1}, 'key2': {'mykey': 2}, 'mykey': 3},
        ...   'mykey'
        ...  )
        ... )
        [1, 2, 3]

    """
    p = r"^{}$".format(name)
    return keys_by_pattern_dict(in_dict, [p], matchs)


def keys_by_pattern_dict(in_dict, patterns, matchs=None):
    """ Recursive dictionary lookup by regex pattern.

        Args:
            in_dict (dict): Input dict.
            patterns (list): Lookup regex pattern list.
            matchs (list): Match accumulator (recursive call only).

        Returns:
            List of Value for each key found in ``in_dict``.

        >>> sorted(
        ...  keys_by_pattern_dict(
        ...   {'key1': {'mykey': 1}, 'key2': {'mykey': 2}, 'mykey': 3},
        ...   [r'^[A-Za-z]*$']
        ...  )
        ... )
        [1, 2, 3]

    """
    matchs = [] if matchs is None else matchs

    if isinstance(in_dict, dict):
        for k, v in six.iteritems(in_dict):
            if any([re.search(p, k) for p in patterns]):
                matchs.append(in_dict[k])
            keys_by_pattern_dict(v, patterns, matchs)
    if isinstance(in_dict, list):
        [keys_by_pattern_dict(item, patterns, matchs) for item in in_dict]

    return matchs


def remove_key_dict(in_dict, patterns):
    """ Recursive key remove by pattern from dictionary.

        Args:
            in_dict (dict): Input dict.
            patterns (list): Lookup regex pattern list.

        Returns:
            New dictionary with all key matching ``patterns`` removed.

        >>> remove_key_dict(
        ...     {'key1': {'mykey': 1}, 'key2': {'mykey': 2}, 'mykey': 3},
        ...     [r'^.*\d$']
        ... )
        {'mykey': 3}

    """
    if isinstance(in_dict, dict):
        in_dict = {
            key: remove_key_dict(value, patterns)
            for key, value in six.iteritems(in_dict)
            if not any([re.search(p, key) for p in patterns])}
    elif isinstance(in_dict, list):
        in_dict = [
            remove_key_dict(item, patterns)
            for item in in_dict]

    return in_dict


def transform_keys_dict(in_dict, func):
    """ Recursively transform all keys in dictionary.

        Args:
            in_dict (dict): Input dict.
            func (callable): Callable object that take one argument.

        Returns :
            New dictionary with keys transformed according to ``func``.

        >>> sorted(
        ...     transform_keys_dict(
        ...         {'A_key': 1, 'BKey': {'c_key': 3} }, camelize
        ...     ).items()
        ... )
        [('AKey', 1), ('BKey', {'cKey': 3})]

    """
    return {
        func(key): transform_keys_dict(value, func)
        if isinstance(value, dict) else value
        for key, value in six.iteritems(in_dict)
    }


def try_convert_number(in_val):
    """ String to number conversion with automatic fallback.

        Args:
            in_val (str): Input String.

        Returns:
            Integer or float representation of ``in_val``.

        >>> try_convert_number('2.0')
        2
        >>> try_convert_number('2.39')
        2.39
        >>> try_convert_number('2.2')
        2.2
        >>> try_convert_number('2.2.2')
        '2.2.2'
        >>> try_convert_number('3346518668994909089')
        3346518668994909089

    """
    if not isinstance(in_val, six.string_types):
        return in_val

    # We need to first try integer conversion because float representation
    # conversion might loose precision if we need to convert back to integer.
    try:
        return int(in_val)
    except (ValueError, TypeError):
        pass

    try:
        in_val = float(in_val)
        if in_val.is_integer():
            return int(in_val)
    except (ValueError, TypeError):
        pass

    return in_val


def camelize(string):
    """ Convert string to CamelCase notation (leave first character upper).

        >>> camelize('Color_space')
        'ColorSpace'
        >>> camelize('ColorSpace')
        'ColorSpace'

    """
    return re.sub(r'_([a-zA-Z])', lambda x: x.group(1).upper(), string)
