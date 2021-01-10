# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six
from collections import defaultdict

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

    def __init(self):
        """ Constructor for CheckReport. """
        self.dcp = None
        self.checks = []
        self.profile = ""
        self.date = ""
        self.duration = -1

    def checks_count(self):
        """ Return the number of different checks executed. """
        check_unique = set([c.name for c in self.checks if not c.bypass])
        return len(check_unique)

    def checks_failed(self):
        """ Returns a list of all failed checks. """
        return [c for c in self.checks if not c.valid and not c.bypass]

    def checks_failed_by_status(self, status):
        """ Returns a list of failed checks with ``status``. """
        return [
            c for c in self.checks
            if not c.valid and not c.bypass and c.criticality == status]

    def checks_succeeded(self):
        """ Returns a list of all succeeded checks. """
        return [c for c in self.checks if c.valid and not c.bypass]

    def checks_bypassed(self):
        """ Returns a set of all bypassed unique checks. """
        return [c for c in self.checks if c.bypass]

    def valid(self):
        """ Returns validity of checked DCP. """
        return not any([c.criticality == "ERROR" for c in self.checks if not c.valid])

    def pretty_str(self):
        """ Format the report in a human friendly way. """
        report = ""
        report += "Status : {}\n".format('Success' if self.valid() else 'Fail')
        report += "Path : {}\n".format(self.dcp.path)
        report += "Size : {}\n".format(human_size(self.dcp.size))
        report += "Total check : {}\n".format(self.checks_count())
        report += "Total time : {:.2f} sec\n".format(self.duration)
        report += "\n"

        nested_dict = lambda: defaultdict(nested_dict)
        status_map = nested_dict()

        # Accumulate all failed check and stack them by asset
        for c in self.checks_failed():
            asset = status_map[c.criticality]
            for filename in c.asset_stack:
                asset = asset[filename]

            asset['msg'] = (asset.get('msg', [])
                + ['. ' + c.short_desc() + '\n' + c.message])

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
            report += "{}\n{}\n".format(self.pretty_status['BYPASS'] + ':', bypassed)

        return report

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
            'valid': self.valid(),
            'profile': self.profile,
            'date': self.date,
            'duration_seconds': self.duration,
            'message': self.pretty_str(),
            'unique_checks_count': self.checks_count(),
            'checks': [c.to_dict() for c in self.checks],
        }
