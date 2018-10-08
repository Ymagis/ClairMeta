# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import unittest
import os

from tests import DCP_MAP
from clairmeta.logger import disable_log
from clairmeta.profile import get_default_profile
from clairmeta.dcp import DCP


class CheckerTestBase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(CheckerTestBase, self).__init__(*args, **kwargs)
        disable_log()
        self.profile = get_default_profile()

    def get_dcp_path(self, dcp_id):
        if dcp_id in DCP_MAP:
            dcp_folder = os.path.join(
                os.path.dirname(__file__),
                'resources', 'DCP', 'ECL-SET')
            dcp_name = DCP_MAP[dcp_id]

            folder_path = os.path.join(dcp_folder, dcp_name)
            self.assertTrue(os.path.exists(folder_path))
            return folder_path

    def check(self, dcp_id, ov_id=None):
        self.dcp = DCP(self.get_dcp_path(dcp_id))
        self.status, self.report = self.dcp.check(
            profile=self.profile,
            ov_path=self.get_dcp_path(ov_id))
        return self.status

    def has_succeeded(self):
        return self.status

    def has_failed(self, check_name):
        failed = self.dcp._checker.find_check_failed()
        return check_name in [c.name for c in failed]


class DCPCheckTest(CheckerTestBase):

    vf_missing = 'check_assets_cpl_missing_from_vf'

    def __init__(self, *args, **kwargs):
        super(DCPCheckTest, self).__init__(*args, **kwargs)
        self.profile['bypass'] = ['check_assets_pkl_hash']

    def test_iop_ov(self):
        self.assertTrue(self.check(1))
        self.assertTrue(self.check(33))

    def test_iop_vf(self):
        self.assertTrue(self.check(2))
        self.assertTrue(self.has_failed(DCPCheckTest.vf_missing))
        self.assertTrue(self.check(2, ov_id=1))
        self.assertFalse(self.has_failed(DCPCheckTest.vf_missing))

    def test_smpte_ov(self):
        self.assertTrue(self.check(7))
        self.assertTrue(self.check(9))
        self.assertTrue(self.check(11))
        self.assertTrue(self.check(28))
        self.assertTrue(self.check(38))

    def test_smpte_vf(self):
        self.assertTrue(self.check(8))
        self.assertTrue(self.has_failed(DCPCheckTest.vf_missing))
        self.assertTrue(self.check(8, ov_id=11))
        self.assertFalse(self.has_failed(DCPCheckTest.vf_missing))

        self.assertTrue(self.check(10))
        self.assertTrue(self.has_failed(DCPCheckTest.vf_missing))
        self.assertTrue(self.check(10, ov_id=9))
        self.assertFalse(self.has_failed(DCPCheckTest.vf_missing))

    def test_smpte_ov_hfr(self):
        self.assertTrue(self.check(22))
        self.assertTrue(self.check(23))

    def test_over_bitrate(self):
        self.check(25)
        self.assertFalse(self.has_succeeded())
        self.assertTrue(self.has_failed('check_picture_cpl_max_bitrate'))
        self.assertTrue(self.has_failed('check_picture_cpl_avg_bitrate'))

        self.check(42)
        self.assertFalse(self.has_succeeded())
        self.assertTrue(self.has_failed('check_picture_cpl_max_bitrate'))
        self.assertTrue(self.has_failed('check_picture_cpl_avg_bitrate'))

    def test_nondci_resolution(self):
        self.assertTrue(self.check(26))
        self.assertTrue(self.has_failed('check_picture_cpl_resolution'))

        self.assertTrue(self.check(27))
        self.assertTrue(self.has_failed('check_picture_cpl_resolution'))

    def test_encrypted(self):
        self.assertTrue(self.check(29))
        self.assertTrue(self.check(30))

    def test_noncoherent_encryption(self):
        self.assertFalse(self.check(31))
        self.assertTrue(self.has_failed('check_cpl_reel_coherence_encryption'))
        self.assertFalse(self.check(32))
        self.assertTrue(self.has_failed('check_cpl_reel_coherence_encryption'))

    def test_iop_subtitle_png(self):
        self.assertTrue(self.check(33))
        self.assertFalse(self.has_failed('check_subtitle_cpl_image'))

    def test_noncoherent_jp2k(self):
        self.assertFalse(self.check(39))
        self.assertTrue(self.has_failed('check_picture_cpl_encoding'))
        self.assertTrue(self.has_failed('check_cpl_reel_coherence'))

    def test_mpeg(self):
        self.assertFalse(self.check(40))

    def test_hfr(self):
        self.assertTrue(self.check(41))
        self.assertTrue(self.check(43))
        self.assertTrue(self.check(44))
        self.assertTrue(self.check(45))
        self.assertTrue(self.check(46))

    def test_multi_pkl(self):
        self.assertTrue(self.check(47))


if __name__ == '__main__':
    unittest.main()
