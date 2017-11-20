# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import six
import json
import os


DCP_CHECK_PROFILE = {
    # Checker criticality
    # Base level is default and can be overrided per check using its name
    # Incomplete name allowed, the best match will be selected automatically
    # 4 levels : ERROR, WARNING, INFO and SILENT.
    'criticality': {
        'default': 'ERROR',
        'check_dcnc_': 'WARNING',
        'check_cpl_reel_duration_picture_subtitles': 'WARNING',
        'check_picture_cpl_avg_bitrate': 'WARNING',
        'check_picture_cpl_resolution': 'WARNING',
    },
    # Checker options
    # Bypass is a list of check names (function names)
    'bypass': [],
    'log_level': 'INFO',
}


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
