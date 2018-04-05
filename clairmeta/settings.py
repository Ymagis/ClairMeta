# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

LOG_SETTINGS = {
    'level': 'INFO',
    'enable_console': True,
    'enable_file': True,
    'file_name': '~/Library/Logs/clairmeta.log',
    'file_size': 1e6,
    'file_count': 10,
}

DCP_SETTINGS = {
    # ISDCF Naming Convention enforced
    'naming_convention': '9.3',
    # Recognized XML namespaces
    'xmlns': {
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'xmldsig': 'http://www.w3.org/2000/09/xmldsig#',
        'cpl_metadata_href': 'http://isdcf.com/schemas/draft/2011/cpl-metadata',
        'interop_pkl': 'http://www.digicine.com/PROTO-ASDCP-PKL-20040311#',
        'interop_cpl': 'http://www.digicine.com/PROTO-ASDCP-CPL-20040511#',
        'interop_am': 'http://www.digicine.com/PROTO-ASDCP-AM-20040311#',
        'interop_vl': 'http://www.digicine.com/PROTO-ASDCP-VL-20040311#',
        'interop_stereo': 'http://www.digicine.com/schemas/437-Y/2007/Main-Stereo-Picture-CPL',
        'interop_subtitle': 'interop_subtitle',
        'smpte_pkl_2006': 'http://www.smpte-ra.org/schemas/429-8/2006/PKL',
        'smpte_pkl_2007': 'http://www.smpte-ra.org/schemas/429-8/2007/PKL',
        'smpte_cpl': 'http://www.smpte-ra.org/schemas/429-7/2006/CPL',
        'smpte_cpl_metadata': 'http://www.smpte-ra.org/schemas/429-16/2014/CPL-Metadata',
        'smpte_am_2006': 'http://www.smpte-ra.org/schemas/429-9/2006/AM',
        'smpte_am_2007': 'http://www.smpte-ra.org/schemas/429-9/2007/AM',
        'smpte_stereo_2007': 'http://www.smpte-ra.org/schemas/429-10/2007/Main-Stereo-Picture-CPL',
        'smpte_stereo_2008': 'http://www.smpte-ra.org/schemas/429-10/2008/Main-Stereo-Picture-CPL',
        'smpte_subtitles_2007': 'http://www.smpte-ra.org/schemas/428-7/2007/DCST',
        'smpte_subtitles_2010': 'http://www.smpte-ra.org/schemas/428-7/2010/DCST',
        'smpte_subtitles_2014': 'http://www.smpte-ra.org/schemas/428-7/2014/DCST',
        'smpte_tt': 'http://www.smpte-ra.org/schemas/429-12/2008/TT',
        'smpte_etm': 'http://www.smpte-ra.org/schemas/430-3/2006/ETM',
        'smpte_kdm': 'http://www.smpte-ra.org/schemas/430-1/2006/KDM',
        'atmos': 'http://www.dolby.com/schemas/2012/AD',
    },
    # Recognized XML identifiers
    'xmluri': {
        'interop_sig': 'http://www.w3.org/2000/09/xmldsig#rsa-sha1',
        'smpte_sig': 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256',
        'enveloped_sig': 'http://www.w3.org/2000/09/xmldsig#enveloped-signature',
        'c14n': 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315',
        'sha1': 'http://www.w3.org/2000/09/xmldsig#sha1',
        'dolby_edr': 'http://www.dolby.com/schemas/2014/EDR-Metadata',
    },
    'picture': {
        # Standard resolutions
        'resolutions': {
            '2K': ['1998x1080', '2048x858', '2048x1080'],
            '4K': ['3996x2160', '4096x1716', '4096x2160'],
            'HD': ['1920x1080'],
            'UHD': ['3840x2160'],
        },
        # Standard editrate
        'editrates': {
            '2K': {'2D': [24, 25, 30, 48, 50, 60], '3D': [24, 25, 30, 48, 50, 60]},
            '4K': {'2D': [24, 25, 30], '3D': []},
        },
        # Archival editrate
        'editrates_archival': [16, 200.0/11, 20, 240.0/11],
        # HFR capable quipements (projection servers)
        'editrates_min_series2': {
            '2D': 96,
            '3D': 48,
        },
        # Standard aspect ratio
        'aspect_ratio': {
            'F': {'ratio': 1.85, 'resolutions': ['1998x1080', '3996x2160']},
            'S': {'ratio': 2.39, 'resolutions': ['2048x858', '4096x1716']},
            'C': {'ratio': 1.90, 'resolutions': ['2048x1080', '4096x2160']},
        },
        # For metadata tagging, decoupled from bitrate thresholds
        'min_hfr_editrate': 48,
        # As stated in http://www.dcimovies.com/Recommended_Practice/
        # These are in Mb/s
        # Note : asdcplib use a 400Mb/s threshold for HFR, why ?
        'max_dci_bitrate': 250,
        'max_hfr_bitrate': 500,
        'max_dvi_bitrate': 400,
        'min_editrate_hfr_bitrate': {
            '2K': {'2D': 60, '3D': 48},
            '4K': {'2D': 48, '3D': 0}
        },
        # We allow a small offset above DCI specification :
        # asdcplib use a method of computation that can only give an
        # approximation (worst case scenario) of the actual max bitrate.
        # asdcplib basically find the biggest frame in the whole track and
        # multiply it by the editrate.
        # Note : DCI specification seems to limit individual j2c frame size,
        # the method used by asdcplib should be valid is this regard, it seems
        # that the observed bitrate between 250 and 250.05 are due to the
        # encryption overhead in the KLV packaging.
        'bitrate_tolerance': 0.05,
        # This is a percentage below max_bitrate
        'average_bitrate_margin': 2.0,
        # As stated in SMPTE 429-2
        'dwt_levels_2k': 5,
        'dwt_levels_4k': 6,
    },
    'sound': {
        'sampling_rate': [48000, 96000],
        'max_channel_count': 16,
        'quantization': 24,
        # This maps SMPTE 429-2 AudioDescriptor.ChannelFormat to a label and
        # a min / max number of allowed channels.
        # See. Section A.1.2 'Channel Configuration Tables'
        'configuration_channels': {
            1: ('5.1 with optional HI/VI', 6, 8),
            2: ('6.1 (5.1 + center surround) with optional HI/VI', 7, 10),
            3: ('7.1 (SDDS) with optional HI/VI', 8, 10),
            4: ('Wild Track Format', 1, 16),
            5: ('7.1 DS with optional HI/VI', 8, 10),
        },
        'format_channels': {
            '10': 1,
            '20': 2,
            '51': 6,
            '61': 7,
            '71': 8,
            '11.1': 12,
        },
    },
    'atmos': {
        'max_channel_count': 64,
        'max_object_count': 118
    },
    'subtitle': {
        # In bytes
        'font_max_size': 655360,
    },
}

