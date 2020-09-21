# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

from clairmeta.dcp_check import CheckerBase, CheckException
from clairmeta.dcp_utils import list_cpl_assets
from clairmeta.settings import DCP_SETTINGS


class Checker(CheckerBase):

    def __init__(self, dcp, profile):
        super(Checker, self).__init__(dcp, profile)

    def run_checks(self):
        for source in self.dcp._list_cpl:
            asset_checks = self.find_check('sound_cpl')
            [self.run_check(
                check, source, asset,
                stack=[
                    source['FileName'],
                    asset[1].get('Path') or asset[1]['Id']])
             for asset in list_cpl_assets(
                source, filters='Sound', required_keys=['Probe'])
             for check in asset_checks]

        return self.checks

    def check_sound_cpl_channels(self, playlist, asset):
        """ Sound max channels count.

            Reference :
                SMPTE 428-2-2006 3.3
        """
        channels = DCP_SETTINGS['sound']['max_channel_count']
        _, asset = asset
        cc = asset['Probe']['ChannelCount']

        if cc > channels:
            raise CheckException(
                "Invalid Sound ChannelCount, should be less than {} but got {}"
                "".format(channels, cc))

    def check_sound_cpl_channels_odd(self, playlist, asset):
        """ Sound channels count must be an even number.

            Extract fom ISDCF recommandation : Note 1. Not all channels need to
            be present in a given DCP. For instance, only the first 8 channels
            should be used when delivering 5.1 + HI/VI content. In all cases,
            an even number of channels shall be used.

            Reference :
                http://isdcf.com/papers/ISDCF-Doc4-Audio-channel-recommendations.pdf
        """
        _, asset = asset
        cc = asset['Probe']['ChannelCount']

        if cc % 2 != 0:
            raise CheckException(
                "Invalid Sound ChannelCount, should be an even number, got {}"
                "".format(cc))

    def check_sound_cpl_format(self, playlist, asset):
        """ Sound channels count coherence with format.

            Reference :
                SMPTE 429-2-2013 A.1.2
        """
        configurations = DCP_SETTINGS['sound']['configuration_channels']
        _, asset = asset
        cf = asset['Probe']['ChannelFormat']
        cc = asset['Probe']['ChannelCount']

        if cf in configurations:
            label, min_cc, max_cc = configurations[cf]
            if label and cc < min_cc or cc > max_cc:
                raise CheckException(
                    "Invalid Sound ChannelCount, {} require between {} and {} "
                    "channels, got {}".format(label, min_cc, max_cc, cc))

    def check_sound_cpl_sampling(self, playlist, asset):
        """ Sound sampling rate check.

            Reference :
                SMPTE 428-2-2006 3.2
        """
        rates = DCP_SETTINGS['sound']['sampling_rate']
        _, asset = asset
        sr = asset['Probe']['AudioSamplingRate']

        if sr not in rates:
            raise CheckException(
                "Invalid Sound SamplingRate, expected {} but got {}".format(
                    rates, sr))

    def check_sound_cpl_quantization(self, playlist, asset):
        """ Sound quantization check.

            Reference :
                SMPTE 428-2-2006 3.1
        """
        bitdepth = DCP_SETTINGS['sound']['quantization']
        _, asset = asset
        depth = asset['Probe']['QuantizationBits']

        if depth != bitdepth:
            raise CheckException(
                "Invalid Sound Quantization, expected {} but got {}".format(
                    bitdepth, depth))

    def check_sound_cpl_blockalign(self, playlist, asset):
        """ Sound block alignement check.

            Reference : N/A
        """
        align = DCP_SETTINGS['sound']['quantization'] / 8
        _, asset = asset
        al = asset['Probe']['BlockAlign']
        cc = asset['Probe']['ChannelCount']

        if al != cc * align:
            raise CheckException(
                "Invalid Sound BlockAlign, expected {} but got {} (it should "
                "be ChannelCount x 3)".format(cc * align, al))
