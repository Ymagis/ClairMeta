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
            asset_stack = [source['FileName']]

            checks = self.find_check('am')
            [self.run_check(check, source, stack=asset_stack)
             for check in checks]

            asset_checks = self.find_check('assets_am')
            [self.run_check(
                check, source, asset,
                stack=asset_stack + [asset[2]['ChunkList']['Chunk']['Path']])
             for asset in list_am_assets(source)
             for check in asset_checks]

        return self.checks

    def check_am_xml(self, am):
        """ AssetMap XML syntax and structure check.

            References: N/A
        """
        check_xml(
            am['FilePath'],
            am['Info']['AssetMap']['__xmlns__'],
            am['Info']['AssetMap']['Schema'],
            self.dcp.schema)

    def check_am_name(self, am):
        """ AssetMap file name respect DCP standard.

            References: N/A
        """
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

    def check_am_empty_text_fields(self, am):
        """ AssetMap empty text fields check.

            This check for empty 'Creator', 'Issuer' or 'AnnotationText' text
            fields. While not invalid per specification, it appears other
            checking tools might trigger error / warning here so we provide
            this to align with other check reports.

            References:
                mpeg_ii_am_spec.doc (v3.4) 4.1.2, 4.1.5, 4.1.6
                SMPTE ST 429-9:2014 5.2, 5.3, 5.6
        """
        fields = ['Creator', 'Issuer', 'AnnotationText']
        empty_fields = []

        for f in fields:
            am_f = am['Info']['AssetMap'].get(f)
            if am_f == '':
                empty_fields.append(f)

        if empty_fields:
            raise CheckException("Empty {} field(s)".format(
                ", ".join(empty_fields)))

    def check_assets_am_uuid(self, am, asset):
        """ AssetMap UUIDs validation.

            References:
                SMPTE ST 429-9:2014 6.1
        """
        uuid, _, _ = asset
        if not check_uuid(uuid):
            raise CheckException(
                "Invalid uuid found : {}".format(uuid, RFC4122_RE))

    def check_assets_am_volindex(self, am, asset):
        """ AssetMap assets shall reference existing VolIndex.

            References:
                SMPTE ST 429-9:2014
        """
        _, _, asset = asset
        # Note : schema already check for positive integer
        asset_vol = asset['ChunkList']['Chunk'].get('VolumeIndex')
        if asset_vol and asset_vol > am['Info']['AssetMap']['VolumeCount']:
            raise CheckException(
                "Invalid VolIndex found : {}".format(asset_vol))

    def check_assets_am_volindex_one(self, am, asset):
        """ AssetMap assets VolIndex shall be one or absent.

            References:
                SMPTE ST 429-9:2014 7.2
        """
        _, _, asset = asset
        asset_vol = asset['ChunkList']['Chunk'].get('VolumeIndex')
        if asset_vol and asset_vol != 1:
            raise CheckException(
                "VolIndex is now deprecated and shall always be 1, got {}"
                .format(asset_vol))

    def check_assets_am_path(self, am, asset):
        """ AssetMap assets path validation.

            References:
                SMPTE ST 429-9:2014 7.1
        """
        uuid, path, _ = asset

        if path == '':
            raise CheckException("Empty path for {}".format(uuid))

        if ' ' in path:
            raise CheckException("Space in path")

        if not os.path.isfile(os.path.join(self.dcp.path, path)):
            raise CheckException("Missing asset")

    def check_assets_am_size(self, am, asset):
        """ AssetMap assets size check.

            References:
                SMPTE ST 429-9:2014 7.4
        """
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
