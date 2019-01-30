# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import unittest
import os

from clairmeta import Sequence
from clairmeta.logger import disable_log
from clairmeta.settings import SEQUENCE_SETTINGS


class SequenceTestBase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(SequenceTestBase, self).__init__(*args, **kwargs)
        disable_log()

    def get_path(self, name):
        file_path = os.path.join(
            os.path.dirname(__file__),
            'resources', 'SEQ', name)

        return file_path

    def check_dsm(self, path):
        return Sequence(self.get_path(path)).check(SEQUENCE_SETTINGS['DSM'])

    def check_dcdm(self, path):
        return Sequence(self.get_path(path)).check(SEQUENCE_SETTINGS['DCDM'])


class ParseTest(SequenceTestBase):

    def test_parse_dsm(self):
        res = Sequence(self.get_path('DSM_PKG/MINI_DSM1')).parse()
        self.assertTrue(isinstance(res, dict))
        self.assertEqual(len(res.keys()), 1)

    def test_parse_dsm_package(self):
        res = Sequence(self.get_path('DSM_PKG')).parse()
        self.assertTrue(isinstance(res, dict))
        self.assertEqual(len(res.keys()), 3)

    def test_parse_dcdm(self):
        res = Sequence(self.get_path('DCDM')).parse()
        self.assertTrue(isinstance(res, dict))
        self.assertEqual(len(res.keys()), 1)


class CheckTest(SequenceTestBase):

    def test_check_raise_not_folder(self):
        with self.assertRaises(ValueError):
            self.check_dsm('null')

    def test_check_raise_empty_folder(self):
        with self.assertRaises(ValueError):
            self.check_dsm('EMPTY')

    def test_check_raise_foreign(self):
        with self.assertRaises(ValueError):
            self.check_dsm('DSM_FOREIGN_FILE')

    def test_check_raise_j2k(self):
        with self.assertRaises(ValueError):
            self.check_dsm('REEL_J2K')

    def test_check_raise_length(self):
        with self.assertRaises(ValueError):
            self.check_dsm('DSM_BAD_FILE_NAME_LENGTH')

    def test_check_raise_jump(self):
        with self.assertRaises(ValueError):
            self.check_dsm('DSM_BAD_JUMP')

    def test_check_raise_desc(self):
        with self.assertRaises(ValueError):
            self.check_dsm('DSM_BAD_DESC')

    def test_check_dsm_ok(self):
        self.assertTrue(self.check_dsm('DSM_PKG/MINI_DSM1'))

    def test_check_dsm_empty_name(self):
        self.assertTrue(self.check_dsm('DSM_EMPTY_NAME'))

    def test_check_dsm_no_padding(self):
        self.assertTrue(self.check_dsm('DSM_NO_PADDING'))

    def test_check_package_ok(self):
        self.assertTrue(self.check_dsm('DSM_PKG'))

    def test_check_dcdm_ok(self):
        self.assertTrue(self.check_dcdm('DCDM'))


if __name__ == '__main__':
    unittest.main()
