# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six

from clairmeta.utils.time import compare_ratio
from clairmeta.dcp_check import CheckerBase
from clairmeta.dcp_utils import list_cpl_assets
from clairmeta.settings import DCP_SETTINGS


class Checker(CheckerBase):

    def __init__(self, dcp):
        super(Checker, self).__init__(dcp)
        self.settings = DCP_SETTINGS['picture']

    def run_checks(self):
        for source in self.dcp._list_cpl:
            asset_stack = []

            asset_checks = self.find_check('picture_cpl')
            [self.run_check(
                check, source, asset,
                stack=[
                    source['FileName'],
                    asset[1].get('Path', asset[1]['Id'])])
             for asset in list_cpl_assets(source, filters='Picture')
             for check in asset_checks]

        return self.checks

    def get_picture_max_bitrate(self, playlist, asset):
        bitrate_map = {
            'DCI': self.settings['max_dci_bitrate'],
            'HFR': self.settings['max_hfr_bitrate'],
            'DVI': self.settings['max_dvi_bitrate'],
        }

        resolution = asset['Probe']['Resolution']
        editrate = asset['Probe']['EditRate']
        dimension = '3D' if asset['Stereoscopic'] else '2D'
        hfr_threshold = self.settings['min_editrate_hfr_bitrate']

        bitrate = 'DCI'

        if playlist['Info']['CompositionPlaylist']['DolbyVision']:
            bitrate = 'DVI'
        elif resolution in self.settings['resolutions']['2K']:
            hfr_bitrate = editrate >= hfr_threshold['2K'][dimension]
            bitrate = 'HFR' if hfr_bitrate else 'DCI'
        elif resolution in self.settings['resolutions']['4K']:
            hfr_bitrate = editrate >= hfr_threshold['4K'][dimension]
            bitrate = 'HFR' if hfr_bitrate else 'DCI'

        return bitrate_map[bitrate]

    def check_picture_cpl_resolution(self, playlist, asset):
        """ Stored pixel array size compliance.

            Useful discussion can be found at:
                https://github.com/Ymagis/ClairMeta/pull/184

            References:
                DCI CTP 4.5.1
                SMPTE 428-1-2006 3
                SMPTE 429-2-2013 8.2
                SMPTE RDD 52:2020 7.1

        """
        dci_resolutions = [
            self.settings['resolutions']['2K'] +
            self.settings['resolutions']['4K']
        ]
        rdd52_array_sizes = [
            self.settings['pixel_array_sizes']['2K'] +
            self.settings['pixel_array_sizes']['4K']
        ]

        _, asset = asset
        if 'Probe' in asset:
            resolution = asset['Probe']['Resolution']

            if not any([resolution in res for res in dci_resolutions]):
                self.error(
                    "Picture has non DCI compliant pixel array size {}"
                    .format(resolution), "dci")

            if not any([resolution in res for res in rdd52_array_sizes]):
                self.error(
                    "Picture has non RDD52 compliant pixel array size {}"
                    .format(resolution), "rdd52")


    def check_picture_cpl_encoding(self, playlist, asset):
        """ Picture wavelet transform levels SMPTE compliance.

            References:
                SMPTE ST 422:2014 8.2.3
                SMPTE ST 429-2:2013 10.2.2
                DCI DCSS (v1.4) 4.3.3
        """
        resolutions = self.settings['resolutions']
        levels_map = {
            '2K': self.settings['dwt_levels_2k'],
            '4K': self.settings['dwt_levels_4k'],
        }

        _, asset = asset
        if 'Probe' in asset and self.dcp.schema == 'SMPTE':
            levels = asset['Probe']['DecompositionLevels']
            resolution = asset['Probe']['Resolution']
            resolution_name = ''

            # asdcp-lib was not able to extract DecompositionLevels, this
            # probably means that the J2KCodingStyleDefault descriptor is not
            # present.
            # It is indeed listed as an optional field in ST 422, but
            # DCI Specification and RDD 52 seems to imply that it should be
            # present so dedicated checks could be added to validate the J2K
            # codestream.
            if levels == 0:
                return

            for k, v in six.iteritems(resolutions):
                if resolution in v:
                    resolution_name = k
                    break

            is_dci = resolution_name in levels_map
            if is_dci and levels_map[resolution_name] != levels:
                self.error(
                    "Picture must have {} wavelet transform levels, {}"
                    " found".format(levels_map[resolution_name], levels))

    def check_picture_cpl_max_bitrate(self, playlist, asset):
        """ Picture maximum bitrate DCI compliance.

            References:
                DCI HFR RP 2
                DCI DCSS (v1.3) 4.3.3
        """
        tolerance = self.settings['bitrate_tolerance']

        _, asset = asset
        if 'Probe' in asset:
            max_bitrate = asset['Probe']['MaxBitRate']
            dci_bitrate = self.get_picture_max_bitrate(playlist, asset)
            t_bitrate = dci_bitrate + tolerance

            if max_bitrate > t_bitrate:
                self.error(
                    "Exceed DCI maximum bitrate ({} Mb/s) : {} Mb/s".format(
                        t_bitrate, max_bitrate))

    def check_picture_cpl_avg_bitrate(self, playlist, asset):
        """ Picture average bitrate DCI compliance.

            References: N/A
        """
        margin = self.settings['average_bitrate_margin']

        _, asset = asset
        if 'Probe' in asset:
            avg_bitrate = asset['Probe']['AverageBitRate']
            dci_bitrate = self.get_picture_max_bitrate(playlist, asset)
            t_bitrate = dci_bitrate - (dci_bitrate * margin) / 100.0

            if avg_bitrate > t_bitrate:
                self.error(
                    "Exceed DCI safe average bitrate ({} Mb/s) "
                    ": {} Mb/s".format(t_bitrate, avg_bitrate))

    def check_picture_cpl_framerate(self, playlist, asset):
        """ Picture framerate DCI compliance.

            References:
                SMPTE ST 428-11:2013 5.1
                SMPTE ST 429-13:2009 7.2
        """
        _, asset = asset

        if 'Probe' in asset:
            resolution = asset['Probe']['Resolution']
            editrate = asset['EditRate']
            dimension = '3D' if asset['Stereoscopic'] else '2D'
            editrate_map = self.settings['editrates']

            if resolution in self.settings['resolutions']['2K']:
                if editrate not in editrate_map['2K'][dimension]:
                    self.error('Invalid EditRate {} for 2K {} content'
                        .format(editrate, dimension))
            elif resolution in self.settings['resolutions']['4K']:
                if editrate not in editrate_map['4K'][dimension]:
                    self.error('Invalid EditRate {} for 4K {} content'
                        .format(editrate, dimension))

    def check_picture_cpl_archival_framerate(self, playlist, asset):
        """ Picture archival framerate.

            References:
                SMPTE ST 428-21:2011 5
                FIAF D-Cinema Equipment Frequently Asked Questions (v1.1) 5
                https://www.fiafnet.org/images/tinyUpload/E-Resources/Commission-And-PIP-Resources/TC_resources/D-Cinema%20FAQs%20release%20FIAF%202012%20V1.1.pdf
        """
        _, asset = asset
        editrate = asset['EditRate']
        archival_editrates = self.settings['editrates_archival']

        for archival_editrate in archival_editrates:
            if compare_ratio(editrate, archival_editrate):
                self.error(
                    "Archival EditRate {} may not play safely on all hardware"
                    .format(editrate))

    def check_picture_cpl_hfr_framerate(self, playlist, asset):
        """ Picture HFR capable (Series II) framerate.

            References:
                IMAGO Frame rate support of Digital Cinema
                https://www.imago.org/index.php/technical/item/462-frame-rate-support-of-digital-cinema.html
        """
        _, asset = asset
        editrate = asset['EditRate']
        dimension = '3D' if asset['Stereoscopic'] else '2D'
        series2_map = self.settings['editrates_min_series2']

        if editrate >= series2_map[dimension]:
            self.error(
                "EditRate {} require an HFR capable projection server "
                "(Series II), may not play safely on all hardware".format(
                    editrate))

    def check_picture_cpl_editrate_framerate(self, playlist, asset):
        """ Picture editrate / framerate coherence check.

            References:
                SMPTE ST 429-7:2006 8.1.3
                SMPTE ST 429-10:2008 5.2
        """
        _, asset = asset
        editrate = asset['EditRate']
        framerate = asset['FrameRate']
        is_stereo = asset['Stereoscopic']

        if is_stereo and editrate * 2 != framerate:
            self.error("3D FrameRate must be double of EditRate")

        if not is_stereo and editrate != framerate:
            self.error("2D FrameRate must be equal to EditRate")
