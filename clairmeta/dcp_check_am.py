# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os

from clairmeta.utils.uuid import check_uuid
from clairmeta.dcp_check import CheckerBase, CheckException
from clairmeta.dcp_check_utils import check_xml
from clairmeta.dcp_utils import list_am_assets


class Checker(CheckerBase):
    def __init__(self, dcp, profile):
        super(Checker, self).__init__(dcp, profile)

    def run_checks(self):
        for source in self.dcp._list_am:
            checks = self.find_check('am')
            [self.run_check(check, source, message=source['FileName'])
             for check in checks]

            asset_checks = self.find_check('assets_am')
            [self.run_check(
                check, source, asset, message="{} (Asset {})".format(
                    source['FileName'],
                    asset[2]['ChunkList']['Chunk']['Path']))
             for asset in list_am_assets(source)
             for check in asset_checks]

        return self.check_executions

    def check_am_xml(self, am):
        """ AssetMap XML syntax and structure check. """
        check_xml(
            am['FilePath'],
            am['Info']['AssetMap']['__xmlns__'],
            am['Info']['AssetMap']['Schema'],
            self.dcp.schema)

    def check_am_name(self, am):
        """ AssetMap file name respect DCP standard. """
        schema = am['Info']['AssetMap']['Schema']
        mandatory_name = {
            'Interop': 'ASSETMAP',
            'SMPTE': 'ASSETMAP.xml'
        }

        if mandatory_name[schema] != am['FileName']:
            raise CheckException(
                "{} Assetmap must be named {}, got {} instead".format(
                    schema, mandatory_name[schema], am['FileName'])
            )

    def check_assets_am_uuid(self, am, asset):
        """ AssetMap UUIDs validation. """
        uuid, _, _ = asset
        if not check_uuid(uuid):
            raise CheckException(
                "Invalid uuid found : {}".format(uuid))

    def check_assets_am_volindex(self, am, asset):
        """ AssetMap assets shall reference existing VolIndex. """
        _, _, asset = asset
        # Note : schema already check for positive integer
        asset_vol = asset['ChunkList']['Chunk'].get('VolumeIndex')
        if asset_vol and asset_vol > am['Info']['AssetMap']['VolumeCount']:
            raise CheckException(
                "Invalid VolIndex found : {}".format(asset_vol))

    def check_assets_am_path(self, am, asset):
        """ AssetMap assets path validation. """
        uuid, path, _ = asset

        if path == '':
            raise CheckException("Empty path for {}".format(uuid))

        if ' ' in path:
            raise CheckException("Space in path")

        if not os.path.isfile(os.path.join(self.dcp.path, path)):
            raise CheckException("Missing asset")

    def check_assets_am_size(self, am, asset):
        """ AssetMap assets size check. """
        _, path, asset = asset
        path = os.path.join(self.dcp.path, path)
        chunk = asset['ChunkList']['Chunk']

        if 'Length' not in chunk:
            return
        if os.path.isfile(path):
            actual_size = os.path.getsize(path)
            offset = chunk.get('Offset', 0)
            length = chunk['Length']

            if offset >= actual_size:
                raise CheckException("Invalid offset value ()".format(offset))
            if length != actual_size:
                raise CheckException("Invalid size value, expected {} but got "
                                     "{}".format(length, actual_size))
