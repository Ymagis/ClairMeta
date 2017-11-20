# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import re


RE = '(^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$)'
FILE_RE = '([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
RFC4122_RE = '(^[0-9a-f]{8}-[0-9a-f]{4}-([1-5])[0-9a-f]{3}\
-[8-9a-b][0-9a-f]{3}-[0-9a-f]{12}$)'


def check_uuid(uuid, regex=RE):
    """ Check UUID validity against one of the available regex.

        Args:
            uuid (str): UUID string.
            regex: Pattern to validate ``uuid``.

        Returns:
            True if successful, False otherwise.

        >>> check_uuid('123e4567-e89b-12d3-a456-426655440000')
        True
        >>> check_uuid('23e4567-e89b-12d3-a456-426655440000')
        False

    """
    return re.match(regex, uuid) is not None


def extract_uuid(in_str, regex=FILE_RE):
    """ Extract UUID from a string.

        Args:
            in_str (str): Input string.
            regex: Pattern to extract the UUID.

        Returns:
            UUID extracted if sucessful.

        >>> extract_uuid('jp2k_123e4567-e89b-12d3-a456-426655440000_ecl')
        '123e4567-e89b-12d3-a456-426655440000'
        >>> extract_uuid('abcdefg') is None
        True

    """
    match = re.search(regex, in_str)
    if match:
        return match.group(0)
