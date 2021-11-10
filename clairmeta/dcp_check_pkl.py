# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os

from clairmeta.utils.file import shaone_b64
from clairmeta.dcp_check import CheckerBase
from clairmeta.dcp_check_utils import check_xml, check_issuedate
from clairmeta.dcp_utils import list_pkl_assets


class Checker(CheckerBase):

    def __init__(self, dcp):
        super(Checker, self).__init__(dcp)

    def run_checks(self):
        # Accumulate hash by UUID, useful for multi PKL package
        self.hash_map = {}

        for source in self.dcp._list_pkl:
            asset_stack = [source['FileName']]

            checks = self.find_check('pkl')
            [self.run_check(check, source, stack=asset_stack)
             for check in checks]

            asset_checks = self.find_check('assets_pkl')
            [self.run_check(check, source, asset,
             stack=asset_stack + [asset[2].get('Path', asset[2]['Id'])])
             for asset in list_pkl_assets(source)
             for check in asset_checks]

        return self.checks

    def check_pkl_xml(self, pkl):
        """ PKL XML syntax and structure check. """
        pkl_node = pkl['Info']['PackingList']
        check_xml(
            self,
            pkl['FilePath'],
            pkl_node['__xmlns__'],
            pkl_node['Schema'],
            self.dcp.schema)

    def check_pkl_empty_text_fields(self, am):
        """ PKL empty text fields check.

            References: N/A
        """
        fields = ['Creator', 'Issuer', 'AnnotationText']
        madatory_fields = ['Creator']
        empty_fields = []
        missing_fields = []

        for f in fields:
            am_f = am['Info']['PackingList'].get(f)
            if am_f == '':
                empty_fields.append(f)
            elif am_f is None and f in madatory_fields:
                missing_fields.append(f)

        if empty_fields:
            self.error("Empty {} field(s)".format( ", ".join(empty_fields)))
        if missing_fields:
            self.error("Missing {} field(s)".format(
                ", ".join(missing_fields)), "missing")

    def check_pkl_issuedate(self, pkl):
        """ PKL Issue Date validation.

            References: N/A
        """
        check_issuedate(self, pkl['Info']['PackingList']['IssueDate'])

    def check_assets_pkl_referenced_by_assetamp(self, pkl, asset):
        """ PKL assets shall be present in AssetMap.

            References: N/A
        """
        uuid, _, _ = asset
        # Note : dcp._list_asset is directly extracted from Assetmap
        if uuid not in self.dcp._list_asset.keys():
            self.error("Not present in Assetmap")

    def check_assets_pkl_size(self, pkl, asset):
        """ PKL assets size check.

            References:
                SMPTE ST 429-8:2007 6.4
        """
        _, path, asset = asset
        if not path or not os.path.exists(path):
            return

        asset_size = asset['Size']
        actual_size = os.path.getsize(path)

        if actual_size != asset_size:
            self.error("Invalid size, expected {} but got {}".format(
                asset_size, actual_size))

    def check_assets_pkl_hash(self, pkl, asset):
        """ PKL assets hash check.

            References:
                SMPTE ST 429-8:2007 6.3
        """
        _, path, asset = asset
        if not path or not os.path.exists(path):
            return

        asset_hash = asset['Hash']
        asset_id = asset['Id']

        if asset_id not in self.hash_map:
            self.hash_map[asset_id] = shaone_b64(path, self.hash_callback)

        if self.hash_map[asset_id] != asset_hash:
            self.error("Corrupt file, expected hash {} but got {}".format(
                asset_hash, self.hash_map[asset_id]))
