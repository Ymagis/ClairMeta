# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

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

    def test_dcp_probe_formating_xml(self):
        res = self.launch_command([
            'probe', self.get_dcp_path(1),
            '-type', 'dcp', '-format', 'xml'])
        ET.XML(res)

    def test_dcp_probe_formating_json(self):
        res = self.launch_command([
            'probe', self.get_dcp_path(1),
            '-type', 'dcp', '-format', 'json'])

        json_test = json.loads(res, object_pairs_hook=OrderedDict)
        with open(self.get_file_path('ECL01.json')) as f:
            json_gold = json.load(f, object_pairs_hook=OrderedDict)
        self.assertEqual(json_test, json_gold)

    def test_dcp_check_good(self):
        res = self.launch_command([
            'check', self.get_dcp_path(1),
            '-type', 'dcp', '-log', 'CRITICAL'])
        self.assertTrue(res)

    def test_dcp_check_bad(self):
        res = self.launch_command([
            'check', self.get_dcp_path(25),
            '-type', 'dcp', '-log', 'CRITICAL'])
        self.assertFalse(res)

    def test_dsm_probe(self):
        res = self.launch_command([
            'probe', '-type', 'dsm',
            self.get_dsm_path('DSM_PKG/MINI_DSM1')])
        self.assertTrue(res)

    def test_dsm_check_good(self):
        res = self.launch_command([
            'check', '-type', 'dsm',
            self.get_dsm_path('DSM_PKG/MINI_DSM1')])
        self.assertTrue(res)

    def test_dsm_check_bad(self):
        res = self.launch_command([
            'check', '-type', 'dsm',
            self.get_dsm_path('DSM_BAD_FILE_NAME_LENGTH')])
        self.assertFalse(res)


if __name__ == '__main__':
    unittest.main()
