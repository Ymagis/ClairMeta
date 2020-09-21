# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six
import time
import inspect
import traceback
from datetime import datetime

from clairmeta.logger import get_log
from clairmeta.utils.file import human_size


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
        return docstring_lines[0] if docstring_lines else c.name


class CheckReport(object):
    """ Check report listing all checks executions. """

    def __init(self):
        """ Constructor for CheckReport. """
        self.checks = []
        self.profile = ""
        self.date = ""
        self.duration = ""

    def checks_count(self):
        """ Return the number of different checks executed. """
        check_unique = set([c.name for c in self.checks if not c.bypass])
        return len(check_unique)

    def checks_failed(self):
        """ Returns a list of all failed checks. """
        return [c for c in self.checks if not c.valid if not c.bypass]

    def checks_succeeded(self):
        """ Returns a list of all succeeded checks. """
        return [c for c in self.checks if c.valid if not c.bypass]

    def checks_bypassed(self):
        """ Returns a set of all bypassed unique checks. """
        return [c for c in self.checks if c.bypass]

    def valid(self):
        """ Returns validity of checked DCP. """
        return not any([c.criticality == "ERROR" for c in self.checks if not c.valid])


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
        report.checks = self.checks
        report.profile = self.profile
        report.date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        report.duration = sum([c.seconds_elapsed for c in self.checks])

        self.report = report

    def dump_report(self):
        """ Dump check report. """
        pretty_status = {
            'ERROR': 'Error(s)',
            'WARNING': 'Warning(s)',
            'INFO': 'Info(s)',
            'SILENT': 'Supressed(s)',
            'BYPASS': 'Bypass(s)',
        }

        map_status = {
            'ERROR': {},
            'WARNING': {},
            'INFO': {},
            'SILENT': {},
        }

        # Accumulate all failed check and stack them by asset
        for c in self.report.checks_failed():
            node = map_status[c.criticality]
            for filename in c.asset_stack:
                if filename not in node:
                    node[filename] = {}

                node = node[filename]
                if 'messages' not in node:
                    node['messages'] = []

            node['messages'] += ['.' + c.short_desc() + '\n' + c.message]

        self.log.info("DCP : {}".format(self.dcp.path))
        self.log.info("Size : {}".format(human_size(self.dcp.size)))

        for status, vals in six.iteritems(map_status):
            out_stack = []
            for k, v in six.iteritems(vals):
                out_stack += [self.dump_stack("", k, v, indent_level=0)]
            if out_stack:
                self.log.info("{}\n{}".format(
                    pretty_status[status] + ':',
                    "\n".join(out_stack)))

        bypassed = "\n".join(set(
            ['  .' + c.short_desc() for c in self.report.checks_bypassed()]))
        if bypassed:
            self.log.info("{}\n{}".format(pretty_status['BYPASS'] + ':', bypassed))

        self.log.info("Total check : {}".format(self.report.checks_count()))
        self.log.info("Total time : {:.2f} sec".format(self.report.duration))
        self.log.info("Validation : {}\n".format(
            'Success' if self.report.valid() else 'Fail'))

    def dump_stack(self, out_str, key, values, indent_level):
        """ Recursively iterate through the error message stack.

            Args:
                out_str (str): Accumulate messages to ``out_str``
                key (str): Filename of the current asset.
                values (dict): Message stack to dump.
                indent_level (int): Current indentation level.

            Returns:
                Output error message string

        """
        indent_offset = 2
        indent_step = 2
        indent_char = ' '
        ind = indent_offset + indent_level

        filename = key
        desc = self.title_from_filename(filename)
        messages = values.pop('messages', [])

        out_str = '' if indent_level == 0 else '\n'
        out_str += indent_char * ind + '+ '
        out_str += filename
        out_str += ' ' + desc if desc else ''

        ind += indent_step
        for m in messages:
            out_str += "\n"
            out_str += indent_char * ind
            # Correct indentation for multi-lines messages
            out_str += ("\n" + indent_char * (ind + 2)).join(m.split("\n"))
        ind -= indent_step

        for k, v in six.iteritems(values):
            out_str += self.dump_stack(
                out_str, k, v, indent_level + indent_step)

        return out_str

    def title_from_filename(self, filename):
        """ Returns a human friendly title for the given file. """
        for cpl in self.dcp._list_cpl:
            if cpl['FileName'] == filename:
                desc = "({})".format(
                    cpl['Info']['CompositionPlaylist'].get(
                        'ContentTitleText', ''))
                return desc

        for pkl in self.dcp._list_pkl:
            if pkl['FileName'] == filename:
                desc = "({})".format(
                    pkl['Info']['PackingList'].get('AnnotationText', ''))
                return desc

        return ''
