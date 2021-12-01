# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import re

from clairmeta.utils.uuid import check_uuid, RFC4122_RE
from clairmeta.dcp_check import CheckerBase
from clairmeta.dcp_check_utils import check_xml
from clairmeta.dcp_utils import list_am_assets


class Checker(CheckerBase):
    def __init__(self, dcp):
        super(Checker, self).__init__(dcp)

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
            self,
            am['FilePath'],
            am['Info']['AssetMap']['__xmlns__'],
            am['Info']['AssetMap']['Schema'],
            self.dcp.schema)

    def check_am_volume_count(self, am):
        """ The VolumeCount element shall be 1

            References:
                SMPTE ST 429-9:2014 5.4

        """
        volume_count = am['Info']['AssetMap']['VolumeCount']
        if volume_count != 1:
            self.error("Invalid VolumeCount value: {}".format(volume_count))

    def check_am_name(self, am):
        """ AssetMap file name respect DCP standard.

            References:
                mpeg_ii_am_spec.doc (v3.4) 6.2
                https://interop-docs.cinepedia.com/Document_Release_2.0/mpeg_ii_am_spec.pdf
                SMPTE ST 429-9:2014 A.4

        """
        schema = am['Info']['AssetMap']['Schema']
        mandatory_name = {
            'Interop': 'ASSETMAP',
            'SMPTE': 'ASSETMAP.xml'
        }

        if mandatory_name[schema] != am['FileName']:
            self.error(
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
        madatory_fields = ['Creator']
        empty_fields = []
        missing_fields = []

        for f in fields:
            am_f = am['Info']['AssetMap'].get(f)
            if am_f == '':
                empty_fields.append(f)
            elif am_f is None and f in madatory_fields:
                missing_fields.append(f)

        if empty_fields:
            self.error("Empty {} field(s)".format(", ".join(empty_fields)))
        if missing_fields:
            self.error("Missing {} field(s)".format(
                ", ".join(missing_fields)), "missing")

    def check_assets_am_uuid(self, am, asset):
        """ AssetMap UUIDs validation.

            References:
                mpeg_ii_am_spec.doc (v3.4) 4.1.1
                https://interop-docs.cinepedia.com/Document_Release_2.0/mpeg_ii_am_spec.pdf
                SMPTE ST 429-9:2014 5.1

            ST 429-9 references the final version of RFC 4122 (July 2005)
            whereas mpeg_ii_am_spec.doc references Draft 03 (January 2004).

            Diff here:
            https://tools.ietf.org/rfcdiff?url1=draft-mealling-uuid-urn-03.txt&url2=rfc4122.txt

        """
        uuid, _, _ = asset
        if not check_uuid(uuid):
            self.error("Invalid uuid found : {}".format(uuid))

    def check_assets_am_volindex_one(self, am, asset):
        """ AssetMap Asset VolumeIndex element shall be 1 or absent.

            References:
                SMPTE ST 429-9:2014 7.2
        """
        _, _, asset = asset
        asset_vol = asset['ChunkList']['Chunk'].get('VolumeIndex')
        if asset_vol and asset_vol != 1:
            self.error(
                "VolIndex is now deprecated and shall always be 1, got {}"
                .format(asset_vol))

    def check_assets_am_path(self, am, asset):
        """ AssetMap assets path validation.

            References:
                mpeg_ii_am_spec.doc (v3.4) 4.3.1, 5.3, 6.4
                https://interop-docs.cinepedia.com/Document_Release_2.0/mpeg_ii_am_spec.pdf
                SMPTE ST 429-9:2014 7.1, A.2

        """
        _, path, _ = asset

        path_segments = list(filter(None, path.split('/')))
        path_segments_count = len(path_segments)
        if path_segments_count > 10:
            self.error(">10 path segments: {}".format(path_segments_count))

        max_path_seg = max(map(len, path_segments))
        if max_path_seg > 100:
            self.error("Path segment >100 characters: {}".format(max_path_seg))

        if len(path) > 100:
            self.error("Path >100 characters: {}".format(len(path)))

        path_invalid_chars = re.findall(r'[^a-zA-Z0-9._/-]', path)
        if path_invalid_chars:
            unique_char_str = ", ".join(sorted(set(path_invalid_chars)))
            self.error("Invalid characters in path: {}".format(unique_char_str))

        if path[0] == '/':
            self.error("Path is not relative")

        rel_path = os.path.relpath(
            os.path.join(self.dcp.path, path), self.dcp.path)
        if rel_path.startswith("../"):
            self.error("Path points outside of DCP root")

        if not os.path.isfile(os.path.join(self.dcp.path, path)):
            self.error("Missing asset file: {}".format(os.path.basename(path)))

    def check_assets_am_offset(self, am, asset):
        """ AssetMap Chunk Offset check

            References:
                SMPTE ST 429-9:2014 7.3
        """
        _, _, asset = asset
        chunk = asset['ChunkList']['Chunk']

        if 'Offset' not in chunk:
            return

        offset = chunk['Offset']
        if offset != 0:
            self.error("Invalid offset value {}".format(offset))

    def check_assets_am_size(self, am, asset):
        """ AssetMap assets size check.

            References:
                mpeg_ii_am_spec.doc (v3.4) 4.3.4
                https://interop-docs.cinepedia.com/Document_Release_2.0/mpeg_ii_am_spec.pdf
                SMPTE ST 429-9:2014 7.4

        """
        _, path, asset = asset
        path = os.path.join(self.dcp.path, path)
        chunk = asset['ChunkList']['Chunk']

        if 'Length' not in chunk:
            return
        if os.path.isfile(path):
            actual_size = os.path.getsize(path)
            length = chunk['Length']

            if length != actual_size:
                self.error("Invalid size value, expected {} but got "
                           "{}".format(length, actual_size))
