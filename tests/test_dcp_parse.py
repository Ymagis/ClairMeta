# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import unittest
import os

from tests import DCP_MAP
from clairmeta.logger import disable_log
from clairmeta.dcp import DCP


class ParserTestBase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(ParserTestBase, self).__init__(*args, **kwargs)
        disable_log()

    def get_dcp_path(self, dcp_id):
        if dcp_id in DCP_MAP:
            dcp_folder = os.path.join(
                os.path.dirname(__file__),
                'resources', 'DCP', 'ECL-SET')
            dcp_name = DCP_MAP[dcp_id]

            folder_path = os.path.join(dcp_folder, dcp_name)
            self.assertTrue(os.path.exists(folder_path))
            return folder_path

    def parse(self, dcp_id):
        self.dcp = DCP(self.get_dcp_path(dcp_id))
        return self.dcp.parse()


class DCPParseTest(ParserTestBase):

    vf_missing = 'check_assets_cpl_missing_from_vf'

    def __init__(self, *args, **kwargs):
        super(DCPParseTest, self).__init__(*args, **kwargs)

    def test_dcp_01(self):
        res = self.parse(1)
        self.assertEqual(len(res['asset_list']), 14)
        self.assertEqual(len(res['volindex_list']), 1)
        self.assertEqual(len(res['assetmap_list']), 1)
        self.assertEqual(len(res['cpl_list']), 1)
        self.assertEqual(len(res['pkl_list']), 1)
        self.assertTrue(res['package_type'], 'OV')
        self.assertTrue(res['count_file'], '16')
        self.assertTrue(res['schema'], 'Interop')
        self.assertTrue(res['type'], 'DCP')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertFalse(cpl['AuxData'])
        self.assertFalse(cpl['HighFrameRate'])
        self.assertFalse(cpl['Stereoscopic'])
        self.assertFalse(cpl['Subtitle'])

    def test_dcp_02(self):
        res = self.parse(2)
        self.assertTrue(res['schema'], 'Interop')
        self.assertTrue(res['package_type'], 'VF')

    def test_dcp_07(self):
        res = self.parse(7)
        self.assertTrue(res['schema'], 'SMPTE')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertTrue(cpl['Stereoscopic'])

    def test_dcp_08(self):
        res = self.parse(8)
        self.assertTrue(res['schema'], 'SMPTE')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertTrue(cpl['Subtitle'])

    def test_dcp_09(self):
        res = self.parse(9)
        self.assertTrue(res['schema'], 'SMPTE')
        self.assertTrue(res['package_type'], 'OV')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertTrue(cpl['AuxData'])

    def test_dcp_10(self):
        res = self.parse(10)
        self.assertTrue(res['schema'], 'SMPTE')
        self.assertTrue(res['package_type'], 'VF')

    def test_dcp_11(self):
        res = self.parse(11)
        self.assertTrue(res['schema'], 'Interop')
        self.assertTrue(res['package_type'], 'VF')

    def test_dcp_22(self):
        res = self.parse(22)
        self.assertTrue(res['schema'], 'SMPTE')
        self.assertTrue(res['package_type'], 'OV')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertEqual(cpl['FrameRate'], 48)

    def test_dcp_23(self):
        res = self.parse(23)
        self.assertTrue(res['schema'], 'SMPTE')
        self.assertTrue(res['package_type'], 'OV')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertEqual(cpl['FrameRate'], 60)

    def test_dcp_25(self):
        res = self.parse(25)
        self.assertTrue(res['schema'], 'SMPTE')
        self.assertTrue(res['package_type'], 'OV')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertEqual(cpl['FrameRate'], 48)

    def test_dcp_26(self):
        res = self.parse(26)
        self.assertTrue(res['schema'], 'SMPTE')
        self.assertTrue(res['package_type'], 'OV')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertEqual(cpl['Resolution'], '1920x1080')

    def test_dcp_27(self):
        res = self.parse(27)
        self.assertTrue(res['schema'], 'SMPTE')
        self.assertTrue(res['package_type'], 'OV')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertEqual(cpl['Resolution'], '3840x2160')

    def test_dcp_28(self):
        res = self.parse(28)
        self.assertTrue(res['schema'], 'SMPTE')
        self.assertTrue(res['package_type'], 'OV')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertEqual(cpl['Resolution'], '4096x2160')

    def test_dcp_29(self):
        res = self.parse(29)
        self.assertTrue(res['schema'], 'Interop')
        self.assertTrue(res['package_type'], 'OV')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertTrue(cpl['Encrypted'])

    def test_dcp_30(self):
        res = self.parse(30)
        self.assertTrue(res['schema'], 'SMPTE')
        self.assertTrue(res['package_type'], 'OV')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertTrue(cpl['Encrypted'])

    def test_dcp_31(self):
        res = self.parse(31)
        self.assertTrue(res['schema'], 'Interop')
        self.assertTrue(res['package_type'], 'OV')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertEqual(cpl['Encrypted'], 'Mixed')

    def test_dcp_32(self):
        res = self.parse(32)
        self.assertTrue(res['schema'], 'SMPTE')
        self.assertTrue(res['package_type'], 'OV')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertEqual(cpl['Encrypted'], 'Mixed')

    def test_dcp_33(self):
        res = self.parse(33)
        self.assertTrue(res['schema'], 'Interop')
        self.assertTrue(res['package_type'], 'OV')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertTrue(cpl['Subtitle'])

    def test_dcp_38(self):
        res = self.parse(38)
        self.assertTrue(res['schema'], 'SMPTE')
        self.assertTrue(res['package_type'], 'OV')

    def test_dcp_39(self):
        res = self.parse(39)
        self.assertTrue(res['schema'], 'SMPTE')
        self.assertTrue(res['package_type'], 'OV')

        cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
        self.assertEqual(cpl['DecompositionLevels'], 'Mixed')

    def test_dcp_40(self):
        res = self.parse(40)
        self.assertTrue(res['schema'], 'SMPTE')
        self.assertTrue(res['package_type'], 'OV')

    def test_dcp_41_46(self):
        for dcp_id in [41, 42, 43, 44, 45, 46]:
            res = self.parse(dcp_id)
            self.assertTrue(res['schema'], 'SMPTE')
            self.assertTrue(res['package_type'], 'OV')

            cpl = res['cpl_list'][0]['Info']['CompositionPlaylist']
            self.assertTrue(cpl['HighFrameRate'])
