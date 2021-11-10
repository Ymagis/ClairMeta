# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import six

from clairmeta.utils.isdcf import parse_isdcf_string
from clairmeta.utils.xml import parse_xml
from clairmeta.utils.time import frame_to_tc, format_ratio
from clairmeta.utils.sys import all_keys_in_dict
from clairmeta.settings import DCP_SETTINGS
from clairmeta.logger import get_log
from clairmeta.exception import ProbeException


def discover_schema(node):
    """ Assign file Schema using detected namespace """
    xmlns = node.get('__xmlns__', None)

    if xmlns:
        node['Schema'] = 'Unknown'
        if xmlns.startswith('smpte_stereo'):
            node['Schema'] = 'SMPTE Stereoscopic'
        elif xmlns.startswith('smpte'):
            node['Schema'] = 'SMPTE'
        elif xmlns.startswith('interop'):
            node['Schema'] = 'Interop'
        elif xmlns.startswith('atmos'):
            node['Schema'] = 'Atmos'


def generic_parse(
    path,
    root_name,
    force_list=(),
    namespaces=DCP_SETTINGS['xmlns']
):
    """ Parse an XML and returns a Python Dictionary """
    try:
        res_dict = parse_xml(
            path,
            namespaces=namespaces,
            force_list=force_list)

        if res_dict and root_name in res_dict:
            node = res_dict[root_name]
            discover_schema(node)

            return {
                'FileName': os.path.basename(path),
                'FilePath': path,
                'Info': {
                    root_name: node
                }
            }
    except Exception as e:
        get_log().error("Error parsing XML {} : {}".format(path, str(e)))


def assetmap_parse(path):
    """ Parse DCP ASSETMAP """
    am = generic_parse(path, "AssetMap", ("Asset",))

    if am:
        total_size = 0
        total_size_ondisk = 0

        # Two ways of identifying a PKL inside the assetmap :
        # <PackingList></PackingList> (Interop)
        # <PackingList>true</PackingList> (SMPTE)
        # Hide these specificities and return PackingList: True in both cases
        for asset in am['Info']['AssetMap']['AssetList']['Asset']:
            total_size += asset['ChunkList']['Chunk'].get('Length', 0)
            filename = asset['ChunkList']['Chunk']['Path']
            filepath = os.path.join(os.path.dirname(path), filename)
            if os.path.exists(filepath):
                total_size_ondisk += os.path.getsize(filepath)

            if 'PackingList' in asset:
                asset['PackingList'] = True

        am['Info']['AssetMap']['AssetsSizeBytes'] = total_size
        am['Info']['AssetMap']['AssetsOnDiskSizeBytes'] = total_size_ondisk

    return am


def volindex_parse(path):
    """ Parse DCP VOLINDEX """
    return generic_parse(path, "VolumeIndex")


def pkl_parse(path):
    """ Parse DCP PKL """
    pkl = generic_parse(path, "PackingList", ("Asset",))

    if pkl:
        total_size = 0

        for asset in pkl['Info']['PackingList']['AssetList']['Asset']:
            total_size += asset.get('Size', 0)

        pkl['Info']['PackingList']['AssetsSizeBytes'] = total_size

    return pkl


def cpl_parse(path):
    """ Parse DCP CPL """
    cpl = generic_parse(
        path, "CompositionPlaylist",
        ("Reel", "ExtensionMetadata", "PropertyList"))

    if cpl:
        cpl_node = cpl['Info']['CompositionPlaylist']
        cpl_dcnc_parse(cpl_node)
        cpl_reels_parse(cpl_node)

    return cpl


def cpl_dcnc_parse(cpl_node):
    """ Extract information from ContentTitle """
    fields, errors = parse_isdcf_string(cpl_node.get('ContentTitleText'))
    cpl_node["NamingConvention"] = fields


