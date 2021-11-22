# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import collections
import platform
import unittest
import os
import json
from collections import OrderedDict
from xml.etree import ElementTree as ET

from tests import DCP_MAP
from clairmeta.logger import disable_log
from clairmeta.cli import get_parser


class CliTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(CliTest, self).__init__(*args, **kwargs)
        disable_log()

    def get_file_path(self, name):
        file_path = os.path.join(
            os.path.dirname(__file__),
            'resources', name)

        return file_path

    def get_dcp_path(self, dcp_id):
        if dcp_id in DCP_MAP:
            dcp_folder = os.path.join(
                os.path.dirname(__file__),
                'resources', 'DCP', 'ECL-SET')
            dcp_name = DCP_MAP[dcp_id]

            folder_path = os.path.join(dcp_folder, dcp_name)
            self.assertTrue(os.path.exists(folder_path))
            return os.path.relpath(folder_path)

    def get_dsm_path(self, name):
        file_path = os.path.join(
            os.path.dirname(__file__),
            'resources', 'SEQ', name)

        return file_path

    def launch_command(self, args):
        parser = get_parser()
        args = parser.parse_args(args)
        return args.func(args)

    def test_dcp_probe_formating_dict(self):
        status, msg = self.launch_command([
            'probe', self.get_dcp_path(1),
            '-type', 'dcp', '-format', 'dict'])
        self.assertTrue(isinstance(eval(msg), collections.abc.Mapping))

    def test_dcp_probe_formating_xml(self):
        status, msg = self.launch_command([
            'probe', self.get_dcp_path(1),
            '-type', 'dcp', '-format', 'xml'])
        ET.XML(msg)

    def test_dcp_probe_formating_json(self):
        # Reference file contains Unix specific values (path formating)
        if platform.system() == "Windows":
            return

        status, msg = self.launch_command([
            'probe', self.get_dcp_path(1),
            '-type', 'dcp', '-format', 'json'])

        json_test = json.loads(msg, object_pairs_hook=OrderedDict)
        with open(self.get_file_path('ECL01.json')) as f:
            json_gold = json.load(f, object_pairs_hook=OrderedDict)

        # Prefer comparing strings for better diagnostic messages
        self.assertEqual(
            json.dumps(json_test, indent=4, sort_keys=True),
            json.dumps(json_gold, indent=4, sort_keys=True))

    def test_dcp_check_formating_dict(self):
        status, msg = self.launch_command([
            'check', self.get_dcp_path(1),
            '-type', 'dcp', '-format', 'dict'])
        self.assertTrue(isinstance(eval(msg), collections.abc.Mapping))

    def test_dcp_check_formating_xml(self):
        status, msg = self.launch_command([
            'check', self.get_dcp_path(1),
            '-type', 'dcp', '-format', 'xml'])
        ET.XML(msg)

    def test_dcp_check_formating_json(self):
        status, msg = self.launch_command([
            'check', self.get_dcp_path(1),
            '-type', 'dcp', '-format', 'json'])
        json.loads(msg, object_pairs_hook=OrderedDict)

    def test_dcp_check_good(self):
        status, msg = self.launch_command([
            'check', self.get_dcp_path(1),
            '-type', 'dcp', '-log', 'CRITICAL'])
        self.assertTrue(status)

    def test_dcp_check_good_progress(self):
        status, msg = self.launch_command([
            'check', self.get_dcp_path(1),
            '-type', 'dcp', '-log', 'CRITICAL', '-progress'])
        self.assertTrue(status)

    def test_dcp_check_good_relink(self):
        status, msg = self.launch_command([
            'check', self.get_dcp_path(2),
            '-type', 'dcp', '-log', 'CRITICAL',
            '-ov', self.get_dcp_path(1)])
        self.assertTrue(status)

    def test_dcp_check_wrong_relink(self):
        status, msg = self.launch_command([
            'check', self.get_dcp_path(1),
            '-type', 'dcp', '-log', 'CRITICAL',
            '-ov', self.get_dcp_path(2)])
        self.assertFalse(status)

    def test_dcp_check_bad(self):
        status, msg = self.launch_command([
            'check', self.get_dcp_path(25),
            '-type', 'dcp', '-log', 'CRITICAL'])
        self.assertFalse(status)

    def test_dsm_probe(self):
        status, msg = self.launch_command([
            'probe', '-type', 'dsm',
            self.get_dsm_path('DSM_PKG/MINI_DSM1')])
        self.assertTrue(status)

    def test_dsm_check_good(self):
        status, msg = self.launch_command([
            'check', '-type', 'dsm',
            self.get_dsm_path('DSM_PKG/MINI_DSM1')])
        self.assertTrue(status)

    def test_dsm_check_bad(self):
        status, msg = self.launch_command([
            'check', '-type', 'dsm',
            self.get_dsm_path('DSM_BAD_FILE_NAME_LENGTH')])
        self.assertFalse(status)


if __name__ == '__main__':
    unittest.main()
