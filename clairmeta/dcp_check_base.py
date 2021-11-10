# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import re
import six
import time
import inspect
import traceback
from datetime import datetime

from clairmeta.logger import get_log
from clairmeta.dcp_check_execution import (
    CheckException, CheckError, CheckExecution)
from clairmeta.dcp_check_report import CheckReport



class CheckerBase(object):
    """ Base class for check module, provide check discover and run utilities.

        All check module shall derive from this class.

    """

    ERROR_NAME_RE = re.compile("^\w+$")

    def __init__(self, dcp, profile):
        """ CheckerBase constructor.

            Args:
                dcp (clairmeta.DCP): DCP object.
                profile (dict): Checker profile.

        """
        self.dcp = dcp
        self.profile = profile
        self.log = get_log()
        self.checks = []
        self.errors = []
        self.report = None
        self.hash_callback = None

    def find_check_criticality(self, name):
        """ Find criticality of a particular check (using profile).

            Args:
                name (str): Name of the check function.

            Returns:
                Criticality level string.

        """
        check_level = self.profile['criticality']
        default = check_level.get('default', 'ERROR')
        score_profile = {
            0: default
        }

        for c_name, c_level in six.iteritems(check_level):
            # NOTE: very rough implementation
            # NOTE: not-optimized by compiling patterm
            # Translate Perl like syntax to Python
            c_name = c_name.replace('*', '.*')

            if re.search(c_name, name):
                score_profile[len(c_name)] = c_level

        return score_profile[max(score_profile.keys())]

    def find_check(self, prefix):
        """ Discover checks functions (using introspection).

            Args:
                prefix (str): Prefix of the checks to find (excluding leading
                    'check_').

            Returns:
                List of check functions.

        """
        member_list = inspect.getmembers(self, predicate=inspect.ismethod)
        bypass = self.profile['bypass']

        checks = []
        for k, v in member_list:
            check_prefix = k.startswith('check_' + prefix)
            check_bypass = any([k.startswith(c) for c in bypass])

            if check_prefix and not check_bypass:
                checks.append(v)
            elif check_bypass:
                check_exec = CheckExecution(v)
                check_exec.bypass = True
                self.checks.append(check_exec)

        return checks

    def run_check(self, check, *args, **kwargs):
        """ Execute a check.

            Args:
                check (function): Check function.
                *args: Variable list of check function arguments.
                **kwargs: Variable list of keywords arguments.
                    error_prefix (str): error message prefix

            Returns:
                Check function return value

        """
        self._check_setup()

        check_exec = CheckExecution(check)

        try:
            start = time.time()
            check_res = None
            check_res = check(*args)
        except CheckException as e:
            pass
        except Exception as e:
            error = CheckError("{}".format(traceback.format_exc()))
            error.name = "internal_error"
            error.parent_name = check_exec.name
            error.doc = "ClairMeta internal error"
            error.criticality = "ERROR"
            check_exec.errors.append(error)
            self.log.error(error.message)
        finally:
            for error in self.errors:
                error.parent_name = check_exec.name
                error.parent_doc = check_exec.doc
                error.criticality = self.find_check_criticality(
                    error.full_name())
                check_exec.errors.append(error)

            check_exec.asset_stack = kwargs.get('stack', [self.dcp.path])
            check_exec.seconds_elapsed = time.time() - start

            self.checks.append(check_exec)

            return check_res

    def _check_setup(self):
        """ Internal setup executed before each check is run. """
        self.errors = []

    def error(self, message, name="", doc=""):
        """ Append an error to the current check execution.

            Args:
                message (str): Error message.
                name (str): Error name that will be appended to the check name
                    to uniquely identify this error. Only alphanumeric
                    characters allowed.
                doc (str): Error description.

        """
        if name and not re.match(self.ERROR_NAME_RE, name):
            raise Exception("Error name invalid : {}".format(name))

        self.errors.append(CheckError(
            message,
            name.lower(),
            doc
        ))

    def fatal_error(self, message, name="", doc=""):
        """ Append an error and halt the current check execution. """
        self.error(message, name, doc)
        raise CheckException()

    def make_report(self):
        """ Check report generation. """
        report = CheckReport()
        report.dcp = self.dcp
        report.checks = self.checks
        report.profile = self.profile
        report.date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        report.duration = sum([c.seconds_elapsed for c in self.checks])

        self.report = report

    def dump_report(self):
        """ Dump check report. """
        self.log.info("Check report:\n\n" + self.report.pretty_str())
