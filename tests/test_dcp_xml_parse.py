# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import unittest
import os

from clairmeta.logger import disable_log
from clairmeta.dcp_utils import cpl_extract_characteristics
from clairmeta.dcp_parse import (assetmap_parse, volindex_parse, pkl_parse,
                                 cpl_parse, kdm_parse)


class ParserTestBase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(ParserTestBase, self).__init__(*args, **kwargs)
        disable_log()

    def get_file_path(self, name):
        file_path = os.path.join(
            os.path.dirname(__file__),
            'resources', 'XML', name)

        self.assertTrue(os.path.exists(file_path))
        return file_path


class VolIndexTest(ParserTestBase):

    def parse_and_check_schema(self, name, schema):
        vol = volindex_parse(self.get_file_path(name))
        self.assertIsNotNone(vol)
        self.assertEqual(vol['Info']['VolumeIndex']['Schema'], schema)
        return vol

    def test_volindex_smpte(self):
        self.parse_and_check_schema('VOLINDEX_SMPTE.xml', 'SMPTE')

    def test_volindex_smpte_nsprefix(self):
        self.parse_and_check_schema('VOLINDEX_SMPTE_NSPREFIX.xml', 'SMPTE')

    def test_volindex_iop(self):
        self.parse_and_check_schema('VOLINDEX_IOP', 'Interop')

    def test_volindex_void(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('ASSETVOID', 'Unknown')

    def test_volindex_plaintext(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('PLAINTEXT', 'Unknown')

    def test_volindex_assetmap(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('ASSETMAP_IOP', 'Interop')

    def test_volindex_cpl(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('CPL_SMPTE.xml', 'SMPTE')

    def test_volindex_pkl(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('PKL_SMPTE.xml', 'SMPTE')


class AssetMapTest(ParserTestBase):

    def parse_and_check_schema(self, name, schema):
        am = assetmap_parse(self.get_file_path(name))
        self.assertIsNotNone(am)
        self.assertEqual(am['Info']['AssetMap']['Schema'], schema)
        return am

    def test_assetmap_smpte(self):
        am = self.parse_and_check_schema('ASSETMAP_SMPTE.xml', 'SMPTE')
        assets = am['Info']['AssetMap']['AssetList']['Asset']

        self.assertTrue(isinstance(assets, list))
        for a in assets:
            if 'PackingList' in a:
                self.assertEqual(a['PackingList'], True)

    def test_assetmap_smpte_wrong_ext(self):
        self.parse_and_check_schema('ASSETMAP_SMPTE', 'SMPTE')

    def test_assetmap_smpte_nsprefix(self):
        self.parse_and_check_schema('ASSETMAP_SMPTE_NSPREFIX.xml', 'SMPTE')

    def test_asstemap_iop(self):
        am = self.parse_and_check_schema('ASSETMAP_IOP', 'Interop')
        assets = am['Info']['AssetMap']['AssetList']['Asset']

        self.assertTrue(isinstance(assets, list))
        for a in assets:
            if 'PackingList' in a:
                self.assertEqual(a['PackingList'], True)

    def test_asstemap_unknow_schema(self):
        self.parse_and_check_schema('ASSETMAP_BAD_SCHEMA', 'Unknown')

    def test_asstemap_bad_xml(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('ASSETMAP_BAD_XML.xml', 'Interop')

    def test_asstemap_void(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('ASSETVOID', 'Unknown')

    def test_asstemap_plaintext(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('PLAINTEXT', 'Unknown')

    def test_asstemap_cpl(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('CPL_SMPTE.xml', 'SMPTE')

    def test_asstemap_pkl(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('PKL_SMPTE.xml', 'SMPTE')


class PklTest(ParserTestBase):

    def parse_and_check_schema(self, name, schema):
        pkl = pkl_parse(self.get_file_path(name))
        self.assertIsNotNone(pkl)
        self.assertEqual(pkl['Info']['PackingList']['Schema'], schema)
        return pkl

    def test_pkl_smpte(self):
        self.parse_and_check_schema('PKL_SMPTE.xml', 'SMPTE')

    def test_pkl_iop(self):
        self.parse_and_check_schema('PKL_IOP.xml', 'Interop')

    def test_pkl_empty_tag(self):
        pkl = self.parse_and_check_schema('PKL_IOP_EMPTY_TAG.xml', 'Interop')
        self.assertEqual(pkl['Info']['PackingList']['Signer'], '')
        self.assertEqual(pkl['Info']['PackingList']['Signature'], '')

    def test_pkl_one_asset(self):
        pkl = self.parse_and_check_schema('PKL_IOP_ONE_ASSET.xml', 'Interop')
        assets = pkl['Info']['PackingList']['AssetList']['Asset']

        self.assertTrue(isinstance(assets, list))

    def test_pkl_assetmap(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('ASSETMAP_SMPTE.xml', 'SMPTE')

    def test_pkl_cpl(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('CPL_SMPTE.ml', 'SMPTE')

    def test_pkl_void(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('ASSETVOID', 'Unknown')

    def test_pkl_parse_plaintext(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('PLAINTEXT', 'Unknown')


class CplTest(ParserTestBase):

    def parse_and_check_schema(self, name, schema):
        cpl = cpl_parse(self.get_file_path(name))
        self.assertIsNotNone(cpl)
        self.assertEqual(cpl['Info']['CompositionPlaylist']['Schema'], schema)
        return cpl

    def test_cpl_smpte(self):
        self.parse_and_check_schema('CPL_SMPTE.xml', 'SMPTE')

    def test_cpl_iop(self):
        self.parse_and_check_schema('CPL_IOP.xml', 'Interop')

    def test_cpl_qubemaster(self):
        self.parse_and_check_schema('CPL_IOP_QUBEMASTER.xml', 'Interop')

    def test_cpl_mainstereo(self):
        cpl = self.parse_and_check_schema('CPL_SMPTE_MAINSTEREOSCOPIC.xml', 'SMPTE')
        cpl_extract_characteristics(cpl['Info']['CompositionPlaylist'])
        self.assertTrue(cpl['Info']['CompositionPlaylist']['Stereoscopic'])

    def test_cpl_no_mainsound(self):
        self.parse_and_check_schema('CPL_IOP_NO_MAINSOUND.xml', 'Interop')

    def test_cpl_no_mainpicture(self):
        cpl = self.parse_and_check_schema('CPL_SMPTE_NO_MAINPICTURE.xml', 'SMPTE')
        cpl_extract_characteristics(cpl['Info']['CompositionPlaylist'])
        self.assertFalse(cpl['Info']['CompositionPlaylist']['Picture'])

    def test_cpl_no_reellist(self):
        cpl = self.parse_and_check_schema('CPL_IOP_REEL_LIST_EMPTY.xml', 'Interop')
        self.assertEqual(cpl['Info']['CompositionPlaylist']['ReelList'], [])

    def test_cpl_rational_framerate(self):
        cpl = self.parse_and_check_schema('CPL_SMPTE_FRAMERATE_RATIONAL.xml', 'SMPTE')
        cpl_extract_characteristics(cpl['Info']['CompositionPlaylist'])
        self.assertEqual(cpl['Info']['CompositionPlaylist']['FrameRate'], 96)
        self.assertEqual(cpl['Info']['CompositionPlaylist']['EditRate'], 48)

    def test_cpl_missing_fields(self):
        self.parse_and_check_schema('CPL_SMPTE_MISSING_FIELDS.xml', 'SMPTE')

    def test_cpl_assetmap(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('ASSETMAP_IOP', 'Unknown')

    def test_cpl_pkl(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('PKL_SMPTE.xml', 'Unknown')

    def test_cpl_void(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('ASSETVOID', 'Unknown')

    def test_cpl_plaintext(self):
        with self.assertRaises(AssertionError):
            self.parse_and_check_schema('PLAINTEXT', 'Unknown')


class KdmTest(ParserTestBase):

    def parse(self, name):
        kdm = kdm_parse(self.get_file_path(name))
        self.assertIsNotNone(kdm)
        return kdm

    def test_kdm(self):
        kdm = self.parse('KDM.xml')
        self.assertEqual(kdm['Info']['KDM']['ImageKeys'], 6)
        self.assertEqual(kdm['Info']['KDM']['AudioKeys'], 6)
        self.assertEqual(kdm['Info']['KDM']['AtmosKeys'], 0)

    def test_kdm_void(self):
        with self.assertRaises(AssertionError):
            self.parse('ASSETVOID')

    def test_kdm_plaintext(self):
        with self.assertRaises(AssertionError):
            self.parse('PLAINTEXT')

    def test_kdm_assetmap(self):
        with self.assertRaises(AssertionError):
            self.parse('ASSETMAP_IOP')

    def test_kdm_cpl(self):
        with self.assertRaises(AssertionError):
            self.parse('CPL_SMPTE.xml')

    def test_kdm_pkl(self):
        with self.assertRaises(AssertionError):
            self.parse('PKL_SMPTE.xml')


if __name__ == '__main__':
    unittest.main()
