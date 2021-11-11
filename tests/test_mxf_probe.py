# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import unittest
import os

from clairmeta.utils.probe import probe_mxf
from clairmeta.exception import CommandException


class TestAssetProbe(unittest.TestCase):

    def get_path(self, name):
        file_path = os.path.join(
            os.path.dirname(__file__),
            'resources', 'MXF', name)

        return file_path

    def test_video_iop(self):
        metadata = probe_mxf(
            self.get_path('picture_2D_iop.mxf'), stereoscopic=False)
        self.assertTrue(metadata['EditRate'] == 24)
        self.assertTrue(metadata['LabelSetType'] == 'MXFInterop')

    def test_video_smpte(self):
        metadata = probe_mxf(
            self.get_path('picture_2D_smpte.mxf'), stereoscopic=False)
        self.assertTrue(metadata['EditRate'] == 24)
        self.assertTrue(metadata['LabelSetType'] == 'SMPTE')

    def test_video_bitrate(self):
        metadata = probe_mxf(
            self.get_path('picture_over_250_mb.mxf'), stereoscopic=False)
        self.assertTrue(metadata['LabelSetType'] == 'SMPTE')
        self.assertTrue(metadata['AverageBitRate'] > 250)
        self.assertTrue(metadata['MaxBitRate'] > 350)

    def test_audio_iop(self):
        metadata = probe_mxf(self.get_path('audio_iop.mxf'))
        self.assertTrue(metadata['AudioSamplingRate'] == 48000)

    def test_audio_smpte(self):
        metadata = probe_mxf(self.get_path('audio_smpte.mxf'))
        self.assertTrue(metadata['AudioSamplingRate'] == 48000)

    def test_atmos(self):
        metadata = probe_mxf(self.get_path('atmos.mxf'))
        self.assertTrue(metadata['AtmosVersion'] == 1)

    def test_subtitle_smpte(self):
        metadata = probe_mxf(self.get_path('subtitle_smpte.mxf'))
        self.assertTrue(metadata['LabelSetType'] == 'SMPTE')
        self.assertEqual(
            metadata['NamespaceName'],
            r'http://www.smpte-ra.org/schemas/428-7/2007/DCST')

    def test_fake(self):
        with self.assertRaises(CommandException):
            probe_mxf('null')


if __name__ == '__main__':
    unittest.main()
