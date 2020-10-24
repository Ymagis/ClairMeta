# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six
import os
import base64
import binascii
import uuid

from clairmeta.utils.sys import key_by_path_dict
from clairmeta.utils.probe import probe_mxf, stat_mxf_audio


#
# Generators to iterate on assets
#

def list_am_assets(assetmap):
    """ Iterator on AssetMap assets.

        Args:
            assetmap (dict): Dictionary representation of AssetMap.

        Yields:
            (str, str, dict): Tuple containing asset UUID, Path, Dict.

    """
    am = assetmap['Info']['AssetMap']
    for asset in am['AssetList'].get('Asset', []):
        uuid = asset['Id']
        path = asset['ChunkList']['Chunk']['Path']
        path = path.replace('file:///', '').replace('file://', '')
        yield uuid, path, asset


def list_pkl_assets(packinglist):
    """ Iterator on PackingList assets.

        Args:
            packinglist (dict): Dictionary representation of PackingList.

        Yields:
            (str, str, dict): Tuple containing asset UUID, Path, Dict.

    """
    root_path = os.path.dirname(packinglist['FilePath'])
    pkl = packinglist['Info']['PackingList']
    for asset in pkl['AssetList'].get('Asset', []):
        uuid = asset['Id']
        path = asset.get('Path')
        path = os.path.join(root_path, path) if path else path
        yield uuid, path, asset


def list_cpl_assets(
    cpl,
    filters=[
        'Picture', 'Sound', 'AuxData', 'Subtitle',
        'OpenCaption', 'ClosedCaption'
    ],
    required_keys=[]
):
    """ Iterator on CompositionPlayList assets.

        Args:
            cpl (dict): Dictionary representation of CompositionPlayList.
            filters (list): Restricted assets type.
            required_keys: Required keys for assets.

        Yields:
            (str, dict): Tuple containing asset Type, Dict.

    """
    for reel in cpl['Info']['CompositionPlaylist']['ReelList']:
        assets = reel.get('Assets', {})
        assets = {k: v for k, v in six.iteritems(assets) if k in filters}

        if required_keys:
            assets = {
                k: v for k, v in six.iteritems(assets)
                for req_k in required_keys if req_k in v}

        for k, v in six.iteritems(assets):
            yield k, v


#
# Lookup utilities
#

def get_reel_for_asset(cpl, uuid):
    """ Asset Reel lookup.

        Args:
            cpl (dict): Dictionary representation of CompositionPlayList.
            uuid (str): Asset UUID.

        Returns:
            Returns the Reel Dictionary in which ``uuid`` Asset was found.

    """
    for reel in cpl['Info']['CompositionPlaylist']['ReelList']:
        assets = reel.get('Assets', [])
        uuids = [a['Id'] for a in assets.values()]

        if uuid in uuids:
            return reel


def get_type_for_asset(cpl, uuid):
    """ Asset Track type lookup (eg. Picture, Sound, AuxData, ...).

        Args:
            cpl (dict): Dictionary representation of CompositionPlayList.
            uuid (str): Asset UUID.

        Returns:
            Returns the a string describing the asset type.

    """
    for reel in cpl['Info']['CompositionPlaylist']['ReelList']:
        assets = reel.get('Assets', [])
        for asset_type, asset in six.iteritems(assets):
            if uuid == asset['Id']:
                return asset_type

    return "Unknown"


def get_contentkey_for_asset(dcp, asset):
    """ Asset encryption key lookup.

        Args:
            asset (dict): Dictionary representation of Asset.

        Returns:
            Returns the ContentKey of the encrypted MXF essence or None if not
            found.

        Raise:
            ValueError: Asset ``asset_id`` don't have a KeyId tag.
            LookupError: Asset ``asset_id`` key was not found.

    """
    if 'KeyId' not in asset:
        raise ValueError("Asset {} don't have a KeyId tag".format(asset['Id']))

    key_id = asset['KeyId']
    for kdm in dcp.list_kdm:
        keys_list = kdm['Info']['KDM']['Keys']
        if key_id in keys_list and 'ContentKey' in keys_list[key_id]:
            return keys_list[key_id]['ContentKey']

    raise LookupError("Asset {} key was not found".format(asset['Id']))


#
# CPL utilities
#

