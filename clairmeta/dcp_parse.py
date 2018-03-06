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
        get_log().info("Error parsing XML {} : {}".format(path, str(e)))


def assetmap_parse(path):
    """ Parse DCP ASSETMAP """
    am = generic_parse(path, "AssetMap", ("Asset",))

    if am:
        # Two ways of identifying a PKL inside the assetmap :
        # <PackingList></PackingList> (Interop)
        # <PackingList>true</PackingList> (SMPTE)
        # Hide these specificities and return PackingList: True in both cases
        for asset in am['Info']['AssetMap']["AssetList"]["Asset"]:
            if 'PackingList' in asset:
                asset['PackingList'] = True

    return am


def volindex_parse(path):
    """ Parse DCP VOLINDEX """
    return generic_parse(path, "VolumeIndex")


def pkl_parse(path):
    """ Parse DCP PKL """
    return generic_parse(path, "PackingList", ("Asset",))


def cpl_parse(path):
    """ Parse DCP CPL """
    cpl = generic_parse(
        path, "CompositionPlaylist",
        ("Reel", "ExtensionMetadataList", "PropertyList"))

    if cpl:
        cpl_node = cpl['Info']['CompositionPlaylist']
        cpl_dcnc_parse(cpl_node)
        cpl_reels_parse(cpl_node)

    return cpl


def cpl_dcnc_parse(cpl_node):
    """ Extract information from ContentTitle """
    fields, errors = parse_isdcf_string(cpl_node.get('ContentTitleText'))
    if not errors:
        cpl_node["NamingConvention"] = fields


def cpl_reels_parse(cpl_node):
    """ Transform Reels list to a more uniform representation """
    in_reels = cpl_node['ReelList']['Reel']
    out_reels = []

    global_editrate = 0
    total_frame_duration = 0
    is_dvi = False

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
            'ClosedCaption': 'ClosedCaption'
        }

        # Generic asset parsing
        for key, val in six.iteritems(asset_mapping):
            if key in assetlist:
                out_reel['Assets'][val] = assetlist[key]
                asset = out_reel['Assets'][val]
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
            if type(marker_list) is list:
                marker['MarkerList'] = marker_list
            else:
                marker['MarkerList'] = [{
                    marker_list["Label"]: marker_list["Offset"]
                }]

        if 'Metadata' in out_reel['Assets']:
            meta = out_reel['Assets']['Metadata']
            exts = meta.get('ExtensionMetadataList', [])
            for ext in exts:
                ext_desc = ext.get('ExtensionMetadata', {})
                ext_name = ext_desc.get('Name')
                # DolbyVision
                if ext_name == 'Dolby EDR':
                    is_dvi = True

        out_reels.append(out_reel)

    cpl_node['DolbyVision'] = is_dvi
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

    counter_mapping = {
        'MDIK': 0,
        'MDAK': 0,
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

            for item in root['KeyIdList']['TypedKeyId']:
                if isinstance(item['KeyType'], dict):
                    key = item['KeyType']['#text']
                else:
                    key = item['KeyType']

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
        out_dict['AtmosKeys'] = counter_mapping['MDEK']

        return {
            'FileName': os.path.basename(path),
            'FilePath': path,
            'Info': {
                'KDM': out_dict
            }
        }
