# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six

from clairmeta.dcp_check import CheckerBase, CheckException
from clairmeta.dcp_utils import list_cpl_assets
from clairmeta.settings import DCP_SETTINGS


class Checker(CheckerBase):
    def __init__(self, dcp, profile):
        super(Checker, self).__init__(dcp, profile)

    def run_checks(self):
        for source in self.dcp._list_cpl:

            asset_checks = self.find_check('picture_cpl')
            [self.run_check(
                check, source, asset, message="{} (Asset {})".format(
                    source['FileName'], asset[1].get('Path', asset[1]['Id'])))
             for asset in list_cpl_assets(source, filters='Picture')
             for check in asset_checks]

        return self.check_executions

    def get_picture_max_bitrate(self, asset):
        settings = DCP_SETTINGS['picture']
        bitrate_hfr_map = {
            True: settings['max_hfr_bitrate'],
            False: settings['max_bitrate']
        }

        is_hfr = asset.get('HighFrameRate', False)
        dci_bitrate = bitrate_hfr_map[is_hfr]
        return dci_bitrate

    def check_picture_cpl_resolution(self, playlist, asset):
        dci_resolutions = [
            DCP_SETTINGS['picture']['resolutions']['2K'],
            DCP_SETTINGS['picture']['resolutions']['4K']
        ]

        _, asset = asset
        if 'Probe' in asset:
            resolution = asset['Probe']['Resolution']
            is_dci_res = any([resolution in res for res in dci_resolutions])

            if not is_dci_res:
                raise CheckException("Picture have non-DCI Resolution")

    def check_picture_cpl_encoding(self, playlist, asset):
        """ SMPTE 429-2
            There shall be 5 wavelet transform levels for 2K picture essence.
            There shall be 6 wavelet transform levels for 4K picture essence.
        """
        resolutions = DCP_SETTINGS['picture']['resolutions']
        levels_map = {
            '2K': DCP_SETTINGS['picture']['dwt_levels_2k'],
            '4K': DCP_SETTINGS['picture']['dwt_levels_4k'],
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
        tolerance = DCP_SETTINGS['picture']['bitrate_tolerance']

        _, asset = asset
        if 'Probe' in asset:
            max_bitrate = asset['Probe']['MaxBitRate']
            dci_bitrate = self.get_picture_max_bitrate(asset)
            t_bitrate = dci_bitrate + tolerance

            if max_bitrate > t_bitrate:
                raise CheckException(
                    "Exceed DCI bitrate ({} Mb/s) : {} Mb/s".format(
                        t_bitrate, max_bitrate))

    def check_picture_cpl_avg_bitrate(self, playlist, asset):
        margin = DCP_SETTINGS['picture']['average_bitrate_margin']

        _, asset = asset
        if 'Probe' in asset:
            avg_bitrate = asset['Probe']['AverageBitRate']
            dci_bitrate = self.get_picture_max_bitrate(asset)
            t_bitrate = dci_bitrate - (dci_bitrate * margin) / 100.0

            if avg_bitrate > t_bitrate:
                raise CheckException(
                    "Exceed DCI safe average bitrate ({} Mb/s) "
                    ": {} Mb/s".format(t_bitrate, avg_bitrate))

    def check_picture_cpl_framerate(self, playlist, asset):
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
        _, asset = asset
        editrate = asset['EditRate']
        framerate = asset['FrameRate']
        is_stereo = asset['Stereoscopic']

        if is_stereo and editrate * 2 != framerate:
            raise CheckException("3D FrameRate must be double of EditRate")

        if not is_stereo and editrate != framerate:
            raise CheckException("2D FrameRate must be equal to EditRate")
