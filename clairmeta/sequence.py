# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os
import six

from clairmeta.sequence_check import check_sequence
from clairmeta.settings import SEQUENCE_SETTINGS
from clairmeta.utils.sys import key_by_path_dict
from clairmeta.utils.probe import probe_folder, probe_mediainfo


class Sequence(object):
    """ Image file sequence abstraction. """

    def __init__(self, path):
        """ Sequence constructor.

            Args:
                path (str): Absolute path to directory.

            Raises:
                ValueError: ``path`` directory not found.

        """
        if not os.path.isdir(path):
            raise ValueError("{} is not a valid folder".format(path))

        self.path = path
        self.probe_folder = probe_folder(path)

    def parse(self):
        """ Extract metadata. """
        return self.probe_folder

    def check(self, setting):
        """ Check validity.

            Raises:
                ValueError: Validity check failure.

        """
        check_sequence(
            self.path,
            setting['allowed_extensions'],
            setting['file_white_list'],
            setting['directory_white_list']
        )

        for folder, seqs in six.iteritems(self.probe_folder):
            for seq, keys in six.iteritems(seqs):
                ext = keys.get('Extension')
                check_keys = setting['allowed_extensions'].get('.' + ext)
                probe_keys = keys.get('Probe')

                if not probe_keys or not check_keys:
                    continue

                self._check_keys(check_keys, probe_keys, folder)

        return True

    def _check_keys(self, check_keys, probe_keys, folder):
        """ Compare expected and detected file probe informations.

            Raises:
                ValueError: Mismatch.

        """
        for key, expect_val in six.iteritems(check_keys):
            val = key_by_path_dict(probe_keys, key)

            if isinstance(expect_val, list):
                if val not in expect_val:
                    raise ValueError("{} - Invalid {}, got {} but expected"
                                     .format(folder, key, val, expect_val))
            else:
                if val != expect_val:
                    raise ValueError("{} - Invalid {}, got {} but expected {}"
                                     .format(folder, key, val, expect_val))
