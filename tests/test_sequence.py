# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import unittest
import os

from clairmeta.logger import disable_log
from clairmeta.dsm import DSM
from clairmeta.dcdm import DCDM


class SequenceTestBase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(SequenceTestBase, self).__init__(*args, **kwargs)
        disable_log()

    def get_path(self, name):
        file_path = os.path.join(
            os.path.dirname(__file__),
            'resources', 'SEQ', name)

        return file_path


class ParseTest(SequenceTestBase):

    def test_parse_dsm(self):
        res = DSM(self.get_path('DSM_PKG/MINI_DSM1')).parse()
        self.assertTrue(isinstance(res, dict))
        self.assertEqual(len(res.keys()), 1)

    def test_parse_dsm_package(self):
        res = DSM(self.get_path('DSM_PKG')).parse()
        self.assertTrue(isinstance(res, dict))
        self.assertEqual(len(res.keys()), 3)

    def test_parse_dcdm(self):
        res = DCDM(self.get_path('DCDM')).parse()
        self.assertTrue(isinstance(res, dict))
        self.assertEqual(len(res.keys()), 1)


class CheckTest(SequenceTestBase):

    def test_check_raise_not_folder(self):
        with self.assertRaises(ValueError):
            DSM(self.get_path('null')).check()

    def test_check_raise_empty_folder(self):
        with self.assertRaises(ValueError):
            DSM(self.get_path('EMPTY')).check()

    def test_check_raise_foreign(self):
        with self.assertRaises(ValueError):
            DSM(self.get_path('DSM_FOREIGN_FILE')).check()

    def test_check_raise_j2k(self):
        with self.assertRaises(ValueError):
            DSM(self.get_path('REEL_J2K')).check()

    def test_check_raise_length(self):
        with self.assertRaises(ValueError):
            DSM(self.get_path('DSM_BAD_FILE_NAME_LENGTH')).check()

    def test_check_raise_jump(self):
        with self.assertRaises(ValueError):
            DSM(self.get_path('DSM_BAD_JUMP')).check()

    def test_check_raise_desc(self):
        with self.assertRaises(ValueError):
            DSM(self.get_path('DSM_BAD_DESC')).check()

    def test_check_dsm_ok(self):
        self.assertTrue(DSM(self.get_path('DSM_PKG/MINI_DSM1')).check())

    def test_check_dsm_empty_name(self):
        self.assertTrue(DSM(self.get_path('DSM_EMPTY_NAME')).check())

    def test_check_dsm_no_padding(self):
        self.assertTrue(DSM(self.get_path('DSM_NO_PADDING')).check())

    def test_check_package_ok(self):
        self.assertTrue(DSM(self.get_path('DSM_PKG')).check())

    def test_check_dcdm_ok(self):
        self.assertTrue(DCDM(self.get_path('DCDM')).check())


if __name__ == '__main__':
    unittest.main()
