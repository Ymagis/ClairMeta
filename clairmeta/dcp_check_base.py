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
    def __init__(self, msg):
        super(CheckException, self).__init__(six.ensure_str(msg))


class CheckExecution(object):
    """ Check execution with status and time elapsed. """

    def __init__(self, name):
        self.name = name
        self.doc = ""
        self.message = ""
        self.valid = False
        self.seconds_elapsed = 0
        self.asset_stack = []
        self.criticality = ""


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
        """ Find criticality of a particular check (using profile).

            Args:
                name (str): Name of the check function.

            Returns:
                Criticality level string.

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
        bypass = self.check_profile['bypass']

        checks = []
        for k, v in member_list:
            check_prefix = k.startswith('check_' + prefix)
            check_bypass = any([k.startswith(c) for c in bypass])

            if check_prefix and not check_bypass:
                checks.append(v)

        return checks

    def find_check_failed(self):
        """ Returns a list of all failed checks. """
        return [c for c in self.check_executions if not c.valid]

    def run_check(self, check, *args, **kwargs):
        """ Execute a check.

            Args:
                check (tuple): Tuple (function name, function).
                *args: Variable list of check function arguments.
                **kwargs: Variable list of keywords arguments.
                    error_prefix (str): error message prefix

            Returns:
                Tuple (status, return_value)

        """
        start = time.time()
        name, func = check.__name__, check
        check_exec = CheckExecution(name)
        check_exec.doc = check.__doc__
        check_res = None

        try:
            check_res = func(*args)
            check_exec.valid = True
            check_exec.msg = "Check valid"
        except CheckException as e:
            if kwargs.get('error_prefix'):
                msg = "{}\n\t{}".format(kwargs.get('error_prefix'), str(e))
            else:
                msg = str(e)
            check_exec.msg = msg
            check_exec.criticality = self.find_check_criticality(name)
        except Exception as e:
            check_exec.msg = "Check unknown error\n{}".format(
                traceback.format_exc())
            check_exec.criticality = "ERROR"
            self.check_log.error(check_exec.msg)
        finally:
            check_exec.asset_stack = kwargs.get('stack', [self.dcp.path])
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
            self.check_report[c.criticality].append((c.name, c.msg))

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
        valid_str = 'Success' if self.get_valid() else 'Fail'

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
        for c in self.find_check_failed():
            node = map_status[c.criticality]
            for filename in c.asset_stack:
                if filename not in node:
                    node[filename] = {}

                node = node[filename]
                if 'messages' not in node:
                    node['messages'] = []

            docstring_lines = c.doc.split('\n')
            desc = docstring_lines[0] if docstring_lines else c.name
            node['messages'] += ['.' + desc + '\n' + c.msg]

        self.check_log.info("DCP : {}".format(self.dcp.path))
        self.check_log.info("Size : {}".format(human_size(self.dcp.size)))

        for status, vals in six.iteritems(map_status):
            out_stack = []
            for k, v in six.iteritems(vals):
                out_stack += [self.dump_stack("", k, v, indent_level=0)]
            if out_stack:
                self.check_log.info("{}\n{}".format(
                    pretty_status[status] + ':',
                    "\n".join(out_stack)))

        if self.check_profile['bypass']:
            checks_str = '  ' + '\n  '.join(self.check_profile['bypass'])
            self.check_log.info("{}\n{}".format(
                pretty_status['BYPASS'] + ':', checks_str))

        self.check_log.info("Total check : {}".format(self.total_check))
        self.check_log.info("Total time : {:.2f} sec".format(self.total_time))
        self.check_log.info("Validation : {}\n".format(valid_str))

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

    def get_valid(self):
        """ Check status is valid. """
        return self.check_report['ERROR'] == []
