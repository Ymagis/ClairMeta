# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os

from clairmeta.utils.probe import probe_folder
from clairmeta.check_sequence import check_sequence
from clairmeta.settings import DSM_SETTINGS


class DSM(object):
    """ Digital Source Master abstraction. """

    def __init__(self, path):
        """ DSM constructor.

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

    def check(self):
        """ Check validity.

            Raises:
                ValueError: DCDM validity check failure.

        """
        check_sequence(
            self.path,
            DSM_SETTINGS['allowed_extensions'],
            DSM_SETTINGS['file_white_list'],
            DSM_SETTINGS['directory_white_list']
        )

        return True
