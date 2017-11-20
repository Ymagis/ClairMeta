# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six

from clairmeta.utils.sys import all_keys_in_dict
from clairmeta.utils.uuid import check_uuid, extract_uuid, RFC4122_RE
from clairmeta.dcp_check import CheckerBase, CheckException
from clairmeta.dcp_check_utils import check_xml, check_issuedate, compare_uuid
from clairmeta.dcp_utils import list_cpl_assets


class Checker(CheckerBase):
    def __init__(self, dcp, profile):
        super(Checker, self).__init__(dcp, profile)

    def run_checks(self):
        for source in self.dcp._list_cpl:
            checks = self.find_check('cpl')
            [self.run_check(check, source, message=source['FileName'])
             for check in checks]

            asset_checks = self.find_check('assets_cpl')
            [self.run_check(
                check, source, asset, message="{} (Asset {})".format(
                    source['FileName'], asset[1].get('Path', asset[1]['Id'])))
             for asset in list_cpl_assets(source)
             for check in asset_checks]

        return self.check_executions

    def metadata_match_pair(
        self,
        playlist,
        metadata,
        type_a,
        type_b
    ):
        for reel in playlist['Info']['CompositionPlaylist']['ReelList']:
            metadatas = {
                k: v[metadata] for k, v in six.iteritems(reel['Assets'])
                if v.get(metadata) and k in [type_a, type_b]
            }

            if len(set(list(metadatas.values()))) != 1:
                raise CheckException(
                    "{} / {} duration mismatch for Reel {}".format(
                        type_a, type_b, reel['Position']))

    def check_cpl_xml(self, playlist):
        cpl = playlist['Info']['CompositionPlaylist']
        check_xml(
            playlist['FilePath'],
            cpl['__xmlns__'],
            cpl['Schema'],
            self.dcp.schema)

    def check_cpl_id_rfc4122(self, playlist):
        cpl = playlist['Info']['CompositionPlaylist']
        uuid = cpl['Id']

        if not check_uuid(uuid, RFC4122_RE):
            raise CheckException("CPL ID invalid (RFC 4122) : {}".format(uuid))

    def check_cpl_contenttitle_annotationtext_match(self, playlist):
        cpl_node = playlist['Info']['CompositionPlaylist']
        ct = cpl_node['ContentTitleText']
        at = cpl_node.get('AnnotationText')
        if at and at != ct:
            raise CheckException("CPL ContentTitleText / AnnotationText "
                                 "mismatch : {} / {}".format(ct, at))

    def check_cpl_contenttitle_pklannotationtext_match(self, playlist):
        cpl_node = playlist['Info']['CompositionPlaylist']
        ct = cpl_node['ContentTitleText']
        cpl_pkl = [
            pkl for pkl in self.dcp._list_pkl
            if pkl['Info']['PackingList']['Id'] == cpl_node['PKLId']]
        if cpl_pkl:
            pkl = cpl_pkl[0]
            at = pkl['Info']['PackingList'].get('AnnotationText')
            if at and at != ct:
                raise CheckException(
                    "CPL ContentTitleText / PKL "
                    "AnnotationText mismatch : {} / {}".format(ct, at))

    def check_cpl_issuedate(self, playlist):
        cpl = playlist['Info']['CompositionPlaylist']
        check_issuedate(cpl['IssueDate'])

    def check_cpl_referenced_by_pkl(self, playlist):
        cpl = playlist['Info']['CompositionPlaylist']
        pkl_id = cpl.get('PKLId')
        if not pkl_id:
            raise CheckException("CPL is not referenced in any PKL")

    def check_cpl_reel_coherence(self, playlist):
        cpl = playlist['Info']['CompositionPlaylist']

        coherence_keys = [
            'EditRate',
            'FrameRate',
            'HighFrameRate',
            'ScreenAspectRatio',
            'Stereoscopic',
            'Resolution',
            'Encrypted',
            'DecompositionLevels',
            'Precincts',
            'ChannelCount',
            'ChannelFormat',
            'ChannelConfiguration',
            'SoundLanguage',
        ]

        for k in coherence_keys:
            if cpl[k] == "Mixed":
                raise CheckException(
                    "{} is not coherent for all reels".format(k))

    def check_cpl_reel_duration(self, playlist):
        for reel in playlist['Info']['CompositionPlaylist']['ReelList']:
            pic = reel['Assets']['Picture']
            edit = pic['EditRate']
            if pic['Duration'] < edit or pic['IntrinsicDuration'] < edit:
                raise CheckException(
                    "Reel {} last less than one second".format(
                        reel['Position']))

    def check_cpl_reel_duration_picture_sound(self, playlist):
        self.metadata_match_pair(playlist, 'Duration', 'Picture', 'Sound')

    def check_cpl_reel_duration_picture_aux(self, playlist):
        self.metadata_match_pair(playlist, 'Duration', 'Picture', 'AuxData')

    def check_cpl_reel_duration_picture_subtitles(self, playlist):
        self.metadata_match_pair(playlist, 'Duration', 'Picture', 'Subtitle')

    def check_cpl_reels_cut(self, playlist):
        cpl_position = 0
        cut_keys = ['CPLEntryPoint', 'CPLOutPoint', 'Duration']

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
                    raise CheckException(
                        "Invalid CPLEntryPoint in Reel {}".format(pos_reel))

                if end - start != dur:
                    raise CheckException(
                        "Invalid Duration in Reel {}".format(pos_reel))

            cpl_position += assets[0]['Duration']

    def check_assets_cpl_schema(self, playlist, asset):
        _, asset = asset
        mxf_schema_map = {
            'Interop': 'MXFInterop',
            'SMPTE': 'SMPTE',
        }

        if 'Probe' in asset:
            label = asset['Probe'].get('LabelSetType')
            if label and mxf_schema_map[self.dcp.schema] != label:
                raise CheckException(
                    "MXF Label invalid, got {} but expected {}".format(
                        label, mxf_schema_map[self.dcp.schema]))

    def check_assets_cpl_uuid(self, playlist, asset):
        _, asset = asset
        uuid = asset['Id']

        if not check_uuid(uuid, RFC4122_RE):
            raise CheckException(
                "Asset ID invalid (RFC 4122) : {}".format(uuid))

    def check_assets_cpl_filename_uuid(self, playlist, asset):
        _, asset = asset

        if 'Path' in asset:
            file_uuid = extract_uuid(asset['Path'])
            cpl_uuid = asset['Id']
            if file_uuid:
                compare_uuid(
                    ('FILENAME', file_uuid),
                    ('CPL', cpl_uuid))

    def check_assets_cpl_hash(self, playlist, asset):
        """ SMPTE 429-2 : the Hash element shall be present in an asset when
            the KeyId element is present (i.e., when the referenced Track File
            is encrypted).
        """
        if 'KeyId' in asset and 'Hash' not in asset:
            raise CheckException("Encrypted asset must have a Hash element")

    def check_assets_cpl_cut(self, playlist, asset):
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

        if 'Probe' in asset:
            for k, v in six.iteritems(metadata_map):
                if k in asset and v in asset['Probe']:
                    if asset[k] != asset['Probe'][v]:
                        raise CheckException(
                            "{} metadata mismatch, CPL claims {} but MXF {}"
                            .format(k, asset[k], asset['Probe'][v]))
                if k in asset and v not in asset['Probe']:
                    raise CheckException("Missing MXF Metadata {}".format(v))
                if k not in asset and v in asset['Probe']:
                    raise CheckException("Missing CPL Metadata {} for asset {}"
                                         "".format(k))
