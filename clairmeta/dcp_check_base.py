# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six
import time
import inspect
import traceback
from datetime import datetime

from clairmeta.logger import get_log
from clairmeta.dcp_check_report import CheckReport


class CheckException(Exception):
    """ All check shall raise a CheckException in case of falure. """
    def __init__(self, msg):
        super(CheckException, self).__init__(six.ensure_str(msg))


class CheckExecution(object):
    """ Check execution with status and related metadatas. """

    def __init__(self, func):
        """ Constructor for CheckExecution.

            Args:
                func (function): Check function.

        """
        self.name = func.__name__
        self.doc = func.__doc__
        self.message = ""
        self.valid = False
        self.bypass = False
        self.seconds_elapsed = 0
        self.asset_stack = []
        self.criticality = ""

    def short_desc(self):
        """ Returns first line of the docstring or function name. """
        docstring_lines = self.doc.split('\n')
        return docstring_lines[0].strip() if docstring_lines else c.name

    def to_dict(self):
        """ Returns a dictionary representation. """
        return {
            'name': self.name,
            'pretty_name': self.short_desc(),
            'doc': self.doc,
            'message': self.message,
            'valid': self.valid,
            'bypass': self.bypass,
            'seconds_elapsed': self.seconds_elapsed,
            'asset_stack': self.asset_stack,
            'criticality': self.criticality
        }



class CheckerBase(object):
    """ Base class for check module, provide check discover and run utilities.

        All check module shall derive from this class.

    """

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
            if name.startswith(c_name):
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
                Tuple (status, return_value)

        """
        check_exec = CheckExecution(check)
        check_exec.criticality = self.find_check_criticality(check_exec.name)
        check_exec.valid = False

        try:
            start = time.time()
            check_res = None
            check_res = check(*args)
        except CheckException as e:
            prefix = kwargs.get('error_prefix', '')
            check_exec.message = "{}{}".format(
                prefix + "\n\t" if prefix else '', str(e))
        except Exception as e:
            check_exec.message = "Check unknown error\n{}".format(
                traceback.format_exc())
            check_exec.criticality = "ERROR"
            self.log.error(check.msg)
        else:
            check_exec.valid = True
        finally:
            check_exec.asset_stack = kwargs.get('stack', [self.dcp.path])
            check_exec.seconds_elapsed = time.time() - start
            self.checks.append(check_exec)
            return check_exec.valid, check_res

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
