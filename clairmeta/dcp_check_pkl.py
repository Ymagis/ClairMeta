# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import re
import magic

from clairmeta.utils.file import shaone_b64
from clairmeta.dcp_check import CheckerBase, CheckException
from clairmeta.dcp_check_utils import check_xml, check_issuedate
from clairmeta.dcp_utils import list_pkl_assets


class Checker(CheckerBase):

    def __init__(self, dcp, profile):
        super(Checker, self).__init__(dcp, profile)

    def run_checks(self):
        # Accumulate hash by UUID, useful for multi PKL package
        self.hash_map = {}

        for source in self.dcp._list_pkl:
            checks = self.find_check('pkl')
            [self.run_check(check, source, message=source['FileName'])
             for check in checks]

            asset_checks = self.find_check('assets_pkl')
            [self.run_check(
                check, source, asset, message="{} (Asset {})".format(
                    source['FileName'], asset[2].get('Path', asset[2]['Id'])))
             for asset in list_pkl_assets(source)
             for check in asset_checks]

        return self.check_executions

    def check_pkl_xml(self, pkl):
        """ PKL XML syntax and structure check. """
        pkl_node = pkl['Info']['PackingList']
        check_xml(
            pkl['FilePath'],
            pkl_node['__xmlns__'],
            pkl_node['Schema'],
            self.dcp.schema)

    def check_pkl_issuedate(self, pkl):
        """ PKL Issue Date validation. """
        check_issuedate(pkl['Info']['PackingList']['IssueDate'])

    def check_assets_pkl_referenced_by_assetamp(self, pkl, asset):
        """ PKL assets shall be present in AssetMap. """
        uuid, _, _ = asset
        # Note : dcp._list_asset is directly extracted from Assetmap
        if uuid not in self.dcp._list_asset.keys():
            raise CheckException("Not present in Assetmap")

    # TODO : MIME Type might not be worth checking (too versatile)
    # def check_assets_pkl_type(self, pkl, asset):
    #     """ PKL assets MimeType check. """
    #     _, path, asset = asset
    #     mime_type = asset['Type']
    #
    #     if mime_type == "":
    #         raise CheckException("Empty Type")
    #     if not path or not os.path.exists(path):
    #         return
    #
    #     mime_type = mime_type.split(';')[0]
    #     mime_type = re.sub(r'x-\w+-', '', mime_type)
    #     actual_type = magic.from_file(path, mime=True)
    #     actual_type = re.sub(r'x-\w+-', '', actual_type)
    #
    #     if actual_type != mime_type:
    #         raise CheckException(
    #             "Mime Type mismatch, expected (from PKL) {} but found {}"
    #             "".format(mime_type, actual_type))

    def check_assets_pkl_size(self, pkl, asset):
        """ PKL assets size check. """
        _, path, asset = asset
        if not path or not os.path.exists(path):
            return

        asset_size = asset['Size']
        actual_size = os.path.getsize(path)

        if actual_size != asset_size:
            raise CheckException(
                "Invalid size, expected {} but got {}".format(
                    asset_size, actual_size))

    def check_assets_pkl_hash(self, pkl, asset):
        """ PKL assets hash check. """
        _, path, asset = asset
        if not path or not os.path.exists(path):
            return

        asset_hash = asset['Hash']
        asset_id = asset['Id']
        if asset_id not in self.hash_map:
            self.hash_map[asset_id] = shaone_b64(path, self.hash_callback)

        if self.hash_map[asset_id] != asset_hash:
            raise CheckException(
                "Corrupt file, expected hash {} but got {}".format(
                    asset_hash, self.hash_map[asset_id]))