def cpl_reels_parse(cpl_node):
    """ Transform Reels list to a more uniform representation """
    in_reels = cpl_node['ReelList']['Reel']
    out_reels = []

    global_editrate = 0
    total_frame_duration = 0

    is_dvi = False
    is_ec = False
    is_dbox = False
    eidr = ''

    for pos, in_reel in enumerate(in_reels, 1):

        assetlist = in_reel.get('AssetList')
        if not assetlist:
            continue

        out_reel = {}
        out_reel['Position'] = pos
        out_reel['Id'] = in_reel.get('Id', '')
        out_reel['AnnotationText'] = in_reel.get('AnnotationText', '')
        out_reel['Assets'] = {}

        # Recognized asset categories
        asset_mapping = {
            'MainPicture': 'Picture',
            'MainStereoscopicPicture': 'Picture',
            'MainSound': 'Sound',
            'AuxData': 'AuxData',
            'MainSubtitle': 'Subtitle',
            'MainMarkers': 'Markers',
            'CompositionMetadataAsset': 'Metadata',
            'MainCaption' : 'OpenCaption',
            'ClosedCaption': 'ClosedCaption',
            'MainClosedCaption': 'ClosedCaption',
        }

        # Generic asset parsing
        for key, val in six.iteritems(asset_mapping):
            if key in assetlist:
                out_reel['Assets'][val] = assetlist[key]

                asset = out_reel['Assets'][val]
                # Duplicated assets is a fatal error
                if isinstance(asset, list):
                    raise ProbeException(
                        "Duplicated {} asset in CPL {}, Reel {}".format(
                            key,
                            cpl_node.get('ContentTitleText', ''),
                            pos))

                discover_schema(asset)

                # Encryption
                asset['Encrypted'] = 'KeyId' in asset
                # Format Cut
                cpl_asset_parse_cut(asset, total_frame_duration)

        if 'Picture' in out_reel['Assets']:
            picture = out_reel['Assets']['Picture']

            editrate_r = float(picture.get('EditRate', 0))
            picture['Stereoscopic'] = 'MainStereoscopicPicture' in assetlist
            min_hfr_editrate = DCP_SETTINGS['picture']['min_hfr_editrate']
            picture['HighFrameRate'] = editrate_r >= min_hfr_editrate
            picture['FrameRate'] = format_ratio(picture.get('FrameRate'))
            picture["ScreenAspectRatio"] = format_ratio(
                picture.get('ScreenAspectRatio'))

            # Picture track is the reference for EditRate / Duration
            global_editrate = editrate_r
            total_frame_duration += picture.get('Duration', 0)

        if 'Markers' in out_reel['Assets']:
            marker = out_reel['Assets']['Markers']
            editrate_r = format_ratio(marker.get('EditRate'))
            marker['EditRate'] = editrate_r

            marker_list = marker['MarkerList']['Marker']
            if not type(marker_list) is list:
                marker['MarkerList'] = [marker_list]
            else:
                marker['MarkerList'] = marker_list

        if 'Metadata' in out_reel['Assets']:
            meta = out_reel['Assets']['Metadata']
            exts = meta.get(
                'ExtensionMetadataList', {}).get('ExtensionMetadata', [])
            for ext in exts:
                ext_name = ext.get('Name')
                properties = ext.get('PropertyList')

                if ext_name == 'Dolby EDR':
                    is_dvi = True
                elif ext_name == 'Eclair Color':
                    is_ec = True
                elif ext_name == 'D-BOX Enabled':
                    is_dbox = True
                elif ext_name == 'EIDR':
                    for p in properties:
                        prop_name = p['Property'].get('Name', '')
                        if prop_name != 'structural-type':
                            continue

                        eidr = p['Property'].get('Value', '')
                        eidr = eidr.replace('urn:eidr:10.5240:', '').strip()

        out_reels.append(out_reel)

    cpl_node['DolbyVision'] = is_dvi
    cpl_node['EclairColor'] = is_ec
    cpl_node['D-BOX'] = is_dbox
    cpl_node['EIDR'] = eidr

    cpl_node['ReelList'] = out_reels
    cpl_node['TotalDuration'] = total_frame_duration
    cpl_node['TotalTimeCodeDuration'] = frame_to_tc(
        total_frame_duration, global_editrate)


def cpl_asset_parse_cut(asset, position):
    """ Parse an asset Cut """
    edit_r = 0

    # Format Editrate
    if 'EditRate' in asset:
        edit_r = format_ratio(asset['EditRate'])
        asset['EditRate'] = edit_r

    # Format Cut
    if all_keys_in_dict(asset, ["EditRate", "Duration", "EntryPoint"]):
        asset['OutPoint'] = asset['Duration'] + asset['EntryPoint']
        asset['CPLEntryPoint'] = position
        asset['CPLOutPoint'] = position + asset['Duration']
        asset['TimeCodeIn'] = frame_to_tc(asset['CPLEntryPoint'], edit_r)
        asset['TimeCodeOut'] = frame_to_tc(asset['CPLOutPoint'], edit_r)
        asset['TimeCodeDuration'] = frame_to_tc(asset['Duration'], edit_r)


def kdm_parse(path):
    """ Parse KDM XML """
    in_dict = parse_xml(path, namespaces=DCP_SETTINGS['xmlns'])
    out_dict = {}

    keys = {}
    counter_mapping = {
        'MDIK': 0,
        'MDAK': 0,
        'MDSK': 0,
        'MDEK': 0
    }

    root = None

    if in_dict and 'DCinemaSecurityMessage' in in_dict:
        auth_pub = in_dict['DCinemaSecurityMessage']['AuthenticatedPublic']
        root = auth_pub['RequiredExtensions']
        req_ext = auth_pub['RequiredExtensions']

        if ('KDMRequiredExtensions' in req_ext and
                req_ext['KDMRequiredExtensions']['AuthorizedDeviceInfo']):
            root = req_ext['KDMRequiredExtensions']

            keys_pub = root['KeyIdList']['TypedKeyId']
            keys_priv = in_dict['DCinemaSecurityMessage']['AuthenticatedPrivate']['EncryptedKey']

            for pub, priv in zip(keys_pub, keys_priv):
                keys[pub['KeyId']] = {
                    'Cipher': priv['CipherData']['CipherValue']
                }

                key = pub['KeyType']
                if key in counter_mapping:
                    counter_mapping[key] += 1

            devices = root['AuthorizedDeviceInfo']['DeviceList']
            out_dict['AuthorizedDevice'] = devices['CertificateThumbprint']

        out_dict['ContentTitleText'] = root['ContentTitleText']
        out_dict['CompositionPlaylistId'] = root['CompositionPlaylistId']
        out_dict['StartDate'] = root['ContentKeysNotValidBefore']
        out_dict['EndDate'] = root['ContentKeysNotValidAfter']
        out_dict['Recipient'] = root['Recipient']['X509SubjectName']
        out_dict['Recipient'] = out_dict['Recipient'].split(',')[1]
        out_dict['ImageKeys'] = counter_mapping['MDIK']
        out_dict['AudioKeys'] = counter_mapping['MDAK']
        out_dict['SubtitleKeys'] = counter_mapping['MDSK']
        out_dict['AtmosKeys'] = counter_mapping['MDEK']
        out_dict['Keys'] = keys

        return {
            'FileName': os.path.basename(path),
            'FilePath': path,
            'Info': {
                'KDM': out_dict
            }
        }
