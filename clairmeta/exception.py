# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six


class ClairMetaException(Exception):
    """ Base class for all exception raised by this library. """
    pass


class CommandException(ClairMetaException):
    """ Raised when external command fails. """
    pass


class ProbeException(ClairMetaException):
    """ Raised when probing a DCP fails. """
    def __init__(self, msg):
        super(ProbeException, self).__init__(six.ensure_str(msg))


class CheckException(ClairMetaException):
    """ Non recoverable errors while checking a DCP.

        This is not to be used for regular check errors, where we instead use
        ``error()`` and ``fatal_error()`` methods.

    """
    pass