def cpl_extract_characteristics(cpl):
    """ Extract common characteristics of CompositionPlayList Reels.

        Args:
            cpl (dict): Dictionary representation of CompositionPlayList.
                Extracted values are added in place.

    """

    # These are global coherence keys, last part of the path is the final
    # value in cpl dict : this means all keys ending with eg. EditRate get
    # merged and if only one subset has mixed values, this will be the
    # retained output.
    integrity_keys = {
        'Picture.EditRate': [],
        'Picture.FrameRate': [],
        'Picture.HighFrameRate': [],
        'Picture.ScreenAspectRatio': [],
        'Picture.Stereoscopic': [],
        'Picture.Encrypted': [],
        'Picture.Probe.DecompositionLevels': [],
        'Picture.Probe.Precincts': [],
        'Picture.Probe.Resolution': [],
        'Sound.EditRate': [],
        'Sound.Encrypted': [],
        'Sound.Probe.ChannelCount': [],
        'Sound.Probe.ChannelFormat': [],
        'Sound.Probe.ChannelConfiguration': [],
        'AuxData.EditRate': [],
        'AuxData.Encrypted': [],
        'Subtitle.EditRate': [],
    }

    # These are per essence (picture, sound, ...) coherence keys, this means
    # keys won't get merged.
    essence_keys = {
        'Sound.Language': [],
        'Subtitle.Language': [],
        'OpenCaption.Language': [],
        'ClosedCaption.Language': [],
    }

    # These check the presence of certain essence in the CPL
    presence_keys = {
        'Picture': [],
        'Sound': [],
        'Subtitle': [],
        'OpenCaption': [],
        'ClosedCaption': [],
        'AuxData': [],
        'Markers': [],
        'Metadata': [],
    }

    for reel in cpl['ReelList']:
        # Integrity sets building
        for iset in [integrity_keys, essence_keys]:
            for ikey in iset:
                node_value = key_by_path_dict(reel['Assets'], ikey)
                if node_value is not None:
                    iset[ikey].append(node_value)
        # Presence set building
        for pkey in presence_keys:
            presence_keys[pkey].append(pkey in reel['Assets'])

    unified_integrity_keys = {}
    for k, v in six.iteritems(integrity_keys):
        key = k.split('.')[-1]
        if key in unified_integrity_keys:
            unified_integrity_keys[key] += v
        else:
            unified_integrity_keys[key] = v

    for k, v in six.iteritems(essence_keys):
        key = k.replace('.', '')
        unified_integrity_keys[key] = v

    for k, v in six.iteritems(unified_integrity_keys):
        if len(set(v)) == 1:
            cpl_value = v[0]
        elif len(set(v)) > 1:
            cpl_value = "Mixed"
        else:
            cpl_value = "Unknown"

        cpl[k] = cpl_value

    for k, v in six.iteritems(presence_keys):
        cpl_key = k.split('.')[-1]
        cpl[cpl_key] = any(v)


def cpl_probe_asset(asset, essence, path):
    """ Probe an individual MXF asset.

        Args:
            asset (dict): Dictionary representation of Asset.
            essence (str): Type of Asset.
            path (str): Absolute path of Asset file.

    """
    if not path.endswith('.mxf'):
        return

    try:
        is_stereoscopic = asset.get('Stereoscopic', False)
        asset['Probe'] = probe_mxf(path, stereoscopic=is_stereoscopic)

        is_encrypted = asset['Probe']['EncryptedEssence']
        if essence == 'Sound' and not is_encrypted:
            asset['Probe']['AudioAnalyze'] = stat_mxf_audio(
                path,
                int(asset['Probe']['ChannelCount']),
                asset['EntryPoint'],
                asset['Duration'])
    except Exception as e:
        asset['ProbeError'] = str(e)


#
# KDM utilities
#


def kdm_extract_key_info(data):
    """ Extract fields from decoded key cipher data.

        For more details, see SMPTE 430-1, section 6.1.2

        Args:
            data (bytes): Decoded key cipher data.

        Returns:
            Returns a Dictionary containing all key info fields.
    """
    fields = {}

    fields['StructureID'] = binascii.hexlify(data[:16]).decode()
    fields["CertificateThumbprint"] = base64.b64encode(data[16:36]).decode()
    fields["CompositionPlaylistId"] = str(uuid.UUID(bytes=data[36:52]))
    fields["KeyType"] = data[52:56].decode('ascii')
    fields["KeyId"] = str(uuid.UUID(bytes=data[56:72]))
    fields["NotValidBefore"] = data[72:97].decode('ascii')
    fields["NotValidAfter"] = data[97:122].decode('ascii')
    fields["ContentKey"] = binascii.hexlify((data[122:138])).decode()

    return fields