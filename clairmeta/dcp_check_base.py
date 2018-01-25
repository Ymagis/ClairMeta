# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six
import time
import inspect
import traceback

from clairmeta.logger import get_log
from clairmeta.utils.file import human_size


class CheckException(Exception):
    """ All check shall raise a CheckException in case of falure. """
    pass


class CheckExecution(object):
    """ Check execution with status and time elapsed. """
    def __init__(self, name='', msg='', valid=False, time=0):
        self.name = name
        self.message = msg
        self.valid = valid
        self.seconds_elapsed = time


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
        self.check_profile = profile
        self.check_log = get_log()
        self.check_executions = []
        self.check_report = {}
        self.hash_callback = None

    def find_check_criticality(self, name):
        """ Find criticity of a particular check (using profile).

            Args:
                name (str): Name of the check function.

            Returns:
                Criticity level string.

        """
        check_level = self.check_profile['criticality']
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
        check_bypass = self.check_profile['bypass']

        return [
            v for k, v in member_list
            if k.startswith('check_' + prefix) and k not in check_bypass]

    def find_check_failed(self):
        """ Returns a list of all failed checks. """
        return [c for c in self.check_executions if not c.valid]

    def run_check(self, check, *args, **kwargs):
        """ Execute a check.

            Args:
                check (tuple): Tuple (function name, function).
                *args: Variable list of check function arguments.
                **kwargs: Variable list of keywords arguments.
                    message (str): error message prefix

            Returns:
                Tuple (status, return_value)

        """
        start = time.time()
        name, func = check.__name__, check
        check_exec = CheckExecution(name)
        check_res = None

        try:
            check_res = func(*args)
            check_exec.valid = True
            check_exec.msg = "Check valid"
        except CheckException as e:
            if kwargs.get('message'):
                msg = "{} : {}".format(kwargs.get('message'), str(e))
            else:
                msg = str(e)
            check_exec.msg = msg
        except Exception as e:
            check_exec.msg = "Check unknown error\n{}".format(
                traceback.format_exc())
            self.check_log.error(check_exec.msg)
        finally:
            check_exec.seconds_elapsed = time.time() - start
            self.check_executions.append(check_exec)
            return check_exec.valid, check_res

    def make_report(self):
        """ Check report generation. """
        self.check_report = {
            'ERROR': [],
            'WARNING': [],
            'INFO': [],
            'SILENT': []
        }

        for c in self.find_check_failed():
            level = self.find_check_criticality(c.name)
            self.check_report[level].append((c.name, c.msg))

        check_unique = set([c.name for c in self.check_executions])
        self.check_elapsed = {}
        self.total_time = 0
        self.total_check = len(check_unique)

        for name in check_unique:
            execs = [c.seconds_elapsed
                     for c in self.check_executions if c.name == name]
            elapsed = sum(execs)
            self.total_time += elapsed
            self.check_elapsed[name] = elapsed

    def dump_report(self):
        """ Dump check report. """
        valid_str = 'Sucess' if self.get_valid() else 'Fail'

        pretty_status = {
            'ERROR': 'Error(s)',
            'WARNING': 'Warning(s)',
            'INFO': 'Info(s)',
            'SILENT': 'Supressed(s)',
        }
        status_list = []

        for status, label in six.iteritems(pretty_status):
            checks = ["\t{} - {}".format(name, msg)
                      for name, msg in self.check_report[status]]
            if len(checks) > 0:
                checks_str = '\n'.join(checks)
                status_list.append("{} :\n{}".format(label, checks_str))

        bypass_list = self.check_profile['bypass']
        if len(bypass_list) > 0:
            bypass_list = ['\t' + b for b in bypass_list]
            checks_str = '\n'.join(bypass_list)
            status_list.append("Bypass(s) :\n{}".format(checks_str))

        self.check_log.info("DCP : {}".format(self.dcp.path))
        self.check_log.info("Size : {}".format(human_size(self.dcp.size)))
        [self.check_log.info(msg) for msg in status_list]
        self.check_log.info("Total check : {}".format(self.total_check))
        self.check_log.info("Total time : {:.2f} sec".format(self.total_time))
        self.check_log.info("Validation : {}\n".format(valid_str))

    def get_valid(self):
        """ Check status is valid. """
        return self.check_report['ERROR'] == []
