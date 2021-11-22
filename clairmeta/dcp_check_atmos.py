# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

from clairmeta.dcp_check import CheckerBase
from clairmeta.dcp_utils import list_cpl_assets
from clairmeta.settings import DCP_SETTINGS


class Checker(CheckerBase):

    def __init__(self, dcp):
        super(Checker, self).__init__(dcp)

    def run_checks(self):
        for source in self.dcp._list_cpl:
            asset_checks = self.find_check('atmos_cpl')
            [self.run_check(check, source, asset,
             stack=[
                 source['FileName'],
                 asset[1].get('Path') or asset[1]['Id']])
             for asset in list_cpl_assets(
                source, filters='AuxData', required_keys=['Probe'])
             if asset[1]['Schema'] == 'Atmos'
             for check in asset_checks]

        return self.checks

    def check_atmos_cpl_essence_encoding(self, playlist, asset):
        """ Atmos data essence coding universal label.

            References:
                SMPTE ST 429-18:2019 11
        """
        _, asset = asset
        ul = DCP_SETTINGS['atmos']['smpte_ul']
        cpl_ul = asset.get('DataType', '').replace('urn:smpte:ul:', '').strip()
        mxf_ul = asset['Probe'].get('DataEssenceCoding', '')

        if not cpl_ul:
            self.fatal_error(
                "Missing Atmos DataType tag (CPL/AuxData)",
                "missing_cpl")
        elif not mxf_ul:
            self.fatal_error(
                "Missing Atmos Essence Coding UL (MXF)",
                "missing_mxf")

        cpl_ul, mxf_ul = cpl_ul.lower(), mxf_ul.lower()
        if cpl_ul != mxf_ul:
            self.error(
                "Incoherent Atmos Data Essence Coding, CPL {} / MXF {}"
                .format(cpl_ul, mxf_ul),
                "incoherent")
        elif mxf_ul != ul:
            self.error(
                "Unknown Atmos Data Essence Coding, expecting {} but got {}"
                .format(ul, mxf_ul),
                "unknown")

    def check_atmos_cpl_channels(self, playlist, asset):
        """ Atmos maximum channels count.

            This field will be optional (429-18).

            References:
                Dolby S14/26858/27819
                https://web.archive.org/web/20190407130138/https://www.dolby.com/us/en/technologies/dolby-atmos/dolby-atmos-next-generation-audio-for-cinema-white-paper.pdf
                SMPTE ST 429-18:2019 12 Table 4
        """
        _, asset = asset
        max_atmos = DCP_SETTINGS['atmos']['max_channel_count']
        max_cc = asset['Probe'].get('MaxChannelCount')

        if not max_cc:
            self.error(
                "Missing MaxChannelCount field",
                "missing")
        elif max_cc > max_atmos:
            self.error(
                "Invalid Atmos MaxChannelCount, got {} but maximum is {}"
                .format(max_cc, max_atmos),
                "invalid")

    def check_atmos_cpl_objects(self, playlist, asset):
        """ Atmos maximum objects count.

            This field will be optional (429-18).

            References:
                Dolby S14/26858/27819
                https://web.archive.org/web/20190407130138/https://www.dolby.com/us/en/technologies/dolby-atmos/dolby-atmos-next-generation-audio-for-cinema-white-paper.pdf
                SMPTE ST 429-18:2019 12 Table 4
        """
        _, asset = asset
        max_atmos = DCP_SETTINGS['atmos']['max_object_count']
        max_obj = asset['Probe'].get('MaxObjectCount')

        if not max_obj:
            self.error(
                "Missing MaxObjectCount field",
                "missing")
        elif max_obj > max_atmos:
            self.error(
                "Invalid Atmos MaxObjectCount, got {} but maximum is {}"
                .format(max_obj, max_atmos),
                "invalid")
