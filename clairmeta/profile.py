# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six
import json
import os
import copy

from clairmeta.exception import ClairMetaException


DCP_CHECK_PROFILE = {
    # Checker criticality
    # Base level is default and can be overrided per check using its name
    # Incomplete name allowed, the best match will be selected automatically
    # Wildcard character allowed for regex based matching
    # 4 levels : ERROR, WARNING, INFO and SILENT.
    'criticality': {
        'default': 'ERROR',
        'check_dcnc_': 'WARNING',
        'check_dcp_foreign_files': 'WARNING',
        'check_assets_am_volindex_one': 'WARNING',
        'check_*_empty_text_fields': 'WARNING',
        'check_*_empty_text_fields_missing': 'ERROR',
        'check_*_xml_constraints_line_ending': 'WARNING',
        'check_cpl_contenttitle_annotationtext_match': 'WARNING',
        'check_cpl_contenttitle_pklannotationtext_match': 'WARNING',
        'check_assets_cpl_missing_from_vf': 'WARNING',
        'check_assets_cpl_labels_schema': 'WARNING',
        'check_assets_cpl_filename_uuid': 'WARNING',
        'check_certif_multi_role': 'WARNING',
        'check_certif_date_overflow': 'WARNING',
        'check_picture_cpl_avg_bitrate': 'WARNING',
        'check_picture_cpl_resolution': 'WARNING',
        'check_subtitle_cpl_reel_number': 'WARNING',
        'check_subtitle_cpl_empty': 'WARNING',
        'check_subtitle_cpl_uuid_case': 'WARNING',
        'check_subtitle_cpl_duplicated_uuid': 'WARNING',
        'check_subtitle_cpl_first_tt_event': 'WARNING',
        'check_picture_cpl_archival_framerate': 'WARNING',
        'check_picture_cpl_hfr_framerate': 'WARNING',
        'check_sound_cpl_format': 'WARNING',
        'check_sound_cpl_channel_assignments': 'WARNING',
        'check_atmos_cpl_channels': 'WARNING',
        'check_atmos_cpl_objects': 'WARNING',
    },
    # Checker options
    # Bypass is a list of check names (function names)
    'bypass': [],
    # Allowed foreign files, paths are relative to the DCP root
    'allowed_foreign_files' : [],
}


def get_default_profile():
    """ Returns the default DCP checking profile """
    return copy.deepcopy(DCP_CHECK_PROFILE)


def load_profile(file_path):
    """ Load a check profile config file.

        ``file_path`` must be a valid json configuration file, this function
        include a basic check for correctness (required keys and type).

        Args:
            file_path (str): Config file (json) absolute path.

        Returns:
            Dictionary containing check profile settings.

        Raise:
            ClairMetaException: ``file_path`` is not a valid file.
            ClairMetaException: ``file_path`` is not a json file (.json).
            ClairMetaException: ``file_path`` json parsing error.
            ClairMetaException: ``file_path`` miss some required keys or values
                type are wrong.

    """
    if not os.path.isfile(file_path):
        raise ClairMetaException(
            "Load Profile : {} file not found".format(file_path))

    allowed_ext = ['.json']
    file_ext = os.path.splitext(file_path)[-1]
    if file_ext not in allowed_ext:
        raise ClairMetaException(
            "Load Profile : {} must be a valid json file".format(file_path))

    profile_format = {
        'criticality': dict,
        'bypass': list
    }

    try:
        with open(file_path) as f:
            profile = json.load(f)
    except Exception as e:
        raise ClairMetaException(
            "Load Profile {} : loading error - {}".format(file_path, str(e)))

    for k, v in six.iteritems(profile_format):
        if k not in profile:
            raise ClairMetaException(
                "Load Profile {} : missing key {}".format(file_path, k))
        if not isinstance(profile[k], v):
            raise ClairMetaException(
                "Load Profile {} : key {} should be a {}".format(
                    file_path, k, v))

    return profile


def save_profile(profile, file_path):
    """ Save a check profile to json config file.

        Args:
            profile (dict): Check profile to save.
            file_path (str): Config file (json) absolute path.

    """
    with open(file_path, 'w') as f:
        json.dump(profile, f)