DCP_CHECK_SETTINGS = {
    # List of check modules for DCP check, these modules will be imported
    # dynamically during the check process.
    'module_prefix': 'dcp_check_',
    'modules': {
        'vol': 'VolIndex checks',
        'am': 'AssetMap checks',
        'pkl': 'PackingList checks',
        'cpl': 'CompositionPlayList checks',
        'sign': 'Digital signature checks',
        'isdcf_dcnc': 'Naming Convention checks',
        'picture': 'Picture essence checks',
        'sound': 'Sound essence checks',
        'subtitle': 'Subtitle essence checks',
        'atmos': 'Atmos essence checks',
    }
}

IMP_SETTINGS = {
    'xmlns': {
        'xmldsig': 'http://www.w3.org/2000/09/xmldsig#',
        'imp_am': 'http://www.smpte-ra.org/schemas/429-9/2007/AM',
        'imp_pkl': 'http://www.smpte-ra.org/schemas/429-8/2007/PKL',
        'imp_opl': 'http://www.smpte-ra.org/schemas/2067-100/',
        'imp_cpl': 'http://www.smpte-ra.org/schemas/2067-3/',
    }
}

DSM_SETTINGS = {
    'allowed_extensions': {
        '.dpx': 'DPX image data',
        '.tiff': 'TIFF image data',
        '.tif': 'TIFF image data',
        '.exr': 'OpenEXR image data',
        '.cin': 'Cineon image data',
    },
    'directory_white_list': ['.thumbnails'],
    'file_white_list': ['.DS_Store'],
}

DCDM_SETTINGS = {
    'allowed_extensions': {
        '.tiff': 'TIFF image data',
        '.tif': 'TIFF image data',
    },
    'directory_white_list': ['.thumbnails'],
    'file_white_list': ['.DS_Store'],
}
