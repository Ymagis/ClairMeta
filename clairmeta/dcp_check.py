# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import re
import six
import time
import importlib
import inspect
import traceback

from clairmeta.settings import DCP_CHECK_SETTINGS
from clairmeta.logger import get_log
from clairmeta.dcp_check_execution import CheckError, CheckExecution
from clairmeta.utils.file import ConsoleProgress
from clairmeta.exception import CheckException



class CheckerBase(object):
    """ Digital Cinema Package checker.

        Base class for check module, provide check discover and run utilities.
        All check module shall derive from this class.

    """

    ERROR_NAME_RE = re.compile(r"^\w+$")

    def __init__(
            self,
            dcp,
            ov_path=None,
            hash_callback=None,
            bypass_list=None,
            allowed_foreign_files=None):
        """ CheckerBase constructor.

            Args:
                dcp (clairmeta.DCP): DCP object.
                ov_path (str, optional): Absolute path of OriginalVersion DCP.
                hash_callback (function, optional): Callback function to report
                    file hash progression.
                bypass_list (list, optional): List of checks to bypass.
                allowed_foreign_files (list, optional): List of files allowed
                    in the DCP folder (don't trigger foreign files check).

        """
        self.dcp = dcp
        self.log = get_log()
        self.checks = []
        self.errors = []
        self.report = None
        self.bypass_list = bypass_list or []
        self.allowed_foreign_files = allowed_foreign_files or []
        self.check_modules = {}
        self.ov_path = ov_path
        self.ov_dcp = None

        self.hash_callback = hash_callback
        if not self.hash_callback:
            pass
        elif isinstance(self.hash_callback, ConsoleProgress):
            self.hash_callback._total_size = self.dcp.size
        elif inspect.isclass(self.hash_callback):
            raise CheckException(
                "Invalid callback, please provide a function"
                " or instance of ConsoleProgress (or derivate).")


    def load_modules(self):
        prefix = DCP_CHECK_SETTINGS['module_prefix']
        for k, v in six.iteritems(DCP_CHECK_SETTINGS['modules']):
            try:
                module_path = 'clairmeta.' + prefix + k
                module = importlib.import_module(module_path)
                checker = module.Checker(self.dcp)
                checker.ov_path = self.ov_path
                checker.allowed_foreign_files = self.allowed_foreign_files
                checker.hash_callback = self.hash_callback
                self.check_modules[v] = checker
            except (ImportError, Exception) as e:
                self.log.critical("Import error {} : {}".format(
                    module_path, str(e)))

    def check(self):
        """ Execute the complete check process.

            Returns:
                List of checks executed.

        """
        self.load_modules()
        return self.run_checks()

    def find_check(self, prefix):
        """ Discover checks functions (using introspection).

            Args:
                prefix (str): Prefix of the checks to find (excluding leading
                    'check_').

            Returns:
                List of check functions.

        """
        checks = []

        member_list = inspect.getmembers(self, predicate=inspect.ismethod)
        for k, v in member_list:
            check_prefix = k.startswith('check_' + prefix)
            check_bypass = any([k.startswith(c) for c in self.bypass_list])

            if check_prefix and not check_bypass:
                checks.append(v)
            elif check_bypass:
                check_exec = CheckExecution(v)
                check_exec.bypass = True
                self.checks.append(check_exec)

        return checks

    def run_checks(self):
        """ Execute all checks. """
        self.log.info("Checking DCP : {}".format(self.dcp.path))

        for _, checker in six.iteritems(self.check_modules):
            self.checks += checker.run_checks()
        return self.checks

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
            check_exec.errors.append(error)
            self.log.error(error.message)
        finally:
            for error in self.errors:
                error.parent_name = check_exec.name
                error.parent_doc = check_exec.doc
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
