# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import re
import six
from collections import defaultdict
from datetime import datetime

from clairmeta.utils.file import human_size


class CheckReport(object):
    """ Check report listing all checks executions. """

    pretty_status = {
        'ERROR': 'Error(s)',
        'WARNING': 'Warning(s)',
        'INFO': 'Info(s)',
        'SILENT': 'Supressed(s)',
        'BYPASS': 'Bypass(s)',
    }

    def __init__(self, dcp, profile):
        """ Constructor for CheckReport.

            Args:
                dcp (clairmeta.DCP): DCP.
                profile (dict): Checker profile.

        """
        self.dcp = dcp
        self.checks = dcp.checks
        self.profile = profile
        self.date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.duration = sum([c.seconds_elapsed for c in self.checks])

        self._detect_check_criticality()

    def checks_count(self):
        """ Return the number of different checks executed. """
        check_unique = set([c.name for c in self.checks if not c.bypass])
        return len(check_unique)

    def checks_failed(self):
        """ Returns a list of all failed checks. """
        return [c for c in self.checks if c.has_errors()]

    def checks_succeeded(self):
        """ Returns a list of all succeeded checks. """
        return [c for c in self.checks if not c.has_errors() and not c.bypass]

    def checks_bypassed(self):
        """ Returns a set of all bypassed unique checks. """
        return [c for c in self.checks if c.bypass]

    def checks_by_criticality(self, criticality):
        """ Returns a list of failed checks with ``criticality``. """
        return [
            check
            for check in self.checks
            for error in check.errors
            if error.criticality == criticality]

    def errors_by_criticality(self, criticality):
        """ Returns a list of failed checks with ``criticality``. """
        return [
            error
            for check in self.checks
            for error in check.errors
            if error.criticality == criticality]

    def is_valid(self):
        """ Returns validity of checked DCP. """
        return all([c.is_valid() for c in self.checks])

    def pretty_str(self):
        """ Format the report in a human friendly way. """
        report = ""
        report += "Status : {}\n".format('Success' if self.is_valid() else 'Fail')
        report += "Path : {}\n".format(self.dcp.path)
        report += "Size : {}\n".format(human_size(self.dcp.size))
        report += "Total check : {}\n".format(self.checks_count())
        report += "Total time : {:.2f} sec\n".format(self.duration)
        report += "\n"

        nested_dict = lambda: defaultdict(nested_dict)
        status_map = nested_dict()

        # Accumulate all failed check and stack them by asset
        for check in self.checks_failed():
            lines = [". {}".format(check.short_desc())]

            for error in check.errors:
                asset = status_map[str(error.criticality)]

                for filename in check.asset_stack:
                    asset = asset[filename]

                desc = error.short_desc()
                desc = ". {}\n".format(desc) if desc else ""
                lines.append("{}{}".format(desc, error.message))

            asset['msg'] = asset.get('msg', []) + ["\n".join(lines)]

        # Ignore silenced checks
        status_map.pop('SILENT', None)

        for status, vals in six.iteritems(status_map):
            out_stack = []
            for k, v in six.iteritems(vals):
                out_stack += [self._dump_stack("", k, v, indent_level=0)]
            if out_stack:
                report += "{}\n{}\n".format(
                    self.pretty_status[status] + ':',
                    "\n".join(out_stack))

        bypassed = "\n".join(set(
            ['  . ' + c.short_desc() for c in self.checks_bypassed()]))
        if bypassed:
            report += "{}\n{}\n".format(
                self.pretty_status['BYPASS'] + ':', bypassed)

        return report

    def _detect_check_criticality(self):
        """ Assign criticality for each errors. """
        levels = self.profile['criticality']
        default = levels.get('default', 'ERROR')
        # Translate Perl like syntax to Python
        levels = {k.replace('*', '.*'): v for k, v in six.iteritems(levels)}

        for check in self.checks:
            for error in check.errors:
                score_profile = { 0: default }
                for c_name, c_level in six.iteritems(levels):
                    # Assumes python is internally caching regex compilation
                    if re.search(c_name, error.full_name()):
                        score_profile[len(c_name)] = c_level

                error.criticality = score_profile[max(score_profile.keys())]

    def _dump_stack(self, out_str, key, values, indent_level):
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
        desc = self._title_from_filename(filename)
        messages = values.pop('msg', [])

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
            out_str += self._dump_stack(
                out_str, k, v, indent_level + indent_step)

        return out_str

    def _title_from_filename(self, filename):
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

    def to_dict(self):
        """ Returns a dictionary representation. """
        return {
            'dcp_path': self.dcp.path,
            'dcp_size': self.dcp.size,
            'valid': self.is_valid(),
            'profile': self.profile,
            'date': self.date,
            'duration_seconds': self.duration,
            'message': self.pretty_str(),
            'unique_checks_count': self.checks_count(),
            'checks': [c.to_dict() for c in self.checks],
        }
