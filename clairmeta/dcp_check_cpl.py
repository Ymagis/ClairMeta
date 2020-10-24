# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

from __future__ import unicode_literals

import six
import operator
from clairmeta.utils.sys import all_keys_in_dict
from clairmeta.utils.uuid import check_uuid, extract_uuid, RFC4122_RE
from clairmeta.utils.time import compare_ratio
from clairmeta.dcp_check import CheckerBase, CheckException
from clairmeta.dcp_check_utils import check_xml, check_issuedate, compare_uuid
from clairmeta.dcp_utils import list_cpl_assets, get_type_for_asset


class Checker(CheckerBase):
    def __init__(self, dcp, profile):
        super(Checker, self).__init__(dcp, profile)

        self.mxf_schema_map = {
            'Interop': 'MXFInterop',
            'SMPTE': 'SMPTE',
        }

    def run_checks(self):
        for source in self.dcp._list_cpl:
            asset_stack = [source['FileName']]

            checks = self.find_check('cpl')
            [self.run_check(check, source, stack=asset_stack)
             for check in checks]

            asset_checks = self.find_check('assets_cpl')
            [self.run_check(check, source, asset,
             stack=asset_stack + [
                 asset[1].get('Path') or asset[1]['Id']])
             for asset in list_cpl_assets(source)
             for check in asset_checks]

        return self.checks

    def metadata_cmp_pair(
        self,
        playlist,
        metadata,
        type_a,
        type_b,
        cmp=operator.eq,
        message=""
    ):
        for reel in playlist['Info']['CompositionPlaylist']['ReelList']:
            metadatas = {
                k: v[metadata] for k, v in six.iteritems(reel['Assets'])
                if v.get(metadata) and k in [type_a, type_b]
            }

            vals = list(metadatas.values())
            if len(vals) == 2 and not cmp(vals[0], vals[1]):
                what = "{} / {} {} mismatch for Reel {}".format(
                        type_a, type_b, metadata, reel['Position'])
                if message:
                    what += ", {}".format(message)

                raise CheckException(what)

    def check_cpl_xml(self, playlist):
        """ CPL XML syntax and structure check.

            Reference : N/A
        """
        cpl = playlist['Info']['CompositionPlaylist']
        check_xml(
            playlist['FilePath'],
            cpl['__xmlns__'],
            cpl['Schema'],
            self.dcp.schema)

    def check_cpl_id_rfc4122(self, playlist):
        """ CPL UUID RFC4122 compliance.

            Reference :
                SMPTE 429-7-2006 6.1
        """
        cpl = playlist['Info']['CompositionPlaylist']
        uuid = cpl['Id']

        if not check_uuid(uuid, RFC4122_RE):
            raise CheckException("CPL ID invalid (RFC 4122) : {}".format(uuid))

    def check_cpl_contenttitle_annotationtext_match(self, playlist):
        """ CPL ContentTitleText and AnnotationText shall match.

            Reference : N/A
        """
        cpl_node = playlist['Info']['CompositionPlaylist']
        ct = cpl_node['ContentTitleText']
        at = cpl_node.get('AnnotationText')
        if at and at != ct:
            raise CheckException("CPL ContentTitleText / AnnotationText "
                                 "mismatch : {} / {}".format(ct, at))

    def check_cpl_contenttitle_pklannotationtext_match(self, playlist):
        """ CPL ContentTitleText and PKL AnnotationText shall match.

            Reference : N/A
        """
        cpl_node = playlist['Info']['CompositionPlaylist']
        ct = cpl_node['ContentTitleText']
        cpl_pkl = [
            pkl for pkl in self.dcp._list_pkl
            if pkl['Info']['PackingList']['Id'] == cpl_node.get('PKLId')]

        if not cpl_pkl:
            return

        pkl = cpl_pkl[0]
        at = pkl['Info']['PackingList'].get('AnnotationText')
        is_multi_cpl = len(self.dcp.list_cpl) > 1

        if is_multi_cpl and at and not ct.startswith(at):
            raise CheckException(
                "Multi CPLs package shall use a common denominator of all CPL "
                "titles as the PKL AnnotationText : {} / {}".format(ct, at))
        elif at and at != ct:
            raise CheckException(
                "CPL ContentTitleText / PKL "
                "AnnotationText mismatch : {} / {}".format(ct, at))

    def check_cpl_empty_text_fields(self, am):
        """ CPL empty text fields check.

            Reference : N/A
        """
        fields = ['Creator', 'Issuer', 'AnnotationText']
        empty_fields = []

        for f in fields:
            am_f = am['Info']['CompositionPlaylist'].get(f)
            if am_f == '':
                empty_fields.append(f)

        if empty_fields:
            raise CheckException("Empty {} field(s)".format(
                ", ".join(empty_fields)))

    def check_cpl_issuedate(self, playlist):
        """ CPL Issue Date validation.

            Reference :
                SMPTE 429-7-2006 6.4
        """
        cpl = playlist['Info']['CompositionPlaylist']
        check_issuedate(cpl['IssueDate'])

    def check_cpl_referenced_by_pkl(self, playlist):
        """ CPL shall be present in PKL.

            Reference : N/A
        """
        cpl = playlist['Info']['CompositionPlaylist']
        pkl_id = cpl.get('PKLId')
        if not pkl_id:
            raise CheckException("CPL is not referenced in any PKL")

    def check_cpl_reel_coherence(self, playlist):
        """ CPL reel attributes shall be coherents across all reels.

            Reference :
                SMPTE 429-2-2013 8.7
        """
        cpl = playlist['Info']['CompositionPlaylist']

        coherence_keys = [
            'EditRate',
            'FrameRate',
            'HighFrameRate',
            'ScreenAspectRatio',
            'Stereoscopic',
            'Resolution',
            'DecompositionLevels',
            'Precincts',
            'ChannelCount',
            'ChannelFormat',
            'ChannelConfiguration',
            'SoundLanguage',
        ]

        errors = []
        for k in coherence_keys:
            if cpl[k] == "Mixed":
                errors.append("{} is not coherent for all reels".format(k))
        if errors:
            raise CheckException("\n".join(errors))

    def check_cpl_reel_coherence_encryption(self, playlist):
        """ Encryption should be coherent across all reeels.

            This is not required explicitly in the standards but is known to
            cause issue for some equipements in the field.

            Reference : N/A
        """
        cpl = playlist['Info']['CompositionPlaylist']
        if cpl['Encrypted'] == "Mixed":
            raise CheckException("Encryption is not coherent for all reels")

    def check_cpl_reel_duration(self, playlist):
        """ CPL reels shall last at least one second.

            Reference :
                SMPTE 429-7-2006 9.2
        """
        errors = []
        for reel in playlist['Info']['CompositionPlaylist']['ReelList']:
            pic = reel['Assets']['Picture']
            edit = pic['EditRate']
            if pic['Duration'] < edit or pic['IntrinsicDuration'] < edit:
                errors.append("Reel {} last less than one second".format(
                    reel['Position']))
        if errors:
            raise CheckException("\n".join(errors))

    def check_cpl_reel_duration_picture_sound(self, playlist):
        """ CPL reels picture and audio tracks duration shall match.

            Reference :
                SMPTE 429-2-2013 9.4
        """
        self.metadata_cmp_pair(playlist, 'Duration', 'Picture', 'Sound')

    def check_cpl_reel_duration_picture_aux(self, playlist):
        """ CPL reels picture and auxiliary tracks duration shall match.

            Reference :
                SMPTE 429-2-2013 9.4
        """
        self.metadata_cmp_pair(playlist, 'Duration', 'Picture', 'AuxData')

    def check_cpl_reel_duration_picture_subtitles(self, playlist):
        """ CPL reels picture and subtitle tracks duration check.

            For Interop: MainSubtitle Duration must be equal to MainPicture
            Duration.
            For SMPTE: MainSubtitle duration is allowed to be less than or
            equal to MainPicture Duration.

            Reference : N/A
         """
        cmp_op = None
        mess = None

        if self.dcp.schema == "Interop":
            cmp_op = operator.eq
            mess = ("MainSubtitle and MainPicture Duration must match for "
                    "Interop DCP")
        else:
            cmp_op = operator.ge
            mess = ("MainSubtitle Duration must less than or equal that of "
                    "MainPicture for SMPTE DCP")

        self.metadata_cmp_pair(
            playlist, 'Duration', 'Picture', 'Subtitle', cmp_op, mess)

    def check_cpl_reels_cut(self, playlist):
        """ CPL reels cut coherence check.

            Reference :
                SMPTE 429-7-2006 8.1.4, 8.1.5, 8.1.6
        """
        cpl_position = 0
        cut_keys = ['CPLEntryPoint', 'CPLOutPoint', 'Duration']

        errors = []
        for reel in playlist['Info']['CompositionPlaylist']['ReelList']:
            assets = [
                v for k, v in six.iteritems(reel['Assets'])
                for key in cut_keys
                if key in v.keys()
            ]

            for asset in assets:
                start = asset['CPLEntryPoint']
                end = asset['CPLOutPoint']
                dur = asset['Duration']
                pos_reel = reel['Position']

                if start != cpl_position:
                    errors.append(
                        "Invalid CPLEntryPoint in Reel {}".format(pos_reel))

                if end - start != dur:
                    errors.append(
                        "Invalid Duration in Reel {}".format(pos_reel))

            cpl_position += assets[0]['Duration']

        if errors:
            raise CheckException("\n".join(errors))

    def check_assets_cpl_missing_from_vf(self, playlist, asset):
        """ CPL assets referencing external package.

            Reference : N/A
        """
        _, asset = asset
        uuid = asset['Id']
        is_vf_asset = uuid not in self.dcp._list_asset
        is_relinked_from_ov = 'Probe' in asset

        if is_vf_asset and not is_relinked_from_ov:
            asset_type = get_type_for_asset(playlist, uuid)
            raise CheckException(
                "Asset missing ({}), external reference".format(asset_type))

    def check_assets_cpl_missing_from_multi_cpl(self, playlist, asset):
        """ Multi CPL package must be self contained.

            Reference : N/A
        """
        _, asset = asset
        uuid = asset['Id']
        is_found = uuid in self.dcp._list_asset

        if len(self.dcp.list_cpl) == 1:
            return

        if not is_found:
            asset_type = get_type_for_asset(playlist, uuid)
            raise CheckException(
                "Asset missing ({}), multi CPL must be complete"
                .format(asset_type))

    def check_assets_cpl_labels(self, playlist, asset):
        """ CPL assets labels check.

            Reference : N/A
        """
        _, asset = asset

        if 'Probe' in asset:
            label = asset['Probe'].get('LabelSetType')
            if label and label not in self.mxf_schema_map.values():
                raise CheckException("MXF Label invalid : {}".format(label))

    def check_assets_cpl_labels_schema(self, playlist, asset):
        """ CPL assets labels / schema coherence check.

            Reference : N/A
        """
        _, asset = asset

        if 'Probe' in asset:
            label = asset['Probe'].get('LabelSetType')
            if label and self.mxf_schema_map[self.dcp.schema] != label:
                raise CheckException(
                    "MXF Label incoherent, got {} but expected {}".format(
                        label, self.mxf_schema_map[self.dcp.schema]))

    def check_assets_cpl_uuid(self, playlist, asset):
        """ CPL assets UUID RFC4122 compliance.

            Reference :
                SMPTE 429-7-2006 8.1.1
        """
        _, asset = asset
        uuid = asset['Id']

        if not check_uuid(uuid, RFC4122_RE):
            raise CheckException(
                "Asset ID invalid (RFC 4122) : {}".format(uuid))

    def check_assets_cpl_filename_uuid(self, playlist, asset):
        """ CPL assets file name UUID check.

            Reference : N/A
        """
        _, asset = asset

        if 'Path' in asset:
            file_uuid = extract_uuid(asset['Path'])
            cpl_uuid = asset['Id']
            if file_uuid:
                compare_uuid(
                    ('FILENAME', file_uuid),
                    ('CPL', cpl_uuid))

    def check_assets_cpl_hash(self, playlist, asset):
        """ CPL assets Hash shall be present alongside KeyId (encrypted).

            Reference :
                SMPTE 429-2-2013 9.11
        """
        if 'KeyId' in asset and 'Hash' not in asset:
            raise CheckException("Encrypted asset must have a Hash element")

    def check_assets_cpl_cut(self, playlist, asset):
        """ CPL assets cut coherence check.

            Reference :
                SMPTE 429-7-2006 8.1.4, 8.1.5, 8.1.6
        """
        _, asset = asset
        cut_keys = ['EntryPoint', 'OutPoint', 'IntrinsicDuration']

        if all_keys_in_dict(asset, cut_keys):
            start = asset['EntryPoint']
            end = asset['OutPoint']
            dur = asset['IntrinsicDuration']

            if start >= dur:
                raise CheckException("Invalid EntryPoint")
            if end > dur:
                raise CheckException("Invalid Duration")

    def check_assets_cpl_metadata(self, playlist, asset):
        """ CPL assets metadata coherence with MXF tracks.

            Reference : N/A
        """
        _, asset = asset
        # This a correspondance table between CPL and MXF tags
        metadata_map = {
            'EditRate': 'EditRate',
            'FrameRate': 'SampleRate',
            'Encrypted': 'EncryptedEssence',
            'IntrinsicDuration': 'ContainerDuration',
            'ScreenAspectRatio': 'AspectRatio',
            'Id': 'AssetUUID',
            'KeyId': 'CryptographicKeyID',
        }

        if 'Probe' not in asset:
            return

        errors = []
        for k, v in six.iteritems(metadata_map):
            if k in asset and v in asset['Probe']:
                cpl_val = asset[k]
                mxf_val = asset['Probe'][v]
                is_float = type(cpl_val) is float or type(mxf_val) is float

                matching = is_float and compare_ratio(cpl_val, mxf_val)
                matching = matching or not is_float and cpl_val == mxf_val
                if not matching:
                    errors.append(
                        "{} metadata mismatch, CPL claims {} but MXF {}"
                        .format(k, cpl_val, mxf_val))
            if k in asset and v not in asset['Probe']:
                errors.append("Missing MXF Metadata {}".format(v))
            if k not in asset and v in asset['Probe']:
                errors.append("Missing CPL Metadata {} for asset {}".format(k))
        if errors:
            raise CheckException("\n".join(errors))
