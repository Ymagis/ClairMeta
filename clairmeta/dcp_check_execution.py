# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six


ERROR_SILENT = 0
ERROR_INFO = 1
ERROR_WARNING = 2
ERROR_ERROR = 3

ERROR_FROM_STR = {
    "SILENT": ERROR_SILENT,
    "INFO": ERROR_INFO,
    "WARNING": ERROR_WARNING,
    "ERROR": ERROR_ERROR
}

STR_FROM_ERROR = {
    v: k for k, v in six.iteritems(ERROR_FROM_STR)
}

def ErrorLevelFromString(error_str):
    return ERROR_FROM_STR[error_str]


def ErrorLevelToString(error_level):
    return STR_FROM_ERROR[error_level]


class CheckError(object):
    """ Error reporting from whithin checks accumulate a list of errors. """

    def __init__(self, msg, name="", doc=""):
        self.name = name
        self.parent_name = ""
        self.doc = doc
        self.parent_doc = doc
        self.message = msg
        self.criticality = "ERROR"

    def full_name(self):
        if self.name:
            return "{}_{}".format(self.parent_name, self.name)
        else:
            return self.parent_name

    def short_desc(self):
        """ Returns first line of the documentation. """
        lines = list(filter(None, self.doc.split('\n')))
        return lines[0].strip() if lines else ""

    def to_dict(self):
        """ Returns a dictionary representation. """
        return {
            'name': self.name,
            'pretty_name': self.short_desc(),
            'doc': self.doc,
            'message': self.message,
            'criticality': self.criticality,
        }

class CheckExecution(object):
    """ Check execution with status and related metadatas. """

    def __init__(self, func):
        """ Constructor for CheckExecution.

            Args:
                func (function): Check function.

        """
        self.name = func.__name__
        self.doc = func.__doc__
        self.bypass = False
        self.seconds_elapsed = 0
        self.asset_stack = []
        self.errors = []

    def short_desc(self):
        """ Returns first line of the docstring or function name. """
        docstring_lines = self.doc.split('\n')
        return docstring_lines[0].strip() if docstring_lines else c.name

    def is_valid(self, criticality="ERROR"):
        """ Returns whether check raised any errors is above ``criticality``.

            Args:
                criticality (str, optional): Maximum error level to be
                    considered invalid.

            Returns:
                Boolean

        """
        error_level = ErrorLevelFromString(criticality)
        return not any([
            ErrorLevelFromString(e.criticality) >= error_level
            for e in self.errors]
        )

    def has_errors(self, criticality=None):
        """ Returns whether check raised any errors of ``criticality``.

            Args:
                criticality (str, optional): Error level to consider, if empty
                    will look for all errors.

            Returns:
                Boolean

        """
        if not criticality:
            return self.errors != []
        else:
            error_level = ErrorLevelFromString(criticality)
            return any([
                e for e in self.errors
                if e.criticality == error_level]
            )

    def to_dict(self):
        """ Returns a dictionary representation. """
        return {
            'name': self.name,
            'pretty_name': self.short_desc(),
            'doc': self.doc,
            'bypass': self.bypass,
            'seconds_elapsed': self.seconds_elapsed,
            'asset_stack': self.asset_stack,
            'errors': [e.to_dict() for e in self.errors]
        }
