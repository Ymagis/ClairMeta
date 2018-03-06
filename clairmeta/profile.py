# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six
import json
import os
import copy


DCP_CHECK_PROFILE = {
    # Checker criticality
    # Base level is default and can be overrided per check using its name
    # Incomplete name allowed, the best match will be selected automatically
    # 4 levels : ERROR, WARNING, INFO and SILENT.
    'criticality': {
        'default': 'ERROR',
        'check_dcnc_': 'WARNING',
        'check_cpl_contenttitle_annotationtext_match': 'WARNING',
        'check_cpl_contenttitle_pklannotationtext_match': 'WARNING',
        'check_cpl_reel_duration_picture_subtitles': 'WARNING',
        'check_assets_cpl_missing_from_vf': 'WARNING',
        'check_assets_cpl_labels_schema': 'WARNING',
        'check_certif_multi_role': 'WARNING',
        'check_picture_cpl_avg_bitrate': 'WARNING',
        'check_picture_cpl_resolution': 'WARNING',
        'check_subtitle_cpl_reel_number': 'WARNING',
        'check_picture_cpl_archival_framerate': 'WARNING',
        'check_picture_cpl_hfr_framerate': 'WARNING',
        'check_sound_cpl_format': 'WARNING',
    },
    # Checker options
    # Bypass is a list of check names (function names)
    'bypass': [],
    'log_level': 'INFO',
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
            ValueError: ``file_path`` is not a valid file.
            ValueError: ``file_path`` is not a json file (.json).
            ValueError: ``file_path`` json parsing error.
            ValueError: ``file_path`` miss some required keys or values type
                are wrong.

    """
    if not os.path.isfile(file_path):
        raise ValueError("Load Profile : {} file not found".format(file_path))

    allowed_ext = ['.json']
    file_ext = os.path.splitext(file_path)[-1]
    if file_ext not in allowed_ext:
        raise ValueError(
            "Load Profile : {} must be a valid json file".format(file_path))

    profile_format = {
        'criticality': dict,
        'bypass': list,
        'log_level': six.string_types
    }

    try:
        with open(file_path) as f:
            profile = json.load(f)
    except Exception as e:
        raise ValueError(
            "Load Profile {} : loading error - {}".format(file_path, str(e)))

    for k, v in six.iteritems(profile_format):
        if k not in profile:
            raise ValueError(
                "Load Profile {} : missing key {}".format(file_path, k))
        if not isinstance(profile[k], v):
            raise ValueError(
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
