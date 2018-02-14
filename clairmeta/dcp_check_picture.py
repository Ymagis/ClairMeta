# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six

from clairmeta.dcp_check import CheckerBase, CheckException
from clairmeta.dcp_utils import list_cpl_assets
from clairmeta.settings import DCP_SETTINGS


class Checker(CheckerBase):

    def __init__(self, dcp, profile):
        super(Checker, self).__init__(dcp, profile)
        self.settings = DCP_SETTINGS['picture']

    def run_checks(self):
        for source in self.dcp._list_cpl:

            asset_checks = self.find_check('picture_cpl')
            [self.run_check(
                check, source, asset, message="{} (Asset {})".format(
                    source['FileName'], asset[1].get('Path', asset[1]['Id'])))
             for asset in list_cpl_assets(source, filters='Picture')
             for check in asset_checks]

        return self.check_executions

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
        """ Picture resolution DCI compliance. """
        dci_resolutions = [
            self.settings['resolutions']['2K'] +
            self.settings['resolutions']['4K']
        ]

        _, asset = asset
        if 'Probe' in asset:
            resolution = asset['Probe']['Resolution']
            is_dci_res = any(
                [resolution in res for res in dci_resolutions])

            if not is_dci_res:
                raise CheckException("Picture have non-DCI Resolution")

    def check_picture_cpl_encoding(self, playlist, asset):
        """ Picture wavelet transform levels SMPTE compliance. """
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

            for k, v in six.iteritems(resolutions):
                if resolution in v:
                    resolution_name = k
                    break

            is_dci = resolution_name in levels_map
            if is_dci and levels_map[resolution_name] != levels:
                raise CheckException(
                    "Picture must have {} wavelet transform levels, {}"
                    " found".format(levels_map[resolution_name], levels))

    def check_picture_cpl_max_bitrate(self, playlist, asset):
        """ Picture maximum bitrate DCI compliance. """
        tolerance = self.settings['bitrate_tolerance']

        _, asset = asset
        if 'Probe' in asset:
            max_bitrate = asset['Probe']['MaxBitRate']
            dci_bitrate = self.get_picture_max_bitrate(playlist, asset)
            t_bitrate = dci_bitrate + tolerance

            if max_bitrate > t_bitrate:
                raise CheckException(
                    "Exceed DCI maximum bitrate ({} Mb/s) : {} Mb/s".format(
                        t_bitrate, max_bitrate))

    def check_picture_cpl_avg_bitrate(self, playlist, asset):
        """ Picture average bitrate DCI compliance. """
        margin = self.settings['average_bitrate_margin']

        _, asset = asset
        if 'Probe' in asset:
            avg_bitrate = asset['Probe']['AverageBitRate']
            dci_bitrate = self.get_picture_max_bitrate(playlist, asset)
            t_bitrate = dci_bitrate - (dci_bitrate * margin) / 100.0

            if avg_bitrate > t_bitrate:
                raise CheckException(
                    "Exceed DCI safe average bitrate ({} Mb/s) "
                    ": {} Mb/s".format(t_bitrate, avg_bitrate))

    def check_picture_cpl_framerate(self, playlist, asset):
        """ Picture framerate DCI / HFR check. """
        settings = DCP_SETTINGS['picture']
        editrate_stereo_map = {
            True: settings['min_stereo_high_editrate'],
            False: settings['min_mono_high_editrate']
        }

        _, asset = asset
        framerate = asset['FrameRate']
        is_hfr = asset['HighFrameRate']
        is_stereo = asset['Stereoscopic']

        if is_hfr and framerate < editrate_stereo_map[is_stereo]:
            raise CheckException(
                "Invalid HFR FrameRate, minimum is {} FPS".format(
                    editrate_stereo_map[is_stereo]))

        if not is_hfr and framerate > editrate_stereo_map[is_stereo]:
            raise CheckException(
                "Invalid DCI FrameRate, maximum is {} FPS".format(
                    editrate_stereo_map[is_stereo]))

    def check_picture_cpl_editrate_framerate(self, playlist, asset):
        """ Picture editrate / framerate coherence check. """
        _, asset = asset
        editrate = asset['EditRate']
        framerate = asset['FrameRate']
        is_stereo = asset['Stereoscopic']

        if is_stereo and editrate * 2 != framerate:
            raise CheckException("3D FrameRate must be double of EditRate")

        if not is_stereo and editrate != framerate:
            raise CheckException("2D FrameRate must be equal to EditRate")
