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

            asset_checks = self.find_check('atmos_cpl')
            [self.run_check(
                check, source, asset, message="{} (Asset {})".format(
                    source['FileName'], asset[1].get('Path', asset[1]['Id'])))
             for asset in list_cpl_assets(
                source, filters='AuxData', required_keys=['Probe'])
             if asset[1]['Schema'] == 'Atmos'
             for check in asset_checks]

        return self.check_executions

    def check_atmos_cpl_essence_encoding(self, playlist, asset):
        """ Atmos encoding. """
        _, asset = asset
        ul = DCP_SETTINGS['atmos']['smpte_ul']
        cpl_ul = asset.get('DataType', '').replace('urn:smpte:ul:', '').strip()
        mxf_ul = asset['Probe'].get('DataEssenceCoding', '')

        if not cpl_ul:
            raise CheckException("Missing Atmos DataType tag (CPL/AuxData")
        elif not mxf_ul:
            raise CheckException("Missing Atmos Essence Coding UL (MXF)")

        cpl_ul, mxf_ul = cpl_ul.lower(), mxf_ul.lower()
        if cpl_ul != mxf_ul:
            raise CheckException(
                "Incoherent Atmos Data Essence Coding, CPL {} / MXF {}"
                .format(cpl_ul, mxf_ul))
        elif mxf_ul != ul:
            raise CheckException(
                "Unknown Atmos Data Essence Coding, expecting {} but got {}"
                .format(ul, mxf_ul))

    def check_atmos_cpl_channels(self, playlist, asset):
        """ Atmos maximum channels count.

            This field will be optional, cf. 429-18.
        """
        _, asset = asset
        max_atmos = DCP_SETTINGS['atmos']['max_channel_count']
        max_cc = asset['Probe'].get('MaxChannelCount')

        if not max_cc:
            raise CheckException("Missing MaxChannelCount field")
        elif max_cc > max_atmos:
            raise CheckException(
                "Invalid Atmos MaxChannelCount, got {} but maximum is {}"
                .format(max_cc, max_atmos))

    def check_atmos_cpl_objects(self, playlist, asset):
        """ Atmos maximum objects count.

            This field will be optional, cf. 429-18.
        """
        _, asset = asset
        max_atmos = DCP_SETTINGS['atmos']['max_object_count']
        max_obj = asset['Probe'].get('MaxObjectCount')

        if not max_obj:
            raise CheckException("Missing MaxObjectCount field")
        elif max_obj > max_atmos:
            raise CheckException(
                "Invalid Atmos MaxObjectCount, got {} but maximum is {}"
                .format(max_obj, max_atmos))
