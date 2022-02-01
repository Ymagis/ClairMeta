# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import unittest
import os
import platform
from datetime import datetime

from tests import DCP_MAP, KDM_MAP, KEY
from clairmeta.logger import disable_log
from clairmeta.profile import get_default_profile
from clairmeta.dcp import DCP


class CheckerTestBase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(CheckerTestBase, self).__init__(*args, **kwargs)
        disable_log()
        self.profile = get_default_profile()
        self.profile['bypass'] = ['check_assets_pkl_hash']

    def get_dcp_folder(self):
        return os.path.join(
            os.path.dirname(__file__), 'resources', 'DCP', 'ECL-SET')

    def get_dcp_path(self, dcp_id):
        if dcp_id in DCP_MAP:
            dcp_name = DCP_MAP[dcp_id]
            folder_path = os.path.join(self.get_dcp_folder(), dcp_name)
            self.assertTrue(os.path.exists(folder_path))
            return folder_path

    def get_kdm_path(self, dcp_id):
        if dcp_id in KDM_MAP:
            kdm_name = KDM_MAP[dcp_id]
            file_path = os.path.join(self.get_dcp_folder(), kdm_name)
            self.assertTrue(os.path.exists(file_path))
            return file_path

    def check(self, dcp_id, ov_id=None, kdm=None, pkey=None):
        self.dcp = DCP(self.get_dcp_path(dcp_id))
        self.status, self.report = self.dcp.check(
            profile=self.profile,
            ov_path=self.get_dcp_path(ov_id),
        )
        return self.status

    def has_succeeded(self):
        return self.status

    def has_failed(self, check_name):
        failed = self.report.checks_failed()
        return check_name in [c.name for c in failed]


class DCPCheckTest(CheckerTestBase):

    vf_missing = 'check_assets_cpl_missing_from_vf'

    def __init__(self, *args, **kwargs):
        super(DCPCheckTest, self).__init__(*args, **kwargs)

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

    @unittest.skipIf(platform.system() == "Windows", "asdcp-unwrap on Windows doesn't properly unwrap resources files (including fonts) from MXF making check fails. Help wanted.")
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

    def test_encrypted_kdm(self):
        self.assertTrue(self.check(29, kdm=self.get_kdm_path(29), pkey=KEY))
        self.assertTrue(self.check(30, kdm=self.get_kdm_path(30), pkey=KEY))

    def test_noncoherent_encryption(self):
        self.assertFalse(self.check(31))
        self.assertTrue(self.has_failed('check_cpl_reel_coherence'))
        self.assertFalse(self.check(32))
        self.assertTrue(self.has_failed('check_cpl_reel_coherence'))

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


class DCPCheckReportTest(CheckerTestBase):

    def __init__(self, *args, **kwargs):
        super(DCPCheckReportTest, self).__init__(*args, **kwargs)
        self.check(25)

    def test_report_metadata(self):
        self.assertTrue(isinstance(self.report.profile, dict))
        self.assertTrue(datetime.strptime(self.report.date, "%d/%m/%Y %H:%M:%S"))
        self.assertGreaterEqual(self.report.duration, 0)

    def test_report_checks(self):
        self.assertGreaterEqual(
            len(self.report.checks), self.report.checks_count())

        failed = self.report.checks_failed()
        success = self.report.checks_succeeded()
        bypass = self.report.checks_bypassed()

        all_names = []
        for checks in [failed, success, bypass]:
            all_names += [c.name for c in checks]
        self.assertEqual(sorted(all_names), sorted([c.name for c in self.report.checks]))
        self.assertEqual(
            len(failed) + len(success) + len(bypass),
            len(self.report.checks))

        errors = self.report.errors_by_criticality('ERROR')
        self.assertEqual(3, len(self.report.checks_failed()))
        self.assertEqual(1, len(self.report.errors_by_criticality('ERROR')))
        self.assertEqual(2, len(self.report.errors_by_criticality('WARNING')))

        check = self.report.checks_by_criticality('ERROR')[0]
        self.assertEqual(check.name, "check_picture_cpl_max_bitrate")
        self.assertFalse(check.is_valid())
        self.assertFalse(check.bypass)
        self.assertGreaterEqual(check.seconds_elapsed, 0)
        self.assertEqual(check.asset_stack, [
            'CPL_ECL25SingleCPL_TST-48-600_S_EN-XX_UK-U_51_2K_DI_20180301_ECL_SMPTE_OV.xml',
            'ECL25SingleCPL_TST-48-600_S_EN-XX_UK-U_51_2K_DI_20180301_ECL_SMPTE_OV_01.mxf'])

        error = check.errors[0]
        self.assertEqual(error.full_name(), "check_picture_cpl_max_bitrate")
        self.assertEqual(
            error.message,
            "Exceed DCI maximum bitrate (250.05 Mb/s) : 358.25 Mb/s")
        self.assertTrue(error.criticality == "ERROR")

    def test_report_output(self):
        self.assertEqual(False, self.report.is_valid())

        report = self.report.pretty_str()
        self.assertTrue(report)
        self.assertTrue("Picture maximum bitrate DCI compliance." in report)

        self.assertTrue(self.report.to_dict())


if __name__ == '__main__':
    unittest.main()
