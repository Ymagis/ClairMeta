# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import os

from clairmeta.utils.probe import probe_folder, probe_mediainfo
from clairmeta.check_sequence import check_sequence
from clairmeta.settings import DCDM_SETTINGS


class DCDM(object):
    """ Digital Cinema Distribution Master abstraction. """

    def __init__(self, path):
        """ DCDM constructor.

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
            DCDM_SETTINGS['allowed_extensions'],
            DCDM_SETTINGS['file_white_list'],
            DCDM_SETTINGS['directory_white_list']
        )

        # To save time, we check only the first file for correct structure,
        # check_sequence already check that all files are exactly the same
        # size so we assume they are of similar characteristic (this is
        # possible because dcdm are not compressed sequences).
        for dirpath, dirnames, filenames in os.walk(self.path):
            if not filenames:
                continue
            filenames = [f for f in filenames if not f.startswith('.')]
            f = filenames[0]

            probe = probe_mediainfo(os.path.join(dirpath, f))
            img = probe['Probe']['ProbeImage']

            # Note : Metadata are not reliable but we can at least check
            # for 3 channels colorspace.
            if img["Color_space"] not in ["RGB", "XYZ"]:
                raise ValueError(" {} : invalid colorspace detected {}"
                                 .format(f, img["Color_space"]))
            if img["Bit_depth"] != "16 bits":
                raise ValueError("{} : invalid bitdepth detected {}"
                                 .format(f, img["Bit_depth"]))
            if "Compression_mode" in img:
                if img["Compression_mode"] != "Lossless":
                    raise ValueError("{} : invalid compression detected {}"
                                     .format(f, img["Compression_mode"]))

        return True
