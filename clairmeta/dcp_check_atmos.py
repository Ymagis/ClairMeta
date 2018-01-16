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

    def check_atmos_cpl_channels(self, playlist, asset):
        """ Atmos maximum channels count. """
        _, asset = asset
        max_atmos = DCP_SETTINGS['atmos']['max_channel_count']
        max_cc = asset['Probe']['MaxChannelCount']

        if max_cc > max_atmos:
            raise CheckException(
                "Invalid Atmos MaxChannelCount, got {} but maximum is {}"
                .format(max_cc, max_atmos))

    def check_atmos_cpl_objects(self, playlist, asset):
        """ Atmos maximum objects count. """
        _, asset = asset
        max_atmos = DCP_SETTINGS['atmos']['max_object_count']
        max_obj = asset['Probe']['MaxObjectCount']

        if max_obj > max_atmos:
            raise CheckException(
                "Invalid Atmos MaxObjectCount, got {} but maximum is {}"
                .format(max_obj, max_atmos))
